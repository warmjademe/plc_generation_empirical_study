"""Bounded generation loop with visible feedback and a terminal sealed judge."""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .client import (
    ModelClient,
    OpenAICompatibleClient,
    ProviderSettings,
    is_retryable_model_error,
)
from .cancellation import raise_if_cancelled
from .context import build_task_state, load_pattern_cards
from .dataset import TaskPackage, load_task
from .ledger import EvidenceLedger
from .models import AttemptOutcome, Evidence, GateResult, ParsedCandidate
from .policy import (
    build_evidence_certificate,
    build_evidence_certificate_v2,
    build_evidence_certificate_v3,
    build_raw_feedback,
    choose_anchor,
    choose_repair_mode,
)
from .response import parse_candidate
from .validators import Validator, validators_from_config


METHODS = {"direct", "independent", "raw_repair", "evidence"}

DIVERSIFICATION_PROFILES: dict[str, tuple[str, ...]] = {
    "contrastive_guard_table": (
        "Before coding, enumerate normal, exception, and complement cases for every without/unless/only-when clause.",
        "Use one mutually exclusive priority table so an exception cannot accidentally reuse the normal-branch result.",
    ),
    "pre_state_event_snapshot": (
        "Snapshot retained states needed by event or pulse decisions before updating them.",
        "Distinguish a state active at scan start from the same state newly set during the scan, and clear pulse outputs by default.",
    ),
    "transition_then_decode": (
        "Update retained state in one dominant IF/ELSIF transition section, then derive every external output in a separate final decode section.",
        "Audit same-scan reset, isolation, and stop collisions before emission.",
    ),
    "minimal_priority_chain": (
        "Prefer a compact implementation with one explicit priority chain per retained state and no self-assignments or duplicate shadow state.",
        "Recompute temporary predicates once and reuse them consistently across transition and output logic.",
    ),
    "verification_bounded_state": (
        "Use only requirement-bounded retained state. For each elapsed counter, guard increment with counter < threshold and hold at threshold; do not use an ever-growing global scan clock or subtract timestamps.",
        "Minimize retained integers and timer instances. Use direct local elapsed counters with explicit reset conditions so the formal state space stays finite and behaviorally relevant.",
    ),
}


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _append_progress(artifact_dir: Path, component: str, status: str, **details: Any) -> None:
    """Append public operational telemetry without exposing prompts or hidden cases."""
    event = {
        "time": datetime.now(timezone.utc).isoformat(),
        "component": component,
        "status": status,
        **details,
    }
    with (artifact_dir / "progress.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
        stream.flush()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _gate_from_dict(value: dict[str, Any]) -> GateResult:
    return GateResult(
        name=str(value["name"]),
        status=str(value["status"]),
        summary=str(value.get("summary", "")),
        evidence=tuple(
            Evidence(
                tool=str(item.get("tool", value["name"])),
                kind=str(item.get("kind", "validator_failure")),
                summary=str(item.get("summary", "")),
                requirement_ids=tuple(item.get("requirement_ids", [])),
                severity=str(item.get("severity", "error")),
                trace=item.get("trace"),
                oracle_status=str(item.get("oracle_status", "unconfirmed")),
                raw_log_sha256=item.get("raw_log_sha256"),
            )
            for item in value.get("evidence", [])
        ),
        passed_requirement_ids=tuple(value.get("passed_requirement_ids", [])),
        duration_ms=int(value.get("duration_ms", 0)),
        tool_version=value.get("tool_version"),
    )


def _attempt_from_checkpoint(attempt_dir: Path) -> AttemptOutcome:
    value = json.loads((attempt_dir / "evaluation.json").read_text(encoding="utf-8"))
    candidate_value = dict(value.get("candidate") or {})
    candidate_path = attempt_dir / "candidate.st"
    source_language = str(candidate_value.get("source_language", "st"))
    source_path = attempt_dir / "candidate.ld.json" if source_language == "ld" else candidate_path
    source_text = source_path.read_text(encoding="utf-8") if source_path.is_file() else ""
    parsed = ParsedCandidate(
        program=candidate_path.read_text(encoding="utf-8"),
        hypothesis=str(candidate_value.get("hypothesis", "restored checkpoint")),
        target_requirement_ids=tuple(candidate_value.get("target_requirement_ids", [])),
        format_valid=bool(candidate_value.get("format_valid", True)),
        format_errors=tuple(candidate_value.get("format_errors", [])),
        extraction_mode=str(candidate_value.get("extraction_mode", "restored_checkpoint")),
        source_language=source_language,
        source_text=source_text,
    )
    return AttemptOutcome(
        number=int(value["number"]),
        candidate_path=str(candidate_path),
        candidate_sha256=str(value.get("candidate_sha256") or _sha256(candidate_path)),
        candidate=parsed,
        gates=[_gate_from_dict(item) for item in value.get("gates", [])],
        repair_mode=str(value.get("repair_mode", "SYNTHESIZE")),
        anchor_attempt=value.get("anchor_attempt"),
        usage=dict(value.get("usage") or {}),
        resolved_model=value.get("resolved_model"),
        generation_epoch=int(value.get("generation_epoch", 1)),
        diversification_profile=value.get("diversification_profile"),
    )


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path).resolve()
    value = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or "provider" not in value or "experiment" not in value:
        raise ValueError("config must contain provider and experiment objects")
    value["_config_dir"] = str(config_path.parent)
    value["_config_path"] = str(config_path)
    value["_config_sha256"] = _sha256(config_path)
    return value


class BoundedSynthesisHarness:
    def __init__(
        self,
        config: dict[str, Any],
        task: TaskPackage,
        output_dir: Path,
        method: str,
        *,
        client: ModelClient | None = None,
        validators: list[Validator] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ):
        if method not in METHODS:
            raise ValueError(f"unknown method {method!r}")
        self.config = config
        self.task = task
        self.output_dir = output_dir.resolve()
        self.method = method
        self.provider = ProviderSettings.from_dict(config["provider"])
        self.experiment = dict(config["experiment"])
        self.output_language = str(self.experiment.get("output_language", "st")).lower()
        if self.output_language not in {"st", "ld"}:
            raise ValueError("output_language must be st or ld")
        self.ablation_id = self.experiment.get("ablation_id")
        self.core_component_1_enabled = bool(
            self.experiment.get("core_component_1_enabled", method == "evidence")
        )
        self.core_component_2_enabled = bool(
            self.experiment.get(
                "core_component_2_enabled",
                self.experiment.get("sealed_rejection_policy") == "blind_restart"
                or self.experiment.get("inconclusive_recovery_policy") == "blind_restart",
            )
        )
        configured_max = int(self.experiment.get("max_candidates", 20))
        if configured_max < 1 or configured_max > 20:
            raise ValueError("max_candidates must be between 1 and 20")
        self.max_candidates = 1 if method == "direct" else configured_max
        self.model_call_attempts_per_candidate = int(
            self.experiment.get("model_call_attempts_per_candidate", 3)
        )
        if not 1 <= self.model_call_attempts_per_candidate <= 5:
            raise ValueError("model_call_attempts_per_candidate must be between 1 and 5")
        self.max_feedback_chars = int(self.experiment.get("max_feedback_chars", 6000))
        self.certificate_version = str(self.experiment.get("certificate_version", "v1"))
        if self.certificate_version not in {"v1", "v2", "v3"}:
            raise ValueError("certificate_version must be v1, v2, or v3")
        self.context_strategy = str(self.experiment.get("context_strategy", "full_history"))
        if self.context_strategy not in {"full_history", "state_packet"}:
            raise ValueError("context_strategy must be full_history or state_packet")
        self.anchor_policy = str(self.experiment.get("anchor_policy", "non_regression"))
        if self.anchor_policy not in {"non_regression", "latest"}:
            raise ValueError("anchor_policy must be non_regression or latest")
        self.repair_policy = str(self.experiment.get("repair_policy", "adaptive"))
        if self.repair_policy not in {"adaptive", "patch"}:
            raise ValueError("repair_policy must be adaptive or patch")
        self.pre_emit_review_enabled = bool(self.experiment.get("pre_emit_review", False))
        self.contract_risk_analysis_enabled = bool(
            self.experiment.get("contract_risk_analysis", False)
        )
        self.duplicate_candidate_guard_enabled = bool(
            self.experiment.get("duplicate_candidate_guard", False)
        )
        self.sealed_rejection_policy = str(
            self.experiment.get("sealed_rejection_policy", "terminal")
        )
        if self.sealed_rejection_policy not in {"terminal", "blind_restart", "feedback_repair"}:
            raise ValueError(
                "sealed_rejection_policy must be terminal, blind_restart, or feedback_repair"
            )
        self.max_sealed_attempts = int(self.experiment.get("max_sealed_attempts", 1))
        if not 1 <= self.max_sealed_attempts <= self.max_candidates:
            raise ValueError("max_sealed_attempts must be between 1 and max_candidates")
        self.inconclusive_recovery_policy = str(
            self.experiment.get("inconclusive_recovery_policy", "terminal")
        )
        if self.inconclusive_recovery_policy not in {"terminal", "blind_restart"}:
            raise ValueError(
                "inconclusive_recovery_policy must be terminal or blind_restart"
            )
        self.max_inconclusive_restarts = int(
            self.experiment.get("max_inconclusive_restarts", 0)
        )
        if not 0 <= self.max_inconclusive_restarts < self.max_candidates:
            raise ValueError(
                "max_inconclusive_restarts must be between 0 and max_candidates - 1"
            )
        configured_profiles = self.experiment.get(
            "blind_restart_profiles", list(DIVERSIFICATION_PROFILES)
        )
        if not isinstance(configured_profiles, list) or not configured_profiles:
            raise ValueError("blind_restart_profiles must be a non-empty list")
        unknown_profiles = set(map(str, configured_profiles)) - set(DIVERSIFICATION_PROFILES)
        if unknown_profiles:
            raise ValueError(f"unknown blind-restart profiles: {sorted(unknown_profiles)}")
        self.blind_restart_profiles = tuple(map(str, configured_profiles))
        self.required_visible_gates = tuple(self.experiment["required_visible_gates"])
        self.sealed_gate_name = str(self.experiment["sealed_gate"])
        if self.experiment.get("stop_on_visible_pass") is not True:
            raise ValueError("this protocol requires stop_on_visible_pass=true")
        self.validators = validators if validators is not None else validators_from_config(
            config.get("validators", []),
            base_dir=Path(config.get("_config_dir", Path.cwd())),
        )
        self.client = client
        self.cancel_check = cancel_check
        for validator in self.validators:
            if hasattr(validator, "cancel_check"):
                validator.cancel_check = cancel_check
        self.attempts: list[AttemptOutcome] = []
        self.sealed_attempts: list[tuple[int, GateResult]] = []
        self.inconclusive_restarts = 0
        self.generation_epoch = 1
        self.epoch_start = 0
        self.next_diversification_profile_id: str | None = None
        self.consumed_candidate_slots = 0

        # The production package is installed into an isolated environment while
        # prompts, knowledge cards and validator scripts remain in the immutable
        # deployment tree.  Resolve that tree explicitly instead of assuming an
        # editable source installation.
        method_root = Path(
            os.getenv("PLC_PROJECT_ROOT", Path(__file__).resolve().parents[2])
        ).resolve()
        prompt_suffix = "_ladder" if self.output_language == "ld" else ""
        system_prompt_path = method_root / f"prompts/system{prompt_suffix}.md"
        response_contract_path = method_root / f"prompts/response_contract{prompt_suffix}.md"
        pattern_cards_path = method_root / "knowledge/iec_st_patterns.json"
        self.system_prompt = system_prompt_path.read_text(encoding="utf-8").strip()
        self.response_contract = response_contract_path.read_text(encoding="utf-8").strip()
        self.method_asset_sha256 = {
            "system_prompt": _sha256(system_prompt_path),
            "response_contract": _sha256(response_contract_path),
            "iec_st_patterns": _sha256(pattern_cards_path),
            "orchestrator": _sha256(Path(__file__).resolve()),
            "context_builder": _sha256(Path(__file__).resolve().with_name("context.py")),
            "repair_policy": _sha256(Path(__file__).resolve().with_name("policy.py")),
        }
        ladder_asset = Path(__file__).resolve().with_name("ladder.py")
        if self.output_language == "ld" and ladder_asset.is_file():
            self.method_asset_sha256["ladder_ir"] = _sha256(ladder_asset)
        for name in (
            "matiec_validator.py",
            "formal_plcverif.py",
            "openplc_sealed_validator.py",
            "openplc_container_runner.py",
        ):
            asset = method_root / "scripts" / name
            if asset.is_file():
                self.method_asset_sha256[f"validator:{name}"] = _sha256(asset)
        context_settings = dict(self.experiment.get("domain_context", {}))
        self.domain_context_enabled = bool(context_settings.get("enabled", False))
        self.domain_context_max_cards = int(context_settings.get("max_cards", 4))
        self.domain_context_max_chars = int(context_settings.get("max_chars", 5000))
        self.pattern_cards = (
            load_pattern_cards(pattern_cards_path)
            if self.domain_context_enabled else []
        )
        self._validate_ablation_contract()

    def _validate_ablation_contract(self) -> None:
        """Fail fast when an RQ2 label does not match the executed mechanisms."""
        if self.ablation_id is None:
            return
        if self.ablation_id == "M01_without_component_1":
            predicates = {
                "method=raw_repair": self.method == "raw_repair",
                "component_1=off": not self.core_component_1_enabled,
                "component_2=on": self.core_component_2_enabled,
                "domain_context=off": not self.domain_context_enabled,
                "pre_emit_review=off": not self.pre_emit_review_enabled,
                "contract_risk_analysis=off": not self.contract_risk_analysis_enabled,
                "duplicate_guard=off": not self.duplicate_candidate_guard_enabled,
                "anchor_policy=latest": self.anchor_policy == "latest",
                "repair_policy=patch": self.repair_policy == "patch",
                "sealed_restart=on": self.sealed_rejection_policy == "blind_restart",
                "sealed_budget=3": self.max_sealed_attempts == 3,
                "inconclusive_restart=on": (
                    self.inconclusive_recovery_policy == "blind_restart"
                    and self.max_inconclusive_restarts == 1
                ),
            }
        elif self.ablation_id == "M10_without_component_2":
            predicates = {
                "method=evidence": self.method == "evidence",
                "component_1=on": self.core_component_1_enabled,
                "component_2=off": not self.core_component_2_enabled,
                "domain_context=on": self.domain_context_enabled,
                "pre_emit_review=on": self.pre_emit_review_enabled,
                "contract_risk_analysis=on": self.contract_risk_analysis_enabled,
                "duplicate_guard=on": self.duplicate_candidate_guard_enabled,
                "anchor_policy=non_regression": self.anchor_policy == "non_regression",
                "repair_policy=adaptive": self.repair_policy == "adaptive",
                "sealed_restart=off": self.sealed_rejection_policy == "terminal",
                "sealed_budget=1": self.max_sealed_attempts == 1,
                "inconclusive_restart=off": (
                    self.inconclusive_recovery_policy == "terminal"
                    and self.max_inconclusive_restarts == 0
                ),
            }
        else:
            raise ValueError(f"unknown RQ2 ablation_id {self.ablation_id!r}")
        failed = [name for name, accepted in predicates.items() if not accepted]
        if failed:
            raise ValueError(
                f"RQ2 ablation contract {self.ablation_id} is inconsistent: {failed}"
            )

    def preflight(self) -> None:
        by_name = {validator.name: validator for validator in self.validators}
        missing = set(self.required_visible_gates) - set(by_name)
        if missing:
            raise ValueError(f"required visible validators are missing: {sorted(missing)}")
        if self.sealed_gate_name not in by_name:
            raise ValueError(f"sealed validator {self.sealed_gate_name!r} is missing")
        if not by_name[self.sealed_gate_name].sealed:
            raise ValueError(f"sealed validator {self.sealed_gate_name!r} is not marked sealed")
        for name in self.required_visible_gates:
            if by_name[name].sealed:
                raise ValueError(f"visible gate {name!r} is marked sealed")
        for validator in self.validators:
            validator.preflight(self.task)

    def _certificate(
        self,
        anchor: AttemptOutcome | None,
        attempts: list[AttemptOutcome] | None = None,
    ) -> dict:
        active_attempts = self.attempts if attempts is None else attempts
        if self.method in {"direct", "independent"}:
            return {"format": "no-feedback-baseline", "selected_failures": []}
        if self.method == "raw_repair":
            return build_raw_feedback(active_attempts, self.max_feedback_chars)
        builders = {
            "v1": build_evidence_certificate,
            "v2": build_evidence_certificate_v2,
            "v3": build_evidence_certificate_v3,
        }
        builder = builders[self.certificate_version]
        return builder(
            active_attempts,
            anchor,
            self.task.critical_requirement_ids,
            self.max_feedback_chars,
        )

    def _prompt(
        self,
        mode: str,
        anchor: AttemptOutcome | None,
        certificate: dict,
        task_state: dict | None,
        diversification_profile: dict[str, Any] | None = None,
    ) -> str:
        anchor_text = "NONE"
        if anchor is not None and self.method not in {"direct", "independent"}:
            anchor_text = (
                anchor.candidate.source_text
                or Path(anchor.candidate_path).read_text(encoding="utf-8")
            )
        mode_instructions = {
            "SYNTHESIZE": "Derive retained state, priority order, and post-scan outputs before emitting the complete program.",
            "PATCH": "Implement the exact failed predicate or scan observation with the smallest correction; do not invent unrelated guards, and preserve every requirement supported by the anchor.",
            "RESTRUCTURE": "Re-derive the interacting state transitions and output-update order from the public requirements, then check the reported trace against the new structure.",
            "RESTART": "Abandon the repeated defective structure and synthesize a different implementation from the public contract and state card.",
        }
        state_text = json.dumps(task_state, ensure_ascii=False, sort_keys=True) if task_state else "DISABLED"
        profile_text = (
            json.dumps(diversification_profile, ensure_ascii=False, sort_keys=True)
            if diversification_profile is not None else "DEFAULT"
        )
        return (
            f"{self.task.public_contract()}\n"
            f"REPAIR MODE\n{mode}\n\n"
            f"MODE INSTRUCTION\n{mode_instructions[mode]}\n\n"
            "BOUNDED TASK STATE AND RETRIEVED IEC CONTEXT\n"
            f"{state_text}\n\n"
            "PUBLIC-ONLY DIVERSIFICATION PROFILE\n"
            f"{profile_text}\n\n"
            "ANCHOR CANDIDATE (never a reference answer)\n"
            f"{anchor_text.rstrip()}\n\n"
            "DETERMINISTIC VALIDATION FEEDBACK\n"
            f"{json.dumps(certificate, ensure_ascii=False, sort_keys=True)}\n\n"
            + (
                "PRIVATE PRE-EMIT CHECK\n"
                "Before responding, trace every public requirement through the complete candidate and mentally execute fresh-instance, reset, simultaneous-priority, held-input, and boundary scans. Do not output this private review.\n\n"
                if self.pre_emit_review_enabled else ""
            )
            + f"RESPONSE CONTRACT\n{self.response_contract}\n"
        )

    def _run_validator(
        self,
        validator: Validator,
        candidate_path: Path,
        artifact_dir: Path,
    ) -> GateResult:
        """Retry transient tool failures on the same candidate without an API call."""
        raise_if_cancelled(self.cancel_check)
        retry_results: list[GateResult] = []
        retries = max(0, int(getattr(validator, "inconclusive_retries", 0)))
        retry_delay = max(
            0.0,
            min(30.0, float(getattr(validator, "inconclusive_retry_delay_seconds", 0.0))),
        )
        for retry_number in range(retries + 1):
            raise_if_cancelled(self.cancel_check)
            _append_progress(
                artifact_dir,
                validator.name,
                "retrying" if retry_number else "started",
                retry=retry_number,
                maximum_retries=retries,
            )
            result = validator.run(self.task, candidate_path, artifact_dir)
            _append_progress(
                artifact_dir,
                validator.name,
                "completed",
                result=result.status,
                duration_ms=result.duration_ms,
                summary=result.summary[:240],
                retry=retry_number,
            )
            retryable = (
                result.status == "inconclusive"
                and result.evidence
                and all(item.kind == "tool_error" for item in result.evidence)
            )
            if not retryable or retry_number >= retries:
                break
            retry_results.append(result)
            if retry_delay:
                time.sleep(retry_delay)
        if not retry_results:
            return result
        _write_json(
            artifact_dir / f"{validator.name}.inconclusive_retries.json",
            {
                "retry_count": len(retry_results),
                "prior_inconclusive_results": [item.to_dict() for item in retry_results],
                "final_result": result.to_dict(),
            },
        )
        return GateResult(
            name=result.name,
            status=result.status,
            summary=f"{result.summary} (after {len(retry_results)} infrastructure retry/retries)",
            evidence=result.evidence,
            passed_requirement_ids=result.passed_requirement_ids,
            duration_ms=result.duration_ms + sum(item.duration_ms for item in retry_results),
            tool_version=result.tool_version,
        )

    def _run_visible(
        self,
        candidate_path: Path,
        artifact_dir: Path,
        parsed: ParsedCandidate,
        duplicate_of_attempt: int | None = None,
    ) -> list[GateResult]:
        results: list[GateResult] = []
        blocked = False
        if parsed.format_errors:
            results.append(
                GateResult(
                    "response_format",
                    "fail",
                    "model response violated the required tagged format",
                    evidence=tuple(
                        Evidence(
                            "response_format",
                            "response_format",
                            item,
                            oracle_status="confirmed_candidate_defect",
                        )
                        for item in parsed.format_errors
                    ),
                    tool_version="built-in-v2",
                )
            )
            blocked = True
        else:
            summary = (
                "complete ST extracted from unterminated wrapper without altering the candidate"
                if parsed.extraction_mode == "unterminated_tag_recovery"
                else "tagged response parsed"
            )
            results.append(GateResult("response_format", "pass", summary, tool_version="built-in-v2"))
        if not blocked and duplicate_of_attempt is not None:
            results.append(
                GateResult(
                    "candidate_novelty",
                    "fail",
                    f"candidate is byte-identical to public candidate attempt {duplicate_of_attempt}",
                    evidence=(Evidence(
                        "candidate_novelty",
                        "duplicate_candidate",
                        "Generate a structurally different implementation; this program is byte-identical to a previously generated candidate.",
                        oracle_status="confirmed_candidate_defect",
                    ),),
                    tool_version="built-in-public-candidate-hash-v1",
                )
            )
            blocked = True
        for validator in self.validators:
            if validator.sealed:
                continue
            if blocked:
                results.append(GateResult(validator.name, "skipped", "blocked by an earlier mandatory gate"))
                _append_progress(
                    artifact_dir,
                    validator.name,
                    "skipped",
                    summary="blocked by an earlier mandatory gate",
                )
                continue
            result = self._run_validator(validator, candidate_path, artifact_dir)
            results.append(result)
            if validator.blocking and (
                result.status == "fail"
                or (result.status == "inconclusive" and getattr(validator, "inconclusive_is_blocking", True))
            ):
                blocked = True
        return results

    def _visible_passed(self, gates: list[GateResult]) -> bool:
        statuses = {gate.name: gate.status for gate in gates}
        if not all(statuses.get(name) == "pass" for name in self.required_visible_gates):
            return False
        validators = {validator.name: validator for validator in self.validators}
        for gate in gates:
            validator = validators.get(gate.name)
            if validator is None or not validator.blocking:
                continue
            if gate.status == "fail":
                return False
            if gate.status == "inconclusive" and getattr(validator, "inconclusive_is_blocking", True):
                return False
        return True

    @staticmethod
    def _sum_usage(attempts: list[AttemptOutcome]) -> dict[str, int | float]:
        totals: dict[str, int | float] = {}
        for attempt in attempts:
            for key, value in attempt.usage.items():
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    totals[key] = totals.get(key, 0) + value
        return totals

    def _finish(
        self,
        ledger: EvidenceLedger,
        status: str,
        sealed: GateResult | None = None,
        last_error: str | None = None,
    ) -> dict:
        result = {
            "schema_version": "1.0",
            "task_id": self.task.task_id,
            "method": self.method,
            "output_language": self.output_language,
            "status": status,
            "success": status == "verified_success",
            "candidate_budget": self.max_candidates,
            "candidates_used": len(self.attempts),
            "candidate_slots_consumed": self.consumed_candidate_slots,
            "stopped_early": (
                status == "verified_success" and len(self.attempts) < self.max_candidates
            ),
            "requested_model": self.provider.requested_model,
            "provider": self.provider.name,
            "thinking_mode": self.provider.thinking_mode,
            "resolved_models": sorted({item.resolved_model for item in self.attempts if item.resolved_model}),
            "usage_total": self._sum_usage(self.attempts),
            "winning_attempt": self.attempts[-1].number if status == "verified_success" else None,
            "attempts": [item.to_dict() for item in self.attempts],
            "sealed_attempts": [
                {"attempt": number, "result": result.to_dict()}
                for number, result in self.sealed_attempts
            ],
            "sealed_result": sealed.to_dict() if sealed else None,
            "last_error": last_error,
            "development_only": bool(self.experiment.get("development_only", False)),
            "config_sha256": self.config.get("_config_sha256"),
            "method_revision": self.experiment.get("method_revision"),
            "method_asset_sha256": self.method_asset_sha256,
            "verification_profile": self.experiment.get("verification_profile"),
            "mechanisms": {
                "ablation_id": self.ablation_id,
                "core_component_1_enabled": self.core_component_1_enabled,
                "core_component_2_enabled": self.core_component_2_enabled,
                "certificate_version": self.certificate_version,
                "context_strategy": self.context_strategy,
                "domain_context_enabled": self.domain_context_enabled,
                "anchor_policy": self.anchor_policy,
                "repair_policy": self.repair_policy,
                "pre_emit_review_enabled": self.pre_emit_review_enabled,
                "contract_risk_analysis_enabled": self.contract_risk_analysis_enabled,
                "duplicate_candidate_guard_enabled": self.duplicate_candidate_guard_enabled,
                "sealed_rejection_policy": self.sealed_rejection_policy,
                "max_sealed_attempts": self.max_sealed_attempts,
                "inconclusive_recovery_policy": self.inconclusive_recovery_policy,
                "max_inconclusive_restarts": self.max_inconclusive_restarts,
                "inconclusive_restarts_used": self.inconclusive_restarts,
                "blind_restart_profiles": list(self.blind_restart_profiles),
                "model_call_attempts_per_candidate": self.model_call_attempts_per_candidate,
            },
        }
        _write_json(self.output_dir / "result.json", result)
        ledger.append("run_finished", {key: value for key, value in result.items() if key != "attempts"})
        return result

    def _restore_checkpoints(self, ledger: EvidenceLedger) -> int:
        attempt_root = self.output_dir / "attempts"
        slots: list[int] = []
        for path in sorted(attempt_root.glob("attempt_[0-9][0-9]")):
            try:
                slots.append(int(path.name.rsplit("_", 1)[-1]))
            except ValueError:
                continue
            if not (path / "evaluation.json").is_file() or not (path / "candidate.st").is_file():
                continue
            outcome = _attempt_from_checkpoint(path)
            self.attempts.append(outcome)
            sealed_path = path / "sealed_evaluation.json"
            if sealed_path.is_file():
                sealed = _gate_from_dict(json.loads(sealed_path.read_text(encoding="utf-8")))
                self.sealed_attempts.append((outcome.number, sealed))

        entries = EvidenceLedger.verify(self.output_dir / "ledger.jsonl")
        restart_events = [
            item for item in entries
            if item.get("event_type") == "inconclusive_blind_restart_scheduled"
        ]
        self.inconclusive_restarts = len(restart_events)
        epoch_values = [item.generation_epoch for item in self.attempts]
        for item in entries:
            payload = item.get("payload") or {}
            if isinstance(payload.get("next_epoch"), int):
                epoch_values.append(int(payload["next_epoch"]))
        self.generation_epoch = max(epoch_values, default=1)
        self.epoch_start = next(
            (
                index for index, item in enumerate(self.attempts)
                if item.generation_epoch == self.generation_epoch
            ),
            len(self.attempts),
        )
        if restart_events and self.epoch_start == len(self.attempts):
            self.next_diversification_profile_id = str(
                (restart_events[-1].get("payload") or {}).get(
                    "next_profile", "verification_bounded_state"
                )
            )
        ledger.append(
            "run_resumed",
            {
                "completed_candidates": len(self.attempts),
                "consumed_candidate_slots": len(slots),
                "next_candidate_slot": max(slots, default=0) + 1,
            },
        )
        self.consumed_candidate_slots = max(slots, default=0)
        return max(slots, default=0) + 1

    def run(self, *, resume: bool = False) -> dict:
        raise_if_cancelled(self.cancel_check)
        self.preflight()
        ledger_path = self.output_dir / "ledger.jsonl"
        if ledger_path.exists() and not resume:
            raise FileExistsError(f"refusing to overwrite existing run {self.output_dir}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "attempts").mkdir(exist_ok=True)
        ledger = EvidenceLedger(ledger_path)
        next_candidate = 1
        if resume and ledger_path.exists():
            if (self.output_dir / "result.json").is_file():
                return json.loads((self.output_dir / "result.json").read_text(encoding="utf-8"))
            if self.provider.history_mode != "stateless":
                raise RuntimeError("checkpoint recovery requires stateless provider history")
            next_candidate = self._restore_checkpoints(ledger)
            for _, sealed in self.sealed_attempts:
                if sealed.status == "pass":
                    return self._finish(ledger, "verified_success", sealed)
        else:
            ledger.append(
                "run_started",
                {
                "task_id": self.task.task_id,
                "method": self.method,
                "output_language": self.output_language,
                "candidate_budget": self.max_candidates,
                "provider": self.provider.name,
                "requested_model": self.provider.requested_model,
                "thinking_mode": self.provider.thinking_mode,
                "required_visible_gates": list(self.required_visible_gates),
                "sealed_gate": self.sealed_gate_name,
                "public_prompt_files": ["requirement.md", "interface.st"],
                "excluded_prompt_files": ["reference.st", "openplc_tests.json", "properties.json"],
                "certificate_version": self.certificate_version,
                "context_strategy": self.context_strategy,
                "domain_context_enabled": self.domain_context_enabled,
                "anchor_policy": self.anchor_policy,
                "repair_policy": self.repair_policy,
                "pre_emit_review_enabled": self.pre_emit_review_enabled,
                "contract_risk_analysis_enabled": self.contract_risk_analysis_enabled,
                "duplicate_candidate_guard_enabled": self.duplicate_candidate_guard_enabled,
                "sealed_rejection_policy": self.sealed_rejection_policy,
                "max_sealed_attempts": self.max_sealed_attempts,
                "inconclusive_recovery_policy": self.inconclusive_recovery_policy,
                "max_inconclusive_restarts": self.max_inconclusive_restarts,
                "blind_restart_profiles": list(self.blind_restart_profiles),
                "config_sha256": self.config.get("_config_sha256"),
                "method_revision": self.experiment.get("method_revision"),
                "method_asset_sha256": self.method_asset_sha256,
                "verification_profile": self.experiment.get("verification_profile"),
                "ablation_id": self.ablation_id,
                "core_component_1_enabled": self.core_component_1_enabled,
                "core_component_2_enabled": self.core_component_2_enabled,
                "model_call_attempts_per_candidate": self.model_call_attempts_per_candidate,
                },
            )
        if self.client is None:
            self.client = OpenAICompatibleClient(self.provider)
        by_name = {validator.name: validator for validator in self.validators}
        history: list[dict[str, Any]] = [{"role": "system", "content": self.system_prompt}]

        for number in range(next_candidate, self.max_candidates + 1):
            raise_if_cancelled(self.cancel_check)
            self.consumed_candidate_slots = number
            active_attempts = self.attempts[self.epoch_start:]
            if self.method in {"direct", "independent"}:
                anchor = None
            elif self.method == "raw_repair":
                # The raw-repair baseline must not inherit EGBS's non-regression
                # anchor.  It repairs the immediately preceding candidate only.
                anchor = active_attempts[-1] if active_attempts else None
            elif self.anchor_policy == "latest":
                anchor = active_attempts[-1] if active_attempts else None
            else:
                anchor = choose_anchor(active_attempts, self.task.critical_requirement_ids)

            if self.method in {"direct", "independent"} or not active_attempts:
                mode = "SYNTHESIZE"
            elif self.method == "raw_repair":
                # A fixed repair policy isolates the effect of structured EGBS
                # PATCH/RESTRUCTURE/RESTART decisions.
                mode = "PATCH"
            elif self.repair_policy == "patch":
                mode = "PATCH"
            else:
                mode = choose_repair_mode(active_attempts)
            # A structural restart must not show the model the program it has
            # been told to abandon.  Earlier revisions retained the same anchor
            # text and therefore induced repeated near-identical candidates.
            if mode == "RESTART":
                anchor = None
            diversification_profile = None
            diversification_profile_id = None
            if self.generation_epoch > 1:
                resource_recovery = self.next_diversification_profile_id is not None
                if resource_recovery:
                    diversification_profile_id = self.next_diversification_profile_id
                    self.next_diversification_profile_id = None
                else:
                    diversification_profile_id = self.blind_restart_profiles[
                        (self.generation_epoch - 2) % len(self.blind_restart_profiles)
                    ]
                diversification_profile = {
                    "id": diversification_profile_id,
                    "guidance": list(DIVERSIFICATION_PROFILES[diversification_profile_id]),
                    "selection_basis": (
                        "fixed verifier-resource recovery profile; no candidate or diagnostic evidence"
                        if resource_recovery
                        else "fixed public schedule; no sealed evidence"
                    ),
                }
            certificate = self._certificate(anchor, active_attempts)
            task_state = None
            if self.method == "evidence" and self.domain_context_enabled:
                task_state = build_task_state(
                    self.task,
                    active_attempts,
                    anchor,
                    mode,
                    self.pattern_cards,
                    max_cards=self.domain_context_max_cards,
                    max_chars=self.domain_context_max_chars,
                    include_pre_emit_review=self.pre_emit_review_enabled,
                    include_contract_risks=self.contract_risk_analysis_enabled,
                    diversification_profile=diversification_profile,
                )
            prompt = self._prompt(
                mode, anchor, certificate, task_state, diversification_profile
            )
            user_message = {"role": "user", "content": prompt}
            if (
                self.provider.history_mode == "full"
                and self.method == "evidence"
                and self.context_strategy == "full_history"
            ):
                request_messages = history + [user_message]
            else:
                request_messages = [{"role": "system", "content": self.system_prompt}, user_message]

            attempt_dir = self.output_dir / "attempts" / f"attempt_{number:02d}"
            attempt_dir.mkdir()
            _write_json(
                attempt_dir / "request.json",
                {
                    "provider": self.provider.name,
                    "requested_model": self.provider.requested_model,
                    "thinking_mode": self.provider.thinking_mode,
                    "messages": request_messages,
                    "repair_mode": mode,
                    "anchor_attempt": anchor.number if anchor else None,
                    "generation_epoch": self.generation_epoch,
                    "diversification_profile": diversification_profile_id,
                },
            )
            _write_json(attempt_dir / "feedback_certificate.json", certificate)
            if task_state is not None:
                _write_json(attempt_dir / "task_state.json", task_state)
            reply = None
            for model_call_attempt in range(1, self.model_call_attempts_per_candidate + 1):
                raise_if_cancelled(self.cancel_check)
                _append_progress(
                    attempt_dir,
                    "model",
                    "started",
                    repair_mode=mode,
                    generation_epoch=self.generation_epoch,
                    call_attempt=model_call_attempt,
                    maximum_call_attempts=self.model_call_attempts_per_candidate,
                )
                retry_messages = request_messages
                if model_call_attempt > 1:
                    retry_instruction = (
                            "The previous provider call returned no complete candidate. Retry the original "
                            "request and return one complete, concise answer in the required response format. "
                            "Reserve the output budget for the complete PLC program and omit nonessential prose."
                    )
                    retry_messages = [dict(message) for message in request_messages]
                    retry_messages[-1]["content"] = (
                        str(retry_messages[-1].get("content") or "")
                        + "\n\n"
                        + retry_instruction
                    )
                try:
                    reply = self.client.generate(retry_messages)
                    raise_if_cancelled(self.cancel_check)
                    break
                except Exception as exc:
                    error = f"{type(exc).__name__}: {exc}"
                    retryable = is_retryable_model_error(exc)
                    has_next = model_call_attempt < self.model_call_attempts_per_candidate
                    ledger.append(
                        "model_call_failed",
                        {
                            "attempt_slot": number,
                            "call_attempt": model_call_attempt,
                            "maximum_call_attempts": self.model_call_attempts_per_candidate,
                            "retryable": retryable,
                            "error_type": type(exc).__name__,
                            "message": str(exc),
                        },
                    )
                    if retryable and has_next:
                        _append_progress(
                            attempt_dir,
                            "model",
                            "retrying",
                            retry=model_call_attempt + 1,
                            maximum_retries=self.model_call_attempts_per_candidate,
                            summary=error[:240],
                        )
                        continue
                    _append_progress(attempt_dir, "model", "failed", summary=error[:240])
                    return self._finish(ledger, "infrastructure_error", last_error=error)
            if reply is None:
                return self._finish(
                    ledger,
                    "infrastructure_error",
                    last_error="model call ended without a complete candidate",
                )
            _append_progress(
                attempt_dir,
                "model",
                "completed",
                latency_ms=reply.latency_ms,
                resolved_model=reply.resolved_model,
                total_tokens=reply.usage.get("total_tokens"),
            )
            _write_json(attempt_dir / "raw_response.json", reply.raw_response)
            parsed = parse_candidate(
                reply.message,
                self.task.requirement_ids,
                output_language=self.output_language,
                interface_text=self.task.interface_text,
                task_id=self.task.task_id,
            )
            candidate_path = attempt_dir / "candidate.st"
            candidate_path.write_text(parsed.program, encoding="utf-8")
            if parsed.source_language == "ld" and parsed.source_text:
                (attempt_dir / "candidate.ld.json").write_text(
                    parsed.source_text, encoding="utf-8"
                )
            if parsed.ladder_svg is not None:
                (attempt_dir / "candidate.ld.svg").write_text(
                    parsed.ladder_svg, encoding="utf-8"
                )
            _append_progress(
                attempt_dir,
                "response_format",
                "completed",
                result="fail" if parsed.format_errors else "pass",
                summary=(
                    "响应格式存在问题"
                    if parsed.format_errors
                    else "已提取并编译完整梯形图" if self.output_language == "ld"
                    else "已提取完整 ST 程序"
                ),
            )
            candidate_sha256 = _sha256(candidate_path)
            duplicate_of_attempt = next(
                (
                    attempt.number for attempt in self.attempts
                    if attempt.candidate_sha256 == candidate_sha256
                ),
                None,
            ) if self.duplicate_candidate_guard_enabled else None
            gates = self._run_visible(
                candidate_path, attempt_dir, parsed, duplicate_of_attempt
            )
            outcome = AttemptOutcome(
                number=number,
                candidate_path=str(candidate_path),
                candidate_sha256=candidate_sha256,
                candidate=parsed,
                gates=gates,
                repair_mode=mode,
                anchor_attempt=anchor.number if anchor else None,
                usage=reply.usage,
                resolved_model=reply.resolved_model,
                generation_epoch=self.generation_epoch,
                diversification_profile=diversification_profile_id,
            )
            self.attempts.append(outcome)
            _write_json(attempt_dir / "evaluation.json", outcome.to_dict())
            ledger.append("candidate_evaluated", outcome.to_dict())

            blocking_inconclusive = any(
                gate.status == "inconclusive"
                and gate.name in self.required_visible_gates
                for gate in gates
            )
            if blocking_inconclusive:
                if (
                    self.inconclusive_recovery_policy == "blind_restart"
                    and self.inconclusive_restarts < self.max_inconclusive_restarts
                    and number < self.max_candidates
                ):
                    self.inconclusive_restarts += 1
                    self.epoch_start = len(self.attempts)
                    self.generation_epoch += 1
                    self.next_diversification_profile_id = "verification_bounded_state"
                    # An inconclusive result is not a semantic counterexample.
                    # Discard its program and diagnostics, then make one bounded
                    # public-contract resynthesis.  This permits recovery from
                    # candidate-specific state explosion without teaching the
                    # model an unconfirmed property.
                    history = [{"role": "system", "content": self.system_prompt}]
                    ledger.append(
                        "inconclusive_blind_restart_scheduled",
                        {
                            "attempt": number,
                            "completed_epoch": self.generation_epoch - 1,
                            "next_epoch": self.generation_epoch,
                            "restart_number": self.inconclusive_restarts,
                            "policy": "fresh public-contract synthesis; inconclusive diagnostics excluded",
                            "next_profile": self.next_diversification_profile_id,
                        },
                    )
                    continue
                ledger.append(
                    "verification_inconclusive",
                    {
                        "attempt": number,
                        "policy": "stop_without_spending_another_model_candidate",
                        "gates": [
                            gate.to_dict() for gate in gates
                            if gate.status == "inconclusive"
                        ],
                    },
                )
                return self._finish(ledger, "infrastructure_error")

            if (
                self.provider.history_mode == "full"
                and self.method == "evidence"
                and self.context_strategy == "full_history"
            ):
                assistant_message = dict(reply.message)
                assistant_message.setdefault("role", "assistant")
                history.extend([user_message, assistant_message])

            if self._visible_passed(gates):
                sealed_validator = by_name[self.sealed_gate_name]
                sealed = self._run_validator(sealed_validator, candidate_path, attempt_dir)
                _write_json(attempt_dir / "sealed_evaluation.json", sealed.to_dict())
                ledger.append("sealed_judge_completed", {"attempt": number, "result": sealed.to_dict()})
                self.sealed_attempts.append((number, sealed))
                if sealed.status == "pass":
                    return self._finish(ledger, "verified_success", sealed)
                if sealed.status == "fail" and self.sealed_rejection_policy == "feedback_repair":
                    # In production the confirmation suite is not a research
                    # holdout.  Attach its deterministic counterexample to the
                    # current candidate so the next evidence certificate and
                    # anchor decision can use it to repair the ST program.
                    outcome.gates.append(sealed)
                    _write_json(attempt_dir / "evaluation.json", outcome.to_dict())
                    ledger.append(
                        "confirmation_feedback_added",
                        {"attempt": number, "result": sealed.to_dict()},
                    )
                    if number < self.max_candidates:
                        continue
                    return self._finish(ledger, "candidate_budget_exhausted", sealed)
                # Independent@k evaluates fresh, stateless candidates.  A sealed
                # failure may decide whether to consume another candidate slot,
                # but its contents are never added to a later model request.
                if self.method == "independent":
                    continue
                if sealed.status == "fail":
                    if (
                        self.sealed_rejection_policy == "blind_restart"
                        and len(self.sealed_attempts) < self.max_sealed_attempts
                        and number < self.max_candidates
                    ):
                        self.epoch_start = len(self.attempts)
                        self.generation_epoch += 1
                        # Full-history providers must not carry a rejected
                        # candidate or any sealed result into the new epoch.
                        history = [{"role": "system", "content": self.system_prompt}]
                        ledger.append(
                            "sealed_blind_restart_scheduled",
                            {
                                "completed_epoch": self.generation_epoch - 1,
                                "next_epoch": self.generation_epoch,
                                "policy": "fresh public-contract synthesis; sealed contents excluded",
                            },
                        )
                        continue
                    return self._finish(ledger, "sealed_failure", sealed)
                return self._finish(ledger, "sealed_inconclusive", sealed)

        last_sealed = self.sealed_attempts[-1][1] if self.sealed_attempts else None
        return self._finish(ledger, "candidate_budget_exhausted", last_sealed)


def run_from_paths(config_path: Path, task_path: Path, output_dir: Path, method: str) -> dict:
    config = load_config(config_path)
    task = load_task(task_path)
    return BoundedSynthesisHarness(config, task, output_dir, method).run()

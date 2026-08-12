#!/usr/bin/env python3
"""Reproducible adapters for the three external methods in Agents4PLC."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


SOURCE_ROOT = Path(__file__).resolve().parent
OUR_METHOD_ROOT = SOURCE_ROOT / "our_method"
sys.path.insert(0, str(OUR_METHOD_ROOT / "src"))

from plc_loop.client import OpenAICompatibleClient, ProviderSettings  # noqa: E402
from plc_loop.dataset import TaskPackage, load_task  # noqa: E402
from plc_loop.ledger import EvidenceLedger  # noqa: E402
from plc_loop.models import AttemptOutcome, Evidence, GateResult  # noqa: E402
from plc_loop.orchestrator import load_config  # noqa: E402
from plc_loop.policy import build_raw_feedback  # noqa: E402
from plc_loop.response import parse_candidate  # noqa: E402
from plc_loop.validators import validators_from_config  # noqa: E402


EXTERNAL_BASELINES = {
    "llm4plc": {
        "id": "baseline1_llm4plc",
        "label": "LLM4PLC-adapted",
        "implementation_status": "official-prompts-and-workflow-adapted-to-common-judges",
        "upstream_url": "https://github.com/AICPS/LLM_4_PLC",
        "upstream_commit": "fb84215103dea8b1bf4e90b7856ec2ecba6f2dae",
    },
    "agents4plc": {
        "id": "baseline2_agents4plc",
        "label": "Agents4PLC-paper-reimplementation",
        "implementation_status": "paper-reimplemented-full-upstream-workflow-not-public",
        "upstream_url": "https://github.com/Luoji-zju/Agents4PLC_release",
        "upstream_commit": "aac8a8073a2ec55a492a9f790f3c1b946b74a4c2",
    },
    "chatdev": {
        "id": "baseline3_chatdev",
        "label": "ChatDev-1.0-workflow-adapted",
        "implementation_status": "official-chatdev1.0-role-workflow-adapted-to-single-ST-artifact",
        "upstream_url": "https://github.com/OpenBMB/ChatDev/tree/chatdev1.0",
        "upstream_commit": "31fd994416a251ecdeb1f0a73c329271743bfb56",
    },
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _write_json(path: Path, value: object) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _sum_usage(items: list[dict[str, Any]]) -> dict[str, int | float]:
    total: dict[str, int | float] = {}
    for item in items:
        for key, value in item.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                total[key] = total.get(key, 0) + value
    return total


def is_resource_bounded_inconclusive(gate: GateResult) -> bool:
    """A verifier resource limit rejects this candidate but is not a broken harness."""
    if gate.status != "inconclusive":
        return False
    diagnostic = "\n".join([gate.summary, *(item.summary for item in gate.evidence)]).casefold()
    markers = (
        "timeoutexpired",
        "timed out after",
        "timeout during the execution of verification backend",
        "exceeded the verification resource",
    )
    return any(marker in diagnostic for marker in markers)


def _retrieve_public_knowledge(corpus: Path, query: str, limit: int = 5) -> list[str]:
    """Small deterministic lexical retriever; it never reads a task answer artifact."""
    text = corpus.read_text(encoding="utf-8")
    chunks = [item.strip() for item in re.split(r"\n(?=#{1,4}\s)|\n\s*\n", text) if item.strip()]
    terms = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", query.casefold()))
    ranked = []
    for index, chunk in enumerate(chunks):
        chunk_terms = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", chunk.casefold()))
        ranked.append((len(terms & chunk_terms), -index, chunk))
    selected = [item[2] for item in sorted(ranked, reverse=True)[:limit] if item[0] > 0]
    return selected or chunks[:limit]


class ExternalBaselineHarness:
    """Bounded candidate generator preserving each external method's information flow."""

    def __init__(
        self,
        config_path: Path,
        task_dir: Path,
        output: Path,
        baseline: str,
        corpus: Path,
        *,
        client: Any | None = None,
        validators: list[Any] | None = None,
    ):
        self.config_path = config_path.resolve()
        self.config = load_config(self.config_path)
        self.task: TaskPackage = load_task(task_dir)
        self.output = output.resolve()
        self.baseline = baseline
        self.spec = EXTERNAL_BASELINES[baseline]
        self.corpus = corpus.resolve()
        self.provider = ProviderSettings.from_dict(self.config["provider"])
        self.client = client if client is not None else OpenAICompatibleClient(self.provider)
        self.experiment = self.config["experiment"]
        self.max_candidates = int(self.experiment["max_candidates"])
        self.max_feedback_chars = int(self.experiment.get("max_feedback_chars", 6000))
        self.required_visible = tuple(self.experiment["required_visible_gates"])
        self.sealed_name = str(self.experiment["sealed_gate"])
        self.validators = validators if validators is not None else validators_from_config(
            self.config["validators"], Path(self.config["_config_dir"])
        )
        self.attempts: list[AttemptOutcome] = []
        self.sealed_attempts: list[tuple[int, GateResult]] = []
        self.model_call_records: list[dict[str, Any]] = []
        self.resolved_models: set[str] = set()
        self.aux_call_number = 0
        self.response_contract = (OUR_METHOD_ROOT / "prompts/response_contract.md").read_text(
            encoding="utf-8"
        ).strip()

    def preflight(self) -> None:
        if self.max_candidates != 10:
            raise ValueError("external baseline comparison requires max_candidates=10")
        if self.required_visible != ("compiler", "plcverif") or self.sealed_name != "openplc":
            raise ValueError("external baselines require MatIEC -> PLCverif -> OpenPLC")
        if [item.name for item in self.validators] != ["compiler", "plcverif", "openplc"]:
            raise ValueError("validator order differs from the frozen common judging protocol")
        if not self.corpus.is_file():
            raise FileNotFoundError(self.corpus)
        for validator in self.validators:
            validator.preflight(self.task)

    def _call_model(self, system: str, user: str, call_kind: str, directory: Path) -> Any:
        directory.mkdir(parents=True, exist_ok=False)
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        _write_json(directory / "request.json", {
            "baseline_id": self.spec["id"],
            "call_kind": call_kind,
            "messages": messages,
        })
        reply = self.client.generate(messages)
        _write_json(directory / "raw_response.json", reply.raw_response)
        _write_json(directory / "assistant_message.json", reply.message)
        record = {
            "call_kind": call_kind,
            "requested_model": reply.requested_model,
            "resolved_model": reply.resolved_model,
            "usage": reply.usage,
            "latency_ms": reply.latency_ms,
        }
        _write_json(directory / "call_record.json", record)
        self.model_call_records.append(record)
        self.resolved_models.add(reply.resolved_model)
        return reply

    def _aux_call(self, system: str, user: str, call_kind: str) -> str:
        self.aux_call_number += 1
        directory = self.output / "aux_calls" / f"call_{self.aux_call_number:02d}_{call_kind}"
        reply = self._call_model(system, user, call_kind, directory)
        return str(reply.message.get("content") or "")

    def _planning(self) -> tuple[str, str]:
        contract = self.task.public_contract()
        if self.baseline == "llm4plc":
            system = (
                "Act as the planning phase of LLM4PLC. Convert an IEC 61131-3 ST requirement "
                "into a detailed model-based design. Respect PLC scan-cycle state, list declarations, "
                "state transitions, outputs, and edge/timer behavior. Do not emit code and do not ask questions."
            )
            plan = self._aux_call(system, contract, "planning")
            return plan, ""
        if self.baseline == "agents4plc":
            chunks = _retrieve_public_knowledge(self.corpus, contract)
            retrieval = "\n\n---\n\n".join(chunks)
            (self.output / "retrieved_context.md").write_text(retrieval + "\n", encoding="utf-8")
            system = (
                "Act as the Agents4PLC Planning Agent. Rank a concrete IEC ST implementation plan "
                "using only the public task and retrieved IEC knowledge. Include scan states, invariants, "
                "fixed interface handling, initialization, and a direct coding sequence. Do not emit ST."
            )
            plan = self._aux_call(
                system,
                f"PUBLIC TASK\n{contract}\n\nRETRIEVED KNOWLEDGE\n{retrieval}",
                "planning",
            )
            return plan, retrieval
        analysis = self._aux_call(
            "Act as ChatDev's Chief Product Officer. Convert the public request into a precise, complete "
            "single-artifact product specification. The requested product is one IEC 61131-3 Structured "
            "Text function block. Do not write code.",
            contract,
            "demand_analysis",
        )
        design = self._aux_call(
            "Act as ChatDev's Chief Technology Officer. Produce a software design for one IEC 61131-3 "
            "Structured Text function block. Preserve the supplied interface and PLC scan-cycle semantics. "
            "Do not write code.",
            f"PUBLIC TASK\n{contract}\n\nPRODUCT ANALYSIS\n{analysis}",
            "technology_design",
        )
        return design, analysis

    def _raw_feedback(self) -> str:
        return str(build_raw_feedback(self.attempts, self.max_feedback_chars).get("text", ""))

    def _candidate_messages(
        self, number: int, plan: str, retrieved_or_analysis: str
    ) -> tuple[str, str, str, int | None]:
        contract = self.task.public_contract()
        common = (
            "Return one complete IEC 61131-3 Structured Text FUNCTION_BLOCK. Preserve the fixed interface. "
            "The fixed interface is a declaration skeleton: reproduce its FUNCTION_BLOCK name, complete "
            "VAR_INPUT block, and complete VAR_OUTPUT block before local VAR declarations and executable "
            "statements, with one END_FUNCTION_BLOCK after the body. Emit no comments or only IEC block "
            "comments (* ... *); do not use // comments because the frozen MatIEC profile rejects them. "
            "No Markdown fences or additional files. Follow this exact response contract:\n"
            f"{self.response_contract}"
        )
        if self.baseline == "llm4plc":
            if number == 1:
                return (
                    "Act as the LLM4PLC SCL code generation phase. " + common,
                    f"PUBLIC TASK\n{contract}\n\nMODEL-BASED DESIGN PLAN\n{plan}",
                    "LLM4PLC_SYNTHESIZE",
                    None,
                )
            previous = Path(self.attempts[-1].candidate_path).read_text(encoding="utf-8")
            return (
                "Act as the LLM4PLC toolchain-feedback repair phase. Diagnose the supplied compiler or "
                "formal-verifier report and return the complete corrected program. " + common,
                f"PUBLIC TASK\n{contract}\n\nPLAN\n{plan}\n\nPREVIOUS ST\n{previous}"
                f"\n\nTOOLCHAIN FEEDBACK\n{self._raw_feedback()}",
                "LLM4PLC_TOOLCHAIN_REPAIR",
                number - 1,
            )
        if self.baseline == "agents4plc":
            if number == 1:
                return (
                    "Act as the Agents4PLC Coding Agent. Use the plan and retrieved PLC knowledge. " + common,
                    f"PUBLIC TASK\n{contract}\n\nPLAN\n{plan}\n\nRETRIEVED KNOWLEDGE\n{retrieved_or_analysis}",
                    "AGENTS4PLC_CODE",
                    None,
                )
            previous = Path(self.attempts[-1].candidate_path).read_text(encoding="utf-8")
            advice = self._aux_call(
                "Act as the Agents4PLC Debugging Agent. Analyze the latest ST and deterministic "
                "MatIEC/PLCverif diagnostics. Give concrete fixing advice tied to the public requirements. "
                "Do not emit a replacement program.",
                f"PUBLIC TASK\n{contract}\n\nLATEST ST\n{previous}"
                f"\n\nVALIDATION DIAGNOSTICS\n{self._raw_feedback()}",
                f"debugging_attempt_{number:02d}",
            )
            return (
                "Act as the Agents4PLC Coding Agent receiving advice from the Debugging Agent. "
                "Return the complete repaired program, not a patch. " + common,
                f"PUBLIC TASK\n{contract}\n\nPLAN\n{plan}\n\nRETRIEVED KNOWLEDGE\n"
                f"{retrieved_or_analysis}\n\nLATEST ST\n{previous}\n\nDEBUGGING ADVICE\n{advice}",
                "AGENTS4PLC_DEBUG_REPAIR",
                number - 1,
            )
        if number == 1:
            return (
                "Act as ChatDev's Programmer implementing the CTO design. " + common,
                f"PUBLIC TASK\n{contract}\n\nPRODUCT ANALYSIS\n{retrieved_or_analysis}\n\nCTO DESIGN\n{plan}",
                "CHATDEV_CODING",
                None,
            )
        previous = Path(self.attempts[-1].candidate_path).read_text(encoding="utf-8")
        review = self._aux_call(
            "Act as ChatDev's Code Reviewer. Review the latest Structured Text against the public task. "
            "Return the highest-priority correctness comment and concrete revision instructions. You do "
            "not receive or infer hidden tests, formal properties, or tool diagnostics.",
            f"PUBLIC TASK\n{contract}\n\nLATEST ST\n{previous}",
            f"code_review_attempt_{number:02d}",
        )
        return (
            "Act as ChatDev's Programmer applying the Code Review Modification phase. "
            "Return the complete revised program. " + common,
            f"PUBLIC TASK\n{contract}\n\nCTO DESIGN\n{plan}\n\nLATEST ST\n{previous}"
            f"\n\nCODE REVIEW\n{review}",
            "CHATDEV_REVIEW_REPAIR",
            number - 1,
        )

    def _run_visible(
        self, candidate: Path, artifact: Path, format_errors: tuple[str, ...]
    ) -> list[GateResult]:
        results = []
        blocked = bool(format_errors)
        results.append(GateResult(
            "response_format",
            "fail" if blocked else "pass",
            "external baseline response failed the shared contract" if blocked else "shared response contract parsed",
            evidence=tuple(Evidence("response_format", "response_format", item) for item in format_errors),
            tool_version="built-in-v1",
        ))
        for validator in self.validators:
            if validator.sealed:
                continue
            if blocked:
                results.append(GateResult(validator.name, "skipped", "blocked by an earlier mandatory gate"))
                continue
            result = validator.run(self.task, candidate, artifact)
            results.append(result)
            if validator.blocking and result.status in {"fail", "inconclusive"}:
                blocked = True
        return results

    def _visible_passed(self, gates: list[GateResult]) -> bool:
        statuses = {gate.name: gate.status for gate in gates}
        return all(statuses.get(name) == "pass" for name in self.required_visible)

    def _finish(self, ledger: EvidenceLedger, status: str, sealed: GateResult | None = None) -> dict[str, Any]:
        usage = _sum_usage([item["usage"] for item in self.model_call_records])
        result = {
            "schema_version": "1.0",
            "task_id": self.task.task_id,
            "baseline_id": self.spec["id"],
            "label": self.spec["label"],
            "implementation_status": self.spec["implementation_status"],
            "upstream_url": self.spec["upstream_url"],
            "upstream_commit": self.spec["upstream_commit"],
            "status": status,
            "success": status == "verified_success",
            "candidate_budget": self.max_candidates,
            "candidates_used": len(self.attempts),
            "model_calls_used": len(self.model_call_records),
            "auxiliary_model_calls": len(self.model_call_records) - len(self.attempts),
            "winning_attempt": self.attempts[-1].number if status == "verified_success" else None,
            "requested_model": self.provider.requested_model,
            "thinking_mode": self.provider.thinking_mode,
            "resolved_models": sorted(self.resolved_models),
            "usage_total": usage,
            "attempts": [item.to_dict() for item in self.attempts],
            "sealed_attempts": [
                {"attempt": number, "result": item.to_dict()}
                for number, item in self.sealed_attempts
            ],
            "sealed_result": sealed.to_dict() if sealed else None,
        }
        _write_json(self.output / "result.json", result)
        ledger.append("run_finished", {key: value for key, value in result.items() if key != "attempts"})
        return result

    def run(self) -> dict[str, Any]:
        self.preflight()
        if self.output.exists():
            raise FileExistsError(f"refusing to overwrite external baseline run {self.output}")
        self.output.mkdir(parents=True)
        (self.output / "attempts").mkdir()
        (self.output / "aux_calls").mkdir()
        ledger = EvidenceLedger(self.output / "ledger.jsonl")
        ledger.append("run_started", {
            "task_id": self.task.task_id,
            "baseline_id": self.spec["id"],
            "implementation_status": self.spec["implementation_status"],
            "upstream_commit": self.spec["upstream_commit"],
            "candidate_budget": self.max_candidates,
            "thinking_mode": self.provider.thinking_mode,
            "verification_profile": "MatIEC -> PLCverif -> terminal sealed OpenPLC",
            "public_prompt_files": ["requirement.md", "interface.st"],
            "excluded_prompt_files": ["reference.st", "properties.json", "openplc_tests.json"],
        })
        try:
            plan, retrieved_or_analysis = self._planning()
        except Exception as exc:
            ledger.append("model_call_failed", {"stage": "planning", "error": f"{type(exc).__name__}: {exc}"})
            return self._finish(ledger, "infrastructure_error")

        by_name = {item.name: item for item in self.validators}
        for number in range(1, self.max_candidates + 1):
            attempt_dir = self.output / "attempts" / f"attempt_{number:02d}"
            try:
                system, user, mode, anchor = self._candidate_messages(number, plan, retrieved_or_analysis)
                reply = self._call_model(system, user, f"candidate_{number:02d}", attempt_dir)
            except Exception as exc:
                ledger.append("model_call_failed", {
                    "stage": "candidate", "attempt_slot": number,
                    "error": f"{type(exc).__name__}: {exc}",
                })
                return self._finish(ledger, "infrastructure_error")
            parsed = parse_candidate(reply.message, self.task.requirement_ids)
            candidate = attempt_dir / "candidate.st"
            candidate.write_text(parsed.program, encoding="utf-8")
            gates = self._run_visible(candidate, attempt_dir, parsed.format_errors)
            outcome = AttemptOutcome(
                number=number,
                candidate_path=str(candidate),
                candidate_sha256=_sha256(candidate),
                candidate=parsed,
                gates=gates,
                repair_mode=mode,
                anchor_attempt=anchor,
                usage=reply.usage,
                resolved_model=reply.resolved_model,
            )
            self.attempts.append(outcome)
            _write_json(attempt_dir / "evaluation.json", outcome.to_dict())
            ledger.append("candidate_evaluated", outcome.to_dict())
            fatal_inconclusive = [
                gate for gate in gates
                if gate.status == "inconclusive" and not is_resource_bounded_inconclusive(gate)
            ]
            if fatal_inconclusive:
                return self._finish(ledger, "infrastructure_error")
            if not self._visible_passed(gates):
                continue
            sealed = by_name[self.sealed_name].run(self.task, candidate, attempt_dir)
            _write_json(attempt_dir / "sealed_evaluation.json", sealed.to_dict())
            ledger.append("sealed_judge_completed", {"attempt": number, "result": sealed.to_dict()})
            self.sealed_attempts.append((number, sealed))
            if sealed.status == "pass":
                return self._finish(ledger, "verified_success", sealed)
            if sealed.status == "fail":
                return self._finish(ledger, "sealed_failure", sealed)
            return self._finish(ledger, "sealed_inconclusive", sealed)
        return self._finish(ledger, "candidate_budget_exhausted")


def _validate_config(config: dict[str, Any]) -> None:
    experiment = config.get("experiment", {})
    if int(experiment.get("max_candidates", 0)) != 10:
        raise ValueError("comparison config must declare max_candidates=10")
    if experiment.get("required_visible_gates") != ["compiler", "plcverif"]:
        raise ValueError("visible gates must be compiler then plcverif")
    if experiment.get("sealed_gate") != "openplc":
        raise ValueError("sealed gate must be openplc")
    if [item.get("name") for item in config.get("validators", [])] != ["compiler", "plcverif", "openplc"]:
        raise ValueError("validator order must be MatIEC -> PLCverif -> OpenPLC")


def run_external_baseline(baseline: str, argv: list[str] | None = None) -> int:
    spec = EXTERNAL_BASELINES[baseline]
    parser = argparse.ArgumentParser(description=f"Run {spec['label']}")
    parser.add_argument("--config", type=Path, default=OUR_METHOD_ROOT / "configs/kimi_k3_runtime_full.json")
    parser.add_argument("--dataset-root", required=True, type=Path)
    parser.add_argument("--qualification", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--task-id", action="append", default=[])
    parser.add_argument("--public-corpus", type=Path, default=SOURCE_ROOT / "datasets/IEC_ST_CORE.md")
    args = parser.parse_args(argv)

    config_path = args.config.resolve()
    dataset_root = args.dataset_root.resolve()
    qualification_path = args.qualification.resolve()
    output = args.output.resolve()
    corpus = args.public_corpus.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    _validate_config(config)
    key_env = str(config["provider"]["api_key_env"])
    if not os.environ.get(key_env):
        raise RuntimeError(f"{key_env} is required; silent fallback is forbidden")
    qualification = json.loads(qualification_path.read_text(encoding="utf-8"))
    if qualification.get("status") == "pass":
        qualified = {
            str(item["task_id"])
            for item in qualification.get("tasks", [])
            if item.get("qualified") is True
        }
    elif qualification.get("success") is True:
        qualified = {
            str(item["task_id"])
            for item in qualification.get("tasks", [])
            if item.get("status") == "pass"
        }
    else:
        raise ValueError("a completed passing qualification or calibration summary is required")
    task_root = dataset_root / "tasks" if (dataset_root / "tasks").is_dir() else dataset_root
    task_dirs = sorted(path for path in task_root.iterdir() if path.is_dir())
    if args.task_id:
        selected = set(args.task_id)
        missing = selected - {path.name for path in task_dirs}
        if missing:
            raise ValueError(f"unknown task IDs: {sorted(missing)}")
        task_dirs = [path for path in task_dirs if path.name in selected]
    unqualified = {path.name for path in task_dirs} - qualified
    if unqualified:
        raise ValueError(f"unqualified tasks selected: {sorted(unqualified)}")
    if not task_dirs:
        raise ValueError("no tasks selected")
    if output == dataset_root or dataset_root in output.parents:
        raise ValueError("output must be outside the frozen dataset")
    output.mkdir(parents=True, exist_ok=True)
    run_spec = {
        "schema_version": "1.0",
        **spec,
        "config_sha256": _sha256(config_path),
        "dataset_tree_sha256": _tree_sha256(dataset_root),
        "qualification_sha256": _sha256(qualification_path),
        "public_corpus_sha256": _sha256(corpus),
        "task_ids": [path.name for path in task_dirs],
    }
    run_spec_path = output / "run_spec.json"
    if run_spec_path.is_file():
        if json.loads(run_spec_path.read_text(encoding="utf-8")) != run_spec:
            raise RuntimeError("resume refused: external baseline run specification changed")
    else:
        if any(output.iterdir()):
            raise FileExistsError(f"refusing unbound non-empty output: {output}")
        _write_json(run_spec_path, run_spec)

    allowed = tuple(config["provider"].get(
        "allowed_resolved_models", [config["provider"]["requested_model"]]
    ))

    def run_task(task_dir: Path) -> dict[str, Any]:
        run_dir = output / task_dir.name
        result_path = run_dir / "result.json"
        if result_path.is_file():
            result = json.loads(result_path.read_text(encoding="utf-8"))
            resumed = True
        else:
            if run_dir.exists():
                raise RuntimeError("incomplete run exists; refusing potentially duplicate model calls")
            result = ExternalBaselineHarness(config_path, task_dir, run_dir, baseline, corpus).run()
            resumed = False
        if result.get("baseline_id") != spec["id"] or result.get("task_id") != task_dir.name:
            raise RuntimeError("persisted result does not match task or external baseline")
        entries = EvidenceLedger.verify(run_dir / "ledger.jsonl")
        requests = sorted(run_dir.glob("**/request.json"))
        reference = (task_dir / "reference.st").read_text(encoding="utf-8").strip()
        prompt_isolation = True
        for request in requests:
            document = json.loads(request.read_text(encoding="utf-8"))
            messages = document.get("messages", [])
            prompt = "\n".join(str(item.get("content", "")) for item in messages)
            prompt_isolation = prompt_isolation and [item.get("role") for item in messages] == ["system", "user"]
            prompt_isolation = prompt_isolation and (not reference or reference not in prompt)
        models_ok = all(
            any(model == item or str(model).startswith(f"{item}-") for item in allowed)
            for model in result.get("resolved_models", [])
        )
        return {
            "task_id": task_dir.name,
            "status": result["status"],
            "success": bool(result["success"]),
            "candidates_used": int(result["candidates_used"]),
            "model_calls_used": int(result["model_calls_used"]),
            "winning_attempt": result.get("winning_attempt"),
            "usage_total": result.get("usage_total", {}),
            "ledger_valid": bool(entries),
            "request_count_valid": len(requests) == int(result["model_calls_used"]),
            "prompt_isolation_valid": prompt_isolation,
            "resolved_model_valid": models_ok,
            "resumed": resumed,
        }

    records = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(run_task, task_dir): task_dir.name for task_dir in task_dirs}
        for future in as_completed(futures):
            task_id = futures[future]
            try:
                record = future.result()
            except Exception as exc:
                record = {
                    "task_id": task_id, "status": "batch_exception", "success": False,
                    "error": f"{type(exc).__name__}: {exc}", "ledger_valid": False,
                    "request_count_valid": False, "prompt_isolation_valid": False,
                    "resolved_model_valid": False,
                }
            records.append(record)
            print(json.dumps({
                "task_id": task_id, "status": record["status"],
                "candidates_used": record.get("candidates_used"),
                "model_calls_used": record.get("model_calls_used"),
            }, ensure_ascii=False), flush=True)
            _write_json(output / "progress.json", sorted(records, key=lambda item: item["task_id"]))
    records.sort(key=lambda item: item["task_id"])
    protocol_ok = all(
        item.get("ledger_valid") and item.get("request_count_valid")
        and item.get("prompt_isolation_valid") and item.get("resolved_model_valid")
        for item in records
    )
    summary = {
        **run_spec,
        "task_count": len(records),
        "success_count": sum(item.get("success", False) for item in records),
        "total_candidates_used": sum(int(item.get("candidates_used", 0)) for item in records),
        "total_model_calls_used": sum(int(item.get("model_calls_used", 0)) for item in records),
        "usage_total": _sum_usage([item.get("usage_total", {}) for item in records]),
        "protocol_ok": protocol_ok,
        "runs": records,
    }
    _write_json(output / "baseline_summary.json", summary)
    print(json.dumps({
        "baseline": spec["label"], "task_count": len(records),
        "success_count": summary["success_count"], "protocol_ok": protocol_ok,
    }, ensure_ascii=False))
    return 0 if protocol_ok and not any(item["status"] == "batch_exception" for item in records) else 2

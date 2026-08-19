#!/usr/bin/env python3
"""Baseline 4: the official Claude Code CLI, restricted to Claude Sonnet 5.

Claude Code receives up to ten independent opportunities per task.  Every
opportunity uses a new non-persistent session and workspace initialized from the
same public requirement and interface.  The outer harness invokes the frozen
MatIEC -> PLCverif -> OpenPLC judges, but no candidate, diagnostic, or verdict is
ever returned to a later opportunity.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol


SOURCE_ROOT = Path(__file__).resolve().parent
OUR_METHOD_ROOT = SOURCE_ROOT / "our_method"
sys.path.insert(0, str(OUR_METHOD_ROOT / "src"))

from baseline0_external_runner import (  # noqa: E402
    _sha256,
    _sum_usage,
    _tree_sha256,
    _validate_config,
    _write_json,
    is_resource_bounded_inconclusive,
)
from plc_loop.dataset import TaskPackage, load_task  # noqa: E402
from plc_loop.ledger import EvidenceLedger  # noqa: E402
from plc_loop.models import AttemptOutcome, GateResult, ParsedCandidate  # noqa: E402
from plc_loop.process import run_captured  # noqa: E402
from plc_loop.validators import validators_from_config  # noqa: E402


BASELINE_SPEC = {
    "id": "baseline4_claude_code_sonnet5",
    "label": "Claude-Code-Sonnet-5",
    "implementation_status": "official-cli-isolated-common-judge-adapter",
    "upstream_url": "https://docs.anthropic.com/en/docs/claude-code/cli-usage",
}

PUBLIC_FILES = {"requirement.md", "interface.st", "candidate.st"}
WRITEABLE_FILES = {"candidate.st"}


@dataclass(frozen=True)
class ClaudeCallResult:
    session_id: str
    result_text: str
    resolved_models: tuple[str, ...]
    usage: dict[str, int | float]
    duration_ms: int
    agent_turns: int
    total_cost_usd: float | None
    access_audit_valid: bool


class ClaudeAgent(Protocol):
    requested_model: str
    expected_model: re.Pattern[str]

    def preflight(self) -> str: ...

    def invoke(
        self,
        workspace: Path,
        prompt: str,
        call_dir: Path,
        session_id: str,
    ) -> ClaudeCallResult: ...


def _usage_from_events(events: list[dict[str, Any]]) -> dict[str, int | float]:
    """Sum usage once per assistant event and cost once per result event."""
    usage: dict[str, int | float] = {}
    for event in events:
        if event.get("type") == "assistant":
            message_usage = event.get("message", {}).get("usage", {})
            if isinstance(message_usage, dict):
                for key, value in message_usage.items():
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        usage[key] = usage.get(key, 0) + value
        if event.get("type") == "result":
            value = event.get("total_cost_usd")
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                usage["total_cost_usd"] = usage.get("total_cost_usd", 0) + value
    return usage


def _models_from_events(events: list[dict[str, Any]]) -> tuple[str, ...]:
    models: set[str] = set()
    for event in events:
        if event.get("type") == "system" and isinstance(event.get("model"), str):
            models.add(event["model"])
        if event.get("type") == "assistant":
            model = event.get("message", {}).get("model")
            if isinstance(model, str):
                models.add(model)
        model_usage = event.get("modelUsage") or event.get("model_usage")
        if isinstance(model_usage, dict):
            models.update(str(key) for key in model_usage)
    return tuple(sorted(models))


def _tool_uses(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    uses = []
    for event in events:
        message = event.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                uses.append(block)
    return uses


def _path_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _audit_tool_access(events: list[dict[str, Any]], workspace: Path) -> dict[str, Any]:
    """Reject undeclared tools and reads/writes outside the public workspace."""
    workspace = workspace.resolve()
    records = []
    violations = []
    for block in _tool_uses(events):
        name = str(block.get("name", ""))
        inputs = block.get("input") if isinstance(block.get("input"), dict) else {}
        path_value = inputs.get("file_path") or inputs.get("path")
        record: dict[str, Any] = {"tool": name, "path": path_value}
        if name not in {"Read", "Write", "Edit"}:
            violations.append(f"undeclared tool used: {name}")
        if name in {"Read", "Write", "Edit"}:
            if not isinstance(path_value, str) or not path_value:
                violations.append(f"{name} omitted file path")
            else:
                supplied = Path(path_value)
                resolved = (supplied if supplied.is_absolute() else workspace / supplied).resolve()
                record["resolved_path"] = str(resolved)
                if not _path_within(resolved, workspace):
                    violations.append(f"{name} accessed outside isolated workspace: {resolved}")
                elif resolved.relative_to(workspace).as_posix() not in PUBLIC_FILES:
                    violations.append(f"{name} accessed undeclared workspace file: {resolved.name}")
                elif name in {"Write", "Edit"} and resolved.name not in WRITEABLE_FILES:
                    violations.append(f"{name} modified read-only public input: {resolved.name}")
        records.append(record)
    return {"valid": not violations, "tool_uses": records, "violations": violations}


def _parse_stream(stdout: str) -> list[dict[str, Any]]:
    events = []
    malformed = []
    for number, line in enumerate(stdout.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            malformed.append(f"line {number}: {exc}")
            continue
        if not isinstance(event, dict):
            malformed.append(f"line {number}: event is not an object")
            continue
        events.append(event)
    if malformed:
        raise RuntimeError("Claude Code returned malformed stream-json: " + "; ".join(malformed[:3]))
    if not any(event.get("type") == "result" for event in events):
        raise RuntimeError("Claude Code stream is missing its terminal result event")
    return events


@lru_cache(maxsize=8)
def _cli_version(executable: str) -> str:
    completed = run_captured([executable, "--version"], timeout=30)
    if completed.returncode != 0:
        raise RuntimeError(f"{executable} --version failed: {completed.stderr.strip()}")
    return completed.stdout.strip()


class ClaudeCodeCLI:
    """Non-interactive Claude Code adapter with a single audited model family."""

    def __init__(self, settings: dict[str, Any], provider: dict[str, Any]):
        self.executable = str(settings.get("executable", "claude"))
        self.requested_model = str(settings["model_selector"])
        self.expected_model = re.compile(str(settings["expected_resolved_model_regex"]))
        self.timeout_seconds = int(settings.get("timeout_seconds", 900))
        self.max_turns = int(settings.get("max_turns_per_candidate", 8))
        self.effort = str(settings.get("effort", "high"))
        self.safe_mode = bool(settings.get("safe_mode", True))
        self.tools = tuple(map(str, settings.get("tools", ["Read", "Write", "Edit"])))
        self.provider_name = str(provider["name"])
        self.base_url = str(provider["base_url"]).rstrip("/")
        self.api_key_env = str(provider["api_key_env"])

    def preflight(self) -> str:
        executable = shutil.which(self.executable)
        if executable is None:
            raise FileNotFoundError(f"Claude Code executable not found: {self.executable}")
        if not self.safe_mode:
            raise ValueError("baseline4 requires safe_mode=true to disable local instructions and plugins")
        if self.tools != ("Read", "Write", "Edit"):
            raise ValueError("baseline4 tool surface must be exactly Read, Write, Edit")
        if not 1 <= self.max_turns <= 32:
            raise ValueError("max_turns_per_candidate must be between 1 and 32")
        if self.requested_model != "sonnet" and not self.expected_model.fullmatch(self.requested_model):
            raise ValueError("model_selector must be the Sonnet alias or an explicit Sonnet 5 identifier")
        if self.provider_name != "teamorouter":
            raise ValueError("baseline4 provider must be exactly teamorouter")
        if self.base_url != "https://api.teamorouter.com":
            raise ValueError("baseline4 must use the audited Teamorouter Anthropic endpoint")
        if self.api_key_env != "TEAMOROUTER_API_KEY":
            raise ValueError("baseline4 must obtain its credential from TEAMOROUTER_API_KEY")
        if not os.environ.get(self.api_key_env):
            raise RuntimeError(f"{self.api_key_env} is required; no provider fallback is allowed")
        return _cli_version(executable)

    def invoke(
        self,
        workspace: Path,
        prompt: str,
        call_dir: Path,
        session_id: str,
    ) -> ClaudeCallResult:
        call_dir.mkdir(parents=True, exist_ok=False)
        command = [
            self.executable,
            "--print",
            "--output-format",
            "stream-json",
            "--verbose",
            "--safe-mode",
            "--no-session-persistence",
            "--no-chrome",
            "--disable-slash-commands",
            "--prompt-suggestions",
            "false",
            "--model",
            self.requested_model,
            "--effort",
            self.effort,
            "--max-turns",
            str(self.max_turns),
            "--tools",
            ",".join(self.tools),
            "--allowedTools",
            ",".join(self.tools),
            "--disallowedTools",
            "Bash,WebFetch,WebSearch,Task,Agent,NotebookEdit,mcp__*",
            "--permission-mode",
            "acceptEdits",
            "--strict-mcp-config",
            "--session-id",
            session_id,
        ]
        command.append(prompt)
        _write_json(call_dir / "request.json", {
            "baseline_id": BASELINE_SPEC["id"],
            "provider": self.provider_name,
            "base_url": self.base_url,
            "requested_model": self.requested_model,
            "session_id": session_id,
            "resume": False,
            "no_session_persistence": True,
            "safe_mode": True,
            "strict_mcp_config": True,
            "fresh_claude_config_dir": True,
            "user_settings_loaded": False,
            "prompt": prompt,
            "command_options": command[1:-1],
            "workspace_public_files": sorted(PUBLIC_FILES),
            "workspace_inputs_sha256": {
                name: _sha256(workspace / name) for name in sorted(PUBLIC_FILES)
            },
        })

        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="baseline4_claude_config_") as config_dir:
            environment = os.environ.copy()
            for name in (
                "ANTHROPIC_API_KEY",
                "ANTHROPIC_AUTH_TOKEN",
                "ANTHROPIC_BASE_URL",
                "ANTHROPIC_MODEL",
                "ANTHROPIC_SMALL_FAST_MODEL",
                "CLAUDE_CONFIG_DIR",
            ):
                environment.pop(name, None)
            environment.update({
                "ANTHROPIC_BASE_URL": self.base_url,
                "ANTHROPIC_AUTH_TOKEN": os.environ[self.api_key_env],
                "CLAUDE_CONFIG_DIR": config_dir,
            })
            try:
                completed = run_captured(
                    command,
                    cwd=workspace,
                    env=environment,
                    timeout=self.timeout_seconds,
                )
            except subprocess.TimeoutExpired as exc:
                (call_dir / "claude.stdout.jsonl").write_text(str(exc.output or ""), encoding="utf-8")
                (call_dir / "claude.stderr").write_text(str(exc.stderr or ""), encoding="utf-8")
                raise RuntimeError(f"Claude Code timed out after {self.timeout_seconds}s") from exc
        duration_ms = int((time.monotonic() - started) * 1000)
        (call_dir / "claude.stdout.jsonl").write_text(completed.stdout, encoding="utf-8")
        (call_dir / "claude.stderr").write_text(completed.stderr, encoding="utf-8")
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout)[-3000:]
            raise RuntimeError(f"Claude Code exited with {completed.returncode}: {detail}")

        events = _parse_stream(completed.stdout)
        result_events = [event for event in events if event.get("type") == "result"]
        terminal = result_events[-1]
        if terminal.get("is_error") is True or terminal.get("subtype") not in {None, "success"}:
            raise RuntimeError(f"Claude Code result is an error: {terminal.get('result')}")
        models = _models_from_events(events)
        if not models:
            raise RuntimeError("Claude Code did not report a resolved model")
        unexpected = [model for model in models if not self.expected_model.fullmatch(model)]
        if unexpected:
            raise RuntimeError(
                "single-model protocol violation; expected Sonnet 5, observed " + ", ".join(unexpected)
            )
        access_audit = _audit_tool_access(events, workspace)
        _write_json(call_dir / "access_audit.json", access_audit)
        if not access_audit["valid"]:
            raise RuntimeError("Claude Code workspace isolation violation: " + "; ".join(access_audit["violations"]))
        usage = _usage_from_events(events)
        _write_json(call_dir / "call_record.json", {
            "session_id": session_id,
            "requested_model": self.requested_model,
            "resolved_models": list(models),
            "usage": usage,
            "duration_ms": duration_ms,
            "agent_turns": int(terminal.get("num_turns", 0)),
            "total_cost_usd": terminal.get("total_cost_usd"),
            "access_audit_valid": True,
        })
        return ClaudeCallResult(
            session_id=str(terminal.get("session_id") or session_id),
            result_text=str(terminal.get("result") or ""),
            resolved_models=models,
            usage=usage,
            duration_ms=duration_ms,
            agent_turns=int(terminal.get("num_turns", 0)),
            total_cost_usd=(
                float(terminal["total_cost_usd"])
                if isinstance(terminal.get("total_cost_usd"), (int, float))
                else None
            ),
            access_audit_valid=True,
        )


class ClaudeCodeBaselineHarness:
    def __init__(
        self,
        config_path: Path,
        task_dir: Path,
        output: Path,
        *,
        agent: ClaudeAgent | None = None,
        validators: list[Any] | None = None,
    ):
        self.config_path = config_path.resolve()
        self.config = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.config["_config_dir"] = str(self.config_path.parent)
        self.task: TaskPackage = load_task(task_dir)
        self.output = output.resolve()
        self.experiment = dict(self.config["experiment"])
        self.max_candidates = int(self.experiment["max_candidates"])
        self.required_visible = tuple(self.experiment["required_visible_gates"])
        self.sealed_name = str(self.experiment["sealed_gate"])
        self.agent = (
            agent
            if agent is not None
            else ClaudeCodeCLI(self.config["claude_code"], self.config["provider"])
        )
        validator_config_path = (self.config_path.parent / self.config["validator_config"]).resolve()
        self.validator_config_path = validator_config_path
        shared_config = json.loads(validator_config_path.read_text(encoding="utf-8"))
        _validate_config(shared_config)
        self.validators = validators if validators is not None else validators_from_config(
            shared_config["validators"], validator_config_path.parent
        )
        self.attempts: list[AttemptOutcome] = []
        self.sealed_attempts: list[tuple[int, GateResult]] = []
        self.calls: list[ClaudeCallResult] = []
        self.resolved_models: set[str] = set()
        self.session_ids: list[str] = []
        self.cli_version = ""

    def preflight(self) -> None:
        if self.max_candidates != 10:
            raise ValueError("baseline4 comparison requires max_candidates=10")
        if self.experiment.get("candidate_policy") != "independent_pass_at_10":
            raise ValueError("baseline4 requires independent Pass@10 candidates")
        if self.experiment.get("validator_feedback_to_model") is not False:
            raise ValueError("baseline4 must not expose validator feedback to Claude Code")
        if self.required_visible != ("compiler", "plcverif") or self.sealed_name != "openplc":
            raise ValueError("baseline4 requires MatIEC -> PLCverif -> OpenPLC")
        if [item.name for item in self.validators] != ["compiler", "plcverif", "openplc"]:
            raise ValueError("validator order differs from the frozen common judging protocol")
        self.cli_version = self.agent.preflight()
        for validator in self.validators:
            validator.preflight(self.task)

    def _prepare_workspace(self, root: Path, number: int) -> Path:
        workspace = root / f"workspace_{number:02d}"
        workspace.mkdir()
        (workspace / "requirement.md").write_text(self.task.requirement_text, encoding="utf-8")
        (workspace / "interface.st").write_text(self.task.interface_text, encoding="utf-8")
        (workspace / "candidate.st").write_text(self.task.interface_text, encoding="utf-8")
        return workspace

    def _prompt(self) -> str:
        return (
            "Read requirement.md and interface.st, reason about scan-cycle state and priorities, then "
            "replace candidate.st with one complete IEC 61131-3 Structured Text FUNCTION_BLOCK. "
            "This is an independent generation: no earlier candidate or validator feedback is available.\n\n"
            "Experimental restrictions:\n"
            "- Only read requirement.md, interface.st, and candidate.st in the current directory.\n"
            "- Only candidate.st may be modified. Do not create or modify any other file.\n"
            "- Do not search the web, invoke shells, validators, MCP, plugins, subagents, skills, or external tools.\n"
            "- Preserve the exact FUNCTION_BLOCK name and complete VAR_INPUT/VAR_OUTPUT declarations.\n"
            "- Use IEC block comments (* ... *) only; do not use // comments or Markdown fences.\n"
            "- candidate.st must contain the full compilable program, not a patch or explanation.\n"
            "After writing candidate.st, briefly state that the candidate is ready."
        )

    def _run_visible(self, candidate: Path, attempt_dir: Path) -> list[GateResult]:
        results = []
        blocked = False
        for validator in self.validators:
            if validator.sealed:
                continue
            if blocked:
                results.append(GateResult(validator.name, "skipped", "blocked by an earlier mandatory gate"))
                continue
            result = validator.run(self.task, candidate, attempt_dir)
            results.append(result)
            if validator.blocking and result.status in {"fail", "inconclusive"}:
                blocked = True
        return results

    def _visible_passed(self, gates: list[GateResult]) -> bool:
        statuses = {gate.name: gate.status for gate in gates}
        return all(statuses.get(name) == "pass" for name in self.required_visible)

    def _finish(
        self, ledger: EvidenceLedger, status: str, sealed: GateResult | None = None
    ) -> dict[str, Any]:
        usage = _sum_usage([item.usage for item in self.calls])
        result = {
            "schema_version": "1.0",
            "task_id": self.task.task_id,
            "baseline_id": BASELINE_SPEC["id"],
            "label": BASELINE_SPEC["label"],
            "implementation_status": BASELINE_SPEC["implementation_status"],
            "upstream_url": BASELINE_SPEC["upstream_url"],
            "status": status,
            "success": status == "verified_success",
            "candidate_budget": self.max_candidates,
            "candidates_used": len(self.attempts),
            "model_calls_used": len(self.calls),
            "agent_turns_used": sum(item.agent_turns for item in self.calls),
            "auxiliary_model_calls": 0,
            "winning_attempt": self.attempts[-1].number if status == "verified_success" else None,
            "requested_model": self.agent.requested_model,
            "model_provider": getattr(self.agent, "provider_name", "test-double"),
            "model_constraint": "Claude Sonnet 5 only; no fallback model",
            "resolved_models": sorted(self.resolved_models),
            "claude_code_version": self.cli_version,
            "session_ids": self.session_ids,
            "candidate_policy": "independent_pass_at_10",
            "validator_feedback_to_model": False,
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
            raise FileExistsError(f"refusing to overwrite baseline4 run {self.output}")
        self.output.mkdir(parents=True)
        (self.output / "attempts").mkdir()
        (self.output / "calls").mkdir()
        ledger = EvidenceLedger(self.output / "ledger.jsonl")
        ledger.append("run_started", {
            "task_id": self.task.task_id,
            "baseline_id": BASELINE_SPEC["id"],
            "candidate_budget": self.max_candidates,
            "requested_model": self.agent.requested_model,
            "model_provider": getattr(self.agent, "provider_name", "test-double"),
            "model_constraint": "Sonnet 5 only; runtime model audit required",
            "claude_code_version": self.cli_version,
            "safe_mode": True,
            "allowed_tools": ["Read", "Write", "Edit"],
            "candidate_policy": "at most 10 independent candidates; stop on first full pass",
            "validator_feedback_to_model": False,
            "verification_profile": "per candidate: MatIEC -> PLCverif -> OpenPLC",
            "public_workspace_files": sorted(PUBLIC_FILES),
            "excluded_files": ["reference.st", "properties.json", "openplc_tests.json"],
            "session_policy": "fresh non-persistent Claude Code session and workspace per candidate",
        })

        by_name = {item.name: item for item in self.validators}
        with tempfile.TemporaryDirectory(prefix="plc_baseline4_", dir="/tmp") as temporary:
            for number in range(1, self.max_candidates + 1):
                workspace = self._prepare_workspace(Path(temporary), number)
                call_dir = self.output / "calls" / f"call_{number:02d}"
                attempt_dir = self.output / "attempts" / f"attempt_{number:02d}"
                attempt_dir.mkdir()
                session_id = str(uuid.uuid4())
                try:
                    call = self.agent.invoke(
                        workspace,
                        self._prompt(),
                        call_dir,
                        session_id,
                    )
                except Exception as exc:
                    ledger.append("model_call_failed", {
                        "attempt_slot": number,
                        "error": f"{type(exc).__name__}: {exc}",
                    })
                    return self._finish(ledger, "infrastructure_error")
                if call.session_id != session_id:
                    ledger.append("session_protocol_failed", {
                        "attempt_slot": number,
                        "expected_session_id": session_id,
                        "observed_session_id": call.session_id,
                    })
                    return self._finish(ledger, "infrastructure_error")
                self.session_ids.append(session_id)
                self.calls.append(call)
                self.resolved_models.update(call.resolved_models)

                workspace_candidate = workspace / "candidate.st"
                if not workspace_candidate.is_file() or not workspace_candidate.read_text(encoding="utf-8").strip():
                    ledger.append("candidate_artifact_missing", {"attempt_slot": number})
                    return self._finish(ledger, "infrastructure_error")
                candidate = attempt_dir / "candidate.st"
                shutil.copyfile(workspace_candidate, candidate)
                gates = self._run_visible(candidate, attempt_dir)
                parsed = ParsedCandidate(
                    program=candidate.read_text(encoding="utf-8"),
                    hypothesis="Claude Code workspace edit",
                    target_requirement_ids=tuple(sorted(self.task.requirement_ids)),
                    format_valid=True,
                    extraction_mode="claude_code_file_artifact",
                )
                outcome = AttemptOutcome(
                    number=number,
                    candidate_path=str(candidate),
                    candidate_sha256=_sha256(candidate),
                    candidate=parsed,
                    gates=gates,
                    repair_mode="CLAUDE_CODE_INDEPENDENT_SAMPLE",
                    anchor_attempt=None,
                    usage=call.usage,
                    resolved_model=",".join(call.resolved_models),
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
                    continue
                return self._finish(ledger, "sealed_inconclusive", sealed)
        return self._finish(ledger, "candidate_budget_exhausted")


def _load_qualified_tasks(path: Path) -> set[str]:
    qualification = json.loads(path.read_text(encoding="utf-8"))
    if qualification.get("status") == "pass":
        return {
            str(item["task_id"])
            for item in qualification.get("tasks", [])
            if item.get("qualified") is True
        }
    if qualification.get("success") is True:
        return {
            str(item["task_id"])
            for item in qualification.get("tasks", [])
            if item.get("status") == "pass"
        }
    raise ValueError("a completed passing qualification or calibration summary is required")


def _validate_baseline4_config(config: dict[str, Any], config_path: Path) -> Path:
    required = {"provider", "claude_code", "experiment", "validator_config"}
    if not required <= set(config):
        raise ValueError(f"baseline4 config is missing: {sorted(required - set(config))}")
    validator_path = (config_path.parent / str(config["validator_config"])).resolve()
    shared = json.loads(validator_path.read_text(encoding="utf-8"))
    _validate_config(shared)
    experiment = config["experiment"]
    comparison = {
        "experiment": experiment,
        "validators": shared["validators"],
    }
    _validate_config(comparison)
    ClaudeCodeCLI(config["claude_code"], config["provider"]).preflight()
    return validator_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run baseline4: Claude Code with Sonnet 5 only")
    parser.add_argument(
        "--config",
        type=Path,
        default=OUR_METHOD_ROOT / "configs/claude_code_sonnet5_external_baseline.json",
    )
    parser.add_argument("--dataset-root", required=True, type=Path)
    parser.add_argument("--qualification", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--task-id", action="append", default=[])
    args = parser.parse_args(argv)

    config_path = args.config.resolve()
    dataset_root = args.dataset_root.resolve()
    qualification_path = args.qualification.resolve()
    output = args.output.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    validator_path = _validate_baseline4_config(config, config_path)
    qualified = _load_qualified_tasks(qualification_path)
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
    executable = shutil.which(str(config["claude_code"].get("executable", "claude")))
    if executable is None:
        raise FileNotFoundError("Claude Code executable was not found")
    run_spec = {
        "schema_version": "1.0",
        **BASELINE_SPEC,
        "config_sha256": _sha256(config_path),
        "validator_config_sha256": _sha256(validator_path),
        "dataset_tree_sha256": _tree_sha256(dataset_root),
        "qualification_sha256": _sha256(qualification_path),
        "adapter_sha256": _sha256(Path(__file__).resolve()),
        "claude_code_version": _cli_version(executable),
        "requested_model": config["claude_code"]["model_selector"],
        "model_provider": config["provider"]["name"],
        "provider_base_url": config["provider"]["base_url"],
        "expected_resolved_model_regex": config["claude_code"]["expected_resolved_model_regex"],
        "task_ids": [path.name for path in task_dirs],
    }
    run_spec_path = output / "run_spec.json"
    if run_spec_path.is_file():
        if json.loads(run_spec_path.read_text(encoding="utf-8")) != run_spec:
            raise RuntimeError("resume refused: baseline4 run specification changed")
    else:
        if any(output.iterdir()):
            raise FileExistsError(f"refusing unbound non-empty output: {output}")
        _write_json(run_spec_path, run_spec)

    expected_model = re.compile(str(config["claude_code"]["expected_resolved_model_regex"]))

    def run_task(task_dir: Path) -> dict[str, Any]:
        run_dir = output / task_dir.name
        result_path = run_dir / "result.json"
        if result_path.is_file():
            result = json.loads(result_path.read_text(encoding="utf-8"))
            resumed = True
        else:
            if run_dir.exists():
                raise RuntimeError("incomplete run exists; refusing potentially duplicate Claude calls")
            result = ClaudeCodeBaselineHarness(config_path, task_dir, run_dir).run()
            resumed = False
        if result.get("baseline_id") != BASELINE_SPEC["id"] or result.get("task_id") != task_dir.name:
            raise RuntimeError("persisted result does not match task or baseline4")
        entries = EvidenceLedger.verify(run_dir / "ledger.jsonl")
        requests = sorted(run_dir.glob("calls/call_*/request.json"))
        audits = sorted(run_dir.glob("calls/call_*/access_audit.json"))
        request_payloads = [json.loads(path.read_text(encoding="utf-8")) for path in requests]
        reference = (task_dir / "reference.st").read_text(encoding="utf-8").strip()
        prompt_isolation = all(
            not reference or reference not in path.read_text(encoding="utf-8")
            for path in requests
        )
        models = result.get("resolved_models", [])
        models_ok = bool(models) and all(expected_model.fullmatch(str(model)) for model in models)
        request_sessions = [str(item.get("session_id", "")) for item in request_payloads]
        prompts = [str(item.get("prompt", "")) for item in request_payloads]
        interface_sha256 = _sha256(task_dir / "interface.st")
        independence_ok = (
            result.get("candidate_policy") == "independent_pass_at_10"
            and result.get("validator_feedback_to_model") is False
            and int(result.get("model_calls_used", 0)) <= 10
            and int(result.get("candidates_used", 0)) <= 10
            and len(request_sessions) == len(set(request_sessions))
            and request_sessions == result.get("session_ids", [])
            and len(set(prompts)) <= 1
            and all(item.get("resume") is False for item in request_payloads)
            and all(item.get("no_session_persistence") is True for item in request_payloads)
            and all(item.get("safe_mode") is True for item in request_payloads)
            and all(item.get("strict_mcp_config") is True for item in request_payloads)
            and all(item.get("fresh_claude_config_dir") is True for item in request_payloads)
            and all(item.get("user_settings_loaded") is False for item in request_payloads)
            and all(item.get("provider") == "teamorouter" for item in request_payloads)
            and all(
                item.get("base_url") == "https://api.teamorouter.com"
                for item in request_payloads
            )
            and all(item.get("workspace_public_files") == sorted(PUBLIC_FILES) for item in request_payloads)
            and all(
                item.get("workspace_inputs_sha256", {}).get("candidate.st") == interface_sha256
                for item in request_payloads
            )
        )
        return {
            "task_id": task_dir.name,
            "status": result["status"],
            "success": bool(result["success"]),
            "candidates_used": int(result["candidates_used"]),
            "model_calls_used": int(result["model_calls_used"]),
            "agent_turns_used": int(result.get("agent_turns_used", 0)),
            "winning_attempt": result.get("winning_attempt"),
            "usage_total": result.get("usage_total", {}),
            "ledger_valid": bool(entries),
            "request_count_valid": len(requests) == int(result["model_calls_used"]),
            "access_audit_valid": len(audits) == len(requests) and all(
                json.loads(path.read_text(encoding="utf-8")).get("valid") is True for path in audits
            ),
            "prompt_isolation_valid": prompt_isolation,
            "independence_audit_valid": independence_ok,
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
                    "task_id": task_id,
                    "status": "batch_exception",
                    "success": False,
                    "error": f"{type(exc).__name__}: {exc}",
                    "ledger_valid": False,
                    "request_count_valid": False,
                    "access_audit_valid": False,
                    "prompt_isolation_valid": False,
                    "independence_audit_valid": False,
                    "resolved_model_valid": False,
                }
            records.append(record)
            print(json.dumps({
                "task_id": task_id,
                "status": record["status"],
                "candidates_used": record.get("candidates_used"),
                "model_calls_used": record.get("model_calls_used"),
            }, ensure_ascii=False), flush=True)
            _write_json(output / "progress.json", sorted(records, key=lambda item: item["task_id"]))

    records.sort(key=lambda item: item["task_id"])
    protocol_ok = all(
        item.get("ledger_valid")
        and item.get("request_count_valid")
        and item.get("access_audit_valid")
        and item.get("prompt_isolation_valid")
        and item.get("independence_audit_valid")
        and item.get("resolved_model_valid")
        for item in records
    )
    summary = {
        **run_spec,
        "task_count": len(records),
        "success_count": sum(item.get("success", False) for item in records),
        "total_candidates_used": sum(int(item.get("candidates_used", 0)) for item in records),
        "total_model_calls_used": sum(int(item.get("model_calls_used", 0)) for item in records),
        "total_agent_turns_used": sum(int(item.get("agent_turns_used", 0)) for item in records),
        "usage_total": _sum_usage([item.get("usage_total", {}) for item in records]),
        "protocol_ok": protocol_ok,
        "runs": records,
    }
    _write_json(output / "baseline_summary.json", summary)
    print(json.dumps({
        "baseline": BASELINE_SPEC["label"],
        "task_count": len(records),
        "success_count": summary["success_count"],
        "protocol_ok": protocol_ok,
    }, ensure_ascii=False))
    return 0 if protocol_ok and not any(item["status"] == "batch_exception" for item in records) else 2


if __name__ == "__main__":
    raise SystemExit(main())

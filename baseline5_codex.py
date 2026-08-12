#!/usr/bin/env python3
"""Baseline 5: official Codex CLI restricted to GPT-5.6 Luna.

Each candidate is produced by a fresh, isolated ``codex exec`` session and a
workspace initialized from the same public requirement and interface.  The
outer harness owns the frozen MatIEC -> PLCverif -> OpenPLC judges, but no prior
candidate, diagnostic, or verdict is returned to any later opportunity.  Each
task therefore implements independent Pass@10 with early stopping on a full pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
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
    "id": "baseline5_codex_gpt_5_6_luna",
    "label": "Codex-GPT-5.6-Luna",
    "implementation_status": "official-cli-isolated-common-judge-adapter",
    "upstream_url": "https://developers.openai.com/codex/non-interactive-mode",
}
EXACT_MODEL = "gpt-5.6-luna"
PUBLIC_FILES = {"requirement.md", "interface.st", "candidate.st"}
READ_ONLY_FILES = {"requirement.md", "interface.st"}
FORBIDDEN_ITEM_TYPES = {
    "mcp_tool_call",
    "mcpToolCall",
    "dynamic_tool_call",
    "dynamicToolCall",
    "web_search",
    "webSearch",
    "image_generation",
    "imageGeneration",
}
FORBIDDEN_COMMANDS = re.compile(
    r"(?i)(?:^|[;&|]\s*|\b(?:bash|sh)\s+-[a-z]*c\s+['\"]?)"
    r"(?:curl|wget|ssh|scp|rsync|git|nc|ncat|telnet|env|printenv|codex|claude)\b"
)
ABSOLUTE_PATH = re.compile(
    r"(?<![A-Za-z0-9_.-])/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+"
)


@dataclass(frozen=True)
class CodexCallResult:
    session_id: str
    result_text: str
    resolved_models: tuple[str, ...]
    usage: dict[str, int | float]
    duration_ms: int
    agent_turns: int
    agent_items: int
    estimated_cost_usd: float
    access_audit_valid: bool
    instruction_isolation_valid: bool


class CodexAgent(Protocol):
    requested_model: str

    def preflight(self) -> dict[str, str]: ...

    def invoke(self, workspace: Path, prompt: str, call_dir: Path) -> CodexCallResult: ...


def _parse_jsonl(text: str, *, source: str, require_terminal: bool = False) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    malformed: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
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
        raise RuntimeError(f"{source} contains malformed JSONL: " + "; ".join(malformed[:3]))
    if require_terminal and not any(
        event.get("type") in {"turn.completed", "turn.failed"} for event in events
    ):
        raise RuntimeError(f"{source} is missing a terminal turn event")
    return events


def _usage_from_events(events: list[dict[str, Any]]) -> dict[str, int | float]:
    usage: dict[str, int | float] = {}
    for event in events:
        if event.get("type") != "turn.completed" or not isinstance(event.get("usage"), dict):
            continue
        for key, value in event["usage"].items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                usage[key] = usage.get(key, 0) + value
    return usage


def _estimate_cost(usage: dict[str, int | float], pricing: dict[str, Any]) -> float:
    input_tokens = float(usage.get("input_tokens", 0))
    cached_tokens = min(input_tokens, float(usage.get("cached_input_tokens", 0)))
    output_tokens = float(usage.get("output_tokens", 0))
    uncached_tokens = max(0.0, input_tokens - cached_tokens)
    cost = (
        uncached_tokens * float(pricing["input_per_million"])
        + cached_tokens * float(pricing["cached_input_per_million"])
        + output_tokens * float(pricing["output_per_million"])
    ) / 1_000_000
    return round(cost, 10)


def _workspace_hashes(workspace: Path) -> dict[str, str]:
    return {
        path.relative_to(workspace).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(workspace.rglob("*"))
        if path.is_file()
    }


def _audit_cli_events(
    events: list[dict[str, Any]], workspace: Path, before: dict[str, str], after: dict[str, str]
) -> dict[str, Any]:
    """Audit tool kinds, shell paths, and the observable workspace delta."""
    violations: list[str] = []
    commands: list[str] = []
    file_changes: list[dict[str, str]] = []
    item_types: list[str] = []
    for event in events:
        item = event.get("item")
        if not isinstance(item, dict):
            continue
        item_type = str(item.get("type", ""))
        if item_type:
            item_types.append(item_type)
        if item_type in FORBIDDEN_ITEM_TYPES:
            violations.append(f"forbidden Codex item type: {item_type}")
        if item_type == "file_change":
            changes = item.get("changes") if isinstance(item.get("changes"), list) else []
            for change in changes:
                if not isinstance(change, dict) or not isinstance(change.get("path"), str):
                    violations.append("file_change item omitted its path")
                    continue
                supplied = Path(change["path"])
                resolved = (supplied if supplied.is_absolute() else workspace / supplied).resolve()
                file_changes.append({"path": str(resolved), "kind": str(change.get("kind", ""))})
                try:
                    relative = resolved.relative_to(workspace.resolve()).as_posix()
                except ValueError:
                    violations.append(f"file_change escaped isolated workspace: {resolved}")
                    continue
                if relative != "candidate.st":
                    violations.append(f"file_change modified undeclared artifact: {relative}")
        if item_type != "command_execution":
            continue
        command = str(item.get("command", ""))
        commands.append(command)
        if FORBIDDEN_COMMANDS.search(command):
            violations.append(f"network or VCS command is forbidden: {command[:240]}")
        if re.search(r"(?:^|[\s'\"])[.][.](?:/|[\s'\"]|$)", command):
            violations.append(f"parent-directory traversal in command: {command[:240]}")
        if re.search(r"(?:^|[\s'\"])/(?:[\s'\";|&<>]|$)", command):
            violations.append(f"filesystem-root access in command: {command[:240]}")
        if "$" in command or "`" in command or re.search(r"(?:^|\s)~(?:/|\s|$)", command):
            violations.append(f"environment or home expansion in command: {command[:240]}")
        for match in ABSOLUTE_PATH.finditer(command):
            candidate = Path(match.group(0)).resolve()
            if any(
                candidate == allowed or allowed in candidate.parents
                for allowed in (Path("/bin"), Path("/usr/bin"), Path("/usr/local/bin"))
            ) or candidate == Path("/dev/null"):
                continue
            try:
                candidate.relative_to(workspace.resolve())
            except ValueError:
                violations.append(f"command referenced path outside isolated workspace: {candidate}")

    before_names = set(before)
    after_names = set(after)
    unexpected = sorted(after_names - PUBLIC_FILES)
    missing = sorted(PUBLIC_FILES - after_names)
    if unexpected:
        violations.append(f"undeclared files created: {unexpected}")
    if missing:
        violations.append(f"required public files removed: {missing}")
    for name in sorted(READ_ONLY_FILES & before_names & after_names):
        if before[name] != after[name]:
            violations.append(f"read-only public file modified: {name}")
    return {
        "valid": not violations,
        "commands": commands,
        "file_changes": file_changes,
        "item_types": sorted(set(item_types)),
        "workspace_before": before,
        "workspace_after": after,
        "violations": violations,
    }


def _audit_rollouts(
    codex_home: Path,
    workspace: Path,
    expected_model: str,
    expected_provider: str,
) -> dict[str, Any]:
    models: set[str] = set()
    session_ids: set[str] = set()
    cli_versions: set[str] = set()
    model_providers: set[str] = set()
    base_instruction_hashes: set[str] = set()
    violations: list[str] = []
    files = sorted(codex_home.glob("sessions/**/*.jsonl"))
    for path in files:
        for event in _parse_jsonl(path.read_text(encoding="utf-8"), source=str(path)):
            payload = event.get("payload")
            if not isinstance(payload, dict):
                continue
            if event.get("type") == "session_meta":
                if isinstance(payload.get("id"), str):
                    session_ids.add(payload["id"])
                if isinstance(payload.get("cli_version"), str):
                    cli_versions.add(payload["cli_version"])
                if isinstance(payload.get("model_provider"), str):
                    model_providers.add(payload["model_provider"])
                if isinstance(payload.get("base_instructions"), str):
                    base_instruction_hashes.add(
                        hashlib.sha256(payload["base_instructions"].encode("utf-8")).hexdigest()
                    )
                cwd = payload.get("cwd")
                if isinstance(cwd, str) and Path(cwd).resolve() != workspace.resolve():
                    violations.append(f"session cwd escaped isolated workspace: {cwd}")
            if event.get("type") == "turn_context":
                model = payload.get("model")
                if isinstance(model, str):
                    models.add(model)
                cwd = payload.get("cwd")
                if isinstance(cwd, str) and Path(cwd).resolve() != workspace.resolve():
                    violations.append(f"turn cwd escaped isolated workspace: {cwd}")
            if event.get("type") == "inter_agent_communication_metadata":
                violations.append("Codex spawned or communicated with a subagent")
    if not files:
        violations.append("Codex emitted no rollout file for runtime model audit")
    if not models:
        violations.append("Codex rollout did not report a resolved model")
    unexpected = sorted(model for model in models if model != expected_model)
    if unexpected:
        violations.append("single-model protocol violation: " + ", ".join(unexpected))
    if not model_providers:
        violations.append("Codex rollout did not report a model provider")
    elif model_providers != {expected_provider}:
        violations.append("unexpected model provider(s): " + ", ".join(sorted(model_providers)))
    return {
        "valid": not violations,
        "rollout_file_count": len(files),
        "resolved_models": sorted(models),
        "session_ids": sorted(session_ids),
        "cli_versions": sorted(cli_versions),
        "model_providers": sorted(model_providers),
        "base_instruction_sha256": sorted(base_instruction_hashes),
        "violations": violations,
    }


def _instruction_files_in_ancestry(workspace: Path) -> list[str]:
    names = ("AGENTS.md", "AGENTS.override.md", "CLAUDE.md")
    found: list[str] = []
    for directory in (workspace.resolve(), *workspace.resolve().parents):
        for name in names:
            path = directory / name
            if path.exists():
                found.append(str(path))
    return found


def _terminate(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def _run_isolated(
    command: list[str],
    prompt: str,
    workspace: Path,
    codex_home: Path,
    timeout: int,
    provider_key_env: str,
) -> subprocess.CompletedProcess[str]:
    env: dict[str, str] = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": str(codex_home.parent),
        "CODEX_HOME": str(codex_home),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "LC_ALL": os.environ.get("LC_ALL", "C.UTF-8"),
        "NO_COLOR": "1",
    }
    for name in ("HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY", "NO_PROXY", "SSL_CERT_FILE", "SSL_CERT_DIR"):
        if os.environ.get(name):
            env[name] = os.environ[name]
    if os.environ.get(provider_key_env):
        env[provider_key_env] = os.environ[provider_key_env]
    process = subprocess.Popen(
        command,
        cwd=workspace,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(prompt, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        _terminate(process)
        stdout, stderr = process.communicate()
        raise subprocess.TimeoutExpired(command, timeout, output=stdout, stderr=stderr) from exc
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


@lru_cache(maxsize=4)
def _cli_identity(executable: str) -> dict[str, str]:
    resolved = shutil.which(executable)
    if resolved is None:
        raise FileNotFoundError(f"Codex executable not found: {executable}")
    version = run_captured([resolved, "--version"], timeout=30)
    if version.returncode != 0:
        raise RuntimeError(f"{resolved} --version failed: {version.stderr.strip()}")
    bundled = run_captured([resolved, "debug", "models", "--bundled"], timeout=30)
    if bundled.returncode != 0:
        raise RuntimeError(f"Codex bundled model catalog failed: {bundled.stderr.strip()}")
    try:
        catalog = json.loads(bundled.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Codex bundled model catalog is not JSON") from exc
    catalog_models = {
        str(item.get("slug") or item.get("model") or item.get("id"))
        for item in catalog.get("models", [])
        if isinstance(item, dict)
    }
    if EXACT_MODEL not in catalog_models:
        raise RuntimeError(f"installed Codex CLI does not advertise {EXACT_MODEL}")
    binary = Path(resolved).resolve()
    return {
        "executable": str(binary),
        "version": version.stdout.strip(),
        "executable_sha256": _sha256(binary),
    }


class CodexCLI:
    """One-model Codex CLI adapter with per-call configuration isolation."""

    def __init__(self, settings: dict[str, Any]):
        self.executable = str(settings.get("executable", "codex"))
        self.requested_model = str(settings["model"])
        self.reasoning_effort = str(settings.get("reasoning_effort", "medium"))
        self.timeout_seconds = int(settings.get("timeout_seconds", 900))
        self.pricing = dict(settings["pricing_usd_per_million_tokens"])
        provider = dict(settings["provider"])
        self.provider_id = str(provider["id"])
        self.provider_name = str(provider["name"])
        self.provider_base_url = str(provider["base_url"]).rstrip("/")
        self.provider_key_env = str(provider["api_key_env"])
        self.provider_wire_api = str(provider.get("wire_api", "responses"))
        self.provider_supports_websockets = bool(provider.get("supports_websockets", False))

    def preflight(self) -> dict[str, str]:
        if self.requested_model != EXACT_MODEL:
            raise ValueError(f"baseline5 model must be exactly {EXACT_MODEL}; fallback is forbidden")
        if self.reasoning_effort not in {"none", "low", "medium", "high", "xhigh", "max"}:
            raise ValueError("unsupported GPT-5.6 Luna reasoning effort")
        if self.timeout_seconds < 1:
            raise ValueError("timeout_seconds must be positive")
        if not re.fullmatch(r"[a-z][a-z0-9_-]*", self.provider_id):
            raise ValueError("Codex provider id must be a safe TOML table identifier")
        if not self.provider_base_url.startswith("https://"):
            raise ValueError("Codex provider base_url must use HTTPS")
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", self.provider_key_env):
            raise ValueError("Codex provider api_key_env is invalid")
        if self.provider_wire_api != "responses":
            raise ValueError("Codex custom provider must use the Responses wire API")
        for key in ("input_per_million", "cached_input_per_million", "output_per_million"):
            if float(self.pricing.get(key, -1)) < 0:
                raise ValueError(f"missing or invalid pricing field: {key}")
        return _cli_identity(self.executable)

    def invoke(self, workspace: Path, prompt: str, call_dir: Path) -> CodexCallResult:
        call_dir.mkdir(parents=True, exist_ok=False)
        ancestry = _instruction_files_in_ancestry(workspace)
        if ancestry:
            raise RuntimeError("isolated workspace has ambient instruction files: " + ", ".join(ancestry))
        before = _workspace_hashes(workspace)
        with tempfile.TemporaryDirectory(prefix="baseline5_home_", dir="/tmp") as home_dir:
            isolated_home = Path(home_dir)
            codex_home = isolated_home / ".codex"
            codex_home.mkdir(mode=0o700)
            if not os.environ.get(self.provider_key_env):
                raise RuntimeError(
                    f"Codex provider authentication unavailable: {self.provider_key_env} is unset"
                )

            last_message = call_dir / "last_message.txt"
            command = [
                self.executable,
                "exec",
                "--model",
                self.requested_model,
                "--sandbox",
                "workspace-write",
                "--ignore-user-config",
                "--ignore-rules",
                "--disable",
                "plugins",
                "--disable",
                "remote_plugin",
                "--disable",
                "plugin_sharing",
                "--disable",
                "apps",
                "--disable",
                "multi_agent",
                "--disable",
                "skill_search",
                "--disable",
                "skill_mcp_dependency_install",
                "--disable",
                "browser_use",
                "--disable",
                "browser_use_external",
                "--disable",
                "computer_use",
                "--disable",
                "image_generation",
                "--disable",
                "goals",
                "--disable",
                "hooks",
                "--strict-config",
                "--skip-git-repo-check",
                "--json",
                "--color",
                "never",
                "--cd",
                str(workspace),
                "--output-last-message",
                str(last_message),
                "--config",
                f'model_reasoning_effort="{self.reasoning_effort}"',
                "--config",
                f'model_provider="{self.provider_id}"',
                "--config",
                f'model_providers.{self.provider_id}.name="{self.provider_name}"',
                "--config",
                f'model_providers.{self.provider_id}.base_url="{self.provider_base_url}"',
                "--config",
                f'model_providers.{self.provider_id}.env_key="{self.provider_key_env}"',
                "--config",
                f'model_providers.{self.provider_id}.wire_api="{self.provider_wire_api}"',
                "--config",
                (
                    f"model_providers.{self.provider_id}.supports_websockets="
                    f"{str(self.provider_supports_websockets).lower()}"
                ),
                "-",
            ]
            _write_json(call_dir / "request.json", {
                "baseline_id": BASELINE_SPEC["id"],
                "requested_model": self.requested_model,
                "model_provider": self.provider_id,
                "prompt": prompt,
                "command_options": command[2:-1],
                "public_workspace_files": sorted(PUBLIC_FILES),
                "workspace_inputs_sha256": {
                    name: _sha256(workspace / name) for name in sorted(PUBLIC_FILES)
                },
                "isolation": {
                    "fresh_codex_home": True,
                    "ignore_user_config": True,
                    "ignore_rules": True,
                    "workspace_outside_research_tree": True,
                    "mcp_configured": False,
                    "plugins_configured": False,
                    "skills_installed": False,
                },
            })
            started = time.monotonic()
            try:
                completed = _run_isolated(
                    command,
                    prompt,
                    workspace,
                    codex_home,
                    self.timeout_seconds,
                    self.provider_key_env,
                )
            except subprocess.TimeoutExpired as exc:
                (call_dir / "codex.stdout.jsonl").write_text(str(exc.output or ""), encoding="utf-8")
                (call_dir / "codex.stderr").write_text(str(exc.stderr or ""), encoding="utf-8")
                raise RuntimeError(f"Codex timed out after {self.timeout_seconds}s") from exc
            duration_ms = int((time.monotonic() - started) * 1000)
            (call_dir / "codex.stdout.jsonl").write_text(completed.stdout, encoding="utf-8")
            (call_dir / "codex.stderr").write_text(completed.stderr, encoding="utf-8")
            if completed.returncode != 0:
                detail = (completed.stderr or completed.stdout)[-3000:]
                raise RuntimeError(f"Codex exited with {completed.returncode}: {detail}")
            events = _parse_jsonl(completed.stdout, source="Codex --json", require_terminal=True)
            # Codex emits recoverable ``error`` events while reconnecting an SSE
            # stream.  A later turn.completed is authoritative; only a terminal
            # turn.failed event makes the invocation fail.
            failed = [event for event in events if event.get("type") == "turn.failed"]
            if failed:
                raise RuntimeError(f"Codex reported a failed turn: {failed[-1]}")
            transport_warnings = [
                str(event.get("message", ""))
                for event in events
                if event.get("type") == "error"
            ]
            rollout_audit = _audit_rollouts(
                codex_home,
                workspace,
                self.requested_model,
                self.provider_id,
            )
            _write_json(call_dir / "runtime_audit.json", rollout_audit)
            if not rollout_audit["valid"]:
                raise RuntimeError("Codex runtime audit failed: " + "; ".join(rollout_audit["violations"]))

        after = _workspace_hashes(workspace)
        access_audit = _audit_cli_events(events, workspace, before, after)
        _write_json(call_dir / "access_audit.json", access_audit)
        if not access_audit["valid"]:
            raise RuntimeError("Codex workspace isolation violation: " + "; ".join(access_audit["violations"]))
        usage = _usage_from_events(events)
        cost = _estimate_cost(usage, self.pricing)
        turns = sum(event.get("type") == "turn.completed" for event in events)
        items = sum(event.get("type") == "item.completed" for event in events)
        session_ids = rollout_audit["session_ids"]
        result_text = last_message.read_text(encoding="utf-8") if last_message.is_file() else ""
        _write_json(call_dir / "call_record.json", {
            "session_ids": session_ids,
            "requested_model": self.requested_model,
            "model_provider": self.provider_id,
            "resolved_models": rollout_audit["resolved_models"],
            "transport_warnings": transport_warnings,
            "usage": usage,
            "estimated_cost_usd": cost,
            "duration_ms": duration_ms,
            "agent_turns": turns,
            "agent_items": items,
            "access_audit_valid": True,
            "instruction_isolation_valid": True,
        })
        return CodexCallResult(
            session_id=",".join(session_ids),
            result_text=result_text,
            resolved_models=tuple(rollout_audit["resolved_models"]),
            usage={**usage, "estimated_cost_usd": cost},
            duration_ms=duration_ms,
            agent_turns=turns,
            agent_items=items,
            estimated_cost_usd=cost,
            access_audit_valid=True,
            instruction_isolation_valid=True,
        )


class CodexBaselineHarness:
    def __init__(
        self,
        config_path: Path,
        task_dir: Path,
        output: Path,
        *,
        agent: CodexAgent | None = None,
        validators: list[Any] | None = None,
    ):
        self.config_path = config_path.resolve()
        self.config = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.task: TaskPackage = load_task(task_dir)
        self.output = output.resolve()
        self.experiment = dict(self.config["experiment"])
        self.max_candidates = int(self.experiment["max_candidates"])
        self.required_visible = tuple(self.experiment["required_visible_gates"])
        self.sealed_name = str(self.experiment["sealed_gate"])
        self.agent = agent if agent is not None else CodexCLI(self.config["codex"])
        validator_path = (self.config_path.parent / self.config["validator_config"]).resolve()
        self.validator_config_path = validator_path
        shared = json.loads(validator_path.read_text(encoding="utf-8"))
        _validate_config(shared)
        self.validators = validators if validators is not None else validators_from_config(
            shared["validators"], validator_path.parent
        )
        self.attempts: list[AttemptOutcome] = []
        self.sealed_attempts: list[tuple[int, GateResult]] = []
        self.calls: list[CodexCallResult] = []
        self.resolved_models: set[str] = set()
        self.cli_identity: dict[str, str] = {}

    def preflight(self) -> None:
        if self.max_candidates != 10:
            raise ValueError("baseline5 comparison requires max_candidates=10")
        if self.experiment.get("candidate_policy") != "independent_pass_at_10":
            raise ValueError("baseline5 requires independent Pass@10 candidates")
        if self.experiment.get("validator_feedback_to_model") is not False:
            raise ValueError("baseline5 must not expose validator feedback to Codex")
        if self.required_visible != ("compiler", "plcverif") or self.sealed_name != "openplc":
            raise ValueError("baseline5 requires MatIEC -> PLCverif -> OpenPLC")
        if [item.name for item in self.validators] != ["compiler", "plcverif", "openplc"]:
            raise ValueError("validator order differs from the frozen common judging protocol")
        self.cli_identity = self.agent.preflight()
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
            "Read requirement.md and interface.st, then replace candidate.st with one complete "
            "IEC 61131-3 Structured Text FUNCTION_BLOCK. This is an independent generation: no "
            "earlier candidate or validator feedback is available.\n\n"
            "Experimental restrictions:\n"
            "- Only inspect requirement.md, interface.st, and candidate.st in this workspace.\n"
            "- Only candidate.st may be modified; do not create any other file.\n"
            "- Do not access parent/absolute paths, environment variables, network, web, MCP, plugins, "
            "skills, subagents, git, or external validators.\n"
            "- Preserve the exact FUNCTION_BLOCK name and complete VAR_INPUT/VAR_OUTPUT declarations.\n"
            "- Use IEC block comments (* ... *) only; do not use // comments or Markdown fences.\n"
            "- candidate.st must contain the full compilable program, not a patch or explanation.\n"
            "When candidate.st is ready, return only a brief completion note."
        )

    def _run_visible(self, candidate: Path, attempt_dir: Path) -> list[GateResult]:
        results: list[GateResult] = []
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

    def _finish(self, ledger: EvidenceLedger, status: str, sealed: GateResult | None = None) -> dict[str, Any]:
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
            "agent_items_used": sum(item.agent_items for item in self.calls),
            "auxiliary_model_calls": 0,
            "winning_attempt": self.attempts[-1].number if status == "verified_success" else None,
            "requested_model": self.agent.requested_model,
            "model_provider": getattr(self.agent, "provider_id", "test-double"),
            "model_constraint": f"exactly {EXACT_MODEL}; no aliases and no fallback",
            "resolved_models": sorted(self.resolved_models),
            "codex_cli": self.cli_identity,
            "candidate_policy": "independent_pass_at_10",
            "validator_feedback_to_model": False,
            "usage_total": _sum_usage([item.usage for item in self.calls]),
            "attempts": [item.to_dict() for item in self.attempts],
            "sealed_attempts": [
                {"attempt": number, "result": item.to_dict()} for number, item in self.sealed_attempts
            ],
            "sealed_result": sealed.to_dict() if sealed else None,
        }
        _write_json(self.output / "result.json", result)
        ledger.append("run_finished", {key: value for key, value in result.items() if key != "attempts"})
        return result

    def run(self) -> dict[str, Any]:
        self.preflight()
        if self.output.exists():
            raise FileExistsError(f"refusing to overwrite baseline5 run {self.output}")
        self.output.mkdir(parents=True)
        (self.output / "attempts").mkdir()
        (self.output / "calls").mkdir()
        ledger = EvidenceLedger(self.output / "ledger.jsonl")
        ledger.append("run_started", {
            "task_id": self.task.task_id,
            "baseline_id": BASELINE_SPEC["id"],
            "candidate_budget": self.max_candidates,
            "requested_model": self.agent.requested_model,
            "model_provider": getattr(self.agent, "provider_id", "test-double"),
            "model_constraint": f"exactly {EXACT_MODEL}; runtime rollout audit required",
            "codex_cli": self.cli_identity,
            "candidate_policy": "at most 10 independent candidates; stop on first full pass",
            "validator_feedback_to_model": False,
            "verification_profile": "per candidate: MatIEC -> PLCverif -> OpenPLC",
            "public_workspace_files": sorted(PUBLIC_FILES),
            "excluded_files": ["reference.st", "properties.json", "openplc_tests.json"],
            "session_policy": "fresh isolated Codex session per candidate",
        })
        by_name = {item.name: item for item in self.validators}
        with tempfile.TemporaryDirectory(prefix="plc_baseline5_", dir="/tmp") as temporary:
            for number in range(1, self.max_candidates + 1):
                workspace = self._prepare_workspace(Path(temporary), number)
                attempt_dir = self.output / "attempts" / f"attempt_{number:02d}"
                attempt_dir.mkdir()
                try:
                    call = self.agent.invoke(
                        workspace, self._prompt(), self.output / "calls" / f"call_{number:02d}"
                    )
                except Exception as exc:
                    ledger.append("model_call_failed", {
                        "attempt_slot": number,
                        "error": f"{type(exc).__name__}: {exc}",
                    })
                    return self._finish(ledger, "infrastructure_error")
                self.calls.append(call)
                self.resolved_models.update(call.resolved_models)
                if not call.resolved_models or any(model != EXACT_MODEL for model in call.resolved_models):
                    ledger.append("model_protocol_failed", {
                        "attempt_slot": number,
                        "observed_models": list(call.resolved_models),
                    })
                    return self._finish(ledger, "infrastructure_error")
                workspace_candidate = workspace / "candidate.st"
                if not workspace_candidate.is_file() or not workspace_candidate.read_text(encoding="utf-8").strip():
                    ledger.append("candidate_artifact_missing", {"attempt_slot": number})
                    return self._finish(ledger, "infrastructure_error")
                candidate = attempt_dir / "candidate.st"
                shutil.copyfile(workspace_candidate, candidate)
                gates = self._run_visible(candidate, attempt_dir)
                parsed = ParsedCandidate(
                    program=candidate.read_text(encoding="utf-8"),
                    hypothesis="Codex isolated workspace edit",
                    target_requirement_ids=tuple(sorted(self.task.requirement_ids)),
                    format_valid=True,
                    extraction_mode="codex_file_artifact",
                )
                outcome = AttemptOutcome(
                    number=number,
                    candidate_path=str(candidate),
                    candidate_sha256=_sha256(candidate),
                    candidate=parsed,
                    gates=gates,
                    repair_mode="CODEX_INDEPENDENT_SAMPLE",
                    anchor_attempt=None,
                    usage=call.usage,
                    resolved_model=",".join(call.resolved_models),
                )
                self.attempts.append(outcome)
                _write_json(attempt_dir / "evaluation.json", outcome.to_dict())
                ledger.append("candidate_evaluated", outcome.to_dict())
                fatal = [
                    gate for gate in gates
                    if gate.status == "inconclusive" and not is_resource_bounded_inconclusive(gate)
                ]
                if fatal:
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


def _validate_baseline5_config(config: dict[str, Any], config_path: Path) -> Path:
    required = {"codex", "experiment", "validator_config"}
    if not required <= set(config):
        raise ValueError(f"baseline5 config is missing: {sorted(required - set(config))}")
    if str(config["codex"].get("model")) != EXACT_MODEL:
        raise ValueError(f"baseline5 must request exactly {EXACT_MODEL}")
    validator_path = (config_path.parent / str(config["validator_config"])).resolve()
    shared = json.loads(validator_path.read_text(encoding="utf-8"))
    _validate_config(shared)
    _validate_config({"experiment": config["experiment"], "validators": shared["validators"]})
    return validator_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run baseline5: official Codex CLI with GPT-5.6 Luna only")
    parser.add_argument(
        "--config",
        type=Path,
        default=OUR_METHOD_ROOT / "configs/codex_gpt_5_6_luna_external_baseline.json",
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
    validator_path = _validate_baseline5_config(config, config_path)
    cli = CodexCLI(config["codex"])
    cli_identity = cli.preflight()
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
    run_spec = {
        "schema_version": "1.0",
        **BASELINE_SPEC,
        "config_sha256": _sha256(config_path),
        "validator_config_sha256": _sha256(validator_path),
        "dataset_tree_sha256": _tree_sha256(dataset_root),
        "qualification_sha256": _sha256(qualification_path),
        "adapter_sha256": _sha256(Path(__file__).resolve()),
        "codex_cli": cli_identity,
        "requested_model": EXACT_MODEL,
        "task_ids": [path.name for path in task_dirs],
    }
    run_spec_path = output / "run_spec.json"
    if run_spec_path.is_file():
        if json.loads(run_spec_path.read_text(encoding="utf-8")) != run_spec:
            raise RuntimeError("resume refused: baseline5 run specification changed")
    else:
        if any(output.iterdir()):
            raise FileExistsError(f"refusing unbound non-empty output: {output}")
        _write_json(run_spec_path, run_spec)

    def run_task(task_dir: Path) -> dict[str, Any]:
        run_dir = output / task_dir.name
        result_path = run_dir / "result.json"
        if result_path.is_file():
            result = json.loads(result_path.read_text(encoding="utf-8"))
            resumed = True
        else:
            if run_dir.exists():
                raise RuntimeError("incomplete run exists; refusing potentially duplicate Codex calls")
            result = CodexBaselineHarness(config_path, task_dir, run_dir).run()
            resumed = False
        if result.get("baseline_id") != BASELINE_SPEC["id"] or result.get("task_id") != task_dir.name:
            raise RuntimeError("persisted result does not match task or baseline5")
        entries = EvidenceLedger.verify(run_dir / "ledger.jsonl")
        requests = sorted(run_dir.glob("calls/call_*/request.json"))
        access_audits = sorted(run_dir.glob("calls/call_*/access_audit.json"))
        runtime_audits = sorted(run_dir.glob("calls/call_*/runtime_audit.json"))
        request_payloads = [json.loads(path.read_text(encoding="utf-8")) for path in requests]
        runtime_payloads = [json.loads(path.read_text(encoding="utf-8")) for path in runtime_audits]
        reference = (task_dir / "reference.st").read_text(encoding="utf-8").strip()
        prompt_isolation = all(
            not reference or reference not in path.read_text(encoding="utf-8") for path in requests
        )
        models = result.get("resolved_models", [])
        prompts = [str(item.get("prompt", "")) for item in request_payloads]
        runtime_sessions = [
            str(session_id)
            for item in runtime_payloads
            for session_id in item.get("session_ids", [])
        ]
        interface_sha256 = _sha256(task_dir / "interface.st")
        independence_ok = (
            result.get("candidate_policy") == "independent_pass_at_10"
            and result.get("validator_feedback_to_model") is False
            and int(result.get("model_calls_used", 0)) <= 10
            and int(result.get("candidates_used", 0)) <= 10
            and len(set(prompts)) <= 1
            and len(runtime_sessions) == len(set(runtime_sessions))
            and all(item.get("public_workspace_files") == sorted(PUBLIC_FILES) for item in request_payloads)
            and all(
                item.get("workspace_inputs_sha256", {}).get("candidate.st") == interface_sha256
                for item in request_payloads
            )
            and all(
                item.get("isolation", {}).get("fresh_codex_home") is True
                and item.get("isolation", {}).get("mcp_configured") is False
                and item.get("isolation", {}).get("plugins_configured") is False
                and item.get("isolation", {}).get("skills_installed") is False
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
            "agent_items_used": int(result.get("agent_items_used", 0)),
            "winning_attempt": result.get("winning_attempt"),
            "usage_total": result.get("usage_total", {}),
            "ledger_valid": bool(entries),
            "request_count_valid": len(requests) == int(result["model_calls_used"]),
            "access_audit_valid": len(access_audits) == len(requests) and all(
                json.loads(path.read_text(encoding="utf-8")).get("valid") is True
                for path in access_audits
            ),
            "runtime_audit_valid": len(runtime_audits) == len(requests) and all(
                json.loads(path.read_text(encoding="utf-8")).get("valid") is True
                for path in runtime_audits
            ),
            "prompt_isolation_valid": prompt_isolation,
            "independence_audit_valid": independence_ok,
            "resolved_model_valid": models == [EXACT_MODEL],
            "resumed": resumed,
        }

    records: list[dict[str, Any]] = []
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
                    "runtime_audit_valid": False,
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
        and item.get("runtime_audit_valid")
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
        "total_agent_items_used": sum(int(item.get("agent_items_used", 0)) for item in records),
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

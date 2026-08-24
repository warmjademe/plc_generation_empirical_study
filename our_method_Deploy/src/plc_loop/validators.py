"""Deterministic validation adapters used by visible and sealed gates."""

from __future__ import annotations

import hashlib
import importlib
import json
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

from .dataset import TaskPackage
from .models import Evidence, GateResult
from .process import run_captured


class Validator(Protocol):
    name: str
    blocking: bool
    inconclusive_is_blocking: bool
    sealed: bool

    def preflight(self, task: TaskPackage) -> None: ...

    def run(self, task: TaskPackage, candidate_path: Path, artifact_dir: Path) -> GateResult: ...


def _declarations(text: str, block_name: str) -> list[tuple[str, str]]:
    match = re.search(
        rf"(?ims)^\s*{block_name}\s*$\s*(.*?)^\s*END_VAR\s*$",
        text,
    )
    if not match:
        return []
    declarations = []
    for item in re.finditer(r"(?im)^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*([A-Za-z_][A-Za-z0-9_]*)\s*;", match.group(1)):
        declarations.append((item.group(1).casefold(), item.group(2).upper()))
    return declarations


@dataclass
class InterfaceValidator:
    name: str = "interface"
    blocking: bool = True
    inconclusive_is_blocking: bool = True
    sealed: bool = False

    def preflight(self, task: TaskPackage) -> None:
        if not task.interface_text:
            raise ValueError("empty fixed interface")

    def run(self, task: TaskPackage, candidate_path: Path, artifact_dir: Path) -> GateResult:
        started = time.monotonic()
        source = candidate_path.read_text(encoding="utf-8")
        failures = []
        if "```" in source:
            failures.append("candidate contains Markdown fences")
        starts = re.findall(r"(?im)^\s*FUNCTION_BLOCK\s+([A-Za-z_][A-Za-z0-9_]*)\s*$", source)
        ends = re.findall(r"(?im)^\s*END_FUNCTION_BLOCK\s*$", source)
        if starts != [task.task_id] or len(ends) != 1:
            failures.append(f"expected exactly one FUNCTION_BLOCK {task.task_id}")
        for block in ("VAR_INPUT", "VAR_OUTPUT"):
            expected = _declarations(task.interface_text, block)
            actual = _declarations(source, block)
            if actual != expected:
                failures.append(f"{block} differs: expected {expected}, got {actual}")
        duration = int((time.monotonic() - started) * 1000)
        if failures:
            return GateResult(
                name=self.name,
                status="fail",
                summary="fixed interface or response structure is invalid",
                evidence=tuple(
                    Evidence(
                        tool=self.name,
                        kind="interface_error",
                        summary=item,
                        oracle_status="confirmed_candidate_defect",
                    )
                    for item in failures
                ),
                duration_ms=duration,
                tool_version="built-in-v1",
            )
        return GateResult(
            name=self.name,
            status="pass",
            summary="function-block identity and fixed interface match",
            duration_ms=duration,
            tool_version="built-in-v1",
        )


@dataclass
class DatasetScanValidator:
    name: str
    suite: str
    engine_root: Path
    blocking: bool = True
    inconclusive_is_blocking: bool = True
    sealed: bool = False

    def preflight(self, task: TaskPackage) -> None:
        if self.suite not in {"feedback", "hidden", "stress"}:
            raise ValueError(f"invalid scan suite {self.suite}")
        if not task.suite_path(self.suite).is_file():
            raise FileNotFoundError(task.suite_path(self.suite))
        if not (self.engine_root / "deltaplc/engine.py").is_file():
            raise FileNotFoundError(self.engine_root / "deltaplc/engine.py")

    def _engine(self):
        root = str(self.engine_root)
        if root not in sys.path:
            sys.path.insert(0, root)
        return importlib.import_module("deltaplc.engine")

    def run(self, task: TaskPackage, candidate_path: Path, artifact_dir: Path) -> GateResult:
        started = time.monotonic()
        suite = json.loads(task.suite_path(self.suite).read_text(encoding="utf-8"))
        case_requirements = {case["name"]: tuple(case["requirement_ids"]) for case in suite["cases"]}
        vectors = []
        for case in suite["cases"]:
            steps = []
            for item in case["steps"]:
                converted = {
                    "set": item["inputs"],
                    "dt_ms": suite["scan_period_ms"],
                    "scans": item["repeat"],
                    "expect": item["expect"],
                }
                if item.get("check") == "last_only":
                    converted["check"] = "last_only"
                    steps.append(converted)
                else:
                    # The scan engine checks at the end of a vector step.  Expand
                    # ``check=each`` so every repeated scan is an observation,
                    # matching the dataset schema and the OpenPLC sealed runner.
                    for _ in range(int(item["repeat"])):
                        steps.append({**converted, "scans": 1})
            vectors.append({"name": case["name"], "steps": steps})
        source = candidate_path.read_text(encoding="utf-8")
        try:
            passed, results = self._engine().run_vectors(
                source,
                vectors,
                suite.get("real_absolute_tolerance", 0.001),
            )
        except Exception as exc:
            duration = int((time.monotonic() - started) * 1000)
            return GateResult(
                name=self.name,
                status="fail",
                summary="scan engine rejected or could not execute the candidate",
                evidence=(Evidence(tool=self.name, kind="execution_error", summary=f"{type(exc).__name__}: {exc}"),),
                duration_ms=duration,
                tool_version="deltaplc-subset-engine",
            )
        result_path = artifact_dir / f"{self.name}.json"
        result_path.write_text(json.dumps({"passed": passed, "results": results}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        evidence = []
        passed_requirements: set[str] = set()
        for result in results:
            requirements = case_requirements.get(result["name"], ())
            if result.get("pass"):
                passed_requirements.update(requirements)
                continue
            trace = {
                "case": result["name"],
                "mismatches": result.get("mismatches", [])[:8],
                "error": result.get("error"),
            }
            evidence.append(
                Evidence(
                    tool=self.name,
                    kind="test_failure" if not result.get("error") else "execution_error",
                    summary=f"scan test {result['name']} failed",
                    requirement_ids=tuple(requirements),
                    trace=trace,
                    oracle_status="confirmed_candidate_defect",
                    raw_log_sha256=hashlib.sha256(result_path.read_bytes()).hexdigest(),
                )
            )
        duration = int((time.monotonic() - started) * 1000)
        status = "pass" if passed == len(results) else "fail"
        return GateResult(
            name=self.name,
            status=status,
            summary=f"{passed}/{len(results)} {self.suite} scan tests passed",
            evidence=tuple(evidence),
            passed_requirement_ids=tuple(sorted(passed_requirements)),
            duration_ms=duration,
            tool_version="deltaplc-subset-engine",
        )


@dataclass
class CommandValidator:
    name: str
    command: tuple[str, ...]
    protocol: str = "json"
    timeout_seconds: int = 120
    blocking: bool = True
    inconclusive_is_blocking: bool = True
    sealed: bool = False
    version: str | None = None
    inconclusive_retries: int = 0
    inconclusive_retry_delay_seconds: float = 0.0
    cancel_check: Callable[[], bool] | None = None

    def preflight(self, task: TaskPackage) -> None:
        if not self.command:
            raise ValueError(f"{self.name}: empty command")
        if self.protocol not in {"json", "exit_code"}:
            raise ValueError(f"{self.name}: protocol must be json or exit_code")
        executable = self.command[0]
        if "{" not in executable and shutil.which(executable) is None:
            raise FileNotFoundError(f"{self.name}: executable not found: {executable}")

    def run(self, task: TaskPackage, candidate_path: Path, artifact_dir: Path) -> GateResult:
        replacements = {
            "{candidate}": str(candidate_path),
            "{task_dir}": str(task.root),
            "{feedback_suite}": str(task.suite_path("feedback")),
            "{hidden_suite}": str(task.suite_path("hidden")),
        }
        command = tuple(replacements.get(token, token) for token in self.command)
        started = time.monotonic()
        try:
            completed = run_captured(
                command,
                cwd=artifact_dir,
                timeout=self.timeout_seconds,
                cancel_check=self.cancel_check,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return GateResult(
                name=self.name,
                status="inconclusive",
                summary=f"validator infrastructure error: {type(exc).__name__}: {exc}",
                evidence=(Evidence(tool=self.name, kind="tool_error", summary=str(exc)),),
                duration_ms=int((time.monotonic() - started) * 1000),
                tool_version=self.version,
            )
        stdout_path = artifact_dir / f"{self.name}.stdout"
        stderr_path = artifact_dir / f"{self.name}.stderr"
        stdout_path.write_text(completed.stdout, encoding="utf-8")
        stderr_path.write_text(completed.stderr, encoding="utf-8")
        raw_hash = hashlib.sha256(stdout_path.read_bytes() + stderr_path.read_bytes()).hexdigest()
        duration = int((time.monotonic() - started) * 1000)
        if self.protocol == "exit_code":
            if completed.returncode == 0:
                return GateResult(self.name, "pass", "command exited with status 0", duration_ms=duration, tool_version=self.version)
            summary = (completed.stderr or completed.stdout or f"exit code {completed.returncode}")[:2000]
            return GateResult(
                self.name,
                "fail",
                f"command exited with status {completed.returncode}",
                evidence=(Evidence(self.name, "compile_error", summary, raw_log_sha256=raw_hash),),
                duration_ms=duration,
                tool_version=self.version,
            )
        try:
            document = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            return GateResult(
                self.name,
                "inconclusive",
                f"validator did not return JSON: {exc}",
                evidence=(Evidence(self.name, "tool_error", (completed.stderr or completed.stdout)[:2000], raw_log_sha256=raw_hash),),
                duration_ms=duration,
                tool_version=self.version,
            )
        status = document.get("status")
        if status not in {"pass", "fail", "inconclusive"}:
            status = "inconclusive"
        evidence = tuple(
            Evidence(
                tool=self.name,
                kind=str(item.get("kind", "validator_failure")),
                summary=str(item.get("summary", "unspecified validator evidence")),
                requirement_ids=tuple(item.get("requirement_ids", [])),
                trace=item.get("trace"),
                oracle_status=str(item.get("oracle_status", "unconfirmed")),
                raw_log_sha256=raw_hash,
            )
            for item in document.get("evidence", [])
        )
        return GateResult(
            self.name,
            status,
            str(document.get("summary", f"validator returned {status}")),
            evidence=evidence,
            passed_requirement_ids=tuple(document.get("passed_requirement_ids", [])),
            duration_ms=duration,
            tool_version=self.version or document.get("tool_version"),
        )


def validators_from_config(items: list[dict[str, Any]], base_dir: Path | None = None) -> list[Validator]:
    base_dir = (base_dir or Path.cwd()).resolve()
    validators: list[Validator] = []
    for item in items:
        kind = item["kind"]
        common = {
            "name": item["name"],
            "blocking": bool(item.get("blocking", True)),
            "inconclusive_is_blocking": bool(item.get("inconclusive_is_blocking", True)),
            "sealed": bool(item.get("sealed", False)),
        }
        if kind == "interface":
            validators.append(InterfaceValidator(**common))
        elif kind == "dataset_scan":
            engine_root = Path(item["engine_root"])
            if not engine_root.is_absolute():
                engine_root = base_dir / engine_root
            validators.append(
                DatasetScanValidator(
                    **common,
                    suite=item["suite"],
                    engine_root=engine_root.resolve(),
                )
            )
        elif kind == "command":
            command = tuple(
                str(token).replace("{config_dir}", str(base_dir))
                for token in item["command"]
            )
            validators.append(
                CommandValidator(
                    **common,
                    command=command,
                    protocol=item.get("protocol", "json"),
                    timeout_seconds=int(item.get("timeout_seconds", 120)),
                    version=item.get("version"),
                    inconclusive_retries=int(item.get("inconclusive_retries", 0)),
                    inconclusive_retry_delay_seconds=float(
                        item.get("inconclusive_retry_delay_seconds", 0.0)
                    ),
                )
            )
        else:
            raise ValueError(f"unknown validator kind {kind!r}")
    names = [validator.name for validator in validators]
    if len(names) != len(set(names)):
        raise ValueError("validator names must be unique")
    return validators

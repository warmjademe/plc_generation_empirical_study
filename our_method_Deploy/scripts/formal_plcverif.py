#!/usr/bin/env python3
"""Run frozen, native PLCverif pattern cases with an unmodified backend.

``properties.json`` is the authority for which cases belong to the qualified
PLCverif profile.  This adapter does not ask an LLM to translate requirements and
does not interpret unsupported temporal DSL as a pass.  Each native case is sent
to PLCverif's built-in pattern plug-in and must yield a parseable nuXmv verdict.
"""

from __future__ import annotations

import argparse
import html
import hashlib
import json
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any


SOURCE_ROOT = Path(__file__).resolve().parents[1]
if str(SOURCE_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT / "src"))
from plc_loop.process import run_captured  # noqa: E402


KEYWORDS = {"AND", "OR", "NOT", "XOR", "TRUE", "FALSE"}
CANDIDATE_SOURCE_DEFECT_MARKERS = (
    "not a valid function or function block",
    "unable to generate the cfa due to errors in parsing the source file",
    "error parsing the source file",
    "source code cannot be parsed",
)
TOOL_VERSION = (
    "PLCverif-1.0.0.202410210930+nuXmv-2.0.0+CBMC-6.10.0+"
    "native-pattern-invariant-v1+deterministic-case-scheduler-v2+process-group-timeout-v1+"
    "isolated-eclipse-configuration-v1"
)


def emit(value: dict[str, Any]) -> int:
    print(json.dumps(value, ensure_ascii=False))
    return 0


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_candidate_source_defect(diagnostic: str) -> bool:
    """Separate candidate-source rejection from verifier infrastructure failure."""
    lowered = diagnostic.casefold()
    return any(marker in lowered for marker in CANDIDATE_SOURCE_DEFECT_MARKERS)


def qualify_parameter(expression: str, variable_names: set[str]) -> str:
    """Convert a PLCverif-native parameter from public names to FB instance fields."""
    expression = re.sub(
        r"\(\s*-\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)",
        r"(0.0 - \1)",
        expression,
    )
    if re.search(r"[^A-Za-z0-9_()=<>!\s.+\-*/]", expression):
        raise ValueError("native PLCverif parameter contains an unsupported token")

    def qualify(match: re.Match[str]) -> str:
        token = match.group(0)
        if token.upper() in KEYWORDS:
            return token.upper()
        if token not in variable_names:
            raise ValueError(f"native PLCverif parameter refers to non-interface identifier {token!r}")
        return f"instance.{token}"

    qualified = re.sub(r"[A-Za-z_][A-Za-z0-9_]*", qualify, expression)
    qualified = qualified.replace("->", "-->")
    return re.sub(r"!(?!=)", "NOT ", qualified)


def verdict_file(output_dir: Path, backend: str) -> Path | None:
    patterns = ("*.smv.cex",) if backend == "nusmv" else ("*.cbmc.cex", "*.cex")
    for pattern in patterns:
        matches = sorted(output_dir.glob(pattern))
        if matches:
            return matches[0]
    return None


def cbmc_verdict(output_dir: Path) -> tuple[str, str, str]:
    """Parse PLCverif's CBMC report without confusing unwind with a requirement."""
    reports = sorted(output_dir.glob("*.report.html"))
    if not reports:
        return "inconclusive", "missing_report", "PLCverif produced no CBMC HTML report"
    raw = reports[0].read_text(encoding="utf-8", errors="replace")
    plain = re.sub(r"<br\s*/?>", "\n", raw, flags=re.IGNORECASE)
    plain = re.sub(r"<[^>]+>", "", plain)
    plain = html.unescape(plain)
    business = re.findall(
        r"\[VerificationLoop\.assertion\.\d+\][^\n]*:\s*(SUCCESS|FAILURE)",
        plain,
    )
    if not business:
        return "inconclusive", "unparseable_report", plain[-4000:]
    if "FAILURE" in business:
        return "false", "bounded_counterexample", plain[-8000:]
    failed_checks = re.findall(r"\[([^\]]+)\][^\n]*:\s*FAILURE", plain)
    non_unwind_failures = [item for item in failed_checks if ".unwind." not in item]
    if non_unwind_failures:
        return "inconclusive", "non_requirement_cbmc_failure", plain[-8000:]
    if "VERIFICATION SUCCESSFUL" in plain:
        return "true", "bounded_no_counterexample", plain[-4000:]
    if failed_checks and not non_unwind_failures:
        return "true", "bounded_no_counterexample_unwind_limit_reached", plain[-4000:]
    return "inconclusive", "unparseable_report", plain[-4000:]


def compact_counterexample(text: str, limit: int = 2200) -> str:
    """Keep the verdict and final states instead of an arbitrary raw-log tail."""
    if not text:
        return ""
    lines = text.splitlines()
    verdict = [
        line.strip()
        for line in lines
        if " is false" in line.casefold()
        or "assertion" in line.casefold() and "failure" in line.casefold()
    ][:2]
    state_starts = [index for index, line in enumerate(lines) if "-> State:" in line]
    selected: list[str] = list(verdict)
    if state_starts:
        for position in state_starts[-3:]:
            end = next((item for item in state_starts if item > position), len(lines))
            block = [
                line for line in lines[position:end]
                if not re.match(r"\s*(loc|BoC|EoC)\s*=", line)
            ]
            selected.extend(block)
    else:
        selected.extend(lines[-50:])
    excerpt = "\n".join(selected).strip()
    if len(excerpt) <= limit:
        return excerpt
    marker = "\n...[trace middle omitted]...\n"
    head = max(0, limit // 3)
    tail = max(0, limit - head - len(marker))
    return excerpt[:head] + marker + excerpt[-tail:]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--task-dir", required=True, type=Path)
    parser.add_argument("--plcverif", required=True, type=Path)
    parser.add_argument("--nuxmv", required=True, type=Path)
    parser.add_argument("--cbmc", required=True, type=Path)
    parser.add_argument("--timer-library", required=True, type=Path)
    parser.add_argument("--numeric-library", required=True, type=Path)
    parser.add_argument("--property-kind", choices=("all", "safety", "functional"), default="all")
    parser.add_argument("--minimum-properties", type=int, default=1)
    parser.add_argument("--backend-timeout", type=int, default=120)
    parser.add_argument("--cbmc-unwind", type=int, default=10)
    parser.add_argument(
        "--counterexample-feedback",
        choices=("raw", "actionable"),
        default="raw",
        help="choose the ablatable counterexample representation returned to the synthesis loop",
    )
    parser.add_argument(
        "--case-workers",
        type=int,
        default=1,
        help="run independent native property cases concurrently; results remain in declaration order",
    )
    parser.add_argument(
        "--stop-on-first-counterexample",
        action="store_true",
        help="return failure after the first trustworthy mandatory-property counterexample",
    )
    args = parser.parse_args()
    tool_version = f"{TOOL_VERSION}+counterexample-feedback-{args.counterexample_feedback}-v1"
    if args.case_workers < 1 or args.case_workers > 12:
        parser.error("--case-workers must be between 1 and 12")
    if args.stop_on_first_counterexample and args.case_workers != 1:
        parser.error("--stop-on-first-counterexample requires --case-workers 1")

    candidate = args.candidate.resolve()
    task_dir = args.task_dir.resolve()
    plcverif = args.plcverif.resolve()
    nuxmv = args.nuxmv.resolve()
    cbmc = args.cbmc.resolve()
    timer_library = args.timer_library.resolve()
    numeric_library = args.numeric_library.resolve()
    required_paths = (
        candidate, task_dir / "metadata.json", task_dir / "properties.json",
        plcverif, nuxmv, cbmc, timer_library, numeric_library,
    )
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        return emit({
            "status": "inconclusive",
            "summary": "PLCverif infrastructure is incomplete",
            "evidence": [{"kind": "tool_error", "summary": f"missing: {', '.join(missing)}"}],
            "tool_version": tool_version,
        })

    metadata = json.loads((task_dir / "metadata.json").read_text(encoding="utf-8"))
    property_document = json.loads((task_dir / "properties.json").read_text(encoding="utf-8"))
    profile = property_document.get("plcverif_profile")
    if not isinstance(profile, dict) or profile.get("name") != "native-pattern-invariant-v1":
        return emit({
            "status": "inconclusive",
            "summary": "task has no qualified native PLCverif profile",
            "evidence": [{"kind": "formal_profile_missing", "summary": "expected native-pattern-invariant-v1"}],
            "tool_version": tool_version,
        })
    input_names = {item["name"] for item in metadata["interface"]["inputs"]}
    variable_names = {
        item["name"]
        for section in ("inputs", "outputs")
        for item in metadata["interface"][section]
    }
    environment = profile.get("environment", {})
    environment_parameters = environment.get("parameters", [])
    environment_guards = environment.get("assumption_invariants", [])
    environment_cbmc_unwind = environment.get("cbmc_unwind", args.cbmc_unwind)
    if (
        not isinstance(environment_parameters, list)
        or not isinstance(environment_guards, list)
        or not set(environment_parameters) <= input_names
        or not isinstance(environment_cbmc_unwind, int)
        or environment_cbmc_unwind < 2
    ):
        return emit({
            "status": "inconclusive",
            "summary": "qualified PLCverif environment is invalid",
            "evidence": [{"kind": "formal_profile_error", "summary": "parameters must be fixed input names"}],
            "tool_version": tool_version,
        })
    try:
        qualified_environment_guards = [
            qualify_parameter(str(value), variable_names)
            for value in environment_guards
        ]
    except ValueError as exc:
        return emit({
            "status": "inconclusive",
            "summary": "qualified PLCverif environment is invalid",
            "evidence": [{"kind": "formal_profile_error", "summary": str(exc)}],
            "tool_version": tool_version,
        })
    properties = [item for item in property_document["properties"] if item.get("mandatory")]
    selected_properties = [
        item for item in properties
        if (args.property_kind == "all" or item.get("kind") == args.property_kind)
        and item.get("plcverif", {}).get("status") in {"required", "required_partial"}
    ]
    uncovered = [
        {"id": item["id"], "requirement_ids": item.get("requirement_ids", []), "reason": item.get("plcverif", {}).get("status", "profile_missing")}
        for item in properties
        if (args.property_kind == "all" or item.get("kind") == args.property_kind)
        and item.get("plcverif", {}).get("status") != "required"
    ]
    native_cases = []
    try:
        for prop in selected_properties:
            cases = prop["plcverif"].get("cases", [])
            if not cases:
                raise ValueError(f"required property {prop['id']} has no native case")
            for case_index, case in enumerate(cases, start=1):
                backend = str(case.get("backend"))
                pattern_id = str(case.get("pattern_id"))
                parameters = case.get("parameters")
                if backend not in {"auto", "nusmv", "cbmc"}:
                    raise ValueError(f"{prop['id']}: unsupported configured backend {backend!r}")
                if not pattern_id.startswith("pattern-"):
                    raise ValueError(f"{prop['id']}: invalid built-in pattern id {pattern_id!r}")
                if not isinstance(parameters, list) or not parameters:
                    raise ValueError(f"{prop['id']}: native pattern has no parameters")
                qualified_parameters = [
                    qualify_parameter(str(value), variable_names)
                    for value in parameters
                ]
                if qualified_environment_guards:
                    guard = " AND ".join(f"({value})" for value in qualified_environment_guards)
                    qualified_parameters = [
                        f"({guard}) --> ({value})"
                        for value in qualified_parameters
                    ]
                native_cases.append({
                    "case_id": prop["id"] if len(cases) == 1 else f"{prop['id']}_{case_index}",
                    "property_id": prop["id"],
                    "requirement_ids": list(prop.get("requirement_ids", [])),
                    "backend": backend,
                    "pattern_id": pattern_id,
                    "parameters": qualified_parameters,
                    "public_parameters": [str(value) for value in parameters],
                    "public_property_expression": str(prop.get("expression", "")),
                    "property_coverage": prop["plcverif"].get("coverage", "complete"),
                })
    except (KeyError, TypeError, ValueError) as exc:
        return emit({
            "status": "inconclusive",
            "summary": "qualified PLCverif profile is invalid",
            "evidence": [{"kind": "formal_profile_error", "summary": str(exc)}],
            "tool_version": tool_version,
        })
    if len(selected_properties) < args.minimum_properties or not native_cases:
        return emit({
            "status": "inconclusive",
            "summary": f"formal profile contains {len(selected_properties)} native properties; minimum is {args.minimum_properties}",
            "evidence": [{"kind": "formal_coverage_gap", "summary": "no sufficient mandatory native property set"}],
            "formal_coverage": {"native": len(selected_properties), "total": len(properties), "uncovered": uncovered},
            "tool_version": tool_version,
        })

    source = candidate.read_text(encoding="utf-8")
    uses_timer = bool(re.search(r"(?im):\s*(TON|TOF)\s*;", source))
    uses_numeric_library = bool(re.search(r"(?i)\b(ABS|INT_TO_REAL)\s*\(", source))
    requires_cbmc = uses_numeric_library or bool(re.search(r"(?<![A-Za-z0-9_])\d+\.\d+", source))
    if uses_timer and int(metadata["scan"]["period_ms"]) != 100:
        return emit({
            "status": "inconclusive",
            "summary": "timer environment model is qualified only for a 100 ms scan",
            "evidence": [{"kind": "environment_model_mismatch", "summary": "scan period is not 100 ms"}],
            "tool_version": tool_version,
        })

    artifact_root = Path.cwd() / "plcverif_artifacts"
    artifact_root.mkdir(exist_ok=True)
    # PLCverif is an Eclipse application.  Its native launcher otherwise derives
    # a configuration directory from the account passwd entry (not $HOME), which
    # fails under a read-only production home and makes a valid candidate look
    # inconclusive.  Keep the cache inside this attempt's writable evidence tree;
    # case_workers is frozen to one in production, so no launcher races occur.
    eclipse_configuration = artifact_root / "eclipse_configuration"
    eclipse_configuration.mkdir(exist_ok=True)
    failures = []
    passed_requirements: set[str] = set()
    case_results = []

    def execute_case(case: dict[str, Any]) -> dict[str, Any]:
        case_id = case["case_id"]
        configured_backend = case["backend"]
        preferred_backend = "cbmc" if configured_backend == "auto" and requires_cbmc else (
            "nusmv" if configured_backend == "auto" else configured_backend
        )
        backend_order = [preferred_backend]
        if preferred_backend == "nusmv":
            backend_order.append("cbmc")
        verdict = "inconclusive"
        proof_scope = "none"
        result_text = ""
        raw_log = ""
        log_path: Path | None = None
        resolved_backend = preferred_backend
        attempted_backends = []
        for backend in backend_order:
            attempted_backends.append(backend)
            resolved_backend = backend
            output_dir = artifact_root / case_id / backend
            # A validator retry must never parse a verdict left by a timed-out
            # prior execution of the same candidate and case.
            if output_dir.exists():
                shutil.rmtree(output_dir)
            command = [
                str(plcverif),
                "-configuration", str(eclipse_configuration),
                "-id", case_id,
                "-job", "verif",
                "-job.strict", "true",
                "-job.diagnostic_outputs", "true",
                "-job.backend", backend,
                "-job.backend.binary_path", str(nuxmv if backend == "nusmv" else cbmc),
                "-job.backend.timeout", str(args.backend_timeout),
            ]
            if backend == "cbmc":
                command.extend([
                    "-job.backend.timeout_executor_path", '""',
                    "-job.backend.unwind", str(environment_cbmc_unwind),
                    "-job.backend.verbosity", "7",
                ])
            else:
                command.extend(["-job.backend.req_as_invar", "true"])
            command.extend(["-lf", "step7", "-sourcefiles.0", str(candidate)])
            source_index = 1
            if uses_timer:
                command.extend([f"-sourcefiles.{source_index}", str(timer_library)])
                source_index += 1
            if uses_numeric_library:
                command.extend([f"-sourcefiles.{source_index}", str(numeric_library)])
            command.extend([
                "-output", str(output_dir),
                "-job.req", "pattern",
                "-job.req.pattern_id", case["pattern_id"],
            ])
            for index, parameter in enumerate(case["parameters"], start=1):
                command.append(f'-job.req.pattern_params.{index}="{parameter}"')
            for index, parameter in enumerate(environment_parameters):
                command.extend([f"-job.req.params.{index}", f"instance.{parameter}"])
            command.extend([
                "-lf.entry", str(metadata["id"]),
                "-job.reporters", "html",
            ])
            try:
                completed = run_captured(
                    command,
                    timeout=max(args.backend_timeout + 90, 180),
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raw_log = f"{type(exc).__name__}: {exc}"
                continue
            raw_log = completed.stdout + completed.stderr
            log_path = artifact_root / f"{case_id}.{backend}.log"
            log_path.write_text(raw_log, encoding="utf-8")
            if backend == "nusmv":
                result_path = verdict_file(output_dir, backend)
                result_text = result_path.read_text(encoding="utf-8", errors="replace") if result_path else ""
                lowered = result_text.lower()
                if " is false" in lowered:
                    verdict, proof_scope = "false", "unbounded_finite_state_counterexample"
                    break
                if " is true" in lowered:
                    verdict, proof_scope = "true", "unbounded_finite_state_proof"
                    break
                # Unsupported datatypes, state-space timeout, and backend failures
                # may use PLCverif's own CBMC backend.  A NuXmv FALSE never falls
                # through this path.
                continue
            verdict, proof_scope, result_text = cbmc_verdict(output_dir)
            if verdict != "inconclusive":
                break

        return {
            "case": case,
            "verdict": verdict,
            "proof_scope": proof_scope,
            "result_text": result_text,
            "raw_log": raw_log,
            "log_path": log_path,
            "resolved_backend": resolved_backend,
            "attempted_backends": attempted_backends,
        }

    if args.case_workers == 1:
        execution_records = map(execute_case, native_cases)
    else:
        # executor.map preserves the frozen property declaration order even when
        # backend processes finish in a different order.  Each case has a unique
        # artifact directory, so concurrency changes scheduling but not evidence.
        pool = ThreadPoolExecutor(max_workers=min(args.case_workers, len(native_cases)))
        execution_records = pool.map(execute_case, native_cases)

    try:
        for execution in execution_records:
            case = execution["case"]
            case_id = case["case_id"]
            verdict = execution["verdict"]
            proof_scope = execution["proof_scope"]
            result_text = execution["result_text"]
            raw_log = execution["raw_log"]
            log_path = execution["log_path"]
            resolved_backend = execution["resolved_backend"]
            attempted_backends = execution["attempted_backends"]

            if verdict == "inconclusive":
                diagnostic = result_text or raw_log or "missing backend verdict"
                if is_candidate_source_defect(diagnostic):
                    return emit({
                        "status": "fail",
                        "summary": f"PLCverif rejected the candidate source before checking {case_id}",
                        "evidence": [{
                            "kind": "formal_source_error",
                            "summary": diagnostic[-4000:],
                            "requirement_ids": [],
                            "oracle_status": "confirmed_candidate_defect",
                            "raw_log_sha256": sha256(log_path) if log_path else None,
                        }],
                        "formal_coverage": {"native": len(selected_properties), "total": len(properties), "uncovered": uncovered},
                        "tool_version": tool_version,
                    })
                return emit({
                    "status": "inconclusive",
                    "summary": f"PLCverif produced no trustworthy verdict for {case_id}",
                    "evidence": [{
                        "kind": "tool_error", "summary": diagnostic[-4000:],
                        "requirement_ids": case["requirement_ids"],
                        "raw_log_sha256": sha256(log_path) if log_path else None,
                    }],
                    "formal_coverage": {"native": len(selected_properties), "total": len(properties), "uncovered": uncovered},
                    "tool_version": tool_version,
                })
            if verdict == "false":
                trace = (
                    {
                        "case_id": case_id,
                        "property_id": case["property_id"],
                        "public_property_expression": case["public_property_expression"],
                        "violated_condition": case["public_parameters"],
                        "backend": resolved_backend,
                        "counterexample_excerpt": compact_counterexample(result_text),
                    }
                    if args.counterexample_feedback == "actionable"
                    else {"counterexample_tail": result_text[-4000:]}
                )
                failures.append({
                    "kind": "formal_counterexample",
                    "summary": f"native PLCverif case {case_id} is false",
                    "requirement_ids": case["requirement_ids"],
                    "trace": trace,
                    "oracle_status": "formal_counterexample_pending_runtime_replay",
                    "raw_log_sha256": sha256(log_path) if log_path else None,
                })
                case_results.append({
                    "case_id": case_id, "verdict": "false",
                    "backend": resolved_backend, "proof_scope": proof_scope,
                    "attempted_backends": attempted_backends,
                })
                if args.stop_on_first_counterexample:
                    break
            else:
                # A sub-formula from a partially expressible property cannot justify
                # claiming that the whole linked natural-language requirement passed.
                if case["property_coverage"] == "complete":
                    passed_requirements.update(case["requirement_ids"])
                case_results.append({
                    "case_id": case_id, "verdict": "true",
                    "backend": resolved_backend, "proof_scope": proof_scope,
                    "attempted_backends": attempted_backends,
                })
    finally:
        if args.case_workers != 1:
            pool.shutdown(wait=True, cancel_futures=True)

    coverage = {
        "profile": profile["name"],
        "native_properties": len(selected_properties),
        "native_cases": len(native_cases),
        "evaluated_cases": len(case_results),
        "exhaustive": len(case_results) == len(native_cases),
        "fully_native_properties": sum(
            item["plcverif"].get("coverage") == "complete"
            for item in selected_properties
        ),
        "partially_native_properties": sum(
            item["plcverif"].get("coverage") == "partial"
            for item in selected_properties
        ),
        "total_mandatory_properties": len(properties),
        "uncovered_properties": uncovered,
        "environment_parameters": environment_parameters,
        "environment_assumption_invariants": environment_guards,
        "cbmc_unwind": environment_cbmc_unwind,
        "timer_environment_model_used": uses_timer,
        "timer_environment_model_sha256": sha256(timer_library) if uses_timer else None,
        "numeric_environment_model_used": uses_numeric_library,
        "numeric_environment_model_sha256": sha256(numeric_library) if uses_numeric_library else None,
        "case_workers": args.case_workers,
        "case_result_order": "frozen_property_declaration_order",
        "unbounded_proof_cases": sum(
            item.get("proof_scope") == "unbounded_finite_state_proof"
            for item in case_results
        ),
        "bounded_no_counterexample_cases": sum(
            str(item.get("proof_scope", "")).startswith("bounded_no_counterexample")
            for item in case_results
        ),
    }
    if failures:
        failed_requirements = {
            requirement_id
            for failure in failures
            for requirement_id in failure.get("requirement_ids", [])
        }
        supported_requirements = passed_requirements - failed_requirements
        return emit({
            "status": "fail",
            "summary": (
                f"{len(failures)} mandatory native PLCverif case was violated; "
                f"stopped after {len(case_results)}/{len(native_cases)} cases"
                if args.stop_on_first_counterexample
                else f"{len(failures)}/{len(native_cases)} native PLCverif cases were violated"
            ),
            "evidence": failures,
            "passed_requirement_ids": sorted(supported_requirements),
            "formal_coverage": coverage,
            "case_results": case_results,
            "tool_version": tool_version,
        })
    return emit({
        "status": "pass",
        "summary": f"{len(native_cases)}/{len(native_cases)} native PLCverif cases have no property counterexample",
        "evidence": [],
        "passed_requirement_ids": sorted(passed_requirements),
        "formal_coverage": coverage,
        "case_results": case_results,
        "tool_version": tool_version,
    })


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Audit a completed Balanced-100 DVP48ES300R experiment.

The batch summary is not accepted on its own.  This audit replays the ledger
checks, verifies the frozen method snapshot, and links every attempted Delta
gate to an immutable ISPSoft/COMMGR spool job by task, candidate hash, role,
and run time window.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import tarfile
from collections import Counter
from pathlib import Path
from typing import Any

METHOD_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = METHOD_ROOT / "src"
SCRIPTS_ROOT = METHOD_ROOT / "scripts"
import sys

for path in (SRC_ROOT, SCRIPTS_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from plc_loop.delta_dvp import parse_function_block, select_openplc_cases  # noqa: E402
from plc_loop.ledger import EvidenceLedger  # noqa: E402
from run_method_batch import audit_completed_run, sha256  # noqa: E402


ASSET_MEMBERS = {
    "system_prompt": "prompts/system.md",
    "response_contract": "prompts/response_contract.md",
    "iec_st_patterns": "knowledge/iec_st_patterns.json",
    "orchestrator": "src/plc_loop/orchestrator.py",
    "context_builder": "src/plc_loop/context.py",
    "repair_policy": "src/plc_loop/policy.py",
    "validator:matiec_validator.py": "scripts/matiec_validator.py",
    "validator:formal_plcverif.py": "scripts/formal_plcverif.py",
    "validator:openplc_sealed_validator.py": "scripts/openplc_sealed_validator.py",
    "validator:openplc_container_runner.py": "scripts/openplc_container_runner.py",
    "validator:dvp48es300r_validator.py": "scripts/dvp48es300r_validator.py",
    "validator:dvp48es300r_sealed_composite.py": "scripts/dvp48es300r_sealed_composite.py",
    "validator:Run-DvpValidationWorker.ps1": "windows/Run-DvpValidationWorker.ps1",
    "validator:Invoke-DvpRuntimeCase.ps1": "windows/Invoke-DvpRuntimeCase.ps1",
}
ADAPTER_ASSET_MEMBERS = {
    "adapter:delta_dvp/__init__.py": "src/plc_loop/delta_dvp/__init__.py",
    "adapter:delta_dvp/source_unit.py": "src/plc_loop/delta_dvp/source_unit.py",
    "adapter:delta_dvp/harness.py": "src/plc_loop/delta_dvp/harness.py",
}
JOB_ID = re.compile(r"^(\d{13})-[0-9a-f]{12}-[0-9a-f]{10}$")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_timestamp(value: str) -> float:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def job_timestamp(job_id: str) -> float:
    match = JOB_ID.fullmatch(job_id)
    if match is None:
        raise ValueError(f"invalid DVP job id: {job_id!r}")
    return int(match.group(1)) / 1000.0


def verify_snapshot(archive: Path, expected: dict[str, str]) -> list[str]:
    errors: list[str] = []
    with tarfile.open(archive, "r:gz") as bundle:
        members = {item.name.removeprefix("./"): item for item in bundle.getmembers()}
        for label, relative in ASSET_MEMBERS.items():
            member = members.get(relative)
            if member is None:
                errors.append(f"snapshot is missing {relative}")
                continue
            stream = bundle.extractfile(member)
            if stream is None:
                errors.append(f"snapshot member is not readable: {relative}")
                continue
            actual = hashlib.sha256(stream.read()).hexdigest()
            if actual != expected.get(label):
                errors.append(f"snapshot hash mismatch for {label}")
        # Runs created after the adapter-hash hardening record these modules in
        # the ledger.  Older frozen runs are still auditable through the whole
        # archive digest, but their weaker per-asset coverage is reported
        # separately rather than retroactively inventing a hash-chain entry.
        for label, relative in ADAPTER_ASSET_MEMBERS.items():
            if label not in expected:
                continue
            member = members.get(relative)
            if member is None:
                errors.append(f"snapshot is missing {relative}")
                continue
            stream = bundle.extractfile(member)
            if stream is None:
                errors.append(f"snapshot member is not readable: {relative}")
                continue
            actual = hashlib.sha256(stream.read()).hexdigest()
            if actual != expected[label]:
                errors.append(f"snapshot hash mismatch for {label}")
    return errors


def verify_spool_job(spool: Path, result_dir: Path) -> dict[str, Any]:
    job_id = result_dir.name
    submitted = spool / "pending" / job_id
    manifest = load_json(result_dir / "manifest.json")
    result = load_json(result_dir / "result.json")
    if manifest != load_json(submitted / "manifest.json"):
        raise ValueError(f"{job_id}: pending/result manifests differ")
    if manifest.get("job_id") != job_id:
        raise ValueError(f"{job_id}: manifest job id differs")
    for name, field in (
        ("candidate.st", "candidate_sha256"),
        ("candidate.FBU", "function_unit_sha256"),
        ("MAIN.MPU", "program_unit_sha256"),
        ("suite.json", "suite_sha256"),
    ):
        if hash_file(submitted / name) != manifest.get(field):
            raise ValueError(f"{job_id}: {name} hash differs from manifest")
    for field in ("job_id", "task_id", "role", "candidate_sha256", "target"):
        if result.get(field) != manifest.get(field):
            raise ValueError(f"{job_id}: result {field} differs from manifest")
    if result.get("target") != "DVP48ES300R":
        raise ValueError(f"{job_id}: unexpected target")
    gates = result.get("gates") or []
    if [gate.get("name") for gate in gates] != [
        "ispsoft_compile", "commgr_connect", "dvp_es3_runtime"
    ]:
        raise ValueError(f"{job_id}: invalid gate sequence")
    statuses = [gate.get("status") for gate in gates]
    if result.get("status") == "pass" and statuses != ["pass", "pass", "pass"]:
        raise ValueError(f"{job_id}: pass without three passing gates")
    suite = load_json(submitted / "suite.json")
    if suite.get("case_role") != manifest.get("role"):
        raise ValueError(f"{job_id}: suite role differs")
    expected_cases = [str(case["id"]) for case in suite.get("cases", [])]
    observed_cases = [str(item.get("case_id")) for item in result.get("evidence", [])]
    if result.get("status") == "pass":
        if observed_cases != expected_cases:
            raise ValueError(f"{job_id}: passing result did not execute every selected case")
        if any(item.get("status") != "pass" for item in result.get("evidence", [])):
            raise ValueError(f"{job_id}: passing result contains a non-passing case")
    return {
        "job_id": job_id,
        "submitted_at": job_timestamp(job_id),
        "task_id": str(manifest["task_id"]),
        "role": str(manifest["role"]),
        "candidate_sha256": str(manifest["candidate_sha256"]),
        "status": str(result["status"]),
        "case_count": len(observed_cases),
        "selected_case_ids": expected_cases,
        "observed_case_ids": observed_cases,
    }


def index_spool(spool: Path) -> tuple[dict[tuple[str, str, str], list[dict[str, Any]]], list[str]]:
    index: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    errors: list[str] = []
    for result_dir in sorted((spool / "results").iterdir()):
        if not result_dir.is_dir() or not (result_dir / "result.json").is_file():
            continue
        try:
            record = verify_spool_job(spool, result_dir)
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{result_dir.name}: {type(exc).__name__}: {exc}")
            continue
        key = (record["task_id"], record["candidate_sha256"], record["role"])
        index.setdefault(key, []).append(record)
    return index, errors


def verify_openplc_sealed_trace(
    attempt_dir: Path,
    expected_case_ids: list[str],
) -> dict[str, Any]:
    """Independently verify the persisted sealed OpenPLC suite and trace."""
    evidence_dir = attempt_dir / "openplc_sealed"
    suite = load_json(evidence_dir / "openplc_sealed_suite.json")
    trace = load_json(evidence_dir / "openplc_test_trace.json")
    if not isinstance(trace, list):
        raise ValueError("sealed OpenPLC trace is not a list")
    cases = list(suite.get("cases") or [])
    observed_case_ids = [str(case.get("id")) for case in cases]
    if observed_case_ids != expected_case_ids:
        raise ValueError("sealed OpenPLC suite differs from dataset sealed cases")

    expected_rows: list[tuple[str, int, int, bool, dict[str, Any], dict[str, Any]]] = []
    for case in cases:
        case_name = str(case["name"])
        for step_index, step in enumerate(case.get("steps") or [], start=1):
            repetitions = int(step["repeat"])
            for repeat_index in range(1, repetitions + 1):
                checked = (
                    step.get("check") != "last_only"
                    or repeat_index == repetitions
                )
                expected_rows.append((
                    case_name,
                    step_index,
                    repeat_index,
                    checked,
                    dict(step["inputs"]),
                    dict(step["expect"]),
                ))
    if len(trace) != len(expected_rows):
        raise ValueError(
            f"sealed OpenPLC trace has {len(trace)} rows, expected {len(expected_rows)}"
        )
    checked_count = 0
    for index, (row, expected) in enumerate(zip(trace, expected_rows), start=1):
        case_name, step_index, repeat_index, checked, inputs, outputs = expected
        identity = (str(row.get("case")), int(row.get("step", -1)), int(row.get("repeat", -1)))
        if identity != (case_name, step_index, repeat_index):
            raise ValueError(f"sealed OpenPLC trace row {index} identity differs")
        if row.get("inputs") != inputs or row.get("expected") != outputs:
            raise ValueError(f"sealed OpenPLC trace row {index} Oracle differs")
        if bool(row.get("checked")) != checked:
            raise ValueError(f"sealed OpenPLC trace row {index} checked flag differs")
        if not checked:
            continue
        checked_count += 1
        matches = row.get("matches")
        if not isinstance(matches, dict) or set(matches) != set(outputs):
            raise ValueError(f"sealed OpenPLC trace row {index} output set differs")
        if not matches or not all(value is True for value in matches.values()):
            raise ValueError(f"sealed OpenPLC trace row {index} contains a mismatch")
    if checked_count == 0:
        raise ValueError("sealed OpenPLC trace contains no checked observations")
    return {
        "case_ids": observed_case_ids,
        "trace_rows": len(trace),
        "checked_observations": checked_count,
        "all_checked_outputs_match": True,
    }


def find_job(
    index: dict[tuple[str, str, str], list[dict[str, Any]]],
    *,
    task_id: str,
    candidate_sha256: str,
    role: str,
    status: str | None,
    started_at: float,
    finished_at: float,
) -> dict[str, Any] | None:
    candidates = index.get((task_id, candidate_sha256, role), [])
    candidates = [
        item for item in candidates
        if started_at <= item["submitted_at"] <= finished_at
        and (status is None or item["status"] == status)
    ]
    return candidates[-1] if candidates else None


def is_result_transport_failure(gate: dict[str, Any]) -> bool:
    """Recognise an adapter read failure without treating worker failures alike."""
    if gate.get("status") != "inconclusive":
        return False
    if "Windows DVP worker returned unverifiable evidence" not in str(gate.get("summary", "")):
        return False
    return any(
        item.get("kind") == "tool_error"
        and "JSONDecodeError" in str(item.get("summary", ""))
        for item in gate.get("evidence", [])
    )


def find_job_for_gate(
    index: dict[tuple[str, str, str], list[dict[str, Any]]],
    *,
    task_id: str,
    candidate_sha256: str,
    role: str,
    gate: dict[str, Any],
    started_at: float,
    finished_at: float,
) -> dict[str, Any] | None:
    """Link a gate to worker evidence while preserving adapter/worker disagreement.

    Normally the persisted gate and Windows worker status must agree.  The only
    exception is an explicitly evidenced JSON read race: the adapter remains
    inconclusive, but the immutable worker result can still be audited as a
    transport-status mismatch.  This annotation never changes task scoring.
    """
    adapter_status = str(gate.get("status"))
    job = find_job(
        index,
        task_id=task_id,
        candidate_sha256=candidate_sha256,
        role=role,
        status=adapter_status,
        started_at=started_at,
        finished_at=finished_at,
    )
    mismatch = False
    if job is None and is_result_transport_failure(gate):
        job = find_job(
            index,
            task_id=task_id,
            candidate_sha256=candidate_sha256,
            role=role,
            status=None,
            started_at=started_at,
            finished_at=finished_at,
        )
        mismatch = job is not None and job["status"] != adapter_status
    if job is None:
        return None
    linked = dict(job)
    linked.update({
        "adapter_status": adapter_status,
        "worker_status": str(job["status"]),
        "transport_status_mismatch": mismatch,
    })
    return linked


def task_window(entries: list[dict[str, Any]]) -> tuple[float, float]:
    return parse_timestamp(entries[0]["timestamp_utc"]), parse_timestamp(entries[-1]["timestamp_utc"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--dataset-root", required=True, type=Path)
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument("--spool-root", required=True, type=Path)
    parser.add_argument("--frozen-source", required=True, type=Path)
    parser.add_argument("--frozen-source-sha256", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--expected-task-count", type=int, default=100)
    args = parser.parse_args()

    config = load_json(args.config.resolve())
    tasks_root = args.dataset_root.resolve() / "tasks"
    task_dirs = [path for path in sorted(tasks_root.iterdir()) if path.is_dir()]
    errors: list[str] = []
    if len(task_dirs) != args.expected_task_count:
        errors.append(f"dataset contains {len(task_dirs)} tasks, expected {args.expected_task_count}")
    summary_path = args.run_root.resolve() / "batch_summary.json"
    if not summary_path.is_file():
        errors.append("batch_summary.json is absent; the run is incomplete")
        summary: dict[str, Any] = {}
    else:
        summary = load_json(summary_path)

    expected_archive_hash = args.frozen_source_sha256.read_text(encoding="utf-8").split()[0]
    if hash_file(args.frozen_source) != expected_archive_hash:
        errors.append("frozen method archive hash differs from its sidecar")

    spool_index, spool_errors = index_spool(args.spool_root.resolve())
    errors.extend(spool_errors)
    requested_model = str(config["provider"]["requested_model"])
    allowed_models = tuple(config["provider"].get("allowed_resolved_models") or [requested_model])
    candidate_budget = int(config["experiment"]["max_candidates"])
    config_hash = sha256(args.config.resolve())
    records: list[dict[str, Any]] = []
    method_assets: list[dict[str, str]] = []
    successful_candidate_isolation: list[bool] = []

    for task_dir in task_dirs:
        run_dir = args.run_root.resolve() / task_dir.name
        if not (run_dir / "result.json").is_file():
            errors.append(f"{task_dir.name}: terminal result is absent")
            continue
        try:
            record = audit_completed_run(
                run_dir,
                task_id=task_dir.name,
                method="evidence",
                candidate_budget=candidate_budget,
                allowed_models=allowed_models,
                expected_config_sha256=config_hash,
                expected_ablation_id=config["experiment"].get("ablation_id"),
                expected_component_1=config["experiment"].get("core_component_1_enabled"),
                expected_component_2=config["experiment"].get("core_component_2_enabled"),
            )
            ledger = EvidenceLedger.verify(run_dir / "ledger.jsonl")
            started_at, finished_at = task_window(ledger)
            method_assets.append(dict(ledger[0]["payload"]["method_asset_sha256"]))
            result = load_json(run_dir / "result.json")
            source_suite = load_json(task_dir / "openplc_tests.json")
            expected_cases = {
                role: [str(case["id"]) for case in select_openplc_cases(source_suite, role)["cases"]]
                for role in ("feedback", "sealed")
            }
            linked_jobs: list[dict[str, Any]] = []
            for attempt in result.get("attempts", []):
                gate = next(
                    (item for item in attempt.get("gates", []) if item.get("name") == "dvp48es300r_feedback"),
                    None,
                )
                if gate is None or gate.get("status") == "skipped":
                    continue
                job = find_job_for_gate(
                    spool_index,
                    task_id=task_dir.name,
                    candidate_sha256=str(attempt["candidate_sha256"]),
                    role="feedback",
                    gate=gate,
                    started_at=started_at,
                    finished_at=finished_at,
                )
                if job is None:
                    raise ValueError(
                        f"attempt {attempt['number']} has no matching visible Windows job"
                    )
                if job["selected_case_ids"] != expected_cases["feedback"]:
                    raise ValueError(
                        f"attempt {attempt['number']} Windows suite differs from dataset feedback cases"
                    )
                linked_jobs.append(job)
            if result.get("success"):
                winning = int(result["winning_attempt"])
                attempt = next(item for item in result["attempts"] if int(item["number"]) == winning)
                winning_source = run_dir / "attempts" / f"attempt_{winning:02d}" / "candidate.st"
                parse_function_block(winning_source.read_text(encoding="utf-8-sig"))
                successful_candidate_isolation.append(True)
                visible = {item["name"]: item["status"] for item in attempt["gates"]}
                required = {"compiler", "plcverif", "openplc_feedback", "dvp48es300r_feedback"}
                if any(visible.get(name) != "pass" for name in required):
                    raise ValueError("winning attempt does not pass every visible gate")
                sealed = result.get("sealed_result") or {}
                if sealed.get("name") != "openplc_dvp48es300r_sealed" or sealed.get("status") != "pass":
                    raise ValueError("verified success lacks a passing composite sealed gate")
                record["openplc_sealed_trace"] = verify_openplc_sealed_trace(
                    run_dir / "attempts" / f"attempt_{winning:02d}",
                    expected_cases["sealed"],
                )
                sealed_job = find_job(
                    spool_index,
                    task_id=task_dir.name,
                    candidate_sha256=str(attempt["candidate_sha256"]),
                    role="sealed",
                    status="pass",
                    started_at=started_at,
                    finished_at=finished_at,
                )
                if sealed_job is None:
                    raise ValueError("verified success has no matching sealed Windows job")
                if sealed_job["selected_case_ids"] != expected_cases["sealed"]:
                    raise ValueError("sealed Windows suite differs from dataset sealed cases")
                linked_jobs.append(sealed_job)
            record["dvp_jobs"] = linked_jobs
            records.append(record)
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{task_dir.name}: {type(exc).__name__}: {exc}")

    unique_assets = {json.dumps(item, sort_keys=True) for item in method_assets}
    adapter_assets_ledgered = bool(method_assets) and all(
        set(ADAPTER_ASSET_MEMBERS).issubset(item) for item in method_assets
    )
    if len(unique_assets) != 1:
        errors.append(f"completed tasks contain {len(unique_assets)} method-asset sets")
    elif method_assets:
        errors.extend(verify_snapshot(args.frozen_source, method_assets[0]))

    successes = sum(bool(item.get("success")) for item in records)
    statuses = Counter(str(item.get("status")) for item in records)
    candidates = [int(item.get("candidates_used", 0)) for item in records]
    report = {
        "schema_version": "1.0",
        "audit_pass": not errors and len(records) == args.expected_task_count,
        "expected_task_count": args.expected_task_count,
        "audited_task_count": len(records),
        "verified_success_count": successes,
        "success_rate": successes / args.expected_task_count,
        "status_counts": dict(sorted(statuses.items())),
        "candidate_usage": {
            "total": sum(candidates),
            "minimum": min(candidates) if candidates else None,
            "maximum": max(candidates) if candidates else None,
            "mean": sum(candidates) / len(candidates) if candidates else None,
        },
        "batch_summary_matches": bool(summary) and (
            int(summary.get("task_count", -1)) == len(records)
            and int(summary.get("success_count", -1)) == successes
            and int(summary.get("total_candidates_used", -1)) == sum(candidates)
        ),
        "model_identity_valid": all(item.get("model_identity_valid") for item in records),
        "successful_candidate_isolation_valid": (
            len(successful_candidate_isolation) == successes
            and all(successful_candidate_isolation)
        ),
        "adapter_assets_ledgered": adapter_assets_ledgered,
        "ledger_valid": all(item.get("ledger_valid") for item in records),
        "sealed_accounting_valid": all(
            item.get("sealed_events") == item.get("sealed_files") == item.get("sealed_records")
            for item in records
        ),
        "frozen_source_sha256": expected_archive_hash,
        "errors": errors,
        "tasks": records,
    }
    if not report["batch_summary_matches"]:
        report["errors"].append("batch summary totals differ from independently audited tasks")
        report["audit_pass"] = False
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    print(json.dumps({key: report[key] for key in (
        "audit_pass", "audited_task_count", "verified_success_count", "success_rate",
        "status_counts", "candidate_usage", "batch_summary_matches", "errors",
    )}, ensure_ascii=False))
    return 0 if report["audit_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

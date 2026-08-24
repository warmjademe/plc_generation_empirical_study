#!/usr/bin/env python3
"""Submit one ISPSoft/COMMGR DVP48ES300R validation job.

The command is run on the experiment host.  A single interactive Windows worker
claims jobs from the shared SSH spool, imports the generated FBU/MPU units into a
clean ISPSoft project, compiles/downloads them, drives DVP-ES3 through COMMGR, and
returns one fail-closed JSON result.  The worker is deliberately serial because
Delta documents only one DVP simulator channel at a time.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import sys
import time
import uuid
from pathlib import Path

METHOD_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = METHOD_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from plc_loop.delta_dvp import (  # noqa: E402
    SourceUnitError,
    build_dvp_harness,
    build_ispsoft_package,
    parse_function_block,
    render_native_ld_function_block_source,
    render_function_block_source,
    render_program_source,
    select_openplc_cases,
    unsaturated_retained_integer_names,
)


TOOL_VERSION = "ISPSoft-3.24+COMMGR-2.11+DVP-ES3+spool-protocol-v2-native-ld"


def emit(document: dict) -> int:
    print(json.dumps(document, ensure_ascii=False, separators=(",", ":")))
    return 0


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def result_artifact_name(role: str) -> str:
    if role not in {"feedback", "sealed"}:
        raise ValueError(f"unsupported DVP result role: {role!r}")
    return f"dvp48es300r_{role}_result.json"


def prepare_job(
    candidate: Path,
    task_dir: Path,
    role: str,
    spool_root: Path,
    password: str,
) -> tuple[str, Path, dict]:
    candidate_bytes = candidate.read_bytes()
    candidate_hash = _sha256_bytes(candidate_bytes)
    source = candidate_bytes.decode("utf-8-sig")
    block = parse_function_block(source)
    ladder_ir_path = candidate.with_name("candidate.ld.json")
    ladder_ir_bytes: bytes | None = None
    native_ld_source: bytes | None = None
    if ladder_ir_path.is_file():
        ladder_ir_bytes = ladder_ir_path.read_bytes()
        try:
            ladder_document = json.loads(ladder_ir_bytes.decode("utf-8-sig"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise SourceUnitError(f"candidate.ld.json is invalid JSON: {exc}") from exc
        native_ld_source = render_native_ld_function_block_source(
            ladder_document,
            (task_dir / "interface.st").read_text(encoding="utf-8"),
            str(block.name),
        ).source
    saturation_advisories = unsaturated_retained_integer_names(block)
    metadata = json.loads((task_dir / "metadata.json").read_text(encoding="utf-8"))
    full_suite = json.loads((task_dir / "openplc_tests.json").read_text(encoding="utf-8"))
    suite = select_openplc_cases(full_suite, role)
    identity_material = b"\0".join((
        candidate_bytes,
        ladder_ir_bytes or b"",
        str(metadata["id"]).encode("utf-8"),
        role.encode("ascii"),
        json.dumps(suite, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"),
    ))
    image_identity_sha256 = _sha256_bytes(identity_material)
    harness = build_dvp_harness(
        block,
        metadata,
        suite,
        image_identity_sha256=image_identity_sha256,
        inline_candidate=native_ld_source is None,
    )

    function_source = native_ld_source or render_function_block_source(block)
    main_source = render_program_source("MAIN", harness.declarations, harness.body)
    package_time = dt.datetime.now()
    function_package = build_ispsoft_package(
        function_source,
        password,
        timestamp=package_time,
    )
    # ISPSoft uses a fixed temporary member name (Unzipped.src).  Its importer
    # may reuse the first extraction when two consecutive units have the same
    # DOS timestamp, so make the program unit one DOS tick newer.
    main_package = build_ispsoft_package(
        main_source,
        password,
        timestamp=package_time + dt.timedelta(seconds=2),
    )
    job_id = f"{int(time.time() * 1000):013d}-{candidate_hash[:12]}-{uuid.uuid4().hex[:10]}"

    staging_root = spool_root / "staging"
    pending_root = spool_root / "pending"
    staging_root.mkdir(parents=True, exist_ok=True)
    pending_root.mkdir(parents=True, exist_ok=True)
    staging = staging_root / job_id
    staging.mkdir()
    (staging / "candidate.st").write_bytes(candidate_bytes)
    if ladder_ir_bytes is not None:
        (staging / "candidate.ld.json").write_bytes(ladder_ir_bytes)
        (staging / "candidate.ispsoft.ld.src").write_bytes(function_source)
    (staging / "candidate.FBU").write_bytes(function_package)
    (staging / "MAIN.MPU").write_bytes(main_package)
    (staging / "suite.json").write_text(
        json.dumps(harness.suite, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "schema_version": 1,
        "job_id": job_id,
        "target": "DVP48ES300R",
        "task_id": metadata["id"],
        "role": role,
        "candidate_sha256": candidate_hash,
        "candidate_language": "ld" if native_ld_source is not None else "st",
        "ladder_ir_sha256": _sha256_bytes(ladder_ir_bytes) if ladder_ir_bytes is not None else None,
        "native_ld_source_sha256": _sha256_bytes(native_ld_source) if native_ld_source is not None else None,
        "execution_adapter": "native-ld-function-block" if native_ld_source is not None else "candidate-body-inlined-into-main",
        "image_identity_sha256": image_identity_sha256,
        "function_unit_sha256": _sha256_bytes(function_package),
        "program_unit_sha256": _sha256_bytes(main_package),
        "suite_sha256": _sha256_file(staging / "suite.json"),
        "expected_toolchain": {
            "ispsoft": "3.24",
            "commgr": "2.11",
            "simulator": "DVP-ES3",
            "driver": "DVP48ES300R_SIM",
        },
        "sealed": role == "sealed",
        "prospective_policy_advisories": [{
            "kind": "retained_int_without_simple_saturation_pattern",
            "variables": list(saturation_advisories),
            "blocking": False,
        }] if saturation_advisories else [],
    }
    (staging / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    pending = pending_root / job_id
    staging.rename(pending)
    return job_id, pending, manifest


def validate_result(document: dict, manifest: dict) -> dict:
    if document.get("schema_version") != 1:
        raise ValueError("Windows result schema_version is not 1")
    for key in ("job_id", "task_id", "role", "candidate_sha256", "target"):
        if document.get(key) != manifest.get(key):
            raise ValueError(f"Windows result {key} does not match submitted job")
    if document.get("status") not in {"pass", "fail", "inconclusive"}:
        raise ValueError("Windows result has an invalid status")
    gates = document.get("gates")
    if not isinstance(gates, list):
        raise ValueError("Windows result has no gate list")
    names = [gate.get("name") for gate in gates]
    required = ["ispsoft_compile", "commgr_connect", "dvp_es3_runtime"]
    if names != required:
        raise ValueError(f"Windows result gate order differs: {names!r}")
    statuses = [gate.get("status") for gate in gates]
    if document["status"] == "pass" and statuses != ["pass", "pass", "pass"]:
        raise ValueError("Windows result claims pass without three passing gates")
    if document["status"] == "fail" and "fail" not in statuses:
        raise ValueError("Windows result claims fail without a failing gate")
    return document


def load_worker_result(
    result_path: Path,
    manifest: dict,
    *,
    poll_seconds: float = 0.1,
    parse_grace_seconds: float = 10.0,
) -> dict:
    """Read a just-published worker result without accepting a partial copy.

    Redirected-drive transports can make the destination name visible before
    the final bytes have arrived.  A transient JSON/identity error is therefore
    retried for a short, bounded interval.  A permanently malformed result is
    still rejected fail-closed.
    """
    started = time.monotonic()
    last_error: Exception | None = None
    while True:
        try:
            return validate_result(
                json.loads(result_path.read_text(encoding="utf-8-sig")), manifest
            )
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            last_error = exc
        if time.monotonic() - started >= max(0.0, parse_grace_seconds):
            assert last_error is not None
            raise last_error
        time.sleep(max(0.01, poll_seconds))


def visible_feedback_evidence(document: dict) -> list[dict]:
    """Normalize worker records into actionable, non-sealed evidence."""
    normalized: list[dict] = []
    for item in document.get("evidence", []):
        if item.get("kind") and item.get("summary"):
            normalized.append(item)
            continue
        status = item.get("status")
        case_id = str(item.get("case_id", "unknown"))
        if status == "pass":
            continue
        if status == "fail":
            normalized.append({
                "kind": "dvp_runtime_failure",
                "summary": f"COMMGR DVP-ES3 case {case_id} violated its output oracle",
                "requirement_ids": list(item.get("requirement_ids", [])),
                "trace": {
                    "case_id": case_id,
                    "repetitions_executed": item.get("repetitions_executed", 0),
                    "failures": list(item.get("failures", []))[:8],
                },
                "oracle_status": "confirmed_candidate_defect",
            })
            continue
        normalized.append({
            "kind": "tool_error",
            "summary": str(item.get("error") or f"COMMGR DVP-ES3 case {case_id} was inconclusive"),
            "trace": {"case_id": case_id},
            "oracle_status": "unconfirmed",
        })
    return normalized


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--task-dir", required=True)
    parser.add_argument("--case-role", choices=("feedback", "sealed"), required=True)
    parser.add_argument(
        "--spool-root",
        help="shared DVP spool; defaults to DELTAPLC_SPOOL_ROOT",
    )
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--poll-seconds", type=float, default=1.0)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()

    candidate = Path(args.candidate).resolve()
    task_dir = Path(args.task_dir).resolve()
    spool_value = args.spool_root or os.environ.get("DELTAPLC_SPOOL_ROOT", "")
    if not spool_value:
        return emit({
            "status": "inconclusive",
            "summary": "DVP validation spool is not configured",
            "evidence": [{
                "kind": "tool_error",
                "summary": "--spool-root and DELTAPLC_SPOOL_ROOT are both absent",
            }],
            "tool_version": TOOL_VERSION,
        })
    spool_root = Path(spool_value).resolve()
    missing = [
        str(path)
        for path in (candidate, task_dir / "metadata.json", task_dir / "openplc_tests.json")
        if not path.exists()
    ]
    if missing:
        return emit({
            "status": "inconclusive",
            "summary": "DVP validator input is incomplete",
            "evidence": [{"kind": "tool_error", "summary": f"missing: {', '.join(missing)}"}],
            "tool_version": TOOL_VERSION,
        })
    password = os.environ.get("DELTAPLC_ISPSOFT_SOURCE_PASSWORD", "")
    if not password:
        return emit({
            "status": "inconclusive",
            "summary": "ISPSoft source-unit packaging is not configured",
            "evidence": [{"kind": "tool_error", "summary": "private source-unit password environment is absent"}],
            "tool_version": TOOL_VERSION,
        })
    try:
        job_id, pending, manifest = prepare_job(
            candidate, task_dir, args.case_role, spool_root, password
        )
    except (OSError, UnicodeError, KeyError, ValueError, SourceUnitError) as exc:
        return emit({
            "status": "fail" if isinstance(exc, SourceUnitError) else "inconclusive",
            "summary": "candidate could not be translated for DVP48ES300R",
            "evidence": [{
                "kind": "dvp_translation_error" if isinstance(exc, SourceUnitError) else "tool_error",
                "summary": f"{type(exc).__name__}: {exc}",
                "oracle_status": "confirmed_candidate_defect" if isinstance(exc, SourceUnitError) else "unconfirmed",
            }],
            "tool_version": TOOL_VERSION,
        })
    if args.prepare_only:
        return emit({
            "status": "inconclusive",
            "summary": "DVP job prepared without execution",
            "evidence": [{"kind": "tool_error", "summary": f"prepared job {job_id}"}],
            "tool_version": TOOL_VERSION,
        })

    result_path = spool_root / "results" / job_id / "result.json"
    deadline = time.monotonic() + max(1, args.timeout_seconds)
    while time.monotonic() < deadline and not result_path.is_file():
        time.sleep(max(0.05, args.poll_seconds))
    if not result_path.is_file():
        return emit({
            "status": "inconclusive",
            "summary": "Windows DVP validation worker did not return before the deadline",
            "evidence": [{"kind": "tool_error", "summary": f"job {job_id} timed out"}],
            "tool_version": TOOL_VERSION,
        })
    try:
        document = load_worker_result(
            result_path,
            manifest,
            poll_seconds=args.poll_seconds,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return emit({
            "status": "inconclusive",
            "summary": "Windows DVP worker returned unverifiable evidence",
            "evidence": [{"kind": "tool_error", "summary": f"{type(exc).__name__}: {exc}"}],
            "tool_version": TOOL_VERSION,
        })
    # Preserve the worker result beside the current validator artifacts without
    # mutating or deleting the immutable spool evidence.
    # Keep role-specific copies so the sealed result cannot overwrite the
    # visible-feedback evidence.  The legacy name is retained for callers that
    # predate the role split; final audits use the role-specific artifacts.
    shutil.copy2(result_path, Path.cwd() / result_artifact_name(args.case_role))
    shutil.copy2(result_path, Path.cwd() / "dvp48es300r_result.json")
    if args.case_role == "sealed":
        # Never expose hidden vectors or mismatches in the command response.
        return emit({
            "status": document["status"],
            "summary": document.get("public_summary", "sealed DVP48ES300R evaluation completed"),
            "evidence": [] if document["status"] == "pass" else [{
                "kind": "dvp_sealed_failure" if document["status"] == "fail" else "tool_error",
                "summary": document.get("public_summary", "sealed DVP evaluation did not pass"),
                "oracle_status": "confirmed_candidate_defect" if document["status"] == "fail" else "unconfirmed",
            }],
            "passed_requirement_ids": document.get("passed_requirement_ids", []) if document["status"] == "pass" else [],
            "dvp_job_id": job_id,
            "tool_version": document.get("tool_version", TOOL_VERSION),
        })
    return emit({
        "status": document["status"],
        "summary": document.get("public_summary", "visible DVP48ES300R evaluation completed"),
        "evidence": visible_feedback_evidence(document),
        "passed_requirement_ids": document.get("passed_requirement_ids", []),
        "dvp_job_id": job_id,
        "tool_version": document.get("tool_version", TOOL_VERSION),
    })


if __name__ == "__main__":
    raise SystemExit(main())

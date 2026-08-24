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
import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import os
import signal
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
    render_deployment_program,
    render_native_ld_function_block_source,
    render_function_block_source,
    render_program_source,
    select_openplc_cases,
    unsaturated_retained_integer_names,
)


TOOL_VERSION = "ISPSoft-3.24+COMMGR-2.11+Delta-simulators+spool-protocol-v2-native-ld"
TARGETS = {
    "DVP48ES300R": {
        "driver": "DVP48ES300R_SIM",
        "simulator": "DVP-ES3",
        "runtime_gate": "dvp_es3_runtime",
        "artifact_prefix": "dvp48es300r",
        "maximum_m": 8191,
    },
    "AS228T-A": {
        "driver": "AS228T_SIM",
        "simulator": "AS200",
        "runtime_gate": "as200_runtime",
        "artifact_prefix": "as228t",
        "maximum_m": 65535,
    },
}

VENDOR_PHASES = {
    "queued": ("等待 Windows 验证 worker", 86),
    "input_check": ("核对候选与测试包完整性", 87),
    "project_load": ("装载 ISPSoft 干净工程", 88),
    "communication_setup": ("绑定对应型号的 COMMGR 通信驱动", 89),
    "program_import": ("导入生成程序与测试 harness", 90),
    "ispsoft_compile": ("使用 ISPSoft 编译工程", 92),
    "controller_download": ("下载程序到台达仿真控制器", 94),
    "commgr_runtime": ("通过 COMMGR 执行仿真输入", 96),
    "oracle_evaluation": ("判定当前仿真用例输出", 97),
    "deployment_compile": ("换入物理 I/O MAIN 并编译交付工程", 98),
    "project_package": ("封装可下载 ISPSoft 工程", 99),
    "result_publish": ("回传厂商验证证据", 99),
    "complete": ("厂商验证已完成", 100),
}


def _read_worker_state(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _worker_snapshot(spool_root: Path, target: str) -> dict:
    """Return the fail-closed capability and queue state of one worker."""

    bridge_root = spool_root.parent
    heartbeat = _read_worker_state(bridge_root / "bridge_heartbeat.json")
    worker = _read_worker_state(bridge_root / "worker_heartbeat.json")
    bootstrap = _read_worker_state(bridge_root / "bootstrap_status.json")
    simulator = _read_worker_state(bridge_root / "simulator_status.json")
    template = _read_worker_state(bridge_root / "as228t_template_status.json")
    health = _read_worker_state(bridge_root / "health_status.json")
    qualification_active = (bridge_root / "qualification_active").is_file()
    qualification_override = os.getenv("DELTAPLC_ALLOW_QUALIFICATION") == "1"

    def fresh(path: Path, seconds: float) -> bool:
        try:
            return time.time() - path.stat().st_mtime <= seconds
        except OSError:
            return False

    pending_root = spool_root / "pending"
    results_root = spool_root / "results"
    common_ready = bool(
        pending_root.is_dir()
        and results_root.is_dir()
        and fresh(bridge_root / "bridge_heartbeat.json", 60)
        and heartbeat.get("status") == "connected"
        and fresh(bridge_root / "worker_heartbeat.json", 30)
        and worker.get("status") == "connected"
        and bootstrap.get("status") in {"worker_started", "worker_already_running"}
        and simulator.get("status") == "ready"
        and simulator.get("commgr_running") is True
        and health.get("state", "ready") not in {"draining", "quarantined"}
        and worker.get("state", "missing") not in {"draining", "recovering"}
        and (not qualification_active or qualification_override)
    )
    target_ready = bool(
        common_ready
        and (
            simulator.get("dvp_simulator_running") is True
            if target == "DVP48ES300R"
            else simulator.get("as200_simulator_running") is True
            and template.get("status") == "ready"
        )
    )
    pending = 0
    if pending_root.is_dir():
        pending = sum(
            1
            for item in pending_root.iterdir()
            if item.is_dir()
            and not (item / "cancelled.json").is_file()
            and not (results_root / item.name / "result.json").is_file()
        )
    return {
        "spool_root": spool_root,
        "worker_id": str(
            worker.get("worker_id")
            or heartbeat.get("worker_id")
            or bridge_root.name
        ),
        "target_ready": target_ready,
        "pending_jobs": pending,
    }


@contextlib.contextmanager
def _worker_pool_lock(spool_roots: list[Path]):
    """Serialize least-queue selection and publication across app processes."""

    identity = "\0".join(sorted(str(path) for path in spool_roots)).encode("utf-8")
    lock_name = hashlib.sha256(identity).hexdigest()[:20]
    lock_root = Path(
        os.getenv("DELTAPLC_POOL_LOCK_ROOT", str(spool_roots[0].parent / ".pool-locks"))
    )
    lock_path = lock_root / (
        f"delta-plc-worker-pool-{lock_name}.lock"
    )
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def select_worker(spool_roots: list[Path], target: str) -> dict:
    """Choose a healthy target-capable worker with the shortest queue."""

    candidates = [
        snapshot
        for snapshot in (_worker_snapshot(root, target) for root in spool_roots)
        if snapshot["target_ready"]
    ]
    if not candidates:
        raise RuntimeError(f"no healthy Windows worker is ready for {target}")
    return min(
        candidates,
        key=lambda item: (int(item["pending_jobs"]), str(item["worker_id"])),
    )


def _read_worker_progress(path: Path, job_id: str) -> list[dict]:
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError):
        return []
    records: list[dict] = []
    for line in lines:
        try:
            value = json.loads(line.lstrip("\ufeff"))
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and str(value.get("job_id", "")) == job_id:
            records.append(value)
    return records


def _append_vendor_progress(
    path: Path,
    *,
    phase: str,
    target: str,
    case_index: int = 0,
    case_total: int = 0,
    result: str | None = None,
) -> None:
    label, percent = VENDOR_PHASES.get(phase, ("执行台达官方工具链验证", 90))
    document = {
        "time": dt.datetime.now(dt.timezone.utc).isoformat(),
        "component": "delta_vendor_validation",
        "status": "completed" if phase == "complete" else "stage",
        "vendor_phase": phase,
        "phase_label": label,
        "phase_percent": percent,
        "target": target,
        "case_index": max(0, int(case_index)),
        "case_total": max(0, int(case_total)),
    }
    if result is not None:
        document["result"] = result
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(document, ensure_ascii=False, separators=(",", ":")) + "\n")


def write_cancellation_marker(pending: Path, job_id: str, reason: str) -> None:
    """Durably tell the serial Windows worker not to execute an orphaned job."""
    document = {
        "schema_version": 1,
        "job_id": job_id,
        "status": "cancelled",
        "reason": reason,
        "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    temporary = pending / f"cancelled.json.tmp-{uuid.uuid4().hex}"
    temporary.write_text(
        json.dumps(document, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    temporary.replace(pending / "cancelled.json")


def emit(document: dict) -> int:
    print(json.dumps(document, ensure_ascii=False, separators=(",", ":")))
    return 0


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def result_artifact_name(role: str, target: str = "DVP48ES300R") -> str:
    if role not in {"feedback", "sealed", "all"}:
        raise ValueError(f"unsupported DVP result role: {role!r}")
    return f"{TARGETS[target]['artifact_prefix']}_{role}_result.json"


def prepare_job(
    candidate: Path,
    task_dir: Path,
    role: str,
    spool_root: Path,
    password: str,
    target: str = "DVP48ES300R",
    worker_id: str | None = None,
) -> tuple[str, Path, dict]:
    target_config = TARGETS[target]
    candidate_bytes = candidate.read_bytes()
    candidate_hash = _sha256_bytes(candidate_bytes)
    source = candidate_bytes.decode("utf-8-sig")
    block = parse_function_block(source)
    ladder_ir_path = candidate.with_name("candidate.ld.json")
    ladder_ir_bytes: bytes | None = None
    native_ld_source: bytes | None = None
    engineering_path = task_dir / "engineering_config.json"
    engineering_config: dict | None = None
    engineering_bytes: bytes | None = None
    if engineering_path.is_file():
        engineering_bytes = engineering_path.read_bytes()
        try:
            loaded_engineering = json.loads(engineering_bytes.decode("utf-8-sig"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise SourceUnitError(f"engineering_config.json is invalid: {exc}") from exc
        if not isinstance(loaded_engineering, dict):
            raise SourceUnitError("engineering_config.json must contain one object")
        engineering_config = loaded_engineering
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
        engineering_bytes or b"",
        str(metadata["id"]).encode("utf-8"),
        role.encode("ascii"),
        target.encode("ascii"),
        json.dumps(suite, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"),
    ))
    image_identity_sha256 = _sha256_bytes(identity_material)
    harness = build_dvp_harness(
        block,
        metadata,
        suite,
        image_identity_sha256=image_identity_sha256,
        # Import and execute the exact deliverable function unit for both ST
        # and LD.  Inlining ST only into the private MAIN harness would validate
        # its body but not the customer-downloadable FBU as an imported unit.
        inline_candidate=False,
        target=target,
        commgr_driver=str(target_config["driver"]),
        maximum_m=int(target_config["maximum_m"]),
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
    deployment_package: bytes | None = None
    deployment_readable: str | None = None
    if engineering_config is not None:
        deployment_declarations, deployment_body, deployment_readable = render_deployment_program(
            block,
            metadata,
            engineering_config,
        )
        deployment_source = render_program_source(
            "MAIN", deployment_declarations, deployment_body
        )
        deployment_package = build_ispsoft_package(
            deployment_source,
            password,
            timestamp=package_time + dt.timedelta(seconds=4),
        )
    # Preserve the exact function unit beside this attempt so the Web service
    # returns the same content-addressed FBU that ISPSoft compiled.  For ST it
    # contains the target-qualified function-block source; for Ladder it is the
    # native [FB,LD] unit emitted from the typed Ladder IR.
    (Path.cwd() / "candidate.ISPSoft.FBU").write_bytes(function_package)
    if deployment_package is not None and deployment_readable is not None:
        (Path.cwd() / "deployment.MPU").write_bytes(deployment_package)
        (Path.cwd() / "deployment_main.st").write_text(
            deployment_readable, encoding="utf-8"
        )
        (Path.cwd() / "engineering_mapping.json").write_text(
            json.dumps(engineering_config, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    if native_ld_source is not None:
        (Path.cwd() / "candidate.ispsoft.ld.src").write_bytes(native_ld_source)
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
    if deployment_package is not None and deployment_readable is not None:
        (staging / "deployment.MPU").write_bytes(deployment_package)
        (staging / "deployment_main.st").write_text(
            deployment_readable, encoding="utf-8"
        )
        (staging / "engineering_mapping.json").write_bytes(engineering_bytes or b"")
    (staging / "suite.json").write_text(
        json.dumps(harness.suite, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "schema_version": 1,
        "job_id": job_id,
        "target": target,
        "worker_id": worker_id or spool_root.parent.name,
        "task_id": metadata["id"],
        "role": role,
        "candidate_sha256": candidate_hash,
        "candidate_language": "ld" if native_ld_source is not None else "st",
        "ladder_ir_sha256": (
            _sha256_bytes(ladder_ir_bytes) if ladder_ir_bytes is not None else None
        ),
        "native_ld_source_sha256": (
            _sha256_bytes(native_ld_source) if native_ld_source is not None else None
        ),
        "execution_adapter": (
            "native-ld-function-block"
            if native_ld_source is not None
            else "st-function-block-instance"
        ),
        "image_identity_sha256": image_identity_sha256,
        "function_unit_sha256": _sha256_bytes(function_package),
        "program_unit_sha256": _sha256_bytes(main_package),
        "delivery_mode": (
            "downloadable_project" if deployment_package is not None else "function_unit"
        ),
        "deployment_program_sha256": (
            _sha256_bytes(deployment_package) if deployment_package is not None else None
        ),
        "engineering_mapping_sha256": (
            _sha256_bytes(engineering_bytes) if engineering_bytes is not None else None
        ),
        "project_name": (
            str(engineering_config.get("project_name")) if engineering_config else None
        ),
        "suite_sha256": _sha256_file(staging / "suite.json"),
        "expected_toolchain": {
            "ispsoft": "3.24",
            "commgr": "2.11",
            "simulator": target_config["simulator"],
            "driver": target_config["driver"],
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
    if document.get("worker_id") != manifest.get("worker_id"):
        raise ValueError("Windows result worker_id does not match assigned worker")
    if document.get("status") not in {"pass", "fail", "inconclusive"}:
        raise ValueError("Windows result has an invalid status")
    gates = document.get("gates")
    if not isinstance(gates, list):
        raise ValueError("Windows result has no gate list")
    names = [gate.get("name") for gate in gates]
    required = [
        "ispsoft_compile",
        "commgr_connect",
        str(TARGETS[manifest["target"]]["runtime_gate"]),
    ]
    if manifest.get("delivery_mode") == "downloadable_project":
        required.append("deployment_compile")
    if names != required:
        raise ValueError(f"Windows result gate order differs: {names!r}")
    statuses = [gate.get("status") for gate in gates]
    if document["status"] == "pass" and statuses != ["pass"] * len(required):
        raise ValueError(
            f"Windows result claims pass without {len(required)} passing gates"
        )
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
            if last_error is None:  # defensive: the read block always sets it
                raise RuntimeError("worker result remained unreadable without a diagnostic")
            raise last_error
        time.sleep(max(0.01, poll_seconds))


def visible_feedback_evidence(document: dict, target: str = "DVP48ES300R") -> list[dict]:
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
                "kind": "delta_runtime_failure",
                "summary": f"COMMGR {TARGETS[target]['simulator']} case {case_id} violated its output oracle",
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
            "summary": str(item.get("error") or f"COMMGR {TARGETS[target]['simulator']} case {case_id} was inconclusive"),
            "trace": {"case_id": case_id},
            "oracle_status": "unconfirmed",
        })
    return normalized


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--task-dir", required=True)
    parser.add_argument("--case-role", choices=("feedback", "sealed", "all"), required=True)
    parser.add_argument("--target", choices=tuple(TARGETS), default="DVP48ES300R")
    parser.add_argument(
        "--spool-root", action="append", dest="spool_roots",
        help="repeatable shared DVP spool; defaults to DELTAPLC_SPOOL_ROOT(S)",
    )
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--poll-seconds", type=float, default=1.0)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()

    candidate = Path(args.candidate).resolve()
    task_dir = Path(args.task_dir).resolve()
    configured = list(args.spool_roots or [])
    if not configured:
        environment_value = (
            os.environ.get("DELTAPLC_SPOOL_ROOTS")
            or os.environ.get("DELTAPLC_SPOOL_ROOT", "")
        )
        configured = [item.strip() for item in environment_value.split(",") if item.strip()]
    if not configured:
        return emit({
            "status": "inconclusive",
            "summary": "DVP validation spool is not configured",
            "evidence": [{
                "kind": "tool_error",
                "summary": "--spool-root and DELTAPLC_SPOOL_ROOT(S) are absent",
            }],
            "tool_version": TOOL_VERSION,
        })
    spool_roots = [Path(value).resolve() for value in configured]
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
        # Preparation-only is an offline packaging operation used by calibration
        # and tests; execution always requires a live, target-capable worker.
        if args.prepare_only:
            worker = {
                "spool_root": spool_roots[0],
                "worker_id": spool_roots[0].parent.name,
            }
            job_id, pending, manifest = prepare_job(
                candidate, task_dir, args.case_role, worker["spool_root"], password,
                args.target, str(worker["worker_id"]),
            )
        else:
            with _worker_pool_lock(spool_roots):
                worker = select_worker(spool_roots, args.target)
                job_id, pending, manifest = prepare_job(
                    candidate, task_dir, args.case_role, worker["spool_root"], password,
                    args.target, str(worker["worker_id"]),
                )
        spool_root = Path(worker["spool_root"])
    except (
        OSError, UnicodeError, KeyError, ValueError, RuntimeError, SourceUnitError
    ) as exc:
        return emit({
            "status": "fail" if isinstance(exc, SourceUnitError) else "inconclusive",
            "summary": f"candidate could not be translated for {args.target}",
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

    artifact_prefix = str(TARGETS[args.target]["artifact_prefix"])
    vendor_progress_path = Path.cwd() / f"{artifact_prefix}_{args.case_role}_vendor_progress.jsonl"
    _append_vendor_progress(vendor_progress_path, phase="queued", target=args.target)

    def cancel_on_signal(signum: int, _frame: object) -> None:
        try:
            write_cancellation_marker(pending, job_id, f"linux_validator_signal_{signum}")
        finally:
            raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, cancel_on_signal)
    signal.signal(signal.SIGINT, cancel_on_signal)

    result_path = spool_root / "results" / job_id / "result.json"
    worker_state_path = spool_root.parent / "worker_state.json"
    worker_progress_path = pending / "worker_progress.jsonl"
    seen_worker_signatures: set[tuple[str, int, int]] = set()
    deadline = time.monotonic() + max(1, args.timeout_seconds)
    while time.monotonic() < deadline and not result_path.is_file():
        worker_records = _read_worker_progress(worker_progress_path, job_id)
        for worker_record in worker_records:
            phase = str(worker_record.get("phase") or "queued")
            case_index = int(worker_record.get("case_index", 0) or 0)
            case_total = int(worker_record.get("case_total", 0) or 0)
            signature = (phase, case_index, case_total)
            if signature in seen_worker_signatures:
                continue
            _append_vendor_progress(
                vendor_progress_path,
                phase=phase,
                target=args.target,
                case_index=case_index,
                case_total=case_total,
            )
            seen_worker_signatures.add(signature)
        worker_state = _read_worker_state(worker_state_path)
        if str(worker_state.get("job_id", "")) == job_id:
            phase = str(worker_state.get("phase") or "queued")
            case_index = int(worker_state.get("case_index", 0) or 0)
            case_total = int(worker_state.get("case_total", 0) or 0)
            signature = (phase, case_index, case_total)
            if signature not in seen_worker_signatures:
                _append_vendor_progress(
                    vendor_progress_path,
                    phase=phase,
                    target=args.target,
                    case_index=case_index,
                    case_total=case_total,
                )
                seen_worker_signatures.add(signature)
        time.sleep(max(0.05, args.poll_seconds))
    # The worker writes its final Oracle/result-publish events immediately
    # before publishing result.json. Drain that append-only stream once more
    # so a fast result hand-off cannot hide the last visualization stages.
    for worker_record in _read_worker_progress(worker_progress_path, job_id):
        phase = str(worker_record.get("phase") or "queued")
        case_index = int(worker_record.get("case_index", 0) or 0)
        case_total = int(worker_record.get("case_total", 0) or 0)
        signature = (phase, case_index, case_total)
        if signature in seen_worker_signatures:
            continue
        _append_vendor_progress(
            vendor_progress_path,
            phase=phase,
            target=args.target,
            case_index=case_index,
            case_total=case_total,
        )
        seen_worker_signatures.add(signature)
    if not result_path.is_file():
        write_cancellation_marker(pending, job_id, "linux_validator_deadline_exceeded")
        _append_vendor_progress(
            vendor_progress_path, phase="complete", target=args.target, result="inconclusive"
        )
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
        _append_vendor_progress(
            vendor_progress_path, phase="complete", target=args.target, result="inconclusive"
        )
        return emit({
            "status": "inconclusive",
            "summary": "Windows DVP worker returned unverifiable evidence",
            "evidence": [{"kind": "tool_error", "summary": f"{type(exc).__name__}: {exc}"}],
            "tool_version": TOOL_VERSION,
        })
    _append_vendor_progress(
        vendor_progress_path,
        phase="complete",
        target=args.target,
        result=str(document.get("status", "inconclusive")),
    )
    # Preserve the worker result beside the current validator artifacts without
    # mutating or deleting the immutable spool evidence.
    # Keep role-specific copies so the sealed result cannot overwrite the
    # visible-feedback evidence.  The legacy name is retained for callers that
    # predate the role split; final audits use the role-specific artifacts.
    shutil.copy2(result_path, Path.cwd() / result_artifact_name(args.case_role, args.target))
    shutil.copy2(result_path, Path.cwd() / f"{artifact_prefix}_result.json")
    result_root = result_path.parent
    for name in (
        "downloadable_project.zip",
        "engineering_mapping.json",
        "deployment_main.st",
        "field_acceptance_checklist.json",
    ):
        source = result_root / name
        if source.is_file():
            shutil.copy2(source, Path.cwd() / name)
    if args.case_role == "sealed":
        # Never expose hidden vectors or mismatches in the command response.
        return emit({
            "status": document["status"],
            "summary": document.get("public_summary", f"sealed {args.target} evaluation completed"),
            "evidence": [] if document["status"] == "pass" else [{
                "kind": "delta_sealed_failure" if document["status"] == "fail" else "tool_error",
                "summary": document.get("public_summary", f"sealed {args.target} evaluation did not pass"),
                "oracle_status": "confirmed_candidate_defect" if document["status"] == "fail" else "unconfirmed",
            }],
            "passed_requirement_ids": document.get("passed_requirement_ids", []) if document["status"] == "pass" else [],
            "delta_job_id": job_id,
            "tool_version": document.get("tool_version", TOOL_VERSION),
        })
    return emit({
        "status": document["status"],
        "summary": document.get("public_summary", f"visible {args.target} evaluation completed"),
        "evidence": visible_feedback_evidence(document, args.target),
        "passed_requirement_ids": document.get("passed_requirement_ids", []),
        "delta_job_id": job_id,
        "tool_version": document.get("tool_version", TOOL_VERSION),
    })


if __name__ == "__main__":
    raise SystemExit(main())

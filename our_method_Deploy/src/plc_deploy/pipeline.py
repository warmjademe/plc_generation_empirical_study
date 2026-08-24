from __future__ import annotations

import json
import hashlib
import fcntl
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import traceback
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from plc_loop.dataset import load_task
from plc_loop.orchestrator import BoundedSynthesisHarness
from plc_loop.cancellation import OperationCancelled, raise_if_cancelled
from plc_loop.delta_dvp import build_engineering_template

from .catalog import Catalog
from .contracts import (
    CONTRACT_ATTEMPT_BUDGET,
    ContractInfrastructureError,
    compile_contract,
    has_passed_semantic_audit,
    write_task_package,
)
from .settings import Settings
from .store import JobStore


_STATUS_DOCUMENT_CACHE: dict[Path, tuple[dict[str, Any], float]] = {}
_STATUS_DOCUMENT_CACHE_LOCK = threading.Lock()


def _read_status_document(
    path: Path,
    *,
    cache_grace_seconds: float = 0,
    attempts: int = 3,
) -> tuple[dict[str, Any], float | None]:
    """Read status JSON without exposing short redirected-drive replace gaps."""
    for attempt in range(max(1, attempts)):
        try:
            document = json.loads(path.read_text(encoding="utf-8-sig"))
            modified_at = path.stat().st_mtime
            if not isinstance(document, dict):
                raise ValueError("status document must be a JSON object")
            with _STATUS_DOCUMENT_CACHE_LOCK:
                _STATUS_DOCUMENT_CACHE[path] = (document, modified_at)
            return document, modified_at
        except (OSError, json.JSONDecodeError, ValueError):
            if attempt + 1 < max(1, attempts):
                time.sleep(0.05)

    if cache_grace_seconds > 0:
        with _STATUS_DOCUMENT_CACHE_LOCK:
            cached = _STATUS_DOCUMENT_CACHE.get(path)
        if cached is not None and time.time() - cached[1] <= cache_grace_seconds:
            return cached
    return {}, None


def _provider_settings(catalog_entry: dict[str, Any]) -> dict[str, Any]:
    provider = dict(catalog_entry)
    provider.pop("id", None)
    provider.pop("label", None)
    provider["name"] = provider.pop("provider")
    return provider


def _supports_native_ladder(vendor_id: str, plc_model_id: str) -> bool:
    return vendor_id == "delta" and plc_model_id in {"DVP48ES300R", "AS228T-A"}


def _delta_official_target(vendor_id: str, plc_model_id: str) -> dict[str, str] | None:
    if vendor_id != "delta":
        return None
    return {
        "DVP48ES300R": {
            "gate": "dvp48es300r",
            "target": "DVP48ES300R",
            "artifact": "dvp48es300r_all_result.json",
            "simulator": "DVP-ES3",
        },
        "AS228T-A": {
            "gate": "as228t",
            "target": "AS228T-A",
            "artifact": "as228t_all_result.json",
            "simulator": "AS200",
        },
    }.get(plc_model_id)


def _validator_config(
    settings: Settings,
    provider: dict[str, Any],
    max_candidates: int,
    vendor_id: str = "generic",
    plc_model_id: str = "generic",
    output_language: str = "st",
    assigned_dvp_spool: Path | None = None,
) -> dict[str, Any]:
    if output_language not in {"st", "ld"}:
        raise ValueError("output_language must be st or ld")
    if output_language == "ld" and not _supports_native_ladder(vendor_id, plc_model_id):
        raise ValueError(
            "native Ladder generation is calibrated only for Delta DVP48ES300R and AS228T-A"
        )
    root = settings.project_root
    tools = settings.tool_root
    delta_target = _delta_official_target(vendor_id, plc_model_id)
    confirmation_name = "openplc_confirmation" if delta_target else "openplc"
    sealed_gate = delta_target["gate"] if delta_target else "openplc"
    required_visible_gates = ["compiler", "plcverif", "openplc_feedback"]
    if delta_target:
        required_visible_gates.append("openplc_confirmation")
    verification_profile = (
        "MatIEC -> PLCverif(native invariants) -> OpenPLC(primary feedback) -> "
        "OpenPLC(confirmation feedback) -> ISPSoft 3.24 compile -> "
        f"COMMGR {delta_target['simulator']} all-case Oracle"
        if delta_target
        else "MatIEC -> PLCverif(native invariants) -> OpenPLC(primary feedback) -> OpenPLC(confirmation feedback)"
    )
    if output_language == "ld":
        verification_profile += "; Ladder IR -> equivalent ST + SVG -> ISPSoft native [FB,LD]"
    validators: list[dict[str, Any]] = [
        {
            "name": "interface", "kind": "interface", "blocking": True,
            "inconclusive_is_blocking": True, "sealed": False,
        },
        {
            "name": "compiler", "kind": "command", "blocking": True, "protocol": "json",
            "version": "matiec-0.1",
            "command": [sys.executable, str(root / "scripts/matiec_validator.py"), "--candidate", "{candidate}",
                        "--iec2iec", str(tools / "matiec/iec2iec")],
        },
        {
            "name": "plcverif", "kind": "command", "blocking": True,
            "inconclusive_is_blocking": True, "protocol": "json", "timeout_seconds": 900,
            "version": "PLCverif-1.0.0.202410210930+nuXmv-2.0.0+CBMC-6.10.0",
            "command": [
                sys.executable, str(root / "scripts/formal_plcverif.py"), "--candidate", "{candidate}",
                "--task-dir", "{task_dir}", "--plcverif", str(tools / "plcverif/plcverif-cli"),
                "--nuxmv", str(tools / "nuXmv-2.0.0-Linux/bin/nuXmv"),
                "--cbmc", str(tools / "cbmc-6.10.0/usr/bin/cbmc"),
                "--timer-library", str(root / "formal_lib/iec_timers_100ms.scl"),
                "--numeric-library", str(root / "formal_lib/iec_numeric_functions.scl"),
                "--property-kind", "all", "--minimum-properties", "1", "--backend-timeout", "120",
                "--cbmc-unwind", "10", "--counterexample-feedback", "actionable", "--case-workers", "1",
            ],
        },
        {
            "name": "openplc_feedback", "kind": "command", "blocking": True,
            "inconclusive_is_blocking": True, "inconclusive_retries": 1,
            "inconclusive_retry_delay_seconds": 1, "protocol": "json", "timeout_seconds": 300,
            "version": "OpenPLC_v3@b5d41356+feedback",
            "command": [
                sys.executable, str(root / "scripts/openplc_sealed_validator.py"), "--candidate", "{candidate}",
                "--task-dir", "{task_dir}", "--docker", "/usr/bin/docker", "--image", settings.openplc_image,
                "--runner", str(root / "scripts/openplc_container_runner.py"), "--case-role", "feedback",
                "--include-failure-prefix",
            ],
        },
        {
            "name": confirmation_name, "kind": "command", "blocking": True,
            "sealed": not delta_target,
            "inconclusive_retries": 1, "inconclusive_retry_delay_seconds": 1,
            "protocol": "json", "timeout_seconds": 420,
            "version": "OpenPLC_v3@b5d41356+confirmation",
            "command": [
                sys.executable, str(root / "scripts/openplc_sealed_validator.py"), "--candidate", "{candidate}",
                "--task-dir", "{task_dir}", "--docker", "/usr/bin/docker", "--image", settings.openplc_image,
                "--runner", str(root / "scripts/openplc_container_runner.py"), "--case-role", "sealed",
                "--include-failure-prefix",
            ],
        },
    ]
    if delta_target:
        validators.append({
            "name": delta_target["gate"], "kind": "command", "blocking": True, "sealed": True,
            "inconclusive_is_blocking": True, "inconclusive_retries": 1,
            "inconclusive_retry_delay_seconds": 5, "protocol": "json",
            "timeout_seconds": settings.dvp_timeout_seconds + 60,
            "version": f"ISPSoft-3.24+COMMGR-2.11.0.14+{delta_target['simulator']}+all-oracle",
            "command": [
                sys.executable, str(root / "scripts/dvp48es300r_validator.py"),
                "--candidate", "{candidate}", "--task-dir", "{task_dir}",
                "--case-role", "all",
                *[
                    token
                    for spool in (
                        (assigned_dvp_spool,)
                        if assigned_dvp_spool is not None
                        else settings.dvp_spool_roots
                    )
                    for token in ("--spool-root", str(spool))
                ],
                "--timeout-seconds", str(settings.dvp_timeout_seconds),
                "--target", delta_target["target"],
            ],
        })
    return {
        "provider": provider,
        "experiment": {
            "method_revision": "production-evidence-loop-v4-st-native-ld",
            "output_language": output_language,
            "max_candidates": max_candidates,
            # Calls that produce no complete assistant candidate are retried in
            # place and therefore do not consume a candidate opportunity.
            "model_call_attempts_per_candidate": 3,
            "max_feedback_chars": 8000,
            "certificate_version": "v3",
            "context_strategy": "state_packet",
            "anchor_policy": "non_regression",
            "repair_policy": "adaptive",
            "pre_emit_review": True,
            "contract_risk_analysis": True,
            "duplicate_candidate_guard": True,
            # Production jobs may use every deterministic validator diagnostic
            # to improve the next candidate.  Unlike the research protocol, the
            # confirmation OpenPLC suite is therefore actionable feedback.
            "sealed_rejection_policy": "feedback_repair",
            "max_sealed_attempts": max_candidates,
            "inconclusive_recovery_policy": "blind_restart" if max_candidates > 1 else "terminal",
            "max_inconclusive_restarts": 1 if max_candidates > 1 else 0,
            "blind_restart_profiles": [
                "contrastive_guard_table",
                "pre_state_event_snapshot",
                "transition_then_decode",
                "minimal_priority_chain",
            ],
            "domain_context": {"enabled": True, "max_cards": 5, "max_chars": 7000},
            "required_visible_gates": required_visible_gates,
            "sealed_gate": sealed_gate,
            "stop_on_visible_pass": True,
            "development_only": False,
            "verification_profile": verification_profile,
        },
        "validators": validators,
        "_config_dir": str(root / "configs"),
        "_config_path": "generated-in-memory",
        "_config_sha256": None,
    }


def _acquire_delta_worker(
    settings: Settings,
    *,
    job_id: str,
    target: str,
    job_root: Path,
    cancel_check: Callable[[], bool],
) -> tuple[Any, Path]:
    """Reserve one healthy Windows VM for the complete user generation job."""

    deadline = time.monotonic() + settings.dvp_timeout_seconds
    assignment_path = job_root / "windows_worker_assignment.json"
    while time.monotonic() < deadline:
        raise_if_cancelled(cancel_check)
        ready_workers = [
            item
            for item in (
                _single_dvp_bridge_readiness(spool)
                for spool in settings.dvp_spool_roots
            )
            if item["targets_ready"].get(target) is True
        ]
        if not ready_workers:
            raise RuntimeError(f"no healthy Windows worker is ready for {target}")
        ready_workers.sort(
            key=lambda item: (int(item.get("pending_jobs", 0)), str(item["worker_id"]))
        )
        for worker in ready_workers:
            spool = Path(worker["spool_root"])
            lock_path = spool.parent / "user_job.lock"
            stream = lock_path.open("a+")
            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                stream.close()
                continue
            document = {
                "job_id": job_id,
                "worker_id": worker["worker_id"],
                "target": target,
                "state": "reserved",
                "acquired_at": datetime.now(timezone.utc).isoformat(),
            }
            assignment_path.write_text(
                json.dumps(document, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            temporary = spool.parent / "active_user_job.json.tmp"
            temporary.write_text(
                json.dumps(document, ensure_ascii=False, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            temporary.replace(spool.parent / "active_user_job.json")
            return stream, spool
        time.sleep(1.0)
    raise RuntimeError(f"timed out waiting for an exclusive Windows worker for {target}")


def _release_delta_worker(lease: tuple[Any, Path] | None, job_id: str) -> None:
    if lease is None:
        return
    stream, spool = lease
    active_path = spool.parent / "active_user_job.json"
    try:
        active, _ = _read_status_document(active_path)
        if active.get("job_id") == job_id:
            active_path.unlink(missing_ok=True)
    finally:
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        finally:
            stream.close()


def _contract_resume_evidence(
    job_root: Path,
) -> tuple[int, dict[str, int | float], int, str | None, str | None]:
    """Recover bounded contract progress without exposing private drafts publicly."""

    trace_path = job_root / "contract_progress.jsonl"
    if not trace_path.is_file():
        return 0, {}, 0, None, None
    max_requested = 0
    received_by_attempt: dict[int, dict[str, Any]] = {}
    last_rejection: dict[str, Any] | None = None
    for line in trace_path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            record = json.loads(line)
            attempt = int(record.get("attempt", 0))
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
        status = str(record.get("status", ""))
        if status == "requesting" and attempt > 0:
            max_requested = max(max_requested, attempt)
        elif status == "received" and attempt > 0:
            received_by_attempt[attempt] = record
        elif status == "rejected" and attempt > 0:
            if last_rejection is None or attempt >= int(last_rejection.get("attempt", 0)):
                last_rejection = record
    usage: dict[str, int | float] = {}
    latency_ms = 0
    for record in received_by_attempt.values():
        latency_ms += int(record.get("latency_ms") or 0)
        for key, value in (record.get("usage") or {}).items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                usage[key] = usage.get(key, 0) + value
    resume_error = str(last_rejection.get("error") or "") if last_rejection else None
    resume_draft = None
    if last_rejection is not None:
        attempt = int(last_rejection["attempt"])
        drafts = list(job_root.glob(f"contract_attempt_{attempt:02d}_rejected*.txt"))
        if drafts:
            resume_draft = max(drafts, key=lambda path: path.stat().st_mtime_ns).read_text(
                encoding="utf-8", errors="replace"
            ).strip()
    return max_requested, usage, latency_ms, resume_draft or None, resume_error or None


def create_contract_job(job_id: str, store: JobStore, catalog: Catalog, settings: Settings,
                        auto_approve_callback: Callable[[str], None] | None = None,
                        approval_delay_seconds: float = 5.0) -> None:
    try:
        raise_if_cancelled(lambda: store.cancellation_requested(job_id))
        job = store.update(job_id, status="contract_generating")
        request = job["request"]
        vendor, plc_model = catalog.target(request["vendor"], request["plc_model"])
        provider = _provider_settings(catalog.model(request["llm_model"]))
        task_id = "PLC_" + job_id.replace("-", "")[:12].upper()
        job_root = settings.data_root / "jobs" / job_id
        job_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        trace_path = job_root / "contract_progress.jsonl"
        (
            attempt_offset,
            prior_usage,
            prior_latency_ms,
            resume_draft,
            resume_error,
        ) = _contract_resume_evidence(job_root)
        if trace_path.exists():
            with trace_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps({
                    "time": datetime.now(timezone.utc).isoformat(),
                    "status": "resumed_after_service_restart",
                }, ensure_ascii=False) + "\n")
        else:
            trace_path.write_text("", encoding="utf-8")
            trace_path.chmod(0o600)

        def record_contract_progress(event: dict[str, Any]) -> None:
            record = dict(event)
            private_draft = record.pop("private_draft", None)
            if isinstance(private_draft, str) and private_draft:
                attempt = int(record.get("attempt", 0))
                draft_path = job_root / f"contract_attempt_{attempt:02d}_rejected.txt"
                if draft_path.exists():
                    draft_path = job_root / (
                        f"contract_attempt_{attempt:02d}_rejected_resume_{time.time_ns()}.txt"
                    )
                draft_path.write_text(private_draft + "\n", encoding="utf-8")
                draft_path.chmod(0o600)
                record["private_draft_sha256"] = hashlib.sha256(
                    private_draft.encode("utf-8")
                ).hexdigest()
            record["time"] = datetime.now(timezone.utc).isoformat()
            with trace_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")

        contract, audit = compile_contract(
            request["requirement"], vendor, plc_model, provider, task_id,
            output_language=request.get("output_language", "st"),
            progress_callback=record_contract_progress,
            cancel_check=lambda: store.cancellation_requested(job_id),
            attempt_offset=attempt_offset,
            attempt_budget=CONTRACT_ATTEMPT_BUDGET - attempt_offset,
            prior_usage=prior_usage,
            prior_latency_ms=prior_latency_ms,
            resume_draft=resume_draft,
            resume_error=resume_error,
        )
        contract["contract_generation"] = audit
        contract["target"] = {
            "vendor": request["vendor"], "vendor_label": vendor["label"],
            "model": request["plc_model"], "model_label": plc_model["label"],
            "verification_scope": plc_model["notes"],
            "output_language": request.get("output_language", "st"),
        }
        contract["delivery_mode"] = request.get("delivery_mode", "function_unit")
        if contract["delivery_mode"] == "downloadable_project":
            contract["engineering_template"] = build_engineering_template(
                contract,
                request["plc_model"],
                project_name=task_id,
            )
        store.update(job_id, status="awaiting_contract_approval", contract=contract)
        if auto_approve_callback is not None:
            deadline = time.monotonic() + max(0.0, approval_delay_seconds)
            while time.monotonic() < deadline:
                raise_if_cancelled(lambda: store.cancellation_requested(job_id))
                time.sleep(min(0.1, max(0.0, deadline - time.monotonic())))
            auto_approve_callback(job_id)
    except OperationCancelled:
        store.update(job_id, status="cancelled", last_error="用户主动取消了生成任务")
    except ContractInfrastructureError as exc:
        store.update(
            job_id,
            status="infrastructure_error",
            last_error=f"{type(exc).__name__}: {exc}",
        )
    except Exception as exc:
        store.update(job_id, status="contract_failed", last_error=f"{type(exc).__name__}: {exc}")


def run_generation_job(job_id: str, store: JobStore, catalog: Catalog, settings: Settings) -> None:
    delta_lease: tuple[Any, Path] | None = None
    try:
        raise_if_cancelled(lambda: store.cancellation_requested(job_id))
        job = store.update(job_id, status="generating")
        request, contract = job["request"], dict(job["contract"] or {})
        if not contract:
            raise RuntimeError("approved job has no frozen contract")
        if not has_passed_semantic_audit(contract):
            raise RuntimeError(
                "approved job contract has no current deterministic semantic audit"
            )
        contract.setdefault("oracle_provenance", "user_confirmed_llm_draft")
        job_root = settings.data_root / "jobs" / job_id
        task_root = job_root / "task" / contract["task_id"]
        run_root = job_root / "run"
        job_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not task_root.exists():
            write_task_package(
                task_root, contract, request["requirement"], request["vendor"], request["plc_model"]
            )
        else:
            persisted_contract = json.loads(
                (task_root / "contract.json").read_text(encoding="utf-8")
            )
            if persisted_contract.get("task_id") != contract.get("task_id"):
                raise RuntimeError("persisted task package belongs to another contract")
        delta_target = _delta_official_target(request["vendor"], request["plc_model"])
        if delta_target is not None:
            delta_lease = _acquire_delta_worker(
                settings,
                job_id=job_id,
                target=delta_target["target"],
                job_root=job_root,
                cancel_check=lambda: store.cancellation_requested(job_id),
            )
        provider = _provider_settings(catalog.model(request["llm_model"]))
        config = _validator_config(
            settings,
            provider,
            int(request["max_candidates"]),
            request["vendor"],
            request["plc_model"],
            request.get("output_language", "st"),
            assigned_dvp_spool=delta_lease[1] if delta_lease is not None else None,
        )
        (job_root / "effective_config.json").write_text(
            json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        harness = BoundedSynthesisHarness(
            config,
            load_task(task_root),
            run_root,
            "evidence",
            cancel_check=lambda: store.cancellation_requested(job_id),
        )
        result = harness.run(resume=(run_root / "ledger.jsonl").is_file())
        attempt_dirs = sorted((run_root / "attempts").glob("attempt_*"))
        output_language = request.get("output_language", "st")
        final_attempt = _select_final_attempt(
            attempt_dirs,
            output_language,
            result.get("winning_attempt"),
        )
        final_source_path = (
            final_attempt / "candidate.ld.json"
            if final_attempt is not None and output_language == "ld"
            else final_attempt / "candidate.st" if final_attempt is not None else None
        )
        final_program = (
            final_source_path.read_text(encoding="utf-8")
            if final_source_path is not None and final_source_path.is_file()
            else None
        )
        public_result = {
            key: result.get(key) for key in (
                "status", "success", "candidate_budget", "candidates_used", "stopped_early",
                "requested_model", "resolved_models", "usage_total", "winning_attempt",
                "verification_profile", "sealed_result",
            )
        }
        public_result["target"] = contract["target"]
        public_result["output_language"] = output_language
        public_result["final_attempt"] = (
            int(final_attempt.name.rsplit("_", 1)[-1]) if final_attempt else None
        )
        public_result["vendor_validation"] = _vendor_validation_result(
            result,
            run_root,
            request["vendor"],
            request["plc_model"],
        )
        if final_attempt is not None:
            _write_delivery_manifest(
                final_attempt,
                job_id=job_id,
                request=request,
                contract=contract,
                result=public_result,
            )
        public_result["artifacts"] = _public_artifacts(job_id, final_attempt, output_language)
        terminal_status = (
            "verified_success" if result["success"]
            else "infrastructure_error" if result["status"] in {"infrastructure_error", "sealed_inconclusive"}
            else "generation_failed"
        )
        store.update(
            job_id,
            status=terminal_status,
            result=public_result,
            final_program=final_program,
            last_error=None if result["success"] else _last_failure(result),
        )
    except OperationCancelled:
        store.update(job_id, status="cancelled", last_error="用户主动取消了生成任务")
    except Exception as exc:
        job_root = settings.data_root / "jobs" / job_id
        job_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        (job_root / "service_exception.log").write_text(traceback.format_exc(), encoding="utf-8")
        store.update(job_id, status="infrastructure_error", last_error=f"{type(exc).__name__}: {exc}")
    finally:
        _release_delta_worker(delta_lease, job_id)


def _last_failure(result: dict[str, Any]) -> str:
    if result.get("last_error"):
        return _public_generation_failure(str(result["last_error"]))
    attempts = result.get("attempts") or []
    if not attempts:
        return f"generation ended with {result.get('status', 'unknown status')}"
    # Report the deepest validation stage reached by any candidate.  Reporting
    # only the final candidate can hide a later-stage infrastructure problem
    # behind a subsequent early compiler failure after a bounded restart.
    gate_rank = {
        "response_format": 0,
        "interface": 1,
        "compiler": 2,
        "plcverif": 3,
        "openplc_feedback": 4,
        "openplc_confirmation": 5,
        "openplc": 5,
        "dvp48es300r": 6,
        "as228t": 6,
        "deployment_compile": 7,
    }
    failures: list[tuple[int, int, str]] = []
    for attempt_index, attempt in enumerate(attempts):
        for gate in attempt.get("gates") or []:
            if gate.get("status") not in {"fail", "inconclusive"}:
                continue
            name = str(gate.get("name", "validator"))
            summary = str(gate.get("summary") or f"{name} validation failed")
            failures.append((gate_rank.get(name, 0), attempt_index, summary))
    if failures:
        return _public_generation_failure(max(failures)[2])
    return f"generation ended with {result.get('status')}"


def _public_generation_failure(error: str) -> str:
    """Translate provider/infrastructure diagnostics without leaking internals."""

    lowered = error.casefold()
    if any(marker in lowered for marker in (
        "network unreachable", "name resolution", "temporary failure in name",
        "connection refused", "connection reset", "urlopen error",
        "provider request failed after transport retries",
        "provider streaming request failed without retry",
    )):
        return "大语言模型网络连接在重试后仍不可用；任务已安全终止，请在网络恢复后重新提交。"
    match = re.search(r"(?:provider\s+)?http\s+(\d{3})", error, re.IGNORECASE)
    if match:
        status = int(match.group(1))
        if status == 429:
            return "大语言模型服务当前限流；任务已安全终止，请稍后重新提交。"
        if status >= 500:
            return f"大语言模型上游服务返回 HTTP {status}；任务已安全终止，请稍后重试。"
    if "unexpected model" in lowered:
        return "大语言模型服务返回了与所选模型不一致的标识；系统已拒绝该结果。"
    if any(marker in lowered for marker in (
        "output-token limit", "empty assistant content", "no complete candidate",
    )):
        return "大语言模型在限定重试内未返回完整程序；请重新提交或改用当前在线的其他模型。"
    return error[:800]


def _select_final_attempt(
    attempt_dirs: list[Path],
    output_language: str,
    winning_attempt: Any,
) -> Path | None:
    """Choose the winner, or the latest candidate that was actually parseable."""

    source_name = "candidate.ld.json" if output_language == "ld" else "candidate.st"
    by_number = {
        int(path.name.rsplit("_", 1)[-1]): path
        for path in attempt_dirs
        if path.name.rsplit("_", 1)[-1].isdigit()
    }
    if isinstance(winning_attempt, int):
        winner = by_number.get(winning_attempt)
        if winner is not None:
            source = winner / source_name
            if source.is_file() and source.stat().st_size > 0:
                return winner
    for attempt in reversed(attempt_dirs):
        source = attempt / source_name
        if source.is_file() and source.stat().st_size > 0:
            return attempt
    return None


def _public_artifacts(
    job_id: str,
    attempt_dir: Path | None,
    output_language: str,
) -> list[dict[str, str]]:
    if attempt_dir is None:
        return []
    definitions = (
        [
            ("ld-json", "梯形图源文件（Ladder IR）", "candidate.ld.json"),
            ("ld-svg", "梯形图预览（SVG）", "candidate.ld.svg"),
            ("lowered-st", "等价 ST 验证程序", "candidate.st"),
            ("ispsoft-fbu", "ISPSoft 原生梯形图功能块", "candidate.ISPSoft.FBU"),
        ]
        if output_language == "ld"
        else [
            ("st", "Structured Text 程序", "candidate.st"),
            ("ispsoft-fbu", "所选台达型号 ISPSoft 功能块", "candidate.ISPSoft.FBU"),
        ]
    )
    definitions.append(
        ("delivery-manifest", "型号绑定与验证清单", "delivery_manifest.json")
    )
    definitions.extend([
        ("ispsoft-project", "可下载 ISPSoft 工程包", "downloadable_project.zip"),
        ("engineering-mapping", "物理 I/O 映射表", "engineering_mapping.json"),
        ("deployment-main", "生产 MAIN 程序", "deployment_main.st"),
        ("field-checklist", "真实 PLC 点检与验收清单", "field_acceptance_checklist.json"),
    ])
    return [
        {
            "kind": kind,
            "label": label,
            "url": f"/api/jobs/{job_id}/artifacts/{kind}",
        }
        for kind, label, name in definitions
        if (attempt_dir / name).is_file()
    ]


def _write_delivery_manifest(
    attempt_dir: Path,
    *,
    job_id: str,
    request: dict[str, Any],
    contract: dict[str, Any],
    result: dict[str, Any],
) -> None:
    artifact_names = (
        "candidate.st",
        "candidate.ld.json",
        "candidate.ld.svg",
        "candidate.ISPSoft.FBU",
        "downloadable_project.zip",
        "engineering_mapping.json",
        "deployment_main.st",
        "field_acceptance_checklist.json",
    )
    artifacts = []
    for name in artifact_names:
        path = attempt_dir / name
        if path.is_file():
            artifacts.append({
                "name": name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "size_bytes": path.stat().st_size,
            })
    manifest = {
        "schema_version": 1,
        "job_id": job_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "target": {
            "vendor": request["vendor"],
            "controller": request["plc_model"],
            "compatibility_profile": contract["target"]["verification_scope"],
        },
        "output_language": request.get("output_language", "st"),
        "verified_success": bool(result.get("success")),
        "verification_profile": result.get("verification_profile"),
        "vendor_validation": result.get("vendor_validation"),
        "artifacts": artifacts,
        "delivery_level": (
            "ispsoft_compiled_downloadable_project"
            if (attempt_dir / "downloadable_project.zip").is_file()
            else "target_qualified_function_unit"
        ),
        "field_boundary": (
            "The downloadable ISPSoft project contains the user-confirmed built-in I/O mapping "
            "and has passed target compilation. Cabinet wiring, independent safety circuits, "
            "real-controller download, I/O point checks, and site commissioning remain mandatory."
            if (attempt_dir / "downloadable_project.zip").is_file()
            else "Physical I/O mapping and site engineering were not supplied; this delivery is a target-qualified function unit."
        ),
    }
    (attempt_dir / "delivery_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _vendor_validation_result(
    result: dict[str, Any],
    run_root: Path,
    vendor_id: str,
    plc_model_id: str,
) -> dict[str, Any]:
    delta_target = _delta_official_target(vendor_id, plc_model_id)
    if delta_target is None:
        return {
            "status": "not_run",
            "reason": "No official vendor compiler/simulator is configured for this controller.",
        }
    sealed_attempts = list(result.get("sealed_attempts") or [])
    sealed = result.get("sealed_result")
    attempt_number = None
    if sealed_attempts:
        attempt_number = int(sealed_attempts[-1]["attempt"])
        sealed = sealed or sealed_attempts[-1].get("result")
    if not isinstance(sealed, dict) or sealed.get("name") != delta_target["gate"]:
        return {
            "status": "not_run",
            "reason": "The candidate did not reach the ISPSoft/COMMGR gate.",
        }
    worker: dict[str, Any] = {}
    if attempt_number is not None:
        worker_path = (
            run_root / "attempts" / f"attempt_{attempt_number:02d}"
            / delta_target["artifact"]
        )
        try:
            loaded = json.loads(worker_path.read_text(encoding="utf-8-sig"))
            if isinstance(loaded, dict):
                worker = loaded
        except (OSError, json.JSONDecodeError):
            worker = {}
    status = str(sealed.get("status", "inconclusive"))
    return {
        "status": {"pass": "passed", "fail": "failed"}.get(status, "inconclusive"),
        "target": f"Delta {delta_target['target']}",
        "toolchain": f"ISPSoft 3.24 + COMMGR 2.11.0.14 + {delta_target['simulator']} Simulator",
        "summary": str(sealed.get("summary") or worker.get("public_summary") or ""),
        "tool_version": sealed.get("tool_version") or worker.get("tool_version"),
        "job_id": worker.get("job_id"),
        "gates": [
            {"name": item.get("name"), "status": item.get("status")}
            for item in worker.get("gates", [])
            if isinstance(item, dict)
        ],
        "delivery": worker.get("delivery") if isinstance(worker.get("delivery"), dict) else None,
    }


def _single_dvp_bridge_readiness(spool_root: Path) -> dict[str, Any]:
    bridge_root = spool_root.parent
    bootstrap_path = bridge_root / "bootstrap_status.json"
    heartbeat_path = bridge_root / "bridge_heartbeat.json"
    simulator_path = bridge_root / "simulator_status.json"
    as_template_path = bridge_root / "as228t_template_status.json"
    worker_heartbeat_path = bridge_root / "worker_heartbeat.json"
    endpoint_path = bridge_root / "worker_endpoint.json"
    health_path = bridge_root / "health_status.json"
    qualification_active = (bridge_root / "qualification_active").is_file()
    bootstrap, _ = _read_status_document(bootstrap_path)
    simulator, _ = _read_status_document(simulator_path)
    as_template, _ = _read_status_document(as_template_path)
    heartbeat, heartbeat_mtime = _read_status_document(
        heartbeat_path, cache_grace_seconds=60
    )
    worker_heartbeat, worker_heartbeat_mtime = _read_status_document(
        worker_heartbeat_path, cache_grace_seconds=30
    )
    endpoint, _ = _read_status_document(endpoint_path)
    health, _ = _read_status_document(health_path)
    active_user_job, _ = _read_status_document(bridge_root / "active_user_job.json")
    heartbeat_fresh = bool(
        heartbeat_mtime is not None and time.time() - heartbeat_mtime <= 60
    )
    worker_heartbeat_fresh = bool(
        worker_heartbeat_mtime is not None
        and time.time() - worker_heartbeat_mtime <= 30
    )
    spool_ready = all(
        (spool_root / name).is_dir() for name in ("pending", "results")
    )
    bootstrap_ready = bootstrap.get("status") in {
        "worker_started", "worker_already_running"
    }
    admitted = (
        health.get("state", "ready") not in {"draining", "quarantined"}
        and worker_heartbeat.get("state", "missing") not in {"draining", "recovering"}
        and not qualification_active
    )
    value = {
        "ready": bool(
            heartbeat_fresh
            and worker_heartbeat_fresh
            and spool_ready
            and bootstrap_ready
            and simulator.get("status") == "ready"
            and simulator.get("commgr_running") is True
            and simulator.get("dvp_simulator_running") is True
            and simulator.get("as200_simulator_running") is True
            and admitted
        ),
        "heartbeat_fresh": heartbeat_fresh,
        "worker_heartbeat_fresh": worker_heartbeat_fresh,
        "spool_ready": spool_ready,
        "worker_status": bootstrap.get("status", "missing"),
        "worker_state": worker_heartbeat.get("state", "missing"),
        "bridge_status": heartbeat.get("status", "missing"),
        "simulator_status": simulator.get("status", "missing"),
        "commgr_running": simulator.get("commgr_running", False),
        "dvp_simulator_running": simulator.get("dvp_simulator_running", False),
        "as200_simulator_running": simulator.get("as200_simulator_running", False),
        "as228t_template_ready": as_template.get("status") == "ready",
        "spool_root": str(spool_root),
        "worker_id": str(
            worker_heartbeat.get("worker_id")
            or endpoint.get("worker_id")
            or bridge_root.name
        ),
        "address": endpoint.get("address"),
        "port": endpoint.get("port"),
        "admission_state": (
            "qualification" if qualification_active else health.get("state", "ready")
        ),
        "health_reason": health.get("reason", ""),
        "busy": bool(active_user_job.get("job_id")),
        "active_target": active_user_job.get("target"),
        "active_since": active_user_job.get("acquired_at"),
        "pending_jobs": sum(
            1
            for item in (spool_root / "pending").iterdir()
            if item.is_dir()
            and not (item / "cancelled.json").is_file()
            and not (spool_root / "results" / item.name / "result.json").is_file()
        ) if spool_ready else 0,
    }
    value["targets_ready"] = {
        "DVP48ES300R": bool(
            heartbeat_fresh and worker_heartbeat_fresh and spool_ready and bootstrap_ready
            and value["commgr_running"] and value["dvp_simulator_running"] and admitted
        ),
        "AS228T-A": bool(
            heartbeat_fresh and worker_heartbeat_fresh and spool_ready and bootstrap_ready
            and value["commgr_running"] and value["as200_simulator_running"]
            and value["as228t_template_ready"]
            and admitted
        ),
    }
    return value


def dvp_bridge_readiness(settings: Settings) -> dict[str, Any]:
    workers = [_single_dvp_bridge_readiness(root) for root in settings.dvp_spool_roots]
    primary = dict(workers[0])
    primary["workers"] = workers
    primary["worker_count"] = len(workers)
    primary["ready_worker_count"] = sum(any(item["targets_ready"].values()) for item in workers)
    primary["targets_ready"] = {
        target: any(item["targets_ready"][target] for item in workers)
        for target in ("DVP48ES300R", "AS228T-A")
    }
    primary["ready"] = any(primary["targets_ready"].values())
    primary["dvp_simulator_running"] = any(
        item["dvp_simulator_running"] for item in workers
    )
    primary["as200_simulator_running"] = any(
        item["as200_simulator_running"] for item in workers
    )
    primary["as228t_template_ready"] = any(
        item["as228t_template_ready"] for item in workers
    )
    return primary


def _tcp_endpoint_status(host: str, port: int, timeout_seconds: float = 1.0) -> dict[str, Any]:
    """Return a credential-free TCP reachability measurement for the dashboard."""

    started = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            pass
    except OSError as exc:
        return {
            "online": False,
            "latency_ms": int((time.monotonic() - started) * 1000),
            "detail": exc.__class__.__name__,
        }
    return {
        "online": True,
        "latency_ms": max(1, int((time.monotonic() - started) * 1000)),
        "detail": "tcp_connected",
    }


def delta_validation_status(settings: Settings) -> dict[str, Any]:
    """Return a public, credential-free health view for both Delta targets."""
    bridge = dvp_bridge_readiness(settings)
    host_probe = _tcp_endpoint_status(
        settings.validation_host_public_address,
        settings.validation_host_public_port,
    )
    worker_views = []
    for index, item in enumerate(bridge.get("workers") or [bridge]):
        address = item.get("address") or (
            settings.validation_guest_address if index == 0 else None
        )
        port = int(item.get("port") or settings.validation_guest_port)
        guest_probe = (
            _tcp_endpoint_status(str(address), port)
            if address else {"online": False, "latency_ms": 0, "detail": "missing_endpoint"}
        )
        worker_views.append({
            "name": str(
                item.get("worker_id")
                if item.get("address")
                else "vps_windows" if index == 0 else f"vps_windows_{index + 1}"
            ),
            "address": address,
            "port": port,
            "transport_online": guest_probe["online"],
            "latency_ms": guest_probe["latency_ms"],
            "ready": bool(any(item["targets_ready"].values()) and guest_probe["online"]),
            "connection": item["bridge_status"],
            "worker": item["worker_status"],
            "worker_state": item["worker_state"],
            "heartbeat": "fresh" if item["heartbeat_fresh"] else "stale",
            "worker_heartbeat": "fresh" if item["worker_heartbeat_fresh"] else "stale",
            "admission_state": item.get("admission_state", "ready"),
            "pending_jobs": item.get("pending_jobs", 0),
            "busy": bool(item.get("busy")),
            "active_target": item.get("active_target"),
            "active_since": item.get("active_since"),
            "simulator_status": item.get("simulator_status", "missing"),
            "commgr_running": bool(item.get("commgr_running")),
            "dvp_simulator_running": bool(item.get("dvp_simulator_running")),
            "as200_simulator_running": bool(item.get("as200_simulator_running")),
            "as228t_template_ready": bool(item.get("as228t_template_ready")),
            "targets_ready": {
                target: bool(ready and guest_probe["online"])
                for target, ready in item["targets_ready"].items()
            },
        })
    primary_worker = worker_views[0]
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "host": {
            "name": "kemei",
            "address": settings.validation_host_public_address,
            "port": settings.validation_host_public_port,
            **host_probe,
        },
        "windows_worker": primary_worker,
        "windows_workers": worker_views,
        "controllers": {
            "DVP48ES300R": {
                "ready": any(item["targets_ready"]["DVP48ES300R"] for item in worker_views),
                "ready_workers": sum(item["targets_ready"]["DVP48ES300R"] for item in worker_views),
                "compiler": "ISPSoft 3.24",
                "runtime": "COMMGR DVP-ES3 Simulator",
                "simulator_running": bridge["dvp_simulator_running"],
            },
            "AS228T-A": {
                "ready": (
                    any(item["targets_ready"]["AS228T-A"] for item in worker_views)
                ),
                "ready_workers": sum(item["targets_ready"]["AS228T-A"] for item in worker_views),
                "compiler": "ISPSoft 3.24",
                "runtime": "COMMGR AS200 Simulator",
                "simulator_running": bridge["as200_simulator_running"],
                "template_ready": bridge["as228t_template_ready"],
            },
        },
    }


def readiness(settings: Settings, catalog: Catalog) -> dict[str, Any]:
    checks = {
        "matiec": settings.tool_root / "matiec/iec2iec",
        "plcverif": settings.tool_root / "plcverif/plcverif-cli",
        "nuxmv": settings.tool_root / "nuXmv-2.0.0-Linux/bin/nuXmv",
        "cbmc": settings.tool_root / "cbmc-6.10.0/usr/bin/cbmc",
        "docker": Path("/usr/bin/docker"),
        "java": Path(shutil.which("java") or "/missing/java"),
    }
    tools = {name: path.is_file() and os.access(path, os.X_OK) for name, path in checks.items()}
    try:
        image = subprocess.run(
            ["/usr/bin/docker", "image", "inspect", settings.openplc_image],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, check=False,
        ).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        image = False
    tools["openplc_image"] = image
    models = {item["id"]: bool(os.getenv(item["api_key_env"])) for item in catalog.models}
    return {
        "ready": all(tools.values()) and any(models.values()),
        "tools": tools,
        "models_configured": models,
        "dvp48es300r_bridge": dvp_bridge_readiness(settings),
    }

#!/usr/bin/env python3
"""Run a bounded post-release model acceptance matrix.

The script uses the protected local API, submits all cases before polling, and
writes only sanitized task outcomes.  Provider credentials and hidden Oracle
details are never copied into the report.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TERMINAL = {
    "verified_success",
    "generation_failed",
    "contract_failed",
    "infrastructure_error",
    "cancelled",
}

CASES = (
    {
        "name": "dvp_st_latched_motor_alarm",
        "plc_model": "DVP48ES300R",
        "output_language": "st",
        "requirement": (
            "输入 Start、Stop、Overload、Reset 均为 BOOL；输出 MotorRun、FaultAlarm 均为 BOOL。"
            "初始 MotorRun=FALSE、FaultAlarm=FALSE。Start 在 Stop=FALSE 且 Overload=FALSE 时置位并保持 MotorRun；"
            "Stop 或 Overload 清除 MotorRun，二者优先于 Start。Overload 置位并锁存 FaultAlarm；仅当 Overload=FALSE "
            "且 Reset=TRUE 时清除 FaultAlarm，Overload 与 Reset 同时出现时 Overload 优先。"
        ),
    },
    {
        "name": "dvp_ld_dual_motor_interlock",
        "plc_model": "DVP48ES300R",
        "output_language": "ld",
        "requirement": (
            "输入 Enable、SelectA、SelectB、EmergencyStop 均为 BOOL；输出 MotorA、MotorB 均为 BOOL。"
            "初始两个输出均为 FALSE。Enable=TRUE、EmergencyStop=FALSE 且仅 SelectA=TRUE 时 MotorA=TRUE；"
            "相同条件下仅 SelectB=TRUE 时 MotorB=TRUE。SelectA 与 SelectB 同时为 TRUE 时两个电机均停止，"
            "EmergencyStop 具有最高优先级，两个输出不得同时为 TRUE；无保持状态。"
        ),
    },
    {
        "name": "as_st_two_stage_sequence",
        "plc_model": "AS228T-A",
        "output_language": "st",
        "requirement": (
            "输入 Start、Stage1Done、Stage2Done、Stop、Reset 均为 BOOL；输出 Stage1Run、Stage2Run、Complete 均为 BOOL。"
            "上电初始三个输出均为 FALSE。Start 置位并保持 Stage1Run；Stage1Done 清除 Stage1Run并置位保持 Stage2Run；"
            "Stage2Done 清除 Stage2Run并置位保持 Complete。Reset 清除全部状态；Stop 清除两个运行输出但不清除 Complete。"
            "Reset 优先级最高，其次 Stop，再次完成信号，最后 Start；同时输入按此优先级处理。"
        ),
    },
    {
        "name": "as_ld_valve_mode_safety",
        "plc_model": "AS228T-A",
        "output_language": "ld",
        "requirement": (
            "输入 AutoMode、ManualMode、AutoRequest、ManualRequest、PressureOK、EmergencyStop 均为 BOOL；"
            "输出 ValveOpen、WarningLamp 均为 BOOL。初始两个输出均为 FALSE。AutoMode=TRUE、ManualMode=FALSE、"
            "AutoRequest=TRUE、PressureOK=TRUE 且 EmergencyStop=FALSE 时 ValveOpen=TRUE；ManualMode=TRUE、"
            "AutoMode=FALSE、ManualRequest=TRUE 且 EmergencyStop=FALSE 时 ValveOpen=TRUE。"
            "AutoMode 与 ManualMode 同时为 TRUE 或 EmergencyStop=TRUE 时 ValveOpen=FALSE；"
            "AutoMode 与 ManualMode 同时为 TRUE 或 EmergencyStop=TRUE 时 WarningLamp=TRUE。安全停止优先，"
            "无保持状态。"
        ),
    },
    {
        "name": "dvp_st_fan_alarm_reset",
        "plc_model": "DVP48ES300R",
        "output_language": "st",
        "requirement": (
            "输入 Enable、Stop、OverTemperature、Reset 均为 BOOL；输出 FanRun、Alarm 均为 BOOL。"
            "初始两个输出均为 FALSE。Enable=TRUE、Stop=FALSE、OverTemperature=FALSE 时 FanRun=TRUE；"
            "Stop 或 OverTemperature 立即令 FanRun=FALSE，且优先于 Enable。OverTemperature 置位并保持 Alarm；"
            "仅当 OverTemperature=FALSE 且 Reset=TRUE 时清除 Alarm。Reset 不得直接启动风机，无其他保持状态。"
        ),
    },
)


def call(
    base_url: str,
    token: str,
    method: str,
    path: str,
    payload: dict | None = None,
    *,
    extra_headers: dict[str, str] | None = None,
    timeout: float = 30,
) -> dict:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"X-API-Key": token, "Content-Type": "application/json"}
    headers.update(extra_headers or {})
    request = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=body,
        method=method,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"{method} {path} returned HTTP {exc.code}: {detail}") from exc


def retryable_submission_error(exc: BaseException) -> bool:
    """Return whether a failed submission is safe to replay with its idempotency key."""

    if isinstance(exc, (TimeoutError, urllib.error.URLError)):
        return True
    message = str(exc).lower()
    return any(
        marker in message
        for marker in (
            "http 429",
            "http 502",
            "http 503",
            "http 504",
            "model_unavailable",
        )
    )


def resilient_call(
    base_url: str,
    token: str,
    method: str,
    path: str,
    payload: dict | None = None,
    *,
    extra_headers: dict[str, str] | None = None,
    timeout: float = 30,
    attempts: int = 10,
    backoff_seconds: float = 2.0,
) -> dict:
    """Retry transient API outages without changing the server-side operation."""

    for attempt in range(1, attempts + 1):
        try:
            return call(
                base_url,
                token,
                method,
                path,
                payload,
                extra_headers=extra_headers,
                timeout=timeout,
            )
        except Exception as exc:
            if attempt == attempts or not retryable_submission_error(exc):
                raise
            time.sleep(min(backoff_seconds * attempt, 30.0))
    raise AssertionError("unreachable")


def write_json_atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:18081")
    parser.add_argument(
        "--model",
        choices=("deepseek-v4-pro", "sonnet-5"),
        default="deepseek-v4-pro",
    )
    parser.add_argument("--max-candidates", type=int, default=8)
    parser.add_argument(
        "--delivery-mode",
        choices=("downloadable_project", "function_unit"),
        default="downloadable_project",
    )
    parser.add_argument("--timeout-seconds", type=int, default=3600)
    parser.add_argument("--poll-seconds", type=float, default=5.0)
    parser.add_argument("--submission-attempts", type=int, default=6)
    parser.add_argument("--submission-backoff-seconds", type=float, default=15.0)
    parser.add_argument(
        "--resume",
        action="store_true",
        help="resume polling jobs from the atomic checkpoint beside --output",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--case",
        action="append",
        choices=[item["name"] for item in CASES],
        help="run only the named case; repeat to select multiple cases",
    )
    args = parser.parse_args()
    if not 1 <= args.max_candidates <= 20:
        parser.error("--max-candidates must be in 1..20")
    if not 1 <= args.submission_attempts <= 20:
        parser.error("--submission-attempts must be in 1..20")
    if not 0 <= args.submission_backoff_seconds <= 300:
        parser.error("--submission-backoff-seconds must be in 0..300")
    token = os.environ.get("PLC_WEB_API_TOKEN", "")
    if not token:
        parser.error("PLC_WEB_API_TOKEN is required")

    started = time.monotonic()
    selected_cases = tuple(
        item for item in CASES if not args.case or item["name"] in set(args.case)
    )
    checkpoint_path = args.output.with_name(args.output.name + ".checkpoint.json")
    jobs: list[dict[str, Any]] = []
    if args.resume:
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        if (
            checkpoint.get("model") != args.model
            or checkpoint.get("delivery_mode") != args.delivery_mode
            or int(checkpoint.get("max_candidates", 0)) != args.max_candidates
        ):
            raise RuntimeError("checkpoint configuration does not match requested matrix")
        jobs = list(checkpoint.get("jobs") or [])
        if not jobs:
            raise RuntimeError("checkpoint contains no jobs")
        print(f"resumed {len(jobs)} jobs from {checkpoint_path}", flush=True)
    existing_cases = {str(item.get("case", {}).get("name", "")) for item in jobs}
    cases_to_submit = (
        tuple(case for case in selected_cases if case["name"] not in existing_cases)
        if args.resume else selected_cases
    )
    if cases_to_submit:
        for case in cases_to_submit:
            payload = {
                "requirement": case["requirement"],
                "vendor": "delta",
                "plc_model": case["plc_model"],
                "llm_model": args.model,
                "output_language": case["output_language"],
                "delivery_mode": args.delivery_mode,
                "max_candidates": args.max_candidates,
            }
            submission_key = str(uuid.uuid4())
            for submission_attempt in range(1, args.submission_attempts + 1):
                try:
                    job = call(
                        args.base_url, token, "POST", "/api/jobs", payload,
                        extra_headers={"Idempotency-Key": submission_key}, timeout=120,
                    )
                    break
                except Exception as exc:
                    if (
                        submission_attempt == args.submission_attempts
                        or not retryable_submission_error(exc)
                    ):
                        raise
                    delay = min(
                        args.submission_backoff_seconds * submission_attempt,
                        300.0,
                    )
                    print(
                        f"submission retry {submission_attempt}/{args.submission_attempts} "
                        f"case={case['name']} delay={delay:.1f}s error={type(exc).__name__}",
                        flush=True,
                    )
                    time.sleep(delay)
            jobs.append({"case": case, "id": job["id"], "status": job["status"]})
            write_json_atomic(checkpoint_path, {
                "schema_version": 1,
                "model": args.model,
                "delivery_mode": args.delivery_mode,
                "max_candidates": args.max_candidates,
                "jobs": jobs,
            })
            print(f"submitted {case['name']} job={job['id']}", flush=True)

    deadline = started + args.timeout_seconds
    last_report = 0.0
    pool_evidence = {
        "configured_slots": None,
        "max_running": 0,
        "max_queued": 0,
        "queue_observed": False,
        "assigned_workers": [],
    }
    assignment_by_job: dict[str, str] = {}
    approved_jobs: set[str] = set()
    while any(item["status"] not in TERMINAL for item in jobs):
        if time.monotonic() >= deadline:
            raise TimeoutError("delivery matrix did not reach terminal states before timeout")
        dashboard = resilient_call(
            args.base_url,
            token,
            "GET",
            "/api/jobs?ids=" + ",".join(item["id"] for item in jobs),
        )
        capacity = dashboard.get("capacity") or {}
        pool_evidence["configured_slots"] = capacity.get("slots")
        pool_evidence["max_running"] = max(
            int(pool_evidence["max_running"]), int(capacity.get("running") or 0)
        )
        pool_evidence["max_queued"] = max(
            int(pool_evidence["max_queued"]), int(capacity.get("queued") or 0)
        )
        for summary in dashboard.get("jobs") or []:
            if summary.get("queue_position"):
                pool_evidence["queue_observed"] = True
            worker = summary.get("windows_worker")
            if worker and assignment_by_job.get(summary["id"]) != worker:
                assignment_by_job[summary["id"]] = worker
                print(f"assigned job={summary['id']} worker={worker}", flush=True)
        for item in jobs:
            if item["status"] in TERMINAL:
                continue
            job = resilient_call(args.base_url, token, "GET", f"/api/jobs/{item['id']}")
            item["status"] = job["status"]
            item["job"] = job
            if (
                args.delivery_mode == "downloadable_project"
                and job["status"] == "awaiting_contract_approval"
                and item["id"] not in approved_jobs
            ):
                engineering = (job.get("contract") or {}).get("engineering_template")
                if not isinstance(engineering, dict):
                    raise RuntimeError(
                        f"job {item['id']} awaits approval without an engineering template"
                    )
                engineering["wiring_review_acknowledged"] = True
                engineering["field_acceptance_acknowledged"] = True
                for mapping in engineering.get("mappings") or []:
                    mapping["terminal_note"] = "automated release acceptance mapping"
                approved = resilient_call(
                    args.base_url,
                    token,
                    "POST",
                    f"/api/jobs/{item['id']}/approve",
                    {"approve": True, "engineering_config": engineering},
                    timeout=120,
                )
                approved_jobs.add(item["id"])
                item["status"] = approved["status"]
                item["job"] = approved
                print(f"approved job={item['id']} target={item['case']['plc_model']}", flush=True)
        write_json_atomic(checkpoint_path, {
            "schema_version": 1,
            "model": args.model,
            "delivery_mode": args.delivery_mode,
            "max_candidates": args.max_candidates,
            "jobs": [
                {key: value for key, value in item.items() if key != "job"}
                for item in jobs
            ],
        })
        if time.monotonic() - last_report >= 30:
            print(
                "progress " + ", ".join(
                    f"{item['case']['name']}={item['status']}" for item in jobs
                ),
                flush=True,
            )
            last_report = time.monotonic()
        time.sleep(args.poll_seconds)

    results = []
    for item in jobs:
        job = item.get("job") or resilient_call(
            args.base_url, token, "GET", f"/api/jobs/{item['id']}"
        )
        result = job.get("result") or {}
        vendor = result.get("vendor_validation") or {}
        artifacts = {
            str(artifact.get("kind"))
            for artifact in result.get("artifacts") or []
            if isinstance(artifact, dict)
        }
        expected_artifacts = (
            {"ispsoft-project", "engineering-mapping", "deployment-main", "field-checklist"}
            if args.delivery_mode == "downloadable_project"
            else set()
        )
        results.append({
            "case": item["case"]["name"],
            "job_id": item["id"],
            "controller": item["case"]["plc_model"],
            "output_language": item["case"]["output_language"],
            "status": job["status"],
            "success": (
                job["status"] == "verified_success"
                and expected_artifacts <= artifacts
            ),
            "candidates_used": result.get("candidates_used"),
            "vendor_validation": vendor.get("status"),
            "delivery_mode": args.delivery_mode,
            "delivery_artifacts_complete": expected_artifacts <= artifacts,
            "windows_worker": assignment_by_job.get(item["id"]),
            "error_class": (
                str(job.get("last_error") or "").split(":", 1)[0] or None
            ),
        })
    report = {
        "schema_version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "delivery_mode": args.delivery_mode,
        "max_candidates": args.max_candidates,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "passed": sum(item["success"] for item in results),
        "total": len(results),
        "pool_evidence": {
            **pool_evidence,
            "assigned_workers": sorted(set(assignment_by_job.values())),
        },
        "results": results,
    }
    write_json_atomic(args.output, report)
    checkpoint_path.unlink(missing_ok=True)
    print(json.dumps(report, ensure_ascii=False), flush=True)
    return 0 if report["passed"] == report["total"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

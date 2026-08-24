#!/usr/bin/env python3
"""Run a resumable 24/72-hour model, queue, database, and vendor stability test."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


COMBINATIONS = (
    ("deepseek-v4-pro", "function_unit"),
    ("sonnet-5", "function_unit"),
    ("deepseek-v4-pro", "downloadable_project"),
    ("sonnet-5", "downloadable_project"),
)
CASES = (
    "dvp_st_latched_motor_alarm",
    "dvp_ld_dual_motor_interlock",
    "as_st_two_stage_sequence",
    "as_ld_valve_mode_safety",
    "dvp_st_fan_alarm_reset",
)
INFRASTRUCTURE_STATUSES = {"infrastructure_error", "cancelled"}


def write_json_atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def notify(title: str, body: str) -> None:
    endpoint = os.environ.get("PLC_BARK_URL", "")
    if not endpoint:
        return
    request = urllib.request.Request(
        endpoint,
        data=json.dumps({"title": title, "body": body, "group": "PLC交付"}, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15):
            pass
    except Exception:
        pass


def api_json(base_url: str, token: str, path: str) -> dict:
    request = urllib.request.Request(
        base_url.rstrip("/") + path,
        headers={"X-API-Key": token},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def snapshot(base_url: str, token: str) -> dict:
    history = api_json(base_url, token, "/api/history?page=1&page_size=1&archive=all")
    validation = api_json(base_url, token, "/api/validation-status")
    models = api_json(base_url, token, "/api/model-status")
    workers = validation.get("windows_workers") or []
    pagination = history.get("pagination") or {}
    capacity = history.get("capacity") or {}
    return {
        "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "history_total": int(pagination.get("total", 0)),
        "active_jobs": int(capacity.get("running", 0)),
        "queued_jobs": int(capacity.get("queued", 0)),
        "ready_windows_workers": sum(bool(item.get("ready")) for item in workers),
        "model_status": {
            str(item.get("id")): str(item.get("status"))
            for item in models.get("models") or []
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--duration-hours", type=float, default=72)
    parser.add_argument("--checkpoint-hours", type=float, default=24)
    parser.add_argument("--interval-hours", type=float, default=1.5)
    parser.add_argument("--max-candidates", type=int, default=6)
    parser.add_argument("--base-url", default="http://127.0.0.1:18081")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    token = os.environ.get("PLC_WEB_API_TOKEN", "")
    if not token:
        parser.error("PLC_WEB_API_TOKEN is required")
    if args.duration_hours < args.checkpoint_hours or args.checkpoint_hours <= 0:
        parser.error("duration must be at least the positive checkpoint duration")
    if args.interval_hours <= 0:
        parser.error("interval must be positive")

    root = Path(__file__).resolve().parents[1]
    output_root = args.output_root.resolve()
    state_path = output_root / "stability_state.json"
    output_root.mkdir(parents=True, exist_ok=True)
    if args.resume and state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
    else:
        state = {
            "schema_version": 1,
            "status": "running",
            "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "checkpoint_24h": None,
            "rounds": [],
            "initial_snapshot": snapshot(args.base_url, token),
        }
        write_json_atomic(state_path, state)

    started = dt.datetime.fromisoformat(state["started_at"])
    round_index = len(state["rounds"])
    while True:
        elapsed_hours = (
            dt.datetime.now(dt.timezone.utc) - started
        ).total_seconds() / 3600
        if elapsed_hours >= args.duration_hours:
            break

        model, delivery_mode = COMBINATIONS[round_index % len(COMBINATIONS)]
        case = CASES[round_index % len(CASES)]
        round_root = output_root / f"round_{round_index + 1:03d}"
        report_path = round_root / "matrix.json"
        command = [
            sys.executable,
            str(root / "scripts/run_delivery_matrix.py"),
            "--model", model,
            "--delivery-mode", delivery_mode,
            "--max-candidates", str(args.max_candidates),
            "--timeout-seconds", "14400",
            "--submission-attempts", "20",
            "--submission-backoff-seconds", "30",
            "--output", str(report_path),
            "--case", case,
        ]
        completed = subprocess.run(command, cwd=root, env=dict(os.environ), check=False)
        report = (
            json.loads(report_path.read_text(encoding="utf-8"))
            if report_path.is_file() else {}
        )
        statuses = [str(item.get("status")) for item in report.get("results") or []]
        state["rounds"].append({
            "round": round_index + 1,
            "model": model,
            "delivery_mode": delivery_mode,
            "case": case,
            "return_code": completed.returncode,
            "passed": int(report.get("passed", 0)),
            "total": int(report.get("total", 0)),
            "infrastructure_failures": sum(
                status in INFRASTRUCTURE_STATUSES for status in statuses
            ) + int(not report),
            "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "snapshot": snapshot(args.base_url, token),
        })
        round_index += 1
        elapsed_hours = (
            dt.datetime.now(dt.timezone.utc) - started
        ).total_seconds() / 3600
        if elapsed_hours >= args.checkpoint_hours and state["checkpoint_24h"] is None:
            infrastructure_failures = sum(
                int(item["infrastructure_failures"]) for item in state["rounds"]
            )
            state["checkpoint_24h"] = {
                "status": "pass" if infrastructure_failures == 0 else "fail",
                "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "rounds": len(state["rounds"]),
                "infrastructure_failures": infrastructure_failures,
            }
            notify(
                "PLC 24小时稳定性检查",
                f"状态：{state['checkpoint_24h']['status']}；轮次：{len(state['rounds'])}；基础设施错误：{infrastructure_failures}",
            )
            if infrastructure_failures:
                state["status"] = "failed_at_24h_checkpoint"
                write_json_atomic(state_path, state)
                return 1
        write_json_atomic(state_path, state)

        next_due = started + dt.timedelta(hours=args.interval_hours * round_index)
        remaining = (next_due - dt.datetime.now(dt.timezone.utc)).total_seconds()
        if remaining > 0:
            time.sleep(remaining)

    infrastructure_failures = sum(
        int(item["infrastructure_failures"]) for item in state["rounds"]
    )
    state.update({
        "status": "pass" if infrastructure_failures == 0 else "fail",
        "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "infrastructure_failures": infrastructure_failures,
        "final_snapshot": snapshot(args.base_url, token),
    })
    write_json_atomic(state_path, state)
    notify(
        "PLC 72小时稳定性测试已结束",
        f"状态：{state['status']}；轮次：{len(state['rounds'])}；基础设施错误：{infrastructure_failures}",
    )
    print(json.dumps(state, ensure_ascii=False), flush=True)
    return 0 if infrastructure_failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Notify the PI when a Sonnet 5 EGBS or baseline4 experiment terminates."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.request
from pathlib import Path


ENDPOINT_FILE = Path.home() / ".config/plc-evidence-loop/bark_endpoint"


def notify(title: str, body: str) -> None:
    endpoint = ENDPOINT_FILE.read_text(encoding="utf-8").strip()
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(
            {"title": title, "body": body, "group": "PLC-100-Sonnet5"}
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        if response.status // 100 != 2:
            raise RuntimeError(f"Bark returned HTTP {response.status}")


def process_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def load_summary(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--controller-pid", required=True, type=int)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--poll-seconds", type=int, default=30)
    parser.add_argument("--kind", choices=("method", "baseline4"), default="method")
    args = parser.parse_args()
    if args.controller_pid <= 0 or args.poll_seconds <= 0:
        raise ValueError("controller PID and poll interval must be positive")

    while True:
        summary = load_summary(args.summary)
        if summary is not None:
            tasks = int(summary.get("task_count", 0))
            successes = int(summary.get("success_count", 0))
            if args.kind == "baseline4":
                model_ok = all(
                    row.get("resolved_model_valid") is True
                    for row in summary.get("runs", [])
                    if int(row.get("model_calls_used", 0)) > 0
                )
                protocol_ok = summary.get("protocol_ok") is True
                title = "PLC-100 Sonnet 5 Baseline4 完成"
                label = "Baseline4"
            else:
                model_ok = summary.get("all_model_identities_valid") is True
                protocol_ok = all(
                    summary.get(key) is True
                    for key in (
                        "all_ledgers_valid",
                        "all_model_identities_valid",
                        "sealed_judge_count_valid",
                        "inconclusive_restart_count_valid",
                    )
                )
                title = "PLC-100 Sonnet 5 我们的方法完成"
                label = "Our method"
            rate = 100.0 * successes / tasks if tasks else 0.0
            notify(
                title,
                f"{label}: {successes}/{tasks} ({rate:.1f}%); "
                f"model_identity_ok={model_ok}; protocol_ok={protocol_ok}",
            )
            print(
                f"completed successes={successes}/{tasks} "
                f"model_identity_ok={model_ok} protocol_ok={protocol_ok}",
                flush=True,
            )
            return 0 if tasks == 100 and protocol_ok else 2

        if not process_running(args.controller_pid):
            title = (
                "PLC-100 Sonnet 5 Baseline4 异常"
                if args.kind == "baseline4"
                else "PLC-100 Sonnet 5 我们的方法异常"
            )
            notify(
                title,
                "后继控制器已停止，但未生成 batch_summary.json；请检查控制器日志。",
            )
            raise RuntimeError("successor controller stopped without a batch summary")
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())

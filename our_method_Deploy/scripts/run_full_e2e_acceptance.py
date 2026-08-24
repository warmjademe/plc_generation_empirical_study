#!/usr/bin/env python3
"""Run the complete 2x2x2x2 production acceptance matrix."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path


MODELS = ("deepseek-v4-pro", "sonnet-5")
DELIVERY_MODES = ("function_unit", "downloadable_project")
CASES = (
    "dvp_st_latched_motor_alarm",
    "dvp_ld_dual_motor_interlock",
    "as_st_two_stage_sequence",
    "as_ld_valve_mode_safety",
)


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--max-candidates", type=int, default=20)
    parser.add_argument("--timeout-seconds", type=int, default=14400)
    args = parser.parse_args()
    if not os.environ.get("PLC_WEB_API_TOKEN"):
        parser.error("PLC_WEB_API_TOKEN is required")
    if not 1 <= args.max_candidates <= 20:
        parser.error("--max-candidates must be in 1..20")

    root = Path(__file__).resolve().parents[1]
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    started = dt.datetime.now(dt.timezone.utc)
    combinations: list[dict] = []
    aggregate_path = output_root / "full_matrix_summary.json"

    for model in MODELS:
        for delivery_mode in DELIVERY_MODES:
            output = output_root / f"{model}__{delivery_mode}.json"
            command = [
                sys.executable,
                str(root / "scripts/run_delivery_matrix.py"),
                "--model", model,
                "--delivery-mode", delivery_mode,
                "--max-candidates", str(args.max_candidates),
                "--timeout-seconds", str(args.timeout_seconds),
                "--submission-attempts", "20",
                "--submission-backoff-seconds", "30",
                "--output", str(output),
            ]
            for case in CASES:
                command.extend(("--case", case))
            completed = subprocess.run(command, cwd=root, env=dict(os.environ), check=False)
            report = {}
            if output.is_file():
                report = json.loads(output.read_text(encoding="utf-8"))
            combinations.append({
                "model": model,
                "delivery_mode": delivery_mode,
                "return_code": completed.returncode,
                "passed": int(report.get("passed", 0)),
                "total": int(report.get("total", len(CASES))),
                "report": output.name,
            })
            write_json_atomic(aggregate_path, {
                "schema_version": 1,
                "status": "running",
                "started_at": started.isoformat(),
                "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "expected_tasks": len(MODELS) * len(DELIVERY_MODES) * len(CASES),
                "combinations": combinations,
            })

    passed = sum(item["passed"] for item in combinations)
    total = sum(item["total"] for item in combinations)
    result = {
        "schema_version": 1,
        "status": "pass" if passed == total else "fail",
        "started_at": started.isoformat(),
        "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "passed": passed,
        "total": total,
        "combinations": combinations,
    }
    write_json_atomic(aggregate_path, result)
    notify("PLC 完整组合矩阵已结束", f"结果：{passed}/{total}；状态：{result['status']}")
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return 0 if passed == total else 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Monitor one GPT-5.6 Luna experiment group and send its final Bark result."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.request
from pathlib import Path


SOURCE = Path("/home/qyb/RESEARCH/PLC_Generation/PLC_Generation_Empirical_Study/source_codes")
ENDPOINT_FILE = Path.home() / ".config/plc-evidence-loop/bark_endpoint"
METHOD_SUMMARY = (
    SOURCE / "our_method/runs/"
    "egbs_gpt_5_6_luna_agentic_context_v5_2_datasets100_20260812_v1/"
    "batch_summary.json"
)
BASELINE_SUMMARIES = {
    "LLM4PLC": SOURCE / "RQ1/runs/"
    "baseline1_llm4plc_gpt_5_6_luna_datasets100_20260812_v1/baseline_summary.json",
    "Agents4PLC": SOURCE / "RQ1/runs/"
    "baseline2_agents4plc_gpt_5_6_luna_datasets100_20260812_v1/baseline_summary.json",
    "ChatDev": SOURCE / "RQ1/runs/"
    "baseline3_chatdev_gpt_5_6_luna_datasets100_20260812_v1/baseline_summary.json",
}
PID_FILES = {
    "method": Path("/tmp/run_datasets100_gpt56_luna_method_nas_v1.pid"),
    "baselines": Path("/tmp/run_datasets100_gpt56_luna_baselines_huashuo_v1.pid"),
}


def load(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def running(pid_file: Path) -> bool:
    try:
        os.kill(int(pid_file.read_text(encoding="utf-8").strip()), 0)
        return True
    except (FileNotFoundError, ProcessLookupError, PermissionError, ValueError):
        return False


def notify(title: str, body: str) -> None:
    endpoint = ENDPOINT_FILE.read_text(encoding="utf-8").strip()
    request = urllib.request.Request(
        endpoint,
        data=json.dumps({"title": title, "body": body, "group": "PLC-100-Luna"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        if response.status // 100 != 2:
            raise RuntimeError(f"Bark returned HTTP {response.status}")


def rate_line(name: str, value: dict) -> str:
    tasks = int(value.get("task_count", 0))
    successes = int(value.get("success_count", 0))
    rate = 100.0 * successes / tasks if tasks else 0.0
    return f"{name}: {successes}/{tasks} ({rate:.1f}%)"


def monitor_method() -> None:
    while True:
        value = load(METHOD_SUMMARY)
        if value is not None:
            notify("PLC-100 Luna 我们的方法完成", rate_line("Our method", value))
            print(rate_line("Our method", value), flush=True)
            return
        if not running(PID_FILES["method"]):
            notify("PLC-100 Luna 我们的方法异常", "控制器已经停止，但未生成 batch_summary.json。")
            raise RuntimeError("method controller stopped without a summary")
        time.sleep(20)


def monitor_baselines() -> None:
    while True:
        values = {name: load(path) for name, path in BASELINE_SUMMARIES.items()}
        if all(value is not None for value in values.values()):
            body = "\n".join(rate_line(name, value or {}) for name, value in values.items())
            notify("PLC-100 Luna 三个 Baseline 完成", body)
            print(body, flush=True)
            return
        if not running(PID_FILES["baselines"]):
            completed = sorted(name for name, value in values.items() if value is not None)
            notify("PLC-100 Luna Baseline 异常", f"控制器提前停止；已完成：{completed}")
            raise RuntimeError("baseline controller stopped before all summaries were created")
        time.sleep(20)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=("method", "baselines"))
    args = parser.parse_args()
    if args.mode == "method":
        monitor_method()
    else:
        monitor_baselines()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Finish qualification, launch the two-host DeepSeek study, and notify via Bark."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path


LOCAL_SOURCE = Path(
    "/root/RESEARCH/PLC_Generation/PLC_Generation_Empirical_Study/source_codes"
)
SSH_KEY = "/root/.ssh/nas_qyb"
SSH_HOST = "qyb@nas.qyb.name"
NAS_PORT = 2222
HUASHUO_PORT = 3333
REMOTE_SOURCE = "/home/qyb/RESEARCH/PLC_Generation/PLC_Generation_Empirical_Study/source_codes"
NAS_CALIBRATION = (
    f"{REMOTE_SOURCE}/our_method/runs/"
    "calibration_datasets100_full_20260812_v1/calibration_summary.json"
)
NAS_METHOD_SUMMARY = (
    f"{REMOTE_SOURCE}/our_method/runs/"
    "egbs_deepseek_v4_flash_agentic_context_v5_2_datasets100_20260812_v1/"
    "batch_summary.json"
)
HUASHUO_CONTROLLER = (
    f"{REMOTE_SOURCE}/RQ1/run_datasets100_deepseek_baselines_huashuo.sh"
)
HUASHUO_SUMMARIES = {
    "LLM4PLC": (
        f"{REMOTE_SOURCE}/RQ1/runs/"
        "baseline1_llm4plc_deepseek_v4_flash_datasets100_20260812_v1/"
        "baseline_summary.json"
    ),
    "Agents4PLC": (
        f"{REMOTE_SOURCE}/RQ1/runs/"
        "baseline2_agents4plc_deepseek_v4_flash_datasets100_20260812_v1/"
        "baseline_summary.json"
    ),
    "ChatDev": (
        f"{REMOTE_SOURCE}/RQ1/runs/"
        "baseline3_chatdev_deepseek_v4_flash_datasets100_20260812_v1/"
        "baseline_summary.json"
    ),
}
POLL_SECONDS = 20


def log(message: str) -> None:
    print(f"{datetime.now().astimezone().isoformat()} {message}", flush=True)


def remote(port: int, command: str, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "ssh", "-i", SSH_KEY, "-p", str(port), "-o", "BatchMode=yes",
            "-o", "IdentitiesOnly=yes", SSH_HOST, command,
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def remote_json(port: int, path: str) -> dict | None:
    result = remote(port, f"test -s '{path}' && cat '{path}'", check=False)
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return json.loads(result.stdout)


def scp_from(port: int, remote_path: str, local_path: Path) -> None:
    subprocess.run(
        [
            "scp", "-q", "-i", SSH_KEY, "-P", str(port), "-o", "BatchMode=yes",
            "-o", "IdentitiesOnly=yes", f"{SSH_HOST}:{remote_path}", str(local_path),
        ],
        check=True,
    )


def scp_to(port: int, local_path: Path, remote_path: str, *, recursive: bool = False) -> None:
    command = ["scp", "-q"]
    if recursive:
        command.append("-r")
    command.extend([
        "-i", SSH_KEY, "-P", str(port), "-o", "BatchMode=yes",
        "-o", "IdentitiesOnly=yes", str(local_path), f"{SSH_HOST}:{remote_path}",
    ])
    subprocess.run(command, check=True)


def bark_endpoint() -> str | None:
    text = Path("/root/RESEARCH/CLAUDE.md").read_text(encoding="utf-8")
    match = re.search(r"https://api\.day\.app/[A-Za-z0-9]+", text)
    return match.group(0) if match else None


def notify(title: str, body: str) -> None:
    endpoint = bark_endpoint()
    if not endpoint:
        log("Bark endpoint unavailable")
        return
    request = urllib.request.Request(
        endpoint,
        data=json.dumps({"title": title, "body": body, "group": "PLC-100"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.status // 100 != 2:
                raise RuntimeError(f"Bark returned HTTP {response.status}")
        log(f"Bark notification sent: {title}")
    except Exception as exc:  # Notification failure must not erase experiment results.
        log(f"Bark notification failed: {type(exc).__name__}: {exc}")


def validate_calibration(summary: dict) -> None:
    if not (
        summary.get("success") is True
        and summary.get("task_count") == 100
        and summary.get("pass_count") == 100
    ):
        raise RuntimeError(f"reference calibration failed: {summary.get('status_counts')}")


def import_and_distribute_calibration() -> None:
    local_calibration = Path("/tmp/datasets100_calibration_summary_20260812_v1.json")
    scp_from(NAS_PORT, NAS_CALIBRATION, local_calibration)
    dataset = LOCAL_SOURCE / "datasets_100"
    config = LOCAL_SOURCE / "our_method/configs/deepseek_v4_flash_agentic_context_v5_2.json"
    subprocess.run(
        [
            sys.executable, str(dataset / "record_revalidation.py"),
            "--calibration-summary", str(local_calibration),
            "--validator-config", str(config),
        ],
        check=True,
    )
    for port in (NAS_PORT, HUASHUO_PORT):
        remote_dataset = f"{REMOTE_SOURCE}/datasets_100"
        remote(port, f"mkdir -p '{remote_dataset}/evidence'")
        for name in ("record_revalidation.py", "revalidation_summary.json", "dataset_summary.json"):
            scp_to(port, dataset / name, f"{remote_dataset}/{name}")
        scp_to(
            port,
            dataset / "evidence/exact_revalidation",
            f"{remote_dataset}/evidence/",
            recursive=True,
        )
    log("exact calibration evidence imported locally and synchronized to both hosts")


def start_huashuo_baselines() -> int:
    command = (
        f"nohup '{HUASHUO_CONTROLLER}' "
        ">/tmp/run_datasets100_deepseek_baselines_huashuo.launch.log 2>&1 "
        "</dev/null & echo $!"
    )
    result = remote(HUASHUO_PORT, command)
    pid = int(result.stdout.strip().splitlines()[-1])
    log(f"huashuo baseline controller started pid={pid}")
    return pid


def summarize_method(value: dict) -> str:
    successes = int(value.get("success_count", 0))
    tasks = int(value.get("task_count", 0))
    rate = 100.0 * successes / tasks if tasks else 0.0
    return f"Our method: {successes}/{tasks} ({rate:.1f}%), status={value.get('status_counts')}"


def summarize_baseline(name: str, value: dict) -> str:
    successes = int(value.get("success_count", 0))
    tasks = int(value.get("task_count", 0))
    rate = 100.0 * successes / tasks if tasks else 0.0
    return f"{name}: {successes}/{tasks} ({rate:.1f}%), protocol_ok={value.get('protocol_ok')}"


def main() -> int:
    log("orchestrator waiting for NAS reference calibration")
    while True:
        calibration = remote_json(NAS_PORT, NAS_CALIBRATION)
        if calibration is not None:
            validate_calibration(calibration)
            break
        running = remote(
            NAS_PORT,
            "pid=$(cat /tmp/calibration_datasets100_full_20260812_v1.pid 2>/dev/null) "
            "&& kill -0 \"$pid\" 2>/dev/null",
            check=False,
        )
        if running.returncode != 0:
            raise RuntimeError("NAS calibration stopped before producing a summary")
        time.sleep(POLL_SECONDS)

    log("NAS reference calibration passed 100/100")
    import_and_distribute_calibration()
    notify("PLC-100 数据集校验完成", "100/100 参考程序通过 MatIEC → PLCverif → OpenPLC。")
    huashuo_pid = start_huashuo_baselines()

    method_notified = False
    baselines_notified = False
    method_summary: dict | None = None
    baseline_summaries: dict[str, dict] = {}
    while not (method_notified and baselines_notified):
        if not method_notified:
            method_summary = remote_json(NAS_PORT, NAS_METHOD_SUMMARY)
            if method_summary is not None:
                message = summarize_method(method_summary)
                log(message)
                notify("PLC-100 我们的方法完成", message)
                method_notified = True
        if not baselines_notified:
            baseline_summaries = {
                name: value
                for name, path in HUASHUO_SUMMARIES.items()
                if (value := remote_json(HUASHUO_PORT, path)) is not None
            }
            if len(baseline_summaries) == len(HUASHUO_SUMMARIES):
                message = "\n".join(
                    summarize_baseline(name, baseline_summaries[name])
                    for name in HUASHUO_SUMMARIES
                )
                log(message.replace("\n", "; "))
                notify("PLC-100 三个 Baseline 完成", message)
                baselines_notified = True
            elif remote(
                HUASHUO_PORT, f"kill -0 {huashuo_pid} 2>/dev/null", check=False
            ).returncode != 0:
                raise RuntimeError(
                    "huashuo baseline controller stopped before all summaries were produced; "
                    f"completed={sorted(baseline_summaries)}"
                )
        if not (method_notified and baselines_notified):
            time.sleep(POLL_SECONDS)

    combined = summarize_method(method_summary or {}) + "\n" + "\n".join(
        summarize_baseline(name, baseline_summaries[name]) for name in HUASHUO_SUMMARIES
    )
    notify("PLC-100 DeepSeek 对比实验全部完成", combined)
    log("all datasets100 DeepSeek experiments completed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        log(f"fatal: {type(exc).__name__}: {exc}")
        notify("PLC-100 实验异常", f"{type(exc).__name__}: {exc}")
        raise

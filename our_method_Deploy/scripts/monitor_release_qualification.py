#!/usr/bin/env python3
"""Send one sanitized notification for each long-test milestone."""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path


ROOT = Path("/opt/plc-generation/data/release-tests")
STATE_PATH = ROOT / "long-test-monitor-state.json"


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def unit_state(name: str) -> str:
    completed = subprocess.run(
        ["/usr/bin/systemctl", "is-active", name],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.stdout.strip() or "unknown"


def notify(title: str, body: str) -> None:
    endpoint = os.environ.get("PLC_BARK_URL", "")
    if not endpoint:
        raise RuntimeError("PLC_BARK_URL is required")
    request = urllib.request.Request(
        endpoint,
        data=json.dumps({"title": title, "body": body, "group": "PLC交付"}, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15):
        pass


def save(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(STATE_PATH)


def qualification_jobs() -> int:
    path = Path("/opt/plc-generation/dvp-bridge-04/qualification_report.jsonl")
    jobs = 0
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return 0
    for line in lines:
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if item.get("status") == "pass":
            jobs += int(item.get("jobs_executed", 0))
    return jobs


def main() -> int:
    state = read_json(STATE_PATH)
    state.setdefault("sent", [])
    sent = set(state["sent"])
    while True:
        qualification_state = unit_state("plc-dvp-qualification@04.service")
        jobs = qualification_jobs()
        if "qualification" not in sent and qualification_state in {"inactive", "failed"}:
            status = "通过" if qualification_state == "inactive" and jobs >= 100 else "失败"
            notify("Windows 节点 04 资格测试已结束", f"状态：{status}；通过任务：{jobs}/100")
            sent.add("qualification")

        matrix = read_json(ROOT / "full-e2e-matrix-current/full_matrix_summary.json")
        if "matrix" not in sent and matrix.get("status") in {"pass", "fail"}:
            notify(
                "PLC 完整组合矩阵已结束",
                f"状态：{matrix['status']}；通过：{matrix.get('passed', 0)}/{matrix.get('total', 16)}",
            )
            sent.add("matrix")

        stability = read_json(ROOT / "stability-72h-current/stability_state.json")
        checkpoint = stability.get("checkpoint_24h") or {}
        if "stability_24h" not in sent and checkpoint.get("status") in {"pass", "fail"}:
            notify(
                "PLC 24小时稳定性检查",
                f"状态：{checkpoint['status']}；轮次：{checkpoint.get('rounds', 0)}；基础设施错误：{checkpoint.get('infrastructure_failures', 0)}",
            )
            sent.add("stability_24h")
        if "stability_72h" not in sent and stability.get("status") in {"pass", "fail", "failed_at_24h_checkpoint"}:
            notify(
                "PLC 长稳测试已结束",
                f"状态：{stability['status']}；轮次：{len(stability.get('rounds', []))}；基础设施错误：{stability.get('infrastructure_failures', 0)}",
            )
            sent.add("stability_72h")

        state["sent"] = sorted(sent)
        save(state)
        if {"qualification", "matrix", "stability_24h", "stability_72h"} <= sent:
            return 0
        time.sleep(60)


if __name__ == "__main__":
    raise SystemExit(main())

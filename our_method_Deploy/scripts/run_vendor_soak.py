#!/usr/bin/env python3
"""Execute a resumable 100-job vendor-worker qualification soak."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

from run_vendor_canary import execution_identity_error


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
    parser.add_argument("--spool-root", required=True)
    parser.add_argument("--cycles", type=int, default=25)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    if not 1 <= args.cycles <= 100:
        parser.error("--cycles must be between 1 and 100")
    root = Path(__file__).resolve().parents[1]
    report = Path(args.report).resolve()
    spool = Path(args.spool_root).resolve()
    identity_error = execution_identity_error(spool)
    if identity_error:
        parser.error(identity_error)
    qualification_marker = spool.parent / "qualification_active"
    report.parent.mkdir(parents=True, exist_ok=True)
    completed: set[tuple[int, str]] = set()
    if report.is_file():
        for line in report.read_text(encoding="utf-8").splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if item.get("status") == "pass":
                completed.add((int(item["cycle"]), str(item["target"])))
    qualification_marker.write_text(
        dt.datetime.now(dt.timezone.utc).isoformat() + "\n", encoding="utf-8"
    )
    environment = dict(os.environ)
    environment["DELTAPLC_ALLOW_QUALIFICATION"] = "1"
    qualified = False
    try:
        for cycle in range(1, args.cycles + 1):
            for target in ("DVP48ES300R", "AS228T-A"):
                if (cycle, target) in completed:
                    continue
                started = dt.datetime.now(dt.timezone.utc)
                result = subprocess.run([
                    sys.executable, str(root / "scripts/run_vendor_canary.py"),
                    "--spool-root", args.spool_root, "--target", target,
                ], check=False, env=environment)
                record = {
                    "cycle": cycle,
                    "target": target,
                    "jobs_executed": 2,
                    "status": "pass" if result.returncode == 0 else "fail",
                    "started_at": started.isoformat(),
                    "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                }
                with report.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(record, separators=(",", ":")) + "\n")
                if result.returncode != 0:
                    notify(
                        "Windows 节点资格测试失败",
                        f"节点：{spool.parent.name}；周期：{cycle}；型号：{target}",
                    )
                    return 1
        qualified = True
        notify(
            "Windows 节点资格测试通过",
            f"节点：{spool.parent.name}；完成厂商任务：{args.cycles * 4}",
        )
        return 0
    finally:
        # Admission is fail-closed: a failed or interrupted qualification run
        # must leave the marker in place so the scheduler cannot use the VM.
        if qualified:
            qualification_marker.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())

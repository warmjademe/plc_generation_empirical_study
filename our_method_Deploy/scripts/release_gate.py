#!/usr/bin/env python3
"""Fail-closed production release gate with machine-readable evidence."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

from plc_deploy.settings import Settings


SERVICES = (
    "plc-generation-postgres.service",
    "plc-generation-worker.service",
    "plc-generation.service",
    "plc-generation-proxy.service",
    "plc-dvp-bridge@01.service",
    "plc-dvp-bridge@02.service",
    "plc-dvp-bridge@03.service",
    "plc-dvp-bridge@04.service",
)
TIMERS = (
    "plc-generation-backup.timer",
    "plc-dvp-canary@01.timer",
    "plc-dvp-canary@02.timer",
    "plc-dvp-canary@03.timer",
    "plc-dvp-canary@04.timer",
)
TARGETS = {"DVP48ES300R", "AS228T-A"}


def command_ok(*command: str) -> bool:
    return subprocess.run(
        command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False
    ).returncode == 0


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def qualification_jobs(path: Path) -> int:
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--minimum-qualification-jobs", type=int, default=100)
    parser.add_argument("--maximum-health-age-seconds", type=int, default=93600)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    settings = Settings.load()
    failures: list[str] = []
    checks: dict[str, object] = {}

    service_state = {name: command_ok("systemctl", "is-active", "--quiet", name) for name in SERVICES}
    timer_state = {name: command_ok("systemctl", "is-enabled", "--quiet", name) for name in TIMERS}
    checks["services"] = service_state
    checks["timers"] = timer_state
    failures.extend(f"service inactive: {name}" for name, ok in service_state.items() if not ok)
    failures.extend(f"timer disabled: {name}" for name, ok in timer_state.items() if not ok)

    nodes: dict[str, dict] = {}
    for index, spool in enumerate(settings.dvp_spool_roots, start=1):
        bridge = spool.parent
        health_path = bridge / "health_status.json"
        health = read_json(health_path)
        age = time.time() - health_path.stat().st_mtime if health_path.is_file() else float("inf")
        targets = set((health.get("targets") or {}).keys())
        qualified_jobs = qualification_jobs(bridge / "qualification_report.jsonl")
        daily = read_json(bridge / "daily_canary_report.json")
        node = {
            "state": health.get("state"),
            "health_age_seconds": round(age, 1),
            "targets": sorted(targets),
            "qualification_jobs": qualified_jobs,
            "daily_canary": daily.get("status"),
        }
        nodes[f"{index:02d}"] = node
        if health.get("state") != "ready" or not TARGETS.issubset(targets):
            failures.append(f"Windows node {index:02d} is not ready for both targets")
        if age > args.maximum_health_age_seconds:
            failures.append(f"Windows node {index:02d} health evidence is stale")
        if qualified_jobs < args.minimum_qualification_jobs:
            failures.append(
                f"Windows node {index:02d} qualification has {qualified_jobs}/"
                f"{args.minimum_qualification_jobs} jobs"
            )
        if daily.get("status") != "pass":
            failures.append(f"Windows node {index:02d} has no passing leased daily canary")
    checks["windows_nodes"] = nodes

    backup_root = Path("/opt/plc-generation/backups")
    backups = sorted(
        (item for item in backup_root.glob("*") if (item / "manifest.json").is_file()),
        key=lambda item: item.name,
    )
    checks["latest_backup"] = backups[-1].name if backups else None
    if not backups:
        failures.append("no verified production backup exists")

    disk = shutil.disk_usage(settings.data_root)
    free_ratio = disk.free / disk.total
    checks["disk_free_percent"] = round(free_ratio * 100, 1)
    if free_ratio < 0.10:
        failures.append("less than 10% disk space remains")

    try:
        with urllib.request.urlopen("http://127.0.0.1:18081/health", timeout=5) as response:
            checks["local_health"] = response.status == 200
    except Exception:
        checks["local_health"] = False
    if not checks["local_health"]:
        failures.append("local Web health check failed")

    result = {"status": "pass" if not failures else "fail", "checks": checks, "failures": failures}
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

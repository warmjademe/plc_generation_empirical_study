#!/usr/bin/env python3
"""Exercise one Windows validation VM under a single long-lived pool lease."""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

from run_vendor_canary import execution_identity_error


TARGETS = ("DVP48ES300R", "AS228T-A")


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def heartbeat_age(path: Path) -> float:
    try:
        return max(0.0, time.time() - path.stat().st_mtime)
    except OSError:
        return float("inf")


def write_active(path: Path, document: dict) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(document, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spool-root", type=Path, required=True)
    parser.add_argument("--cycles", type=int, default=3)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--lease-timeout-seconds", type=int, default=300)
    args = parser.parse_args()
    if not 1 <= args.cycles <= 25:
        parser.error("--cycles must be in 1..25")

    root = Path(__file__).resolve().parents[1]
    spool = args.spool_root.resolve()
    identity_error = execution_identity_error(spool)
    if identity_error:
        parser.error(identity_error)
    bridge = spool.parent
    args.report.parent.mkdir(parents=True, exist_ok=True)
    job_id = f"stability-long-{uuid.uuid4().hex[:12]}"
    lock_path = bridge / "user_job.lock"
    active_path = bridge / "active_user_job.json"
    stream = lock_path.open("a+")
    deadline = time.monotonic() + max(1, args.lease_timeout_seconds)
    while True:
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            if time.monotonic() >= deadline:
                raise TimeoutError("long stability task could not acquire the Windows VM lease")
            time.sleep(1)

    started = dt.datetime.now(dt.timezone.utc)
    records: list[dict] = []
    active = {
        "job_id": job_id,
        "worker_id": read_json(bridge / "worker_endpoint.json").get("worker_id", bridge.name),
        "target": "DVP48ES300R+AS228T-A",
        "state": "long_stability_test",
        "acquired_at": started.isoformat(),
    }
    write_active(active_path, active)
    return_code = 0
    try:
        for cycle in range(1, args.cycles + 1):
            for target in TARGETS:
                case_started = dt.datetime.now(dt.timezone.utc)
                completed = subprocess.run(
                    [
                        sys.executable,
                        str(root / "scripts/run_vendor_canary.py"),
                        "--spool-root",
                        str(spool),
                        "--target",
                        target,
                    ],
                    cwd=root,
                    env=dict(os.environ),
                    check=False,
                )
                bridge_age = heartbeat_age(bridge / "bridge_heartbeat.json")
                worker_age = heartbeat_age(bridge / "worker_heartbeat.json")
                lease_record_intact = read_json(active_path).get("job_id") == job_id
                record = {
                    "cycle": cycle,
                    "target": target,
                    "status": "pass" if completed.returncode == 0 else "fail",
                    "started_at": case_started.isoformat(),
                    "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "bridge_heartbeat_age_seconds": round(bridge_age, 3),
                    "worker_heartbeat_age_seconds": round(worker_age, 3),
                    "lease_record_intact": lease_record_intact,
                }
                records.append(record)
                if (
                    completed.returncode != 0
                    or bridge_age > 60
                    or worker_age > 30
                    or not lease_record_intact
                ):
                    return_code = 1
                    break
            if return_code:
                break
    finally:
        if read_json(active_path).get("job_id") == job_id:
            active_path.unlink(missing_ok=True)
        fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        stream.close()

    report = {
        "schema_version": 1,
        "job_id": job_id,
        "worker_id": active["worker_id"],
        "cycles_requested": args.cycles,
        "checks_completed": len(records),
        "status": "pass" if return_code == 0 else "fail",
        "started_at": started.isoformat(),
        "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "records": records,
    }
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False), flush=True)
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())

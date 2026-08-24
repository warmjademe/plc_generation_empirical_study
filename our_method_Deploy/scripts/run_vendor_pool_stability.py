#!/usr/bin/env python3
"""Verify four-way Windows pool allocation and queued hand-off."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from types import SimpleNamespace

from run_vendor_canary import execution_identity_error


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spool-root", action="append", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--lease-timeout-seconds", type=int, default=3600)
    args = parser.parse_args()
    if len(args.spool_root) != 4:
        parser.error("exactly four --spool-root values are required")

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    from plc_deploy.pipeline import _acquire_delta_worker, _release_delta_worker

    spools = [item.resolve() for item in args.spool_root]
    for spool in spools:
        identity_error = execution_identity_error(spool)
        if identity_error:
            parser.error(identity_error)
    settings = SimpleNamespace(
        dvp_spool_roots=spools,
        dvp_timeout_seconds=args.lease_timeout_seconds,
    )
    targets = ("DVP48ES300R", "AS228T-A", "DVP48ES300R", "AS228T-A", "DVP48ES300R")
    run_root = args.report.parent / ("pool-stability-" + uuid.uuid4().hex[:12])
    run_root.mkdir(parents=True, exist_ok=True)
    state_lock = threading.Lock()
    active = 0
    maximum_active = 0
    assignments: list[dict] = []
    started = dt.datetime.now(dt.timezone.utc)

    def execute(index: int, target: str) -> dict:
        nonlocal active, maximum_active
        job_id = f"pool-stability-{index + 1}-{uuid.uuid4().hex[:8]}"
        job_root = run_root / job_id
        job_root.mkdir()
        requested_at = time.monotonic()
        lease = _acquire_delta_worker(
            settings,
            job_id=job_id,
            target=target,
            job_root=job_root,
            cancel_check=lambda: False,
        )
        acquired_at = time.monotonic()
        assignment = json.loads(
            (job_root / "windows_worker_assignment.json").read_text(encoding="utf-8")
        )
        with state_lock:
            active += 1
            maximum_active = max(maximum_active, active)
            assignments.append(
                {
                    "job_id": job_id,
                    "worker_id": assignment["worker_id"],
                    "target": target,
                    "acquired_monotonic": acquired_at,
                }
            )
        try:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(root / "scripts/run_vendor_canary.py"),
                    "--spool-root",
                    str(lease[1]),
                    "--target",
                    target,
                ],
                cwd=root,
                check=False,
            )
            return {
                "job_id": job_id,
                "target": target,
                "worker_id": assignment["worker_id"],
                "status": "pass" if completed.returncode == 0 else "fail",
                "wait_seconds": round(acquired_at - requested_at, 3),
                "duration_seconds": round(time.monotonic() - acquired_at, 3),
            }
        finally:
            with state_lock:
                active -= 1
            _release_delta_worker(lease, job_id)

    records: list[dict] = []
    with ThreadPoolExecutor(max_workers=5, thread_name_prefix="vendor-pool") as executor:
        futures = [executor.submit(execute, index, target) for index, target in enumerate(targets)]
        for future in as_completed(futures):
            records.append(future.result())

    records.sort(key=lambda item: item["job_id"])
    initial_assignments = sorted(assignments, key=lambda item: item["acquired_monotonic"])[:4]
    initial_workers = {item["worker_id"] for item in initial_assignments}
    queued_handoff = max((item["wait_seconds"] for item in records), default=0) > 1.0
    passed = bool(
        all(item["status"] == "pass" for item in records)
        and maximum_active == 4
        and len(initial_workers) == 4
        and queued_handoff
    )
    report = {
        "schema_version": 1,
        "status": "pass" if passed else "fail",
        "started_at": started.isoformat(),
        "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "configured_workers": 4,
        "submitted_jobs": len(records),
        "maximum_active_leases": maximum_active,
        "initial_distinct_workers": len(initial_workers),
        "queued_handoff_observed": queued_handoff,
        "records": records,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False), flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Run positive and negative ISPSoft/COMMGR canaries for one Windows worker."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


GOOD_ST = """FUNCTION_BLOCK DVP_VALIDATION_CANARY
VAR_INPUT
    Start : BOOL;
    Stop : BOOL;
END_VAR
VAR_OUTPUT
    Motor : BOOL;
END_VAR
IF Stop THEN
    Motor := FALSE;
ELSIF Start THEN
    Motor := TRUE;
END_IF;
END_FUNCTION_BLOCK
"""

BAD_ST = """FUNCTION_BLOCK DVP_VALIDATION_CANARY
VAR_INPUT
    Start : BOOL;
    Stop : BOOL;
END_VAR
VAR_OUTPUT
    Motor : BOOL;
END_VAR
Motor := Start;
END_FUNCTION_BLOCK
"""

METADATA = {
    "id": "DVP_VALIDATION_CANARY",
    "interface": {
        "inputs": [{"name": "Start", "type": "BOOL"}, {"name": "Stop", "type": "BOOL"}],
        "outputs": [{"name": "Motor", "type": "BOOL"}],
    },
    "scan": {"period_ms": 100},
}

SUITE = {
    "schema_version": "1.0",
    "suite": "openplc",
    "task_id": "DVP_VALIDATION_CANARY",
    "scan_period_ms": 100,
    "independent_requirement_oracle": True,
    "cases": [
        {
            "id": "OT_CANARY_START",
            "name": "canary_start",
            "requirement_ids": ["R1"],
            "fresh_instance": True,
            "steps": [{"inputs": {"Start": True, "Stop": False}, "expect": {"Motor": True}, "repeat": 1, "check": "each"}],
        },
        {
            "id": "OT_CANARY_STOP_PRIORITY",
            "name": "canary_stop_priority",
            "requirement_ids": ["R2"],
            "fresh_instance": True,
            "steps": [
                {"inputs": {"Start": True, "Stop": False}, "expect": {"Motor": True}, "repeat": 1, "check": "each"},
                {"inputs": {"Start": True, "Stop": True}, "expect": {"Motor": False}, "repeat": 1, "check": "each"},
            ],
        },
    ],
}


def execution_identity_error(spool: Path, *, effective_uid: int | None = None) -> str | None:
    """Prevent an operator-side account mismatch from quarantining a healthy VM."""

    if os.name != "posix":
        return None
    try:
        owner_uid = spool.stat().st_uid
    except OSError as exc:
        return f"validation spool is unavailable: {type(exc).__name__}"
    current_uid = os.geteuid() if effective_uid is None else effective_uid
    if current_uid != owner_uid:
        return "vendor canary must run as the validation spool owner"
    return None


def _write_status(path: Path, state: str, reason: str, evidence: dict | None = None) -> None:
    targets: dict[str, dict] = {}
    try:
        previous = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(previous.get("targets"), dict):
            targets = dict(previous["targets"])
    except (OSError, UnicodeError, json.JSONDecodeError):
        pass
    if evidence and evidence.get("target"):
        targets[str(evidence["target"])] = dict(evidence)
    document = {
        "schema_version": 1,
        "state": state,
        "reason": reason,
        "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "evidence": evidence or {},
        "targets": targets,
    }
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _run_validator(root: Path, task: Path, candidate: Path, spool: Path, target: str) -> dict:
    completed = subprocess.run(
        [
            sys.executable, str(root / "scripts/dvp48es300r_validator.py"),
            "--candidate", str(candidate), "--task-dir", str(task),
            "--case-role", "all", "--spool-root", str(spool),
            "--target", target, "--timeout-seconds", os.getenv("PLC_DVP_TIMEOUT_SECONDS", "2400"),
        ],
        cwd=candidate.parent,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=int(os.getenv("PLC_DVP_TIMEOUT_SECONDS", "2400")) + 90,
        check=False,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if completed.returncode != 0 or not lines:
        raise RuntimeError(
            f"validator process failed rc={completed.returncode}: {completed.stderr[-500:]}"
        )
    return json.loads(lines[-1])


def _wait_until_worker_ready(spool: Path, target: str, timeout_seconds: int = 420) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        bridge = spool.parent
        try:
            heartbeat = json.loads((bridge / "bridge_heartbeat.json").read_text(encoding="utf-8-sig"))
            worker = json.loads((bridge / "worker_heartbeat.json").read_text(encoding="utf-8-sig"))
            simulator = json.loads((bridge / "simulator_status.json").read_text(encoding="utf-8-sig"))
            template = json.loads((bridge / "as228t_template_status.json").read_text(encoding="utf-8-sig"))
            fresh = (
                time.time() - (bridge / "bridge_heartbeat.json").stat().st_mtime <= 60
                and time.time() - (bridge / "worker_heartbeat.json").stat().st_mtime <= 30
            )
            target_process = (
                simulator.get("dvp_simulator_running") is True
                if target == "DVP48ES300R"
                else simulator.get("as200_simulator_running") is True
                and template.get("status") == "ready"
            )
            if (
                fresh
                and heartbeat.get("status") == "connected"
                and worker.get("status") == "connected"
                and worker.get("state") in {"idle", "polling"}
                and simulator.get("status") == "ready"
                and simulator.get("commgr_running") is True
                and target_process
            ):
                return
        except (OSError, UnicodeError, json.JSONDecodeError):
            pass
        time.sleep(2)
    raise RuntimeError(f"Windows worker did not become ready for {target} before canary timeout")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spool-root", required=True)
    parser.add_argument("--target", choices=("DVP48ES300R", "AS228T-A"), required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    spool = Path(args.spool_root).resolve()
    identity_error = execution_identity_error(spool)
    if identity_error:
        print(json.dumps({
            "status": "configuration_error",
            "summary": identity_error,
        }, ensure_ascii=False))
        return 2
    health_path = spool.parent / "health_status.json"
    _write_status(health_path, "testing", f"running {args.target} positive/negative canary")
    try:
        with tempfile.TemporaryDirectory(prefix="plc-vendor-canary-") as temporary:
            work = Path(temporary)
            task = work / "task"
            task.mkdir()
            (task / "metadata.json").write_text(json.dumps(METADATA), encoding="utf-8")
            (task / "openplc_tests.json").write_text(json.dumps(SUITE), encoding="utf-8")
            (task / "interface.st").write_text(
                GOOD_ST.split("IF Stop", 1)[0] + "END_FUNCTION_BLOCK\n", encoding="utf-8"
            )
            good_dir, bad_dir = work / "good", work / "bad"
            good_dir.mkdir(); bad_dir.mkdir()
            good = good_dir / "candidate.st"; good.write_text(GOOD_ST, encoding="utf-8")
            bad = bad_dir / "candidate.st"; bad.write_text(BAD_ST, encoding="utf-8")
            _wait_until_worker_ready(spool, args.target)
            positive = _run_validator(root, task, good, spool, args.target)
            _wait_until_worker_ready(spool, args.target)
            negative = _run_validator(root, task, bad, spool, args.target)
        if positive.get("status") != "pass" or negative.get("status") != "fail":
            raise RuntimeError(
                "canary polarity mismatch: "
                f"positive={positive.get('status')} ({positive.get('summary')}), "
                f"negative={negative.get('status')} ({negative.get('summary')})"
            )
        _write_status(health_path, "ready", "positive passed and negative was rejected", {
            "target": args.target,
            "positive_status": positive.get("status"),
            "negative_status": negative.get("status"),
            "positive_job_id": positive.get("delta_job_id"),
            "negative_job_id": negative.get("delta_job_id"),
        })
        return 0
    except Exception as exc:
        _write_status(health_path, "quarantined", f"{type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Require both sealed OpenPLC and sealed Delta DVP-ES3 execution."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def emit(document: dict) -> int:
    print(json.dumps(document, ensure_ascii=False, separators=(",", ":")))
    return 0


def run_json(command: list[str], timeout: int) -> dict:
    completed = subprocess.run(
        command,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"validator exited {completed.returncode}: {(completed.stderr or completed.stdout)[-1200:]}"
        )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"validator returned non-JSON output: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--task-dir", required=True)
    parser.add_argument("--openplc-validator", required=True)
    parser.add_argument("--openplc-runner", required=True)
    parser.add_argument("--docker", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--dvp-validator", required=True)
    parser.add_argument(
        "--spool-root",
        help="shared DVP spool; defaults to DELTAPLC_SPOOL_ROOT in the DVP validator",
    )
    parser.add_argument("--dvp-timeout-seconds", type=int, default=1800)
    args = parser.parse_args()
    try:
        portable = run_json(
            [
                sys.executable,
                str(Path(args.openplc_validator).resolve()),
                "--candidate", args.candidate,
                "--task-dir", args.task_dir,
                "--docker", args.docker,
                "--image", args.image,
                "--runner", str(Path(args.openplc_runner).resolve()),
                "--case-role", "sealed",
            ],
            420,
        )
    except (OSError, subprocess.TimeoutExpired, RuntimeError) as exc:
        return emit({
            "status": "inconclusive",
            "summary": "sealed OpenPLC prerequisite did not complete",
            "evidence": [{"kind": "tool_error", "summary": f"{type(exc).__name__}: {exc}"}],
        })
    if portable.get("status") != "pass":
        # This command is itself a sealed gate.  Keep only a role-safe summary.
        return emit({
            "status": portable.get("status", "inconclusive"),
            "summary": "sealed portable runtime evaluation did not pass",
            "evidence": [] if portable.get("status") == "pass" else [{
                "kind": "sealed_portable_failure" if portable.get("status") == "fail" else "tool_error",
                "summary": "sealed portable runtime evaluation did not pass",
                "oracle_status": "confirmed_candidate_defect" if portable.get("status") == "fail" else "unconfirmed",
            }],
            "tool_version": "OpenPLC-sealed+DVP48ES300R-sealed-composite-v1",
        })
    try:
        target_command = [
                sys.executable,
                str(Path(args.dvp_validator).resolve()),
                "--candidate", args.candidate,
                "--task-dir", args.task_dir,
                "--case-role", "sealed",
                "--timeout-seconds", str(args.dvp_timeout_seconds),
            ]
        if args.spool_root:
            target_command.extend(("--spool-root", args.spool_root))
        target = run_json(
            target_command,
            args.dvp_timeout_seconds + 30,
        )
    except (OSError, subprocess.TimeoutExpired, RuntimeError) as exc:
        return emit({
            "status": "inconclusive",
            "summary": "sealed DVP48ES300R evaluation did not complete",
            "evidence": [{"kind": "tool_error", "summary": f"{type(exc).__name__}: {exc}"}],
            "tool_version": "OpenPLC-sealed+DVP48ES300R-sealed-composite-v1",
        })
    target["tool_version"] = "OpenPLC-sealed+DVP48ES300R-sealed-composite-v1"
    if target.get("status") == "pass":
        target["summary"] = "sealed OpenPLC and DVP48ES300R simulator evaluations passed"
    return emit(target)


if __name__ == "__main__":
    raise SystemExit(main())

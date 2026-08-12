#!/usr/bin/env python3
"""Run hidden, stress, and OpenPLC checks as one fail-closed sealed gate."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


METHOD_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(METHOD_ROOT / "src"))

from plc_loop.dataset import load_task  # noqa: E402
from plc_loop.validators import DatasetScanValidator  # noqa: E402


def emit(value: dict) -> int:
    print(json.dumps(value, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--task-dir", required=True)
    parser.add_argument("--engine-root", required=True)
    parser.add_argument("--openplc-validator", required=True)
    parser.add_argument("--docker", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--runner", required=True)
    args = parser.parse_args()

    started = time.monotonic()
    candidate = Path(args.candidate).resolve()
    task_dir = Path(args.task_dir).resolve()
    artifact_root = Path.cwd()
    hidden_dir = artifact_root / "sealed_hidden_artifacts"
    stress_dir = artifact_root / "sealed_stress_artifacts"
    openplc_dir = artifact_root / "sealed_openplc_artifacts"
    hidden_dir.mkdir(exist_ok=True)
    stress_dir.mkdir(exist_ok=True)
    openplc_dir.mkdir(exist_ok=True)

    try:
        task = load_task(task_dir)
        hidden_validator = DatasetScanValidator(
            "sealed_hidden", "hidden", Path(args.engine_root).resolve(), sealed=True,
        )
        hidden_validator.preflight(task)
        hidden = hidden_validator.run(task, candidate, hidden_dir)
    except Exception as exc:
        return emit({
            "status": "inconclusive",
            "summary": "sealed hidden-test infrastructure failed",
            "evidence": [{"kind": "tool_error", "summary": f"{type(exc).__name__}: {exc}"}],
        })
    if hidden.status != "pass":
        result = hidden.to_dict()
        result["summary"] = f"sealed hidden-test gate {hidden.status}: {hidden.summary}"
        result["duration_ms"] = int((time.monotonic() - started) * 1000)
        result["tool_version"] = "sealed-hidden+stress-v0.3+deltaplc-subset-engine"
        return emit(result)

    try:
        stress_validator = DatasetScanValidator(
            "sealed_stress", "stress", Path(args.engine_root).resolve(), sealed=True,
        )
        stress_validator.preflight(task)
        stress = stress_validator.run(task, candidate, stress_dir)
    except Exception as exc:
        return emit({
            "status": "inconclusive",
            "summary": "sealed stress infrastructure failed",
            "evidence": [{"kind": "tool_error", "summary": f"{type(exc).__name__}: {exc}"}],
        })
    if stress.status != "pass":
        result = stress.to_dict()
        result["summary"] = f"sealed stress gate {stress.status}: {stress.summary}"
        result["duration_ms"] = int((time.monotonic() - started) * 1000)
        result["tool_version"] = "sealed-hidden+stress-v0.3+deltaplc-subset-engine"
        return emit(result)

    command = [
        sys.executable,
        str(Path(args.openplc_validator).resolve()),
        "--candidate", str(candidate),
        "--task-dir", str(task_dir),
        "--docker", args.docker,
        "--image", args.image,
        "--runner", str(Path(args.runner).resolve()),
    ]
    try:
        completed = subprocess.run(
            command, cwd=openplc_dir, text=True, capture_output=True,
            timeout=400, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return emit({
            "status": "inconclusive",
            "summary": "OpenPLC sealed sub-gate did not complete",
            "evidence": [{"kind": "tool_error", "summary": f"{type(exc).__name__}: {exc}"}],
        })
    (artifact_root / "sealed_openplc_subgate.stdout").write_text(completed.stdout, encoding="utf-8")
    (artifact_root / "sealed_openplc_subgate.stderr").write_text(completed.stderr, encoding="utf-8")
    try:
        openplc = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        return emit({
            "status": "inconclusive",
            "summary": "OpenPLC sealed sub-gate returned invalid JSON",
            "evidence": [{"kind": "tool_error", "summary": f"{exc}: {completed.stdout[-1200:]}"}],
        })
    status = openplc.get("status") if openplc.get("status") in {"pass", "fail", "inconclusive"} else "inconclusive"
    requirements = sorted(
        set(hidden.passed_requirement_ids)
        | set(stress.passed_requirement_ids)
        | set(openplc.get("passed_requirement_ids", []))
    )
    return emit({
        "status": status,
        "summary": (
            f"hidden: {hidden.summary}; stress: {stress.summary}; "
            f"OpenPLC: {openplc.get('summary', status)}"
        ),
        "evidence": openplc.get("evidence", []),
        "passed_requirement_ids": requirements if status == "pass" else [],
        "duration_ms": int((time.monotonic() - started) * 1000),
        "tool_version": "sealed-hidden+stress-v0.3+OpenPLC_v3@b5d41356dab4aeadca0dd7ca64ba542f870b595d",
    })


if __name__ == "__main__":
    raise SystemExit(main())

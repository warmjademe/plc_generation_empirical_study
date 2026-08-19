#!/usr/bin/env python3
"""Audit the qualified Boolean pilot and clean K3 run evidence."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from plc_loop.dataset import load_task
from plc_loop.ledger import EvidenceLedger
from plc_loop.orchestrator import BoundedSynthesisHarness, load_config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--method-root", required=True)
    parser.add_argument("--qualification", required=True)
    parser.add_argument("--aggregate", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    method = Path(args.method_root).resolve()
    output = Path(args.output).resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    config_path = method / "configs/kimi_k3_bool_pilot.json"
    config = load_config(config_path)
    dataset_root = method.parent / "datasets"
    qualification = json.loads(Path(args.qualification).read_text(encoding="utf-8"))
    aggregate = json.loads(Path(args.aggregate).read_text(encoding="utf-8"))
    scope = list(config["scope"]["task_ids"])
    checks: dict[str, object] = {}

    checks["qualification_pass"] = qualification.get("status") == "pass"
    checks["qualification_scope_exact"] = (
        qualification.get("task_count") == len(scope)
        and {item["task_id"] for item in qualification.get("tasks", [])} == set(scope)
        and all(item.get("qualified") for item in qualification.get("tasks", []))
    )

    preflight_tasks = []
    for task_id in scope:
        task = load_task(dataset_root / "tasks" / task_id)
        harness = BoundedSynthesisHarness(
            config,
            task,
            output.parent / f"unused-preflight-{task_id}",
            "evidence",
            client=None,
        )
        harness.preflight()
        preflight_tasks.append(task_id)
    checks["preflight_tasks"] = preflight_tasks

    clean_run_records = []
    all_runs_valid = True
    for aggregate_record in aggregate.get("runs", []):
        run = Path(aggregate_record["run_dir"])
        result = json.loads((run / "result.json").read_text(encoding="utf-8"))
        ledger = EvidenceLedger.verify(run / "ledger.jsonl")
        winner = result["attempts"][int(result["winning_attempt"]) - 1]
        gates = {item["name"]: item["status"] for item in winner["gates"]}
        sealed_events = sum(item["event_type"] == "sealed_judge_completed" for item in ledger)
        request_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted((run / "attempts").glob("*/request.json"))
        )
        run_valid = (
            result["status"] == "verified_success"
            and result["success"] is True
            and result["requested_model"] == "k3"
            and result["resolved_models"] == ["k3"]
            and all(gates.get(name) == "pass" for name in config["experiment"]["required_visible_gates"])
            and result["sealed_result"]["name"] == "sealed_openplc"
            and result["sealed_result"]["status"] == "pass"
            and sealed_events == 1
            and "tests_hidden.json" not in request_text
            and "reference.st" not in request_text
        )
        all_runs_valid = all_runs_valid and run_valid
        clean_run_records.append({
            "task_id": result["task_id"],
            "run_dir": str(run),
            "valid": run_valid,
            "candidates_used": result["candidates_used"],
            "resolved_models": result["resolved_models"],
            "visible_gate_statuses": gates,
            "sealed_status": result["sealed_result"]["status"],
            "sealed_summary": result["sealed_result"]["summary"],
            "sealed_event_count": sealed_events,
            "ledger_final_hash": ledger[-1]["event_hash"],
        })
    checks["clean_runs"] = clean_run_records
    checks["clean_runs_valid"] = all_runs_valid and len(clean_run_records) >= 1
    checks["aggregate_consistent"] = (
        aggregate.get("run_count") == len(clean_run_records)
        and aggregate.get("verified_successes") == len(clean_run_records)
        and aggregate.get("all_ledgers_valid") is True
        and aggregate.get("all_sealed_judges_invoked_once") is True
    )

    compiler = (method / "configs/../../../../Source_codes_Agents4PLC/tools/matiec/iec2iec").resolve()
    compiler_library = compiler.parent / "lib/ieclib.txt"
    plcverif = (method / "configs/../../../../Source_codes_Agents4PLC/tools/plcverif/plcverif-cli").resolve()
    nuxmv = (method / "configs/../../../../Source_codes_Agents4PLC/tools/nuXmv-2.0.0-Linux/bin/nuXmv").resolve()
    checks["tool_files"] = {
        "matiec": compiler.is_file(),
        "matiec_library": compiler_library.is_file(),
        "plcverif": plcverif.is_file(),
        "nuxmv": nuxmv.is_file(),
    }
    docker_check = subprocess.run(
        ["/snap/bin/docker", "image", "inspect", "plc-egbs/openplc-v3:b5d41356"],
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    checks["openplc_image_present"] = docker_check.returncode == 0

    secret_files = []
    credential_prefix = b"sk-" + b"kimi-"
    for path in method.rglob("*"):
        if not path.is_file() or "runs" in path.parts or "__pycache__" in path.parts or ".venv" in path.parts:
            continue
        try:
            if credential_prefix in path.read_bytes():
                secret_files.append(str(path.relative_to(method)))
        except OSError:
            pass
    checks["credential_marker_files"] = secret_files
    checks["credential_scan_pass"] = not secret_files

    test_env = dict(os.environ)
    test_env["PYTHONPATH"] = str(method / "src")
    tests = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=method,
        env=test_env,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
    test_log = output.with_suffix(".tests.log")
    test_log.write_text(tests.stdout + tests.stderr, encoding="utf-8")
    checks["unit_tests_pass"] = tests.returncode == 0

    required_booleans = [
        checks["qualification_pass"],
        checks["qualification_scope_exact"],
        checks["clean_runs_valid"],
        checks["aggregate_consistent"],
        all(checks["tool_files"].values()),
        checks["openplc_image_present"],
        checks["credential_scan_pass"],
        checks["unit_tests_pass"],
    ]
    document = {
        "schema_version": "1.0",
        "status": "pass" if all(required_booleans) else "fail",
        "config": str(config_path),
        "qualification": str(Path(args.qualification).resolve()),
        "aggregate": str(Path(args.aggregate).resolve()),
        "checks": checks,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": document["status"],
        "qualified_tasks": len(scope),
        "clean_verified_runs": len(clean_run_records),
        "unit_tests_pass": checks["unit_tests_pass"],
        "credential_scan_pass": checks["credential_scan_pass"],
    }, ensure_ascii=False))
    return 0 if document["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

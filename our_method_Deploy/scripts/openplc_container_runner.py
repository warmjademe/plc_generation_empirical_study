#!/usr/bin/env python3
"""Compile and execute one Boolean task inside a pinned OpenPLC v3 image."""

from __future__ import annotations

import argparse
import json
import shutil
import socket
import subprocess
import time
from pathlib import Path

TOOL_VERSION = "OpenPLC_v3@b5d41356dab4aeadca0dd7ca64ba542f870b595d+one-scan-request-ack-v2+visible-state-prefix-v1"


def compact_scan_prefix(case: dict, failing_step: int, failing_repeat: int) -> list[dict]:
    """Represent the executed case prefix as initial inputs plus later deltas."""
    prefix: list[dict] = []
    previous: dict = {}
    for step_index, step in enumerate(case.get("steps", []), start=1):
        if step_index > failing_step:
            break
        inputs = dict(step.get("inputs") or {})
        changes = {
            key: value for key, value in inputs.items()
            if step_index == 1 or previous.get(key) != value
        }
        prefix.append({
            "step": step_index,
            "repeat_through": (
                failing_repeat if step_index == failing_step else int(step.get("repeat", 1))
            ),
            "input_changes": changes,
        })
        previous = inputs
    return prefix


def rpc(message: str, retries: int = 80) -> str:
    last_error = None
    for _ in range(retries):
        try:
            with socket.create_connection(("127.0.0.1", 43628), timeout=0.5) as connection:
                connection.sendall((message + "\n").encode("utf-8"))
                return connection.recv(4096).decode("utf-8", errors="replace")
        except OSError as exc:
            last_error = exc
            time.sleep(0.05)
    raise RuntimeError(f"OpenPLC interactive server unavailable: {last_error}")


def start_runtime(webserver: Path, runtime_log):
    from pymodbus.client.sync import ModbusTcpClient

    process = subprocess.Popen(
        [str(webserver / "core/openplc")],
        cwd=webserver,
        stdout=runtime_log,
        stderr=subprocess.STDOUT,
        text=True,
    )
    rpc("exec_time()")
    rpc("start_modbus(1502)")
    client = ModbusTcpClient("127.0.0.1", port=1502)
    for _ in range(80):
        if client.connect():
            return process, client
        time.sleep(0.05)
    process.terminate()
    raise RuntimeError("OpenPLC Modbus server did not start")


def stop_runtime(process, client) -> None:
    try:
        client.close()
    finally:
        try:
            rpc("quit()", retries=3)
        except Exception:
            process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)


def value_key(value) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def read_coil(client, address: int) -> bool:
    response = client.read_coils(address, 1, unit=1)
    if response.isError():
        raise RuntimeError(f"Modbus read failed at coil {address}: {response}")
    return bool(response.bits[0])


def wait_for_value(client, address: int, expected: bool, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if read_coil(client, address) == expected:
            return
        time.sleep(0.002)
    raise RuntimeError("OpenPLC one-scan request/acknowledgement timed out")


def write_coil(client, address: int, value: bool, label: str) -> None:
    response = client.write_coil(address, value, unit=1)
    if response.isError():
        raise RuntimeError(f"Modbus {label} write failed at coil {address}: {response}")


def write_inputs(client, mapping: dict, values: dict) -> None:
    coil_count = int(mapping["input_coil_count"])
    coils = [False] * coil_count
    for name, value in values.items():
        item = mapping["inputs"][name]
        if item["kind"] == "bool":
            coils[int(item["address"])] = bool(value)
        elif item["kind"] == "selector":
            key = value_key(value)
            if key not in item["values"]:
                raise RuntimeError(f"no OpenPLC selector for {name}={value!r}")
            coils[int(item["values"][key])] = True
        else:
            raise RuntimeError(f"unknown OpenPLC input mapping kind {item['kind']!r}")
    # OpenPLC stores located BOOLs in packed bytes.  Some Modbus paths clear the
    # unused padding bits of a multi-coil write, which can overwrite adjacent
    # output or scan-handshake coils.  Write each declared input coil explicitly.
    for address, value in enumerate(coils):
        write_coil(client, address, value, "input")


def check_outputs(client, mapping: dict, expected: dict) -> tuple[dict, dict]:
    observed = {}
    matches = {}
    for name, value in expected.items():
        item = mapping["outputs"][name]
        if item["kind"] == "bool":
            actual = read_coil(client, int(item["address"]))
            observed[name] = actual
            matches[name] = actual == bool(value)
        elif item["kind"] == "expected_match":
            key = value_key(value)
            if key not in item["values"]:
                raise RuntimeError(f"no OpenPLC expectation comparator for {name}={value!r}")
            matches[name] = read_coil(client, int(item["values"][key]))
            observed[name] = value if matches[name] else "<different>"
        else:
            raise RuntimeError(f"unknown OpenPLC output mapping kind {item['kind']!r}")
    return observed, matches


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("program")
    parser.add_argument("suite")
    parser.add_argument("evidence_dir")
    args = parser.parse_args()

    webserver = Path("/workdir/webserver")
    evidence_dir = Path(args.evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    target = webserver / "st_files/egbs_candidate.st"
    shutil.copyfile(args.program, target)
    compile_result = subprocess.run(
        ["./scripts/compile_program.sh", target.name],
        cwd=webserver,
        text=True,
        capture_output=True,
        timeout=240,
        check=False,
    )
    compile_log = compile_result.stdout + compile_result.stderr
    (evidence_dir / "openplc_compile.log").write_text(compile_log, encoding="utf-8")
    if compile_result.returncode != 0 or "Compilation finished successfully!" not in compile_log:
        print(json.dumps({
            "status": "fail",
            "summary": "OpenPLC v3 rejected the executable harness",
            "evidence": [{"kind": "openplc_compile_error", "summary": compile_log[-2000:]}],
            "tool_version": TOOL_VERSION,
        }))
        return 0

    suite = json.loads(Path(args.suite).read_text(encoding="utf-8"))
    mapping = suite["openplc_mapping"]
    scan_seconds = float(suite["scan_period_ms"]) / 1000.0
    traces = []
    mismatches = []
    runtime_log_path = evidence_dir / "openplc_runtime.log"
    with runtime_log_path.open("w", encoding="utf-8") as runtime_log:
        for case in suite["cases"]:
            process = client = None
            try:
                process, client = start_runtime(webserver, runtime_log)
                request_address = int(mapping["step_request_address"])
                ack_address = int(mapping["step_ack_address"])
                request = read_coil(client, request_address)
                ack = read_coil(client, ack_address)
                if request != ack:
                    write_coil(client, request_address, ack, "step-request initialization")
                    wait_for_value(client, ack_address, ack, max(scan_seconds * 4.0, 1.0))
                    request = ack
                for step_index, step in enumerate(case["steps"], start=1):
                    for repeat_index in range(1, int(step["repeat"]) + 1):
                        write_inputs(client, mapping, step["inputs"])
                        request = not request
                        write_coil(client, request_address, request, "step request")
                        wait_for_value(client, ack_address, request, max(scan_seconds * 4.0, 1.0))
                        observed, matches = check_outputs(client, mapping, step["expect"])
                        checked = step.get("check") != "last_only" or repeat_index == int(step["repeat"])
                        row = {
                            "case": case["name"],
                            "step": step_index,
                            "repeat": repeat_index,
                            "inputs": step["inputs"],
                            "expected": step["expect"],
                            "observed": observed,
                            "matches": matches,
                            "checked": checked,
                        }
                        traces.append(row)
                        if checked and not all(matches.values()):
                            mismatches.append(row)
            finally:
                if process is not None and client is not None:
                    stop_runtime(process, client)

    (evidence_dir / "openplc_test_trace.json").write_text(
        json.dumps(traces, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    checked_traces = [row for row in traces if row["checked"]]
    case_requirements = {
        str(case["name"]): tuple(case.get("requirement_ids", []))
        for case in suite["cases"]
    }
    cases_by_name = {str(case["name"]): case for case in suite["cases"]}
    role = str(suite.get("case_role", "all"))
    oracle_label = "visible runtime oracle" if role == "feedback" else "sealed runtime oracle"
    if mismatches:
        evidence = []
        for row in mismatches[:8]:
            failing_outputs = [name for name, matched in row["matches"].items() if not matched]
            failure_trace = {
                "case": row["case"],
                "step": row["step"],
                "repeat": row["repeat"],
                "inputs": row["inputs"],
                "expected": {name: row["expected"][name] for name in failing_outputs},
                "observed": {name: row["observed"][name] for name in failing_outputs},
            }
            if suite.get("include_failure_prefix") is True:
                failure_trace["scan_prefix"] = compact_scan_prefix(
                    cases_by_name[str(row["case"])],
                    int(row["step"]),
                    int(row["repeat"]),
                )
            evidence.append({
                "kind": "openplc_functional_failure",
                "summary": (
                    f"{row['case']} scan step {row['step']} repeat {row['repeat']} "
                    f"differs on {', '.join(failing_outputs)}"
                ),
                "requirement_ids": list(case_requirements.get(str(row["case"]), ())),
                "trace": failure_trace,
                "oracle_status": "confirmed_candidate_defect",
            })
        print(json.dumps({
            "status": "fail",
            "summary": f"OpenPLC v3 failed {len(mismatches)} {role} functional scan observations",
            "evidence": evidence,
            "tool_version": TOOL_VERSION,
        }))
    else:
        requirements = sorted({rid for values in case_requirements.values() for rid in values})
        print(json.dumps({
            "status": "pass",
            "summary": (
                f"OpenPLC v3 passed {len(checked_traces)}/{len(checked_traces)} "
                f"checked {oracle_label} observations"
            ),
            "evidence": [],
            "passed_requirement_ids": requirements,
            "tool_version": TOOL_VERSION,
        }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

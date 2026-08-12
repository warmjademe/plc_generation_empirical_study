#!/usr/bin/env python3
"""Build an OpenPLC wrapper and execute the task's independent functional suite."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


def emit(value: dict) -> int:
    print(json.dumps(value, ensure_ascii=False))
    return 0


def value_key(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def st_literal(value: object, typ: str) -> str:
    if typ == "BOOL" and isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if typ == "INT" and isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if typ == "REAL" and isinstance(value, (int, float)) and not isinstance(value, bool):
        text = repr(float(value))
        return text if any(char in text for char in ".eE") else text + ".0"
    raise ValueError(f"test value {value!r} is incompatible with {typ}")


def located_bool(name: str, address: int) -> str:
    return f"    {name} AT %QX{address // 8}.{address % 8} : BOOL;"


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", value)


def case_role(case: dict) -> str:
    """Return the prespecified visibility role of an authored runtime case."""
    case_id = str(case.get("id", ""))
    name = str(case.get("name", "")).casefold()
    if case_id.startswith("FT") or "_feedback_" in name:
        return "feedback"
    return "sealed"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--task-dir", required=True)
    parser.add_argument("--docker", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--runner", required=True)
    parser.add_argument("--case-role", choices=("all", "feedback", "sealed"), default="all")
    parser.add_argument("--include-failure-prefix", action="store_true")
    args = parser.parse_args()
    if args.include_failure_prefix and args.case_role != "feedback":
        return emit({
            "status": "inconclusive",
            "summary": "stateful failure prefixes are restricted to visible feedback cases",
            "evidence": [{"kind": "oracle_error", "summary": "failure prefix requested for a non-feedback role"}],
        })

    candidate = Path(args.candidate).resolve()
    task_dir = Path(args.task_dir).resolve()
    # Do not resolve the snap launcher symlink: /snap/bin/docker dispatches through
    # snap, while its resolved target is the generic snap executable.
    docker = Path(args.docker)
    runner = Path(args.runner).resolve()
    openplc_suite = task_dir / "openplc_tests.json"
    metadata_path = task_dir / "metadata.json"
    missing = [str(path) for path in (candidate, openplc_suite, metadata_path, docker, runner) if not path.exists()]
    if missing:
        return emit({
            "status": "inconclusive",
            "summary": "OpenPLC sealed-judge infrastructure is incomplete",
            "evidence": [{"kind": "tool_error", "summary": f"missing: {', '.join(missing)}"}],
        })

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    suite = json.loads(openplc_suite.read_text(encoding="utf-8"))
    if suite.get("suite") != "openplc" or suite.get("independent_requirement_oracle") is not True:
        return emit({
            "status": "inconclusive",
            "summary": "OpenPLC suite is not declared as an independent requirement oracle",
            "evidence": [{"kind": "oracle_error", "summary": "invalid openplc_tests.json provenance"}],
        })
    selected_cases = [
        case for case in suite.get("cases", [])
        if args.case_role == "all" or case_role(case) == args.case_role
    ]
    if not selected_cases:
        return emit({
            "status": "inconclusive",
            "summary": f"OpenPLC suite has no {args.case_role} cases",
            "evidence": [{"kind": "oracle_error", "summary": "empty selected runtime-test role"}],
        })
    suite["cases"] = selected_cases
    suite["case_role"] = args.case_role
    suite["include_failure_prefix"] = bool(args.include_failure_prefix)
    inputs = metadata["interface"]["inputs"]
    outputs = metadata["interface"]["outputs"]
    supported_types = {"BOOL", "INT", "REAL"}
    if any(item["type"].upper() not in supported_types for item in inputs + outputs):
        return emit({
            "status": "inconclusive",
            "summary": "the OpenPLC adapter encountered an unsupported interface type",
            "evidence": [{"kind": "translator_unsupported", "summary": "supported types are BOOL, INT, and REAL"}],
        })

    located_lines = []
    internal_lines = []
    selector_lines = []
    input_args = []
    mapping = {"inputs": {}, "outputs": {}}
    address = 0
    for item in inputs:
        name = item["name"]
        typ = item["type"].upper()
        harness_name = f"EGBS_IN_{safe_name(name)}"
        if typ == "BOOL":
            located_lines.append(located_bool(harness_name, address))
            mapping["inputs"][name] = {"kind": "bool", "address": address}
            address += 1
        else:
            internal_lines.append(f"    {harness_name} : {typ};")
            values = []
            for case in suite["cases"]:
                for step in case["steps"]:
                    if name in step["inputs"] and step["inputs"][name] not in values:
                        values.append(step["inputs"][name])
            value_addresses = {}
            selector_names = []
            for index, value in enumerate(values):
                selector = f"EGBS_SEL_{safe_name(name)}_{index}"
                located_lines.append(located_bool(selector, address))
                value_addresses[value_key(value)] = address
                selector_names.append((selector, value))
                address += 1
            if not selector_names:
                return emit({"status": "inconclusive", "summary": f"OpenPLC suite has no values for input {name}", "evidence": []})
            for index, (selector, value) in enumerate(selector_names):
                keyword = "IF" if index == 0 else "ELSIF"
                selector_lines.append(f"{keyword} {selector} THEN")
                selector_lines.append(f"    {harness_name} := {st_literal(value, typ)};")
            selector_lines.append("ELSE")
            selector_lines.append(f"    {harness_name} := {st_literal(values[0], typ)};")
            selector_lines.append("END_IF;")
            mapping["inputs"][name] = {
                "kind": "selector",
                "type": typ,
                "values": value_addresses,
            }
        input_args.append(f"        {name} := {harness_name}")
    # The DUT must not run on OpenPLC's default all-FALSE inputs before the
    # first authored vector is installed.  A request/acknowledgement handshake
    # makes each test repetition correspond to exactly one DUT scan: the
    # runner writes every input first and toggles STEP_REQUEST last; the PLC
    # executes the DUT once and copies that value to STEP_ACK afterwards.
    mapping["input_coil_count"] = address
    request_address = address
    located_lines.append(located_bool("EGBS_STEP_REQUEST", request_address))
    mapping["step_request_address"] = request_address
    address += 1

    output_lines = []
    for item in outputs:
        name = item["name"]
        typ = item["type"].upper()
        if typ == "BOOL":
            harness_name = f"EGBS_OUT_{safe_name(name)}"
            located_lines.append(located_bool(harness_name, address))
            mapping["outputs"][name] = {"kind": "bool", "address": address}
            output_lines.append(f"{harness_name} := DUT.{name};")
            address += 1
        else:
            values = []
            for case in suite["cases"]:
                for step in case["steps"]:
                    if name in step["expect"] and step["expect"][name] not in values:
                        values.append(step["expect"][name])
            value_addresses = {}
            for index, value in enumerate(values):
                match_name = f"EGBS_MATCH_{safe_name(name)}_{index}"
                located_lines.append(located_bool(match_name, address))
                value_addresses[value_key(value)] = address
                literal = st_literal(value, typ)
                if typ == "REAL":
                    tolerance = float(suite.get("real_absolute_tolerance", 0.001))
                    lower = st_literal(float(value) - tolerance, "REAL")
                    upper = st_literal(float(value) + tolerance, "REAL")
                    output_lines.append(
                        f"{match_name} := (DUT.{name} >= {lower}) AND (DUT.{name} <= {upper});"
                    )
                else:
                    output_lines.append(f"{match_name} := DUT.{name} = {literal};")
                address += 1
            mapping["outputs"][name] = {
                "kind": "expected_match",
                "type": typ,
                "values": value_addresses,
            }
    ack_address = address
    located_lines.append(located_bool("EGBS_STEP_ACK", ack_address))
    mapping["step_ack_address"] = ack_address
    scan_ms = int(metadata["scan"]["period_ms"])
    wrapper = (
        candidate.read_text(encoding="utf-8").rstrip()
        + "\n\nPROGRAM EGBS_Harness\nVAR\n"
        + "\n".join(located_lines)
        + "\nEND_VAR\nVAR\n"
        + "\n".join(internal_lines)
        + ("\n" if internal_lines else "")
        + f"    DUT : {metadata['id']};\n"
        + "END_VAR\n\n"
        + "IF EGBS_STEP_REQUEST <> EGBS_STEP_ACK THEN\n"
        + "\n".join(f"    {line}" if line else line for line in selector_lines)
        + ("\n" if selector_lines else "")
        + "    DUT(\n"
        + ",\n".join(input_args)
        + "\n    );\n"
        + "\n".join(f"    {line}" for line in output_lines)
        + "\n    EGBS_STEP_ACK := EGBS_STEP_REQUEST;\n"
        + "END_IF;"
        + "\nEND_PROGRAM\n\n"
        + "CONFIGURATION Config0\n"
        + "    RESOURCE Res0 ON PLC\n"
        + f"        TASK Main(INTERVAL := T#{scan_ms}ms, PRIORITY := 0);\n"
        + "        PROGRAM Inst0 WITH Main : EGBS_Harness;\n"
        + "    END_RESOURCE\n"
        + "END_CONFIGURATION\n"
    )
    # Visible and sealed adapters may run for the same candidate.  Keep their
    # executable programs, suites, traces, and logs in role-specific directories
    # so the terminal judge cannot overwrite visible evidence.
    artifact_dir = Path.cwd() / f"openplc_{args.case_role}"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    program_path = artifact_dir / "openplc_program.st"
    program_path.write_text(wrapper, encoding="utf-8")
    suite["openplc_mapping"] = mapping
    suite_path = artifact_dir / "openplc_sealed_suite.json"
    suite_path.write_text(json.dumps(suite, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    command = [
        str(docker), "run", "--rm", "--network", "none",
        "--entrypoint", "/workdir/.venv/bin/python3",
        "-v", f"{program_path}:/input/program.st:ro",
        "-v", f"{suite_path}:/input/suite.json:ro",
        "-v", f"{runner}:/input/runner.py:ro",
        "-v", f"{artifact_dir}:/evidence",
        args.image,
        "/input/runner.py", "/input/program.st", "/input/suite.json", "/evidence",
    ]
    try:
        completed = subprocess.run(command, text=True, capture_output=True, timeout=360, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return emit({
            "status": "inconclusive",
            "summary": "OpenPLC container did not complete",
            "evidence": [{"kind": "tool_error", "summary": f"{type(exc).__name__}: {exc}"}],
        })
    (artifact_dir / "openplc_docker.stderr").write_text(completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        return emit({
            "status": "inconclusive",
            "summary": f"OpenPLC container exited with status {completed.returncode}",
            "evidence": [{"kind": "tool_error", "summary": (completed.stderr or completed.stdout)[-2000:]}],
        })
    try:
        document = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        return emit({
            "status": "inconclusive",
            "summary": "OpenPLC runner returned an invalid result document",
            "evidence": [{"kind": "tool_error", "summary": f"{exc}: {completed.stdout[-1500:]}"}],
        })
    return emit(document)


if __name__ == "__main__":
    raise SystemExit(main())

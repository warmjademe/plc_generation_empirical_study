"""Build a deterministic DVP48ES300R MAIN program and COMMGR mapping."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from .source_unit import Declaration, FunctionBlock, SourceUnitError


SUPPORTED_INTERFACE_TYPES = {"BOOL", "INT", "REAL"}


@dataclass(frozen=True)
class DvpHarness:
    declarations: tuple[Declaration, ...]
    body: str
    suite: dict[str, Any]
    mapping: dict[str, Any]


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", value)


def _value_key(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def _literal(value: object, type_name: str) -> str:
    if type_name == "BOOL" and isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if type_name == "INT" and isinstance(value, int) and not isinstance(value, bool):
        if not -32768 <= value <= 32767:
            raise SourceUnitError(f"INT test value is outside DVP 16-bit range: {value}")
        return str(value)
    if type_name == "REAL" and isinstance(value, (int, float)) and not isinstance(value, bool):
        text = repr(float(value))
        return text if any(char in text for char in ".eE") else text + ".0"
    raise SourceUnitError(f"test value {value!r} is incompatible with {type_name}")


def _case_role(case: dict[str, Any]) -> str:
    case_id = str(case.get("id", ""))
    name = str(case.get("name", "")).casefold()
    return "feedback" if case_id.startswith("FT") or "_feedback_" in name else "sealed"


def select_openplc_cases(suite: dict[str, Any], role: str) -> dict[str, Any]:
    if role not in {"feedback", "sealed", "all"}:
        raise SourceUnitError(f"unknown DVP test role {role!r}")
    if suite.get("suite") != "openplc" or suite.get("independent_requirement_oracle") is not True:
        raise SourceUnitError("openplc_tests.json is not an independent requirement oracle")
    selected = [
        case for case in suite.get("cases", [])
        if role == "all" or _case_role(case) == role
    ]
    if not selected:
        raise SourceUnitError(f"runtime suite has no {role} cases")
    result = dict(suite)
    result["cases"] = selected
    result["case_role"] = role
    return result


def _unique_values(suite: dict[str, Any], section: str, name: str) -> list[object]:
    values: list[object] = []
    keys: set[str] = set()
    for case in suite["cases"]:
        for step in case["steps"]:
            document = step[section]
            if name not in document:
                continue
            value = document[name]
            key = _value_key(value)
            if key not in keys:
                values.append(value)
                keys.add(key)
    return values


def build_dvp_harness(
    block: FunctionBlock,
    metadata: dict[str, Any],
    suite: dict[str, Any],
    *,
    first_m: int = 1000,
    image_identity_sha256: str | None = None,
    inline_candidate: bool = False,
    target: str = "DVP48ES300R",
    commgr_driver: str = "DVP48ES300R_SIM",
    maximum_m: int = 8191,
) -> DvpHarness:
    """Map a fixed task interface to Delta M devices.

    Non-Boolean values use one-hot M selectors and output-comparison bits.  This
    avoids undocumented D-register/REAL byte-order assumptions: COMMGR only
    writes and reads M coils, a path qualified independently on DVP-ES3.  The
    ISPSoft ``ModbusComm`` SDK takes the logical M index (M0 -> 0), not the
    protocol-level Modbus offset (M0 is commonly documented as 0x800).
    """
    if metadata.get("id") != block.name:
        raise SourceUnitError("candidate function-block name differs from task id")
    inputs = list(metadata["interface"]["inputs"])
    outputs = list(metadata["interface"]["outputs"])
    unsupported = sorted(
        {
            str(item["type"]).upper()
            for item in inputs + outputs
            if str(item["type"]).upper() not in SUPPORTED_INTERFACE_TYPES
        }
    )
    if unsupported:
        raise SourceUnitError(f"unsupported DVP interface types: {unsupported}")

    selected_suite = dict(suite)
    address = first_m
    mapping: dict[str, Any] = {
        "target": target,
        "commgr_driver": commgr_driver,
        "commgr_coil_base": 0,
        "inputs": {},
        "outputs": {},
    }
    if inline_candidate:
        # A PROGRAM-local variable has the same retained scan-to-scan storage
        # needed by the qualified benchmark fragment.  Inputs, outputs and
        # internal FB state are therefore materialised as MAIN locals before
        # the candidate body is inserted verbatim below.
        declarations = [
            Declaration(item.name, item.type_text, "VAR", item.initializer)
            for item in block.declarations
        ]
    else:
        declarations = [Declaration("EGBS_DUT", block.name, "VAR")]
    selector_lines: list[str] = []
    call_args: list[str] = []

    for item in inputs:
        name = str(item["name"])
        type_name = str(item["type"]).upper()
        if type_name == "BOOL":
            mapping["inputs"][name] = {
                "kind": "bool",
                "device": f"M{address}",
                "coil_address": address,
            }
            expression = f"M{address}"
            if inline_candidate:
                selector_lines.append(f"{name} := {expression};")
            address += 1
        else:
            variable = name if inline_candidate else f"EGBS_IN_{_safe_name(name)}"
            if not inline_candidate:
                declarations.append(Declaration(variable, type_name, "VAR"))
            values = _unique_values(selected_suite, "inputs", name)
            if not values:
                raise SourceUnitError(f"runtime suite has no values for input {name}")
            mapped_values: dict[str, Any] = {}
            for index, value in enumerate(values):
                selector = f"M{address}"
                mapped_values[_value_key(value)] = {
                    "device": selector,
                    "coil_address": address,
                }
                selector_lines.append(("IF" if index == 0 else "ELSIF") + f" {selector} THEN")
                selector_lines.append(f"    {variable} := {_literal(value, type_name)};")
                address += 1
            selector_lines.append("ELSE")
            selector_lines.append(f"    {variable} := {_literal(values[0], type_name)};")
            selector_lines.append("END_IF;")
            mapping["inputs"][name] = {
                "kind": "selector",
                "type": type_name,
                "values": mapped_values,
            }
            expression = variable
        call_args.append(f"        {name} := {expression}")

    output_lines: list[str] = []
    for item in outputs:
        name = str(item["name"])
        type_name = str(item["type"]).upper()
        if type_name == "BOOL":
            mapping["outputs"][name] = {
                "kind": "bool",
                "device": f"M{address}",
                "coil_address": address,
            }
            output_expression = name if inline_candidate else f"EGBS_DUT.{name}"
            output_lines.append(f"M{address} := {output_expression};")
            address += 1
            continue
        values = _unique_values(selected_suite, "expect", name)
        if not values:
            # A task may intentionally leave an output unobserved in one role.
            mapping["outputs"][name] = {"kind": "unobserved", "type": type_name}
            continue
        mapped_values: dict[str, Any] = {}
        for value in values:
            device = f"M{address}"
            mapped_values[_value_key(value)] = {
                "device": device,
                "coil_address": address,
            }
            if type_name == "REAL":
                tolerance = float(selected_suite.get("real_absolute_tolerance", 0.001))
                lower = _literal(float(value) - tolerance, "REAL")
                upper = _literal(float(value) + tolerance, "REAL")
                output_expression = name if inline_candidate else f"EGBS_DUT.{name}"
                output_lines.append(
                    f"{device} := ({output_expression} >= {lower}) AND ({output_expression} <= {upper});"
                )
            else:
                output_expression = name if inline_candidate else f"EGBS_DUT.{name}"
                output_lines.append(f"{device} := {output_expression} = {_literal(value, type_name)};")
            address += 1
        mapping["outputs"][name] = {
            "kind": "expected_match",
            "type": type_name,
            "values": mapped_values,
        }

    request_m = address
    ack_m = address + 1
    address = ack_m + 1
    identity_lines: list[str] = []
    if image_identity_sha256 is not None:
        if not re.fullmatch(r"[0-9a-f]{64}", image_identity_sha256):
            raise SourceUnitError("DVP image identity must be a lowercase SHA-256 digest")
        identity_bits: list[dict[str, Any]] = []
        # Sixty-four independently observable coils make a stale-image match
        # negligible while keeping the ES3 harness well below M8191.
        identity_value = int(image_identity_sha256[:16], 16)
        for bit_index in range(64):
            expected = bool((identity_value >> bit_index) & 1)
            identity_bits.append({
                "bit_index": bit_index,
                "device": f"M{address}",
                "coil_address": address,
                "expected": expected,
            })
            identity_lines.append(f"M{address} := {'TRUE' if expected else 'FALSE'};")
            address += 1
        mapping["image_identity"] = {
            "sha256": image_identity_sha256,
            "encoded_bits": 64,
            "bits": identity_bits,
        }
    if address - 1 > maximum_m:
        raise SourceUnitError(f"Delta M-device allocation exceeds M{maximum_m}")
    mapping["step_request"] = {
        "device": f"M{request_m}",
        "coil_address": request_m,
    }
    mapping["step_ack"] = {
        "device": f"M{ack_m}",
        "coil_address": ack_m,
    }
    mapping["first_m"] = first_m
    mapping["writable_last_m"] = ack_m
    mapping["last_m"] = address - 1
    mapping["scan_period_ms"] = int(metadata["scan"]["period_ms"])

    indented_selectors = [f"    {line}" for line in selector_lines]
    indented_outputs = [f"    {line}" for line in output_lines]
    # The identity assignments execute every PLC scan.  COMMGR verifies them
    # after each download before applying any test input, proving that the
    # simulator is running this exact candidate/harness image rather than a
    # stale program left by an earlier job.
    body_lines = list(identity_lines)
    body_lines.append(f"IF M{request_m} <> M{ack_m} THEN")
    body_lines.extend(indented_selectors)
    if inline_candidate:
        body_lines.extend(f"    {line}" if line else "" for line in block.body.splitlines())
    else:
        body_lines.append("    EGBS_DUT(")
        body_lines.append(",\r\n".join(call_args))
        body_lines.append("    );")
    body_lines.extend(indented_outputs)
    body_lines.append(f"    M{ack_m} := M{request_m};")
    body_lines.append("END_IF;")

    selected_suite["dvp_mapping"] = mapping
    selected_suite["fresh_instance_policy"] = "redownload_before_each_case"
    selected_suite["logical_scan_protocol"] = "toggle-request-wait-ack"
    selected_suite["execution_adapter"] = (
        "candidate-body-inlined-into-main" if inline_candidate else "function-block-instance"
    )
    return DvpHarness(tuple(declarations), "\r\n".join(body_lines), selected_suite, mapping)

"""Build and audit target-bound ISPSoft deployment adapters.

The generated function block remains address-free so the requirement Oracle can
exercise it independently.  This module deterministically binds that verified
interface to one controller's built-in digital terminals and emits a production
``MAIN`` program.  It deliberately supports only the hardware ranges calibrated
from the two frozen Delta CPU profiles; expansion modules require a separate,
user-supplied hardware configuration profile.
"""

from __future__ import annotations

import re
from typing import Any

from .source_unit import Declaration, FunctionBlock, SourceUnitError


class EngineeringConfigError(ValueError):
    """The field engineering contract cannot be safely materialised."""


def _dvp_octal_addresses(prefix: str, count: int) -> tuple[str, ...]:
    return tuple(f"{prefix}{index:o}" for index in range(count))


TARGET_PROFILES: dict[str, dict[str, Any]] = {
    "DVP48ES300R": {
        "profile": "delta-dvp-es3-dvp48es300r-built-in-io-v1",
        "input_addresses": _dvp_octal_addresses("X", 24),
        "output_addresses": _dvp_octal_addresses("Y", 24),
        "scan_period_ms": 100,
        "output_electrical_type": "relay",
        "source": "Delta DVP-ES3 Hardware and Operation Manual",
    },
    "AS228T-A": {
        "profile": "delta-as200-as228t-a-built-in-io-v1",
        "input_addresses": tuple(f"X0.{index}" for index in range(16)),
        "output_addresses": tuple(f"Y0.{index}" for index in range(12)),
        "scan_period_ms": 100,
        "output_electrical_type": "transistor NPN (sinking)",
        "source": "Delta AS Series Hardware and Operation Manual",
    },
}


_PROJECT_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,47}")


def _interface(contract: dict[str, Any]) -> list[dict[str, str]]:
    interface = contract.get("interface")
    if not isinstance(interface, dict):
        raise EngineeringConfigError("contract has no interface")
    result: list[dict[str, str]] = []
    for direction, key in (("input", "inputs"), ("output", "outputs")):
        values = interface.get(key)
        if not isinstance(values, list):
            raise EngineeringConfigError(f"contract interface {key} is invalid")
        for item in values:
            if not isinstance(item, dict):
                raise EngineeringConfigError(f"contract interface {key} contains a non-object")
            result.append({
                "symbol": str(item.get("name", "")),
                "direction": direction,
                "iec_type": str(item.get("type", "")).upper(),
                "description": str(item.get("description", "")),
            })
    return result


def _scan_period(contract: dict[str, Any]) -> int:
    if "scan_period_ms" in contract:
        return int(contract.get("scan_period_ms", 0))
    scan = contract.get("scan")
    return int(scan.get("period_ms", 0)) if isinstance(scan, dict) else 0


def build_engineering_template(
    contract: dict[str, Any], target: str, *, project_name: str | None = None
) -> dict[str, Any]:
    """Return a complete, editable built-in-I/O proposal for one contract."""

    profile = TARGET_PROFILES.get(target)
    if profile is None:
        raise EngineeringConfigError(f"unsupported engineering target {target}")
    ports = _interface(contract)
    unsupported = sorted({item["iec_type"] for item in ports if item["iec_type"] != "BOOL"})
    if unsupported:
        raise EngineeringConfigError(
            "downloadable built-in-I/O projects currently require BOOL external ports; "
            f"unsupported types: {', '.join(unsupported)}"
        )
    inputs = [item for item in ports if item["direction"] == "input"]
    outputs = [item for item in ports if item["direction"] == "output"]
    if len(inputs) > len(profile["input_addresses"]):
        raise EngineeringConfigError(
            f"{target} has only {len(profile['input_addresses'])} calibrated built-in digital inputs"
        )
    if len(outputs) > len(profile["output_addresses"]):
        raise EngineeringConfigError(
            f"{target} has only {len(profile['output_addresses'])} calibrated built-in digital outputs"
        )
    scan_period = _scan_period(contract)
    if scan_period != int(profile["scan_period_ms"]):
        raise EngineeringConfigError(
            f"the qualified {target} project template uses {profile['scan_period_ms']} ms, "
            f"but the contract requests {scan_period} ms"
        )
    safe_project = re.sub(r"[^A-Za-z0-9_]", "_", str(project_name or contract.get("task_id", "PLC_APP")))
    if not safe_project or not safe_project[0].isalpha():
        safe_project = "PLC_" + safe_project
    safe_project = safe_project[:48]
    mappings: list[dict[str, Any]] = []
    input_index = output_index = 0
    for item in ports:
        if item["direction"] == "input":
            address = profile["input_addresses"][input_index]
            input_index += 1
        else:
            address = profile["output_addresses"][output_index]
            output_index += 1
        mappings.append({
            **item,
            "address": address,
            "active_high": True,
            "safe_logical_value": False,
            "terminal_note": "",
        })
    return {
        "schema_version": 1,
        "mode": "downloadable_project",
        "target": target,
        "target_profile": profile["profile"],
        "project_name": safe_project,
        "scan_period_ms": scan_period,
        "input_addresses": list(profile["input_addresses"]),
        "output_addresses": list(profile["output_addresses"]),
        "output_electrical_type": profile["output_electrical_type"],
        "profile_source": profile["source"],
        "mappings": mappings,
        "wiring_review_acknowledged": False,
        "field_acceptance_acknowledged": False,
        "scope": "built-in digital I/O only; no expansion, analogue, motion, or network modules",
    }


def validate_engineering_config(
    config: dict[str, Any], contract: dict[str, Any], target: str
) -> dict[str, Any]:
    """Validate and normalize a user-confirmed field mapping contract."""

    if not isinstance(config, dict):
        raise EngineeringConfigError("engineering_config must be an object")
    profile = TARGET_PROFILES.get(target)
    if profile is None:
        raise EngineeringConfigError(f"unsupported engineering target {target}")
    if config.get("schema_version") != 1 or config.get("mode") != "downloadable_project":
        raise EngineeringConfigError("engineering_config schema or mode is invalid")
    if config.get("target") != target or config.get("target_profile") != profile["profile"]:
        raise EngineeringConfigError("engineering_config target profile differs from the selected PLC")
    project_name = str(config.get("project_name", ""))
    if _PROJECT_NAME.fullmatch(project_name) is None:
        raise EngineeringConfigError(
            "project_name must start with a letter and contain at most 48 ASCII letters, digits, or underscores"
        )
    expected_scan = _scan_period(contract)
    if int(config.get("scan_period_ms", 0)) != expected_scan:
        raise EngineeringConfigError("engineering scan period differs from the frozen contract")
    if expected_scan != int(profile["scan_period_ms"]):
        raise EngineeringConfigError("engineering scan period differs from the qualified project template")
    if config.get("wiring_review_acknowledged") is not True:
        raise EngineeringConfigError("the physical I/O mapping has not been explicitly confirmed")
    if config.get("field_acceptance_acknowledged") is not True:
        raise EngineeringConfigError("the mandatory physical commissioning boundary has not been acknowledged")

    expected = {(item["symbol"], item["direction"]): item for item in _interface(contract)}
    mappings = config.get("mappings")
    if not isinstance(mappings, list) or len(mappings) != len(expected):
        raise EngineeringConfigError("every contract port must have exactly one physical mapping")
    normalized: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()
    seen_addresses: set[str] = set()
    for raw in mappings:
        if not isinstance(raw, dict):
            raise EngineeringConfigError("a physical mapping is not an object")
        symbol = str(raw.get("symbol", ""))
        direction = str(raw.get("direction", ""))
        key = (symbol, direction)
        port = expected.get(key)
        if port is None or key in seen_keys:
            raise EngineeringConfigError(f"unexpected or duplicate physical mapping for {symbol}")
        seen_keys.add(key)
        iec_type = str(raw.get("iec_type", "")).upper()
        if iec_type != port["iec_type"] or iec_type != "BOOL":
            raise EngineeringConfigError(f"physical mapping type differs for {symbol}")
        address = str(raw.get("address", "")).upper()
        allowed = (
            profile["input_addresses"] if direction == "input" else profile["output_addresses"]
        )
        if address not in allowed:
            raise EngineeringConfigError(f"{address or '<empty>'} is not a built-in {direction} of {target}")
        if address in seen_addresses:
            raise EngineeringConfigError(f"physical address {address} is assigned more than once")
        seen_addresses.add(address)
        active_high = raw.get("active_high")
        safe_value = raw.get("safe_logical_value")
        if not isinstance(active_high, bool) or not isinstance(safe_value, bool):
            raise EngineeringConfigError(f"polarity and safe value must be BOOL for {symbol}")
        normalized.append({
            **port,
            "address": address,
            "active_high": active_high,
            "safe_logical_value": safe_value,
            "terminal_note": str(raw.get("terminal_note", ""))[:200],
        })
    if set(expected) != seen_keys:
        raise EngineeringConfigError("the physical mapping does not cover the complete interface")
    return {
        "schema_version": 1,
        "mode": "downloadable_project",
        "target": target,
        "target_profile": profile["profile"],
        "project_name": project_name,
        "scan_period_ms": expected_scan,
        "output_electrical_type": profile["output_electrical_type"],
        "profile_source": profile["source"],
        "mappings": normalized,
        "wiring_review_acknowledged": True,
        "field_acceptance_acknowledged": True,
        "scope": "built-in digital I/O only; no expansion, analogue, motion, or network modules",
    }


def render_deployment_program(
    block: FunctionBlock, contract: dict[str, Any], config: dict[str, Any]
) -> tuple[tuple[Declaration, ...], str, str]:
    """Return ISPSoft declarations/body and a readable IEC ``PROGRAM MAIN``."""

    normalized = validate_engineering_config(config, contract, str(config.get("target", "")))
    by_key = {
        (item["symbol"], item["direction"]): item for item in normalized["mappings"]
    }
    declared = {
        (item.name, "input" if item.scope == "VAR_INPUT" else "output")
        for item in block.declarations
        if item.scope in {"VAR_INPUT", "VAR_OUTPUT"}
    }
    expected = {
        (item["symbol"], item["direction"])
        for item in normalized["mappings"]
    }
    if declared != expected:
        raise SourceUnitError("candidate interface differs from the confirmed engineering mapping")

    def physical_expression(item: dict[str, Any]) -> str:
        return item["address"] if item["active_high"] else f"NOT {item['address']}"

    input_ports = [
        item for item in normalized["mappings"] if item["direction"] == "input"
    ]
    output_ports = [
        item for item in normalized["mappings"] if item["direction"] == "output"
    ]
    body_lines = [
        "(* 由已确认的物理 I/O 映射确定性生成；修改接线后必须重新生成并验证。 *)",
        "APP(",
        ",\r\n".join(
            f"    {item['symbol']} := {physical_expression(item)}" for item in input_ports
        ),
        ");",
    ]
    for item in output_ports:
        logical = f"APP.{item['symbol']}"
        expression = logical if item["active_high"] else f"NOT {logical}"
        body_lines.append(f"{item['address']} := {expression};")
    body = "\r\n".join(line for line in body_lines if line != "")
    declarations = (Declaration("APP", block.name, "VAR"),)
    readable = "\n".join((
        "PROGRAM MAIN",
        "VAR",
        f"    APP : {block.name};",
        "END_VAR",
        body.replace("\r\n", "\n"),
        "END_PROGRAM",
        "",
    ))
    return declarations, body, readable

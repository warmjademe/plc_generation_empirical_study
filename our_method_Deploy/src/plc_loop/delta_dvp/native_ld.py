"""Deterministically export Ladder IR as an ISPSoft native LD source unit.

The serialization in this module is intentionally limited to the ISPSoft 3.24
constructs calibrated from official exports.  Unsupported Ladder IR fails
closed; the exporter never substitutes an ST body while labelling it as LD.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..ladder import LadderError, compile_ladder_document
from .source_unit import Declaration, SourceUnitError, _render_variable_section, parse_function_block


class NativeLdError(SourceUnitError):
    """The Ladder IR uses an ISPSoft LD construct that is not calibrated."""


@dataclass(frozen=True)
class NativeLdCompilation:
    """One deterministic ISPSoft native-LD function-block source unit."""

    source: bytes
    network_count: int
    calibrated_subset: str = "ispsoft-3.24-dvp-es3-boolean-ld-v1"


# Values confirmed with controlled exports from ISPSoft 3.24 on 2026-08-22.
_CONTACT_NO = 1
_CONTACT_NC = 2
_EMPTY_BRANCH_CELL = 5
_PARALLEL_GROUP = 6
_COIL_NORMAL = 13
_COIL_SET = 15
_COIL_RESET = 16


def _node(node_type: int, **fields: str | int) -> list[str]:
    rows = ["[LD_NODE]", f"TYPE={node_type}"]
    rows.extend(f"{name}={value}" for name, value in fields.items())
    rows.append("[END_LD_NODE]")
    return rows


def _contact_branches(
    expression: Any,
    context: str,
    depth: int = 0,
    *,
    negated: bool = False,
) -> list[list[tuple[str, bool]]]:
    """Lower a Boolean expression to bounded disjunctive normal form.

    Negation is pushed to variable contacts with De Morgan's laws.  ISPSoft
    therefore receives only calibrated normally-open and normally-closed
    contacts even when the Ladder IR contains ``NOT`` around a compound
    Boolean expression.
    """
    if depth > 32 or not isinstance(expression, dict):
        raise NativeLdError(f"{context} is not a supported Boolean contact expression")
    op = str(expression.get("op", "")).lower()
    if op == "var":
        return [[(str(expression.get("name", "")), negated)]]
    if op == "not":
        child = expression.get("arg")
        return _contact_branches(
            child,
            f"{context}.arg",
            depth + 1,
            negated=not negated,
        )
    # Under a negation, AND and OR exchange roles.  The result remains a DNF
    # list: the effective AND is a Cartesian product and the effective OR is
    # concatenation.
    effective_op = (
        "or" if op == "and" and negated
        else "and" if op == "or" and negated
        else op
    )
    if effective_op == "and":
        arguments = expression.get("args")
        if not isinstance(arguments, list) or len(arguments) < 2:
            raise NativeLdError(f"{context}: {op.upper()} requires at least two arguments")
        branches: list[list[tuple[str, bool]]] = [[]]
        for index, argument in enumerate(arguments):
            child = _contact_branches(
                argument,
                f"{context}.args[{index}]",
                depth + 1,
                negated=negated,
            )
            branches = [left + right for left in branches for right in child]
            if len(branches) > 64 or any(len(branch) > 32 for branch in branches):
                raise NativeLdError(f"{context}: normalized contact topology exceeds the calibrated limit")
        return branches
    if effective_op == "or":
        arguments = expression.get("args")
        if not isinstance(arguments, list) or len(arguments) < 2:
            raise NativeLdError(f"{context}: {op.upper()} requires at least two arguments")
        branches: list[list[tuple[str, bool]]] = []
        for index, argument in enumerate(arguments):
            branches.extend(_contact_branches(
                argument,
                f"{context}.args[{index}]",
                depth + 1,
                negated=negated,
            ))
            if len(branches) > 64:
                raise NativeLdError(f"{context}: normalized contact topology exceeds the calibrated limit")
        return branches
    raise NativeLdError(
        f"{context}: operator {op!r} has no calibrated ISPSoft native-LD encoding"
    )


def _root_link_rows(branches: list[list[tuple[str, bool]]]) -> list[str]:
    if not branches or any(not branch for branch in branches):
        raise NativeLdError("a native LD network must contain at least one contact per branch")
    width = max(len(branch) for branch in branches)
    rows: list[str] = []
    for branch in branches:
        for name, normally_closed in branch:
            rows.extend(_node(_CONTACT_NC if normally_closed else _CONTACT_NO, DEV_NAME=name))
        for _ in range(width - len(branch)):
            rows.extend(_node(_EMPTY_BRANCH_CELL, DEV_NAME=""))
    if len(branches) > 1:
        rows.extend(_node(_PARALLEL_GROUP, LNK_C=len(branches), LNK_L=width))
    return rows


def _coil_type(instruction: Any, context: str) -> tuple[int, str]:
    if not isinstance(instruction, dict) or str(instruction.get("type", "")).lower() != "coil":
        raise NativeLdError(
            f"{context}: only normal, set, and reset coils have calibrated ISPSoft native-LD encodings"
        )
    mode = str(instruction.get("mode", "normal")).lower()
    node_type = {
        "normal": _COIL_NORMAL,
        "set": _COIL_SET,
        "reset": _COIL_RESET,
    }.get(mode)
    if node_type is None:
        raise NativeLdError(f"{context}: unsupported coil mode {mode!r}")
    return node_type, str(instruction.get("target", ""))


def _network_rows(
    network_id: int,
    label: str,
    comment: str,
    branches: list[list[tuple[str, bool]]],
    coil_type: int,
    target: str,
) -> list[str]:
    # ISPSoft stores comments between an IEC comment pair in the property area.
    safe_comment = comment.replace("(*", "(").replace("*)", ")")
    return [
        "<NETWORK_START>",
        "<PROPERTIES_START>",
        f"NET_ID={network_id}",
        f"NET_LABEL={label}",
        "NET_ACTIVE=TRUE",
        "NET_BOOKMARK=FALSE",
        "NET_MODIFY=TRUE",
        "NET_FOLD=FALSE",
        "(*",
        safe_comment,
        "*)",
        "<PROPERTIES_END>",
        "<ROOTLINK_START>",
        *_root_link_rows(branches),
        "<ROOTLINK_END>",
        "<OUTLINK_START>",
        *_node(coil_type, DEV_NAME=target),
        "<OUTLINK_END>",
        "<NETWORK_END>",
    ]


def render_native_ld_function_block_source(
    document: dict[str, Any],
    interface_text: str,
    expected_name: str | None = None,
) -> NativeLdCompilation:
    """Validate Ladder IR and render an importable ISPSoft ``[FB,LD]`` unit.

    A rung containing several coils is emitted as several equivalent networks,
    one coil per network.  This avoids relying on an uncalibrated multi-output
    serialization while preserving scan semantics for the supported coil-only
    subset.
    """
    try:
        portable = compile_ladder_document(document, interface_text, expected_name)
    except LadderError as exc:
        raise NativeLdError(str(exc)) from exc
    normalized = portable.document
    block = parse_function_block(portable.st_program)
    networks: list[list[str]] = []
    network_id = 1
    for rung_index, rung in enumerate(normalized["rungs"]):
        branches = _contact_branches(rung["condition"], f"rungs[{rung_index}].condition")
        instructions = rung["instructions"]
        for instruction_index, instruction in enumerate(instructions):
            node_type, target = _coil_type(
                instruction,
                f"rungs[{rung_index}].instructions[{instruction_index}]",
            )
            suffix = "" if len(instructions) == 1 else f"_{instruction_index + 1}"
            networks.append(
                _network_rows(
                    network_id,
                    f"{rung['id']}{suffix}",
                    str(rung.get("comment", "")),
                    branches,
                    node_type,
                    target,
                )
            )
            network_id += 1

    source = _render_native_ld_source(block.name, block.declarations, networks)
    return NativeLdCompilation(source=source, network_count=len(networks))


def _render_native_ld_source(
    name: str,
    declarations: tuple[Declaration, ...],
    networks: list[list[str]],
) -> bytes:
    if not networks:
        raise NativeLdError("native LD function block has no networks")
    rows = [
        "<GroupPOUFolder>",
        "<FBFolder>",
        "<FolderContent>",
        "ContentType=1",
        f"ContentName={name} [FB,LD]",
        f"ContentPath=FB/{name} [FB,LD]",
        "</FolderContent>",
        "</FBFolder>",
        "</GroupPOUFolder>",
        "<POU>",
        f"P_Name={name}",
        "P_En_Eno=TRUE",
        "P_Last_Chg=",
        "P_type=1",
        "P_Rtn_Type=",
        "P_Lang=1",
        "P_Step=0",
        "P_Version=1.00",
        "P_DeltaFB=FALSE",
        "P_Security=",
        "P_Active=TRUE",
        "P_Priority=9999",
        "P_DFBName=",
        "(*",
        "",
        "*)",
        _render_variable_section(declarations),
        "<VAR_EXTERN>",
        "</VAR_EXTERN>",
        "<VAR_EXTERN_C>",
        "</VAR_EXTERN_C>",
    ]
    for network in networks:
        rows.extend(network)
    rows.extend(["</POU>", ""])
    return "\r\n".join(rows).encode("utf-8")

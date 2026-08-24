"""Typed, deterministic ladder-diagram intermediate representation.

The model emits this JSON representation instead of drawing pixels or writing
vendor-private ISPSoft files.  One accepted document is deterministically
lowered to IEC 61131-3 ST for the existing verification toolchain and rendered
to SVG for human inspection.  The supported subset is intentionally bounded;
unknown constructs fail closed instead of being guessed or silently dropped.
"""

from __future__ import annotations

import html
import json
import math
import re
from dataclasses import dataclass
from typing import Any


IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
DIRECT_DEVICE = re.compile(r"^(?:[MXYSDTC][0-9]+)$", re.IGNORECASE)
SUPPORTED_TYPES = {"BOOL", "INT", "DINT", "REAL"}
NUMERIC_TYPES = {"INT", "DINT", "REAL"}
RESERVED_PREFIX = "EGBS_"


class LadderError(ValueError):
    """Raised when ladder IR is malformed, unsafe, or cannot be typed."""


@dataclass(frozen=True)
class Symbol:
    name: str
    type_name: str
    scope: str
    initial: bool | int | float | None = None


@dataclass(frozen=True)
class LadderCompilation:
    document: dict[str, Any]
    canonical_json: str
    st_program: str
    svg: str


def _exact_keys(value: dict[str, Any], allowed: set[str], context: str) -> None:
    unexpected = sorted(set(value) - allowed)
    if unexpected:
        raise LadderError(f"{context} contains unsupported keys: {unexpected}")


def _identifier(value: Any, context: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise LadderError(f"{context} must be an IEC identifier")
    if value.upper().startswith(RESERVED_PREFIX):
        raise LadderError(f"{context} uses a reserved harness name: {value}")
    return value


def parse_interface(interface_text: str) -> tuple[str, list[Symbol]]:
    """Extract the fixed function-block identity and public declarations."""
    match = re.search(
        r"(?im)^\s*FUNCTION_BLOCK\s+([A-Za-z_][A-Za-z0-9_]*)\s*$",
        interface_text,
    )
    if not match:
        raise LadderError("fixed interface has no FUNCTION_BLOCK declaration")
    name = match.group(1)
    symbols: list[Symbol] = []
    for scope in ("VAR_INPUT", "VAR_OUTPUT"):
        block = re.search(
            rf"(?ims)^\s*{scope}\s*$\s*(.*?)^\s*END_VAR\s*$",
            interface_text,
        )
        if not block:
            raise LadderError(f"fixed interface has no {scope} block")
        for row in block.group(1).splitlines():
            stripped = re.sub(r"\(\*.*?\*\)", "", row).strip()
            if not stripped:
                continue
            declaration = re.fullmatch(
                r"([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(BOOL|INT|DINT|REAL)\s*;",
                stripped,
                flags=re.IGNORECASE,
            )
            if not declaration:
                raise LadderError(f"unsupported declaration in {scope}: {stripped}")
            symbols.append(Symbol(declaration.group(1), declaration.group(2).upper(), scope))
    folded = [item.name.casefold() for item in symbols]
    if len(folded) != len(set(folded)):
        raise LadderError("fixed interface contains duplicate symbols")
    return name, symbols


def _literal(value: Any, type_name: str, context: str) -> str:
    if type_name == "BOOL":
        if not isinstance(value, bool):
            raise LadderError(f"{context} must be a BOOL literal")
        return "TRUE" if value else "FALSE"
    if type_name in {"INT", "DINT"}:
        if not isinstance(value, int) or isinstance(value, bool):
            raise LadderError(f"{context} must be an integer literal")
        if type_name == "INT" and not -32768 <= value <= 32767:
            raise LadderError(f"{context} is outside the IEC INT range")
        return str(value)
    if type_name == "REAL":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise LadderError(f"{context} must be a REAL literal")
        if not math.isfinite(float(value)):
            raise LadderError(f"{context} must be finite")
        rendered = repr(float(value))
        return rendered if any(mark in rendered for mark in (".", "e", "E")) else rendered + ".0"
    raise LadderError(f"{context} uses unsupported type {type_name}")


def _locals(document: dict[str, Any], public: list[Symbol]) -> list[Symbol]:
    raw_locals = document.get("locals", [])
    if not isinstance(raw_locals, list):
        raise LadderError("locals must be an array")
    if len(raw_locals) > 64:
        raise LadderError("locals exceeds the supported limit of 64")
    names = {item.name.casefold() for item in public}
    result: list[Symbol] = []
    for index, item in enumerate(raw_locals):
        context = f"locals[{index}]"
        if not isinstance(item, dict):
            raise LadderError(f"{context} must be an object")
        _exact_keys(item, {"name", "type", "initial"}, context)
        name = _identifier(item.get("name"), f"{context}.name")
        if DIRECT_DEVICE.fullmatch(name):
            raise LadderError(f"{context}.name resembles a direct Delta device: {name}")
        folded = name.casefold()
        if folded in names:
            raise LadderError(f"duplicate symbol {name}")
        type_name = str(item.get("type", "")).upper()
        if type_name not in SUPPORTED_TYPES:
            raise LadderError(f"{context}.type must be one of {sorted(SUPPORTED_TYPES)}")
        initial = item.get("initial")
        if "initial" in item:
            _literal(initial, type_name, f"{context}.initial")
        result.append(Symbol(name, type_name, "VAR", initial))
        names.add(folded)
    return result


def _symbol_table(symbols: list[Symbol]) -> dict[str, Symbol]:
    return {item.name.casefold(): item for item in symbols}


def _symbol(name: Any, symbols: dict[str, Symbol], context: str) -> Symbol:
    identifier = _identifier(name, context)
    try:
        return symbols[identifier.casefold()]
    except KeyError as exc:
        raise LadderError(f"{context} references unknown symbol {identifier}") from exc


def _writable_symbol(name: Any, symbols: dict[str, Symbol], context: str) -> Symbol:
    item = _symbol(name, symbols, context)
    if item.scope == "VAR_INPUT":
        raise LadderError(f"{context} cannot write fixed input {item.name}")
    return item


def _compatible(left: str, right: str) -> bool:
    return left == right or (left in NUMERIC_TYPES and right in NUMERIC_TYPES)


def _expression(
    value: Any,
    symbols: dict[str, Symbol],
    context: str,
    depth: int = 0,
) -> tuple[str, str, str]:
    """Return ST, inferred type, and a short ladder label."""
    if depth > 32:
        raise LadderError(f"{context} exceeds the expression-depth limit")
    if not isinstance(value, dict):
        raise LadderError(f"{context} must be an expression object")
    op = str(value.get("op", "")).lower()
    if op == "var":
        _exact_keys(value, {"op", "name"}, context)
        item = _symbol(value.get("name"), symbols, f"{context}.name")
        return item.name, item.type_name, item.name
    if op == "const":
        _exact_keys(value, {"op", "type", "value"}, context)
        type_name = str(value.get("type", "")).upper()
        rendered = _literal(value.get("value"), type_name, f"{context}.value")
        return rendered, type_name, rendered
    if op == "not":
        _exact_keys(value, {"op", "arg"}, context)
        child, child_type, label = _expression(value.get("arg"), symbols, f"{context}.arg", depth + 1)
        if child_type != "BOOL":
            raise LadderError(f"{context}.arg must be BOOL")
        return f"NOT ({child})", "BOOL", f"NOT {label}"
    if op in {"and", "or", "xor"}:
        _exact_keys(value, {"op", "args"}, context)
        args = value.get("args")
        if not isinstance(args, list) or len(args) < 2:
            raise LadderError(f"{context}.args must contain at least two expressions")
        if len(args) > 16:
            raise LadderError(f"{context}.args exceeds the supported limit of 16")
        compiled = [_expression(item, symbols, f"{context}.args[{index}]", depth + 1) for index, item in enumerate(args)]
        if any(type_name != "BOOL" for _, type_name, _ in compiled):
            raise LadderError(f"{context}.args must all be BOOL")
        operator = {"and": "AND", "or": "OR", "xor": "XOR"}[op]
        return (
            "(" + f") {operator} (".join(item[0] for item in compiled) + ")",
            "BOOL",
            f" {operator} ".join(item[2] for item in compiled),
        )
    if op == "compare":
        _exact_keys(value, {"op", "operator", "left", "right"}, context)
        operator = str(value.get("operator", "")).upper()
        operators = {"EQ": "=", "NE": "<>", "LT": "<", "LE": "<=", "GT": ">", "GE": ">="}
        if operator not in operators:
            raise LadderError(f"{context}.operator is unsupported")
        left, left_type, left_label = _expression(value.get("left"), symbols, f"{context}.left", depth + 1)
        right, right_type, right_label = _expression(value.get("right"), symbols, f"{context}.right", depth + 1)
        if not _compatible(left_type, right_type):
            raise LadderError(f"{context} compares incompatible types {left_type} and {right_type}")
        symbol = operators[operator]
        return f"({left}) {symbol} ({right})", "BOOL", f"{left_label} {symbol} {right_label}"
    if op == "arithmetic":
        _exact_keys(value, {"op", "operator", "left", "right"}, context)
        operator = str(value.get("operator", "")).upper()
        operators = {"ADD": "+", "SUB": "-", "MUL": "*"}
        if operator not in operators:
            raise LadderError(f"{context}.operator is unsupported")
        left, left_type, left_label = _expression(value.get("left"), symbols, f"{context}.left", depth + 1)
        right, right_type, right_label = _expression(value.get("right"), symbols, f"{context}.right", depth + 1)
        if left_type not in NUMERIC_TYPES or right_type not in NUMERIC_TYPES:
            raise LadderError(f"{context} arithmetic operands must be numeric")
        result_type = "REAL" if "REAL" in {left_type, right_type} else "DINT" if "DINT" in {left_type, right_type} else "INT"
        symbol = operators[operator]
        return f"({left}) {symbol} ({right})", result_type, f"{left_label} {symbol} {right_label}"
    raise LadderError(f"{context}.op is unsupported: {op!r}")


def _comment(value: Any, context: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, str) or len(value) > 500:
        raise LadderError(f"{context} must be a string of at most 500 characters")
    return value.replace("(*", "(").replace("*)", ")").strip()


def _instruction(
    item: Any,
    condition_st: str,
    symbols: dict[str, Symbol],
    context: str,
) -> tuple[list[str], str, str]:
    if not isinstance(item, dict):
        raise LadderError(f"{context} must be an object")
    kind = str(item.get("type", "")).lower()
    if kind == "coil":
        _exact_keys(item, {"type", "target", "mode"}, context)
        target = _writable_symbol(item.get("target"), symbols, f"{context}.target")
        if target.type_name != "BOOL":
            raise LadderError(f"{context}.target must be BOOL")
        mode = str(item.get("mode", "normal")).lower()
        if mode == "normal":
            return [f"{target.name} := {condition_st};"], f"({target.name})", "normal"
        if mode not in {"set", "reset"}:
            raise LadderError(f"{context}.mode must be normal, set, or reset")
        literal = "TRUE" if mode == "set" else "FALSE"
        return [f"IF {condition_st} THEN", f"    {target.name} := {literal};", "END_IF;"], f"({mode[0].upper()} {target.name})", mode
    if kind == "assign":
        _exact_keys(item, {"type", "target", "value"}, context)
        target = _writable_symbol(item.get("target"), symbols, f"{context}.target")
        expression, expression_type, label = _expression(item.get("value"), symbols, f"{context}.value")
        if not _compatible(target.type_name, expression_type):
            raise LadderError(f"{context} assigns {expression_type} to {target.type_name}")
        return [f"IF {condition_st} THEN", f"    {target.name} := {expression};", "END_IF;"], f"[MOV {label} -> {target.name}]", "assign"
    if kind == "increment_saturating":
        _exact_keys(item, {"type", "target", "limit"}, context)
        target = _writable_symbol(item.get("target"), symbols, f"{context}.target")
        if target.type_name not in {"INT", "DINT"}:
            raise LadderError(f"{context}.target must be INT or DINT")
        limit = item.get("limit")
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise LadderError(f"{context}.limit must be a positive integer")
        if target.type_name == "INT" and limit > 32767:
            raise LadderError(f"{context}.limit exceeds the IEC INT range")
        return [
            f"IF ({condition_st}) AND ({target.name} < {limit}) THEN",
            f"    {target.name} := {target.name} + 1;",
            "END_IF;",
        ], f"[SAT_INC {target.name} <= {limit}]", "increment_saturating"
    raise LadderError(f"{context}.type is unsupported: {kind!r}")


def _normalise_and_compile(
    document: dict[str, Any],
    interface_text: str,
    expected_name: str | None,
) -> tuple[dict[str, Any], str, list[dict[str, Any]]]:
    if not isinstance(document, dict):
        raise LadderError("ladder_program must be a JSON object")
    _exact_keys(document, {"schema_version", "function_block", "locals", "rungs"}, "ladder_program")
    if document.get("schema_version") != "1.0":
        raise LadderError("schema_version must be \"1.0\"")
    interface_name, public = parse_interface(interface_text)
    function_block = _identifier(document.get("function_block"), "function_block")
    if function_block != interface_name or (expected_name is not None and function_block != expected_name):
        raise LadderError(f"function_block must be {expected_name or interface_name}")
    local_symbols = _locals(document, public)
    symbols = _symbol_table(public + local_symbols)
    rungs = document.get("rungs")
    if not isinstance(rungs, list) or not rungs:
        raise LadderError("rungs must be a non-empty array")
    if len(rungs) > 128:
        raise LadderError("rungs exceeds the supported limit of 128")
    rung_ids: set[str] = set()
    normal_writers: set[str] = set()
    mixed_writers: set[str] = set()
    compiled_rungs: list[dict[str, Any]] = []
    for index, rung in enumerate(rungs):
        context = f"rungs[{index}]"
        if not isinstance(rung, dict):
            raise LadderError(f"{context} must be an object")
        _exact_keys(rung, {"id", "comment", "condition", "instructions"}, context)
        rung_id = _identifier(rung.get("id"), f"{context}.id")
        if rung_id.casefold() in rung_ids:
            raise LadderError(f"duplicate rung id {rung_id}")
        rung_ids.add(rung_id.casefold())
        comment = _comment(rung.get("comment", ""), f"{context}.comment")
        condition_st, condition_type, condition_label = _expression(rung.get("condition"), symbols, f"{context}.condition")
        if condition_type != "BOOL":
            raise LadderError(f"{context}.condition must be BOOL")
        instructions = rung.get("instructions")
        if not isinstance(instructions, list) or not instructions:
            raise LadderError(f"{context}.instructions must be a non-empty array")
        if len(instructions) > 16:
            raise LadderError(f"{context}.instructions exceeds the supported limit of 16")
        st_rows: list[str] = []
        labels: list[str] = []
        for instruction_index, instruction in enumerate(instructions):
            rows, label, writer_kind = _instruction(
                instruction,
                condition_st,
                symbols,
                f"{context}.instructions[{instruction_index}]",
            )
            target_name = str(instruction.get("target", "")).casefold()
            if writer_kind == "normal":
                if target_name in normal_writers or target_name in mixed_writers:
                    raise LadderError(f"normal coil {instruction.get('target')} must be its only writer")
                normal_writers.add(target_name)
            else:
                if target_name in normal_writers:
                    raise LadderError(f"target {instruction.get('target')} mixes a normal coil with retained writes")
                mixed_writers.add(target_name)
            st_rows.extend(rows)
            labels.append(label)
        compiled_rungs.append({
            "id": rung_id,
            "comment": comment,
            "condition_ir": rung["condition"],
            "condition_label": condition_label,
            "condition_st": condition_st,
            "instruction_labels": labels,
            "st_rows": st_rows,
        })

    interface_prefix = re.sub(
        r"(?ims)^\s*END_FUNCTION_BLOCK\s*$.*\Z",
        "",
        interface_text.strip(),
    ).rstrip()
    rows = [interface_prefix]
    if local_symbols:
        rows.append("VAR")
        for item in local_symbols:
            initial = ""
            if item.initial is not None:
                initial = f" := {_literal(item.initial, item.type_name, item.name)}"
            rows.append(f"    {item.name} : {item.type_name}{initial};")
        rows.append("END_VAR")
    for rung in compiled_rungs:
        description = rung["comment"] or "generated ladder network"
        rows.append(f"(* LD {rung['id']}: {description} *)")
        rows.extend(rung["st_rows"])
    rows.append("END_FUNCTION_BLOCK")
    normalized = {
        "schema_version": "1.0",
        "function_block": function_block,
        "locals": [
            ({"name": item.name, "type": item.type_name} | ({"initial": item.initial} if item.initial is not None else {}))
            for item in local_symbols
        ],
        "rungs": rungs,
    }
    return normalized, "\n".join(rows) + "\n", compiled_rungs


def _svg_text(value: str) -> str:
    return html.escape(value, quote=True)


def _compact_svg_label(value: str, limit: int) -> str:
    """Keep display-only labels inside fixed SVG nodes without changing IR semantics."""
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(1, limit - 1)].rstrip() + "…"


def _condition_branches(expression: dict[str, Any], fallback_label: str) -> list[list[tuple[str, str, bool]]]:
    """Convert Boolean structure to display-only parallel contact branches."""
    op = str(expression.get("op", "")).lower()
    if op == "var":
        return [[("contact", str(expression["name"]), False)]]
    if op == "not" and isinstance(expression.get("arg"), dict) and str(expression["arg"].get("op", "")).lower() == "var":
        return [[("contact", str(expression["arg"]["name"]), True)]]
    if op == "and":
        branches: list[list[tuple[str, str, bool]]] = [[]]
        for arg in expression.get("args", []):
            child_branches = _condition_branches(arg, fallback_label)
            combined = [left + right for left in branches for right in child_branches]
            # The semantic compiler accepts larger expressions, but the visual
            # renderer remains bounded and collapses an unusually large DNF.
            if len(combined) > 24:
                return [[("block", fallback_label, False)]]
            branches = combined
        return branches
    if op == "or":
        branches = []
        for arg in expression.get("args", []):
            branches.extend(_condition_branches(arg, fallback_label))
            if len(branches) > 24:
                return [[("block", fallback_label, False)]]
        return branches
    return [[("block", fallback_label, False)]]


def _render_contact(rows: list[str], x: float, y: float, width: float, token: tuple[str, str, bool]) -> None:
    kind, label, normally_closed = token
    # The same renderer is used for a wide single expression and for narrow
    # cells in a series branch, so derive the display budget from node width.
    width_budget = max(6, int((width - 20) / 7.2))
    display_label = _compact_svg_label(
        label,
        min(18, width_budget) if kind == "contact" else min(52, width_budget),
    )
    rows.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x + width:.1f}" y2="{y:.1f}" class="wire"/>')
    if kind == "contact":
        left = x + width * 0.36
        right = x + width * 0.64
        rows.extend([
            f'<g><title>{_svg_text(label)}</title>',
            f'<line x1="{left:.1f}" y1="{y - 17:.1f}" x2="{left:.1f}" y2="{y + 17:.1f}" class="contact"/>',
            f'<line x1="{right:.1f}" y1="{y - 17:.1f}" x2="{right:.1f}" y2="{y + 17:.1f}" class="contact"/>',
            f'<text x="{x + width / 2:.1f}" y="{y - 23:.1f}" text-anchor="middle" class="contact-label">{_svg_text(display_label)}</text>',
        ])
        if normally_closed:
            rows.append(f'<line x1="{left - 3:.1f}" y1="{y + 18:.1f}" x2="{right + 3:.1f}" y2="{y - 18:.1f}" class="contact"/>')
        rows.append('</g>')
    else:
        rows.extend([
            f'<g><title>{_svg_text(label)}</title>',
            f'<rect x="{x + 6:.1f}" y="{y - 20:.1f}" width="{width - 12:.1f}" height="40" rx="5" class="box"/>',
            f'<text x="{x + width / 2:.1f}" y="{y + 5:.1f}" text-anchor="middle" class="small-label">{_svg_text(display_label)}</text>',
            '</g>',
        ])


def render_svg(function_block: str, rungs: list[dict[str, Any]]) -> str:
    """Render deterministic ladder rails, contacts, branches, and instructions."""
    width = 1200
    top = 92
    layouts = []
    for rung in rungs:
        branches = _condition_branches(rung["condition_ir"], rung["condition_label"])
        lanes = max(len(branches), len(rung["instruction_labels"]), 1)
        layouts.append((rung, branches, 76 + lanes * 48))
    height = top + sum(item[2] for item in layouts) + 36
    rows = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Ladder diagram {_svg_text(function_block)}">',
        "<style>text{font-family:Arial,'Noto Sans SC',sans-serif;fill:#dbeafe}.wire{stroke:#60a5fa;stroke-width:3;fill:none}.rail{stroke:#93c5fd;stroke-width:6}.contact{stroke:#7dd3fc;stroke-width:3}.box{fill:#0f2744;stroke:#38bdf8;stroke-width:2}.muted{fill:#93a4bb;font-size:14px}.label{font-size:15px}.small-label{font-size:12px}.contact-label{font-size:13px}.title{font-size:24px;font-weight:700}.coil{fill:#102c4d;stroke:#22d3ee;stroke-width:2}</style>",
        f'<rect width="{width}" height="{height}" fill="#071525"/>',
        f'<text x="40" y="42" class="title">{_svg_text(function_block)} · IEC Ladder IR</text>',
        f'<line x1="42" y1="{top - 20}" x2="42" y2="{height - 28}" class="rail"/>',
        f'<line x1="1158" y1="{top - 20}" x2="1158" y2="{height - 28}" class="rail"/>',
    ]
    y_cursor = top
    for rung, branches, rung_height in layouts:
        comment = rung["comment"] or "无注释"
        comment_label = _compact_svg_label(comment, 96)
        rows.append(
            f'<text x="58" y="{y_cursor - 12}" class="muted">'
            f'<title>{_svg_text(comment)}</title>{_svg_text(rung["id"])} · {_svg_text(comment_label)}</text>'
        )
        lane_top = y_cursor + 24
        lane_bottom = lane_top + (max(len(branches), len(rung["instruction_labels"])) - 1) * 48
        rows.extend([
            f'<line x1="42" y1="{lane_top:.1f}" x2="92" y2="{lane_top:.1f}" class="wire"/>',
            f'<line x1="92" y1="{lane_top:.1f}" x2="92" y2="{lane_bottom:.1f}" class="wire"/>',
            f'<line x1="720" y1="{lane_top:.1f}" x2="720" y2="{lane_bottom:.1f}" class="wire"/>',
        ])
        for branch_index, branch in enumerate(branches):
            y = lane_top + branch_index * 48
            rows.append(f'<line x1="92" y1="{y:.1f}" x2="110" y2="{y:.1f}" class="wire"/>')
            contact_width = 590 / max(1, len(branch))
            for contact_index, token in enumerate(branch):
                _render_contact(rows, 110 + contact_index * contact_width, y, contact_width, token)
            rows.append(f'<line x1="700" y1="{y:.1f}" x2="720" y2="{y:.1f}" class="wire"/>')
        labels = rung["instruction_labels"]
        action_bottom = lane_top + (len(labels) - 1) * 48
        rows.append(f'<line x1="720" y1="{lane_top:.1f}" x2="720" y2="{action_bottom:.1f}" class="wire"/>')
        labels = rung["instruction_labels"]
        for action_index, label in enumerate(labels):
            y = lane_top + action_index * 48
            display_label = _compact_svg_label(label, 34)
            rows.extend([
                f'<line x1="720" y1="{y:.1f}" x2="780" y2="{y:.1f}" class="wire"/>',
                f'<g><title>{_svg_text(label)}</title>',
                f'<rect x="780" y="{y - 21:.1f}" width="310" height="42" rx="21" class="coil"/>',
                f'<text x="935" y="{y + 5:.1f}" text-anchor="middle" class="label">{_svg_text(display_label)}</text>',
                '</g>',
                f'<line x1="1090" y1="{y:.1f}" x2="1158" y2="{y:.1f}" class="wire"/>',
            ])
        y_cursor += rung_height
    rows.append("</svg>\n")
    return "\n".join(rows)


def compile_ladder_document(
    document: dict[str, Any],
    interface_text: str,
    expected_name: str | None = None,
) -> LadderCompilation:
    normalized, st_program, compiled_rungs = _normalise_and_compile(
        document,
        interface_text,
        expected_name,
    )
    canonical_json = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"
    return LadderCompilation(
        document=normalized,
        canonical_json=canonical_json,
        st_program=st_program,
        svg=render_svg(normalized["function_block"], compiled_rungs),
    )

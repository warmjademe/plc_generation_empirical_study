"""Deterministically extract model output without altering the PLC program."""

from __future__ import annotations

import re
from typing import Any

from .models import ParsedCandidate


def message_text(message: dict[str, Any]) -> str:
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "\n".join(parts)
    return str(content or "")


def _tag(text: str, name: str) -> str | None:
    match = re.search(rf"<{name}>\s*(.*?)\s*</{name}>", text, flags=re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else None


def _st_program(text: str) -> tuple[str | None, str]:
    strict = _tag(text, "st_program")
    if strict is not None:
        return strict, "strict_tagged"
    opening = re.search(r"<st_program>\s*", text, flags=re.IGNORECASE)
    if not opening:
        return None, "missing"
    tail = text[opening.end():].strip()
    starts = re.findall(r"(?im)^\s*FUNCTION_BLOCK\b", tail)
    ends = re.findall(r"(?im)^\s*END_FUNCTION_BLOCK\s*$", tail)
    if len(starts) == 1 and len(ends) == 1 and re.search(r"(?im)^\s*END_FUNCTION_BLOCK\s*$", tail):
        end = re.search(r"(?im)^\s*END_FUNCTION_BLOCK\s*$", tail)
        if end and not tail[end.end():].strip():
            return tail, "unterminated_tag_recovery"
    return None, "missing"


def parse_candidate(message: dict[str, Any], valid_requirement_ids: set[str]) -> ParsedCandidate:
    text = message_text(message)
    errors: list[str] = []
    program, extraction_mode = _st_program(text)
    hypothesis = _tag(text, "repair_hypothesis")
    targets_text = _tag(text, "target_requirements")
    if program is None:
        errors.append("missing <st_program> block")
        program = ""
    if hypothesis is None:
        errors.append("missing <repair_hypothesis> block")
        hypothesis = ""
    if targets_text is None:
        errors.append("missing <target_requirements> block")
        targets: tuple[str, ...] = ()
    else:
        raw_targets = [] if targets_text.upper() == "NONE" else re.findall(r"\bR[0-9]+\b", targets_text.upper())
        targets = tuple(dict.fromkeys(raw_targets))
        unknown = set(targets) - valid_requirement_ids
        if unknown:
            errors.append(f"unknown target requirements: {sorted(unknown)}")
    if "```" in program:
        errors.append("Markdown fence inside ST program")
    if not program.strip():
        errors.append("empty ST program")
    return ParsedCandidate(
        program=program.rstrip() + ("\n" if program else ""),
        hypothesis=hypothesis,
        target_requirement_ids=targets,
        format_valid=not errors,
        format_errors=tuple(errors),
        extraction_mode=extraction_mode,
    )

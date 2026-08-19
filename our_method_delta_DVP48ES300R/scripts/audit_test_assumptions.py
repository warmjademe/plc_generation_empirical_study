#!/usr/bin/env python3
"""Detect authored runtime vectors that violate explicit public assumptions."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


VARIABLE = r"([A-Za-z][A-Za-z0-9_]*)"


def assumption_constraints(text: str) -> list[dict[str, Any]]:
    constraints: list[dict[str, Any]] = []
    for raw in text.splitlines():
        line = raw.strip().lstrip("-").strip()
        if not line:
            continue
        for match in re.finditer(
            rf"\b{VARIABLE}\b[^.]*?\b(?:is|are) positive\b", line, re.IGNORECASE
        ):
            constraints.append({"variable": match.group(1), "kind": "lower_exclusive", "value": 0, "source": line})
        for match in re.finditer(
            rf"\b{VARIABLE}\b[^.]*?\bis at least\s+(-?\d+)\b", line, re.IGNORECASE
        ):
            constraints.append({"variable": match.group(1), "kind": "lower_inclusive", "value": int(match.group(2)), "source": line})
        for match in re.finditer(
            rf"\b{VARIABLE}\b[^.]*?\bis non-negative\b", line, re.IGNORECASE
        ):
            constraints.append({"variable": match.group(1), "kind": "lower_inclusive", "value": 0, "source": line})
        for match in re.finditer(
            rf"\b{VARIABLE}\b[^.]*?\b(?:within|in) the closed interval\s*\[\s*(-?\d+)\s*,\s*(-?\d+)\s*\]",
            line,
            re.IGNORECASE,
        ):
            constraints.append({
                "variable": match.group(1), "kind": "closed_interval",
                "lower": int(match.group(2)), "upper": int(match.group(3)), "source": line,
            })
        for match in re.finditer(
            rf"\b{VARIABLE}\b[^.]*?\bremains constant during (?:a|the) test\b",
            line,
            re.IGNORECASE,
        ):
            constraints.append({"variable": match.group(1), "kind": "case_constant", "source": line})
    unique: dict[tuple, dict[str, Any]] = {}
    for item in constraints:
        key = tuple(sorted((key, value) for key, value in item.items() if key != "source"))
        unique[key] = item
    return list(unique.values())


def value_violates(value: Any, constraint: dict[str, Any]) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    kind = constraint["kind"]
    if kind == "lower_exclusive":
        return value <= constraint["value"]
    if kind == "lower_inclusive":
        return value < constraint["value"]
    if kind == "closed_interval":
        return not constraint["lower"] <= value <= constraint["upper"]
    return False


def audit_task(task_dir: Path) -> dict[str, Any]:
    constraints = assumption_constraints((task_dir / "requirement.md").read_text(encoding="utf-8"))
    suite = json.loads((task_dir / "openplc_tests.json").read_text(encoding="utf-8"))
    violations: list[dict[str, Any]] = []
    for case in suite.get("cases", []):
        seen: dict[str, Any] = {}
        for step_number, step in enumerate(case.get("steps", []), start=1):
            inputs = step.get("inputs") or {}
            for constraint in constraints:
                variable = constraint["variable"]
                if variable not in inputs:
                    continue
                value = inputs[variable]
                if constraint["kind"] == "case_constant":
                    if variable in seen and seen[variable] != value:
                        violations.append({
                            "case": case.get("name"), "case_id": case.get("id"),
                            "step": step_number, "variable": variable, "value": value,
                            "kind": "case_constant", "initial_value": seen[variable],
                            "assumption": constraint["source"],
                        })
                    else:
                        seen[variable] = value
                elif value_violates(value, constraint):
                    violations.append({
                        "case": case.get("name"), "case_id": case.get("id"),
                        "step": step_number, "variable": variable, "value": value,
                        "kind": constraint["kind"], "assumption": constraint["source"],
                    })
    return {
        "task_id": task_dir.name,
        "constraint_count": len(constraints),
        "violation_count": len(violations),
        "violations": violations,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    tasks = [audit_task(path) for path in sorted((args.dataset_root / "tasks").iterdir()) if path.is_dir()]
    document = {
        "schema_version": "1.0",
        "scope": "explicit numeric-bound and per-case-constant assumptions",
        "task_count": len(tasks),
        "violating_task_count": sum(item["violation_count"] > 0 for item in tasks),
        "violation_count": sum(item["violation_count"] for item in tasks),
        "tasks": [item for item in tasks if item["violation_count"] > 0],
    }
    encoded = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 1 if document["violation_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Statically qualify the DVP M-coil adapter over every dataset interface."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from plc_loop.delta_dvp import (
    Declaration,
    FunctionBlock,
    build_dvp_harness,
    select_openplc_cases,
)


DEFAULTS = {"BOOL": "FALSE", "INT": "0", "REAL": "0.0"}


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def interface_stub(metadata: dict[str, Any]) -> FunctionBlock:
    declarations: list[Declaration] = []
    body: list[str] = []
    for item in metadata["interface"]["inputs"]:
        declarations.append(Declaration(str(item["name"]), str(item["type"]), "VAR_INPUT"))
    for item in metadata["interface"]["outputs"]:
        name = str(item["name"])
        type_name = str(item["type"]).upper()
        if type_name not in DEFAULTS:
            raise ValueError(f"unsupported output type {type_name}")
        declarations.append(Declaration(name, type_name, "VAR_OUTPUT"))
        body.append(f"{name} := {DEFAULTS[type_name]};")
    return FunctionBlock(str(metadata["id"]), tuple(declarations), "\n".join(body))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--expected-task-count", type=int, default=100)
    args = parser.parse_args()

    tasks_root = args.dataset_root.resolve() / "tasks"
    task_dirs = [path for path in sorted(tasks_root.iterdir()) if path.is_dir()]
    errors: list[str] = []
    records: list[dict[str, Any]] = []
    for task_dir in task_dirs:
        try:
            metadata = json.loads((task_dir / "metadata.json").read_text(encoding="utf-8-sig"))
            suite = json.loads((task_dir / "openplc_tests.json").read_text(encoding="utf-8-sig"))
            block = interface_stub(metadata)
            source_case_ids = [str(case["id"]) for case in suite["cases"]]
            if len(source_case_ids) != len(set(source_case_ids)):
                raise ValueError("runtime case identifiers are duplicated")
            role_records: dict[str, Any] = {}
            selected_ids: set[str] = set()
            for role in ("feedback", "sealed"):
                selected = select_openplc_cases(suite, role)
                role_ids = [str(case["id"]) for case in selected["cases"]]
                overlap = selected_ids.intersection(role_ids)
                if overlap:
                    raise ValueError(f"case-role overlap: {sorted(overlap)}")
                selected_ids.update(role_ids)
                harness = build_dvp_harness(
                    block,
                    metadata,
                    selected,
                    image_identity_sha256="0" * 64,
                    inline_candidate=True,
                )
                role_records[role] = {
                    "case_count": len(role_ids),
                    "case_ids": role_ids,
                    "first_m": harness.mapping["first_m"],
                    "writable_last_m": harness.mapping["writable_last_m"],
                    "last_m": harness.mapping["last_m"],
                    "input_count": len(harness.mapping["inputs"]),
                    "output_count": len(harness.mapping["outputs"]),
                }
            if selected_ids != set(source_case_ids):
                raise ValueError("feedback/sealed split does not cover every runtime case")
            records.append({"task_id": task_dir.name, "roles": role_records})
        except Exception as exc:
            errors.append(f"{task_dir.name}: {type(exc).__name__}: {exc}")

    if len(task_dirs) != args.expected_task_count:
        errors.append(
            f"dataset contains {len(task_dirs)} tasks, expected {args.expected_task_count}"
        )
    all_roles = [
        role
        for record in records
        for role in record["roles"].values()
    ]
    report = {
        "schema_version": "1.0",
        "target": "DVP48ES300R",
        "task_count": len(task_dirs),
        "qualified_task_count": len(records),
        "feedback_case_count": sum(item["case_count"] for item in (
            record["roles"]["feedback"] for record in records
        )),
        "sealed_case_count": sum(item["case_count"] for item in (
            record["roles"]["sealed"] for record in records
        )),
        "maximum_allocated_m": max((item["last_m"] for item in all_roles), default=None),
        "all_allocations_within_m8191": all(item["last_m"] <= 8191 for item in all_roles),
        "audit_pass": not errors and len(records) == args.expected_task_count,
        "errors": errors,
        "tasks": records,
    }
    write_json(args.output.resolve(), report)
    print(json.dumps({key: report[key] for key in (
        "audit_pass", "task_count", "qualified_task_count", "feedback_case_count",
        "sealed_case_count", "maximum_allocated_m", "all_allocations_within_m8191",
        "errors",
    )}, ensure_ascii=False))
    return 0 if report["audit_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

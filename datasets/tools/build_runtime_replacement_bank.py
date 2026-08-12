#!/usr/bin/env python3
"""Build a compact replacement bank from independently authored base tasks.

The compositional C04/C06 tasks can make PLCverif explore a large product state
space.  This builder preserves the original single-controller requirements and
oracles, adds the OpenPLC suite expected by the strict harness, and records every
copied artifact hash.  Reference qualification, including the runtime budget, is
performed separately and remains the eligibility authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any


COPY_FILES = (
    "interface.st",
    "metadata.json",
    "properties.json",
    "reference.st",
    "requirement.md",
    "tests_feedback.json",
    "tests_hidden.json",
    "tests_stress.json",
    "validation_report.json",
)


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def openplc_suite(task_dir: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for suite_name in ("feedback", "hidden", "stress"):
        document = json.loads((task_dir / f"tests_{suite_name}.json").read_text(encoding="utf-8"))
        for index, original in enumerate(document["cases"], start=1):
            case = dict(original)
            case["id"] = f"{suite_name[:1].upper()}T{index:02d}"
            case["oracle_source"] = f"independently_authored_{suite_name}_oracle"
            cases.append(case)
    scan = metadata["scan"]
    return {
        "schema_version": "1.0",
        "suite": "openplc",
        "task_id": metadata["id"],
        "scan_period_ms": scan["period_ms"],
        "real_absolute_tolerance": 0.001,
        "oracle_source": "independently_authored_base_task_oracles",
        "independent_requirement_oracle": True,
        "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--category", action="append", default=["C04", "C06"])
    args = parser.parse_args()

    base_root = args.base_root.resolve()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite replacement bank: {output}")
    task_output = output / "tasks"
    task_output.mkdir(parents=True)
    categories = set(args.category)
    source_tasks = sorted(
        path for path in base_root.iterdir()
        if path.is_dir() and path.name[:3] in categories
    )
    if not source_tasks:
        raise RuntimeError("no source tasks matched the requested categories")

    records = []
    for source in source_tasks:
        destination = task_output / source.name
        destination.mkdir()
        for relative in COPY_FILES:
            shutil.copy2(source / relative, destination / relative)
        shutil.copytree(source / "negative_control", destination / "negative_control")
        metadata = json.loads((destination / "metadata.json").read_text(encoding="utf-8"))
        metadata["dataset_version"] = "runtime-replacement-0.1-dev"
        provenance = dict(metadata.get("provenance", {}))
        provenance["replacement_source_task_id"] = source.name
        provenance["construction"] = "unchanged independently authored base task"
        metadata["provenance"] = provenance
        write_json(destination / "metadata.json", metadata)
        write_json(destination / "openplc_tests.json", openplc_suite(source, metadata))
        write_json(destination / "validation_report.json", {
            "schema_version": "1.0",
            "task_id": source.name,
            "structural": {"status": "not_run"},
            "external": {name: {"status": "not_run"} for name in ("matiec", "plcverif", "openplc")},
            "screening": {"kimi_k3_direct_once": "not_run"},
        })
        artifacts = sorted(
            path.relative_to(destination).as_posix()
            for path in destination.rglob("*") if path.is_file()
        )
        records.append({
            "id": source.name,
            "category_id": source.name[:3],
            "path": f"tasks/{source.name}",
            "source": str(source),
            "hashes": {relative: sha256(destination / relative) for relative in artifacts},
        })

    with (output / "manifest.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    write_json(output / "dataset_summary.json", {
        "schema_version": "1.0",
        "dataset": "IEC-ST-VerifyBench runtime replacement candidates",
        "task_count": len(records),
        "category_counts": dict(sorted(Counter(record["category_id"] for record in records).items())),
        "construction_rule": "independently authored base tasks; no compositional product state",
        "eligibility_rule": "reference MatIEC -> PLCverif -> OpenPLC within a separately recorded wall-time budget",
        "selection_status": "not_run",
    })
    print(json.dumps({"status": "built", "task_count": len(records), "output": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

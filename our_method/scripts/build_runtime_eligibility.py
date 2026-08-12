#!/usr/bin/env python3
"""Freeze a task-level reference-verification runtime eligibility decision."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def gate_by_name(record: dict[str, Any], name: str) -> dict[str, Any] | None:
    for gate in record.get("candidates", {}).get("reference", {}).get("gates", []):
        if gate.get("name") == name:
            return gate
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qualification", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-reference-plcverif-seconds", type=float, default=300.0)
    args = parser.parse_args()
    if args.max_reference_plcverif_seconds <= 0:
        raise ValueError("runtime budget must be positive")

    qualification = args.qualification.resolve()
    output = args.output.resolve()
    records = []
    for path in sorted(qualification.glob("*/qualification.json")):
        source = json.loads(path.read_text(encoding="utf-8"))
        task_id = str(source["task_id"])
        compiler = gate_by_name(source, "compiler")
        plcverif = gate_by_name(source, "plcverif")
        openplc = gate_by_name(source, "openplc")
        duration_ms = plcverif.get("duration_ms") if plcverif else None
        reasons = []
        if source.get("qualified") is not True:
            reasons.append("reference_or_negative_not_qualified")
        if plcverif is None or plcverif.get("status") != "pass":
            reasons.append("reference_plcverif_not_pass")
        if not isinstance(duration_ms, (int, float)):
            reasons.append("reference_plcverif_duration_missing")
        elif duration_ms > args.max_reference_plcverif_seconds * 1000:
            reasons.append("reference_plcverif_runtime_budget_exceeded")
        records.append({
            "task_id": task_id,
            "category_id": task_id[:3],
            "eligible": not reasons,
            "exclusion_reasons": reasons,
            "reference_gate_status": {
                "compiler": compiler.get("status") if compiler else None,
                "plcverif": plcverif.get("status") if plcverif else None,
                "openplc": openplc.get("status") if openplc else None,
            },
            "reference_gate_duration_ms": {
                "compiler": compiler.get("duration_ms") if compiler else None,
                "plcverif": duration_ms,
                "openplc": openplc.get("duration_ms") if openplc else None,
            },
            "qualification_sha256": sha256(path),
        })

    category_total = Counter(record["category_id"] for record in records)
    category_eligible = Counter(record["category_id"] for record in records if record["eligible"])
    document = {
        "schema_version": "1.0",
        "policy": "task is eligible only when its qualified reference completes full PLCverif within the fixed wall-time budget",
        "max_reference_plcverif_seconds": args.max_reference_plcverif_seconds,
        "qualification_root": str(qualification),
        "task_count": len(records),
        "eligible_count": sum(record["eligible"] for record in records),
        "excluded_count": sum(not record["eligible"] for record in records),
        "category_total_counts": dict(sorted(category_total.items())),
        "category_eligible_counts": dict(sorted(category_eligible.items())),
        "tasks": records,
    }
    write_json(output, document)
    print(json.dumps({
        "status": "pass",
        "task_count": document["task_count"],
        "eligible_count": document["eligible_count"],
        "excluded_count": document["excluded_count"],
        "output": str(output),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

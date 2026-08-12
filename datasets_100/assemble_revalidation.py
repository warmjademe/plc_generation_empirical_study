#!/usr/bin/env python3
"""Assemble an exact 100-task calibration after a qualified task replacement."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_manifest(path: Path) -> dict[str, dict]:
    return {
        row["id"]: row
        for row in (
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-summary", required=True, type=Path)
    parser.add_argument("--replacement-summary", required=True, type=Path)
    parser.add_argument("--base-manifest", required=True, type=Path)
    parser.add_argument("--current-manifest", required=True, type=Path)
    parser.add_argument("--removed-task", required=True)
    parser.add_argument("--added-task", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    base = json.loads(args.base_summary.read_text(encoding="utf-8"))
    replacement = json.loads(args.replacement_summary.read_text(encoding="utf-8"))
    old_manifest = load_manifest(args.base_manifest)
    current_manifest = load_manifest(args.current_manifest)
    if set(old_manifest) - {args.removed_task} != set(current_manifest) - {args.added_task}:
        raise ValueError("the manifests differ by more than the declared replacement")
    for task_id in set(old_manifest) & set(current_manifest):
        if old_manifest[task_id] != current_manifest[task_id]:
            raise ValueError(f"unchanged task manifest record differs: {task_id}")
    if base.get("config_sha256") != replacement.get("config_sha256"):
        raise ValueError("base and replacement calibrations use different validator configs")

    records = {
        row["task_id"]: row
        for row in base.get("tasks", [])
        if row.get("task_id") != args.removed_task
    }
    replacement_rows = replacement.get("tasks", [])
    if len(replacement_rows) != 1 or replacement_rows[0].get("task_id") != args.added_task:
        raise ValueError("replacement summary does not contain exactly the added task")
    records[args.added_task] = replacement_rows[0]
    if set(records) != set(current_manifest) or len(records) != 100:
        raise ValueError("assembled calibration IDs differ from the current 100-task manifest")
    for task_id, row in records.items():
        if row.get("status") != "pass":
            raise ValueError(f"assembled calibration contains a non-pass task: {task_id}")
        expected = current_manifest[task_id]["hashes"]["reference.st"]
        if row.get("reference_sha256") != expected:
            raise ValueError(f"reference hash mismatch: {task_id}")

    ordered = [records[task_id] for task_id in sorted(records)]
    gate_durations: Counter[str] = Counter()
    for row in ordered:
        for gate in row.get("gates", []):
            gate_durations[str(gate["name"])] += int(gate.get("duration_ms", 0))
    document = {
        "schema_version": "1.0",
        "purpose": "exact reference-program calibration assembled after one runtime-driven task replacement",
        "config": base.get("config"),
        "config_sha256": base["config_sha256"],
        "dataset_root": str(args.current_manifest.resolve().parent),
        "dataset_manifest_sha256": sha256(args.current_manifest),
        "workers": "20 for the base calibration; 1 for the replacement",
        "task_count": 100,
        "pass_count": 100,
        "status_counts": {"pass": 100},
        "gate_duration_ms_total": dict(sorted(gate_durations.items())),
        "success": True,
        "replacement": {
            "removed_task": args.removed_task,
            "reason": "PLCverif P6 was inconclusive after the fixed 120-second CBMC backend timeout",
            "added_task": args.added_task,
            "base_summary_sha256": sha256(args.base_summary),
            "replacement_summary_sha256": sha256(args.replacement_summary),
            "base_manifest_sha256": sha256(args.base_manifest),
        },
        "tasks": ordered,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "task_count": 100,
        "pass_count": 100,
        "success": True,
        "removed_task": args.removed_task,
        "added_task": args.added_task,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

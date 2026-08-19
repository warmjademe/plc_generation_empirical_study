#!/usr/bin/env python3
"""Replace runtime-ineligible tasks in a frozen dataset with audited candidates.

The script builds a new dataset directory and never mutates the input.  It copies
task packages and immutable evidence from a prior audited assembly, updates the
manifest and selection metadata, and verifies that all non-replaced task/evidence
files are byte-identical to the input dataset.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

from plc_loop.ledger import EvidenceLedger


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_manifest(path: Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            records[str(record["id"])] = record
    return records


def file_hashes(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def reference_plcverif_duration(record: dict[str, Any]) -> int:
    for gate in record.get("candidates", {}).get("reference", {}).get("gates", []):
        if gate.get("name") == "plcverif" and gate.get("status") == "pass":
            return int(gate.get("duration_ms", -1))
    raise ValueError(f"{record.get('task_id')}: no passing reference PLCverif gate")


def audit_source_task(source: Path, task_id: str, max_reference_ms: int) -> dict[str, Any]:
    task = source / "tasks" / task_id
    qualification_path = source / "evidence" / "qualification" / f"{task_id}.json"
    screening = source / "evidence" / "screening" / task_id
    required = [
        task / "metadata.json",
        task / "requirement.md",
        task / "interface.st",
        task / "reference.st",
        task / "properties.json",
        task / "openplc_tests.json",
        qualification_path,
        screening / "result.json",
        screening / "ledger.jsonl",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"{task_id}: incomplete source package: {missing}")

    qualification = json.loads(qualification_path.read_text(encoding="utf-8"))
    if not all(qualification.get(key) is True for key in (
        "qualified", "reference_ok", "authored_negative_killed"
    )):
        raise ValueError(f"{task_id}: source task is not fully qualified")
    duration_ms = reference_plcverif_duration(qualification)
    if duration_ms > max_reference_ms:
        raise ValueError(
            f"{task_id}: reference PLCverif duration {duration_ms} ms exceeds "
            f"the {max_reference_ms} ms runtime budget"
        )

    result = json.loads((screening / "result.json").read_text(encoding="utf-8"))
    if result.get("task_id") != task_id or int(result.get("candidates_used", -1)) != 1:
        raise ValueError(f"{task_id}: source evidence is not a matching Direct@1 run")
    if result.get("success") is True:
        raise ValueError(f"{task_id}: replacement must be a Direct@1 failure")
    if result.get("status") not in {"candidate_budget_exhausted", "sealed_failure"}:
        raise ValueError(f"{task_id}: unsupported screening outcome {result.get('status')!r}")
    if not EvidenceLedger.verify(screening / "ledger.jsonl"):
        raise ValueError(f"{task_id}: screening ledger is empty or invalid")
    return {
        "reference_plcverif_duration_ms": duration_ms,
        "screening_status": result["status"],
        "result_sha256": sha256(screening / "result.json"),
        "ledger_sha256": sha256(screening / "ledger.jsonl"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--replacement-source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--replace", required=True, action="append", metavar="OLD=NEW",
        help="replace one selected task ID with another task from replacement-source",
    )
    parser.add_argument("--max-reference-plcverif-ms", type=int, default=900_000)
    args = parser.parse_args()

    input_root = args.input.resolve()
    source_root = args.replacement_source.resolve()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output}")
    replacements = dict(item.split("=", 1) for item in args.replace)
    if len(replacements) != len(args.replace) or len(set(replacements.values())) != len(replacements):
        raise ValueError("replacement task IDs must be unique")
    if any(old[:3] != new[:3] for old, new in replacements.items()):
        raise ValueError("each replacement must remain in the same task category")

    current_selection = json.loads((input_root / "selection.json").read_text(encoding="utf-8"))
    source_selection = json.loads((source_root / "selection.json").read_text(encoding="utf-8"))
    current_by_id = {item["task_id"]: item for item in current_selection["selected_tasks"]}
    source_by_id = {item["task_id"]: item for item in source_selection["selected_tasks"]}
    if not set(replacements).issubset(current_by_id):
        raise ValueError("one or more replaced tasks are not selected in the input dataset")
    if not set(replacements.values()).issubset(source_by_id):
        raise ValueError("one or more replacement tasks are absent from the replacement assembly")

    replacement_audit = {
        new: audit_source_task(source_root, new, args.max_reference_plcverif_ms)
        for new in replacements.values()
    }
    before_unchanged = {
        task_id: {
            "task": file_hashes(input_root / "tasks" / task_id),
            "qualification": sha256(input_root / "evidence" / "qualification" / f"{task_id}.json"),
            "screening": file_hashes(input_root / "evidence" / "screening" / task_id),
        }
        for task_id in current_by_id
        if task_id not in replacements
    }

    shutil.copytree(input_root, output)
    for old, new in replacements.items():
        shutil.rmtree(output / "tasks" / old)
        shutil.rmtree(output / "evidence" / "screening" / old)
        (output / "evidence" / "qualification" / f"{old}.json").unlink()
        shutil.copytree(source_root / "tasks" / new, output / "tasks" / new)
        shutil.copytree(
            source_root / "evidence" / "screening" / new,
            output / "evidence" / "screening" / new,
        )
        shutil.copy2(
            source_root / "evidence" / "qualification" / f"{new}.json",
            output / "evidence" / "qualification" / f"{new}.json",
        )

    selected_records = [
        source_by_id[replacements[item["task_id"]]] if item["task_id"] in replacements else item
        for item in current_selection["selected_tasks"]
    ]
    for item in selected_records:
        result = json.loads((output / item["result_path"]).read_text(encoding="utf-8"))
        item["outcome_class"] = "verified_success" if result.get("success") else "screening_failure"
        item["result_sha256"] = sha256(output / item["result_path"])
        item["ledger_sha256"] = sha256(
            output / "evidence" / "screening" / item["task_id"] / "ledger.jsonl"
        )
        item["source_model_run_path"] = f"evidence/screening/{item['task_id']}"
        item["qualification_path"] = f"evidence/qualification/{item['task_id']}.json"
    selected_records.sort(
        key=lambda item: (
            item["category_id"],
            item["outcome_class"] == "verified_success",
            item["task_id"],
        )
    )

    current_manifest = load_manifest(input_root / "manifest.jsonl")
    source_manifest = load_manifest(source_root / "manifest.jsonl")
    manifest_by_id = {
        item["task_id"]: (
            source_manifest[item["task_id"]]
            if item["task_id"] in replacements.values()
            else current_manifest[item["task_id"]]
        )
        for item in selected_records
    }
    with (output / "manifest.jsonl").open("w", encoding="utf-8") as handle:
        for item in selected_records:
            handle.write(json.dumps(manifest_by_id[item["task_id"]], ensure_ascii=False, sort_keys=True) + "\n")

    excluded = set(current_selection.get("excluded_task_ids", []))
    excluded.difference_update(replacements.values())
    excluded.update(replacements)
    replacement_records = [
        {
            "removed_task_id": old,
            "replacement_task_id": new,
            "reason": "reference PLCverif runtime exceeded the configured 900-second validator budget",
            **replacement_audit[new],
        }
        for old, new in sorted(replacements.items())
    ]
    current_selection.update({
        "selection_protocol": (
            "qualification-backed Kimi-K3 Direct@1 screening outcomes with five tasks per "
            "category; runtime-ineligible tasks are replaced by previously qualified Direct@1 "
            "failures from the same category"
        ),
        "task_count": len(selected_records),
        "category_counts": dict(sorted(Counter(item["category_id"] for item in selected_records).items())),
        "outcome_counts": dict(sorted(Counter(item["outcome_class"] for item in selected_records).items())),
        "excluded_task_ids": sorted(excluded),
        "runtime_replacements": replacement_records,
        "max_reference_plcverif_ms": args.max_reference_plcverif_ms,
        "selected_tasks": selected_records,
        "output_manifest_sha256": sha256(output / "manifest.jsonl"),
    })
    write_json(output / "selection.json", current_selection)
    write_json(output / "dataset_summary.json", {
        "schema_version": "1.0",
        "dataset_name": "PLC Generation Balanced-50",
        "task_count": len(selected_records),
        "category_counts": current_selection["category_counts"],
        "outcome_counts": current_selection["outcome_counts"],
        "runtime_replacement_count": len(replacement_records),
        "max_reference_plcverif_ms": args.max_reference_plcverif_ms,
        "selection_sha256": sha256(output / "selection.json"),
        "manifest_sha256": current_selection["output_manifest_sha256"],
    })

    after_unchanged = {
        task_id: {
            "task": file_hashes(output / "tasks" / task_id),
            "qualification": sha256(output / "evidence" / "qualification" / f"{task_id}.json"),
            "screening": file_hashes(output / "evidence" / "screening" / task_id),
        }
        for task_id in before_unchanged
    }
    if before_unchanged != after_unchanged:
        changed = sorted(task_id for task_id in before_unchanged if before_unchanged[task_id] != after_unchanged[task_id])
        raise RuntimeError(f"non-replaced task evidence changed: {changed}")
    if len(selected_records) != 50 or set(current_selection["category_counts"].values()) != {5}:
        raise RuntimeError("balanced 50-task invariant was not preserved")

    write_json(output / "replacement_audit.json", {
        "status": "pass",
        "input_dataset": str(input_root),
        "replacement_source": str(source_root),
        "replacements": replacement_records,
        "unchanged_task_count": len(before_unchanged),
        "unchanged_task_evidence_byte_identical": True,
        "task_count": len(selected_records),
        "category_counts": current_selection["category_counts"],
        "outcome_counts": current_selection["outcome_counts"],
        "manifest_sha256": sha256(output / "manifest.jsonl"),
        "selection_sha256": sha256(output / "selection.json"),
    })
    print(json.dumps({
        "status": "pass",
        "output": str(output),
        "unchanged_task_count": len(before_unchanged),
        "replacements": replacement_records,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

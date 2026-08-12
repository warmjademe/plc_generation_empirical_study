#!/usr/bin/env python3
"""Fail-closed structural and contract/Oracle audit for datasets_100."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
EXCLUDED = {
    "C02_B08_composite",
    "C02_B12_composite",
    "C06_M02_bounded_up_down_counter",
    "C06_W03_lean_composite",
    "C06_W05_lean_composite",
    "C06_W10_lean_composite",
    "C06_W20_lean_composite",
    "C09_B02_composite",
}
REQUIRED_FILES = {
    "metadata.json",
    "requirement.md",
    "interface.st",
    "reference.st",
    "properties.json",
    "openplc_tests.json",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def declared_variables(interface_text: str, section: str) -> set[str]:
    match = re.search(rf"\b{section}\b(.*?)\bEND_VAR\b", interface_text, re.S | re.I)
    if not match:
        return set()
    return {
        item.group(1)
        for item in re.finditer(r"^\s*([A-Za-z][A-Za-z0-9_]*)\s*:", match.group(1), re.M)
    }


def openplc_case_role(case: dict) -> str:
    """Mirror the prespecified split in openplc_sealed_validator.py."""
    case_id = str(case.get("id", ""))
    name = str(case.get("name", "")).casefold()
    if case_id.startswith("FT") or "_feedback_" in name:
        return "feedback"
    return "sealed"


def main() -> int:
    errors: list[str] = []
    tasks = sorted(path for path in (ROOT / "tasks").iterdir() if path.is_dir())
    if len(tasks) != 100:
        errors.append(f"expected 100 tasks, found {len(tasks)}")
    counts = Counter(path.name[:3] for path in tasks)
    expected_counts = {f"C{number:02d}": 10 for number in range(1, 11)}
    if dict(sorted(counts.items())) != expected_counts:
        errors.append(f"category counts differ: {dict(sorted(counts.items()))}")
    present = {path.name for path in tasks}
    if present & EXCLUDED:
        errors.append(f"excluded tasks are present: {sorted(present & EXCLUDED)}")

    manifest_records = [
        json.loads(line)
        for line in (ROOT / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(manifest_records) != 100:
        errors.append(f"manifest has {len(manifest_records)} records")
    manifest_by_id = {record["id"]: record for record in manifest_records}
    if set(manifest_by_id) != present:
        errors.append("manifest IDs do not equal task directory IDs")

    selection_audit = json.loads((ROOT / "selection_audit.json").read_text(encoding="utf-8"))
    selection_records = {
        record["task_id"]: record for record in selection_audit.get("records", [])
    }
    if set(selection_records) != present:
        errors.append("selection-audit IDs do not equal task directory IDs")
    runtime_limit_ms = int(
        selection_audit.get("selection_policy", {}).get(
            "historical_reference_runtime_limit_ms", 0
        )
    )
    if runtime_limit_ms <= 0:
        errors.append("selection audit has no positive historical runtime limit")

    for task_dir in tasks:
        task_id = task_dir.name
        missing = sorted(name for name in REQUIRED_FILES if not (task_dir / name).is_file())
        if missing:
            errors.append(f"{task_id}: missing files {missing}")
            continue
        metadata = json.loads((task_dir / "metadata.json").read_text(encoding="utf-8"))
        if metadata.get("id") != task_id or metadata.get("category_id") != task_id[:3]:
            errors.append(f"{task_id}: metadata identity mismatch")
        interface = (task_dir / "interface.st").read_text(encoding="utf-8")
        inputs = declared_variables(interface, "VAR_INPUT")
        outputs = declared_variables(interface, "VAR_OUTPUT")
        if not inputs or not outputs:
            errors.append(f"{task_id}: interface has no parsed inputs or outputs")
        suite = json.loads((task_dir / "openplc_tests.json").read_text(encoding="utf-8"))
        cases = suite.get("cases", [])
        if not cases:
            errors.append(f"{task_id}: OpenPLC suite is empty")
        roles = Counter(openplc_case_role(case) for case in cases)
        if not roles.get("feedback") or not roles.get("sealed"):
            errors.append(f"{task_id}: OpenPLC suite lacks feedback or sealed cases")
        if suite.get("suite") != "openplc" or suite.get("independent_requirement_oracle") is not True:
            errors.append(f"{task_id}: invalid independent OpenPLC-oracle declaration")
        expected_names = {
            name
            for case in cases
            for step in case.get("steps", [])
            for name in (step.get("expect") or {})
        }
        input_names = {
            name
            for case in cases
            for step in case.get("steps", [])
            for name in (step.get("inputs") or {})
        }
        if not expected_names <= outputs:
            errors.append(f"{task_id}: oracle expects undeclared outputs {sorted(expected_names - outputs)}")
        if not input_names <= inputs:
            errors.append(f"{task_id}: oracle supplies undeclared inputs {sorted(input_names - inputs)}")
        properties = json.loads((task_dir / "properties.json").read_text(encoding="utf-8"))
        property_rows = properties.get("properties", []) if isinstance(properties, dict) else []
        if not property_rows:
            errors.append(f"{task_id}: formal property suite is empty")
        requirement_rows = metadata.get("requirements", [])
        requirement_ids = [str(row.get("id", "")) for row in requirement_rows]
        if not requirement_ids or "" in requirement_ids or len(requirement_ids) != len(set(requirement_ids)):
            errors.append(f"{task_id}: metadata requirements are empty or have duplicate IDs")
        case_requirement_ids = {
            str(requirement_id)
            for case in cases
            for requirement_id in case.get("requirement_ids", [])
        }
        if not case_requirement_ids <= set(requirement_ids):
            errors.append(
                f"{task_id}: OpenPLC cases cite unknown requirements "
                f"{sorted(case_requirement_ids - set(requirement_ids))}"
            )
        record = manifest_by_id.get(task_id)
        if record:
            for relative, expected_hash in record.get("hashes", {}).items():
                path = task_dir / relative
                if not path.is_file() or sha256(path) != expected_hash:
                    errors.append(f"{task_id}: manifest hash mismatch for {relative}")
        selection_record = selection_records.get(task_id)
        if selection_record:
            duration_ms = int(selection_record.get("reference_total_duration_ms", -1))
            if duration_ms < 0 or (runtime_limit_ms > 0 and duration_ms > runtime_limit_ms):
                errors.append(
                    f"{task_id}: historical validation duration {duration_ms} exceeds "
                    f"limit {runtime_limit_ms}"
                )
            if selection_record.get("reference_sha256") != sha256(task_dir / "reference.st"):
                errors.append(f"{task_id}: selected reference hash differs from qualification evidence")

    report = {
        "schema_version": "1.0",
        "task_count": len(tasks),
        "category_counts": dict(sorted(counts.items())),
        "known_exclusions_absent": not bool(present & EXCLUDED),
        "error_count": len(errors),
        "errors": errors,
        "success": not errors,
        "scope": [
            "task count and category balance",
            "known data-quality exclusions",
            "required artifacts and identities",
            "feedback/sealed OpenPLC case presence",
            "interface-to-oracle variable consistency",
            "requirement identifiers referenced by runtime cases",
            "nonempty formal properties",
            "manifest file hashes",
            "historical runtime cap and qualified-reference hash",
        ],
    }
    (ROOT / "structural_audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["success"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

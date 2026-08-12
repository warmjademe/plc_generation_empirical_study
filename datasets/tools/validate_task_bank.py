#!/usr/bin/env python3
"""Validate the frozen 200-task category-balanced pre-screen bank."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path


EXPECTED_CATEGORIES = {f"C{index:02d}" for index in range(1, 11)}
ALLOWED_TYPES = {"BOOL", "INT", "DINT", "REAL"}
REQUIRED_FILES = {
    "metadata.json", "requirement.md", "interface.st", "reference.st",
    "properties.json", "openplc_tests.json", "negative_control/index.json",
    "negative_control/NC1.st", "validation_report.json",
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def value_matches_type(value: object, plc_type: str) -> bool:
    if plc_type == "BOOL":
        return isinstance(value, bool)
    if plc_type in {"INT", "DINT"}:
        return isinstance(value, int) and not isinstance(value, bool)
    if plc_type == "REAL":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return False


def validate_openplc_suite(
    task_id: str, suite: dict, inputs: dict[str, str], outputs: dict[str, str],
    requirement_ids: set[str], errors: list[str],
) -> None:
    prefix = f"{task_id}/openplc"
    if suite.get("task_id") != task_id or suite.get("suite") != "openplc":
        errors.append(f"{prefix}: identity or suite label mismatch")
    if suite.get("oracle_source") != "independent_base_oracles_plus_explicit_composition_rules":
        errors.append(f"{prefix}: unexpected oracle provenance")
    if suite.get("independent_requirement_oracle") is not True:
        errors.append(f"{prefix}: oracle must be independently specified")
    cases = suite.get("cases", [])
    if not cases:
        errors.append(f"{prefix}: no functional test cases")
        return
    case_ids = [case.get("id") for case in cases]
    if len(case_ids) != len(set(case_ids)):
        errors.append(f"{prefix}: duplicate case ids")
    covered: set[str] = set()
    for case in cases:
        case_prefix = f"{prefix}/{case.get('id', '?')}"
        if case.get("fresh_instance") is not True:
            errors.append(f"{case_prefix}: fresh_instance must be true")
        if not str(case.get("oracle_source", "")).startswith("independent"):
            errors.append(f"{case_prefix}: case oracle is not independently sourced")
        refs = set(case.get("requirement_ids", []))
        if not refs or refs - requirement_ids:
            errors.append(f"{case_prefix}: invalid requirement references")
        covered.update(refs)
        steps = case.get("steps", [])
        if not steps:
            errors.append(f"{case_prefix}: no scan steps")
        for index, step in enumerate(steps, start=1):
            step_prefix = f"{case_prefix}/step{index}"
            actual_inputs = step.get("inputs", {})
            expected_outputs = step.get("expect", {})
            if set(actual_inputs) != set(inputs):
                errors.append(f"{step_prefix}: inputs do not match the fixed interface")
            if not expected_outputs or not set(expected_outputs) <= set(outputs):
                errors.append(f"{step_prefix}: expected outputs must be a non-empty interface subset")
            for name, value in actual_inputs.items():
                if name in inputs and not value_matches_type(value, inputs[name]):
                    errors.append(f"{step_prefix}: input {name} does not match {inputs[name]}")
            for name, value in expected_outputs.items():
                if name in outputs and not value_matches_type(value, outputs[name]):
                    errors.append(f"{step_prefix}: output {name} does not match {outputs[name]}")
            if not isinstance(step.get("repeat"), int) or step["repeat"] < 1:
                errors.append(f"{step_prefix}: repeat must be positive")
            if step.get("check") not in {"each", "last_only"}:
                errors.append(f"{step_prefix}: invalid check mode")
    if covered != requirement_ids:
        errors.append(f"{prefix}: requirement coverage differs; missing={sorted(requirement_ids-covered)}")


def validate_task(task_dir: Path, errors: list[str]) -> dict:
    task_id = task_dir.name
    present = {str(path.relative_to(task_dir)) for path in task_dir.rglob("*") if path.is_file()}
    missing = REQUIRED_FILES - present
    if missing:
        errors.append(f"{task_id}: missing files {sorted(missing)}")
        return {}
    metadata = read_json(task_dir / "metadata.json")
    properties = read_json(task_dir / "properties.json")
    suite = read_json(task_dir / "openplc_tests.json")
    control = read_json(task_dir / "negative_control/index.json")
    if metadata.get("id") != task_id:
        errors.append(f"{task_id}: metadata id mismatch")
    category = metadata.get("category_id")
    if category not in EXPECTED_CATEGORIES:
        errors.append(f"{task_id}: invalid category {category}")
    if "difficulty" in metadata or metadata.get("difficulty_stratification") != "not_used":
        errors.append(f"{task_id}: ordinal difficulty labels must not be used")

    interface = metadata.get("interface", {})
    input_fields = interface.get("inputs", [])
    output_fields = interface.get("outputs", [])
    names = [field.get("name") for field in input_fields + output_fields]
    if len(names) != len(set(names)):
        errors.append(f"{task_id}: duplicate interface names")
    for field in input_fields + output_fields:
        if field.get("type") not in ALLOWED_TYPES:
            errors.append(f"{task_id}: unsupported type {field.get('type')}")
    inputs = {field["name"]: field["type"] for field in input_fields}
    outputs = {field["name"]: field["type"] for field in output_fields}

    requirements = metadata.get("requirements", [])
    requirement_ids = {item.get("id") for item in requirements}
    if requirement_ids != {f"R{index}" for index in range(1, len(requirements) + 1)}:
        errors.append(f"{task_id}: requirement ids are not contiguous")
    if len(requirements) < 8:
        errors.append(f"{task_id}: fewer than eight interacting requirements")
    property_items = properties.get("properties", [])
    property_coverage = {rid for item in property_items for rid in item.get("requirement_ids", [])}
    critical_ids = {item["id"] for item in requirements if item.get("safety_critical")}
    if critical_ids - property_coverage:
        errors.append(f"{task_id}: safety requirements lack a stated property")
    if any(item.get("mandatory") is not True for item in property_items):
        errors.append(f"{task_id}: every listed property must be mandatory")
    if int(properties.get("plcverif_profile", {}).get("native_property_count", 0)) < 1:
        errors.append(f"{task_id}: no native PLCverif invariant")

    validate_openplc_suite(task_id, suite, inputs, outputs, requirement_ids, errors)
    interface_st = (task_dir / "interface.st").read_text(encoding="utf-8")
    reference_st = (task_dir / "reference.st").read_text(encoding="utf-8")
    for label, text in (("interface", interface_st), ("reference", reference_st)):
        if not text.startswith(f"FUNCTION_BLOCK {task_id}\n"):
            errors.append(f"{task_id}: {label}.st has the wrong block name")
        if len(re.findall(r"(?m)^FUNCTION_BLOCK\s+\w+\s*$", text)) != 1:
            errors.append(f"{task_id}: {label}.st has multiple blocks")
        if len(re.findall(r"(?m)^END_FUNCTION_BLOCK\s*$", text)) != 1:
            errors.append(f"{task_id}: {label}.st has unbalanced block markers")
    for name in outputs:
        if not re.search(rf"\b{re.escape(name)}\s*:=", reference_st):
            errors.append(f"{task_id}: output {name} is never assigned")
    controls = control.get("controls", [])
    if control.get("count") != 1 or len(controls) != 1 or controls[0].get("id") != "NC1":
        errors.append(f"{task_id}: exactly one NC1 control is required")
    negative_st = (task_dir / "negative_control/NC1.st").read_text(encoding="utf-8")
    if negative_st == reference_st:
        errors.append(f"{task_id}: negative control equals the reference")
    if controls and controls[0].get("operator") != "supervisory_blocked_stuck_false":
        errors.append(f"{task_id}: NC1 is not the predeclared supervisory sentinel")
    if reference_st.count("CrossBlocked := SubsystemBEnable AND (NOT CrossReady);") != 1:
        errors.append(f"{task_id}: reference lacks the calibrated CrossBlocked assignment")
    if negative_st.count("CrossBlocked := FALSE;") != 1:
        errors.append(f"{task_id}: NC1 does not force CrossBlocked FALSE exactly once")
    native_parameters = [
        str(parameter)
        for prop in property_items
        for case in prop.get("plcverif", {}).get("cases", [])
        for parameter in case.get("parameters", [])
    ]
    if not any("CrossBlocked = (SubsystemBEnable AND !CrossReady)" in value for value in native_parameters):
        errors.append(f"{task_id}: PLCverif profile does not cover the NC1 supervisory defect")
    sentinel_observed = any(
        step.get("inputs", {}).get("SubsystemBEnable") is True
        and step.get("expect", {}).get("CrossBlocked") is True
        for case in suite.get("cases", [])
        for step in case.get("steps", [])
    )
    if not sentinel_observed:
        errors.append(f"{task_id}: OpenPLC suite cannot observe the NC1 supervisory defect")
    complexity = metadata.get("complexity", {})
    if complexity.get("interactions", 0) < 8 or complexity.get("horizon_scans", 0) < 5:
        errors.append(f"{task_id}: documented complexity floor is not met")
    composition = metadata.get("composition", {})
    return {
        "id": task_id,
        "category": category,
        "base_a": composition.get("base_a"),
        "base_b": composition.get("base_b"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bank-root", required=True, type=Path)
    args = parser.parse_args()
    root = args.bank_root.resolve()
    task_root = root / "tasks"
    errors: list[str] = []
    task_dirs = sorted(path for path in task_root.iterdir() if path.is_dir()) if task_root.is_dir() else []
    if len(task_dirs) != 200:
        errors.append(f"expected 200 tasks, found {len(task_dirs)}")
    records = [validate_task(task_dir, errors) for task_dir in task_dirs]
    records = [record for record in records if record]
    categories = Counter(record["category"] for record in records)
    if set(categories) != EXPECTED_CATEGORIES or any(categories[category] != 20 for category in EXPECTED_CATEGORIES):
        errors.append(f"category counts invalid: {dict(sorted(categories.items()))}")
    compositions = [(record["category"], record["base_a"], record["base_b"]) for record in records]
    if len(set(compositions)) != len(compositions):
        errors.append("duplicate ordered compositions")
    for category in EXPECTED_CATEGORIES:
        rows = [record for record in records if record["category"] == category]
        if any(record["base_a"] == record["base_b"] for record in rows):
            errors.append(f"{category}: self-composition found")
        if set(Counter(record["base_a"] for record in rows).values()) != {4}:
            errors.append(f"{category}: subsystem-A base roles are imbalanced")
        if set(Counter(record["base_b"] for record in rows).values()) != {4}:
            errors.append(f"{category}: subsystem-B base roles are imbalanced")

    manifest_path = root / "manifest.jsonl"
    manifest = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines() if line] if manifest_path.is_file() else []
    if len(manifest) != 200:
        errors.append(f"manifest contains {len(manifest)} records")
    for item in manifest:
        for name, expected in item.get("hashes", {}).items():
            path = root / item["path"] / name
            if not path.is_file() or digest(path) != expected:
                errors.append(f"{item.get('id')}: hash mismatch for {name}")
    summary = read_json(root / "dataset_summary.json") if (root / "dataset_summary.json").is_file() else {}
    if summary.get("task_count") != 200 or summary.get("selection_status") != "not_run":
        errors.append("task-bank summary is not in frozen pre-screen state")
    if summary.get("difficulty_stratification") != "not_used":
        errors.append("task-bank summary must disable difficulty stratification")
    if errors:
        print(f"FAILED: {len(errors)} task-bank error(s)", file=sys.stderr)
        for error in errors[:300]:
            print(f"- {error}", file=sys.stderr)
        return 1
    for task_dir in task_dirs:
        report_path = task_dir / "validation_report.json"
        report = read_json(report_path)
        report["structural"] = {"status": "pass", "validator": "tools/validate_task_bank.py"}
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PASS: 200 tasks; 10 categories x 20 ordered non-self compositions")
    print("PASS: no difficulty strata; every base appears four times in each directional role")
    print("PASS: OpenPLC vectors use independent base oracles and explicit composition rules")
    print("NOTE: MatIEC, PLCverif, and OpenPLC qualification remain external gates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate IEC-ST-VerifyBench structure without claiming compiler correctness."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TASK_ROOT = ROOT / "tasks"
EXPECTED_CATEGORIES = {f"C{i:02d}" for i in range(1, 11)}
EXPECTED_PER_CATEGORY = {"easy": 1, "medium": 2, "hard": 2}
REQUIRED_FILES = {
    "metadata.json",
    "requirement.md",
    "interface.st",
    "reference.st",
    "properties.json",
    "tests_feedback.json",
    "tests_hidden.json",
    "negative_control/index.json",
    "negative_control/NC1.st",
    "validation_report.json",
}
ALLOWED_TYPES = {"BOOL", "INT", "DINT", "REAL", "TIME"}


def read_json(path: Path) -> object:
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
    if plc_type == "TIME":
        return isinstance(value, str) and bool(re.fullmatch(r"T#[0-9]+(?:ms|s|m)", value))
    return False


def validate_suite(
    task_id: str,
    suite_name: str,
    suite: dict,
    inputs: dict[str, str],
    outputs: dict[str, str],
    requirement_ids: set[str],
    errors: list[str],
) -> set[str]:
    prefix = f"{task_id}/{suite_name}"
    covered: set[str] = set()
    if suite.get("task_id") != task_id:
        errors.append(f"{prefix}: task_id mismatch")
    if suite.get("suite") != suite_name:
        errors.append(f"{prefix}: suite label mismatch")
    cases = suite.get("cases")
    if not isinstance(cases, list) or not cases:
        errors.append(f"{prefix}: cases must be a non-empty list")
        return covered
    case_ids = [case.get("id") for case in cases]
    if len(case_ids) != len(set(case_ids)):
        errors.append(f"{prefix}: duplicate case ids")
    for case in cases:
        case_prefix = f"{prefix}/{case.get('id', '?')}"
        refs = set(case.get("requirement_ids", []))
        unknown = refs - requirement_ids
        if unknown:
            errors.append(f"{case_prefix}: unknown requirements {sorted(unknown)}")
        covered.update(refs)
        if case.get("fresh_instance") is not True:
            errors.append(f"{case_prefix}: every case must request a fresh instance")
        steps = case.get("steps")
        if not isinstance(steps, list) or not steps:
            errors.append(f"{case_prefix}: steps must be a non-empty list")
            continue
        for index, item in enumerate(steps, start=1):
            step_prefix = f"{case_prefix}/step{index}"
            actual_inputs = item.get("inputs", {})
            expected_outputs = item.get("expect", {})
            if set(actual_inputs) != set(inputs):
                errors.append(
                    f"{step_prefix}: inputs differ; missing={sorted(set(inputs)-set(actual_inputs))}, "
                    f"extra={sorted(set(actual_inputs)-set(inputs))}"
                )
            if set(expected_outputs) != set(outputs):
                errors.append(
                    f"{step_prefix}: outputs differ; missing={sorted(set(outputs)-set(expected_outputs))}, "
                    f"extra={sorted(set(expected_outputs)-set(outputs))}"
                )
            for name, value in actual_inputs.items():
                if name in inputs and not value_matches_type(value, inputs[name]):
                    errors.append(f"{step_prefix}: input {name} does not match {inputs[name]}")
            for name, value in expected_outputs.items():
                if name in outputs and not value_matches_type(value, outputs[name]):
                    errors.append(f"{step_prefix}: output {name} does not match {outputs[name]}")
            if not isinstance(item.get("repeat"), int) or item["repeat"] < 1:
                errors.append(f"{step_prefix}: repeat must be a positive integer")
            if item.get("check") not in {"each", "last_only"}:
                errors.append(f"{step_prefix}: invalid check mode")
    return covered


def validate_task(task_dir: Path, errors: list[str]) -> dict:
    task_id = task_dir.name
    present = {
        str(path.relative_to(task_dir))
        for path in task_dir.rglob("*")
        if path.is_file()
    }
    missing = REQUIRED_FILES - present
    if missing:
        errors.append(f"{task_id}: missing files {sorted(missing)}")
        return {}

    try:
        metadata = read_json(task_dir / "metadata.json")
        properties = read_json(task_dir / "properties.json")
        feedback = read_json(task_dir / "tests_feedback.json")
        hidden = read_json(task_dir / "tests_hidden.json")
        control_index = read_json(task_dir / "negative_control/index.json")
    except (json.JSONDecodeError, OSError) as exc:
        errors.append(f"{task_id}: JSON read failure: {exc}")
        return {}

    if metadata.get("id") != task_id:
        errors.append(f"{task_id}: metadata id mismatch")
    category = metadata.get("category_id")
    difficulty = metadata.get("difficulty")
    if category not in EXPECTED_CATEGORIES:
        errors.append(f"{task_id}: invalid category {category}")
    if difficulty not in EXPECTED_PER_CATEGORY:
        errors.append(f"{task_id}: invalid difficulty {difficulty}")

    interface = metadata.get("interface", {})
    input_fields = interface.get("inputs", [])
    output_fields = interface.get("outputs", [])
    all_fields = input_fields + output_fields
    names = [field.get("name") for field in all_fields]
    if len(names) != len(set(names)):
        errors.append(f"{task_id}: duplicate interface names")
    for field in all_fields:
        if field.get("type") not in ALLOWED_TYPES:
            errors.append(f"{task_id}: unsupported type {field.get('type')}")
    inputs = {field["name"]: field["type"] for field in input_fields}
    outputs = {field["name"]: field["type"] for field in output_fields}

    requirements = metadata.get("requirements", [])
    requirement_ids = {item.get("id") for item in requirements}
    expected_ids = {f"R{i}" for i in range(1, len(requirements) + 1)}
    if requirement_ids != expected_ids:
        errors.append(f"{task_id}: requirement ids are not contiguous from R1")
    if not requirements:
        errors.append(f"{task_id}: no requirements")

    property_items = properties.get("properties", [])
    property_ids = [item.get("id") for item in property_items]
    if len(property_ids) != len(set(property_ids)):
        errors.append(f"{task_id}: duplicate property ids")
    property_coverage: set[str] = set()
    for item in property_items:
        refs = set(item.get("requirement_ids", []))
        if refs - requirement_ids:
            errors.append(f"{task_id}/{item.get('id')}: unknown requirement reference")
        property_coverage.update(refs)
        if item.get("mandatory") is not True:
            errors.append(f"{task_id}/{item.get('id')}: generated properties must be mandatory")
        if not item.get("expression"):
            errors.append(f"{task_id}/{item.get('id')}: empty expression")
    critical_ids = {r["id"] for r in requirements if r.get("safety_critical")}
    if critical_ids - property_coverage:
        errors.append(f"{task_id}: safety requirements lack properties {sorted(critical_ids-property_coverage)}")

    dynamic_coverage = set()
    dynamic_coverage.update(validate_suite(task_id, "feedback", feedback, inputs, outputs, requirement_ids, errors))
    dynamic_coverage.update(validate_suite(task_id, "hidden", hidden, inputs, outputs, requirement_ids, errors))
    if requirement_ids - dynamic_coverage:
        errors.append(f"{task_id}: requirements lack dynamic coverage {sorted(requirement_ids-dynamic_coverage)}")

    interface_st = (task_dir / "interface.st").read_text(encoding="utf-8")
    reference_st = (task_dir / "reference.st").read_text(encoding="utf-8")
    for label, text in (("interface", interface_st), ("reference", reference_st)):
        if not text.startswith(f"FUNCTION_BLOCK {task_id}\n"):
            errors.append(f"{task_id}: {label}.st has wrong function-block declaration")
        start_count = len(re.findall(r"(?m)^FUNCTION_BLOCK\s+\w+\s*$", text))
        end_count = len(re.findall(r"(?m)^END_FUNCTION_BLOCK\s*$", text))
        if start_count != 1 or end_count != 1:
            errors.append(f"{task_id}: {label}.st has unbalanced outer block markers")
    for name in outputs:
        if not re.search(rf"\b{re.escape(name)}\s*:=", reference_st):
            errors.append(f"{task_id}: output {name} is never assigned in reference.st")

    controls = control_index.get("controls", [])
    if control_index.get("count") != 1 or len(controls) != 1 or controls[0].get("id") != "NC1":
        errors.append(f"{task_id}: exactly one NC1 negative control is required")
    if controls:
        target_refs = set(controls[0].get("target_requirement_ids", []))
        if not target_refs or target_refs - requirement_ids:
            errors.append(f"{task_id}: negative control has invalid target requirement")
    if (task_dir / "negative_control/NC1.st").read_bytes() == (task_dir / "reference.st").read_bytes():
        errors.append(f"{task_id}: negative control is identical to reference")

    return {"id": task_id, "category": category, "difficulty": difficulty}


def update_structural_reports(task_dirs: list[Path]) -> None:
    for task_dir in task_dirs:
        path = task_dir / "validation_report.json"
        report = read_json(path)
        report["structural"] = {
            "status": "pass",
            "validator": "tools/validate_dataset.py",
            "checks": "schema, coverage, interfaces, value types, artifacts, controls, manifest hashes",
        }
        path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    errors: list[str] = []
    task_dirs = sorted(path for path in TASK_ROOT.iterdir() if path.is_dir()) if TASK_ROOT.exists() else []
    if len(task_dirs) != 50:
        errors.append(f"dataset: expected 50 task directories, found {len(task_dirs)}")
    records = [validate_task(path, errors) for path in task_dirs]
    records = [record for record in records if record]

    by_category = Counter(record["category"] for record in records)
    if set(by_category) != EXPECTED_CATEGORIES or any(by_category[c] != 5 for c in EXPECTED_CATEGORIES):
        errors.append(f"dataset: category counts invalid: {dict(sorted(by_category.items()))}")
    for category in EXPECTED_CATEGORIES:
        observed = Counter(record["difficulty"] for record in records if record["category"] == category)
        if dict(observed) != EXPECTED_PER_CATEGORY:
            errors.append(f"dataset: {category} difficulty counts invalid: {dict(observed)}")

    manifest_path = ROOT / "manifest.jsonl"
    if not manifest_path.exists():
        errors.append("dataset: manifest.jsonl missing")
    else:
        manifest = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines() if line]
        if len(manifest) != 50:
            errors.append(f"dataset: manifest has {len(manifest)} records")
        if {item.get("id") for item in manifest} != {path.name for path in task_dirs}:
            errors.append("dataset: manifest task ids differ from task directories")
        for item in manifest:
            task_dir = ROOT / item["path"]
            for name, expected in item.get("hashes", {}).items():
                path = task_dir / name
                if not path.exists() or digest(path) != expected:
                    errors.append(f"{item.get('id')}: manifest hash mismatch for {name}")

    summary_path = ROOT / "dataset_summary.json"
    if not summary_path.exists():
        errors.append("dataset: dataset_summary.json missing")
    else:
        summary = read_json(summary_path)
        if summary.get("primary_task_count") != 50:
            errors.append("dataset: primary_task_count must be exactly 50")
        if summary.get("optional_negative_control_count") != 50:
            errors.append("dataset: optional_negative_control_count must be 50")
        if summary.get("negative_controls_use_llm") is not False:
            errors.append("dataset: negative controls must not use LLM calls")

    if errors:
        print(f"FAILED: {len(errors)} structural error(s)", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    update_structural_reports(task_dirs)
    print("PASS: 50 primary tasks; 10 categories x (1 easy, 2 medium, 2 hard)")
    print("PASS: all requirements have dynamic coverage; all safety requirements have formal properties")
    print("PASS: 50 optional NC1 controls are excluded from LLM scoring")
    print("NOTE: compiler, formal-backend, and OpenPLC statuses remain not_run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

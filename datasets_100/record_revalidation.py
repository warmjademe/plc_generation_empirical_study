#!/usr/bin/env python3
"""Import a successful exact-toolchain reference calibration into the dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def percentile(values: list[int], probability: float) -> int:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(probability * len(ordered)))]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calibration-summary", required=True, type=Path)
    parser.add_argument("--validator-config", required=True, type=Path)
    args = parser.parse_args()

    calibration_path = args.calibration_summary.resolve()
    config_path = args.validator_config.resolve()
    calibration = json.loads(calibration_path.read_text(encoding="utf-8"))
    manifest_path = ROOT / "manifest.jsonl"
    manifest = {
        record["id"]: record
        for record in (
            json.loads(line)
            for line in manifest_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }
    records = calibration.get("tasks", [])
    by_id = {record.get("task_id"): record for record in records}
    errors: list[str] = []
    if calibration.get("success") is not True:
        errors.append("calibration did not report success")
    if calibration.get("task_count") != 100 or calibration.get("pass_count") != 100:
        errors.append("calibration is not a 100/100 reference pass")
    if calibration.get("dataset_manifest_sha256") != sha256(manifest_path):
        errors.append("calibration manifest hash differs from this dataset")
    if calibration.get("config_sha256") != sha256(config_path):
        errors.append("calibration validator-config hash differs from the supplied config")
    if set(by_id) != set(manifest):
        errors.append("calibration task IDs differ from this dataset")
    for task_id, record in by_id.items():
        if record.get("status") != "pass":
            errors.append(f"{task_id}: reference status is not pass")
            continue
        expected = manifest.get(task_id, {}).get("hashes", {}).get("reference.st")
        if record.get("reference_sha256") != expected:
            errors.append(f"{task_id}: calibrated reference hash differs from manifest")
        gate_names = [gate.get("name") for gate in record.get("gates", [])]
        if gate_names != ["compiler", "plcverif", "openplc_feedback", "openplc"]:
            errors.append(f"{task_id}: unexpected validator order {gate_names}")
    if errors:
        raise ValueError("; ".join(errors))

    evidence = ROOT / "evidence" / "exact_revalidation"
    evidence.mkdir(parents=True, exist_ok=True)
    imported_calibration = evidence / "calibration_summary.json"
    imported_config = evidence / "validator_config.json"
    shutil.copy2(calibration_path, imported_calibration)
    shutil.copy2(config_path, imported_config)

    durations = [
        sum(int(gate.get("duration_ms", 0)) for gate in record.get("gates", []))
        for record in records
    ]
    result = {
        "schema_version": "1.0",
        "task_count": 100,
        "pass_count": 100,
        "success": True,
        "toolchain": ["MatIEC", "PLCverif", "OpenPLC feedback", "OpenPLC sealed"],
        "reference_duration_ms": {
            "minimum": min(durations),
            "median": statistics.median(durations),
            "p90": percentile(durations, 0.9),
            "maximum": max(durations),
        },
        "manifest_sha256": sha256(manifest_path),
        "calibration_summary_sha256": sha256(imported_calibration),
        "validator_config_sha256": sha256(imported_config),
    }
    write_json(ROOT / "revalidation_summary.json", result)

    dataset_summary_path = ROOT / "dataset_summary.json"
    dataset_summary = json.loads(dataset_summary_path.read_text(encoding="utf-8"))
    dataset_summary["qualification_status"] = "exact current toolchain revalidation passed 100/100"
    dataset_summary["exact_reference_revalidation"] = result
    write_json(dataset_summary_path, dataset_summary)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

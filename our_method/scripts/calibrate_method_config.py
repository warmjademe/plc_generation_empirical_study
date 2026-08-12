#!/usr/bin/env python3
"""Calibrate every configured validator on frozen reference programs."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from plc_loop.dataset import load_task
from plc_loop.orchestrator import load_config
from plc_loop.validators import validators_from_config


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--dataset-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--include", action="append", default=[])
    args = parser.parse_args()
    if args.workers < 1:
        raise ValueError("workers must be positive")

    config_path = args.config.resolve()
    config = load_config(config_path)
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty calibration directory: {output}")
    output.mkdir(parents=True, exist_ok=True)
    included = set(args.include)
    task_dirs = [
        path for path in sorted((args.dataset_root.resolve() / "tasks").iterdir())
        if path.is_dir() and (not included or path.name in included)
    ]
    missing = included - {path.name for path in task_dirs}
    if missing:
        raise ValueError(f"included tasks were not found: {sorted(missing)}")

    def calibrate(task_dir: Path) -> dict[str, Any]:
        task = load_task(task_dir)
        validators = validators_from_config(
            config.get("validators", []),
            base_dir=Path(config["_config_dir"]),
        )
        for validator in validators:
            validator.preflight(task)
        task_output = output / task.task_id
        task_output.mkdir()
        candidate = task_dir / "reference.st"
        gates = []
        blocked = False
        for validator in validators:
            if blocked:
                break
            gate = validator.run(task, candidate, task_output)
            gates.append(gate)
            if validator.blocking and gate.status != "pass":
                blocked = True
        record = {
            "task_id": task.task_id,
            "reference_sha256": sha256(candidate),
            "status": "pass" if len(gates) == len(validators) and all(gate.status == "pass" for gate in gates) else "fail",
            "gates": [gate.to_dict() for gate in gates],
        }
        write_json(task_output / "calibration.json", record)
        return record

    records = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(calibrate, task_dir): task_dir.name for task_dir in task_dirs}
        for future in as_completed(futures):
            task_id = futures[future]
            try:
                record = future.result()
            except Exception as exc:
                record = {
                    "task_id": task_id,
                    "status": "infrastructure_error",
                    "error": f"{type(exc).__name__}: {exc}",
                    "gates": [],
                }
            records.append(record)
            print(json.dumps({
                "completed": len(records),
                "total": len(task_dirs),
                "task_id": task_id,
                "status": record["status"],
            }, ensure_ascii=False), flush=True)

    records.sort(key=lambda item: item["task_id"])
    status_counts = Counter(item["status"] for item in records)
    gate_durations: Counter[str] = Counter()
    for record in records:
        for gate in record.get("gates", []):
            gate_durations[gate["name"]] += int(gate.get("duration_ms", 0))
    document = {
        "schema_version": "1.0",
        "purpose": "reference-program calibration of the exact method validator configuration",
        "config": str(config_path),
        "config_sha256": sha256(config_path),
        "dataset_root": str(args.dataset_root.resolve()),
        "dataset_manifest_sha256": sha256(args.dataset_root.resolve() / "manifest.jsonl"),
        "workers": args.workers,
        "task_count": len(records),
        "pass_count": status_counts.get("pass", 0),
        "status_counts": dict(sorted(status_counts.items())),
        "gate_duration_ms_total": dict(sorted(gate_durations.items())),
        "success": bool(records) and status_counts == Counter({"pass": len(records)}),
        "tasks": records,
    }
    write_json(output / "calibration_summary.json", document)
    print(json.dumps({
        "task_count": document["task_count"],
        "pass_count": document["pass_count"],
        "status_counts": document["status_counts"],
        "success": document["success"],
    }, ensure_ascii=False), flush=True)
    return 0 if document["success"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

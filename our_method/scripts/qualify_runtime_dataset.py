#!/usr/bin/env python3
"""Qualify compiler, scan, and sealed OpenPLC judges on the full dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from plc_loop.dataset import load_task
from plc_loop.validators import CommandValidator, DatasetScanValidator, InterfaceValidator


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", required=True, type=Path)
    parser.add_argument("--engine-root", required=True, type=Path)
    parser.add_argument("--matiec", required=True, type=Path)
    parser.add_argument("--openplc-validator", required=True, type=Path)
    parser.add_argument("--openplc-runner", required=True, type=Path)
    parser.add_argument("--docker", default="/snap/bin/docker")
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    dataset_root = args.dataset_root.resolve()
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty qualification directory {output}")
    output.mkdir(parents=True, exist_ok=True)
    task_dirs = sorted(path for path in (dataset_root / "tasks").iterdir() if path.is_dir())

    def qualify(task_dir: Path) -> dict:
        task = load_task(task_dir)
        validators = [
            InterfaceValidator(),
            CommandValidator(
                name="compiler",
                command=(
                    "python3",
                    str((Path(__file__).parent / "matiec_validator.py").resolve()),
                    "--candidate", "{candidate}",
                    "--iec2iec", str(args.matiec.resolve()),
                ),
                timeout_seconds=120,
                version="matiec-0.1",
            ),
            DatasetScanValidator("feedback_tests", "feedback", args.engine_root.resolve()),
            DatasetScanValidator("hidden_scan", "hidden", args.engine_root.resolve(), sealed=True),
            CommandValidator(
                name="sealed_openplc",
                command=(
                    "python3", str(args.openplc_validator.resolve()),
                    "--candidate", "{candidate}",
                    "--task-dir", "{task_dir}",
                    "--docker", str(args.docker),
                    "--image", args.image,
                    "--runner", str(args.openplc_runner.resolve()),
                ),
                timeout_seconds=420,
                sealed=True,
                version="OpenPLC_v3@b5d41356dab4aeadca0dd7ca64ba542f870b595d",
            ),
        ]
        for validator in validators:
            validator.preflight(task)
        candidates = {
            "reference": task_dir / "reference.st",
            "authored_negative": task_dir / "negative_control" / "NC1.st",
        }
        record = {"task_id": task.task_id, "candidates": {}}
        for role, candidate in candidates.items():
            artifact_dir = output / task.task_id / role
            artifact_dir.mkdir(parents=True, exist_ok=True)
            gates = [validator.run(task, candidate, artifact_dir) for validator in validators]
            record["candidates"][role] = {
                "candidate_sha256": sha256(candidate),
                "gates": [gate.to_dict() for gate in gates],
            }
        reference = {g["name"]: g["status"] for g in record["candidates"]["reference"]["gates"]}
        negative = {g["name"]: g["status"] for g in record["candidates"]["authored_negative"]["gates"]}
        record["reference_statuses"] = reference
        record["authored_negative_statuses"] = negative
        record["qualified"] = (
            all(status == "pass" for status in reference.values())
            and negative.get("interface") == "pass"
            and negative.get("compiler") == "pass"
            and any(negative.get(name) == "fail" for name in ("feedback_tests", "hidden_scan", "sealed_openplc"))
        )
        return record

    records = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(qualify, task_dir): task_dir.name for task_dir in task_dirs}
        for future in as_completed(futures):
            task_id = futures[future]
            try:
                record = future.result()
            except Exception as exc:
                record = {
                    "task_id": task_id,
                    "qualified": False,
                    "infrastructure_exception": f"{type(exc).__name__}: {exc}",
                }
            records.append(record)
            print(json.dumps({"task_id": task_id, "qualified": record["qualified"]}, ensure_ascii=False), flush=True)
    records.sort(key=lambda item: item["task_id"])
    document = {
        "schema_version": "1.0",
        "qualification_scope": "interface + MatIEC + visible/hidden deterministic scan + sealed OpenPLC",
        "formal_qualification_included": False,
        "task_count": len(records),
        "qualified_count": sum(bool(item["qualified"]) for item in records),
        "status": "pass" if all(item["qualified"] for item in records) else "fail",
        "tasks": records,
    }
    (output / "qualification.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": document["status"],
        "qualified_count": document["qualified_count"],
        "failed_tasks": [item["task_id"] for item in records if not item["qualified"]],
    }, ensure_ascii=False))
    return 0 if document["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

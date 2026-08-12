#!/usr/bin/env python3
"""Qualify the Boolean pilot judges with references and negative controls."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from plc_loop.dataset import load_task
from plc_loop.orchestrator import load_config
from plc_loop.validators import validators_from_config


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--dataset-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    config = load_config(args.config)
    dataset_root = Path(args.dataset_root).resolve()
    output = Path(args.output).resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty qualification directory {output}")
    output.mkdir(parents=True, exist_ok=True)
    task_ids = list(config.get("scope", {}).get("task_ids", []))
    if not task_ids:
        raise ValueError("configuration has no scope.task_ids")
    validators = validators_from_config(
        config["validators"],
        base_dir=Path(config["_config_dir"]),
    )
    records = []
    qualified = True
    for task_id in task_ids:
        task = load_task(dataset_root / "tasks" / task_id)
        for validator in validators:
            validator.preflight(task)
        candidates = {
            "reference": task.root / "reference.st",
            "authored_negative": task.root / "negative_control" / "NC1.st",
        }
        first_output = task.metadata["interface"]["outputs"][0]["name"]
        sentinel_dir = output / task_id / "sealed_sentinel"
        sentinel_dir.mkdir(parents=True)
        sentinel = sentinel_dir / "candidate.st"
        reference_source = candidates["reference"].read_text(encoding="utf-8")
        sentinel_source, replacements = re.subn(
            r"(?im)^\s*END_FUNCTION_BLOCK\s*$",
            f"\n{first_output} := NOT {first_output};\nEND_FUNCTION_BLOCK",
            reference_source,
            count=1,
        )
        if replacements != 1:
            raise ValueError(f"unable to construct sealed sentinel for {task_id}")
        sentinel.write_text(sentinel_source, encoding="utf-8")
        candidates["sealed_sentinel"] = sentinel
        task_record = {"task_id": task_id, "candidates": {}, "qualified": True}
        for role, candidate in candidates.items():
            artifact_dir = output / task_id / role
            artifact_dir.mkdir(parents=True, exist_ok=True)
            results = [validator.run(task, candidate, artifact_dir) for validator in validators]
            task_record["candidates"][role] = {
                "candidate_sha256": sha256(candidate),
                "gates": [result.to_dict() for result in results],
            }
        reference_status = {
            item["name"]: item["status"]
            for item in task_record["candidates"]["reference"]["gates"]
        }
        authored_negative_status = {
            item["name"]: item["status"]
            for item in task_record["candidates"]["authored_negative"]["gates"]
        }
        sentinel_status = {
            item["name"]: item["status"]
            for item in task_record["candidates"]["sealed_sentinel"]["gates"]
        }
        task_record["qualified"] = (
            all(status == "pass" for status in reference_status.values())
            and authored_negative_status.get("interface") == "pass"
            and authored_negative_status.get("compiler") == "pass"
            and authored_negative_status.get("feedback_tests") == "fail"
            and authored_negative_status.get("plcverif") == "fail"
            and sentinel_status.get("interface") == "pass"
            and sentinel_status.get("compiler") == "pass"
            and sentinel_status.get("plcverif") == "fail"
            and sentinel_status.get("sealed_openplc") == "fail"
        )
        task_record["reference_statuses"] = reference_status
        task_record["authored_negative_statuses"] = authored_negative_status
        task_record["sealed_sentinel_statuses"] = sentinel_status
        qualified = qualified and task_record["qualified"]
        records.append(task_record)

    document = {
        "schema_version": "1.0",
        "status": "pass" if qualified else "fail",
        "qualification_contract": {
            "reference": "all configured gates pass",
            "authored_negative": "interface and compiler pass; visible scan and PLCverif fail",
            "sealed_sentinel": "interface and compiler pass; PLCverif and sealed OpenPLC fail",
        },
        "task_count": len(records),
        "tasks": records,
    }
    (output / "qualification.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": document["status"],
        "task_count": len(records),
        "qualified_tasks": [record["task_id"] for record in records if record["qualified"]],
        "failed_tasks": [record["task_id"] for record in records if not record["qualified"]],
    }, ensure_ascii=False))
    return 0 if qualified else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Run the mandatory native PLCverif profile on every reference program."""

from __future__ import annotations

import argparse
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", required=True, type=Path)
    parser.add_argument("--validator", required=True, type=Path)
    parser.add_argument("--plcverif", required=True, type=Path)
    parser.add_argument("--nuxmv", required=True, type=Path)
    parser.add_argument("--cbmc", required=True, type=Path)
    parser.add_argument("--timer-library", required=True, type=Path)
    parser.add_argument("--numeric-library", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty qualification directory {output}")
    output.mkdir(parents=True, exist_ok=True)
    task_dirs = sorted(path for path in (args.dataset_root.resolve() / "tasks").iterdir() if path.is_dir())

    def run(task_dir: Path) -> dict:
        artifact = output / task_dir.name
        artifact.mkdir()
        command = [
            "python3", str(args.validator.resolve()),
            "--candidate", str((task_dir / "reference.st").resolve()),
            "--task-dir", str(task_dir.resolve()),
            "--plcverif", str(args.plcverif.resolve()),
            "--nuxmv", str(args.nuxmv.resolve()),
            "--cbmc", str(args.cbmc.resolve()),
            "--timer-library", str(args.timer_library.resolve()),
            "--numeric-library", str(args.numeric_library.resolve()),
            "--property-kind", "all",
            "--minimum-properties", "1",
            "--backend-timeout", "120",
            "--cbmc-unwind", "10",
        ]
        completed = subprocess.run(command, cwd=artifact, text=True, capture_output=True, timeout=600, check=False)
        (artifact / "validator.stdout").write_text(completed.stdout, encoding="utf-8")
        (artifact / "validator.stderr").write_text(completed.stderr, encoding="utf-8")
        try:
            result = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            result = {"status": "inconclusive", "summary": f"invalid validator JSON: {exc}"}
        return {"task_id": task_dir.name, "returncode": completed.returncode, "result": result}

    records = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(run, task_dir): task_dir.name for task_dir in task_dirs}
        for future in as_completed(futures):
            task_id = futures[future]
            try:
                record = future.result()
            except Exception as exc:
                record = {"task_id": task_id, "returncode": -1, "result": {"status": "inconclusive", "summary": f"{type(exc).__name__}: {exc}"}}
            records.append(record)
            print(json.dumps({"task_id": task_id, "status": record["result"].get("status")}), flush=True)
    records.sort(key=lambda item: item["task_id"])
    statuses = {item["task_id"]: item["result"].get("status") for item in records}
    document = {
        "schema_version": "1.0",
        "scope": "all mandatory cases in each task's frozen native-pattern-invariant-v1 PLCverif profile",
        "status": "pass" if all(status == "pass" for status in statuses.values()) else "fail",
        "task_count": len(records),
        "pass_count": sum(status == "pass" for status in statuses.values()),
        "records": records,
    }
    (output / "qualification.json").write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": document["status"],
        "pass_count": document["pass_count"],
        "failed_tasks": [task for task, status in statuses.items() if status != "pass"],
    }, ensure_ascii=False))
    return 0 if document["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Export auditable RQ2 raw records without verbose verifier work directories."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
from pathlib import Path


ATTEMPT_FILES = (
    "request.json",
    "raw_response.json",
    "candidate.st",
    "feedback_certificate.json",
    "task_state.json",
    "evaluation.json",
    "sealed_evaluation.json",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_gzip_jsonl(path: Path, records) -> None:
    with gzip.open(path, "wt", encoding="utf-8", compresslevel=9) as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def export_arm(name: str, root: Path, output: Path) -> list[Path]:
    destination = output / name
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / "batch_summary.json", destination / "batch_summary.json")
    task_dirs = sorted(path for path in root.iterdir() if (path / "result.json").is_file())
    if len(task_dirs) != 100:
        raise ValueError(f"{name} has {len(task_dirs)} completed task results, expected 100")

    results = []
    ledgers = []
    attempts = []
    for task_dir in task_dirs:
        task = task_dir.name
        results.append({"task_id": task, "result": json.loads((task_dir / "result.json").read_text())})
        for line in (task_dir / "ledger.jsonl").read_text(encoding="utf-8").splitlines():
            ledgers.append({"task_id": task, "event": json.loads(line)})
        for attempt_dir in sorted((task_dir / "attempts").glob("attempt_*")):
            record = {"task_id": task, "attempt": attempt_dir.name, "files": {}}
            for filename in ATTEMPT_FILES:
                path = attempt_dir / filename
                if not path.is_file():
                    continue
                if path.suffix == ".json":
                    record["files"][filename] = json.loads(path.read_text(encoding="utf-8"))
                else:
                    record["files"][filename] = path.read_text(encoding="utf-8")
            attempts.append(record)

    write_gzip_jsonl(destination / "task_results.jsonl.gz", results)
    write_gzip_jsonl(destination / "ledger_events.jsonl.gz", ledgers)
    write_gzip_jsonl(destination / "attempt_records.jsonl.gz", attempts)
    return sorted(path for path in destination.iterdir() if path.is_file())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--m01-run", required=True, type=Path)
    parser.add_argument("--m10-run", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--m01-log", type=Path)
    parser.add_argument("--m10-log", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite export: {args.output}")
    args.output.mkdir(parents=True)
    files = []
    files.extend(export_arm("M01_without_component_1", args.m01_run, args.output))
    files.extend(export_arm("M10_without_component_2", args.m10_run, args.output))
    for label, source in (("M01.controller.log", args.m01_log), ("M10.controller.log", args.m10_log)):
        if source and source.is_file():
            destination = args.output / label
            shutil.copy2(source, destination)
            files.append(destination)
    manifest = {
        "schema_version": "1.0",
        "scope": "RQ2 compact raw records; verbose validator work files excluded",
        "artifacts": [
            {
                "path": path.relative_to(args.output).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in sorted(files)
        ],
    }
    (args.output / "artifact_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

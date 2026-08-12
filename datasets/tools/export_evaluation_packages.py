#!/usr/bin/env python3
"""Physically separate model-visible tasks from visible and sealed oracle files."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


DATASET_ROOT = Path(__file__).resolve().parents[1]


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def public_metadata(metadata: dict) -> dict:
    return {
        "schema_version": metadata["schema_version"],
        "dataset_version": metadata["dataset_version"],
        "id": metadata["id"],
        "title": metadata["title"],
        "category_id": metadata["category_id"],
        "category": metadata["category"],
        "difficulty": metadata["difficulty"],
        "iec_profile": metadata["iec_profile"],
        "iec_features": metadata["iec_features"],
        "complexity": metadata["complexity"],
        "interface": metadata["interface"],
        "scan": metadata["scan"],
        "assumptions": metadata["assumptions"],
        "requirements": [
            {
                "id": requirement["id"],
                "text": requirement["text"],
                "safety_critical": requirement["safety_critical"],
            }
            for requirement in metadata["requirements"]
        ],
    }


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export(output: Path) -> None:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing export: {output}")
    roots = {
        "public_tasks": output / "public_tasks",
        "visible_oracles": output / "visible_oracles",
        "sealed_oracles": output / "sealed_oracles",
        "qualification_only": output / "qualification_only",
    }
    for root in roots.values():
        root.mkdir(parents=True)

    split_manifest = []
    for task_dir in sorted((DATASET_ROOT / "tasks").iterdir()):
        if not task_dir.is_dir():
            continue
        task_id = task_dir.name
        destinations = {name: root / task_id for name, root in roots.items()}
        for destination in destinations.values():
            destination.mkdir()

        metadata = json.loads((task_dir / "metadata.json").read_text(encoding="utf-8"))
        write_json(destinations["public_tasks"] / "metadata.json", public_metadata(metadata))
        shutil.copy2(task_dir / "requirement.md", destinations["public_tasks"] / "requirement.md")
        shutil.copy2(task_dir / "interface.st", destinations["public_tasks"] / "interface.st")

        shutil.copy2(task_dir / "tests_feedback.json", destinations["visible_oracles"] / "tests_feedback.json")
        shutil.copy2(task_dir / "properties.json", destinations["visible_oracles"] / "properties.json")

        shutil.copy2(task_dir / "tests_hidden.json", destinations["sealed_oracles"] / "tests_hidden.json")

        shutil.copy2(task_dir / "reference.st", destinations["qualification_only"] / "reference.st")
        shutil.copytree(task_dir / "negative_control", destinations["qualification_only"] / "negative_control")
        shutil.copy2(task_dir / "validation_report.json", destinations["qualification_only"] / "validation_report.json")

        split_manifest.append(
            {
                "id": task_id,
                "public_hashes": {
                    name: file_hash(destinations["public_tasks"] / name)
                    for name in ("metadata.json", "requirement.md", "interface.st")
                },
                "visible_oracle_hashes": {
                    name: file_hash(destinations["visible_oracles"] / name)
                    for name in ("tests_feedback.json", "properties.json")
                },
                "sealed_oracle_hashes": {
                    "tests_hidden.json": file_hash(destinations["sealed_oracles"] / "tests_hidden.json")
                },
            }
        )

    (output / "manifest.jsonl").write_text(
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in split_manifest),
        encoding="utf-8",
    )
    (output / "PACKAGE_README.md").write_text(
        """# Evaluation package separation

- `public_tasks/` is the only tree allowed in model prompts.
- `visible_oracles/` is available to the feedback harness, not to the model.
- `sealed_oracles/` is mounted only by the terminal judge and returns no feedback.
- `qualification_only/` contains reference answers and negative controls.  It is
  used to validate the dataset and must never be mounted in a scored model worker.

There are exactly 50 task IDs in each split.  `reference.st` is not a model input or
an evaluated candidate; it exists only to show that the authored contract is
satisfiable and to calibrate the oracles.
""",
        encoding="utf-8",
    )
    roots["sealed_oracles"].chmod(0o700)
    roots["qualification_only"].chmod(0o700)
    print(f"Exported {len(split_manifest)} task IDs into four isolated trees at {output}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    export(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


"""Load the public task contract while keeping answer artifacts out of prompts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TaskPackage:
    root: Path
    metadata: dict
    requirement_text: str
    interface_text: str

    @property
    def task_id(self) -> str:
        return str(self.metadata["id"])

    @property
    def requirement_ids(self) -> set[str]:
        return {item["id"] for item in self.metadata["requirements"]}

    @property
    def critical_requirement_ids(self) -> set[str]:
        return {
            item["id"]
            for item in self.metadata["requirements"]
            if item.get("safety_critical")
        }

    def suite_path(self, suite: str) -> Path:
        if suite not in {"feedback", "hidden", "stress"}:
            raise ValueError(f"unknown test suite {suite!r}")
        return self.root / f"tests_{suite}.json"

    def public_contract(self) -> str:
        return (
            "PUBLIC REQUIREMENTS\n"
            f"{self.requirement_text.rstrip()}\n\n"
            "FIXED INTERFACE\n"
            f"{self.interface_text.rstrip()}\n"
        )


def load_task(path: str | Path) -> TaskPackage:
    root = Path(path).resolve()
    required = [root / "metadata.json", root / "requirement.md", root / "interface.st"]
    missing = [str(item) for item in required if not item.is_file()]
    if missing:
        raise FileNotFoundError(f"task package is incomplete: {missing}")
    metadata = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
    if metadata.get("id") != root.name:
        raise ValueError("task directory and metadata id differ")
    # Deliberately do not open reference.st, tests_hidden.json, or properties.json.
    return TaskPackage(
        root=root,
        metadata=metadata,
        requirement_text=(root / "requirement.md").read_text(encoding="utf-8"),
        interface_text=(root / "interface.st").read_text(encoding="utf-8"),
    )

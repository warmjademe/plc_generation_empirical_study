#!/usr/bin/env python3
"""Verify release executables and container images against the frozen manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def docker_image_id(reference: str) -> str:
    completed = subprocess.run(
        ["/usr/bin/docker", "image", "inspect", reference, "--format", "{{.Id}}"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=15,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"container image unavailable: {reference}")
    return completed.stdout.strip()


def verify_manifest(project_root: Path, tool_root: Path) -> dict:
    manifest = json.loads(
        (project_root / "deploy/tool-manifest.json").read_text(encoding="utf-8")
    )
    checks: dict[str, dict] = {}
    failures: list[str] = []
    for relative, expected_value in manifest.get("executables", {}).items():
        path = tool_root / relative
        expected = str(expected_value).removeprefix("sha256:")
        actual = file_sha256(path) if path.is_file() else None
        passed = actual == expected
        checks[f"executable:{relative}"] = {"pass": passed, "sha256": actual}
        if not passed:
            failures.append(f"tool hash mismatch: {relative}")
    for key, reference_key in (("openplc_image", "tag"), ("postgres_image", "reference")):
        item = manifest.get(key, {})
        reference = str(item.get(reference_key, ""))
        try:
            actual = docker_image_id(reference)
        except RuntimeError:
            actual = None
        expected = str(item.get("image_id", ""))
        passed = bool(reference and actual == expected)
        checks[key] = {"pass": passed, "reference": reference, "image_id": actual}
        if not passed:
            failures.append(f"container identity mismatch: {key}")
    return {"status": "pass" if not failures else "fail", "checks": checks, "failures": failures}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--tool-root", type=Path, required=True)
    args = parser.parse_args()
    result = verify_manifest(args.project_root.resolve(), args.tool_root.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

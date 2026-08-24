#!/usr/bin/env python3
"""Create and verify a consistent database plus immutable-evidence backup."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_backup(root: Path) -> dict:
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for name, expected in manifest["sha256"].items():
        path = root / name
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"backup checksum mismatch: {name}")
    # The path exists only inside the private database container. A random name
    # prevents overlapping manual and scheduled verification runs.
    container_dump = str(
        Path(tempfile.gettempdir())
        / f"plc_generation_backup_verify_{uuid.uuid4().hex}.dump"
    )
    subprocess.run(
        [
            "/usr/bin/docker", "cp", str(root / "database.dump"),
            f"plc-generation-postgres:{container_dump}",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        check=True,
    )
    try:
        subprocess.run(
            [
                "/usr/bin/docker", "exec", "plc-generation-postgres",
                "pg_restore", "--list", container_dump,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=True,
        )
    finally:
        subprocess.run(
            [
                "/usr/bin/docker", "exec", "plc-generation-postgres",
                "rm", "-f", container_dump,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    subprocess.run(
        ["/usr/bin/tar", "--list", "--gzip", "--file", str(root / "evidence.tar.gz")],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        check=True,
    )
    return manifest


def create_backup(data_root: Path, backup_root: Path, retention_days: int) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    partial = backup_root / f".{stamp}.partial"
    complete = backup_root / stamp
    backup_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if partial.exists():
        shutil.rmtree(partial)
    partial.mkdir(mode=0o700)
    try:
        with (partial / "database.dump").open("wb") as stream:
            subprocess.run(
                [
                    "/usr/bin/docker", "exec", "plc-generation-postgres",
                    "pg_dump", "-U", "plc_generation", "-d", "plc_generation", "-Fc",
                ],
                stdout=stream,
                stderr=subprocess.PIPE,
                check=True,
            )
        evidence = partial / "evidence.tar.gz"
        jobs = data_root / "jobs"
        if jobs.is_dir():
            subprocess.run(
                [
                    "/usr/bin/tar", "--create", "--gzip", "--file", str(evidence),
                    "--directory", str(data_root), "jobs",
                ],
                stderr=subprocess.PIPE,
                check=True,
            )
        else:
            subprocess.run(
                ["/usr/bin/tar", "--create", "--gzip", "--file", str(evidence), "--files-from", "/dev/null"],
                stderr=subprocess.PIPE,
                check=True,
            )
        manifest = {
            "schema_version": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "database_container": "plc-generation-postgres",
            "data_root": str(data_root),
            "sha256": {
                "database.dump": sha256(partial / "database.dump"),
                "evidence.tar.gz": sha256(evidence),
            },
        }
        (partial / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        os.chmod(partial / "manifest.json", 0o600)
        verify_backup(partial)
        partial.replace(complete)
    except BaseException:
        shutil.rmtree(partial, ignore_errors=True)
        raise

    cutoff = datetime.now(timezone.utc).timestamp() - retention_days * 86400
    for item in backup_root.iterdir():
        if item == complete or not item.is_dir() or item.name.startswith("."):
            continue
        if item.stat().st_mtime < cutoff and (item / "manifest.json").is_file():
            shutil.rmtree(item)
    return complete


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=Path("/opt/plc-generation/data"))
    parser.add_argument("--backup-root", type=Path, default=Path("/opt/plc-generation/backups"))
    parser.add_argument("--retention-days", type=int, default=14)
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.verify:
        manifest = verify_backup(args.verify.resolve())
        print(json.dumps({"status": "pass", "created_at": manifest["created_at"]}))
        return 0
    if not 1 <= args.retention_days <= 365:
        parser.error("--retention-days must be in 1..365")
    result = create_backup(args.data_root.resolve(), args.backup_root.resolve(), args.retention_days)
    print(json.dumps({"status": "pass", "backup": str(result)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

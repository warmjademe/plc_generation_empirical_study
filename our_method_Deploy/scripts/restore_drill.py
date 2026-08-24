#!/usr/bin/env python3
"""Restore one verified backup into an isolated database and evidence directory."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import uuid
from pathlib import Path

from backup_production import verify_backup


def run(*command: str, capture: bool = False) -> str:
    completed = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        check=True,
    )
    return completed.stdout.strip() if capture else ""


def restore_drill(backup: Path, work_root: Path) -> dict:
    manifest = verify_backup(backup)
    suffix = uuid.uuid4().hex[:10]
    database = f"plc_restore_drill_{suffix}"
    container_dump = str(Path(tempfile.gettempdir()) / f"{database}.dump")
    extracted_jobs = 0
    try:
        run(
            "/usr/bin/docker", "exec", "plc-generation-postgres",
            "createdb", "-U", "plc_generation", database,
        )
        run(
            "/usr/bin/docker", "cp", str(backup / "database.dump"),
            f"plc-generation-postgres:{container_dump}",
        )
        run(
            "/usr/bin/docker", "exec", "plc-generation-postgres",
            "pg_restore", "-U", "plc_generation", "-d", database, container_dump,
        )
        job_count = int(run(
            "/usr/bin/docker", "exec", "plc-generation-postgres",
            "psql", "-U", "plc_generation", "-d", database,
            "-Atc", "SELECT COUNT(*) FROM plc_jobs", capture=True,
        ))
        with tempfile.TemporaryDirectory(prefix="plc-restore-drill-", dir=work_root) as temporary:
            destination = Path(temporary)
            run(
                "/usr/bin/tar", "--extract", "--gzip",
                "--file", str(backup / "evidence.tar.gz"),
                "--directory", str(destination),
            )
            jobs = destination / "jobs"
            extracted_jobs = sum(1 for item in jobs.iterdir() if item.is_dir()) if jobs.is_dir() else 0
        if job_count and extracted_jobs == 0:
            raise RuntimeError("database restored jobs but evidence archive contained no job directories")
        return {
            "status": "pass",
            "backup_created_at": manifest["created_at"],
            "database_jobs": job_count,
            "evidence_job_directories": extracted_jobs,
        }
    finally:
        run(
            "/usr/bin/docker", "exec", "plc-generation-postgres",
            "rm", "-f", container_dump,
        )
        subprocess.run(
            [
                "/usr/bin/docker", "exec", "plc-generation-postgres",
                "dropdb", "-U", "plc_generation", "--if-exists", database,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backup", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, default=Path("/opt/plc-generation/data/release-tests"))
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    args.work_root.mkdir(parents=True, exist_ok=True)
    result = restore_drill(args.backup.resolve(), args.work_root.resolve())
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Fail a deployment guard when in-process PLC jobs are still active."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from plc_deploy.settings import Settings
from plc_deploy.store_factory import create_job_store


ACTIVE_STATUSES = (
    "contract_queued",
    "contract_generating",
    "awaiting_contract_approval",
    "generation_queued",
    "generating",
    "cancelling",
)


def active_jobs(database: Path) -> list[dict[str, str]]:
    if not database.is_file():
        return []
    placeholders = ",".join("?" for _ in ACTIVE_STATUSES)
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            f"SELECT id, status, created_at, updated_at FROM jobs "
            f"WHERE status IN ({placeholders}) ORDER BY created_at",
            ACTIVE_STATUSES,
        ).fetchall()
    return [dict(row) for row in rows]


def active_jobs_from_config() -> list[dict[str, str]]:
    settings = Settings.load()
    store = create_job_store(settings.data_root, settings.database_url)
    jobs, _ = store.list_history(
        page=1,
        page_size=settings.max_active_jobs,
        statuses=ACTIVE_STATUSES,
        archive_scope="all",
    )
    return [
        {
            "id": str(job["id"]),
            "status": str(job["status"]),
            "created_at": str(job["created_at"]),
            "updated_at": str(job["updated_at"]),
        }
        for job in jobs
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=None,
        help="explicit legacy SQLite path; omit to inspect the configured production store",
    )
    args = parser.parse_args()
    jobs = active_jobs(args.database) if args.database is not None else active_jobs_from_config()
    print(json.dumps({"safe_to_restart": not jobs, "active_jobs": jobs}, ensure_ascii=False))
    return 0 if not jobs else 3


if __name__ == "__main__":
    raise SystemExit(main())

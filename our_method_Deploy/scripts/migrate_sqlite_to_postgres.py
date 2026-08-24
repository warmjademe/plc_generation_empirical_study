#!/usr/bin/env python3
"""One-way, idempotent migration of PLC jobs from SQLite to PostgreSQL."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

from psycopg.types.json import Jsonb

METHOD_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = METHOD_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from plc_deploy.postgres_store import PostgresJobStore  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sqlite", required=True)
    parser.add_argument("--database-url", default=os.getenv("PLC_DATABASE_URL"))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.database_url:
        parser.error("--database-url or PLC_DATABASE_URL is required")
    source = Path(args.sqlite).resolve()
    with sqlite3.connect(source) as sqlite_db:
        sqlite_db.row_factory = sqlite3.Row
        jobs = [dict(row) for row in sqlite_db.execute("SELECT * FROM jobs ORDER BY created_at")]
        keys = [dict(row) for row in sqlite_db.execute("SELECT * FROM submission_keys")]
    print(json.dumps({"jobs": len(jobs), "submission_keys": len(keys), "apply": args.apply}))
    if not args.apply:
        return 0
    target = PostgresJobStore(args.database_url)
    with target._connect() as db, db.cursor() as cursor:
        for row in jobs:
            cursor.execute(
                "INSERT INTO plc_jobs (id,status,created_at,updated_at,request_json,"
                "contract_json,result_json,final_program,last_error,cancel_requested,cancel_reason) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING",
                (
                    row["id"], row["status"], row["created_at"], row["updated_at"],
                    Jsonb(json.loads(row["request_json"])),
                    Jsonb(json.loads(row["contract_json"])) if row.get("contract_json") else None,
                    Jsonb(json.loads(row["result_json"])) if row.get("result_json") else None,
                    row.get("final_program"), row.get("last_error"),
                    bool(row.get("cancel_requested", 0)), row.get("cancel_reason"),
                ),
            )
        for row in keys:
            cursor.execute(
                "INSERT INTO plc_submission_keys "
                "(idempotency_key,request_fingerprint,job_id,created_at) VALUES (%s,%s,%s,%s) "
                "ON CONFLICT (idempotency_key) DO NOTHING",
                (row["idempotency_key"], row["request_fingerprint"], row["job_id"], row["created_at"]),
            )
    print(json.dumps({"status": "migration_complete", "jobs": len(jobs)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

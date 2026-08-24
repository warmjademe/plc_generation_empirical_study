"""PostgreSQL implementation of the production job store.

The API mirrors :class:`plc_deploy.store.JobStore`.  PostgreSQL advisory locks
make capacity and idempotency decisions atomic across Web/worker processes.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
except ImportError as exc:  # pragma: no cover - exercised by deployment preflight
    raise RuntimeError("PostgreSQL storage requires psycopg[binary]") from exc


def now() -> datetime:
    return datetime.now(timezone.utc)


TERMINAL_STATUSES = (
    "verified_success",
    "generation_failed",
    "infrastructure_error",
    "contract_failed",
    "cancelled",
)


class PostgresJobStore:
    def __init__(self, database_url: str):
        self.database_url = database_url
        with self._connect() as db:
            with db.cursor() as cursor:
                # Web and background-worker processes can start at the same
                # time.  Serialize all idempotent DDL so concurrent ALTER
                # TABLE statements cannot deadlock during a service restart.
                cursor.execute(
                    "SELECT pg_advisory_xact_lock("
                    "hashtext('plc_job_schema_migration'))"
                )
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS plc_jobs (
                        id TEXT PRIMARY KEY,
                        status TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL,
                        request_json JSONB NOT NULL,
                        contract_json JSONB,
                        result_json JSONB,
                        final_program TEXT,
                        last_error TEXT,
                        cancel_requested BOOLEAN NOT NULL DEFAULT FALSE,
                        cancel_reason TEXT,
                        lease_owner TEXT,
                        lease_until TIMESTAMPTZ
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS plc_submission_keys (
                        idempotency_key TEXT PRIMARY KEY,
                        request_fingerprint TEXT NOT NULL,
                        job_id TEXT NOT NULL UNIQUE REFERENCES plc_jobs(id) ON DELETE CASCADE,
                        created_at TIMESTAMPTZ NOT NULL
                    )
                """)
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS plc_jobs_status_idx ON plc_jobs(status)"
                )
                cursor.execute("ALTER TABLE plc_jobs ADD COLUMN IF NOT EXISTS lease_owner TEXT")
                cursor.execute("ALTER TABLE plc_jobs ADD COLUMN IF NOT EXISTS lease_until TIMESTAMPTZ")
                cursor.execute("ALTER TABLE plc_jobs ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS plc_jobs_created_at_idx "
                    "ON plc_jobs(created_at DESC)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS plc_jobs_archived_at_idx "
                    "ON plc_jobs(archived_at)"
                )

    def _connect(self):
        return psycopg.connect(self.database_url, row_factory=dict_row, connect_timeout=10)

    @staticmethod
    def _view(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["id"]),
            "status": str(row["status"]),
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat(),
            "request": dict(row["request_json"]),
            "contract": dict(row["contract_json"]) if row.get("contract_json") else None,
            "result": dict(row["result_json"]) if row.get("result_json") else None,
            "final_program": row.get("final_program"),
            "last_error": row.get("last_error"),
            "cancel_requested": bool(row.get("cancel_requested", False)),
            "cancel_reason": row.get("cancel_reason"),
            "archived_at": (
                row["archived_at"].isoformat() if row.get("archived_at") else None
            ),
        }

    def create(self, job_id: str, request: dict[str, Any]) -> dict[str, Any]:
        timestamp = now()
        with self._connect() as db, db.cursor() as cursor:
            cursor.execute(
                "INSERT INTO plc_jobs (id,status,created_at,updated_at,request_json) "
                "VALUES (%s,'contract_queued',%s,%s,%s)",
                (job_id, timestamp, timestamp, Jsonb(request)),
            )
        return self.get(job_id)

    def create_if_capacity(
        self,
        job_id: str,
        request: dict[str, Any],
        active_statuses: tuple[str, ...],
        limit: int,
        *,
        idempotency_key: str | None = None,
        request_fingerprint: str | None = None,
    ) -> tuple[dict[str, Any], bool] | None:
        if not active_statuses or limit < 1:
            raise ValueError("active_statuses and a positive limit are required")
        timestamp = now()
        with self._connect() as db, db.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtext('plc_job_capacity'))")
            if idempotency_key is not None:
                if not request_fingerprint:
                    raise ValueError("request_fingerprint is required with idempotency_key")
                cursor.execute(
                    "SELECT request_fingerprint,job_id FROM plc_submission_keys "
                    "WHERE idempotency_key=%s",
                    (idempotency_key,),
                )
                existing = cursor.fetchone()
                if existing is not None:
                    if existing["request_fingerprint"] != request_fingerprint:
                        raise ValueError("idempotency key was already used for another request")
                    existing_id = str(existing["job_id"])
                    db.rollback()
                    return self.get(existing_id), False
            cursor.execute(
                "SELECT COUNT(*) AS count FROM plc_jobs WHERE status = ANY(%s)",
                (list(active_statuses),),
            )
            if int(cursor.fetchone()["count"]) >= limit:
                db.rollback()
                return None
            cursor.execute(
                "INSERT INTO plc_jobs (id,status,created_at,updated_at,request_json) "
                "VALUES (%s,'contract_queued',%s,%s,%s)",
                (job_id, timestamp, timestamp, Jsonb(request)),
            )
            if idempotency_key is not None:
                cursor.execute(
                    "INSERT INTO plc_submission_keys "
                    "(idempotency_key,request_fingerprint,job_id,created_at) VALUES (%s,%s,%s,%s)",
                    (idempotency_key, request_fingerprint, job_id, timestamp),
                )
        return self.get(job_id), True

    def get_by_idempotency(
        self, idempotency_key: str, request_fingerprint: str
    ) -> dict[str, Any] | None:
        with self._connect() as db, db.cursor() as cursor:
            cursor.execute(
                "SELECT request_fingerprint,job_id FROM plc_submission_keys WHERE idempotency_key=%s",
                (idempotency_key,),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        if row["request_fingerprint"] != request_fingerprint:
            raise ValueError("idempotency key was already used for another request")
        return self.get(str(row["job_id"]))

    def count_statuses(self, statuses: tuple[str, ...]) -> int:
        if not statuses:
            return 0
        with self._connect() as db, db.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS count FROM plc_jobs WHERE status = ANY(%s)",
                (list(statuses),),
            )
            return int(cursor.fetchone()["count"])

    def update(
        self, job_id: str, *, status: str | None = None, contract: dict | None = None,
        result: dict | None = None, final_program: str | None = None,
        last_error: str | None = None,
    ) -> dict[str, Any]:
        assignments = ["updated_at=%s"]
        values: list[Any] = [now()]
        for column, value in (
            ("status", status),
            ("contract_json", Jsonb(contract) if contract is not None else None),
            ("result_json", Jsonb(result) if result is not None else None),
            ("final_program", final_program),
            ("last_error", last_error),
        ):
            if value is not None:
                assignments.append(f"{column}=%s")
                values.append(value)
        values.append(job_id)
        with self._connect() as db, db.cursor() as cursor:
            cursor.execute(
                f"UPDATE plc_jobs SET {', '.join(assignments)} WHERE id=%s", values
            )
            if cursor.rowcount != 1:
                raise KeyError(job_id)
        return self.get(job_id)

    def transition_status(
        self, job_id: str, expected_status: str, status: str,
        *, contract: dict | None = None,
    ) -> dict[str, Any] | None:
        assignments = ["updated_at=%s", "status=%s"]
        values: list[Any] = [now(), status]
        if contract is not None:
            assignments.append("contract_json=%s")
            values.append(Jsonb(contract))
        values.extend([job_id, expected_status])
        with self._connect() as db, db.cursor() as cursor:
            cursor.execute(
                f"UPDATE plc_jobs SET {', '.join(assignments)} WHERE id=%s AND status=%s",
                values,
            )
            changed = cursor.rowcount == 1
        return self.get(job_id) if changed else None

    def get(self, job_id: str) -> dict[str, Any]:
        with self._connect() as db, db.cursor() as cursor:
            cursor.execute("SELECT * FROM plc_jobs WHERE id=%s", (job_id,))
            row = cursor.fetchone()
        if row is None:
            raise KeyError(job_id)
        return self._view(row)

    def list_history(
        self,
        *,
        page: int,
        page_size: int,
        statuses: tuple[str, ...] = (),
        plc_model: str | None = None,
        output_language: str | None = None,
        llm_model: str | None = None,
        search: str | None = None,
        created_from: str | None = None,
        created_to: str | None = None,
        archive_scope: str = "active",
    ) -> tuple[list[dict[str, Any]], int]:
        clauses: list[str] = []
        values: list[Any] = []
        if archive_scope == "active":
            clauses.append("archived_at IS NULL")
        elif archive_scope == "archived":
            clauses.append("archived_at IS NOT NULL")
        if statuses:
            clauses.append("status = ANY(%s)")
            values.append(list(statuses))
        for key, value in (
            ("plc_model", plc_model),
            ("output_language", output_language),
            ("llm_model", llm_model),
        ):
            if value:
                clauses.append(f"request_json->>'{key}' = %s")
                values.append(value)
        if search:
            clauses.append(
                "(id || ' ' || request_json::text || ' ' || "
                "COALESCE(final_program,'') || ' ' || COALESCE(last_error,'')) ILIKE %s"
            )
            values.append(f"%{search}%")
        if created_from:
            clauses.append("created_at >= %s")
            values.append(datetime.fromisoformat(created_from))
        if created_to:
            clauses.append("created_at < %s")
            values.append(datetime.fromisoformat(created_to))
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        offset = (page - 1) * page_size
        with self._connect() as db, db.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) AS count FROM plc_jobs{where}", values)
            total = int(cursor.fetchone()["count"])
            cursor.execute(
                "SELECT id,status,created_at,updated_at,request_json,archived_at "
                f"FROM plc_jobs{where} ORDER BY created_at DESC,id DESC LIMIT %s OFFSET %s",
                (*values, page_size, offset),
            )
            rows = cursor.fetchall()
        return [
            {
                "id": str(row["id"]),
                "status": str(row["status"]),
                "created_at": row["created_at"].isoformat(),
                "updated_at": row["updated_at"].isoformat(),
                "request": dict(row["request_json"]),
                "archived_at": (
                    row["archived_at"].isoformat() if row.get("archived_at") else None
                ),
            }
            for row in rows
        ], total

    def archive_job(self, job_id: str) -> dict[str, Any]:
        with self._connect() as db, db.cursor() as cursor:
            cursor.execute(
                "UPDATE plc_jobs SET archived_at=%s,updated_at=%s WHERE id=%s "
                "AND archived_at IS NULL AND status = ANY(%s)",
                (now(), now(), job_id, list(TERMINAL_STATUSES)),
            )
            if cursor.rowcount != 1:
                cursor.execute("SELECT status FROM plc_jobs WHERE id=%s", (job_id,))
                row = cursor.fetchone()
                if row is None:
                    raise KeyError(job_id)
                if str(row["status"]) not in TERMINAL_STATUSES:
                    raise ValueError("active jobs cannot be archived")
        return self.get(job_id)

    def restore_job(self, job_id: str) -> dict[str, Any]:
        with self._connect() as db, db.cursor() as cursor:
            cursor.execute(
                "UPDATE plc_jobs SET archived_at=NULL,updated_at=%s WHERE id=%s",
                (now(), job_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(job_id)
        return self.get(job_id)

    def archive_expired(self, cutoff: str) -> int:
        with self._connect() as db, db.cursor() as cursor:
            cursor.execute(
                "UPDATE plc_jobs SET archived_at=%s,updated_at=%s WHERE archived_at IS NULL "
                "AND created_at < %s AND status = ANY(%s)",
                (now(), now(), cutoff, list(TERMINAL_STATUSES)),
            )
            return int(cursor.rowcount)

    def delete_job(self, job_id: str) -> None:
        with self._connect() as db, db.cursor() as cursor:
            cursor.execute("SELECT status FROM plc_jobs WHERE id=%s FOR UPDATE", (job_id,))
            row = cursor.fetchone()
            if row is None:
                raise KeyError(job_id)
            if str(row["status"]) not in TERMINAL_STATUSES:
                raise ValueError("active jobs cannot be deleted")
            cursor.execute("DELETE FROM plc_jobs WHERE id=%s", (job_id,))

    def request_cancel(self, job_id: str, reason: str) -> dict[str, Any]:
        terminal = {
            "verified_success", "generation_failed", "infrastructure_error",
            "contract_failed", "cancelled",
        }
        immediate = {"contract_queued", "awaiting_contract_approval", "generation_queued"}
        with self._connect() as db, db.cursor() as cursor:
            cursor.execute("SELECT status FROM plc_jobs WHERE id=%s FOR UPDATE", (job_id,))
            row = cursor.fetchone()
            if row is None:
                raise KeyError(job_id)
            current = str(row["status"])
            if current not in terminal:
                next_status = "cancelled" if current in immediate else "cancelling"
                cursor.execute(
                    "UPDATE plc_jobs SET status=%s,updated_at=%s,cancel_requested=TRUE,"
                    "cancel_reason=%s,last_error=%s WHERE id=%s",
                    (next_status, now(), reason, reason, job_id),
                )
        return self.get(job_id)

    def cancellation_requested(self, job_id: str) -> bool:
        with self._connect() as db, db.cursor() as cursor:
            cursor.execute("SELECT cancel_requested FROM plc_jobs WHERE id=%s", (job_id,))
            row = cursor.fetchone()
        if row is None:
            raise KeyError(job_id)
        return bool(row["cancel_requested"])

    def claim_job(
        self, job_id: str, stage: str, owner: str, lease_seconds: int
    ) -> dict[str, Any] | None:
        queued, running = (
            ("contract_queued", "contract_generating")
            if stage == "contract"
            else ("generation_queued", "generating")
        )
        lease_until = now() + timedelta(seconds=lease_seconds)
        with self._connect() as db, db.cursor() as cursor:
            cursor.execute(
                "SELECT status,lease_until,cancel_requested FROM plc_jobs WHERE id=%s FOR UPDATE",
                (job_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise KeyError(job_id)
            expired = row["lease_until"] is None or row["lease_until"] <= now()
            if bool(row["cancel_requested"]) or not (
                row["status"] == queued or (row["status"] == running and expired)
            ):
                return None
            cursor.execute(
                "UPDATE plc_jobs SET status=%s,updated_at=%s,lease_owner=%s,lease_until=%s WHERE id=%s",
                (running, now(), owner, lease_until, job_id),
            )
        return self.get(job_id)

    def renew_lease(self, job_id: str, owner: str, lease_seconds: int) -> bool:
        with self._connect() as db, db.cursor() as cursor:
            cursor.execute(
                "UPDATE plc_jobs SET lease_until=%s WHERE id=%s AND lease_owner=%s",
                (now() + timedelta(seconds=lease_seconds), job_id, owner),
            )
            return cursor.rowcount == 1

    def release_lease(self, job_id: str, owner: str) -> None:
        with self._connect() as db, db.cursor() as cursor:
            cursor.execute(
                "UPDATE plc_jobs SET lease_owner=NULL,lease_until=NULL WHERE id=%s AND lease_owner=%s",
                (job_id, owner),
            )

    def dispatchable_jobs(self, limit: int = 64) -> list[tuple[str, str]]:
        with self._connect() as db, db.cursor() as cursor:
            cursor.execute(
                "SELECT id,status FROM plc_jobs WHERE cancel_requested=FALSE AND ("
                "status IN ('contract_queued','generation_queued') OR "
                "(status IN ('contract_generating','generating') AND "
                "(lease_until IS NULL OR lease_until<=%s))) ORDER BY created_at LIMIT %s",
                (now(), max(1, limit)),
            )
            rows = cursor.fetchall()
        return [
            (str(row["id"]), "contract" if str(row["status"]).startswith("contract_") else "generation")
            for row in rows
        ]

    def auto_approvable_jobs(self, delay_seconds: float, limit: int = 64) -> list[str]:
        cutoff = now() - timedelta(seconds=delay_seconds)
        with self._connect() as db, db.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM plc_jobs WHERE status='awaiting_contract_approval' "
                "AND cancel_requested=FALSE AND updated_at<=%s ORDER BY updated_at LIMIT %s",
                (cutoff, max(1, limit)),
            )
            return [str(row["id"]) for row in cursor.fetchall()]

    def finalize_abandoned_cancellations(self) -> list[str]:
        with self._connect() as db, db.cursor() as cursor:
            cursor.execute(
                "UPDATE plc_jobs SET status='cancelled',updated_at=%s,lease_owner=NULL,"
                "lease_until=NULL WHERE status='cancelling' AND "
                "(lease_until IS NULL OR lease_until<=%s) RETURNING id",
                (now(), now()),
            )
            return [str(row["id"]) for row in cursor.fetchall()]

    def recover_interrupted(self) -> dict[str, list[str]]:
        recovered = {"contract": [], "approval": [], "generation": [], "cancelled": []}
        with self._connect() as db, db.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtext('plc_job_recovery'))")
            cursor.execute(
                "SELECT id,status,cancel_requested FROM plc_jobs WHERE status = ANY(%s) FOR UPDATE",
                (["contract_queued", "contract_generating", "awaiting_contract_approval",
                  "generation_queued", "generating", "cancelling"],),
            )
            for row in cursor.fetchall():
                job_id, status = str(row["id"]), str(row["status"])
                if bool(row["cancel_requested"]) or status == "cancelling":
                    next_status, group = "cancelled", "cancelled"
                elif status in {"contract_queued", "contract_generating"}:
                    next_status, group = "contract_queued", "contract"
                elif status == "awaiting_contract_approval":
                    recovered["approval"].append(job_id)
                    continue
                else:
                    next_status, group = "generation_queued", "generation"
                cursor.execute(
                    "UPDATE plc_jobs SET status=%s,updated_at=%s WHERE id=%s",
                    (next_status, now(), job_id),
                )
                recovered[group].append(job_id)
        return recovered

    def mark_interrupted(self, statuses: tuple[str, ...], message: str) -> list[str]:
        with self._connect() as db, db.cursor() as cursor:
            cursor.execute(
                "UPDATE plc_jobs SET status='infrastructure_error',updated_at=%s,last_error=%s "
                "WHERE status = ANY(%s) RETURNING id",
                (now(), message, list(statuses)),
            )
            return [str(row["id"]) for row in cursor.fetchall()]

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


TERMINAL_STATUSES = (
    "verified_success",
    "generation_failed",
    "infrastructure_error",
    "contract_failed",
    "cancelled",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobStore:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._lock = threading.RLock()
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute(
                """CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    contract_json TEXT,
                    result_json TEXT,
                    final_program TEXT,
                    last_error TEXT
                )"""
            )
            columns = {
                str(row[1]) for row in db.execute("PRAGMA table_info(jobs)").fetchall()
            }
            if "cancel_requested" not in columns:
                db.execute(
                    "ALTER TABLE jobs ADD COLUMN cancel_requested INTEGER NOT NULL DEFAULT 0"
                )
            if "cancel_reason" not in columns:
                db.execute("ALTER TABLE jobs ADD COLUMN cancel_reason TEXT")
            if "lease_owner" not in columns:
                db.execute("ALTER TABLE jobs ADD COLUMN lease_owner TEXT")
            if "lease_until" not in columns:
                db.execute("ALTER TABLE jobs ADD COLUMN lease_until TEXT")
            if "archived_at" not in columns:
                db.execute("ALTER TABLE jobs ADD COLUMN archived_at TEXT")
            db.execute(
                "CREATE INDEX IF NOT EXISTS jobs_created_at_idx ON jobs(created_at DESC)"
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS jobs_archived_at_idx ON jobs(archived_at)"
            )
            db.execute(
                """CREATE TABLE IF NOT EXISTS submission_keys (
                    idempotency_key TEXT PRIMARY KEY,
                    request_fingerprint TEXT NOT NULL,
                    job_id TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(job_id) REFERENCES jobs(id)
                )"""
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    def create(self, job_id: str, request: dict[str, Any]) -> dict[str, Any]:
        timestamp = now_iso()
        with self._lock, self._connect() as db:
            db.execute(
                "INSERT INTO jobs "
                "(id, status, created_at, updated_at, request_json, contract_json, "
                "result_json, final_program, last_error, cancel_requested, cancel_reason) "
                "VALUES (?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, 0, NULL)",
                (job_id, "contract_queued", timestamp, timestamp, json.dumps(request, ensure_ascii=False)),
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
        """Atomically claim capacity and return ``(job, created)``.

        An idempotent replay returns the original job with ``created=False`` so
        callers do not dispatch the same background work a second time.
        """
        if not active_statuses or limit < 1:
            raise ValueError("active_statuses and a positive limit are required")
        timestamp = now_iso()
        placeholders = ",".join("?" for _ in active_statuses)
        with self._lock, self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if idempotency_key is not None:
                if not request_fingerprint:
                    raise ValueError("request_fingerprint is required with idempotency_key")
                existing = db.execute(
                    "SELECT request_fingerprint, job_id FROM submission_keys "
                    "WHERE idempotency_key = ?",
                    (idempotency_key,),
                ).fetchone()
                if existing is not None:
                    if existing["request_fingerprint"] != request_fingerprint:
                        db.rollback()
                        raise ValueError("idempotency key was already used for another request")
                    existing_job_id = str(existing["job_id"])
                    db.rollback()
                    return self.get(existing_job_id), False
            active = int(db.execute(
                f"SELECT COUNT(*) FROM jobs WHERE status IN ({placeholders})",
                active_statuses,
            ).fetchone()[0])
            if active >= limit:
                db.rollback()
                return None
            db.execute(
                "INSERT INTO jobs "
                "(id, status, created_at, updated_at, request_json, contract_json, "
                "result_json, final_program, last_error, cancel_requested, cancel_reason) "
                "VALUES (?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, 0, NULL)",
                (job_id, "contract_queued", timestamp, timestamp,
                 json.dumps(request, ensure_ascii=False)),
            )
            if idempotency_key is not None:
                db.execute(
                    "INSERT INTO submission_keys VALUES (?, ?, ?, ?)",
                    (idempotency_key, request_fingerprint, job_id, timestamp),
                )
        return self.get(job_id), True

    def get_by_idempotency(
        self, idempotency_key: str, request_fingerprint: str
    ) -> dict[str, Any] | None:
        """Return the prior job for an identical retry, rejecting key reuse."""

        with self._connect() as db:
            row = db.execute(
                "SELECT request_fingerprint, job_id FROM submission_keys "
                "WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
        if row is None:
            return None
        if row["request_fingerprint"] != request_fingerprint:
            raise ValueError("idempotency key was already used for another request")
        return self.get(str(row["job_id"]))

    def count_statuses(self, statuses: tuple[str, ...]) -> int:
        if not statuses:
            return 0
        placeholders = ",".join("?" for _ in statuses)
        with self._connect() as db:
            return int(db.execute(
                f"SELECT COUNT(*) FROM jobs WHERE status IN ({placeholders})", statuses
            ).fetchone()[0])

    def update(self, job_id: str, *, status: str | None = None, contract: dict | None = None,
               result: dict | None = None, final_program: str | None = None,
               last_error: str | None = None) -> dict[str, Any]:
        fields: list[str] = ["updated_at = ?"]
        values: list[Any] = [now_iso()]
        for column, value in (
            ("status", status),
            ("contract_json", json.dumps(contract, ensure_ascii=False) if contract is not None else None),
            ("result_json", json.dumps(result, ensure_ascii=False) if result is not None else None),
            ("final_program", final_program),
            ("last_error", last_error),
        ):
            if value is not None:
                fields.append(f"{column} = ?")
                values.append(value)
        values.append(job_id)
        with self._lock, self._connect() as db:
            cursor = db.execute(f"UPDATE jobs SET {', '.join(fields)} WHERE id = ?", values)
            if cursor.rowcount != 1:
                raise KeyError(job_id)
        return self.get(job_id)

    def transition_status(self, job_id: str, expected_status: str, status: str,
                          *, contract: dict | None = None) -> dict[str, Any] | None:
        """Atomically claim one lifecycle transition; return None when another caller won."""
        timestamp = now_iso()
        fields = ["updated_at = ?", "status = ?"]
        values: list[Any] = [timestamp, status]
        if contract is not None:
            fields.append("contract_json = ?")
            values.append(json.dumps(contract, ensure_ascii=False))
        values.extend([job_id, expected_status])
        with self._lock, self._connect() as db:
            cursor = db.execute(
                f"UPDATE jobs SET {', '.join(fields)} WHERE id = ? AND status = ?", values
            )
        return self.get(job_id) if cursor.rowcount == 1 else None

    def request_cancel(self, job_id: str, reason: str) -> dict[str, Any]:
        """Persist cancellation before signalling an in-process worker."""

        terminal = {
            "verified_success", "generation_failed", "infrastructure_error",
            "contract_failed", "cancelled",
        }
        immediate = {"contract_queued", "awaiting_contract_approval", "generation_queued"}
        timestamp = now_iso()
        with self._lock, self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT status FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if row is None:
                db.rollback()
                raise KeyError(job_id)
            current = str(row["status"])
            if current not in terminal:
                next_status = "cancelled" if current in immediate else "cancelling"
                db.execute(
                    "UPDATE jobs SET status = ?, updated_at = ?, cancel_requested = 1, "
                    "cancel_reason = ?, last_error = ? WHERE id = ?",
                    (next_status, timestamp, reason, reason, job_id),
                )
        return self.get(job_id)

    def cancellation_requested(self, job_id: str) -> bool:
        with self._connect() as db:
            row = db.execute(
                "SELECT cancel_requested FROM jobs WHERE id = ?", (job_id,)
            ).fetchone()
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
        timestamp = now_iso()
        lease_until = (datetime.now(timezone.utc) + timedelta(seconds=lease_seconds)).isoformat()
        with self._lock, self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT status,lease_until,cancel_requested FROM jobs WHERE id=?",
                (job_id,),
            ).fetchone()
            if row is None:
                db.rollback()
                raise KeyError(job_id)
            expired = not row["lease_until"] or str(row["lease_until"]) <= timestamp
            if bool(row["cancel_requested"]) or not (
                row["status"] == queued or (row["status"] == running and expired)
            ):
                db.rollback()
                return None
            db.execute(
                "UPDATE jobs SET status=?,updated_at=?,lease_owner=?,lease_until=? WHERE id=?",
                (running, timestamp, owner, lease_until, job_id),
            )
        return self.get(job_id)

    def renew_lease(self, job_id: str, owner: str, lease_seconds: int) -> bool:
        lease_until = (datetime.now(timezone.utc) + timedelta(seconds=lease_seconds)).isoformat()
        with self._lock, self._connect() as db:
            cursor = db.execute(
                "UPDATE jobs SET lease_until=? WHERE id=? AND lease_owner=?",
                (lease_until, job_id, owner),
            )
        return cursor.rowcount == 1

    def release_lease(self, job_id: str, owner: str) -> None:
        with self._lock, self._connect() as db:
            db.execute(
                "UPDATE jobs SET lease_owner=NULL,lease_until=NULL WHERE id=? AND lease_owner=?",
                (job_id, owner),
            )

    def dispatchable_jobs(self, limit: int = 64) -> list[tuple[str, str]]:
        timestamp = now_iso()
        with self._connect() as db:
            rows = db.execute(
                "SELECT id,status FROM jobs WHERE cancel_requested=0 AND ("
                "status IN ('contract_queued','generation_queued') OR "
                "(status IN ('contract_generating','generating') AND "
                "(lease_until IS NULL OR lease_until<=?))) ORDER BY created_at LIMIT ?",
                (timestamp, max(1, limit)),
            ).fetchall()
        return [
            (str(row["id"]), "contract" if str(row["status"]).startswith("contract_") else "generation")
            for row in rows
        ]

    def auto_approvable_jobs(self, delay_seconds: float, limit: int = 64) -> list[str]:
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=delay_seconds)).isoformat()
        with self._connect() as db:
            rows = db.execute(
                "SELECT id FROM jobs WHERE status='awaiting_contract_approval' "
                "AND cancel_requested=0 AND updated_at<=? ORDER BY updated_at LIMIT ?",
                (cutoff, max(1, limit)),
            ).fetchall()
        return [str(row["id"]) for row in rows]

    def finalize_abandoned_cancellations(self) -> list[str]:
        timestamp = now_iso()
        with self._lock, self._connect() as db:
            rows = db.execute(
                "SELECT id FROM jobs WHERE status='cancelling' AND "
                "(lease_until IS NULL OR lease_until<=?)",
                (timestamp,),
            ).fetchall()
            job_ids = [str(row["id"]) for row in rows]
            if job_ids:
                placeholders = ",".join("?" for _ in job_ids)
                db.execute(
                    f"UPDATE jobs SET status='cancelled',updated_at=?,lease_owner=NULL,"
                    f"lease_until=NULL WHERE id IN ({placeholders})",
                    (timestamp, *job_ids),
                )
        return job_ids

    def get(self, job_id: str) -> dict[str, Any]:
        with self._connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            raise KeyError(job_id)
        value = dict(row)
        return {
            "id": value["id"],
            "status": value["status"],
            "created_at": value["created_at"],
            "updated_at": value["updated_at"],
            "request": json.loads(value["request_json"]),
            "contract": json.loads(value["contract_json"]) if value["contract_json"] else None,
            "result": json.loads(value["result_json"]) if value["result_json"] else None,
            "final_program": value["final_program"],
            "last_error": value["last_error"],
            "cancel_requested": bool(value.get("cancel_requested", 0)),
            "cancel_reason": value.get("cancel_reason"),
            "archived_at": value.get("archived_at"),
        }

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
            placeholders = ",".join("?" for _ in statuses)
            clauses.append(f"status IN ({placeholders})")
            values.extend(statuses)
        for json_key, value in (
            ("plc_model", plc_model),
            ("output_language", output_language),
            ("llm_model", llm_model),
        ):
            if value:
                clauses.append(f"json_extract(request_json, '$.{json_key}') = ?")
                values.append(value)
        if search:
            clauses.append(
                "lower(id || ' ' || request_json || ' ' || "
                "coalesce(final_program,'') || ' ' || coalesce(last_error,'')) LIKE ?"
            )
            values.append(f"%{search.casefold()}%")
        if created_from:
            clauses.append("created_at >= ?")
            values.append(created_from)
        if created_to:
            clauses.append("created_at < ?")
            values.append(created_to)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        offset = (page - 1) * page_size
        with self._connect() as db:
            total = int(
                db.execute(f"SELECT COUNT(*) FROM jobs{where}", values).fetchone()[0]
            )
            rows = db.execute(
                "SELECT id,status,created_at,updated_at,request_json,archived_at "
                f"FROM jobs{where} ORDER BY created_at DESC,id DESC LIMIT ? OFFSET ?",
                (*values, page_size, offset),
            ).fetchall()
        return [
            {
                "id": str(row["id"]),
                "status": str(row["status"]),
                "created_at": str(row["created_at"]),
                "updated_at": str(row["updated_at"]),
                "request": json.loads(row["request_json"]),
                "archived_at": row["archived_at"],
            }
            for row in rows
        ], total

    def archive_job(self, job_id: str) -> dict[str, Any]:
        with self._lock, self._connect() as db:
            cursor = db.execute(
                "UPDATE jobs SET archived_at=?,updated_at=? WHERE id=? "
                "AND archived_at IS NULL AND status IN (?,?,?,?,?)",
                (now_iso(), now_iso(), job_id, *TERMINAL_STATUSES),
            )
            if cursor.rowcount != 1:
                row = db.execute("SELECT status FROM jobs WHERE id=?", (job_id,)).fetchone()
                if row is None:
                    raise KeyError(job_id)
                if str(row["status"]) not in TERMINAL_STATUSES:
                    raise ValueError("active jobs cannot be archived")
        return self.get(job_id)

    def restore_job(self, job_id: str) -> dict[str, Any]:
        with self._lock, self._connect() as db:
            cursor = db.execute(
                "UPDATE jobs SET archived_at=NULL,updated_at=? WHERE id=?",
                (now_iso(), job_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(job_id)
        return self.get(job_id)

    def archive_expired(self, cutoff: str) -> int:
        with self._lock, self._connect() as db:
            cursor = db.execute(
                "UPDATE jobs SET archived_at=?,updated_at=? WHERE archived_at IS NULL "
                "AND created_at < ? AND status IN (?,?,?,?,?)",
                (now_iso(), now_iso(), cutoff, *TERMINAL_STATUSES),
            )
            return int(cursor.rowcount)

    def delete_job(self, job_id: str) -> None:
        with self._lock, self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT status FROM jobs WHERE id=?", (job_id,)).fetchone()
            if row is None:
                db.rollback()
                raise KeyError(job_id)
            if str(row["status"]) not in TERMINAL_STATUSES:
                db.rollback()
                raise ValueError("active jobs cannot be deleted")
            db.execute("DELETE FROM submission_keys WHERE job_id=?", (job_id,))
            db.execute("DELETE FROM jobs WHERE id=?", (job_id,))

    def mark_interrupted(self, statuses: tuple[str, ...], message: str) -> list[str]:
        """Terminate jobs whose in-process worker disappeared during a restart."""

        if not statuses:
            return []
        placeholders = ",".join("?" for _ in statuses)
        timestamp = now_iso()
        with self._lock, self._connect() as db:
            rows = db.execute(
                f"SELECT id FROM jobs WHERE status IN ({placeholders})",
                statuses,
            ).fetchall()
            job_ids = [str(row["id"]) for row in rows]
            if job_ids:
                db.execute(
                    f"UPDATE jobs SET status = ?, updated_at = ?, last_error = ? "
                    f"WHERE status IN ({placeholders})",
                    ("infrastructure_error", timestamp, message, *statuses),
                )
        return job_ids

    def recover_interrupted(self) -> dict[str, list[str]]:
        """Requeue durable stages after a process restart without duplicating finished work."""

        recovered = {"contract": [], "approval": [], "generation": [], "cancelled": []}
        with self._lock, self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute(
                "SELECT id, status, cancel_requested FROM jobs WHERE status IN "
                "('contract_queued','contract_generating','awaiting_contract_approval',"
                "'generation_queued','generating','cancelling')"
            ).fetchall()
            timestamp = now_iso()
            for row in rows:
                job_id = str(row["id"])
                status = str(row["status"])
                if bool(row["cancel_requested"]) or status == "cancelling":
                    db.execute(
                        "UPDATE jobs SET status='cancelled', updated_at=? WHERE id=?",
                        (timestamp, job_id),
                    )
                    recovered["cancelled"].append(job_id)
                elif status in {"contract_queued", "contract_generating"}:
                    db.execute(
                        "UPDATE jobs SET status='contract_queued', updated_at=? WHERE id=?",
                        (timestamp, job_id),
                    )
                    recovered["contract"].append(job_id)
                elif status == "awaiting_contract_approval":
                    recovered["approval"].append(job_id)
                else:
                    db.execute(
                        "UPDATE jobs SET status='generation_queued', updated_at=? WHERE id=?",
                        (timestamp, job_id),
                    )
                    recovered["generation"].append(job_id)
        return recovered

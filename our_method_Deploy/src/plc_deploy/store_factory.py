from __future__ import annotations

from pathlib import Path

from .store import JobStore


def create_job_store(data_root: Path, database_url: str | None):
    if database_url:
        if not database_url.startswith(("postgresql://", "postgresql+psycopg://")):
            raise ValueError("PLC_DATABASE_URL must be a PostgreSQL URL")
        from .postgres_store import PostgresJobStore

        normalized = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
        return PostgresJobStore(normalized)
    return JobStore(data_root / "service.db")

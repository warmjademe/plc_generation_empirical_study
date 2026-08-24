from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    environment: str
    project_root: Path
    data_root: Path
    tool_root: Path
    openplc_image: str
    dvp_spool_root: Path
    dvp_spool_roots: tuple[Path, ...]
    dvp_timeout_seconds: int
    validation_host_public_address: str
    validation_host_public_port: int
    validation_guest_address: str
    validation_guest_port: int
    host: str
    port: int
    web_workers: int
    job_workers: int
    job_lease_seconds: int
    job_poll_seconds: float
    run_background_jobs: bool
    max_active_jobs: int
    job_retention_days: int
    api_token: str | None
    login_username: str
    login_password: str
    allow_test_static_password: bool
    session_secret: str
    session_ttl_seconds: int
    database_url: str | None
    login_max_failures: int
    login_window_seconds: int
    login_lockout_seconds: int
    auth_state_path: Path

    @classmethod
    def load(cls) -> "Settings":
        project_root = Path(
            os.getenv("PLC_PROJECT_ROOT", Path(__file__).resolve().parents[2])
        ).resolve()
        data_root = Path(os.getenv("PLC_DATA_ROOT", project_root / "data")).resolve()
        api_token = os.getenv("PLC_WEB_API_TOKEN") or None
        login_username = os.getenv("PLC_LOGIN_USERNAME", "kemei")
        login_password = os.getenv("PLC_LOGIN_PASSWORD", "kemei")
        web_workers = int(os.getenv("PLC_WORKERS", "1"))
        database_url = os.getenv("PLC_DATABASE_URL") or None
        if web_workers != 1 and not str(database_url or "").startswith(("postgres://", "postgresql://")):
            raise ValueError(
                "PLC_WORKERS may exceed 1 only with PostgreSQL durable leases; "
                "set PLC_DATABASE_URL or keep PLC_WORKERS=1"
            )
        primary_spool = Path(
            os.getenv(
                "PLC_DVP_SPOOL_ROOT",
                "/opt/plc-generation/dvp-bridge/dvp-spool",
            )
        ).resolve()
        configured_spools = os.getenv("PLC_DVP_SPOOL_ROOTS", "").strip()
        spool_roots = tuple(
            Path(item.strip()).resolve()
            for item in configured_spools.split(",")
            if item.strip()
        ) or (primary_spool,)
        value = cls(
            environment=os.getenv("PLC_ENVIRONMENT", "development").strip().casefold(),
            project_root=project_root,
            data_root=data_root,
            tool_root=Path(os.getenv("PLC_TOOL_ROOT", project_root / "tools")).resolve(),
            openplc_image=os.getenv("PLC_OPENPLC_IMAGE", "plc-egbs/openplc-v3:b5d41356"),
            dvp_spool_root=spool_roots[0],
            dvp_spool_roots=spool_roots,
            dvp_timeout_seconds=max(
                300, min(7200, int(os.getenv("PLC_DVP_TIMEOUT_SECONDS", "2400")))
            ),
            validation_host_public_address=os.getenv(
                "PLC_VALIDATION_HOST_PUBLIC_ADDRESS", "58.221.227.30"
            ),
            validation_host_public_port=int(
                os.getenv("PLC_VALIDATION_HOST_PUBLIC_PORT", "60000")
            ),
            validation_guest_address=os.getenv(
                "PLC_VALIDATION_GUEST_ADDRESS", "10.0.2.15"
            ),
            validation_guest_port=int(
                os.getenv("PLC_VALIDATION_GUEST_PORT", "3389")
            ),
            host=os.getenv("PLC_HOST", "127.0.0.1"),
            port=int(os.getenv("PLC_PORT", "18080")),
            web_workers=web_workers,
            job_workers=max(1, min(16, int(os.getenv("PLC_JOB_WORKERS", "4")))),
            job_lease_seconds=max(
                120, min(7200, int(os.getenv("PLC_JOB_LEASE_SECONDS", "300")))
            ),
            job_poll_seconds=max(
                0.25, min(30.0, float(os.getenv("PLC_JOB_POLL_SECONDS", "2")))
            ),
            run_background_jobs=os.getenv(
                "PLC_RUN_BACKGROUND_JOBS", "true"
            ).strip().casefold() in {"1", "true", "yes", "on"},
            max_active_jobs=max(2, min(64, int(os.getenv("PLC_MAX_ACTIVE_JOBS", "8")))),
            job_retention_days=max(
                0, min(3650, int(os.getenv("PLC_JOB_RETENTION_DAYS", "180")))
            ),
            api_token=api_token,
            login_username=login_username,
            login_password=login_password,
            allow_test_static_password=os.getenv(
                "PLC_ALLOW_TEST_STATIC_PASSWORD", "false"
            ).strip().casefold() in {"1", "true", "yes", "on"},
            session_secret=os.getenv("PLC_SESSION_SECRET") or api_token or login_password,
            session_ttl_seconds=max(
                300, min(86400, int(os.getenv("PLC_SESSION_TTL_SECONDS", "43200")))
            ),
            database_url=database_url,
            login_max_failures=max(
                2, min(20, int(os.getenv("PLC_LOGIN_MAX_FAILURES", "5")))
            ),
            login_window_seconds=max(
                60, min(86400, int(os.getenv("PLC_LOGIN_WINDOW_SECONDS", "900")))
            ),
            login_lockout_seconds=max(
                60, min(86400, int(os.getenv("PLC_LOGIN_LOCKOUT_SECONDS", "900")))
            ),
            auth_state_path=Path(
                os.getenv("PLC_AUTH_STATE_PATH", data_root / "auth_failures.json")
            ).resolve(),
        )
        value.validate_for_startup()
        return value

    def validate_for_startup(self) -> None:
        if self.environment not in {"development", "test", "production"}:
            raise ValueError("PLC_ENVIRONMENT must be development, test, or production")
        if self.environment != "production":
            return
        weak_password = (
            self.login_password in {"kemei", "change-me", "password"}
            or len(self.login_password) < 12
        )
        test_password_exception = (
            self.allow_test_static_password and self.login_password == "kemei"
        )
        if weak_password and not test_password_exception:
            raise ValueError("production requires a non-default login password of at least 12 characters")
        if len(self.session_secret) < 32 or self.session_secret in {
            self.login_password, self.api_token
        }:
            raise ValueError("production requires an independent session secret of at least 32 characters")
        if not str(self.database_url or "").startswith(("postgres://", "postgresql://")):
            raise ValueError("production requires PostgreSQL durable storage")
        if self.host not in {"127.0.0.1", "::1", "localhost"}:
            raise ValueError("production Web service must bind to a loopback address behind TLS")

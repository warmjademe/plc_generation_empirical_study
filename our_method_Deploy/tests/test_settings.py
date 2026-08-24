from __future__ import annotations

import pytest

from plc_deploy.settings import Settings


def test_multiple_web_processes_require_postgresql_leases(monkeypatch) -> None:
    monkeypatch.setenv("PLC_WORKERS", "2")
    monkeypatch.delenv("PLC_DATABASE_URL", raising=False)
    with pytest.raises(ValueError, match="only with PostgreSQL durable leases"):
        Settings.load()

    monkeypatch.setenv("PLC_DATABASE_URL", "postgresql://plc:test@127.0.0.1/plc")
    assert Settings.load().web_workers == 2


def test_concurrent_users_use_background_job_workers(monkeypatch) -> None:
    monkeypatch.setenv("PLC_WORKERS", "1")
    monkeypatch.setenv("PLC_JOB_WORKERS", "6")
    settings = Settings.load()
    assert settings.web_workers == 1
    assert settings.job_workers == 6


def test_private_validation_endpoints_have_production_defaults(monkeypatch) -> None:
    for name in (
        "PLC_VALIDATION_HOST_PUBLIC_ADDRESS",
        "PLC_VALIDATION_HOST_PUBLIC_PORT",
        "PLC_VALIDATION_GUEST_ADDRESS",
        "PLC_VALIDATION_GUEST_PORT",
    ):
        monkeypatch.delenv(name, raising=False)
    settings = Settings.load()
    assert (settings.validation_host_public_address, settings.validation_host_public_port) == (
        "58.221.227.30", 60000
    )
    assert (settings.validation_guest_address, settings.validation_guest_port) == (
        "10.0.2.15", 3389
    )


def test_production_rejects_default_password_and_requires_durable_storage(monkeypatch) -> None:
    monkeypatch.setenv("PLC_ENVIRONMENT", "production")
    monkeypatch.setenv("PLC_LOGIN_PASSWORD", "kemei")
    with pytest.raises(ValueError, match="non-default login password"):
        Settings.load()

    monkeypatch.setenv("PLC_LOGIN_PASSWORD", "customer-password-strong")
    monkeypatch.setenv("PLC_SESSION_SECRET", "s" * 64)
    monkeypatch.delenv("PLC_DATABASE_URL", raising=False)
    with pytest.raises(ValueError, match="PostgreSQL"):
        Settings.load()


def test_production_accepts_independent_secrets_and_loopback(monkeypatch) -> None:
    monkeypatch.setenv("PLC_ENVIRONMENT", "production")
    monkeypatch.setenv("PLC_LOGIN_PASSWORD", "customer-password-strong")
    monkeypatch.setenv("PLC_SESSION_SECRET", "s" * 64)
    monkeypatch.setenv("PLC_DATABASE_URL", "postgresql://plc:test@127.0.0.1/plc")
    monkeypatch.setenv("PLC_HOST", "127.0.0.1")
    assert Settings.load().environment == "production"


def test_login_rate_limit_state_uses_writable_data_root(monkeypatch, tmp_path) -> None:
    data_root = tmp_path / "durable-data"
    monkeypatch.setenv("PLC_DATA_ROOT", str(data_root))
    monkeypatch.delenv("PLC_AUTH_STATE_PATH", raising=False)
    settings = Settings.load()
    assert settings.auth_state_path == data_root / "auth_failures.json"

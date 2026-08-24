from __future__ import annotations

import importlib.util
from pathlib import Path

from plc_deploy.store import JobStore


def load_guard():
    path = Path(__file__).resolve().parents[1] / "scripts/check_active_jobs.py"
    spec = importlib.util.spec_from_file_location("check_active_jobs", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_deployment_guard_reports_only_active_jobs(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "service.db")
    store.create("running", {"requirement": "x"})
    store.update("running", status="generating")
    store.create("done", {"requirement": "y"})
    store.update("done", status="verified_success")
    jobs = load_guard().active_jobs(store.path)
    assert [(item["id"], item["status"]) for item in jobs] == [("running", "generating")]


def test_deployment_guard_uses_configured_durable_store_by_default() -> None:
    source = (
        Path(__file__).resolve().parents[1] / "scripts/check_active_jobs.py"
    ).read_text(encoding="utf-8")
    assert "create_job_store(settings.data_root, settings.database_url)" in source
    assert "default=None" in source
    assert '"cancelling"' in source


def test_tls_proxy_has_reload_endpoint_and_browser_security_headers() -> None:
    project = Path(__file__).resolve().parents[1]
    caddy = (project / "deploy/plc-generation.Caddyfile").read_text(encoding="utf-8")
    service = (project / "deploy/plc-generation-proxy.service").read_text(
        encoding="utf-8"
    )

    assert "admin 127.0.0.1:2020" in caddy
    assert "Content-Security-Policy" in caddy
    assert "Permissions-Policy" in caddy
    assert "Strict-Transport-Security" in caddy
    assert "-Server" in caddy
    assert "reload --address 127.0.0.1:2020" in service


def test_release_promotion_is_prechecked_and_rolls_back_on_failure() -> None:
    project = Path(__file__).resolve().parents[1]
    script = (project / "scripts/promote_release_candidate.sh").read_text(encoding="utf-8")
    assert "trap rollback ERR" in script
    assert 'PLC_ENVIRONMENT=production sudo -u ubuntu -E "$python"' in script
    assert '-m pytest -q "$staging_root/tests"' in script
    assert '"$staging_root/scripts/preflight.py"' in script
    assert "plc-dvp-canary@01.timer" in script
    assert "https://ai.fuxtagent.com:18080/health" in script
    assert "systemctl restart plc-dvp-bridge@01.service" not in script


def test_validation_pool_has_an_explicit_one_node_at_a_time_restart_procedure() -> None:
    project = Path(__file__).resolve().parents[1]
    script = (project / "scripts/rolling_restart_validation_pool.sh").read_text(
        encoding="utf-8"
    )
    assert "for node in 01 02 03 04" in script
    assert "active_user_job.json" in script
    assert 'systemctl restart "plc-dvp-bridge@$node.service"' in script
    assert "run_vendor_long_lease.py" in script


def test_each_windows_node_has_a_leased_daily_positive_negative_canary() -> None:
    project = Path(__file__).resolve().parents[1]
    service = (project / "deploy/plc-dvp-canary@.service").read_text(encoding="utf-8")
    timer = (project / "deploy/plc-dvp-canary@.timer").read_text(encoding="utf-8")
    assert "run_vendor_long_lease.py" in service
    assert "--cycles 1" in service
    assert "ConditionPathExists=!/opt/plc-generation/dvp-bridge-%i/qualification_active" in service
    assert "OnUnitActiveSec=24h" in timer


def test_release_installs_verified_daily_backup_outside_the_repository() -> None:
    project = Path(__file__).resolve().parents[1]
    script = (project / "scripts/backup_production.py").read_text(encoding="utf-8")
    service = (project / "deploy/plc-generation-backup.service").read_text(encoding="utf-8")
    timer = (project / "deploy/plc-generation-backup.timer").read_text(encoding="utf-8")
    assert '"pg_dump"' in script and '"pg_restore"' in script
    assert "sha256" in script and "verify_backup(partial)" in script
    assert "/opt/plc-generation/backups" in service
    assert "OnCalendar=" in timer and "Persistent=true" in timer


def test_restore_drill_uses_isolated_targets_and_always_cleans_them() -> None:
    project = Path(__file__).resolve().parents[1]
    script = (project / "scripts/restore_drill.py").read_text(encoding="utf-8")
    assert "plc_restore_drill_" in script
    assert '"createdb"' in script and '"pg_restore"' in script
    assert '"dropdb"' in script and '"--if-exists"' in script
    assert "finally:" in script


def test_release_gate_requires_services_timers_backups_and_node_qualification() -> None:
    project = Path(__file__).resolve().parents[1]
    gate = (project / "scripts/release_gate.py").read_text(encoding="utf-8")
    assert "plc-generation-backup.timer" in gate
    assert "plc-dvp-canary@04.timer" in gate
    assert "minimum-qualification-jobs" in gate
    assert "daily_canary_report.json" in gate
    assert "no verified production backup exists" in gate

from __future__ import annotations

import json
import importlib.util
import os
import time
from pathlib import Path

from plc_deploy.pipeline import (
    _acquire_delta_worker,
    _release_delta_worker,
    _validator_config,
    _vendor_validation_result,
    delta_validation_status,
    dvp_bridge_readiness,
)
from plc_deploy.settings import Settings
from plc_loop.delta_dvp import build_dvp_harness, parse_function_block, select_openplc_cases


def settings(
    tmp_path: Path,
    monkeypatch,
    *,
    spool_roots: tuple[Path, ...] | None = None,
) -> Settings:
    monkeypatch.setenv("PLC_PROJECT_ROOT", str(Path(__file__).resolve().parents[1]))
    monkeypatch.setenv("PLC_TOOL_ROOT", str(tmp_path / "tools"))
    monkeypatch.setenv("PLC_DATA_ROOT", str(tmp_path / "data"))
    # Production config defines the multi-worker variable.  Remove it so this
    # test fixture can never resolve to or mutate a live Windows spool.
    monkeypatch.delenv("PLC_DVP_SPOOL_ROOTS", raising=False)
    if spool_roots:
        monkeypatch.setenv("PLC_DVP_SPOOL_ROOTS", ",".join(map(str, spool_roots)))
        monkeypatch.setenv("PLC_DVP_SPOOL_ROOT", str(spool_roots[0]))
    else:
        monkeypatch.setenv("PLC_DVP_SPOOL_ROOT", str(tmp_path / "bridge/dvp-spool"))
    return Settings.load()


def provider() -> dict:
    return {
        "name": "test",
        "base_url": "https://example.test/v1",
        "api_key_env": "UNUSED",
        "requested_model": "test",
        "allowed_resolved_models": ["test"],
    }


def test_worker_progress_reader_ignores_partial_and_foreign_records(tmp_path: Path) -> None:
    script = Path(__file__).resolve().parents[1] / "scripts/dvp48es300r_validator.py"
    spec = importlib.util.spec_from_file_location("dvp_validator_progress_test", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    path = tmp_path / "worker_progress.jsonl"
    path.write_text(
        "\n".join([
            json.dumps({"job_id": "other", "phase": "project_load"}),
            json.dumps({
                "job_id": "job-1", "phase": "oracle_evaluation",
                "target": "DVP48ES300R", "case_index": 2, "case_total": 5,
            }),
            '{"job_id":"job-1","phase":',
        ]),
        encoding="utf-8-sig",
    )

    records = module._read_worker_progress(path, "job-1")
    assert len(records) == 1
    assert records[0]["phase"] == "oracle_evaluation"
    assert records[0]["case_index"] == 2


def test_vendor_canary_rejects_wrong_execution_identity_before_health_mutation(
    tmp_path: Path,
) -> None:
    script = Path(__file__).resolve().parents[1] / "scripts/run_vendor_canary.py"
    spec = importlib.util.spec_from_file_location("vendor_canary_identity_test", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    owner_uid = tmp_path.stat().st_uid
    assert module.execution_identity_error(tmp_path, effective_uid=owner_uid) is None
    assert "spool owner" in module.execution_identity_error(
        tmp_path, effective_uid=owner_uid + 1
    )


def test_all_vendor_qualification_entrypoints_enforce_spool_identity() -> None:
    root = Path(__file__).resolve().parents[1] / "scripts"
    for name in (
        "run_vendor_canary.py",
        "run_vendor_pool_stability.py",
        "run_vendor_soak.py",
        "run_vendor_long_lease.py",
    ):
        source = (root / name).read_text(encoding="utf-8")
        assert "execution_identity_error" in source


def _write_ready_worker(root: Path, worker_id: str, pending_jobs: int = 0) -> Path:
    spool = root / "dvp-spool"
    (spool / "pending").mkdir(parents=True)
    (spool / "results").mkdir()
    (root / "bootstrap_status.json").write_text(
        json.dumps({"status": "worker_started"}), encoding="utf-8"
    )
    (root / "bridge_heartbeat.json").write_text(
        json.dumps({"status": "connected", "worker_id": worker_id}), encoding="utf-8"
    )
    (root / "worker_heartbeat.json").write_text(
        json.dumps({"status": "connected", "worker_id": worker_id}), encoding="utf-8"
    )
    (root / "simulator_status.json").write_text(json.dumps({
        "status": "ready", "commgr_running": True,
        "dvp_simulator_running": True, "as200_simulator_running": True,
    }), encoding="utf-8")
    (root / "as228t_template_status.json").write_text(
        json.dumps({"status": "ready"}), encoding="utf-8"
    )
    for index in range(pending_jobs):
        (spool / "pending" / f"job-{index}").mkdir()
    return spool


def test_worker_pool_selects_shortest_healthy_target_queue(tmp_path: Path) -> None:
    script = Path(__file__).resolve().parents[1] / "scripts/dvp48es300r_validator.py"
    spec = importlib.util.spec_from_file_location("dvp_validator_pool_test", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    busy = _write_ready_worker(tmp_path / "worker-a", "worker-a", pending_jobs=2)
    idle = _write_ready_worker(tmp_path / "worker-b", "worker-b", pending_jobs=0)

    selected = module.select_worker([busy, idle], "DVP48ES300R")

    assert selected["worker_id"] == "worker-b"
    assert selected["spool_root"] == idle
    with module._worker_pool_lock([busy, idle]):
        pass
    assert (busy.parent / ".pool-locks").is_dir()


def test_generation_jobs_receive_distinct_exclusive_windows_workers(
    tmp_path: Path, monkeypatch
) -> None:
    first = _write_ready_worker(tmp_path / "worker-a", "worker-a")
    second = _write_ready_worker(tmp_path / "worker-b", "worker-b")
    value = settings(tmp_path, monkeypatch, spool_roots=(first, second))
    job_a = tmp_path / "jobs/a"; job_a.mkdir(parents=True)
    job_b = tmp_path / "jobs/b"; job_b.mkdir(parents=True)

    lease_a = _acquire_delta_worker(
        value, job_id="job-a", target="DVP48ES300R", job_root=job_a,
        cancel_check=lambda: False,
    )
    lease_b = _acquire_delta_worker(
        value, job_id="job-b", target="AS228T-A", job_root=job_b,
        cancel_check=lambda: False,
    )
    try:
        assert lease_a[1] != lease_b[1]
        assert json.loads((lease_a[1].parent / "active_user_job.json").read_text())["job_id"] == "job-a"
        assert json.loads((lease_b[1].parent / "active_user_job.json").read_text())["job_id"] == "job-b"
    finally:
        _release_delta_worker(lease_b, "job-b")
        _release_delta_worker(lease_a, "job-a")


def test_assigned_worker_is_the_only_vendor_spool_in_effective_config(
    tmp_path: Path, monkeypatch
) -> None:
    value = settings(tmp_path, monkeypatch)
    assigned = tmp_path / "worker-4/dvp-spool"
    config = _validator_config(
        value, provider(), 20, "delta", "DVP48ES300R",
        assigned_dvp_spool=assigned,
    )
    command = next(item for item in config["validators"] if item["name"] == "dvp48es300r")["command"]
    assert command.count("--spool-root") == 1
    assert str(assigned) in command


def test_worker_pool_rejects_stale_worker_and_wrong_target(tmp_path: Path) -> None:
    script = Path(__file__).resolve().parents[1] / "scripts/dvp48es300r_validator.py"
    spec = importlib.util.spec_from_file_location("dvp_validator_pool_stale_test", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    spool = _write_ready_worker(tmp_path / "worker-a", "worker-a")
    heartbeat = spool.parent / "worker_heartbeat.json"
    old = time.time() - 120
    os.utime(heartbeat, (old, old))

    try:
        module.select_worker([spool], "AS228T-A")
    except RuntimeError as exc:
        assert "no healthy Windows worker" in str(exc)
    else:
        raise AssertionError("a stale worker must never receive a vendor job")


def test_dvp_target_uses_vendor_toolchain_as_final_gate(tmp_path: Path, monkeypatch) -> None:
    config = _validator_config(
        settings(tmp_path, monkeypatch), provider(), 20, "delta", "DVP48ES300R"
    )
    by_name = {item["name"]: item for item in config["validators"]}
    assert config["experiment"]["sealed_gate"] == "dvp48es300r"
    assert config["experiment"]["required_visible_gates"] == [
        "compiler", "plcverif", "openplc_feedback", "openplc_confirmation"
    ]
    assert by_name["openplc_confirmation"]["sealed"] is False
    assert by_name["dvp48es300r"]["sealed"] is True
    assert "--case-role" in by_name["dvp48es300r"]["command"]
    assert "all" in by_name["dvp48es300r"]["command"]


def test_internal_generic_target_keeps_openplc_as_final_gate(tmp_path: Path, monkeypatch) -> None:
    config = _validator_config(
        settings(tmp_path, monkeypatch), provider(), 20, "generic", "generic"
    )
    assert config["experiment"]["sealed_gate"] == "openplc"
    assert all(item["name"] != "dvp48es300r" for item in config["validators"])


def test_as228t_target_uses_as200_vendor_toolchain(tmp_path: Path, monkeypatch) -> None:
    config = _validator_config(
        settings(tmp_path, monkeypatch), provider(), 20, "delta", "AS228T-A", "ld"
    )
    by_name = {item["name"]: item for item in config["validators"]}
    assert config["experiment"]["sealed_gate"] == "as228t"
    assert by_name["as228t"]["sealed"] is True
    command = by_name["as228t"]["command"]
    assert command[command.index("--target") + 1] == "AS228T-A"
    assert "Ladder IR" in config["experiment"]["verification_profile"]


def test_bridge_readiness_requires_worker_and_fresh_heartbeat(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "plc_deploy.pipeline._tcp_endpoint_status",
        lambda host, port, timeout_seconds=1.0: {
            "online": True, "latency_ms": 7, "detail": "tcp_connected"
        },
    )
    value = settings(tmp_path, monkeypatch)
    bridge = value.dvp_spool_root.parent
    (value.dvp_spool_root / "pending").mkdir(parents=True)
    (value.dvp_spool_root / "results").mkdir()
    (bridge / "bootstrap_status.json").write_text(
        json.dumps({"status": "worker_started"}), encoding="utf-8"
    )
    (bridge / "bridge_heartbeat.json").write_text(
        json.dumps({"status": "connected"}), encoding="utf-8"
    )
    (bridge / "worker_heartbeat.json").write_text(
        json.dumps({"status": "connected", "state": "polling"}), encoding="utf-8"
    )
    (bridge / "simulator_status.json").write_text(json.dumps({
        "status": "ready",
        "commgr_running": True,
        "dvp_simulator_running": True,
        "as200_simulator_running": True,
    }), encoding="utf-8")
    (bridge / "as228t_template_status.json").write_text(
        json.dumps({"status": "ready"}), encoding="utf-8"
    )
    assert dvp_bridge_readiness(value)["ready"] is True

    public = delta_validation_status(value)
    assert public["windows_worker"]["ready"] is True
    assert public["controllers"]["DVP48ES300R"]["ready"] is True
    assert public["controllers"]["AS228T-A"]["ready"] is True
    assert public["controllers"]["AS228T-A"]["template_ready"] is True
    assert public["host"]["address"] == "58.221.227.30"
    assert public["host"]["port"] == 60000
    assert public["windows_worker"]["name"] == "vps_windows"
    assert public["windows_worker"]["address"] == "10.0.2.15"
    assert public["windows_worker"]["port"] == 3389
    assert public["windows_worker"]["commgr_running"] is True
    assert public["windows_worker"]["dvp_simulator_running"] is True
    assert public["windows_worker"]["as200_simulator_running"] is True
    assert public["windows_worker"]["as228t_template_ready"] is True


def test_bridge_readiness_rejects_stale_or_missing_windows_worker_heartbeat(
    tmp_path: Path, monkeypatch
) -> None:
    value = settings(tmp_path, monkeypatch)
    bridge = value.dvp_spool_root.parent
    (value.dvp_spool_root / "pending").mkdir(parents=True)
    (value.dvp_spool_root / "results").mkdir()
    (bridge / "bootstrap_status.json").write_text(
        json.dumps({"status": "worker_started"}), encoding="utf-8"
    )
    (bridge / "bridge_heartbeat.json").write_text(
        json.dumps({"status": "connected"}), encoding="utf-8"
    )
    (bridge / "simulator_status.json").write_text(json.dumps({
        "status": "ready",
        "commgr_running": True,
        "dvp_simulator_running": True,
        "as200_simulator_running": True,
    }), encoding="utf-8")
    (bridge / "as228t_template_status.json").write_text(
        json.dumps({"status": "ready"}), encoding="utf-8"
    )

    readiness = dvp_bridge_readiness(value)
    assert readiness["heartbeat_fresh"] is True
    assert readiness["worker_heartbeat_fresh"] is False
    assert readiness["ready"] is False
    assert delta_validation_status(value)["windows_worker"]["ready"] is False


def test_bridge_readiness_tolerates_transient_redirected_drive_replace_gap(
    tmp_path: Path, monkeypatch
) -> None:
    value = settings(tmp_path, monkeypatch)
    bridge = value.dvp_spool_root.parent
    (value.dvp_spool_root / "pending").mkdir(parents=True)
    (value.dvp_spool_root / "results").mkdir()
    (bridge / "bootstrap_status.json").write_text(
        json.dumps({"status": "worker_started"}), encoding="utf-8"
    )
    (bridge / "bridge_heartbeat.json").write_text(
        json.dumps({"status": "connected"}), encoding="utf-8"
    )
    worker_path = bridge / "worker_heartbeat.json"
    worker_path.write_text(
        json.dumps({"status": "connected", "state": "polling"}), encoding="utf-8"
    )
    (bridge / "simulator_status.json").write_text(json.dumps({
        "status": "ready",
        "commgr_running": True,
        "dvp_simulator_running": True,
        "as200_simulator_running": True,
    }), encoding="utf-8")
    (bridge / "as228t_template_status.json").write_text(
        json.dumps({"status": "ready"}), encoding="utf-8"
    )

    assert dvp_bridge_readiness(value)["ready"] is True
    worker_path.unlink()
    transient = dvp_bridge_readiness(value)
    assert transient["worker_heartbeat_fresh"] is True
    assert transient["worker_state"] == "polling"
    assert transient["ready"] is True


def test_public_vendor_result_comes_from_immutable_worker_result(tmp_path: Path) -> None:
    attempt = tmp_path / "attempts/attempt_02"
    attempt.mkdir(parents=True)
    (attempt / "dvp48es300r_all_result.json").write_text(json.dumps({
        "job_id": "job-dvp-1",
        "status": "pass",
        "public_summary": "passed",
        "tool_version": "qualified-toolchain",
        "gates": [
            {"name": "ispsoft_compile", "status": "pass"},
            {"name": "commgr_connect", "status": "pass"},
            {"name": "dvp_es3_runtime", "status": "pass"},
        ],
    }), encoding="utf-8")
    result = {
        "sealed_attempts": [{
            "attempt": 2,
            "result": {
                "name": "dvp48es300r", "status": "pass", "summary": "passed",
                "tool_version": "qualified-toolchain",
            },
        }],
        "sealed_result": None,
    }
    value = _vendor_validation_result(result, tmp_path, "delta", "DVP48ES300R")
    assert value["status"] == "passed"
    assert value["job_id"] == "job-dvp-1"
    assert [item["status"] for item in value["gates"]] == ["pass", "pass", "pass"]


def test_public_as228t_result_uses_as_worker_artifact(tmp_path: Path) -> None:
    attempt = tmp_path / "attempts/attempt_01"
    attempt.mkdir(parents=True)
    (attempt / "as228t_all_result.json").write_text(json.dumps({
        "job_id": "job-as-1",
        "status": "pass",
        "public_summary": "passed",
        "tool_version": "qualified-as-toolchain",
        "gates": [
            {"name": "ispsoft_compile", "status": "pass"},
            {"name": "commgr_connect", "status": "pass"},
            {"name": "as200_runtime", "status": "pass"},
        ],
    }), encoding="utf-8")
    result = {
        "sealed_attempts": [{
            "attempt": 1,
            "result": {"name": "as228t", "status": "pass", "summary": "passed"},
        }],
        "sealed_result": None,
    }
    value = _vendor_validation_result(result, tmp_path, "delta", "AS228T-A")
    assert value["status"] == "passed"
    assert value["job_id"] == "job-as-1"
    assert "AS200" in value["toolchain"]


def test_all_role_builds_one_dvp_suite_for_both_oracle_groups() -> None:
    source = """FUNCTION_BLOCK Demo
VAR_INPUT
    Start : BOOL;
END_VAR
VAR_OUTPUT
    Motor : BOOL;
END_VAR
Motor := Start;
END_FUNCTION_BLOCK
"""
    metadata = {
        "id": "Demo",
        "scan": {"period_ms": 100},
        "interface": {
            "inputs": [{"name": "Start", "type": "BOOL"}],
            "outputs": [{"name": "Motor", "type": "BOOL"}],
        },
    }
    suite = {
        "suite": "openplc",
        "independent_requirement_oracle": True,
        "cases": [
            {"id": "FT01", "requirement_ids": ["R1"], "steps": [
                {"inputs": {"Start": True}, "expect": {"Motor": True}, "repeat": 1}
            ]},
            {"id": "OT01", "requirement_ids": ["R1"], "steps": [
                {"inputs": {"Start": False}, "expect": {"Motor": False}, "repeat": 1}
            ]},
        ],
    }
    selected = select_openplc_cases(suite, "all")
    harness = build_dvp_harness(parse_function_block(source), metadata, selected)
    assert [case["id"] for case in harness.suite["cases"]] == ["FT01", "OT01"]
    assert harness.mapping["target"] == "DVP48ES300R"


def test_as228t_harness_binds_as_target_and_driver() -> None:
    source = """FUNCTION_BLOCK Demo
VAR_INPUT
    Start : BOOL;
END_VAR
VAR_OUTPUT
    Motor : BOOL;
END_VAR
Motor := Start;
END_FUNCTION_BLOCK
"""
    metadata = {
        "id": "Demo",
        "scan": {"period_ms": 100},
        "interface": {
            "inputs": [{"name": "Start", "type": "BOOL"}],
            "outputs": [{"name": "Motor", "type": "BOOL"}],
        },
    }
    suite = {
        "suite": "openplc",
        "independent_requirement_oracle": True,
        "cases": [{"id": "FT01", "requirement_ids": ["R1"], "steps": [
            {"inputs": {"Start": True}, "expect": {"Motor": True}, "repeat": 1}
        ]}],
    }
    harness = build_dvp_harness(
        parse_function_block(source), metadata, suite,
        target="AS228T-A", commgr_driver="AS228T_SIM", maximum_m=65535,
    )
    assert harness.mapping["target"] == "AS228T-A"
    assert harness.mapping["commgr_driver"] == "AS228T_SIM"

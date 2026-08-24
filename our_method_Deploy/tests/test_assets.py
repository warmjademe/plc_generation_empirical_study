from pathlib import Path

from plc_deploy.pipeline import _validator_config
from plc_deploy.settings import Settings
from plc_loop.dataset import load_task
from plc_loop.orchestrator import BoundedSynthesisHarness


def test_installed_harness_resolves_assets_from_project_root(monkeypatch, tmp_path: Path) -> None:
    project = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("PLC_PROJECT_ROOT", str(project))
    monkeypatch.setenv("PLC_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("PLC_TOOL_ROOT", str(tmp_path / "tools"))
    settings = Settings.load()
    provider = {
        "name": "test", "base_url": "https://example.test/v1", "api_key_env": "UNUSED",
        "requested_model": "test", "allowed_resolved_models": ["test"],
    }
    harness = BoundedSynthesisHarness(
        _validator_config(settings, provider, 2),
        load_task(project / "fixtures/smoke_task/SMOKE_MOTOR"),
        tmp_path / "run", "evidence", client=object(), validators=[],
    )
    assert harness.system_prompt
    assert "system_prompt" in harness.method_asset_sha256


def test_production_page_contains_ready_to_run_default_requirement() -> None:
    project = Path(__file__).resolve().parents[1]
    page = (project / "templates/app.html").read_text(encoding="utf-8")
    assert "任务名称：输送机启停与安全联锁控制" in page
    assert "EmergencyStop" in page
    assert "同一扫描周期内 StartButton 与任一停止条件同时出现" in page
    assert '<textarea id="requirement" rows="18"' in page
    assert '<button id="approve" disabled>' in page
    assert 'id="progressPanel"' in page
    assert 'id="progressBar"' in page
    assert 'id="jobModal"' in page
    assert 'id="approvalCountdown"' in page
    assert "涉及真实硬件的地址配置不会自动确认" in (
        project / "static/app.js"
    ).read_text(encoding="utf-8")
    assert 'id="modelStatusGrid"' in page
    assert 'id="refreshModelStatus"' in page
    assert 'id="serviceTopologyTitle"' in page
    assert 'id="topologyCore"' in page
    assert 'id="modelTopologyLink"' in page
    assert 'id="validatorTopologyLink"' in page
    assert 'id="validationHostStatus"' in page
    assert 'id="windowsPoolStatus"' in page
    assert 'id="dvpValidationStatus"' not in page
    assert 'id="asValidationStatus"' not in page
    assert 'id="windowsWorkerGrid"' in page
    assert "4 台 ISPSoft worker" in page
    assert 'id="topologyPage"' in page
    assert 'id="newTaskPage"' in page
    assert 'id="taskCenterPage"' in page
    assert 'id="taskList"' in page
    assert 'data-page-target="topologyPage"' in page
    script = (project / "static/app.js").read_text(encoding="utf-8")
    assert "worker-target-status" in script
    assert "DVP48ES300R','AS228T-A" in script
    assert "COMMGR DVP-ES3 Simulator" in script
    assert "COMMGR AS200 Simulator" in script
    assert "model-channel-details" in script
    assert "接口地址" in script
    assert "在线待准入校验" in script
    assert "TRACKED_JOBS_KEY" in script
    assert "refreshTaskCenter" in script
    assert 'id="outputLanguage"' in page
    assert 'id="requirementCheck"' in page
    assert 'id="requirementQuality"' in page
    assert 'id="ladderPanel"' in page
    assert 'id="vendorProcessPanel"' in page
    assert 'id="vendorProcessFlow"' in page
    assert 'class="product-banner"' in page
    assert page.index('class="service-topology topology-primary app-page"') < page.index(
        'class="panel workspace-panel app-page hidden"'
    )


def test_windows_worker_republishes_completed_result_after_redirected_drive_loss() -> None:
    project = Path(__file__).resolve().parents[1]
    worker = (project / "windows/Run-DvpValidationWorker.ps1").read_text(
        encoding="utf-8"
    )
    assert "shared result missing for completed job" in worker
    assert "Publish-Result $completedJob $completedDocument" in worker
    assert "$sharedCompletion" in worker


def test_windows_worker_uses_disposable_project_and_discards_gui_changes() -> None:
    project = Path(__file__).resolve().parents[1]
    worker = (project / "windows/Run-DvpValidationWorker.ps1").read_text(
        encoding="utf-8"
    )
    assert "function Stop-IspSoftWithoutSaving" in worker
    assert "active project" not in worker.casefold()
    assert "[int]$IspSoftStartupTimeoutSeconds = 120" in worker
    assert "ISPSoft startup pending after" in worker
    assert "ISPSoft main project window became ready after" in worker
    assert "$script:placeholderMainY = 410" in worker
    assert "$script:placeholderFunctionY = 426" in worker
    assert "function Remove-PlaceholderFunction" in worker
    assert "Join-Path $WorkerRoot 'projects'" in worker
    assert "Remove-Item -LiteralPath $script:ProjectRoot -Recurse -Force" in worker
    assert "recover|recovery|恢复|復原" in worker


def test_windows_worker_heartbeat_avoids_redirected_drive_move_replace() -> None:
    project = Path(__file__).resolve().parents[1]
    worker = (project / "windows/Run-DvpValidationWorker.ps1").read_text(
        encoding="utf-8"
    )
    heartbeat = (project / "windows/Write-DvpWorkerHeartbeat.ps1").read_text(
        encoding="utf-8"
    )
    assert "Set-Content -LiteralPath $workerStatePath" in worker
    assert "Set-Content -LiteralPath $HeartbeatPath" in heartbeat
    assert "$temporary = $workerStatePath" not in worker
    assert "$temporary = $HeartbeatPath" not in heartbeat


def test_windows_bridge_assigns_a_unique_pool_worker_identity() -> None:
    project = Path(__file__).resolve().parents[1]
    bootstrap = (project / "windows/Start-DvpValidationWorkerFromRdp.ps1").read_text(
        encoding="utf-8"
    )
    assert "worker_endpoint.json" in bootstrap
    assert "-WorkerId $workerId" in bootstrap


def test_rdp_bridge_uses_explorer_session_for_desktop_bootstrap() -> None:
    project = Path(__file__).resolve().parents[1]
    bridge = (project / "scripts/start_dvp_bridge.sh").read_text(encoding="utf-8")
    assert "/shell:" not in bridge
    assert "launch_windows_worker" in bridge
    assert "xdotool key --window" in bridge
    assert "Test-Path \\$p" in bridge
    assert "device_announce" in bridge


def test_windows_worker_emits_public_vendor_stage_telemetry() -> None:
    project = Path(__file__).resolve().parents[1]
    worker = (project / "windows/Run-DvpValidationWorker.ps1").read_text(
        encoding="utf-8"
    )
    heartbeat = (project / "windows/Write-DvpWorkerHeartbeat.ps1").read_text(
        encoding="utf-8"
    )
    for phase in (
        "input_check", "project_load", "communication_setup", "program_import",
        "ispsoft_compile", "controller_download", "commgr_runtime",
        "oracle_evaluation", "result_publish",
    ):
        assert f"'{phase}'" in worker
    assert "case_index = $CaseIndex" in worker
    assert "case_total = $CaseTotal" in worker
    assert "phase = if ($state.phase)" in heartbeat
    assert "worker_progress.jsonl" in worker

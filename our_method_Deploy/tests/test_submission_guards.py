from __future__ import annotations

from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi import HTTPException

from plc_deploy import main
from plc_deploy.schemas import JobCreate
from plc_deploy.store import JobStore


VALID_REQUIREMENT = (
    "输入 Start、Stop 均为 BOOL；输出 Motor 为 BOOL。当 Start=TRUE 时 Motor=TRUE，"
    "当 Stop=TRUE 时 Motor=FALSE，Stop 优先。初始 Motor=FALSE。"
)


class FakeExecutor:
    def __init__(self) -> None:
        self.submitted = []

    def submit(self, *args):
        self.submitted.append(args)


def configure_submission(monkeypatch, tmp_path: Path, *, capacity: int = 8) -> FakeExecutor:
    fake = FakeExecutor()
    monkeypatch.setattr(main, "store", JobStore(tmp_path / "service.db"))
    monkeypatch.setattr(main, "executor", fake)
    monkeypatch.setattr(main, "settings", replace(main.settings, max_active_jobs=capacity))
    monkeypatch.setattr(main, "dvp_bridge_readiness", lambda _settings: {"ready": True})
    monkeypatch.setattr(
        main,
        "_selected_model_readiness",
        lambda model_id: {"id": model_id, "status": "online", "detail": "ok"},
    )
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-only")
    return fake


def test_unclear_requirement_is_rejected_before_model_probe(monkeypatch, tmp_path: Path) -> None:
    configure_submission(monkeypatch, tmp_path)
    monkeypatch.setattr(
        main,
        "_selected_model_readiness",
        lambda _model_id: (_ for _ in ()).throw(AssertionError("model probe must not run")),
    )
    with pytest.raises(HTTPException) as caught:
        main.create_job(JobCreate(requirement="帮我控制一台水泵，需要安全。"))
    assert caught.value.status_code == 422
    assert caught.value.detail["code"] == "requirement_needs_clarification"
    assert caught.value.detail["missing"]


def test_unknown_or_removed_model_is_rejected_as_configuration_error(
    monkeypatch, tmp_path: Path
) -> None:
    configure_submission(monkeypatch, tmp_path)
    with pytest.raises(HTTPException) as caught:
        main.create_job(JobCreate(requirement=VALID_REQUIREMENT, llm_model="kimi-k3"))
    assert caught.value.status_code == 422
    assert caught.value.detail["code"] == "unsupported_configuration"


def test_numeric_ladder_requirement_is_rejected_before_model_call(
    monkeypatch, tmp_path: Path
) -> None:
    fake = configure_submission(monkeypatch, tmp_path)
    requirement = (
        "输入 Pulse、Reset 均为 BOOL；输出 Count 为 INT。初始 Count=0。"
        "Pulse 上升沿时 Count 增加 1；Reset=TRUE 时 Count=0，Reset 优先于 Pulse。"
    )
    with pytest.raises(HTTPException) as caught:
        main.create_job(JobCreate(requirement=requirement, output_language="ld"))
    assert caught.value.status_code == 422
    assert caught.value.detail["code"] == "unsupported_ladder_interface"
    assert fake.submitted == []


def test_offline_selected_model_fails_before_job_creation(monkeypatch, tmp_path: Path) -> None:
    fake = configure_submission(monkeypatch, tmp_path)
    monkeypatch.setattr(
        main,
        "_selected_model_readiness",
        lambda model_id: {"id": model_id, "status": "offline", "detail": "HTTP 503"},
    )
    with pytest.raises(HTTPException) as caught:
        main.create_job(JobCreate(requirement=VALID_REQUIREMENT))
    assert caught.value.status_code == 503
    assert caught.value.detail["code"] == "model_unavailable"
    assert main.store.count_statuses(main.INTERRUPTIBLE_JOB_STATUSES) == 0
    assert fake.submitted == []


def test_offline_windows_validator_fails_before_model_probe_and_job_creation(
    monkeypatch, tmp_path: Path
) -> None:
    fake = configure_submission(monkeypatch, tmp_path)
    monkeypatch.setattr(
        main,
        "dvp_bridge_readiness",
        lambda _settings: {
            "ready": False,
            "bridge_status": "missing",
            "worker_status": "missing",
            "simulator_status": "missing",
            "heartbeat_fresh": False,
        },
    )
    monkeypatch.setattr(
        main,
        "_selected_model_readiness",
        lambda _model_id: (_ for _ in ()).throw(
            AssertionError("model probe must not run while vendor validation is offline")
        ),
    )
    with pytest.raises(HTTPException) as caught:
        main.create_job(JobCreate(requirement=VALID_REQUIREMENT))
    assert caught.value.status_code == 503
    assert "ISPSoft/COMMGR" in caught.value.detail["message"]
    assert main.store.count_statuses(main.INTERRUPTIBLE_JOB_STATUSES) == 0
    assert fake.submitted == []


def test_as228t_submission_requires_qualified_clean_template(
    monkeypatch, tmp_path: Path
) -> None:
    fake = configure_submission(monkeypatch, tmp_path)
    monkeypatch.setattr(
        main,
        "dvp_bridge_readiness",
        lambda _settings: {
            "ready": True,
            "as228t_template_ready": False,
            "bridge_status": "connected",
            "worker_status": "worker_started",
        },
    )
    monkeypatch.setattr(
        main,
        "_selected_model_readiness",
        lambda _model_id: (_ for _ in ()).throw(
            AssertionError("model probe must not run without the AS228T template")
        ),
    )
    request = JobCreate(
        requirement=VALID_REQUIREMENT,
        plc_model="AS228T-A",
    )
    with pytest.raises(HTTPException) as caught:
        main.create_job(request)
    assert caught.value.status_code == 503
    assert fake.submitted == []


def test_active_job_capacity_accepts_two_users_and_rejects_excess(
    monkeypatch, tmp_path: Path
) -> None:
    fake = configure_submission(monkeypatch, tmp_path, capacity=2)
    first = main.create_job(JobCreate(requirement=VALID_REQUIREMENT))
    second = main.create_job(JobCreate(requirement=VALID_REQUIREMENT))
    assert first["id"] != second["id"]
    assert len(fake.submitted) == 2

    with pytest.raises(HTTPException) as caught:
        main.create_job(JobCreate(requirement=VALID_REQUIREMENT))
    assert caught.value.status_code == 429
    assert caught.value.detail["code"] == "job_capacity_reached"


def test_multiple_users_can_submit_distinct_jobs_concurrently(
    monkeypatch, tmp_path: Path
) -> None:
    fake = configure_submission(monkeypatch, tmp_path, capacity=8)

    def submit(_number: int):
        return main.create_job(JobCreate(requirement=VALID_REQUIREMENT))

    with ThreadPoolExecutor(max_workers=6) as executor:
        jobs = list(executor.map(submit, range(6)))
    assert len({job["id"] for job in jobs}) == 6
    assert all(job["status"] == "contract_queued" for job in jobs)
    assert len(fake.submitted) == 6


def test_capacity_is_released_after_another_users_job_finishes(
    monkeypatch, tmp_path: Path
) -> None:
    fake = configure_submission(monkeypatch, tmp_path, capacity=2)
    first = main.create_job(JobCreate(requirement=VALID_REQUIREMENT))
    main.create_job(JobCreate(requirement=VALID_REQUIREMENT))
    main.store.update(first["id"], status="verified_success")

    third = main.create_job(JobCreate(requirement=VALID_REQUIREMENT))

    assert third["status"] == "contract_queued"
    assert len(fake.submitted) == 3


def test_two_users_with_distinct_idempotency_keys_get_isolated_jobs(
    monkeypatch, tmp_path: Path
) -> None:
    fake = configure_submission(monkeypatch, tmp_path)
    request = JobCreate(requirement=VALID_REQUIREMENT)
    first = main.create_job(request, idempotency_key="user-a-request-1")
    second = main.create_job(request, idempotency_key="user-b-request-1")

    assert first["id"] != second["id"]
    assert main.store.get(first["id"])["request"] == main.store.get(second["id"])["request"]
    assert len(fake.submitted) == 2


def test_idempotency_key_reuses_job_without_duplicate_background_work(
    monkeypatch, tmp_path: Path
) -> None:
    fake = configure_submission(monkeypatch, tmp_path)
    request = JobCreate(requirement=VALID_REQUIREMENT)
    first = main.create_job(request, idempotency_key="browser-retry-1234")
    second = main.create_job(request, idempotency_key="browser-retry-1234")
    assert second["id"] == first["id"]
    assert len(fake.submitted) == 1


def test_idempotency_key_cannot_be_reused_for_a_different_request(
    monkeypatch, tmp_path: Path
) -> None:
    configure_submission(monkeypatch, tmp_path)
    main.create_job(JobCreate(requirement=VALID_REQUIREMENT), idempotency_key="browser-retry-1234")
    changed = VALID_REQUIREMENT.replace(
        "输入 Start、Stop", "输入 Start、Stop、EmergencyStop"
    ) + " EmergencyStop=TRUE 时 Motor=FALSE。"
    with pytest.raises(HTTPException) as caught:
        main.create_job(JobCreate(requirement=changed), idempotency_key="browser-retry-1234")
    assert caught.value.status_code == 409
    assert caught.value.detail["code"] == "idempotency_conflict"

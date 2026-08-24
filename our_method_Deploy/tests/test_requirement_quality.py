from __future__ import annotations

import html
import re
import runpy
import urllib.error
from pathlib import Path

import pytest

from plc_deploy.requirement_quality import assess_requirement
from plc_deploy.schemas import JobCreate, RequirementCheck


VALID_REQUIREMENTS = [
    (
        "输入 Start、Stop 均为 BOOL；输出 Motor 为 BOOL。当 Start=TRUE 时 Motor=TRUE，"
        "当 Stop=TRUE 时 Motor=FALSE，Stop 优先。初始 Motor=FALSE。"
    ),
    (
        "Inputs Start and Stop are BOOL. Output MotorRun is BOOL. When Start is TRUE, "
        "MotorRun becomes TRUE; Stop has priority and turns it FALSE. Initially MotorRun is FALSE."
    ),
    (
        "输入变量：LevelLow BOOL，LevelHigh BOOL。输出变量：Pump BOOL。控制逻辑：若 LevelLow=TRUE "
        "则启动 Pump，LevelHigh=TRUE 则停止；LevelHigh 优先于 LevelLow，二者同时出现时 Pump=FALSE。"
        "上电初始 Pump=FALSE。"
    ),
    (
        "inputs: Enable BOOL, Fault BOOL; outputs: Valve BOOL; logic: if Enable=TRUE and "
        "Fault=FALSE then Valve=TRUE, otherwise Valve=FALSE; Fault has priority over Enable; initial Valve=FALSE."
    ),
]


@pytest.mark.parametrize("requirement", VALID_REQUIREMENTS)
def test_diverse_complete_requirements_are_accepted(requirement: str) -> None:
    result = assess_requirement(requirement)
    assert result["ready"] is True
    assert result["missing"] == []


def test_retained_numeric_output_is_rejected_before_model_call() -> None:
    requirement = (
        "输入 Reset、Pulse 均为 BOOL；输出 Count 为 INT、Done 为 BOOL。Pulse 上升沿时 Count 增加，"
        "Reset 优先并清除 Count；Count 达到 10 时 Done=TRUE。初始 Count=0 且 Done=FALSE。"
    )
    result = assess_requirement(requirement)
    assert result["ready"] is False
    missing = {item["id"]: item for item in result["missing"]}
    assert missing["supported_state_model"]["evidence"] == ["Count"]
    assert "只能描述 BOOL 跨扫描状态" in missing["supported_state_model"]["message"]


@pytest.mark.parametrize(
    ("requirement", "missing"),
    [
        ("帮我控制水泵", {"inputs", "outputs", "behavior", "initial_state", "priority"}),
        (
            "输入 Start 为 BOOL；当 Start=TRUE 时启动。初始为停止，且不存在输入冲突。",
            {"outputs"},
        ),
        (
            "输入 Start；输出 Motor 为 BOOL。当 Start=TRUE 时 Motor=TRUE。初始 Motor=FALSE，"
            "且不存在输入冲突。",
            {"inputs"},
        ),
        (
            "输入 Start 为 BOOL，输出 Motor 为 BOOL；Start 时启动；Stop 优先。",
            {"initial_state"},
        ),
        (
            "输入 Alarm 为 BOOL，输出 Lamp 为 BOOL；Alarm 时 Lamp 置位并保持。初始 Lamp=FALSE；"
            "同时输入不存在冲突。",
            {"state_release"},
        ),
    ],
)
def test_ambiguous_requirements_return_actionable_missing_fields(
    requirement: str, missing: set[str]
) -> None:
    result = assess_requirement(requirement)
    assert result["ready"] is False
    assert missing <= {item["id"] for item in result["missing"]}
    assert all(item["message"] for item in result["missing"])


def test_blank_requirement_is_rejected_by_request_schema() -> None:
    with pytest.raises(ValueError, match="blank"):
        JobCreate(requirement="   ")


@pytest.mark.parametrize("schema", [JobCreate, RequirementCheck])
def test_control_characters_are_rejected_before_storage_or_prompting(schema) -> None:
    with pytest.raises(ValueError, match="control characters"):
        schema(requirement="输入 Start 为 BOOL\x00；输出 Motor 为 BOOL")


def test_default_web_requirement_passes_the_same_server_check() -> None:
    page = (Path(__file__).resolve().parents[1] / "templates/app.html").read_text(
        encoding="utf-8"
    )
    match = re.search(
        r'<textarea id="requirement"[^>]*>(.*?)</textarea>', page, re.DOTALL
    )
    assert match is not None
    assert assess_requirement(html.unescape(match.group(1)))["ready"] is True


def test_delivery_acceptance_matrix_uses_complete_requirements() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts/run_delivery_matrix.py"
    cases = runpy.run_path(str(script))["CASES"]
    # Four cases cover the controller/language matrix; the fifth forces the
    # four-slot production scheduler to exercise its queued hand-off path.
    assert len(cases) == 5
    assert all(assess_requirement(item["requirement"])["ready"] for item in cases)
    assert {
        (item["plc_model"], item["output_language"]) for item in cases
    } == {
        ("DVP48ES300R", "st"),
        ("DVP48ES300R", "ld"),
        ("AS228T-A", "st"),
        ("AS228T-A", "ld"),
    }
    source = script.read_text(encoding="utf-8")
    assert 'choices=("downloadable_project", "function_unit")' in source
    assert '"engineering_template"' in source
    assert '"engineering-mapping"' in source


@pytest.mark.parametrize(
    "error",
    [
        TimeoutError("timeout"),
        urllib.error.URLError("temporary network failure"),
        RuntimeError("POST /api/jobs returned HTTP 503: model_unavailable"),
        RuntimeError("POST /api/jobs returned HTTP 429: rate limited"),
        RuntimeError("POST /api/jobs returned HTTP 502: upstream unavailable"),
        RuntimeError("POST /api/jobs returned HTTP 504: gateway timeout"),
    ],
)
def test_delivery_matrix_retries_transient_submission_failures(error: BaseException) -> None:
    script = Path(__file__).resolve().parents[1] / "scripts/run_delivery_matrix.py"
    retryable_submission_error = runpy.run_path(str(script))["retryable_submission_error"]
    assert retryable_submission_error(error) is True


def test_delivery_matrix_does_not_retry_request_validation_errors() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts/run_delivery_matrix.py"
    retryable_submission_error = runpy.run_path(str(script))["retryable_submission_error"]
    assert retryable_submission_error(
        RuntimeError("POST /api/jobs returned HTTP 422: invalid requirement")
    ) is False


def test_delivery_matrix_recovers_from_temporary_local_api_restart(monkeypatch) -> None:
    script = Path(__file__).resolve().parents[1] / "scripts/run_delivery_matrix.py"
    namespace = runpy.run_path(str(script))
    attempts = []

    def flaky_call(*args, **kwargs):
        attempts.append(1)
        if len(attempts) < 3:
            raise urllib.error.URLError("connection refused")
        return {"status": "ok"}

    monkeypatch.setitem(namespace["resilient_call"].__globals__, "call", flaky_call)
    monkeypatch.setattr(namespace["time"], "sleep", lambda _seconds: None)
    assert namespace["resilient_call"]("http://local", "token", "GET", "/health") == {
        "status": "ok"
    }
    assert len(attempts) == 3


def test_delivery_matrix_writes_atomic_resume_checkpoint(tmp_path: Path) -> None:
    script = Path(__file__).resolve().parents[1] / "scripts/run_delivery_matrix.py"
    write_json_atomic = runpy.run_path(str(script))["write_json_atomic"]
    checkpoint = tmp_path / "matrix.checkpoint.json"
    write_json_atomic(checkpoint, {"jobs": [{"id": "job-1"}]})
    assert checkpoint.read_text(encoding="utf-8").endswith("\n")
    assert not checkpoint.with_name(checkpoint.name + ".tmp").exists()
    assert '"job-1"' in checkpoint.read_text(encoding="utf-8")

from __future__ import annotations

import json
from pathlib import Path

from plc_deploy.progress import build_job_progress


def job(status: str = "generating") -> dict:
    return {
        "id": "job-1",
        "status": status,
        "created_at": "2026-08-20T00:00:00+00:00",
        "updated_at": "2026-08-20T00:00:00+00:00",
        "request": {"max_candidates": 20},
    }


def test_progress_reports_current_validator_and_safe_events(tmp_path: Path) -> None:
    attempt = tmp_path / "jobs/job-1/run/attempts/attempt_01"
    attempt.mkdir(parents=True)
    (attempt / "request.json").write_text("{}", encoding="utf-8")
    (attempt / "raw_response.json").write_text("{}", encoding="utf-8")
    (attempt / "compiler.stdout").write_text("{}", encoding="utf-8")

    progress = build_job_progress(job(), tmp_path)

    assert progress["phase"] == "plcverif"
    assert progress["current_attempt"] == 1
    assert progress["candidate_budget"] == 20
    assert any("已收到完整 ST 候选" in item["message"] for item in progress["events"])


def test_progress_exposes_gate_outcomes_without_raw_traces(tmp_path: Path) -> None:
    attempt = tmp_path / "jobs/job-1/run/attempts/attempt_01"
    attempt.mkdir(parents=True)
    for name in ("request.json", "raw_response.json", "compiler.stdout", "plcverif.stdout", "openplc_feedback.stdout"):
        (attempt / name).write_text("{}", encoding="utf-8")
    (attempt / "evaluation.json").write_text(json.dumps({
        "gates": [{
            "name": "plcverif",
            "status": "fail",
            "summary": "property P1 failed",
            "evidence": [{"trace": {"private": "not returned by progress API"}}],
        }]
    }), encoding="utf-8")

    progress = build_job_progress(job(), tmp_path)
    encoded = json.dumps(progress, ensure_ascii=False)

    assert "PLCverif 形式验证：未通过" in encoded
    assert "property P1 failed" in encoded
    assert "not returned by progress API" not in encoded


def test_terminal_progress_is_complete(tmp_path: Path) -> None:
    progress = build_job_progress(job("verified_success"), tmp_path)
    assert progress["phase_percent"] == 100
    assert progress["active"] is False


def test_queued_job_is_not_misreported_as_delayed(tmp_path: Path) -> None:
    queued = job("generation_queued")
    queued["created_at"] = "2026-08-20T00:00:00+00:00"
    queued["updated_at"] = queued["created_at"]
    progress = build_job_progress(queued, tmp_path)
    assert progress["health"] == "working"


def test_contract_retry_progress_is_visible(tmp_path: Path) -> None:
    root = tmp_path / "jobs/job-1"
    root.mkdir(parents=True)
    (root / "contract_progress.jsonl").write_text(
        '\n'.join([
            json.dumps({"time": "2026-08-20T00:00:01+00:00", "attempt": 1, "status": "requesting"}),
            json.dumps({"time": "2026-08-20T00:00:02+00:00", "attempt": 1, "status": "rejected", "error": "invalid JSON"}),
            json.dumps({"time": "2026-08-20T00:00:03+00:00", "attempt": 2, "status": "requesting"}),
        ]) + '\n', encoding="utf-8"
    )
    progress = build_job_progress(job("contract_generating"), tmp_path)
    assert progress["contract_attempt"] == 2
    assert progress["message"].endswith("第 2/10 次）")
    assert progress["contract_budget"] == 10
    assert any("invalid JSON" in event["message"] for event in progress["events"])
    assert any("等待调用名额或模型返回" in event["message"] for event in progress["events"])


def test_progress_names_dvp_vendor_gate(tmp_path: Path) -> None:
    attempt = tmp_path / "jobs/job-1/run/attempts/attempt_01"
    attempt.mkdir(parents=True)
    for name in ("request.json", "raw_response.json", "evaluation.json"):
        (attempt / name).write_text("{}", encoding="utf-8")
    (attempt / "sealed_evaluation.json").write_text(json.dumps({
        "name": "dvp48es300r",
        "status": "pass",
        "summary": "ISPSoft compile and DVP runtime passed",
    }), encoding="utf-8")
    progress = build_job_progress(job(), tmp_path)
    encoded = json.dumps(progress, ensure_ascii=False)
    assert "ISPSoft/COMMGR DVP48ES300R 验证：通过" in encoded


def test_progress_exposes_sanitized_live_vendor_stages(tmp_path: Path) -> None:
    attempt = tmp_path / "jobs/job-1/run/attempts/attempt_01"
    attempt.mkdir(parents=True)
    for name in ("request.json", "raw_response.json"):
        (attempt / name).write_text("{}", encoding="utf-8")
    (attempt / "evaluation.json").write_text(json.dumps({
        "gates": [
            {"name": "compiler", "status": "pass"},
            {"name": "plcverif", "status": "pass"},
            {"name": "openplc_feedback", "status": "pass"},
            {"name": "openplc_confirmation", "status": "pass"},
        ]
    }), encoding="utf-8")
    (attempt / "dvp48es300r_sealed_vendor_progress.jsonl").write_text(
        "\n".join([
            json.dumps({
                "time": "2026-08-20T00:00:06+00:00", "component": "delta_vendor_validation",
                "status": "stage", "vendor_phase": "project_load",
                "phase_label": "private text is ignored", "phase_percent": 88,
                "target": "DVP48ES300R", "case_index": 0, "case_total": 0,
            }),
            json.dumps({
                "time": "2026-08-20T00:00:07+00:00", "component": "delta_vendor_validation",
                "status": "stage", "vendor_phase": "commgr_runtime",
                "phase_label": "private text is ignored", "phase_percent": 96,
                "target": "DVP48ES300R", "case_index": 2, "case_total": 5,
                "case_id": "sealed-secret-case",
            }),
        ]) + "\n", encoding="utf-8",
    )

    progress = build_job_progress(job(), tmp_path)
    encoded = json.dumps(progress, ensure_ascii=False)

    assert progress["phase"] == "delta_vendor_validation"
    assert progress["message"] == "通过 COMMGR 执行仿真输入（仿真用例 2/5）"
    assert progress["vendor_visualization"] == {
        "active": True,
        "target": "DVP48ES300R",
        "phase": "commgr_runtime",
        "phase_label": "通过 COMMGR 执行仿真输入",
        "phase_percent": 96,
        "case_index": 2,
        "case_total": 5,
        "result": "",
    }
    assert "装载 ISPSoft 干净工程" in encoded
    assert "仿真用例 2/5" in encoded
    assert "sealed-secret-case" not in encoded


def test_progress_reports_live_validator_telemetry_and_timing(tmp_path: Path) -> None:
    attempt = tmp_path / "jobs/job-1/run/attempts/attempt_01"
    attempt.mkdir(parents=True)
    (attempt / "request.json").write_text("{}", encoding="utf-8")
    (attempt / "raw_response.json").write_text("{}", encoding="utf-8")
    (attempt / "compiler.stdout").write_text("{}", encoding="utf-8")
    (attempt / "progress.jsonl").write_text(
        "\n".join([
            json.dumps({"time": "2026-08-20T00:00:01+00:00", "component": "model", "status": "started"}),
            json.dumps({"time": "2026-08-20T00:00:03+00:00", "component": "model", "status": "completed", "latency_ms": 2000, "total_tokens": 120}),
            json.dumps({"time": "2026-08-20T00:00:04+00:00", "component": "compiler", "status": "completed", "result": "pass", "duration_ms": 500}),
            json.dumps({"time": "2026-08-20T00:00:05+00:00", "component": "plcverif", "status": "started"}),
        ]) + "\n",
        encoding="utf-8",
    )

    progress = build_job_progress(job(), tmp_path)
    encoded = json.dumps(progress, ensure_ascii=False)

    assert progress["current_component"] == "PLCverif 形式验证"
    assert progress["elapsed_seconds"] >= 0
    assert "120 tokens" in encoded
    assert "PLCverif 形式验证：已开始" in encoded


def test_progress_explains_same_candidate_model_retry(tmp_path: Path) -> None:
    attempt = tmp_path / "jobs/job-1/run/attempts/attempt_02"
    attempt.mkdir(parents=True)
    (attempt / "request.json").write_text("{}", encoding="utf-8")
    (attempt / "progress.jsonl").write_text(
        "\n".join([
            json.dumps({"time": "2026-08-20T00:00:01+00:00", "component": "model", "status": "started"}),
            json.dumps({
                "time": "2026-08-20T00:00:02+00:00",
                "component": "model",
                "status": "retrying",
                "retry": 2,
                "maximum_retries": 3,
                "summary": "provider returned empty assistant content (finish_reason='length')",
            }),
        ]) + "\n",
        encoding="utf-8",
    )

    progress = build_job_progress(job(), tmp_path)
    encoded = json.dumps(progress, ensure_ascii=False)
    assert "同一候选槽重试 2/3" in encoded
    assert "empty assistant content" in encoded

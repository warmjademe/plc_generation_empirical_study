from pathlib import Path

from plc_deploy import pipeline
from plc_deploy.catalog import Catalog
from plc_deploy.contracts import ContractError, ContractInfrastructureError
from plc_deploy.pipeline import (
    _last_failure,
    _public_generation_failure,
    _provider_settings,
    _select_final_attempt,
    _validator_config,
)
from plc_deploy.schemas import JobCreate
from plc_deploy.settings import Settings
from plc_deploy.store import JobStore


def test_provider_catalog_entry_is_converted_to_harness_schema() -> None:
    value = _provider_settings({
        "id": "model-a", "label": "Model A", "provider": "provider-a",
        "base_url": "https://example.test/v1", "api_key_env": "KEY",
        "requested_model": "model", "allowed_resolved_models": ["model"],
    })
    assert value["name"] == "provider-a"
    assert "provider" not in value and "id" not in value and "label" not in value


def test_production_defaults_and_feedback_policy(tmp_path: Path, monkeypatch) -> None:
    request = JobCreate(requirement="Generate a motor controller with stop priority.")
    assert request.vendor == "delta"
    assert request.plc_model == "DVP48ES300R"
    assert request.llm_model == "deepseek-v4-pro"
    assert request.output_language == "st"
    assert request.max_candidates == 20

    monkeypatch.setenv("PLC_PROJECT_ROOT", str(Path(__file__).resolve().parents[1]))
    monkeypatch.setenv("PLC_TOOL_ROOT", str(tmp_path / "tools"))
    settings = Settings.load()
    config = _validator_config(
        settings,
        {
            "name": "test",
            "base_url": "https://example.test/v1",
            "api_key_env": "UNUSED",
            "requested_model": "test",
            "allowed_resolved_models": ["test"],
        },
        20,
    )
    assert config["experiment"]["max_candidates"] == 20
    assert config["experiment"]["sealed_rejection_policy"] == "feedback_repair"
    assert config["experiment"]["max_sealed_attempts"] == 20


def test_model_infrastructure_error_is_exposed_to_the_web_job() -> None:
    result = {
        "status": "infrastructure_error",
        "last_error": (
            "RuntimeError: provider exhausted the output-token limit in reasoning "
            "(8192 reasoning tokens) and returned no final ST content"
        ),
        "attempts": [],
    }
    assert "未返回完整程序" in _last_failure(result)


def test_network_and_upstream_errors_are_publicly_sanitized() -> None:
    network = _public_generation_failure(
        "RuntimeError: provider request failed after transport retries: "
        "<urlopen error [Errno 101] Network is unreachable>"
    )
    upstream = _public_generation_failure("RuntimeError: provider HTTP 503: private body")
    mismatch = _public_generation_failure("provider resolved unexpected model 'other-secret-name'")
    assert "网络连接" in network and "urlopen" not in network
    assert "HTTP 503" in upstream and "private body" not in upstream
    assert "模型不一致" in mismatch and "other-secret-name" not in mismatch


def test_failure_summary_uses_deepest_gate_across_restarts() -> None:
    result = {
        "status": "candidate_budget_exhausted",
        "attempts": [
            {"gates": [
                {"name": "compiler", "status": "pass", "summary": "compiled"},
                {
                    "name": "openplc_feedback",
                    "status": "inconclusive",
                    "summary": "OpenPLC deterministic semantic audit was not accepted",
                },
            ]},
            {"gates": [{
                "name": "compiler",
                "status": "fail",
                "summary": "MatIEC rejected the restarted candidate",
            }]},
        ],
    }
    assert _last_failure(result) == (
        "OpenPLC deterministic semantic audit was not accepted"
    )


def test_failed_ld_run_returns_latest_parseable_candidate(tmp_path: Path) -> None:
    attempts = []
    for number in range(1, 4):
        root = tmp_path / f"attempt_{number:02d}"
        root.mkdir()
        attempts.append(root)
    (attempts[0] / "candidate.ld.json").write_text("{\"rungs\":[]}")
    (attempts[1] / "candidate.ld.json").write_text("{\"rungs\":[1]}")
    (attempts[2] / "candidate.st").write_text("")
    assert _select_final_attempt(attempts, "ld", None) == attempts[1]


def test_contract_transport_failure_becomes_infrastructure_status(
    tmp_path: Path, monkeypatch
) -> None:
    project = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("PLC_PROJECT_ROOT", str(project))
    monkeypatch.setenv("PLC_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("PLC_TOOL_ROOT", str(tmp_path / "tools"))
    settings = Settings.load()
    store = JobStore(settings.data_root / "service.db")
    store.create("job-network", {
        "requirement": "valid requirement",
        "vendor": "delta",
        "plc_model": "DVP48ES300R",
        "llm_model": "deepseek-v4-pro",
        "output_language": "st",
        "max_candidates": 20,
    })

    def offline(*_args, **_kwargs):
        raise ContractInfrastructureError("上游模型网络连接不可用")

    monkeypatch.setattr(pipeline, "compile_contract", offline)
    pipeline.create_contract_job(
        "job-network", store, Catalog(project / "configs"), settings
    )
    job = store.get("job-network")
    assert job["status"] == "infrastructure_error"
    assert "网络连接不可用" in job["last_error"]


def test_rejected_contract_draft_is_private_and_progress_log_is_sanitized(
    tmp_path: Path, monkeypatch
) -> None:
    project = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("PLC_PROJECT_ROOT", str(project))
    monkeypatch.setenv("PLC_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("PLC_TOOL_ROOT", str(tmp_path / "tools"))
    settings = Settings.load()
    store = JobStore(settings.data_root / "service.db")
    store.create("job-draft", {
        "requirement": "valid requirement",
        "vendor": "delta",
        "plc_model": "DVP48ES300R",
        "llm_model": "deepseek-v4-pro",
        "output_language": "st",
        "max_candidates": 20,
    })

    def reject(*_args, **kwargs):
        kwargs["progress_callback"]({
            "attempt": 1,
            "maximum_attempts": 7,
            "status": "rejected",
            "error": "state/test contradiction",
            "private_draft": '{"private":"model draft"}',
        })
        raise ContractError("invalid contract")

    monkeypatch.setattr(pipeline, "compile_contract", reject)
    pipeline.create_contract_job(
        "job-draft", store, Catalog(project / "configs"), settings
    )

    job_root = settings.data_root / "jobs/job-draft"
    trace = (job_root / "contract_progress.jsonl").read_text(encoding="utf-8")
    draft = job_root / "contract_attempt_01_rejected.txt"
    assert store.get("job-draft")["status"] == "contract_failed"
    assert "model draft" not in trace
    assert "private_draft_sha256" in trace
    assert draft.read_text(encoding="utf-8").strip() == '{"private":"model draft"}'
    assert draft.stat().st_mode & 0o777 == 0o600

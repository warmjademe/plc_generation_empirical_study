from __future__ import annotations

from pathlib import Path

import pytest

from plc_deploy.pipeline import _validator_config
from plc_deploy.settings import Settings
from plc_loop.dataset import load_task
from plc_loop.models import Evidence, GateResult, ModelReply
from plc_loop.orchestrator import BoundedSynthesisHarness


class PassingValidator:
    blocking = True
    inconclusive_is_blocking = True
    sealed = False

    def __init__(self, name: str):
        self.name = name

    def preflight(self, task) -> None:
        return None

    def run(self, task, candidate_path, artifact_dir) -> GateResult:
        return GateResult(self.name, "pass", f"{self.name} passed")


class ConfirmationValidator(PassingValidator):
    sealed = True

    def __init__(self):
        super().__init__("openplc")
        self.calls = 0

    def run(self, task, candidate_path, artifact_dir) -> GateResult:
        self.calls += 1
        if self.calls == 1:
            return GateResult(
                self.name,
                "fail",
                "confirmation case stop-priority failed",
                evidence=(Evidence(
                    tool=self.name,
                    kind="openplc_functional_failure",
                    summary="Motor remained TRUE while Stop was TRUE",
                    requirement_ids=("R1",),
                    trace={
                        "inputs": {"Start": True, "Stop": True},
                        "expected": {"Motor": False},
                        "observed": {"Motor": True},
                    },
                    oracle_status="confirmed_candidate_defect",
                ),),
            )
        return GateResult(self.name, "pass", "confirmation cases passed")


class RecordingClient:
    def __init__(self):
        self.messages: list[list[dict]] = []

    def generate(self, messages: list[dict]) -> ModelReply:
        self.messages.append(messages)
        body = "Motor := Start;" if len(self.messages) == 1 else "Motor := Start AND NOT Stop;"
        content = (
            "<repair_hypothesis>apply stop priority</repair_hypothesis>\n"
            "<target_requirements>R1</target_requirements>\n"
            "<st_program>\n"
            "FUNCTION_BLOCK SMOKE_MOTOR\n"
            "VAR_INPUT\n    Start : BOOL;\n    Stop : BOOL;\nEND_VAR\n"
            "VAR_OUTPUT\n    Motor : BOOL;\nEND_VAR\n"
            f"{body}\nEND_FUNCTION_BLOCK\n"
            "</st_program>"
        )
        message = {"role": "assistant", "content": content}
        return ModelReply(
            message=message,
            raw_response={"model": "test", "choices": [{"message": message}]},
            requested_model="test",
            resolved_model="test",
            provider="test",
            usage={"total_tokens": 10},
            finish_reason="stop",
            latency_ms=1,
        )


class RetryOnSecondCandidateClient(RecordingClient):
    def __init__(self):
        super().__init__()
        self.calls = 0

    def generate(self, messages: list[dict]) -> ModelReply:
        self.calls += 1
        if self.calls == 2:
            self.messages.append(messages)
            raise RuntimeError(
                "provider returned empty assistant content (finish_reason='length')"
            )
        return super().generate(messages)


class ContentConfirmationValidator(PassingValidator):
    sealed = True

    def __init__(self):
        super().__init__("openplc")

    def run(self, task, candidate_path, artifact_dir) -> GateResult:
        if "NOT Stop" in candidate_path.read_text(encoding="utf-8"):
            return GateResult(self.name, "pass", "confirmation cases passed")
        return GateResult(
            self.name,
            "fail",
            "stop priority failed",
            evidence=(Evidence(
                self.name, "openplc_functional_failure", "Motor ignored Stop",
                requirement_ids=("R1",), oracle_status="confirmed_candidate_defect",
            ),),
        )


class CrashAfterFirstCandidateClient(RecordingClient):
    def generate(self, messages: list[dict]) -> ModelReply:
        if self.messages:
            raise KeyboardInterrupt("simulated service process loss")
        return super().generate(messages)


class FixedCandidateClient(RecordingClient):
    def generate(self, messages: list[dict]) -> ModelReply:
        self.messages.append(messages)
        content = (
            "<repair_hypothesis>restore from durable evidence</repair_hypothesis>\n"
            "<target_requirements>R1</target_requirements>\n"
            "<st_program>\nFUNCTION_BLOCK SMOKE_MOTOR\n"
            "VAR_INPUT\n    Start : BOOL;\n    Stop : BOOL;\nEND_VAR\n"
            "VAR_OUTPUT\n    Motor : BOOL;\nEND_VAR\n"
            "Motor := Start AND NOT Stop;\nEND_FUNCTION_BLOCK\n</st_program>"
        )
        message = {"role": "assistant", "content": content}
        return ModelReply(
            message=message,
            raw_response={"model": "test", "choices": [{"message": message}]},
            requested_model="test", resolved_model="test", provider="test",
            usage={"total_tokens": 10}, finish_reason="stop", latency_ms=1,
        )


def test_confirmation_failure_is_fed_into_next_st_generation(tmp_path: Path, monkeypatch) -> None:
    project = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("PLC_PROJECT_ROOT", str(project))
    monkeypatch.setenv("PLC_TOOL_ROOT", str(tmp_path / "tools"))
    settings = Settings.load()
    provider = {
        "name": "test",
        "base_url": "https://example.test/v1",
        "api_key_env": "UNUSED",
        "requested_model": "test",
        "allowed_resolved_models": ["test"],
    }
    config = _validator_config(settings, provider, 2)
    client = RecordingClient()
    validators = [
        PassingValidator("interface"),
        PassingValidator("compiler"),
        PassingValidator("plcverif"),
        PassingValidator("openplc_feedback"),
        ConfirmationValidator(),
    ]
    harness = BoundedSynthesisHarness(
        config,
        load_task(project / "fixtures/smoke_task/SMOKE_MOTOR"),
        tmp_path / "run",
        "evidence",
        client=client,
        validators=validators,
    )

    result = harness.run()

    assert result["success"] is True
    assert result["candidates_used"] == 2
    assert len(client.messages) == 2
    second_prompt = client.messages[1][-1]["content"]
    assert "Motor remained TRUE while Stop was TRUE" in second_prompt
    assert "openplc_functional_failure" in second_prompt


def test_empty_length_response_retries_same_candidate_slot(tmp_path: Path, monkeypatch) -> None:
    project = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("PLC_PROJECT_ROOT", str(project))
    monkeypatch.setenv("PLC_TOOL_ROOT", str(tmp_path / "tools"))
    settings = Settings.load()
    provider = {
        "name": "test",
        "base_url": "https://example.test/v1",
        "api_key_env": "UNUSED",
        "requested_model": "test",
        "allowed_resolved_models": ["test"],
    }
    config = _validator_config(settings, provider, 2)
    client = RetryOnSecondCandidateClient()
    validators = [
        PassingValidator("interface"),
        PassingValidator("compiler"),
        PassingValidator("plcverif"),
        PassingValidator("openplc_feedback"),
        ConfirmationValidator(),
    ]
    run_root = tmp_path / "run"
    result = BoundedSynthesisHarness(
        config,
        load_task(project / "fixtures/smoke_task/SMOKE_MOTOR"),
        run_root,
        "evidence",
        client=client,
        validators=validators,
    ).run()

    assert result["success"] is True
    assert result["candidates_used"] == 2
    assert client.calls == 3
    progress = (run_root / "attempts/attempt_02/progress.jsonl").read_text()
    assert '"status":"retrying"' in progress
    assert '"retry":2' in progress
    ledger = (run_root / "ledger.jsonl").read_text()
    assert '"retryable": true' in ledger


def test_service_restart_resumes_from_completed_candidate_checkpoint(
    tmp_path: Path, monkeypatch
) -> None:
    project = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("PLC_PROJECT_ROOT", str(project))
    monkeypatch.setenv("PLC_TOOL_ROOT", str(tmp_path / "tools"))
    settings = Settings.load()
    provider = {
        "name": "test", "base_url": "https://example.test/v1", "api_key_env": "UNUSED",
        "requested_model": "test", "allowed_resolved_models": ["test"],
    }
    config = _validator_config(settings, provider, 3)
    validators = [
        PassingValidator("interface"), PassingValidator("compiler"),
        PassingValidator("plcverif"), PassingValidator("openplc_feedback"),
        ContentConfirmationValidator(),
    ]
    run_root = tmp_path / "run"
    with pytest.raises(KeyboardInterrupt):
        BoundedSynthesisHarness(
            config, load_task(project / "fixtures/smoke_task/SMOKE_MOTOR"),
            run_root, "evidence", client=CrashAfterFirstCandidateClient(),
            validators=validators,
        ).run()

    resumed = FixedCandidateClient()
    result = BoundedSynthesisHarness(
        config, load_task(project / "fixtures/smoke_task/SMOKE_MOTOR"),
        run_root, "evidence", client=resumed, validators=validators,
    ).run(resume=True)

    assert result["success"] is True
    assert result["candidates_used"] == 2
    assert result["candidate_slots_consumed"] == 3
    assert len(resumed.messages) == 1
    assert "Motor ignored Stop" in resumed.messages[0][-1]["content"]
    assert '"event_type": "run_resumed"' in (run_root / "ledger.jsonl").read_text()


def test_nonretryable_model_configuration_error_is_terminal(tmp_path: Path, monkeypatch) -> None:
    project = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("PLC_PROJECT_ROOT", str(project))
    monkeypatch.setenv("PLC_TOOL_ROOT", str(tmp_path / "tools"))
    settings = Settings.load()
    provider = {
        "name": "test",
        "base_url": "https://example.test/v1",
        "api_key_env": "UNUSED",
        "requested_model": "test",
        "allowed_resolved_models": ["test"],
    }
    config = _validator_config(settings, provider, 2)

    class WrongModelClient:
        calls = 0

        def generate(self, messages):
            self.calls += 1
            raise RuntimeError("provider resolved unexpected model 'other'")

    client = WrongModelClient()
    result = BoundedSynthesisHarness(
        config,
        load_task(project / "fixtures/smoke_task/SMOKE_MOTOR"),
        tmp_path / "run",
        "evidence",
        client=client,
        validators=[
            PassingValidator("compiler"),
            PassingValidator("plcverif"),
            PassingValidator("openplc_feedback"),
            ConfirmationValidator(),
        ],
    ).run()
    assert result["status"] == "infrastructure_error"
    assert result["candidates_used"] == 0
    assert client.calls == 1


def test_network_loss_during_candidate_generation_is_bounded_and_infrastructure_error(
    tmp_path: Path, monkeypatch
) -> None:
    project = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("PLC_PROJECT_ROOT", str(project))
    monkeypatch.setenv("PLC_TOOL_ROOT", str(tmp_path / "tools"))
    settings = Settings.load()
    provider = {
        "name": "test", "base_url": "https://example.test/v1", "api_key_env": "UNUSED",
        "requested_model": "test", "allowed_resolved_models": ["test"],
    }
    config = _validator_config(settings, provider, 2)

    class OfflineClient:
        calls = 0

        def generate(self, messages):
            self.calls += 1
            raise RuntimeError(
                "provider request failed after transport retries: network unreachable"
            )

    client = OfflineClient()
    result = BoundedSynthesisHarness(
        config,
        load_task(project / "fixtures/smoke_task/SMOKE_MOTOR"),
        tmp_path / "run",
        "evidence",
        client=client,
        validators=[
            PassingValidator("compiler"),
            PassingValidator("plcverif"),
            PassingValidator("openplc_feedback"),
            ConfirmationValidator(),
        ],
    ).run()
    assert result["status"] == "infrastructure_error"
    assert result["candidates_used"] == 0
    assert client.calls == 3

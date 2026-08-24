from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

from plc_deploy import model_status
from plc_deploy import main
from plc_loop.models import ModelReply


def configured_model() -> dict:
    return {
        "id": "model-a",
        "label": "Model A",
        "provider": "provider-a",
        "base_url": "https://example.test/v1",
        "api_key_env": "MODEL_A_KEY",
        "requested_model": "model-a",
        "allowed_resolved_models": ["model-a"],
    }


def test_status_uses_real_completion_and_cache(monkeypatch) -> None:
    calls = []

    class FakeClient:
        def __init__(self, settings):
            calls.append(settings)

        def generate(self, messages):
            return ModelReply(
                message={"role": "assistant", "content": "OK"}, raw_response={},
                requested_model="model-a", resolved_model="model-a", provider="provider-a",
                usage={"total_tokens": 2}, finish_reason="stop", latency_ms=12,
            )

    monkeypatch.setenv("MODEL_A_KEY", "configured-for-test")
    monkeypatch.setattr(model_status, "OpenAICompatibleClient", FakeClient)
    model_status.clear_model_status_cache()
    first = model_status.model_service_status([configured_model()], now=100.0)
    second = model_status.model_service_status([configured_model()], now=101.0)

    assert first["probe"] == "minimal_real_inference"
    assert first["models"][0]["status"] == "online"
    assert second == first
    assert len(calls) == 1
    assert calls[0].max_output_tokens == 8
    assert calls[0].transport_retries == 0
    assert calls[0].timeout_seconds == 12


def test_status_distinguishes_unconfigured_and_http_failure(monkeypatch) -> None:
    class FailingClient:
        def __init__(self, settings):
            pass

        def generate(self, messages):
            raise RuntimeError("provider request failed: HTTP 503: secret upstream detail")

    model_status.clear_model_status_cache()
    monkeypatch.delenv("MODEL_A_KEY", raising=False)
    missing = model_status.model_service_status([configured_model()], now=200.0)
    assert missing["models"][0]["status"] == "unconfigured"

    model_status.clear_model_status_cache()
    monkeypatch.setenv("MODEL_A_KEY", "configured-for-test")
    monkeypatch.setattr(model_status, "OpenAICompatibleClient", FailingClient)
    failed = model_status.model_service_status([configured_model()], now=300.0)
    assert failed["models"][0]["status"] == "offline"
    assert failed["models"][0]["detail"] == "上游服务返回 HTTP 503"


def test_status_reports_network_disconnect_without_exposing_raw_exception(monkeypatch) -> None:
    class OfflineClient:
        def __init__(self, settings):
            pass

        def generate(self, messages):
            raise RuntimeError("<urlopen error [Errno 101] Network is unreachable>")

    model_status.clear_model_status_cache()
    monkeypatch.setenv("MODEL_A_KEY", "configured-for-test")
    monkeypatch.setattr(model_status, "OpenAICompatibleClient", OfflineClient)
    result = model_status.model_service_status([configured_model()], now=400.0)
    assert result["models"][0]["status"] == "offline"
    assert result["models"][0]["detail"] == "无法连接上游模型网络"


def test_job_submission_requests_a_fresh_enough_model_probe(monkeypatch) -> None:
    calls = []

    def status(_models, *, force=False):
        calls.append(force)
        return {
            "models": [{"id": "deepseek-v4-pro", "status": "online", "detail": "ok"}]
        }

    monkeypatch.setattr(main, "model_service_status", status)
    assert main._selected_model_readiness("deepseek-v4-pro")["status"] == "online"
    assert calls == [True]


def test_status_cache_is_isolated_by_requested_model_set(monkeypatch) -> None:
    requested = []

    class FakeClient:
        def __init__(self, settings):
            self.settings = settings

        def generate(self, _messages):
            requested.append(self.settings.requested_model)
            return ModelReply(
                message={"role": "assistant", "content": "OK"}, raw_response={},
                requested_model=self.settings.requested_model,
                resolved_model=self.settings.requested_model,
                provider=self.settings.name, usage={"total_tokens": 1},
                finish_reason="stop", latency_ms=1,
            )

    first = configured_model()
    second = {**configured_model(), "id": "model-b", "requested_model": "model-b",
              "allowed_resolved_models": ["model-b"]}
    monkeypatch.setenv("MODEL_A_KEY", "configured-for-test")
    monkeypatch.setattr(model_status, "OpenAICompatibleClient", FakeClient)
    model_status.clear_model_status_cache()
    assert model_status.model_service_status([first], now=500.0)["models"][0]["id"] == "model-a"
    assert model_status.model_service_status([second], now=501.0)["models"][0]["id"] == "model-b"
    assert requested == ["model-a", "model-b"]


def test_concurrent_users_share_one_availability_probe(monkeypatch) -> None:
    calls = 0
    call_lock = threading.Lock()

    class SlowClient:
        def __init__(self, settings):
            self.settings = settings

        def generate(self, _messages):
            nonlocal calls
            with call_lock:
                calls += 1
            time.sleep(0.05)
            return ModelReply(
                message={"role": "assistant", "content": "OK"}, raw_response={},
                requested_model="model-a", resolved_model="model-a", provider="provider-a",
                usage={"total_tokens": 1}, finish_reason="stop", latency_ms=50,
            )

    monkeypatch.setenv("MODEL_A_KEY", "configured-for-test")
    monkeypatch.setattr(model_status, "OpenAICompatibleClient", SlowClient)
    model_status.clear_model_status_cache()
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(
            lambda _index: model_status.model_service_status([configured_model()], now=600.0),
            range(8),
        ))
    assert all(item["models"][0]["status"] == "online" for item in results)
    assert calls == 1

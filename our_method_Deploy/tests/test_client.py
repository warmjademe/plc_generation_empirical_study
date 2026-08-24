from __future__ import annotations

import urllib.error

import pytest

from plc_loop.client import OpenAICompatibleClient, ProviderSettings, is_retryable_model_error


def _settings() -> ProviderSettings:
    return ProviderSettings(
        name="test",
        base_url="https://example.test/v1",
        api_key_env="TEST_PROVIDER_API_KEY",
        requested_model="test-model",
        allowed_resolved_models=("test-model",),
        max_output_tokens=8192,
        thinking_mode="disabled",
    )


def test_generation_disables_thinking_and_rejects_reasoning_only_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_PROVIDER_API_KEY", "test-only")
    client = OpenAICompatibleClient(_settings())
    captured = {}

    def fake_request(payload):
        captured.update(payload)
        return {
            "model": "test-model",
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "",
                    "reasoning_content": "unfinished reasoning",
                },
                "finish_reason": "length",
            }],
            "usage": {
                "completion_tokens": 8192,
                "completion_tokens_details": {"reasoning_tokens": 8192},
            },
        }

    monkeypatch.setattr(client, "_request", fake_request)
    with pytest.raises(RuntimeError, match="8192 reasoning tokens.*no final assistant content"):
        client.generate([{"role": "user", "content": "generate ST"}])

    assert captured["thinking"] == {"type": "disabled"}


def test_anthropic_protocol_translates_messages_and_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_PROVIDER_API_KEY", "test-only")
    settings = ProviderSettings(
        name="anthropic-proxy",
        base_url="https://example.test/anthropic",
        api_key_env="TEST_PROVIDER_API_KEY",
        requested_model="claude-sonnet-5",
        allowed_resolved_models=("claude-sonnet-5",),
        api_protocol="anthropic",
        max_output_tokens=32,
    )
    client = OpenAICompatibleClient(settings)
    captured = {}

    def fake_request_json(url, payload, headers):
        captured.update({"url": url, "payload": payload, "headers": headers})
        return {
            "id": "msg_test",
            "model": "claude-sonnet-5",
            "stop_reason": "end_turn",
            "content": [{"type": "text", "text": "OK"}],
            "usage": {"input_tokens": 7, "output_tokens": 1},
        }

    monkeypatch.setattr(client, "_request_json", fake_request_json)
    reply = client.generate([
        {"role": "system", "content": "Return concise text."},
        {"role": "user", "content": "Reply OK"},
    ])

    assert captured["url"] == "https://example.test/anthropic/v1/messages"
    assert captured["payload"] == {
        "model": "claude-sonnet-5",
        "messages": [{"role": "user", "content": "Reply OK"}],
        "max_tokens": 32,
        "system": "Return concise text.",
    }
    assert captured["headers"]["anthropic-version"] == "2023-06-01"
    assert reply.message["content"] == "OK"
    assert reply.finish_reason == "stop"
    assert reply.usage["total_tokens"] == 8


def test_anthropic_streaming_configuration_is_rejected() -> None:
    with pytest.raises(ValueError, match="Anthropic streaming"):
        ProviderSettings.from_dict({
            "name": "anthropic-proxy",
            "base_url": "https://example.test/anthropic",
            "api_key_env": "TEST_PROVIDER_API_KEY",
            "requested_model": "claude-sonnet-5",
            "allowed_resolved_models": ["claude-sonnet-5"],
            "api_protocol": "anthropic",
            "stream": True,
        })


@pytest.mark.parametrize("message", [
    "provider returned empty assistant content (finish_reason='length')",
    "provider request failed after transport retries: HTTP 503",
    "provider stream ended before a complete assistant message",
])
def test_retryable_model_errors_are_classified(message: str) -> None:
    assert is_retryable_model_error(RuntimeError(message)) is True


def test_identity_error_is_not_retryable() -> None:
    assert is_retryable_model_error(
        RuntimeError("provider resolved unexpected model 'other'")
    ) is False


def test_transport_network_outage_uses_bounded_retries(monkeypatch) -> None:
    monkeypatch.setenv("TEST_PROVIDER_API_KEY", "test-only")
    settings = ProviderSettings(
        name="test", base_url="https://example.test/v1",
        api_key_env="TEST_PROVIDER_API_KEY", requested_model="model-a",
        allowed_resolved_models=("model-a",), transport_retries=2,
    )
    client = OpenAICompatibleClient(settings)
    calls = []

    def offline(*_args, **_kwargs):
        calls.append(1)
        raise urllib.error.URLError("network unreachable")

    monkeypatch.setattr("plc_loop.client.urllib.request.urlopen", offline)
    monkeypatch.setattr("plc_loop.client.time.sleep", lambda _seconds: None)
    with pytest.raises(RuntimeError, match="after transport retries"):
        client.generate([{"role": "user", "content": "test"}])
    assert len(calls) == 3


def test_transport_recovers_after_one_transient_disconnect(monkeypatch) -> None:
    monkeypatch.setenv("TEST_PROVIDER_API_KEY", "test-only")
    settings = ProviderSettings(
        name="test", base_url="https://example.test/v1",
        api_key_env="TEST_PROVIDER_API_KEY", requested_model="model-a",
        allowed_resolved_models=("model-a",), transport_retries=2,
    )
    client = OpenAICompatibleClient(settings)
    calls = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return (
                b'{"model":"model-a","choices":[{"message":{"role":"assistant",'
                b'"content":"OK"},"finish_reason":"stop"}],"usage":{}}'
            )

    def flaky(*_args, **_kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise urllib.error.URLError("temporary disconnect")
        return Response()

    monkeypatch.setattr("plc_loop.client.urllib.request.urlopen", flaky)
    monkeypatch.setattr("plc_loop.client.time.sleep", lambda _seconds: None)
    reply = client.generate([{"role": "user", "content": "test"}])
    assert reply.message["content"] == "OK"
    assert len(calls) == 2

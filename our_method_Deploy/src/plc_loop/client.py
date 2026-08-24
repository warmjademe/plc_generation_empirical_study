"""Minimal OpenAI/Anthropic client with explicit provider identity checks."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from .models import ModelReply
from .provider_control import ProviderControlSettings, provider_controller


_RETRYABLE_MODEL_ERROR_MARKERS = (
    "provider returned empty assistant content",
    "provider exhausted the output-token limit",
    "provider stream ended before a complete assistant message",
    "provider streaming request failed without retry",
    "provider request failed after transport retries",
    "provider http 429",
    "provider http 500",
    "provider http 502",
    "provider http 503",
    "provider http 504",
    "timed out",
    "timeout",
    "provider circuit is open",
    "provider concurrency queue timed out",
    "provider rate-limit queue timed out",
)


def is_retryable_model_error(exc: BaseException) -> bool:
    """Return whether a stateless call can safely be retried."""

    message = str(exc).lower()
    return any(marker in message for marker in _RETRYABLE_MODEL_ERROR_MARKERS)


class ModelClient(Protocol):
    def generate(self, messages: list[dict[str, Any]]) -> ModelReply: ...


@dataclass(frozen=True)
class ProviderSettings:
    name: str
    base_url: str
    api_key_env: str
    requested_model: str
    allowed_resolved_models: tuple[str, ...]
    api_protocol: str = "openai"
    timeout_seconds: int = 180
    max_output_tokens: int = 8192
    history_mode: str = "stateless"
    reasoning_effort: str | None = None
    thinking_mode: str | None = None
    transport_retries: int = 2
    stream: bool = False
    max_concurrency: int = 2
    requests_per_minute: int = 30
    provider_queue_timeout_seconds: float = 120.0
    circuit_failure_threshold: int = 3
    circuit_open_seconds: float = 60.0

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ProviderSettings":
        if "api_key" in value:
            raise ValueError("literal API keys are forbidden; use api_key_env")
        settings = cls(
            name=str(value["name"]),
            base_url=str(value["base_url"]).rstrip("/"),
            api_key_env=str(value["api_key_env"]),
            requested_model=str(value["requested_model"]),
            allowed_resolved_models=tuple(value.get("allowed_resolved_models", [value["requested_model"]])),
            api_protocol=str(value.get("api_protocol", "openai")),
            timeout_seconds=int(value.get("timeout_seconds", 180)),
            max_output_tokens=int(value.get("max_output_tokens", 8192)),
            history_mode=str(value.get("history_mode", "stateless")),
            reasoning_effort=value.get("reasoning_effort"),
            thinking_mode=value.get("thinking_mode"),
            transport_retries=int(value.get("transport_retries", 2)),
            stream=bool(value.get("stream", False)),
            max_concurrency=int(value.get("max_concurrency", 2)),
            requests_per_minute=int(value.get("requests_per_minute", 30)),
            provider_queue_timeout_seconds=float(
                value.get("provider_queue_timeout_seconds", 120.0)
            ),
            circuit_failure_threshold=int(value.get("circuit_failure_threshold", 3)),
            circuit_open_seconds=float(value.get("circuit_open_seconds", 60.0)),
        )
        if settings.history_mode not in {"stateless", "full"}:
            raise ValueError("history_mode must be stateless or full")
        if settings.api_protocol not in {"openai", "anthropic"}:
            raise ValueError("api_protocol must be openai or anthropic")
        if settings.api_protocol == "anthropic" and settings.stream:
            raise ValueError("Anthropic streaming is not supported by this deployment client")
        if settings.thinking_mode not in {None, "enabled", "disabled"}:
            raise ValueError("thinking_mode must be enabled, disabled, or omitted")
        if not settings.base_url.startswith("https://"):
            raise ValueError("provider base_url must use HTTPS")
        ProviderControlSettings(
            max_concurrency=settings.max_concurrency,
            requests_per_minute=settings.requests_per_minute,
            queue_timeout_seconds=settings.provider_queue_timeout_seconds,
            circuit_failure_threshold=settings.circuit_failure_threshold,
            circuit_open_seconds=settings.circuit_open_seconds,
        )
        return settings


class OpenAICompatibleClient:
    def __init__(self, settings: ProviderSettings):
        self.settings = settings
        self.api_key = os.environ.get(settings.api_key_env)
        if not self.api_key:
            raise RuntimeError(
                f"missing {settings.api_key_env}; refusing to call {settings.requested_model} "
                "or silently substitute another model"
            )
        control_settings = ProviderControlSettings(
            max_concurrency=settings.max_concurrency,
            requests_per_minute=settings.requests_per_minute,
            queue_timeout_seconds=settings.provider_queue_timeout_seconds,
            circuit_failure_threshold=settings.circuit_failure_threshold,
            circuit_open_seconds=settings.circuit_open_seconds,
        )
        self.controller = provider_controller(
            settings.name,
            settings.base_url,
            settings.requested_model,
            control_settings,
        )

    def _request_json(
        self, url: str, payload: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers=headers,
        )
        last_error: Exception | None = None
        for retry in range(self.settings.transport_retries + 1):
            retry_after = 0.0
            try:
                with urllib.request.urlopen(request, timeout=self.settings.timeout_seconds) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                message = exc.read().decode("utf-8", errors="replace")[:2000]
                last_error = RuntimeError(f"provider HTTP {exc.code}: {message}")
                if exc.code < 500 and exc.code != 429:
                    break
                try:
                    retry_after = float(exc.headers.get("Retry-After", "0"))
                except (TypeError, ValueError):
                    retry_after = 0.0
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = exc
            if retry < self.settings.transport_retries:
                time.sleep(max(retry_after, min(2**retry, 30)))
        raise RuntimeError(f"provider request failed after transport retries: {last_error}")

    def _request(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request_json(
            f"{self.settings.base_url}/chat/completions",
            payload,
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "plc-evidence-loop/0.1.0",
            },
        )

    def _anthropic_request(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        system_parts: list[str] = []
        native_messages: list[dict[str, str]] = []
        for message in messages:
            role = str(message.get("role", ""))
            content = message.get("content")
            if not isinstance(content, str):
                raise ValueError("Anthropic messages require string content")
            if role == "system":
                system_parts.append(content)
            elif role in {"user", "assistant"}:
                native_messages.append({"role": role, "content": content})
            else:
                raise ValueError(f"Anthropic messages do not support role {role!r}")
        if not native_messages:
            raise ValueError("Anthropic request has no user or assistant messages")
        payload: dict[str, Any] = {
            "model": self.settings.requested_model,
            "messages": native_messages,
            "max_tokens": self.settings.max_output_tokens,
        }
        if system_parts:
            payload["system"] = "\n\n".join(system_parts)
        response = self._request_json(
            f"{self.settings.base_url}/v1/messages",
            payload,
            {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
                "User-Agent": "plc-evidence-loop/0.1.0",
            },
        )
        text_parts: list[str] = []
        reasoning_parts: list[str] = []
        for block in response.get("content") or []:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text" and block.get("text") is not None:
                text_parts.append(str(block["text"]))
            elif block.get("type") == "thinking" and block.get("thinking") is not None:
                reasoning_parts.append(str(block["thinking"]))
        message: dict[str, Any] = {"role": "assistant", "content": "".join(text_parts)}
        if reasoning_parts:
            message["reasoning_content"] = "".join(reasoning_parts)
        native_usage = dict(response.get("usage") or {})
        input_tokens = int(native_usage.get("input_tokens", 0) or 0)
        output_tokens = int(native_usage.get("output_tokens", 0) or 0)
        finish_reason = {
            "end_turn": "stop",
            "stop_sequence": "stop",
            "max_tokens": "length",
        }.get(response.get("stop_reason"), response.get("stop_reason"))
        return {
            "id": response.get("id"),
            "model": response.get("model") or self.settings.requested_model,
            "choices": [{"index": 0, "message": message, "finish_reason": finish_reason}],
            "usage": {
                **native_usage,
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            },
            "anthropic_response": response,
        }

    def _stream_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Consume OpenAI SSE chunks and reconstruct one complete chat response."""
        url = f"{self.settings.base_url}/chat/completions"
        payload = {**payload, "stream": True, "stream_options": {"include_usage": True}}
        request = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "plc-evidence-loop/0.1.0",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.settings.timeout_seconds) as response:
                envelope: dict[str, Any] = {}
                content_parts: list[str] = []
                reasoning_parts: list[str] = []
                finish_reason: str | None = None
                usage: dict[str, Any] = {}
                saw_data = False
                saw_done = False
                for raw_line in response:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        saw_done = True
                        break
                    chunk = json.loads(data)
                    saw_data = True
                    for key in ("id", "object", "created", "model", "system_fingerprint"):
                        if chunk.get(key) is not None:
                            envelope[key] = chunk[key]
                    if chunk.get("usage"):
                        usage = dict(chunk["usage"])
                    for choice in chunk.get("choices") or []:
                        delta = choice.get("delta") or {}
                        if delta.get("content") is not None:
                            content_parts.append(str(delta["content"]))
                        if delta.get("reasoning_content") is not None:
                            reasoning_parts.append(str(delta["reasoning_content"]))
                        if choice.get("finish_reason") is not None:
                            finish_reason = str(choice["finish_reason"])
                if not saw_data or not saw_done or finish_reason is None:
                    raise RuntimeError("provider stream ended before a complete assistant message")
                message: dict[str, Any] = {
                    "role": "assistant",
                    "content": "".join(content_parts),
                }
                if reasoning_parts:
                    message["reasoning_content"] = "".join(reasoning_parts)
                return {
                    **envelope,
                    "choices": [{"index": 0, "message": message, "finish_reason": finish_reason}],
                    "usage": usage,
                    "stream_reconstructed": True,
                }
        except urllib.error.HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")[:2000]
            raise RuntimeError(f"provider HTTP {exc.code}: {message}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            # Streaming requests are never retried automatically: once accepted,
            # the upstream may bill or finish even if this connection is lost.
            raise RuntimeError(f"provider streaming request failed without retry: {exc}") from exc

    def _generate_admitted(self, messages: list[dict[str, Any]]) -> ModelReply:
        if self.settings.api_protocol == "anthropic":
            started = time.monotonic()
            response = self._anthropic_request(messages)
            latency_ms = int((time.monotonic() - started) * 1000)
            return self._model_reply(response, latency_ms)
        payload: dict[str, Any] = {
            "model": self.settings.requested_model,
            "messages": messages,
            "max_tokens": self.settings.max_output_tokens,
        }
        if self.settings.reasoning_effort:
            payload["reasoning_effort"] = self.settings.reasoning_effort
        if self.settings.thinking_mode:
            payload["thinking"] = {"type": self.settings.thinking_mode}
        started = time.monotonic()
        response = self._stream_request(payload) if self.settings.stream else self._request(payload)
        latency_ms = int((time.monotonic() - started) * 1000)
        return self._model_reply(response, latency_ms)

    def generate(self, messages: list[dict[str, Any]]) -> ModelReply:
        return self.controller.execute(
            lambda: self._generate_admitted(messages),
            is_retryable_model_error,
        )

    def _model_reply(self, response: dict[str, Any], latency_ms: int) -> ModelReply:
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0].get("message"), dict):
            raise RuntimeError("provider response has no assistant message")
        choice = choices[0]
        message = choice["message"]
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            finish_reason = choice.get("finish_reason")
            usage = response.get("usage") or {}
            completion_details = usage.get("completion_tokens_details") or {}
            reasoning_tokens = completion_details.get("reasoning_tokens")
            if finish_reason == "length" and reasoning_tokens:
                raise RuntimeError(
                    "provider exhausted the output-token limit in reasoning "
                    f"({reasoning_tokens} reasoning tokens) and returned no final assistant content"
                )
            raise RuntimeError(
                "provider returned empty assistant content "
                f"(finish_reason={finish_reason!r})"
            )
        resolved_model = str(response.get("model") or self.settings.requested_model)
        allowed = any(
            resolved_model == model or resolved_model.startswith(f"{model}-")
            for model in self.settings.allowed_resolved_models
        )
        if not allowed:
            raise RuntimeError(
                f"provider resolved unexpected model {resolved_model!r}; allowed={self.settings.allowed_resolved_models}"
            )
        return ModelReply(
            message=dict(message),
            raw_response=response,
            requested_model=self.settings.requested_model,
            resolved_model=resolved_model,
            provider=self.settings.name,
            usage=dict(response.get("usage") or {}),
            finish_reason=choice.get("finish_reason"),
            latency_ms=latency_ms,
        )

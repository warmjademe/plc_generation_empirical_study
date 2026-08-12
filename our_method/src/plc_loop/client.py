"""Minimal OpenAI-compatible client with explicit provider identity checks."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from .models import ModelReply


class ModelClient(Protocol):
    def generate(self, messages: list[dict[str, Any]]) -> ModelReply: ...


@dataclass(frozen=True)
class ProviderSettings:
    name: str
    base_url: str
    api_key_env: str
    requested_model: str
    allowed_resolved_models: tuple[str, ...]
    timeout_seconds: int = 180
    max_output_tokens: int = 8192
    history_mode: str = "stateless"
    reasoning_effort: str | None = None
    thinking_mode: str | None = None
    transport_retries: int = 2
    stream: bool = False

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
            timeout_seconds=int(value.get("timeout_seconds", 180)),
            max_output_tokens=int(value.get("max_output_tokens", 8192)),
            history_mode=str(value.get("history_mode", "stateless")),
            reasoning_effort=value.get("reasoning_effort"),
            thinking_mode=value.get("thinking_mode"),
            transport_retries=int(value.get("transport_retries", 2)),
            stream=bool(value.get("stream", False)),
        )
        if settings.history_mode not in {"stateless", "full"}:
            raise ValueError("history_mode must be stateless or full")
        if settings.thinking_mode not in {None, "enabled", "disabled"}:
            raise ValueError("thinking_mode must be enabled, disabled, or omitted")
        if not settings.base_url.startswith("https://"):
            raise ValueError("provider base_url must use HTTPS")
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

    def _request(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.settings.base_url}/chat/completions"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "plc-evidence-loop/0.1.0",
            },
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

    def generate(self, messages: list[dict[str, Any]]) -> ModelReply:
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
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0].get("message"), dict):
            raise RuntimeError("provider response has no assistant message")
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
            message=dict(choices[0]["message"]),
            raw_response=response,
            requested_model=self.settings.requested_model,
            resolved_model=resolved_model,
            provider=self.settings.name,
            usage=dict(response.get("usage") or {}),
            finish_reason=choices[0].get("finish_reason"),
            latency_ms=latency_ms,
        )

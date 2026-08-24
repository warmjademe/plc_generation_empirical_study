from __future__ import annotations

import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

from plc_loop.client import OpenAICompatibleClient, ProviderSettings


STATUS_CACHE_SECONDS = 300.0
FORCED_REFRESH_FLOOR_SECONDS = 30.0
PROBE_TIMEOUT_SECONDS = 12
_cache_lock = threading.Lock()
_cached_results: dict[tuple[tuple[str, str, str, str], ...], tuple[float, dict[str, Any]]] = {}
_probe_locks: dict[tuple[tuple[str, str, str, str], ...], threading.Lock] = {}


def _cache_key(models: list[dict[str, Any]]) -> tuple[tuple[str, str, str, str], ...]:
    return tuple(
        (
            str(model["id"]),
            str(model.get("base_url", "")),
            str(model.get("requested_model", "")),
            str(model.get("api_protocol", "openai")),
        )
        for model in models
    )


def _public_error(exc: Exception) -> str:
    text = re.sub(r"\s+", " ", str(exc)).strip()
    match = re.search(r"(?:HTTP|status(?: code)?)\s*(\d{3})", text, flags=re.IGNORECASE)
    if match:
        return f"上游服务返回 HTTP {match.group(1)}"
    lowered = text.casefold()
    if "timed out" in lowered or "timeout" in lowered:
        return "连接上游模型超时"
    if any(marker in lowered for marker in (
        "name resolution", "network unreachable", "connection refused",
        "connection reset", "urlopen error", "temporary failure in name",
    )):
        return "无法连接上游模型网络"
    if "ssl" in lowered or "certificate" in lowered:
        return "上游模型 HTTPS 连接失败"
    if "unexpected model" in lowered:
        return "上游返回的模型标识不匹配"
    return "模型实际推理探测失败"


def _probe_model(model: dict[str, Any]) -> dict[str, Any]:
    public = {
        "id": str(model["id"]),
        "label": str(model["label"]),
        "provider": str(model["provider"]),
        "api_protocol": str(model.get("api_protocol", "openai")),
        "requested_model": str(model["requested_model"]),
    }
    if not os.getenv(str(model["api_key_env"])):
        return {**public, "status": "unconfigured", "detail": "服务器未配置该模型的访问凭据"}

    probe = dict(model)
    probe["name"] = probe.pop("provider")
    for key in ("id", "label", "contract_thinking_mode", "reasoning_effort"):
        probe.pop(key, None)
    probe.update({
        "timeout_seconds": PROBE_TIMEOUT_SECONDS,
        "max_output_tokens": 8,
        # Availability checks must be fail-fast.  The real generation call has
        # its own bounded transport retries after a job has been accepted.
        "transport_retries": 0,
        "stream": False,
    })
    started = time.monotonic()
    try:
        reply = OpenAICompatibleClient(ProviderSettings.from_dict(probe)).generate([
            {"role": "system", "content": "This is a service availability probe. Reply only OK."},
            {"role": "user", "content": "OK"},
        ])
    except Exception as exc:
        return {
            **public,
            "status": "offline",
            "detail": _public_error(exc),
            "latency_ms": int((time.monotonic() - started) * 1000),
        }
    return {
        **public,
        "status": "online",
        "detail": "实际推理请求成功",
        "latency_ms": reply.latency_ms,
        "resolved_model": reply.resolved_model,
    }


def clear_model_status_cache() -> None:
    with _cache_lock:
        _cached_results.clear()


def model_service_status(
    models: list[dict[str, Any]], *, force: bool = False, now: float | None = None
) -> dict[str, Any]:
    current = time.monotonic() if now is None else now
    key = _cache_key(models)
    with _cache_lock:
        cached = _cached_results.get(key)
        cache_age = current - cached[0] if cached is not None else float("inf")
        minimum_age = FORCED_REFRESH_FLOOR_SECONDS if force else STATUS_CACHE_SECONDS
        if cached is not None and cache_age < minimum_age:
            return dict(cached[1])
        probe_lock = _probe_locks.setdefault(key, threading.Lock())

    # Only callers probing the same model set wait for each other.  Other model
    # channels remain independent, while a burst of user submissions is
    # coalesced into one paid availability request.
    with probe_lock:
        with _cache_lock:
            cached = _cached_results.get(key)
            cache_age = current - cached[0] if cached is not None else float("inf")
            if cached is not None and cache_age < minimum_age:
                return dict(cached[1])

        # Do not hold the global cache lock while a provider is slow/offline.
        with ThreadPoolExecutor(max_workers=max(1, min(4, len(models)))) as executor:
            futures = {executor.submit(_probe_model, dict(model)): model for model in models}
            results = [future.result() for future in as_completed(futures)]
        order = {str(model["id"]): index for index, model in enumerate(models)}
        results.sort(key=lambda item: order[item["id"]])
        result = {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "cache_seconds": int(STATUS_CACHE_SECONDS),
            "probe": "minimal_real_inference",
            "models": results,
        }
        with _cache_lock:
            _cached_results[key] = (current, result)
        return dict(result)

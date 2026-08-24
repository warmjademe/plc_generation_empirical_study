"""Provider admission control for the dedicated production task worker.

Web processes only enqueue durable jobs.  All contract and candidate requests
run in one separately supervised worker process and pass through this registry,
which prevents independent jobs from creating an upstream retry storm.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable, TypeVar


T = TypeVar("T")


class ProviderAdmissionError(RuntimeError):
    """Raised before a provider call when local admission control rejects it."""


@dataclass(frozen=True)
class ProviderControlSettings:
    max_concurrency: int = 2
    requests_per_minute: int = 30
    queue_timeout_seconds: float = 120.0
    circuit_failure_threshold: int = 3
    circuit_open_seconds: float = 60.0

    def __post_init__(self) -> None:
        if not 1 <= self.max_concurrency <= 32:
            raise ValueError("provider max_concurrency must be between 1 and 32")
        if not 1 <= self.requests_per_minute <= 600:
            raise ValueError("provider requests_per_minute must be between 1 and 600")
        if not 0.1 <= self.queue_timeout_seconds <= 3600:
            raise ValueError("provider queue_timeout_seconds must be between 0.1 and 3600")
        if not 1 <= self.circuit_failure_threshold <= 20:
            raise ValueError("provider circuit_failure_threshold must be between 1 and 20")
        if not 1 <= self.circuit_open_seconds <= 3600:
            raise ValueError("provider circuit_open_seconds must be between 1 and 3600")


class ProviderController:
    def __init__(self, settings: ProviderControlSettings):
        self.settings = settings
        self._slots = threading.BoundedSemaphore(settings.max_concurrency)
        self._lock = threading.Lock()
        self._recent_starts: list[float] = []
        self._consecutive_failures = 0
        self._circuit_open_until = 0.0

    def _admit_rate(self, deadline: float) -> None:
        while True:
            now = time.monotonic()
            with self._lock:
                if now < self._circuit_open_until:
                    remaining = self._circuit_open_until - now
                    raise ProviderAdmissionError(
                        f"provider circuit is open for another {remaining:.1f} seconds"
                    )
                cutoff = now - 60.0
                self._recent_starts = [item for item in self._recent_starts if item > cutoff]
                if len(self._recent_starts) < self.settings.requests_per_minute:
                    self._recent_starts.append(now)
                    return
                wait_for = max(0.01, self._recent_starts[0] + 60.0 - now)
            remaining = deadline - now
            if remaining <= 0 or wait_for > remaining:
                raise ProviderAdmissionError("provider rate-limit queue timed out")
            time.sleep(min(wait_for, 0.25))

    def execute(self, operation: Callable[[], T], retryable: Callable[[BaseException], bool]) -> T:
        deadline = time.monotonic() + self.settings.queue_timeout_seconds
        if not self._slots.acquire(timeout=self.settings.queue_timeout_seconds):
            raise ProviderAdmissionError("provider concurrency queue timed out")
        try:
            self._admit_rate(deadline)
            try:
                value = operation()
            except BaseException as exc:
                if retryable(exc):
                    with self._lock:
                        self._consecutive_failures += 1
                        if self._consecutive_failures >= self.settings.circuit_failure_threshold:
                            self._circuit_open_until = (
                                time.monotonic() + self.settings.circuit_open_seconds
                            )
                            self._consecutive_failures = 0
                raise
            with self._lock:
                self._consecutive_failures = 0
                self._circuit_open_until = 0.0
            return value
        finally:
            self._slots.release()


_REGISTRY_LOCK = threading.Lock()
_REGISTRY: dict[tuple[str, str, str], ProviderController] = {}


def provider_controller(
    provider: str,
    base_url: str,
    requested_model: str,
    settings: ProviderControlSettings,
) -> ProviderController:
    key = (provider, base_url, requested_model)
    with _REGISTRY_LOCK:
        controller = _REGISTRY.get(key)
        if controller is None or controller.settings != settings:
            controller = ProviderController(settings)
            _REGISTRY[key] = controller
        return controller


def reset_provider_controllers_for_test() -> None:
    with _REGISTRY_LOCK:
        _REGISTRY.clear()

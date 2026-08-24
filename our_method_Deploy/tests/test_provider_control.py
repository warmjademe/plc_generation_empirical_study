from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import math
from pathlib import Path
import threading
import time

import pytest

from plc_loop.provider_control import (
    ProviderAdmissionError,
    ProviderControlSettings,
    ProviderController,
)


def test_provider_controller_caps_concurrent_calls() -> None:
    controller = ProviderController(ProviderControlSettings(max_concurrency=2))
    lock = threading.Lock()
    active = 0
    maximum = 0

    def operation() -> str:
        nonlocal active, maximum
        with lock:
            active += 1
            maximum = max(maximum, active)
        time.sleep(0.03)
        with lock:
            active -= 1
        return "ok"

    with ThreadPoolExecutor(max_workers=6) as executor:
        results = list(executor.map(lambda _: controller.execute(operation, lambda _e: False), range(6)))

    assert results == ["ok"] * 6
    assert maximum == 2


def test_provider_controller_opens_and_recovers_circuit() -> None:
    controller = ProviderController(ProviderControlSettings(
        circuit_failure_threshold=2,
        circuit_open_seconds=1,
    ))

    def failure() -> None:
        raise RuntimeError("provider HTTP 503")

    for _ in range(2):
        with pytest.raises(RuntimeError, match="503"):
            controller.execute(failure, lambda _e: True)

    with pytest.raises(ProviderAdmissionError, match="circuit is open"):
        controller.execute(lambda: "should not run", lambda _e: True)


def test_non_retryable_failure_does_not_open_circuit() -> None:
    controller = ProviderController(ProviderControlSettings(circuit_failure_threshold=1))
    with pytest.raises(ValueError):
        controller.execute(lambda: (_ for _ in ()).throw(ValueError("bad input")), lambda _e: False)
    assert controller.execute(lambda: "ok", lambda _e: False) == "ok"


def test_production_provider_queue_covers_all_generation_worker_batches() -> None:
    catalog = json.loads(
        (Path(__file__).resolve().parents[1] / "configs/models.json").read_text(
            encoding="utf-8"
        )
    )
    production_workers = 4
    for model in catalog["models"]:
        waiting_batches = max(
            1,
            math.ceil(production_workers / int(model["max_concurrency"])) - 1,
        )
        assert float(model["provider_queue_timeout_seconds"]) >= (
            float(model["timeout_seconds"]) * waiting_batches
        )

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import pytest

from plc_deploy.store import JobStore
from plc_loop.cancellation import OperationCancelled
from plc_loop.process import run_captured


def test_store_cancellation_is_idempotent_and_preserves_terminal_job(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "service.db")
    store.create("queued", {"requirement": "test"})
    first = store.request_cancel("queued", "user stop")
    second = store.request_cancel("queued", "user stop again")
    assert first["status"] == second["status"] == "cancelled"
    assert second["cancel_requested"] is True

    store.create("done", {"requirement": "test"})
    store.update("done", status="verified_success")
    assert store.request_cancel("done", "too late")["status"] == "verified_success"


def test_run_captured_terminates_process_group_on_user_cancel(tmp_path: Path) -> None:
    cancelled = False

    def request_cancel() -> None:
        nonlocal cancelled
        time.sleep(0.1)
        cancelled = True

    thread = threading.Thread(target=request_cancel)
    thread.start()
    started = time.monotonic()
    with pytest.raises(OperationCancelled):
        run_captured(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            cwd=tmp_path,
            timeout=60,
            cancel_check=lambda: cancelled,
            cancel_poll_seconds=0.02,
        )
    thread.join()
    assert time.monotonic() - started < 3

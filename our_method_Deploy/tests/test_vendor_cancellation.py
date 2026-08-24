from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def load_validator_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts/dvp48es300r_validator.py"
    spec = importlib.util.spec_from_file_location("dvp_validator_under_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_linux_cancellation_marker_is_atomic_and_machine_readable(tmp_path: Path) -> None:
    module = load_validator_module()
    pending = tmp_path / "pending" / "job-1"
    pending.mkdir(parents=True)
    module.write_cancellation_marker(pending, "job-1", "test_shutdown")
    document = json.loads((pending / "cancelled.json").read_text(encoding="utf-8"))
    assert document["job_id"] == "job-1"
    assert document["status"] == "cancelled"
    assert document["reason"] == "test_shutdown"
    assert list(pending.glob("cancelled.json.tmp-*")) == []


def test_windows_worker_skips_and_rechecks_cancelled_jobs() -> None:
    root = Path(__file__).resolve().parents[1]
    worker = (root / "windows/Run-DvpValidationWorker.ps1").read_text(encoding="utf-8")
    assert "Join-Path $_.FullName 'cancelled.json'" in worker
    assert "Linux validator cancelled job" in worker
    assert "RuntimeCaseTimeoutSeconds = 90" in worker

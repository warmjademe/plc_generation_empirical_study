from pathlib import Path
from datetime import datetime, timedelta, timezone

from plc_deploy.store import JobStore
from plc_deploy.pipeline import _contract_resume_evidence


def test_restart_requeues_durable_stages_and_preserves_completed_jobs(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.db")
    statuses = [
        "contract_queued",
        "contract_generating",
        "awaiting_contract_approval",
        "generation_queued",
        "generating",
    ]
    for index, status in enumerate(statuses):
        job_id = f"active-{index}"
        store.create(job_id, {"requirement": "test"})
        store.update(job_id, status=status)
    store.create("done", {"requirement": "test"})
    store.update("done", status="verified_success")

    recovered = store.recover_interrupted()

    assert recovered["contract"] == ["active-0", "active-1"]
    assert recovered["approval"] == ["active-2"]
    assert recovered["generation"] == ["active-3", "active-4"]
    assert store.get("active-0")["status"] == "contract_queued"
    assert store.get("active-1")["status"] == "contract_queued"
    assert store.get("active-2")["status"] == "awaiting_contract_approval"
    assert store.get("active-3")["status"] == "generation_queued"
    assert store.get("active-4")["status"] == "generation_queued"
    assert store.get("done")["status"] == "verified_success"


def test_restart_finishes_a_pending_cancellation(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.db")
    store.create("running", {"requirement": "test"})
    store.update("running", status="generating")
    assert store.request_cancel("running", "user stop")["status"] == "cancelling"

    recovered = store.recover_interrupted()

    assert recovered["cancelled"] == ["running"]
    assert store.get("running")["status"] == "cancelled"


def test_durable_lease_prevents_duplicate_execution_and_allows_takeover(
    tmp_path: Path,
) -> None:
    store = JobStore(tmp_path / "jobs.db")
    store.create("job-1", {"requirement": "test"})

    first = store.claim_job("job-1", "contract", "worker-a", 300)
    duplicate = store.claim_job("job-1", "contract", "worker-b", 300)

    assert first is not None and first["status"] == "contract_generating"
    assert duplicate is None

    expired = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    with store._connect() as db:
        db.execute("UPDATE jobs SET lease_until=? WHERE id='job-1'", (expired,))

    takeover = store.claim_job("job-1", "contract", "worker-b", 300)
    assert takeover is not None
    assert store.renew_lease("job-1", "worker-a", 300) is False
    assert store.renew_lease("job-1", "worker-b", 300) is True


def test_abandoned_cancellation_is_finalized_after_lease_expiry(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.db")
    store.create("job-1", {"requirement": "test"})
    assert store.claim_job("job-1", "contract", "worker-a", 300) is not None
    assert store.request_cancel("job-1", "stop") ["status"] == "cancelling"

    assert store.finalize_abandoned_cancellations() == []
    expired = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    with store._connect() as db:
        db.execute("UPDATE jobs SET lease_until=? WHERE id='job-1'", (expired,))

    assert store.finalize_abandoned_cancellations() == ["job-1"]
    assert store.get("job-1")["status"] == "cancelled"


def test_contract_restart_recovers_consumed_budget_diagnostic_and_usage(
    tmp_path: Path,
) -> None:
    root = tmp_path / "job"
    root.mkdir()
    (root / "contract_progress.jsonl").write_text(
        "\n".join([
            '{"attempt":1,"status":"requesting"}',
            '{"attempt":1,"status":"received","usage":{"total_tokens":120},"latency_ms":17}',
            '{"attempt":1,"status":"rejected","error":"state/test contradiction"}',
            '{"attempt":2,"status":"requesting"}',
        ]) + "\n",
        encoding="utf-8",
    )
    (root / "contract_attempt_01_rejected.txt").write_text(
        '{"title":"draft"}\n', encoding="utf-8"
    )

    offset, usage, latency, draft, error = _contract_resume_evidence(root)

    assert offset == 2
    assert usage == {"total_tokens": 120}
    assert latency == 17
    assert draft == '{"title":"draft"}'
    assert error == "state/test contradiction"

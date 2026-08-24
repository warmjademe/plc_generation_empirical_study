from pathlib import Path

from plc_deploy import main
from plc_deploy.store import JobStore


def test_manual_and_auto_confirmation_enqueue_generation_only_once(
    tmp_path: Path, monkeypatch
) -> None:
    local_store = JobStore(tmp_path / "jobs.db")
    local_store.create("job-1", {"requirement": "test"})
    local_store.update(
        "job-1", status="awaiting_contract_approval", contract={
            "task_id": "PLC_JOB",
            "semantic_audit": {
                "status": "passed",
                "version": "deterministic-contract-semantics-v4",
                "traceability": {"status": "passed", "requirements_covered": 1},
            },
        }
    )
    submitted = []

    class FakeExecutor:
        def submit(self, *args):
            submitted.append(args)

    monkeypatch.setattr(main, "store", local_store)
    monkeypatch.setattr(main, "executor", FakeExecutor())

    first = main._queue_generation(
        "job-1", "auto_confirmed_llm_draft_after_5_seconds"
    )
    second = main._queue_generation("job-1", "user_confirmed_llm_draft")

    assert first["status"] == "generation_queued"
    assert second["status"] == "generation_queued"
    assert first["contract"]["oracle_provenance"] == (
        "auto_confirmed_llm_draft_after_5_seconds"
    )
    assert len(submitted) == 1


def test_confirmation_rejects_contract_without_current_semantic_audit(
    tmp_path: Path, monkeypatch
) -> None:
    local_store = JobStore(tmp_path / "jobs.db")
    local_store.create("job-1", {"requirement": "test"})
    local_store.update(
        "job-1", status="awaiting_contract_approval", contract={"task_id": "PLC_JOB"}
    )

    class FakeExecutor:
        def submit(self, *args):
            raise AssertionError("an unaudited contract must not start generation")

    monkeypatch.setattr(main, "store", local_store)
    monkeypatch.setattr(main, "executor", FakeExecutor())

    try:
        main._queue_generation("job-1", "user_confirmed_llm_draft")
    except ValueError as exc:
        assert "语义一致性审计" in str(exc)
    else:
        raise AssertionError("an unaudited contract was accepted")

    assert local_store.get("job-1")["status"] == "awaiting_contract_approval"

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from plc_deploy.store import JobStore


def test_store_lifecycle(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.db")
    created = store.create("job-1", {"requirement": "test"})
    assert created["status"] == "contract_queued"
    updated = store.update("job-1", status="awaiting_contract_approval", contract={"task_id": "PLC_JOB"})
    assert updated["contract"]["task_id"] == "PLC_JOB"


def test_store_allows_only_one_atomic_status_claim(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.db")
    store.create("job-1", {"requirement": "test"})
    store.update("job-1", status="awaiting_contract_approval", contract={"task_id": "PLC_JOB"})
    first = store.transition_status(
        "job-1", "awaiting_contract_approval", "generation_queued",
        contract={"task_id": "PLC_JOB", "oracle_provenance": "confirmed"},
    )
    second = store.transition_status("job-1", "awaiting_contract_approval", "generation_queued")
    assert first is not None and first["status"] == "generation_queued"
    assert second is None


def test_capacity_claim_is_atomic_under_concurrent_users(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.db")
    statuses = ("contract_queued", "contract_generating", "generating")

    def submit(number: int):
        return store.create_if_capacity(
            f"job-{number}", {"requirement": f"request-{number}"}, statuses, 8
        )

    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(submit, range(20)))
    accepted = [item for item in results if item is not None]
    assert len(accepted) == 8
    assert len({item[0]["id"] for item in accepted}) == 8
    assert all(created for _, created in accepted)
    assert store.count_statuses(statuses) == 8


def test_idempotent_concurrent_submission_creates_one_job(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.db")
    statuses = ("contract_queued", "contract_generating", "generating")

    def submit(number: int):
        return store.create_if_capacity(
            f"job-{number}", {"requirement": "same request"}, statuses, 8,
            idempotency_key="retry-key-1234", request_fingerprint="same-fingerprint",
        )

    with ThreadPoolExecutor(max_workers=6) as executor:
        results = list(executor.map(submit, range(6)))
    assert all(item is not None for item in results)
    assert len({item[0]["id"] for item in results if item is not None}) == 1
    assert sum(1 for item in results if item is not None and item[1]) == 1
    assert store.count_statuses(statuses) == 1


def test_job_remains_retrievable_after_web_process_reopens_database(tmp_path: Path) -> None:
    database = tmp_path / "jobs.db"
    first_process = JobStore(database)
    first_process.create("refresh-job", {"requirement": "persist this task"})
    first_process.update("refresh-job", status="generating")

    after_refresh = JobStore(database).get("refresh-job")

    assert after_refresh["id"] == "refresh-job"
    assert after_refresh["status"] == "generating"
    assert after_refresh["request"]["requirement"] == "persist this task"

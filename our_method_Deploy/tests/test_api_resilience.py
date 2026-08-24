from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from plc_deploy import main
from plc_deploy.store import JobStore


VALID_REQUEST = {
    "requirement": (
        "输入 Start、Stop 均为 BOOL；输出 Motor 为 BOOL。初始 Motor=FALSE。"
        "Start=TRUE 且 Stop=FALSE 时 Motor=TRUE；Stop=TRUE 时 Motor=FALSE；Stop 优先于 Start。"
    ),
    "vendor": "delta",
    "plc_model": "DVP48ES300R",
    "llm_model": "deepseek-v4-pro",
    "output_language": "st",
    "max_candidates": 20,
}


class FakeExecutor:
    def __init__(self) -> None:
        self.calls = []

    def submit(self, *args):
        self.calls.append(args)


@dataclass
class Response:
    status_code: int
    document: dict

    def json(self) -> dict:
        return self.document


async def asgi_request(
    method: str, path: str, *, body: dict | None = None,
    headers: dict[str, str] | None = None,
) -> Response:
    target = urlsplit(path)
    payload = json.dumps(body).encode("utf-8") if body is not None else b""
    raw_headers = [(b"content-type", b"application/json")]
    raw_headers.extend(
        (name.casefold().encode("ascii"), value.encode("utf-8"))
        for name, value in (headers or {}).items()
    )
    messages: list[dict] = []
    received = False

    async def receive() -> dict:
        nonlocal received
        if not received:
            received = True
            return {"type": "http.request", "body": payload, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message: dict) -> None:
        messages.append(message)

    await main.app(
        {
            "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
            "method": method, "scheme": "http", "path": target.path, "raw_path": target.path.encode(),
            "query_string": target.query.encode(), "root_path": "", "headers": raw_headers,
            "client": ("127.0.0.1", 12345), "server": ("test", 80),
        },
        receive,
        send,
    )
    start = next(item for item in messages if item["type"] == "http.response.start")
    raw = b"".join(item.get("body", b"") for item in messages if item["type"] == "http.response.body")
    return Response(start["status"], json.loads(raw.decode("utf-8")))


def configure(monkeypatch, tmp_path: Path, capacity: int = 8) -> FakeExecutor:
    executor = FakeExecutor()
    monkeypatch.setattr(main, "store", JobStore(tmp_path / "service.db"))
    monkeypatch.setattr(main, "executor", executor)
    monkeypatch.setattr(main, "settings", replace(main.settings, max_active_jobs=capacity))
    monkeypatch.setattr(main, "dvp_bridge_readiness", lambda _settings: {"ready": True})
    monkeypatch.setattr(
        main,
        "_selected_model_readiness",
        lambda model_id: {"id": model_id, "status": "online", "detail": "ok"},
    )
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-only")
    main.app.dependency_overrides[main.authorize] = lambda: None
    return executor


def test_browser_refresh_reads_same_server_side_job(monkeypatch, tmp_path: Path) -> None:
    executor = configure(monkeypatch, tmp_path)
    try:
        async def scenario() -> None:
            created = await asgi_request(
                "POST", "/api/jobs", body=VALID_REQUEST,
                headers={"Idempotency-Key": "refresh-window-1"},
            )
            assert created.status_code == 200
            job_id = created.json()["id"]

            # A page reload creates a new HTTP request, not a new PLC job.
            restored = await asgi_request("GET", f"/api/jobs/{job_id}")
            assert restored.status_code == 200
            assert restored.json()["id"] == job_id
            assert restored.json()["status"] == "contract_queued"
            assert len(executor.calls) == 1
        asyncio.run(scenario())
    finally:
        main.app.dependency_overrides.clear()


def test_task_center_lists_multiple_browser_owned_jobs_with_queue_positions(
    monkeypatch, tmp_path: Path
) -> None:
    configure(monkeypatch, tmp_path, capacity=8)
    try:
        async def scenario() -> None:
            created = [
                await asgi_request(
                    "POST", "/api/jobs", body=VALID_REQUEST,
                    headers={"Idempotency-Key": f"task-center-{index}"},
                )
                for index in range(3)
            ]
            ids = [response.json()["id"] for response in created]
            listed = await asgi_request("GET", f"/api/jobs?ids={','.join(ids)}")
            assert listed.status_code == 200
            document = listed.json()
            assert {job["id"] for job in document["jobs"]} == set(ids)
            assert sorted(job["queue_position"] for job in document["jobs"]) == [1, 2, 3]
            assert document["capacity"] == {
                "slots": main.settings.job_workers,
                "running": 0,
                "queued": 3,
                "accepted_limit": 8,
            }
            assert all("final_program" not in job for job in document["jobs"])
        asyncio.run(scenario())
    finally:
        main.app.dependency_overrides.clear()


def test_lost_post_response_is_recovered_idempotently_over_http(
    monkeypatch, tmp_path: Path
) -> None:
    executor = configure(monkeypatch, tmp_path)
    try:
        async def scenario() -> None:
            headers = {"Idempotency-Key": "lost-response-1"}
            first = await asgi_request("POST", "/api/jobs", body=VALID_REQUEST, headers=headers)
            replay = await asgi_request("POST", "/api/jobs", body=VALID_REQUEST, headers=headers)
            assert first.status_code == replay.status_code == 200
            assert first.json()["id"] == replay.json()["id"]
            assert len(executor.calls) == 1
        asyncio.run(scenario())
    finally:
        main.app.dependency_overrides.clear()


def test_concurrent_http_users_obey_atomic_capacity(monkeypatch, tmp_path: Path) -> None:
    executor = configure(monkeypatch, tmp_path, capacity=4)
    try:
        async def scenario() -> None:
            async def submit(index: int):
                return await asgi_request(
                    "POST", "/api/jobs", body=VALID_REQUEST,
                    headers={"Idempotency-Key": f"concurrent-user-{index}"},
                )

            responses = await asyncio.gather(*(submit(index) for index in range(10)))
            accepted = [response for response in responses if response.status_code == 200]
            rejected = [response for response in responses if response.status_code == 429]
            assert len(accepted) == 4
            assert len(rejected) == 6
            assert len({response.json()["id"] for response in accepted}) == 4
            assert all(
                response.json()["detail"]["code"] == "job_capacity_reached"
                for response in rejected
            )
            assert len(executor.calls) == 4
        asyncio.run(scenario())
    finally:
        main.app.dependency_overrides.clear()

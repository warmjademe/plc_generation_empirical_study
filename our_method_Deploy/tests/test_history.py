from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import HTTPException

from plc_deploy import main
from plc_deploy.store import JobStore


def request(
    title: str,
    *,
    plc_model: str = "DVP48ES300R",
    output_language: str = "st",
    llm_model: str = "deepseek-v4-pro",
) -> dict:
    return {
        "requirement": f"任务名称：{title}\n输入 Start，输出 Motor，Stop 优先。",
        "vendor": "delta",
        "plc_model": plc_model,
        "output_language": output_language,
        "llm_model": llm_model,
        "max_candidates": 20,
    }


def terminal_job(store: JobStore, payload: dict, *, program: str = "Motor := Start;") -> str:
    job_id = str(uuid.uuid4())
    store.create(job_id, payload)
    store.update(
        job_id,
        status="verified_success",
        result={"success": True, "output_language": payload["output_language"]},
        final_program=program,
    )
    return job_id


def test_server_history_supports_pagination_and_combined_filters(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "service.db")
    first = terminal_job(store, request("输送机联锁"), program="Conveyor := Start;")
    terminal_job(
        store,
        request(
            "阀门顺序",
            plc_model="AS228T-A",
            output_language="ld",
            llm_model="claude-sonnet-5-proxy",
        ),
        program="Valve := Enable;",
    )
    rows, total = store.list_history(
        page=1,
        page_size=1,
        plc_model="DVP48ES300R",
        output_language="st",
        llm_model="deepseek-v4-pro",
        search="输送机",
    )
    assert total == 1
    assert [item["id"] for item in rows] == [first]

    all_rows, all_total = store.list_history(page=1, page_size=1)
    assert len(all_rows) == 1
    assert all_total == 2


def test_archive_restore_retention_and_delete_are_terminal_only(tmp_path: Path) -> None:
    path = tmp_path / "service.db"
    store = JobStore(path)
    active_id = str(uuid.uuid4())
    store.create(active_id, request("运行中"))
    with pytest.raises(ValueError, match="active jobs"):
        store.archive_job(active_id)
    with pytest.raises(ValueError, match="active jobs"):
        store.delete_job(active_id)

    old_id = terminal_job(store, request("旧任务"))
    cutoff = datetime.now(timezone.utc) - timedelta(days=180)
    with sqlite3.connect(path) as db:
        db.execute(
            "UPDATE jobs SET created_at=? WHERE id=?",
            ((cutoff - timedelta(days=1)).isoformat(), old_id),
        )
    assert store.archive_expired(cutoff.isoformat()) == 1
    assert store.get(old_id)["archived_at"] is not None
    assert store.list_history(page=1, page_size=20, archive_scope="active")[1] == 1
    assert store.list_history(page=1, page_size=20, archive_scope="archived")[1] == 1

    restored = store.restore_job(old_id)
    assert restored["archived_at"] is None
    store.delete_job(old_id)
    with pytest.raises(KeyError):
        store.get(old_id)


def test_history_api_lists_details_and_moves_deleted_artifacts_to_trash(
    monkeypatch, tmp_path: Path
) -> None:
    store = JobStore(tmp_path / "service.db")
    job_id = terminal_job(store, request("历史查询"))
    job_root = tmp_path / "jobs" / job_id
    job_root.mkdir(parents=True)
    (job_root / "evidence.txt").write_text("validated", encoding="utf-8")
    monkeypatch.setattr(main, "store", store)
    monkeypatch.setattr(
        main,
        "settings",
        replace(main.settings, data_root=tmp_path, job_retention_days=180),
    )

    history = main.list_job_history(search="历史查询")
    assert history["pagination"]["total"] == 1
    assert history["jobs"][0]["request"]["requirement_title"] == "任务名称：历史查询"
    assert history["retention_days"] == 180

    archived = main.archive_history_job(job_id)
    assert archived["archived_at"] is not None
    assert main.restore_history_job(job_id)["archived_at"] is None
    deleted = main.delete_history_job(job_id)
    assert deleted == {
        "deleted": True,
        "job_id": job_id,
        "artifacts_moved_to_trash": True,
    }
    assert not job_root.exists()
    assert list((tmp_path / "trash" / "jobs").glob(f"*_{job_id}/evidence.txt"))


def test_history_api_rejects_invalid_dates_and_active_mutation(
    monkeypatch, tmp_path: Path
) -> None:
    store = JobStore(tmp_path / "service.db")
    job_id = str(uuid.uuid4())
    store.create(job_id, request("运行中"))
    monkeypatch.setattr(main, "store", store)
    monkeypatch.setattr(main, "settings", replace(main.settings, data_root=tmp_path))

    with pytest.raises(HTTPException) as invalid_date:
        main.list_job_history(date_from="2026-99-99")
    assert invalid_date.value.status_code == 400
    with pytest.raises(HTTPException) as active_archive:
        main.archive_history_job(job_id)
    assert active_archive.value.status_code == 409


def test_history_ui_and_postgres_migration_are_present() -> None:
    project = Path(__file__).resolve().parents[1]
    page = (project / "templates/app.html").read_text(encoding="utf-8")
    script = (project / "static/app.js").read_text(encoding="utf-8")
    style = (project / "static/style.css").read_text(encoding="utf-8")
    postgres = (project / "src/plc_deploy/postgres_store.py").read_text(encoding="utf-8")
    for element_id in (
        "historySearch",
        "historyPlcModel",
        "historyLanguage",
        "historyModel",
        "historyDateFrom",
        "historyDateTo",
        "historyArchive",
        "historyPrevious",
        "historyNext",
        "resultContract",
    ):
        assert f'id="{element_id}"' in page
    assert "/api/history" in script
    assert "archiveHistoryJob" in script
    assert "deleteHistoryJob" in script
    assert "title.title=title.textContent" in script
    assert ".task-card-head b { display:-webkit-box" in style
    assert "overflow-wrap:anywhere" in style
    assert "white-space:normal" in style
    assert "-webkit-line-clamp:3" in style
    assert "ADD COLUMN IF NOT EXISTS archived_at" in postgres
    assert "plc_job_schema_migration" in postgres
    assert "def list_history(" in postgres

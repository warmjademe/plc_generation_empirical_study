from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is required for the browser helper test")
def test_session_storage_job_id_survives_page_refresh() -> None:
    project = Path(__file__).resolve().parents[1]
    module = project / "static/job_recovery.js"
    script = f"""
const recovery=require({json.dumps(str(module))});
const values=new Map();
const storage={{setItem:(k,v)=>values.set(k,v),getItem:k=>values.get(k)||null,removeItem:k=>values.delete(k)}};
recovery.save(storage,'job-user-a');
if(recovery.load(storage)!=='job-user-a') process.exit(2);
recovery.clear(storage);
if(recovery.load(storage)!==null) process.exit(3);
recovery.saveSubmission(storage,'submission-key-1');
if(recovery.loadSubmission(storage)!=='submission-key-1') process.exit(4);
recovery.clearSubmission(storage);
if(recovery.loadSubmission(storage)!==null) process.exit(5);
const body={{requirement:'motor',vendor:'delta'}};
recovery.savePending(storage,'submission-key-2',body);
const pending=recovery.loadPending(storage);
if(!pending||pending.key!=='submission-key-2'||pending.request.requirement!=='motor') process.exit(6);
recovery.clearPending(storage);
if(recovery.loadPending(storage)!==null) process.exit(7);
const delays=[1,2,3,4,5,20].map(recovery.reconnectDelay);
if(JSON.stringify(delays)!==JSON.stringify([2000,4000,8000,16000,30000,30000])) process.exit(8);
"""
    subprocess.run(["node", "-e", script], check=True)


def test_web_client_restores_jobs_and_retries_after_network_loss() -> None:
    project = Path(__file__).resolve().parents[1]
    app = (project / "static/app.js").read_text(encoding="utf-8")
    page = (project / "templates/app.html").read_text(encoding="utf-8")
    assert "jobRecovery.save(sessionStorage,currentJob.id)" in app
    assert "async function resumeStoredJob()" in app
    assert "服务器任务不会因页面断网而取消" in app
    assert "scheduleReconnect(poll,delay)" in app
    assert "if(submissionBusy) return" in app
    assert "'Idempotency-Key':submissionKey" in app
    assert "jobRecovery.loadSubmission(sessionStorage)" in app
    assert "jobRecovery.savePending(sessionStorage,submissionKey,body)" in app
    assert "const pending=jobRecovery.loadPending(sessionStorage)" in app
    assert "pending.request" in app
    assert "scheduleReconnect(resumeStoredJob,delay)" in app
    assert "if(pollHandle) clearTimeout(pollHandle)" in app
    assert "jobRecovery.clearPending(sessionStorage)" in app
    assert "job_recovery.js" in page
    assert "const awaitingApproval=progress.phase==='awaiting_contract_approval'" in app
    assert "$('progressPanel').classList.toggle('hidden',awaitingApproval)" in app
    assert "$('contractDetails').open=false" in app
    assert 'id="contractDetails"' in page


def test_downloadable_approval_panel_has_explicit_scroll_and_sticky_action() -> None:
    project = Path(__file__).resolve().parents[1]
    style = (project / "static/style.css").read_text(encoding="utf-8")
    assert ".contract-review { max-height:calc(100vh - 48px); overflow-y:scroll" in style
    assert "touch-action:pan-y" in style
    assert ".approval-row { position:sticky; bottom:0" in style
    assert ".engineering-table-wrap { overflow-x:auto; overflow-y:visible; touch-action:pan-x pan-y" in style

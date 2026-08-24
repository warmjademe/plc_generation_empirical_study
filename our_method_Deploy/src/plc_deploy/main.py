from __future__ import annotations

import hmac
import base64
import hashlib
import json
import logging
import re
import threading
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .catalog import Catalog
from .auth_rate_limit import LoginRateLimiter
from .contracts import has_passed_semantic_audit
from plc_loop.delta_dvp import EngineeringConfigError, validate_engineering_config
from .model_status import model_service_status
from .pipeline import (
    create_contract_job,
    delta_validation_status,
    dvp_bridge_readiness,
    readiness,
    run_generation_job,
)
from .progress import build_job_progress
from .requirement_quality import assess_requirement, requirement_uses_numeric_types
from .schemas import ContractDecision, JobCreate, JobView, LoginRequest, RequirementCheck
from .settings import Settings
from .store import JobStore
from .store_factory import create_job_store


settings = Settings.load()
logger = logging.getLogger(__name__)
settings.data_root.mkdir(parents=True, exist_ok=True)
login_limiter = LoginRateLimiter(
    settings.auth_state_path,
    max_failures=settings.login_max_failures,
    window_seconds=settings.login_window_seconds,
    lockout_seconds=settings.login_lockout_seconds,
)
catalog = Catalog(settings.project_root / "configs")
store = create_job_store(settings.data_root, settings.database_url)
executor = ThreadPoolExecutor(max_workers=settings.job_workers, thread_name_prefix="plc-job")
execution_owner = f"web-{uuid.uuid4().hex}"
_scheduled_jobs: set[str] = set()
_scheduled_lock = threading.Lock()
_dispatcher_stop = threading.Event()
_dispatcher_thread: threading.Thread | None = None
INTERRUPTIBLE_JOB_STATUSES = (
    "contract_queued",
    "contract_generating",
    "awaiting_contract_approval",
    "generation_queued",
    "generating",
    "cancelling",
)
TERMINAL_JOB_STATUSES = (
    "verified_success",
    "generation_failed",
    "infrastructure_error",
    "contract_failed",
    "cancelled",
)
ALL_JOB_STATUSES = INTERRUPTIBLE_JOB_STATUSES + TERMINAL_JOB_STATUSES


def _lease_heartbeat(job_id: str, finished: threading.Event) -> None:
    interval = max(10.0, settings.job_lease_seconds / 3)
    while not finished.wait(interval):
        if not store.renew_lease(job_id, execution_owner, settings.job_lease_seconds):
            return


def _run_leased_job(job_id: str, stage: str) -> None:
    finished = threading.Event()
    heartbeat: threading.Thread | None = None
    try:
        if store.claim_job(job_id, stage, execution_owner, settings.job_lease_seconds) is None:
            return
        heartbeat = threading.Thread(
            target=_lease_heartbeat,
            args=(job_id, finished),
            name=f"plc-lease-{job_id[:8]}",
            daemon=True,
        )
        heartbeat.start()
        if stage == "contract":
            create_contract_job(
                job_id, store, catalog, settings,
                _auto_approve_contract, AUTO_APPROVAL_DELAY_SECONDS,
            )
        else:
            run_generation_job(job_id, store, catalog, settings)
    finally:
        finished.set()
        if heartbeat is not None:
            heartbeat.join(timeout=1)
        try:
            store.release_lease(job_id, execution_owner)
        except KeyError:
            pass
        with _scheduled_lock:
            _scheduled_jobs.discard(job_id)


def _schedule_job(job_id: str, stage: str) -> bool:
    with _scheduled_lock:
        if job_id in _scheduled_jobs:
            return False
        _scheduled_jobs.add(job_id)
    try:
        executor.submit(_run_leased_job, job_id, stage)
    except Exception:
        with _scheduled_lock:
            _scheduled_jobs.discard(job_id)
        raise
    return True


def _recover_after_process_restart() -> dict[str, list[str]]:
    """Schedule queued or expired leased stages without stealing live work."""

    recovered = {"contract": [], "approval": [], "generation": [], "cancelled": []}
    recovered["cancelled"] = store.finalize_abandoned_cancellations()
    for job_id in store.auto_approvable_jobs(AUTO_APPROVAL_DELAY_SECONDS):
        _auto_approve_contract(job_id)
        recovered["approval"].append(job_id)
    for job_id, stage in store.dispatchable_jobs(settings.job_workers * 4):
        if _schedule_job(job_id, stage):
            recovered[stage].append(job_id)
    return recovered


def _dispatcher_loop() -> None:
    last_error_log_at = 0.0
    while not _dispatcher_stop.is_set():
        try:
            _recover_after_process_restart()
        except Exception:
            # Readiness endpoints and persisted jobs remain available; the next
            # bounded poll retries database ownership without duplicating work.
            current = time.monotonic()
            if current - last_error_log_at >= 60:
                logger.exception("durable job dispatcher poll failed")
                last_error_log_at = current
        _dispatcher_stop.wait(settings.job_poll_seconds)


def _resume_auto_approval(job_id: str) -> None:
    deadline = time.monotonic() + AUTO_APPROVAL_DELAY_SECONDS
    while time.monotonic() < deadline:
        if store.cancellation_requested(job_id):
            return
        time.sleep(min(0.1, deadline - time.monotonic()))
    _auto_approve_contract(job_id)


@asynccontextmanager
async def lifespan(_: FastAPI):
    global _dispatcher_thread
    if not settings.run_background_jobs:
        yield
        return
    _dispatcher_stop.clear()
    _recover_after_process_restart()
    _dispatcher_thread = threading.Thread(
        target=_dispatcher_loop, name="plc-durable-dispatcher", daemon=True
    )
    _dispatcher_thread.start()
    yield
    _dispatcher_stop.set()
    if _dispatcher_thread is not None:
        _dispatcher_thread.join(timeout=max(1.0, settings.job_poll_seconds * 2))


app = FastAPI(
    title="PLC ST and Ladder Generation Service",
    version="0.3.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)
static_root = settings.project_root / "static"
template_root = settings.project_root / "templates"
app.mount("/static", StaticFiles(directory=static_root), name="static")
SESSION_COOKIE = "plc_session"
AUTO_APPROVAL_DELAY_SECONDS = 5.0


def _selected_model_readiness(model_id: str) -> dict:
    # Submission is the cost boundary.  Request a fresh-enough real inference
    # probe here instead of trusting the five-minute dashboard cache.  The
    # status module still coalesces probes submitted within its 30-second floor.
    snapshot = model_service_status([catalog.model(model_id)], force=True)
    match = next(
        (item for item in snapshot.get("models", []) if item.get("id") == model_id),
        None,
    )
    return match or {
        "id": model_id,
        "status": "offline",
        "detail": "模型状态探测没有返回所选通道",
    }


def _queue_generation(
    job_id: str,
    approval_source: str,
    engineering_config: dict | None = None,
) -> dict:
    job = store.get(job_id)
    if job["status"] in {
        "generation_queued", "generating", "verified_success", "generation_failed", "infrastructure_error"
    }:
        return job
    if job["status"] != "awaiting_contract_approval":
        raise ValueError(f"验证契约尚不可确认，当前任务状态为 {job['status']}")
    contract = dict(job["contract"] or {})
    if not has_passed_semantic_audit(contract):
        raise ValueError("验证契约未通过当前版本的确定性语义一致性审计")
    delivery_mode = str(job.get("request", {}).get("delivery_mode", "function_unit"))
    if delivery_mode == "downloadable_project":
        if engineering_config is None:
            raise ValueError("可下载工程必须先确认完整的物理 I/O 映射")
        try:
            contract["engineering_config"] = validate_engineering_config(
                engineering_config,
                contract,
                str(job["request"]["plc_model"]),
            )
        except EngineeringConfigError as exc:
            raise ValueError(f"工程配置无效：{exc}") from exc
        contract.pop("engineering_template", None)
    elif engineering_config is not None:
        raise ValueError("功能块交付不接受物理 I/O 工程配置")
    contract["oracle_provenance"] = approval_source
    claimed = store.transition_status(
        job_id, "awaiting_contract_approval", "generation_queued", contract=contract
    )
    if claimed is None:
        return store.get(job_id)
    if settings.run_background_jobs:
        _schedule_job(job_id, "generation")
    return claimed


def _auto_approve_contract(job_id: str) -> None:
    try:
        job = store.get(job_id)
        if job.get("request", {}).get("delivery_mode", "function_unit") == "downloadable_project":
            return
        _queue_generation(job_id, "auto_confirmed_llm_draft_after_5_seconds")
    except (KeyError, ValueError):
        return


def _make_session(username: str, now: int | None = None) -> str:
    issued = int(time.time() if now is None else now)
    payload = f"{username}:{issued + settings.session_ttl_seconds}".encode("utf-8")
    encoded = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    signature = hmac.new(
        settings.session_secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256
    ).hexdigest()
    return f"{encoded}.{signature}"


def _valid_session(token: str | None, now: int | None = None) -> bool:
    if not token or "." not in token:
        return False
    encoded, supplied_signature = token.rsplit(".", 1)
    expected_signature = hmac.new(
        settings.session_secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(supplied_signature, expected_signature):
        return False
    try:
        padded = encoded + "=" * (-len(encoded) % 4)
        username, expires_text = base64.urlsafe_b64decode(padded).decode("utf-8").rsplit(":", 1)
        expires = int(expires_text)
    except (ValueError, UnicodeDecodeError):
        return False
    current = int(time.time() if now is None else now)
    return hmac.compare_digest(username, settings.login_username) and current <= expires


def authorize(
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
) -> None:
    if _valid_session(request.cookies.get(SESSION_COOKIE)):
        return
    supplied = x_api_key or (authorization[7:] if authorization and authorization.startswith("Bearer ") else "")
    if settings.api_token and hmac.compare_digest(supplied, settings.api_token):
        return
    raise HTTPException(status_code=401, detail="authentication required")


@app.get("/", include_in_schema=False)
def index(request: Request) -> FileResponse:
    page = "app.html" if _valid_session(request.cookies.get(SESSION_COOKIE)) else "login.html"
    return FileResponse(template_root / page, headers={"Cache-Control": "no-store"})


def _login_identity(request: Request, username: str) -> str:
    peer = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("x-forwarded-for", "")
    if peer in {"127.0.0.1", "::1"} and forwarded:
        peer = forwarded.split(",", 1)[0].strip() or peer
    return f"{peer}:{username.casefold()}"


@app.post("/api/login")
def login(credentials: LoginRequest, request: Request) -> JSONResponse:
    identity = _login_identity(request, credentials.username)
    current = time.time()
    retry_after = login_limiter.retry_after(identity, now=current)
    if retry_after:
        raise HTTPException(
            status_code=429,
            detail="登录失败次数过多，请稍后重试",
            headers={"Retry-After": str(retry_after)},
        )
    accepted = hmac.compare_digest(credentials.username, settings.login_username) and hmac.compare_digest(
        credentials.password, settings.login_password
    )
    if not accepted:
        retry_after = login_limiter.record_failure(identity, now=current)
        if retry_after:
            raise HTTPException(
                status_code=429,
                detail="登录失败次数过多，请稍后重试",
                headers={"Retry-After": str(retry_after)},
            )
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    login_limiter.reset(identity, now=current)
    response = JSONResponse({"authenticated": True})
    response.set_cookie(
        SESSION_COOKIE,
        _make_session(credentials.username),
        httponly=True,
        secure=True,
        samesite="strict",
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@app.post("/api/logout")
def logout() -> JSONResponse:
    response = JSONResponse({"authenticated": False})
    response.delete_cookie(SESSION_COOKIE, path="/", secure=True, httponly=True, samesite="strict")
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/ready", dependencies=[Depends(authorize)])
def ready() -> dict:
    value = readiness(settings, catalog)
    if not value["ready"]:
        raise HTTPException(status_code=503, detail=value)
    return value


@app.get("/api/catalog", dependencies=[Depends(authorize)])
def get_catalog() -> dict:
    return {"vendors": catalog.vendors, "models": catalog.models,
            "defaults": {"vendor": "delta", "plc_model": "DVP48ES300R",
                         "llm_model": "deepseek-v4-pro", "output_language": "st"},
            "output_languages": [
                {"id": "st", "label": "Structured Text（ST）"},
                {
                    "id": "ld",
                    "label": "梯形图（LD）",
                    "native_targets": ["delta/DVP48ES300R", "delta/AS228T-A"],
                },
            ]}


@app.get("/api/validation-status", dependencies=[Depends(authorize)])
def get_validation_status() -> dict:
    return delta_validation_status(settings)


@app.get("/api/model-status", dependencies=[Depends(authorize)])
def get_model_status(refresh: bool = False) -> dict:
    return model_service_status(catalog.models, force=refresh)


@app.post("/api/requirements/check", dependencies=[Depends(authorize)])
def check_requirement(request: RequirementCheck) -> dict:
    return assess_requirement(request.requirement)


def _submission_identity(request: JobCreate, supplied_key: object) -> tuple[str | None, str]:
    fingerprint = hashlib.sha256(
        json.dumps(
            request.model_dump(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    key = supplied_key.strip() if isinstance(supplied_key, str) else ""
    if not key:
        return None, fingerprint
    if len(key) > 128 or not re.fullmatch(r"[A-Za-z0-9._:-]{8,128}", key):
        raise HTTPException(status_code=422, detail={
            "code": "invalid_idempotency_key",
            "message": "Idempotency-Key 必须为 8–128 位字母、数字、点、下划线、冒号或连字符。",
        })
    return key, fingerprint


@app.post("/api/jobs", response_model=JobView, dependencies=[Depends(authorize)])
def create_job(
    request: JobCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    submission_key, request_fingerprint = _submission_identity(request, idempotency_key)
    try:
        catalog.target(request.vendor, request.plc_model)
        model = catalog.model(request.llm_model)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={
            "code": "unsupported_configuration",
            "message": str(exc),
        }) from exc
    if request.output_language == "ld" and requirement_uses_numeric_types(request.requirement):
        raise HTTPException(status_code=422, detail={
            "code": "unsupported_ladder_interface",
            "message": (
                "当前台达原生梯形图导出器只校准 BOOL 接口；检测到 INT 或 REAL。"
                "请改用 Structured Text，或将需求改写为布尔触点/线圈控制。"
            ),
        })
    quality = assess_requirement(request.requirement)
    if not quality["ready"]:
        raise HTTPException(status_code=422, detail={
            "code": "requirement_needs_clarification",
            **quality,
        })
    if submission_key is not None:
        try:
            existing = store.get_by_idempotency(submission_key, request_fingerprint)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail={
                "code": "idempotency_conflict",
                "message": str(exc),
            }) from exc
        if existing is not None:
            return existing
    if request.output_language == "ld" and (
        request.vendor != "delta"
        or request.plc_model not in {"DVP48ES300R", "AS228T-A"}
    ):
        raise HTTPException(
            status_code=422,
            detail="原生梯形图目前仅校准并开放于台达 DVP48ES300R 和 AS228T-A；请选择支持的型号或改用 ST。",
        )
    if request.vendor == "delta" and request.plc_model in {"DVP48ES300R", "AS228T-A"}:
        bridge = dvp_bridge_readiness(settings)
        target_map = bridge.get("targets_ready")
        target_ready = (
            bool(target_map.get(request.plc_model))
            if isinstance(target_map, dict)
            else bool(
                bridge.get("ready")
                and (
                    request.plc_model == "DVP48ES300R"
                    or bridge.get("as228t_template_ready", True)
                )
            )
        )
        if not target_ready:
            raise HTTPException(
                status_code=503,
                detail={
                    "message": f"{request.plc_model} ISPSoft/COMMGR validation worker is not ready",
                    "bridge": bridge,
                },
            )
    if not __import__("os").getenv(model["api_key_env"]):
        raise HTTPException(status_code=503, detail={
            "code": "model_unconfigured",
            "message": f"所选模型 {model['label']} 尚未配置服务端访问凭据。",
            "model": request.llm_model,
            "retryable": False,
        })
    model_state = _selected_model_readiness(request.llm_model)
    if model_state.get("status") != "online":
        raise HTTPException(status_code=503, detail={
            "code": "model_unavailable",
            "message": (
                f"所选模型 {model['label']} 当前不可用；任务尚未创建，也没有产生模型费用。"
            ),
            "model": request.llm_model,
            "status": model_state.get("status", "offline"),
            "reason": model_state.get("detail", "模型推理探测失败"),
            "retryable": True,
        })
    job_id = str(uuid.uuid4())
    try:
        claimed = store.create_if_capacity(
            job_id,
            request.model_dump(),
            INTERRUPTIBLE_JOB_STATUSES,
            settings.max_active_jobs,
            idempotency_key=submission_key,
            request_fingerprint=request_fingerprint,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={
            "code": "idempotency_conflict",
            "message": str(exc),
        }) from exc
    if claimed is None:
        raise HTTPException(status_code=429, detail={
            "code": "job_capacity_reached",
            "message": (
                f"当前已有 {settings.max_active_jobs} 个任务在生成或排队；"
                "请等待任一任务结束后重新提交。"
            ),
            "retryable": True,
        })
    job, created = claimed
    if created and settings.run_background_jobs:
        _schedule_job(job_id, "contract")
    return job


@app.get("/api/jobs", dependencies=[Depends(authorize)])
def list_tracked_jobs(ids: str = "") -> dict:
    """Return a bounded dashboard view for job ids owned by this browser.

    The UI persists only opaque UUIDs that it created.  Keeping the requested
    id list client-side avoids exposing one customer's task catalogue to every
    authenticated browser while still allowing a refreshed page to recover
    multiple concurrent and completed jobs.
    """

    requested: list[str] = []
    for value in ids.split(","):
        value = value.strip()
        if not value or value in requested:
            continue
        try:
            uuid.UUID(value)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="invalid job id") from exc
        requested.append(value)
    if len(requested) > 50:
        raise HTTPException(status_code=400, detail="at most 50 job ids may be listed")

    dispatchable = [job_id for job_id, _ in store.dispatchable_jobs(settings.max_active_jobs)]
    queue_positions = {job_id: index + 1 for index, job_id in enumerate(dispatchable)}
    jobs: list[dict] = []
    for job_id in requested:
        try:
            job = store.get(job_id)
        except KeyError:
            continue
        progress = build_job_progress(job, settings.data_root)
        assignment_path = settings.data_root / "jobs" / job_id / "windows_worker_assignment.json"
        assignment: dict = {}
        try:
            loaded = json.loads(assignment_path.read_text(encoding="utf-8-sig"))
            if isinstance(loaded, dict):
                assignment = loaded
        except (OSError, json.JSONDecodeError):
            pass
        request = dict(job.get("request") or {})
        requirement_title = next(
            (line.strip() for line in str(request.get("requirement", "")).splitlines() if line.strip()),
            "PLC 控制任务",
        )
        jobs.append({
            "id": job["id"],
            "status": job["status"],
            "created_at": job.get("created_at"),
            "updated_at": job.get("updated_at"),
            "request": {
                "requirement_title": requirement_title[:160],
                "plc_model": request.get("plc_model"),
                "output_language": request.get("output_language"),
                "llm_model": request.get("llm_model"),
            },
            "queue_position": queue_positions.get(job_id),
            "progress_summary": {
                key: progress.get(key)
                for key in (
                    "phase", "message", "phase_percent", "current_attempt",
                    "candidate_budget", "active", "current_component",
                    "elapsed_seconds", "idle_seconds", "health",
                )
            },
            "windows_worker": assignment.get("worker_id"),
            "windows_target": assignment.get("target"),
        })
    jobs.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
    running_statuses = ("contract_generating", "generating")
    queued_statuses = ("contract_queued", "generation_queued")
    return {
        "jobs": jobs,
        "capacity": {
            "slots": settings.job_workers,
            "running": store.count_statuses(running_statuses),
            "queued": store.count_statuses(queued_statuses),
            "accepted_limit": settings.max_active_jobs,
        },
    }


def _history_date_bounds(
    date_from: str | None, date_to: str | None
) -> tuple[str | None, str | None]:
    try:
        lower = (
            datetime.combine(date.fromisoformat(date_from), datetime.min.time(), timezone.utc)
            if date_from else None
        )
        upper = (
            datetime.combine(
                date.fromisoformat(date_to) + timedelta(days=1),
                datetime.min.time(),
                timezone.utc,
            )
            if date_to else None
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="日期必须使用 YYYY-MM-DD 格式") from exc
    if lower and upper and lower >= upper:
        raise HTTPException(status_code=400, detail="开始日期不能晚于结束日期")
    return lower.isoformat() if lower else None, upper.isoformat() if upper else None


def _history_statuses(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    groups = {
        "active": INTERRUPTIBLE_JOB_STATUSES,
        "success": ("verified_success",),
        "failed": (
            "generation_failed", "infrastructure_error", "contract_failed", "cancelled"
        ),
        "ended": TERMINAL_JOB_STATUSES,
    }
    if value in groups:
        return tuple(groups[value])
    values = tuple(dict.fromkeys(item.strip() for item in value.split(",") if item.strip()))
    if not values or any(item not in ALL_JOB_STATUSES for item in values):
        raise HTTPException(status_code=400, detail="历史状态筛选值无效")
    return values


def _history_summary(job: dict, queue_positions: dict[str, int]) -> dict:
    request = dict(job.get("request") or {})
    requirement = str(request.get("requirement", ""))
    title = next((line.strip() for line in requirement.splitlines() if line.strip()), "PLC 控制任务")
    assignment_path = settings.data_root / "jobs" / job["id"] / "windows_worker_assignment.json"
    assignment: dict = {}
    try:
        loaded = json.loads(assignment_path.read_text(encoding="utf-8-sig"))
        if isinstance(loaded, dict):
            assignment = loaded
    except (OSError, json.JSONDecodeError):
        pass
    active = job["status"] in INTERRUPTIBLE_JOB_STATUSES
    progress = (
        build_job_progress(store.get(job["id"]), settings.data_root)
        if active else {
            "phase": job["status"],
            "message": job["status"],
            "phase_percent": 100,
            "active": False,
            "current_component": "任务已结束",
            "elapsed_seconds": max(
                0,
                int((
                    datetime.fromisoformat(str(job["updated_at"]))
                    - datetime.fromisoformat(str(job["created_at"]))
                ).total_seconds()),
            ),
        }
    )
    return {
        "id": job["id"],
        "status": job["status"],
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
        "archived_at": job.get("archived_at"),
        "request": {
            "requirement_title": title[:160],
            "requirement_preview": requirement[:300],
            "plc_model": request.get("plc_model"),
            "output_language": request.get("output_language"),
            "llm_model": request.get("llm_model"),
        },
        "queue_position": queue_positions.get(job["id"]),
        "progress_summary": {
            key: progress.get(key)
            for key in (
                "phase", "message", "phase_percent", "current_attempt",
                "candidate_budget", "active", "current_component", "elapsed_seconds",
                "idle_seconds", "health",
            )
        },
        "windows_worker": assignment.get("worker_id"),
        "windows_target": assignment.get("target"),
    }


@app.get("/api/history", dependencies=[Depends(authorize)])
def list_job_history(
    page: int = 1,
    page_size: int = 12,
    status: str | None = None,
    plc_model: str | None = None,
    output_language: str | None = None,
    llm_model: str | None = None,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    archive: str = "active",
) -> dict:
    """Return the single-user server-side PLC generation history."""

    if page < 1 or page_size < 1 or page_size > 50:
        raise HTTPException(status_code=400, detail="分页参数超出允许范围")
    if search is not None and len(search) > 200:
        raise HTTPException(status_code=400, detail="搜索关键词不能超过 200 个字符")
    if archive not in {"active", "archived", "all"}:
        raise HTTPException(status_code=400, detail="归档筛选值无效")
    created_from, created_to = _history_date_bounds(date_from, date_to)
    if settings.job_retention_days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.job_retention_days)
        store.archive_expired(cutoff.isoformat())
    jobs, total = store.list_history(
        page=page,
        page_size=page_size,
        statuses=_history_statuses(status),
        plc_model=plc_model or None,
        output_language=output_language or None,
        llm_model=llm_model or None,
        search=(search or "").strip() or None,
        created_from=created_from,
        created_to=created_to,
        archive_scope=archive,
    )
    dispatchable = [job_id for job_id, _ in store.dispatchable_jobs(settings.max_active_jobs)]
    queue_positions = {job_id: index + 1 for index, job_id in enumerate(dispatchable)}
    pages = max(1, (total + page_size - 1) // page_size)
    return {
        "jobs": [_history_summary(job, queue_positions) for job in jobs],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": pages,
        },
        "capacity": {
            "slots": settings.job_workers,
            "running": store.count_statuses(("contract_generating", "generating")),
            "queued": store.count_statuses(("contract_queued", "generation_queued")),
            "accepted_limit": settings.max_active_jobs,
        },
        "retention_days": settings.job_retention_days,
    }


def _history_mutation_error(exc: Exception) -> HTTPException:
    if isinstance(exc, KeyError):
        return HTTPException(status_code=404, detail="job not found")
    return HTTPException(status_code=409, detail=str(exc))


@app.post("/api/history/{job_id}/archive", response_model=JobView, dependencies=[Depends(authorize)])
def archive_history_job(job_id: str) -> dict:
    try:
        uuid.UUID(job_id)
        return store.archive_job(job_id)
    except (KeyError, ValueError) as exc:
        raise _history_mutation_error(exc) from exc


@app.post("/api/history/{job_id}/restore", response_model=JobView, dependencies=[Depends(authorize)])
def restore_history_job(job_id: str) -> dict:
    try:
        uuid.UUID(job_id)
        return store.restore_job(job_id)
    except (KeyError, ValueError) as exc:
        raise _history_mutation_error(exc) from exc


@app.delete("/api/history/{job_id}", dependencies=[Depends(authorize)])
def delete_history_job(job_id: str) -> dict:
    try:
        uuid.UUID(job_id)
        job = store.get(job_id)
        if job["status"] not in TERMINAL_JOB_STATUSES:
            raise ValueError("active jobs cannot be deleted")
    except (KeyError, ValueError) as exc:
        raise _history_mutation_error(exc) from exc

    job_root = settings.data_root / "jobs" / job_id
    moved_to: Path | None = None
    if job_root.is_dir():
        trash_root = settings.data_root / "trash" / "jobs"
        trash_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        moved_to = trash_root / (
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + job_id
        )
        job_root.replace(moved_to)
    try:
        store.delete_job(job_id)
    except (KeyError, ValueError) as exc:
        if moved_to is not None and moved_to.exists() and not job_root.exists():
            moved_to.replace(job_root)
        raise _history_mutation_error(exc) from exc
    return {"deleted": True, "job_id": job_id, "artifacts_moved_to_trash": moved_to is not None}


@app.get("/api/jobs/{job_id}", response_model=JobView, dependencies=[Depends(authorize)])
def get_job(job_id: str) -> dict:
    try:
        return store.get(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="job not found") from exc


@app.get("/api/jobs/{job_id}/progress", dependencies=[Depends(authorize)])
def get_job_progress(job_id: str) -> dict:
    try:
        job = store.get(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="job not found") from exc
    return build_job_progress(job, settings.data_root)


@app.post("/api/jobs/{job_id}/cancel", response_model=JobView, dependencies=[Depends(authorize)])
def cancel_job(job_id: str) -> dict:
    try:
        return store.request_cancel(job_id, "用户主动取消了生成任务")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="job not found") from exc


@app.get("/api/jobs/{job_id}/artifacts/{kind}", dependencies=[Depends(authorize)])
def get_job_artifact(job_id: str, kind: str) -> FileResponse:
    try:
        job = store.get(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="job not found") from exc
    allowed = {
        "st": ("candidate.st", "text/plain; charset=utf-8", "program.st"),
        "ld-json": ("candidate.ld.json", "application/json", "ladder.ld.json"),
        "ld-svg": ("candidate.ld.svg", "image/svg+xml", "ladder.svg"),
        "lowered-st": ("candidate.st", "text/plain; charset=utf-8", "ladder-equivalent.st"),
        "ispsoft-fbu": (
            "candidate.ISPSoft.FBU",
            "application/octet-stream",
            (
                "ladder" if job.get("request", {}).get("output_language") == "ld" else "st"
            ) + f"_{job.get('request', {}).get('plc_model', 'Delta')}.FBU",
        ),
        "delivery-manifest": (
            "delivery_manifest.json",
            "application/json",
            f"{job.get('request', {}).get('plc_model', 'PLC')}_validation_manifest.json",
        ),
        "ispsoft-project": (
            "downloadable_project.zip",
            "application/zip",
            f"{job.get('request', {}).get('plc_model', 'Delta')}_ISPSoft_project.zip",
        ),
        "engineering-mapping": (
            "engineering_mapping.json",
            "application/json",
            f"{job.get('request', {}).get('plc_model', 'Delta')}_IO_mapping.json",
        ),
        "deployment-main": (
            "deployment_main.st",
            "text/plain; charset=utf-8",
            "MAIN.st",
        ),
        "field-checklist": (
            "field_acceptance_checklist.json",
            "application/json",
            "physical_PLC_acceptance_checklist.json",
        ),
    }
    artifact = allowed.get(kind)
    advertised = {
        str(item.get("kind")) for item in (job.get("result") or {}).get("artifacts", [])
        if isinstance(item, dict)
    }
    if artifact is None or kind not in advertised:
        raise HTTPException(status_code=404, detail="artifact not found")
    attempts_root = settings.data_root / "jobs" / job_id / "run" / "attempts"
    final_attempt = (job.get("result") or {}).get("final_attempt")
    selected = (
        attempts_root / f"attempt_{int(final_attempt):02d}" / artifact[0]
        if isinstance(final_attempt, int)
        else None
    )
    if selected is None or not selected.is_file():
        matches = sorted(attempts_root.glob(f"attempt_*/{artifact[0]}"))
        selected = matches[-1] if matches else None
    if selected is None:
        raise HTTPException(status_code=404, detail="artifact not found")
    return FileResponse(selected, media_type=artifact[1], filename=artifact[2])


@app.post("/api/jobs/{job_id}/approve", response_model=JobView, dependencies=[Depends(authorize)])
def approve_contract(job_id: str, decision: ContractDecision) -> dict:
    try:
        return _queue_generation(
            job_id,
            "user_confirmed_llm_draft",
            decision.engineering_config,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="job not found") from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc


def run() -> None:
    uvicorn.run("plc_deploy.main:app", host=settings.host, port=settings.port,
                workers=settings.web_workers, proxy_headers=True)


if __name__ == "__main__":
    run()

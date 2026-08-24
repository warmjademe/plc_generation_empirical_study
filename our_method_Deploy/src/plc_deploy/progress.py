from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts import CONTRACT_ATTEMPT_BUDGET


GATE_LABELS = {
    "model": "大语言模型生成",
    "response_format": "响应格式检查",
    "interface": "接口检查",
    "compiler": "MatIEC 编译",
    "plcverif": "PLCverif 形式验证",
    "openplc_feedback": "OpenPLC 功能测试",
    "openplc_confirmation": "OpenPLC 确认测试",
    "openplc": "OpenPLC 确认测试",
    "dvp48es300r": "ISPSoft/COMMGR DVP48ES300R 验证",
    "as228t": "ISPSoft/COMMGR AS228T-A 验证",
    "candidate_novelty": "候选重复检查",
}
STATUS_LABELS = {
    "pass": "通过",
    "fail": "未通过",
    "inconclusive": "未得到确定结论",
    "skipped": "跳过",
}
VENDOR_PHASE_LABELS = {
    "queued": "等待 Windows 验证 worker",
    "input_check": "核对候选与测试包完整性",
    "project_load": "装载 ISPSoft 干净工程",
    "communication_setup": "绑定 COMMGR 通信驱动",
    "program_import": "导入生成程序与测试 harness",
    "ispsoft_compile": "使用 ISPSoft 编译工程",
    "controller_download": "下载程序到仿真控制器",
    "commgr_runtime": "通过 COMMGR 执行仿真输入",
    "oracle_evaluation": "判定当前仿真用例输出",
    "result_publish": "回传厂商验证证据",
    "complete": "厂商验证已完成",
}


def _timestamp(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _contract_events(path: Path) -> tuple[list[dict[str, str]], int, int]:
    events: list[dict[str, str]] = []
    current_attempt = 0
    maximum_attempts = CONTRACT_ATTEMPT_BUDGET
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return events, current_attempt, maximum_attempts
    for line in lines:
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        attempt = int(item.get("attempt", 0))
        maximum_attempts = max(
            maximum_attempts,
            int(item.get("maximum_attempts", CONTRACT_ATTEMPT_BUDGET)),
        )
        current_attempt = max(current_attempt, attempt)
        status = str(item.get("status", ""))
        if status == "preparing":
            message, event_status = "正在装载目标控制器约束并构造验证契约请求", "info"
        elif status == "requesting":
            message, event_status = (
                f"验证契约 {attempt}/{maximum_attempts}：已进入模型调用队列，"
                "正在等待调用名额或模型返回",
                "running",
            )
        elif status == "received":
            latency = int(item.get("latency_ms", 0))
            usage = item.get("usage") if isinstance(item.get("usage"), dict) else {}
            tokens = usage.get("total_tokens")
            suffix = f"，耗时 {latency / 1000:.1f} 秒" if latency else ""
            suffix += f"，{tokens} tokens" if tokens is not None else ""
            message, event_status = f"验证契约 {attempt}/{maximum_attempts}：模型响应已完整接收{suffix}", "pass"
        elif status == "validating":
            message, event_status = f"验证契约 {attempt}/{maximum_attempts}：正在执行 JSON、接口、性质和测试结构检查", "running"
        elif status == "accepted":
            message, event_status = f"验证契约 {attempt}/{maximum_attempts}：结构检查通过", "pass"
        elif status == "blind_rebuild":
            message, event_status = (
                f"验证契约 {attempt}/{maximum_attempts}：连续修正未通过，正从原始需求重新构建",
                "inconclusive",
            )
        elif status == "rejected":
            error = str(item.get("error", "格式不符合要求"))[:180]
            if item.get("error_kind") == "provider_retryable":
                message, event_status = (
                    f"验证契约 {attempt}/{maximum_attempts}：模型响应未完整返回，系统将自动使用下一次机会；{error}",
                    "inconclusive",
                )
            else:
                message, event_status = f"验证契约 {attempt}/{maximum_attempts}：结构检查未通过；{error}", "fail"
        else:
            continue
        events.append({"time": str(item.get("time") or datetime.now(timezone.utc).isoformat()),
                       "status": event_status, "message": message})
    return events, current_attempt, maximum_attempts


def _runtime_events(attempt_dir: Path, number: int) -> list[dict[str, str]]:
    path = attempt_dir / "progress.jsonl"
    events: list[dict[str, str]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return events
    for line in lines:
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        component = str(item.get("component", "unknown"))
        label = GATE_LABELS.get(component, component)
        status = str(item.get("status", ""))
        if status == "started":
            message, event_status = f"候选 {number} · {label}：已开始", "running"
        elif status == "retrying":
            retry = int(item.get("retry", 1))
            maximum = int(item.get("maximum_retries", retry))
            summary = str(item.get("summary", "")).strip()
            suffix = f"；{summary[:180]}" if summary else ""
            message, event_status = (
                f"候选 {number} · {label}：响应未完整返回，正在进行同一候选槽重试 {retry}/{maximum}{suffix}",
                "inconclusive",
            )
        elif status == "completed":
            result = str(item.get("result", "pass"))
            duration = int(item.get("duration_ms", item.get("latency_ms", 0)))
            timing = f"，耗时 {duration / 1000:.1f} 秒" if duration else ""
            tokens = item.get("total_tokens")
            timing += f"，{tokens} tokens" if tokens is not None else ""
            summary = str(item.get("summary", "")).strip()
            suffix = f"；{summary[:180]}" if summary else ""
            message = f"候选 {number} · {label}：{STATUS_LABELS.get(result, result)}{timing}{suffix}"
            event_status = result
        elif status == "failed":
            message = f"候选 {number} · {label}：调用失败；{str(item.get('summary', ''))[:180]}"
            event_status = "fail"
        elif status == "skipped":
            message, event_status = f"候选 {number} · {label}：因前置检查未通过而跳过", "skipped"
        else:
            continue
        events.append({
            "time": str(item.get("time") or _timestamp(path)),
            "status": event_status,
            "component": component,
            "message": message,
        })
    return events


def _vendor_progress(
    attempt_dir: Path, number: int
) -> tuple[list[dict[str, str]], dict[str, Any] | None]:
    records: list[dict[str, Any]] = []
    for path in sorted(attempt_dir.glob("*_vendor_progress.jsonl")):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict) and item.get("vendor_phase") in VENDOR_PHASE_LABELS:
                records.append(item)
    if not records:
        return [], None
    records.sort(key=lambda item: str(item.get("time", "")))
    events: list[dict[str, str]] = []
    for item in records:
        phase = str(item["vendor_phase"])
        target = str(item.get("target", "台达 PLC"))
        label = VENDOR_PHASE_LABELS[phase]
        index = int(item.get("case_index", 0) or 0)
        total = int(item.get("case_total", 0) or 0)
        case_suffix = f"（仿真用例 {index}/{total}）" if index and total else ""
        result = str(item.get("result", ""))
        if phase == "complete":
            event_status = STATUS_LABELS.get(result, result or "pass")
            status = "pass" if result == "pass" else "fail" if result == "fail" else "inconclusive"
            message = f"候选 {number} · {target} 厂商验证：{event_status}"
        else:
            status = "running"
            message = f"候选 {number} · {target}：{label}{case_suffix}"
        events.append({
            "time": str(item.get("time") or datetime.now(timezone.utc).isoformat()),
            "status": status,
            "component": "delta_vendor_validation",
            "message": message,
        })
    latest = records[-1]
    return events, {
        "active": str(latest.get("vendor_phase")) != "complete",
        "target": str(latest.get("target", "台达 PLC")),
        "phase": str(latest.get("vendor_phase", "queued")),
        "phase_label": VENDOR_PHASE_LABELS[str(latest.get("vendor_phase", "queued"))],
        "phase_percent": int(latest.get("phase_percent", 86) or 86),
        "case_index": int(latest.get("case_index", 0) or 0),
        "case_total": int(latest.get("case_total", 0) or 0),
        "result": str(latest.get("result", "")),
    }


def _event(path: Path | None, message: str, status: str = "info") -> dict[str, str]:
    return {
        "time": _timestamp(path) if path and path.exists() else datetime.now(timezone.utc).isoformat(),
        "status": status,
        "message": message,
    }


def _attempt_events(attempt_dir: Path, number: int) -> list[dict[str, str]]:
    runtime_events = _runtime_events(attempt_dir, number)
    vendor_events, _ = _vendor_progress(attempt_dir, number)
    if runtime_events:
        return sorted(runtime_events + vendor_events, key=lambda item: item["time"])
    events: list[dict[str, str]] = []
    request = attempt_dir / "request.json"
    response = attempt_dir / "raw_response.json"
    evaluation_path = attempt_dir / "evaluation.json"
    sealed_path = attempt_dir / "sealed_evaluation.json"
    if request.exists():
        events.append(_event(request, f"候选 {number}：已向大语言模型提交生成或修正请求"))
    if response.exists():
        events.append(_event(response, f"候选 {number}：已收到完整 ST 候选，开始确定性验证"))
    evaluation = _read_json(evaluation_path)
    if evaluation:
        for gate in evaluation.get("gates", []):
            name = str(gate.get("name", "validator"))
            if name == "openplc" and sealed_path.exists():
                continue
            status = str(gate.get("status", "inconclusive"))
            label = GATE_LABELS.get(name, name)
            summary = str(gate.get("summary", "")).strip()
            suffix = f"；{summary[:180]}" if summary else ""
            events.append(_event(
                evaluation_path,
                f"候选 {number} · {label}：{STATUS_LABELS.get(status, status)}{suffix}",
                status,
            ))
    sealed = _read_json(sealed_path)
    if sealed:
        name = str(sealed.get("name", "openplc"))
        status = str(sealed.get("status", "inconclusive"))
        summary = str(sealed.get("summary", "")).strip()
        suffix = f"；{summary[:180]}" if summary else ""
        events.append(_event(
            sealed_path,
            f"候选 {number} · {GATE_LABELS.get(name, name)}：{STATUS_LABELS.get(status, status)}{suffix}",
            status,
        ))
    return sorted(events + vendor_events, key=lambda item: item["time"])


def _active_phase(attempt_dir: Path | None, evaluation: dict[str, Any] | None) -> tuple[str, str, int]:
    if attempt_dir is None:
        return "generation_queued", "正在准备第一个候选", 5
    _, vendor = _vendor_progress(attempt_dir, 0)
    if vendor and vendor["active"]:
        case_suffix = (
            f"（仿真用例 {vendor['case_index']}/{vendor['case_total']}）"
            if vendor["case_index"] and vendor["case_total"] else ""
        )
        return (
            "delta_vendor_validation",
            f"{vendor['phase_label']}{case_suffix}",
            int(vendor["phase_percent"]),
        )
    if not (attempt_dir / "raw_response.json").exists():
        return "model_generation", "正在等待大语言模型生成完整 PLC 程序", 15
    if evaluation:
        statuses = {str(gate.get("name")): str(gate.get("status")) for gate in evaluation.get("gates", [])}
        if statuses.get("openplc_confirmation") == "pass":
            if not any((attempt_dir / name).exists() for name in ("dvp48es300r.stdout", "as228t.stdout")):
                return "delta_vendor_validation", "正在等待 ISPSoft 编译并执行 COMMGR 厂商仿真 Oracle 测试", 90
        elif all(statuses.get(name) == "pass" for name in {"compiler", "plcverif", "openplc_feedback"}):
            if not (attempt_dir / "openplc.stdout").exists():
                return "openplc_confirmation", "正在执行 OpenPLC 确认测试", 90
        return "feedback_processing", "正在整理验证反馈并准备下一版 ST 候选", 95
    if not (attempt_dir / "compiler.stdout").exists():
        return "compiler", "正在执行接口检查与 MatIEC 编译", 30
    if not (attempt_dir / "plcverif.stdout").exists():
        return "plcverif", "正在执行 PLCverif 形式验证（该阶段可能耗时较长）", 55
    if not (attempt_dir / "openplc_feedback.stdout").exists():
        return "openplc_feedback", "正在执行 OpenPLC 功能测试", 75
    if not (attempt_dir / "openplc_confirmation.stdout").exists() and any(
        (attempt_dir / name).exists() for name in ("openplc_confirmation.stderr", "openplc_feedback.stdout")
    ):
        return "openplc_confirmation", "正在执行 OpenPLC 确认测试", 82
    return "visible_validation", "正在汇总当前候选的验证结果", 85


def _parse_time(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed.astimezone(timezone.utc)


def _active_component(events: list[dict[str, str]], phase: str) -> str:
    return {
        "contract_generation": "验证契约生成",
        "generation_queued": "后台任务队列",
        "model_generation": GATE_LABELS["model"],
        "compiler": GATE_LABELS["compiler"],
        "plcverif": GATE_LABELS["plcverif"],
        "openplc_feedback": GATE_LABELS["openplc_feedback"],
        "openplc_confirmation": GATE_LABELS["openplc_confirmation"],
        "feedback_processing": "验证反馈整理",
        "delta_vendor_validation": "台达官方工具链",
    }.get(phase, GATE_LABELS.get(phase, phase))


def build_job_progress(job: dict[str, Any], data_root: Path) -> dict[str, Any]:
    status = str(job["status"])
    budget = int(job.get("request", {}).get("max_candidates", 20))
    events = [_event(None, "任务已创建")]
    events[0]["time"] = str(job.get("created_at") or events[0]["time"])
    phase, message, percent = "queued", "任务已进入队列", 2
    contract_events, contract_attempt, contract_maximum = _contract_events(
        data_root / "jobs" / str(job["id"]) / "contract_progress.jsonl"
    )
    events.extend(contract_events)

    if status in {"contract_queued", "contract_generating"}:
        phase = "contract_generation"
        message = f"正在生成并校验验证契约（第 {max(contract_attempt, 1)}/{contract_maximum} 次）"
        percent = min(9, 4 + max(contract_attempt, 1) * 2)
    elif status == "awaiting_contract_approval":
        phase = "awaiting_contract_approval"
        message = "验证契约已就绪，等待用户确认"
        percent = 10
        events.append(_event(None, "验证契约已经通过结构检查，等待确认", "pass"))
        events[-1]["time"] = str(job.get("updated_at") or events[-1]["time"])
    elif status == "contract_failed":
        phase, message, percent = "contract_failed", "验证契约生成失败", 100
        events.append(_event(None, message, "fail"))
        events[-1]["time"] = str(job.get("updated_at") or events[-1]["time"])

    run_root = data_root / "jobs" / str(job["id"]) / "run"
    attempt_dirs = sorted((run_root / "attempts").glob("attempt_*")) if (run_root / "attempts").is_dir() else []
    for number, attempt_dir in enumerate(attempt_dirs, 1):
        events.extend(_attempt_events(attempt_dir, number))

    current_attempt = len(attempt_dirs)
    completed_attempts = sum((path / "evaluation.json").is_file() for path in attempt_dirs)
    vendor_visualization = None
    if attempt_dirs:
        _, vendor_visualization = _vendor_progress(attempt_dirs[-1], current_attempt)
    terminal = status in {"verified_success", "generation_failed", "infrastructure_error", "cancelled"}
    if status in {"generation_queued", "generating"}:
        latest = attempt_dirs[-1] if attempt_dirs else None
        evaluation = _read_json(latest / "evaluation.json") if latest else None
        phase, message, percent = _active_phase(latest, evaluation)
    elif status == "verified_success":
        phase, message, percent = "verified_success", "PLC 程序已通过全部验证", 100
        events.append(_event(None, message, "pass"))
        events[-1]["time"] = str(job.get("updated_at") or events[-1]["time"])
    elif status == "generation_failed":
        phase, message, percent = "generation_failed", "候选已结束，但尚未通过全部验证", 100
        events.append(_event(None, message, "fail"))
        events[-1]["time"] = str(job.get("updated_at") or events[-1]["time"])
    elif status == "infrastructure_error":
        phase, message, percent = "infrastructure_error", "模型或验证基础设施发生错误", 100
        events.append(_event(None, message, "inconclusive"))
        events[-1]["time"] = str(job.get("updated_at") or events[-1]["time"])
    elif status == "cancelling":
        phase, message = "cancelling", "正在安全停止模型或验证进程"
        events.append(_event(None, "已收到用户取消请求，正在保留现有证据", "running"))
        events[-1]["time"] = str(job.get("updated_at") or events[-1]["time"])
    elif status == "cancelled":
        phase, message, percent = "cancelled", "任务已由用户取消", 100
        events.append(_event(None, message, "fail"))
        events[-1]["time"] = str(job.get("updated_at") or events[-1]["time"])

    events.sort(key=lambda item: item["time"])
    now = datetime.now(timezone.utc)
    created = _parse_time(job.get("created_at")) or now
    activity_times = [value for item in events if (value := _parse_time(item.get("time"))) is not None]
    latest = max(activity_times, default=created)
    phase_started = latest
    current_component = _active_component(events, phase)
    elapsed_seconds = max(0, int((now - created).total_seconds()))
    idle_seconds = max(0, int((now - latest).total_seconds()))
    expected_quiet_seconds = {
        "contract_generation": 180,
        "model_generation": 300,
        "plcverif": 900,
        "delta_vendor_validation": 900,
    }.get(phase, 180)
    if terminal or status == "contract_failed":
        health = "complete" if status == "verified_success" else "failed"
    elif status in {"contract_queued", "generation_queued"}:
        # A queued task has not gone silent: it is deliberately waiting for a
        # bounded worker slot, so age alone must not label it as delayed.
        health = "working"
    elif idle_seconds > expected_quiet_seconds:
        health = "delayed"
    else:
        health = "working"
    return {
        "job_id": job["id"],
        "status": status,
        "phase": phase,
        "message": message,
        "phase_percent": percent,
        "current_attempt": current_attempt,
        "completed_attempts": completed_attempts,
        "candidate_budget": budget,
        "contract_attempt": contract_attempt,
        "contract_budget": contract_maximum,
        "active": not terminal and status != "contract_failed",
        "current_component": current_component,
        "created_at": created.isoformat(),
        "phase_started_at": phase_started.isoformat(),
        "last_activity_at": latest.isoformat(),
        "elapsed_seconds": elapsed_seconds,
        "idle_seconds": idle_seconds,
        "health": health,
        "vendor_visualization": vendor_visualization,
        "events": events[-80:],
    }

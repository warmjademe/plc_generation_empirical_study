#!/usr/bin/env python3
"""Shared, auditable batch runner for internal controls and ablations."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


SOURCE_ROOT = Path(__file__).resolve().parent
OUR_METHOD_ROOT = SOURCE_ROOT / "our_method"
sys.path.insert(0, str(OUR_METHOD_ROOT / "src"))

from plc_loop.ledger import EvidenceLedger  # noqa: E402
from plc_loop.orchestrator import run_from_paths  # noqa: E402


ABLATION_SPECS = {
    "direct": {
        "id": "ablation1",
        "label": "Direct@1",
        "protocol": "one stateless candidate without validation feedback",
    },
    "independent": {
        "id": "ablation2",
        "label": "Independent@10",
        "protocol": "up to ten mutually independent stateless candidates without feedback",
    },
    "raw_repair": {
        "id": "ablation3",
        "label": "LatestRawRepair@10",
        "protocol": (
            "up to ten candidates; each repair uses only the immediately preceding "
            "candidate and bounded raw MatIEC/PLCverif diagnostics"
        ),
    },
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _write_json(path: Path, value: object) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _load_tasks(dataset_root: Path, selected_ids: set[str]) -> list[Path]:
    task_root = dataset_root / "tasks" if (dataset_root / "tasks").is_dir() else dataset_root
    task_dirs = sorted(path for path in task_root.iterdir() if path.is_dir())
    if selected_ids:
        unknown = selected_ids - {path.name for path in task_dirs}
        if unknown:
            raise ValueError(f"requested task IDs are absent from the dataset: {sorted(unknown)}")
        task_dirs = [path for path in task_dirs if path.name in selected_ids]
    if not task_dirs:
        raise ValueError("no task directories selected")
    return task_dirs


def _validate_protocol_config(config: dict[str, Any], method: str) -> None:
    experiment = config.get("experiment", {})
    if int(experiment.get("max_candidates", 0)) != 10:
        raise ValueError("all comparison configs must declare max_candidates=10")
    if experiment.get("required_visible_gates") != ["compiler", "plcverif"]:
        raise ValueError("required visible gates must be compiler then plcverif")
    if experiment.get("sealed_gate") != "openplc":
        raise ValueError("the terminal sealed gate must be openplc")
    if experiment.get("stop_on_visible_pass") is not True:
        raise ValueError("stop_on_visible_pass must be true")
    if experiment.get("development_only") is True:
        raise ValueError("development-only configurations cannot produce baseline scores")
    validator_names = [item.get("name") for item in config.get("validators", [])]
    if validator_names != ["compiler", "plcverif", "openplc"]:
        raise ValueError("validator order must be MatIEC -> PLCverif -> OpenPLC")
    if method not in ABLATION_SPECS:
        raise ValueError(f"unsupported ablation method: {method}")


def _audit_requests(run_dir: Path, task_dir: Path, result: dict[str, Any], method: str) -> dict[str, Any]:
    request_paths = sorted((run_dir / "attempts").glob("attempt_*/request.json"))
    request_count_ok = len(request_paths) == int(result.get("candidates_used", -1))
    reference = (task_dir / "reference.st").read_text(encoding="utf-8").strip()
    checks = []
    for number, request_path in enumerate(request_paths, start=1):
        request = json.loads(request_path.read_text(encoding="utf-8"))
        certificate = json.loads(
            (request_path.parent / "feedback_certificate.json").read_text(encoding="utf-8")
        )
        messages = request.get("messages", [])
        prompt = "\n".join(str(item.get("content", "")) for item in messages)
        valid = [item.get("role") for item in messages] == ["system", "user"]
        valid = valid and (not reference or reference not in prompt)
        if method in {"direct", "independent"}:
            valid = valid and request.get("anchor_attempt") is None
            valid = valid and request.get("repair_mode") == "SYNTHESIZE"
            valid = valid and certificate.get("format") == "no-feedback-baseline"
            valid = valid and certificate.get("selected_failures") == []
        elif number == 1:
            valid = valid and request.get("anchor_attempt") is None
            valid = valid and request.get("repair_mode") == "SYNTHESIZE"
            valid = valid and certificate.get("format") == "raw-latest-diagnostics-v1"
        else:
            valid = valid and request.get("anchor_attempt") == number - 1
            valid = valid and request.get("repair_mode") == "PATCH"
            valid = valid and certificate.get("format") == "raw-latest-diagnostics-v1"
        checks.append(valid)
    candidate_budget_ok = result.get("candidate_budget") == (1 if method == "direct" else 10)
    return {
        "request_count": len(request_paths),
        "request_count_ok": request_count_ok,
        "request_protocol_ok": request_count_ok and all(checks),
        "candidate_budget_ok": candidate_budget_ok,
    }


def run_ablation(method: str, argv: list[str] | None = None) -> int:
    spec = ABLATION_SPECS[method]
    parser = argparse.ArgumentParser(description=f"Run {spec['id']} ({spec['label']})")
    parser.add_argument("--config", type=Path, default=OUR_METHOD_ROOT / "configs/kimi_k3_runtime_full.json")
    parser.add_argument("--dataset-root", required=True, type=Path)
    parser.add_argument("--qualification", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--task-id", action="append", default=[])
    args = parser.parse_args(argv)

    config_path = args.config.resolve()
    dataset_root = args.dataset_root.resolve()
    qualification_path = args.qualification.resolve()
    output = args.output.resolve()
    if output == dataset_root or dataset_root in output.parents:
        raise ValueError("output must be outside the frozen dataset directory")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    _validate_protocol_config(config, method)
    key_env = str(config["provider"]["api_key_env"])
    if not os.environ.get(key_env):
        raise RuntimeError(f"{key_env} is required; silent model fallback is forbidden")

    if not qualification_path.is_file():
        raise ValueError("--qualification must name the completed qualification.json file")
    qualification = json.loads(qualification_path.read_text(encoding="utf-8"))
    if qualification.get("status") != "pass":
        raise ValueError("the task bank has not completed reference and negative-control qualification")
    qualified_ids = {
        str(item["task_id"])
        for item in qualification.get("tasks", [])
        if item.get("qualified") is True
    }
    task_dirs = _load_tasks(dataset_root, set(args.task_id))
    unqualified = {path.name for path in task_dirs} - qualified_ids
    if unqualified:
        raise ValueError(f"selected tasks are not qualified: {sorted(unqualified)}")

    output.mkdir(parents=True, exist_ok=True)
    run_spec = {
        "schema_version": "1.0",
        "ablation_id": spec["id"],
        "label": spec["label"],
        "method": method,
        "protocol": spec["protocol"],
        "config_sha256": _sha256(config_path),
        "dataset_tree_sha256": _tree_sha256(dataset_root),
        "qualification_sha256": _sha256(qualification_path),
        "task_ids": [path.name for path in task_dirs],
    }
    run_spec_path = output / "run_spec.json"
    if run_spec_path.is_file():
        if json.loads(run_spec_path.read_text(encoding="utf-8")) != run_spec:
            raise RuntimeError("resume refused because the frozen baseline run specification changed")
    else:
        if any(output.iterdir()):
            raise FileExistsError(f"refusing unbound non-empty output directory: {output}")
        _write_json(run_spec_path, run_spec)

    allowed_models = tuple(config["provider"].get(
        "allowed_resolved_models", [config["provider"]["requested_model"]]
    ))

    def run_task(task_dir: Path) -> dict[str, Any]:
        run_dir = output / task_dir.name
        result_path = run_dir / "result.json"
        if result_path.is_file():
            result = json.loads(result_path.read_text(encoding="utf-8"))
            resumed = True
        else:
            if run_dir.exists():
                raise RuntimeError(
                    f"incomplete run exists for {task_dir.name}; refusing a potentially duplicate model call"
                )
            result = run_from_paths(config_path, task_dir, run_dir, method)
            resumed = False
        if result.get("task_id") != task_dir.name or result.get("method") != method:
            raise RuntimeError("persisted result does not match task or baseline method")
        entries = EvidenceLedger.verify(run_dir / "ledger.jsonl")
        audit = _audit_requests(run_dir, task_dir, result, method)
        resolved = result.get("resolved_models", [])
        models_ok = all(
            any(model == allowed or str(model).startswith(f"{allowed}-") for allowed in allowed_models)
            for model in resolved
        )
        return {
            "task_id": task_dir.name,
            "status": result["status"],
            "success": bool(result["success"]),
            "candidates_used": int(result["candidates_used"]),
            "winning_attempt": result.get("winning_attempt"),
            "usage_total": result.get("usage_total", {}),
            "resolved_models": resolved,
            "ledger_event_count": len(entries),
            "ledger_valid": True,
            "resolved_model_valid": models_ok,
            "resumed": resumed,
            **audit,
        }

    records = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(run_task, task_dir): task_dir.name for task_dir in task_dirs}
        for future in as_completed(futures):
            task_id = futures[future]
            try:
                record = future.result()
            except Exception as exc:
                record = {
                    "task_id": task_id,
                    "status": "batch_exception",
                    "success": False,
                    "error": f"{type(exc).__name__}: {exc}",
                    "ledger_valid": False,
                    "request_protocol_ok": False,
                    "candidate_budget_ok": False,
                    "resolved_model_valid": False,
                }
            records.append(record)
            print(json.dumps({
                "task_id": task_id,
                "status": record["status"],
                "candidates_used": record.get("candidates_used"),
            }, ensure_ascii=False), flush=True)
            _write_json(output / "progress.json", sorted(records, key=lambda item: item["task_id"]))

    records.sort(key=lambda item: item["task_id"])
    usage: dict[str, int | float] = {}
    for record in records:
        for key, value in record.get("usage_total", {}).items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                usage[key] = usage.get(key, 0) + value
    cumulative_success = {
        str(k): sum(
            bool(record.get("success")) and int(record.get("winning_attempt") or 11) <= k
            for record in records
        )
        for k in range(1, 11)
    }
    protocol_ok = all(
        record.get("ledger_valid")
        and record.get("request_protocol_ok")
        and record.get("candidate_budget_ok")
        and record.get("resolved_model_valid")
        for record in records
    )
    summary = {
        **run_spec,
        "task_count": len(records),
        "success_count": sum(record.get("success", False) for record in records),
        "status_counts": {
            status: sum(record["status"] == status for record in records)
            for status in sorted({record["status"] for record in records})
        },
        "cumulative_verified_success": cumulative_success,
        "total_candidates_used": sum(int(record.get("candidates_used", 0)) for record in records),
        "usage_total": usage,
        "protocol_ok": protocol_ok,
        "runs": records,
    }
    _write_json(output / "ablation_summary.json", summary)
    print(json.dumps({
        "ablation": spec["label"],
        "task_count": summary["task_count"],
        "success_count": summary["success_count"],
        "total_candidates_used": summary["total_candidates_used"],
        "protocol_ok": protocol_ok,
    }, ensure_ascii=False))
    return 0 if protocol_ok and not any(item["status"] == "batch_exception" for item in records) else 2

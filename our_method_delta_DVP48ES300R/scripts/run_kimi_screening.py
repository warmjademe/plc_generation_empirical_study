#!/usr/bin/env python3
"""Run exactly one isolated Kimi-K3 candidate over qualified bank tasks."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from plc_loop.ledger import EvidenceLedger
from plc_loop.orchestrator import run_from_paths


OPTIONAL_INCONCLUSIVE_GATES: set[str] = set()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def classify(result: dict[str, Any]) -> tuple[str, list[str]]:
    reasons = []
    protocol_reasons = []
    if result["status"] == "infrastructure_error":
        reasons.append("model transport/provider failure")
    if result["status"] == "sealed_inconclusive":
        reasons.append("sealed validator inconclusive")
    for attempt in result.get("attempts", []):
        for gate in attempt.get("gates", []):
            if gate.get("name") == "response_format" and gate.get("status") != "pass":
                protocol_reasons.append("model response did not satisfy the harness output contract")
            if gate.get("status") == "inconclusive" and gate.get("name") not in OPTIONAL_INCONCLUSIVE_GATES:
                reasons.append(f"mandatory gate inconclusive: {gate.get('name')}")
            for evidence in gate.get("evidence", []):
                if evidence.get("kind") == "tool_error" and gate.get("name") not in OPTIONAL_INCONCLUSIVE_GATES:
                    reasons.append(f"tool error: {gate.get('name')}")
    sealed = result.get("sealed_result") or {}
    if sealed.get("status") == "inconclusive":
        reasons.append("sealed result inconclusive")
    if reasons:
        return "infrastructure_excluded", sorted(set(reasons))
    if protocol_reasons:
        return "protocol_excluded", sorted(set(protocol_reasons))
    if result["status"] == "verified_success":
        return "verified_success", []
    if result["status"] in {"candidate_budget_exhausted", "sealed_failure"}:
        return "semantic_failure", []
    return "protocol_excluded", [f"unexpected terminal status: {result['status']}"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--bank-root", required=True, type=Path)
    parser.add_argument("--qualification", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument(
        "--max-tasks",
        type=int,
        help="Run only the first N eligible tasks in frozen manifest order.",
    )
    parser.add_argument("--plan-only", action="store_true", help="Write and print the frozen task plan without model calls.")
    parser.add_argument(
        "--category",
        action="append",
        default=[],
        help="Restrict this run to a category ID such as C05; may be repeated.",
    )
    parser.add_argument(
        "--skip-task-id",
        action="append",
        default=[],
        help="Conservatively exclude a task that already consumed an unusable model request.",
    )
    parser.add_argument(
        "--continue-from",
        type=Path,
        help=(
            "A previous screening output. Tasks with a trustworthy semantic verdict "
            "are skipped; infrastructure/protocol failures are run again in this output."
        ),
    )
    parser.add_argument(
        "--target-failures-per-category",
        type=int,
        help=(
            "Stop after the union of this run and --continue-from contains this many "
            "semantic failures in every qualified category. Requires --workers=1 so "
            "no paid request remains in flight after the target is reached."
        ),
    )
    parser.add_argument(
        "--partial-qualified",
        action="store_true",
        help="incrementally screen only tasks with completed per-task qualification records",
    )
    args = parser.parse_args()
    if args.max_tasks is not None and args.max_tasks <= 0:
        raise ValueError("--max-tasks must be positive")
    if args.target_failures_per_category is not None:
        if args.target_failures_per_category <= 0:
            raise ValueError("--target-failures-per-category must be positive")
        if args.workers != 1:
            raise ValueError("balanced early stopping requires --workers=1")
        if args.continue_from is None:
            raise ValueError("balanced early stopping requires --continue-from")

    config = args.config.resolve()
    config_document = json.loads(config.read_text(encoding="utf-8"))
    provider_config = config_document.get("provider", {})
    key_env = str(provider_config.get("api_key_env", ""))
    if not key_env or not os.environ.get(key_env):
        raise RuntimeError(f"{key_env or 'provider api_key_env'} is required; fallback models are forbidden")
    allowed_models = tuple(
        str(value)
        for value in provider_config.get(
            "allowed_resolved_models", [provider_config.get("requested_model", "")]
        )
        if value
    )
    if not allowed_models:
        raise RuntimeError("provider.allowed_resolved_models must not be empty")
    bank_root = args.bank_root.resolve()
    qualification_path = args.qualification.resolve()
    expected_task_count = sum(1 for line in (bank_root / "manifest.jsonl").read_text(encoding="utf-8").splitlines() if line.strip())
    if expected_task_count <= 0:
        raise RuntimeError("task-bank manifest is empty")
    qualification_complete = False
    if qualification_path.is_dir():
        if not args.partial_qualified:
            raise RuntimeError("a qualification directory requires --partial-qualified")
        run_spec_path = qualification_path / "run_spec.json"
        if not run_spec_path.is_file():
            raise RuntimeError("partial qualification directory has no frozen run_spec.json")
        qualification = json.loads(run_spec_path.read_text(encoding="utf-8"))
        qualified_task_ids = set()
        for record_path in qualification_path.glob("*/qualification.json"):
            record = json.loads(record_path.read_text(encoding="utf-8"))
            if record.get("qualified") is True:
                qualified_task_ids.add(str(record["task_id"]))
        qualification_binding_path = run_spec_path
    else:
        qualification = json.loads(qualification_path.read_text(encoding="utf-8"))
        if qualification.get("status") != "pass" or qualification.get("qualified_count") != expected_task_count:
            raise RuntimeError("the frozen task bank has not passed full reference qualification")
        qualified_task_ids = {
            str(record["task_id"])
            for record in qualification.get("tasks", [])
            if record.get("qualified") is True
        }
        qualification_complete = len(qualified_task_ids) == expected_task_count
        qualification_binding_path = qualification_path
    if qualification.get("bank_manifest_sha256") != sha256(bank_root / "manifest.jsonl"):
        raise RuntimeError("qualification is not bound to the current task-bank manifest")

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    all_task_dirs = sorted(path for path in (bank_root / "tasks").iterdir() if path.is_dir())
    if len(all_task_dirs) != expected_task_count:
        raise RuntimeError(
            f"manifest declares {expected_task_count} bank tasks, found {len(all_task_dirs)} directories"
        )
    task_dirs = [path for path in all_task_dirs if path.name in qualified_task_ids]
    requested_categories = set(args.category)
    known_categories = {path.name[:3] for path in all_task_dirs}
    unknown_categories = requested_categories - known_categories
    if unknown_categories:
        raise ValueError(f"unknown categories: {sorted(unknown_categories)}")
    if requested_categories:
        task_dirs = [path for path in task_dirs if path.name[:3] in requested_categories]
    skipped_task_ids = set(args.skip_task_id)
    unknown_skips = skipped_task_ids - {path.name for path in all_task_dirs}
    if unknown_skips:
        raise ValueError(f"unknown skipped task IDs: {sorted(unknown_skips)}")
    task_dirs = [path for path in task_dirs if path.name not in skipped_task_ids]
    if not task_dirs:
        raise RuntimeError("no qualified tasks are currently available for screening")

    continued_from: Path | None = None
    continued_valid_task_ids: set[str] = set()
    continued_semantic_failure_ids: set[str] = set()
    continuation_summary_sha256: str | None = None
    if args.continue_from:
        continued_from = args.continue_from.resolve()
        if not continued_from.is_dir():
            raise FileNotFoundError(f"continuation output does not exist: {continued_from}")
        summary_path = continued_from / "screening_summary.json"
        if summary_path.is_file():
            continuation_summary_sha256 = sha256(summary_path)
        for result_path in continued_from.glob("*/result.json"):
            result = json.loads(result_path.read_text(encoding="utf-8"))
            failure_class, _ = classify(result)
            if failure_class in {"verified_success", "semantic_failure"}:
                continued_valid_task_ids.add(str(result["task_id"]))
            if failure_class == "semantic_failure":
                continued_semantic_failure_ids.add(str(result["task_id"]))
        unknown = continued_valid_task_ids - {path.name for path in all_task_dirs}
        if unknown:
            raise RuntimeError(f"continuation output contains unknown task IDs: {sorted(unknown)}")
        task_dirs = [path for path in task_dirs if path.name not in continued_valid_task_ids]
        if not task_dirs:
            raise RuntimeError("continuation source already contains all currently qualified semantic verdicts")

    qualified_categories = sorted({path.name[:3] for path in task_dirs})
    semantic_failure_counts = collections.Counter(
        task_id[:3] for task_id in continued_semantic_failure_ids
    )
    if args.target_failures_per_category is not None:
        task_dirs = [
            path for path in task_dirs
            if semantic_failure_counts[path.name[:3]] < args.target_failures_per_category
        ]
        if not task_dirs:
            raise RuntimeError("balanced semantic-failure target is already satisfied")
    if args.max_tasks is not None:
        task_dirs = task_dirs[: args.max_tasks]

    write_json(output / "selection_plan.json", {
        "schema_version": "1.0",
        "requested_categories": sorted(requested_categories),
        "qualified_categories": qualified_categories,
        "continued_semantic_failure_counts": dict(sorted(semantic_failure_counts.items())),
        "target_failures_per_category": args.target_failures_per_category,
        "skipped_task_ids": sorted(skipped_task_ids),
        "candidate_task_ids_in_order": [path.name for path in task_dirs],
    })
    print(json.dumps({
        "selection_plan": str(output / "selection_plan.json"),
        "qualified_categories": qualified_categories,
        "candidate_task_count": len(task_dirs),
        "first_candidate": task_dirs[0].name,
    }, ensure_ascii=False), flush=True)
    if args.plan_only:
        return 0

    def run_task(task_dir: Path) -> dict[str, Any]:
        run_dir = output / task_dir.name
        result_path = run_dir / "result.json"
        if result_path.is_file():
            result = json.loads(result_path.read_text(encoding="utf-8"))
            resumed = True
        else:
            result = run_from_paths(config, task_dir, run_dir, "direct")
            resumed = False
        entries = EvidenceLedger.verify(run_dir / "ledger.jsonl")
        requests = sorted((run_dir / "attempts").glob("attempt_*/request.json"))
        request_isolated = len(requests) == 1
        for request_path in requests:
            request = json.loads(request_path.read_text(encoding="utf-8"))
            messages = request.get("messages", [])
            prompt = "\n".join(str(message.get("content", "")) for message in messages)
            request_isolated = request_isolated and [message.get("role") for message in messages] == ["system", "user"]
            request_isolated = request_isolated and request.get("anchor_attempt") is None
            request_isolated = request_isolated and request.get("repair_mode") == "SYNTHESIZE"
            request_isolated = request_isolated and "no-feedback-baseline" in prompt
            reference = (task_dir / "reference.st").read_text(encoding="utf-8").strip()
            request_isolated = request_isolated and reference not in prompt
        failure_class, exclusion_reasons = classify(result)
        return {
            "task_id": task_dir.name,
            "status": result["status"],
            "success": result["success"],
            "failure_class": failure_class,
            "selection_eligible": failure_class == "semantic_failure",
            "exclusion_reasons": exclusion_reasons,
            "candidates_used": result["candidates_used"],
            "resolved_models": result["resolved_models"],
            "usage_total": result["usage_total"],
            "ledger_valid": bool(entries),
            "request_isolated": request_isolated,
            "run_dir": str(run_dir),
            "resumed": resumed,
        }

    records = []

    def record_completed(task_id: str, future_result: dict[str, Any] | Exception) -> None:
        if isinstance(future_result, Exception):
            exc = future_result
            record = {
                "task_id": task_id, "status": "batch_exception", "success": False,
                "failure_class": "infrastructure_excluded", "selection_eligible": False,
                "exclusion_reasons": [f"{type(exc).__name__}: {exc}"],
                "ledger_valid": False, "request_isolated": False,
            }
        else:
            record = future_result
        records.append(record)
        if record.get("failure_class") == "semantic_failure":
            semantic_failure_counts[task_id[:3]] += 1
        print(json.dumps({
            "task_id": task_id, "status": record["status"],
            "failure_class": record["failure_class"],
            "semantic_failure_counts": dict(sorted(semantic_failure_counts.items())),
        }, ensure_ascii=False), flush=True)
        write_json(output / "progress.json", sorted(records, key=lambda item: item["task_id"]))

    if args.target_failures_per_category is not None:
        target = args.target_failures_per_category
        for task_dir in task_dirs:
            category = task_dir.name[:3]
            if semantic_failure_counts[category] >= target:
                continue
            try:
                record_completed(task_dir.name, run_task(task_dir))
            except Exception as exc:
                record_completed(task_dir.name, exc)
            if all(semantic_failure_counts[cat] >= target for cat in qualified_categories):
                break
    else:
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            futures = {pool.submit(run_task, task_dir): task_dir.name for task_dir in task_dirs}
            for future in as_completed(futures):
                task_id = futures[future]
                try:
                    record_completed(task_id, future.result())
                except Exception as exc:
                    record_completed(task_id, exc)

    records.sort(key=lambda item: item["task_id"])
    class_counts = {
        value: sum(record["failure_class"] == value for record in records)
        for value in sorted({record["failure_class"] for record in records})
    }
    usage: dict[str, int | float] = {}
    for record in records:
        for key, value in record.get("usage_total", {}).items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                usage[key] = usage.get(key, 0) + value
    document = {
        "schema_version": "1.0",
        "protocol": "Kimi-K3 Direct@1; stateless prompt; frozen validators; no feedback",
        "bank_manifest_sha256": sha256(bank_root / "manifest.jsonl"),
        "qualification_sha256": sha256(qualification_binding_path),
        "qualification_complete": qualification_complete,
        "qualified_task_count_at_launch": len(task_dirs),
        "config_sha256": sha256(config),
        "provider_name": provider_config.get("name"),
        "requested_model": provider_config.get("requested_model"),
        "allowed_resolved_models": list(allowed_models),
        "continuation_source": str(continued_from) if continued_from else None,
        "continuation_summary_sha256": continuation_summary_sha256,
        "continued_valid_task_count": len(continued_valid_task_ids),
        "continued_valid_task_ids": sorted(continued_valid_task_ids),
        "continued_semantic_failure_count": len(continued_semantic_failure_ids),
        "continued_semantic_failure_ids": sorted(continued_semantic_failure_ids),
        "target_failures_per_category": args.target_failures_per_category,
        "semantic_failure_counts_by_category": dict(sorted(semantic_failure_counts.items())),
        "balanced_target_met": (
            args.target_failures_per_category is not None
            and all(
                semantic_failure_counts[category] >= args.target_failures_per_category
                for category in qualified_categories
            )
        ),
        "task_count": len(records),
        "class_counts": class_counts,
        "eligible_semantic_failure_count": sum(record["selection_eligible"] for record in records),
        "usage_total": usage,
        "all_ledgers_valid": all(record.get("ledger_valid", False) for record in records),
        "all_requests_isolated": all(record.get("request_isolated", False) for record in records),
        "all_candidates_exactly_once": all(record.get("candidates_used") == 1 for record in records),
        "all_resolved_to_requested_model": all(
            len(record.get("resolved_models", [])) == 1
            and any(
                str(record["resolved_models"][0]) == model
                or str(record["resolved_models"][0]).startswith(f"{model}-")
                for model in allowed_models
            )
            for record in records
        ),
        "screening_calls_excluded_from_later_baseline_scores": True,
        "screening_complete": qualification_complete and len(records) == expected_task_count,
        "runs": records,
    }
    write_json(output / "screening_summary.json", document)
    protocol_ok = (
        len(records) == len(task_dirs)
        and document["all_ledgers_valid"]
        and document["all_requests_isolated"]
        and document["all_candidates_exactly_once"]
        and document["all_resolved_to_requested_model"]
        and not any(record["failure_class"] in {"infrastructure_excluded", "protocol_excluded"} for record in records)
    )
    print(json.dumps({
        "task_count": len(records), "class_counts": class_counts,
        "eligible_semantic_failure_count": document["eligible_semantic_failure_count"],
        "protocol_ok": protocol_ok,
    }, ensure_ascii=False))
    return 0 if protocol_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())

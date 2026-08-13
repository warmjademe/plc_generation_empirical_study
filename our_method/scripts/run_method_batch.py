#!/usr/bin/env python3
"""Run a resumable, concurrent batch for one synthesis method.

The per-task run directories remain the authoritative artifacts.  This wrapper
only schedules them and derives aggregate statistics from immutable result and
ledger files; it does not weaken or replace any validator in the configured
MatIEC -> PLCverif -> OpenPLC chain.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from plc_loop.ledger import EvidenceLedger
from plc_loop.orchestrator import METHODS, run_from_paths


def write_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def model_is_allowed(resolved: str, allowed: tuple[str, ...]) -> bool:
    return any(resolved == item or resolved.startswith(f"{item}-") for item in allowed)


def terminal_failure_stage(result: dict[str, Any]) -> str:
    if result.get("success"):
        return "none"
    if result.get("status") == "infrastructure_error":
        return "infrastructure"
    sealed = result.get("sealed_result") or {}
    if sealed.get("status") in {"fail", "inconclusive"}:
        return "openplc"
    attempts = result.get("attempts") or []
    if not attempts:
        return "model_or_infrastructure"
    gates = {gate.get("name"): gate.get("status") for gate in attempts[-1].get("gates", [])}
    for name in ("response_format", "compiler", "plcverif", "openplc_feedback"):
        if gates.get(name) in {"fail", "inconclusive"}:
            return name
    return "candidate_budget"


def audit_completed_run(
    run_dir: Path,
    *,
    task_id: str,
    method: str,
    candidate_budget: int,
    allowed_models: tuple[str, ...],
    expected_config_sha256: str,
    expected_ablation_id: str | None = None,
    expected_component_1: bool | None = None,
    expected_component_2: bool | None = None,
) -> dict[str, Any]:
    result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    if result.get("task_id") != task_id:
        raise ValueError(f"result task mismatch: {result.get('task_id')!r}")
    if result.get("method") != method:
        raise ValueError(f"result method mismatch: {result.get('method')!r}")
    if int(result.get("candidate_budget", -1)) != candidate_budget:
        raise ValueError(f"candidate budget mismatch: {result.get('candidate_budget')!r}")
    if result.get("config_sha256") != expected_config_sha256:
        raise ValueError(
            "result was produced by a different configuration: "
            f"{result.get('config_sha256')!r}"
        )

    ledger_path = run_dir / "ledger.jsonl"
    entries = EvidenceLedger.verify(ledger_path)
    if not entries or entries[0].get("event_type") != "run_started":
        raise ValueError("ledger does not start with run_started")
    if entries[-1].get("event_type") != "run_finished":
        raise ValueError("ledger does not end with run_finished")

    attempts = result.get("attempts") or []
    sealed_events = sum(entry.get("event_type") == "sealed_judge_completed" for entry in entries)
    sealed_files = len(list((run_dir / "attempts").glob("attempt_*/sealed_evaluation.json")))
    sealed_records = len(result.get("sealed_attempts") or [])
    mechanisms = result.get("mechanisms") or {}
    if expected_ablation_id is not None:
        observed = (
            mechanisms.get("ablation_id"),
            mechanisms.get("core_component_1_enabled"),
            mechanisms.get("core_component_2_enabled"),
        )
        expected = (
            expected_ablation_id,
            expected_component_1,
            expected_component_2,
        )
        if observed != expected:
            raise ValueError(
                f"ablation mechanism mismatch: observed={observed!r}, expected={expected!r}"
            )
    sealed_attempt_budget = int(mechanisms.get("max_sealed_attempts", 1))
    inconclusive_restart_events = sum(
        entry.get("event_type") == "inconclusive_blind_restart_scheduled"
        for entry in entries
    )
    inconclusive_restart_budget = int(mechanisms.get("max_inconclusive_restarts", 0))
    inconclusive_restarts_used = int(mechanisms.get("inconclusive_restarts_used", 0))
    resolved_models = sorted({str(item) for item in result.get("resolved_models") or []})
    model_identity_valid = bool(resolved_models) and all(
        model_is_allowed(item, allowed_models) for item in resolved_models
    )
    winning_attempt = result.get("winning_attempt")
    if result.get("success") and not isinstance(winning_attempt, int):
        raise ValueError("successful run has no integer winning_attempt")
    sealed_count_valid = (
        sealed_events == sealed_files == sealed_records
        and 0 <= sealed_events <= sealed_attempt_budget
        and (not result.get("success") or 1 <= sealed_events <= sealed_attempt_budget)
    )
    if not sealed_count_valid:
        raise ValueError(
            "invalid sealed-judge accounting: "
            f"events={sealed_events}, files={sealed_files}, records={sealed_records}"
        )
    inconclusive_restart_count_valid = (
        inconclusive_restart_events == inconclusive_restarts_used
        and 0 <= inconclusive_restart_events <= inconclusive_restart_budget
    )
    if not inconclusive_restart_count_valid:
        raise ValueError(
            "invalid inconclusive-restart accounting: "
            f"events={inconclusive_restart_events}, "
            f"reported={inconclusive_restarts_used}, "
            f"budget={inconclusive_restart_budget}"
        )

    return {
        "task_id": task_id,
        "run_dir": str(run_dir),
        "status": result.get("status"),
        "success": bool(result.get("success")),
        "failure_stage": terminal_failure_stage(result),
        "candidates_used": int(result.get("candidates_used", len(attempts))),
        "candidate_budget": candidate_budget,
        "winning_attempt": winning_attempt,
        "resolved_models": resolved_models,
        "model_identity_valid": model_identity_valid,
        "usage_total": result.get("usage_total") or {},
        "sealed_events": sealed_events,
        "sealed_files": sealed_files,
        "sealed_records": sealed_records,
        "sealed_attempt_budget": sealed_attempt_budget,
        "inconclusive_restart_events": inconclusive_restart_events,
        "inconclusive_restart_budget": inconclusive_restart_budget,
        "inconclusive_restart_count_valid": inconclusive_restart_count_valid,
        "ledger_valid": True,
        "ablation_id": mechanisms.get("ablation_id"),
        "core_component_1_enabled": mechanisms.get("core_component_1_enabled"),
        "core_component_2_enabled": mechanisms.get("core_component_2_enabled"),
    }


def summarize(
    records: list[dict[str, Any]],
    *,
    method: str,
    candidate_budget: int,
    requested_model: str,
    provider: str,
    workers: int,
) -> dict[str, Any]:
    records = sorted(records, key=lambda item: item["task_id"])
    usage: Counter[str] = Counter()
    for record in records:
        for key, value in record.get("usage_total", {}).items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                usage[key] += value
    success_count = sum(record.get("success", False) for record in records)
    task_count = len(records)
    cumulative = {
        str(k): sum(
            bool(record.get("success"))
            and isinstance(record.get("winning_attempt"), int)
            and record["winning_attempt"] <= k
            for record in records
        )
        for k in range(1, candidate_budget + 1)
    }
    statuses = Counter(str(record.get("status")) for record in records)
    stages = Counter(str(record.get("failure_stage")) for record in records if not record.get("success"))
    return {
        "schema_version": "1.0",
        "protocol": f"{method}@{candidate_budget}; MatIEC -> PLCverif -> OpenPLC; early stop on verified success",
        "method": method,
        "provider": provider,
        "requested_model": requested_model,
        "workers": workers,
        "task_count": task_count,
        "success_count": success_count,
        "success_rate": success_count / task_count if task_count else 0.0,
        "verified_success_at_k": cumulative,
        "status_counts": dict(sorted(statuses.items())),
        "terminal_failure_stage_counts": dict(sorted(stages.items())),
        "total_candidates_used": sum(int(record.get("candidates_used", 0)) for record in records),
        "usage_total": dict(sorted(usage.items())),
        "all_ledgers_valid": all(record.get("ledger_valid", False) for record in records),
        "all_model_identities_valid": all(
            record.get("model_identity_valid", False)
            for record in records
            if int(record.get("candidates_used", 0)) > 0
        ),
        "sealed_judge_count_valid": all(
            record.get("sealed_events", 0)
            == record.get("sealed_files", -1)
            == record.get("sealed_records", -1)
            and 0 <= record.get("sealed_events", 0) <= record.get("sealed_attempt_budget", 1)
            and (
                not record.get("success")
                or 1 <= record.get("sealed_events", 0) <= record.get("sealed_attempt_budget", 1)
            )
            for record in records
        ),
        "inconclusive_restart_count_valid": all(
            record.get("inconclusive_restart_count_valid", False)
            for record in records
        ),
        "runs": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--dataset-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--method", choices=sorted(METHODS), default="evidence")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--include", action="append", default=[])
    parser.add_argument("--exclude", action="append", default=[])
    args = parser.parse_args()
    if args.workers < 1:
        raise ValueError("workers must be positive")

    config_path = args.config.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    provider_config = config["provider"]
    api_key_env = str(provider_config["api_key_env"])
    if not os.environ.get(api_key_env):
        raise RuntimeError(f"{api_key_env} is required; no fallback is allowed")
    candidate_budget = 1 if args.method == "direct" else int(config["experiment"]["max_candidates"])
    allowed_models = tuple(provider_config.get("allowed_resolved_models") or [provider_config["requested_model"]])

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    included = set(args.include)
    excluded = set(args.exclude)
    tasks_root = args.dataset_root.resolve() / "tasks"
    task_dirs = [
        path for path in sorted(tasks_root.iterdir())
        if path.is_dir()
        and (not included or path.name in included)
        and path.name not in excluded
    ]
    missing_includes = included - {path.name for path in task_dirs}
    if missing_includes:
        raise ValueError(f"included tasks were not found: {sorted(missing_includes)}")
    if not task_dirs:
        raise ValueError(f"no task directories found under {tasks_root}")
    manifest_path = args.dataset_root.resolve() / "manifest.jsonl"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"dataset manifest is missing: {manifest_path}")
    run_identity = {
        "config_path": str(config_path),
        "config_sha256": sha256(config_path),
        "dataset_root": str(args.dataset_root.resolve()),
        "dataset_manifest_sha256": sha256(manifest_path),
        "ablation_id": config["experiment"].get("ablation_id"),
        "core_component_1_enabled": config["experiment"].get(
            "core_component_1_enabled"
        ),
        "core_component_2_enabled": config["experiment"].get(
            "core_component_2_enabled"
        ),
    }

    def run_task(task_dir: Path) -> dict[str, Any]:
        run_dir = output / task_dir.name
        result_path = run_dir / "result.json"
        resumed = result_path.is_file()
        if not resumed:
            if run_dir.exists():
                raise FileExistsError(
                    f"incomplete run directory exists and is not overwritten: {run_dir}"
                )
            run_from_paths(config_path, task_dir, run_dir, args.method)
        record = audit_completed_run(
            run_dir,
            task_id=task_dir.name,
            method=args.method,
            candidate_budget=candidate_budget,
            allowed_models=allowed_models,
            expected_config_sha256=run_identity["config_sha256"],
            expected_ablation_id=run_identity["ablation_id"],
            expected_component_1=run_identity["core_component_1_enabled"],
            expected_component_2=run_identity["core_component_2_enabled"],
        )
        record["resumed"] = resumed
        return record

    records: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
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
                    "failure_stage": "batch_exception",
                    "error": f"{type(exc).__name__}: {exc}",
                    "ledger_valid": False,
                    "model_identity_valid": False,
                }
            records.append(record)
            print(
                json.dumps(
                    {
                        "completed": len(records),
                        "total": len(task_dirs),
                        "task_id": task_id,
                        "status": record["status"],
                        "candidates_used": record.get("candidates_used"),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
            progress = summarize(
                records,
                method=args.method,
                candidate_budget=candidate_budget,
                requested_model=str(provider_config["requested_model"]),
                provider=str(provider_config["name"]),
                workers=args.workers,
            )
            progress["expected_task_count"] = len(task_dirs)
            progress.update(run_identity)
            write_json(output / "progress.json", progress)

    document = summarize(
        records,
        method=args.method,
        candidate_budget=candidate_budget,
        requested_model=str(provider_config["requested_model"]),
        provider=str(provider_config["name"]),
        workers=args.workers,
    )
    document.update(run_identity)
    write_json(output / "batch_summary.json", document)
    print(
        json.dumps(
            {key: document[key] for key in (
                "task_count",
                "success_count",
                "success_rate",
                "status_counts",
                "terminal_failure_stage_counts",
                "total_candidates_used",
                "all_ledgers_valid",
                "all_model_identities_valid",
                "sealed_judge_count_valid",
            )},
            ensure_ascii=False,
        ),
        flush=True,
    )
    return 0 if document["status_counts"].get("batch_exception", 0) == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

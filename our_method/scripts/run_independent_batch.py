#!/usr/bin/env python3
"""Run a resumable Independent@k batch and aggregate immutable run results."""

from __future__ import annotations

import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from plc_loop.ledger import EvidenceLedger
from plc_loop.orchestrator import run_from_paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--dataset-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()

    if not os.environ.get("KIMI_API_KEY"):
        raise RuntimeError("KIMI_API_KEY is required; no fallback is allowed")
    config_document = json.loads(args.config.resolve().read_text(encoding="utf-8"))
    candidate_budget = int(config_document["experiment"]["max_candidates"])
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    task_dirs = [
        path for path in sorted((args.dataset_root.resolve() / "tasks").iterdir())
        if path.is_dir() and path.name not in set(args.exclude)
    ]

    def run_task(task_dir: Path) -> dict:
        run_dir = output / task_dir.name
        result_path = run_dir / "result.json"
        if result_path.is_file():
            result = json.loads(result_path.read_text(encoding="utf-8"))
            resumed = True
        else:
            result = run_from_paths(args.config.resolve(), task_dir, run_dir, "independent")
            resumed = False
        ledger_path = run_dir / "ledger.jsonl"
        entries = EvidenceLedger.verify(ledger_path)
        sealed_events = sum(entry["event_type"] == "sealed_judge_completed" for entry in entries)
        sealed_files = len(list((run_dir / "attempts").glob("attempt_*/sealed_evaluation.json")))
        request_isolation = True
        for request_path in sorted((run_dir / "attempts").glob("attempt_*/request.json")):
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request_isolation = request_isolation and [message.get("role") for message in request["messages"]] == ["system", "user"]
            request_isolation = request_isolation and request.get("anchor_attempt") is None
            request_isolation = request_isolation and request.get("repair_mode") == "SYNTHESIZE"
        return {
            "task_id": task_dir.name,
            "run_dir": str(run_dir),
            "status": result["status"],
            "success": result["success"],
            "candidates_used": result["candidates_used"],
            "candidate_budget": result["candidate_budget"],
            "winning_attempt": result["winning_attempt"],
            "resolved_models": result["resolved_models"],
            "usage_total": result["usage_total"],
            "sealed_events": sealed_events,
            "sealed_files": sealed_files,
            "ledger_valid": True,
            "request_isolation": request_isolation,
            "resumed": resumed,
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
                    "request_isolation": False,
                }
            records.append(record)
            print(json.dumps({
                "task_id": task_id,
                "status": record["status"],
                "candidates_used": record.get("candidates_used"),
            }, ensure_ascii=False), flush=True)
            (output / "progress.json").write_text(
                json.dumps(sorted(records, key=lambda item: item["task_id"]), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

    records.sort(key=lambda item: item["task_id"])
    usage = {}
    for record in records:
        for key, value in record.get("usage_total", {}).items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                usage[key] = usage.get(key, 0) + value
    document = {
        "schema_version": "1.0",
        "protocol": (
            f"Independent@{candidate_budget} with stateless candidates and early stop "
            "on first complete visible-plus-sealed pass"
        ),
        "task_count": len(records),
        "success_count": sum(bool(record["success"]) for record in records),
        "status_counts": {
            status: sum(record["status"] == status for record in records)
            for status in sorted({record["status"] for record in records})
        },
        "total_candidates_used": sum(int(record.get("candidates_used", 0)) for record in records),
        "usage_total": usage,
        "all_ledgers_valid": all(record.get("ledger_valid", False) for record in records),
        "all_requests_isolated": all(record.get("request_isolation", False) for record in records),
        "all_resolved_to_k3": all(record.get("resolved_models") == ["k3"] for record in records if record.get("candidates_used", 0)),
        "sealed_judge_count_valid": all(
            record.get("sealed_events", 0) == record.get("sealed_files", -1)
            and 0 <= record.get("sealed_events", 0) <= record.get("candidates_used", 0)
            and (record["status"] != "verified_success" or record.get("sealed_events", 0) >= 1)
            for record in records
        ),
        "runs": records,
    }
    (output / "batch_summary.json").write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: document[key] for key in (
        "task_count", "success_count", "status_counts", "total_candidates_used",
        "all_ledgers_valid", "all_requests_isolated", "all_resolved_to_k3", "sealed_judge_count_valid",
    )}, ensure_ascii=False))
    return 0 if all(record["status"] != "batch_exception" for record in records) else 2


if __name__ == "__main__":
    raise SystemExit(main())

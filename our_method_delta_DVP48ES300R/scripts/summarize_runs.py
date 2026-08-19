#!/usr/bin/env python3
"""Create an auditable aggregate for completed harness run directories."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from plc_loop.ledger import EvidenceLedger


def add_numeric(target: dict, source: dict) -> None:
    for key, value in source.items():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            target[key] = target.get(key, 0) + value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("runs", nargs="+")
    args = parser.parse_args()
    output = Path(args.output).resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")

    records = []
    usage_total: dict[str, int | float] = {}
    for raw_run in args.runs:
        run = Path(raw_run).resolve()
        result = json.loads((run / "result.json").read_text(encoding="utf-8"))
        ledger_entries = EvidenceLedger.verify(run / "ledger.jsonl")
        sealed_events = sum(item["event_type"] == "sealed_judge_completed" for item in ledger_entries)
        add_numeric(usage_total, result.get("usage_total", {}))
        records.append({
            "run_dir": str(run),
            "task_id": result["task_id"],
            "method": result["method"],
            "status": result["status"],
            "success": result["success"],
            "candidates_used": result["candidates_used"],
            "requested_model": result["requested_model"],
            "resolved_models": result["resolved_models"],
            "usage_total": result.get("usage_total", {}),
            "sealed_result": result.get("sealed_result"),
            "ledger_events": len(ledger_entries),
            "ledger_final_hash": ledger_entries[-1]["event_hash"] if ledger_entries else None,
            "sealed_event_count": sealed_events,
        })

    document = {
        "schema_version": "1.0",
        "run_count": len(records),
        "verified_successes": sum(item["success"] for item in records),
        "total_candidates_used": sum(item["candidates_used"] for item in records),
        "usage_total": usage_total,
        "all_ledgers_valid": True,
        "all_sealed_judges_invoked_once": all(item["sealed_event_count"] == 1 for item in records),
        "runs": records,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "run_count": document["run_count"],
        "verified_successes": document["verified_successes"],
        "total_candidates_used": document["total_candidates_used"],
        "usage_total": document["usage_total"],
        "all_ledgers_valid": document["all_ledgers_valid"],
        "all_sealed_judges_invoked_once": document["all_sealed_judges_invoked_once"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

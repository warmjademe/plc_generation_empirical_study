#!/usr/bin/env python3
"""Re-run frozen validators on existing Direct@1 candidates without model calls."""

from __future__ import annotations

import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from pathlib import Path
from typing import Any

from plc_loop.dataset import load_task
from plc_loop.ledger import EvidenceLedger
from plc_loop.orchestrator import load_config
from plc_loop.validators import validators_from_config


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def classify(result: dict[str, Any]) -> str:
    if result.get("status") in {"infrastructure_error", "sealed_inconclusive"}:
        return "infrastructure_excluded"
    for attempt in result.get("attempts", []):
        for gate in attempt.get("gates", []):
            if gate.get("status") == "inconclusive":
                return "infrastructure_excluded"
            if any(item.get("kind") == "tool_error" for item in gate.get("evidence", [])):
                return "infrastructure_excluded"
    if (result.get("sealed_result") or {}).get("status") == "inconclusive":
        return "infrastructure_excluded"
    if result.get("status") == "verified_success":
        return "verified_success"
    if result.get("status") in {"candidate_budget_exhausted", "sealed_failure"}:
        return "semantic_failure"
    return "protocol_excluded"


def discover(source_roots: list[Path], categories: set[str]) -> dict[str, dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}
    for root in source_roots:
        for task_run in sorted(path for path in root.rglob("*") if path.is_dir()):
            task_id = task_run.name
            if task_id[:3] not in categories:
                continue
            candidate = task_run / "attempts" / "attempt_01" / "candidate.st"
            raw_response = task_run / "attempts" / "attempt_01" / "raw_response.json"
            if not candidate.is_file() or not raw_response.is_file():
                continue
            result_path = task_run / "result.json"
            source_class = "interrupted_after_model_response"
            source_result_sha256 = None
            if result_path.is_file():
                result = json.loads(result_path.read_text(encoding="utf-8"))
                source_class = classify(result)
                source_result_sha256 = sha256(result_path)
                if source_class != "infrastructure_excluded":
                    continue
                if int(result.get("candidates_used", -1)) != 1:
                    continue
            request_count = len(list(task_run.glob("attempts/attempt_*/request.json")))
            raw_response_count = len(list(task_run.glob("attempts/attempt_*/raw_response.json")))
            if request_count != 1 or raw_response_count != 1:
                raise RuntimeError(f"{task_id}: revalidation requires exactly one request and response")
            if task_id in candidates:
                raise RuntimeError(f"duplicate candidate source for {task_id}")
            candidates[task_id] = {
                "task_id": task_id,
                "candidate": candidate.resolve(),
                "candidate_sha256": sha256(candidate),
                "source_run": task_run.resolve(),
                "source_class": source_class,
                "source_result_sha256": source_result_sha256,
                "source_raw_response_sha256": sha256(raw_response),
            }
    return candidates


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--bank-root", required=True, type=Path)
    parser.add_argument("--source-run", required=True, action="append", type=Path)
    parser.add_argument("--category", required=True, action="append")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=5)
    parser.add_argument("--backend-timeout", type=int, default=600)
    parser.add_argument("--wall-timeout", type=int, default=7200)
    args = parser.parse_args()

    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty output: {output}")
    output.mkdir(parents=True, exist_ok=True)
    bank_root = args.bank_root.resolve()
    source_roots = [path.resolve() for path in args.source_run]
    candidates = discover(source_roots, set(args.category))
    if not candidates:
        raise RuntimeError("no inconclusive existing candidates were found")

    config = load_config(args.config.resolve())
    validators = {
        validator.name: validator
        for validator in validators_from_config(config["validators"], Path(config["_config_dir"]))
    }
    formal = validators["plcverif"]
    command = list(formal.command)
    index = command.index("--backend-timeout") + 1
    command[index] = str(args.backend_timeout)
    validators["plcverif"] = replace(
        formal, command=tuple(command), timeout_seconds=args.wall_timeout
    )
    ordered = [validators["compiler"], validators["plcverif"], validators["openplc"]]

    run_spec = {
        "schema_version": "1.0",
        "protocol": "existing-candidate MatIEC -> PLCverif -> OpenPLC revalidation; no model call",
        "config_sha256": sha256(args.config.resolve()),
        "bank_manifest_sha256": sha256(bank_root / "manifest.jsonl"),
        "source_runs": [str(path) for path in source_roots],
        "categories": sorted(set(args.category)),
        "backend_timeout_seconds": args.backend_timeout,
        "wall_timeout_seconds": args.wall_timeout,
        "candidate_count": len(candidates),
        "candidate_sha256": {task_id: row["candidate_sha256"] for task_id, row in sorted(candidates.items())},
    }
    write_json(output / "run_spec.json", run_spec)

    def validate(row: dict[str, Any]) -> dict[str, Any]:
        task_id = row["task_id"]
        task = load_task(bank_root / "tasks" / task_id)
        task_output = output / task_id
        task_output.mkdir()
        ledger = EvidenceLedger(task_output / "ledger.jsonl")
        ledger.append("revalidation_started", {
            "task_id": task_id,
            "candidate_sha256": row["candidate_sha256"],
            "source_raw_response_sha256": row["source_raw_response_sha256"],
            "model_called": False,
        })
        gates = []
        for validator in ordered:
            validator.preflight(task)
            gate = validator.run(task, row["candidate"], task_output)
            gates.append(gate.to_dict())
            ledger.append("gate_completed", {"task_id": task_id, "gate": gate.to_dict()})
            if gate.status in {"fail", "inconclusive"}:
                break
        statuses = {gate["name"]: gate["status"] for gate in gates}
        if any(value == "inconclusive" for value in statuses.values()):
            verdict = "infrastructure_excluded"
        elif any(value == "fail" for value in statuses.values()):
            verdict = "semantic_failure"
        elif all(statuses.get(name) == "pass" for name in ("compiler", "plcverif", "openplc")):
            verdict = "verified_success"
        else:
            verdict = "infrastructure_excluded"
        result = {
            "schema_version": "1.0",
            **row,
            "candidate": str(row["candidate"]),
            "source_run": str(row["source_run"]),
            "model_called": False,
            "gates": gates,
            "verdict": verdict,
        }
        write_json(task_output / "revalidation.json", result)
        ledger.append("revalidation_completed", {"task_id": task_id, "verdict": verdict})
        return result

    records = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(validate, row): task_id for task_id, row in candidates.items()}
        for future in as_completed(futures):
            task_id = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                result = {"task_id": task_id, "verdict": "infrastructure_excluded", "error": f"{type(exc).__name__}: {exc}"}
            records.append(result)
            print(json.dumps({"task_id": task_id, "verdict": result["verdict"], "error": result.get("error")}, ensure_ascii=False), flush=True)
            write_json(output / "progress.json", sorted(records, key=lambda item: item["task_id"]))
    records.sort(key=lambda item: item["task_id"])
    summary = {
        **run_spec,
        "completed_count": len(records),
        "verdict_counts": {
            verdict: sum(record.get("verdict") == verdict for record in records)
            for verdict in sorted({str(record.get("verdict")) for record in records})
        },
        "runs": records,
    }
    write_json(output / "revalidation_summary.json", summary)
    print(json.dumps({"completed_count": len(records), "verdict_counts": summary["verdict_counts"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

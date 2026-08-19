#!/usr/bin/env python3
"""Assemble a frozen, category-balanced Direct@1 screening dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from plc_loop.ledger import EvidenceLedger


SCREENING_FAILURE_STATUSES = {"candidate_budget_exhausted", "sealed_failure"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_qualified(roots: list[Path]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for root in roots:
        for path in root.glob("*/qualification.json"):
            record = json.loads(path.read_text(encoding="utf-8"))
            task_id = str(record["task_id"])
            if task_id in records and records[task_id] != record:
                raise RuntimeError(f"conflicting qualification records for {task_id}")
            if record.get("qualified") is True:
                records[task_id] = record
    return records


def classify_screening(result: dict[str, Any]) -> str:
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
    if result.get("status") in SCREENING_FAILURE_STATUSES:
        return "screening_failure"
    return "protocol_excluded"


def load_failures(
    roots: list[Path],
    revalidation_roots: list[Path],
    qualified: dict[str, dict[str, Any]],
    verified_backfill_ids: set[str],
    excluded_task_ids: set[str],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    failures: dict[str, dict[str, Any]] = {}
    verified_backfills: dict[str, dict[str, Any]] = {}
    terminal_verdicts: dict[str, set[str]] = defaultdict(set)
    for root in roots:
        for path in root.rglob("result.json"):
            result = json.loads(path.read_text(encoding="utf-8"))
            task_id = str(result.get("task_id") or path.parent.name)
            if task_id in excluded_task_ids:
                continue
            status = str(result.get("status"))
            result_class = classify_screening(result)
            if result_class in {"screening_failure", "verified_success"}:
                terminal_verdicts[task_id].add(result_class)
            if result_class != "screening_failure" and not (
                result_class == "verified_success" and task_id in verified_backfill_ids
            ):
                continue
            if task_id not in qualified:
                raise RuntimeError(f"selected model verdict is not qualification-backed: {task_id}")
            if int(result.get("candidates_used", -1)) != 1:
                raise RuntimeError(f"Direct@1 candidate count mismatch for {task_id}")
            ledger_path = path.parent / "ledger.jsonl"
            if not ledger_path.is_file() or not EvidenceLedger.verify(ledger_path):
                raise RuntimeError(f"missing or invalid evidence ledger for {task_id}")
            destination = failures if result_class == "screening_failure" else verified_backfills
            if task_id in destination:
                raise RuntimeError(f"duplicate {result_class} verdict for {task_id}")
            destination[task_id] = {
                "task_id": task_id,
                "category_id": task_id[:3],
                "outcome_class": result_class,
                "status": status,
                "requested_model": result.get("requested_model"),
                "resolved_models": result.get("resolved_models", []),
                "evidence_kind": "screening",
                "result_path": path,
                "source_model_run_path": path.parent,
                "result_sha256": sha256(path),
                "ledger_sha256": sha256(ledger_path),
            }
    for root in revalidation_roots:
        for path in root.rglob("revalidation.json"):
            result = json.loads(path.read_text(encoding="utf-8"))
            if result.get("verdict") != "semantic_failure":
                continue
            task_id = str(result["task_id"])
            if task_id not in qualified:
                raise RuntimeError(f"revalidated semantic failure is not qualification-backed: {task_id}")
            ledger_path = path.parent / "ledger.jsonl"
            if not ledger_path.is_file() or not EvidenceLedger.verify(ledger_path):
                raise RuntimeError(f"missing or invalid revalidation ledger for {task_id}")
            if result.get("model_called") is not False:
                raise RuntimeError(f"revalidation unexpectedly called a model for {task_id}")
            if task_id in failures:
                raise RuntimeError(f"duplicate semantic-failure verdict for {task_id}")
            source_model_run = Path(str(result["source_run"]))
            raw_response = source_model_run / "attempts" / "attempt_01" / "raw_response.json"
            candidate = source_model_run / "attempts" / "attempt_01" / "candidate.st"
            if not raw_response.is_file() or not candidate.is_file():
                raise RuntimeError(f"missing original Direct@1 evidence for revalidated {task_id}")
            if sha256(raw_response) != result.get("source_raw_response_sha256"):
                raise RuntimeError(f"source response hash mismatch for {task_id}")
            if sha256(candidate) != result.get("candidate_sha256"):
                raise RuntimeError(f"source candidate hash mismatch for {task_id}")
            failures[task_id] = {
                "task_id": task_id,
                "category_id": task_id[:3],
                "outcome_class": "screening_failure",
                "status": "semantic_failure_after_revalidation",
                "requested_model": None,
                "resolved_models": [],
                "evidence_kind": "revalidation",
                "result_path": path,
                "source_model_run_path": source_model_run,
                "result_sha256": sha256(path),
                "ledger_sha256": sha256(ledger_path),
            }
    conflicts = {
        task_id: sorted(statuses)
        for task_id, statuses in terminal_verdicts.items()
        if "verified_success" in statuses and "screening_failure" in statuses
    }
    if conflicts:
        raise RuntimeError(f"conflicting terminal model verdicts: {conflicts}")
    missing_backfills = sorted(verified_backfill_ids - set(verified_backfills))
    if missing_backfills:
        raise RuntimeError(f"requested verified-success backfills were not found: {missing_backfills}")
    return failures, verified_backfills


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bank-root", required=True, action="append", type=Path)
    parser.add_argument("--qualification", required=True, action="append", type=Path)
    parser.add_argument("--screening", required=True, action="append", type=Path)
    parser.add_argument("--revalidation", action="append", default=[], type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--per-category", type=int, default=5)
    parser.add_argument("--verified-success-backfill-task-id", action="append", default=[])
    parser.add_argument("--exclude-task-id", action="append", default=[])
    args = parser.parse_args()

    bank_roots = [path.resolve() for path in args.bank_root]
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty output: {output}")
    output.mkdir(parents=True, exist_ok=True)

    qualification_roots = [path.resolve() for path in args.qualification]
    screening_roots = [path.resolve() for path in args.screening]
    revalidation_roots = [path.resolve() for path in args.revalidation]
    qualified = load_qualified(qualification_roots)
    requested_backfills = set(args.verified_success_backfill_task_id)
    excluded_task_ids = set(args.exclude_task_id)
    if requested_backfills & excluded_task_ids:
        raise ValueError("a verified-success backfill cannot also be excluded")
    failures, verified_backfills = load_failures(
        screening_roots, revalidation_roots, qualified, requested_backfills, excluded_task_ids
    )
    categories = [f"C{index:02d}" for index in range(1, 11)]
    by_category: dict[str, list[str]] = {
        category: sorted(task_id for task_id in failures if task_id.startswith(category + "_"))
        for category in categories
    }
    selected: list[str] = []
    for category in categories:
        chosen = by_category[category][: args.per_category]
        deficit = args.per_category - len(chosen)
        if deficit:
            eligible_backfills = sorted(
                task_id for task_id in verified_backfills if task_id.startswith(category + "_")
            )
            chosen.extend(eligible_backfills[:deficit])
        if len(chosen) != args.per_category:
            raise RuntimeError(
                f"balanced target is not met for {category}: missing {args.per_category - len(chosen)}"
            )
        selected.extend(chosen)
    selected_outcomes = {**failures, **verified_backfills}
    unused_backfills = sorted(requested_backfills - set(selected))
    if unused_backfills:
        raise RuntimeError(f"requested verified-success backfills were not needed: {unused_backfills}")

    tasks_output = output / "tasks"
    screening_output = output / "evidence" / "screening"
    revalidation_output = output / "evidence" / "revalidation"
    qualification_output = output / "evidence" / "qualification"
    tasks_output.mkdir(parents=True)
    screening_output.mkdir(parents=True)
    revalidation_output.mkdir(parents=True)
    qualification_output.mkdir(parents=True)
    task_sources: dict[str, Path] = {}
    manifest_by_id: dict[str, dict[str, Any]] = {}
    source_bank_by_id: dict[str, Path] = {}
    for bank_root in bank_roots:
        for record_line in (bank_root / "manifest.jsonl").read_text(encoding="utf-8").splitlines():
            if not record_line.strip():
                continue
            record = json.loads(record_line)
            task_id = str(record["id"])
            if task_id in task_sources:
                raise RuntimeError(f"duplicate task ID across source banks: {task_id}")
            task_sources[task_id] = bank_root / "tasks" / task_id
            manifest_by_id[task_id] = record
            source_bank_by_id[task_id] = bank_root
    missing_sources = sorted(set(selected) - set(task_sources))
    if missing_sources:
        raise RuntimeError(f"selected tasks are missing from source banks: {missing_sources}")

    for task_id in selected:
        shutil.copytree(task_sources[task_id], tasks_output / task_id)
        source_result = Path(selected_outcomes[task_id]["result_path"])
        source_model_run = Path(selected_outcomes[task_id]["source_model_run_path"])
        shutil.copytree(source_model_run, screening_output / task_id)
        if selected_outcomes[task_id]["evidence_kind"] == "revalidation":
            shutil.copytree(source_result.parent, revalidation_output / task_id)
        write_json(qualification_output / f"{task_id}.json", qualified[task_id])

    with (output / "manifest.jsonl").open("w", encoding="utf-8") as handle:
        for task_id in selected:
            record = dict(manifest_by_id[task_id])
            record["source_bank"] = source_bank_by_id[task_id].name
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    selected_records = []
    for task_id in selected:
        item = dict(selected_outcomes[task_id])
        item["source_model_run_path"] = f"evidence/screening/{task_id}"
        item["result_path"] = (
            f"evidence/revalidation/{task_id}/revalidation.json"
            if item["evidence_kind"] == "revalidation"
            else f"evidence/screening/{task_id}/result.json"
        )
        item["qualification_path"] = f"evidence/qualification/{task_id}.json"
        selected_records.append(item)
    document = {
        "schema_version": "1.0",
        "selection_protocol": "first five qualification-backed Kimi-K3 Direct@1 screening failures in frozen task-ID order per category; explicit verified-success backfill only where the user stopped further failure search",
        "task_count": len(selected),
        "category_count": len(categories),
        "per_category": args.per_category,
        "category_counts": dict(Counter(task_id[:3] for task_id in selected)),
        "outcome_counts": dict(Counter(item["outcome_class"] for item in selected_records)),
        "verified_success_backfill_task_ids": sorted(requested_backfills),
        "excluded_task_ids": sorted(excluded_task_ids),
        "source_banks": [
            {
                "path": str(bank_root),
                "manifest_sha256": sha256(bank_root / "manifest.jsonl"),
            }
            for bank_root in bank_roots
        ],
        "output_manifest_sha256": sha256(output / "manifest.jsonl"),
        "qualification_roots": [str(path) for path in qualification_roots],
        "screening_roots": [str(path) for path in screening_roots],
        "revalidation_roots": [str(path) for path in revalidation_roots],
        "selected_tasks": selected_records,
    }
    write_json(output / "selection.json", document)
    write_json(output / "dataset_summary.json", {
        "schema_version": "1.0",
        "dataset_name": "PLC Generation Balanced-50",
        "task_count": len(selected),
        "category_counts": document["category_counts"],
        "outcome_counts": document["outcome_counts"],
        "selection_sha256": sha256(output / "selection.json"),
        "manifest_sha256": document["output_manifest_sha256"],
    })
    print(json.dumps({
        "status": "pass", "task_count": len(selected),
        "category_counts": document["category_counts"], "output": str(output),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

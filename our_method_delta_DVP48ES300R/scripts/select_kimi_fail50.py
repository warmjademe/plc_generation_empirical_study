#!/usr/bin/env python3
"""Freeze 50 Kimi-K3 failures with equal categories and balanced base roles."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def choose_role_balanced(records: list[dict[str, Any]], bank_root: Path, count: int) -> tuple[list[dict[str, Any]], dict]:
    """Choose a fixed-size subset maximizing distinct A/B base-role coverage."""
    metadata = {
        record["task_id"]: json.loads((bank_root / "tasks" / record["task_id"] / "metadata.json").read_text(encoding="utf-8"))
        for record in records
    }

    def key(combination: tuple[dict[str, Any], ...]) -> tuple[int, int, str]:
        left = Counter(metadata[item["task_id"]]["composition"]["base_a"] for item in combination)
        right = Counter(metadata[item["task_id"]]["composition"]["base_b"] for item in combination)
        coverage = len(left) + len(right)
        concentration = sum(value * value for value in left.values()) + sum(value * value for value in right.values())
        names = "|".join(sorted(item["task_id"] for item in combination))
        tie_break = hashlib.sha256(("K3-Fail-50-role-balance-v1:" + names).encode("utf-8")).hexdigest()
        return (-coverage, concentration, tie_break)

    selected_tuple = min(itertools.combinations(records, count), key=key)
    selected = sorted(selected_tuple, key=lambda item: item["task_id"])
    left = Counter(metadata[item["task_id"]]["composition"]["base_a"] for item in selected)
    right = Counter(metadata[item["task_id"]]["composition"]["base_b"] for item in selected)
    return selected, {
        "distinct_base_a": len(left), "distinct_base_b": len(right),
        "base_a_counts": dict(sorted(left.items())), "base_b_counts": dict(sorted(right.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bank-root", required=True, type=Path)
    parser.add_argument("--screening-summary", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--per-category", type=int, default=5)
    args = parser.parse_args()
    bank_root = args.bank_root.resolve()
    summary_path = args.screening_summary.resolve()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("task_count") != 200:
        raise RuntimeError("selection requires a complete 200-task screening run")
    if summary.get("bank_manifest_sha256") != sha256(bank_root / "manifest.jsonl"):
        raise RuntimeError("screening summary does not match the task-bank manifest")
    if not all(summary.get(key) for key in (
        "all_ledgers_valid", "all_requests_isolated", "all_candidates_exactly_once", "all_resolved_to_k3",
    )):
        raise RuntimeError("screening protocol checks did not all pass")

    eligible: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in summary["runs"]:
        if record.get("selection_eligible"):
            eligible[record["task_id"].split("_", 1)[0]].append(record)
    categories = [f"C{number:02d}" for number in range(1, 11)]
    shortfalls = {
        category: args.per_category - len(eligible[category])
        for category in categories if len(eligible[category]) < args.per_category
    }
    if shortfalls:
        print(json.dumps({
            "status": "insufficient_failures", "shortfalls": shortfalls,
            "policy": "do not fill one category with another category; revise or extend the frozen bank before selection",
        }, ensure_ascii=False))
        return 2
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite selected dataset {output}")
    (output / "tasks").mkdir(parents=True)

    selections = []
    source_manifest = {
        item["id"]: item
        for item in (
            json.loads(line) for line in (bank_root / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
        )
    }
    for category in categories:
        selected, role_balance = choose_role_balanced(eligible[category], bank_root, args.per_category)
        for position, record in enumerate(selected, start=1):
            task_id = record["task_id"]
            source = bank_root / "tasks" / task_id
            destination = output / "tasks" / task_id
            shutil.copytree(source, destination)
            selections.append({
                **source_manifest[task_id],
                "category_selection_rank": position,
                "selection_reason": "Kimi-K3 Direct@1 semantic failure",
                "category_role_balance": role_balance,
            })
    with (output / "manifest.jsonl").open("w", encoding="utf-8") as handle:
        for record in sorted(selections, key=lambda item: item["id"]):
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    write_json(output / "dataset_summary.json", {
        "dataset": "IEC-ST-VerifyBench-K3-Fail-50",
        "version": "1.0.0-screened",
        "task_count": len(selections),
        "category_counts": {category: args.per_category for category in categories},
        "source_bank_manifest_sha256": sha256(bank_root / "manifest.jsonl"),
        "screening_summary_sha256": sha256(summary_path),
        "screening_model": "Kimi-K3",
        "screening_protocol": "one isolated direct candidate per task",
        "difficulty_stratification": "not_used",
        "selection_rule": "five semantic failures per category; maximize distinct base behaviors in A/B roles; minimize role concentration; seeded hash tie-break",
        "screening_calls_excluded_from_later_baseline_scores": True,
        "construct_validity_limit": "model-conditioned challenge set; not an unbiased estimate of performance on all IEC ST tasks",
    })
    print(json.dumps({
        "status": "pass", "selected": len(selections),
        "category_counts": {category: args.per_category for category in categories},
        "output": str(output),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

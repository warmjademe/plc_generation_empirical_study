#!/usr/bin/env python3
"""Reconstruct RQ4 budget--effectiveness curves from one frozen DeepSeek run.

The analyzer never calls a model or a validator.  It truncates the immutable
K=10 attempt traces, so every K point uses the same realized candidate prefix.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


MODEL_ID = "deepseek-v4-flash"
DEFAULT_BUDGETS = (1, 3, 5, 7, 10)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def parse_budgets(text: str) -> tuple[int, ...]:
    values = tuple(sorted({int(item.strip()) for item in text.split(",") if item.strip()}))
    if not values or values[0] < 1 or values[-1] > 10:
        raise ValueError("budgets must be distinct integers in [1, 10]")
    return values


def usage_sum(attempts: Iterable[dict[str, Any]]) -> Counter[str]:
    total: Counter[str] = Counter()
    for attempt in attempts:
        usage = attempt.get("usage") or {}
        for key in (
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "prompt_cache_hit_tokens",
            "prompt_cache_miss_tokens",
        ):
            value = usage.get(key, 0)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                total[key] += value
    return total


def stage_ms(
    attempts: Iterable[dict[str, Any]], sealed_attempts: Iterable[dict[str, Any]]
) -> Counter[str]:
    durations: Counter[str] = Counter()
    for attempt in attempts:
        for gate in attempt.get("gates") or []:
            durations[str(gate.get("name"))] += int(gate.get("duration_ms") or 0)
    for sealed in sealed_attempts:
        durations["openplc_sealed"] += int(
            (sealed.get("result") or {}).get("duration_ms") or 0
        )
    return durations


def estimate_usd(usage: Counter[str], prices: dict[str, float]) -> float:
    return (
        usage["prompt_cache_hit_tokens"] * prices["input_cache_hit_per_million"]
        + usage["prompt_cache_miss_tokens"] * prices["input_cache_miss_per_million"]
        + usage["completion_tokens"] * prices["output_per_million"]
    ) / 1_000_000


def validate_summary(summary: dict[str, Any], run_root: Path) -> None:
    required_true = (
        "all_ledgers_valid",
        "all_model_identities_valid",
        "sealed_judge_count_valid",
        "inconclusive_restart_count_valid",
    )
    if summary.get("task_count") != 100 or len(summary.get("runs") or []) != 100:
        raise ValueError("RQ4 requires exactly 100 completed tasks")
    if summary.get("method") != "evidence" or summary.get("requested_model") != MODEL_ID:
        raise ValueError("RQ4 requires the frozen full method on deepseek-v4-flash")
    if not all(summary.get(field) is True for field in required_true):
        raise ValueError("the input batch failed its protocol audit")
    if not run_root.is_dir():
        raise FileNotFoundError(run_root)


def load_tasks(summary: dict[str, Any], run_root: Path) -> list[dict[str, Any]]:
    tasks = []
    expected_config = summary.get("config_sha256")
    for record in sorted(summary["runs"], key=lambda item: item["task_id"]):
        task_id = str(record["task_id"])
        result_path = run_root / task_id / "result.json"
        ledger_path = run_root / task_id / "ledger.jsonl"
        result = read_json(result_path)
        if result.get("task_id") != task_id:
            raise ValueError(f"task identity mismatch for {task_id}")
        if result.get("requested_model") != MODEL_ID:
            raise ValueError(f"model identity mismatch for {task_id}")
        if result.get("candidate_budget") != 10:
            raise ValueError(f"candidate budget mismatch for {task_id}")
        if result.get("config_sha256") != expected_config:
            raise ValueError(f"configuration mismatch for {task_id}")
        attempts = sorted(result.get("attempts") or [], key=lambda item: item["number"])
        if len(attempts) != result.get("candidates_used"):
            raise ValueError(f"attempt accounting mismatch for {task_id}")
        ledgers = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines()]
        tasks.append(
            {
                "task_id": task_id,
                "category": task_id.split("_", 1)[0],
                "result": result,
                "attempts": attempts,
                "ledger": ledgers,
                "result_sha256": sha256(result_path),
                "ledger_sha256": sha256(ledger_path),
            }
        )
    return tasks


def task_prefix(task: dict[str, Any], budget: int) -> dict[str, Any]:
    result = task["result"]
    attempts = [item for item in task["attempts"] if int(item["number"]) <= budget]
    sealed = [
        item for item in result.get("sealed_attempts") or []
        if int(item["attempt"]) <= budget
    ]
    success = any((item.get("result") or {}).get("status") == "pass" for item in sealed)
    terminal_infrastructure = bool(
        result.get("status") == "infrastructure_error"
        and int(result.get("candidates_used", 0)) <= budget
    )
    return {
        "success": success,
        "infrastructure": terminal_infrastructure,
        "candidate_count": len(attempts),
        "usage": usage_sum(attempts),
        "stage_ms": stage_ms(attempts, sealed),
    }


def aggregate_budget(
    tasks: list[dict[str, Any]], budget: int, prices: dict[str, float]
) -> dict[str, Any]:
    prefixes = [task_prefix(task, budget) for task in tasks]
    success = sum(item["success"] for item in prefixes)
    infrastructure = sum(item["infrastructure"] for item in prefixes)
    usage: Counter[str] = Counter()
    stages: Counter[str] = Counter()
    for item in prefixes:
        usage.update(item["usage"])
        stages.update(item["stage_ms"])
    candidate_count = sum(item["candidate_count"] for item in prefixes)
    estimated_cost = estimate_usd(usage, prices)
    return {
        "budget": budget,
        "success_count": success,
        "success_rate_lower": success / len(tasks),
        "success_rate_upper": (success + infrastructure) / len(tasks),
        "terminal_infrastructure_count": infrastructure,
        "candidate_count": candidate_count,
        **{key: int(usage[key]) for key in sorted(usage)},
        "estimated_api_cost_usd": estimated_cost,
        "validator_work_seconds": sum(stages.values()) / 1000,
        "stage_seconds": {
            key: value / 1000 for key, value in sorted(stages.items())
        },
        "candidates_per_success": candidate_count / success if success else None,
        "tokens_per_success": usage["total_tokens"] / success if success else None,
        "api_cost_usd_per_success": estimated_cost / success if success else None,
        "validator_seconds_per_success": (
            sum(stages.values()) / 1000 / success if success else None
        ),
    }


def add_marginal_costs(rows: list[dict[str, Any]]) -> None:
    previous = {
        "budget": 0,
        "success_count": 0,
        "candidate_count": 0,
        "total_tokens": 0,
        "estimated_api_cost_usd": 0.0,
        "validator_work_seconds": 0.0,
    }
    for row in rows:
        added_success = row["success_count"] - previous["success_count"]
        added_candidates = row["candidate_count"] - previous["candidate_count"]
        added_tokens = row["total_tokens"] - previous["total_tokens"]
        added_cost = row["estimated_api_cost_usd"] - previous["estimated_api_cost_usd"]
        added_validator = (
            row["validator_work_seconds"]
            - previous["validator_work_seconds"]
        )
        row.update(
            {
                "previous_budget": previous["budget"],
                "added_successes": added_success,
                "added_candidates": added_candidates,
                "added_tokens": added_tokens,
                "added_api_cost_usd": added_cost,
                "added_validator_seconds": added_validator,
                "marginal_candidates_per_added_success": (
                    added_candidates / added_success if added_success else None
                ),
                "marginal_tokens_per_added_success": (
                    added_tokens / added_success if added_success else None
                ),
            }
        )
        previous = row


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(probability * len(ordered)))]


def add_bootstrap_intervals(
    rows: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
    prices: dict[str, float],
    *,
    samples: int,
    seed: int,
) -> None:
    """Add paired task-bootstrap intervals without treating attempts as samples."""
    if samples < 100:
        raise ValueError("bootstrap samples must be at least 100")
    budgets = [int(row["budget"]) for row in rows]
    prefixes = {
        budget: [task_prefix(task, budget) for task in tasks]
        for budget in budgets
    }
    generator = random.Random(seed)
    distributions = {
        budget: defaultdict(list) for budget in budgets
    }
    marginal_distributions = {budget: [] for budget in budgets}
    size = len(tasks)
    for _ in range(samples):
        indices = [generator.randrange(size) for _ in range(size)]
        prior_success = 0
        for budget in budgets:
            selected = [prefixes[budget][index] for index in indices]
            success = sum(item["success"] for item in selected)
            candidates = sum(item["candidate_count"] for item in selected)
            usage: Counter[str] = Counter()
            validator_ms = 0
            for item in selected:
                usage.update(item["usage"])
                validator_ms += sum(item["stage_ms"].values())
            values = distributions[budget]
            values["success_rate"].append(success / size)
            if success:
                values["candidates_per_success"].append(candidates / success)
                values["tokens_per_success"].append(usage["total_tokens"] / success)
                values["api_cost_usd_per_success"].append(
                    estimate_usd(usage, prices) / success
                )
                values["validator_seconds_per_success"].append(
                    validator_ms / 1000 / success
                )
            marginal_distributions[budget].append((success - prior_success) / size)
            prior_success = success
    for row in rows:
        budget = int(row["budget"])
        for metric, values in distributions[budget].items():
            row[f"{metric}_ci95"] = [
                percentile(values, 0.025), percentile(values, 0.975)
            ]
        row["added_success_rate_ci95"] = [
            percentile(marginal_distributions[budget], 0.025),
            percentile(marginal_distributions[budget], 0.975),
        ]


def sealed_sensitivity(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for limit in (1, 2, 3):
        success = 0
        candidates = 0
        for task in tasks:
            result = task["result"]
            sealed = sorted(
                result.get("sealed_attempts") or [], key=lambda item: item["attempt"]
            )
            considered = sealed[:limit]
            success += any(
                (item.get("result") or {}).get("status") == "pass"
                for item in considered
            )
            cap = int(considered[-1]["attempt"]) if len(sealed) >= limit else 10
            candidates += sum(int(item["number"]) <= cap for item in task["attempts"])
        rows.append(
            {
                "parameter": "max_sealed_attempts",
                "value": limit,
                "success_count": success,
                "candidate_count": candidates,
                "identification": "observed-trace terminal truncation",
            }
        )
    return rows


def inconclusive_sensitivity(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actual_success = sum(bool(task["result"].get("success")) for task in tasks)
    recovered = 0
    restart_tasks = 0
    for task in tasks:
        events = [
            event for event in task["ledger"]
            if event.get("event_type") == "inconclusive_blind_restart_scheduled"
        ]
        if events:
            restart_tasks += 1
            recovered += bool(task["result"].get("success"))
    return [
        {
            "parameter": "max_inconclusive_restarts",
            "value": 0,
            "success_count": actual_success - recovered,
            "affected_task_count": restart_tasks,
            "identification": "observed-trace terminal truncation",
        },
        {
            "parameter": "max_inconclusive_restarts",
            "value": 1,
            "success_count": actual_success,
            "affected_task_count": restart_tasks,
            "identification": "observed configuration",
        },
    ]


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--budgets", default=",".join(map(str, DEFAULT_BUDGETS)))
    parser.add_argument("--price-date", default="2026-08-13")
    parser.add_argument(
        "--price-source",
        default="https://api-docs.deepseek.com/quick_start/pricing",
    )
    parser.add_argument("--cache-hit-usd-per-million", type=float, default=0.0028)
    parser.add_argument("--cache-miss-usd-per-million", type=float, default=0.14)
    parser.add_argument("--output-usd-per-million", type=float, default=0.28)
    parser.add_argument("--bootstrap", type=int, default=20000)
    parser.add_argument("--bootstrap-seed", type=int, default=20260813)
    args = parser.parse_args()

    budgets = parse_budgets(args.budgets)
    run_root = args.run_root.resolve()
    summary_path = run_root / "batch_summary.json"
    summary = read_json(summary_path)
    validate_summary(summary, run_root)
    tasks = load_tasks(summary, run_root)
    prices = {
        "input_cache_hit_per_million": args.cache_hit_usd_per_million,
        "input_cache_miss_per_million": args.cache_miss_usd_per_million,
        "output_per_million": args.output_usd_per_million,
    }
    budget_rows = [aggregate_budget(tasks, budget, prices) for budget in budgets]
    add_marginal_costs(budget_rows)
    add_bootstrap_intervals(
        budget_rows,
        tasks,
        prices,
        samples=args.bootstrap,
        seed=args.bootstrap_seed,
    )
    sensitivity = sealed_sensitivity(tasks) + inconclusive_sensitivity(tasks)

    task_rows = []
    for task in tasks:
        row: dict[str, Any] = {
            "task_id": task["task_id"],
            "category": task["category"],
            "result_sha256": task["result_sha256"],
            "ledger_sha256": task["ledger_sha256"],
        }
        for budget in budgets:
            prefix = task_prefix(task, budget)
            row[f"success_at_{budget}"] = int(prefix["success"])
            row[f"candidates_at_{budget}"] = prefix["candidate_count"]
            row[f"tokens_at_{budget}"] = int(prefix["usage"]["total_tokens"])
        task_rows.append(row)

    document = {
        "schema_version": "1.0",
        "research_question": "RQ4 frozen-trace candidate-budget efficiency",
        "model": MODEL_ID,
        "task_count": len(tasks),
        "budgets": list(budgets),
        "bootstrap_samples": args.bootstrap,
        "bootstrap_seed": args.bootstrap_seed,
        "input": {
            "batch_summary_file": summary_path.name,
            "batch_summary_sha256": sha256(summary_path),
            "config_sha256": summary.get("config_sha256"),
            "dataset_manifest_sha256": summary.get("dataset_manifest_sha256"),
            "all_ledgers_valid": summary.get("all_ledgers_valid"),
            "all_model_identities_valid": summary.get("all_model_identities_valid"),
        },
        "pricing": {
            "currency": "USD",
            "unit": "per_million_tokens",
            "snapshot_date": args.price_date,
            "source": args.price_source,
            **prices,
        },
        "budget_efficiency": budget_rows,
        "restart_sensitivity": sensitivity,
        "interpretation_limits": [
            "K points are prefixes of one frozen K=10 stochastic run, not independent reruns",
            "validator time is the sum of per-gate durations, not parallel batch wall-clock time",
            "pricing is a dated tariff estimate and excludes non-API infrastructure costs",
            "E_max and R_max results identify only terminal truncations of observed traces",
        ],
    }
    if args.output.exists() and any(args.output.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty output: {args.output}")
    args.output.mkdir(parents=True, exist_ok=True)
    write_json(args.output / "rq4_results.json", document)
    write_csv(
        args.output / "budget_efficiency.csv",
        budget_rows,
        [
            "budget", "success_count", "success_rate_lower", "success_rate_upper",
            "terminal_infrastructure_count", "candidate_count", "prompt_tokens",
            "completion_tokens", "total_tokens", "prompt_cache_hit_tokens",
            "prompt_cache_miss_tokens", "estimated_api_cost_usd",
            "validator_work_seconds", "candidates_per_success",
            "tokens_per_success", "api_cost_usd_per_success",
            "validator_seconds_per_success", "previous_budget", "added_successes",
            "added_candidates", "added_tokens", "added_api_cost_usd",
            "added_validator_seconds", "marginal_candidates_per_added_success",
            "marginal_tokens_per_added_success", "success_rate_ci95",
            "candidates_per_success_ci95", "tokens_per_success_ci95",
            "api_cost_usd_per_success_ci95", "validator_seconds_per_success_ci95",
            "added_success_rate_ci95",
        ],
    )
    write_csv(
        args.output / "restart_sensitivity.csv",
        sensitivity,
        ["parameter", "value", "success_count", "candidate_count", "affected_task_count", "identification"],
    )
    write_csv(args.output / "task_budget_outcomes.csv", task_rows, list(task_rows[0]))
    print(json.dumps(document, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

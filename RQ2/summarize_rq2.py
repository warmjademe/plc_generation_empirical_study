#!/usr/bin/env python3
"""Derive paired RQ2 statistics from one full and two ablation summaries."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from collections import Counter
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_map(summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(record["task_id"]): record for record in summary["runs"]}


def exact_mcnemar(n10: int, n01: int) -> float:
    discordant = n10 + n01
    if discordant == 0:
        return 1.0
    tail = sum(math.comb(discordant, i) for i in range(min(n10, n01) + 1))
    return min(1.0, 2.0 * tail / (2**discordant))


def bootstrap_risk_difference(
    full: dict[str, dict[str, Any]],
    ablated: dict[str, dict[str, Any]],
    task_ids: list[str],
    *,
    samples: int,
    seed: int,
) -> tuple[float, float]:
    generator = random.Random(seed)
    size = len(task_ids)
    values = []
    for _ in range(samples):
        selected = [task_ids[generator.randrange(size)] for _ in range(size)]
        values.append(
            sum(
                int(bool(full[task]["success"]))
                - int(bool(ablated[task]["success"]))
                for task in selected
            )
            / size
        )
    values.sort()
    return (
        values[int(0.025 * samples)],
        values[min(samples - 1, int(0.975 * samples))],
    )


def paired_risk_difference(
    full: dict[str, dict[str, Any]],
    ablated: dict[str, dict[str, Any]],
    task_ids: list[str],
) -> float:
    return sum(
        int(bool(full[task]["success"]))
        - int(bool(ablated[task]["success"]))
        for task in task_ids
    ) / len(task_ids)


def bh_adjust(rows: list[dict[str, Any]]) -> None:
    ordered = sorted(enumerate(rows), key=lambda pair: pair[1]["p_exact"])
    running = 1.0
    adjusted = [1.0] * len(rows)
    for reverse_rank in range(len(ordered) - 1, -1, -1):
        original_index, row = ordered[reverse_rank]
        rank = reverse_rank + 1
        running = min(running, row["p_exact"] * len(rows) / rank)
        adjusted[original_index] = min(1.0, running)
    for row, value in zip(rows, adjusted):
        row["p_bh"] = value


def validate(
    full: dict[str, Any], m01: dict[str, Any], m10: dict[str, Any]
) -> list[str]:
    summaries = {"full": full, "M01": m01, "M10": m10}
    identifiers = {name: set(run_map(value)) for name, value in summaries.items()}
    if any(value.get("task_count") != 100 for value in summaries.values()):
        raise ValueError("every RQ2 summary must contain exactly 100 tasks")
    if any(len(identifiers[name]) != 100 for name in summaries):
        raise ValueError("every RQ2 summary must contain 100 unique task IDs")
    if len({frozenset(value) for value in identifiers.values()}) != 1:
        raise ValueError("full and ablation summaries do not contain the same task IDs")
    if any(value.get("requested_model") != "deepseek-v4-flash" for value in summaries.values()):
        raise ValueError("RQ2 requires the exact deepseek-v4-flash model identifier")
    if full.get("method") != "evidence":
        raise ValueError("the RQ2 full control must use the evidence method")
    dataset_hashes = {value.get("dataset_manifest_sha256") for value in summaries.values()}
    if len(dataset_hashes) != 1 or None in dataset_hashes:
        raise ValueError("full and ablation summaries must use the same dataset manifest")
    for name, summary in summaries.items():
        if summary.get("status_counts", {}).get("batch_exception", 0):
            raise ValueError(f"{name} contains a batch exception")
        if summary.get("success_count") != sum(
            bool(record.get("success")) for record in summary.get("runs") or []
        ):
            raise ValueError(f"{name} success accounting is inconsistent")
        if not (
            summary.get("all_ledgers_valid")
            and summary.get("all_model_identities_valid")
            and summary.get("sealed_judge_count_valid")
            and summary.get("inconclusive_restart_count_valid")
        ):
            raise ValueError(f"{name} failed batch protocol audit")
    expected = {
        "M01": ("M01_without_component_1", False, True),
        "M10": ("M10_without_component_2", True, False),
    }
    for name, summary in (("M01", m01), ("M10", m10)):
        observed = (
            summary.get("ablation_id"),
            summary.get("core_component_1_enabled"),
            summary.get("core_component_2_enabled"),
        )
        if observed != expected[name]:
            raise ValueError(f"{name} protocol mismatch: {observed!r}")
    return sorted(identifiers["full"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", required=True, type=Path)
    parser.add_argument("--m01", required=True, type=Path)
    parser.add_argument("--m10", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--bootstrap", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=20260813)
    args = parser.parse_args()

    full, m01, m10 = map(read_json, (args.full, args.m01, args.m10))
    task_ids = validate(full, m01, m10)
    maps = {"full": run_map(full), "M01": run_map(m01), "M10": run_map(m10)}
    summaries = {"full": full, "M01": m01, "M10": m10}
    comparisons = []
    for offset, arm in enumerate(("M01", "M10")):
        complete = [
            task for task in task_ids
            if maps["full"][task]["status"] != "infrastructure_error"
            and maps[arm][task]["status"] not in {"infrastructure_error", "batch_exception"}
        ]
        n10 = sum(
            maps["full"][task]["success"] and not maps[arm][task]["success"]
            for task in complete
        )
        n01 = sum(
            not maps["full"][task]["success"] and maps[arm][task]["success"]
            for task in complete
        )
        low, high = bootstrap_risk_difference(
            maps["full"], maps[arm], complete,
            samples=args.bootstrap, seed=args.seed + offset,
        )
        comparisons.append({
            "comparison": f"full_vs_{arm}",
            "component_removed": 1 if arm == "M01" else 2,
            "full_success": full["success_count"],
            "ablation_success": summaries[arm]["success_count"],
            "observed_all_task_risk_difference": (
                full["success_count"] - summaries[arm]["success_count"]
            ) / 100,
            "infrastructure_extreme_risk_difference": [
                (
                    full["success_count"]
                    - summaries[arm]["success_count"]
                    - int(summaries[arm].get("status_counts", {}).get("infrastructure_error", 0))
                ) / 100,
                (
                    full["success_count"]
                    + int(full.get("status_counts", {}).get("infrastructure_error", 0))
                    - summaries[arm]["success_count"]
                ) / 100,
            ],
            "risk_difference": paired_risk_difference(
                maps["full"], maps[arm], complete
            ),
            "risk_difference_ci95": [low, high],
            "complete_case_count": len(complete),
            "full_only_success": n10,
            "ablation_only_success": n01,
            "p_exact": exact_mcnemar(n10, n01),
        })
    bh_adjust(comparisons)

    overview = []
    for arm in ("full", "M01", "M10"):
        summary = summaries[arm]
        infrastructure = int(summary.get("status_counts", {}).get("infrastructure_error", 0))
        overview.append({
            "arm": arm,
            "success_count": summary["success_count"],
            "success_rate_lower": summary["success_count"] / 100,
            "success_rate_upper": (summary["success_count"] + infrastructure) / 100,
            "status_counts": summary["status_counts"],
            "total_candidates_used": summary["total_candidates_used"],
            "usage_total": summary.get("usage_total", {}),
            "verified_success_at_k": summary["verified_success_at_k"],
        })

    task_rows = []
    for task in task_ids:
        task_rows.append({
            "task_id": task,
            "category": task.split("_", 1)[0],
            **{
                f"{arm}_status": maps[arm][task]["status"]
                for arm in ("full", "M01", "M10")
            },
            **{
                f"{arm}_success": int(bool(maps[arm][task]["success"]))
                for arm in ("full", "M01", "M10")
            },
            **{
                f"{arm}_candidates": maps[arm][task].get("candidates_used")
                for arm in ("full", "M01", "M10")
            },
        })

    category = {}
    for code in sorted({row["category"] for row in task_rows}):
        selected = [row for row in task_rows if row["category"] == code]
        category[code] = {
            arm: sum(row[f"{arm}_success"] for row in selected)
            for arm in ("full", "M01", "M10")
        }

    document = {
        "schema_version": "1.0",
        "research_question": "RQ2 two-component deletion ablation",
        "task_count": 100,
        "model": "deepseek-v4-flash",
        "bootstrap_samples": args.bootstrap,
        "bootstrap_seed": args.seed,
        "inputs": {
            "full": {"file": args.full.name, "sha256": sha256(args.full)},
            "M01": {"file": args.m01.name, "sha256": sha256(args.m01)},
            "M10": {"file": args.m10.name, "sha256": sha256(args.m10)},
        },
        "overview": overview,
        "primary_comparisons": comparisons,
        "category_success_counts": category,
        "limitations": [
            "one frozen stochastic run per arm",
            "full control ran on NAS; ablations ran concurrently on huashuo",
            "no M00 joint ablation; component interaction is not estimated",
        ],
    }
    args.output.mkdir(parents=True, exist_ok=True)
    write_json(args.output / "rq2_results.json", document)
    for name, rows in (("paired_results.csv", comparisons), ("task_outcomes.csv", task_rows)):
        with (args.output / name).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=list(rows[0]), lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(rows)
    with (args.output / "verified_success_at_k.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["k", "full", "M01", "M10"])
        for k in range(1, 11):
            writer.writerow([
                k,
                full["verified_success_at_k"][str(k)],
                m01["verified_success_at_k"][str(k)],
                m10["verified_success_at_k"][str(k)],
            ])
    print(json.dumps(document, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

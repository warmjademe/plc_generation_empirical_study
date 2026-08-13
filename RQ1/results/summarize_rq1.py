#!/usr/bin/env python3
"""Build compact RQ1 tables from the frozen 100-task summary logs.

The script intentionally ignores raw candidate workspaces and every run whose
directory name does not identify the frozen 100-task experiment.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DERIVED = ROOT / "derived"

RUNS = (
    # Proposed method, one frozen run per model.
    ("final/proposed_method/nas/egbs_deepseek_v4_flash_agentic_context_v5_2_datasets100_20260812_v1.json", "本文方法", "DeepSeek-V4-Flash", "nas", "proposed"),
    ("final/proposed_method/nas/egbs_gpt_5_6_luna_agentic_context_v5_2_datasets100_20260812_v1.json", "本文方法", "GPT-5.6 Luna", "nas", "proposed"),
    ("final/proposed_method/nas/egbs_gemini_3_5_flash_lite_agentic_context_v5_2_datasets100_20260812_v1.json", "本文方法", "Gemini-3.5-Flash-Lite", "nas", "proposed"),
    ("final/proposed_method/nas/egbs_claude_sonnet_5_agentic_context_v5_2_datasets100_20260812_v1.json", "本文方法", "Claude Sonnet 5", "nas", "proposed"),
    # PLC-agent comparisons.
    ("final/baselines/huashuo/baseline1_llm4plc_deepseek_v4_flash_datasets100_20260812_v1.json", "LLM4PLC-adapted", "DeepSeek-V4-Flash", "huashuo", "plc_agent"),
    ("final/baselines/huashuo/baseline1_llm4plc_gpt_5_6_luna_datasets100_20260812_v1.json", "LLM4PLC-adapted", "GPT-5.6 Luna", "huashuo", "plc_agent"),
    ("final/baselines/huashuo/baseline1_llm4plc_gemini_3_5_flash_lite_datasets100_20260812_v1.json", "LLM4PLC-adapted", "Gemini-3.5-Flash-Lite", "huashuo", "plc_agent"),
    ("final/baselines/huashuo/baseline1_llm4plc_claude_sonnet_5_datasets100_20260812_v1.json", "LLM4PLC-adapted", "Claude Sonnet 5", "huashuo", "plc_agent"),
    ("final/baselines/huashuo/baseline2_agents4plc_deepseek_v4_flash_datasets100_20260812_v1.json", "Agents4PLC-reimplemented", "DeepSeek-V4-Flash", "huashuo", "plc_agent"),
    ("final/baselines/huashuo/baseline2_agents4plc_gpt_5_6_luna_datasets100_20260812_v1.json", "Agents4PLC-reimplemented", "GPT-5.6 Luna", "huashuo", "plc_agent"),
    ("final/baselines/huashuo/baseline2_agents4plc_gemini_3_5_flash_lite_datasets100_20260812_v1.json", "Agents4PLC-reimplemented", "Gemini-3.5-Flash-Lite", "huashuo", "plc_agent"),
    ("final/baselines/huashuo/baseline2_agents4plc_claude_sonnet_5_datasets100_20260812_v1.json", "Agents4PLC-reimplemented", "Claude Sonnet 5", "huashuo", "plc_agent"),
    ("final/baselines/huashuo/baseline3_chatdev_deepseek_v4_flash_datasets100_20260812_v1.json", "ChatDev-adapted", "DeepSeek-V4-Flash", "huashuo", "plc_agent"),
    ("final/baselines/huashuo/baseline3_chatdev_gpt_5_6_luna_datasets100_20260812_v1.json", "ChatDev-adapted", "GPT-5.6 Luna", "huashuo", "plc_agent"),
    ("final/baselines/huashuo/baseline3_chatdev_gemini_3_5_flash_lite_datasets100_20260812_v1.json", "ChatDev-adapted", "Gemini-3.5-Flash-Lite", "huashuo", "plc_agent"),
    ("final/baselines/huashuo/baseline3_chatdev_claude_sonnet_5_datasets100_20260812_v1.json", "ChatDev-adapted", "Claude Sonnet 5", "huashuo", "plc_agent"),
    # General coding-agent controls, each fixed to its native model.
    ("final/baselines/nas/baseline4_claude_code_sonnet5_datasets100_20260812_v4_independent_pass_at_10.json", "Claude Code", "Claude Sonnet 5", "nas", "coding_agent"),
    ("final/baselines/nas/baseline5_codex_gpt_5_6_luna_datasets100_20260812_v4_independent_pass_at_10.json", "Codex", "GPT-5.6 Luna", "nas", "coding_agent"),
)

MODEL_ORDER = {
    "DeepSeek-V4-Flash": 0,
    "GPT-5.6 Luna": 1,
    "Gemini-3.5-Flash-Lite": 2,
    "Claude Sonnet 5": 3,
}
METHOD_ORDER = {
    "本文方法": 0,
    "LLM4PLC-adapted": 1,
    "Agents4PLC-reimplemented": 2,
    "ChatDev-adapted": 3,
    "Claude Code": 4,
    "Codex": 5,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def protocol_ok(document: dict[str, Any], family: str) -> bool:
    if family == "proposed":
        return all(
            document.get(key) is True
            for key in (
                "all_ledgers_valid",
                "all_model_identities_valid",
                "sealed_judge_count_valid",
                "inconclusive_restart_count_valid",
            )
        )
    return document.get("protocol_ok") is True


def load_runs() -> list[dict[str, Any]]:
    loaded = []
    canonical_ids: set[str] | None = None
    for relative, method, model, host, family in RUNS:
        path = ROOT / relative
        document = json.loads(path.read_text(encoding="utf-8"))
        records = document.get("runs")
        if document.get("task_count") != 100 or not isinstance(records, list) or len(records) != 100:
            raise ValueError(f"not a complete 100-task summary: {relative}")
        by_task = {record["task_id"]: record for record in records}
        if len(by_task) != 100:
            raise ValueError(f"duplicate task identifiers: {relative}")
        if canonical_ids is None:
            canonical_ids = set(by_task)
        elif set(by_task) != canonical_ids:
            raise ValueError(f"task set differs from the other runs: {relative}")
        loaded.append(
            {
                "path": path,
                "relative": relative,
                "method": method,
                "model": model,
                "host": host,
                "family": family,
                "document": document,
                "records": records,
                "by_task": by_task,
                "protocol_ok": protocol_ok(document, family),
            }
        )
    return loaded


def percentile(values: list[float], probability: float) -> float:
    values = sorted(values)
    position = (len(values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return values[lower]
    weight = position - lower
    return values[lower] * (1.0 - weight) + values[upper] * weight


def paired_bootstrap_ci(differences: list[int], seed_material: str) -> tuple[float, float]:
    seed = int(hashlib.sha256(seed_material.encode("utf-8")).hexdigest()[:16], 16)
    rng = random.Random(seed)
    size = len(differences)
    samples = [
        sum(differences[rng.randrange(size)] for _ in range(size)) / size
        for _ in range(20_000)
    ]
    return percentile(samples, 0.025), percentile(samples, 0.975)


def exact_mcnemar_p(left_only: int, right_only: int) -> float:
    discordant = left_only + right_only
    if discordant == 0:
        return 1.0
    tail = sum(math.comb(discordant, i) for i in range(min(left_only, right_only) + 1))
    return min(1.0, 2.0 * tail / (2**discordant))


def regularized_gamma_q(shape: float, value: float) -> float:
    """Upper regularized gamma Q(shape, value), for the chi-square tail."""
    if value < 0.0 or shape <= 0.0:
        raise ValueError("invalid gamma arguments")
    if value == 0.0:
        return 1.0
    epsilon = 3.0e-14
    tiny = 1.0e-300
    if value < shape + 1.0:
        term = 1.0 / shape
        total = term
        cursor = shape
        for _ in range(10_000):
            cursor += 1.0
            term *= value / cursor
            total += term
            if abs(term) < abs(total) * epsilon:
                break
        lower = total * math.exp(-value + shape * math.log(value) - math.lgamma(shape))
        return max(0.0, min(1.0, 1.0 - lower))
    b = value + 1.0 - shape
    c = 1.0 / tiny
    d = 1.0 / b
    fraction = d
    for index in range(1, 10_001):
        coefficient = -index * (index - shape)
        b += 2.0
        d = coefficient * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + coefficient / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        fraction *= delta
        if abs(delta - 1.0) < epsilon:
            break
    return max(
        0.0,
        min(1.0, math.exp(-value + shape * math.log(value) - math.lgamma(shape)) * fraction),
    )


def cochran_q(rows: list[list[int]]) -> tuple[float, float]:
    treatments = len(rows[0])
    columns = [sum(row[column] for row in rows) for column in range(treatments)]
    grand_total = sum(columns)
    row_squares = sum(sum(row) ** 2 for row in rows)
    denominator = treatments * grand_total - row_squares
    if denominator == 0:
        return 0.0, 1.0
    statistic = (
        treatments
        * (treatments - 1)
        * (sum(value * value for value in columns) - grand_total * grand_total / treatments)
        / denominator
    )
    p_value = regularized_gamma_q((treatments - 1) / 2.0, statistic / 2.0)
    return statistic, p_value


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    DERIVED.mkdir(exist_ok=True)
    runs = load_runs()

    overview = []
    success_at_k = []
    for run in runs:
        document = run["document"]
        records = run["records"]
        verified = sum(record.get("success") is True for record in records)
        candidates = document.get("total_candidates_used")
        if candidates is None:
            candidates = sum(record.get("candidates_used", 0) for record in records)
        # The proposed-method batch summary records accepted candidates and
        # token usage but not failed provider calls as a separate counter.  Do
        # not infer a call total from candidate count when the log omits it.
        calls = document.get("total_model_calls_used")
        successful_attempts = [
            record["winning_attempt"]
            for record in records
            if record.get("success") and isinstance(record.get("winning_attempt"), int)
        ]
        overview.append(
            {
                "model": run["model"],
                "method": run["method"],
                "family": run["family"],
                "host": run["host"],
                "tasks": 100,
                "verified_success": verified,
                "success_rate_pct": f"{verified:.1f}",
                "total_candidates": candidates,
                "total_model_calls": calls,
                "mean_candidates_per_task": f"{candidates / 100.0:.2f}",
                "candidates_per_verified_success": (
                    f"{candidates / verified:.2f}" if verified else ""
                ),
                "model_calls_per_verified_success": (
                    f"{calls / verified:.2f}" if verified and isinstance(calls, int) else ""
                ),
                "median_winning_attempt": (
                    f"{percentile([float(value) for value in successful_attempts], 0.5):.1f}"
                    if successful_attempts
                    else ""
                ),
                "protocol_ok": str(run["protocol_ok"]).lower(),
                "source": run["relative"],
                "sha256": sha256(run["path"]),
            }
        )
        for budget in range(1, 11):
            successes = sum(
                1
                for record in records
                if record.get("success")
                and isinstance(record.get("winning_attempt"), int)
                and record["winning_attempt"] <= budget
            )
            success_at_k.append(
                {
                    "model": run["model"],
                    "method": run["method"],
                    "k": budget,
                    "verified_success": successes,
                    "rate_pct": f"{successes:.1f}",
                }
            )

    overview.sort(key=lambda row: (MODEL_ORDER[row["model"]], METHOD_ORDER[row["method"]]))
    success_at_k.sort(
        key=lambda row: (MODEL_ORDER[row["model"]], METHOD_ORDER[row["method"]], row["k"])
    )
    write_csv(
        DERIVED / "run_overview.csv",
        overview,
        list(overview[0]),
    )
    write_csv(
        DERIVED / "verified_success_at_k.csv",
        success_at_k,
        list(success_at_k[0]),
    )

    index = {(run["model"], run["method"]): run for run in runs}
    primary = []
    omnibus = []
    plc_agents = ("LLM4PLC-adapted", "Agents4PLC-reimplemented", "ChatDev-adapted")
    for model in MODEL_ORDER:
        selected = [index[(model, method)] for method in ("本文方法",) + plc_agents]
        common_ids = sorted(selected[0]["by_task"])
        matrix = [
            [int(run["by_task"][task_id].get("success") is True) for run in selected]
            for task_id in common_ids
        ]
        q_statistic, q_p = cochran_q(matrix)
        omnibus.append(
            {
                "model": model,
                "paired_tasks": len(common_ids),
                "cochran_q": f"{q_statistic:.6f}",
                "df": 3,
                "p_value": f"{q_p:.12g}",
                "all_protocols_ok": str(all(run["protocol_ok"] for run in selected)).lower(),
            }
        )
        proposed = index[(model, "本文方法")]
        for baseline_name in plc_agents:
            baseline = index[(model, baseline_name)]
            pair_ids = common_ids
            differences = []
            proposed_only = 0
            baseline_only = 0
            both_success = 0
            both_failure = 0
            for task_id in pair_ids:
                left = int(proposed["by_task"][task_id].get("success") is True)
                right = int(baseline["by_task"][task_id].get("success") is True)
                differences.append(left - right)
                if left and right:
                    both_success += 1
                elif left:
                    proposed_only += 1
                elif right:
                    baseline_only += 1
                else:
                    both_failure += 1
            lower, upper = paired_bootstrap_ci(differences, f"{model}:{baseline_name}")
            primary.append(
                {
                    "model": model,
                    "baseline": baseline_name,
                    "paired_tasks": len(pair_ids),
                    "both_success": both_success,
                    "proposed_only": proposed_only,
                    "baseline_only": baseline_only,
                    "both_failure": both_failure,
                    "risk_difference_pp": f"{100.0 * sum(differences) / len(differences):.1f}",
                    "bootstrap_95ci_low_pp": f"{100.0 * lower:.1f}",
                    "bootstrap_95ci_high_pp": f"{100.0 * upper:.1f}",
                    "mcnemar_exact_p": exact_mcnemar_p(proposed_only, baseline_only),
                    "both_protocols_ok": proposed["protocol_ok"] and baseline["protocol_ok"],
                }
            )

    ordered = sorted(range(len(primary)), key=lambda index_: primary[index_]["mcnemar_exact_p"])
    adjusted = [1.0] * len(primary)
    running = 1.0
    for rank_from_end, index_ in reversed(list(enumerate(ordered, start=1))):
        candidate = primary[index_]["mcnemar_exact_p"] * len(primary) / rank_from_end
        running = min(running, candidate)
        adjusted[index_] = min(1.0, running)
    for row, adjusted_p in zip(primary, adjusted):
        row["bh_fdr_p"] = f"{adjusted_p:.12g}"
        row["mcnemar_exact_p"] = f"{row['mcnemar_exact_p']:.12g}"
        row["both_protocols_ok"] = str(row["both_protocols_ok"]).lower()

    write_csv(DERIVED / "cochran_q.csv", omnibus, list(omnibus[0]))
    write_csv(DERIVED / "pairwise_primary.csv", primary, list(primary[0]))

    controller_logs = sorted((ROOT / "system_logs").rglob("*.txt"))
    manifest = {
        "scope": "frozen Balanced-100 runs only",
        "task_count": 100,
        "task_id_set_sha256": hashlib.sha256(
            "\n".join(sorted(runs[0]["by_task"])).encode("utf-8")
        ).hexdigest(),
        "summary_count": len(runs),
        "controller_log_count": len(controller_logs),
        "artifacts": [
            {
                "path": run["relative"],
                "bytes": run["path"].stat().st_size,
                "sha256": sha256(run["path"]),
                "host": run["host"],
                "method": run["method"],
                "model": run["model"],
                "protocol_ok": run["protocol_ok"],
            }
            for run in runs
        ],
        "controller_logs": [
            {
                "path": str(path.relative_to(ROOT)),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "host": path.relative_to(ROOT / "system_logs").parts[0],
            }
            for path in controller_logs
        ],
    }
    (ROOT / "artifact_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"validated {len(runs)} complete summaries over one shared 100-task set")


if __name__ == "__main__":
    main()

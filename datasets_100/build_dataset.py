#!/usr/bin/env python3
"""Build a balanced 100-task dataset from previously qualified task banks."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import shutil
import statistics
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
SOURCE_CODES = ROOT.parent
DATASETS = SOURCE_CODES / "datasets"
TASKS_PER_CATEGORY = 10
REFERENCE_RUNTIME_LIMIT_MS = 600_000
COMPLEXITY_METRICS = (
    "requirements",
    "interactions",
    "transitions",
    "retained_state",
    "stateful_blocks",
    "fault_modes",
    "horizon_scans",
    "inputs",
    "outputs",
)
SOURCE_BANK = {
    "C04": "task_bank_c04_reverse_runtime_v0_3",
    "C06": "task_bank_c06_formal_core_runtime_v0_4",
}
DEFAULT_SOURCE_BANK = "task_bank_v0_3_1"
EXCLUSIONS = {
    "C02_B08_composite": "scan-start versus post-update rejection-pulse semantics are ambiguous",
    "C02_B12_composite": "scan-start versus post-update rejection-pulse semantics are ambiguous",
    "C06_M02_bounded_up_down_counter": "authored runtime vectors violate the public positive-capacity assumption",
    "C06_W03_lean_composite": "the public contract does not define when B_Accepted becomes TRUE or its pulse lifetime",
    "C06_W05_lean_composite": "authored runtime vectors violate the public B_Target interval assumption",
    "C06_W10_lean_composite": "authored runtime vectors violate the public B_Target interval assumption",
    "C06_W20_lean_composite": "authored runtime vectors violate the public B_Target interval assumption",
    "C09_B02_composite": "exact PLCverif reference calibration exceeds the 120-second CBMC backend timeout",
}


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def percentile_ranks(records: list[dict[str, Any]], metric: str) -> dict[str, float]:
    values = [int(record.get("complexity", {}).get(metric, 0)) for record in records]
    ranks: dict[str, float] = {}
    for record, value in zip(records, values):
        below = sum(other < value for other in values)
        equal = sum(other == value for other in values)
        ranks[record["task_id"]] = (below + 0.5 * equal) / len(values)
    return ranks


def enrich(records: list[dict[str, Any]], bank: str) -> list[dict[str, Any]]:
    rank_maps = {metric: percentile_ranks(records, metric) for metric in COMPLEXITY_METRICS}
    enriched = []
    for source in records:
        record = dict(source)
        record["complexity_percentiles"] = {
            metric: rank_maps[metric][record["task_id"]]
            for metric in COMPLEXITY_METRICS
        }
        record["structural_complexity_score"] = statistics.fmean(
            record["complexity_percentiles"].values()
        )
        metadata = json.loads(
            (DATASETS / bank / "tasks" / record["task_id"] / "metadata.json").read_text(
                encoding="utf-8"
            )
        )
        composition = metadata["composition"]
        components = (str(composition["base_a"]), str(composition["base_b"]))
        record["composition_pair"] = list(components)
        record["unordered_composition_pair"] = sorted(components)
        enriched.append(record)
    return enriched


def choose_category(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if len(records) < TASKS_PER_CATEGORY:
        raise ValueError(f"only {len(records)} eligible records; need {TASKS_PER_CATEGORY}")
    ordered = sorted(records, key=lambda item: item["task_id"])
    best_objective: tuple[int, int, float, int] | None = None
    best: tuple[dict[str, Any], ...] | None = None
    for combination in itertools.combinations(ordered, TASKS_PER_CATEGORY):
        pairs = {tuple(item["unordered_composition_pair"]) for item in combination}
        components = {
            component
            for item in combination
            for component in item["composition_pair"]
        }
        objective = (
            len(pairs),
            len(components),
            round(sum(item["structural_complexity_score"] for item in combination), 12),
            -sum(item["reference_total_duration_ms"] for item in combination),
        )
        if best_objective is None or objective > best_objective:
            best_objective = objective
            best = combination
    assert best is not None and best_objective is not None
    selected = sorted(best, key=lambda item: item["task_id"])
    return selected, {
        "distinct_unordered_composition_pairs": best_objective[0],
        "distinct_base_behaviors": best_objective[1],
        "structural_complexity_score_sum": best_objective[2],
        "historical_reference_duration_ms_sum": -best_objective[3],
    }


def file_hashes(task_dir: Path) -> dict[str, str]:
    return {
        str(path.relative_to(task_dir)): sha256(path)
        for path in sorted(task_dir.rglob("*"))
        if path.is_file()
    }


def build(catalog_path: Path) -> None:
    if (ROOT / "tasks").exists() or (ROOT / "manifest.jsonl").exists():
        raise FileExistsError("refusing to overwrite an existing datasets_100 build")
    catalog_path = catalog_path.resolve()
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    records = catalog.get("records")
    if not isinstance(records, list):
        raise ValueError("qualification catalog has no records list")

    selected: list[dict[str, Any]] = []
    category_audit: dict[str, Any] = {}
    for number in range(1, 11):
        category = f"C{number:02d}"
        bank = SOURCE_BANK.get(category, DEFAULT_SOURCE_BANK)
        pool = [
            record
            for record in records
            if record.get("category_id") == category
            and record.get("source_bank") == bank
            and record.get("task_id") not in EXCLUSIONS
            and record.get("qualified") is True
            and record.get("reference_ok") is True
            and record.get("authored_negative_killed") is True
            and int(record.get("reference_total_duration_ms", REFERENCE_RUNTIME_LIMIT_MS + 1))
            <= REFERENCE_RUNTIME_LIMIT_MS
        ]
        pool = enrich(pool, bank)
        category_selected, objective = choose_category(pool)
        for record in category_selected:
            record["selection_source_bank"] = bank
        selected.extend(category_selected)
        category_audit[category] = {
            "source_bank": bank,
            "eligible_count": len(pool),
            "selected_count": len(category_selected),
            "objective": objective,
            "selected_task_ids": [record["task_id"] for record in category_selected],
        }

    if len(selected) != 100 or len({record["task_id"] for record in selected}) != 100:
        raise AssertionError("selection must contain 100 unique tasks")
    if set(EXCLUSIONS) & {record["task_id"] for record in selected}:
        raise AssertionError("a known data-quality exclusion was selected")

    tasks_root = ROOT / "tasks"
    evidence_root = ROOT / "evidence"
    tasks_root.mkdir()
    evidence_root.mkdir()
    shutil.copy2(catalog_path, evidence_root / "source_qualification_catalog.json")

    manifest = []
    for record in sorted(selected, key=lambda item: item["task_id"]):
        task_id = record["task_id"]
        bank = record["selection_source_bank"]
        source = DATASETS / bank / "tasks" / task_id
        destination = tasks_root / task_id
        shutil.copytree(source, destination)
        metadata = json.loads((destination / "metadata.json").read_text(encoding="utf-8"))
        manifest.append({
            "id": task_id,
            "category_id": record["category_id"],
            "path": f"tasks/{task_id}",
            "source_bank": bank,
            "base_a": metadata["composition"]["base_a"],
            "base_b": metadata["composition"]["base_b"],
            "hashes": file_hashes(destination),
        })

    manifest_text = "".join(
        json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
        for record in manifest
    )
    (ROOT / "manifest.jsonl").write_text(manifest_text, encoding="utf-8")
    manifest_sha = sha256(ROOT / "manifest.jsonl")

    selection_records = []
    for record in sorted(selected, key=lambda item: item["task_id"]):
        selection_records.append({
            key: record.get(key)
            for key in (
                "task_id",
                "category_id",
                "selection_source_bank",
                "reference_sha256",
                "gate_durations_ms",
                "reference_total_duration_ms",
                "structural_complexity_score",
                "complexity_percentiles",
                "complexity",
                "composition_pair",
                "screening_status",
                "screening_success",
                "screening_candidates_used",
                "qualification_artifact",
            )
        })
    selection_document = {
        "schema_version": "1.0",
        "dataset_name": "PLC Generation Balanced-100",
        "selection_policy": {
            "qualification": "reference passes MatIEC, PLCverif, and OpenPLC; predeclared negative is killed",
            "historical_reference_runtime_limit_ms": REFERENCE_RUNTIME_LIMIT_MS,
            "difficulty": "equal-weight mean of within-category percentile ranks over nine pre-existing structural metrics",
            "optimization_order": [
                "maximize distinct unordered composition pairs",
                "maximize distinct base behaviors",
                "maximize summed structural complexity",
                "minimize historical reference-validation time",
            ],
            "model_screening_outcome_used_for_selection": False,
        },
        "known_exclusions": [
            {"task_id": task_id, "reason": reason}
            for task_id, reason in sorted(EXCLUSIONS.items())
        ],
        "category_audit": category_audit,
        "records": selection_records,
        "source_catalog_sha256": sha256(catalog_path),
        "manifest_sha256": manifest_sha,
    }
    write_json(ROOT / "selection_audit.json", selection_document)

    durations = [record["reference_total_duration_ms"] for record in selected]
    screen_counts = Counter(record["screening_status"] for record in selected)
    source_counts = Counter(record["selection_source_bank"] for record in selected)
    retained_ids = {
        path.name for path in (SOURCE_CODES / "datasets_50" / "tasks").iterdir()
        if path.is_dir()
    }
    summary = {
        "schema_version": "1.0",
        "dataset_name": "PLC Generation Balanced-100",
        "task_count": 100,
        "category_counts": {f"C{number:02d}": 10 for number in range(1, 11)},
        "source_bank_counts": dict(sorted(source_counts.items())),
        "historical_screening_status_counts": dict(sorted(screen_counts.items())),
        "historical_screening_outcome_used_for_selection": False,
        "historical_reference_duration_ms": {
            "minimum": min(durations),
            "median": statistics.median(durations),
            "p90": sorted(durations)[89],
            "maximum": max(durations),
            "hard_limit": REFERENCE_RUNTIME_LIMIT_MS,
        },
        "known_data_quality_exclusions": sorted(EXCLUSIONS),
        "retained_from_balanced_50_count": len(
            retained_ids & {record["task_id"] for record in selected}
        ),
        "selection_audit_sha256": sha256(ROOT / "selection_audit.json"),
        "manifest_sha256": manifest_sha,
        "qualification_status": "historically qualified; exact 100-task revalidation pending",
    }
    write_json(ROOT / "dataset_summary.json", summary)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qualification-catalog", required=True, type=Path)
    args = parser.parse_args()
    build(args.qualification_catalog)
    print("built 100 tasks in", ROOT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

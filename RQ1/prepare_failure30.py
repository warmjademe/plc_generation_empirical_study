#!/usr/bin/env python3
"""Freeze the first prespecified set of 30 valid Kimi Direct@1 failures for RQ1."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bank-root", required=True, type=Path)
    parser.add_argument("--screening-root", required=True, type=Path)
    parser.add_argument("--screening-summary", required=True, type=Path)
    parser.add_argument("--qualification-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--expected-failures", type=int, default=30)
    args = parser.parse_args()

    bank = args.bank_root.resolve()
    screening_root = args.screening_root.resolve()
    screening_summary_path = args.screening_summary.resolve()
    qualification_dir = args.qualification_dir.resolve()
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"refusing to overwrite frozen RQ1 subset: {output}")
    output.mkdir(parents=True, exist_ok=True)
    (output / "tasks").mkdir()
    (output / "selection_evidence").mkdir()

    summary = json.loads(screening_summary_path.read_text(encoding="utf-8"))
    if not (
        summary.get("all_ledgers_valid")
        and summary.get("all_requests_isolated")
        and summary.get("all_candidates_exactly_once")
        and summary.get("all_resolved_to_k3")
    ):
        raise ValueError("screening summary failed the Direct@1 protocol audit")
    selected = sorted(
        (item for item in summary.get("runs", []) if item.get("selection_eligible") is True),
        key=lambda item: item["task_id"],
    )
    if len(selected) != args.expected_failures:
        raise ValueError(
            f"expected exactly {args.expected_failures} semantic failures in the frozen summary, found {len(selected)}"
        )

    records = []
    qualification_records = []
    for item in selected:
        task_id = item["task_id"]
        source_task = bank / "tasks" / task_id
        model_result_path = screening_root / task_id / "result.json"
        qualification_path = qualification_dir / task_id / "qualification.json"
        if not source_task.is_dir() or not model_result_path.is_file() or not qualification_path.is_file():
            raise FileNotFoundError(f"missing frozen evidence for {task_id}")
        model_result = json.loads(model_result_path.read_text(encoding="utf-8"))
        qualification = json.loads(qualification_path.read_text(encoding="utf-8"))
        if qualification.get("qualified") is not True:
            raise ValueError(f"{task_id} is not reference-qualified")
        if not (
            model_result.get("candidates_used") == 1
            and model_result.get("candidate_budget") == 1
            and model_result.get("resolved_models") == ["k3"]
            and model_result.get("status") in {"candidate_budget_exhausted", "sealed_failure"}
        ):
            raise ValueError(f"{task_id} is not an eligible Kimi K3 Direct@1 semantic failure")

        shutil.copytree(source_task, output / "tasks" / task_id)
        evidence_dir = output / "selection_evidence" / task_id
        evidence_dir.mkdir()
        shutil.copy2(model_result_path, evidence_dir / "kimi_direct_result.json")
        shutil.copy2(qualification_path, evidence_dir / "qualification.json")
        qualification_records.append(qualification)
        records.append({
            "task_id": task_id,
            "category": task_id.split("_")[0],
            "kimi_status": model_result["status"],
            "kimi_result_sha256": sha256(model_result_path),
            "qualification_sha256": sha256(qualification_path),
            "source_task_tree_files": sum(path.is_file() for path in source_task.rglob("*")),
        })

    shutil.copy2(screening_summary_path, output / "selection_source_screening_summary.json")
    qualification_subset = {
        "schema_version": "1.0",
        "status": "pass",
        "scope": "RQ1 exploratory subset selected only from qualified Kimi K3 Direct@1 semantic failures",
        "task_count": len(qualification_records),
        "qualified_count": len(qualification_records),
        "source_qualification_run_spec_sha256": sha256(qualification_dir / "run_spec.json"),
        "tasks": qualification_records,
    }
    write_json(output / "qualification.json", qualification_subset)
    selection = {
        "schema_version": "1.0",
        "study_role": "exploratory RQ1 pilot; not the final category-balanced 50-task benchmark",
        "selection_rule": "all semantic failures in the frozen 68-task Kimi K3 Direct@1 screening summary",
        "source_screening_summary_sha256": sha256(screening_summary_path),
        "selected_count": len(records),
        "category_counts": dict(sorted(Counter(item["category"] for item in records).items())),
        "status_counts": dict(sorted(Counter(item["kimi_status"] for item in records).items())),
        "tasks": records,
    }
    write_json(output / "selection.json", selection)
    print(json.dumps({
        "status": "pass",
        "selected_count": len(records),
        "category_counts": selection["category_counts"],
        "status_counts": selection["status_counts"],
        "output": str(output),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


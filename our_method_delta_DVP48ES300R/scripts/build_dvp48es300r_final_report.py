#!/usr/bin/env python3
"""Build the final DVP48ES300R experiment report from independent evidence.

The prespecified score and the post-hoc differential diagnostic are deliberately
kept separate.  A reference mismatch is never converted into a defect without
an explicit requirement-level review record.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


REVIEW_CLASSES = {
    "confirmed_requirement_violation",
    "acceptable_alternative",
    "underspecified",
    "unresolved",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def review_index(document: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if document is None:
        return {}
    result: dict[str, dict[str, Any]] = {}
    for item in document.get("records", []):
        task_id = str(item["task_id"])
        classification = str(item["classification"])
        if classification not in REVIEW_CLASSES:
            raise ValueError(
                f"{task_id}: unsupported manual-review classification {classification!r}"
            )
        if task_id in result:
            raise ValueError(f"duplicate manual-review record for {task_id}")
        if not str(item.get("rationale", "")).strip():
            raise ValueError(f"{task_id}: manual-review rationale is empty")
        result[task_id] = item
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-summary", required=True, type=Path)
    parser.add_argument("--independent-audit", required=True, type=Path)
    parser.add_argument("--differential-audit", required=True, type=Path)
    parser.add_argument("--manual-review", type=Path)
    parser.add_argument("--target-policy-audit", type=Path)
    parser.add_argument("--corrected-infrastructure-summary", type=Path)
    parser.add_argument("--corrected-infrastructure-audit", type=Path)
    parser.add_argument("--corrected-infrastructure-differential", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--expected-task-count", type=int, default=100)
    args = parser.parse_args()

    batch = load_json(args.batch_summary.resolve())
    audit = load_json(args.independent_audit.resolve())
    differential = load_json(args.differential_audit.resolve())
    manual = load_json(args.manual_review.resolve()) if args.manual_review else None
    target_policy = (
        load_json(args.target_policy_audit.resolve()) if args.target_policy_audit else None
    )
    corrected_infrastructure = (
        load_json(args.corrected_infrastructure_summary.resolve())
        if args.corrected_infrastructure_summary else None
    )
    corrected_audit = (
        load_json(args.corrected_infrastructure_audit.resolve())
        if args.corrected_infrastructure_audit else None
    )
    corrected_differential = (
        load_json(args.corrected_infrastructure_differential.resolve())
        if args.corrected_infrastructure_differential else None
    )
    reviews = review_index(manual)
    errors: list[str] = []

    expected = args.expected_task_count
    if int(batch.get("task_count", -1)) != expected:
        errors.append(f"batch contains {batch.get('task_count')} tasks, expected {expected}")
    if audit.get("audit_pass") is not True:
        errors.append("independent cross-layer audit did not pass")
    for field in (
        "model_identity_valid",
        "successful_candidate_isolation_valid",
        "ledger_valid",
        "sealed_accounting_valid",
        "batch_summary_matches",
    ):
        if audit.get(field) is not True:
            errors.append(f"independent audit field {field} is not true")
    if int(audit.get("audited_task_count", -1)) != expected:
        errors.append("independent audit does not cover every task")
    if int(audit.get("verified_success_count", -1)) != int(batch.get("success_count", -2)):
        errors.append("batch and independent audit success counts differ")
    if int(differential.get("task_count", -1)) != expected:
        errors.append("differential audit does not cover every task")
    if target_policy is not None:
        if target_policy.get("audit_valid") is not True:
            errors.append("prospective target-policy audit is not valid")
        if int(target_policy.get("completed_task_count", -1)) != expected:
            errors.append("prospective target-policy audit does not cover every task")
        if int(target_policy.get("prespecified_success_count", -1)) != int(
            batch.get("success_count", -2)
        ):
            errors.append("target-policy audit and batch success counts differ")

    batch_runs = {str(item["task_id"]): item for item in batch.get("runs", [])}
    diff_runs = {str(item["task_id"]): item for item in differential.get("records", [])}
    if len(batch_runs) != expected:
        errors.append("batch run records are missing or duplicated")
    if len(diff_runs) != expected:
        errors.append("differential records are missing or duplicated")

    infrastructure_task_ids = {
        task_id for task_id, item in batch_runs.items()
        if item.get("status") == "infrastructure_error"
    }
    corrected_runs: dict[str, dict[str, Any]] = {}
    corrected_diff_runs: dict[str, dict[str, Any]] = {}
    if corrected_infrastructure is not None:
        corrected_runs = {
            str(item["task_id"]): item
            for item in corrected_infrastructure.get("runs", [])
        }
        if set(corrected_runs) != infrastructure_task_ids:
            errors.append(
                "corrected run must cover exactly every original infrastructure-error task"
            )
        if corrected_infrastructure.get("requested_model") != batch.get("requested_model"):
            errors.append("corrected run used a different requested model")
        if corrected_infrastructure.get("method") != batch.get("method"):
            errors.append("corrected run used a different synthesis method")
        if any(
            int(item.get("candidate_budget", -1))
            != int(batch_runs.get(task_id, {}).get("candidate_budget", -2))
            for task_id, item in corrected_runs.items()
        ):
            errors.append("corrected run did not preserve the original candidate budget")
        if corrected_audit is None:
            errors.append("corrected run has no independent cross-layer audit")
        else:
            for field in (
                "audit_pass",
                "model_identity_valid",
                "successful_candidate_isolation_valid",
                "ledger_valid",
                "sealed_accounting_valid",
                "batch_summary_matches",
            ):
                if corrected_audit.get(field) is not True:
                    errors.append(f"corrected-run audit field {field} is not true")
            if int(corrected_audit.get("audited_task_count", -1)) != len(
                infrastructure_task_ids
            ):
                errors.append("corrected-run audit does not cover every rerun task")
            if int(corrected_audit.get("verified_success_count", -1)) != int(
                corrected_infrastructure.get("success_count", -2)
            ):
                errors.append("corrected summary and audit success counts differ")
        if corrected_differential is None:
            errors.append("corrected run has no post-hoc differential audit")
        else:
            corrected_diff_runs = {
                str(item["task_id"]): item
                for item in corrected_differential.get("records", [])
            }
            if int(corrected_differential.get("task_count", -1)) != len(
                infrastructure_task_ids
            ):
                errors.append("corrected differential audit has the wrong task count")
            if set(corrected_diff_runs) != infrastructure_task_ids:
                errors.append("corrected differential audit does not cover exactly the rerun tasks")
    elif corrected_audit is not None or corrected_differential is not None:
        errors.append("corrected-run audits were supplied without a corrected summary")

    successes = {task_id for task_id, item in batch_runs.items() if item.get("success") is True}
    recovered_infrastructure_successes = {
        task_id for task_id, item in corrected_runs.items()
        if item.get("success") is True
    }
    corrected_successes = successes | recovered_infrastructure_successes
    differential_counts: Counter[str] = Counter()
    strict_successes: list[str] = []
    review_rows: list[dict[str, Any]] = []
    for task_id in sorted(successes):
        item = diff_runs.get(task_id)
        if item is None:
            errors.append(f"{task_id}: no differential record")
            continue
        status = str(item.get("status"))
        differential_counts[status] += 1
        if status == "pass":
            strict_successes.append(task_id)
            continue
        if status == "fail":
            review = reviews.get(task_id)
            if review is None:
                review_rows.append({
                    "task_id": task_id,
                    "classification": "unresolved",
                    "rationale": "no manual requirement-level review was supplied",
                })
                continue
            review_rows.append(dict(review))
            if review["classification"] == "acceptable_alternative":
                strict_successes.append(task_id)
            continue
        review_rows.append({
            "task_id": task_id,
            "classification": "unresolved",
            "rationale": f"differential audit status is {status}",
        })

    corrected_differential_counts: Counter[str] = Counter()
    strict_corrected_successes = set(strict_successes)
    for task_id in sorted(recovered_infrastructure_successes):
        item = corrected_diff_runs.get(task_id)
        if item is None:
            errors.append(f"{task_id}: no corrected-run differential record")
            continue
        status = str(item.get("status"))
        corrected_differential_counts[status] += 1
        if status == "pass":
            strict_corrected_successes.add(task_id)
            continue
        if status == "fail":
            review = reviews.get(task_id)
            if review is None:
                review_rows.append({
                    "task_id": task_id,
                    "classification": "unresolved",
                    "rationale": "no manual requirement-level review was supplied",
                })
                continue
            review_rows.append(dict(review))
            if review["classification"] == "acceptable_alternative":
                strict_corrected_successes.add(task_id)
            continue
        review_rows.append({
            "task_id": task_id,
            "classification": "unresolved",
            "rationale": f"corrected-run differential audit status is {status}",
        })

    divergent_task_ids = {
        task_id for task_id, item in diff_runs.items() if item.get("status") == "fail"
    } | {
        task_id
        for task_id, item in corrected_diff_runs.items()
        if item.get("status") == "fail"
    }
    extraneous_reviews = sorted(set(reviews) - divergent_task_ids)
    if extraneous_reviews:
        errors.append(f"manual review contains non-divergent tasks: {extraneous_reviews}")

    windows_jobs = [
        job
        for task in audit.get("tasks", [])
        for job in task.get("dvp_jobs", [])
    ]
    role_counts = Counter(str(job.get("role")) for job in windows_jobs)
    review_class_counts = Counter(str(item["classification"]) for item in review_rows)
    candidates = [int(item.get("candidates_used", 0)) for item in batch_runs.values()]
    success_candidates = [
        int(batch_runs[task_id].get("candidates_used", 0)) for task_id in successes
    ]
    report = {
        "schema_version": "1.0",
        "target": "Delta DVP48ES300R via ISPSoft 3.24 and COMMGR 2.11 DVP-ES3 simulator",
        "requested_model": batch.get("requested_model"),
        "method": batch.get("method"),
        "task_count": expected,
        "prespecified_oracle": {
            "verified_success_count": len(successes),
            "success_rate": len(successes) / expected,
            "status_counts": batch.get("status_counts", {}),
            "verified_success_at_k": batch.get("verified_success_at_k", {}),
        },
        "post_hoc_differential_review": {
            "successful_tasks_checked": len(successes),
            "status_counts": dict(sorted(differential_counts.items())),
            "manual_classification_counts": dict(sorted(review_class_counts.items())),
            "conservative_success_count": len(strict_successes),
            "conservative_success_rate": len(strict_successes) / expected,
            "conservative_success_task_ids": strict_successes,
            "reviews": review_rows,
            "interpretation": (
                "This diagnostic compares bounded extra traces with one reference "
                "implementation. Only an explicit requirement-level review may "
                "classify a mismatch as a defect or an acceptable alternative."
            ),
        },
        "prospective_target_policy": None if target_policy is None else {
            "purpose": target_policy.get("purpose"),
            "policy": target_policy.get("policy"),
            "status_counts": target_policy.get("status_counts", {}),
            "hard_noncompliant_task_ids": [
                str(item["task_id"])
                for item in target_policy.get("records", [])
                if item.get("policy_status") == "noncompliant"
            ],
            "advisory_task_ids": [
                str(item["task_id"])
                for item in target_policy.get("records", [])
                if item.get("policy_status") == "advisory"
            ],
            "interpretation": (
                "This later compatibility policy is diagnostic only and does not "
                "retroactively change the frozen prespecified score."
            ),
        },
        "infrastructure_corrected_protocol": (
            None if corrected_infrastructure is None else {
                "original_infrastructure_task_ids": sorted(infrastructure_task_ids),
                "rerun_status_counts": corrected_infrastructure.get("status_counts", {}),
                "recovered_success_count": len(recovered_infrastructure_successes),
                "recovered_success_task_ids": sorted(recovered_infrastructure_successes),
                "corrected_verified_success_count": len(corrected_successes),
                "corrected_success_rate": len(corrected_successes) / expected,
                "cross_layer_audit_pass": (
                    corrected_audit is not None and corrected_audit.get("audit_pass") is True
                ),
                "differential_status_counts": dict(
                    sorted(corrected_differential_counts.items())
                ),
                "conservative_corrected_success_count": len(strict_corrected_successes),
                "conservative_corrected_success_rate": (
                    len(strict_corrected_successes) / expected
                ),
                "interpretation": (
                    "Every original infrastructure-error task was independently "
                    "rerun under the repaired adapter and independently audited; "
                    "the frozen raw score is retained."
                ),
            }
        ),
        "resource_usage": {
            "total_candidates": sum(candidates),
            "candidate_minimum_per_task": min(candidates) if candidates else None,
            "candidate_maximum_per_task": max(candidates) if candidates else None,
            "candidate_mean_per_task": sum(candidates) / len(candidates) if candidates else None,
            "successful_candidate_minimum": min(success_candidates) if success_candidates else None,
            "successful_candidate_maximum": max(success_candidates) if success_candidates else None,
            "successful_candidate_mean": (
                sum(success_candidates) / len(success_candidates) if success_candidates else None
            ),
            "model_usage": batch.get("usage_total", {}),
            "linked_windows_jobs": len(windows_jobs),
            "linked_windows_jobs_by_role": dict(sorted(role_counts.items())),
            "linked_windows_cases": sum(int(job.get("case_count", 0)) for job in windows_jobs),
        },
        "audit": {
            "cross_layer_audit_pass": audit.get("audit_pass") is True,
            "adapter_assets_ledgered": audit.get("adapter_assets_ledgered"),
            "frozen_source_sha256": audit.get("frozen_source_sha256"),
            "transport_status_mismatch_count": sum(
                bool(job.get("transport_status_mismatch")) for job in windows_jobs
            ),
        },
        "errors": errors,
    }
    report["report_valid"] = not errors
    write_json(args.output.resolve(), report)
    print(json.dumps({
        "report_valid": report["report_valid"],
        "verified_success_count": len(successes),
        "prespecified_success_rate": len(successes) / expected,
        "conservative_success_count": len(strict_successes),
        "conservative_success_rate": len(strict_successes) / expected,
        "differential_status_counts": dict(sorted(differential_counts.items())),
        "manual_classification_counts": dict(sorted(review_class_counts.items())),
        "errors": errors,
    }, ensure_ascii=False))
    return 0 if report["report_valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

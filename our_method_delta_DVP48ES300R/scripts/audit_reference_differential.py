#!/usr/bin/env python3
"""Exploratory differential stress audit for completed generated candidates.

This is deliberately outside the prespecified success oracle.  It executes a
generated candidate and the task reference side by side in pinned OpenPLC on
additional deterministic input sequences.  A mismatch flags a possible
bounded-oracle false positive for manual review; agreement is supporting, not
proof of semantic correctness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


SUPPORTED_TYPES = {"BOOL", "INT", "REAL"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def rename_function_block(source: str, old: str, new: str) -> str:
    pattern = re.compile(
        rf"^(\s*FUNCTION_BLOCK\s+){re.escape(old)}\s*$",
        flags=re.IGNORECASE | re.MULTILINE,
    )
    renamed, count = pattern.subn(rf"\g<1>{new}", source, count=1)
    if count != 1:
        raise ValueError(f"expected exactly one FUNCTION_BLOCK {old} header")
    return renamed.strip()


def build_pair_source(
    candidate_source: str,
    reference_source: str,
    metadata: dict[str, Any],
    *,
    real_tolerance: float,
) -> str:
    task_id = str(metadata["id"])
    candidate_name = "EGBS_CANDIDATE"
    reference_name = "EGBS_REFERENCE"
    candidate = rename_function_block(candidate_source, task_id, candidate_name)
    reference = rename_function_block(reference_source, task_id, reference_name)
    inputs = list(metadata["interface"]["inputs"])
    outputs = list(metadata["interface"]["outputs"])
    unsupported = sorted(
        {
            str(item["type"]).upper()
            for item in inputs + outputs
            if str(item["type"]).upper() not in SUPPORTED_TYPES
        }
    )
    if unsupported:
        raise ValueError(f"unsupported interface types: {unsupported}")
    match_names = [f"Match_{item['name']}" for item in outputs]
    declarations = [
        "FUNCTION_BLOCK EGBS_DIFFERENTIAL",
        "VAR_INPUT",
        *[f"    {item['name']} : {str(item['type']).upper()};" for item in inputs],
        "END_VAR",
        "VAR_OUTPUT",
        "    Equivalent : BOOL;",
        *[f"    {name} : BOOL;" for name in match_names],
        "END_VAR",
        "VAR",
        f"    Candidate : {candidate_name};",
        f"    Reference : {reference_name};",
        "END_VAR",
    ]
    arguments = ",\n".join(
        f"    {item['name']} := {item['name']}" for item in inputs
    )
    comparisons: list[tuple[str, str]] = []
    for item in outputs:
        name = str(item["name"])
        match_name = f"Match_{name}"
        type_name = str(item["type"]).upper()
        if type_name == "REAL":
            comparisons.append((match_name,
                f"((Candidate.{name} >= (Reference.{name} - {real_tolerance})) AND "
                f"(Candidate.{name} <= (Reference.{name} + {real_tolerance})))"
            ))
        else:
            comparisons.append((match_name, f"(Candidate.{name} = Reference.{name})"))
    body = [
        "Candidate(", arguments, ");",
        "Reference(", arguments, ");",
        *[f"{match_name} := {expression};" for match_name, expression in comparisons],
        "Equivalent := " + (" AND ".join(name for name, _ in comparisons) if comparisons else "TRUE") + ";",
        "END_FUNCTION_BLOCK",
    ]
    return "\n\n".join((candidate, reference, "\n".join(declarations + body))) + "\n"


def input_domains(metadata: dict[str, Any], authored_suite: dict[str, Any]) -> dict[str, list[Any]]:
    domains: dict[str, list[Any]] = {
        str(item["name"]): [] for item in metadata["interface"]["inputs"]
    }
    for case in authored_suite.get("cases", []):
        for step in case.get("steps", []):
            for name, value in step.get("inputs", {}).items():
                if value not in domains[name]:
                    domains[name].append(value)
    for item in metadata["interface"]["inputs"]:
        name = str(item["name"])
        type_name = str(item["type"]).upper()
        if type_name == "BOOL":
            domains[name] = [False, True]
        if not domains[name]:
            raise ValueError(f"authored suite has no values for input {name}")
    return domains


def build_stress_suite(
    metadata: dict[str, Any],
    authored_suite: dict[str, Any],
    *,
    case_count: int,
    scans_per_case: int,
    seed: int,
) -> dict[str, Any]:
    domains = input_domains(metadata, authored_suite)
    names = list(domains)
    rng = random.Random(seed)
    cases: list[dict[str, Any]] = []
    for case_index in range(case_count):
        current = {name: domains[name][case_index % len(domains[name])] for name in names}
        steps: list[dict[str, Any]] = []
        for scan in range(scans_per_case):
            if scan == 0:
                current = {name: domains[name][0] for name in names}
            elif scan == 1:
                current = {name: domains[name][-1] for name in names}
            elif scan == 2:
                current = {
                    name: domains[name][(case_index + position) % len(domains[name])]
                    for position, name in enumerate(names)
                }
            else:
                for name in names:
                    # Retain most inputs between scans so latches, edges and
                    # priority transitions are exercised as sequences rather
                    # than as unrelated random points.
                    if rng.random() < 0.30:
                        current[name] = rng.choice(domains[name])
            steps.append({
                "inputs": dict(current),
                "expect": {"Equivalent": True},
                "repeat": 1,
                "check": "each",
            })
        cases.append({
            "id": f"DA{case_index + 1:02d}",
            "name": f"differential_audit_{case_index + 1:02d}",
            "requirement_ids": [],
            "fresh_instance": True,
            "steps": steps,
        })
    return {
        "schema_version": "1.0",
        "suite": "openplc",
        "independent_requirement_oracle": True,
        "oracle_source": "post_hoc_reference_differential_audit",
        "scan_period_ms": int(metadata["scan"]["period_ms"]),
        "real_absolute_tolerance": float(authored_suite.get("real_absolute_tolerance", 0.001)),
        "cases": cases,
    }


def normalize_reference_evidence(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Label behavioral disagreement without assuming the reference is unique.

    The OpenPLC runner normally evaluates an authored Oracle and therefore
    labels an expectation mismatch as a confirmed candidate defect.  Here its
    synthetic expectation is only equality with one reference implementation.
    A disagreement can instead expose an underspecified priority or another
    valid implementation, so it must remain a manual-review finding.
    """
    normalized: list[dict[str, Any]] = []
    for item in items:
        record = dict(item)
        if record.get("kind") == "openplc_functional_failure":
            record["underlying_kind"] = record["kind"]
            record["kind"] = "reference_behavior_divergence"
            record["oracle_status"] = "post_hoc_reference_divergence_requires_review"
            record["requirement_ids"] = []
        normalized.append(record)
    return normalized


def audit_task(
    task_dir: Path,
    run_dir: Path,
    validator: Path,
    runner: Path,
    docker: str,
    image: str,
    case_count: int,
    scans_per_case: int,
) -> dict[str, Any]:
    result = load_json(run_dir / "result.json")
    if not result.get("success"):
        return {"task_id": task_dir.name, "status": "not_applicable", "reason": "task did not verify"}
    winning = int(result["winning_attempt"])
    candidate_path = run_dir / "attempts" / f"attempt_{winning:02d}" / "candidate.st"
    metadata = load_json(task_dir / "metadata.json")
    authored_suite = load_json(task_dir / "openplc_tests.json")
    seed = int.from_bytes(hashlib.sha256(task_dir.name.encode()).digest()[:8], "big")
    pair_source = build_pair_source(
        candidate_path.read_text(encoding="utf-8-sig"),
        (task_dir / "reference.st").read_text(encoding="utf-8-sig"),
        metadata,
        real_tolerance=float(authored_suite.get("real_absolute_tolerance", 0.001)),
    )
    stress_suite = build_stress_suite(
        metadata,
        authored_suite,
        case_count=case_count,
        scans_per_case=scans_per_case,
        seed=seed,
    )
    match_outputs = [
        {"name": f"Match_{item['name']}", "type": "BOOL"}
        for item in metadata["interface"]["outputs"]
    ]
    expected_matches = {item["name"]: True for item in match_outputs}
    for case in stress_suite["cases"]:
        for step in case["steps"]:
            step["expect"] = {"Equivalent": True, **expected_matches}
    stress_metadata = {
        "id": "EGBS_DIFFERENTIAL",
        "scan": dict(metadata["scan"]),
        "interface": {
            "inputs": list(metadata["interface"]["inputs"]),
            "outputs": [{"name": "Equivalent", "type": "BOOL"}, *match_outputs],
        },
    }
    # Snap-confined Docker cannot bind-mount the system /tmp tree.  Keep the
    # ephemeral audit package under the experiment run, which is already an
    # allowed bind-mount root on the huashuo host.
    scratch_root = run_dir.parent / ".differential_tmp"
    scratch_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=f"dvp_diff_{task_dir.name}_", dir=scratch_root
    ) as temporary:
        temporary_path = Path(temporary)
        synthetic_task = temporary_path / "task"
        synthetic_task.mkdir()
        candidate = temporary_path / "pair.st"
        candidate.write_text(pair_source, encoding="utf-8")
        (synthetic_task / "metadata.json").write_text(
            json.dumps(stress_metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (synthetic_task / "openplc_tests.json").write_text(
            json.dumps(stress_suite, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        command = [
            sys.executable, str(validator),
            "--candidate", str(candidate), "--task-dir", str(synthetic_task),
            "--docker", docker, "--image", image, "--runner", str(runner), "--case-role", "all",
        ]
        completed = subprocess.run(
            command,
            cwd=temporary_path,
            text=True,
            capture_output=True,
            timeout=max(420, case_count * 120),
            check=False,
        )
        try:
            document = json.loads(completed.stdout)
        except json.JSONDecodeError:
            document = {
                "status": "inconclusive",
                "summary": "differential validator returned invalid JSON",
                "evidence": [{"stdout": completed.stdout[-1000:], "stderr": completed.stderr[-1000:]}],
            }
    return {
        "task_id": task_dir.name,
        "status": document.get("status", "inconclusive"),
        "summary": document.get("summary"),
        "candidate_sha256": hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
        "seed": seed,
        "case_count": case_count,
        "scans_per_case": scans_per_case,
        "total_scans": case_count * scans_per_case,
        "evidence": normalize_reference_evidence(document.get("evidence", [])),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", required=True, type=Path)
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument("--validator", required=True, type=Path)
    parser.add_argument("--runner", required=True, type=Path)
    parser.add_argument("--docker", default="/snap/bin/docker")
    parser.add_argument("--image", default="plc-egbs/openplc-v3:b5d41356")
    parser.add_argument("--case-count", type=int, default=4)
    parser.add_argument("--scans-per-case", type=int, default=32)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    task_dirs = [path for path in sorted((args.dataset_root / "tasks").iterdir()) if path.is_dir()]
    completed = [path for path in task_dirs if (args.run_root / path.name / "result.json").is_file()]
    if args.limit is not None:
        completed = completed[: max(0, args.limit)]
    records: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {
            pool.submit(
                audit_task,
                task_dir,
                args.run_root / task_dir.name,
                args.validator.resolve(),
                args.runner.resolve(),
                args.docker,
                args.image,
                args.case_count,
                args.scans_per_case,
            ): task_dir.name
            for task_dir in completed
        }
        for future in as_completed(futures):
            try:
                records.append(future.result())
            except Exception as exc:
                records.append({
                    "task_id": futures[future],
                    "status": "inconclusive",
                    "summary": f"{type(exc).__name__}: {exc}",
                })
    records.sort(key=lambda item: str(item["task_id"]))
    counts: dict[str, int] = {}
    for item in records:
        counts[str(item["status"])] = counts.get(str(item["status"]), 0) + 1
    report = {
        "schema_version": "1.0",
        "purpose": "post_hoc_false_positive_diagnostic_not_used_for_formal_scoring",
        "task_count": len(records),
        "status_counts": counts,
        "configuration": {
            "case_count": args.case_count,
            "scans_per_case": args.scans_per_case,
            "workers": args.workers,
            "image": args.image,
        },
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"task_count": len(records), "status_counts": counts}, ensure_ascii=False))
    return 0 if counts.get("fail", 0) == 0 and counts.get("inconclusive", 0) == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

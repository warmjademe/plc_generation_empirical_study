#!/usr/bin/env python3
"""Build runtime-bounded replacement candidates for C04 and C06.

Each stateful edge/counter behavior is composed with one stateless C01 Boolean
behavior.  This keeps the semantic interaction of a supervisory composition while
avoiding the product of two retained-state machines that made the original C04/C06
composites impractical for repeated verification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from build_dataset import CATEGORIES, TASKS
from build_task_bank import compose, write_json, write_task


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bound_formal_core(task_dir: Path, record: dict, case_budget: int) -> None:
    """Keep a predeclared bounded formal core; defer other checks to OpenPLC.

    The negative-control target is always retained.  Additional safety properties
    are retained only while their complete native case set fits the case budget.
    The deferred native cases remain in the artifact for auditability, but the
    PLCverif adapter ignores them because their status is not ``required``.
    """
    properties_path = task_dir / "properties.json"
    document = json.loads(properties_path.read_text(encoding="utf-8"))
    control = json.loads((task_dir / "negative_control/index.json").read_text(encoding="utf-8"))["controls"][0]
    target_ids = set(control["target_requirement_ids"])
    native = [item for item in document["properties"] if item.get("plcverif", {}).get("cases")]
    target = [item for item in native if target_ids.intersection(item.get("requirement_ids", []))]
    if len(target) != 1:
        raise RuntimeError(f"{task_dir.name}: expected one native negative-control target")
    selected = [target[0]]
    used_cases = len(target[0]["plcverif"]["cases"])
    if used_cases > case_budget:
        raise RuntimeError(f"{task_dir.name}: target exceeds formal case budget")
    candidates = sorted(
        (item for item in native if item is not target[0]),
        key=lambda item: (item.get("kind") != "safety", item["id"]),
    )
    for item in candidates:
        count = len(item["plcverif"]["cases"])
        if used_cases + count <= case_budget:
            selected.append(item)
            used_cases += count
    selected_ids = {item["id"] for item in selected}
    for item in native:
        if item["id"] in selected_ids:
            continue
        profile = item["plcverif"]
        profile["deferred_cases"] = profile.pop("cases")
        profile["status"] = "deferred_to_openplc_oracle"
        profile["cases"] = []
        profile["coverage"] = "runtime_only"
    formal_profile = document["plcverif_profile"]
    formal_profile["native_property_count"] = len(selected)
    formal_profile["fully_native_property_count"] = len(selected)
    formal_profile["native_case_count"] = used_cases
    formal_profile["selection_policy"] = (
        "predeclared negative-control target plus safety properties within the fixed native-case budget; "
        "all requirements remain mandatory in the independent OpenPLC oracle"
    )
    formal_profile["native_case_budget"] = case_budget
    write_json(properties_path, document)

    metadata_path = task_dir / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["verification_profile"] = {
        "formal_core_native_case_budget": case_budget,
        "formal_core_property_ids": sorted(selected_ids),
        "runtime_oracle_scope": "all mandatory requirements",
    }
    write_json(metadata_path, metadata)
    record["hashes"]["properties.json"] = sha256(properties_path)
    record["hashes"]["metadata.json"] = sha256(metadata_path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--category", action="append", choices=("C04", "C06"))
    parser.add_argument(
        "--direction",
        choices=("stateful-first", "stateful-second"),
        default="stateful-first",
    )
    parser.add_argument("--id-prefix", default="R")
    parser.add_argument(
        "--formal-case-budget",
        type=int,
        help="predeclare a bounded PLCverif core and defer remaining mandatory checks to OpenPLC",
    )
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Z][A-Z0-9]*", args.id_prefix):
        raise ValueError("--id-prefix must be an uppercase alphanumeric identifier")
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite task bank {output}")
    task_root = output / "tasks"
    task_root.mkdir(parents=True)

    selected_categories = tuple(args.category or ("C04", "C06"))
    stateful = {
        category: sorted(
            (item for item in TASKS if item["category_id"] == category),
            key=lambda item: item["id"],
        )
        for category in selected_categories
    }
    stateless = sorted(
        (item for item in TASKS if item["category_id"] == "C01"),
        key=lambda item: item["id"],
    )
    if any(len(items) != 5 for items in stateful.values()) or len(stateless) != 5:
        raise RuntimeError("expected five independently authored bases per source category")

    records = []
    for category in selected_categories:
        index = 0
        pairs = (
            ((primary, secondary) for primary in stateful[category] for secondary in stateless)
            if args.direction == "stateful-first"
            else ((primary, secondary) for primary in stateless for secondary in stateful[category])
        )
        for left, right in pairs:
            index += 1
            task_id = f"{category}_{args.id_prefix}{index:02d}_lean_composite"
            item = compose(left, right, task_id)
            item["category_id"] = category
            item["composition"]["runtime_design"] = (
                "one stateful subsystem plus one stateless Boolean subsystem"
            )
            if category == "C06":
                environment = item["plcverif_environment"]
                bounds = []
                for parameter in environment.get("parameters", []):
                    bounds.extend((f"{parameter} >= -4", f"{parameter} <= 4"))
                    item["assumptions"].append(
                        f"{parameter} remains within the closed interval [-4, 4] during a test."
                    )
                environment["assumption_invariants"] = list(dict.fromkeys(
                    environment.get("assumption_invariants", []) + bounds
                ))
            record = write_task(task_root, item)
            if args.formal_case_budget is not None:
                if args.formal_case_budget < 1:
                    raise ValueError("--formal-case-budget must be positive")
                bound_formal_core(task_root / task_id, record, args.formal_case_budget)
            records.append(record)

    with (output / "manifest.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    write_json(output / "dataset_summary.json", {
        "schema_version": "1.0",
        "dataset": "IEC-ST-VerifyBench lean runtime replacement candidates",
        "task_count": len(records),
        "category_counts": dict(sorted(Counter(row["category_id"] for row in records).items())),
        "categories": {key: CATEGORIES[key] for key in selected_categories},
        "construction_rule": f"five-by-five cross-category composition; direction={args.direction}",
        "eligibility_rule": "reference MatIEC -> PLCverif -> OpenPLC within 300 seconds",
        "numeric_domain_policy": "C06 public parameters are fixed during a test and bounded to [-4,4]",
        "formal_case_budget": args.formal_case_budget,
        "selection_status": "not_run",
        "model_calls_used_to_build_oracles": False,
    })
    print(json.dumps({"status": "built", "task_count": len(records), "output": str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

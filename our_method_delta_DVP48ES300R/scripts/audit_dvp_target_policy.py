#!/usr/bin/env python3
"""Apply the prospective DVP target policy to frozen generated winners.

This is a post-hoc diagnostic.  It never changes the prespecified task result:
the report only states whether a successful historical candidate would pass the
newer target-compatibility preflight before being submitted to Windows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


METHOD_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = METHOD_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from plc_loop.delta_dvp import (  # noqa: E402
    SourceUnitError,
    parse_function_block,
    unsaturated_retained_integer_names,
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def audit_run(run_dir: Path) -> dict[str, Any]:
    result = load_json(run_dir / "result.json")
    record: dict[str, Any] = {
        "task_id": str(result["task_id"]),
        "prespecified_status": str(result["status"]),
    }
    if result.get("success") is not True:
        record["policy_status"] = "not_applicable"
        return record
    winning_attempt = int(result["winning_attempt"])
    candidate = run_dir / "attempts" / f"attempt_{winning_attempt:02d}" / "candidate.st"
    record.update({
        "winning_attempt": winning_attempt,
        "candidate_sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
    })
    try:
        block = parse_function_block(candidate.read_text(encoding="utf-8-sig"))
    except SourceUnitError as exc:
        record.update({
            "policy_status": "noncompliant",
            "reason": str(exc),
        })
    except (OSError, UnicodeError, ValueError) as exc:
        record.update({
            "policy_status": "audit_error",
            "reason": f"{type(exc).__name__}: {exc}",
        })
    else:
        advisories = unsaturated_retained_integer_names(block)
        if advisories:
            record.update({
                "policy_status": "advisory",
                "advisory": "retained_int_without_simple_saturation_pattern",
                "variables": list(advisories),
                "interpretation": (
                    "syntax-only finding; state transitions may still bound the value"
                ),
            })
        else:
            record["policy_status"] = "compliant"
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--expected-completed", type=int)
    args = parser.parse_args()

    run_root = args.run_root.resolve()
    run_dirs = sorted(
        path for path in run_root.iterdir()
        if path.is_dir() and path.name.startswith("C") and (path / "result.json").is_file()
    )
    records: list[dict[str, Any]] = []
    for run_dir in run_dirs:
        try:
            records.append(audit_run(run_dir))
        except (KeyError, TypeError, json.JSONDecodeError, OSError, ValueError) as exc:
            records.append({
                "task_id": run_dir.name,
                "policy_status": "audit_error",
                "reason": f"{type(exc).__name__}: {exc}",
            })
    counts = Counter(str(item["policy_status"]) for item in records)
    errors: list[str] = []
    if args.expected_completed is not None and len(records) != args.expected_completed:
        errors.append(
            f"completed task count is {len(records)}, expected {args.expected_completed}"
        )
    if counts.get("audit_error", 0):
        errors.append(f"{counts['audit_error']} candidates could not be audited")
    report = {
        "schema_version": "1.0",
        "purpose": "post_hoc_prospective_target_policy_not_used_for_formal_scoring",
        "policy": (
            "DVP48ES300R hard isolation/type checks plus a non-blocking syntax "
            "advisory for direct retained-INT self-increments"
        ),
        "completed_task_count": len(records),
        "prespecified_success_count": sum(
            item.get("prespecified_status") == "verified_success" for item in records
        ),
        "status_counts": dict(sorted(counts.items())),
        "records": records,
        "errors": errors,
        "audit_valid": not errors,
    }
    write_json(args.output.resolve(), report)
    print(json.dumps({
        "completed_task_count": len(records),
        "status_counts": report["status_counts"],
        "errors": errors,
    }, ensure_ascii=False))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())

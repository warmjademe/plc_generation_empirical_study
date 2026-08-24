#!/usr/bin/env python3
"""Run the customer-release DeepSeek Pro matrix through the protected Web API."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TERMINAL = {
    "verified_success",
    "generation_failed",
    "infrastructure_error",
    "contract_failed",
}


def request_json(
    url: str,
    token: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={"X-API-Key": token, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            value = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"HTTP {exc.code} from {url}: {detail}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"non-object JSON response from {url}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:18081")
    parser.add_argument("--api-token-env", default="PLC_WEB_API_TOKEN")
    parser.add_argument(
        "--matrix",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "release_tests/deepseek_pro_matrix.json",
    )
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument(
        "--only-failed-from",
        type=Path,
        help="submit only case IDs marked failed in a previous sanitized report",
    )
    parser.add_argument(
        "--requirement-id",
        action="append",
        help="submit only the named requirement ID; may be repeated",
    )
    parser.add_argument("--poll-seconds", type=float, default=5.0)
    parser.add_argument("--timeout-seconds", type=int, default=7200)
    args = parser.parse_args()
    token = os.getenv(args.api_token_env, "")
    if not token:
        raise SystemExit(f"missing {args.api_token_env}")
    matrix = json.loads(args.matrix.read_text(encoding="utf-8"))
    model = str(matrix["model"])
    if model != "deepseek-v4-pro":
        raise SystemExit("release matrix must use deepseek-v4-pro")

    selected_case_ids: set[str] | None = None
    if args.only_failed_from is not None:
        previous = json.loads(args.only_failed_from.read_text(encoding="utf-8"))
        selected_case_ids = {
            f"{item['requirement_id']}::{item['target']}::{item['language']}"
            for item in previous.get("cases", [])
            if not item.get("passed")
        }
        if not selected_case_ids:
            raise SystemExit("previous report contains no failed cases")
    selected_requirement_ids = set(args.requirement_id or [])

    jobs: dict[str, dict[str, Any]] = {}
    for requirement in matrix["requirements"]:
        if selected_requirement_ids and requirement["id"] not in selected_requirement_ids:
            continue
        for target in matrix["targets"]:
            for language in matrix["languages"]:
                case_id = f"{requirement['id']}::{target}::{language}"
                if selected_case_ids is not None and case_id not in selected_case_ids:
                    continue
                payload = {
                        "requirement": requirement["description"],
                        "vendor": "delta",
                        "plc_model": target,
                        "llm_model": model,
                        "output_language": language,
                        "max_candidates": int(matrix["max_candidates"]),
                    }
                submit_deadline = time.monotonic() + 300
                while True:
                    try:
                        created = request_json(
                            args.base_url.rstrip("/") + "/api/jobs",
                            token,
                            method="POST",
                            payload=payload,
                        )
                        break
                    except RuntimeError as exc:
                        if "HTTP 503" not in str(exc) or time.monotonic() >= submit_deadline:
                            raise
                        print(
                            f"WAITING {case_id} validation worker is not ready; retrying submission",
                            flush=True,
                        )
                        time.sleep(5)
                jobs[case_id] = {
                    "job_id": created["id"],
                    "requirement_id": requirement["id"],
                    "target": target,
                    "language": language,
                    "last_snapshot": None,
                }
                print(f"SUBMITTED {case_id} {created['id']}", flush=True)

    deadline = time.monotonic() + args.timeout_seconds
    unfinished = set(jobs)
    while unfinished and time.monotonic() < deadline:
        for case_id in sorted(unfinished):
            item = jobs[case_id]
            job = request_json(
                args.base_url.rstrip("/") + f"/api/jobs/{item['job_id']}", token
            )
            progress = request_json(
                args.base_url.rstrip("/") + f"/api/jobs/{item['job_id']}/progress",
                token,
            )
            snapshot = (
                job["status"],
                progress.get("current_attempt"),
                progress.get("current_component"),
            )
            if snapshot != item["last_snapshot"]:
                print(
                    "STATE",
                    case_id,
                    json.dumps(snapshot, ensure_ascii=False),
                    str(progress.get("message") or ""),
                    flush=True,
                )
                item["last_snapshot"] = snapshot
            if job["status"] not in TERMINAL:
                continue
            result = job.get("result") or {}
            vendor = result.get("vendor_validation") or {}
            artifacts = result.get("artifacts") or []
            artifact_kinds = sorted(
                str(artifact.get("kind"))
                for artifact in artifacts
                if isinstance(artifact, dict)
            )
            checks = {
                "verified_success": job["status"] == "verified_success",
                "resolved_model": result.get("resolved_models") == [model],
                "vendor_passed": vendor.get("status") == "passed",
                "program_returned": bool(job.get("final_program")),
                "language_artifacts": (
                    {"ld-json", "ld-svg", "lowered-st", "ispsoft-fbu"}.issubset(
                        artifact_kinds
                    )
                    if item["language"] == "ld"
                    else "st" in artifact_kinds
                ),
            }
            item.update({
                "status": job["status"],
                "candidates_used": result.get("candidates_used"),
                "resolved_models": result.get("resolved_models"),
                "vendor_status": vendor.get("status"),
                "vendor_gates": vendor.get("gates"),
                "artifact_kinds": artifact_kinds,
                "last_error": job.get("last_error"),
                "checks": checks,
                "passed": all(checks.values()),
            })
            item.pop("last_snapshot", None)
            level = "PASS" if item["passed"] else "ERROR"
            print(
                level,
                case_id,
                json.dumps(
                    {
                        "status": item["status"],
                        "candidates": item["candidates_used"],
                        "checks": checks,
                        "last_error": item["last_error"],
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
            unfinished.remove(case_id)
        if unfinished:
            time.sleep(max(1.0, args.poll_seconds))

    for case_id in sorted(unfinished):
        jobs[case_id].update({
            "status": "matrix_timeout",
            "passed": False,
            "last_error": "release matrix timeout",
        })
        jobs[case_id].pop("last_snapshot", None)
        print("ERROR", case_id, "matrix timeout", flush=True)

    report = {
        "schema_version": 1,
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "max_candidates": matrix["max_candidates"],
        "case_count": len(jobs),
        "passed": sum(bool(item.get("passed")) for item in jobs.values()),
        "failed": sum(not bool(item.get("passed")) for item in jobs.values()),
        "cases": [jobs[key] for key in sorted(jobs)],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        "SUMMARY",
        json.dumps(
            {key: report[key] for key in ("case_count", "passed", "failed")},
            ensure_ascii=False,
        ),
        flush=True,
    )
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Run MatIEC from its installation directory and return validator JSON."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


def emit(document: dict) -> int:
    print(json.dumps(document, ensure_ascii=False))
    return 0


def diagnostic_excerpt(
    stderr: str,
    stdout: str,
    returncode: int,
    limit: int = 2000,
    source: str = "",
) -> str:
    """Keep the earliest compiler errors because later diagnostics are often cascades."""
    diagnostic = stderr or stdout or f"exit code {returncode}"
    note = ""
    if "//" in source:
        note = (
            "Compatibility diagnosis: candidate contains // line comments; "
            "the frozen MatIEC profile accepts IEC block comments (* ... *) instead.\n"
        )
    if re.search(r"(?i)\bREAL\s*\(", source):
        note += (
            "Compatibility diagnosis: REAL(x) is not an IEC conversion function in the frozen "
            "profile; use INT_TO_REAL(x) when converting INT to REAL.\n"
        )
    return (note + diagnostic)[:limit]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--iec2iec", required=True)
    args = parser.parse_args()
    candidate = Path(args.candidate).resolve()
    compiler = Path(args.iec2iec).resolve()
    if not candidate.is_file() or not compiler.is_file():
        return emit({
            "status": "inconclusive",
            "summary": "MatIEC infrastructure is incomplete",
            "evidence": [{"kind": "tool_error", "summary": "candidate or iec2iec is missing"}],
        })
    try:
        completed = subprocess.run(
            [str(compiler), str(candidate)],
            cwd=compiler.parent,
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return emit({
            "status": "inconclusive",
            "summary": "MatIEC did not complete",
            "evidence": [{"kind": "tool_error", "summary": f"{type(exc).__name__}: {exc}"}],
        })
    artifact_dir = Path.cwd()
    (artifact_dir / "matiec.stdout").write_text(completed.stdout, encoding="utf-8")
    (artifact_dir / "matiec.stderr").write_text(completed.stderr, encoding="utf-8")
    if completed.returncode == 0:
        return emit({
            "status": "pass",
            "summary": "MatIEC accepted the IEC Structured Text candidate",
            "evidence": [],
            "tool_version": "matiec-0.1",
        })
    diagnostic = diagnostic_excerpt(
        completed.stderr,
        completed.stdout,
        completed.returncode,
        source=candidate.read_text(encoding="utf-8", errors="replace"),
    )
    return emit({
        "status": "fail",
        "summary": f"MatIEC rejected the candidate (exit {completed.returncode})",
        "evidence": [{
            "kind": "compile_error",
            "summary": diagnostic,
            "oracle_status": "confirmed_candidate_defect",
        }],
        "tool_version": "matiec-0.1",
    })


if __name__ == "__main__":
    raise SystemExit(main())

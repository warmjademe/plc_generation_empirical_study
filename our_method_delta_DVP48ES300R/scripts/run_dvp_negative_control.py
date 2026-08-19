#!/usr/bin/env python3
"""Replay one post-hoc requirement counterexample on OpenPLC and DVP-ES3.

Both the generated candidate and the dataset reference are evaluated.  The
negative control passes only when both runtimes reject the candidate and accept
the reference, which distinguishes an executable requirement gap from a
validator-specific translation artifact.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def write_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def parse_result(completed: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    try:
        document = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        return {
            "status": "inconclusive",
            "summary": f"validator returned invalid JSON: {exc}",
            "stdout_tail": completed.stdout[-1500:],
            "stderr_tail": completed.stderr[-1500:],
        }
    document["returncode"] = completed.returncode
    return document


def calibration_verdict(results: dict[str, dict[str, dict[str, Any]]]) -> bool:
    return all(
        results[implementation][runtime].get("status") == expected
        for implementation, expected in (("candidate", "fail"), ("reference", "pass"))
        for runtime in ("openplc", "dvp48es300r")
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--task-dir", required=True, type=Path)
    parser.add_argument("--suite", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--openplc-validator", required=True, type=Path)
    parser.add_argument("--openplc-runner", required=True, type=Path)
    parser.add_argument("--dvp-validator", required=True, type=Path)
    parser.add_argument("--spool-root", required=True, type=Path)
    parser.add_argument("--docker", default="/snap/bin/docker")
    parser.add_argument("--image", default="plc-egbs/openplc-v3:b5d41356")
    parser.add_argument("--timeout-seconds", type=int, default=2400)
    args = parser.parse_args()

    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty output {output}")
    output.mkdir(parents=True, exist_ok=True)
    task_dir = args.task_dir.resolve()
    candidate = args.candidate.resolve()
    reference = task_dir / "reference.st"
    required = [
        candidate,
        reference,
        task_dir / "metadata.json",
        args.suite.resolve(),
        args.openplc_validator.resolve(),
        args.openplc_runner.resolve(),
        args.dvp_validator.resolve(),
        args.spool_root.resolve(),
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"negative-control input is missing: {missing}")

    suite = json.loads(args.suite.read_text(encoding="utf-8-sig"))
    if suite.get("independent_requirement_oracle") is not True:
        raise ValueError("negative-control suite must be an independent requirement Oracle")
    if not suite.get("cases") or any(
        not str(case.get("id", "")).startswith("FT") for case in suite["cases"]
    ):
        raise ValueError("every negative-control case must use a visible FT identifier")
    synthetic_task = output / "task"
    synthetic_task.mkdir()
    shutil.copyfile(task_dir / "metadata.json", synthetic_task / "metadata.json")
    shutil.copyfile(args.suite.resolve(), synthetic_task / "openplc_tests.json")

    results: dict[str, dict[str, dict[str, Any]]] = {}
    commands: dict[str, dict[str, list[str]]] = {}
    for implementation, source in (("candidate", candidate), ("reference", reference)):
        implementation_dir = output / implementation
        implementation_dir.mkdir()
        openplc_dir = implementation_dir / "openplc"
        dvp_dir = implementation_dir / "dvp48es300r"
        openplc_dir.mkdir()
        dvp_dir.mkdir()
        openplc_command = [
            sys.executable,
            str(args.openplc_validator.resolve()),
            "--candidate", str(source),
            "--task-dir", str(synthetic_task),
            "--docker", args.docker,
            "--image", args.image,
            "--runner", str(args.openplc_runner.resolve()),
            "--case-role", "feedback",
        ]
        dvp_command = [
            sys.executable,
            str(args.dvp_validator.resolve()),
            "--candidate", str(source),
            "--task-dir", str(synthetic_task),
            "--case-role", "feedback",
            "--spool-root", str(args.spool_root.resolve()),
            "--timeout-seconds", str(max(60, args.timeout_seconds - 60)),
        ]
        commands[implementation] = {
            "openplc": openplc_command,
            "dvp48es300r": dvp_command,
        }
        openplc_completed = subprocess.run(
            openplc_command,
            cwd=openplc_dir,
            text=True,
            capture_output=True,
            timeout=args.timeout_seconds,
            check=False,
        )
        dvp_completed = subprocess.run(
            dvp_command,
            cwd=dvp_dir,
            text=True,
            capture_output=True,
            timeout=args.timeout_seconds,
            check=False,
        )
        results[implementation] = {
            "openplc": parse_result(openplc_completed),
            "dvp48es300r": parse_result(dvp_completed),
        }
        write_json(implementation_dir / "results.json", results[implementation])

    document = {
        "schema_version": "1.0",
        "purpose": "post_hoc_false_positive_negative_control_not_used_for_formal_scoring",
        "task_id": suite.get("task_id"),
        "candidate": str(candidate),
        "reference": str(reference),
        "suite": str(args.suite.resolve()),
        "commands": commands,
        "results": results,
        "calibration_pass": calibration_verdict(results),
        "interpretation": (
            "A pass means the same added requirement vector rejects the generated "
            "candidate and accepts the reference in both OpenPLC and ISPSoft/COMMGR."
        ),
    }
    write_json(output / "negative_control.json", document)
    print(json.dumps({
        "task_id": document["task_id"],
        "calibration_pass": document["calibration_pass"],
        "statuses": {
            implementation: {
                runtime: result.get("status") for runtime, result in runtime_results.items()
            }
            for implementation, runtime_results in results.items()
        },
    }, ensure_ascii=False))
    return 0 if document["calibration_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

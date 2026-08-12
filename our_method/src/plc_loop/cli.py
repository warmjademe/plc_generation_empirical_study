"""Command-line interface for the bounded synthesis harness."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .dataset import load_task
from .ledger import EvidenceLedger
from .orchestrator import BoundedSynthesisHarness, METHODS, load_config, run_from_paths


def command_preflight(args: argparse.Namespace) -> int:
    harness = BoundedSynthesisHarness(
        load_config(args.config),
        load_task(args.task),
        Path(args.output),
        args.method,
        client=None,
    )
    harness.preflight()
    print(json.dumps({"status": "pass", "task": harness.task.task_id, "method": args.method}, ensure_ascii=False))
    return 0


def command_run(args: argparse.Namespace) -> int:
    result = run_from_paths(Path(args.config), Path(args.task), Path(args.output), args.method)
    print(json.dumps({key: result[key] for key in ("task_id", "method", "status", "candidates_used")}, ensure_ascii=False))
    if result["success"]:
        return 0
    return 2 if result["status"] in {"infrastructure_error", "sealed_inconclusive"} else 1


def command_verify_ledger(args: argparse.Namespace) -> int:
    entries = EvidenceLedger.verify(Path(args.path))
    print(json.dumps({"status": "pass", "events": len(entries), "final_hash": entries[-1]["event_hash"] if entries else None}))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="plc-evidence-loop")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("preflight", "run"):
        command = subparsers.add_parser(name)
        command.add_argument("--config", required=True)
        command.add_argument("--task", required=True)
        command.add_argument("--output", required=True)
        command.add_argument("--method", choices=sorted(METHODS), default="evidence")
        command.set_defaults(func=command_preflight if name == "preflight" else command_run)
    verify = subparsers.add_parser("verify-ledger")
    verify.add_argument("path")
    verify.set_defaults(func=command_verify_ledger)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        print(json.dumps({"status": "error", "type": type(exc).__name__, "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())


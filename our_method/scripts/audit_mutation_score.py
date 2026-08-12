#!/usr/bin/env python3
"""Measure oracle adequacy with compiling, probe-distinguishable ST mutants.

The script never calls an LLM.  It creates first-order mutations only in the
executable body of each reference program, retains mutants for which a bounded
differential probe finds a concrete reference/mutant disagreement, and then runs
the configured verification layers.  A mutant accepted by all scored layers is a
confirmed test-oracle false positive relative to that recorded counterexample.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import random
import re
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from plc_loop.dataset import load_task
from plc_loop.orchestrator import load_config
from plc_loop.validators import DatasetScanValidator, validators_from_config


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def executable_parts(source: str) -> tuple[str, str]:
    marker = "\nEND_VAR\n"
    offset = source.rfind(marker)
    if offset < 0:
        raise ValueError("cannot locate executable body")
    start = offset + len(marker)
    end = source.rfind("\nEND_FUNCTION_BLOCK")
    if end < start:
        raise ValueError("cannot locate END_FUNCTION_BLOCK")
    return source[:start], source[start:end]


def mutation_candidates(source: str, outputs: list[dict[str, Any]]) -> list[dict[str, str]]:
    prefix, body = executable_parts(source)
    suffix = "\nEND_FUNCTION_BLOCK\n"
    candidates: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(operator: str, detail: str, mutated_body: str) -> None:
        program = prefix + mutated_body.rstrip() + suffix
        digest = sha256_text(program)
        if program != source and digest not in seen:
            seen.add(digest)
            candidates.append({"operator": operator, "detail": detail, "program": program})

    token_replacements = {
        "TRUE": "FALSE",
        "FALSE": "TRUE",
        "AND": "OR",
        "OR": "AND",
        "XOR": "OR",
    }
    for match in re.finditer(r"\b(TRUE|FALSE|AND|OR|XOR)\b", body, re.IGNORECASE):
        old = match.group(0).upper()
        new = token_replacements[old]
        add("token_replacement", f"{old}->{new} at body offset {match.start()}", body[:match.start()] + new + body[match.end():])

    comparison_replacements = {
        ">=": ">", "<=": "<", "<>": "=", "=": "<>", ">": ">=", "<": "<=",
    }
    for match in re.finditer(r">=|<=|<>|(?<!:)=(?!=)|(?<![<>])>(?!=)|(?<![<>])<(?!=)", body):
        old = match.group(0)
        new = comparison_replacements[old]
        add("comparison_replacement", f"{old}->{new} at body offset {match.start()}", body[:match.start()] + new + body[match.end():])

    for match in re.finditer(r"(?<![#A-Za-z0-9_.])([0-9]+(?:\.[0-9]+)?)(?![A-Za-z0-9_.])", body):
        raw = match.group(1)
        if "." in raw:
            value = float(raw)
            replacements = (repr(value + 1.0), repr(value - 1.0))
        else:
            value = int(raw)
            replacements = (str(value + 1), str(value - 1))
        for new in replacements:
            add("constant_shift", f"{raw}->{new} at body offset {match.start(1)}", body[:match.start(1)] + new + body[match.end(1):])

    for match in re.finditer(r"(?i)T#([0-9]+)ms", body):
        milliseconds = int(match.group(1))
        for shifted in sorted({max(0, milliseconds - 100), milliseconds + 100}):
            replacement = f"T#{shifted}ms"
            add(
                "timer_boundary_shift",
                f"T#{milliseconds}ms->{replacement} at body offset {match.start()}",
                body[:match.start()] + replacement + body[match.end():],
            )

    for match in re.finditer(r"(?im)^(\s*)(IF|ELSIF)\s+(.+?)\s+THEN\s*$", body):
        indent, keyword, condition = match.groups()
        replacement = f"{indent}{keyword} NOT ({condition}) THEN"
        add("condition_negation", f"negate {keyword} condition at body offset {match.start()}", body[:match.start()] + replacement + body[match.end():])

    # Statement deletion models an omitted output/state update.  Some deletions
    # leave an empty branch and are rejected later by the parser/compiler; valid
    # ones remain valuable semantic mutants.
    for match in re.finditer(r"(?im)^\s*[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?\s*:=\s*[^;]+;\s*$", body):
        add(
            "assignment_deletion",
            f"delete assignment at body offset {match.start()}",
            body[:match.start()] + "(* mutation: assignment omitted *)" + body[match.end():],
        )

    defaults = {"BOOL": "FALSE", "INT": "0", "DINT": "0", "REAL": "0.0"}
    for output in outputs:
        forced = defaults.get(str(output["type"]).upper())
        if forced is None:
            continue
        add(
            "output_override",
            f"force {output['name']} to {forced} after normal logic",
            body.rstrip() + f"\n{output['name']} := {forced};\n",
        )
    # Round-robin mutation families so a five-mutant task does not consist only
    # of, for example, the first five Boolean literal flips in source order.
    by_operator: dict[str, list[dict[str, str]]] = {}
    for candidate in candidates:
        by_operator.setdefault(candidate["operator"], []).append(candidate)
    ordered = []
    for index in range(max((len(items) for items in by_operator.values()), default=0)):
        for operator in sorted(by_operator):
            if index < len(by_operator[operator]):
                ordered.append(by_operator[operator][index])
    return ordered


def value_pools(metadata: dict[str, Any], suites: list[dict[str, Any]]) -> dict[str, list[Any]]:
    observed: dict[str, list[Any]] = {item["name"]: [] for item in metadata["interface"]["inputs"]}
    for suite in suites:
        for case in suite["cases"]:
            for item in case["steps"]:
                for name, value in item["inputs"].items():
                    if value not in observed[name]:
                        observed[name].append(value)
    pools: dict[str, list[Any]] = {}
    for field in metadata["interface"]["inputs"]:
        name, typ = field["name"], field["type"].upper()
        values = list(observed[name])
        if typ == "BOOL":
            values = [False, True]
        elif typ in {"INT", "DINT"}:
            expanded = {-1, 0, 1}
            for value in values:
                expanded.update((int(value) - 1, int(value), int(value) + 1))
            values = sorted(expanded)[:12]
        elif typ == "REAL":
            expanded = {-1.0, 0.0, 1.0}
            for value in values:
                numeric = float(value)
                expanded.update((numeric - 0.5, numeric, numeric + 0.5))
            values = sorted(expanded)[:12]
        pools[name] = values
    return pools


def probe_traces(metadata: dict[str, Any], suites: list[dict[str, Any]], seed: int) -> list[list[dict[str, Any]]]:
    fields = metadata["interface"]["inputs"]
    names = [item["name"] for item in fields]
    pools = value_pools(metadata, suites)
    defaults = {name: values[0] for name, values in pools.items()}
    traces: list[list[dict[str, Any]]] = []

    # Replay every authored scan, including intermediate scans hidden by
    # ``last_only``.  Reference and mutant outputs are compared after each scan.
    for suite in suites:
        for case in suite["cases"]:
            trace = []
            for item in case["steps"]:
                trace.extend([dict(item["inputs"])] * int(item["repeat"]))
            traces.append(trace)

    product_size = 1
    for name in names:
        product_size *= len(pools[name])
    if product_size <= 256:
        combinations = itertools.product(*(pools[name] for name in names))
        traces.extend([[dict(zip(names, values))] for values in combinations])
    else:
        rng = random.Random(seed)
        for _ in range(128):
            traces.append([{name: rng.choice(pools[name]) for name in names}])

    horizon = max(3, int(metadata["complexity"].get("horizon_scans", 1)))
    bool_names = [item["name"] for item in fields if item["type"].upper() == "BOOL"]
    for name in bool_names:
        high = dict(defaults)
        high[name] = True
        traces.append([dict(defaults)] + [high] * (horizon + 2) + [dict(defaults)] * 2)
    for left, right in itertools.combinations(bool_names[:6], 2):
        simultaneous = dict(defaults)
        simultaneous[left] = True
        simultaneous[right] = True
        traces.append([dict(defaults)] + [simultaneous] * (horizon + 1) + [dict(defaults)] * 2)

    rng = random.Random(seed ^ 0x5EED5EED)
    for _ in range(24):
        trace = []
        current = dict(defaults)
        length = min(80, horizon * 3 + 8)
        for scan_index in range(length):
            if scan_index == 0 or rng.random() < 0.35:
                current = {name: rng.choice(pools[name]) for name in names}
            trace.append(dict(current))
        traces.append(trace)
    return traces


def first_difference(
    engine: Any,
    reference: str,
    mutant: str,
    metadata: dict[str, Any],
    suites: list[dict[str, Any]],
    seed: int,
) -> dict[str, Any] | None:
    outputs = [item["name"] for item in metadata["interface"]["outputs"]]
    tolerance = float(suites[0].get("real_absolute_tolerance", 0.001))
    dt_ms = int(metadata["scan"]["period_ms"])
    try:
        traces = probe_traces(metadata, suites, seed)
        for trace_index, trace in enumerate(traces):
            ref_sim = engine.Simulator(reference)
            mut_sim = engine.Simulator(mutant)
            for scan_index, inputs in enumerate(trace, start=1):
                for name, value in inputs.items():
                    ref_sim.set_input(name, value)
                    mut_sim.set_input(name, value)
                ref_sim.scan(dt_ms)
                mut_sim.scan(dt_ms)
                ref_outputs = {name: ref_sim.get(name) for name in outputs}
                mut_outputs = {name: mut_sim.get(name) for name in outputs}
                differs = False
                for name in outputs:
                    left, right = ref_outputs[name], mut_outputs[name]
                    if isinstance(left, float) or isinstance(right, float):
                        differs = differs or abs(float(left) - float(right)) > tolerance
                    else:
                        differs = differs or left != right
                if differs:
                    return {
                        "trace_index": trace_index,
                        "scan": scan_index,
                        "inputs": inputs,
                        "input_trace_prefix": trace[:scan_index],
                        "reference_outputs": ref_outputs,
                        "mutant_outputs": mut_outputs,
                    }
    except Exception:
        return None
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--engine-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--mutants-per-task", type=int, default=5)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20260810)
    parser.add_argument("--run-openplc", action="store_true")
    parser.add_argument(
        "--require-zero-survivors",
        action="store_true",
        help="fail unless every task supplies the requested number of assessed mutants and none survives",
    )
    args = parser.parse_args()

    dataset_root = args.dataset_root.resolve()
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty audit directory {output}")
    output.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(args.engine_root.resolve()))
    from deltaplc import engine  # type: ignore

    config = load_config(args.config.resolve())
    configured = {validator.name: validator for validator in validators_from_config(config["validators"], Path(config["_config_dir"]))}
    hidden_scan = DatasetScanValidator("hidden_scan", "hidden", args.engine_root.resolve(), sealed=True)
    task_dirs = sorted(path for path in (dataset_root / "tasks").iterdir() if path.is_dir())

    def audit_task(task_dir: Path) -> dict[str, Any]:
        task = load_task(task_dir)
        metadata = json.loads((task_dir / "metadata.json").read_text(encoding="utf-8"))
        suites = [
            json.loads((task_dir / "tests_feedback.json").read_text(encoding="utf-8")),
            json.loads((task_dir / "tests_hidden.json").read_text(encoding="utf-8")),
        ]
        reference = (task_dir / "reference.st").read_text(encoding="utf-8")
        task_output = output / task.task_id
        task_output.mkdir()
        compiler = configured["compiler"]
        compiler.preflight(task)
        selected = []
        for index, candidate in enumerate(mutation_candidates(reference, metadata["interface"]["outputs"]), start=1):
            # Mutation adequacy counts only programs accepted by the production
            # compiler.  Syntax-invalid mutants are neither semantic challenges
            # nor evidence that the functional oracle killed a defect.
            with tempfile.TemporaryDirectory(dir=task_output, prefix="compile_probe_") as probe_name:
                probe_dir = Path(probe_name)
                probe_path = probe_dir / "candidate.st"
                probe_path.write_text(candidate["program"], encoding="utf-8")
                compiler_result = compiler.run(task, probe_path, probe_dir)
            if compiler_result.status != "pass":
                continue
            difference = first_difference(
                engine, reference, candidate["program"], metadata, suites,
                args.seed + sum(ord(char) for char in task.task_id) + index,
            )
            if difference is None:
                continue
            selected.append({**candidate, "counterexample": difference})
            if len(selected) >= args.mutants_per_task:
                break

        records = []
        validators = [configured[name] for name in ("interface", "compiler", "feedback_tests", "plcverif")]
        for validator in validators:
            validator.preflight(task)
        hidden_scan.preflight(task)
        if args.run_openplc:
            configured["sealed_openplc"].preflight(task)
        for number, selected_mutant in enumerate(selected, start=1):
            mutant_dir = task_output / f"M{number:02d}"
            mutant_dir.mkdir()
            candidate_path = mutant_dir / "candidate.st"
            candidate_path.write_text(selected_mutant.pop("program"), encoding="utf-8")
            gates = []
            for validator in validators:
                result = validator.run(task, candidate_path, mutant_dir)
                gates.append(result)
                if result.status == "fail" and validator.blocking:
                    break
                if result.status == "inconclusive" and validator.blocking and getattr(validator, "inconclusive_is_blocking", True):
                    break
            gate_statuses = {gate.name: gate.status for gate in gates}
            eligible_for_sealed = (
                gate_statuses.get("interface") == "pass"
                and gate_statuses.get("compiler") == "pass"
                and gate_statuses.get("feedback_tests") == "pass"
                and gate_statuses.get("plcverif") == "pass"
            )
            if eligible_for_sealed:
                hidden = hidden_scan.run(task, candidate_path, mutant_dir)
                gates.append(hidden)
                if hidden.status == "pass" and args.run_openplc:
                    gates.append(configured["sealed_openplc"].run(task, candidate_path, mutant_dir))
            gate_statuses = {gate.name: gate.status for gate in gates}
            accepted = (
                eligible_for_sealed
                and gate_statuses.get("hidden_scan") == "pass"
                and (not args.run_openplc or gate_statuses.get("sealed_openplc") == "pass")
            )
            semantic_failures = {
                name for name, status in gate_statuses.items()
                if status == "fail" and name not in {"interface", "compiler"}
            }
            killed = bool(semantic_failures)
            assessed = accepted or killed
            record = {
                "mutant_id": f"M{number:02d}",
                "operator": selected_mutant["operator"],
                "detail": selected_mutant["detail"],
                "candidate_sha256": hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
                "probe_counterexample": selected_mutant["counterexample"],
                "gates": [gate.to_dict() for gate in gates],
                "verifier_accepted": accepted,
                "verifier_killed": killed,
                "assessment_complete": assessed,
            }
            write_json(mutant_dir / "audit.json", record)
            records.append(record)
        return {
            "task_id": task.task_id,
            "requested_mutants": args.mutants_per_task,
            "qualified_mutants": len(records),
            "accepted_mutants": sum(item["verifier_accepted"] for item in records),
            "killed_mutants": sum(item["verifier_killed"] for item in records),
            "inconclusive_mutants": sum(not item["assessment_complete"] for item in records),
            "records": records,
        }

    task_records = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(audit_task, task_dir): task_dir.name for task_dir in task_dirs}
        for future in as_completed(futures):
            task_id = futures[future]
            try:
                record = future.result()
            except Exception as exc:
                record = {
                    "task_id": task_id, "error": f"{type(exc).__name__}: {exc}",
                    "qualified_mutants": 0, "accepted_mutants": 0,
                    "killed_mutants": 0, "inconclusive_mutants": 0,
                }
            task_records.append(record)
            print(json.dumps({key: record.get(key) for key in ("task_id", "qualified_mutants", "accepted_mutants", "error") if record.get(key) is not None}, ensure_ascii=False), flush=True)
    task_records.sort(key=lambda item: item["task_id"])
    total = sum(int(item["qualified_mutants"]) for item in task_records)
    accepted = sum(int(item["accepted_mutants"]) for item in task_records)
    killed = sum(int(item["killed_mutants"]) for item in task_records)
    inconclusive = sum(int(item["inconclusive_mutants"]) for item in task_records)
    document = {
        "schema_version": "1.0",
        "audit_type": "first-order mutation adequacy with bounded differential non-equivalence witness",
        "dataset_version": json.loads((dataset_root / "dataset_summary.json").read_text(encoding="utf-8"))["version"],
        "seed": args.seed,
        "requested_mutants_per_task": args.mutants_per_task,
        "qualified_non_equivalent_mutants": total,
        "assessed_mutants": accepted + killed,
        "killed_mutants": killed,
        "accepted_false_positive_mutants": accepted,
        "inconclusive_mutants": inconclusive,
        "mutation_score": killed / (accepted + killed) if accepted + killed else None,
        "openplc_included": args.run_openplc,
        "task_shortfall_count": sum(int(item["qualified_mutants"]) < args.mutants_per_task for item in task_records),
        "tasks": task_records,
        "scope_limit": "bounded probes establish non-equivalence for retained mutants; mutation score is not a universal correctness probability",
    }
    write_json(output / "mutation_audit.json", document)
    print(json.dumps({key: document[key] for key in (
        "qualified_non_equivalent_mutants", "assessed_mutants", "killed_mutants",
        "accepted_false_positive_mutants", "inconclusive_mutants", "mutation_score",
        "task_shortfall_count",
    )}, ensure_ascii=False))
    if any("error" in item for item in task_records):
        return 2
    if args.require_zero_survivors and (
        accepted != 0 or inconclusive != 0 or document["task_shortfall_count"] != 0
    ):
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

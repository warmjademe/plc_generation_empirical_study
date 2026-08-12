"""Build sealed, reference-derived stress traces for IEC-ST-VerifyBench.

The hand-authored hidden suite remains the independent requirement oracle.  This
module adds boundary, conflict, temporal-intermediate, and seeded stateful traces.
Expected outputs are materialized by the frozen reference implementation and are
therefore labelled as a differential oracle rather than independent evidence.
"""

from __future__ import annotations

import itertools
import json
import random
import sys
from pathlib import Path
from typing import Any


# Regression traces come from mutation-testing categories, not evaluated model
# outputs.  They make boundary and intermediate-state obligations explicit.
REGRESSION_INPUTS: dict[str, list[list[dict[str, Any]]]] = {
    "C03_H02_safety_zone_arbitration": [[{
        "RobotRequest": False, "ConveyorRequest": True, "ManualRequest": False,
        "GuardClosed": True, "EStopOK": True, "ManualKey": False,
    }]],
    "C05_H01_two_stage_startup": [[{
        "Start": True, "Stop": False, "Permit": True, "Stage1Feedback": False,
    }] * 5],
    "C06_M02_bounded_up_down_counter": [[{
        "AddItem": True, "RemoveItem": False, "Reset": False, "Capacity": 0,
    }]],
    "C07_H01_redundant_sensor_selection": [[{
        "SensorA": 9.5, "SensorB": 10.5, "ValidA": True, "ValidB": True,
        "MaxDifference": 1.0,
    }]],
    "C07_H02_rate_of_change_trip": [[
        {"Value": 10.0, "Enable": True, "MaxRise": 2.5, "MaxFall": 2.5, "Reset": False},
        {"Value": 12.5, "Enable": True, "MaxRise": 2.5, "MaxFall": 2.5, "Reset": False},
    ]],
    "C09_H02_delayed_warning_trip_lockout": [[{
        "WarningCondition": True, "TripCondition": False, "Enable": False,
        "Acknowledge": False, "Reset": False,
    }] * 5],
    "C09_M01_high_high_alarm_priority": [[{
        "Value": 70.0, "HighLimit": 60.0, "HighHighLimit": 70.0, "Reset": False,
    }]],
    "C09_M02_qualified_sensor_disagreement": [[{
        "SensorA": 1.0, "SensorB": 0.0, "MaxDifference": 1.0,
        "Enable": True, "Reset": False,
    }]],
    "C10_M01_alternating_pump_starts": [[{
        "Demand": False, "Pump1Available": False, "Pump2Available": False,
        "Reset": False,
    }]],
}


def load_engine(engine_root: Path):
    root = str(engine_root.resolve())
    if root not in sys.path:
        sys.path.insert(0, root)
    from deltaplc import engine  # type: ignore
    return engine


def _raw_suites(item: dict[str, Any]) -> list[list[dict[str, Any]]]:
    traces = []
    for suite_name in ("feedback_tests", "hidden_tests"):
        for case in item[suite_name]:
            trace = []
            for item_step in case["steps"]:
                trace.extend([dict(item_step["inputs"])] * int(item_step["repeat"]))
            traces.append(trace)
    return traces


def _pools(item: dict[str, Any]) -> dict[str, list[Any]]:
    observed = {field["name"]: [] for field in item["inputs"]}
    for trace in _raw_suites(item):
        for inputs in trace:
            for name, value in inputs.items():
                if value not in observed[name]:
                    observed[name].append(value)
    pools = {}
    for field in item["inputs"]:
        name, typ = field["name"], field["type"].upper()
        values = observed[name]
        if typ == "BOOL":
            pools[name] = [False, True]
        elif typ in {"INT", "DINT"}:
            expanded = {-1, 0, 1}
            for value in values:
                expanded.update((int(value) - 1, int(value), int(value) + 1))
            pools[name] = sorted(expanded)[:10]
        elif typ == "REAL":
            expanded = {-1.0, 0.0, 1.0}
            for value in values:
                numeric = float(value)
                expanded.update((numeric - 0.5, numeric, numeric + 0.5))
            pools[name] = sorted(expanded)[:10]
        else:
            pools[name] = list(values)
    return pools


def _stress_inputs(item: dict[str, Any], seed: int) -> list[tuple[str, list[dict[str, Any]]]]:
    names = [field["name"] for field in item["inputs"]]
    bool_names = [field["name"] for field in item["inputs"] if field["type"].upper() == "BOOL"]
    pools = _pools(item)
    field_types = {field["name"]: field["type"].upper() for field in item["inputs"]}
    defaults = {}
    for name, values in pools.items():
        typ = field_types[name]
        if typ == "BOOL":
            defaults[name] = False
        elif typ in {"INT", "DINT"}:
            defaults[name] = 0 if 0 in values else int(values[0])
        elif typ == "REAL":
            defaults[name] = 0.0 if 0.0 in values else float(values[0])
        else:
            defaults[name] = values[0]
    traces: list[tuple[str, list[dict[str, Any]]]] = []
    for index, trace in enumerate(_raw_suites(item), start=1):
        traces.append((f"authored_replay_{index}", trace))

    product_size = 1
    for name in names:
        product_size *= len(pools[name])
    boundary_vectors = []
    if product_size <= 256:
        boundary_vectors = [dict(zip(names, values)) for values in itertools.product(*(pools[name] for name in names))]
    else:
        rng = random.Random(seed)
        seen = set()
        while len(boundary_vectors) < 64:
            vector = {name: rng.choice(pools[name]) for name in names}
            key = json.dumps(vector, sort_keys=True)
            if key not in seen:
                seen.add(key)
                boundary_vectors.append(vector)
    # Each boundary vector starts from a fresh instance; this avoids retained
    # state from masking an initialization or exact-boundary defect.
    for index, vector in enumerate(boundary_vectors, start=1):
        traces.append((f"boundary_{index:03d}", [vector]))

    horizon = max(3, int(item.get("complexity", {}).get("horizon_scans", 1)))
    hold = min(horizon + 2, 14)
    for name in bool_names:
        active = dict(defaults)
        active[name] = True
        traces.append((f"hold_{name}", [dict(defaults)] + [active] * hold + [dict(defaults)] * 2))
    for index, (left, right) in enumerate(itertools.combinations(bool_names, 2)):
        if index >= 15:
            break
        active = dict(defaults)
        active[left] = True
        active[right] = True
        traces.append((f"conflict_{left}_{right}", [dict(defaults), active, dict(defaults)]))

    rng = random.Random(seed ^ 0x5EED5EED)
    for trace_index in range(4):
        current = dict(defaults)
        trace = []
        for scan_index in range(min(60, horizon * 3 + 12)):
            if scan_index == 0 or rng.random() < 0.30:
                current = {name: rng.choice(pools[name]) for name in names}
            trace.append(dict(current))
        traces.append((f"seeded_hold_{trace_index + 1}", trace))

    for index, trace in enumerate(REGRESSION_INPUTS.get(item["id"], []), start=1):
        traces.append((f"mutation_boundary_regression_{index}", trace))
    return traces


def build_stress_suite(item: dict[str, Any], reference: str, engine_root: Path, seed: int = 20260810) -> dict[str, Any]:
    engine = load_engine(engine_root)
    outputs = [field["name"] for field in item["outputs"]]
    cases = []
    task_seed = seed + sum(ord(character) for character in item["id"])
    for index, (name, trace) in enumerate(_stress_inputs(item, task_seed), start=1):
        simulator = engine.Simulator(reference)
        steps = []
        for inputs in trace:
            for input_name, value in inputs.items():
                simulator.set_input(input_name, value)
            simulator.scan(int(item["scan_period_ms"]))
            steps.append({
                "inputs": inputs,
                "expect": {output: simulator.get(output) for output in outputs},
                "repeat": 1,
                "check": "each",
            })
        cases.append({
            "id": f"ST{index:03d}",
            "name": name,
            "description": "Sealed boundary/state trace generated from the frozen reference implementation.",
            "requirement_ids": [requirement["id"] for requirement in item["requirements"]],
            "fresh_instance": True,
            "steps": steps,
        })
    return {
        "schema_version": "1.0",
        "suite": "stress",
        "task_id": item["id"],
        "scan_period_ms": item["scan_period_ms"],
        "real_absolute_tolerance": item["real_tolerance"],
        "oracle_source": "frozen_reference_st_differential_trace",
        "independent_requirement_oracle": False,
        "seed": seed,
        "cases": cases,
    }

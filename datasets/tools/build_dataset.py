#!/usr/bin/env python3
"""Build the canonical 50-task IEC-ST-VerifyBench dataset.

The task definitions below are the source of truth.  The script materializes the
human-readable requirements, fixed interfaces, reference ST, properties, tests,
one optional negative control per task, validation placeholders, and manifests.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from collections import Counter
from pathlib import Path

from stress_oracle import build_stress_suite
from challenge_tasks import challenge_tasks


ROOT = Path(__file__).resolve().parents[1]
TASK_ROOT = ROOT / "tasks"
DATASET_VERSION = "0.2.0-dev"


CATEGORIES = {
    "C01": "Boolean and conditional logic",
    "C02": "Start/stop and retained state",
    "C03": "Interlocks and safe outputs",
    "C04": "Edge and event handling",
    "C05": "Timers and timeouts",
    "C06": "Counters and batch logic",
    "C07": "Analog processing",
    "C08": "Sequential state machines",
    "C09": "Alarms and fault recovery",
    "C10": "Multi-device coordination",
}


# PLCverif treats ordinary VAR_INPUT fields as fresh nondeterministic values on
# every scan.  These frozen parameters and guards are the machine-readable form
# of public task assumptions; the adapter records and applies them verbatim.
PLCV_ENVIRONMENTS = {
    "C04_H01_qualified_event_counter": {
        "parameters": ["MaxCount"],
        "assumption_invariants": ["MaxCount >= 1"],
    },
    "C04_X01_dual_event_saturating_recorder": {
        "parameters": ["MaxCount"],
        "assumption_invariants": [],
        "public_assumptions": ["MaxCount remains constant during a test."],
    },
    "C06_M01_configurable_batch_counter": {
        "parameters": ["Target"],
        "assumption_invariants": ["Target >= 1", "Target <= 100"],
    },
    "C06_M02_bounded_up_down_counter": {
        "parameters": ["Capacity"],
        "assumption_invariants": ["Capacity >= 1"],
    },
    "C06_H01_quality_batch_statistics": {
        "parameters": ["BatchTarget", "RejectLimit"],
        "assumption_invariants": ["BatchTarget >= 1", "RejectLimit >= 1"],
    },
    "C06_H02_inspection_window_lockout": {
        "parameters": ["WindowSize", "RejectLimit"],
        "assumption_invariants": ["WindowSize >= 1", "RejectLimit >= 0"],
    },
    "C06_X01_batch_quality_lockout": {
        "parameters": ["Target", "RejectLimit"],
        "assumption_invariants": [],
        "public_assumptions": ["Target and RejectLimit remain constant during a test."],
    },
    "C07_H01_redundant_sensor_selection": {
        "parameters": ["MaxDifference"],
        "assumption_invariants": ["MaxDifference >= 0.0"],
    },
    "C07_H02_rate_of_change_trip": {
        "parameters": ["MaxRise", "MaxFall"],
        "assumption_invariants": ["MaxRise >= 0.0", "MaxFall >= 0.0"],
        "public_assumptions": ["MaxRise and MaxFall are non-negative and remain constant during a test."],
        "cbmc_unwind": 3,
    },
    "C09_M01_high_high_alarm_priority": {
        "parameters": ["HighLimit", "HighHighLimit"],
        "assumption_invariants": ["HighHighLimit > HighLimit"],
    },
    "C09_M02_qualified_sensor_disagreement": {
        "parameters": ["MaxDifference"],
        "assumption_invariants": ["MaxDifference >= 0.0"],
    },
}


NEGATIVE_CONTROL_OVERRIDES = {
    "C03_X01_ventilated_heater_interlock": {
        "output": "HeaterCommand",
        "forced_value": "FALSE",
        "target_requirement_ids": ["R2"],
        "witness_suite": "feedback",
        "witness_case": "normal_proven_start",
    },
}


def var(name: str, typ: str, description: str) -> dict:
    return {"name": name, "type": typ, "description": description}


def req(text: str, prop: str | None = None, critical: bool = False) -> dict:
    return {"text": text, "property": prop, "safety_critical": critical}


def step(inputs: dict, expect: dict, repeat: int = 1, check: str = "each") -> dict:
    return {"inputs": inputs, "expect": expect, "repeat": repeat, "check": check}


def test(name: str, requirement_ids: list[str], steps: list[dict], description: str) -> dict:
    return {
        "name": name,
        "description": description,
        "requirement_ids": requirement_ids,
        "fresh_instance": True,
        "steps": steps,
    }


def task(
    task_id: str,
    title: str,
    category: str,
    difficulty: str,
    inputs: list[dict],
    outputs: list[dict],
    requirements: list[dict],
    body: str,
    feedback_tests: list[dict],
    hidden_tests: list[dict],
    *,
    internal_vars: list[str] | None = None,
    iec_features: list[str] | None = None,
    assumptions: list[str] | None = None,
    complexity: dict | None = None,
    scan_period_ms: int = 100,
    real_tolerance: float = 0.001,
) -> dict:
    assert category in CATEGORIES
    assert difficulty in {"easy", "medium", "hard"}
    numbered = []
    for index, item in enumerate(requirements, start=1):
        numbered.append({"id": f"R{index}", **item})
    task_assumptions = list(assumptions) if assumptions is not None else [
        "The function block is called exactly once per PLC scan.",
        "Inputs are sampled at scan start and outputs are checked at scan end.",
        "Each test starts from a fresh function-block instance.",
    ]
    for statement in PLCV_ENVIRONMENTS.get(task_id, {}).get("public_assumptions", []):
        if statement not in task_assumptions:
            task_assumptions.append(statement)
    return {
        "id": task_id,
        "title": title,
        "category_id": category,
        "category": CATEGORIES[category],
        "difficulty": difficulty,
        "inputs": inputs,
        "outputs": outputs,
        "requirements": numbered,
        "body": body.strip(),
        "internal_vars": internal_vars or [],
        "iec_features": iec_features or ["FUNCTION_BLOCK", "BOOL", "IF"],
        "assumptions": task_assumptions,
        "complexity": complexity or {},
        "scan_period_ms": scan_period_ms,
        "real_tolerance": real_tolerance,
        "feedback_tests": feedback_tests,
        "hidden_tests": hidden_tests,
    }


def render_interface(item: dict) -> str:
    lines = [f"FUNCTION_BLOCK {item['id']}", "VAR_INPUT"]
    for field in item["inputs"]:
        lines.append(f"    {field['name']} : {field['type']};")
    lines.extend(["END_VAR", "VAR_OUTPUT"])
    for field in item["outputs"]:
        lines.append(f"    {field['name']} : {field['type']};")
    lines.extend(["END_VAR", "END_FUNCTION_BLOCK", ""])
    return "\n".join(lines)


def render_reference(item: dict) -> str:
    lines = [f"FUNCTION_BLOCK {item['id']}", "VAR_INPUT"]
    for field in item["inputs"]:
        lines.append(f"    {field['name']} : {field['type']};")
    lines.extend(["END_VAR", "VAR_OUTPUT"])
    for field in item["outputs"]:
        lines.append(f"    {field['name']} : {field['type']};")
    lines.append("END_VAR")
    if item["internal_vars"]:
        lines.append("VAR")
        lines.extend(f"    {declaration}" for declaration in item["internal_vars"])
        lines.append("END_VAR")
    lines.extend(["", item["body"], "", "END_FUNCTION_BLOCK", ""])
    return "\n".join(lines)


def render_requirements(item: dict) -> str:
    lines = [f"# {item['id']}: {item['title']}", "", "## Objective", ""]
    lines.append(
        f"Implement `{item['id']}` as an IEC-ST Core v1 function block in the "
        f"{item['category']} category. Preserve the supplied interface exactly."
    )
    lines.extend(["", "## Requirements", ""])
    for requirement in item["requirements"]:
        critical = " **[safety-critical]**" if requirement["safety_critical"] else ""
        lines.append(f"- **{requirement['id']}**{critical}: {requirement['text']}")
    lines.extend(["", "## Assumptions", ""])
    lines.extend(f"- {assumption}" for assumption in item["assumptions"])
    lines.extend(
        [
            "",
            "## Output constraint",
            "",
            "Return one complete function-block implementation without vendor-specific "
            "syntax, physical addresses, Markdown fences, or explanatory prose.",
            "",
        ]
    )
    return "\n".join(lines)


PLCV_EXPR_KEYWORDS = {"AND", "OR", "NOT", "XOR", "TRUE", "FALSE"}


def _top_level_invariant_bodies(expression: str) -> list[str]:
    """Return bodies from an exact ``G(a) [AND G(b) ...]`` expression.

    This is a syntactic decomposition, not an LTL-to-PLCverif translation.  It
    accepts only a conjunction of independently checkable invariants and rejects
    every other temporal shape.
    """
    bodies: list[str] = []
    cursor = 0
    length = len(expression)
    while True:
        while cursor < length and expression[cursor].isspace():
            cursor += 1
        if cursor >= length or expression[cursor] != "G":
            return []
        cursor += 1
        while cursor < length and expression[cursor].isspace():
            cursor += 1
        if cursor >= length or expression[cursor] != "(":
            return []
        start = cursor + 1
        depth = 1
        cursor += 1
        while cursor < length and depth:
            if expression[cursor] == "(":
                depth += 1
            elif expression[cursor] == ")":
                depth -= 1
            cursor += 1
        if depth != 0:
            return []
        body = expression[start:cursor - 1].strip()
        if not body:
            return []
        bodies.append(body)
        while cursor < length and expression[cursor].isspace():
            cursor += 1
        if cursor == length:
            return bodies
        separator = re.match(r"AND\b", expression[cursor:], re.IGNORECASE)
        if separator is None:
            return []
        cursor += separator.end()


def plcverif_native_cases(expression: str, item: dict) -> list[dict]:
    """Map the qualified invariant fragment to PLCverif built-in patterns.

    This does not translate arbitrary temporal DSL.  It deliberately accepts
    only end-of-cycle ``G(expr)`` invariants (or a top-level conjunction of such
    invariants) whose identifiers belong to the public, fixed interface and whose
    bodies have no temporal/helper function.  Every
    accepted case is sent to PLCverif's unmodified ``pattern-invariant`` plug-in;
    unsupported properties remain visible in the coverage report.
    """
    bodies = _top_level_invariant_bodies(expression)
    if not bodies:
        return []
    interface_names = {field["name"] for field in item["inputs"] + item["outputs"]}
    cases = []
    for body in bodies:
        if any(token in body for token in ("G(", "X(", "prev(", "rose(", "fell(", " U ")):
            continue
        called = {
            token.strip().upper()
            for token in re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\s*(?=\()", body)
        } - PLCV_EXPR_KEYWORDS
        if called:
            continue
        identifiers = {
            token
            for token in re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", body)
            if token.upper() not in PLCV_EXPR_KEYWORDS
        }
        if not identifiers <= interface_names:
            continue
        cases.append({
            "backend": "auto",
            "pattern_id": "pattern-invariant",
            "parameters": [body],
            "mapping": "direct end-of-cycle invariant",
        })
    return cases


def properties_for(item: dict) -> dict:
    properties = []
    for requirement in item["requirements"]:
        if requirement["property"]:
            property_record = {
                    "id": f"P{len(properties) + 1}",
                    "requirement_ids": [requirement["id"]],
                    "kind": "safety" if requirement["safety_critical"] else "functional",
                    "mandatory": True,
                    "expression": requirement["property"],
                    "source": "independently authored from the requirement contract",
                }
            native_cases = plcverif_native_cases(requirement["property"], item)
            if native_cases:
                invariant_bodies = _top_level_invariant_bodies(requirement["property"])
                complete = len(native_cases) == len(invariant_bodies)
                property_record["plcverif"] = {
                    "status": "required" if complete else "required_partial",
                    "cases": native_cases,
                    "coverage": "complete" if complete else "partial",
                }
            else:
                property_record["plcverif"] = {
                    "status": "not_expressible_in_qualified_invariant_profile",
                    "cases": [],
                }
            properties.append(property_record)
    native_properties = sum(bool(item["plcverif"]["cases"]) for item in properties)
    fully_native_properties = sum(item["plcverif"].get("coverage") == "complete" for item in properties)
    environment = item.get("plcverif_environment", PLCV_ENVIRONMENTS.get(item["id"], {
        "parameters": [],
        "assumption_invariants": [],
    }))
    return {
        "schema_version": "1.0",
        "semantics": "end-of-scan state sequence; initial state precedes scan 1",
        "notation": "IEC-ST-VerifyBench temporal DSL; see SCHEMA.md",
        "plcverif_profile": {
            "name": "native-pattern-invariant-v1",
            "policy": "every listed native case is mandatory; unsupported DSL is reported, never treated as verified",
            "native_property_count": native_properties,
            "fully_native_property_count": fully_native_properties,
            "total_property_count": len(properties),
            "environment": environment,
        },
        "properties": properties,
    }


def tests_for(item: dict, hidden: bool) -> dict:
    suite = item["hidden_tests"] if hidden else item["feedback_tests"]
    label = "hidden" if hidden else "feedback"
    cases = []
    for index, case in enumerate(suite, start=1):
        cases.append({"id": f"{label[0].upper()}T{index:02d}", **case})
    return {
        "schema_version": "1.0",
        "suite": label,
        "task_id": item["id"],
        "scan_period_ms": item["scan_period_ms"],
        "real_absolute_tolerance": item["real_tolerance"],
        "cases": cases,
    }


def negative_control(reference: str, item: dict) -> dict:
    """Create one deterministic seeded fault without claiming equivalence status."""
    variants: list[tuple[str, str, str]] = []

    # Mutate executable logic only.  Earlier versions searched the complete source,
    # so an integer in a function-block identifier (for example C08) could be
    # changed while the implementation remained semantically identical.  Such a
    # program merely calibrates the interface checker and is not a business-logic
    # negative control.
    last_var_end = reference.rfind("\nEND_VAR\n")
    if last_var_end < 0:
        raise ValueError(f"Could not locate the executable body for {item['id']}")
    body_start = last_var_end + len("\nEND_VAR\n")

    override = NEGATIVE_CONTROL_OVERRIDES.get(item["id"])
    if override is not None:
        marker = "\nEND_FUNCTION_BLOCK"
        mutated = reference.replace(
            marker,
            f"\n(* seeded fault: force {override['output']} *)\n"
            f"{override['output']} := {override['forced_value']};{marker}",
            1,
        )
        if mutated == reference:
            raise ValueError(f"Could not seed the qualified negative control for {item['id']}")
        return {
            "id": "NC1",
            "operator": "output_override",
            "description": f"Force output {override['output']} to {override['forced_value']}.",
            "target_requirement_ids": override["target_requirement_ids"],
            "expected_detection": ["dynamic_test"],
            "equivalence_status": "non_equivalent_by_witness",
            "validation_status": "not_run",
            "witness": {
                "suite": override["witness_suite"],
                "case": override["witness_case"],
            },
            "program": mutated,
        }

    def replace_body(pattern: str, replacement: str) -> tuple[str, int]:
        prefix, body = reference[:body_start], reference[body_start:]
        mutated_body, count = re.subn(pattern, replacement, body, count=1)
        return prefix + mutated_body, count

    def add(operator: str, description: str, mutated: str) -> None:
        if mutated != reference and all(existing[2] != mutated for existing in variants):
            variants.append((operator, description, mutated))

    replacements = [
        (r"\bTRUE\b", "FALSE", "boolean_literal_flip", "Flip the first TRUE literal."),
        (r"\bFALSE\b", "TRUE", "boolean_literal_flip", "Flip the first FALSE literal."),
        (r"\bAND\b", "OR", "boolean_operator", "Replace the first AND with OR."),
        (r"\bOR\b", "AND", "boolean_operator", "Replace the first OR with AND."),
        (r">=", ">", "boundary_operator", "Replace the first >= comparison with >."),
        (r"<=", "<", "boundary_operator", "Replace the first <= comparison with <."),
        (r"<>", "=", "comparison_operator", "Replace the first <> comparison with =."),
    ]
    for pattern, replacement, operator, description in replacements:
        if variants:
            break
        mutated, count = replace_body(pattern, replacement)
        if count:
            add(operator, description, mutated)

    # Fall back to a non-zero decimal integer outside TIME literals.
    body = reference[body_start:]
    match = re.search(r"(?<![#A-Za-z])([1-9][0-9]*)(?![A-Za-z])", body)
    if not variants and match:
        value = int(match.group(1))
        absolute_start = body_start + match.start(1)
        absolute_end = body_start + match.end(1)
        mutated = reference[:absolute_start] + str(value + 1) + reference[absolute_end:]
        add("constant_shift", f"Change the first integer constant {value} to {value + 1}.", mutated)

    # Final fallback: force an observable output to its default value.
    for output in item["outputs"]:
        if variants:
            break
        forced = {
            "BOOL": "FALSE",
            "INT": "0",
            "DINT": "0",
            "REAL": "0.0",
            "TIME": "T#0ms",
        }.get(output["type"])
        if forced is None:
            continue
        marker = "\nEND_FUNCTION_BLOCK"
        mutated = reference.replace(
            marker,
            f"\n(* seeded fault: force {output['name']} *)\n{output['name']} := {forced};{marker}",
            1,
        )
        add("output_override", f"Force output {output['name']} to {forced}.", mutated)

    if not variants:
        raise ValueError(f"Could not seed a negative control for {item['id']}")

    operator, description, program = variants[0]
    return {
        "id": "NC1",
        "operator": operator,
        "description": description,
        "target_requirement_ids": [item["requirements"][0]["id"]],
        "expected_detection": ["dynamic_test", "formal_property"],
        "equivalence_status": "unreviewed",
        "validation_status": "not_run",
        "program": program,
    }


def default_complexity(item: dict) -> dict:
    defaults = {
        "easy": {"retained_state": 0, "transitions": 0, "stateful_blocks": 0, "interactions": 0, "fault_modes": 0, "horizon_scans": 1},
        "medium": {"retained_state": 1, "transitions": 2, "stateful_blocks": 1, "interactions": 2, "fault_modes": 1, "horizon_scans": 5},
        "hard": {"retained_state": 3, "transitions": 5, "stateful_blocks": 2, "interactions": 4, "fault_modes": 2, "horizon_scans": 10},
    }[item["difficulty"]].copy()
    defaults.update(item["complexity"])
    defaults.update(
        {
            "inputs": len(item["inputs"]),
            "outputs": len(item["outputs"]),
            "requirements": len(item["requirements"]),
        }
    )
    return defaults


TASKS: list[dict] = []


def add(item: dict) -> None:
    TASKS.append(item)


# Task definitions are appended below by category.


# C01 -- Boolean and conditional logic -------------------------------------------------
add(
    task(
        "C01_E01_two_input_permissive",
        "Two-input run permissive",
        "C01",
        "easy",
        [var("Enable", "BOOL", "Operator enable request"), var("GuardClosed", "BOOL", "Safety guard status")],
        [var("RunPermit", "BOOL", "Permission to run")],
        [req("RunPermit shall be TRUE exactly when Enable and GuardClosed are both TRUE.", "G(RunPermit = (Enable AND GuardClosed))", True)],
        "RunPermit := Enable AND GuardClosed;",
        [test("nominal_permit", ["R1"], [step({"Enable": False, "GuardClosed": True}, {"RunPermit": False}), step({"Enable": True, "GuardClosed": True}, {"RunPermit": True})], "Exercise disabled and fully permitted states.")],
        [test("truth_table_boundaries", ["R1"], [step({"Enable": False, "GuardClosed": False}, {"RunPermit": False}), step({"Enable": True, "GuardClosed": False}, {"RunPermit": False})], "Cover the remaining Boolean combinations.")],
        iec_features=["FUNCTION_BLOCK", "BOOL", "AND", "assignment"],
    )
)

add(
    task(
        "C01_M01_two_out_of_three_vote",
        "Two-out-of-three sensor voter",
        "C01",
        "medium",
        [var("S1", "BOOL", "Sensor channel 1"), var("S2", "BOOL", "Sensor channel 2"), var("S3", "BOOL", "Sensor channel 3")],
        [var("Vote", "BOOL", "Majority-vote result"), var("Unanimous", "BOOL", "All channels agree")],
        [
            req("Vote shall be TRUE when at least two of S1, S2, and S3 are TRUE.", "G(Vote = ((S1 AND S2) OR (S1 AND S3) OR (S2 AND S3)))"),
            req("Unanimous shall be TRUE only when all three channels have the same value.", "G(Unanimous = ((S1 AND S2 AND S3) OR ((!S1) AND (!S2) AND (!S3))))"),
        ],
        """Vote := (S1 AND S2) OR (S1 AND S3) OR (S2 AND S3);
Unanimous := (S1 AND S2 AND S3) OR ((NOT S1) AND (NOT S2) AND (NOT S3));""",
        [test("majority_cases", ["R1"], [step({"S1": True, "S2": True, "S3": False}, {"Vote": True, "Unanimous": False}), step({"S1": True, "S2": False, "S3": False}, {"Vote": False, "Unanimous": False})], "One positive and one negative majority case.")],
        [test("unanimity_edges", ["R1", "R2"], [step({"S1": False, "S2": False, "S3": False}, {"Vote": False, "Unanimous": True}), step({"S1": True, "S2": True, "S3": True}, {"Vote": True, "Unanimous": True}), step({"S1": False, "S2": True, "S3": True}, {"Vote": True, "Unanimous": False})], "Check both unanimous values and a different majority permutation.")],
        iec_features=["FUNCTION_BLOCK", "BOOL", "AND", "OR", "NOT"],
        complexity={"retained_state": 0, "stateful_blocks": 0, "horizon_scans": 1},
    )
)

add(
    task(
        "C01_M02_mode_dependent_command",
        "Mode-dependent command selection",
        "C01",
        "medium",
        [var("AutoMode", "BOOL", "TRUE selects automatic mode"), var("AutoDemand", "BOOL", "Automatic request"), var("ManualDemand", "BOOL", "Manual request"), var("SafetyOK", "BOOL", "Common safety permission"), var("Inhibit", "BOOL", "High-priority inhibit")],
        [var("Command", "BOOL", "Selected command"), var("Blocked", "BOOL", "A request exists but is blocked")],
        [
            req("Command shall follow AutoDemand in automatic mode and ManualDemand in manual mode, but only when SafetyOK is TRUE and Inhibit is FALSE.", "G(Command = (((AutoMode AND AutoDemand) OR ((!AutoMode) AND ManualDemand)) AND SafetyOK AND (!Inhibit)))", True),
            req("Blocked shall be TRUE when the selected request is TRUE but safety is not OK or Inhibit is TRUE.", "G(Blocked = (((AutoMode AND AutoDemand) OR ((!AutoMode) AND ManualDemand)) AND ((!SafetyOK) OR Inhibit)))"),
        ],
        """Command := ((AutoMode AND AutoDemand) OR ((NOT AutoMode) AND ManualDemand))
           AND SafetyOK AND (NOT Inhibit);
Blocked := ((AutoMode AND AutoDemand) OR ((NOT AutoMode) AND ManualDemand))
           AND ((NOT SafetyOK) OR Inhibit);""",
        [test("mode_selection", ["R1"], [step({"AutoMode": True, "AutoDemand": True, "ManualDemand": False, "SafetyOK": True, "Inhibit": False}, {"Command": True, "Blocked": False}), step({"AutoMode": False, "AutoDemand": True, "ManualDemand": False, "SafetyOK": True, "Inhibit": False}, {"Command": False, "Blocked": False})], "Ensure only the selected mode request is honored.")],
        [test("blocking_priority", ["R1", "R2"], [step({"AutoMode": False, "AutoDemand": False, "ManualDemand": True, "SafetyOK": False, "Inhibit": False}, {"Command": False, "Blocked": True}), step({"AutoMode": True, "AutoDemand": True, "ManualDemand": True, "SafetyOK": True, "Inhibit": True}, {"Command": False, "Blocked": True})], "Exercise both safety and inhibit blocking.")],
        iec_features=["FUNCTION_BLOCK", "BOOL", "AND", "OR", "NOT"],
        complexity={"retained_state": 0, "stateful_blocks": 0, "interactions": 3, "horizon_scans": 1},
    )
)

add(
    task(
        "C01_H01_four_level_priority",
        "Four-level alarm priority encoder",
        "C01",
        "hard",
        [var("Info", "BOOL", "Information condition"), var("Warning", "BOOL", "Warning condition"), var("Trip", "BOOL", "Trip condition"), var("Emergency", "BOOL", "Emergency condition"), var("Suppress", "BOOL", "Suppress non-emergency indications")],
        [var("Active", "BOOL", "At least one reportable condition"), var("Level", "INT", "0 none, 1 info, 2 warning, 3 trip, 4 emergency")],
        [
            req("Emergency shall always produce Level 4 and Active TRUE, even when Suppress is TRUE.", "G(Emergency -> (Active AND (Level = 4)))", True),
            req("When not suppressed, the highest active condition shall determine Level.", "G((!Suppress AND !Emergency) -> (Level = max_priority(Info,Warning,Trip)))"),
            req("Suppress shall force Level 0 and Active FALSE when Emergency is FALSE.", "G((Suppress AND !Emergency) -> ((!Active) AND (Level = 0)))"),
            req("Level 0 shall be equivalent to Active FALSE.", "G((Level = 0) = (!Active))"),
        ],
        """IF Emergency THEN
    Level := 4;
    Active := TRUE;
ELSIF Suppress THEN
    Level := 0;
    Active := FALSE;
ELSIF Trip THEN
    Level := 3;
    Active := TRUE;
ELSIF Warning THEN
    Level := 2;
    Active := TRUE;
ELSIF Info THEN
    Level := 1;
    Active := TRUE;
ELSE
    Level := 0;
    Active := FALSE;
END_IF;""",
        [test("priority_order", ["R2", "R4"], [step({"Info": True, "Warning": True, "Trip": False, "Emergency": False, "Suppress": False}, {"Active": True, "Level": 2}), step({"Info": True, "Warning": True, "Trip": True, "Emergency": False, "Suppress": False}, {"Active": True, "Level": 3})], "Check highest-active-condition selection.")],
        [test("suppression_and_emergency", ["R1", "R3", "R4"], [step({"Info": True, "Warning": True, "Trip": True, "Emergency": False, "Suppress": True}, {"Active": False, "Level": 0}), step({"Info": False, "Warning": False, "Trip": False, "Emergency": True, "Suppress": True}, {"Active": True, "Level": 4}), step({"Info": False, "Warning": False, "Trip": False, "Emergency": False, "Suppress": False}, {"Active": False, "Level": 0})], "Verify emergency override, suppression, and idle state.")],
        iec_features=["FUNCTION_BLOCK", "BOOL", "INT", "IF", "ELSIF", "priority"],
        complexity={"retained_state": 0, "stateful_blocks": 0, "interactions": 5, "fault_modes": 1, "horizon_scans": 1},
    )
)

add(
    task(
        "C01_H02_redundant_channel_gate",
        "Redundant-channel safety gate",
        "C01",
        "hard",
        [var("ChA", "BOOL", "Safety channel A"), var("ChB", "BOOL", "Safety channel B"), var("TestMode", "BOOL", "Maintenance test mode"), var("TestPermit", "BOOL", "Independent test authorization"), var("ProcessRequest", "BOOL", "Process run request")],
        [var("SafeEnable", "BOOL", "Permitted process output"), var("Disagree", "BOOL", "Channel disagreement"), var("TestActive", "BOOL", "Authorized test-mode indication")],
        [
            req("Disagree shall be TRUE exactly when ChA and ChB differ.", "G(Disagree = (ChA <> ChB))", True),
            req("Normal SafeEnable requires ProcessRequest and both channels TRUE.", "G((!TestMode) -> (SafeEnable = (ProcessRequest AND ChA AND ChB)))", True),
            req("Test mode may bypass ChB only when TestPermit and ChA are TRUE.", "G(TestMode -> (SafeEnable = (ProcessRequest AND TestPermit AND ChA)))", True),
            req("TestActive shall indicate TestMode and TestPermit together.", "G(TestActive = (TestMode AND TestPermit))"),
        ],
        """Disagree := ChA <> ChB;
TestActive := TestMode AND TestPermit;
IF TestMode THEN
    SafeEnable := ProcessRequest AND TestPermit AND ChA;
ELSE
    SafeEnable := ProcessRequest AND ChA AND ChB;
END_IF;""",
        [test("normal_two_channel", ["R1", "R2"], [step({"ChA": True, "ChB": True, "TestMode": False, "TestPermit": False, "ProcessRequest": True}, {"SafeEnable": True, "Disagree": False, "TestActive": False}), step({"ChA": True, "ChB": False, "TestMode": False, "TestPermit": False, "ProcessRequest": True}, {"SafeEnable": False, "Disagree": True, "TestActive": False})], "Validate normal redundant operation.")],
        [test("authorized_and_unauthorized_test", ["R3", "R4"], [step({"ChA": True, "ChB": False, "TestMode": True, "TestPermit": False, "ProcessRequest": True}, {"SafeEnable": False, "Disagree": True, "TestActive": False}), step({"ChA": True, "ChB": False, "TestMode": True, "TestPermit": True, "ProcessRequest": True}, {"SafeEnable": True, "Disagree": True, "TestActive": True}), step({"ChA": False, "ChB": True, "TestMode": True, "TestPermit": True, "ProcessRequest": True}, {"SafeEnable": False, "Disagree": True, "TestActive": True})], "Exercise authorization and retained channel-A requirement.")],
        iec_features=["FUNCTION_BLOCK", "BOOL", "IF", "inequality", "priority"],
        complexity={"retained_state": 0, "stateful_blocks": 0, "interactions": 5, "fault_modes": 2, "horizon_scans": 1},
    )
)


# C02 -- Start/stop and retained state ------------------------------------------------
add(
    task(
        "C02_E01_basic_start_stop_latch",
        "Stop-priority start/stop latch",
        "C02",
        "easy",
        [var("Start", "BOOL", "Start command"), var("Stop", "BOOL", "Stop command")],
        [var("Running", "BOOL", "Latched running state")],
        [
            req("A Start command shall latch Running TRUE when Stop is FALSE.", "G((Start AND !Stop) -> X(Running))"),
            req("Stop shall force Running FALSE and shall have priority when Start and Stop are simultaneous.", "G(Stop -> (!Running))", True),
            req("Running shall retain its previous value when neither Start nor Stop is active.", "G((!Start AND !Stop) -> (Running = prev(Running)))"),
        ],
        """IF Stop THEN
    Running := FALSE;
ELSIF Start THEN
    Running := TRUE;
END_IF;""",
        [test("start_hold_stop", ["R1", "R2", "R3"], [step({"Start": False, "Stop": False}, {"Running": False}), step({"Start": True, "Stop": False}, {"Running": True}), step({"Start": False, "Stop": False}, {"Running": True}), step({"Start": False, "Stop": True}, {"Running": False})], "Start, retain, and stop the latch.")],
        [test("simultaneous_priority", ["R2"], [step({"Start": True, "Stop": True}, {"Running": False}), step({"Start": False, "Stop": False}, {"Running": False})], "Confirm stop priority and no automatic restart.")],
        internal_vars=[],
        iec_features=["FUNCTION_BLOCK", "BOOL", "retained output", "IF", "ELSIF"],
        complexity={"retained_state": 1, "transitions": 2, "stateful_blocks": 0, "horizon_scans": 3},
    )
)

add(
    task(
        "C02_M01_enabled_start_stop",
        "Enabled start/stop with forced shutdown",
        "C02",
        "medium",
        [var("Enable", "BOOL", "Controller enable"), var("Start", "BOOL", "Start command"), var("Stop", "BOOL", "Stop command")],
        [var("Running", "BOOL", "Latched running state"), var("Ready", "BOOL", "Controller can accept a start")],
        [
            req("Ready shall be TRUE when Enable is TRUE and Stop is FALSE.", "G(Ready = (Enable AND !Stop))"),
            req("Loss of Enable or assertion of Stop shall force Running FALSE.", "G((!Enable OR Stop) -> (!Running))", True),
            req("Start shall latch Running only while Ready is TRUE.", "G((Start AND Ready) -> Running)"),
            req("Re-enabling without a new Start shall not restart the controller.", "G(rose(Enable) AND !Start -> !Running)", True),
        ],
        """Ready := Enable AND (NOT Stop);
IF (NOT Enable) OR Stop THEN
    Running := FALSE;
ELSIF Start AND Ready THEN
    Running := TRUE;
END_IF;""",
        [test("enable_and_run", ["R1", "R2", "R3"], [step({"Enable": True, "Start": False, "Stop": False}, {"Running": False, "Ready": True}), step({"Enable": True, "Start": True, "Stop": False}, {"Running": True, "Ready": True}), step({"Enable": False, "Start": False, "Stop": False}, {"Running": False, "Ready": False})], "Run and force shutdown through Enable.")],
        [test("no_restart_after_enable", ["R4"], [step({"Enable": True, "Start": True, "Stop": False}, {"Running": True, "Ready": True}), step({"Enable": False, "Start": False, "Stop": False}, {"Running": False, "Ready": False}), step({"Enable": True, "Start": False, "Stop": False}, {"Running": False, "Ready": True})], "Re-enable without a fresh start.")],
        iec_features=["FUNCTION_BLOCK", "BOOL", "retained output", "IF", "ELSIF", "priority"],
        complexity={"retained_state": 1, "transitions": 3, "interactions": 2, "horizon_scans": 4},
    )
)

add(
    task(
        "C02_M02_local_remote_latch",
        "Local/remote command latch",
        "C02",
        "medium",
        [var("RemoteMode", "BOOL", "TRUE selects remote controls"), var("LocalStart", "BOOL", "Local start command"), var("RemoteStart", "BOOL", "Remote start command"), var("Stop", "BOOL", "Common stop"), var("Permit", "BOOL", "Run permission")],
        [var("Running", "BOOL", "Latched running state"), var("SelectedStart", "BOOL", "Start selected by the current mode")],
        [
            req("SelectedStart shall use RemoteStart in remote mode and LocalStart in local mode.", "G(SelectedStart = ((RemoteMode AND RemoteStart) OR ((!RemoteMode) AND LocalStart)))"),
            req("Stop or loss of Permit shall force Running FALSE.", "G((Stop OR !Permit) -> !Running)", True),
            req("The selected start shall latch Running only while Permit is TRUE and Stop is FALSE.", "G((SelectedStart AND Permit AND !Stop) -> Running)"),
            req("A start from the non-selected mode shall have no effect.", "G((RemoteMode AND LocalStart AND !RemoteStart) -> !rose(Running))"),
        ],
        """SelectedStart := (RemoteMode AND RemoteStart) OR ((NOT RemoteMode) AND LocalStart);
IF Stop OR (NOT Permit) THEN
    Running := FALSE;
ELSIF SelectedStart THEN
    Running := TRUE;
END_IF;""",
        [test("selected_modes", ["R1", "R3"], [step({"RemoteMode": False, "LocalStart": True, "RemoteStart": False, "Stop": False, "Permit": True}, {"Running": True, "SelectedStart": True}), step({"RemoteMode": False, "LocalStart": False, "RemoteStart": True, "Stop": True, "Permit": True}, {"Running": False, "SelectedStart": False})], "Use local start and then stop while a non-selected request is present.")],
        [test("remote_and_permit", ["R2", "R4"], [step({"RemoteMode": True, "LocalStart": True, "RemoteStart": False, "Stop": False, "Permit": True}, {"Running": False, "SelectedStart": False}), step({"RemoteMode": True, "LocalStart": False, "RemoteStart": True, "Stop": False, "Permit": True}, {"Running": True, "SelectedStart": True}), step({"RemoteMode": True, "LocalStart": False, "RemoteStart": False, "Stop": False, "Permit": False}, {"Running": False, "SelectedStart": False})], "Reject non-selected start, accept remote, and trip on permit loss.")],
        iec_features=["FUNCTION_BLOCK", "BOOL", "retained output", "mode selection", "priority"],
        complexity={"retained_state": 1, "transitions": 3, "interactions": 3, "horizon_scans": 4},
    )
)

add(
    task(
        "C02_H01_fault_lockout_reset",
        "Fault lockout with qualified manual reset",
        "C02",
        "hard",
        [var("Start", "BOOL", "Start command"), var("Stop", "BOOL", "Stop command"), var("Fault", "BOOL", "Active equipment fault"), var("Reset", "BOOL", "Manual reset"), var("Permit", "BOOL", "External run permission")],
        [var("Running", "BOOL", "Running state"), var("LockedOut", "BOOL", "Latched fault lockout")],
        [
            req("Fault shall immediately stop Running and latch LockedOut TRUE.", "G(Fault -> ((!Running) AND LockedOut))", True),
            req("Reset shall clear LockedOut only when Fault is FALSE and Start is FALSE.", "G((Reset AND !Fault AND !Start) -> !LockedOut)"),
            req("Start shall not run the equipment while LockedOut, Stop, or loss of Permit is active.", "G((LockedOut OR Stop OR !Permit) -> !Running)", True),
            req("Clearing the lockout shall not automatically restart the equipment.", "G(fell(LockedOut) -> !Running)", True),
            req("A new Start after a successful reset may latch Running TRUE.", "G((Start AND !LockedOut AND Permit AND !Stop) -> Running)"),
        ],
        """IF Fault THEN
    LockedOut := TRUE;
    Running := FALSE;
ELSIF Reset AND (NOT Start) THEN
    LockedOut := FALSE;
END_IF;

IF LockedOut OR Stop OR (NOT Permit) THEN
    Running := FALSE;
ELSIF Start THEN
    Running := TRUE;
END_IF;""",
        [test("fault_latches", ["R1", "R3"], [step({"Start": True, "Stop": False, "Fault": False, "Reset": False, "Permit": True}, {"Running": True, "LockedOut": False}), step({"Start": False, "Stop": False, "Fault": True, "Reset": False, "Permit": True}, {"Running": False, "LockedOut": True}), step({"Start": True, "Stop": False, "Fault": False, "Reset": False, "Permit": True}, {"Running": False, "LockedOut": True})], "Trip, latch, and reject start while locked out.")],
        [test("qualified_reset_and_restart", ["R2", "R4", "R5"], [step({"Start": False, "Stop": False, "Fault": True, "Reset": False, "Permit": True}, {"Running": False, "LockedOut": True}), step({"Start": True, "Stop": False, "Fault": False, "Reset": True, "Permit": True}, {"Running": False, "LockedOut": True}), step({"Start": False, "Stop": False, "Fault": False, "Reset": True, "Permit": True}, {"Running": False, "LockedOut": False}), step({"Start": False, "Stop": False, "Fault": False, "Reset": False, "Permit": True}, {"Running": False, "LockedOut": False}), step({"Start": True, "Stop": False, "Fault": False, "Reset": False, "Permit": True}, {"Running": True, "LockedOut": False})], "Reject reset with Start held, then reset and require a new start.")],
        iec_features=["FUNCTION_BLOCK", "BOOL", "retained outputs", "IF", "priority", "fault recovery"],
        complexity={"retained_state": 2, "transitions": 5, "interactions": 5, "fault_modes": 2, "horizon_scans": 6},
    )
)

add(
    task(
        "C02_H02_safe_restart_inhibit",
        "Safe restart after power or safety interruption",
        "C02",
        "hard",
        [var("PowerOK", "BOOL", "Control power available"), var("SafetyOK", "BOOL", "Safety chain healthy"), var("Start", "BOOL", "Start push button"), var("Stop", "BOOL", "Stop push button"), var("Reset", "BOOL", "Restart-inhibit reset")],
        [var("Running", "BOOL", "Machine running"), var("RestartInhibit", "BOOL", "A fresh reset is required")],
        [
            req("Loss of PowerOK or SafetyOK shall stop Running and set RestartInhibit.", "G((!PowerOK OR !SafetyOK) -> ((!Running) AND RestartInhibit))", True),
            req("Stop shall stop Running without by itself setting RestartInhibit.", "G(Stop -> !Running)", True),
            req("Reset may clear RestartInhibit only when PowerOK and SafetyOK are TRUE and Start is FALSE.", "G((prev(RestartInhibit) AND !RestartInhibit) -> (Reset AND PowerOK AND SafetyOK AND !Start))"),
            req("Running shall remain FALSE while RestartInhibit is TRUE.", "G(RestartInhibit -> !Running)", True),
            req("After reset, a new Start may run the machine when PowerOK, SafetyOK, and not Stop hold.", "G((Start AND !RestartInhibit AND PowerOK AND SafetyOK AND !Stop) -> Running)"),
        ],
        """IF (NOT PowerOK) OR (NOT SafetyOK) THEN
    Running := FALSE;
    RestartInhibit := TRUE;
ELSIF Stop THEN
    Running := FALSE;
ELSIF Reset AND (NOT Start) THEN
    RestartInhibit := FALSE;
ELSIF Start AND (NOT RestartInhibit) THEN
    Running := TRUE;
END_IF;

IF RestartInhibit THEN
    Running := FALSE;
END_IF;""",
        [test("safety_interruption", ["R1", "R4"], [step({"PowerOK": True, "SafetyOK": True, "Start": True, "Stop": False, "Reset": False}, {"Running": True, "RestartInhibit": False}), step({"PowerOK": True, "SafetyOK": False, "Start": False, "Stop": False, "Reset": False}, {"Running": False, "RestartInhibit": True}), step({"PowerOK": True, "SafetyOK": True, "Start": True, "Stop": False, "Reset": False}, {"Running": False, "RestartInhibit": True})], "A safety interruption creates a lockout that blocks held Start.")],
        [test("qualified_reset", ["R2", "R3", "R5"], [step({"PowerOK": False, "SafetyOK": True, "Start": False, "Stop": False, "Reset": False}, {"Running": False, "RestartInhibit": True}), step({"PowerOK": True, "SafetyOK": True, "Start": True, "Stop": False, "Reset": True}, {"Running": False, "RestartInhibit": True}), step({"PowerOK": True, "SafetyOK": True, "Start": False, "Stop": False, "Reset": True}, {"Running": False, "RestartInhibit": False}), step({"PowerOK": True, "SafetyOK": True, "Start": True, "Stop": False, "Reset": False}, {"Running": True, "RestartInhibit": False}), step({"PowerOK": True, "SafetyOK": True, "Start": False, "Stop": True, "Reset": False}, {"Running": False, "RestartInhibit": False})], "Require released Start for reset, restart deliberately, and stop normally.")],
        iec_features=["FUNCTION_BLOCK", "BOOL", "retained outputs", "IF", "ELSIF", "safe restart"],
        complexity={"retained_state": 2, "transitions": 6, "interactions": 6, "fault_modes": 2, "horizon_scans": 7},
    )
)


# C03 -- Interlocks and safe outputs --------------------------------------------------
add(
    task(
        "C03_E01_forward_reverse_interlock",
        "Forward/reverse motor interlock",
        "C03",
        "easy",
        [var("ForwardRequest", "BOOL", "Forward request"), var("ReverseRequest", "BOOL", "Reverse request"), var("Permit", "BOOL", "Common safety permit")],
        [var("Forward", "BOOL", "Forward contactor command"), var("Reverse", "BOOL", "Reverse contactor command")],
        [
            req("Forward shall be TRUE only for an exclusive forward request with Permit TRUE.", "G(Forward = (Permit AND ForwardRequest AND !ReverseRequest))", True),
            req("Reverse shall be TRUE only for an exclusive reverse request with Permit TRUE.", "G(Reverse = (Permit AND ReverseRequest AND !ForwardRequest))", True),
            req("Forward and Reverse shall never be TRUE together.", "G(!(Forward AND Reverse))", True),
        ],
        """Forward := Permit AND ForwardRequest AND (NOT ReverseRequest);
Reverse := Permit AND ReverseRequest AND (NOT ForwardRequest);""",
        [test("exclusive_commands", ["R1", "R2"], [step({"ForwardRequest": True, "ReverseRequest": False, "Permit": True}, {"Forward": True, "Reverse": False}), step({"ForwardRequest": False, "ReverseRequest": True, "Permit": True}, {"Forward": False, "Reverse": True})], "Exercise each exclusive direction.")],
        [test("conflict_and_permit", ["R1", "R2", "R3"], [step({"ForwardRequest": True, "ReverseRequest": True, "Permit": True}, {"Forward": False, "Reverse": False}), step({"ForwardRequest": True, "ReverseRequest": False, "Permit": False}, {"Forward": False, "Reverse": False})], "Reject conflicting commands and lost permission.")],
        iec_features=["FUNCTION_BLOCK", "BOOL", "AND", "NOT", "interlock"],
    )
)

add(
    task(
        "C03_M01_pump_valve_interlock",
        "Pump and discharge-valve interlock",
        "C03",
        "medium",
        [var("RunRequest", "BOOL", "Process run request"), var("TankLevelOK", "BOOL", "Suction tank level permissive"), var("ValveFeedbackOpen", "BOOL", "Discharge valve open feedback"), var("PumpFeedback", "BOOL", "Pump running feedback"), var("Stop", "BOOL", "Stop command")],
        [var("ValveCommand", "BOOL", "Discharge valve command"), var("PumpCommand", "BOOL", "Pump command"), var("InterlockAlarm", "BOOL", "Unsafe feedback combination")],
        [
            req("ValveCommand shall follow a valid RunRequest while TankLevelOK and not Stop hold.", "G(ValveCommand = (RunRequest AND TankLevelOK AND !Stop))"),
            req("PumpCommand requires ValveFeedbackOpen in addition to the valve-command permissives.", "G(PumpCommand -> ValveFeedbackOpen)", True),
            req("PumpCommand shall be FALSE when Stop or loss of TankLevelOK is active.", "G((Stop OR !TankLevelOK) -> !PumpCommand)", True),
            req("InterlockAlarm shall be TRUE when PumpFeedback is TRUE while valve feedback is closed.", "G(InterlockAlarm = (PumpFeedback AND !ValveFeedbackOpen))", True),
        ],
        """ValveCommand := RunRequest AND TankLevelOK AND (NOT Stop);
PumpCommand := ValveCommand AND ValveFeedbackOpen;
InterlockAlarm := PumpFeedback AND (NOT ValveFeedbackOpen);""",
        [test("start_sequence_permissions", ["R1", "R2"], [step({"RunRequest": True, "TankLevelOK": True, "ValveFeedbackOpen": False, "PumpFeedback": False, "Stop": False}, {"ValveCommand": True, "PumpCommand": False, "InterlockAlarm": False}), step({"RunRequest": True, "TankLevelOK": True, "ValveFeedbackOpen": True, "PumpFeedback": False, "Stop": False}, {"ValveCommand": True, "PumpCommand": True, "InterlockAlarm": False})], "Valve command precedes pump permission.")],
        [test("unsafe_feedback_and_stop", ["R3", "R4"], [step({"RunRequest": True, "TankLevelOK": True, "ValveFeedbackOpen": False, "PumpFeedback": True, "Stop": False}, {"ValveCommand": True, "PumpCommand": False, "InterlockAlarm": True}), step({"RunRequest": True, "TankLevelOK": True, "ValveFeedbackOpen": True, "PumpFeedback": True, "Stop": True}, {"ValveCommand": False, "PumpCommand": False, "InterlockAlarm": False})], "Detect unsafe feedback and honor stop.")],
        iec_features=["FUNCTION_BLOCK", "BOOL", "interlock", "feedback monitoring"],
        complexity={"retained_state": 0, "stateful_blocks": 0, "interactions": 3, "fault_modes": 1, "horizon_scans": 2},
    )
)

add(
    task(
        "C03_M02_heating_cooling_deadband",
        "Mutually exclusive heating and cooling with deadband",
        "C03",
        "medium",
        [var("Temperature", "REAL", "Measured temperature"), var("Setpoint", "REAL", "Target temperature"), var("Enable", "BOOL", "Controller enable"), var("SafetyTrip", "BOOL", "Common safety trip")],
        [var("Heat", "BOOL", "Heating output"), var("Cool", "BOOL", "Cooling output")],
        [
            req("Heat shall turn on below Setpoint minus 1.0 while enabled and safe.", "G((Enable AND !SafetyTrip AND Temperature < Setpoint-1.0) -> Heat)"),
            req("Cool shall turn on above Setpoint plus 1.0 while enabled and safe.", "G((Enable AND !SafetyTrip AND Temperature > Setpoint+1.0) -> Cool)"),
            req("Neither output shall be active inside the inclusive deadband.", "G((Temperature >= Setpoint-1.0 AND Temperature <= Setpoint+1.0) -> (!Heat AND !Cool))"),
            req("Heat and Cool shall never be active together, and SafetyTrip shall turn both off.", "G((!(Heat AND Cool)) AND (SafetyTrip -> (!Heat AND !Cool)))", True),
        ],
        """Heat := FALSE;
Cool := FALSE;
IF Enable AND (NOT SafetyTrip) THEN
    IF Temperature < (Setpoint - 1.0) THEN
        Heat := TRUE;
    ELSIF Temperature > (Setpoint + 1.0) THEN
        Cool := TRUE;
    END_IF;
END_IF;""",
        [test("deadband_edges", ["R1", "R2", "R3"], [step({"Temperature": 18.9, "Setpoint": 20.0, "Enable": True, "SafetyTrip": False}, {"Heat": True, "Cool": False}), step({"Temperature": 20.0, "Setpoint": 20.0, "Enable": True, "SafetyTrip": False}, {"Heat": False, "Cool": False}), step({"Temperature": 21.1, "Setpoint": 20.0, "Enable": True, "SafetyTrip": False}, {"Heat": False, "Cool": True})], "Exercise both sides and center of the deadband.")],
        [test("inclusive_boundaries_and_trip", ["R3", "R4"], [step({"Temperature": 19.0, "Setpoint": 20.0, "Enable": True, "SafetyTrip": False}, {"Heat": False, "Cool": False}), step({"Temperature": 21.0, "Setpoint": 20.0, "Enable": True, "SafetyTrip": False}, {"Heat": False, "Cool": False}), step({"Temperature": 10.0, "Setpoint": 20.0, "Enable": True, "SafetyTrip": True}, {"Heat": False, "Cool": False})], "Check inclusive boundary semantics and safety trip.")],
        iec_features=["FUNCTION_BLOCK", "BOOL", "REAL", "IF", "ELSIF", "comparison", "interlock"],
        complexity={"retained_state": 0, "stateful_blocks": 0, "interactions": 3, "fault_modes": 1, "horizon_scans": 1},
    )
)

add(
    task(
        "C03_H01_conveyor_cascade_interlock",
        "Three-conveyor downstream interlock",
        "C03",
        "hard",
        [var("RunRequest", "BOOL", "Line run request"), var("Stop", "BOOL", "Common stop"), var("C1Clear", "BOOL", "Conveyor 1 clear"), var("C2Clear", "BOOL", "Conveyor 2 clear"), var("C3Clear", "BOOL", "Conveyor 3 clear"), var("C2Available", "BOOL", "Conveyor 2 available"), var("C3Available", "BOOL", "Conveyor 3 available")],
        [var("C1Run", "BOOL", "Upstream conveyor command"), var("C2Run", "BOOL", "Middle conveyor command"), var("C3Run", "BOOL", "Downstream conveyor command"), var("Blocked", "BOOL", "Run request blocked by availability or occupancy")],
        [
            req("C3Run shall require RunRequest, C3Available, C3Clear, and not Stop.", "G(C3Run = (RunRequest AND C3Available AND C3Clear AND !Stop))", True),
            req("C2Run shall require C3Run, C2Available, and C2Clear.", "G(C2Run -> (C3Run AND C2Available AND C2Clear))", True),
            req("C1Run shall require C2Run and C1Clear.", "G(C1Run -> (C2Run AND C1Clear))", True),
            req("Stop shall turn all three commands off.", "G(Stop -> (!C1Run AND !C2Run AND !C3Run))", True),
            req("Blocked shall indicate RunRequest with at least one unavailable or uncleared stage.", "G(Blocked = (RunRequest AND (!C1Clear OR !C2Clear OR !C3Clear OR !C2Available OR !C3Available)))"),
        ],
        """C3Run := RunRequest AND C3Available AND C3Clear AND (NOT Stop);
C2Run := C3Run AND C2Available AND C2Clear;
C1Run := C2Run AND C1Clear;
Blocked := RunRequest AND ((NOT C1Clear) OR (NOT C2Clear) OR (NOT C3Clear)
           OR (NOT C2Available) OR (NOT C3Available));""",
        [test("healthy_cascade", ["R1", "R2", "R3"], [step({"RunRequest": True, "Stop": False, "C1Clear": True, "C2Clear": True, "C3Clear": True, "C2Available": True, "C3Available": True}, {"C1Run": True, "C2Run": True, "C3Run": True, "Blocked": False})], "All downstream permissions allow the entire cascade.")],
        [test("downstream_failures", ["R2", "R3", "R4", "R5"], [step({"RunRequest": True, "Stop": False, "C1Clear": True, "C2Clear": True, "C3Clear": True, "C2Available": True, "C3Available": False}, {"C1Run": False, "C2Run": False, "C3Run": False, "Blocked": True}), step({"RunRequest": True, "Stop": False, "C1Clear": True, "C2Clear": False, "C3Clear": True, "C2Available": True, "C3Available": True}, {"C1Run": False, "C2Run": False, "C3Run": True, "Blocked": True}), step({"RunRequest": True, "Stop": True, "C1Clear": True, "C2Clear": True, "C3Clear": True, "C2Available": True, "C3Available": True}, {"C1Run": False, "C2Run": False, "C3Run": False, "Blocked": False})], "Propagate downstream restrictions and enforce stop.")],
        iec_features=["FUNCTION_BLOCK", "BOOL", "cascaded interlocks", "priority"],
        complexity={"retained_state": 0, "stateful_blocks": 0, "interactions": 6, "fault_modes": 3, "horizon_scans": 1},
    )
)

add(
    task(
        "C03_H02_safety_zone_arbitration",
        "Safety-zone actuator arbitration",
        "C03",
        "hard",
        [var("RobotRequest", "BOOL", "Robot requests the shared zone"), var("ConveyorRequest", "BOOL", "Conveyor requests the shared zone"), var("ManualRequest", "BOOL", "Manual maintenance request"), var("GuardClosed", "BOOL", "Guard status"), var("EStopOK", "BOOL", "Emergency-stop chain healthy"), var("ManualKey", "BOOL", "Manual mode authorization")],
        [var("RobotEnable", "BOOL", "Robot zone grant"), var("ConveyorEnable", "BOOL", "Conveyor zone grant"), var("ManualEnable", "BOOL", "Manual zone grant"), var("Conflict", "BOOL", "More than one eligible request")],
        [
            req("Loss of GuardClosed or EStopOK shall disable all grants.", "G((!GuardClosed OR !EStopOK) -> (!RobotEnable AND !ConveyorEnable AND !ManualEnable))", True),
            req("Authorized ManualRequest has highest priority.", "G((ManualRequest AND ManualKey AND GuardClosed AND EStopOK) -> ManualEnable)", True),
            req("RobotRequest has priority over ConveyorRequest when manual mode is not granted.", "G((RobotRequest AND !ManualEnable AND GuardClosed AND EStopOK) -> RobotEnable)"),
            req("At most one grant shall be TRUE.", "G(at_most_one(RobotEnable,ConveyorEnable,ManualEnable))", True),
            req("Conflict shall indicate more than one eligible request before arbitration.", "G(Conflict = more_than_one(RobotRequest,ConveyorRequest,(ManualRequest AND ManualKey)))"),
        ],
        """RobotEnable := FALSE;
ConveyorEnable := FALSE;
ManualEnable := FALSE;
Conflict := (RobotRequest AND ConveyorRequest)
            OR (RobotRequest AND ManualRequest AND ManualKey)
            OR (ConveyorRequest AND ManualRequest AND ManualKey);

IF GuardClosed AND EStopOK THEN
    IF ManualRequest AND ManualKey THEN
        ManualEnable := TRUE;
    ELSIF RobotRequest THEN
        RobotEnable := TRUE;
    ELSIF ConveyorRequest THEN
        ConveyorEnable := TRUE;
    END_IF;
END_IF;""",
        [test("priority_chain", ["R2", "R3", "R4"], [step({"RobotRequest": True, "ConveyorRequest": True, "ManualRequest": False, "GuardClosed": True, "EStopOK": True, "ManualKey": False}, {"RobotEnable": True, "ConveyorEnable": False, "ManualEnable": False, "Conflict": True}), step({"RobotRequest": True, "ConveyorRequest": True, "ManualRequest": True, "GuardClosed": True, "EStopOK": True, "ManualKey": True}, {"RobotEnable": False, "ConveyorEnable": False, "ManualEnable": True, "Conflict": True})], "Exercise robot-over-conveyor and manual-over-all priorities.")],
        [test("safety_and_unauthorized_manual", ["R1", "R2", "R5"], [step({"RobotRequest": False, "ConveyorRequest": False, "ManualRequest": True, "GuardClosed": True, "EStopOK": True, "ManualKey": False}, {"RobotEnable": False, "ConveyorEnable": False, "ManualEnable": False, "Conflict": False}), step({"RobotRequest": True, "ConveyorRequest": False, "ManualRequest": False, "GuardClosed": False, "EStopOK": True, "ManualKey": False}, {"RobotEnable": False, "ConveyorEnable": False, "ManualEnable": False, "Conflict": False})], "Reject unauthorized manual operation and enforce guard safety.")],
        iec_features=["FUNCTION_BLOCK", "BOOL", "IF", "ELSIF", "arbitration", "safety interlock"],
        complexity={"retained_state": 0, "stateful_blocks": 0, "interactions": 7, "fault_modes": 3, "horizon_scans": 1},
    )
)


# C04 -- Edge and event handling ------------------------------------------------------
add(
    task(
        "C04_E01_rising_edge_pulse",
        "Single-scan rising-edge pulse",
        "C04",
        "easy",
        [var("Signal", "BOOL", "Observed signal")],
        [var("Pulse", "BOOL", "TRUE for one scan on a rising edge")],
        [
            req("Pulse shall be TRUE for the scan in which Signal changes from FALSE to TRUE.", "G(Pulse = rose(Signal))"),
            req("Pulse shall be FALSE while Signal remains TRUE or remains FALSE.", "G(!rose(Signal) -> !Pulse)"),
        ],
        """Pulse := Signal AND (NOT PrevSignal);
PrevSignal := Signal;""",
        [test("first_rising_edge", ["R1", "R2"], [step({"Signal": False}, {"Pulse": False}), step({"Signal": True}, {"Pulse": True}), step({"Signal": True}, {"Pulse": False})], "Generate one pulse for a rising transition.")],
        [test("second_edge_after_low", ["R1", "R2"], [step({"Signal": True}, {"Pulse": True}), step({"Signal": True}, {"Pulse": False}), step({"Signal": False}, {"Pulse": False}), step({"Signal": True}, {"Pulse": True})], "A new edge is possible only after returning low.")],
        internal_vars=["PrevSignal : BOOL := FALSE;"],
        iec_features=["FUNCTION_BLOCK", "BOOL", "retained state", "edge detection"],
        complexity={"retained_state": 1, "transitions": 2, "stateful_blocks": 1, "horizon_scans": 3},
    )
)

add(
    task(
        "C04_M01_falling_edge_pulse",
        "Armed falling-edge pulse",
        "C04",
        "medium",
        [var("Signal", "BOOL", "Observed signal"), var("Arm", "BOOL", "Enable edge reporting")],
        [var("Pulse", "BOOL", "One-scan falling-edge pulse"), var("Armed", "BOOL", "Current armed status")],
        [
            req("Armed shall equal Arm at the end of each scan.", "G(Armed = Arm)"),
            req("Pulse shall occur on a TRUE-to-FALSE Signal transition only when Arm is TRUE.", "G(Pulse = (Arm AND fell(Signal)))"),
            req("Disarming shall suppress Pulse without corrupting future edge detection.", "G(!Arm -> !Pulse)"),
        ],
        """Pulse := Arm AND (NOT Signal) AND PrevSignal;
Armed := Arm;
PrevSignal := Signal;""",
        [test("armed_falling", ["R1", "R2"], [step({"Signal": True, "Arm": True}, {"Pulse": False, "Armed": True}), step({"Signal": False, "Arm": True}, {"Pulse": True, "Armed": True}), step({"Signal": False, "Arm": True}, {"Pulse": False, "Armed": True})], "Detect one armed falling edge.")],
        [test("disarmed_then_rearmed", ["R2", "R3"], [step({"Signal": True, "Arm": False}, {"Pulse": False, "Armed": False}), step({"Signal": False, "Arm": False}, {"Pulse": False, "Armed": False}), step({"Signal": True, "Arm": True}, {"Pulse": False, "Armed": True}), step({"Signal": False, "Arm": True}, {"Pulse": True, "Armed": True})], "Suppress an edge while disarmed and detect the next armed edge.")],
        internal_vars=["PrevSignal : BOOL := FALSE;"],
        iec_features=["FUNCTION_BLOCK", "BOOL", "retained state", "falling edge"],
        complexity={"retained_state": 1, "transitions": 3, "stateful_blocks": 1, "interactions": 1, "horizon_scans": 4},
    )
)

add(
    task(
        "C04_M02_toggle_on_edge",
        "Toggle output on qualified rising edge",
        "C04",
        "medium",
        [var("Button", "BOOL", "Momentary button"), var("Enable", "BOOL", "Toggle permission"), var("Reset", "BOOL", "Synchronous reset")],
        [var("State", "BOOL", "Toggled state"), var("AcceptedPulse", "BOOL", "Qualified edge accepted this scan")],
        [
            req("Reset shall clear State and suppress AcceptedPulse with highest priority.", "G(Reset -> (!State AND !AcceptedPulse))", True),
            req("A rising Button edge while Enable is TRUE shall invert State exactly once.", "G(AcceptedPulse = (Enable AND rose(Button) AND !Reset))"),
            req("Holding Button TRUE shall not repeatedly toggle State.", "G((Button AND prev(Button) AND !Reset) -> (State = prev(State)))"),
        ],
        """AcceptedPulse := FALSE;
IF Reset THEN
    State := FALSE;
ELSIF Enable AND Button AND (NOT PrevButton) THEN
    State := NOT State;
    AcceptedPulse := TRUE;
END_IF;
PrevButton := Button;""",
        [test("toggle_once", ["R2", "R3"], [step({"Button": False, "Enable": True, "Reset": False}, {"State": False, "AcceptedPulse": False}), step({"Button": True, "Enable": True, "Reset": False}, {"State": True, "AcceptedPulse": True}), step({"Button": True, "Enable": True, "Reset": False}, {"State": True, "AcceptedPulse": False})], "Toggle only on the rising edge.")],
        [test("second_toggle_and_reset", ["R1", "R2"], [step({"Button": True, "Enable": True, "Reset": False}, {"State": True, "AcceptedPulse": True}), step({"Button": False, "Enable": True, "Reset": False}, {"State": True, "AcceptedPulse": False}), step({"Button": True, "Enable": True, "Reset": False}, {"State": False, "AcceptedPulse": True}), step({"Button": True, "Enable": True, "Reset": True}, {"State": False, "AcceptedPulse": False})], "Toggle a second time and apply reset while held.")],
        internal_vars=["PrevButton : BOOL := FALSE;"],
        iec_features=["FUNCTION_BLOCK", "BOOL", "retained output", "edge detection", "priority"],
        complexity={"retained_state": 2, "transitions": 3, "stateful_blocks": 1, "interactions": 2, "horizon_scans": 5},
    )
)

add(
    task(
        "C04_H01_qualified_event_counter",
        "Qualified event capture with saturation",
        "C04",
        "hard",
        [var("Event", "BOOL", "Event input"), var("Qualify", "BOOL", "Event qualification"), var("Reset", "BOOL", "Reset count"), var("MaxCount", "INT", "Saturation limit, assumed at least one")],
        [var("Count", "INT", "Accepted event count"), var("AcceptedPulse", "BOOL", "Accepted event this scan"), var("AtLimit", "BOOL", "Count has reached MaxCount")],
        [
            req("Reset shall clear Count and AcceptedPulse.", "G(Reset -> ((Count = 0) AND !AcceptedPulse))"),
            req("Only a rising Event edge with Qualify TRUE and Count below MaxCount shall increment Count.", "G(AcceptedPulse = (rose(Event) AND Qualify AND (prev(Count) < MaxCount) AND !Reset))"),
            req("Count shall not exceed MaxCount.", "G(Count <= MaxCount)", True),
            req("AtLimit shall be TRUE exactly when Count is at least MaxCount.", "G(AtLimit = (Count >= MaxCount))"),
        ],
        """AcceptedPulse := FALSE;
IF Reset THEN
    Count := 0;
ELSIF Event AND (NOT PrevEvent) AND Qualify AND (Count < MaxCount) THEN
    Count := Count + 1;
    AcceptedPulse := TRUE;
END_IF;
AtLimit := Count >= MaxCount;
PrevEvent := Event;""",
        [test("qualified_edges", ["R1", "R2"], [step({"Event": False, "Qualify": True, "Reset": False, "MaxCount": 2}, {"Count": 0, "AcceptedPulse": False, "AtLimit": False}), step({"Event": True, "Qualify": True, "Reset": False, "MaxCount": 2}, {"Count": 1, "AcceptedPulse": True, "AtLimit": False}), step({"Event": True, "Qualify": True, "Reset": False, "MaxCount": 2}, {"Count": 1, "AcceptedPulse": False, "AtLimit": False}), step({"Event": False, "Qualify": True, "Reset": False, "MaxCount": 2}, {"Count": 1, "AcceptedPulse": False, "AtLimit": False})], "Count a qualified edge once.")],
        [test("saturation_and_reset", ["R1", "R3", "R4"], [step({"Event": True, "Qualify": False, "Reset": False, "MaxCount": 2}, {"Count": 0, "AcceptedPulse": False, "AtLimit": False}), step({"Event": False, "Qualify": True, "Reset": False, "MaxCount": 2}, {"Count": 0, "AcceptedPulse": False, "AtLimit": False}), step({"Event": True, "Qualify": True, "Reset": False, "MaxCount": 2}, {"Count": 1, "AcceptedPulse": True, "AtLimit": False}), step({"Event": False, "Qualify": True, "Reset": False, "MaxCount": 2}, {"Count": 1, "AcceptedPulse": False, "AtLimit": False}), step({"Event": True, "Qualify": True, "Reset": False, "MaxCount": 2}, {"Count": 2, "AcceptedPulse": True, "AtLimit": True}), step({"Event": False, "Qualify": True, "Reset": False, "MaxCount": 2}, {"Count": 2, "AcceptedPulse": False, "AtLimit": True}), step({"Event": True, "Qualify": True, "Reset": False, "MaxCount": 2}, {"Count": 2, "AcceptedPulse": False, "AtLimit": True}), step({"Event": False, "Qualify": True, "Reset": True, "MaxCount": 2}, {"Count": 0, "AcceptedPulse": False, "AtLimit": False})], "Reject unqualified events, saturate, and reset.")],
        internal_vars=["PrevEvent : BOOL := FALSE;"],
        iec_features=["FUNCTION_BLOCK", "BOOL", "INT", "retained state", "edge detection", "saturation"],
        assumptions=["MaxCount is constant during a test and is at least 1.", "The function block is called exactly once per PLC scan.", "Each test starts from a fresh function-block instance."],
        complexity={"retained_state": 2, "transitions": 5, "stateful_blocks": 1, "interactions": 4, "fault_modes": 1, "horizon_scans": 8},
    )
)

add(
    task(
        "C04_H02_dual_event_priority_lockout",
        "Dual-event priority capture with lockout",
        "C04",
        "hard",
        [var("EventA", "BOOL", "High-priority event"), var("EventB", "BOOL", "Lower-priority event"), var("Arm", "BOOL", "Capture enable"), var("Reset", "BOOL", "Clear captured event")],
        [var("Captured", "BOOL", "An event has been captured"), var("Code", "INT", "0 none, 1 event A, 2 event B"), var("Pulse", "BOOL", "Capture occurred this scan")],
        [
            req("Reset shall clear Captured, Code, and Pulse.", "G(Reset -> (!Captured AND (Code = 0) AND !Pulse))"),
            req("While armed and not captured, a rising EventA shall capture Code 1.", "G((Arm AND !prev(Captured) AND rose(EventA) AND !Reset) -> (Captured AND (Code = 1) AND Pulse))"),
            req("A simultaneous rising edge shall select EventA over EventB.", "G((Arm AND rose(EventA) AND rose(EventB) AND !prev(Captured) AND !Reset) -> (Code = 1))"),
            req("A rising EventB without EventA shall capture Code 2.", "G((Arm AND !prev(Captured) AND !rose(EventA) AND rose(EventB) AND !Reset) -> (Code = 2))"),
            req("After capture, later events shall not change Code until Reset.", "G((prev(Captured) AND !Reset) -> (Captured AND (Code = prev(Code)) AND !Pulse))", True),
        ],
        """Pulse := FALSE;
IF Reset THEN
    Captured := FALSE;
    Code := 0;
ELSIF Arm AND (NOT Captured) THEN
    IF EventA AND (NOT PrevA) THEN
        Captured := TRUE;
        Code := 1;
        Pulse := TRUE;
    ELSIF EventB AND (NOT PrevB) THEN
        Captured := TRUE;
        Code := 2;
        Pulse := TRUE;
    END_IF;
END_IF;
PrevA := EventA;
PrevB := EventB;""",
        [test("simultaneous_priority", ["R2", "R3"], [step({"EventA": False, "EventB": False, "Arm": True, "Reset": False}, {"Captured": False, "Code": 0, "Pulse": False}), step({"EventA": True, "EventB": True, "Arm": True, "Reset": False}, {"Captured": True, "Code": 1, "Pulse": True}), step({"EventA": True, "EventB": True, "Arm": True, "Reset": False}, {"Captured": True, "Code": 1, "Pulse": False})], "Event A wins simultaneous capture.")],
        [test("lockout_and_reset", ["R1", "R4", "R5"], [step({"EventA": False, "EventB": True, "Arm": True, "Reset": False}, {"Captured": True, "Code": 2, "Pulse": True}), step({"EventA": False, "EventB": False, "Arm": True, "Reset": False}, {"Captured": True, "Code": 2, "Pulse": False}), step({"EventA": True, "EventB": False, "Arm": True, "Reset": False}, {"Captured": True, "Code": 2, "Pulse": False}), step({"EventA": False, "EventB": False, "Arm": True, "Reset": True}, {"Captured": False, "Code": 0, "Pulse": False})], "Capture B, reject a later A, and reset.")],
        internal_vars=["PrevA : BOOL := FALSE;", "PrevB : BOOL := FALSE;"],
        iec_features=["FUNCTION_BLOCK", "BOOL", "INT", "retained state", "edge detection", "priority"],
        complexity={"retained_state": 4, "transitions": 6, "stateful_blocks": 2, "interactions": 5, "fault_modes": 1, "horizon_scans": 7},
    )
)


# C05 -- Timers and timeouts ----------------------------------------------------------
add(
    task(
        "C05_E01_on_delay_enable",
        "On-delay enable",
        "C05",
        "easy",
        [var("Enable", "BOOL", "Input to be delayed"), var("Reset", "BOOL", "Immediate reset")],
        [var("Delayed", "BOOL", "Delayed output")],
        [
            req("Delayed shall remain FALSE until Enable has remained TRUE continuously for 300 ms.", "G((continuous(Enable,3) AND !Reset) -> Delayed)"),
            req("Reset or Enable FALSE shall make Delayed FALSE without an additional delay.", "G((Reset OR !Enable) -> !Delayed)", True),
        ],
        """DelayTimer(IN := Enable AND (NOT Reset), PT := T#300ms);
Delayed := DelayTimer.Q;""",
        [test("delay_and_reset", ["R1", "R2"], [step({"Enable": False, "Reset": False}, {"Delayed": False}), step({"Enable": True, "Reset": False}, {"Delayed": True}, repeat=5, check="last_only"), step({"Enable": True, "Reset": True}, {"Delayed": False})], "Allow more than the threshold, then reset immediately.")],
        [test("interrupted_timing", ["R1", "R2"], [step({"Enable": True, "Reset": False}, {"Delayed": False}), step({"Enable": False, "Reset": False}, {"Delayed": False}), step({"Enable": True, "Reset": False}, {"Delayed": True}, repeat=5, check="last_only")], "Interrupt the timing interval and require a fresh full interval.")],
        internal_vars=["DelayTimer : TON;"],
        iec_features=["FUNCTION_BLOCK", "BOOL", "TIME", "TON"],
        assumptions=["The runtime scan period is 100 ms.", "Timer tests check exact boundaries with a declared one-scan infrastructure tolerance and stable states without tolerance.", "Each test starts from a fresh function-block instance."],
        complexity={"retained_state": 1, "transitions": 2, "stateful_blocks": 1, "horizon_scans": 5},
    )
)

add(
    task(
        "C05_M01_off_delay_fan",
        "Off-delay ventilation fan",
        "C05",
        "medium",
        [var("Demand", "BOOL", "Ventilation demand"), var("SafetyTrip", "BOOL", "Immediate safety shutdown")],
        [var("Fan", "BOOL", "Fan command"), var("RunOn", "BOOL", "Fan is in off-delay run-on")],
        [
            req("Fan shall turn on without delay when Demand becomes TRUE and SafetyTrip is FALSE.", "G((Demand AND !SafetyTrip) -> Fan)"),
            req("After Demand becomes FALSE, Fan shall remain on for 300 ms unless SafetyTrip occurs.", "G((fell(Demand) AND !SafetyTrip) -> hold(Fan,3))"),
            req("SafetyTrip shall turn Fan and RunOn off immediately.", "G(SafetyTrip -> (!Fan AND !RunOn))", True),
            req("RunOn shall indicate the interval in which Demand is FALSE but the off-delay output remains TRUE.", "G(RunOn = (!Demand AND Fan))"),
        ],
        """OffTimer(IN := Demand AND (NOT SafetyTrip), PT := T#300ms);
IF SafetyTrip THEN
    Fan := FALSE;
ELSE
    Fan := OffTimer.Q;
END_IF;
RunOn := (NOT Demand) AND Fan;""",
        [test("demand_and_run_on", ["R1", "R2", "R4"], [step({"Demand": True, "SafetyTrip": False}, {"Fan": True, "RunOn": False}), step({"Demand": False, "SafetyTrip": False}, {"Fan": True, "RunOn": True}), step({"Demand": False, "SafetyTrip": False}, {"Fan": False, "RunOn": False}, repeat=5, check="last_only")], "Start immediately and retain output for a bounded run-on.")],
        [test("trip_during_run_on", ["R3"], [step({"Demand": True, "SafetyTrip": False}, {"Fan": True, "RunOn": False}), step({"Demand": False, "SafetyTrip": False}, {"Fan": True, "RunOn": True}), step({"Demand": False, "SafetyTrip": True}, {"Fan": False, "RunOn": False})], "Safety trip overrides the remaining off delay.")],
        internal_vars=["OffTimer : TOF;"],
        iec_features=["FUNCTION_BLOCK", "BOOL", "TIME", "TOF", "IF"],
        assumptions=["The runtime scan period is 100 ms.", "Demand is held TRUE for at least one scan before an off-delay test.", "Each test starts from a fresh function-block instance."],
        complexity={"retained_state": 1, "transitions": 3, "stateful_blocks": 1, "interactions": 2, "fault_modes": 1, "horizon_scans": 6},
    )
)

add(
    task(
        "C05_M02_heartbeat_watchdog",
        "Heartbeat watchdog timeout",
        "C05",
        "medium",
        [var("MonitorEnable", "BOOL", "Enable monitoring"), var("Heartbeat", "BOOL", "One-scan heartbeat pulse"), var("Reset", "BOOL", "Clear timeout latch")],
        [var("TimedOut", "BOOL", "Latched timeout"), var("Healthy", "BOOL", "Monitor enabled and not timed out")],
        [
            req("While monitoring, a Heartbeat shall restart the 400 ms watchdog interval.", "G(Heartbeat -> reset(watchdog))"),
            req("Absence of Heartbeat for at least 400 ms shall latch TimedOut TRUE.", "G((MonitorEnable AND no_event(Heartbeat,4)) -> TimedOut)", True),
            req("Reset shall clear TimedOut only while MonitorEnable is FALSE.", "G((Reset AND !MonitorEnable) -> !TimedOut)"),
            req("Healthy shall equal MonitorEnable and not TimedOut.", "G(Healthy = (MonitorEnable AND !TimedOut))"),
        ],
        """Watchdog(IN := MonitorEnable AND (NOT Heartbeat) AND (NOT TimedOut), PT := T#400ms);
IF Watchdog.Q THEN
    TimedOut := TRUE;
ELSIF Reset AND (NOT MonitorEnable) THEN
    TimedOut := FALSE;
END_IF;
Healthy := MonitorEnable AND (NOT TimedOut);""",
        [test("timeout_without_heartbeat", ["R2", "R4"], [step({"MonitorEnable": True, "Heartbeat": False, "Reset": False}, {"TimedOut": True, "Healthy": False}, repeat=6, check="last_only")], "Allow the watchdog to expire.")],
        [test("heartbeat_and_qualified_reset", ["R1", "R3"], [step({"MonitorEnable": True, "Heartbeat": False, "Reset": False}, {"TimedOut": False, "Healthy": True}), step({"MonitorEnable": True, "Heartbeat": True, "Reset": False}, {"TimedOut": False, "Healthy": True}), step({"MonitorEnable": True, "Heartbeat": False, "Reset": False}, {"TimedOut": True, "Healthy": False}, repeat=6, check="last_only"), step({"MonitorEnable": True, "Heartbeat": False, "Reset": True}, {"TimedOut": True, "Healthy": False}), step({"MonitorEnable": False, "Heartbeat": False, "Reset": True}, {"TimedOut": False, "Healthy": False})], "Restart the interval, time out, reject an enabled reset, then reset while disabled.")],
        internal_vars=["Watchdog : TON;"],
        iec_features=["FUNCTION_BLOCK", "BOOL", "TIME", "TON", "retained output", "watchdog"],
        assumptions=["The runtime scan period is 100 ms.", "Heartbeat is a pulse lasting no more than one scan.", "Each test starts from a fresh function-block instance."],
        complexity={"retained_state": 2, "transitions": 4, "stateful_blocks": 1, "interactions": 3, "fault_modes": 1, "horizon_scans": 8},
    )
)

add(
    task(
        "C05_H01_two_stage_startup",
        "Two-stage timed startup with safe abort",
        "C05",
        "hard",
        [var("Start", "BOOL", "Start sequence"), var("Stop", "BOOL", "Abort sequence"), var("Permit", "BOOL", "Safety permission"), var("Stage1Feedback", "BOOL", "Stage 1 feedback")],
        [var("Stage1", "BOOL", "Stage 1 command"), var("Stage2", "BOOL", "Stage 2 command"), var("Fault", "BOOL", "Stage 1 feedback timeout")],
        [
            req("Start with Permit shall command Stage1 immediately.", "G((Start AND Permit AND !Stop AND !Fault) -> Stage1)"),
            req("Stage2 shall not start until Stage1Feedback has remained TRUE for at least 300 ms.", "G(Stage2 -> continuous(Stage1Feedback,3))", True),
            req("If Stage1Feedback is absent for 600 ms after Stage1 starts, Fault shall latch and both stages shall stop.", "G((Stage1 AND no_event(Stage1Feedback,6)) -> (Fault AND !Stage1 AND !Stage2))", True),
            req("Stop or loss of Permit shall turn both stages off immediately.", "G((Stop OR !Permit) -> (!Stage1 AND !Stage2))", True),
            req("Fault remains latched until Stop is TRUE while Start is FALSE.", "G((Fault AND !(Stop AND !Start)) -> X(Fault))"),
        ],
        """FeedbackStable(IN := Stage1Feedback AND Stage1, PT := T#300ms);
FeedbackTimeout(IN := Stage1 AND (NOT Stage1Feedback), PT := T#600ms);

IF FeedbackTimeout.Q THEN
    Fault := TRUE;
END_IF;
IF Stop AND (NOT Start) THEN
    Fault := FALSE;
END_IF;

IF Stop OR (NOT Permit) OR Fault THEN
    Stage1 := FALSE;
    Stage2 := FALSE;
ELSIF Start THEN
    Stage1 := TRUE;
    Stage2 := FeedbackStable.Q;
END_IF;""",
        [test("successful_start", ["R1", "R2"], [step({"Start": True, "Stop": False, "Permit": True, "Stage1Feedback": False}, {"Stage1": True, "Stage2": False, "Fault": False}), step({"Start": True, "Stop": False, "Permit": True, "Stage1Feedback": True}, {"Stage1": True, "Stage2": True, "Fault": False}, repeat=5, check="last_only")], "Stage 2 follows stable feedback.")],
        [test("timeout_and_fault_reset", ["R3", "R4", "R5"], [step({"Start": True, "Stop": False, "Permit": True, "Stage1Feedback": False}, {"Stage1": False, "Stage2": False, "Fault": True}, repeat=8, check="last_only"), step({"Start": True, "Stop": True, "Permit": True, "Stage1Feedback": False}, {"Stage1": False, "Stage2": False, "Fault": True}), step({"Start": False, "Stop": True, "Permit": True, "Stage1Feedback": False}, {"Stage1": False, "Stage2": False, "Fault": False})], "Latch a feedback timeout and require released Start for fault reset.")],
        internal_vars=["FeedbackStable : TON;", "FeedbackTimeout : TON;"],
        iec_features=["FUNCTION_BLOCK", "BOOL", "TIME", "TON", "retained fault", "timed sequence"],
        assumptions=["The runtime scan period is 100 ms.", "Permit changes are sampled at scan start.", "Each test starts from a fresh function-block instance."],
        complexity={"retained_state": 3, "transitions": 6, "stateful_blocks": 2, "interactions": 5, "fault_modes": 2, "horizon_scans": 10},
    )
)

add(
    task(
        "C05_H02_star_delta_sequence",
        "Star-delta motor transition",
        "C05",
        "hard",
        [var("Start", "BOOL", "Start command"), var("Stop", "BOOL", "Stop command"), var("Overload", "BOOL", "Motor overload"), var("Reset", "BOOL", "Fault reset")],
        [var("Main", "BOOL", "Main contactor"), var("Star", "BOOL", "Star contactor"), var("Delta", "BOOL", "Delta contactor"), var("Fault", "BOOL", "Latched overload fault")],
        [
            req("Start shall energize Main and Star when no fault, Stop, or Overload is active.", "G((Start AND !Stop AND !Overload AND !Fault AND phase=idle) -> (Main AND Star AND !Delta))"),
            req("After 500 ms in Star, Star shall turn off before Delta turns on after a 200 ms transition gap.", "G(Delta -> (Main AND !Star AND elapsed_star>=7))", True),
            req("Star and Delta shall never be TRUE together.", "G(!(Star AND Delta))", True),
            req("Stop or Overload shall immediately turn off all contactors; Overload latches Fault.", "G((Stop OR Overload) -> (!Main AND !Star AND !Delta))", True),
            req("Reset clears Fault only while Start is FALSE and Overload is FALSE.", "G((Reset AND !Start AND !Overload) -> !Fault)"),
        ],
        """StarTimer(IN := Main AND Star, PT := T#500ms);
GapTimer(IN := Main AND (NOT Star) AND (NOT Delta), PT := T#200ms);

IF Overload THEN
    Fault := TRUE;
END_IF;
IF Reset AND (NOT Start) AND (NOT Overload) THEN
    Fault := FALSE;
END_IF;

IF Stop OR Overload OR Fault THEN
    Main := FALSE;
    Star := FALSE;
    Delta := FALSE;
ELSIF Start AND (NOT Main) THEN
    Main := TRUE;
    Star := TRUE;
    Delta := FALSE;
ELSIF StarTimer.Q THEN
    Star := FALSE;
ELSIF GapTimer.Q AND Main THEN
    Delta := TRUE;
END_IF;""",
        [test("normal_transition", ["R1", "R2", "R3"], [step({"Start": True, "Stop": False, "Overload": False, "Reset": False}, {"Main": True, "Star": True, "Delta": False, "Fault": False}), step({"Start": True, "Stop": False, "Overload": False, "Reset": False}, {"Main": True, "Star": False, "Delta": True, "Fault": False}, repeat=10, check="last_only")], "Reach delta after star time and transition gap.")],
        [test("overload_and_reset", ["R4", "R5"], [step({"Start": True, "Stop": False, "Overload": False, "Reset": False}, {"Main": True, "Star": True, "Delta": False, "Fault": False}), step({"Start": True, "Stop": False, "Overload": True, "Reset": False}, {"Main": False, "Star": False, "Delta": False, "Fault": True}), step({"Start": True, "Stop": False, "Overload": False, "Reset": True}, {"Main": False, "Star": False, "Delta": False, "Fault": True}), step({"Start": False, "Stop": False, "Overload": False, "Reset": True}, {"Main": False, "Star": False, "Delta": False, "Fault": False})], "Trip on overload and require a qualified reset.")],
        internal_vars=["StarTimer : TON;", "GapTimer : TON;"],
        iec_features=["FUNCTION_BLOCK", "BOOL", "TIME", "TON", "retained outputs", "timed transition", "interlock"],
        assumptions=["The runtime scan period is 100 ms.", "Start may remain TRUE during normal operation.", "Each test starts from a fresh function-block instance."],
        complexity={"retained_state": 5, "transitions": 7, "stateful_blocks": 2, "interactions": 6, "fault_modes": 2, "horizon_scans": 12},
    )
)


# C06 -- Counters and batch logic -----------------------------------------------------
add(
    task(
        "C06_E01_three_part_counter",
        "Three-part completion counter",
        "C06",
        "easy",
        [var("PartPulse", "BOOL", "One-scan part pulse"), var("Reset", "BOOL", "Counter reset")],
        [var("Count", "INT", "Current count"), var("Complete", "BOOL", "Count reached three")],
        [
            req("Each rising PartPulse shall increment Count once until Count reaches three.", "G((rose(PartPulse) AND prev(Count)<3 AND !Reset) -> (Count=prev(Count)+1))"),
            req("Count shall saturate at three.", "G((Count >= 0) AND (Count <= 3))", True),
            req("Complete shall be TRUE exactly when Count equals three.", "G(Complete = (Count = 3))"),
            req("Reset shall clear Count and Complete.", "G(Reset -> ((Count=0) AND !Complete))"),
        ],
        """IF Reset THEN
    Count := 0;
ELSIF PartPulse AND (NOT PrevPart) AND (Count < 3) THEN
    Count := Count + 1;
END_IF;
Complete := Count = 3;
PrevPart := PartPulse;""",
        [test("count_two_edges", ["R1"], [step({"PartPulse": True, "Reset": False}, {"Count": 1, "Complete": False}), step({"PartPulse": True, "Reset": False}, {"Count": 1, "Complete": False}), step({"PartPulse": False, "Reset": False}, {"Count": 1, "Complete": False}), step({"PartPulse": True, "Reset": False}, {"Count": 2, "Complete": False})], "Count edges, not held levels.")],
        [test("complete_saturate_reset", ["R2", "R3", "R4"], [step({"PartPulse": True, "Reset": False}, {"Count": 1, "Complete": False}), step({"PartPulse": False, "Reset": False}, {"Count": 1, "Complete": False}), step({"PartPulse": True, "Reset": False}, {"Count": 2, "Complete": False}), step({"PartPulse": False, "Reset": False}, {"Count": 2, "Complete": False}), step({"PartPulse": True, "Reset": False}, {"Count": 3, "Complete": True}), step({"PartPulse": False, "Reset": False}, {"Count": 3, "Complete": True}), step({"PartPulse": True, "Reset": False}, {"Count": 3, "Complete": True}), step({"PartPulse": False, "Reset": True}, {"Count": 0, "Complete": False})], "Reach, saturate, and reset the batch count.")],
        internal_vars=["PrevPart : BOOL := FALSE;"],
        iec_features=["FUNCTION_BLOCK", "BOOL", "INT", "retained state", "edge detection", "counter"],
        complexity={"retained_state": 2, "transitions": 3, "stateful_blocks": 1, "horizon_scans": 8},
    )
)

add(
    task(
        "C06_M01_configurable_batch_counter",
        "Configurable batch counter",
        "C06",
        "medium",
        [var("Item", "BOOL", "Item detection"), var("Reset", "BOOL", "Reset current batch"), var("Target", "INT", "Batch target, assumed 1 through 100"), var("Enable", "BOOL", "Counting enable")],
        [var("Count", "INT", "Accepted item count"), var("BatchDone", "BOOL", "Target reached"), var("Accepted", "BOOL", "Item accepted this scan")],
        [
            req("Only a rising Item edge while Enable and below Target shall increment Count.", "G(Accepted = (rose(Item) AND Enable AND prev(Count)<Target AND !Reset))"),
            req("Count shall remain between zero and Target.", "G((Count>=0) AND (Count<=Target))", True),
            req("BatchDone shall be TRUE when Count reaches Target.", "G(BatchDone = (Count>=Target))"),
            req("Reset shall clear Count, BatchDone, and Accepted.", "G(Reset -> ((Count=0) AND !BatchDone AND !Accepted))"),
        ],
        """Accepted := FALSE;
IF Reset THEN
    Count := 0;
ELSIF Enable AND Item AND (NOT PrevItem) AND (Count < Target) THEN
    Count := Count + 1;
    Accepted := TRUE;
END_IF;
BatchDone := Count >= Target;
PrevItem := Item;""",
        [test("enabled_counting", ["R1", "R3"], [step({"Item": True, "Reset": False, "Target": 2, "Enable": False}, {"Count": 0, "BatchDone": False, "Accepted": False}), step({"Item": False, "Reset": False, "Target": 2, "Enable": True}, {"Count": 0, "BatchDone": False, "Accepted": False}), step({"Item": True, "Reset": False, "Target": 2, "Enable": True}, {"Count": 1, "BatchDone": False, "Accepted": True})], "Reject disabled events and accept an enabled edge.")],
        [test("target_and_reset", ["R2", "R3", "R4"], [step({"Item": True, "Reset": False, "Target": 2, "Enable": True}, {"Count": 1, "BatchDone": False, "Accepted": True}), step({"Item": False, "Reset": False, "Target": 2, "Enable": True}, {"Count": 1, "BatchDone": False, "Accepted": False}), step({"Item": True, "Reset": False, "Target": 2, "Enable": True}, {"Count": 2, "BatchDone": True, "Accepted": True}), step({"Item": False, "Reset": False, "Target": 2, "Enable": True}, {"Count": 2, "BatchDone": True, "Accepted": False}), step({"Item": True, "Reset": False, "Target": 2, "Enable": True}, {"Count": 2, "BatchDone": True, "Accepted": False}), step({"Item": False, "Reset": True, "Target": 2, "Enable": True}, {"Count": 0, "BatchDone": False, "Accepted": False})], "Saturate at a configurable target and reset.")],
        internal_vars=["PrevItem : BOOL := FALSE;"],
        iec_features=["FUNCTION_BLOCK", "BOOL", "INT", "retained state", "edge detection", "configurable counter"],
        assumptions=["Target remains constant during a test and is between 1 and 100.", "Item pulses are separated by at least one low scan.", "Each test starts from a fresh function-block instance."],
        complexity={"retained_state": 2, "transitions": 4, "stateful_blocks": 1, "interactions": 2, "horizon_scans": 7},
    )
)

add(
    task(
        "C06_M02_bounded_up_down_counter",
        "Bounded up/down inventory counter",
        "C06",
        "medium",
        [var("AddItem", "BOOL", "Add one item"), var("RemoveItem", "BOOL", "Remove one item"), var("Reset", "BOOL", "Reset inventory"), var("Capacity", "INT", "Maximum count, assumed positive")],
        [var("Count", "INT", "Inventory count"), var("Empty", "BOOL", "Count is zero"), var("Full", "BOOL", "Count reached Capacity"), var("Conflict", "BOOL", "Add and Remove rose together")],
        [
            req("A lone rising AddItem edge increments Count when below Capacity.", "G((rose(AddItem) AND !rose(RemoveItem) AND prev(Count)<Capacity AND !Reset) -> Count=prev(Count)+1)"),
            req("A lone rising RemoveItem edge decrements Count when above zero.", "G((rose(RemoveItem) AND !rose(AddItem) AND prev(Count)>0 AND !Reset) -> Count=prev(Count)-1)"),
            req("Simultaneous rising edges shall leave Count unchanged and set Conflict for one scan.", "G((rose(AddItem) AND rose(RemoveItem) AND !Reset) -> ((Count=prev(Count)) AND Conflict))"),
            req("Count shall remain within zero and Capacity; Empty and Full reflect the boundaries.", "G((Count>=0) AND (Count<=Capacity) AND (Empty=(Count=0)) AND (Full=(Count>=Capacity)))", True),
            req("Reset shall clear Count and Conflict.", "G(Reset -> ((Count=0) AND !Conflict))"),
        ],
        """Conflict := FALSE;
IF Reset THEN
    Count := 0;
ELSIF AddItem AND (NOT PrevAdd) AND RemoveItem AND (NOT PrevRemove) THEN
    Conflict := TRUE;
ELSIF AddItem AND (NOT PrevAdd) AND (Count < Capacity) THEN
    Count := Count + 1;
ELSIF RemoveItem AND (NOT PrevRemove) AND (Count > 0) THEN
    Count := Count - 1;
END_IF;
Empty := Count = 0;
Full := Count >= Capacity;
PrevAdd := AddItem;
PrevRemove := RemoveItem;""",
        [test("add_and_remove", ["R1", "R2", "R4"], [step({"AddItem": True, "RemoveItem": False, "Reset": False, "Capacity": 2}, {"Count": 1, "Empty": False, "Full": False, "Conflict": False}), step({"AddItem": False, "RemoveItem": False, "Reset": False, "Capacity": 2}, {"Count": 1, "Empty": False, "Full": False, "Conflict": False}), step({"AddItem": False, "RemoveItem": True, "Reset": False, "Capacity": 2}, {"Count": 0, "Empty": True, "Full": False, "Conflict": False})], "Increment and decrement within bounds.")],
        [test("conflict_capacity_reset", ["R3", "R4", "R5"], [step({"AddItem": True, "RemoveItem": True, "Reset": False, "Capacity": 2}, {"Count": 0, "Empty": True, "Full": False, "Conflict": True}), step({"AddItem": False, "RemoveItem": False, "Reset": False, "Capacity": 2}, {"Count": 0, "Empty": True, "Full": False, "Conflict": False}), step({"AddItem": True, "RemoveItem": False, "Reset": False, "Capacity": 2}, {"Count": 1, "Empty": False, "Full": False, "Conflict": False}), step({"AddItem": False, "RemoveItem": False, "Reset": False, "Capacity": 2}, {"Count": 1, "Empty": False, "Full": False, "Conflict": False}), step({"AddItem": True, "RemoveItem": False, "Reset": False, "Capacity": 2}, {"Count": 2, "Empty": False, "Full": True, "Conflict": False}), step({"AddItem": False, "RemoveItem": False, "Reset": True, "Capacity": 2}, {"Count": 0, "Empty": True, "Full": False, "Conflict": False})], "Resolve conflict, reach capacity, and reset.")],
        internal_vars=["PrevAdd : BOOL := FALSE;", "PrevRemove : BOOL := FALSE;"],
        iec_features=["FUNCTION_BLOCK", "BOOL", "INT", "retained state", "dual edge detection", "bounded counter"],
        assumptions=["Capacity remains constant during a test and is positive.", "Each test starts from a fresh function-block instance."],
        complexity={"retained_state": 3, "transitions": 5, "stateful_blocks": 2, "interactions": 3, "horizon_scans": 7},
    )
)

add(
    task(
        "C06_H01_quality_batch_statistics",
        "Good/reject batch statistics with reject lockout",
        "C06",
        "hard",
        [var("GoodPart", "BOOL", "Good-part pulse"), var("RejectPart", "BOOL", "Rejected-part pulse"), var("Reset", "BOOL", "Reset statistics"), var("BatchTarget", "INT", "Total parts in a batch"), var("RejectLimit", "INT", "Maximum allowed rejects")],
        [var("GoodCount", "INT", "Good parts"), var("RejectCount", "INT", "Rejected parts"), var("BatchDone", "BOOL", "Total reached target"), var("QualityFault", "BOOL", "Reject count exceeded limit")],
        [
            req("A good-part rising edge increments only GoodCount; a reject-part rising edge increments only RejectCount.", "G(exclusive_edges_update_matching_counter)"),
            req("Simultaneous good and reject edges shall count one reject and no good part.", "G((rose(GoodPart) AND rose(RejectPart) AND !Reset) -> (RejectCount=prev(RejectCount)+1 AND GoodCount=prev(GoodCount)))"),
            req("BatchDone shall be TRUE when GoodCount plus RejectCount reaches BatchTarget.", "G(BatchDone = ((GoodCount+RejectCount)>=BatchTarget))"),
            req("QualityFault shall latch when RejectCount reaches RejectLimit and remain set until Reset.", "G((RejectCount>=RejectLimit) -> QualityFault)", True),
            req("Reset shall clear both counts, BatchDone, and QualityFault.", "G(Reset -> (GoodCount=0 AND RejectCount=0 AND !BatchDone AND !QualityFault))"),
        ],
        """IF Reset THEN
    GoodCount := 0;
    RejectCount := 0;
    QualityFault := FALSE;
ELSE
    IF RejectPart AND (NOT PrevReject) THEN
        RejectCount := RejectCount + 1;
    ELSIF GoodPart AND (NOT PrevGood) THEN
        GoodCount := GoodCount + 1;
    END_IF;
    IF RejectCount >= RejectLimit THEN
        QualityFault := TRUE;
    END_IF;
END_IF;
BatchDone := (GoodCount + RejectCount) >= BatchTarget;
PrevGood := GoodPart;
PrevReject := RejectPart;""",
        [test("good_and_reject", ["R1", "R3"], [step({"GoodPart": True, "RejectPart": False, "Reset": False, "BatchTarget": 3, "RejectLimit": 2}, {"GoodCount": 1, "RejectCount": 0, "BatchDone": False, "QualityFault": False}), step({"GoodPart": False, "RejectPart": False, "Reset": False, "BatchTarget": 3, "RejectLimit": 2}, {"GoodCount": 1, "RejectCount": 0, "BatchDone": False, "QualityFault": False}), step({"GoodPart": False, "RejectPart": True, "Reset": False, "BatchTarget": 3, "RejectLimit": 2}, {"GoodCount": 1, "RejectCount": 1, "BatchDone": False, "QualityFault": False})], "Count each classification independently.")],
        [test("simultaneous_priority_fault_reset", ["R2", "R4", "R5"], [step({"GoodPart": True, "RejectPart": True, "Reset": False, "BatchTarget": 2, "RejectLimit": 2}, {"GoodCount": 0, "RejectCount": 1, "BatchDone": False, "QualityFault": False}), step({"GoodPart": False, "RejectPart": False, "Reset": False, "BatchTarget": 2, "RejectLimit": 2}, {"GoodCount": 0, "RejectCount": 1, "BatchDone": False, "QualityFault": False}), step({"GoodPart": False, "RejectPart": True, "Reset": False, "BatchTarget": 2, "RejectLimit": 2}, {"GoodCount": 0, "RejectCount": 2, "BatchDone": True, "QualityFault": True}), step({"GoodPart": False, "RejectPart": False, "Reset": True, "BatchTarget": 2, "RejectLimit": 2}, {"GoodCount": 0, "RejectCount": 0, "BatchDone": False, "QualityFault": False})], "Prioritize reject, latch quality fault, and reset.")],
        internal_vars=["PrevGood : BOOL := FALSE;", "PrevReject : BOOL := FALSE;"],
        iec_features=["FUNCTION_BLOCK", "BOOL", "INT", "retained counters", "edge detection", "priority", "fault latch"],
        assumptions=["BatchTarget and RejectLimit remain positive and constant during a test.", "Each test starts from a fresh function-block instance."],
        complexity={"retained_state": 5, "transitions": 6, "stateful_blocks": 2, "interactions": 5, "fault_modes": 2, "horizon_scans": 8},
    )
)

add(
    task(
        "C06_H02_inspection_window_lockout",
        "Inspection-window reject lockout",
        "C06",
        "hard",
        [var("Inspected", "BOOL", "One item inspected"), var("Rejected", "BOOL", "Current inspected item rejected"), var("Reset", "BOOL", "Manual lockout reset"), var("WindowSize", "INT", "Items per inspection window"), var("RejectLimit", "INT", "Rejects allowed in one window")],
        [var("WindowCount", "INT", "Items in current window"), var("RejectCount", "INT", "Rejects in current window"), var("LockedOut", "BOOL", "Quality lockout"), var("WindowComplete", "BOOL", "One-scan window-complete pulse")],
        [
            req("Each rising Inspected edge shall add one to WindowCount and, when Rejected is TRUE, one to RejectCount.", "G(rose(Inspected) AND !Reset AND !LockedOut -> update_window_counts)"),
            req("Completing WindowSize items shall pulse WindowComplete for one scan and then start a new zeroed window.", "G(WindowComplete -> ((WindowCount=0) AND (RejectCount=0)))"),
            req("If rejects in the completed window exceed RejectLimit, LockedOut shall latch TRUE.", "G(completed_rejects>RejectLimit -> LockedOut)", True),
            req("No new items shall be counted while LockedOut.", "G(LockedOut AND !Reset -> (WindowCount=prev(WindowCount) AND RejectCount=prev(RejectCount)))", True),
            req("Reset shall clear counts, WindowComplete, and LockedOut.", "G(Reset -> (WindowCount=0 AND RejectCount=0 AND !WindowComplete AND !LockedOut))"),
        ],
        """WindowComplete := FALSE;
IF Reset THEN
    WindowCount := 0;
    RejectCount := 0;
    LockedOut := FALSE;
ELSIF (NOT LockedOut) AND Inspected AND (NOT PrevInspected) THEN
    WindowCount := WindowCount + 1;
    IF Rejected THEN
        RejectCount := RejectCount + 1;
    END_IF;
    IF WindowCount >= WindowSize THEN
        IF RejectCount > RejectLimit THEN
            LockedOut := TRUE;
        END_IF;
        WindowCount := 0;
        RejectCount := 0;
        WindowComplete := TRUE;
    END_IF;
END_IF;
PrevInspected := Inspected;""",
        [test("acceptable_window", ["R1", "R2"], [step({"Inspected": True, "Rejected": False, "Reset": False, "WindowSize": 2, "RejectLimit": 1}, {"WindowCount": 1, "RejectCount": 0, "LockedOut": False, "WindowComplete": False}), step({"Inspected": False, "Rejected": False, "Reset": False, "WindowSize": 2, "RejectLimit": 1}, {"WindowCount": 1, "RejectCount": 0, "LockedOut": False, "WindowComplete": False}), step({"Inspected": True, "Rejected": True, "Reset": False, "WindowSize": 2, "RejectLimit": 1}, {"WindowCount": 0, "RejectCount": 0, "LockedOut": False, "WindowComplete": True})], "Complete an acceptable window and reset its counters.")],
        [test("lockout_and_reset", ["R3", "R4", "R5"], [step({"Inspected": True, "Rejected": True, "Reset": False, "WindowSize": 2, "RejectLimit": 1}, {"WindowCount": 1, "RejectCount": 1, "LockedOut": False, "WindowComplete": False}), step({"Inspected": False, "Rejected": False, "Reset": False, "WindowSize": 2, "RejectLimit": 1}, {"WindowCount": 1, "RejectCount": 1, "LockedOut": False, "WindowComplete": False}), step({"Inspected": True, "Rejected": True, "Reset": False, "WindowSize": 2, "RejectLimit": 1}, {"WindowCount": 0, "RejectCount": 0, "LockedOut": True, "WindowComplete": True}), step({"Inspected": False, "Rejected": False, "Reset": False, "WindowSize": 2, "RejectLimit": 1}, {"WindowCount": 0, "RejectCount": 0, "LockedOut": True, "WindowComplete": False}), step({"Inspected": True, "Rejected": False, "Reset": False, "WindowSize": 2, "RejectLimit": 1}, {"WindowCount": 0, "RejectCount": 0, "LockedOut": True, "WindowComplete": False}), step({"Inspected": False, "Rejected": False, "Reset": True, "WindowSize": 2, "RejectLimit": 1}, {"WindowCount": 0, "RejectCount": 0, "LockedOut": False, "WindowComplete": False})], "Exceed the reject limit, block further items, and reset.")],
        internal_vars=["PrevInspected : BOOL := FALSE;"],
        iec_features=["FUNCTION_BLOCK", "BOOL", "INT", "retained counters", "edge detection", "windowing", "fault latch"],
        assumptions=["WindowSize is at least 1 and RejectLimit is non-negative.", "Rejected is sampled only on a rising Inspected edge.", "Each test starts from a fresh function-block instance."],
        complexity={"retained_state": 5, "transitions": 7, "stateful_blocks": 1, "interactions": 6, "fault_modes": 2, "horizon_scans": 10},
    )
)


# C07 -- Analog processing ------------------------------------------------------------
add(
    task(
        "C07_E01_linear_scaling",
        "Linear raw-value scaling",
        "C07",
        "easy",
        [var("Raw", "INT", "Raw input from 0 to 1000")],
        [var("Engineering", "REAL", "Scaled output from 0.0 to 100.0")],
        [req("Engineering shall equal Raw multiplied by 0.1 for Raw values from 0 through 1000.", "G(Engineering = INT_TO_REAL(Raw)*0.1)")],
        "Engineering := INT_TO_REAL(Raw) * 0.1;",
        [test("scale_endpoints", ["R1"], [step({"Raw": 0}, {"Engineering": 0.0}), step({"Raw": 1000}, {"Engineering": 100.0})], "Scale both range endpoints.")],
        [test("scale_interior", ["R1"], [step({"Raw": 1}, {"Engineering": 0.1}), step({"Raw": 537}, {"Engineering": 53.7}), step({"Raw": 999}, {"Engineering": 99.9})], "Scale non-round interior values.")],
        iec_features=["FUNCTION_BLOCK", "INT", "REAL", "INT_TO_REAL", "arithmetic"],
        real_tolerance=0.0001,
    )
)

add(
    task(
        "C07_M01_clamped_scaling",
        "Clamped analog scaling with range status",
        "C07",
        "medium",
        [var("Raw", "INT", "Raw input nominally 0 through 4095")],
        [var("Engineering", "REAL", "Scaled output 0.0 through 10.0"), var("UnderRange", "BOOL", "Raw below zero"), var("OverRange", "BOOL", "Raw above 4095")],
        [
            req("Raw below zero shall set UnderRange, clear OverRange, and clamp Engineering to 0.0.", "G((Raw<0) -> (UnderRange AND !OverRange AND Engineering=0.0))"),
            req("Raw above 4095 shall set OverRange, clear UnderRange, and clamp Engineering to 10.0.", "G((Raw>4095) -> (OverRange AND !UnderRange AND Engineering=10.0))"),
            req("In-range Raw shall clear both flags and scale linearly to 0.0 through 10.0.", "G((Raw>=0 AND Raw<=4095) -> (!UnderRange AND !OverRange AND Engineering=INT_TO_REAL(Raw)*10.0/4095.0))"),
        ],
        """UnderRange := FALSE;
OverRange := FALSE;
IF Raw < 0 THEN
    Engineering := 0.0;
    UnderRange := TRUE;
ELSIF Raw > 4095 THEN
    Engineering := 10.0;
    OverRange := TRUE;
ELSE
    Engineering := INT_TO_REAL(Raw) * 10.0 / 4095.0;
END_IF;""",
        [test("clamp_out_of_range", ["R1", "R2"], [step({"Raw": -1}, {"Engineering": 0.0, "UnderRange": True, "OverRange": False}), step({"Raw": 4096}, {"Engineering": 10.0, "UnderRange": False, "OverRange": True})], "Clamp immediately outside each bound.")],
        [test("inclusive_boundaries", ["R3"], [step({"Raw": 0}, {"Engineering": 0.0, "UnderRange": False, "OverRange": False}), step({"Raw": 4095}, {"Engineering": 10.0, "UnderRange": False, "OverRange": False}), step({"Raw": 2048}, {"Engineering": 5.0012210012, "UnderRange": False, "OverRange": False})], "Check inclusive endpoints and midpoint scaling.")],
        iec_features=["FUNCTION_BLOCK", "BOOL", "INT", "REAL", "IF", "ELSIF", "clamping", "conversion"],
        real_tolerance=0.0002,
        complexity={"retained_state": 0, "stateful_blocks": 0, "interactions": 2, "fault_modes": 2, "horizon_scans": 1},
    )
)

add(
    task(
        "C07_M02_temperature_hysteresis",
        "Temperature control with hysteresis",
        "C07",
        "medium",
        [var("Temperature", "REAL", "Measured temperature"), var("LowThreshold", "REAL", "Heater-on threshold"), var("HighThreshold", "REAL", "Heater-off threshold"), var("Enable", "BOOL", "Controller enable")],
        [var("Heater", "BOOL", "Latched heater command"), var("ConfigError", "BOOL", "Threshold configuration invalid")],
        [
            req("ConfigError shall be TRUE when LowThreshold is not less than HighThreshold.", "G(ConfigError = (LowThreshold>=HighThreshold))", True),
            req("Disable or ConfigError shall turn Heater off.", "G((!Enable OR ConfigError) -> !Heater)", True),
            req("While enabled with valid thresholds, Temperature below or equal to LowThreshold shall turn Heater on.", "G((Enable AND !ConfigError AND Temperature<=LowThreshold) -> Heater)"),
            req("Temperature above or equal to HighThreshold shall turn Heater off.", "G((Enable AND !ConfigError AND Temperature>=HighThreshold) -> !Heater)"),
            req("Between thresholds, Heater shall retain its previous state.", "G((Enable AND !ConfigError AND Temperature>LowThreshold AND Temperature<HighThreshold) -> Heater=prev(Heater))"),
        ],
        """ConfigError := LowThreshold >= HighThreshold;
IF (NOT Enable) OR ConfigError THEN
    Heater := FALSE;
ELSIF Temperature <= LowThreshold THEN
    Heater := TRUE;
ELSIF Temperature >= HighThreshold THEN
    Heater := FALSE;
END_IF;""",
        [test("hysteresis_cycle", ["R2", "R3", "R4", "R5"], [step({"Temperature": 18.0, "LowThreshold": 19.0, "HighThreshold": 21.0, "Enable": True}, {"Heater": True, "ConfigError": False}), step({"Temperature": 20.0, "LowThreshold": 19.0, "HighThreshold": 21.0, "Enable": True}, {"Heater": True, "ConfigError": False}), step({"Temperature": 21.0, "LowThreshold": 19.0, "HighThreshold": 21.0, "Enable": True}, {"Heater": False, "ConfigError": False})], "Turn on, retain through deadband, and turn off.")],
        [test("configuration_and_boundaries", ["R1", "R2", "R3", "R4"], [step({"Temperature": 19.0, "LowThreshold": 19.0, "HighThreshold": 21.0, "Enable": True}, {"Heater": True, "ConfigError": False}), step({"Temperature": 20.0, "LowThreshold": 21.0, "HighThreshold": 21.0, "Enable": True}, {"Heater": False, "ConfigError": True}), step({"Temperature": 18.0, "LowThreshold": 19.0, "HighThreshold": 21.0, "Enable": False}, {"Heater": False, "ConfigError": False})], "Exercise inclusive low boundary, invalid thresholds, and disable.")],
        iec_features=["FUNCTION_BLOCK", "BOOL", "REAL", "retained output", "IF", "ELSIF", "hysteresis"],
        complexity={"retained_state": 1, "transitions": 3, "stateful_blocks": 0, "interactions": 3, "fault_modes": 1, "horizon_scans": 3},
    )
)

add(
    task(
        "C07_H01_redundant_sensor_selection",
        "Redundant analog sensor selection",
        "C07",
        "hard",
        [var("SensorA", "REAL", "Sensor A value"), var("SensorB", "REAL", "Sensor B value"), var("ValidA", "BOOL", "Sensor A validity"), var("ValidB", "BOOL", "Sensor B validity"), var("MaxDifference", "REAL", "Maximum agreement difference")],
        [var("Selected", "REAL", "Selected process value"), var("Degraded", "BOOL", "Only one sensor valid"), var("Disagree", "BOOL", "Both valid but disagree"), var("NoValidSensor", "BOOL", "Neither sensor valid")],
        [
            req("When both sensors are valid and agree within MaxDifference, Selected shall be their average.", "G((ValidA AND ValidB AND ABS(SensorA-SensorB)<=MaxDifference) -> Selected=(SensorA+SensorB)/2.0)"),
            req("When both sensors are valid but disagree beyond MaxDifference, Disagree shall be TRUE and Selected shall retain its previous value.", "G((ValidA AND ValidB AND ABS(SensorA-SensorB)>MaxDifference) -> (Disagree AND Selected=prev(Selected)))", True),
            req("When exactly one sensor is valid, Selected shall use that sensor and Degraded shall be TRUE.", "G((ValidA XOR ValidB) -> Degraded)"),
            req("When neither sensor is valid, NoValidSensor shall be TRUE and Selected shall retain its previous value.", "G((!ValidA AND !ValidB) -> (NoValidSensor AND Selected=prev(Selected)))", True),
            req("Degraded, Disagree, and NoValidSensor shall be mutually exclusive.", "G(at_most_one(Degraded,Disagree,NoValidSensor))"),
        ],
        """Degraded := FALSE;
Disagree := FALSE;
NoValidSensor := FALSE;
IF ValidA AND ValidB THEN
    IF ABS(SensorA - SensorB) <= MaxDifference THEN
        Selected := (SensorA + SensorB) / 2.0;
    ELSE
        Disagree := TRUE;
    END_IF;
ELSIF ValidA THEN
    Selected := SensorA;
    Degraded := TRUE;
ELSIF ValidB THEN
    Selected := SensorB;
    Degraded := TRUE;
ELSE
    NoValidSensor := TRUE;
END_IF;""",
        [test("normal_and_degraded", ["R1", "R3"], [step({"SensorA": 10.0, "SensorB": 12.0, "ValidA": True, "ValidB": True, "MaxDifference": 3.0}, {"Selected": 11.0, "Degraded": False, "Disagree": False, "NoValidSensor": False}), step({"SensorA": 20.0, "SensorB": 99.0, "ValidA": True, "ValidB": False, "MaxDifference": 3.0}, {"Selected": 20.0, "Degraded": True, "Disagree": False, "NoValidSensor": False})], "Average agreeing channels and fall back to one valid channel.")],
        [test("disagreement_and_total_loss", ["R2", "R4", "R5"], [step({"SensorA": 10.0, "SensorB": 10.0, "ValidA": True, "ValidB": True, "MaxDifference": 1.0}, {"Selected": 10.0, "Degraded": False, "Disagree": False, "NoValidSensor": False}), step({"SensorA": 10.0, "SensorB": 20.0, "ValidA": True, "ValidB": True, "MaxDifference": 1.0}, {"Selected": 10.0, "Degraded": False, "Disagree": True, "NoValidSensor": False}), step({"SensorA": 30.0, "SensorB": 40.0, "ValidA": False, "ValidB": False, "MaxDifference": 1.0}, {"Selected": 10.0, "Degraded": False, "Disagree": False, "NoValidSensor": True})], "Retain the previous trusted value on disagreement and total loss.")],
        iec_features=["FUNCTION_BLOCK", "BOOL", "REAL", "ABS", "retained output", "sensor voting", "fault status"],
        assumptions=["MaxDifference is non-negative and constant during a test.", "Selected initializes to 0.0 in a fresh instance.", "Each test starts from a fresh function-block instance."],
        complexity={"retained_state": 1, "transitions": 5, "stateful_blocks": 0, "interactions": 5, "fault_modes": 3, "horizon_scans": 3},
    )
)

add(
    task(
        "C07_H02_rate_of_change_trip",
        "Rate-of-change monitoring with latched trip",
        "C07",
        "hard",
        [var("Value", "REAL", "Current process value"), var("Enable", "BOOL", "Monitoring enable"), var("MaxRise", "REAL", "Maximum permitted positive change per scan"), var("MaxFall", "REAL", "Maximum permitted negative change magnitude per scan"), var("Reset", "BOOL", "Trip reset")],
        [var("Delta", "REAL", "Current minus previous value"), var("Trip", "BOOL", "Latched rate trip"), var("Ready", "BOOL", "A previous enabled sample exists")],
        [
            req("The first enabled sample shall initialize history, set Ready, and shall not trip.", "G(rose(Enable) -> (Ready AND !Trip))"),
            req("For subsequent enabled samples, Delta shall equal Value minus the previous enabled Value.", "G((Enable AND prev(Ready)) -> Delta=Value-prev(Value))"),
            req("A Delta above MaxRise or below negative MaxFall shall latch Trip.", "G((Ready AND (Delta>MaxRise OR Delta<(-MaxFall))) -> Trip)", True),
            req("Trip shall remain set until Reset occurs while Enable is FALSE.", "G((Trip AND !(Reset AND !Enable)) -> X(Trip))", True),
            req("Disabling monitoring shall clear Ready but shall not by itself clear Trip.", "G(!Enable -> !Ready)"),
        ],
        """IF NOT Enable THEN
    Ready := FALSE;
    Delta := 0.0;
    IF Reset THEN
        Trip := FALSE;
    END_IF;
ELSE
    IF NOT Ready THEN
        Previous := Value;
        Delta := 0.0;
        Ready := TRUE;
    ELSE
        Delta := Value - Previous;
        Previous := Value;
        IF (Delta > MaxRise) OR (Delta < (0.0 - MaxFall)) THEN
            Trip := TRUE;
        END_IF;
    END_IF;
END_IF;""",
        [test("normal_rate", ["R1", "R2"], [step({"Value": 10.0, "Enable": True, "MaxRise": 2.0, "MaxFall": 3.0, "Reset": False}, {"Delta": 0.0, "Trip": False, "Ready": True}), step({"Value": 11.5, "Enable": True, "MaxRise": 2.0, "MaxFall": 3.0, "Reset": False}, {"Delta": 1.5, "Trip": False, "Ready": True}), step({"Value": 9.0, "Enable": True, "MaxRise": 2.0, "MaxFall": 3.0, "Reset": False}, {"Delta": -2.5, "Trip": False, "Ready": True})], "Accept changes within asymmetric bounds.")],
        [test("trip_latch_and_reset", ["R3", "R4", "R5"], [step({"Value": 10.0, "Enable": True, "MaxRise": 2.0, "MaxFall": 3.0, "Reset": False}, {"Delta": 0.0, "Trip": False, "Ready": True}), step({"Value": 13.0, "Enable": True, "MaxRise": 2.0, "MaxFall": 3.0, "Reset": False}, {"Delta": 3.0, "Trip": True, "Ready": True}), step({"Value": 13.0, "Enable": True, "MaxRise": 2.0, "MaxFall": 3.0, "Reset": True}, {"Delta": 0.0, "Trip": True, "Ready": True}), step({"Value": 13.0, "Enable": False, "MaxRise": 2.0, "MaxFall": 3.0, "Reset": True}, {"Delta": 0.0, "Trip": False, "Ready": False})], "Trip above the rise limit, retain while enabled, and reset while disabled.")],
        internal_vars=["Previous : REAL := 0.0;"],
        iec_features=["FUNCTION_BLOCK", "BOOL", "REAL", "retained state", "arithmetic", "boundary monitoring", "fault latch"],
        complexity={"retained_state": 3, "transitions": 6, "stateful_blocks": 0, "interactions": 5, "fault_modes": 2, "horizon_scans": 5},
    )
)


# C08 -- Sequential state machines ----------------------------------------------------
add(
    task(
        "C08_E01_two_step_cycle",
        "Two-step process cycle",
        "C08",
        "easy",
        [var("Start", "BOOL", "Start cycle"), var("Step1Done", "BOOL", "Step 1 completion"), var("Step2Done", "BOOL", "Step 2 completion"), var("Reset", "BOOL", "Return to idle")],
        [var("Step1", "BOOL", "Step 1 active"), var("Step2", "BOOL", "Step 2 active"), var("Complete", "BOOL", "Cycle complete"), var("State", "INT", "0 idle, 1 step 1, 2 step 2, 3 complete")],
        [
            req("Start in idle shall enter Step 1.", "G((State=0 AND Start AND !Reset) -> X(State=1))"),
            req("Step1Done in Step 1 shall enter Step 2.", "G((State=1 AND Step1Done AND !Reset) -> X(State=2))"),
            req("Step2Done in Step 2 shall enter complete state.", "G((State=2 AND Step2Done AND !Reset) -> X(State=3))"),
            req("Only the output corresponding to the current active step shall be TRUE; Complete is TRUE only in state 3.", "G(outputs_match_state(State,Step1,Step2,Complete))", True),
            req("Reset shall return to idle from any state.", "G(Reset -> (State=0 AND !Step1 AND !Step2 AND !Complete))"),
        ],
        """IF Reset THEN
    State := 0;
ELSE
    CASE State OF
        0: IF Start THEN State := 1; END_IF;
        1: IF Step1Done THEN State := 2; END_IF;
        2: IF Step2Done THEN State := 3; END_IF;
        3: State := 3;
        ELSE State := 0;
    END_CASE;
END_IF;
Step1 := State = 1;
Step2 := State = 2;
Complete := State = 3;""",
        [test("normal_cycle", ["R1", "R2", "R3", "R4"], [step({"Start": True, "Step1Done": False, "Step2Done": False, "Reset": False}, {"Step1": True, "Step2": False, "Complete": False, "State": 1}), step({"Start": False, "Step1Done": True, "Step2Done": False, "Reset": False}, {"Step1": False, "Step2": True, "Complete": False, "State": 2}), step({"Start": False, "Step1Done": False, "Step2Done": True, "Reset": False}, {"Step1": False, "Step2": False, "Complete": True, "State": 3})], "Traverse the normal cycle.")],
        [test("ignore_wrong_completion_and_reset", ["R4", "R5"], [step({"Start": False, "Step1Done": True, "Step2Done": True, "Reset": False}, {"Step1": False, "Step2": False, "Complete": False, "State": 0}), step({"Start": True, "Step1Done": False, "Step2Done": False, "Reset": False}, {"Step1": True, "Step2": False, "Complete": False, "State": 1}), step({"Start": False, "Step1Done": False, "Step2Done": False, "Reset": True}, {"Step1": False, "Step2": False, "Complete": False, "State": 0})], "Ignore completion signals in idle and reset from an active state.")],
        internal_vars=[],
        iec_features=["FUNCTION_BLOCK", "BOOL", "INT", "CASE", "state machine", "retained output"],
        complexity={"retained_state": 1, "transitions": 4, "stateful_blocks": 0, "interactions": 1, "horizon_scans": 4},
    )
)

add(
    task(
        "C08_M01_branching_sorter",
        "Branching item sorter sequence",
        "C08",
        "medium",
        [var("ItemPresent", "BOOL", "Item at inspection point"), var("RejectClass", "BOOL", "Item classified for rejection"), var("TransferDone", "BOOL", "Transfer completed"), var("Reset", "BOOL", "Reset sequence")],
        [var("Inspect", "BOOL", "Inspection active"), var("AcceptGate", "BOOL", "Accept path selected"), var("RejectGate", "BOOL", "Reject path selected"), var("State", "INT", "0 wait, 1 inspect, 2 accept, 3 reject")],
        [
            req("ItemPresent in wait state shall enter inspection.", "G((State=0 AND ItemPresent AND !Reset) -> X(State=1))"),
            req("Inspection shall branch to reject when RejectClass is TRUE and to accept otherwise.", "G((State=1 AND RejectClass) -> X(State=3)) AND G((State=1 AND !RejectClass) -> X(State=2))"),
            req("TransferDone in either transfer state shall return to wait.", "G(((State=2 OR State=3) AND TransferDone) -> X(State=0))"),
            req("Inspect, AcceptGate, and RejectGate shall be mutually exclusive and match State.", "G(outputs_match_sorter_state)", True),
            req("Reset shall return to wait and close both gates.", "G(Reset -> (State=0 AND !Inspect AND !AcceptGate AND !RejectGate))", True),
        ],
        """IF Reset THEN
    State := 0;
ELSE
    CASE State OF
        0: IF ItemPresent THEN State := 1; END_IF;
        1: IF RejectClass THEN State := 3; ELSE State := 2; END_IF;
        2: IF TransferDone THEN State := 0; END_IF;
        3: IF TransferDone THEN State := 0; END_IF;
        ELSE State := 0;
    END_CASE;
END_IF;
Inspect := State = 1;
AcceptGate := State = 2;
RejectGate := State = 3;""",
        [test("accept_branch", ["R1", "R2", "R3"], [step({"ItemPresent": True, "RejectClass": False, "TransferDone": False, "Reset": False}, {"Inspect": True, "AcceptGate": False, "RejectGate": False, "State": 1}), step({"ItemPresent": True, "RejectClass": False, "TransferDone": False, "Reset": False}, {"Inspect": False, "AcceptGate": True, "RejectGate": False, "State": 2}), step({"ItemPresent": False, "RejectClass": False, "TransferDone": True, "Reset": False}, {"Inspect": False, "AcceptGate": False, "RejectGate": False, "State": 0})], "Take the accept branch and return.")],
        [test("reject_branch_and_reset", ["R2", "R4", "R5"], [step({"ItemPresent": True, "RejectClass": True, "TransferDone": False, "Reset": False}, {"Inspect": True, "AcceptGate": False, "RejectGate": False, "State": 1}), step({"ItemPresent": True, "RejectClass": True, "TransferDone": False, "Reset": False}, {"Inspect": False, "AcceptGate": False, "RejectGate": True, "State": 3}), step({"ItemPresent": False, "RejectClass": False, "TransferDone": False, "Reset": True}, {"Inspect": False, "AcceptGate": False, "RejectGate": False, "State": 0})], "Take the reject branch and reset safely.")],
        iec_features=["FUNCTION_BLOCK", "BOOL", "INT", "CASE", "branching state machine"],
        complexity={"retained_state": 1, "transitions": 5, "stateful_blocks": 0, "interactions": 2, "horizon_scans": 4},
    )
)

add(
    task(
        "C08_M02_fill_mix_drain",
        "Fill-mix-drain sequence",
        "C08",
        "medium",
        [var("Start", "BOOL", "Start batch"), var("HighLevel", "BOOL", "Vessel high level"), var("MixDone", "BOOL", "Mixing completion"), var("LowLevel", "BOOL", "Vessel low level"), var("Abort", "BOOL", "Abort batch")],
        [var("FillValve", "BOOL", "Fill command"), var("Mixer", "BOOL", "Mixer command"), var("DrainValve", "BOOL", "Drain command"), var("Complete", "BOOL", "Batch completion pulse"), var("State", "INT", "0 idle, 1 fill, 2 mix, 3 drain")],
        [
            req("Start in idle shall enter fill and open only FillValve.", "G((State=0 AND Start AND !Abort) -> X(State=1))"),
            req("HighLevel shall transition fill to mix; MixDone transitions mix to drain.", "G((State=1 AND HighLevel)->X(State=2)) AND G((State=2 AND MixDone)->X(State=3))"),
            req("LowLevel in drain shall return to idle and pulse Complete for one scan.", "G((State=3 AND LowLevel AND !Abort) -> X(State=0))"),
            req("FillValve, Mixer, and DrainValve shall be mutually exclusive and correspond to State.", "G(outputs_match_batch_state)", True),
            req("Abort shall immediately return to idle, close all actuators, and suppress Complete.", "G(Abort -> (State=0 AND !FillValve AND !Mixer AND !DrainValve AND !Complete))", True),
        ],
        """Complete := FALSE;
IF Abort THEN
    State := 0;
ELSE
    CASE State OF
        0: IF Start THEN State := 1; END_IF;
        1: IF HighLevel THEN State := 2; END_IF;
        2: IF MixDone THEN State := 3; END_IF;
        3: IF LowLevel THEN State := 0; Complete := TRUE; END_IF;
        ELSE State := 0;
    END_CASE;
END_IF;
FillValve := State = 1;
Mixer := State = 2;
DrainValve := State = 3;""",
        [test("normal_batch", ["R1", "R2", "R3", "R4"], [step({"Start": True, "HighLevel": False, "MixDone": False, "LowLevel": False, "Abort": False}, {"FillValve": True, "Mixer": False, "DrainValve": False, "Complete": False, "State": 1}), step({"Start": False, "HighLevel": True, "MixDone": False, "LowLevel": False, "Abort": False}, {"FillValve": False, "Mixer": True, "DrainValve": False, "Complete": False, "State": 2}), step({"Start": False, "HighLevel": False, "MixDone": True, "LowLevel": False, "Abort": False}, {"FillValve": False, "Mixer": False, "DrainValve": True, "Complete": False, "State": 3}), step({"Start": False, "HighLevel": False, "MixDone": False, "LowLevel": True, "Abort": False}, {"FillValve": False, "Mixer": False, "DrainValve": False, "Complete": True, "State": 0})], "Traverse all batch stages.")],
        [test("abort_each_active_stage", ["R5"], [step({"Start": True, "HighLevel": False, "MixDone": False, "LowLevel": False, "Abort": False}, {"FillValve": True, "Mixer": False, "DrainValve": False, "Complete": False, "State": 1}), step({"Start": False, "HighLevel": False, "MixDone": False, "LowLevel": False, "Abort": True}, {"FillValve": False, "Mixer": False, "DrainValve": False, "Complete": False, "State": 0})], "Abort from an active stage.")],
        iec_features=["FUNCTION_BLOCK", "BOOL", "INT", "CASE", "sequential control", "priority abort"],
        complexity={"retained_state": 1, "transitions": 5, "stateful_blocks": 0, "interactions": 3, "fault_modes": 1, "horizon_scans": 5},
    )
)

add(
    task(
        "C08_H01_pause_resume_abort_sequence",
        "Pause/resume sequence with abort recovery",
        "C08",
        "hard",
        [var("Start", "BOOL", "Start sequence"), var("Advance", "BOOL", "Advance current step"), var("Pause", "BOOL", "Pause active step"), var("Resume", "BOOL", "Resume paused step"), var("Abort", "BOOL", "Abort sequence"), var("Reset", "BOOL", "Clear aborted state")],
        [var("Step1", "BOOL", "Step 1 command"), var("Step2", "BOOL", "Step 2 command"), var("Paused", "BOOL", "Sequence paused"), var("Aborted", "BOOL", "Abort latched"), var("State", "INT", "0 idle, 1 step1, 2 step2, 3 done")],
        [
            req("Start shall begin Step 1 only when idle and not Aborted.", "G((State=0 AND Start AND !Aborted AND !Abort) -> X(State=1))"),
            req("Advance shall move Step 1 to Step 2 and Step 2 to done only while not Paused.", "G((Advance AND !Paused AND State=1)->X(State=2)) AND G((Advance AND !Paused AND State=2)->X(State=3))"),
            req("Pause shall suppress active step outputs without losing State; Resume clears Paused.", "G(Paused -> (!Step1 AND !Step2))"),
            req("Abort shall return State to idle, suppress outputs, clear Paused, and latch Aborted.", "G(Abort -> (State=0 AND !Step1 AND !Step2 AND !Paused AND Aborted))", True),
            req("Reset shall clear Aborted only while Start, Advance, Pause, Resume, and Abort are all FALSE.", "G(qualified_reset -> !Aborted)"),
        ],
        """IF Abort THEN
    State := 0;
    Paused := FALSE;
    Aborted := TRUE;
ELSIF Reset AND (NOT Start) AND (NOT Advance) AND (NOT Pause) AND (NOT Resume) THEN
    Aborted := FALSE;
ELSIF NOT Aborted THEN
    IF Pause AND ((State = 1) OR (State = 2)) THEN
        Paused := TRUE;
    ELSIF Resume THEN
        Paused := FALSE;
    END_IF;
    IF NOT Paused THEN
        CASE State OF
            0: IF Start THEN State := 1; END_IF;
            1: IF Advance THEN State := 2; END_IF;
            2: IF Advance THEN State := 3; END_IF;
            3: State := 3;
            ELSE State := 0;
        END_CASE;
    END_IF;
END_IF;
Step1 := (State = 1) AND (NOT Paused) AND (NOT Aborted);
Step2 := (State = 2) AND (NOT Paused) AND (NOT Aborted);""",
        [test("pause_resume", ["R1", "R2", "R3"], [step({"Start": True, "Advance": False, "Pause": False, "Resume": False, "Abort": False, "Reset": False}, {"Step1": True, "Step2": False, "Paused": False, "Aborted": False, "State": 1}), step({"Start": False, "Advance": False, "Pause": True, "Resume": False, "Abort": False, "Reset": False}, {"Step1": False, "Step2": False, "Paused": True, "Aborted": False, "State": 1}), step({"Start": False, "Advance": True, "Pause": False, "Resume": False, "Abort": False, "Reset": False}, {"Step1": False, "Step2": False, "Paused": True, "Aborted": False, "State": 1}), step({"Start": False, "Advance": False, "Pause": False, "Resume": True, "Abort": False, "Reset": False}, {"Step1": True, "Step2": False, "Paused": False, "Aborted": False, "State": 1}), step({"Start": False, "Advance": True, "Pause": False, "Resume": False, "Abort": False, "Reset": False}, {"Step1": False, "Step2": True, "Paused": False, "Aborted": False, "State": 2})], "Pause without losing state, resume, and advance.")],
        [test("abort_and_qualified_reset", ["R4", "R5"], [step({"Start": True, "Advance": False, "Pause": False, "Resume": False, "Abort": False, "Reset": False}, {"Step1": True, "Step2": False, "Paused": False, "Aborted": False, "State": 1}), step({"Start": False, "Advance": False, "Pause": False, "Resume": False, "Abort": True, "Reset": False}, {"Step1": False, "Step2": False, "Paused": False, "Aborted": True, "State": 0}), step({"Start": True, "Advance": False, "Pause": False, "Resume": False, "Abort": False, "Reset": True}, {"Step1": False, "Step2": False, "Paused": False, "Aborted": True, "State": 0}), step({"Start": False, "Advance": False, "Pause": False, "Resume": False, "Abort": False, "Reset": True}, {"Step1": False, "Step2": False, "Paused": False, "Aborted": False, "State": 0})], "Abort, reject reset with Start held, and accept a qualified reset.")],
        iec_features=["FUNCTION_BLOCK", "BOOL", "INT", "CASE", "retained state", "pause resume", "abort lockout"],
        complexity={"retained_state": 3, "transitions": 7, "stateful_blocks": 0, "interactions": 6, "fault_modes": 2, "horizon_scans": 8},
    )
)

add(
    task(
        "C08_H02_timed_sequence_fault",
        "State sequence with per-stage timeout",
        "C08",
        "hard",
        [var("Start", "BOOL", "Start sequence"), var("Sensor1", "BOOL", "Stage 1 completion sensor"), var("Sensor2", "BOOL", "Stage 2 completion sensor"), var("Stop", "BOOL", "Stop and reset-to-idle command"), var("ResetFault", "BOOL", "Fault reset")],
        [var("Actuator1", "BOOL", "Stage 1 actuator"), var("Actuator2", "BOOL", "Stage 2 actuator"), var("Complete", "BOOL", "Completion pulse"), var("Fault", "BOOL", "Latched timeout fault"), var("State", "INT", "0 idle, 1 stage1, 2 stage2")],
        [
            req("Start in idle shall enter stage 1 and energize only Actuator1.", "G((State=0 AND Start AND !Fault AND !Stop)->X(State=1))"),
            req("Sensor1 shall transition stage 1 to stage 2; Sensor2 shall complete stage 2 and return idle.", "G((State=1 AND Sensor1)->X(State=2)) AND G((State=2 AND Sensor2)->X(State=0))"),
            req("Either stage remaining incomplete for 500 ms shall latch Fault and return idle with both actuators off.", "G(stage_timeout -> (Fault AND State=0 AND !Actuator1 AND !Actuator2))", True),
            req("Stop shall return idle and turn both actuators off without clearing Fault.", "G(Stop -> (State=0 AND !Actuator1 AND !Actuator2))", True),
            req("ResetFault clears Fault only while Stop is TRUE and Start is FALSE.", "G((ResetFault AND Stop AND !Start)->!Fault)"),
            req("Complete shall pulse only on the stage-2-to-idle completion transition.", "G(Complete = (prev(State)=2 AND Sensor2 AND !Stop AND !Fault))"),
        ],
        """Complete := FALSE;
StageTimeout(IN := (State = 1) OR (State = 2), PT := T#500ms);
IF Stop THEN
    State := 0;
    IF ResetFault AND (NOT Start) THEN
        Fault := FALSE;
    END_IF;
ELSIF StageTimeout.Q THEN
    Fault := TRUE;
    State := 0;
ELSIF NOT Fault THEN
    CASE State OF
        0: IF Start THEN State := 1; END_IF;
        1: IF Sensor1 THEN State := 2; END_IF;
        2: IF Sensor2 THEN State := 0; Complete := TRUE; END_IF;
        ELSE State := 0;
    END_CASE;
END_IF;
Actuator1 := (State = 1) AND (NOT Fault);
Actuator2 := (State = 2) AND (NOT Fault);""",
        [test("normal_fast_sequence", ["R1", "R2", "R6"], [step({"Start": True, "Sensor1": False, "Sensor2": False, "Stop": False, "ResetFault": False}, {"Actuator1": True, "Actuator2": False, "Complete": False, "Fault": False, "State": 1}), step({"Start": False, "Sensor1": True, "Sensor2": False, "Stop": False, "ResetFault": False}, {"Actuator1": False, "Actuator2": True, "Complete": False, "Fault": False, "State": 2}), step({"Start": False, "Sensor1": False, "Sensor2": True, "Stop": False, "ResetFault": False}, {"Actuator1": False, "Actuator2": False, "Complete": True, "Fault": False, "State": 0})], "Complete both stages before timeout.")],
        [test("stage_timeout_and_reset", ["R3", "R4", "R5"], [step({"Start": True, "Sensor1": False, "Sensor2": False, "Stop": False, "ResetFault": False}, {"Actuator1": False, "Actuator2": False, "Complete": False, "Fault": True, "State": 0}, repeat=8, check="last_only"), step({"Start": True, "Sensor1": False, "Sensor2": False, "Stop": True, "ResetFault": True}, {"Actuator1": False, "Actuator2": False, "Complete": False, "Fault": True, "State": 0}), step({"Start": False, "Sensor1": False, "Sensor2": False, "Stop": True, "ResetFault": True}, {"Actuator1": False, "Actuator2": False, "Complete": False, "Fault": False, "State": 0})], "Time out, enforce safe outputs, and require a qualified reset.")],
        internal_vars=["StageTimeout : TON;"],
        iec_features=["FUNCTION_BLOCK", "BOOL", "INT", "TIME", "TON", "CASE", "state machine", "timeout fault"],
        assumptions=["The runtime scan period is 100 ms.", "Sensor completion is expected within 500 ms of entering each stage.", "Each test starts from a fresh function-block instance."],
        complexity={"retained_state": 3, "transitions": 8, "stateful_blocks": 1, "interactions": 6, "fault_modes": 2, "horizon_scans": 10},
    )
)


# C09 -- Alarms and fault recovery ----------------------------------------------------
add(
    task(
        "C09_E01_latched_alarm_acknowledge",
        "Latched alarm with acknowledge and reset",
        "C09",
        "easy",
        [var("AlarmCondition", "BOOL", "Active alarm condition"), var("Acknowledge", "BOOL", "Operator acknowledgement"), var("Reset", "BOOL", "Alarm reset")],
        [var("AlarmActive", "BOOL", "Latched alarm status"), var("AlarmUnacked", "BOOL", "Alarm requires acknowledgement")],
        [
            req("AlarmCondition shall latch AlarmActive and AlarmUnacked TRUE.", "G(AlarmCondition -> (AlarmActive AND AlarmUnacked))"),
            req("Acknowledge may clear AlarmUnacked while AlarmActive remains latched.", "G((Acknowledge AND !AlarmCondition) -> !AlarmUnacked)"),
            req("Reset shall clear both outputs only while AlarmCondition is FALSE.", "G((Reset AND !AlarmCondition) -> (!AlarmActive AND !AlarmUnacked))"),
        ],
        """IF AlarmCondition THEN
    AlarmActive := TRUE;
    AlarmUnacked := TRUE;
ELSE
    IF Acknowledge THEN
        AlarmUnacked := FALSE;
    END_IF;
    IF Reset THEN
        AlarmActive := FALSE;
        AlarmUnacked := FALSE;
    END_IF;
END_IF;""",
        [test("raise_and_acknowledge", ["R1", "R2"], [step({"AlarmCondition": True, "Acknowledge": False, "Reset": False}, {"AlarmActive": True, "AlarmUnacked": True}), step({"AlarmCondition": False, "Acknowledge": True, "Reset": False}, {"AlarmActive": True, "AlarmUnacked": False})], "Raise and acknowledge an alarm without resetting it.")],
        [test("qualified_reset", ["R1", "R3"], [step({"AlarmCondition": True, "Acknowledge": False, "Reset": False}, {"AlarmActive": True, "AlarmUnacked": True}), step({"AlarmCondition": True, "Acknowledge": False, "Reset": True}, {"AlarmActive": True, "AlarmUnacked": True}), step({"AlarmCondition": False, "Acknowledge": False, "Reset": True}, {"AlarmActive": False, "AlarmUnacked": False})], "Reject reset while active and accept it after the condition clears.")],
        iec_features=["FUNCTION_BLOCK", "BOOL", "retained alarm", "IF", "acknowledge", "qualified reset"],
        complexity={"retained_state": 2, "transitions": 4, "interactions": 3, "fault_modes": 1, "horizon_scans": 3},
    )
)

add(
    task(
        "C09_M01_high_high_alarm_priority",
        "High and high-high alarm priority",
        "C09",
        "medium",
        [var("Value", "REAL", "Measured process value"), var("HighLimit", "REAL", "High threshold"), var("HighHighLimit", "REAL", "High-high threshold"), var("Reset", "BOOL", "Latched alarm reset")],
        [var("HighAlarm", "BOOL", "Latched high alarm"), var("HighHighAlarm", "BOOL", "Latched high-high alarm"), var("Shutdown", "BOOL", "Latched shutdown command")],
        [
            req("Value at or above HighLimit shall latch HighAlarm.", "G((Value>=HighLimit) -> HighAlarm)"),
            req("Value at or above HighHighLimit shall latch both alarms and Shutdown.", "G((Value>=HighHighLimit) -> (HighAlarm AND HighHighAlarm AND Shutdown))", True),
            req("A high alarm below HighHighLimit shall not by itself assert Shutdown.", "G((Value>=HighLimit AND Value<HighHighLimit AND !HighHighAlarm) -> !Shutdown)"),
            req("Reset shall clear all latched outputs only below HighLimit.", "G((Reset AND Value<HighLimit) -> (!HighAlarm AND !HighHighAlarm AND !Shutdown))"),
        ],
        """IF Value >= HighHighLimit THEN
    HighAlarm := TRUE;
    HighHighAlarm := TRUE;
    Shutdown := TRUE;
ELSIF Value >= HighLimit THEN
    HighAlarm := TRUE;
END_IF;
IF Reset AND (Value < HighLimit) THEN
    HighAlarm := FALSE;
    HighHighAlarm := FALSE;
    Shutdown := FALSE;
END_IF;""",
        [test("high_then_high_high", ["R1", "R2", "R3"], [step({"Value": 75.0, "HighLimit": 70.0, "HighHighLimit": 90.0, "Reset": False}, {"HighAlarm": True, "HighHighAlarm": False, "Shutdown": False}), step({"Value": 95.0, "HighLimit": 70.0, "HighHighLimit": 90.0, "Reset": False}, {"HighAlarm": True, "HighHighAlarm": True, "Shutdown": True})], "Exercise both alarm levels and shutdown priority.")],
        [test("latch_and_qualified_reset", ["R2", "R4"], [step({"Value": 95.0, "HighLimit": 70.0, "HighHighLimit": 90.0, "Reset": False}, {"HighAlarm": True, "HighHighAlarm": True, "Shutdown": True}), step({"Value": 80.0, "HighLimit": 70.0, "HighHighLimit": 90.0, "Reset": True}, {"HighAlarm": True, "HighHighAlarm": True, "Shutdown": True}), step({"Value": 60.0, "HighLimit": 70.0, "HighHighLimit": 90.0, "Reset": True}, {"HighAlarm": False, "HighHighAlarm": False, "Shutdown": False})], "Preserve latches until the process is below the high limit.")],
        iec_features=["FUNCTION_BLOCK", "BOOL", "REAL", "comparisons", "retained alarms", "priority"],
        assumptions=["HighHighLimit is greater than HighLimit.", "Each test starts from a fresh function-block instance."],
        complexity={"retained_state": 3, "transitions": 4, "stateful_blocks": 0, "interactions": 4, "fault_modes": 2, "horizon_scans": 3},
    )
)

add(
    task(
        "C09_M02_qualified_sensor_disagreement",
        "Time-qualified sensor disagreement alarm",
        "C09",
        "medium",
        [var("SensorA", "REAL", "First sensor value"), var("SensorB", "REAL", "Second sensor value"), var("MaxDifference", "REAL", "Allowed absolute difference"), var("Enable", "BOOL", "Monitoring enable"), var("Reset", "BOOL", "Alarm reset")],
        [var("Alarm", "BOOL", "Latched disagreement alarm"), var("Disagreeing", "BOOL", "Current disagreement status")],
        [
            req("Disagreeing shall be TRUE exactly when monitoring is enabled and the absolute difference exceeds MaxDifference.", "G(Disagreeing = (Enable AND ABS(SensorA-SensorB)>MaxDifference))"),
            req("A disagreement lasting 300 ms shall latch Alarm.", "G(within(3, Disagreeing, Alarm))"),
            req("A shorter disagreement shall not latch Alarm.", "G((Disagreeing AND duration(Disagreeing)<3) -> !Alarm)"),
            req("Reset shall clear Alarm only while no disagreement is present.", "G((Reset AND !Disagreeing) -> !Alarm)"),
        ],
        """Disagreeing := Enable AND (ABS(SensorA - SensorB) > MaxDifference);
DisagreeTimer(IN := Disagreeing, PT := T#300ms);
IF DisagreeTimer.Q THEN
    Alarm := TRUE;
ELSIF Reset AND (NOT Disagreeing) THEN
    Alarm := FALSE;
END_IF;""",
        [test("short_then_sustained_disagreement", ["R1", "R2", "R3"], [step({"SensorA": 10.0, "SensorB": 13.0, "MaxDifference": 2.0, "Enable": True, "Reset": False}, {"Alarm": False, "Disagreeing": True}, repeat=2), step({"SensorA": 10.0, "SensorB": 10.5, "MaxDifference": 2.0, "Enable": True, "Reset": False}, {"Alarm": False, "Disagreeing": False}), step({"SensorA": 10.0, "SensorB": 13.0, "MaxDifference": 2.0, "Enable": True, "Reset": False}, {"Alarm": True, "Disagreeing": True}, repeat=4, check="last_only")], "Reject a transient and accept a sustained disagreement; the activation scan precedes three elapsed scan intervals.")],
        [test("disable_and_reset", ["R1", "R2", "R4"], [step({"SensorA": 0.0, "SensorB": 5.0, "MaxDifference": 1.0, "Enable": True, "Reset": False}, {"Alarm": True, "Disagreeing": True}, repeat=4, check="last_only"), step({"SensorA": 0.0, "SensorB": 5.0, "MaxDifference": 1.0, "Enable": False, "Reset": True}, {"Alarm": False, "Disagreeing": False})], "Qualify the alarm across three elapsed intervals, then disable and reset it.")],
        internal_vars=["DisagreeTimer : TON;"],
        iec_features=["FUNCTION_BLOCK", "BOOL", "REAL", "TIME", "TON", "ABS", "retained alarm"],
        assumptions=["The runtime scan period is 100 ms.", "MaxDifference is non-negative.", "Each test starts from a fresh function-block instance."],
        complexity={"retained_state": 1, "transitions": 4, "stateful_blocks": 1, "interactions": 4, "fault_modes": 1, "horizon_scans": 6},
    )
)

add(
    task(
        "C09_H01_first_out_fault_recorder",
        "First-out fault recorder with deterministic priority",
        "C09",
        "hard",
        [var("FaultA", "BOOL", "Fault channel A"), var("FaultB", "BOOL", "Fault channel B"), var("FaultC", "BOOL", "Fault channel C"), var("Reset", "BOOL", "Recorder reset")],
        [var("AnyFault", "BOOL", "Current aggregate fault input"), var("LockedOut", "BOOL", "Latched lockout"), var("FirstFault", "INT", "First fault code: 0 none, 1 A, 2 B, 3 C")],
        [
            req("AnyFault shall equal the disjunction of all three fault inputs.", "G(AnyFault = (FaultA OR FaultB OR FaultC))"),
            req("The first observed fault shall latch LockedOut and its code in FirstFault.", "G((!LockedOut AND AnyFault) -> X(LockedOut AND FirstFault<>0))", True),
            req("Simultaneous first faults shall use priority A, then B, then C.", "G((!LockedOut AND FaultA)->X(FirstFault=1)) AND G((!LockedOut AND !FaultA AND FaultB)->X(FirstFault=2))"),
            req("Later faults shall not overwrite FirstFault while LockedOut is TRUE.", "G((LockedOut AND !qualified_reset) -> X(FirstFault=FirstFault))"),
            req("Reset shall clear LockedOut and FirstFault only when all fault inputs are FALSE.", "G((Reset AND !AnyFault) -> (!LockedOut AND FirstFault=0))"),
        ],
        """AnyFault := FaultA OR FaultB OR FaultC;
IF (NOT LockedOut) AND AnyFault THEN
    LockedOut := TRUE;
    IF FaultA THEN
        FirstFault := 1;
    ELSIF FaultB THEN
        FirstFault := 2;
    ELSE
        FirstFault := 3;
    END_IF;
ELSIF Reset AND (NOT AnyFault) THEN
    LockedOut := FALSE;
    FirstFault := 0;
END_IF;""",
        [test("record_and_preserve_first_fault", ["R1", "R2", "R4"], [step({"FaultA": False, "FaultB": True, "FaultC": False, "Reset": False}, {"AnyFault": True, "LockedOut": True, "FirstFault": 2}), step({"FaultA": True, "FaultB": False, "FaultC": False, "Reset": False}, {"AnyFault": True, "LockedOut": True, "FirstFault": 2}), step({"FaultA": False, "FaultB": False, "FaultC": False, "Reset": False}, {"AnyFault": False, "LockedOut": True, "FirstFault": 2})], "Record B first and prevent A from overwriting it.")],
        [test("simultaneous_priority_and_reset", ["R1", "R2", "R3", "R5"], [step({"FaultA": True, "FaultB": True, "FaultC": True, "Reset": False}, {"AnyFault": True, "LockedOut": True, "FirstFault": 1}), step({"FaultA": True, "FaultB": False, "FaultC": False, "Reset": True}, {"AnyFault": True, "LockedOut": True, "FirstFault": 1}), step({"FaultA": False, "FaultB": False, "FaultC": False, "Reset": True}, {"AnyFault": False, "LockedOut": False, "FirstFault": 0})], "Resolve simultaneous faults and require all inputs clear for reset.")],
        iec_features=["FUNCTION_BLOCK", "BOOL", "INT", "retained state", "priority encoding", "qualified reset"],
        complexity={"retained_state": 2, "transitions": 6, "stateful_blocks": 0, "interactions": 6, "fault_modes": 3, "horizon_scans": 4},
    )
)

add(
    task(
        "C09_H02_delayed_warning_trip_lockout",
        "Delayed warning with trip lockout and acknowledgement",
        "C09",
        "hard",
        [var("WarningCondition", "BOOL", "Warning-level condition"), var("TripCondition", "BOOL", "Immediate trip condition"), var("Enable", "BOOL", "Alarm system enable"), var("Acknowledge", "BOOL", "Operator acknowledgement"), var("Reset", "BOOL", "Qualified trip reset")],
        [var("Warning", "BOOL", "Time-qualified warning"), var("Trip", "BOOL", "Latched trip"), var("Unacked", "BOOL", "Unacknowledged active event"), var("LockedOut", "BOOL", "Equipment lockout")],
        [
            req("WarningCondition shall assert Warning only after it remains enabled for 300 ms.", "G(within(3, (Enable AND WarningCondition), Warning))"),
            req("TripCondition while enabled shall immediately latch Trip and LockedOut.", "G((Enable AND TripCondition) -> (Trip AND LockedOut))", True),
            req("A newly asserted Warning or Trip shall set Unacked.", "G((rose(Warning) OR rose(Trip)) -> Unacked)"),
            req("Acknowledge shall clear Unacked without clearing active Warning or latched Trip.", "G(Acknowledge -> !Unacked)"),
            req("Reset shall clear Trip and LockedOut only while both conditions and Enable are FALSE.", "G((Reset AND !Enable AND !WarningCondition AND !TripCondition) -> (!Trip AND !LockedOut))"),
            req("Disabling the system shall clear the non-latched Warning but not an existing Trip.", "G(!Enable -> !Warning)", True),
        ],
        """WarningTimer(IN := Enable AND WarningCondition, PT := T#300ms);
Warning := WarningTimer.Q;
IF Enable AND TripCondition THEN
    Trip := TRUE;
    LockedOut := TRUE;
END_IF;
IF (Warning AND (NOT PrevWarning)) OR (Trip AND (NOT PrevTrip)) THEN
    Unacked := TRUE;
END_IF;
IF Acknowledge THEN
    Unacked := FALSE;
END_IF;
IF Reset AND (NOT Enable) AND (NOT WarningCondition) AND (NOT TripCondition) THEN
    Trip := FALSE;
    LockedOut := FALSE;
END_IF;
PrevWarning := Warning;
PrevTrip := Trip;""",
        [test("warning_delay_and_ack", ["R1", "R3", "R4"], [step({"WarningCondition": True, "TripCondition": False, "Enable": True, "Acknowledge": False, "Reset": False}, {"Warning": True, "Trip": False, "Unacked": True, "LockedOut": False}, repeat=4, check="last_only"), step({"WarningCondition": True, "TripCondition": False, "Enable": True, "Acknowledge": True, "Reset": False}, {"Warning": True, "Trip": False, "Unacked": False, "LockedOut": False})], "Qualify a warning across three elapsed intervals and acknowledge it.")],
        [test("trip_disable_and_qualified_reset", ["R2", "R3", "R4", "R5", "R6"], [step({"WarningCondition": False, "TripCondition": True, "Enable": True, "Acknowledge": False, "Reset": False}, {"Warning": False, "Trip": True, "Unacked": True, "LockedOut": True}), step({"WarningCondition": False, "TripCondition": False, "Enable": True, "Acknowledge": True, "Reset": True}, {"Warning": False, "Trip": True, "Unacked": False, "LockedOut": True}), step({"WarningCondition": False, "TripCondition": False, "Enable": False, "Acknowledge": False, "Reset": True}, {"Warning": False, "Trip": False, "Unacked": False, "LockedOut": False})], "Latch and acknowledge a trip, then apply a qualified disabled reset.")],
        internal_vars=["WarningTimer : TON;", "PrevWarning : BOOL;", "PrevTrip : BOOL;"],
        iec_features=["FUNCTION_BLOCK", "BOOL", "TIME", "TON", "edge memory", "alarm acknowledgement", "trip lockout"],
        assumptions=["The runtime scan period is 100 ms.", "Acknowledge has priority over a new Unacked indication within the same scan.", "Each test starts from a fresh function-block instance."],
        complexity={"retained_state": 5, "transitions": 8, "stateful_blocks": 1, "interactions": 7, "fault_modes": 2, "horizon_scans": 7},
    )
)


# C10 -- Multi-device coordination ----------------------------------------------------
add(
    task(
        "C10_E01_master_follower_coordination",
        "Master-follower motor coordination",
        "C10",
        "easy",
        [var("RunRequest", "BOOL", "Request to run both motors"), var("MasterReady", "BOOL", "Master motor is available"), var("FollowerReady", "BOOL", "Follower motor is available")],
        [var("MasterRun", "BOOL", "Master motor command"), var("FollowerRun", "BOOL", "Follower motor command")],
        [
            req("MasterRun shall be TRUE exactly when RunRequest and MasterReady are TRUE.", "G(MasterRun = (RunRequest AND MasterReady))"),
            req("FollowerRun shall require RunRequest, MasterRun, and FollowerReady.", "G(FollowerRun = (RunRequest AND MasterRun AND FollowerReady))", True),
        ],
        """MasterRun := RunRequest AND MasterReady;
FollowerRun := RunRequest AND MasterRun AND FollowerReady;""",
        [test("both_ready", ["R1", "R2"], [step({"RunRequest": True, "MasterReady": True, "FollowerReady": True}, {"MasterRun": True, "FollowerRun": True}), step({"RunRequest": False, "MasterReady": True, "FollowerReady": True}, {"MasterRun": False, "FollowerRun": False})], "Start and stop both ready devices.")],
        [test("readiness_interlocks", ["R1", "R2"], [step({"RunRequest": True, "MasterReady": False, "FollowerReady": True}, {"MasterRun": False, "FollowerRun": False}), step({"RunRequest": True, "MasterReady": True, "FollowerReady": False}, {"MasterRun": True, "FollowerRun": False})], "Check master dependency and follower availability.")],
        iec_features=["FUNCTION_BLOCK", "BOOL", "AND", "coordinated outputs"],
        complexity={"retained_state": 0, "transitions": 0, "stateful_blocks": 0, "interactions": 2, "fault_modes": 2, "horizon_scans": 1},
    )
)

add(
    task(
        "C10_M01_alternating_pump_starts",
        "Alternating two-pump starts",
        "C10",
        "medium",
        [var("Demand", "BOOL", "Pump demand"), var("Pump1Available", "BOOL", "Pump 1 availability"), var("Pump2Available", "BOOL", "Pump 2 availability"), var("Reset", "BOOL", "Alternation reset")],
        [var("Pump1Run", "BOOL", "Pump 1 command"), var("Pump2Run", "BOOL", "Pump 2 command"), var("NextPump", "INT", "Preferred pump for next demand: 1 or 2"), var("Unavailable", "BOOL", "No available pump for demand")],
        [
            req("Each rising Demand shall start at most one available pump.", "G(!(Pump1Run AND Pump2Run))", True),
            req("When both pumps are available, successive demand episodes shall alternate the selected pump.", "G(alternating_rising_demands -> alternating_selected_pumps)"),
            req("If the preferred pump is unavailable, the other available pump shall run.", "G((Demand AND exactly_one_available) -> (Pump1Run OR Pump2Run))"),
            req("Unavailable shall be TRUE exactly when Demand is TRUE and neither pump is available.", "G(Unavailable = (Demand AND !Pump1Available AND !Pump2Available))"),
            req("Reset without Demand shall set NextPump to 1 and stop both pumps.", "G((Reset AND !Demand) -> (NextPump=1 AND !Pump1Run AND !Pump2Run))"),
        ],
        """IF (NextPump <> 1) AND (NextPump <> 2) THEN
    NextPump := 1;
END_IF;
IF Reset AND (NOT Demand) THEN
    NextPump := 1;
END_IF;
IF NOT Demand THEN
    Pump1Run := FALSE;
    Pump2Run := FALSE;
ELSIF NOT PrevDemand THEN
    IF (NextPump = 1) AND Pump1Available THEN
        Pump1Run := TRUE;
        Pump2Run := FALSE;
        NextPump := 2;
    ELSIF Pump2Available THEN
        Pump1Run := FALSE;
        Pump2Run := TRUE;
        NextPump := 1;
    ELSIF Pump1Available THEN
        Pump1Run := TRUE;
        Pump2Run := FALSE;
        NextPump := 2;
    ELSE
        Pump1Run := FALSE;
        Pump2Run := FALSE;
    END_IF;
END_IF;
Unavailable := Demand AND (NOT Pump1Available) AND (NOT Pump2Available);
PrevDemand := Demand;""",
        [test("two_alternating_demands", ["R1", "R2", "R5"], [step({"Demand": False, "Pump1Available": True, "Pump2Available": True, "Reset": True}, {"Pump1Run": False, "Pump2Run": False, "NextPump": 1, "Unavailable": False}), step({"Demand": True, "Pump1Available": True, "Pump2Available": True, "Reset": False}, {"Pump1Run": True, "Pump2Run": False, "NextPump": 2, "Unavailable": False}), step({"Demand": False, "Pump1Available": True, "Pump2Available": True, "Reset": False}, {"Pump1Run": False, "Pump2Run": False, "NextPump": 2, "Unavailable": False}), step({"Demand": True, "Pump1Available": True, "Pump2Available": True, "Reset": False}, {"Pump1Run": False, "Pump2Run": True, "NextPump": 1, "Unavailable": False})], "Alternate across two demand episodes.")],
        [test("fallback_and_unavailable", ["R1", "R3", "R4"], [step({"Demand": False, "Pump1Available": True, "Pump2Available": True, "Reset": True}, {"Pump1Run": False, "Pump2Run": False, "NextPump": 1, "Unavailable": False}), step({"Demand": True, "Pump1Available": False, "Pump2Available": True, "Reset": False}, {"Pump1Run": False, "Pump2Run": True, "NextPump": 1, "Unavailable": False}), step({"Demand": False, "Pump1Available": False, "Pump2Available": False, "Reset": False}, {"Pump1Run": False, "Pump2Run": False, "NextPump": 1, "Unavailable": False}), step({"Demand": True, "Pump1Available": False, "Pump2Available": False, "Reset": False}, {"Pump1Run": False, "Pump2Run": False, "NextPump": 1, "Unavailable": True})], "Fall back to pump 2 and report no available pump.")],
        internal_vars=["PrevDemand : BOOL;"],
        iec_features=["FUNCTION_BLOCK", "BOOL", "INT", "edge memory", "alternation", "availability fallback"],
        complexity={"retained_state": 4, "transitions": 6, "stateful_blocks": 1, "interactions": 5, "fault_modes": 2, "horizon_scans": 5},
    )
)

add(
    task(
        "C10_M02_lead_lag_demand_control",
        "Lead-lag pump demand control",
        "C10",
        "medium",
        [var("LowDemand", "BOOL", "At least one pump is required"), var("HighDemand", "BOOL", "Both pumps are requested"), var("LeadIsPump1", "BOOL", "Pump 1 is selected lead"), var("Pump1Available", "BOOL", "Pump 1 availability"), var("Pump2Available", "BOOL", "Pump 2 availability")],
        [var("Pump1Run", "BOOL", "Pump 1 command"), var("Pump2Run", "BOOL", "Pump 2 command"), var("CapacityShortfall", "BOOL", "Requested capacity cannot be supplied")],
        [
            req("With LowDemand only, the available selected lead pump shall run and the lag pump shall remain off.", "G((LowDemand AND !HighDemand AND lead_available) -> exactly_one_run)"),
            req("With HighDemand, every available pump shall run.", "G(HighDemand -> (Pump1Run=Pump1Available AND Pump2Run=Pump2Available))"),
            req("If the selected lead is unavailable under LowDemand, the available lag pump shall run.", "G((LowDemand AND !HighDemand AND !lead_available AND lag_available) -> lag_runs)"),
            req("No pump shall run when neither demand input is TRUE.", "G((!LowDemand AND !HighDemand) -> (!Pump1Run AND !Pump2Run))"),
            req("CapacityShortfall shall indicate zero available pumps for LowDemand or fewer than two for HighDemand.", "G(CapacityShortfall = insufficient_available_capacity)"),
        ],
        """Pump1Run := FALSE;
Pump2Run := FALSE;
IF HighDemand THEN
    Pump1Run := Pump1Available;
    Pump2Run := Pump2Available;
ELSIF LowDemand THEN
    IF LeadIsPump1 THEN
        IF Pump1Available THEN Pump1Run := TRUE;
        ELSIF Pump2Available THEN Pump2Run := TRUE;
        END_IF;
    ELSE
        IF Pump2Available THEN Pump2Run := TRUE;
        ELSIF Pump1Available THEN Pump1Run := TRUE;
        END_IF;
    END_IF;
END_IF;
CapacityShortfall := (HighDemand AND ((NOT Pump1Available) OR (NOT Pump2Available))) OR
    (LowDemand AND (NOT HighDemand) AND (NOT Pump1Available) AND (NOT Pump2Available));""",
        [test("lead_and_high_demand", ["R1", "R2"], [step({"LowDemand": True, "HighDemand": False, "LeadIsPump1": True, "Pump1Available": True, "Pump2Available": True}, {"Pump1Run": True, "Pump2Run": False, "CapacityShortfall": False}), step({"LowDemand": True, "HighDemand": True, "LeadIsPump1": True, "Pump1Available": True, "Pump2Available": True}, {"Pump1Run": True, "Pump2Run": True, "CapacityShortfall": False})], "Run the lead alone, then both pumps.")],
        [test("fallback_shortfall_and_idle", ["R3", "R4", "R5"], [step({"LowDemand": True, "HighDemand": False, "LeadIsPump1": True, "Pump1Available": False, "Pump2Available": True}, {"Pump1Run": False, "Pump2Run": True, "CapacityShortfall": False}), step({"LowDemand": True, "HighDemand": True, "LeadIsPump1": False, "Pump1Available": True, "Pump2Available": False}, {"Pump1Run": True, "Pump2Run": False, "CapacityShortfall": True}), step({"LowDemand": False, "HighDemand": False, "LeadIsPump1": False, "Pump1Available": True, "Pump2Available": True}, {"Pump1Run": False, "Pump2Run": False, "CapacityShortfall": False})], "Exercise fallback, high-demand shortfall, and idle.")],
        iec_features=["FUNCTION_BLOCK", "BOOL", "IF", "lead-lag coordination", "availability"],
        complexity={"retained_state": 0, "transitions": 0, "stateful_blocks": 0, "interactions": 7, "fault_modes": 2, "horizon_scans": 1},
    )
)

add(
    task(
        "C10_H01_duty_standby_failover",
        "Duty-standby pump feedback failover",
        "C10",
        "hard",
        [var("Demand", "BOOL", "Pump demand"), var("DutyIsPump1", "BOOL", "Selected duty pump"), var("Pump1Available", "BOOL", "Pump 1 availability"), var("Pump2Available", "BOOL", "Pump 2 availability"), var("Pump1Feedback", "BOOL", "Pump 1 running feedback"), var("Pump2Feedback", "BOOL", "Pump 2 running feedback"), var("Reset", "BOOL", "Failure reset")],
        [var("Pump1Run", "BOOL", "Pump 1 command"), var("Pump2Run", "BOOL", "Pump 2 command"), var("FailoverActive", "BOOL", "Standby is serving demand"), var("Failure", "BOOL", "Latched inability to establish running feedback")],
        [
            req("A new Demand shall command the available duty pump, or the standby if the duty pump is unavailable.", "G(rose(Demand) -> selected_available_pump_runs)"),
            req("If the commanded pump lacks feedback for 300 ms, control shall transfer to an available standby pump.", "G(command_without_feedback_for_3 -> standby_runs)"),
            req("Both run commands shall never be TRUE simultaneously.", "G(!(Pump1Run AND Pump2Run))", True),
            req("Failure shall latch if demand cannot be served by an available pump with feedback after failover.", "G(unserved_after_failover -> Failure)", True),
            req("Demand FALSE shall stop both pumps; Reset may clear Failure only with Demand FALSE.", "G(!Demand -> (!Pump1Run AND !Pump2Run)) AND G((Reset AND !Demand)->!Failure)"),
        ],
        """DutyNoFeedback(IN := Demand AND (NOT FailoverActive) AND ((Pump1Run AND (NOT Pump1Feedback)) OR (Pump2Run AND (NOT Pump2Feedback))), PT := T#300ms);
StandbyNoFeedback(IN := Demand AND FailoverActive AND ((Pump1Run AND (NOT Pump1Feedback)) OR (Pump2Run AND (NOT Pump2Feedback))), PT := T#300ms);
IF NOT Demand THEN
    Pump1Run := FALSE;
    Pump2Run := FALSE;
    FailoverActive := FALSE;
    IF Reset THEN Failure := FALSE; END_IF;
ELSIF NOT PrevDemand THEN
    IF DutyIsPump1 AND Pump1Available THEN
        Pump1Run := TRUE; Pump2Run := FALSE;
    ELSIF (NOT DutyIsPump1) AND Pump2Available THEN
        Pump1Run := FALSE; Pump2Run := TRUE;
    ELSIF Pump1Available THEN
        Pump1Run := TRUE; Pump2Run := FALSE; FailoverActive := TRUE;
    ELSIF Pump2Available THEN
        Pump1Run := FALSE; Pump2Run := TRUE; FailoverActive := TRUE;
    ELSE
        Failure := TRUE;
    END_IF;
ELSIF DutyNoFeedback.Q THEN
    IF Pump1Run AND Pump2Available AND (NOT FailoverActive) THEN
        Pump1Run := FALSE; Pump2Run := TRUE; FailoverActive := TRUE;
    ELSIF Pump2Run AND Pump1Available AND (NOT FailoverActive) THEN
        Pump1Run := TRUE; Pump2Run := FALSE; FailoverActive := TRUE;
    ELSE
        Pump1Run := FALSE; Pump2Run := FALSE; Failure := TRUE;
    END_IF;
ELSIF StandbyNoFeedback.Q THEN
    Pump1Run := FALSE; Pump2Run := FALSE; Failure := TRUE;
END_IF;
PrevDemand := Demand;""",
        [test("healthy_duty_start", ["R1", "R3", "R5"], [step({"Demand": True, "DutyIsPump1": True, "Pump1Available": True, "Pump2Available": True, "Pump1Feedback": True, "Pump2Feedback": False, "Reset": False}, {"Pump1Run": True, "Pump2Run": False, "FailoverActive": False, "Failure": False}), step({"Demand": False, "DutyIsPump1": True, "Pump1Available": True, "Pump2Available": True, "Pump1Feedback": False, "Pump2Feedback": False, "Reset": False}, {"Pump1Run": False, "Pump2Run": False, "FailoverActive": False, "Failure": False})], "Start a healthy duty pump and stop on demand loss.")],
        [test("feedback_timeout_failover_and_failure", ["R2", "R3", "R4", "R5"], [step({"Demand": True, "DutyIsPump1": True, "Pump1Available": True, "Pump2Available": True, "Pump1Feedback": False, "Pump2Feedback": False, "Reset": False}, {"Pump1Run": False, "Pump2Run": True, "FailoverActive": True, "Failure": False}, repeat=5, check="last_only"), step({"Demand": True, "DutyIsPump1": True, "Pump1Available": True, "Pump2Available": True, "Pump1Feedback": False, "Pump2Feedback": False, "Reset": False}, {"Pump1Run": False, "Pump2Run": False, "FailoverActive": True, "Failure": True}, repeat=4, check="last_only"), step({"Demand": False, "DutyIsPump1": True, "Pump1Available": True, "Pump2Available": True, "Pump1Feedback": False, "Pump2Feedback": False, "Reset": True}, {"Pump1Run": False, "Pump2Run": False, "FailoverActive": False, "Failure": False})], "Give the duty and standby pumps separate feedback windows, then reset while idle.")],
        internal_vars=["PrevDemand : BOOL;", "DutyNoFeedback : TON;", "StandbyNoFeedback : TON;"],
        iec_features=["FUNCTION_BLOCK", "BOOL", "TIME", "TON", "edge memory", "duty standby", "feedback failover"],
        assumptions=["The runtime scan period is 100 ms.", "Pump feedback is sampled at scan start.", "Each test starts from a fresh function-block instance."],
        complexity={"retained_state": 5, "transitions": 9, "stateful_blocks": 2, "interactions": 8, "fault_modes": 3, "horizon_scans": 10},
    )
)

add(
    task(
        "C10_H02_fair_resource_arbiter",
        "Fair two-client resource arbiter with emergency lockout",
        "C10",
        "hard",
        [var("RequestA", "BOOL", "Client A requests the resource"), var("RequestB", "BOOL", "Client B requests the resource"), var("Done", "BOOL", "Current client releases the resource"), var("Emergency", "BOOL", "Emergency resource shutdown"), var("Reset", "BOOL", "Lockout reset")],
        [var("GrantA", "BOOL", "Resource grant to client A"), var("GrantB", "BOOL", "Resource grant to client B"), var("Busy", "BOOL", "Resource has an active owner"), var("Turn", "INT", "Tie-break preference: 1 A, 2 B"), var("LockedOut", "BOOL", "Emergency lockout")],
        [
            req("GrantA and GrantB shall never be TRUE simultaneously.", "G(!(GrantA AND GrantB))", True),
            req("When idle, a single request shall receive the resource; simultaneous requests shall follow Turn.", "G((!Busy AND request_present AND !LockedOut) -> X(Busy))"),
            req("Done shall release the resource before a new owner is selected on a later scan.", "G(Done -> (!GrantA AND !GrantB AND !Busy))"),
            req("After A completes Turn shall prefer B, and after B completes Turn shall prefer A.", "G((Done AND GrantA)->X(Turn=2)) AND G((Done AND GrantB)->X(Turn=1))"),
            req("Emergency shall immediately revoke all grants and latch LockedOut.", "G(Emergency -> (!GrantA AND !GrantB AND !Busy AND LockedOut))", True),
            req("Reset shall clear LockedOut only while Emergency and both requests are FALSE.", "G((Reset AND !Emergency AND !RequestA AND !RequestB) -> !LockedOut)"),
        ],
        """IF (Turn <> 1) AND (Turn <> 2) THEN Turn := 1; END_IF;
IF Emergency THEN
    GrantA := FALSE; GrantB := FALSE; Busy := FALSE; LockedOut := TRUE;
ELSE
    IF Reset AND (NOT RequestA) AND (NOT RequestB) THEN
        LockedOut := FALSE;
    END_IF;
    IF NOT LockedOut THEN
        IF Done THEN
            IF Busy THEN
                IF GrantA THEN Turn := 2; ELSE Turn := 1; END_IF;
            END_IF;
            GrantA := FALSE; GrantB := FALSE; Busy := FALSE;
        ELSIF NOT Busy THEN
            IF RequestA AND RequestB THEN
                IF Turn = 1 THEN GrantA := TRUE; ELSE GrantB := TRUE; END_IF;
                Busy := TRUE;
            ELSIF RequestA THEN
                GrantA := TRUE; GrantB := FALSE; Busy := TRUE;
            ELSIF RequestB THEN
                GrantA := FALSE; GrantB := TRUE; Busy := TRUE;
            END_IF;
        END_IF;
    END_IF;
END_IF;""",
        [test("tie_break_and_release", ["R1", "R2", "R3", "R4"], [step({"RequestA": False, "RequestB": False, "Done": False, "Emergency": False, "Reset": True}, {"GrantA": False, "GrantB": False, "Busy": False, "Turn": 1, "LockedOut": False}), step({"RequestA": True, "RequestB": True, "Done": False, "Emergency": False, "Reset": False}, {"GrantA": True, "GrantB": False, "Busy": True, "Turn": 1, "LockedOut": False}), step({"RequestA": True, "RequestB": True, "Done": True, "Emergency": False, "Reset": False}, {"GrantA": False, "GrantB": False, "Busy": False, "Turn": 2, "LockedOut": False}), step({"RequestA": True, "RequestB": True, "Done": False, "Emergency": False, "Reset": False}, {"GrantA": False, "GrantB": True, "Busy": True, "Turn": 2, "LockedOut": False})], "Use A first, release for one scan, then prefer B.")],
        [test("emergency_and_qualified_reset", ["R1", "R5", "R6"], [step({"RequestA": True, "RequestB": False, "Done": False, "Emergency": False, "Reset": False}, {"GrantA": True, "GrantB": False, "Busy": True, "Turn": 1, "LockedOut": False}), step({"RequestA": True, "RequestB": False, "Done": False, "Emergency": True, "Reset": False}, {"GrantA": False, "GrantB": False, "Busy": False, "Turn": 1, "LockedOut": True}), step({"RequestA": True, "RequestB": False, "Done": False, "Emergency": False, "Reset": True}, {"GrantA": False, "GrantB": False, "Busy": False, "Turn": 1, "LockedOut": True}), step({"RequestA": False, "RequestB": False, "Done": False, "Emergency": False, "Reset": True}, {"GrantA": False, "GrantB": False, "Busy": False, "Turn": 1, "LockedOut": False})], "Revoke on emergency and require an idle reset.")],
        iec_features=["FUNCTION_BLOCK", "BOOL", "INT", "retained state", "mutual exclusion", "round-robin arbitration", "emergency lockout"],
        complexity={"retained_state": 5, "transitions": 9, "stateful_blocks": 0, "interactions": 8, "fault_modes": 2, "horizon_scans": 6},
    )
)


# v0.1's ten single-mechanism easy cases are retained in the archived pilot only.
# v0.2 replaces one easy task per category with a compositional challenge while
# keeping the total cost fixed at 50 scored task units.
TASKS[:] = [item for item in TASKS if item["difficulty"] != "easy"]
TASKS.extend(challenge_tasks(task, var, req, step, test))


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> None:
    if TASK_ROOT.exists():
        shutil.rmtree(TASK_ROOT)
    TASK_ROOT.mkdir(parents=True)

    default_engine_root = Path(__file__).resolve().parents[4] / "ISPSoft_CLI_Linux/src"
    engine_root = Path(os.environ.get("PLC_SCAN_ENGINE_ROOT", str(default_engine_root))).resolve()
    if not (engine_root / "deltaplc/engine.py").is_file():
        raise FileNotFoundError(
            f"sealed stress-oracle generation requires deltaplc engine at {engine_root}; "
            "set PLC_SCAN_ENGINE_ROOT to override"
        )

    manifest_records = []
    for item in TASKS:
        task_dir = TASK_ROOT / item["id"]
        task_dir.mkdir()
        reference = render_reference(item)
        metadata = {
            "schema_version": "1.0",
            "dataset_version": DATASET_VERSION,
            "id": item["id"],
            "title": item["title"],
            "category_id": item["category_id"],
            "category": item["category"],
            "difficulty": item["difficulty"],
            "iec_profile": "IEC-ST Core v1",
            "iec_features": item["iec_features"],
            "complexity": default_complexity(item),
            "interface": {"inputs": item["inputs"], "outputs": item["outputs"]},
            "scan": {
                "period_ms": item["scan_period_ms"],
                "input_sampling": "scan_start",
                "output_observation": "scan_end",
                "initialization": "fresh function-block instance for every test case",
            },
            "assumptions": item["assumptions"],
            "requirements": item["requirements"],
            "provenance": {
                "origin": "newly authored for IEC-ST-VerifyBench",
                "public_before_evaluation": False,
                "license": "research-internal; public license pending",
            },
            "review": {"author_review": "pending", "independent_review": "pending"},
        }
        (task_dir / "requirement.md").write_text(render_requirements(item), encoding="utf-8")
        (task_dir / "interface.st").write_text(render_interface(item), encoding="utf-8")
        (task_dir / "reference.st").write_text(reference, encoding="utf-8")
        write_json(task_dir / "metadata.json", metadata)
        write_json(task_dir / "properties.json", properties_for(item))
        write_json(task_dir / "tests_feedback.json", tests_for(item, hidden=False))
        write_json(task_dir / "tests_hidden.json", tests_for(item, hidden=True))
        write_json(task_dir / "tests_stress.json", build_stress_suite(item, reference, engine_root))

        control = negative_control(reference, item)
        control_dir = task_dir / "negative_control"
        control_dir.mkdir()
        (control_dir / "NC1.st").write_text(control.pop("program"), encoding="utf-8")
        write_json(
            control_dir / "index.json",
            {
                "purpose": "optional local oracle calibration; excluded from LLM evaluation",
                "count": 1,
                "controls": [control],
            },
        )
        write_json(
            task_dir / "validation_report.json",
            {
                "schema_version": "1.0",
                "task_id": item["id"],
                "structural": {"status": "not_run", "validator": "tools/validate_dataset.py"},
                "external": {
                    "matiec": {"status": "not_run", "version": None, "evidence": None},
                    "formal": {"status": "not_run", "version": None, "evidence": None},
                    "openplc": {"status": "not_run", "version": None, "evidence": None},
                },
                "negative_control": {"status": "not_run", "required_for_primary_experiment": False},
                "human_review": {"status": "pending", "reviewer": None},
            },
        )

        artifact_names = [
            "metadata.json",
            "requirement.md",
            "interface.st",
            "reference.st",
            "properties.json",
            "tests_feedback.json",
            "tests_hidden.json",
            "tests_stress.json",
            "negative_control/index.json",
            "negative_control/NC1.st",
        ]
        manifest_records.append(
            {
                "id": item["id"],
                "category_id": item["category_id"],
                "difficulty": item["difficulty"],
                "path": f"tasks/{item['id']}",
                "hashes": {name: sha256(task_dir / name) for name in artifact_names},
            }
        )

    with (ROOT / "manifest.jsonl").open("w", encoding="utf-8") as handle:
        for record in manifest_records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    write_json(
        ROOT / "dataset_summary.json",
        {
            "dataset": "IEC-ST-VerifyBench",
            "version": DATASET_VERSION,
            "primary_task_count": len(TASKS),
            "generation_opportunities_per_task": 10,
            "maximum_primary_candidate_programs": len(TASKS) * 10,
            "optional_negative_control_count": len(TASKS),
            "negative_controls_use_llm": False,
            "category_counts": dict(sorted(Counter(t["category_id"] for t in TASKS).items())),
            "difficulty_counts": dict(sorted(Counter(t["difficulty"] for t in TASKS).items())),
            "scoring_unit": "task",
            "primary_metric": "VerifiedSuccess@10",
        },
    )
    print(f"Built {len(TASKS)} primary tasks and {len(TASKS)} optional negative controls in {TASK_ROOT}")


if __name__ == "__main__":
    build()

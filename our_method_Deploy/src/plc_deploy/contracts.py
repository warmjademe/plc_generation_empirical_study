from __future__ import annotations

import ast
import itertools
import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from plc_loop.client import OpenAICompatibleClient, ProviderSettings, is_retryable_model_error


IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
SUPPORTED_TYPES = {"BOOL", "INT", "REAL"}
PROPERTY_TOKENS = {"AND", "OR", "NOT", "XOR", "TRUE", "FALSE"}
STATEFUL_WORDS = (
    "latch", "latched", "remain", "retained", "retain", "until",
    "hold", "persists", "persistent", "保持", "锁存", "直到",
)
SEMANTIC_AUDIT_VERSION = "deterministic-contract-semantics-v4"
CONTRACT_ATTEMPT_BUDGET = 10
CONTRACT_BLIND_REBUILD_STREAK = 3


class ContractError(ValueError):
    pass


class ContractInfrastructureError(RuntimeError):
    pass


def _contract_error_family(error: str) -> str:
    """Group diagnostics by repair target for evidence-triggered blind rebuilds."""
    patterns = (
        "lacks traceability coverage",
        "state/test contradiction",
        "property/test contradiction",
        "priority contradiction",
        "incomplete feedback priority coverage",
        "incomplete sealed priority coverage",
        "invalid semantic expression",
        "input mismatch",
        "output mismatch",
        "provider returned empty assistant content",
        "model exhausted its output-token limit",
    )
    lowered = error.casefold()
    for pattern in patterns:
        if pattern.casefold() in lowered:
            return pattern
    return error.split(":", 1)[0].strip().casefold()


def has_passed_semantic_audit(contract: dict[str, Any]) -> bool:
    """Return whether a normalized contract passed the current deterministic audit."""
    audit = contract.get("semantic_audit")
    traceability = audit.get("traceability") if isinstance(audit, dict) else None
    return (
        isinstance(audit, dict)
        and audit.get("status") == "passed"
        and audit.get("version") == SEMANTIC_AUDIT_VERSION
        and isinstance(traceability, dict)
        and traceability.get("status") == "passed"
        and int(traceability.get("requirements_covered", 0)) > 0
    )


def _extract_json(content: Any) -> dict[str, Any]:
    if not isinstance(content, str):
        raise ContractError("contract model returned non-text content")
    text = content.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1)
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            raise ContractError(f"contract model did not return JSON: {exc}") from exc
        try:
            value = json.loads(text[start:end + 1])
        except json.JSONDecodeError as nested:
            raise ContractError(f"contract JSON is invalid: {nested}") from nested
    if not isinstance(value, dict):
        raise ContractError("contract root must be a JSON object")
    return value


def _check_value(value: Any, typ: str, label: str) -> None:
    if typ == "BOOL" and not isinstance(value, bool):
        raise ContractError(f"{label} must be BOOL")
    if typ == "INT" and (not isinstance(value, int) or isinstance(value, bool)):
        raise ContractError(f"{label} must be INT")
    if typ == "REAL" and (not isinstance(value, (int, float)) or isinstance(value, bool)):
        raise ContractError(f"{label} must be REAL")


def _python_expression(expression: str) -> str:
    value = expression.strip()
    if not value:
        raise ContractError("empty semantic expression")
    value = value.replace("<>", "!=")
    value = re.sub(r"(?<![<>=!])=(?!=)", "==", value)
    for source, target in (
        ("TRUE", "True"), ("FALSE", "False"), ("AND", "and"),
        ("OR", "or"), ("NOT", "not"), ("XOR", "!="),
    ):
        value = re.sub(rf"\b{source}\b", target, value, flags=re.IGNORECASE)
    return value


def _evaluate_ast(node: ast.AST, values: dict[str, Any]) -> Any:
    if isinstance(node, ast.Expression):
        return _evaluate_ast(node.body, values)
    if isinstance(node, ast.Constant) and isinstance(node.value, (bool, int, float)):
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in values:
            raise ContractError(f"semantic expression has no value for {node.id}")
        return values[node.id]
    if isinstance(node, ast.UnaryOp):
        operand = _evaluate_ast(node.operand, values)
        if isinstance(node.op, ast.Not):
            return not bool(operand)
        if isinstance(node.op, ast.USub) and isinstance(operand, (int, float)):
            return -operand
    if isinstance(node, ast.BoolOp):
        items = [bool(_evaluate_ast(item, values)) for item in node.values]
        if isinstance(node.op, ast.And):
            return all(items)
        if isinstance(node.op, ast.Or):
            return any(items)
    if isinstance(node, ast.BinOp):
        left = _evaluate_ast(node.left, values)
        right = _evaluate_ast(node.right, values)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
    if isinstance(node, ast.Compare):
        left = _evaluate_ast(node.left, values)
        for operator, comparator in zip(node.ops, node.comparators):
            right = _evaluate_ast(comparator, values)
            if isinstance(operator, ast.Eq):
                passed = left == right
            elif isinstance(operator, ast.NotEq):
                passed = left != right
            elif isinstance(operator, ast.Lt):
                passed = left < right
            elif isinstance(operator, ast.LtE):
                passed = left <= right
            elif isinstance(operator, ast.Gt):
                passed = left > right
            elif isinstance(operator, ast.GtE):
                passed = left >= right
            else:
                raise ContractError("semantic expression uses an unsupported comparison")
            if not passed:
                return False
            left = right
        return True
    raise ContractError(
        f"semantic expression uses unsupported syntax: {type(node).__name__}"
    )


def _expression_identifiers(expression: str) -> set[str]:
    pieces = expression.split("->")
    identifiers: set[str] = set()
    for piece in pieces:
        try:
            tree = ast.parse(_python_expression(piece), mode="eval")
        except SyntaxError as exc:
            raise ContractError(f"invalid semantic expression {expression!r}: {exc.msg}") from exc
        identifiers.update(node.id for node in ast.walk(tree) if isinstance(node, ast.Name))
    return identifiers - {"True", "False"}


def _equality_identifiers(expression: str) -> set[str]:
    """Return identifiers participating in an explicit equality predicate."""
    identifiers: set[str] = set()
    for piece in expression.split("->"):
        try:
            tree = ast.parse(_python_expression(piece), mode="eval")
        except SyntaxError as exc:
            raise ContractError(f"invalid semantic expression {expression!r}: {exc.msg}") from exc
        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare) or not any(
                isinstance(operator, ast.Eq) for operator in node.ops
            ):
                continue
            identifiers.update(
                child.id for child in ast.walk(node) if isinstance(child, ast.Name)
            )
    return identifiers - {"True", "False"}


def _evaluate_expression(expression: str, values: dict[str, Any]) -> bool:
    implication = expression.split("->")
    if len(implication) == 2:
        return (not _evaluate_expression(implication[0], values)) or _evaluate_expression(
            implication[1], values
        )
    if len(implication) > 2:
        raise ContractError(f"semantic expression has multiple implications: {expression!r}")
    try:
        tree = ast.parse(_python_expression(expression), mode="eval")
    except SyntaxError as exc:
        raise ContractError(f"invalid semantic expression {expression!r}: {exc.msg}") from exc
    return bool(_evaluate_ast(tree, values))


def _stateful_outputs(requirements: list[dict[str, Any]], output_names: set[str]) -> set[str]:
    """Attribute retention words to the nearest output in the same requirement clause.

    A whole requirement can mention both combinational run outputs and a retained alarm.
    Marking every mentioned output as stateful in that situation creates a false latch.
    """
    required: set[str] = set()
    for requirement in requirements:
        text = str(requirement["text"])
        for clause in re.split(r"[.;；。\n]+", text):
            lowered = clause.casefold()
            word_positions = [
                match.start()
                for word in STATEFUL_WORDS
                for match in re.finditer(re.escape(word), lowered)
            ]
            output_positions = [
                (output, match.start())
                for output in output_names
                for match in re.finditer(rf"\b{re.escape(output)}\b", clause, re.IGNORECASE)
            ]
            for word_position in word_positions:
                if output_positions:
                    nearest_distance = min(abs(position - word_position) for _, position in output_positions)
                    required.update(
                        output for output, position in output_positions
                        if abs(position - word_position) == nearest_distance
                    )
    return required


def _normalize_state_rules(
    raw_rules: Any,
    *,
    input_names: set[str],
    outputs: list[dict[str, str]],
    requirements: list[dict[str, Any]],
    stateful_requirements: list[dict[str, Any]] | None,
    requirement_ids: set[str],
) -> list[dict[str, Any]]:
    if not isinstance(raw_rules, list):
        raise ContractError("state_rules must be a list")
    output_types = {item["name"]: item["type"] for item in outputs}
    output_names = set(output_types)
    required_stateful = _stateful_outputs(
        stateful_requirements if stateful_requirements is not None else requirements,
        output_names,
    )
    normalized: list[dict[str, Any]] = []
    governed: set[str] = set()
    for index, item in enumerate(raw_rules, 1):
        try:
            variable = str(item["variable"])
            initial = item["initial"]
            set_when = str(item["set_when"]).strip()
            clear_when = str(item["clear_when"]).strip()
            priority = str(item["priority"]).lower()
            otherwise = str(item.get("otherwise", "hold")).lower()
            linked = [str(value) for value in item["requirement_ids"]]
        except (KeyError, TypeError) as exc:
            raise ContractError(f"state rule {index} is incomplete: {exc}") from exc
        if variable in governed or output_types.get(variable) != "BOOL":
            raise ContractError(
                f"state rule {index} variable must be a unique BOOL output: {variable!r}"
            )
        if not isinstance(initial, bool):
            raise ContractError(f"state rule {index} initial must be BOOL")
        if priority not in {"set", "clear"} or otherwise != "hold":
            raise ContractError(
                f"state rule {index} requires priority set/clear and otherwise hold"
            )
        if not linked or not set(linked) <= requirement_ids:
            raise ContractError(f"state rule {index} has invalid requirement_ids")
        # The user's original requirement, rather than an LLM paraphrase, decides
        # whether an output may retain state across scans. Ignore invented latches.
        if variable not in required_stateful:
            continue
        governed.add(variable)
        normalized.append({
            "variable": variable,
            "initial": initial,
            "set_when": set_when,
            "clear_when": clear_when,
            "priority": priority,
            "otherwise": "hold",
            "requirement_ids": linked,
        })
    allowed = input_names | governed
    for index, rule in enumerate(normalized, 1):
        for field in ("set_when", "clear_when"):
            unknown = _expression_identifiers(rule[field]) - allowed
            if unknown:
                raise ContractError(
                    f"state rule {index} {field} uses unknown or ungoverned identifiers: "
                    f"{sorted(unknown)}"
                )
    missing = required_stateful - governed
    if missing:
        raise ContractError(
            "state_rules omit retained outputs identified by the requirements: "
            f"{sorted(missing)}"
        )
    return normalized


def _audit_contract_semantics(
    *,
    requirements: list[dict[str, Any]],
    input_names: set[str],
    tests: list[dict[str, Any]],
    properties: list[dict[str, Any]],
    state_rules: list[dict[str, Any]],
    all_inputs_boolean: bool,
) -> dict[str, Any]:
    state_observations = 0
    property_observations = 0
    priority_coverage: dict[str, set[tuple[str, str]]] = {
        "feedback": set(), "sealed": set()
    }
    property_invariants = [
        (item["id"], item["plcverif"]["cases"][0]["parameters"][0])
        for item in properties
    ]
    priority_groups = _extract_priority_groups(requirements, input_names)
    priority_observations = 0
    exhaustive_property_observations = 0
    governed = {rule["variable"] for rule in state_rules}
    exhaustive_names = sorted(input_names | governed)
    reachable_states_checked = 0
    if (
        all_inputs_boolean
        and state_rules
        and len(exhaustive_names) <= 12
    ):
        # Safety properties are invariants over states reachable from the
        # declared initial state.  Enumerating arbitrary prior-state bit
        # patterns is stronger than model checking and rejects otherwise valid
        # contracts because those patterns may be unreachable by construction.
        input_order = sorted(input_names)
        state_order = sorted(governed)
        initial_values = {
            rule["variable"]: bool(rule["initial"]) for rule in state_rules
        }
        initial_state = tuple(initial_values[name] for name in state_order)
        pending_states = [initial_state]
        seen_states = {initial_state}
        while pending_states:
            state_bits = pending_states.pop()
            reachable_states_checked += 1
            prior_state = dict(zip(state_order, state_bits))
            for input_bits in itertools.product((False, True), repeat=len(input_order)):
                scan_inputs = dict(zip(input_order, input_bits))
                rule_values = {**scan_inputs, **prior_state}
                next_state: dict[str, bool] = {}
                for rule in state_rules:
                    set_active = _evaluate_expression(rule["set_when"], rule_values)
                    clear_active = _evaluate_expression(rule["clear_when"], rule_values)
                    if set_active and clear_active:
                        next_value = rule["priority"] == "set"
                    elif set_active:
                        next_value = True
                    elif clear_active:
                        next_value = False
                    else:
                        next_value = prior_state[rule["variable"]]
                    next_state[rule["variable"]] = next_value
                observation = {**scan_inputs, **next_state}
                for property_id, invariant in property_invariants:
                    if not _expression_identifiers(invariant) <= observation.keys():
                        continue
                    exhaustive_property_observations += 1
                    if not _evaluate_expression(invariant, observation):
                        raise ContractError(
                            "semantic audit found a property/state-rule contradiction: "
                            f"{property_id} ({invariant}) is false for reachable "
                            f"active_inputs={sorted(name for name, value in scan_inputs.items() if value)}, "
                            f"active_prior_state={sorted(name for name, value in prior_state.items() if value)}, "
                            f"next_state={next_state}"
                        )
                next_bits = tuple(next_state[name] for name in state_order)
                if next_bits not in seen_states:
                    seen_states.add(next_bits)
                    pending_states.append(next_bits)
    for case in tests:
        case_role = "feedback" if case["id"].startswith("FT") else "sealed"
        state = {rule["variable"]: rule["initial"] for rule in state_rules}
        for step_number, step in enumerate(case["steps"], 1):
            for repeat_number in range(1, step["repeat"] + 1):
                pre_state = dict(state)
                values = {**step["inputs"], **pre_state}
                next_state: dict[str, bool] = {}
                for rule in state_rules:
                    set_active = _evaluate_expression(rule["set_when"], values)
                    clear_active = _evaluate_expression(rule["clear_when"], values)
                    if set_active and clear_active:
                        next_value = rule["priority"] == "set"
                    elif set_active:
                        next_value = True
                    elif clear_active:
                        next_value = False
                    else:
                        next_value = bool(pre_state[rule["variable"]])
                    next_state[rule["variable"]] = next_value
                # A lower-priority event must not change governed state while a
                # higher-priority event is active. Compare the declared result
                # with a counterfactual in which all lower-priority events are
                # suppressed, using the exact same pre-scan state.
                for higher_index, higher_group in enumerate(priority_groups):
                    if not any(bool(step["inputs"].get(name)) for name in higher_group):
                        continue
                    masking_names = {
                        name for group in priority_groups[:higher_index] for name in group
                    }
                    if any(bool(step["inputs"].get(name)) for name in masking_names):
                        # A still-higher event masks this pair, so the step can
                        # demonstrate only that higher level's precedence.
                        continue
                    lower_names = {
                        name for group in priority_groups[higher_index + 1:] for name in group
                    }
                    active_lower = {
                        name for name in lower_names if bool(step["inputs"].get(name))
                    }
                    if not active_lower:
                        continue
                    for higher_name in higher_group:
                        if not bool(step["inputs"].get(higher_name)):
                            continue
                        for lower_name in active_lower:
                            priority_coverage[case_role].add((higher_name, lower_name))
                    counter_inputs = {**step["inputs"], **{name: False for name in lower_names}}
                    counter_values = {**counter_inputs, **pre_state}
                    for rule in state_rules:
                        set_active = _evaluate_expression(rule["set_when"], counter_values)
                        clear_active = _evaluate_expression(rule["clear_when"], counter_values)
                        if set_active and clear_active:
                            counter_value = rule["priority"] == "set"
                        elif set_active:
                            counter_value = True
                        elif clear_active:
                            counter_value = False
                        else:
                            counter_value = bool(pre_state[rule["variable"]])
                        priority_observations += 1
                        if next_state[rule["variable"]] != counter_value:
                            raise ContractError(
                                "semantic audit found a priority contradiction: "
                                f"{case['name']} step {step_number} activates higher-priority "
                                f"{sorted(higher_group)} with lower-priority {sorted(active_lower)}, "
                                f"but {rule['variable']} still depends on the lower-priority event "
                                f"(actual={next_state[rule['variable']]!r}, "
                                f"lower-suppressed={counter_value!r}, "
                                f"set_when={rule['set_when']!r}, clear_when={rule['clear_when']!r}). "
                                "Gate every lower-priority activation in this rule with NOT of every "
                                "input in the active higher-priority group; preserve this test step"
                            )
                state.update(next_state)
                should_check = step["check"] == "each" or repeat_number == step["repeat"]
                if not should_check:
                    continue
                expected = step["expect"]
                for variable, actual in next_state.items():
                    if variable not in expected:
                        continue
                    state_observations += 1
                    if expected[variable] != actual:
                        rule = next(
                            item for item in state_rules if item["variable"] == variable
                        )
                        rule_values = {**step["inputs"], **pre_state}
                        set_active = _evaluate_expression(rule["set_when"], rule_values)
                        clear_active = _evaluate_expression(rule["clear_when"], rule_values)
                        active_inputs = sorted(
                            name for name, value in step["inputs"].items() if value is True
                        )
                        active_prior_state = sorted(
                            name for name, value in pre_state.items() if value is True
                        )
                        raise ContractError(
                            "semantic audit found a state/test contradiction: "
                            f"{case['name']} step {step_number} repeat {repeat_number} expects "
                            f"{variable}={expected[variable]!r}, but its state rule yields {actual!r}; "
                            f"set_when={rule['set_when']!r} evaluated {set_active!r}, "
                            f"clear_when={rule['clear_when']!r} evaluated {clear_active!r}, "
                            f"prior {variable}={pre_state[variable]!r}, "
                            f"active_inputs={active_inputs}, active_prior_state={active_prior_state}. "
                            "Correct the rule or the expectation from the original user request, then "
                            "resimulate the complete case from its fresh initial state"
                        )
                observation = {**step["inputs"], **expected}
                for property_id, invariant in property_invariants:
                    identifiers = _expression_identifiers(invariant)
                    if not identifiers <= observation.keys():
                        continue
                    property_observations += 1
                    if not _evaluate_expression(invariant, observation):
                        raise ContractError(
                            "semantic audit found a property/test contradiction: "
                            f"{case['name']} step {step_number} repeat {repeat_number} violates "
                            f"{property_id} ({invariant})"
                        )
    required_priority_pairs = {
        (higher, lower)
        for higher_group, lower_group in zip(priority_groups, priority_groups[1:])
        for higher in higher_group
        for lower in lower_group
    }
    for role in ("feedback", "sealed"):
        missing_pairs = sorted(required_priority_pairs - priority_coverage[role])
        if missing_pairs:
            rendered = ", ".join(f"{higher}>{lower}" for higher, lower in missing_pairs)
            raise ContractError(
                f"semantic audit found incomplete {role} priority coverage: {rendered}; "
                "add simultaneous-TRUE steps for every listed pair"
            )
    return {
        "status": "passed",
        "version": SEMANTIC_AUDIT_VERSION,
        "state_rules_checked": len(state_rules),
        "state_observations_checked": state_observations,
        "property_observations_checked": property_observations,
        "exhaustive_property_observations_checked": exhaustive_property_observations,
        "reachable_states_checked": reachable_states_checked,
        "priority_observations_checked": priority_observations,
    }


def _extract_priority_groups(
    requirements: list[dict[str, Any]], input_names: set[str]
) -> list[set[str]]:
    """Extract explicit high-to-low input groups from normalized requirements.

    The contract author must use interface identifiers in a priority statement.
    Slash-separated identifiers are treated as one level. This audit is narrow
    by design: it enforces explicit priority declarations without guessing from
    unrelated prose.
    """

    for requirement in requirements:
        source = str(requirement.get("text", ""))
        clauses = [item.strip() for item in re.split(r"[；;。\n]+", source) if item.strip()]
        for text in clauses:
            lowered = text.casefold()
            has_priority_marker = (
                "优先级" in text or "优先于" in text or "priority" in lowered
                or ">" in text
            )
            if not has_priority_marker:
                continue
            pairwise = re.search(
                r"\b([A-Za-z_][A-Za-z0-9_]*)\b\s*优先于\s*\b([A-Za-z_][A-Za-z0-9_]*)\b",
                text, re.IGNORECASE,
            ) or re.search(
                r"\b([A-Za-z_][A-Za-z0-9_]*)\b\s+(?:has\s+)?priority\s+over\s+"
                r"\b([A-Za-z_][A-Za-z0-9_]*)\b",
                text, re.IGNORECASE,
            )
            if pairwise is not None:
                higher, lower = pairwise.group(1), pairwise.group(2)
                canonical = {name.casefold(): name for name in input_names}
                if higher.casefold() in canonical and lower.casefold() in canonical:
                    return [{canonical[higher.casefold()]}, {canonical[lower.casefold()]}]
            if not (
                "高到低" in text or ("最高" in text and "其次" in text)
                or "highest" in lowered or ">" in text
            ):
                continue
            ordered: list[tuple[int, set[str], str]] = []
            for name in input_names:
                match = re.search(rf"\b{re.escape(name)}\b", text, re.IGNORECASE)
                if match:
                    ordered.append((match.start(), {name}, name))
            aliases = (
                (r"完成信号|completion signals?", {name for name in input_names if re.search(r"done|complete|finished", name, re.IGNORECASE)}),
                (r"停止信号|stop signals?", {name for name in input_names if re.search(r"stop|e_?stop|emergency", name, re.IGNORECASE)}),
                (r"启动信号|start signals?", {name for name in input_names if re.search(r"start|enable", name, re.IGNORECASE)}),
            )
            exact_names = {name for _, names, _ in ordered for name in names}
            for pattern, names in aliases:
                match = re.search(pattern, text, re.IGNORECASE)
                remaining = names - exact_names
                if match and remaining:
                    ordered.append((match.start(), remaining, match.group(0)))
                    exact_names.update(remaining)
            ordered.sort(key=lambda item: item[0])
            if len(ordered) < 2:
                continue
            groups: list[set[str]] = []
            for index, (position, names, token) in enumerate(ordered):
                if index == 0:
                    groups.append(set(names))
                    continue
                previous_position, _, previous_token = ordered[index - 1]
                between = text[previous_position + len(previous_token):position]
                if re.fullmatch(r"\s*[/／]\s*", between):
                    groups[-1].update(names)
                else:
                    groups.append(set(names))
            if len(groups) >= 2:
                return groups
    return []


def _audit_requirement_traceability(
    *,
    requirements: list[dict[str, Any]],
    properties: list[dict[str, Any]],
    state_rules: list[dict[str, Any]],
    tests: list[dict[str, Any]],
) -> dict[str, Any]:
    """Require every frozen requirement to have semantic and runtime evidence.

    Linking IDs is intentionally checked after normalization, so the model cannot
    satisfy coverage with an unknown requirement, an empty test, or an invalid
    property.  Feedback and sealed tests are both mandatory: the former guides
    generation while the latter independently confirms the same requirement.
    """

    rows: list[dict[str, Any]] = []
    for requirement in requirements:
        requirement_id = requirement["id"]
        property_ids = [
            item["id"] for item in properties
            if requirement_id in item["requirement_ids"]
        ]
        state_variables = [
            item["variable"] for item in state_rules
            if requirement_id in item["requirement_ids"]
        ]
        feedback_test_ids = [
            item["id"] for item in tests
            if item["id"].startswith("FT") and requirement_id in item["requirement_ids"]
        ]
        sealed_test_ids = [
            item["id"] for item in tests
            if item["id"].startswith("OT") and requirement_id in item["requirement_ids"]
        ]
        missing: list[str] = []
        if not property_ids and not state_variables:
            missing.append("semantic definition (property or state rule)")
        if requirement["safety_critical"] and not property_ids:
            missing.append("mandatory safety property")
        if not feedback_test_ids:
            missing.append("feedback runtime test")
        if not sealed_test_ids:
            missing.append("sealed runtime test")
        if missing:
            raise ContractError(
                f"requirement {requirement_id} lacks traceability coverage: "
                + ", ".join(missing)
            )
        rows.append({
            "requirement_id": requirement_id,
            "safety_critical": requirement["safety_critical"],
            "property_ids": property_ids,
            "state_variables": state_variables,
            "feedback_test_ids": feedback_test_ids,
            "sealed_test_ids": sealed_test_ids,
        })
    return {
        "status": "passed",
        "requirements_covered": len(rows),
        "rows": rows,
    }


def _augment_stateful_priority_tests(
    *,
    task_id: str,
    requirements: list[dict[str, Any]],
    priority_requirements: list[dict[str, Any]],
    inputs: list[dict[str, str]],
    outputs: list[dict[str, str]],
    state_rules: list[dict[str, Any]],
    tests: list[dict[str, Any]],
) -> int:
    """Add missing runtime priority pairs when all outputs have explicit state rules.

    Expected outputs are computed from the frozen state rules, but the priority
    check remains independent: the semantic audit compares each result with a
    counterfactual scan where the lower-priority event is suppressed.  Incorrect
    rules therefore still fail instead of being normalized into success.
    """
    input_names = {item["name"] for item in inputs}
    output_names = {item["name"] for item in outputs}
    rules_by_output = {item["variable"]: item for item in state_rules}
    if not output_names or set(rules_by_output) != output_names:
        return 0
    priority_groups = _extract_priority_groups(priority_requirements, input_names)
    required_pairs = {
        (higher, lower)
        for higher_group, lower_group in zip(priority_groups, priority_groups[1:])
        for higher in higher_group
        for lower in lower_group
    }
    if not required_pairs:
        return 0

    observed: dict[str, set[tuple[str, str]]] = {"feedback": set(), "sealed": set()}
    for case in tests:
        role = "feedback" if case["id"].startswith("FT") else "sealed"
        for step in case["steps"]:
            for higher_index, higher_group in enumerate(priority_groups):
                masking = {
                    name for group in priority_groups[:higher_index] for name in group
                }
                if any(bool(step["inputs"].get(name)) for name in masking):
                    continue
                active_higher = {
                    name for name in higher_group if bool(step["inputs"].get(name))
                }
                if not active_higher:
                    continue
                active_lower = {
                    name
                    for group in priority_groups[higher_index + 1:]
                    for name in group
                    if bool(step["inputs"].get(name))
                }
                observed[role].update(
                    (higher, lower)
                    for higher in active_higher
                    for lower in active_lower
                )

    input_defaults = {
        item["name"]: False if item["type"] == "BOOL" else 0
        for item in inputs
    }
    initial_state = {
        variable: bool(rule["initial"]) for variable, rule in rules_by_output.items()
    }
    generated = 0
    for role, prefix in (("feedback", "FT"), ("sealed", "OT")):
        role_count = sum(case["id"].startswith(prefix) for case in tests)
        for higher, lower in sorted(required_pairs - observed[role]):
            step_inputs = dict(input_defaults)
            step_inputs[higher] = True
            step_inputs[lower] = True
            values = {**step_inputs, **initial_state}
            expected: dict[str, bool] = {}
            for variable, rule in rules_by_output.items():
                set_active = _evaluate_expression(rule["set_when"], values)
                clear_active = _evaluate_expression(rule["clear_when"], values)
                if set_active and clear_active:
                    expected[variable] = rule["priority"] == "set"
                elif set_active:
                    expected[variable] = True
                elif clear_active:
                    expected[variable] = False
                else:
                    expected[variable] = initial_state[variable]
            linked = [
                item["id"] for item in requirements
                if re.search(rf"\b(?:{re.escape(higher)}|{re.escape(lower)})\b", item["text"], re.I)
            ]
            if not linked:
                linked = [item["id"] for item in requirements if item["safety_critical"]]
            if not linked:
                linked = [requirements[0]["id"]]
            role_count += 1
            tests.append({
                "id": f"{prefix}{role_count:02d}",
                "name": f"{task_id}_{role}_priority_{higher}_{lower}",
                "description": (
                    f"deterministic adjacent-priority check: {higher} over {lower}"
                ),
                "requirement_ids": linked,
                "fresh_instance": True,
                "steps": [{
                    "inputs": step_inputs,
                    "expect": expected,
                    "repeat": 1,
                    "check": "each",
                }],
            })
            generated += 1
    return generated


def normalize_contract(
    raw: dict[str, Any],
    task_id: str,
    *,
    source_requirement: str | None = None,
) -> dict[str, Any]:
    try:
        title = str(raw["title"]).strip()
        scan_period_ms = int(raw.get("scan_period_ms", 100))
        assumptions = [str(item).strip() for item in raw.get("assumptions", [])]
        inputs = raw["inputs"]
        outputs = raw["outputs"]
        requirements = raw["requirements"]
        state_rules = raw["state_rules"]
        properties = raw["properties"]
        tests = raw["tests"]
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractError(f"contract has missing or invalid top-level fields: {exc}") from exc
    if not title or not 10 <= scan_period_ms <= 1000:
        raise ContractError("title is empty or scan_period_ms is outside 10..1000")
    if not isinstance(inputs, list) or not inputs or not isinstance(outputs, list) or not outputs:
        raise ContractError("at least one input and one output are required")

    names: set[str] = set()
    interface: dict[str, list[dict[str, str]]] = {"inputs": [], "outputs": []}
    type_by_name: dict[str, str] = {}
    for section, items in (("inputs", inputs), ("outputs", outputs)):
        for item in items:
            name = str(item["name"])
            typ = str(item["type"]).upper()
            if not IDENTIFIER.fullmatch(name) or name in names:
                raise ContractError(f"invalid or duplicate interface identifier: {name!r}")
            if typ not in SUPPORTED_TYPES:
                raise ContractError(f"unsupported interface type {typ!r}; use BOOL, INT, or REAL")
            names.add(name)
            type_by_name[name] = typ
            interface[section].append({
                "name": name,
                "type": typ,
                "description": str(item.get("description", "")).strip(),
            })

    if not isinstance(requirements, list) or not requirements:
        raise ContractError("at least one requirement is required")
    normalized_requirements = []
    requirement_ids: set[str] = set()
    for index, item in enumerate(requirements, 1):
        requirement_id = str(item.get("id", f"R{index}"))
        if not re.fullmatch(r"R[1-9][0-9]*", requirement_id) or requirement_id in requirement_ids:
            raise ContractError(f"invalid or duplicate requirement id: {requirement_id}")
        text = str(item["text"]).strip()
        if not text:
            raise ContractError(f"{requirement_id} has empty text")
        requirement_ids.add(requirement_id)
        normalized_requirements.append({
            "id": requirement_id,
            "text": text,
            "safety_critical": bool(item.get("safety_critical", False)),
        })

    input_names = {item["name"] for item in interface["inputs"]}
    normalized_state_rules = _normalize_state_rules(
        state_rules,
        input_names=input_names,
        outputs=interface["outputs"],
        requirements=normalized_requirements,
        stateful_requirements=(
            [{"text": source_requirement}] if source_requirement is not None else None
        ),
        requirement_ids=requirement_ids,
    )

    if not isinstance(properties, list) or not properties:
        raise ContractError("at least one PLCverif invariant is required")
    normalized_properties = []
    definition_covered_outputs: set[str] = set()
    for index, item in enumerate(properties, 1):
        invariant = str(item["invariant"]).strip()
        if re.search(r"[^A-Za-z0-9_()=<>!\s.+\-*/]", invariant):
            raise ContractError(f"property P{index} contains unsupported syntax")
        identifiers = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", invariant))
        unknown = identifiers - names - PROPERTY_TOKENS
        if unknown:
            raise ContractError(f"property P{index} uses non-interface identifiers: {sorted(unknown)}")
        linked = tuple(str(value) for value in item.get("requirement_ids", []))
        if not linked or not set(linked) <= requirement_ids:
            raise ContractError(f"property P{index} has invalid requirement_ids")
        normalized_properties.append({
            "id": f"P{index}",
            "requirement_ids": list(linked),
            "kind": str(item.get("kind", "safety")),
            "mandatory": True,
            "expression": f"G({invariant})",
            "source": "user-confirmed contract derived before candidate generation",
            "plcverif": {
                "status": "required",
                "cases": [{
                    "backend": "auto",
                    "pattern_id": "pattern-invariant",
                    "parameters": [invariant],
                    "mapping": "direct end-of-cycle invariant",
                }],
                "coverage": "complete",
            },
        })
        definition_covered_outputs.update(
            _equality_identifiers(invariant) & {item["name"] for item in interface["outputs"]}
        )

    governed_outputs = {rule["variable"] for rule in normalized_state_rules}
    for item in normalized_properties:
        invariant = item["plcverif"]["cases"][0]["parameters"][0]
        for output in governed_outputs:
            for equality in re.finditer(
                rf"\b{re.escape(output)}\b\s*=\s*([^)]*(?:\)[^)]*)?)",
                invariant,
                re.IGNORECASE,
            ):
                right_hand_side = equality.group(1)
                if re.search(rf"\b{re.escape(output)}\b", right_hand_side, re.IGNORECASE):
                    raise ContractError(
                        "retained output property uses an invalid self-referential "
                        f"end-of-scan equality for {output}; express retention only in state_rules"
                    )
    missing_definitions = (
        {item["name"] for item in interface["outputs"]}
        - governed_outputs
        - definition_covered_outputs
    )
    if missing_definitions:
        raise ContractError(
            "combinational outputs lack a definitional equality property: "
            f"{sorted(missing_definitions)}"
        )

    if not isinstance(tests, list) or len(tests) < 2:
        raise ContractError("at least one feedback test and one sealed test are required")
    normalized_tests = []
    role_counts = {"feedback": 0, "sealed": 0}
    output_names = {item["name"] for item in interface["outputs"]}
    for index, case in enumerate(tests, 1):
        role = str(case["role"]).lower()
        if role not in role_counts:
            raise ContractError(f"test {index} role must be feedback or sealed")
        role_counts[role] += 1
        linked = [str(value) for value in case.get("requirement_ids", [])]
        if not linked or not set(linked) <= requirement_ids:
            raise ContractError(f"test {index} has invalid requirement_ids")
        steps = []
        for step_index, step in enumerate(case.get("steps", []), 1):
            step_inputs = dict(step["inputs"])
            expected = dict(step["expect"])
            if set(step_inputs) != input_names:
                missing = sorted(input_names - set(step_inputs))
                extra = sorted(set(step_inputs) - input_names)
                raise ContractError(f"test {index} step {step_index} input mismatch: missing={missing}, extra={extra}")
            if set(expected) != output_names:
                missing = sorted(output_names - set(expected))
                extra = sorted(set(expected) - output_names)
                raise ContractError(
                    f"test {index} step {step_index} output mismatch: "
                    f"missing={missing}, extra={extra}"
                )
            for name, value in step_inputs.items():
                _check_value(value, type_by_name[name], f"test input {name}")
            for name, value in expected.items():
                _check_value(value, type_by_name[name], f"expected output {name}")
            repeat = int(step.get("repeat", 1))
            check = str(step.get("check", "each"))
            if not 1 <= repeat <= 100 or check not in {"each", "last_only"}:
                raise ContractError(f"test {index} step {step_index} has invalid repeat/check")
            steps.append({"inputs": step_inputs, "expect": expected, "repeat": repeat, "check": check})
        if not steps:
            raise ContractError(f"test {index} has no steps")
        prefix = "FT" if role == "feedback" else "OT"
        normalized_tests.append({
            "id": f"{prefix}{role_counts[role]:02d}",
            "name": f"{task_id}_{role}_{role_counts[role]}",
            "description": str(case.get("description", "")).strip(),
            "requirement_ids": linked,
            "fresh_instance": True,
            "steps": steps,
        })
    if min(role_counts.values()) < 1:
        raise ContractError("both feedback and sealed runtime tests are required")

    priority_requirements = (
        ([{"text": source_requirement}] if source_requirement is not None else [])
        + normalized_requirements
    )
    generated_priority_cases = _augment_stateful_priority_tests(
        task_id=task_id,
        requirements=normalized_requirements,
        priority_requirements=priority_requirements,
        inputs=interface["inputs"],
        outputs=interface["outputs"],
        state_rules=normalized_state_rules,
        tests=normalized_tests,
    )
    traceability = _audit_requirement_traceability(
        requirements=normalized_requirements,
        properties=normalized_properties,
        state_rules=normalized_state_rules,
        tests=normalized_tests,
    )
    semantic_audit = _audit_contract_semantics(
        # The original request has precedence: an LLM paraphrase must not erase
        # a priority relation and thereby shrink mandatory test coverage.
        requirements=priority_requirements,
        input_names=input_names,
        tests=normalized_tests,
        properties=normalized_properties,
        state_rules=normalized_state_rules,
        all_inputs_boolean=all(item["type"] == "BOOL" for item in interface["inputs"]),
    )
    semantic_audit["generated_priority_cases"] = generated_priority_cases
    semantic_audit["traceability"] = traceability

    return {
        "schema_version": "1.1",
        "task_id": task_id,
        "title": title,
        "scan_period_ms": scan_period_ms,
        "assumptions": assumptions,
        "interface": interface,
        "requirements": normalized_requirements,
        "state_rules": normalized_state_rules,
        "properties": normalized_properties,
        "tests": normalized_tests,
        "semantic_audit": semantic_audit,
        "oracle_provenance": "llm_draft_pending_user_confirmation",
    }


def compile_contract(requirement: str, vendor: dict[str, Any], plc_model: dict[str, Any],
                     provider: dict[str, Any], task_id: str,
                     output_language: str = "st",
                     progress_callback: Callable[[dict[str, Any]], None] | None = None,
                     cancel_check: Callable[[], bool] | None = None,
                     attempt_offset: int = 0,
                     attempt_budget: int | None = None,
                     prior_usage: dict[str, int | float] | None = None,
                     prior_latency_ms: int = 0,
                     resume_draft: str | None = None,
                     resume_error: str | None = None,
                     ) -> tuple[dict[str, Any], dict[str, Any]]:
    from plc_loop.cancellation import raise_if_cancelled

    if not 0 <= attempt_offset <= CONTRACT_ATTEMPT_BUDGET:
        raise ValueError("contract attempt_offset is outside the fixed budget")
    remaining_budget = CONTRACT_ATTEMPT_BUDGET - attempt_offset
    effective_budget = remaining_budget if attempt_budget is None else min(
        int(attempt_budget), remaining_budget
    )
    if effective_budget < 1:
        raise ContractError(
            f"contract attempt budget was already exhausted after {attempt_offset} attempts"
        )
    raise_if_cancelled(cancel_check)
    if progress_callback:
        progress_callback({
            "attempt": attempt_offset,
            "maximum_attempts": CONTRACT_ATTEMPT_BUDGET,
            "status": "resuming" if attempt_offset else "preparing",
        })
    contract_provider = dict(provider)
    contract_thinking_mode = contract_provider.pop("contract_thinking_mode", None)
    contract_max_output_tokens = contract_provider.pop("contract_max_output_tokens", None)
    if contract_thinking_mode is not None:
        contract_provider["thinking_mode"] = contract_thinking_mode
    if contract_max_output_tokens is not None:
        contract_provider["max_output_tokens"] = int(contract_max_output_tokens)
    settings = ProviderSettings.from_dict(contract_provider)
    client = OpenAICompatibleClient(settings)
    system = (
        "You translate an industrial control request into a reviewable IEC 61131-3 verification contract. "
        "Do not generate the PLC implementation. Return exactly one JSON object and no prose. "
        "Use only BOOL, INT, and REAL external variables. Every test step must assign every input. "
        "Every test step must use an integer repeat from 1 through 100 and check equal to either each or last_only. "
        "State rules are mandatory for every BOOL output whose value is retained across scans. "
        "Do not create a state rule for a purely combinational output. If a run output must become false "
        "when an enable, selection, permissive, or safety input changes, model that condition explicitly; "
        "never let an old run state survive after its selection or permissive becomes false. "
        "Each state rule is the single semantic source for its initial, set, clear, priority, and hold behavior; "
        "all runtime expectations must agree with those rules. "
        "For an output governed by a state rule, do not add a definitional equality that uses the output "
        "itself as if its end-of-scan value were its prior value. Properties observe end-of-scan interface "
        "values and cannot express prior state; use state_rules for transitions and only non-temporal safety "
        "implications for such retained outputs. "
        "Every test case runs on a fresh controller instance initialized from state_rules.initial. A retained "
        "output may therefore be expected true only after an earlier step in that same test case triggers it; "
        "a feedback test never leaves state for a sealed test. "
        "Within one test case, retained state persists across every later step until its declared clear_when "
        "condition occurs. If a later priority scenario needs that state FALSE, put it in a different fresh "
        "test case or execute its real reset condition first; never silently reset it by changing expect. "
        "An initial output value describes the state before the first function-block invocation. At the end "
        "of the first test scan, every combinational output must already satisfy its definitional equality; "
        "do not add a one-scan startup delay unless the user explicitly requests one. "
        "Every test step must provide the expected value of every output. For every output not governed by "
        "a state_rule, include a definitional equality invariant such as Output = boolean_expression; safety "
        "implications alone are insufficient. Simulate those equalities against every test expectation. "
        "Every requirement ID must be linked to a state rule or property, a feedback test, and a sealed test. "
        "Every safety-critical requirement must be linked to a mandatory invariant property. "
        "For every explicitly ordered priority level, both feedback and sealed tests must contain "
        "simultaneous-TRUE steps for every input pair in adjacent priority levels. The expected state "
        "must match a counterfactual scan in which the lower-priority input is suppressed. While testing "
        "one pair, every input above that pair's higher level must be FALSE so it cannot mask the pair. "
        "If the higher-priority event is meaningful only after a retained prerequisite state is active, "
        "first establish that state in an earlier step of the same fresh test case, then apply the pair. "
        "An explicit priority group is collective: if any input in that group is TRUE, no input in any "
        "lower group may change a governed output. For example, under Reset > Stop > {Done1, Done2} > "
        "Start, a Start-based set condition must include NOT Reset, NOT Stop, NOT Done1, and NOT Done2; "
        "a Done-based transition must include NOT Reset and NOT Stop. Do not remove a simultaneous pair "
        "test to hide a rule defect. "
        "For a retained multi-stage sequence, all stage-run outputs must remain mutually exclusive in every "
        "reachable state. Unless the user explicitly requests restart behavior, ignore Start while a later "
        "stage or a latched completion output is active: gate an earlier-stage set_when with NOT of every "
        "later retained stage and completion output. A completion transition must clear its running stage, "
        "and a stage transition must clear the previous stage in the same scan. Include a repeated-Start "
        "scenario after entering a later stage so the contract demonstrates this rule. "
        "Keep the contract compact: use no more than 6 requirements, 10 properties, and 6 tests, "
        "with no more than 8 steps per test and concise descriptions. "
        "Properties must be end-of-scan invariants over interface identifiers using AND, OR, NOT, XOR, "
        "TRUE, FALSE, =, <>, <, <=, >, >=, +, -, *, / and parentheses; do not use G, X, timers, or internal variables."
    )
    prompt = f"""Create a contract for function block {task_id}.

Target vendor: {vendor['label']}
Target controller: {plc_model['label']}
Compatibility profile: {plc_model['iec_profile']}
Compatibility note: {plc_model['notes']}
Requested implementation language: {"native ladder diagram; use BOOL interface variables only" if output_language == "ld" else "Structured Text"}

User request:
{requirement}

JSON schema (keys and nesting are mandatory):
{{
  "title": "...",
  "scan_period_ms": 100,
  "assumptions": ["..."],
  "inputs": [{{"name":"Start","type":"BOOL","description":"..."}}],
  "outputs": [{{"name":"Motor","type":"BOOL","description":"..."}}],
  "requirements": [
    {{"id":"R1","text":"Start sets Motor and Motor remains active after Start is released until Stop is pressed.","safety_critical":false}},
    {{"id":"R2","text":"Stop clears Motor and has priority over Start.","safety_critical":true}}
  ],
  "state_rules": [
    {{"variable":"Motor","initial":false,"set_when":"Start AND NOT Stop","clear_when":"Stop","priority":"clear","otherwise":"hold","requirement_ids":["R1","R2"]}}
  ],
  "properties": [{{"requirement_ids":["R2"],"kind":"safety","invariant":"Stop -> NOT Motor"}}],
  "tests": [
    {{"role":"feedback","description":"start, retained run, and stop priority","requirement_ids":["R1","R2"],"steps":[
      {{"inputs":{{"Start":true,"Stop":false}},"expect":{{"Motor":true}},"repeat":1,"check":"each"}},
      {{"inputs":{{"Start":false,"Stop":false}},"expect":{{"Motor":true}},"repeat":1,"check":"each"}},
      {{"inputs":{{"Start":false,"Stop":true}},"expect":{{"Motor":false}},"repeat":1,"check":"each"}}
    ]}},
    {{"role":"sealed","description":"independent start, retention, and simultaneous stop priority","requirement_ids":["R1","R2"],"steps":[
      {{"inputs":{{"Start":true,"Stop":false}},"expect":{{"Motor":true}},"repeat":1,"check":"each"}},
      {{"inputs":{{"Start":false,"Stop":false}},"expect":{{"Motor":true}},"repeat":1,"check":"each"}},
      {{"inputs":{{"Start":true,"Stop":true}},"expect":{{"Motor":false}},"repeat":1,"check":"each"}}
    ]}}
  ]
}}

Conditions in state_rules may reference inputs and other governed BOOL outputs. They are evaluated from scan-start inputs and prior-scan governed outputs; all governed outputs update simultaneously. When set_when and clear_when are both true, priority selects the result. Otherwise must be hold.

Include normal, boundary, reset/stop, simultaneous-priority, and unsafe-input cases when relevant. For each adjacent level in an explicit high-to-low priority order, exercise every input pair as simultaneously TRUE in at least one feedback test and one sealed test; set all inputs in higher priority levels to FALSE in that pair's test step. Every requirement ID must occur in semantic evidence (a property or state rule), at least one feedback test, and at least one sealed test; every safety-critical requirement must occur in a property. Before returning JSON, simulate every state rule over every test step and ensure each expected output agrees with the resulting state and every listed invariant. """
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    initial_messages = list(messages)
    if resume_draft and resume_error:
        messages.extend([
            {"role": "assistant", "content": resume_draft},
            {
                "role": "user",
                "content": (
                    "The service restarted after the deterministic validator rejected the prior JSON. "
                    "Continue the same bounded repair without resetting the attempt budget. The last "
                    f"diagnostic was:\n{resume_error}\nReturn one complete corrected JSON object only."
                ),
            },
        ])
    attempts: list[dict[str, Any]] = []
    usage_total: dict[str, int | float] = {
        key: value for key, value in (prior_usage or {}).items()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    }
    last_rejection_error = resume_error or ""
    last_rejection_family = (
        _contract_error_family(last_rejection_error) if last_rejection_error else ""
    )
    repeated_rejection_count = 1 if last_rejection_error else 0
    for local_attempt in range(1, effective_budget + 1):
        attempt_number = attempt_offset + local_attempt
        raise_if_cancelled(cancel_check)
        if repeated_rejection_count >= CONTRACT_BLIND_REBUILD_STREAK:
            messages = [initial_messages[0], {
                "role": "user",
                "content": (
                    str(initial_messages[1]["content"])
                    + "\n\n"
                    "Rebuild the contract from the original user request without copying the previous JSON. "
                    f"The prior repair sequence remained inconsistent: {last_rejection_error}\n"
                    "Derive retained state versus combinational outputs again, then simulate every test step "
                    "from initial state. Return one complete compact JSON object only."
                ),
            }]
            if progress_callback:
                progress_callback({
                    "attempt": attempt_number,
                    "maximum_attempts": CONTRACT_ATTEMPT_BUDGET,
                    "status": "blind_rebuild",
                })
            last_rejection_family = ""
            repeated_rejection_count = 0
        if progress_callback:
            progress_callback({
                "attempt": attempt_number,
                "maximum_attempts": CONTRACT_ATTEMPT_BUDGET,
                "status": "requesting",
            })
        try:
            reply = client.generate(messages)
            raise_if_cancelled(cancel_check)
        except RuntimeError as exc:
            if not is_retryable_model_error(exc):
                raise
            lowered_error = str(exc).casefold()
            if (
                "provider concurrency queue timed out" in lowered_error
                or "provider rate-limit queue timed out" in lowered_error
            ):
                raise ContractInfrastructureError(
                    "本地模型调用队列在当前并发负载下等待超时；"
                    "任务未进入 PLC 候选生成，请稍后重新提交。"
                ) from exc
            if (
                "provider request failed after transport retries" in lowered_error
                or "provider streaming request failed without retry" in lowered_error
                or "provider circuit is open" in lowered_error
            ):
                raise ContractInfrastructureError(
                    "上游模型网络连接在完成传输重试后仍不可用；"
                    "任务未进入 PLC 候选生成，请在模型服务恢复后重新提交。"
                ) from exc
            error = f"{type(exc).__name__}: {exc}"
            rejected = {
                "attempt": attempt_number,
                "maximum_attempts": CONTRACT_ATTEMPT_BUDGET,
                "status": "rejected",
                "error": error,
                "error_kind": "provider_retryable",
                "usage": {},
                "latency_ms": 0,
            }
            attempts.append(rejected)
            last_rejection_error = error
            rejection_family = _contract_error_family(error)
            if rejection_family == last_rejection_family:
                repeated_rejection_count += 1
            else:
                last_rejection_family = rejection_family
                repeated_rejection_count = 1
            if progress_callback:
                progress_callback(dict(rejected))
            if local_attempt == effective_budget:
                raise ContractError(
                    f"contract provider failed after {attempt_number} attempts: {error}"
                ) from exc
            messages = initial_messages + [{
                "role": "user",
                "content": (
                    "The previous request returned no complete JSON contract. Retry from the original "
                    "request and return JSON only. Keep descriptions concise, avoid optional detail, "
                    "and reserve the output budget for the complete JSON object."
                ),
            }]
            continue
        if progress_callback:
            progress_callback({
                "attempt": attempt_number,
                "maximum_attempts": CONTRACT_ATTEMPT_BUDGET,
                "status": "received",
                "resolved_model": reply.resolved_model,
                "usage": reply.usage,
                "latency_ms": reply.latency_ms,
            })
        for key, value in reply.usage.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                usage_total[key] = usage_total.get(key, 0) + value
        try:
            if progress_callback:
                progress_callback({
                    "attempt": attempt_number,
                    "maximum_attempts": CONTRACT_ATTEMPT_BUDGET,
                    "status": "validating",
                })
            if reply.finish_reason == "length" and not str(reply.message.get("content") or "").strip():
                raise ContractError(
                    "model exhausted its output-token limit in reasoning and returned no contract JSON"
                )
            contract = normalize_contract(
                _extract_json(reply.message.get("content")),
                task_id,
                source_requirement=requirement,
            )
        except (ContractError, KeyError, TypeError, ValueError) as exc:
            error = str(exc) if isinstance(exc, ContractError) else f"{type(exc).__name__}: {exc}"
            content = str(reply.message.get("content") or "").strip()
            rejected = {
                "attempt": attempt_number,
                "maximum_attempts": CONTRACT_ATTEMPT_BUDGET,
                "status": "rejected",
                "error": error,
                "resolved_model": reply.resolved_model,
                "usage": reply.usage,
                "latency_ms": reply.latency_ms,
            }
            attempts.append(rejected)
            if progress_callback:
                private_event = dict(rejected)
                if content:
                    private_event["private_draft"] = content
                progress_callback(private_event)
            last_rejection_error = error
            rejection_family = _contract_error_family(error)
            if rejection_family == last_rejection_family:
                repeated_rejection_count += 1
            else:
                last_rejection_family = rejection_family
                repeated_rejection_count = 1
            if local_attempt == effective_budget:
                raise ContractError(
                    f"contract remained invalid after {attempt_number} attempts: {error}"
                ) from exc
            if content:
                assistant_message = dict(reply.message)
                assistant_message.setdefault("role", "assistant")
                messages.extend([assistant_message, {
                    "role": "user",
                    "content": (
                    "The deterministic contract validator rejected the JSON with this error:\n"
                    f"{error}\n"
                    "Return the complete corrected JSON object. Preserve valid requirements and interfaces, "
                    "and fix the reported schema or value violation. For a state/test contradiction, first "
                    "re-read the user request: retain only outputs explicitly described as latched, held, "
                    "persistent, or remaining until a reset/stop condition. Remove state_rules for ordinary "
                    "run, valve, selection, permissive, and interlock outputs and define their expected values "
                    "from the current inputs. Each test starts from a fresh instance: if its first step expects "
                    "a retained alarm or latch to be true, add an earlier trigger step in that same test or fix "
                    "the expectation. Initial output values apply before the first invocation, not after it; "
                    "the first checked scan must satisfy every combinational equality. Then resimulate every "
                    "test step. Build a coverage checklist over every requirement ID before returning: if an "
                    "existing test actually exercises an uncovered requirement, add that ID without removing "
                    "the existing IDs; otherwise add a compact test that exercises it. Every requirement must "
                    "be covered by both feedback and sealed tests and by semantic evidence; safety-critical "
                    "requirements also require a property. "
                    "For sequential state transitions, evaluate every state rule from scan-start inputs and "
                    "the prior-scan retained outputs, then update governed outputs simultaneously. A next-stage "
                    "output must be set by the completion event while the prior stage is active and must not be "
                    "cleared merely because that one-scan completion event becomes false. "
                    "For a retained output, do not add an equality property that refers to the same output on "
                    "both sides; that cannot represent prior state in an end-of-scan invariant. When a priority "
                    "test needs a prior stage, establish it in an earlier step of that same test before asserting "
                    "the simultaneous inputs. "
                    "Retained outputs persist between steps in the same test. If the diagnostic shows a prior "
                    "retained output TRUE and neither set_when nor clear_when changes it, its expected value must "
                    "remain TRUE. To test a FALSE-state priority scenario, move it to a fresh test or first apply "
                    "the declared reset condition. "
                    "A priority level containing multiple inputs is collective: any active input in that level "
                    "must suppress every lower-level event for every governed output. Fix the state rule named "
                    "by the diagnostic; never delete the simultaneous test to conceal the conflict. "
                    "Return JSON only."
                ),
            }])
            else:
                messages = initial_messages + [{
                    "role": "user",
                    "content": (
                        "The previous response was truncated before the JSON contract. Return a fresh, "
                        "complete, compact JSON object only; omit optional descriptive detail."
                    ),
                }]
            continue
        attempts.append({
            "attempt": attempt_number,
            "maximum_attempts": CONTRACT_ATTEMPT_BUDGET,
            "status": "accepted",
            "resolved_model": reply.resolved_model,
            "usage": reply.usage,
            "latency_ms": reply.latency_ms,
        })
        if progress_callback:
            progress_callback(dict(attempts[-1]))
        return contract, {
            "provider": reply.provider,
            "requested_model": reply.requested_model,
            "resolved_model": reply.resolved_model,
            "usage": usage_total,
            "latency_ms": prior_latency_ms + sum(item["latency_ms"] for item in attempts),
            "resumed_after_attempt": attempt_offset,
            "attempt_budget": CONTRACT_ATTEMPT_BUDGET,
            "attempts": attempts,
        }
    raise AssertionError("unreachable contract generation state")


def write_task_package(root: Path, contract: dict[str, Any], original_requirement: str,
                       vendor_id: str, model_id: str) -> None:
    root.mkdir(parents=True, exist_ok=False)
    task_id = contract["task_id"]
    interface = contract["interface"]
    oracle_provenance = str(contract.get("oracle_provenance", "llm_draft_pending_confirmation"))
    delta_official = vendor_id == "delta" and model_id in {"DVP48ES300R", "AS228T-A"}
    compatibility_scope = (
        f"portable IEC 61131-3 ST plus ISPSoft/COMMGR validation for Delta {model_id}"
        if delta_official
        else "portable IEC 61131-3 ST checked by the configured Linux toolchain"
    )
    metadata = {
        "schema_version": "1.0",
        "dataset_version": "production-user-contract-v1",
        "id": task_id,
        "title": contract["title"],
        "category_id": "USER",
        "category": "User supplied control requirement",
        "iec_profile": (
            "delta-dvp-es3-portable-st-v1" if model_id == "DVP48ES300R"
            else "delta-as200-as228t-portable-st-v1" if model_id == "AS228T-A"
            else "portable-iec-st-core-v1"
        ),
        "target": {"vendor": vendor_id, "model": model_id},
        "interface": interface,
        "scan": {
            "period_ms": contract["scan_period_ms"],
            "input_sampling": "scan_start",
            "output_observation": "scan_end",
            "initialization": "fresh function-block instance for every test case",
        },
        "assumptions": contract["assumptions"],
        "requirements": contract["requirements"],
        "state_rules": contract["state_rules"],
        "semantic_audit": contract["semantic_audit"],
        "oracle_provenance": oracle_provenance,
        "compatibility_scope": compatibility_scope,
    }
    requirement_lines = [
        f"# {task_id}: {contract['title']}", "", "## Target", "",
        f"- Vendor: {vendor_id}", f"- Controller model: {model_id}",
        f"- Compatibility scope: {compatibility_scope}.",
        "", "## User request", "", original_requirement,
        "", "## Frozen requirements", "",
    ]
    for item in contract["requirements"]:
        marker = " **[safety-critical]**" if item["safety_critical"] else ""
        requirement_lines.append(f"- **{item['id']}**{marker}: {item['text']}")
    requirement_lines.extend(["", "## Frozen state semantics", ""])
    if contract["state_rules"]:
        for rule in contract["state_rules"]:
            requirement_lines.append(
                f"- **{rule['variable']}**: initial={str(rule['initial']).upper()}; "
                f"set when `({rule['set_when']})`; clear when `({rule['clear_when']})`; "
                f"simultaneous priority={rule['priority']}; otherwise=hold; "
                f"requirements={','.join(rule['requirement_ids'])}."
            )
    else:
        requirement_lines.append("- No retained BOOL output was declared by the frozen contract.")
    requirement_lines.extend([
        "", "## Assumptions", "",
        *[f"- {item}" for item in contract["assumptions"]],
        "", "## Output constraint", "",
        "Return one complete function-block implementation. Preserve the fixed interface exactly and use portable IEC 61131-3 ST without physical addresses, Markdown, or explanatory prose outside the program. Add detailed Simplified Chinese IEC block comments using only (* ... *). Explain the function block, every interface variable, retained state, scan-cycle behavior, safety priority, reset behavior, and each non-trivial branch for novice readers.",
    ])
    interface_lines = [f"FUNCTION_BLOCK {task_id}", "VAR_INPUT"]
    interface_lines.extend(f"    {item['name']} : {item['type']};" for item in interface["inputs"])
    interface_lines.extend(["END_VAR", "VAR_OUTPUT"])
    interface_lines.extend(f"    {item['name']} : {item['type']};" for item in interface["outputs"])
    interface_lines.extend(["END_VAR", "END_FUNCTION_BLOCK"])
    properties = {
        "schema_version": "1.0",
        "semantics": "end-of-scan state sequence; initial state precedes scan 1",
        "notation": "qualified PLCverif native invariant profile",
        "plcverif_profile": {
            "name": "native-pattern-invariant-v1",
            "policy": "every listed native case is mandatory",
            "native_property_count": len(contract["properties"]),
            "fully_native_property_count": len(contract["properties"]),
            "total_property_count": len(contract["properties"]),
            "environment": {"parameters": [], "assumption_invariants": []},
        },
        "properties": contract["properties"],
        "semantic_audit": contract["semantic_audit"],
        "oracle_provenance": oracle_provenance,
    }
    tests = {
        "schema_version": "1.0",
        "suite": "openplc",
        "task_id": task_id,
        "scan_period_ms": contract["scan_period_ms"],
        "real_absolute_tolerance": 0.001,
        "oracle_source": oracle_provenance,
        "independent_requirement_oracle": True,
        "oracle_provenance": oracle_provenance,
        "semantic_audit": contract["semantic_audit"],
        "state_rules": contract["state_rules"],
        "cases": contract["tests"],
    }
    documents = {
        "metadata.json": metadata,
        "properties.json": properties,
        "openplc_tests.json": tests,
        "contract.json": {**contract, "oracle_provenance": oracle_provenance},
    }
    engineering_config = contract.get("engineering_config")
    if isinstance(engineering_config, dict):
        documents["engineering_config.json"] = engineering_config
    for name, document in documents.items():
        (root / name).write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (root / "requirement.md").write_text("\n".join(requirement_lines) + "\n", encoding="utf-8")
    (root / "interface.st").write_text("\n".join(interface_lines) + "\n", encoding="utf-8")

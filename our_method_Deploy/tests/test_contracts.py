from __future__ import annotations

import json
from pathlib import Path

import pytest

from plc_deploy import contracts
from plc_deploy.contracts import (
    ContractError,
    ContractInfrastructureError,
    compile_contract,
    has_passed_semantic_audit,
    normalize_contract,
    write_task_package,
)
from plc_loop.models import ModelReply
from plc_loop.dataset import load_task


def sample() -> dict:
    return {
        "title": "Motor permissive",
        "scan_period_ms": 100,
        "assumptions": ["One call per scan"],
        "inputs": [{"name": "Start", "type": "BOOL"}, {"name": "Stop", "type": "BOOL"}],
        "outputs": [{"name": "Motor", "type": "BOOL"}],
        "requirements": [{"id": "R1", "text": "Stop has priority", "safety_critical": True}],
        "state_rules": [],
        "properties": [{"requirement_ids": ["R1"], "kind": "safety", "invariant": "Motor = (Start AND NOT Stop)"}],
        "tests": [
            {"role": "feedback", "requirement_ids": ["R1"], "steps": [{"inputs": {"Start": True, "Stop": False}, "expect": {"Motor": True}}]},
            {"role": "sealed", "requirement_ids": ["R1"], "steps": [{"inputs": {"Start": True, "Stop": True}, "expect": {"Motor": False}}]},
        ],
    }


def latched_alarm_sample() -> dict:
    return {
        "title": "Latched overload alarm",
        "scan_period_ms": 100,
        "assumptions": ["One call per scan"],
        "inputs": [
            {"name": "Overload", "type": "BOOL"},
            {"name": "ResetButton", "type": "BOOL"},
        ],
        "outputs": [{"name": "FaultAlarm", "type": "BOOL"}],
        "requirements": [
            {
                "id": "R1",
                "text": "Overload sets FaultAlarm and it remains latched when Overload clears.",
                "safety_critical": True,
            },
            {
                "id": "R2",
                "text": "FaultAlarm clears only when Overload is false and ResetButton is true.",
                "safety_critical": True,
            },
        ],
        "state_rules": [{
            "variable": "FaultAlarm",
            "initial": False,
            "set_when": "Overload",
            "clear_when": "NOT Overload AND ResetButton",
            "priority": "set",
            "otherwise": "hold",
            "requirement_ids": ["R1", "R2"],
        }],
        "properties": [
            {
                "requirement_ids": ["R1"],
                "kind": "safety",
                "invariant": "Overload -> FaultAlarm",
            },
            {
                "requirement_ids": ["R2"],
                "kind": "safety",
                "invariant": "NOT Overload AND ResetButton -> NOT FaultAlarm",
            },
        ],
        "tests": [
            {
                "role": "feedback",
                "requirement_ids": ["R1", "R2"],
                "steps": [
                    {
                        "inputs": {"Overload": True, "ResetButton": False},
                        "expect": {"FaultAlarm": True},
                    },
                    {
                        "inputs": {"Overload": False, "ResetButton": False},
                        "expect": {"FaultAlarm": True},
                    },
                    {
                        "inputs": {"Overload": False, "ResetButton": True},
                        "expect": {"FaultAlarm": False},
                    },
                ],
            },
            {
                "role": "sealed",
                "requirement_ids": ["R1", "R2"],
                "steps": [{
                    "inputs": {"Overload": True, "ResetButton": True},
                    "expect": {"FaultAlarm": True},
                }],
            },
        ],
    }


def test_normalize_and_write(tmp_path: Path) -> None:
    contract = normalize_contract(sample(), "PLC_TEST")
    contract["oracle_provenance"] = "user_confirmed_llm_draft"
    root = tmp_path / "PLC_TEST"
    write_task_package(root, contract, "A motor request", "delta", "DVP48ES300R")
    task = load_task(root)
    assert task.task_id == "PLC_TEST"
    assert json.loads((root / "openplc_tests.json").read_text())["oracle_provenance"] == "user_confirmed_llm_draft"
    assert "DVP48ES300R" in (root / "requirement.md").read_text()


def test_rejects_incomplete_test_inputs() -> None:
    value = sample()
    del value["tests"][0]["steps"][0]["inputs"]["Stop"]
    with pytest.raises(ContractError, match="input mismatch"):
        normalize_contract(value, "PLC_TEST")


def test_rejects_incomplete_expected_outputs() -> None:
    value = sample()
    value["outputs"].append({"name": "Alarm", "type": "BOOL"})
    value["properties"].append({
        "requirement_ids": ["R1"],
        "kind": "functional",
        "invariant": "Alarm = FALSE",
    })
    with pytest.raises(ContractError, match="output mismatch.*Alarm"):
        normalize_contract(value, "PLC_TEST")


def test_requires_definitional_property_for_combinational_output() -> None:
    value = sample()
    value["properties"][0]["invariant"] = "Stop -> NOT Motor"
    with pytest.raises(ContractError, match="lack a definitional equality.*Motor"):
        normalize_contract(value, "PLC_TEST")


def test_rejects_non_interface_property_identifier() -> None:
    value = sample()
    value["properties"][0]["invariant"] = "InternalState = 1"
    with pytest.raises(ContractError, match="non-interface"):
        normalize_contract(value, "PLC_TEST")


def test_semantic_audit_rejects_latch_test_that_clears_without_reset() -> None:
    value = latched_alarm_sample()
    value["tests"][0]["steps"][1]["expect"]["FaultAlarm"] = False
    with pytest.raises(
        ContractError,
        match=(
            "state/test contradiction.*step 2.*set_when='Overload' evaluated False.*"
            "prior FaultAlarm=True"
        ),
    ):
        normalize_contract(value, "PLC_LATCH")


def test_semantic_audit_accepts_consistent_latch_lifecycle() -> None:
    contract = normalize_contract(latched_alarm_sample(), "PLC_LATCH")
    assert contract["semantic_audit"]["status"] == "passed"
    assert contract["semantic_audit"]["version"] == "deterministic-contract-semantics-v4"
    assert contract["semantic_audit"]["state_rules_checked"] == 1
    assert contract["semantic_audit"]["traceability"]["requirements_covered"] == 2
    assert contract["semantic_audit"]["traceability"]["rows"][1] == {
        "requirement_id": "R2",
        "safety_critical": True,
        "property_ids": ["P2"],
        "state_variables": ["FaultAlarm"],
        "feedback_test_ids": ["FT01"],
        "sealed_test_ids": ["OT01"],
    }


def test_rejects_self_referential_end_of_scan_equality_for_retained_output() -> None:
    value = latched_alarm_sample()
    value["properties"][0]["invariant"] = "FaultAlarm = (Overload OR FaultAlarm)"
    with pytest.raises(ContractError, match="invalid self-referential.*FaultAlarm"):
        normalize_contract(value, "PLC_LATCH")


def test_exhaustive_audit_finds_property_state_conflict_outside_runtime_tests() -> None:
    value = latched_alarm_sample()
    value["inputs"].append({"name": "Maintenance", "type": "BOOL"})
    for case in value["tests"]:
        for step in case["steps"]:
            step["inputs"]["Maintenance"] = False
    value["properties"].append({
        "requirement_ids": ["R2"],
        "kind": "safety",
        "invariant": "Maintenance -> NOT FaultAlarm",
    })
    with pytest.raises(ContractError, match="property/state-rule contradiction"):
        normalize_contract(value, "PLC_LATCH")


def test_reachable_state_audit_does_not_reject_unreachable_state_combinations() -> None:
    value = {
        "title": "Two-stage sequence",
        "scan_period_ms": 100,
        "assumptions": ["One call per scan"],
        "inputs": [
            {"name": "Start", "type": "BOOL"},
            {"name": "Switch", "type": "BOOL"},
            {"name": "Reset", "type": "BOOL"},
        ],
        "outputs": [
            {"name": "RunA", "type": "BOOL"},
            {"name": "RunB", "type": "BOOL"},
        ],
        "requirements": [{
            "id": "R1",
            "text": (
                "Start sets RunA and RunA remains retained until Switch or Reset. "
                "Switch clears RunA, sets RunB, and RunB remains retained until Reset."
            ),
            "safety_critical": True,
        }],
        "state_rules": [
            {
                "variable": "RunA", "initial": False,
                "set_when": "Start AND NOT RunB AND NOT Switch AND NOT Reset",
                "clear_when": "Switch OR Reset", "priority": "clear",
                "otherwise": "hold", "requirement_ids": ["R1"],
            },
            {
                "variable": "RunB", "initial": False,
                "set_when": "Switch AND NOT Reset", "clear_when": "Reset",
                "priority": "clear", "otherwise": "hold",
                "requirement_ids": ["R1"],
            },
        ],
        "properties": [{
            "requirement_ids": ["R1"], "kind": "safety",
            "invariant": "NOT (RunA AND RunB)",
        }],
        "tests": [
            {
                "role": "feedback", "requirement_ids": ["R1"],
                "steps": [
                    {"inputs": {"Start": True, "Switch": False, "Reset": False},
                     "expect": {"RunA": True, "RunB": False}},
                    {"inputs": {"Start": False, "Switch": True, "Reset": False},
                     "expect": {"RunA": False, "RunB": True}},
                ],
            },
            {
                "role": "sealed", "requirement_ids": ["R1"],
                "steps": [
                    {"inputs": {"Start": False, "Switch": True, "Reset": False},
                     "expect": {"RunA": False, "RunB": True}},
                    {"inputs": {"Start": False, "Switch": False, "Reset": True},
                     "expect": {"RunA": False, "RunB": False}},
                ],
            },
        ],
    }

    contract = normalize_contract(value, "PLC_SEQUENCE")

    assert contract["semantic_audit"]["status"] == "passed"
    assert contract["semantic_audit"]["reachable_states_checked"] == 3


def test_missing_stateful_priority_pair_gets_deterministic_runtime_case() -> None:
    value = latched_alarm_sample()
    contract = normalize_contract(
        value,
        "PLC_LATCH",
        source_requirement=(
            "Overload sets FaultAlarm and FaultAlarm remains latched until reset. "
            "Overload has priority over ResetButton."
        ),
    )
    generated = [
        case for case in contract["tests"]
        if "deterministic adjacent-priority check" in case["description"]
    ]
    assert contract["semantic_audit"]["generated_priority_cases"] == 1
    assert len(generated) == 1
    assert generated[0]["id"].startswith("FT")
    assert generated[0]["steps"][0]["inputs"] == {
        "Overload": True,
        "ResetButton": True,
    }
    assert generated[0]["steps"][0]["expect"] == {"FaultAlarm": True}


def test_traceability_rejects_requirement_missing_from_sealed_tests() -> None:
    value = latched_alarm_sample()
    value["tests"][1]["requirement_ids"] = ["R1"]
    with pytest.raises(ContractError, match="R2 lacks traceability.*sealed runtime test"):
        normalize_contract(value, "PLC_LATCH")


def test_traceability_requires_property_for_safety_requirement() -> None:
    value = latched_alarm_sample()
    value["properties"] = [value["properties"][0]]
    with pytest.raises(ContractError, match="R2 lacks traceability.*mandatory safety property"):
        normalize_contract(value, "PLC_LATCH")


def test_current_audit_cannot_be_forged_without_traceability_rows() -> None:
    contract = normalize_contract(sample(), "PLC_TEST")
    assert has_passed_semantic_audit(contract) is True
    del contract["semantic_audit"]["traceability"]
    assert has_passed_semantic_audit(contract) is False


def test_semantic_audit_requires_rule_for_retained_output() -> None:
    value = latched_alarm_sample()
    value["state_rules"] = []
    with pytest.raises(ContractError, match="omit retained outputs.*FaultAlarm"):
        normalize_contract(value, "PLC_LATCH")


def test_semantic_audit_removes_state_rule_for_combinational_output() -> None:
    value = sample()
    value["state_rules"] = [{
        "variable": "Motor",
        "initial": False,
        "set_when": "Start AND NOT Stop",
        "clear_when": "Stop",
        "priority": "clear",
        "otherwise": "hold",
        "requirement_ids": ["R1"],
    }]
    contract = normalize_contract(value, "PLC_TEST")
    assert contract["state_rules"] == []


def test_only_when_does_not_imply_retained_state() -> None:
    value = sample()
    value["requirements"][0]["text"] = "Motor runs only when Start is true and Stop is false."
    normalize_contract(value, "PLC_TEST")


def test_retention_word_is_attributed_to_nearest_output_only() -> None:
    requirements = [{
        "id": "R1",
        "text": (
            "Pump1Run and Pump2Run follow the current selection, and any fault sets and "
            "retains FaultAlarm"
        ),
    }]
    assert contracts._stateful_outputs(
        requirements, {"Pump1Run", "Pump2Run", "FaultAlarm"}
    ) == {"FaultAlarm"}


def test_original_requirement_prevents_llm_from_inventing_pump_latches() -> None:
    value = latched_alarm_sample()
    value["inputs"].extend([
        {"name": "Enable", "type": "BOOL"},
        {"name": "Stop", "type": "BOOL"},
    ])
    value["outputs"].append({"name": "Pump1Run", "type": "BOOL"})
    value["properties"].append({
        "requirement_ids": ["R1"],
        "kind": "functional",
        "invariant": "Pump1Run = (Enable AND NOT Stop)",
    })
    value["requirements"][0]["text"] = (
        "Pump1Run remains active until Stop; Overload latches FaultAlarm."
    )
    value["state_rules"].append({
        "variable": "Pump1Run",
        "initial": False,
        "set_when": "Enable AND NOT Stop",
        "clear_when": "Stop",
        "priority": "clear",
        "otherwise": "hold",
        "requirement_ids": ["R1"],
    })
    for case in value["tests"]:
        for step in case["steps"]:
            step["inputs"].update({"Enable": False, "Stop": False})
            step["expect"]["Pump1Run"] = False
    contract = normalize_contract(
        value,
        "PLC_DUAL",
        source_requirement=(
            "Enable=TRUE 且 Stop=FALSE 时运行被选择的泵；"
            "任一故障置位并保持 FaultAlarm。"
        ),
    )
    assert [rule["variable"] for rule in contract["state_rules"]] == ["FaultAlarm"]


def test_semantic_audit_rejects_property_test_contradiction() -> None:
    value = sample()
    value["tests"][1]["steps"][0]["expect"]["Motor"] = True
    with pytest.raises(ContractError, match="property/test contradiction"):
        normalize_contract(value, "PLC_TEST")


def test_semantic_audit_rejects_lower_event_overriding_explicit_priority() -> None:
    value = {
        "title": "Two-stage sequence",
        "inputs": [
            {"name": name, "type": "BOOL"}
            for name in ("Start", "Stage1Done", "Stage2Done", "Stop", "Reset")
        ],
        "outputs": [
            {"name": name, "type": "BOOL"}
            for name in ("Stage1Run", "Stage2Run", "Complete")
        ],
        "requirements": [
            {"id": "R1", "text": "Stage1Run remains latched; Stage2Run remains latched; Complete remains latched."},
            {"id": "R2", "text": "优先级从高到低为 Reset、Stop、Stage1Done/Stage2Done、Start。", "safety_critical": True},
        ],
        "state_rules": [
            {"variable": "Stage1Run", "initial": False, "set_when": "Start", "clear_when": "Reset OR Stop OR Stage1Done", "priority": "clear", "otherwise": "hold", "requirement_ids": ["R1", "R2"]},
            {"variable": "Stage2Run", "initial": False, "set_when": "Stage1Done AND Stage1Run", "clear_when": "Reset OR Stop OR Stage2Done", "priority": "clear", "otherwise": "hold", "requirement_ids": ["R1", "R2"]},
            {"variable": "Complete", "initial": False, "set_when": "Stage2Done AND Stage2Run", "clear_when": "Reset", "priority": "clear", "otherwise": "hold", "requirement_ids": ["R1", "R2"]},
        ],
        "properties": [
            {"requirement_ids": ["R2"], "invariant": "Reset -> (NOT Stage1Run AND NOT Stage2Run AND NOT Complete)"},
        ],
        "tests": [
            {"role": role, "requirement_ids": ["R1", "R2"], "steps": [
                {"inputs": {"Start": True, "Stage1Done": False, "Stage2Done": False, "Stop": False, "Reset": False}, "expect": {"Stage1Run": True, "Stage2Run": False, "Complete": False}},
                {"inputs": {"Start": False, "Stage1Done": True, "Stage2Done": False, "Stop": False, "Reset": False}, "expect": {"Stage1Run": False, "Stage2Run": True, "Complete": False}},
                {"inputs": {"Start": False, "Stage1Done": False, "Stage2Done": True, "Stop": True, "Reset": False}, "expect": {"Stage1Run": False, "Stage2Run": False, "Complete": True}},
            ]}
            for role in ("feedback", "sealed")
        ],
    }
    with pytest.raises(
        ContractError,
        match="priority contradiction.*Complete.*actual=True.*lower-suppressed=False.*set_when",
    ):
        normalize_contract(value, "PLC_SEQUENCE")


def test_semantic_audit_requires_priority_pairs_in_both_test_roles() -> None:
    value = sample()
    value["requirements"][0]["text"] = "Priority from highest to lowest: Stop > Start."
    with pytest.raises(ContractError, match="incomplete feedback priority coverage.*Stop>Start"):
        normalize_contract(value, "PLC_TEST")


def test_pairwise_priority_wording_is_audited() -> None:
    value = sample()
    value["requirements"][0]["text"] = "Stop has priority over Start."
    with pytest.raises(ContractError, match="incomplete feedback priority coverage.*Stop>Start"):
        normalize_contract(value, "PLC_TEST")


def test_higher_event_cannot_mask_priority_pair_coverage() -> None:
    value = sample()
    value["inputs"].append({"name": "Reset", "type": "BOOL"})
    value["requirements"][0]["text"] = (
        "Priority from highest to lowest: Reset > Stop > Start."
    )
    value["properties"][0]["invariant"] = (
        "Motor = (Start AND NOT Stop AND NOT Reset)"
    )
    for case in value["tests"]:
        for step in case["steps"]:
            step["inputs"]["Reset"] = True
            step["inputs"]["Start"] = True
            step["inputs"]["Stop"] = True
            step["expect"]["Motor"] = False
    with pytest.raises(ContractError, match="incomplete feedback priority coverage.*Stop>Start"):
        normalize_contract(value, "PLC_TEST")


def test_original_requirement_priority_cannot_be_erased_by_paraphrase() -> None:
    value = sample()
    value["requirements"][0]["text"] = "Stop has priority over Start."
    with pytest.raises(ContractError, match="incomplete feedback priority coverage.*Stop>Start"):
        normalize_contract(
            value,
            "PLC_TEST",
            source_requirement="优先级从高到低为 Stop、Start；同时输入按此顺序处理。",
        )


def test_priority_parser_ignores_interface_declaration_order() -> None:
    groups = contracts._extract_priority_groups(
        [{"text": (
            "输入 Start、Stage1Done、Stage2Done、Stop、Reset 均为 BOOL；"
            "Reset 优先级最高，其次 Stop，再次完成信号，最后 Start。"
        )}],
        {"Start", "Stage1Done", "Stage2Done", "Stop", "Reset"},
    )
    assert groups == [
        {"Reset"}, {"Stop"}, {"Stage1Done", "Stage2Done"}, {"Start"}
    ]


def test_contract_generation_repairs_deterministic_schema_error(monkeypatch) -> None:
    invalid = sample()
    invalid["tests"][0]["steps"][0]["repeat"] = 0
    replies = [invalid, sample()]

    class FakeClient:
        def __init__(self, settings):
            self.calls = 0

        def generate(self, messages):
            value = replies[self.calls]
            self.calls += 1
            message = {"role": "assistant", "content": json.dumps(value)}
            return ModelReply(
                message=message,
                raw_response={},
                requested_model="test-model",
                resolved_model="test-model",
                provider="test",
                usage={"total_tokens": 10},
                finish_reason="stop",
                latency_ms=2,
            )

    monkeypatch.setattr(contracts, "OpenAICompatibleClient", FakeClient)
    contract, audit = compile_contract(
        "Create a motor controller with a stop-priority safety interlock.",
        {"label": "Delta"},
        {"label": "DVP48ES300R", "iec_profile": "portable", "notes": "test"},
        {
            "name": "test",
            "base_url": "https://example.test/v1",
            "api_key_env": "UNUSED",
            "requested_model": "test-model",
            "allowed_resolved_models": ["test-model"],
        },
        "PLC_TEST",
    )

    assert contract["task_id"] == "PLC_TEST"
    assert [item["status"] for item in audit["attempts"]] == ["rejected", "accepted"]
    assert audit["usage"]["total_tokens"] == 20


def test_contract_generation_resume_continues_remaining_budget_and_usage(monkeypatch) -> None:
    seen = {}

    class FakeClient:
        def __init__(self, settings):
            pass

        def generate(self, messages):
            seen["messages"] = messages
            return ModelReply(
                message={"role": "assistant", "content": json.dumps(sample())},
                raw_response={}, requested_model="test-model", resolved_model="test-model",
                provider="test", usage={"total_tokens": 10}, finish_reason="stop",
                latency_ms=2,
            )

    monkeypatch.setattr(contracts, "OpenAICompatibleClient", FakeClient)
    events = []
    _, audit = compile_contract(
        "motor", {"label": "Delta"},
        {"label": "DVP48ES300R", "iec_profile": "portable", "notes": "test"},
        {"name": "test", "base_url": "https://example.test/v1", "api_key_env": "UNUSED",
         "requested_model": "test-model", "allowed_resolved_models": ["test-model"]},
        "PLC_TEST", progress_callback=events.append,
        attempt_offset=4, attempt_budget=6,
        prior_usage={"total_tokens": 100}, prior_latency_ms=9,
        resume_draft=json.dumps(sample()), resume_error="state/test contradiction",
    )

    assert events[0] == {
        "attempt": 4, "maximum_attempts": 10, "status": "resuming"
    }
    assert audit["attempts"][0]["attempt"] == 5
    assert audit["resumed_after_attempt"] == 4
    assert audit["attempt_budget"] == 10
    assert audit["usage"]["total_tokens"] == 110
    assert audit["latency_ms"] == 11
    assert [message["role"] for message in seen["messages"]] == [
        "system", "user", "assistant", "user"
    ]


def test_contract_generation_uses_contract_only_thinking_mode(monkeypatch) -> None:
    seen = {}

    class FakeClient:
        def __init__(self, settings):
            seen["thinking_mode"] = settings.thinking_mode

        def generate(self, messages):
            seen["system_prompt"] = messages[0]["content"]
            return ModelReply(
                message={"role": "assistant", "content": json.dumps(sample())},
                raw_response={}, requested_model="test-model", resolved_model="test-model",
                provider="test", usage={}, finish_reason="stop", latency_ms=1,
            )

    monkeypatch.setattr(contracts, "OpenAICompatibleClient", FakeClient)
    compile_contract(
        "motor", {"label": "Delta"},
        {"label": "DVP48ES300R", "iec_profile": "portable", "notes": "test"},
        {"name": "test", "base_url": "https://example.test/v1", "api_key_env": "UNUSED",
         "requested_model": "test-model", "allowed_resolved_models": ["test-model"],
         "contract_thinking_mode": "disabled"},
        "PLC_TEST",
    )
    assert seen["thinking_mode"] == "disabled"
    assert "retained multi-stage sequence" in seen["system_prompt"]
    assert "ignore Start while a later stage" in seen["system_prompt"]


def test_contract_generation_reports_token_exhaustion(monkeypatch) -> None:
    class FakeClient:
        def __init__(self, settings):
            pass

        def generate(self, messages):
            return ModelReply(
                message={"role": "assistant", "content": "", "reasoning_content": "unfinished"},
                raw_response={}, requested_model="test-model", resolved_model="test-model",
                provider="test", usage={}, finish_reason="length", latency_ms=1,
            )

    monkeypatch.setattr(contracts, "OpenAICompatibleClient", FakeClient)
    events = []
    with pytest.raises(ContractError, match="exhausted its output-token limit"):
        compile_contract(
            "motor", {"label": "Delta"},
            {"label": "DVP48ES300R", "iec_profile": "portable", "notes": "test"},
            {"name": "test", "base_url": "https://example.test/v1", "api_key_env": "UNUSED",
             "requested_model": "test-model", "allowed_resolved_models": ["test-model"]},
            "PLC_TEST", progress_callback=events.append,
        )
    statuses = [event["status"] for event in events]
    assert statuses[0] == "preparing"
    assert statuses.count("requesting") == contracts.CONTRACT_ATTEMPT_BUDGET
    assert statuses.count("received") == contracts.CONTRACT_ATTEMPT_BUDGET
    assert statuses.count("validating") == contracts.CONTRACT_ATTEMPT_BUDGET
    assert statuses.count("rejected") == contracts.CONTRACT_ATTEMPT_BUDGET
    assert statuses.count("blind_rebuild") == 3


def test_contract_generation_retries_client_level_length_failure(monkeypatch) -> None:
    seen = {}

    class FakeClient:
        def __init__(self, settings):
            self.calls = 0
            seen["max_output_tokens"] = settings.max_output_tokens

        def generate(self, messages):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError(
                    "provider returned empty assistant content (finish_reason='length')"
                )
            return ModelReply(
                message={"role": "assistant", "content": json.dumps(sample())},
                raw_response={}, requested_model="test-model", resolved_model="test-model",
                provider="test", usage={"total_tokens": 10},
                finish_reason="stop", latency_ms=2,
            )

    monkeypatch.setattr(contracts, "OpenAICompatibleClient", FakeClient)
    events = []
    contract, audit = compile_contract(
        "motor", {"label": "Delta"},
        {"label": "DVP48ES300R", "iec_profile": "portable", "notes": "test"},
        {
            "name": "test", "base_url": "https://example.test/v1",
            "api_key_env": "UNUSED", "requested_model": "test-model",
            "allowed_resolved_models": ["test-model"],
            "contract_max_output_tokens": 16384,
        },
        "PLC_TEST", output_language="ld", progress_callback=events.append,
    )
    assert contract["task_id"] == "PLC_TEST"
    assert seen["max_output_tokens"] == 16384
    assert [item["status"] for item in audit["attempts"]] == ["rejected", "accepted"]
    assert [event["status"] for event in events] == [
        "preparing", "requesting", "rejected",
        "requesting", "received", "validating", "accepted",
    ]


def test_contract_generation_blind_rebuilds_after_three_invalid_drafts(monkeypatch) -> None:
    invalid = sample()
    invalid["tests"][0]["steps"][0]["repeat"] = 0
    seen_messages = []

    class FakeClient:
        def __init__(self, settings):
            self.calls = 0

        def generate(self, messages):
            self.calls += 1
            seen_messages.append(messages)
            value = invalid if self.calls <= 3 else sample()
            message = {"role": "assistant", "content": json.dumps(value)}
            return ModelReply(
                message=message, raw_response={}, requested_model="test-model",
                resolved_model="test-model", provider="test", usage={},
                finish_reason="stop", latency_ms=1,
            )

    monkeypatch.setattr(contracts, "OpenAICompatibleClient", FakeClient)
    _, audit = compile_contract(
        "motor", {"label": "Delta"},
        {"label": "DVP48ES300R", "iec_profile": "portable", "notes": "test"},
        {"name": "test", "base_url": "https://example.test/v1", "api_key_env": "UNUSED",
         "requested_model": "test-model", "allowed_resolved_models": ["test-model"]},
        "PLC_TEST",
    )
    assert [item["status"] for item in audit["attempts"]] == [
        "rejected", "rejected", "rejected", "accepted"
    ]
    assert len(seen_messages[3]) == 2
    assert "Rebuild the contract from the original user request" in seen_messages[3][1]["content"]


def test_contract_generation_preserves_repair_context_while_error_family_changes(
    monkeypatch,
) -> None:
    invalid_repeat = sample()
    invalid_repeat["tests"][0]["steps"][0]["repeat"] = 0
    missing_trace = sample()
    missing_trace["tests"][1]["requirement_ids"] = []
    seen_messages = []
    replies = [invalid_repeat, missing_trace, sample()]

    class FakeClient:
        def __init__(self, settings):
            self.calls = 0

        def generate(self, messages):
            seen_messages.append(messages)
            value = replies[self.calls]
            self.calls += 1
            return ModelReply(
                message={"role": "assistant", "content": json.dumps(value)},
                raw_response={}, requested_model="test-model", resolved_model="test-model",
                provider="test", usage={}, finish_reason="stop", latency_ms=1,
            )

    monkeypatch.setattr(contracts, "OpenAICompatibleClient", FakeClient)
    _, audit = compile_contract(
        "motor", {"label": "Delta"},
        {"label": "DVP48ES300R", "iec_profile": "portable", "notes": "test"},
        {"name": "test", "base_url": "https://example.test/v1", "api_key_env": "UNUSED",
         "requested_model": "test-model", "allowed_resolved_models": ["test-model"]},
        "PLC_TEST",
    )
    assert [item["status"] for item in audit["attempts"]] == [
        "rejected", "rejected", "accepted"
    ]
    assert len(seen_messages[2]) == 6
    assert "Rebuild the contract from the original user request" not in str(seen_messages[2])


def test_contract_network_outage_is_infrastructure_error_without_llm_level_loop(
    monkeypatch,
) -> None:
    calls = []

    class OfflineClient:
        def __init__(self, settings):
            pass

        def generate(self, messages):
            calls.append(messages)
            raise RuntimeError(
                "provider request failed after transport retries: network unreachable"
            )

    monkeypatch.setattr(contracts, "OpenAICompatibleClient", OfflineClient)
    with pytest.raises(ContractInfrastructureError, match="网络连接"):
        compile_contract(
            "motor", {"label": "Delta"},
            {"label": "DVP48ES300R", "iec_profile": "portable", "notes": "test"},
            {"name": "test", "base_url": "https://example.test/v1",
             "api_key_env": "UNUSED", "requested_model": "test-model",
             "allowed_resolved_models": ["test-model"]},
            "PLC_TEST",
        )
    assert len(calls) == 1


def test_contract_local_provider_queue_timeout_has_distinct_diagnostic(monkeypatch) -> None:
    class SaturatedClient:
        def __init__(self, settings):
            pass

        def generate(self, messages):
            raise RuntimeError("provider concurrency queue timed out")

    monkeypatch.setattr(contracts, "OpenAICompatibleClient", SaturatedClient)
    with pytest.raises(ContractInfrastructureError, match="本地模型调用队列"):
        compile_contract(
            "motor", {"label": "Delta"},
            {"label": "DVP48ES300R", "iec_profile": "portable", "notes": "test"},
            {"name": "test", "base_url": "https://example.test/v1",
             "api_key_env": "UNUSED", "requested_model": "test-model",
             "allowed_resolved_models": ["test-model"]},
            "PLC_TEST",
        )

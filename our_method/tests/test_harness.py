from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from plc_loop.client import ProviderSettings
from plc_loop.context import (
    build_task_state,
    derive_contract_risk_obligations,
    load_pattern_cards,
    retrieve_pattern_cards,
)
from plc_loop.dataset import load_task
from plc_loop.ledger import EvidenceLedger
from plc_loop.models import AttemptOutcome, Evidence, GateResult, ModelReply, ParsedCandidate
from plc_loop.orchestrator import BoundedSynthesisHarness
from plc_loop.policy import build_evidence_certificate_v3, choose_anchor
from plc_loop.process import run_captured
from plc_loop.response import parse_candidate
from plc_loop.validators import DatasetScanValidator, InterfaceValidator

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from formal_plcverif import cbmc_verdict, compact_counterexample, is_candidate_source_defect
from matiec_validator import diagnostic_excerpt
from openplc_sealed_validator import case_role
from audit_test_assumptions import audit_task
from openplc_container_runner import compact_scan_prefix

SOURCE_CODES = Path(__file__).resolve().parents[2]
if str(SOURCE_CODES) not in sys.path:
    sys.path.insert(0, str(SOURCE_CODES))
from baseline0_external_runner import ExternalBaselineHarness, is_resource_bounded_inconclusive


ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / "datasets/tasks/C01_M01_two_out_of_three_vote"
ENGINE_ROOT = Path(
    os.environ.get(
        "PLC_SCAN_ENGINE_ROOT",
        str(Path(__file__).resolve().parents[4] / "ISPSoft_CLI_Linux/src"),
    )
)


def tagged(program: str, target: str = "R1") -> str:
    return (
        "<repair_hypothesis>replace the failing implementation</repair_hypothesis>\n"
        f"<target_requirements>{target}</target_requirements>\n"
        f"<st_program>\n{program}\n</st_program>"
    )


class FakeClient:
    def __init__(self, replies: list[str]):
        self.replies = list(replies)
        self.calls: list[list[dict]] = []

    def generate(self, messages):
        self.calls.append(messages)
        if not self.replies:
            raise AssertionError("unexpected model call")
        content = self.replies.pop(0)
        message = {"role": "assistant", "content": content, "reasoning_content": "retained-for-history"}
        return ModelReply(
            message=message,
            raw_response={"model": "fake-model", "choices": [{"message": message, "finish_reason": "stop"}]},
            requested_model="fake-model",
            resolved_model="fake-model",
            provider="fake",
            usage={"prompt_tokens": 10, "completion_tokens": 5},
            finish_reason="stop",
            latency_ms=1,
        )


class FakeValidator:
    def __init__(
        self,
        name: str,
        *,
        sealed: bool = False,
        sealed_status: str | tuple[str, ...] = "pass",
        inconclusive_is_blocking: bool = True,
    ):
        self.name = name
        self.sealed = sealed
        self.blocking = True
        self.inconclusive_is_blocking = inconclusive_is_blocking
        self.sealed_status = sealed_status
        self.calls = 0

    def preflight(self, task):
        pass

    def run(self, task, candidate_path, artifact_dir):
        self.calls += 1
        if self.sealed:
            status = self.sealed_status
            if isinstance(status, tuple):
                status = status[self.calls - 1]
            return GateResult(self.name, status, "sealed result")
        source = candidate_path.read_text(encoding="utf-8")
        if "GOOD" in source:
            return GateResult(self.name, "pass", "visible pass", passed_requirement_ids=("R1",))
        return GateResult(
            self.name,
            "fail",
            "visible failure",
            evidence=(Evidence(self.name, "test_failure", "expected GOOD", ("R1",)),),
        )


class SequenceValidator:
    def __init__(self, name: str, statuses: list[str], *, retries: int):
        self.name = name
        self.statuses = list(statuses)
        self.inconclusive_retries = retries
        self.inconclusive_retry_delay_seconds = 0
        self.sealed = False
        self.blocking = True
        self.inconclusive_is_blocking = True
        self.calls = 0

    def preflight(self, task):
        pass

    def run(self, task, candidate_path, artifact_dir):
        status = self.statuses[min(self.calls, len(self.statuses) - 1)]
        self.calls += 1
        evidence = (
            (Evidence(self.name, "tool_error", "temporary timeout"),)
            if status == "inconclusive" else ()
        )
        return GateResult(
            self.name,
            status,
            status,
            evidence=evidence,
            passed_requirement_ids=("R1",) if status == "pass" else (),
        )


def config(max_candidates: int = 10, history_mode: str = "stateless") -> dict:
    return {
        "provider": {
            "name": "fake",
            "base_url": "https://example.invalid/v1",
            "api_key_env": "NEVER_READ_IN_FAKE_TEST",
            "requested_model": "fake-model",
            "allowed_resolved_models": ["fake-model"],
            "history_mode": history_mode,
        },
        "experiment": {
            "max_candidates": max_candidates,
            "max_feedback_chars": 2000,
            "required_visible_gates": ["visible"],
            "sealed_gate": "sealed",
            "stop_on_visible_pass": True,
        },
    }


class HarnessTests(unittest.TestCase):
    def test_timeout_terminates_complete_process_group(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "descendant_received_term"
            child = (
                "import pathlib,signal,sys,time; "
                f"p=pathlib.Path({str(marker)!r}); "
                "signal.signal(signal.SIGTERM, lambda *_: (p.write_text('term'), sys.exit(0))); "
                "print('ready', flush=True); time.sleep(30)"
            )
            parent = (
                "import subprocess,sys,time; "
                f"subprocess.Popen([sys.executable, '-c', {child!r}]); "
                "time.sleep(30)"
            )
            with self.assertRaises(subprocess.TimeoutExpired):
                run_captured([sys.executable, "-c", parent], timeout=0.5)
            deadline = time.monotonic() + 2
            while not marker.exists() and time.monotonic() < deadline:
                time.sleep(0.05)
            self.assertTrue(marker.exists(), "descendant did not receive process-group termination")

    def test_unterminated_st_wrapper_recovers_only_one_complete_function_block(self):
        content = (
            "<repair_hypothesis>complete candidate</repair_hypothesis>\n"
            "<target_requirements>R1</target_requirements>\n"
            "<st_program>\nFUNCTION_BLOCK Demo\nEND_FUNCTION_BLOCK"
        )
        parsed = parse_candidate({"content": content}, {"R1"})
        self.assertTrue(parsed.format_valid)
        self.assertEqual(parsed.extraction_mode, "unterminated_tag_recovery")
        self.assertTrue(parsed.program.endswith("END_FUNCTION_BLOCK\n"))

    def test_unterminated_st_wrapper_rejects_incomplete_or_trailing_text(self):
        base = (
            "<repair_hypothesis>x</repair_hypothesis>\n"
            "<target_requirements>R1</target_requirements>\n<st_program>\n"
        )
        for body in ("FUNCTION_BLOCK Demo", "FUNCTION_BLOCK Demo\nEND_FUNCTION_BLOCK\nprose"):
            parsed = parse_candidate({"content": base + body}, {"R1"})
            self.assertFalse(parsed.format_valid)
            self.assertIn("missing <st_program> block", parsed.format_errors)

    def test_early_stop_after_second_candidate(self):
        client = FakeClient([tagged("BAD"), tagged("GOOD")])
        visible = FakeValidator("visible")
        sealed = FakeValidator("sealed", sealed=True)
        with tempfile.TemporaryDirectory() as directory:
            harness = BoundedSynthesisHarness(
                config(), load_task(TASK), Path(directory) / "run", "evidence",
                client=client, validators=[visible, sealed],
            )
            result = harness.run()
            self.assertEqual(result["status"], "verified_success")
            self.assertEqual(result["candidates_used"], 2)
            self.assertTrue(result["stopped_early"])
            self.assertEqual(len(client.calls), 2)
            self.assertEqual(sealed.calls, 1)

    def test_malformed_response_consumes_candidate(self):
        client = FakeClient(["not a tagged candidate", tagged("GOOD")])
        visible = FakeValidator("visible")
        sealed = FakeValidator("sealed", sealed=True)
        with tempfile.TemporaryDirectory() as directory:
            result = BoundedSynthesisHarness(
                config(), load_task(TASK), Path(directory) / "run", "evidence",
                client=client, validators=[visible, sealed],
            ).run()
            self.assertEqual(result["candidates_used"], 2)
            self.assertEqual(result["attempts"][0]["gates"][0]["name"], "response_format")
            self.assertEqual(result["attempts"][0]["gates"][0]["status"], "fail")
            self.assertEqual(visible.calls, 1)

    def test_sealed_failure_is_terminal_and_not_feedback(self):
        client = FakeClient([tagged("GOOD"), tagged("GOOD")])
        visible = FakeValidator("visible")
        sealed = FakeValidator("sealed", sealed=True, sealed_status="fail")
        with tempfile.TemporaryDirectory() as directory:
            result = BoundedSynthesisHarness(
                config(), load_task(TASK), Path(directory) / "run", "evidence",
                client=client, validators=[visible, sealed],
            ).run()
            self.assertEqual(result["status"], "sealed_failure")
            self.assertEqual(result["candidates_used"], 1)
            self.assertEqual(len(client.calls), 1)
            self.assertEqual(sealed.calls, 1)

    def test_independent_candidate_continues_after_sealed_failure_without_feedback(self):
        client = FakeClient([tagged("GOOD"), tagged("GOOD")])
        visible = FakeValidator("visible")
        sealed = FakeValidator("sealed", sealed=True, sealed_status=("fail", "pass"))
        with tempfile.TemporaryDirectory() as directory:
            result = BoundedSynthesisHarness(
                config(max_candidates=2), load_task(TASK), Path(directory) / "run", "independent",
                client=client, validators=[visible, sealed],
            ).run()
            self.assertEqual(result["status"], "verified_success")
            self.assertEqual(result["candidates_used"], 2)
            self.assertEqual(result["winning_attempt"], 2)
            self.assertEqual(sealed.calls, 2)
            self.assertEqual([item["result"]["status"] for item in result["sealed_attempts"]], ["fail", "pass"])
            self.assertEqual(len(client.calls), 2)
            self.assertEqual(client.calls[0], client.calls[1])

    def test_evidence_blind_restart_uses_budget_without_sealed_feedback(self):
        class SecretSealedValidator(FakeValidator):
            def run(self, task, candidate_path, artifact_dir):
                self.calls += 1
                status = ("fail", "pass")[self.calls - 1]
                evidence = () if status == "pass" else (
                    Evidence(
                        self.name,
                        "openplc_functional_failure",
                        "SECRET_SEALED_DIAGNOSTIC",
                        ("R1",),
                        trace={"secret": "SECRET_SEALED_TRACE"},
                        oracle_status="confirmed_candidate_defect",
                    ),
                )
                return GateResult(self.name, status, "sealed result", evidence=evidence)

        value = config(max_candidates=2, history_mode="full")
        value["experiment"].update({
            "sealed_rejection_policy": "blind_restart",
            "max_sealed_attempts": 2,
            "blind_restart_profiles": ["contrastive_guard_table"],
        })
        client = FakeClient([tagged("GOOD_REJECTED_PROGRAM"), tagged("GOOD_SECOND_PROGRAM")])
        sealed = SecretSealedValidator("sealed", sealed=True)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            result = BoundedSynthesisHarness(
                value, load_task(TASK), output, "evidence",
                client=client, validators=[FakeValidator("visible"), sealed],
            ).run()
            self.assertEqual(result["status"], "verified_success")
            self.assertEqual(result["candidates_used"], 2)
            self.assertEqual(len(result["sealed_attempts"]), 2)
            self.assertEqual([item["generation_epoch"] for item in result["attempts"]], [1, 2])
            second_prompt = json.dumps(client.calls[1], ensure_ascii=False)
            self.assertNotIn("GOOD_REJECTED_PROGRAM", second_prompt)
            self.assertNotIn("SECRET_SEALED_DIAGNOSTIC", second_prompt)
            self.assertNotIn("SECRET_SEALED_TRACE", second_prompt)
            self.assertIn("contrastive_guard_table", second_prompt)
            entries = EvidenceLedger.verify(output / "ledger.jsonl")
            self.assertEqual(
                sum(item["event_type"] == "sealed_blind_restart_scheduled" for item in entries),
                1,
            )

    def test_duplicate_guard_does_not_spend_a_second_sealed_query(self):
        value = config(max_candidates=3)
        value["experiment"].update({
            "sealed_rejection_policy": "blind_restart",
            "max_sealed_attempts": 2,
            "blind_restart_profiles": ["contrastive_guard_table"],
            "duplicate_candidate_guard": True,
        })
        client = FakeClient([
            tagged("GOOD_REPEATED"), tagged("GOOD_REPEATED"), tagged("GOOD_DIFFERENT")
        ])
        sealed = FakeValidator("sealed", sealed=True, sealed_status=("fail", "pass"))
        with tempfile.TemporaryDirectory() as directory:
            result = BoundedSynthesisHarness(
                value, load_task(TASK), Path(directory) / "run", "evidence",
                client=client, validators=[FakeValidator("visible"), sealed],
            ).run()
            self.assertEqual(result["status"], "verified_success")
            self.assertEqual(result["candidates_used"], 3)
            self.assertEqual(sealed.calls, 2)
            novelty = next(
                gate for gate in result["attempts"][1]["gates"]
                if gate["name"] == "candidate_novelty"
            )
            self.assertEqual(novelty["status"], "fail")

    def test_contract_risk_obligations_cover_exception_and_pulse_semantics(self):
        root = ROOT / "datasets_50/tasks"
        bypass = derive_contract_risk_obligations(load_task(root / "C01_B04_composite"))
        restart = derive_contract_risk_obligations(load_task(root / "C02_B12_composite"))
        by_id = {item["requirement_id"]: item for item in bypass}
        restart_by_id = {item["requirement_id"]: item for item in restart}
        self.assertIn("contrastive_exception", by_id["R6"]["risk_types"])
        self.assertIn("one_scan_pulse", restart_by_id["R9"]["risk_types"])
        window = derive_contract_risk_obligations(
            load_task(root / "C06_W07_lean_composite")
        )
        window_by_id = {item["requirement_id"]: item for item in window}
        self.assertIn("threshold_crossing", window_by_id["R6"]["risk_types"])

    def test_assumption_audit_detects_out_of_contract_counter_vector(self):
        record = audit_task(ROOT / "datasets_50/tasks/C06_M02_bounded_up_down_counter")
        self.assertGreater(record["violation_count"], 0)
        self.assertTrue(any(
            item["variable"] == "Capacity" and item["value"] == -1
            for item in record["violations"]
        ))

    def test_visible_runtime_prefix_keeps_initial_state_and_input_deltas(self):
        case = {"steps": [
            {"inputs": {"Start": False, "Proof": False}, "repeat": 1},
            {"inputs": {"Start": True, "Proof": False}, "repeat": 1},
            {"inputs": {"Start": True, "Proof": True}, "repeat": 5},
        ]}
        prefix = compact_scan_prefix(case, 3, 4)
        self.assertEqual(prefix[0]["input_changes"], {"Start": False, "Proof": False})
        self.assertEqual(prefix[1]["input_changes"], {"Start": True})
        self.assertEqual(prefix[2]["input_changes"], {"Proof": True})
        self.assertEqual(prefix[2]["repeat_through"], 4)

    def test_full_history_preserves_complete_assistant_message(self):
        client = FakeClient([tagged("BAD"), tagged("GOOD")])
        with tempfile.TemporaryDirectory() as directory:
            BoundedSynthesisHarness(
                config(history_mode="full"), load_task(TASK), Path(directory) / "run", "evidence",
                client=client, validators=[FakeValidator("visible"), FakeValidator("sealed", sealed=True)],
            ).run()
            second_messages = client.calls[1]
            assistant = next(message for message in second_messages if message.get("role") == "assistant")
            self.assertEqual(assistant["reasoning_content"], "retained-for-history")

    def test_state_packet_strategy_compacts_conversation_and_writes_context(self):
        client = FakeClient([tagged("BAD"), tagged("GOOD")])
        value = config(history_mode="full")
        value["experiment"].update({
            "context_strategy": "state_packet",
            "certificate_version": "v2",
            "domain_context": {"enabled": True, "max_cards": 3, "max_chars": 4000},
        })
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            result = BoundedSynthesisHarness(
                value, load_task(TASK), output, "evidence",
                client=client, validators=[FakeValidator("visible"), FakeValidator("sealed", sealed=True)],
            ).run()
            self.assertEqual(result["status"], "verified_success")
            self.assertEqual(len(client.calls[1]), 2)
            state = json.loads((output / "attempts/attempt_02/task_state.json").read_text())
            self.assertEqual(state["format"], "bounded-agent-state-v2")
            self.assertTrue(state["retrieved_pattern_cards"])

    def test_partial_formal_support_is_kept_but_failed_requirement_is_removed(self):
        outcome = AttemptOutcome(
            number=1,
            candidate_path="candidate.st",
            candidate_sha256="one",
            candidate=ParsedCandidate("PROGRAM", "hypothesis", ("R1", "R2"), True),
            gates=[GateResult(
                "plcverif",
                "fail",
                "one property failed",
                evidence=(Evidence(
                    "plcverif", "formal_counterexample", "R2 false", ("R2",),
                    oracle_status="formal_counterexample_pending_runtime_replay",
                ),),
                passed_requirement_ids=("R1", "R2"),
            )],
            repair_mode="SYNTHESIZE",
            anchor_attempt=None,
        )
        self.assertEqual(outcome.failed_requirements, {"R2"})
        self.assertEqual(outcome.passed_requirements, {"R1"})

    def test_equal_evidence_anchor_prefers_newest_candidate(self):
        def outcome(number):
            return AttemptOutcome(
                number=number,
                candidate_path=f"candidate-{number}.st",
                candidate_sha256=str(number),
                candidate=ParsedCandidate("PROGRAM", "hypothesis", ("R1",), True),
                gates=[GateResult("plcverif", "pass", "pass", passed_requirement_ids=("R1",))],
                repair_mode="PATCH",
                anchor_attempt=number - 1 or None,
            )
        self.assertEqual(choose_anchor([outcome(1), outcome(2)], {"R1"}).number, 2)

    def test_certificate_v3_is_hard_bounded_and_excludes_tool_errors(self):
        candidate = ParsedCandidate("PROGRAM", "h" * 2000, ("R1",), True)
        confirmed = Evidence(
            "plcverif", "formal_counterexample", "P1 is false", ("R1",),
            trace={"violated_condition": "X" * 5000},
            oracle_status="formal_counterexample_pending_runtime_replay",
        )
        unconfirmed = Evidence("plcverif", "tool_error", "timeout" * 1000, ("R1",))
        attempt = AttemptOutcome(
            1, "candidate.st", "hash", candidate,
            [GateResult("plcverif", "fail", "failure", evidence=(confirmed, unconfirmed))],
            "SYNTHESIZE", None,
        )
        certificate = build_evidence_certificate_v3([attempt], attempt, {"R1"}, 2000)
        self.assertLessEqual(len(json.dumps(certificate, ensure_ascii=False, sort_keys=True)), 2000)
        self.assertEqual([item["kind"] for item in certificate["selected_failures"]], ["formal_counterexample"])

    def test_transient_validator_failure_retries_same_candidate_without_new_api_call(self):
        client = FakeClient([tagged("GOOD"), tagged("UNUSED")])
        visible = SequenceValidator("visible", ["inconclusive", "pass"], retries=1)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            result = BoundedSynthesisHarness(
                config(max_candidates=2), load_task(TASK), output, "evidence",
                client=client, validators=[visible, FakeValidator("sealed", sealed=True)],
            ).run()
            self.assertEqual(result["status"], "verified_success")
            self.assertEqual(result["candidates_used"], 1)
            self.assertEqual(len(client.calls), 1)
            self.assertEqual(visible.calls, 2)
            self.assertTrue((output / "attempts/attempt_01/visible.inconclusive_retries.json").is_file())

    def test_persistent_validator_failure_stops_without_spending_candidate_budget(self):
        client = FakeClient([tagged("GOOD"), tagged("UNUSED")])
        visible = SequenceValidator("visible", ["inconclusive", "inconclusive"], retries=1)
        with tempfile.TemporaryDirectory() as directory:
            result = BoundedSynthesisHarness(
                config(max_candidates=2), load_task(TASK), Path(directory) / "run", "evidence",
                client=client, validators=[visible, FakeValidator("sealed", sealed=True)],
            ).run()
            self.assertEqual(result["status"], "infrastructure_error")
            self.assertEqual(result["candidates_used"], 1)
            self.assertEqual(len(client.calls), 1)

    def test_persistent_inconclusive_can_use_one_blind_public_restart(self):
        client = FakeClient([tagged("GOOD_FIRST"), tagged("GOOD_SECOND")])
        visible = SequenceValidator(
            "visible", ["inconclusive", "inconclusive", "pass"], retries=1
        )
        value = config(max_candidates=2, history_mode="full")
        value["experiment"].update({
            "inconclusive_recovery_policy": "blind_restart",
            "max_inconclusive_restarts": 1,
            "blind_restart_profiles": ["minimal_priority_chain"],
        })
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            result = BoundedSynthesisHarness(
                value, load_task(TASK), output, "evidence",
                client=client, validators=[visible, FakeValidator("sealed", sealed=True)],
            ).run()
            self.assertEqual(result["status"], "verified_success")
            self.assertEqual(result["candidates_used"], 2)
            self.assertEqual(result["mechanisms"]["inconclusive_restarts_used"], 1)
            second_prompt = json.dumps(client.calls[1], ensure_ascii=False)
            self.assertNotIn("GOOD_FIRST", second_prompt)
            self.assertNotIn("temporary timeout", second_prompt)
            self.assertIn("verification_bounded_state", second_prompt)
            self.assertIn("global scan clock", second_prompt)
            self.assertIn("counter < threshold", second_prompt)
            request = json.loads(
                (output / "attempts/attempt_02/request.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                request["diversification_profile"], "verification_bounded_state"
            )
            entries = EvidenceLedger.verify(output / "ledger.jsonl")
            self.assertEqual(
                sum(
                    item["event_type"] == "inconclusive_blind_restart_scheduled"
                    for item in entries
                ),
                1,
            )

    def test_restart_does_not_include_abandoned_anchor_program(self):
        client = FakeClient([
            tagged("CANDIDATE_ONE"), tagged("CANDIDATE_TWO"),
            tagged("CANDIDATE_THREE"), tagged("CANDIDATE_FOUR"),
        ])
        with tempfile.TemporaryDirectory() as directory:
            result = BoundedSynthesisHarness(
                config(max_candidates=4), load_task(TASK), Path(directory) / "run", "evidence",
                client=client,
                validators=[FakeValidator("visible"), FakeValidator("sealed", sealed=True)],
            ).run()
            self.assertEqual(
                [item["repair_mode"] for item in result["attempts"]],
                ["SYNTHESIZE", "PATCH", "RESTRUCTURE", "RESTART"],
            )
            restart_prompt = client.calls[3][-1]["content"]
            anchor_section = restart_prompt.split("ANCHOR CANDIDATE (never a reference answer)\n", 1)[1]
            anchor_section = anchor_section.split("\n\nDETERMINISTIC VALIDATION FEEDBACK", 1)[0]
            self.assertEqual(anchor_section, "NONE")

    def test_certificate_v2_deduplicates_repeated_failure_signature(self):
        client = FakeClient([tagged("BAD"), tagged("BAD"), tagged("GOOD")])
        value = config(max_candidates=3)
        value["experiment"]["certificate_version"] = "v2"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            BoundedSynthesisHarness(
                value, load_task(TASK), output, "evidence",
                client=client, validators=[FakeValidator("visible"), FakeValidator("sealed", sealed=True)],
            ).run()
            certificate = json.loads(
                (output / "attempts/attempt_03/feedback_certificate.json").read_text()
            )
            self.assertEqual(certificate["format"], "requirement-aligned-failure-certificate-v2")
            self.assertEqual(len(certificate["selected_failures"]), 1)
            self.assertEqual(certificate["selected_failures"][0]["seen_count"], 2)
            self.assertEqual(len(certificate["attempt_history"]), 2)
            self.assertTrue(certificate["repair_directives"])

    def test_raw_repair_uses_latest_candidate_and_fixed_patch_mode(self):
        client = FakeClient([tagged("BAD_ONE"), tagged("BAD_TWO"), tagged("GOOD")])
        with tempfile.TemporaryDirectory() as directory:
            result = BoundedSynthesisHarness(
                config(max_candidates=3, history_mode="full"),
                load_task(TASK),
                Path(directory) / "run",
                "raw_repair",
                client=client,
                validators=[FakeValidator("visible"), FakeValidator("sealed", sealed=True)],
            ).run()
            self.assertEqual(result["status"], "verified_success")
            self.assertEqual(
                [attempt["anchor_attempt"] for attempt in result["attempts"]],
                [None, 1, 2],
            )
            self.assertEqual(
                [attempt["repair_mode"] for attempt in result["attempts"]],
                ["SYNTHESIZE", "PATCH", "PATCH"],
            )
            self.assertTrue(all(len(messages) == 2 for messages in client.calls))
            self.assertIn("BAD_TWO", client.calls[2][-1]["content"])
            self.assertNotIn("BAD_ONE", client.calls[2][-1]["content"])

    def test_rq2_component_one_ablation_contract_and_metadata(self):
        value = config(max_candidates=3)
        value["experiment"].update({
            "ablation_id": "M01_without_component_1",
            "core_component_1_enabled": False,
            "core_component_2_enabled": True,
            "anchor_policy": "latest",
            "repair_policy": "patch",
            "pre_emit_review": False,
            "contract_risk_analysis": False,
            "duplicate_candidate_guard": False,
            "sealed_rejection_policy": "blind_restart",
            "max_sealed_attempts": 3,
            "inconclusive_recovery_policy": "blind_restart",
            "max_inconclusive_restarts": 1,
        })
        with tempfile.TemporaryDirectory() as directory:
            result = BoundedSynthesisHarness(
                value,
                load_task(TASK),
                Path(directory) / "run",
                "raw_repair",
                client=FakeClient([tagged("GOOD")]),
                validators=[
                    FakeValidator("visible"),
                    FakeValidator("sealed", sealed=True),
                ],
            ).run()
        self.assertEqual(result["mechanisms"]["ablation_id"], "M01_without_component_1")
        self.assertFalse(result["mechanisms"]["core_component_1_enabled"])
        self.assertTrue(result["mechanisms"]["core_component_2_enabled"])

    def test_rq2_component_two_ablation_is_terminal_on_sealed_failure(self):
        value = config(max_candidates=3)
        value["experiment"].update({
            "ablation_id": "M10_without_component_2",
            "core_component_1_enabled": True,
            "core_component_2_enabled": False,
            "anchor_policy": "non_regression",
            "repair_policy": "adaptive",
            "pre_emit_review": True,
            "contract_risk_analysis": True,
            "duplicate_candidate_guard": True,
            "domain_context": {"enabled": True, "max_cards": 3, "max_chars": 4000},
            "sealed_rejection_policy": "terminal",
            "max_sealed_attempts": 1,
            "inconclusive_recovery_policy": "terminal",
            "max_inconclusive_restarts": 0,
        })
        client = FakeClient([tagged("GOOD"), tagged("UNUSED")])
        with tempfile.TemporaryDirectory() as directory:
            result = BoundedSynthesisHarness(
                value,
                load_task(TASK),
                Path(directory) / "run",
                "evidence",
                client=client,
                validators=[
                    FakeValidator("visible"),
                    FakeValidator("sealed", sealed=True, sealed_status="fail"),
                ],
            ).run()
        self.assertEqual(result["status"], "sealed_failure")
        self.assertEqual(len(client.calls), 1)
        self.assertTrue(result["mechanisms"]["core_component_1_enabled"])
        self.assertFalse(result["mechanisms"]["core_component_2_enabled"])

    def test_rq2_ablation_label_rejects_inconsistent_mechanism_flags(self):
        value = config(max_candidates=3)
        value["experiment"].update({
            "ablation_id": "M10_without_component_2",
            "core_component_1_enabled": True,
            "core_component_2_enabled": True,
        })
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "RQ2 ablation contract"):
                BoundedSynthesisHarness(
                    value,
                    load_task(TASK),
                    Path(directory) / "run",
                    "evidence",
                    client=FakeClient([]),
                    validators=[
                        FakeValidator("visible"),
                        FakeValidator("sealed", sealed=True),
                    ],
                )

    def test_optional_formal_inconclusive_does_not_pass_or_block_but_failure_blocks(self):
        optional_formal = FakeValidator("formal", inconclusive_is_blocking=False)
        harness = BoundedSynthesisHarness(
            config(), load_task(TASK), Path("/tmp/not-run"), "independent",
            client=FakeClient([]), validators=[FakeValidator("visible"), optional_formal, FakeValidator("sealed", sealed=True)],
        )
        self.assertTrue(harness._visible_passed([
            GateResult("visible", "pass", "visible pass"),
            GateResult("formal", "inconclusive", "unsupported fragment"),
        ]))
        self.assertFalse(harness._visible_passed([
            GateResult("visible", "pass", "visible pass"),
            GateResult("formal", "fail", "counterexample"),
        ]))

    def test_required_formal_inconclusive_never_counts_as_visible_pass(self):
        value = config()
        value["experiment"]["required_visible_gates"] = ["visible", "formal"]
        harness = BoundedSynthesisHarness(
            value, load_task(TASK), Path("/tmp/not-run"), "independent",
            client=FakeClient([]),
            validators=[FakeValidator("visible"), FakeValidator("formal"), FakeValidator("sealed", sealed=True)],
        )
        self.assertFalse(harness._visible_passed([
            GateResult("visible", "pass", "visible pass"),
            GateResult("formal", "inconclusive", "tool timeout"),
        ]))

    def test_public_contract_does_not_include_reference_program(self):
        task = load_task(TASK)
        contract = task.public_contract()
        reference = (TASK / "reference.st").read_text(encoding="utf-8")
        self.assertNotEqual(contract, reference)
        self.assertNotIn(
            "Vote := (S1 AND S2) OR (S1 AND S3) OR (S2 AND S3);",
            contract,
        )
        self.assertIn("FIXED INTERFACE", contract)

    def test_hash_chained_ledger_detects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.jsonl"
            ledger = EvidenceLedger(path)
            ledger.append("one", {"value": 1})
            ledger.append("two", {"value": 2})
            self.assertEqual(len(EvidenceLedger.verify(path)), 2)
            lines = path.read_text(encoding="utf-8").splitlines()
            event = json.loads(lines[0])
            event["payload"]["value"] = 9
            lines[0] = json.dumps(event)
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                EvidenceLedger.verify(path)

    def test_literal_api_key_is_rejected(self):
        value = config()["provider"]
        value["api_key"] = "must-not-be-accepted"
        with self.assertRaises(ValueError):
            ProviderSettings.from_dict(value)

    def test_provider_thinking_mode_is_explicit_and_validated(self):
        value = config()["provider"]
        value["thinking_mode"] = "disabled"
        self.assertEqual(ProviderSettings.from_dict(value).thinking_mode, "disabled")
        value["thinking_mode"] = "sometimes"
        with self.assertRaises(ValueError):
            ProviderSettings.from_dict(value)

    def test_matiec_feedback_keeps_earliest_diagnostic(self):
        stderr = "first actionable error\n" + ("later cascade\n" * 300)
        excerpt = diagnostic_excerpt(stderr, "", 1, limit=80)
        self.assertTrue(excerpt.startswith("first actionable error"))
        self.assertLessEqual(len(excerpt), 80)

    def test_matiec_feedback_identifies_unsupported_line_comments(self):
        excerpt = diagnostic_excerpt("line 2: invalid statement", "", 1, source="// note\nX := TRUE;")
        self.assertIn("candidate contains // line comments", excerpt)
        self.assertIn("line 2: invalid statement", excerpt)

    def test_matiec_feedback_identifies_non_iec_real_cast(self):
        excerpt = diagnostic_excerpt(
            "line 4: invalid expression", "", 1,
            source="Scaled := REAL(Raw) / 10.0;",
        )
        self.assertIn("use INT_TO_REAL(x)", excerpt)

    def test_evidence_signature_ignores_attempt_specific_candidate_path(self):
        first = Evidence(
            "compiler", "compile_error",
            "/tmp/run/attempt_01/candidate.st:4: invalid expression",
            oracle_status="confirmed_candidate_defect",
        )
        second = Evidence(
            "compiler", "compile_error",
            "/tmp/run/attempt_02/candidate.st:4: invalid expression",
            oracle_status="confirmed_candidate_defect",
        )
        self.assertEqual(first.signature, second.signature)

    def test_plcverif_source_rejection_is_a_candidate_defect(self):
        self.assertTrue(is_candidate_source_defect(
            "The called unit 'R_TRIG_X' is not a valid function or function block."
        ))
        self.assertTrue(is_candidate_source_defect(
            "Unable to generate the CFA due to errors in parsing the source file."
        ))
        self.assertFalse(is_candidate_source_defect("TimeoutExpired: backend exceeded 120 seconds"))

    def test_verifier_timeout_is_a_bounded_candidate_failure_for_baselines(self):
        timeout = GateResult(
            "plcverif", "inconclusive", "validator infrastructure error: TimeoutExpired after 900 seconds"
        )
        missing = GateResult(
            "plcverif", "inconclusive", "PLCverif infrastructure is incomplete"
        )
        self.assertTrue(is_resource_bounded_inconclusive(timeout))
        self.assertFalse(is_resource_bounded_inconclusive(missing))

    def test_runtime_case_role_split_is_prespecified(self):
        self.assertEqual(case_role({"id": "FT01", "name": "add"}), "feedback")
        self.assertEqual(case_role({"id": "OT01", "name": "A_feedback_1"}), "feedback")
        self.assertEqual(case_role({"id": "HT01", "name": "hidden"}), "sealed")
        self.assertEqual(case_role({"id": "OT05", "name": "cross_reset_priority"}), "sealed")

    def test_pattern_retrieval_uses_public_task_text(self):
        task = load_task(ROOT / "datasets_50/tasks/C06_M02_bounded_up_down_counter")
        cards = load_pattern_cards(ROOT / "our_method/knowledge/iec_st_patterns.json")
        selected = retrieve_pattern_cards(task, cards, max_cards=4)
        selected_ids = {item["id"] for item in selected}
        self.assertIn("scan_semantics", selected_ids)
        self.assertIn("edge_and_pulse_memory", selected_ids)
        self.assertIn("bounded_counter", selected_ids)
        state = build_task_state(task, [], None, "SYNTHESIZE", cards, max_cards=4)
        self.assertEqual(state["anchor_attempt"], None)
        self.assertEqual(len(state["requirement_state"]), 5)

    def test_edge_pattern_distinguishes_rising_and_falling_polarity(self):
        cards = load_pattern_cards(ROOT / "our_method/knowledge/iec_st_patterns.json")
        edge = next(card for card in cards if card["id"] == "edge_and_pulse_memory")
        guidance = " ".join(edge["guidance"])
        self.assertIn("rising_edge := current_input AND NOT previous_input", guidance)
        self.assertIn("falling_edge := NOT current_input AND previous_input", guidance)

    def test_timer_pattern_requires_finite_saturating_scan_counters(self):
        cards = load_pattern_cards(ROOT / "our_method/knowledge/iec_st_patterns.json")
        timer = next(card for card in cards if card["id"] == "timers_and_timeouts")
        guidance = " ".join(timer["guidance"])
        self.assertIn("Saturate every retained scan counter", guidance)
        self.assertIn("formal verification", guidance)


class RealAdapterTests(unittest.TestCase):
    @unittest.skipUnless(ENGINE_ROOT.is_dir(), "local deterministic scan engine not available")
    def test_reference_passes_public_interface_and_feedback_adapter(self):
        task = load_task(TASK)
        with tempfile.TemporaryDirectory() as directory:
            artifact_dir = Path(directory)
            candidate = artifact_dir / "candidate.st"
            candidate.write_text((TASK / "reference.st").read_text(encoding="utf-8"), encoding="utf-8")
            interface = InterfaceValidator()
            scan = DatasetScanValidator("feedback_tests", "feedback", ENGINE_ROOT)
            self.assertEqual(interface.run(task, candidate, artifact_dir).status, "pass")
            self.assertEqual(scan.run(task, candidate, artifact_dir).status, "pass")


class ExternalBaselineWorkflowTests(unittest.TestCase):
    def _config(self, root: Path) -> Path:
        value = config(max_candidates=10)
        value["experiment"]["required_visible_gates"] = ["compiler", "plcverif"]
        value["experiment"]["sealed_gate"] = "openplc"
        value["validators"] = []
        path = root / "config.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def _run(self, baseline: str, replies: list[str]):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        corpus = root / "iec.md"
        corpus.write_text("# IEC ST\nFUNCTION_BLOCK programs execute once per scan.\n", encoding="utf-8")
        client = FakeClient(replies)
        harness = ExternalBaselineHarness(
            self._config(root),
            TASK,
            root / "run",
            baseline,
            corpus,
            client=client,
            validators=[
                FakeValidator("compiler"),
                FakeValidator("plcverif"),
                FakeValidator("openplc", sealed=True),
            ],
        )
        result = harness.run()
        return temporary, client, result

    def test_llm4plc_plan_then_toolchain_repair(self):
        temporary, client, result = self._run(
            "llm4plc", ["finite-state plan", tagged("BAD"), tagged("GOOD")]
        )
        self.addCleanup(temporary.cleanup)
        self.assertEqual(result["status"], "verified_success")
        self.assertEqual(result["candidates_used"], 2)
        self.assertEqual(result["model_calls_used"], 3)
        self.assertIn("TOOLCHAIN FEEDBACK", client.calls[-1][-1]["content"])

    def test_agents4plc_includes_debugging_agent_call(self):
        temporary, client, result = self._run(
            "agents4plc", ["ranked plan", tagged("BAD"), "fix the faulty branch", tagged("GOOD")]
        )
        self.addCleanup(temporary.cleanup)
        self.assertEqual(result["status"], "verified_success")
        self.assertEqual(result["candidates_used"], 2)
        self.assertEqual(result["model_calls_used"], 4)
        self.assertIn("DEBUGGING ADVICE", client.calls[-1][-1]["content"])

    def test_chatdev_uses_role_review_without_tool_diagnostics(self):
        temporary, client, result = self._run(
            "chatdev", ["product analysis", "CTO design", tagged("BAD"), "review", tagged("GOOD")]
        )
        self.addCleanup(temporary.cleanup)
        self.assertEqual(result["status"], "verified_success")
        self.assertEqual(result["candidates_used"], 2)
        self.assertEqual(result["model_calls_used"], 5)
        review_prompt = client.calls[-2][-1]["content"]
        self.assertNotIn("TOOLCHAIN FEEDBACK", review_prompt)


class FormalReportParserTests(unittest.TestCase):
    def _parse(self, body: str):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "P1.report.html"
            report.write_text(body, encoding="utf-8")
            return cbmc_verdict(Path(directory))

    def test_unwind_failure_is_bounded_pass_when_business_assertion_succeeds(self):
        verdict, scope, _ = self._parse(
            "[VerificationLoop.assertion.1] assertion x &lt; y: SUCCESS<br/>"
            "[VerificationLoop.unwind.1] unwinding assertion: FAILURE<br/>"
            "VERIFICATION FAILED"
        )
        self.assertEqual(verdict, "true")
        self.assertEqual(scope, "bounded_no_counterexample_unwind_limit_reached")

    def test_business_assertion_failure_is_not_hidden_by_unwind(self):
        verdict, scope, _ = self._parse(
            "[VerificationLoop.assertion.1] assertion x: FAILURE<br/>"
            "[VerificationLoop.unwind.1] unwinding assertion: FAILURE<br/>"
            "VERIFICATION FAILED"
        )
        self.assertEqual(verdict, "false")
        self.assertEqual(scope, "bounded_counterexample")

    def test_counterexample_compaction_keeps_verdict_and_final_state(self):
        text = (
            "-- invariant (instance.X --> instance.Y) is false\n"
            "  -> State: 1.1 <-\n    instance_X = TRUE\n"
            + ("noise\n" * 1000)
            + "  -> State: 1.2 <-\n    instance_Y = FALSE\n"
        )
        excerpt = compact_counterexample(text, limit=500)
        self.assertIn("is false", excerpt)
        self.assertIn("instance_Y = FALSE", excerpt)
        self.assertLessEqual(len(excerpt), 500)


if __name__ == "__main__":
    unittest.main()

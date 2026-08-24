from __future__ import annotations

import io
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from plc_loop.ladder import LadderError, compile_ladder_document
from plc_loop.delta_dvp import (
    NativeLdError,
    build_ispsoft_package,
    parse_function_block,
    render_native_ld_function_block_source,
    render_program_source,
)
from plc_loop.models import GateResult, ModelReply
from plc_loop.orchestrator import BoundedSynthesisHarness
from plc_loop.response import parse_candidate


INTERFACE = """FUNCTION_BLOCK MotorControl
VAR_INPUT
    StartButton : BOOL;
    StopButton : BOOL;
    Permit : BOOL;
END_VAR
VAR_OUTPUT
    MotorRun : BOOL;
    Ready : BOOL;
END_VAR
END_FUNCTION_BLOCK
"""
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def ladder_document() -> dict:
    return {
        "schema_version": "1.0",
        "function_block": "MotorControl",
        "locals": [
            {"name": "RunLatch", "type": "BOOL", "initial": False},
            {"name": "DelayScans", "type": "INT", "initial": 0},
        ],
        "rungs": [
            {
                "id": "RUNG_01",
                "comment": "满足许可时锁存启动命令",
                "condition": {
                    "op": "and",
                    "args": [
                        {"op": "var", "name": "StartButton"},
                        {"op": "var", "name": "Permit"},
                    ],
                },
                "instructions": [
                    {"type": "coil", "target": "RunLatch", "mode": "set"},
                    {"type": "increment_saturating", "target": "DelayScans", "limit": 3},
                ],
            },
            {
                "id": "RUNG_02",
                "comment": "停止命令具有更高优先级",
                "condition": {"op": "var", "name": "StopButton"},
                "instructions": [
                    {"type": "coil", "target": "RunLatch", "mode": "reset"}
                ],
            },
            {
                "id": "RUNG_03",
                "comment": "输出运行状态",
                "condition": {
                    "op": "and",
                    "args": [
                        {"op": "var", "name": "RunLatch"},
                        {"op": "not", "arg": {"op": "var", "name": "StopButton"}},
                    ],
                },
                "instructions": [
                    {"type": "coil", "target": "MotorRun", "mode": "normal"}
                ],
            },
            {
                "id": "RUNG_04",
                "comment": "比较扫描计数器",
                "condition": {
                    "op": "compare",
                    "operator": "GE",
                    "left": {"op": "var", "name": "DelayScans"},
                    "right": {"op": "const", "type": "INT", "value": 3},
                },
                "instructions": [
                    {"type": "coil", "target": "Ready", "mode": "normal"}
                ],
            },
        ],
    }


def tagged_ladder(document: dict) -> str:
    return (
        "<repair_hypothesis>使用停止优先的有序梯级</repair_hypothesis>\n"
        "<target_requirements>R1</target_requirements>\n"
        "<ladder_program>\n"
        + json.dumps(document, ensure_ascii=False)
        + "\n</ladder_program>"
    )


def native_boolean_document() -> dict:
    """Subset calibrated against ISPSoft 3.24 official native-LD exports."""
    return {
        "schema_version": "1.0",
        "function_block": "MotorControl",
        "locals": [{"name": "RunLatch", "type": "BOOL", "initial": False}],
        "rungs": [
            {
                "id": "RUNG_01",
                "comment": "two-wide branch OR one-wide branch",
                "condition": {
                    "op": "or",
                    "args": [
                        {
                            "op": "and",
                            "args": [
                                {"op": "var", "name": "StartButton"},
                                {"op": "var", "name": "Permit"},
                            ],
                        },
                        {"op": "not", "arg": {"op": "var", "name": "StopButton"}},
                    ],
                },
                "instructions": [{"type": "coil", "target": "RunLatch", "mode": "set"}],
            },
            {
                "id": "RUNG_02",
                "comment": "reset retained state",
                "condition": {"op": "var", "name": "StopButton"},
                "instructions": [{"type": "coil", "target": "RunLatch", "mode": "reset"}],
            },
            {
                "id": "RUNG_03",
                "comment": "drive public output",
                "condition": {"op": "var", "name": "RunLatch"},
                "instructions": [{"type": "coil", "target": "MotorRun", "mode": "normal"}],
            },
        ],
    }


class LadderCompilerTests(unittest.TestCase):
    def test_compiles_to_st_and_renders_valid_svg(self):
        compiled = compile_ladder_document(ladder_document(), INTERFACE, "MotorControl")
        self.assertIn("FUNCTION_BLOCK MotorControl", compiled.st_program)
        self.assertIn("RunLatch : BOOL := FALSE;", compiled.st_program)
        self.assertIn("RunLatch := TRUE;", compiled.st_program)
        self.assertIn("RunLatch := FALSE;", compiled.st_program)
        self.assertIn("DelayScans < 3", compiled.st_program)
        self.assertIn("MotorRun := (RunLatch) AND (NOT (StopButton));", compiled.st_program)
        ET.fromstring(compiled.svg)
        self.assertIn("停止命令具有更高优先级", compiled.svg)

    def test_rejects_unknown_symbol(self):
        document = ladder_document()
        document["rungs"][0]["condition"] = {"op": "var", "name": "MissingInput"}
        with self.assertRaisesRegex(LadderError, "unknown symbol MissingInput"):
            compile_ladder_document(document, INTERFACE, "MotorControl")

    def test_rejects_direct_device_and_reserved_harness_names(self):
        for name in ("M1000", "EGBS_ACK"):
            document = ladder_document()
            document["locals"].append({"name": name, "type": "BOOL", "initial": False})
            with self.subTest(name=name), self.assertRaises(LadderError):
                compile_ladder_document(document, INTERFACE, "MotorControl")

    def test_rejects_normal_coil_mixed_with_retained_writer(self):
        document = ladder_document()
        document["rungs"].append({
            "id": "RUNG_05",
            "comment": "非法重复写入",
            "condition": {"op": "var", "name": "StartButton"},
            "instructions": [{"type": "coil", "target": "MotorRun", "mode": "set"}],
        })
        with self.assertRaisesRegex(LadderError, "mixes a normal coil"):
            compile_ladder_document(document, INTERFACE, "MotorControl")

    def test_rejects_writing_a_fixed_input(self):
        document = ladder_document()
        document["rungs"][0]["instructions"] = [
            {"type": "coil", "target": "StartButton", "mode": "normal"}
        ]
        with self.assertRaisesRegex(LadderError, "cannot write fixed input StartButton"):
            compile_ladder_document(document, INTERFACE, "MotorControl")

    def test_response_parser_returns_canonical_st_and_ld_artifacts(self):
        parsed = parse_candidate(
            {"content": tagged_ladder(ladder_document())},
            {"R1"},
            output_language="ld",
            interface_text=INTERFACE,
            task_id="MotorControl",
        )
        self.assertTrue(parsed.format_valid, parsed.format_errors)
        self.assertEqual(parsed.source_language, "ld")
        self.assertIsNotNone(parsed.ladder_document)
        self.assertTrue(parsed.source_text.endswith("\n"))
        self.assertIn("END_FUNCTION_BLOCK", parsed.program)
        self.assertIn("<svg", parsed.ladder_svg or "")

    def test_response_parser_fails_closed_on_malformed_ir(self):
        parsed = parse_candidate(
            {"content": tagged_ladder({"schema_version": "1.0"})},
            {"R1"},
            output_language="ld",
            interface_text=INTERFACE,
            task_id="MotorControl",
        )
        self.assertFalse(parsed.format_valid)
        self.assertEqual(parsed.program, "")
        self.assertTrue(any("unsupported keys" in item or "function_block" in item for item in parsed.format_errors))

    def test_response_parser_rejects_duplicate_json_keys(self):
        response = (
            "<repair_hypothesis>x</repair_hypothesis>\n"
            "<target_requirements>R1</target_requirements>\n"
            '<ladder_program>{"schema_version":"1.0","schema_version":"2.0"}</ladder_program>'
        )
        parsed = parse_candidate(
            {"content": response}, {"R1"}, output_language="ld",
            interface_text=INTERFACE, task_id="MotorControl",
        )
        self.assertFalse(parsed.format_valid)
        self.assertIn("duplicate JSON key", parsed.format_errors[-1])

    def test_lowered_st_is_accepted_by_delta_source_unit_adapter(self):
        compiled = compile_ladder_document(ladder_document(), INTERFACE, "MotorControl")
        block = parse_function_block(compiled.st_program)
        self.assertEqual(block.name, "MotorControl")
        package = build_ispsoft_package(
            render_program_source("MAIN", block.declarations, block.body),
            "unit-test-password",
        )
        self.assertGreater(len(package), 152)

    def test_balanced100_composite_fixture_compiles_for_delta_adapter(self):
        task = PROJECT_ROOT.parent / "datasets_100" / "tasks" / "C01_B02_composite"
        document = json.loads(
            (PROJECT_ROOT / "tests/fixtures/ladder/C01_B02_composite.ld.json").read_text()
        )
        compiled = compile_ladder_document(
            document,
            (task / "interface.st").read_text(),
            task.name,
        )
        block = parse_function_block(compiled.st_program)
        self.assertEqual(block.name, task.name)
        self.assertIn("CrossBlocked := (SubsystemBEnable) AND (NOT (CrossReady));", block.body)

    def test_exports_calibrated_ispsoft_native_ld_function_block(self):
        compiled = render_native_ld_function_block_source(
            native_boolean_document(), INTERFACE, "MotorControl"
        )
        source = compiled.source.decode()
        self.assertEqual(compiled.network_count, 3)
        self.assertIn("ContentName=MotorControl [FB,LD]", source)
        self.assertIn("P_type=1\r\nP_Rtn_Type=\r\nP_Lang=1", source)
        self.assertNotIn("<IL_ST_CODE>", source)
        self.assertIn("RunLatch : BOOL := FALSE [@@] {VAR}", source)
        # Official LD_TOPOLOGY.MPU used the same two-by-two topology encoding:
        # three contacts, one empty cell, then the parallel-group dimensions.
        expected_root = (
            "TYPE=1\r\nDEV_NAME=StartButton\r\n[END_LD_NODE]\r\n"
            "[LD_NODE]\r\nTYPE=1\r\nDEV_NAME=Permit\r\n[END_LD_NODE]\r\n"
            "[LD_NODE]\r\nTYPE=2\r\nDEV_NAME=StopButton\r\n[END_LD_NODE]\r\n"
            "[LD_NODE]\r\nTYPE=5\r\nDEV_NAME=\r\n[END_LD_NODE]\r\n"
            "[LD_NODE]\r\nTYPE=6\r\nLNK_C=2\r\nLNK_L=2"
        )
        self.assertIn(expected_root, source)
        self.assertIn("TYPE=15\r\nDEV_NAME=RunLatch", source)
        self.assertIn("TYPE=16\r\nDEV_NAME=RunLatch", source)
        self.assertIn("TYPE=13\r\nDEV_NAME=MotorRun", source)

    def test_native_ld_splits_multiple_coils_into_independent_networks(self):
        document = native_boolean_document()
        document["rungs"][2]["instructions"].append(
            {"type": "coil", "target": "Ready", "mode": "normal"}
        )
        compiled = render_native_ld_function_block_source(document, INTERFACE)
        source = compiled.source.decode()
        self.assertEqual(compiled.network_count, 4)
        self.assertIn("NET_LABEL=RUNG_03_1", source)
        self.assertIn("NET_LABEL=RUNG_03_2", source)

    def test_native_ld_package_round_trip_preserves_ld_source(self):
        source = render_native_ld_function_block_source(
            native_boolean_document(), INTERFACE
        ).source
        package = build_ispsoft_package(source, "unit-test-password")
        with zipfile.ZipFile(io.BytesIO(package[152:])) as archive:
            self.assertEqual(
                archive.read("Unzipped.src", pwd=b"unit-test-password"), source
            )

    def test_native_ld_fails_closed_for_uncalibrated_instructions(self):
        document = native_boolean_document()
        document["rungs"][0]["instructions"] = [
            {
                "type": "increment_saturating",
                "target": "DelayScans",
                "limit": 3,
            }
        ]
        document["locals"].append({"name": "DelayScans", "type": "INT", "initial": 0})
        with self.assertRaisesRegex(NativeLdError, "only normal, set, and reset coils"):
            render_native_ld_function_block_source(document, INTERFACE)

    def test_native_ld_fails_closed_for_uncalibrated_comparison(self):
        document = native_boolean_document()
        document["locals"].append({"name": "DelayScans", "type": "INT", "initial": 0})
        document["rungs"][0]["condition"] = {
            "op": "compare",
            "operator": "GE",
            "left": {"op": "var", "name": "DelayScans"},
            "right": {"op": "const", "type": "INT", "value": 3},
        }
        with self.assertRaisesRegex(NativeLdError, "no calibrated ISPSoft"):
            render_native_ld_function_block_source(document, INTERFACE)


class FakeClient:
    def __init__(self, content: str):
        self.content = content

    def generate(self, messages):
        message = {"role": "assistant", "content": self.content}
        return ModelReply(
            message=message,
            raw_response={"model": "fake-model", "choices": [{"message": message}]},
            requested_model="fake-model",
            resolved_model="fake-model",
            provider="fake",
            usage={"prompt_tokens": 1, "completion_tokens": 1},
            finish_reason="stop",
            latency_ms=1,
        )


class PassingValidator:
    blocking = True
    inconclusive_is_blocking = True

    def __init__(self, name: str, sealed: bool = False):
        self.name = name
        self.sealed = sealed

    def preflight(self, task):
        return None

    def run(self, task, candidate_path, artifact_dir):
        source = candidate_path.read_text(encoding="utf-8")
        status = "pass" if "FUNCTION_BLOCK MotorControl" in source else "fail"
        return GateResult(self.name, status, "checked canonical ST")


class Task:
    task_id = "MotorControl"
    requirement_ids = {"R1"}
    critical_requirement_ids = {"R1"}
    interface_text = INTERFACE

    def public_contract(self):
        return "PUBLIC REQUIREMENTS\nR1: stop has priority\n\nFIXED INTERFACE\n" + INTERFACE


class LadderHarnessTests(unittest.TestCase):
    def test_harness_persists_ld_json_svg_and_verifies_lowered_st(self):
        config = {
            "provider": {
                "name": "fake",
                "base_url": "https://example.invalid/v1",
                "api_key_env": "NOT_USED",
                "requested_model": "fake-model",
                "allowed_resolved_models": ["fake-model"],
                "history_mode": "stateless",
            },
            "experiment": {
                "output_language": "ld",
                "max_candidates": 1,
                "required_visible_gates": ["visible"],
                "sealed_gate": "sealed",
                "stop_on_visible_pass": True,
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            result = BoundedSynthesisHarness(
                config,
                Task(),
                output,
                "evidence",
                client=FakeClient(tagged_ladder(ladder_document())),
                validators=[PassingValidator("visible"), PassingValidator("sealed", sealed=True)],
            ).run()
            self.assertTrue(result["success"])
            self.assertEqual(result["output_language"], "ld")
            attempt = output / "attempts" / "attempt_01"
            self.assertTrue((attempt / "candidate.ld.json").is_file())
            self.assertTrue((attempt / "candidate.ld.svg").is_file())
            self.assertTrue((attempt / "candidate.st").is_file())
            self.assertEqual(result["attempts"][0]["candidate"]["source_language"], "ld")


if __name__ == "__main__":
    unittest.main()

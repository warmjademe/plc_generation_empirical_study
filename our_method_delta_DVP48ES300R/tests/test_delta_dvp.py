from __future__ import annotations

import io
import datetime as dt
import json
import subprocess
import struct
import sys
import tempfile
import threading
import time
import unittest
import zipfile
from pathlib import Path

import plc_loop

# The copied external-baseline tests intentionally import the sibling
# ``our_method`` package.  When unittest discovers those modules first, Python
# caches that package before this DVP-specific test module is imported.  Extend
# the cached package path with this variant's implementation so full-suite test
# order cannot hide the delta_dvp subpackage.
LOCAL_PLC_LOOP = Path(__file__).resolve().parents[1] / "src" / "plc_loop"
if str(LOCAL_PLC_LOOP) not in plc_loop.__path__:
    plc_loop.__path__.insert(0, str(LOCAL_PLC_LOOP))
SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from plc_loop.delta_dvp import (
    SourceUnitError,
    build_dvp_harness,
    build_ispsoft_package,
    parse_function_block,
    render_function_block_source,
    render_program_source,
    select_openplc_cases,
    validate_saturating_retained_integers,
)
from dvp48es300r_validator import prepare_job, result_artifact_name
from audit_dvp48es300r_batch import (
    find_job_for_gate,
    job_timestamp,
    verify_openplc_sealed_trace,
)
from audit_reference_differential import (
    build_pair_source,
    build_stress_suite,
    normalize_reference_evidence,
)
from run_dvp_negative_control import calibration_verdict
from plc_loop.ladder import compile_ladder_document


SIMPLE_ST = """FUNCTION_BLOCK Demo
VAR_INPUT
    Enable : BOOL;
    Level : INT;
END_VAR
VAR_OUTPUT
    Active : BOOL;
    Scaled : REAL;
END_VAR
VAR
    Held : BOOL := FALSE;
END_VAR
IF Enable THEN
    Held := TRUE;
END_IF;
Active := Held;
Scaled := INT_TO_REAL(Level) * 0.5;
END_FUNCTION_BLOCK
"""


def sample_metadata() -> dict:
    return {
        "id": "Demo",
        "scan": {"period_ms": 100},
        "interface": {
            "inputs": [
                {"name": "Enable", "type": "BOOL"},
                {"name": "Level", "type": "INT"},
            ],
            "outputs": [
                {"name": "Active", "type": "BOOL"},
                {"name": "Scaled", "type": "REAL"},
            ],
        },
    }


def sample_suite() -> dict:
    return {
        "suite": "openplc",
        "independent_requirement_oracle": True,
        "real_absolute_tolerance": 0.01,
        "cases": [
            {
                "id": "FT1",
                "name": "feedback_basic",
                "requirement_ids": ["R1"],
                "steps": [
                    {
                        "inputs": {"Enable": True, "Level": 2},
                        "expect": {"Active": True, "Scaled": 1.0},
                        "repeat": 1,
                    }
                ],
            },
            {
                "id": "HT1",
                "name": "sealed_basic",
                "requirement_ids": ["R2"],
                "steps": [
                    {
                        "inputs": {"Enable": False, "Level": -2},
                        "expect": {"Active": False, "Scaled": -1.0},
                        "repeat": 1,
                    }
                ],
            },
        ],
    }


class SourceUnitTests(unittest.TestCase):
    def test_candidate_is_split_into_ispsoft_declarations_and_body(self):
        block = parse_function_block(SIMPLE_ST)
        self.assertEqual(block.name, "Demo")
        self.assertEqual(
            [(item.name, item.type_text, item.scope, item.initializer) for item in block.declarations],
            [
                ("Enable", "BOOL", "VAR_INPUT", None),
                ("Level", "INT", "VAR_INPUT", None),
                ("Active", "BOOL", "VAR_OUTPUT", None),
                ("Scaled", "REAL", "VAR_OUTPUT", None),
                ("Held", "BOOL", "VAR", "FALSE"),
            ],
        )
        rendered = render_function_block_source(block).decode()
        self.assertIn("ContentName=Demo [FB,ST]", rendered)
        self.assertIn("Enable : BOOL :=  [@@] {VAR_INPUT}", rendered)
        self.assertIn("Held : BOOL := FALSE [@@] {VAR}", rendered)
        self.assertNotIn("FUNCTION_BLOCK", rendered)
        self.assertIn("<IL_ST_CODE>\r\nIF Enable THEN", rendered)

    def test_package_is_a_valid_encrypted_zip_inside_exact_delta_header(self):
        source = render_function_block_source(parse_function_block(SIMPLE_ST))
        package = build_ispsoft_package(source, "unit-test-password")
        self.assertEqual(len(package), 152 + struct.unpack_from("<I", package, 148)[0])
        self.assertEqual(struct.unpack_from("<I", package, 12)[0], 0x3FC)
        self.assertEqual(struct.unpack_from("<I", package, 16)[0], 0xED8)
        archive_bytes = package[152:]
        compressed_size = struct.unpack_from("<I", archive_bytes, 18)[0]
        filename_size = struct.unpack_from("<H", archive_bytes, 26)[0]
        extra_size = struct.unpack_from("<H", archive_bytes, 28)[0]
        descriptor_offset = 30 + filename_size + extra_size + compressed_size
        self.assertEqual(
            struct.unpack_from("<I", archive_bytes, descriptor_offset)[0],
            0x08074B50,
        )
        with zipfile.ZipFile(io.BytesIO(package[152:])) as archive:
            self.assertEqual(archive.namelist(), ["Unzipped.src"])
            self.assertEqual(
                archive.read("Unzipped.src", pwd=b"unit-test-password"),
                source,
            )

    def test_program_package_uses_delta_program_attributes(self):
        source = render_program_source("MAIN", (), "M0 := M1;")
        package = build_ispsoft_package(source, "unit-test-password")
        archive_bytes = package[152:]
        central_offset = archive_bytes.index(b"PK\x01\x02")
        self.assertEqual(struct.unpack_from("<I", archive_bytes, central_offset + 38)[0], 0x20)

    def test_explicit_transport_timestamps_can_separate_consecutive_units(self):
        source = render_program_source("MAIN", (), "M0 := M1;")
        first = build_ispsoft_package(
            source,
            "unit-test-password",
            timestamp=dt.datetime(2026, 8, 18, 11, 34, 30),
        )[152:]
        second = build_ispsoft_package(
            source,
            "unit-test-password",
            timestamp=dt.datetime(2026, 8, 18, 11, 34, 32),
        )[152:]
        self.assertNotEqual(struct.unpack_from("<H", first, 10)[0], struct.unpack_from("<H", second, 10)[0])

    def test_rejects_multiple_or_incomplete_blocks(self):
        with self.assertRaises(SourceUnitError):
            parse_function_block("FUNCTION_BLOCK A\nEND_FUNCTION_BLOCK\nFUNCTION_BLOCK B\nEND_FUNCTION_BLOCK")

    def test_rejects_direct_delta_devices_and_harness_identifiers(self):
        for body in (
            "Active := M1000;",
            "Y0 := Active;",
            "Active := S1;",
            "Active := %IX0.0;",
            "EGBS_STEP_ACK := Active;",
        ):
            source = (
                "FUNCTION_BLOCK Demo\n"
                "VAR_OUTPUT\n    Active : BOOL;\nEND_VAR\n"
                f"{body}\nEND_FUNCTION_BLOCK\n"
            )
            with self.subTest(body=body), self.assertRaises(SourceUnitError):
                parse_function_block(source)

    def test_device_shaped_fixed_interface_names_remain_abstract_symbols(self):
        source = """FUNCTION_BLOCK SensorVote
VAR_INPUT
    S1 : BOOL;
    D1 : INT;
END_VAR
VAR_OUTPUT
    Vote : BOOL;
END_VAR
Vote := S1 AND (D1 > 0);
END_FUNCTION_BLOCK
"""
        self.assertEqual(parse_function_block(source).name, "SensorVote")

    def test_device_shaped_local_cannot_bypass_candidate_isolation(self):
        source = """FUNCTION_BLOCK HiddenDevice
VAR_OUTPUT
    Active : BOOL;
END_VAR
VAR
    M1000 : BOOL;
END_VAR
Active := M1000;
END_FUNCTION_BLOCK
"""
        with self.assertRaisesRegex(SourceUnitError, "direct Delta device M1000"):
            parse_function_block(source)

    def test_device_like_text_inside_comment_is_not_treated_as_access(self):
        source = SIMPLE_ST.replace(
            "IF Enable THEN",
            "(* M1000 and %IX0.0 are examples, not accesses. *)\nIF Enable THEN",
        )
        self.assertEqual(parse_function_block(source).name, "Demo")

    def test_rejects_ton_with_actionable_dvp_es3_compatibility_feedback(self):
        source = SIMPLE_ST.replace(
            "Held : BOOL := FALSE;",
            "Held : BOOL := FALSE;\n    DelayTimer : TON;",
        )
        with self.assertRaisesRegex(SourceUnitError, "saturating scan counter"):
            parse_function_block(source)

    def test_rejects_time_with_actionable_dvp_es3_compatibility_feedback(self):
        source = SIMPLE_ST.replace(
            "Held : BOOL := FALSE;",
            "Held : BOOL := FALSE;\n    Elapsed : TIME := T#0ms;",
        )
        with self.assertRaisesRegex(SourceUnitError, "IEC TIME"):
            parse_function_block(source)

    def test_target_policy_rejects_unbounded_retained_int_self_increment(self):
        source = SIMPLE_ST.replace(
            "Held : BOOL := FALSE;",
            "Held : BOOL := FALSE;\n    FeedbackTimer : INT := 0;",
        ).replace(
            "IF Enable THEN\n    Held := TRUE;\nEND_IF;",
            "IF Enable THEN\n"
            "    FeedbackTimer := FeedbackTimer + 1;\n"
            "    Held := FeedbackTimer >= 3;\n"
            "ELSE\n"
            "    FeedbackTimer := 0;\n"
            "END_IF;",
        )
        block = parse_function_block(source)
        with self.assertRaisesRegex(SourceUnitError, "FeedbackTimer"):
            validate_saturating_retained_integers(block)

    def test_target_policy_accepts_explicitly_saturated_retained_int(self):
        source = SIMPLE_ST.replace(
            "Held : BOOL := FALSE;",
            "Held : BOOL := FALSE;\n    FeedbackTimer : INT := 0;",
        ).replace(
            "IF Enable THEN\n    Held := TRUE;\nEND_IF;",
            "IF Enable THEN\n"
            "    IF FeedbackTimer < 3 THEN\n"
            "        FeedbackTimer := FeedbackTimer + 1;\n"
            "    END_IF;\n"
            "    Held := FeedbackTimer >= 3;\n"
            "ELSE\n"
            "    FeedbackTimer := 0;\n"
            "END_IF;",
        )
        validate_saturating_retained_integers(parse_function_block(source))

    def test_target_policy_accepts_a_per_scan_channel_accumulator(self):
        source = SIMPLE_ST.replace(
            "Held : BOOL := FALSE;",
            "Held : BOOL := FALSE;\n    ChannelCount : INT := 0;",
        ).replace(
            "IF Enable THEN",
            "IF Enable THEN\n"
            "    ChannelCount := 0;\n"
            "    IF Level > 0 THEN ChannelCount := ChannelCount + 1; END_IF;\n"
            "    IF Level > 1 THEN ChannelCount := ChannelCount + 1; END_IF;\n"
            "END_IF;\n"
            "IF Enable THEN",
        )
        validate_saturating_retained_integers(parse_function_block(source))

    def test_target_policy_does_not_treat_a_conditional_reset_as_scan_local(self):
        source = SIMPLE_ST.replace(
            "Held : BOOL := FALSE;",
            "Held : BOOL := FALSE;\n    FeedbackTimer : INT := 0;",
        ).replace(
            "IF Enable THEN\n    Held := TRUE;\nEND_IF;",
            "IF NOT Enable THEN\n"
            "    FeedbackTimer := 0;\n"
            "ELSE\n"
            "    FeedbackTimer := FeedbackTimer + 1;\n"
            "END_IF;\n"
            "Held := FeedbackTimer >= 3;",
        )
        with self.assertRaisesRegex(SourceUnitError, "FeedbackTimer"):
            validate_saturating_retained_integers(parse_function_block(source))


class HarnessTests(unittest.TestCase):
    def test_feedback_role_builds_coil_only_request_ack_mapping(self):
        block = parse_function_block(SIMPLE_ST)
        selected = select_openplc_cases(sample_suite(), "feedback")
        identity = "0123456789abcdef" * 4
        harness = build_dvp_harness(
            block,
            sample_metadata(),
            selected,
            image_identity_sha256=identity,
        )
        self.assertEqual(len(harness.suite["cases"]), 1)
        self.assertEqual(harness.suite["cases"][0]["id"], "FT1")
        self.assertEqual(harness.mapping["inputs"]["Enable"]["device"], "M1000")
        level = harness.mapping["inputs"]["Level"]
        self.assertEqual(level["kind"], "selector")
        self.assertEqual(level["values"]["2"]["device"], "M1001")
        self.assertEqual(harness.mapping["outputs"]["Active"]["kind"], "bool")
        self.assertEqual(harness.mapping["outputs"]["Scaled"]["kind"], "expected_match")
        self.assertIn("EGBS_DUT(", harness.body)
        self.assertIn("M1001 THEN", harness.body)
        self.assertIn("EGBS_DUT.Scaled >= 0.99", harness.body)
        self.assertEqual(
            harness.mapping["step_request"]["coil_address"],
            int(harness.mapping["step_request"]["device"][1:]),
        )
        self.assertEqual(harness.mapping["commgr_coil_base"], 0)
        self.assertEqual(harness.mapping["image_identity"]["sha256"], identity)
        self.assertEqual(len(harness.mapping["image_identity"]["bits"]), 64)
        self.assertEqual(
            harness.mapping["writable_last_m"],
            harness.mapping["step_ack"]["coil_address"],
        )
        self.assertEqual(
            harness.mapping["last_m"],
            harness.mapping["writable_last_m"] + 64,
        )
        self.assertIn("M1007 := TRUE;", harness.body)
        program = render_program_source("MAIN", harness.declarations, harness.body).decode()
        self.assertIn("EGBS_DUT : Demo :=  [@@] {VAR}", program)

    def test_sealed_role_does_not_include_feedback_case(self):
        selected = select_openplc_cases(sample_suite(), "sealed")
        self.assertEqual([case["id"] for case in selected["cases"]], ["HT1"])

    def test_inline_main_materialises_candidate_state_without_fb_instance(self):
        block = parse_function_block(SIMPLE_ST)
        harness = build_dvp_harness(
            block,
            sample_metadata(),
            select_openplc_cases(sample_suite(), "feedback"),
            image_identity_sha256="0123456789abcdef" * 4,
            inline_candidate=True,
        )
        declarations = {item.name: item for item in harness.declarations}
        self.assertNotIn("EGBS_DUT", declarations)
        self.assertEqual(declarations["Held"].scope, "VAR")
        self.assertEqual(declarations["Held"].initializer, "FALSE")
        self.assertIn("Enable := M1000;", harness.body)
        self.assertIn("IF Enable THEN", harness.body)
        self.assertIn("M1002 := Active;", harness.body)
        self.assertNotIn("EGBS_DUT(", harness.body)
        self.assertEqual(harness.suite["execution_adapter"], "candidate-body-inlined-into-main")


class ResultProtocolTests(unittest.TestCase):
    def test_auditor_replays_persisted_openplc_sealed_trace(self) -> None:
        suite = {
            "cases": [{
                "id": "HT1",
                "name": "hidden",
                "steps": [{
                    "inputs": {"Enable": True},
                    "expect": {"Active": True},
                    "repeat": 2,
                    "check": "last_only",
                }],
            }],
        }
        trace = [
            {
                "case": "hidden", "step": 1, "repeat": 1,
                "inputs": {"Enable": True}, "expected": {"Active": True},
                "observed": {"Active": False}, "matches": {"Active": False},
                "checked": False,
            },
            {
                "case": "hidden", "step": 1, "repeat": 2,
                "inputs": {"Enable": True}, "expected": {"Active": True},
                "observed": {"Active": True}, "matches": {"Active": True},
                "checked": True,
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            evidence = Path(directory) / "openplc_sealed"
            evidence.mkdir()
            (evidence / "openplc_sealed_suite.json").write_text(
                json.dumps(suite), encoding="utf-8"
            )
            (evidence / "openplc_test_trace.json").write_text(
                json.dumps(trace), encoding="utf-8"
            )
            result = verify_openplc_sealed_trace(Path(directory), ["HT1"])
            self.assertEqual(result["trace_rows"], 2)
            self.assertEqual(result["checked_observations"], 1)

    def test_auditor_rejects_a_checked_openplc_sealed_mismatch(self) -> None:
        suite = {"cases": [{
            "id": "HT1", "name": "hidden",
            "steps": [{
                "inputs": {"Enable": True}, "expect": {"Active": True},
                "repeat": 1, "check": "each",
            }],
        }]}
        trace = [{
            "case": "hidden", "step": 1, "repeat": 1,
            "inputs": {"Enable": True}, "expected": {"Active": True},
            "observed": {"Active": False}, "matches": {"Active": False},
            "checked": True,
        }]
        with tempfile.TemporaryDirectory() as directory:
            evidence = Path(directory) / "openplc_sealed"
            evidence.mkdir()
            (evidence / "openplc_sealed_suite.json").write_text(
                json.dumps(suite), encoding="utf-8"
            )
            (evidence / "openplc_test_trace.json").write_text(
                json.dumps(trace), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "contains a mismatch"):
                verify_openplc_sealed_trace(Path(directory), ["HT1"])

    def test_job_records_saturation_pattern_as_nonblocking_advisory(self) -> None:
        source = SIMPLE_ST.replace(
            "Held : BOOL := FALSE;",
            "Held : BOOL := FALSE;\n    FeedbackTimer : INT := 0;",
        ).replace(
            "IF Enable THEN\n    Held := TRUE;\nEND_IF;",
            "IF Enable THEN\n"
            "    FeedbackTimer := FeedbackTimer + 1;\n"
            "    Held := FeedbackTimer >= 3;\n"
            "ELSE\n"
            "    FeedbackTimer := 0;\n"
            "END_IF;",
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = root / "task"
            task.mkdir()
            candidate = root / "candidate.st"
            candidate.write_text(source, encoding="utf-8")
            (task / "metadata.json").write_text(
                json.dumps(sample_metadata()), encoding="utf-8"
            )
            (task / "openplc_tests.json").write_text(
                json.dumps(sample_suite()), encoding="utf-8"
            )
            _job_id, pending, manifest = prepare_job(
                candidate, task, "feedback", root / "spool", "unit-test-password"
            )
            self.assertTrue(pending.is_dir())
            self.assertEqual(manifest["prospective_policy_advisories"], [{
                "kind": "retained_int_without_simple_saturation_pattern",
                "variables": ["FeedbackTimer"],
                "blocking": False,
            }])

    def test_ld_job_uses_native_function_block_and_non_inline_harness(self) -> None:
        interface = """FUNCTION_BLOCK FB_GEN_JOB
VAR_INPUT
    Enable : BOOL;
    Block : BOOL;
END_VAR
VAR_OUTPUT
    Active : BOOL;
    Latched : BOOL;
END_VAR
END_FUNCTION_BLOCK
"""
        document = {
            "schema_version": "1.0",
            "function_block": "FB_GEN_JOB",
            "locals": [],
            "rungs": [
                {
                    "id": "RUNG_01",
                    "comment": "normal output",
                    "condition": {
                        "op": "and",
                        "args": [
                            {"op": "var", "name": "Enable"},
                            {"op": "not", "arg": {"op": "var", "name": "Block"}},
                        ],
                    },
                    "instructions": [{"type": "coil", "target": "Active", "mode": "normal"}],
                },
                {
                    "id": "RUNG_02",
                    "comment": "set output",
                    "condition": {"op": "var", "name": "Enable"},
                    "instructions": [{"type": "coil", "target": "Latched", "mode": "set"}],
                },
                {
                    "id": "RUNG_03",
                    "comment": "reset output",
                    "condition": {"op": "var", "name": "Block"},
                    "instructions": [{"type": "coil", "target": "Latched", "mode": "reset"}],
                },
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = root / "task"
            attempt = root / "attempt"
            task.mkdir()
            attempt.mkdir()
            candidate = attempt / "candidate.st"
            candidate.write_text(
                compile_ladder_document(document, interface, "FB_GEN_JOB").st_program,
                encoding="utf-8",
            )
            (attempt / "candidate.ld.json").write_text(
                json.dumps(document), encoding="utf-8"
            )
            (task / "interface.st").write_text(interface, encoding="utf-8")
            (task / "metadata.json").write_text(json.dumps({
                "id": "FB_GEN_JOB",
                "scan": {"period_ms": 100},
                "interface": {
                    "inputs": [
                        {"name": "Enable", "type": "BOOL"},
                        {"name": "Block", "type": "BOOL"},
                    ],
                    "outputs": [
                        {"name": "Active", "type": "BOOL"},
                        {"name": "Latched", "type": "BOOL"},
                    ],
                },
            }), encoding="utf-8")
            (task / "openplc_tests.json").write_text(json.dumps({
                "suite": "openplc",
                "independent_requirement_oracle": True,
                "cases": [{
                    "id": "FT1",
                    "name": "feedback_basic",
                    "requirement_ids": ["R1"],
                    "steps": [{
                        "inputs": {"Enable": True, "Block": False},
                        "expect": {"Active": True, "Latched": True},
                        "repeat": 1,
                    }],
                }],
            }), encoding="utf-8")
            _job_id, pending, manifest = prepare_job(
                candidate, task, "feedback", root / "spool", "unit-test-password"
            )
            self.assertEqual(manifest["candidate_language"], "ld")
            self.assertEqual(manifest["execution_adapter"], "native-ld-function-block")
            self.assertTrue((pending / "candidate.ld.json").is_file())
            self.assertTrue((pending / "candidate.ispsoft.ld.src").is_file())
            with zipfile.ZipFile(io.BytesIO((pending / "candidate.FBU").read_bytes()[152:])) as archive:
                source = archive.read("Unzipped.src", pwd=b"unit-test-password").decode()
            self.assertIn("ContentName=FB_GEN_JOB [FB,LD]", source)
            self.assertIn("P_Lang=1", source)
            self.assertNotIn("<IL_ST_CODE>", source)
            suite = json.loads((pending / "suite.json").read_text(encoding="utf-8"))
            self.assertEqual(suite["execution_adapter"], "function-block-instance")

    def test_dvp_job_timestamp_is_derived_from_immutable_job_id(self) -> None:
        self.assertEqual(
            job_timestamp("1787040109516-87da80d52e35-a95929c9ac"),
            1787040109.516,
        )
        with self.assertRaises(ValueError):
            job_timestamp("not-a-job")

    def test_visible_and_sealed_worker_results_use_distinct_artifacts(self) -> None:
        self.assertEqual(
            result_artifact_name("feedback"),
            "dvp48es300r_feedback_result.json",
        )
        self.assertEqual(
            result_artifact_name("sealed"),
            "dvp48es300r_sealed_result.json",
        )
        with self.assertRaises(ValueError):
            result_artifact_name("unknown")

    def test_auditor_links_explicit_result_read_race_without_changing_gate_status(self) -> None:
        worker = {
            "job_id": "1787040109516-87da80d52e35-a95929c9ac",
            "submitted_at": 10.0,
            "task_id": "Demo",
            "candidate_sha256": "abc",
            "role": "feedback",
            "status": "pass",
        }
        index = {("Demo", "abc", "feedback"): [worker]}
        gate = {
            "status": "inconclusive",
            "summary": "Windows DVP worker returned unverifiable evidence",
            "evidence": [{
                "kind": "tool_error",
                "summary": "JSONDecodeError: Expecting value: line 1 column 1 (char 0)",
            }],
        }
        linked = find_job_for_gate(
            index,
            task_id="Demo",
            candidate_sha256="abc",
            role="feedback",
            gate=gate,
            started_at=0.0,
            finished_at=20.0,
        )
        self.assertIsNotNone(linked)
        assert linked is not None
        self.assertEqual(linked["adapter_status"], "inconclusive")
        self.assertEqual(linked["worker_status"], "pass")
        self.assertTrue(linked["transport_status_mismatch"])

    def test_auditor_does_not_relax_status_for_generic_inconclusive_gate(self) -> None:
        worker = {
            "job_id": "1787040109516-87da80d52e35-a95929c9ac",
            "submitted_at": 10.0,
            "task_id": "Demo",
            "candidate_sha256": "abc",
            "role": "feedback",
            "status": "pass",
        }
        index = {("Demo", "abc", "feedback"): [worker]}
        gate = {
            "status": "inconclusive",
            "summary": "COMMGR timed out",
            "evidence": [{"kind": "tool_error", "summary": "TimeoutExpired"}],
        }
        self.assertIsNone(find_job_for_gate(
            index,
            task_id="Demo",
            candidate_sha256="abc",
            role="feedback",
            gate=gate,
            started_at=0.0,
            finished_at=20.0,
        ))

    def test_worker_result_requires_all_three_gates_for_pass(self):
        import importlib.util

        path = Path(__file__).resolve().parents[1] / "scripts" / "dvp48es300r_validator.py"
        spec = importlib.util.spec_from_file_location("dvp_validator", path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        manifest = {
            "job_id": "job",
            "task_id": "Demo",
            "role": "feedback",
            "candidate_sha256": "abc",
            "target": "DVP48ES300R",
        }
        document = dict(manifest)
        document.update({
            "schema_version": 1,
            "status": "pass",
            "gates": [
                {"name": "ispsoft_compile", "status": "pass"},
                {"name": "commgr_connect", "status": "pass"},
                {"name": "dvp_es3_runtime", "status": "pass"},
            ],
        })
        self.assertEqual(module.validate_result(document, manifest)["status"], "pass")
        document["gates"][-1]["status"] = "inconclusive"
        with self.assertRaises(ValueError):
            module.validate_result(document, manifest)

    def test_worker_result_reader_retries_a_partial_redirected_drive_copy(self):
        import importlib.util

        path = Path(__file__).resolve().parents[1] / "scripts" / "dvp48es300r_validator.py"
        spec = importlib.util.spec_from_file_location("dvp_validator_retry", path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        manifest = {
            "job_id": "job",
            "task_id": "Demo",
            "role": "feedback",
            "candidate_sha256": "abc",
            "target": "DVP48ES300R",
        }
        document = dict(manifest)
        document.update({
            "schema_version": 1,
            "status": "pass",
            "gates": [
                {"name": "ispsoft_compile", "status": "pass"},
                {"name": "commgr_connect", "status": "pass"},
                {"name": "dvp_es3_runtime", "status": "pass"},
            ],
        })
        with tempfile.TemporaryDirectory() as directory:
            result_path = Path(directory) / "result.json"
            result_path.write_text("{", encoding="utf-8")

            def complete_copy() -> None:
                time.sleep(0.05)
                result_path.write_text(json.dumps(document), encoding="utf-8")

            writer = threading.Thread(target=complete_copy)
            writer.start()
            observed = module.load_worker_result(
                result_path,
                manifest,
                poll_seconds=0.01,
                parse_grace_seconds=0.5,
            )
            writer.join()
            self.assertEqual(observed["status"], "pass")

    def test_worker_result_reader_rejects_a_stable_malformed_result(self):
        import importlib.util

        path = Path(__file__).resolve().parents[1] / "scripts" / "dvp48es300r_validator.py"
        spec = importlib.util.spec_from_file_location("dvp_validator_bad_result", path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            result_path = Path(directory) / "result.json"
            result_path.write_text("{", encoding="utf-8")
            with self.assertRaises(json.JSONDecodeError):
                module.load_worker_result(
                    result_path,
                    {},
                    poll_seconds=0.01,
                    parse_grace_seconds=0.03,
                )

    def test_runtime_failure_is_normalized_as_actionable_feedback(self):
        import importlib.util

        path = Path(__file__).resolve().parents[1] / "scripts" / "dvp48es300r_validator.py"
        spec = importlib.util.spec_from_file_location("dvp_validator_feedback", path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        evidence = module.visible_feedback_evidence({
            "evidence": [{
                "case_id": "OT02",
                "status": "fail",
                "repetitions_executed": 2,
                "requirement_ids": ["R5"],
                "failures": [{
                    "step_index": 1,
                    "repeat_index": 0,
                    "output": "B_Vote",
                    "expected": True,
                    "actual": False,
                }],
            }],
        })
        self.assertEqual(evidence[0]["kind"], "dvp_runtime_failure")
        self.assertEqual(evidence[0]["requirement_ids"], ["R5"])
        self.assertEqual(evidence[0]["trace"]["case_id"], "OT02")
        self.assertEqual(evidence[0]["oracle_status"], "confirmed_candidate_defect")


class DifferentialAuditTests(unittest.TestCase):
    def test_reference_mismatch_is_not_preclassified_as_a_candidate_defect(self):
        evidence = normalize_reference_evidence([{
            "kind": "openplc_functional_failure",
            "oracle_status": "confirmed_candidate_defect",
            "requirement_ids": ["R1"],
            "summary": "candidate and reference differ",
        }])
        self.assertEqual(evidence[0]["kind"], "reference_behavior_divergence")
        self.assertEqual(
            evidence[0]["oracle_status"],
            "post_hoc_reference_divergence_requires_review",
        )
        self.assertEqual(evidence[0]["underlying_kind"], "openplc_functional_failure")
        self.assertEqual(evidence[0]["requirement_ids"], [])

    def test_pair_source_executes_candidate_and_reference_on_identical_inputs(self):
        source = build_pair_source(
            SIMPLE_ST,
            SIMPLE_ST,
            sample_metadata(),
            real_tolerance=0.01,
        )
        self.assertIn("FUNCTION_BLOCK EGBS_CANDIDATE", source)
        self.assertIn("FUNCTION_BLOCK EGBS_REFERENCE", source)
        self.assertIn("FUNCTION_BLOCK EGBS_DIFFERENTIAL", source)
        self.assertIn("Candidate(\n    Enable := Enable,", source)
        self.assertIn("Reference(\n    Enable := Enable,", source)
        self.assertIn("Candidate.Active = Reference.Active", source)
        self.assertIn("Candidate.Scaled >= (Reference.Scaled - 0.01)", source)
        self.assertIn("Match_Active := (Candidate.Active = Reference.Active);", source)
        self.assertIn("Equivalent := Match_Active AND Match_Scaled;", source)

    def test_stress_suite_is_deterministic_and_checks_every_scan(self):
        first = build_stress_suite(
            sample_metadata(), sample_suite(), case_count=2, scans_per_case=8, seed=7
        )
        second = build_stress_suite(
            sample_metadata(), sample_suite(), case_count=2, scans_per_case=8, seed=7
        )
        self.assertEqual(first, second)
        self.assertEqual(len(first["cases"]), 2)
        self.assertTrue(all(len(case["steps"]) == 8 for case in first["cases"]))
        self.assertTrue(all(
            step["expect"] == {"Equivalent": True} and step["check"] == "each"
            for case in first["cases"] for step in case["steps"]
        ))


class FinalReportTests(unittest.TestCase):
    def test_final_report_keeps_prespecified_and_reviewed_scores_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            batch = {
                "task_count": 2,
                "success_count": 1,
                "requested_model": "claude-sonnet-5",
                "method": "evidence",
                "status_counts": {"verified_success": 1, "candidate_budget_exhausted": 1},
                "verified_success_at_k": {"1": 1},
                "usage_total": {"total_tokens": 20},
                "runs": [
                    {"task_id": "T1", "success": True, "candidates_used": 1},
                    {"task_id": "T2", "success": False, "candidates_used": 10},
                ],
            }
            audit = {
                "audit_pass": True,
                "audited_task_count": 2,
                "verified_success_count": 1,
                "model_identity_valid": True,
                "successful_candidate_isolation_valid": True,
                "ledger_valid": True,
                "sealed_accounting_valid": True,
                "batch_summary_matches": True,
                "adapter_assets_ledgered": True,
                "frozen_source_sha256": "0" * 64,
                "tasks": [{
                    "task_id": "T1",
                    "dvp_jobs": [{"role": "feedback", "case_count": 2}],
                }],
            }
            differential = {
                "task_count": 2,
                "records": [
                    {"task_id": "T1", "status": "fail"},
                    {"task_id": "T2", "status": "not_applicable"},
                ],
            }
            review = {"records": [{
                "task_id": "T1",
                "classification": "acceptable_alternative",
                "rationale": "the public contract leaves this priority unspecified",
            }]}
            paths = {}
            for name, value in (
                ("batch", batch), ("audit", audit),
                ("differential", differential), ("review", review),
            ):
                paths[name] = root / f"{name}.json"
                paths[name].write_text(json.dumps(value), encoding="utf-8")
            output = root / "final.json"
            completed = subprocess.run([
                sys.executable,
                str(SCRIPTS / "build_dvp48es300r_final_report.py"),
                "--batch-summary", str(paths["batch"]),
                "--independent-audit", str(paths["audit"]),
                "--differential-audit", str(paths["differential"]),
                "--manual-review", str(paths["review"]),
                "--expected-task-count", "2",
                "--output", str(output),
            ], text=True, capture_output=True, check=True)
            self.assertIn('"report_valid": true', completed.stdout)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["prespecified_oracle"]["verified_success_count"], 1)
            self.assertEqual(
                report["post_hoc_differential_review"]["conservative_success_count"], 1
            )
            self.assertEqual(report["resource_usage"]["total_candidates"], 11)
            self.assertEqual(report["resource_usage"]["linked_windows_cases"], 2)

    def test_corrected_rate_requires_and_uses_independent_audits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            batch = {
                "task_count": 2,
                "success_count": 1,
                "requested_model": "claude-sonnet-5",
                "method": "evidence",
                "status_counts": {"verified_success": 1, "infrastructure_error": 1},
                "verified_success_at_k": {"1": 1},
                "usage_total": {"total_tokens": 20},
                "runs": [
                    {
                        "task_id": "T1", "success": True, "status": "verified_success",
                        "candidates_used": 1, "candidate_budget": 10,
                    },
                    {
                        "task_id": "T2", "success": False, "status": "infrastructure_error",
                        "candidates_used": 2, "candidate_budget": 10,
                    },
                ],
            }
            audit = {
                "audit_pass": True,
                "audited_task_count": 2,
                "verified_success_count": 1,
                "model_identity_valid": True,
                "successful_candidate_isolation_valid": True,
                "ledger_valid": True,
                "sealed_accounting_valid": True,
                "batch_summary_matches": True,
                "adapter_assets_ledgered": True,
                "frozen_source_sha256": "0" * 64,
                "tasks": [],
            }
            differential = {
                "task_count": 2,
                "records": [
                    {"task_id": "T1", "status": "pass"},
                    {"task_id": "T2", "status": "not_applicable"},
                ],
            }
            corrected = {
                "task_count": 1,
                "success_count": 1,
                "requested_model": "claude-sonnet-5",
                "method": "evidence",
                "status_counts": {"verified_success": 1},
                "runs": [{
                    "task_id": "T2", "success": True, "status": "verified_success",
                    "candidates_used": 1, "candidate_budget": 10,
                }],
            }
            corrected_audit = {
                "audit_pass": True,
                "audited_task_count": 1,
                "verified_success_count": 1,
                "model_identity_valid": True,
                "successful_candidate_isolation_valid": True,
                "ledger_valid": True,
                "sealed_accounting_valid": True,
                "batch_summary_matches": True,
            }
            corrected_differential = {
                "task_count": 1,
                "records": [{"task_id": "T2", "status": "pass"}],
            }
            paths = {}
            for name, value in (
                ("batch", batch), ("audit", audit),
                ("differential", differential), ("corrected", corrected),
                ("corrected_audit", corrected_audit),
                ("corrected_differential", corrected_differential),
            ):
                paths[name] = root / f"{name}.json"
                paths[name].write_text(json.dumps(value), encoding="utf-8")
            output = root / "final.json"
            completed = subprocess.run([
                sys.executable,
                str(SCRIPTS / "build_dvp48es300r_final_report.py"),
                "--batch-summary", str(paths["batch"]),
                "--independent-audit", str(paths["audit"]),
                "--differential-audit", str(paths["differential"]),
                "--corrected-infrastructure-summary", str(paths["corrected"]),
                "--corrected-infrastructure-audit", str(paths["corrected_audit"]),
                "--corrected-infrastructure-differential",
                str(paths["corrected_differential"]),
                "--expected-task-count", "2",
                "--output", str(output),
            ], text=True, capture_output=True, check=True)
            self.assertIn('"report_valid": true', completed.stdout)
            report = json.loads(output.read_text(encoding="utf-8"))
            corrected_report = report["infrastructure_corrected_protocol"]
            self.assertTrue(corrected_report["cross_layer_audit_pass"])
            self.assertEqual(corrected_report["corrected_verified_success_count"], 2)
            self.assertEqual(corrected_report["conservative_corrected_success_count"], 2)

    def test_negative_control_requires_both_runtimes_to_reject_only_candidate(self):
        expected = {
            "candidate": {
                "openplc": {"status": "fail"},
                "dvp48es300r": {"status": "fail"},
            },
            "reference": {
                "openplc": {"status": "pass"},
                "dvp48es300r": {"status": "pass"},
            },
        }
        self.assertTrue(calibration_verdict(expected))
        expected["candidate"]["dvp48es300r"]["status"] = "pass"
        self.assertFalse(calibration_verdict(expected))


if __name__ == "__main__":
    unittest.main()

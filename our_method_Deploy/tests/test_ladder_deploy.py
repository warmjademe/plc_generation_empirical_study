from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

from plc_deploy.pipeline import _validator_config
from plc_deploy.schemas import JobCreate
from plc_deploy.settings import Settings
from plc_loop.delta_dvp import render_native_ld_function_block_source
from plc_loop.ladder import compile_ladder_document
from plc_loop.response import parse_candidate


ROOT = Path(__file__).resolve().parents[1]
INTERFACE = (ROOT / "fixtures/smoke_task/SMOKE_MOTOR/interface.st").read_text()


def document() -> dict:
    return {
        "schema_version": "1.0",
        "function_block": "SMOKE_MOTOR",
        "locals": [{"name": "RunLatch", "type": "BOOL", "initial": False}],
        "rungs": [
            {
                "id": "RUNG_01", "comment": "启动锁存",
                "condition": {"op": "var", "name": "Start"},
                "instructions": [{"type": "coil", "target": "RunLatch", "mode": "set"}],
            },
            {
                "id": "RUNG_02", "comment": "停止优先",
                "condition": {"op": "var", "name": "Stop"},
                "instructions": [{"type": "coil", "target": "RunLatch", "mode": "reset"}],
            },
            {
                "id": "RUNG_03", "comment": "驱动输出",
                "condition": {"op": "var", "name": "RunLatch"},
                "instructions": [{"type": "coil", "target": "Motor", "mode": "normal"}],
            },
        ],
    }


def test_ladder_ir_produces_st_svg_and_native_ispsoft_ld() -> None:
    compiled = compile_ladder_document(document(), INTERFACE, "SMOKE_MOTOR")
    ET.fromstring(compiled.svg)
    assert "RunLatch := TRUE" in compiled.st_program
    native = render_native_ld_function_block_source(
        document(), INTERFACE, "SMOKE_MOTOR"
    )
    assert native.network_count == 3
    assert b"ContentName=SMOKE_MOTOR [FB,LD]" in native.source
    assert b"P_Lang=1" in native.source


def test_native_ispsoft_ld_pushes_compound_negation_to_contacts() -> None:
    value = document()
    value["rungs"] = [{
        "id": "RUNG_01",
        "comment": "NOT(Start AND Stop) becomes two parallel NC contacts",
        "condition": {
            "op": "not",
            "arg": {
                "op": "and",
                "args": [
                    {"op": "var", "name": "Start"},
                    {"op": "var", "name": "Stop"},
                ],
            },
        },
        "instructions": [{"type": "coil", "target": "Motor", "mode": "normal"}],
    }]

    native = render_native_ld_function_block_source(
        value, INTERFACE, "SMOKE_MOTOR"
    )
    source = native.source.decode("utf-8")
    assert native.network_count == 1
    assert source.count("TYPE=2") == 2
    assert "TYPE=6" in source
    assert "DEV_NAME=Start" in source
    assert "DEV_NAME=Stop" in source


def test_ladder_response_is_canonicalized_before_validation() -> None:
    content = (
        "<repair_hypothesis>有序线圈</repair_hypothesis>\n"
        "<target_requirements>R1</target_requirements>\n"
        f"<ladder_program>{json.dumps(document(), ensure_ascii=False)}</ladder_program>"
    )
    parsed = parse_candidate(
        {"content": content}, {"R1"}, output_language="ld",
        interface_text=INTERFACE, task_id="SMOKE_MOTOR",
    )
    assert parsed.format_valid
    assert parsed.source_language == "ld"
    assert parsed.source_text.endswith("\n")
    assert parsed.ladder_svg and parsed.program


def test_ladder_response_accepts_json_envelope_used_by_deepseek() -> None:
    content = json.dumps({
        "repair_hypothesis": "使用停止优先级",
        "target_requirements": ["R1"],
        "ladder_program": document(),
    }, ensure_ascii=False)
    parsed = parse_candidate(
        {"content": content}, {"R1"}, output_language="ld",
        interface_text=INTERFACE, task_id="SMOKE_MOTOR",
    )
    assert parsed.format_valid
    assert parsed.extraction_mode == "json_envelope"
    assert parsed.target_requirement_ids == ("R1",)


def test_ladder_response_accepts_raw_ladder_json_for_initial_synthesis() -> None:
    parsed = parse_candidate(
        {"content": json.dumps(document(), ensure_ascii=False)}, {"R1"},
        output_language="ld", interface_text=INTERFACE, task_id="SMOKE_MOTOR",
    )
    assert parsed.format_valid
    assert parsed.extraction_mode == "raw_ladder_json"
    assert parsed.target_requirement_ids == ("R1",)


def test_web_request_and_harness_config_carry_output_language(
    tmp_path: Path, monkeypatch,
) -> None:
    request = JobCreate(
        requirement="Generate a verified motor control function block.",
        output_language="ld",
    )
    assert request.output_language == "ld"
    monkeypatch.setenv("PLC_PROJECT_ROOT", str(ROOT))
    monkeypatch.setenv("PLC_TOOL_ROOT", str(tmp_path / "tools"))
    config = _validator_config(
        Settings.load(),
        {
            "name": "test", "base_url": "https://example.test/v1",
            "api_key_env": "UNUSED", "requested_model": "test",
            "allowed_resolved_models": ["test"],
        },
        2, "delta", "DVP48ES300R", "ld",
    )
    assert config["experiment"]["output_language"] == "ld"
    assert "native [FB,LD]" in config["experiment"]["verification_profile"]


def test_page_exposes_ladder_selection_and_artifacts() -> None:
    page = (ROOT / "templates/app.html").read_text(encoding="utf-8")
    script = (ROOT / "static/app.js").read_text(encoding="utf-8")
    worker = (ROOT / "windows/Run-DvpValidationWorker.ps1").read_text(encoding="utf-8")
    assert 'id="outputLanguage"' in page
    assert 'id="ladderDiagram"' in page
    assert "output_language:$('outputLanguage').value" in script
    assert "importing generated $($manifest.candidate_language) function block" in worker

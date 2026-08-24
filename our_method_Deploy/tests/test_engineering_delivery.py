from __future__ import annotations

import json
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from plc_deploy.schemas import ContractDecision, JobCreate
from plc_loop.delta_dvp import (
    EngineeringConfigError,
    build_engineering_template,
    parse_function_block,
    render_deployment_program,
    validate_engineering_config,
)


def load_vendor_validator():
    project = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "engineering_delivery_vendor_validator",
        project / "scripts/dvp48es300r_validator.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def contract(*, numeric: bool = False) -> dict:
    return {
        "task_id": "PLC_TEST_APP",
        "scan_period_ms": 100,
        "interface": {
            "inputs": [
                {"name": "Start", "type": "INT" if numeric else "BOOL", "description": "启动"},
                {"name": "Stop", "type": "BOOL", "description": "停止"},
            ],
            "outputs": [
                {"name": "Motor", "type": "BOOL", "description": "电机"},
            ],
        },
    }


def confirmed(document: dict) -> dict:
    value = json.loads(json.dumps(document))
    value["wiring_review_acknowledged"] = True
    value["field_acceptance_acknowledged"] = True
    return value


@pytest.mark.parametrize(
    ("target", "input_addresses", "output_address"),
    [
        ("DVP48ES300R", ["X0", "X1"], "Y0"),
        ("AS228T-A", ["X0.0", "X0.1"], "Y0.0"),
    ],
)
def test_engineering_template_binds_each_interface_to_target_built_in_io(
    target: str, input_addresses: list[str], output_address: str
) -> None:
    template = build_engineering_template(contract(), target)
    assert [item["address"] for item in template["mappings"][:2]] == input_addresses
    assert template["mappings"][2]["address"] == output_address
    normalized = validate_engineering_config(confirmed(template), contract(), target)
    assert normalized["target"] == target


def test_engineering_contract_rejects_duplicate_or_unconfirmed_addresses() -> None:
    template = build_engineering_template(contract(), "AS228T-A")
    with pytest.raises(EngineeringConfigError, match="not been explicitly confirmed"):
        validate_engineering_config(template, contract(), "AS228T-A")
    duplicate = confirmed(template)
    duplicate["mappings"][1]["address"] = duplicate["mappings"][0]["address"]
    with pytest.raises(EngineeringConfigError, match="assigned more than once"):
        validate_engineering_config(duplicate, contract(), "AS228T-A")


def test_downloadable_project_fails_closed_for_unconfigured_numeric_io() -> None:
    with pytest.raises(EngineeringConfigError, match="require BOOL external ports"):
        build_engineering_template(contract(numeric=True), "DVP48ES300R")


def test_rendered_deployment_main_uses_confirmed_polarity_and_complete_interface() -> None:
    template = confirmed(build_engineering_template(contract(), "AS228T-A"))
    template["mappings"][1]["active_high"] = False
    block = parse_function_block(
        """FUNCTION_BLOCK PLC_TEST_APP
VAR_INPUT
    Start : BOOL;
    Stop : BOOL;
END_VAR
VAR_OUTPUT
    Motor : BOOL;
END_VAR
Motor := Start AND NOT Stop;
END_FUNCTION_BLOCK
"""
    )
    declarations, body, readable = render_deployment_program(block, contract(), template)
    assert declarations[0].name == "APP"
    assert "Start := X0.0" in body
    assert "Stop := NOT X0.1" in body
    assert "Y0.0 := APP.Motor;" in body
    assert readable.startswith("PROGRAM MAIN\n")


def test_api_model_keeps_legacy_default_while_accepting_project_mapping() -> None:
    request = JobCreate(requirement="输入 Start，输出 Motor，Stop 优先。")
    assert request.delivery_mode == "function_unit"
    decision = ContractDecision(approve=True, engineering_config={"schema_version": 1})
    assert decision.engineering_config == {"schema_version": 1}


def test_worker_and_web_expose_deployment_project_flow() -> None:
    project = Path(__file__).resolve().parents[1]
    worker = (project / "windows/Run-DvpValidationWorker.ps1").read_text(encoding="utf-8")
    validator = (project / "scripts/dvp48es300r_validator.py").read_text(encoding="utf-8")
    page = (project / "templates/app.html").read_text(encoding="utf-8")
    script = (project / "static/app.js").read_text(encoding="utf-8")
    for marker in (
        "deployment_compile",
        "downloadable_project.zip",
        "field_acceptance_checklist.json",
        "Compress-Archive",
        "$script:deploymentMainY = 394",
        "Remove-PlaceholderMain $main.hwnd $deploymentMainY",
        "Start-Sleep -Milliseconds 500",
        "$result.gates[2].status = 'pass'",
    ):
        assert marker in worker
    assert "render_deployment_program" in validator
    for element in (
        'id="deliveryMode"',
        'id="engineeringPanel"',
        'id="engineeringMappings"',
        'id="wiringReviewAck"',
        'id="fieldAcceptanceAck"',
    ):
        assert element in page
    assert "collectEngineeringConfig" in script
    assert "物理 I/O 映射不能自动确认" in script


def test_project_delivery_result_requires_and_accepts_four_passing_gates() -> None:
    validator = load_vendor_validator()
    manifest = {
        "job_id": "job-1",
        "task_id": "SMOKE_MOTOR",
        "role": "all",
        "candidate_sha256": "abc",
        "target": "DVP48ES300R",
        "worker_id": "vps_windows_04",
        "delivery_mode": "downloadable_project",
    }
    document = {
        **{key: manifest[key] for key in (
            "job_id", "task_id", "role", "candidate_sha256", "target", "worker_id"
        )},
        "schema_version": 1,
        "status": "pass",
        "gates": [
            {"name": "ispsoft_compile", "status": "pass"},
            {"name": "commgr_connect", "status": "pass"},
            {"name": "dvp_es3_runtime", "status": "pass"},
            {"name": "deployment_compile", "status": "pass"},
        ],
    }
    assert validator.validate_result(document, manifest)["status"] == "pass"
    with pytest.raises(ValueError, match="four passing gates|4 passing gates"):
        validator.validate_result(
            {**document, "gates": [*document["gates"][:-1], {
                "name": "deployment_compile", "status": "fail"
            }]},
            manifest,
        )


@pytest.mark.parametrize("target", ["DVP48ES300R", "AS228T-A"])
def test_vendor_validator_packages_separate_test_and_deployment_main(
    target: str, tmp_path: Path
) -> None:
    project = Path(__file__).resolve().parents[1]
    source_task = project / "fixtures/smoke_task/SMOKE_MOTOR"
    task = tmp_path / "SMOKE_MOTOR"
    shutil.copytree(source_task, task)
    metadata = json.loads((task / "metadata.json").read_text(encoding="utf-8"))
    mapping = confirmed(build_engineering_template(metadata, target))
    (task / "engineering_config.json").write_text(
        json.dumps(mapping, ensure_ascii=False), encoding="utf-8"
    )
    spool = tmp_path / "spool"
    environment = dict(os.environ)
    environment["DELTAPLC_ISPSOFT_SOURCE_PASSWORD"] = "unit-test-only"
    result = subprocess.run(
        [
            sys.executable,
            str(project / "scripts/dvp48es300r_validator.py"),
            "--candidate", str(task / "reference.st"),
            "--task-dir", str(task),
            "--case-role", "all",
            "--spool-root", str(spool),
            "--target", target,
            "--prepare-only",
        ],
        cwd=tmp_path,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout)["status"] == "inconclusive"
    pending = next((spool / "pending").iterdir())
    manifest = json.loads((pending / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["delivery_mode"] == "downloadable_project"
    assert manifest["target"] == target
    assert (pending / "MAIN.MPU").read_bytes() != (pending / "deployment.MPU").read_bytes()
    assert "PROGRAM MAIN" in (pending / "deployment_main.st").read_text(encoding="utf-8")
    assert (tmp_path / "candidate.ISPSoft.FBU").is_file()

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from plc_deploy.contracts import SEMANTIC_AUDIT_VERSION


def test_openplc_validator_uses_contract_semantic_audit_version() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts/openplc_sealed_validator.py"
    spec = importlib.util.spec_from_file_location("openplc_sealed_validator", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.SEMANTIC_AUDIT_VERSION == SEMANTIC_AUDIT_VERSION


def test_fixed_smoke_oracles_use_current_semantic_audit_version() -> None:
    root = Path(__file__).resolve().parents[1] / "fixtures/smoke_task/SMOKE_MOTOR"
    for name in ("metadata.json", "properties.json", "openplc_tests.json"):
        document = json.loads((root / name).read_text(encoding="utf-8"))
        assert document["semantic_audit"]["version"] == SEMANTIC_AUDIT_VERSION


def test_preflight_actually_verifies_frozen_tool_and_container_manifest() -> None:
    root = Path(__file__).resolve().parents[1]
    preflight = (root / "scripts/preflight.py").read_text(encoding="utf-8")
    verifier = (root / "scripts/verify_toolchain_manifest.py").read_text(encoding="utf-8")
    postgres = (root / "deploy/plc-generation-postgres.service").read_text(encoding="utf-8")
    manifest = json.loads((root / "deploy/tool-manifest.json").read_text(encoding="utf-8"))
    assert "verify_manifest(settings.project_root, settings.tool_root)" in preflight
    assert "file_sha256" in verifier and "docker_image_id" in verifier
    assert manifest["postgres_image"]["reference"] in postgres
    assert manifest["postgres_image"]["image_id"].startswith("sha256:")

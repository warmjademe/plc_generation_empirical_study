#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from plc_loop.dataset import load_task
from plc_loop.validators import validators_from_config
from plc_deploy.pipeline import _validator_config
from plc_deploy.settings import Settings
from verify_toolchain_manifest import verify_manifest


def main() -> int:
    settings = Settings.load()
    manifest_result = verify_manifest(settings.project_root, settings.tool_root)
    if manifest_result["status"] != "pass":
        print(json.dumps({"status": "fail", "phase": "tool_manifest", **manifest_result}, ensure_ascii=False, indent=2))
        return 1
    task_root = settings.project_root / "fixtures/smoke_task/SMOKE_MOTOR"
    task = load_task(task_root)
    provider = {
        "name": "preflight-no-model-call", "base_url": "https://invalid.example/v1",
        "api_key_env": "PREFLIGHT_UNUSED", "requested_model": "unused",
        "allowed_resolved_models": ["unused"],
    }
    config = _validator_config(settings, provider, 2)
    validators = validators_from_config(config["validators"], settings.project_root / "configs")
    results: dict[str, dict] = {}
    with tempfile.TemporaryDirectory(prefix="plc-preflight-") as temporary:
        root = Path(temporary)
        for validator in validators:
            validator.preflight(task)
            artifact = root / f"good_{validator.name}"
            artifact.mkdir()
            result = validator.run(task, task_root / "reference.st", artifact)
            results[validator.name] = result.to_dict()
            if result.status != "pass":
                print(json.dumps({"status": "fail", "phase": "known_good", "results": results}, ensure_ascii=False, indent=2))
                return 1
        negative_results = {}
        for validator in validators:
            if validator.name in {"interface", "compiler"}:
                continue
            artifact = root / f"bad_{validator.name}"
            artifact.mkdir()
            result = validator.run(task, task_root / "known_bad.st", artifact)
            negative_results[validator.name] = result.to_dict()
            if result.status != "fail":
                print(json.dumps({"status": "fail", "phase": "known_bad", "positive": results,
                                  "negative": negative_results}, ensure_ascii=False, indent=2))
                return 1
    print(json.dumps({"status": "pass", "tool_manifest": manifest_result, "known_good": results, "known_bad": negative_results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

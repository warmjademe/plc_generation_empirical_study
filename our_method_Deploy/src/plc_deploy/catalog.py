from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"catalog is not an object: {path}")
    return value


class Catalog:
    def __init__(self, config_dir: Path):
        self.vendors = _load(config_dir / "vendors.json")["vendors"]
        self.models = _load(config_dir / "models.json")["models"]

    def model(self, model_id: str) -> dict[str, Any]:
        match = next((item for item in self.models if item["id"] == model_id), None)
        if match is None:
            raise ValueError(f"unknown model: {model_id}")
        return dict(match)

    def target(self, vendor_id: str, model_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        vendor = next((item for item in self.vendors if item["id"] == vendor_id), None)
        if vendor is None:
            raise ValueError(f"unknown PLC vendor: {vendor_id}")
        model = next((item for item in vendor["models"] if item["id"] == model_id), None)
        if model is None:
            raise ValueError(f"model {model_id!r} does not belong to vendor {vendor_id!r}")
        return dict(vendor), dict(model)

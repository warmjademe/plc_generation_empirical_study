"""Append-only, hash-chained JSONL evidence ledger."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


GENESIS_HASH = "0" * 64


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


class EvidenceLedger:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.sequence = 0
        self.previous_hash = GENESIS_HASH
        if path.exists() and path.stat().st_size:
            entries = self.verify(path)
            self.sequence = entries[-1]["sequence"]
            self.previous_hash = entries[-1]["event_hash"]

    def append(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        core = {
            "sequence": self.sequence + 1,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "previous_hash": self.previous_hash,
            "event_type": event_type,
            "payload": payload,
        }
        event = {**core, "event_hash": hashlib.sha256(_canonical(core)).hexdigest()}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
        self.sequence = event["sequence"]
        self.previous_hash = event["event_hash"]
        return event

    @staticmethod
    def verify(path: Path) -> list[dict[str, Any]]:
        previous = GENESIS_HASH
        entries = []
        for expected_sequence, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            event = json.loads(line)
            if event.get("sequence") != expected_sequence:
                raise ValueError(f"ledger sequence mismatch at line {expected_sequence}")
            if event.get("previous_hash") != previous:
                raise ValueError(f"ledger chain mismatch at line {expected_sequence}")
            supplied_hash = event.get("event_hash")
            core = {key: value for key, value in event.items() if key != "event_hash"}
            calculated = hashlib.sha256(_canonical(core)).hexdigest()
            if supplied_hash != calculated:
                raise ValueError(f"ledger event hash mismatch at line {expected_sequence}")
            previous = supplied_hash
            entries.append(event)
        return entries


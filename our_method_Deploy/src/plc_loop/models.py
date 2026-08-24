"""Shared immutable experiment records."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any


VALID_STATUSES = {"pass", "fail", "inconclusive", "skipped"}


def canonical_hash(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Evidence:
    tool: str
    kind: str
    summary: str
    requirement_ids: tuple[str, ...] = ()
    severity: str = "error"
    trace: Any = None
    oracle_status: str = "unconfirmed"
    raw_log_sha256: str | None = None

    @property
    def signature(self) -> str:
        normalized_summary = re.sub(
            r"(?:/[A-Za-z0-9_.-]+)+/candidate\.st",
            "<candidate.st>",
            self.summary,
        )
        return canonical_hash(
            {
                "tool": self.tool,
                "kind": self.kind,
                "requirements": sorted(self.requirement_ids),
                "summary": normalized_summary,
                "oracle_status": self.oracle_status,
            }
        )[:16]

    def to_dict(self) -> dict:
        value = asdict(self)
        value["signature"] = self.signature
        value["requirement_ids"] = list(self.requirement_ids)
        return value


@dataclass(frozen=True)
class GateResult:
    name: str
    status: str
    summary: str
    evidence: tuple[Evidence, ...] = ()
    passed_requirement_ids: tuple[str, ...] = ()
    duration_ms: int = 0
    tool_version: str | None = None

    def __post_init__(self) -> None:
        if self.status not in VALID_STATUSES:
            raise ValueError(f"invalid gate status {self.status!r}")

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "summary": self.summary,
            "evidence": [item.to_dict() for item in self.evidence],
            "passed_requirement_ids": list(self.passed_requirement_ids),
            "duration_ms": self.duration_ms,
            "tool_version": self.tool_version,
        }


@dataclass(frozen=True)
class ModelReply:
    message: dict[str, Any]
    raw_response: dict[str, Any]
    requested_model: str
    resolved_model: str
    provider: str
    usage: dict[str, Any]
    finish_reason: str | None
    latency_ms: int


@dataclass(frozen=True)
class ParsedCandidate:
    program: str
    hypothesis: str
    target_requirement_ids: tuple[str, ...]
    format_valid: bool
    format_errors: tuple[str, ...] = ()
    extraction_mode: str = "strict_tagged"
    source_language: str = "st"
    source_text: str = ""
    ladder_document: dict[str, Any] | None = None
    ladder_svg: str | None = None


@dataclass
class AttemptOutcome:
    number: int
    candidate_path: str
    candidate_sha256: str
    candidate: ParsedCandidate
    gates: list[GateResult]
    repair_mode: str
    anchor_attempt: int | None
    usage: dict[str, Any] = field(default_factory=dict)
    resolved_model: str | None = None
    generation_epoch: int = 1
    diversification_profile: str | None = None

    @property
    def failed_requirements(self) -> set[str]:
        """Requirements contradicted by trustworthy candidate-defect evidence."""
        return {
            requirement
            for evidence in self.failing_evidence
            if evidence.oracle_status != "unconfirmed"
            for requirement in evidence.requirement_ids
        }

    @property
    def passed_requirements(self) -> set[str]:
        """Requirements supported without a counterexample in the same attempt.

        A multi-property validator can return a failing gate while also reporting
        the properties that passed.  The previous implementation discarded that
        partial evidence because it required the *whole gate* to pass.  This made
        most formal-failure candidates look equally unsupported and trapped the
        non-regression anchor on an early candidate.  A requirement is supported
        here only when at least one validator reports it and no trustworthy
        failure in the same attempt contradicts it.
        """
        observed = {
            requirement
            for gate in self.gates
            for requirement in gate.passed_requirement_ids
        }
        return observed - self.failed_requirements

    @property
    def failing_evidence(self) -> list[Evidence]:
        return [evidence for gate in self.gates if gate.status == "fail" for evidence in gate.evidence]

    @property
    def passed_gate_count(self) -> int:
        return sum(gate.status == "pass" for gate in self.gates)

    def to_dict(self) -> dict:
        return {
            "number": self.number,
            "candidate_path": self.candidate_path,
            "candidate_sha256": self.candidate_sha256,
            "candidate": {
                "hypothesis": self.candidate.hypothesis,
                "target_requirement_ids": list(self.candidate.target_requirement_ids),
                "format_valid": self.candidate.format_valid,
                "format_errors": list(self.candidate.format_errors),
                "extraction_mode": self.candidate.extraction_mode,
                "source_language": self.candidate.source_language,
            },
            "gates": [gate.to_dict() for gate in self.gates],
            "repair_mode": self.repair_mode,
            "anchor_attempt": self.anchor_attempt,
            "usage": self.usage,
            "resolved_model": self.resolved_model,
            "generation_epoch": self.generation_epoch,
            "diversification_profile": self.diversification_profile,
        }

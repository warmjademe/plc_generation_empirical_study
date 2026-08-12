"""Deterministic evidence selection, anchor scoring, and repair-mode policy."""

from __future__ import annotations

import json
from collections import Counter

from .models import AttemptOutcome, Evidence


def choose_anchor(attempts: list[AttemptOutcome], critical_ids: set[str]) -> AttemptOutcome | None:
    if not attempts:
        return None

    def score(attempt: AttemptOutcome) -> tuple[int, int, int, int, int]:
        passed = attempt.passed_requirements
        return (
            len(passed & critical_ids),
            len(passed),
            attempt.passed_gate_count,
            -len({item.signature for item in attempt.failing_evidence}),
            # Equal evidence should keep the newest implementation.  Preferring
            # the oldest candidate caused neutral structural improvements to be
            # discarded and repeatedly reintroduced the same defect.
            attempt.number,
        )

    return max(attempts, key=score)


def choose_repair_mode(attempts: list[AttemptOutcome]) -> str:
    if not attempts:
        return "SYNTHESIZE"
    latest = attempts[-1]
    if any(
        latest.candidate_sha256 == previous.candidate_sha256
        for previous in attempts[:-1]
    ):
        return "RESTART"
    latest_kinds = {item.kind for item in latest.failing_evidence}
    if "duplicate_candidate" in latest_kinds:
        return "RESTART"
    if latest_kinds and latest_kinds <= {
        "response_format", "interface_error", "compile_error", "formal_source_error"
    }:
        return "PATCH"
    latest_signatures = {item.signature for item in latest.failing_evidence}
    if len(attempts) >= 2:
        previous_signatures = {item.signature for item in attempts[-2].failing_evidence}
        if latest_signatures and latest_signatures == previous_signatures:
            # Escalate once, then change strategy.  The old policy selected
            # RESTART forever after one repeated signature, even though every
            # restart prompt still contained the same anchor program.
            if latest.repair_mode == "RESTART":
                return "RESTRUCTURE"
            if latest.repair_mode == "RESTRUCTURE":
                return "RESTART"
            return "RESTRUCTURE"
    affected = {requirement for item in latest.failing_evidence for requirement in item.requirement_ids}
    if len(affected) >= 2 or len(latest.failing_evidence) >= 3:
        return "RESTRUCTURE"
    return "PATCH"


def _clip(value: object, limit: int) -> object:
    """Bound verbose diagnostic strings without changing structured values."""
    if isinstance(value, str):
        if len(value) <= limit:
            return value
        head = max(0, limit // 3)
        tail = max(0, limit - head - 38)
        return value[:head] + "\n...[diagnostic middle omitted]...\n" + value[-tail:]
    if isinstance(value, dict):
        return {str(key): _clip(item, limit) for key, item in value.items()}
    if isinstance(value, list):
        return [_clip(item, limit) for item in value]
    return value


def _certificate_record(
    attempt_number: int,
    item: Evidence,
    frequencies: Counter[str],
) -> dict:
    return {
        "attempt": attempt_number,
        "tool": item.tool,
        "kind": item.kind,
        "requirement_ids": list(item.requirement_ids),
        "summary": _clip(item.summary, 700),
        "oracle_status": item.oracle_status,
        "signature": item.signature,
        "seen_count": frequencies[item.signature],
        "trace": _clip(item.trace, 1400),
    }


def _json_characters(value: object) -> int:
    return len(json.dumps(value, ensure_ascii=False, sort_keys=True))


def _fit_certificate(document: dict, max_chars: int) -> dict:
    """Enforce the advertised prompt budget while retaining current evidence."""
    document["character_budget"] = max_chars
    while _json_characters(document) > max_chars and document["historical_failure_memory"]:
        document["historical_failure_memory"].pop()
    while _json_characters(document) > max_chars and len(document["attempt_history"]) > 1:
        document["attempt_history"].pop(0)
    while _json_characters(document) > max_chars and len(document["selected_failures"]) > 1:
        document["selected_failures"].pop()
    if _json_characters(document) > max_chars and document["selected_failures"]:
        document["selected_failures"][0]["trace"] = _clip(
            document["selected_failures"][0].get("trace"), 500
        )
    if _json_characters(document) > max_chars:
        document["attempt_history"] = []
        document["historical_failure_memory"] = []
        document["budget_emergency_truncated"] = True
    if _json_characters(document) > max_chars and document["selected_failures"]:
        record = document["selected_failures"][0]
        record["trace"] = None
        record["summary"] = _clip(record.get("summary", ""), 240)
    if _json_characters(document) > max_chars:
        # This only applies to unrealistically tiny test configurations.  Keep
        # the actionable current failure and the declared budget.
        document = {
            "format": document["format"],
            "selected_failures": document["selected_failures"][:1],
            "character_budget": max_chars,
            "budget_emergency_truncated": True,
        }
    return document


def build_evidence_certificate_v3(
    attempts: list[AttemptOutcome],
    anchor: AttemptOutcome | None,
    critical_ids: set[str],
    max_chars: int,
) -> dict:
    """Focus on current/anchor defects and keep older failures as compact memory."""
    located = [
        (attempt.number, item)
        for attempt in attempts
        for item in attempt.failing_evidence
        if item.oracle_status != "unconfirmed"
    ]
    frequencies = Counter(item.signature for _, item in located)
    latest_located = [
        (attempts[-1].number, item)
        for item in attempts[-1].failing_evidence
        if item.oracle_status != "unconfirmed"
    ] if attempts else []
    anchor_located = [
        (anchor.number, item)
        for item in anchor.failing_evidence
        if item.oracle_status != "unconfirmed"
    ] if anchor and (not attempts or anchor.number != attempts[-1].number) else []

    selected_pairs: list[tuple[int, Evidence]] = []
    selected_signatures: set[str] = set()
    for pair in sorted(
        latest_located + anchor_located,
        key=lambda pair: _evidence_priority(pair[1], critical_ids, frequencies),
    ):
        if pair[1].signature not in selected_signatures:
            selected_pairs.append(pair)
            selected_signatures.add(pair[1].signature)
    selected = [
        _certificate_record(number, item, frequencies)
        for number, item in selected_pairs[:6]
    ]

    last_seen: dict[str, tuple[int, Evidence]] = {}
    for number, item in located:
        last_seen[item.signature] = (number, item)
    historical = [
        {
            "signature": signature,
            "last_attempt": number,
            "seen_count": frequencies[signature],
            "kind": item.kind,
            "requirement_ids": list(item.requirement_ids),
            "summary": _clip(item.summary, 240),
        }
        for signature, (number, item) in sorted(
            last_seen.items(), key=lambda pair: (-pair[1][0], pair[0])
        )
        if signature not in selected_signatures
    ][:12]

    latest_passed = attempts[-1].passed_requirements if attempts else set()
    anchor_passed = anchor.passed_requirements if anchor else set()
    current_kinds = {item.kind for _, item in latest_located}
    directives = []
    if any(frequencies[item.signature] >= 2 for _, item in latest_located):
        directives.append(
            "The current defect repeated; derive the violated predicate from its exact inputs and outputs before changing code."
        )
    if current_kinds & {"openplc_functional_failure", "test_failure"}:
        directives.append(
            "Replay each reported scan from a fresh instance and compare post-scan expected and observed outputs."
        )
    if "formal_counterexample" in current_kinds:
        directives.append(
            "Implement the reported violated condition literally; do not add unrelated guards absent from the public requirement."
        )
    if current_kinds & {"compile_error", "interface_error", "response_format", "formal_source_error"}:
        directives.append("Repair only the blocking source defect before functional changes.")

    document = {
        "format": "requirement-aligned-failure-certificate-v3",
        "anchor_attempt": anchor.number if anchor else None,
        "requirements_supported_by_anchor": sorted(anchor_passed),
        "requirements_supported_by_latest": sorted(latest_passed),
        "latest_regressions_against_anchor": sorted(anchor_passed - latest_passed),
        "selected_failures": selected,
        "historical_failure_memory": historical,
        "attempt_history": [
            {
                "attempt": attempt.number,
                "repair_mode": attempt.repair_mode,
                "anchor_attempt": attempt.anchor_attempt,
                "hypothesis": _clip(attempt.candidate.hypothesis, 260),
                "supported_requirements": sorted(attempt.passed_requirements),
                "failed_requirements": sorted(attempt.failed_requirements),
                "failure_signatures": sorted({
                    item.signature for item in attempt.failing_evidence
                    if item.oracle_status != "unconfirmed"
                }),
            }
            for attempt in attempts[-4:]
        ],
        "repair_directives": directives,
        "selection_policy": [
            "current candidate defects before historical defects",
            "anchor defect included only when distinct",
            "unconfirmed tool failures excluded from repair evidence",
            "hard character budget",
        ],
    }
    return _fit_certificate(document, max_chars)


def _evidence_priority(item: Evidence, critical_ids: set[str], seen: Counter[str]) -> tuple:
    safety = bool(set(item.requirement_ids) & critical_ids)
    blocking = item.kind in {"response_format", "interface_error", "compile_error"}
    novel = seen[item.signature] == 1
    trace_length = len(json.dumps(item.trace, ensure_ascii=False)) if item.trace is not None else 0
    return (not safety, not blocking, not novel, trace_length, item.signature)


def build_evidence_certificate(
    attempts: list[AttemptOutcome],
    anchor: AttemptOutcome | None,
    critical_ids: set[str],
    max_chars: int,
) -> dict:
    evidence = [item for attempt in attempts for item in attempt.failing_evidence]
    frequencies = Counter(item.signature for item in evidence)
    selected = []
    used = 0
    for item in sorted(evidence, key=lambda value: _evidence_priority(value, critical_ids, frequencies)):
        record = {
            "tool": item.tool,
            "kind": item.kind,
            "requirement_ids": list(item.requirement_ids),
            "summary": item.summary,
            "oracle_status": item.oracle_status,
            "signature": item.signature,
            "seen_count": frequencies[item.signature],
            "trace": item.trace,
        }
        size = len(json.dumps(record, ensure_ascii=False))
        if selected and used + size > max_chars:
            continue
        selected.append(record)
        used += size
        if used >= max_chars:
            break
    latest_passed = attempts[-1].passed_requirements if attempts else set()
    anchor_passed = anchor.passed_requirements if anchor else set()
    return {
        "format": "requirement-aligned-failure-certificate-v1",
        "anchor_attempt": anchor.number if anchor else None,
        "requirements_supported_by_anchor": sorted(anchor_passed),
        "requirements_supported_by_latest": sorted(latest_passed),
        "latest_regressions_against_anchor": sorted(anchor_passed - latest_passed),
        "selected_failures": selected,
        "selection_policy": [
            "safety requirement first",
            "blocking syntax/interface evidence first",
            "new signature before repeated signature",
            "shorter trace first",
        ],
        "character_budget": max_chars,
    }


def build_evidence_certificate_v2(
    attempts: list[AttemptOutcome],
    anchor: AttemptOutcome | None,
    critical_ids: set[str],
    max_chars: int,
) -> dict:
    """Build a deduplicated state-and-delta certificate under a fixed budget."""
    evidence = [item for attempt in attempts for item in attempt.failing_evidence]
    frequencies = Counter(item.signature for item in evidence)
    # The most recent representative has the newest trace while frequency keeps
    # the complete history of repeated failures.
    representative = {item.signature: item for item in evidence}
    ordered = sorted(
        representative.values(),
        key=lambda value: _evidence_priority(value, critical_ids, frequencies),
    )
    selected = []
    used = 0
    for item in ordered:
        record = {
            "tool": item.tool,
            "kind": item.kind,
            "requirement_ids": list(item.requirement_ids),
            "summary": item.summary,
            "oracle_status": item.oracle_status,
            "signature": item.signature,
            "seen_count": frequencies[item.signature],
            "trace": item.trace,
        }
        size = len(json.dumps(record, ensure_ascii=False))
        if selected and used + size > max_chars:
            continue
        selected.append(record)
        used += size
        if used >= max_chars:
            break

    latest_passed = attempts[-1].passed_requirements if attempts else set()
    anchor_passed = anchor.passed_requirements if anchor else set()
    directives = []
    if any(item["seen_count"] >= 2 for item in selected):
        directives.append(
            "A failure signature repeated: do not submit the same local repair; re-derive the affected state/update order."
        )
    kinds = {item["kind"] for item in selected}
    if "openplc_functional_failure" in kinds or "test_failure" in kinds:
        directives.append(
            "Replay the reported input scan and compare expected with observed post-scan outputs before editing."
        )
    if "formal_counterexample" in kinds:
        directives.append(
            "Trace retained state and output assignment order through the counterexample; internal state and output may differ within one scan."
        )
    if kinds & {"compile_error", "interface_error", "response_format"}:
        directives.append("Repair the blocking format or compilation defect before changing functional behavior.")

    return {
        "format": "requirement-aligned-failure-certificate-v2",
        "anchor_attempt": anchor.number if anchor else None,
        "requirements_supported_by_anchor": sorted(anchor_passed),
        "requirements_supported_by_latest": sorted(latest_passed),
        "latest_regressions_against_anchor": sorted(anchor_passed - latest_passed),
        "attempt_history": [
            {
                "attempt": attempt.number,
                "repair_mode": attempt.repair_mode,
                "anchor_attempt": attempt.anchor_attempt,
                "hypothesis": attempt.candidate.hypothesis,
                "target_requirements": list(attempt.candidate.target_requirement_ids),
                "supported_requirements": sorted(attempt.passed_requirements),
                "failure_signatures": sorted({item.signature for item in attempt.failing_evidence}),
            }
            for attempt in attempts
        ],
        "selected_failures": selected,
        "repair_directives": directives,
        "selection_policy": [
            "one newest representative per failure signature",
            "safety requirement first",
            "blocking syntax/interface evidence first",
            "new signature before repeated signature",
            "shorter trace first",
        ],
        "character_budget": max_chars,
        "selected_failure_characters": used,
    }


def build_raw_feedback(attempts: list[AttemptOutcome], max_chars: int) -> dict:
    if not attempts:
        return {"format": "raw-latest-diagnostics-v1", "text": "No previous attempt."}
    latest = attempts[-1]
    text = "\n".join(
        f"[{gate.name}/{gate.status}] {gate.summary}\n"
        + "\n".join(item.summary for item in gate.evidence)
        for gate in latest.gates
    )
    return {"format": "raw-latest-diagnostics-v1", "text": text[:max_chars]}

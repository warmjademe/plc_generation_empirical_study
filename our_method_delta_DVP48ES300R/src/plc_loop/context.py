"""Deterministic, bounded task-state context and IEC-pattern retrieval."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .dataset import TaskPackage
from .models import AttemptOutcome


def derive_contract_risk_obligations(task: TaskPackage) -> list[dict[str, Any]]:
    """Compile public requirement wording into bounded, requirement-specific checks.

    This is deliberately lexical and deterministic: it never reads the reference
    implementation, test vectors, or formal-property file.  The obligations do
    not claim to prove a requirement.  They tell the synthesizer which scan-level
    distinctions must be made explicit before it emits code.
    """
    obligations: list[dict[str, Any]] = []
    for requirement in task.metadata.get("requirements", []):
        requirement_id = str(requirement.get("id", ""))
        text = str(requirement.get("text", ""))
        lowered = text.casefold()
        risks: list[str] = []
        checks: list[str] = []

        if any(token in lowered for token in ("without ", "unless ", "otherwise", " even when")):
            risks.append("contrastive_exception")
            checks.append(
                "Evaluate both the named condition and its complement; an exception branch must not accidentally reuse the normal-branch guard or result."
            )
        if any(token in lowered for token in ("only when", "may clear only", "may latch only", "only while")):
            risks.append("guarded_transition")
            checks.append(
                "Enumerate the complete allowed guard and at least one disallowed near-miss; a failed guard must preserve retained state."
            )
        if any(token in lowered for token in ("pulse", "one-scan", "one scan")):
            risks.append("one_scan_pulse")
            checks.append(
                "Default the pulse FALSE every scan, then distinguish a state already active at scan start from that state being newly set in this scan; use the wording and priority order to choose the trigger."
            )
        if any(token in lowered for token in ("priority", "same scan", "dominant", "even when")):
            risks.append("simultaneous_priority")
            checks.append(
                "Trace simultaneous high- and low-priority inputs through one mutually exclusive transition order and confirm the lower-priority branch cannot overwrite the result."
            )
        if any(token in lowered for token in ("latch", "latched", "remain", "until", "once set", "restart inhibit")):
            risks.append("retained_lifecycle")
            checks.append(
                "List set, guarded clear, isolation, and hold transitions separately; do not implement a retained state as an output that is recomputed away."
            )
        if any(token in lowered for token in ("exactly", "equivalent")):
            risks.append("bidirectional_equivalence")
            checks.append(
                "Check both directions of the equivalence, including the all-FALSE/default case."
            )
        if any(token in lowered for token in ("edge", "new ", "re-enabl", "released")):
            risks.append("pre_post_scan_state")
            checks.append(
                "Snapshot any required previous value before assignments and update edge memory only after all decisions for the scan."
            )
        if any(token in lowered for token in ("capacity", "boundary", "bounded", "clamp", "within zero", "minimum", "maximum")):
            risks.append("numeric_boundary")
            checks.append(
                "Check zero, the declared lower and upper bounds, and the exact boundary equality. Apply only behavior defined inside the public assumptions; do not invent semantics for excluded inputs."
            )
        if any(token in lowered for token in (" ms", "timeout", "completing", "completed window", "items shall", "threshold")):
            risks.append("threshold_crossing")
            checks.append(
                "Compute the tentative post-scan counter/time value before comparing the threshold; identify whether completion occurs on the Nth qualifying scan and when the counter is reset."
            )

        if risks:
            obligations.append({
                "requirement_id": requirement_id,
                "safety_critical": bool(requirement.get("safety_critical")),
                "risk_types": risks,
                "checks": checks,
            })
    return obligations


def _keyword_score(text: str, card: dict[str, Any]) -> float:
    lowered = text.casefold()
    matches = sum(1 for keyword in card.get("keywords", []) if str(keyword).casefold() in lowered)
    return matches * float(card.get("retrieval_weight", 1.0))


def load_pattern_cards(path: Path) -> list[dict[str, Any]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    cards = document.get("cards")
    if not isinstance(cards, list) or not cards:
        raise ValueError(f"IEC pattern library is empty: {path}")
    ids = [str(card.get("id")) for card in cards]
    if len(ids) != len(set(ids)):
        raise ValueError("IEC pattern-card IDs must be unique")
    return cards


def retrieve_pattern_cards(
    task: TaskPackage,
    cards: list[dict[str, Any]],
    *,
    max_cards: int,
) -> list[dict[str, Any]]:
    query = f"{task.requirement_text}\n{task.interface_text}"
    always = [card for card in cards if card.get("always") is True]
    ranked = sorted(
        (
            (_keyword_score(query, card), str(card["id"]), card)
            for card in cards
            if card.get("always") is not True
        ),
        key=lambda item: (-item[0], item[1]),
    )
    selected = list(always)
    selected.extend(card for score, _, card in ranked if score > 0)
    return selected[:max_cards]


def build_task_state(
    task: TaskPackage,
    attempts: list[AttemptOutcome],
    anchor: AttemptOutcome | None,
    mode: str,
    cards: list[dict[str, Any]],
    *,
    max_cards: int = 4,
    max_chars: int = 5000,
    include_pre_emit_review: bool = False,
    include_contract_risks: bool = False,
    diversification_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    all_ids = sorted(task.requirement_ids)
    support_attempts = {
        requirement_id: [attempt.number for attempt in attempts if requirement_id in attempt.passed_requirements]
        for requirement_id in all_ids
    }
    latest_failures: dict[str, list[str]] = {requirement_id: [] for requirement_id in all_ids}
    if attempts:
        for item in attempts[-1].failing_evidence:
            for requirement_id in item.requirement_ids:
                if requirement_id in latest_failures:
                    latest_failures[requirement_id].append(item.signature)
    anchor_supported = anchor.passed_requirements if anchor else set()
    latest_supported = attempts[-1].passed_requirements if attempts else set()
    historically_supported = {
        requirement_id
        for attempt in attempts
        for requirement_id in attempt.passed_requirements
    }
    requirement_state = []
    for requirement_id in all_ids:
        if latest_failures[requirement_id]:
            status = "failing"
        elif requirement_id in latest_supported:
            status = "supported_by_visible_evidence"
        elif support_attempts[requirement_id]:
            status = "previously_supported_not_currently_observed"
        else:
            status = "not_yet_supported"
        requirement_state.append({
            "id": requirement_id,
            "safety_critical": requirement_id in task.critical_requirement_ids,
            "status": status,
            "support_attempts": support_attempts[requirement_id],
            "latest_failure_signatures": latest_failures[requirement_id],
        })

    retrieved = retrieve_pattern_cards(task, cards, max_cards=max_cards)
    packet = {
        "format": "bounded-agent-state-v3" if include_contract_risks else "bounded-agent-state-v2",
        "repair_mode": mode,
        "scan_model": task.metadata.get("scan", {}),
        "anchor_attempt": anchor.number if anchor else None,
        "do_not_regress": sorted(anchor_supported),
        "historically_supported_requirements": sorted(historically_supported),
        "requirements_without_current_visible_support": sorted(
            set(all_ids) - latest_supported
        ),
        "latest_regressions": sorted(anchor_supported - latest_supported),
        "requirement_state": requirement_state,
        "retrieved_pattern_cards": [
            {"id": card["id"], "guidance": card.get("guidance", [])}
            for card in retrieved
        ],
    }
    if include_contract_risks:
        packet["public_contract_risk_obligations"] = derive_contract_risk_obligations(task)
    if diversification_profile is not None:
        packet["public_diversification_profile"] = diversification_profile
    if include_pre_emit_review:
        packet["private_pre_emit_review"] = [
            "Map every public requirement to an assignment or retained-state transition in the candidate.",
            "Simulate a fresh instance and at least one nominal, reset, simultaneous-priority, held-input, and boundary scan.",
            "Check post-scan outputs after sequential ST assignments, including same-scan latch changes.",
            "For each requirement without current visible support, inspect the code directly rather than assuming it is covered.",
            "Emit the candidate only; do not expose this private review in the response.",
        ]
    encoded = json.dumps(packet, ensure_ascii=False, sort_keys=True)
    if len(encoded) <= max_chars:
        return packet
    packet["context_truncated"] = True
    packet["character_budget"] = max_chars
    # Preserve state and progressively drop the least-relevant retrieved cards.
    while packet["retrieved_pattern_cards"] and len(
        json.dumps(packet, ensure_ascii=False, sort_keys=True)
    ) > max_chars:
        packet["retrieved_pattern_cards"].pop()
    # Risk obligations are ordered by public requirement ID.  If an unusually
    # large contract still exceeds the packet budget, retain safety-critical
    # obligations before non-critical ones and then trim from the tail.
    risks = packet.get("public_contract_risk_obligations")
    if isinstance(risks, list):
        risks.sort(key=lambda item: (not item.get("safety_critical", False), item.get("requirement_id", "")))
        while risks and len(json.dumps(packet, ensure_ascii=False, sort_keys=True)) > max_chars:
            risks.pop()
    # Empty evidence arrays dominate initial packets with many requirements but
    # carry no information.  Remove only empty fields; keep every requirement's
    # ID, criticality, and status.
    for item in packet["requirement_state"]:
        if not item.get("support_attempts"):
            item.pop("support_attempts", None)
        if not item.get("latest_failure_signatures"):
            item.pop("latest_failure_signatures", None)
    if len(json.dumps(packet, ensure_ascii=False, sort_keys=True)) > max_chars:
        review = packet.get("private_pre_emit_review")
        if isinstance(review, list):
            del review[2:]
    if len(json.dumps(packet, ensure_ascii=False, sort_keys=True)) > max_chars:
        packet.pop("historically_supported_requirements", None)
        packet.pop("latest_regressions", None)
    if len(json.dumps(packet, ensure_ascii=False, sort_keys=True)) > max_chars:
        # A very small configured budget cannot carry per-requirement history.
        # Keep the current categorical state rather than silently exceeding it.
        packet["requirement_state"] = [
            {
                "id": item["id"],
                "safety_critical": item["safety_critical"],
                "status": item["status"],
            }
            for item in packet["requirement_state"]
        ]
    if len(json.dumps(packet, ensure_ascii=False, sort_keys=True)) > max_chars:
        packet.pop("private_pre_emit_review", None)
    if len(json.dumps(packet, ensure_ascii=False, sort_keys=True)) > max_chars:
        raise ValueError(
            f"task-state budget {max_chars} is too small for the minimal public state packet"
        )
    return packet

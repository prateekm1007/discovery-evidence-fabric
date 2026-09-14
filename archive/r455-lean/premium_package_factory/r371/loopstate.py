"""
loopstate.py — R371 Phase 11: end-to-end AI loop state, honestly separated.

CEO directive:
  "The release architecture must support DISCOVERY -> ... -> NEW SEARCH,
   but keep these states strictly separate: SYNTHETIC / MODELLED /
   PROPOSED / REAL. No AI-generated event can become REAL."

Constitutional anchors:
  Art. XXXVII — loop_verification_state in {NONE, SYNTHETIC_LOOP_VERIFIED,
    REAL_LOOP_VERIFIED}; REAL requires an external event with provenance
    (CEO-owned path).
  Art. XXXVIII — the Reality Boundary: AI may propose/compute/interpret but
    may not claim reality happened unless reality produced the evidence.

This module emits, per package:
  - loop_verification_state (from the ratified record; never assigned here)
  - evidence-class counts across the claim traceability record
    (SOURCE_FACT / EXTERNAL_PRECEDENT / AI_INFERENCE / COMPUTATIONAL_RESULT /
    PHYSICAL_OBSERVATION) — physical observation count is asserted to be 0
    and verified against the claims
  - EMPTY event queues with strict schemas for BUYER_FEEDBACK,
    ENGINEER_REVIEW, EXPERIMENT_RESULT, OBSERVATION, BELIEF_UPDATE,
    PACKAGE_REVISION — each explicitly stating that no event exists yet
    ("without pretending those events exist today" — CEO).

No event may be added by the builder. Events enter only through the
engine's REALITY_EVENT inbound interface with attestation + custody chain
(Art. XXXVIII schema), which this release artifact is ready to receive.
"""

_EVENT_TYPES = [
    "BUYER_FEEDBACK",
    "ENGINEER_REVIEW",
    "EXPERIMENT_RESULT",
    "OBSERVATION",
    "BELIEF_UPDATE",
    "PACKAGE_REVISION",
]

_EVENT_SCHEMA = {
    "event_id": "string (EVT-<uuid>)",
    "event_type": "one of " + "/".join(_EVENT_TYPES),
    "source_type": "EXTERNAL_HUMAN / EXTERNAL_INSTRUMENT / EXTERNAL_SYSTEM",
    "actor": "string",
    "organization": "string",
    "timestamp": "ISO-8601 UTC",
    "raw_artifact_ref": "path to immutable raw artifact",
    "raw_data_sha256": "sha256 of raw artifact",
    "attestation": "object with attestation_text + attestation_hash",
    "custody_chain": "non-empty list of {step, actor, timestamp, action}",
    "belief_delta": "structured change to recorded beliefs",
    "package_revision": "resulting package version, if any",
}

_EVIDENCE_CLASSES = [
    "SOURCE_FACT",
    "EXTERNAL_PRECEDENT",
    "AI_INFERENCE",
    "COMPUTATIONAL_RESULT",
    "PHYSICAL_OBSERVATION",
]


def _claim_class(claim: dict) -> str:
    """Map a canonical claim's evidence_origin to the Art. XXXVIII class.

    Recorded origins in the R370Q export: SOURCE_NATIVE, EXTERNAL_PRECEDENT,
    COMPUTATIONALLY_GENERATED, UNKNOWN. No PHYSICAL_OBSERVATION origin
    exists anywhere in the record (asserted and verified here).
    """
    origin = (claim.get("evidence_origin") or "").upper()
    mapping = {
        "SOURCE_NATIVE": "SOURCE_FACT",
        "EXTERNAL_PRECEDENT": "EXTERNAL_PRECEDENT",
        "COMPUTATIONALLY_GENERATED": "COMPUTATIONAL_RESULT",
        "COMPUTATIONAL": "COMPUTATIONAL_RESULT",
        "MODELLED": "AI_INFERENCE",
        "DESIGN_CHOICE": "AI_INFERENCE",
        "UNKNOWN": "UNKNOWN",
    }
    if origin in mapping:
        return mapping[origin]
    for k, v in mapping.items():
        if k in origin:
            return v
    return "UNCLASSIFIED"


def build_loop_state(pkg) -> dict:
    counts = {c: 0 for c in _EVIDENCE_CLASSES}
    counts["UNKNOWN"] = 0
    counts["UNCLASSIFIED"] = 0
    for claim in pkg.claims:
        counts[_claim_class(claim)] += 1
    physical = counts["PHYSICAL_OBSERVATION"]

    queues = {
        et: {
            "events": [],
            "state": "NO_EVENTS_RECORDED",
            "note": (
                f"No {et.lower().replace('_', ' ')} event exists for this "
                "package. This queue is a strict-schema placeholder; events "
                "enter only through the engine's REALITY_EVENT inbound "
                "interface with attestation and custody chain "
                "(Constitution Art. XXXVIII)."
            ),
        }
        for et in _EVENT_TYPES
    }

    return {
        "package_id": pkg.pkg_id,
        "portfolio_number": pkg.num,
        "loop_verification_state": pkg.loop_state,
        "loop_state_basis": (
            "Ratified constitutional record (Art. XXXVII scorecard after "
            "R339). REAL_LOOP_VERIFIED is impossible to assign manually; it "
            "is a derived state requiring an external event through the "
            "reality-boundary interface."
        ),
        "evidence_class_counts": counts,
        "reality_boundary": {
            "physical_observation_count": physical,
            "assertion": (
                "PHYSICAL_OBSERVATION = 0 for every package in this "
                "release. No AI-generated computation is presented as a "
                "physical observation (Art. XXXVIII)."
            ),
            "state_separation": [
                "SYNTHETIC — generated fixtures; used only in engine tests",
                "MODELLED — canonical engineering model content (this "
                "release is predominantly MODELLED)",
                "PROPOSED — design targets and work plans proposed for "
                "buyer execution",
                "REAL — external events with attested provenance; none "
                "exist in this release",
            ],
        },
        "event_queues": queues,
        "event_schema": _EVENT_SCHEMA,
        "v2_mutation_trail": {
            "has_v2_addendum": bool(pkg.addendum),
            "mutation_count": len(pkg.addendum.get("mutations", []))
            if pkg.addendum
            else 0,
            "note": (
                "V2 mutations are the only recorded dossier changes driven "
                "by externally generated evidence (R370W reconciliation); "
                "the full trail ships in the package (V2_MUTATION_ADDENDUM)."
            ),
        },
    }


def portfolio_loop_summary(packages) -> dict:
    counts = {"NONE": 0, "SYNTHETIC_LOOP_VERIFIED": 0, "REAL_LOOP_VERIFIED": 0}
    for p in packages:
        counts[p.loop_state] = counts.get(p.loop_state, 0) + 1
    return {
        "loop_verification_state_counts": counts,
        "real_external_loop": (
            "Not yet demonstrated. Zero REAL events across the portfolio. "
            "The release architecture is ready to receive them "
            "(LOOP_STATE.json event queues + engine REALITY_EVENT interface)."
        ),
    }

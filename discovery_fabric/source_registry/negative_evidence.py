"""NEGATIVE-EVIDENCE ARCHITECTURE — CEO directive 2026-08-30 #5.

> Toscanini needs to know not only "What has been proposed?" but
> "What was tried and failed?"

Failure/negative evidence becomes FIRST-CLASS: recalls, adverse events,
failed/terminated trials, incident reports — each classified, each with
its epistemic limits attached (the MAUDE-not-ground-truth principle,
generalized to every failure source).

Classification is DETERMINISTIC from record fields (Art. II):
- RECALL_EVENT            — recall/adverse-recall campaign records
- ADVERSE_EVENT_SIGNAL    — adverse-event report records (signal, never
                            incidence — Art. XXI.5 generalized)
- TERMINATED_TRIAL        — clinical trial with overall_status in
                            TERMINATED/ WITHDRAWN/ SUSPENDED
- COMPLETED_NO_RESULTS    — completed past primary completion date with
                            no results posted (publication-bias signal;
                            SOFT class, disclosed as inference-from-absence
                            which is NOT evidence of failure by itself)
- INCIDENT_REPORT         — investigation/incident records (transport,
                            industrial, aerospace — NTSB-class sources)
- NONE                    — not a negative-evidence record

Every classified record carries:
- evidence_class + failure_domain
- limitations: the structural epistemic caps for that class
- provenance: source, record id, payload hash (already in custody)

NO record is EVER classified by keyword vibes: classes derive from
structured fields (overall_status, campaign number presence, report
type). If the fields are absent, class is NONE, not guessed (Art. XXV).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Class definitions
# ---------------------------------------------------------------------------

NEGATIVE_EVIDENCE_CLASSES = {
    "RECALL_EVENT": (
        "Regulatory recall campaign — an acknowledged defect exists. NOT "
        "an incidence or field-failure rate; affected-unit counts are not "
        "failure counts."
    ),
    "ADVERSE_EVENT_SIGNAL": (
        "Adverse-event report — a reporting-system signal. Causality "
        "unverified; duplicates/bias/incompleteness documented by the "
        "regulator (FDA's MAUDE warning, generalized to every reporting "
        "system). NEVER an incidence estimate (Art. XXI.5)."
    ),
    "TERMINATED_TRIAL": (
        "Trial stopped before completion (terminated/withdrawn/suspended) "
        "— a negative outcome signal with reason text where the registry "
        "provides it. Absence of a reason is unknown, not 'no reason'."
    ),
    "COMPLETED_NO_RESULTS": (
        "Trial marked completed with no posted results — a publication- "
        "and reporting-bias SIGNAL ONLY. This is inference from absence "
        "and must never be cited as evidence the intervention failed."
    ),
    "INCIDENT_REPORT": (
        "Investigated incident — a documented failure event with "
        "investigation-grade root cause where the investigator published "
        "one. Domain-limited to the investigating authority's "
        "jurisdiction."
    ),
}

_TRIAL_NEGATIVE_STATUSES = {
    "TERMINATED", "WITHDRAWN", "SUSPENDED",
    "NO LONGER AVAILABLE", "TEMPORARILLY NOT AVAILABLE",
}

CLASS_LIMITATIONS = {
    "RECALL_EVENT": [
        "ACKNOWLEDGED_DEFECT_SEMANTICS: recall = defect acknowledged, not "
        "quantified",
        "INCIDENCE_UNKNOWN: field-failure rates are not derivable",
    ],
    "ADVERSE_EVENT_SIGNAL": [
        "SIGNAL_NOT_INCIDENCE",
        "CAUSALITY_UNVERIFIED",
        "DUPLICATES_POSSIBLE",
        "REPORTING_BIAS",
    ],
    "TERMINATED_TRIAL": [
        "STOP_REASON_QUALITY_VARIES: registry free-text, may be "
        "administrative rather than efficacy-driven",
        "NEGATIVE_SIGNAL_NOT_PROOF: termination is not proof the "
        "intervention failed",
    ],
    "COMPLETED_NO_RESULTS": [
        "INFERENCE_FROM_ABSENCE: no posted results is NOT evidence of "
        "failure or success; reporting lag is a live alternative "
        "explanation",
    ],
    "INCIDENT_REPORT": [
        "JURISDICTION_LIMITED",
        "INVESTIGATOR_DEPENDENT_DEPTH",
    ],
}


def classify_negative_evidence(record: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic classification from structured fields only."""
    norm = record.get("normalized") or {}
    sid = (record.get("source_id") or record.get("source") or "").lower()
    role = (record.get("role") or "").upper()
    limits_meta = record.get("limitations") or []

    cls: Optional[str] = None
    domain: Optional[str] = None

    # --- incident / recall / adverse-event classes by structure ---------
    if norm.get("nhtsa_campaign_number") or "nhtsa" in sid:
        cls, domain = "RECALL_EVENT", "transport"
    elif norm.get("recall_event_id") or (
            role == "RECALL" and ("fda" in sid)):
        cls, domain = "RECALL_EVENT", "medical"
    elif role == "ADVERSE_EVENT" or "maude" in sid:
        cls, domain = "ADVERSE_EVENT_SIGNAL", "medical"
    elif norm.get("incident_id") or "ntsb" in sid:
        cls, domain = "INCIDENT_REPORT", "transport"

    # --- trial classes by overall_status ---------------------------------
    status = norm.get("overall_status")
    if status:
        s = str(status).upper()
        if s in _TRIAL_NEGATIVE_STATUSES:
            cls, domain = "TERMINATED_TRIAL", "medical"
        elif cls is None:
            # completed-but-no-results heuristic must be explicit and soft
            cls, domain = _maybe_completed_no_results(norm), "medical"

    if cls is None:
        return {"evidence_class": "NONE",
                "failure_domain": None,
                "limitations": [],
                "why_not": "no structured negative-evidence fields present"}

    out = {
        "evidence_class": cls,
        "failure_domain": domain,
        "class_definition": NEGATIVE_EVIDENCE_CLASSES[cls],
        "limitations": list(CLASS_LIMITATIONS[cls]),
        "stop_reason": norm.get("why_stopped"),
    }
    # source-native limitations travel too (e.g. MAUDE_LIMITATIONS)
    if limits_meta:
        out["source_limitations"] = limits_meta
    return out


def _maybe_completed_no_results(norm: Dict[str, Any]) -> Optional[str]:
    """COMPLETED_NO_RESULTS requires BOTH structured markers:
    status COMPLETED *and* the registry's no-results flag/absence we can
    see locally. With only status visible we return None — the class is
    assigned only when the connector exposes results-posting fields."""
    if str(norm.get("overall_status", "")).upper() != "COMPLETED":
        return None
    if norm.get("results_posted") is False:
        return "COMPLETED_NO_RESULTS"
    return None


def build_negative_evidence_view(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate view over an evidence set: what was tried and failed,
    by class and domain, with unresolved counts disclosed."""
    by_class: Dict[str, List[Dict[str, Any]]] = {}
    n_none = 0
    for rec in records:
        cls = classify_negative_evidence(rec)
        if cls["evidence_class"] == "NONE":
            n_none += 1
            continue
        by_class.setdefault(cls["evidence_class"], []).append({
            "source_id": rec.get("source_id") or rec.get("source"),
            "record_id": rec.get("record_id") or rec.get("id"),
            "raw_payload_sha256": rec.get("raw_payload_sha256")
            or rec.get("content_hash"),
            "failure_domain": cls["failure_domain"],
            "stop_reason": cls.get("stop_reason"),
            "limitations": cls["limitations"],
        })
    domains = sorted({e["failure_domain"]
                      for entries in by_class.values() for e in entries
                      if e["failure_domain"]})
    return {
        "artifact": "NEGATIVE_EVIDENCE_VIEW",
        "negative_records": sum(len(v) for v in by_class.values()),
        "non_negative_records": n_none,
        "by_class": {k: len(v) for k, v in sorted(by_class.items())},
        "by_domain": {d: sum(1 for v in by_class.values() for e in v
                             if e["failure_domain"] == d) for d in domains},
        "entries": by_class,
        "policy": ("negative evidence is FIRST-CLASS but epistemically "
                   "capped: signals, acknowledged defects, and terminations "
                   "are never converted into incidence, causation, or "
                   "failure-rate claims (Art. XXI.5 generalized)")
    }

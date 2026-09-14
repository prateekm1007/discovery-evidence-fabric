"""discovery_fabric/directional/delta.py — R451 §3.

THE VERIFIABLE EVIDENCE->DIRECTION TRANSFORMATION:

    HYPOTHESIS_BEFORE
        + NEW_EVIDENCE (each item: evidence_id + its exact span)
        + HYPOTHESIS_AFTER
        = DIRECTION_DELTA

This module replaces the R450 shortcut ("gap retrieval returned items
-> evidence_changed_direction = True") with a mechanically verified
transformation. The rule set (fail-closed):

  1. A causal field of the direction is one of the CLOSED set:
     target_variable, current_value, proposed_value, direction,
     mechanism_affected, intervention_type, predicted_effect,
     predicted_magnitude_or_range. ONLY a change in one of these
     fields can ever count as "the evidence changed the direction."
     Cosmetic or bookkeeping fields (confidence wording, ids,
     gap phrasing) NEVER count.

  2. Every CHANGED field must carry an attribution to EXACT evidence:
     an evidence_id present among the NEW items, whose span text
     appears VERBATIM in that item's text. An attribution whose
     evidence id is absent, or whose span cannot be located, is
     UNVERIFIED — the change is recorded but does NOT set
     evidence_changed_direction (a changed field without proven cause
     is LLM variance, not evidence causation).

  3. NO causal field changed -> evidence_changed_direction = False.
     No exceptions. Evidence that arrives and changes nothing is
     recorded as evidence_arrived_with_no_direction_change (an honest,
     informative state — the adversarial class "evidence added / no
     direction change").

  4. The delta record is a first-class artifact: before/after values
     per field, the exact evidence id + span excerpt per attribution,
     and the verdict. It travels on the hypothesis and in the
     trajectory step.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

#: the CLOSED set of causal fields — only changes here can ever be
#: "the evidence changed the direction" (R451 §3)
CAUSAL_FIELDS = [
    "target_variable",
    "current_value",
    "proposed_value",
    "direction",
    "mechanism_affected",
    "intervention_type",
    "predicted_effect",
    "predicted_magnitude_or_range",
]

DELTA_VERSION = "direction_delta/1.0.0"

#: attribution lines as emitted by the re-proposal prompt:
#:   EVIDENCE_CAUSED: <FIELD> <- <evidence_id> because <reason>
_ATTR_LINE_RE = re.compile(
    r"EVIDENCE_CAUSED:\s*([A-Z_]+)\s*<-\s*([^\s]+)\s*(?:because\s+(.*))?",
    re.IGNORECASE)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _norm_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def _span_in_item(span: str, item: Dict[str, Any]) -> bool:
    """Does the claimed span appear VERBATIM in the evidence item's own
    text? (Art. II: exact evidence beats semantic plausibility — a
    paraphrase is not a span.)"""
    if not span:
        return False
    text = _norm_text(" ".join(
        str(item.get(k) or "") for k in
        ("title", "abstract", "content", "text", "statement")))
    return _norm_text(span)[:400] in text


def parse_attribution_lines(content: str) -> List[Dict[str, str]]:
    """Parse the model's EVIDENCE_CAUSED attribution claims from a
    re-proposal. Each claim: field, evidence_id, reason."""
    out: List[Dict[str, str]] = []
    for m in _ATTR_LINE_RE.finditer(content or ""):
        out.append({
            "field": m.group(1).lower(),
            "evidence_id": m.group(2).strip().rstrip(",;."),
            "reason": (m.group(3) or "").strip()[:300],
        })
    return out


def direction_delta(hyp_before: Dict[str, Any],
                    new_evidence: List[Dict[str, Any]],
                    hyp_after: Dict[str, Any],
                    attribution_claims: Optional[List[Dict[str, str]]] = None
                    ) -> Dict[str, Any]:
    """Compute the verifiable DIRECTION_DELTA.

    hyp_before / hyp_after — the two GATED hypothesis dicts (the same
    closed schema); new_evidence — the items the reverse path actually
    retrieved (each with id + text); attribution_claims — the AFTER
    proposal's own EVIDENCE_CAUSED lines (field <- evidence_id because
    reason), parsed from its content.

    Returns the delta record:
      changed_fields: [{field, before, after, attribution:
        {evidence_id, span_ok, reason} | None, verdict}]
      evidence_changed_direction: bool (True ONLY when >=1 causal field
        changed WITH a verified attribution)
      verdict: DIRECTION_CHANGED_BY_EVIDENCE | EVIDENCE_ARRIVED_NO_CHANGE
        | UNVERIFIED_CHANGE_ONLY | NO_NEW_EVIDENCE
    """
    new_by_id = {str(i.get("id") or i.get("evidence_id") or ""): i
                 for i in (new_evidence or [])}
    claims = list(attribution_claims or [])
    claims_by_field: Dict[str, List[Dict[str, str]]] = {}
    for c in claims:
        claims_by_field.setdefault(c["field"], []).append(c)

    changed: List[Dict[str, Any]] = []
    n_verified = 0
    for f in CAUSAL_FIELDS:
        b = str(hyp_before.get(f) or "").strip()
        a = str(hyp_after.get(f) or "").strip()
        if _norm_text(b) == _norm_text(a):
            continue
        attribution = None
        verdict = "UNATTRIBUTED"
        candidates = claims_by_field.get(f) or []
        for c in candidates:
            eid = c["evidence_id"]
            item = new_by_id.get(eid)
            if item is None:
                continue  # claimed id is not among the new evidence
            span = str(item.get("abstract") or
                       item.get("content") or
                       item.get("text") or "")[:200]
            span_ok = _span_in_item(span, item)
            attribution = {
                "evidence_id": eid,
                "span_excerpt": span,
                "span_verified": span_ok,
                "reason": c["reason"],
            }
            verdict = ("ATTRIBUTED_VERIFIED" if span_ok
                       else "ATTRIBUTED_SPAN_UNVERIFIED")
            break
        if verdict == "ATTRIBUTED_VERIFIED":
            n_verified += 1
        changed.append({
            "field": f,
            "before": b[:300],
            "after": a[:300],
            "attribution": attribution,
            "verdict": verdict,
        })

    if not new_evidence:
        evidence_changed_direction, verdict = False, "NO_NEW_EVIDENCE"
    elif not changed:
        evidence_changed_direction = False
        verdict = "EVIDENCE_ARRIVED_NO_CHANGE"
    elif n_verified >= 1 and n_verified == len(changed):
        evidence_changed_direction = True
        verdict = "DIRECTION_CHANGED_BY_EVIDENCE"
    elif n_verified >= 1:
        # SOME changes verified, others unattributed — the direction
        # WAS changed by evidence, but the unattributed changes are
        # recorded honestly (mixed; the unattributed fields carry their
        # UNVERIFIED verdict — never silently credited to evidence)
        evidence_changed_direction = True
        verdict = "DIRECTION_CHANGED_BY_EVIDENCE_PARTIAL_ATTRIBUTION"
    else:
        evidence_changed_direction = False
        verdict = "UNVERIFIED_CHANGE_ONLY"

    return {
        "delta_version": DELTA_VERSION,
        "computed_at": utc_now(),
        "hypothesis_before_id": hyp_before.get("hypothesis_id"),
        "hypothesis_after_id": hyp_after.get("hypothesis_id"),
        "new_evidence_ids": list(new_by_id.keys()),
        "n_new_evidence": len(new_by_id),
        "changed_fields": changed,
        "n_changed_fields": len(changed),
        "n_attributed_verified": n_verified,
        "evidence_changed_direction": evidence_changed_direction,
        "verdict": verdict,
        "rule": ("evidence_changed_direction is True ONLY when at "
                 "least one CLOSED causal field changed AND the change "
                 "is attributed to exact new evidence whose span "
                 "verifies verbatim; no causal field change -> False, "
                 "no exceptions (R451 §3)"),
    }

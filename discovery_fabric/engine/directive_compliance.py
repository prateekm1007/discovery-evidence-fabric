"""discovery_fabric/engine/directive_compliance.py — R470: the steering
directive-COMPLIANCE instrument (the external re-audit's P0-5 remainder).

The re-audit's measured complaint (production-verified, 2026-09-15): a
steered child round received the directive verbatim, adopted it in the
INTERVENTION, but its dominant MECHANISM identity stayed inside the
explicitly forbidden territory — and the typed directive_outcome card
computed "changed" by string inequality, so it reported success while
the directive's exclusion was violated. Two fixes were demanded:

  (POWER)  the parent's recorded mechanism identity is EXCLUDED from
           the child's mechanism search when the directive says
           "different" — the constraint rides the problem into the
           SYNTHESIZE prompt and a mechanical post-parse check;
  (SEMANTICS) the outcome compares against the DIRECTIVE (compliance),
           not just the parent (change).

This module is the ONE compliance implementation (Art. X): the engine
layer (a2/synthesize.py) and the product layer (worker.py) both import
it. It lives in the engine because the dependency direction is engine
<- product, never the reverse.

DESIGN (declared, Art. XXV):
- The forbidden referent is the PARENT's recorded mechanism identity
  (envelope_SYNTHESIZE.mechanism_map.mechanism) — the record-derived
  thing the user is steering away from when they open a CHANGE_MECHANISM
  or RESEARCH round on a completed run. Free-text directive parsing
  would be a second, fragile authority; the record is the referent.
- The mechanical check is distinctive-vocabulary containment: the
  forbidden identity's meaningful tokens (lowercased, stopwords
  stripped) vs the child mechanism's tokens; the ratio of the
  forbidden vocabulary the child restates. Threshold 0.5: restating
  HALF the forbidden identity's distinctive vocabulary is the
  forbidden territory. Deliberately NOT synonym-aware — this is a
  floor on blatant re-derivation, not a semantic judge; the record
  carries both identities verbatim either way, and the adversarial
  gates judge quality independently. The check can never alter a
  verdict — it steers the search (one repair retry) and TYPES the
  outcome; nothing is hidden and nothing is fabricated.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

DIRECTIVE_COMPLIANCE_VERSION = "directive_compliance/1.0.0"

# exclusion-class action verbs: a child round opened under one of these
# carries a directive whose explicit intent is "away from the recorded
# mechanism" (the R459 action contract's steering verbs)
EXCLUSION_VERBS = frozenset({"CHANGE_MECHANISM", "RESEARCH"})

_STOPWORDS = frozenset("""
a an and are as at be been being but by can could did do does doing done
for from had has have having he her hers him his how i if in into is it
its itself may might must of on or our ours out over own same she should
so some such than that the their theirs them then there these they this
those through to too under until up use used using very was we were what
when where which while who whom why will with would you your yours
not no nor instead without within also more most much many any each
other another new using via based both all about after before between
during above below further once here there why how
""".split())

_TOKEN_RE = re.compile(r"[a-z][a-z0-9]{2,}")
# NO hyphen in the class (the engineer's pass-2 BLOCKER): a hyphenated
# identity must SPLIT into tokens, or "retrieval-augmented-generation"
# evades a forbidden "retrieval augmented generation" by orthography —
# the exact re-audit failure mode (violation reported as success).

# the distinctive-vocabulary containment ratio at which a child
# mechanism is judged to restate the forbidden identity (declared:
# 0.5 = half the forbidden identity's meaningful vocabulary; the
# declared threshold is the honest alternative to a hidden fudge)
VIOLATION_THRESHOLD = 0.5


def meaningful_terms(text: str) -> List[str]:
    """The meaningful vocabulary of a mechanism identity: lowercase
    alpha tokens of length >= 3, stopwords stripped, deduplicated in
    first-appearance order. Deterministic; no stemming, no synonyms —
    the floor, not a judge."""
    seen: List[str] = []
    for tok in _TOKEN_RE.findall(str(text or "").lower()):
        if tok in _STOPWORDS:
            continue
        if tok not in seen:
            seen.append(tok)
    return seen


def build_constraint(verb: str, directive: str,
                     forbidden_mechanism: str) -> Dict[str, Any]:
    """The typed directive-constraint record (the spawn site builds it
    from the parent's recorded identity; the worker persists it; the
    engine consumes it). No secret, no transport vocabulary."""
    return {
        "version": DIRECTIVE_COMPLIANCE_VERSION,
        "verb": str(verb or ""),
        "directive_verbatim": str(directive or "")[:500],
        "forbidden_mechanism": str(forbidden_mechanism or "")[:300],
        "forbidden_terms": meaningful_terms(forbidden_mechanism),
        "threshold": VIOLATION_THRESHOLD,
    }


def territory_violation(mechanism: str, terms: List[str],
                        threshold: float = VIOLATION_THRESHOLD) -> Dict[str, Any]:
    """The mechanical check: what fraction of the forbidden identity's
    meaningful vocabulary does the candidate mechanism restate? The
    SAME function at synthesis time (the repair decision) and at
    outcome time (the compliance verdict) — one instrument, Art. X."""
    uniq = [t for t in dict.fromkeys(terms or []) if t]
    if not uniq:
        return {"violation": False, "overlap_ratio": 0.0,
                "overlapping_terms": [], "checked_terms": 0}
    child = set(meaningful_terms(mechanism))
    overlap = [t for t in uniq if t in child]
    ratio = len(overlap) / len(uniq)
    return {
        "violation": ratio >= threshold,
        "overlap_ratio": round(ratio, 4),
        "overlapping_terms": overlap,
        "checked_terms": len(uniq),
    }


def compliance_verdict(constraint: Dict[str, Any] | None,
                       parent_mechanism: str | None,
                       child_mechanism: str | None) -> Dict[str, Any]:
    """The typed outcome verdict (record_directive_outcome consumes this;
    the UI card renders the summary). Typed classes:
      NOT_APPLICABLE            — no exclusion-class constraint on record
      NO_BASELINE               — constraint present, no parent mechanism
      NO_CHILD_MECHANISM        — the round recorded no mechanism to judge
      COMPLIED_CHANGED          — mechanism moved AND out of the territory
      MOVED_BUT_IN_TERRITORY    — mechanism moved but restates the
                                  forbidden identity (the re-audit's
                                  measured case, now honestly typed)
      NOT_COMPLIED_SAME_AS_PARENT — the same mechanism family re-derived
      CONSTRAINT_DERIVATION_FAILED — the spawn site could not derive the
                                  constraint from the parent record; the
                                  card states it (never a silent
                                  unconstrained search, the engineer's
                                  review F1)
    Honest either way; no verdict is ever softened."""
    if isinstance(constraint, dict) and \
            constraint.get("status") == "derivation_failed":
        # R470 (the engineer's review F1): a derivation failure is a
        # TYPED state, never a silent downgrade — the outcome card
        # states it instead of pretending no constraint existed.
        return {"verdict": "CONSTRAINT_DERIVATION_FAILED",
                "mechanism_changed": None, "territory": None}
    if not constraint or not constraint.get("forbidden_mechanism"):
        return {"verdict": "NOT_APPLICABLE", "mechanism_changed": None,
                "territory": None}
    if not (parent_mechanism or "").strip():
        return {"verdict": "NO_BASELINE", "mechanism_changed": None,
                "territory": None}
    if not (child_mechanism or "").strip():
        return {"verdict": "NO_CHILD_MECHANISM", "mechanism_changed": None,
                "territory": None}
    changed = (str(parent_mechanism).strip().lower()
               != str(child_mechanism).strip().lower())
    # the record's OWN declared threshold applies (the engineer's pass-2
    # F2: the threshold field is not dead code — a per-record threshold
    # must reach the check, or the declared-threshold discipline is a
    # hidden default)
    territory = territory_violation(
        child_mechanism, constraint.get("forbidden_terms") or [],
        (constraint.get("threshold") if isinstance(
            constraint.get("threshold"), (int, float))
         else VIOLATION_THRESHOLD))
    if not changed:
        verdict = "NOT_COMPLIED_SAME_AS_PARENT"
    elif territory.get("violation"):
        verdict = "MOVED_BUT_IN_TERRITORY"
    else:
        verdict = "COMPLIED_CHANGED"
    return {"verdict": verdict, "mechanism_changed": changed,
            "territory": territory}

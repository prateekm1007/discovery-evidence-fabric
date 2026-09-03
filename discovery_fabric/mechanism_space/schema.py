"""R401 Phase 7 — schemas: evidence records and mechanism candidates.

Field lists are the CEO directive's exact Phase-7 vocabulary. Everything
is a plain dict (JSON-serializable, diffable, provenance-carrying) in the
engine's house style. No scientific field may exist without provenance.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ------------------------------------------------------------------ evidence
EVIDENCE_FIELDS = (
    "source",            # provider + record id (e.g. "openalex:W123")
    "claim",             # the mechanistic claim this record makes (verbatim span)
    "observed_effect",   # what was observed (the phenomenon/effect)
    "system",            # the system studied
    "intervention",      # intervention applied, if any
    "mechanism",         # the causal account asserted (string, V0)
    "boundary_conditions",  # conditions of validity
    "constraints",       # limitations stated
    "failure_mode",      # failure mode addressed, if any
    "confidence",        # stated/derived confidence
    "provenance",        # retrieval method, timestamp, content hash
)


def evidence_record(**kw) -> Dict[str, Any]:
    missing = [f for f in ("source", "claim", "observed_effect", "mechanism",
                           "provenance") if f not in kw]
    if missing:
        raise ValueError(f"evidence record missing mandatory fields: {missing}")
    rec = {f: kw.get(f) for f in EVIDENCE_FIELDS}
    return rec


# ----------------------------------------------------------------- candidate
CANDIDATE_FIELDS = (
    "id",
    "problem",           # problem statement (held-out or fixture)
    "system",            # the engineered system the mechanism lives in
    "failure_mode",
    "mechanism_graph",   # {"nodes": [...], "edges": [...]} — the causal core
    "evidence_bundle",   # list of evidence source-ids backing the mechanism
    "constraint_set",
    "boundary_conditions",
    "predicted_effect",
    "known_failure_modes",
    "novel_design_variable",
    "testable_prediction",
    "transformation_operator",   # None for seeds; one of OPERATORS for M2+
    "derivation_trace",          # full operator audit trail
    "provenance",
    "status",                    # routing/decision state (never science)
)

OPERATORS = (
    "DIRECT_TRANSFER",
    "CROSS_DOMAIN_ANALOGY",
    "GEOMETRIC_TRANSFORMATION",
    "BOUNDARY_CONDITION_CHANGE",
    "FAILURE_PATH_INVERSION",
)

NODE_TYPES = ("COMPONENT", "PROCESS", "PHENOMENON", "MATERIAL", "GEOMETRY",
              "CONDITION", "DESIGN_VARIABLE")
EDGE_RELS = ("CAUSES", "INHIBITS", "ENABLES", "MEDIATES", "FEEDBACK")


def mechanism_candidate(**kw) -> Dict[str, Any]:
    missing = [f for f in ("id", "problem", "system", "failure_mode",
                           "mechanism_graph", "provenance") if f not in kw]
    if missing:
        raise ValueError(f"candidate missing mandatory fields: {missing}")
    cand = {f: kw.get(f) for f in CANDIDATE_FIELDS}
    return cand


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()

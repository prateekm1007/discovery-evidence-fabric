"""Evidence-driven causal evolution bridge (R449 directive Phase 9).

The desired loop:
    EVIDENCE -> MECHANISM -> CANDIDATE -> ATTACK ->
    FAILURE DIAGNOSIS ->
    WHAT EVIDENCE WOULD CHANGE THE MECHANISM? ->
    RETRIEVE -> NEW EVIDENCE -> CAUSAL DELTA -> NEW CANDIDATE

This is a knowledge-driven evolution loop — much more than
generate -> critic -> regenerate: the retrieval step is DERIVED FROM
the failure diagnosis (what mechanism assumption failed -> what
evidence would test or change it), and the fresh evidence enters the
generation context through the SAME additive channel as the discovery
retrieval (never a second, weaker evidence path — Art. IV).

Constitutional discipline:
  Art. XLIV — the fresh evidence is a NEW versioned snapshot; the
               causal delta records which evidence items (ids) it
               consumed; nothing silently merges.
  Art. XLIII — the gap queries derive from the DIAGNOSED FAILURE and
               the problem's own terms (never a pre-seeded solution
               class).
  Art. XVIII — the generated causal delta stays AI_PROPOSED; the
               evidence citations are custody ids, and the gauntlet
               re-evaluates the child like every candidate.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from discovery_fabric.evidence_fabric import retrieve_evidence as _retrieve
from discovery_fabric.evidence_fabric.registry import license_ok

#: gap-query templates: how a diagnosed failure maps to the evidence
#: that would CHANGE the mechanism (fixed vocabulary — the derivation
#: is deterministic from the diagnosis + parent mechanism, never tuned
#: against an outcome)
_GAP_TEMPLATES = [
    "{mech_terms} failure mechanism",
    "{mech_terms} limitation",
    "{cause_terms} prevention",
    "{cause_terms} alternative approach",
]


def _distinctive_terms(text: str, cap: int = 4) -> List[str]:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    generic = set("""the and with using used that this from for into
    through between during their provides providing based approach
    system method design when where which while failure failed cause
    caused""".split())
    return [w for w in words if len(w) >= 4 and w not in generic][:cap]


def evidence_gap_queries(diagnosis: Dict[str, Any],
                         parent_mechanism: str) -> List[str]:
    """WHAT EVIDENCE WOULD CHANGE THE MECHANISM?

    Deterministic derivation from the diagnosed failure: the parent
    mechanism's distinctive terms + the diagnosed cause's distinctive
    terms, composed through the fixed gap templates. Each query is
    RECORDED with its derivation basis (the audit trail of the loop).
    """
    cause = str(diagnosis.get("cause") or "")
    mech_terms = " ".join(_distinctive_terms(parent_mechanism))
    cause_terms = " ".join(_distinctive_terms(cause) or
                           _distinctive_terms(
                               str(diagnosis.get("description") or "")))
    queries: List[str] = []
    seen = set()
    for tmpl in _GAP_TEMPLATES:
        q = tmpl.format(mech_terms=mech_terms, cause_terms=cause_terms
                        ).strip()
        q = re.sub(r"\s+", " ", q).strip()
        if len(q.split()) >= 2 and q not in seen:
            seen.add(q)
            queries.append(q)
    return queries[:4]


def retrieve_evolution_evidence(
        problem: Dict[str, Any],
        diagnosis: Dict[str, Any],
        parent: Dict[str, Any],
        snapshot_version: int) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """The RETRIEVE step of the evidence-driven evolution loop.

    Returns (engine_items, record): the evidence-fabric items for the
    gap queries (same canonical EvidenceRecord normalization; the same
    relevance + license discipline), and the loop's own audit record
    (gap queries + derivation, channel states, evidence ids, snapshot
    version — Art. XLIV versioning).
    """
    mechanism = str((parent.get("architecture") or {}).get(
        "mechanism") or "")
    gap_queries = evidence_gap_queries(diagnosis, mechanism)
    items, fabric_report = _retrieve(problem,
                                     extra_queries=gap_queries[:2])
    record: Dict[str, Any] = {
        "loop_step": "EVIDENCE_DRIVEN_CAUSAL_EVOLUTION_RETRIEVAL",
        "snapshot_version": snapshot_version,
        "gap_queries": gap_queries,
        "gap_query_derivation": (
            "deterministic: parent mechanism distinctive terms + "
            "diagnosed-cause distinctive terms through the fixed "
            "gap templates (the WHAT-EVIDENCE-WOULD-CHANGE-THE-"
            "MECHANISM step; Art. XLIII — problem/diagnosis-derived, "
            "never solution-class-seeded)"),
        "fabric_version": fabric_report.get("fabric_version"),
        "retrieved_at": fabric_report.get("retrieved_at"),
        "channel_states": [
            {"source_id": c.get("source_id"), "query": c.get("query"),
             "state": c.get("state")}
            for c in fabric_report.get("channels", [])],
        "n_items": len(items),
        "evidence_ids": [i.get("id") for i in items],
        "federated": True,
        "boundary": ("NEW evidence for THIS generation (Art. XLIV: new "
                     "evidence -> new snapshot -> new freeze; never "
                     "silently merged into the parent's frozen set)"),
    }
    return items, record


def bind_causal_delta_to_evidence(
        causal_delta: Dict[str, Any],
        evidence_items: List[Dict[str, Any]],
        gap_record: Dict[str, Any]) -> Dict[str, Any]:
    """The CAUSAL DELTA <- evidence binding.

    The generated causal delta stays AI_PROPOSED (Art. XVIII); this
    binding records WHICH exact evidence items (custody ids) the
    generation consumed, so a skeptic can trace:
        evidence X -> proposition (AI-interpreted) -> causal delta ->
        new candidate architecture
    backward to the pinned span bytes. The binding NEVER edits the
    delta's content — it annotates it.
    """
    delta = dict(causal_delta or {})
    delta["evidence_binding"] = {
        "consumed_evidence_ids": [i.get("id") for i in evidence_items],
        "n_items": len(evidence_items),
        "gap_queries": gap_record.get("gap_queries"),
        "snapshot_version": gap_record.get("snapshot_version"),
        "provenance_note": (
            "the causal delta is AI_PROPOSED; the evidence ids are "
            "custody anchors (source + document + version + location + "
            "verbatim span + content hash) — the generation consumed "
            "them, and the skeptic re-verifies the spans independently "
            "(Art. III/XII); passing through this binding grants the "
            "delta NO additional epistemic authority beyond the "
            "gauntlet's own re-evaluation"),
        "sources_represented": sorted({(i.get("provenance") or {}).get(
            "provider") for i in evidence_items if i.get("provenance")}),
    }
    return delta

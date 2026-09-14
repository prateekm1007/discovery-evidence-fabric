"""Evidence-driven contradiction search (R449 directive Phase 8).

The required behavior:
    candidate mechanism
           |
    supporting evidence
    +
    contradictory evidence
           |
    mechanism survives / changes / dies

Do NOT make retrieval a support-only engine — otherwise the machine is
a confirmation machine. For every leading candidate mechanism the
fabric actively searches for evidence that would INVALIDATE it:
negation-bearing and limitation-bearing queries against the SAME
federated sources that produced the support.

Constitutional discipline:
  Art. XXI.4 — relevance adjudication applies to contradiction results
               too (a keyword collision is not a contradiction).
  Art. XXV   — ABSENCE IS NOT CONTRADICTION. Zero contradicting rows
               after a SUCCESS/EMPTY_RESULT search is
               NO_CONTRADICTING_EVIDENCE_FOUND (an absence claim for
               the queried index only), never "mechanism confirmed".
               UNKNOWN-class states are CONTRADICTION_SEARCH_UNKNOWN.
  Art. IV    — no weakening: a contradiction verdict is derived from
               the evidence states, never from convenience.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from discovery_fabric.evidence_fabric import connectors as hc
from discovery_fabric.evidence_fabric.evidence_record import (
    EvidenceRecord, build_evidence_record, utc_now,
)
from discovery_fabric.evidence_fabric.registry import (
    license_ok, production_sources,
)

#: contradiction-seeking query templates: terms that co-occur with
#: failure/limitation/negation of a mechanism in patent + abstract
#: text. Fixed vocabulary — no prompt-tuning against results (the
#: corpus is the operator's, not ours; Art. LIX spirit).
CONTRADICTION_PREFIXES = [
    "{m} failure",
    "{m} ineffective",
    "{m} limitation",
    "{m} degradation",
    "{m} problem",
]

#: the adjudication vocabulary (closed)
CONTRADICTION_VERDICTS = [
    "MECHANISM_SURVIVES",        # contradicting search returned real
                                 # contradicting evidence AND the
                                 # support still dominates on relevance
    "MECHANISM_WEAKENED",        # contradicting evidence found with
                                 # equal-or-better relevance grounding
    "MECHANISM_DIES",            # a contradicting record shares the
                                 # mechanism's own distinctive terms
                                 # (direct counter-evidence)
    "NO_CONTRADICTING_EVIDENCE_FOUND",   # successful search, zero rows
                                         # — an absence claim for the
                                         # queried index ONLY
    "CONTRADICTION_SEARCH_UNKNOWN",      # provider/index failure —
                                         # never an absence claim
]


def contradiction_queries(mechanism: str) -> List[str]:
    """Deterministic contradiction-seeking queries from the mechanism
    phrase. Mechanism terms are pruned to distinctive content words
    (>= 4 chars, non-generic) so the query targets the mechanism, not
    the sentence."""
    words = re.findall(r"[a-z0-9]+", (mechanism or "").lower())
    generic = set("""the and with using used that this from for into
    through between during their provides providing based approach
    system method design""".split())
    distinctive = [w for w in words if len(w) >= 4 and w not in generic]
    mech_phrase = " ".join(distinctive[:4])
    if not mech_phrase:
        return []
    out = []
    for tmpl in CONTRADICTION_PREFIXES:
        q = tmpl.format(m=mech_phrase).strip()
        if q:
            out.append(q)
    return out[:3]


def _adjudicate(mechanism: str, support: List[Dict[str, Any]],
                contra: List[Dict[str, Any]],
                search_states: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Derive the verdict from the measured evidence states (never from
    convenience — Art. IV). Absence of contradicting rows NEVER becomes
    support (Art. XXV)."""
    mech_terms = set(re.findall(r"[a-z0-9]{4,}", (mechanism or "").lower()))
    any_unknown = any(s.get("state") == "UNKNOWN" for s in search_states)
    any_success = any(s.get("state") in ("SUCCESS", "EMPTY_RESULT")
                      for s in search_states)
    if not any_success:
        return {"verdict": "CONTRADICTION_SEARCH_UNKNOWN",
                "basis": "every contradiction-seeking channel failed "
                         "(provider/index class) — the absence of "
                         "contradicting evidence is UNKNOWN, never "
                         "confirmation (Art. XXI.3)"}
    if not contra:
        return {"verdict": "NO_CONTRADICTING_EVIDENCE_FOUND",
                "basis": "successful searches returned zero "
                         "contradiction-adjudicated rows — an absence "
                         "claim for the queried indexes only, NOT a "
                         "novelty or validity claim (Art. XXI.2/XXV)"}
    # direct counter-evidence: a contradicting record sharing the
    # mechanism's distinctive terms
    best_overlap = 0
    best_rec = None
    for c in contra:
        terms = set(re.findall(r"[a-z0-9]{4,}",
                               str(c.get("abstract") or
                                   (c.get("evidence_fabric") or {}).get(
                                       "exact_span", {}).get("text", ""))))
        overlap = len(terms & mech_terms)
        if overlap > best_overlap:
            best_overlap, best_rec = overlap, c
    support_strength = len([s for s in support if
                            (s.get("epistemic_state") in
                             ("PENDING_CORROBORATION", "ADMITTED"))])
    contra_strength = len(contra)
    if best_overlap >= 3:
        verdict = "MECHANISM_DIES"
    elif contra_strength > support_strength:
        verdict = "MECHANISM_WEAKENED"
    else:
        verdict = "MECHANISM_SURVIVES"
    return {"verdict": verdict,
            "basis": f"contradicting rows {contra_strength} vs support "
                     f"rows {support_strength}; best term overlap "
                     f"{best_overlap}",
            "strongest_contradiction": (best_rec or {}).get("id"),
            "any_unknown_channel": any_unknown}


def search_contradictions(mechanism: str,
                          support_items: List[Dict[str, Any]],
                          per_query_limit: int = 3,
                          source_ids: Optional[List[str]] = None
                          ) -> Dict[str, Any]:
    """Contradiction search for ONE candidate mechanism.

    Returns the full contradiction record: queries, per-channel states,
    contradicting evidence items (a2-schema compatible), the verdict,
    and the recorded limitation. The caller (engine CONTRADICTION stage
    extension / the round's contradiction run) feeds this into the
    adjudication surface.
    """
    queries = contradiction_queries(mechanism)
    record: Dict[str, Any] = {
        "mechanism": mechanism,
        "queries": queries,
        "searched_at": utc_now(),
        "channels": [],
        "contradicting_evidence": [],
        "support_evidence_count": len(support_items),
        "verdict": None,
        "federated": True,
    }
    if not queries:
        record["verdict"] = "CONTRADICTION_SEARCH_UNKNOWN"
        record["basis"] = "mechanism phrase carried no distinctive terms"
        return record
    sources = production_sources()
    if source_ids:
        sources = [s for s in sources if s.get("source_id") in source_ids]
    text_sources = [s for s in sources
                    if (s.get("query_mode") or "search") == "search"
                    and license_ok(s)]
    contra_records: List[EvidenceRecord] = []
    for src in text_sources:
        for q in queries:
            rows, meta = hc.search_rows(
                src["dataset_id"], src.get("config") or "default",
                src.get("split") or "train", q,
                length=per_query_limit)
            ch = {"source_id": src["source_id"], "query": q,
                  "state": meta.get("state"),
                  "reason": meta.get("reason"),
                  "num_rows_total": meta.get("num_rows_total")}
            record["channels"].append(ch)
            if not rows:
                continue
            for r in rows:
                row_idx = int(r.get("row_idx", -1))
                row = r.get("row") or {}
                rec = build_evidence_record(
                    source=src, row=row, row_idx=row_idx,
                    text_field=src.get("text_field") or "text",
                    document_field=src.get("document_field") or "id",
                    retrieval_endpoint="search",
                    connector_state=meta.get("state", "SUCCESS"),
                    license_verified=bool(src.get("license_verified")),
                    license_basis=str(src.get("license_basis") or
                                      "UNVERIFIED"),
                    card_license=src.get("license"),
                    origin_description=str(src.get("provenance_origin")
                                           or ""),
                    retrieval_query=q)
                if rec is None:
                    continue
                # contradiction records are relevant-by-construction of
                # the query BUT still need term grounding to the
                # mechanism (Art. XXI.4 discipline)
                span_terms = set(re.findall(r"[a-z0-9]{4,}",
                                            rec.exact_span.text.lower()))
                mech_terms = set(re.findall(r"[a-z0-9]{4,}",
                                            (mechanism or "").lower()))
                overlap = span_terms & mech_terms
                if not overlap:
                    continue  # keyword collision, not a contradiction
                rec.proposition = (
                    "candidate counter-evidence for mechanism: "
                    + (mechanism or "")[:200])
                rec.mechanisms = [mechanism[:200]]
                rec.admissibility.state = "PENDING_CORROBORATION"
                rec.admissibility.reasons = [
                    "contradiction-seeking retrieval; term-grounded to "
                    "the mechanism (" + ", ".join(sorted(overlap)[:6])
                    + ")"]
                contra_records.append(rec)
    adjudication = _adjudicate(mechanism, support_items,
                               [r.to_engine_item()
                                for r in contra_records],
                               record["channels"])
    record["verdict"] = adjudication["verdict"]
    record["basis"] = adjudication.get("basis")
    record["strongest_contradiction"] = adjudication.get(
        "strongest_contradiction")
    record["contradicting_evidence"] = [
        {"id": r.evidence_id,
         "source": r.source_identity.source_id,
         "document_ref": r.exact_span.document_ref,
         "span_sha256": r.exact_span.text_sha256,
         "text": r.exact_span.text[:300],
         "shared_terms": sorted(set(
             re.findall(r"[a-z0-9]{4,}", r.exact_span.text.lower())) &
             set(re.findall(r"[a-z0-9]{4,}", (mechanism or "").lower())))[:8]}
        for r in contra_records]
    record["n_contradicting"] = len(contra_records)
    return record

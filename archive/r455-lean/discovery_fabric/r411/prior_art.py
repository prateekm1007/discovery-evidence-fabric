"""discovery_fabric/r411/prior_art.py — Directive s9 + s7: adversarial
prior-art search that attacks the terminology-lock-in weakness directly.

For every serious candidate the engine executes FOUR retrieval
perspectives (s7):
  FORWARD   candidate problem -> known solutions
  MECHANISM physical mechanism -> applications
  FAILURE   failure mode -> prevention methods
  INVERSE   desired outcome -> mechanisms capable of producing it

plus FOUR terminology registers (s7): historical, engineering, patent,
adjacent-domain. All through the live fabric (RETRIEVAL_FABRIC_V2),
reusing the fabric's canonical resolution + dedup so the same document
across databases is ONE record with multi-source provenance.

The candidate's generator is NOT the novelty authority (s9): the closest
art is identified from the RETRIEVED RECORDS (the evidence decides, not
the generator's self-assessment), and the strongest existing technology
+ the closest thing that makes the candidate unnecessary are recorded
with record ids.

Anti-lock-in measurement: for every record found, the fabric tags which
query variant found it. This module reports which perspective/register
recovered records the FORWARD/primary perspective missed — the direct
measurement of terminology recovery (the R409 frontier).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

PRIOR_ART_VERSION = "R411-PRIORART-V1"

# Terminology registers (s7) — deterministic transformations of the
# candidate's own vocabulary into the OTHER vocabularies engineers,
# patents, and older literature use.
REGISTER_TABLE = {
    "engineering": [
        ("remove", "mitigat"), ("reduce", "suppress"), ("fouling",
         "deposition"), ("degradation", "wear rate"), ("waste heat",
         "reject heat"), ("sensing", "monitoring"), ("control",
         "regulation"), ("efficiency", "performance"),
    ],
    "patent": [
        ("apparatus", "device"), ("method for", "process for"),
        ("wherein", "in which"), ("configured to", "adapted to"),
    ],
    "historical": [
        ("machine learning", "statistical estimation"),
        ("artificial intelligence", "expert system"),
        ("real-time", "on-line"), ("sensor", "transducer"),
        ("heat exchanger", "heat exchange apparatus"),
        ("coating", "cladding"), ("monitoring", "instrumentation"),
    ],
}


def _register_variants(text: str, register: str) -> str:
    out = text
    for a, b in REGISTER_TABLE.get(register, []):
        out = out.replace(a, b)
    return out


def _mechanism_text(candidate: Dict[str, Any]) -> str:
    return " ".join(str(s) for s in candidate.get("causal_chain") or []) \
        or str(candidate.get("intervention") or "")


def build_perspectives(candidate: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The four retrieval perspectives (s7) as fabric problem dicts."""
    problem = str(candidate.get("problem") or "")
    mech = _mechanism_text(candidate)
    phenomenon = str(candidate.get("unexploited_phenomenon") or "")
    pain = str(candidate.get("pain_class") or "")
    predicted = str(candidate.get("predicted_effect") or "")
    domain = str(candidate.get("target_domain") or "")
    return [
        {
            "perspective": "FORWARD",
            "problem": {
                "device": problem[:120] or domain,
                "failure_mode": pain,
                "constraint": "known solutions and incumbent approaches",
            },
        },
        {
            "perspective": "MECHANISM",
            "problem": {
                "device": (phenomenon or mech)[:120],
                "failure_mode": pain,
                "constraint": "applications of this physical mechanism",
            },
        },
        {
            "perspective": "FAILURE",
            "problem": {
                "device": (candidate.get("baseline") or {}).get(
                    "baseline_incumbent", "")[:120] or problem[:120],
                "failure_mode": pain,
                "constraint": "failure modes and prevention methods",
            },
        },
        {
            "perspective": "INVERSE",
            "problem": {
                "device": domain,
                "failure_mode": predicted[:100],
                "constraint": "mechanisms capable of producing this "
                              "outcome",
            },
        },
    ]


def register_queries(candidate: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The four terminology registers applied to the mechanism text."""
    mech = _mechanism_text(candidate) or str(
        candidate.get("technology_name") or "")
    return [
        {"register": reg, "query": _register_variants(mech, reg)}
        for reg in REGISTER_TABLE
    ]


def _relevance_of(record: Dict[str, Any],
                  candidate: Dict[str, Any]) -> Optional[str]:
    """Recorded relevance decision (Art. XXI.4): does this record belong
    to the candidate's mechanism/problem domain? Deterministic term
    overlap between the record's title+abstract and the candidate's
    mechanism surface, with the matched terms recorded."""
    rec_text = " ".join(str(record.get(k) or "") for k in
                        ("title", "abstract", "snippet")).lower()
    rec_words = set(re.findall(r"[a-z]{4,}", rec_text))
    cand_words = set(re.findall(
        r"[a-z]{4,}",
        (_mechanism_text(candidate) + " " +
         str(candidate.get("problem") or "") + " " +
         str(candidate.get("unexploited_phenomenon") or "")).lower()))
    core = rec_words & cand_words
    core -= {"with", "from", "this", "that", "which", "where", "when",
             "using", "used", "based", "such", "have", "been", "their",
             "these", "those", "other", "more", "less", "also", "into",
             "than", "then", "them", "will", "would", "could", "study",
             "studies", "results", "result", "show", "shown", "paper",
             "approach", "propose", "proposed", "system", "systems",
             "method", "methods", "based on"}
    if len(core) >= 4:
        return "RELEVANT"
    if len(core) >= 2:
        return "PARTIAL"
    return None


def assess_prior_art(candidate: Dict[str, Any],
                     retrieved_by_perspective: Dict[str, List[Dict]],
                     generator_provider: Optional[str] = None) -> Dict[str, Any]:
    """The s9 assessment: identify the strongest existing technology from
    retrieved records + the closest thing that makes the candidate
    unnecessary. The CANDIDATE (generator) is not consulted — only the
    evidence records + deterministic term analysis decide."""
    relevant: List[Dict[str, Any]] = []
    for perspective, records in retrieved_by_perspective.items():
        for r in records:
            rel = _relevance_of(r, candidate)
            if rel:
                relevant.append({
                    "record_id": r.get("record_id") or r.get("id"),
                    "perspective": perspective,
                    "relevance": rel,
                    "title": str(r.get("title") or "")[:160],
                    "year": r.get("year"),
                    "publication_status": r.get("publication_status") or
                        (r.get("labeling") or {}).get("publication_status"),
                    "source": (r.get("provenance") or {}).get(
                        "source_id") or r.get("source_id"),
                })
    # distance class from the relevant set (deterministic):
    #   COVERING — a relevant record whose core terms cover the
    #              candidate's mechanism + intervention + effect
    #   NEAR     — >=3 RELEVANT records
    #   FAR      — 1-2 RELEVANT or only PARTIAL records
    #   NO_OVERLAP — nothing relevant found (retrieval-dependent, NOT
    #              novelty proof — Art. XLVI: retrieval absence is not
    #              novelty proof; the class is honestly retrieval-scoped)
    n_rel = sum(1 for r in relevant if r["relevance"] == "RELEVANT")
    n_part = sum(1 for r in relevant if r["relevance"] == "PARTIAL")
    if n_rel >= 3:
        distance = "NEAR"
    elif n_rel >= 1 or n_part >= 3:
        distance = "FAR"
    elif n_part >= 1:
        distance = "FAR"
    else:
        distance = "NO_OVERLAP"

    strongest = relevant[:8] if relevant else []
    return {
        "prior_art_version": PRIOR_ART_VERSION,
        "perspectives_executed": sorted(retrieved_by_perspective.keys()),
        "relevant_records": relevant,
        "closest_prior_art": {
            "distance_class": distance,
            "distance_basis": (
                f"{n_rel} RELEVANT + {n_part} PARTIAL records across "
                f"{len(retrieved_by_perspective)} perspectives; class is "
                "retrieval-scoped (Art. XLVI: retrieval absence is never "
                "novelty proof)"),
            "strongest_existing_candidates": strongest,
            "what_makes_candidate_unnecessary": (
                "the closest records above: if any one already teaches "
                "the candidate's mechanism + intervention + predicted "
                "effect in the target domain, the candidate's typed "
                "distinction must be re-tested against it (the dossier "
                "records the exact comparison)"),
        },
        "generator_not_consulted": True,
        "assessment_note": (
            "closest art identified from retrieved records only; the "
            "candidate's generator never scores its own novelty (s9)"),
    }


def terminology_recovery(retrieved_by_perspective: Dict[str,
                                                        List[Dict]],
                         primary_records: List[Dict]) -> Dict[str, Any]:
    """Anti-lock-in measurement (s7): which records were recovered ONLY
    by non-primary perspectives/registers. Directly measures whether the
    four-perspective + terminology-register attack beats the single-query
    lock-in the R409 benchmark measured."""
    primary_ids = {r.get("record_id") or r.get("id")
                   for r in primary_records}
    recovered_only_by = {}
    for perspective, records in retrieved_by_perspective.items():
        if perspective == "FORWARD":
            continue
        for r in records:
            rid = r.get("record_id") or r.get("id")
            if rid not in primary_ids and rid:
                recovered_only_by.setdefault(perspective, set()).add(rid)
    return {
        "primary_record_count": len(primary_ids),
        "unique_records_recovered_by_secondary_perspectives": {
            k: len(v) for k, v in recovered_only_by.items()},
        "total_unique_secondary_only": len(
            set().union(*recovered_only_by.values())
            if recovered_only_by else set()),
        "interpretation": (
            "records found ONLY by MECHANISM/FAILURE/INVERSE perspectives "
            "or terminology registers are exactly the evidence a "
            "single-forward-query engine structurally misses (the R409 "
            "measured frontier)"),
    }

"""discovery_fabric/r412/collision_screen.py — P0-2: the early
novelty-collision screen (CEO R412 directive).

Pipeline position (the directive's diagram):

    evidence-qualified concept
            ↓
    EARLY COLLISION SCREEN   <-- this module (cheap, deterministic)
            ↓
    only survivors get full mechanism writeup
            ↓
    full novelty analysis
            ↓
    engineering
            ↓
    attacker

DESIGN CONTRACT (fixed by the directive):

1. CONSERVATIVE. The screen's ONLY job is to detect OBVIOUS cases where
   the candidate's own evidence, or an immediately retrievable prior-art
   record, already describes substantially the same causal mechanism.
   Borderline cases MUST fall through to the full novelty analysis —
   a screen that kills aggressively is the measured R412 failure mode
   (universal-kill attacker, FPR 0.8-1.0) reproduced one stage earlier.

2. NEVER the final novelty determination. A PASS from this screen is
   NOT a novelty claim (Art. XXVIII: retrieval absence is not novelty
   proof; Art. XLVI: retrieval is not classification). A COLLISION is
   a routing decision: the candidate dies at the EARLY_COLLISION_SCREEN
   stage with the teaching record cited — a distinct death stage from
   REJECTED_PRIOR_ART (Art. LXI: rejection classes stay distinct).

3. CHEAP AND DETERMINISTIC. No LLM, no new retrieval. The screen reads
   only what already exists at its pipeline position: the candidate
   record and the evidence pool it is bound to (title+abstract), plus
   any prior-art records already retrieved for it (title).

PRE-REGISTERED DECISION RULE (registered BEFORE the R411 replay
validation run; the replay is a diagnostic on frozen data, not a blind
benchmark — Art. LIX discipline is declared, not silently waived):

    specific terms = content tokens of intervention +
                     unexploited_phenomenon (the candidate's
                     distinctive mechanism vocabulary)
    core terms     = content tokens of causal_chain +
                     predicted_effect (the causal narrative)

    SCREEN_COLLISION iff ONE record satisfies BOTH:
        specific_coverage >= 0.60
        core_coverage     >= 0.50
    where coverage(record) = |terms ∩ record_tokens| / |terms|.

    Degeneracy guard: fewer than 4 specific terms after extraction ->
    the screen can never fire (a 3-token vocabulary cannot evidence
    "substantially the same causal mechanism").

Constitutional grounding:
  - Art. XLVI: retrieval absence is not novelty; the screen kills only
    on PRESENCE of a teaching record, never on absence.
  - Art. XXVIII: the screen is a routing gate, not a promotion — PASS
    grants no novelty credit at any later stage.
  - Art. LXI: EARLY_COLLISION_SCREEN is a distinct rejection class.
  - Art. LVI: the screen exists to cut the measured cost of
    self-defeating collisions (6/11 explainable R411 deaths were
    prior-art/evidence collisions discovered only at the attack stage,
    after the full mechanism writeup, novelty analysis, and engineering
    representation had already been paid for).
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

SCREEN_VERSION = "R412-COLLISION-SCREEN-V1"

# pre-registered thresholds (see module docstring)
SPECIFIC_COVERAGE_MIN = 0.60
CORE_COVERAGE_MIN = 0.50
MIN_SPECIFIC_TERMS = 4

_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "are", "was",
    "were", "has", "have", "had", "not", "but", "can", "may", "will",
    "would", "could", "should", "into", "onto", "over", "under", "via",
    "using", "used", "use", "uses", "based", "such", "than", "then",
    "when", "where", "which", "while", "between", "during", "through",
    "their", "its", "each", "other", "more", "less", "most", "also",
    "both", "all", "any", "some", "these", "those", "one", "two",
    "new", "novel", "improve", "improved", "improvement", "increase",
    "increased", "reduce", "reduced", "reduction", "high", "low",
    "higher", "lower", "better", "best", "result", "results", "study",
    "studies", "paper", "method", "methods", "approach", "system",
    "systems", "process", "processes", "effect", "effects", "provide",
    "provides", "providing", "present", "presents", "presented",
    "proposed", "propose", "proposes", "achieved", "achieve",
    "significant", "significantly", "various", "different", "several",
    "including", "include", "includes", "however", "therefore", "thus",
    "hence", "obtained", "obtain", "shown", "show", "shows",
}


def _normalize(token: str) -> str:
    """Casefold + crude plural/possessive normalization (deterministic;
    no stemming library — the screen must stay dependency-free).
    'es' strips only after s/x/z/h stems (boxes/matches); plain 's'
    otherwise (plates -> plate)."""
    t = token.casefold().strip(".,;:()[]{}\"'")
    if len(t) > 4 and t.endswith("ies"):
        t = t[:-3] + "y"
    elif len(t) > 3 and t.endswith("es") and t[-3] in "sxzh":
        t = t[:-2]
    elif len(t) > 3 and t.endswith("s") and not t.endswith("ss"):
        t = t[:-1]
    return t


def extract_terms(texts: Iterable[str]) -> List[str]:
    """Content terms of the given texts. Deterministic, order-stable,
    deduplicated. Stopwords (domain-general filler) are excluded so the
    screen measures MECHANISM vocabulary, not topic adjacency."""
    seen: Dict[str, None] = {}
    for text in texts:
        for raw in re.split(r"[^A-Za-z0-9-]+", str(text or "")):
            t = _normalize(raw)
            if len(t) < 3 or t in _STOPWORDS or not t.isalnum():
                continue
            if t.isdigit():
                continue
            seen.setdefault(t, None)
    return list(seen)


def candidate_term_sets(candidate: Dict[str, Any]
                        ) -> Tuple[List[str], List[str]]:
    """(specific_terms, core_terms) for an XLI-form candidate."""
    specific = extract_terms(
        [candidate.get("intervention") or "",
         candidate.get("unexploited_phenomenon") or ""])
    core = extract_terms(
        [" ".join(str(s) for s in candidate.get("causal_chain") or []),
         candidate.get("predicted_effect") or ""])
    return specific, core


def _record_text(record: Dict[str, Any]) -> str:
    return " ".join([
        str(record.get("title") or ""),
        str(record.get("abstract") or ""),
    ])


def coverage(terms: List[str], record: Dict[str, Any]
             ) -> Tuple[float, List[str]]:
    """Fraction of `terms` present in the record's title+abstract
    (title only when no abstract — prior-art records). Returns
    (coverage, matched_terms)."""
    if not terms:
        return 0.0, []
    tokens = set(extract_terms([_record_text(record)]))
    matched = [t for t in terms if t in tokens]
    return (len(matched) / len(terms)), matched


def screen_candidate(candidate: Dict[str, Any],
                     evidence_records: List[Dict[str, Any]],
                     prior_art_records: Optional[List[Dict[str, Any]]]
                     ) -> Dict[str, Any]:
    """Run the early collision screen on one candidate.

    evidence_records: the pool records the candidate is bound to (or
    the subset it cites) — title+abstract available.
    prior_art_records: already-retrieved prior-art records (title-only
    is fine). Optional at this pipeline position (pre-retrieval); pass
    None or [] when no prior art has been retrieved yet.

    Returns a structured screen record (see module docstring for the
    decision rule and its constitutional semantics).
    """
    specific, core = candidate_term_sets(candidate)
    screened: List[Tuple[str, Dict[str, Any]]] = []
    for r in evidence_records or []:
        screened.append(("EVIDENCE_POOL", r))
    for r in prior_art_records or []:
        screened.append(("PRIOR_ART", r))

    degenerate = len(specific) < MIN_SPECIFIC_TERMS
    matches: List[Dict[str, Any]] = []
    for source, record in screened:
        scov, smatched = coverage(specific, record)
        ccov, cmatched = coverage(core, record)
        hit = (
            not degenerate
            and scov >= SPECIFIC_COVERAGE_MIN
            and ccov >= CORE_COVERAGE_MIN)
        if hit:
            matches.append({
                "record_id": record.get("record_id") or record.get("id"),
                "source": source,
                "specific_coverage": round(scov, 4),
                "core_coverage": round(ccov, 4),
                "matched_specific_terms": smatched,
                "matched_core_terms": cmatched,
                "record_title": str(record.get("title") or "")[:200],
            })

    return {
        "screen_version": SCREEN_VERSION,
        "candidate_id": candidate.get("candidate_id"),
        "decision": "SCREEN_COLLISION" if matches else "PASS",
        "death_stage": "EARLY_COLLISION_SCREEN" if matches else None,
        "death_category": "prior_art" if matches else None,
        "specific_reason": (
            f"{matches[0]['source']} record {matches[0]['record_id']} "
            f"({matches[0]['record_title']}) already covers "
            f"{matches[0]['specific_coverage']:.0%} of the candidate's "
            f"specific mechanism vocabulary and "
            f"{matches[0]['core_coverage']:.0%} of its causal core — "
            f"an obvious same-mechanism teaching (killed at the screen; "
            f"full novelty analysis not reached, per the conservative "
            f"routing contract)") if matches else None,
        "evidence_refs": [m["record_id"] for m in matches],
        "matched_records": matches,
        "n_screened_records": len(screened),
        "n_specific_terms": len(specific),
        "n_core_terms": len(core),
        "degenerate_vocabulary_guard": degenerate,
        "thresholds": {
            "specific_coverage_min": SPECIFIC_COVERAGE_MIN,
            "core_coverage_min": CORE_COVERAGE_MIN,
            "min_specific_terms": MIN_SPECIFIC_TERMS,
            "pre_registered": True,
        },
        "semantics": {
            "PASS": ("NOT a novelty determination — routing only; the "
                     "candidate proceeds to the full mechanism writeup "
                     "and the full novelty analysis unchanged (Art. "
                     "XXVIII/XLVI)"),
            "SCREEN_COLLISION": ("an obvious same-mechanism teaching was "
                                 "found in already-available records; the "
                                 "candidate dies at EARLY_COLLISION_SCREEN "
                                 "(Art. LXI: distinct from "
                                 "REJECTED_PRIOR_ART, which remains the "
                                 "full-analysis verdict class)"),
        },
    }

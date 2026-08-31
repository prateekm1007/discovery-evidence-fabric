"""PRIOR-ART DIFFERENTIATION + RESOLUTION collision core — CEO directive
2026-08-31 (cycle R376).

> "Build a stronger multi-query prior-art search strategy around the actual
>  mechanism and distinguishing technical features — not generic
>  intervention words."
> "Require claim/mechanism-level relevance before a result can become
>  nearest prior art."
> "Search for both direct prior art and adjacent technical approaches that
>  could destroy differentiation."
> "Preserve unresolved states honestly. 'UNRESOLVED' is acceptable; falsely
>  claiming resolution is not."

MEASURED DEFECTS THIS MODULE REPLACES (TOSCANINI/PRIOR_ART_FAILURE_TRACE.json,
53 runs, weakest 20):
  F  search formulation (15/20) — 'first 6 keyword words' of a verb-first
     LLM intervention lost the technical core (CFRP knee prosthesis was
     searched as 'implement comprehensive post-market surveillance system
     using'; battery thermal runaway query contained neither 'battery' nor
     'thermal')
  B  insufficient breadth (18/20) — 1 source, 1-2 queries, <=10 hits
  E  entity/claim mismatch (17/20) — nearest prior art adjudicated against
     the QUERY string, not the candidate; 'Database access system' became
     nearest prior art for a pedicle screw candidate; grid candidates
     inherited the NAIVE candidate's collision results verbatim
  M  no family resolution (17/20) — the status vocabulary carried no
     RESOLVED state at all; resolution was structurally impossible

Constitutional anchors:
  Art. II      exact term evidence, transparent rule (no fuzzy match added)
  Art. VII     the >= 2 term-overlap rule family is UNCHANGED; this module
               EXPANDS the evidence the adjudicator sees (mechanism profile
               + abstract text), it does not lower any threshold
  Art. XXI.3   provider failure -> UNRESOLVED_*, never NO_MATCH
  Art. XXI.4   relevance adjudicated per record with recorded basis
  Art. XXV     UNKNOWN stays UNKNOWN; zero relevant hits is NOT novelty
  Art. XXVII   thresholds declared below with class + justification
  Art. XXVIII  search-derived RESOLVED_* states are SEARCH_RESULT class,
               never novelty determinations; limitation recorded inline

Deterministic: no randomness, no LLM calls in this module. All thresholds
declared in THRESHOLDS with provenance class ENGINEERING (declared before
measurement, per the instrument discipline).
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from discovery_fabric.source_registry.query_relevance import terms

# ---------------------------------------------------------------------------
# Declared thresholds (Art. XXVII — provenance, class, uncertainty, rationale)
# ---------------------------------------------------------------------------
THRESHOLDS: Dict[str, Dict[str, Any]] = {
    "MIN_MECHANISM_OVERLAP": {
        "value": 2,
        "epistemic_class": "ENGINEERING",
        "justification": (
            "same term-overlap rule family as the pipeline relevance "
            "adjudicator and the Q2 instrument (>= 2 shared content terms "
            "= domain-specific rather than accidental collision); NOT "
            "weakened relative to any prior gate"),
        "uncertainty": "term overlap is a proxy for mechanism identity",
    },
    "ANTICIPATION_COVERAGE_RATIO": {
        "value": 0.8,
        "epistemic_class": "ENGINEERING",
        "justification": (
            "a family ANTICIPATES only when nearly ALL elements of the "
            "candidate's FULL distinguishing set (uncapped — the claim "
            "elements, not the 6-term query core) appear in the family's "
            "claim/abstract text; 0.8 leaves a >= 20% element margin — "
            "anything lower would convert partial art into a kill "
            "(Art. XXVIII forbids). Measured adversarial case: a "
            "domain-only patent reached 0.857 against a capped "
            "denominator whose true differentiators (acoustic, "
            "multi-modal) had been ranked out"),
        "uncertainty": "claim coverage measured by term overlap, not a "
                       "claim chart; recorded per family with evidence tier",
    },
    "MAX_QUERY_TERMS": {
        "value": 6,
        "epistemic_class": "ENGINEERING",
        "justification": "provider-measured sweet spot for keyword patent "
                         "queries (longer queries dilute ranking)",
    },
    "ABSTRACT_TIER_MIN_CHARS": {
        "value": 80,
        "epistemic_class": "ENGINEERING",
        "justification": "below ~80 chars a snippet carries title echoes, "
                         "not mechanism description; it cannot support an "
                         "abstract-tier coverage decision",
    },
}

# Verbs/filler that open LLM-written interventions and carry no search value.
# The measured defect: position-based term selection captured these first.
_INTERVENTION_FILLER = {
    "implement", "implementing", "incorporate", "incorporating",
    "design", "designing", "develop", "developing", "apply", "applying",
    "add", "adding", "use", "using", "utilize", "utilizing", "introduce",
    "introducing", "create", "creating", "provide", "providing",
    "comprehensive", "systematic", "systematically", "novel", "improved",
    "enhanced", "enhance", "enhancing", "integrated", "multiple",
    "various", "specific", "based", "system", "method", "apparatus",
    "device", "approach", "technique", "process", "solution", "step",
    "steps", "measures", "measure", "ensure", "ensuring", "maintain",
    "maintaining", "allow", "allowing", "enable", "enabling", "protect",
    "protecting", "prevent", "preventing", "detect", "detecting",
    "monitor", "monitoring", "control", "controlling", "reduce",
    "reducing", "improve", "improving", "optimize", "optimizing",
}


def _term_set(text: str) -> set:
    return set(terms(text or ""))


_TOKEN_RE = re.compile(r"[^a-z0-9]+")


def _natural_tokens(text: str) -> List[str]:
    """Original (unfolded) lowercase tokens — search engines need natural
    word forms; the folded forms ('prosthesis'->'prosthesi') are for the
    term-overlap machinery ONLY. Measured defect: folded tokens in query
    strings returned EMPTY from Lens (no lexical match)."""
    return [t for t in _TOKEN_RE.split((text or "").lower())
            if len(t) > 2 and t not in _STOP_NATURAL]


_STOP_NATURAL = {
    "the", "and", "for", "with", "that", "this", "from", "into", "are",
    "was", "were", "has", "have", "had", "can", "could", "should", "would",
    "will", "shall", "may", "might", "must", "not", "but", "all", "any",
    "more", "most", "than", "then", "them", "they", "their", "there",
    "when", "which", "while", "whose", "your", "our", "its",
}


def _ranked_terms(text: str, anchors: Dict[str, int],
                  cap: int, exclude: set = None) -> List[str]:
    """Priority-weighted content-term selection across the WHOLE text,
    returning NATURAL word forms (search-ready).

    The measured formulation defect was positional: 'first 6 keyword
    words' of a verb-first intervention captured the verb phrase. This
    ranks every natural token by anchor membership (folded-key match
    against entity/mechanism/effect weights) then by first occurrence,
    so 'knee prosthesis' and 'carbon fiber reinforced' outrank
    sentence-openers regardless of position. Deterministic; disclosed.
    """
    from discovery_fabric.source_registry.query_relevance import _fold
    exclude_folded = {_fold(t) for t in (exclude or set())}
    weights: Dict[str, int] = {}
    order: Dict[str, int] = {}
    for i, t in enumerate(_natural_tokens(text)):
        order.setdefault(t, i)
        key = _fold(t)
        if key in exclude_folded:
            continue
        w = anchors.get(key, 0) + (1 if len(t) > 6 else 0)
        weights[t] = max(weights.get(t, 0), w)
    ranked = sorted(weights, key=lambda t: (-weights[t], order.get(t, 0)))
    return ranked[:cap]


# ---------------------------------------------------------------------------
# Candidate profile
# ---------------------------------------------------------------------------

@dataclass
class CandidateProfile:
    """The technical identity a prior-art search must differentiate.

    `*_terms` fields carry NATURAL word forms (search-ready, unfolded).
    `distinguishing_full` carries the UNCAPPED element set of the
    intervention (the coverage denominator — a patent claim has ALL its
    elements; measuring coverage on a capped top-8 let domain anchors
    crowd out true differentiators and inflate coverage ratios —
    measured on the battery adversarial case: 0.857 with 'acoustic' and
    'multi-modal' absent from the denominator).
    The `folded_*` methods produce folded term sets for the overlap
    machinery (same fold as query_relevance.terms — one rule family).
    """
    intervention: str
    mechanism: str
    expected_effect: str
    entity_terms: List[str]       # device + failure domain anchors
    mechanism_terms: List[str]    # the causal mechanism
    distinguishing_terms: List[str]  # candidate core (query-facing, capped)
    adjacent_terms: List[str]     # function-level, implementation-free
    distinguishing_full: List[str] = field(default_factory=list)  # ALL elements

    @staticmethod
    def _folded(words: List[str]) -> set:
        from discovery_fabric.source_registry.query_relevance import _fold
        return {_fold(w) for w in words}

    def folded_search_profile(self) -> set:
        return (self._folded(self.mechanism_terms)
                | self._folded(self.distinguishing_terms))

    def folded_entity(self) -> set:
        return self._folded(self.entity_terms)

    def folded_all(self) -> set:
        return (self.folded_search_profile() | self.folded_entity()
                | self._folded(self.adjacent_terms))


def build_candidate_profile(mechanism_map: Dict[str, Any],
                            problem: Dict[str, Any]) -> CandidateProfile:
    intervention = str(mechanism_map.get("intervention") or "")
    mechanism = str(mechanism_map.get("mechanism") or "")
    expected_effect = str(mechanism_map.get("expected_effect") or "")
    device = str(problem.get("device") or "")
    failure = str(problem.get("failure") or
                  problem.get("failure_mode") or "")

    entity_set = _term_set(f"{device} {failure}")
    mech_set = _term_set(mechanism)
    device_set = _term_set(device)

    # distinguishing terms: intervention content terms minus verb/filler,
    # ranked by anchor membership. MEASURED (A12 p01 replay): entity
    # terms must rank DEVICE-first — the failure sentence's leading
    # fragment ('battery surgical replacement') is not a coherent
    # entity query; the device ('cardiac pacemaker') is.
    anchors: Dict[str, int] = {}
    for t in device_set:
        anchors[t] = anchors.get(t, 0) + 4
    for t in entity_set - device_set:
        anchors[t] = anchors.get(t, 0) + 2
    for t in mech_set:
        anchors[t] = anchors.get(t, 0) + 3
    for t in _term_set(expected_effect):
        anchors[t] = anchors.get(t, 0) + 1
    cap = THRESHOLDS["MAX_QUERY_TERMS"]["value"]
    distinguishing = _ranked_terms(
        intervention, anchors, cap=max(8, cap + 2))
    # drop pure filler verbs that survive term extraction
    distinguishing = [t for t in distinguishing
                      if t not in _INTERVENTION_FILLER][:cap + 2]

    mechanism_q = _ranked_terms(mechanism, anchors, cap)
    entity_q = _ranked_terms(f"{device} {failure}", anchors, cap)
    # adjacent-function terms: entity + effect WITHOUT the candidate's
    # implementation terms — finds alternative approaches that could
    # destroy differentiation
    adjacent_q = _ranked_terms(
        f"{device} {expected_effect} {failure}", anchors, cap,
        exclude=set(distinguishing) - entity_set)

    # FULL element set (coverage denominator): every natural content
    # term of the intervention minus filler — UNCAPPED. A patent claim
    # has ALL its elements; a capped denominator measured 0.857 for a
    # domain-only patent against the battery candidate whose true
    # differentiators (acoustic, multi-modal) were ranked out.
    full = [t for t in _natural_tokens(intervention)
            if t not in _INTERVENTION_FILLER]
    seen_f, distinguishing_full = set(), []
    for t in full:
        if t not in seen_f:
            seen_f.add(t)
            distinguishing_full.append(t)

    return CandidateProfile(
        intervention=intervention, mechanism=mechanism,
        expected_effect=expected_effect,
        entity_terms=entity_q, mechanism_terms=mechanism_q,
        distinguishing_terms=distinguishing, adjacent_terms=adjacent_q,
        distinguishing_full=distinguishing_full)


# ---------------------------------------------------------------------------
# Query ladder — 4 classes, direct + adjacent (CEO directive 3/5)
# ---------------------------------------------------------------------------

QUERY_CLASSES = ("ENTITY", "MECHANISM", "DISTINGUISHING", "ADJACENT")


def build_query_ladder(profile: CandidateProfile) -> List[Dict[str, Any]]:
    """Multi-query strategy around the mechanism and distinguishing
    technical features — not generic intervention words.

    Each step carries BOTH forms (source-aware routing, CEO doctrine):
      query        — full keyword form (up to MAX_QUERY_TERMS) for
                     free-text endpoints (google_patents)
      query_compact — top-2 term form for TITLE-SCOPED endpoints
                     (lens_patent binds 'title:(...)'; measured:
                     4+ term title queries return 0 hits — AND-like
                     matching; 2-3 coherent terms return the right art;
                     the A12 p01 replay measured that an incoherent
                     3-fragment ('battery surgical replacement') also
                     returns 0 — device-first ranking keeps the compact
                     pair coherent)
    """
    ladder = [
        {"query_class": "ENTITY",
         "terms": profile.entity_terms,
         "purpose": "anchor the device/failure domain"},
        {"query_class": "MECHANISM",
         "terms": profile.mechanism_terms,
         "purpose": "direct prior art on the causal mechanism"},
        {"query_class": "DISTINGUISHING",
         "terms": profile.distinguishing_terms,
         "purpose": "direct prior art on the candidate's technical core"},
        {"query_class": "ADJACENT",
         "terms": profile.adjacent_terms,
         "purpose": "adjacent technical approaches that could destroy "
                    "differentiation (function without implementation)"},
    ]
    out = []
    for step in ladder:
        q = " ".join(step["terms"])
        if not q.strip():
            continue
        out.append({"query_class": step["query_class"],
                    "query": q,
                    "query_compact": " ".join(step["terms"][:2]),
                    "terms": step["terms"],
                    "purpose": step["purpose"]})
    return out


# ---------------------------------------------------------------------------
# Search execution (two patent sources, honest failure states)
# ---------------------------------------------------------------------------

@dataclass
class PatentHit:
    patent_id: str
    title: str
    snippet: str
    source_id: str
    source_url: str
    query_class: str
    query: str
    assignee: str = ""
    publication_date: str = ""
    raw_payload_sha256: str = ""


def search_patents(ladder: List[Dict[str, Any]],
                   sources: Optional[List[str]] = None,
                   sleep_between: float = 0.4,
                   per_source_results: int = 5) -> Tuple[List[PatentHit],
                                                         List[Dict[str, Any]]]:
    """Run the query ladder against the live patent sources.

    Sources: google_patents (free) + lens_patent (live token).
    patentbear is PROVIDER-METERED (20/month) and is NOT queried here by
    default (metered-source policy; recorded as NOT_QUERIED_METERED).
    Failures are recorded as UNRESOLVED_SOURCE_FAILURE per query+source —
    never converted to absence (Art. XXI.3).
    """
    sources = sources or ["google_patents", "lens_patent"]
    hits: List[PatentHit] = []
    errors: List[Dict[str, Any]] = []
    src = __import__(
        "discovery_fabric.prior_art_v2.sources", fromlist=["x"])

    class _GoogleSearch:
        """Free-text endpoint: full keyword form."""

        def __call__(self, step, n):
            return src.search_google_patents(step["query"], num_results=n)

    class _LensSearch:
        """Title-scoped endpoint (title:(...) binding — measured): compact
        top-3 form; the full 6-term form measured 0 hits on titles."""

        def __call__(self, step, n):
            return src.search_lens_patent(
                step.get("query_compact") or step["query"], num_results=n)

    fns = {"google_patents": _GoogleSearch(),
           "lens_patent": _LensSearch()}

    def _call_with_backoff(fn, step, n, source_id):
        """Retry on HTTP 429 (Lens short-window rate limit — measured
        during the 53-run replay: 52/53 runs saw at least one 429 with
        0.4s spacing; the limit clears within seconds). Backoff: 2s, 5s.
        Non-429 failures return immediately (no retry masking of real
        errors — Art. XXI.3 states stay honest)."""
        delays = (0.0, 2.0, 5.0)
        last = None
        for delay in delays:
            if delay:
                time.sleep(delay)
            last = fn(step, n)
            ok = bool(getattr(last, "success", False))
            err = str(getattr(last, "error", "") or "")
            if ok or "429" not in err:
                return last
        return last

    for step in ladder:
        for source_id in sources:
            fn = fns.get(source_id)
            if fn is None:
                errors.append({"query": step["query"], "source": source_id,
                               "error": "unknown source",
                               "epistemic_state": "UNRESOLVED_SOURCE_FAILURE"})
                continue
            try:
                r = _call_with_backoff(fn, step, per_source_results,
                                       source_id)
            except Exception as exc:  # noqa: BLE001 — recorded, never hidden
                errors.append({"query": step["query"], "source": source_id,
                               "error": f"{type(exc).__name__}: {exc}",
                               "epistemic_state": "UNRESOLVED_SOURCE_FAILURE"})
                continue
            if not getattr(r, "success", False):
                errors.append({
                    "query": step["query"], "source": source_id,
                    "error": str(getattr(r, "error", "unknown")),
                    "epistemic_state": "UNRESOLVED_SOURCE_FAILURE"})
            else:
                for h in (getattr(r, "hits", None) or []):
                    d = h if isinstance(h, dict) else vars(h)
                    hits.append(PatentHit(
                        patent_id=str(d.get("patent_id") or ""),
                        title=str(d.get("title") or ""),
                        snippet=str(d.get("snippet") or ""),
                        source_id=source_id,
                        source_url=str(d.get("source_url") or ""),
                        query_class=step["query_class"],
                        query=step["query"],
                        assignee=str(d.get("assignee_or_authors") or ""),
                        publication_date=str(
                            d.get("publication_date") or ""),
                        raw_payload_sha256=str(
                            d.get("raw_payload_sha256") or "")))
            time.sleep(sleep_between)
    return hits, errors


def dedupe_hits(hits: List[PatentHit]) -> List[PatentHit]:
    """Deduplicate by patent identity (doc key), keeping the richest
    evidence (longest snippet), then the first query class in ladder
    order (Art. XXI.6 — entity resolution before counting)."""
    best: Dict[str, PatentHit] = {}
    for h in hits:
        key = h.patent_id or h.source_url or h.title.lower()[:80]
        cur = best.get(key)
        if cur is None or len(h.snippet) > len(cur.snippet):
            best[key] = h
    return list(best.values())


# ---------------------------------------------------------------------------
# Mechanism-level adjudication (CEO directive 4)
# ---------------------------------------------------------------------------

def adjudicate_hit(hit: PatentHit,
                   profile: CandidateProfile) -> Dict[str, Any]:
    """Claim/mechanism-level relevance: the hit's TITLE + SNIPPET text is
    adjudicated against the candidate's MECHANISM + DISTINGUISHING terms
    (not against the query that found it). A hit that overlaps the entity
    domain but not the mechanism is ADJACENT_ONLY — it can threaten
    differentiation but is NOT nearest prior art."""
    from discovery_fabric.source_registry.query_relevance import _fold  # noqa: F401
    text_terms = _term_set(f"{hit.title} {hit.snippet}")
    profile_terms = profile.folded_search_profile()
    mech_overlap = sorted(profile_terms & text_terms)
    entity_overlap = sorted(profile.folded_entity() & text_terms)
    min_ov = THRESHOLDS["MIN_MECHANISM_OVERLAP"]["value"]
    mechanism_relevant = len(mech_overlap) >= min_ov
    adjacent_only = (not mechanism_relevant
                     and len(entity_overlap) >= min_ov)
    if mechanism_relevant:
        verdict = "MECHANISM_RELEVANT"
    elif adjacent_only:
        verdict = "ADJACENT_ONLY"
    else:
        verdict = "IRRELEVANT"
    return {
        "patent_id": hit.patent_id,
        "title": hit.title[:140],
        "source_id": hit.source_id,
        "verdict": verdict,
        "mechanism_overlap_terms": mech_overlap,
        "entity_overlap_terms": entity_overlap,
        "relevance_basis": {
            "method": (f"term overlap >= {min_ov} between hit text "
                       f"(title+snippet) and the candidate's mechanism ∪ "
                       f"distinguishing terms — same rule family as the "
                       f"pipeline adjudicator; the QUERY that found the "
                       f"hit is NOT the adjudication basis"),
            "query_class": hit.query_class,
        },
    }


# ---------------------------------------------------------------------------
# Family clustering (deterministic, disclosed heuristic)
# ---------------------------------------------------------------------------

def cluster_families(relevant: List[PatentHit],
                     adjudications: List[Dict[str, Any]]
                     ) -> List[Dict[str, Any]]:
    """Group mechanism-relevant hits into prior-art families: single-pass
    greedy clustering; a hit joins the first family whose representative
    shares >= 3 title content terms with it (or the same assignee —
    national-phase entries).

    MEASURED (CFRP knee case): a >= 2 threshold merged CFRP-composite
    MATERIAL art with metal-reinforced knee-component art via a weak
    'polymer reinforced' overlap — two genuinely distinct families the
    CEO directive names as a defect class ('failure to resolve multiple
    related prior-art families'). >= 3 splits them; over-splitting is
    the SAFER error direction because every split family gets its own
    coverage decision (more scrutiny, less hidden art).

    Disclosed heuristic (MODEL_DERIVED class) — deterministic."""
    adj_by_id = {a["patent_id"]: a for a in adjudications}
    families: List[Dict[str, Any]] = []
    for h in relevant:
        h_terms = _term_set(h.title)
        placed = False
        for fam in families:
            rep = fam["members"][0]
            same_assignee = (h.assignee and h.assignee == rep.assignee)
            shared = h_terms & _term_set(rep.title)
            if len(shared) >= 3 or same_assignee:
                fam["members"].append(h)
                placed = True
                break
        if not placed:
            families.append({"members": [h]})
    out = []
    for i, fam in enumerate(families):
        # representative = member with the longest snippet (richest
        # evidence); ties broken by patent_id for determinism
        rep = sorted(fam["members"],
                     key=lambda m: (-len(m.snippet), m.patent_id))[0]
        out.append({
            "family_id": f"PA-FAM-{i + 1:02d}",
            "representative": rep,
            "members": sorted(fam["members"],
                              key=lambda m: m.patent_id),
            "adjudication": adj_by_id.get(rep.patent_id, {}),
        })
    return out


# ---------------------------------------------------------------------------
# Evidence tiers + coverage decision
# ---------------------------------------------------------------------------

def fetch_claim_evidence(patent_id: str,
                         hit: PatentHit) -> Dict[str, Any]:
    """Deep-fetch full claims (google_patents, free). On failure the hit
    keeps its abstract-tier evidence (Lens snippet); failures are
    recorded, never silently downgraded to 'no evidence'."""
    src = __import__(
        "discovery_fabric.prior_art_v2.sources", fromlist=["x"])
    fetched: Dict[str, Any] = {"claims_text": "", "abstract": "",
                               "fetch_status": "NOT_ATTEMPTED"}
    if patent_id:
        try:
            r = src.fetch_google_patent_full_claims(patent_id)
            if r.get("claims") or r.get("abstract"):
                fetched["claims_text"] = " ".join(r.get("claims") or [])
                fetched["abstract"] = str(r.get("abstract") or "")
                fetched["fetch_status"] = "OK"
            else:
                fetched["fetch_status"] = str(
                    r.get("error") or "EMPTY_RESPONSE")
        except Exception as exc:  # noqa: BLE001
            fetched["fetch_status"] = f"{type(exc).__name__}: {exc}"
    return fetched


def evidence_tier(hit: PatentHit, claims: Dict[str, Any]) -> str:
    if claims.get("fetch_status") == "OK" and claims.get("claims_text"):
        return "CLAIMS"
    min_chars = THRESHOLDS["ABSTRACT_TIER_MIN_CHARS"]["value"]
    if len(hit.snippet) >= min_chars:
        return "ABSTRACT"
    return "TITLE"


def family_text(hit: PatentHit, claims: Dict[str, Any]) -> str:
    return " ".join([hit.title, hit.snippet,
                     claims.get("claims_text") or "",
                     claims.get("abstract") or ""])


def coverage_decision(profile: CandidateProfile,
                      fam_text: str) -> Dict[str, Any]:
    """Per-family coverage of the candidate's FULL element set.

    coverage_ratio = |full_elements ∩ family_text| / |full_elements|
    (UNCAPPED element set — the claim's elements, not the query core;
    measured defect: a capped denominator let a domain-only patent
    reach 0.857 while the true differentiators were ranked out of it)
    FULL_COVER (anticipation evidence): mechanism overlap >= 2 AND
        coverage_ratio >= 0.8 (declared threshold)
    PARTIAL_COVER: mechanism overlap >= 2, some but not full coverage
    NONE: mechanism overlap < 2 (family is not mechanism art)
    """
    f_terms = _term_set(fam_text)
    # full element set as the denominator; query-facing capped set as
    # the disclosed fallback when the intervention is terse
    d_terms = (profile._folded(profile.distinguishing_full)
               or profile._folded(profile.distinguishing_terms)
               or profile.folded_search_profile())
    m_terms = profile.folded_search_profile()
    d_hit = sorted(d_terms & f_terms)
    m_hit = sorted(m_terms & f_terms)
    ratio = (len(d_hit) / len(d_terms)) if d_terms else None
    min_ov = THRESHOLDS["MIN_MECHANISM_OVERLAP"]["value"]
    cov_ratio = THRESHOLDS["ANTICIPATION_COVERAGE_RATIO"]["value"]
    if len(m_hit) >= min_ov and ratio is not None and ratio >= cov_ratio:
        cls = "FULL_COVER"
    elif len(m_hit) >= min_ov and d_hit:
        cls = "PARTIAL_COVER"
    elif len(m_hit) >= min_ov:
        cls = "MECHANISM_ONLY"
    else:
        cls = "NONE"
    return {
        "coverage_class": cls,
        "mechanism_overlap_terms": m_hit,
        "distinguishing_terms_covered": d_hit,
        "distinguishing_terms_surviving": sorted(d_terms - f_terms),
        "coverage_ratio": round(ratio, 3) if ratio is not None else None,
        "thresholds_applied": {
            "min_mechanism_overlap": min_ov,
            "anticipation_coverage_ratio": cov_ratio},
    }


# ---------------------------------------------------------------------------
# Resolution state machine (CEO directive 6 — honest UNRESOLVED)
# ---------------------------------------------------------------------------

RESOLVED_STATES = ("RESOLVED_DIFFERENTIATED", "RESOLVED_ANTICIPATED")
UNRESOLVED_STATES = ("UNRESOLVED_INSUFFICIENT_EVIDENCE",
                     "UNRESOLVED_NO_RELEVANT_ART",
                     "UNRESOLVED_PARTIAL_EVIDENCE")


def resolve_differentiation(families: List[Dict[str, Any]],
                            profile: CandidateProfile,
                            search_errors: List[Dict[str, Any]],
                            searches_succeeded: bool,
                            deep_fetch: bool = True
                            ) -> Dict[str, Any]:
    """Decide the prior-art position with per-family evidence.

    RESOLVED_ANTICIPATED    some family shows FULL_COVER at >= ABSTRACT
                            tier — the candidate's distinguishing core is
                            already covered (specific-disclosure-class
                            evidence; kill-grade at CLASSIFY)
    RESOLVED_DIFFERENTIATED every family adjudicated at >= ABSTRACT tier,
                            no family covers the core — the position is
                            resolved with surviving differentiators
    UNRESOLVED_PARTIAL_EVIDENCE  families exist but at least one is stuck
                            at TITLE tier (evidence too thin to decide)
    UNRESOLVED_NO_RELEVANT_ART   searches succeeded, nothing relevant
                            (zero hits is NOT novelty — Art. XXI.2)
    UNRESOLVED_INSUFFICIENT_EVIDENCE  all searches failed (provider
                            failures are not absence — Art. XXI.3)
    """
    per_family: List[Dict[str, Any]] = []
    for fam in families:
        rep: PatentHit = fam["representative"]
        claims = (fetch_claim_evidence(rep.patent_id, rep)
                  if deep_fetch else {"fetch_status": "NOT_ATTEMPTED"})
        tier = evidence_tier(rep, claims)
        cov = coverage_decision(profile, family_text(rep, claims))
        per_family.append({
            "family_id": fam["family_id"],
            "representative": {
                "patent_id": rep.patent_id, "title": rep.title[:140],
                "source_id": rep.source_id, "source_url": rep.source_url,
                "assignee": rep.assignee,
                "publication_date": rep.publication_date},
            "family_size": len(fam["members"]),
            "member_patent_ids": [m.patent_id for m in fam["members"]],
            "evidence_tier": tier,
            "claims_fetch_status": claims.get("fetch_status"),
            "coverage": cov,
        })
    tiers = [f["evidence_tier"] for f in per_family]
    full_cover = [f for f in per_family
                  if f["coverage"]["coverage_class"] == "FULL_COVER"]
    tier_rank = {"TITLE": 0, "ABSTRACT": 1, "CLAIMS": 2}
    if full_cover and all(tier_rank[t] >= 1 for t in tiers):
        state = "RESOLVED_ANTICIPATED"
    elif per_family and all(tier_rank[t] >= 1 for t in tiers):
        state = "RESOLVED_DIFFERENTIATED"
    elif per_family:
        state = "UNRESOLVED_PARTIAL_EVIDENCE"
    elif searches_succeeded:
        state = "UNRESOLVED_NO_RELEVANT_ART"
    else:
        state = "UNRESOLVED_INSUFFICIENT_EVIDENCE"

    evidence_tier_summary = (
        f"CLAIMS:{tiers.count('CLAIMS')} ABSTRACT:{tiers.count('ABSTRACT')} "
        f"TITLE:{tiers.count('TITLE')}" if tiers else "NO_FAMILIES")

    resolution = {
        "state": state,
        "epistemic_class": "SEARCH_RESULT",
        "constitutional_limitation": (
            "a search-derived prior-art POSITION, not a novelty "
            "determination (Art. XXVIII); coverage measured by declared "
            "term-overlap thresholds, not a claim chart"),
        "evidence_tier_summary": evidence_tier_summary,
        "per_family": per_family,
        "n_families": len(per_family),
        "n_search_errors": len(search_errors),
        "thresholds": THRESHOLDS,
    }
    if state == "RESOLVED_ANTICIPATED":
        resolution["anticipated_by"] = [
            f["family_id"] for f in full_cover]
        resolution["kill_semantics"] = (
            "specific-disclosure-class evidence found by search; "
            "CLASSIFY treats this as a prior-art kill with the evidence "
            "recorded here")
    if state == "RESOLVED_DIFFERENTIATED":
        surviving = set()
        for f in per_family:
            surviving.update(
                f["coverage"]["distinguishing_terms_surviving"])
        resolution["surviving_differentiators"] = sorted(surviving)
    return resolution


# ---------------------------------------------------------------------------
# The collision core — one authority for the loop stage AND grid candidates
# ---------------------------------------------------------------------------

def run_collision(mechanism_map: Dict[str, Any],
                  problem: Dict[str, Any],
                  sources: Optional[List[str]] = None,
                  deep_fetch: bool = True,
                  sleep_between: float = 0.4,
                  ) -> Dict[str, Any]:
    """Full mechanism-centered prior-art collision. LLM-free, network
    search only. Returns the collision_results dict consumed by the
    COLLISION adapter, the invention spec, and (for grid/ensemble
    candidates) the per-candidate env view — ONE implementation for all
    call sites (Art. X: single authority)."""
    profile = build_candidate_profile(mechanism_map, problem)
    ladder = build_query_ladder(profile)
    hits, errors = search_patents(ladder, sources=sources,
                                  sleep_between=sleep_between)
    hits = dedupe_hits(hits)
    adjudications = [adjudicate_hit(h, profile) for h in hits]
    relevant = [h for h, a in zip(hits, adjudications)
                if a["verdict"] == "MECHANISM_RELEVANT"]
    adjacent = [h for h, a in zip(hits, adjudications)
                if a["verdict"] == "ADJACENT_ONLY"]
    families = cluster_families(relevant, adjudications)
    searches_succeeded = bool(hits) or not errors
    resolution = resolve_differentiation(
        families, profile, errors, searches_succeeded,
        deep_fetch=deep_fetch)

    # nearest prior art = family representatives (mechanism-relevant by
    # construction, per-family evidence tiers recorded)
    nearest = []
    for fam_res in resolution["per_family"]:
        rep = fam_res["representative"]
        cov = fam_res["coverage"]
        nearest.append({
            "patent_id": rep["patent_id"],
            "title": rep["title"],
            "url": rep["source_url"],
            "family_id": fam_res["family_id"],
            "family_size": fam_res["family_size"],
            "evidence_tier": fam_res["evidence_tier"],
            "mechanism_overlap_terms":
                cov["mechanism_overlap_terms"],
            "distinguishing_terms_covered":
                cov["distinguishing_terms_covered"],
            "distinguishing_terms_surviving":
                cov["distinguishing_terms_surviving"],
            "coverage_class": cov["coverage_class"],
            "coverage_ratio": cov["coverage_ratio"],
        })

    # novelty_risk: backward-compatible vocabulary for downstream stages
    if resolution["state"] == "RESOLVED_ANTICIPATED":
        novelty_risk = "ADJACENT_COLLISION_CANDIDATES"
    elif nearest:
        novelty_risk = "ADJACENT_COLLISION_CANDIDATES"
    elif errors and not hits:
        novelty_risk = "UNRESOLVED_INSUFFICIENT_EVIDENCE"
    elif searches_succeeded:
        novelty_risk = "SEARCHED_NO_DIRECT_TITLE_MATCH"
    else:
        novelty_risk = "UNRESOLVED_INSUFFICIENT_EVIDENCE"

    return {
        "strategy": "mechanism-centered multi-query (R376)",
        "query_ladder": ladder,
        "candidate_profile": {
            "entity_terms": profile.entity_terms,
            "mechanism_terms": profile.mechanism_terms,
            "distinguishing_terms": profile.distinguishing_terms,
            "adjacent_terms": profile.adjacent_terms,
        },
        "patent": {
            "sources": (sources or ["google_patents", "lens_patent"]),
            "metered_sources_not_queried": [
                {"source": "patentbear",
                 "reason": "provider-metered 20/month; reserved by the "
                           "metered-source policy (K-series) — not spent "
                           "on collision search"}],
            "hit_count": len(hits),
            "hits": [{"patent_id": h.patent_id, "title": h.title,
                      "snippet": h.snippet[:400], "source_id": h.source_id,
                      "query_class": h.query_class, "query": h.query,
                      "assignee": h.assignee,
                      "publication_date": h.publication_date}
                     for h in hits],
            "source_errors": errors,
            "relevance_adjudications": adjudications,
            "relevant_hit_count": len(relevant),
            "adjacent_only_hits": [
                {"patent_id": h.patent_id, "title": h.title,
                 "source_id": h.source_id, "query_class": h.query_class}
                for h in adjacent],
        },
        "families": [{
            "family_id": f["family_id"],
            "family_size": len(f["members"]),
            "member_patent_ids": [m.patent_id for m in f["members"]],
        } for f in families],
        "differentiation_resolution": resolution,
        "nearest_prior_art": nearest,
        "nearest_prior_art_note": (
            "family representatives; every entry is MECHANISM_RELEVANT "
            "(>= 2 term overlap with the candidate's mechanism ∪ "
            "distinguishing terms against title+snippet text) with "
            "per-family coverage and evidence tier recorded"),
        "novelty_risk": novelty_risk,
        "prior_art_status": resolution["state"],
        "actions": (["inspect_nearest_claims"] if nearest
                    else ["expand_search_sources"]),
    }

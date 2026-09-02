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
    "CROSS_DOMAIN_MIN_NONGENERIC_OVERLAP": {
        "value": 3,
        "epistemic_class": "ENGINEERING",
        "justification": (
            "R377 patent-text ground truth (TOSCANINI/"
            "R377_PATENT_TEXT_FETCH.json + R377_PATENT_TEXT_GROUND_"
            "TRUTH.json): 12/30 family representatives (40%) were "
            "substantively irrelevant cross-domain term collisions "
            "(CWDM optical link for a battery-thermal candidate; "
            "dental-condition monitoring for rolling stock; bone "
            "fracture forceps for rail steel...). A hit sharing NO "
            "entity term with the candidate now needs >= 3 NON-generic "
            "mechanism terms to be mechanism art: the measured true "
            "cross-domain analog (line-pipe steel with hydrogen "
            "fracture toughness for a rail-steel candidate) shares 3 "
            "non-generic terms and survives; every measured false "
            "positive shares <= 2 and is demoted. This RAISES the "
            "cross-domain bar (was the same >= 2 as same-domain) — "
            "stricter, not weaker (Art. VII)."
        ),
        "uncertainty": "term overlap remains a proxy; entity word-sense "
                       "collisions ('gear': steering vs draft) can still "
                       "pass — disclosed limitation, not a solved problem",
    },
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

# Generic function vocabulary: appears in every technical domain, so a
# term overlap consisting ONLY of these is a cross-domain collision,
# not a substantive relationship (R377 measured: CWDM optical-link
# patent matched a battery-thermal candidate on 'optical'+'thermal';
# a dental-monitoring patent matched a rolling-stock candidate on
# 'condition'+'monitoring'+'based').
GENERIC_FUNCTION_TERMS = {
    "system", "systems", "method", "methods", "apparatus", "device",
    "devices", "process", "processes", "technique", "techniques",
    "monitoring", "monitor", "monitors", "sensor", "sensors",
    "sensing", "detection", "detecting", "detect", "control",
    "controlling", "controller", "management", "managing", "data",
    "signal", "signals", "processing", "based", "including",
    "configured", "assembly", "structure", "structures",
    "component", "components", "element", "elements", "unit",
    "module", "circuit", "circuits", "level", "point", "points",
    "along", "path", "early", "real", "time", "smart", "advanced",
    "improved", "novel", "existing", "retrofit", "retrofitted",
    "implement", "implemented", "deployment", "deploy", "install",
    "installed", "connected", "integrated", "analysis", "analyzes",
    "pattern", "patterns",
}

# Verbs/filler that open LLM-written interventions and carry no search value.
# The measured defect: position-based term selection captured these first.
# NOTE (R377 measured): these verbs are filler for QUERY TERM SELECTION
# in the DISTINGUISHING class, but the FUNCTION noun forms (detection,
# monitoring, protection...) are NOT filler — they are the function
# vocabulary the FUNCTION query class searches on (the EV run's ladder
# had no form of 'detect' anywhere and never retrieved the rich
# thermal-runaway-DETECTION art family that a single function-word
# query returns).
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
    device_terms: List[str] = field(default_factory=list)  # DEVICE-only
    function_terms: List[str] = field(default_factory=list)  # R377: what it DOES
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

    def folded_device(self) -> set:
        """DEVICE-only anchors (no failure-mode words). The same-domain
        adjudication path requires a DEVICE term: 'thermal' is a
        failure-mode adjective that appears in every thermal patent
        ('Thermal-efficient CWDM link') and must not confer same-domain
        status on a battery candidate (R377 measured case)."""
        return self._folded(self.device_terms)

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

    # R377 (measured anchor-crowding defect): the DISTINGUISHING query
    # must carry the candidate's TECHNICAL CORE. In the electronics run
    # the query was 'battery consumer lithium management ion temperature
    # current' — 'overcharge' and 'protection' (the actual differentiating
    # technical terms) were ranked out by entity anchors (+4) while the
    # true art ('battery overcharge protection circuit') went unfound.
    # SECOND measured iteration: anchoring on the mechanism text is NOT
    # enough — the mechanism itself can be entity-dominated ('smart
    # battery management systems'). The technical core is the
    # intervention vocabulary that is NOT entity/device boilerplate and
    # NOT generic: 'overcharge', 'protection', 'perovskite',
    # 'semitransparent' — the words only THIS candidate's claim adds to
    # the domain. Those lead the query; entity anchors fill the rest.
    from discovery_fabric.source_registry.query_relevance import _fold
    entity_folded = {_fold(t) for t in entity_set}
    device_folded = {_fold(t) for t in device_set}
    mech_folded = {_fold(t) for t in mech_set}

    def _core_weight(tok: str) -> int:
        f = _fold(tok)
        w = 0
        if f not in entity_folded and f not in device_folded:
            w += 3  # not domain boilerplate = differentiating by definition
        if f in mech_folded:
            w += 1
        if len(tok) > 6:
            w += 1
        return w

    core_candidates = [t for t in _natural_tokens(intervention)
                       if t not in _INTERVENTION_FILLER
                       and t not in GENERIC_FUNCTION_TERMS]
    core_order: Dict[str, int] = {}
    core_ranked: List[str] = []
    for t in core_candidates:
        if t in core_order:
            continue
        core_order[t] = len(core_ranked)
        core_ranked.append(t)
    core_ranked.sort(key=lambda t: (-_core_weight(t), core_order[t]))
    tech_core = [t for t in core_ranked if _core_weight(t) >= 3][
        :max(3, cap - 3)]
    # prepend the technical core (deduplicated) — the differentiating
    # vocabulary leads the query; entity anchors follow it
    for t in reversed(tech_core):
        if t not in distinguishing:
            distinguishing.insert(0, t)
    distinguishing = distinguishing[:cap + 2]

    mechanism_q = _ranked_terms(mechanism, anchors, cap)
    entity_q = _ranked_terms(f"{device} {failure}", anchors, cap)
    device_q = _ranked_terms(device, anchors, cap)
    # adjacent-function terms: entity + effect WITHOUT the candidate's
    # implementation terms — finds alternative approaches that could
    # destroy differentiation
    adjacent_q = _ranked_terms(
        f"{device} {expected_effect} {failure}", anchors, cap,
        exclude=set(distinguishing) - entity_set)

    # R377 (measured adjacent-collapse defect): in both inspected runs
    # the ADJACENT query came out IDENTICAL to the ENTITY query — the
    # exclude set (distinguishing minus entity) was empty because the
    # distinguishing terms overlapped the entity terms, so the
    # adjacent search re-ran the entity search and found the SAME art.
    # Fix: the adjacent query excludes ALL entity terms and searches
    # the FUNCTION vocabulary (effect + failure function) — the
    # alternative-approach space by construction.
    if adjacent_q == entity_q:
        adjacent_q = _ranked_terms(
            f"{expected_effect} {failure}", anchors, cap,
            exclude=entity_set)

    # R377 FUNCTION query class (measured function-term starvation): the
    # EV run's ladder contained no form of 'detect' for a DETECTION
    # candidate and never retrieved the thermal-runaway-DETECTION art
    # (a single 'thermal runaway detection battery' query returns 5
    # direct-art patents). Function nouns are extracted from the
    # expected_effect + intervention in NOUN form and combined with the
    # top entity term — the function-word search the ladder lacked.
    function_q = _function_terms(entity_q, expected_effect,
                                 intervention, failure)

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
        entity_terms=entity_q, device_terms=device_q,
        mechanism_terms=mechanism_q,
        distinguishing_terms=distinguishing, adjacent_terms=adjacent_q,
        function_terms=function_q,
        distinguishing_full=distinguishing_full)


# Verb -> canonical function-noun map (deterministic, disclosed). The
# measured starvation defect: the intervention says "to detect early
# thermal runaway initiation" — the VERB 'detect' was stripped as filler
# and the noun 'detection' never entered any query, while the art is
# TITLED 'thermal runaway detection system'. Patents name the function
# with nouns; the ladder must search the noun form.
_FUNCTION_VERB_TO_NOUN = {
    "detect": "detection", "detects": "detection",
    "detecting": "detection", "detected": "detection",
    "monitor": "monitoring", "monitors": "monitoring",
    "monitored": "monitoring",
    "prevent": "prevention", "prevents": "prevention",
    "preventing": "prevention", "prevented": "prevention",
    "protect": "protection", "protects": "protection",
    "protecting": "protection", "protected": "protection",
    "sense": "sensing", "senses": "sensing",
    "diagnose": "diagnosis", "diagnoses": "diagnosis",
    "diagnosing": "diagnosis",
    "predict": "prediction", "predicts": "prediction",
    "predicting": "prediction", "predicted": "prediction",
    "regulate": "regulation", "regulates": "regulation",
    "regulating": "regulation",
    "isolate": "isolation", "isolates": "isolation",
    "isolating": "isolation",
    "mitigate": "mitigation", "mitigates": "mitigation",
    "mitigating": "mitigation",
    "suppress": "suppression", "suppresses": "suppression",
    "suppressing": "suppression",
    "estimate": "estimation", "estimates": "estimation",
    "estimating": "estimation",
    "activate": "activation", "activates": "activation",
    "activating": "activation",
    "indicate": "indication", "indicates": "indication",
    "indicating": "indication",
    "measure": "measurement", "measures": "measurement",
    "measuring": "measurement",
    "inspect": "inspection", "inspects": "inspection",
    "inspecting": "inspection",
    "compensate": "compensation", "compensates": "compensation",
    "compensating": "compensation",
    "adjust": "adjustment", "adjusts": "adjustment",
    "adjusting": "adjustment",
    "warn": "warning", "warns": "warning",
    "switch": "switching", "switches": "switching",
}


# Words that add NOTHING to a function query (structure-only words).
# NOTE: function nouns themselves (detection, protection, monitoring,
# imaging, measurement...) are GOOD query terms even though they sit in
# GENERIC_FUNCTION_TERMS — that set governs CROSS-DOMAIN ADJUDICATION
# (a collision of only generic words is not substantive), while THIS
# set governs QUERY CONSTRUCTION (patents are titled '... detection
# system', '... protection circuit'). Two roles, two lists.
_FUNCTION_QUERY_STOP = {
    "system", "systems", "method", "methods", "apparatus", "device",
    "devices", "process", "processes", "technique", "using", "based",
    "including", "configured", "processing", "management", "unit",
    "module", "circuit", "circuits", "implementation", "implementing",
    "implement", "development", "developing", "develop",
}


def _function_terms(entity_q: List[str], expected_effect: str,
                    intervention: str, failure: str) -> List[str]:
    """FUNCTION query terms: what the candidate DOES (canonical noun
    form) + the top entity anchor. Deterministic extraction: function
    verbs AND function nouns present in the effect/intervention text
    are normalized to the noun patents are TITLED with (detect ->
    'detection', prevent -> 'protection'...). The verb forms stay in
    _INTERVENTION_FILLER for the DISTINGUISHING class; the NOUN forms
    here are the function vocabulary ('thermal runaway detection
    system', 'battery overcharge protection circuit')."""
    _FN_RE = re.compile(
        r"\b[a-z]+(?:tion|sion|ment|ing|ness|ity|ance|ence)\b")
    source_text = f"{expected_effect} {intervention} {failure}".lower()
    candidates: List[str] = []
    # 1. verb forms normalized to canonical function nouns
    for w in re.findall(r"[a-z]+", source_text):
        if w in _FUNCTION_VERB_TO_NOUN:
            fn = _FUNCTION_VERB_TO_NOUN[w]
            if fn not in _FUNCTION_QUERY_STOP and fn not in candidates:
                candidates.append(fn)
    # 2. noun-suffix function words already in the text
    for m in _FN_RE.finditer(source_text):
        w = m.group(0)
        if w in _FUNCTION_QUERY_STOP or w in _STOP_NATURAL:
            continue
        if w not in candidates:
            candidates.append(w)
    out: List[str] = []
    if entity_q:
        out.append(entity_q[0])
    for w in candidates:
        if len(out) >= THRESHOLDS["MAX_QUERY_TERMS"]["value"]:
            break
        if w not in out:
            out.append(w)
    return out[:THRESHOLDS["MAX_QUERY_TERMS"]["value"]]


# ---------------------------------------------------------------------------
# Query ladder — 4 classes, direct + adjacent (CEO directive 3/5)
# ---------------------------------------------------------------------------

QUERY_CLASSES = ("ENTITY", "MECHANISM", "DISTINGUISHING", "FUNCTION",
                 "ADJACENT")


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
         "purpose": "direct prior art on the candidate's technical core "
                    "(technical terms lead; entity anchors follow — "
                    "R377 anchor-crowding fix)"},
        {"query_class": "FUNCTION",
         "terms": profile.function_terms,
         "purpose": "prior art on the FUNCTION itself (detection / "
                    "protection / regulation...): patents are titled "
                    "with function nouns; a detection candidate whose "
                    "ladder lacks 'detection' cannot find detection art "
                    "(R377 measured: the EV run missed the entire "
                    "thermal-runaway-DETECTION family)"},
        {"query_class": "ADJACENT",
         "terms": profile.adjacent_terms,
         "purpose": "adjacent technical approaches that could destroy "
                    "differentiation (function without implementation; "
                    "entity terms excluded so it never collapses into "
                    "the entity query — R377 fix)"},
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
    patentbear (R378, CEO directive 'Use PatentBear for patents') is an
    OPT-IN source: pass sources=["patentbear", ...] explicitly. It is
    provider-metered and carries a persistent quota guard with a
    reserve floor (patentbear_meter.json; metered-source policy) —
    when the guard refuses, the refusal is recorded as
    NOT_QUERIED_QUOTA_GUARD, never as absence.
    Failures are recorded as UNRESOLVED_SOURCE_FAILURE per
    query+source — never converted to absence (Art. XXI.3).
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

    class _PatentBearSearch:
        """R378 CEO-designated patent source. Free-text keyword form
        (PatentBear searches full text natively). The persistent meter
        guard inside search_patent_bear refuses at the reserve floor —
        the refusal surfaces here as a recorded error, never absence."""

        def __call__(self, step, n):
            return src.search_patent_bear(step["query"],
                                          num_results=max(n, 8))

    fns = {"google_patents": _GoogleSearch(),
           "lens_patent": _LensSearch(),
           "patentbear": _PatentBearSearch()}

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
    differentiation but is NOT nearest prior art.

    R377 entity-anchored precision rule (measured: 12/30 family
    representatives in the six fresh runs were substantively irrelevant
    cross-domain term collisions):

      same-domain (>= 1 entity term in the hit text):
          MECHANISM_RELEVANT requires >= 2 mechanism terms (UNCHANGED
          threshold; generic function words count — in-domain they are
          meaningful: 'pressure monitoring device for medicine
          infusion' IS the medical candidate's function)
      cross-domain (0 entity terms):
          MECHANISM_RELEVANT requires >= 3 NON-GENERIC mechanism terms
          (RAISED bar — 'optical'+'thermal' alone is a CWDM collision,
          not battery art; 'hydrogen'+'fracture'+'steel' IS genuine
          cross-domain steel art for a rail-steel candidate)
      CROSS_DOMAIN_TERM_COLLISION: mechanism overlap exists, no entity
          overlap, below the cross-domain bar — recorded with terms and
          basis, never a family (the measured demotion class)
    """
    from discovery_fabric.source_registry.query_relevance import _fold  # noqa: F401
    text_terms = _term_set(f"{hit.title} {hit.snippet}")
    profile_terms = profile.folded_search_profile()
    mech_overlap = sorted(profile_terms & text_terms)
    entity_overlap = sorted(profile.folded_entity() & text_terms)
    device_overlap = sorted(profile.folded_device() & text_terms)
    min_ov = THRESHOLDS["MIN_MECHANISM_OVERLAP"]["value"]
    cross_min = THRESHOLDS["CROSS_DOMAIN_MIN_NONGENERIC_OVERLAP"]["value"]
    mech_nongeneric = sorted(
        t for t in mech_overlap if t not in GENERIC_FUNCTION_TERMS)

    if device_overlap:
        # same/related domain (a DEVICE noun appears in the hit text):
        # the ORIGINAL >= 2 rule, unchanged
        mechanism_relevant = len(mech_overlap) >= min_ov
    else:
        # cross-domain (no device term): stricter — non-generic terms
        # only, higher bar
        mechanism_relevant = len(mech_nongeneric) >= cross_min
    adjacent_only = (not mechanism_relevant
                     and len(entity_overlap) >= min_ov)
    term_collision = (not mechanism_relevant and not adjacent_only
                      and len(mech_overlap) >= 1)

    if mechanism_relevant:
        verdict = "MECHANISM_RELEVANT"
    elif adjacent_only:
        verdict = "ADJACENT_ONLY"
    elif term_collision:
        verdict = "CROSS_DOMAIN_TERM_COLLISION"
    else:
        verdict = "IRRELEVANT"

    basis = {
        "method": (f"term overlap >= {min_ov} between hit text "
                   f"(title+snippet) and the candidate's mechanism ∪ "
                   f"distinguishing terms — same rule family as the "
                   f"pipeline adjudicator; the QUERY that found the "
                   f"hit is NOT the adjudication basis"),
        "query_class": hit.query_class,
    }
    if not device_overlap:
        basis["cross_domain_rule"] = (
            f"no DEVICE-term overlap: mechanism relevance required "
            f">= {cross_min} NON-generic mechanism terms "
            f"(R377 precision rule; generic function words excluded "
            f"from the cross-domain count; failure-mode adjectives do "
            f"not confer same-domain status)")
    return {
        "patent_id": hit.patent_id,
        "title": hit.title[:140],
        "source_id": hit.source_id,
        "verdict": verdict,
        "mechanism_overlap_terms": mech_overlap,
        "mechanism_overlap_nongeneric": mech_nongeneric,
        "entity_overlap_terms": entity_overlap,
        "device_overlap_terms": device_overlap,
        "relevance_basis": basis,
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
    recorded, never silently downgraded to 'no evidence'.

    R377 fixes (both measured):
      1. the Google URL is built from the CANONICAL id form — the Lens
         doc_key ('US_20260253984_A1_20260827') 404s on Google; the
         canonical form is 'US20260253984A1'
      2. when Google fails (503-bot-blocked from this ASN), the FULL
         Lens abstract is deep-fetched by doc_key — the family's
         coverage decision then measures against the COMPLETE abstract
         text, not the 400-char search snippet (more evidence, same
         rules — Art. VII)
    """
    src = __import__(
        "discovery_fabric.prior_art_v2.sources", fromlist=["x"])
    fetched: Dict[str, Any] = {"claims_text": "", "abstract": "",
                               "fetch_status": "NOT_ATTEMPTED",
                               "fetch_path": None}
    if patent_id:
        canonical = src.google_patents_canonical_id(patent_id)
        try:
            r = src.fetch_google_patent_full_claims(canonical or patent_id)
            if r.get("claims") or r.get("abstract"):
                fetched["claims_text"] = " ".join(r.get("claims") or [])
                fetched["abstract"] = str(r.get("abstract") or "")
                fetched["fetch_status"] = "OK"
                fetched["fetch_path"] = "google_patents_canonical"
            else:
                fetched["fetch_status"] = str(
                    r.get("error") or "EMPTY_RESPONSE")
        except Exception as exc:  # noqa: BLE001
            fetched["fetch_status"] = f"{type(exc).__name__}: {exc}"
        # Lens full-abstract fallback — claims unavailable, but the
        # COMPLETE abstract is strictly better evidence than the
        # 400-char snippet (measured: all 30 family reps in the six
        # fresh runs were stuck on truncated snippets)
        if fetched["fetch_status"] != "OK":
            google_error = str(fetched["fetch_status"])
            try:
                lr = src.fetch_lens_patent_full_abstract(patent_id)
                if lr.get("abstract_full"):
                    fetched["abstract"] = str(lr["abstract_full"])
                    fetched["fetch_status"] = "OK"
                    fetched["fetch_path"] = (
                        "lens_doc_key_full_abstract (google claims "
                        f"unavailable: {google_error})")
                else:
                    fetched["lens_fallback_error"] = str(
                        lr.get("error") or "NO_ABSTRACT")
            except Exception as exc:  # noqa: BLE001
                fetched["lens_fallback_error"] = f"{type(exc).__name__}: {exc}"
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
                     "UNRESOLVED_PARTIAL_EVIDENCE",
                     "UNRESOLVED_SEARCH_INCOMPLETE")

# R394 section 3: the relevance-instrument identity. Persisted in every
# resolution record and every adjudication so the determinism contract
# is checkable: same problem + source snapshot + query + THIS model
# version + THESE thresholds must yield the same relevance decision.
RELEVANCE_MODEL_VERSION = "collision_resolution/2.0.0"


def mandatory_searches_complete(errors: List[Dict[str, Any]],
                                ladder: List[Dict[str, Any]],
                                sources: Optional[List[str]] = None) -> Dict[str, Any]:
    """R394 section 2: which (ladder query class x source) pairs are
    MANDATORY search dependencies for a positive differentiation claim,
    and whether every one of them completed successfully.

    Rule (declared, fail-closed): every query class in the ladder that
    was ATTEMPTED against every configured source is mandatory. A pair
    is complete when its search returned without error (hits or a
    legitimate zero). Any error on any mandatory pair makes the search
    universe incomplete -> positive differentiation is FORBIDDEN.

    The deployed-production defect this closes (R394/PRODUCTION_AUDIT
    claim 4, CONFIRMED_CURRENT): run ts_d1ab9fd4d756 claimed
    RESOLVED_DIFFERENTIATED while 5 of 10 ladder searches had FAILED —
    resolve_differentiation never consulted search_errors and
    run_collision computed searches_succeeded = bool(hits) or not
    errors (one surviving query 'succeeded' the whole search).
    """
    sources = sources or ["google_patents", "lens_patent"]
    n_pairs = len(ladder) * len(sources)
    n_err = len(errors)
    complete = (n_err == 0) and n_pairs > 0
    failed_pairs = [
        {"query": e.get("query", ""), "source": e.get("source"),
         "error": str(e.get("error", ""))[:200]}
        for e in errors]
    return {
        "mandatory_pairs": n_pairs,
        "failed_pairs": n_err,
        "complete": complete,
        "failed": failed_pairs,
        "rule": ("every attempted (query_class x source) pair must "
                 "complete successfully before RESOLVED_DIFFERENTIATED "
                 "is permitted (R394 s2; a partial search cannot "
                 "support a no-covering-art claim)"),
        "relevance_model_version": RELEVANCE_MODEL_VERSION,
    }


def resolve_differentiation(families: List[Dict[str, Any]],
                            profile: CandidateProfile,
                            search_errors: List[Dict[str, Any]],
                            searches_succeeded: bool,
                            deep_fetch: bool = True,
                            precomputed: Optional[List[Dict[str, Any]]] = None,
                            search_incomplete: Optional[bool] = None,
                            ) -> Dict[str, Any]:
    """Decide the prior-art position with per-family evidence.

    RESOLVED_ANTICIPATED    some family shows FULL_COVER at >= ABSTRACT
                            tier — the candidate's distinguishing core is
                            already covered (specific-disclosure-class
                            evidence; kill-grade at CLASSIFY). May stand
                            on a PARTIALLY failed search: the covering
                            family is found art regardless of whether
                            other searches ran; the incompleteness is
                            disclosed, never silently dropped.
    RESOLVED_DIFFERENTIATED every family adjudicated at >= ABSTRACT tier,
                            no family covers the core, AND every
                            mandatory (query_class x source) search
                            completed successfully (R394 s2: a failed
                            mandatory search forbids the no-covering-art
                            claim this state makes)
    UNRESOLVED_SEARCH_INCOMPLETE  some mandatory search failed: the
                            searched universe is incomplete; findings
                            stand as evidence but NO position may be
                            claimed (R394 s2 — the state that replaces
                            the measured false RESOLVED_DIFFERENTIATED)
    UNRESOLVED_PARTIAL_EVIDENCE  families exist but at least one is stuck
                            at TITLE tier (evidence too thin to decide)
    UNRESOLVED_NO_RELEVANT_ART   searches succeeded, nothing relevant
                            (zero hits is NOT novelty — Art. XXI.2)
    UNRESOLVED_INSUFFICIENT_EVIDENCE  no search succeeded at all
                            (provider failures are not absence — Art. XXI.3)

    `precomputed` (R378 technical-improvement-engine re-adjudication
    path): a list of family records whose evidence was ALREADY fetched
    and custody-recorded ({family_id, representative: PatentHit,
    members, evidence_tier, fam_text, claims_fetch_status,
    claims_fetch_path}). When supplied, the network fetch is skipped and
    the CACHED evidence text/tier is re-adjudicated against the GIVEN
    profile — the same state machine, same thresholds, one authority
    (Art. X). The caller records collision_mode=REPLAY_CACHE; the
    artifact discloses that the SEARCH was cached while the
    ADJUDICATION re-ran (CEO improvement-engine rule 11: re-run the
    checks — never inherit the parent's score).
    """
    per_family: List[Dict[str, Any]] = []
    # R394 section 2: the mandatory-search gate. `search_incomplete`
    # may be supplied by callers that replay precomputed evidence (the
    # searches were NOT re-run; the recorded completeness governs).
    search_incomplete = (search_incomplete
                         if search_incomplete is not None
                         else bool(search_errors))
    if precomputed is not None:
        for fam in precomputed:
            rep: PatentHit = fam["representative"]
            tier = str(fam.get("evidence_tier") or "TITLE")
            fam_text = str(fam.get("fam_text") or "")
            cov = coverage_decision(profile, fam_text)
            per_family.append({
                "family_id": fam.get("family_id"),
                "representative": {
                    "patent_id": rep.patent_id, "title": rep.title[:140],
                    "source_id": rep.source_id,
                    "source_url": rep.source_url,
                    "assignee": rep.assignee,
                    "publication_date": rep.publication_date},
                "family_size": len(fam.get("members") or []),
                "member_patent_ids": [m.patent_id for m in
                                      (fam.get("members") or [])],
                "evidence_tier": tier,
                "claims_fetch_status": fam.get("claims_fetch_status"),
                "claims_fetch_path": fam.get("claims_fetch_path"),
                "adjudicated_text_excerpt": fam_text[:1200],
                "adjudicated_text_sha256": __import__("hashlib").sha256(
                    fam_text.encode("utf-8", errors="ignore")).hexdigest(),
                "coverage": cov,
            })
        families = []
    else:
        for fam in families:
            rep: PatentHit = fam["representative"]
            claims = (fetch_claim_evidence(rep.patent_id, rep)
                      if deep_fetch else {"fetch_status": "NOT_ATTEMPTED"})
            tier = evidence_tier(rep, claims)
            fam_text = family_text(rep, claims)
            cov = coverage_decision(profile, fam_text)
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
                "claims_fetch_path": claims.get("fetch_path"),
                # R377: the ADJUDICATED TEXT the coverage decision measured
                # against, hash-custodied — auditability (the coverage class
                # is now verifiable from the artifact alone) and instrument
                # measurability (I4 pair-novelty needs the family text on
                # the artifact, not just the title)
                "adjudicated_text_excerpt": fam_text[:1200],
                "adjudicated_text_sha256": __import__("hashlib").sha256(
                    fam_text.encode("utf-8", errors="ignore")).hexdigest(),
                "coverage": cov,
            })
    tiers = [f["evidence_tier"] for f in per_family]
    full_cover = [f for f in per_family
                  if f["coverage"]["coverage_class"] == "FULL_COVER"]
    tier_rank = {"TITLE": 0, "ABSTRACT": 1, "CLAIMS": 2}
    # R394 s2 state machine — the order is load-bearing:
    #   1. a KILL (anticipation) may stand on found art even when the
    #      search was incomplete (more search cannot un-find covering
    #      art; the incompleteness is disclosed alongside);
    #   2. any mandatory-search failure FORBIDS the positive
    #      differentiation claim (UNRESOLVED_SEARCH_INCOMPLETE);
    #   3. only then do tier/resolution checks apply.
    if full_cover and all(tier_rank[t] >= 1 for t in tiers):
        state = "RESOLVED_ANTICIPATED"
    elif search_incomplete and searches_succeeded:
        state = "UNRESOLVED_SEARCH_INCOMPLETE"
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
        "search_errors": search_errors[:12],
        "search_execution": {
            "mandatory_complete": not search_incomplete,
            "n_errors": len(search_errors),
            "rule": ("RESOLVED_DIFFERENTIATED requires every mandatory "
                     "(query_class x source) search to have completed "
                     "successfully (R394 s2); provider failure never "
                     "becomes absence (Art. XXI.3)"),
        },
        "relevance_model_version": RELEVANCE_MODEL_VERSION,
        "determinism_contract": {
            "inputs": ("problem + candidate profile + query ladder + "
                       "source results (per-family adjudicated text, "
                       "hash-custodied) + thresholds + relevance model "
                       "version"),
            "check": ("identical inputs must yield identical coverage "
                      "decisions and state; divergence on replay is "
                      "FLAG_INCONSISTENT_RETRIEVAL (R394 s3)"),
        },
        "thresholds": THRESHOLDS,
    }
    if state == "RESOLVED_ANTICIPATED":
        resolution["anticipated_by"] = [
            f["family_id"] for f in full_cover]
        resolution["kill_semantics"] = (
            "specific-disclosure-class evidence found by search; "
            "CLASSIFY treats this as a prior-art kill with the evidence "
            "recorded here")
        if search_incomplete:
            resolution["search_incomplete_disclosure"] = (
                "the kill stands on the found covering family (found art "
                "is art regardless of other searches); other mandatory "
                "searches FAILED and are recorded in search_errors — "
                "the search universe is incomplete, which only matters "
                "for absence/differentiation claims (R394 s2)")
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

def _determinism_block(mechanism_map: Dict[str, Any],
                       problem: Dict[str, Any],
                       resolution: Dict[str, Any]) -> Dict[str, Any]:
    """R396 P6 — build the run-record determinism block (pure call into
    prior_art_v2.determinism; ledger failures are disclosed inside the
    block, never fatal to the collision itself)."""
    from discovery_fabric.prior_art_v2 import determinism as det
    return det.record_and_compare(
        fingerprint=det.problem_fingerprint(problem, mechanism_map),
        verdict=str(resolution.get("state") or ""),
        relevance_model_version=str(
            resolution.get("relevance_model_version") or ""),
        evset_identity=det.evidence_set_identity(resolution),
        run_id=str(problem.get("problem_id") or ""))


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
    term_collisions = [h for h, a in zip(hits, adjudications)
                       if a["verdict"] == "CROSS_DOMAIN_TERM_COLLISION"]
    families = cluster_families(relevant, adjudications)
    # R394 s2: 'searches_succeeded' now means AT LEAST ONE mandatory
    # (query_class x source) pair completed without error — hit count is
    # irrelevant to execution success. The old `bool(hits) or not
    # errors` made a single surviving query 'succeed' the entire search
    # while five mandatory pairs had failed (measured on production,
    # ts_d1ab9fd4d756: RESOLVED_DIFFERENTIATED with 5/10 errors).
    sources_used = sources or ["google_patents", "lens_patent"]
    n_pairs = len(ladder) * len(sources_used)
    searches_succeeded = n_pairs > 0 and len(errors) < n_pairs
    mandatory = mandatory_searches_complete(errors, ladder, sources_used)
    resolution = resolve_differentiation(
        families, profile, errors, searches_succeeded,
        deep_fetch=deep_fetch,
        search_incomplete=not mandatory["complete"])

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
    elif errors and not searches_succeeded:
        novelty_risk = "UNRESOLVED_INSUFFICIENT_EVIDENCE"
    elif errors:
        novelty_risk = "UNRESOLVED_SEARCH_INCOMPLETE"
    elif searches_succeeded:
        novelty_risk = "SEARCHED_NO_DIRECT_TITLE_MATCH"
    else:
        novelty_risk = "UNRESOLVED_INSUFFICIENT_EVIDENCE"

    return {
        "strategy": "mechanism-centered multi-query (R376; R377 adds the "
                    "FUNCTION class, entity-anchored cross-domain "
                    "precision, canonical claims fetch + Lens full "
                    "abstract)",
        "query_ladder": ladder,
        "candidate_profile": {
            "entity_terms": profile.entity_terms,
            "mechanism_terms": profile.mechanism_terms,
            "distinguishing_terms": profile.distinguishing_terms,
            "function_terms": profile.function_terms,
            "adjacent_terms": profile.adjacent_terms,
        },
        "patent": {
            "sources": (sources or ["google_patents", "lens_patent"]),
            "metered_sources": {
                "patentbear": {
                    "policy": ("OPT-IN since R378 (CEO directive: "
                               "'Use PatentBear for patents'); queried "
                               "only when listed in sources; persistent "
                               "quota guard with reserve floor "
                               "(patentbear_meter.json)"),
                    "not_queried_when_absent":
                        ("metered-source policy — not spent on default "
                         "collision search (K-series)")},
            },
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
            "cross_domain_term_collisions": [
                {"patent_id": h.patent_id, "title": h.title,
                 "source_id": h.source_id,
                 "query_class": h.query_class,
                 "overlap_terms": next(
                     (a["mechanism_overlap_terms"] for a in adjudications
                      if a["patent_id"] == h.patent_id), [])}
                for h in term_collisions],
            "cross_domain_collision_note": (
                "R377: demoted with recorded terms — mechanism overlap "
                "without entity overlap and below the non-generic bar "
                "is a term collision, not prior art (measured: 40% of "
                "R376 family reps were collisions)"),
        },
        "families": [{
            "family_id": f["family_id"],
            "family_size": len(f["members"]),
            "member_patent_ids": [m.patent_id for m in f["members"]],
        } for f in families],
        "mandatory_searches": mandatory,
        "differentiation_resolution": resolution,
        # R396 P6: the run-record determinism block — verdict,
        # relevance model version, relevant-evidence-set identity,
        # variance summary vs identical prior replays, and the
        # DETERMINISTIC / NON_DETERMINISTIC / BASELINE_RUN class
        "determinism": _determinism_block(mechanism_map, problem,
                                          resolution),
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


# ---------------------------------------------------------------------------
# R394 section 3 — deterministic relevance: the replay-consistency check
# ---------------------------------------------------------------------------

def check_replay_consistency(mechanism_map: Dict[str, Any],
                             problem: Dict[str, Any],
                             recorded_resolution: Dict[str, Any],
                             ) -> Dict[str, Any]:
    """Re-run the deterministic adjudication over a RECORDED resolution
    and compare. R394 section 3:

      'Same problem + source snapshot + retrieval query +
       relevance-model version + threshold must yield the same
       relevance decision... If two identical runs produce different
       evidence judgments from identical evidence: FLAG_INCONSISTENT_
    RETRIEVAL. Do not silently choose one.'

    The relevance decision is a pure function of (candidate profile,
    per-family adjudicated text, thresholds, model version). This check
    rebuilds the profile from the recorded mechanism map, re-derives the
    coverage decision for every recorded family from its custody-hashed
    adjudicated text, and compares against the recorded decisions.

    Returns {consistent: bool, flag: FLAG_INCONSISTENT_RETRIEVAL|None,
    divergences: [...]}. PURE FUNCTION — no network, no LLM, no clock.
    """
    profile = build_candidate_profile(mechanism_map, problem)
    recorded_version = recorded_resolution.get("relevance_model_version")
    divergences: List[Dict[str, Any]] = []

    if recorded_version != RELEVANCE_MODEL_VERSION:
        divergences.append({
            "field": "relevance_model_version",
            "recorded": recorded_version,
            "recomputed": RELEVANCE_MODEL_VERSION,
            "basis": ("the recorded decision was produced by a different "
                      "relevance model — not comparable without the "
                      "recorded model's code (disclosed, not silently "
                      "re-judged)"),
        })

    for fam in (recorded_resolution.get("per_family") or []):
        fam_text = str(fam.get("adjudicated_text_excerpt") or "")
        cov_rec = fam.get("coverage") or {}
        cov_new = coverage_decision(profile, fam_text)
        for key in ("coverage_class", "coverage_ratio",
                    "distinguishing_terms_surviving"):
            a, b = cov_rec.get(key), cov_new.get(key)
            if a != b:
                divergences.append({
                    "family_id": fam.get("family_id"),
                    "field": f"coverage.{key}",
                    "recorded": a,
                    "recomputed": b,
                    "basis": ("identical profile + identical custody-"
                              "hashed family text produced a different "
                              "relevance decision — the determinism "
                              "contract is violated"),
                })
        # custody check: the excerpt must still hash to the recorded
        # sha256 (truncation caveat: the excerpt is capped at 1200 chars
        # so the hash binds the EXCERPT, disclosed as such)
        recorded_sha = fam.get("adjudicated_text_sha256")
        if recorded_sha:
            import hashlib as _h
            recomputed_sha = _h.sha256(
                fam_text.encode("utf-8", errors="ignore")).hexdigest()
            if recomputed_sha != recorded_sha:
                divergences.append({
                    "family_id": fam.get("family_id"),
                    "field": "adjudicated_text_sha256",
                    "recorded": recorded_sha,
                    "recomputed": recomputed_sha,
                    "basis": "the adjudicated text changed after the "
                             "decision was recorded",
                })

    consistent = not divergences
    return {
        "consistent": consistent,
        "flag": None if consistent else "FLAG_INCONSISTENT_RETRIEVAL",
        "n_divergences": len(divergences),
        "divergences": divergences[:20],
        "relevance_model_version": RELEVANCE_MODEL_VERSION,
        "rule": ("identical inputs must yield identical relevance "
                 "decisions; any divergence is FLAGGED, never silently "
                 "resolved (R394 s3)"),
    }

"""Query expansion — mechanism terms, synonyms, cross-domain terminology.

Directive section 6: escape terminology lock-in. The LLM (or any
external generator) MAY propose query variants; it may NEVER
manufacture a retrieved source — every record must originate from an
actual source adapter with source-level provenance (enforced by tests:
the pipeline only ingests SourceQueryResult.records).

Constitutional anchor — Art. XLIII (search-space neutrality): every
variant carries its derivation class; solution-class injection is
explicitly marked EXPLORATORY_HYPOTHESIS (never DERIVED_FROM_EVIDENCE
unless the evidence snapshot contains the term).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# Reuse the existing deterministic table (no second factory, Art. XXXIV):
# FUNCTION_EQUIV_EXPANSION lives in engine/adapters.py. R515: the
# ADJACENT_INDUSTRY_MAP + DEFAULT_ADJACENT tables moved HERE from
# engine/adapters.py — the R513 closure retired them from adapters
# with the MSD removal but query_expansion.py (the live RETRIEVE
# path's adjacent-industry expansion, line ~180) is their sole
# remaining consumer. Values byte-identical to the retired copies
# (zero semantic change; completes the closure's retirement).
from discovery_fabric.engine.adapters import FUNCTION_EQUIV_EXPANSION

ADJACENT_INDUSTRY_MAP = {
    "valve": ["automotive fluid systems", "aerospace hydraulics"],
    "sensor": ["automotive sensing", "industrial instrumentation"],
    "battery": ["consumer electronics power", "automotive energy"],
    "coating": ["marine anti-fouling", "medical device surfaces"],
    "catheter": ["minimally invasive surgery", "interventional radiology"],
    "flow": ["process industry fluidics", "aerospace fuel systems"],
}
DEFAULT_ADJACENT = ["aerospace", "automotive", "industrial automation"]

#: domain-term translation table — terminology that DIFFERS between
#: domains for the same physical mechanism (measured need: the P13
#: case, where the decisive prior art used "dummy element" /
#: "matched dies" / "biopressure" where the problem statement said
#: "reference sensor" / "dual matched sensing elements"). Keys are
#: matched as substrings of the primary query, so fine-grained tokens
#: ("matched", "reference", "dummy") fire where full phrases would not.
CROSS_DOMAIN_TERMS: Dict[str, List[str]] = {
    "reference element": ["dummy element", "dummy resistor", "reference leg"],
    "reference sensor": ["dummy element", "reference die"],
    "reference": ["dummy element", "reference leg"],
    "dummy element": ["reference element", "compensation element"],
    "dummy": ["dummy element", "dummy resistor"],
    "matched elements": ["matched dies", "matched pair", "matched sensors"],
    "matched": ["matched dies", "matched pair"],
    "dual sensor": ["dual die", "twin sensor", "differential pair"],
    "dual": ["dual die", "differential pair"],
    "common mode": ["common-mode rejection", "common stress subtraction"],
    "drift compensation": ["thermal drift cancellation", "self-calibration",
                           "auto-zero"],
    "drift": ["thermal drift cancellation", "drift compensation"],
    "differential measurement": ["differential pair output",
                                 "cross-coupled outputs"],
    "biopressure": ["biomedical pressure", "physiological pressure"],
    "implantable sensor": ["in vivo sensor", "implanted transducer"],
    "shunt": ["cerebrospinal fluid diversion", "CSF shunt", "ventricular drain"],
    "valve": ["regulator", "flow control element"],
    "obstruction": ["occlusion", "blockage", "occluded catheter"],
    "catheter": ["cannula", "drainage tube"],
    "fouling": ["biofouling", "deposition", "ingrowth"],
    "sensor": ["transducer", "detector"],
    "pressure": ["intracranial pressure", "ICP", "hydrostatic pressure"],
    "flow": ["perfusion", "fluid transport", "volumetric flow rate"],
    "battery": ["energy harvester", "power scavenging"],
    "wireless power": ["inductive coupling", "RF harvesting", "telemetry power"],
    "antenna": ["implant antenna", "miniaturized radiator"],
}

#: historical terminology (older literature uses different words for the
#: same mechanism — directive: historical terminology expansion)
HISTORICAL_TERMS: Dict[str, List[str]] = {
    "sensor": ["transducer", "pick-up", "sensing element"],
    "monitoring": ["telemetry", "surveillance"],
    "implantable": "indwelling implanted".split(),
    "intracranial pressure": ["ICP", "cerebrospinal fluid pressure"],
    "programmable valve": ["adjustable valve", "variable orifice valve"],
}


def _keyword_pairs(text: str,
                   table: Dict[str, List[str]]) -> List[tuple]:
    """(key, values) pairs whose key matches the text as a substring —
    used where the VALUES must be looked up from the matched KEY (the
    cross-domain/historical tables)."""
    t = (text or "").lower()
    out: List[tuple] = []
    for k, vs in table.items():
        if k in t:
            out.append((k, vs))
    return out


def _keyword_hits(text: str, table: Dict[str, List[str]]) -> List[str]:
    t = (text or "").lower()
    out: List[str] = []
    for k, vs in table.items():
        if k in t:
            out.extend(v for v in vs if v not in out)
    return out


def mechanism_query(problem: Dict[str, Any]) -> str:
    """The PRIMARY query — derived ONLY from problem facts (device +
    failure mode), per Art. XLIII. No solution-class terms injected."""
    fm = problem.get("failure_mode", "") or ""
    device = problem.get("device", "") or ""
    q = f"{device} {fm.lower().replace('_', ' ')}".strip()
    return " ".join(q.split())


_STOPWORDS = frozenset(
    "a an the and or of to in on for with by from as at is are was were be "
    "been being that this these those it its into over under must shall "
    "should may can will would than then so such not no nor only same "
    "their there when where which while who whom why how all any both each "
    "few more most other some own s t just don now during before after "
    "above below up down out off very using use used new existing via per"
    .split())

#: R6 A4 follow-up (measured 2026-11-12, live europepmc probes during the
#: composer-era DEV12 chunk 1 diagnosis): narrative PROGRESSION/temporal
#: prose words are weak search terms — the scholarly APIs AND every
#: term, and 'inner-race spalling progresses weeks vibration alarm trips
#: past repair' retrieved 0 records where 'inner-race spalling vibration
#: alarm' retrieved 10 (same failure text, junk verbs removed). Same
#: instrument class as _STOPWORDS / FUNCTION_EQUIV_EXPANSION (recorded
#: policy input, Art. XXVII); only verb/temporal forms measured harmful
#: are listed — equipment/mechanism nouns stay.
WEAK_QUERY_TERMS = frozenset(
    "progresses progressed progressing trips tripped "
    "weeks months past least"
    .split())


def _content_terms(text: str, exclude: str = "") -> List[str]:
    """Deterministic content-term extraction: lowercase tokens, stopwords
    and pure numbers dropped, hyphenated compounds kept whole, tokens
    already present in `exclude` (the primary query) dropped, order =
    first occurrence. Zero LLM, zero tables — the problem's OWN words
    (Art. XLIII: problem facts only, never solution-class injection).

    R6 A4 follow-up (measured 2026-11-12, chunk 1 of the composer-era
    DEV12 run): the exclusion matches WHOLE tokens only. The old rule
    hyphen-split the exclude string, so the primary's compound
    'bearing-spalling' hid the failure text's own strongest predictor
    term 'spalling' from the FAILURE_TEXT_TERMS variant — and the
    sentence-form primary retrieves 0 records on the scholarly APIs
    (measured live: the full sentence -> 0 on europepmc; 'inner race
    spalling vibration alarm' -> 10 on-domain records), so the hidden
    term was lost from EVERY effective query. A compound in the
    primary is a different search token from its parts; only a whole
    match excludes."""
    excl = frozenset(w.strip(",.;:()[]\"'?!/*")
                     for w in (exclude or "").lower().split())
    seen: set = set()
    out: List[str] = []
    for raw in (text or "").lower().replace("_", " ").split():
        tok = raw.strip(",.;:()[]\"'?!/*")
        if not tok:
            continue
        base = tok.replace("-", " ")
        if tok in seen or base in excl or tok in _STOPWORDS:
            continue
        if tok in WEAK_QUERY_TERMS:
            continue  # measured 0-record killer (see WEAK_QUERY_TERMS)
        if not any(ch.isalpha() for ch in tok):
            continue  # pure numbers/units are search-hostile noise
        if len(tok) < 3 and "-" not in tok:
            continue
        seen.add(tok)
        out.append(tok)
    return out


def failure_constraint_variants(problem: Dict[str, Any],
                                primary: str) -> List[Dict[str, Any]]:
    """R6 A4 (owner round 2026-11-12): queries refined from the failure
    text and the user constraint — the measured starvation cause.

    The primary query is `device + failure_mode` only; measured on the
    committed DEV pairs this is too thin: new02's failure_mode
    ('contact-wear') + a device string carrying search-hostile tokens
    ('1.5 MW', '1800 rpm') never surfaces the failure text's own
    mechanism vocabulary ('brush wear', 'arcing', 'open-circuit
    excitation'), and p05's failure_mode ('degradation') never carries
    'creep' / 'ozone cracking'. The failure and constraint texts ARE
    problem facts (Art. XLIII scope: problem facts, still no
    solution-class injection), so their content terms become explicit
    variants. Deterministic, zero LLM."""
    out: List[Dict[str, Any]] = []
    failure = (problem or {}).get("failure", "") or ""
    constraint = (problem or {}).get("constraint", "") or ""
    # R6 A4 follow-up (measured 2026-11-12 on the live europepmc API):
    # the term-count cliff is FIVE — 'inner race spalling vibration'
    # (4 terms) -> 10 records, '... alarm' (5) -> 10, a 6th term -> 0
    # (the scholarly APIs AND every term; the 8-term variant built
    # before this measurement returned 0 on every lane). Variants are
    # capped at the measured cliff, never past it.
    # Within the cap, DIGIT-BEARING terms sort first (stable): the
    # constraint's measurable bound ('75-year service life') is the
    # search-critical content and must never be the cap's casualty —
    # measured 2026-11-12 on bench-p05: first-occurrence order capped
    # the variant at 'hold vertical deflection percent design' and cut
    # the bound the variant exists to surface.
    def _digit_first(terms: List[str]) -> List[str]:
        return (sorted(terms, key=lambda t: (0 if any(
            ch.isdigit() for ch in t) else 1)) if terms else terms)

    fterms = _digit_first(_content_terms(failure, exclude=primary))[:5]
    if fterms:
        out.append({"query": " ".join(fterms),
                    "derivation_class": "FAILURE_TEXT_TERMS",
                    "derivation_basis":
                        "content terms of the problem's own failure text "
                        "(not already in the primary query as whole "
                        "tokens; digit-bearing measurable terms first, "
                        "capped at the measured 5-term cliff; Art. XLIII "
                        "problem facts)"})
    cterms = _digit_first(
        _content_terms(constraint,
                       exclude=f"{primary} {failure}"))[:5]
    if cterms:
        out.append({"query": " ".join(cterms),
                    "derivation_class": "CONSTRAINT_TARGETED",
                    "derivation_basis":
                        "content terms of the user constraint (the "
                        "measurable bound the evidence must speak to)"})
    return out


def expand_query(primary: str,
                 problem: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Generate query variants. Each variant is a dict:
      {query, derivation_class, derivation_basis}

    derivation_class vocabulary (honest, machine-checkable):
      PRIMARY               — problem facts verbatim (Art. XLIII)
      FAILURE_TEXT_TERMS    — content terms of the problem's failure text
                              (R6 A4: the measured starvation cause — the
                              primary is device+failure_mode only, too
                              thin on the committed DEV pairs)
      CONSTRAINT_TARGETED   — content terms of the user constraint (R6 A4:
                              the measurable bound the evidence must speak to)
      FUNCTION_EQUIV        — deterministic functional-equivalence table
      CROSS_DOMAIN_TERM     — cross-domain/historical terminology table
      ADJACENT_INDUSTRY     — cross-domain industry transfer
      DOMAIN_NARROW         — top mechanism keywords only (for
                              weak-ranking sources like CORE)
      COMPARISON_TARGETED   — the measured query-form learning (R412-V3
                              decomposition cause 1): the '{capability}
                              experimental comparison' form retrieves the
                              numeric-bearing comparative-experimental
                              document class; adopted per Art. LI
      EXPLORATORY_HYPOTHESIS — solution-class term NOT derived from
                              evidence; marked exploratory, never
                              counted as evidence-derived
    Cosmetic rewrites (case/order changes only) are filtered — a variant
    must differ in at least one content term (test-pinned).
    """
    variants: List[Dict[str, Any]] = []
    seen_tokens: set = set()

    def _add(query: str, cls: str, basis: str) -> None:
        q = " ".join((query or "").split())
        if not q:
            return
        toks = frozenset(q.lower().split())
        if toks in seen_tokens:
            return
        seen_tokens.add(toks)
        variants.append({"query": q, "derivation_class": cls,
                         "derivation_basis": basis})

    _add(primary, "PRIMARY", "problem facts: device + failure_mode")

    # R6 A4: failure-text and constraint-derived variants (problem facts,
    # Art. XLIII — measured starvation fix on the committed DEV pairs)
    for v in failure_constraint_variants(problem or {}, primary):
        _add(v["query"], v["derivation_class"], v["derivation_basis"])

    # FUNCTION_EQUIV expansions on the primary string
    equiv_hits = _keyword_hits(primary, FUNCTION_EQUIV_EXPANSION)
    for term in equiv_hits:
        replaced = primary
        for k, vs in FUNCTION_EQUIV_EXPANSION.items():
            if k in primary.lower() and term in vs:
                replaced = primary.lower().replace(k, term)
                break
        _add(replaced, "FUNCTION_EQUIV",
             f"functional-equivalence of '{term}' (engine adapters table)")

    # CROSS_DOMAIN_TERM expansions: each matched key produces variants
    # substituting its alternative terminology
    cd_pairs = _keyword_pairs(primary, CROSS_DOMAIN_TERMS)
    for key, repls in cd_pairs[:4]:
        for repl in repls[:2]:
            replaced = primary.lower().replace(key, repl)
            _add(replaced, "CROSS_DOMAIN_TERM",
                 f"cross-domain terminology: '{key}' -> '{repl}'")
    if cd_pairs:
        appended = primary
        for key, repls in cd_pairs[:2]:
            alts = [r for r in repls[:2] if r not in primary.lower()]
            appended = f"{appended} {' '.join(alts)}".strip()
        _add(appended, "CROSS_DOMAIN_TERM",
             "primary + alternative terminology for measured-ambiguous "
             "mechanism terms")

    # HISTORICAL terminology
    hist_pairs = _keyword_pairs(primary, HISTORICAL_TERMS)
    for key, repls in hist_pairs[:2]:
        for repl in repls[:2]:
            _add(primary.lower().replace(key, repl), "CROSS_DOMAIN_TERM",
                 f"historical terminology: '{key}' -> '{repl}'")

    # ADJACENT_INDUSTRY transfer queries (from the problem's device)
    device = (problem or {}).get("device", "") or ""
    industries = _keyword_hits(device, ADJACENT_INDUSTRY_MAP) or DEFAULT_ADJACENT
    mechanism_core = " ".join(primary.lower().split()[:3])
    for ind in industries[:3]:
        _add(f"{mechanism_core} {ind}", "ADJACENT_INDUSTRY",
             f"cross-domain transfer to '{ind}' (adjacent-industry map)")

    # COMPARISON_TARGETED: the R412-V3 measured learning, adopted
    # forward (Art. LI: negative knowledge must change future search).
    # The V3 gate-fail decomposition (R412/GRADIENT_V3/RUN/
    # GATE_FAIL_DECOMPOSITION.json, cause 1) measured that the query
    # FORM is the dominant retrieval variable for numeric-bearing
    # evidence: the comparison-targeted form ('{capability}
    # experimental comparison') outperformed all three sealed lane
    # forms on reference recall (the 12 unmatched numeric-bearing
    # records were europepmc/core-indexed). Mechanism: the form
    # selects for comparative-experimental literature — the document
    # class that carries measured values. This is a DERIVED-from-
    # measurement query variant, not a solution-class injection (Art.
    # XLIII: it adds no mechanism/technology term — only the
    # document-class selector).
    base = " ".join(primary.lower().split()[:6])
    if len(base.split()) >= 2:
        _add(f"{base} experimental comparison",
             "COMPARISON_TARGETED",
             "measured query-form learning (R412/GRADIENT_V3/RUN/"
             "GATE_FAIL_DECOMPOSITION.json cause 1: the comparison-"
             "targeted form retrieves the numeric-bearing comparative-"
             "experimental document class; adopted per Art. LI)")

    # DOMAIN_NARROW: short keyword form for weak-ranking sources
    # (measured: CORE's long-query behavior matched 9.7M works)
    narrow_terms = [primary.split()[0]] if primary.split() else []
    for key, repls in cd_pairs[:2]:
        narrow_terms.extend(r for r in repls[:1] if r not in narrow_terms)
    if len(narrow_terms) >= 2:
        _add(" ".join(narrow_terms[:4]), "DOMAIN_NARROW",
             "short keyword form for weak-ranking repository sources "
             "(measured CORE behavior)")

    return variants


def llm_expand(primary: str, llm_generate=None) -> List[Dict[str, Any]]:
    """OPTIONAL LLM query expansion. The LLM may propose query variants
    ONLY — every returned variant is labeled LLM_PROPOSED and must still
    pass the no-fabrication gate: it is a query STRING, never a record.
    Returns [] when no transport is available (hermetic default)."""
    if llm_generate is None:
        return []
    prompt = (
        "You are expanding a scientific discovery search query into "
        "genuinely different retrieval terms. Mechanism-level synonyms, "
        "cross-domain engineering terminology, biological terminology, and "
        "historical terminology only. Return a JSON array of strings; "
        "each string must be a search query, NOT a document, citation, "
        "identifier or claim. No document titles. No DOIs. No inventing "
        "sources.\n"
        f"PRIMARY QUERY: {primary}\n"
        'RESPOND WITH: {"queries": ["...", "..."]} (max 6 queries)'
    )
    try:
        out = llm_generate(prompt)
    except Exception:
        return []
    import json as _json
    try:
        data = _json.loads(out) if isinstance(out, str) else out
        queries = data.get("queries", []) if isinstance(data, dict) else []
    except Exception:
        return []
    variants: List[Dict[str, Any]] = []
    seen = frozenset(primary.lower().split())
    for q in queries[:6]:
        if not isinstance(q, str) or not q.strip():
            continue
        toks = frozenset(q.lower().split())
        if toks == seen or not toks:
            continue
        # no-fabrication gate: reject anything that looks like a record
        # (DOIs / patent numbers anywhere in the string) — the LLM
        # proposes TERMS, never records
        import re as _re
        looks_like_record = (
            _re.search(r"10\.\d{4,}\s*/", q)
            or _re.search(r"\b(?:US|EP|WO|CN|JP|DE|FR|GB)\s?\d{6,}\w*\b", q,
                          _re.I)
            or any(tok.startswith("10.") for tok in q.split()))
        if looks_like_record:
            continue
        variants.append({"query": " ".join(q.split()),
                         "derivation_class": "LLM_PROPOSED",
                         "derivation_basis": "LLM query expansion "
                         "(terms only; never records — pipeline ingests "
                         "only adapter results)"})
        seen = toks
    return variants

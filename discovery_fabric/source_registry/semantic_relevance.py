"""SEMANTIC_RELEVANCE v1 — the Phase-P1 relevance instrument.

Lands the reinstatement criterion the source registry has recorded since
R399 W3: "the Phase P1 semantic reranker lands (semantic relevance
adjudication between query and record, replacing lexical overlap)".

Why this instrument exists (the measured defect it closes):
  The R452 frozen assay (R452/DISCOVERY_QUALITY_MEASUREMENT.json, shim
  sha 2ed92827...) measured the lexical TEXT_TERM_OVERLAP gate admitting
  OpenFOAM prompt-template boilerplate as RELEVANT evidence for four
  unrelated problems — the shared terms were ["problem", "state"] and
  ["deep", "model", "problem", "state"]: generic vocabulary, zero domain
  content. The audit (EXT-AUDIT-LEAN-R454) measured evidence-relevance
  rates of 0.115 / 0.333 / 0.706 / 0.095 with ANALOGY-dominated pools
  and zero good discoveries, and named relevance as the live bottleneck:
  "the machine currently rejects 12 of 12 evidence records with a
  keyword-overlap test and calls that an evidence base" (false negatives)
  while the frozen records show the same gate admitting boilerplate
  (false positives). Both failure classes come from the same cause:
  raw term overlap has no notion of how DISCRIMINATIVE a shared term is.

What this instrument is:
  A deterministic, stdlib-only, network-free relatedness scorer between
  a query/problem text and a record text, with three declared components:

    term_mass  (w=0.55) — IDF-weighted soft coverage of the query's
        informative core (the MASS_TOP_K highest-weight query terms).
        A core term is matched when it appears in the record (exact
        after plural folding) OR when its character-trigram best match
        among the record's terms reaches SOFT_MATCH_SIMILARITY
        (morphological variants: biofouling/fouling,
        embrittlement/embrittle). Term weights are the declared
        generic penalty (word property, always applied) MULTIPLIED by
        inverse document frequency over the record pool being
        adjudicated (pool-relative; disclosed per decision); pools
        smaller than MIN_POOL_FOR_IDF use pure weights (generic 0.25,
        content 1.0).
    trigram_coverage (w=0.35) — DIRECTIONAL query-side coverage over
        content-term char-trigram sets: how much of the query's
        morphology the record echoes. (A symmetric cosine was rejected
        in calibration: unrelated long texts share a ~0.45 floor of
        derivational morphology, drowning the bands.)
    phrase_bonus (w=0.10) — shared adjacent content-term pairs (bigrams:
        "thermal runaway", "shunt valve"), capped — a domain phrase is
        stronger evidence than two independent unigram hits, but it
        must not dominate.

  Composite score s = W_TERM_MASS*term_mass + W_TRIGRAM*trigram_coverage
  + W_PHRASE*phrase_bonus, banded:

    s >= RELEVANT_FLOOR   -> RELEVANT
    s >= WEAK_FLOOR       -> WEAK_RELEVANCE (kept in custody, NOT
                             admitted — the gray zone is never silently
                             resolved)
    else                  -> REJECTED

Threshold provenance (Art. XXVII — declared, not invented):
  Class: ENGINEERING (an instrument threshold about the engine's
  evidence-consumption needs, not a claim about providers).
  Justification: the committed calibration corpus
  (discovery_fabric/source_registry/RELEVANCE_CORPUS_R456.json — labels
  authored from problem facts BEFORE the scorer was run, Art. VIII)
  measured a separated band structure: the off-domain collision class
  (tire-pressure, ML-paper, pool-chemistry, and the REAL frozen R452
  prompt-template records) scores <= 0.16; the adjacent-domain gray
  zone (same material, wrong layer of the stack; single shared rare
  term) scores 0.28-0.356; on-domain records score >= 0.39. The floors
  0.36 / 0.18 sit inside the measured gaps. The corpus is the
  development set (Art. LIX: tuning happened there, and nowhere else);
  the frozen R452 assay records are held out and reported as the
  experiment result, never tuned on.

Metamorphic contract (Art. V, declared): a surface paraphrase of a
  record must not move its verdict more than ONE band step, and must
  never flip REJECTED <-> RELEVANT directly. The calibration corpus
  pins both directions (positive and negative pairs).

Constitutional anchors:
  - Art. XXI.4: relevance is established per record; every decision
    carries its basis (score components, matched terms, IDF source).
  - Art. II/III: this is a RELEVANCE gate on retrieval quality — it
    never touches span-verbatim verification (the VERIFY stage is
    unchanged) and never upgrades a record's evidentiary class.
  - Art. V: fail closed, but not a universal rejector — the corpus
    pins positives that MUST admit and negatives that MUST reject.
  - Art. XXV: WEAK and REJECTED records stay in custody; a rejection
    is a recorded decision with its basis, never a silent drop.
  - Art. IV: no fallback epistemology — this instrument is total (it
    scores any input deterministically); the lexical overlap is one
    reported COMPONENT of its basis, not a separate weaker path.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

__version__ = "SEMANTIC_RELEVANCE_V1"

#: the corpus-provenance marker embedded in every recorded basis (a
#: test pins that the string survives — the threshold's justification
#: must be reconstructable from any single decision record)
CORPUS_PROVENANCE = "RELEVANCE_CORPUS_R456"

# ---------------------------------------------------------------------------
# Declared instrument constants (Art. XXVII provenance above)
# ---------------------------------------------------------------------------

RELEVANT_FLOOR = 0.36
WEAK_FLOOR = 0.18
W_TERM_MASS = 0.55
W_TRIGRAM = 0.35
W_PHRASE = 0.08
SOFT_MATCH_SIMILARITY = 0.82
MIN_POOL_FOR_IDF = 8
#: mass denominator = the K highest-weight query terms (the query's
#: informative core). Calibration finding: full-coverage mass dilutes
#: a long problem statement (25+ content terms) until genuine domain
#: matches cannot clear any floor; relevance is carried by the
#: query's discriminative core, not by its entire prose.
MASS_TOP_K = 8

#: declared generic vocabulary — engine/boilerplate words that appear in
#: prompt templates, abstracts, and problem statements alike. They carry
#: the minimum weight wherever they appear (the measured false-positive
#: class shared exactly these words: problem, state, deep, model).
GENERIC_TERMS = frozenset("""
problem problems state states model models deep system systems method
methods device devices expert knowledge result results case cases study
studies analysis data time high low used using based performance effect
effects process design design control test testing value values level
levels rate rates number different various several multiple important
significant approach technique application field area condition
conditions feature features type types form forms range set sets work
works provide provides ensure ensures include includes follow follows
new novel improve improved improvement reduce reduces input output
first second third however therefore also thus such same other another
""".split())

#: the shared tokenization/fold rule family (the same fold query_relevance
#: applies: ies->y, trailing-s strip — disclosed in both modules)
_STOPWORDS = frozenset("""
the a an of in for and or to with on by at from is are was were be been
it its this that these those as into their there they them has have had
will would can could should may might not no than then when where which
while what who how why
""".split())


def fold(term: str) -> str:
    """Deterministic plural folding (same rule family as
    query_relevance._fold; kept self-contained to avoid an import
    cycle — the two modules disclose each other's rule)."""
    if len(term) > 3 and term.endswith("ies"):
        return term[:-3] + "y"
    if len(term) > 3 and term.endswith("s") and not term.endswith("ss"):
        return term[:-1]
    return term


def content_terms(text: str) -> List[str]:
    """Content terms of a text: folded, stopword-stripped, >2 chars."""
    return [fold(t) for t in re.findall(r"[a-z0-9]+", (text or "").lower())
            if len(t) > 2 and t not in _STOPWORDS]


def _trigrams(text: str) -> Counter:
    norm = re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()
    if len(norm) < 3:
        return Counter({norm: 1}) if norm else Counter()
    grams: Counter = Counter()
    compact = norm.replace(" ", "  ")
    for i in range(len(compact) - 2):
        grams[compact[i:i + 3]] += 1
    return grams


def _trigram_set(text: str) -> set:
    """Distinct char-trigram set over the (content-term) text — the
    unit of the directional coverage component."""
    norm = re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()
    if not norm:
        return set()
    compact = norm.replace(" ", "  ")
    return {compact[i:i + 3] for i in range(max(0, len(compact) - 2))}


def _trigram_sim(a: str, b: str) -> float:
    """Char-trigram Dice-style similarity between two terms."""
    if a == b:
        return 1.0
    ga, gb = _trigrams(a), _trigrams(b)
    if not ga or not gb:
        return 0.0
    inter = sum(((ga & gb)).values())
    total = sum(ga.values()) + sum(gb.values())
    if total == 0:
        return 0.0
    return 2.0 * inter / total


def pool_idf(pool_texts: Optional[Sequence[str]]) -> Dict[str, float]:
    """IDF weights from the adjudication pool (deterministic, disclosed).

    idf(t) = log((N+1)/(df+0.5)) / log(N+1), clamped to [0.15, 1.0].
    A term in every pool record (df == N, the boilerplate signature)
    collapses toward the clamp floor; a term in one record carries
    ~full weight. Pools smaller than MIN_POOL_FOR_IDF use the declared
    static fallback (generic 0.25 / content 1.0) — disclosed as
    "static_fallback" in the decision basis.
    """
    texts = [t for t in (pool_texts or []) if t]
    n = len(texts)
    if n < MIN_POOL_FOR_IDF:
        return {}
    df: Counter = Counter()
    for t in texts:
        df.update(set(content_terms(t)))
    denom = math.log(n + 1)
    out: Dict[str, float] = {}
    for term, c in df.items():
        raw = math.log((n + 1) / (c + 0.5)) / denom if denom > 0 else 1.0
        out[term] = min(1.0, max(0.15, raw))
    return out


def _weight(term: str, idf: Dict[str, float]) -> float:
    """Final term weight: the declared generic penalty (word property,
    always applied) MULTIPLIED by the pool IDF (measured context).
    Composition, not fallback: the calibration corpus showed generic
    words can carry high pool IDF when the pool is small and lacks
    them — the declared list must hold regardless of pool composition."""
    w = idf.get(term, 1.0) if idf else 1.0
    if term in GENERIC_TERMS:
        w *= 0.25
    return w


def _term_mass(qterms: List[str], qweights: Dict[str, float],
               rterm_set: set, rterm_list: List[str],
               rterm_grams: Dict[str, Counter],
               idf: Dict[str, float]) -> Tuple[float, List[str], List[str]]:
    """IDF-weighted soft coverage of the query's informative core (the
    MASS_TOP_K highest-weight query terms) by the record terms.

    Returns (mass in [0,1], exact_matches, soft_matches)."""
    if not qterms:
        return 0.0, [], []
    core = [t for t, _ in sorted(qweights.items(), key=lambda kv: -kv[1])
            if t in qterms][:MASS_TOP_K]
    if not core:
        core = qterms[:MASS_TOP_K]
    total_w = sum(qweights.get(t, 1.0) for t in core)
    matched_w = 0.0
    exact: List[str] = []
    soft: List[str] = []
    for t in core:
        w = qweights.get(t, 1.0)
        if t in rterm_set:
            matched_w += w
            exact.append(t)
            continue
        # soft match: best trigram similarity against the record terms
        # (only content-bearing record terms are indexed)
        best = 0.0
        best_term = ""
        tg = _trigrams(t)
        for rt in rterm_list:
            if abs(len(rt) - len(t)) > max(4, len(t) // 2):
                continue
            cached = rterm_grams.get(rt)
            if cached is None:
                cached = _trigrams(rt)
                rterm_grams[rt] = cached
            inter = sum((tg & cached).values())
            tot = sum(tg.values()) + sum(cached.values())
            sim = (2.0 * inter / tot) if tot else 0.0
            if sim > best:
                best, best_term = sim, rt
        if best >= SOFT_MATCH_SIMILARITY:
            matched_w += w * best
            soft.append(f"{t}~{best_term}")
    mass = matched_w / total_w if total_w else 0.0
    return min(1.0, mass), exact, soft


def _query_coverage(qtext_trigrams: set, rtext_trigrams: set) -> float:
    """Directional query-side trigram coverage: how much of the query's
    content-term morphology the record echoes.

    Calibration finding: a symmetric cosine over content-term trigrams
    carries a ~0.45 floor between UNRELATED long English texts (shared
    derivational morphology: -tion/-ing/-ent fragments), which drowned
    the band separation. The directional measure scores the record
    against the query's own trigram set — an unrelated record shares
    almost none of it, while a paraphrasing record echoes much of it."""
    if not qtext_trigrams:
        return 0.0
    inter = len(qtext_trigrams & rtext_trigrams)
    return inter / len(qtext_trigrams)


def _phrase_bonus(qterms: List[str], rtext_norm: str) -> Tuple[float, List[str]]:
    """Shared adjacent content-term pairs (bigrams), capped contribution."""
    hits: List[str] = []
    for i in range(len(qterms) - 1):
        bg = f"{qterms[i]} {qterms[i + 1]}"
        if bg in rtext_norm:
            hits.append(bg)
    # cap: 3 phrases at full credit, the rest ignored (declared cap)
    return min(1.0, len(hits) / 3.0), hits[:3]


def semantic_score(query_text: str, record_text: str,
                   pool_texts: Optional[Sequence[str]] = None
                   ) -> Dict[str, Any]:
    """Score one query/record pair. Deterministic; total (never raises
    on empty input — an empty side scores 0)."""
    qtext = query_text or ""
    rtext = record_text or ""
    qterms = content_terms(qtext)
    # dedupe preserving order (a repeated query term must not multiply
    # its own weight — the measured boilerplate class echoed few terms)
    seen: set = set()
    qterms = [t for t in qterms if not (t in seen or seen.add(t))]
    rterms = content_terms(rtext)
    rterm_set = set(rterms)
    rnorm = re.sub(r"[^a-z0-9]+", " ", rtext.lower())

    idf = pool_idf(pool_texts)
    idf_source = "pool_idf" if idf else "static_fallback"
    qweights = {t: _weight(t, idf) for t in qterms}

    rterm_grams: Dict[str, Counter] = {}
    mass, exact, soft = _term_mass(qterms, qweights, rterm_set, rterms,
                                   rterm_grams, idf)
    # the trigram component is DIRECTIONAL query-side coverage over
    # content-term trigram SETS (see _query_coverage for the measured
    # reason the symmetric cosine is unusable as a component)
    q_grams = _trigram_set(" ".join(qterms))
    r_grams = _trigram_set(" ".join(rterms))
    trig = _query_coverage(q_grams, r_grams)
    phrase, phrase_hits = _phrase_bonus(qterms, rnorm)

    score = (W_TERM_MASS * mass + W_TRIGRAM * trig + W_PHRASE * phrase)
    return {
        "score": round(score, 4),
        "components": {
            "term_mass": round(mass, 4),
            "trigram_coverage": round(trig, 4),
            "phrase_bonus": round(phrase, 4),
        },
        "weights": {"term_mass": W_TERM_MASS, "trigram": W_TRIGRAM,
                    "phrase": W_PHRASE},
        "matched_terms": exact,
        "soft_matched": soft,
        "phrase_hits": phrase_hits,
        "idf_source": idf_source,
        "generic_terms_matched": sorted(set(qterms) & GENERIC_TERMS),
    }


def adjudicate(query_text: str, record_text: str,
               pool_texts: Optional[Sequence[str]] = None
               ) -> Dict[str, Any]:
    """Adjudicate one pair with the declared bands. The verdict
    vocabulary is the evidence fabric's own (RELEVANT / WEAK_RELEVANCE /
    REJECTED) so consumers are unchanged; every decision carries the
    full basis (Art. XXI.4)."""
    s = semantic_score(query_text, record_text, pool_texts)
    score = s["score"]
    if score >= RELEVANT_FLOOR:
        verdict = "RELEVANT"
    elif score >= WEAK_FLOOR:
        verdict = "WEAK_RELEVANCE"
    else:
        verdict = "REJECTED"
    s["verdict"] = verdict
    s["method"] = (
        f"{__version__}: deterministic semantic relatedness "
        f"(IDF-weighted soft core coverage {s['components']['term_mass']}, "
        f"directional trigram coverage {s['components']['trigram_coverage']}, "
        f"phrase bonus {s['components']['phrase_bonus']}; declared "
        f"bands {RELEVANT_FLOOR}/{WEAK_FLOOR}, idf_source="
        f"{s['idf_source']}); thresholds ENGINEERING class, corpus "
        f"provenance in {CORPUS_PROVENANCE}.json (Art. XXVII)")
    return s

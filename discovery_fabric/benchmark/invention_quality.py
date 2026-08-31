"""INVENTION-QUALITY instrument — CEO directive 2026-08-31 (cycle R377).

> "Most importantly, begin measuring the QUALITY OF THE INVENTION ITSELF:
>  * Is the mechanism genuinely derived from evidence?
>  * Is the differentiator technically meaningful?
>  * Is it merely a recombination of known elements?
>  * Does it create a meaningful new technical relationship?
>  * Can a decisive experiment distinguish the candidate from existing
>    approaches?"

The R376 chain instrument (candidate_quality.py — FROZEN, hash-pinned)
measures whether the chain is complete and evidence-bound. It measured
all six fresh-domain survivors STRONG — and the survivors still include
a mechanism whose evidence span is about a different therapy entirely
(measured: span-derivation 0/17 terms) and a "decisive experiment" that
is a literature task (measured: all six selected 'fetch and audit
claims of nearest collision patents'). Chain structure is necessary but
not sufficient: this instrument measures the INVENTION SUBSTANCE.

Constitutional anchors:
- Art. XXVI  builder-measured diagnostic. NEVER wired into kill/promote
             decisions. It diagnoses invention quality; it does not
             adjudicate.
- Art. XXV   UNKNOWN stays UNKNOWN. Missing spans/families measure as
             UNMEASURABLE states, never as passes.
- Art. XXVII bands declared below BEFORE measurement, with justification.
- Art. II    same term-rule family as the engine adjudicator
             (query_relevance.terms) — one transparent rule, no fuzzy
             matching invented for this instrument.
- Art. XXX   the FROZEN Q-instrument is untouched (hash-pinned by test);
             this module is NEW and additive — before/after Q2/Q3
             comparisons remain valid.

Dimensions (each 0.0-1.0 or an honest UNMEASURABLE state):

  I1 MECHANISM_EVIDENCE_DERIVATION
     span_support      — |terms(span) ∩ terms(mechanism+intervention)|
                         / |terms(span)|: is the quoted span ABOUT the
                         claimed mechanism, or a decorative sentence?
     evidence_support  — |terms(mechanism) ∩ terms(evidence title +
                         abstract)| / |terms(mechanism)|: does the cited
                         evidence actually contain the mechanism's
                         technical vocabulary?
     score = min(span_support, evidence_support) — the derivation chain
     is as strong as its weakest link (a mechanism "from" a paper it
     never mentions is underived no matter which link breaks).

  I2 DIFFERENTIATOR_TECHNICAL_MEANING
     Of the surviving differentiators (terms no found family covers),
     what fraction are SPECIFIC technical terms rather than generic
     engineering vocabulary (dual, independent, monitoring, signal,
     processing...)? A differentiator whose entire surviving set is
     generic configuration words is a re-arrangement, not a technical
     distinction.

  I3 RECOMBINATION_RISK (novel residue)
     Union coverage: which of the candidate's distinguishing elements
     are covered by AT LEAST ONE family (any family, not one family)?
     Elements covered by no family are the NOVEL RESIDUE. Score =
     meaningful (non-generic) residue fraction. A candidate with zero
     meaningful residue across >= 2 families is a RECOMBINATION of
     known elements — flagged, and the flag is the finding, not a
     failure of the search.

  I4 NEW_TECHNICAL_RELATIONSHIP
     The mechanism's non-generic term PAIRS (A,B): a pair is KNOWN if A
     and B co-occur in some family's adjudicated text (title +
     abstract + claims). new_relationship_fraction = novel pairs /
     total pairs. Measures whether the candidate COMBINES technical
     concepts in a way no found family does — the "meaningful new
     technical relationship" question, measured at the pair level
     (pair co-occurrence is the weakest deterministic proxy for a
     causal link; recorded as such).

  I5 EXPERIMENT_DISCRIMINATION
     (a) the selected decisive experiment is an EXPERIMENT, not an
         administrative action (measured defect: 'fetch and audit
         claims of nearest collision patents' selected for all six
         R376 survivors — a literature task cannot falsify a physical
         claim);
     (b) it DISCRIMINATES — names a baseline/control/comparison or
         tests a surviving differentiator (distinguishes the candidate
         FROM EXISTING APPROACHES, not from nothing);
     (c) expected information gain present and > 0.

Band interpretation (ENGINEERING judgment, declared before measurement):
  >= 0.70 STRONG        the invention itself carries measured substance
  0.40-0.69 ADEQUATE    substance present, at least one dimension weak
  < 0.40 WEAK           the candidate is a structured proposal, not a
                        differentiated invention (regardless of chain
                        completeness — that is exactly the Q-instrument's
                        blind spot this module exists to expose)
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from discovery_fabric.source_registry.query_relevance import terms

# Generic engineering vocabulary: survives in every domain, carries no
# technical distinction. A differentiator consisting only of these is a
# configuration, not an invention. (Declared list; extends the collision
# core's _INTERVENTION_FILLER with function/configuration nouns.)
GENERIC_ENGINEERING = {
    "system", "systems", "method", "methods", "apparatus", "device",
    "devices", "process", "processes", "technique", "techniques",
    "monitoring", "monitor", "monitors", "sensor", "sensors", "sensing",
    "detection", "detecting", "detect", "control", "controlling",
    "controller", "management", "managing", "data", "processing",
    "signal", "signals", "processing", "independent", "dual", "multiple",
    "redundant", "signal", "unit", "module", "circuit", "circuits",
    "level", "point", "points", "along", "path", "based", "including",
    "using", "configured", "assembly", "structure", "structures",
    "component", "components", "element", "elements", "layer", "layers",
    "early", "real", "time", "smart", "advanced", "improved", "novel",
    "existing", "retrofit", "retrofitted", "implement", "implemented",
    "deployment", "deploy", "installed", "install", "connected",
    "integrated", "analysis", "analyzes", "pattern", "patterns",
}

# Administrative action vocabulary: a decisive experiment MUST NOT be
# one of these (measured defect: 'fetch and audit claims of nearest
# collision patents' was selected as the decisive experiment for all
# six R376 survivors).
ADMINISTRATIVE_ACTION_RE = re.compile(
    r"\b(fetch|audit|search|inspect|review|query|expand|retrieve|"
    r"consult|browse|catalog|inventory|survey|update|refresh|"
    r"re-?run|rerun|record|document|file|register|list|read)\b",
    re.IGNORECASE)

# Discrimination markers: the experiment must compare against something
# (existing approach / baseline / control / with-without / conventional
# art) — measuring the candidate in isolation cannot distinguish it
# from existing approaches.
DISCRIMINATION_MARKERS = (
    "baseline", "control", "with and without", "versus", " vs ",
    "compared", "comparison", "existing", "conventional", "reference",
    "current art", "state of the art", "prior art", "without the",
)


def _t(text: str) -> set:
    return set(terms(text or ""))


def _nongeneric(ts: set) -> set:
    return {x for x in ts if x not in GENERIC_ENGINEERING and len(x) > 3}


# ---------------------------------------------------------------------------
# I1 — mechanism evidence derivation
# ---------------------------------------------------------------------------

def measure_mechanism_derivation(spec: Dict[str, Any]) -> Dict[str, Any]:
    mv = (spec.get("mechanism") or {}).get("value") or {}
    mechanism = str(mv.get("mechanism") or "")
    intervention = str(mv.get("intervention") or "")
    span = str(mv.get("mechanism_source_span") or "")

    # candidate-level source evidence (abstract text) when present
    source_span = ""
    raw = (spec.get("mechanism") or {})
    if isinstance(raw.get("raw_candidate"), dict):
        se = raw["raw_candidate"].get("source_evidence") or {}
        source_span = str(se.get("source_span") or "")
    evidence_titles = " ".join(
        str(e.get("title") or "")
        for e in ((spec.get("evidence") or {}).get("value") or [])
        if isinstance(e, dict))

    mech_terms = _t(f"{mechanism} {intervention}")
    span_terms = _t(span)
    evidence_text_terms = _t(f"{evidence_titles} {source_span}")

    if not mech_terms:
        return {"dimension": "I1_MECHANISM_EVIDENCE_DERIVATION",
                "score": None, "state": "UNMEASURABLE_NO_MECHANISM"}

    span_support = None
    if span_terms:
        shared = span_terms & mech_terms
        span_support = round(len(shared) / len(span_terms), 3)
    evidence_support = None
    if evidence_text_terms:
        shared_e = _nongeneric(mech_terms) & _nongeneric(evidence_text_terms)
        denom = len(_nongeneric(mech_terms)) or 1
        evidence_support = round(len(shared_e) / denom, 3)

    # score = weakest link; missing links are UNMEASURABLE, never zero
    # (Art. XXV: absence of a span is a recording gap, not proof of
    # non-derivation — but it is reported, loudly)
    measured = [x for x in (span_support, evidence_support)
                if x is not None]
    score = round(min(measured), 3) if measured else None
    return {
        "dimension": "I1_MECHANISM_EVIDENCE_DERIVATION",
        "score": score,
        "state": "MEASURED" if measured else "UNMEASURABLE_NO_SPAN",
        "span_support": span_support,
        "evidence_support": evidence_support,
        "span_excerpt": span[:200],
        "underived_flag": (score is not None and score < 0.20),
        "note": "score = min(span_support, evidence_support); "
                "score < 0.20 flags an UNDERIVED mechanism (the quoted "
                "span and/or the evidence does not contain the "
                "mechanism's technical vocabulary)",
    }


# ---------------------------------------------------------------------------
# I2 — differentiator technical meaning
# ---------------------------------------------------------------------------

def measure_differentiator_meaning(spec: Dict[str, Any]) -> Dict[str, Any]:
    dv = (spec.get("distinguishing_features") or {}).get("value") or {}
    surviving = dv.get("surviving_differentiators") or []
    if not surviving:
        # union across families (same rule as the chain audit)
        s = set()
        for pa in (dv.get("vs_nearest_prior_art") or []):
            if isinstance(pa, dict):
                s.update(pa.get("distinguishing_terms_surviving") or [])
        surviving = sorted(s)
    if not surviving:
        return {"dimension": "I2_DIFFERENTIATOR_TECHNICAL_MEANING",
                "score": None, "state": "UNMEASURABLE_NO_SURVIVORS"}
    specific = [t for t in surviving if str(t).lower()
                not in GENERIC_ENGINEERING]
    fraction = round(len(specific) / len(surviving), 3)
    return {
        "dimension": "I2_DIFFERENTIATOR_TECHNICAL_MEANING",
        "score": fraction,
        "state": "MEASURED",
        "surviving_total": len(surviving),
        "surviving_specific": len(specific),
        "specific_terms": specific,
        "generic_terms": [t for t in surviving if str(t).lower()
                          in GENERIC_ENGINEERING],
        "note": "fraction of surviving differentiators that are specific "
                "technical vocabulary rather than generic engineering "
                "configuration words",
    }


# ---------------------------------------------------------------------------
# I3 — recombination risk (novel residue across families)
# ---------------------------------------------------------------------------

def measure_recombination(spec: Dict[str, Any]) -> Dict[str, Any]:
    dv = (spec.get("distinguishing_features") or {}).get("value") or {}
    intervention = str(dv.get("intervention") or "")
    from discovery_fabric.prior_art_v2.collision_resolution import (
        _natural_tokens, _INTERVENTION_FILLER)
    elements = [t for t in _natural_tokens(intervention)
                if t not in _INTERVENTION_FILLER]
    elements = list(dict.fromkeys(elements))
    if not elements:
        return {"dimension": "I3_RECOMBINATION_RISK", "score": None,
                "state": "UNMEASURABLE_NO_ELEMENTS"}

    # union coverage across ALL families' covered terms
    covered_union: set = set()
    n_families = 0
    for pa in (dv.get("vs_nearest_prior_art") or []):
        if not isinstance(pa, dict):
            continue
        n_families += 1
        for t in (pa.get("distinguishing_terms_covered") or []):
            covered_union.add(str(t).lower())
    # family texts also cover terms via mechanism overlap; include them
    pav = (spec.get("prior_art") or {}).get("value") or {}
    for fam in ((pav.get("differentiation_resolution") or {})
                .get("per_family") or []):
        for t in ((fam.get("coverage") or {})
                  .get("distinguishing_terms_covered") or []):
            covered_union.add(str(t).lower())
        for t in ((fam.get("coverage") or {})
                  .get("mechanism_overlap_terms") or []):
            covered_union.add(str(t).lower())

    el_lower = {e.lower() for e in elements}
    covered = el_lower & covered_union
    residue = sorted(el_lower - covered_union)
    meaningful_residue = [r for r in residue
                          if r not in GENERIC_ENGINEERING]
    if not n_families:
        # Art. XXV / XXI.2: ZERO families searched means the residue is
        # UNMEASURED — an uncovered element is only "novel" against art
        # that was actually found. Inference from absence is forbidden
        # (caught live on the s7/m7 stress runs whose Lens quota
        # exhausted mid-grid: I3 initially scored 1.0 'all-novel' on
        # unsearched candidates).
        return {
            "dimension": "I3_RECOMBINATION_RISK",
            "score": None,
            "state": "UNMEASURABLE_NO_FAMILIES",
            "n_elements": len(elements),
            "elements": elements,
            "note": "no prior-art families were adjudicated — the "
                    "recombination/novel-residue question is UNMEASURED "
                    "(absence of found art is not novelty, Art. XXI.2)",
        }
    n_meaningful_elements = len(
        [e for e in el_lower if e not in GENERIC_ENGINEERING]) or 1
    score = round(len(meaningful_residue) / n_meaningful_elements, 3)
    recombination_only = (n_families >= 2 and not meaningful_residue)
    return {
        "dimension": "I3_RECOMBINATION_RISK",
        "score": score,
        "state": "MEASURED",
        "n_elements": len(elements),
        "n_families": n_families,
        "elements_covered_by_some_family": len(covered),
        "novel_residue": residue,
        "meaningful_residue": meaningful_residue,
        "recombination_only_flag": recombination_only,
        "note": "score = fraction of the candidate's meaningful elements "
                "covered by NO found family (the novel residue); "
                "recombination_only_flag: every element is known to some "
                "family across >= 2 families — the only novelty is the "
                "combination",
    }


# ---------------------------------------------------------------------------
# I4 — new technical relationship (mechanism pair novelty)
# ---------------------------------------------------------------------------

def measure_new_relationship(spec: Dict[str, Any]) -> Dict[str, Any]:
    mv = (spec.get("mechanism") or {}).get("value") or {}
    mechanism_terms = _nongeneric(_t(str(mv.get("mechanism") or "")))
    mechanism_terms = {t for t in mechanism_terms if len(t) > 3}
    if len(mechanism_terms) < 2:
        return {"dimension": "I4_NEW_TECHNICAL_RELATIONSHIP",
                "score": None,
                "state": "UNMEASURABLE_TERSE_MECHANISM"}

    # family adjudicated text: title + snippet/abstract (+ claims when
    # stored) per family — the found-art corpus the relationship must
    # be novel against. R377: the collision core now stores the
    # adjudicated_text_excerpt per family (hash-custodied); legacy
    # artifacts carry the representative title only.
    family_texts: List[str] = []
    pav = (spec.get("prior_art") or {}).get("value") or {}
    for fam in ((pav.get("differentiation_resolution") or {})
                .get("per_family") or []):
        rep = fam.get("representative") or {}
        family_texts.append(
            f"{rep.get('title', '')} "
            f"{fam.get('adjudicated_text_excerpt') or ''}")
    # collision hit snippets (when stored on the spec)
    col = spec.get("collision_results") or {}
    if isinstance(col, dict):
        for h in ((col.get("patent") or {}).get("hits") or []):
            if isinstance(h, dict):
                family_texts.append(
                    f"{h.get('title', '')} {h.get('snippet', '')}")

    known_pair_sets = [_t(ft) for ft in family_texts if ft]
    pairs = list(_pairs_sorted(mechanism_terms))
    if not known_pair_sets or not pairs:
        return {"dimension": "I4_NEW_TECHNICAL_RELATIONSHIP",
                "score": None,
                "state": "UNMEASURABLE_NO_FAMILY_TEXT",
                "note": "no adjudicated family text stored on the spec — "
                        "novelty of the technical relationship cannot be "
                        "measured (UNKNOWN, Art. XXV)"}
    novel_pairs = []
    known_pairs = []
    for a, b in pairs:
        known = any((a in fts and b in fts) for fts in known_pair_sets)
        (known_pairs if known else novel_pairs).append((a, b))
    score = round(len(novel_pairs) / len(pairs), 3)
    return {
        "dimension": "I4_NEW_TECHNICAL_RELATIONSHIP",
        "score": score,
        "state": "MEASURED",
        "n_pairs": len(pairs),
        "novel_pairs": [f"{a}+{b}" for a, b in novel_pairs][:20],
        "known_pairs": [f"{a}+{b}" for a, b in known_pairs][:20],
        "note": "pair co-occurrence of the mechanism's non-generic terms "
                "across found family texts — the weakest deterministic "
                "proxy for a causal relationship; a novel PAIR is "
                "necessary but not sufficient for a new technical "
                "relationship",
    }


def _pairs_sorted(ts: set) -> set:
    out = set()
    tl = sorted(ts)
    for i in range(len(tl)):
        for j in range(i + 1, len(tl)):
            out.add((tl[i], tl[j]))
    return out


# ---------------------------------------------------------------------------
# I5 — experiment discrimination
# ---------------------------------------------------------------------------

def measure_experiment_discrimination(
        spec: Dict[str, Any],
        decisive: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    sel = (decisive or {}).get("selected") or {}
    if not isinstance(sel, dict):
        ke = spec.get("killer_experiment") or {}
        kv = ke.get("value") or {}
        sel = {"experiment": kv.get("selected"),
               "expected_information_gain": kv.get("eig")}
    exp_text = str(sel.get("experiment") or "")
    checks: Dict[str, bool] = {}

    checks["is_physical_experiment"] = bool(
        exp_text and not ADMINISTRATIVE_ACTION_RE.search(exp_text))

    # discrimination: baseline markers OR tests a surviving differentiator
    dv = (spec.get("distinguishing_features") or {}).get("value") or {}
    surviving = set()
    for pa in (dv.get("vs_nearest_prior_art") or []):
        if isinstance(pa, dict):
            surviving.update(
                str(t).lower() for t in
                (pa.get("distinguishing_terms_surviving") or []))
    surviving.discard("")
    exp_l = exp_text.lower()
    has_baseline = any(m in exp_l for m in DISCRIMINATION_MARKERS)
    tests_differentiator = bool(surviving) and any(
        t in exp_l for t in surviving if len(t) > 4)
    checks["discriminates_against_existing"] = bool(
        has_baseline or tests_differentiator)

    eig = sel.get("expected_information_gain")
    checks["eig_present_positive"] = (
        isinstance(eig, (int, float)) and eig > 0)

    if not exp_text:
        return {"dimension": "I5_EXPERIMENT_DISCRIMINATION", "score": None,
                "state": "UNMEASURABLE_NO_EXPERIMENT"}
    score = round(sum(1 for v in checks.values() if v) / len(checks), 3)
    return {
        "dimension": "I5_EXPERIMENT_DISCRIMINATION",
        "score": score,
        "state": "MEASURED",
        "selected_experiment": exp_text[:200],
        "checks": checks,
        "note": "a literature/administrative action is not an experiment; "
                "an experiment without baseline or differentiator "
                "isolation cannot distinguish the candidate from "
                "existing approaches",
    }


# ---------------------------------------------------------------------------
# Band + run measurement
# ---------------------------------------------------------------------------

def grade_band(avg: Optional[float]) -> str:
    if avg is None:
        return "UNMEASURED"
    if avg >= 0.70:
        return "STRONG"
    if avg >= 0.40:
        return "ADEQUATE"
    return "WEAK"


def measure_run(run_dir: Path) -> Dict[str, Any]:
    """Measure one run's INVENTION quality on the survivor's spec."""
    spec_path = run_dir / "INVENTION_SPECIFICATION.json"
    if not spec_path.exists():
        return {"run_dir": str(run_dir), "state": "NO_SPEC",
                "verdict": "UNMEASURABLE"}
    spec = json.loads(spec_path.read_text())
    decisive = None
    dec_path = run_dir / "DECISIVE_EXPERIMENT.json"
    if dec_path.exists():
        try:
            decisive = json.loads(dec_path.read_text())
        except Exception:  # noqa: BLE001 — disclosed per-run
            decisive = None
    dims = [
        measure_mechanism_derivation(spec),
        measure_differentiator_meaning(spec),
        measure_recombination(spec),
        measure_new_relationship(spec),
        measure_experiment_discrimination(spec, decisive),
    ]
    scores = [d["score"] for d in dims
              if isinstance(d.get("score"), (int, float))]
    avg = round(sum(scores) / len(scores), 3) if scores else None
    weakest = min(
        (d for d in dims if isinstance(d.get("score"), (int, float))),
        key=lambda d: d["score"], default=None)
    return {
        "run_dir": str(run_dir),
        "state": "MEASURED",
        "instrument": "INVENTION_QUALITY (R377)",
        "dimensions": dims,
        "average": avg,
        "band": grade_band(avg),
        "weakest_dimension": (weakest or {}).get("dimension"),
        "flags": {
            "underived_mechanism": any(
                d.get("underived_flag") for d in dims),
            "recombination_only": any(
                d.get("recombination_only_flag") for d in dims),
        },
    }

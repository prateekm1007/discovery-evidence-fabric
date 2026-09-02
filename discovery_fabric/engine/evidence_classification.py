"""evidence_classification.py — R394 section 5: evidence must understand
the claim.

Directive:

  "Evidence classification must operate at:
     PROBLEM -> FAILURE MODE -> MECHANISM -> EXPECTED EFFECT.
   A document being topically similar is insufficient.
   For each evidence item record: domain relevance, failure-mode
   relevance, mechanism relevance, material relevance, operating-regime
   relevance. Then classify:
     DIRECT_SUPPORT / PARTIAL_SUPPORT / BACKGROUND / ANALOGY /
     CONTRADICTORY / IRRELEVANT.
   The engine must be able to say: 'This source is relevant to the
   domain but does not support the mechanism.'"

DESIGN (deterministic, transparent, same rule family as the rest of the
engine — term overlap with declared thresholds, no LLM in the decision):

  Per evidence item, five relevance dimensions are computed against the
  CLAIM AXIS (problem device/domain, failure mode, mechanism, expected
  effect, materials, operating regime):

    domain_relevance          device/domain terms shared with the item
    failure_mode_relevance    failure-mode content terms shared
    mechanism_relevance       mechanism terms shared (>= 2 — the engine's
                              standing domain-specificity bar)
    material_relevance        material vocabulary shared
    operating_regime_relevance regime vocabulary shared

  Each dimension records the overlapping terms (auditable basis, Art. II
  spirit) and a boolean. Classification then follows the declared rule
  table below. CONTRADICTORY uses a transparent negation-proximity
  heuristic (disclosed as a proxy, not a claim chart).

  Thresholds (Art. XXVII — declared, ENGINEERING class):
    MIN_DOMAIN_OVERLAP       2   same rule family as MIN_MECHANISM_OVERLAP
    MIN_MECHANISM_OVERLAP    2   standing engine bar (collision core)
    MIN_FAILURE_MODE_OVERLAP 1   a single specific failure term is a
                                 real signal (e.g. 'occlusion')
    MIN_SPECIALTY_OVERLAP    1   material/regime terms are sparse and
                                 specific; one shared term is signal

No fuzzy matching, no semantic similarity fallback (Art. IV). An item
that cannot reach a class on its overlaps is IRRELEVANT — recorded with
its basis, never silently dropped.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from discovery_fabric.source_registry.query_relevance import terms

EVIDENCE_CLASSES = ("DIRECT_SUPPORT", "PARTIAL_SUPPORT", "BACKGROUND",
                    "ANALOGY", "CONTRADICTORY", "IRRELEVANT")

# Relevance-model identity (R394 section 3 — persisted with every
# classification so determinism is checkable).
EVIDENCE_CLASSIFIER_VERSION = "evidence_classification/1.0.0"

THRESHOLDS: Dict[str, Dict[str, Any]] = {
    "MIN_DOMAIN_OVERLAP": {
        "value": 2,
        "epistemic_class": "ENGINEERING",
        "justification": ("same rule family as the engine's standing "
                          "domain-specificity bar (>= 2 shared content "
                          "terms = domain-specific rather than accidental "
                          "collision)"),
        "uncertainty": "term overlap is a proxy for domain identity",
    },
    "MIN_MECHANISM_OVERLAP": {
        "value": 2,
        "epistemic_class": "ENGINEERING",
        "justification": ("the collision core's MIN_MECHANISM_OVERLAP — "
                          "one rule family across the engine (Art. VII: "
                          "no per-callsite threshold invention)"),
        "uncertainty": "term overlap is a proxy for mechanism identity",
    },
    "MIN_FAILURE_MODE_OVERLAP": {
        "value": 1,
        "epistemic_class": "ENGINEERING",
        "justification": ("failure-mode vocabulary is sparse and specific "
                          "('occlusion', 'drift', 'delamination'); a "
                          "single shared specific term is a real signal, "
                          "accidental single-term collisions are already "
                          "filtered by the domain gate"),
        "uncertainty": "word-sense collisions remain possible",
    },
    "MIN_SPECIALTY_OVERLAP": {
        "value": 1,
        "epistemic_class": "ENGINEERING",
        "justification": ("material and operating-regime vocabulary "
                          "(polyethylene, titanium, 310 K, cyclic load) "
                          "is highly specific; one shared term is signal"),
        "uncertainty": "none disclosed beyond term-overlap proxy limits",
    },
}

# Material vocabulary classes (deterministic lexicon, disclosed)
_MATERIAL_HINTS = {
    "polyethylene", "titanium", "titanium alloy", "stainless",
    "stainless steel", "cobalt", "chromium", "silicon", "silica",
    "borosilicate", "glass", "aluminum", "aluminium", "alumina",
    " CFRP", "carbon fiber", "graphite", "pdms", "silicone",
    "nitinol", "platinum", "iridium", "perovskite", "composite",
    "polymer", "ceramic", "steel", "alloy", "elastomer", "hydrogel",
    "parylene", "eptfe", "dacron", "polyurethane", "pmma",
}
_MATERIAL_HINTS = {m.strip() for m in _MATERIAL_HINTS}

_REGIME_HINTS = {
    "temperature", "pressure", "flow", "flow rate", "cyclic", "fatigue",
    "load", "loading", "stress", "strain", "ph", "osmolality",
    "viscosity", "frequency", "voltage", "current", "power", "thermal",
    "humidity", "sterilization", "autoclave", "body temperature",
    "physiological", "in vivo", "in vitro", "operating temperature",
    "service temperature", "cathodic", "corrosive", "abrasive",
}
_REGIME_HINTS = {r.strip() for r in _REGIME_HINTS}

# Negation-proximity markers for the CONTRADICTORY heuristic (proxy,
# disclosed): a negated claim near mechanism/effect terms.
_NEGATION_MARKERS = (
    "did not", "does not", "no effect", "not associated", "failed to",
    "without improvement", "no improvement", "no significant",
    "contradicts", "inconsistent with", "refutes", "unlikely",
    "no difference", "not effective", "ineffective", "worsened",
    "adverse", "complication", "no reduction",
)

_WORD_RE = re.compile(r"[a-z]+")

_GENERIC_DOMAIN_TERMS = {
    "system", "method", "device", "apparatus", "process", "technique",
    "based", "using", "including", "data", "signal", "control",
    "management", "analysis", "monitoring", "detection", "study",
    "studies", "result", "results", "effect", "effects", "review",
    "approach", "application", "development", "research", "clinical",
}


def _fold_terms(text: str) -> set:
    return set(terms(text or ""))


def _phrase_hits(phrase_set: set, text_lower: str) -> List[str]:
    return sorted(p for p in phrase_set if p in text_lower)


def classify_evidence_item(item: Dict[str, Any],
                           problem: Dict[str, Any],
                           mechanism_map: Dict[str, Any]) -> Dict[str, Any]:
    """Classify ONE evidence item against the claim axes.

    The item text is its title + abstract (the evidence the engine
    actually holds). The claim axes come from the frozen problem
    (device, failure, failure_mode) and the candidate mechanism map
    (mechanism, expected_effect).
    """
    device = str(problem.get("device") or "")
    failure = str(problem.get("failure") or
                  problem.get("failure_mode") or "")
    failure_mode = str(problem.get("failure_mode") or "")
    mechanism = str(mechanism_map.get("mechanism") or "")
    expected_effect = str(mechanism_map.get("expected_effect") or "")

    item_text = " ".join(str(item.get(k) or "") for k in
                         ("title", "abstract", "snippet"))
    text_terms = _fold_terms(item_text)
    text_lower = item_text.lower()

    domain_terms = _fold_terms(device)
    failure_terms = (_fold_terms(failure) | _fold_terms(failure_mode))
    mechanism_terms = _fold_terms(mechanism) - _GENERIC_DOMAIN_TERMS
    effect_terms = _fold_terms(expected_effect) - _GENERIC_DOMAIN_TERMS

    dom_overlap = sorted(domain_terms & text_terms)
    fm_overlap = sorted(failure_terms & text_terms)
    mech_overlap = sorted(mechanism_terms & text_terms)
    effect_overlap = sorted(effect_terms & text_terms)
    material_overlap = _phrase_hits(_MATERIAL_HINTS, text_lower) + \
        sorted((text_terms & _MATERIAL_HINTS))
    material_overlap = sorted(set(material_overlap))
    regime_overlap = _phrase_hits(_REGIME_HINTS, text_lower) + \
        sorted((text_terms & _REGIME_HINTS))
    regime_overlap = sorted(set(regime_overlap))

    min_dom = THRESHOLDS["MIN_DOMAIN_OVERLAP"]["value"]
    min_mech = THRESHOLDS["MIN_MECHANISM_OVERLAP"]["value"]
    min_fm = THRESHOLDS["MIN_FAILURE_MODE_OVERLAP"]["value"]
    min_spec = THRESHOLDS["MIN_SPECIALTY_OVERLAP"]["value"]

    domain_relevant = len(dom_overlap) >= min_dom
    failure_mode_relevant = len(fm_overlap) >= min_fm
    mechanism_relevant = len(mech_overlap) >= min_mech
    material_relevant = len(material_overlap) >= min_spec
    regime_relevant = len(regime_overlap) >= min_spec

    # CONTRADICTORY heuristic (transparent proxy): a negation marker
    # within the same sentence as mechanism/effect/failure terms.
    contradictory = False
    contradiction_basis = ""
    sentences = re.split(r"(?<=[.!?])\s+", item_text)
    mech_or_effect = (mechanism_terms | effect_terms | failure_terms)
    for sent in sentences:
        s_lower = sent.lower()
        if not any(m in s_lower for m in _NEGATION_MARKERS):
            continue
        s_terms = _fold_terms(sent)
        near = sorted(s_terms & mech_or_effect)
        if near:
            contradictory = True
            contradiction_basis = (
                f"negation marker co-located with claim terms {near} "
                f"in: '{sent[:160]}'")
            break

    # ---- the six-class rule table (declared, deterministic) ----
    if contradictory:
        cls = "CONTRADICTORY"
    elif domain_relevant and failure_mode_relevant and mechanism_relevant:
        cls = "DIRECT_SUPPORT"
    elif domain_relevant and (failure_mode_relevant or mechanism_relevant):
        cls = "PARTIAL_SUPPORT"
    elif domain_relevant:
        cls = "BACKGROUND"
    elif not domain_relevant and (mechanism_relevant or
                                  failure_mode_relevant):
        cls = "ANALOGY"
    else:
        cls = "IRRELEVANT"

    # The buyer-facing one-liner the directive demands
    if domain_relevant and not mechanism_relevant and cls in (
            "PARTIAL_SUPPORT", "BACKGROUND"):
        statement = ("This source is relevant to the domain but does not "
                     "support the mechanism.")
    elif cls == "DIRECT_SUPPORT":
        statement = ("This source is relevant to the domain, the failure "
                     "mode, and the mechanism.")
    elif cls == "ANALOGY":
        statement = ("This source is from an adjacent domain but speaks "
                     "to the mechanism or failure mode (analogy, not "
                     "direct domain evidence).")
    elif cls == "CONTRADICTORY":
        statement = ("This source contains a negated claim co-located "
                     "with the candidate's mechanism/effect terms — "
                     "treated as potential contradictory evidence.")
    elif cls == "IRRELEVANT":
        statement = ("This source does not share domain, failure-mode, "
                     "or mechanism vocabulary with the claim.")
    else:
        statement = ("This source partially overlaps the claim axes; "
                     "recorded as partial support.")

    return {
        "source_id": item.get("id") or item.get("source_id"),
        "title": (item.get("title") or "")[:140],
        "classification": cls,
        "relevance": {
            "domain": {"relevant": domain_relevant,
                       "overlapping_terms": dom_overlap},
            "failure_mode": {"relevant": failure_mode_relevant,
                             "overlapping_terms": fm_overlap},
            "mechanism": {"relevant": mechanism_relevant,
                          "overlapping_terms": mech_overlap},
            "expected_effect": {"relevant": bool(effect_overlap),
                                "overlapping_terms": effect_overlap},
            "material": {"relevant": material_relevant,
                         "overlapping_terms": material_overlap},
            "operating_regime": {"relevant": regime_relevant,
                                 "overlapping_terms": regime_overlap},
        },
        "classification_basis": {
            "rule": _rule_text(cls, domain_relevant, failure_mode_relevant,
                               mechanism_relevant),
            "contradiction_basis": contradiction_basis or None,
            "thresholds_applied": {
                "min_domain_overlap": min_dom,
                "min_failure_mode_overlap": min_fm,
                "min_mechanism_overlap": min_mech,
                "min_specialty_overlap": min_spec,
            },
        },
        "buyer_statement": statement,
        "classifier_version": EVIDENCE_CLASSIFIER_VERSION,
    }


def _rule_text(cls: str, dom: bool, fm: bool, mech: bool) -> str:
    if cls == "CONTRADICTORY":
        return ("negation marker co-located with claim terms "
                "(transparent proxy — not a claim chart)")
    bits = [f"domain={dom}", f"failure_mode={fm}", f"mechanism={mech}"]
    return "term-overlap rule table: " + ", ".join(bits)


def classify_evidence_set(evidence: List[Dict[str, Any]],
                          problem: Dict[str, Any],
                          mechanism_map: Dict[str, Any]) -> Dict[str, Any]:
    """Classify every evidence item; aggregate honestly (counts, never
    silent selection). The aggregate is what downstream stages and the
    dossier consume: every item's class + basis travels with it."""
    items = [classify_evidence_item(e, problem, mechanism_map)
             for e in (evidence or [])]
    counts = {c: 0 for c in EVIDENCE_CLASSES}
    for it in items:
        counts[it["classification"]] += 1
    # Support profile: does ANY item directly support the mechanism?
    direct = [it for it in items if it["classification"] == "DIRECT_SUPPORT"]
    contradictory = [it for it in items
                     if it["classification"] == "CONTRADICTORY"]
    return {
        "classifier_version": EVIDENCE_CLASSIFIER_VERSION,
        "n_items": len(items),
        "counts": counts,
        "items": items,
        "mechanism_support": {
            "n_direct_support": len(direct),
            "direct_support_source_ids": [
                d.get("source_id") for d in direct],
            "n_contradictory": len(contradictory),
            "contradictory_source_ids": [
                c.get("source_id") for c in contradictory],
            "note": ("DIRECT_SUPPORT requires domain + failure-mode + "
                     "mechanism relevance; domain-only relevance is "
                     "BACKGROUND and can never support a mechanism claim "
                     "(R394 s5)"),
        },
        "thresholds": THRESHOLDS,
    }

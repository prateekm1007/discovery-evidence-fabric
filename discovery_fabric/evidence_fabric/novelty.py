"""Evidence-to-invention novelty defense (R449 directive Phase 11).

The explicit distinction the machine must make before granting
invention credit:
    KNOWN MECHANISM          — the mechanism itself is documented in
                               retrieved evidence (no invention credit;
                               at most engineering application credit)
    CAUSAL COMBINATION       — components each known, combination
                               asserted; LOW credit UNLESS the
                               interaction itself is evidenced
    MEANINGFUL NEW INTERACTION — evidence-backed interaction effect
                               between the combined mechanisms (the
                               combination is not mere adjacency)
    NEW OPERATING REGIME     — evidence-backed regime where the known
                               mechanism behaves materially differently

A candidate does NOT receive invention credit simply because the
retrieval system found two technologies that can be placed next to
each other. This attacks the historical obvious-combination problem:
the credit move from CAUSAL_COMBINATION to the higher levels requires
EXACT-SPAN evidence whose own terms ground the INTERACTION or the
REGIME — not the components separately.

Deterministic term-grounding adjudication (no LLM judgment in the
credit decision — Art. XVIII: the model proposes, the infrastructure
adjudicates; Art. XLVI: the machine must distinguish known/recombined/
transferred/...).

Vocabulary (closed):
    KNOWN_MECHANISM / CAUSAL_COMBINATION / MEANINGFUL_NEW_INTERACTION /
    NEW_OPERATING_REGIME / NOVEL_BEHAVIOR / INSUFFICIENT_EVIDENCE

R450 §13 (obvious-combination protection, the reproduction leg): the
strongest level — NOVEL_BEHAVIOR — requires the full chain
    known A + known B -> unexpected interaction C -> predicted by
    mechanism -> REPRODUCED BY EVALUATION
where the reproduction is a RECORDED evaluation/observation artifact
that grounds the interaction. A combination without the reproduction
evidence stays at CAUSAL_COMBINATION/MEANINGFUL_NEW_INTERACTION —
novelty-by-description is never upgraded to novelty-by-demonstration
without the recorded reproduction (Art. XXVIII).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

#: interaction-regime markers: terms that co-occur in evidence text
#: when an INTERACTION or REGIME (not mere co-presence) is described.
#: Fixed vocabulary, authored from mechanism-literature phrasing, not
#: tuned against any result set.
_INTERACTION_MARKERS = [
    "synergy", "synergistic", "interaction", "interplay", "coupled",
    "coupling", "combined effect", "when combined", "in combination",
    "cooperative", "antagonistic", "potentiates", "synergistically",
]
_REGIME_MARKERS = [
    "regime", "operating window", "threshold", "below", "above",
    "critical temperature", "critical concentration", "transition",
    "onset", "beyond", "exceeds", "at high", "at low", "extremes",
    "limits", "boundary condition", "boundary conditions",
]

NOVELTY_LEVELS = [
    "KNOWN_MECHANISM",
    "CAUSAL_COMBINATION",
    "MEANINGFUL_NEW_INTERACTION",
    "NEW_OPERATING_REGIME",
    "NOVEL_BEHAVIOR",
    "INSUFFICIENT_EVIDENCE",
]


def _terms(text: str, min_len: int = 4) -> set:
    return set(re.findall(r"[a-z0-9]{%d,}" % min_len,
                          (text or "").lower()))


def _markers(text: str, markers: List[str]) -> List[str]:
    low = (text or "").lower()
    return [m for m in markers if m in low]


def adjudicate_novelty_level(
        mechanism: str,
        intervention: str,
        evidence_items: List[Dict[str, Any]],
        reproduction_evidence: Optional[Dict[str, Any]] = None
        ) -> Dict[str, Any]:
    """Adjudicate the novelty level of ONE candidate against its
    evidence pool.

    evidence_items: a2-schema dicts (the engine pool / fabric pool),
    with optional evidence_fabric.exact_span.text for span grounding.

    Deterministic rules (each recorded with its basis):
      1. mechanism-identity: any evidence item whose span shares >= 3
         distinctive mechanism terms documents the mechanism ->
         KNOWN_MECHANISM (unless an interaction/regime marker set is
         ALSO grounded in that same span or another span sharing the
         combination terms).
      2. combination terms present in >= 2 DIFFERENT items (two
         technology clusters both grounded) -> CAUSAL_COMBINATION
         baseline.
      3. an interaction marker grounded in an item that ALSO shares
         the combination's cross-cluster terms -> MEANINGFUL_NEW_
         INTERACTION.
      4. a regime marker grounded in an item that shares the
         mechanism's terms AND carries a quantitative bound token
         (number+unit pattern) -> NEW_OPERATING_REGIME.
      5. fewer than 2 grounded items -> INSUFFICIENT_EVIDENCE (Art. II:
         the answer to an unproven credit claim is INSUFFICIENT
         EVIDENCE, never "probably novel").
    """
    mech_terms = _terms(mechanism) | _terms(intervention)
    per_item: List[Dict[str, Any]] = []
    for it in evidence_items:
        span_text = str(it.get("abstract") or "") + " " + str(
            ((it.get("evidence_fabric") or {}).get("exact_span") or {}
             ).get("text") or "")
        shared = sorted(_terms(span_text) & mech_terms)
        markers_i = _markers(span_text, _INTERACTION_MARKERS)
        markers_r = _markers(span_text, _REGIME_MARKERS)
        has_quant = bool(re.search(
            r"\b\d+(\.\d+)?\s*(mm|cm|m|km|k?pa|mpa|bar|atm|c|f|k|c|"
            r"v|a|w|kw|mw|hz|khz|mhz|ghz|s|ms|min|h|mol|mmol|ppm|"
            r"ph|%\b)", span_text.lower()))
        per_item.append({
            "id": it.get("id"),
            "shared_terms": shared,
            "n_shared": len(shared),
            "interaction_markers": markers_i,
            "regime_markers": markers_r,
            "quantitative": has_quant,
            "text": span_text[:200],
        })
    grounded = [p for p in per_item if p["n_shared"] >= 3]
    basis: List[str] = []
    if len(grounded) < 2 and not grounded:
        return {
            "level": "INSUFFICIENT_EVIDENCE",
            "basis": ["fewer than two evidence items share >= 3 "
                      "distinctive mechanism terms — the novelty claim "
                      "cannot be grounded (Art. II: INSUFFICIENT "
                      "EVIDENCE, never 'probably novel')"],
            "per_item": per_item,
        }
    # interaction: markers grounded in an item that shares mechanism
    # terms AND the candidate is a combination (intervention carries
    # >= 2 technology clusters across the grounded items)
    interaction_items = [p for p in grounded
                         if p["interaction_markers"] and p["n_shared"] >= 2]
    regime_items = [p for p in grounded
                    if p["regime_markers"] and p["quantitative"]
                    and p["n_shared"] >= 2]
    clusters = {}
    for p in grounded:
        for t in p["shared_terms"][:6]:
            clusters.setdefault(t, 0)
            clusters[t] += 1
    n_clusters = len([t for t, c in clusters.items() if c >= 1])
    # ---- R450 §13: the reproduction leg (NOVEL_BEHAVIOR) ----------
    # known A + known B -> unexpected interaction C -> predicted by
    # mechanism -> REPRODUCED BY EVALUATION. The reproduction is a
    # RECORDED evaluation artifact (observation/gauntlet record) whose
    # own text grounds the interaction; without it the level stays at
    # the interaction/regime level (novelty-by-description only).
    reproduced = False
    reproduction_basis = ""
    if reproduction_evidence and interaction_items:
        rep_text = " ".join(str(reproduction_evidence.get(k) or "")
                            for k in ("predicted_effect",
                                      "observed_effect", "basis",
                                      "kill_reason", "text"))
        if rep_text.strip() and _markers(rep_text, _INTERACTION_MARKERS):
            reproduced = True
            reproduction_basis = (
                "reproduction recorded: "
                + str(reproduction_evidence.get("observation_id")
                      or reproduction_evidence.get("evaluation_id")
                      or "<recorded evaluation artifact>")
                + " grounds the interaction in its own measured text")
    if regime_items:
        level = "NEW_OPERATING_REGIME"
        basis.append(
            "regime evidence grounded: "
            + "; ".join(f"{p['id']} markers={p['regime_markers'][:3]} "
                        f"quantitative={p['quantitative']}"
                        for p in regime_items[:2]))
    elif interaction_items:
        level = "MEANINGFUL_NEW_INTERACTION"
        basis.append(
            "interaction evidence grounded: "
            + "; ".join(f"{p['id']} markers="
                        f"{p['interaction_markers'][:3]}"
                        for p in interaction_items[:2]))
    elif len(grounded) >= 2 and n_clusters >= 2:
        level = "CAUSAL_COMBINATION"
        basis.append(
            f"{len(grounded)} items ground separate technology clusters "
            f"({', '.join(list(clusters)[:6])}) with NO grounded "
            f"interaction or regime marker — adjacency only, the "
            f"historical obvious-combination case: LOW credit")
    elif grounded:
        level = "KNOWN_MECHANISM"
        basis.append(
            "a single evidence cluster documents the mechanism itself "
            "(no evidenced combination, interaction, or regime): the "
            "mechanism is KNOWN — engineering application credit only, "
            "no invention credit")
    else:
        return {
            "level": "INSUFFICIENT_EVIDENCE",
            "basis": ["mechanism terms not grounded in the evidence "
                      "pool"],
            "per_item": per_item,
        }
    if reproduced and level in ("MEANINGFUL_NEW_INTERACTION",
                               "NEW_OPERATING_REGIME"):
        level = "NOVEL_BEHAVIOR"
        basis.append(reproduction_basis)
        basis.append(
            "the full chain holds: known components + evidenced "
            "interaction + mechanism prediction + RECORDED "
            "reproduction — the strongest invention-evidence class "
            "(novelty-by-demonstration, not novelty-by-description)")
    return {
        "level": level,
        "basis": basis,
        "per_item": per_item,
        "reproduced_by_evaluation": reproduced,
        "credit_rule": (
            "invention credit at MEANINGFUL_NEW_INTERACTION or "
            "NEW_OPERATING_REGIME requires exact-span evidence grounding "
            "the INTERACTION or the REGIME — component adjacency alone "
            "stays CAUSAL_COMBINATION (low credit); a documented "
            "single mechanism is KNOWN_MECHANISM (no invention credit)"),
    }

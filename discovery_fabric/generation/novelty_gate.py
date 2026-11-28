"""R144 generation strength (R143-F6c) — the novelty gate.

V110: 0/30 v16 inventions were STRONG — the dominant weakness is
generic modulation (flow/pressure tweaks), passive insulation, and
monitoring-dressed-as-mitigation. This gate scores a generated
candidate BEFORE it can be admitted as an invention:

  strong    : a mapped mechanism class named + a cross-domain precedent
              + a quantitative falsifiable prediction
  marginal  : a mapped mechanism class named, no quantified prediction
  weak      : a generic pattern (documented R143-F6c list) or an
              off-target coupling — REJECTED with typed reasons

The gate is deterministic (regex+table) so it is checkable; the LLM
half (the critic) still runs on top.
"""
from __future__ import annotations

import re

# The generic-pattern blacklist (documented R143-F6c): these surface
# patterns, WITHOUT a coupled mapped mechanism, are the generic-
# modulation monoculture that scored 0-strong.
GENERIC_PATTERNS = [
    (r"increas\w* (?:the )?(?:flow|pressure|coolant flow|feed rate)",
     "generic flow/pressure modulation"),
    (r"decreas\w* (?:the )?(?:flow|pressure|feed rate|temperature)",
     "generic flow/pressure modulation"),
    (r"install\w* (?:additional |more )?(?:sensor|monitor|cam|gauge|"
     r"detection system)", "monitoring dressed as mitigation"),
    (r"(?:regular |scheduled |frequent )(?:inspection|monitoring)",
     "monitoring dressed as mitigation"),
    (r"add\w* (?:insulation|lagging|thermal barrier)",
     "passive insulation as a cure-all"),
    (r"upgrad\w* (?:to )?(?:a )?(?:thicker|larger|bigger)",
     "bigger-component genericism"),
    (r"operator (?:should|must) (?:check|inspect|monitor)",
     "procedural note, not an engineering intervention"),
]

STRONG_MARKERS = [
    (r"\d+(?:\.\d+)?\s*%", "quantified percentage effect"),
    (r"falsif", "explicit falsification language"),
    (r"(?:coupon|whirling|test rig|bench test|pit test|triple test)",
     "named physical test"),
    (r"(?:within|inside)\s+[^.]*?\d+\s*(?:mm|m|kPa|K|°C|%|mg)",
     "numeric tolerance/window"),
]


def score_novelty(candidate_text: str, mechanism_class: str = "",
                  cross_domain: str = "") -> dict:
    """The typed novelty verdict with reasons."""
    t = (candidate_text or "").lower()
    reasons, hits_generic = [], []
    for pat, label in GENERIC_PATTERNS:
        m = re.search(pat, t)
        if m:
            hits_generic.append(label)
    has_mapped = bool(mechanism_class)
    has_xdomain = bool(cross_domain)
    n_strong = sum(1 for pat, _ in STRONG_MARKERS if re.search(pat, t))
    # verdict logic: generic patterns sink it unless a mapped mechanism
    # with quantification dominates the text
    if hits_generic and not has_mapped:
        return {"novelty": "weak", "reject": True,
                "reasons": [f"generic pattern: {g}" for g in hits_generic],
                "quant_markers": n_strong}
    if has_mapped and n_strong >= 2 and (has_xdomain or n_strong >= 3):
        verdict = "strong"
    elif has_mapped and n_strong >= 1:
        verdict = "marginal"
    elif has_mapped:
        verdict = "marginal"
        reasons.append("mapped mechanism but no quantified prediction "
                       "(the quantitative testability clause)")
    else:
        verdict = "weak"
        reasons.append("no mapped mechanism class named (blind-operator "
                       "generation is retired — R143-F6)")
        reasons += [f"generic pattern: {g}" for g in hits_generic]
    if hits_generic:
        reasons.append(f"generic surface pattern present but a mapped "
                       f"mechanism dominates: {hits_generic}")
    return {"novelty": verdict, "reject": verdict == "weak",
            "reasons": reasons, "quant_markers": n_strong,
            "mapped_mechanism": mechanism_class,
            "cross_domain": cross_domain}


def gate(candidate_text: str, selection) -> dict:
    """Full gate: the mechanism selection + the novelty verdict."""
    mech = getattr(selection, "selected_mech_class", "") or ""
    xd = getattr(selection, "cross_domain", "") or ""
    out = score_novelty(candidate_text, mech, xd)
    if getattr(selection, "off_target", False):
        out["novelty"] = "weak"
        out["reject"] = True
        out["reasons"].insert(0, f"OFF-TARGET: {selection.off_target_reason}")
    return out

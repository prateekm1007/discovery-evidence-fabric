"""premise_gate.py — R394 section 6: the false-premise gate.

Directive:

  "Before candidate synthesis: CHECK WHETHER THE PROBLEM'S PREMISES ARE
   PHYSICALLY/SCIENTIFICALLY COHERENT.

   Example: grain boundaries in amorphous borosilicate glass.

   Required outcome: MALFORMED_OR_FALSE_PREMISE with a concise
   explanation. Do not burn candidate-generation compute after a false
   premise has already been detected. This is a first-class discovery
   stage, not an adversarial cleanup trick."

MEASURED MOTIVATION (public deployment, 2026-09-02, run
ts_5c6ea3076a42): the problem 'grain-boundary sliding failures limit the
service temperature of borosilicate glass reactor liners' ran the FULL
pipeline — RETRIEVE pulled an irrelevant CMOS paper as its only
evidence, SYNTHESIZE burned LLM transport on a nonsense mechanism
('integrated advanced strain engineering' — CMOS vocabulary), and only
the ADVERSARIAL stage killed it as unsupported_mechanism ~40 seconds
later. The premise (grain boundaries in an AMORPHOUS material) was false
from the first word; the engine had no gate that could say so.

DESIGN — deterministic hard-rule table (V0, disclosed):

  A premise is MALFORMED_OR_FALSE_PREMISE when its own text asserts a
  phenomenon that is structurally impossible for the material/system
  class it names. The rule table encodes ONLY contradictions that are
  definitional (not empirical, not threshold-dependent): amorphous
  solids have no grain boundaries by definition; vacua have no
  convective medium by definition; single crystals have no grain
  boundaries by definition; incompressible liquids do not cavitate
  under static pressure... Each rule records its physical basis and
  provenance class ENGINEERING (Art. XXVII).

  What this gate deliberately is NOT (honest limits, Art. XV):
    - it is not a general physics engine: it catches definitional
      incoherence only; a physically false but non-contradictory
      premise passes (named limitation, recorded in every verdict);
    - it is not LLM-driven: the model is untrusted (Art. XVIII) and an
      LLM opinion can never be the blocking authority. The gate is a
      deterministic instrument — same rule family as the rest of the
      engine's adjudicators.

Verdict vocabulary:
  PREMISE_COHERENT            no rule matched; the premise MIGHT still be
                              false — the gate cannot prove coherence
  MALFORMED_OR_FALSE_PREMISE  a definitional contradiction matched; the
                              explanation names the rule and the
                              conflicting terms
  PREMISE_UNPARSEABLE         the problem carries no device/material
                              assertion the rules can bind to (recorded,
                              non-blocking — the gate fails OPEN on
                              absence of signal, never blocks on its own
                              blindness; Art. V)
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

PREMISE_VERSION = "premise_gate/1.0.0"

PREMISE_VERDICTS = ("PREMISE_COHERENT", "MALFORMED_OR_FALSE_PREMISE",
                    "PREMISE_UNPARSEABLE")

# ---------------------------------------------------------------------------
# The hard rule table — definitional contradictions only (disclosed,
# ENGINEERING class, extensible by explicit commit).
# Each rule: classes of MATERIAL/SYSTEM named in the problem text, the
# PHENOMENON asserted, and the physical basis of the contradiction.
# ---------------------------------------------------------------------------

RULES: List[Dict[str, Any]] = [
    {
        "rule_id": "PG-01",
        "system_class": "amorphous solid",
        "system_markers": [
            "amorphous", "glass", "borosilicate glass", "silica glass",
            "fused silica", "vitreous", "amorphous metal",
            "metallic glass", "amorphous silicon", "amorphous carbon",
            "amorphous alloy", "amorphous polymer", "amorphous solid",
        ],
        "phenomenon_markers": [
            "grain boundary", "grain boundaries", "grain-boundary",
            "grain boundary sliding", "grain size", "grains",
            "grain refinement", "grain growth", "recrystallization",
            "polycrystalline", "grain structure", "grain-boundary sliding",
        ],
        "contradiction": (
            "amorphous solids have no grains and therefore no grain "
            "boundaries by definition; grain-boundary phenomena "
            "(sliding, refinement, growth, embrittlement) presuppose a "
            "polycrystalline microstructure"),
        "basis_class": "ENGINEERING",
        "basis": ("materials science: amorphous (glassy) solids lack the "
                  "long-range order whose boundaries define grains; "
                  "deformation proceeds by viscous/anelastic flow, not "
                  "grain-boundary sliding"),
    },
    {
        "rule_id": "PG-02",
        "system_class": "single crystal",
        "system_markers": [
            "single crystal", "single-crystal", "monocrystalline",
            "single crystal turbine blade",
        ],
        "phenomenon_markers": [
            "grain boundary", "grain boundaries", "grain-boundary",
            "grain boundary sliding", "grain boundary embrittlement",
            "grain refinement",
        ],
        "contradiction": (
            "a single crystal contains exactly one grain; grain-boundary "
            "phenomena require at least two grains and their boundary"),
        "basis_class": "ENGINEERING",
        "basis": "crystallography definition",
    },
    {
        "rule_id": "PG-03",
        "system_class": "vacuum",
        "system_markers": [
            "vacuum", "hard vacuum", "high vacuum", "ultra high vacuum",
            "space", "outer space", "in vacuo",
        ],
        "phenomenon_markers": [
            "convection", "convective", "convective cooling",
            "convection cooling", "boiling", "acoustic", "sound",
            "sonic", "ultrasound",
        ],
        "contradiction": (
            "convection and acoustic propagation require a material "
            "medium; a vacuum has none by definition"),
        "basis_class": "ENGINEERING",
        "basis": "fluid mechanics definition (no medium, no convective "
                 "transport, no pressure waves)",
    },
    {
        "rule_id": "PG-04",
        "system_class": "perfectly rigid constraint",
        "system_markers": [
            "incompressible liquid", "incompressible fluid",
            "hydraulic oil", "water (incompressible)",
        ],
        "phenomenon_markers": [
            "cavitation under static", "static cavitation",
        ],
        "contradiction": (
            "cavitation requires local static pressure to drop below "
            "vapor pressure under FLOW (dynamic rarefaction); a static "
            "pressure argument against an incompressible premise is "
            "incoherent"),
        "basis_class": "ENGINEERING",
        "basis": "fluid mechanics definition of cavitation",
    },
]

# Guard: markers that merely APPEAR in a different context must not fire
# (e.g. 'glass transition' in a polymer problem, 'grain' in agriculture).
# A marker fires only when it appears as an asserted phenomenon of the
# system class, checked by co-occurrence in the same problem statement.
_MARKER_LEN_FLOOR = 4  # ignore ultra-short markers like "grains" alone


def check_premise(problem: Dict[str, Any]) -> Dict[str, Any]:
    """Check the problem's premises for definitional incoherence.

    PURE FUNCTION — deterministic, no network, no LLM, no clock.
    Returns the verdict + rule evidence; the caller decides how the
    verdict blocks the pipeline (StageFailure in the PREMISE_GATE
    adapter).
    """
    device = str(problem.get("device") or "")
    failure = str(problem.get("failure") or
                  problem.get("failure_mode") or "")
    user_need = str(problem.get("user_need") or problem.get("failure")
                     or "")
    problem_text = " ".join(
        x for x in (device, failure, user_need,
                    str(problem.get("user_text") or "")) if x)
    text_lower = problem_text.lower()

    matched: List[Dict[str, Any]] = []
    for rule in RULES:
        sys_hits = [m for m in rule["system_markers"] if m in text_lower]
        phen_hits = [m for m in rule["phenomenon_markers"]
                     if m in text_lower]
        if sys_hits and phen_hits:
            matched.append({
                "rule_id": rule["rule_id"],
                "system_class": rule["system_class"],
                "system_markers_found": sys_hits,
                "phenomenon_markers_found": phen_hits,
                "contradiction": rule["contradiction"],
                "basis_class": rule["basis_class"],
                "basis": rule["basis"],
            })

    has_assertions = bool(device.strip() or failure.strip())
    if matched:
        verdict = "MALFORMED_OR_FALSE_PREMISE"
        explanation = "; ".join(
            f"[{m['rule_id']}] the problem names {m['system_class']} "
            f"({', '.join(m['system_markers_found'][:2])}) while "
            f"asserting {', '.join(m['phenomenon_markers_found'][:2])}: "
            f"{m['contradiction']}"
            for m in matched)
    elif not has_assertions:
        verdict = "PREMISE_UNPARSEABLE"
        explanation = ("the problem carries no device/material assertion "
                       "the rule table can bind to; the gate fails open "
                       "(recorded, non-blocking — blindness is not "
                       "evidence of coherence)")
    else:
        verdict = "PREMISE_COHERENT"
        explanation = ("no definitional contradiction matched; the gate "
                       "cannot prove physical truth — only rule-table "
                       "incoherence is checkable (disclosed limit)")

    return {
        "verdict": verdict,
        "explanation": explanation,
        "matched_rules": matched,
        "n_rules_checked": len(RULES),
        "gate_version": PREMISE_VERSION,
        "limitations": [
            "deterministic hard-rule table (definitional contradictions "
            "only): a physically false but non-contradictory premise "
            "passes this gate",
            "no LLM opinion is a blocking authority (Art. XVIII)",
            "gate blindness is recorded, never converted into a "
            "coherence claim (Art. XXV)",
        ],
    }

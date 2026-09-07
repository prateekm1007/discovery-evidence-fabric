"""Epistemic constants and language guards for the invention-to-3D-to-package bridge.

These rules are binding on every artifact this module produces. They encode the
Toscanini epistemic boundary between INVENTED ARCHITECTURE and INVENTED EVIDENCE:

  - invented architecture != invented evidence
  - CONCEPTUAL_3D != ENGINEERING_3D (never invent engineering dimensions for a
    conceptual model)
  - EXPERIMENTALLY VERIFIED may only come from real reality-loop evidence
  - no patentability / FTO / claim-language assertions (counsel is downstream)

Reference: handoff sections 9, 18, 29, 30, 34.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Visualizability classes (handoff section 18)
# ---------------------------------------------------------------------------

ENGINEERING_3D = "ENGINEERING_3D"
CONCEPTUAL_3D = "CONCEPTUAL_3D"
SYSTEM_3D = "SYSTEM_3D"
PROCESS_3D = "PROCESS_3D"
NOT_VISUALIZABLE = "NOT_VISUALIZABLE"

VISUALIZABILITY_CLASSES = (
    ENGINEERING_3D,
    CONCEPTUAL_3D,
    SYSTEM_3D,
    PROCESS_3D,
    NOT_VISUALIZABLE,
)

VISUALIZABILITY_MEANINGS = {
    ENGINEERING_3D: (
        "a parametric engineering model built by the CadQuery/OCCT geometry "
        "authority from sourced/declared geometry parameters; carries real "
        "dimensions, STEP/STL exports and measured geometry"
    ),
    CONCEPTUAL_3D: (
        "a conceptual visualization of a single device-form invention; "
        "represents arrangement and interaction, never engineering dimensions"
    ),
    SYSTEM_3D: (
        "a conceptual system-architecture visualization (subsystems, data and "
        "power flows); represents topology and interaction, never engineering "
        "dimensions"
    ),
    PROCESS_3D: (
        "a conceptual process-flow visualization (stages, streams); represents "
        "sequence and coupling, never engineering dimensions"
    ),
    NOT_VISUALIZABLE: (
        "no honest visual representation is supported by the recorded state"
    ),
}

# ---------------------------------------------------------------------------
# Parameter value classes (released-chain conventions, e.g. P-07)
# ---------------------------------------------------------------------------

VALUE_CLASS_MODELLED = "MODELLED"          # engine-declared design proposal inside a declared envelope
VALUE_CLASS_SOURCE_FACT = "SOURCE_FACT"    # value bound to a custody-frozen evidence span

# ---------------------------------------------------------------------------
# Package maturity (handoff section 30 — invention existence != package maturity)
# ---------------------------------------------------------------------------

PACKAGE_MATURITY_EARLY = "EARLY_TECHNICAL_EVALUATION"
PACKAGE_MATURITY_ENGINEERING = "ENGINEERING_DEFINITION"

# ---------------------------------------------------------------------------
# Language guards (handoff sections 27, 29, 34)
# ---------------------------------------------------------------------------

FORBIDDEN_ASSERTIONS = (
    "patentable",
    "patent cleared",
    "fto confirmed",
    "experimentally verified",
    "physically validated",
    "measured in reality",
)

COUNSEL_LANGUAGE = (
    "Potential IP territory — formal legal review required. Toscanini performs "
    "technology discovery; patentability, claim drafting, infringement/FTO and "
    "legal opinions are matters for qualified IP counsel."
)


class EpistemicViolation(RuntimeError):
    """Raised when an artifact would cross the epistemic boundary."""


def guard_no_engineering_dimensions(visualizability_class: str, key_dimensions: dict) -> None:
    """A conceptual artifact must not claim engineering dimensions."""
    if visualizability_class == ENGINEERING_3D:
        return
    forbidden_keys = ("volume_mm3", "wall_thickness_mm", "diameter_mm", "length_mm")
    for key in key_dimensions:
        if any(f in str(key).lower() for f in forbidden_keys):
            raise EpistemicViolation(
                f"conceptual artifact ({visualizability_class}) claims engineering "
                f"dimension '{key}' — CONCEPTUAL_3D != ENGINEERING_3D"
            )


def guard_experimental_language(maturity: dict) -> None:
    """EXPERIMENTALLY VERIFIED may only come from real reality-loop evidence."""
    if maturity.get("experimentally_verified") is True:
        loop = (maturity.get("reality_loop_state") or "NONE").upper()
        if loop in ("NONE", "", "SIMULATED", "MODELLED"):
            raise EpistemicViolation(
                "EXPERIMENTALLY VERIFIED may only come from real reality-loop "
                "evidence — reality cannot be simulated into existence"
            )


def guard_language(text: str) -> None:
    """Package/essay copy must not contain forbidden legal/validation assertions."""
    low = text.lower()
    for phrase in FORBIDDEN_ASSERTIONS:
        if phrase in low:
            # allow the *negated* guard copy we print ourselves
            ctx = low[max(0, low.find(phrase) - 60): low.find(phrase) + len(phrase) + 60]
            if "never" in ctx or "not " in ctx or "only come" in ctx or "no " in ctx:
                continue
            raise EpistemicViolation(f"forbidden assertion language: '{phrase}'")


def conceptual_disclaimer(visualizability_class: str) -> dict:
    """Standard honest label attached to every conceptual artifact."""
    return {
        "artifact": "CONCEPTUAL_3D_DISCLAIMER",
        "visualizability_class": visualizability_class,
        "meaning": VISUALIZABILITY_MEANINGS[visualizability_class],
        "rule": (
            "This visualization represents architecture topology and component "
            "interaction only. It carries NO engineering dimensions: sizes, "
            "proportions and positions are abstract presentation units, not mm, "
            "and must never be read as engineering geometry. Engineering CAD "
            "requires sourced geometry parameters and is a separate, earned "
            "artifact (ENGINEERING_3D)."
        ),
        "epistemic_boundary": "CONCEPTUAL_3D != ENGINEERING_3D",
    }

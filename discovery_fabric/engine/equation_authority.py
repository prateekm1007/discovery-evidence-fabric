"""discovery_fabric/engine/equation_authority.py — R401A A1: THE ONE
CANONICAL EQUATION AUTHORITY.

Audit result (measured, not assumed):
  equations.py             EQUATION_LIBRARY (36 domain equations,
                          FLUID-xxx ids) — the engineering-spec
                          governing-equation REGISTRY (selection +
                          applicability adjudication; consumed by the
                          portfolio/dossier builders).
  technical_equations.py  EQUATIONS (9 eq:*_v1 analytical laws) — the
                          analytical EVALUATION layer (compute_si +
                          validity_si + units + monotonicity; consumed
                          by the technical improvement engine).

  TRUE DUPLICATE: Hagen-Poiseuille appears in BOTH:
    FLUID-001:                 Q = pi * r^4 * dP / (8 * mu * L)
    eq:hagen_poiseuille_flow_v1: Q = pi * D^4 * dP / (128 * mu * L)
  With r = D/2 these are ALGEBRAICALLY IDENTICAL (r^4/8 == D^4/128).
  Everything else is layer-distinct (impedance-contrast selection vs
  reflection-ratio computation, PV conversion law vs delivered-power
  evaluation, etc.) — unique behavior, preserved untouched.

This module is the single authority for every law BOTH layers share.
Each layer keeps its own machinery (selection vs computation) but the
shared law's identity — canonical form, SI symbol table, units,
assumptions, provenance, numerical evaluation — is defined HERE once
(Art. X: one authority; Art. XI: the superseded standalone definitions
are archived, retrievable in git history).

Pinned by tests/test_r401_stream_a.py: equivalence (both ids resolve to
the same law), numerical regression, provenance regression.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

AUTHORITY_VERSION = "equation_authority/1.0.0"

# ---------------------------------------------------------------------------
# The canonical shared-law registry
# ---------------------------------------------------------------------------
CANONICAL_LAWS: Dict[str, Dict[str, Any]] = {
    "hagen_poiseuille": {
        "canonical_id": "law:hagen_poiseuille",
        "authority_version": AUTHORITY_VERSION,
        "name": "Hagen–Poiseuille laminar volumetric flow",
        "canonical_form": "Q = pi * D^4 * dP / (128 * mu * L)",
        "equivalent_forms": {
            "radius_form": "Q = pi * r^4 * dP / (8 * mu * L)   "
                           "[r = D/2]",
            "diameter_form": "Q = pi * D^4 * dP / (128 * mu * L)"},
        "domain": "fluidics",
        "relation_epistemic_class": "ANALYTICAL_LAW",
        "provenance": (
            "closed-form solution of the Navier–Stokes equations for "
            "steady incompressible laminar flow of a Newtonian fluid "
            "in a long circular tube; a conservation-derived analytical "
            "law, not a fit; the BINDING to a candidate is a declared "
            "model relation (rank-4 COMPUTATIONAL_RESULT outputs once "
            "computed, Art. XXXVIII)"),
        "symbol_table": [
            {"symbol": "Q", "description": "volumetric flow rate",
             "unit_si": "m^3/s", "canonical": True},
            {"symbol": "D", "description": "lumen diameter",
             "unit_si": "m", "canonical": True},
            {"symbol": "r", "description": "lumen radius (r = D/2)",
             "unit_si": "m", "canonical": False},
            {"symbol": "dP", "description": "pressure drop",
             "unit_si": "Pa", "canonical": True},
            {"symbol": "mu", "description": "dynamic viscosity",
             "unit_si": "Pa.s", "canonical": True},
            {"symbol": "L", "description": "lumen length",
             "unit_si": "m", "canonical": True},
        ],
        "assumptions": [
            "steady, incompressible, Newtonian fluid",
            "fully developed laminar flow (Re < 2300, L/D >= 10)",
            "rigid circular cross-section of constant diameter",
        ],
        "layer_aliases": {
            "equations.py": "FLUID-001",
            "technical_equations.py": "eq:hagen_poiseuille_flow_v1",
        },
        "monotonicity": {"lumen_diameter": 1, "flow_path_length": -1,
                         "viscosity": -1, "pressure_drop": 1},
        "compute_si": "_hp_flow (in this module)",
        "validity_si": "_hp_validity (in this module)",
    },
}


def canonical_law(name: str) -> Optional[Dict[str, Any]]:
    """Resolve a canonical law by canonical id or ANY layer alias."""
    key = name.removeprefix("law:")
    if key in CANONICAL_LAWS:
        return CANONICAL_LAWS[key]
    for law in CANONICAL_LAWS.values():
        if name in law["layer_aliases"].values():
            return law
    return None


def resolve_alias(layer: str, layer_equation_id: str) -> Optional[str]:
    """Map a layer-local equation id to the canonical law id."""
    for law in CANONICAL_LAWS.values():
        if law["layer_aliases"].get(layer) == layer_equation_id:
            return law["canonical_id"]
    return None


# ---------------------------------------------------------------------------
# The canonical numerical evaluation (one implementation, both layers
# call it — the two historical standalone implementations are retired
# to git history; their equivalence is pinned by regression tests)
# ---------------------------------------------------------------------------
def hagen_poiseuille_flow_si(diameter_m: float, pressure_drop_Pa: float,
                             viscosity_Pa_s: float,
                             length_m: float) -> float:
    """Q = pi * D^4 * dP / (128 * mu * L)  [SI: m^3/s]."""
    return (math.pi * diameter_m ** 4 * pressure_drop_Pa
            / (128.0 * viscosity_Pa_s * length_m))


def hagen_poiseuille_validity_si(diameter_m: float,
                                 pressure_drop_Pa: float,
                                 viscosity_Pa_s: float,
                                 length_m: float,
                                 density_kg_m3: Optional[float] = None
                                 ) -> List[Dict[str, Any]]:
    """The law's assumption checks (deterministic, shared): laminar
    regime + developed flow + geometric scale, the SAME validity
    contract the analytical layer enforced."""
    checks: List[Dict[str, Any]] = []
    if density_kg_m3 is not None and diameter_m > 0 \
            and viscosity_Pa_s > 0:
        v_mean = 0.0  # filled below when computable
        # Re = rho * v * D / mu with v = Q/A
        q = hagen_poiseuille_flow_si(
            diameter_m, pressure_drop_Pa, viscosity_Pa_s, length_m)
        area = math.pi * diameter_m ** 2 / 4.0
        v_mean = q / area if area else 0.0
        re = density_kg_m3 * v_mean * diameter_m / viscosity_Pa_s
        checks.append({
            "class": "REGIME",
            "check": "laminar (Re < 2300)",
            "value": round(re, 2),
            "ok": re < 2300.0,
        })
    if length_m and diameter_m:
        ld = length_m / diameter_m
        checks.append({
            "class": "DEVELOPED",
            "check": "L/D >= 10 (fully developed)",
            "value": round(ld, 2),
            "ok": ld >= 10.0,
        })
    if diameter_m:
        checks.append({
            "class": "SCALE",
            "check": "0.1 um .. 1 m (equation_authority range)",
            "value": diameter_m,
            "ok": 1e-7 <= diameter_m <= 1.0,
        })
    return checks

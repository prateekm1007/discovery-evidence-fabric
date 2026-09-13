"""Visualizability classifier — decides which honest 3D representation an
invention supports, from MEASURED features of the recorded run state.

Decision basis is fully recorded: every classification carries the measurements
that produced it, so the frontend (and the buyer) can audit why a run received
SYSTEM_3D rather than ENGINEERING_3D. The UI never decides this (handoff 20/29).

Classification (handoff section 18):

    ENGINEERING_3D    physical invention with sourced/declared geometry
                      parameters sufficient for a parametric CadQuery build
    SYSTEM_3D         >= 2 subsystems, no sourced geometry parameters ->
                      conceptual system-architecture visualization
    CONCEPTUAL_3D     single device-form invention, no sourced parameters ->
                      conceptual device visualization
    PROCESS_3D        process/flow invention (stage chain) ->
                      conceptual process visualization
    NOT_VISUALIZABLE  no physical substrate at all (pure algorithm/policy)
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from ..domains import physical_site_vocabulary
from .epistemics import (
    CONCEPTUAL_3D,
    ENGINEERING_3D,
    NOT_VISUALIZABLE,
    PROCESS_3D,
    SYSTEM_3D,
)

# ---------------------------------------------------------------------------
# Measured feature extraction
# ---------------------------------------------------------------------------

_NON_NUMERIC = {"UNKNOWN", "NOT ESTABLISHED", "NOT_ESTABLISHED", "", "NONE", "TBD", "N/A"}

# ---------------------------------------------------------------------------
# R452 A4 — the physical-site vocabulary (one authority: the registry)
# ---------------------------------------------------------------------------
# The pre-R452 check was a closed 27-noun regex and independently blocked
# ENGINEERING_3D on 4/6 real physical inventions (no "vial", no
# "lyophilizer", no "die", no "punch"). The vocabulary is now DERIVED
# from the engine's own canonical domain registry (one authority, Art. X)
# so the site check can never be narrower than the registry. The
# derivation, its exclusion rules and its basis are recorded and travel
# in every classification (the vocabulary is a threshold WITH provenance,
# Art. XXVII).

def _build_physical_site_pattern() -> tuple:
    words, basis = physical_site_vocabulary()
    ordered = sorted(words, key=len, reverse=True)
    pattern = re.compile(
        r"\b(" + "|".join(re.escape(w) for w in ordered) + r")\b",
        re.I,
    )
    return pattern, basis

_PHYSICAL_SITE_PATTERN, _PHYSICAL_SITE_BASIS = _build_physical_site_pattern()

_PROCESS_SIGNALS = re.compile(
    r"\b(process|synthesis|annealing|deposition|etching|refining|fermentation|"
    r"separation|distillation|catalysis|flow route|manufacturing route)\b",
    re.I,
)

_ALGORITHM_SIGNALS = re.compile(
    r"\b(algorithm|protocol|policy|software|workflow|control law|scheduler|"
    r"optimization framework|pricing|method for)\b",
    re.I,
)


def _numeric(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if text.upper() in _NON_NUMERIC:
        return None
    try:
        return float(text.split()[0])
    except (ValueError, IndexError):
        return None


def _geometry_parameters(engineering_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Geometry-capable parameters: numeric value + unit, from either the
    released-chain parameters list or the run's critical_parameters."""
    found: List[Dict[str, Any]] = []

    for p in engineering_spec.get("parameters") or []:
        if not isinstance(p, dict):
            continue
        if _numeric(p.get("value")) is not None and p.get("unit"):
            found.append({
                "param_id": p.get("param_id") or p.get("name"),
                "unit": p.get("unit"),
                "value": _numeric(p.get("value")),
                "envelope": p.get("envelope"),
                "value_class": p.get("value_class") or "MODELLED",
                "origin": "engineering_spec.parameters",
            })

    core = engineering_spec.get("engineering_core") or {}
    for p in core.get("critical_parameters") or []:
        if not isinstance(p, dict):
            continue
        value_status = str(p.get("value_status") or "").upper()
        val = _numeric(p.get("value"))
        if val is not None and "UNKNOWN" not in value_status and p.get("unit"):
            # R452 A2 (external audit): the param id carried into the
            # build chain is the SEMANTIC name ("device outer diameter"),
            # never the registry's positional id ("CP-001") — the
            # measured defect: every CP-nnn key missed the FORM_LIBRARY
            # builders' semantic lookups and every build fell through to
            # hardcoded defaults, producing byte-identical geometry for
            # specs differing 80x. The positional id rides along as
            # provenance (never lost, never the join key).
            found.append({
                "param_id": (p.get("parameter") or p.get("name")
                             or p.get("parameter_id")),
                "parameter_id": p.get("parameter_id"),
                "unit": p.get("unit"),
                "value": val,
                "envelope": p.get("envelope"),
                "value_class": p.get("value_status") or p.get("basis")
                or "MODELLED",
                "source": p.get("source"),
                "source_hash": p.get("source_hash"),
                "origin": "engineering_core.critical_parameters",
            })

    return found


def _subsystems(engineering_spec: Dict[str, Any]) -> List[str]:
    arch = engineering_spec.get("system_architecture") or {}
    names: List[str] = []
    for s in arch.get("subsystems") or []:
        if isinstance(s, dict) and s.get("name"):
            names.append(str(s["name"]))
        elif isinstance(s, str):
            names.append(s)
    return names


def _intervention_site(final_state: Dict[str, Any], cio_identity: Dict[str, Any],
                       run_result: Dict[str, Any]) -> str:
    def unwrap(obj: Any) -> Any:
        if isinstance(obj, dict) and isinstance(obj.get("value"), (dict, str)):
            return obj.get("value")
        return obj

    candidates = []
    cc = final_state.get("causal_chain") or {}
    candidates.append(cc.get("intervention_site") if isinstance(cc, dict) else None)
    inv = run_result.get("invention_specification") or {}
    inv_cc = unwrap(inv.get("causal_chain"))
    if isinstance(inv_cc, dict):
        candidates.append(inv_cc.get("intervention_site"))
    inv_problem = unwrap(inv.get("problem"))
    if isinstance(inv_problem, dict):
        candidates.append(inv_problem.get("device"))
    candidates.append((cio_identity or {}).get("intervention_site"))
    candidates.append(run_result.get("final_state", {}).get("device"))
    for c in candidates:
        if c and isinstance(c, str) and c.strip() and "UNKNOWN" not in c.upper():
            return c.strip()
    return ""


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

ENGINEERING_MIN_PARAMS = 3  # sourced/declared geometry params needed for parametric CAD


def classify(run_result: Dict[str, Any], cio: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Classify the invention's honest visualizability from recorded state.

    Returns a dict with:
      visualizability_class, basis (measured counts), subsystems,
      geometry_parameters, intervention_site, physical_form
    """
    cio = cio or {}
    final_state = run_result.get("final_state") or {}
    engineering_spec = run_result.get("engineering_specification") or {}
    cio_identity = cio.get("identity") or {}
    invention = run_result.get("invention_specification") or {}

    geo_params = _geometry_parameters(engineering_spec)
    subsystems = _subsystems(engineering_spec)
    site = _intervention_site(final_state, cio_identity, run_result)

    mechanism = str(
        (final_state.get("causal_chain") or {}).get("mechanism")
        or cio_identity.get("mechanism")
        or ""
    )
    intervention = str(
        (final_state.get("causal_chain") or {}).get("intervention")
        or cio_identity.get("intervention")
        or ""
    )
    combined = " ".join([site, mechanism, intervention,
                         str(invention.get("mechanism") or "")])

    physical_site = bool(_PHYSICAL_SITE_PATTERN.search(combined))
    process_signal = bool(_PROCESS_SIGNALS.search(combined))
    algorithm_signal = bool(_ALGORITHM_SIGNALS.search(combined))

    # --- decision ladder (recorded, deterministic) -------------------------
    if not physical_site and algorithm_signal and not subsystems:
        chosen, reason = NOT_VISUALIZABLE, (
            "no physical intervention site detected in the recorded causal chain; "
            "invention is algorithmic/computational"
        )
    elif len(geo_params) >= ENGINEERING_MIN_PARAMS and physical_site:
        chosen, reason = ENGINEERING_3D, (
            f"{len(geo_params)} geometry-capable parameters with numeric values "
            f"and units recorded, physical intervention site '{site}'"
        )
    elif len(subsystems) >= 2:
        chosen, reason = SYSTEM_3D, (
            f"{len(subsystems)} recorded subsystems and only "
            f"{len(geo_params)} sourced geometry parameters — conceptual "
            "system-architecture visualization (topology, not dimensions)"
        )
    elif process_signal and not physical_site:
        chosen, reason = PROCESS_3D, (
            "process/flow invention without a single physical device form"
        )
    else:
        chosen, reason = CONCEPTUAL_3D, (
            f"single device-form invention (site '{site}'), "
            f"{len(geo_params)} sourced geometry parameters — conceptual "
            "device visualization"
        )

    return {
        "visualizability_class": chosen,
        "classification_basis": {
            "geometry_parameters_sourced": len(geo_params),
            "subsystems_recorded": len(subsystems),
            "physical_site_detected": physical_site,
            # R452 A4: the vocabulary the site decision consumed — a
            # threshold WITH provenance (Art. XXVII), recorded per
            # classification
            "physical_site_vocabulary": {
                "n_words": _PHYSICAL_SITE_BASIS["n_words"],
                "authority": _PHYSICAL_SITE_BASIS["authority"],
                "registry_domains_excluded":
                    _PHYSICAL_SITE_BASIS["registry_domains_excluded"],
                "layers_used": _PHYSICAL_SITE_BASIS["layers_used"],
            },
            "process_signal": process_signal,
            "algorithmic_signal": algorithm_signal,
            "intervention_site": site,
            "engineering_min_params": ENGINEERING_MIN_PARAMS,
            "reason": reason,
            "measured_from": ["engineering_specification.parameters",
                              "engineering_specification.engineering_core.critical_parameters",
                              "engineering_specification.system_architecture.subsystems",
                              "final_state.causal_chain"],
        },
        "subsystems": subsystems,
        "geometry_parameters": geo_params,
        "intervention_site": site,
    }

"""discovery_fabric/engine/parameter_join.py — R452: THE PARAMETER JOIN.

Constitution v2.5.0, Articles LXXIV + LX (as amended):

> Numerical values may enter canonical state only as SOURCE_FACT,
> COMPUTED, or MODELLED values with provenance, derivation, units, and
> uncertainty appropriate to their class. (LXXIV)

> Every physical invention candidate that reaches engineering evaluation
> must either produce a provenance-backed parameterized representation or
> a typed explanation of the missing evidence and the smallest action
> capable of supplying it. (LX)

This module joins the value-sourcing organ's typed bindings onto the
engineering specification the classifier consumes — the exact join the
external audit found missing (producer emitted named parameters with no
values; classifier found nothing; ENGINEERING_3D unreachable).

THE JOIN (deterministic, recorded):

    critical-parameter bindings (physics params, any unit family)
      + geometry slot bindings (LENGTH-family SOURCE_FACTs)
      + MODELLED envelope fills for the routed form's remaining slots
        (basis: the FORM_LIBRARY's documented default envelope — a
        parametric DESIGN PROPOSAL, never evidence)
    -> engineering_spec.parameters[] (the classifier's contract:
       param_id / unit / value / envelope / value_class / provenance)

VALIDATION (the machine-enforced Article LXXIV guard):

    validate_typed_parameter() rejects:
      - a naked number (no class / no provenance)
      - a MODELLED value masquerading as SOURCE_FACT (class tamper)
      - a SOURCE_FACT without verifiable custody (source id + span +
        content hash)
      - a MODELLED value outside its declared envelope

reviewer_provenance: AI_REVIEW (Art. LXVII).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

ORGAN = "PARAMETER_JOIN"
ORGAN_VERSION = "1.0.0"

_LENGTH_UNITS = {"mm", "millimeter", "millimetre", "MM"}


def is_length_unit(unit: str) -> bool:
    return (unit or "").strip() in _LENGTH_UNITS


# ---------------------------------------------------------------------------
# MODELLED envelopes for the parametric form families (Art. LXXIV: the
# envelope basis is recorded provenance — the FORM_LIBRARY's documented
# engineering defaults, i.e. a declared design proposal, NOT evidence).
# ---------------------------------------------------------------------------

FORM_DEFAULT_ENVELOPES: Dict[str, Dict[str, Dict[str, Any]]] = {
    "layered_panel": {
        "panel_width": {"default": 160.0, "envelope": [80.0, 400.0]},
        "panel_length": {"default": 160.0, "envelope": [80.0, 400.0]},
        "substrate_t": {"default": 3.0, "envelope": [0.5, 10.0]},
        "cell_t": {"default": 0.2, "envelope": [0.05, 2.0]},
        "functional_t": {"default": 0.5, "envelope": [0.1, 3.0]},
        "frame_w": {"default": 10.0, "envelope": [2.0, 40.0]},
    },
    "dual_lumen_catheter": {
        "outer_diameter": {"default": 3.0, "envelope": [1.0, 8.0]},
        "primary_lumen_diameter": {"default": 1.1, "envelope": [0.3, 3.0]},
        "floor_lumen_diameter": {"default": 0.6, "envelope": [0.2, 1.5]},
        "floor_offset": {"default": 1.0, "envelope": [0.2, 3.0]},
        "length": {"default": 100.0, "envelope": [50.0, 1500.0]},
    },
    "cylindrical_device": {
        "outer_diameter": {"default": 20.0, "envelope": [2.0, 200.0]},
        "height": {"default": 50.0, "envelope": [5.0, 500.0]},
        "wall_thickness": {"default": 2.0, "envelope": [0.5, 20.0]},
        "port_diameter": {"default": 5.0, "envelope": [1.0, 50.0]},
    },
}

_ENVELOPE_BASIS = (
    "engineering_geometry.FORM_LIBRARY documented default envelope for "
    "the routed form family — a parametric DESIGN PROPOSAL with design "
    "freedom declared inside the envelope; explicitly NOT evidence "
    "(Constitution v2.5.0 Art. LXXIV; never citable as a factual claim)")


# ---------------------------------------------------------------------------
# The typed-parameter validator (Article LXXIV machine guard)
# ---------------------------------------------------------------------------

class NakedNumberError(ValueError):
    """A value without class+provenance attempted to enter canonical
    state (Constitution v2.5.0 Art. LXXIV)."""


def validate_typed_parameter(p: Dict[str, Any]) -> Dict[str, Any]:
    """Fail-closed validation of one typed parameter record. Raises
    NakedNumberError on any Article LXXIV violation."""
    if not isinstance(p, dict):
        raise NakedNumberError("parameter record is not a dict")
    cls = p.get("value_class")
    if cls not in ("SOURCE_FACT", "COMPUTED", "MODELLED"):
        raise NakedNumberError(
            f"parameter {p.get('param_id')!r} carries value "
            f"{p.get('value')!r} without a lawful value class — "
            "that is a NAKED NUMBER (invented; Art. XXVII/LXXIV). "
            "BLOCKED.")
    prov = p.get("provenance")
    if not isinstance(prov, dict) or not prov:
        raise NakedNumberError(
            f"parameter {p.get('param_id')!r} class {cls} carries no "
            "provenance — naked number (Art. LXXIV). BLOCKED.")
    value = p.get("value")
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise NakedNumberError(
            f"parameter {p.get('param_id')!r} value {value!r} is not "
            "numeric (the join only admits numeric typed values)")
    if not p.get("unit"):
        raise NakedNumberError(
            f"parameter {p.get('param_id')!r} carries no unit — "
            "un-unit-ed numbers cannot enter canonical state (Art. XXVII)")
    if cls == "SOURCE_FACT":
        for key in ("source_id", "span", "content_hash"):
            if not prov.get(key):
                raise NakedNumberError(
                    f"parameter {p.get('param_id')!r} claims SOURCE_FACT "
                    f"without {key} — the custody chain is broken "
                    "(Art. VI/XII), or a MODELLED value is masquerading "
                    "as sourced (Art. XXVIII). BLOCKED.")
    if cls == "MODELLED":
        env = p.get("envelope")
        if (not isinstance(env, list) or len(env) != 2
                or not all(isinstance(x, (int, float)) for x in env)):
            raise NakedNumberError(
                f"parameter {p.get('param_id')!r} MODELLED without a "
                "declared [lo, hi] envelope — an unbounded design "
                "proposal is indistinguishable from an invented number "
                "(Art. XXVII/LXXIV). BLOCKED.")
        if not (env[0] <= value <= env[1]):
            raise NakedNumberError(
                f"parameter {p.get('param_id')!r} MODELLED value "
                f"{value} outside its declared envelope {env}. BLOCKED.")
        if not prov.get("envelope_basis"):
            raise NakedNumberError(
                f"parameter {p.get('param_id')!r} MODELLED without an "
                "envelope basis — 'seems reasonable' is forbidden "
                "(Art. XXVII). BLOCKED.")
    if cls == "COMPUTED" and not prov.get("derivation"):
        raise NakedNumberError(
            f"parameter {p.get('param_id')!r} claims COMPUTED without a "
            "recorded derivation (Art. LXXIV). BLOCKED.")
    return p


# ---------------------------------------------------------------------------
# The join
# ---------------------------------------------------------------------------

def _intervention_site(run_result: Dict[str, Any],
                       spec: Dict[str, Any]) -> str:
    for getter in (
            lambda: ((run_result or {}).get("final_state") or {}).get(
                "device"),
            lambda: ((run_result or {}).get("problem") or {}).get("device"),
            lambda: (spec.get("applicability") or {}).get("device"),
    ):
        v = getter()
        if v and isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _subsystems(spec: Dict[str, Any]) -> List[str]:
    arch = spec.get("system_architecture") or {}
    out: List[str] = []
    for s in arch.get("subsystems") or []:
        if isinstance(s, dict) and s.get("name"):
            out.append(str(s["name"]))
        elif isinstance(s, str):
            out.append(s)
    return out


def join_parameters(engineering_spec: Dict[str, Any],
                    sourcing_record: Dict[str, Any],
                    run_result: Optional[Dict[str, Any]] = None,
                    ) -> Dict[str, Any]:
    """Join the sourcing organ's typed bindings onto the engineering
    specification. Returns {spec, join_report, physical_site}.

    The returned spec is a COPY — the producer's committed artifact is
    never mutated in place (Art. IX)."""
    from discovery_fabric.engine.invention_bridge import (
        engineering_geometry)

    spec = json_copy(engineering_spec or {})
    sourcing_record = sourcing_record or {}
    run_result = run_result or {}

    site = _intervention_site(run_result, spec)
    subsystems = _subsystems(spec)
    form = engineering_geometry.route_form(site, subsystems)

    geometry_bindings: Dict[str, Dict] = dict(
        sourcing_record.get("geometry_bindings") or {})
    envelopes = FORM_DEFAULT_ENVELOPES.get(form) or {}

    parameters: List[Dict[str, Any]] = []
    records: List[Dict[str, Any]] = []
    counts = {"SOURCE_FACT": 0, "COMPUTED": 0, "MODELLED": 0, "UNKNOWN": 0}
    envelope_rejections: List[Dict[str, Any]] = []

    # --- 1. geometry slots for the routed form --------------------------
    for slot, env in envelopes.items():
        bound = geometry_bindings.get(slot)
        use_bound = bound is not None and is_length_unit(
            bound.get("unit") or "mm")
        if use_bound:
            # envelope sanity (Art. XXI.4 relevance discipline): a fact
            # whose magnitude falls outside the form family's physical
            # envelope — e.g. an accelerator's '230 m' read as a laptop
            # outer diameter — is not a dimension of THIS device class.
            lo, hi = env["envelope"]
            if not (lo * 0.5 <= float(bound["value"]) <= hi * 2.0):
                envelope_rejections.append({
                    "slot": slot,
                    "span": (bound.get("provenance") or {}).get("span"),
                    "source_id": (bound.get("provenance") or {}).get(
                        "source_id"),
                    "value_mm": bound["value"],
                    "envelope": env["envelope"],
                    "rejection_reason": (
                        "magnitude outside the form family envelope "
                        "(expanded x0.5-x2.0) — unit or relevance "
                        "mismatch; not a dimension of this device class "
                        "(Art. XXI.4)"),
                })
                use_bound = False
        if use_bound:
            p = {
                "param_id": f"GEOM-{slot}",
                "unit": "mm",
                "value": float(bound["value"]),
                "envelope": env["envelope"],
                "value_class": "SOURCE_FACT",
                "provenance": bound["provenance"],
                "origin": "value_sourcing.geometry_bindings",
            }
        else:
            p = {
                "param_id": f"GEOM-{slot}",
                "unit": "mm",
                "value": float(env["default"]),
                "envelope": list(env["envelope"]),
                "value_class": "MODELLED",
                "provenance": {
                    "envelope_basis": _ENVELOPE_BASIS,
                    "form": form,
                    "design_proposal": (
                        "the parametric build uses the form family's "
                        "documented default; the declared envelope is the "
                        "design freedom — a buyer or measurement can move "
                        "the value anywhere inside it"),
                },
                "origin": "parameter_join.form_default_envelope",
            }
        validate_typed_parameter(p)
        counts[p["value_class"]] += 1
        parameters.append(p)
        records.append(_public_record(p, slot))

    # --- 2. critical-parameter bindings (physics params, any family) ----
    for b in sourcing_record.get("parameters") or []:
        if b.get("value_class") in ("SOURCE_FACT", "COMPUTED"):
            p = {
                "param_id": b.get("param_id") or b.get("parameter"),
                "unit": b.get("unit") or "",
                "value": float(b["value"]),
                "envelope": None,
                "value_class": b["value_class"],
                "provenance": b["provenance"],
                "origin": "value_sourcing.critical_parameters",
            }
            validate_typed_parameter(p)
            counts[p["value_class"]] += 1
            parameters.append(p)
            records.append(_public_record(p, b.get("parameter")))
        elif b.get("value_class") == "UNKNOWN":
            counts["UNKNOWN"] += 1
            records.append({
                "param_id": b.get("param_id"),
                "parameter": b.get("parameter"),
                "unit": b.get("unit"),
                "value_class": "UNKNOWN",
                "next_action": b.get("next_action"),
            })

    # --- 3. write the classifier's contract field ------------------------
    spec["parameters"] = parameters
    spec["parameter_provenance"] = {
        "organ": ORGAN,
        "organ_version": ORGAN_VERSION,
        "value_class_counts": counts,
        "records": records,
    }

    # --- 4. enrich engineering_core.critical_parameters (typed values) --
    core = spec.get("engineering_core")
    if isinstance(core, dict):
        by_id = {b.get("param_id"): b
                 for b in sourcing_record.get("parameters") or []}
        enriched = []
        for cp in core.get("critical_parameters") or []:
            b = by_id.get(cp.get("parameter_id"))
            if b and b.get("value_class") in ("SOURCE_FACT", "COMPUTED"):
                cp = dict(cp)
                cp["value"] = b["value"]
                cp["value_status"] = ("SOURCED" if b["value_class"]
                                      == "SOURCE_FACT" else "COMPUTED")
                cp["basis"] = (
                    f"{b['value_class']} via value_sourcing "
                    "(Constitution v2.5.0 Art. LXXIV)")
                cp["source"] = (b.get("provenance") or {}).get("source_id")
                cp["source_hash"] = (b.get("provenance") or {}).get(
                    "content_hash")
            enriched.append(cp)
        core["critical_parameters"] = enriched

    # --- 5. physical-site validation (the R452 PHYSICAL SITE step) ------
    from discovery_fabric.engine.invention_bridge import classifier as _clf
    site_signal = bool(_clf._PHYSICAL_SITE_SIGNALS.search(
        " ".join([site, " ".join(subsystems)])))
    length_params = [p for p in parameters if is_length_unit(p.get("unit"))]
    physical_site = {
        "intervention_site": site or None,
        "physical_site_detected": site_signal,
        "site_basis": ("classifier._PHYSICAL_SITE_SIGNALS over the "
                       "intervention site + subsystem names"),
        "subsystem_count": len(subsystems),
        "length_family_parameters": len(length_params),
        "form": form,
        "sufficient_for_engineering": (
            site_signal and len(length_params) >= 3),
        "note": (
            "a physical intervention site with >=3 length-family typed "
            "parameters opens the ENGINEERING_3D path (Constitution "
            "v2.5.0 Art. LX amendment); no site signal honestly remains "
            "CONCEPTUAL/NOT_VISUALIZABLE"),
    }

    join_report = {
        "organ": ORGAN,
        "organ_version": ORGAN_VERSION,
        "joined_parameter_count": len(parameters),
        "value_class_counts": counts,
        "form": form,
        "geometry_slots": {
            slot: {
                "value_class": (geometry_bindings.get(slot) or {}).get(
                    "value_class", "MODELLED"),
                "value": (geometry_bindings.get(slot) or {}).get(
                    "value", env["default"]),
            }
            for slot, env in envelopes.items()},
        "envelope_rejections": envelope_rejections,
        "parameter_records": records,
    }
    return {"spec": spec, "join_report": join_report,
            "physical_site": physical_site}


def _public_record(p: Dict[str, Any], name: Optional[str]) -> Dict[str, Any]:
    pub = dict(p)
    pub["parameter"] = name or p.get("param_id")
    return pub


def json_copy(obj: Any) -> Any:
    import json as _json
    return _json.loads(_json.dumps(obj, default=str))

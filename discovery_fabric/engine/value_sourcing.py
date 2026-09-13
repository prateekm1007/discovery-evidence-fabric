"""discovery_fabric/engine/value_sourcing.py — R452 (external audit
A1): THE evidence->dimension binding stage.

THE MEASURED DEFECT THIS MODULE CLOSES (external audit 2026-09-13,
E3a/E3b, root cause A1):

    engineering_spec._build_critical_parameters hardcoded
    "value": "UNKNOWN (no sourced value)" / "value_status":
    "UNKNOWN" into EVERY critical parameter, and no other production
    code ever wrote those fields. The classifier requires >= 3
    numeric+unit parameters for ENGINEERING_3D; the numerator was
    identically zero, so ENGINEERING_3D was UNREACHABLE, CadQuery/
    OCCT was dead code in production, and no STEP/STL ever existed.

THE CONSTITUTIONAL COLLISION, RESOLVED EXPLICITLY (audit Coder-1
action 2): Article XXVII forbids INVENTING thresholds — it does NOT
forbid SOURCING a value from evidence with a provenance hash. This
module binds each critical parameter to a legitimate source, in a
fixed precedence:

  1. SOURCE_FACT  — a number+unit declared in the PROBLEM STATEMENT
                    itself (the operator's own custodied text), with
                    the EXACT character span, the verbatim raw text,
                    and a sha256 of the span (Art. II: exact evidence
                    beats semantic plausibility; Art. XII: custody).
  2. COMPUTED     — a value computed by the deterministic mechanistic
                    solver chain (R452 Phase 5: the 1D hydraulic
                    Poiseuille network solver), carrying the solver
                    version + input/output hashes (Art. XXXVIII layer
                    4; a computation, never an observation).
  3. MODELLED     — a value declared by the candidate's own
                    architecture/derivation trace (the invention's
                    declared design), tagged as model content, never
                    evidence.

  A parameter with NO legitimate source STAYS UNKNOWN — Article XXVII
  is preserved, and the ABSENCE becomes a measured fact rather than a
  universal constant (the audit's exact words).

Name-aware binding (audit A2): each parameter is bound by its
SEMANTIC name (the registry's own parameter name — "outer diameter",
"lumen length", "viscosity"...) to the matching quantity class, so
the classifier's param_id is the semantic name and the
normalize_parameters join reaches the FORM_LIBRARY builders.

Constitutional anchors: Art. II (exact spans), Art. VI (provenance
never manufactured — source_hash is the span's own sha256), Art.
XXVII (no threshold invention — every threshold carries its source),
Art. LX (engineering representability REACHABLE), Art. LIII
(COMPUTED never silently becomes an observation).
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Optional, Tuple

from . import mechanistic_solver as ms

VALUE_SOURCING_VERSION = "value_sourcing/1.0.0"

#: the closed value_status vocabulary (the audit's Coder-1 action 2)
VALUE_STATUSES = ("SOURCE_FACT", "COMPUTED", "MODELLED", "UNKNOWN")

#: semantic-name -> quantity-class binding vocabulary (the name-join
#: the parameter records have always carried; deterministic)
_NAME_CLASS_RULES: List[Tuple[Tuple[str, ...], str]] = [
    (("viscosity", "dynamic viscosity"), "viscosity_mPa_s"),
    (("outer diameter", "outer dia", "body diameter", "housing "
      "diameter", "pipe diameter", "tube diameter", "cannula "
      "diameter", "branch diameter", "lumen diameter", "primary "
      "lumen", "bore", "inner diameter", "internal diameter"),
     "diameter_mm"),
    (("length", "length of", "segment length", "branch length",
      "tube length", "cannula length", "flow path length",
      "residence length"), "length_mm"),
    (("pressure", "supply pressure", "inlet pressure", "upstream "
      "pressure", "operating pressure", "delivery pressure"),
     "pressure_mmHg"),
    (("flow", "flow rate", "volumetric flow", "required flow",
      "target flow", "delivery rate", "throughput"),
     "flow_ml_min"),
]

#: canonical engineering variable per quantity class (the mechanistic
#: chain's own canonical variables — ONE namespace, Art. X)
_CLASS_TO_VARIABLE = {
    "viscosity_mPa_s": "viscosity_mPa_s",
    "diameter_mm": "primary_diameter_mm",
    "length_mm": "primary_length_mm",
    "pressure_mmHg": "inlet_pressure_mmHg",
    "flow_ml_min": "required_flow_ml_min",
}


def _semantic_class(parameter_name: str) -> Optional[str]:
    """Bind a parameter's SEMANTIC name to a quantity class
    (deterministic; longest-match-first over the rule table)."""
    name = " " + re.sub(r"[_\-]+", " ", str(parameter_name or "")
                        .strip().lower()) + " "
    best = None
    best_len = 0
    for keys, cls in _NAME_CLASS_RULES:
        for key in keys:
            if key in name and len(key) > best_len:
                best = cls
                best_len = len(key)
    return best


def _span_hash(text: str, span: Tuple[int, int]) -> str:
    return hashlib.sha256(
        text[span[0]:span[1]].encode("utf-8")).hexdigest()


def source_critical_parameters(
        critical_parameters: List[Dict[str, Any]],
        problem_text: str,
        mechanistic_record: Optional[Dict[str, Any]] = None,
        candidate_parameters: Optional[Dict[str, Dict[str, Any]]] = None
        ) -> List[Dict[str, Any]]:
    """THE VALUE_SOURCING stage: bind each critical parameter record
    to a legitimate source (fixed precedence SOURCE_FACT > COMPUTED >
    MODELLED; no source -> STAYS UNKNOWN).

    Mutates nothing: returns NEW parameter records (the caller
    replaces its list). Each sourced record carries:
      value (float), unit, value_status, source, source_hash,
      derivation, envelope (bounds context when the problem states
      one), and sourcing_version.
    """
    cand = candidate_parameters or {}
    # the problem's own declared quantities, with exact spans
    quantities = ms.classify_length_quantities(
        problem_text or "", ms.extract_quantities(problem_text or ""))

    # the mechanistic chain's canonical variables (COMPUTED arm)
    mech_vars: Dict[str, Dict[str, Any]] = {}
    if mechanistic_record:
        for arm in ("candidate_arm", "baseline_arm"):
            vset = ((mechanistic_record.get("canonical_variables")
                     or {}).get(arm) or {}).get("variables") or {}
            for k, v in vset.items():
                if isinstance(v.get("value"), (int, float)) and \
                        k not in mech_vars:
                    mech_vars[k] = v

    out: List[Dict[str, Any]] = []
    sourcing_counts = {"SOURCE_FACT": 0, "COMPUTED": 0,
                       "MODELLED": 0, "UNKNOWN": 0}
    for p in critical_parameters:
        q = dict(p)
        pname = str(p.get("parameter") or p.get("name") or "")
        cls = _semantic_class(pname)

        # --- 1. SOURCE_FACT: the problem statement's own number -----
        bound = None
        if cls:
            qcls = {"diameter_mm": ("diameter_mm",
                                    "diameter_or_length_mm"),
                    "length_mm": ("length_mm",
                                  "diameter_or_length_mm"),
                    }.get(cls, (cls,))
            hits = [x for x in quantities
                    if x["quantity_class"] in qcls]
            if cls == "flow_ml_min":
                # the failure threshold resolves ONLY from a
                # requirement-declaring context (Art. XXVII: an
                # incidental number is never promoted to a threshold)
                hits = [x for x in hits
                        if ms._requirement_score(
                            problem_text, x["span"]) > 0]
            if hits:
                h = hits[0]
                bound = {
                    "value": float(h["value"]),
                    "unit": h["unit_canonical"],
                    "value_status": "SOURCE_FACT",
                    "source": (f"problem statement span {h['span']}: "
                               f"{h['raw_text']!r} "
                               f"({h.get('classification_basis' , '')}"
                               f")"),
                    "source_hash": _span_hash(problem_text,
                                              h["span"]),
                    "derivation": (
                        "value read verbatim from the operator's own "
                        "problem statement (the custodied SOURCE_FACT "
                        "authority; exact span + sha256 — Art. II/XII)"),
                }

        # --- 2. COMPUTED: the mechanistic solver chain ---------------
        if bound is None and cls and mech_vars:
            var = _CLASS_TO_VARIABLE.get(cls)
            v = mech_vars.get(var) if var else None
            if v and isinstance(v.get("value"), (int, float)):
                bound = {
                    "value": float(v["value"]),
                    "unit": v.get("unit") or "mm",
                    "value_status": "COMPUTED",
                    "source": (f"mechanistic solver chain "
                               f"({mechanistic_record.get('solver_version')}) "
                               f"canonical variable {var!r} — "
                               f"{v.get('source', '')[:160]}"),
                    "source_hash": (
                        mechanistic_record.get("candidate_prediction")
                        or {}).get("input_hash"),
                    "derivation": (
                        "computed by the deterministic 1D hydraulic "
                        "network solver chain (COMPUTATIONAL_RESULT — "
                        "a computation, never an observation; Art. "
                        "XXXVIII layer 4 / Art. LIII)"),
                }

        # --- 3. MODELLED: the candidate's declared parameter ----------
        if bound is None and cls:
            var = _CLASS_TO_VARIABLE.get(cls)
            cp = cand.get(var) if var else None
            if isinstance(cp, dict) and isinstance(
                    cp.get("value"), (int, float)):
                bound = {
                    "value": float(cp["value"]),
                    "unit": cp.get("unit") or "mm",
                    "value_status": "MODELLED",
                    "source": ("the candidate's declared parameter ("
                               + str(cp.get("source")
                                     or "design declaration") + ")"),
                    "source_hash": None,
                    "derivation": (
                        "declared by the invention's own architecture "
                        "(MODELLED content — a design choice, never "
                        "evidence; Art. XXXVIII layer 3)"),
                }

        if bound is not None:
            q.update(bound)
            q["sourcing_version"] = VALUE_SOURCING_VERSION
            q["value"] = bound["value"]
            q["basis"] = f"{bound['value_status']} (value_sourcing)"
            q["status"] = (f"ENGINEERING_SOURCED / "
                           f"{bound['value_status']}")
            q["uncertainty"] = (
                "unit-exact span value; measurement uncertainty "
                "UNKNOWN (no physical measurement exists — Art. XXV)")
            sourcing_counts[bound["value_status"]] += 1
        else:
            # NO legitimate source: STAYS UNKNOWN (Art. XXVII — the
            # absence is now a measured fact, not a universal constant)
            q["sourcing_version"] = VALUE_SOURCING_VERSION
            q["value"] = "UNKNOWN (no sourced value)"
            q["value_status"] = "UNKNOWN"
            q["source"] = None
            q["source_hash"] = None
            q["derivation"] = (
                "VALUE_SOURCING found no legitimate source for this "
                "parameter (no problem-statement number, no mechanistic "
                "computation, no candidate declaration) — the value "
                "STAYS UNKNOWN (Art. XXVII: never invented)")
            sourcing_counts["UNKNOWN"] += 1
        out.append(q)
    return out


def sourcing_summary(parameters: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Machine-readable sourcing summary for the record."""
    counts = {"SOURCE_FACT": 0, "COMPUTED": 0, "MODELLED": 0,
              "UNKNOWN": 0}
    for p in parameters:
        vs = str(p.get("value_status") or "UNKNOWN").upper()
        if vs in counts:
            counts[vs] += 1
    return {
        "value_sourcing_version": VALUE_SOURCING_VERSION,
        "counts": counts,
        "n_total": len(parameters),
        "n_sourced": counts["SOURCE_FACT"] + counts["COMPUTED"] +
                     counts["MODELLED"],
        "geometry_reachable": (
            counts["SOURCE_FACT"] + counts["COMPUTED"] +
            counts["MODELLED"]) >= 3,
        "rule": ("SOURCE_FACT > COMPUTED > MODELLED; no source stays "
                 "UNKNOWN — the Article XXVII <-> Article LX collision "
                 "resolved explicitly: sourcing from evidence with a "
                 "provenance hash is not threshold invention"),
    }

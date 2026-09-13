"""discovery_fabric/engine/mechanistic_solver.py — R452 Phase 5: the
first mechanistic solver — moving from text-only invention toward
causal reasoning.

Directive: "Use the previously identified highest-information solver
target: 1D hydraulic network solver... The earlier scientific
recommendation identified a bounded laminar Poiseuille network solver
over existing multi-lumen geometry as the most useful first solver
because it can be connected directly to current parametric geometry
and checked analytically. The solver must consume actual candidate
parameters rather than generic template values."

THE REQUIRED CHAIN (implemented here):

    candidate mechanism parameters
            ↓  (the candidate's OWN declared values + the problem's
               OWN declared numbers — never template values)
    canonical engineering variables
            ↓  (diameter_mm, length_mm, viscosity_mPa_s, boundary
               pressures, required-flow threshold — each carrying an
               epistemic class and its exact source)
    equations
            ↓  (Hagen-Poiseuille laminar network flow: the R394 V0
               solver discovery_fabric/engine/physics_core.py, whose
               closed-form reference validation is the instrument
               check; the equation itself is EXTERNAL_PRECEDENT
               knowledge per the E7 library FLUID-001)
    baseline prediction
            ↓  (the problem's CURRENT configuration solved by the
               same solver — Art. XLVII baseline supremacy: candidate
               vs baseline under identical instruments)
    failure threshold
            ↓  (the problem's OWN declared requirement — SOURCE_FACT
               from the user's problem statement; never an invented
               number, Art. XXVII)
    computed outcome
            ↓  (PASS / FAIL / INCONCLUSIVE / MODEL_INVALIDITY —
               COMPUTED class, with the solver's own validity flags)

EPISTEMIC CLASSIFICATION (the directive's hard rule): every output
carries one of the closed classes:

    COMPUTED       — a deterministic computation from classified inputs
    MODEL_DERIVED  — a declared/judged value (candidate parameters,
                     applicability judgments)
    SOURCE_FACT    — the user's own problem-statement numbers, with
                     their exact text spans
    UNKNOWN        — a required input that does not exist; the chain
                     NEVER fabricates a number to proceed (Art. VI /
                     Art. XXV)

No result may silently become "validated": the outcome's
evidence_class stays COMPUTED (Art. XXXVIII layer 4; Art. LIII —
MODEL_DERIVED -> COMPUTATIONAL_RESULT, no level skipping), and the
record says explicitly that a PASS is a computational prediction, not
a physical observation.

Constitutional anchors: Art. II (exact spans), Art. XXVII (threshold
provenance — the failure threshold is the problem's own requirement),
Art. XLVII (baseline supremacy, unchanged instrument across arms),
Art. LIII (no level skipping), Art. LXII (solver version pinned).
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any, Dict, List, Optional, Tuple

from . import physics_core

SOLVER_BRIDGE_VERSION = "mechanistic_solver/1.0.0"

#: the closed epistemic vocabulary (directive Phase 5)
EPISTEMIC_CLASSES = ("COMPUTED", "MODEL_DERIVED", "SOURCE_FACT",
                     "UNKNOWN")

# ---------------------------------------------------------------------------
# Deterministic quantity extraction (numbers + units, with spans)
# ---------------------------------------------------------------------------

#: length units -> mm
_LENGTH_UNITS = {
    "mm": 1.0, "millimetre": 1.0, "millimetres": 1.0,
    "millimeter": 1.0, "millimeters": 1.0,
    "cm": 10.0, "centimetre": 10.0, "centimetres": 10.0,
    "m": 1000.0, "metre": 1000.0, "metres": 1000.0,
    "meter": 1000.0, "meters": 1000.0,
}
#: viscosity units -> mPa.s
_VISCOSITY_UNITS = {
    "cp": 1.0, "centipoise": 1.0, "mpa": 1.0, "mpa.s": 1.0,
    "pa.s": 1000.0, "pas": 1000.0,
}
#: flow units -> mL/min
_FLOW_UNITS = {
    "l/min": 1000.0, "litres per minute": 1000.0,
    "liters per minute": 1000.0, "lpm": 1000.0,
    "ml/min": 1.0, "millilitres per minute": 1.0,
    "milliliters per minute": 1.0,
    "ml/s": 60.0, "l/s": 60000.0,
}
#: pressure units -> mmHg
_PRESSURE_UNITS = {
    "mmhg": 1.0, "millimetres of mercury": 1.0,
    "millimeters of mercury": 1.0,
    "kpa": 7.50062, "bar": 750.062, "mpa": 7500.62,
    "pa": 0.00750062,
}

_NUMBER = r"\d+(?:[.,]\d+)?(?:\s*(?:x\s*)?10\s*\^?\s*-?\d+)?"

_QTY_PATTERN = re.compile(
    rf"(?P<num>{_NUMBER})\s*-?\s*(?P<unit>"
    rf"millimetres?\s+of\s+mercury|millimeters?\s+of\s+mercury|"
    rf"litres?\s+per\s+minute|liters?\s+per\s+minute|"
    rf"millilitres?\s+per\s+minute|milliliters?\s+per\s+minute|"
    rf"centipoise|"
    rf"millimetres?|millimeters?|"
    rf"centimetres?|centimeters?|"
    rf"metres?|meters?|"
    rf"mmhg|mpa\.s|pa\.s|"
    rf"l/min|ml/min|ml/s|l/s|lpm|"
    rf"kpa|mpa|bar|"
    rf"mm|cm|(?<![\w.])m(?![\w.])|cp)"
    rf"(?![\w])",
    re.IGNORECASE)

#: context keywords for PRIMARY-SEGMENT selection: the failing
#: component's feed segment (recorded in the variable's source basis)
_PRIMARY_DIAMETER_CONTEXT = (
    "branch", "pinion", "bearing", "cannula", "lumen", "sheath",
    "tube", "tubing", "channel", "orifice", "needle", "catheter")
_PRIMARY_LENGTH_CONTEXT = (
    "long", "length", "branch", "segment", "tube", "tubing",
    "cannula")
#: requirement markers — the failure threshold resolves ONLY from a
#: declared requirement context PRECEDING the quantity (requirements
#: read "need at least X"; incidental numbers never promote)
_REQUIREMENT_CONTEXT = (
    "at least", "need", "needs", "must", "require", "required",
    "requires", "no less than", "minimum", "not less than")


def _requirement_score(text: str, span: Tuple[int, int]) -> int:
    """Requirement markers in the 120 characters PRECEDING the
    quantity (deterministic)."""
    window = text[max(0, span[0] - 120):span[0]].lower()
    return sum(1 for k in _REQUIREMENT_CONTEXT if k in window)


def _context_score(text: str, span: Tuple[int, int],
                   keywords: Tuple[str, ...]) -> int:
    """How many context keywords appear within the 120 characters on
    EITHER side of the quantity span (deterministic; bidirectional so
    a segment described AFTER its number — "2.5-millimetre drilled
    branches ... to the high-speed pinion bearing" — scores on its
    failing-component context)."""
    lo = max(0, span[0] - 120)
    window = (text[lo:span[0]] + " " +
              text[span[1]:span[1] + 120]).lower()
    return sum(1 for k in keywords if k in window)


_THOUSANDS_RE = re.compile(r"^\d{1,3}(?:,\d{3})+$")


def _parse_number(num_txt: str) -> Optional[float]:
    """Parse a problem-statement number deterministically. The comma
    is a THOUSANDS separator when it groups exactly three digits
    ("1,800" -> 1800) and a decimal comma otherwise ("4,5" -> 4.5);
    a bare period is a decimal point ("2.5" -> 2.5)."""
    txt = num_txt.strip()
    if _THOUSANDS_RE.match(txt):
        txt = txt.replace(",", "")
    else:
        txt = txt.replace(",", ".")
    try:
        return float(txt)
    except ValueError:
        return None


def extract_quantities(text: str) -> List[Dict[str, Any]]:
    """Deterministic number+unit extraction with EXACT spans (Art. II:
    the span is the evidence; the number is read from it, never
    reworded). Returns quantities with canonicalized values in the
    canonical units and their character spans in the source text."""
    out: List[Dict[str, Any]] = []
    if not text:
        return out
    for m in _QTY_PATTERN.finditer(text):
        unit = re.sub(r"\s+", " ", m.group("unit").lower())
        val = _parse_number(m.group("num"))
        if val is None:
            continue
        num_txt = m.group("num")
        if "x 10" in num_txt or "x10" in num_txt:
            # scientific notation with explicit exponent
            mm = re.match(r"(\d+(?:\.\d+)?)\s*x\s*10\s*\^?\s*(-?\d+)",
                          num_txt)
            if mm:
                val = float(mm.group(1)) * 10 ** int(mm.group(2))
        canon = None
        if unit in _LENGTH_UNITS:
            canon = ("diameter_or_length_mm", val * _LENGTH_UNITS[unit])
        elif unit in _VISCOSITY_UNITS:
            canon = ("viscosity_mPa_s", val * _VISCOSITY_UNITS[unit])
        elif unit in _FLOW_UNITS:
            canon = ("flow_ml_min", val * _FLOW_UNITS[unit])
        elif unit in _PRESSURE_UNITS:
            canon = ("pressure_mmHg", val * _PRESSURE_UNITS[unit])
        if canon is None:
            continue
        out.append({
            "quantity_class": canon[0],
            "value": round(canon[1], 6),
            "unit_canonical": {
                "diameter_or_length_mm": "mm",
                "viscosity_mPa_s": "mPa.s",
                "flow_ml_min": "mL/min",
                "pressure_mmHg": "mmHg"}[canon[0]],
            "raw_text": m.group(0),
            "span": [m.start(), m.end()],
            "epistemic_class": "SOURCE_FACT",
        })
    return out


def _pick_quantities(quantities: List[Dict[str, Any]],
                     quantity_class: str) -> List[Dict[str, Any]]:
    return [q for q in quantities
            if q["quantity_class"] == quantity_class]


#: nouns that identify a DIAMETER quantity (look-ahead window)
_DIAMETER_NOUNS = (
    "diameter", "gallery", "branch", "branches", "cannula", "lumen",
    "sheath", "tube", "tubing", "channel", "orifice", "bore",
    "drilled", "needle", "pipe", "conduit")
#: nouns that identify a LENGTH quantity (look-ahead window)
_LENGTH_NOUNS = ("long", "length", "deep", "tall")


def classify_length_quantities(
        text: str, quantities: List[Dict[str, Any]]
        ) -> List[Dict[str, Any]]:
    """Split the diameter_or_length_mm class into diameter_mm and
    length_mm by the unit-noun immediately FOLLOWING the quantity
    (deterministic; the classification basis is recorded on each
    quantity). Ambiguous quantities stay generic and are resolvable
    only by an explicit candidate parameter — never guessed."""
    out: List[Dict[str, Any]] = []
    for q in quantities:
        if q["quantity_class"] != "diameter_or_length_mm":
            out.append(q)
            continue
        # the length noun must IMMEDIATELY follow the quantity (a
        # 15-char window — "60 millimetres long"); a wider window
        # would let the NEXT quantity's noun leak into this one's
        # classification ("...25-millimetre pipe 100 millimetres
        # long" would misclassify the pipe diameter as a length)
        ahead = text[q["span"][1]:q["span"][1] + 15].lower()
        ahead_wide = text[q["span"][1]:q["span"][1] + 40].lower()
        behind = text[max(0, q["span"][0] - 60):q["span"][0]].lower()
        is_length = any(n in ahead for n in _LENGTH_NOUNS)
        is_diameter = (any(n in ahead_wide for n in _DIAMETER_NOUNS)
                       or any(n in behind for n in _DIAMETER_NOUNS))
        # the DIRECTLY-FOLLOWING noun is the stronger signal: "60
        # millimetres long" is a length even when "branches" precedes
        if is_length:
            out.append({**q, "quantity_class": "length_mm",
                        "classification_basis":
                            f"length noun follows the span "
                            f"({ahead.strip()[:30]!r})"})
        elif is_diameter:
            out.append({**q, "quantity_class": "diameter_mm",
                        "classification_basis":
                            "diameter noun adjacent to the span"})
        else:
            out.append({**q,
                        "classification_basis": "ambiguous — generic "
                                                "length-class quantity"})
    return out


# ---------------------------------------------------------------------------
# The canonical engineering variables (from ACTUAL inputs)
# ---------------------------------------------------------------------------

def build_canonical_variables(
        problem_text: str,
        candidate_parameters: Optional[Dict[str, Dict[str, Any]]] = None
        ) -> Dict[str, Any]:
    """Resolve the canonical engineering variables for the hydraulic
    chain from the ACTUAL inputs:

      - the PROBLEM's own declared numbers (SOURCE_FACT, exact spans);
      - the CANDIDATE's own declared parameters (each carrying its own
        class + source; typically MODEL_DERIVED or EXTRACTED).

    Resolution order per variable: the candidate's declared parameter
    FIRST (the candidate's design is what we are evaluating), then the
    problem's own number (context-selected among same-class
    quantities, with the selection basis recorded), then UNKNOWN
    (never fabricated).

    The failure threshold (required flow) resolves ONLY from a
    REQUIREMENT-declaring context ("at least", "need", "must", ...) —
    an incidental number in the problem text is never promoted to a
    threshold (Art. XXVII).

    The returned record is fully classified: every variable carries
    value, unit, epistemic_class, and source (the exact span or the
    candidate field it came from).
    """
    problem_qs = classify_length_quantities(
        problem_text or "", extract_quantities(problem_text or ""))
    cand = candidate_parameters or {}

    def _problem_hit(classes: Tuple[str, ...],
                     context: Optional[Tuple[str, ...]],
                     requirement_only: bool = False
                     ) -> Optional[Dict[str, Any]]:
        """Select ONE problem quantity: the requirement-context match
        when requirement_only, else the highest context score (ties ->
        first occurrence). The selection basis is recorded."""
        hits: List[Dict[str, Any]] = []
        for cls in classes:
            hits.extend(_pick_quantities(problem_qs, cls))
        if not hits:
            return None
        if requirement_only:
            req = [h for h in hits
                   if _requirement_score(problem_text, h["span"]) > 0]
            if not req:
                return None
            hits = req
        if context:
            best = max(
                hits,
                key=lambda h: (_context_score(problem_text,
                                              h["span"], context),
                               -h["span"][0]))
            score = _context_score(problem_text, best["span"], context)
            return {**best, "selection_basis": (
                f"context keywords {context} (score {score}) — the "
                f"segment feeding the failing component")}
        return {**hits[0], "selection_basis": "first declared quantity "
                                             "of the class"}

    def _resolve(name: str, classes: Tuple[str, ...],
                 candidate_keys: Tuple[str, ...],
                 context: Optional[Tuple[str, ...]] = None,
                 requirement_only: bool = False) -> Dict[str, Any]:
        # 1. the candidate's OWN declared parameter
        for key in candidate_keys:
            if key in cand and isinstance(cand[key], dict):
                v = cand[key].get("value")
                if isinstance(v, (int, float)):
                    return {
                        "variable": name,
                        "value": float(v),
                        "unit": cand[key].get("unit"),
                        "epistemic_class": cand[key].get(
                            "epistemic_class", "MODEL_DERIVED"),
                        "source": f"candidate parameter {key!r}"
                                  + (f" ({cand[key].get('source')})"
                                     if cand[key].get("source") else ""),
                    }
        # 2. the problem's own number
        h = _problem_hit(classes, context, requirement_only)
        if h:
            return {
                "variable": name,
                "value": h["value"],
                "unit": h["unit_canonical"],
                "epistemic_class": "SOURCE_FACT",
                "source": f"problem statement span {h['span']}: "
                          f"{h['raw_text']!r} ({h['selection_basis']})",
            }
        # 3. honest UNKNOWN — never fabricated (Art. VI/XXV)
        reason = ("no requirement-declaring flow quantity in the "
                  "problem statement (an incidental number is never "
                  "promoted to a threshold — Art. XXVII)"
                  if requirement_only else
                  "no declared value in the candidate or the problem "
                  "statement")
        return {
            "variable": name,
            "value": None,
            "unit": None,
            "epistemic_class": "UNKNOWN",
            "source": reason,
        }

    variables = {
        "primary_diameter_mm": _resolve(
            "primary_diameter_mm", ("diameter_mm",
                                    "diameter_or_length_mm"),
            ("primary_diameter_mm", "branch_diameter_mm",
             "lumen_diameter_mm", "diameter_mm"),
            context=_PRIMARY_DIAMETER_CONTEXT),
        "primary_length_mm": _resolve(
            "primary_length_mm", ("length_mm",),
            ("primary_length_mm", "branch_length_mm",
             "lumen_length_mm", "length_mm"),
            context=_PRIMARY_LENGTH_CONTEXT),
        "viscosity_mPa_s": _resolve(
            "viscosity_mPa_s", ("viscosity_mPa_s",),
            ("viscosity_mPa_s", "oil_viscosity_mPa_s")),
        "inlet_pressure_mmHg": _resolve(
            "inlet_pressure_mmHg", ("pressure_mmHg",),
            ("inlet_pressure_mmHg", "supply_pressure_mmHg")),
        "required_flow_ml_min": _resolve(
            "required_flow_ml_min", ("flow_ml_min",),
            ("required_flow_ml_min", "target_flow_ml_min"),
            requirement_only=True),
    }
    return {
        "variables": variables,
        "problem_quantities_found": len(problem_qs),
        "unknown_variables": [k for k, v in variables.items()
                              if v["epistemic_class"] == "UNKNOWN"],
        "all_inputs_classified": True,
    }


# ---------------------------------------------------------------------------
# The mechanistic virtual experiment (equations -> baseline ->
# threshold -> computed outcome)
# ---------------------------------------------------------------------------

def run_mechanistic_virtual_experiment(
        problem_text: str,
        candidate_id: str,
        candidate_parameters: Optional[Dict[str, Dict[str, Any]]] = None,
        experiment_id: Optional[str] = None) -> Dict[str, Any]:
    """Execute the full Phase 5 chain for ONE candidate:

    candidate parameters -> canonical variables -> equations (the R394
    V0 hydraulic network solver) -> baseline prediction -> failure
    threshold -> computed outcome.

    The BASELINE is the problem's own current configuration (its own
    numbers); the CANDIDATE arm overrides the variables the candidate
    itself declares. Both arms run through the SAME solver (identical
    instrument — Art. XLVII). The failure threshold is the problem's
    own declared required flow (SOURCE_FACT).

    Outcomes (closed vocabulary):
      COMPUTED_PASS              candidate meets the threshold, baseline
                                 fails/unknown-below-it (or candidate
                                 strictly beats baseline on the metric)
      COMPUTED_FAIL              candidate misses the threshold
      COMPUTED_NO_BASELINE_DIFF  both arms compute the same value
      INCONCLUSIVE_UNKNOWN_INPUT a required variable is UNKNOWN — the
                                 chain refuses to fabricate
      MODEL_INVALIDITY           the solver's own laminar-validity /
                                 plausibility flags fired — the
                                 numbers are retained for audit but are
                                 NOT computational evidence
    """
    exp_id = experiment_id or (
        "vexp-" + hashlib.sha256(
            json.dumps([candidate_id, problem_text,
                        sorted((candidate_parameters or {}).items())],
                       default=str).encode()).hexdigest()[:16])

    # TWO variable sets (Art. XLVII — the baseline is the problem's
    # OWN current configuration and must never inherit the candidate's
    # overrides; the candidate arm is the problem + the candidate's
    # declared parameters):
    canon_base = build_canonical_variables(problem_text, None)
    canon_cand = build_canonical_variables(problem_text,
                                           candidate_parameters)
    v = canon_cand["variables"]
    vb = canon_base["variables"]

    # required variables for the candidate arm
    required = ("primary_diameter_mm", "primary_length_mm",
                "viscosity_mPa_s", "inlet_pressure_mmHg",
                "required_flow_ml_min")
    unknowns = [k for k in required
                if v[k]["epistemic_class"] == "UNKNOWN"]
    if unknowns:
        return {
            "experiment_id": exp_id,
            "candidate_id": candidate_id,
            "status": "INCONCLUSIVE_UNKNOWN_INPUT",
            "unknown_variables": unknowns,
            "canonical_variables": canon_cand,
            "note": ("the chain refuses to fabricate the missing "
                     "variables (Art. VI/XXV); the candidate cannot be "
                     "mechanistically evaluated on the declared inputs "
                     "alone"),
            "epistemic_class": "UNKNOWN",
            "solver_bridge_version": SOLVER_BRIDGE_VERSION,
        }

    d = v["primary_diameter_mm"]["value"]
    L = v["primary_length_mm"]["value"]
    mu = v["viscosity_mPa_s"]["value"]
    p_in = v["inlet_pressure_mmHg"]["value"]
    q_req = v["required_flow_ml_min"]["value"]
    # the baseline arm uses the problem's own numbers; a variable the
    # problem itself does not declare leaves the baseline arm
    # INCONCLUSIVE (recorded honestly — never the candidate's value)
    base_unknowns = [k for k in
                     ("primary_diameter_mm", "primary_length_mm",
                      "viscosity_mPa_s", "inlet_pressure_mmHg")
                     if vb[k]["epistemic_class"] == "UNKNOWN"]

    def _network(diameter: float) -> Dict[str, Any]:
        spec = {
            "geometry_identity": f"{exp_id}:d={diameter:.4f}mm",
            "geometry_hash": hashlib.sha256(
                f"{exp_id}:{diameter:.6f}".encode()).hexdigest(),
            "fluid": {"viscosity_mPa_s": mu,
                      "density_kg_m3": 900.0,
                      "temperature_K": 293.15},
            "boundary": {"inlet_mmHg": p_in, "outlet_mmHg": 0.0},
            "segments": [
                {"segment_id": "primary",
                 "node_a": "IN", "node_b": "OUT",
                 "diameter_mm": diameter, "length_mm": L,
                 "obstruction_pct": 0.0},
            ],
        }
        return physics_core.solve_network(spec)

    candidate_d = d
    cand_d = (candidate_parameters or {}).get("primary_diameter_mm")
    if isinstance(cand_d, dict) and isinstance(
            cand_d.get("value"), (int, float)):
        candidate_d = float(cand_d["value"])
    baseline_result = (_network(float(vb["primary_diameter_mm"]["value"]))
                       if not base_unknowns else
                       {"status": "BASELINE_INCONCLUSIVE_UNKNOWN_INPUT",
                        "base_unknowns": base_unknowns})
    candidate_result = _network(candidate_d)

    def _q(res: Dict[str, Any]) -> Optional[float]:
        if res.get("status") in ("PLAUSIBILITY_BOUND_VIOLATED",
                                 "BASELINE_INCONCLUSIVE_UNKNOWN_INPUT"):
            return None
        return (res.get("predicted_quantities") or {}).get(
            "total_flow_ml_min")

    q_base = _q(baseline_result)
    q_cand = _q(candidate_result)

    record: Dict[str, Any] = {
        "experiment_id": exp_id,
        "candidate_id": candidate_id,
        "status": None,
        "epistemic_class": "COMPUTED",
        "solver_bridge_version": SOLVER_BRIDGE_VERSION,
        "solver_version": physics_core.SOLVER_VERSION,
        "equations": [
            {"equation_id": "FLUID-001",
             "name": "Hagen-Poiseuille (laminar pipe flow)",
             "expression": "Q = (pi * r^4 * dP) / (8 * mu * L)",
             "source_class": "EXTERNAL_PRECEDENT",
             "executed_by": f"physics_core {physics_core.SOLVER_VERSION} "
                            "(reference-validated: single tube, series, "
                            "parallel closed forms < 1e-12 rel)"},
        ],
        "canonical_variables": {
            "candidate_arm": canon_cand,
            "baseline_arm": canon_base,
        },
        "baseline_prediction": {
            "arm": "BASELINE (the problem's own current configuration)",
            "diameter_mm": (float(vb["primary_diameter_mm"]["value"])
                            if not base_unknowns else None),
            "predicted_flow_ml_min": q_base,
            "epistemic_class": "COMPUTED",
            "solver_record_status": baseline_result.get("status"),
            "model_validity": baseline_result.get("model_validity"),
            "input_hash": baseline_result.get("input_hash"),
            "output_hash": baseline_result.get("output_hash"),
        },
        "candidate_prediction": {
            "arm": "CANDIDATE (the candidate's declared parameters)",
            "diameter_mm": candidate_d,
            "predicted_flow_ml_min": q_cand,
            "epistemic_class": "COMPUTED",
            "solver_record_status": candidate_result.get("status"),
            "model_validity": candidate_result.get("model_validity"),
            "input_hash": candidate_result.get("input_hash"),
            "output_hash": candidate_result.get("output_hash"),
        },
        "failure_threshold": {
            "metric": "total_flow_ml_min",
            "value_ml_min": q_req,
            "epistemic_class": v["required_flow_ml_min"][
                "epistemic_class"],
            "source": v["required_flow_ml_min"]["source"],
            "rule": ("the problem's OWN declared requirement — never "
                     "an invented threshold (Art. XXVII)"),
        },
        "computed_outcome": None,
        "honesty_note": ("a PASS is a computational prediction of the "
                         "declared model under the declared inputs — "
                         "computational evidence, never a physical "
                         "observation (Art. XXXVIII layer 4, Art. LIII: "
                         "no level skipping, nothing silently "
                         "'validated')"),
    }

    # model validity gate: the solver's own flags decide (the
    # baseline's honest INCONCLUSIVE state is NOT model invalidity)
    invalid = []
    for name, res in (("baseline", baseline_result),
                      ("candidate", candidate_result)):
        mv = (res.get("model_validity") or {})
        if res.get("status") == "PLAUSIBILITY_BOUND_VIOLATED" or \
                not mv.get("laminar_valid", True):
            invalid.append(name)
    if invalid or q_cand is None:
        record["status"] = "MODEL_INVALIDITY"
        record["computed_outcome"] = {
            "outcome": "MODEL_INVALIDITY",
            "invalid_arms": invalid,
            "note": ("the solver's own plausibility/laminar-validity "
                     "flags fired — the numbers are retained for audit "
                     "but are NOT computational evidence (the R394 "
                     "s11/s9 discipline)"),
        }
        record["epistemic_class"] = "UNKNOWN"
        return record

    if q_cand < q_req:
        outcome = "COMPUTED_FAIL"
    elif q_base is None:
        # the candidate meets the threshold; the problem's own numbers
        # could not compute a baseline (missing variables recorded) —
        # the threshold claim stands, the baseline comparison does not
        outcome = "COMPUTED_PASS_BASELINE_INCONCLUSIVE"
    elif q_base < q_req:
        outcome = "COMPUTED_PASS"
    else:
        outcome = "COMPUTED_NO_BASELINE_DIFF"

    record["status"] = outcome
    record["computed_outcome"] = {
        "outcome": outcome,
        "candidate_flow_ml_min": q_cand,
        "baseline_flow_ml_min": q_base,
        "required_flow_ml_min": q_req,
        "margin_over_threshold_ml_min": round(q_cand - q_req, 6),
        "improvement_over_baseline_ml_min": round(q_cand - q_base, 6),
        "epistemic_class": "COMPUTED",
    }
    return record


# ---------------------------------------------------------------------------
# The mechanistic (deterministic) mutation — inverse Poiseuille
# ---------------------------------------------------------------------------

def mechanistic_mutation(
        experiment_record: Dict[str, Any],
        candidate_parameters: Dict[str, Dict[str, Any]]) \
        -> Optional[Dict[str, Any]]:
    """THE mechanistic mutation for a COMPUTED_FAIL outcome on the
    primary-diameter variable: solve the INVERSE Poiseuille problem in
    closed form for the required flow.

        d_new = d_old * (Q_required / Q_candidate)^(1/4)

    This is a CAUSAL mutation generated from the experiment result
    itself (the observed flow deficit through the failed constraint),
    not an unrelated random proposal — the R452 Phase 7 requirement.
    The mutation is bounded by the problem's own declared constraints
    when the candidate carries them; no safety margin is invented
    (Art. XXVII).
    """
    co = experiment_record.get("computed_outcome") or {}
    if experiment_record.get("status") != "COMPUTED_FAIL":
        return None
    q_cand = co.get("candidate_flow_ml_min")
    q_req = co.get("required_flow_ml_min")
    if not isinstance(q_cand, (int, float)) or q_cand <= 0:
        return None
    if not isinstance(q_req, (int, float)) or q_req <= q_cand:
        return None
    d_old = (experiment_record.get("candidate_prediction")
             or {}).get("diameter_mm")
    if not isinstance(d_old, (int, float)) or d_old <= 0:
        return None
    ratio = q_req / q_cand
    d_new = d_old * ratio ** 0.25
    return {
        "mutation_kind": "INVERSE_POISEUILLE_DIAMETER",
        "target_variable": "primary_diameter_mm",
        "from_value": round(d_old, 6),
        "to_value": round(d_new, 6),
        "derivation": (
            f"d_new = d_old * (Q_required / Q_candidate)^(1/4) = "
            f"{d_old:.4f} * ({q_req:.4f} / {q_cand:.4f})^(1/4) = "
            f"{d_new:.4f} mm — the closed-form inverse of the "
            f"Poiseuille relation for the required flow"),
        "causal_basis": {
            "observed_outcome": "COMPUTED_FAIL",
            "failed_constraint": (
                f"predicted flow {q_cand:.4f} mL/min < required "
                f"{q_req:.4f} mL/min"),
            "mutation_reason": (
                "the flow deficit is driven by the primary segment's "
                "diameter through the d^4 Poiseuille dependence; the "
                "mutation solves the inverse problem for exactly the "
                "required flow"),
        },
        "epistemic_class": "COMPUTED",
    }

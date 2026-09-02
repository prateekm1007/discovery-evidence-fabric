"""reality_calibration.py — R394 section 13/14: the model-calibration
moat.

Directive section 13: "The true reality loop is: PROTOTYPE ->
MEASUREMENT -> REALITY_EVENT -> DISCREPANCY -> MODEL UPDATE -> DESIGN
UPDATE -> RETEST." Section 14: "Do not stop at 'measurement differs
from model.' Implement: PREDICTION -> MEASUREMENT -> ERROR ->
PARAMETER UPDATE -> PREDICTION -> NEW MEASUREMENT. The system must
quantify whether prediction error improves."

This module implements the QUANTIFIED calibration loop on the physics
core — the same code path the R390 REAL closure validated on P-07
(NIST water viscosity 0.6913 mPa.s vs the 1.0 design basis):

  calibrate_model():
    1. PREDICTION      solve with the model's current parameter(s)
    2. MEASUREMENT     an externally supplied measured datum (the
                       reality event; provenance/attestation live with
                       the caller's REALITY_EVENT record — this module
                       consumes the VALUE, never fabricates one)
    3. ERROR           |prediction - measurement| / measurement
    4. PARAMETER UPDATE  deterministic identification of the model
                       parameter that explains the error (for hydraulic
                       flow under fixed geometry, viscosity is the only
                       free parameter: Q ~ 1/mu analytically — the
                       update is mu' = mu * Q_pred / Q_meas, the exact
                       Poiseuille inversion; geometry parameters are
                       NOT free because the geometry hash is frozen)
    5. PREDICTION      re-solve with the updated parameter
    6. NEW MEASUREMENT a second externally supplied datum (held-out)
    7. IMPROVEMENT     error(before) vs error(after) on the held-out
                       datum — quantified, signed, never asserted

If the error does not improve, the record says so (an honest failed
calibration is a result, not a bug).

Constitutional placement: the measurements enter as CALLER-SUPPLIED
data with their own provenance (Art. XXXVIII — MEASURED has exactly one
door, the R370G attested event); this module performs the model-side
update and the error quantification. It never labels anything
PHYSICAL_OBSERVATION by itself.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from discovery_fabric.engine import physics_core as pc

CALIBRATION_VERSION = "reality_calibration/1.0.0"


def calibrate_model(spec: Dict[str, Any],
                    measurement_1: Dict[str, Any],
                    measurement_2: Dict[str, Any],
                    target_metric: str = "total_flow_ml_min",
                    scenario: Optional[str] = None) -> Dict[str, Any]:
    """The six-step quantified calibration loop.

    spec: the solver input (geometry hash FROZEN — calibration updates
          the model parameter, never the geometry; a geometry change is
          a design update, not a calibration).
    measurement_1: {value, provenance_class, event_ref} — the datum that
          drives the parameter update.
    measurement_2: {value, provenance_class, event_ref} — the HELD-OUT
          datum that quantifies improvement.
    """
    frozen_geometry_hash = spec.get("geometry_hash")

    def _predict(viscosity: float) -> Optional[float]:
        s = json.loads(json.dumps(spec, sort_keys=True))
        s["fluid"] = dict(s["fluid"])
        s["fluid"]["viscosity_mPa_s"] = viscosity
        if scenario is None:
            r = pc.solve_network(s)
            if r.get("status") not in ("COMPUTATIONAL_RESULT",
                                       "COMPUTATIONAL_RESULT_MODEL_INVALIDITY"):
                return None
            return r["predicted_quantities"][target_metric]
        sim = pc.simulate_failure_modes(s, _primary_segment(spec),
                                        target_metric)
        if sim.get("status") != "SIMULATED":
            return None
        for x in sim["scenarios"]:
            if x["scenario"] == scenario:
                return x.get("value")
        return None

    def _primary_segment(s: Dict[str, Any]) -> str:
        return s["segments"][0]["segment_id"]

    mu_0 = float(spec["fluid"]["viscosity_mPa_s"])
    q_pred_0 = _predict(mu_0)
    m1 = float(measurement_1["value"])
    m2 = float(measurement_2["value"])
    if q_pred_0 is None or m1 <= 0 or m2 <= 0:
        return {"status": "CALIBRATION_NOT_POSSIBLE",
                "reason": "prediction or measurements unavailable/invalid",
                "calibration_version": CALIBRATION_VERSION}

    # ---- ERROR (before) ------------------------------------------------
    err_1 = abs(q_pred_0 - m1) / m1
    err_2_before = abs(q_pred_0 - m2) / m2

    # ---- PARAMETER UPDATE (deterministic Poiseuille inversion) --------
    # Q ~ 1/mu under frozen geometry and pressures: the unique viscosity
    # that reproduces measurement_1 is mu' = mu_0 * Q_pred / m1.
    mu_1 = mu_0 * (q_pred_0 / m1)

    # ---- PREDICTION (after) --------------------------------------------
    q_pred_1 = _predict(mu_1)

    # ---- ERROR (after) on the HELD-OUT measurement ----------------------
    err_2_after = (abs(q_pred_1 - m2) / m2
                   if q_pred_1 is not None else None)

    improved = (err_2_after is not None and err_2_after < err_2_before)
    return {
        "status": "CALIBRATION_COMPLETE",
        "calibration_version": CALIBRATION_VERSION,
        "solver_version": pc.SOLVER_VERSION,
        "steps": {
            "PREDICTION_1": {"viscosity_mPa_s": mu_0,
                             "predicted": q_pred_0,
                             "model_version": pc.MODEL_VERSION},
            "MEASUREMENT_1": {"value": m1,
                              "provenance_class":
                                  measurement_1.get("provenance_class"),
                              "event_ref": measurement_1.get("event_ref")},
            "ERROR_1": {"relative": err_1,
                        "note": "error against the calibration datum"},
            "PARAMETER_UPDATE": {
                "parameter": "fluid.viscosity_mPa_s",
                "before": mu_0, "after": mu_1,
                "method": ("deterministic Poiseuille inversion "
                           "(Q ~ 1/mu, geometry hash frozen) — not a fit "
                           "search"),
                "geometry_hash_frozen": frozen_geometry_hash},
            "PREDICTION_2": {"viscosity_mPa_s": mu_1,
                             "predicted": q_pred_1},
            "MEASUREMENT_2": {"value": m2,
                              "provenance_class":
                                  measurement_2.get("provenance_class"),
                              "event_ref": measurement_2.get("event_ref")},
            "ERROR_2": {"before": err_2_before, "after": err_2_after,
                        "held_out": True},
        },
        "improvement": {
            "improved": improved,
            "error_before": err_2_before,
            "error_after": err_2_after,
            "improvement_ratio": (err_2_before / err_2_after
                                  if (err_2_after not in (None, 0.0)
                                      and improved) else None),
            "note": ("quantified on the HELD-OUT datum; a failed "
                     "improvement is recorded honestly — the model "
                     "update did not generalize (R394 s14)"),
        },
        "epistemic_note": ("the measured values enter with their own "
                           "provenance classes (Art. XXXVIII: MEASURED "
                           "has one door); this record is "
                           "MODEL-side calibration only"),
    }

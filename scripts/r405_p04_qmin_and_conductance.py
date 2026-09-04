#!/usr/bin/env python3
"""R405 — P04 Q_min / corrected-conductance computation + P11 instrument MDD.

Responds to the R405 external audit (P04 Week 2-3: "Declare Q_min"; P11
Week 2-4: "power calculation or minimum-detectable-difference") AND records
the CORRECTED absolute conductances after the R405 unit-conversion fix
(both `discovery_fabric.engine.reality_loop._conductance_ml_per_min_mmhg`
and `discovery_fabric.engine.physics_core.poiseuille_conductance` divided
by 133.322 where they must multiply — every recorded absolute conductance
was 133.322^2 = 17,774.7x too small; ratio-based results unaffected).

Everything computed here is a COMPUTATIONAL_RESULT: the script IS the
computation log; every input carries its value/unit/source/evidence class
(Constitution Art. XXVII threshold provenance; Art. II exact arithmetic).
Physiological anchors verified by live web search 2026-09-04 (queries
logged in the R405 response record):
  - CSF production 0.2-0.4 mL/min (Tariq 2023, PMC10409822;
    Silverberg 2002, J Neurosurg 97(6):1271: 0.4 +/- 0.13 mL/min acute,
    0.25 +/- 0.08 mL/min chronic; kenhub secondary: 0.2-0.7 mL/min).
    NOTE: the external audit's "0.3-0.4 mL/hr" is a UNIT ERROR (60x too
    low) — flagged in the response record, never adopted.
"""
import json
import math
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import reality_loop  # noqa: E402
from discovery_fabric.engine import physics_core  # noqa: E402

MMHG_TO_PA = 133.322
R_MM = 0.0


def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=1)


# ---------------------------------------------------------------------------
# Independent closed-form reference (NOT the engine function — Art. III:
# the verifier must not trust the claimant; derive from raw SI units)
# ---------------------------------------------------------------------------
def independent_conductance_mL_per_min_mmHg(d_mm, eta_mPa_s, L_mm):
    """Hand-derived in raw SI, converted once, dimensionally annotated.

    G = pi*d^4 / (128*eta*L)
      d [m], eta [Pa*s], L [m] -> G [m^3/(s*Pa)]
    Q(dP=1 mmHg) = G * 133.322 Pa = [m^3/s] -> *1e6 [mL/s] -> *60 [mL/min]
    """
    d_m = d_mm * 1e-3
    eta = eta_mPa_s * 1e-3
    L_m = L_mm * 1e-3
    g_si = math.pi * d_m ** 4 / (128.0 * eta * L_m)
    return g_si * MMHG_TO_PA * 1e6 * 60.0


def main():
    out = {}

    # -- 1. corrected conductances (engine function vs independent) ------
    cases = [
        # (label, d_mm, eta, L_mm, provenance)
        ("r390_loop_design_basis", 0.6, 1.0, 100.0,
         "R390 reality-loop 'before' case (design constant + design geometry)"),
        ("r390_loop_as_built", 0.6, 0.6913036, 100.0,
         "R390 reality-loop 'as_built' case (measured eta, unchanged geometry)"),
        ("r390_loop_corrected", 0.5471, 0.6913036, 100.0,
         "R390 reality-loop 'after' case (measured eta + NIST-compensated geometry)"),
    ]
    cond_rows = []
    for label, d, eta, L, prov in cases:
        g_engine = reality_loop._conductance_ml_per_min_mmhg(d, eta, L)
        g_indep = independent_conductance_mL_per_min_mmHg(d, eta, L)
        rel = abs(g_engine - g_indep) / g_indep
        cond_rows.append({
            "case": label, "d_mm": d, "eta_mPa_s": eta, "L_mm": L,
            "provenance": prov,
            "engine_value_mL_min_mmHg": round(g_engine, 8),
            "independent_value_mL_min_mmHg": round(g_indep, 8),
            "relative_difference": rel,
            "agreement": "EXACT to float precision" if rel < 1e-12 else "MISMATCH",
            "pre_r405_recorded_value": None,  # filled below
        })
    # the pre-R405 recorded (defective) values, for the correction record
    pre = {"r390_loop_design_basis": 1.4315098311274948e-05,
           "r390_loop_as_built": 2.070735e-05,
           "r390_loop_corrected": 1.431495e-05}
    for row in cond_rows:
        row["pre_r405_recorded_value"] = pre[row["case"]]
        row["correction_factor_true_over_recorded"] = round(
            row["independent_value_mL_min_mmHg"]
            / row["pre_r405_recorded_value"], 3)
    out["corrected_conductances"] = cond_rows

    # the defect constant, derived once, transparently
    out["defect_factor"] = {
        "value": MMHG_TO_PA ** 2,
        "derivation": "133.322^2 = 17,774.7 — the pre-R405 code divided by "
                      "133.322 where per-mmHg requires multiplying, so "
                      "recorded absolute conductances were this factor too "
                      "small",
    }

    # -- 2. P04 Q_min declaration + floor-flow computation ----------------
    q_min = {
        "quantity": "minimum clinically meaningful floor drainage (Q_min)",
        "physiological_basis": "CSF production rate",
        "value_range": [0.2, 0.4],
        "unit": "mL/min",
        "equivalent_mL_hr": [12.0, 24.0],
        "threshold_class": "PHYSIOLOGICAL",
        "evidence_class": "EXTERNAL_PRECEDENT (web-search-verified existence, "
                          "snippet-quoted; full-text verification open)",
        "sources": [
            {"citation": "Tariq et al. 2023, 'Cerebrospinal fluid production "
                         "rate in various pathological conditions', "
                         "PMC10409822",
             "verified_snippet": "CSF production rate between 0.2 to 0.4 "
                                 "ml/min ... estimated to be 18-24 ml/h",
             "retrieval": "z-ai web_search, 2026-09-04"},
            {"citation": "Silverberg et al. 2002, J Neurosurg 97(6):1271",
             "verified_snippet": "mean CSF production rate for patients with "
                                 "acute hydrocephalus was 0.4 +/- 0.13 "
                                 "ml/minute; chronic 0.25 +/- 0.08 ml/min",
             "retrieval": "z-ai web_search, 2026-09-04"},
        ],
        "external_audit_error_flagged": {
            "audit_claim": "The literature suggests 0.3-0.4 mL/hr as the "
                           "physiological CSF production baseline",
            "verdict": "UNIT ERROR — CSF production is 0.2-0.4 mL/MIN "
                       "(= 12-24 mL/hr). The audit's threshold as written "
                       "would be 60x too lenient (a floor draining 0.3 "
                       "mL/hr against ~20 mL/hr production is "
                       "physiologically negligible). Never adopted "
                       "(Constitution Art. XXVII).",
        },
        "pre_registration_status": "RANGE DECLARED from physiology; the "
                                   "single operating value for the run's "
                                   "pass/fail rule is owner-gated "
                                   "pre-registration (Art. XXVII)",
    }

    floor_rows = []
    for label, d, eta, note in [
        ("canonical_shipped", 0.6, 0.6913036,
         "buyer-surface/canonical geometry, measured NIST viscosity"),
        ("nist_corrected_candidate", 0.5471, 0.6913036,
         "R390-loop NIST-compensated rebuild (sandbox; application to the "
         "canonical package is an owner release-chain decision — Art. XXXIX)"),
    ]:
        g = independent_conductance_mL_per_min_mmHg(d, eta, 100.0)
        row = {
            "geometry": label, "floor_lumen_diameter_mm": d,
            "length_mm": 100.0,
            "viscosity_mPa_s": eta,
            "conductance_mL_min_mmHg": round(g, 6),
            "evidence_class": "COMPUTATIONAL_RESULT (this script is the "
                              "computation log; inputs from recorded "
                              "geometry + NIST-measured constant)",
            "flows": {},
            "note": note,
        }
        for dp in (10.0, 20.0, 40.0):
            q = g * dp
            row["flows"][f"at_{dp:.0f}_mmHg"] = {
                "mL_per_min": round(q, 4),
                "mL_per_hr": round(q * 60.0, 1),
                "passes_q_min": bool(q >= q_min["value_range"][0]),
                "margin_over_q_min_lower": round(
                    q / q_min["value_range"][0], 1),
            }
        floor_rows.append(row)
    out["p04_q_min"] = {
        "declaration": q_min,
        "floor_flow_computation": floor_rows,
        "engineering_conclusion": (
            "The floor lumen's Poiseuille conductance EXCEEDS the "
            "physiological production rate by 6-12x at the minimum "
            "physiological head (10 mmHg) in BOTH geometries: the safety "
            "floor is NOT the flow-limiting element. Two consequences: "
            "(1) the Q_min pass rule is satisfiable with large margin "
            "when the floor lumen is unobstructed — the experiment's "
            "discriminating power therefore lies in PARTIAL common-cause "
            "obstruction, not clean-lumen conductance; (2) in the shunt "
            "SYSTEM, total drainage is governed by the valve, not by this "
            "catheter segment — a buyer must not read these numbers as "
            "'the floor drains 152 mL/hr into the patient' (over-drainage "
            "protection is the valve's function; this record is "
            "catheter-segment hydraulics only)."),
        "common_cause_tolerance_margin": {
            "statement": "effective floor diameter at which floor flow "
                         "falls to the Q_min lower bound (0.2 mL/min) at "
                         "10 mmHg, NIST-corrected geometry",
            "d_eff_mm": round(0.5471 * (0.2 / (
                independent_conductance_mL_per_min_mmHg(
                    0.5471, 0.6913036, 100.0) * 10.0)) ** 0.25, 4),
            "tolerated_diameter_reduction_pct": round(
                100.0 * (1.0 - (0.2 / (
                    independent_conductance_mL_per_min_mmHg(
                        0.5471, 0.6913036, 100.0) * 10.0)) ** 0.25), 1),
            "meaning": "obstruction beyond ~47% effective-diameter "
                       "reduction of the floor lumen at minimum head "
                       "takes residual flow below Q_min — this is the "
                       "quantified boundary the common-cause arm "
                       "measures",
            "evidence_class": "COMPUTATIONAL_RESULT",
        },
    }

    # -- 3. P11 instrument MDD (minimum detectable difference) ------------
    # Declared assumptions (all MODELLED / instrument-spec class):
    #   - sampling 10 Hz -> settling-time quantization +/- 0.05 s (half
    #     sample), uniform -> sigma_quant = 0.1/sqrt(12) = 0.0289 s
    #   - flowmeter resolution +/- 0.01 mL/min vs a 10%-of-steady-state
    #     settling band; steady-state flow range 0.1-0.5 mL/min (valved
    #     mock-CSF loop class) -> band 0.01-0.05 mL/min = 1-5x resolution
    #   - n = 10 runs per arm (R339 protocol), two-sample z-test,
    #     alpha = 0.05 two-sided (z = 1.96)
    sigma_q = 0.1 / math.sqrt(12.0)
    n = 10
    se_diff = sigma_q * math.sqrt(2.0 / n)
    mdd = 1.96 * se_diff
    claimed_diff = 0.1  # s (0.4 s damper vs 0.5 s ASD, MODELLED)
    # resolution-limited settling detection (worst case: smallest band)
    band_worst = 0.1 * 0.1  # 10% of 0.1 mL/min steady flow
    resolution = 0.01
    out["p11_instrument_mdd"] = {
        "question": "can the proposed bench instrument resolve the claimed "
                    "0.1 s settling-time difference at p<0.05 with n=10 "
                    "runs/arm?",
        "declared_assumptions": [
            {"assumption": "sampling rate", "value": 10, "unit": "Hz",
             "class": "INSTRUMENT_SPEC (proposed, R339 protocol class)"},
            {"assumption": "settling criterion",
             "value": "flow within 10% of steady state",
             "class": "PROTOCOL"},
            {"assumption": "runs per arm", "value": 10, "unit": "count",
             "class": "RECORDED (R339 protocol)"},
            {"assumption": "steady-state flow range", "value": [0.1, 0.5],
             "unit": "mL/min",
             "class": "MODELLED (valved mock-CSF loop class)"},
            {"assumption": "flowmeter resolution",
             "value": 0.01, "unit": "mL/min",
             "class": "INSTRUMENT_SPEC (proposed)"},
        ],
        "computation": {
            "settling_time_quantization_sigma_s": round(sigma_q, 5),
            "se_of_difference_s": round(se_diff, 5),
            "mdd_at_p05_s": round(mdd, 5),
            "claimed_difference_s": claimed_diff,
            "verdict": "DETECTABLE" if mdd < claimed_diff else
                       "NOT DETECTABLE AT THIS DESIGN",
            "margin_ratio": round(claimed_diff / mdd, 2),
        },
        "resolution_check": {
            "worst_case_settling_band_mL_min": round(band_worst, 4),
            "instrument_resolution_mL_min": resolution,
            "band_to_resolution_ratio": round(band_worst / resolution, 2),
            "verdict": "BAND-TO-RESOLUTION >= 1 REQUIRED; worst case "
                       f"({'PASS' if band_worst >= resolution else 'FAIL'}): "
                       "at 0.1 mL/min steady flow the 10% band (0.01 "
                       "mL/min) equals the resolution — settling detection "
                       "is marginal there; at >=0.2 mL/min it is resolved",
        },
        "honest_limits": [
            "the 0.4 s vs 0.5 s settling values are MODEL_DERIVED (tau = "
            "I_h/c_h with c_h back-calculated from gap geometry) — this "
            "MDD record says the INSTRUMENT can resolve the difference, "
            "not that the difference exists",
            "trace noise beyond quantization is not modelled (no recorded "
            "noise spectrum for the proposed instrument); if run-to-run "
            "settling-time scatter exceeds 0.05 s sigma, n must rise "
            "above 10",
            "the clinical materiality of a 0.1 s difference remains "
            "UNESTABLISHED (the differentiation record says so; this "
            "calculation does not touch that verdict)",
        ],
        "evidence_class": "COMPUTATIONAL_RESULT (this script is the "
                          "computation log)",
    }

    # -- 4. R396 recorded values: corrected counterparts ------------------
    # R396/P07_FAILURE_MODE_CONTRACT.json recorded (pre-R405):
    #   baseline (1.0mm x 90mm, eta 1.0, dP 8mmHg): 9.81831e-06 mL/min
    #   candidate SEVERE_OBSTRUCTION (floor 0.6mm x 90mm): 1.37064e-04
    #   PARTIAL_OBSTRUCTION: 3.72703e-04
    g_base = independent_conductance_mL_per_min_mmHg(1.0, 1.0, 90.0)
    g_floor_396 = independent_conductance_mL_per_min_mmHg(0.6, 1.0, 90.0)
    out["r396_recorded_values_corrected"] = {
        "baseline_true_mL_min_at_8mmHg": round(g_base * 8.0, 5),
        "recorded_value": 9.81831159895401e-06,
        "severe_obstruction_floor_true_mL_min_at_8mmHg": round(
            g_floor_396 * 8.0, 5),
        "recorded_value_severe": 1.3706362992139801e-04,
        "ratio_note": "recorded/true = 1/17,774.7 for every absolute value; "
                      "BEATS_BASELINE margins and KEEP/KILL decisions are "
                      "ratios and are unaffected",
    }

    # -- write records ------------------------------------------------------
    p04_rec = {
        "artifact_type": "QMIN_FLOOR_FLOW_CALCULATION",
        "company_designation": "P04",
        "historical_package_id": "P-07",
        "technology_name": "Passive Drainage Priority Safety Floor",
        "constitutional_basis": "Art. XXVII (threshold provenance: value, "
                                "unit, source, class, uncertainty), Art. II "
                                "(exact arithmetic shown), Art. LII "
                                "(falsification threshold quantified)",
        "purpose": "R405 external-audit item 'Declare Q_min': the decisive "
                   "experiment's pass rule references a literature-derived "
                   "Q_min; this record declares the physiological range, "
                   "computes the floor lumen's corrected flow against it, "
                   "and quantifies the common-cause tolerance margin that "
                   "makes the obstruction arm discriminating.",
        "computation_log": "scripts/r405_p04_qmin_and_conductance.py "
                           "(deterministic; this output is generated by it)",
        "contents": {
            "q_min": out["p04_q_min"]["declaration"],
            "floor_flow_computation": out["p04_q_min"][
                "floor_flow_computation"],
            "engineering_conclusion": out["p04_q_min"][
                "engineering_conclusion"],
            "common_cause_tolerance_margin": out["p04_q_min"][
                "common_cause_tolerance_margin"],
        },
    }
    (REPO / "LEAD_PORTFOLIO_4" / "P04" /
     "QMIN_FLOOR_FLOW_CALCULATION.json").write_text(canonical(p04_rec))

    p11_rec = {
        "artifact_type": "INSTRUMENT_MDD_CALCULATION",
        "company_designation": "P11",
        "historical_package_id": "P-24",
        "technology_name": "Gravity Compensation Hydraulic Damper for "
                           "Postural Transients",
        "constitutional_basis": "Art. XXVII (declared assumptions with "
                                "classes), Art. LII (measurement must be "
                                "able to falsify: an instrument that "
                                "cannot resolve the claimed difference "
                                "cannot test the hypothesis)",
        "purpose": "R405 external-audit item 'power calculation or "
                   "minimum-detectable-difference declaration': the "
                   "recorded differentiator is a 0.1 s settling-time "
                   "difference (MODELLED); this record computes whether "
                   "the proposed bench instrument can resolve it at the "
                   "recorded n=10/arm.",
        "computation_log": "scripts/r405_p04_qmin_and_conductance.py",
        "contents": out["p11_instrument_mdd"],
    }
    (REPO / "LEAD_PORTFOLIO_4" / "P11" /
     "INSTRUMENT_MDD_CALCULATION.json").write_text(canonical(p11_rec))

    # -- console summary ----------------------------------------------------
    print("=== corrected conductances (engine vs independent) ===")
    for row in cond_rows:
        print(f"  {row['case']}: engine {row['engine_value_mL_min_mmHg']:.6f}"
              f"  indep {row['independent_value_mL_min_mmHg']:.6f}"
              f"  pre-R405 recorded {row['pre_r405_recorded_value']:.3e}"
              f"  (x{row['correction_factor_true_over_recorded']})")
    print()
    print("=== P04 floor flows (mL/hr) ===")
    for row in floor_rows:
        fl = row["flows"]
        print(f"  {row['geometry']}: 10mmHg {fl['at_10_mmHg']['mL_per_hr']}"
              f"  20mmHg {fl['at_20_mmHg']['mL_per_hr']}"
              f"  40mmHg {fl['at_40_mmHg']['mL_per_hr']}")
    print(f"  Q_min range: {q_min['value_range']} mL/min "
          f"({q_min['equivalent_mL_hr']} mL/hr)")
    tm = out["p04_q_min"]["common_cause_tolerance_margin"]
    print(f"  common-cause tolerance: d_eff {tm['d_eff_mm']} mm "
          f"({tm['tolerated_diameter_reduction_pct']}% reduction tolerated)")
    print()
    print("=== P11 MDD ===")
    c = out["p11_instrument_mdd"]["computation"]
    print(f"  quantization sigma {c['settling_time_quantization_sigma_s']} s"
          f"  MDD(p<0.05) {c['mdd_at_p05_s']} s"
          f"  vs claimed 0.1 s -> {c['verdict']}"
          f" (margin x{c['margin_ratio']})")
    print()
    print("records written: LEAD_PORTFOLIO_4/P04/QMIN_FLOOR_FLOW_CALCULATION"
          ".json, LEAD_PORTFOLIO_4/P11/INSTRUMENT_MDD_CALCULATION.json")


if __name__ == "__main__":
    main()

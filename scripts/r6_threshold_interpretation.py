#!/usr/bin/env python3
"""
R6 V21.3 — Final Threshold Interpretation Tightening

Per CEO v30.18 directive:
  "Do not let a useful number become a magic number."

  0.35 mL/min is useful because it is a physiological reference.
  It becomes dangerous when silently transformed into 'therefore safe.'

  Preserve the causal chain:
    measurement → physiology → model → buyer requirement → decision

Three concepts must be separated:

  A. PHYSIOLOGICAL REFERENCE: ~0.35 mL/min average CSF production (±0.05)
  B. MODEL-DERIVED CONSEQUENCE: what time-to-ICP-danger results from each flow
  C. BUYER REQUIREMENT: how much time constitutes a clinically meaningful bridge

Do NOT assume 4 hours is clinically established.
Mark it BUYER_DEFINED / PROVISIONAL.
Replace "0.35 = indefinite drainage" with model-qualified language.
Build a flow-response curve rather than relying on two point thresholds.
"""
import json
import math
from pathlib import Path
from datetime import datetime, timezone

REPO = Path(__file__).parent.parent

# Well-established physiological parameters (from V21.2 evidence bindings)
CSF_PRODUCTION_ML_MIN = 0.35  # Pollay 2010, ±0.05
CSF_PRODUCTION_RANGE = (0.30, 0.40)  # uncertainty range
COMPLIANCE_ML_MMHG = 0.5  # Marmarou 1978, range 0.3-1.0
COMPLIANCE_RANGE = (0.3, 1.0)
ICP_ACTIVATION_MMHG = 25  # Kestle 2003
ICP_HERNIATION_MMHG = 40  # BTF 2016 (30 = emergency, 40 = herniation risk)
ICP_HERNIATION_RANGE = (30, 50)  # varies by patient


def compute_time_to_herniation(q_bypass, q_production=0.35, c_ic=0.5,
                                 icp_start=25, icp_herniation=40):
    """Compute time (hours) from bypass activation to herniation.

    Model: dICP/dt = (Q_production - Q_bypass) / C_ic

    If Q_bypass >= Q_production: net accumulation <= 0 → ICP does not rise
    → time = INDEFINITE (under model assumptions)

    If Q_bypass < Q_production: ICP rises at rate (Q_prod - Q_bypass) / C_ic
    → time = (ICP_herniation - ICP_start) / rate
    """
    net = q_production - q_bypass
    if net <= 0:
        return float('inf'), "INDEFINITE (under model: bypass flow ≥ CSF production → no net accumulation)"
    rate_mmhg_per_min = net / c_ic  # mmHg/min
    delta_icp = icp_herniation - icp_start
    time_min = delta_icp / rate_mmhg_per_min
    return time_min / 60, f"{time_min:.1f} min = {time_min/60:.2f} hours"


def flow_response_curve():
    """Build the flow-response curve for EXP-R6-02.

    Instead of relying on two point thresholds (0.05 and 0.35),
    measure the actual pressure trajectory across a range of bypass flows.
    This gives a CONTINUOUS relationship, not a binary pass/fail.
    """
    flow_points = [0, 0.05, 0.10, 0.20, 0.30, 0.35, 0.50, 1.0]

    curve = []
    for q in flow_points:
        # Best case: high compliance (1.0), low CSF production (0.30), high herniation (50)
        t_best, desc_best = compute_time_to_herniation(
            q, q_production=CSF_PRODUCTION_RANGE[0], c_ic=COMPLIANCE_RANGE[1],
            icp_herniation=ICP_HERNIATION_RANGE[1]
        )
        # Nominal case: median values
        t_nominal, desc_nominal = compute_time_to_herniation(q)
        # Worst case: low compliance (0.3), high CSF production (0.40), low herniation (30)
        t_worst, desc_worst = compute_time_to_herniation(
            q, q_production=CSF_PRODUCTION_RANGE[1], c_ic=COMPLIANCE_RANGE[0],
            icp_herniation=ICP_HERNIATION_RANGE[0]
        )

        curve.append({
            "bypass_flow_ml_min": q,
            "model_time_to_herniation": {
                "best_case_hours": t_best if t_best != float('inf') else "INDEFINITE",
                "best_case_params": "Q_prod=0.30, C_ic=1.0, ICP_hern=50",
                "nominal_case_hours": t_nominal if t_nominal != float('inf') else "INDEFINITE",
                "nominal_case_params": "Q_prod=0.35, C_ic=0.5, ICP_hern=40",
                "worst_case_hours": t_worst if t_worst != float('inf') else "INDEFINITE",
                "worst_case_params": "Q_prod=0.40, C_ic=0.3, ICP_hern=30",
            },
            "interpretation": _interpret_flow(q),
        })
    return curve


def _interpret_flow(q):
    """Provide the model-qualified interpretation for each flow point."""
    if q == 0:
        return "No bypass flow. ICP rises at physiological rate. Standard obstruction."
    if q < 0.10:
        return (f"Very low bypass flow ({q} mL/min). Under model assumptions, "
                f"provides only minutes to low tens of minutes before herniation "
                f"in the worst case. This is a VERY SHORT bridge — likely "
                f"insufficient for any meaningful clinical intervention window. "
                f"MODEL_DERIVED: actual time depends on patient-specific compliance, "
                f"CSF production, and herniation threshold.")
    if q < 0.30:
        return (f"Low bypass flow ({q} mL/min). Under model assumptions, "
                f"provides tens of minutes to ~1 hour in the nominal case. "
                f"This may be sufficient for hospitalized patients with rapid "
                f"access to neurosurgery but insufficient for community patients. "
                f"MODEL_DERIVED: clinical adequacy NOT established.")
    if q < 0.35:
        return (f"Near-physiological flow ({q} mL/min). Under model assumptions, "
                f"provides ~1-4 hours in the nominal case. This MAY constitute "
                f"a clinically meaningful bridge for urban populations. "
                f"MODEL_DERIVED: clinical adequacy PROVISIONAL — needs buyer "
                f"confirmation of target population and access-to-care time.")
    if q < 0.50:
        return (f"Flow exceeds physiological production at the lower bound "
                f"({q} > 0.30 mL/min). Under model assumptions, ICP stabilizes "
                f"or drops for patients with CSF production ≤ 0.30 mL/min. "
                f"For patients with higher production (0.40 mL/min), ICP "
                f"continues rising slowly. MODEL_DERIVED: 'indefinite drainage' "
                f"is NOT guaranteed — it depends on individual patient CSF "
                f"production relative to bypass flow.")
    return (f"Flow well exceeds physiological production ({q} mL/min >> 0.35). "
            f"Under model assumptions, ICP drops for all patients within the "
            f"physiological CSF production range (0.30-0.40). This is the "
            f"strongest model prediction. However, 'indefinite drainage' is "
            f"a MODEL CONCLUSION, not a measured clinical outcome. "
            f"The bypass may have flow degradation, valve drift, or biological "
            f"fouling that reduces flow over time.")


def final_threshold_interpretation():
    return {
        "task_id": "R6-V21.3-THRESHOLD-INTERPRETATION-TIGHTENING",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ceo_directive": "Do not let a useful number become a magic number. "
                         "Preserve: measurement → physiology → model → buyer requirement → decision.",
        "status": "INTERPRETATION_FINALIZED",

        "three_concepts_separated": {
            "A_physiological_reference": {
                "name": "CSF production rate",
                "value": "~0.35 mL/min (500 mL/day)",
                "source": "Pollay 2010 (doi:10.1186/1743-8454-7-S1-S9)",
                "exact_passage": "Cerebrospinal fluid is produced at a rate of "
                                 "approximately 500 mL per day (0.35 mL per minute) "
                                 "in the adult human.",
                "uncertainty": "±0.05 mL/min (range 0.30-0.40 across individuals)",
                "what_it_is": "A MEASURED PHYSIOLOGICAL AVERAGE. Not a safety boundary. "
                              "Not a universal constant. Not a pass criterion.",
                "what_it_is_NOT": "It is NOT 'the flow at which drainage is safe.' "
                                  "It is NOT 'the flow at which ICP stabilizes.' "
                                  "It is NOT a clinical guarantee of any kind.",
            },
            "B_model_derived_consequence": {
                "name": "Time-to-ICP-danger from bypass flow",
                "formula": "t = (ICP_herniation - ICP_activation) / "
                          "((Q_production - Q_bypass) / C_ic)",
                "parameters": {
                    "ICP_herniation": "30-50 mmHg (BTF 2016: 30 = emergency; varies)",
                    "ICP_activation": "25 mmHg (Kestle 2003: typical obstruction presentation)",
                    "Q_production": "0.30-0.40 mL/min (Pollay 2010, ±0.05)",
                    "C_ic": "0.3-1.0 mL/mmHg (Marmarou 1978; NONLINEAR — decreases at high ICP)",
                },
                "what_it_is": "A MODEL COMPUTATION showing the RELATIONSHIP between "
                              "bypass flow and time-to-danger. The model uses simplified "
                              "linear assumptions. Real physiology is nonlinear.",
                "what_it_is_NOT": "It is NOT a clinical prediction for any specific patient. "
                                  "It is NOT a safety guarantee. It is NOT a substitute "
                                  "for clinical judgment.",
                "key_limitation": "The model assumes: (1) linear compliance (WRONG — "
                                  "compliance decreases at high ICP), (2) constant CSF "
                                  "production (WRONG — varies with circadian rhythm), "
                                  "(3) no CSF absorption (WRONG — some absorption continues), "
                                  "(4) no biological degradation of bypass flow over time "
                                  "(WRONG — biofilm and valve drift may reduce flow).",
            },
            "C_buyer_requirement": {
                "name": "Minimum clinically meaningful emergency bridge duration",
                "value": "4 hours (PROVISIONAL)",
                "source": "BUYER_DEFINED — not yet clinically established",
                "status": "PROVISIONAL",
                "what_it_is": "A buyer assumption that 4 hours is sufficient time for "
                              "an urban patient to recognize symptoms, seek medical "
                              "attention, and reach a neurosurgeon for shunt revision.",
                "what_it_is_NOT": "It is NOT a clinically validated threshold. It is NOT "
                                  "based on measured time-to-revision data. It is NOT "
                                  "universal (rural patients may need 12+ hours).",
                "evidence_needed_to_upgrade": [
                    "1. Clinical data: median time from shunt obstruction symptom onset "
                    "to hospital arrival for the target patient population",
                    "2. Clinical data: median time from hospital arrival to shunt "
                    "revision surgery for the target neurosurgical center",
                    "3. Clinical data: complication rate of emergency vs scheduled "
                    "shunt revision (to quantify the benefit of the bridge)",
                    "4. Buyer confirmation: what is the target patient population "
                    "(urban vs rural, pediatric vs adult, developed vs developing)?",
                ],
                "current_status": "The 4-hour target is BUYER_DEFINED / PROVISIONAL. "
                                  "It CANNOT be treated as a clinical fact. The experiment "
                                  "must measure the flow-response curve and let the BUYER "
                                  "decide whether the resulting bridge duration is "
                                  "clinically meaningful — rather than pre-deciding that "
                                  "4 hours is the threshold.",
            },
        },

        "corrected_interpretation_of_0.35": {
            "old_language": "bypass flow ≥ 0.35 mL/min = indefinite drainage = PASS",
            "corrected_language": "At model assumptions (linear compliance, constant CSF "
                                  "production of 0.35 mL/min, no flow degradation), bypass "
                                  "flow ≥ 0.35 mL/min prevents net volume accumulation in the "
                                  "NOMINAL case. This is a MODEL CONCLUSION, not a clinical "
                                  "guarantee. The experiment must measure ACTUAL flow and "
                                  "ACTUAL pressure trajectory to determine whether the "
                                  "model holds.",
            "why_the_change_matters": "0.35 mL/min is a physiological REFERENCE value, "
                                      "not a safety BOUNDARY. Actual patient CSF production "
                                      "may be 0.40 mL/min — in which case 0.35 mL/min bypass "
                                      "flow is INSUFFICIENT for indefinite drainage. The "
                                      "experiment should measure the FLOW-RESPONSE CURVE, "
                                      "not just check whether flow exceeds a single number.",
        },

        "flow_response_curve": {
            "description": "Instead of relying on two point thresholds (0.05 and 0.35), "
                           "EXP-R6-02 will measure the actual pressure trajectory across "
                           "a range of bypass flows. This gives a CONTINUOUS relationship "
                           "that the buyer can interpret clinically.",
            "flow_points_ml_min": [0, 0.05, 0.10, 0.20, 0.30, 0.35, 0.50, 1.0],
            "what_to_measure_at_each_point": [
                "Steady-state bypass flow (mL/min, ±1%)",
                "Steady-state pressure (mmHg, ±0.5)",
                "Time to reach steady state (seconds)",
                "Pressure trajectory: does ICP rise, stabilize, or drop?",
            ],
            "model_predictions": flow_response_curve(),
            "interpretation_protocol": "The experiment measures ACTUAL flow and ACTUAL "
                                       "pressure. The model predictions above are HYPOTHESES "
                                       "to be tested, not expected results. If the actual "
                                       "pressure trajectory differs from the model, the "
                                       "MODEL is wrong, not the measurement. Report the "
                                       "actual trajectory and let the buyer interpret.",
        },

        "revised_exp_r6_02_protocol": {
            "old_protocol": "Measure bypass flow at 25 mmHg. PASS if ≥ 0.35, "
                            "CONDITIONAL_FAIL if 0.05-0.35, KILL if < 0.05.",
            "revised_protocol": "Measure bypass flow AND pressure trajectory across "
                                "8 flow points (0 to 1.0 mL/min). For each point: "
                                "record steady-state flow, steady-state pressure, "
                                "time to steady state, and pressure trajectory "
                                "(rising/stable/dropping). Report the FULL curve. "
                                "Let the buyer interpret which flow points constitute "
                                "a clinically meaningful bridge.",
            "kill_criterion_unchanged": "KILL if bypass flow at 25 mmHg < 0.05 mL/min "
                                        "(insufficient for even the shortest theoretical "
                                        "bridge under any model assumption). This is the "
                                        "only absolute kill — everything else is "
                                        "buyer-interpreted.",
            "pass_criterion_revised": "There is no single PASS threshold. The experiment "
                                      "produces a flow-response curve. The buyer decides "
                                      "which point on the curve constitutes clinical "
                                      "adequacy based on: (a) target population, "
                                      "(b) time-to-revision data, (c) complication rate "
                                      "comparison. The experiment does NOT pre-decide "
                                      "what 'adequate' means.",
        },

        "causal_chain_preserved": {
            "measurement": "Benchtop: actual bypass flow + actual pressure trajectory",
            "physiology": "CSF production ~0.35 mL/min (±0.05, Pollay 2010)",
            "model": "Time-to-ICP-danger = f(Q_bypass, Q_production, C_ic) — "
                     "linear, simplified, uncertain",
            "buyer_requirement": "4 hours PROVISIONAL — needs clinical time-to-revision "
                                 "data to upgrade from PROVISIONAL to ESTABLISHED",
            "decision": "KILL if flow < 0.05 (model-independent minimum). "
                        "Everything else: buyer interprets the flow-response curve.",
            "principle": "Do not let a useful number become a magic number. "
                         "0.35 is a physiological reference, not a safety boundary. "
                         "The experiment measures reality; the buyer interprets it.",
        },
    }


if __name__ == "__main__":
    print("=" * 78)
    print("R6 V21.3 — FINAL THRESHOLD INTERPRETATION TIGHTENING")
    print("Preserve: measurement → physiology → model → buyer requirement → decision")
    print("=" * 78)

    results = final_threshold_interpretation()

    print("\n1. THREE CONCEPTS SEPARATED")
    for key, concept in results["three_concepts_separated"].items():
        print(f"\n  {key}:")
        print(f"    Name: {concept['name']}")
        print(f"    Value: {concept.get('value', 'N/A')}")
        print(f"    What it IS: {concept['what_it_is'][:100]}...")
        print(f"    What it is NOT: {concept['what_it_is_NOT'][:100]}...")

    print("\n2. CORRECTED INTERPRETATION OF 0.35")
    ci = results["corrected_interpretation_of_0.35"]
    print(f"  Old: {ci['old_language']}")
    print(f"  New: {ci['corrected_language'][:150]}...")

    print("\n3. FLOW-RESPONSE CURVE")
    curve = results["flow_response_curve"]["model_predictions"]
    print(f"  {'Flow (mL/min)':<15} {'Best (h)':<15} {'Nominal (h)':<15} {'Worst (h)':<15}")
    print(f"  {'-'*60}")
    for c in curve:
        best = c["model_time_to_herniation"]["best_case_hours"]
        nom = c["model_time_to_herniation"]["nominal_case_hours"]
        worst = c["model_time_to_herniation"]["worst_case_hours"]
        best_s = f"{best:.2f}" if isinstance(best, float) else str(best)[:10]
        nom_s = f"{nom:.2f}" if isinstance(nom, float) else str(nom)[:10]
        worst_s = f"{worst:.2f}" if isinstance(worst, float) else str(worst)[:10]
        print(f"  {c['bypass_flow_ml_min']:<15} {best_s:<15} {nom_s:<15} {worst_s:<15}")

    print("\n4. REVISED EXP-R6-02 PROTOCOL")
    rp = results["revised_exp_r6_02_protocol"]
    print(f"  Old: {rp['old_protocol'][:100]}...")
    print(f"  New: {rp['revised_protocol'][:100]}...")
    print(f"  Kill: {rp['kill_criterion_unchanged'][:100]}...")
    print(f"  Pass: {rp['pass_criterion_revised'][:100]}...")

    print(f"\n{'='*78}")
    print("CAUSAL CHAIN PRESERVED:")
    cc = results["causal_chain_preserved"]
    print(f"  measurement → {cc['measurement']}")
    print(f"  physiology  → {cc['physiology']}")
    print(f"  model       → {cc['model']}")
    print(f"  buyer       → {cc['buyer_requirement']}")
    print(f"  decision    → {cc['decision']}")
    print(f"  principle   → {cc['principle']}")
    print(f"{'='*78}")

    output = REPO / "CEREVASC_TERRITORY_6_V8_MECHANISM_RESET" / "V21_3_R6_THRESHOLD_INTERPRETATION.json"
    with open(output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to: {output}")

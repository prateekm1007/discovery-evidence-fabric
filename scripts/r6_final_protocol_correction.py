#!/usr/bin/env python3
"""
R6 V21.4 — Final Protocol Correction Before Physical Execution

Per CEO v30.19 directive:
  "Stop asking whether the invention passes a threshold.
   Ask what measurable relationship the invention creates in the real world."

Three changes:

1. RENAME: "KILL < 0.05 mL/min" → "PRE-REGISTERED ENGINEERING FLOOR /
   PROVISIONAL KILL CRITERION" with explicit contingencies on:
   target population + compliance envelope + danger threshold +
   access-to-care requirement.

2. EXPAND EXP-R6-01: measure opening pressure DISTRIBUTION → HYSTERESIS →
   REPEATABILITY → DRIFT, not just a single opening number.

3. PRIMARY OUTPUT: the flow-response curve is the primary experimental
   output. No simulated curves as substitutes for measured curves.

The invention question is no longer "does R6 pass?" but:
  "What flow can this architecture reliably produce, and what pressure
   trajectory does that create across the clinically relevant
   physiological envelope?"
"""
import json
from pathlib import Path
from datetime import datetime, timezone

REPO = Path(__file__).parent.parent


def final_protocol_correction():
    return {
        "task_id": "R6-V21.4-FINAL-PROTOCOL-CORRECTION",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ceo_directive": "Stop asking whether the invention passes a threshold. "
                         "Ask what measurable relationship the invention creates.",
        "status": "PROTOCOL_FINALIZED — ready for physical execution",

        "change_1_rename_kill_threshold": {
            "old_name": "KILL if bypass flow < 0.05 mL/min",
            "new_name": "PRE-REGISTERED ENGINEERING FLOOR / PROVISIONAL KILL CRITERION",
            "value": 0.05,
            "unit": "mL/min",
            "rationale_for_rename": "The 0.05 threshold was called 'model-independent' "
                                    "but it is NOT model-independent. It depends on "
                                    "assumptions about compliance, ICP danger threshold, "
                                    "CSF production, acceptable bridge time, and patient "
                                    "population. The correct status is a PRE-REGISTERED "
                                    "ENGINEERING FLOOR: a conservative lower bound below "
                                    "which no plausible model interpretation gives a "
                                    "clinically useful bridge. It is PROVISIONAL because "
                                    "the contingencies below have not been independently "
                                    "validated.",
            "contingencies": {
                "target_population": "Assumed urban with hospital access within 2-4 hours. "
                                     "Rural populations may need a higher floor.",
                "compliance_envelope": "Assumed C_ic = 0.3-1.0 mL/mmHg. At C_ic = 0.3 "
                                       "(worst case), 0.05 mL/min gives ~7 minutes "
                                       "to herniation — likely insufficient for any "
                                       "population.",
                "danger_threshold": "Assumed ICP > 30 mmHg = emergency (BTF 2016). "
                                    "Some patients herniate at 25 mmHg.",
                "access_to_care_requirement": "Assumed 4 hours (PROVISIONAL — not "
                                              "clinically established). At 0.05 mL/min, "
                                              "the model gives 25 minutes (nominal) to "
                                              "1.67 hours (best case) — below 4 hours "
                                              "in ALL model cases.",
                "cSF_production": "Assumed 0.30-0.40 mL/min (Pollay 2010). At 0.40 "
                                  "(high production), 0.05 mL/min gives less time.",
            },
            "what_happens_if_flow_is_below_0.05": "The bypass provides insufficient flow "
                "for ANY plausible model interpretation to give a clinically useful bridge. "
                "R6 is KILLED under the PROVISIONAL kill criterion. The kill is "
                "PROVISIONAL because the contingencies above have not been independently "
                "validated — but the conservative interpretation is that 0.05 mL/min "
                "is too low for any realistic clinical scenario.",
            "what_happens_if_flow_is_0.05_to_0.50": "The bypass provides a flow that "
                "MAY be clinically useful depending on patient physiology and access-to-"
                "care time. The experiment measures the ACTUAL flow-response curve and "
                "the BUYER interprets which point constitutes clinical adequacy. No "
                "pre-registered pass/fail — the data speaks for itself.",
            "what_happens_if_flow_is_above_0.50": "The bypass provides flow exceeding "
                "CSF production in ALL model cases (0.30-0.40 mL/min). Under model "
                "assumptions, ICP drops for all patients. This is the strongest model "
                "prediction — but it is still a MODEL conclusion, not a measured "
                "clinical outcome.",
        },

        "change_2_expand_exp_r6_01": {
            "old_protocol": "Measure opening pressure for 20 valves. "
                            "PASS if ≥19/20 open in 15-30 mmHg, median 20-25.",
            "expanded_protocol": "Measure the FULL opening pressure CHARACTERIZATION, "
                                 "not just a single opening number.",
            "measurements_per_valve": [
                {
                    "measurement": "opening_pressure_distribution",
                    "what": "Pressure at which flow first exceeds 0.01 mL/min on "
                            "increasing pressure ramp (0→50 mmHg, 1 mmHg steps)",
                    "why": "Establishes the population distribution of opening pressures "
                           "across manufacturing variation",
                    "output": "Histogram + median + IQR + range",
                },
                {
                    "measurement": "hysteresis",
                    "what": "Pressure at which flow drops below 0.01 mL/min on "
                            "DECREASING pressure ramp (50→0 mmHg, 1 mmHg steps). "
                            "Compare opening vs closing pressure.",
                    "why": "A valve that opens at 25 mmHg but closes at 10 mmHg "
                           "creates a wide hysteresis loop — the bypass stays open "
                           "even after ICP drops. This could cause over-drainage "
                           "after the emergency passes.",
                    "output": "Hysteresis loop width (mmHg) = P_open - P_close",
                    "concern_if": "Hysteresis > 10 mmHg (bypass stays open after "
                                  "ICP returns to normal → chronic over-drainage risk)",
                },
                {
                    "measurement": "repeatability",
                    "what": "Repeat the opening pressure measurement 3 times per valve "
                            "on separate pressure ramps (with 5-minute rest between). "
                            "Calculate within-valve coefficient of variation (CV).",
                    "why": "A valve that opens at 22 mmHg on cycle 1, 18 mmHg on "
                           "cycle 2, and 28 mmHg on cycle 3 is UNRELIABLE — the "
                           "opening pressure is not repeatable.",
                    "output": "Within-valve CV (%) = SD / mean × 100",
                    "concern_if": "CV > 10% (opening pressure varies by >10% between "
                                  "cycles → unreliable valve)",
                },
                {
                    "measurement": "drift",
                    "what": "After 100 open-close cycles (simulating 100 obstruction-"
                            "resolution events over a simulated device lifetime), "
                            "re-measure opening pressure. Compare to initial.",
                    "why": "A valve that drifts from 22 mmHg to 15 mmHg after 100 "
                           "cycles will open during normal operation after a few "
                           "years of use — creating chronic over-drainage.",
                    "output": "Drift (mmHg) = P_open_after_100_cycles - P_open_initial",
                    "concern_if": "Drift > 5 mmHg downward (valve loosens over time → "
                                  "premature opening → over-drainage)",
                },
            ],
            "revised_pass_criteria": {
                "opening_distribution": "≥ 19/20 valves open in 15-30 mmHg, median 20-25",
                "hysteresis": "Median hysteresis < 10 mmHg",
                "repeatability": "Within-valve CV < 10%",
                "drift": "Median drift < 5 mmHg downward after 100 cycles",
            },
            "revised_kill_criteria": {
                "opening_distribution": "> 1/20 outside 15-30 mmHg OR median outside 20-25",
                "hysteresis": "Median hysteresis > 15 mmHg (bypass stays open too long "
                              "after ICP normalizes → chronic over-drainage risk)",
                "repeatability": "Any valve with CV > 20% (unreliable opening pressure)",
                "drift": "Any valve with drift > 10 mmHg downward (valve loosens → "
                         "premature opening after simulated lifetime)",
            },
            "statistical_interpretation": {
                "PASS": "ALL four criteria pass",
                "CONDITIONAL_PASS": "Opening distribution passes BUT one secondary "
                                    "criterion (hysteresis/repeatability/drift) fails. "
                                    "R6 survives but needs design improvement before "
                                    "EXP-R6-02.",
                "FAIL": "Opening distribution fails → R6 is KILLED. Do not proceed "
                        "to EXP-R6-02.",
                "INCONCLUSIVE": "Calibration failure (positive control outside spec) → "
                                "entire experiment invalidated, repeat after recalibration.",
            },
        },

        "change_3_primary_output": {
            "principle": "The flow-response curve is the PRIMARY EXPERIMENTAL OUTPUT. "
                         "No simulated curves as substitutes for measured curves.",
            "what_this_means": "EXP-R6-02 does NOT compare measured flow to a model "
                               "prediction and declare pass/fail. It MEASURES the actual "
                               "flow-pressure relationship and REPORTS it. The model "
                               "predictions (from V21.3) are HYPOTHESES to be tested, "
                               "not expected results.",
            "if_model_and_measurement_disagree": "The MODEL is wrong, not the measurement. "
                "Report the actual curve. Do not adjust the model to match the data "
                "(Article VII). Do not discard data points that deviate from the model "
                "(Article XV). The disagreement between model and measurement IS the "
                "finding — it tells us where our assumptions break down.",
            "what_the_buyer_receives": "A measured flow-response curve with: actual "
                "bypass flow at each pressure point, actual pressure trajectory (rising/"
                "stable/dropping), time to steady state, and measurement uncertainty. "
                "The buyer interprets this against their clinical requirements — which "
                "are PROVISIONAL until time-to-revision data is obtained.",
        },

        "invention_question_reformulated": {
            "old_question": "Does R6 pass the threshold?",
            "new_question": "What flow can this architecture reliably produce, and what "
                            "pressure trajectory does that create across the clinically "
                            "relevant physiological envelope?",
            "why_this_is_stronger": "The old question treats the invention as a binary "
                                    "pass/fail. The new question treats it as a "
                                    "MEASURABLE RELATIONSHIP. The invention's value "
                                    "depends on WHERE on the flow-response curve the "
                                    "device operates and HOW that maps to the buyer's "
                                    "clinical requirements. The experiment discovers "
                                    "the relationship; the buyer interprets it.",
        },

        "summary": {
            "total_changes": 3,
            "change_1": "Renamed KILL < 0.05 to PRE-REGISTERED ENGINEERING FLOOR / "
                        "PROVISIONAL KILL with 5 explicit contingencies",
            "change_2": "Expanded EXP-R6-01 from single opening measurement to 4 "
                        "characterization measurements (distribution + hysteresis + "
                        "repeatability + drift)",
            "change_3": "Flow-response curve is primary output; no simulated curves "
                        "as substitutes; model-measurement disagreement IS the finding",
            "protocol_status": "FINALIZED — ready for physical execution of EXP-R6-01",
            "next_step": "Fabricate 20 valve prototypes. Execute EXP-R6-01 with the "
                         "expanded 4-measurement protocol. Do not proceed to EXP-R6-02 "
                         "unless EXP-R6-01 passes.",
        },
    }


if __name__ == "__main__":
    print("=" * 78)
    print("R6 V21.4 — FINAL PROTOCOL CORRECTION BEFORE PHYSICAL EXECUTION")
    print("=" * 78)

    results = final_protocol_correction()

    print("\n1. RENAMED KILL THRESHOLD")
    c1 = results["change_1_rename_kill_threshold"]
    print(f"  Old: {c1['old_name']}")
    print(f"  New: {c1['new_name']}")
    print(f"  Value: {c1['value']} {c1['unit']}")
    print(f"  Contingencies: {len(c1['contingencies'])} explicit")
    for k, v in c1["contingencies"].items():
        print(f"    {k}: {v[:80]}...")

    print("\n2. EXPANDED EXP-R6-01")
    c2 = results["change_2_expand_exp_r6_01"]
    print(f"  Measurements per valve: {len(c2['measurements_per_valve'])}")
    for m in c2["measurements_per_valve"]:
        print(f"    {m['measurement']}: {m['what'][:80]}...")
        if 'concern_if' in m:
            print(f"      Concern if: {m['concern_if'][:80]}...")

    print("\n3. PRIMARY OUTPUT = FLOW-RESPONSE CURVE")
    c3 = results["change_3_primary_output"]
    print(f"  Principle: {c3['principle'][:80]}...")
    print(f"  If model≠measurement: {c3['if_model_and_measurement_disagree'][:80]}...")

    print(f"\n{'='*78}")
    print("INVENTION QUESTION REFORMULATED:")
    iq = results["invention_question_reformulated"]
    print(f"  Old: {iq['old_question']}")
    print(f"  New: {iq['new_question']}")
    print(f"\nPROTOCOL STATUS: {results['summary']['protocol_status']}")
    print(f"NEXT: {results['summary']['next_step']}")
    print(f"{'='*78}")

    output = REPO / "CEREVASC_TERRITORY_6_V8_MECHANISM_RESET" / "V21_4_R6_FINAL_PROTOCOL_CORRECTION.json"
    with open(output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to: {output}")

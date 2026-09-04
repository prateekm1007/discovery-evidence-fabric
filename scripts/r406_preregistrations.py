#!/usr/bin/env python3
"""R406 Steps 4, 5, 8 — frozen experiment pre-registrations.

Step 4 (P04): finalize the common-cause physical protocol with full
pre-registration — Q_min, common-cause kill threshold, false-pass rule,
repeatability, sample size, decision rule. Arms: primary-only obstruction,
floor-only obstruction, simultaneous common-cause obstruction, vs
single-lumen baseline.

Step 5 (P11): the buyer-executable experimental contract — blinded
analysis, predefined primary endpoint, predefined MDD, quantitative kill
condition, manufacturing tolerance, cost, timeline, statistical analysis
plan. Capable of SUPPORTED or KILLED.

Step 8 (P13): the KA-014 explicit kill experiment — baseline,
self-reference, accelerated fouling, thermal cycling, combined
fouling+thermal. Periodic recalibration is NOT counted as a mechanism fix.

Threshold provenance: every registered value carries class + source per
Art. XXVII. The R405 'owner-gated' single-value pre-registrations are
REGISTERED NOW under the R406 CEO directive (the operator instruction
authorizing registration is itself the recorded provenance). No threshold
is invented: each is (a) carried from a recorded R405 proposal now
confirmed, (b) derived arithmetically from a recorded physiological
range, or (c) a recorded protocol constant.
"""
import json
import math
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def write(rel, obj):
    out = os.path.join(REPO, rel)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(obj, f, indent=1, sort_keys=True)
    print(f"wrote {rel}")


# ---------------- Step 4: P04 ----------------
P04 = {
    "artifact_type": "EXPERIMENT_PREREGISTRATION",
    "company_designation": "P04",
    "historical_package_id": "P-07",
    "portfolio_number": "04",
    "technology_name": "Passive Drainage Priority Safety Floor",
    "directive_basis": "R406 Step 4: the common-cause experiment becomes the primary reality target; pre-register Q_min, common-cause kill threshold, false-pass rule, repeatability, sample size, decision rule — no post-hoc threshold selection",
    "constitutional_basis": "Art. LII (falsification contract), Art. XXVII (threshold provenance — every value below carries class, source, uncertainty), Art. XLVII (identical instrument across arms)",
    "contract_of_record": "LEAD_PORTFOLIO_4/P04/DECISIVE_EXPERIMENT.json (the 12-element contract; this pre-registration freezes its numeric rules)",
    "registration_event": {
        "registered_by": "R406 round under the CEO directive (the operator instruction to pre-register is the authorizing provenance for the single-value rules the R405 records left owner-gated)",
        "frozen_before_any_run": True,
        "no_post_hoc_rule": "if any threshold below is changed after data collection begins, the run is void and the change is recorded as a constitutional event (Art. XXVII forbids silent drift)"
    },

    "arms": {
        "A_control_single_lumen": "standard single-lumen distal CSF shunt catheter, same material/OD/length — the clinical baseline (Art. XLVII: identical bench, identical instrument)",
        "B_treatment_dual_lumen": "shipped parametric design: primary 1.1 mm + floor 0.6 mm, 3.0 mm OD, 100 mm (canonical geometry per R406_P04_NIST_DECISION.json: RETAIN 0.6)",
        "obstruction_conditions": [
            "PRIMARY_ONLY: primary lumen fully obstructed (simulant), floor lumen open — residual floor drainage is the headline measurement",
            "FLOOR_ONLY: floor lumen fully obstructed, primary open — degradation behavior and drainage-priority validation (the primary must carry the load; this arm falsifies the 'floor is a liability when blocked' alternative)",
            "COMMON_CAUSE: both lumens exposed to the same simulant simultaneously — the package's own recorded critical kill condition, measured per-lumen (isolated floor port sensor)"
        ],
        "simulant_classes": ["proteinaceous debris analog", "tissue-ingrowth analog"],
        "pressure_heads_mmHg": [10, 20, 40],
        "measured_quantities": ["steady-state flow per lumen (mL/min, gravimetric or calibrated meter)",
                                 "inlet/outlet pressure (mmHg)",
                                 "time-to-steady-state and time-to-zero-flow (s)",
                                 "obstruction state (endoscopic/visual verification per lumen, post-test)",
                                 "residual drainage (integrated volume over protocol horizon)"]
    },

    "preregistered_thresholds": {
        "Q_min_pass_rule": {
            "rule": "PASS requires residual floor-lumen flow (PRIMARY_ONLY arm) >= 0.4 mL/min (12 mL/hr) at >= 2 of the 3 pressure heads",
            "value": 0.4,
            "unit": "mL/min",
            "threshold_class": "PHYSIOLOGICAL",
            "provenance": "upper bound of the literature-derived CSF production range 0.2-0.4 mL/min (Tariq et al. 2023 PMC10409822; Silverberg et al. 2002 J Neurosurg 97(6):1271 — web-search-verified snippets recorded in QMIN_FLOOR_FLOW_CALCULATION.json)",
            "justification": "the floor must keep pace with the WORST-CASE production rate to claim clinically meaningful protection; using the upper bound makes the pass rule strict, not lenient",
            "uncertainty": "literature range carried from external precedent; full-text verification open"
        },
        "Q_min_kill_rule": {
            "rule": "KILL (channel b of the falsifier) if residual floor-lumen flow < 0.2 mL/min (6 mL/hr) at ALL pressure heads",
            "value": 0.2,
            "unit": "mL/min",
            "threshold_class": "PHYSIOLOGICAL",
            "provenance": "lower bound of the same literature range — below minimal production the floor provides no meaningful protection",
            "justification": "the kill bound is the mirror of the pass bound; the 0.2-0.4 band between them routes to INDETERMINATE (recorded, never promoted)"
        },
        "common_cause_kill_threshold": {
            "rule": "KILL (channel a) if the simulant occludes the floor lumen in >= 90% of the tested pressure/flow cases in the COMMON_CAUSE arm",
            "value": 90,
            "unit": "percent of tested cases",
            "threshold_class": "ENGINEERING",
            "provenance": "the R405-recorded proposal (external-audit quantification of the package's own recorded critical kill condition), now REGISTERED under the R406 directive",
            "justification": "a safety floor that is occluded in the common-cause mode nearly always is not a safety floor; 90% leaves explicit room for borderline behavior to route to INDETERMINATE rather than KILL",
            "uncertainty": "engineering bound, not a clinical-epidemiology derivation; the common-cause mechanism itself is qualitatively recorded in the frozen dossier"
        },
        "false_pass_rule": {
            "rule": "a trial counts as a PASS only if ALL hold: (1) primary-lumen obstruction verified post-test (endoscopic/visual) in obstruction arms; (2) floor flow measured through the isolated floor port with the primary fixture independently blanked (no parallel leak path); (3) fixture leak test at 1.5x max head passes with leak <= 0.02 mL/min; (4) the single-lumen control arm, fully obstructed, reads < 0.02 mL/min (the zero-leak anchor); (5) steady state confirmed (flow drift < 10% of mean over the final 5 minutes). Any trial failing (1)-(5) is VOID and cannot count toward a pass.",
            "leak_threshold_value": 0.02,
            "leak_threshold_derivation": "10% of the Q_min lower bound (0.2 mL/min) — derived arithmetically from the registered physiological bound, not invented",
            "threshold_class": "ENGINEERING (derived from PHYSIOLOGICAL bound)"
        },
        "repeatability": {
            "rule": "3 repetitions per condition per sample; a condition-level criterion is met only if it holds in >= 2 of 3 repetitions; ALL raw traces are reported (no selection)",
            "threshold_class": "PROTOCOL (recorded R403/R339 sibling-protocol class)"
        },
        "sample_size": {
            "rule": "3 samples per arm x 2 simulant classes x 3 pressure heads x 3 repetitions (minimum credible matrix, per the R403 contract's sample_size_basis)",
            "sizing_target": "detects qualitative mechanism failure (residual flow vs none; common-cause vs not); NOT powered for a clinical effect size — recorded limitation",
            "threshold_class": "ENGINEERING (protocol)"
        },
        "modelled_expectations_preregistered": {
            "floor_segment_conductance": "0.368 mL/(min*mmHg) at the measured NIST viscosity (QMIN record, canonical geometry) — the bench value is compared against THIS prediction (Step 11 model-vs-measurement update)",
            "G_ratio_modelled": "G_floor/G_primary = (0.6/1.1)^4 = 0.0885 (viscosity-invariant; Poiseuille validity endpoint)"
        }
    },

    "decision_rule": {
        "ACCEPT": "residual floor flow >= 0.4 mL/min at >=2 of 3 heads AND common-cause occlusion rate < 90% AND measured G ratio within +/-30% of the modelled 0.0885 (Poiseuille validity at bench Reynolds) -> package advances to SPONSORED_VALIDATION with the first PHYSICAL_OBSERVATION-class evidence through the reality-boundary interface",
        "KILL": "common-cause occlusion >= 90% (mechanism's own kill condition) OR residual floor flow < 0.2 mL/min at all heads (no meaningful protection) OR no sample passes the min-wall constraint across the full manufacturing attempt (Art. XXIX invariant-class only if proven for the design space) -> cemetery entry with the kill class + lesson codified (Art. LI)",
        "INDETERMINATE": "residual flow in the 0.2-0.4 band, or simulant-only doubt dominant -> recorded exactly so; never promoted (Art. XLII discipline applied to experiments)",
        "G_ratio_tolerance_provenance": {"value": 30, "class": "ENGINEERING", "justification": "bench-vs-Poiseuille agreement band for laminar micro-lumen flow with simulant-laden fixtures; the ratio endpoint is secondary, so a wide disclosed band; +/-30% is registered, not tuned"}
    },

    "cost_and_time": {
        "cost_range": "$11-25K (REPORTED external-audit itemization: loop $2-5K, extrusion samples $3-8K, simulants $1-2K, personnel $5-10K)",
        "cost_class": "ENGINEERING_ESTIMATE (REPORTED; owner confirmation outstanding)",
        "time": "~8 weeks (sibling protocol class, REPORTED)",
        "sibling_anchor": "P-24's recorded $15K/8wk comparable bench loop"
    },
    "safety": "in-vitro bench only; no human/animal subjects; no implantation",
    "honest_limits": [
        "obstruction simulants are analogs, not ex-vivo human tissue (transfer risk recorded)",
        "water/CSF-mimic viscosity residual vs CSF (NIST 310.15 K water anchored; CSF slightly higher)",
        "bench horizon excludes biological fouling timelines (chronic in-vivo obstruction differs from acute simulant occlusion)",
        "the manufacturing observation is qualitative (process capability remains a recorded UNKNOWN)"
    ]
}

# ---------------- Step 5: P11 ----------------
P11 = {
    "artifact_type": "EXPERIMENT_PREREGISTRATION",
    "company_designation": "P11",
    "historical_package_id": "P-24",
    "portfolio_number": "11",
    "technology_name": "Gravity Compensation Hydraulic Damper for Postural Transients",
    "directive_basis": "R406 Step 5: turn the R339 protocol into a buyer-executable experimental contract — blinded analysis, predefined primary endpoint, predefined MDD, quantitative kill condition, manufacturing tolerance, cost, timeline, statistical analysis plan; capable of SUPPORTED or KILLED, not merely an interesting graph",
    "constitutional_basis": "Art. LII, Art. XXVII, Art. XLVII (REAL ASD comparator, identical instrument, baseline unchanged across arms)",
    "contract_of_record": "LEAD_PORTFOLIO_4/P11/DECISIVE_EXPERIMENT.json (the 12-element lift of the R339 protocol; this pre-registration freezes its numeric rules)",
    "registration_event": {
        "registered_by": "R406 round under the CEO directive (the authorizing provenance for the R405 owner-gated kill conditions)",
        "frozen_before_any_run": True,
        "no_post_hoc_rule": "any post-collection change to a registered threshold voids the run (Art. XXVII)"
    },

    "design": {
        "arms": {
            "treatment": "the hydraulic damper element (annular-gap architecture, 0.18 mm gap class) inline in the mock CSF loop",
            "control_1_ASD": "a REAL commercial anti-siphon device (the incumbent baseline the differentiators are claimed against — not a modeled ASD)",
            "control_2_standard": "standard valve catheter (null anchor)"
        },
        "matrix": "3 arms x 4 postural pressures (10/20/30/40 mmHg) x 10 runs per arm-pressure (the recorded R339 protocol) x 2 step profiles (physiological 1-3 s transition class AND fast-step stress case)",
        "apparatus": "mock CSF loop: programmable pressure-head reservoir, flow sensor (0.01 mL/min resolution class), postural-step actuation, continuous acquisition >= 10 Hz, temperature-controlled fluid",
        "blinding": "blinded analysis: the analysis script receives arm labels as anonymized codes A/B/C unsealed only after the primary-endpoint verdicts are computed and committed (the recorded R339 requirement, made explicit)"
    },

    "primary_endpoints_preregistered": {
        "endpoint_1_response_time": {
            "definition": "time from postural pressure step to flow settling within 10% of steady state (per run)",
            "headline_claim_under_test": "damper settles 0.1 s FASTER than ASD (MODELLED: tau = I_h/c_h; 0.4 s vs 0.5 s class)",
            "instrument_MDD": 0.0253,
            "MDD_unit": "s",
            "MDD_provenance": "LEAD_PORTFOLIO_4/P11/INSTRUMENT_MDD_CALCULATION.json (COMPUTATIONAL_RESULT: MDD 0.0253 s at p<0.05, n=10/arm — the claimed 0.1 s difference is 3.95x the MDD, DETECTABLE)",
            "kill_condition_A_registered": {
                "rule": "the response-speed differentiator is NOT established — KILL unless endpoint 2 is decisively positive — if the damper's mean settling time is not >= 20% faster than the ASD arm at ALL four postural pressures",
                "value": 20,
                "unit": "percent faster",
                "threshold_class": "MODEL_DERIVED (engineering-judgment proposal, R405-recorded; registered under the R406 directive — NEVER presented as a clinical-materiality derivation)",
                "uncertainty": "clinical materiality of a 0.1 s difference remains UNESTABLISHED (the differentiation record); the registered margin tests ENGINEERING materiality only",
                "statistical_form": "paired comparison per pressure: mean settling time damper vs ASD, one-sided test, alpha 0.05, n=10 pairs"
            }
        },
        "endpoint_2_proportional_modulation": {
            "definition": "flow-trace proportionality error: mean absolute deviation of instantaneous flow from the linear-in-pressure target trajectory across the step (per run)",
            "headline_claim_under_test": "the damper modulates flow proportionally/continuously where the ASD acts stepwise",
            "kill_condition_B_registered": {
                "rule": "the safety case is negative — KILL — if the damper's target-flow accuracy (mean absolute deviation from target flow at steady state) is statistically worse than the ASD arm at ANY tested pressure",
                "threshold_class": "ENGINEERING (recorded falsifier disadvantage-class clause, R339/R405)",
                "statistical_form": "paired one-sided test per pressure, alpha 0.05 (Wilcoxon signed-rank on paired per-pressure means; n=10 pairs)"
            }
        }
    },

    "statistical_analysis_plan": {
        "primary_analysis": "per-endpoint, per-pressure paired comparisons (damper vs ASD), one-sided, alpha = 0.05, n = 10 pairs per comparison",
        "alpha_class": {"value": 0.05, "class": "PROTOCOL (conventional; registered, not tuned)"},
        "test_choice": "Wilcoxon signed-rank (paired, distribution-free — no normality assumption for settling-time traces); reported with exact p and Hodges-Lehmann shift estimate",
        "multiplicity": "the four pressures are REPORTED per-pressure (no pooled override); a pooled verdict requires the same direction in >= 3 of 4 pressures (registered)",
        "no_data_peeking": "all thresholds above are frozen; the analysis script is committed before any run (the recorded R339 blinded-analysis harness)",
        "success_requires": "BOTH endpoint 1 kill-condition-A avoided AND endpoint 2 kill-condition-B avoided AND >= 1 endpoint decisively POSITIVE (the pre-declared differentiators promoted to endpoints) — otherwise the honest outcome is NOT SUPPORTED (recorded exactly)"
    },

    "manufacturing_tolerance": {
        "constraint": "damper prototypes at 0.18 mm +/- 0.01 mm annular gap, implant-grade polymer (the audit's tolerance challenge, recorded as the manufacturing feasibility UNKNOWN)",
        "class": "ENGINEERING (REPORTED external-audit challenge)",
        "measurement": "gap verification per prototype (metrology record required before the run; prototypes outside tolerance are excluded and REPORTED, not silently dropped)"
    },
    "MDD_and_resolution_disclosure": {
        "worst_case": "at 0.1 mL/min steady flow the 10% settling band equals the 0.01 mL/min flowmeter resolution — settling detection is marginal there (INSTRUMENT_MDD_CALCULATION resolution_check)",
        "mitigation_registered": "the physiological flow range for analysis is >= 0.2 mL/min pressures; runs at < 0.2 mL/min steady flow are flagged resolution-limited in the report (never silently included or excluded)"
    },
    "cost_and_time": {
        "recorded": "$15K / 8 weeks (R339-recorded for this exact protocol class)",
        "wider_range_context": "$15-38K (REPORTED audit itemization: loop $3-8K; prototypes $5-15K; commercial ASD controls $2-5K; personnel $5-10K)",
        "class": "RECORDED + REPORTED context"
    },
    "decision_rule": {
        "SUPPORTED": "both kill conditions avoided AND at least one endpoint decisively positive -> SPONSORED_VALIDATION advances with the first PHYSICAL_OBSERVATION-class evidence attached",
        "KILLED": "kill condition A (with endpoint 2 not decisively positive) OR kill condition B -> repair pipeline, then cemetery if repair fails (the R339-recorded path), lesson codified (Art. LI)",
        "MIXED": "one differentiator positive, one null -> recorded exactly so; no partial promotion",
        "model_update_hook": "prediction_before registered: settling time 0.4 s (damper) / 0.5 s (ASD class) per the first-order model tau = I_h/c_h — the bench measurement updates this model through the Step 11 machinery (error_before/error_after/held_out_error)"
    },
    "honest_limits": [
        "mock loop fluid is water/CSF-mimic (NIST 310.15 K viscosity class; CSF residual disclosed)",
        "excludes biological fouling and in-vivo compliance",
        "clinical materiality of the settling difference is NOT established by this bench (it establishes engineering materiality only)",
        "commercial ASD device tolerances may differ from the modeled ASD profile (why a REAL ASD is the comparator)"
    ]
}

# ---------------- Step 8: P13 ----------------
P13 = {
    "artifact_type": "EXPERIMENT_PREREGISTRATION",
    "company_designation": "P13",
    "historical_package_id": "P-27-R1",
    "portfolio_number": "13",
    "technology_name": "Self-Referencing Piezoresistive Pressure Sensor",
    "directive_basis": "R406 Step 8: KA-014 must be an explicit kill experiment — build the predecessor failure directly in: baseline / self-reference / accelerated fouling / thermal cycling / combined fouling + thermal cycling. The experiment must determine whether the architecture actually suppresses non-common-mode drift. Periodic recalibration must NOT be counted as a mechanism fix.",
    "constitutional_basis": "Art. LII, Art. XXVII, Art. XLVII (paired same-die baseline; identical instrument, simultaneous acquisition), Art. XXIX (the predecessor T1-FAIL conditions re-admission, does not kill the family)",
    "contract_of_record": "LEAD_PORTFOLIO_4/P13/DECISIVE_EXPERIMENT.json + LEAD_PORTFOLIO_4/P13/BENCHMARK_SPECIFICATION.json",
    "registration_event": {
        "registered_by": "R406 round under the CEO directive (authorizing the R405 owner-gated fouling criterion)",
        "frozen_before_any_run": True,
        "no_post_hoc_rule": "any post-collection change to a registered threshold voids the run (Art. XXVII)"
    },

    "design": {
        "arms": [
            {"arm": "1_baseline_single_ended", "what": "same die/process family single-ended sensor — the control (ONLY the self-referencing architecture differs)"},
            {"arm": "2_self_referencing_clean", "what": "active + dummy bridge, no fouling/cycling stress — the common-mode thermal-drift claim, isolated"},
            {"arm": "3_self_referencing_fouling", "what": "self-referencing arm under accelerated fouling (BSA at physiological concentration, 37 C, 4-week soak, weekly bridge-offset reads) — the KA-014 kill channel, isolated"},
            {"arm": "4_self_referencing_thermal_cycling", "what": "self-referencing arm under thermal cycling (33-41 C sweep class) — the common-mode channel the architecture claims, stressed"},
            {"arm": "5_combined_fouling_plus_thermal", "what": "self-referencing arm under BOTH stresses simultaneously — the real-world composition the P-25 failure mode predicts"}
        ],
        "apparatus": "calibrated pressure reference (ICP range 0-40 mmHg), temperature chamber (33-41 C), simultaneous two-arm acquisition (no cross-run instrument drift confound), fouling deposition quantified (mass/QCM-class or equivalent) so exposure is recorded, not narrative",
        "simultaneous_acquisition_rule": "baseline and self-referencing arms are measured against the SAME reference at the SAME time in every stress arm (Art. XLVII)"
    },

    "primary_endpoint_preregistered": {
        "endpoint": "differential bridge output drift (mmHg-equivalent) per arm over the registered horizon, decomposed into common-mode and non-common-mode channels",
        "the_architectural_question": "does the self-referencing arm suppress NON-COMMON-MODE drift (the P-25 kill channel) or only common-mode drift (which the baseline can be trimmed for)?",
        "drift_target_modelled": {"value": 0.5, "unit": "mmHg/month", "class": "MODEL_DERIVED (the dossier's recorded drift target; EXTERNAL_PRECEDENT sourcing remains an open owner action)"},
        "ka014_kill_criterion_registered": {
            "rule": "KILL (route to repair) if the self-referencing arm's differential output drifts > 1 mmHg after the 4-week fouling exposure (arm 3) or the combined arm (arm 5) — the non-common-mode channel dominates; KA-014 recurs; repair requires a NON-common-mode compensation mechanism, else cemetery",
            "value": 1,
            "unit": "mmHg differential drift",
            "threshold_class": "MODEL_DERIVED (aligned with the P-25 precedent's 2.0 mmHg total-error class / 2 and the dossier's 1-2 mmHg accuracy target class; the R405-recorded proposal, registered under the R406 directive)",
            "provenance": "P-25 measured 3.45 mmHg over 30 days through exactly this channel (R337 falsification); the registered 1 mmHg over 4 weeks is the strict bound that catches the recurrence early",
            "uncertainty": "model-derived strict bound; the owner may relax to 2 mmHg (P-25 precedent total-error class) ONLY before the run, never after"
        },
        "common_mode_success_condition": {
            "rule": "the common-mode thermal claim is CONFIRMED only if arm 2 (clean) shows thermal zero/sensitivity error ratio vs the baseline arm >= the registered margin AND arm 4 retains >= half that margin under cycling",
            "margin_value": 3,
            "unit": "x baseline",
            "threshold_class": "MODEL_DERIVED (the P-25 precedent measured 67.8% common-mode cancellation in-model = ~3.1x vs uncancelled; the registered 3x requires the architecture to at least match the predecessor's measured cancellation)",
            "justification": "the bridge's reason to exist is the cancellation the predecessor actually demonstrated (67.8%) — this experiment must reproduce or beat it on hardware"
        },
        "recalibration_rule": {
            "rule": "periodic recalibration is NOT counted as a mechanism fix: any arm whose post-recalibration performance is used to satisfy a criterion is recorded as CALIBRATION-DEPENDENT, which FAILS the mechanism claim (the architecture must suppress drift autonomously; recalibration is a maintenance procedure, not a compensation mechanism)",
            "directive_basis": "R406 Step 8 verbatim: 'Periodic recalibration must not be counted as a mechanism fix'",
            "precedent": "the P-25 cemetery entry's own open boundary question — carried as a label, never demonstrated"
        }
    },

    "decision_rule": {
        "SUPPORTED": "ka014 criterion avoided (differential drift <= 1 mmHg in arms 3 AND 5) AND common-mode condition met (>= 3x cancellation vs baseline, retained >= 1.5x under cycling) -> SPONSORED_VALIDATION with the first PHYSICAL_OBSERVATION-class drift comparison attached",
        "KILLED": "ka014 criterion triggered (non-common-mode dominates) -> repair requires a non-common-mode compensation mechanism (per KA-014/DC-P-25-001), else cemetery",
        "ARCHITECTURAL_SELF_DEFEAT": "the reference element itself drifts comparably to the active element (falsifier channel c) -> the bridge references an equally unstable reference -> same path as KILLED",
        "INDETERMINATE": "proxy-transfer doubt dominant (accelerated fouling vs in-vivo biofouling) -> recorded exactly so"
    },

    "cost_and_time": {
        "cost_range": "$95-265K (REPORTED external-audit itemization: MEMS NRE $50-150K/mask set; engineering-sample wafer $20-50K; baseline comparator $20-50K; bench packaging $5-15K)",
        "cost_class": "ENGINEERING_ESTIMATE (REPORTED; 5-10x the other three packages — material to the commercial calculus, disclosed)",
        "time": "weeks-to-months (die procurement + 4-week fouling horizon dominate)"
    },
    "novelty_gate_note": "R406 Step 7 is a HARD GATE on this package: the specific novelty assessment (LEAD_PORTFOLIO_4/P13/NOVELTY_ASSESSMENT.json r406 extensions) must exist before large engineering spend; the experiment above is PROTOCOL-READY but spending the fab NRE before the novelty verdict is the exact inversion the directive forbids",
    "honest_limits": [
        "accelerated fouling is a proxy for in-vivo biofouling (the P-25 record itself marks this channel dominant — the proxy's transfer risk is the experiment's main caveat)",
        "bench horizon vs implant lifetime (acceleration assumptions must be declared, never silently equated)",
        "die/process family representativeness (the catheter-integrated MEMS process is unvalidated)",
        "zero physical measurement exists for ANY variant of this architecture — the predecessor's 3.45 mmHg record is in-model evidence, not hardware"
    ]
}


def main():
    # arithmetic self-checks on cross-referenced numbers
    assert P04["preregistered_thresholds"]["Q_min_pass_rule"]["value"] == 0.4
    assert P04["preregistered_thresholds"]["Q_min_kill_rule"]["value"] == 0.2
    assert abs((0.6 / 1.1) ** 4 - 0.0885) < 1e-3
    assert P04["preregistered_thresholds"]["false_pass_rule"]["leak_threshold_value"] == round(0.1 * 0.2, 2)
    assert P11["primary_endpoints_preregistered"]["endpoint_1_response_time"]["instrument_MDD"] == 0.0253
    assert P13["primary_endpoint_preregistered"]["common_mode_success_condition"]["margin_value"] == 3
    write("LEAD_PORTFOLIO_4/P04/EXPERIMENT_PREREGISTRATION.json", P04)
    write("LEAD_PORTFOLIO_4/P11/EXPERIMENT_PREREGISTRATION.json", P11)
    write("LEAD_PORTFOLIO_4/P13/EXPERIMENT_PREREGISTRATION.json", P13)
    print("all pre-registration self-checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

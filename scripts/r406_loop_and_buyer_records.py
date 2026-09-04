#!/usr/bin/env python3
"""R406 Steps 9, 10, 11, 12 records — per-package loop chains,
model-update ledgers, buyer evaluation states, killability assessments.

Step 10: LEAD_PORTFOLIO_4/Pnn/LOOP_CHAIN.json — the 14-state canonical
chain with machine-readable transition events; the derived state is
computed by discovery_fabric/engine/loop_chain.py (promotion past
PREDICTION is blocked while no REALITY_EVENT exists).

Step 11: LEAD_PORTFOLIO_4/Pnn/MODEL_UPDATE_LEDGER.json — the
model-vs-measurement records (prediction_before filled from the
pre-registrations; actual_measurement null until reality arrives ->
INSUFFICIENT_DATA, never promoted).

Step 9: LEAD_PORTFOLIO_4/Pnn/BUYER_EVALUATION_STATE.json — REAL_BUYER=0,
no fabricated interest.

Step 12: LEAD_PORTFOLIO_4/Pnn/KILLABILITY_ASSESSMENT.json — "could a
competent buyer kill this technology within one reasonably funded
experiment?" with the concrete money/time/apparatus/measurement/
threshold/decision path.
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from discovery_fabric.engine import loop_chain  # noqa: E402
from discovery_fabric.engine import model_measurement as mm  # noqa: E402


def write(rel, obj):
    out = os.path.join(REPO, rel)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(obj, f, indent=1, sort_keys=True)
    print(f"wrote {rel}")


# --- per-package chain events (every evidence_ref points at a committed artifact) ---
CHAINS = {
    "P04": {
        "events": [
            {"event_id": "r406-p04-ev01", "from_state": "DISCOVERY", "to_state": "EVIDENCE",
             "evidence_ref": "BENCHMARK_ENGINEERING_DOSSIERS/frozen_corpus_r370/04_drainage_floor/ (frozen dossier: 5 external evidence items)",
             "evidence_class": "EXTERNAL_PRECEDENT", "round": "R336/R370"},
            {"event_id": "r406-p04-ev02", "from_state": "EVIDENCE", "to_state": "MECHANISM",
             "evidence_ref": "frozen dossier mechanism: 4 governing equations, 10 design inputs, 5 failure modes (GEOMETRY_SEPARATION.json layers.scientific_concept)",
             "evidence_class": "AI_INFERENCE", "round": "R336"},
            {"event_id": "r406-p04-ev03", "from_state": "MECHANISM", "to_state": "ENGINEERING",
             "evidence_ref": "LEAD_PORTFOLIO_4/GEOMETRY_REVERIFICATION_EVIDENCE.json (independent G1-G9 re-execution on fresh rebuild, R404)",
             "evidence_class": "COMPUTATIONAL_RESULT", "round": "R381/R404"},
            {"event_id": "r406-p04-ev04", "from_state": "ENGINEERING", "to_state": "SIMULATION",
             "evidence_ref": "R396/P07_FAILURE_MODE_CONTRACT.json + R401/BASELINE_RUN_ARTIFACTS/envelope_PHYSICS.json (solve_network chain; unit-defect history disclosed, ratios proven unaffected)",
             "evidence_class": "COMPUTATIONAL_RESULT", "round": "R394-R401 (corrected R405)"},
            {"event_id": "r406-p04-ev05", "from_state": "SIMULATION", "to_state": "PREDICTION",
             "evidence_ref": "LEAD_PORTFOLIO_4/P04/EXPERIMENT_PREREGISTRATION.json (floor conductance 0.368 mL/(min*mmHg); G_ratio 0.0885; Q_min margins 12.7-18.4x)",
             "evidence_class": "COMPUTATIONAL_RESULT", "round": "R405/R406"},
        ],
        "legacy_loop_state": "NONE",
        "blockers": ["physical experiment not executed (protocol registered, cost $11-25K REPORTED)"],
    },
    "P08": {
        "events": [
            {"event_id": "r406-p08-ev01", "from_state": "DISCOVERY", "to_state": "EVIDENCE",
             "evidence_ref": "Jacques 2013 optical properties + the R370Q dossier evidence layer (ENERGY_BUDGET.json chain stage 2)",
             "evidence_class": "EXTERNAL_PRECEDENT", "round": "R309/R336"},
            {"event_id": "r406-p08-ev02", "from_state": "EVIDENCE", "to_state": "MECHANISM",
             "evidence_ref": "ENERGY_BUDGET.json chain (the 9-stage causal power-delivery model)",
             "evidence_class": "AI_INFERENCE", "round": "R308-R310"},
            {"event_id": "r406-p08-ev03", "from_state": "MECHANISM", "to_state": "ENGINEERING",
             "evidence_ref": "LEAD_PORTFOLIO_4/GEOMETRY_REVERIFICATION_EVIDENCE.json (receiver 38.4845 mm2 re-measured on fresh rebuild, R404)",
             "evidence_class": "COMPUTATIONAL_RESULT", "round": "R381/R404"},
            {"event_id": "r406-p08-ev04", "from_state": "ENGINEERING", "to_state": "SIMULATION",
             "evidence_ref": "LEAD_PORTFOLIO_4/P08/VERIFICATION_EVIDENCE/ (R310/R311/R312 restored anchors) + R406/P08_ENERGY_PIPELINE/PIPELINE_RUN.json (independent MC, seed 20260904, reproducibility contest recorded)",
             "evidence_class": "COMPUTATIONAL_RESULT", "round": "R310-R312 + R406"},
            {"event_id": "r406-p08-ev05", "from_state": "SIMULATION", "to_state": "PREDICTION",
             "evidence_ref": "ENERGY_BUDGET.json canonical conditional band 121-163 uW (anchor basis) with the R406 independent-run 81 uW GaAs-conditional basis recorded as a contest",
             "evidence_class": "MODELLED", "round": "R404-R406"},
        ],
        "legacy_loop_state": "NONE",
        "blockers": ["physical experiment not executed (phantom-path bench protocol specified)", "D2 engineering decision owner-gated", "fluence reproducibility contest open (anchor band vs independent run)"],
    },
    "P11": {
        "events": [
            {"event_id": "r406-p11-ev01", "from_state": "DISCOVERY", "to_state": "EVIDENCE",
             "evidence_ref": "R339/g2_p24_buyer_package/P-24_BUYER_PACKAGE.json + the frozen corpus evidence layer",
             "evidence_class": "EXTERNAL_PRECEDENT", "round": "R336/R339"},
            {"event_id": "r406-p11-ev02", "from_state": "EVIDENCE", "to_state": "MECHANISM",
             "evidence_ref": "LEAD_PORTFOLIO_4/P11/DIFFERENTIATION_AND_CAUSAL_CHAIN.json (tau = I_h/c_h first-order model; 2 unestablished differentiators promoted to endpoints)",
             "evidence_class": "AI_INFERENCE", "round": "R339"},
            {"event_id": "r406-p11-ev03", "from_state": "MECHANISM", "to_state": "ENGINEERING",
             "evidence_ref": "LEAD_PORTFOLIO_4/GEOMETRY_REVERIFICATION_EVIDENCE.json (damper gap 0.18 mm KEEP re-verified, R404)",
             "evidence_class": "COMPUTATIONAL_RESULT", "round": "R381/R404"},
            {"event_id": "r406-p11-ev04", "from_state": "ENGINEERING", "to_state": "SIMULATION",
             "evidence_ref": "R339 synthetic loop + INSTRUMENT_MDD_CALCULATION.json (0.4 s vs 0.5 s settling model; MDD 0.0253 s)",
             "evidence_class": "COMPUTATIONAL_RESULT", "round": "R339/R405"},
            {"event_id": "r406-p11-ev05", "from_state": "SIMULATION", "to_state": "PREDICTION",
             "evidence_ref": "LEAD_PORTFOLIO_4/P11/EXPERIMENT_PREREGISTRATION.json (kill conditions A/B registered; settling predictions 0.4/0.5 s)",
             "evidence_class": "MODELLED", "round": "R406"},
        ],
        "legacy_loop_state": "SYNTHETIC_LOOP_VERIFIED (R339; synthetic observations only — never physical; the R406 chain records it as legacy, the derived state does not inherit it)",
        "blockers": ["bench experiment not executed ($15K/8wk RECORDED protocol)"],
    },
    "P13": {
        "events": [
            {"event_id": "r406-p13-ev01", "from_state": "DISCOVERY", "to_state": "EVIDENCE",
             "evidence_ref": "R336 DISCOVERY_ENGINE_RESULT.json (CAND-002 admission attacks) + the R370Q consultant competitive findings",
             "evidence_class": "EXTERNAL_PRECEDENT", "round": "R336"},
            {"event_id": "r406-p13-ev02", "from_state": "EVIDENCE", "to_state": "MECHANISM",
             "evidence_ref": "LEAD_PORTFOLIO_4/P13/LINEAGE_AUDIT.json (self-referencing dual-element bridge; common-mode cancellation with the non-common-mode channel)",
             "evidence_class": "AI_INFERENCE", "round": "R336/R404"},
            {"event_id": "r406-p13-ev03", "from_state": "MECHANISM", "to_state": "ENGINEERING",
             "evidence_ref": "LEAD_PORTFOLIO_4/GEOMETRY_REVERIFICATION_EVIDENCE.json (diaphragm 0.07 mm KEEP re-verified, R404)",
             "evidence_class": "COMPUTATIONAL_RESULT", "round": "R381/R404"},
            {"event_id": "r406-p13-ev04", "from_state": "ENGINEERING", "to_state": "SIMULATION",
             "evidence_ref": "predecessor P-25 in-model falsification (R337: 67.8% common-mode cancellation, 3.45 mmHg residual — the family's only quantitative model evidence) + the MODEL_DERIVED drift target 0.5 mmHg/month",
             "evidence_class": "COMPUTATIONAL_RESULT", "round": "R337 (predecessor; zero hardware measurement exists for any variant)"},
            {"event_id": "r406-p13-ev05", "from_state": "SIMULATION", "to_state": "PREDICTION",
             "evidence_ref": "LEAD_PORTFOLIO_4/P13/EXPERIMENT_PREREGISTRATION.json (KA-014 kill criterion 1 mmHg; common-mode margin 3x) + LEAD_PORTFOLIO_4/P13/NOVELTY_SEARCH_R406/NOVELTY_SEARCH_RESULT.json (novelty CONTESTED)",
             "evidence_class": "MODELLED", "round": "R406"},
        ],
        "legacy_loop_state": "NONE",
        "blockers": ["novelty hard gate: verdict CONTESTED — engineering spend gated pending claim-differentiation review of PA-1 (Seaver 2018 dual-die dissertation) / PA-2 (US4320664)", "physical experiment not executed (5-arm protocol registered, $95-265K REPORTED)", "re-admission waiver for the P-25 cemetery lineage still open"],
    },
}

PREDICTIONS = {
    "P04": [
        {"metric": "floor-lumen segment conductance at measured viscosity (canonical 0.6 mm)",
         "prediction_before": 0.368069, "unit": "mL/(min*mmHg)",
         "source": "LEAD_PORTFOLIO_4/P04/QMIN_FLOOR_FLOW_CALCULATION.json"},
        {"metric": "G_floor/G_primary split (Poiseuille validity)",
         "prediction_before": 0.0885, "unit": "dimensionless",
         "source": "LEAD_PORTFOLIO_4/P04/EXPERIMENT_PREREGISTRATION.json"},
    ],
    "P08": [
        {"metric": "detector-plane fluence (anchor basis)", "prediction_before": 1.049054,
         "unit": "mW/cm^2", "source": "LEAD_PORTFOLIO_4/P08/VERIFICATION_EVIDENCE/R310/"},
        {"metric": "detector-plane fluence (R406 independent MC basis)", "prediction_before": 0.705,
         "unit": "mW/cm^2", "source": "R406/P08_ENERGY_PIPELINE/PIPELINE_RUN.json"},
        {"metric": "conditional electrical power (GaAs 0.30 assumption, anchor basis)",
         "prediction_before": 121.0, "unit": "uW", "source": "ENERGY_BUDGET.json"},
    ],
    "P11": [
        {"metric": "damper settling time", "prediction_before": 0.4, "unit": "s",
         "source": "INSTRUMENT_MDD_CALCULATION.json (tau = I_h/c_h model)"},
        {"metric": "ASD settling time (comparator class)", "prediction_before": 0.5, "unit": "s",
         "source": "INSTRUMENT_MDD_CALCULATION.json"},
    ],
    "P13": [
        {"metric": "self-referencing differential drift over 4-week fouling (the KA-014 channel)",
         "prediction_before": None, "unit": "mmHg",
         "source": "UNPREDICTED at the architecture level — the predecessor's measured 3.45 mmHg/30d is the only in-family datapoint (in-model, not hardware); the honest prediction_before is UNKNOWN until a paired-die hardware arm exists"},
        {"metric": "common-mode cancellation vs baseline", "prediction_before": 3.1, "unit": "x (cancellation ratio)",
         "source": "P-25 in-model precedent 67.8% (~3.1x) — MODEL_DERIVED"},
    ],
}

KILLABILITY = {
    "P04": {
        "question": "Could a competent buyer kill this technology within one reasonably funded experiment?",
        "answer": "YES — KILLABLE_IN_ONE_FUNDED_EXPERIMENT",
        "money": "$11-25K (REPORTED itemization; owner confirmation outstanding)",
        "time": "~8 weeks (sibling protocol class)",
        "apparatus": "bench hydrostatic/column flow loop + obstruction fixtures + isolated floor-port flow sensor",
        "measurement": "residual floor flow per lumen after primary-only / floor-only / common-cause obstruction vs the single-lumen control, across 10/20/40 mmHg",
        "threshold": "KILL: common-cause occlusion >= 90% of cases OR residual floor flow < 0.2 mL/min at all heads (pre-registered, EXPERIMENT_PREREGISTRATION.json)",
        "decision": "ACCEPT / KILL / INDETERMINATE per the registered decision rule; KILL routes to the mechanism cemetery with the kill class (Art. LI)",
        "kill_path_quality": "the experiment tests the package's OWN recorded critical kill condition — a genuine falsification contract (Art. LII), not a confirmation ritual",
    },
    "P08": {
        "question": "Could a competent buyer kill this technology within one reasonably funded experiment?",
        "answer": "YES — KILLABLE_IN_ONE_FUNDED_EXPERIMENT (the physics-chain experiment; the D2 target decision is separate and is a decision, not an experiment)",
        "money": "$16-42K (REPORTED context; the decisive-experiment cost basis UNESTIMATED owner input)",
        "time": "weeks-class (phantom-path bench + thermal envelope)",
        "apparatus": "tissue-equivalent phantom path + source + calibrated detector + thermal instrumentation",
        "measurement": "measured detector-plane fluence and PV output vs the recorded band, plus surface irradiance vs the applicable exposure limit",
        "threshold": "KILL: measured fluence materially outside both the anchor band (1.0-1.4 mW/cm^2) and the independent-run basis (0.705) — i.e. the power-delivery premise (uW-scale power at implant-safe irradiance on the shipped receiver area) collapses; the thermal boundary (ANSI/IEC MPE) is a second kill channel (owner-extracted numbers required)",
        "decision": "the falsifier in DECISIVE_EXPERIMENT.json: measured power inside the recorded band CONFIRMS the chain and relocates the D2 gap to a target/area decision; power outside the viable band KILLS the premise",
        "kill_path_quality": "decisive and now MORE informative: the anchor-vs-independent-run 40% contest means the measurement arbitrates two live quantitative bases (R406 pipeline finding)",
    },
    "P11": {
        "question": "Could a competent buyer kill this technology within one reasonably funded experiment?",
        "answer": "YES — KILLABLE_IN_ONE_FUNDED_EXPERIMENT (the cleanest of the four: the only RECORDED cost)",
        "money": "$15K (RECORDED, R339) with the $15-38K REPORTED range as context",
        "time": "8 weeks (RECORDED)",
        "apparatus": "mock CSF loop, 3 arms (damper / REAL ASD / standard), postural-step actuation, blinded analysis harness",
        "measurement": "settling time to 10% band + proportional modulation error, per pressure, n=10 runs/arm",
        "threshold": "KILL: condition A (not >= 20% faster than ASD at all four pressures, unless endpoint 2 decisively positive) OR condition B (target-flow accuracy statistically worse than ASD at any pressure) — both pre-registered",
        "decision": "SUPPORTED / KILLED / MIXED per the registered rule with the pre-registered SAP (Wilcoxon signed-rank, alpha 0.05, no peeking)",
        "kill_path_quality": "registered falsification contract with the MDD already computed (0.0253 s resolves the claimed 0.1 s difference at 3.95x margin)",
    },
    "P13": {
        "question": "Could a competent buyer kill this technology within one reasonably funded experiment?",
        "answer": "QUALIFIED — two kill paths: the CHEAP one is live NOW (novelty: the CONTESTED verdict — a claim-differentiation review against Seaver 2018 / US4320664 costs days, not dollars), the EXPENSIVE one (the 5-arm bench) is registered but $95-265K (5-10x the others) and gated behind the novelty review",
        "money": "novelty path: patent-counsel review class; bench path: $95-265K (REPORTED, 5-10x disclosure)",
        "time": "novelty path: days-weeks; bench path: weeks-to-months (4-week fouling horizon)",
        "apparatus": "novelty path: claim charts; bench path: paired-die arms + pressure reference + thermal chamber + BSA fouling protocol",
        "measurement": "novelty path: element-by-element claim mapping vs PA-1/PA-2; bench path: differential drift per arm (baseline / self-ref / fouling / thermal / combined)",
        "threshold": "novelty path: the architecture's elements fully disclosed by located art -> the differentiation space collapses; bench path: KILL at differential drift > 1 mmHg after fouling (KA-014) or reference-element self-defeat",
        "decision": "novelty first (the R406 hard gate), then the bench kill experiment only if the differentiation space survives counsel review",
        "kill_path_quality": "the package is killable CHEAPLY first (novelty) and EXPENSIVELY second (physics) — both paths are concretely specified; the predecessor's measured failure channel is built directly into the bench protocol",
    },
}


def main():
    for pkg, spec in CHAINS.items():
        events = spec["events"]
        derived = loop_chain.derive_loop_state(events)
        chain_rec = {
            "artifact_type": "LOOP_CHAIN",
            "company_designation": pkg,
            "directive_basis": "R406 Step 10: the canonical chain with machine-readable transition events; absence of physical data prevents promotion",
            "canonical_chain": loop_chain.LOOP_STATES,
            "events": events,
            "derived": derived,
            "legacy_loop_state_art_xxxvii": spec["legacy_loop_state"],
            "promotion_rule": "the derived state is computed by discovery_fabric/engine/loop_chain.py from the events alone; no narrative assignment; transitions at or beyond PHYSICAL_EXPERIMENT require a valid REALITY_EVENT (Art. XXXVIII) — with none present the chain is capped at PREDICTION with promotion_blocked_reason NO_PHYSICAL_DATA",
            "open_blockers": spec["blockers"],
            "how_to_advance": "execute the registered experiment (see EXPERIMENT_PREREGISTRATION.json / DECISIVE_EXPERIMENT.json), deliver the raw data through the reality-boundary interface (REALITY_EVENT with custody chain + attestation), then the OBSERVATION -> MODEL_UPDATE transitions unlock through the model-vs-measurement ledger",
        }
        assert derived["current_state"] == "PREDICTION", (pkg, derived)
        assert derived["promotion_blocked_reason"] == "NO_PHYSICAL_DATA", (pkg, derived)
        write(f"LEAD_PORTFOLIO_4/{pkg}/LOOP_CHAIN.json", chain_rec)

        # Step 11 ledger
        records = []
        for pred in PREDICTIONS[pkg]:
            rec = mm.build_update_record(
                prediction_before=pred["prediction_before"],
                actual_measurement=None,
                model_update=None,
                prediction_after=None,
                error_before=None,
                error_after=None,
                held_out_error=None,
                reality_event=None,
                unit=pred["unit"],
                notes=[f"metric: {pred['metric']}", f"source: {pred['source']}"],
            )
            records.append(rec)
        ledger = {
            "artifact_type": "MODEL_UPDATE_LEDGER",
            "company_designation": pkg,
            "directive_basis": "R406 Step 11: prediction_before / actual_measurement / error_before / model_update / prediction_after / error_after / held_out_error for every physical experiment; prove whether the model improved",
            "records": records,
            "summary": mm.verdict_for_ledger(records),
            "state": "AWAITING_PHYSICAL_OBSERVATION — every field is present; actual_measurement is null until a REALITY_EVENT arrives; INSUFFICIENT_DATA is the honest state and can never be promoted (Art. XXV)",
            "armed_fields": list(mm._REQUIRED_FIELDS),
        }
        assert ledger["summary"]["counts"]["INSUFFICIENT_DATA"] == len(records)
        write(f"LEAD_PORTFOLIO_4/{pkg}/MODEL_UPDATE_LEDGER.json", ledger)

        # Step 9 buyer state
        buyer = {
            "artifact_type": "BUYER_EVALUATION_STATE",
            "company_designation": pkg,
            "directive_basis": "R406 Step 9: buyer / contact / date / material received / technical response / requested follow-up / NDA state / experiment interest / commercial interest — do not fabricate buyer interest",
            "buyer": None,
            "contact": None,
            "date_of_engagement": None,
            "material_received": "the buyer-distribution repository release exists (Art. XXXIX chain of custody); no engagement with any recipient is recorded",
            "technical_response": "NONE",
            "requested_follow_up": "NONE",
            "nda_state": "NONE",
            "experiment_interest": "NONE",
            "commercial_interest": "NONE",
            "REAL_BUYER": 0,
            "fabrication_guard": "every engagement field above is NONE/null because zero engagement evidence exists in the repository; any non-null value requires a recorded engagement event (this file's fields update only through such events)",
        }
        write(f"LEAD_PORTFOLIO_4/{pkg}/BUYER_EVALUATION_STATE.json", buyer)

        # Step 12 killability
        k = dict(KILLABILITY[pkg])
        k.update({
            "artifact_type": "KILLABILITY_ASSESSMENT",
            "company_designation": pkg,
            "directive_basis": "R406 Step 12: 'Could a competent buyer kill this technology within one reasonably funded experiment?' If the answer is no, the package is not ready.",
        })
        write(f"LEAD_PORTFOLIO_4/{pkg}/KILLABILITY_ASSESSMENT.json", k)

    print("all chains derived: PREDICTION, blocked NO_PHYSICAL_DATA — as required")
    return 0


if __name__ == "__main__":
    sys.exit(main())

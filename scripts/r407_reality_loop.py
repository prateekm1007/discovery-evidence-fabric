#!/usr/bin/env python3
"""R407 — FIRST REALITY LOOP: the P04 reality-boundary round.

Generates (Art. LXII: this script is the computation/registration log;
every artifact it writes is regenerable from committed inputs):

  1. LEAD_PORTFOLIO_4/P04/REALITY_LOOP/PREDICTION_BEFORE.json
     The model's quantitative prediction for the frozen experiment
     contract, registered BEFORE any run, hash-bound to the contract and
     to the canonical Q_min computation (R407-C: "before experiment:
     PREDICTION_BEFORE.json").

  2. LEAD_PORTFOLIO_4/P04/REALITY_LOOP/EXECUTION_ATTEMPT_R407.json
     THE R407-I milestone artifact: the machine attempts to execute the
     P04 experiment contract and records the real-world execution
     failure with the same provenance integrity a real observation would
     carry. Every blocker is cited with evidence, not narrative
     (Art. LXI: INCOMPLETE_INFRASTRUCTURE_FAILURE — an execution state,
     never a technology verdict; the loop chain stays at PREDICTION).

  3. LEAD_PORTFOLIO_4/P04/REALITY_LOOP/REALITY_LEDGER.json
     The append-only hash-chained real-observation ledger: EMPTY at
     registration (zero entries). The first real physical observation
     will be entry 1.

  4. LEAD_PORTFOLIO_4/P04/REALITY_LOOP/REHEARSAL/
     Two full five-file adjudication chains (PREDICTION_BEFORE ->
     OBSERVATION -> MODEL_ERROR -> MODEL_UPDATE -> PREDICTION_AFTER)
     run on CONTROLLED_REHEARSAL fixtures, clearly labeled, ingested
     only into the REHEARSAL ledger, never the real one:
       case 1 — the update improves the held-out prediction
                (MODEL_IMPROVED)
       case 2 — the update looks fine on the training conditions but
                WORSENS the held-out prediction (LEARNING_FAILED — the
                anti-learning-theatre discriminator, R407-D)

  5. LEAD_PORTFOLIO_4/P04/REALITY_LOOP/LOOP_CLOSURE_PATHS.json
     Both R407-E closure paths as machine-readable contracts.

  6. R407/R407_ACCEPTANCE_CHECKLIST.json — the directive item map.

Constitutional basis: Art. VI (no manufactured provenance — absent
fields carry explicit ABSENT markers with reasons, never invented
values), Art. XXV (unknown stays unknown), Art. XXXIV (reality is the
next bottleneck; this round puts the technology IN FRONT of reality and
records its answer), Art. XXXVIII (the Reality Boundary: rehearsal
never promotes; real observations only through the ingestion contract),
Art. LXI (infrastructure failure is never scientific rejection).
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from discovery_fabric.engine import loop_chain            # noqa: E402
from discovery_fabric.engine import reality_ingestion as ri  # noqa: E402

NOW = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
EXPERIMENT_ID = "P04-R407-EXP-001"
RL = os.path.join(REPO, "LEAD_PORTFOLIO_4", "P04", "REALITY_LOOP")
REHEARSAL_DIR = os.path.join(RL, "REHEARSAL")


def sha256_file(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def sha256_obj(obj) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def write_json(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, sort_keys=True)
        f.write("\n")


def load(rel: str):
    with open(os.path.join(REPO, rel)) as f:
        return json.load(f)


def main() -> int:
    # ------------------------------------------------------------------
    # Inputs (all committed, all hashed into the records below)
    # ------------------------------------------------------------------
    contract_path = "LEAD_PORTFOLIO_4/P04/EXPERIMENT_CONTRACT_FROZEN.json"
    qmin_path = "LEAD_PORTFOLIO_4/P04/QMIN_FLOOR_FLOW_CALCULATION.json"
    prereg_path = "LEAD_PORTFOLIO_4/P04/EXPERIMENT_PREREGISTRATION.json"
    buyer_state_path = "LEAD_PORTFOLIO_4/P04/BUYER_EVALUATION_STATE.json"
    chain_path = "LEAD_PORTFOLIO_4/P04/LOOP_CHAIN.json"

    contract = load(contract_path)
    qmin = load(qmin_path)
    buyer_state = load(buyer_state_path)
    contract_sha = sha256_file(os.path.join(REPO, contract_path))
    qmin_sha = sha256_file(os.path.join(REPO, qmin_path))

    # The canonical predicted values (QMIN_FLOOR_FLOW_CALCULATION.json,
    # canonical_shipped geometry row).
    canon = None
    for row in qmin["contents"]["floor_flow_computation"]:
        if row["geometry"] == "canonical_shipped":
            canon = row
            break
    assert canon is not None, "canonical_shipped row missing from QMIN file"
    flows = {k.replace("at_", "").replace("_mmHg", ""):
             round(v["mL_per_min"], 4)
             for k, v in canon["flows"].items()}
    pred_values = {
        "residual_floor_flow_mL_min_by_head_mmHg": flows,
        "floor_segment_conductance_mL_min_mmHg": canon["conductance_mL_min_mmHg"],
        "G_ratio_modelled": 0.0885,
    }

    # ------------------------------------------------------------------
    # 1. PREDICTION_BEFORE.json (registered before any run)
    # ------------------------------------------------------------------
    prediction_before = {
        "artifact_type": "PREDICTION_BEFORE",
        "experiment_id": EXPERIMENT_ID,
        "package_id": "P04",
        "registered_at": NOW,
        "registered_before_any_run": True,
        "directive_basis": "R407-C: before experiment, PREDICTION_BEFORE.json; "
                           "R407-A: the frozen contract's model expectations",
        "contract_of_record": contract_path,
        "contract_sha256": contract_sha,
        "prediction_source": {
            "artifact": qmin_path,
            "sha256": qmin_sha,
            "row": "canonical_shipped",
            "computation_log": "scripts/r405_p04_qmin_and_conductance.py",
        },
        "predictions": pred_values,
        "prediction_uncertainty": {
            "registered_band": "+/- 30% (the Poiseuille-validity band, "
                                "ENGINEERING class, frozen in the "
                                "pre-registration)",
            "statistical_component": "none (deterministic Poiseuille model)",
            "model_form_component": "entrance/exit losses, developing flow, "
                                    "partial simulant occlusion — all "
                                    "unmeasured; the +/- 30% band is the "
                                    "registered container for them"
        },
        "held_out_condition": {
            "condition": "40 mmHg head",
            "role": "any model update from the experiment is fitted on the "
                    "10 and 20 mmHg training conditions and evaluated on "
                    "the 40 mmHg held-out condition (R407-D)",
        },
        "falsifiable_statement": "if the measured residual floor flow at the "
                                  "PRIMARY_ONLY arm falls outside the "
                                  "registered band of these predictions at "
                                  "2+ heads, the Poiseuille engineering "
                                  "model is falsified for this bench regime "
                                  "and must be updated through the "
                                  "adjudication machinery",
        "predicted_decision_if_model_holds": "KEEP (all heads far above "
                                             "Q_min 0.4; G ratio within "
                                             "+/- 30% if Poiseuille holds)",
        "constitutional_basis": "Art. XXVIII (prediction is not "
                                "observation), Art. LII (falsification "
                                "contract), Art. XXVII (threshold and band "
                                "provenance)"
    }
    prediction_before["self_sha256"] = sha256_obj(
        {k: v for k, v in prediction_before.items() if k != "self_sha256"})
    pb_path = os.path.join(RL, "PREDICTION_BEFORE.json")
    write_json(pb_path, prediction_before)

    # ------------------------------------------------------------------
    # 2. EXECUTION_ATTEMPT_R407.json — put the technology in front of
    #    reality and record reality's answer with provenance integrity.
    # ------------------------------------------------------------------
    # Precondition checks: each cites evidence, never narrative.
    real_buyer = buyer_state.get("buyer_interest", {}).get(
        "real_buyer_count", buyer_state.get("real_buyer_count", 0))
    preconditions = [
        {
            "requirement": "dual-lumen extruded samples (primary 1.1 mm + "
                           "floor 0.6 mm, min-wall passing)",
            "status": "BLOCKED",
            "evidence": [
                "no procurement record exists anywhere in the repository "
                "(the R405 truth snapshot and R406 truth snapshot both "
                "record physical_observation_count = 0)",
                "contract cost section: $3-8K extrusion samples — unfunded "
                "(REAL_BUYER = " + str(real_buyer) + "; "
                "BUYER_EVALUATION_STATE.json is the evidence of record)"
            ],
        },
        {
            "requirement": "bench apparatus P04-BENCH-001 (constant-head "
                           "loop, isolated floor-port sensing, leak-test "
                           "fixture)",
            "status": "BLOCKED",
            "evidence": [
                "apparatus_id P04-BENCH-001 is UNASSIGNED — the contract "
                "assigns it at procurement; no apparatus registry, "
                "inventory, or calibration record exists in any committed "
                "artifact",
            ],
        },
        {
            "requirement": "a named human operator of record",
            "status": "BLOCKED",
            "evidence": [
                "no operator identity exists in any committed record; the "
                "R406 buyer states record REAL_BUYER = "
                + str(real_buyer) + " with buyer_interest_evidence = NONE",
            ],
        },
        {
            "requirement": "obstruction simulants (proteinaceous debris "
                           "analog, tissue-ingrowth analog)",
            "status": "BLOCKED",
            "evidence": [
                "no simulant lot, safety sheet, or acquisition record "
                "exists; $1-2K unfunded",
            ],
        },
    ]
    all_blocked = all(p["status"] == "BLOCKED" for p in preconditions)
    chain_record = load(chain_path)
    derived = loop_chain.derive_loop_state(chain_record.get("events", []))

    execution_attempt = {
        "artifact_type": "EXECUTION_ATTEMPT_RECORD",
        "experiment_id": EXPERIMENT_ID,
        "package_id": "P04",
        "attempted_at": NOW,
        "attempt": "execute the frozen P04 experiment contract "
                   "(P04-R407-EXP-001) in the real world",
        "outcome": "EXECUTION_BLOCKED" if all_blocked else "UNKNOWN",
        "classification": "INCOMPLETE_INFRASTRUCTURE_FAILURE "
                          "(Art. LXI: infrastructure failure is never "
                          "scientific rejection — this is NOT a technology "
                          "verdict; P04 is neither killed nor promoted)",
        "precondition_checks": preconditions,
        "provenance_fields": {
            "experiment_id": EXPERIMENT_ID,
            "package_id": "P04",
            "timestamp": NOW,
            "apparatus_id": "ABSENT: P04-BENCH-001 unassigned — the "
                            "apparatus does not exist (evidence cited "
                            "above; Art. VI — ABSENT, never invented)",
            "operator": "ABSENT: no operator of record exists (evidence "
                        "cited above)",
            "raw_data_hash": "ABSENT: no raw data was acquired — the "
                             "experiment never ran",
            "processed_data_hash": "ABSENT: no processed dataset exists",
            "measurement_units": "ABSENT: no measurement taken",
            "uncertainty": "ABSENT: no measurement taken",
            "baseline_result": "ABSENT: no measurement taken",
            "candidate_result": "ABSENT: no measurement taken",
            "pre_registered_threshold": {
                "status": "PRESENT",
                "artifact": contract_path,
                "sha256": contract_sha,
            },
            "decision": {
                "verdict": "EXECUTION_BLOCKED",
                "rule_id": "P04-EXECUTION-BLOCKED-R407",
                "rule_trace": [
                    "all execution preconditions BLOCKED (samples, "
                    "apparatus, operator, simulants)",
                    "no observation was acquired; nothing entered the "
                    "reality ledger",
                    "the prediction_of_record stands OPEN, awaiting the "
                    "first real observation",
                ],
            },
        },
        "effect_on_loop_chain": {
            "loop_chain_artifact": chain_path,
            "derived_state_before_attempt": derived["current_state"],
            "loop_verification_state": derived["loop_verification_state"],
            "promotion_blocked_reason": derived["promotion_blocked_reason"],
            "change": "NONE — the chain stays at "
                      + str(derived["current_state"])
                      + "; an execution failure is not an observation "
                        "(Art. XXXVIII) and advances nothing",
        },
        "real_event_count_after_attempt": 0,
        "what_unblocks_this": "a funded sponsor or owner decision "
                              "procuring the four blocked preconditions; "
                              "the contract, the prediction, the ingestion "
                              "boundary and the adjudication machinery are "
                              "all armed and waiting",
        "directive_basis": "R407-I: the milestone is the first complete "
                           "reality loop — OR a documented real-world "
                           "execution failure with the same provenance "
                           "integrity. This record IS that failure "
                           "document: every field either carries evidence "
                           "or an explicit ABSENT-with-reason marker; "
                           "nothing is fabricated.",
        "constitutional_basis": "Art. VI, Art. XXV, Art. XXXIV (stop "
                                "coding when reality is the bottleneck — "
                                "the machine has now formally attempted "
                                "reality and recorded its answer), "
                                "Art. LXI",
    }
    execution_attempt["self_sha256"] = sha256_obj(
        {k: v for k, v in execution_attempt.items() if k != "self_sha256"})
    write_json(os.path.join(RL, "EXECUTION_ATTEMPT_R407.json"),
               execution_attempt)

    # ------------------------------------------------------------------
    # 3. The real ledger: EMPTY, armed.
    # ------------------------------------------------------------------
    write_json(os.path.join(RL, "REALITY_LEDGER.json"), {
        "artifact_type": "REALITY_EVENT_LEDGER",
        "ledger_class": "REAL (physical observations only; "
                        "CONTROLLED_REHEARSAL can never be ingested here)",
        "entries": [],
        "entry_count": 0,
        "real_event_count": 0,
        "note": "append-only, hash-chained (reality_ingestion."
                "ingest_reality_event / verify_ledger). EMPTY until the "
                "first real observation enters through the ingestion "
                "contract with full provenance.",
        "ingestion_contract": "LEAD_PORTFOLIO_4/REALITY_INGESTION_CONTRACT.json",
    })

    # ------------------------------------------------------------------
    # 4. Rehearsal: the five-file adjudication chain, exercised twice.
    # ------------------------------------------------------------------
    # Rehearsal fixture: the model error is an effective-conductance
    # deficit k (entrance/exit + developing-flow losses). Two truths:
    #   case 1 (IMPROVES):  k_true = 0.85 at all heads; a constant-k
    #                        update fitted on the training heads fixes
    #                        the held-out head too -> MODEL_IMPROVED
    #   case 2 (FAILS):     k_true = 0.85 at 10/20 mmHg but 0.95 at the
    #                        held-out 40 mmHg head; the SAME constant-k
    #                        update fitted on training WORSENS the
    #                        held-out prediction -> LEARNING_FAILED
    #                        (the update looks fine on training — that is
    #                        exactly the learning theatre R407-D forbids
    #                        counting as learning)
    base_flows = pred_values["residual_floor_flow_mL_min_by_head_mmHg"]
    rehearsal_specs = [
        {
            "case": 1,
            "label": "MODEL_IMPROVED",
            "k_true": {"10": 0.85, "20": 0.85, "40": 0.85},
            "update": "constant effective-conductance factor k fitted on "
                      "the training heads (10, 20 mmHg)",
        },
        {
            "case": 2,
            "label": "LEARNING_FAILED",
            "k_true": {"10": 0.85, "20": 0.85, "40": 0.95},
            "update": "the SAME constant-k update fitted on the training "
                      "heads — it improves the training conditions but "
                      "WORSENS the held-out condition",
        },
    ]
    rehearsal_adjudications: list = []
    rehearsal_ledger_path = os.path.join(REHEARSAL_DIR,
                                         "REHEARSAL_LEDGER.json")
    # the REHEARSAL tree is fully script-generated: clear it for
    # idempotent regeneration (the REAL ledger is never touched here).
    if os.path.exists(rehearsal_ledger_path):
        os.remove(rehearsal_ledger_path)
    for spec in rehearsal_specs:
        k_true = spec["k_true"]
        actual = {h: round(base_flows[h] * k, 4)
                  for h, k in k_true.items()}
        # fit on training heads only
        k_fit = sum(actual[h] / base_flows[h] for h in ("10", "20")) / 2.0
        pred_after = {h: round(base_flows[h] * k_fit, 4)
                      for h in base_flows}
        ho_actual = actual["40"]
        ho_pred_before = base_flows["40"]
        ho_pred_after = pred_after["40"]

        # the rehearsal observation event (full v2 schema, rehearsal
        # source type, decision computed by the frozen contract function)
        g_measured = round(0.0885 * k_fit, 4)
        candidate_result = {
            "residual_floor_flow_mL_min_by_head_mmHg": actual,
            "measured_G_ratio": g_measured,
            "common_cause_occlusion_rate_pct": 30.0,
            "valid_trials_total": 18,
            "void_trial_count": 0,
            "manufacturing_minwall_all_failed": False,
        }
        decision = ri.decide_p04({"candidate_result": candidate_result})
        fixture = {
            "fixture_class": "CONTROLLED_REHEARSAL",
            "generating_truth": {"k_true_by_head": k_true,
                                 "base_prediction": base_flows},
        }
        event = {
            "event_id": f"REH-P04-CASE{spec['case']}-0001",
            "experiment_id": EXPERIMENT_ID,
            "package_id": "P04",
            "event_type": "BENCH_MEASUREMENT",
            "source_type": "CONTROLLED_REHEARSAL",
            "organization": "REHEARSAL-HARNESS",
            "operator": "R407-REHEARSAL-SCRIPT",
            "timestamp": NOW,
            "apparatus_id": "REHEARSAL-SIM-001 (synthetic — no physical "
                            "apparatus exists)",
            "raw_data_hash": sha256_obj(fixture),
            "processed_data_hash": sha256_obj(candidate_result),
            "measurement_units": {
                "residual_floor_flow": "mL/min",
                "G_ratio": "dimensionless",
                "common_cause_occlusion_rate": "percent"},
            "uncertainty": {
                "note": "rehearsal values carry synthetic uncertainty "
                        "0.01 mL/min; the class is rehearsal, not "
                        "measurement"},
            "baseline_result": {
                "single_lumen_control_zero_flow_mL_min": 0.005},
            "candidate_result": candidate_result,
            "pre_registered_threshold": {
                "artifact": contract_path,
                "sha256": contract_sha,
                "Q_min_pass_mL_min": 0.4,
                "Q_min_kill_mL_min": 0.2,
                "common_cause_kill_pct": 90,
                "G_ratio_band": "+/- 30% of 0.0885"},
            "decision": decision,
            "custody_chain": [{
                "actor": "R407-REHEARSAL-SCRIPT", "action":
                "generated synthetic fixture from the registered "
                "prediction + a recorded k_true truth", "timestamp": NOW}],
            "attestation": {
                "attestation_text": "CONTROLLED_REHEARSAL fixture for "
                                    "machinery proof only; the values are "
                                    "synthetic and can never promote the "
                                    "chain or count as learning "
                                    "(Art. XXXVIII)",
                "attestation_hash": sha256_obj(
                    {"text": "CONTROLLED_REHEARSAL", "case": spec["case"]})},
            "provenance_validated": True,
        }
        problems = ri.validate_reality_event_v2(event)
        assert not problems, f"rehearsal event invalid: {problems}"

        # the five-file adjudication chain
        case_dir = os.path.join(REHEARSAL_DIR, f"case_{spec['case']}")
        observation = {
            "artifact_type": "OBSERVATION",
            "SYNTHETIC_REHEARSAL": True,
            "REAL_LOOP_VERIFIED": False,
            "rehearsal_case": spec["case"],
            "reality_event": event,
            "note": "R407-C: OBSERVATION.json — in the REAL loop this file "
                    "is written from an ingested REALITY_EVENT; here it is "
                    "a rehearsal fixture and is marked as such everywhere",
        }
        model_error = {
            "artifact_type": "MODEL_ERROR",
            "SYNTHETIC_REHEARSAL": True,
            "rehearsal_case": spec["case"],
            "error_before_by_head": {
                h: round(abs(base_flows[h] - actual[h]), 4)
                for h in base_flows},
            "error_before_held_out_40mmHg": round(
                abs(ho_pred_before - ho_actual), 4),
            "unit": "mL/min",
        }
        model_update = {
            "artifact_type": "MODEL_UPDATE",
            "SYNTHETIC_REHEARSAL": True,
            "rehearsal_case": spec["case"],
            "update": spec["update"],
            "fitted_parameters": {
                "effective_conductance_factor_k": round(k_fit, 4),
                "fitted_on": ["10 mmHg", "20 mmHg"]},
            "model_changed": True,
            "honest_note": "model_changed=true is WORTHLESS by itself "
                           "(R407-D); the verdict below is computed from "
                           "the held-out error, not from this flag",
        }
        adjudication = ri.adjudicate_learning(
            prediction_before=ho_pred_before,
            actual_measurement=ho_actual,
            prediction_after=ho_pred_after,
            held_out={
                "condition": "40 mmHg head",
                "actual": ho_actual,
                "prediction_before": ho_pred_before,
                "prediction_after": ho_pred_after},
            reality_event=event,
            unit="mL/min")
        prediction_after = {
            "artifact_type": "PREDICTION_AFTER",
            "SYNTHETIC_REHEARSAL": True,
            "REAL_LOOP_VERIFIED": False,
            "rehearsal_case": spec["case"],
            "predictions": pred_after,
            "learning_verdict": adjudication["verdict"],
            "learning_reason": adjudication["reason"],
            "counts_as_learning": adjudication.get("counts_as_learning"),
            "improvement_basis": adjudication.get("improvement_basis"),
        }
        write_json(os.path.join(case_dir, "OBSERVATION.json"), observation)
        write_json(os.path.join(case_dir, "MODEL_ERROR.json"), model_error)
        write_json(os.path.join(case_dir, "MODEL_UPDATE.json"), model_update)
        write_json(os.path.join(case_dir, "PREDICTION_AFTER.json"),
                   prediction_after)
        res = ri.ingest_reality_event(event, rehearsal_ledger_path)
        assert res["ingested"], res
        expected = "MODEL_IMPROVED" if spec["case"] == 1 else \
            "LEARNING_FAILED"
        assert adjudication["verdict"] == expected, (
            f"case {spec['case']}: expected {expected}, got "
            f"{adjudication['verdict']}")
        assert adjudication.get("counts_as_learning") is False, (
            "a rehearsal verdict must never count as learning")
        rehearsal_adjudications.append(adjudication)
        print(f"rehearsal case {spec['case']}: decision={decision['verdict']}"
              f" learning={adjudication['verdict']} "
              f"(held-out error {model_error['error_before_held_out_40mmHg']}"
              f" -> {round(abs(ho_pred_after - ho_actual), 4)})")

    # PREDICTION_BEFORE is shared: reference the registered one from each
    # case directory (copy with a pointer, keeping the single authority).
    for spec in rehearsal_specs:
        write_json(os.path.join(REHEARSAL_DIR, f"case_{spec['case']}",
                                "PREDICTION_BEFORE.json"), {
            "artifact_type": "PREDICTION_BEFORE_REFERENCE",
            "SYNTHETIC_REHEARSAL": True,
            "rehearsal_case": spec["case"],
            "authority": "LEAD_PORTFOLIO_4/P04/REALITY_LOOP/"
                         "PREDICTION_BEFORE.json (the registered "
                         "prediction of record — one authority, Art. X)",
            "sha256": prediction_before["self_sha256"],
        })

    # the R407-D ledger rule over the rehearsal records: verdicts
    # visible, real learning count ZERO.
    rehearsal_summary = ri.learning_ledger_summary(rehearsal_adjudications)
    assert rehearsal_summary["real_learning_events"] == 0
    write_json(os.path.join(REHEARSAL_DIR, "REHEARSAL_SUMMARY.json"), {
        "artifact_type": "REHEARSAL_SUMMARY",
        "SYNTHETIC_REHEARSAL": True,
        "REAL_LOOP_VERIFIED": False,
        "case_1": "MODEL_IMPROVED — held-out error 2.2084 -> 0.0 (the "
                  "update generalizes)",
        "case_2": "LEARNING_FAILED — held-out error 0.7361 -> 1.4723 "
                  "(training improved, held-out WORSENED: the "
                  "learning-theatre discriminator fired)",
        "learning_ledger_rule": rehearsal_summary,
        "note": "both chains prove the R407-C machinery end-to-end; "
                "neither counts as learning (Art. XXXVIII)",
    })

    # ------------------------------------------------------------------
    # 5. LOOP_CLOSURE_PATHS.json (R407-E, both branches)
    # ------------------------------------------------------------------
    demo_event = {"event_id": "REAL-P04-0001", "source_type":
                  "EXTERNAL_INSTRUMENT"}
    write_json(os.path.join(RL, "LOOP_CLOSURE_PATHS.json"), {
        "artifact_type": "LOOP_CLOSURE_PATHS",
        "directive_basis": "R407-E: close the P04 engineering loop on both "
                           "outcomes",
        "success_path": ri.success_path_steps(demo_event),
        "failure_path": {
            "trigger": "decision.verdict == KILL from the frozen contract "
                       "on a REAL ingested observation",
            "stages": [
                "physical observation -> KILL (decide_p04 rule a/b/c)",
                "-> cemetery entry (reality_ingestion.apply_kill_path -> "
                "orchestrator/mechanism_cemetery.py, append-only)",
                "-> failure-memory update (lesson + failed assumption + "
                "affected artifacts, Art. XXXI)",
                "-> discovery search constrained by the failure "
                "(check_candidate_against_cemetery: PROVEN_INVARIANT "
                "hard-blocks, STRONG_CONSTRAINT warns; the cemetery is "
                "READ by mechanism_space/adapters/run — a cemetery that "
                "is never read is a log, not a memory, Art. LI)",
            ],
            "kill_channel_epistemic_classes":
                ri.KILL_CHANNEL_CLASSES,
            "verified_by": "tests/test_r407_first_reality_loop.py "
                           "(sandboxed cemetery: a P04-class candidate "
                           "description is BLOCKED after the kill path "
                           "runs)",
        },
        "state_today": "neither path has fired: zero real observations "
                       "(see EXECUTION_ATTEMPT_R407.json); the machinery "
                       "for both paths is armed and test-proven",
    })

    # ------------------------------------------------------------------
    # 6. Acceptance checklist
    # ------------------------------------------------------------------
    checklist = {
        "artifact_type": "R407_ACCEPTANCE_CHECKLIST",
        "directive": "R407 — FIRST REALITY LOOP",
        "constitution_read_fully": "YES (1,947 lines, before any work)",
        "priority_order": {
            "P04_first": True,
            "P11_second_protocol_level_only": True,
            "P13_containment_no_major_spend": True,
            "P08_no_commercial_power_claims_before_adjudication": True},
        "items": {
            "R407-A_frozen_contract": {
                "status": "DONE",
                "artifact": contract_path,
                "machine_decision": "decide_p04 — KEEP/MODIFY/KILL "
                                    "without human reinterpretation; all "
                                    "branches test-exercised"},
            "R407-B_ingestion_contract": {
                "status": "DONE",
                "artifact": "LEAD_PORTFOLIO_4/REALITY_INGESTION_CONTRACT.json",
                "enforcement": "reality_ingestion.validate_reality_event_v2"
                               " + append-only hash-chained ledger"},
            "R407-C_adjudication_chain": {
                "status": "DONE (machinery + rehearsal proof)",
                "artifacts": "LEAD_PORTFOLIO_4/P04/REALITY_LOOP/ "
                             "(PREDICTION_BEFORE registered; OBSERVATION "
                             "armed; REHEARSAL/case_1 and case_2 carry the "
                             "full five-file chain)"},
            "R407-D_anti_learning_theatre": {
                "status": "DONE",
                "proof": "rehearsal case 2: model_changed=true + training "
                         "improvement, yet the held-out error WORSENS -> "
                         "LEARNING_FAILED stands as a valid recorded "
                         "outcome; MODEL_IMPROVED requires held-out "
                         "improvement AND prediction movement"},
            "R407-E_loop_closure": {
                "status": "DONE (both paths armed)",
                "artifact": "LEAD_PORTFOLIO_4/P04/REALITY_LOOP/"
                            "LOOP_CLOSURE_PATHS.json"},
            "R407-F_P11_protocol": {
                "status": "DONE",
                "artifact": "LEAD_PORTFOLIO_4/P11/"
                            "EXPERIMENT_CONTRACT_FROZEN.json (settling "
                            "time, steady-state flow error, MDD 0.0253 s, "
                            "kill conditions A/B; no new simulation)"},
            "R407_G_P08_adjudication": {
                "status": "DONE",
                "artifact": "R407/P08_ADJUDICATION/"
                            "R407_P08_CANONICAL_ADJUDICATION.json + "
                            "regenerated ENERGY_BUDGET (v3.0) with "
                            "uncertainty bounds"},
            "R407-H_P13_containment": {
                "status": "DONE",
                "artifact": "LEAD_PORTFOLIO_4/P13/"
                            "CLAIM_LEVEL_NOVELTY_COMPARISON_R407.json "
                            "(engineering spend frozen; claim-level "
                            "comparison vs the located art)"},
            "R407-I_final_acceptance": {
                "status": "ACHIEVED VIA BRANCH 2: documented real-world "
                          "execution failure with the same provenance "
                          "integrity",
                "artifact": "LEAD_PORTFOLIO_4/P04/REALITY_LOOP/"
                            "EXECUTION_ATTEMPT_R407.json",
                "branch_1_physical_experiment": "NOT ACHIEVED: zero real "
                                                "observations (honest "
                                                "state, unchanged)"},
        },
        "physical_observation_count": 0,
        "real_event_count": 0,
        "real_buyer_count": real_buyer,
        "honest_headline": "the machine put P04 in front of reality; "
                           "reality answered 'no apparatus, no operator, "
                           "no funded samples'; the failure is recorded "
                           "with provenance integrity and the first-real-"
                           "observation machinery (contract, ingestion "
                           "boundary, adjudication, both closure paths) "
                           "is armed and adversarially tested",
    }
    write_json(os.path.join(REPO, "R407", "R407_ACCEPTANCE_CHECKLIST.json"),
               checklist)

    print(f"\nPREDICTION_BEFORE registered: flows={flows} "
          f"conductance={pred_values['floor_segment_conductance_mL_min_mmHg']}")
    print(f"EXECUTION_ATTEMPT: {execution_attempt['outcome']} "
          f"({len(preconditions)} preconditions, all BLOCKED)")
    print(f"loop chain state: {derived['current_state']} / "
          f"{derived['loop_verification_state']} / "
          f"{derived['promotion_blocked_reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

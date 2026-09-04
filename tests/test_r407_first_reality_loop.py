"""R407 adversarial test battery — FIRST REALITY LOOP.

Pins (Art. XVI/XIX/XVII: code is a hypothesis about enforcement; these
tests are evidence of enforcement):
  - R407-B: the REALITY_EVENT v2 ingestion contract (positive + every
    mandatory-field negative + hash-format, source-type, provenance,
    blank-operator adversarial cases)
  - the append-only hash-chained reality ledger (ingest / verify /
    double-entry / tamper detection)
  - R407-A: the frozen P04 contract decision function (KEEP / KILL-a /
    KILL-b / KILL-c / MODIFY / EXECUTION_INVALID — every branch,
    no human reinterpretation)
  - R407-F: the frozen P11 contract decision function (SUPPORTED /
    KILLED-A / KILLED-AB / MIXED)
  - R407-C/D: adjudicate_learning (MODEL_IMPROVED requires held-out
    improvement + movement; LEARNING_FAILED is a valid outcome; rehearsal
    NEVER counts as learning; INSUFFICIENT_DATA stays honest)
  - the committed rehearsal records verify (case 1 MODEL_IMPROVED, case 2
    LEARNING_FAILED — the anti-learning-theatre discriminator)
  - the committed REALITY_LEDGER is valid and EMPTY (0 real events)
  - EXECUTION_ATTEMPT_R407: execution blocked with provenance integrity,
    loop unchanged at PREDICTION, 0 real events
  - R407-G: canonical == budget consistency (the ONE canonical fluence
    appears identically in the adjudication record and the regenerated
    ENERGY_BUDGET v3.0; the clean-checkout replay verdict; the R406
    byte-identical fluence pin)
  - R407-H: the P13 claim-level comparison verdict + spend freeze
  - the acceptance checklist's honest counts (0 physical observations,
    0 real buyers, 0 real events)
"""
import json
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from discovery_fabric.engine import reality_ingestion as ri  # noqa: E402


def load(rel):
    with open(os.path.join(REPO, rel)) as f:
        return json.load(f)


SHA = "a" * 64
SHA2 = "b" * 64


def valid_event(**over):
    """A fully valid REALITY_EVENT v2 (a real instrument observation)."""
    ev = {
        "event_id": "EVT-TEST-001",
        "experiment_id": "P04-R407-EXP-001",
        "package_id": "P04",
        "timestamp": "2026-09-04T12:00:00Z",
        "apparatus_id": "P04-BENCH-001",
        "operator": "UNKNOWN",
        "raw_data_hash": SHA,
        "processed_data_hash": SHA2,
        "measurement_units": {"flow": "mL/min"},
        "uncertainty": {"flow": 0.05},
        "baseline_result": {"flow": 0.005},
        "candidate_result": {"flow": 0.55},
        "pre_registered_threshold": {"q_min": 0.4},
        "decision": {"verdict": "KEEP", "rule_id": "P04-KEEP-ACCEPT"},
        "source_type": "EXTERNAL_INSTRUMENT",
        "organization": "SPONSOR-LAB-1",
        "custody_chain": [{"actor": "operator-1", "action": "acquired",
                            "timestamp": "2026-09-04T12:00:00Z"}],
        "attestation": {"attestation_text": "measured on the bench",
                         "attestation_hash": SHA},
        "provenance_validated": True,
    }
    ev.update(over)
    return ev


# ---------------------------------------------------------------------------
# R407-B — the ingestion contract
# ---------------------------------------------------------------------------

def test_valid_event_passes():
    assert ri.validate_reality_event_v2(valid_event()) == []


@pytest.mark.parametrize("field", ri.REALITY_EVENT_V2_MANDATORY)
def test_every_mandatory_field_is_required(field):
    ev = valid_event()
    ev[field] = None
    problems = ri.validate_reality_event_v2(ev)
    assert any(field in p for p in problems), problems


def test_all_19_mandatory_fields_are_the_directive_set():
    assert len(ri.REALITY_EVENT_V2_MANDATORY) == 19
    assert set(ri.R407_B_MANDATORY_FIELDS) == {
        "experiment_id", "package_id", "timestamp", "apparatus_id",
        "operator", "raw_data_hash", "processed_data_hash",
        "measurement_units", "uncertainty", "baseline_result",
        "candidate_result", "pre_registered_threshold", "decision"}


def test_hash_format_enforced():
    ev = valid_event(raw_data_hash="not-a-hash")
    assert any("raw_data_hash" in p for p in
               ri.validate_reality_event_v2(ev))


def test_invalid_source_type_rejected():
    ev = valid_event(source_type="AI_GENERATED")
    assert any("source_type" in p for p in
               ri.validate_reality_event_v2(ev))


def test_provenance_must_be_validated():
    ev = valid_event(provenance_validated=False)
    assert any("provenance_validated" in p for p in
               ri.validate_reality_event_v2(ev))


def test_blank_operator_rejected_but_unknown_is_legitimate():
    blank = valid_event(operator="   ")
    assert any("operator" in p for p in ri.validate_reality_event_v2(blank))
    unknown = valid_event(operator="UNKNOWN")
    assert not any("operator" in p for p in
                   ri.validate_reality_event_v2(unknown))


def test_free_text_decision_rejected():
    ev = valid_event(decision="looks good to me")
    assert any("decision" in p for p in ri.validate_reality_event_v2(ev))


def test_controlled_rehearsal_is_a_valid_source_type():
    ev = valid_event(source_type="CONTROLLED_REHEARSAL",
                     event_id="EVT-REH-001")
    assert ri.validate_reality_event_v2(ev) == []


# ---------------------------------------------------------------------------
# the ledger: ingest / verify / double-entry / tamper
# ---------------------------------------------------------------------------

def test_ledger_ingest_verify_doubleentry_tamper(tmp_path):
    ledger = str(tmp_path / "REALITY_LEDGER.json")
    r1 = ri.ingest_reality_event(valid_event(), ledger)
    assert r1["ingested"] is True
    r2 = ri.ingest_reality_event(valid_event(), ledger)  # same event_id
    assert r2["ingested"] is False
    assert any("double entry" in p for p in r2["problems"])
    v = ri.verify_ledger(ledger)
    assert v["valid"] is True and v["entries"] == 1

    # adversarial: tamper with the committed record -> chain breaks
    with open(ledger) as f:
        data = json.load(f)
    data["entries"][0]["record"]["candidate_result"]["flow"] = 99.0
    with open(ledger, "w") as f:
        json.dump(data, f)
    v2 = ri.verify_ledger(ledger)
    assert v2["valid"] is False and "tampered" in v2["reason"]


def test_rehearsal_never_counts_as_real_event(tmp_path):
    ledger = str(tmp_path / "REALITY_LEDGER.json")
    ev = valid_event(source_type="CONTROLLED_REHEARSAL",
                     event_id="EVT-REH-002")
    r = ri.ingest_reality_event(ev, ledger)
    assert r["ingested"] is True
    assert r["real_event_count"] == 0  # Art. XXXVIII
    ev2 = valid_event(event_id="EVT-REAL-002")
    r2 = ri.ingest_reality_event(ev2, ledger)
    assert r2["real_event_count"] == 1


def test_committed_reality_ledger_is_valid_and_empty():
    v = ri.verify_ledger(os.path.join(
        REPO, "LEAD_PORTFOLIO_4", "P04", "REALITY_LOOP",
        "REALITY_LEDGER.json"))
    assert v["valid"] is True
    ledger = load("LEAD_PORTFOLIO_4/P04/REALITY_LOOP/REALITY_LEDGER.json")
    assert ledger["entry_count"] == 0
    assert ledger["real_event_count"] == 0


# ---------------------------------------------------------------------------
# R407-A — the frozen P04 contract decision function, every branch
# ---------------------------------------------------------------------------

def obs(**over):
    base = {
        "residual_floor_flow_mL_min_by_head_mmHg": {"10": 3.13,
                                                     "20": 6.26,
                                                     "40": 12.51},
        "measured_G_ratio": 0.0752,
        "common_cause_occlusion_rate_pct": 30.0,
        "valid_trials_total": 18,
        "void_trial_count": 0,
        "manufacturing_minwall_all_failed": False,
    }
    base.update(over)
    return {"candidate_result": base}


def test_p04_keep_branch():
    d = ri.decide_p04(obs())
    assert d["verdict"] == "KEEP"
    assert d["rule_id"] == "P04-KEEP-ACCEPT"


def test_p04_kill_a_common_cause():
    d = ri.decide_p04(obs(common_cause_occlusion_rate_pct=90.0))
    assert d["verdict"] == "KILL"
    assert d["rule_id"] == "P04-KILL-A-COMMONCAUSE"


def test_p04_kill_b_no_protection():
    d = ri.decide_p04(obs(residual_floor_flow_mL_min_by_head_mmHg={
        "10": 0.1, "20": 0.15, "40": 0.19}))
    assert d["verdict"] == "KILL"
    assert d["rule_id"] == "P04-KILL-B-NOPROTECTION"


def test_p04_kill_c_manufacturing():
    d = ri.decide_p04(obs(manufacturing_minwall_all_failed=True))
    assert d["verdict"] == "KILL"
    assert d["rule_id"] == "P04-KILL-C-MFG"


def test_p04_modify_indeterminate_band():
    d = ri.decide_p04(obs(residual_floor_flow_mL_min_by_head_mmHg={
        "10": 0.25, "20": 0.30, "40": 0.35}))
    assert d["verdict"] == "MODIFY"


def test_p04_modify_g_ratio_miss():
    d = ri.decide_p04(obs(measured_G_ratio=0.5))
    assert d["verdict"] == "MODIFY"


def test_p04_execution_invalid():
    d = ri.decide_p04(obs(valid_trials_total=0))
    assert d["verdict"] == "EXECUTION_INVALID"  # Art. LXI


def test_p04_frozen_thresholds_are_the_preregistered_values():
    assert ri.P04_G_RATIO_MODELLED == 0.0885
    assert ri.P04_Q_MIN_PASS == 0.4
    assert ri.P04_Q_MIN_KILL == 0.2
    assert ri.P04_COMMON_CAUSE_KILL_PCT == 90.0
    assert ri.P04_PASS_HEADS_REQUIRED == 2


def test_p04_committed_rehearsal_case1_decision_matches_pure_function():
    o = load("LEAD_PORTFOLIO_4/P04/REALITY_LOOP/REHEARSAL/case_1/"
             "OBSERVATION.json")
    d_fn = ri.decide_p04(o["reality_event"])
    d_committed = o["reality_event"]["decision"]
    assert d_fn["verdict"] == d_committed["verdict"] == "KEEP"
    assert d_fn["rule_id"] == d_committed["rule_id"]


# ---------------------------------------------------------------------------
# R407-F — the frozen P11 contract decision function
# ---------------------------------------------------------------------------

def p11_obs(**over):
    base = {
        "settling_time_s_by_pressure": {
            "10": {"damper": 0.75, "asd": 1.00},   # 25% faster
            "20": {"damper": 1.50, "asd": 2.00}},  # 25% faster
        "damper_flow_deviation_worse_than_asd": False,
    }
    base.update(over)
    return {"candidate_result": base}


def test_p11_supported():
    assert ri.decide_p11(p11_obs())["verdict"] == "SUPPORTED"


def test_p11_killed_a_speed():
    d = ri.decide_p11(p11_obs(settling_time_s_by_pressure={
        "10": {"damper": 0.95, "asd": 1.00},   # only 5% faster
        "20": {"damper": 1.60, "asd": 2.00}}))
    assert d["verdict"] == "KILLED"
    assert d["rule_id"] == "P11-KILLED-A"


def test_p11_killed_ab_both_channels():
    d = ri.decide_p11(p11_obs(
        settling_time_s_by_pressure={
            "10": {"damper": 0.95, "asd": 1.00},
            "20": {"damper": 1.60, "asd": 2.00}},
        damper_flow_deviation_worse_than_asd=True))
    assert d["verdict"] == "KILLED"
    assert d["rule_id"] == "P11-KILLED-AB"


def test_p11_mixed_recorded_exactly():
    d = ri.decide_p11(p11_obs(damper_flow_deviation_worse_than_asd=None))
    assert d["verdict"] == "MIXED"


def test_p11_frozen_kill_thresholds():
    assert ri.P11_SETTLING_KILL_PCT == 20.0
    assert ri.P11_MDD_S == 0.0253


# ---------------------------------------------------------------------------
# R407-C/D — the anti-learning-theatre adjudication
# ---------------------------------------------------------------------------

REAL = valid_event(event_id="EVT-ADJ-REAL")
REH = valid_event(source_type="CONTROLLED_REHEARSAL",
                  event_id="EVT-ADJ-REH")


def test_model_improved_requires_heldout_improvement_and_movement():
    r = ri.adjudicate_learning(
        prediction_before=2.0, actual_measurement=3.0,
        prediction_after=3.0,
        held_out={"actual": 4.0, "prediction_before": 1.5,
                  "prediction_after": 3.9},
        reality_event=REAL)
    assert r["verdict"] == "MODEL_IMPROVED"
    assert r["improvement_basis"] == "held_out"


def test_learning_failed_when_heldout_worsens_despite_training_gain():
    # the R407-D discriminator: training error improves, held-out worsens
    r = ri.adjudicate_learning(
        prediction_before=2.0, actual_measurement=2.0,
        prediction_after=2.0,   # training error 0
        held_out={"actual": 4.0, "prediction_before": 3.26,
                  "prediction_after": 5.47},
        reality_event=REAL)
    assert r["verdict"] == "LEARNING_FAILED"
    assert r["held_out_error_after"] > r["held_out_error_before"]


def test_learning_failed_when_prediction_did_not_move():
    r = ri.adjudicate_learning(
        prediction_before=2.0, actual_measurement=2.5,
        prediction_after=2.0,  # identical prediction: nothing learned
        reality_event=REAL)
    assert r["verdict"] == "LEARNING_FAILED"


def test_rehearsal_never_counts_as_learning():
    r = ri.adjudicate_learning(
        prediction_before=2.0, actual_measurement=3.0,
        prediction_after=3.0,
        held_out={"actual": 4.0, "prediction_before": 1.5,
                  "prediction_after": 3.9},
        reality_event=REH)
    assert r["verdict"] == "MODEL_IMPROVED"       # machinery demonstrated
    assert r["counts_as_learning"] is False        # Art. XXXVIII


def test_insufficient_data_without_measurement():
    r = ri.adjudicate_learning(prediction_before=2.0,
                               actual_measurement=None,
                               prediction_after=None,
                               reality_event=REAL)
    assert r["verdict"] == "INSUFFICIENT_DATA"


def test_learning_ledger_only_counts_real_improved():
    real_ok = ri.adjudicate_learning(
        2.0, 3.0, 3.0, held_out={"actual": 4.0, "prediction_before": 1.5,
                                  "prediction_after": 3.9},
        reality_event=REAL)
    reh_ok = ri.adjudicate_learning(
        2.0, 3.0, 3.0, held_out={"actual": 4.0, "prediction_before": 1.5,
                                  "prediction_after": 3.9},
        reality_event=REH)
    failed = ri.adjudicate_learning(
        2.0, 2.0, 2.0, held_out={"actual": 4.0, "prediction_before": 3.2,
                                  "prediction_after": 5.4},
        reality_event=REAL)
    s = ri.learning_ledger_summary([real_ok, reh_ok, failed])
    assert s["counts_by_verdict"]["MODEL_IMPROVED"] == 2
    assert s["real_learning_events"] == 1          # rehearsal excluded
    assert s["learning_loop_operational"] is True


# ---------------------------------------------------------------------------
# committed R407 artifacts — the pins
# ---------------------------------------------------------------------------

def test_committed_rehearsal_chains_and_discriminator():
    p04 = os.path.join(REPO, "LEAD_PORTFOLIO_4", "P04",
                       "REALITY_LOOP", "REHEARSAL")
    for case, expected in (("case_1", "MODEL_IMPROVED"),
                           ("case_2", "LEARNING_FAILED")):
        for fname in ri.ADJUDICATION_CHAIN_FILES:
            assert os.path.exists(os.path.join(p04, case, fname)), fname
        after = load(f"LEAD_PORTFOLIO_4/P04/REALITY_LOOP/REHEARSAL/{case}/"
                     "PREDICTION_AFTER.json")
        assert after["learning_verdict"] == expected
        for f in ("OBSERVATION", "MODEL_ERROR", "MODEL_UPDATE",
                  "PREDICTION_AFTER"):
            rec = load(f"LEAD_PORTFOLIO_4/P04/REALITY_LOOP/REHEARSAL/"
                       f"{case}/{f}.json")
            assert rec.get("SYNTHETIC_REHEARSAL") is True
            # the loop-verification marker appears on the boundary files
            # (observation in, prediction out) and is False when present
            if "REAL_LOOP_VERIFIED" in rec:
                assert rec["REAL_LOOP_VERIFIED"] is False


def test_committed_rehearsal_summary_never_learning():
    s = load("LEAD_PORTFOLIO_4/P04/REALITY_LOOP/REHEARSAL/"
             "REHEARSAL_SUMMARY.json")
    assert s["SYNTHETIC_REHEARSAL"] is True
    assert s["REAL_LOOP_VERIFIED"] is False
    assert s["learning_ledger_rule"]["real_learning_events"] == 0


def test_execution_attempt_record_provenance_integrity():
    r = load("LEAD_PORTFOLIO_4/P04/REALITY_LOOP/EXECUTION_ATTEMPT_R407.json")
    assert r["outcome"] == "EXECUTION_BLOCKED"
    assert r["classification"].startswith("INCOMPLETE_INFRASTRUCTURE_FAILURE")
    pf = r["provenance_fields"]
    for field in ("raw_data_hash", "processed_data_hash", "operator",
                  "measurement_units", "uncertainty", "baseline_result",
                  "candidate_result"):
        assert str(pf[field]).startswith("ABSENT"), field
    assert r["effect_on_loop_chain"]["derived_state_before_attempt"] == \
        "PREDICTION"
    assert r["effect_on_loop_chain"]["promotion_blocked_reason"] == \
        "NO_PHYSICAL_DATA"
    assert r["real_event_count_after_attempt"] == 0
    for check in r["precondition_checks"]:
        assert check["status"] == "BLOCKED"
        assert check["evidence"], "each blocker must cite evidence"


# ---------------------------------------------------------------------------
# R407-G — canonical == budget consistency pins
# ---------------------------------------------------------------------------

def test_p08_canonical_adjudication_consistency():
    adj = load("R407/P08_ADJUDICATION/R407_P08_CANONICAL_ADJUDICATION.json")
    declared = adj["step_5_canonical_declaration"][
        "declared_canonical_fluence_mW_per_cm2"]
    # the canonical is the committed R406 pipeline's byte-identical value
    assert declared == 0.7050488365664916
    # the clean-checkout replay verdict
    replay = adj["step_1_canonical_model_from_clean_checkout"]
    assert replay["outputs_byte_identical"] is True
    assert replay["verdict"] == \
        "CANONICAL_MODEL_REGENERABLE_FROM_CLEAN_CHECKOUT"
    # the historical values are preserved, never erased (Art. XI)
    hist = adj["step_6_historical_preservation"]
    for key in ("R308_0.744", "R310_1.049054", "R311_1.415645",
                "R312_1.146949"):
        assert key in hist and "HISTORICAL" in hist[key]


def test_p08_energy_budget_v3_matches_canonical():
    budget = load("LEAD_PORTFOLIO_4/P08/ENERGY_BUDGET.json")
    adj = load("R407/P08_ADJUDICATION/R407_P08_CANONICAL_ADJUDICATION.json")
    declared = adj["step_5_canonical_declaration"][
        "declared_canonical_fluence_mW_per_cm2"]
    assert budget["artifact_version"] == "3.0"
    cc = budget["canonical_calculation"]
    phi = [i for i in cc["inputs"] if i["symbol"] == "Phi_det"][0]
    assert phi["value"] == declared
    assert phi["evidence_class"] == "COMPUTATIONAL_RESULT_CANONICAL"
    # the buyer-facing band is derived from the canonical, not the
    # superseded 1.049054 anchor
    band = budget["r407_extensions"]["uncertainty_bounds"][
        "conditional_band_uW"]
    p_inc = declared * 0.384845 * 1000
    assert band[0] == round(p_inc * 0.186, 1)
    assert band[1] == round(p_inc * 0.30, 1)
    # historical values preserved verbatim in the budget too
    assert cc["historical_values_preserved"][
        "R310_converged_fluence_mW_per_cm2"] == 1.049054387745623


def test_p08_buyer_sequence_carries_the_adjudicated_statement():
    bs = load("LEAD_PORTFOLIO_4/P08/BUYER_SEQUENCE.json")
    txt = bs["sections"]["5_evidence"]
    assert "50.5-81.4 uW" in txt
    assert "HISTORICAL" in txt
    assert "121-163 uW" not in txt          # superseded band not quotable


# ---------------------------------------------------------------------------
# R407-H — the P13 claim-level comparison
# ---------------------------------------------------------------------------

def test_p13_claim_level_comparison_verdict():
    c = load("LEAD_PORTFOLIO_4/P13/CLAIM_LEVEL_NOVELTY_COMPARISON_R407.json")
    assert c["verdict"]["result"] == \
        "NO_INCONTROVERTIBLE_TECHNICAL_DISTINCTION"
    summary = c["claim_level_summary"]
    assert summary["elements_located"] == ["E1", "E2", "E3", "E4"]
    assert summary["elements_not_located"] == ["E5", "E6"]
    # the spend freeze is permanent and the kill is NOT machine-executed
    assert c["disposition"]["engineering_spend"] == \
        "FROZEN (permanent per the R407-H rule; the R406 $95-265K " \
        "fab-NRE gate stands)"
    assert c["disposition"]["machine_executed_kill"] is False
    # every located element cites verbatim spans (Art. II)
    for el in c["claim_elements"]:
        for art in el.get("located_in", []):
            assert art.get("verbatim"), el["id"]
    # inputs of record are hash-pinned
    assert c["inputs_of_record"]["novelty_search_record"]["sha256"]


# ---------------------------------------------------------------------------
# the acceptance checklist's honest counts
# ---------------------------------------------------------------------------

def test_acceptance_checklist_honest_counts():
    c = load("R407/R407_ACCEPTANCE_CHECKLIST.json")
    assert c["physical_observation_count"] == 0
    assert c["real_buyer_count"] == 0
    assert c["real_event_count"] == 0
    assert c["constitution_read_fully"].startswith("YES")


def test_p04_prediction_before_registered():
    p = load("LEAD_PORTFOLIO_4/P04/REALITY_LOOP/PREDICTION_BEFORE.json")
    assert p["artifact_type"] == "PREDICTION_BEFORE"
    assert p["registered_before_any_run"] is True
    assert p["experiment_id"] == "P04-R407-EXP-001"
    assert p["falsifiable_statement"]  # Art. LII: the falsifier exists
    assert p["predictions"]["residual_floor_flow_mL_min_by_head_mmHg"]
    assert p["predictions"]["G_ratio_modelled"] == 0.0885
    assert p["held_out_condition"]["condition"] == "40 mmHg head"
    assert len(p["contract_sha256"]) == 64

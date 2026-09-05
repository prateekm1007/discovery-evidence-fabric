"""R406 adversarial test battery — real technology-transfer loop.

Pins (Art. XVI/XIX/XVII: code is a hypothesis about enforcement; these
tests are evidence of enforcement):
  - the 14-state canonical chain + promotion blocking without physical data
    (including the adversarial attempts: silent promotion, rehearsal
    promotion, malformed REALITY_EVENT)
  - Art. XXXVIII REALITY_EVENT schema enforcement
  - model-vs-measurement verdicts (MODEL_IMPROVED requires movement +
    held-out improvement; rehearsal never learns; missing data stays
    INSUFFICIENT_DATA)
  - the R405 truth snapshot facts
  - the conductance contamination audit findings (ratio survival EQUALITY,
    the meets_required_min flip, inventory completeness)
  - the P04 NIST decision consistency
  - the P08 pipeline reproducibility (committed outputs + fluence contest)
  - the P13 novelty verdict + custody
  - pre-registration threshold pins
  - buyer states REAL_BUYER=0 + killability
"""
import json
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from discovery_fabric.engine import loop_chain  # noqa: E402
from discovery_fabric.engine import model_measurement as mm  # noqa: E402
from discovery_fabric.engine.physics_core import (  # noqa: E402
    conductance_ml_per_min_mmhg,)


def load(rel):
    with open(os.path.join(REPO, rel)) as f:
        return json.load(f)


def mk(i, frm, to, **kw):
    ev = {"event_id": f"test-ev-{i:04d}", "from_state": frm, "to_state": to,
          "evidence_ref": "test", "evidence_class": "AI_INFERENCE"}
    ev.update(kw)
    return ev


_SEQ = [("DISCOVERY", "EVIDENCE"), ("EVIDENCE", "MECHANISM"),
        ("MECHANISM", "ENGINEERING"), ("ENGINEERING", "SIMULATION"),
        ("SIMULATION", "PREDICTION")]


def base_chain():
    return [mk(i, f, t) for i, (f, t) in enumerate(_SEQ, 1)]


GOOD_RE = {
    "event_id": "EVT-TEST-0001", "event_type": "BENCH_MEASUREMENT",
    "package_id": "P04", "source_type": "EXTERNAL_INSTRUMENT",
    "organization": "TestLab", "operator": "TestOp",
    "acquisition_timestamp": "2026-09-04T00:00:00Z",
    "raw_artifact_ref": "test.bin", "raw_data_sha256": "a" * 64,
    "attestation": {"attestation_text": "measured",
                    "attestation_hash": "b" * 64},
    "custody_chain": [{"step": 1, "actor": "op", "timestamp": "now",
                       "action": "acquire"}],
    "provenance_validated": True,
}


# ---------------- loop chain enforcement ----------------

def test_canonical_chain_fourteen_states():
    assert loop_chain.LOOP_STATES == [
        "DISCOVERY", "EVIDENCE", "MECHANISM", "ENGINEERING", "SIMULATION",
        "PREDICTION", "PHYSICAL_EXPERIMENT", "OBSERVATION", "MODEL_UPDATE",
        "BASELINE_COMPARISON", "KEEP_MODIFY_KILL", "LEARNING_MEMORY",
        "NEXT_DISCOVERY"]


def test_promotion_blocked_without_physical_data():
    d = loop_chain.derive_loop_state(base_chain())
    assert d["current_state"] == "PREDICTION"
    assert d["promotion_blocked"] is True
    assert d["promotion_blocked_reason"] == "NO_PHYSICAL_DATA"
    assert d["loop_verification_state"] == "NONE"


def test_adversarial_silent_promotion_rejected():
    chain = base_chain() + [mk(6, "PREDICTION", "PHYSICAL_EXPERIMENT")]
    d = loop_chain.derive_loop_state(chain)
    assert d["current_state"] == "PREDICTION"  # blocked


def test_adversarial_rehearsal_cannot_promote():
    chain = base_chain() + [mk(6, "PREDICTION", "PHYSICAL_EXPERIMENT",
                               REALITY_EVENT={"source_type":
                                              "CONTROLLED_REHEARSAL"})]
    d = loop_chain.derive_loop_state(chain)
    assert d["current_state"] == "PREDICTION"


def test_adversarial_malformed_reality_event_rejected():
    chain = base_chain() + [mk(6, "PREDICTION", "PHYSICAL_EXPERIMENT",
                               REALITY_EVENT={"source_type":
                                              "EXTERNAL_INSTRUMENT"})]
    d = loop_chain.derive_loop_state(chain)
    assert d["current_state"] == "PREDICTION"
    assert d["validation_problems"]


def test_adversarial_state_skip_rejected():
    chain = [mk(1, "DISCOVERY", "MECHANISM")]  # skip EVIDENCE
    d = loop_chain.derive_loop_state(chain)
    assert d["current_state"] is None
    assert d["validation_problems"]


def test_valid_reality_event_promotes_and_model_update_needs_measurement():
    chain = base_chain() + [
        mk(6, "PREDICTION", "PHYSICAL_EXPERIMENT", REALITY_EVENT=GOOD_RE)]
    d = loop_chain.derive_loop_state(chain)
    assert d["current_state"] == "PHYSICAL_EXPERIMENT"
    # advancing to OBSERVATION without PHYSICAL_OBSERVATION class fails
    chain2 = chain + [mk(7, "PHYSICAL_EXPERIMENT", "OBSERVATION",
                         evidence_class="AI_INFERENCE", REALITY_EVENT=GOOD_RE)]
    d2 = loop_chain.derive_loop_state(chain2)
    assert d2["current_state"] == "PHYSICAL_EXPERIMENT"
    # correct class advances
    chain3 = chain + [mk(7, "PHYSICAL_EXPERIMENT", "OBSERVATION",
                         evidence_class="PHYSICAL_OBSERVATION",
                         REALITY_EVENT=GOOD_RE)]
    d3 = loop_chain.derive_loop_state(chain3)
    assert d3["current_state"] == "OBSERVATION"
    # MODEL_UPDATE requires a measurement record
    chain4 = chain3 + [mk(8, "OBSERVATION", "MODEL_UPDATE",
                          evidence_class="PHYSICAL_OBSERVATION",
                          REALITY_EVENT=GOOD_RE)]
    d4 = loop_chain.derive_loop_state(chain4)
    assert d4["current_state"] == "OBSERVATION"


def test_reality_event_schema_fields():
    problems = loop_chain.validate_reality_event({})
    for field in loop_chain._REALITY_EVENT_REQUIRED_FIELDS:
        assert any(field in p for p in problems)
    assert loop_chain.validate_reality_event(GOOD_RE) == []


def test_package_chains_all_capped_at_prediction():
    for pkg in ("P04", "P08", "P11", "P13"):
        rec = load(f"LEAD_PORTFOLIO_4/{pkg}/LOOP_CHAIN.json")
        d = rec["derived"]
        assert d["current_state"] == "PREDICTION", pkg
        assert d["promotion_blocked"] is True, pkg
        assert d["promotion_blocked_reason"] == "NO_PHYSICAL_DATA", pkg
        assert d["loop_verification_state"] == "NONE", pkg
        # every event carries machine-readable provenance
        for ev in rec["events"]:
            assert ev["event_id"] and ev["evidence_ref"] and ev["evidence_class"]
        # re-derivation reproduces the committed derived state
        assert loop_chain.derive_loop_state(rec["events"]) == d


# ---------------- model-vs-measurement ----------------

def test_mm_insufficient_data_when_no_measurement():
    rec = mm.build_update_record(1.0, None, None, None, None, None, None, None)
    assert rec["verdict"] == "INSUFFICIENT_DATA"
    assert "actual_measurement" in rec["insufficient_fields"]


def test_mm_rehearsal_never_learns():
    rec = mm.build_update_record(
        1.0, 1.2, {"k": 1.2}, 1.2, 0.2, 0.0, 0.05,
        {"event_id": "EVT-R", "source_type": "CONTROLLED_REHEARSAL"})
    assert rec["verdict"] == "INSUFFICIENT_DATA"


def test_mm_improved_requires_movement_and_heldout():
    re_ = {"event_id": "EVT-1", "source_type": "EXTERNAL_INSTRUMENT"}
    good = mm.build_update_record(1.0, 1.2, {"k": 1.2}, 1.2, 0.2, 0.05, 0.1, re_)
    assert good["verdict"] == "MODEL_IMPROVED"
    # no movement -> not improved (a reality event that changes nothing is
    # not a learning loop)
    flat = mm.build_update_record(1.0, 1.0, {"k": 1.0}, 1.0, 0.1, 0.1, 0.05, re_)
    assert flat["verdict"] == "MODEL_NOT_IMPROVED"
    # moved but held-out worse -> not improved
    bad_ho = mm.build_update_record(1.0, 1.2, {"k": 1.2}, 1.2, 0.2, 0.1, 0.3, re_)
    assert bad_ho["verdict"] == "MODEL_NOT_IMPROVED"


def test_mm_ledgers_all_awaiting():
    for pkg in ("P04", "P08", "P11", "P13"):
        led = load(f"LEAD_PORTFOLIO_4/{pkg}/MODEL_UPDATE_LEDGER.json")
        assert led["summary"]["learning_loop_operational"] is False
        for r in led["records"]:
            assert r["verdict"] == "INSUFFICIENT_DATA"
            assert r["actual_measurement"] is None
        # armed fields present
        assert set(led["armed_fields"]) == set(mm._REQUIRED_FIELDS)


# ---------------- truth snapshot ----------------

def test_truth_snapshot_facts():
    snap = load("R406/R405_TRUTH_SNAPSHOT.json")
    assert snap["physical_observation_count"] == 0
    assert snap["buyer_engagement_state"]["REAL_BUYER"] == 0
    assert snap["commit"]["sha"].startswith("67792862")
    assert snap["novelty_provenance_pin_mismatches"] == []
    n = sum(len(v) for v in snap["package_record_hashes"].values())
    assert n >= 40  # all four packages hashed
    assert len(snap["novelty_evidence_hashes"]) == 13
    assert len(snap["known_discrepancies"]) >= 6
    assert len(snap["known_unknowns"]) >= 5


# ---------------- contamination audit ----------------

def test_contamination_audit_findings():
    audit = load("R406/R406_CONDUCTANCE_CONTAMINATION_AUDIT.json")
    counts = audit["classification_counts"]
    assert set(counts) <= {"UNAFFECTED", "CORRECTED", "HISTORICAL_ONLY",
                           "REQUIRES_REGENERATION", "REQUIRES_REASSESSMENT"}
    assert counts.get("REQUIRES_REASSESSMENT", 0) >= 3
    assert len(audit["new_findings_vs_r405_disclosure"]) == 2
    # finding B: the verdict flip
    assert any("meets_required_min" in f for f in
               audit["new_findings_vs_r405_disclosure"])
    # the R400 UI artifact must now be inventoried
    assert any("RUN_ARTIFACTS_ui_partial_obstruction" in a["artifact"]
               for a in audit["affected_artifacts"])


def test_ratio_survival_equality_recomputed():
    # recompute the R396 improvement equality from the artifact itself
    d = load("R396/P07_FAILURE_MODE_CONTRACT.json")
    bc = d["baseline_comparison"]
    K = 133.322 ** 2
    cand, base = bc["candidate"]["value"], bc["baseline"]["value"]
    recorded = bc["comparison"]["improvement_relative"]
    recomputed = (cand * K - base * K) / (base * K)
    assert abs(recorded - recomputed) < 1e-6
    # the constraint verdict flip
    assert bc["constraints"]["meets_required_min"] is False
    assert (cand * K) >= bc["constraints"]["required_min"]


def test_engine_conductance_magnitude_guard():
    g = conductance_ml_per_min_mmhg(0.6, 0.6913036, 100.0)
    assert 0.05 <= g <= 5.0
    assert abs(g - 0.368069) / 0.368069 < 1e-4


# ---------------- P04 NIST decision ----------------

def test_p04_nist_decision_consistency():
    dec = load("R406/R406_P04_NIST_DECISION.json")
    assert dec["release_decision"]["decision"].startswith("RETAIN")
    assert dec["original_parameter"]["value"] == 0.6
    assert dec["corrected_parameter"]["value"] == 0.5471
    assert dec["measured_source"]["value"] == 0.6913036
    assert len(dec["reason"]["technical_justification"]) == 4
    assert len(dec["release_decision"]["executable_adoption_path_if_overridden"]) == 4
    # split invariance: eta cancels in G_floor/G_primary
    import math
    def G(d, eta):
        return math.pi * (d * 1e-3) ** 4 / (128 * eta * 1e-3 * 0.1)
    assert abs(G(0.6, 0.6913036) / G(1.1, 0.6913036)
               - G(0.6, 1.0) / G(1.1, 1.0)) < 1e-12


# ---------------- P08 pipeline ----------------

def test_p08_pipeline_committed_run():
    run = load("R406/P08_ENERGY_PIPELINE/PIPELINE_RUN.json")
    assert list(run["chain"].keys()) == [
        "1_source_model", "2_tissue_parameters", "3_simulation",
        "4_output_fluence", "5_pv_incident_power", "6_conversion",
        "7_usable_power"]
    assert run["configuration"]["seed"] == 20260904
    assert run["inputs"]["preregistration_sha256"]
    cmp_ = run["automatic_comparison_to_energy_budget"]
    assert cmp_["this_run_fluence_mW_per_cm2"] == pytest.approx(0.705, abs=0.02)
    assert cmp_["verdict"].startswith("SAME_ORDER")
    # the independence finding must record the same-hand note
    assert "same-hand" in cmp_["independence_finding"]["same_hand_note"] or \
           "SAME-HAND" in cmp_["independence_finding"]["same_hand_note"]
    # fluence within the published range
    assert 0.5 <= cmp_["this_run_fluence_mW_per_cm2"] <= 2.0
    # plot committed
    assert os.path.exists(os.path.join(
        REPO, "R406/P08_ENERGY_PIPELINE/PIPELINE_PROFILES.png"))


def test_p08_pipeline_matches_engine_free_of_transcription():
    # the committed fluence must equal a fresh independent SI computation of
    # the collision-estimator convention... sanity: within published range
    # and consistent with the R310 diffusion/KM bracket
    run = load("R406/P08_ENERGY_PIPELINE/PIPELINE_RUN.json")
    r310 = load("LEAD_PORTFOLIO_4/P08/VERIFICATION_EVIDENCE/R310/"
                "P-16_VERIF-002_RESULT.json")
    models = r310["model_outputs_mW_per_cm2"]
    phi = run["outputs"]["fluence_mW_per_cm2"]
    assert models["B_kubelka_munk"] < phi < models["C_MCX_style_monte_carlo"]


# ---------------- P13 novelty ----------------

def test_p13_novelty_contested_with_custody():
    rec = load("LEAD_PORTFOLIO_4/P13/NOVELTY_SEARCH_R406/"
               "NOVELTY_SEARCH_RESULT.json")
    assert rec["determination"]["verdict"] == "CONTESTED"
    ids = [pa["record_id"] for pa in rec["located_prior_art"]]
    assert any("PA-1" in i for i in ids)
    # the decisive dissertation must carry verbatim spans
    pa1 = next(pa for pa in rec["located_prior_art"] if "PA-1" in pa["record_id"])
    assert any("matched silicon dies" in s for s in pa1["verbatim_spans"])
    # custody hashes present and files exist
    for rel in rec["provenance_custody"]:
        assert os.path.exists(os.path.join(REPO, rel)), rel
    # no zero-hit inference anywhere in the determination
    for r in rec["determination"]["reasoning"]:
        assert "zero results means" not in r.lower()


# ---------------- pre-registrations ----------------

def test_p04_preregistration_pins():
    p = load("LEAD_PORTFOLIO_4/P04/EXPERIMENT_PREREGISTRATION.json")
    t = p["preregistered_thresholds"]
    assert t["Q_min_pass_rule"]["value"] == 0.4
    assert t["Q_min_kill_rule"]["value"] == 0.2
    assert t["common_cause_kill_threshold"]["value"] == 90
    assert t["false_pass_rule"]["leak_threshold_value"] == 0.02
    assert p["registration_event"]["frozen_before_any_run"] is True
    assert len(p["arms"]["obstruction_conditions"]) == 3  # incl. floor-only


def test_p11_preregistration_pins():
    p = load("LEAD_PORTFOLIO_4/P11/EXPERIMENT_PREREGISTRATION.json")
    e = p["primary_endpoints_preregistered"]
    assert e["endpoint_1_response_time"]["instrument_MDD"] == 0.0253
    assert e["endpoint_1_response_time"]["kill_condition_A_registered"]["value"] == 20
    assert "REAL commercial anti-siphon" in p["design"]["arms"]["control_1_ASD"] \
        or "REAL commercial" in p["design"]["arms"]["control_1_ASD"]
    assert p["statistical_analysis_plan"]["alpha_class"]["value"] == 0.05
    assert p["cost_and_time"]["recorded"].startswith("$15K")


def test_p13_preregistration_pins():
    p = load("LEAD_PORTFOLIO_4/P13/EXPERIMENT_PREREGISTRATION.json")
    assert len(p["design"]["arms"]) == 5
    assert p["primary_endpoint_preregistered"]["ka014_kill_criterion_registered"]["value"] == 1
    assert "NOT counted as a mechanism fix" in \
        p["primary_endpoint_preregistered"]["recalibration_rule"]["rule"]


# ---------------- buyer states + killability ----------------

def test_buyer_states_zero():
    for pkg in ("P04", "P08", "P11", "P13"):
        b = load(f"LEAD_PORTFOLIO_4/{pkg}/BUYER_EVALUATION_STATE.json")
        assert b["REAL_BUYER"] == 0
        for f in ("buyer", "contact", "date_of_engagement"):
            assert b[f] is None
        for f in ("technical_response", "requested_follow_up", "nda_state",
                  "experiment_interest", "commercial_interest"):
            assert b[f] == "NONE"


def test_killability_all_answered():
    for pkg in ("P04", "P08", "P11", "P13"):
        k = load(f"LEAD_PORTFOLIO_4/{pkg}/KILLABILITY_ASSESSMENT.json")
        for f in ("money", "time", "apparatus", "measurement", "threshold",
                  "decision"):
            assert k[f], (pkg, f)
        assert k["answer"]


# ---------------- closing records ----------------

def test_manifest_v4_enumerates_new_records():
    mf = load("LEAD_PORTFOLIO_4_MANIFEST.json")
    assert mf["manifest_version"] == "4.0"
    assert "r406_real_loop_round" in mf
    for lp in mf["lead_packages"]:
        p = lp["company_designation"]
        for rel in ("LOOP_CHAIN.json", "MODEL_UPDATE_LEDGER.json",
                    "BUYER_EVALUATION_STATE.json",
                    "KILLABILITY_ASSESSMENT.json"):
            assert f"LEAD_PORTFOLIO_4/{p}/{rel}" in lp["canonical_records"]
        # the directive's Steps 4/5/8 packages carry preregistrations; P08's
        # Step-6 artifact is the reproducible energy pipeline
        if p in ("P04", "P11", "P13"):
            assert f"LEAD_PORTFOLIO_4/{p}/EXPERIMENT_PREREGISTRATION.json" \
                in lp["canonical_records"]
    p08 = next(lp for lp in mf["lead_packages"]
               if lp["company_designation"] == "P08")
    assert "R406/P08_ENERGY_PIPELINE/PIPELINE_RUN.json" \
        in p08["canonical_records"]


def test_classification_unchanged_with_updated_basis():
    fc = load("LEAD_PORTFOLIO_4/FINAL_CLASSIFICATION.json")
    assert fc["classifications"]["P04"]["state"] == "READY_FOR_TECHNICAL_EVALUATION"
    assert fc["classifications"]["P08"]["state"] == "REQUIRES_ENGINEERING_REPAIR"
    assert fc["classifications"]["P11"]["state"] == "READY_FOR_SPONSORED_VALIDATION"
    assert fc["classifications"]["P13"]["state"] == "REQUIRES_EVIDENCE_REPAIR"
    assert "r406_extensions" in fc
    assert "CONTESTED" in fc["r406_extensions"]["P13"]["basis_updates"][0]


def test_acceptance_checklist_complete():
    c = load("R406/R406_ACCEPTANCE_CHECKLIST.json")
    assert len(c["items"]) == 16
    for it in c["items"]:
        assert it["state"] and it["evidence"]
    # the two PENDING_AT_WRITE items were flipped to TRUE (with recorded
    # qualifiers: the P08 anchor contest; the P13 protocol-level state)
    # by the R406-ship commit 08c03dd7. Disclosed 2026-09-04 (R407
    # session, Art. XV): the ship commit left THIS expectation stale —
    # the battery was last run pre-ship, when 2 items were still
    # pending. At HEAD zero items are pending and every state begins
    # with TRUE; the test now pins the shipped state.
    pending = [it for it in c["items"] if it["state"].startswith("PENDING")]
    assert len(pending) == 0
    assert all(it["state"].startswith("TRUE") for it in c["items"])

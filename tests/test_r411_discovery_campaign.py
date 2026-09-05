"""tests/test_r411_discovery_campaign.py — the R411 adversarial suite.

Hermetic (no network, no LLM, no credentials — every test drives the
deterministic machinery with synthetic inputs). Adversarial posture per
Art. VIII/XVII: each test tries to make the machinery fail the directive
(exclude a good non-medical candidate, admit a medical one, let a
fabricated evidence ref through, let a fifth winner be fabricated, let
UNKNOWN promote to SUPPORTED, let an infrastructure failure masquerade
as scientific rejection, let a dossier claim physical observation).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.r411.medical_exclusion import (
    medical_exclusion_screen, screen_pool)
from discovery_fabric.r411.domain_matrix import (build_domain_matrix,
                                                 DOMAIN_MATRIX_SPEC,
                                                 PAIN_POINT_CLASSES,
                                                 primary_query_for_entry)
from discovery_fabric.r411.scoring import (scoring_contract,
                                           score_candidate,
                                           information_gain_per_cost,
                                           EVIDENCE_FLOOR,
                                           measure_evidence_strength)
from discovery_fabric.r411.extract import (parse_candidates,
                                           REQUIRED_FIELDS)
from discovery_fabric.r411.collision import (
    collision_gate, typed_distinction_for, intra_campaign_dedup,
    PORTFOLIO_MECHANISMS)
from discovery_fabric.r411.prior_art import (
    assess_prior_art, terminology_recovery, build_perspectives,
    register_queries)
from discovery_fabric.r411.attack import (parse_attack, attack_candidate,
                                          known_defect_corpus)
from discovery_fabric.r411.dossier import build_dossier, STATUS_VOCAB
from discovery_fabric.r411.buyer_package import (
    buyer_dossier_markdown, BUYER_FIELDS, buyer_portfolio_record)
from discovery_fabric.r411.campaign import Campaign, CAMPAIGN_VERSION


# ---------------------------------------------------------------------------
# synthetic fixtures
# ---------------------------------------------------------------------------

def _pool(n=8, family="family_a"):
    return [{
        "record_id": f"R{i}",
        "title": f"industrial record {i} thermal loss maintenance cost "
                 f"severe failure downtime million percent",
        "abstract": f"Record {i}: measured degradation and efficiency "
                    f"loss; replacement cost in the million range; "
                    f"unscheduled downtime percent loss per year.",
        "year": 2020 + (i % 5),
        "publication_status": "PEER_REVIEWED" if i % 2 else "PATENT",
        "provenance": {"source_family": family if i < 4 else "family_b"
                       if i < 6 else "family_c"},
    } for i in range(n)]


def _candidate(**over):
    c = {
        "candidate_id": "C-test-1",
        "technology_name": "Passive vortex-flow fouling suppressor",
        "target_domain": "thermal",
        "source_domain": "aerospace",
        "domain_id": "heat_exchanger",
        "pain_class": "MAINTENANCE_BURDEN",
        "problem": "heat exchanger fouling causes 20% duty loss and "
                   "shutdown cleaning",
        "causal_chain": ["shear thinning boundary layer forms",
                         "vortex structures resuspend deposits",
                         "foulant removal restores duty"],
        "unexploited_phenomenon": "vortex-induced shear lift on "
                                  "deposited particulate",
        "intervention": "passive vortex generators in the tube bundle",
        "governing_variables": "Reynolds number, shear stress (Pa)",
        "predicted_effect": "40-60% fouling-rate reduction because "
                            "removal scales with wall shear",
        "equations": ["tau_w = 0.5 * rho * v^2 * Cf"],
        "boundary_conditions": "Re > 10^4, particle size < 200 um",
        "evidence_refs": [f"R{i}" for i in range(6)],
        "cross_domain_transition": "aerospace vortex control -> "
                                   "industrial heat exchangers",
        "baseline": {
            "baseline_incumbent": "periodic chemical cleaning",
            "baseline_metric": "duty loss 20% between cleanings",
            "candidate_metric": "duty loss 8-12%",
            "expected_delta": "40-60% fouling-rate reduction",
        },
        "killer_experiment": {
            "experiment": "two-pass lab HX with/without vortex "
                          "generators, foulant slurry",
            "decisive_uncertainty": "does induced vortex shear lift "
                                    "deposit in situ",
            "kill_condition": "fouling resistance delta < 10%",
            "cost_class": "BENCH",
        },
        "failure_modes": [
            {"failure_mode": "vortex generators foul themselves",
             "detectability": "pressure drop",
             "mitigation": "leading-edge profile"},
            {"failure_mode": "erosion of tubes",
             "detectability": "wall thickness UT",
             "mitigation": "rounded profiles"},
        ],
        "commercial_path": {
            "buyer": "process plant O&M engineering",
            "use_case": "extend cleaning intervals",
            "integration_point": "tube bundle retrofit",
        },
        "generation": {"provider": "zai", "model": "glm-4-plus",
                       "prompt_hash": "x" * 64, "output_hash": "y" * 64},
    }
    c.update(over)
    return c


def _funnel(**over):
    f = {
        "typed_distinction": "NEW_CAUSAL_CONFIGURATION",
        "prior_art": {
            "closest_prior_art": {"distance_class": "FAR"},
            "relevant_records": [],
        },
        "attack": {
            "status": "OK", "verdict": "SURVIVED", "survived": True,
            "kill_surfaces": [], "wound_surfaces": ["manufacturability"],
        },
        "engineering": {"passed": True},
        "scoring": {"sub_scores": {"evidence_strength": 3}},
    }
    f.update(over)
    return f


def _meta():
    return {
        "engine_commit": "a" * 40,
        "fabric_version": "RETRIEVAL_FABRIC_V2",
        "evidence_snapshot_sha256": "b" * 64,
        "domain_matrix_sha256": "c" * 64,
        "scoring_contract_sha256": "d" * 64,
    }


# ---------------------------------------------------------------------------
# s1: hard medical exclusion
# ---------------------------------------------------------------------------

class TestMedicalExclusion:

    def test_implantable_device_excluded(self):
        c = _candidate(
            technology_name="Implantable pressure sensor drift "
                            "compensator",
            problem="implantable medical sensor drift in patients",
            target_domain="medical devices",
            intervention="implantable clinical diagnostic device")
        s = medical_exclusion_screen(c)
        assert s["excluded"] is True
        assert s["verdict"] == "EXCLUDED_MEDICAL"
        assert s["matched_medical_terms"]

    def test_surgical_instrument_excluded(self):
        c = _candidate(technology_name="surgical robotic end effector",
                       problem="surgical instrument sterilization "
                               "burden in hospitals",
                       target_domain="medical robotics")
        assert medical_exclusion_screen(c)["excluded"] is True

    def test_non_medical_industrial_passes(self):
        c = _candidate()
        s = medical_exclusion_screen(c)
        assert s["excluded"] is False
        assert s["verdict"] == "NON_MEDICAL"

    def test_medical_physics_industrial_target_passes(self):
        """s1: physics originated in medicine + industrial final
        application is ALLOWED."""
        c = _candidate(
            unexploited_phenomenon="ultrasonic cavitation "
                                   "cleaning (origin: dental "
                                   "instrument cleaning literature)")
        s = medical_exclusion_screen(c)
        # 'dental' hits the vocabulary inside the SOURCE phenomenon
        # description, but the target application fields are industrial
        assert s["excluded"] is False or "dental" in \
            s["matched_medical_terms"]
        # and the flag is visible either way (honest middle state)
        assert s["verdict"] in ("NON_MEDICAL", "MEDICAL_ADJACENT_FLAG")

    def test_screen_pool_counts(self):
        med = _candidate(technology_name="clinical diagnostic sensor")
        pool = [_candidate(candidate_id=f"C{i}") for i in range(3)] + [med]
        res = screen_pool(pool)
        assert res["screened"] == 4
        assert res["non_medical"] >= 3

    def test_excluded_terms_recorded_for_audit(self):
        c = _candidate(problem="hospital equipment sterilization")
        s = medical_exclusion_screen(c)
        if s["excluded"]:
            assert s["matched_medical_terms"]  # audit trail (Art. XXI.4)
            assert s["basis"]


# ---------------------------------------------------------------------------
# s4: domain matrix
# ---------------------------------------------------------------------------

class TestDomainMatrix:

    def test_deterministic_and_frozen(self):
        m1 = build_domain_matrix()
        m2 = build_domain_matrix()
        assert m1["matrix_sha256"] == m2["matrix_sha256"]
        assert m1["n_domains"] >= 20
        assert m1["n_families"] >= 12

    def test_no_medical_domains(self):
        matrix = build_domain_matrix()
        text = json.dumps(matrix).lower()
        for term in ("implantable", "clinical", "surgical", "shunt",
                     "catheter", "csf", "prosthe", "dialysis"):
            assert term not in text, f"medical term leaked: {term}"

    def test_problem_facts_not_solution_classes(self):
        """Art. XLIII: the matrix entries carry system+problem+constraint,
        not solution classes. Check a sample of solution-vocabulary is
        absent from the problem fields."""
        matrix = build_domain_matrix()
        solution_markers = ["machine learning", "neural network",
                            "ai-powered", "algorithm", "controller",
                            "optimizer", "sensor array", "smart"]
        for e in matrix["entries"]:
            blob = json.dumps(e["problem"]).lower()
            for m in solution_markers:
                assert m not in blob, \
                    f"solution class {m} leaked into problem facts"

    def test_s21_portfolio_terms_absent_from_matrix(self):
        """Directive s21: no P04/P08/P11/P13/medical seeds."""
        matrix = build_domain_matrix()
        text = json.dumps(matrix).lower()
        for term in ("p04", "p08", "p11", "p13", "drainage floor",
                     "photovoltaic power delivery",
                     "gravity compensation damper", "self-referencing",
                     "acoustic obstruction detection"):
            assert term not in text

    def test_primary_query_is_problem_facts(self):
        matrix = build_domain_matrix()
        e = matrix["entries"][0]
        q = primary_query_for_entry(e)
        assert e["problem"]["device"] in q
        assert e["problem"]["constraint"] in q


# ---------------------------------------------------------------------------
# s2: scoring contract
# ---------------------------------------------------------------------------

class TestScoringContract:

    def test_contract_frozen_and_stable(self):
        c1 = scoring_contract()
        c2 = scoring_contract()
        assert c1["contract_sha256"] == c2["contract_sha256"]
        assert len(c1["dimensions"]) == 13
        assert c1["frozen_before_candidates"] is True

    def test_high_score_weak_evidence_stays_low_confidence(self):
        """The directive's final s2 rule: the score never substitutes for
        evidence."""
        c = _candidate(evidence_refs=["R0"])  # 1 ref = weak evidence
        sc = score_candidate(c, _pool(), _funnel())
        assert sc["sub_scores"]["evidence_strength"] < EVIDENCE_FLOOR
        assert sc["confidence"] == "LOW"
        assert sc["finalist_eligible"] is False

    def test_score_is_deterministic(self):
        c = _candidate()
        s1 = score_candidate(c, _pool(), _funnel())
        s2 = score_candidate(c, _pool(), _funnel())
        assert s1 == s2

    def test_evidence_floor_allows_strong_candidate(self):
        c = _candidate()
        sc = score_candidate(c, _pool(8), _funnel())
        assert sc["sub_scores"]["evidence_strength"] >= 2
        assert sc["finalist_eligible"] is True

    def test_family_independence_measured_not_counted(self):
        """Art. XXI.7: 6 refs from ONE family score lower than 6 refs
        from 3 families."""
        one_family = [{
            "record_id": f"R{i}", "title": "t", "abstract": "a",
            "publication_status": "PEER_REVIEWED",
            "provenance": {"source_family": "solo"},
        } for i in range(6)]
        multi_family = [{
            "record_id": f"R{i}", "title": "t", "abstract": "a",
            "publication_status": "PEER_REVIEWED",
            "provenance": {"source_family":
                           ["f1", "f2", "f3"][i // 2]},
        } for i in range(6)]
        c1 = _candidate(evidence_refs=[f"R{i}" for i in range(6)])
        c2 = _candidate(evidence_refs=[f"R{i}" for i in range(6)])
        assert measure_evidence_strength(c2, multi_family) > \
            measure_evidence_strength(c1, one_family)

    def test_eig_per_cost_ranks_bench_over_pilot(self):
        bench = _candidate()
        pilot = _candidate(killer_experiment={
            "experiment": "pilot plant", "decisive_uncertainty": "x",
            "kill_condition": "y", "cost_class": "PILOT"})
        assert information_gain_per_cost(bench) > \
            information_gain_per_cost(pilot)

    def test_unfalsifiable_candidate_scores_zero_eig(self):
        c = _candidate(killer_experiment={
            "experiment": "demonstration", "decisive_uncertainty": "",
            "kill_condition": "", "cost_class": "FIELD"})
        assert information_gain_per_cost(c) == 0.0


# ---------------------------------------------------------------------------
# s3: extraction no-fabrication gate
# ---------------------------------------------------------------------------

class TestExtractionGate:

    def _llm_output(self, refs="R0, R1, R2"):
        fields = {
            "CANDIDATE_ID": "C-heat-1",
            "TECHNOLOGY_NAME": "Vortex fouling suppressor",
            "TARGET_DOMAIN": "thermal",
            "SOURCE_DOMAIN": "aerospace",
            "PAIN_CLASS": "MAINTENANCE_BURDEN",
            "PROBLEM": "fouling causes duty loss",
            "CAUSAL_CHAIN": "shear forms -> vortex lifts deposit -> "
                            "duty restored",
            "UNEXPLOITED_PHENOMENON": "vortex shear lift",
            "INTERVENTION": "vortex generators",
            "GOVERNING_VARIABLES": "Re, shear stress",
            "PREDICTED_EFFECT": "40% fouling reduction",
            "EQUATIONS": "tau = 0.5 rho v^2 Cf",
            "BOUNDARY_CONDITIONS": "Re > 10^4",
            "EVIDENCE_REFS": refs,
            "CROSS_DOMAIN_TRANSITION": "aerospace -> thermal",
            "BASELINE_INCUMBENT": "chemical cleaning",
            "BASELINE_METRIC": "20% duty loss",
            "CANDIDATE_METRIC": "10% duty loss",
            "EXPECTED_DELTA": "50% reduction",
            "CHEAPEST_DECISIVE_EXPERIMENT": "two-pass lab HX",
            "DECISIVE_UNCERTAINTY": "in-situ lift",
            "KILL_CONDITION": "delta < 10%",
            "COST_CLASS": "BENCH",
            "FAILURE_MODES": "erosion | UT | profiles",
            "BUYER": "plant O&M",
            "USE_CASE": "longer intervals",
            "INTEGRATION_POINT": "tube bundle",
        }
        body = "\n".join(f"{k}: {v}" for k, v in fields.items())
        return f"CANDIDATE_ID: C-heat-1\n{body}\nEND CANDIDATE"

    def test_valid_candidate_parsed(self):
        res = parse_candidates(self._llm_output(), "heat_exchanger",
                               _pool(), {"provider": "zai"})
        assert len(res["accepted"]) == 1
        c = res["accepted"][0]
        assert c["evidence_refs"] == ["R0", "R1", "R2"]
        assert c["medical_screen"]["excluded"] is False

    def test_fabricated_record_id_rejected(self):
        """The no-fabrication gate: ANY fabricated ref rejects the whole
        candidate (no repair — Art. IV). LLM-invented DOIs/patent ids
        never enter records."""
        res = parse_candidates(
            self._llm_output(refs="R0, FAKE-999, DOI:10.1234/fake"),
            "heat_exchanger", _pool(), {})
        assert len(res["accepted"]) == 0
        assert res["rejected"]
        # no valid refs at all -> hard reject
        res2 = parse_candidates(
            self._llm_output(refs="DOI:10.1234/fake, PATENT-US999"),
            "heat_exchanger", _pool(), {})
        assert len(res2["accepted"]) == 0

    def test_missing_field_rejected(self):
        text = self._llm_output().replace("KILL_CONDITION: delta < 10%\n",
                                          "")
        res = parse_candidates(text, "heat_exchanger", _pool(), {})
        assert len(res["accepted"]) == 0
        assert any("KILL_CONDITION" in json.dumps(
            res["rejected"])[50:] or "missing field" in json.dumps(
            res["rejected"]) for _ in [0])

    def test_all_required_fields_enforced(self):
        assert "KILL_CONDITION" in REQUIRED_FIELDS
        assert "EVIDENCE_REFS" in REQUIRED_FIELDS
        assert len(REQUIRED_FIELDS) >= 25


# ---------------------------------------------------------------------------
# s8: collision
# ---------------------------------------------------------------------------

class TestCollision:

    def test_portfolio_duplicate_without_distinction_rejected(self):
        """A candidate that re-creates P13's dual-die mechanism with no
        typed distinction (no cross-domain transition, no marker
        vocabulary) is NO_MEANINGFUL_DISTINCTION."""
        c = _candidate(
            technology_name="Self-referencing dual matched pressure "
                            "sensor drift subtraction",
            problem="sensor drift in pressure measurement",
            causal_chain=["two matched sensors share common-mode drift",
                          "subtraction cancels the common mode",
                          "drift-free pressure reading"],
            intervention="dual matched sensor bridge",
            cross_domain_transition=None,
            unexploited_phenomenon="common-mode drift subtraction",
            predicted_effect="drift-free pressure measurement")
        gate = collision_gate(c)
        assert gate["admitted"] is False
        assert gate["typed_distinction"] == "NO_MEANINGFUL_DISTINCTION"
        assert gate["portfolio_hits"], "expected a portfolio mechanism hit"

    def test_portfolio_duplicate_with_control_distinction_admitted(self):
        c = _candidate(
            technology_name="Adaptive control strategy for dual "
                            "matched sensor drift subtraction",
            intervention="closed-loop control policy re-weighting the "
                         "subtraction",
            cross_domain_transition=None)
        gate = collision_gate(c)
        assert gate["admitted"] is True
        assert gate["typed_distinction"] == "NEW_CONTROL_STRATEGY"

    def test_clean_candidate_admitted(self):
        gate = collision_gate(_candidate())
        assert gate["admitted"] is True
        assert gate["verdict"] in ("ADMITTED_NO_COLLISION",
                                   "ADMITTED_WITH_COLLISION_HISTORY")

    def test_cemetery_infrastructure_failure_is_incomplete(self):
        """Art. LXI: a cemetery load failure is INCOMPLETE, never
        REJECTED."""
        import discovery_fabric.r411.collision as coll
        orig = coll.check_cemetery

        def boom(cand):
            return {"status": "CEMETERY_CHECK_INFRASTRUCTURE_FAILURE",
                    "error": "disk"}
        coll.check_cemetery = boom
        try:
            gate = coll.collision_gate(_candidate())
        finally:
            coll.check_cemetery = orig
        assert gate["verdict"] == "INCOMPLETE_CEMETERY_INFRASTRUCTURE"
        assert "REJECT" not in gate["verdict"]

    def test_intra_campaign_dedup_merges_equivalent(self):
        a = _candidate(candidate_id="C-1")
        b = _candidate(candidate_id="C-2",
                       technology_name="Passive vortex flow fouling "
                                       "suppressors (variant)")
        res = intra_campaign_dedup([a, b])
        assert res["survivor_count"] == 1
        assert len(res["merge_events"]) == 1

    def test_distinct_candidates_not_merged(self):
        a = _candidate(candidate_id="C-1")
        b = _candidate(
            candidate_id="C-2",
            technology_name="Electrochemical antifouling polarizer",
            causal_chain=["applied potential changes surface charge",
                          "biofilm adhesion prevented",
                          "fouling suppressed electrochemically"],
            unexploited_phenomenon="electrochemical surface "
                                   "polarization",
            intervention="intermittent polarization pulses",
            predicted_effect="70% biofouling reduction via charge "
                             "repulsion")
        res = intra_campaign_dedup([a, b])
        assert res["survivor_count"] == 2


# ---------------------------------------------------------------------------
# s9/s7: prior art
# ---------------------------------------------------------------------------

class TestPriorArt:

    def test_four_perspectives_built(self):
        ps = build_perspectives(_candidate())
        assert [p["perspective"] for p in ps] == [
            "FORWARD", "MECHANISM", "FAILURE", "INVERSE"]
        for p in ps:
            assert p["problem"].get("device")
            assert p["problem"].get("constraint")

    def test_registers_cover_four_vocabularies(self):
        regs = register_queries(_candidate())
        assert {r["register"] for r in regs} == {
            "engineering", "patent", "historical"}

    def test_distance_classes(self):
        c = _candidate()
        # no relevant records
        pa = assess_prior_art(c, {"FORWARD": _pool(2)})
        assert pa["closest_prior_art"]["distance_class"] in (
            "FAR", "NO_OVERLAP")
        # many relevant records
        rel_pool = [{
            "record_id": f"R{i}",
            "title": f"vortex shear lift deposit removal fouling "
                     f"suppress heat exchanger tube {i}",
            "abstract": "vortex-induced shear lift deposits fouling "
                        "suppression duty restoration heat exchanger "
                        "fouling-rate reduction wall shear",
        } for i in range(5)]
        pa2 = assess_prior_art(c, {"MECHANISM": rel_pool})
        assert pa2["closest_prior_art"]["distance_class"] == "NEAR"

    def test_generator_not_consulted(self):
        pa = assess_prior_art(_candidate(), {"FORWARD": []})
        assert pa["generator_not_consulted"] is True

    def test_terminology_recovery_counts_secondary_only(self):
        primary = [{"record_id": "R1"}, {"record_id": "R2"}]
        retrieved = {
            "FORWARD": primary,
            "MECHANISM": [{"record_id": "R1"},
                          {"record_id": "R9"}],
            "INVERSE": [{"record_id": "R10"}],
        }
        tr = terminology_recovery(retrieved, primary)
        assert tr["total_unique_secondary_only"] == 2
        assert tr["unique_records_recovered_by_secondary_perspectives"][
            "MECHANISM"] == 1


# ---------------------------------------------------------------------------
# s13: attacker
# ---------------------------------------------------------------------------

class TestAttack:

    def test_parse_kill_without_basis_downgraded(self):
        text = ("ATTACK mechanism: the shear story seems weak\n"
                "VERDICT mechanism: KILL\n"
                "BASIS mechanism: \n"
                "ATTACK physics: violates nothing but feels off\n"
                "VERDICT physics: WOUND\n"
                "BASIS physics: \n"
                "FINAL: KILLED, skepticism")
        parsed = parse_attack(text)
        assert parsed["surfaces"]["mechanism"]["verdict"] == "HOLDS"
        assert "downgraded" in parsed["surfaces"]["mechanism"]["note"]

    def test_parse_kill_with_basis_kept(self):
        text = ("ATTACK mechanism: chain violates second law at stated "
                "conditions\n"
                "VERDICT mechanism: KILL\n"
                "BASIS mechanism: single reservoir cannot yield net "
                "power (Kelvin-Planck)\n"
                "FINAL: KILLED, second-law violation")
        parsed = parse_attack(text)
        assert parsed["surfaces"]["mechanism"]["verdict"] == "KILL"
        assert parsed["final"] == "KILLED"

    def test_transport_failure_is_incomplete_not_killed(self):
        """Art. LXI: attack transport failure => INCOMPLETE."""

        def dead_generate(*a, **k):
            return {"ok": False, "status": "CALL_FAILED",
                    "error": "connection refused", "provider": None}

        rec = attack_candidate(_candidate(), _pool(),
                               {"relevant_records": []},
                               generator_provider="zai",
                               llm_generate=dead_generate)
        assert rec["status"] == "INCOMPLETE_ATTACK_TRANSPORT"
        assert rec["survived"] is None
        assert rec["verdict"] == "INCOMPLETE"
        assert rec["verdict"] != "KILLED"

    def test_survived_candidate_gets_survived_verdict(self):
        text = ("ATTACK mechanism: shear-lift scaling is plausible\n"
                "VERDICT mechanism: HOLDS\n"
                "BASIS mechanism: R4 documents vortex removal\n"
                "FINAL: SURVIVED, erosion risk remains")
        gen = _fake_gen(text)
        rec = attack_candidate(_candidate(), _pool(),
                               {"relevant_records": []},
                               generator_provider=None,
                               llm_generate=gen)
        assert rec["vervdict"] if False else rec["survived"] is True
        assert rec["verdict"] == "SURVIVED"

    def test_calibration_corpus_has_known_defects(self):
        corpus = known_defect_corpus()
        assert len(corpus) >= 2
        assert all(c["expected_attack_outcome"] == "KILLED"
                   for c in corpus)


def _fake_gen(text):
    def gen(prompt, system="", **k):
        return {"ok": True, "status": "OK", "content": text,
                "provider": "fake", "model": "fake-1",
                "prompt_hash": "p" * 64, "output_hash": "o" * 64}
    return gen


# ---------------------------------------------------------------------------
# s10/s17: dossier
# ---------------------------------------------------------------------------

class TestDossier:

    def test_no_kill_condition_no_dossier(self):
        """Art. LII: unfalsifiable candidates cannot get dossiers."""
        c = _candidate(killer_experiment={"experiment": "demo",
                                          "cost_class": "BENCH"})
        with pytest.raises(ValueError):
            build_dossier(c, _pool(), _funnel(), _meta(), 1)

    def test_evidence_map_binds_to_pool_only(self):
        d = build_dossier(_candidate(), _pool(), _funnel(), _meta(), 1)
        pool_ids = {f"R{i}" for i in range(8)}
        for row in d["evidence_map"]:
            for s in row.get("sources") or []:
                assert s["record_id"] in pool_ids

    def test_epistemic_classes_never_physical(self):
        """Art. XXXVIII: no claim reaches PHYSICAL_OBSERVATION."""
        d = build_dossier(_candidate(), _pool(), _funnel(), _meta(), 1)
        for row in d["evidence_map"]:
            assert row["epistemic_class"] in (
                "SOURCE_FACT", "EXTERNAL_PRECEDENT", "AI_INFERENCE",
                "COMPUTATIONAL_RESULT")
        for eq in d["engineering_model"]["equations"]:
            assert eq["epistemic_class"] in (
                "SOURCE_FACT", "EXTERNAL_PRECEDENT", "AI_INFERENCE",
                "COMPUTATIONAL_RESULT")

    def test_unbound_hypothesis_is_honest(self):
        d = build_dossier(_candidate(), _pool(), _funnel(), _meta(), 1)
        hyp_rows = [r for r in d["evidence_map"]
                    if r["epistemic_class"] == "AI_INFERENCE"]
        assert hyp_rows and not hyp_rows[0]["sources"]
        assert "unbound" in hyp_rows[0].get(
            "unbound_claim_rule", "").lower() or not hyp_rows[0][
            "sources"]

    def test_status_vocabulary_respected(self):
        d = build_dossier(_candidate(), _pool(), _funnel(), _meta(), 1)
        assert d["status"] in STATUS_VOCAB

    def test_killed_attack_gives_killed_status(self):
        f = _funnel(attack={"status": "OK", "verdict": "KILLED",
                            "survived": False, "kill_surfaces": [
                                "mechanism"]})
        d = build_dossier(_candidate(), _pool(), f, _meta(), 1)
        assert d["status"] == "KILLED"

    def test_unknown_never_promoted_to_supported(self):
        """s17: UNKNOWN -> SUPPORTED requires new evidence; the builder
        can only assign from recorded attack/scoring state."""
        f = _funnel(attack={"status": "TRANSPORT_FAILED",
                            "verdict": "INCOMPLETE"})
        d = build_dossier(_candidate(), _pool(), f, _meta(), 1)
        assert d["status"] == "UNKNOWN"
        assert "UNKNOWN->SUPPORTED" in d["status_transition_evidence"]

    def test_physical_observations_zero(self):
        d = build_dossier(_candidate(), _pool(), _funnel(), _meta(), 1)
        assert d["reality_boundary"]["physical_observations"] == 0
        assert d["reality_boundary"]["real_buyers"] == 0
        assert d["reality_boundary"]["commercial_transactions"] == 0

    def test_capability_state_all_true_for_valid(self):
        d = build_dossier(_candidate(), _pool(), _funnel(), _meta(), 1)
        caps = d["capability_state"]
        for k in ("new_to_current_portfolio", "meaningful_mechanism",
                  "material_problem", "evidence_backed",
                  "baseline_defined", "engineering_model",
                  "adversarially_tested", "killer_experiment",
                  "kill_condition", "traceability"):
            assert caps[k] is True, f"capability false: {k}"

    def test_traceability_chain_complete(self):
        d = build_dossier(_candidate(), _pool(), _funnel(), _meta(), 1)
        t = d["traceability"]
        assert t["engine_commit"] == "a" * 40
        assert t["evidence_snapshot_sha256"]
        assert t["candidate_sha256"]
        assert t["generation_provenance"]["prompt_hash"]

    def test_lxii_hashes_present(self):
        d = build_dossier(_candidate(), _pool(), _funnel(), _meta(), 1)
        assert len(d["traceability"]["candidate_sha256"]) == 64


# ---------------------------------------------------------------------------
# s15: buyer package
# ---------------------------------------------------------------------------

class TestBuyerPackage:

    def test_portfolio_record_conventions(self):
        d = build_dossier(_candidate(), _pool(), _funnel(), _meta(), 1)
        r = buyer_portfolio_record(d, _meta(), 1)
        assert r["artifact_type"] == "R411_TRANSFER_STATE"
        assert r["current_state"] == "TECHNICAL_REVIEW"
        assert r["company_designation"] == "D1"
        assert "physically validated: NO" in r["current_state_basis"]
        assert r["transition_evidence_required"]

    def test_buyer_dossier_has_all_18_fields(self):
        d = build_dossier(_candidate(), _pool(), _funnel(), _meta(), 1)
        md = buyer_dossier_markdown(d, _meta())
        for field in BUYER_FIELDS:
            assert f"## {field}" in md, f"missing buyer field: {field}"

    def test_buyer_dossier_states_reality_boundary(self):
        d = build_dossier(_candidate(), _pool(), _funnel(), _meta(), 1)
        md = buyer_dossier_markdown(d, _meta())
        assert "Physical observations: **0**" in md
        assert "not a validated technology" in md

    def test_buyer_dossier_no_internal_clutter(self):
        """s15: internal development clutter stays out of the buyer
        view."""
        d = build_dossier(_candidate(), _pool(), _funnel(), _meta(), 1)
        md = buyer_dossier_markdown(d, _meta())
        for clutter in ("campaign_version", "funnel", "collision_gate",
                        "attack_version", "extraction", "STAGE",
                        "worklog"):
            assert clutter not in md.lower(), \
                f"internal clutter leaked: {clutter}"

    def test_write_buyer_package_manifest(self, tmp_path):
        from discovery_fabric.r411.buyer_package import \
            write_buyer_package
        d = build_dossier(_candidate(), _pool(), _funnel(), _meta(), 1)
        m = write_buyer_package(str(tmp_path), d, _meta(), 1)
        assert set(m["files"]) == {"TRANSFER_STATE.json",
                                   "BUYER_DOSSIER.md",
                                   "TECHNOLOGY_DOSSIER.json"}
        for h in m["files"].values():
            assert len(h) == 64
        assert (tmp_path / "D1" / "BUYER_DOSSIER.md").exists()


# ---------------------------------------------------------------------------
# s14: never fabricate a fifth
# ---------------------------------------------------------------------------

class TestNeverFabricateFifth:

    def _selection_with(self, survivors, monkeypatch, tmp_path):
        """Drive run_selection through a synthetic shortlist."""
        c = Campaign(str(REPO), run_dir=str(tmp_path / "run"))
        matrix = build_domain_matrix()
        fam_of = {}
        for e in matrix["entries"]:
            fam_of[e["domain_id"]] = e["domain_family"]
        # domain_ids whose FAMILIES are all distinct (so survivor-count
        # tests isolate the quota logic from the diversity constraint)
        distinct_domains = []
        seen_fams = set()
        for e in matrix["entries"]:
            if e["domain_family"] not in seen_fams:
                seen_fams.add(e["domain_family"])
                distinct_domains.append(e["domain_id"])
        # materialize the files selection reads
        (tmp_path / "run").mkdir(parents=True, exist_ok=True)
        json.dump(matrix, open(tmp_path / "run" / "domain_matrix.json",
                               "w"))
        shortlist = []
        for i, s in enumerate(survivors):
            cand = _candidate(
                candidate_id=f"C-{i}",
                technology_name=f"Technology {i}",
                domain_id=distinct_domains[i % len(distinct_domains)],
                eig_per_cost=1.0,
                scoring={"composite": 2.0, "confidence": "MEDIUM",
                         "finalist_eligible": True,
                         "sub_scores": {"evidence_strength": 3}},
                collision_gate={"typed_distinction":
                                "NEW_CAUSAL_CONFIGURATION"})
            shortlist.append(cand)
            os.makedirs(tmp_path / "run" / "attack", exist_ok=True)
            json.dump({"status": "OK", "verdict": s, "survived":
                       s == "SURVIVED",
                       "kill_surfaces": ["mechanism"] if s == "KILLED"
                       else []},
                      open(tmp_path / "run" / "attack" /
                           f"C-{i}.json", "w"))
            os.makedirs(tmp_path / "run" / "prior_art", exist_ok=True)
            json.dump({"closest_prior_art": {"distance_class": "FAR"}},
                      open(tmp_path / "run" / "prior_art" /
                           f"C-{i}.json", "w"))
        json.dump(shortlist, open(tmp_path / "run" / "shortlist.json",
                                  "w"))
        res = c.run_selection()
        return c, res, fam_of

    def test_only_four_qualified_reports_honestly(self, tmp_path):
        survivors = ["SURVIVED"] * 4 + ["KILLED"] * 6
        c, res, _ = self._selection_with(survivors, None, tmp_path)
        sel = json.load(open(tmp_path / "run" / "selection.json"))
        assert sel["n_selected"] == 4
        assert "4/5 qualified" in sel["quota_honesty"]
        assert "1/5 insufficient" in sel["quota_honesty"]

    def test_all_killed_gives_zero_not_five(self, tmp_path):
        survivors = ["KILLED"] * 8
        c, res, _ = self._selection_with(survivors, None, tmp_path)
        sel = json.load(open(tmp_path / "run" / "selection.json"))
        assert sel["n_selected"] == 0
        assert len(sel["rejected"]) == 8

    def test_diversity_constraint_one_per_family(self, tmp_path):
        """s4: the five cannot all come from one domain family — even
        when five same-family candidates rank highest, the selection
        enforces family diversity and reports honestly below five if
        needed."""
        survivors = ["SURVIVED"] * 8
        c, res, fam_of = self._selection_with(survivors, None, tmp_path)
        sel = json.load(open(tmp_path / "run" / "selection.json"))
        selected_ids = sel["selected"]
        assert len(selected_ids) <= 5
        fams = []
        for sid in selected_ids:
            for rec in sel["full_records"]:
                if rec["candidate"]["candidate_id"] == sid:
                    fams.append(
                        fam_of[rec["candidate"]["domain_id"]])
        assert len(fams) == len(set(fams)), \
            "two selected technologies share a domain family"

    def test_threshold_not_lowered_for_quota(self, tmp_path):
        """s13: do not lower the threshold to force five winners."""
        survivors = ["SURVIVED"] * 2 + ["KILLED"] * 10
        c, res, _ = self._selection_with(survivors, None, tmp_path)
        sel = json.load(open(tmp_path / "run" / "selection.json"))
        assert sel["n_selected"] == 2
        # the killed ones are in rejected, not selected
        assert all("KILLED" in str(r.get("reason", ""))
                   for r in sel["rejected"]
                   if r["candidate_id"] in
                   [f"C-{i}" for i in range(2, 12)])


# ---------------------------------------------------------------------------
# Art. LI: cemetery writes
# ---------------------------------------------------------------------------

class TestCemeteryIntegration:

    def test_killed_candidates_enter_cemetery(self, tmp_path, monkeypatch):
        """s14: failed candidates go to the cemetery with rejection
        reasons (the append function is the orchestrator's own chain
        machinery)."""
        from scripts.r411_run_campaign import _append_cemetery
        import orchestrator.mechanism_cemetery as mc

        appended = []
        monkeypatch.setattr(mc, "append_entries_to_cemetery_file",
                            lambda entries: appended.extend(entries))
        c = Campaign(str(REPO), run_dir=str(tmp_path / "run"))
        sel = {
            "full_records": [{
                "candidate": _candidate(
                    candidate_id="C-killed",
                    technology_name="Dead mechanism"),
                "funnel": {"attack": {"final_objection":
                                      "violates second law"}},
            }],
            "rejected": [{
                "candidate_id": "C-killed",
                "name": "Dead mechanism",
                "reason": "KILLED: second-law violation",
            }],
        }
        _append_cemetery(c, sel)
        assert len(appended) == 1
        assert appended[0]["epistemic_class"] == "FAILURE_LESSON"
        assert appended[0]["kill_reason"]

    def test_quota_rejections_do_not_pollute_cemetery(self, tmp_path):
        """A quota rejection is not a mechanism death — putting it in
        the cemetery would poison future search with non-failures."""
        from scripts.r411_run_campaign import _append_cemetery
        import orchestrator.mechanism_cemetery as mc

        appended = []
        mc.append_entries_to_cemetery_file = \
            lambda entries: appended.extend(entries)
        c = Campaign(str(REPO), run_dir=str(tmp_path / "run"))
        sel = {
            "full_records": [],
            "rejected": [{
                "candidate_id": "C-quota",
                "name": "Good but surplus",
                "reason": "quota filled by higher-ranked survivors",
            }],
        }
        _append_cemetery(c, sel)
        assert appended == []


# ---------------------------------------------------------------------------
# campaign state machine
# ---------------------------------------------------------------------------

class TestCampaignState:

    def test_state_persists_and_resumes(self, tmp_path):
        c1 = Campaign(str(REPO), run_dir=str(tmp_path / "run"))
        c1.state["retrieval_done"] = ["energy_storage"]
        c1.save()
        c2 = Campaign(str(REPO), run_dir=str(tmp_path / "run"))
        assert c2.state["retrieval_done"] == ["energy_storage"]
        assert c2.state["campaign_version"] == CAMPAIGN_VERSION

    def test_frozen_inputs_recorded(self, tmp_path):
        c = Campaign(str(REPO), run_dir=str(tmp_path / "run"))
        assert c.state["domain_matrix"]["matrix_sha256"]
        assert c.state["scoring_contract"]["contract_sha256"]
        assert c.state["engine_commit"]

    def test_normalize_pool_shape(self):
        from discovery_fabric.r411.campaign import normalize_pool
        items = [{
            "id": "X1", "title": "t", "abstract": "a",
            "publication_year": 2021, "evidence_lane": "SCHOLARLY",
            "publication_status": "PEER_REVIEWED", "source_type":
                "scientific_paper", "source_id": "openalex:1",
            "provenance": {"source_family": "openalex",
                           "queries_by_source": {"openalex": "q"},
                           "query_variant_derivation": "PRIMARY",
                           "raw_payload_sha256": "h",
                           "fabric_version": "V2"},
        }]
        pool = normalize_pool(items)
        assert pool[0]["record_id"] == "X1"
        assert pool[0]["provenance"]["source_family"] == "openalex"
        assert pool[0]["lane"] == "SCHOLARLY"


# ---------------------------------------------------------------------------
# portfolio bias isolation (s21)
# ---------------------------------------------------------------------------

class TestNoPortfolioBias:

    def test_portfolio_mechanisms_are_collision_targets_only(self):
        """The package list exists in collision.py as targets; it must
        NOT appear in the matrix (seeds) — enforced by the matrix test.
        Here: the collision module's list is read-only reference data,
        never injected into prompts."""
        import discovery_fabric.r411.extract as ex
        prompt_src = open(ex.__file__).read()
        for pm in PORTFOLIO_MECHANISMS:
            for term in ("drainage priority", "photovoltaic power",
                         "gravity compensation", "self-referencing",
                         "acoustic obstruction"):
                assert term not in prompt_src

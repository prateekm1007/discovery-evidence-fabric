"""tests/test_engine_integration.py — D5/D7/D8/D10 contract + behavioral tests.

Offline by default (no network, no LLM). Live tests are gated behind
ENGINE_LIVE=1. Synthetic fixtures carry epistemic_class=SYNTHETIC_TEST_ONLY
and are permitted in TESTS only — never in research run artifacts (Art. VI).

D10 acceptance (behavioral difference): the ablation test proves each
integrated module changes the candidate envelope, and that removing/
flipping a module's verdict changes the final ranking. A module whose
removal causes no behavioral difference is NOT part of the engine.
"""
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.candidate import Candidate, sha256_obj  # noqa: E402
from discovery_fabric.engine import adapters as A  # noqa: E402
from discovery_fabric.engine.adapters import (  # noqa: E402
    ADAPTERS, STAGE_ORDER, PRIOR_ART_STATUS_MAP, _CemeterySubCheck)

CTX = {"run_id": "testrun:fixture", "problem_id": "fixture"}

PROBLEM = {
    "problem_id": "fixture",
    "device": "CSF shunt system",
    "failure_mode": "OBSTRUCTION",
    "failure": "proximal catheter obstruction by choroid plexus ingrowth",
    "constraint": "maintain patency for device lifetime without Revision",
}

ABSTRACT = (
    "In a canine model of communicating hydrocephalus, a porous titanium "
    "microstructure maintained patency for 90 days while reducing proximal "
    "shunt obstruction rates by 40 percent compared to standard silicone "
    "catheters. Inflammatory response was graded mild at 6 months.")

MECHANISM_SPAN = ("reducing proximal shunt obstruction rates by 40 percent "
                  "compared to standard silicone catheters")

FIXTURE_ATTACK_PASS = {
    "overall": "PASS", "killed_count": 0, "reason": "synthetic pass",
    "attacks": {d: "SURVIVED" for d in (
        "unsupported_mechanism", "weak_transfer", "obvious_combination",
        "prior_art", "contradiction", "boundary_failure",
        "engineering_infeasibility", "regulatory_incompatibility")},
    "invalid_dimensions": [], "v4_corrections_applied": [],
    "prior_art_state": "NO_MATCH_FOUND", "evidence_verified": True,
    "prompt_hash": "0" * 16, "output_hash": "0" * 16,
    "timestamp": "2026-01-01T00:00:00Z",
    "_fixture_epistemic_class": "SYNTHETIC_TEST_ONLY",
}


def fixture_envelope(attack_overall="PASS"):
    env = Candidate(problem=PROBLEM, problem_id="fixture")
    ev = {
        "id": "europepmc:FIXTURE1", "source_type": "scientific_paper",
        "source": "EuropePMC", "source_id": "FIXTURE1",
        "source_uri": "https://fixture.invalid/1", "title": "Fixture study",
        "abstract": ABSTRACT, "doi": "10.0000/fixture",
        "publication_date": "2020-01-01",
        "content_hash": sha256_obj({"t": "fixture-evidence-payload"}),
    }
    env.evidence = [ev]
    env.evidence_ids = [ev["id"]]
    # the fixture represents an envelope that already passed RETRIEVE+FREEZE:
    # record the custody snapshot the EvidenceFreezeAdapter would have written
    freeze_snapshot = {
        "run_id": "testrun:fixture",
        "problem_id": "fixture",
        "frozen_at": "2026-01-01T00:00:00Z",
        "evidence_count": 1,
        "custody_records": [{
            "record_id": ev["id"], "content_hash": ev["content_hash"],
            "source": ev["source"], "evidence_class": "SCIENTIFIC_ABSTRACT"}],
        "hash_verification_all_pass": True,
        "_fixture_epistemic_class": "SYNTHETIC_TEST_ONLY",
    }
    freeze_snapshot["snapshot_hash"] = sha256_obj(freeze_snapshot)
    env.provenance = {"evidence_freeze": freeze_snapshot}
    raw = {
        "candidate_id": "cand:FIXTURE",
        "falsification_test": (
            "Bench shunt loop with choroid plexus tissue analog; measure "
            "flow decay over 30 days vs silicone control catheter."),
        "mechanism_source_span": MECHANISM_SPAN,
        "source_evidence": {
            "source_id": ev["id"],
            "source_hash": ev["content_hash"],
            "source_span": ABSTRACT[:500],
            "source_title": ev["title"],
        },
        "mechanism": "porous titanium microstructure resists tissue ingrowth",
        "intervention": "porous titanium proximal catheter tip",
        "expected_effect": "reduced proximal obstruction at 90 days",
        "_fixture_epistemic_class": "SYNTHETIC_TEST_ONLY",
    }
    # E15-B content standard: mirror the multi-sentence mechanism
    # narrative a real LLM synthesis produces (fixtures represent real
    # survivors; the depth evaluator is never lowered to admit thin ones)
    mechanism_rich = (
        f"{raw['mechanism']}. The proposed intervention realizes this "
        f"mechanism by placing {raw['intervention']} at the failure site "
        "identified in the problem statement, where the governing "
        f"physical effect produces {raw['expected_effect']} under the "
        "stated constraint; the transfer logic follows from the custodied "
        "source observation and its mechanism source span.")
    env.mechanism_map = {
        "mechanism": mechanism_rich,
        "intervention": raw["intervention"],
        "expected_effect": raw["expected_effect"],
        "falsification_test": raw["falsification_test"],
        "mechanism_source_span": MECHANISM_SPAN,
        "raw_candidate": raw,
    }
    attack = json.loads(json.dumps(FIXTURE_ATTACK_PASS))
    attack["overall"] = attack_overall
    if attack_overall == "KILLED":
        attack["killed_count"] = 1
        attack["attacks"]["unsupported_mechanism"] = "KILLED"
        attack["reason"] = "synthetic kill"
    env.attack_results = attack
    env.prior_art = {
        "prior_art_status": "NO_MATCH_FOUND",
        "legacy_status": "NO_MATCHING_EVIDENCE_FOUND",
        "state_vocabulary": "classify/v4_corrections",
    }
    env.collision_results = {
        "novelty_risk": "SEARCHED_NO_DIRECT_TITLE_MATCH",
        "patent": {"hits": [], "hit_count": 0, "source_errors": []},
    }
    return env


# ----------------------------------------------------------------------
# D8 invariant: the loop chain is exactly the directive chain
# ----------------------------------------------------------------------

def test_stage_order_is_exact_d8_chain():
    # R394 s6: PREMISE_GATE is a first-class stage between FREEZE and
    # SYNTHESIZE (directive: "a first-class discovery stage, not an
    # adversarial cleanup trick").
    # R397 Phase 2: PHYSICS is a first-class stage between COLLISION and
    # ATTACK — the physics solver is part of the LIVE RUN CHAIN for
    # every ordinary user run (consultant finding: "validated code but
    # not part of the live run chain"). The D8 chain is 15 stages.
    assert STAGE_ORDER == [
        "RETRIEVE", "FREEZE", "PREMISE_GATE", "SYNTHESIZE", "VERIFY",
        "MULTI_SOURCE_DISCOVERY", "COLLISION", "PHYSICS", "ATTACK",
        "CONTRADICTION", "KILLER_EXPERIMENT", "ADJUDICATION", "CLASSIFY",
        "NEXT_BEST_ACTION", "RANK"]


# ----------------------------------------------------------------------
# D5 adapter contracts (offline)
# ----------------------------------------------------------------------

def test_prior_art_status_map_no_silent_kill_promotion():
    """LIKELY_PRIOR_ART_EXISTS (abstract-level 'likely') must NOT be promoted
    to a KILL state — Art. XXV: unresolved is not negative evidence."""
    mapped = PRIOR_ART_STATUS_MAP["LIKELY_PRIOR_ART_EXISTS"]["mapped"]
    assert mapped == "UNRESOLVED_INSUFFICIENT_EVIDENCE"
    from discovery_fabric.a2.classify import KILL_STATES
    for row in PRIOR_ART_STATUS_MAP.values():
        assert row["mapped"] not in KILL_STATES


def test_freeze_adapter_on_fixture():
    env = fixture_envelope()
    entry = env.run_stage("FREEZE", "EVIDENCE_FREEZE",
                          A.EvidenceFreezeAdapter.module_path,
                          A.EvidenceFreezeAdapter.canonical_fn,
                          A.EvidenceFreezeAdapter().execute, env, CTX)
    assert entry["delta_real"] is True
    snap = env.provenance["evidence_freeze"]
    assert snap["hash_verification_all_pass"] is True
    assert snap["snapshot_hash"] and len(snap["snapshot_hash"]) == 64
    assert len(snap["custody_records"]) == 1


def test_verify_adapter_accepts_exact_span():
    env = fixture_envelope()
    entry = env.run_stage("VERIFY", "EVIDENCE_VERIFY",
                          A.EvidenceVerifyAdapter.module_path,
                          A.EvidenceVerifyAdapter.canonical_fn,
                          A.EvidenceVerifyAdapter().execute, env, CTX)
    ev = env.adjudication["evidence_verification"]
    assert ev["verified"] is True
    assert ev["mechanism_span_verbatim"] is True
    assert entry["delta_real"] is True


def test_contradiction_queue_adapter():
    env = fixture_envelope(attack_overall="KILLED")
    entry = env.run_stage("CONTRADICTION", "CONTRADICTION_QUEUE",
                          A.ContradictionQueueAdapter.module_path,
                          A.ContradictionQueueAdapter.canonical_fn,
                          A.ContradictionQueueAdapter().execute, env, CTX)
    assert entry["delta_real"] is True
    d = env.contradictions
    assert d["blocking_count"] >= 1
    ids = [c["contradiction_id"] for c in d["contradictions"]]
    assert "con:attack:unsupported_mechanism" in ids


def test_killer_experiment_adapter_ranks_by_eig():
    env = fixture_envelope()
    env.run_stage("CONTRADICTION", "CONTRADICTION_QUEUE",
                  A.ContradictionQueueAdapter.module_path,
                  A.ContradictionQueueAdapter.canonical_fn,
                  A.ContradictionQueueAdapter().execute, env, CTX)
    entry = env.run_stage("KILLER_EXPERIMENT", "KILLER_EXPERIMENT",
                          A.KillerExperimentAdapter.module_path,
                          A.KillerExperimentAdapter.canonical_fn,
                          A.KillerExperimentAdapter().execute, env, CTX)
    ke = env.killer_experiment
    assert entry["delta_real"] is True
    assert ke["selected"]["name"]
    assert len(ke["options_ranked"]) >= 1
    assert ke["options_ranked"][0]["eig"] >= ke["options_ranked"][-1]["eig"]
    assert all(h["provenance"]["epistemic_class"] == "MODEL_DERIVED"
               for h in ke["hypotheses"])


def test_adjudication_fail_closed_on_evaluator_failure():
    env = fixture_envelope()
    env.attack_results["overall"] = "EVALUATION_FAILED"
    _run_chain_to_adjudication(env)
    council = env.adjudication["council"]
    assert council["verdict"] == "INSUFFICIENT_ADJUDICATION"
    assert "adversarial_not_killed" in council["failed_checks"]


def _run_chain_to_adjudication(env):
    env.run_stage("VERIFY", "EVIDENCE_VERIFY",
                  A.EvidenceVerifyAdapter.module_path,
                  A.EvidenceVerifyAdapter.canonical_fn,
                  A.EvidenceVerifyAdapter().execute, env, CTX)
    for stage, adapter in (("CONTRADICTION", A.ContradictionQueueAdapter),
                           ("KILLER_EXPERIMENT", A.KillerExperimentAdapter),
                           ("ADJUDICATION", A.AdjudicationAdapter)):
        env.run_stage(stage, adapter.capability_id, adapter.module_path,
                      adapter.canonical_fn, adapter().execute, env, CTX)


def test_cemetery_check_inside_adjudication():
    env = fixture_envelope()
    _run_chain_to_adjudication(env)
    assert env.cemetery_check.get("verdict") in ("PROCEED", "WARNING",
                                                 "BLOCKED", "UNRESOLVED")
    council = env.adjudication["council"]
    checks = [c["check"] for c in council["checks"]]
    assert "cemetery_not_hard_blocked" in checks


def test_classify_adapter_with_fixture_promotes_to_candidate():
    env = fixture_envelope()
    _run_chain_to_adjudication(env)
    entry = env.run_stage("CLASSIFY", "EPISTEMIC_CLASSIFICATION",
                          A.EpistemicClassificationAdapter.module_path,
                          A.EpistemicClassificationAdapter.canonical_fn,
                          A.EpistemicClassificationAdapter().execute, env, CTX)
    eps = env.epistemic_state
    assert eps["final_status"] == "AUTOMATED_INVENTION_CANDIDATE"
    assert eps["promotion_blocked"] is False


def test_next_best_action_adapter():
    env = fixture_envelope(attack_overall="KILLED")
    env.run_stage("CONTRADICTION", "CONTRADICTION_QUEUE",
                  A.ContradictionQueueAdapter.module_path,
                  A.ContradictionQueueAdapter.canonical_fn,
                  A.ContradictionQueueAdapter().execute, env, CTX)
    env.run_stage("KILLER_EXPERIMENT", "KILLER_EXPERIMENT",
                  A.KillerExperimentAdapter.module_path,
                  A.KillerExperimentAdapter.canonical_fn,
                  A.KillerExperimentAdapter().execute, env, CTX)
    entry = env.run_stage("NEXT_BEST_ACTION", "NEXT_BEST_ACTION",
                          A.NextBestActionAdapter.module_path,
                          A.NextBestActionAdapter.canonical_fn,
                          A.NextBestActionAdapter().execute, env, CTX)
    nba = env.next_best_action
    assert entry["delta_real"] is True
    assert nba["ranked_actions"]
    assert nba["ranked_actions"][0]["score"] >= nba["ranked_actions"][-1]["score"]


def test_ranking_is_allocation_policy():
    env = fixture_envelope()
    env.run_stage("CONTRADICTION", "CONTRADICTION_QUEUE",
                  A.ContradictionQueueAdapter.module_path,
                  A.ContradictionQueueAdapter.canonical_fn,
                  A.ContradictionQueueAdapter().execute, env, CTX)
    env.run_stage("KILLER_EXPERIMENT", "KILLER_EXPERIMENT",
                  A.KillerExperimentAdapter.module_path,
                  A.KillerExperimentAdapter.canonical_fn,
                  A.KillerExperimentAdapter().execute, env, CTX)
    _env_adjudication_classify(env)
    entry = env.run_stage("NEXT_BEST_ACTION", "NEXT_BEST_ACTION",
                          A.NextBestActionAdapter.module_path,
                          A.NextBestActionAdapter.canonical_fn,
                          A.NextBestActionAdapter().execute, env, CTX)
    entry = env.run_stage("RANK", "PORTFOLIO_RANKING",
                          A.PortfolioRankingAdapter.module_path,
                          A.PortfolioRankingAdapter.canonical_fn,
                          A.PortfolioRankingAdapter().execute, env, CTX)
    r = env.ranking
    assert entry["delta_real"] is True
    assert r["is_allocation_policy_not_truth"] is True
    assert r["formula_version"] == "engine-ranking-v1"
    assert 0.0 <= r["score"] <= 1.5


def _env_adjudication_classify(env):
    env.run_stage("ADJUDICATION", "ADJUDICATION",
                  A.AdjudicationAdapter.module_path,
                  A.AdjudicationAdapter.canonical_fn,
                  A.AdjudicationAdapter().execute, env, CTX)
    env.run_stage("CLASSIFY", "EPISTEMIC_CLASSIFICATION",
                  A.EpistemicClassificationAdapter.module_path,
                  A.EpistemicClassificationAdapter.canonical_fn,
                  A.EpistemicClassificationAdapter().execute, env, CTX)


# ----------------------------------------------------------------------
# D10 behavioral proof (offline ablation)
# ----------------------------------------------------------------------

def _full_offline_chain(attack_overall):
    env = fixture_envelope(attack_overall=attack_overall)
    plan = [("VERIFY", A.EvidenceVerifyAdapter),
            ("CONTRADICTION", A.ContradictionQueueAdapter),
            ("KILLER_EXPERIMENT", A.KillerExperimentAdapter),
            ("ADJUDICATION", A.AdjudicationAdapter),
            ("CLASSIFY", A.EpistemicClassificationAdapter),
            ("NEXT_BEST_ACTION", A.NextBestActionAdapter),
            ("RANK", A.PortfolioRankingAdapter)]
    for stage, adapter in plan:
        env.run_stage(stage, adapter.capability_id, adapter.module_path,
                      adapter.canonical_fn, adapter().execute, env, CTX)
    return env


def test_d10_every_offline_stage_changes_envelope():
    env = _full_offline_chain("PASS")
    for entry in env.stage_log:
        assert entry["delta_real"] is True, \
            f"stage {entry['stage']} produced NO candidate delta — it is not " \
            "demonstrably part of the engine (D10)"
        assert entry["after_envelope_hash"] != entry["before_envelope_hash"]


def test_d10_attack_verdict_flip_changes_final_outcome():
    survivor = _full_offline_chain("PASS")
    killed = _full_offline_chain("KILLED")
    s_survivor = survivor.ranking["score"]
    s_killed = killed.ranking["score"]
    assert s_survivor != s_killed, \
        "flipping the ATTACK verdict did not change the ranking — ATTACK " \
        "would not be a real part of the engine (D10)"
    assert s_survivor > s_killed
    assert survivor.epistemic_state["final_status"] == "AUTOMATED_INVENTION_CANDIDATE"
    assert killed.epistemic_state["final_status"] == "REJECTED"


def test_candidate_envelope_roundtrip_and_hashing():
    env = fixture_envelope()
    h1 = env.envelope_hash()
    d = env.to_dict()
    env2 = Candidate.from_dict(d)
    assert env2.envelope_hash() == h1
    assert len(h1) == 64


# ----------------------------------------------------------------------
# Live (network) tests — gated
# ----------------------------------------------------------------------

@pytest.mark.skipif(not __import__("os").environ.get("ENGINE_LIVE"),
                    reason="network test; set ENGINE_LIVE=1")
def test_retrieval_adapter_live():
    env = Candidate(problem={
        "problem_id": "live_probe",
        "device": "CSF shunt valve",
        "failure_mode": "OBSTRUCTION",
        "failure": "proximal shunt obstruction",
        "constraint": "long-term patency"}, problem_id="live_probe")
    A.A2RetrievalAdapter().execute(env, {"run_id": "live", "problem_id": "live_probe"})
    assert len(env.evidence) >= 1


@pytest.mark.skipif(not __import__("os").environ.get("ENGINE_LIVE"),
                    reason="network test; set ENGINE_LIVE=1")
def test_multisource_adapter_live():
    env = fixture_envelope()
    A.MultiSourceDiscoveryAdapter().execute(env, CTX)
    assert env.multi_source.get("sources_hit") is not None

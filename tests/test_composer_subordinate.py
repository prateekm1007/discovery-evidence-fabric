"""R6 P0-5: the composer is subordinate to discovery eligibility.

The composer must not become an independent invention generator:
 - it composes ONLY gate-adjudicated candidates (ranked survivors, or
   the attack-adjudicated raw candidate), never raw/unfiltered
   mechanism records without a verdict;
 - a KILLED attack verdict yields an empty admissible set — the state
   is typed NO_ADMISSIBLE_CANDIDATES (ZERO LLM calls), never a composed
   recommendation;
 - hypothesis-class verdicts are admissible only flagged as
   UNVERIFIED_HYPOTHESIS (already hypothesis verdict machinery rides
   with them into the prompt);
 - when nothing is admissible, the completion is a skip, not an answer.
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.answer_composer import candidates_from_state

RAW = {"candidate_id": "cand:raw-1", "mechanism": "compliant buffer absorbs differential expansion",
       "intervention": "bond the glass-ceramic joint with a compliant buffer"}


def _env(attack_overall, raw=True, ranked=None):
    env = {"attack_results": {"overall": attack_overall},
           "mechanism_map": {"raw_candidate": RAW} if raw else {}}
    if ranked is not None:
        env["ranked_results"] = {"results": ranked}
    return env


def test_killed_attack_verdict_yields_no_admissible_candidates():
    cands = candidates_from_state(_env("KILLED"))
    assert cands == []


def test_pass_verdict_admits_the_adjudicated_candidate():
    cands = candidates_from_state(_env("PASS"))
    assert len(cands) == 1
    assert cands[0]["attack_verdict"] == "PASS"
    assert "hypothesis_unverified" not in cands[0]


def test_escalated_objection_admits_only_as_hypothesis():
    cands = candidates_from_state(_env("ESCALATED_OBJECTION"))
    assert len(cands) == 1
    assert cands[0]["hypothesis_unverified"] is True


def test_ranked_survived_takes_precedence_over_raw():
    ranked = [{"candidate_id": "cand:r1", "disposition": "SURVIVED",
               "mechanism": "m", "intervention": "i"}]
    cands = candidates_from_state(_env("PASS", ranked=ranked))
    assert cands[0]["candidate_id"] == "cand:r1"
    cands2 = candidates_from_state(_env("KILLED", ranked=ranked))
    assert cands2 and cands2[0]["candidate_id"] == "cand:r1"  # survivors still admissible


def test_ranked_present_without_survivors_and_raw_killed_yields_nothing():
    ranked = [{"candidate_id": "cand:r2", "disposition": "KILLED"}]
    cands = candidates_from_state(_env("KILLED", ranked=ranked))
    assert cands == []


def test_missing_attack_results_yields_nothing_admissible():
    env = {"mechanism_map": {"raw_candidate": RAW}}
    # unadjudicated (attack never ran / no record): never a recommendation
    assert candidates_from_state(env) == []
    env = {"mechanism_map": {"raw_candidate": RAW, "attack_overall": ""}}
    assert candidates_from_state(env) == []
    env = {"mechanism_map": {}}
    assert candidates_from_state(env) == []


# ---------------------------------------------------------------------
# P0-2 (owner directive 2026-11-11, item 2): the EXPLICIT allowlist.
# Every failure / incomplete verdict — including EVALUATOR_CALL_FAILED
# (the evaluator-transport failure adversarial.py returns explicitly) —
# is non-admissible and typed; those states produce
# NO_ADMISSIBLE_CANDIDATES with ZERO composer LLM calls.
# ---------------------------------------------------------------------

import pytest

from discovery_fabric.engine.answer_composer import (
    admission_reasons_from_state, compose_if_admissible,
    classify_verdict_admissibility)

# every failure and incomplete verdict the gauntlet can record
NON_ADMISSIBLE_VERDICTS = [
    "EVALUATOR_CALL_FAILED", "EVALUATION_FAILED",
    "NOT_RUN", "INCOMPLETE_EVIDENCE", "INCOMPLETE_INFRASTRUCTURE",
    "INCOMPLETE_DATA", "UNKNOWN", "PENDING", "PENDING_CORROBORATION",
    "ERROR", "INCONCLUSIVE", "INDETERMINATE",
    "KILL", "KILLED", "KILLED_DETERMINISTIC", "KILLED_SCIENTIFIC",
    "REJECTED", "REJECTED_ATTACK", "PROVIDER_UNAVAILABLE", "RISK",
    "", "NO_VERDICT",
]

# DIRECTIVE 2 (owner audit round 2026-11-12): the typed no-answer is
# reserved for SCIENTIFIC kills — infrastructure-typed verdicts
# (Art. LXI classes) deliver the record-bound raw candidate as a
# clearly flagged UNVERIFIED hypothesis instead of silence.
INFRASTRUCTURE_DELIVERED_VERDICTS = [
    "EVALUATOR_CALL_FAILED", "EVALUATION_FAILED",
    "PROVIDER_UNAVAILABLE", "INCOMPLETE_EVIDENCE",
    "INCOMPLETE_INFRASTRUCTURE", "INCOMPLETE_DATA", "PENDING",
    "PENDING_CORROBORATION",
]
STRICT_NON_ADMISSIBLE_VERDICTS = [
    v for v in NON_ADMISSIBLE_VERDICTS
    if v not in INFRASTRUCTURE_DELIVERED_VERDICTS]


def _compose_llm(prompt, system="", timeout=240, max_tokens=700,
                 purpose="", **kw):
    return {"ok": True, "content": (
        "PARAMETER: sealed joint — compliant buffer — ASSUMPTION\n"
        "INDICATOR: buffer strain. THRESHOLD: 40 MPa — ASSUMPTION. "
        "PROTOCOL: 100 cycles; fail if delamination before 500."),
        "prompt_hash": "p" * 8, "output_hash": "o" * 8}


ADMISSIBLE_VERDICTS = ["PASS", "SURVIVED", "SURVIVE"]
HYPOTHESIS_VERDICTS = ["ESCALATED_OBJECTION", "UNVERIFIED_HYPOTHESIS",
                       "HYPOTHESIS", "SURVIVED_UNVERIFIED"]


@pytest.mark.parametrize("v", STRICT_NON_ADMISSIBLE_VERDICTS)
def test_non_admissible_verdicts_produce_no_candidates(v):
    cands = candidates_from_state(_env(v))
    assert cands == []


@pytest.mark.parametrize("v", INFRASTRUCTURE_DELIVERED_VERDICTS)
def test_infrastructure_verdicts_admit_flagged_hypothesis_candidate(v):
    # DIRECTIVE 2 (2026-11-12): infrastructure-typed verdicts (Art. LXI)
    # deliver the record-bound raw candidate as a flagged hypothesis —
    # never silence, never an endorsed claim.
    cands = candidates_from_state(_env(v))
    assert len(cands) == 1, (v, cands)
    assert cands[0]["admission"]["class"] == "HYPOTHESIS"
    assert cands[0]["admission"]["reason"] == \
        "VERDICT_IS_INFRASTRUCTURE_NOT_SCIENTIFIC"


@pytest.mark.parametrize("v", NON_ADMISSIBLE_VERDICTS)
def test_non_admissible_verdicts_are_typed(v):
    reasons = admission_reasons_from_state(_env(v))
    assert reasons, f"verdict {v!r} must leave a typed reason"
    r = reasons[0]
    assert r["reason"] not in (None, ""), r
    assert r["verdict"].strip().upper() in (v.strip().upper(), "NO_VERDICT")


@pytest.mark.parametrize("v", ADMISSIBLE_VERDICTS)
def test_admissible_survived_verdicts_admit_the_candidate(v):
    cands = candidates_from_state(_env(v))
    assert len(cands) == 1, f"{v!r} must admit exactly the adjudicated candidate"
    assert cands[0]["attack_verdict"] == v
    assert "hypothesis_unverified" not in cands[0]
    assert cands[0]["admission"]["class"] == "SURVIVED"


@pytest.mark.parametrize("v", HYPOTHESIS_VERDICTS)
def test_hypothesis_verdicts_admit_only_flagged(v):
    cands = candidates_from_state(_env(v))
    assert len(cands) == 1
    assert cands[0]["hypothesis_unverified"] is True
    assert cands[0]["admission"]["class"] == "HYPOTHESIS"


def test_classify_evaluator_call_failed_is_evaluator_failure():
    cls = classify_verdict_admissibility("EVALUATOR_CALL_FAILED")
    assert cls == {"admissible": False, "class": "NON_ADMISSIBLE",
                   "hypothesis": False,
                   "reason": "EVALUATOR_FAILURE"}


def test_evaluator_call_failed_delivers_flagged_hypothesis():
    # UPDATED by DIRECTIVE 2 (owner audit round 2026-11-12): the typed
    # no-answer is reserved for SCIENTIFIC kills. The evaluator
    # transport failure (the exact defect from the earlier audit) is
    # Art. LXI INFRASTRUCTURE — the record-bound raw candidate now
    # delivers as a clearly flagged UNVERIFIED hypothesis (the user
    # gets a partly-verified answer with one plain caveat, never
    # silence); the infrastructure verdict rides the admission record.
    rec = compose_if_admissible(_env("EVALUATOR_CALL_FAILED"),
                                {"device": "d", "failure": "f"},
                                [{"id": "e1", "title": "t"}],
                                None, "intervention-proposal",
                                llm_generate=_compose_llm)
    assert rec["admitted_candidates"][0]["hypothesis"] is True
    assert rec["admitted_candidates"][0]["attack_verdict"] == \
        "EVALUATOR_CALL_FAILED"
    assert rec["state"] != "NO_ADMISSIBLE_CANDIDATES"
    assert isinstance(rec["answer"], str) and rec["answer"].strip()
    assert rec["n_llm_calls"] == 1


@pytest.mark.parametrize("v", INFRASTRUCTURE_DELIVERED_VERDICTS)
def test_infrastructure_verdict_delivers_flagged_hypothesis(v):
    rec = compose_if_admissible(_env(v), {"device": "d", "failure": "f"},
                                [{"id": "e1", "title": "t"}], None,
                                "intervention-proposal",
                                llm_generate=_compose_llm)
    assert rec["admitted_candidates"][0]["hypothesis"] is True, (v, rec)
    assert rec["state"] in ("COMPOSED_CONTRACT_VALID",
                            "COMPOSED_CONTRACT_DOWNGRADED",
                            "COMPOSED_CONTRACT_INVALID"), (v, rec["state"])
    assert isinstance(rec["answer"], str) and rec["answer"].strip()


@pytest.mark.parametrize("v", STRICT_NON_ADMISSIBLE_VERDICTS)
def test_non_admission_zero_composer_calls(v):
    def _boom(*a, **k):
        raise AssertionError("composer must not run on no-admission")
    rec = compose_if_admissible(_env(v), {"device": "d", "failure": "f"},
                                [{"id": "e1", "title": "t"}], None,
                                "intervention-proposal", llm_generate=_boom)
    assert rec["state"] == "NO_ADMISSIBLE_CANDIDATES", (v, rec["state"])
    assert rec["n_llm_calls"] == 0
    assert rec["answer"] is None


def test_skipped_no_packet_zero_composer_calls():
    # admissible candidate but no frozen packet: typed refusal, zero
    # LLM calls (the empty-evidence composition is forbidden)
    def _boom(*a, **k):
        raise AssertionError("composer must not run without a packet")
    rec = compose_if_admissible(_env("PASS"), {"device": "d",
                                               "failure": "f"},
                                [], None, "intervention-proposal",
                                llm_generate=_boom)
    assert rec["state"] == "SKIPPED_NO_PACKET"
    assert rec["n_llm_calls"] == 0
    assert rec["answer"] is None


def test_composition_runs_when_admissible():
    from discovery_fabric.engine.answer_composer import _COMPOSER_SYSTEM
    calls = {"n": 0}

    def llm(prompt, system="", timeout=240, max_tokens=700,
             purpose="", **kw):
        calls["n"] += 1
        return {"ok": True, "content": ("Recommend the compliant buffer "
                                        "joint. INDICATOR: buffer strain. "
                                        "THRESHOLD: 40 MPa — ASSUMPTION. "
                                        "PROTOCOL: 100 cycles; fail if "
                                        "delamination before 500."),
                "prompt_hash": "p" * 8, "output_hash": "o" * 8}
    rec = compose_if_admissible(_env("PASS"), {"device": "glass vessel",
                                               "failure": "joint delamination",
                                               "question_type":
                                               "intervention-proposal",
                                               "user_variables": []},
                                [{"id": "iso12100", "title": "t",
                                  "abstract": "a"}],
                                None, "intervention-proposal",
                                llm_generate=llm)
    assert calls["n"] == 1
    assert rec["state"] in ("COMPOSED_CONTRACT_VALID",
                            "COMPOSED_CONTRACT_INVALID")
    assert rec["admitted_candidates"][0]["attack_verdict"] == "PASS"


def test_attack_record_not_bound_to_raw_candidate_is_typed_out():
    # mechanism_map was re-stamped by a critique-revise pass; the
    # attack record carries no matching revision marker — it predates
    # the candidate it would be cited for: NOT admissible (a global
    # status must not promote an unadjudicated candidate)
    env = {"attack_results": {"overall": "PASS"},
           "mechanism_map": {"raw_candidate": RAW,
                             "revision": "CRITIQUE_REVISE_ONCE"}}
    assert candidates_from_state(env) == []
    reasons = admission_reasons_from_state(env)
    assert reasons[0]["reason"].startswith(
        "ATTACK_RECORD_NOT_CANDIDATE_BOUND")


def test_missing_attack_record_is_typed_out():
    env = {"mechanism_map": {"raw_candidate": RAW}}
    reasons = admission_reasons_from_state(env)
    assert reasons[0]["reason"].startswith("ATTACK_RECORD_ABSENT")


def test_ranked_survived_row_with_evaluator_failure_verdict_typed_out():
    # the row's OWN recorded attack verdict (not a synthesized "PASS")
    # decides admissibility
    ranked = [{"candidate_id": "cand:r3", "disposition": "SURVIVED",
               "attack_verdict": "EVALUATOR_CALL_FAILED",
               "mechanism": "m", "intervention": "i"}]
    assert candidates_from_state(_env("KILLED", ranked=ranked)) == []
    reasons = admission_reasons_from_state(_env("KILLED", ranked=ranked))
    assert reasons and reasons[0]["source"] == "ranked"
    assert reasons[0]["reason"] == "EVALUATOR_FAILURE"


def test_ranked_survived_row_admits_on_recorded_disposition():
    # a SURVIVED row with no separate attack_verdict field rides on its
    # OWN recorded post-gate disposition — never a fabricated "PASS"
    ranked = [{"candidate_id": "cand:r4", "disposition": "SURVIVED",
               "mechanism": "m", "intervention": "i"}]
    cands = candidates_from_state(_env("KILLED", ranked=ranked))
    assert len(cands) == 1
    assert cands[0]["candidate_id"] == "cand:r4"
    assert cands[0]["attack_verdict"] == "SURVIVED"
    assert cands[0]["admission"]["class"] == "SURVIVED"


def test_admitted_raw_candidate_carries_own_recorded_states():
    env = {"attack_results": {"overall": "PASS"},
           "mechanism_map": {"raw_candidate": dict(RAW)},
           "adjudication": {"evidence_verification": {"verified": True}},
           "contradictions": {"overall": "NO_CONTRADICTIONS"}}
    cands = candidates_from_state(env)
    assert len(cands) == 1
    states = cands[0]["own_recorded_states"]
    assert states["evidence_verification"] == "VERIFIED"
    assert states["contradictions"] == "NO_CONTRADICTIONS"
    # technical gates the run never stamped: typed NOT_RECORDED,
    # never assumed clean (Art. XXV)
    assert states["technical_gates"]["not_an_intervention"] == "NOT_RECORDED"


def test_admitted_candidate_reports_unverified_evidence_state():
    env = {"attack_results": {"overall": "PASS"},
           "mechanism_map": {"raw_candidate": dict(RAW)},
           "adjudication": {"evidence_verification": {"verified": False}}}
    cands = candidates_from_state(env)
    assert cands[0]["own_recorded_states"]["evidence_verification"] == \
        "NOT_VERIFIED"

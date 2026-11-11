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

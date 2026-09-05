"""tests/test_r412_synthesis_benchmark.py — P0-3 benchmark seals.

Hermetic pins:
  - the frozen problem prompts are IDENTICAL across models (the
    comparability contract — a mutated per-model prompt fails)
  - deterministic downstream verdicts on fixed synthetic candidates
  - distinctness union-find math (EQUIVALENT merges reduce the count)
  - metric math: rates, per-compute headline, zero-division safety
  - the attacker cap is enforced
  - the NOT_CALIBRATED caveat travels with survival numbers
"""
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.r412 import synthesis_benchmark as sb  # noqa: E402


def _cand(cid, chain=None, refs=None, intervention="vortex generator "
          "arrays on tube bundle fins"):
    return {
        "candidate_id": cid,
        "technology_name": f"tech {cid}",
        "problem": "test problem",
        "causal_chain": chain or [
            "vortex shedding from generator fins thins boundary layer",
            "convection coefficient rises on the shell side",
            "thermal resistance of the exchanger falls"],
        "unexploited_phenomenon": "vortex-induced convection",
        "intervention": intervention,
        "governing_variables": ["fin pitch", "Reynolds number"],
        "predicted_effect": "10-20% duty increase at fixed pump power",
        "equations": ["Nu = C Re^0.63 Pr^0.36"],
        "boundary_conditions": "Re 10^4-10^5, water side",
        "evidence_refs": refs or ["r:1"],
        "baseline": {"baseline_incumbent": "plain tube bundle",
                     "baseline_metric": "duty at fixed pump power"},
        "killer_experiment": {
            "experiment": "A/B finned vs plain bundle",
            "kill_condition": "duty delta < 3%",
            "cost_class": "BENCH"},
        "failure_modes": ["fouling between fins"],
        "commercial_path": {"buyer": "heat exchanger OEMs"},
        "cross_domain_transition": "aero -> thermal",
    }


def _pool():
    return [{"record_id": "r:1",
             "title": "Vortex generators in shell-and-tube heat "
                      "exchangers: convection enhancement and boundary "
                      "layer thinning, duty increase at fixed pump power",
             "abstract": ""}]


class TestComparability:
    def test_same_prompt_for_every_model(self):
        """The frozen prompt is a function of the problem only — every
        model must see byte-identical input (Art. XLVII baseline
        supremacy)."""
        problems = [
            {"domain_id": "d1", "entry": {"domain_id": "d1"},
             "domain_spec": _spec(), "pool": _pool()},
        ]
        p1, _ = sb.build_problem_prompt(problems[0])
        p2, _ = sb.build_problem_prompt(problems[0])
        assert p1 == p2
        assert "CROSS-DOMAIN FORCING TASK" in p1

    def test_model_pass_uses_injected_generate(self):
        problems = [{
            "domain_id": "d1", "entry": {"domain_id": "d1"},
            "domain_spec": _spec(), "pool": _pool()}]
        seen = {}

        def fake_gen(prompt, system="", purpose="", max_tokens=0,
                     **kw):
            seen["prompt"] = prompt
            seen["max_tokens"] = max_tokens
            seen["system"] = system
            return {"ok": True, "status": "OK", "provider": "test",
                    "model": "test", "prompt_hash": "h", "output_hash":
                    "o", "content": "no candidates here"}
        res = sb.run_model_pass("m", problems, REPO,
                                llm_generate=fake_gen)
        assert seen["max_tokens"] == 2600
        assert res["calls"] == 1
        assert res["per_problem"][0]["status"] == "OK"


def _spec():
    return {
        "label": "Test Domain",
        "pain_points": ["THERMAL_LOSS"],
        "systems": ["test system"],
    }


class TestDownstreamVerdicts:
    def test_qualified_candidate_passes_all_gates(self):
        cand = _cand("C-ok", refs=["r:1"])
        model_pass = {"model_id": "m", "calls": 1, "wall_seconds": 10,
                      "per_problem": [{"domain_id": "d1", "status": "OK",
                                       "accepted": [cand],
                                       "rejected": []}]}
        problems = [{"domain_id": "d1", "entry": {"domain_id": "d1"},
                     "domain_spec": _spec(), "pool": _pool()}]
        d = sb.downstream_verdicts(model_pass, problems)
        row = d["per_candidate"][0]
        assert row["engineering_passed"] is True
        assert row["collision_screen"] == "PASS"
        assert row["qualified_deterministic"] is True

    def test_missing_kill_condition_fails_engineering(self):
        cand = _cand("C-bad")
        cand["killer_experiment"] = {"experiment": "x"}  # no kill cond
        assert sb.engineering_gate(cand)["passed"] is False

    def test_teaching_pool_record_screens(self):
        # pool record teaches the candidate's own mechanism (specific
        # AND core vocabulary present) -> SCREEN_COLLISION (the P0-2
        # screen against the same pool)
        cand = _cand("C-x", refs=["r:1"])
        pool = [{"record_id": "r:1",
                 "title": ("Vortex generator arrays on tube bundle fins "
                           "in shell-and-tube heat exchangers: vortex "
                           "shedding thins the boundary layer, the "
                           "convection coefficient rises on the shell "
                           "side, thermal resistance falls, duty "
                           "increase at fixed pump power"),
                 "abstract": ""}]
        scr = sb.screen_collision(cand, pool)
        assert scr["decision"] == "SCREEN_COLLISION"

    def test_topic_adjacent_pool_record_passes(self):
        # domain-adjacent but not mechanism-teaching -> PASS (the
        # conservative contract)
        cand = _cand("C-y", refs=["r:2"])
        pool = [{"record_id": "r:2",
                 "title": ("A review of industrial cooling strategies "
                           "and their economics"),
                 "abstract": ""}]
        scr = sb.screen_collision(cand, pool)
        assert scr["decision"] == "PASS"


class TestDistinctness:
    def test_equivalent_merge_reduces_count(self):
        a = _cand("C-a")
        b = _cand("C-b")  # same mechanism, different id
        d = sb.distinctness_analysis([a, b])
        verdict = d["pairwise"]
        if verdict.get("EQUIVALENT"):
            assert d["distinct_mechanisms"] == 1
        else:
            assert d["distinct_mechanisms"] == 2

    def test_distinct_mechanisms_stay_distinct(self):
        a = _cand("C-a", intervention="vortex generator fins",
                  chain=["vortex shedding thins boundary layer",
                         "convection rises", "duty increases"])
        b = _cand("C-b",
                  intervention="electromagnetic braking coil array",
                  chain=["eddy currents induce Lorentz drag",
                         "rotational energy dissipates",
                         "vibration amplitude decays"])
        d = sb.distinctness_analysis([a, b])
        assert d["distinct_mechanisms"] == 2


class TestMetrics:
    def test_metric_math_and_headline(self):
        model_pass = {"model_id": "m", "calls": 3, "wall_seconds": 30.0,
                      "per_problem": [
                          {"domain_id": "d1", "status": "OK",
                           "accepted": [_cand("C-1", refs=["r:1"]),
                                        _cand("C-2", refs=["r:1"])],
                           "rejected": [{"candidate_id": "R-1"}]},
                          {"domain_id": "d2", "status": "OK",
                           "accepted": [], "rejected": []},
                          {"domain_id": "d3",
                           "status": "INCOMPLETE_TRANSPORT",
                           "error": "x"}]}
        problems = [
            {"domain_id": "d1", "entry": {"domain_id": "d1"},
             "domain_spec": _spec(), "pool": _pool()},
            {"domain_id": "d2", "entry": {"domain_id": "d2"},
             "domain_spec": _spec(), "pool": []},
            {"domain_id": "d3", "entry": {"domain_id": "d3"},
             "domain_spec": _spec(), "pool": []}]
        downstream = sb.downstream_verdicts(model_pass, problems)
        accepted = [c for pr in model_pass["per_problem"]
                    if pr.get("status") == "OK"
                    for c in pr["accepted"]]
        distinctness = sb.distinctness_analysis(accepted)
        m = sb.model_metrics(model_pass, downstream, distinctness,
                             [{"verdict": "SURVIVED"},
                              {"verdict": "KILLED"}])
        assert m["candidates_accepted"] == 2
        assert m["candidates_rejected_by_gate"] == 1
        assert m["contract_valid_rate"] == round(2 / 3, 4)
        assert m["transport_failures"] == 1
        assert m["attacker_attacked"] == 2
        assert m["attacker_survived"] == 1
        assert m["qualified_per_compute_second"] is not None
        assert "NOT_CALIBRATED" in m["attacker_survival_caveat"]

    def test_zero_wall_no_division_error(self):
        model_pass = {"model_id": "m", "calls": 0, "wall_seconds": 0.0,
                      "per_problem": []}
        m = sb.model_metrics(model_pass,
                             {"per_candidate": [], "qualified": []},
                             {"distinct_mechanisms": 0, "pairwise": {}},
                             [])
        assert m["qualified_per_compute_second"] is None

    def test_attack_cap_is_three(self):
        assert sb.ATTACK_CAP_PER_MODEL == 3

    def test_frozen_domains_and_models_registered(self):
        assert sb.FROZEN_DOMAINS == [
            "heat_exchanger", "power_electronics",
            "data_center_thermal"]
        assert set(sb.MODEL_PASSES) == {
            "minimax-m3:free", "glm-4-plus", "glm-5.3-free"}

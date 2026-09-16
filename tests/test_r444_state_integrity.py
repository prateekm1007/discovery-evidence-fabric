"""R444 — state-integrity enforcement for the impossible states.

The operator directive R444-E: add ONLY the controls that mechanically
prevent these states:

    0 evolution generations        -> EVOLVED               (R443, kept)
    null causal delta              -> causal evolution      (R443, kept)
    null experiment selection      -> selected experiment   (R443, kept)
    null falsification threshold   -> complete experiment   (R444-D, NEW)
    benchmark not run              -> WORLD_CLASS_DISCOVERY_GREEN (NEW)
    attacker calibration not run   -> certified attacker    (NEW)

And R444-D: a package whose experiment contract cannot answer 'what
experimental outcome would kill this mechanism?' presents as
INVENTION_REQUIRES_EXPERIMENT — never as a fully defensible technical
opportunity.

Adversarial discipline (Art. XVII/XXX): every test first attacks the
control with the exact impossible state, then proves the positive
control (the honest state passes).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine.state_integrity import (  # noqa: E402
    ARTICLE_LII_FIELDS,
    evolution_status_violations,
    experiment_claim_violations,
    experiment_claim_violations_r444,
    falsification_contract_status,
    honest_fallback_status,
    system_claim_violations,
)
from discovery_fabric.engine.experiment_selector import (  # noqa: E402
    article_lii_contract,
)


# ---------------------------------------------------------------------------
# R444-D — the Article LII falsification contract
# ---------------------------------------------------------------------------
class TestFalsificationContractStatus(unittest.TestCase):
    def test_the_twelve_article_lii_fields_are_canonical(self):
        self.assertEqual(len(ARTICLE_LII_FIELDS), 12)
        self.assertIn("FALSIFICATION_THRESHOLD", ARTICLE_LII_FIELDS)

    def test_null_falsification_threshold_is_not_complete(self):
        """THE impossible state: null falsification threshold -> complete
        experiment. The contract without the kill answer is INCOMPLETE."""
        contract = {
            "HYPOTHESIS": "the effect holds",
            "TREATMENT": "the intervention",
            "FALSIFICATION_THRESHOLD": None,
        }
        s = falsification_contract_status(contract)
        self.assertFalse(s["falsification_threshold_answered"])
        self.assertFalse(s["contract_complete"])
        self.assertIn("FALSIFICATION_THRESHOLD", s["unknown_fields"])

    def test_unknown_falsification_threshold_is_not_complete(self):
        contract = {"FALSIFICATION_THRESHOLD":
                    "UNKNOWN (no kill outcome recorded)"}
        s = falsification_contract_status(contract)
        self.assertFalse(s["contract_complete"])

    def test_absent_contract_is_not_complete(self):
        s = falsification_contract_status(None)
        self.assertFalse(s["contract_complete"])
        self.assertEqual(len(s["unknown_fields"]), 12)

    def test_answered_falsification_threshold_is_complete(self):
        contract = {
            "FALSIFICATION_THRESHOLD":
                "the test fails to show the effect — mechanism killed",
            "HYPOTHESIS": "h",
        }
        s = falsification_contract_status(contract)
        self.assertTrue(s["falsification_threshold_answered"])
        self.assertTrue(s["contract_complete"])

    def test_unknown_fields_are_honest_not_violations(self):
        """Art. XXV: UNKNOWN fields limit maturity, not existence —
        COST/TIME/SAMPLE unknown do not make a falsifiable contract
        'absent', they make it unexecuted."""
        contract = {
            "FALSIFICATION_THRESHOLD": "the kill outcome",
            "COST": "UNKNOWN (no sourced estimate)",
            "TIME_BLOCKER": "no stage recorded time",
        }
        s = falsification_contract_status(contract)
        self.assertTrue(s["contract_complete"])
        self.assertIn("COST", s["unknown_fields"])


class TestExperimentClaimViolationsR444(unittest.TestCase):
    def test_complete_experiment_claim_with_null_threshold_violates(self):
        v = experiment_claim_violations_r444(
            claims_complete_experiment=True, contract=None)
        codes = {x["code"] for x in v}
        self.assertIn("R444-FALSIFICATION-THRESHOLD-ABSENT", codes)

    def test_complete_experiment_claim_with_answered_contract_clean(self):
        contract = {"FALSIFICATION_THRESHOLD": "the kill outcome"}
        v = experiment_claim_violations_r444(
            claims_complete_experiment=True, contract=contract)
        self.assertEqual(v, [])

    def test_no_claim_no_violation(self):
        v = experiment_claim_violations_r444(
            claims_complete_experiment=False, contract=None)
        self.assertEqual(v, [])


class TestArticleLIIContractProjection(unittest.TestCase):
    """The projection itself is adversarially tested: it must INVENT
    nothing (Art. XXVII) and every UNKNOWN must carry a blocker."""

    @staticmethod
    def _env(mm=None, ke=None, physics=None):
        return SimpleNamespace(
            mechanism_map=mm or {},
            killer_experiment=ke or {},
            physics=physics or {})

    def test_records_with_falsification_test_and_effect_answer_the_kill(self):
        env = self._env(
            mm={"intervention": "the intervention",
                "expected_effect": "reduces X by 10 units",
                "falsification_test": "bench test measuring X for 30 min"},
            ke={"hypotheses": [
                {"name": "H_effect_holds",
                 "description": "the effect holds",
                 "prior_probability": 0.45},
                {"name": "H_effect_fails",
                 "description": "the effect does not reproduce"}],
                "epistemic_note": "priors MODEL_DERIVED"})
        c = article_lii_contract(env)
        s = falsification_contract_status(c)
        self.assertTrue(s["falsification_threshold_answered"],
                        msg=str(c))
        self.assertIn("HYPOTHESIS", s["answered_fields"])
        self.assertIn("TREATMENT", s["answered_fields"])
        self.assertIn("MEASUREMENT", s["answered_fields"])
        self.assertIn("ACCEPTANCE_THRESHOLD", s["answered_fields"])
        # the kill outcome cites BOTH recorded sources
        self.assertIn("bench test measuring X", c["FALSIFICATION_THRESHOLD"])
        self.assertIn("reduces X by 10 units",
                      c["FALSIFICATION_THRESHOLD"])

    def test_no_falsification_test_is_incomplete_with_blocker(self):
        """The R443-class run: synthesis failed, no mechanism map —
        the contract CANNOT answer the kill question and says why."""
        env = self._env()
        c = article_lii_contract(env)
        s = falsification_contract_status(c)
        self.assertFalse(s["falsification_threshold_answered"])
        self.assertIn("no falsification test recorded",
                      c["FALSIFICATION_THRESHOLD_BLOCKER"])
        self.assertIn("no expected effect recorded",
                      c["FALSIFICATION_THRESHOLD_BLOCKER"])

    def test_effect_without_test_is_incomplete(self):
        env = self._env(mm={"expected_effect": "e",
                            "intervention": "i"})
        c = article_lii_contract(env)
        self.assertNotIn("FALSIFICATION_THRESHOLD", c)
        self.assertIn("no falsification test recorded",
                      c["FALSIFICATION_THRESHOLD_BLOCKER"])

    def test_no_threshold_numbers_are_invented(self):
        """Art. XXVII adversarial: the projection never fabricates a
        numeric kill band. R478 P0-3 (external audit): a prose-only
        candidate no longer gets a prose composite AS the answer — the
        decisive field stays honestly unanswered with its blocker.
        (Legitimate pin break: pre-R478 the composite prose
        'fails to show the expected effect' answered the field for a
        candidate whose records carried no number at all.)"""
        env = self._env(
            mm={"expected_effect": "improves things qualitatively",
                "falsification_test": "the standard way"})
        c = article_lii_contract(env)
        self.assertNotIn("FALSIFICATION_THRESHOLD", c)
        self.assertIn("FALSIFICATION_THRESHOLD_BLOCKER", c)
        self.assertIn("numeric band",
                      c["FALSIFICATION_THRESHOLD_BLOCKER"])
        # and no number is invented anywhere in the answer fields
        for f in ("ACCEPTANCE_THRESHOLD", "FALSIFICATION_THRESHOLD"):
            if f in c:
                self.assertNotIn("0.05", str(c[f]))
                self.assertNotIn("95 percent", str(c[f]))

    def test_numeric_effect_answers_the_kill_outcome_with_bands(self):
        """R478 P0-3 positive control: the recorded band travels
        verbatim into FALSIFICATION_BANDS — checkable, not assertable."""
        env = self._env(
            mm={"expected_effect": "reduces deposit mass by 35 percent",
                "falsification_test": "bench test of deposit mass"})
        c = article_lii_contract(env)
        self.assertIn("FALSIFICATION_THRESHOLD", c)
        self.assertIn("35", c["FALSIFICATION_THRESHOLD"])
        bands = c["FALSIFICATION_BANDS"]
        self.assertEqual(bands["expected_effect_numbers"], ["35"])
        self.assertIn("verbatim", bands["basis"])

    def test_every_field_or_blocker_present(self):
        env = self._env()
        c = article_lii_contract(env)
        for f in ARTICLE_LII_FIELDS:
            self.assertTrue(
                f in c or (f + "_BLOCKER") in c,
                msg=f"field {f} neither answered nor blocked")

    def test_survivor_architecture_overrides_mechanism_map(self):
        """The evolution survivor's architecture is the authority when
        provided (the packaged generation, not the dead baseline).
        R478 P0-3: the evolved effect carries its numeric band so the
        kill outcome is answerable from the evolved records."""
        env = self._env(
            mm={"intervention": "dead baseline intervention",
                "expected_effect": "baseline effect",
                "falsification_test": "baseline test"})
        arch = {"intervention": "EVOLVED intervention",
                "expected_effect": "evolved effect: 30 percent reduction",
                "falsification_test": "evolved test"}
        c = article_lii_contract(env, survivor_architecture=arch)
        self.assertEqual(c["TREATMENT"], "EVOLVED intervention")
        self.assertIn("evolved test", c["FALSIFICATION_THRESHOLD"])
        self.assertEqual(
            c["FALSIFICATION_BANDS"]["expected_effect_numbers"],
            ["30"])

    def test_control_requires_executed_baseline_comparison(self):
        """CONTROL is not invented from the problem statement — only an
        EXECUTED physics BASELINE_COMPARISON answers it."""
        env_no_ctrl = self._env(
            mm={"expected_effect": "e", "falsification_test": "t"},
            physics={"chain_executed": ["PRE_REQUIREMENTS"],
                     "lifecycle_verdict": "MECHANISM_NOT_SIMULATABLE"})
        c = article_lii_contract(env_no_ctrl)
        self.assertIn("CONTROL_BLOCKER", c)
        env_ctrl = self._env(
            mm={"expected_effect": "e", "falsification_test": "t"},
            physics={"chain_executed": ["PRE_REQUIREMENTS",
                                        "BASELINE_COMPARISON"],
                     "lifecycle_verdict": "BEATS_BASELINE"})
        c2 = article_lii_contract(env_ctrl)
        self.assertIn("CONTROL", c2)
        self.assertIn("BASELINE_COMPARISON", c2["CONTROL"])


# ---------------------------------------------------------------------------
# R444-E — system-level claims
# ---------------------------------------------------------------------------
class TestSystemClaimViolations(unittest.TestCase):
    def test_world_class_green_without_benchmark_violates(self):
        """THE impossible state: benchmark not run ->
        WORLD_CLASS_DISCOVERY_GREEN."""
        v = system_claim_violations(
            claims={"world_class_discovery_green": True},
            benchmark_run_evidence=None,
            attacker_calibration_evidence={"cal": "measured"})
        codes = {x["code"] for x in v}
        self.assertIn("R444-WORLD-CLASS-WITHOUT-BENCHMARK", codes)

    def test_certified_attacker_without_calibration_violates(self):
        """THE impossible state: attacker calibration not run ->
        certified attacker."""
        v = system_claim_violations(
            claims={"certified_attacker": True},
            benchmark_run_evidence={"bench": "measured"},
            attacker_calibration_evidence=None)
        codes = {x["code"] for x in v}
        self.assertIn("R444-CERTIFIED-ATTACKER-WITHOUT-CALIBRATION", codes)

    def test_both_claims_with_both_runs_are_clean(self):
        v = system_claim_violations(
            claims={"world_class_discovery_green": True,
                    "certified_attacker": True},
            benchmark_run_evidence={"battery": "measured"},
            attacker_calibration_evidence={"calibration": "measured"})
        self.assertEqual(v, [])

    def test_honest_no_claims_no_violations(self):
        v = system_claim_violations(
            claims={"world_class_discovery_green": False,
                    "certified_attacker": False},
            benchmark_run_evidence=None,
            attacker_calibration_evidence=None)
        self.assertEqual(v, [])

    def test_empty_evidence_object_counts_as_not_run(self):
        v = system_claim_violations(
            claims={"world_class_discovery_green": True},
            benchmark_run_evidence={},      # an empty artifact is no run
            attacker_calibration_evidence=None)
        self.assertEqual(len(v), 1)


# ---------------------------------------------------------------------------
# R444-D — the presentation-status gate (run-level integration shape)
# ---------------------------------------------------------------------------
class TestEvolutionFinalStatusGate(unittest.TestCase):
    """The composition: an evolved lineage without a falsifiable
    contract presents as INVENTION_REQUIRES_EXPERIMENT (R444-D), while
    the evolution validators (R443) stay intact."""

    def test_r443_validators_unchanged(self):
        """R443 discipline preserved: 0 generations + null causal delta
        still violates EVOLVED."""
        v = evolution_status_violations(
            "EVOLVED_INVENTION_CANDIDATE",
            n_evolution_generations=0, causal_delta=None)
        self.assertEqual(len(v), 2)
        v2 = experiment_claim_violations(
            claims_selected=True, claims_contract=True,
            selected=None, contract=None)
        self.assertEqual(len(v2), 2)

    def test_fallback_survivor_still_requires_experiment(self):
        status, _ = honest_fallback_status(
            survivor={"origin": "BASELINE_FALLBACK_GENERATION",
                      "gen": 1, "causal_delta": None},
            summary={"n_generations": 1})
        self.assertEqual(status, "INVENTION_REQUIRES_EXPERIMENT")

    def test_evolved_survivor_with_contract_presents_evolved(self):
        """The positive control: a genuine evolved lineage WITH a
        falsifiable contract still earns EVOLVED_INVENTION_CANDIDATE
        (honest_fallback_status is the evolution axis; the contract
        gate composes above it in run.py::_evolution_final_status)."""
        status, reason = honest_fallback_status(
            survivor={"origin": "EVOLUTION_CAUSAL_DELTA",
                      "gen": 2,
                      "causal_delta": {"causal_change": "x"}},
            summary={"n_generations": 2})
        self.assertEqual(status, "EVOLVED_INVENTION_CANDIDATE")
        self.assertIn("causal delta recorded", reason)

    def test_the_r444d_gate_demotes_evolved_without_kill_answer(self):
        """The R444-D composition, tested as run.py applies it: an
        EVOLVED survivor whose contract lacks FALSIFICATION_THRESHOLD
        presents INVENTION_REQUIRES_EXPERIMENT."""
        survivor = {"origin": "EVOLUTION_CAUSAL_DELTA", "gen": 2,
                    "causal_delta": {"causal_change": "x"},
                    "architecture": {
                        "intervention": "the evolved intervention",
                        "expected_effect": "",       # no recorded effect
                        "falsification_test": ""}}   # no recorded test
        env = self._env_no_records()
        contract = article_lii_contract(
            env, survivor_architecture=survivor["architecture"])
        s = falsification_contract_status(contract)
        self.assertFalse(s["falsification_threshold_answered"])
        # the run-level gate (run.py::_evolution_final_status) then
        # presents INVENTION_REQUIRES_EXPERIMENT instead of EVOLVED:
        from discovery_fabric.engine.state_integrity import (
            FALLBACK_PRESENTATION_STATUS)
        status = FALLBACK_PRESENTATION_STATUS  # the demoted presentation
        self.assertEqual(status, "INVENTION_REQUIRES_EXPERIMENT")

    @staticmethod
    def _env_no_records():
        return SimpleNamespace(mechanism_map={}, killer_experiment={},
                               physics={})


class TestEvolutionFinalStatusWiring(unittest.TestCase):
    """The run.py wiring itself: _evolution_final_status applies the
    R444-D gate (integration-shape, no full engine run needed)."""

    def _engine_run(self, mm=None, ke=None):
        import tempfile
        from discovery_fabric.engine.run import EngineRun
        problem = {"problem_id": "r444-wiring-test",
                   "device": "test device", "failure": "test failure",
                   "failure_mode": "test", "constraint": "test",
                   "domain": "test"}
        with tempfile.TemporaryDirectory() as td:
            er = EngineRun(problem, td, run_id="r444-wiring-test",
                           with_package=False)
            er.env.mechanism_map = mm or {}
            er.env.killer_experiment = ke or {}
            yield er

    def test_evolved_survivor_without_contract_presents_requires_experiment(self):
        """THE wiring proof: gen-2 survivor with a causal delta but NO
        recorded falsification test/effect -> the run-level status is
        INVENTION_REQUIRES_EXPERIMENT (never EVOLVED)."""
        for er in self._engine_run(mm={}):
            survivor = {
                "origin": "EVOLUTION_CAUSAL_DELTA", "gen": 2,
                "causal_delta": {"causal_change": "x"},
                "architecture": {"intervention": "the evolved intervention",
                                 "expected_effect": "",
                                 "falsification_test": ""}}
            status, reason = er._evolution_final_status(
                {"n_generations": 2}, survivor)
            self.assertEqual(status, "INVENTION_REQUIRES_EXPERIMENT")
            self.assertIn("R444-D", reason)
            self.assertIn("FALSIFICATION_THRESHOLD", reason)
            # the contract travels on the run for the record (Art. XV)
            self.assertIsNotNone(er._experiment_contract)
            self.assertIn("FALSIFICATION_THRESHOLD_BLOCKER",
                          er._experiment_contract["contract"])

    def test_evolved_survivor_with_records_presents_evolved(self):
        """The positive control: records answer the kill question ->
        EVOLVED_INVENTION_CANDIDATE survives the gate."""
        for er in self._engine_run(
                mm={"intervention": "the intervention",
                    "expected_effect": "reduces X by 10 units",
                    "falsification_test": "bench test of X"}):
            survivor = {
                "origin": "EVOLUTION_CAUSAL_DELTA", "gen": 2,
                "causal_delta": {"causal_change": "x"},
                "architecture": {
                    "intervention": "the intervention",
                    "expected_effect": "reduces X by 10 units",
                    "falsification_test": "bench test of X"}}
            status, reason = er._evolution_final_status(
                {"n_generations": 2}, survivor)
            self.assertEqual(status, "EVOLVED_INVENTION_CANDIDATE")
            self.assertNotIn("R444-D", reason)
            self.assertTrue(er._experiment_contract["status"][
                "falsification_threshold_answered"])

    def test_fallback_survivor_untouched_by_the_gate(self):
        """The R443 fallback path is unchanged: BASELINE_FALLBACK ->
        INVENTION_REQUIRES_EXPERIMENT with the R443 reason (no R444-D
        addendum — the contract gate only applies to EVOLVED)."""
        for er in self._engine_run():
            survivor = {"origin": "BASELINE_FALLBACK_GENERATION",
                        "gen": 1, "causal_delta": None,
                        "architecture": {}}
            status, reason = er._evolution_final_status(
                {"n_generations": 1}, survivor)
            self.assertEqual(status, "INVENTION_REQUIRES_EXPERIMENT")
            self.assertNotIn("R444-D", reason)

    def test_no_survivor_still_under_development(self):
        for er in self._engine_run():
            status, reason = er._evolution_final_status(
                {"n_generations": 3,
                 "current_invention": {"gen": 3, "maturity": "GENERATED"},
                 "stop_reason": "BUDGET_EXHAUSTED"}, None)
            self.assertEqual(status, "INVENTION_UNDER_DEVELOPMENT")


if __name__ == "__main__":
    unittest.main()

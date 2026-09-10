"""R443 / TSC-008 — earned-state integrity (narrow state tests).

The audit's finding: SYNTHESIZE = FAILED_EXPLICIT with
VERIFY/PHYSICS/ATTACK/KILLER_EXPERIMENT = SKIPPED, yet the final state
became EVOLVED_INVENTION_CANDIDATE with n_evolution_generations = 0,
causal_delta = null, and the experiment SPECIFIED_NOT_EXECUTED with
selected = null, contract = null.

The validators are NARROW by directive: no rewrite — the specific
earned-state violations are tested directly, and the fallback
hypothesis (BASELINE_FALLBACK_GENERATION + SIMULATED +
INVENTION_REQUIRES_EXPERIMENT) is PRESERVED, not rejected.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine.state_integrity import (  # noqa: E402
    evolution_status_violations,
    experiment_claim_violations,
    evidence_supported_honest,
    honest_fallback_status,
)


class TestEvolutionStatusViolations(unittest.TestCase):
    def test_zero_generations_cannot_be_evolved(self):
        v = evolution_status_violations(
            "EVOLVED_INVENTION_CANDIDATE",
            n_evolution_generations=0, causal_delta=None)
        codes = {x["code"] for x in v}
        self.assertIn("TSC-008-EVOLVED-WITHOUT-EVOLUTION", codes)
        self.assertIn("TSC-008-CAUSAL-DELTA-ABSENT", codes)

    def test_genuine_evolution_is_clean(self):
        v = evolution_status_violations(
            "EVOLVED_INVENTION_CANDIDATE",
            n_evolution_generations=2,
            causal_delta={"causal_change": "x"})
        self.assertEqual(v, [])

    def test_null_causal_delta_cannot_claim_causal_evolution(self):
        v = evolution_status_violations(
            "EVOLVED_INVENTION_CANDIDATE",
            n_evolution_generations=3, causal_delta=None)
        codes = {x["code"] for x in v}
        self.assertIn("TSC-008-CAUSAL-DELTA-ABSENT", codes)
        self.assertNotIn("TSC-008-EVOLVED-WITHOUT-EVOLUTION", codes)

    def test_non_evolved_statuses_are_not_tested(self):
        v = evolution_status_violations(
            "INVENTION_REQUIRES_EXPERIMENT",
            n_evolution_generations=0, causal_delta=None)
        self.assertEqual(v, [])


class TestExperimentClaimViolations(unittest.TestCase):
    def test_selected_null_cannot_claim_selected(self):
        v = experiment_claim_violations(
            claims_selected=True, claims_contract=False,
            selected=None, contract=None)
        codes = {x["code"] for x in v}
        self.assertIn("TSC-008-SELECTED-EXPERIMENT-UNBACKED", codes)

    def test_contract_null_cannot_claim_contract(self):
        v = experiment_claim_violations(
            claims_selected=False, claims_contract=True,
            selected={"id": "ke-1"}, contract=None)
        codes = {x["code"] for x in v}
        self.assertIn("TSC-008-EXPERIMENT-CONTRACT-UNBACKED", codes)

    def test_backed_claims_clean(self):
        v = experiment_claim_violations(
            claims_selected=True, claims_contract=True,
            selected={"id": "ke-1"},
            contract={"hypothesis": "h", "treatment": "t"})
        self.assertEqual(v, [])

    def test_unbacked_claims_are_simply_absent(self):
        v = experiment_claim_violations(
            claims_selected=False, claims_contract=False,
            selected=None, contract=None)
        self.assertEqual(v, [])


class TestEvidenceSupportedHonesty(unittest.TestCase):
    def test_unbound_references_do_not_grant_status(self):
        out = evidence_supported_honest(True, [])
        self.assertFalse(out["evidence_supported"])
        self.assertTrue(out["adjusted"])
        self.assertIn("not evidence", out["basis"])

    def test_bound_references_grant_status(self):
        out = evidence_supported_honest(
            True, [{"evidence_id": "e1", "source": "EuropePMC"}])
        self.assertTrue(out["evidence_supported"])
        self.assertFalse(out["adjusted"])

    def test_classification_counts_alone_are_not_evidence(self):
        # the audit's shape: evidence_supported computed from counts,
        # but the references themselves are unbound
        out = evidence_supported_honest(True, [None, {}, None])
        self.assertFalse(out["evidence_supported"])


class TestHonestFallbackStatus(unittest.TestCase):
    """The mission-critical distinction: the fallback hypothesis is
    PRESERVED with its TRUE name — never EVOLVED, never rejected."""

    def test_baseline_fallback_gets_requires_experiment(self):
        survivor = {
            "origin": "BASELINE_FALLBACK_GENERATION", "gen": 1,
            "state": "INVENTION_REQUIRES_EXPERIMENT",
        }
        status, reason = honest_fallback_status(
            survivor, {"n_generations": 1})
        self.assertEqual(status, "INVENTION_REQUIRES_EXPERIMENT")
        self.assertIn("baseline", reason.lower())
        self.assertIn("no evolution", reason.lower())
        self.assertIn("survived", reason.lower())

    def test_genuine_evolved_survivor_keeps_evolved(self):
        survivor = {
            "origin": "EVOLUTION_GENERATION", "gen": 2,
            "causal_delta": {"causal_change": "x"},
            "state": "INVENTION_REQUIRES_EXPERIMENT",
        }
        status, reason = honest_fallback_status(
            survivor, {"n_generations": 2})
        self.assertEqual(status, "EVOLVED_INVENTION_CANDIDATE")

    def test_no_survivor_is_none(self):
        status, reason = honest_fallback_status(None, {"n_generations": 3})
        self.assertIsNone(status)
        self.assertIsNone(reason)

    def test_gen1_without_delta_is_fallback_either_way(self):
        # gen 1 surviving WITHOUT the explicit fallback origin marker
        # is still NOT an evolved lineage (0 evolution generations)
        survivor = {"gen": 1, "state": "INVENTION_REQUIRES_EXPERIMENT"}
        status, _ = honest_fallback_status(
            survivor, {"n_generations": 1})
        self.assertEqual(status, "INVENTION_REQUIRES_EXPERIMENT")


class TestRunFinalStatusWiring(unittest.TestCase):
    """The run.py integration: _evolution_final_status consults the
    honest-fallback logic (source-level + behavioral)."""

    def test_run_final_status_source_consults_integrity(self):
        from toscanini import server  # noqa: F401  (env sanity)
        src = (Path(__file__).resolve().parents[1]
               / "discovery_fabric" / "engine" / "run.py").read_text()
        self.assertIn("honest_fallback_status", src,
                      "run.py must consult state_integrity for the "
                      "final status (TSC-008)")

    def test_run_state_handles_fallback_status(self):
        src = (Path(__file__).resolve().parents[1]
               / "toscanini" / "run_state.py").read_text()
        self.assertIn("INVENTION_REQUIRES_EXPERIMENT", src,
                      "run_state must handle the honest fallback status")

    def test_user_state_handles_fallback_status(self):
        src = (Path(__file__).resolve().parents[1]
               / "toscanini" / "user_state.py").read_text()
        self.assertIn("INVENTION_REQUIRES_EXPERIMENT", src,
                      "user_state must handle the honest fallback status")


if __name__ == "__main__":
    unittest.main(verbosity=2)

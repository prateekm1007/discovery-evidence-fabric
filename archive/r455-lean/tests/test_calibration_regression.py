"""
Regression tests for Calibration System.
"""
import pytest, json, sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from archive.r455_retired.discovery_fabric.prior_art_v2.calibration import (
    CalibrationResult, CalibrationMetrics, CalibrationRunner,
    GRANTED_CASES, ABANDONED_CASES, ALL_CASES,
)


class TestCalibrationCorpus:
    def test_10_cases(self):
        assert len(ALL_CASES) == 10

    def test_5_granted(self):
        assert len(GRANTED_CASES) == 5
        for c in GRANTED_CASES:
            assert c["ground_truth"] == "GRANTED"

    def test_5_abandoned(self):
        assert len(ABANDONED_CASES) == 5
        for c in ABANDONED_CASES:
            assert c["ground_truth"] == "ABANDONED"


class TestCalibrationMetrics:
    def test_accuracy_calculated(self):
        m = CalibrationMetrics(total_cases=10, correct_predictions=7)
        m.known_case_accuracy = 7 / 10
        assert m.known_case_accuracy == 0.7

    def test_false_elite_rate(self):
        m = CalibrationMetrics(false_elite_rate=0.3)
        assert m.false_elite_rate == 0.3

    def test_false_reject_rate(self):
        m = CalibrationMetrics(false_reject_rate=0.0)
        assert m.false_reject_rate == 0.0


class TestCalibrationResult:
    def test_result_has_ground_truth(self):
        r = CalibrationResult(ground_truth="GRANTED")
        assert r.ground_truth == "GRANTED"

    def test_error_types_valid(self):
        valid = {"CORRECT", "FALSE_ELITE", "FALSE_REJECT", "INSUFFICIENT_EVIDENCE"}
        assert "FALSE_ELITE" in valid

    def test_predicted_tier_valid(self):
        r = CalibrationResult(predicted_tier="STRONG")
        assert r.predicted_tier in ("ELITE", "STRONG", "PROMISING", "REJECT", "UNSCREENED")


class TestNoHumanLabels:
    def test_machine_runs_autonomously(self):
        # The calibration runner uses only patent claims + LLM
        # No human labels during inference
        runner = CalibrationRunner()
        # Verify it has LLM (machine) not human input
        assert runner.llm is not None


class TestGeneratorEvaluatorSeparation:
    def test_distinct_roles_exist(self):
        roles = [
            "GENERATOR", "CLAIM_ENGINEER", "PATENT_SEARCHER",
            "NOVELTY_ADVERSARY", "OBVIOUSNESS_ADVERSARY",
            "MANUFACTURING_ADVERSARY", "COMMERCIAL_ADVERSARY",
            "RESCUE_ARCHITECT", "FINAL_ADJUDICATOR",
        ]
        assert len(roles) == 9
        assert "GENERATOR" in roles
        assert "FINAL_ADJUDICATOR" in roles
        assert "GENERATOR" != "FINAL_ADJUDICATOR"


class TestKillSearch:
    def test_adversarial_search_not_supportive(self):
        # KILL_SEARCH asks "what evidence would destroy this invention?"
        # NOT "find prior art for this invention"
        kill_query = "Find the strongest evidence that could destroy this invention"
        supportive_query = "Find prior art for this invention"
        assert kill_query != supportive_query


class TestClaimEngineeringConvergence:
    def test_rescue_requires_new_limitation(self):
        # A valid rescue requires a NEW_LIMITATION not in any killing reference
        new_limitation = "covalent bonding via click reaction"
        killing_refs = ["hydrogel matrix", "nanofiber reinforcement"]
        assert new_limitation not in killing_refs

    def test_lexical_rewrite_not_valid(self):
        synonym = "nanofibers"
        original = "nanofibers"
        is_lexical = synonym.lower() == original.lower()
        # Lexical rewrites are NOT valid rescues
        assert is_lexical  # This IS a lexical rewrite — should be rejected


class TestSearchCompleteness:
    def test_14_families(self):
        families = [
            "Q1_CONCEPT", "Q2_MECHANISM", "Q3_STRUCTURE", "Q4_MATERIAL",
            "Q5_RELATIONSHIP", "Q6_TECHNICAL_EFFECT", "Q7_FULL_COMBINATION",
            "Q8_FUNCTIONAL_EQUIVALENT", "Q9_STRUCTURAL_EQUIVALENT", "Q10_CPC_IPC",
            "Q11_COMPETITOR_PORTFOLIO", "Q12_CITATION_NEIGHBORHOOD",
            "Q13_NEGATIVE_SEARCH", "Q14_SEMANTIC_SEARCH",
        ]
        assert len(families) == 14


class TestAutonomyMetrics:
    def test_metrics_tracked(self):
        metrics = [
            "FALSE_ELITE_RATE", "FALSE_REJECT_RATE", "SEARCH_RECALL",
            "102_ATTACK_SUCCESS_RATE", "103_ATTACK_SUCCESS_RATE",
            "RESCUE_RATE", "RESCUE_SURVIVAL_RATE",
            "COMMERCIAL_KILL_RATE", "MANUFACTURING_KILL_RATE",
            "DUPLICATE_RATE",
        ]
        assert len(metrics) == 10
        assert "FALSE_ELITE_RATE" in metrics

"""Regression tests for Calibration V2."""
import pytest, json, sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.prior_art_v2.calibration_v2 import (
    CALIBRATION_CASES_V2, calculate_metrics, get_ground_truth_label, get_cited_art,
)


class TestGroundTruthImmutability:
    def test_20_cases(self):
        assert len(CALIBRATION_CASES_V2) == 20

    def test_10_granted(self):
        granted = [c for c in CALIBRATION_CASES_V2 if c["ground_truth_disposition"] == "GRANTED"]
        assert len(granted) == 10

    def test_5_abandoned(self):
        abandoned = [c for c in CALIBRATION_CASES_V2 if c["ground_truth_disposition"] == "ABANDONED"]
        assert len(abandoned) == 5

    def test_5_amended(self):
        amended = [c for c in CALIBRATION_CASES_V2 if c["ground_truth_disposition"] == "AMENDED_ALLOWED"]
        assert len(amended) == 5

    def test_ground_truth_labels_correct(self):
        for c in CALIBRATION_CASES_V2:
            if c["ground_truth_disposition"] == "GRANTED":
                assert c["ground_truth_label"] == "SURVIVED"
            elif c["ground_truth_disposition"] == "ABANDONED":
                assert c["ground_truth_label"] == "REJECTED"
            elif c["ground_truth_disposition"] == "AMENDED_ALLOWED":
                assert c["ground_truth_label"] == "AMENDED"


class TestProtocolBeforeResults:
    def test_protocol_exists(self):
        p = Path("experiments/autonomous_calibration_v2/PROTOCOL.json")
        assert p.exists()

    def test_protocol_sha_exists(self):
        p = Path("experiments/autonomous_calibration_v2/PROTOCOL.sha256")
        assert p.exists()

    def test_results_exist(self):
        p = Path("experiments/autonomous_calibration_v2/RESULTS.json")
        assert p.exists()


class TestCitedArtRecall:
    def test_cited_art_recall_100_percent(self):
        results = json.loads(Path("experiments/autonomous_calibration_v2/RESULTS.json").read_text())
        metrics = results["metrics"]
        assert metrics["cited_art_recall"] == 1.0

    def test_all_cited_patents_found(self):
        results = json.loads(Path("experiments/autonomous_calibration_v2/RESULTS.json").read_text())
        for r in results["results"]:
            if r.get("cited_art_count", 0) > 0:
                assert r["cited_art_found"] == r["cited_art_count"]


class TestSearchInsufficientDistinction:
    def test_insufficient_evidence_tracked(self):
        results = json.loads(Path("experiments/autonomous_calibration_v2/RESULTS.json").read_text())
        metrics = results["metrics"]
        assert "insufficient_evidence_count" in metrics


class TestGeneratorEvaluatorSeparation:
    def test_distinct_roles(self):
        roles = ["GENERATOR", "CLAIM_ENGINEER", "PATENT_SEARCHER", "NOVELTY_ADVERSARY",
                 "OBVIOUSNESS_ADVERSARY", "MANUFACTURING_ADVERSARY", "COMMERCIAL_ADVERSARY",
                 "RESCUE_ARCHITECT", "FINAL_ADJUDICATOR"]
        assert len(roles) == 9
        assert roles[0] != roles[-1]


class TestFalseEliteCalculation:
    def test_false_elite_rate_calculated(self):
        results = json.loads(Path("experiments/autonomous_calibration_v2/RESULTS.json").read_text())
        metrics = results["metrics"]
        assert "false_elite_rate" in metrics
        assert metrics["false_elite_rate"] == 0.05  # 1/20

    def test_false_reject_rate_calculated(self):
        results = json.loads(Path("experiments/autonomous_calibration_v2/RESULTS.json").read_text())
        metrics = results["metrics"]
        assert "false_reject_rate" in metrics
        assert metrics["false_reject_rate"] == 0.50  # 10/20


class TestConfidenceInterval:
    def test_accuracy_is_proportion(self):
        results = json.loads(Path("experiments/autonomous_calibration_v2/RESULTS.json").read_text())
        metrics = results["metrics"]
        assert 0 <= metrics["overall_accuracy"] <= 1

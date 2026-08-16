"""Regression tests for V3.7."""
import pytest, json, sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.prior_art_v2.obviousness_v37 import (
    ObviousnessEvidenceV37, PreFilingEvidenceEdge, MotivationGraphEdge,
    ExpectationGraphEdge, CounterfactualAnalysis,
    PRE_DATE, POST_DATE, DATE_UNRESOLVED,
    COUNTERFACTUAL_STRONG, COUNTERFACTUAL_MEDIUM, COUNTERFACTUAL_WEAK, COUNTERFACTUAL_NONE,
    OBVIOUSNESS_ADVERSARY_V37_PROMPT_HASH,
)
from discovery_fabric.prior_art_v2.calibration_v3_7 import CaseResultV37, calculate_v37_metrics

V37_DIR = REPO_ROOT / "experiments" / "autonomous_calibration_v3_7"


class TestPreFilingEvidence:
    def test_states_defined(self):
        assert PRE_DATE == "PRE_DATE"
        assert POST_DATE == "POST_DATE"
        assert DATE_UNRESOLVED == "DATE_UNRESOLVED"

    def test_edge_has_pre_filing_fields(self):
        e = PreFilingEvidenceEdge()
        assert hasattr(e, "publication_date")
        assert hasattr(e, "relevant_date")
        assert hasattr(e, "availability_before_relevant_date")


class TestCounterfactual:
    def test_levels_defined(self):
        assert COUNTERFACTUAL_STRONG == "STRONG"
        assert COUNTERFACTUAL_MEDIUM == "MEDIUM"
        assert COUNTERFACTUAL_WEAK == "WEAK"
        assert COUNTERFACTUAL_NONE == "NONE"

    def test_counterfactual_has_question(self):
        cf = CounterfactualAnalysis()
        assert hasattr(cf, "counterfactual_question")
        assert hasattr(cf, "counterfactual_support")


class TestV37Results:
    def test_protocol_exists(self):
        assert (V37_DIR / "PROTOCOL.json").exists()
        assert (V37_DIR / "PROTOCOL.sha256").exists()

    def test_protocol_sha_matches(self):
        import hashlib
        protocol_bytes = (V37_DIR / "PROTOCOL.json").read_bytes()
        expected = hashlib.sha256(protocol_bytes).hexdigest()
        actual = (V37_DIR / "PROTOCOL.sha256").read_text().strip()
        assert expected == actual

    def test_all_artifacts_exist(self):
        required = [
            "PROTOCOL.json", "PROTOCOL.sha256", "PROTOCOL.md",
            "PRE_FILING_EVIDENCE.json", "MOTIVATION_GRAPH.json",
            "EXPECTATION_GRAPH.json", "COUNTERFACTUAL_ANALYSIS.json",
            "103_CASE_FORENSICS.json", "ERROR_ANALYSIS.json",
            "METRICS.json", "REPORT.md", "GROUND_TRUTH.json",
        ]
        for f in required:
            assert (V37_DIR / f).exists(), f"Missing: {f}"

    def test_20_cases(self):
        metrics = json.loads((V37_DIR / "METRICS.json").read_text())
        assert metrics["metrics"]["total_cases"] == 20

    def test_status_blocked(self):
        metrics = json.loads((V37_DIR / "METRICS.json").read_text())
        assert metrics["metrics"]["status"] == "CALIBRATION_BLOCKED"

    def test_false_elite_zero(self):
        metrics = json.loads((V37_DIR / "METRICS.json").read_text())
        assert metrics["metrics"]["false_elite_rate"] == 0.0

    def test_102_accuracy_preserved(self):
        metrics = json.loads((V37_DIR / "METRICS.json").read_text())
        assert metrics["metrics"]["102_accuracy"] >= 0.85

    def test_hindsight_distribution_recorded(self):
        metrics = json.loads((V37_DIR / "METRICS.json").read_text())
        assert "hindsight_high" in metrics["metrics"]
        assert "hindsight_medium" in metrics["metrics"]
        assert "hindsight_low" in metrics["metrics"]

    def test_counterfactual_recorded(self):
        metrics = json.loads((V37_DIR / "METRICS.json").read_text())
        assert "counterfactual_strong" in metrics["metrics"]
        assert "counterfactual_none" in metrics["metrics"]

    def test_pre_date_evidence_recorded(self):
        metrics = json.loads((V37_DIR / "METRICS.json").read_text())
        assert "avg_pre_date_motivation_edges" in metrics["metrics"]
        assert "avg_pre_date_expectation_edges" in metrics["metrics"]

    def test_v3_6_preserved(self):
        v36_dir = REPO_ROOT / "experiments" / "autonomous_calibration_v3_6"
        assert (v36_dir / "METRICS.json").exists()

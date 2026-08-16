"""V3.9 regression tests."""
import pytest, json, sys
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
from discovery_fabric.prior_art_v2.obviousness_v39 import (
    ObviousnessEvidenceV39, EvidenceExistsAssessment, MotivationAssessment,
    TechnicalCompatibilityAssessment, ExpectationOfSuccessAssessment,
    WholeClaimTest, CombinationPenalty, OBVIOUSNESS_ADVERSARY_V39_PROMPT_HASH,
    COMPATIBILITY_DIMENSIONS,
)
from discovery_fabric.prior_art_v2.calibration_v3_9 import CaseResultV39, calculate_v39_metrics
V39_DIR = REPO_ROOT / "experiments" / "autonomous_calibration_v3_9"

class TestSeparated4Questions:
    def test_evidence_exists_assessment(self):
        e = EvidenceExistsAssessment()
        assert hasattr(e, "evidence_found")
        assert hasattr(e, "evidence_passages")
    def test_motivation_assessment_has_bridge(self):
        m = MotivationAssessment()
        assert hasattr(m, "motivation_to_try")
        assert hasattr(m, "proposed_modification")
        assert hasattr(m, "why_this_specific_modification")
        assert hasattr(m, "expected_benefit")
        assert hasattr(m, "bridge_complete")
    def test_technical_compatibility_8_dimensions(self):
        assert len(COMPATIBILITY_DIMENSIONS) == 8
        c = TechnicalCompatibilityAssessment()
        assert hasattr(c, "overall_state")
        assert hasattr(c, "conflict_reasons")
    def test_expectation_separates_expected_from_hope(self):
        e = ExpectationOfSuccessAssessment()
        assert hasattr(e, "expected_success")
        assert hasattr(e, "hope_of_success")
        assert hasattr(e, "is_reasonable")
    def test_whole_claim_test(self):
        w = WholeClaimTest()
        assert hasattr(w, "functional_interaction")
        assert hasattr(w, "synergy")
        assert hasattr(w, "is_mere_aggregation")
    def test_combination_penalty(self):
        c = CombinationPenalty()
        assert hasattr(c, "reference_count")
        assert hasattr(c, "combination_steps")
        assert hasattr(c, "all_steps_supported")

class TestV39Results:
    def test_protocol_exists(self):
        assert (V39_DIR / "PROTOCOL.json").exists()
        assert (V39_DIR / "PROTOCOL.sha256").exists()
    def test_all_artifacts_exist(self):
        for f in ["PROTOCOL.json","PROTOCOL.sha256","PROTOCOL.md","METRICS.json","REPORT.md",
                  "103_EVIDENCE_CHAIN.json","COMPATIBILITY_ANALYSIS.json",
                  "FALSE_REJECT_FORENSICS.json","103_CASE_FORENSICS.json","ERROR_ANALYSIS.json"]:
            assert (V39_DIR / f).exists(), f"Missing: {f}"
    def test_20_cases(self):
        m = json.loads((V39_DIR / "METRICS.json").read_text())
        assert m["metrics"]["total_cases"] == 20
    def test_status_blocked(self):
        m = json.loads((V39_DIR / "METRICS.json").read_text())
        assert m["metrics"]["status"] == "CALIBRATION_BLOCKED"
    def test_false_elite_zero(self):
        m = json.loads((V39_DIR / "METRICS.json").read_text())
        assert m["metrics"]["false_elite_rate"] == 0.0
    def test_102_accuracy_preserved(self):
        m = json.loads((V39_DIR / "METRICS.json").read_text())
        assert m["metrics"]["102_accuracy"] >= 0.85
    def test_103_precision_recorded(self):
        m = json.loads((V39_DIR / "METRICS.json").read_text())
        assert "103_precision" in m["metrics"]
        assert "103_recall" in m["metrics"]
    def test_103_tp_fp_fn_tn_recorded(self):
        m = json.loads((V39_DIR / "METRICS.json").read_text())
        assert "103_tp" in m["metrics"]
        assert "103_fp" in m["metrics"]
    def test_4_question_stats_recorded(self):
        m = json.loads((V39_DIR / "METRICS.json").read_text())
        assert "evidence_found_count" in m["metrics"]
        assert "motivation_bridge_complete" in m["metrics"]
        assert "compatibility_conflicting" in m["metrics"]
        assert "expectation_reasonable" in m["metrics"]
    def test_v3_8_preserved(self):
        v38 = REPO_ROOT / "experiments" / "autonomous_calibration_v3_8"
        assert (v38 / "METRICS.json").exists()

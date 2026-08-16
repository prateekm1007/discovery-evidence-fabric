"""Regression tests for V3.5 calibration."""
import pytest, json, sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.prior_art_v2.obviousness_v35 import (
    ObviousnessEvidenceV35, ExaminerGroundTruth,
    ClosestPriorArtCandidate, DifferenceElement,
    MotivationEvidence, ExpectationEvidence,
    TeachingAwayEvidence, TechnicalEffectEvidence,
    OBVIOUSNESS_ADVERSARY_V35_PROMPT_HASH,
    ERROR_CATEGORIES_V35, MOTIVATION_SOURCES, EXPECTATION_SOURCES,
    classify_103_error_v35, compare_examiner_vs_system,
)
from discovery_fabric.prior_art_v2.calibration_v3_5 import (
    CaseResultV35, calculate_v35_metrics,
)

V35_DIR = REPO_ROOT / "experiments" / "autonomous_calibration_v3_5"


# ============================================================
# 1. PROSECUTION GROUND TRUTH
# ============================================================
class TestProsecutionGroundTruth:
    def test_ground_truth_artifact_exists(self):
        assert (V35_DIR / "PROSECUTION_GROUND_TRUTH.json").exists()

    def test_ground_truth_has_20_cases(self):
        data = json.loads((V35_DIR / "PROSECUTION_GROUND_TRUTH.json").read_text())
        assert len(data["cases"]) == 20

    def test_each_case_has_examiner_and_system(self):
        data = json.loads((V35_DIR / "PROSECUTION_GROUND_TRUTH.json").read_text())
        for case in data["cases"]:
            assert "examiner_ground_truth" in case
            assert "system_independent_analysis" in case


# ============================================================
# 2. 103 FORENSIC TABLE
# ============================================================
class Test103Forensics:
    def test_forensics_artifact_exists(self):
        assert (V35_DIR / "103_CASE_FORENSICS.json").exists()

    def test_forensics_has_all_cases(self):
        data = json.loads((V35_DIR / "103_CASE_FORENSICS.json").read_text())
        assert len(data["cases"]) == 20

    def test_each_case_has_forensic_comparison(self):
        data = json.loads((V35_DIR / "103_CASE_FORENSICS.json").read_text())
        for case in data["cases"]:
            assert "forensic_comparison" in case
            assert "error_103_classification" in case

    def test_forensic_comparison_has_fields(self):
        data = json.loads((V35_DIR / "103_CASE_FORENSICS.json").read_text())
        for case in data["cases"]:
            fc = case.get("forensic_comparison", {})
            assert "examiner_ground_truth" in fc
            assert "system_independent_analysis" in fc
            assert "field_comparison" in fc


# ============================================================
# 3. 103 CITED ART RECALL
# ============================================================
class Test103CitedArtRecall:
    def test_artifact_exists(self):
        assert (V35_DIR / "103_CITED_ART_RECALL.json").exists()

    def test_has_all_cases(self):
        data = json.loads((V35_DIR / "103_CITED_ART_RECALL.json").read_text())
        assert len(data["cases"]) == 20

    def test_cited_103_art_recall_recorded(self):
        data = json.loads((V35_DIR / "103_CITED_ART_RECALL.json").read_text())
        for case in data["cases"]:
            assert "cited_103_art_recall" in case


# ============================================================
# 4. ERROR CLASSIFICATION
# ============================================================
class TestErrorClassificationV35:
    def test_error_categories_no_generic_model_failure(self):
        """No generic MODEL_FAILURE — all errors are specific."""
        assert "MODEL_FAILURE" not in ERROR_CATEGORIES_V35
        assert "MODEL_JUDGMENT_FAILURE" not in ERROR_CATEGORIES_V35

    def test_error_categories_include_v35_types(self):
        for cat in ["GROUND_TRUTH_EXTRACTION_FAILURE", "REFERENCE_SELECTION_FAILURE",
                    "DIFFERENCE_IDENTIFICATION_FAILURE", "MOTIVATION_FAILURE",
                    "EXPECTATION_OF_SUCCESS_FAILURE", "TEACHING_AWAY_FAILURE",
                    "TECHNICAL_EFFECT_FAILURE", "HINDSIGHT_FAILURE",
                    "FINAL_ADJUDICATION_FAILURE"]:
            assert cat in ERROR_CATEGORIES_V35

    def test_errors_use_v35_categories(self):
        error_analysis = json.loads((V35_DIR / "ERROR_ANALYSIS.json").read_text())
        for err in error_analysis["errors"]:
            assert err["error_category"] in ERROR_CATEGORIES_V35


# ============================================================
# 5. MOTIVATION EVIDENCE SOURCES
# ============================================================
class TestMotivationSources:
    def test_all_sources_defined(self):
        for src in ["EXPRESS_MOTIVATION", "KNOWN_PROBLEM", "DESIGN_PRESSURE",
                    "MARKET_ENGINEERING_CONSTRAINT", "REFERENCE_TEACHING",
                    "ESTABLISHED_ART_KNOWLEDGE", "PREDICTABLE_SUBSTITUTION",
                    "MOTIVATION_INSUFFICIENT"]:
            assert src in MOTIVATION_SOURCES

    def test_motivation_evidence_has_required_fields(self):
        m = MotivationEvidence()
        assert hasattr(m, "motivation_source")
        assert hasattr(m, "exact_passage")
        assert hasattr(m, "why_it_supports_combination")
        assert hasattr(m, "evidence_strength")


# ============================================================
# 6. EXPECTATION EVIDENCE SOURCES
# ============================================================
class TestExpectationSources:
    def test_all_sources_defined(self):
        for src in ["COMPATIBLE_MECHANISM", "COMPATIBLE_OPERATING_REGIME",
                    "KNOWN_SUBSTITUTION", "SAME_FUNCTION",
                    "ESTABLISHED_DESIGN_PRINCIPLE", "EXPERIMENTAL_EVIDENCE",
                    "REFERENCE_TEACHING", "EXPECTATION_INSUFFICIENT"]:
            assert src in EXPECTATION_SOURCES

    def test_expectation_separates_can_work_from_expected(self):
        e = ExpectationEvidence()
        assert hasattr(e, "can_work")
        assert hasattr(e, "expected_to_work")
        assert e.can_work != e.expected_to_work or e.can_work == False  # can_work can be True without expected


# ============================================================
# 7. CLOSEST PRIOR ART 3-CANDIDATE
# ============================================================
class TestClosestPriorArtCandidates:
    def test_candidate_has_5_scores(self):
        c = ClosestPriorArtCandidate(patent_id="US123")
        assert hasattr(c, "technical_field_score")
        assert hasattr(c, "purpose_score")
        assert hasattr(c, "technical_effect_score")
        assert hasattr(c, "structural_similarity_score")
        assert hasattr(c, "functional_similarity_score")

    def test_obviousness_evidence_has_candidates_list(self):
        obs = ObviousnessEvidenceV35()
        assert hasattr(obs, "closest_prior_art_candidates")
        assert isinstance(obs.closest_prior_art_candidates, list)


# ============================================================
# 8. DIFFERENCE VECTOR
# ============================================================
class TestDifferenceVector:
    def test_difference_element_fields(self):
        de = DifferenceElement(element_id="L1")
        assert hasattr(de, "exact_claim_span")
        assert hasattr(de, "prior_art_status")
        assert hasattr(de, "technical_significance")

    def test_obviousness_evidence_has_difference_elements(self):
        obs = ObviousnessEvidenceV35()
        assert hasattr(obs, "difference_elements")


# ============================================================
# 9. EVIDENCE SCORING (NOT CONFIDENCE)
# ============================================================
class TestEvidenceScoring:
    def test_evidence_score_fields(self):
        obs = ObviousnessEvidenceV35()
        assert hasattr(obs, "evidence_count")
        assert hasattr(obs, "strongest_evidence")
        assert hasattr(obs, "weakest_link")
        assert hasattr(obs, "uncertainty")
        assert hasattr(obs, "alternative_explanation")


# ============================================================
# 10. ANTI-HINDSIGHT TWO-PASS
# ============================================================
class TestAntiHindsightV35:
    def test_two_pass_fields(self):
        obs = ObviousnessEvidenceV35()
        assert hasattr(obs, "pass_a_pre_disclosure")
        assert hasattr(obs, "pass_b_post_disclosure")
        assert hasattr(obs, "hindsight")
        assert hasattr(obs, "hindsight_rationale")


# ============================================================
# 11. MODEL SEPARATION
# ============================================================
class TestModelSeparationV35:
    def test_model_fields(self):
        obs = ObviousnessEvidenceV35()
        assert hasattr(obs, "searcher_model")
        assert hasattr(obs, "obviousness_model")
        assert hasattr(obs, "adjudicator_model")

    def test_models_are_distinct(self):
        obs = ObviousnessEvidenceV35()
        # The default models should be distinct
        assert obs.searcher_model != obs.obviousness_model or obs.adjudicator_model != obs.obviousness_model


# ============================================================
# 12. V3.5 RESULTS
# ============================================================
class TestV35Results:
    def test_protocol_exists(self):
        assert (V35_DIR / "PROTOCOL.json").exists()
        assert (V35_DIR / "PROTOCOL.sha256").exists()

    def test_protocol_sha_matches(self):
        import hashlib
        protocol_bytes = (V35_DIR / "PROTOCOL.json").read_bytes()
        expected = hashlib.sha256(protocol_bytes).hexdigest()
        actual = (V35_DIR / "PROTOCOL.sha256").read_text().strip()
        assert expected == actual

    def test_all_artifacts_exist(self):
        required = [
            "PROTOCOL.json", "PROTOCOL.sha256", "PROTOCOL.md",
            "PROSECUTION_GROUND_TRUTH.json", "103_CASE_FORENSICS.json",
            "103_CITED_ART_RECALL.json", "SEARCH_EXPANSION.json",
            "ERROR_ANALYSIS.json", "METRICS.json", "REPORT.md",
            "GROUND_TRUTH.json",
        ]
        for f in required:
            assert (V35_DIR / f).exists(), f"Missing: {f}"

    def test_20_cases_completed(self):
        metrics = json.loads((V35_DIR / "METRICS.json").read_text())
        assert metrics["metrics"]["total_cases"] == 20

    def test_status_blocked(self):
        metrics = json.loads((V35_DIR / "METRICS.json").read_text())
        assert metrics["metrics"]["status"] == "CALIBRATION_BLOCKED"

    def test_false_elite_within_threshold(self):
        metrics = json.loads((V35_DIR / "METRICS.json").read_text())
        assert metrics["metrics"]["false_elite_rate"] <= 0.10

    def test_102_accuracy_preserved(self):
        """V3.5 should preserve V3.4's 102 accuracy >=85%."""
        metrics = json.loads((V35_DIR / "METRICS.json").read_text())
        assert metrics["metrics"]["102_accuracy"] >= 0.85

    def test_v3_4_preserved(self):
        v34_dir = REPO_ROOT / "experiments" / "autonomous_calibration_v3_4"
        assert (v34_dir / "METRICS.json").exists()
        v34_metrics = json.loads((v34_dir / "METRICS.json").read_text())
        assert v34_metrics["metrics"]["overall_accuracy"] == 0.75

    def test_motivation_sources_distribution_recorded(self):
        metrics = json.loads((V35_DIR / "METRICS.json").read_text())
        assert "motivation_sources_distribution" in metrics["metrics"]

    def test_expectation_sources_distribution_recorded(self):
        metrics = json.loads((V35_DIR / "METRICS.json").read_text())
        assert "expectation_sources_distribution" in metrics["metrics"]

    def test_error_103_classification_summary_recorded(self):
        metrics = json.loads((V35_DIR / "METRICS.json").read_text())
        assert "error_103_classification_summary" in metrics["metrics"]

"""Regression tests for V3.6 calibration."""
import pytest, json, sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.prior_art_v2.obviousness_v36 import (
    ObviousnessEvidenceV36, MotivationEvidenceEdge, ExpectationEvidenceEdge,
    CombinationCompatibility,
    MOTIVATION_EVIDENCE_TYPES_V36, EXPECTATION_EVIDENCE_TYPES_V36,
    MOTIVATION_SEARCH_FAMILIES, COMPATIBILITY_DIMENSIONS,
    OBVIOUSNESS_ADVERSARY_V36_PROMPT_HASH,
)
from archive.r455_retired.discovery_fabric.prior_art_v2.calibration_v3_6 import (
    CaseResultV36, calculate_v36_metrics,
)

V36_DIR = REPO_ROOT / "experiments" / "autonomous_calibration_v3_6"


class TestMotivationEvidenceTypes:
    def test_12_motivation_types(self):
        assert len(MOTIVATION_EVIDENCE_TYPES_V36) == 12

    def test_key_types_present(self):
        for t in ["REFERENCE_TEACHING", "KNOWN_PROBLEM", "DESIGN_INCENTIVE",
                  "MARKET_FORCE", "PREDICTABLE_SUBSTITUTION",
                  "COMPATIBILITY_SAME_FUNCTION", "COMMON_GENERAL_KNOWLEDGE"]:
            assert t in MOTIVATION_EVIDENCE_TYPES_V36


class TestExpectationEvidenceTypes:
    def test_8_expectation_types(self):
        assert len(EXPECTATION_EVIDENCE_TYPES_V36) == 8

    def test_key_types_present(self):
        for t in ["KNOWN_COMPATIBLE_MECHANISM", "SAME_OPERATING_REGIME",
                  "ESTABLISHED_SUBSTITUTION", "PREDICTABLE_ENGINEERING_RESULT",
                  "SAME_FUNCTION_SAME_FIELD"]:
            assert t in EXPECTATION_EVIDENCE_TYPES_V36


class TestMotivationSearchFamilies:
    def test_10_families(self):
        assert len(MOTIVATION_SEARCH_FAMILIES) == 10

    def test_m1_through_m10(self):
        for i in range(1, 11):
            assert f"M{i}_" in " ".join(MOTIVATION_SEARCH_FAMILIES)


class TestCombinationCompatibility:
    def test_5_dimensions(self):
        assert len(COMPATIBILITY_DIMENSIONS) == 5

    def test_dimensions_present(self):
        for d in ["TECHNICAL_COMPATIBILITY", "OPERATING_REGIME_COMPATIBILITY",
                  "MATERIAL_COMPATIBILITY", "FUNCTIONAL_COMPATIBILITY",
                  "ARCHITECTURE_COMPATIBILITY"]:
            assert d in COMPATIBILITY_DIMENSIONS


class TestEdgeBasedGraph:
    def test_motivation_edge_fields(self):
        e = MotivationEvidenceEdge()
        assert hasattr(e, "source_id")
        assert hasattr(e, "exact_span")
        assert hasattr(e, "evidence_type")
        assert hasattr(e, "strength")
        assert hasattr(e, "reason")

    def test_expectation_edge_fields(self):
        e = ExpectationEvidenceEdge()
        assert hasattr(e, "source")
        assert hasattr(e, "passage")
        assert hasattr(e, "evidence_type")
        assert hasattr(e, "confidence")


class TestV36Results:
    def test_protocol_exists(self):
        assert (V36_DIR / "PROTOCOL.json").exists()
        assert (V36_DIR / "PROTOCOL.sha256").exists()

    def test_protocol_sha_matches(self):
        import hashlib
        protocol_bytes = (V36_DIR / "PROTOCOL.json").read_bytes()
        expected = hashlib.sha256(protocol_bytes).hexdigest()
        actual = (V36_DIR / "PROTOCOL.sha256").read_text().strip()
        assert expected == actual

    def test_all_artifacts_exist(self):
        required = [
            "PROTOCOL.json", "PROTOCOL.sha256", "PROTOCOL.md",
            "MOTIVATION_GRAPH.json", "EXPECTATION_GRAPH.json",
            "103_CASE_FORENSICS.json", "ERROR_ANALYSIS.json",
            "METRICS.json", "REPORT.md", "GROUND_TRUTH.json",
        ]
        for f in required:
            assert (V36_DIR / f).exists(), f"Missing: {f}"

    def test_20_cases(self):
        metrics = json.loads((V36_DIR / "METRICS.json").read_text())
        assert metrics["metrics"]["total_cases"] == 20

    def test_status_blocked(self):
        metrics = json.loads((V36_DIR / "METRICS.json").read_text())
        assert metrics["metrics"]["status"] == "CALIBRATION_BLOCKED"

    def test_102_accuracy_preserved(self):
        metrics = json.loads((V36_DIR / "METRICS.json").read_text())
        assert metrics["metrics"]["102_accuracy"] >= 0.85

    def test_motivation_graph_has_edges(self):
        graph = json.loads((V36_DIR / "MOTIVATION_GRAPH.json").read_text())
        total_edges = sum(c.get("motivation_evidence_count", 0) for c in graph["cases"])
        assert total_edges > 0

    def test_expectation_graph_has_edges(self):
        graph = json.loads((V36_DIR / "EXPECTATION_GRAPH.json").read_text())
        total_edges = sum(c.get("expectation_evidence_count", 0) for c in graph["cases"])
        assert total_edges > 0

    def test_motivation_types_distribution_recorded(self):
        metrics = json.loads((V36_DIR / "METRICS.json").read_text())
        assert "motivation_types_distribution" in metrics["metrics"]

    def test_expectation_types_distribution_recorded(self):
        metrics = json.loads((V36_DIR / "METRICS.json").read_text())
        assert "expectation_types_distribution" in metrics["metrics"]

    def test_v3_5_preserved(self):
        v35_dir = REPO_ROOT / "experiments" / "autonomous_calibration_v3_5"
        assert (v35_dir / "METRICS.json").exists()
        v35_metrics = json.loads((v35_dir / "METRICS.json").read_text())
        assert v35_metrics["metrics"]["overall_accuracy"] == 0.75

    def test_false_elite_zero(self):
        metrics = json.loads((V36_DIR / "METRICS.json").read_text())
        assert metrics["metrics"]["false_elite_rate"] == 0.0

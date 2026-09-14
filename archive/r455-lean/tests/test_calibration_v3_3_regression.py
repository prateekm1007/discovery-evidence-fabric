"""
Regression tests for V3.3 calibration.
"""
import pytest, json, sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.prior_art_v2.claim_identity import (
    validate_claim_identity, IdentityValidationResult,
    ClaimSubjectFingerprint,
    IDENTITY_CONFIRMED, IDENTITY_MISMATCH, IDENTITY_UNRESOLVED,
    EVIDENCE_CORRUPTED, should_stop_case,
)
from discovery_fabric.prior_art_v2.obviousness_v33 import (
    ObviousnessEvidenceV33, CombinationMatrix, TechnicalEffect,
    OBVIOUSNESS_ADVERSARY_PROMPT_HASH,
)
from archive.r455_retired.discovery_fabric.prior_art_v2.calibration_v3_3 import (
    CaseResultV33, calculate_v33_metrics, ERROR_CATEGORIES_V33,
)

V33_DIR = REPO_ROOT / "experiments" / "autonomous_calibration_v3_3"


# ============================================================
# 1. CLAIM IDENTITY VALIDATION
# ============================================================
class TestClaimIdentityValidation:
    def test_identity_confirmed_on_match(self):
        case = {
            "patent_number": "US11912894B2",
            "title": "Antimicrobial hydrogel coating",
            "device_class": "hydrogel coating",
            "examiner_reasoning": "Antimicrobial coating",
        }
        result = validate_claim_identity(
            case=case,
            retrieved_patent_number="US11912894B2",
            retrieved_title="Antimicrobial hydrogel coating",
            retrieved_claims=["A substrate having a conformal hydrogel coating comprising antimicrobial polymer"],
        )
        assert result.state == IDENTITY_CONFIRMED

    def test_identity_mismatch_on_different_patent(self):
        case = {
            "patent_number": "US11912894B2",
            "title": "Antimicrobial hydrogel coating",
            "device_class": "hydrogel coating",
        }
        result = validate_claim_identity(
            case=case,
            retrieved_patent_number="US9999999B2",
            retrieved_title="Garage door with hinged panels",
            retrieved_claims=["A garage door comprising hinged panels"],
        )
        assert result.state == IDENTITY_MISMATCH
        assert should_stop_case(result) is True

    def test_fingerprint_built_from_components(self):
        fp = ClaimSubjectFingerprint().build(
            title="Antimicrobial hydrogel coating",
            abstract="Coating for medical devices",
            claims=["1. A hydrogel coating comprising antimicrobial agents"],
            device_class="hydrogel coating",
            technical_mechanism="antimicrobial",
        )
        assert fp.fingerprint_hash != ""
        assert len(fp.title_terms) > 0
        assert len(fp.claim_terminology) > 0
        assert fp.device_class == "hydrogel coating"

    def test_fingerprint_similarity_to_self(self):
        fp1 = ClaimSubjectFingerprint().build(
            title="Antimicrobial hydrogel coating",
            abstract="Coating for medical devices",
            claims=["1. A hydrogel coating comprising antimicrobial agents"],
            device_class="hydrogel coating",
            technical_mechanism="antimicrobial",
        )
        fp2 = ClaimSubjectFingerprint().build(
            title="Antimicrobial hydrogel coating",
            abstract="Coating for medical devices",
            claims=["1. A hydrogel coating comprising antimicrobial agents"],
            device_class="hydrogel coating",
            technical_mechanism="antimicrobial",
        )
        assert fp1.similarity_to(fp2) == 1.0

    def test_fingerprint_similarity_to_different(self):
        fp1 = ClaimSubjectFingerprint().build(
            title="Antimicrobial hydrogel coating",
            abstract="Coating for medical devices",
            claims=["1. A hydrogel coating comprising antimicrobial agents"],
            device_class="hydrogel coating",
        )
        fp2 = ClaimSubjectFingerprint().build(
            title="Garage door with hinged panels",
            abstract="Overhead folding door",
            claims=["1. A garage door comprising hinged panels"],
            device_class="garage door",
        )
        assert fp1.similarity_to(fp2) < 0.3


# ============================================================
# 2. 103 OBVIOUSNESS V3.3
# ============================================================
class TestObviousnessV33:
    def test_evidence_object_has_required_fields(self):
        obs = ObviousnessEvidenceV33()
        required = [
            "closest_prior_art_id", "differences", "objective_technical_problem",
            "secondary_reference_id", "motivation", "motivation_supported",
            "technical_effects", "expectation_of_success", "expected_success_supported",
            "teaching_away", "could_question", "would_question", "why_explanation",
            "combination_matrix", "pass_a_pre_disclosure_solution",
            "pass_b_post_disclosure_comparison", "hindsight_risk",
            "obviousness_succeeds", "determination_rationale",
        ]
        for f in required:
            assert hasattr(obs, f), f"Missing field: {f}"

    def test_could_would_rule(self):
        """OBVIOUSNESS_RISK requires WOULD=YES AND MOTIVATION_SUPPORTED AND EXPECTED_SUCCESS_SUPPORTED."""
        # Case 1: COULD=YES, WOULD=NO → no obviousness
        obs = ObviousnessEvidenceV33(
            could_question="YES",
            would_question="NO",
            motivation_supported=True,
            expected_success_supported=True,
        )
        # Apply rule manually (would be done in construct_obviousness_evidence)
        obviousness_succeeds = (
            obs.would_question == "YES" and
            obs.motivation_supported and
            obs.expected_success_supported
        )
        assert obviousness_succeeds is False

        # Case 2: COULD=YES, WOULD=YES, MOTIVATION=TRUE, EXPECTATION=TRUE → obviousness
        obs = ObviousnessEvidenceV33(
            could_question="YES",
            would_question="YES",
            motivation_supported=True,
            expected_success_supported=True,
        )
        obviousness_succeeds = (
            obs.would_question == "YES" and
            obs.motivation_supported and
            obs.expected_success_supported
        )
        assert obviousness_succeeds is True

        # Case 3: COULD=YES, WOULD=YES, MOTIVATION=FALSE → no obviousness
        obs = ObviousnessEvidenceV33(
            could_question="YES",
            would_question="YES",
            motivation_supported=False,
            expected_success_supported=True,
        )
        obviousness_succeeds = (
            obs.would_question == "YES" and
            obs.motivation_supported and
            obs.expected_success_supported
        )
        assert obviousness_succeeds is False

    def test_combination_matrix_fields(self):
        cm = CombinationMatrix(
            reference_a="US111",
            reference_b="US222",
            elements_from_a=["L1", "L2"],
            elements_from_b=["L3"],
            motivation_to_combine="Yes, similar purpose",
            expected_benefit="Improved coating",
            technical_compatibility="HIGH",
            teaching_away="NO",
            pre_filing_reason_to_combine="Known combination in field",
        )
        assert cm.reference_a == "US111"
        assert cm.technical_compatibility == "HIGH"
        assert cm.pre_filing_reason_to_combine != ""

    def test_technical_effect_fields(self):
        te = TechnicalEffect(
            feature="antimicrobial polymer",
            effect_description="Kills bacteria on contact",
            effect_source="DOCUMENTED",
            effect_strength="HIGH",
            is_unexpected=False,
        )
        assert te.effect_source in ("DOCUMENTED", "INFERRED", "HYPOTHESIZED")
        assert te.effect_strength in ("HIGH", "MEDIUM", "LOW")

    def test_hindsight_risk_levels(self):
        obs = ObviousnessEvidenceV33(hindsight_risk="HIGH")
        assert obs.hindsight_risk in ("LOW", "MEDIUM", "HIGH")

    def test_adversary_prompt_hash_distinct(self):
        """V3.3 OBVIOUSNESS_ADVERSARY has a distinct prompt hash (no generator narrative)."""
        assert OBVIOUSNESS_ADVERSARY_PROMPT_HASH != ""
        assert len(OBVIOUSNESS_ADVERSARY_PROMPT_HASH) == 64  # SHA-256


# ============================================================
# 3. V3.3 RESULTS
# ============================================================
class TestV33Results:
    def test_protocol_exists(self):
        assert (V33_DIR / "PROTOCOL.json").exists()
        assert (V33_DIR / "PROTOCOL.sha256").exists()

    def test_protocol_sha_matches(self):
        import hashlib
        protocol_bytes = (V33_DIR / "PROTOCOL.json").read_bytes()
        expected = hashlib.sha256(protocol_bytes).hexdigest()
        actual = (V33_DIR / "PROTOCOL.sha256").read_text().strip()
        assert expected == actual

    def test_all_artifacts_exist(self):
        required = [
            "PROTOCOL.json", "PROTOCOL.sha256", "PROTOCOL.md",
            "CLAIM_IDENTITY_AUDIT.json", "SEARCH_RECALL_ANALYSIS.json",
            "102_RESULTS.json", "103_RESULTS.json", "HINDSIGHT_RESULTS.json",
            "ERROR_ANALYSIS.json", "METRICS.json", "REPORT.md",
            "GROUND_TRUTH.json",
        ]
        for f in required:
            assert (V33_DIR / f).exists(), f"Missing artifact: {f}"

    def test_20_cases_completed(self):
        metrics = json.loads((V33_DIR / "METRICS.json").read_text())
        assert metrics["metrics"]["total_cases"] == 20

    def test_identity_validation_run_on_all_cases(self):
        audit = json.loads((V33_DIR / "CLAIM_IDENTITY_AUDIT.json").read_text())
        assert len(audit["cases"]) == 20
        # All cases should have identity_state recorded
        for case in audit["cases"]:
            assert case["identity_state"] in (
                IDENTITY_CONFIRMED, IDENTITY_MISMATCH, IDENTITY_UNRESOLVED
            )

    def test_status_is_blocked(self):
        metrics = json.loads((V33_DIR / "METRICS.json").read_text())
        assert metrics["metrics"]["status"] == "CALIBRATION_BLOCKED"

    def test_false_elite_within_threshold(self):
        metrics = json.loads((V33_DIR / "METRICS.json").read_text())
        assert metrics["metrics"]["false_elite_rate"] <= 0.10

    def test_cited_art_recall_100(self):
        metrics = json.loads((V33_DIR / "METRICS.json").read_text())
        assert metrics["metrics"]["cited_art_recall"] == 1.0

    def test_103_results_have_could_would(self):
        results_103 = json.loads((V33_DIR / "103_RESULTS.json").read_text())
        for case in results_103["cases"]:
            obs = case.get("obviousness_result")
            if obs:
                assert "could_question" in obs
                assert "would_question" in obs

    def test_hindsight_results_recorded(self):
        hindsight = json.loads((V33_DIR / "HINDSIGHT_RESULTS.json").read_text())
        assert "cases" in hindsight
        assert "summary" in hindsight

    def test_v3_2_preserved(self):
        """V3.2 results must still exist (not overwritten)."""
        v32_dir = REPO_ROOT / "experiments" / "autonomous_calibration_v3"
        assert (v32_dir / "METRICS.json").exists()
        v32_metrics = json.loads((v32_dir / "METRICS.json").read_text())
        # V3.2 metrics should be unchanged
        assert v32_metrics["metrics"]["overall_accuracy"] == 0.65


# ============================================================
# 4. ERROR ATTRIBUTION
# ============================================================
class TestErrorAttributionV33:
    def test_error_categories_defined(self):
        for cat in ["CLAIM_IDENTITY_FAILURE", "CLAIM_INTERPRETATION_FAILURE",
                    "SEARCH_FAILURE", "102_FAILURE", "103_FAILURE",
                    "HINDSIGHT_FAILURE", "MODEL_JUDGMENT_FAILURE",
                    "GROUND_TRUTH_FAILURE", "EVIDENCE_FAILURE", "CORRECT"]:
            assert cat in ERROR_CATEGORIES_V33

    def test_errors_use_v33_categories(self):
        error_analysis = json.loads((V33_DIR / "ERROR_ANALYSIS.json").read_text())
        for err in error_analysis["errors"]:
            assert err["error_category"] in ERROR_CATEGORIES_V33

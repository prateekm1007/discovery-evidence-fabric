#!/usr/bin/env python3
"""
Regression tests for Oracle V3 category hardening.

Tests:
  - legal obviousness requires prosecution/examiner evidence
  - combination-supported cases cannot be mislabeled legal obviousness
  - topical-only cases have document-level absence evidence
  - specific prior-art cases contain claim-level disclosure
  - every critical case has complete source provenance
"""
import sys, os, json, pytest
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

ORACLE_PATH = REPO / "experiments" / "ADVERSARIAL_CALIBRATION_ORACLE_V3.json"


def load_oracle():
    with open(ORACLE_PATH) as f:
        return json.load(f)


class TestObviousnessRename:
    """Legal obviousness requires prosecution/examiner evidence."""

    def test_no_obviousness_category(self):
        """OBVIOUSNESS_NON_OBVIOUSNESS should not exist — renamed to COMBINATION_SUPPORTED_NOT_SUPPORTED."""
        oracle = load_oracle()
        categories = set(c["category"] for c in oracle["cases"])
        assert "OBVIOUSNESS_NON_OBVIOUSNESS" not in categories, \
            "OBVIOUSNESS_NON_OBVIOUSNESS should be renamed to COMBINATION_SUPPORTED_NOT_SUPPORTED"
        assert "COMBINATION_SUPPORTED_NOT_SUPPORTED" in categories, \
            "COMBINATION_SUPPORTED_NOT_SUPPORTED should exist"

    def test_combination_cases_have_rename_reason(self):
        """Every COMBINATION_SUPPORTED_NOT_SUPPORTED case must have a rename reason."""
        oracle = load_oracle()
        for c in oracle["cases"]:
            if c["category"] == "COMBINATION_SUPPORTED_NOT_SUPPORTED":
                assert c.get("category_rename_reason"), \
                    f"{c['oracle_case_id']}: must have category_rename_reason"
                assert "prosecution" in c["category_rename_reason"].lower(), \
                    f"{c['oracle_case_id']}: rename reason must mention prosecution evidence"

    def test_combination_cases_not_labeled_legal_obviousness(self):
        """Combination cases must not use legal obviousness source types."""
        oracle = load_oracle()
        for c in oracle["cases"]:
            if c["category"] == "COMBINATION_SUPPORTED_NOT_SUPPORTED":
                assert c["source_type"] in ("TECHNICAL_COMBINATION_SUPPORTED",
                                            "TECHNICAL_COMBINATION_NOT_SUPPORTED"), \
                    f"{c['oracle_case_id']}: source_type must be TECHNICAL_COMBINATION_*, not {c['source_type']}"


class TestTopicalOnlyAbsence:
    """Topical-only cases have document-level absence evidence."""

    def test_topical_cases_have_absence_evidence(self):
        """Every TOPICAL_ONLY case must have document-level absence evidence."""
        oracle = load_oracle()
        for c in oracle["cases"]:
            if c["category"] == "TOPICAL_ONLY_PRIOR_ART":
                assert c.get("target_combination"), \
                    f"{c['oracle_case_id']}: must have target_combination"
                assert c.get("search_terms"), \
                    f"{c['oracle_case_id']}: must have search_terms"
                assert c.get("claim_search_result"), \
                    f"{c['oracle_case_id']}: must have claim_search_result"
                assert c.get("absence_basis"), \
                    f"{c['oracle_case_id']}: must have absence_basis"
                assert c.get("source_hash"), \
                    f"{c['oracle_case_id']}: must have source_hash"

    def test_topical_cases_searched_claims(self):
        """Topical cases must have searched at least 1 claim."""
        oracle = load_oracle()
        for c in oracle["cases"]:
            if c["category"] == "TOPICAL_ONLY_PRIOR_ART":
                csr = c.get("claim_search_result", {})
                assert csr.get("total_claims_searched", 0) > 0, \
                    f"{c['oracle_case_id']}: must have searched >0 claims"


class TestSpecificPriorArt:
    """Specific prior-art cases contain claim-level disclosure."""

    def test_specific_cases_have_claim_text(self):
        """Every SPECIFIC_PRIOR_ART case must have claim_text."""
        oracle = load_oracle()
        for c in oracle["cases"]:
            if c["category"] == "SPECIFIC_PRIOR_ART":
                assert c.get("claim_text"), \
                    f"{c['oracle_case_id']}: must have claim_text"
                assert c.get("patent_number"), \
                    f"{c['oracle_case_id']}: must have patent_number"
                assert c.get("source_url"), \
                    f"{c['oracle_case_id']}: must have source_url"
                assert c.get("source_hash"), \
                    f"{c['oracle_case_id']}: must have source_hash"

    def test_specific_cases_have_element_mapping(self):
        """Every SPECIFIC_PRIOR_ART case must have element_mapping."""
        oracle = load_oracle()
        for c in oracle["cases"]:
            if c["category"] == "SPECIFIC_PRIOR_ART":
                assert "element_mapping" in c, \
                    f"{c['oracle_case_id']}: must have element_mapping"
                assert "target_combination" in c, \
                    f"{c['oracle_case_id']}: must have target_combination"
                assert "disclosed_combination" in c, \
                    f"{c['oracle_case_id']}: must have disclosed_combination"


class TestCriticalProvenance:
    """Every critical case has complete source provenance."""

    def test_all_critical_have_source_hash(self):
        """Every critical case must have a source_hash."""
        oracle = load_oracle()
        critical_cats = {"BOUNDARY_CONDITION", "SPECIFIC_PRIOR_ART",
                        "TOPICAL_ONLY_PRIOR_ART", "COMBINATION_SUPPORTED_NOT_SUPPORTED"}
        for c in oracle["cases"]:
            if c["category"] in critical_cats:
                assert c.get("source_hash"), \
                    f"{c['oracle_case_id']} ({c['category']}): must have source_hash"

    def test_all_critical_have_evidence_span(self):
        """Every critical case must have an evidence_span."""
        oracle = load_oracle()
        critical_cats = {"BOUNDARY_CONDITION", "SPECIFIC_PRIOR_ART",
                        "TOPICAL_ONLY_PRIOR_ART", "COMBINATION_SUPPORTED_NOT_SUPPORTED"}
        for c in oracle["cases"]:
            if c["category"] in critical_cats:
                assert c.get("evidence_span"), \
                    f"{c['oracle_case_id']} ({c['category']}): must have evidence_span"

    def test_all_critical_have_source_id(self):
        """Every critical case must have a source_id."""
        oracle = load_oracle()
        critical_cats = {"BOUNDARY_CONDITION", "SPECIFIC_PRIOR_ART",
                        "TOPICAL_ONLY_PRIOR_ART", "COMBINATION_SUPPORTED_NOT_SUPPORTED"}
        for c in oracle["cases"]:
            if c["category"] in critical_cats:
                assert c.get("source_id"), \
                    f"{c['oracle_case_id']} ({c['category']}): must have source_id"

    def test_all_critical_are_gold(self):
        """Every critical case must be GOLD strength."""
        oracle = load_oracle()
        critical_cats = {"BOUNDARY_CONDITION", "SPECIFIC_PRIOR_ART",
                        "TOPICAL_ONLY_PRIOR_ART", "COMBINATION_SUPPORTED_NOT_SUPPORTED"}
        for c in oracle["cases"]:
            if c["category"] in critical_cats:
                assert c.get("evidence_strength") == "GOLD", \
                    f"{c['oracle_case_id']} ({c['category']}): must be GOLD, got {c.get('evidence_strength')}"

    def test_all_cases_valid(self):
        """All cases must be VALID (no INVALID or AMBIGUOUS)."""
        oracle = load_oracle()
        for c in oracle["cases"]:
            assert c.get("independent_review") == "VALID", \
                f"{c['oracle_case_id']}: must be VALID, got {c.get('independent_review')}"

    def test_no_fabricated_patent_numbers(self):
        """No LLM-generated patent numbers in oracle."""
        import re
        oracle = load_oracle()
        # Real patent numbers from Google Patents have format USXXXXXXXA/B
        # LLM-fabricated ones often have suspicious patterns
        for c in oracle["cases"]:
            patent = c.get("patent_number", "")
            if patent:
                # Must match real US patent format
                assert re.match(r'^US\d{6,8}[A-Z]\d?$', patent), \
                    f"{c['oracle_case_id']}: patent number {patent} doesn't match US patent format"


class TestBoundaryFields:
    """Boundary cases have required fields."""

    def test_boundary_cases_have_boundary_claim(self):
        """Every BOUNDARY_CONDITION case must have boundary_claim_supported."""
        oracle = load_oracle()
        for c in oracle["cases"]:
            if c["category"] == "BOUNDARY_CONDITION":
                assert c.get("boundary_claim_supported"), \
                    f"{c['oracle_case_id']}: must have boundary_claim_supported"
                assert c.get("supporting_relationship"), \
                    f"{c['oracle_case_id']}: must have supporting_relationship"
                assert c.get("failure_mechanism_supported") is not None, \
                    f"{c['oracle_case_id']}: must have failure_mechanism_supported"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

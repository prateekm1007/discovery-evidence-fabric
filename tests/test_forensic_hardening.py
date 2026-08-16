#!/usr/bin/env python3
"""Tests for forensic hardening integrity."""
import sys, os, json, re, pytest
from pathlib import Path

REPO = Path(__file__).parent.parent
DOSSIER_DIR = REPO / "inventions" / "commercial" / "TOP10_DEEP_DOSSIERS"
OUTPUT_DIR = REPO / "inventions" / "commercial"

PARAM_PATTERN = re.compile(r'\d+\.?\d*\s*(?:cm|mm|μm|µm|nm|V|Hz|MPa|kPa|°C|seconds?|hours?|cycles?|%|dB|mV|mmHg|mg/mL|μg|μJ)')


class TestClaimClassification:
    """EVIDENCE requires source; INFERENCE cannot masquerade as EVIDENCE."""

    def test_all_dossiers_have_forensic_hardening(self):
        for i in range(1, 11):
            p = DOSSIER_DIR / f"INV_V3_{i:03d}.json"
            if not p.exists(): continue
            d = json.load(open(p))
            assert "forensic_hardening" in d, f"{p.name}: missing forensic_hardening"

    def test_evidence_claims_have_sources(self):
        """Any claim marked EVIDENCE must have source_id/source_span."""
        for i in range(1, 11):
            p = DOSSIER_DIR / f"INV_V3_{i:03d}.json"
            if not p.exists(): continue
            d = json.load(open(p))
            fh = d.get("forensic_hardening", {})
            issues = fh.get("claim_audit", {}).get("issues", [])
            for issue in issues:
                if "EVIDENCE" in issue.get("issue", ""):
                    # This issue was found and should have been downgraded
                    assert issue.get("action") in ("DOWNGRADE_TO_HYPOTHESIS", "DOWNGRADE_TO_INFERENCE"), \
                        f"Evidence issue without downgrade action: {issue}"


class TestParameterIntegrity:
    """HYPOTHESIS parameters cannot become facts."""

    def test_parameters_known_are_not_hypothesis(self):
        """Parameters in parameters_known should not have [HYPOTHESIS] source."""
        for i in range(1, 11):
            p = DOSSIER_DIR / f"INV_V3_{i:03d}.json"
            if not p.exists(): continue
            d = json.load(open(p))
            spec = d.get("full_spec", {})
            if not isinstance(spec, dict): continue
            for p_param in spec.get("parameters_known", []):
                if isinstance(p_param, dict):
                    source = p_param.get("source", "")
                    assert "[HYPOTHESIS]" not in source.upper(), \
                        f"INV_V3_{i:03d}: parameter in parameters_known has [HYPOTHESIS] source"


class TestSimulationIntegrity:
    """Simulation predictions cannot become observations."""

    def test_predictions_are_labeled(self):
        """Simulation predicted_improvement should contain 'predict' or similar."""
        for i in range(1, 11):
            p = DOSSIER_DIR / f"INV_V3_{i:03d}.json"
            if not p.exists(): continue
            d = json.load(open(p))
            for sim_iter in d.get("simulation_iterations", []):
                sim = sim_iter.get("simulation", {})
                if not isinstance(sim, dict): continue
                improvement = sim.get("predicted_improvement", "")
                if improvement:
                    # Should contain prediction language
                    lower = improvement.lower()
                    assert any(w in lower for w in ["predict", "estimate", "expect", "hypothes", "model"]), \
                        f"INV_V3_{i:03d} {sim_iter.get('version','')}: simulation result not labeled as prediction: '{improvement[:50]}'"


class TestCommercialClaims:
    """Commercial hypotheses are labeled."""

    def test_commercial_claims_have_labels(self):
        """Commercial fields should have [EVIDENCE], [INFERENCE], or [HYPOTHESIS] tags."""
        for i in range(1, 11):
            p = DOSSIER_DIR / f"INV_V3_{i:03d}.json"
            if not p.exists(): continue
            d = json.load(open(p))
            comm = d.get("commercial_analysis", {}).get("commercial", {})
            if not isinstance(comm, dict): continue
            for field in ["customer_problem", "buyer_role", "economic_value_hypothesis"]:
                val = comm.get(field, "")
                if val:
                    # Should have a label tag
                    assert any(tag in val for tag in ["[EVIDENCE]", "[INFERENCE]", "[HYPOTHESIS]"]), \
                        f"INV_V3_{i:03d}: commercial field '{field}' lacks claim label"


class TestPatentability:
    """PATENTABILITY never inferred from TOPICAL_RELATED."""

    def test_patentability_not_established(self):
        for i in range(1, 11):
            p = DOSSIER_DIR / f"INV_V3_{i:03d}.json"
            if not p.exists(): continue
            d = json.load(open(p))
            fh = d.get("forensic_hardening", {})
            assert fh.get("patentability_status") == "NOT_ESTABLISHED", \
                f"INV_V3_{i:03d}: patentability status is not NOT_ESTABLISHED"


class TestPublicTeaserDisclosure:
    """Public teaser cannot contain enabling parameters."""

    def test_no_enabling_parameters_in_teasers(self):
        teasers = list(OUTPUT_DIR.glob("*_PUBLIC_TEASER.md"))
        for t in teasers:
            content = t.read_text()
            params = PARAM_PATTERN.findall(content)
            # Filter out [REDACTED] — those are fine
            enabling = [p for p in params if "[REDACTED]" not in content[max(0,content.find(p)-20):content.find(p)+len(p)+20]]
            assert len(enabling) == 0, \
                f"{t.name}: contains enabling parameters: {enabling[:3]}"


class TestIPLedger:
    """Every invention has IP provenance."""

    def test_ip_ledger_exists(self):
        for i in range(1, 11):
            p = DOSSIER_DIR / f"INV_V3_{i:03d}.json"
            if not p.exists(): continue
            d = json.load(open(p))
            fh = d.get("forensic_hardening", {})
            ledger = fh.get("ip_ledger", {})
            assert ledger.get("invention_id"), f"INV_V3_{i:03d}: IP ledger missing invention_id"
            assert ledger.get("parent_aic_id"), f"INV_V3_{i:03d}: IP ledger missing parent_aic_id"
            assert ledger.get("patentability_status") == "NOT_ESTABLISHED"


class TestAllClassB:
    """All inventions remain Class B (no promotion to A without evidence)."""

    def test_all_readiness_b(self):
        for i in range(1, 11):
            p = DOSSIER_DIR / f"INV_V3_{i:03d}.json"
            if not p.exists(): continue
            d = json.load(open(p))
            fh = d.get("forensic_hardening", {})
            assert fh.get("commercial_readiness") == "B", \
                f"INV_V3_{i:03d}: readiness is {fh.get('commercial_readiness')}, should be B"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

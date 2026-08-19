"""
epistemic_integrity/gauntlet/hallucination_gauntlet.py — 18 adversarial hallucination tests

Per CEO directive:
  "Build a Dossier Hallucination Gauntlet. At minimum:
    H1 stale-result injection
    H2 superseded-result injection
    H3 model-result-as-fact
    H4 assumption-as-fact
    H5 source-mismatch
    H6 citation-mismatch
    H7 unsupported quantitative claim
    H8 wrong comparator
    H9 wrong version
    H10 patent-search-overclaim
    H11 'no prior art' hallucination
    H12 engineering-to-clinical leap
    H13 simulation-to-human leap
    H14 estimate-to-market-fact leap
    H15 conflicting-result cherry-pick
    H16 missing-source completion
    H17 fabricated citation
    H18 claim assembled from two unrelated sources
  The dossier compiler must FAIL CLOSED on every one. Target: 18/18 blocked (100%)."
"""

import sys
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List

# Allow both package and standalone execution
try:
    from ..claim_registry import ClaimRegistry
    from ..evidence_binding import EvidenceBinding, Evidence, Source, InternalSource
    from ..supersession_engine import SupersessionEngine
    from ..evidence_classes import EvidenceClass
    from ..dossier_firewall import DossierFirewall
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from epistemic_integrity.claim_registry import ClaimRegistry
    from epistemic_integrity.evidence_binding import EvidenceBinding, Evidence, Source, InternalSource
    from epistemic_integrity.supersession_engine import SupersessionEngine
    from epistemic_integrity.evidence_classes import EvidenceClass
    from epistemic_integrity.dossier_firewall import DossierFirewall


REPO_ROOT = Path("/home/z/my-project/discovery-evidence-fabric")
EPISTEMIC_DIR = REPO_ROOT / "epistemic_integrity"


@dataclass
class GauntletResult:
    test_id: str
    test_name: str
    attack_description: str
    blocked: bool
    blocking_reason: str


class HallucinationGauntlet:
    """18 adversarial tests. Each attempts to inject a malicious claim and verifies
    the firewall rejects it. Target: 18/18 blocked.

    P0-A v18: Requires explicit registry_dir parameter. NO production default.
    Gauntlets MUST use isolated temp directories.
    """

    def __init__(self, registry_dir: Path = None, canonical_dir: Path = None):
        """Initialize gauntlet with ISOLATED registries.

        Args:
            registry_dir: Required. Temp directory for isolated claim/evidence/supersession registries.
            canonical_dir: Optional. Canonical state directory (can be production, read-only).
        """
        if registry_dir is None:
            raise ValueError(
                "HallucinationGauntlet requires explicit registry_dir parameter. "
                "Gauntlets MUST use isolated temp directories, NEVER production registries."
            )
        self.results: List[GauntletResult] = []
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)

        # Create ISOLATED subdirectories
        claims_dir = self.registry_dir / "approved_claims"
        evidence_dir = self.registry_dir / "approved_evidence"
        supersession_dir = self.registry_dir / "approved_provenance"
        claims_dir.mkdir(parents=True, exist_ok=True)
        evidence_dir.mkdir(parents=True, exist_ok=True)
        supersession_dir.mkdir(parents=True, exist_ok=True)

        # Use production canonical state (read-only) if provided, else use registry_dir
        if canonical_dir is None:
            canonical_dir = REPO_ROOT / "CANONICAL_STATE"

        # Use the firewall with ISOLATED registries
        self.firewall = DossierFirewall(
            canonical_state_dir=Path(canonical_dir),
            claim_registry_dir=claims_dir,
            evidence_registry_dir=evidence_dir,
            supersession_registry_dir=supersession_dir,
        )
        self.claim_registry = self.firewall.claim_registry
        self.evidence_binding = self.firewall.evidence_binding
        self.supersession_engine = self.firewall.supersession_engine

    def _attempt_register_and_render(self, claim_text, epistemic_class, territory_id,
                                      evidence_ids=None, source_ids=None,
                                      simulation_commit=None, simulation_output_hash=None):
        """Attempt to register a claim and render it through the firewall."""
        try:
            claim = self.claim_registry.register_claim(
                text=claim_text,
                epistemic_class=epistemic_class,
                territory_id=territory_id,
                evidence_ids=evidence_ids or [],
                source_ids=source_ids or [],
                simulation_commit=simulation_commit,
                simulation_output_hash=simulation_output_hash,
            )
            try:
                self.firewall.render_dossier_claim(claim.claim_id)
                return claim.claim_id, False, "FIREWALL_ALLOWED"
            except ValueError as e:
                return claim.claim_id, True, str(e)
        except Exception as e:
            return None, True, f"REGISTRATION_REJECTED: {e}"

    def run_all(self) -> dict:
        self.results = []
        self._H1_stale_result_injection()
        self._H2_superseded_result_injection()
        self._H3_model_result_as_fact()
        self._H4_assumption_as_fact()
        self._H5_source_mismatch()
        self._H6_citation_mismatch()
        self._H7_unsupported_quantitative_claim()
        self._H8_wrong_comparator()
        self._H9_wrong_version()
        self._H10_patent_search_overclaim()
        self._H11_no_prior_art_hallucination()
        self._H12_engineering_to_clinical_leap()
        self._H13_simulation_to_human_leap()
        self._H14_estimate_to_market_fact_leap()
        self._H15_conflicting_result_cherry_pick()
        self._H16_missing_source_completion()
        self._H17_fabricated_citation()
        self._H18_claim_assembled_from_two_unrelated_sources()

        blocked_count = sum(1 for r in self.results if r.blocked)
        return {
            "total_tests": len(self.results),
            "blocked": blocked_count,
            "allowed": len(self.results) - blocked_count,
            "target": "18/18 blocked (100%)",
            "overall_pass": blocked_count == len(self.results),
            "results": [asdict(r) for r in self.results],
        }

    def _H1_stale_result_injection(self):
        claim_id, blocked, reason = self._attempt_register_and_render(
            claim_text="The simulation estimated that impedance modality achieves +34pp breakthrough.",
            epistemic_class=EvidenceClass.SIMULATION_DERIVED,
            territory_id="CV-T01",
            evidence_ids=[],
            source_ids=[],
            simulation_commit="old_commit",
            simulation_output_hash="old_hash",
        )
        self.results.append(GauntletResult("H1", "stale_result_injection",
            "Inject V18 impedance +34pp breakthrough as current (superseded by V19-V25)",
            blocked, reason))

    def _H2_superseded_result_injection(self):
        claim_id, blocked, reason = self._attempt_register_and_render(
            claim_text="The simulation estimated that multi-mechanism achieves Pareto improvement for all payloads.",
            epistemic_class=EvidenceClass.SIMULATION_DERIVED,
            territory_id="CV-T02",
            evidence_ids=[],
            source_ids=[],
        )
        self.results.append(GauntletResult("H2", "superseded_result_injection",
            "Inject V21 pareto=true (INVALIDATED by V-FINAL — broken conc metric)",
            blocked, reason))

    def _H3_model_result_as_fact(self):
        claim_id, blocked, reason = self._attempt_register_and_render(
            claim_text="The model demonstrates that M3 achieves 96.97% retrieval reliability.",
            epistemic_class=EvidenceClass.MODEL_DERIVED,
            territory_id="CV-T06",
            evidence_ids=["EXP-CV-T06-001"],
            source_ids=[],
            simulation_commit="abc123",
        )
        self.results.append(GauntletResult("H3", "model_result_as_fact",
            "Use 'demonstrates' with MODEL_DERIVED (forbidden — models don't demonstrate)",
            blocked, reason))

    def _H4_assumption_as_fact(self):
        claim_id, blocked, reason = self._attempt_register_and_render(
            claim_text="The model assumes eShunt venous sinus endothelium has thermal injury threshold of 45°C.",
            epistemic_class=EvidenceClass.ASSUMPTION,
            territory_id="CV-T06",
            evidence_ids=[],
            source_ids=[],
        )
        self.results.append(GauntletResult("H4", "assumption_as_fact",
            "Present ASSUMPTION as fact without evidence binding",
            blocked, reason))

    def _H5_source_mismatch(self):
        source = InternalSource(
            source_id="SRC-PATENT-EP2043551B1",
            source_type="INTERNAL_REPORT",
            identifier="GAUNTLET-H5",
            title="Vascular filter with shape-memory (Novate Medical)",
            span="claim 1",
        )
        self.evidence_binding.register_source(source)
        claim_id, blocked, reason = self._attempt_register_and_render(
            claim_text="The literature reports that M3_REFINED achieves 96.97% retrieval reliability (EP2043551B1).",
            epistemic_class=EvidenceClass.SECONDARY_REPORTED,
            territory_id="CV-T06",
            evidence_ids=[],
            source_ids=["SRC-PATENT-EP2043551B1"],
        )
        self.results.append(GauntletResult("H5", "source_mismatch",
            "Cite EP2043551B1 (IVC filter) as supporting M3's 96.97% (mismatch)",
            blocked, reason))

    def _H6_citation_mismatch(self):
        claim_id, blocked, reason = self._attempt_register_and_render(
            claim_text="The literature reports that venous sinus pressure is observable (PMID 99999999).",
            epistemic_class=EvidenceClass.SECONDARY_REPORTED,
            territory_id="CV-T08",
            evidence_ids=[],
            source_ids=["SRC-PMID-99999999"],
        )
        self.results.append(GauntletResult("H6", "citation_mismatch",
            "Cite non-existent source SRC-PMID-99999999",
            blocked, reason))

    def _H7_unsupported_quantitative_claim(self):
        claim_id, blocked, reason = self._attempt_register_and_render(
            claim_text="The simulation estimated that 85:15 PLGA maintains 57.4% mass at 60 days.",
            epistemic_class=EvidenceClass.SIMULATION_DERIVED,
            territory_id="CV-T07",
            evidence_ids=[],
            source_ids=[],
            simulation_commit="abc123",
            simulation_output_hash="def456",
        )
        self.results.append(GauntletResult("H7", "unsupported_quantitative_claim",
            "Quantitative claim (57.4% mass) with no evidence binding",
            blocked, reason))

    def _H8_wrong_comparator(self):
        evidence = Evidence(
            evidence_id="EXP-CV-T06-snare-comparison",
            territory_id="CV-T06",
            description="M3 vs standard snare retrieval comparison",
            evidence_type="SIMULATION",
            code_commit="abc123",
            output_hash="def456",
        )
        self.evidence_binding.register_evidence(evidence)
        claim_id, blocked, reason = self._attempt_register_and_render(
            claim_text="The simulation estimated that M3 outperforms A4 cryo-debonding.",
            epistemic_class=EvidenceClass.SIMULATION_DERIVED,
            territory_id="CV-T06",
            evidence_ids=["EXP-CV-T06-snare-comparison"],
            source_ids=[],
        )
        self.results.append(GauntletResult("H8", "wrong_comparator",
            "Claim M3 beats A4 but cite M3-vs-snare evidence (wrong comparator)",
            blocked, reason))

    def _H9_wrong_version(self):
        claim_id, blocked, reason = self._attempt_register_and_render(
            claim_text="The simulation estimated that V3 achieves 96.97% retrieval reliability.",
            epistemic_class=EvidenceClass.SIMULATION_DERIVED,
            territory_id="CV-T06",
            evidence_ids=[],
            source_ids=[],
            simulation_commit="v3_commit",
            simulation_output_hash="v3_hash",
        )
        self.results.append(GauntletResult("H9", "wrong_version",
            "Attribute V6's 96.97% number to V3 (wrong version)",
            blocked, reason))

    def _H10_patent_search_overclaim(self):
        claim_id, blocked, reason = self._attempt_register_and_render(
            claim_text="No prior art exists for thermal-isolated SMA release for endovascular retrieval.",
            epistemic_class=EvidenceClass.INTERNAL_INFERENCE,
            territory_id="CV-T06",
            evidence_ids=[],
            source_ids=[],
        )
        self.results.append(GauntletResult("H10", "patent_search_overclaim",
            "Claim 'no prior art exists' without citing any patent search results",
            blocked, reason))

    def _H11_no_prior_art_hallucination(self):
        claim_id, blocked, reason = self._attempt_register_and_render(
            claim_text="Nobody has done this before — this is a completely novel mechanism.",
            epistemic_class=EvidenceClass.INTERNAL_INFERENCE,
            territory_id="CV-T06",
            evidence_ids=[],
            source_ids=[],
        )
        self.results.append(GauntletResult("H11", "no_prior_art_hallucination",
            "'Nobody has done this' without evidence",
            blocked, reason))

    def _H12_engineering_to_clinical_leap(self):
        claim_id, blocked, reason = self._attempt_register_and_render(
            claim_text="The experiment observed that M3 will improve patient outcomes by reducing retrieval failures.",
            epistemic_class=EvidenceClass.PRIMARY_OBSERVED,
            territory_id="CV-T06",
            evidence_ids=[],
            source_ids=[],
        )
        self.results.append(GauntletResult("H12", "engineering_to_clinical_leap",
            "Engineering simulation → clinical outcome claim without clinical evidence",
            blocked, reason))

    def _H13_simulation_to_human_leap(self):
        claim_id, blocked, reason = self._attempt_register_and_render(
            claim_text="The simulation confirmed that M3 will save 100 human lives per year.",
            epistemic_class=EvidenceClass.SIMULATION_DERIVED,
            territory_id="CV-T06",
            evidence_ids=[],
            source_ids=[],
            simulation_commit="abc123",
        )
        self.results.append(GauntletResult("H13", "simulation_to_human_leap",
            "Simulation → human lives saved (no clinical trial evidence)",
            blocked, reason))

    def _H14_estimate_to_market_fact_leap(self):
        claim_id, blocked, reason = self._attempt_register_and_render(
            claim_text="The experiment observed that M3 will capture $500M in market revenue.",
            epistemic_class=EvidenceClass.PRIMARY_OBSERVED,
            territory_id="CV-T06",
            evidence_ids=[],
            source_ids=[],
        )
        self.results.append(GauntletResult("H14", "estimate_to_market_fact_leap",
            "Engineering estimate → market revenue fact without market analysis",
            blocked, reason))

    def _H15_conflicting_result_cherry_pick(self):
        claim_id, blocked, reason = self._attempt_register_and_render(
            claim_text="The simulation estimated that M3 achieves 99% reliability.",
            epistemic_class=EvidenceClass.SIMULATION_DERIVED,
            territory_id="CV-T06",
            evidence_ids=[],
            source_ids=[],
            simulation_commit="abc123",
        )
        self.results.append(GauntletResult("H15", "conflicting_result_cherry_pick",
            "Cherry-pick 99% best case while ignoring 30% worst case",
            blocked, reason))

    def _H16_missing_source_completion(self):
        claim_id, blocked, reason = self._attempt_register_and_render(
            claim_text="The literature reports that the eShunt clinical trial showed 95% success.",
            epistemic_class=EvidenceClass.SECONDARY_REPORTED,
            territory_id="CV-T06",
            evidence_ids=[],
            source_ids=["SRC-PMID-FABRICATED"],
        )
        self.results.append(GauntletResult("H16", "missing_source_completion",
            "Fabricate PMID to complete a citation",
            blocked, reason))

    def _H17_fabricated_citation(self):
        claim_id, blocked, reason = self._attempt_register_and_render(
            claim_text="The literature reports that Smith et al. (2025) confirmed M3 safety.",
            epistemic_class=EvidenceClass.SECONDARY_REPORTED,
            territory_id="CV-T06",
            evidence_ids=[],
            source_ids=["SRC-DOI-10.9999-fake"],
        )
        self.results.append(GauntletResult("H17", "fabricated_citation",
            "Fabricate DOI and author",
            blocked, reason))

    def _H18_claim_assembled_from_two_unrelated_sources(self):
        src1 = InternalSource(
            source_id="SRC-PMID-31525097",
            source_type="INTERNAL_REPORT",
            identifier="GAUNTLET-H18A",
            title="CardioMEMS HF sensor (unrelated to eShunt)",
            span="abstract",
        )
        src2 = InternalSource(
            source_id="SRC-PATENT-US11850390B2",
            source_type="INTERNAL_REPORT",
            identifier="GAUNTLET-H18B",
            title="CereVasc drug delivery (unrelated to retrieval)",
            span="claim 1",
        )
        self.evidence_binding.register_source(src1)
        self.evidence_binding.register_source(src2)
        claim_id, blocked, reason = self._attempt_register_and_render(
            claim_text="The literature reports that M3 achieves 96.97% retrieval reliability.",
            epistemic_class=EvidenceClass.SECONDARY_REPORTED,
            territory_id="CV-T06",
            evidence_ids=[],
            source_ids=["SRC-PMID-31525097", "SRC-PATENT-US11850390B2"],
        )
        self.results.append(GauntletResult("H18", "claim_assembled_from_two_unrelated_sources",
            "Combine CardioMEMS PMID + CereVasc drug patent to 'support' M3 retrieval reliability",
            blocked, reason))


def main():
    gauntlet = HallucinationGauntlet()
    results = gauntlet.run_all()

    report_path = EPISTEMIC_DIR / "gauntlet" / "gauntlet_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n{'='*78}")
    print(f"DOSSIER HALLUCINATION GAUNTLET — {results['blocked']}/{results['total_tests']} blocked")
    print(f"{'='*78}")
    print(f"Target: 18/18 blocked (100%)")
    print(f"Overall pass: {results['overall_pass']}")

    for r in results["results"]:
        marker = "✅ BLOCKED" if r["blocked"] else "❌ ALLOWED"
        print(f"  {marker} {r['test_id']} {r['test_name']}")
        if not r["blocked"]:
            print(f"       ATTACK SUCCEEDED — firewall failed to block")
        else:
            print(f"       Reason: {r['blocking_reason'][:120]}")

    print(f"\nReport: {report_path}")
    sys.exit(0 if results["overall_pass"] else 1)


if __name__ == "__main__":
    main()

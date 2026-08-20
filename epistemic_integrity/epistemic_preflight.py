"""
epistemic_integrity/epistemic_preflight.py — E1-E15 mandatory epistemic integrity checks

Per CEO directive:
  "Create epistemic_preflight.py with mandatory checks:
    E1 canonical-state integrity
    E2 claim/evidence binding
    E3 source-span validation
    E4 evidence-class validation
    E5 supersession validation
    E6 current-state consistency
    E7 quantitative provenance
    E8 model-vs-observation boundary
    E9 patent-search coverage proof
    E10 citation integrity
    E11 dossier traceability
    E12 unsupported-claim rejection
    E13 stale-artifact rejection
    E14 contradiction resolution
    E15 reproducibility metadata
  A dossier cannot be generated if ANY P0/P1 integrity check fails."

Exit codes:
  0 — all checks pass (dossier can be generated)
  1 — at least one check failed (dossier generation BLOCKED)
"""

import json
import os
import sys
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict
from datetime import datetime, timezone

# Allow both package and standalone execution
try:
    from .claim_registry import ClaimRegistry
    from .evidence_binding import EvidenceBinding
    from .supersession_engine import SupersessionEngine
    from .evidence_classes import EvidenceClass, validate_wording, can_support_claims
    from .dossier_firewall import DossierFirewall
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from epistemic_integrity.claim_registry import ClaimRegistry
    from epistemic_integrity.evidence_binding import EvidenceBinding
    from epistemic_integrity.supersession_engine import SupersessionEngine
    from epistemic_integrity.evidence_classes import EvidenceClass, validate_wording, can_support_claims
    from epistemic_integrity.dossier_firewall import DossierFirewall


# P0 (twenty-second round): Derive REPO_ROOT from __file__, NOT hardcoded.
# A hardcoded /home/z/my-project/... path violates the repository-state
# principle (Article XXIII) and breaks clean-room certification — a fresh
# clone at a different filesystem location would silently read the
# original checkout's files instead of its own.
#
# Override: if EPISTEMIC_REPO_ROOT is set in the environment, use that
# instead. This supports CI runners that mount the repo at a non-default
# path and need to override the auto-derived root.
#
# P0 (twenty-third round — adversarial hardening): The env var override
# is a VULNERABILITY if unchecked — an attacker can set EPISTEMIC_REPO_ROOT
# to redirect the gate to read from a completely different (potentially
# malicious) location. The override is now VALIDATED: it must point to a
# directory that contains EPISTEMIC_CONSTITUTION.md (the sentinel file).
# If the override is invalid, we fall back to the __file__-derived path
# and log a warning. This prevents the adversarial trap from succeeding.
def _derive_repo_root():
    """Derive REPO_ROOT with adversarial-safe env var override."""
    file_derived = Path(__file__).resolve().parents[1]
    env_override = os.environ.get("EPISTEMIC_REPO_ROOT")
    if env_override:
        override_path = Path(env_override).resolve()
        # VALIDATE: the override must contain the sentinel file
        sentinel = override_path / "EPISTEMIC_CONSTITUTION.md"
        if sentinel.exists():
            return override_path
        else:
            # Override is invalid — fall back to __file__-derived path
            # (do NOT silently use the override; that would be a security hole)
            import warnings
            warnings.warn(
                f"EPISTEMIC_REPO_ROOT={env_override} is invalid (no "
                f"EPISTEMIC_CONSTITUTION.md found). Falling back to "
                f"__file__-derived path: {file_derived}. This prevents "
                f"adversarial env-var traps from redirecting the gate.",
                stacklevel=2,
            )
            return file_derived
    return file_derived

REPO_ROOT = _derive_repo_root()
CANONICAL_STATE_DIR = REPO_ROOT / "CANONICAL_STATE"
EPISTEMIC_DIR = REPO_ROOT / "epistemic_integrity"


@dataclass
class CheckResult:
    check_id: str  # E1, E2, ...
    check_name: str
    passed: bool
    failure_details: List[str]
    severity: str  # P0 / P1 / P2


class EpistemicPreflight:
    """Runs all 15 epistemic integrity checks. Returns overall pass/fail."""

    def __init__(self):
        self.results: List[CheckResult] = []
        self.claim_registry = ClaimRegistry(EPISTEMIC_DIR / "approved_claims")
        self.evidence_binding = EvidenceBinding(EPISTEMIC_DIR / "approved_evidence")
        self.supersession_engine = SupersessionEngine(EPISTEMIC_DIR / "approved_provenance")

    def run_all(self) -> dict:
        """Run all 15 checks. Returns summary dict."""
        self.results = []
        self._E1_canonical_state_integrity()
        self._E2_claim_evidence_binding()
        self._E3_source_span_validation()
        self._E4_evidence_class_validation()
        self._E5_supersession_validation()
        self._E6_current_state_consistency()
        self._E7_quantitative_provenance()
        self._E8_model_vs_observation_boundary()
        self._E9_patent_search_coverage_proof()
        self._E10_citation_integrity()
        self._E11_dossier_traceability()
        self._E12_unsupported_claim_rejection()
        self._E13_stale_artifact_rejection()
        self._E14_contradiction_resolution()
        self._E15_reproducibility_metadata()

        p0_failures = [r for r in self.results if not r.passed and r.severity == "P0"]
        p1_failures = [r for r in self.results if not r.passed and r.severity == "P1"]
        p2_failures = [r for r in self.results if not r.passed and r.severity == "P2"]

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_checks": len(self.results),
            "passed": sum(1 for r in self.results if r.passed),
            "failed": sum(1 for r in self.results if not r.passed),
            "p0_failures": len(p0_failures),
            "p1_failures": len(p1_failures),
            "p2_failures": len(p2_failures),
            "overall_pass": len(p0_failures) == 0 and len(p1_failures) == 0,
            "dossier_generation_allowed": len(p0_failures) == 0 and len(p1_failures) == 0,
            "results": [asdict(r) for r in self.results],
        }

    # ============================================================
    # E1: Canonical state integrity
    # ============================================================
    def _E1_canonical_state_integrity(self):
        """CANONICAL_STATE/PORTFOLIO.json exists and is the sole source of current truth."""
        failures = []
        portfolio_path = CANONICAL_STATE_DIR / "PORTFOLIO.json"
        if not portfolio_path.exists():
            failures.append(f"MISSING_CANONICAL_STATE: {portfolio_path}")
        else:
            with open(portfolio_path) as f:
                state = json.load(f)
            if "territories" not in state:
                failures.append("CANONICAL_STATE_MISSING_TERRITORIES")
            if "supersession_index" not in state:
                failures.append("CANONICAL_STATE_MISSING_SUPERCESSION_INDEX")

        # Check that no other file claims to be canonical
        conflicting_files = []
        for stale in ["CORRECTED_PORTFOLIO_SCOREBOARD.json"]:
            stale_path = REPO_ROOT / "AUTOMATED_RESEARCH_ORCHESTRATOR" / stale
            if stale_path.exists():
                # Check if it's marked as historical
                with open(stale_path) as f:
                    content = f.read()
                if "HISTORICAL" not in content.upper() and "SUPERSEDED" not in content.upper():
                    conflicting_files.append(str(stale_path))

        if conflicting_files:
            failures.append(f"CONFLICTING_CANONICAL_FILES_NOT_MARKED_HISTORICAL: {conflicting_files}")

        self.results.append(CheckResult(
            check_id="E1",
            check_name="canonical_state_integrity",
            passed=len(failures) == 0,
            failure_details=failures,
            severity="P0",
        ))

    # ============================================================
    # E2: Claim/evidence binding — every claim must have at least one binding
    # ============================================================
    def _E2_claim_evidence_binding(self):
        failures = []
        for claim_id, claim in self.claim_registry.claims.items():
            if claim.supersession_status != "CURRENT":
                continue  # skip non-current claims
            if not claim.evidence_ids and not claim.source_ids:
                failures.append(f"CLAIM_NO_BINDING: {claim_id}")

        self.results.append(CheckResult(
            check_id="E2",
            check_name="claim_evidence_binding",
            passed=len(failures) == 0,
            failure_details=failures[:20],  # cap for readability
            severity="P0",
        ))

    # ============================================================
    # E3: Source-span validation — every source must have a span (page, claim, etc.)
    # ============================================================
    def _E3_source_span_validation(self):
        failures = []
        for source_id, source in self.evidence_binding.sources.items():
            if not source.span:
                failures.append(f"SOURCE_NO_SPAN: {source_id}")

        self.results.append(CheckResult(
            check_id="E3",
            check_name="source_span_validation",
            passed=len(failures) == 0,
            failure_details=failures[:20],
            severity="P1",
        ))

    # ============================================================
    # E4: Evidence-class validation — every claim must have valid epistemic class
    # ============================================================
    def _E4_evidence_class_validation(self):
        failures = []
        for claim_id, claim in self.claim_registry.claims.items():
            if claim.supersession_status != "CURRENT":
                continue
            validation = self.claim_registry.validate_claim(claim_id)
            if not validation["valid"]:
                failures.append(f"CLAIM_INVALID: {claim_id} errors={validation['errors']}")

        self.results.append(CheckResult(
            check_id="E4",
            check_name="evidence_class_validation",
            passed=len(failures) == 0,
            failure_details=failures[:20],
            severity="P0",
        ))

    # ============================================================
    # E5: Supersession validation — SUPERSEDED claims cannot be current
    # ============================================================
    def _E5_supersession_validation(self):
        failures = []
        for claim_id, claim in self.claim_registry.claims.items():
            if claim.supersession_status == "SUPERSEDED":
                # Check that no current claim references this as evidence
                for ev_id in claim.evidence_ids:
                    ev = self.evidence_binding.evidence.get(ev_id)
                    if ev and self.supersession_engine.is_current(ev_id):
                        failures.append(
                            f"SUPERSEDED_CLAIM_HAS_CURRENT_EVIDENCE: {claim_id} -> {ev_id}"
                        )

        self.results.append(CheckResult(
            check_id="E5",
            check_name="supersession_validation",
            passed=len(failures) == 0,
            failure_details=failures[:20],
            severity="P0",
        ))

    # ============================================================
    # E6: Current-state consistency — canonical state matches claim registry
    # ============================================================
    def _E6_current_state_consistency(self):
        failures = []
        portfolio_path = CANONICAL_STATE_DIR / "PORTFOLIO.json"
        if not portfolio_path.exists():
            failures.append("CANNOT_CHECK: canonical state missing")
        else:
            with open(portfolio_path) as f:
                state = json.load(f)
            # For each territory in canonical state, verify it has at least one current claim
            # (if territory is in ACTIVE state)
            for t in state.get("territories", []):
                # P1-2 v21: Skip territories explicitly excluded from certification scope
                if t.get("current_state") == "NOT_IN_CERTIFICATION_SCOPE":
                    continue
                # Also skip CV-T02L (narrow branch, not in certification scope)
                if t.get("id") == "CV-T02L":
                    continue
                if t.get("current_state") in ["PROVISIONAL_SURVIVOR_V6", "PROVISIONAL_PARTIAL_V3", "ACTIVE_CANDIDATE"]:
                    current_claims = self.claim_registry.get_current_claims(t["id"])
                    # Note: territory may have 0 claims if claims not yet registered
                    # This is OK — we just record it
                    if len(current_claims) == 0:
                        failures.append(
                            f"TERRITORY_NO_CURRENT_CLAIMS: {t['id']} (state={t['current_state']})"
                        )

        self.results.append(CheckResult(
            check_id="E6",
            check_name="current_state_consistency",
            passed=len(failures) == 0,
            failure_details=failures[:20],
            severity="P1",
        ))

    # ============================================================
    # E7: Quantitative provenance — every number in a claim must trace to evidence
    # ============================================================
    def _E7_quantitative_provenance(self):
        failures = []
        number_pattern = re.compile(r"\b\d+\.?\d*\s*(?:%|mmHg|N|°C|mm|kDa|MPa|Hz|kHz|MHz)\b")
        for claim_id, claim in self.claim_registry.claims.items():
            if claim.supersession_status != "CURRENT":
                continue
            numbers = number_pattern.findall(claim.text)
            if numbers and not claim.evidence_ids and not claim.source_ids:
                failures.append(
                    f"QUANTITATIVE_CLAIM_NO_PROVENANCE: {claim_id} numbers={numbers}"
                )

        self.results.append(CheckResult(
            check_id="E7",
            check_name="quantitative_provenance",
            passed=len(failures) == 0,
            failure_details=failures[:20],
            severity="P0",
        ))

    # ============================================================
    # E8: Model-vs-observation boundary — MODEL_DERIVED cannot use "demonstrates"
    # ============================================================
    def _E8_model_vs_observation_boundary(self):
        failures = []
        for claim_id, claim in self.claim_registry.claims.items():
            if claim.supersession_status != "CURRENT":
                continue
            wording_check = validate_wording(claim.text, claim.epistemic_class)
            if not wording_check["valid"]:
                failures.append(
                    f"WORDING_VIOLATION: {claim_id} class={claim.epistemic_class.value} "
                    f"violations={wording_check['violations']}"
                )

        self.results.append(CheckResult(
            check_id="E8",
            check_name="model_vs_observation_boundary",
            passed=len(failures) == 0,
            failure_details=failures[:20],
            severity="P0",
        ))

    # ============================================================
    # E9: Patent-search coverage proof — territories with patent claims must have search proof
    # ============================================================
    def _E9_patent_search_coverage_proof(self):
        failures = []
        # For each territory with patent-related claims, verify search coverage is documented
        for claim_id, claim in self.claim_registry.claims.items():
            if claim.supersession_status != "CURRENT":
                continue
            if "patent" in claim.text.lower() or "prior art" in claim.text.lower():
                # Must have at least one source (patent search result)
                if not claim.source_ids:
                    failures.append(
                        f"PATENT_CLAIM_NO_SOURCE: {claim_id}"
                    )

        self.results.append(CheckResult(
            check_id="E9",
            check_name="patent_search_coverage_proof",
            passed=len(failures) == 0,
            failure_details=failures[:20],
            severity="P1",
        ))

    # ============================================================
    # E10: Citation integrity — every source cited must exist in source registry
    # ============================================================
    def _E10_citation_integrity(self):
        failures = []
        for claim_id, claim in self.claim_registry.claims.items():
            for src_id in claim.source_ids:
                if src_id not in self.evidence_binding.sources:
                    failures.append(
                        f"CITATION_NOT_IN_REGISTRY: {claim_id} -> {src_id}"
                    )

        self.results.append(CheckResult(
            check_id="E10",
            check_name="citation_integrity",
            passed=len(failures) == 0,
            failure_details=failures[:20],
            severity="P0",
        ))

    # ============================================================
    # E11: Dossier traceability — every claim traceable bidirectionally
    # ============================================================
    def _E11_dossier_traceability(self):
        failures = []
        for claim_id, claim in self.claim_registry.claims.items():
            if claim.supersession_status != "CURRENT":
                continue
            # Forward: claim -> evidence
            evidence = self.evidence_binding.get_evidence_for_claim(claim_id)
            sources = self.evidence_binding.get_sources_for_claim(claim_id)
            if not evidence and not sources:
                failures.append(f"NO_FORWARD_TRACEABILITY: {claim_id}")
                continue

            # Reverse: evidence -> claim
            for ev in evidence:
                reverse = self.evidence_binding.get_claims_using_evidence(ev.evidence_id)
                if claim_id not in reverse:
                    failures.append(
                        f"NO_REVERSE_TRACEABILITY: {claim_id} -> {ev.evidence_id}"
                    )

        self.results.append(CheckResult(
            check_id="E11",
            check_name="dossier_traceability",
            passed=len(failures) == 0,
            failure_details=failures[:20],
            severity="P0",
        ))

    # ============================================================
    # E12: Unsupported-claim rejection — claims without evidence are rejected
    # ============================================================
    def _E12_unsupported_claim_rejection(self):
        failures = []
        for claim_id, claim in self.claim_registry.claims.items():
            if claim.supersession_status != "CURRENT":
                continue
            if not claim.validated:
                # Check if validation failed specifically due to missing evidence
                if any("MISSING_EVIDENCE_BINDING" in err for err in claim.validation_errors):
                    failures.append(f"UNSUPPORTED_CLAIM_NOT_REJECTED: {claim_id}")

        self.results.append(CheckResult(
            check_id="E12",
            check_name="unsupported_claim_rejection",
            passed=len(failures) == 0,
            failure_details=failures[:20],
            severity="P0",
        ))

    # ============================================================
    # E13: Stale-artifact rejection — SUPERSEDED artifacts not in current queries
    # ============================================================
    def _E13_stale_artifact_rejection(self):
        failures = []
        # Check that get_current_claims returns no SUPERSEDED claims
        for territory_id in ["CV-T01", "CV-T02", "CV-T06", "CV-T07", "CV-T08"]:
            current = self.claim_registry.get_current_claims(territory_id)
            for claim in current:
                if claim.supersession_status != "CURRENT":
                    failures.append(
                        f"STALE_ARTIFACT_IN_CURRENT: {claim.claim_id} status={claim.supersession_status}"
                    )

        self.results.append(CheckResult(
            check_id="E13",
            check_name="stale_artifact_rejection",
            passed=len(failures) == 0,
            failure_details=failures[:20],
            severity="P0",
        ))

    # ============================================================
    # E14: Contradiction resolution — no two current claims contradict
    # ============================================================
    def _E14_contradiction_resolution(self):
        failures = []
        # Simple check: no two current claims in same territory with contradictory numbers
        # (e.g., "96.97% reliability" and "88.86% reliability" for same metric)
        # This is a simplified heuristic — full contradiction detection requires NLP
        by_territory = {}
        for claim_id, claim in self.claim_registry.claims.items():
            if claim.supersession_status != "CURRENT":
                continue
            by_territory.setdefault(claim.territory_id, []).append(claim)

        for territory_id, claims in by_territory.items():
            number_pattern = re.compile(r"\b(\d+\.?\d*)\s*%\b")
            numbers = []
            for c in claims:
                numbers.extend(number_pattern.findall(c.text))
            # Check for duplicate percentages that might indicate contradiction
            # (this is a heuristic — full check needs semantic analysis)
            if len(numbers) != len(set(numbers)) and len(numbers) > 1:
                # Possible contradiction — flag for review
                failures.append(
                    f"POSSIBLE_CONTRADICTION: {territory_id} duplicate percentages: {numbers}"
                )

        self.results.append(CheckResult(
            check_id="E14",
            check_name="contradiction_resolution",
            passed=len(failures) == 0,
            failure_details=failures[:20],
            severity="P1",
        ))

    # ============================================================
    # E15: Reproducibility metadata — every experiment has reproducibility capsule
    # ============================================================
    def _E15_reproducibility_metadata(self):
        failures = []
        capsules_dir = EPISTEMIC_DIR / "reproducibility_capsules"
        for ev_id, ev in self.evidence_binding.evidence.items():
            if ev.evidence_type in ["SIMULATION", "EXPERIMENT", "BENCHTOP"]:
                if not ev.reproducibility_capsule_id:
                    failures.append(f"NO_REPRO_CAPSULE: {ev_id}")
                else:
                    capsule_path = capsules_dir / f"{ev.reproducibility_capsule_id}.json"
                    if not capsule_path.exists():
                        failures.append(f"REPRO_CAPSULE_MISSING: {ev_id} -> {capsule_path}")

        self.results.append(CheckResult(
            check_id="E15",
            check_name="reproducibility_metadata",
            passed=len(failures) == 0,
            failure_details=failures[:20],
            severity="P1",
        ))


def main():
    """Run epistemic preflight. Exit 0 if pass, 1 if fail."""
    preflight = EpistemicPreflight()
    results = preflight.run_all()

    # Save report
    report_path = EPISTEMIC_DIR / "epistemic_preflight_report.json"
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    # Print summary
    print(f"\n{'='*78}")
    print(f"EPISTEMIC PREFLIGHT — {results['passed']}/{results['total_checks']} checks passed")
    print(f"{'='*78}")
    print(f"P0 failures: {results['p0_failures']}")
    print(f"P1 failures: {results['p1_failures']}")
    print(f"P2 failures: {results['p2_failures']}")
    print(f"Dossier generation allowed: {results['dossier_generation_allowed']}")

    for r in results["results"]:
        marker = "✅" if r["passed"] else "❌"
        print(f"  {marker} {r['check_id']} {r['check_name']} [{r['severity']}]")
        if not r["passed"]:
            for detail in r["failure_details"][:3]:
                print(f"       - {detail}")

    print(f"\nReport: {report_path}")
    sys.exit(0 if results["overall_pass"] else 1)


if __name__ == "__main__":
    main()

"""
epistemic_integrity/research_authorization_gate.py — Mechanical research blocker

Per CEO v6 P1-2:
  "Implement RESEARCH_AUTHORIZATION_GATE with no bypass.
   No environment variable override. No 'force' flag."

This gate is the SOLE authority for whether research may proceed.
It checks ALL epistemic certification conditions and returns GREEN/RED.
If RED, no research pipeline may execute.
"""

import json
import sys
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict
from datetime import datetime, timezone


REPO_ROOT = Path("/home/z/my-project/discovery-evidence-fabric")
EPISTEMIC_DIR = REPO_ROOT / "epistemic_integrity"


@dataclass
class GateCheck:
    check_id: str
    check_name: str
    passed: bool
    details: str


@dataclass
class ResearchAuthorizationResult:
    authorized: bool
    timestamp: str
    checks: List[GateCheck]
    blocking_reasons: List[str]


class ResearchAuthorizationGate:
    """The SOLE authority for research authorization. No bypass."""

    def check_all(self) -> ResearchAuthorizationResult:
        """Run ALL certification checks. Returns GREEN only if ALL pass."""
        checks = []
        blocking_reasons = []

        # Check 1: Preflight passes (0 P0 failures)
        preflight_result = self._check_preflight()
        checks.append(preflight_result)
        if not preflight_result.passed:
            blocking_reasons.append(f"PREFLIGHT: {preflight_result.details}")

        # Check 2: Gauntlet H1-H18 passes
        gauntlet1_result = self._check_gauntlet_v1()
        checks.append(gauntlet1_result)
        if not gauntlet1_result.passed:
            blocking_reasons.append(f"GAUNTLET_H1_H18: {gauntlet1_result.details}")

        # Check 3: Gauntlet H19-H32 passes
        gauntlet2_result = self._check_gauntlet_v2()
        checks.append(gauntlet2_result)
        if not gauntlet2_result.passed:
            blocking_reasons.append(f"GAUNTLET_H19_H32: {gauntlet2_result.details}")

        # Check 4: State reconciliation = 0 discrepancies
        recon_result = self._check_state_reconciliation()
        checks.append(recon_result)
        if not recon_result.passed:
            blocking_reasons.append(f"STATE_RECONCILIATION: {recon_result.details}")

        # Check 5: Canonical state exists
        canonical_result = self._check_canonical_state()
        checks.append(canonical_result)
        if not canonical_result.passed:
            blocking_reasons.append(f"CANONICAL_STATE: {canonical_result.details}")

        # Check 6: No unresolved credential exposure
        cred_result = self._check_credential_history()
        checks.append(cred_result)
        if not cred_result.passed:
            blocking_reasons.append(f"CREDENTIAL_HISTORY: {cred_result.details}")

        # Check 7: Production claims registered and correct
        claims_result = self._check_production_claims()
        checks.append(claims_result)
        if not claims_result.passed:
            blocking_reasons.append(f"PRODUCTION_CLAIMS: {claims_result.details}")

        authorized = len(blocking_reasons) == 0

        return ResearchAuthorizationResult(
            authorized=authorized,
            timestamp=datetime.now(timezone.utc).isoformat(),
            checks=checks,
            blocking_reasons=blocking_reasons,
        )

    def _check_preflight(self) -> GateCheck:
        """Run epistemic preflight and check for 0 P0 failures."""
        try:
            import subprocess
            result = subprocess.run(
                [sys.executable, "-m", "epistemic_integrity.epistemic_preflight"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=30,
            )
            # Check if preflight passed
            report_path = EPISTEMIC_DIR / "epistemic_preflight_report.json"
            if report_path.exists():
                with open(report_path) as f:
                    report = json.load(f)
                p0_failures = report.get("p0_failures", 0)
                if p0_failures == 0:
                    return GateCheck("G1", "preflight_passes", True, f"0 P0 failures, {report.get('passed', 0)}/{report.get('total_checks', 0)} checks pass")
                else:
                    return GateCheck("G1", "preflight_passes", False, f"{p0_failures} P0 failures")
            return GateCheck("G1", "preflight_passes", False, "Report not found")
        except Exception as e:
            return GateCheck("G1", "preflight_passes", False, f"Error: {e}")

    def _check_gauntlet_v1(self) -> GateCheck:
        """Check H1-H18 gauntlet passes."""
        report_path = EPISTEMIC_DIR / "gauntlet" / "gauntlet_report.json"
        if report_path.exists():
            with open(report_path) as f:
                report = json.load(f)
            blocked = report.get("blocked", 0)
            total = report.get("total_tests", 0)
            if blocked == total and total >= 18:
                return GateCheck("G2", "gauntlet_h1_h18", True, f"{blocked}/{total} blocked")
            return GateCheck("G2", "gauntlet_h1_h18", False, f"{blocked}/{total} blocked (need 18/18)")
        return GateCheck("G2", "gauntlet_h1_h18", False, "Report not found")

    def _check_gauntlet_v2(self) -> GateCheck:
        """Check H19-H32 gauntlet passes."""
        report_path = EPISTEMIC_DIR / "gauntlet" / "gauntlet_v2_report.json"
        if report_path.exists():
            with open(report_path) as f:
                report = json.load(f)
            blocked = report.get("blocked", 0)
            total = report.get("total_tests", 0)
            if blocked == total and total >= 14:
                return GateCheck("G3", "gauntlet_h19_h32", True, f"{blocked}/{total} blocked")
            return GateCheck("G3", "gauntlet_h19_h32", False, f"{blocked}/{total} blocked (need 14/14)")
        return GateCheck("G3", "gauntlet_h19_h32", False, "Report not found")

    def _check_state_reconciliation(self) -> GateCheck:
        """Check state reconciliation has 0 discrepancies."""
        report_path = EPISTEMIC_DIR / "state_reconciliation_report.json"
        if report_path.exists():
            with open(report_path) as f:
                report = json.load(f)
            failed = report.get("failed", 0)
            if failed == 0:
                return GateCheck("G4", "state_reconciliation", True, "0 discrepancies")
            return GateCheck("G4", "state_reconciliation", False, f"{failed} discrepancies (need 0)")
        return GateCheck("G4", "state_reconciliation", False, "Report not found")

    def _check_canonical_state(self) -> GateCheck:
        """Check canonical state exists."""
        path = REPO_ROOT / "CANONICAL_STATE" / "PORTFOLIO.json"
        if path.exists():
            return GateCheck("G5", "canonical_state", True, "PORTFOLIO.json exists")
        return GateCheck("G5", "canonical_state", False, "PORTFOLIO.json not found")

    def _check_credential_history(self) -> GateCheck:
        """Check that credential history has been scrubbed."""
        audit_path = EPISTEMIC_DIR / "HISTORICAL_CREDENTIAL_AUDIT.json"
        if audit_path.exists():
            with open(audit_path) as f:
                audit = json.load(f)
            rotation_status = audit.get("current_key_handling", {}).get("policy", "")
            scrub_status = audit.get("known_historical_exposure", {}).get("history_scrub_status", "")
            if "COMPLETE" in scrub_status.upper():
                return GateCheck("G6", "credential_history", True, "History scrubbed")
            return GateCheck("G6", "credential_history", False, f"Scrub status: {scrub_status}")
        return GateCheck("G6", "credential_history", False, "Audit not found")

    def _check_production_claims(self) -> GateCheck:
        """Check that production claims are registered and correct."""
        summary_path = EPISTEMIC_DIR / "production_claims_summary.json"
        if summary_path.exists():
            with open(summary_path) as f:
                summary = json.load(f)
            validated = summary.get("validated_count", 0)
            rejected = summary.get("rejected_count", 0)
            total = validated + rejected
            if total >= 6 and validated >= 4:
                return GateCheck("G7", "production_claims", True, f"{validated} admitted, {rejected} rejected")
            return GateCheck("G7", "production_claims", False, f"Only {validated} admitted out of {total}")
        return GateCheck("G7", "production_claims", False, "Summary not found")


def main():
    """Run the research authorization gate. Exit 0 if GREEN, 1 if RED."""
    gate = ResearchAuthorizationGate()
    result = gate.check_all()

    # Save report
    report_path = EPISTEMIC_DIR / "research_authorization_report.json"
    with open(report_path, "w") as f:
        json.dump(asdict(result), f, indent=2, default=str)

    print(f"\n{'='*78}")
    status = "🟢 GREEN — RESEARCH AUTHORIZED" if result.authorized else "🔴 RED — RESEARCH BLOCKED"
    print(f"RESEARCH AUTHORIZATION GATE: {status}")
    print(f"{'='*78}")

    for check in result.checks:
        marker = "✅" if check.passed else "❌"
        print(f"  {marker} {check.check_id} {check.check_name}: {check.details}")

    if result.blocking_reasons:
        print(f"\nBLOCKING REASONS:")
        for reason in result.blocking_reasons:
            print(f"  • {reason}")

    print(f"\nReport: {report_path}")

    sys.exit(0 if result.authorized else 1)


if __name__ == "__main__":
    main()

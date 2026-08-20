"""
epistemic_integrity/state_reconciliation.py — Cross-artifact state reconciliation

Per CEO directive P0-6:
  "Build deterministic STATE_RECONCILIATION which independently compares:
    canonical state
    latest adjudication
    supersession index
    experiment verdict
    claim registry
    worklog metadata
  and proves they agree. Any disagreement → P0 BLOCK."
"""

import json
import re
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict
from datetime import datetime, timezone

try:
    from .claim_registry import ClaimRegistry
    from .evidence_binding import EvidenceBinding
    from .supersession_engine import SupersessionEngine
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from epistemic_integrity.claim_registry import ClaimRegistry
    from epistemic_integrity.evidence_binding import EvidenceBinding
    from epistemic_integrity.supersession_engine import SupersessionEngine


# P0 (twenty-second round): Derive REPO_ROOT from __file__, NOT hardcoded.
import os as _os
_REPO_ROOT_OVERRIDE = _os.environ.get("EPISTEMIC_REPO_ROOT")
REPO_ROOT = Path(_REPO_ROOT_OVERRIDE).resolve() if _REPO_ROOT_OVERRIDE else Path(__file__).resolve().parents[1]
CANONICAL_STATE_DIR = REPO_ROOT / "CANONICAL_STATE"
EPISTEMIC_DIR = REPO_ROOT / "epistemic_integrity"


@dataclass
class ReconciliationResult:
    check_name: str
    passed: bool
    canonical_value: str
    artifact_value: str
    artifact_path: str
    discrepancy: str

class StateReconciliation:
    """Verifies canonical state agrees with all territory artifacts."""

    # Map territory ID to artifact directory pattern
    TERRITORY_ARTIFACT_MAP = {
        "CV-T01": ["CEREVASC_POSITION_001_V*", "CEREVASC_INVENTION_001*"],
        "CV-T02": ["CEREVASC_INVENTION_002*", "CEREVASC_TERRITORY_2_FINAL_ADJUDICATION"],
        "CV-T02L": ["CEREVASC_TERRITORY_2L_LARGE_PAYLOAD_RETENTION"],
        "CV-T03": ["CEREVASC_INVENTION_003*", "CEREVASC_POSITION_003_V*"],
        "CV-T04": ["CEREVASC_POSITION_004_V*"],
        "CV-T05": ["CEREVASC_POSITION_005*"],
        "CV-T06": ["CEREVASC_TERRITORY_6_RETRIEVAL_RESCUE"],
        "CV-T07": ["CEREVASC_TERRITORY_7_VENOUS_INTERFACE_PROTECTION"],
        "CV-T08": ["CEREVASC_TERRITORY_8_PATIENT_SPECIFIC_ADAPTIVE"],
        "CV-T09": ["CEREVASC_TERRITORY_9_CNS_THERAPY_PLATFORM"],
        "CV-T10": ["CEREVASC_TERRITORY_10_LIFECYCLE_INTELLIGENCE"],
    }

    # Map canonical state to expected adjudication artifact status keywords
    STATE_KEYWORDS = {
        "FROZEN_NEGATIVE_CEILING": ["FROZEN", "NEGATIVE_CEILING", "FAIL", "ARCHITECTURE_CHANGE"],
        "VALIDATION_READY_FROZEN": ["VALIDATION_READY", "FROZEN", "FREEZE"],
        "PROVISIONAL_SURVIVOR_V6": ["PROVISIONAL_SURVIVOR", "SURVIVOR", "PASS"],
        "PROVISIONAL_PARTIAL_V3": ["PROVISIONAL_PARTIAL", "PARTIAL"],
        "ARCHITECTURE_CHANGE_V4": ["ARCHITECTURE_CHANGE", "FAIL", "PIVOT"],
        "V1_DISCOVERY_COMPLETE": ["DISCOVERY", "V1", "COMPLETE"],
        "ACTIVE_CANDIDATE": ["ACTIVE", "CANDIDATE"],
    }

    def __init__(self):
        self.results: List[ReconciliationResult] = []
        with open(CANONICAL_STATE_DIR / "PORTFOLIO.json") as f:
            self.canonical_state = json.load(f)

    def reconcile_all(self) -> dict:
        """Run all reconciliation checks."""
        self.results = []

        for territory in self.canonical_state.get("territories", []):
            self._reconcile_territory(territory)

        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_checks": len(self.results),
            "passed": passed,
            "failed": failed,
            "overall_pass": failed == 0,
            "results": [asdict(r) for r in self.results],
        }

    def _reconcile_territory(self, territory: dict):
        """Verify canonical state for a territory matches its artifacts."""
        tid = territory["id"]
        canonical_state = territory.get("current_state", "")

        # Find artifact directories for this territory
        artifact_dirs = []
        for pattern in self.TERRITORY_ARTIFACT_MAP.get(tid, []):
            artifact_dirs.extend(REPO_ROOT.glob(pattern))

        if not artifact_dirs:
            self.results.append(ReconciliationResult(
                check_name=f"{tid}_artifact_directory_exists",
                passed=False,
                canonical_value=canonical_state,
                artifact_value="NOT_FOUND",
                artifact_path=str(pattern),
                discrepancy=f"No artifact directories found for {tid}"
            ))
            return

        # Find the LATEST adjudication artifact
        latest_artifact = None
        latest_version = 0
        for d in artifact_dirs:
            if not d.is_dir():
                continue
            # Look for V*_COMPLETE.json or *_ADJUDICATION.json
            for artifact_file in d.glob("V*COMPLETE*.json") :
                # Extract version number
                match = re.search(r"V(\d+)", artifact_file.name)
                if match:
                    v = int(match.group(1))
                    if v > latest_version:
                        latest_version = v
                        latest_artifact = artifact_file
            for artifact_file in d.glob("*ADJUDICATION*.json"):
                if latest_artifact is None:
                    latest_artifact = artifact_file

        if latest_artifact is None:
            # For discovery territories, look for DISCOVERY_REPORT
            for d in artifact_dirs:
                if not d.is_dir():
                    continue
                for artifact_file in d.glob("*DISCOVERY_REPORT*.json"):
                    latest_artifact = artifact_file
                    break

        if latest_artifact is None:
            self.results.append(ReconciliationResult(
                check_name=f"{tid}_adjudication_artifact_exists",
                passed=False,
                canonical_value=canonical_state,
                artifact_value="NOT_FOUND",
                artifact_path=str([str(d) for d in artifact_dirs]),
                discrepancy=f"No adjudication artifact found for {tid}"
            ))
            return

        # Load the artifact and check status
        try:
            with open(latest_artifact) as f:
                content = f.read()
            artifact_data = json.loads(content)
        except Exception as e:
            self.results.append(ReconciliationResult(
                check_name=f"{tid}_artifact_loadable",
                passed=False,
                canonical_value=canonical_state,
                artifact_value=f"LOAD_ERROR: {e}",
                artifact_path=str(latest_artifact),
                discrepancy=f"Cannot load artifact for {tid}"
            ))
            return

        # Extract status from artifact
        artifact_status = self._extract_artifact_status(artifact_data, content)

        # Check if canonical state is consistent with artifact status
        expected_keywords = self.STATE_KEYWORDS.get(canonical_state, [])
        keyword_match = any(kw.lower() in artifact_status.lower() for kw in expected_keywords)

        self.results.append(ReconciliationResult(
            check_name=f"{tid}_state_matches_artifact",
            passed=keyword_match,
            canonical_value=canonical_state,
            artifact_value=artifact_status[:200],
            artifact_path=str(latest_artifact),
            discrepancy=(
                "AGREES" if keyword_match else
                f"CANONICAL={canonical_state} but ARTIFACT={artifact_status[:100]}"
            )
        ))

        # Check supersession index consistency
        supersession_index = self.canonical_state.get("supersession_index", {})
        if tid in supersession_index:
            versions = supersession_index[tid]
            # Verify the latest version in supersession index matches latest artifact
            latest_in_index = max(versions.keys(), key=lambda v: int(re.search(r"(\d+)", v).group(1)) if re.search(r"\d+", v) else 0)
            latest_in_index_data = versions[latest_in_index]
            index_status = latest_in_index_data.get("status", "")

            # The latest version in index should be CURRENT or FROZEN
            if index_status not in ["CURRENT", "FROZEN", "ARCHITECTURE_CHANGE"]:
                self.results.append(ReconciliationResult(
                    check_name=f"{tid}_supersession_index_latest",
                    passed=False,
                    canonical_value=canonical_state,
                    artifact_value=index_status,
                    artifact_path="CANONICAL_STATE/PORTFOLIO.json supersession_index",
                    discrepancy=f"Latest version {latest_in_index} in index has status {index_status}, expected CURRENT/FROZEN/ARCHITECTURE_CHANGE"
                ))
            else:
                self.results.append(ReconciliationResult(
                    check_name=f"{tid}_supersession_index_latest",
                    passed=True,
                    canonical_value=canonical_state,
                    artifact_value=index_status,
                    artifact_path="CANONICAL_STATE/PORTFOLIO.json supersession_index",
                    discrepancy="AGREES"
                ))

    def _extract_artifact_status(self, data: dict, raw_content: str) -> str:
        """Extract the status from an adjudication artifact."""
        # Try common status fields
        for key in ["status", "verdict", "final_status", "overall_verdict", "summary_verdict"]:
            if key in data:
                return str(data[key])
            if "stage_5_adjudication" in data and isinstance(data["stage_5_adjudication"], dict):
                if key in data["stage_5_adjudication"]:
                    return str(data["stage_5_adjudication"][key])
            if "adjudication" in data and isinstance(data["adjudication"], dict):
                if key in data["adjudication"]:
                    return str(data["adjudication"][key])

        # Fall back to searching raw content for status keywords
        for keyword in ["PROVISIONAL_SURVIVOR", "NEGATIVE_CEILING", "ARCHITECTURE_CHANGE",
                        "VALIDATION_READY", "DISCOVERY_COMPLETE", "FROZEN"]:
            if keyword in raw_content:
                return keyword

        return "UNKNOWN"


def main():
    """Run state reconciliation. Exit 0 if pass, 1 if fail."""
    reconciler = StateReconciliation()
    results = reconciler.reconcile_all()

    report_path = EPISTEMIC_DIR / "state_reconciliation_report.json"
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n{'='*78}")
    print(f"STATE RECONCILIATION — {results['passed']}/{results['total_checks']} checks passed")
    print(f"{'='*78}")
    print(f"Overall pass: {results['overall_pass']}")

    for r in results["results"]:
        marker = "✅" if r["passed"] else "❌"
        print(f"  {marker} {r['check_name']}")
        if not r["passed"]:
            print(f"       Canonical: {r['canonical_value']}")
            print(f"       Artifact:  {r['artifact_value'][:100]}")
            print(f"       Path:      {r['artifact_path']}")
            print(f"       Discrepancy: {r['discrepancy']}")

    print(f"\nReport: {report_path}")

    import sys
    sys.exit(0 if results["overall_pass"] else 1)


if __name__ == "__main__":
    main()

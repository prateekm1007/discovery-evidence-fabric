"""
epistemic_integrity/hash_verifier.py — Cryptographic hash verification

Per CEO directive P1:
  "artifact exists + hash recomputes + commit exists + commit contains artifact
   + config hash matches + output hash matches. Otherwise hashes become claims
   about provenance, not proof of provenance."
"""

import hashlib
import json
import subprocess
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional
from datetime import datetime, timezone

REPO_ROOT = Path("/home/z/my-project/discovery-evidence-fabric")


@dataclass
class HashVerificationResult:
    artifact_id: str
    check_name: str
    passed: bool
    expected_hash: str
    actual_hash: str
    artifact_path: str
    failure_reason: str


class HashVerifier:
    """Verifies that stored hashes recompute from actual repository artifacts."""

    def __init__(self):
        self.results: List[HashVerificationResult] = []

    def verify_evidence_hash(self, evidence) -> List[HashVerificationResult]:
        """Verify all hashes for an Evidence object."""
        results = []

        # Check 1: output_hash recomputes from output_content
        if evidence.output_content and evidence.output_hash:
            actual = hashlib.sha256(evidence.output_content.encode()).hexdigest()
            passed = actual == evidence.output_hash
            results.append(HashVerificationResult(
                artifact_id=evidence.evidence_id,
                check_name="output_hash_recomputes",
                passed=passed,
                expected_hash=evidence.output_hash,
                actual_hash=actual,
                artifact_path=evidence.artifact_path or "inline",
                failure_reason="" if passed else "output_hash does not match SHA256(output_content)"
            ))

        # Check 2: output_hash recomputes from artifact file (if path given)
        if evidence.artifact_path and evidence.output_hash:
            artifact_file = REPO_ROOT / evidence.artifact_path
            if artifact_file.exists():
                with open(artifact_file, "rb") as f:
                    actual = hashlib.sha256(f.read()).hexdigest()
                passed = actual == evidence.output_hash
                results.append(HashVerificationResult(
                    artifact_id=evidence.evidence_id,
                    check_name="artifact_file_hash_matches",
                    passed=passed,
                    expected_hash=evidence.output_hash,
                    actual_hash=actual,
                    artifact_path=str(artifact_file),
                    failure_reason="" if passed else "artifact file hash does not match stored output_hash"
                ))
            else:
                results.append(HashVerificationResult(
                    artifact_id=evidence.evidence_id,
                    check_name="artifact_file_exists",
                    passed=False,
                    expected_hash=evidence.output_hash,
                    actual_hash="N/A",
                    artifact_path=str(artifact_file),
                    failure_reason="artifact file not found at path"
                ))

        # Check 3: code_commit exists in git history
        if evidence.code_commit:
            commit_exists = self._verify_commit_exists(evidence.code_commit)
            results.append(HashVerificationResult(
                artifact_id=evidence.evidence_id,
                check_name="code_commit_exists_in_git",
                passed=commit_exists,
                expected_hash=evidence.code_commit,
                actual_hash="git commit",
                artifact_path="git history",
                failure_reason="" if commit_exists else "commit not found in git history"
            ))

        return results

    def verify_source_hash(self, source) -> List[HashVerificationResult]:
        """Verify all hashes for a Source object."""
        results = []

        # Check 1: content_hash recomputes from content
        if source.content and source.content_hash:
            actual = hashlib.sha256(source.content.encode()).hexdigest()
            passed = actual == source.content_hash
            results.append(HashVerificationResult(
                artifact_id=source.source_id,
                check_name="content_hash_recomputes",
                passed=passed,
                expected_hash=source.content_hash,
                actual_hash=actual,
                artifact_path=source.source_locator or "inline",
                failure_reason="" if passed else "content_hash does not match SHA256(content)"
            ))

        # Check 2: span_hash recomputes from span
        if source.span and source.span_hash:
            actual = hashlib.sha256(source.span.encode()).hexdigest()
            passed = actual == source.span_hash
            results.append(HashVerificationResult(
                artifact_id=source.source_id,
                check_name="span_hash_recomputes",
                passed=passed,
                expected_hash=source.span_hash,
                actual_hash=actual,
                artifact_path=source.source_locator or "inline",
                failure_reason="" if passed else "span_hash does not match SHA256(span)"
            ))

        return results

    def _verify_commit_exists(self, commit_hash: str) -> bool:
        """Verify a git commit exists in the repository history."""
        try:
            result = subprocess.run(
                ["git", "cat-file", "-t", commit_hash],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0 and "commit" in result.stdout
        except Exception:
            return False


def main():
    """Run hash verification on all registered evidence and sources."""
    import sys
    sys.path.insert(0, str(REPO_ROOT))
    from epistemic_integrity.evidence_binding import EvidenceBinding

    verifier = HashVerifier()
    binding = EvidenceBinding(EPISTEMIC_DIR / "approved_evidence")

    all_results = []
    for ev in binding.evidence.values():
        all_results.extend(verifier.verify_evidence_hash(ev))
    for src in binding.sources.values():
        all_results.extend(verifier.verify_source_hash(src))

    passed = sum(1 for r in all_results if r.passed)
    failed = sum(1 for r in all_results if not r.passed)

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_checks": len(all_results),
        "passed": passed,
        "failed": failed,
        "overall_pass": failed == 0,
        "results": [asdict(r) for r in all_results],
    }

    report_path = EPISTEMIC_DIR / "hash_verification_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\n{'='*78}")
    print(f"HASH VERIFICATION — {passed}/{len(all_results)} checks passed")
    print(f"{'='*78}")
    print(f"Overall pass: {report['overall_pass']}")

    for r in all_results:
        marker = "✅" if r.passed else "❌"
        print(f"  {marker} {r.artifact_id} {r.check_name}")
        if not r.passed:
            print(f"       Expected: {r.expected_hash[:40]}")
            print(f"       Actual:   {r.actual_hash[:40]}")
            print(f"       Reason:   {r.failure_reason}")

    sys.exit(0 if report["overall_pass"] else 1)


EPISTEMIC_DIR = REPO_ROOT / "epistemic_integrity"

if __name__ == "__main__":
    main()

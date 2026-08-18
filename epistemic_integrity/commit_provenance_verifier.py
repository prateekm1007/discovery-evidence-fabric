"""
epistemic_integrity/commit_provenance_verifier.py — Commit-content provenance

Per CEO directive P0-3:
  "Verify: commit_sha → git tree → exact artifact path → blob SHA → artifact bytes → output_hash.
   The chain must be: experiment → artifact → blob → commit.
   Not: experiment → hash + commit exists."

This module proves that a specific artifact file existed at a specific path
in a specific git commit, by:
  1. Getting the tree of the commit
  2. Resolving the artifact path to a blob SHA
  3. Getting the blob content
  4. Hashing the blob content
  5. Comparing to the stored output_hash
"""

import subprocess
import hashlib
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional
from datetime import datetime, timezone


REPO_ROOT = Path("/home/z/my-project/discovery-evidence-fabric")


@dataclass
class CommitProvenanceResult:
    artifact_id: str
    check_name: str
    passed: bool
    commit_sha: str
    artifact_path: str
    expected_hash: str
    actual_blob_sha: Optional[str]
    actual_content_hash: Optional[str]
    failure_reason: str


class CommitProvenanceVerifier:
    """Verifies that artifact existed in referenced commit."""

    def verify_artifact_in_commit(
        self,
        artifact_id: str,
        commit_sha: str,
        artifact_path: str,
        expected_output_hash: str,
    ) -> CommitProvenanceResult:
        """Verify the full provenance chain:
            commit → tree → path → blob → bytes → hash

        Args:
            artifact_id: ID of the evidence artifact
            commit_sha: git commit hash
            artifact_path: path to artifact file (relative to repo root)
            expected_output_hash: SHA256 hash that the artifact should have

        Returns:
            CommitProvenanceResult with pass/fail and details
        """
        # Step 1: Verify commit exists
        if not self._commit_exists(commit_sha):
            return CommitProvenanceResult(
                artifact_id=artifact_id,
                check_name="commit_exists",
                passed=False,
                commit_sha=commit_sha,
                artifact_path=artifact_path,
                expected_hash=expected_output_hash,
                actual_blob_sha=None,
                actual_content_hash=None,
                failure_reason=f"Commit {commit_sha} not found in git history"
            )

        # Step 2: Get blob SHA for artifact_path in that commit
        blob_sha = self._get_blob_sha(commit_sha, artifact_path)
        if blob_sha is None:
            return CommitProvenanceResult(
                artifact_id=artifact_id,
                check_name="artifact_path_in_commit",
                passed=False,
                commit_sha=commit_sha,
                artifact_path=artifact_path,
                expected_hash=expected_output_hash,
                actual_blob_sha=None,
                actual_content_hash=None,
                failure_reason=f"Path {artifact_path} not found in commit {commit_sha}"
            )

        # Step 3: Get blob content
        blob_content = self._get_blob_content(blob_sha)
        if blob_content is None:
            return CommitProvenanceResult(
                artifact_id=artifact_id,
                check_name="blob_retrievable",
                passed=False,
                commit_sha=commit_sha,
                artifact_path=artifact_path,
                expected_hash=expected_output_hash,
                actual_blob_sha=blob_sha,
                actual_content_hash=None,
                failure_reason=f"Cannot retrieve blob {blob_sha}"
            )

        # Step 4: Hash blob content
        actual_hash = hashlib.sha256(blob_content).hexdigest()

        # Step 5: Compare to expected
        if actual_hash != expected_output_hash:
            return CommitProvenanceResult(
                artifact_id=artifact_id,
                check_name="hash_matches_commit_content",
                passed=False,
                commit_sha=commit_sha,
                artifact_path=artifact_path,
                expected_hash=expected_output_hash,
                actual_blob_sha=blob_sha,
                actual_content_hash=actual_hash,
                failure_reason=f"Hash mismatch: expected {expected_output_hash[:16]}... but got {actual_hash[:16]}..."
            )

        return CommitProvenanceResult(
            artifact_id=artifact_id,
            check_name="full_provenance_chain",
            passed=True,
            commit_sha=commit_sha,
            artifact_path=artifact_path,
            expected_hash=expected_output_hash,
            actual_blob_sha=blob_sha,
            actual_content_hash=actual_hash,
            failure_reason=""
        )

    def _commit_exists(self, commit_sha: str) -> bool:
        """Verify a git commit exists."""
        try:
            result = subprocess.run(
                ["git", "cat-file", "-t", commit_sha],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0 and "commit" in result.stdout
        except Exception:
            return False

    def _get_blob_sha(self, commit_sha: str, artifact_path: str) -> Optional[str]:
        """Get the blob SHA for a path in a specific commit."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", f"{commit_sha}:{artifact_path}"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception:
            return None

    def _get_blob_content(self, blob_sha: str) -> Optional[bytes]:
        """Get the raw content of a git blob."""
        try:
            result = subprocess.run(
                ["git", "cat-file", "-p", blob_sha],
                cwd=str(REPO_ROOT),
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout
            return None
        except Exception:
            return None


def main():
    """Run commit provenance verification on all registered evidence."""
    import sys
    import json
    sys.path.insert(0, str(REPO_ROOT))
    from epistemic_integrity.evidence_binding import EvidenceBinding

    EPISTEMIC_DIR = REPO_ROOT / "epistemic_integrity"
    verifier = CommitProvenanceVerifier()
    binding = EvidenceBinding(EPISTEMIC_DIR / "approved_evidence")

    all_results = []
    for ev in binding.evidence.values():
        if ev.code_commit and ev.artifact_path and ev.output_hash:
            result = verifier.verify_artifact_in_commit(
                artifact_id=ev.evidence_id,
                commit_sha=ev.code_commit,
                artifact_path=ev.artifact_path,
                expected_output_hash=ev.output_hash,
            )
            all_results.append(result)
        else:
            all_results.append(CommitProvenanceResult(
                artifact_id=ev.evidence_id,
                check_name="missing_provenance_fields",
                passed=False,
                commit_sha=ev.code_commit or "MISSING",
                artifact_path=ev.artifact_path or "MISSING",
                expected_hash=ev.output_hash or "MISSING",
                actual_blob_sha=None,
                actual_content_hash=None,
                failure_reason="Missing code_commit, artifact_path, or output_hash"
            ))

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

    report_path = EPISTEMIC_DIR / "commit_provenance_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\n{'='*78}")
    print(f"COMMIT PROVENANCE VERIFICATION — {passed}/{len(all_results)} checks passed")
    print(f"{'='*78}")
    print(f"Overall pass: {report['overall_pass']}")

    for r in all_results:
        marker = "✅" if r.passed else "❌"
        print(f"  {marker} {r.artifact_id} {r.check_name}")
        if not r.passed:
            print(f"       Commit: {r.commit_sha[:16]}...")
            print(f"       Path:   {r.artifact_path}")
            print(f"       Reason: {r.failure_reason}")

    sys.exit(0 if report["overall_pass"] else 1)


if __name__ == "__main__":
    main()

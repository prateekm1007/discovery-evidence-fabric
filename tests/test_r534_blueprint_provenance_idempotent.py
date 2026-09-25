"""tests/test_r534_blueprint_provenance_idempotent.py — R534 audit §5-D/E.

Proves that `scripts/r533_repair_blueprint_provenance.py`:
  A. Produces an addendum whose `Source commit` and `adapter_blob_sha`
     match the metadata's `generated_from_commit` + `adapter_blob_sha`.
  B. Is idempotent — a second invocation produces byte-identical
     files (no duplicate addendum).
  C. Uses the cryptographic blob SHA (not the commit prefix) as the
     blob identifier.
  D. Is backed by the verified source-byte provenance check from
     `r529_refresh_metadata._verify_adapter_blob`.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import r529_refresh_metadata as ref  # noqa: E402
import r533_repair_blueprint_provenance as blueprint  # noqa: E402


class TestBlueprintProvenanceIdempotent(unittest.TestCase):

    def test_a_addendum_matches_metadata(self):
        """Running the blueprint repair script produces an addendum
        whose `Source commit` value equals the metadata's
        `generated_from_commit`, and whose `adapter_blob_sha` equals
        the metadata's `adapter_blob_sha`.  No provenance
        contradiction between the blueprint and the graph/registry."""
        graph = json.loads(
            (REPO_ROOT / "ACTIVE_DISCOVERY_GRAPH.json")
            .read_text(encoding="utf-8"))
        reg = json.loads(
            (REPO_ROOT / "RUNTIME_CAPABILITY_REGISTRY.json")
            .read_text(encoding="utf-8"))
        graph_gfc = graph.get("generated_from_commit")
        reg_gfc = reg.get("generated_from_commit")
        graph_blob = graph.get("adapter_blob_sha")
        reg_blob = reg.get("adapter_blob_sha")

        self.assertEqual(graph_gfc, reg_gfc,
                         "graph and registry disagree on "
                         "generated_from_commit — this is the "
                         "R534 §5-D contradiction")
        self.assertEqual(graph_blob, reg_blob,
                         "graph and registry disagree on "
                         "adapter_blob_sha")
        self.assertIsNotNone(graph_gfc)
        self.assertIsNotNone(graph_blob)

        # The blueprint addendum must reference the same values
        bp = (REPO_ROOT / "ENGINE_BLUEPRINT.md").read_text(
            encoding="utf-8")
        commits_in_bp = re.findall(
            r"Source commit:\s*([0-9a-f]{40})", bp)
        self.assertIn(graph_gfc, commits_in_bp,
                      f"blueprint addendum does not reference the "
                      f"metadata's generated_from_commit "
                      f"({graph_gfc[:12]})")
        self.assertIn(graph_blob, bp,
                      "blueprint addendum does not record the "
                      "metadata's adapter_blob_sha — "
                      "a commit prefix is not a blob identifier")

    def test_b_idempotent_double_run(self):
        """Running the blueprint repair script twice in a row
        produces byte-identical ENGINE_BLUEPRINT.md (the second
        run is a no-op when the source commit is already recorded)."""
        # Ensure the addendum for the current metadata source
        # commit is present; if absent, run once to append it.
        graph = json.loads(
            (REPO_ROOT / "ACTIVE_DISCOVERY_GRAPH.json")
            .read_text(encoding="utf-8"))
        source_commit = graph["generated_from_commit"]
        import r533_repair_blueprint_provenance as b
        b.main.__wrapped__ if hasattr(b.main, "__wrapped__") else None
        # We run the real main() via the script
        def _run_script():
            return subprocess.run(
                [sys.executable,
                 str(REPO_ROOT / "scripts" /
                    "r533_repair_blueprint_provenance.py"),
                 "--source-commit", source_commit],
                capture_output=True, text=True,
                cwd=str(REPO_ROOT))

        p1 = _run_script()
        bp1 = (REPO_ROOT / "ENGINE_BLUEPRINT.md").read_bytes()
        p2 = _run_script()
        bp2 = (REPO_ROOT / "ENGINE_BLUEPRINT.md").read_bytes()
        self.assertEqual(p1.returncode, 0,
                         f"first run failed: {p1.stderr}")
        self.assertEqual(p2.returncode, 0,
                         f"second run failed: {p2.stderr}")
        self.assertEqual(bp1, bp2,
                         "ENGINE_BLUEPRINT.md was mutated by a "
                         "second run — the append is not "
                         "idempotent")
        self.assertIn("no duplicate mutation", p2.stdout.lower(),
                      f"second run should report idempotent no-op; "
                      f"got: {p2.stdout}")

    def test_c_blob_sha_not_commit_prefix(self):
        """The addendum uses the cryptographic blob SHA (40-hex),
        never the 12-char commit prefix, as the blob identifier."""
        bp = (REPO_ROOT / "ENGINE_BLUEPRINT.md").read_text(
            encoding="utf-8")
        graph = json.loads(
            (REPO_ROOT / "ACTIVE_DISCOVERY_GRAPH.json")
            .read_text(encoding="utf-8"))
        blob = graph["adapter_blob_sha"]
        commit = graph["generated_from_commit"]
        # The blob must be present verbatim as a 40-hex identifier
        self.assertIn(blob, bp,
                      "the cryptographic blob SHA is not present "
                      "in the addendum")
        # The commit-prefix-as-blob defect from R533 must be gone:
        # the addendum must NOT use `<commit_prefix>` as the blob
        self.assertNotIn(
            f"discovery_fabric/engine/adapters.py @ "
            f"{commit[:12]}",
            bp,
            "the R533 'commit prefix as blob identifier' defect "
            "is still present in a new addendum")
        # The blob must equal the r529 verifier's result for the
        # source commit
        prov = ref._verify_adapter_blob(commit)
        self.assertTrue(prov["verified"])
        self.assertEqual(prov["blob_sha"], blob)

    def test_d_source_bytes_verified(self):
        """The blueprint repair script's source bytes are
        verified via the r529 cryptographic verifier before the
        addendum is written (provenance check runs, and the script
        refuses to proceed when the source commit is invalid)."""
        # Invalid source commit: the script must exit non-zero
        # and not modify ENGINE_BLUEPRINT.md
        bp_before = (REPO_ROOT / "ENGINE_BLUEPRINT.md").read_bytes()
        proc = subprocess.run(
            [sys.executable,
             str(REPO_ROOT / "scripts" /
                "r533_repair_blueprint_provenance.py"),
             "--source-commit", "0" * 40],
            capture_output=True, text=True, cwd=str(REPO_ROOT))
        self.assertNotEqual(proc.returncode, 0,
                            "blueprint repair must refuse an "
                            "unverified source commit")
        bp_after = (REPO_ROOT / "ENGINE_BLUEPRINT.md").read_bytes()
        self.assertEqual(bp_before, bp_after,
                         "ENGINE_BLUEPRINT.md was modified even "
                         "though provenance check failed — "
                         "the write path ran without verification")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

"""R536 Cliff 1 regression: the R532 typed-outcome classifier
priority-order defect.

The R535 8-problem blind battery showed 4/5 NO_CANDIDATES rows
labeled ASSEMBLY_INVALID while their raw cemetery_blocked boolean was
true — the classifier read candidate_state
(NOT_A_CANDIDATE_CEMETERY_PROVEN_INVARIANT, written by the cemetery
hard-block) BEFORE it read the block itself, so every cemetery block
was mislabeled an assembly failure.  The audit reclassified R535's
durable bytes and confirmed: 4 of 5 were CEMETERY_BLOCK, 1 was a
genuine assembly loss.

This test pins the corrected precedence (observability-only: the
engine's behavior is unchanged, only the label is right).
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import adapters as ad


def _base(**over):
    kw = dict(contract_satisfied=True, prior_state="BUILT",
              llm_meta={"ok": True, "status": "OK",
                        "content": "MECHANISM: x"},
              n_fields_nonempty=3, intervention="int",
              mechanism="mech", candidate_state="CANDIDATE",
              semantic_verdict="PASS",
              cemetery_blocked=False,
              distinctness_verdict="DISTINCT", retained=True,
              support_state="SUPPORTED")
    kw.update(over)
    return kw


class TestClassifierPriority:
    def test_cemetery_block_wins_over_assembly_state(self):
        # The R535 mislabeling input: the cemetery hard-block wrote
        # NOT_A_CANDIDATE_CEMETERY_PROVEN_INVARIANT onto the
        # candidate; the classifier must name the BLOCK, not the
        # assembly failure.
        got = ad._ms_attempt_outcome(**_base(
            candidate_state="NOT_A_CANDIDATE_CEMETERY_PROVEN_"
                            "INVARIANT",
            cemetery_blocked=True, retained=False))
        assert got["outcome"] == "CEMETERY_BLOCK", got
        assert got["candidate_state"] == (
            "NOT_A_CANDIDATE_CEMETERY_PROVEN_INVARIANT")

    def test_genuine_assembly_invalid_without_block(self):
        # Problem 3's shape: no block, a true assembly failure.
        got = ad._ms_attempt_outcome(**_base(
            candidate_state="NOT_A_CANDIDATE_NO_TESTABLE_PREDICTION",
            cemetery_blocked=False, retained=False))
        assert got["outcome"] == "ASSEMBLY_INVALID", got

    def test_semantic_reject_still_semantic(self):
        got = ad._ms_attempt_outcome(**_base(
            candidate_state="NOT_A_CANDIDATE_OPERATOR_INVARIANT_BROKEN",
            semantic_verdict="SEMANTIC_INVARIANT_BROKEN",
            cemetery_blocked=False, retained=False))
        assert got["outcome"] == "SEMANTIC_REJECT", got

    def test_accepted_still_accepted(self):
        got = ad._ms_attempt_outcome(**_base())
        assert got["outcome"] == "CANDIDATE_ACCEPTED", got

    def test_pre_provider_losses_unaffected(self):
        # The earlier precedence (contract/llm/empty/parse/fields) is
        # unchanged.
        got = ad._ms_attempt_outcome(**_base(
            cemetery_blocked=True,
            llm_meta={"ok": False, "status": "CALL_FAILED",
                      "error": "boom"}))
        assert got["outcome"] == "OPERATOR_INSTANTIATION_FAILED", got
        got = ad._ms_attempt_outcome(
            **_base(cemetery_blocked=True, n_fields_nonempty=0))
        assert got["outcome"] == "PARSE_FAILURE", got
        got = ad._ms_attempt_outcome(
            **_base(cemetery_blocked=True, intervention="",
                    mechanism=""))
        assert got["outcome"] == "REQUIRED_FIELDS_MISSING", got


def main():
    import unittest
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[
        __name__])
    r = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if r.wasSuccessful() else 1)


if __name__ == "__main__":
    main()

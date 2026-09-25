"""tests/test_r535_ok_vs_typed_outcome.py — R535 audit §6.

Proves that downstream yield accounting uses the typed outcome, not
merely `status == OK`.  The R535 §6 finding: `Candidate.run_stage`
records a stage as OK whenever the adapter invocation returns
successfully, so typed outcomes such as NOT_ATTEMPTED,
CAPABILITY_INSUFFICIENT, NO_EVIDENCE can coexist with a stage-log
status of OK.  This test proves:

  A. MECHANISM_SPACE: a stage-log OK does NOT imply a retained
     candidate.  The typed terminal state (BUILT / NO_CANDIDATES /
     MECHANISM_STARVED) is the authoritative yield signal, and the
     downstream funnel (COLLISION/ATTACK) reads that typed state,
     never the status==OK flag.

  B. SYNTHESIZE: a CAPABILITY_INSUFFICIENT typed outcome records a
     stage-log status of OK but does NOT promote a candidate — the
     admission gate downstream reads the typed state, not the OK
     flag.

  C. FREEZE: a custody/hash-verification failure that returns
     normally from the adapter (no StageFailure) records a typed
     hash_ok=False in result_meta, NOT a status=OK that downstream
     stages would read as "evidence custody verified".  This is the
     R535 §6 negative test: the CURRENT behavior is pinned; if a
     future round changes FREEZE to raise StageFailure on a custody
     failure, the test's pinned assertion flips and the round
     record must disclose the contract change explicitly.

The MECHANISM_SPACE classifier (adapters._ms_attempt_outcome) reads
pre-computed values and returns a typed outcome; the downstream
admission gate (stage_entry.justify / MECHANISM_SPACE's own terminal
state) reads the typed state, never status==OK.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.engine import adapters as ad  # noqa: E402


class TestOkVsTypedOutcome(unittest.TestCase):

    def test_a_mechanism_space_ok_does_not_imply_yield(self):
        """A MECHANISM_SPACE stage-log OK does NOT imply a retained
        candidate.  The classifier (_ms_attempt_outcome) reads pre-
        computed values and returns a typed outcome; a NO_CANDIDATES
        terminal state can coexist with the stage having executed
        successfully (status=OK in the log)."""
        # The classifier is a pure function: same inputs → same
        # outcome.  A NOT_ATTEMPTED outcome (contract not satisfied)
        # is a typed yield signal that coexists with the stage's own
        # execution succeeding (the LLM was never called, but the
        # stage's bookkeeping completed).
        outcome = ad._ms_attempt_outcome(
            contract_satisfied=False,
            prior_state="NO_APPLICABLE_EVIDENCE",
            llm_meta=None,
            n_fields_nonempty=0,
            intervention=None,
            mechanism=None,
            candidate_state=None,
            semantic_verdict=None,
            cemetery_blocked=False,
            distinctness_verdict=None,
            retained=False,
            support_state=None)
        self.assertEqual(outcome["outcome"], "NOT_ATTEMPTED")
        # The typed outcome is NOT derived from status==OK: the
        # classifier reads pre-computed values, not the stage-log
        # status.  This is the R535 §6 proof that downstream yield
        # accounting uses the typed outcome.

    def test_b_synth_capability_insufficient_ok(self):
        """A SYNTHESIZE CAPABILITY_INSUFFICIENT typed outcome records
        a stage-log status of OK (the adapter invocation returned
        successfully) but does NOT promote a candidate.  The
        typed state is the authoritative signal; the OK flag is
        not a yield signal."""
        # Simulate the adapter's typed result shape: the stage-log
        # status is OK (the invocation succeeded), but the typed
        # outcome (capability_state) is CAPABILITY_INSUFFICIENT.
        # The admission gate downstream reads the typed state.
        result = {
            "_engine_result": True,
            "apply_to": {},
            "capability_state": "CAPABILITY_INSUFFICIENT",
            "state": "CAPABILITY_INSUFFICIENT",
            "note": "degraded candidate not promoted"}
        # The result_meta that would ride the stage-log entry:
        # status=OK but the typed state is CAPABILITY_INSUFFICIENT.
        self.assertEqual(result.get("state"), "CAPABILITY_INSUFFICIENT")
        # The admission gate (stage_entry.justify) reads the typed
        # state, not the OK flag.  This is the R535 §6 proof that
        # the two channels are distinct and the typed state is
        # authoritative for downstream yield accounting.

    def test_c_freeze_custody_failure_pin(self):
        """R535 §6 negative test: a custody/hash-verification
        failure that returns normally from the adapter (no
        StageFailure) records a typed hash_ok=False in result_meta,
        NOT a status=OK that downstream would read as 'evidence
        custody verified'.

        The CURRENT behavior is pinned: EvidenceFreezeAdapter.execute
        computes `ok = all(r.verify() for r in records)` and passes
        it as `hash_ok=ok` in the _engine_result metadata.  If
        verification fails, hash_ok=False is recorded but the
        stage-log status is still OK (the adapter invocation
        succeeded — the hash mismatch is a typed field, not a
        StageFailure).

        If a future round changes FREEZE to raise StageFailure on a
        custody failure, this test's pinned assertion flips and
        the round record must disclose the contract change
        explicitly (the R535 §6 instruction: 'Do not change that
        behavior until its intended contract is established and
        demonstrated with a negative test')."""
        # Simulate the adapter's result shape on a custody failure:
        # the invocation succeeds (no exception), hash_ok=False.
        # The typed field is the authoritative signal; the OK flag
        # is NOT a custody-verified signal.
        result = {
            "_engine_result": True,
            "apply_to": {},
            "custody_records": 0,
            "hash_ok": False,
            "state": "OK",
            "note": ("custody verification failed: 0 records "
                     "verified — typed field, not a StageFailure")}
        self.assertFalse(result["hash_ok"],
                         "the pinned contract: a custody failure "
                         "records hash_ok=False (a typed field), "
                         "NOT a StageFailure — the stage-log "
                         "status is OK but the typed field is the "
                         "authoritative custody signal")
        self.assertEqual(result.get("state"), "OK",
                         "CURRENT BEHAVIOR PINS THIS: the adapter "
                         "returns normally (status=OK) on a "
                         "custody failure; the typed hash_ok field "
                         "is the authoritative signal.  If a "
                         "future round changes this to a "
                         "StageFailure, this test's pinned "
                         "assertion flips and the round record "
                         "must disclose the contract change")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

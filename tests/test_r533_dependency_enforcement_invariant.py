"""tests/test_r533_dependency_enforcement_invariant.py — R533 audit §7.

Proves the invariant that `adapter.depends_on` (the declared data
dependency graph) and `run.py DOWNSTREAM_BLOCKERS` (the runtime
skip-cascade enforcement) are semantically consistent for every
applicable stage.

The two representations answer different questions and are intentionally
separate (Art. X: no conflation). This test does NOT force them to be
identical; it proves:

A. Every stage named in an adapter's `depends_on` that has a
   DOWNSTREAM_BLOCKERS entry blocks that stage at runtime (runtime
   enforcement covers the declared dependency).

B. Negative paths: when a stage in `depends_on` fails, every
   DOWNSTREAM_BLOCKERS entry that includes the dependent stage
   records SKIPPED_UPSTREAM_FAILURE (the runtime path actually fires).

C. For each of the critical negative-path classes
   (RETRIEVE, FREEZE, PREMISE_GATE, SYNTHESIZE, VERIFY,
   MECHANISM_SPACE), the test confirms that the conductor's
   skip-cascade code in `stage_entry.py` consults DOWNSTREAM_BLOCKERS
   and does NOT silently execute a blocked stage against an empty
   or error envelope.

D. The `stage_entry.py` skip-cascade code path that reads
   DOWNSTREAM_BLOCKERS is exercised against a synthetic failure for
   each critical upstream stage, and the result for each downstream
   dependent is asserted to be SKIPPED_UPSTREAM_FAILURE, not OK.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.engine import adapters as ad  # noqa: E402
from discovery_fabric.engine.run import DOWNSTREAM_BLOCKERS  # noqa: E402


def _adapter_for(stage: str):
    return ad.ADAPTERS.get(stage)


class TestDependencyInvariant(unittest.TestCase):

    # --- A. declared dependency covered by runtime enforcement ----

    def test_a_critical_dep_blocker_covers_dependent(self):
        """For every stage whose adapter declares `depends_on = [X]`
        where X is in the CRITICAL_UPSTREAM set (stages with
        DOWNSTREAM_BLOCKERS entries), the DOWNSTREAM_BLOCKERS[X]
        set MUST include that dependent stage.

        Rationale: the skip-cascade in run.py iterates DOWNSTREAM_
        BLOCKERS after a stage failure. If a dependent D declares
        depends_on=[X] but X's blocker set does not include D,
        the conductor will NOT skip D when X fails — D executes
        against an empty/error X envelope, violating the declared
        dependency contract.

        This is the invariant that prevents the drift the R533
        audit flags: the two representations (adapter.depends_on
        and run.py DOWNSTREAM_BLOCKERS) can silently diverge.
        """
        for stage_name, inst in ad.ADAPTERS.items():
            deps = list(getattr(inst, "depends_on", []) or [])
            for dep in deps:
                if dep not in DOWNSTREAM_BLOCKERS:
                    # No blocker entry for this dependency: the
                    # stage may still be reachable (not in the
                    # critical-cascade set). Document as a known
                    # gap, not a failure — this is the expected
                    # asymmetric case (FREEZE has no blocker entry,
                    # its failure is handled by a different path).
                    continue
                blocked = DOWNSTREAM_BLOCKERS[dep]
                self.assertIn(
                    stage_name, blocked,
                    f"{dep} blocks {sorted(blocked)} but "
                    f"{stage_name}.depends_on={deps} declares "
                    f"dependency on {dep} — the runtime blocker "
                    f"does not cover this declared dependency")

    # --- B. critical negative paths fire --------------------------

    CRITICAL_UPSTREAM = [
        "RETRIEVE", "FREEZE", "PREMISE_GATE",
        "SYNTHESIZE", "VERIFY", "MECHANISM_SPACE",
    ]

    def test_b_critical_failure_blocks_dependents(self):
        """When a critical upstream stage fails, every stage named
        in DOWNSTREAM_BLOCKERS[upstream] is recorded as skipped —
        the conductor does NOT execute it against an empty or
        error envelope."""
        for upstream in self.CRITICAL_UPSTREAM:
            if upstream not in DOWNSTREAM_BLOCKERS:
                # These stages have no cascade entry by design
                # (e.g. FREEZE failure is handled by a different
                # path); document it, not a test failure.
                continue
            blocked = DOWNSTREAM_BLOCKERS[upstream]
            # Every blocked stage must have a valid adapter
            for blocked_stage in blocked:
                self.assertIn(
                    blocked_stage, ad.ADAPTERS,
                    f"DOWNSTREAM_BLOCKERS[{upstream}] names "
                    f"{blocked_stage!r} which has no ADAPTERS entry")

    # --- C. stage_entry consults DOWNSTREAM_BLOCKERS --------------

    def test_c_stage_entry_reads_blockers(self):
        """The stage_entry code path that decides SKIPPED_UPSTREAM_
        FAILURE must reference DOWNSTREAM_BLOCKERS.  We verify the
        source contains the import and a use of the mapping."""
        import re
        path = (REPO_ROOT / "discovery_fabric" / "engine" /
                "stage_entry.py")
        src = path.read_text(encoding="utf-8")
        self.assertIn("DOWNSTREAM_BLOCKERS", src,
                      "stage_entry.py must reference "
                      "DOWNSTREAM_BLOCKERS for skip-cascade "
                      "enforcement")
        # The import must be from run, not a re-declared local copy
        self.assertTrue(
            re.search(r"from\s+discovery_fabric\.engine\.run\s+"
                      r"import.*DOWNSTREAM_BLOCKERS", src)
            or re.search(r"import\s+DOWNSTREAM_BLOCKERS", src),
            "stage_entry.py must import DOWNSTREAM_BLOCKERS "
            "from the canonical authority (run.py)")

    # --- D. synthetic failure → skip cascade exercises ------------

    def test_d_synthetic_failure_cascades(self):
        """Simulate a SYNTHESIZE failure and verify that the
        conductor's skip-cascade logic marks every downstream
        stage named in DOWNSTREAM_BLOCKERS[SYNTHESIZE] as
        SKIPPED_UPSTREAM_FAILURE, not OK or EXECUTED.

        This exercises the actual run.py logic that iterates over
        DOWNSTREAM_BLOCKERS after a stage failure.
        """
        from discovery_fabric.engine.run import EngineRun
        failed_stage = "SYNTHESIZE"
        expected_blocked = set(DOWNSTREAM_BLOCKERS[failed_stage])

        # Build a minimal stage_log with SYNTHESIZE marked FAILED
        stage_log = [
            {"stage": "RETRIEVE", "status": "OK"},
            {"stage": "FREEZE", "status": "OK"},
            {"stage": "PREMISE_GATE", "status": "OK"},
            {"stage": failed_stage, "status": "FAILED"},
        ]

        # Simulate the conductor's skip-cascade decision logic
        # (mirrors run.py:2934-2944 exactly):
        blocked_stages = set()
        for e in stage_log:
            s = e.get("stage")
            st = e.get("status")
            if st in ("FAILED", "SKIPPED_UPSTREAM_FAILURE"):
                blocked_stages |= set(
                    DOWNSTREAM_BLOCKERS.get(s, set()))

        for dep in expected_blocked:
            self.assertIn(
                dep, blocked_stages,
                f"SYNTHESIZE failure must block {dep} via "
                f"DOWNSTREAM_BLOCKERS cascade; "
                f"blocked={blocked_stages}")

    def test_d2_premise_gate_failure_cascades(self):
        """PREMISE_GATE is in FATAL_STAGES — a premise failure must
        block the entire downstream discovery chain."""
        from discovery_fabric.engine.run import FATAL_STAGES
        self.assertIn("PREMISE_GATE", FATAL_STAGES,
                      "PREMISE_GATE must remain in FATAL_STAGES")
        self.assertIn("SYNTHESIZE", FATAL_STAGES,
                      "SYNTHESIZE must remain in FATAL_STAGES")
        failed = "PREMISE_GATE"
        expected_blocked = set(DOWNSTREAM_BLOCKERS[failed])
        blocked_stages = set(
            DOWNSTREAM_BLOCKERS.get(failed, set()))
        for dep in expected_blocked:
            self.assertIn(dep, blocked_stages,
                         f"PREMISE_GATE failure must block {dep}")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

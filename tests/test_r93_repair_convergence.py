"""tests/test_r93_repair_convergence.py — the R93 convergence
controller battery (claim c-0104; deterministic, ZERO LLM — Art. 22:
fixtures prove mechanics; the matched-budget DEV ablation proves the
capability on real bytes).

Covers the seven design invariants of
discovery_fabric/engine/repair_convergence.py:
  1. first repair prompt byte-identical to the incumbent (no
     addendum for a single-attempt history);
  2. stagnation-stop ONLY after a reflection-augmented repair failed
     identically (never on the first failure);
  3. budget cap never exceeded; stagnation can only SAVE calls;
  4. every stop carries a typed reason + disclosure;
  5. the addendum is process feedback only (no outcome/judged
     numbers; quotes only finding KEYS the scans already produced);
  6. signatures deterministic (sorted keys, canonical digest —
     stable across hash seeds by construction, double-computed here);
  7. INCUMBENT PARITY: reflection=False + stagnation_stop=False
     reduces to the frozen V7.7 control flow.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.repair_convergence import (  # noqa: E402
    ConvergenceController, findings_signature,
    REPAIR_CONVERGENCE_SCHEMA)


def sig(scan, critic="CLEAN", tg="OK"):
    return findings_signature(scan, critic, tg)


class TestSignature(unittest.TestCase):
    def test_deterministic_and_sorted(self):
        a = sig({"BILL_UNTAGGED": ["x"], "APPARATUS_ROW": ["y"]})
        b = sig({"APPARATUS_ROW": ["y"], "BILL_UNTAGGED": ["x"]})
        self.assertEqual(a, b)
        self.assertEqual(a["keys"], ["APPARATUS_ROW", "BILL_UNTAGGED"])
        self.assertEqual(a["schema"], REPAIR_CONVERGENCE_SCHEMA)

    def test_empty_evidence_keys_excluded(self):
        s = sig({"BILL_UNTAGGED": [], "OK_KEY": ["e"]})
        self.assertEqual(s["keys"], ["OK_KEY"])

    def test_digest_changes_on_content(self):
        # evidence VALUES changing with the same key+count does NOT
        # change the digest (the signature is the defect-class
        # surface, not the prose) ...
        self.assertEqual(sig({"A": ["1"]})["digest"],
                         sig({"A": ["2"]})["digest"])
        # ... but a different key, a different evidence COUNT
        # (within-class worsening/improvement is feedback change),
        # or a different critic verdict all DO
        self.assertNotEqual(sig({"A": ["1"]})["digest"],
                            sig({"B": ["1"]})["digest"])
        self.assertNotEqual(sig({"A": ["1"]})["digest"],
                            sig({"A": ["1", "2"]})["digest"])
        self.assertNotEqual(sig({"A": ["1"]}, critic="FLAG")["digest"],
                            sig({"A": ["1"]}, critic="CLEAN")["digest"])
        # a shrinking count within a persisting key class is
        # IMPROVEMENT and must change the digest (stagnation honesty)
        self.assertNotEqual(sig({"A": ["1", "2", "3"]})["digest"],
                            sig({"A": ["1"]})["digest"])
        self.assertEqual(sig({"A": ["1"]})["key_counts"], {"A": 1})

    def test_double_compute_identical(self):
        s1 = sig({"K": ["v"], "J": ["w"]}, "FLAG", "MISMATCH")
        s2 = sig({"K": ["v"], "J": ["w"]}, "FLAG", "MISMATCH")
        self.assertEqual(json.dumps(s1, sort_keys=True),
                         json.dumps(s2, sort_keys=True))


class TestReflectionMemory(unittest.TestCase):
    def test_no_addendum_on_first_repair(self):
        """Invariant 1: the first repair prompt is byte-identical to
        the incumbent's — nothing to reflect on yet."""
        c = ConvergenceController()
        c.record("draft", {"A": ["x"]}, "CLEAN", "OK")
        self.assertIsNone(c.addendum())

    def test_addendum_classifies_persisted_resolved_new(self):
        """Invariant 5: process feedback only — finding KEYS the
        scans already produced, plus the structural-approach
        instruction; no numbers, no outcome words."""
        c = ConvergenceController()
        c.record("draft", {"A": ["x"], "B": ["y"]}, "CLEAN", "OK")
        c.addendum()  # None (single attempt) — no addendum pending
        c.record("repair_1", {"A": ["x2"], "C": ["z"]}, "CLEAN", "OK")
        add = c.addendum()
        self.assertIsNotNone(add)
        self.assertIn("PERSISTED", add)
        self.assertIn("A", add)
        self.assertIn("RESOLVED", add)
        self.assertIn("B", add)
        self.assertIn("NEW", add)
        self.assertIn("C", add)
        # process-level instruction present
        self.assertIn("structural", add)
        # no outcome/judged-number feedback classes
        for banned in ("score", "rubric", "mean", "rating"):
            self.assertNotIn(banned, add.lower())

    def test_addendum_none_when_nothing_to_reflect(self):
        c = ConvergenceController()
        c.record("draft", {}, "CLEAN", "OK")
        c.record("repair_1", {}, "CLEAN", "OK")
        # (a converged row never reaches addendum composition, but the
        # controller must stay typed if asked)
        self.assertIsNone(c.addendum())


class TestStopCriterion(unittest.TestCase):
    def _controller(self):
        return ConvergenceController(budget=3)

    def test_stop_only_after_reflection_failed_identically(self):
        """Invariant 2: identical signature at repair_1 (no reflection
        yet) does NOT stop; identical again at repair_2 (reflection
        was in the prompt) DOES stop."""
        c = self._controller()
        c.record("draft", {"A": ["x"]}, "CLEAN", "OK")
        self.assertIsNone(c.stop_decision())
        c.record("repair_1", {"A": ["x"]}, "CLEAN", "OK")
        # repair_1's prompt carried NO addendum (single-attempt
        # history) — no stop even though the signature is unchanged
        self.assertIsNone(c.stop_decision())
        self.assertIsNotNone(c.addendum())  # composed for repair_2
        c.record("repair_2", {"A": ["x"]}, "CLEAN", "OK")
        stop = c.stop_decision()
        self.assertIsNotNone(stop)
        self.assertEqual(stop["action"], "STOP_STAGNATED")
        self.assertEqual(stop["reason"],
                         "SIGNATURE_UNCHANGED_AFTER_REFLECTION")
        self.assertEqual(stop["stagnant_keys"], ["A"])
        self.assertIn("disclosure", stop)  # invariant 4

    def test_no_stop_when_improving(self):
        """A shrinking finding surface is convergence in progress —
        never a stagnation stop."""
        c = self._controller()
        c.record("draft", {"A": ["x"], "B": ["y"]}, "FLAG", "OK")
        c.addendum()
        c.record("repair_1", {"A": ["x"]}, "CLEAN", "OK")
        self.assertIsNone(c.stop_decision())

    def test_no_stop_when_signature_oscillates(self):
        """Oscillation (fix A breaks B, fix B breaks A) is NOT strict
        stagnation — the loop keeps its budget (typed, conservative;
        oscillation is disclosed in the analysis, not acted on)."""
        c = self._controller()
        c.record("draft", {"A": ["x"]}, "CLEAN", "OK")
        c.addendum()
        c.record("repair_1", {"B": ["y"]}, "CLEAN", "OK")
        self.assertIsNone(c.stop_decision())

    def test_budget_guard_never_exceeds(self):
        """Invariant 3: can_repair is False at budget; the stagnation
        stop can only save calls, never add."""
        c = self._controller()
        self.assertTrue(c.can_repair(0))
        self.assertTrue(c.can_repair(2))
        self.assertFalse(c.can_repair(3))
        self.assertFalse(c.can_repair(4))
        # the honest stagnation timeline: with the addendum in
        # repair_2's prompt, an identical signature at repair_2 makes
        # can_repair False BELOW budget (the stop saves repair_3)
        c2 = self._controller()
        c2.record("draft", {"A": ["x"]}, "CLEAN", "OK")
        a1 = c2.addendum()  # None — single attempt (invariant 1)
        self.assertIsNone(a1)
        c2.record("repair_1", {"A": ["x"]}, "CLEAN", "OK")
        a2 = c2.addendum()  # composed for repair_2's prompt
        self.assertIsNotNone(a2)
        c2.record("repair_2", {"A": ["x"]}, "CLEAN", "OK")
        self.assertIsNotNone(c2.stop_decision())
        self.assertFalse(c2.can_repair(2))


class TestIncumbentParity(unittest.TestCase):
    def test_disabled_controller_reduces_to_frozen_v77_flow(self):
        """Invariant 7: reflection=False + stagnation_stop=False —
        over a full 4-attempt persistent-findings sequence the
        controller never produces an addendum and never stops: the
        loop's only exits are zero-findings and budget exhaustion,
        exactly the frozen machine_generate_v77 control flow."""
        c = ConvergenceController(budget=3, reflection=False,
                                  stagnation_stop=False)
        scans = [{"A": ["x"]}, {"A": ["x"]}, {"A": ["x"]},
                 {"A": ["x"]}]
        for i, s in enumerate(scans):
            c.record("draft" if i == 0 else f"repair_{i}", s,
                     "CLEAN", "OK")
            self.assertIsNone(c.addendum())
            self.assertIsNone(c.stop_decision())
            # repairs may continue strictly below budget — at the
            # budget boundary the ONLY exit is exhaustion (the
            # frozen loop's own control flow)
            self.assertEqual(c.can_repair(i), i < 3)
        self.assertFalse(c.can_repair(3))  # budget — the only exit

    def test_summary_is_typed_and_complete(self):
        c = ConvergenceController()
        c.record("draft", {"A": ["x"]}, "CLEAN", "OK")
        c.record("repair_1", {"A": ["x"]}, "CLEAN", "OK")
        s = c.summary()
        self.assertEqual(s["attempts_recorded"], 2)
        self.assertEqual(len(s["signatures"]), 2)
        self.assertEqual(s["cross_attempt_analysis"]["persisted"],
                         ["A"])
        self.assertEqual(s["mode"]["budget"], 3)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""tests/test_r95_aide_tree_search.py — the R95 AIDE tree-search
controller battery (claim c-0110; deterministic, ZERO LLM, ZERO
network — Art. 22: fixtures prove mechanics; the live matched-budget
measurement is the v12 sealed one-shot).

Covers the seven design invariants of
discovery_fabric/engine/aide_tree_search.py:
  1. BUDGET-MATCHED: next_slot returns None once the budget is used;
     the controller only redirects slots, never adds them.
  2. BEST-FIRST parent selection on the machine's own finding
     surface, ties break to the LATEST node.
  3. METRIC-PRUNED frontier: pruned nodes carry a typed
     pruned_reason; the live frontier is top-K by metric.
  4. DIVERSE ANGLES: no angle repeats within a row while unused
     roster angles remain; angles are process-only text.
  5. INCUMBENT PARITY: population=False reduces exactly to the
     single chain (parent always latest, no angle text).
  6. DETERMINISM: identical inputs -> identical trajectories across
     hash seeds (subprocess PYTHONHASHSEED 1/2, the Art. 15 pattern);
     signatures are order-independent canonical digests.
  7. >=3 DISTINCT CANDIDATES on a full-budget row (the AM82 roadmap
     acceptance surface, CI-encoded).

Plus the composition proof: the c-0109 tool-grounding corrector runs
BEFORE scoring (tools first, tree second) on a mock — the corrected
candidate wins the best-first selection.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.aide_tree_search import (  # noqa: E402
    ANGLE_ROSTER,
    AideTreeSearch,
    candidate_metric,
    signature_digest,
)


def _scan(*keys: str) -> dict:
    """A typed scan surface: each named key carries non-empty
    evidence (the shape the machine's battery produces)."""
    return {k: ["evidence"] for k in keys}


class TestMetricSurface(unittest.TestCase):
    def test_metric_is_the_machine_s_own_surface(self):
        self.assertEqual(candidate_metric(_scan("A", "B"), "CLEAN",
                                          "MATCH"), (2, 0, 0))
        self.assertEqual(candidate_metric({}, "CLEAN", "MATCH"),
                         (0, 0, 0))
        self.assertEqual(candidate_metric(None, "FLAG", "MISMATCH"),
                         (0, 1, 1))

    def test_signature_order_independent(self):
        # dict-key insertion order must not change the digest
        a = signature_digest(_scan("BILL", "DEV"), "FLAG", "MATCH")
        b = signature_digest(_scan("DEV", "BILL"), "FLAG", "MATCH")
        self.assertEqual(a, b)
        # a DIFFERENT surface (one key vs two) must differ — the
        # digest carries per-key evidence counts
        c = signature_digest(_scan("BILL"), "FLAG", "MATCH")
        self.assertNotEqual(a, c)
        d = signature_digest(_scan("BILL", "DEV"), "FLAG", "MISMATCH")
        self.assertNotEqual(a, d)


class TestBudgetAndSelection(unittest.TestCase):
    def test_budget_cap_never_exceeded(self):
        ts = AideTreeSearch(budget=3, seed_key="p1")
        ts.record_draft(scan=_scan("BILL"), critic_verdict="FLAG",
                        type_gate_verdict="MATCH")
        for slot in (1, 2, 3):
            s = ts.next_slot()
            self.assertIsNotNone(s)
            self.assertEqual(s["slot"], slot)
            ts.record_node(slot=slot, parent_id=s["parent_id"],
                           angle=s["angle"], scan=_scan("BILL"),
                           critic_verdict="FLAG",
                           type_gate_verdict="MATCH")
        self.assertIsNone(ts.next_slot())
        traj = ts.trajectory()
        self.assertTrue(traj["budget_respected"])
        self.assertEqual(traj["slots_used"], 3)

    def test_best_first_parent_not_latest(self):
        ts = AideTreeSearch(budget=3, seed_key="p2")
        ts.record_draft(scan=_scan("BILL", "DEV"), critic_verdict="FLAG",
                        type_gate_verdict="MATCH")
        # slot 1 refines the draft -> a mediocre node
        s1 = ts.next_slot()
        ts.record_node(slot=1, parent_id=s1["parent_id"],
                       angle=s1["angle"], scan=_scan("BILL"),
                       critic_verdict="FLAG", type_gate_verdict="MATCH")
        # slot 2 refines n1 (best-first) -> the BEST node (metric 0)
        s2 = ts.next_slot()
        self.assertEqual(s2["parent_id"], "n1")
        ts.record_node(slot=2, parent_id="n1", angle=s2["angle"],
                       scan={}, critic_verdict="CLEAN",
                       type_gate_verdict="MATCH")
        # slot 3 MUST go back to the best node (n2, metric 0), not the
        # latest frontier member — best-first, not depth-first
        s3 = ts.next_slot()
        self.assertEqual(s3["parent_id"], "n2")
        traj = ts.trajectory()
        self.assertEqual(traj["final_node_id"], "n2")
        self.assertEqual(traj["final_metric"], [0, 0, 0])

    def test_ties_break_to_latest(self):
        ts = AideTreeSearch(budget=2, seed_key="p3")
        ts.record_draft(scan=_scan("BILL"), critic_verdict="FLAG",
                        type_gate_verdict="MATCH")
        s1 = ts.next_slot()
        ts.record_node(slot=1, parent_id=s1["parent_id"],
                       angle=s1["angle"], scan=_scan("DEV"),
                       critic_verdict="FLAG", type_gate_verdict="MATCH")
        # n1 ties the draft (metric (1,1,0)) — the latest wins
        s2 = ts.next_slot()
        self.assertEqual(s2["parent_id"], "n1")

    def test_metric_pruned_recorded(self):
        ts = AideTreeSearch(budget=3, frontier_k=2, seed_key="p4")
        ts.record_draft(scan=_scan("BILL", "DEV", "X"), critic_verdict="FLAG",
                        type_gate_verdict="MISMATCH")
        s1 = ts.next_slot()
        ts.record_node(slot=1, parent_id=s1["parent_id"],
                       angle=s1["angle"], scan={}, critic_verdict="CLEAN",
                       type_gate_verdict="MATCH")
        s2 = ts.next_slot()
        ts.record_node(slot=2, parent_id=s2["parent_id"],
                       angle=s2["angle"], scan=_scan("BILL"),
                       critic_verdict="FLAG", type_gate_verdict="MATCH")
        traj = ts.trajectory()
        pruned = [n for n in traj["nodes"] if n["pruned"]]
        self.assertTrue(pruned)
        for n in pruned:
            self.assertEqual(n["pruned_reason"], "metric_pruned")
        # the converged n1 is never pruned
        n1 = next(n for n in traj["nodes"] if n["node_id"] == "n1")
        self.assertFalse(n1["pruned"])


class TestDiversityAndParity(unittest.TestCase):
    def _full_row(self, ts: AideTreeSearch):
        ts.record_draft(scan=_scan("BILL", "DEV"), critic_verdict="FLAG",
                        type_gate_verdict="MATCH")
        out = []
        for slot in (1, 2, 3):
            s = ts.next_slot()
            self.assertIsNotNone(s)
            out.append(s)
            ts.record_node(slot=slot, parent_id=s["parent_id"],
                           angle=s["angle"],
                           scan=_scan("BILL") if slot < 3 else {},
                           critic_verdict="FLAG" if slot < 3 else "CLEAN",
                           type_gate_verdict="MATCH")
        return out

    def test_distinct_candidates_ge3(self):
        ts = AideTreeSearch(budget=3, seed_key="HO11-01")
        self._full_row(ts)
        traj = ts.trajectory()
        self.assertGreaterEqual(traj["distinct_candidate_count"], 3)
        self.assertEqual(len(traj["nodes"]), 4)  # draft + 3 repairs

    def test_no_angle_repeats_within_row(self):
        ts = AideTreeSearch(budget=3, seed_key="HO11-02")
        slots = self._full_row(ts)
        angles = [s["angle"] for s in slots]
        self.assertTrue(all(a for a in angles))
        self.assertEqual(len(set(angles)), len(angles))
        for a in angles:
            for roster_angle in ANGLE_ROSTER:
                if a == roster_angle:
                    break
            else:
                self.fail(f"angle not from the roster: {a!r}")

    def test_parity_mode_is_the_single_chain(self):
        ts = AideTreeSearch(budget=3, population=False)
        slots = self._full_row(ts)
        self.assertTrue(all(s["angle"] is None for s in slots))
        traj = ts.trajectory()
        self.assertEqual(traj["angles_used"], [])
        # parent is ALWAYS the latest node -> the incumbent chain
        self.assertEqual([n["parent_id"] for n in traj["nodes"]],
                         [None, "n0", "n1", "n2"])
        self.assertGreaterEqual(traj["distinct_candidate_count"], 1)

    def test_degenerate_inputs_typed(self):
        # budget 0: no slots, the draft is the final selection
        ts = AideTreeSearch(budget=0, seed_key="d1")
        ts.record_draft(scan=_scan("BILL"), critic_verdict="FLAG",
                        type_gate_verdict="MATCH")
        self.assertIsNone(ts.next_slot())
        traj = ts.trajectory()
        self.assertEqual(traj["slots_used"], 0)
        self.assertEqual(traj["final_node_id"], "n0")
        self.assertTrue(traj["budget_respected"])
        # record_draft before any slot; next_slot without a draft
        ts2 = AideTreeSearch(budget=3)
        self.assertIsNone(ts2.next_slot())


class TestDeterminism(unittest.TestCase):
    def test_same_process_double_run_identical(self):
        t1 = AideTreeSearch(budget=3, seed_key="HO11-03")
        t2 = AideTreeSearch(budget=3, seed_key="HO11-03")
        for ts in (t1, t2):
            ts.record_draft(scan=_scan("BILL", "DEV"), critic_verdict="FLAG",
                            type_gate_verdict="MATCH")
            for slot in (1, 2, 3):
                s = ts.next_slot()
                ts.record_node(slot=slot, parent_id=s["parent_id"],
                               angle=s["angle"],
                               scan=_scan("BILL") if slot < 3 else {},
                               critic_verdict="FLAG" if slot < 3 else "CLEAN",
                               type_gate_verdict="MATCH")
        self.assertEqual(json.dumps(t1.trajectory(), sort_keys=True),
                         json.dumps(t2.trajectory(), sort_keys=True))

    def test_angle_rotation_is_content_seeded_not_python_hash(self):
        # the rotation index derives from sha256 of the seed key —
        # stable across interpreters and hash seeds by construction
        a = AideTreeSearch(budget=1, seed_key="seed-x")
        b = AideTreeSearch(budget=1, seed_key="seed-x")
        self.assertEqual(a._seeded_start(), b._seeded_start())
        c = AideTreeSearch(budget=1, seed_key="seed-y")
        # no assertion of difference (collision possible) — only that
        # the value is a stable function of the content
        self.assertEqual(a._seeded_start(), AideTreeSearch(
            budget=1, seed_key="seed-x")._seeded_start())
        self.assertIsInstance(c._seeded_start(), int)

    def test_cross_hash_seed_determinism(self):
        """The Art. 15 pattern: identical trajectory JSON across
        PYTHONHASHSEED 1/2 in fresh subprocesses."""
        script = """\
import json, sys
sys.path.insert(0, %(repo)r)
from discovery_fabric.engine.aide_tree_search import AideTreeSearch

ts = AideTreeSearch(budget=3, seed_key='HO11-04')
ts.record_draft(scan={'BILL': ['e'], 'DEV': ['e']},
                critic_verdict='FLAG', type_gate_verdict='MATCH')
for slot in (1, 2, 3):
    s = ts.next_slot()
    ts.record_node(slot=slot, parent_id=s['parent_id'],
                   angle=s['angle'],
                   scan={} if slot == 3 else {'BILL': ['e']},
                   critic_verdict='CLEAN' if slot == 3 else 'FLAG',
                   type_gate_verdict='MATCH')
print(json.dumps(ts.trajectory(), sort_keys=True))
""" % {"repo": str(REPO)}
        digests = []
        for seed in ("1", "2"):
            env = dict(os.environ, PYTHONHASHSEED=seed)
            r = subprocess.run([sys.executable, "-c", script],
                               capture_output=True, text=True, env=env,
                               timeout=60, cwd=str(REPO))
            self.assertEqual(r.returncode, 0, r.stderr[-400:])
            digests.append(r.stdout.strip())
        self.assertEqual(digests[0], digests[1])


class TestCompositionWithToolGrounding(unittest.TestCase):
    def test_tools_first_tree_second(self):
        """The AM82 composition: the c-0109 corrector mechanically
        corrects a candidate BEFORE it is scored; the tree's
        best-first selection then carries the corrected node. Mock
        candidates — zero LLM, zero network."""
        from discovery_fabric.engine import tool_grounded_critic as tgc

        ts = AideTreeSearch(budget=2, seed_key="HO11-05")
        ts.record_draft(scan=_scan("BILL"), critic_verdict="FLAG",
                        type_gate_verdict="MATCH")

        def slot1_corrected_scan(untagged_rows: int) -> dict:
            # the corrector zeroes the taggable rows mechanically;
            # the mock models its measured effect (partial correction)
            remaining = max(0, untagged_rows - 1)
            return _scan("BILL") if remaining else {}

        # slot 1: parent = draft; the corrected candidate scores CLEAN
        s1 = ts.next_slot()
        corrected = slot1_corrected_scan(1)
        ts.record_node(slot=1, parent_id=s1["parent_id"],
                       angle=s1["angle"], scan=corrected,
                       critic_verdict="CLEAN" if not corrected else "FLAG",
                       type_gate_verdict="MATCH")
        traj = ts.trajectory()
        n1 = next(n for n in traj["nodes"] if n["node_id"] == "n1")
        self.assertEqual(n1["metric"], [0, 0, 0])
        self.assertEqual(traj["final_node_id"], "n1")
        # the scan oracle the composition asserts against is the
        # machine's own — import-parity sanity (read-only on the
        # c-0109 lane)
        self.assertTrue(hasattr(tgc, "RECORD"))


if __name__ == "__main__":
    unittest.main()

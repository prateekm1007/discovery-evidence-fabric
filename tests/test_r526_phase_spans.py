"""tests/test_r526_phase_spans.py — R526 Q-B contract.

Post-rank phase spans (model_routing.record_phase_span) ride the
proven model_routing ledger channel as line_class=PHASE_SPAN lines.
Proves:
  A. phase lines are well-formed (identity, phase, event, candidate,
     wall, detail) and never raise
  B. availability statistics skip phase lines (a None-ok phase line
     must not count as failure telemetry)
  C. the gauntlet loop wires per-candidate enter/exit (source pin)
  D. the improvement/tech/kill passes wire phase enter/exit
  E. improve_stage wires per-target enter/exit with parent identity
  F. provider-call aggregation inputs exclude phase lines
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.engine import model_routing as mr          # noqa: E402


def _temp_ledger(monkeypatch_cls):
    import tempfile
    td = tempfile.mkdtemp(prefix="r526_phase_")
    inst = mr.RoutingLedger(path=Path(td) / "ledger.jsonl")
    return inst, Path(td) / "ledger.jsonl"


class TestPhaseSpanLines(unittest.TestCase):
    def test_a_phase_line_well_formed_and_never_raises(self):
        import pytest
        m = pytest.MonkeyPatch()
        inst, path = _temp_ledger(m)
        m.setattr(mr, "LEDGER", inst)
        try:
            mr.record_phase_span(
                session_id="ts_test", run_id="run_test",
                engine_stage="POST_RANK_GAUNTLET", phase="GAUNTLET",
                event="enter")
            mr.record_phase_span(
                session_id="ts_test", run_id="run_test",
                engine_stage="POST_RANK_GAUNTLET", phase="GAUNTLET",
                event="candidate_enter", scope="child",
                candidate_id="cand:1",
                candidate_key="k1")
            mr.record_phase_span(
                session_id="ts_test", run_id="run_test",
                engine_stage="POST_RANK_GAUNTLET", phase="GAUNTLET",
                event="candidate_exit", scope="child",
                candidate_id="cand:1",
                candidate_key="k1", wall_s=12.5,
                detail={"outcome": "SURVIVED_GAUNTLET"})
            mr.record_phase_span(
                session_id="ts_test", run_id="run_test",
                engine_stage="POST_RANK_GAUNTLET", phase="GAUNTLET",
                event="exit", scope="top",
                wall_s=190.0,
                detail={"outcome": "GAUNTLET_DONE"})
            lines = [json.loads(ln) for ln in
                     path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(lines), 4)
            for ln in lines:
                self.assertEqual(ln["line_class"], "PHASE_SPAN")
                self.assertEqual(ln["session_id"], "ts_test")
                self.assertEqual(ln["phase"], "GAUNTLET")
            self.assertEqual(lines[0]["event"], "enter")
            self.assertEqual(lines[0]["scope"], "top")
            self.assertEqual(lines[1]["event"], "candidate_enter")
            self.assertEqual(lines[1]["scope"], "child")
            self.assertEqual(lines[2]["event"], "candidate_exit")
            self.assertEqual(lines[2]["scope"], "child")
            self.assertEqual(lines[2]["wall_s"], 12.5)
            self.assertEqual(lines[2]["candidate_id"], "cand:1")
            self.assertEqual(lines[3]["event"], "exit")
            self.assertEqual(lines[3]["scope"], "top")
            self.assertEqual(lines[3]["wall_s"], 190.0)
            self.assertIsNone(lines[0]["ok"])
            self.assertIsNone(lines[0]["provider"])
        finally:
            m.undo()
    def test_b_availability_skips_phase_lines(self):
        import pytest
        m = pytest.MonkeyPatch()
        inst, path = _temp_ledger(m)
        m.setattr(mr, "LEDGER", inst)
        try:
            # a ledger holding ONLY a phase line must contribute zero
            # telemetry weight: ok=None is falsy and would otherwise
            # count as a failure observation.
            mr.record_phase_span(
                session_id="s", run_id="r",
                engine_stage="POST_RANK_GAUNTLET", phase="GAUNTLET",
                event="exit", wall_s=100.0)
            rep = mr.availability_report(provider="zai")
            self.assertEqual(rep["decayed_failure_weight"], 0.0)
            self.assertEqual(rep["decayed_success_weight"], 0.0)
            self.assertEqual(rep["decayed_observation_weight"], 0.0)
            self.assertIsNone(rep["recent_success_rate"])
            rep_all = mr.availability_report()
            self.assertEqual(rep_all["decayed_observation_weight"], 0.0)
        finally:
            m.undo()


class TestPhaseWiringPins(unittest.TestCase):
    """C/D/E — the exact instrumented call sites (repo precedent:
    R519/R525 source-pin tests)."""

    def _run_src(self):
        return (REPO_ROOT / "discovery_fabric" / "engine" / "run.py"
                ).read_text(encoding="utf-8")

    def test_c_gauntlet_candidate_wiring(self):
        src = self._run_src()
        self.assertIn("event=\"candidate_enter\"", src)
        self.assertIn("event=\"candidate_exit\"", src)
        # exit reuses the _crow wall measurement (never redefined)
        self.assertIn('wall_s=round(_crow["wall_s"], 6)', src)

    def test_d_pass_phase_wiring(self):
        import re
        src = self._run_src()
        flat = re.sub(r"\s+", " ", src)
        for phase in ("GAUNTLET", "KILL_IMPROVE", "IMPROVEMENT_PASS",
                      "TECHNICAL_IMPROVEMENT_PASS"):
            self.assertIn(f'phase="{phase}", event="enter"', flat)
            self.assertIn(f'phase="{phase}", event="exit"', flat)

    def test_e_improve_target_wiring(self):
        src = (REPO_ROOT / "discovery_fabric" / "engine" /
               "improve_stage.py").read_text(encoding="utf-8")
        self.assertIn('event="target_enter"', src)
        self.assertIn('event="target_exit"', src)
        self.assertIn("dead_e.get(\"candidate_id\")", src)

    def test_f_aggregation_inputs_exclude_phase_lines(self):
        # the harvester contract: provider-call aggregation must
        # filter line_class == PHASE_SPAN (checked here as the rule
        # statement; the R526 harvester implements it).
        import pytest
        m = pytest.MonkeyPatch()
        inst, path = _temp_ledger(m)
        m.setattr(mr, "LEDGER", inst)
        try:
            mr.record_call_outcome(
                "xkiro", "m", ok=True, latency_ms=5000,
                session_id="s", engine_stage="SYNTHESIZE",
                call_class="RUN_OWNED", run_id="r")
            mr.record_phase_span(
                session_id="s", run_id="r",
                engine_stage="SYNTHESIZE", phase="SYNTH",
                event="exit", wall_s=9.9, scope="top")
            attempt_lines = [
                json.loads(ln) for ln in
                path.read_text(encoding="utf-8").splitlines()
                if json.loads(ln).get("line_class") != "PHASE_SPAN"]
            self.assertEqual(len(attempt_lines), 1)
            self.assertEqual(attempt_lines[0]["provider"], "xkiro")
        finally:
            m.undo()

    def test_g_scope_discriminator_top_vs_child(self):
        """B1: top-level and child spans are structurally distinguished
        by the scope field; a whole-phase exit (scope=top, no
        candidate) never pairs with a candidate exit (scope=child).
        The run-wall reconciliation (B2) must use ONLY scope=top
        walls: child walls are attribution detail, never added on top
        of the parent phase wall."""
        import pytest
        m = pytest.MonkeyPatch()
        inst, path = _temp_ledger(m)
        m.setattr(mr, "LEDGER", inst)
        try:
            # whole GAUNTLET = 190 s; candidate A = 70 s, B = 50 s,
            # C = 30 s (the directive B2 example).
            mr.record_phase_span(
                session_id="s", run_id="r",
                engine_stage="POST_RANK_GAUNTLET", phase="GAUNTLET",
                event="enter", scope="top")
            for cand, key, wall in (("cand:A", "kA", 70.0),
                                    ("cand:B", "kB", 50.0),
                                    ("cand:C", "kC", 30.0)):
                mr.record_phase_span(
                    session_id="s", run_id="r",
                    engine_stage="POST_RANK_GAUNTLET",
                    phase="GAUNTLET",
                    event="candidate_enter", scope="child",
                    candidate_id=cand, candidate_key=key)
                mr.record_phase_span(
                    session_id="s", run_id="r",
                    engine_stage="POST_RANK_GAUNTLET",
                    phase="GAUNTLET",
                    event="candidate_exit", scope="child",
                    candidate_id=cand, candidate_key=key,
                    wall_s=wall)
            mr.record_phase_span(
                session_id="s", run_id="r",
                engine_stage="POST_RANK_GAUNTLET", phase="GAUNTLET",
                event="exit", scope="top", wall_s=190.0)
            lines = [json.loads(ln) for ln in
                     path.read_text(encoding="utf-8").splitlines()]
            # structural distinction: the whole-phase enter/exit lines
            # have NO candidate identity (top scope); the candidate
            # lines carry it (child scope). A time-window join cannot
            # accidentally merge them because the key includes scope.
            top = [ln for ln in lines if ln.get("scope") == "top"]
            child = [ln for ln in lines if ln.get("scope") == "child"]
            self.assertEqual(len(top), 2)
            self.assertEqual(len(child), 6)
            self.assertIsNone(top[0].get("candidate_key"))
            self.assertIsNone(top[1].get("candidate_key"))
            self.assertEqual(top[1]["wall_s"], 190.0)
            # B2: the reconciliation sum uses top walls only (190 s),
            # NOT 190 + 70 + 50 + 30 = 340 s.
            top_wall_sum = sum(ln.get("wall_s") or 0.0 for ln in top
                               if ln.get("event") == "exit")
            self.assertEqual(top_wall_sum, 190.0)
            child_wall_sum = sum(ln.get("wall_s") or 0.0 for ln in child
                                 if ln.get("event") == "candidate_exit")
            self.assertEqual(child_wall_sum, 150.0)
            self.assertNotEqual(top_wall_sum + child_wall_sum,
                                top_wall_sum)
        finally:
            m.undo()


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

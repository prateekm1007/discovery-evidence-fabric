"""tests/test_r515_improve_station.py — R515 adversarial battery for the
IMPROVE stationing change (auditor directive, Part A/B + starvation
interaction).

The 12 required proofs (test 9 lives in test_r515_yield_starvation.py
against the v1.1.0 instrument; the mapping is recorded in
R515/R515_ROUND_RECORD.json):

  1. fresh normal run has no sequential D8 IMPROVE stage
  2. remaining D8 stages run in their exact declared order
  3. no-kill run produces zero actual IMPROVE mutation calls
  4. kill-evidence run invokes the actual IMPROVE implementation
     exactly once at the kill point
  5. admitted child carries parent identity, kill-basis hash, causal
     change and fresh re-evaluation
  6. improvement transport failure records the typed infrastructure
     state
  7. resume does not manufacture a second mutation
  8. starved run stays MECHANISM_STARVED under a promoting evolution
 10. diverse run admits collision/attack exactly as before
 11. unknown distinctness fails open
 12. non-starved kill-point behavior unchanged

Every test attacks the bypass (Art. XXX): each would FAIL if the
prohibited behavior (second invocation site, synthetic child,
re-burned mutation, promoted starved terminal) were present.
Hermetic: stub adapters, mocked gates, fixture bytes only.
"""
from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.adapters import (  # noqa: E402
    ADAPTERS, STAGE_ORDER, ImproveAdapter)
from discovery_fabric.engine import improve_stage as imp  # noqa: E402
from discovery_fabric.engine import stage_entry  # noqa: E402
from discovery_fabric.engine.run import (  # noqa: E402
    IMPROVE_EXECUTED_STATUSES, improve_kill_point_resume_state)

# the R481 hermetic gauntlet harness (real modules, patched gates —
# the production verdict vocabulary, not a reimplementation).
from tests.test_r481_improve_stage import (  # noqa: E402
    PASS_GATES, VALID, _payload)
from tests.test_r514_starvation_gate import (  # noqa: E402
    _run_stubbed)

_GATE_ATTRS = (
    ("discovery_fabric.engine.invention_spec", "build_invention_spec"),
    ("discovery_fabric.engine.engineering_spec",
     "build_engineering_spec"),
    ("discovery_fabric.engine.physics_gate",
     "evaluate_candidate_physics"),
    ("discovery_fabric.engine.engineering_attack",
     "attack_engineering"),
    ("discovery_fabric.engine.engineering_attack",
     "repair_engineering"),
    ("discovery_fabric.engine.independent_attack",
     "independent_attack"),
    ("discovery_fabric.engine.dossier_quality",
     "evaluate_dossier_quality"),
    ("discovery_fabric.engine.llm_registry", "generate"),
)


def _payload_restored(testcase, td, dead, gates):
    """r481 _payload + guaranteed gate restoration (the harness
    patches module globals; without restore they leak across tests
    in the session — Art. IX)."""
    import importlib
    saved = {}
    for modname, attr in _GATE_ATTRS:
        mod = importlib.import_module(modname)
        saved[(modname, attr)] = getattr(mod, attr, None)

    def _restore():
        for (modname, attr), fn in saved.items():
            if fn is not None:
                setattr(importlib.import_module(modname), attr, fn)
    testcase.addCleanup(_restore)
    payload, _ = _payload(td, dead, gates)
    return payload

D8_15 = ["RETRIEVE", "FREEZE", "PREMISE_GATE", "SYNTHESIZE", "VERIFY",
         "MECHANISM_SPACE", "COLLISION", "PHYSICS", "ATTACK",
         "CONTRADICTION", "KILLER_EXPERIMENT", "ADJUDICATION",
         "CLASSIFY", "NEXT_BEST_ACTION", "RANK"]


class TestLinearPlaceholderGone(unittest.TestCase):
    """Required tests 1-2: the D8 chain without the dead slot."""

    def test_1_no_sequential_d8_improve_stage(self):
        self.assertNotIn("IMPROVE", STAGE_ORDER)
        self.assertEqual(len(STAGE_ORDER), 15)

    def test_2_remaining_stages_in_exact_declared_order(self):
        self.assertEqual(list(STAGE_ORDER), D8_15)

    def test_kill_point_operation_still_registered_single(self):
        # Part B: exactly one canonical mutation implementation —
        # the registered kill-point operation (no duplicate, no
        # second engine created by this round).
        self.assertIn("IMPROVE", ADAPTERS)
        self.assertIsInstance(ADAPTERS["IMPROVE"], ImproveAdapter)
        self.assertEqual(ADAPTERS["IMPROVE"].canonical_fn,
                         "improve_stage.run_improve")
        import discovery_fabric.engine.improve_stage as _is
        self.assertIs(_is.run_improve, imp.run_improve)

    def test_kill_point_is_the_only_invocation_site(self):
        # Attacks the bypass directly: a second env.run_stage
        # IMPROVE call site (a restored linear slot by another
        # name) fails this test. Source-level pin (the r483
        # REG_SRC precedent): exactly one call site in run.py.
        src = (REPO / "discovery_fabric" / "engine" / "run.py"
               ).read_text(encoding="utf-8")
        sites = re.findall(r'run_stage\(\s*"IMPROVE"', src)
        self.assertEqual(len(sites), 1,
                         f"IMPROVE invocation sites != 1: {len(sites)}")


class TestKillPointSemantics(unittest.TestCase):
    """Required tests 3-6 + 12: run_improve behavior at the kill point."""

    def test_3_no_kill_run_produces_zero_mutation_calls(self):
        calls = []

        def _counting(*a, **k):
            calls.append((a, k))
            return type("R", (), {"status": "OK", "content": VALID,
                                  "provider_id": "atria"})()

        gates = dict(PASS_GATES)
        gates["generate"] = _counting
        with tempfile.TemporaryDirectory() as td:
            payload = _payload_restored(self, td, [], gates)
            res = imp.run_improve(payload)
        self.assertEqual(res["status"], "NO_KILL_EVIDENCE")
        self.assertEqual(calls, [],
                         "mutation LLM called with zero dead — "
                         "a synthetic child path")

    def test_4_kill_evidence_invokes_improve_exactly_once(self):
        calls = []

        def _counting(*a, **k):
            calls.append((a, k))
            return type("R", (), {"status": "OK", "content": VALID,
                                  "provider_id": "atria"})()

        gates = dict(PASS_GATES)
        gates["generate"] = _counting
        dead = [{"candidate_id": "cand-1", "key": "mech-OP-1",
                 "kill_class": "PHYSICS",
                 "kill_basis": ["input envelope violates bound x"],
                 "parent_fields": {"mechanism": "a fixed damper",
                                   "intervention": "bolt it"}}]
        with tempfile.TemporaryDirectory() as td:
            payload = _payload_restored(self, td, dead, gates)
            res = imp.run_improve(payload)
        self.assertEqual(len(calls), 1,
                         f"expected exactly 1 mutation call, got "
                         f"{len(calls)}")
        self.assertEqual(res["status"], "CHILDREN_ADMITTED")
        self.assertEqual(res["ledger"]["dead_consumed"], 1)

    def test_5_admitted_child_carries_lineage_and_fresh_reeval(self):
        dead = [{"candidate_id": "cand-1", "key": "mech-OP-1",
                 "kill_class": "PHYSICS",
                 "kill_basis": ["input envelope violates bound x"],
                 "parent_fields": {"mechanism": "a fixed damper",
                                   "intervention": "bolt it"}}]
        with tempfile.TemporaryDirectory() as td:
            payload = _payload_restored(self, td, dead, PASS_GATES)
            res = imp.run_improve(payload)
        self.assertEqual(res["status"], "CHILDREN_ADMITTED")
        ch = res["children"][0]
        lin = ch["improve_lineage"]
        self.assertEqual(lin["parent_id"], "cand-1")
        from discovery_fabric.engine.candidate import sha256_obj
        self.assertEqual(lin["kill_basis_hash"],
                         sha256_obj(["input envelope violates bound x"]))
        # fresh re-evaluation fields present on the evaluated entry,
        # nothing inherited
        for field in ("attack", "independent_attack", "quality",
                      "killed", "physics_lifecycle"):
            self.assertIn(field, ch)
        self.assertFalse(ch["killed"])
        # front door: the child joined the mechanism space carrying
        # the causal change + novel design variable on its
        # derivation trace
        ms = res["apply_to"]["mechanism_space"]
        ms_child = ms["candidates"][-1]
        self.assertTrue(
            ms_child["candidate_id"].endswith("+improve-g1"))
        trace = ms_child["derivation_trace"]
        self.assertTrue(trace["causal_change"])
        self.assertTrue(trace["novel_design_variable"])
        self.assertEqual(trace["improved_from"], "cand-1")

    def test_6_transport_failure_records_typed_infrastructure_state(
            self):
        tgate = dict(PASS_GATES)

        def _boom(*a, **k):
            raise ConnectionError("endpoint unreachable")
        tgate["generate"] = _boom
        dead = [{"candidate_id": "cand-3", "key": "mech-OP-3",
                 "kill_class": "PHYSICS", "kill_basis": ["b"],
                 "parent_fields": {"mechanism": "m",
                                   "intervention": "i"}}]
        with tempfile.TemporaryDirectory() as td:
            payload = _payload_restored(self, td, dead, tgate)
            res = imp.run_improve(payload)
        self.assertEqual(res["status"], "IMPROVEMENT_BLOCKED_TRANSPORT")
        self.assertEqual(res["children"], [])
        self.assertEqual(res["apply_to"], {})
        self.assertIn("ConnectionError", res["transport"]["error"])

    def test_12_non_starved_kill_point_behavior_unchanged(self):
        # The R515 stationing change must not alter kill-point
        # semantics on diverse runs: full ledger shape + status
        # vocabulary identical to the pre-change contract.
        dead = [{"candidate_id": "cand-9", "key": "mech-OP-9",
                 "kill_class": "PHYSICS", "kill_basis": ["b"],
                 "parent_fields": {"mechanism": "m",
                                   "intervention": "i"}}]
        with tempfile.TemporaryDirectory() as td:
            payload = _payload_restored(self, td, dead, PASS_GATES)
            res = imp.run_improve(payload)
        self.assertEqual(res["status"], "CHILDREN_ADMITTED")
        for key in ("dead_consumed", "dead_total", "max_children",
                    "children_admitted", "children_rekilled",
                    "attempts", "loop_closure"):
            self.assertIn(key, res["ledger"])
        self.assertIn("re-entered the SAME gauntlet",
                      res["ledger"]["loop_closure"])


class TestResumeManufacturesNoSecondMutation(unittest.TestCase):
    """Required test 7: the extracted resume predicate."""

    def _write(self, td, name, obj):
        (Path(td) / name).write_text(
            __import__("json").dumps(obj))

    def test_executed_outcomes_count_as_done(self):
        with tempfile.TemporaryDirectory() as td:
            for status in sorted(IMPROVE_EXECUTED_STATUSES):
                self._write(td, "stage_IMPROVE.json",
                            {"status": status})
                done, seen = improve_kill_point_resume_state(td)
                self.assertTrue(done, status)
                self.assertEqual(seen, status)

    def test_missing_corrupt_or_failure_state_re_executes(self):
        with tempfile.TemporaryDirectory() as td:
            # missing file
            done, seen = improve_kill_point_resume_state(td)
            self.assertFalse(done)
            self.assertIsNone(seen)
            # corrupt bytes
            (Path(td) / "stage_IMPROVE.json").write_text("{nope")
            done, seen = improve_kill_point_resume_state(td)
            self.assertFalse(done)
            # a FAILURE record is not an executed outcome
            self._write(td, "stage_IMPROVE.json",
                        {"error": "boom"})
            done, seen = improve_kill_point_resume_state(td)
            self.assertFalse(done)
            # the old deferral never counts as done (a deferral must
            # still execute at the kill point)
            self._write(td, "stage_IMPROVE.json",
                        {"status": "DEFERRED_TO_KILL_POINT"})
            done, seen = improve_kill_point_resume_state(td)
            self.assertFalse(done)
            self.assertEqual(seen, "DEFERRED_TO_KILL_POINT")

    def test_failure_sidecar_alone_does_not_count(self):
        # stage_IMPROVE_FAILURE.json without stage_IMPROVE.json: the
        # mutation never produced an executed outcome.
        with tempfile.TemporaryDirectory() as td:
            self._write(td, "stage_IMPROVE_FAILURE.json",
                        {"stage": "IMPROVE", "error": "x"})
            done, _ = improve_kill_point_resume_state(td)
            self.assertFalse(done)


class TestStarvationInteraction(unittest.TestCase):
    """Required tests 8, 10, 11 on the 15-stage chain."""

    def test_8_starved_terminal_holds_without_linear_slot(self):
        # Promoting evolution + NO linear IMPROVE slot anywhere in
        # the log: the terminal must stay MECHANISM_STARVED.
        with tempfile.TemporaryDirectory() as td:
            from tests.test_r514_starvation_gate import _run_stubbed
            engine, fired = _run_stubbed(
                1, td,
                evo_final={"final_status": "INVENTION_REQUIRES_EXPERIMENT",
                           "reason": "mock promoting evolution"})
            self.assertEqual(fired, [])
            stages = [e["stage"] for e in engine.env.stage_log]
            self.assertNotIn("IMPROVE", stages)
            import json as _json
            final = _json.loads(
                (Path(td) / "final_state.json").read_text())
            self.assertEqual(final["final_status"],
                             "MECHANISM_STARVED")

    def test_10_diverse_run_admits_collision_attack(self):
        with tempfile.TemporaryDirectory() as td:
            from tests.test_r514_starvation_gate import _run_stubbed
            engine, fired = _run_stubbed(2, td)
            self.assertIn("COLLISION", fired)
            self.assertIn("ATTACK", fired)

    def test_11_unknown_distinctness_fails_open(self):
        from discovery_fabric.engine.candidate import Candidate
        env = Candidate(problem={"problem_id": "x"},
                        problem_id="x")
        env.mechanism_space = {"state": "BUILT",
                               "n_candidates_retained": 1}
        for stage in ("COLLISION", "ATTACK"):
            block = stage_entry.justify(stage, env, {}, set())
            self.assertEqual(block["entry_status"], "ALLOWED", stage)


if __name__ == "__main__":
    unittest.main()

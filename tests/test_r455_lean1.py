"""tests/test_r455_lean1.py — R455-LEAN-1 "NO SURVIVOR, NO ARTIFACT;
NO REASONING, NO SPEND" (the EXT-AUDIT-LEAN-R454 §O coder directive).

The five required tests (§O.8):

  1. test_r455_no_survivor_no_artifact
       a run terminating without a surviving, promoted candidate
       produces ZERO GLB/render/package artifacts and exactly one
       honest NO_SURVIVOR bridge report.
  2. test_r455_bridge_no_invention_branch_reachable
       the refusal branches are EXERCISED (the audited defect: the
       NO_INVENTION branch was unreachable because every run's
       final_state.json manufactured a CIO) — and the survivor-class
       positive control still passes the gate (Art. V: not a universal
       rejector).
  3. test_r455_model_route_matches_ledger
       `model_route.call_count` equals the run's OWN routing-ledger
       run-owned count — positive AND negative controls; envelope
       aggregation is dead (the audited 13-vs-1 defect, Art. XXIV).
  4. test_r455_mechanism_generated_requires_mechanism
       `GENERATED + mechanism: null` is unrepresentable at the single
       canonical writer (the audited live nonsense combination).
  5. test_r455_capability_gate_precedes_retrieval
       on a degraded-only route, ZERO retrieval sources are queried:
       the pre-retrieval capability gate records BLOCKED /
       CAPABILITY_INSUFFICIENT before any spend, and the run stays
       resumable on a capable route (Art. LXI).

Constitutional contract:
  - OFFLINE by construction (the r446 stub pattern): no network, no
    LLM, no Blender, no Chromium (Art. LXI discipline).
  - Art. V: every refusal has a positive control — survivor-class
    runs and capable routes still pass.
  - reviewer_provenance=AI_REVIEW (Art. LXVII).
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from toscanini import bridge_gate  # noqa: E402
from toscanini import run_state as rs  # noqa: E402
from toscanini import sessions as store  # noqa: E402


# ---------------------------------------------------------------------------
# fixture helpers
# ---------------------------------------------------------------------------

_NON_SURVIVOR_RELEASE = {
    "release_id": "rel:run_a:nosurvivor",
    "run_id": "run_a",
    "candidate_id": None,
    "invention_id": None,
    "problem_id": "p_a",
    "invention_spec_hash": None,
    "engineering_spec_hash": None,
    "status": "DISCOVERY_INCOMPLETE",
    "failure_reason": ("model did not emit verbatim evidence-bound "
                       "spans (INCOMPLETE_INFERENCE_FAILURE)"),
}

_SURVIVOR_RELEASE = {
    "release_id": "rel:run_b:inv_abc123",
    "run_id": "run_b",
    "candidate_id": "cand_1",
    "invention_id": "inv:run_b:abc123def456",
    "problem_id": "p_b",
    "invention_spec_hash": "a" * 64,
    "engineering_spec_hash": "b" * 64,
    "status": "HELD_FOR_HUMAN_REVIEW",
    "failure_reason": None,
}


def _session(run_dir: Path) -> dict:
    return {"session_id": "ts_r455_test", "status": "COMPLETE",
            "run_dir": str(run_dir)}


def _patched_store(monkeypatch, run_dir: Path):
    session = _session(run_dir)
    monkeypatch.setattr(store, "get_session", lambda sid: dict(session))
    monkeypatch.setattr(store, "update_session",
                        lambda sid, **f: dict(session))
    monkeypatch.setattr(store, "session_detail", lambda sid: {})
    return session


def _write(run_dir: Path, name: str, obj) -> Path:
    p = run_dir / name
    p.write_text(json.dumps(obj))
    return p


# ---------------------------------------------------------------------------
# 1 — no survivor, no artifact
# ---------------------------------------------------------------------------

class TestNoSurvivorNoArtifact(unittest.TestCase):
    """§O.8-1: a no-survivor run gets ONE honest record and NOTHING
    else — no GLB, no render job, no package."""

    def test_r455_no_survivor_no_artifact(self, ):
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td) / "run"
            run_dir.mkdir()
            # the audited failure shape: final_state exists (every run
            # writes one), the release says DISCOVERY_INCOMPLETE with a
            # null invention identity — AND a stale GLB from an earlier
            # generation sits in MODEL/ (the stale-positive trap: the
            # gate must add nothing and must not present it as current)
            (run_dir / "MODEL").mkdir()
            (run_dir / "MODEL" / "model-001.glb").write_bytes(b"stale")
            _write(run_dir, "final_state.json",
                   {"run_id": "run_a", "final_status":
                    "INCOMPLETE_INFERENCE_FAILURE"})
            _write(run_dir, "DISCOVERY_RELEASE.json",
                   _NON_SURVIVOR_RELEASE)

            with mock.patch.object(store, "get_session",
                                   lambda sid: _session(run_dir)), \
                 mock.patch.object(store, "update_session",
                                   lambda sid, **f: dict(
                                       _session(run_dir))), \
                 mock.patch.object(store, "session_detail",
                                   lambda sid: {}):
                report = bridge_gate.ensure_artifacts("ts_r455_test")

            self.assertEqual(report["outcome"], "NO_SURVIVOR")
            gate = report.get("survivor_gate") or {}
            self.assertEqual(gate.get("status"), "DISCOVERY_INCOMPLETE")
            self.assertIsNone(gate.get("invention_id"))
            self.assertIn("no surviving, promoted candidate",
                          report.get("note", ""))
            # ZERO artifact additions: no bridge package, no new model
            self.assertFalse(list(run_dir.glob("TECHNOLOGY_PACKAGE_*.zip")))
            self.assertFalse(list(run_dir.glob("TECHNOLOGY_TRANSFER_"
                                              "PACKAGE_*.zip")))
            self.assertEqual(
                sorted(p.name for p in (run_dir / "MODEL").glob("*")),
                ["model-001.glb"],
                "the stale GLB is untouched — the gate neither "
                "endorses it as current nor replaces it")
            # the persisted report is the only new file
            self.assertTrue((run_dir / "BRIDGE_REPORT.json").is_file())

    def test_render_request_never_fires_on_no_survivor(self):
        """The audited runs received full render sets on non-inventions:
        the async render REQUEST must be unreachable from the refusal
        path."""
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td) / "run"
            run_dir.mkdir()
            _write(run_dir, "final_state.json", {"run_id": "run_a"})
            _write(run_dir, "DISCOVERY_RELEASE.json",
                   _NON_SURVIVOR_RELEASE)
            with mock.patch.object(store, "get_session",
                                   lambda sid: _session(run_dir)), \
                 mock.patch.object(store, "update_session",
                                   lambda sid, **f: dict(
                                       _session(run_dir))), \
                 mock.patch.object(store, "session_detail",
                                   lambda sid: {}), \
                 mock.patch.object(bridge_gate, "_request_renders",
                                   side_effect=AssertionError(
                                       "a render request fired on a "
                                       "no-survivor run")):
                report = bridge_gate.ensure_artifacts("ts_r455_test")
            self.assertEqual(report["outcome"], "NO_SURVIVOR")


# ---------------------------------------------------------------------------
# 2 — the refusal branches are reachable (and the survivor path lives)
# ---------------------------------------------------------------------------

class TestRefusalBranchesReachable(unittest.TestCase):
    """§O.8-2: the NO_INVENTION/NO_SURVIVOR branch is exercised — the
    audit measured it UNREACHABLE at the audited HEAD (every run wrote
    final_state.json, which manufactured a CIO and made
    `_invention_exists` always true)."""

    def test_r455_bridge_no_invention_branch_reachable(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td) / "run"
            run_dir.mkdir()
            # release record ABSENT (pre-release-era record): the legacy
            # branch decides — and with the cio.py fix, final_state.json
            # alone no longer manufactures a CIO
            _write(run_dir, "final_state.json",
                   {"run_id": "run_c", "final_status":
                    "INCOMPLETE_INFERENCE_FAILURE"})
            with mock.patch.object(store, "get_session",
                                   lambda sid: _session(run_dir)), \
                 mock.patch.object(store, "update_session",
                                   lambda sid, **f: dict(
                                       _session(run_dir))), \
                 mock.patch.object(store, "session_detail",
                                   lambda sid: {}):
                report = bridge_gate.ensure_artifacts("ts_r455_test")
            self.assertEqual(report["outcome"], "NO_INVENTION")
            self.assertFalse(
                (run_dir / "MODEL" / "model-001.glb").exists())

    def test_survivor_release_still_passes_the_gate(self):
        """Art. V positive control: a survivor-class release (HELD for
        human review, invention identity present) PASSES the gate and
        the bridge is invoked."""
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td) / "run"
            run_dir.mkdir()
            _write(run_dir, "DISCOVERY_RELEASE.json", _SURVIVOR_RELEASE)
            _write(run_dir, "INVENTION_SPECIFICATION.json",
                   {"invention_id": {"value": _SURVIVOR_RELEASE[
                       "invention_id"]}})
            called = {}

            def _fake_bridge(detail, cio_obj, run_dir_s, **kw):
                called["invoked"] = True
                return {"geometry_out": None,
                        "visualizability": {"visualizability_class":
                                            "SYSTEM_3D"},
                        "package_out": None, "report": {"steps": []}}

            from discovery_fabric.engine.invention_bridge import bridge \
                as bridge_mod
            with mock.patch.object(store, "get_session",
                                   lambda sid: _session(run_dir)), \
                 mock.patch.object(store, "update_session",
                                   lambda sid, **f: dict(
                                       _session(run_dir))), \
                 mock.patch.object(store, "session_detail",
                                   lambda sid: {}), \
                 mock.patch.object(bridge_mod, "bridge", _fake_bridge):
                report = bridge_gate.ensure_artifacts("ts_r455_test")
            self.assertTrue(called.get("invoked"),
                            "a survivor-class run must still reach the "
                            "bridge (Art. V: fail closed, not a "
                            "universal rejector)")
            self.assertNotIn(report["outcome"],
                             ("NO_SURVIVOR", "NO_INVENTION"))


# ---------------------------------------------------------------------------
# 3 — model_route tells the ledger's truth
# ---------------------------------------------------------------------------

_LEDGER_LINE = {
    "request_id": "req_x1", "run_id": "run_d", "session_id": "ts_x",
    "engine_stage": "SYNTHESIZE", "call_class": "RUN_OWNED",
    "stage": "synthesis", "task": "STRONG", "provider": "localqwen",
    "model": "qwen3-1.7b", "attempt": 1, "ok": True, "status": "OK",
    "latency_ms": 29626, "cost_class": "ZERO_PAID_COST_SELF_HOSTED",
    "task_degradation": {"requested_task": "STRONG",
                         "actual_task_capability":
                         "CHEAP_EMERGENCY_FALLBACK",
                         "task_capability_match": False},
}

_PROBE_LINE = {
    "request_id": "req_p1", "run_id": None, "engine_stage": None,
    "call_class": "CAPABILITY_PROBE", "task": None,
    "provider": "localqwen", "model": "qwen3-1.7b", "ok": True,
    "status": "OK", "latency_ms": 12,
}


def _envelope_with_fake_providers(n: int) -> dict:
    """The OLD aggregation source: an envelope carrying n provider
    records (the audited 13-vs-1 shape)."""
    return {"stage_log": [
        {"stage": f"s{i}", "status": "OK",
         "provider": "ghost", "model": "m", "status_ok": True,
         "latency_ms": 1, "purpose": "p"} for i in range(n)]}


class TestModelRouteMatchesLedger(unittest.TestCase):
    """§O.8-3: call_count == the ledger's run-owned count (positive and
    negative controls, Art. V); envelopes are never aggregated."""

    def _route(self, run_dir: Path):
        return rs._model_route({}, run_dir)

    def test_r455_model_route_matches_ledger(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td) / "run"
            run_dir.mkdir()
            _write(run_dir, "ROUTING_LEDGER_RUN.json", {
                "run_id": "run_d", "line_count": 3,
                "run_owned_call_lines": 1,
                "capability_probe_lines": 2,
                "lines": [dict(_LEDGER_LINE),
                          dict(_PROBE_LINE), dict(_PROBE_LINE)]})
            # the aggregation bait: 12 fake provider records in the
            # envelope — the old code reported 1 + 12 = 13 "calls"
            _write(run_dir, "envelope_SYNTHESIZE.json",
                   _envelope_with_fake_providers(12))

            route = self._route(run_dir)
            self.assertEqual(route["call_count"], 1,
                             "call_count is the ledger's run-owned "
                             "count — envelopes are never aggregated")
            self.assertEqual(len(route["calls"]), 1)
            call = route["calls"][0]
            self.assertEqual(call["provider"], "localqwen")
            self.assertEqual(call["model"], "qwen3-1.7b")
            self.assertEqual(call["actual_task_capability"],
                             "CHEAP_EMERGENCY_FALLBACK")
            self.assertEqual(call["task_capability_match"], False)
            self.assertEqual(route["capability_probe_lines"], 2)
            self.assertIn("ROUTING_LEDGER_RUN.json", route["basis"])

    def test_negative_control_count_tracks_the_ledger(self):
        """Art. V negative control: tamper the ledger to 2 run-owned
        lines and the reported count FOLLOWS THE LEDGER — it can never
        be derived from the envelopes."""
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td) / "run"
            run_dir.mkdir()
            second = dict(_LEDGER_LINE)
            second.update({"engine_stage": "ATTACK", "task": "STRONG"})
            _write(run_dir, "ROUTING_LEDGER_RUN.json", {
                "run_id": "run_d", "line_count": 4,
                "run_owned_call_lines": 2,
                "lines": [dict(_LEDGER_LINE), second,
                          dict(_PROBE_LINE)]})
            _write(run_dir, "envelope_SYNTHESIZE.json",
                   _envelope_with_fake_providers(5))
            route = self._route(run_dir)
            self.assertEqual(route["call_count"], 2)
            self.assertEqual(
                sorted(c["role"] for c in route["calls"]),
                ["ATTACK", "SYNTHESIZE"])

    def test_ledger_absent_is_honest_absence(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td) / "run"
            run_dir.mkdir()
            _write(run_dir, "envelope_SYNTHESIZE.json",
                   _envelope_with_fake_providers(3))
            route = self._route(run_dir)
            self.assertEqual(route["call_count"], 0)
            self.assertIn("absent", route["basis"])


# ---------------------------------------------------------------------------
# 4 — GENERATED requires a mechanism
# ---------------------------------------------------------------------------

class TestMechanismInvariant(unittest.TestCase):
    """§O.8-4: `mechanism_state.state = GENERATED` with a null
    mechanism is unrepresentable at the single canonical writer
    (`run_state._mechanism_state`)."""

    def test_r455_mechanism_generated_requires_mechanism(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td) / "run"
            run_dir.mkdir()
            # the audited live shape: synthesis ran OK, mechanism_map
            # exists, mechanism is null, zero candidates
            _write(run_dir, "envelope_SYNTHESIZE.json",
                   {"mechanism_map": {"raw_candidate": {"candidate_id":
                                                        "c1"}}})
            st = rs._mechanism_state({"status": "COMPLETE"}, run_dir,
                                     {"SYNTHESIZE": "OK"})
            self.assertEqual(st["state"], "NOT_ESTABLISHED")
            self.assertNotEqual(st["state"], "GENERATED")
            self.assertIsNone(st["mechanism"])
            self.assertIn("GENERATED requires a recorded mechanism",
                          st["reason"])

    def test_candidate_count_is_not_a_mechanism(self):
        """Art. XXVIII attack: a populated candidate list with no
        recorded mechanism still cannot read GENERATED."""
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td) / "run"
            run_dir.mkdir()
            _write(run_dir, "envelope_SYNTHESIZE.json",
                   {"mechanism_map": {}})
            _write(run_dir, "envelope_MECHANISM_SPACE.json",
                   {"candidates": [{"id": f"c{i}"} for i in range(3)]})
            st = rs._mechanism_state({"status": "COMPLETE"}, run_dir,
                                     {"SYNTHESIZE": "OK",
                                      "MECHANISM_SPACE": "OK"})
            self.assertEqual(st["state"], "NOT_ESTABLISHED")
            self.assertEqual(st["candidate_count"], 3)

    def test_positive_control_generated_with_mechanism(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td) / "run"
            run_dir.mkdir()
            _write(run_dir, "envelope_SYNTHESIZE.json",
                   {"mechanism_map": {
                       "mechanism": "staged lumen taper",
                       "intervention": "taper geometry",
                       "expected_effect": "conductance restored"}})
            st = rs._mechanism_state({"status": "COMPLETE"}, run_dir,
                                     {"SYNTHESIZE": "OK"})
            self.assertEqual(st["state"], "GENERATED")
            self.assertEqual(st["mechanism"], "staged lumen taper")


# ---------------------------------------------------------------------------
# 5 — capability gate precedes retrieval spend
# ---------------------------------------------------------------------------

class TestCapabilityGatePrecedesRetrieval(unittest.TestCase):
    """§O.8-5: on a degraded-only route, ZERO retrieval sources are
    queried — the gate records BLOCKED / CAPABILITY_INSUFFICIENT
    before the fan-out and the run stays resumable (Art. LXI)."""

    def test_gate_mirror_degraded_only(self):
        """The registry mirror, on the audited production shape:
        localqwen (CHEAP-only) is the only reachable rung."""
        from discovery_fabric.engine import llm_registry as reg
        with mock.patch.dict(os.environ,
                             {"LOCAL_QWEN_BASE_URL":
                              "http://127.0.0.1:18999/v1/chat/completions"}):
            rec = reg.strong_route_capability()
        self.assertEqual(rec["state"], "DEGRADED_ONLY")
        self.assertEqual(rec["strong_rungs"], [])
        self.assertTrue(rec["degraded_rungs"])
        self.assertTrue(all("STRONG" not in r["task_capabilities"]
                            for r in rec["degraded_rungs"]))

    def test_gate_mirror_positive_control(self):
        """Art. V positive control: one reachable STRONG rung → OK —
        the gate never fires when a capable route exists."""
        from discovery_fabric.engine import llm_registry as reg
        from discovery_fabric.engine import model_routing as mr_mod
        fake_matrix = [{"provider_id": "zai", "available": True,
                        "cost_policy_eligible": True}]
        fake_ladder = {"rungs": [
            {"provider": "zai", "model": "zai-org/GLM-5.3",
             "task_capabilities": ["STRONG", "FAST", "CHEAP"]}]}
        with mock.patch.object(reg, "availability_matrix",
                               return_value=fake_matrix), \
             mock.patch.object(reg._cost_policy, "active_policy",
                               return_value="UNRESTRICTED"), \
             mock.patch.object(mr_mod, "build_ladder",
                               return_value=fake_ladder):
            rec = reg.strong_route_capability()
        self.assertEqual(rec["state"], "OK")
        self.assertEqual(len(rec["strong_rungs"]), 1)

    def test_r455_capability_gate_precedes_retrieval(self):
        """The REAL conductor: stub RETRIEVE adapter whose execute() is
        the tripwire — if the fan-out ran at all, the test fails."""
        from discovery_fabric.engine import run as run_mod

        tripwire = {"retrieval_executed": False}

        class _TripwireAdapter:
            capability_id = "EVIDENCE_RETRIEVE"
            module_path = "stub"
            canonical_fn = "stub"

            def execute(self, env, run_ctx):
                tripwire["retrieval_executed"] = True
                return {"stub": True}

        problem = {"problem_id": "r455_cap",
                   "device": "test fixture",
                   "failure_mode": "none",
                   "failure": "fixture",
                   "user_need": "fixture"}

        with tempfile.TemporaryDirectory() as td:
            patched = dict(run_mod.ADAPTERS)
            patched["RETRIEVE"] = _TripwireAdapter()
            with mock.patch.dict(os.environ,
                                 {"LOCAL_QWEN_BASE_URL":
                                  "http://127.0.0.1:18999/v1/chat/"
                                  "completions"}), \
                 mock.patch.object(run_mod, "ADAPTERS", patched):
                engine = run_mod.EngineRun(
                    problem, td, with_package=True)
                manifest = engine.run()

            run_dir = Path(td)
            # zero retrieval source calls — the tripwire never fired
            self.assertFalse(
                tripwire["retrieval_executed"],
                "the retrieval fan-out executed on a degraded-only "
                "route — the pre-retrieval gate did not hold")
            # the typed refusal record
            gate = json.loads(
                (run_dir / "CAPABILITY_GATE.json").read_text())
            self.assertEqual(gate["status"], "BLOCKED")
            self.assertEqual(gate["blocked_class"], "CAPABILITY")
            self.assertTrue(gate["resumable"])
            self.assertEqual(
                gate["capability_route"]["state"], "DEGRADED_ONLY")
            # the stage ledger carries the refusal, not an envelope
            stage_log = engine.env.stage_log
            retrieve = next(e for e in stage_log
                            if e["stage"] == "RETRIEVE")
            self.assertEqual(retrieve["status"], "SKIPPED_ADMISSION")
            self.assertEqual(retrieve["skip_class"], "BLOCKED")
            self.assertIn("SYNTHESIS_CAPABILITY_INSUFFICIENT_PRE_"
                          "RETRIEVAL", retrieve["skip_reason"])
            freeze = next(e for e in stage_log if e["stage"] == "FREEZE")
            self.assertEqual(freeze["skip_class"], "NOT_REACHED")
            self.assertFalse((run_dir / "envelope_RETRIEVE.json").exists(),
                             "an admission refusal writes a ledger "
                             "line, never a full envelope (§3)")
            # the honest terminal: infrastructure class, never a verdict
            final = json.loads(
                (run_dir / "final_state.json").read_text())
            self.assertEqual(final["final_status"],
                             "RUN_BLOCKED_CAPABILITY")
            self.assertIsNotNone(final.get("capability_gate"))
            self.assertIn("never a scientific rejection",
                          final["reason"])
            # the expensive tail and the evolution layer spent NOTHING
            skipped = json.loads(
                (run_dir / "POST_RANK_PIPELINE_SKIPPED.json").read_text())
            self.assertEqual(
                skipped["skip_reason"],
                "SYNTHESIS_CAPABILITY_INSUFFICIENT_PRE_RETRIEVAL")
            lineage = json.loads(
                (run_dir / "INVENTION_LINEAGE.json").read_text())
            self.assertEqual(lineage["status"], "SKIPPED_ADMISSION")
            # the honest release record: no invention, no survivor
            release = json.loads(
                (run_dir / "DISCOVERY_RELEASE.json").read_text())
            self.assertEqual(release["status"], "DISCOVERY_INCOMPLETE")
            self.assertIsNone(release["invention_id"])

    def test_blocked_run_resumes_on_a_capable_route(self):
        """Art. LXI: the refusal is RESUMABLE — on a capable route the
        same run dir re-runs RETRIEVE (the gate is re-evaluated, never
        a sticky terminal)."""
        from discovery_fabric.engine import run as run_mod

        class _StubAdapter:
            capability_id = "EVIDENCE_RETRIEVE"
            module_path = "stub"
            canonical_fn = "stub"

            def __init__(self):
                self.calls = 0

            def execute(self, env, run_ctx):
                self.calls += 1
                return {"stub": True}

        problem = {"problem_id": "r455_resume",
                   "device": "test fixture",
                   "failure_mode": "none",
                   "failure": "fixture",
                   "user_need": "fixture"}
        stub = _StubAdapter()

        with tempfile.TemporaryDirectory() as td:
            patched = dict(run_mod.ADAPTERS)
            patched["RETRIEVE"] = stub
            with mock.patch.dict(os.environ,
                                 {"LOCAL_QWEN_BASE_URL":
                                  "http://127.0.0.1:18999/v1/chat/"
                                  "completions"}), \
                 mock.patch.object(run_mod, "ADAPTERS", patched):
                engine = run_mod.EngineRun(problem, td,
                                           with_package=False)
                engine.run()
            self.assertEqual(stub.calls, 0)
            # a capable route appears; the run resumes on the SAME dir
            with mock.patch.object(run_mod.EngineRun,
                                   "_pre_retrieval_capability_gate",
                                   return_value={"state": "OK",
                                                 "strong_rungs": [
                                                     {"provider": "zai"}],
                                                 "degraded_rungs": []}), \
                 mock.patch.object(run_mod, "ADAPTERS", patched):
                engine2 = run_mod.EngineRun(problem, td,
                                            with_package=False,
                                            resume=True)
                engine2.run()
            self.assertEqual(stub.calls, 1,
                             "a capable route must unblock the run "
                             "(Art. LXI resumability)")

if __name__ == "__main__":
    unittest.main()

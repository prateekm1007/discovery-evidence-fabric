"""tests/test_r514_starvation_gate.py — R514 (Art. LXXXIV) + registry
at-ceiling empty-content discipline.

ROUND CLAIM (falsifiable):
  G1. A run whose mechanism-space distinctness adjudication counts <2
      materially distinct mechanisms records COLLISION and ATTACK as
      SKIPPED_ADMISSION / MINIMUM_DIVERSITY (never executes them) and
      terminates MECHANISM_STARVED — attack/contradiction/experiment
      results are not reported as discovery evidence.
  G2. A run WITH >=2 distinct mechanisms (or with no distinctness
      adjudication at all — fail-open on unknown, Art. XXV) admits
      COLLISION/ATTACK exactly as before (no behavior change).
  T1. An EmptyContentWithFinish raised at the max token budget does NOT
      trigger an identical same-model retry (no mechanism to succeed
      differently); the cascade advances. The below-ceiling
      larger-budget rescue is preserved.

EVIDENCE BASIS (not generated for the tests):
  R513 durable envelopes: run A n_distinct=1 + retained=1 executed
  ATTACK (overall KILLED); run B n_distinct=0 + NO_CANDIDATES executed
  ATTACK (overall PASS) — both terminated INVENTION_REQUIRES_
  EXPERIMENT (the Art. LXXXIV violation this round closes).
  R513 durable model_routing ledger: 16 empty-content failures at
  max_tokens=2048 (atria/zai/xkiro), every one resolved via provider
  change, none via identical retry (25-245 s wasted each).

Hermetic (Art. IX): stub adapters + monkeypatched provider calls —
no network, no production state, deterministic.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.candidate import Candidate  # noqa: E402
from discovery_fabric.engine import stage_entry  # noqa: E402

PROBLEM = {
    "problem_id": "r514_starvation_test",
    "device": "test fixture device",
    "failure": "test fixture failure",
    "failure_mode": "none",
    "user_need": "fixture",
}


def _env_with_ms(n_distinct=None, retained=1):
    """Envelope with a BUILT mechanism space; distinctness present
    unless n_distinct is None (legacy/empty envelope shape)."""
    env = Candidate(problem=PROBLEM, problem_id="r514_starvation_test")
    ms = {"state": "BUILT", "n_candidates_retained": retained,
          "candidates": [{"candidate_id": "cand:test:1"}]}
    if n_distinct is not None:
        ms["distinctness"] = {
            "n_distinct": n_distinct,
            "instrument_version": "mechanism_distinctness/2.0.0"}
    env.mechanism_space = ms
    return env


class TestMinimumDiversityDoor(unittest.TestCase):
    """The justify door's MINIMUM_DIVERSITY rule (R514, Art. LXXXIV)."""

    def test_starved_single_distinct_skips_collision_and_attack(self):
        # R513 run A shape: retained=1, n_distinct=1.
        env = _env_with_ms(n_distinct=1, retained=1)
        for stage in ("COLLISION", "ATTACK"):
            block = stage_entry.justify(stage, env, {}, set())
            self.assertEqual(block["entry_status"], "SKIPPED", stage)
            self.assertEqual(block["prerequisite"],
                             "MINIMUM_DIVERSITY", stage)
            self.assertIn("MINIMUM_DIVERSITY",
                          block["skip_reason"], stage)
            self.assertIn("MECHANISM_STARVED",
                          block["skip_reason"], stage)
            self.assertIn("LXXXIV", block["skip_reason"], stage)
            self.assertEqual(
                block["prerequisite_evidence"]["n_distinct"], 1, stage)

    def test_starved_zero_distinct_skips_collision_and_attack(self):
        # R513 run B shape: retained=0 would trip retention first, so
        # use retained=1 + distinct=0 to isolate the diversity rule.
        env = _env_with_ms(n_distinct=0, retained=1)
        for stage in ("COLLISION", "ATTACK"):
            block = stage_entry.justify(stage, env, {}, set())
            self.assertEqual(block["entry_status"], "SKIPPED", stage)
            self.assertEqual(block["prerequisite"],
                             "MINIMUM_DIVERSITY", stage)

    def test_retention_rule_still_fires_first_on_empty(self):
        # Layering: zero retention + zero distinctness reports the
        # pre-existing NO_RETAINED_CANDIDATE reason (unchanged).
        env = _env_with_ms(n_distinct=0, retained=0)
        block = stage_entry.justify("ATTACK", env, {}, set())
        self.assertEqual(block["entry_status"], "SKIPPED")
        self.assertIn("NO_RETAINED_CANDIDATE", block["skip_reason"])

    def test_diverse_run_admits_collision_and_attack(self):
        env = _env_with_ms(n_distinct=2, retained=2)
        for stage in ("COLLISION", "ATTACK"):
            block = stage_entry.justify(stage, env, {}, set())
            self.assertEqual(block["entry_status"], "ALLOWED", stage)

    def test_absent_adjudication_fails_open(self):
        # Legacy/empty envelope (no distinctness record): the gate
        # does not fire on unknown (Art. XXV) — behavior unchanged.
        env = _env_with_ms(n_distinct=None, retained=1)
        for stage in ("COLLISION", "ATTACK"):
            block = stage_entry.justify(stage, env, {}, set())
            self.assertEqual(block["entry_status"], "ALLOWED", stage)

    def test_contradiction_deliberately_ungated(self):
        # CONTRADICTION stays admitted on starved runs: deterministic,
        # and it consumes evidence-verification issues independent of
        # candidates (R478 P0-2). An empty attack input yields an
        # (honest) empty queue, never fabricated results.
        env = _env_with_ms(n_distinct=0, retained=1)
        block = stage_entry.justify("CONTRADICTION", env, {}, set())
        self.assertEqual(block["entry_status"], "ALLOWED")

    def test_mechanism_starved_helper(self):
        self.assertIsNone(stage_entry.mechanism_starved(None))
        self.assertIsNone(
            stage_entry.mechanism_starved(_env_with_ms(None, 1)))
        self.assertIsNone(
            stage_entry.mechanism_starved(_env_with_ms(2, 2)))
        starved = stage_entry.mechanism_starved(_env_with_ms(1, 1))
        self.assertIsNotNone(starved)
        self.assertEqual(starved["n_distinct"], 1)

    def test_diversity_set_and_floor_pinned(self):
        self.assertEqual(stage_entry.MINIMUM_DIVERSITY_STAGES,
                         frozenset({"COLLISION", "ATTACK"}))
        self.assertEqual(stage_entry.MINIMUM_DISTINCT_MECHANISMS, 2)


def _stub_adapters(fired, n_distinct, retained=1):
    """Full 16-stage stub set. MECHANISM_SPACE installs the starved /
    diverse envelope; COLLISION/ATTACK are tripwires."""
    from discovery_fabric.engine.adapters import STAGE_ORDER

    def _stub(name):
        class _S:
            capability_id = name
            module_path = "stub"
            canonical_fn = "stub"

            def execute(self, env, run_ctx):
                return {"_engine_result": True, "apply_to": {}}
        _S.__name__ = name + "Stub"
        return _S()

    stubs = {s: _stub(s) for s in STAGE_ORDER}

    class _MS:
        capability_id = "MECHANISM_SPACE"
        module_path = "stub"
        canonical_fn = "stub"

        def execute(self, env, run_ctx):
            ms = {"state": "BUILT",
                  "n_candidates_retained": retained,
                  "candidates": [{"candidate_id": "cand:test:1"}]}
            if n_distinct is not None:
                ms["distinctness"] = {
                    "n_distinct": n_distinct,
                    "instrument_version":
                        "mechanism_distinctness/2.0.0"}
            return {"_engine_result": True,
                    "apply_to": {"mechanism_space": ms}}

    stubs["MECHANISM_SPACE"] = _MS()

    # VERIFY installs one DIRECT_SUPPORT item so MECHANISM_SPACE
    # itself passes the R399 W2.3 verified-evidence prerequisite
    # (rule 2) — otherwise the space never builds and the test
    # would exercise retention instead of diversity.
    class _Ver:
        capability_id = "EVIDENCE_VERIFY"
        module_path = "stub"
        canonical_fn = "stub"

        def execute(self, env, run_ctx):
            return {"_engine_result": True,
                    "apply_to": {"evidence_classification": {
                        "items": [{"source_id": "test:1",
                                   "classification":
                                       "DIRECT_SUPPORT"}],
                        "counts": {"DIRECT_SUPPORT": 1}}}}

    stubs["VERIFY"] = _Ver()

    for trip in ("COLLISION", "ATTACK"):
        class _Trip:
            capability_id = trip
            module_path = "stub"
            canonical_fn = "stub"

            def __init__(self, stage):
                self._stage = stage

            def execute(self, env, run_ctx):
                fired.append(self._stage)
                return {"_engine_result": True, "apply_to": {}}
        stubs[trip] = _Trip(trip)

    class _Adj:
        capability_id = "ADJUDICATION"
        module_path = "stub"
        canonical_fn = "stub"

        def execute(self, env, run_ctx):
            return {"_engine_result": True,
                    "apply_to": {
                        "adjudication": {},
                        "epistemic_state": {
                            "final_status":
                                "INVENTION_REQUIRES_EXPERIMENT"}}}

    stubs["ADJUDICATION"] = _Adj()
    return stubs


def _run_stubbed(n_distinct, td, evo_final="USE_MOCK_NONE"):
    """Drive the REAL conductor on stubs. The evolution layer is
    replaced by an explicit mock (these tests measure the stage
    chain + standard-path terminal, not evolution — R416 owns that
    layer): evo_final=None means evolution reports nothing;
    otherwise evolution reports the given final_state (the starved
    test uses a PROMOTING one to prove the terminal guard holds)."""
    from discovery_fabric.engine import run as run_mod
    fired = []
    stubs = _stub_adapters(fired, n_distinct)
    evo_ret = None if evo_final == "USE_MOCK_NONE" else {
        "final_state": evo_final}
    with mock.patch.object(run_mod, "ADAPTERS", stubs), \
         mock.patch.object(
             run_mod.EngineRun, "_pre_retrieval_capability_gate",
             lambda self: {"state": "OK"}), \
         mock.patch.object(run_mod.EngineRun, "_evolution_pipeline",
                           lambda self, run_ctx, final: evo_ret):
        engine = run_mod.EngineRun(PROBLEM, td, with_package=False)
        engine.run()
    return engine, fired


class TestStarvedConductorTerminal(unittest.TestCase):
    """The REAL conductor on a starved envelope (R455 stub harness)."""

    def test_starved_run_skips_attack_and_terminal_starved(self):
        # Evolution is mocked PROMOTING (INVENTION_REQUIRES_EXPERIMENT):
        # the terminal must STAY starved — without the R514 guard this
        # test fails (Art. XXX adversarial form).
        with tempfile.TemporaryDirectory() as td:
            engine, fired = _run_stubbed(
                1, td,
                evo_final={"final_status": "INVENTION_REQUIRES_EXPERIMENT",
                           "reason": "mock promoting evolution"})
            self.assertEqual(
                fired, [],
                "COLLISION/ATTACK executed on a starved run "
                f"(n_distinct=1): {fired}")
            log = engine.env.stage_log
            for stage in ("COLLISION", "ATTACK"):
                entry = next(e for e in log if e["stage"] == stage)
                self.assertEqual(entry["status"],
                                 "SKIPPED_ADMISSION", stage)
                self.assertIn("MINIMUM_DIVERSITY",
                              entry["skip_reason"], stage)
            final = json.loads(
                (Path(td) / "final_state.json").read_text())
            self.assertEqual(final["final_status"],
                             "MECHANISM_STARVED")
            self.assertIn("LXXXIV", final["reason"])

    def test_diverse_run_executes_attack_and_keeps_terminal(self):
        with tempfile.TemporaryDirectory() as td:
            engine, fired = _run_stubbed(2, td)
            self.assertIn("ATTACK", fired)
            self.assertIn("COLLISION", fired)
            final = json.loads(
                (Path(td) / "final_state.json").read_text())
            self.assertEqual(final["final_status"],
                             "INVENTION_REQUIRES_EXPERIMENT")


class TestEmptyContentAtCeiling(unittest.TestCase):
    """Registry: at-ceiling empty content advances the cascade."""

    def test_at_ceiling_empty_advances_without_identical_retry(self):
        """max_tokens already at the reasoning ceiling: ONE attempt,
        CALL_FAILED with the typed route (no 2nd/3rd identical burn).
        max_retries=2 default would have meant 3 identical calls."""
        calls = []
        import unittest.mock as um
        with um.patch.dict("os.environ",
                           {"NVIDIA_API_KEY": "fake-key-hermetic-test"}):
            import discovery_fabric.engine.llm_registry as reg
            import discovery_fabric.engine.model_routing as mr_mod
            import discovery_fabric.engine.runtime_admission as ra_mod
            with um.patch.object(reg, "_call_openai_flavor") as fc, \
                 um.patch.object(mr_mod, "build_ladder") as bl, \
                 um.patch.object(reg, "availability_matrix") as am, \
                 um.patch.object(reg._cost_policy,
                                 "active_policy") as ap, \
                 um.patch.object(ra_mod, "requires_probe") as rp, \
                 um.patch.object(ra_mod, "runtime_admission") as ra:
                def _empty(spec, messages, timeout, max_tokens,
                           model_override=None):
                    calls.append({"timeout": timeout,
                                  "max_tokens": max_tokens})
                    raise reg.EmptyContentWithFinish(
                        "nvidia returned empty content "
                        "(finish_reason=length, max_tokens=2048)",
                        finish_reason="length")
                fc.side_effect = _empty
                bl.return_value = {
                    "rungs": [{"provider": "nvidia",
                               "model": "test/test-model",
                               "band": "PRIMARY"}],
                    "provenance": {"source": "TEST"}}
                am.return_value = [{"provider_id": "nvidia",
                                    "available": True,
                                    "cost_policy_eligible": True}]
                ap.return_value = "UNRESTRICTED"
                rp.return_value = False
                ra.return_value = (True, "TEST_ADMITTED",
                                   {"state": "PROBE_OK"})
                res = reg.generate(
                    "prompt",
                    policy=reg.SelectionPolicy(
                        preferred_providers=["nvidia"],
                        purpose="general"),
                    max_tokens=2048, max_retries=2)
        self.assertFalse(res.ok)
        self.assertEqual(len(calls), 1,
                         f"identical same-model retry fired at ceiling: "
                         f"{len(calls)} calls")
        # the hop record is the decision footprint (retry_notes ride
        # the success path only): one attempt, MODEL_FAILURE class.
        hop = (res.route or [{}])[0]
        self.assertEqual(hop.get("attempts"), 1)
        self.assertEqual(hop.get("failure_type"), "MODEL_FAILURE")

    def test_below_ceiling_empty_keeps_larger_budget_rescue(self):
        """The designed rescue is preserved: below-ceiling empty grows
        the budget and retries the same rung."""
        calls = []
        import unittest.mock as um
        with um.patch.dict("os.environ",
                           {"NVIDIA_API_KEY": "fake-key-hermetic-test"}):
            import discovery_fabric.engine.llm_registry as reg
            import discovery_fabric.engine.model_routing as mr_mod
            import discovery_fabric.engine.runtime_admission as ra_mod
            with um.patch.object(reg, "_call_openai_flavor") as fc, \
                 um.patch.object(mr_mod, "build_ladder") as bl, \
                 um.patch.object(reg, "availability_matrix") as am, \
                 um.patch.object(reg._cost_policy,
                                 "active_policy") as ap, \
                 um.patch.object(ra_mod, "requires_probe") as rp, \
                 um.patch.object(ra_mod, "runtime_admission") as ra:
                def _empty_once(spec, messages, timeout, max_tokens,
                                model_override=None):
                    calls.append({"max_tokens": max_tokens})
                    if len(calls) == 1:
                        raise reg.EmptyContentWithFinish(
                            "simulated empty", finish_reason="length")
                    return "FIELD: ok"
                fc.side_effect = _empty_once
                bl.return_value = {
                    "rungs": [{"provider": "nvidia",
                               "model": "test/test-model",
                               "band": "PRIMARY"}],
                    "provenance": {"source": "TEST"}}
                am.return_value = [{"provider_id": "nvidia",
                                    "available": True,
                                    "cost_policy_eligible": True}]
                ap.return_value = "UNRESTRICTED"
                rp.return_value = False
                ra.return_value = (True, "TEST_ADMITTED",
                                   {"state": "PROBE_OK"})
                res = reg.generate(
                    "prompt",
                    policy=reg.SelectionPolicy(
                        preferred_providers=["nvidia"],
                        purpose="general"),
                    max_tokens=512, max_retries=2)
        self.assertTrue(res.ok, f"expected rescue OK: {res.error}")
        self.assertEqual(len(calls), 2)
        self.assertGreater(calls[1]["max_tokens"],
                           calls[0]["max_tokens"])


if __name__ == "__main__":
    unittest.main()

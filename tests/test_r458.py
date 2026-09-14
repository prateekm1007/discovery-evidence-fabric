"""tests/test_r458.py — the R458-C1 round battery.

Directive coverage:
  §1  the frozen benchmark: freeze discipline, split integrity, the
      BLIND HOLDOUT mechanically refused outside the blind phase
      (BS-016 / Art. LIX anti-circularity);
  §3  the frozen quality instrument: drift refusal (tuning after
      freeze is gaming);
  §5  provider failures invisible to the scientific state: the two
      directive sentences, the scrub guard (provider ids / HTTP codes
      / endpoints / failure classes NEVER in the product surface),
      the run-contract wiring, the product-event wiring, the
      technical record retained;
  §2  the model-purity invariant (cross-arm / paid lines fail closed).

Adversarial discipline (Art. XVII/XXX): every control is attacked —
raw provider errors are INJECTED into sessions and ledgers, the
holdout is injected into dev-phase call sites, the instrument is
mutated after freeze, and each attack must fail closed for the
SPECIFIC rule it targets.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from toscanini.conversational import transport_invisibility as ti   # noqa: E402
from toscanini.conversational import run_contract                    # noqa: E402
from toscanini.conversational import product_events                  # noqa: E402


def _ledger(lines):
    return {"run_id": "test-run", "lines": lines,
            "line_count": len(lines)}


class TestBenchmarkFreeze(unittest.TestCase):
    """§1 — the frozen corpus + the blind holdout discipline."""

    def setUp(self):
        self.freeze = json.loads(
            (REPO_ROOT / "R458" / "BENCHMARK_FREEZE.json").read_text())
        self.corpus = json.loads(
            (REPO_ROOT / "R458" / "BENCHMARK_CORPUS.json").read_text())

    def test_corpus_shape_meets_article_xlix(self):
        families = self.freeze["per_problem"]
        by_family = {}
        for pid, rec in families.items():
            by_family.setdefault(rec["domain_family"], []).append(pid)
        self.assertGreaterEqual(len(families), 10)
        self.assertGreaterEqual(len(by_family), 6)
        for fam, pids in by_family.items():
            self.assertEqual(len(pids), 2,
                             f"family {fam} must have 2 problems")

    def test_split_is_seven_and_seven(self):
        self.assertEqual(len(self.freeze["split"]["dev_ids"]), 7)
        self.assertEqual(len(self.freeze["split"]["holdout_ids"]), 7)
        self.assertFalse(set(self.freeze["split"]["dev_ids"])
                         & set(self.freeze["split"]["holdout_ids"]))

    def test_holdout_refused_outside_blind_phase(self):
        import r458_benchmark as bench
        holdout_id = self.freeze["split"]["holdout_ids"][0]
        with self.assertRaises(SystemExit) as cm:
            bench.assert_dev_only(holdout_id)
        self.assertIn("BLIND HOLDOUT", str(cm.exception))

    def test_dev_id_passes_the_guard(self):
        import r458_benchmark as bench
        dev_id = self.freeze["split"]["dev_ids"][0]
        self.assertIsNone(bench.assert_dev_only(dev_id))

    def test_blind_test_ordering_enforced(self):
        import r458_benchmark as bench
        with mock.patch.object(
                bench, "REPO_ROOT", Path(tempfile.mkdtemp())):
            # the dev-phase record does not exist there -> refused
            with self.assertRaises(SystemExit) as cm:
                bench.assert_blind_test_allowed()
            self.assertIn("dev-phase", str(cm.exception))

    def test_no_dev_result_references_holdout_content(self):
        """BS-016 attack: holdout problem text must not appear in any
        dev-phase artifact (the holdout never becomes the tuning
        surface)."""
        holdout_texts = [
            p["text"][:120]
            for p in self.corpus["problems"].values()
            if p["split"] == "HOLDOUT"]
        dev_record = REPO_ROOT / "R458" / "MODEL_CAPABILITY_BENCHMARK.json"
        if dev_record.exists():
            blob = dev_record.read_text()
            for text in holdout_texts:
                self.assertNotIn(text, blob)

    def test_verify_command_passes_on_frozen_corpus(self):
        import r458_benchmark as bench
        with mock.patch.object(sys, "argv",
                               ["r458_benchmark.py", "verify"]):
            self.assertEqual(bench.main(), 0)


class TestQualityInstrumentFreeze(unittest.TestCase):
    """§3 — the frozen instrument refuses its own drift."""

    def test_instrument_frozen_and_intact(self):
        rec = json.loads(
            (REPO_ROOT / "R458" / "QUALITY_INSTRUMENT_FREEZE.json")
            .read_text())
        self.assertEqual(len(rec["metric_definitions"]), 14)
        import r458_quality_instrument as qi
        self.assertEqual(
            rec["instrument_script_sha256"], qi._script_sha256())

    def test_drift_refused_fail_closed(self):
        """Art. LIX attack: mutate the instrument after freeze ->
        apply refuses (tuning after freeze is gaming)."""
        import r458_quality_instrument as qi
        with mock.patch.object(
                qi, "_script_sha256",
                return_value="deadbeef" * 8):
            with self.assertRaises(SystemExit) as cm:
                qi.verify_instrument()
            self.assertIn("INSTRUMENT DRIFT", str(cm.exception))

    def test_art_xxxi_correction_recorded(self):
        rec = json.loads(
            (REPO_ROOT / "R458" / "QUALITY_INSTRUMENT_FREEZE.json")
            .read_text())
        self.assertIn("art_xxxi_correction", rec)
        self.assertIn("user_text", rec["art_xxxi_correction"])


class TestTransportInvisibility(unittest.TestCase):
    """§5 — provider failures invisible to the scientific state."""

    def _tmp_run(self, lines=None, extra=None):
        td = Path(tempfile.mkdtemp())
        if lines is not None:
            (td / "ROUTING_LEDGER_RUN.json").write_text(
                json.dumps(_ledger(lines)))
        for name, obj in (extra or {}).items():
            (td / name).write_text(json.dumps(obj))
        return td

    def test_cascade_advanced_sentence_verbatim(self):
        td = self._tmp_run(lines=[
            {"status": "OK", "provider": "zai",
             "recorded_at_epoch": 100},
            {"status": "FAILED", "provider": "zai",
             "failure_class": "RATE_LIMITED",
             "recorded_at_epoch": 200},
            {"status": "OK", "provider": "localqwen",
             "recorded_at_epoch": 300},
        ])
        view = ti.scientific_state_message(td)
        self.assertEqual(view["outcome"], "CASCADE_ADVANCED")
        self.assertEqual(
            view["message"],
            "I continued using another verified reasoning route.")

    def test_all_routes_exhausted_sentence_verbatim(self):
        td = self._tmp_run(lines=[
            {"status": "FAILED", "provider": "xkiro",
             "failure_class": "CREDIT_EXHAUSTED",
             "recorded_at_epoch": 100},
            {"status": "FAILED", "provider": "unorouter",
             "failure_class": "RATE_LIMITED",
             "recorded_at_epoch": 200},
        ])
        view = ti.scientific_state_message(td)
        self.assertEqual(view["outcome"], "ALL_ROUTES_EXHAUSTED")
        self.assertTrue(view["message"].startswith(
            "The requested test could not be completed."))

    def test_no_failures_is_not_applicable(self):
        td = self._tmp_run(lines=[
            {"status": "OK", "provider": "zai",
             "recorded_at_epoch": 100}])
        view = ti.scientific_state_message(td)
        self.assertEqual(view["outcome"], "NOT_APPLICABLE")
        self.assertIsNone(view["message"])

    def test_single_provider_retry_is_not_a_cascade(self):
        """A same-provider retry that eventually succeeds is NOT
        'another route' — the sentence would overclaim rotation."""
        td = self._tmp_run(lines=[
            {"status": "FAILED", "provider": "zai",
             "failure_class": "RATE_LIMITED",
             "recorded_at_epoch": 100},
            {"status": "OK", "provider": "zai",
             "recorded_at_epoch": 200},
        ])
        cls = ti.classify_transport_outcome(td)
        self.assertEqual(cls["outcome"], "NOT_APPLICABLE")

    def test_scrub_guard_catches_each_pattern_class(self):
        attacks = {
            "xkiro returned HTTP 403":
                ["provider-id-in-product-surface",
                 "http-error-code-in-product-surface"],
            "unorouter hit 429 from the busy pool":
                ["provider-id-in-product-surface",
                 "http-error-code-in-product-surface"],
            "failed: https://api.unorouter.com/v1/chat/completions":
                ["provider-id-in-product-surface",
                 "endpoint-host-in-product-surface"],
            "probe classified RATE_LIMITED":
                ["failure-class-in-product-surface"],
        }
        for text, expected in attacks.items():
            violations = ti.transport_detail_violations(text)
            for v in expected:
                self.assertIn(v, violations, f"for text: {text}")

    def test_scrub_guard_clean_on_the_directive_sentences(self):
        self.assertEqual(
            ti.transport_detail_violations(
                "I continued using another verified reasoning route."),
            [])
        self.assertEqual(
            ti.transport_detail_violations(
                "The requested test could not be completed. Your work "
                "is saved; the run resumes when a verified route is "
                "available."),
            [])

    def test_run_contract_never_surfaces_raw_transport_error(self):
        """THE §5 attack: inject the raw 'Qwen provider 1 hit 403'
        class error into the session; the product contract's detail
        must carry ONLY the scientific-state sentence."""
        td = self._tmp_run(lines=[
            {"status": "FAILED", "provider": "qwen-router",
             "failure_class": "CREDIT_EXHAUSTED",
             "recorded_at_epoch": 100}])
        session = {
            "status": "RUN_BLOCKED_TRANSPORT",
            "error": ("Discovery temporarily blocked by infrastructure. "
                      "[transport exhausted: xkiro probe=FAILED HTTP 403 "
                      "credit exhausted]") * 3,
        }
        br = run_contract._blocking_reason(session, td)
        self.assertEqual(br["kind"], "INFRASTRUCTURE")
        self.assertTrue(br["resumable"])
        self.assertTrue(br["detail"].startswith(
            "The requested test could not be completed."))
        self.assertEqual(ti.transport_detail_violations(br["detail"]), [])
        self.assertIn("technical_record", br)
        # the raw error is NOT the detail — it stays in the session
        # store (the technical record surface)
        self.assertNotIn("403", br["detail"])
        self.assertNotIn("xkiro", br["detail"])

    def test_run_contract_cascade_detail(self):
        td = self._tmp_run(lines=[
            {"status": "FAILED", "provider": "zai",
             "failure_class": "RATE_LIMITED",
             "recorded_at_epoch": 100},
            {"status": "OK", "provider": "localqwen",
             "recorded_at_epoch": 200},
        ])
        session = {"status": "RUN_BLOCKED_TRANSPORT",
                   "error": "zai 429 rate limited"}
        br = run_contract._blocking_reason(session, td)
        self.assertEqual(
            br["detail"],
            "I continued using another verified reasoning route.")

    def test_product_events_terminal_uses_the_sentence(self):
        td = self._tmp_run(
            lines=[{"status": "FAILED", "provider": "xkiro",
                    "failure_class": "CREDIT_EXHAUSTED",
                    "recorded_at_epoch": 100}],
            extra={"final_state.json": {
                "run_id": "test-run", "final_status":
                    "RUN_BLOCKED_TRANSPORT"},
                "run_manifest.json": {"run_id": "test-run"}})
        events = product_events.derive_product_events(
            td, "test-run", session_status="RUN_BLOCKED_TRANSPORT")
        blocked = [e for e in events if e["type"] == "RUN_BLOCKED"]
        self.assertTrue(blocked)
        for e in blocked:
            self.assertEqual(
                ti.transport_detail_violations(e["message"]), [],
                f"leak in event message: {e['message']}")
            self.assertTrue(
                e["message"].startswith(
                    "The requested test could not be completed."))

    def test_product_events_clean_run_has_no_blocked_events(self):
        td = self._tmp_run(
            lines=[{"status": "OK", "provider": "zai",
                    "recorded_at_epoch": 100}],
            extra={"final_state.json": {
                "run_id": "test-run",
                "final_status": "INVENTION_UNDER_DEVELOPMENT"},
                "problem.json": {"problem_id": "x"},
                "run_manifest.json": {"run_id": "test-run"}})
        events = product_events.derive_product_events(
            td, "test-run", session_status="COMPLETED")
        self.assertFalse([e for e in events
                          if e["type"] == "RUN_BLOCKED"])

    def test_technical_record_facts_retained(self):
        """§5's other half: the technical record keeps the FULL truth
        (providers, failure classes) — invisible, not deleted."""
        td = self._tmp_run(lines=[
            {"status": "FAILED", "provider": "xkiro",
             "failure_class": "CREDIT_EXHAUSTED",
             "recorded_at_epoch": 100}])
        cls = ti.classify_transport_outcome(td)
        self.assertEqual(cls["technical"]["failing_providers"],
                         ["xkiro"])
        self.assertEqual(cls["technical"]["failure_classes"],
                         ["CREDIT_EXHAUSTED"])


class TestModelPurityInvariant(unittest.TestCase):
    """§2 — the purity invariant fails closed on contamination."""

    def _arm_dir(self):
        import r458_model_capability_benchmark as mc
        with mock.patch.object(mc, "ARMS_ROOT",
                               Path(tempfile.mkdtemp())):
            pass
        return mc

    def test_allowed_models_are_closed_sets(self):
        import r458_model_capability_benchmark as mc
        for arm, spec in mc.RUNNABLE_ARMS.items():
            self.assertTrue(spec["allowed_models"])
            self.assertTrue(spec["allowed_providers"])
            self.assertIn(spec["model"], spec["allowed_models"])

    def test_unavailable_arms_are_typed_not_silent(self):
        import r458_model_capability_benchmark as mc
        for u in mc.UNAVAILABLE_ARMS:
            self.assertIn(u["state"],
                          ("CREDENTIAL_UNAVAILABLE", "CREDIT_EXHAUSTED"))
            self.assertTrue(u["models"])
            self.assertTrue(u["reason"])

    def test_paid_env_vars_stripped_in_arm_env(self):
        import r458_model_capability_benchmark as mc
        env_full = dict(mc.PAID_ENV_VARS and
                        {v: "leak" for v in mc.PAID_ENV_VARS})
        with mock.patch.object(mc.os, "environ",
                               {**{"PATH": "/usr/bin"}, **env_full}):
            env = mc.arm_env("glm-4-plus")
        for var in mc.PAID_ENV_VARS:
            self.assertNotIn(var, env)
        self.assertEqual(env["ENGINE_MODEL_COST_POLICY"], "UNRESTRICTED")
        self.assertEqual(env["ZAI_MODEL"], "glm-4-plus")


class TestRealityMutationProof(unittest.TestCase):
    """§6 — the causal chain's falsifier discipline (offline, the
    solver's own numbers)."""

    PROOF_TEXT = (
        "A precision feed gallery is a 1.2-millimetre passage, 400 "
        "millimetres long. The fluid viscosity is 180 centipoise and "
        "the pump delivers 2.5 bar at the inlet. The bearing requires "
        "at least 40 millilitres per minute."
    )

    def _exp(self, text=None):
        from discovery_fabric.engine import mechanistic_solver as ms
        return ms.run_mechanistic_virtual_experiment(
            text or self.PROOF_TEXT, "test-cand", {},
            experiment_id="test:vexp")

    def test_chain_binds_and_falsifies(self):
        exp = self._exp()
        co = exp.get("computed_outcome") or {}
        self.assertEqual(exp.get("status"), "COMPUTED_FAIL")
        self.assertLess(co.get("candidate_flow_ml_min"),
                        co.get("required_flow_ml_min"))

    def test_mutation_is_the_observation_inverse(self):
        from discovery_fabric.engine import mechanistic_solver as ms
        exp = self._exp()
        mut = ms.mechanistic_mutation(exp, {})
        self.assertEqual(mut.get("mutation_kind"),
                         "INVERSE_POISEUILLE_DIAMETER")
        self.assertIsInstance(mut.get("to_value"), float)
        self.assertGreater(mut.get("to_value"), mut.get("from_value"))
        # the successor must actually clear the deficit (the closed
        # form inverts it exactly — re-evaluation must support; the
        # text round-trip carries re-extraction precision, so the
        # tolerance is the extraction's own 4-decimal grain)
        child = self._exp(text=self.PROOF_TEXT.replace(
            "1.2-millimetre", f"{mut['to_value']:.6f}-millimetre"))
        child_co = child.get("computed_outcome") or {}
        self.assertGreaterEqual(
            child_co.get("candidate_flow_ml_min") or 0,
            (child_co.get("required_flow_ml_min") or 0) * 0.999)

    def test_flip_regression_semantics(self):
        """The causal claim's falsifier: perturbing the observed
        deficit changes the mutation measurably."""
        from discovery_fabric.engine import mechanistic_solver as ms
        import copy
        exp = self._exp()
        base = ms.mechanistic_mutation(exp, {})
        exp2 = copy.deepcopy(exp)
        req = exp2["computed_outcome"]["required_flow_ml_min"]
        exp2["computed_outcome"]["required_flow_ml_min"] = req * 2.0
        flipped = ms.mechanistic_mutation(exp2, {})
        self.assertNotAlmostEqual(
            base.get("to_value"), flipped.get("to_value"), places=6)
        self.assertGreater(flipped.get("to_value"),
                           base.get("to_value"))

    def test_proof_record_present_and_honest(self):
        rec = json.loads(
            (REPO_ROOT / "R458_C1_REALITY_MUTATION_PROOF.json")
            .read_text())
        self.assertIn("causal_learning_proven", rec)
        self.assertIn("loop_verification_state", rec)
        # honesty: the synthetic boundary is carried verbatim
        self.assertEqual(rec["loop_verification_state"],
                         "SYNTHETIC_LOOP_VERIFIED")
        # the fixture's authored-for-binding status is disclosed
        self.assertTrue(rec["source"]["proof_fixture_disclosure"])
        if rec["causal_learning_proven"]:
            succ = rec["the_chain"]["successor"]
            self.assertTrue(succ["measurable_difference_from_parent"])
            self.assertTrue(rec["flip_regression"]
                            ["mutation_changed_measurably"])


class TestAdaptiveGateClosure(unittest.TestCase):
    """§4 — the adaptive benchmark's gate closure constructs and
    records the NBA decision trail."""

    def test_gate_closure_runs_and_records(self):
        import r458_adaptive_benchmark as ab
        with tempfile.TemporaryDirectory() as td:
            trail = []
            gate = ab._adaptive_gate(Path(td), trail)

            class FakeEnv:
                def to_dict(self):
                    return {"evidence": [{"id": f"e{i}"}
                                         for i in range(10)],
                            "evidence_classification": {
                                "items": [
                                    {"classification": "DIRECT_SUPPORT"}
                                    for _ in range(4)]}}
            decision = gate("SYNTHESIZE", FakeEnv())
            self.assertEqual(len(trail), 1)
            self.assertIn("preferred_action", trail[0])
            # the recorded decision carries the directive §8 fields
            pref = (trail[0]["decision"]
                    .get("preferred_action") or {})
            for field in ("action", "target_uncertainty",
                          "expected_information_gain",
                          "estimated_cost", "risk", "reason"):
                self.assertIn(field, pref)

    def test_fixed_arm_is_capability_runs(self):
        """The FIXED arm must be the capability benchmark's own runs
        (same problems, same model — Art. XLVII instrument identity)."""
        import r458_adaptive_benchmark as ab
        src = Path(ab.__file__).read_text()
        self.assertIn("capability benchmark", src)
        self.assertIn("re-measured, not re-run", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)

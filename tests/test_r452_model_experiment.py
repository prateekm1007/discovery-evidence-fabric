"""tests/test_r452_model_experiment.py — the adversarial battery for
the A3 controlled stronger-model experiment machinery (R452).

Attacks the machine, not the narrative (Art. XVI/XVII):
  - arm environment hygiene: the zero-cost contract is STRUCTURAL
    (paid keys stripped in BOTH arms) and the arms differ ONLY in the
    served model (same policy, same provider slot, pinned base URLs);
  - the purity invariant catches a fabricated PAID_API line AND a
    cross-arm model line (the adversarial cases — the invariant must
    fire, not pass);
  - the domain-correctness extractor detects the E10 defect class
    (ml_data on a physical problem);
  - the engineering-reachability extractor types NOT_REACHED when no
    CAD ledger exists (never a silent zero, Art. XXV);
  - the dimension rollup refuses to manufacture means from missing
    values (UNKNOWN, not 0.0);
  - the run-identity discipline: experiment run ids are FRESH (never
    collide with the R452 assay run ids — run-ID laundering guard).
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import r452_model_experiment as mx  # noqa: E402
import r452_assay as assay  # noqa: E402


class TestArmEnvironmentHygiene(unittest.TestCase):
    """The zero-cost contract is structural; the model is the only
    variable between the arms."""

    def setUp(self):
        self._saved = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._saved)

    def test_both_arms_strip_every_paid_credential(self):
        for arm in mx.ARMS:
            os.environ["OPENROUTER_API_KEY"] = "paid-key-present"
            os.environ["OPENAI_API_KEY"] = "paid-key-present"
            os.environ["TOKEN_ROUTER_API_KEY"] = "paid-key-present"
            os.environ["ZAI_API_KEY"] = "paid-key-present"
            env = mx.arm_env(arm)
            for k in list(mx.PAID_ENV_VARS) + ["ZAI_API_KEY",
                                               "ZAI_MODEL"]:
                self.assertNotIn(
                    k, env,
                    f"{arm}: credential {k} survived arm_env — the "
                    "zero-cost contract must be structural")

    def test_both_arms_run_the_deployed_default_policy(self):
        for arm in mx.ARMS:
            env = mx.arm_env(arm)
            self.assertEqual(
                env["ENGINE_MODEL_COST_POLICY"], "ZERO_PAID_COST",
                f"{arm}: the experiment must run the DEPLOYED default "
                "policy — a policy difference would confound the A/B")

    def test_arms_differ_only_in_the_served_model(self):
        e1 = mx.arm_env("arm1-qwen3-1.7b")
        e2 = mx.arm_env("arm2-qwen3-4b")
        self.assertEqual(e1["ENGINE_MODEL_COST_POLICY"],
                         e2["ENGINE_MODEL_COST_POLICY"])
        self.assertIn("8790", e1["LOCAL_QWEN_BASE_URL"])
        self.assertIn("8791", e2["LOCAL_QWEN_BASE_URL"])
        self.assertNotIn("LOCALQWEN_MODEL", e1)   # spec default 1.7b
        self.assertEqual(e2["LOCALQWEN_MODEL"], "qwen3-4b")

    def test_arm2_pins_the_4b_server_exclusively(self):
        env = mx.arm_env("arm2-qwen3-4b")
        self.assertEqual(env["LOCAL_QWEN_BASE_URL"],
                         "http://127.0.0.1:8791/v1/chat/completions",
                         "arm2 must point ONLY at the 4B server — a "
                         "1.7B fallback would mix models inside one arm "
                         "(Art. XLVII)")


class TestPurityInvariant(unittest.TestCase):
    """The invariant must FIRE on bad lines — never pass them."""

    def _with_ledger(self, arm, extra_line):
        ledger = (mx.REPO_ROOT / "ENGINE_RUNS" /
                  "model_routing" / "ledger.jsonl")
        ledger.parent.mkdir(parents=True, exist_ok=True)
        original = ledger.read_text() if ledger.exists() else ""
        arm_dir = mx._arm_dir(arm, "A")
        vrec = arm_dir / "ZERO_COST_INVARIANT.json"
        had_vrec = vrec.exists()
        saved_vrec = vrec.read_text() if had_vrec else None
        try:
            ledger.write_text(original + json.dumps(extra_line) + "\n")
            ok = mx._verify_zero_cost_invariant(arm, "A")
            data = json.loads(vrec.read_text())
            return ok, data
        finally:
            ledger.write_text(original)
            if had_vrec:
                vrec.write_text(saved_vrec)
            else:
                vrec.unlink(missing_ok=True)
                try:
                    arm_dir.rmdir()
                except OSError:
                    pass

    def test_fabricated_paid_line_fails_closed(self):
        ok, data = self._with_ledger("arm2-qwen3-4b", {
            "run_id": "r452mx2-A: fabricated",
            "provider": "openrouter",
            "model": "gpt-4o",
            "cost_class": "PAID_API",
            "ok": True,
        })
        self.assertFalse(
            ok, "a PAID_API line MUST fail the invariant closed")
        self.assertEqual(data["violation_lines"], 1)
        self.assertEqual(data["violations"][0]["cost_class"], "PAID_API")

    def test_cross_arm_model_line_fails_closed(self):
        """A 1.7B line inside arm2's run would mix models inside the
        arm — the model-purity invariant must fire (Art. XLVII)."""
        ok, data = self._with_ledger("arm2-qwen3-4b", {
            "run_id": "r452mx2-A: cross-contamination",
            "provider": "localqwen",
            "model": "qwen3-1.7b",
            "cost_class": "ZERO_PAID_COST_SELF_HOSTED",
            "ok": True,
        })
        self.assertFalse(
            ok, "a cross-arm model line MUST fail the purity invariant")
        self.assertEqual(data["violations"][0]["model"], "qwen3-1.7b")

    def test_allowed_lines_pass(self):
        ok, data = self._with_ledger("arm1-qwen3-1.7b", {
            "run_id": "r452mx1-A: allowed",
            "provider": "localqwen",
            "model": "qwen3-1.7b",
            "cost_class": "ZERO_PAID_COST_SELF_HOSTED",
            "ok": True,
        })
        self.assertTrue(ok)
        self.assertEqual(data["violation_lines"], 0)


class TestExtractors(unittest.TestCase):

    def test_ml_data_misroute_detected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "envelope_CLASSIFY.json").write_text(json.dumps({
                "physics": {"pre_requirements": {
                    "domain": "ml_data",
                    "domain_detection": {"domain": "ml_data"}}}}))
            out = mx._domain_correctness(d, "medical_device")
            self.assertTrue(
                out["ml_data_misroute"],
                "the E10 defect class (ml_data on a physical problem) "
                "must be detected")

    def test_physical_domain_not_flagged(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "envelope_CLASSIFY.json").write_text(json.dumps({
                "physics": {"pre_requirements": {
                    "domain": "fluidics_hydraulic"}}}))
            out = mx._domain_correctness(d, "energy_industrial")
            self.assertFalse(out["ml_data_misroute"])
            self.assertEqual(out["detected_domain"], "fluidics_hydraulic")

    def test_no_cad_ledger_is_typed_not_reached(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            out = mx._engineering_reachability(Path(td))
            self.assertFalse(out["reached"])
            self.assertIn("NOT_REACHED", out["reason"])

    def test_cad_ledger_with_step_is_reached(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "CAD_PIPELINE_LEDGER_gen-001.json").write_text(
                json.dumps({"status": "OK", "outcome": "COMPLETE"}))
            (d / "three_d" / "gen-001").mkdir(parents=True)
            (d / "three_d" / "gen-001" / "assembly.step").write_text("x")
            (d / "three_d" / "gen-001" / "body.stl").write_text("x")
            out = mx._engineering_reachability(d)
            self.assertTrue(out["reached"])
            self.assertTrue(out["step_exported"])
            self.assertTrue(out["stl_exported"])

    def test_rollup_manufactures_no_mean_from_missing(self):
        roll = mx._arm_dimension_rollup([
            {"instrument": {},
             "attack_execution": {}, "parameter_sourcing": {},
             "engineering_reachability": {}, "transport": {}}])
        self.assertEqual(
            roll["1_evidence_grounding"][
                "mean_evidence_relevance_rate"],
            "UNKNOWN_NO_NUMERIC_VALUES",
            "missing measurements stay UNKNOWN — never a silent 0.0 "
            "(Art. XXV)")


class TestRunIdentityDiscipline(unittest.TestCase):

    def test_experiment_run_ids_are_fresh_vs_assay(self):
        """Run-ID laundering guard: the experiment arms' run ids can
        never collide with the R452 assay runs' ids (a reused id would
        launder the assay's artifacts into the experiment)."""
        assay_ids = {assay.ALL_CASES[c]["run_id"]
                     for c in ("A", "B", "C", "A2")}
        for arm, spec in mx.ARMS.items():
            for case in ("A", "B", "C"):
                mx_id = (f"{spec['run_id_prefix']}-{case}: "
                         f"{mx.CASES[case]['case_id']} (model "
                         f"experiment {arm})")
                self.assertNotIn(mx_id, assay_ids)

    def test_problem_texts_are_byte_identical_to_the_frozen_assay(self):
        """Art. XLVII: same frozen problems — the import must carry the
        EXACT assay texts (a re-typed text would be a different
        problem)."""
        for case in ("A", "B", "C"):
            self.assertEqual(mx.CASES[case]["text"],
                             assay.AUTHORED_PROBLEMS[case]["text"])
            self.assertEqual(mx.CASES[case]["case_id"],
                             assay.AUTHORED_PROBLEMS[case]["case_id"])

    def test_the_instrument_is_imported_unmodified(self):
        """The frozen instrument's own file must be byte-identical to
        its committed state (the freeze discipline — importing a
        modified instrument would be tuning after freeze, Art. LIX)."""
        import subprocess
        r = subprocess.run(
            ["git", "diff", "--stat", "HEAD",
             "--", "scripts/r452_quality_instrument.py"],
            cwd=str(REPO), capture_output=True, text=True)
        self.assertEqual(
            r.stdout.strip(), "",
            "scripts/r452_quality_instrument.py must not be modified "
            "relative to HEAD (the frozen instrument)")


if __name__ == "__main__":
    unittest.main()

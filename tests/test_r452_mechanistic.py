"""tests/test_r452_mechanistic.py — R452 Phase 5/6/7 battery: the
mechanistic solver, the decisive-experiment contract, and the causal
learning loop (the directive's Phase 9 acceptance names these three
test families explicitly).

Phase 5 — the solver chain:
  candidate mechanism parameters -> canonical engineering variables
  -> equations -> baseline prediction -> failure threshold ->
  computed outcome, with the closed epistemic vocabulary
  (COMPUTED / MODEL_DERIVED / SOURCE_FACT / UNKNOWN) on every output
  and NO result silently becoming "validated".

Phase 6 — the constitutional experiment object: all thirteen fields,
the kill-outcome invariant (an experiment that can only confirm is
REJECTED as incomplete).

Phase 7 — the causal learning loop: the eight stages, the causal edge
(parent_candidate_id, experiment_id, observed_outcome,
failed_constraint, mutation_reason, child_candidate_id), the
outcome-sensitivity regression, and determinism.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from discovery_fabric.engine import mechanistic_solver as ms  # noqa: E402
from discovery_fabric.engine import decisive_experiment as de  # noqa: E402
from discovery_fabric.engine import causal_learning as cl  # noqa: E402

PROBLEM_B = json.loads(
    (REPO_ROOT / "R452" / "ASSAY_RUN_B" / "authored_problem.json")
    .read_text())["text"]


class TestQuantityExtraction(unittest.TestCase):
    """Phase 5: numbers + units with exact spans (Art. II)."""

    def test_spans_are_exact(self):
        text = "a 2.5-millimetre branch feeds the pinion"
        qs = ms.extract_quantities(text)
        self.assertEqual(len(qs), 1)
        q = qs[0]
        self.assertEqual(text[q["span"][0]:q["span"][1]],
                         q["raw_text"])
        self.assertEqual(q["raw_text"], "2.5-millimetre")
        self.assertEqual(q["value"], 2.5)

    def test_units_canonicalize(self):
        qs = ms.extract_quantities(
            "3 centimetres and 1800 centipoise and 2 bar and "
            "0.5 litres per minute")
        vals = {q["quantity_class"]: q["value"] for q in qs}
        self.assertEqual(vals["diameter_or_length_mm"], 30.0)
        self.assertEqual(vals["viscosity_mPa_s"], 1800.0)
        self.assertAlmostEqual(vals["pressure_mmHg"], 1500.124, places=2)
        self.assertEqual(vals["flow_ml_min"], 500.0)

    def test_thousands_separator(self):
        qs = ms.extract_quantities("near 1,800 centipoise")
        self.assertEqual(qs[0]["value"], 1800.0)

    def test_no_numbers_no_quantities(self):
        self.assertEqual(ms.extract_quantities("no numbers here"), [])

    def test_diameter_length_disambiguation(self):
        text = ("a 4-millimetre main gallery feeding 2.5-millimetre "
                "drilled branches, each roughly 60 millimetres long")
        cls = ms.classify_length_quantities(
            text, ms.extract_quantities(text))
        by_class = {}
        for q in cls:
            if q["quantity_class"] in ("diameter_mm", "length_mm"):
                by_class.setdefault(q["quantity_class"], []).append(
                    q["value"])
        self.assertEqual(by_class.get("diameter_mm"), [4.0, 2.5])
        self.assertEqual(by_class.get("length_mm"), [60.0])


class TestCanonicalVariables(unittest.TestCase):
    """Phase 5: the canonical engineering variables from ACTUAL
    inputs (candidate parameters first, then the problem's own
    numbers, else UNKNOWN — never fabricated)."""

    def test_candidate_parameter_takes_priority(self):
        canon = ms.build_canonical_variables(
            PROBLEM_B,
            {"primary_diameter_mm": {
                "value": 3.2, "unit": "mm",
                "epistemic_class": "MODEL_DERIVED",
                "source": "the candidate's declared design"}})
        v = canon["variables"]["primary_diameter_mm"]
        self.assertEqual(v["value"], 3.2)
        self.assertEqual(v["epistemic_class"], "MODEL_DERIVED")
        self.assertIn("candidate parameter", v["source"])

    def test_problem_numbers_are_source_facts_with_spans(self):
        canon = ms.build_canonical_variables(PROBLEM_B)
        v = canon["variables"]["viscosity_mPa_s"]
        self.assertEqual(v["value"], 1800.0)
        self.assertEqual(v["epistemic_class"], "SOURCE_FACT")
        self.assertIn("1,800 centipoise", v["source"])

    def test_unknown_never_fabricated(self):
        canon = ms.build_canonical_variables("a problem with no "
                                             "numbers at all")
        for v in canon["variables"].values():
            self.assertIsNone(v["value"])
            self.assertEqual(v["epistemic_class"], "UNKNOWN")

    def test_requirement_context_only_for_threshold(self):
        canon = ms.build_canonical_variables(
            "circulates 5 litres per minute normally")
        self.assertIsNone(
            canon["variables"]["required_flow_ml_min"]["value"])
        canon2 = ms.build_canonical_variables(
            "must deliver at least 5 litres per minute")
        self.assertEqual(
            canon2["variables"]["required_flow_ml_min"]["value"],
            5000.0)

    def test_every_variable_is_classified(self):
        canon = ms.build_canonical_variables(PROBLEM_B)
        for v in canon["variables"].values():
            self.assertIn(v["epistemic_class"],
                          ms.EPISTEMIC_CLASSES)


class TestVirtualExperiment(unittest.TestCase):
    """Phase 5: the full chain with baseline supremacy and honest
    outcome vocabulary."""

    def test_baseline_arm_uses_problem_numbers_only(self):
        """The baseline must NEVER inherit the candidate's override
        (Art. XLVII: the baseline is the problem's own current
        configuration)."""
        rec = ms.run_mechanistic_virtual_experiment(
            PROBLEM_B, candidate_id="cand:t",
            candidate_parameters={"primary_diameter_mm": {
                "value": 4.5, "unit": "mm",
                "epistemic_class": "MODEL_DERIVED"}})
        self.assertEqual(rec["baseline_prediction"]["diameter_mm"],
                         2.5)
        self.assertEqual(rec["candidate_prediction"]["diameter_mm"],
                         4.5)

    def test_outcome_vocabulary_is_closed(self):
        rec = ms.run_mechanistic_virtual_experiment(
            PROBLEM_B, candidate_id="cand:t")
        self.assertIn(rec["status"], (
            "COMPUTED_PASS", "COMPUTED_FAIL",
            "COMPUTED_NO_BASELINE_DIFF",
            "COMPUTED_PASS_BASELINE_INCONCLUSIVE",
            "MODEL_INVALIDITY", "INCONCLUSIVE_UNKNOWN_INPUT"))

    def test_every_output_carries_epistemic_class(self):
        rec = ms.run_mechanistic_virtual_experiment(
            PROBLEM_B, candidate_id="cand:t")
        self.assertEqual(rec["epistemic_class"], "COMPUTED")
        self.assertEqual(rec["baseline_prediction"]
                         ["epistemic_class"], "COMPUTED")
        self.assertEqual(rec["candidate_prediction"]
                         ["epistemic_class"], "COMPUTED")
        self.assertEqual(rec["failure_threshold"]["epistemic_class"],
                         "SOURCE_FACT")
        self.assertIn("never a physical observation",
                      rec["honesty_note"])

    def test_fail_then_mutate_then_child_passes(self):
        rec = ms.run_mechanistic_virtual_experiment(
            PROBLEM_B, candidate_id="cand:t")
        self.assertEqual(rec["status"], "COMPUTED_FAIL")
        mut = ms.mechanistic_mutation(rec, {})
        self.assertIsNotNone(mut)
        self.assertEqual(mut["mutation_kind"],
                         "INVERSE_POISEUILLE_DIAMETER")
        child = ms.run_mechanistic_virtual_experiment(
            PROBLEM_B, candidate_id="cand:t:child",
            candidate_parameters={"primary_diameter_mm": {
                "value": mut["to_value"], "unit": "mm",
                "epistemic_class": "COMPUTED"}})
        self.assertIn(child["status"], ("COMPUTED_PASS",
                                        "COMPUTED_PASS_BASELINE_"
                                        "INCONCLUSIVE"))
        self.assertGreaterEqual(
            child["computed_outcome"]["candidate_flow_ml_min"],
            child["computed_outcome"]["required_flow_ml_min"])

    def test_unknown_input_refuses_to_compute(self):
        rec = ms.run_mechanistic_virtual_experiment(
            "a problem with no numbers", candidate_id="cand:t")
        self.assertEqual(rec["status"], "INCONCLUSIVE_UNKNOWN_INPUT")
        self.assertEqual(rec["epistemic_class"], "UNKNOWN")

    def test_solver_version_pinned(self):
        rec = ms.run_mechanistic_virtual_experiment(
            PROBLEM_B, candidate_id="cand:t")
        self.assertEqual(rec["solver_bridge_version"],
                         ms.SOLVER_BRIDGE_VERSION)
        self.assertEqual(rec["solver_version"],
                         "hydraulic_network_1d/1.0.0")


class TestDecisiveExperimentContract(unittest.TestCase):
    """Phase 6: the constitutional experiment object."""

    def _build(self):
        rec = ms.run_mechanistic_virtual_experiment(
            PROBLEM_B, candidate_id="cand:t")
        return de.build_virtual_experiment_contract(rec)

    def test_all_thirteen_fields_present(self):
        exp = self._build()
        for field in de.REQUIRED_FIELDS:
            self.assertIn(field, exp, field)
            self.assertTrue(str(exp[field]).strip(), field)

    def test_valid_contract(self):
        v = self._build()["validation"]
        self.assertTrue(v["valid"], v["rejection_reason"])
        self.assertTrue(v["kill_outcome_present"])
        self.assertTrue(v["kill_outcome_directional"])
        self.assertTrue(v["thresholds_distinct"])

    def test_no_kill_outcome_rejected_as_incomplete(self):
        """THE directive's required test: an experiment with NO
        possible kill outcome must be REJECTED as incomplete."""
        exp = self._build()
        exp = dict(exp)
        exp["kill_outcome"] = ("any outcome of the experiment "
                                "confirms the mechanism")
        v = de.validate_experiment_contract(exp)
        self.assertFalse(v["valid"])
        self.assertFalse(v["decisive"])
        self.assertIn("VACUOUS", v["rejection_reason"])

    def test_kill_outcome_must_name_failure_direction(self):
        exp = self._build()
        exp = dict(exp)
        exp["kill_outcome"] = "the measurement happens"
        v = de.validate_experiment_contract(exp)
        self.assertFalse(v["valid"])
        self.assertIn("no measurable failure direction",
                      v["rejection_reason"])

    def test_blocker_field_is_incomplete_not_valid(self):
        exp = self._build()
        exp = dict(exp)
        exp["sample"] = "UNKNOWN (no sample-size stage recorded)"
        v = de.validate_experiment_contract(exp)
        self.assertFalse(v["valid"])
        self.assertIn("sample", v["blocker_fields"])

    def test_identical_thresholds_rejected(self):
        exp = self._build()
        exp = dict(exp)
        exp["falsification_threshold"] = exp["acceptance_threshold"]
        v = de.validate_experiment_contract(exp)
        self.assertFalse(v["valid"])
        self.assertIn("not distinct observations",
                      v["rejection_reason"])

    def test_epistemic_classes_closed_vocabulary(self):
        exp = self._build()
        for field, cls in exp["field_epistemic_classes"].items():
            self.assertIn(cls, de.FIELD_EPISTEMIC_CLASSES,
                          f"{field}: {cls}")

    def test_virtual_experiment_never_physical(self):
        exp = self._build()
        self.assertIn("COMPUTATIONAL_RESULT", exp["apparatus"])
        self.assertIn("never a physical observation",
                      exp["apparatus"])


class TestCausalLearningLoop(unittest.TestCase):
    """Phase 7: the loop, the causal edge, sensitivity, determinism."""

    def test_all_eight_stages_execute(self):
        loop = cl.run_causal_learning_loop(
            PROBLEM_B, "cand:loop:t")
        self.assertEqual(loop["loop_stages_executed"],
                         list(cl.LOOP_STAGES))

    def test_causal_edge_six_fields(self):
        loop = cl.run_causal_learning_loop(
            PROBLEM_B, "cand:loop:t")
        edge = loop["causal_edge"]
        for field in ("parent_candidate_id", "experiment_id",
                      "observed_outcome", "failed_constraint",
                      "mutation_reason", "child_candidate_id"):
            self.assertIn(field, edge)
            self.assertTrue(edge[field], field)
        self.assertEqual(edge["parent_candidate_id"], "cand:loop:t")
        self.assertEqual(edge["child_candidate_id"],
                         "cand:loop:t:mut1")
        self.assertEqual(edge["observed_outcome"], "COMPUTED_FAIL")

    def test_outcome_sensitivity_regression(self):
        """THE directive's required regression: changing the
        experiment outcome changes the resulting mutation."""
        loop1 = cl.run_causal_learning_loop(
            PROBLEM_B, "cand:loop:a")
        loop2 = cl.run_causal_learning_loop(
            PROBLEM_B.replace("at least 0.8 litres per minute",
                              "at least 1.2 litres per minute"),
            "cand:loop:b")
        self.assertNotEqual(loop1["mutation"]["to_value"],
                            loop2["mutation"]["to_value"])
        self.assertGreater(loop2["mutation"]["to_value"],
                           loop1["mutation"]["to_value"])
        self.assertNotEqual(
            loop1["causal_edge"]["failed_constraint"],
            loop2["causal_edge"]["failed_constraint"])

    def test_technical_state_transition_recorded(self):
        loop = cl.run_causal_learning_loop(
            PROBLEM_B, "cand:loop:t")
        ts = loop["technical_state"]
        self.assertEqual(ts["before"]["status"], "UNMEASURED")
        self.assertEqual(ts["after"]["status"],
                         "VIOLATED_COMPUTATIONALLY")
        self.assertGreater(ts["after"]["deficit_ml_min"], 0)
        self.assertEqual(ts["transition"],
                         "TECHNICAL_STATE_UPDATED_FROM_EXPERIMENT")

    def test_determinism(self):
        l1 = cl.run_causal_learning_loop(
            PROBLEM_B, "cand:loop:d", run_label="det")
        l2 = cl.run_causal_learning_loop(
            PROBLEM_B, "cand:loop:d", run_label="det")
        self.assertEqual(l1["loop_id"], l2["loop_id"])
        self.assertEqual(
            l1["mutation"]["to_value"], l2["mutation"]["to_value"])
        self.assertEqual(
            l1["experiment"]["input_hash"] if "input_hash" in
            l1["experiment"] else l1["experiment"]
            ["baseline_prediction"]["input_hash"],
            l2["experiment"]["baseline_prediction"]["input_hash"])

    def test_zero_llm_calls(self):
        loop = cl.run_causal_learning_loop(
            PROBLEM_B, "cand:loop:t")
        self.assertEqual(loop["llm_calls"], 0)
        self.assertTrue(loop["deterministic"])

    def test_synthetic_loop_verification_honest(self):
        loop = cl.run_causal_learning_loop(
            PROBLEM_B, "cand:loop:t")
        self.assertEqual(loop["loop_verification_state"],
                         "SYNTHETIC_LOOP_VERIFIED")
        self.assertIn("NO external reality",
                      loop["loop_verification_basis"])

    def test_bounded(self):
        loop = cl.run_causal_learning_loop(
            PROBLEM_B, "cand:loop:t")
        self.assertTrue(loop["bounded"])
        # exactly one experiment + one child experiment
        self.assertEqual(
            len([s for s in loop["stages"]
                 if s["stage"] == "VIRTUAL_EXPERIMENT"]), 1)
        self.assertIsNotNone(loop["child_experiment"])


class TestReferenceValidation(unittest.TestCase):
    """The solver's own instrument check (the directive: 'checked
    analytically')."""

    def test_hydraulic_solver_reference_validated(self):
        from discovery_fabric.engine import physics_core
        r = physics_core.validate_against_reference()
        self.assertEqual(r["status"], "REFERENCE_VALIDATED")
        for case in r["cases"]:
            self.assertTrue(case["pass"], case)


if __name__ == "__main__":
    unittest.main()

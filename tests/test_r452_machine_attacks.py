"""tests/test_r452_machine_attacks.py — R452 Phase 4: the adversarial
battery that attacks the MACHINE ITSELF.

"The R452 test battery must contain explicit attacks against:

  generic-template mechanism bias
  obvious-combination masquerading as novelty
  contradictory evidence
  LLM hallucinated mechanism details
  invention drift from problem constraints
  equation misuse
  attack-status mismatch
  adjudication mismatch
  run-ID laundering
  synthetic benchmark leakage

At least one known-defect control must be included. The expected
outcome is not 100% survival. A healthy discovery engine should kill
bad ideas."

Each attack below feeds the machinery a CRAFTED input designed to
make a weak instrument pass, and requires the machinery to DETECT or
REFUSE it (Art. XVII: every control must have an attempted bypass;
Art. XXX: "what would make this test pass while the underlying
system is still wrong?").

The KNOWN-DEFECT CONTROL is the R451 production fresh run's own
defect shape (the attack-status mismatch that closed R451 with
prose ambiguity) — the detector must fire on it.
"""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from r452_preflight import (  # noqa: E402
    PreflightIdentityError,
    assert_no_foreign_run_ids,
    check_contradictions,
    rebuild_attack_adjudication_record,
    SESSION_ID,
)

AUTHORITATIVE_RUN_ID = (
    "engrun:ui_40_000_vial_batches_protein_injectable_she_291053:"
    "2026-09-13T09:17:33")
import r452_quality_instrument as instrument  # noqa: E402
import r452_assay as assay  # noqa: E402
from discovery_fabric.engine import mechanistic_solver as ms  # noqa: E402
from discovery_fabric.engine import decisive_experiment as de  # noqa: E402
from discovery_fabric.engine import causal_learning as cl  # noqa: E402


# ---------------------------------------------------------------------------
# fixtures: a candidate record in the envelope's persisted shape
# ---------------------------------------------------------------------------

def _candidate(**over):
    """A well-formed candidate record (the envelope's
    mechanism_space.candidates[] shape) — the control object."""
    base = {
        "candidate_id": "cand:MS:DIRECT_TRANSFER:0001",
        "transformation_operator": "PARAMETER_BOUND",
        "mechanism": "branch diameter increase raises Poiseuille flow",
        "intervention": "enlarged drilled branch",
        "novel_design_variable": "primary branch diameter",
        "distinctness_verdict": "DISTINCT",
        "distinctness_basis": "GENUINE_MECHANISM_DIFFERENCE",
        "testable_prediction": "flow reaches 800 mL/min at cold start",
        "testable_prediction_check": {
            "present": True, "measurable_quantity": True,
            "sufficiently_specific": True, "testable": True},
        "span_binding": {
            "mechanism_source_span": "the high-speed pinion bearing "
                                      "runs starved",
            "verbatim_in_record": True, "match_mode": "VERBATIM"},
        "mechanism_support": {
            "counts": {"SUPPORTS": 2, "PARTIALLY_SUPPORTS": 1,
                       "CONTRADICTS": 0, "IRRELEVANT": 0,
                       "NOT_ENOUGH_EVIDENCE": 1},
            "n_items": 4},
    }
    base.update(over)
    return base


def _envelope(candidates, counts=None, contradictions=None,
              adversarial_status="EXECUTED", attacks=None):
    """A minimal ADJUDICATION-envelope fixture in the persisted
    shape (only the fields the instrument reads)."""
    return {
        "evidence_classification": {
            "classifier_version": "evidence_classification/1.0.0",
            "n_items": sum((counts or {"DIRECT_SUPPORT": 4}).values()),
            "counts": counts or {"DIRECT_SUPPORT": 4,
                                 "PARTIAL_SUPPORT": 2,
                                 "BACKGROUND": 0, "ANALOGY": 0,
                                 "CONTRADICTORY": 0, "IRRELEVANT": 0},
        },
        "mechanism_space": {"candidates": candidates},
        "contradictions": {"contradictions": contradictions or []},
        "attack_results": {
            "adversarial_status": adversarial_status,
            "overall": "EXECUTED" if adversarial_status == "EXECUTED"
            else "NOT_RUN",
            "attacks": attacks or [],
        },
        "adjudication": {
            "council": {"verdict": "CONTESTED",
                        "checks": []},
            "evidence_verification": {"verified": False},
        },
    }


class TestGenericTemplateMechanismBias(unittest.TestCase):
    """ATTACK 1 — generic-template mechanism bias: a template-shaped
    candidate (no novel design variable, no specific prediction) must
    NOT score as a good discovery, however well-worded its mechanism
    string is."""

    def _composite(self, cand):
        env = _envelope([cand])
        with unittest.mock.patch.object(
                instrument, "_read_json", lambda p: env):
            m = instrument._case_metrics(Path("/nonexistent"))
        return m

    def test_template_candidate_fails_composite(self):
        template = _candidate(
            candidate_id="cand:TEMPLATE:generic",
            transformation_operator="DIRECT_TRANSFER",
            novel_design_variable="",
            testable_prediction="performance improves",
            testable_prediction_check={
                "present": True, "measurable_quantity": False,
                "sufficiently_specific": False, "testable": False})
        m = self._composite(template)
        comp = m["candidate_composite"][0]
        self.assertFalse(comp["good_discovery"])
        self.assertIn("sufficiently_specific",
                      comp["failing_dimensions"])
        self.assertIn("not_obvious_combination",
                      comp["failing_dimensions"])

    def test_well_formed_candidate_passes_composite(self):
        """The control: the instrument is NOT a universal rejector
        (Art. V) — a genuinely well-formed candidate passes all six
        dimensions."""
        m = self._composite(_candidate())
        comp = m["candidate_composite"][0]
        self.assertTrue(comp["good_discovery"], comp["failing_dimensions"])
        self.assertEqual(m["differentiated_mechanism_rate"], 1.0)
        self.assertEqual(m["obvious_combination_rate"], 0.0)


class TestObviousCombinationMasquerade(unittest.TestCase):
    """ATTACK 2 — obvious-combination masquerading as novelty: a
    candidate whose distinctness verdict says DISTINCT (wording
    trick) but whose transformation is a bare DIRECT_TRANSFER with no
    novel design variable must still fail the composite."""

    def test_distinct_verdict_does_not_launder_direct_transfer(self):
        masquerade = _candidate(
            transformation_operator="DIRECT_TRANSFER",
            novel_design_variable="",
            distinctness_verdict="DISTINCT",
            distinctness_basis="vocabulary variation only")
        env = _envelope([masquerade])
        with unittest.mock.patch.object(
                instrument, "_read_json", lambda p: env):
            m = instrument._case_metrics(Path("/nonexistent"))
        comp = m["candidate_composite"][0]
        self.assertFalse(comp["good_discovery"])
        self.assertIn("not_obvious_combination",
                      comp["failing_dimensions"])
        self.assertIn("differentiated", comp["failing_dimensions"])

    def test_equivalent_verdict_never_counts_as_differentiated(self):
        renamed = _candidate(distinctness_verdict="EQUIVALENT")
        env = _envelope([renamed])
        with unittest.mock.patch.object(
                instrument, "_read_json", lambda p: env):
            m = instrument._case_metrics(Path("/nonexistent"))
        self.assertEqual(m["differentiated_mechanism_rate"], 0.0)


class TestContradictoryEvidence(unittest.TestCase):
    """ATTACK 3 — contradictory evidence: a candidate supported by a
    frozen pool that classifies records as CONTRADICTY and carries an
    unresolved HIGH contradiction must fail not_contradicted, and the
    contradiction rate must be MEASURED, not narrated."""

    def test_contradicted_candidate_fails(self):
        contradicted = _candidate(mechanism_support={
            "counts": {"SUPPORTS": 1, "PARTIALLY_SUPPORTS": 0,
                       "CONTRADICTS": 3, "IRRELEVANT": 0,
                       "NOT_ENOUGH_EVIDENCE": 0}, "n_items": 4})
        env = _envelope(
            [contradicted],
            counts={"DIRECT_SUPPORT": 1, "PARTIAL_SUPPORT": 0,
                    "BACKGROUND": 0, "ANALOGY": 0,
                    "CONTRADICTORY": 3, "IRRELEVANT": 0},
            contradictions=[{
                "contradiction_id": "con:1",
                "description": "the pool contradicts the mechanism",
                "severity": "HIGH", "currently_unresolved": True}])
        with unittest.mock.patch.object(
                instrument, "_read_json", lambda p: env):
            m = instrument._case_metrics(Path("/nonexistent"))
        comp = m["candidate_composite"][0]
        self.assertFalse(comp["good_discovery"])
        self.assertIn("not_contradicted", comp["failing_dimensions"])
        self.assertEqual(m["evidence_contradiction_rate"], 0.75)
        self.assertEqual(m["unresolved_high_contradictions"], 1)


class TestHallucinatedMechanismDetails(unittest.TestCase):
    """ATTACK 4 — LLM-hallucinated mechanism details: a candidate
    whose claimed source span does NOT appear verbatim in the frozen
    record must fail span_verbatim (the R451-C1.1 50% honesty number
    made a standing gate)."""

    def test_fabricated_span_fails(self):
        hallucinated = _candidate(span_binding={
            "mechanism_source_span": "a span that exists nowhere in "
                                     "the frozen record",
            "verbatim_in_record": False,
            "match_mode": "REJECTED_REWORDED"})
        env = _envelope([hallucinated])
        with unittest.mock.patch.object(
                instrument, "_read_json", lambda p: env):
            m = instrument._case_metrics(Path("/nonexistent"))
        comp = m["candidate_composite"][0]
        self.assertFalse(comp["good_discovery"])
        self.assertIn("span_verbatim", comp["failing_dimensions"])
        self.assertEqual(m["mechanism_span_verbatim_support"], 0.0)

    def test_ungrounded_mechanism_fails(self):
        ungrounded = _candidate(mechanism_support={
            "counts": {"SUPPORTS": 0, "PARTIALLY_SUPPORTS": 0,
                       "CONTRADICTS": 0, "IRRELEVANT": 0,
                       "NOT_ENOUGH_EVIDENCE": 4}, "n_items": 4})
        env = _envelope([ungrounded])
        with unittest.mock.patch.object(
                instrument, "_read_json", lambda p: env):
            m = instrument._case_metrics(Path("/nonexistent"))
        comp = m["candidate_composite"][0]
        self.assertIn("evidence_bound", comp["failing_dimensions"])


class TestInventionDriftFromProblemConstraints(unittest.TestCase):
    """ATTACK 5 — invention drift from problem constraints: the
    mutation machinery must REFUSE a mutation that violates the
    problem's own declared constraints, and the threshold resolution
    must never promote an incidental number to a requirement."""

    PROBLEM_B = json.loads(
        (REPO_ROOT / "R452" / "ASSAY_RUN_B" / "authored_problem.json")
        .read_text())["text"]

    def test_mutation_refused_past_declared_constraint(self):
        loop = cl.run_causal_learning_loop(
            self.PROBLEM_B, "cand:drift:test",
            problem_constraints={"max_primary_diameter_mm": 3.0})
        self.assertIsNotNone(loop["mutation"])
        self.assertTrue(loop["mutation"].get("refused"))
        self.assertEqual(loop["stop_reason"],
                         "MUTATION_REFUSED_BY_PROBLEM_CONSTRAINT")
        self.assertIn("exceeds the problem's own declared constraint",
                      loop["mutation"]["refusal_reason"])
        # no child was created past the constraint
        self.assertIsNone(loop["causal_edge"])

    def test_incidental_number_never_becomes_threshold(self):
        """A flow number with NO requirement context must not promote
        to the failure threshold (the drift-guard in variable
        resolution)."""
        text = ("The system circulates 5 litres per minute during "
                "normal operation and the operators are satisfied.")
        canon = ms.build_canonical_variables(text)
        self.assertIsNone(
            canon["variables"]["required_flow_ml_min"]["value"])
        self.assertEqual(
            canon["variables"]["required_flow_ml_min"]
            ["epistemic_class"], "UNKNOWN")

    def test_requirement_context_resolves_threshold(self):
        text = ("The operators need at least 0.9 litres per minute "
                "within 60 seconds of a cold start.")
        canon = ms.build_canonical_variables(text)
        self.assertEqual(
            canon["variables"]["required_flow_ml_min"]["value"], 900.0)


class TestEquationMisuse(unittest.TestCase):
    """ATTACK 6 — equation misuse: the Poiseuille relation applied
    outside its laminar applicability regime must flag
    MODEL_INVALIDITY, and a number-unit misparse must not silently
    change physics (the 1,800-centipoise thousands-separator case)."""

    def test_turbulent_regime_flags_model_invalidity(self):
        rec = ms.run_mechanistic_virtual_experiment(
            "Water at 1 centipoise flows through a 25-millimetre "
            "pipe 100 millimetres long; the operators need at least "
            "90 litres per minute. The supply is 2000 millimetres of "
            "mercury.",
            candidate_id="cand:turb")
        self.assertEqual(rec["status"], "MODEL_INVALIDITY")
        self.assertIn("candidate", rec["computed_outcome"]
                      ["invalid_arms"])

    def test_thousands_separator_not_decimal(self):
        qs = ms.extract_quantities("the oil is near 1,800 centipoise")
        self.assertEqual(qs[0]["value"], 1800.0)

    def test_decimal_comma_still_parses(self):
        qs = ms.extract_quantities("a 4,5 millimetre branch")
        self.assertEqual(qs[0]["value"], 4.5)


class TestAttackStatusMismatch(unittest.TestCase):
    """ATTACK 7 + THE KNOWN-DEFECT CONTROL — attack-status mismatch:
    the R451 production fresh run's own defect shape (ATTACK stage OK,
    adversarial NEVER CALLED with EVIDENCE_GATE_FAILED, adjudication
    CONTESTED, round-record prose 'the ATTACK stage EXECUTED') must be
    DETECTED by the contradiction machinery, and the instrument must
    measure attack_completeness as INCOMPLETE (0 produced), never as
    executed."""

    REAL_ATTACK_RESULTS = {
        "adversarial_status": "NOT_RUN",
        "adversarial_not_run_reason": "EVIDENCE_GATE_FAILED",
        "transport": {"status": "NEVER_CALLED"},
        "attacks": [], "killed_count": 0, "overall": "NOT_RUN",
    }

    def _known_defect_env(self):
        return {
            "evidence_classification": {
                "n_items": 22,
                "counts": {"DIRECT_SUPPORT": 5, "PARTIAL_SUPPORT": 8,
                           "BACKGROUND": 2, "ANALOGY": 3,
                           "CONTRADICTORY": 1, "IRRELEVANT": 3}},
            "mechanism_space": {"candidates": [_candidate()]},
            "contradictions": {"contradictions": []},
            "attack_results": dict(self.REAL_ATTACK_RESULTS),
            "adjudication": {
                "council": {"verdict": "CONTESTED", "checks": []},
                "evidence_verification": {
                    "verified": False,
                    "evidence_class": "UNSUPPORTED"}},
        }

    def test_known_defect_detected_by_contradiction_machinery(self):
        identity = {"run_ids_found": [AUTHORITATIVE_RUN_ID]}
        rebuilt = rebuild_attack_adjudication_record(
            {"attack_results": self.REAL_ATTACK_RESULTS},
            {"adjudication": self._known_defect_env()["adjudication"]},
            {"adversarial_overall": "NOT_RUN",
             "adjudication_verdict": "CONTESTED"},
            [{"stage": "ATTACK", "status": "OK"},
             {"stage": "ADJUDICATION", "status": "OK"}],
            identity)
        round_record = {"production_fresh_run": {"chain": {
            "attack": "the ATTACK stage EXECUTED (envelope persisted) "
                      "and the ADJUDICATION recorded verdict "
                      "CONTESTED"}}}
        defects = check_contradictions(rebuilt, round_record, None)
        kinds = {d["defect"] for d in defects}
        self.assertIn("ROUND_RECORD_ATTACK_PROSE_CONTRADICTS_STATE",
                      kinds)

    def test_instrument_measures_incomplete_attack(self):
        env = self._known_defect_env()
        with unittest.mock.patch.object(
                instrument, "_read_json", lambda p: env):
            m = instrument._case_metrics(Path("/nonexistent"))
        self.assertEqual(m["attacks_recorded"], 0)
        self.assertEqual(m["adversarial_status"], "NOT_RUN")
        self.assertEqual(m["adversarial_not_run_reason"],
                         "EVIDENCE_GATE_FAILED")
        # a stage that "executed" with zero challenges is NOT a
        # complete attack — the R451 defect made measurable
        produced = 1 if (m["attacks_recorded"] or 0) > 0 else 0
        self.assertEqual(produced / 1, 0.0)


class TestAdjudicationMismatch(unittest.TestCase):
    """ATTACK 8 — adjudication mismatch: a verdict claimed in the
    result envelope with no adjudication execution evidence must be
    detected; and a phantom KILL summary with an empty attack record
    must not fabricate kill statistics."""

    def test_verdict_without_execution_detected(self):
        rebuilt = rebuild_attack_adjudication_record(
            {"attack_results": {"overall": "NOT_RUN"}},
            {"adjudication": {"council": {"verdict": "CONTESTED"}}},
            {"adjudication_verdict": "CONTESTED"},
            [{"stage": "ATTACK", "status": "OK"}],  # NO ADJUDICATION
            {"run_ids_found": [AUTHORITATIVE_RUN_ID]})
        rebuilt["adjudication"]["adjudication_occurred"] = False
        defects = check_contradictions(rebuilt, None, None)
        kinds = {d["defect"] for d in defects}
        self.assertIn("ADJUDICATION_VERDICT_WITHOUT_EXECUTION", kinds)

    def test_phantom_kill_summary_not_counted(self):
        """attack_results.overall says KILLED but the attacks list is
        EMPTY — the instrument must count zero kills (UNKNOWN_NO_KILLS),
        never fabricate a kill-rate from the summary field."""
        env = _envelope(
            [_candidate()],
            attacks=[],
            adversarial_status="EXECUTED")
        env["attack_results"]["overall"] = "KILLED"
        with unittest.mock.patch.object(
                instrument, "_read_json", lambda p: env):
            m = instrument._case_metrics(Path("/nonexistent"))
        self.assertEqual(m["total_kills"], 0)
        self.assertEqual(m["false_kill_rate"], "UNKNOWN_NO_KILLS")

    def test_unsupported_kill_counted_as_false_kill(self):
        """A kill whose bases carry no source id, no computed
        quantity, and no record reference is an UNSUPPORTED kill
        (the R445-B class) — the false-kill rate measures it."""
        unsupported_kill = {
            "verdict": "KILL",
            "dimension": "unsupported_mechanism",
            "basis": "this seems wrong to the attacker"}
        env = _envelope([_candidate()], attacks=[unsupported_kill])
        with unittest.mock.patch.object(
                instrument, "_read_json", lambda p: env):
            m = instrument._case_metrics(Path("/nonexistent"))
        self.assertEqual(m["total_kills"], 1)
        self.assertEqual(m["unsupported_kills"], 1)
        self.assertEqual(m["false_kill_rate"], 1.0)

    def test_supported_kill_not_a_false_kill(self):
        supported_kill = {
            "verdict": "KILL",
            "dimension": "prior_art_collision",
            "basis": "US11185021B2 discloses the same labyrinth "
                     "geometry at 2.5 mm",
        }
        env = _envelope([_candidate()], attacks=[supported_kill])
        with unittest.mock.patch.object(
                instrument, "_read_json", lambda p: env):
            m = instrument._case_metrics(Path("/nonexistent"))
        self.assertEqual(m["false_kill_rate"], 0.0)


class TestRunIdLaundering(unittest.TestCase):
    """ATTACK 9 — run-ID laundering (the class is fully specified in
    tests/test_r452_preflight.py; this pins the cross-reference so the
    battery enumerates the directive's full attack list)."""

    def test_foreign_run_id_fails_closed(self):
        foreign = {
            "run_id": "engrun:FOREIGN:2026-09-13",
            "session_id": SESSION_ID,
            "call_class": "RUN_OWNED",
        }
        with self.assertRaises(PreflightIdentityError):
            assert_no_foreign_run_ids(
                [foreign], [AUTHORITATIVE_RUN_ID])


class TestSyntheticBenchmarkLeakage(unittest.TestCase):
    """ATTACK 10 — synthetic benchmark leakage: an assay problem whose
    text is copied (or near-copied) from a previously submitted
    problem must FAIL the freshness check; and the instrument must
    refuse to apply when it was modified after freeze."""

    def test_copied_problem_fails_freshness(self):
        prior = assay.collect_prior_problem_texts()
        self.assertTrue(prior)
        # copy a prior problem's text verbatim into a fake case
        copied = dict(assay.AUTHORED_PROBLEMS["A"])
        copied["case_id"] = "r452-leak-test"
        copied["text"] = prior[0]["text"]
        saved = dict(assay.AUTHORED_PROBLEMS)
        try:
            assay.AUTHORED_PROBLEMS["LEAK"] = copied
            assay.ALL_CASES["LEAK"] = copied
            fresh = assay.check_freshness()
            self.assertFalse(fresh["fresh"])
            self.assertTrue(any(
                "hash matches a prior problem text" in v
                or "near-duplicate" in v
                for v in fresh["violations"]))
        finally:
            assay.AUTHORED_PROBLEMS.clear()
            assay.AUTHORED_PROBLEMS.update(
                {k: v for k, v in saved.items()})
            assay.ALL_CASES.clear()
            assay.ALL_CASES.update(
                {**assay.AUTHORED_PROBLEMS, **assay.REPEAT_CASE})

    def test_paraphrased_problem_fails_freshness(self):
        """A truncated copy with filler (token overlap high) must also
        fail the near-duplicate check — leakage is not only
        verbatim."""
        prior = assay.collect_prior_problem_texts()
        text = prior[0]["text"]
        paraphrase = (text[: max(400, len(text) * 2 // 3)]
                      + " slightly reworded filler for the leak test")
        copied = dict(assay.AUTHORED_PROBLEMS["A"])
        copied["case_id"] = "r452-leak-test-2"
        copied["text"] = paraphrase
        saved = dict(assay.AUTHORED_PROBLEMS)
        try:
            assay.AUTHORED_PROBLEMS["LEAK2"] = copied
            assay.ALL_CASES["LEAK2"] = copied
            fresh = assay.check_freshness()
            self.assertFalse(fresh["fresh"])
            self.assertTrue(any(
                "near-duplicate" in v
                for v in fresh["violations"]))
        finally:
            assay.AUTHORED_PROBLEMS.clear()
            assay.AUTHORED_PROBLEMS.update(saved)
            assay.ALL_CASES.clear()
            assay.ALL_CASES.update(
                {**assay.AUTHORED_PROBLEMS, **assay.REPEAT_CASE})

    def test_instrument_refuses_post_freeze_modification(self):
        """The frozen instrument's sha256 discipline: any post-freeze
        script change makes apply() refuse (Art. LIX — no tuning
        against the results)."""
        frozen = json.loads(
            (REPO_ROOT / "R452" /
             "DISCOVERY_QUALITY_INSTRUMENT.json").read_text())
        self.assertNotEqual(frozen["instrument_sha256"], "0" * 64)
        # the ACTUAL verify passes (the instrument is unchanged); a
        # tampered frozen hash fails closed
        tampered = dict(frozen)
        tampered["instrument_sha256"] = "0" * 64
        with unittest.mock.patch.object(
                instrument, "_read_json", lambda p: tampered):
            doc = instrument.verify_instrument()
        self.assertIsNone(doc)


class TestExperimentContractDecisiveness(unittest.TestCase):
    """ATTACK (equation-misuse adjacent) — the Phase 6 invariant: an
    experiment with NO possible kill outcome must be REJECTED as
    incomplete (the directive's explicit required test)."""

    def _contract(self):
        rec = ms.run_mechanistic_virtual_experiment(
            json.loads((REPO_ROOT / "R452" / "ASSAY_RUN_B" /
                        "authored_problem.json").read_text())["text"],
            candidate_id="cand:contract:test")
        return de.build_virtual_experiment_contract(rec)

    def test_no_kill_outcome_rejected(self):
        exp = self._contract()
        broken = dict(exp)
        broken["kill_outcome"] = ("the experiment completes and data "
                                   "is collected, which confirms the "
                                   "mechanism")
        v = de.validate_experiment_contract(broken)
        self.assertFalse(v["valid"])
        self.assertIn("VACUOUS", v["rejection_reason"])

    def test_missing_field_rejected(self):
        exp = self._contract()
        broken = dict(exp)
        broken.pop("falsification_threshold")
        v = de.validate_experiment_contract(broken)
        self.assertFalse(v["valid"])
        self.assertIn("falsification_threshold", v["missing_fields"])

    def test_valid_contract_from_mechanistic_record(self):
        v = self._contract()["validation"]
        self.assertTrue(v["valid"], v["rejection_reason"])
        self.assertTrue(v["kill_outcome_directional"])
        self.assertTrue(v["thresholds_distinct"])


class TestCausalLoopSensitivity(unittest.TestCase):
    """THE PHASE 7 REGRESSION — "changing the experiment outcome
    changes the resulting mutation": a different required-flow
    threshold (a different experiment outcome) must produce a
    DIFFERENT mutation; a PASS outcome must produce NO mutation."""

    PROBLEM_B = json.loads(
        (REPO_ROOT / "R452" / "ASSAY_RUN_B" / "authored_problem.json")
        .read_text())["text"]

    def test_outcome_changes_mutation(self):
        loop1 = cl.run_causal_learning_loop(
            self.PROBLEM_B, "cand:sens:1")
        loop2 = cl.run_causal_learning_loop(
            self.PROBLEM_B.replace("at least 0.8 litres per minute",
                                   "at least 1.6 litres per minute"),
            "cand:sens:2")
        m1, m2 = loop1["mutation"], loop2["mutation"]
        self.assertIsNotNone(m1)
        self.assertIsNotNone(m2)
        self.assertNotEqual(m1["to_value"], m2["to_value"])
        self.assertGreater(m2["to_value"], m1["to_value"])
        # the causal edges carry the different observed outcomes
        self.assertNotEqual(
            loop1["causal_edge"]["failed_constraint"],
            loop2["causal_edge"]["failed_constraint"])

    def test_pass_outcome_produces_no_mutation(self):
        """A candidate that already meets the requirement: the loop
        records SUPPORT and NO mutation executes (mutation here would
        be optimization, not learning)."""
        passing = {"primary_diameter_mm": {
            "value": 4.5, "unit": "mm",
            "epistemic_class": "MODEL_DERIVED",
            "source": "the candidate's declared design"}}
        loop = cl.run_causal_learning_loop(
            self.PROBLEM_B, "cand:sens:pass",
            candidate_parameters=passing)
        self.assertEqual(loop["loop_outcome"],
                         "SUPPORTED_COMPUTATIONALLY")
        self.assertIsNone(loop["mutation"])
        self.assertEqual(loop["stop_reason"], "NO_MUTATION_REQUIRED")

    def test_child_reaches_support(self):
        loop = cl.run_causal_learning_loop(
            self.PROBLEM_B, "cand:sens:child")
        self.assertEqual(loop["child_outcome"],
                         "CHILD_SUPPORTS_HYPOTHESIS_COMPUTATIONALLY")
        edge = loop["causal_edge"]
        self.assertEqual(edge["parent_candidate_id"],
                         "cand:sens:child")
        self.assertEqual(edge["observed_outcome"], "COMPUTED_FAIL")
        self.assertIn("mL/min", edge["failed_constraint"])
        self.assertEqual(edge["child_candidate_id"],
                         "cand:sens:child:mut1")

    def test_invalid_contract_stops_loop(self):
        """A problem whose requirement resolves (valid contract) is
        the control; a problem with NO requirement produces an
        honest INCONCLUSIVE stop — never a fabricated experiment."""
        loop = cl.run_causal_learning_loop(
            "A vague problem with no numbers at all.",
            "cand:sens:vague")
        self.assertIn(loop["stop_reason"],
                      ("EXPERIMENT_CONTRACT_INVALID",
                       "EXPERIMENT_INCONCLUSIVE_UNKNOWN_INPUT"))
        self.assertIsNone(loop["causal_edge"])


# mock import used above
import unittest.mock  # noqa: E402


if __name__ == "__main__":
    unittest.main()

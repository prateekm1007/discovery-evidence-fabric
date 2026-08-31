"""tests/test_r379_technical_engine.py — adversarial test suite for
the R379 TECHNICAL IMPROVEMENT ENGINE V2 (structured technical state +
technical evaluator contract + technical mutation loop).

Constitutional mandate (Art. V/VIII/XVII): every control gets
positive, negative and metamorphic tests, INCLUDING attempted bypasses:

  ATTACKED BYPASSES
  - fabricated evidence span on an EXTRACTED value (Art. VI forgery)
  - value claimed from a span that proves something else (Art. II)
  - constraint without justification (Art. XXVII invented threshold)
  - objective unrelated to the problem (score-chasing objective)
  - sign inversion on a MINIMIZE objective (the direct-target defect
    the first draft HAD — pinned so it can never return)
  - off-target technical mutation (CEO rule 8 analog)
  - wrong-direction mutation (against the evaluator's prediction)
  - out-of-envelope value (unbounded invention)
  - mutation of an UNBOUNDED parameter (ADR_R379 anti-gaming)
  - EXTRACTED forgery on the new value
  - no-op mutation
  - spec-text/state divergence (deltas that ignore the variable)
  - constraint laundering (UNVERIFIABLE -> SATISFIED via a MODELLED
    value — Art. XXV certainty laundering)
  - constraint wall that must end in an honest kill
  - technical-state numbers escaping the numerical-provenance audit
    (a new section must not become a laundering path)

All tests are HERMETIC: the LLM proposer is mocked; no network; no
live keys (conftest guarantee).
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

from discovery_fabric.engine import technical_state as ts  # noqa: E402
from discovery_fabric.engine import technical_evaluator as te  # noqa: E402
from discovery_fabric.engine import technical_improvement_engine as tie  # noqa: E402
from discovery_fabric.engine.evaluator_contract import (  # noqa: E402
    get_evaluator, register_evaluator, registered_evaluators)
from discovery_fabric.engine.evaluator_contract import (  # noqa: E402
    CandidateContext)
from discovery_fabric.benchmark.numerical_provenance import (  # noqa: E402
    audit_numerical_provenance)

# ---------------------------------------------------------------------------
# fixtures — a quantified cooling-domain candidate
# ---------------------------------------------------------------------------
EV_TEXT = ("Water-glycol coolant flow rates of 0.01-1.0 mL/min were "
           "tested in a lithium battery module; peak cell temperature "
           "fell from 55 to 42 degrees C at the highest flow. Pump "
           "noise above 0.6 mL/min exceeded cabin limits.")
EV_ITEMS = [{"id": "ev:1", "title": "Cooling study",
             "text": EV_TEXT, "content_hash": "cb1"}]

PROBLEM = {"device": "aircraft onboard lithium battery installation",
           "failure_mode": "battery thermal event containment failure",
           "failure": "thermal event", "constraint": "containment"}

STATE_PROPOSAL = {
    "parameters": [
        {"param_id": "coolant_flow", "name": "coolant flow rate",
         "category": "OPERATING_CONDITIONS", "unit": "mL/min",
         "value": 0.2, "value_class": "MODELLED",
         "range_min": 0.01, "range_max": 1.0,
         "range_span": "flow rates of 0.01-1.0 mL/min",
         "range_evidence_id": "ev:1",
         "role": "convective heat removal"},
        {"param_id": "peak_temp", "name": "peak cell temperature",
         "category": "PARAMETERS", "unit": "degC",
         "value": 55.0, "value_class": "EXTRACTED",
         "value_span": "fell from 55 to 42", "value_evidence_id": "ev:1",
         "range_min": 42.0, "range_max": 55.0,
         "range_span": "fell from 55 to 42", "range_evidence_id": "ev:1",
         "role": "thermal safety metric"},
    ],
    "constraints": [
        {"constraint_id": "c1", "target": "peak_temp", "bound": "<=",
         "limit": 60.0, "unit": "degC", "limit_class": "MODELLED",
         "justification": "cell safety threshold from problem constraint"},
        {"constraint_id": "c2", "target": "coolant_flow", "bound": "<=",
         "limit": 0.6, "unit": "mL/min", "limit_class": "MODELLED",
         "justification": "pump noise cabin limit in the evidence narrative"},
    ],
    "objectives": [
        {"objective_id": "o1", "target": "peak_temp",
         "direction": "MINIMIZE",
         "basis": "battery thermal event containment failure requires "
                  "peak temperature minimized"}],
    "dependencies": [
        {"relation_id": "r1", "cause": "coolant_flow",
         "effect": "peak_temp", "direction": "DECREASES",
         "statement": "higher coolant flow removes more heat",
         "relation_class": "MODELLED"}],
}

SPEC = {
    "invention_id": {"value": "t-test-1"},
    "mechanism": {"value": {
        "mechanism": "Convective cooling of the battery module by a "
                     "water-glycol coolant loop",
        "intervention": "Battery module with coolant loop at flow 0.2 "
                        "mL/min",
        "expected_effect": "Peak cell temperature stays below the "
                           "safety threshold",
        "falsification_test": "Measure temperature at operating load",
        "mechanism_source_span": "peak cell temperature"}},
    "distinguishing_features": {"value": {}},
    "prior_art": {"value": {}},
    "novelty_hypothesis": {"value": {}},
}


def _validated_state(proposal=None):
    state, report = ts.validate_technical_state(
        copy.deepcopy(proposal or STATE_PROPOSAL), EV_ITEMS, PROBLEM)
    return state, report


def _spec_with_state(proposal=None):
    state, report = _validated_state(proposal)
    spec = copy.deepcopy(SPEC)
    spec["technical_state"] = {
        "value": state, "epistemic_class": "MODELLED",
        "origin_stage": "TECHNICAL_STATE_EXTRACTION",
        "evidence_ids": ["ev:1"], "note": "test state"}
    return spec


def _ctx(proposal=None):
    return CandidateContext(spec=_spec_with_state(proposal),
                            decisive=None, problem=PROBLEM,
                            evidence_items=EV_ITEMS)


VALID_MUTATION_FIELDS = {
    "MUTATION_KIND": "OPERATING_CONDITION_CHANGE",
    "TARGET_PARAM": "coolant_flow",
    "NEW_VALUE": "0.5",
    "DIRECTION": "INCREASE",
    "VALUE_CLASS": "MODELLED",
    "VALUE_SPAN": "NONE",
    "VALUE_EVIDENCE_ID": "NONE",
    "RATIONALE": "more flow removes more heat lowering peak temperature",
    "MECHANISM_DELTA": "coolant flow rate increased to 0.5 mL/min "
                       "within the evidence envelope for convective "
                       "heat removal",
    "INTERVENTION_DELTA": "the battery module coolant loop operates at "
                          "0.5 mL/min",
}


def _proposal(fields=None, status="OK"):
    return {"proposal_id": "tmp:test", "provider": "mock",
            "model": "mock", "status": status, "prompt_hash": "ph",
            "output_hash": "oh", "latency_ms": 1, "error": None,
            "fields": dict(fields or VALID_MUTATION_FIELDS)}


def _mock_state_proposer(monkeypatch, proposal, status="OK"):
    def fake(problem, spec, ev_items, provider=None, feedback=None):
        return {"proposal_id": "tsp:test", "provider": "mock",
                "model": "mock", "status": status, "prompt_hash": "ph",
                "output_hash": "oh", "latency_ms": 1, "error": None,
                "proposal": proposal}
    monkeypatch.setattr(tie, "propose_technical_state", fake)


def _mock_mutation_proposer(monkeypatch, field_sets):
    calls = {"n": 0}

    def fake(ctx, evaluation, provider=None, feedback=None):
        i = min(calls["n"], len(field_sets) - 1)
        calls["n"] += 1
        return _proposal(field_sets[i])
    monkeypatch.setattr(tie, "propose_technical_mutation", fake)
    return calls


# ===========================================================================
# 1. TECHNICAL STATE VALIDATION
# ===========================================================================
class TestStateValidation:
    def test_extracted_value_admitted_with_envelope(self):
        state, report = _validated_state()
        flow = [p for p in state["parameters"]
                if p["param_id"] == "coolant_flow"][0]
        assert flow["range_class"] == "EXTRACTED"
        assert (flow["range_min"], flow["range_max"]) == (0.01, 1.0)
        temp = [p for p in state["parameters"]
                if p["param_id"] == "peak_temp"][0]
        assert temp["value_class"] == "EXTRACTED"
        assert temp["value"] == 55.0

    def test_fabricated_span_is_not_admitted(self):
        """Art. VI forgery attempt: span not in the evidence."""
        prop = copy.deepcopy(STATE_PROPOSAL)
        prop["parameters"][1]["value_span"] = \
            "peak temperature rose to 99 degrees C"
        state, report = _validated_state(prop)
        temp = [p for p in state["parameters"]
                if p["param_id"] == "peak_temp"][0]
        assert temp["value"] is None
        assert temp["value_class"] == "UNKNOWN"
        assert any(d["gate"] == "P3" for d in report["dropped"])

    def test_value_not_proven_by_its_span_demotes_keeps_param(self):
        """Art. II: a span proving 0.01-1.0 does not prove 0.5."""
        prop = copy.deepcopy(STATE_PROPOSAL)
        prop["parameters"][0]["value"] = 0.5
        prop["parameters"][0]["value_class"] = "EXTRACTED"
        prop["parameters"][0]["value_span"] = "flow rates of 0.01-1.0"
        state, report = _validated_state(prop)
        flow = [p for p in state["parameters"]
                if p["param_id"] == "coolant_flow"][0]
        assert flow["value"] is None
        assert flow["value_class"] == "UNKNOWN"
        # the span-proven envelope SURVIVES (demotion, not deletion)
        assert flow["range_class"] == "EXTRACTED"
        assert flow["range_max"] == 1.0

    def test_constraint_without_justification_dropped(self):
        """Art. XXVII: an invented threshold never gates anything."""
        prop = copy.deepcopy(STATE_PROPOSAL)
        prop["constraints"][0]["justification"] = ""
        state, report = _validated_state(prop)
        assert state["constraints"] == [c for c in
                                        state["constraints"]
                                        if c["constraint_id"] != "c1"]
        assert any(d["gate"] == "C1" and d["id"] == "c1"
                   for d in report["dropped"])

    def test_objective_not_tied_to_problem_dropped(self):
        prop = copy.deepcopy(STATE_PROPOSAL)
        prop["objectives"][0]["basis"] = \
            "make the submarine dive faster than a dolphin"
        state, report = _validated_state(prop)
        assert state["objectives"] == []
        assert any(d["gate"] == "O1" for d in report["dropped"])

    def test_dependency_with_undeclared_endpoints_dropped(self):
        prop = copy.deepcopy(STATE_PROPOSAL)
        prop["dependencies"][0]["cause"] = "solar_flare_intensity"
        state, report = _validated_state(prop)
        assert state["dependencies"] == []
        assert any(d["gate"] == "D1" for d in report["dropped"])

    def test_extracted_relation_span_must_name_both_endpoints(self):
        """Art. II: a span about something else is not evidence for
        THIS relationship."""
        prop = copy.deepcopy(STATE_PROPOSAL)
        prop["dependencies"][0]["relation_class"] = "EXTRACTED"
        prop["dependencies"][0]["span"] = "pump noise above 0.6 mL/min"
        prop["dependencies"][0]["evidence_id"] = "ev:1"
        state, report = _validated_state(prop)
        assert state["dependencies"] == []
        assert any(d["gate"] == "D2" for d in report["dropped"])

    def test_unproven_range_on_extracted_param_is_dropped(self):
        """Art. XXVII: EXTRACTED-value params cannot carry unproven
        envelopes."""
        prop = copy.deepcopy(STATE_PROPOSAL)
        prop["parameters"][1]["range_span"] = None
        prop["parameters"][1]["range_evidence_id"] = None
        state, report = _validated_state(prop)
        temp = [p for p in state["parameters"]
                if p["param_id"] == "peak_temp"][0]
        assert temp["range_min"] is None and temp["range_max"] is None

    def test_unknown_is_explicit_never_invented(self):
        prop = {"parameters": [
            {"param_id": "x", "name": "unmeasured", "category":
             "PARAMETERS", "value": None, "value_class": "UNKNOWN"}]}
        state, report = _validated_state(prop)
        assert state["parameters"][0]["value_class"] == "UNKNOWN"
        assert state["parameters"][0]["value"] is None


# ===========================================================================
# 2. THE ANALYTICAL EVALUATOR
# ===========================================================================
class TestEvaluator:
    def test_directional_feedback_statement(self):
        ev = te.evaluate_candidate_technically(_spec_with_state())
        lv = ev["limiting_variable"]
        assert lv is not None
        assert lv["param_id"] == "coolant_flow"
        assert lv["improving_move"] == "INCREASE"
        assert ("The limiting variable is" in lv["statement"]
                and "while preserving" in lv["statement"])

    def test_minimize_direct_target_improving_move_is_decrease(self):
        """PINNED: the inverted first draft proposed INCREASING the
        target of a MINIMIZE objective — this test makes that defect
        permanently visible if it ever returns."""
        prop = copy.deepcopy(STATE_PROPOSAL)
        # remove the relation: peak_temp becomes a pure design variable
        prop["dependencies"] = []
        spec = _spec_with_state(prop)
        ev = te.evaluate_candidate_technically(spec)
        dirs = {d["param_id"]: d for d in ev["improvement_directions"]}
        assert dirs["peak_temp"]["improving_move"] == "DECREASE"

    def test_sign_propagation_through_decreases_relation(self):
        ev = te.evaluate_candidate_technically(_spec_with_state())
        sens = ev["sensitivity"]["coolant_flow"]
        # flow UP -> temp DOWN -> MINIMIZE improves: increase IMPROVES
        assert sens["increase_effect"] == "IMPROVES"

    def test_outcome_variables_are_not_design_variables(self):
        ev = te.evaluate_candidate_technically(_spec_with_state())
        dirs = {d["param_id"]: d for d in ev["improvement_directions"]}
        assert dirs["peak_temp"]["is_design_variable"] is False
        assert dirs["coolant_flow"]["is_design_variable"] is True
        # the objective target is an outcome: the limiting variable must
        # be its upstream design cause
        assert ev["limiting_variable"]["param_id"] == "coolant_flow"

    def test_constraint_wall_blocks_limiting_variable(self):
        prop = copy.deepcopy(STATE_PROPOSAL)
        # flow at its constraint limit: INCREASE is blocked
        prop["parameters"][0]["value"] = 0.6
        spec = _spec_with_state(prop)
        ev = te.evaluate_candidate_technically(spec)
        assert ev["limiting_variable"] is None
        dirs = {d["param_id"]: d for d in ev["improvement_directions"]}
        assert dirs["coolant_flow"]["blocked_by"]

    def test_unverifiable_constraint_is_not_satisfied(self):
        """Art. XXV/IV: unknown is not satisfied."""
        prop = copy.deepcopy(STATE_PROPOSAL)
        prop["parameters"][1]["value"] = None
        prop["parameters"][1]["value_class"] = "UNKNOWN"
        spec = _spec_with_state(prop)
        ev = te.evaluate_candidate_technically(spec)
        crs = {c["constraint_id"]: c for c in ev["constraint_results"]}
        assert crs["c1"]["status"] == "UNVERIFIABLE"

    def test_deterministic_evaluation(self):
        """Metamorphic: same state -> byte-identical computation log."""
        spec = _spec_with_state()
        ev1 = te.evaluate_candidate_technically(spec)
        ev2 = te.evaluate_candidate_technically(_spec_with_state())
        log1 = dict(ev1["computation_log"])
        log2 = dict(ev2["computation_log"])
        log1.pop("computed_at"), log2.pop("computed_at")
        assert log1["input_state_sha256"] == log2["input_state_sha256"]
        assert log1["steps"] == log2["steps"]

    def test_spec_without_state_is_unquantified_not_error(self):
        ev = te.evaluate_candidate_technical = \
            te.evaluate_candidate_technically  # noqa
        ev = te.evaluate_candidate_technically(copy.deepcopy(SPEC))
        assert ev["status"] == "UNQUANTIFIED"
        assert "no technical_state" in ev["uncertainty"]["note"]

    def test_registered_behind_contract_not_default(self):
        regs = {r["evaluator_id"] for r in registered_evaluators()}
        assert te.EVALUATOR_ID in regs
        # no silent upgrade: the default stays the term-rule evaluator
        assert get_evaluator()["fidelity_tier"] == "TERM_RULE"

    def test_experiment_tier_still_unregistrable(self):
        """Art. XXXVIII: the reality boundary survives V2."""
        with pytest.raises(ValueError):
            register_evaluator("fake_experiment", "EXPERIMENT",
                               lambda ctx: None)


# ===========================================================================
# 3. MUTATION VALIDATION (the deterministic trust boundary)
# ===========================================================================
class TestMutationValidation:
    def _diag(self):
        return te.evaluate_candidate_technically(_spec_with_state())

    def test_valid_mutation_passes(self):
        v = tie.validate_technical_mutation(
            _ctx(), _proposal(), self._diag())
        assert v["valid"], v["reasons"]

    def test_off_target_mutation_rejected(self):
        """CEO rule 8 analog: a technical mutation exists only with its
        named diagnostic trigger."""
        f = dict(VALID_MUTATION_FIELDS, TARGET_PARAM="peak_temp")
        v = tie.validate_technical_mutation(_ctx(), _proposal(f),
                                            self._diag())
        assert not v["valid"]
        assert "target_is_limiting_variable" in v["checks"]

    def test_wrong_direction_rejected(self):
        f = dict(VALID_MUTATION_FIELDS, DIRECTION="DECREASE")
        v = tie.validate_technical_mutation(_ctx(), _proposal(f),
                                            self._diag())
        assert not v["valid"]
        assert "direction_matches_evaluator" in v["checks"]

    def test_out_of_envelope_rejected(self):
        f = dict(VALID_MUTATION_FIELDS, NEW_VALUE="2.5")
        v = tie.validate_technical_mutation(_ctx(), _proposal(f),
                                            self._diag())
        assert not v["valid"]
        assert "value_inside_envelope" in v["checks"]

    def test_unbounded_parameter_is_immutable(self):
        """ADR_R379 anti-gaming: no envelope -> no quantitative
        mutation (unconstrained invention is not improvement). Two
        layers: the evaluator never NAMES an unbounded param as
        limiting, and T2 rejects it even if the state was stripped of
        its envelope AFTER diagnosis (state-tampering defense)."""
        # layer 1: the evaluator refuses to name it
        prop = copy.deepcopy(STATE_PROPOSAL)
        prop["parameters"][0]["range_min"] = None
        prop["parameters"][0]["range_max"] = None
        prop["parameters"][0]["range_span"] = None
        ctx = _ctx(prop)
        diag = te.evaluate_candidate_technically(ctx.spec)
        assert diag["limiting_variable"] is None
        # layer 2: T2 fails closed on a tampered state
        diag = te.evaluate_candidate_technically(_ctx().spec)
        assert diag["limiting_variable"]["param_id"] == "coolant_flow"
        stripped = _ctx()
        stripped.spec["technical_state"]["value"]["parameters"][0][
            "range_min"] = None
        stripped.spec["technical_state"]["value"]["parameters"][0][
            "range_max"] = None
        v = tie.validate_technical_mutation(stripped, _proposal(), diag)
        assert not v["valid"]
        assert "envelope_declared" in v["checks"]

    def test_extracted_forgery_rejected(self):
        """Two forgery classes: (a) a span that does not exist in the
        evidence; (b) a VERBATIM span that does not contain the
        claimed number (span proves something else — Art. II)."""
        # (a) nonexistent span
        f = dict(VALID_MUTATION_FIELDS, VALUE_CLASS="EXTRACTED",
                 VALUE_SPAN="flow rates of 0.4 mL/min",
                 VALUE_EVIDENCE_ID="ev:1")
        v = tie.validate_technical_mutation(_ctx(), _proposal(f),
                                            self._diag())
        assert not v["valid"]
        assert v["checks"]["extracted_value_span_verbatim"] is False
        # (b) verbatim span, wrong number
        f2 = dict(VALID_MUTATION_FIELDS, VALUE_CLASS="EXTRACTED",
                  VALUE_SPAN="fell from 55 to 42",
                  VALUE_EVIDENCE_ID="ev:1")
        v2 = tie.validate_technical_mutation(_ctx(), _proposal(f2),
                                             self._diag())
        assert not v2["valid"]
        assert "extracted_value_in_span" in v2["checks"]
        assert v2["checks"]["extracted_value_in_span"] is False

    def test_no_op_rejected(self):
        f = dict(VALID_MUTATION_FIELDS, NEW_VALUE="0.2")
        v = tie.validate_technical_mutation(_ctx(), _proposal(f),
                                            self._diag())
        assert not v["valid"]
        assert "mutation_changes_value" in v["checks"]

    def test_spec_text_divergence_rejected(self):
        f = dict(VALID_MUTATION_FIELDS,
                 MECHANISM_DELTA="the device is painted blue",
                 INTERVENTION_DELTA="a nicer installation")
        v = tie.validate_technical_mutation(_ctx(), _proposal(f),
                                            self._diag())
        assert not v["valid"]
        assert "spec_text_sync" in v["checks"]

    def test_kind_category_mismatch_rejected(self):
        f = dict(VALID_MUTATION_FIELDS,
                 MUTATION_KIND="GEOMETRY_CHANGE")
        v = tie.validate_technical_mutation(_ctx(), _proposal(f),
                                            self._diag())
        assert not v["valid"]
        assert "kind_matches_category" in v["checks"]

    def test_own_constraint_violation_rejected(self):
        """T7: new value must not violate a constraint on the target."""
        f = dict(VALID_MUTATION_FIELDS, NEW_VALUE="0.7")  # c2 <= 0.6
        v = tie.validate_technical_mutation(_ctx(), _proposal(f),
                                            self._diag())
        assert not v["valid"]
        assert "own_constraint_satisfied" in v["checks"]

    def test_transport_failure_not_validated(self):
        v = tie.validate_technical_mutation(
            _ctx(), _proposal(status="CALL_FAILED"), self._diag())
        assert not v["valid"]
        assert v["stage"] == "TRANSPORT_OR_PARSE"


# ===========================================================================
# 4. APPLY + PROVENANCE CHAIN
# ===========================================================================
class TestApply:
    def test_causal_chain_and_hashes(self):
        ctx = _ctx()
        diag = te.evaluate_candidate_technically(ctx.spec)
        v = tie.validate_technical_mutation(ctx, _proposal(), diag)
        child = tie.apply_technical_mutation(ctx, _proposal(), v)
        mut = child.spec["_technical_improvement"]["mutation"]
        assert mut["chain"] == ("ORIGINAL CANDIDATE -> TECHNICAL "
                                "DIAGNOSIS -> TECHNICAL MUTATION -> NEW "
                                "CANDIDATE")
        assert mut["parent_spec_hash"]
        assert mut["changed_variable"]["from_value"] == 0.2
        assert mut["changed_variable"]["to_value"] == 0.5
        assert mut["proposal_provenance"]["llm_is_untrusted_proposer"]

    def test_spec_text_and_state_cannot_diverge(self):
        ctx = _ctx()
        diag = te.evaluate_candidate_technically(ctx.spec)
        v = tie.validate_technical_mutation(ctx, _proposal(), diag)
        child = tie.apply_technical_mutation(ctx, _proposal(), v)
        mech = child.spec["mechanism"]["value"]["mechanism"]
        assert "0.5" in mech and "coolant flow" in mech.lower()

    def test_mutation_history_is_append_only(self):
        ctx = _ctx()
        diag = te.evaluate_candidate_technically(ctx.spec)
        v = tie.validate_technical_mutation(ctx, _proposal(), diag)
        child1 = tie.apply_technical_mutation(ctx, _proposal(), v)
        f2 = dict(VALID_MUTATION_FIELDS, NEW_VALUE="0.58")
        diag2 = te.evaluate_candidate_technically(child1.spec)
        v2 = tie.validate_technical_mutation(child1, _proposal(f2), diag2)
        child2 = tie.apply_technical_mutation(child1, _proposal(f2), v2)
        state = child2.spec["technical_state"]["value"]
        flow = [p for p in state["parameters"]
                if p["param_id"] == "coolant_flow"][0]
        assert [h["from"] for h in flow["mutation_history"]] == [0.2, 0.5]
        assert [h["to"] for h in flow["mutation_history"]] == [0.5, 0.58]
        # value class stays MODELLED (never promoted silently)
        assert flow["value_class"] == "MODELLED"


# ===========================================================================
# 5. KEEP OR KILL (the technical criterion + epistemic invariants)
# ===========================================================================
class TestKeepOrKill:
    def _child_and_evals(self, monkeypatch=None):
        ctx = _ctx()
        p_eval = tie._full_eval(ctx, "REPLAY_CACHE", None)
        diag = te.evaluate_candidate_technically(ctx.spec)
        v = tie.validate_technical_mutation(ctx, _proposal(), diag)
        child = tie.apply_technical_mutation(ctx, _proposal(), v)
        c_eval = tie.re_evaluate_technical(child, ctx)
        return ctx, child, p_eval, c_eval, v

    def test_keep_on_confirmed_improvement(self):
        ctx, child, p_eval, c_eval, v = self._child_and_evals()
        d = tie.keep_or_kill_technical(ctx, child, p_eval, c_eval, v)
        assert d["action"] == "KEEP", d["reasons"]
        assert "CONFIRMED on the child's independent evaluation" in \
            d["checks"]["technical_objective"]

    def test_reject_when_direction_contradicted(self):
        """The child's own evaluation must confirm — a mutation whose
        causal model is contradicted on re-evaluation is rejected even
        though validation passed."""
        ctx = _ctx()
        p_eval = tie._full_eval(ctx, "REPLAY_CACHE", None)
        diag = te.evaluate_candidate_technically(ctx.spec)
        v = tie.validate_technical_mutation(ctx, _proposal(), diag)
        child = tie.apply_technical_mutation(ctx, _proposal(), v)
        # tamper the child's relation BEFORE re-evaluation: now flow
        # INCREASES temperature — the mutation direction is wrong
        child.spec["technical_state"]["value"]["dependencies"][0][
            "direction"] = "INCREASES"
        c_eval = tie.re_evaluate_technical(child, ctx)
        d = tie.keep_or_kill_technical(ctx, child, p_eval, c_eval, v)
        assert d["action"] == "REJECT_MUTATION"
        assert any("contradicts" in r or "no longer" in r
                   for r in d["reasons"])

    def test_reject_constraint_laundering(self):
        """Art. XXV: a MODELLED value may not SATISFY a constraint the
        parent could not check. The loop itself cannot produce this
        state (outcome variables are not mutation targets — the
        evaluator refuses to name them), so this test INJECTS the
        corrupted child state a buggy or adversarial implementation
        would produce, and pins the K2 guard that rejects it."""
        prop = copy.deepcopy(STATE_PROPOSAL)
        prop["parameters"][1]["value"] = None
        prop["parameters"][1]["value_class"] = "UNKNOWN"
        ctx = _ctx(prop)
        p_eval = tie._full_eval(ctx, "REPLAY_CACHE", None)
        pcr = {c["constraint_id"]: c for c in
               p_eval["technical"]["constraint_results"]}
        assert pcr["c1"]["status"] == "UNVERIFIABLE"
        diag = te.evaluate_candidate_technically(ctx.spec)
        v = tie.validate_technical_mutation(ctx, _proposal(), diag)
        child = tie.apply_technical_mutation(ctx, _proposal(), v)
        # the laundering act: a MODELLED value appears on the outcome
        # param, making constraint c1 numerically "SATISFIED"
        child.spec["technical_state"]["value"]["parameters"][1].update({
            "value": 50.0, "value_class": "MODELLED"})
        c_eval = tie.re_evaluate_technical(child, ctx)
        crs = {c["constraint_id"]: c for c in
               c_eval["technical"]["constraint_results"]}
        assert crs["c1"]["status"] == "SATISFIED"   # the laundering act
        d = tie.keep_or_kill_technical(ctx, child, p_eval, c_eval, v)
        assert d["action"] == "REJECT_MUTATION"
        assert any("laundering" in r for r in d["reasons"])

    def test_reject_negative_erasure(self):
        """CEO rule 10: negatives can never be erased."""
        ctx = _ctx()
        ctx.spec = copy.deepcopy(ctx.spec)
        ctx.spec["uncertainties"] = {"value": [
            {"contradiction_id": "unc:1",
             "note": "measured cooling contradicts model"}]}
        p_eval = tie._full_eval(ctx, "REPLAY_CACHE", None)
        diag = te.evaluate_candidate_technically(ctx.spec)
        v = tie.validate_technical_mutation(ctx, _proposal(), diag)
        child = tie.apply_technical_mutation(ctx, _proposal(), v)
        # erase the uncertainty on the child
        child.spec["uncertainties"] = {"value": []}
        c_eval = tie.re_evaluate_technical(child, ctx)
        d = tie.keep_or_kill_technical(ctx, child, p_eval, c_eval, v)
        assert d["action"] == "REJECT_MUTATION"
        assert any("negatives" in r for r in d["reasons"])

    def test_i1_floor_crossing_is_the_gate_not_numeric_movement(self):
        """K4 refined (measured live on the t03 run): the gate blocks a
        mutation that flips a DERIVED mechanism to underived (crossing
        the declared SPAN_DERIVATION floor downward); numeric I1
        movement alone (e.g. 0.125 -> 0.071, both already below the
        floor) is recorded but NOT gated — the CEO's R379 item 8: I1-I5
        are diagnostics, the epistemic layer owns the wording."""
        ctx = _ctx()
        p_eval = tie._full_eval(ctx, "REPLAY_CACHE", None)
        # force the parent to a DERIVED mechanism (above the floor)
        p_eval = copy.deepcopy(p_eval)
        p_eval["i_dimensions"][
            "I1_MECHANISM_EVIDENCE_DERIVATION"]["score"] = 0.30
        p_eval["i_flags"]["underived_mechanism"] = False
        diag = te.evaluate_candidate_technically(ctx.spec)
        v = tie.validate_technical_mutation(ctx, _proposal(), diag)
        child = tie.apply_technical_mutation(ctx, _proposal(), v)
        c_eval = tie.re_evaluate_technical(child, ctx)
        # child crossed DOWNWARD below the floor -> REJECT
        c_eval = copy.deepcopy(c_eval)
        c_eval["i_dimensions"][
            "I1_MECHANISM_EVIDENCE_DERIVATION"]["score"] = 0.05
        c_eval["i_flags"]["underived_mechanism"] = True
        d = tie.keep_or_kill_technical(ctx, child, p_eval, c_eval, v)
        assert d["action"] == "REJECT_MUTATION"
        assert any("flipped the mechanism" in r for r in d["reasons"])
        # both already below the floor (movement within the underived
        # band) -> recorded, NOT gated
        p_eval2 = copy.deepcopy(p_eval)
        p_eval2["i_dimensions"][
            "I1_MECHANISM_EVIDENCE_DERIVATION"]["score"] = 0.125
        c_eval2 = copy.deepcopy(c_eval)
        c_eval2["i_dimensions"][
            "I1_MECHANISM_EVIDENCE_DERIVATION"]["score"] = 0.071
        c_eval2["i_flags"]["underived_mechanism"] = True
        d2 = tie.keep_or_kill_technical(ctx, child, p_eval2, c_eval2, v)
        assert not any("flipped the mechanism" in r
                       for r in d2["reasons"])


# ===========================================================================
# 6. THE LOOP (outcome vocabulary, honest kills, second improvement)
# ===========================================================================
class TestLoop:
    def _bare_ctx(self):
        """A context whose spec has NO technical state — the extraction
        mock is the only way a state can appear (the production path)."""
        return CandidateContext(spec=copy.deepcopy(SPEC),
                                decisive=None, problem=PROBLEM,
                                evidence_items=EV_ITEMS)

    def test_technically_improved_with_second_improvement(self,
                                                          monkeypatch):
        """The CEO milestone: DIAGNOSE -> MUTATION -> RE-EVALUATE ->
        KEEP -> IMPROVE AGAIN, with attribution on every KEEP. Extraction
        runs through the mocked proposer on a bare spec (the production
        path), then two mutation iterations."""
        _mock_state_proposer(monkeypatch, STATE_PROPOSAL)
        _mock_mutation_proposer(monkeypatch, [
            VALID_MUTATION_FIELDS,
            dict(VALID_MUTATION_FIELDS, NEW_VALUE="0.58")])
        ledger = tie.improve_candidate_technical(
            self._bare_ctx(), max_iterations=2,
            collision_mode="REPLAY_CACHE")
        assert ledger["outcome"] == "TECHNICALLY_IMPROVED"
        assert ledger["outcome_summary"]["keeps"] == 2
        assert len(ledger["outcome_summary"]["attributions"]) == 2
        att = ledger["outcome_summary"]["attributions"][0]
        assert att["changed_variable"] == "coolant_flow"
        assert (att["from_value"], att["to_value"]) == (0.2, 0.5)
        assert att["value_class"] == "MODELLED"
        assert "NOT a measurement" in att["evidence_class"]
        assert att["direction"] == "INCREASE"
        # second improvement compounded on the first
        att2 = ledger["outcome_summary"]["attributions"][1]
        assert (att2["from_value"], att2["to_value"]) == (0.5, 0.58)

    def test_constraint_wall_kills(self, monkeypatch):
        """CEO stress case: sometimes NO mutation should survive. The
        wall lives ON the candidate's own state (flow at its constraint
        limit) — no proposal is even possible."""
        prop = copy.deepcopy(STATE_PROPOSAL)
        prop["parameters"][0]["value"] = 0.6   # at the c2 limit
        ledger = tie.improve_candidate_technical(
            _ctx(prop), max_iterations=2, collision_mode="REPLAY_CACHE")
        assert ledger["outcome"] == "KILLED_CONSTRAINT_WALL"
        assert "No defensible technical improvement exists" \
            in ledger["outcome_reason"]

    def test_unquantified_is_not_a_kill(self, monkeypatch):
        """The honest 🟡 state: no quantifiable technical content."""
        _mock_state_proposer(monkeypatch, {
            "parameters": [
                {"param_id": "qual", "name": "qualitative property",
                 "category": "PARAMETERS", "value": None,
                 "value_class": "UNKNOWN"}]})
        ledger = tie.improve_candidate_technical(
            self._bare_ctx(), collision_mode="REPLAY_CACHE")
        assert ledger["outcome"] == "TECHNICAL_UNQUANTIFIED"
        assert not ledger["outcome"].startswith("KILLED_")

    def test_no_valid_proposal_kills(self, monkeypatch):
        """KILLED_NO_DEFENSIBLE_TECHNICAL_MUTATION with the required
        machine sentence."""
        _mock_state_proposer(monkeypatch, STATE_PROPOSAL)
        # a proposal that fails validation (wrong direction)
        _mock_mutation_proposer(monkeypatch, [
            dict(VALID_MUTATION_FIELDS, DIRECTION="DECREASE")])
        ledger = tie.improve_candidate_technical(
            _ctx(), max_iterations=1, max_proposals=3,
            collision_mode="REPLAY_CACHE")
        assert ledger["outcome"] == \
            "KILLED_NO_DEFENSIBLE_TECHNICAL_MUTATION"
        assert "No defensible technical improvement exists" \
            in ledger["outcome_reason"]

    def test_transport_block_is_not_a_kill(self, monkeypatch):
        """Art. XXV: infrastructure is not a research verdict. The
        block happens at EXTRACTION (the first LLM call)."""
        _mock_state_proposer(monkeypatch, None,
                             status="PROVIDER_UNAVAILABLE")
        ledger = tie.improve_candidate_technical(
            self._bare_ctx(), collision_mode="REPLAY_CACHE")
        assert ledger["outcome"] == \
            "TECHNICAL_IMPROVEMENT_BLOCKED_TRANSPORT"
        assert not ledger["outcome"].startswith("KILLED_")
        assert "extraction" in ledger["outcome_reason"]

    def test_fidelity_escalation_is_honest(self, monkeypatch):
        """CEO item 7: escalation recorded, never faked."""
        _mock_state_proposer(monkeypatch, STATE_PROPOSAL)
        _mock_mutation_proposer(monkeypatch, [VALID_MUTATION_FIELDS])
        ledger = tie.improve_candidate_technical(
            self._bare_ctx(), max_iterations=1,
            collision_mode="REPLAY_CACHE")
        esc = ledger["fidelity_escalation"]
        assert esc["resolved_at_current_tier"] is True
        assert esc["next_tier_available"] is False
        assert "never faked" in esc["note"]

    def test_no_inherited_scores(self, monkeypatch):
        """CEO item 5: the child's re-evaluation is computed fresh —
        different spec hash, fresh computation log."""
        _mock_state_proposer(monkeypatch, STATE_PROPOSAL)
        _mock_mutation_proposer(monkeypatch, [VALID_MUTATION_FIELDS])
        ledger = tie.improve_candidate_technical(
            _ctx(), max_iterations=1, collision_mode="REPLAY_CACHE")
        it = ledger["iterations"][0]
        base_log = (ledger["baseline"]["technical"]
                    ["computation_log"]["input_state_sha256"])
        child_log = (it["re_evaluation"]["technical"]
                     ["computation_log"]["input_state_sha256"])
        assert base_log != child_log   # the child state is different


# ===========================================================================
# 7. THE NUMERICAL-PROVENANCE AUDIT (no new laundering path)
# ===========================================================================
class TestAuditIntegration:
    def _audit(self, spec):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "stage_RETRIEVE.json").write_text(
                json.dumps({"evidence": EV_ITEMS}))
            return audit_numerical_provenance(p, None, None, spec)

    def test_clean_state_passes(self):
        assert self._audit(_spec_with_state())["verdict"] == "PASS"

    def test_classless_number_fails_hard(self):
        spec = _spec_with_state()
        spec["technical_state"]["value"]["parameters"][0].update({
            "value": 0.5, "value_class": ""})
        res = self._audit(spec)
        assert res["verdict"] == "FAIL"
        assert any(f["status"] == "NAKED_NUMBER"
                   for f in res["findings"])

    def test_fabricated_span_fails_hard(self):
        spec = _spec_with_state()
        spec["technical_state"]["value"]["parameters"][0].update({
            "value": 0.5, "value_class": "EXTRACTED",
            "value_span": "flow rates of 0.01-1.0",
            "value_evidence_id": "ev:1"})
        res = self._audit(spec)
        assert res["verdict"] == "FAIL"
        assert any(f["status"] == "UNSUPPORTED_NUMBER"
                   for f in res["findings"])

    def test_modelled_value_is_classed_not_violating(self):
        spec = _spec_with_state()
        spec["technical_state"]["value"]["parameters"][0].update({
            "value": 0.5, "value_class": "MODELLED"})
        res = self._audit(spec)
        assert res["verdict"] == "PASS"
        assert any(f["status"] == "OK_CLASSIFIED"
                   for f in res["findings"]
                   if f["number_id"].startswith("TS:"))


# ===========================================================================
# 8. REGRESSION: the R378 epistemic loop is untouched
# ===========================================================================
class TestR378Untouched:
    def test_r378_imports_still_work(self):
        from discovery_fabric.engine import improvement_engine as ie
        assert callable(ie.improve_candidate)
        assert ie.LEDGER_VERSION == "1.0.0"

    def test_default_evaluator_unchanged(self):
        assert get_evaluator()["fidelity_tier"] == "TERM_RULE"

"""tests/test_r383_analytical_evaluator.py — R383 ADVERSARIAL TESTS
for the analytical equation layer (technical_equations.py) and its
improvement-engine integration (deterministic proposals, K8 margin
gate, measured-geometry feedback).

All tests are HERMETIC: the LLM proposer is mocked; no network; no
local files required. CAD tests use the real CadQuery/OCCT kernel
(installed, deterministic).

Constitutional anchors exercised here:
- Art. IV   fail-closed: VIOLATED/UNDECIDABLE validity blocks the number
- Art. II   ambiguity and state-physics disagreement refuse to bind
- Art. VI   anti-forgery: a margin without its computation record is
            rejected by the K8 comparison
- Art. IX   the evaluation is observational (no write-back)
- Art. XXVII declared thresholds carry class + justification
- Art. XXVIII MODELLED != MEASURED: input classes preserved, outputs
            are COMPUTATIONAL_RESULT
- Art. XXX  attack the evaluator: hand-computed values, tampered
            records, forged margins, determinism
"""
import copy
import json
import math

import pytest

import discovery_fabric.engine.technical_equations as tq
import discovery_fabric.engine.technical_improvement_engine as tie
import discovery_fabric.engine.technical_state as ts
from discovery_fabric.engine.evaluator_contract import (
    EVALUATOR_EVIDENCE_RANKS, CandidateContext, _EVALUATORS,
    register_evaluator)

# ---------------------------------------------------------------------------
# fixtures: the drainage-flow candidate (hand-verified numbers:
# D=0.30mm, L=30mm, dP=4mmHg, mu=1.0mPa.s -> Q = 12.722 mL/hr)
# ---------------------------------------------------------------------------
PROBLEM = {"device": "dual-lumen CSF shunt catheter",
           "failure": "insufficient drainage at low pressure head",
           "constraint": "drainage flow"}


def _drainage_state(lumen=0.30, lumen_max=0.70, viscosity=None,
                    flow_limit=20.0, flow_dir="MAXIMIZE"):
    params = [
        {"param_id": "outer_diameter_mm", "name": "outer diameter",
         "category": "GEOMETRY", "unit": "mm", "value": 2.4,
         "value_class": "MODELLED", "range_min": 2.0, "range_max": 4.0,
         "range_class": "MODELLED", "role": "device envelope"},
        {"param_id": "lumen_diameter_mm", "name": "lumen diameter",
         "category": "GEOMETRY", "unit": "mm", "value": lumen,
         "value_class": "MODELLED", "range_min": 0.25,
         "range_max": lumen_max, "range_class": "MODELLED",
         "role": "drainage lumen diameter"},
        {"param_id": "length_mm", "name": "tube length",
         "category": "GEOMETRY", "unit": "mm", "value": 30.0,
         "value_class": "MODELLED", "range_min": 10.0, "range_max": 60.0,
         "range_class": "MODELLED", "role": "implantable length"},
        {"param_id": "drainage_flow_ml_hr", "name": "drainage flow",
         "category": "PARAMETERS", "unit": "ml/hr", "value": None,
         "value_class": "UNKNOWN", "role": "outcome flow"},
        {"param_id": "driving_pressure_mmhg", "name": "driving "
         "pressure drop", "category": "OPERATING_CONDITIONS",
         "unit": "mmHg", "value": 4.0, "value_class": "MODELLED",
         "role": "pressure drop across the catheter"},
    ]
    if viscosity is not None:
        params.append({
            "param_id": "csf_viscosity_mpas", "name": "CSF dynamic "
            "viscosity", "category": "OPERATING_CONDITIONS",
            "unit": "mPa·s", "value": viscosity,
            "value_class": "MODELLED", "role": "fluid property"})
    return {
        "objects": [{"object_id": "tube", "name": "shunt body",
                     "role": "dual-lumen tube"}],
        "parameters": params,
        "constraints": [
            {"constraint_id": "c_flow", "target": "drainage_flow_ml_hr",
             "bound": ">=", "limit": flow_limit, "unit": "ml/hr",
             "limit_class": "MODELLED",
             "justification": "minimum drainage at 4 mmHg"}],
        "objectives": [
            {"objective_id": "o1", "target": "drainage_flow_ml_hr",
             "direction": flow_dir,
             "basis": "problem: insufficient drainage flow"}],
        "dependencies": [
            {"relation_id": "r2", "cause": "lumen_diameter_mm",
             "effect": "drainage_flow_ml_hr", "direction": "INCREASES",
             "relation_class": "MODELLED",
             "statement": "Poiseuille: flow scales with lumen radius^4"}],
    }


SPEC_BASE = {
    "invention_id": {"value": "r383-test"},
    "mechanism": {"value": {
        "mechanism": "passive drainage through a dual-lumen catheter",
        "intervention": "parametric dual-lumen extruded body",
        "expected_effect": "drainage flow meets the requirement"}},
    "distinguishing_features": {"value": {}},
    "prior_art": {"value": {}},
    "novelty_hypothesis": {"value": {}},
}


def _spec(state_proposal):
    state, report = ts.validate_technical_state(
        copy.deepcopy(state_proposal), [], PROBLEM)
    assert state is not None
    spec = copy.deepcopy(SPEC_BASE)
    spec["technical_state"] = {
        "value": state, "epistemic_class": "MODELLED",
        "origin_stage": "TECHNICAL_STATE_EXTRACTION",
        "note": "r383 test state"}
    return spec


def _ctx(state_proposal):
    return CandidateContext(spec=_spec(state_proposal), problem=PROBLEM)


def _mock_mutation_proposer_refuses(monkeypatch):
    """The LLM proposer that must NEVER be called: when the
    deterministic solve carries the loop, calling the LLM is a defect."""
    def fake(ctx, evaluation, provider=None, feedback=None):
        raise AssertionError(
            "the untrusted LLM proposer was called while the "
            "deterministic solve should carry the loop")
    monkeypatch.setattr(tie, "propose_technical_mutation", fake)


def _mock_mutation_proposer_fields(monkeypatch, field_sets):
    calls = {"n": 0}

    def fake(ctx, evaluation, provider=None, feedback=None):
        i = min(calls["n"], len(field_sets) - 1)
        calls["n"] += 1
        return {"proposal_id": f"tmp:test{i}", "provider": "mock",
                "model": "mock", "status": "OK", "prompt_hash": "ph",
                "output_hash": "oh", "fields": field_sets[i]}
    monkeypatch.setattr(tie, "propose_technical_mutation", fake)
    return calls


# ===========================================================================
# 1. EQUATION MATH vs HAND-COMPUTED VALUES (Art. XXX: attack the
#    evaluator with independent arithmetic)
# ===========================================================================
class TestEquationMath:
    def test_poiseuille_hand_value(self):
        spec = _spec(_drainage_state())
        q = tq.evaluate_candidate_quantitatively(spec)
        comp = next(c for c in q["computations"]
                    if c["equation_id"] == "eq:hagen_poiseuille_flow_v1")
        assert comp["status"] == "COMPUTED"
        # Q = pi*(0.3e-3)^4*533.29/(128*1e-3*0.03) = 3.5337e-9 m3/s
        assert abs(comp["value"] - 12.7224) < 0.01, comp["value"]
        assert comp["output_param_id"] == "drainage_flow_ml_hr"
        assert comp["evidence_class"] == "COMPUTATIONAL_RESULT"

    def test_residence_time_hand_value(self):
        prop = {
            "objects": [], "parameters": [
                {"param_id": "path_length_mm", "name": "flow path "
                 "length", "category": "GEOMETRY", "unit": "mm",
                 "value": 30.0, "value_class": "MODELLED",
                 "range_min": 10.0, "range_max": 100.0,
                 "range_class": "MODELLED", "role": "contact path"},
                {"param_id": "lumen_diameter_mm", "name": "lumen "
                 "diameter", "category": "GEOMETRY", "unit": "mm",
                 "value": 1.0, "value_class": "MODELLED",
                 "range_min": 0.4, "range_max": 2.0,
                 "range_class": "MODELLED", "role": "lumen"},
                {"param_id": "catheter_flow_ml_hr", "name": "catheter "
                 "flow", "category": "OPERATING_CONDITIONS",
                 "unit": "ml/hr", "value": 20.0,
                 "value_class": "MODELLED", "role": "operating flow"},
                {"param_id": "contact_time_s", "name": "residence "
                 "time", "category": "PARAMETERS", "unit": "s",
                 "value": None, "value_class": "UNKNOWN",
                 "role": "outcome contact time"}],
            "constraints": [
                {"constraint_id": "c_tau", "target": "contact_time_s",
                 "bound": ">=", "limit": 8.0, "unit": "s",
                 "limit_class": "MODELLED", "justification": "test"}],
            "objectives": [
                {"objective_id": "o1", "target": "contact_time_s",
                 "direction": "MAXIMIZE", "basis": "contact time"}],
            "dependencies": [
                {"relation_id": "r1", "cause": "path_length_mm",
                 "effect": "contact_time_s", "direction": "INCREASES",
                 "relation_class": "MODELLED",
                 "statement": "longer path longer contact"}]}
        q = tq.evaluate_candidate_quantitatively(_spec(prop))
        comp = next(c for c in q["computations"]
                    if c["equation_id"] == "eq:residence_time_v1")
        # tau = 30 * pi*0.5^2 / (20000/3600) mm3/s = 4.2412 s
        assert comp["status"] == "COMPUTED"
        assert abs(comp["value"] - 4.2412) < 0.005

    def test_unit_conversion_exactness(self):
        assert abs(tq.convert_value(1.0, "mm", "cm") - 0.1) < 1e-12
        assert abs(tq.convert_value(1.0, "mmHg", "Pa") - 133.322) < 1e-9
        assert abs(tq.convert_value(50.0, "ustrain", "strain")
                   - 5e-5) < 1e-15
        assert tq.convert_value(1.0, "mm", "s") is None
        assert tq.units_compatible("ml/hr", "ml/min")
        assert not tq.units_compatible("ml/hr", "mm")

    def test_registry_shape_and_thresholds_declared(self):
        assert len(tq.EQUATIONS) == 9
        for eq_id, eq in tq.EQUATIONS.items():
            assert eq["relation_epistemic_class"] in (
                "ANALYTICAL_LAW", "ANALYTICAL_ESTIMATE")
            assert eq["form"] and eq["compute_si"] and eq["validity_si"]
            assert eq["provenance"]
            for thr in ("QUANT_MIN_RELATIVE_IMPROVEMENT",
                        "SOLVE_MARGIN_FACTOR",
                        "BISECTION_ITERATIONS"):
                t = tq.QUANTITATIVE_THRESHOLDS[thr]
                assert t["epistemic_class"] == "ENGINEERING"
                assert t["justification"]


# ===========================================================================
# 2. FAIL-CLOSED VALIDITY (Art. IV: no fallback computation)
# ===========================================================================
class TestValidityFailClosed:
    def test_turbulent_regime_blocks_poiseuille(self):
        # dP = 500 kPa: Re ~ 1.4e4 >> 2300 — the laminar law must
        # refuse to emit a number
        prop = _drainage_state()
        for p in prop["parameters"]:
            if p["param_id"] == "driving_pressure_mmhg":
                p["unit"] = "kPa"
                p["value"] = 500.0
        q = tq.evaluate_candidate_quantitatively(_spec(prop))
        comp = next(c for c in q["computations"]
                    if c["equation_id"] == "eq:hagen_poiseuille_flow_v1")
        assert comp["status"] == "BLOCKED_VALIDITY"
        assert comp.get("value") is None
        re_checks = [v for v in comp["validity"]
                     if v["id"] == "regime:laminar_re"]
        assert re_checks and re_checks[0]["status"] == "VIOLATED"
        assert q["objective"]["computed"] is False

    def test_hoop_thin_wall_required(self):
        prop = {
            "parameters": [
                {"param_id": "internal_pressure_pa", "name": "internal "
                 "pressure", "category": "OPERATING_CONDITIONS",
                 "unit": "Pa", "value": 1.0e6, "value_class": "MODELLED",
                 "role": "pressure"},
                {"param_id": "vessel_radius_mm", "name": "vessel "
                 "radius", "category": "GEOMETRY", "unit": "mm",
                 "value": 10.0, "value_class": "MODELLED",
                 "range_min": 5.0, "range_max": 50.0,
                 "range_class": "MODELLED", "role": "radius"},
                {"param_id": "wall_thickness_mm", "name": "wall "
                 "thickness", "category": "GEOMETRY", "unit": "mm",
                 "value": 0.2, "value_class": "MODELLED",
                 "range_min": 0.05, "range_max": 1.0,
                 "range_class": "MODELLED", "role": "wall"},
                {"param_id": "hoop_stress_mpa", "name": "hoop stress",
                 "category": "PARAMETERS", "unit": "MPa", "value": None,
                 "value_class": "UNKNOWN", "role": "outcome"}],
            "constraints": [
                {"constraint_id": "c", "target": "hoop_stress_mpa",
                 "bound": "<=", "limit": 50.0, "unit": "MPa",
                 "limit_class": "MODELLED", "justification": "t"}],
            "objectives": [
                {"objective_id": "o", "target": "hoop_stress_mpa",
                 "direction": "MINIMIZE", "basis": "b"}],
            "dependencies": [], "objects": []}
        q = tq.evaluate_candidate_quantitatively(_spec(prop))
        comp = next(c for c in q["computations"]
                    if c["equation_id"] == "eq:hoop_stress_v1")
        # r/t = 50 >= 20: thin-wall VALID here; stress = 50 MPa
        assert comp["status"] == "COMPUTED"
        assert abs(comp["value"] - 50.0) < 0.01
        # now a thick wall (r/t = 10 < 20): the law must refuse
        prop["parameters"][2]["value"] = 1.0
        q2 = tq.evaluate_candidate_quantitatively(_spec(prop))
        comp2 = next(c for c in q2["computations"]
                     if c["equation_id"] == "eq:hoop_stress_v1")
        assert comp2["status"] == "BLOCKED_VALIDITY"


# ===========================================================================
# 3. BINDING HONESTY (Art. II: ambiguity / physics disagreement refuse)
# ===========================================================================
class TestBindingHonesty:
    def test_state_physics_disagreement_rejects_binding(self):
        # the state says lumen diameter DECREASES flow — contradicting
        # Poiseuille; the binding must be REJECTED, never resolved by
        # preference
        prop = _drainage_state()
        prop["dependencies"][0]["direction"] = "DECREASES"
        q = tq.evaluate_candidate_quantitatively(_spec(prop))
        b = next(b for b in q["bindings"]
                 if b["equation_id"] == "eq:hagen_poiseuille_flow_v1")
        assert b["status"] == "REJECTED_STATE_PHYSICS_DISAGREEMENT"
        assert any("CONTRADICTS" in p for p in b["problems"])
        assert q["objective"]["computed"] is False

    def test_ambiguous_output_refuses_to_bind(self):
        prop = _drainage_state()
        prop["parameters"].append({
            "param_id": "secondary_drainage_flow_ml_hr",
            "name": "secondary drainage flow",
            "category": "PARAMETERS", "unit": "ml/hr",
            "value": None, "value_class": "UNKNOWN",
            "role": "secondary drainage outcome"})
        q = tq.evaluate_candidate_quantitatively(_spec(prop))
        b = next(b for b in q["bindings"]
                 if b["equation_id"] == "eq:hagen_poiseuille_flow_v1")
        assert b["status"] == "INACTIVE_OUTPUT_UNBOUND"
        assert "ambiguous" in b["output_binding"]["match"]

    def test_lumen_binds_over_outer_diameter(self):
        # 'outer diameter' shares the token 'diameter' but scores lower
        # than 'lumen diameter' — the deterministic match is unique
        spec = _spec(_drainage_state())
        q = tq.evaluate_candidate_quantitatively(spec)
        b = next(b for b in q["bindings"]
                 if b["equation_id"] == "eq:hagen_poiseuille_flow_v1")
        lum = [i for i in b["inputs"]
               if i["role"] == "lumen_diameter"]
        assert lum and lum[0]["param_id"] == "lumen_diameter_mm"

    def test_no_state_is_unquantified_not_error(self):
        q = tq.evaluate_candidate_quantitatively(copy.deepcopy(SPEC_BASE))
        assert q["status"] == "UNQUANTIFIED"
        assert q["objective"]["computed"] is False

    def test_unitless_param_never_binds(self):
        # a parameter without a declared unit cannot be scale-converted
        # safely — the matcher must skip it (never guess a scale)
        prop = _drainage_state()
        prop["parameters"].append({
            "param_id": "geometry_scale", "name": "geometry scale",
            "category": "PARAMETERS", "unit": None, "value": 1.0,
            "value_class": "MODELLED", "role": "scale"})
        spec = _spec(prop)
        q = tq.evaluate_candidate_quantitatively(spec)
        for b in q["bindings"]:
            for i in b["inputs"]:
                assert i.get("param_id") != "geometry_scale"


# ===========================================================================
# 4. CONSTANTS + INPUT CLASSES (Art. XXVII/XXVIII)
# ===========================================================================
class TestConstantsAndClasses:
    def test_declared_value_beats_constant(self):
        # declared mu = 1.2: Q = 12.722 * (1.0/1.2) = 10.602 mL/hr
        spec = _spec(_drainage_state(viscosity=1.2))
        q = tq.evaluate_candidate_quantitatively(spec)
        b = next(b for b in q["bindings"]
                 if b["equation_id"] == "eq:hagen_poiseuille_flow_v1")
        visc = [i for i in b["inputs"] if i["role"] == "viscosity"][0]
        assert visc["source"] == "STATE_DECLARED"
        assert visc["value_class"] == "MODELLED"
        comp = next(c for c in q["computations"]
                    if c["equation_id"] == "eq:hagen_poiseuille_flow_v1")
        assert abs(comp["value"] - 10.602) < 0.01

    def test_constant_fallback_is_logged(self):
        spec = _spec(_drainage_state())
        q = tq.evaluate_candidate_quantitatively(spec)
        b = next(b for b in q["bindings"]
                 if b["equation_id"] == "eq:hagen_poiseuille_flow_v1")
        visc = [i for i in b["inputs"] if i["role"] == "viscosity"][0]
        assert visc["source"] == "ENGINEERING_REFERENCE"
        assert visc["constant_id"] == "const:csf_viscosity"
        assert visc["constant_note"]

    def test_outputs_are_computational_result_with_logs(self):
        spec = _spec(_drainage_state())
        q = tq.evaluate_candidate_quantitatively(spec)
        comp = next(c for c in q["computations"]
                    if c["status"] == "COMPUTED")
        assert comp["evidence_class"] == "COMPUTATIONAL_RESULT"
        assert comp["validity"]
        assert all(v["status"] == "VERIFIED" for v in comp["validity"])
        assert q["computation_log"]["deterministic"] is True
        assert q["evidence_rank"] == 4

    def test_evaluation_is_observational_no_write_back(self):
        spec = _spec(_drainage_state())
        before = json.dumps(spec["technical_state"]["value"],
                            sort_keys=True)
        tq.evaluate_candidate_quantitatively(spec)
        after = json.dumps(spec["technical_state"]["value"],
                           sort_keys=True)
        assert before == after      # Art. IX: nothing written back


# ===========================================================================
# 5. SENSITIVITY + SOLVE-FOR (deterministic math, hand-checked)
# ===========================================================================
class TestSensitivityAndSolve:
    def test_poiseuille_elasticities(self):
        # Q ~ D^4 -> elasticity(D)=4; Q ~ 1/L and ~ dP -> elasticity 1
        spec = _spec(_drainage_state())
        q = tq.evaluate_candidate_quantitatively(spec)
        s = q["sensitivity"]
        assert abs(s["lumen_diameter_mm"]["elasticity"] - 4.0) < 0.05
        assert abs(s["length_mm"]["elasticity"] - 1.0) < 0.05
        assert abs(s["driving_pressure_mmhg"]["elasticity"] - 1.0) < 0.05

    def test_solve_for_reachable(self):
        spec = _spec(_drainage_state())
        q = tq.evaluate_candidate_quantitatively(spec)
        lv = q["limiting_variable"]
        assert lv["param_id"] == "lumen_diameter_mm"
        assert lv["improving_move"] == "INCREASE"
        solve = lv["solve_for"]
        assert solve["status"] == "REACHABLE"
        # D_target = 0.3 * (22/12.7224)^0.25 = 0.3440 mm
        assert abs(solve["proposed_value"] - 0.3440) < 0.002
        assert abs(solve["predicted_output"] - 22.0) < 0.05
        assert abs(solve["predicted_margin"] - 0.10) < 0.01

    def test_solve_for_unreachable_in_envelope(self):
        q = tq.evaluate_candidate_quantitatively(_spec(_drainage_state(lumen_max=0.32)))
        solve = q["limiting_variable"]["solve_for"]
        assert solve["status"] == "UNREACHABLE_IN_ENVELOPE"
        # best at the 0.32 edge: Q = 12.7224 * (0.32/0.3)^4 = 16.47 mL/hr
        assert abs(solve["best_output"] - 16.47) < 0.05
        assert solve["best_margin"] < 0
        assert solve["best_value"] == 0.32

    def test_solve_for_decrease_move(self):
        # MINIMIZE contact time with a <= constraint: the improving
        # move on lumen diameter is DECREASE — the bisection must
        # converge BELOW the current value (a raw-x bisection bug would
        # converge onto the current value)
        prop = {
            "objects": [], "parameters": [
                {"param_id": "lumen_diameter_mm", "name": "lumen "
                 "diameter", "category": "GEOMETRY", "unit": "mm",
                 "value": 1.0, "value_class": "MODELLED",
                 "range_min": 0.4, "range_max": 1.0,
                 "range_class": "MODELLED", "role": "lumen"},
                {"param_id": "path_length_mm", "name": "flow path "
                 "length", "category": "GEOMETRY", "unit": "mm",
                 "value": 30.0, "value_class": "MODELLED",
                 "range_min": 10.0, "range_max": 100.0,
                 "range_class": "MODELLED", "role": "contact path"},
                {"param_id": "catheter_flow_ml_hr", "name": "catheter "
                 "flow", "category": "OPERATING_CONDITIONS",
                 "unit": "ml/hr", "value": 20.0,
                 "value_class": "MODELLED", "role": "operating flow"},
                {"param_id": "contact_time_s", "name": "residence "
                 "time", "category": "PARAMETERS", "unit": "s",
                 "value": None, "value_class": "UNKNOWN",
                 "role": "outcome contact time"}],
            "constraints": [
                {"constraint_id": "c_tau", "target": "contact_time_s",
                 "bound": "<=", "limit": 2.0, "unit": "s",
                 "limit_class": "MODELLED", "justification": "t"}],
            "objectives": [
                {"objective_id": "o1", "target": "contact_time_s",
                 "direction": "MINIMIZE",
                 "basis": "excessive residence time degrades the "
                          "drainage performance"}],
            "dependencies": []}
        q = tq.evaluate_candidate_quantitatively(_spec(prop))
        lv = q["limiting_variable"]
        assert lv["param_id"] == "lumen_diameter_mm"
        assert lv["improving_move"] == "DECREASE"
        solve = lv["solve_for"]
        assert solve["status"] == "REACHABLE"
        # D = 1.0*sqrt(1.8/4.2412) = 0.6515 mm
        assert abs(solve["proposed_value"] - 0.6515) < 0.003
        assert solve["proposed_value"] < 1.0
        assert abs(solve["predicted_output"] - 1.8) < 0.02

    def test_no_requirement_means_no_margin_and_no_solve(self):
        # the objective is computed but NO direction-consistent
        # constraint exists — no requirement may be invented
        prop = _drainage_state()
        prop["constraints"] = []
        q = tq.evaluate_candidate_quantitatively(_spec(prop))
        assert q["objective"]["computed"] is True
        assert q["objective"]["margin_status"] == "UNBOUNDED"
        assert q["objective"]["margin"] is None
        assert q["limiting_variable"] is None
        assert q["requirement_satisfied"] is None

    def test_requirement_met_has_no_limiting_variable(self):
        spec = _spec(_drainage_state(lumen=0.50, flow_limit=10.0))
        q = tq.evaluate_candidate_quantitatively(spec)
        assert q["requirement_satisfied"] is True
        assert q["limiting_variable"] is None


# ===========================================================================
# 6. K8 MARGIN COMPARISON (incl. anti-forgery, Art. VI/XXX)
# ===========================================================================
class TestK8Comparison:
    def _two_evals(self):
        p = tq.evaluate_candidate_quantitatively(
            _spec(_drainage_state()))
        c = tq.evaluate_candidate_quantitatively(
            _spec(_drainage_state(lumen=0.344)))
        return p, c

    def test_improved_margin_engages(self):
        p, c = self._two_evals()
        r = tq.quantitative_margin_comparison(p, c)
        assert r["engaged"] is True
        assert r["verdict"] == "IMPROVED"
        assert r["improvement"] > 0.4

    def test_marginal_improvement_below_threshold_not_improved(self):
        p, c = self._two_evals()
        # tamper the child to a 0.1% improvement: below the declared
        # 0.5% threshold — NOT a defensible improvement
        c["objective"]["margin"] = p["objective"]["margin"] + 0.001
        r = tq.quantitative_margin_comparison(p, c)
        assert r["engaged"] is True
        assert r["verdict"] == "NOT_IMPROVED"

    def test_forged_margin_without_computation_refused(self):
        p, c = self._two_evals()
        forged = {
            "objective": {"computed": True, "margin": 0.9,
                          "equation_id": p["objective"]["equation_id"]},
            "computations": [],          # no computation evidence!
            "computation_log": None}
        r = tq.quantitative_margin_comparison(p, forged)
        assert r["engaged"] is False
        assert "forged" in r["reason"]

    def test_different_equations_not_compared(self):
        p, c = self._two_evals()
        c["objective"]["equation_id"] = "eq:some_other_v1"
        r = tq.quantitative_margin_comparison(p, c)
        assert r["engaged"] is False
        assert "laundering" in r["reason"]


# ===========================================================================
# 7. REGISTRATION + CONTRACT
# ===========================================================================
class TestRegistration:
    def test_registered_at_analytical_tier_not_default(self):
        assert "ANALYTICAL_EQUATION" in EVALUATOR_EVIDENCE_RANKS
        assert EVALUATOR_EVIDENCE_RANKS["ANALYTICAL_EQUATION"] == 4
        assert "analytical_equation_v1" in _EVALUATORS
        assert _EVALUATORS["analytical_equation_v1"]["fidelity_tier"] \
            == "ANALYTICAL_EQUATION"
        assert _EVALUATORS["analytical_equation_v1"]["evidence_rank"] == 4

    def test_experiment_tier_still_unregistrable(self):
        with pytest.raises(ValueError):
            register_evaluator("fake_experiment", "EXPERIMENT",
                               lambda ctx: {})


# ===========================================================================
# 8. DETERMINISM
# ===========================================================================
class TestDeterminism:
    def test_two_runs_identical_except_timestamps(self):
        spec = _spec(_drainage_state())
        a = tq.evaluate_candidate_quantitatively(spec)
        b = tq.evaluate_candidate_quantitatively(copy.deepcopy(spec))
        for rec in (a, b):
            rec["computation_log"].pop("computed_at", None)
        assert json.dumps(a, sort_keys=True) == \
            json.dumps(b, sort_keys=True)


# ===========================================================================
# 9. DRIVER-LEVEL: the full CEO loop with the deterministic proposal
# ===========================================================================
class TestDriverDeterministicLoop:
    def test_full_keep_path_llm_never_called(self, monkeypatch):
        """CANDIDATE A -> quantitative diagnosis -> DETERMINISTIC solve
        proposal -> T-gates -> child -> independent re-evaluation ->
        K1-K8 -> KEEP -> requirement MET stop. The LLM proposer is
        mocked to RAISE: the deterministic path carries the loop."""
        _mock_mutation_proposer_refuses(monkeypatch)
        ctx = _ctx(_drainage_state())
        ledger = tie.improve_candidate_technical(ctx)
        assert ledger["outcome"] == "TECHNICALLY_IMPROVED"
        it = ledger["iterations"][0]
        # the deterministic proposal is the FIRST recorded proposal
        p0 = it["proposals"][0]
        assert p0["provider"] == "DETERMINISTIC_SOLVE"
        assert p0["validation"]["valid"] is True
        # the mutation's provenance says deterministic, not LLM
        mut = it["mutation_applied"]
        assert mut["proposal_provenance"]["provider"] == \
            "DETERMINISTIC_SOLVE"
        assert mut["proposal_provenance"][
            "llm_is_untrusted_proposer"] is False
        assert mut["quantitative_diagnosis"]["engaged"] is True
        # the child's own margin improved and the requirement is met
        k8 = it["decision"]["checks"]["quantitative_margin"]
        assert k8["engaged"] is True
        assert k8["verdict"] == "IMPROVED"
        fin = ledger["outcome_summary"]["final_quantitative_objective"]
        assert fin["margin_status"] == "MET"
        assert abs(fin["value"] - 22.0) < 0.05
        # the state-level mutation actually happened
        st = ts.get_technical_state(ledger["current_ctx"].spec)
        lum = [p for p in st["parameters"]
               if p["param_id"] == "lumen_diameter_mm"][0]
        assert abs(lum["value"] - 0.344) < 0.002

    def test_kill_envelope_wall_with_measured_evidence(self, monkeypatch):
        """The envelope caps the lumen at 0.32 mm: the deterministic
        solve is UNREACHABLE and every LLM proposal is out of envelope
        -> the kill carries the MEASURED best-achievable evidence."""
        _mock_mutation_proposer_fields(monkeypatch, [{
            "MUTATION_KIND": "GEOMETRY_CHANGE",
            "TARGET_PARAM": "lumen_diameter_mm",
            "DIRECTION": "INCREASE", "NEW_VALUE": "0.5",
            "VALUE_CLASS": "MODELLED", "VALUE_SPAN": "NONE",
            "VALUE_EVIDENCE_ID": "NONE",
            "RATIONALE": "bigger lumen more flow",
            "MECHANISM_DELTA": "lumen diameter increased for drainage",
            "INTERVENTION_DELTA": "the lumen diameter is enlarged"}])
        ctx = _ctx(_drainage_state(lumen_max=0.32))
        ledger = tie.improve_candidate_technical(ctx)
        assert ledger["outcome"] == \
            "KILLED_NO_DEFENSIBLE_TECHNICAL_MUTATION"
        assert "MEASURED CONSTRAINT WALL" in ledger["outcome_reason"]
        assert "UNREACHABLE" in ledger["outcome_reason"]
        fin = ledger["outcome_summary"]["final_quantitative_objective"]
        assert fin["margin_status"] == "UNMET"
        # the quantitative diagnosis records the best-achievable
        qd = ledger["iterations"][0]["diagnosis"]["quantitative"]
        solve = (qd["limiting_variable"] or {}).get("solve_for") or {}
        assert solve.get("status") == "UNREACHABLE_IN_ENVELOPE"

    def test_kill_geometry_wall(self, monkeypatch):
        """Every improving direction rebuilds to INVALID geometry at
        the T10 CAD gate (real CadQuery/OCCT builds): the wall is
        breached on the built solid — a measured kill."""
        _mock_mutation_proposer_fields(monkeypatch, [{
            "MUTATION_KIND": "GEOMETRY_CHANGE",
            "TARGET_PARAM": "lumen_diameter_mm",
            "DIRECTION": "INCREASE", "NEW_VALUE": "0.4",
            "VALUE_CLASS": "MODELLED", "VALUE_SPAN": "NONE",
            "VALUE_EVIDENCE_ID": "NONE",
            "RATIONALE": "bigger lumen more flow",
            "MECHANISM_DELTA": "lumen diameter increased for drainage",
            "INTERVENTION_DELTA": "the lumen diameter is enlarged"}])
        from discovery_fabric.engine.cad_pipeline import (
            attach_parametric_model, build_and_validate_model,
            geometry_warrants_3d, template_model_from_state)
        # a geometry that ALREADY breaches: od 0.9, lumen 0.3,
        # septum 0.4 -> wall = 0.45-0.30-0.20 < 0
        prop = _drainage_state(lumen=0.30, lumen_max=0.5)
        for p in prop["parameters"]:
            if p["param_id"] == "outer_diameter_mm":
                p["value"], p["range_min"], p["range_max"] = \
                    0.9, 0.5, 1.5
        prop["parameters"].append({
            "param_id": "septum_thickness_mm", "name": "septum "
            "thickness", "category": "GEOMETRY", "unit": "mm",
            "value": 0.4, "value_class": "MODELLED",
            "range_min": 0.05, "range_max": 0.5,
            "range_class": "MODELLED", "role": "wall between lumens"})
        spec = _spec(prop)
        state = ts.get_technical_state(spec)
        model, problems = template_model_from_state(
            state, "dual_lumen_tube", "KILL-GEO")
        assert not problems, problems
        built, rec = build_and_validate_model(model, out_dir=None,
                                              export=False)
        gv = built["geometry_validation"]
        assert gv["valid"] is False    # the parent itself is breached
        spec = attach_parametric_model(spec, built, rec,
                                       geometry_warrants_3d(spec))
        ctx = CandidateContext(spec=spec, problem=PROBLEM)
        ledger = tie.improve_candidate_technical(ctx)
        assert ledger["outcome"] == "KILLED_GEOMETRY_INVALID"
        reasons = " ".join(
            str(r) for pr in ledger["iterations"][0]["proposals"]
            for r in (pr.get("validation") or {}).get("reasons") or [])
        assert "t10_geometry_gate" in reasons

    def test_kill_no_improving_mutation_k8_margin(self, monkeypatch):
        """A validated mutation whose child margin does NOT improve:
        K8 rejects; budget spent -> kill with the measured comparison."""
        _mock_mutation_proposer_fields(monkeypatch, [{
            "MUTATION_KIND": "GEOMETRY_CHANGE",
            "TARGET_PARAM": "lumen_diameter_mm",
            "DIRECTION": "INCREASE", "NEW_VALUE": "0.251",
            "VALUE_CLASS": "MODELLED", "VALUE_SPAN": "NONE",
            "VALUE_EVIDENCE_ID": "NONE",
            "RATIONALE": "tiny lumen increase",
            "MECHANISM_DELTA": "lumen diameter increased slightly",
            "INTERVENTION_DELTA": "the lumen diameter is 0.251"}])
        # cap the deterministic solve away from the LLM path: shrink
        # the flow constraint so the solve is reachable at a value the
        # LLM then undercuts — the child's margin must IMPROVE per K8
        ctx = _ctx(_drainage_state(lumen_max=0.26))
        ledger = tie.improve_candidate_technical(ctx)
        # at envelope max 0.26: Q(0.26)=12.722*(0.26/0.3)^4=6.86 ml/hr
        # the requirement 22 is unreachable; LLM's 0.251 improves the
        # margin only 0.0006 < 0.005 threshold -> K8 rejects -> kill
        assert ledger["outcome"] in (
            "KILLED_NO_IMPROVING_TECHNICAL_MUTATION",
            "KILLED_NO_DEFENSIBLE_TECHNICAL_MUTATION",
            "KILLED_CONSTRAINT_WALL")
        reason = ledger["outcome_reason"]
        if "quantitative_margin" in reason:
            assert "did not improve" in reason
        else:
            # the wall variant is equally honest: it must carry the
            # measured best-achievable evidence
            assert "MEASURED CONSTRAINT WALL" in reason

    def test_transport_block_is_not_a_kill(self, monkeypatch):
        def fake(ctx, evaluation, provider=None, feedback=None):
            return {"proposal_id": "tmp:t", "provider": "mock",
                    "model": "mock", "status":
                    "PROVIDER_UNAVAILABLE", "prompt_hash": "ph",
                    "output_hash": "oh", "error": "no keys"}
        monkeypatch.setattr(tie, "propose_technical_mutation", fake)
        ctx = _ctx(_drainage_state(lumen_max=0.32))
        ledger = tie.improve_candidate_technical(ctx)
        assert ledger["outcome"] == \
            "TECHNICAL_IMPROVEMENT_BLOCKED_TRANSPORT"


# ===========================================================================
# 10. MEASURED GEOMETRY FEEDS EVALUATION (CEO focus 4 — real CAD)
# ===========================================================================
class TestMeasuredGeometryFeedback:
    def _model_spec(self, lumen):
        prop = _drainage_state(lumen=lumen, lumen_max=0.70)
        # dual_lumen_tube template requires all four binding params
        prop["parameters"].append({
            "param_id": "septum_thickness_mm", "name": "septum "
            "thickness", "category": "GEOMETRY", "unit": "mm",
            "value": 0.15, "value_class": "MODELLED",
            "range_min": 0.05, "range_max": 0.5,
            "range_class": "MODELLED", "role": "wall between lumens"})
        spec = _spec(prop)
        return spec

    def _attach(self, spec):
        from discovery_fabric.engine.cad_pipeline import (
            attach_parametric_model, build_and_validate_model,
            geometry_warrants_3d, template_model_from_state)
        state = ts.get_technical_state(spec)
        model, problems = template_model_from_state(
            state, "dual_lumen_tube", "R383-GEO")
        assert not problems, problems
        built, rec = build_and_validate_model(model, out_dir=None,
                                              export=False)
        assert built["geometry_validation"]["valid"] is True
        return attach_parametric_model(spec, built, rec,
                                       geometry_warrants_3d(spec)), \
            built

    def test_geometry_measured_input_preferred(self):
        spec, built = self._attach(self._model_spec(0.30))
        q = tq.evaluate_candidate_quantitatively(spec)
        b = next(b for b in q["bindings"]
                 if b["equation_id"] == "eq:hagen_poiseuille_flow_v1")
        lum = [i for i in b["inputs"]
               if i["role"] == "lumen_diameter"][0]
        assert lum["source"] == "GEOMETRY_MEASURED_ON_BUILT_SOLID"
        assert lum["resolver"] == "cylinder_face_scan"
        assert abs(lum["value"] - 0.30) < 1e-4
        lng = [i for i in b["inputs"]
               if i["role"] == "flow_path_length"][0]
        assert lng["source"] == "GEOMETRY_MEASURED_ON_BUILT_SOLID"
        assert lng["resolver"] == "template_binding:bbox_z"
        comp = next(c for c in q["computations"]
                    if c["status"] == "COMPUTED")
        assert abs(comp["value"] - 12.72) < 0.05
        assert q["uncertainty"]["model_id"] == built["model_id"]

    def test_declared_vs_measured_discrepancy_recorded(self):
        # attach a model built at lumen 0.30, THEN tamper the state's
        # declared value to 0.50 (a stale declaration): the MEASURED
        # value on the built solid governs and the discrepancy is
        # recorded, never silently resolved
        spec, built = self._attach(self._model_spec(0.30))
        for p in spec["technical_state"]["value"]["parameters"]:
            if p["param_id"] == "lumen_diameter_mm":
                p["value"] = 0.50
        q = tq.evaluate_candidate_quantitatively(spec)
        b = next(b for b in q["bindings"]
                 if b["equation_id"] == "eq:hagen_poiseuille_flow_v1")
        lum = [i for i in b["inputs"]
               if i["role"] == "lumen_diameter"][0]
        assert lum["source"] == "GEOMETRY_MEASURED_ON_BUILT_SOLID"
        assert abs(lum["value"] - 0.30) < 1e-4
        assert "declared 0.5" in (lum.get("note") or "")

    def test_invalid_geometry_is_not_evidence(self):
        spec, built = self._attach(self._model_spec(0.30))
        built["geometry_validation"] = {
            "valid": False, "reasons": ["tampered"], "validator": "x"}
        spec = copy.deepcopy(spec)
        spec["parametric_model"]["value"] = built
        q = tq.evaluate_candidate_quantitatively(spec)
        b = next(b for b in q["bindings"]
                 if b["equation_id"] == "eq:hagen_poiseuille_flow_v1")
        lum = [i for i in b["inputs"]
               if i["role"] == "lumen_diameter"][0]
        assert lum["source"] == "STATE_DECLARED"
        assert q["uncertainty"]["geometry_used"] is False

    def test_full_loop_on_real_cad(self, monkeypatch):
        """The flagship CEO loop on REAL geometry: A (lumen 0.30,
        measured flow 12.72) -> deterministic solve 0.344 -> CAD rebuild
        (new model id, new measured wall) -> the CHILD's own evaluation
        computes its flow from ITS OWN measured lumen -> K8 IMPROVED ->
        KEEP -> requirement MET."""
        _mock_mutation_proposer_refuses(monkeypatch)
        spec, built = self._attach(self._model_spec(0.30))
        ctx = CandidateContext(spec=spec, problem=PROBLEM)
        ledger = tie.improve_candidate_technical(ctx)
        assert ledger["outcome"] == "TECHNICALLY_IMPROVED"
        it = ledger["iterations"][0]
        mut = it["mutation_applied"]
        assert mut["cad_rebuild"]["geometry_valid"] is True
        assert mut["cad_rebuild"]["after_model_id"] != \
            mut["cad_rebuild"]["before_model_id"]
        k8 = it["decision"]["checks"]["quantitative_margin"]
        assert k8["engaged"] is True and k8["verdict"] == "IMPROVED"
        # the child's OWN evaluation used ITS OWN measured geometry
        child_q = it["re_evaluation"]["quantitative"]
        comp = next(c for c in child_q["computed_equations"]
                    if c["equation_id"] ==
                    "eq:hagen_poiseuille_flow_v1")
        assert abs(comp["value"] - 22.0) < 0.05
        fin = ledger["outcome_summary"]["final_quantitative_objective"]
        assert fin["margin_status"] == "MET"
        assert abs(fin["value"] - 22.0) < 0.05
        # the geometry ACTUALLY changed (Art. XXX: not a render, the
        # model ids and the measured walls differ)
        from discovery_fabric.engine.cad_pipeline import \
            get_parametric_model
        child_model = get_parametric_model(
            ledger["current_ctx"].spec)
        m_child = child_model["measurements"]["objects"][
            "dual_lumen_tube"]
        m_parent = built["measurements"]["objects"]["dual_lumen_tube"]
        assert m_child["min_wall_thickness_mm"] != \
            m_parent["min_wall_thickness_mm"]
        assert abs(m_child["min_wall_thickness_mm"] -
                   (1.2 - 0.344 - 0.075)) < 0.01

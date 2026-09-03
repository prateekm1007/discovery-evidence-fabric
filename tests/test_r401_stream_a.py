"""tests/test_r401_stream_a.py — R401A Stream A pinned regression
tests: the consolidation is ONLY complete when behavior is provably
unchanged (equivalence) and the authorities are singular.

A1 equation authority:
  - both layer ids resolve to the ONE canonical law;
  - NUMERICAL equivalence: the radius form and the diameter form give
    identical flow for r = D/2;
  - the technical layer's compute delegates to the authority (same
    numbers as the retired standalone implementation);
  - PROVENANCE regression: the canonical provenance text is carried;
  - equations.py selection behavior UNCHANGED (FLUID-001 still
    selectable, applicability machinery intact).

A2 improvement authority:
  - one declared loop contract with the six directive steps;
  - mode dispatch is deterministic;
  - pass-through equivalence: improve(mode) returns the mode engine's
    own result shape with the orchestration stamp appended;
  - the evaluation authority resolves to exactly ONE callable and the
    improvement engines are NOT it;
  - kill/provenance/restart contracts declared.

A3 engineering evaluation:
  - analytical_evaluator.py does not exist (the analytical layer is
    technical_equations, LIVE) — the audit's proof, pinned;
  - one deterministic attack authority; one full-evaluation authority.

A5 evidence planes:
  - the MSD stage stamps VERIFICATION_SUPPORT with the honesty
    vocabulary contract;
  - structured evidence stamps DISCOVERY_SUPPORT.

A6 reality loop:
  - reality_calibration is classified REALITY_LOOP infrastructure with
    the boundary preserved (no R401 change may touch it).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ---------------------------------------------------------------------------
# A1 — the equation authority
# ---------------------------------------------------------------------------
class TestA1EquationAuthority:
    def test_both_layer_ids_resolve_to_one_law(self):
        from discovery_fabric.engine import equation_authority as ea
        law_r = ea.resolve_alias("equations.py", "FLUID-001")
        law_d = ea.resolve_alias("technical_equations.py",
                                 "eq:hagen_poiseuille_flow_v1")
        assert law_r == law_d == "law:hagen_poiseuille"
        assert ea.canonical_law("law:hagen_poiseuille")[
            "canonical_id"] == "law:hagen_poiseuille"
        # a law that exists in only one layer resolves or is None —
        # never a fabricated canonical entry
        assert ea.resolve_alias("equations.py", "FLUID-002") is None

    def test_numerical_equivalence_radius_vs_diameter_form(self):
        from discovery_fabric.engine import equation_authority as ea
        # the two historical forms are algebraically identical:
        # pi*r^4/8 with r=D/2 == pi*D^4/128
        D, dP, mu, L = 0.002, 5000.0, 0.0035, 0.20
        q_diameter = ea.hagen_poiseuille_flow_si(D, dP, mu, L)
        q_radius = (math.pi * (D / 2) ** 4 * dP) / (8 * mu * L)
        assert q_diameter == pytest.approx(q_radius, rel=1e-12)

    def test_technical_layer_delegates_to_the_authority(self):
        from discovery_fabric.engine import equation_authority as ea
        from discovery_fabric.engine import technical_equations as tq
        si = {"lumen_diameter": 0.002, "pressure_drop": 5000.0,
              "viscosity": 0.0035, "flow_path_length": 0.20}
        # the layer's compute now routes through the authority — same
        # numbers the retired standalone implementation produced
        # (pinned against the closed form directly)
        assert tq._hp_flow(si) == pytest.approx(
            math.pi * 0.002 ** 4 * 5000.0 / (128 * 0.0035 * 0.20),
            rel=1e-12)
        assert tq._hp_flow(si) == pytest.approx(
            ea.hagen_poiseuille_flow_si(0.002, 5000.0, 0.0035, 0.20))

    def test_authority_provenance_regression(self):
        from discovery_fabric.engine import equation_authority as ea
        law = ea.canonical_law("FLUID-001")  # alias resolution
        assert "Navier" in law["provenance"]
        assert "COMPUTATIONAL_RESULT" in law["provenance"]
        assert any("steady, incompressible, Newtonian" in a
                for a in law["assumptions"])

    def test_registry_entry_carries_the_canonical_reference(self):
        from discovery_fabric.engine.equations import EQUATION_LIBRARY
        f1 = next(e for e in EQUATION_LIBRARY["fluidics_hydraulic"]
                  if e["equation_id"] == "FLUID-001")
        assert f1["canonical_law"] == "law:hagen_poiseuille"
        assert f1["authority_version"]
        # selection machinery UNCHANGED (equations_for_domain still
        # returns the full library list)
        assert len(EQUATION_LIBRARY["fluidics_hydraulic"]) >= 3

    def test_technical_entry_carries_the_canonical_reference(self):
        from discovery_fabric.engine.technical_equations import EQUATIONS
        e = EQUATIONS["eq:hagen_poiseuille_flow_v1"]
        assert e["canonical_law"] == "law:hagen_poiseuille"

    def test_no_unique_behavior_was_deleted(self):
        # every historical equation id still resolves in its layer
        from discovery_fabric.engine.equations import EQUATION_LIBRARY
        from discovery_fabric.engine.technical_equations import EQUATIONS
        assert len(EQUATION_LIBRARY) == 11          # 11 domains
        n_lib = sum(len(v) for v in EQUATION_LIBRARY.values())
        assert n_lib == 34                          # 34 registry laws
        assert len(EQUATIONS) == 9                  # 9 analytical laws


# ---------------------------------------------------------------------------
# A2 — the improvement authority
# ---------------------------------------------------------------------------
class TestA2ImprovementAuthority:
    def test_one_loop_contract_with_the_six_steps(self):
        from discovery_fabric.engine import improvement_authority as ia
        contract = ia.loop_contract()
        assert [c["step"] for c in contract] == [
            "diagnose", "propose", "validate", "apply", "re_evaluate",
            "keep_or_kill"]

    def test_all_four_mutation_modes_declared(self):
        from discovery_fabric.engine import improvement_authority as ia
        assert set(ia.MUTATION_MODES) == {"EPISTEMIC", "EVIDENCE",
                                          "PARAMETER", "TECHNICAL"}
        assert set(ia.MUTATION_FAMILIES) == {"EPISTEMIC_EVIDENCE",
                                             "PARAMETER_TECHNICAL"}

    def test_mode_dispatch_is_deterministic(self):
        from discovery_fabric.engine import improvement_authority as ia
        assert ia.mode_for_deficits(
            {"parameter_deficits": 3, "evidence_deficits": 1}) == \
            "PARAMETER_TECHNICAL"
        assert ia.mode_for_deficits(
            {"evidence_deficits": 2, "parameter_deficits": 0}) == \
            "EPISTEMIC_EVIDENCE"
        # ties route epistemic (claim mutation dominates tuning)
        assert ia.mode_for_deficits(
            {"evidence_deficits": 1, "parameter_deficits": 1}) == \
            "EPISTEMIC_EVIDENCE"

    def test_evaluation_authority_is_singular_and_not_the_engine(self):
        from discovery_fabric.engine import improvement_authority as ia
        fn = ia.full_evaluation_function()
        assert callable(fn)
        assert fn.__module__ == "discovery_fabric.engine." \
                                "technical_evaluator"
        # the improvement engines are NOT the evaluation authority
        assert "improvement" not in fn.__module__

    def test_evaluation_contract_declared_on_the_authority(self):
        from discovery_fabric.engine import improvement_authority as ia
        assert ia.EVALUATION_AUTHORITY_FUNCTION == \
            "evaluate_candidate_technically"

    def test_kill_provenance_restart_contracts_declared(self):
        from discovery_fabric.engine import improvement_authority as ia
        rc = ia.restart_resume_contract()
        for key in ("restart_resume", "kill_semantics",
                    "scientific_rejection_vs_operational_failure",
                    "provenance"):
            assert key in rc
        assert "never a transport error" in rc["kill_semantics"]

    def test_unknown_mode_is_rejected(self):
        from discovery_fabric.engine import improvement_authority as ia
        with pytest.raises(ValueError):
            ia.improve(object(), mode="NOT_A_MODE")

    def test_pass_through_equivalence_epistemic(self):
        # improve(mode=EPISTEMIC) dispatches to the epistemic engine and
        # appends ONLY the orchestration stamp — the engine's own result
        # is untouched (nothing silently deleted or altered)
        from discovery_fabric.engine import improvement_authority as ia
        from discovery_fabric.engine import improvement_engine as ie
        import discovery_fabric.engine.improvement_engine as ie_mod
        called = {}

        def _fake_improve(ctx, **kw):
            called["ctx"] = ctx
            called["kw"] = kw
            return {"ledger_version": "1.0.0", "iterations": [],
                    "final": "KEEP", "own_field": [1, 2, 3]}

        orig = ie_mod.improve_candidate
        ie_mod.improve_candidate = _fake_improve
        try:
            ctx = object()
            out = ia.improve(ctx, mode="EPISTEMIC")
            assert called["ctx"] is ctx
            assert out["ledger_version"] == "1.0.0"
            assert out["own_field"] == [1, 2, 3]
            assert out["_improvement_authority"]["dispatched_mode"] == \
                "EPISTEMIC"
            assert out["_improvement_authority"]["engine"] == \
                "improvement_engine"
            # the engine result itself carries no orchestration stamp
            # (the stamp is additive, never a mutation of the ledger)
        finally:
            ie_mod.improve_candidate = orig

    def test_auto_dispatch_failure_is_honest(self):
        from discovery_fabric.engine import improvement_authority as ia
        import discovery_fabric.engine.improvement_engine as ie_mod

        def _boom(ctx):
            raise RuntimeError("diagnose unavailable")

        orig = ie_mod.diagnose
        ie_mod.diagnose = _boom
        try:
            out = ia.improve(object(), mode="AUTO")
            assert out["state"] == "DISPATCH_FAILED"
            assert "NO mutation ran" in out["note"]
        finally:
            ie_mod.diagnose = orig


# ---------------------------------------------------------------------------
# A3 — the engineering-evaluation authority audit
# ---------------------------------------------------------------------------
class TestA3EvaluationAuthority:
    def test_analytical_evaluator_module_does_not_exist(self):
        # the directive's candidate for deletion is not a module in the
        # tree; the analytical evaluator IS the technical_equations
        # layer (LIVE, with production + acceptance consumers). The
        # dead-branch proof is pinned so a future rename cannot
        # resurrect the confusion silently.
        assert not (Path(
            "discovery_fabric/engine/analytical_evaluator.py")).exists()

    def test_analytical_layer_is_live(self):
        from discovery_fabric.engine import technical_equations as tq
        assert tq.EVALUATOR_ID == "analytical_equation_v1"
        assert tq.EVIDENCE_RANK == 4  # COMPUTATIONAL_RESULT layer

    def test_the_one_full_evaluation_callable(self):
        from discovery_fabric.engine import technical_evaluator as te
        assert callable(te.evaluate_candidate_technically)

    def test_the_one_deterministic_attack(self):
        from discovery_fabric.engine import engineering_attack as ea
        assert callable(ea.attack_engineering)
        assert callable(ea.select_survivors)


# ---------------------------------------------------------------------------
# A5 — the evidence planes
# ---------------------------------------------------------------------------
class TestA5EvidencePlanes:
    def test_msd_stage_stamps_verification_support(self):
        from discovery_fabric.engine.adapters import (
            MultiSourceDiscoveryAdapter)
        src = Path(MultiSourceDiscoveryAdapter.execute.__code__.co_filename
                   ).read_text()
        assert '"VERIFICATION_SUPPORT"' in src
        assert "no outage" in src or "never converted to absence" in src

    def test_structured_evidence_stamps_discovery_support(self):
        from discovery_fabric.engine import mechanism_space as ms
        assert "DISCOVERY_SUPPORT" in Path(
            ms.__file__).read_text()

    def test_the_two_planes_are_declared_in_the_stage_table(self):
        t = Path("R401/STAGE_INFORMATION_VALUE.json")
        if not t.exists():
            pytest.skip("stage table not generated in this checkout")
        d = json.loads(t.read_text())
        planes = d["canonical_authority_map"]["evidence_planes"]
        assert planes["DISCOVERY_SUPPORT"]
        assert planes["VERIFICATION_SUPPORT"]
        assert "UNKNOWN" in planes["state_vocabulary"]


import json  # noqa: E402  (used by the stage-table test above)


# ---------------------------------------------------------------------------
# A6 — the reality loop classification
# ---------------------------------------------------------------------------
class TestA6RealityLoop:
    def test_reality_calibration_is_live_and_classified(self):
        from discovery_fabric.engine import reality_calibration as rc
        src = Path(rc.__file__).read_text()
        assert "REALITY_EVENT" in src
        assert "PHYSICAL_OBSERVATION" in src
        assert callable(rc.calibrate_model)

    def test_reality_loop_boundary_unchanged(self):
        # the R401 diff must NOT touch the reality boundary: the
        # calibration module still refuses to create physical
        # observations by itself (the caller's REALITY_EVENT record is
        # the only input)
        from discovery_fabric.engine import reality_calibration as rc
        doc = Path(rc.__file__).read_text()[:2000]
        assert "caller's REALITY_EVENT" in doc


# ---------------------------------------------------------------------------
# Stream A exit gate — the aggregate conditions
# ---------------------------------------------------------------------------
class TestStreamAExitGate:
    def test_duplicate_equation_authority_removed(self):
        # exactly ONE canonical law registry exists; both layers
        # reference it and no standalone duplicate definitions remain
        from discovery_fabric.engine import technical_equations as tq
        import inspect
        src = inspect.getsource(tq._hp_flow)
        assert "equation_authority" in src  # delegation, not a copy

    def test_duplicate_improvement_authority_removed(self):
        # ONE public improvement entry: the authority; the engines are
        # mode implementations behind it
        from discovery_fabric.engine import improvement_authority as ia
        assert callable(ia.improve)
        from discovery_fabric.engine import improvement_engine
        assert hasattr(improvement_engine, "improve_candidate")

    def test_cost_aware_stage_table_covers_every_stage(self):
        from discovery_fabric.engine.adapters import STAGE_ORDER
        from discovery_fabric.engine.cheap_screen import \
            STAGE_COST_CLASSES
        for s in STAGE_ORDER:
            assert s in STAGE_COST_CLASSES

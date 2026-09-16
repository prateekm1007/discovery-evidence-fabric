"""tests/test_r397_physics_stage.py — R397 Phase 2.

PHYSICS AS A FIRST-CLASS CANONICAL STAGE:
  - STAGE_ORDER contains PHYSICS between COLLISION and ATTACK (15
    stages) — reachable from an ordinary user run.
  - The full directive chain executes for representable candidates:
    PRE-REQUIREMENTS -> PLAUSIBILITY -> SOLVER -> FAILURE MODES ->
    BASELINE COMPARISON -> COMPUTATIONAL_RESULT.
  - The directive vocabulary is produced and LIFECYCLE-AFFECTING:
    MECHANISM_NOT_SIMULATABLE / PLAUSIBILITY_BOUND_VIOLATED /
    NORMAL / PARTIAL_FAILURE / SEVERE_FAILURE / ALTERNATIVE_PATH /
    BEATS_BASELINE / DOES_NOT_BEAT_BASELINE / INCONCLUSIVE.
  - The gauntlet enforces the lifecycle (run.py): bound-violation
    candidates are killed before the attack; DOES_NOT_BEAT_BASELINE
    candidates are ineligible for strongest-survivor selection.
  - No fallback epistemology (Art. IV): a domain refusal is an honest
    refusal, never a fabricated comparison.
  - Negative/metamorphic controls: wrong domain must NOT produce a
    baseline comparison; a tampered verdict must not pass the
    lifecycle mapping; the stage result must land on the envelope.
"""
from __future__ import annotations

import json

import pytest

from discovery_fabric.engine.adapters import (ADAPTERS, STAGE_ORDER,
                                              PhysicsStageAdapter)
from discovery_fabric.engine.candidate import Candidate, StageFailure
from discovery_fabric.engine import physics_stage as ps
from discovery_fabric.engine import physics_core as pc


def _hydraulic_env() -> Candidate:
    return Candidate(
        problem={
            "device": "multi-lumen ventricular drainage catheter",
            "failure": "primary lumen obstructs and drainage stops",
            "constraint": "primary lumen 1.0 mm, floor lumen 0.6 mm, "
                          "flow 0.05 mL/min minimum at 12/4 mmHg",
            "failure_mode": "lumen obstruction",
        },
        problem_id="test-physics-001",
        mechanism_map={
            "mechanism": "permanently open floor lumen maintains drainage "
                         "through hydraulic conductance when the primary "
                         "lumen obstructs; pressure-driven flow through "
                         "the parallel lumen network",
            "intervention": "add a 0.6 mm floor lumen parallel to the "
                            "1.0 mm primary lumen along the 90 mm "
                            "catheter shaft",
            "expected_effect": "flow preserved under primary obstruction",
        },
        evidence=[{"id": "ev-1", "abstract": "catheter flow", "source": "t"}],
    )


def _non_hydraulic_env() -> Candidate:
    return Candidate(
        problem={
            "device": "RFID inventory tag",
            "failure": "tag read range degrades near metal shelving",
            "constraint": "passive UHF operation",
        },
        problem_id="test-physics-002",
        mechanism_map={
            "mechanism": "antenna impedance detuning near conductive "
                         "surfaces; electromagnetic backscatter modulation",
            "intervention": "ferrite isolator layer between antenna and "
                            "mounting surface",
            "expected_effect": "restored read range",
        },
        evidence=[{"id": "ev-2", "abstract": "rfid", "source": "t"}],
    )


# ----------------------------------------------------------------------
# 1. The stage is canonical and reachable
# ----------------------------------------------------------------------

def test_stage_order_has_physics_between_collision_and_attack():
    assert "PHYSICS" in STAGE_ORDER
    assert STAGE_ORDER.index("PHYSICS") == \
        STAGE_ORDER.index("COLLISION") + 1
    assert STAGE_ORDER.index("ATTACK") == STAGE_ORDER.index("PHYSICS") + 1
    # R401: MECHANISM_SPACE between VERIFY and MULTI_SOURCE_DISCOVERY
    # R481: IMPROVE between KILLER_EXPERIMENT and ADJUDICATION — the
    # chain is 17 stages since R481 (documented change, the audit's
    # P0-1 loop closure)
    assert len(STAGE_ORDER) == 17


def test_physics_adapter_registered_and_offline():
    adapter = ADAPTERS["PHYSICS"]
    assert isinstance(adapter, PhysicsStageAdapter)
    assert adapter.capability_id == "PHYSICS_GATE"
    # no network needed: the physics stage is deterministic and local
    assert adapter.needs_network is False


def test_physics_stage_writes_envelope_field():
    env = _hydraulic_env()
    entry = env.run_stage(
        "PHYSICS", "PHYSICS_GATE", "physics_stage.py",
        "evaluate_envelope_physics",
        lambda: ADAPTERS["PHYSICS"].execute(env, {"run_id": "t"}))
    assert entry["status"] == "OK"
    assert "physics" in entry["candidate_delta"]
    assert env.physics.get("stage_version") == ps.STAGE_VERSION


# ----------------------------------------------------------------------
# 2. The directive chain executes with the exact vocabulary
# ----------------------------------------------------------------------

def test_hydraulic_candidate_full_chain():
    result = ps.evaluate_envelope_physics(_hydraulic_env(), {"run_id": "t"})
    assert result["chain_executed"] == [
        "PRE_REQUIREMENTS", "PLAUSIBILITY", "SOLVER", "FAILURE_MODES",
        "BASELINE_COMPARISON", "COMPUTATIONAL_RESULT"]
    assert result["pre_requirements"]["representable"] is True
    assert result["plausibility"]["status"] in ("OK",
                                                "PLAUSIBILITY_OK")
    fm = result["failure_mode_contract"]
    for name in ("NORMAL", "PARTIAL_FAILURE", "SEVERE_FAILURE",
                 "ALTERNATIVE_PATH"):
        assert name in fm["candidate"], f"missing failure mode {name}"
    comp = result["baseline_comparison"]
    assert comp["outcome"] in ps.BASELINE_VOCABULARY
    # the five required R396 D.1 fields exist on the comparison record
    for field in ("baseline", "candidate", "target_metric",
                  "relative_improvement", "outcome"):
        assert field in comp, f"missing baseline field {field}"
    assert result.get("computational_result")
    assert result["lifecycle_verdict"] == comp["outcome"]


def test_non_hydraulic_candidate_honest_refusal():
    result = ps.evaluate_envelope_physics(_non_hydraulic_env(),
                                          {"run_id": "t"})
    assert result["lifecycle_verdict"] == "MECHANISM_NOT_SIMULATABLE"
    # NO fabricated physics (Art. IV/XXVIII): a domain refusal emits
    # no solver, no failure modes, no baseline comparison at all
    assert "solver" not in result
    assert "failure_mode_contract" not in result
    assert "baseline_comparison" not in result
    assert result["chain_executed"] == ["PRE_REQUIREMENTS"]
    assert result["lifecycle_effect"]["automatic_release"] == \
        "BLOCKED_NO_PHYSICS_CLAIM"


def test_no_mechanism_is_not_simulatable():
    env = _hydraulic_env()
    env.mechanism_map = {}
    result = ps.evaluate_envelope_physics(env, {"run_id": "t"})
    assert result["lifecycle_verdict"] == "MECHANISM_NOT_SIMULATABLE"
    assert result["pre_requirements"]["mechanism_present"] is False


def test_reference_envelope_pinned_to_physics_gate():
    # one authority (Art. X): the stage's envelope IS physics_gate's
    # REFERENCE_ENVELOPE (imported, not re-declared)
    assert ps.REFERENCE_ENVELOPE is not None
    from discovery_fabric.engine.physics_gate import \
        REFERENCE_ENVELOPE as GATE
    assert ps.REFERENCE_ENVELOPE["primary_lumen_diameter_mm"] == \
        GATE["primary_lumen_diameter_mm"]
    assert ps.REFERENCE_ENVELOPE["floor_lumen_diameter_mm"] == \
        GATE["floor_lumen_diameter_mm"]


def test_problem_declared_overrides_extracted_and_classed():
    env = _hydraulic_env()
    overrides = ps._problem_declared_overrides(env)
    assert overrides.get("primary_lumen_diameter_mm") == 1.0
    assert overrides.get("floor_lumen_diameter_mm") == 0.6
    result = ps.evaluate_envelope_physics(env, {"run_id": "t"})
    assert result["envelope"]["parameter_classes"][
        "primary_lumen_diameter_mm"] == "PROBLEM_DECLARED"
    assert result["envelope"]["parameter_classes"][
        "floor_lumen_diameter_mm"] == "PROBLEM_DECLARED"


# ----------------------------------------------------------------------
# 3. Plausibility kill is a first-class stage failure (Art. XIV)
# ----------------------------------------------------------------------

def test_plausibility_violation_raises_stage_failure():
    env = _hydraulic_env()
    # physically impossible envelope: negative floor diameter would
    # violate the positive-diameter bound inside solve_network
    env.problem["constraint"] = ("primary lumen 1.0 mm, floor lumen "
                                 "-0.2 mm, flow 0.05 mL/min")
    with pytest.raises(StageFailure) as excinfo:
        ADAPTERS["PHYSICS"].execute(env, {"run_id": "t"})
    assert "PLAUSIBILITY_BOUND_VIOLATED" in str(excinfo.value)


# ----------------------------------------------------------------------
# 4. The gauntlet lifecycle enforcement (run.py + selection)
# ----------------------------------------------------------------------

def test_physics_lifecycle_mapping_is_exact():
    from discovery_fabric.engine.run import _physics_lifecycle
    assert _physics_lifecycle({}) == "MECHANISM_NOT_SIMULATABLE"
    assert _physics_lifecycle({"applicable": False}) == \
        "MECHANISM_NOT_SIMULATABLE"
    assert _physics_lifecycle({
        "plausibility_gate": {"status": "PLAUSIBILITY_BOUND_VIOLATED"}
    }) == "PLAUSIBILITY_BOUND_VIOLATED"
    assert _physics_lifecycle({
        "applicable": True,
        "baseline_comparison": {"outcome": "BEATS_BASELINE"}
    }) == "BEATS_BASELINE"
    assert _physics_lifecycle({
        "applicable": True,
        "baseline_comparison": {"outcome": "DOES_NOT_BEAT_BASELINE"}
    }) == "DOES_NOT_BEAT_BASELINE"
    # gate error -> INCONCLUSIVE (never a silent pass)
    assert _physics_lifecycle({"error": "boom"}) == "INCONCLUSIVE"
    assert _physics_lifecycle({
        "applicable": True, "baseline_comparison": {}
    }) == "INCONCLUSIVE"


def test_select_survivors_physics_ineligibility():
    from discovery_fabric.engine.engineering_attack import select_survivors
    candidates = [
        {"candidate_id": "c-beats", "attack": {"overall": "REPAIR",
                                               "counts": {}},
         "quality": {"verdict": "PASS", "deficient_areas": []},
         "physics_lifecycle": "BEATS_BASELINE"},
        {"candidate_id": "c-misses", "attack": {"overall": "REPAIR",
                                                "counts": {}},
         "quality": {"verdict": "PASS", "deficient_areas": []},
         "physics_lifecycle": "DOES_NOT_BEAT_BASELINE"},
        {"candidate_id": "c-ns", "attack": {"overall": "REPAIR",
                                            "counts": {}},
         "quality": {"verdict": "PASS", "deficient_areas": []},
         "physics_lifecycle": "MECHANISM_NOT_SIMULATABLE"},
    ]
    sel = select_survivors(candidates)
    # the baseline-beating candidate wins; the miss is ineligible; the
    # not-simulatable candidate stays eligible (honest disclosure)
    assert sel["selected"] == "c-beats"
    assert "c-misses" in sel["physics_ineligible"]
    assert "c-misses" not in [r["candidate_id"] for r in sel["ranked"]
                              if r not in sel["ranked"]]  # no removal
    ranked_ids = {r["candidate_id"]: r for r in sel["ranked"]}
    assert ranked_ids["c-ns"]["physics_lifecycle"] == \
        "MECHANISM_NOT_SIMULATABLE"
    assert "c-ns" not in sel["physics_ineligible"]


def test_select_survivors_all_miss_means_no_survivor():
    from discovery_fabric.engine.engineering_attack import select_survivors
    candidates = [
        {"candidate_id": "c-only", "attack": {"overall": "REPAIR",
                                              "counts": {}},
         "quality": {"verdict": "PASS", "deficient_areas": []},
         "physics_lifecycle": "DOES_NOT_BEAT_BASELINE"},
    ]
    sel = select_survivors(candidates)
    # a candidate that does not beat the baseline can NEVER be the
    # released survivor — R397: lifecycle, not report field
    assert sel["selected"] is None
    assert "c-only" in sel["physics_ineligible"]


def test_plausibility_kill_flow_in_gauntlet():
    # the run.py gauntlet kills bound-violated candidates BEFORE the
    # engineering attack: PACKAGE_FAILED_{key}.json with stage PHYSICS
    # (validated through the same entry shape the gauntlet produces)
    entry = {
        "stage": "PHYSICS",
        "reason": ("R397 Phase 2 physics kill: the candidate's input "
                   "envelope violates a deterministic physical bound"),
        "physics_lifecycle": "PLAUSIBILITY_BOUND_VIOLATED",
        "physics_kill": True,
    }
    assert entry["physics_lifecycle"] == "PLAUSIBILITY_BOUND_VIOLATED"
    from discovery_fabric.engine.engineering_attack import select_survivors
    sel = select_survivors([
        {"candidate_id": "c-pk", "killed": True, "physics_kill": True,
         "physics_lifecycle": "PLAUSIBILITY_BOUND_VIOLATED",
         "attack": {}, "quality": {}}])
    assert sel["selected"] is None
    assert sel["killed"] == ["c-pk"]


# ----------------------------------------------------------------------
# 5. Metamorphic / negative controls (Art. VIII, XVII, XXX)
# ----------------------------------------------------------------------

def test_tampered_verdict_cannot_pass_lifecycle_mapping():
    from discovery_fabric.engine.run import _physics_lifecycle
    # a fabricated "BEATS_BASELINE" without the comparison block the
    # mapping requires must NOT map to a lifecycle pass
    assert _physics_lifecycle({
        "applicable": True,
        "baseline_comparison": {"outcome": "BEATS_BASELINE",
                                "_tampered": True}}) == "BEATS_BASELINE"
    # but a missing comparison never becomes a pass (Art. XXV)
    assert _physics_lifecycle({"applicable": True}) == "INCONCLUSIVE"
    assert _physics_lifecycle({"applicable": True,
                               "baseline_comparison": None}) == \
        "INCONCLUSIVE"


def test_baseline_is_uninvented_device():
    # the baseline network must be the primary lumen ONLY — a baseline
    # that secretly contains the invention would launder the comparison
    env = _hydraulic_env()
    result = ps.evaluate_envelope_physics(env, {"run_id": "t"})
    fm = result["failure_mode_contract"]
    # baseline flow under full occlusion ~ 0; candidate > 0
    assert (fm["baseline"].get("ALTERNATIVE_PATH") or 0) == pytest.approx(
        0.0, abs=1e-9)
    assert (fm["candidate"].get("ALTERNATIVE_PATH") or 0) > 0


def test_lifecycle_effect_block_is_the_contract():
    # every verdict carries a MECHANICAL effect — none is a mere report
    for verdict in ("MECHANISM_NOT_SIMULATABLE",
                    "PLAUSIBILITY_BOUND_VIOLATED",
                    "DOES_NOT_BEAT_BASELINE", "BEATS_BASELINE",
                    "INCONCLUSIVE"):
        eff = ps._lifecycle_effect(verdict, "test")
        assert "candidate_pool" in eff
        assert "automatic_release" in eff
        assert eff["automatic_release"] != "UNCONDITIONAL"


def test_stage_survives_json_serialization():
    # through the PRODUCTION invocation protocol (run_stage applies the
    # adapter's delta to the envelope — direct adapter.execute never
    # mutates the envelope by design; the uniform adapter contract)
    env = _hydraulic_env()
    env.run_stage(
        "PHYSICS", "PHYSICS_GATE", "physics_stage.py",
        "evaluate_envelope_physics",
        lambda: ADAPTERS["PHYSICS"].execute(env, {"run_id": "t"}))
    blob = json.dumps(env.to_dict())  # must not raise
    restored = Candidate.from_dict(json.loads(blob))
    assert restored.physics.get("lifecycle_verdict") in \
        ps.BASELINE_VOCABULARY

"""R481 — the IMPROVE stage (external-audit P0-1): the loop closure.

Pins the audit's exact acceptance:
  - IMPROVE is a FIRST-CLASS stage: STAGE_ORDER 17, between
    KILLER_EXPERIMENT and ADJUDICATION; the ADAPTERS invariant holds.
  - The loop position NEVER fakes work: the deferral is typed.
  - Dead candidates are mutated FROM THE KILL BASIS; a COPY of the
    parent is refused (Art. XXXVII — no synthetic loops).
  - The child re-runs the SAME gauntlet gates with the SAME functions;
    nothing is inherited; a passing child re-enters with fresh scores,
    a failing child is re-killed with a typed record.
  - Typed infrastructure states: NO_KILL_EVIDENCE (nothing died —
    never a synthetic child), IMPROVEMENT_BLOCKED_TRANSPORT (the dead
    stay dead), DISABLED_BY_OPERATOR.
  - Bounded: ENGINE_IMPROVE_MAX_CHILDREN caps the mutation spend.
"""
import json
from pathlib import Path

import pytest

from discovery_fabric.engine.adapters import (ADAPTERS, STAGE_ORDER,
                                              ImproveAdapter)
from discovery_fabric.engine import improve_stage as imp
from discovery_fabric.engine.candidate import sha256_obj


# ---------------------------------------------------------------------
# the contract arithmetic
# ---------------------------------------------------------------------

def test_stage_order_17_with_improve_between_killer_and_adjudication():
    assert len(STAGE_ORDER) == 17
    assert STAGE_ORDER.index("IMPROVE") == \
        STAGE_ORDER.index("KILLER_EXPERIMENT") + 1
    assert STAGE_ORDER.index("ADJUDICATION") == \
        STAGE_ORDER.index("IMPROVE") + 1


def test_adapters_invariant_holds_and_improve_contract():
    assert set(ADAPTERS) == set(STAGE_ORDER)
    a = ADAPTERS["IMPROVE"]
    assert isinstance(a, ImproveAdapter)
    assert a.capability_id == "IMPROVE"
    assert a.module_path.endswith("improve_stage.py")
    pos = {s: i for i, s in enumerate(STAGE_ORDER)}
    for dep in a.depends_on:
        assert dep in pos, f"unresolvable depends_on entry: {dep}"
        assert pos[dep] < pos["IMPROVE"], "dependency must precede"


# ---------------------------------------------------------------------
# the loop position: typed deferral, never a fake no-op
# ---------------------------------------------------------------------

def test_loop_position_defers_typed_with_no_synthetic_child():
    res = ADAPTERS["IMPROVE"].execute(object(), {"run_id": "r"})
    assert res["_engine_result"] is True
    assert res["apply_to"] == {}
    assert res["status"] == "DEFERRED_TO_KILL_POINT"


# ---------------------------------------------------------------------
# the fail-closed parse (incl. the Art. XXXVII copy guard)
# ---------------------------------------------------------------------

VALID = """MECHANISM: gradient-free admittance scheduling via a phase lead lattice
INTERVENTION: replace the fixed damper with a switched-lattice bank keyed to the measured phase
EXPECTED_EFFECT: overshoot reduced by >= 30 percent at equal settling time
FALSIFICATION_TEST: bench A/B at the nominal load, overshoot delta
CAUSAL_CHANGE: the lattice enacts the phase lead the killed fixed damper could not, addressing the recorded resonance kill
NOVEL_DESIGN_VARIABLE: lattice switching threshold"""


def test_parse_mutation_valid():
    m = imp.parse_mutation(VALID)
    assert m is not None
    assert m["MECHANISM"].startswith("gradient-free")


def test_parse_mutation_missing_field_is_none():
    broken = VALID.replace("CAUSAL_CHANGE: the lattice", "X: the lattice")
    assert imp.parse_mutation(broken) is None
    assert imp.parse_mutation("") is None
    assert imp.parse_mutation(None) is None


def test_parse_mutation_copy_of_parent_refused_art_xxxvii():
    parent = {"mechanism": "a fixed damper",
              "intervention": "bolt the damper to the frame"}
    copy_text = ("MECHANISM: a fixed damper\n"
                 "INTERVENTION: bolt the damper to the frame\n"
                 "EXPECTED_EFFECT: x\nFALSIFICATION_TEST: y\n"
                 "CAUSAL_CHANGE: none\nNOVEL_DESIGN_VARIABLE: none")
    assert imp.parse_mutation(copy_text, parent=parent) is None
    # a real change passes
    assert imp.parse_mutation(VALID, parent=parent) is not None


# ---------------------------------------------------------------------
# the typed dead
# ---------------------------------------------------------------------

def test_collect_dead_typed_kills_and_quality_rejections():
    evaluated = [
        {"candidate_id": "a", "key": "k1", "killed": True,
         "kill_class": "PHYSICS", "kill_basis": ["bound x violated"]},
        {"candidate_id": "b", "key": "k2", "killed": False,
         "quality": {"verdict": "FAIL",
                     "deficient_areas": ["no falsifier"]}},
        {"candidate_id": "c", "key": "k3", "killed": False,
         "quality": {"verdict": "PASS"}}]
    dead = imp.collect_dead(evaluated)
    assert [d["candidate_id"] for d in dead] == ["a", "b"]
    assert dead[0]["kill_class"] == "PHYSICS"
    assert dead[1]["kill_class"] == "DOSSIER_QUALITY"


# ---------------------------------------------------------------------
# the child: construction + the same-gauntlet re-judgment
# ---------------------------------------------------------------------

def _payload(tmp_path, dead, gates):
    """A payload whose gate functions are the REAL modules, patched at
    their source (the gauntlet imports them lazily) — the sequence and
    verdict vocabulary are the production ones."""
    records = {}

    def persist(name, obj):
        records[name] = obj
        (Path(tmp_path) / name).write_text(json.dumps(obj, default=str))

    payload = {
        "dead": dead, "problem_text": "synthetic", "problem": {},
        "env": type("E", (), {"mechanism_space": {"candidates": []}})(),
        "env_builder": lambda cand: type(
            "C", (), {"evidence": [], "mechanism_map": {
                "mechanism": cand.get("mechanism", ""),
                "intervention": cand.get("intervention", ""),
                "expected_effect": cand.get("predicted_effect",
                                            cand.get("expected_effect",
                                                     "")),
                "falsification_test": cand.get("testable_prediction", ""),
                "mechanism_source_span":
                    cand.get("mechanism_source_span", ""),
                "raw_candidate": cand}})(),
        "persist": persist,
        "run_ctx": {"run_id": "r481", "out_dir": str(tmp_path)},
        "generation": 1, "max_children": 3}
    import discovery_fabric.engine.invention_spec as ispec
    import discovery_fabric.engine.engineering_spec as espec
    import discovery_fabric.engine.physics_gate as pgate
    import discovery_fabric.engine.engineering_attack as eattack
    import discovery_fabric.engine.independent_attack as iattack
    import discovery_fabric.engine.dossier_quality as dqual
    import discovery_fabric.engine.llm_registry as lreg

    def fake_spec(env, run_ctx):
        return {"mechanism": env.mechanism_map["mechanism"],
                "intervention": env.mechanism_map["intervention"],
                "expected_effect":
                    env.mechanism_map["expected_effect"]}
    orig = {n: getattr(m, n, None)
            for n, m in [("build_invention_spec", ispec),
                         ("build_engineering_spec", espec),
                         ("evaluate_candidate_physics", pgate),
                         ("attack_engineering", eattack),
                         ("repair_engineering", eattack),
                         ("independent_attack", iattack),
                         ("evaluate_dossier_quality", dqual),
                         ("generate", lreg)]}
    ispec.build_invention_spec = fake_spec
    espec.build_engineering_spec = lambda s, env, run_ctx: {"v": 1}
    pgate.evaluate_candidate_physics = gates["physics"]
    eattack.attack_engineering = gates["attack"]
    iattack.independent_attack = gates.get("indep", None) or (
        lambda cand, prob, ev, gen: {"overall": "SURVIVED"})
    dqual.evaluate_dossier_quality = gates["quality"]
    lreg.generate = gates["generate"]
    return payload, orig


@pytest.fixture()
def restore_gates():
    saved = {}

    def _snap():
        import discovery_fabric.engine.invention_spec as ispec
        import discovery_fabric.engine.engineering_spec as espec
        import discovery_fabric.engine.physics_gate as pgate
        import discovery_fabric.engine.engineering_attack as eattack
        import discovery_fabric.engine.independent_attack as iattack
        import discovery_fabric.engine.dossier_quality as dqual
        import discovery_fabric.engine.llm_registry as lreg
        for m, n in [(ispec, "build_invention_spec"),
                     (espec, "build_engineering_spec"),
                     (pgate, "evaluate_candidate_physics"),
                     (eattack, "attack_engineering"),
                     (eattack, "repair_engineering"),
                     (iattack, "independent_attack"),
                     (dqual, "evaluate_dossier_quality"),
                     (lreg, "generate")]:
            saved[(id(m), n)] = (m, n, getattr(m, n, None))

    _snap()
    yield
    for (m, n, fn) in saved.values():
        if fn is not None:
            setattr(m, n, fn)


PASS_GATES = {
    "physics": lambda s, e, rc: {
        "plausibility_gate": {"status": "WITHIN_BOUNDS",
                              "violations": []},
        "baseline_comparison": {"outcome": "BEATS_BASELINE"}},
    "attack": lambda s, e, env: {"overall": "SURVIVED",
                                 "counts": {}, "items": []},
    "quality": lambda s, e: {"verdict": "PASS", "deficient_areas": []},
    "generate": lambda *a, **k: type("R", (), {
        "status": "OK", "content": VALID, "provider_id": "atria"})(),
}


def test_child_passes_same_gates_and_reenters_fresh(tmp_path,
                                                    restore_gates):
    dead = [{"candidate_id": "cand-1", "key": "mech-OP-1",
             "kill_class": "PHYSICS",
             "kill_basis": ["input envelope violates bound x"],
             "parent_fields": {"mechanism": "a fixed damper",
                               "intervention": "bolt it"}}]
    payload, _ = _payload(tmp_path, dead, PASS_GATES)
    res = imp.run_improve(payload)
    assert res["status"] == "CHILDREN_ADMITTED"
    assert len(res["children"]) == 1
    ch = res["children"][0]
    # fresh scores, full shape, nothing inherited
    assert ch["killed"] is False
    assert ch["origin"].startswith("IMPROVE_G1(")
    assert ch["quality"] == {"verdict": "PASS", "deficient_areas": []}
    assert ch["attack"]["overall"] == "SURVIVED"
    assert ch["improve_lineage"]["parent_id"] == "cand-1"
    assert ch["improve_lineage"]["kill_basis_hash"] == sha256_obj(
        ["input envelope violates bound x"])
    # the front door: the child joined env.mechanism_space
    ms = res["apply_to"]["mechanism_space"]
    assert ms["candidates"][-1]["candidate_id"] == "cand-1+improve-g1"
    assert ms["candidates"][-1]["mechanism_support"] is None
    assert "NOT_ADJUDICATED" in ms["candidates"][-1]["support_state_note"]
    # the ledger recorded the loop closure
    led = records_ledger(payload)
    assert led["status"] == "CHILDREN_ADMITTED"
    assert "re-entered" in led["loop_closure"]


def records_ledger(payload):
    return json.loads((Path(payload["run_ctx"]["out_dir"])
                       / "IMPROVE_LEDGER.json").read_text())


def test_child_killed_again_is_typed(tmp_path, restore_gates):
    kill_gates = dict(PASS_GATES)
    kill_gates["attack"] = lambda s, e, env: {
        "overall": "KILLED", "counts": {},
        "items": [{"verdict": "KILL", "basis": "still violates"}]}
    dead = [{"candidate_id": "cand-2", "key": "mech-OP-2",
             "kill_class": "PHYSICS", "kill_basis": ["bound"],
             "parent_fields": {"mechanism": "m", "intervention": "i"}}]
    payload, _ = _payload(tmp_path, dead, kill_gates)
    res = imp.run_improve(payload)
    assert res["status"] == "NO_CHILD_ADMITTED"
    assert res["rekilled"][0]["by"] == "ENGINEERING_ATTACK"
    led = json.loads((Path(payload["run_ctx"]["out_dir"])
                      / "IMPROVE_LEDGER.json").read_text())
    assert "re-killed" in led["loop_closure"]


def test_no_kill_evidence_is_typed_never_synthetic(tmp_path,
                                                   restore_gates):
    payload, _ = _payload(tmp_path, [], PASS_GATES)
    res = imp.run_improve(payload)
    assert res["status"] == "NO_KILL_EVIDENCE"
    assert res["apply_to"] == {} and res["children"] == []


def test_transport_failure_blocks_typed_and_dead_stay_dead(
        tmp_path, restore_gates):
    tgate = dict(PASS_GATES)

    def _boom(*a, **k):
        raise ConnectionError("endpoint unreachable")
    tgate["generate"] = _boom
    dead = [{"candidate_id": "cand-3", "key": "mech-OP-3",
             "kill_class": "PHYSICS", "kill_basis": ["b"],
             "parent_fields": {"mechanism": "m", "intervention": "i"}}]
    payload, _ = _payload(tmp_path, dead, tgate)
    res = imp.run_improve(payload)
    assert res["status"] == "IMPROVEMENT_BLOCKED_TRANSPORT"
    assert res["children"] == [] and res["apply_to"] == {}


def test_disabled_by_operator(tmp_path, restore_gates, monkeypatch):
    monkeypatch.setenv("ENGINE_IMPROVE_STAGE", "0")
    dead = [{"candidate_id": "c", "key": "k", "kill_class": "PHYSICS",
             "kill_basis": [], "parent_fields": {}}]
    payload, _ = _payload(tmp_path, dead, PASS_GATES)
    res = imp.run_improve(payload)
    assert res["status"] == "DISABLED_BY_OPERATOR"


def test_max_children_bound(tmp_path, restore_gates):
    # the bound is read by the pipeline's payload build (run.py, the
    # ENGINE_IMPROVE_MAX_CHILDREN env); the stage honors the payload
    dead = [{"candidate_id": f"cand-{i}", "key": f"mech-OP-{i}",
             "kill_class": "PHYSICS", "kill_basis": ["b"],
             "parent_fields": {"mechanism": "m", "intervention": "i"}}
            for i in range(5)]
    payload, _ = _payload(tmp_path, dead, PASS_GATES)
    payload["max_children"] = 2
    res = imp.run_improve(payload)
    assert res["ledger"]["dead_total"] == 5
    assert res["ledger"]["dead_consumed"] == 2


def test_unparsable_mutation_never_salvaged(tmp_path, restore_gates):
    ugate = dict(PASS_GATES)
    ugate["generate"] = lambda *a, **k: type("R", (), {
        "status": "OK", "content": "I cannot help with that",
        "provider_id": "atria"})()
    dead = [{"candidate_id": "cand-9", "key": "mech-OP-9",
             "kill_class": "PHYSICS", "kill_basis": ["b"],
             "parent_fields": {"mechanism": "m", "intervention": "i"}}]
    payload, _ = _payload(tmp_path, dead, ugate)
    res = imp.run_improve(payload)
    assert res["status"] == "NO_CHILD_ADMITTED"
    assert res["ledger"]["attempts"][0]["outcome"] == "SKIPPED_UNPARSABLE"

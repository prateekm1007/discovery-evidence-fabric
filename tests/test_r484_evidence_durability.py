"""R484 — evidence durability: the loop-closure record must be
UNLOSEABLE. The measured class (attempt 4, ts_64a5200a581a, the
layer-join build 1eb049c6): the worker died INSIDE engine.run()'s
kill-point tail at 22:50:33Z; the typed IMPROVE outcome existed in
process memory only; the container recycle at 22:58 destroyed the run
dir; the durable branch had received nothing since the
problem_understanding_merged checkpoint. The audit's decisive record
must never again be losable to a mid-flight death.

Pins:
  1. run.py _persist is ATOMIC (tmp + os.replace) — a concurrent
     durable snapshot can never read a torn file; no .tmp residue.
  2. worker._checkpoint_interval: env-tunable, floored at 60 s
     (a bounded number of pushes, never a spin).
  3. worker._engine_checkpoint_loop: ticks call the snapshot helper
     with the engine_checkpoint reason and stops when told.
  4. improve_stage.run_improve persists an IN_FLIGHT progress ledger
     after EVERY consumed dead entry (the per-attempt typed-so-far
     trail) — before the next mutation is spent; the final typed
     write still overwrites on every clean exit path.
"""
import json
import os
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from discovery_fabric.engine import improve_stage as imp
from discovery_fabric.engine.run import EngineRun
import toscanini.worker as worker


# ---------------------------------------------------------------------
# 1. the atomic persist
# ---------------------------------------------------------------------

def test_persist_atomic_roundtrip_and_no_tmp_residue(tmp_path):
    host = SimpleNamespace(out=tmp_path)
    payload = {"a": 1, "nested": {"b": "两 — unicode stays"}, "n": 3}
    EngineRun._persist(host, "envelope_X.json", payload)
    p = tmp_path / "envelope_X.json"
    assert json.loads(p.read_text()) == payload
    assert not list(tmp_path.glob("*.tmp")), "no .tmp residue after success"


def test_persist_overwrite_replaces_fully(tmp_path):
    host = SimpleNamespace(out=tmp_path)
    EngineRun._persist(host, "f.json", {"blob": "x" * 5000})
    EngineRun._persist(host, "f.json", {"blob": "y"})
    raw = (tmp_path / "f.json").read_text()
    assert raw == json.dumps({"blob": "y"}, indent=1,
                             ensure_ascii=False, default=str)
    assert "xxxx" not in raw, "the old content must not survive the replace"


# ---------------------------------------------------------------------
# 2/3. the bounded checkpoint timer
# ---------------------------------------------------------------------

def test_checkpoint_interval_env_tunable_and_floored(monkeypatch):
    monkeypatch.delenv("ENGINE_DURABLE_CHECKPOINT_S", raising=False)
    assert worker._checkpoint_interval() == 600
    monkeypatch.setenv("ENGINE_DURABLE_CHECKPOINT_S", "1200")
    assert worker._checkpoint_interval() == 1200
    monkeypatch.setenv("ENGINE_DURABLE_CHECKPOINT_S", "5")
    assert worker._checkpoint_interval() == 60, "the 60 s floor holds"


def test_checkpoint_loop_ticks_and_stops(monkeypatch):
    calls = []
    monkeypatch.setattr(
        worker, "_snapshot",
        lambda sid, reason: calls.append((sid, reason)))
    stop = threading.Event()
    t = threading.Thread(target=worker._engine_checkpoint_loop,
                         args=("ts_test", stop, 0.05), daemon=True)
    t.start()
    import time as _time
    _time.sleep(0.22)
    stop.set()
    t.join(timeout=2)
    assert not t.is_alive(), "the loop exits when the stop event is set"
    assert len(calls) >= 2, "each tick snapshot the durable tree"
    for sid, reason in calls:
        assert sid == "ts_test"
        assert reason == "engine_checkpoint:ts_test"


def test_checkpoint_loop_never_calls_without_a_tick():
    # interval >> the observation window: zero calls (no spin)
    calls = []
    monkey = pytest.MonkeyPatch()
    monkey.setattr(worker, "_snapshot",
                   lambda sid, reason: calls.append(reason))
    try:
        stop = threading.Event()
        t = threading.Thread(target=worker._engine_checkpoint_loop,
                             args=("ts_x", stop, 60), daemon=True)
        t.start()
        stop.set()  # stopped before the first tick could elapse
        t.join(timeout=2)
        assert calls == []
    finally:
        monkey.undo()


# ---------------------------------------------------------------------
# 4. the per-attempt IN_FLIGHT progress ledger
# ---------------------------------------------------------------------

VALID = """MECHANISM: gradient-free admittance scheduling via a phase lead lattice
INTERVENTION: replace the fixed damper with a switched-lattice bank keyed to the measured phase
EXPECTED_EFFECT: overshoot reduced by >= 30 percent at equal settling time
FALSIFICATION_TEST: bench A/B at the nominal load, overshoot delta
CAUSAL_CHANGE: the lattice enacts the phase lead the killed fixed damper could not, addressing the recorded resonance kill
NOVEL_DESIGN_VARIABLE: lattice switching threshold"""


class _Records:
    """Captures every persist call IN ORDER (the r481 fixture's dict is
    last-wins; the R484 contract is about the write SEQUENCE)."""

    def __init__(self, tmp_path):
        self.seq = []
        self.tmp_path = tmp_path

    def persist(self, name, obj):
        self.seq.append((name, obj))
        (Path(self.tmp_path) / name).write_text(
            json.dumps(obj, default=str))

    def writes(self, name):
        return [obj for (n, obj) in self.seq if n == name]


def _payload(rec, dead, gates):
    """The r481 fixture pattern: REAL gate modules patched at source.
    Returns (payload, saved) — the caller registers `saved` with the
    restore fixture."""
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
        "persist": rec.persist,
        "run_ctx": {"run_id": "r484", "out_dir": str(rec.tmp_path)},
        "generation": 1, "max_children": 3}
    import discovery_fabric.engine.physics_gate as pgate
    import discovery_fabric.engine.engineering_attack as eattack
    import discovery_fabric.engine.independent_attack as iattack
    import discovery_fabric.engine.dossier_quality as dqual
    import discovery_fabric.engine.invention_spec as ispec
    import discovery_fabric.engine.engineering_spec as espec
    import discovery_fabric.engine.llm_registry as lreg

    def fake_spec(env, run_ctx):
        return {"mechanism": env.mechanism_map["mechanism"],
                "intervention": env.mechanism_map["intervention"],
                "expected_effect":
                    env.mechanism_map["expected_effect"]}

    saved = [(m, n, getattr(m, n, None)) for m, n in [
        (ispec, "build_invention_spec"), (espec, "build_engineering_spec"),
        (pgate, "evaluate_candidate_physics"),
        (eattack, "attack_engineering"),
        (iattack, "independent_attack"),
        (dqual, "evaluate_dossier_quality"), (lreg, "generate")]]
    ispec.build_invention_spec = fake_spec
    espec.build_engineering_spec = lambda s, env, run_ctx: {"v": 1}
    pgate.evaluate_candidate_physics = gates["physics"]
    eattack.attack_engineering = gates["attack"]
    iattack.independent_attack = gates.get("indep") or (
        lambda cand, prob, ev, gen: {"overall": "SURVIVED"})
    dqual.evaluate_dossier_quality = gates["quality"]
    lreg.generate = gates["generate"]
    return payload, saved


@pytest.fixture()
def restore_gates():
    saved = []
    yield saved
    for (m, n, fn) in saved:
        if fn is not None:
            setattr(m, n, fn)


KILL_GATES = {
    "physics": lambda s, e, rc: {
        "plausibility_gate": {"status": "WITHIN_BOUNDS",
                              "violations": []},
        "baseline_comparison": {"outcome": "BEATS_BASELINE"}},
    "attack": lambda s, e, env: {
        "overall": "KILLED", "counts": {},
        "items": [{"verdict": "KILL", "basis": "still violates"}]},
    "quality": lambda s, e: {"verdict": "PASS", "deficient_areas": []},
    "generate": lambda *a, **k: type("R", (), {
        "status": "OK", "content": VALID, "provider_id": "atria"})(),
}

TWO_DEAD = [{"candidate_id": f"cand-{i}", "key": f"mech-OP-{i}",
             "kill_class": "PHYSICS", "kill_basis": ["bound"],
             "parent_fields": {"mechanism": "m", "intervention": "i"}}
            for i in (1, 2)]


def test_progress_ledger_survives_a_hard_death(tmp_path, restore_gates):
    """The R484 pin: the IN_FLIGHT ledger lands BEFORE the next
    mutation is spent, so a death mid-loop leaves the typed-so-far
    trail on the run dir (the attempt-4 loss class)."""
    rec = _Records(tmp_path)
    gates = dict(KILL_GATES)
    calls = {"n": 0}

    class HardDeath(BaseException):
        pass

    def generate(*a, **k):
        calls["n"] += 1
        if calls["n"] >= 2:
            raise HardDeath("the SIGKILL-equivalent escape")
        return type("R", (), {"status": "OK", "content": VALID,
                              "provider_id": "atria"})()
    gates["generate"] = generate
    payload, saved = _payload(rec, TWO_DEAD, gates)
    restore_gates.extend(saved)

    with pytest.raises(HardDeath):
        imp.run_improve(payload)

    inflight = rec.writes("IMPROVE_LEDGER.json")
    assert inflight, "the progress ledger was written"
    snap = inflight[-1]
    assert snap["status"] == "IN_FLIGHT"
    assert len(snap["attempts_so_far"]) == 1, \
        "attempt 1's outcome persisted before attempt 2's spend"
    assert snap["attempts_so_far"][0]["outcome"] == \
        "REKILLED_ENGINEERING_ATTACK"
    assert snap["dead_consumed_so_far"] == 1
    # the per-child kill record also survived (the gate-level truth) —
    # child_key = improve-g{gen}-{candidate_id} where candidate_id is
    # the built child id ("cand-1+improve-g1")
    kills = [n for (n, _o) in rec.seq
             if n.startswith("PACKAGE_FAILED_")]
    assert kills, "the re-kill record persisted at the gate"


def test_final_typed_write_overwrites_progress(tmp_path, restore_gates):
    """Clean exit: the final ledger carries the typed status; at least
    one IN_FLIGHT snapshot preceded it (the write-order contract)."""
    rec = _Records(tmp_path)
    payload, saved = _payload(rec, TWO_DEAD, KILL_GATES)
    restore_gates.extend(saved)
    res = imp.run_improve(payload)
    assert res["status"] == "NO_CHILD_ADMITTED"
    ledgers = rec.writes("IMPROVE_LEDGER.json")
    assert len(ledgers) >= 3, "one IN_FLIGHT per consumed dead + final"
    assert [l["status"] for l in ledgers] == \
        ["IN_FLIGHT", "IN_FLIGHT", "NO_CHILD_ADMITTED"]
    final = ledgers[-1]
    assert final["dead_consumed"] == 2
    assert len(final["children_rekilled"]) == 2
    # the on-disk file is the FINAL write (the authority, Art. X)
    on_disk = json.loads((Path(tmp_path) / "IMPROVE_LEDGER.json")
                         .read_text())
    assert on_disk["status"] == "NO_CHILD_ADMITTED"

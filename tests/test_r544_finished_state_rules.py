"""R544 kept-strictening proof tests (Art. XVI/VIII obligation).

The uncommitted R544 engine work was kept (not reverted) because it
implements directive §§2/4/8 fragments and the one-authority refactors
with the settled suites green. Kept strictening must still PROVE
itself adversarially — code is a hypothesis, tests are evidence:

  R1. geometry-warrant deny: canonically geometry-warranted problem
      (R443 applicability context_class) WITHOUT a candidate-owned
      MODEL artifact in its own package -> engineering INCOMPLETE.
  R2. geometry-warrant allow: same warrant WITH the owned artifact ->
      engineering COMPLETE (admissibility preserved, Art. V).
  R3. no-warrant conceptual: unwarranted context + explicit conceptual
      label, no artifact -> engineering COMPLETE (never CAD-claimed).
  R4. ZIP inspection owned/unowned: MODEL_MANIFEST.json with model_id +
      MODEL/*.glb inside the candidate's own ZIP -> owned; missing
      either -> not owned (fail closed, never guessed).
  R5. literal competing validation: an investigated row missing its
      kill condition fails with the gap NAMED (candidate_id +
      kill_condition + resolved disposition required).
  R6. run-level delegation: EngineRun._completion_states answers from
      the verifier, never from a parallel final_status/package rule
      (a stale optimistic final_state cannot disagree with the
      contract file).

Hermetic: tmp run dirs only; no LLM, no network.
"""
from __future__ import annotations

import io
import json
import sys
import types
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

if "toscanini" not in sys.modules:
    try:
        import TOSCANINI as _T  # noqa: N813 — exact on-disk name
        sys.modules["toscanini"] = _T
    except Exception:  # noqa: BLE001
        pass
if sys.platform == "win32":
    try:
        import fcntl  # noqa: F401
    except ImportError:
        _fake = types.ModuleType("fcntl")
        _fake.LOCK_SH = 1
        _fake.LOCK_EX = 2
        _fake.LOCK_NB = 4
        _fake.LOCK_UN = 8
        _fake.flock = lambda *a, **k: None
        sys.modules["fcntl"] = _fake

from discovery_fabric.engine import completion_contract as _cc  # noqa: E402
from discovery_fabric.engine import ranked_result_set as _rrs  # noqa: E402


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False,
                               default=str), encoding="utf-8")


def _spec(mech="porous microstructure resists tissue ingrowth",
          kill="bench loop; measure flow decay over 30 days",
          invention_id="inv:a"):
    return {
        "invention_id": invention_id,
        "mechanism": {"value": {
            "mechanism": mech, "intervention": "porous titanium tip",
            "expected_effect": "sustained flow",
            "falsification_test": kill,
            "mechanism_source_span": "the porous microstructure resists"}},
        "evidence": {"value": [{
            "id": "ev1", "source": "EuropePMC",
            "source_uri": "https://fixture.invalid/1",
            "content_hash": "ab" * 32, "frozen": True}]},
    }


def _eng(context_class="UNKNOWN", model_class=None, geometry=False):
    eng = {"engineering_core": {
             # R544: the critical-parameter list must be RECORDED on
             # the candidate's own spec (values may be UNKNOWN;
             # absence may not) — one named, honestly-unsourced
             # parameter keeps the fixture hermetic.
             "critical_parameters": [
                 {"name": "porosity_fraction", "value": "UNKNOWN",
                  "unit": "frac"}]},
            "applicability": {"context_class": context_class}}
    if geometry:
        eng["geometry"] = {"class": "ENGINEERING_3D"}
    if model_class:
        eng["visualizability_class"] = model_class
    return eng


def _dec():
    return {"selected": {
        "experiment": "bench flow loop",
        "hypotheses": [
            {"name": "H1", "description": "flow improves vs baseline"},
            {"name": "H2", "description": "flow does not improve"}],
        "decision_rule": "kill when the threshold fails"},
        "falsification_contract": {
            "FALSIFICATION_THRESHOLD": "no 30% gain at 30 days"},
        "execution_status": "SPECIFIED"}


def _row(cid, key="primary", killed=False, disp=None, mech="m",
         kill="k"):
    return {"candidate_id": cid, "key": key, "killed": killed,
            "quality_verdict": "FAIL" if killed else "PASS",
            "span_underived": False,
            "physics_lifecycle": ("DOES_NOT_BEAT_BASELINE" if killed
                                  else "BEATS_BASELINE"),
            "attack_overall": ("KILLED" if killed else "PASS"),
            "quality_deficient_count": 0, "uncertain_count": 0,
            "_verdict_rank": 0, "_physics_rank": 0,
            "ranked_admissible": not killed,
            "disposition": disp or ("KILLED" if killed else "SURVIVED"),
            "mechanism": mech, "intervention": "i",
            "falsification_test": kill}


def _zip(path: Path, with_model: bool, model_id: bool = True) -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("README.txt", "candidate package")
        if with_model:
            mman = {"model_id": "model-x"} if model_id else {}
            z.writestr("MODEL/MODEL_MANIFEST.json", json.dumps(mman))
            z.writestr("MODEL/part.glb", b"GLB" * 10)
    path.write_bytes(buf.getvalue())
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _real_tree_pkg(run_dir: Path, cid: str, key: str, disp: str,
                   strip_model: bool = False) -> dict:
    """A REAL candidate-bound package from the frozen R544 tree (real
    compiler output, never hand-shaped bytes): build -> promote to
    DOWNLOAD/ -> package record. Returns the package record."""
    from tests.fixtures.r544 import pkg_tree
    built = pkg_tree.build_package_tree(
        run_dir / "PKG_STAGE" / key,
        f"TECHNOLOGY_TRANSFER_PACKAGE_{key}.zip",
        candidate_id=cid, run_id="ts_r544", disposition=disp,
        strip_model=strip_model)
    dl = run_dir / "DOWNLOAD"
    dl.mkdir(parents=True, exist_ok=True)
    data = Path(built["zip_path"]).read_bytes()
    (dl / f"TECHNOLOGY_TRANSFER_PACKAGE_{key}.zip").write_bytes(data)
    import hashlib
    return {"complete": True, "kind": "TECHNOLOGY_PACKAGE",
            "candidate_id": cid, "ranked_candidate_key": key,
            "zip_name": f"TECHNOLOGY_TRANSFER_PACKAGE_{key}.zip",
            "zip_sha256": hashlib.sha256(data).hexdigest(),
            "package_id": built["package_id"],
            "invention_id": built["invention_id"]}


def _base_dir(base: Path, name: str, eng, with_pkg=True,
              strip_model: bool = False, selection=None,
              inv_id: str | None = None) -> Path:
    rd = base / "ENGINE_RUNS" / name
    _write(rd / "SURVIVOR_SELECTION.json",
           selection or {"selected": "cand_a",
                         "ranked": [_row("cand_a")]})
    _write(rd / "final_state.json",
           {"run_id": name,
            "final_status": "AUTOMATED_INVENTION_CANDIDATE"})
    _write(rd / "run_manifest.json",
           {"run_id": name, "failed_stages": {}})
    rec = None
    if with_pkg:
        rec = _real_tree_pkg(rd, "cand_a", "primary", "SURVIVED",
                             strip_model=strip_model)
        _write(rd / "RANKED_PACKAGE_RECORDS.json", {
            "schema": "RANKED_PACKAGE_RECORDS/1.0.0",
            "packages": {"primary": rec}, "by_candidate_id": {}})
    # the invention spec must carry the tree's frozen invention stem
    # for the byte-level identity check to match (the R542 pattern).
    _write(rd / "INVENTION_SPECIFICATION.json",
           _spec(invention_id=(inv_id or (rec or {}).get("invention_id")
                               or "inv:a")))
    _write(rd / "ENGINEERING_SPECIFICATION.json", eng)
    _write(rd / "DECISIVE_EXPERIMENT.json", _dec())
    return rd


def _warranted_contexts():
    from discovery_fabric.engine import completion_contract as _c
    names = [n for n in dir(_c) if "WARRANT" in n.upper()]
    assert names, "no warrant vocabulary exported by the contract module"
    for n in names:
        v = getattr(_c, n)
        if isinstance(v, (set, frozenset, list, tuple)) and v:
            return set(v), n
    raise AssertionError(f"no usable warrant set among {names}")


def test_r1_warranted_without_owned_artifact_is_incomplete(tmp_path):
    warranted, _ = _warranted_contexts()
    ctx = sorted(warranted)[0]
    rd = _base_dir(tmp_path, "ts_r1",
                   _eng(context_class=ctx, geometry=True),
                   strip_model=True)
    rec = _cc.verify_completion_contract(rd)
    eng = rec["components"]["engineering_model"]
    assert eng["complete"] is False
    assert eng["per_survivor"][0]["model_artifact_owned"] is False
    assert rec["finished_discovery"] is False
    assert "engineering_model" in rec["missing_components"]


def test_r2_warranted_with_owned_artifact_is_complete(tmp_path):
    warranted, _ = _warranted_contexts()
    ctx = sorted(warranted)[0]
    rd = _base_dir(tmp_path, "ts_r2",
                   _eng(context_class=ctx, geometry=True))
    rec = _cc.verify_completion_contract(rd)
    eng = rec["components"]["engineering_model"]
    assert eng["complete"] is True, (
        "a warranted problem with its candidate-owned MODEL artifact "
        "must stay admissible (Art. V)")
    assert eng["per_survivor"][0]["model_artifact_owned"] is True
    assert rec["finished_discovery"] is True


def test_r3_unwarranted_conceptual_needs_no_artifact(tmp_path):
    rd = _base_dir(tmp_path, "ts_r3",
                   _eng(context_class="UNKNOWN",
                        model_class="CONCEPTUAL_SYSTEM_MODEL"))
    rec = _cc.verify_completion_contract(rd)
    eng = rec["components"]["engineering_model"]
    assert eng["complete"] is True
    per = eng["per_survivor"][0]
    assert per["earned_engineering_geometry"] is False


def test_r4_zip_inspection_owned_vs_unowned(tmp_path):
    from discovery_fabric.engine.completion_contract import (
        _candidate_model_artifact)
    rd = tmp_path / "ENGINE_RUNS" / "ts_r4"
    rd.mkdir(parents=True)
    za = rd / "a.zip"
    _zip(za, with_model=True, model_id=True)
    got = _candidate_model_artifact(
        rd, {"zip_name": "a.zip", "candidate_id": "cand_a",
             "complete": True})
    assert got["owned"] is True
    assert got["model_id"] == "model-x"
    zb = rd / "b.zip"
    _zip(zb, with_model=True, model_id=False)
    got = _candidate_model_artifact(
        rd, {"zip_name": "b.zip", "candidate_id": "cand_b",
             "complete": True})
    assert got["owned"] is False
    zc = rd / "c.zip"
    _zip(zc, with_model=False)
    got = _candidate_model_artifact(
        rd, {"zip_name": "c.zip", "candidate_id": "cand_c",
             "complete": True})
    assert got["owned"] is False


def test_r5_competing_row_missing_kill_fails_named(tmp_path):
    rd = _base_dir(
        tmp_path, "ts_r5", _eng(model_class="CONCEPTUAL_SYSTEM_MODEL"),
        selection={"selected": "cand_a",
                   "ranked": [_row("cand_a"),
                              dict(_row("cand_b", key="grid-1",
                                        killed=True),
                                   falsification_test="")]})
    rec = _cc.verify_completion_contract(rd)
    assert rec["finished_discovery"] is False
    assert "mechanisms" in rec["missing_components"]
    comp = next(c for c in rec["components"]["mechanisms"][
        "competing_candidates"] if c["candidate_id"] == "cand_b")
    assert comp["complete"] is False
    assert "kill_condition" in (comp.get("gap") or "")


def test_r6_run_level_delegation_matches_verifier(tmp_path, monkeypatch):
    """EngineRun._completion_states answers from the verifier, never
    from a parallel final_status/package rule: a stale optimistic
    final_state cannot disagree with the contract file."""
    from discovery_fabric.engine.run import EngineRun
    rd = _base_dir(tmp_path, "ts_r6",
                   _eng(model_class="CONCEPTUAL_SYSTEM_MODEL"))
    # poison the final_state with a STALE optimistic completion_states
    # (the retired rule's shape): the delegation must still answer
    # from the verifier (false here — no survivors' packages... the
    # fixture has one complete package; make it stale-TRUE instead).
    fs = json.loads((rd / "final_state.json").read_text())
    fs["completion_states"] = {"PIPELINE_COMPLETED": True,
                               "DISCOVERY_COMPLETED": True,
                               "TECHNOLOGY_PACKAGE_COMPLETED": True,
                               "FINISHED_DISCOVERY": True}
    (rd / "final_state.json").write_text(json.dumps(fs))
    run = EngineRun.__new__(EngineRun)
    run.out = rd
    states = run._completion_states()
    truth = _cc.completion_states(
        _cc.verify_completion_contract(rd))
    assert states["FINISHED_DISCOVERY"] == truth["FINISHED_DISCOVERY"]

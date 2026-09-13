"""R451-C2.3 — Canonical geometry-to-visual identity chain: the
adversarial false-positive battery.

Operator directive R451-C2.3. The round's question: can the system
prove the exact engineering geometry -> canonical GLB -> Visual
Compiler join WITHOUT trusting filenames, booleans, reports, or stale
projections?

Every attack below feeds a forged or incomplete record shape to THE
canonical evaluator (toscanini/visual_join.py — the SAME evaluator the
dossier and the watchdog consume) and proves the system does NOT
promote the state:

  1. fake GLB path            -> geometry never established
  2. empty GLB                -> geometry never established
  3. wrong GLB SHA (recorded) -> contract fails closed
  4. wrong generation         -> contract fails closed
  5. wrong run_id (receipt)   -> release chain fails closed
  6. STEP only                -> ENGINEERING_GEOMETRY_READY, never
                                 VISUAL_INPUT_READY / visual ready
  7. legacy present=true      -> readable, never engineering authority
  8. empty invention record   -> Invention never RECEIVED
  9. placeholder invention    -> Invention never RECEIVED
 10. bridge report without    -> Engineering never RECEIVED
     realization
 11. render record w/ wrong   -> not VISUAL_READY (fail closed)
     GLB
 12. receipt w/ wrong GLB     -> not VISUAL_READY (fail closed)
 13. gate PASS, hero absent   -> not VISUAL_READY (fail closed)
 14. gate PASS, incomplete    -> not VISUAL_READY (fail closed)
     ladder

Plus: the one-evaluator coupling (the dossier projection and the
watchdog announce the SAME join state on every fixture — no second
state machine), the identity-chain equations, the typed package
classification, and the clean-state replay (byte-identical reports on
re-evaluation).

R451-C2.4 SUPERSESSIONS (Art. LXIV, disclosed): the golden fixture's
GLB_BYTES are now a REAL minimal glTF 2.0 container — the previous
b"canonical-engineering-glb-bytes-v1" blob was a fixture artifact that
misrepresented a non-GLB payload as the canonical GLB, and the C2.4
format-validity proof (a mandatory certification condition) correctly
rejects it. The battery's expectations are unchanged: the golden chain
still reaches VISUAL_READY through the strict evaluator, and every
attack still fails to promote.
"""
from __future__ import annotations

import hashlib
import json
import struct
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from toscanini import dossier as dossier_mod  # noqa: E402
from toscanini import visual_join as vj  # noqa: E402

WEBAPP = REPO / "TOSCANINI_UI" / "webapp"


# ---------------------------------------------------------------------------
# fixture factory — a COMPLETE, honest engineering run the attacks mutate
# ---------------------------------------------------------------------------
def _valid_glb(payload: bytes = b'{"asset":{"version":"2.0"}}') -> bytes:
    """A REAL minimal glTF 2.0 binary container: 12-byte header
    (magic, version 2, declared length) + one JSON chunk. The R451-C2.4
    format-validity proof treats anything else as not-a-GLB."""
    json_data = payload + b" " * ((4 - len(payload) % 4) % 4)
    header = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(json_data))
    chunk_header = struct.pack("<I", len(json_data)) + b"JSON"
    return header + chunk_header + json_data


GLB_BYTES = _valid_glb()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _spec_bytes() -> bytes:
    spec = {"artifact": "GEOMETRY_SPEC", "parameters": [
        {"param_id": "d", "value": 2.0}]}
    payload = json.dumps(spec, sort_keys=True).encode()
    return payload + b"\n" + json.dumps(
        {"spec_sha256": _sha(payload)}).encode() + b"\n"


def _complete_run(run: Path, session_id="ts_r451c23_golden") -> Dict[str, Any]:
    """The golden chain: canonical GLB + spec + identity + bridge
    report + receipt (1.1.0) + render record + COMPLETE_PASS gate +
    the full required presentation ladder + a full invention record.
    Returns the identity tuple the assertions cross-check."""
    model = run / "MODEL"
    model.mkdir(parents=True, exist_ok=True)
    glb = model / "engineering_model.glb"
    glb.write_bytes(GLB_BYTES)
    glb_sha = _sha(GLB_BYTES)
    (model / "GEOMETRY_SPEC.json").write_bytes(_spec_bytes())
    spec_file_sha = _sha((model / "GEOMETRY_SPEC.json").read_bytes())
    identity = {
        "artifact": "ARTIFACT_IDENTITY",
        "run_id": session_id,
        "generation_id": "gen-1",
        "geometry_hash": glb_sha,
        "source_geometry_hash": _sha(json.dumps(
            {"artifact": "GEOMETRY_SPEC", "parameters": [
                {"param_id": "d", "value": 2.0}]},
            sort_keys=True).encode()),
        "glb_path": str(glb),
        "glb_disk_sha256": glb_sha,
        "glb_matches_geometry_hash": True,
        "visualizability_class": "ENGINEERING_3D",
    }
    (model / "ARTIFACT_IDENTITY.json").write_text(json.dumps(identity))
    (run / "BRIDGE_REPORT.json").write_text(json.dumps({
        "outcome": "COMPLETED",
        "visualizability_class": "ENGINEERING_3D",
        "geometry": {"generation_id": "gen-1",
                     "visualizability_class": "ENGINEERING_3D",
                     "artifact_identity": identity},
    }))
    m3d = model / "3D"
    m3d.mkdir(parents=True, exist_ok=True)
    (m3d / "render_record.json").write_text(json.dumps({
        "stage": "RENDER", "status": "OK",
        "source_glb_sha256": glb_sha,
        "scene_spec": {"model": {"node_count": 1}},
        "views": {"hero.glb": {"sha256": _sha(GLB_BYTES)}},
    }))
    (m3d / "visual_gate.json").write_text(json.dumps(
        {"verdict": "COMPLETE_PASS"}))
    (m3d / "VISUAL_COMPILER_INVOCATION.json").write_text(json.dumps({
        "kind": "VISUAL_COMPILER_INVOCATION",
        "schema_version": "1.1.0",
        "run_id": session_id, "generation_id": "gen-1",
        "glb_sha256": glb_sha,
        "geometry_spec_sha256": spec_file_sha,
        "visual_compiler_version": "VISUAL_COMPILER_HEADLESS_THREE",
        "invocation_status": "OK",
        "invoked_at": "2026-09-13T00:00:00Z",
        "skip_reason": None,
        "render_record_reference": str(m3d / "render_record.json"),
        "output_directory": str(m3d),
    }))
    from discovery_fabric.engine.visual_compiler import visual_set
    for name in visual_set.required_artifacts(
            1, visual_set.DEFAULT_TURNTABLE_FRAMES)["required"]:
        p = m3d / name
        p.parent.mkdir(parents=True, exist_ok=True)
        # the exported hero GLB carries the canonical bytes (the
        # render record's own view hash proves it)
        p.write_bytes(GLB_BYTES if name == "hero.glb"
                      else b"artifact-" + name.encode().replace(
                          b"/", b"_"))
    (run / "INVENTION_SPECIFICATION.json").write_text(json.dumps({
        "invention_id": "INV-R451C23",
        "problem": "sediment erosion in hydropower turbines",
        "mechanism": "sediment-bypassing runner inlet geometry",
        "causal_chain": ["sediment entrains", "bypass routes it",
                         "erosion exposure drops"],
    }))
    (run / "session.json").write_text(json.dumps({"status": "COMPLETE"}))
    (run / "problem.json").write_text("{}")
    return {"glb_sha": glb_sha, "spec_file_sha": spec_file_sha,
            "glb_path": glb}


def _geom_block(ids: Dict[str, Any]) -> Dict[str, Any]:
    """The CIO geometry block a real build produces for the golden
    chain (route strings + the recorded sha + the generation id)."""
    return {"present": True, "class": "ENGINEERING_3D",
            "conceptual": False, "glb": "/api/run/x/model",
            "glb_sha256": ids["glb_sha"], "step": [],
            "parametric_model_present": False,
            "generation_id": "gen-1",
            "artifact_identity": {"generation_id": "gen-1"}}


def _session(run: Path, status="COMPLETE") -> Dict[str, Any]:
    return {"session_id": run.name, "status": status,
            "final_status": "AUTOMATED_INVENTION_CANDIDATE",
            "run_dir": str(run), "package": {}}


def _evaluator_state(run: Path) -> Dict[str, Any]:
    """THE evaluator's verdict for a run dir — the same call shape the
    dossier and the watchdog use."""
    session = json.loads((run / "session.json").read_text())
    session.setdefault("run_dir", str(run))
    session.setdefault("session_id", run.name)
    contract = vj.evaluate_geometry_contract(
        session, run, _geom_block(_ids[run.name]))
    join = vj.evaluate_visual_join(
        session, _geom_block(_ids[run.name]), {}, running=False,
        engineering_geometry_ready=contract["engineering_geometry_ready"],
        geometry_state=contract["geometry_state"], contract=contract)
    return {"contract": contract, "join": join}


def _watchdog():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "r451_watchdog", REPO / "scripts" / "r451_c2_watchdog.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_ids: Dict[str, Dict[str, Any]] = {}


@pytest.fixture()
def golden(tmp_path: Path) -> Path:
    run = tmp_path / "ts_r451c23_golden"
    _ids[run.name] = _complete_run(run)
    return run


def _mutated(tmp_path: Path, name: str, mutate) -> Path:
    """A fresh golden run with one attack applied (independently
    authored adversarial fixture)."""
    run = tmp_path / name
    _ids[run.name] = _complete_run(run, session_id=name)
    mutate(run)
    return run


# ---------------------------------------------------------------------------
# the golden chain: the ONLY state that reaches VISUAL_READY
# ---------------------------------------------------------------------------
class TestGoldenChain:
    def test_complete_chain_is_visual_ready(self, golden: Path):
        out = _evaluator_state(golden)
        assert out["contract"]["engineering_authority"] == "ENGINEERING"
        assert out["contract"]["engineering_geometry_ready"] is True
        assert out["contract"]["visual_input_ready"] is True
        assert out["join"]["visual_join_state"] == "VISUAL_READY"
        assert out["join"]["release_chain"]["verified"] is True

    def test_identity_chain_equations_hold(self, golden: Path):
        """R451-C2.3 §6 — the ONE identity chain, measured from bytes:
        geometry_spec_sha256 == receipt.geometry_spec_sha256;
        canonical_glb_sha256 == receipt.glb_sha256 ==
        render_record.source_glb_sha256; hero source == canonical."""
        ids = _ids[golden.name]
        receipt = vj.read_invocation_receipt(golden)
        record = json.loads(
            (golden / "MODEL" / "3D" / "render_record.json").read_text())
        assert receipt["geometry_spec_sha256"] == ids["spec_file_sha"]
        assert receipt["glb_sha256"] == ids["glb_sha"]
        assert record["source_glb_sha256"] == ids["glb_sha"]
        chain = vj.verify_release_chain(golden)
        assert chain["verified"] is True

    def test_clean_state_replay_is_byte_identical(self, golden: Path):
        """Art. XXVIII/XXXVII discipline: re-evaluating the SAME bytes
        from clean state produces the SAME report — the evaluator is a
        deterministic function of the records."""
        first = json.dumps(_evaluator_state(golden), sort_keys=True)
        second = json.dumps(_evaluator_state(golden), sort_keys=True)
        assert first == second
        w = _watchdog()
        r1 = json.dumps(w.run_watchdog(golden), sort_keys=True)
        r2 = json.dumps(w.run_watchdog(golden), sort_keys=True)
        assert r1 == r2
        assert json.loads(r1)["verdict"] == "PASS"

    def test_dossier_and_watchdog_agree_on_golden(self, golden: Path):
        """R451-C2.3 §8: the dossier projection and the watchdog
        announce the SAME join state — one evaluator, two consumers."""
        tab = dossier_mod.design_tab(
            _session(golden), {"geometry": _geom_block(_ids[golden.name])})
        w = _watchdog()
        report = w.run_watchdog(golden)
        assert tab["visual_join_state"] == report["observed_join_state"] \
            == "VISUAL_READY"


# ---------------------------------------------------------------------------
# the fourteen directive attacks — none may promote the state
# ---------------------------------------------------------------------------
class TestFalsePositiveBattery:
    # ---- 1. fake GLB path ------------------------------------------------
    def test_fake_glb_path_never_establishes_geometry(self, tmp_path):
        def attack(run: Path):
            (run / "MODEL" / "engineering_model.glb").unlink()
            ident = json.loads(
                (run / "MODEL" / "ARTIFACT_IDENTITY.json").read_text())
            ident["glb_disk_sha256"] = None
            ident["glb_matches_geometry_hash"] = None
            (run / "MODEL"
             / "ARTIFACT_IDENTITY.json").write_text(json.dumps(ident))
        run = _mutated(tmp_path, "ts_attack_fakepath", attack)
        out = _evaluator_state(run)
        assert out["contract"]["artifact_verified"] is False
        assert out["contract"]["geometry_state"] != "geometry_available"
        assert out["contract"]["engineering_authority"] == "UNKNOWN"
        assert out["contract"]["visual_input_ready"] is False

    # ---- 2. empty GLB ----------------------------------------------------
    def test_empty_glb_never_establishes_geometry(self, tmp_path):
        def attack(run: Path):
            (run / "MODEL" / "engineering_model.glb").write_bytes(b"")
        run = _mutated(tmp_path, "ts_attack_emptyglb", attack)
        out = _evaluator_state(run)
        assert out["contract"]["artifact_verified"] is False
        assert out["contract"]["geometry_state"] != "geometry_available"
        assert out["contract"]["visual_input_ready"] is False

    # ---- 3. wrong GLB SHA --------------------------------------------------
    def test_wrong_recorded_glb_sha_fails_closed(self, tmp_path):
        def attack(run: Path):
            ident_path = run / "MODEL" / "ARTIFACT_IDENTITY.json"
            ident = json.loads(ident_path.read_text())
            ident["geometry_hash"] = "f" * 64
            ident_path.write_text(json.dumps(ident))
        run = _mutated(tmp_path, "ts_attack_wrongsha", attack)
        out = _evaluator_state(run)
        assert out["contract"]["artifact_verified"] is False
        assert out["contract"]["engineering_authority"] == "UNKNOWN"
        assert out["contract"]["visual_input_ready"] is False
        assert "SHA" in (out["contract"]["geometry_state_detail"] or "")

    # ---- 4. wrong generation ---------------------------------------------
    def test_wrong_generation_fails_closed(self, tmp_path):
        def attack(run: Path):
            ident_path = run / "MODEL" / "ARTIFACT_IDENTITY.json"
            ident = json.loads(ident_path.read_text())
            ident["generation_id"] = "gen-7"
            ident_path.write_text(json.dumps(ident))
            br_path = run / "BRIDGE_REPORT.json"
            br = json.loads(br_path.read_text())
            br["geometry"]["generation_id"] = "gen-7"
            br["geometry"]["artifact_identity"] = ident
            br_path.write_text(json.dumps(br))
        run = _mutated(tmp_path, "ts_attack_wronggen", attack)
        out = _evaluator_state(run)
        assert out["contract"]["artifact_verified"] is False
        assert out["contract"]["engineering_authority"] == "UNKNOWN"

    # ---- 5. wrong run_id in the receipt -----------------------------------
    def test_receipt_wrong_run_id_fails_release_chain(self, tmp_path):
        def attack(run: Path):
            p = run / "MODEL" / "3D" / "VISUAL_COMPILER_INVOCATION.json"
            rec = json.loads(p.read_text())
            rec["run_id"] = "ts_some_other_run"
            p.write_text(json.dumps(rec))
        run = _mutated(tmp_path, "ts_attack_wrongrunid", attack)
        out = _evaluator_state(run)
        chain = out["join"]["release_chain"]
        assert chain is not None and chain["verified"] is False
        assert any("run_id" in r["detail"]
                   for r in chain["rungs"]
                   if r["rung"] == "invocation_receipt_identity")
        assert out["join"]["visual_join_state"] != "VISUAL_READY"

    # ---- 6. STEP only ------------------------------------------------------
    def test_step_only_never_claims_visual_readiness(self, tmp_path):
        run = tmp_path / "ts_attack_steponly"
        _ids[run.name] = _complete_run(run, session_id=run.name)
        # the honest STEP-only shape: the GLB (and its GLB-bound
        # identity/render chain) never existed; a real, byte-valid
        # STEP does — the bridge report records the completed
        # engineering realization class
        import shutil
        shutil.rmtree(run / "MODEL" / "3D")
        (run / "MODEL" / "engineering_model.glb").unlink()
        (run / "MODEL" / "ARTIFACT_IDENTITY.json").unlink()
        (run / "MODEL" / "part.step").write_text(
            "ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\nENDSEC;\n"
            "END-ISO-10303-21;\n")
        # the CIO geometry block for a STEP-only run records NO GLB
        # route and NO GLB sha (there was never one)
        geom_block = dict(_geom_block(_ids[run.name]),
                          glb=None, glb_sha256=None)
        session = {"session_id": run.name, "status": "COMPLETE",
                   "final_status": "AUTOMATED_INVENTION_CANDIDATE",
                   "run_dir": str(run), "package": {}}
        contract = vj.evaluate_geometry_contract(session, run, geom_block)
        join = vj.evaluate_visual_join(
            session, geom_block, {}, running=False,
            engineering_geometry_ready=contract["engineering_geometry_ready"],
            geometry_state=contract["geometry_state"], contract=contract)
        out = {"contract": contract, "join": join}
        contract = out["contract"]
        # the STEP is a real, non-empty, byte-valid artifact
        assert contract["artifact_verified"] is True
        assert contract["engineering_authority"] == "ENGINEERING"
        assert contract["engineering_geometry_ready"] is True
        # ... and it NEVER establishes the visual input boundary
        assert contract["visual_input_ready"] is False
        assert out["join"]["visual_join_state"] == "VISUAL_INPUT_NOT_READY"
        geom_block = dict(_geom_block(_ids[run.name]),
                          glb=None, glb_sha256=None)
        tab = dossier_mod.design_tab(_session(run), {"geometry": geom_block})
        rows = {r["key"]: r for r in dossier_mod.pipeline_projection(
            _session(run), run, False,
            {"package_state": {"state": "NOT_PRODUCED"}},
            {"retrieval_state": "RETRIEVED", "retrieved_count": 3}, tab)}
        assert rows["visualization"]["blocked_class"] == "VISUAL_INPUT"
        assert rows["visualization"]["status"] == "STOPPED"

    # ---- 7. legacy present=true --------------------------------------------
    def test_legacy_boolean_never_gains_engineering_authority(self):
        out = dossier_mod._geometry_state(
            {}, {"present": True}, {}, running=False)
        assert out["geometry_state"] != "geometry_available"
        contract = out["geometry_contract"]
        assert contract["engineering_authority"] == "UNKNOWN"
        assert contract["engineering_geometry_ready"] is False
        tab = dossier_mod.design_tab(
            _session(tmp_path=Path("/nonexistent")) if False else
            {"session_id": "x", "status": "COMPLETE", "run_dir": None,
             "package": {}},
            {"geometry": {"present": True}})
        assert tab["epistemic_class"] == "UNKNOWN"
        assert tab["availability"] != "AVAILABLE"

    # ---- 8/9. empty + placeholder invention records ------------------------
    def test_empty_invention_record_never_establishes_invention(
            self, tmp_path):
        def attack(run: Path):
            (run / "INVENTION_SPECIFICATION.json").write_text("{}")
        run = _mutated(tmp_path, "ts_attack_emptyinv", attack)
        rows = {r["key"]: r for r in dossier_mod.pipeline_projection(
            _session(run), run, False,
            {"package_state": {"state": "NOT_PRODUCED"}},
            {"retrieval_state": "RETRIEVED", "retrieved_count": 3},
            {"geometry_state": "upstream_not_reached"})}
        assert rows["invention"]["status"] != "RECEIVED"
        v = dossier_mod._invention_record_validity(
            run, "AUTOMATED_INVENTION_CANDIDATE")
        assert v["validity"] == "INVALID_EMPTY"

    def test_placeholder_invention_record_never_establishes_invention(
            self, tmp_path):
        (tmp_path / "ts_attack_placeholder").mkdir()
        run = tmp_path / "ts_attack_placeholder"
        _ids[run.name] = _complete_run(run, session_id=run.name)
        (run / "INVENTION_SPECIFICATION.json").write_text(json.dumps(
            {"invention_id": "TBD", "problem": "placeholder",
             "mechanism": "N/A", "causal_chain": "todo"}))
        v = dossier_mod._invention_record_validity(
            run, "AUTOMATED_INVENTION_CANDIDATE")
        assert v["validity"] == "INVALID_PLACEHOLDER"
        rows = {r["key"]: r for r in dossier_mod.pipeline_projection(
            _session(run), run, False,
            {"package_state": {"state": "NOT_PRODUCED"}},
            {"retrieval_state": "RETRIEVED", "retrieved_count": 3},
            {"geometry_state": "upstream_not_reached"})}
        assert rows["invention"]["status"] != "RECEIVED"

    def test_minimal_and_partial_invention_records_never_establish(
            self, tmp_path):
        (tmp_path / "ts_attack_minimal").mkdir()
        run = tmp_path / "ts_attack_minimal"
        _ids[run.name] = _complete_run(run, session_id=run.name)
        # a synthetic minimal record: identity only, no substance
        (run / "INVENTION_SPECIFICATION.json").write_text(json.dumps(
            {"invention_id": "INV-MINIMAL"}))
        v = dossier_mod._invention_record_validity(
            run, "AUTOMATED_INVENTION_CANDIDATE")
        assert v["validity"] == "INVALID_MINIMAL"
        # a partial/malformed record: truncated JSON
        (run / "INVENTION_SPECIFICATION.json").write_text(
            '{"invention_id": "INV-PARTIAL", "problem":')
        v = dossier_mod._invention_record_validity(
            run, "AUTOMATED_INVENTION_CANDIDATE")
        assert v["validity"] == "INVALID_MALFORMED"
        # a failed adjudication: the run's own recorded rejection
        (run / "INVENTION_SPECIFICATION.json").write_text(json.dumps(
            {"invention_id": "INV-REJ",
             "problem": "a real problem statement",
             "mechanism": "a real mechanism statement",
             "causal_chain": ["a", "b", "c"]}))
        v = dossier_mod._invention_record_validity(run, "REJECTED")
        assert v["validity"] == "INVALID_ADJUDICATION"

    # ---- 10. bridge report without realization ------------------------------
    def test_bridge_report_without_realization_never_receives_engineering(
            self, tmp_path):
        def attack(run: Path):
            (run / "MODEL" / "engineering_model.glb").unlink()
            (run / "MODEL" / "GEOMETRY_SPEC.json").unlink()
            (run / "MODEL" / "ARTIFACT_IDENTITY.json").unlink()
            # the BRIDGE_REPORT still describes a COMPLETED realization
        run = _mutated(tmp_path, "ts_attack_bridgereport", attack)
        tab = dossier_mod.design_tab(
            _session(run), {"geometry": dict(
                _geom_block(_ids[run.name]), glb_sha256=None)})
        rows = {r["key"]: r for r in dossier_mod.pipeline_projection(
            _session(run), run, False,
            {"package_state": {"state": "NOT_PRODUCED"}},
            {"retrieval_state": "RETRIEVED", "retrieved_count": 3}, tab)}
        assert rows["engineering"]["status"] != "RECEIVED"

    # ---- 11. render record with wrong GLB -----------------------------------
    def test_render_record_wrong_glb_fails_closed(self, tmp_path):
        def attack(run: Path):
            p = run / "MODEL" / "3D" / "render_record.json"
            rec = json.loads(p.read_text())
            rec["source_glb_sha256"] = "e" * 64
            p.write_text(json.dumps(rec))
        run = _mutated(tmp_path, "ts_attack_recsrongglb", attack)
        out = _evaluator_state(run)
        assert out["join"]["visual_join_state"] == "RELEASE_UNVERIFIED"
        chain = out["join"]["release_chain"]
        assert chain["first_failure"] == "render_record_identity"

    # ---- 12. receipt with wrong GLB -----------------------------------------
    def test_receipt_wrong_glb_fails_closed(self, tmp_path):
        def attack(run: Path):
            p = run / "MODEL" / "3D" / "VISUAL_COMPILER_INVOCATION.json"
            rec = json.loads(p.read_text())
            rec["glb_sha256"] = "d" * 64
            p.write_text(json.dumps(rec))
        run = _mutated(tmp_path, "ts_attack_recwrongglb", attack)
        out = _evaluator_state(run)
        assert out["join"]["visual_join_state"] == "RELEASE_UNVERIFIED"
        chain = out["join"]["release_chain"]
        assert chain["first_failure"] == "invocation_receipt_identity"

    def test_receipt_wrong_spec_sha_fails_closed(self, tmp_path):
        """R451-C2.3 §6: geometry_spec_sha256 == receipt.geometry_spec_
        sha256 is part of the enforced chain — a mismatch fails closed
        in the evaluator, not merely in a later report."""
        def attack(run: Path):
            p = run / "MODEL" / "3D" / "VISUAL_COMPILER_INVOCATION.json"
            rec = json.loads(p.read_text())
            rec["geometry_spec_sha256"] = "c" * 64
            p.write_text(json.dumps(rec))
        run = _mutated(tmp_path, "ts_attack_wrongspecsha", attack)
        out = _evaluator_state(run)
        assert out["join"]["visual_join_state"] == "RELEASE_UNVERIFIED"

    # ---- 13. gate PASS but hero absent --------------------------------------
    def test_gate_pass_hero_absent_never_visual_ready(self, tmp_path):
        def attack(run: Path):
            (run / "MODEL" / "3D" / "hero.png").unlink()
        run = _mutated(tmp_path, "ts_attack_nohero", attack)
        out = _evaluator_state(run)
        assert out["join"]["visual_join_state"] == "RELEASE_UNVERIFIED"
        chain = out["join"]["release_chain"]
        # the hero's absence fires through the presentation-set rung
        # (hero.png is part of the unconditional required set) — the
        # typed state is the fail-closed RELEASE_UNVERIFIED either way
        assert chain["first_failure"] in ("presentation_artifact_set",
                                          "hero_exists")
        w = _watchdog()
        report = w.run_watchdog(run)
        assert report["verdict"] == "FAIL"
        assert report["observed_join_state"] == "RELEASE_UNVERIFIED"

    # ---- 14. gate PASS but incomplete ladder --------------------------------
    def test_gate_pass_incomplete_ladder_never_visual_ready(
            self, tmp_path):
        def attack(run: Path):
            (run / "MODEL" / "3D" / "poster.png").unlink()
            (run / "MODEL" / "3D" / "orthographic" / "iso.png").unlink()
        run = _mutated(tmp_path, "ts_attack_shortladder", attack)
        out = _evaluator_state(run)
        assert out["join"]["visual_join_state"] == "RELEASE_UNVERIFIED"
        chain = out["join"]["release_chain"]
        assert chain["first_failure"] == "presentation_artifact_set"

    def test_gate_pass_exported_hero_tampered_fails_closed(
            self, tmp_path):
        """The exported hero.glb's provenance: its bytes must match the
        render record's OWN recorded view hash — a swapped hero fails
        closed inside the evaluator (R451-C2.3 §6)."""
        def attack(run: Path):
            hero_glb = run / "MODEL" / "3D" / "hero.glb"
            hero_glb.write_bytes(b"swaped-hero-scene-bytes")
        run = _mutated(tmp_path, "ts_attack_swaphero", attack)
        out = _evaluator_state(run)
        assert out["join"]["visual_join_state"] == "RELEASE_UNVERIFIED"
        chain = out["join"]["release_chain"]
        assert chain["first_failure"] == "hero_source_identity"

    def test_missing_authority_stays_unknown_never_engineering(
            self, tmp_path):
        """The orphan-GLB attack: a real GLB with NO recorded
        engineering class stays UNKNOWN — never engineering by
        filename, never promoted to the engineering ribbon."""
        def attack(run: Path):
            (run / "MODEL" / "ARTIFACT_IDENTITY.json").unlink()
            (run / "BRIDGE_REPORT.json").unlink()
        run = _mutated(tmp_path, "ts_attack_noclass", attack)
        out = _evaluator_state(run)
        assert out["contract"]["engineering_authority"] == "UNKNOWN"
        assert out["contract"]["engineering_geometry_ready"] is False
        assert out["join"]["visual_join_state"] != "VISUAL_READY"


# ---------------------------------------------------------------------------
# one evaluator, two consumers — the join states agree everywhere
# ---------------------------------------------------------------------------
class TestOneEvaluatorTwoConsumers:
    @pytest.mark.parametrize("mutate,name,expected", [
        (None, "ts_agree_golden", "VISUAL_READY"),
        (lambda r: (r / "MODEL" / "3D"
                    / "VISUAL_COMPILER_INVOCATION.json").unlink(),
         "ts_agree_noreceipt", "INVOCATION_MISSING"),
        (lambda r: (r / "MODEL" / "3D" / "visual_gate.json").write_text(
            json.dumps({"verdict": "FAIL"})),
         "ts_agree_gatefail", "STOPPED_GATE"),
        (lambda r: (r / "MODEL" / "3D"
                    / "VISUAL_COMPILER_INVOCATION.json").write_text(
            json.dumps({"kind": "VISUAL_COMPILER_INVOCATION",
                        "schema_version": "1.1.0", "run_id": r.name,
                        "invocation_status": "RENDER_SKIPPED_LOW_MEMORY",
                        "skip_reason": "memory floor"})),
         "ts_agree_infraskip", "RENDER_BLOCKED"),
    ])
    def test_dossier_and_watchdog_announce_the_same_state(
            self, tmp_path, mutate, name, expected):
        run = tmp_path / name
        _ids[run.name] = _complete_run(run, session_id=name)
        if mutate:
            mutate(run)
        tab = dossier_mod.design_tab(
            _session(run), {"geometry": _geom_block(_ids[run.name])})
        w = _watchdog()
        report = w.run_watchdog(run)
        assert tab["visual_join_state"] == report["observed_join_state"]
        assert tab["visual_join_state"] == expected

    def test_watchdog_vocabulary_is_the_evaluators(self):
        w = _watchdog()
        assert w.JOIN_STATES == vj.VISUAL_JOIN_STATES
        assert w._RENDERED_STATUSES == vj.RENDERER_RAN_STATUSES


# ---------------------------------------------------------------------------
# structural pins: the typed-classification + boundary disciplines
# ---------------------------------------------------------------------------
class TestStructuralPins:
    def test_package_classifier_has_no_free_text_inference(self):
        src = (REPO / "toscanini" / "dossier.py").read_text()
        assert 'in reason.lower()' not in src
        assert "transport_words" not in src
        assert '"quality gate" in' not in src

    def test_visual_join_never_writes(self):
        src = (REPO / "toscanini" / "visual_join.py").read_text()
        for banned in ("write_text", "mkdir", "unlink"):
            assert banned not in src

    def test_ui_renders_the_new_typed_causes(self):
        src = (WEBAPP / "lib" / "presentationState.ts").read_text()
        assert '"visual_input_missing"' in src
        assert '"release_unverified"' in src
        assert "The canonical 3D model file" in src
        assert "could not be " in src
        assert "renderBlockedTitle" in src
        assert 'return "GEOMETRY AUTHORITY UNVERIFIED"' in src
        stage = (WEBAPP / "components" / "TechStage.tsx").read_text()
        assert "renderBlockedTitle(view.engineeringAuthority)" in stage
        assert "canonical 3D model file not produced" in stage
        assert "release chain unverified" in stage

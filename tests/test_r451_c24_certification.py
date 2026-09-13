"""R451-C2.4 — Presentation-state certification battery: artifact
identity is mandatory, the weak fallback is eliminated, and authority
reaches the final UI state.

Operator directive R451-C2.4. The round's question: can the
presentation boundary be reached WITHOUT the recorded artifact
identity chain — a filename that looks right, a stale CIO render
verdict, a legacy boolean projection — and still claim visual
readiness? Every attack below feeds a forged or incomplete shape to
THE canonical evaluator (toscanini/visual_join.py — the SAME evaluator
the dossier and the watchdog consume) and proves the system does NOT
promote the state.

The twelve directive attacks:

  1. artifact identity missing        -> geometry never certified
  2. identity present, SHA missing    -> geometry never certified
  3. generation missing               -> geometry never certified
  4. bridge says engineering,         -> geometry never certified
     identity absent
  5. CAD says completed, identity     -> geometry never certified
     absent
  6. unknown authority + stale CIO    -> NOT VISUAL_READY (the
     render PASS                         directive's acceptance attack)
  7. conceptual authority + render    -> never upgrades into current
     PASS                                VISUAL_READY
  8. valid GLB, wrong generation      -> contract fails closed
  9. valid GLB + missing geometry-    -> release chain fails closed
     spec SHA (spec file present)
 10. valid GLB + receipt spec SHA     -> release chain fails closed
     but no spec file on disk
 11. valid GLB + both spec hashes     -> release chain fails closed
     absent                              (the C2.3-era lenient pass is
                                          SUPERSEDED — mandatory lineage)
 12. old legacy projection + visual   -> never upgrades into current
     PASS                                VISUAL_READY

Plus the positive controls (Art. V: not a universal rejector): the
complete valid chain reaches geometry_available + VISUAL_READY +
"Technology ready" on the recorded ENGINEERING authority; a verified
CONCEPTUAL artifact stays readable and never claims engineering; the
GLB format check passes a real container and rejects magic/version/
length forgeries; artifact DISCOVERY and artifact CERTIFICATION are
separate (a filename-only candidate is a diagnostic, never certified);
the fallback cannot produce visual_complete in ANY branch; the
one-evaluator coupling (dossier == watchdog) holds on the new
fixtures; and the clean-state replay is byte-identical.
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
# fixture machinery — the same recorded shapes the production bridge writes
# ---------------------------------------------------------------------------
def _valid_glb(payload: bytes = b'{"asset":{"version":"2.0"}}') -> bytes:
    json_data = payload + b" " * ((4 - len(payload) % 4) % 4)
    header = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(json_data))
    chunk_header = struct.pack("<I", len(json_data)) + b"JSON"
    return header + chunk_header + json_data


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _spec_bytes() -> bytes:
    spec = {"artifact": "GEOMETRY_SPEC", "parameters": [
        {"param_id": "d", "value": 2.0}]}
    payload = json.dumps(spec, sort_keys=True).encode()
    return payload + b"\n" + json.dumps(
        {"spec_sha256": _sha(payload)}).encode() + b"\n"


def _complete_run(run: Path, session_id="ts_r451c24_golden",
                  with_spec: bool = True) -> Dict[str, Any]:
    """The golden chain: certified-canonical GLB + spec + identity +
    bridge report + receipt (1.1.0) + render record + COMPLETE_PASS
    gate + the full required presentation ladder + a full invention
    record."""
    model = run / "MODEL"
    model.mkdir(parents=True, exist_ok=True)
    glb = model / "engineering_model.glb"
    glb.write_bytes(_valid_glb())
    glb_sha = _sha(glb.read_bytes())
    spec_file_sha = None
    if with_spec:
        (model / "GEOMETRY_SPEC.json").write_bytes(_spec_bytes())
        spec_file_sha = _sha((model / "GEOMETRY_SPEC.json").read_bytes())
    identity = {
        "artifact": "ARTIFACT_IDENTITY",
        "run_id": session_id,
        "generation_id": "gen-1",
        "geometry_hash": glb_sha,
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
        "views": {"hero.glb": {"sha256": _sha(glb.read_bytes())}},
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
        p.write_bytes(_valid_glb() if name == "hero.glb"
                      else b"artifact-" + name.encode().replace(
                          b"/", b"_"))
    (run / "INVENTION_SPECIFICATION.json").write_text(json.dumps({
        "invention_id": "INV-R451C24",
        "problem": "sediment erosion in hydropower turbines",
        "mechanism": "sediment-bypassing runner inlet geometry",
        "causal_chain": ["sediment entrains", "bypass routes it",
                         "erosion exposure drops"],
    }))
    (run / "session.json").write_text(json.dumps({"status": "COMPLETE"}))
    (run / "problem.json").write_text("{}")
    return {"glb_sha": glb_sha, "glb_path": glb}


def _geom_block(ids: Dict[str, Any]) -> Dict[str, Any]:
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


def _evaluator_state(run: Path,
                     geom_override: Dict[str, Any] = None) -> Dict[str, Any]:
    session = json.loads((run / "session.json").read_text())
    session.setdefault("run_dir", str(run))
    session.setdefault("session_id", run.name)
    geom = geom_override if geom_override is not None else \
        _geom_block(_ids[run.name])
    contract = vj.evaluate_geometry_contract(session, run, geom)
    join = vj.evaluate_visual_join(
        session, geom, {}, running=False,
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
    run = tmp_path / "ts_r451c24_golden"
    _ids[run.name] = _complete_run(run)
    return run


def _mutated(tmp_path: Path, name: str, mutate) -> Path:
    run = tmp_path / name
    _ids[run.name] = _complete_run(run, session_id=name)
    mutate(run)
    return run


# ---------------------------------------------------------------------------
# positive controls (Art. V — the verifier must admit the valid chain)
# ---------------------------------------------------------------------------
class TestPositiveControls:
    def test_complete_chain_reaches_every_honest_state(self, golden: Path):
        out = _evaluator_state(golden)
        c = out["contract"]
        assert c["geometry_state"] == "geometry_available"
        assert c["engineering_authority"] == "ENGINEERING"
        assert c["artifact_verified"] is True
        assert c["verification"]["glb_certified"] is True
        assert c["visual_input_ready"] is True
        assert out["join"]["visual_join_state"] == "VISUAL_READY"
        chain = out["join"]["release_chain"]
        assert chain["verified"] is True
        names = [r["rung"] for r in chain["rungs"]]
        # the C2.4 generation rung sits between the receipt and the
        # render record
        assert names.index("invocation_receipt_identity") \
            < names.index("generation_identity") \
            < names.index("render_record_identity")

    def test_ui_announces_technology_ready_only_on_engineering(
            self, golden: Path):
        tab = dossier_mod.design_tab(
            _session(golden), {"geometry": _geom_block(_ids[golden.name])})
        assert tab["geometry_state"] == "visual_complete"
        assert tab["engineering_authority"] == "ENGINEERING"
        # the frontend badge maps (VISUAL_READY, ENGINEERING) ->
        # "Technology ready" — the only path to that label
        stage = (WEBAPP / "components" / "TechStage.tsx").read_text()
        assert stage.count('label: "Technology ready"') == 1
        ready_idx = stage.index('label: "Technology ready"')
        guard = stage[:ready_idx].rfind('case "VISUAL_READY"')
        block = stage[guard:ready_idx]
        assert 'view.engineeringAuthority !== "ENGINEERING"' in block

    def test_verified_conceptual_artifact_stays_readable_never_ready(
            self, tmp_path):
        """A fully certified CONCEPTUAL artifact (real identity chain,
        real container) stays geometry_available — Art. XI readability
        — while its authority is CONCEPTUAL: it can never reach
        VISUAL_READY and never claims engineering."""
        def conceptualize(run: Path):
            (run / "MODEL" / "ARTIFACT_IDENTITY.json").write_text(
                json.dumps({
                    "artifact": "ARTIFACT_IDENTITY",
                    "run_id": run.name, "generation_id": "gen-1",
                    "geometry_hash": _ids[run.name]["glb_sha"],
                    "glb_path": str(_ids[run.name]["glb_path"]),
                    "glb_disk_sha256": _ids[run.name]["glb_sha"],
                    "glb_matches_geometry_hash": True,
                    "visualizability_class": "SYSTEM_3D"}))
            (run / "BRIDGE_REPORT.json").write_text(json.dumps({
                "outcome": "COMPLETED",
                "visualizability_class": "SYSTEM_3D",
                "geometry": {"generation_id": "gen-1",
                             "visualizability_class": "SYSTEM_3D"}}))
        run = _mutated(tmp_path, "ts_c24_conceptual", conceptualize)
        out = _evaluator_state(run)
        assert out["contract"]["geometry_state"] == "geometry_available"
        assert out["contract"]["engineering_authority"] == "CONCEPTUAL"
        assert out["contract"]["engineering_geometry_ready"] is False
        assert out["contract"]["visual_input_ready"] is True
        # the join never drives a conceptual artifact into readiness
        assert out["join"]["visual_join_state"] is None


# ---------------------------------------------------------------------------
# the GLB format validity proof (directive item 3)
# ---------------------------------------------------------------------------
class TestGlbFormatValidity:
    def test_real_container_passes(self, tmp_path):
        p = tmp_path / "ok.glb"
        p.write_bytes(_valid_glb())
        fmt = vj.glb_format_check(p)
        assert fmt["valid"] is True

    def test_correct_hash_over_non_glb_bytes_fails(self, tmp_path):
        """THE directive attack: correct hash + engineering authority
        over bytes that are not a GLB container -> must fail."""
        p = tmp_path / "not-a.glb"
        p.write_bytes(b"a plausible engineering payload, not a glTF")
        fmt = vj.glb_format_check(p)
        assert fmt["valid"] is False
        assert "glTF magic" in fmt["detail"]

    def test_wrong_version_and_truncated_length_fail(self, tmp_path):
        raw = _valid_glb()
        v1 = bytearray(raw)
        struct.pack_into("<I", v1, 4, 1)  # version 1
        p1 = tmp_path / "v1.glb"
        p1.write_bytes(bytes(v1))
        assert vj.glb_format_check(p1)["valid"] is False
        truncated = raw[:-3]
        p2 = tmp_path / "short.glb"
        p2.write_bytes(truncated)
        fmt2 = vj.glb_format_check(p2)
        assert fmt2["valid"] is False
        assert "length" in fmt2["detail"] or "truncated" in fmt2["detail"]

    def test_format_failure_blocks_certification_with_authority_present(
            self, tmp_path):
        """valid-format precondition: an identity-named artifact whose
        bytes hash correctly but whose container is invalid never
        certifies — geometry_unverified, never geometry_available."""
        def corrupt(run: Path):
            glb = _ids[run.name]["glb_path"]
            glb.write_bytes(b"payload-with-matching-identity-not-glb")
            # re-record the sha so ONLY the format fails
            ident_path = run / "MODEL" / "ARTIFACT_IDENTITY.json"
            ident = json.loads(ident_path.read_text())
            ident["geometry_hash"] = ident["glb_disk_sha256"] = \
                _sha(glb.read_bytes())
            ident_path.write_text(json.dumps(ident))
            rec_path = run / "MODEL" / "3D" / "render_record.json"
            rec = json.loads(rec_path.read_text())
            rec["source_glb_sha256"] = _sha(glb.read_bytes())
            rec_path.write_text(json.dumps(rec))
            receipt_path = run / "MODEL" / "3D" / \
                "VISUAL_COMPILER_INVOCATION.json"
            receipt = json.loads(receipt_path.read_text())
            receipt["glb_sha256"] = _sha(glb.read_bytes())
            receipt_path.write_text(json.dumps(receipt))
            _ids[run.name]["glb_sha"] = _sha(glb.read_bytes())
        run = _mutated(tmp_path, "ts_c24_badformat", corrupt)
        out = _evaluator_state(run)
        c = out["contract"]
        assert c["verification"]["glb_certified"] is False
        assert c["geometry_state"] == "geometry_unverified"
        assert c["visual_input_ready"] is False
        assert out["join"]["visual_join_state"] != "VISUAL_READY"


# ---------------------------------------------------------------------------
# artifact DISCOVERY vs artifact CERTIFICATION (directive item 4)
# ---------------------------------------------------------------------------
class TestDiscoveryVsCertification:
    def test_filename_fallback_is_diagnostic_never_certified(
            self, tmp_path):
        """resolve_canonical_glb LOCATES a candidate by filename; only
        the recorded identity chain certifies it. A GLB whose name
        looks right but which NO identity document names is a
        diagnostic candidate — never the certified canonical
        artifact."""
        run = tmp_path / "ts_c24_fallbackonly"
        _ids[run.name] = _complete_run(run)
        # strip every recorded pointer to the artifact: no lineage, no
        # glb_path, no recorded sha — the file itself remains
        (run / "MODEL" / "ARTIFACT_IDENTITY.json").unlink()
        ident = json.loads(
            (run / "BRIDGE_REPORT.json").read_text())
        ident["geometry"]["artifact_identity"]["glb_path"] = None
        ident["geometry"]["artifact_identity"]["geometry_hash"] = None
        ident["geometry"]["artifact_identity"]["glb_disk_sha256"] = None
        (run / "BRIDGE_REPORT.json").write_text(json.dumps(ident))
        locator = vj.resolve_canonical_glb(run)
        assert locator is not None and locator.is_file()
        cert = vj.certified_canonical_glb(run, _geom_block(_ids[run.name]))
        assert cert["certified"] is False
        assert cert["diagnostic_candidate"] is not None
        assert any("filename" in f for f in cert["failures"])
        out = _evaluator_state(run)
        assert out["contract"]["geometry_state"] == "geometry_unverified"
        assert out["contract"]["visual_input_ready"] is False

    def test_lineage_named_artifact_certifies(self, tmp_path):
        """The DESIGN_LINEAGE current-generation pointer is a recorded
        identity document — an artifact named THERE certifies (the
        authoritative path: exact artifact -> measured SHA -> current
        generation)."""
        run = tmp_path / "ts_c24_lineage"
        _ids[run.name] = _complete_run(run)
        (run / "MODEL" / "DESIGN_LINEAGE.json").write_text(json.dumps({
            "generation_models": [
                {"generation": 1, "current": True,
                 "glb": "MODEL/engineering_model.glb"}]}))
        cert = vj.certified_canonical_glb(run, _geom_block(_ids[run.name]))
        assert cert["certified"] is True
        assert cert["basis"] == "DESIGN_LINEAGE.json current generation entry"


# ---------------------------------------------------------------------------
# the twelve directive attacks — none may promote the state
# ---------------------------------------------------------------------------
class TestDirectiveAttacks:
    # -- 1. artifact identity missing -----------------------------------
    def test_identity_missing_never_certifies(self, tmp_path):
        def attack(run: Path):
            (run / "MODEL" / "ARTIFACT_IDENTITY.json").unlink()
            br = json.loads((run / "BRIDGE_REPORT.json").read_text())
            br["geometry"]["artifact_identity"] = {
                "generation_id": "gen-1"}
            (run / "BRIDGE_REPORT.json").write_text(json.dumps(br))
        run = _mutated(tmp_path, "ts_c24_a1", attack)
        out = _evaluator_state(run)
        c = out["contract"]
        assert c["artifact_verified"] is False
        assert c["geometry_state"] == "geometry_unverified"
        assert c["visual_input_ready"] is False
        assert out["join"]["visual_join_state"] != "VISUAL_READY"
        assert any("identity" in f.lower()
                   for f in c["verification"]["certification_failures"])

    # -- 2. identity present but SHA missing -----------------------------
    def test_identity_without_sha_never_certifies(self, tmp_path):
        def attack(run: Path):
            ident_path = run / "MODEL" / "ARTIFACT_IDENTITY.json"
            ident = json.loads(ident_path.read_text())
            ident["geometry_hash"] = None
            ident["glb_disk_sha256"] = None
            ident_path.write_text(json.dumps(ident))
            br = json.loads((run / "BRIDGE_REPORT.json").read_text())
            br["geometry"]["artifact_identity"] = ident
            (run / "BRIDGE_REPORT.json").write_text(json.dumps(br))
        run = _mutated(tmp_path, "ts_c24_a2", attack)
        out = _evaluator_state(run)
        c = out["contract"]
        assert c["artifact_verified"] is False
        assert c["geometry_state"] == "geometry_unverified"
        assert c["visual_input_ready"] is False
        assert any("sha" in f.lower()
                   for f in c["verification"]["certification_failures"])

    # -- 3. generation missing -------------------------------------------
    def test_generation_missing_never_certifies(self, tmp_path):
        def attack(run: Path):
            ident_path = run / "MODEL" / "ARTIFACT_IDENTITY.json"
            ident = json.loads(ident_path.read_text())
            ident["generation_id"] = None
            ident_path.write_text(json.dumps(ident))
            br = json.loads((run / "BRIDGE_REPORT.json").read_text())
            br["geometry"]["artifact_identity"] = ident
            br["geometry"]["generation_id"] = None
            (run / "BRIDGE_REPORT.json").write_text(json.dumps(br))
        run = _mutated(tmp_path, "ts_c24_a3", attack)
        # the projection's own generation id is gone too — NO recorded
        # identity document carries a generation any more
        out = _evaluator_state(run, geom_override={
            k: v for k, v in _geom_block(_ids[run.name]).items()
            if k not in ("generation_id", "artifact_identity")})
        c = out["contract"]
        assert c["artifact_verified"] is False
        assert c["geometry_state"] == "geometry_unverified"
        assert any("generation" in f.lower()
                   for f in c["verification"]["certification_failures"])

    # -- 4. bridge says engineering but identity absent ------------------
    def test_bridge_engineering_claim_without_identity_fails(
            self, tmp_path):
        def attack(run: Path):
            (run / "MODEL" / "ARTIFACT_IDENTITY.json").unlink()
            # the BRIDGE_REPORT still DESCRIBES the ENGINEERING class
            # (a report describes a realization; it does not
            # constitute one — and it cannot substitute the identity)
        run = _mutated(tmp_path, "ts_c24_a4", attack)
        out = _evaluator_state(run)
        c = out["contract"]
        assert c["geometry_state"] == "geometry_unverified"
        assert c["visual_input_ready"] is False
        assert out["join"]["visual_join_state"] != "VISUAL_READY"
        rows = {r["key"]: r for r in dossier_mod.pipeline_projection(
            _session(run), run, False,
            {"package_state": {"state": "NOT_PRODUCED"}},
            {"retrieval_state": "RETRIEVED", "retrieved_count": 3},
            dossier_mod.design_tab(
                _session(run), {"geometry": _geom_block(_ids[run.name])}))}
        assert rows["engineering"]["status"] != "RECEIVED"

    # -- 5. CAD says completed but identity absent -----------------------
    def test_cad_completed_without_identity_fails(self, tmp_path):
        def attack(run: Path):
            (run / "MODEL" / "ARTIFACT_IDENTITY.json").unlink()
            (run / "BRIDGE_REPORT.json").unlink()
            (run / "CAD_PIPELINE_LEDGER.json").write_text(json.dumps(
                {"outcome": "COMPLETED"}))
        run = _mutated(tmp_path, "ts_c24_a5", attack)
        out = _evaluator_state(run)
        c = out["contract"]
        # the CAD ledger's recorded completion is a recorded authority
        # FACT — but the artifact identity is still mandatory, so the
        # certification fails regardless
        assert c["geometry_state"] == "geometry_unverified"
        assert c["visual_input_ready"] is False
        assert out["join"]["visual_join_state"] != "VISUAL_READY"

    # -- 6. unknown authority + stale CIO render PASS (THE attack) -------
    def test_unknown_authority_with_stale_cio_pass_is_not_visual_ready(
            self, tmp_path):
        def attack(run: Path):
            # the identity chain verifies except the CLASS: no recorded
            # authority verdict anywhere -> UNKNOWN
            ident_path = run / "MODEL" / "ARTIFACT_IDENTITY.json"
            ident = json.loads(ident_path.read_text())
            ident["visualizability_class"] = None
            ident_path.write_text(json.dumps(ident))
            (run / "BRIDGE_REPORT.json").unlink()
        run = _mutated(tmp_path, "ts_c24_a6", attack)
        # the STALE CIO render PASS rides in the projection's renders
        # block — exactly the shape the directive attacks
        tab = dossier_mod.design_tab(_session(run), {
            "geometry": _geom_block(_ids[run.name]),
            "visualization": {"renders": {
                "status": "OK",
                "visual_gate": {"verdict": "COMPLETE_PASS"}}}})
        assert tab["geometry_state"] != "visual_complete"
        assert tab["geometry_state"] != "geometry_available" or \
            tab["presentation_cause"] != ""
        rows = {r["key"]: r for r in dossier_mod.pipeline_projection(
            _session(run), run, False,
            {"package_state": {"state": "NOT_PRODUCED"}},
            {"retrieval_state": "RETRIEVED", "retrieved_count": 3}, tab)}
        assert rows["visualization"]["status"] != "RECEIVED"
        # and the contract itself never certifies an unclassed artifact
        out = _evaluator_state(run)
        assert out["contract"]["geometry_state"] == "geometry_unverified"
        assert out["contract"]["engineering_authority"] == "UNKNOWN"
        assert out["join"]["visual_join_state"] != "VISUAL_READY"

    # -- 7. conceptual authority + render PASS ---------------------------
    def test_conceptual_authority_with_render_pass_never_upgrades(
            self, tmp_path):
        def attack(run: Path):
            ident_path = run / "MODEL" / "ARTIFACT_IDENTITY.json"
            ident = json.loads(ident_path.read_text())
            ident["visualizability_class"] = "SYSTEM_3D"
            ident_path.write_text(json.dumps(ident))
            (run / "BRIDGE_REPORT.json").write_text(json.dumps({
                "outcome": "COMPLETED",
                "visualizability_class": "SYSTEM_3D",
                "geometry": {"generation_id": "gen-1",
                             "visualizability_class": "SYSTEM_3D"}}))
        run = _mutated(tmp_path, "ts_c24_a7", attack)
        tab = dossier_mod.design_tab(_session(run), {
            "geometry": _geom_block(_ids[run.name]),
            "visualization": {"renders": {
                "status": "OK",
                "visual_gate": {"verdict": "PASS"}}}})
        assert tab["geometry_state"] == "geometry_available"
        assert tab["presentation_cause"] == "legacy_render_unverified"
        assert tab["epistemic_class"] == "HYPOTHESIZED"
        rows = {r["key"]: r for r in dossier_mod.pipeline_projection(
            _session(run), run, False,
            {"package_state": {"state": "NOT_PRODUCED"}},
            {"retrieval_state": "RETRIEVED", "retrieved_count": 3}, tab)}
        assert rows["visualization"]["blocked_class"] \
            == "LEGACY_RENDER_UNVERIFIED"
        assert rows["visualization"]["status"] == "STOPPED"

    # -- 8. GLB valid but wrong generation --------------------------------
    def test_valid_glb_wrong_generation_fails(self, tmp_path):
        def attack(run: Path):
            ident_path = run / "MODEL" / "ARTIFACT_IDENTITY.json"
            ident = json.loads(ident_path.read_text())
            ident["generation_id"] = "gen-9"
            ident_path.write_text(json.dumps(ident))
            br = json.loads((run / "BRIDGE_REPORT.json").read_text())
            br["geometry"]["artifact_identity"] = ident
            (run / "BRIDGE_REPORT.json").write_text(json.dumps(br))
        run = _mutated(tmp_path, "ts_c24_a8", attack)
        out = _evaluator_state(run)
        c = out["contract"]
        assert c["geometry_state"] == "geometry_unverified"
        assert c["visual_input_ready"] is False
        assert any("generation" in f.lower()
                   for f in c["verification"]["certification_failures"])

    # -- 9/10/11. the spec lineage is MANDATORY ---------------------------
    def test_receipt_without_spec_sha_fails_release_chain(self, tmp_path):
        """Attack 9 + the C2.3-era lenient case superseded: the receipt
        carries no geometry_spec_sha256 while the spec file exists."""
        def attack(run: Path):
            p = run / "MODEL" / "3D" / "VISUAL_COMPILER_INVOCATION.json"
            rec = json.loads(p.read_text())
            rec["geometry_spec_sha256"] = None
            p.write_text(json.dumps(rec))
        run = _mutated(tmp_path, "ts_c24_a9", attack)
        out = _evaluator_state(run)
        assert out["join"]["visual_join_state"] == "RELEASE_UNVERIFIED"
        chain = out["join"]["release_chain"]
        assert chain["first_failure"] == "invocation_receipt_identity"

    def test_receipt_spec_sha_without_spec_file_fails(self, tmp_path):
        """Attack 10: the receipt NAMES a spec sha but no
        GEOMETRY_SPEC.json exists on disk — the equality is unprovable,
        and an unprovable lineage is a failed rung."""
        def attack(run: Path):
            (run / "MODEL" / "GEOMETRY_SPEC.json").unlink()
        run = _mutated(tmp_path, "ts_c24_a10", attack)
        out = _evaluator_state(run)
        assert out["join"]["visual_join_state"] == "RELEASE_UNVERIFIED"
        chain = out["join"]["release_chain"]
        assert chain["first_failure"] == "invocation_receipt_identity"

    def test_both_spec_hashes_absent_fails_release_chain(self, tmp_path):
        """Attack 11 — the C2.3-era lenient pass (both terms absent ->
        unverifiable-but-not-contradicted) is SUPERSEDED: the
        geometry-spec lineage is MANDATORY for VISUAL_READY."""
        def attack(run: Path):
            (run / "MODEL" / "GEOMETRY_SPEC.json").unlink()
            p = run / "MODEL" / "3D" / "VISUAL_COMPILER_INVOCATION.json"
            rec = json.loads(p.read_text())
            rec["geometry_spec_sha256"] = None
            p.write_text(json.dumps(rec))
        run = _mutated(tmp_path, "ts_c24_a11", attack)
        out = _evaluator_state(run)
        assert out["join"]["visual_join_state"] == "RELEASE_UNVERIFIED"
        chain = out["join"]["release_chain"]
        receipt_rung = next(r for r in chain["rungs"]
                            if r["rung"] == "invocation_receipt_identity")
        assert receipt_rung["pass"] is False
        assert "mandatory" in receipt_rung["detail"]

    def test_receipt_wrong_generation_fails_generation_rung(self, tmp_path):
        """Directive item 5: artifact generation == receipt generation
        == current generation — a receipt from another generation
        fails the new generation rung."""
        def attack(run: Path):
            p = run / "MODEL" / "3D" / "VISUAL_COMPILER_INVOCATION.json"
            rec = json.loads(p.read_text())
            rec["generation_id"] = "gen-0"
            p.write_text(json.dumps(rec))
        run = _mutated(tmp_path, "ts_c24_genrung", attack)
        out = _evaluator_state(run)
        assert out["join"]["visual_join_state"] == "RELEASE_UNVERIFIED"
        chain = out["join"]["release_chain"]
        gen_rung = next(r for r in chain["rungs"]
                        if r["rung"] == "generation_identity")
        assert gen_rung["pass"] is False
        assert "generation" in gen_rung["detail"]

    # -- 12. old legacy projection + visual PASS --------------------------
    def test_legacy_projection_with_visual_pass_never_upgrades(self):
        """The directive's most important attack: an old legacy
        projection (boolean presence, a session-only payload, a stale
        CIO gate PASS) must NEVER upgrade into current VISUAL_READY.
        The fallback path is eliminated — the strict evaluator is the
        only current-state authority."""
        out = dossier_mod._geometry_state(
            {"session_id": "legacy", "status": "COMPLETE",
             "run_dir": None, "package": {}},
            {"present": True},
            {"status": "OK", "visual_gate": {"verdict": "PASS"}},
            running=False)
        assert out["geometry_state"] != "visual_complete"
        assert out["geometry_state"] != "geometry_available"
        tab = dossier_mod.design_tab(
            {"session_id": "legacy", "status": "COMPLETE",
             "run_dir": None, "package": {}},
            {"geometry": {"present": True},
             "visualization": {"renders": {
                 "status": "OK",
                 "visual_gate": {"verdict": "COMPLETE_PASS"}}}})
        assert tab["availability"] != "AVAILABLE"


# ---------------------------------------------------------------------------
# the eliminated fallback (directive item 1) — direct proofs
# ---------------------------------------------------------------------------
class TestFallbackEliminated:
    def test_renders_cause_can_never_return_visual_complete(self):
        """Every CIO renders-block shape the fallback can see: none may
        produce visual_complete (the weak path
        undecided -> CIO fallback -> visual_complete is REMOVED)."""
        shapes = [
            {"status": "OK", "visual_gate": {"verdict": "PASS"}},
            {"status": "OK", "visual_gate": {"verdict": "COMPLETE_PASS"}},
            {"status": "SUCCEEDED", "visual_gate": {"verdict": "PASS"}},
            {"status": "OK", "visual_gate": {"verdict": "FAIL"}},
            {"status": "RENDER_SKIPPED_LOW_MEMORY"},
            {"status": "RUNNING"},
            {},
        ]
        for renders in shapes:
            state, cause, _detail = dossier_mod._renders_cause(renders)
            assert state != "visual_complete", renders

    def test_stale_cio_pass_becomes_explicitly_unverified(self):
        state, cause, detail = dossier_mod._renders_cause(
            {"status": "OK", "visual_gate": {"verdict": "COMPLETE_PASS"}})
        assert state == "geometry_available"
        assert cause == "legacy_render_unverified"
        assert "unverified" in (detail or "")
        # readable as historical state — but explicitly unverified

    def test_source_pin_the_fallback_has_no_visual_complete(self):
        src = (REPO / "toscanini" / "dossier.py").read_text()
        renders_body = src[src.index("def _renders_cause"):]
        renders_body = renders_body[:renders_body.index("\ndef ")]
        # no RETURN of visual_complete in any branch (prose mentions in
        # the supersession docstring are the disclosure, not a path)
        assert 'return "visual_complete"' not in renders_body
        assert '("visual_complete"' not in renders_body
        assert '"visual_complete",' not in renders_body


# ---------------------------------------------------------------------------
# the join state vocabulary, one-evaluator coupling, clean-state replay
# ---------------------------------------------------------------------------
class TestEvaluatorCoupling:
    @pytest.mark.parametrize("mutate,name,expected", [
        (None, "ts_c24_agree_golden", "VISUAL_READY"),
        (lambda r: (r / "MODEL" / "ARTIFACT_IDENTITY.json").unlink(),
         "ts_c24_agree_noidentity", None),
        (lambda r: (r / "MODEL" / "engineering_model.glb").write_bytes(
            b"not a glTF container at all"),
         "ts_c24_agree_badformat", None),
        (lambda r: (r / "MODEL" / "3D" / "VISUAL_COMPILER_INVOCATION.json")
         .write_text(json.dumps({"kind": "VISUAL_COMPILER_INVOCATION",
                                 "schema_version": "1.1.0",
                                 "run_id": r.name,
                                 "invocation_status":
                                 "RENDER_SKIPPED_LOW_MEMORY",
                                 "skip_reason": "memory floor"})),
         "ts_c24_agree_infraskip", "RENDER_BLOCKED"),
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

    def test_clean_state_replay_is_byte_identical(self, golden: Path):
        first = json.dumps(_evaluator_state(golden), sort_keys=True)
        second = json.dumps(_evaluator_state(golden), sort_keys=True)
        assert first == second
        w = _watchdog()
        r1 = json.dumps(w.run_watchdog(golden), sort_keys=True)
        r2 = json.dumps(w.run_watchdog(golden), sort_keys=True)
        assert r1 == r2
        assert json.loads(r1)["verdict"] == "PASS"


# ---------------------------------------------------------------------------
# closed vocabularies + the authority-aware final UI state (item 6)
# ---------------------------------------------------------------------------
class TestClosedVocabulariesAndAuthority:
    def test_geometry_state_vocabulary_is_seven_values(self):
        assert dossier_mod.GEOMETRY_STATES == (
            "upstream_not_reached", "geometry_not_applicable",
            "geometry_generation_failed", "geometry_available",
            "geometry_unverified", "visual_render_failed",
            "visual_complete")

    def test_source_pins_frontend_vocabularies(self):
        ps = (WEBAPP / "lib" / "presentationState.ts").read_text()
        # the two new typed causes exist and the vocabulary stays closed
        assert '"geometry_unverified"' in ps
        assert '"legacy_render_unverified"' in ps
        # R451-C2.5 SUPERSESSION of the C2.4-era pin: the legacy
        # pre-C2.1 fallback is now the LEGACY_STATE_UNAVAILABLE branch —
        # the explicit NON-CURRENT state (a legacy payload derives no
        # current state at all; the C2.4-era
        # GEOMETRY_READY_RENDER_BLOCKED[legacy_render_unverified]
        # resolution is superseded — see the C2.5 battery)
        legacy_idx = ps.index("THE LEGACY PAYLOAD RULE")
        legacy_block = ps[legacy_idx:legacy_idx + 2200]
        assert 'state: "VISUAL_READY"' not in legacy_block
        assert 'state: "LEGACY_STATE_UNAVAILABLE"' in legacy_block
        assert 'renderBlockCause: "legacy_render_unverified"' not in \
            legacy_block
        # the VISUAL_READY branch carries the authority through — and
        # (R451-C2.5 §2) the branch exists ONLY behind the ENGINEERING
        # guard: the contradiction pairs fail closed to the non-ready
        # typed state
        visual_idx = ps.index('gstate === "visual_complete"')
        visual_block = ps[visual_idx:visual_idx + 1500]
        assert "engineeringAuthority" in visual_block
        assert 'design?.engineering_authority !== "ENGINEERING"' in \
            visual_block

    def test_source_pin_technology_ready_is_authority_gated(self):
        stage = (WEBAPP / "components" / "TechStage.tsx").read_text()
        # the label exists exactly once and sits behind the
        # ENGINEERING-authority guard inside the VISUAL_READY case
        assert stage.count('label: "Technology ready"') == 1
        assert 'view.engineeringAuthority === "CONCEPTUAL"' in stage
        assert 'view.engineeringAuthority !== "ENGINEERING"' in stage
        assert '"Conceptual model ready"' in stage
        assert '"Visualization ready — geometry authority unverified"' \
            in stage
        # the two new causes have their own labels
        assert "identity unverified" in stage
        assert "presentation state unverified" in stage

    def test_unverified_artifact_tab_is_honest(self, tmp_path):
        """A geometry_unverified run: the tab is not AVAILABLE, the
        note names the certification gap, and nothing claims
        engineering authority."""
        def attack(run: Path):
            (run / "MODEL" / "ARTIFACT_IDENTITY.json").unlink()
        run = _mutated(tmp_path, "ts_c24_tabnote", attack)
        tab = dossier_mod.design_tab(
            _session(run), {"geometry": _geom_block(_ids[run.name])})
        assert tab["availability"] != "AVAILABLE"
        assert "could not be certified" in (tab["note"] or "")
        assert tab["epistemic_class"] == "UNKNOWN"

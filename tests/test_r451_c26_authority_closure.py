"""R451-C2.6 — THE AUTHORITY CLOSURE battery: the directive's decisive
adversarial set, each proven to FAIL CLOSED, plus the fully valid fresh
chain that must keep reaching VISUAL_READY.

Operator directive R451-C2.6 (the LAST authority-hardening round: close
only the remaining authority-boundary defects; no test-count growth —
the eight decisive fixtures below are the required set).

The required adversarial set:

  1. legacy payload + convincing viewerUrl / GLB metadata / render
     metadata
     -> LEGACY_STATE_UNAVAILABLE only; no current state; the frontend
        rendering order structurally cannot mount the viewer (the
        behavioral browser proof lives in R451/C2_PRODUCT/E2E_C26;
        this battery pins the mapping and the TechStage order)
  2. artifact generation with NO independent current-generation anchor
     -> the artifact generation is never its own anchor: the
        certification fails closed (geometry_unverified / UNKNOWN /
        join undecided) and the chain's generation rung fails
  3. stale generation vs the independent persisted current generation
     -> a stale artifact never certifies
  4. projection claims a NEWER generation than the persisted anchor
     -> a projection never anchors; the contradiction fails closed
  5. diagnostic filename + valid GLB + ALL presentation artifacts
     (receipt, gate PASS, ladder, hero) + NO persisted identity
     -> verify_release_chain = NOT VERIFIED (the chain is sovereign:
        discovery never certifies)
  6. receipt = OK / render record = FAILED / gate = COMPLETE_PASS
     -> the renderer-success records contradict; RELEASE_UNVERIFIED,
        never VISUAL_READY
  7. receipt = RENDER_FAILED / render record = OK / gate = COMPLETE_PASS
     -> the receipt side blocks the join (RENDER_BLOCKED); never
        VISUAL_READY
  8. fully valid fresh chain (the positive control, Art. V)
     -> geometry_available + ENGINEERING + VISUAL_READY; the watchdog
        PASSes it

Plus the sovereignty sub-proofs (a caller glb_path that names a
different artifact can never make the chain verify; an agreeing caller
path changes nothing), the one-evaluator coupling (dossier ==
watchdog), and the byte-identical clean-state replay.
"""
from __future__ import annotations

import hashlib
import json
import struct
import sys
from pathlib import Path
from typing import Any, Dict

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


def _complete_run(run: Path, session_id="ts_r451c26_golden",
                  with_anchor: bool = True,
                  artifact_generation: str = "gen-1",
                  anchor_generation: str = "gen-1") -> Dict[str, Any]:
    """The golden chain: certified-canonical GLB + the INDEPENDENT
    persisted current-generation anchor (R451-C2.6 §2) + spec +
    identity + bridge report + receipt (1.1.0) + render record +
    COMPLETE_PASS gate + the full required presentation ladder."""
    model = run / "MODEL"
    model.mkdir(parents=True, exist_ok=True)
    glb = model / "engineering_model.glb"
    glb.write_bytes(_valid_glb())
    glb_sha = _sha(glb.read_bytes())
    (model / "GEOMETRY_SPEC.json").write_bytes(_spec_bytes())
    spec_file_sha = _sha((model / "GEOMETRY_SPEC.json").read_bytes())
    identity = {
        "artifact": "ARTIFACT_IDENTITY",
        "run_id": session_id,
        "generation_id": artifact_generation,
        "geometry_hash": glb_sha,
        "glb_path": str(glb),
        "glb_disk_sha256": glb_sha,
        "glb_matches_geometry_hash": True,
        "visualizability_class": "ENGINEERING_3D",
    }
    (model / "ARTIFACT_IDENTITY.json").write_text(json.dumps(identity))
    if with_anchor:
        # R451-C2.6 §2 — the INDEPENDENT persisted current-generation
        # anchor: DESIGN_LINEAGE.json's current-generation entry with
        # its OWN generation identity (never the artifact's self-
        # anchor).
        (model / "DESIGN_LINEAGE.json").write_text(json.dumps({
            "artifact": "DESIGN_LINEAGE",
            "generation_models": [
                {"generation": 1, "generation_id": anchor_generation,
                 "glb": "MODEL/engineering_model.glb", "current": True}]}))
    (run / "BRIDGE_REPORT.json").write_text(json.dumps({
        "outcome": "COMPLETED",
        "visualizability_class": "ENGINEERING_3D",
        "geometry": {"generation_id": artifact_generation,
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
        "run_id": session_id, "generation_id": artifact_generation,
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
        "invention_id": "INV-R451C26",
        "problem": "fouling in compact heat exchangers",
        "mechanism": "self-clearing channel geometry",
        "causal_chain": ["fouling accumulates", "the geometry sheds it",
                         "the pressure drop stays in band"],
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


def _watchdog_report(run: Path) -> Dict[str, Any]:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "r451_watchdog_c26", REPO / "scripts" / "r451_c2_watchdog.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.run_watchdog(run)


_ids: Dict[str, Dict[str, Any]] = {}


@pytest.fixture()
def golden(tmp_path: Path) -> Path:
    run = tmp_path / "ts_r451c26_golden"
    _ids[run.name] = _complete_run(run)
    return run


def _mutated(tmp_path: Path, name: str, mutate) -> Path:
    run = tmp_path / name
    _ids[run.name] = _complete_run(run, session_id=name)
    mutate(run)
    return run


# ---------------------------------------------------------------------------
# FIXTURE 8 FIRST — the positive control (Art. V: not a universal rejector)
# ---------------------------------------------------------------------------
class TestPositiveControl:
    def test_fully_valid_fresh_chain_reaches_visual_ready(
            self, golden: Path):
        out = _evaluator_state(golden)
        c = out["contract"]
        assert c["geometry_state"] == "geometry_available"
        assert c["engineering_authority"] == "ENGINEERING"
        assert c["verification"]["glb_certified"] is True
        assert c["verification"]["independent_current_generation_anchor_present"] is True
        assert c["visual_input_ready"] is True
        assert out["join"]["visual_join_state"] == "VISUAL_READY"
        report = _watchdog_report(golden)
        assert report["observed_join_state"] == "VISUAL_READY"
        assert report["watchdog_verdict"] == "PASS"
        assert report["verdict"] == "PASS"

    def test_chain_rungs_name_the_certified_artifact(self, golden: Path):
        """R451-C2.6 §3: the sovereign chain's rung 1 reports the
        CERTIFIED basis (the persisted identity chain), not a filename
        resolution."""
        out = _evaluator_state(golden)
        chain = out["join"]["release_chain"]
        assert chain["verified"] is True
        rung1 = chain["rungs"][0]
        assert rung1["rung"] == "canonical_glb_identity"
        assert "certified via" in rung1["detail"]


# ---------------------------------------------------------------------------
# FIXTURE 1 — legacy payload + convincing viewerUrl / GLB metadata /
# render metadata (the mapping-level proof; the browser proof is E2E_C26)
# ---------------------------------------------------------------------------
class TestLegacyViewerImpossible:
    def test_legacy_payload_with_convincing_metadata_maps_non_current(self):
        import subprocess
        import tempfile
        # compile the REAL mapping module (the same code the browser
        # ships) exactly as the UI battery does, then drive it with the
        # platform's node — a behavioral proof, not a source grep
        out_dir = Path(tempfile.mkdtemp(prefix="r451c26-map-"))
        tsc = WEBAPP / "node_modules" / ".bin" / "tsc"
        subprocess.run([str(tsc), str(WEBAPP / "lib" / "presentationState.ts"),
                        "--outDir", str(out_dir), "--module", "commonjs",
                        "--target", "es2020", "--skipLibCheck",
                        "--noEmitOnError"], check=True, capture_output=True)
        compiled = sorted(out_dir.rglob("presentationState.js"))
        assert compiled, "the mapping module did not compile"
        driver = out_dir / "attack.js"
        # THE ATTACK: a legacy projection with NO typed geometry state
        # whose raw fields are maximally convincing — availability, a
        # viewerUrl-shaped glb route, render status OK, gate PASS
        driver.write_text(json.dumps({
            "require": str(compiled[0]),
            "detail": {"status": "COMPLETE", "final_status": None,
                       "user_state_view": {
                           "user_state": "COMPLETED_CANDIDATE",
                           "finished": True, "found_something": True,
                           "rejected": False, "package_available": True},
                       "run_state": None},
            "dossier": {"tabs": {"design": {
                "availability": "AVAILABLE",
                "glb": "/api/run/x/model/engineering_model.glb",
                "renders": {"status": "OK",
                            "visual_gate": {"verdict": "COMPLETE_PASS"}},
                "geometry_class": "ENGINEERING_3D",
            }, "evidence": None}}}))
        driver2 = out_dir / "drive.js"
        driver2.write_text(
            "const fs = require('fs');\n"
            "const spec = JSON.parse(fs.readFileSync(process.argv[2]));\n"
            "const ps = require(spec.require);\n"
            "const view = ps.resolvePresentationState(spec.detail,\n"
            "  spec.dossier);\n"
            "console.log(JSON.stringify(view));\n")
        proc = subprocess.run(["node", str(driver2), str(driver)],
                              capture_output=True, text=True, check=True)
        view = json.loads(proc.stdout.strip().splitlines()[-1])
        assert view["state"] == "LEGACY_STATE_UNAVAILABLE"
        # the four forbidden current states are structurally unreachable
        assert view["state"] != "VISUAL_READY"
        assert view["state"] != "GEOMETRY_READY_RENDER_BLOCKED"
        assert view["state"] != "TECHNOLOGY_NOT_ESTABLISHED"
        assert view["state"] != "SCIENTIFIC_REJECTION"
        # the view carries NO viewer/model field a legacy payload could
        # mount — the mapping cannot even EXPRESS a viewerUrl
        for field in ("glb", "viewerUrl", "modelUrl", "model",
                      "canonicalGlb", "visualization"):
            assert field not in view
        assert view["infrastructurePaused"] is False

    def test_techstage_renders_legacy_hero_first_and_viewer_never(self):
        """SOURCE PIN (R451-C2.6 §1): the hero-viewport resolves the
        legacy state FIRST — before any viewerUrl branch — and
        viewerUrl is computed null under the legacy state; the R441
        gate badge is likewise guarded against a legacy payload."""
        stage = (WEBAPP / "components" / "TechStage.tsx").read_text()
        viewport_idx = stage.index('data-hero-viewport')
        viewport = stage[viewport_idx:viewport_idx + 2000]
        # ORDER: the legacy hero branch is the FIRST branch of the
        # hero-viewport ternary — the viewer branch cannot pre-empt it
        legacy_branch = viewport.index(
            'view.state === "LEGACY_STATE_UNAVAILABLE" ?')
        viewer_branch = viewport.index(") : viewerUrl ? (")
        assert legacy_branch < viewer_branch
        # the viewerUrl computation is null under the legacy state
        head = stage[:viewport_idx]
        assert 'const legacyUnavailable = ' in head
        guard = head.index("const legacyUnavailable = ")
        block = head[guard:head.index(";", guard)]
        assert 'view.state === "LEGACY_STATE_UNAVAILABLE"' in block
        hero_glb_idx = head.index("const heroGlb =")
        assert "!legacyUnavailable" in head[hero_glb_idx:hero_glb_idx + 220]
        # the gate badge never renders for a legacy payload
        badge_idx = stage.index("gateVerdict && !legacyUnavailable")
        assert badge_idx > viewport_idx


# ---------------------------------------------------------------------------
# FIXTURE 2 — artifact generation with NO independent current-generation
# anchor (R451-C2.6 §2: the artifact generation is never its own anchor)
# ---------------------------------------------------------------------------
class TestNoIndependentAnchor:
    def test_anchorless_artifact_never_certifies(self, tmp_path):
        def strip_anchor(run: Path):
            (run / "MODEL" / "DESIGN_LINEAGE.json").unlink()
        run = _mutated(tmp_path, "ts_c26_noanchor", strip_anchor)
        out = _evaluator_state(run)
        c = out["contract"]
        # the certification fails closed at the generation step
        assert c["verification"]["glb_certified"] is False
        assert c["verification"][
            "independent_current_generation_anchor_present"] is False
        assert c["verification"]["current_generation_anchor"] is None
        # the geometry boundary: geometry_unverified (explicit, typed)
        assert c["geometry_state"] == "geometry_unverified"
        # the authority boundary: UNKNOWN
        assert c["engineering_authority"] == "UNKNOWN"
        # the join is undecided — never ready
        assert out["join"]["visual_join_state"] != "VISUAL_READY"
        failures = c["verification"]["certification_failures"]
        assert any("independent persisted current-generation anchor" in f
                   for f in failures)
        assert any("never its own anchor" in f for f in failures)

    def test_anchorless_chain_generation_rung_fails(self, tmp_path):
        """The release-chain boundary: RELEASE_UNVERIFIED — the
        generation identity cannot hold three ways without the
        independent persisted anchor."""
        def strip_anchor(run: Path):
            (run / "MODEL" / "DESIGN_LINEAGE.json").unlink()
        run = _mutated(tmp_path, "ts_c26_noanchor_chain", strip_anchor)
        out = _evaluator_state(run)
        # geometry_unverified leaves the join undecided — the chain
        # boundary is verified directly on the same run
        chain = vj.verify_release_chain(run)
        assert chain["verified"] is False
        gen_rung = next(r for r in chain["rungs"]
                        if r["rung"] == "generation_identity")
        assert gen_rung["pass"] is False
        assert "independent persisted current-generation" in \
            gen_rung["detail"]

    def test_anchorless_watchdog_never_announces_ready(self, tmp_path):
        def strip_anchor(run: Path):
            (run / "MODEL" / "DESIGN_LINEAGE.json").unlink()
        run = _mutated(tmp_path, "ts_c26_noanchor_wd", strip_anchor)
        report = _watchdog_report(run)
        assert report["observed_join_state"] != "VISUAL_READY"


# ---------------------------------------------------------------------------
# FIXTURE 3 — stale generation vs the independent persisted current
# generation
# ---------------------------------------------------------------------------
class TestStaleGeneration:
    def test_stale_artifact_never_certifies(self, tmp_path):
        """The anchor records gen-2 as current; the artifact (and its
        whole recorded chain) still says gen-1 — stale never certifies,
        and the projection's agreeing gen-1 cannot rescue it."""
        def stale(run: Path):
            lineage_path = run / "MODEL" / "DESIGN_LINEAGE.json"
            lineage = json.loads(lineage_path.read_text())
            lineage["generation_models"][0]["generation_id"] = "gen-2"
            lineage_path.write_text(json.dumps(lineage))
            # a NEWER artifact also exists (the current generation's) —
            # the certified artifact must be the anchor-named CURRENT
            # one; here the identity still names the STALE file
        run = _mutated(tmp_path, "ts_c26_stale", stale)
        out = _evaluator_state(run)
        c = out["contract"]
        assert c["verification"]["glb_certified"] is False
        assert c["verification"]["current_generation_anchor"] == "gen-2"
        assert c["geometry_state"] == "geometry_unverified"
        assert c["engineering_authority"] == "UNKNOWN"
        assert out["join"]["visual_join_state"] != "VISUAL_READY"
        failures = c["verification"]["certification_failures"]
        assert any("stale artifact never certifies" in f for f in failures)


# ---------------------------------------------------------------------------
# FIXTURE 4 — projection claims a NEWER generation than the persisted
# anchor
# ---------------------------------------------------------------------------
class TestProjectionNewerGeneration:
    def test_projection_newer_generation_never_anchors(self, tmp_path):
        """A forged projection claiming gen-9 (newer than the persisted
        gen-1 chain) fails the certification closed — the projection
        never anchors the current generation, never promotes it."""
        run = _mutated(tmp_path, "ts_c26_proj_newer", lambda r: None)
        geom = {**_geom_block(_ids[run.name]),
                "generation_id": "gen-9",
                "artifact_identity": {"generation_id": "gen-9"}}
        out = _evaluator_state(run, geom_override=geom)
        c = out["contract"]
        assert c["verification"]["glb_certified"] is False
        assert c["geometry_state"] == "geometry_unverified"
        assert c["engineering_authority"] == "UNKNOWN"
        assert c["visual_input_ready"] is False
        assert out["join"]["visual_join_state"] != "VISUAL_READY"
        failures = c["verification"]["certification_failures"]
        assert any("contradict" in f.lower() for f in failures)


# ---------------------------------------------------------------------------
# FIXTURE 5 — diagnostic filename + valid GLB + ALL presentation
# artifacts + NO persisted identity -> verify_release_chain NOT VERIFIED
# (R451-C2.6 §3: the chain is sovereign)
# ---------------------------------------------------------------------------
class TestChainSovereignty:
    def _strip_identity(self, run: Path) -> None:
        (run / "MODEL" / "ARTIFACT_IDENTITY.json").unlink()
        (run / "MODEL" / "DESIGN_LINEAGE.json").unlink()

    def test_diagnostic_filename_full_set_chain_not_verified(
            self, tmp_path):
        """THE directive attack: identity absent + a VALID,
        correctly-named GLB + a complete render set + gate PASS — the
        filename resolver finds the candidate, the certification has
        nothing to certify WITH, and the sovereign chain reports NOT
        VERIFIED."""
        run = _mutated(tmp_path, "ts_c26_diagchain", self._strip_identity)
        # every presentation artifact is on disk and consistent with the
        # diagnostic candidate's bytes (the most convincing forgery)
        glb = _ids[run.name]["glb_path"]
        glb_sha = _sha(glb.read_bytes())
        m3d = run / "MODEL" / "3D"
        rec = json.loads((m3d / "render_record.json").read_text())
        rec["source_glb_sha256"] = glb_sha
        (m3d / "render_record.json").write_text(json.dumps(rec))
        receipt_path = m3d / "VISUAL_COMPILER_INVOCATION.json"
        receipt = json.loads(receipt_path.read_text())
        receipt["glb_sha256"] = glb_sha
        receipt_path.write_text(json.dumps(receipt))
        # the locator DIAGNOSES the candidate...
        diag = vj.resolve_canonical_glb(run)
        assert diag is not None and diag.is_file()
        # ...and the SOVEREIGN chain still refuses to verify
        chain = vj.verify_release_chain(run)
        assert chain["verified"] is False
        assert chain["first_failure"] == "canonical_glb_identity"
        rung1 = chain["rungs"][0]
        assert "does not certify" in rung1["detail"]
        # through the evaluator: geometry_unverified, never ready
        out = _evaluator_state(run)
        assert out["contract"]["geometry_state"] == "geometry_unverified"
        assert out["join"]["visual_join_state"] != "VISUAL_READY"

    def test_caller_glb_path_cannot_weaken_identity(self, tmp_path):
        """A caller-provided glb_path naming a DIFFERENT valid GLB can
        never make the chain verify — the persisted-identity
        requirement is not weakened by the caller's path (it fails
        closed twice: no identity to certify, and the caller path
        contradicts the certification)."""
        def decoy(run: Path):
            self._strip_identity(run)
            decoy_glb = run / "MODEL" / "model-777.glb"
            decoy_glb.write_bytes(_valid_glb(
                b'{"asset":{"version":"2.0"},"scenes":[]}'))
            _ids[run.name]["decoy"] = decoy_glb
        run = _mutated(tmp_path, "ts_c26_callerpath", decoy)
        chain = vj.verify_release_chain(run, _ids[run.name]["decoy"])
        assert chain["verified"] is False
        rung1 = chain["rungs"][0]
        assert rung1["pass"] is False
        assert "never weakens the persisted-identity requirement" in \
            rung1["detail"]

    def test_agreeing_caller_path_changes_nothing(self, golden: Path):
        """The benign case: a caller path that names the SAME certified
        artifact is recorded harmlessly — no false negative."""
        chain = vj.verify_release_chain(golden,
                                        _ids[golden.name]["glb_path"])
        assert chain["verified"] is True


# ---------------------------------------------------------------------------
# FIXTURE 6 — receipt OK / render record FAILED / gate COMPLETE_PASS
# ---------------------------------------------------------------------------
class TestReceiptRenderContradiction:
    def test_receipt_ok_record_failed_never_visual_ready(self, tmp_path):
        """R451-C2.6 §4: the renderer-success records must agree. The
        production writer copies the record's status into the receipt
        verbatim — a receipt that says OK over a record that says
        RENDER_FAILED is tampering; the rung fails closed and the join
        announces RELEASE_UNVERIFIED, never VISUAL_READY."""
        def contradict(run: Path):
            m3d = run / "MODEL" / "3D"
            rec = json.loads((m3d / "render_record.json").read_text())
            rec["status"] = "RENDER_FAILED"
            (m3d / "render_record.json").write_text(json.dumps(rec))
        run = _mutated(tmp_path, "ts_c26_rec_fail", contradict)
        out = _evaluator_state(run)
        assert out["join"]["visual_join_state"] == "RELEASE_UNVERIFIED"
        chain = out["join"]["release_chain"]
        rung4 = next(r for r in chain["rungs"]
                     if r["rung"] == "render_record_identity")
        assert rung4["pass"] is False
        assert "renderer-success records contradict" in rung4["detail"]
        # the watchdog observes the join failure — no scientific verdict
        report = _watchdog_report(run)
        assert report["observed_join_state"] == "RELEASE_UNVERIFIED"
        assert report["watchdog_verdict"] == "JOIN_FAILURE_OBSERVED"

    def test_gate_pass_with_contradiction_is_not_ready(self, tmp_path):
        """The same contradiction with the gate explicitly COMPLETE_PASS:
        neither record may produce VISUAL_READY (the gate cannot
        arbitrate between two records that disagree about whether the
        renderer even ran)."""
        def contradict(run: Path):
            m3d = run / "MODEL" / "3D"
            rec = json.loads((m3d / "render_record.json").read_text())
            rec["status"] = "RENDER_TIMEOUT"
            (m3d / "render_record.json").write_text(json.dumps(rec))
        run = _mutated(tmp_path, "ts_c26_rec_timeout", contradict)
        out = _evaluator_state(run)
        assert out["join"]["visual_join_state"] != "VISUAL_READY"


# ---------------------------------------------------------------------------
# FIXTURE 7 — receipt RENDER_FAILED / render record OK / gate
# COMPLETE_PASS
# ---------------------------------------------------------------------------
class TestRenderReceiptContradiction:
    def test_receipt_failed_record_ok_never_visual_ready(self, tmp_path):
        """The reverse contradiction: the receipt typed a failure, the
        record claims success. The receipt side blocks the join
        (RENDER_BLOCKED — the boundary's own invocation authority);
        VISUAL_READY is unreachable, and the record-side success claim
        cannot resurrect it."""
        def contradict(run: Path):
            m3d = run / "MODEL" / "3D"
            receipt_path = m3d / "VISUAL_COMPILER_INVOCATION.json"
            receipt = json.loads(receipt_path.read_text())
            receipt["invocation_status"] = "RENDER_FAILED"
            receipt["skip_reason"] = "the renderer recorded RENDER_FAILED"
            receipt_path.write_text(json.dumps(receipt))
        run = _mutated(tmp_path, "ts_c26_rx_fail", contradict)
        out = _evaluator_state(run)
        assert out["join"]["visual_join_state"] == "RENDER_BLOCKED"
        assert out["join"]["visual_join_state"] != "VISUAL_READY"
        # belt: the sovereign chain's cross-check catches the same
        # contradiction when the chain is evaluated directly
        chain = vj.verify_release_chain(run)
        assert chain["verified"] is False
        rung4 = next(r for r in chain["rungs"]
                     if r["rung"] == "render_record_identity")
        assert "renderer-success records contradict" in rung4["detail"]


# ---------------------------------------------------------------------------
# the one-evaluator coupling + the clean-state replay
# ---------------------------------------------------------------------------
class TestCouplingAndDeterminism:
    def test_dossier_and_watchdog_agree_on_every_fixture(
            self, tmp_path):
        """ONE evaluator: the dossier's design tab and the watchdog
        announce the SAME state on the new fixture shapes (golden,
        anchorless, contradictory records)."""
        shapes = []
        golden = tmp_path / "ts_c26_golden"
        _ids[golden.name] = _complete_run(golden)
        shapes.append(golden)
        noanchor = tmp_path / "ts_c26_cpl_noanchor"
        _ids[noanchor.name] = _complete_run(noanchor,
                                            session_id=noanchor.name)
        (noanchor / "MODEL" / "DESIGN_LINEAGE.json").unlink()
        shapes.append(noanchor)
        contradicted = tmp_path / "ts_c26_cpl_contra"
        _ids[contradicted.name] = _complete_run(contradicted,
                                                session_id=contradicted.name)
        rec_path = (contradicted / "MODEL" / "3D" /
                    "render_record.json")
        rec = json.loads(rec_path.read_text())
        rec["status"] = "RENDER_FAILED"
        rec_path.write_text(json.dumps(rec))
        shapes.append(contradicted)
        for run in shapes:
            session = json.loads((run / "session.json").read_text())
            session.setdefault("run_dir", str(run))
            session.setdefault("session_id", run.name)
            geom = _geom_block(_ids[run.name])
            tab = dossier_mod.design_tab(session, {"geometry": geom})
            report = _watchdog_report(run)
            assert tab["visual_join_state"] == \
                report["observed_join_state"]
            assert tab["geometry_state"] in dossier_mod.GEOMETRY_STATES
            assert report["watchdog_verdict"] in \
                ("PASS", "INTEGRITY_VIOLATION", "JOIN_FAILURE_OBSERVED")

    def test_clean_state_replay_is_byte_identical(self, golden: Path):
        out1 = _evaluator_state(golden)
        out2 = _evaluator_state(golden)
        assert json.dumps(out1, sort_keys=True) == \
            json.dumps(out2, sort_keys=True)
        r1 = _watchdog_report(golden)
        r2 = _watchdog_report(golden)
        assert json.dumps(r1, sort_keys=True) == \
            json.dumps(r2, sort_keys=True)

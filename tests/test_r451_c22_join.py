"""R451-C2.2 — Canonical Presentation-State Integrity + Automatic
Geometry-to-Visual Continuity (the adversarial battery).

Operator directive R451-C2.2, covered here:

  §2  The geometry state is ARTIFACT-CONTRACT-driven
      (toscanini/dossier.py::_geometry_artifact_contract): the
      PARAMETRIC_MODEL.json alone NEVER promotes a run into
      "engineering model ready"; recorded chain failures/not-applicable
      verdicts decide. Negative controls included.
  §3  The pipeline strip's milestones are CANONICAL-RECORD predicates:
      Mechanism needs a mechanism RECORD (a premise gate that always
      executed never stands in for it); Invention needs the canonical
      invention record; Engineering needs the realization AND its
      authoritative valid state.
  §4  Package BLOCKED is never automatically PAUSED_INFRASTRUCTURE —
      the canonical blocked stage/reason/release verdict decide
      (VISUAL_GATE / PACKAGE_INTEGRITY / SCIENTIFIC / INFRASTRUCTURE).
  §5  The invocation receipt carries the directive's exact field
      contract (schema 1.1.0) incl. render_record_reference; the join
      evaluator (toscanini/visual_join.py) proves
      geometry->invocation->render->gate->hero with NO silent gap.
  §6  The watchdog's join-state derivation: valid GLB + no invocation
      -> FAIL; + invocation + no render record -> FAIL/pending;
      render + gate fail -> STOPPED; render + gate pass -> VISUAL_READY.
  §7  The C1/C2 boundary is pinned: the presentation layer READS the
      chain and never imports or mutates engineering machinery.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from toscanini import dossier as dossier_mod  # noqa: E402
from toscanini import visual_join as vj  # noqa: E402

WEBAPP = REPO / "TOSCANINI_UI" / "webapp"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _session(status="COMPLETE", run_dir=None, final_status=None) -> dict:
    return {
        "session_id": "ts_r451c22_test",
        "title": "hydropower turbine sediment erosion",
        "user_text": "hydropower turbine sediment erosion",
        "status": status,
        "final_status": final_status,
        "run_dir": str(run_dir) if run_dir else None,
        "package": {},
    }


def _geom_state(geom=None, renders=None, running=False, session=None):
    return dossier_mod._geometry_state(
        session or {}, geom or {}, renders or {}, running)


def _write_receipt(run: Path, **fields) -> None:
    m3d = run / "MODEL" / "3D"
    m3d.mkdir(parents=True, exist_ok=True)
    receipt = {
        "kind": "VISUAL_COMPILER_INVOCATION",
        "schema_version": "1.1.0",
        "run_id": run.name,
        "generation_id": "gen-1",
        "glb_sha256": None,
        "geometry_spec_sha256": None,
        "visual_compiler_version": "VISUAL_COMPILER_HEADLESS_THREE",
        "invocation_status": "RENDER_SKIPPED_LOW_MEMORY",
        "gate_version": "test",
        "invoked_at": "2026-09-13T00:00:00Z",
        "skip_reason": None,
        "render_record_reference": None,
        "output_directory": str(m3d),
    }
    receipt.update(fields)
    (m3d / "VISUAL_COMPILER_INVOCATION.json").write_text(
        json.dumps(receipt))


# ---------------------------------------------------------------------------
# 1. §2 — the artifact contract + negative controls
# ---------------------------------------------------------------------------
class TestArtifactContract:
    def test_parametric_model_alone_never_promotes(self):
        """THE directive's negative control: PARAMETRIC_MODEL.json
        alone (present=True through the definition) is NOT
        geometry_available, and the design tab is NEVER promoted into
        the engineering-model-ready branch."""
        out = _geom_state({"present": True,
                           "parametric_model_present": True,
                           "glb": None, "step": []},
                          session=_session(status="COMPLETE"))
        assert out["geometry_state"] == "geometry_generation_failed"
        assert out["presentation_cause"] is None
        assert "no geometry artifact was produced" \
            in out["geometry_state_detail"]

        tab = dossier_mod.design_tab(
            _session(status="COMPLETE"),
            {"geometry": {"present": True,
                          "parametric_model_present": True,
                          "glb": None, "step": []}})
        assert tab["availability"] == "UNAVAILABLE"
        assert tab["epistemic_class"] != "ENGINEERING_DEFINED"

    def test_parametric_model_running_is_not_a_failure(self):
        """Art. LXI: a live run whose definition exists but whose
        artifact is not produced yet is upstream_not_reached — never a
        failure, never 'engineering model ready'."""
        out = _geom_state({"present": True,
                           "parametric_model_present": True,
                           "glb": None, "step": []},
                          running=True,
                          session=_session(status="RUNNING"))
        assert out["geometry_state"] == "upstream_not_reached"
        assert "has not been produced yet" in \
            (out["geometry_state_detail"] or "")

    def test_bridge_geometry_failed_is_generation_failed(self):
        out = _geom_state({"present": False,
                           "bridge_outcome": "GEOMETRY_FAILED",
                           "bridge_why": "CAD_BUILD_FAILURE: kernel"})
        assert out["geometry_state"] == "geometry_generation_failed"

    def test_cad_ledger_rejected_is_generation_failed(self, tmp_path):
        (tmp_path / "CAD_PIPELINE_LEDGER.json").write_text(json.dumps(
            {"outcome": "MODEL_REJECTED_BY_GEOMETRY_GATES"}))
        out = _geom_state({"present": False,
                           "parametric_model_present": True,
                           "glb": None, "step": []},
                          session=_session(run_dir=tmp_path))
        assert out["geometry_state"] == "geometry_generation_failed"
        assert "MODEL_REJECTED_BY_GEOMETRY_GATES" in \
            out["geometry_state_detail"]

    def test_cad_ledger_not_applicable(self, tmp_path):
        (tmp_path / "CAD_PIPELINE_LEDGER.json").write_text(json.dumps(
            {"outcome": "NOT_APPLICABLE_NO_GEOMETRY"}))
        out = _geom_state({"present": False, "glb": None, "step": []},
                          session=_session(run_dir=tmp_path))
        assert out["geometry_state"] == "geometry_not_applicable"

    def test_cad_ledger_transport_block_is_never_a_failure(self, tmp_path):
        """Art. LXI: BLOCKED_TRANSPORT is infrastructure — the state
        stays upstream_not_reached and the detail names the ledger."""
        (tmp_path / "CAD_PIPELINE_LEDGER.json").write_text(json.dumps(
            {"outcome": "BLOCKED_TRANSPORT"}))
        out = _geom_state({"present": False, "glb": None, "step": []},
                          session=_session(run_dir=tmp_path))
        assert out["geometry_state"] == "upstream_not_reached"
        assert "infrastructure" in (out["geometry_state_detail"] or "")

    def test_glb_artifact_is_geometry_available(self):
        out = _geom_state({"present": True,
                           "glb": "/api/run/x/model", "step": []})
        assert out["geometry_state"] == "geometry_available"

    def test_step_artifact_is_geometry_available(self):
        out = _geom_state({"present": True, "glb": None,
                           "step": ["/api/run/x/step/0"]})
        assert out["geometry_state"] == "geometry_available"

    def test_legacy_projection_still_readable(self):
        """Art. XI: a pre-C2.2 CIO carrying only the boolean `present`
        stays readable — that era's strongest recorded fact."""
        out = _geom_state({"present": True})
        assert out["geometry_state"] == "geometry_available"

    def test_nothing_recorded_is_upstream(self):
        out = _geom_state({"present": False}, running=False)
        assert out["geometry_state"] == "upstream_not_reached"


# ---------------------------------------------------------------------------
# 2. §5 — the visual join evaluator (no silent gap)
# ---------------------------------------------------------------------------
class TestVisualJoin:
    def _ready_geom(self):
        return {"present": True, "glb": "/api/run/x/model", "step": []}

    def test_terminal_glb_no_receipt_no_job_is_invocation_missing(
            self, tmp_path):
        (tmp_path / "MODEL").mkdir()
        join = vj.evaluate_visual_join(
            _session(run_dir=tmp_path), self._ready_geom(), {},
            running=False, engineering_geometry_ready=True,
            geometry_state="geometry_available")
        assert join["visual_join_state"] == "INVOCATION_MISSING"
        assert "did not run" in join["visual_join_detail"]

    def test_running_glb_no_receipt_is_pending(self, tmp_path):
        join = vj.evaluate_visual_join(
            _session(run_dir=tmp_path, status="RUNNING"),
            self._ready_geom(), {}, running=True,
            engineering_geometry_ready=True,
            geometry_state="geometry_available")
        assert join["visual_join_state"] == "INVOCATION_PENDING"

    def test_pending_job_is_explicit_pending(self, tmp_path):
        m3d = tmp_path / "MODEL" / "3D"
        m3d.mkdir(parents=True)
        (m3d / "RENDER_JOB.json").write_text(json.dumps(
            {"status": "RUNNING"}))
        join = vj.evaluate_visual_join(
            _session(run_dir=tmp_path), self._ready_geom(), {},
            running=False, engineering_geometry_ready=True,
            geometry_state="geometry_available")
        assert join["visual_join_state"] == "INVOCATION_PENDING"
        assert join["pending_render_job"] == "RUNNING"

    def test_interrupted_job_is_explicit_pending(self, tmp_path):
        m3d = tmp_path / "MODEL" / "3D"
        m3d.mkdir(parents=True)
        (m3d / "RENDER_JOB.json").write_text(json.dumps(
            {"status": "INTERRUPTED"}))
        join = vj.evaluate_visual_join(
            _session(run_dir=tmp_path), self._ready_geom(), {},
            running=False, engineering_geometry_ready=True,
            geometry_state="geometry_available")
        assert join["visual_join_state"] == "INVOCATION_PENDING"
        assert join["pending_render_job"] == "INTERRUPTED"

    def test_skip_receipt_is_render_blocked_with_typed_causes(
            self, tmp_path):
        _write_receipt(tmp_path,
                       invocation_status="RENDER_SKIPPED_NO_RENDERER",
                       skip_reason="no verified Chromium/Node pair")
        join = vj.evaluate_visual_join(
            _session(run_dir=tmp_path), self._ready_geom(), {},
            running=False, engineering_geometry_ready=True,
            geometry_state="geometry_available")
        assert join["visual_join_state"] == "RENDER_BLOCKED"
        assert join["visual_join_cause"] == "renderer_unavailable"

        _write_receipt(tmp_path,
                       invocation_status="RENDER_SKIPPED_LOW_MEMORY",
                       skip_reason="below the memory floor")
        join = vj.evaluate_visual_join(
            _session(run_dir=tmp_path), self._ready_geom(), {},
            running=False, engineering_geometry_ready=True,
            geometry_state="geometry_available")
        assert join["visual_join_state"] == "RENDER_BLOCKED"
        assert join["visual_join_cause"] == "infrastructure"

    def test_rendered_claim_without_record_is_integrity_failure(
            self, tmp_path):
        _write_receipt(tmp_path, invocation_status="SUCCEEDED",
                       glb_sha256="a" * 64)
        join = vj.evaluate_visual_join(
            _session(run_dir=tmp_path), self._ready_geom(), {},
            running=False, engineering_geometry_ready=True,
            geometry_state="geometry_available")
        assert join["visual_join_state"] == "RENDER_RECORD_MISSING"

    def test_rendered_gate_fail_is_stopped_gate(self, tmp_path):
        m3d = tmp_path / "MODEL" / "3D"
        m3d.mkdir(parents=True, exist_ok=True)
        _write_receipt(tmp_path, invocation_status="SUCCEEDED",
                       glb_sha256="a" * 64,
                       render_record_reference=str(
                           m3d / "render_record.json"))
        (m3d / "render_record.json").write_text(json.dumps(
            {"source_glb_sha256": "a" * 64}))
        (m3d / "visual_gate.json").write_text(json.dumps(
            {"verdict": "FAIL"}))
        join = vj.evaluate_visual_join(
            _session(run_dir=tmp_path), self._ready_geom(), {},
            running=False, engineering_geometry_ready=True,
            geometry_state="geometry_available")
        assert join["visual_join_state"] == "STOPPED_GATE"

    def test_rendered_gate_pass_is_visual_ready(self, tmp_path):
        m3d = tmp_path / "MODEL" / "3D"
        m3d.mkdir(parents=True, exist_ok=True)
        _write_receipt(tmp_path, invocation_status="SUCCEEDED",
                       glb_sha256="a" * 64,
                       render_record_reference=str(
                           m3d / "render_record.json"))
        (m3d / "render_record.json").write_text(json.dumps(
            {"source_glb_sha256": "a" * 64}))
        (m3d / "visual_gate.json").write_text(json.dumps(
            {"verdict": "COMPLETE_PASS"}))
        join = vj.evaluate_visual_join(
            _session(run_dir=tmp_path), self._ready_geom(), {},
            running=False, engineering_geometry_ready=True,
            geometry_state="geometry_available")
        assert join["visual_join_state"] == "VISUAL_READY"

    def test_1_0_0_receipt_era_still_readable(self, tmp_path):
        """Art. XI: historical 1.0.0 receipts normalize to the 1.1.0
        names — no historical run goes unreadable."""
        m3d = tmp_path / "MODEL" / "3D"
        m3d.mkdir(parents=True)
        (m3d / "VISUAL_COMPILER_INVOCATION.json").write_text(json.dumps(
            {"kind": "VISUAL_COMPILER_INVOCATION",
             "schema_version": "1.0.0", "run_id": tmp_path.name,
             "status": "RENDER_SKIPPED_LOW_MEMORY",
             "skip_reason": "memory", "canonical_glb_sha256": "b" * 64,
             "compiler_version": "VISUAL_COMPILER_HEADLESS_THREE"}))
        receipt = vj.read_invocation_receipt(tmp_path)
        assert receipt["invocation_status"] == "RENDER_SKIPPED_LOW_MEMORY"
        assert receipt["glb_sha256"] == "b" * 64
        join = vj.evaluate_visual_join(
            _session(run_dir=tmp_path), self._ready_geom(), {},
            running=False, engineering_geometry_ready=True,
            geometry_state="geometry_available")
        assert join["visual_join_state"] == "RENDER_BLOCKED"
        assert join["visual_join_cause"] == "infrastructure"

    def test_no_run_dir_is_undecided_not_guessed(self):
        """Art. XXV: without records the evaluator decides NOTHING —
        the caller falls back to the CIO renders block."""
        join = vj.evaluate_visual_join(
            _session(), self._ready_geom(), {}, running=False,
            engineering_geometry_ready=True,
            geometry_state="geometry_available")
        assert join["visual_join_state"] is None

    def test_join_states_vocabulary_is_closed(self):
        assert vj.VISUAL_JOIN_STATES == (
            "NOT_APPLICABLE", "NOT_REACHED", "INVOCATION_PENDING",
            "INVOCATION_MISSING", "RENDER_BLOCKED",
            "RENDER_RECORD_MISSING", "STOPPED_GATE", "VISUAL_READY")


# ---------------------------------------------------------------------------
# 3. §6 — the watchdog join derivation (the four directive implications)
# ---------------------------------------------------------------------------
class TestWatchdogJoin:
    @staticmethod
    def _load():
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "r451_watchdog", REPO / "scripts" / "r451_c2_watchdog.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def _eng_glb(self, tmp_path: Path) -> Path:
        (tmp_path / "MODEL").mkdir(parents=True, exist_ok=True)
        glb = tmp_path / "MODEL" / "engineering_model.glb"
        glb.write_bytes(b"glb-bytes")
        return glb

    def test_valid_glb_no_invocation_fails(self, tmp_path):
        """§6 row 1: valid GLB + no visual invocation -> FAIL."""
        w = self._load()
        self._eng_glb(tmp_path)
        report = w.run_watchdog(tmp_path)
        assert report["verdict"] == "FAIL"
        assert report["join_state"] == "INVOCATION_MISSING"
        assert any(v["rule"] == "R8_valid_glb_requires_visual_invocation"
                   for v in report["violations"])

    def test_valid_glb_invocation_skip_is_render_blocked_not_fail(
            self, tmp_path):
        """§6 row 2a: the invocation OCCURRED (typed skip) — the join
        records RENDER_BLOCKED; no integrity violation (the typed skip
        carries its reason)."""
        w = self._load()
        self._eng_glb(tmp_path)
        _write_receipt(tmp_path,
                       invocation_status="RENDER_SKIPPED_LOW_MEMORY",
                       skip_reason="below the memory floor")
        report = w.run_watchdog(tmp_path)
        assert report["verdict"] == "PASS", report["violations"]
        assert report["join_state"] == "RENDER_BLOCKED"

    def test_valid_glb_pending_job_is_explicit_pending(self, tmp_path):
        """§6 row 2b: invocation requested (job in flight), render
        record not yet — explicit pending, never a silent wait."""
        w = self._load()
        self._eng_glb(tmp_path)
        m3d = tmp_path / "MODEL" / "3D"
        m3d.mkdir(parents=True)
        (m3d / "RENDER_JOB.json").write_text(json.dumps(
            {"status": "RUNNING"}))
        report = w.run_watchdog(tmp_path)
        assert report["verdict"] == "PASS", report["violations"]
        assert report["join_state"] == "INVOCATION_PENDING"

    def test_valid_glb_invocation_rendered_no_record_fails(
            self, tmp_path):
        """§6 row 2c: the invocation claims pixels and no render record
        exists -> FAIL (the claim is never its own proof, Art. XXIV)."""
        w = self._load()
        self._eng_glb(tmp_path)
        _write_receipt(tmp_path, invocation_status="SUCCEEDED",
                       glb_sha256="a" * 64)
        report = w.run_watchdog(tmp_path)
        assert report["verdict"] == "FAIL"
        assert report["join_state"] == "RENDER_RECORD_MISSING"
        assert any(v["rule"] == "R9_rendered_requires_render_record"
                   for v in report["violations"])

    def test_valid_glb_render_gate_fail_is_stopped(self, tmp_path):
        """§6 row 3: valid GLB + render + gate fail -> STOPPED_GATE."""
        w = self._load()
        self._eng_glb(tmp_path)
        m3d = tmp_path / "MODEL" / "3D"
        m3d.mkdir(parents=True)
        _write_receipt(tmp_path, invocation_status="SUCCEEDED",
                       glb_sha256="a" * 64)
        (m3d / "render_record.json").write_text(json.dumps(
            {"source_glb_sha256": "a" * 64}))
        (m3d / "visual_gate.json").write_text(json.dumps(
            {"verdict": "FAIL"}))
        report = w.run_watchdog(tmp_path)
        assert report["verdict"] == "PASS", report["violations"]
        assert report["join_state"] == "STOPPED_GATE"

    def test_valid_glb_render_gate_pass_is_visual_ready(self, tmp_path):
        """§6 row 4: valid GLB + render + gate pass -> VISUAL_READY."""
        import hashlib
        w = self._load()
        glb = self._eng_glb(tmp_path)
        glb_sha = hashlib.sha256(glb.read_bytes()).hexdigest()
        m3d = tmp_path / "MODEL" / "3D"
        m3d.mkdir(parents=True)
        _write_receipt(tmp_path, invocation_status="SUCCEEDED",
                       glb_sha256=glb_sha)
        (m3d / "render_record.json").write_text(json.dumps(
            {"source_glb_sha256": glb_sha,
             "scene_spec": {"model": {"node_count": 1}}}))
        (m3d / "visual_gate.json").write_text(json.dumps(
            {"verdict": "COMPLETE_PASS"}))
        from discovery_fabric.engine.visual_compiler import visual_set
        required = visual_set.required_artifacts(
            1, visual_set.DEFAULT_TURNTABLE_FRAMES)["required"]
        for name in required:
            p = m3d / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"artifact-" + name.encode().replace(b"/", b"_"))
        report = w.run_watchdog(tmp_path)
        assert report["verdict"] == "PASS", report["violations"]
        assert report["join_state"] == "VISUAL_READY"

    def test_no_glb_is_not_applicable_never_a_failure(self, tmp_path):
        """A blocked run with no GLB: NOT_APPLICABLE — the watchdog
        never manufactures a violation from an infrastructure stop
        (Art. LXI)."""
        w = self._load()
        report = w.run_watchdog(tmp_path)
        assert report["verdict"] == "PASS"
        assert report["join_state"] == "NOT_APPLICABLE"


# ---------------------------------------------------------------------------
# 4. §3 — the strip's canonical milestone predicates
# ---------------------------------------------------------------------------
class TestStripPredicates:
    def _rows(self, tmp_path=None, session=None, state=None,
              design=None, evidence=None):
        return {r["key"]: r for r in dossier_mod.pipeline_projection(
            session or _session(run_dir=tmp_path),
            tmp_path, False,
            state or {"package_state": {"state": "NOT_PRODUCED"},
                      "invention_state": {"state": "ABSENT"}},
            evidence or {"retrieval_state": "RETRIEVED",
                         "retrieved_count": 3},
            design or {"geometry_state": "upstream_not_reached"})}

    def test_problem_record_predicate(self, tmp_path):
        rows = self._rows(tmp_path)
        assert rows["problem"]["status"] == "RECEIVED"  # problem.json

    def test_problem_text_receipt_without_run_dir(self):
        rows = self._rows(None, session=_session())
        assert rows["problem"]["status"] == "RECEIVED"
        assert "saved" in (rows["problem"].get("detail") or "")

    def test_premise_gate_alone_never_establishes_mechanism(
            self, tmp_path):
        """THE §3 negative control: PREMISE_GATE always executes — its
        OK record is gate activity, NEVER a mechanism milestone
        ('any stage in a family finished' is forbidden). The run reached
        the family (so the row is honestly STOPPED on a terminal run),
        but the milestone is not RECEIVED."""
        (tmp_path / "envelope_PREMISE_GATE.json").write_text(json.dumps(
            {"stage_log": [{"stage": "PREMISE_GATE", "status": "OK"}]}))
        rows = self._rows(tmp_path)
        assert rows["mechanism"]["status"] == "STOPPED"
        assert rows["mechanism"]["status"] != "RECEIVED"

    def test_mechanism_record_establishes_mechanism(self, tmp_path):
        (tmp_path / "envelope_SYNTHESIZE.json").write_text(json.dumps(
            {"stage_log": [{"stage": "SYNTHESIZE", "status": "OK"}]}))
        rows = self._rows(tmp_path)
        assert rows["mechanism"]["status"] == "RECEIVED"

    def test_failed_mechanism_record_stops_the_row(self, tmp_path):
        (tmp_path / "envelope_SYNTHESIZE.json").write_text(json.dumps(
            {"stage_log": [{"stage": "SYNTHESIZE", "status": "ERROR"}]}))
        rows = self._rows(tmp_path)
        assert rows["mechanism"]["status"] == "STOPPED"

    def test_attack_ok_without_invention_record_is_not_received(
            self, tmp_path):
        """The Invention milestone is the CANONICAL RECORD — a family
        stage that finished never substitutes for it."""
        (tmp_path / "envelope_ATTACK.json").write_text(json.dumps(
            {"stage_log": [{"stage": "ATTACK", "status": "OK"}]}))
        rows = self._rows(tmp_path)
        assert rows["invention"]["status"] != "RECEIVED"

    def test_invention_record_establishes_invention(self, tmp_path):
        (tmp_path / "INVENTION_SPECIFICATION.json").write_text("{}")
        rows = self._rows(tmp_path)
        assert rows["invention"]["status"] == "RECEIVED"

    def test_parametric_model_alone_never_receives_engineering(
            self, tmp_path):
        """THE §3 engineering rule: artifact presence alone — and
        PARAMETRIC_MODEL.json in particular — never promotes the row
        when the authoritative state does not say valid."""
        (tmp_path / "PARAMETRIC_MODEL.json").write_text("{}")
        rows = self._rows(tmp_path, design={
            "geometry_state": "geometry_generation_failed",
            "geometry_state_detail":
                "no geometry artifact was produced",
            "geometry_contract": {"pm_only": True,
                                  "has_artifact": False}})
        assert rows["engineering"]["status"] == "STOPPED"
        assert rows["engineering"]["status"] != "RECEIVED"

    def test_engineering_received_on_typed_valid_state(self, tmp_path):
        (tmp_path / "ENGINEERING_SPECIFICATION.json").write_text("{}")
        (tmp_path / "MODEL").mkdir()
        (tmp_path / "MODEL" / "engineering_model.glb").write_bytes(b"x")
        rows = self._rows(tmp_path, design={
            "geometry_state": "geometry_available",
            "geometry_contract": {"has_artifact": True,
                                  "pm_only": False}})
        assert rows["engineering"]["status"] == "RECEIVED"

    def test_bridge_valid_realization_receives_engineering(self, tmp_path):
        (tmp_path / "BRIDGE_REPORT.json").write_text("{}")
        rows = self._rows(tmp_path, design={
            "geometry_state": "upstream_not_reached",
            "geometry_contract": {"bridge_outcome": "COMPLETED"}})
        assert rows["engineering"]["status"] == "RECEIVED"


# ---------------------------------------------------------------------------
# 5. §4 — package BLOCKED disambiguation
# ---------------------------------------------------------------------------
class TestPackageBlockedSemantics:
    def _pkg_row(self, pkg_state):
        rows = dossier_mod.pipeline_projection(
            _session(), None, False,
            {"package_state": pkg_state},
            {"retrieval_state": "RETRIEVED", "retrieved_count": 3},
            {"geometry_state": "visual_complete"})
        return next(r for r in rows if r["key"] == "package")

    def test_visual_release_block_is_visual_gate_class(self):
        row = self._pkg_row({
            "state": "BLOCKED", "blocked_stage": "QUALITY_GATE_BLOCKED",
            "blocked_reason": "the visual gate did not pass",
            "release_verdict": {"verdict": "VISUAL_RELEASE_BLOCKED"}})
        assert row["status"] == "STOPPED"
        assert row["blocked_class"] == "VISUAL_GATE"

    def test_scientific_gate_failures_are_scientific(self):
        row = self._pkg_row({
            "state": "BLOCKED", "blocked_stage": "QUALITY_GATE_BLOCKED",
            "blocked_reason": "problem fidelity",
            "release_verdict": {"verdict": "BLOCKED",
                                "failed_gates": ["B-OBJECTIVE-ABSENT",
                                                 "F-EVIDENCE-WEAK"]}})
        assert row["status"] == "STOPPED"
        assert row["blocked_class"] == "SCIENTIFIC"

    def test_integrity_gate_failures_are_package_integrity(self):
        row = self._pkg_row({
            "state": "BLOCKED", "blocked_stage": "QUALITY_GATE_BLOCKED",
            "blocked_reason": "identity divergence",
            "release_verdict": {"verdict": "BLOCKED",
                                "failed_gates": ["A-CANON-DIVERGENT",
                                                 "Q-MANIFEST-MISMATCH"]}})
        assert row["status"] == "STOPPED"
        assert row["blocked_class"] == "PACKAGE_INTEGRITY"

    def test_model_validation_is_package_integrity(self):
        row = self._pkg_row({
            "state": "BLOCKED", "blocked_stage": "MODEL_VALIDATION_FAILED",
            "blocked_reason": "the model failed validation"})
        assert row["status"] == "STOPPED"
        assert row["blocked_class"] == "PACKAGE_INTEGRITY"

    def test_transport_block_is_infrastructure(self):
        row = self._pkg_row({
            "state": "BLOCKED", "blocked_stage": "COMPILE_ERROR",
            "blocked_reason": "model transport timeout mid-build"})
        assert row["status"] == "PAUSED_INFRASTRUCTURE"
        assert row["blocked_class"] == "INFRASTRUCTURE"

    def test_unknown_stage_is_honest_unknown_never_infra(self):
        row = self._pkg_row({
            "state": "BLOCKED", "blocked_stage": "SOMETHING_ELSE",
            "blocked_reason": "an unclassifiable recorded block"})
        assert row["status"] == "STOPPED"
        assert row["blocked_class"] == "UNKNOWN"

    def test_ready_still_received(self):
        row = self._pkg_row({"state": "READY"})
        assert row["status"] == "RECEIVED"


# ---------------------------------------------------------------------------
# 6. §5 — the strip surfaces the join failure; the design tab carries it
# ---------------------------------------------------------------------------
class TestJoinSurfacing:
    def test_invocation_missing_stops_the_visualization_row(self, tmp_path):
        (tmp_path / "MODEL").mkdir()
        tab = dossier_mod.design_tab(
            _session(run_dir=tmp_path),
            {"geometry": {"present": True, "glb": "/api/run/x/model",
                          "step": []}})
        assert tab["geometry_state"] == "geometry_available"
        assert tab["visual_join_state"] == "INVOCATION_MISSING"
        rows = {r["key"]: r for r in dossier_mod.pipeline_projection(
            _session(run_dir=tmp_path), tmp_path, False,
            {"package_state": {"state": "NOT_PRODUCED"}},
            {"retrieval_state": "RETRIEVED", "retrieved_count": 3},
            tab)}
        viz = rows["visualization"]
        assert viz["status"] == "STOPPED"
        assert viz["blocked_class"] == "JOIN_FAILURE"
        assert "did not run" in (viz.get("detail") or "")

    def test_invocation_pending_reads_in_progress(self, tmp_path):
        m3d = tmp_path / "MODEL" / "3D"
        m3d.mkdir(parents=True)
        (m3d / "RENDER_JOB.json").write_text(json.dumps(
            {"status": "RUNNING"}))
        tab = dossier_mod.design_tab(
            _session(run_dir=tmp_path),
            {"geometry": {"present": True, "glb": "/api/run/x/model",
                          "step": []}})
        rows = {r["key"]: r for r in dossier_mod.pipeline_projection(
            _session(run_dir=tmp_path), tmp_path, False,
            {"package_state": {"state": "NOT_PRODUCED"}},
            {"retrieval_state": "RETRIEVED", "retrieved_count": 3},
            tab)}
        assert rows["visualization"]["status"] == "IN_PROGRESS"


# ---------------------------------------------------------------------------
# 7. §7 — the C1/C2 boundary is structural, not aspirational
# ---------------------------------------------------------------------------
class TestCoderBoundary:
    def test_presentation_layer_never_imports_engineering_machinery(self):
        """The join evaluator and the dossier projection READ records;
        they never import the CAD pipeline, never build geometry, never
        touch the model-provider logic."""
        for path in ("toscanini/visual_join.py", "toscanini/dossier.py"):
            src = (REPO / path).read_text()
            assert "import cadquery" not in src
            assert "from discovery_fabric.engine.cad_pipeline" not in src
            assert "compile_package(" not in src
            assert "rebuild_with_mutation" not in src

    def test_visual_join_writes_nothing(self):
        """Art. IX: the join evaluator is observational — no write_text,
        no mkdir, no unlink in its module source (the receipt belongs
        to the Visual Compiler, the job record to the artifact worker)."""
        src = (REPO / "toscanini" / "visual_join.py").read_text()
        assert "write_text" not in src
        assert "mkdir" not in src
        assert "unlink" not in src

    def test_source_pins_the_frontend_consumption(self):
        """The frontend consumes the typed join/contract fields and the
        five-cause copy split — never a file-existence inference."""
        src = (WEBAPP / "lib" / "presentationState.ts").read_text()
        assert "visual_join_state" in src
        assert "Presentation render not yet " in src
        assert "Presentation rendering paused " in src
        assert "Presentation render in progress." in src
        assert 'RENDER_BLOCK_CAUSES' in src
        strip = (WEBAPP / "components"
                 / "DiscoveryPipelineStrip.tsx").read_text()
        assert "data-pipeline-blocked-class" in strip
        stage = (WEBAPP / "components" / "TechStage.tsx").read_text()
        assert '"Model ready — render not started"' in stage
        assert '"Model ready — rendering paused (infrastructure)"' in stage

"""R451-C2.1 — the five-state geometry/visual battery + the pipeline strip.

Operator directive R451-C2.1 (Stop the false "3D unavailable"
interpretation). Covered here:

  1. The six-value geometry/visual vocabulary, derived by the BACKEND
     from canonical records only (toscanini/dossier.py::_geometry_state):
     upstream_not_reached / geometry_not_applicable /
     geometry_generation_failed / geometry_available /
     visual_render_failed / visual_complete.

  2. The DISCOVERY PIPELINE strip projection — the blocked run shows
     exactly the directive's strip (Problem RECEIVED, everything else
     NOT REACHED), and NOT_REACHED never carries a numeric zero
     (Art. XXV).

  3. The design tab's honest notes: the blanket "3D GEOMETRY
     UNAVAILABLE" reading is gone; State B says "Engineering
     visualization not available on this invention."

  4. Source pins (auditor governance 7: frontend claims trace to
     backend truth): the components render the directive's exact copy
     FROM the mapping output, the strip renders the backend statuses
     verbatim (and nothing when the projection is absent), and the
     mapping consumes the typed geometry_state.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from toscanini import dossier as dossier_mod  # noqa: E402

WEBAPP = REPO / "TOSCANINI_UI" / "webapp"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _session(status="COMPLETE", run_dir=None, final_status=None,
             package=None) -> dict:
    return {
        "session_id": "ts_r451c21_test",
        "title": "hydropower turbine sediment erosion",
        "user_text": "hydropower turbine sediment erosion",
        "status": status,
        "final_status": final_status,
        "run_dir": str(run_dir) if run_dir else None,
        "package": package or {},
    }


def _geom_state(geom=None, renders=None, running=False):
    return dossier_mod._geometry_state(
        {}, geom or {}, renders or {}, running)


# ---------------------------------------------------------------------------
# 1. the six-value geometry/visual vocabulary
# ---------------------------------------------------------------------------
class TestGeometryStates:
    def test_state_b_not_applicable(self):
        out = _geom_state({"present": False,
                           "bridge_outcome": "NOT_VISUALIZABLE",
                           "bridge_why": "process invention"})
        assert out["geometry_state"] == "geometry_not_applicable"
        assert out["presentation_cause"] is None
        assert out["geometry_state_detail"] == "process invention"

    def test_state_b_generation_failed(self):
        out = _geom_state({"present": False,
                           "bridge_outcome": "GEOMETRY_FAILED",
                           "bridge_why": "CAD_BUILD_FAILURE: kernel"})
        assert out["geometry_state"] == "geometry_generation_failed"
        assert "CAD_BUILD_FAILURE" in out["geometry_state_detail"]

    def test_state_c_renderer_unavailable(self):
        out = _geom_state({"present": True},
                          {"status": "RENDER_FAILED"})
        assert out["geometry_state"] == "visual_render_failed"
        assert out["presentation_cause"] == "renderer_unavailable"

    def test_state_c_infra_skip(self):
        out = _geom_state({"present": True},
                          {"status": "RENDER_SKIPPED_LOW_MEMORY",
                           "note": "below the memory floor"})
        assert out["geometry_state"] == "visual_render_failed"
        assert out["presentation_cause"] == "infrastructure"
        assert out["geometry_state_detail"] == "below the memory floor"

    def test_geometry_available_never_attempted(self):
        out = _geom_state({"present": True}, {})
        assert out["geometry_state"] == "geometry_available"
        assert out["presentation_cause"] == "not_attempted"

    def test_state_d_gate_not_passed(self):
        out = _geom_state({"present": True},
                          {"status": "OK",
                           "visual_gate": {"verdict": "FAIL"}})
        assert out["geometry_state"] == "visual_render_failed"
        assert out["presentation_cause"] == "gate_not_passed"
        assert "integrity gate returned FAIL" in out["geometry_state_detail"]

    def test_state_d_partial_is_also_gate_not_passed(self):
        out = _geom_state({"present": True},
                          {"status": "OK",
                           "visual_gate": {"verdict": "PARTIAL"}})
        assert out["presentation_cause"] == "gate_not_passed"

    def test_state_e_visual_complete(self):
        for verdict in ("PASS", "COMPLETE_PASS"):
            out = _geom_state({"present": True},
                              {"status": "OK",
                               "visual_gate": {"verdict": verdict}})
            assert out["geometry_state"] == "visual_complete", verdict
            assert out["presentation_cause"] is None

    def test_upstream_not_reached_running(self):
        out = _geom_state({"present": False}, {}, running=True)
        assert out["geometry_state"] == "upstream_not_reached"
        assert "not reached the engineering stage" \
            in out["geometry_state_detail"]

    def test_upstream_not_reached_no_invention(self):
        out = _geom_state({"present": False,
                           "bridge_outcome": "NO_INVENTION"})
        assert out["geometry_state"] == "upstream_not_reached"
        assert "no invention-side artifacts" in out["geometry_state_detail"]

    def test_blocked_run_is_upstream_not_reached(self):
        """Art. LXI: an infrastructure stop classifies as
        upstream_not_reached — never as a geometry failure."""
        out = _geom_state({"present": False}, {})
        assert out["geometry_state"] == "upstream_not_reached"
        assert "failed" not in (out["geometry_state_detail"] or "").lower()


# ---------------------------------------------------------------------------
# 2. the DISCOVERY PIPELINE strip projection
# ---------------------------------------------------------------------------
class TestPipelineStrip:
    def test_blocked_run_shows_the_directives_exact_strip(self):
        """The directive's own example: a transport-blocked run shows
        Problem RECEIVED and everything else NOT REACHED."""
        d = dossier_mod.build_dossier(_session(
            status="RUN_BLOCKED_TRANSPORT"))
        rows = {r["key"]: r for r in d["pipeline"]}
        assert [r["key"] for r in d["pipeline"]] == list(
            dossier_mod.PIPELINE_STAGES)
        assert rows["problem"]["status"] == "RECEIVED"
        for key in ("evidence", "mechanism", "invention", "engineering",
                    "visualization", "package"):
            assert rows[key]["status"] == "NOT_REACHED", key

    def test_not_reached_never_carries_a_count(self):
        """Art. XXV on the strip: a NOT_REACHED row never shows a
        numeric zero — the count exists only when the envelope exists."""
        d = dossier_mod.build_dossier(_session(
            status="RUN_BLOCKED_TRANSPORT"))
        for r in d["pipeline"]:
            if r["status"] == "NOT_REACHED":
                assert not (r.get("detail") or "").strip().startswith("0")

    def test_measured_zero_is_shown_only_when_retrieved(self):
        """A RETRIEVED zero is the honest measured zero (C2.5) — the
        strip may show '0 sources retrieved' ONLY in that case."""
        rows = dossier_mod.pipeline_projection(
            _session(), None, False,
            {"package_state": {"state": "NOT_PRODUCED"}},
            {"retrieval_state": "RETRIEVED", "retrieved_count": 0,
             "used_count": 0},
            {"geometry_state": "upstream_not_reached"})
        ev = next(r for r in rows if r["key"] == "evidence")
        assert ev["status"] == "RECEIVED"
        assert ev.get("detail") == "0 sources retrieved"

    def test_running_run_shows_in_progress_frontier(self, tmp_path):
        """A running run whose run dir exists but whose RETRIEVE
        envelope has not landed: the ledger says PENDING, the strip says
        IN_PROGRESS (one truth — the strip mirrors the ledger)."""
        run = tmp_path / "ts_running"
        run.mkdir()
        (run / "problem.json").write_text("{}")
        d = dossier_mod.build_dossier(_session(status="RUNNING",
                                               run_dir=run))
        rows = {r["key"]: r for r in d["pipeline"]}
        assert rows["problem"]["status"] == "RECEIVED"
        assert rows["evidence"]["status"] == "IN_PROGRESS"
        for key in ("mechanism", "invention", "engineering",
                    "visualization", "package"):
            assert rows[key]["status"] == "NOT_REACHED", key

    def test_running_run_before_problem_build_strip(self):
        """A queued/running session with no run dir yet: the problem was
        RECEIVED (the user submitted it) and nothing else has run — the
        ledger's own NOT_REACHED is mirrored, never upgraded."""
        d = dossier_mod.build_dossier(_session(status="RUNNING"))
        rows = {r["key"]: r for r in d["pipeline"]}
        assert rows["problem"]["status"] == "RECEIVED"
        assert rows["evidence"]["status"] == "NOT_REACHED"

    def test_success_run_all_received(self, tmp_path):
        run = tmp_path / "ts_success"
        run.mkdir()
        (run / "problem.json").write_text("{}")
        (run / "INVENTION_SPECIFICATION.json").write_text("{}")
        (run / "ENGINEERING_SPECIFICATION.json").write_text("{}")
        (run / "envelope_SYNTHESIZE.json").write_text(
            '{"stage_log": [{"stage": "SYNTHESIZE", "status": "OK"}]}')
        (run / "envelope_ATTACK.json").write_text(
            '{"stage_log": [{"stage": "ATTACK", "status": "OK"}]}')
        rows = dossier_mod.pipeline_projection(
            _session(run_dir=run), run, False,
            {"package_state": {"state": "READY"},
             "invention_state": {"state": "EXISTS"}},
            {"retrieval_state": "RETRIEVED", "retrieved_count": 7,
             "used_count": 3},
            {"geometry_state": "visual_complete"})
        by_key = {r["key"]: r for r in rows}
        for key in dossier_mod.PIPELINE_STAGES:
            assert by_key[key]["status"] == "RECEIVED", key

    def test_gate_fail_is_stopped_with_the_typed_detail(self):
        """State D on the strip: arrived, rendered, gate rejected —
        STOPPED with the recorded detail, never infrastructure."""
        rows = dossier_mod.pipeline_projection(
            _session(), None, False,
            {"package_state": {"state": "NOT_PRODUCED"}},
            {"retrieval_state": "RETRIEVED", "retrieved_count": 4},
            {"geometry_state": "visual_render_failed",
             "presentation_cause": "gate_not_passed",
             "geometry_state_detail":
                 "the render completed but the presentation integrity "
                 "gate returned FAIL"})
        viz = next(r for r in rows if r["key"] == "visualization")
        assert viz["status"] == "STOPPED"
        assert "integrity gate returned FAIL" in (viz.get("detail") or "")

    def test_renderer_skip_is_paused_infrastructure(self):
        rows = dossier_mod.pipeline_projection(
            _session(), None, False,
            {"package_state": {"state": "NOT_PRODUCED"}},
            {"retrieval_state": "RETRIEVED", "retrieved_count": 4},
            {"geometry_state": "visual_render_failed",
             "presentation_cause": "infrastructure",
             "geometry_state_detail": "below the memory floor"})
        viz = next(r for r in rows if r["key"] == "visualization")
        assert viz["status"] == "PAUSED_INFRASTRUCTURE"
        assert viz.get("detail") == "below the memory floor"

    def test_engineering_row_receives_on_typed_geometry(self):
        """The engineering row consumes the typed geometry_state — a
        geometry-available run RECEIVED engineering even when the
        artifacts check is inconclusive."""
        rows = dossier_mod.pipeline_projection(
            _session(), None, False,
            {"package_state": {"state": "NOT_PRODUCED"}},
            {"retrieval_state": "RETRIEVED", "retrieved_count": 4},
            {"geometry_state": "geometry_available",
             "presentation_cause": "not_attempted"})
        eng = next(r for r in rows if r["key"] == "engineering")
        assert eng["status"] == "RECEIVED"

    def test_package_blocked_is_typed_not_auto_infra(self):
        """R451-C2.2 §4 SUPERSESSION: BLOCKED is NOT automatically an
        infrastructure pause — the quality-gate reason classifies as
        PACKAGE_INTEGRITY and stops the row (the C2.1 expectation of
        PAUSED_INFRASTRUCTURE here is superseded by the directive)."""
        rows = dossier_mod.pipeline_projection(
            _session(), None, False,
            {"package_state": {"state": "BLOCKED",
                               "blocked_reason": "the quality gate "
                                                 "did not pass"}},
            {"retrieval_state": "RETRIEVED", "retrieved_count": 4},
            {"geometry_state": "visual_complete"})
        pkg = next(r for r in rows if r["key"] == "package")
        assert pkg["status"] == "STOPPED"
        assert pkg["blocked_class"] == "PACKAGE_INTEGRITY"
        assert "quality gate" in (pkg.get("detail") or "")


# ---------------------------------------------------------------------------
# 3. the design tab's honest notes
# ---------------------------------------------------------------------------
class TestDesignTabNotes:
    def test_no_blanket_geometry_unavailable_note(self):
        """The blanket '3D GEOMETRY UNAVAILABLE' reading the directive
        removed is gone from every typed note."""
        d = dossier_mod.build_dossier(_session(
            status="RUN_BLOCKED_TRANSPORT"))
        assert "3D GEOMETRY UNAVAILABLE" not in \
            d["tabs"]["design"]["note"]
        assert d["tabs"]["design"]["geometry_state"] == \
            "upstream_not_reached"

    def test_state_b_note_is_the_directive_sentence(self):
        d = dossier_mod.build_dossier(_session(
            final_status="AUTOMATED_INVENTION_CANDIDATE"))
        # no run dir at all -> upstream_not_reached; the note names the
        # reach state, not a technology absence
        assert "not reached" in d["tabs"]["design"]["note"]


# ---------------------------------------------------------------------------
# 4. source pins — the frontend renders backend truth, verbatim
# ---------------------------------------------------------------------------
class TestSourcePins:
    def test_mapping_consumes_the_typed_state(self):
        src = (WEBAPP / "lib" / "presentationState.ts").read_text()
        assert "geometry_state" in src
        assert "presentation_cause" in src
        assert 'GEOMETRY_STATES.has(gstate)' in src
        assert "NEVER infers" in src or "never infers" in src

    def test_exact_directive_copy_pinned(self):
        src = (WEBAPP / "lib" / "presentationState.ts").read_text()
        assert '"Engineering visualization not available on this ' \
               'invention."' in src
        assert '"Engineering model ready. Presentation renderer ' \
               'unavailable."' in src
        assert '"Model rendered but did not pass the presentation " +\n' \
               '        "integrity gate."' in src

    def test_strip_renders_backend_statuses_verbatim(self):
        src = (WEBAPP / "components" / "DiscoveryPipelineStrip.tsx") \
            .read_text()
        assert "data-pipeline-strip" in src
        assert 'data-pipeline-stage={row.key}' in src
        assert 'data-pipeline-status={row.status}' in src
        # no projection -> no strip (never a guessed ladder)
        assert "return null" in src

    def test_techstage_uses_state_b_hero_and_ribbon_variants(self):
        src = (WEBAPP / "components" / "TechStage.tsx").read_text()
        assert "HeroNoVisualization" in src
        assert 'view.state === "GEOMETRY_UNAVAILABLE" ?' in src
        assert "renderBlockedCopy(view.renderBlockCause)" in src
        assert "DiscoveryPipelineStrip" in src
        assert 'data-hero-no-visualization' in src
        # the old collapsed ribbon copy is gone from the component
        assert "Presentation rendering is\\n              temporarily" \
            not in src

    def test_no_component_hardcodes_the_blanket_note(self):
        for name in ("TechStage.tsx", "InfrastructureBlockedHero.tsx",
                     "DiscoveryPipelineStrip.tsx"):
            src = (WEBAPP / "components" / name).read_text()
            assert "3D GEOMETRY UNAVAILABLE" not in src, name

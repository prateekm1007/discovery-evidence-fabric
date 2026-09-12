"""R430.1 — the Scientific Technology Artifact Workspace tests.

Covers the Technology Investigation event stream (section 7/9/11),
the Technology Dossier projection (sections 3-6/10/14-16), and the
new server routes. Constitutional anchors:
- Art. X: the dossier/events are PROJECTIONS of the canonical run
  state — tests verify no second truth is authored.
- Art. XXV/LXI: infrastructure failure NEVER collapses with scientific
  failure — BLOCKED / FAILED_INFRASTRUCTURE / FAILED_SCIENTIFIC stay
  structurally distinct.
- Art. XXVIII: epistemic classes never promote (PHYSICS event is
  SIMULATED only when a simulation verdict was recorded).
- Art. XXXVIII: PHYSICAL_OBSERVED never appears without a REAL
  reality-loop ledger entry.
- R430.1 s3: the dossier EXISTS before 3D/package (early state has
  honest PENDING tabs, never a fake invention surface).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from toscanini import dossier as dos  # noqa: E402
from toscanini import investigation as inv  # noqa: E402


# ---------------------------------------------------------------------------
# Synthetic canonical run states (same artifacts a real run persists)
# ---------------------------------------------------------------------------
def _mk_run(tmp_path: Path, *, status="COMPLETE",
            final="AUTOMATED_INVENTION_CANDIDATE", evidence=True,
            invention=True, package=True, lineage_killed=False,
            physics_simulated=False, premise_rejected=False):
    rd = tmp_path / "ENGINE_RUNS" / f"run_{status}_{final[:8]}"
    rd.mkdir(parents=True, exist_ok=True)
    sid = "ts_r430_test"

    if evidence:
        env = {
            "stage_log": [{"stage": "RETRIEVE", "status": "OK",
                           "started_at": "2026-09-09T10:00:00Z",
                           "finished_at": "2026-09-09T10:00:02Z"}],
            "evidence": [
                {"id": "src:1", "title": "Polymer fatigue under cyclic "
                                        "pressure",
                 "source": "EuropePMC", "source_uri": "https://x/1",
                 "doi": "10.1/x", "epistemic_state": "VERIFIED_EVIDENCE",
                 "content_hash": "aa", "retrieval_timestamp": "t1"},
                {"id": "src:2", "title": "Retrieved but unused record",
                 "source": "EuropePMC", "source_uri": "https://x/2",
                 "epistemic_state": "UNKNOWN", "content_hash": "bb",
                 "retrieval_timestamp": "t1"},
            ],
        }
        (rd / "envelope_RETRIEVE.json").write_text(json.dumps(env))
    if physics_simulated:
        (rd / "envelope_PHYSICS.json").write_text(json.dumps({
            "stage_log": [{"stage": "PHYSICS", "status": "OK"}],
            "physics": {"lifecycle_verdict": "SURVIVES_BASELINE",
                        "baseline_comparison": {"outcome": "IMPROVED"}}}))
    if premise_rejected:
        (rd / "envelope_PREMISE_GATE.json").write_text(json.dumps({
            "stage_log": [{"stage": "PREMISE_GATE", "status": "OK"}],
            "premise_gate": {"verdict": "REJECTED",
                             "explanation": "thermodynamically incoherent "
                                            "as stated"}}))
    if invention:
        spec = {
            "invention_id": "INV-430",
            "mechanism": {"value": "passive floor lumen maintains "
                                   "drainage"},
            "problem": {"value": {"device": "catheter"}},
            "evidence": {"value": [{"id": "src:1", "title": "Polymer "
                                                          "fatigue",
                                    "content_hash": "aa"}],
                         "evidence_ids": ["src:1"]},
            "uncertainties": {"value": ["fatigue life at 37C"]},
            "killer_experiment": {"name": "occlusion-bench drainage "
                                          "test"},
        }
        (rd / "INVENTION_SPECIFICATION.json").write_text(
            json.dumps(spec))
        (rd / "final_state.json").write_text(json.dumps(
            {"final_status": final}))
    if lineage_killed:
        (rd / "INVENTION_LINEAGE.json").write_text(json.dumps({
            "generations": [
                {"gen": 1, "architecture": {"mechanism":
                                            "magnetic lumen switching"},
                 "challenge": {"killed": True, "kill_stage": "ATTACK",
                               "kill_reason": "field strength infeasible"},
                 "diagnosis": {"cause": "ATTACK_INFEASIBLE",
                               "basis": ["attack envelope"]}},
                {"gen": 2, "architecture": {"mechanism":
                                            "passive floor lumen"},
                 "challenge": {"survived": True},
                 "change_delta": "replaced active switching with "
                                 "passive floor lumen",
                 "reason_for_change": "attack diagnosed infeasibility"}],
            "n_generations": 2, "current_invention": {"gen": 2},
            "stop_reason": "survivor reached"}))
    if package:
        dl = rd / "DOWNLOAD"
        dl.mkdir(exist_ok=True)
        (dl / "PACKAGE_MANIFEST.json").write_text(json.dumps(
            {"artifact": "PACKAGE_MANIFEST", "package_id": "INV-430",
             "run_id": sid, "file_count": 3, "files": [],
             "package_maturity": "EARLY",
             "visualizability_class": "CONCEPTUAL_3D"}))
        (dl / "02_ENGINEERING_DEFINITION.json").write_text(json.dumps(
            {"artifact": "ENGINEERING_DEFINITION", "parameters": [],
             "build_steps": ["step1"]}))
        (dl / "04_DECISIVE_EXPERIMENT.json").write_text(json.dumps(
            {"artifact": "DECISIVE_EXPERIMENT",
             "contract": {"HYPOTHESIS": {"status": "DERIVED"}},
             "contract_completeness": {}}))
        (dl / "UNKNOWN_ROADMAP.json").write_text(json.dumps(
            {"unknowns": [{"statement": "fatigue life at 37C",
                           "priority": "H"}]}))
        (dl / "TECHNOLOGY_TRANSFER_PACKAGE_INV-430.zip").write_bytes(
            b"zip")
        (rd / "PACKAGE_REPORT.json").write_text(json.dumps(
            {"complete": True, "maturity": "EARLY",
             "zip_name": "TECHNOLOGY_TRANSFER_PACKAGE_INV-430.zip",
             "package_kind": "INVENTION_BRIDGE"}))
    return {
        "session_id": sid, "user_text": "keep minimum drainage when a "
                                        "shunt's primary lumen "
                                        "obstructs",
        "status": status, "created_at": "2026-09-09T09:59:00Z",
        "final_status": final if status == "COMPLETE" else None,
        "run_dir": str(rd),
        "package": {"complete": package, "maturity": "EARLY",
                    "zip_name": "TECHNOLOGY_TRANSFER_PACKAGE_INV-430.zip"}
        if package else {},
    }


# ---------------------------------------------------------------------------
# Section 7: structured scientific events
# ---------------------------------------------------------------------------
class TestEventStream:
    def test_status_vocabulary_closed(self):
        for s in inv.EVENT_STATUSES:
            assert s.isupper()
        assert "FAILED_INFRASTRUCTURE" in inv.EVENT_STATUSES
        assert "FAILED_SCIENTIFIC" in inv.EVENT_STATUSES
        assert "BLOCKED" in inv.EVENT_STATUSES

    def test_epistemic_vocabulary_closed(self):
        assert set(inv.EPISTEMIC_CLASSES) >= {
            "RETRIEVED", "INFERRED", "HYPOTHESIZED", "COMPUTED",
            "SIMULATED", "ENGINEERING_DEFINED", "PHYSICALLY_OBSERVED",
            "UNKNOWN"}

    def test_every_event_uses_closed_vocabularies(self, tmp_path):
        s = _mk_run(tmp_path, lineage_killed=True)
        for e in inv.investigation_events(s):
            assert e["status"] in inv.EVENT_STATUSES, e
            assert e["epistemic_class"] in inv.EPISTEMIC_CLASSES, e
            assert e["event_id"].startswith("evt_")
            assert e["basis_ref"], e
            assert e["kind"], e

    def test_event_ids_deterministic(self, tmp_path):
        s = _mk_run(tmp_path)
        a = [e["event_id"] for e in inv.investigation_events(s)]
        b = [e["event_id"] for e in inv.investigation_events(s)]
        assert a == b

    def test_infra_terminal_never_scientific(self, tmp_path):
        for st in ("INTERRUPTED", "ERROR_RUN", "ERROR_TRANSPORT"):
            s = _mk_run(tmp_path, status=st, invention=False,
                        package=False, evidence=False)
            term = [e for e in inv.investigation_events(s)
                    if e["kind"].startswith("investigation.")]
            assert term[-1]["status"] == "FAILED_INFRASTRUCTURE", st
            assert "infrastructure" in term[-1]["summary"].lower()

    def test_resumable_block_is_distinct(self, tmp_path):
        s = _mk_run(tmp_path, status="RUN_BLOCKED_TRANSPORT",
                    invention=False, package=False, evidence=False)
        term = [e for e in inv.investigation_events(s)
                if e["kind"].startswith("investigation.")]
        assert term[-1]["status"] == "BLOCKED"
        assert term[-1].get("resumable") is True

    def test_scientific_rejection_is_failed_scientific(self, tmp_path):
        s = _mk_run(tmp_path, final="MALFORMED_OR_FALSE_PREMISE",
                    premise_rejected=True, invention=False,
                    package=False)
        term = [e for e in inv.investigation_events(s)
                if e["kind"].startswith("investigation.")]
        assert term[-1]["status"] == "FAILED_SCIENTIFIC"

    def test_stage_event_carries_artifact_timestamp(self, tmp_path):
        s = _mk_run(tmp_path)
        ev = [e for e in inv.investigation_events(s)
              if e["kind"] == "stage.retrieve"]
        assert ev and ev[0]["timestamp"] == "2026-09-09T10:00:02Z"

    def test_no_event_without_artifact(self, tmp_path):
        s = _mk_run(tmp_path, evidence=False, invention=False,
                    package=False, status="PENDING")
        kinds = [e["kind"] for e in inv.investigation_events(s)]
        assert "stage.retrieve" not in kinds
        assert "package.ready" not in kinds

    def test_physics_class_not_promoted_without_verdict(self, tmp_path):
        s = _mk_run(tmp_path, physics_simulated=False)
        # no PHYSICS envelope -> no physics event at all
        kinds = [e["kind"] for e in inv.investigation_events(s)]
        assert "stage.physics" not in kinds

    def test_physics_simulated_only_with_recorded_verdict(self, tmp_path):
        s = _mk_run(tmp_path, physics_simulated=True)
        ev = [e for e in inv.investigation_events(s)
              if e["kind"] == "stage.physics"]
        assert ev and ev[0]["epistemic_class"] == "SIMULATED"

    def test_killed_generation_is_failed_scientific(self, tmp_path):
        s = _mk_run(tmp_path, lineage_killed=True)
        ev = [e for e in inv.investigation_events(s)
              if e["kind"] == "candidate.rejected"]
        assert ev and ev[0]["status"] == "FAILED_SCIENTIFIC"
        assert ev[0]["generation"] == 1

    def test_rebuilt_event_present(self, tmp_path):
        s = _mk_run(tmp_path, lineage_killed=True)
        ev = [e for e in inv.investigation_events(s)
              if e["kind"] == "candidate.rebuilt"]
        assert ev and ev[0]["generation"] == 2


# ---------------------------------------------------------------------------
# Section 9: the collapsible gauntlet
# ---------------------------------------------------------------------------
class TestGauntlet:
    def test_marks_and_states(self, tmp_path):
        s = _mk_run(tmp_path, lineage_killed=True)
        g = inv.gauntlet_projection(inv.investigation_events(s))
        marks = {c["stage"]: c for c in g}
        assert marks["EVIDENCE"]["mark"] == "✓"
        assert marks["CHALLENGE"]["mark"] == "✕"
        assert marks["CHALLENGE"]["state"] == "FAILED_SCIENTIFIC"
        assert marks["REBUILD"]["mark"] == "✓"

    def test_pending_groups_visible(self, tmp_path):
        s = _mk_run(tmp_path, status="RUNNING", invention=False,
                    package=False, evidence=False)
        g = inv.gauntlet_projection(inv.investigation_events(s))
        stages = {c["stage"] for c in g}
        assert {"EXPERIMENT", "ENGINEERING", "TRANSFER"} <= stages

    def test_gauntlet_never_16_tabs(self, tmp_path):
        s = _mk_run(tmp_path, lineage_killed=True)
        g = inv.gauntlet_projection(inv.investigation_events(s))
        assert len(g) <= 9


# ---------------------------------------------------------------------------
# Sections 3-6/10/14: the dossier
# ---------------------------------------------------------------------------
class TestDossier:
    def test_dossier_exists_before_3d(self, tmp_path):
        s = _mk_run(tmp_path, status="RUNNING", invention=False,
                    package=False, evidence=False)
        d = dos.build_dossier(s)
        assert d["kind"] == "TECHNOLOGY_DOSSIER"
        assert d["tabs"]["overview"]["availability"] == "AVAILABLE"
        assert d["tabs"]["design"]["availability"] == "PENDING"
        assert d["tabs"]["transfer"]["availability"] == "PENDING"

    def test_all_tabs_carry_availability_and_class(self, tmp_path):
        s = _mk_run(tmp_path)
        d = dos.build_dossier(s)
        for name in dos.DOSSIER_TABS:
            t = d["tabs"][name]
            assert t["availability"] in ("AVAILABLE", "PENDING",
                                         "UNAVAILABLE",
                                         "NOT_ESTABLISHED"), name
            assert t["epistemic_class"] in dos.EPISTEMIC_CLASSES_OK \
                if hasattr(dos, "EPISTEMIC_CLASSES_OK") else \
                t["epistemic_class"] in inv.EPISTEMIC_CLASSES, name

    def test_evidence_ledger_used_vs_retrieved(self, tmp_path):
        s = _mk_run(tmp_path)
        ev = dos.evidence_ledger(s)
        assert ev["retrieved_count"] == 2
        assert ev["used_count"] == 1
        used = [i for i in ev["items"] if i["used_in_design"]]
        unused = [i for i in ev["items"] if not i["used_in_design"]]
        assert used[0]["id"] == "src:1"
        assert unused[0]["id"] == "src:2"
        assert ev["epistemic_class"] == "RETRIEVED"

    def test_design_unavailable_block_honest(self, tmp_path):
        s = _mk_run(tmp_path)
        design = dos.build_dossier(s)["tabs"]["design"]
        assert design["availability"] == "UNAVAILABLE"
        # R451-C2.1: the honest note follows the TYPED geometry state —
        # the blanket "3D GEOMETRY UNAVAILABLE" reading the operator
        # directive removed is gone; the note still states the absence
        # and the recorded reason plainly.
        assert "unavailable" in design["note"].lower() or \
            "not reached" in design["note"].lower()
        assert "3D GEOMETRY UNAVAILABLE" not in design["note"]
        assert design["geometry_state"] == "upstream_not_reached"
        assert design["reason"]

    def test_falsification_dossier_on_killed_generation(self, tmp_path):
        s = _mk_run(tmp_path, lineage_killed=True)
        d = dos.build_dossier(s)
        f = d["falsification"]
        assert f and f["kind"] == "FALSIFICATION_DOSSIER"
        assert f["initial_candidate"] == "magnetic lumen switching"
        assert f["challenge_condition"] == "ATTACK"
        assert f["observed_failure"] == "field strength infeasible"
        assert f["basis"].startswith("INVENTION_LINEAGE")

    def test_validation_incomplete_on_infra(self, tmp_path):
        s = _mk_run(tmp_path, status="INTERRUPTED", invention=False,
                    package=False, evidence=False,
                    )
        s["error"] = "worker died at 2026-09-09"
        d = dos.build_dossier(s)
        f = d["falsification"]
        assert f and f["kind"] == "VALIDATION_INCOMPLETE"
        assert f["scientific_conclusions"] == "NOT ESTABLISHED"

    def test_no_physical_observed_without_real_loop(self, tmp_path):
        s = _mk_run(tmp_path)
        d = json.dumps(dos.build_dossier(s))
        evs = json.dumps(inv.investigation_events(s))
        assert "PHYSICALLY_OBSERVED" not in d
        assert "PHYSICALLY_OBSERVED" not in evs

    def test_transfer_tab_primary_action(self, tmp_path):
        s = _mk_run(tmp_path)
        t = dos.build_dossier(s)["tabs"]["transfer"]
        assert t["availability"] == "AVAILABLE"
        assert t["primary_action"] == "DOWNLOAD TECHNOLOGY PACKAGE"
        assert t["download"].endswith("/package")
        assert t["package_maturity"] == "EARLY"


# ---------------------------------------------------------------------------
# Section 16: package <-> dossier consistency
# ---------------------------------------------------------------------------
class TestConsistency:
    def test_consistent_projection(self, tmp_path):
        s = _mk_run(tmp_path)
        c = dos.dossier_package_consistency(s)
        assert c["consistent"] is True, c["checks"]

    def test_drift_detected(self, tmp_path):
        s = _mk_run(tmp_path)
        # tamper: the package manifest binds to a DIFFERENT run —
        # an author drift the check must catch (never render around)
        rd = Path(s["run_dir"])
        m = json.loads((rd / "DOWNLOAD" /
                        "PACKAGE_MANIFEST.json").read_text())
        m["run_id"] = "ts_OTHER_run"
        (rd / "DOWNLOAD" / "PACKAGE_MANIFEST.json").write_text(
            json.dumps(m))
        c = dos.dossier_package_consistency(s)
        assert c["consistent"] is False
        failed = [x for x in c["checks"] if not x["consistent"]]
        assert any(x["field"] == "package_run_binding" for x in failed)

    def test_no_package_is_honest_not_pass(self, tmp_path):
        s = _mk_run(tmp_path, package=False)
        c = dos.dossier_package_consistency(s)
        assert c["consistent"] is None


# ---------------------------------------------------------------------------
# Routes: GET /api/run/{id}/events + /dossier (owner-scoped)
# ---------------------------------------------------------------------------
class TestServerRoutes:
    def _handler(self):
        from toscanini import server as srv
        return srv.Handler.__new__(srv.Handler)

    def test_routes_present_in_do_get(self):
        import inspect
        from toscanini import server as srv
        src = inspect.getsource(srv.Handler.do_GET)
        assert '"/events"' in src or "parts[3] == \"events\"" in src
        assert '"/dossier"' in src or "parts[3] == \"dossier\"" in src

    def test_sse_emits_science_events(self):
        import inspect
        from toscanini import server as srv
        src = inspect.getsource(srv.Handler._sse)
        assert 'send("science"' in src
        # dedup by event_id: no duplicate streaming on re-derivation
        assert "seen_events" in src

    def test_events_and_dossier_are_projections_only(self):
        """Art. X: the modules expose NO writer into the run dir."""
        import inspect
        from toscanini import server as srv
        for name in ("dossier", "investigation"):
            mod = sys.modules[f"toscanini.{name}"]
            src = inspect.getsource(mod)
            assert ".write_text(" not in src, name
            assert "write_bytes" not in src, name
        _ = srv

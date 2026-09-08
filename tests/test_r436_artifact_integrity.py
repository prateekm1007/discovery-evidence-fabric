"""R436 — PRODUCTION + ARTIFACT INTEGRITY tests.

The tightened round directive (after the fresh production EV screenshot):
do NOT redesign the frontend — prove the product. Constitutional anchors:

- Direction 1: /api/version — the deployment identity endpoint (read-only,
  no secrets; a missing export stays null, never a plausible hash —
  Art. VI / XXV).
- Direction 3: SEMANTIC_IDENTITY below the acceptance threshold or a
  generic fallback geometry => NO HERO MODEL, the honest
  "visualization not established" state. No substitute object on the
  primary surface (blind-spot register BS-006/007/024/025; Art. XXVIII —
  a conceptual model never silently presents as the invention).
- Direction 5: the machine must be able to say "I have not earned a
  credible visualization" (Art. XXV — absence of evidence is not a
  failure finding; UNKNOWN stays UNKNOWN and is never a reason to
  suppress the EARNED engineering model).
- The identity continuity invariant: one canonical invention identity
  across result / dossier / 3D asset / decisive experiment / package —
  exact joins from persisted bytes (Art. II / X / LXII).
- R436 §1: HTTP 402 is credit exhaustion, not an invalid response —
  the diagnostic honesty the production blocked-transport record
  lacked (Art. XV).
- Art. LXX — all new user-facing copy is English.
"""
from __future__ import annotations

import hashlib
import json
import sys
import urllib.error
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import provider_health as ph  # noqa: E402
from toscanini import dossier as dos  # noqa: E402
from toscanini import identity_continuity as ic  # noqa: E402

WEBAPP = REPO / "TOSCANINI_UI" / "webapp"
TECHSTAGE = WEBAPP / "components" / "TechStage.tsx"
SCIENCE_EVENTS = WEBAPP / "components" / "ScienceEvents.tsx"
DOSSIER_SECTIONS = WEBAPP / "components" / "DossierSections.tsx"

HEATPUMP_RUN = (REPO / "ENGINE_RUNS"
                / "toscanini_ui_ui_insufficient_heating_capacity_899843")


# ---------------------------------------------------------------------------
# A. failure taxonomy: HTTP 402 is credit exhaustion (R436 §1)
# ---------------------------------------------------------------------------
class TestCreditExhaustedClassification:
    def test_402_classifies_as_credit_exhausted(self):
        err = urllib.error.HTTPError(
            "url", 402, "Payment Required", {}, None)
        assert ph.classify_failure(err) == "CREDIT_EXHAUSTED"

    def test_402_with_status_arg(self):
        assert ph.classify_failure(
            RuntimeError("x"), http_status=402) == "CREDIT_EXHAUSTED"

    def test_vocabulary_member(self):
        assert "CREDIT_EXHAUSTED" in ph.FAILURE_TYPES

    def test_existing_members_not_reclassified(self):
        """Art. (R415 precedent): extending the vocabulary never
        reclassifies an existing member — 410/429/401/400 unchanged."""
        assert ph.classify_failure(
            urllib.error.HTTPError("u", 410, "Gone", {}, None)) == "GONE"
        assert ph.classify_failure(
            urllib.error.HTTPError("u", 429, "Too Many", {}, None)) \
            == "RATE_LIMITED"
        assert ph.classify_failure(
            urllib.error.HTTPError("u", 401, "Unauthorized", {}, None)) \
            == "AUTH_FAILURE"
        assert ph.classify_failure(
            urllib.error.HTTPError("u", 400, "Bad", {}, None)) \
            == "INVALID_RESPONSE"

    def test_credit_exhausted_does_not_enter_rate_limit_cooldown(self,
                                                                 tmp_path):
        """Waiting cannot restore credits — the cooldown ladder is for
        rate limits only (recorded policy, Art. XXVII)."""
        book = ph.ProviderHealthBook(health_dir=tmp_path / "health")
        book.record_failure("openrouter", "CREDIT_EXHAUSTED",
                            purpose="test", model="m", error="402")
        e = book._state.get("openrouter") or {}
        assert e.get("consecutive_rate_limits") == 0
        assert not book.in_cooldown("openrouter")


# ---------------------------------------------------------------------------
# B. hero eligibility: the suppression invariant (Direction 3)
# ---------------------------------------------------------------------------
class TestHeroEligibility:
    def _geom(self, **over):
        base = {
            "present": True,
            "conceptual": True,
            "fallback_basis": None,
            "scores": {"semantic_identity": {"passed": True,
                                             "score": "PASS"}},
        }
        base.update(over)
        return base

    def test_generic_fallback_is_suppressed(self):
        he = dos._hero_eligibility(self._geom(
            fallback_basis="domain build failed — labeled generic fallback"))
        assert he["eligible"] is False
        assert "substitute" in he["reason"].lower()

    def test_semantic_fail_conceptual_is_suppressed(self):
        he = dos._hero_eligibility(self._geom(
            scores={"semantic_identity": {
                "passed": False, "score": "FAIL",
                "not_visualized": ["condenser", "compressor"]}}))
        assert he["eligible"] is False
        assert he["not_visualized"] == ["condenser", "compressor"]

    def test_earned_engineering_geometry_never_suppressed(self):
        """Direction 5 / Art. XXV: the engineering model's semantic score
        is structurally UNCHECKABLE (no spec) — UNKNOWN is not a failure
        finding; the earned model is never suppressed."""
        he = dos._hero_eligibility(self._geom(
            conceptual=False,
            scores={"semantic_identity": {"passed": False,
                                          "score": "FAIL"}}))
        assert he["eligible"] is True

    def test_semantic_pass_conceptual_shows(self):
        he = dos._hero_eligibility(self._geom())
        assert he["eligible"] is True

    def test_legacy_record_without_scores_shows(self):
        """Absence of the score record is not evidence of failure
        (Art. XXV) — pre-R433 records are not silently suppressed."""
        he = dos._hero_eligibility(self._geom(scores=None))
        assert he["eligible"] is True


def _mk_session(tmp_path: Path, *, geometry: dict,
                status="COMPLETE") -> dict:
    """A minimal canonical run whose BRIDGE_REPORT geometry block carries
    the given fields (the same artifact shapes a real run persists)."""
    rd = tmp_path / "ENGINE_RUNS" / "run_r436"
    rd.mkdir(parents=True, exist_ok=True)
    model = rd / "MODEL"
    model.mkdir(exist_ok=True)
    (model / "model-002.glb").write_bytes(b"glb-bytes")
    spec = {
        "invention_id": "INV-R436",
        "mechanism": {"value": "a real mechanism sentence"},
        "problem": {"value": {"device": "test device"}},
        "evidence": {"value": [], "evidence_ids": []},
    }
    (rd / "INVENTION_SPECIFICATION.json").write_text(json.dumps(spec))
    (rd / "final_state.json").write_text(
        json.dumps({"final_status": "EVOLVED_INVENTION_CANDIDATE"}))
    bridge = {
        "case": "B",
        "outcome": "COMPLETED",
        "conceptual": True,
        "geometry": {
            "present": True,
            "glb": "MODEL/model-002.glb",
            "domain_family": "VEHICLE",
            "generation_id": "gen-2",
            "generation_count": 2,
            **geometry,
        },
    }
    (rd / "BRIDGE_REPORT.json").write_text(json.dumps(bridge))
    return {
        "session_id": "ts_r436_test",
        "user_text": "a real technical problem statement for the test",
        "status": status,
        "created_at": "2026-09-09T09:00:00Z",
        "final_status": "EVOLVED_INVENTION_CANDIDATE",
        "run_dir": str(rd),
    }


class TestDesignTabSuppression:
    def test_design_tab_carries_ineligible_flag(self, tmp_path):
        s = _mk_session(tmp_path, geometry={
            "fallback_basis": "no domain family earned the minimum form "
                              "score — generic architecture diagram",
            "scores": {"semantic_identity": {"passed": False,
                                             "score": "FAIL"}}})
        d = dos.build_dossier(s)
        he = d["tabs"]["design"]["hero_eligibility"]
        assert he["eligible"] is False

    def test_design_tab_eligible_when_semantic_passes(self, tmp_path):
        s = _mk_session(tmp_path, geometry={
            "scores": {"semantic_identity": {"passed": True,
                                             "score": "PASS"}}})
        d = dos.build_dossier(s)
        he = d["tabs"]["design"]["hero_eligibility"]
        assert he["eligible"] is True

    def test_projection_never_hides_the_record(self, tmp_path):
        """The suppression moves the model OFF the stage; the technical
        record keeps every field (the GLB stays in the tab)."""
        s = _mk_session(tmp_path, geometry={
            "fallback_basis": "domain build failed",
            "scores": {"semantic_identity": {
                "passed": False, "score": "FAIL",
                "not_visualized": ["battery"]}}})
        d = dos.build_dossier(s)
        design = d["tabs"]["design"]
        assert design["availability"] == "AVAILABLE"
        assert design["glb"]
        assert design["hero_eligibility"]["eligible"] is False
        assert design["not_visualized"] == ["battery"]

    @pytest.mark.skipif(not HEATPUMP_RUN.exists(),
                        reason="real heat-pump run not present locally")
    def test_real_semantic_fail_run_is_suppressed(self):
        """The REAL ts_387d8467cbb5 run (conceptual FLUID_DEVICE,
        semantic_identity FAIL) must project as hero-ineligible —
        the exact class the production EV screenshot exposed."""
        from toscanini import cio as cio_mod
        session = {
            "session_id": "ts_387d8467cbb5",
            "user_text": "water heater heating capacity insufficient",
            "status": "COMPLETE",
            "created_at": "2026-09-08T20:37:00Z",
            "final_status": "EVOLVED_INVENTION_CANDIDATE",
            "run_dir": str(HEATPUMP_RUN),
        }
        d = dos.build_dossier(session)
        design = d["tabs"]["design"]
        assert design["hero_eligibility"]["eligible"] is False
        assert design["scores"]["semantic_identity"]["passed"] is False


# ---------------------------------------------------------------------------
# C. the stage source contract (one viewer, suppression, honest language)
# ---------------------------------------------------------------------------
class TestStageSourceContract:
    def test_hero_resolution_is_eligibility_gated(self):
        src = TECHSTAGE.read_text()
        assert "hero_eligibility" in src
        assert "heroEligible" in src
        # the hero GLB only when eligible:
        assert "heroEligible && design && design.availability" in src
        # history swap cannot bypass suppression:
        assert "heroEligible && Boolean(activeRow?.glb)" in src

    def test_unearned_hero_state_exists(self):
        src = TECHSTAGE.read_text()
        assert "HeroNotFaithful" in src
        assert "data-hero-unearned" in src
        assert "Not established yet" in src
        assert "No " in src and "substitute model is shown" in src

    def test_one_viewer_invariant_preserved(self):
        """R433/R435 contract intact: exactly one ModelViewer render in
        TechStage (the suppression adds a state, never a viewer)."""
        src = TECHSTAGE.read_text()
        assert src.count("<ModelViewer") == 1

    def test_compare_generations_hidden_when_suppressed(self):
        src = TECHSTAGE.read_text()
        assert "genCount > 1 && heroEligible" in src

    def test_nothing_is_lost_replaced_with_precise_persistence(self):
        """Audit §5A: absolute continuity claims are forbidden; the
        honest phrasing is persisted-on-server, you can return."""
        for f in (TECHSTAGE, SCIENCE_EVENTS):
            src = f.read_text()
            assert "nothing is lost" not in src
            assert "persisted on the server" in src

    def test_infrastructure_pause_is_not_active_work(self):
        """Audit §5B: FAILED_INFRASTRUCTURE renders its own paused
        state, never as 'Currently: ...' active work."""
        src = TECHSTAGE.read_text()
        assert 'e.status === "ACTIVE"' in src
        assert 'e.status === "FAILED_INFRASTRUCTURE"' in src
        # the two are separate lookups:
        active_block = src[src.index("const activeLabel"):src.index(
            "const pausedLabel")]
        assert "FAILED_INFRASTRUCTURE" not in active_block
        assert "Paused — infrastructure" in SCIENCE_EVENTS.read_text()

    def test_deep_layer_keeps_the_record_and_explains(self):
        src = DOSSIER_SECTIONS.read_text()
        assert "hero_eligibility" in src
        assert "The model record" in src
        assert "did not earn the technology stage" in src

    def test_english_only_new_copy(self):
        for f in (TECHSTAGE, SCIENCE_EVENTS, DOSSIER_SECTIONS):
            for line in f.read_text().splitlines():
                for ch in line:
                    if "\u4e00" <= ch <= "\u9fff":
                        raise AssertionError(
                            f"non-English authorship script in {f.name}")


# ---------------------------------------------------------------------------
# D. /api/version — the production identity endpoint (Direction 1)
# ---------------------------------------------------------------------------
class TestVersionEndpoint:
    def _server(self):
        return pytest.importorskip("toscanini.server")

    def test_payload_shape_and_honesty(self):
        srv = self._server()
        payload = srv._version_payload()
        assert set(payload) == {
            "engine_commit", "engine_commit_source", "web_build_hash",
            "web_build_file_count", "web_build_source",
            "constitution_version"}
        # the constitution version is parsed from the ratified file
        assert payload["constitution_version"] == "2.2.0"
        # engine commit resolves (local checkout: git source)
        assert payload["engine_commit_source"] in ("git", "build_artifact")
        assert len(payload["engine_commit"] or "") in (0, 40)
        # the built export hashes deterministically
        assert payload["web_build_file_count"] > 0
        assert payload["web_build_hash"]
        again = srv._version_payload()
        assert again["web_build_hash"] == payload["web_build_hash"]

    def test_absent_export_stays_null_never_fabricated(self, tmp_path,
                                                       monkeypatch):
        """Art. VI: identity is never manufactured — a missing export
        reports null, and the source says exactly that."""
        srv = self._server()
        monkeypatch.setattr(srv, "WEBAPP_EXPORT", tmp_path / "nope")
        payload = srv._version_payload()
        assert payload["web_build_hash"] is None
        assert payload["web_build_file_count"] == 0
        assert payload["web_build_source"] == "export not built"

    def test_hash_is_a_real_content_hash(self, tmp_path, monkeypatch):
        srv = self._server()
        d = tmp_path / "export"
        d.mkdir()
        (d / "index.html").write_text("hello")
        (d / "app.js").write_text("world")
        monkeypatch.setattr(srv, "WEBAPP_EXPORT", d)
        h, n = srv._web_build_hash()
        assert n == 2
        # changing content changes the hash (it is a content hash)
        (d / "app.js").write_text("changed")
        h2, _ = srv._web_build_hash()
        assert h2 != h


# ---------------------------------------------------------------------------
# E. identity continuity — the canonical invention identity join (§5)
# ---------------------------------------------------------------------------
def _mk_cont_run(tmp_path: Path, *, break_join=None) -> Path:
    """A synthetic but structurally faithful run dir carrying the five
    identity surfaces a real run persists."""
    rd = tmp_path / "ENGINE_RUNS" / "run_cont"
    model = rd / "MODEL"
    model.mkdir(parents=True)
    glb = model / "model-002.glb"
    glb.write_bytes(b"glb-bytes")
    glb_sha = hashlib.sha256(b"glb-bytes").hexdigest()

    problem_id = "ui_test_problem_123"
    inv_id = f"inv:{problem_id}:abcdef123456"
    (rd / "final_state.json").write_text(json.dumps({
        "problem_id": problem_id,
        "run_id": "engrun:x",
        "final_status": "EVOLVED_INVENTION_CANDIDATE"}))
    hyps = [{"name": "H_effect_holds",
             "description": "expected effect holds: the effect"}]
    (rd / "INVENTION_SPECIFICATION.json").write_text(json.dumps({
        "invention_id": {"value": inv_id},
        "mechanism": {"value": {"expected_effect": "the effect"}},
        "killer_experiment": {"value": {"hypotheses": hyps}}}))
    if break_join == "experiment":
        hyps_b = [{"name": "H_other",
                   "description": "a different experiment entirely"}]
        (rd / "DECISIVE_EXPERIMENT.json").write_text(json.dumps({
            "selected": {"hypotheses": hyps_b}}))
    else:
        (rd / "DECISIVE_EXPERIMENT.json").write_text(json.dumps({
            "selected": {"hypotheses": hyps}}))

    ai = {
        "technology_id": problem_id,
        "run_id": "ts_cont_test",
        "generation_id": "gen-2",
        "geometry_hash": glb_sha,
        "glb_disk_sha256": glb_sha,
        "glb_path": str(glb),
    }
    if break_join == "artifact":
        ai["technology_id"] = "ui_DIFFERENT_problem_999"
    (model / "ARTIFACT_IDENTITY.json").write_text(json.dumps(ai))

    pkg = rd / "DOWNLOAD" / "160_test_pkg"
    pkg.mkdir(parents=True)
    body = b"package file body"
    body_sha = hashlib.sha256(body).hexdigest()
    (pkg / "00_README.txt").write_bytes(body)
    (pkg / "PACKAGE_MANIFEST.json").write_text(json.dumps({
        "package_id": inv_id if break_join != "package" else
        "inv:ui_OTHER:000000000000",
        "files": [{"file": "00_README.txt", "sha256": body_sha,
                   "bytes": len(body)}]}))
    (pkg.parent / "160_test_pkg.zip").write_bytes(b"zip")

    (rd / "BRIDGE_REPORT.json").write_text(json.dumps({
        "outcome": "COMPLETED",
        "geometry": {"present": True,
                     "artifact_identity": dict(ai)},
        "package_out": {
            "zip_name": "TECHNOLOGY_TRANSFER_PACKAGE_x.zip",
            "zip_sha256": "deadbeef" * 8,
            "package_maturity": "EARLY_TECHNICAL_EVALATION"}}))
    return rd


class TestIdentityContinuity:
    def test_all_joins_pass_on_faithful_run(self, tmp_path):
        r = ic.check_run(_mk_cont_run(tmp_path), "ts_cont_test")
        assert r["passed"] is True
        by = {j["join"]: j["passed"] for j in r["joins"]}
        assert by == {
            "J1_problem_identity": True,
            "J2_geometry_hash_matches_file": True,
            "J3_run_identity": True,
            "J4_decisive_experiment_binding": True,
            "J5_package_identity": True}

    def test_broken_artifact_identity_fails_j1(self, tmp_path):
        r = ic.check_run(_mk_cont_run(tmp_path, break_join="artifact"),
                         "ts_cont_test")
        assert r["passed"] is False
        j1 = next(j for j in r["joins"] if j["join"] == "J1_problem_identity")
        assert j1["passed"] is False

    def test_broken_experiment_binding_fails_j4(self, tmp_path):
        r = ic.check_run(_mk_cont_run(tmp_path, break_join="experiment"),
                         "ts_cont_test")
        assert r["passed"] is False
        j4 = next(j for j in r["joins"] if j["join"] == "J4_decisive_experiment_binding")
        assert j4["passed"] is False

    def test_broken_package_identity_fails_j5(self, tmp_path):
        r = ic.check_run(_mk_cont_run(tmp_path, break_join="package"),
                         "ts_cont_test")
        assert r["passed"] is False
        j5 = next(j for j in r["joins"] if j["join"] == "J5_package_identity")
        assert j5["passed"] is False

    def test_missing_glb_fails_j2_not_fabricates(self, tmp_path):
        rd = _mk_cont_run(tmp_path)
        (rd / "MODEL" / "model-002.glb").unlink()
        r = ic.check_run(rd, "ts_cont_test")
        j2 = next(j for j in r["joins"] if j["join"] == "J2_geometry_hash_matches_file")
        assert j2["passed"] is False

    def test_bridge_package_observation_recorded(self, tmp_path):
        """The superseded bridge package generation is disclosed as an
        observation — never silently dropped (Art. LXIV)."""
        r = ic.check_run(_mk_cont_run(tmp_path), "ts_cont_test")
        obs = [o for o in r.get("observations", [])
               if o["observation"] == "bridge_package_generation_superseded"]
        assert obs and obs[0]["bridge_zip_on_disk"] is False

    @pytest.mark.skipif(not HEATPUMP_RUN.exists(),
                        reason="real heat-pump run not present locally")
    def test_real_run_identity_continuity(self):
        """REAL integration evidence: the completed ts_387d8467cbb5
        heat-pump run (real LLM, real bridge, real package) carries one
        canonical invention identity across all five surfaces."""
        r = ic.check_run(HEATPUMP_RUN, "ts_387d8467cbb5")
        assert r["passed"] is True, json.dumps(
            [j for j in r["joins"] if not j["passed"]], indent=1)

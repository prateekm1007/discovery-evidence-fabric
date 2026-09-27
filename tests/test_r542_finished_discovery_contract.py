"""tests/test_r542_finished_discovery_contract.py — R542 completion contract.

The operator correction this suite pins: a finished discovery is NOT
"two admissible survivors". It is:

    VALID_QUERY + EVIDENCE_BOUND + AT_LEAST_ONE_ADMISSIBLE_SURVIVOR
    + COMPLETE_DISCOVERY_RECORD (six-part conversation shape)
    + COMPLETE_CANDIDATE_BOUND_TECHNOLOGY_PACKAGE
    = FINISHED_DISCOVERY

so ONE survivor after competing candidates were investigated and some
killed IS a finished discovery (the two-survivor shape stays a ranking
fixture, never the product goal). The verifier is the backend's
authoritative product-state record (COMPLETION_CONTRACT.json at the run
tail); the session/UI surface READS it.

Contract pinned here:

  1.  single survivor after competing kills -> finished discovery
  2.  competing vs surviving recorded distinctly (kills included)
  3.  two survivors + two packages -> still finished (ranking shape)
  4.  missing engineering model class -> not finished, named missing
  5.  conceptual model is LABELED, never presented as earned CAD
  6.  decisive experiment without a stated kill outcome -> not finished
  7.  evidence records without source identity -> not evidence-bound
  8.  missing mechanism source span -> not evidence-bound
  9.  UNRESOLVED adversarial disposition -> never a finished survivor
  10. package deletion after completion -> fails closed (re-measured)
  11. typed invalid-query terminal preserved (never converted)
  12. MECHANISM_STARVED typed terminal, no manufactured survivor
  13. a missing package names the EXISTING recovery path
  14. the bounded package retry runs EXACTLY once (never a loop)
  15. a recovered package re-verifies and the run becomes finished
  16. durable contract reload preserves every answer (fresh process)
  17. session_detail serves the durable contract as the states
  18. completion_states exposes missing components to the UI
  19. the surface reads the contract authority (no UI re-derivation)
  20. EXCLUDED (gate-resolved) rows never block finished; only
      MISSING/UNRESOLVED does — and excluded rows are exposed,
      never admissible, never a survivor (zero-kill scenario)
  21. the mandatory end-to-end ordinary query: the REAL engine path
      runs hermetically (cheap screen -> spec -> physics -> attack ->
      quality -> selection), the candidate-bound packages compile, the
      backend contract persists FINISHED_DISCOVERY, and every answer is
      re-derived from disk — never trusted from the in-process claim

All tests are hermetic: engine modules only, no LLM, no network.
"""
from __future__ import annotations

import hashlib
import json
import sys
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# ---- the toscanini import shim (upper-case dir -> lower-case module) ----
if "toscanini" not in sys.modules:
    try:
        import TOSCANINI as _T  # noqa: N813 — exact on-disk name
        sys.modules["toscanini"] = _T
    except Exception:  # noqa: BLE001
        pass
    if "toscanini" not in sys.modules:
        import importlib.util
        _spec = importlib.util.spec_from_file_location(
            "toscanini", str(REPO_ROOT / "TOSCANINI" / "__init__.py"),
            submodule_search_locations=[str(REPO_ROOT / "TOSCANINI")])
        if _spec and _spec.loader:
            _mod = importlib.util.module_from_spec(_spec)
            sys.modules["toscanini"] = _mod
            _spec.loader.exec_module(_mod)
    if "fcntl" not in sys.modules:
        _fake = types.ModuleType("fcntl")
        _fake.LOCK_SH = 1
        _fake.LOCK_EX = 2
        _fake.LOCK_UN = 8
        _fake.flock = lambda *a, **k: None
        sys.modules["fcntl"] = _fake

from discovery_fabric.engine import completion_contract as cc  # noqa: E402
from discovery_fabric.engine import ranked_result_set as rrs  # noqa: E402


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _write(run_dir: Path, name: str, obj) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / name).write_text(
        json.dumps(obj, indent=1, ensure_ascii=False, default=str),
        encoding="utf-8")


def _zip_bytes(payload: bytes) -> bytes:
    # a minimal ZIP-shaped payload; the contract proves distinctness and
    # recorded-vs-on-disk hash equality, not ZIP internal structure
    return b"PK\x03\x04" + payload


def _row(cid: str, key: str, killed: bool, verdict_rank: int) -> dict:
    return {
        "candidate_id": cid, "key": key, "killed": killed,
        "quality_verdict": "FAIL" if killed else "PASS",
        "span_underived": False,
        "physics_lifecycle": ("DOES_NOT_BEAT_BASELINE" if killed
                              else "BEATS_BASELINE"),
        "attack_overall": "KILLED" if killed else "PASS",
        "quality_deficient_count": 3 if killed else 0,
        "uncertain_count": 0, "_verdict_rank": verdict_rank,
        "_physics_rank": 2 if killed else 0,
        "origin": ("EXPLORATION_GRID" if key != "primary"
                   else "DISCOVERY_LOOP_SURVIVOR"),
        "ranked_admissible": not killed,
        "disposition": "KILLED" if killed else "SURVIVED",
    }


def _selection_single() -> dict:
    """ONE survivor after THREE competing candidates were investigated
    (two killed by the adversarial challenge) — the ordinary-query shape
    that must count as a finished discovery."""
    return {
        "selected": "cand_a",
        "ranked": [_row("cand_a", "primary", killed=False, verdict_rank=0),
                   _row("cand_b", "grid-1", killed=True, verdict_rank=1),
                   _row("cand_c", "grid-2", killed=True, verdict_rank=2)],
    }


def _selection_two() -> dict:
    """Two admissible survivors + one killed (the R541 ranking fixture)."""
    sel = _selection_single()
    sel["ranked"][1] = dict(_row("cand_b", "grid-1", killed=False,
                                 verdict_rank=1),
                            quality_verdict="CONDITIONAL",
                            physics_lifecycle="INCONCLUSIVE",
                            quality_deficient_count=1, uncertain_count=1)
    return sel


def _inv_spec(span: bool = True, source: bool = True,
              custody: bool = True, uri: bool = True) -> dict:
    rec: dict = {"id": "ev1", "title": "fixture study",
                 "doi": "10.0000/fixture.1"}
    if uri:
        rec["source_uri"] = "https://fixture.invalid/1"
    if source:
        rec["source"] = "EuropePMC"
    if custody:
        rec["content_hash"] = "ab" * 32
        rec["frozen"] = True
    mech = {"mechanism": "porous microstructure resists tissue ingrowth",
            "intervention": "porous titanium tip at the failure site",
            "expected_effect": "sustained flow, at least 30% above "
                               "baseline at 30 days",
            "falsification_test": "bench loop; measure flow decay over "
                                  "30 days against baseline"}
    if span:
        mech["mechanism_source_span"] = (
            "the porous microstructure resists fluid-path tissue "
            "ingrowth under the stated constraint")
    return {"invention_id": "inv:a",
            "mechanism": {"value": mech},
            "evidence": {"value": [rec]}}


def _eng_spec(kind: str = "geometry") -> dict:
    core = {"critical_parameters": [
        {"parameter": "lumen patency", "value": "maintained"}]}
    if kind == "geometry":
        return {"engineering_core": core,
                "geometry": {"class": "ENGINEERING_3D"}}
    if kind == "conceptual":
        return {"engineering_core": core,
                "visualizability_class": "CONCEPTUAL_SYSTEM_MODEL"}
    # no model class anywhere: definition present, model NOT established
    return {"engineering_core": core}


def _dec_spec(answered: bool = True) -> dict:
    fc: dict = {}
    if answered:
        fc["FALSIFICATION_THRESHOLD"] = (
            "the bench loop fails to show at least 30% above baseline "
            "at 30 days — the mechanism is killed by its own test's "
            "negative outcome")
    else:
        fc["FALSIFICATION_THRESHOLD_BLOCKER"] = (
            "the kill outcome cannot be stated numerically from records")
    return {"selected": {"experiment": "bench flow loop",
                         "hypotheses": [
                             {"name": "H_effect_holds",
                              "description": "flow improves vs baseline"},
                             {"name": "H_effect_fails",
                              "description": "flow does not improve"}],
                         "decision_rule": "kill when the threshold fails"},
            "falsification_contract": fc,
            "execution_status": "SPECIFIED"}


def _packages(run_dir: Path, zips: dict, in_download: bool = False
              ) -> dict:
    """Write the engine's candidate-bound package record + the on-disk
    ZIPs (root or DOWNLOAD/ tree, both are legal locations the binding
    resolves)."""
    pkgs: dict = {}
    by_cid: dict = {}
    for cid, (zname, zbytes) in zips.items():
        key = "primary" if cid == "cand_a" else f"grid-{cid[-1]}"
        if in_download:
            d = run_dir / "DOWNLOAD"
            d.mkdir(parents=True, exist_ok=True)
            (d / zname).write_bytes(zbytes)
        else:
            (run_dir / zname).write_bytes(zbytes)
        rec = {"complete": True, "kind": "TECHNOLOGY_PACKAGE",
               "candidate_id": cid, "ranked_candidate_key": key,
               "zip_name": zname, "zip_sha256": _sha(zbytes),
               "package_id": f"pkg_{cid}"}
        pkgs[key] = rec
        by_cid[cid] = rec
    out = {"schema": "RANKED_PACKAGE_RECORDS/1.0.0", "packages": pkgs,
           "by_candidate_id": by_cid}
    _write(run_dir, "RANKED_PACKAGE_RECORDS.json", out)
    return out


def _run_dir(tmp_path: Path, two_survivors: bool = False,
             with_pkg: bool = True, eng: str = "geometry",
             experiment_answered: bool = True, span: bool = True,
             source: bool = True, custody: bool = True,
             uri: bool = True,
             final_status: str = "AUTOMATED_INVENTION_CANDIDATE",
             selection: dict | None = None) -> Path:
    run_dir = Path(tmp_path) / "ENGINE_RUNS" / "ts_r542"
    sel = selection if selection is not None else (
        _selection_two() if two_survivors else _selection_single())
    _write(run_dir, "SURVIVOR_SELECTION.json", sel)
    _write(run_dir, "final_state.json",
           {"run_id": "ts_r542", "final_status": final_status})
    _write(run_dir, "run_manifest.json",
           {"run_id": "ts_r542", "failed_stages": {}})
    _write(run_dir, "INVENTION_SPECIFICATION.json",
           _inv_spec(span=span, source=source, custody=custody, uri=uri))
    _write(run_dir, "ENGINEERING_SPECIFICATION.json", _eng_spec(eng))
    _write(run_dir, "DECISIVE_EXPERIMENT.json",
           _dec_spec(experiment_answered))
    if two_survivors:
        _write(run_dir, "INVENTION_SPECIFICATION_grid-1.json",
               _inv_spec(span=span, source=source, custody=custody,
                         uri=uri))
        _write(run_dir, "ENGINEERING_SPECIFICATION_grid-1.json",
               _eng_spec(eng))
        _write(run_dir, "DECISIVE_EXPERIMENT_grid-1.json",
               _dec_spec(experiment_answered))
    if with_pkg:
        zips = {"cand_a": ("TECHNOLOGY_TRANSFER_PACKAGE_primary.zip",
                           _zip_bytes(b"CAND_A_UNIQUE_PAYLOAD"))}
        if two_survivors:
            zips["cand_b"] = ("TECHNOLOGY_TRANSFER_PACKAGE_grid-1.zip",
                              _zip_bytes(b"CAND_B_UNIQUE_PAYLOAD"))
        _packages(run_dir, zips)
    return run_dir


def _verify(run_dir: Path) -> dict:
    return cc.verify_completion_contract(run_dir)


# ---------------------------------------------------------------------------
# 1-3: the product invariant — ONE survivor counts; competing != surviving
# ---------------------------------------------------------------------------
def test_01_single_survivor_after_competing_kills_is_finished(tmp_path):
    run_dir = _run_dir(tmp_path)
    rec = _verify(run_dir)
    assert rec["finished_discovery"] is True, (
        "one survivor after competing candidates were killed must be a "
        f"finished discovery; missing={rec['missing_components']}")
    assert rec["missing_components"] == []
    assert rec["typed_terminal_state"] == "FINISHED_DISCOVERY"
    for name in cc.COMPONENTS:
        assert rec["components"][name]["complete"] is True, name
    assert all(rec["preconditions"].values()), rec["preconditions"]


def test_02_competing_vs_surviving_recorded_distinctly(tmp_path):
    run_dir = _run_dir(tmp_path)
    rec = _verify(run_dir)
    cvs = rec["competing_vs_surviving"]
    assert cvs["competing_candidates_investigated"] == [
        "cand_a", "cand_b", "cand_c"]
    assert cvs["killed_by_challenge"] == ["cand_b", "cand_c"]
    assert cvs["surviving_candidates"] == ["cand_a"]
    mech = rec["components"][cc.COMP_MECHANISMS]
    assert mech["n_competing_investigated"] == 3
    assert mech["n_killed"] == 2
    assert mech["n_surviving"] == 1
    assert mech["complete"] is True


def test_03_two_survivors_two_packages_still_finished(tmp_path):
    run_dir = _run_dir(tmp_path, two_survivors=True)
    rec = _verify(run_dir)
    assert rec["finished_discovery"] is True, rec["missing_components"]
    pkg = rec["components"][cc.COMP_PACKAGE]
    assert pkg["n_admissible_survivors"] == 2
    assert pkg["n_complete_candidate_bound_packages"] == 2
    zips = {h["candidate_id"]: h["zip_sha256"] for h in
            pkg["hash_verification"]}
    assert zips["cand_a"] != zips["cand_b"]


# ---------------------------------------------------------------------------
# 4-9: every missing component is named, never papered over
# ---------------------------------------------------------------------------
def test_04_missing_engineering_model_blocks_finished(tmp_path):
    run_dir = _run_dir(tmp_path, eng="none")
    rec = _verify(run_dir)
    assert rec["finished_discovery"] is False
    assert cc.COMP_ENGINEERING in rec["missing_components"]
    eng = rec["components"][cc.COMP_ENGINEERING]
    assert eng["complete"] is False
    assert eng["per_survivor"][0]["model_class"] is None
    assert rec["preconditions"][cc.PRE_RECORD] is False
    assert rec["typed_terminal_state"] == "INCOMPLETE_DISCOVERY"


def test_05_conceptual_model_is_labeled_never_claimed_as_cad(tmp_path):
    run_dir = _run_dir(tmp_path, eng="conceptual")
    rec = _verify(run_dir)
    assert rec["finished_discovery"] is True, rec["missing_components"]
    per = rec["components"][cc.COMP_ENGINEERING]["per_survivor"][0]
    assert per["model_class"] == "CONCEPTUAL_SYSTEM_MODEL"
    assert per["earned_engineering_geometry"] is False
    assert "conceptual" in per["labeling"]
    assert "CAD" in per["labeling"]


def test_06_missing_kill_outcome_blocks_finished(tmp_path):
    run_dir = _run_dir(tmp_path, experiment_answered=False)
    rec = _verify(run_dir)
    assert rec["finished_discovery"] is False
    assert cc.COMP_EXPERIMENT in rec["missing_components"]
    per = rec["components"][cc.COMP_EXPERIMENT]["per_survivor"][0]
    assert per["decision_rule_state"] == "FALSIFICATION_THRESHOLD_BLOCKER"
    assert per["decisive"] is False


def test_07_evidence_without_source_identity_not_bound(tmp_path):
    # no source name AND no source URI — nothing identifies the source
    run_dir = _run_dir(tmp_path, source=False, uri=False)
    rec = _verify(run_dir)
    assert rec["finished_discovery"] is False
    assert rec["preconditions"][cc.PRE_EVIDENCE_BOUND] is False
    per = rec["components"][cc.COMP_EVIDENCE]["per_survivor"][0]
    assert per["records_missing_source_identity"] == ["ev1"]
    assert per["evidence_bound"] is False
    # the production record shape (source_uri retained, display name
    # dropped by the spec projection) still carries source identity
    run_dir2 = _run_dir(Path(tmp_path) / "prod_shape", source=False,
                        uri=True)
    rec2 = _verify(run_dir2)
    assert rec2["preconditions"][cc.PRE_EVIDENCE_BOUND] is True
    assert rec2["finished_discovery"] is True


def test_08_missing_mechanism_source_span_not_bound(tmp_path):
    run_dir = _run_dir(tmp_path, span=False)
    rec = _verify(run_dir)
    assert rec["finished_discovery"] is False
    assert rec["preconditions"][cc.PRE_EVIDENCE_BOUND] is False
    per = rec["components"][cc.COMP_EVIDENCE]["per_survivor"][0]
    assert per["mechanism_source_span_chars"] == 0


def test_09_unresolved_disposition_never_finished(tmp_path):
    run_dir = _run_dir(tmp_path)
    sel = json.loads((run_dir / "SURVIVOR_SELECTION.json").read_text())
    sel["ranked"][1]["disposition"] = "UNRESOLVED"
    sel["ranked"][1]["killed"] = False
    _write(run_dir, "SURVIVOR_SELECTION.json", sel)
    rec = _verify(run_dir)
    assert rec["finished_discovery"] is False
    assert cc.COMP_ADVERSARIAL in rec["missing_components"]
    adv = rec["components"][cc.COMP_ADVERSARIAL]
    assert adv["unresolved_rows"] == ["cand_b"]
    # the UNRESOLVED row never becomes an admissible survivor
    surv = rec["components"][cc.COMP_MECHANISMS]["n_surviving"]
    assert surv == 1
    for row in adv["per_survivor"]:
        if row["candidate_id"] == "cand_b":
            assert row["resolved"] is False


def test_10_package_deletion_after_completion_fails_closed(tmp_path):
    run_dir = _run_dir(tmp_path)
    assert _verify(run_dir)["finished_discovery"] is True
    (run_dir / "TECHNOLOGY_TRANSFER_PACKAGE_primary.zip").unlink()
    rec = _verify(run_dir)
    assert rec["finished_discovery"] is False
    assert cc.COMP_PACKAGE in rec["missing_components"]
    assert rec["components"][cc.COMP_PACKAGE]["violations"], (
        "a deleted package must be a typed violation, not a silent pass")


# ---------------------------------------------------------------------------
# 11-12: typed constitutional blockers are never converted
# ---------------------------------------------------------------------------
def test_11_typed_invalid_query_preserved(tmp_path):
    run_dir = _run_dir(
        tmp_path, final_status="MALFORMED_OR_FALSE_PREMISE")
    rec = _verify(run_dir)
    assert rec["finished_discovery"] is False
    assert rec["valid_query"]["valid"] is False
    assert rec["typed_terminal_state"] == "MALFORMED_OR_FALSE_PREMISE"
    assert rec["preconditions"][cc.PRE_VALID_QUERY] is False
    # no recovery entry may claim the blocker was recovered
    for entry in rec["recovery"]:
        assert entry["component"] != "valid_query"


def test_12_mechanism_starved_typed_terminal_no_fake_survivor(tmp_path):
    run_dir = _run_dir(tmp_path, final_status="MECHANISM_STARVED",
                       selection={"selected": None, "ranked": []},
                       with_pkg=False)
    rec = _verify(run_dir)
    assert rec["finished_discovery"] is False
    assert rec["preconditions"][cc.PRE_SURVIVOR] is False
    assert rec["typed_terminal_state"] == "MECHANISM_STARVED"
    assert rec["diagnostic_only"] is True
    # nothing is presented as a technology package
    assert rec["components"][cc.COMP_PACKAGE][
        "n_admissible_survivors"] == 0


# ---------------------------------------------------------------------------
# 13-15: bounded automatic recovery — the existing package-compiler path
# ---------------------------------------------------------------------------
def test_13_missing_package_names_existing_recovery_path(tmp_path):
    run_dir = _run_dir(tmp_path, with_pkg=False)
    rec = _verify(run_dir)
    assert rec["finished_discovery"] is False
    assert cc.COMP_PACKAGE in rec["missing_components"]
    entry = next(e for e in rec["recovery"]
                 if e["component"] == cc.COMP_PACKAGE)
    assert entry["recoverable"] is True
    assert "compile" in entry["recovery_path"]
    assert entry["recovery_class"] == "PACKAGE"


def test_14_bounded_package_retry_runs_exactly_once(tmp_path):
    run_dir = _run_dir(tmp_path, with_pkg=False)
    calls = {"n": 0}

    def _retry():
        calls["n"] += 1
        return {}   # re-compile produces nothing (still incomplete)

    rec = cc.persist_completion_contract(run_dir, package_retry=_retry)
    assert calls["n"] == 1, "the recovery retry must run at most once"
    assert rec["finished_discovery"] is False
    assert len(rec["recovery_attempts"]) == 1
    attempt = rec["recovery_attempts"][0]
    assert attempt["component"] == cc.COMP_PACKAGE
    assert attempt["action"] == "PACKAGE_COMPILER_RETRY"
    entry = next(e for e in rec["recovery"]
                 if e["component"] == cc.COMP_PACKAGE)
    assert entry["attempted"] is True
    assert entry["exhausted"] is True


def test_15_recovered_package_re_verifies_and_finishes(tmp_path):
    run_dir = _run_dir(tmp_path, with_pkg=False)

    def _retry():
        # the engine's own path: the canonical package compile succeeds
        # on the second attempt and the ranked record is re-persisted
        _packages(run_dir, {"cand_a": (
            "TECHNOLOGY_TRANSFER_PACKAGE_primary.zip",
            _zip_bytes(b"CAND_A_UNIQUE_PAYLOAD"))})
        rrs.persist_ranked_result_set(run_dir)
        return {}

    rec = cc.persist_completion_contract(run_dir, package_retry=_retry)
    assert rec["finished_discovery"] is True, rec["missing_components"]
    assert len(rec["recovery_attempts"]) == 1
    assert rec["components"][cc.COMP_PACKAGE]["complete"] is True
    # a second persist must NOT re-run the retry (nothing is missing)
    calls = {"n": 0}
    rec2 = cc.persist_completion_contract(
        run_dir, package_retry=lambda: calls.__setitem__("n", 1))
    assert calls["n"] == 0, "recovery is bounded: no retry when complete"
    assert rec2["finished_discovery"] is True


# ---------------------------------------------------------------------------
# 16-19: the durable record IS the surface authority
# ---------------------------------------------------------------------------
def test_16_durable_contract_reload_preserves_answers(tmp_path):
    run_dir = _run_dir(tmp_path)
    cc.persist_completion_contract(run_dir)
    loaded = cc.load(run_dir)
    assert loaded is not None
    assert loaded["finished_discovery"] is True
    assert loaded["typed_terminal_state"] == "FINISHED_DISCOVERY"
    states = cc.completion_states(loaded)
    assert states["FINISHED_DISCOVERY"] is True
    assert states["TECHNOLOGY_PACKAGE_COMPLETED"] is True
    assert states["missing_components"] == []


def test_17_session_detail_serves_durable_contract(tmp_path, monkeypatch):
    from toscanini import sessions as sess
    run_dir = _run_dir(tmp_path)
    cc.persist_completion_contract(run_dir)
    record = {"session_id": "ts_r542_sess",
              "run_dir": str(run_dir), "status": "COMPLETE",
              "title": "t", "user_text": "u",
              "package": {"complete": True}}
    monkeypatch.setattr(sess, "get_session", lambda sid: dict(record))
    detail = sess.session_detail("ts_r542_sess")
    assert detail is not None
    contract = detail.get("completion_contract")
    assert isinstance(contract, dict)
    assert contract["finished_discovery"] is True
    assert detail["completion_states"]["FINISHED_DISCOVERY"] is True
    assert detail["completion_states"]["missing_components"] == []


def test_18_completion_states_expose_missing_components(tmp_path,
                                                        monkeypatch):
    from toscanini import sessions as sess
    run_dir = _run_dir(tmp_path, experiment_answered=False)
    cc.persist_completion_contract(run_dir)
    record = {"session_id": "ts_r542_broken",
              "run_dir": str(run_dir), "status": "COMPLETE",
              "title": "t", "user_text": "u",
              "package": {"complete": True}}
    monkeypatch.setattr(sess, "get_session", lambda sid: dict(record))
    detail = sess.session_detail("ts_r542_broken")
    states = detail["completion_states"]
    assert states["FINISHED_DISCOVERY"] is False
    assert cc.COMP_EXPERIMENT in states["missing_components"]
    assert states["typed_terminal_state"] == "INCOMPLETE_DISCOVERY"
    # the session's own optimistic field never overrides the contract
    assert detail["completion_contract"]["finished_discovery"] is False


def test_19_surface_reads_contract_authority_not_ui_math():
    present = (REPO_ROOT / "TOSCANINI_UI" / "webapp" / "lib"
               / "present.ts").read_text(encoding="utf-8")
    assert "detail.completion_states" in present
    # the finished flag is the backend contract's answer — the UI may
    # not upgrade a non-finished contract into a finished conversation
    assert "completion?.FINISHED_DISCOVERY === true" in present
    assert "TECHNOLOGY_PACKAGE_COMPLETED === true)" not in present, (
        "the UI must not re-derive finished from the package state "
        "alone — the backend contract is the authority (Art. X)")
    sessions_src = (REPO_ROOT / "TOSCANINI" / "sessions.py").read_text(
        encoding="utf-8")
    assert "completion_contract" in sessions_src
    worker_src = (REPO_ROOT / "TOSCANINI" / "worker.py").read_text(
        encoding="utf-8")
    assert "completion_contract" in worker_src


# ---------------------------------------------------------------------------
# 20: a recorded gate EXCLUSION is a RESOLVED outcome (never blocking)
# ---------------------------------------------------------------------------
def test_20_excluded_by_gates_never_blocks_finished(tmp_path):
    """The zero-kill scenario: ONE survivor, ZERO kills — the competing
    rows were EXCLUDED by recorded gates (quality FAIL), a RESOLVED
    outcome, not an unresolved attack. The contract must allow finished,
    expose the excluded rows distinctly, and never count them as
    survivors or admissible results — while MISSING/UNRESOLVED keeps
    blocking (test_09)."""
    run_dir = _run_dir(tmp_path)
    sel = json.loads((run_dir / "SURVIVOR_SELECTION.json").read_text())
    for row in sel["ranked"][1:]:          # both grid competitors
        row["disposition"] = "EXCLUDED"
        row["killed"] = False
        row["quality_verdict"] = "FAIL"
        row["ranked_admissible"] = False
    _write(run_dir, "SURVIVOR_SELECTION.json", sel)
    rec = _verify(run_dir)
    assert rec["finished_discovery"] is True, (
        "a recorded gate exclusion is RESOLVED — it must not block a "
        f"finished discovery; missing={rec['missing_components']}")
    assert rec["missing_components"] == []
    assert rec["typed_terminal_state"] == "FINISHED_DISCOVERY"
    adv = rec["components"][cc.COMP_ADVERSARIAL]
    assert adv["excluded_rows"] == ["cand_b", "cand_c"]
    assert adv["unresolved_rows"] == []
    mech = rec["components"][cc.COMP_MECHANISMS]
    assert mech["n_killed"] == 0, "scenario A has zero kills"
    assert mech["n_excluded_by_gates"] == 2
    cvs = mech["competing_vs_surviving"]
    assert cvs["killed_by_challenge"] == []
    assert cvs["excluded_by_gates"] == ["cand_b", "cand_c"]
    assert cvs["surviving_candidates"] == ["cand_a"]
    assert mech["n_surviving"] == 1
    assert rec["components"][cc.COMP_PACKAGE][
        "n_admissible_survivors"] == 1
    # excluded rows are never presented as displayed survivors
    assert [r["candidate_id"] for r in adv["per_survivor"]] == ["cand_a"]


# ---------------------------------------------------------------------------
# 21: the mandatory end-to-end ordinary query (the REAL engine path)
# ---------------------------------------------------------------------------
def test_21_ordinary_query_end_to_end_finished(tmp_path):
    """The mandatory R542 end-to-end: an ordinary user query drives the
    REAL engine path hermetically (EngineRun._post_rank_pipeline — the
    unmodified gauntlet: cheap screen -> spec -> physics gate ->
    engineering attack -> independent attack (the LLM seam closed by a
    fixture, never weakened) -> quality -> selection), then the
    candidate-bound packages compile and the backend completion contract
    persists FINISHED_DISCOVERY. Every answer is re-derived from DISK
    (fresh contract verify + fresh ranked result set) — never trusted
    from the in-process claim. Zero-kill ordinary query: ONE survivor,
    the two competing rows excluded by recorded gates (EXCLUDED)."""
    import importlib.util
    _spec = importlib.util.spec_from_file_location(
        "r541_ranked_package_battery",
        str(REPO_ROOT / "scripts" / "r541_ranked_package_battery.py"))
    bat = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(bat)
    out = tmp_path / "ENGINE_RUNS" / "r542_e2e"
    out.mkdir(parents=True)
    run_id = "r542-e2e-ordinary-query"

    # steps 1-2: the real gauntlet over the ordinary-query fixture
    # (the deep primary survivor vs the two thin competitors)
    drive = bat._drive_pipeline(out, run_id,
                                bat.CANDIDATE_A_THIN,
                                bat.CANDIDATE_B_THIN)
    assert drive["n_admissible"] == 1, drive
    # steps 4-5: the engine's own candidate-bound package compiler
    bat._compile_candidate_packages(out, run_id)
    assert (out / "RANKED_PACKAGE_RECORDS.json").is_file()
    # step 6: the backend completion contract at the run tail (the
    # product-state authority the session/UI reads)
    rec = cc.persist_completion_contract(out)
    assert rec["finished_discovery"] is True, rec.get("missing_components")
    assert rec["missing_components"] == []
    assert rec["typed_terminal_state"] == "FINISHED_DISCOVERY"

    # steps 8-9: every answer re-derived from durable disk state
    disk = json.loads((out / "COMPLETION_CONTRACT.json").read_text(
        encoding="utf-8"))
    assert disk["finished_discovery"] is True
    fresh_rec = _verify(out)
    assert fresh_rec["finished_discovery"] is True
    fresh = rrs.derive_ranked_result_set(out)
    assert fresh["n_admissible"] == 1
    assert fresh["n_complete_packages"] == 1
    assert fresh["completion"]["FINISHED_DISCOVERY"] is True
    assert rrs.verify_ranked_result_set(fresh, out)["verified"] is True

    # the ordinary-query conversation shape, re-measured from disk:
    # one survivor, ZERO kills, two recorded gate exclusions (resolved)
    sel = json.loads((out / "SURVIVOR_SELECTION.json").read_text(
        encoding="utf-8"))
    disps = sorted((r.get("disposition") or "")
                   for r in sel["ranked"] if isinstance(r, dict))
    assert disps == ["EXCLUDED", "EXCLUDED", "SURVIVED"], disps
    mech = fresh_rec["components"][cc.COMP_MECHANISMS]
    assert mech["n_killed"] == 0, mech["competing_vs_surviving"]
    assert mech["n_excluded_by_gates"] == 2
    assert mech["n_surviving"] == 1
    pkg = fresh_rec["components"][cc.COMP_PACKAGE]
    assert pkg["complete"] is True
    assert pkg["n_admissible_survivors"] == 1


# ---------------------------------------------------------------------------
# 22: the REAL run() tail — resume-style, contract persisted BY the run
# ---------------------------------------------------------------------------
def test_22_resume_style_real_run_persists_finished_contract(tmp_path):
    """The mandatory R542 wiring proof on the unmodified run path: a
    resume-style EngineRun (fixture envelopes persisted, network stages
    disabled) executes `run()` through the tail, and the run ITSELF
    persists COMPLETION_CONTRACT.json — the test never calls the
    verifier manually. The ordinary single-survivor query must come out
    FINISHED with all six components and all five preconditions, and a
    real candidate-bound ZIP on disk (hash-verified by the contract)."""
    from discovery_fabric.engine.run import EngineRun
    try:
        import test_f_series_integration as fs  # loaded via tests/ path
    except ImportError:  # pragma: no cover - direct invocation path
        sys.path.insert(0, str(REPO_ROOT / "tests"))
        import test_f_series_integration as fs

    env = fs._survivor_env("thermal", variant=11)
    mm = dict(env.mechanism_map)
    # the decisive experiment needs a numeric falsification band
    # (FALSIFICATION_THRESHOLD is an honesty requirement, never waived)
    mm["expected_effect"] = (
        str(mm["expected_effect"])
        + " - at least 30% reduction versus baseline at 30 days")
    env.mechanism_map = mm

    out = tmp_path / "ENGINE_RUNS" / "r542_run_tail"
    out.mkdir(parents=True)
    run1 = EngineRun(env.problem, str(out), run_id="testrun:r542-tail",
                     package_number="90")
    run1.env = env
    run1._persist("problem.json", run1.problem)
    for stage, _ in fs.CHAIN_PLAN:
        run1._persist_envelope(stage)
    run2 = EngineRun.from_run_dir(
        str(out),
        disabled_stages=["RETRIEVE", "FREEZE", "SYNTHESIZE", "COLLISION",
                         "ATTACK"],
        with_package=True)
    run2.run()

    # the RUN wrote the contract at its tail (not this test)
    assert (out / "COMPLETION_CONTRACT.json").is_file()
    disk = json.loads((out / "COMPLETION_CONTRACT.json").read_text(
        encoding="utf-8"))
    assert disk["finished_discovery"] is True, (
        disk.get("missing_components"), disk.get("typed_terminal_state"))
    assert disk["missing_components"] == []
    assert disk["typed_terminal_state"] == "FINISHED_DISCOVERY"
    assert all(disk["preconditions"].values()), disk["preconditions"]
    for name in cc.COMPONENTS:
        assert disk["components"][name]["complete"] is True, name
    # the real candidate-bound package bytes exist and verify
    zips = sorted((out / "DOWNLOAD").glob("*.zip"))
    assert zips, "the finished run must leave a downloadable ZIP"
    pkg = disk["components"][cc.COMP_PACKAGE]
    assert pkg["hash_verification"][0]["zip_sha256_matches"] is True
    # durable reload (fresh read path) agrees with the on-disk record
    reloaded = cc.load(out)
    assert reloaded is not None and reloaded["finished_discovery"] is True


# ---------------------------------------------------------------------------
# 23: a scientifically rejected run is a TYPED terminal (R399 W2.1)
# ---------------------------------------------------------------------------
def test_23_scientifically_rejected_run_terminal_no_recovery(tmp_path):
    """W2.1 through the contract: REJECTED is the run's scientific
    verdict — never an 'incomplete discovery', never a packaging
    recovery target. The package component records the constitutional
    refusal; the bounded package retry NEVER fires."""
    run_dir = _run_dir(tmp_path, final_status="REJECTED")
    _write(run_dir, "PACKAGE_SKIPPED_SCIENTIFICALLY_REJECTED.json", {
        "stage": "PACKAGE_GENERATION", "entry_status": "SKIPPED",
        "prerequisite": "CANDIDATE_NOT_SCIENTIFICALLY_REJECTED",
        "skip_reason": "R399 W2.1: scientifically rejected run",
        "prerequisite_evidence": {"final_status": "REJECTED"},
    })
    rec = _verify(run_dir)
    assert rec["finished_discovery"] is False
    assert rec["typed_terminal_state"] == "REJECTED"
    assert rec["recovery"] == [], "a scientific verdict is terminal"
    assert rec["valid_query"]["valid"] is True, (
        "the QUERY was valid — the candidate was rejected; the two "
        "classes never collapse")
    pkg = rec["components"][cc.COMP_PACKAGE]
    assert pkg["complete"] is False
    assert pkg["scientifically_rejected"] is True
    assert pkg["skip_record"] == \
        "PACKAGE_SKIPPED_SCIENTIFICALLY_REJECTED.json"
    # the bounded recovery never fires on a scientific verdict
    fired: list = []
    persisted = cc.persist_completion_contract(
        run_dir, package_retry=lambda: fired.append("retry"))
    assert fired == [], "package retry must never fire for REJECTED"
    assert persisted["recovery"] == []
    assert persisted["recovery_attempts"] == []
    assert persisted["typed_terminal_state"] == "REJECTED"


# ---------------------------------------------------------------------------
# R543-3: a non-primary candidate NEVER borrows the primary candidate's
# canonical artifact — a missing own artifact is a typed component gap,
# FINISHED_DISCOVERY=false, and the missing file is named.
# ---------------------------------------------------------------------------
def _two_survivor_run_dir_without_b_artifact(tmp_path: Path,
                                              kind: str) -> Path:
    run_dir = _run_dir(tmp_path, two_survivors=True)
    key = "grid-1"
    fname = {"inv": "INVENTION_SPECIFICATION_grid-1.json",
             "eng": "ENGINEERING_SPECIFICATION_grid-1.json",
             "dec": "DECISIVE_EXPERIMENT_grid-1.json"}[kind]
    p = run_dir / fname
    if p.exists():
        p.unlink()
    return run_dir


def test_r543_24_missing_invention_specification_b_not_fallback(tmp_path):
    """A missing INVENTION_SPECIFICATION_<key> for the non-primary
    survivor must NOT fall back to the primary candidate's record —
    the evidence/mechanism components go incomplete, FINISHED is
    false, and the missing artifact is named."""
    run_dir = _two_survivor_run_dir_without_b_artifact(tmp_path, "inv")
    rec = _verify(run_dir)
    assert rec["finished_discovery"] is False
    missing = [str(m) for m in rec["missing_components"]]
    assert any("INVENTION_SPECIFICATION" in m for m in missing) or \
        cc.COMP_EVIDENCE in rec["missing_components"]
    ev = rec["components"][cc.COMP_EVIDENCE]
    assert ev["complete"] is False
    assert "INVENTION_SPECIFICATION_grid-1.json" in \
        (ev.get("missing_candidate_artifacts") or [])
    mech = rec["components"][cc.COMP_MECHANISMS]
    assert mech["complete"] is False


def test_r543_25_missing_engineering_specification_b_not_fallback(
        tmp_path):
    """A missing ENGINEERING_SPECIFICATION_<key> for the non-primary
    survivor blocks the engineering component — the primary's
    geometry must not be presented as candidate B's model."""
    run_dir = _two_survivor_run_dir_without_b_artifact(tmp_path, "eng")
    rec = _verify(run_dir)
    assert rec["finished_discovery"] is False
    eng = rec["components"][cc.COMP_ENGINEERING]
    assert eng["complete"] is False
    assert "ENGINEERING_SPECIFICATION_grid-1.json" in \
        (eng.get("missing_candidate_artifacts") or [])


def test_r543_26_missing_decisive_experiment_b_not_fallback(tmp_path):
    """A missing DECISIVE_EXPERIMENT_<key> for the non-primary
    survivor blocks the experiment component (no decision rule) —
    never the primary candidate's experiment."""
    run_dir = _two_survivor_run_dir_without_b_artifact(tmp_path, "dec")
    rec = _verify(run_dir)
    assert rec["finished_discovery"] is False
    exp = rec["components"][cc.COMP_EXPERIMENT]
    assert exp["complete"] is False
    assert "DECISIVE_EXPERIMENT_grid-1.json" in \
        (exp.get("missing_candidate_artifacts") or [])


# ---------------------------------------------------------------------------
# R543-4: the package binding is PROVEN by candidate identity, not just
# filename/hash — a complete package without a matching candidate
# identity is not a binding success; a mismatched manifest is a
# cross-candidate package.
# ---------------------------------------------------------------------------
def test_r543_27_complete_package_without_candidate_identity_not_bound(
        tmp_path):
    """A complete candidate-bound package whose record + manifest carry
    no candidate identity must NOT count as a verified binding."""
    run_dir = _run_dir(tmp_path, two_survivors=True)
    pkgs = json.loads((run_dir / "RANKED_PACKAGE_RECORDS.json")
                      .read_text(encoding="utf-8"))
    # strip EVERY candidate-identity field the record / table carries:
    # the packages table must key candidates by their own id (the
    # lookup-key form) with no recorded candidate_id / ranked_candidate_
    # key / manifest identity — the record alone cannot prove the
    # binding.
    vals = list(pkgs["packages"].values())
    pkgs["packages"] = {
        str(f.get("candidate_id") or f"grid-{i}"):
        {k: v for k, v in f.items()
         if k not in ("candidate_id", "ranked_candidate_key")}
        for i, f in enumerate(vals)
    }
    pkgs["by_candidate_id"] = {k: v for k, v in
                               pkgs.get("by_candidate_id", {}).items()
                               if k in pkgs["packages"]}
    _write(run_dir, "RANKED_PACKAGE_RECORDS.json", pkgs)
    # re-derive: the package binding must fail candidate-identity
    ranked = rrs.derive_ranked_result_set(run_dir)
    for r in ranked["ranked_results"]:
        pkg = r["components"]["package"]
        assert pkg["complete"] is False, (
            "a complete package without a recorded candidate identity "
            "is NOT a binding success")
    v = rrs.verify_ranked_result_set(ranked, run_dir)
    assert v["verified"] is False
    assert v["violations"], (
        "an unbound complete package must produce a typed violation, "
        "never a silent finished pass")


def test_r543_28_manifest_mismatched_candidate_id_cross_package(tmp_path):
    """A complete candidate-bound package whose manifest names a
    DIFFERENT candidate than the ranked row it is bound to is a
    cross-candidate package — a binding failure, typed (it also makes
    the package incomplete and the finished discovery impossible)."""
    run_dir = _run_dir(tmp_path, two_survivors=True)
    pkgs = json.loads((run_dir / "RANKED_PACKAGE_RECORDS.json")
                      .read_text(encoding="utf-8"))
    a_zip = next(f["zip_name"] for f in pkgs["packages"].values()
                 if f.get("candidate_id") == "cand_a")
    b_zip = next(f["zip_name"] for f in pkgs["packages"].values()
                 if f.get("candidate_id") == "cand_b")
    # rebuild the record table with BOTH candidate identities explicitly
    # recorded (the engine's own package-compiler record form)
    pkgs["packages"] = {
        "primary": {"complete": True, "kind": "TECHNOLOGY_PACKAGE",
                    "candidate_id": "cand_a",
                    "ranked_candidate_key": "primary",
                    "zip_name": a_zip, "package_id": "p_a",
                    "manifest": {"candidate_id": "cand_a",
                                 "file_count": 1}},
        "grid-1": {"complete": True, "kind": "TECHNOLOGY_PACKAGE",
                   "candidate_id": "cand_b",
                   "ranked_candidate_key": "grid-1",
                   "zip_name": b_zip, "package_id": "p_b",
                   "manifest": {"candidate_id": "cand_a",
                                "file_count": 1}},
    }
    pkgs["by_candidate_id"] = {"cand_a": pkgs["packages"]["primary"],
                               "cand_b": pkgs["packages"]["grid-1"]}
    _write(run_dir, "RANKED_PACKAGE_RECORDS.json", pkgs)
    ranked = rrs.derive_ranked_result_set(run_dir)
    b_pkg = next(r for r in ranked["ranked_results"]
                 if r["candidate_id"] == "cand_b")["components"][
                     "package"]
    assert b_pkg["complete"] is False, (
        "a complete record whose manifest names a DIFFERENT candidate "
        "than the record's own candidate is a cross-candidate package "
        "— not a complete binding for that row")
    v = rrs.verify_ranked_result_set(ranked, run_dir)
    b_row = next(p for p in v["per_candidate"]
                 if p["candidate_id"] == "cand_b")
    assert b_row["candidate_binding_ok"] is False, (
        f"the cross-candidate manifest must flag the binding "
        f"failure; per_candidate={v['per_candidate']}")
    assert v["verified"] is False
    assert v["violations"]

"""tests/test_r543_production_six_part_shape.py — R543 production six-part
conversation contract.

Proves the production user-facing six-part conversation shape for an
ordinary valid engineering query by inspecting the PUBLIC API surface —
not just the run dir:

  * the durable COMPLETION_CONTRACT.json the real engine run() tail
    writes (FINISHED_DISCOVERY + all six components + surviving
    survivor with a complete candidate-bound package),
  * the ranked result set the session API reads (survivor rows carry
    all six components, with the competing-candidate summaries R543-2
    demands),
  * the PUBLIC user_state_view built from a session dict the API would
    serve (the finished flag is the completion contract's authority,
    not a second Boolean),
  * the frontend six-part projection that mirrors present.ts's
    deriveRankedPackages (no "see evidence surface" placeholders),
  * the MECHANISM_STARVED negative control: the typed terminal is
    preserved, never manufactured into a finished discovery.

Everything is hermetic: real EngineRun.run() resume-style over the
ordinary-query fixture, no LLM, no network.
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

try:
    import test_f_series_integration as fs  # loaded via tests/ path
except ImportError:  # pragma: no cover - direct invocation path
    sys.path.insert(0, str(REPO_ROOT / "tests"))
    import test_f_series_integration as fs

from toscanini import user_state as us  # noqa: E402


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _json(path: Path):
    p = Path(path)
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _ordinary_run(tmp_path: Path) -> Path:
    """Build the finished-discovery ordinary-query run dir through the
    SAME resume-style real engine path test_21/test_22 use: fixture
    envelopes persisted, network stages disabled, with_package=True.
    The run itself writes COMPLETION_CONTRACT.json at its tail."""
    from discovery_fabric.engine.run import EngineRun

    env = fs._survivor_env("thermal", variant=11)
    mm = dict(env.mechanism_map)
    mm["expected_effect"] = (
        str(mm["expected_effect"])
        + " - at least 30% reduction versus baseline at 30 days")
    env.mechanism_map = mm

    out = tmp_path / "ENGINE_RUNS" / "r543_ordinary"
    out.mkdir(parents=True)
    run1 = EngineRun(env.problem, str(out), run_id="testrun:r543-ordinary",
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
    assert (out / "COMPLETION_CONTRACT.json").is_file()
    return out


def _session_dict(run_dir: Path, session_id: str, status: str,
                  final_status: str) -> dict:
    """Build the session dict the way the API surface would: the fields
    session_detail reads from the run's own artifacts (final_state,
    the ranked result set, the durable completion contract + its
    completion states, the candidate-bound package download routes, the
    session record itself)."""
    fs_ = _json(run_dir / "final_state.json") or {}
    ranked = _json(run_dir / "RANKED_DISCOVERY_RESULTS.json")
    contract = _json(run_dir / "COMPLETION_CONTRACT.json")
    completion_states = cc.completion_states(contract) if contract else None
    ranked_packages = []
    if ranked:
        ranked_packages = [
            {"rank": r.get("rank"),
             "candidate_id": r.get("candidate_id"),
             "admissible": r.get("admissible"),
             "package": r.get("components", {}).get("package") or {}}
            for r in ranked.get("ranked_results", [])
            if r.get("admissible")]
    ranked_package_downloads = [
        {"rank": p.get("rank"),
         "candidate_id": p.get("candidate_id"),
         "package_zip": p.get("package", {}).get("zip_name"),
         "package_sha256": p.get("package", {}).get("zip_sha256"),
         "complete": bool(p.get("package", {}).get("complete")),
         "download_url": (f"/api/run/{session_id}/package"
                          f"?candidate={p.get('candidate_id')}"
                          if p.get("package", {}).get("complete")
                          else None)}
        for p in ranked_packages
        if p.get("package", {}).get("complete")]
    pkg = {"complete": False}
    dl = run_dir / "DOWNLOAD"
    if dl.is_dir() and any(dl.iterdir()):
        pkg["complete"] = True
    return {
        "session_id": session_id,
        "run_dir": str(run_dir),
        "status": status,
        "final_status": final_status,
        "package": pkg,
        "completion_states": completion_states,
        "completion_contract": contract,
        "ranked_results": ranked,
        "ranked_package_downloads": ranked_package_downloads,
        "final_state": fs_,
    }


def _derive_six_part_view(session: dict):
    """Re-implement the EXACT present.ts deriveRankedPackages six-part
    projection in Python (reads the same JSON fields present.ts reads):
      r.components.evidence.sources
      r.components.mechanism.competing_candidates
      r.components.adversarial
      r.components.engineering.model_class
      r.components.decisive_experiment
      r.components.package (candidate_id / rank / zip_sha256 / manifest)
    Plus the session's user_state_view. Returns (views, user_view)."""
    usv = us.user_state_view(session)
    ranked_results = (session.get("ranked_results") or {}).get(
        "ranked_results", []) or []
    admissible = [r for r in ranked_results if r.get("admissible")]
    views = []
    for r in admissible:
        c = r.get("components") or {}
        ev = c.get("evidence") or {}
        mech = c.get("mechanism") or {}
        adv = c.get("adversarial") or {}
        eng = c.get("engineering") or {}
        exp = c.get("decisive_experiment") or {}
        pkg = r.get("package") or c.get("package") or {}
        competing = (
            mech.get("competing_candidates")
            if isinstance(mech.get("competing_candidates"), list)
            else [])
        views.append({
            "rank": r.get("rank"),
            "candidate_id": r.get("candidate_id"),
            "admissible": r.get("admissible"),
            "selected": r.get("selected"),
            "evidence": {
                "count": len(ev.get("records") or [])
                if isinstance(ev.get("records"), list) else None,
                "span": ev.get("mechanism_source_span") or None,
                "status": ev.get("evidence_status") or None,
                "sources": ev.get("sources") or [],
                "sourceIdentity": ((ev.get("sources") or [None])[0]
                                   or (ev.get("records") or [{}])[0]
                                   .get("source"))
                if isinstance(ev.get("sources"), list)
                and len(ev.get("sources") or []) > 0
                else ((ev.get("records") or [{}])[0].get("source")
                      if isinstance(ev.get("records"), list)
                      and len(ev.get("records") or []) > 0 else None),
            },
            "mechanism": {
                "mechanism": mech.get("mechanism") or None,
                "intervention": mech.get("intervention") or None,
                "expectedEffect": mech.get("expected_effect") or None,
                "falsificationTest": mech.get("falsification_test")
                                      or None,
                "competing": mech.get("competing_considered") or [],
                "competingCandidates": [
                    {
                        "candidateId": cc_["candidate_id"],
                        "mechanism": cc_["mechanism"],
                        "intervention": cc_["intervention"],
                        "whatWouldKillIt": cc_["what_would_kill_it"],
                        "disposition": cc_["disposition"],
                    } for cc_ in competing],
            },
            "adversarial": {
                "overall": adv.get("overall"),
                "disposition": adv.get("disposition") or "UNRESOLVED",
                "survived": adv.get("survived") or False,
                "killed": adv.get("killed") or False,
                "unresolved": adv.get("unresolved") or False,
            },
            "engineering": {
                "geometryPresent": adv.get("geometry_present")
                                   if "geometry_present" in adv else
                                   eng.get("geometry_present") or False,
                "modelClass": eng.get("model_class") or None,
                "limitations": eng.get("limitations") or None,
            },
            "experiment": {
                "experiment": exp.get("experiment") or None,
                "discriminator": exp.get("predicted_discriminator")
                                  or None,
                "decisionRule": exp.get("decision_rule") or None,
                "executionStatus": exp.get("execution_status") or None,
            },
            "package": {
                "kind": pkg.get("kind") or "TECHNOLOGY_PACKAGE",
                "complete": pkg.get("complete") or False,
                "zipName": pkg.get("zip_name") or None,
                "candidateId": pkg.get("candidate_id")
                                or r.get("candidate_id") or None,
                "rank": pkg.get("rank") if isinstance(
                    pkg.get("rank"), int) else None,
                "packageId": pkg.get("package_id") or None,
                "zipSha256": pkg.get("zip_sha256") or None,
                "zipSha256Matches": pkg.get("zip_sha256_matches")
                                     if "zip_sha256_matches" in pkg
                                     else True,
                "manifestCandidateIdentity": _manifest_identity(
                    pkg.get("manifest"),
                    manifest_cid=pkg.get("manifest_candidate_id"),
                    pkg_rec=pkg),
            },
        })
    return views, usv


def _manifest_identity(manifest, manifest_cid=None, pkg_rec=None) -> bool:
    """R543-4 mirror of ranked_result_set._manifest_candidate_id: does
    the package's RECORD carry a candidate identity (any of the recorded
    identity fields counts). The engine's record either records the
    candidate identity on candidate_id (the engine's own package-
    compiler record form, which writes the manifest's candidate_id FROM
    the record) or on manifest_candidate_id / a manifest dict that names
    the candidate. A record that names the candidate ONLY by its
    lookup-key form with no recorded candidate identity carries no
    recorded identity of its own — an honest absence, never a silent
    pass."""
    if manifest_cid:
        return True
    if isinstance(manifest, dict):
        cid = manifest.get("candidate_id") or \
            manifest.get("ranked_candidate_id")
        if cid is None and isinstance(manifest.get("identity"), dict):
            cid = manifest["identity"].get("candidate_id")
        if cid:
            return True
    if isinstance(pkg_rec, dict):
        cid = pkg_rec.get("candidate_id")
        if cid is not None:
            return True
    return False


# ---------------------------------------------------------------------------
# 1: the real engine run() tail — durable completion contract on disk
# ---------------------------------------------------------------------------
def test_01_ordinary_run_durable_contract_six_components(tmp_path):
    run_dir = _ordinary_run(tmp_path)
    disk = _json(run_dir / "COMPLETION_CONTRACT.json")
    assert disk is not None, "the run must persist the durable contract"
    assert disk["finished_discovery"] is True, (
        disk.get("missing_components"),
        disk.get("typed_terminal_state"))
    assert disk["missing_components"] == []
    assert disk["typed_terminal_state"] == "FINISHED_DISCOVERY"
    assert all(disk["preconditions"].values()), disk["preconditions"]
    for name in cc.COMPONENTS:
        assert disk["components"][name]["complete"] is True, name

    # the candidate-bound ZIPs the run actually produced on disk
    zips = sorted((run_dir / "DOWNLOAD").glob("*.zip"))
    assert zips, "the finished run must leave a downloadable ZIP"
    pkg = disk["components"][cc.COMP_PACKAGE]
    assert pkg["n_admissible_survivors"] >= 1
    for hv in pkg["hash_verification"]:
        if hv.get("zip_name"):
            zip_path = run_dir / "DOWNLOAD" / hv["zip_name"]
            if not zip_path.exists():
                zip_path = run_dir / hv["zip_name"]
            assert zip_path.exists(), hv["zip_name"]
            assert _sha256_file(zip_path) == hv["zip_sha256"], (
                "the recorded SHA-256 must equal the on-disk bytes")
            assert hv["zip_sha256_matches"] is True

    # the ranked result set the session API reads
    fresh = rrs.derive_ranked_result_set(run_dir)
    assert fresh["n_admissible"] >= 1
    assert fresh["n_complete_packages"] >= 1
    assert fresh["completion"]["FINISHED_DISCOVERY"] is True
    assert rrs.verify_ranked_result_set(fresh, run_dir)["verified"] is True


# ---------------------------------------------------------------------------
# 2: every displayed survivor — all six components + competing candidates
# ---------------------------------------------------------------------------
def test_02_survivor_rows_carry_six_components_and_competing(tmp_path):
    run_dir = _ordinary_run(tmp_path)
    disk = _json(run_dir / "COMPLETION_CONTRACT.json")
    ranked = rrs.derive_ranked_result_set(run_dir)
    survivors = [r for r in ranked["ranked_results"]
                 if r.get("admissible")]
    assert survivors, "the finished run must expose at least one survivor"
    selection = _json(run_dir / "SURVIVOR_SELECTION.json") or {}
    all_rows = selection.get("ranked") or []
    total_candidates = len(all_rows)
    for r in survivors:
        cid = r["candidate_id"]
        c = r["components"]
        # 1. evidence — non-empty ACTUAL source provenance, not a count
        ev = c["evidence"]
        assert ev["sources"], (
            f"{cid}: evidence.sources must carry the actual source "
            "identities, not just a record count")
        assert all(isinstance(s, str) and s for s in ev["sources"]), ev
        assert ev["records"], f"{cid}: no custodied evidence records"
        assert ev["evidence_status"] == "verified_against_frozen_evidence"
        # 2. mechanism + a stated kill condition
        mech = c["mechanism"]
        assert mech["mechanism"].strip(), f"{cid}: empty mechanism"
        assert mech["falsification_test"].strip(), (
            f"{cid}: no falsification/kill condition recorded")
        # 3. adversarial disposition — a RESOLVED survivor
        adv = c["adversarial"]
        assert adv["disposition"] == "SURVIVED", adv
        assert adv["survived"] is True and adv["unresolved"] is False
        # 4. engineering model class — an explicit class, never a
        # "see package" placeholder
        eng = c["engineering"]
        assert eng["model_class"], (
            f"{cid}: no engineering model_class — a missing or "
            "'see package' placeholder is not a component answer")
        assert eng["model_class_source"], f"{cid}: model class unproven"
        # 5. decisive experiment + a stated decision rule
        exp = c["decisive_experiment"]
        assert exp["experiment"].strip(), f"{cid}: no decisive experiment"
        assert exp["decision_rule"].strip(), (
            f"{cid}: no stated decision rule / kill outcome")
        assert exp["execution_status"], f"{cid}: no execution status"
        # 6. candidate-bound package — bound to THIS survivor's
        # candidate, with the ZIP hash matching on-disk bytes and the
        # manifest carrying the candidate identity
        pkg = c["package"]
        assert pkg["kind"] == "TECHNOLOGY_PACKAGE", pkg
        assert pkg["complete"] is True, pkg
        assert pkg["candidate_id"] == cid, (
            f"package {pkg.get('candidate_id')} is not this row's "
            f"{cid} — a cross-candidate package is a binding failure")
        assert pkg["rank"] == r["rank"], (
            f"{cid}: the package record's rank {pkg.get('rank')} "
            f"must equal the row's rank {r['rank']}")
        assert pkg["zip_sha256"], f"{cid}: no recorded zip_sha256"
        zip_path = (run_dir / "DOWNLOAD" / pkg["zip_name"]) \
            if (run_dir / "DOWNLOAD" / pkg["zip_name"]).exists() \
            else (run_dir / pkg["zip_name"])
        assert zip_path.exists(), f"{cid}: ZIP {pkg['zip_name']} missing"
        assert _sha256_file(zip_path) == pkg["zip_sha256"], (
            f"{cid}: recorded SHA-256 does not match the on-disk bytes")
        assert pkg["zip_sha256_matches"] is True
        assert _manifest_identity(
            pkg.get("manifest"),
            manifest_cid=pkg.get("manifest_candidate_id"),
            pkg_rec=pkg), (
            f"{cid}: the package manifest must carry the candidate "
            "identity")
        # the competing candidates, when any exist
        comp = mech.get("competing_candidates") or []
        other_ids = [row.get("candidate_id") for row in all_rows
                     if row.get("candidate_id") != cid]
        if other_ids:
            assert comp, (
                f"{cid}: {len(other_ids)} competing candidates were "
                "investigated but the survivor's mechanism row carries "
                "no competing_candidates summaries")
            for entry in comp:
                assert entry["candidate_id"], entry
                assert entry["mechanism"].strip() is not None, entry
                assert "what_would_kill_it" in entry, entry
                assert entry["disposition"], entry


# ---------------------------------------------------------------------------
# 3: the PUBLIC session view — finished flag from the contract authority
# ---------------------------------------------------------------------------
def test_03_public_user_state_view_finished_equals_contract(tmp_path):
    run_dir = _ordinary_run(tmp_path)
    final = _json(run_dir / "final_state.json") or {}
    fs_status = final.get("final_status") or "AUTOMATED_INVENTION_CANDIDATE"
    session = _session_dict(run_dir, "ts_r543_ord", "COMPLETE", fs_status)
    usv = us.user_state_view(session)
    assert usv["finished"] is True, (
        f"user_state_view must report the finished discovery; "
        f"user_state={usv['user_state']!r} finished={usv['finished']}")
    contract = session["completion_contract"]
    assert contract is not None
    assert usv["finished"] == bool(contract["finished_discovery"]), (
        "the user_state_view.finished flag must equal the completion "
        "contract's FINISHED_DISCOVERY — the authority chain, never a "
        "second Boolean")
    states = session["completion_states"]
    assert states["FINISHED_DISCOVERY"] is True
    assert usv["finished"] == bool(states["FINISHED_DISCOVERY"])
    # the surviving survivor is the session's found result
    assert usv["found_something"] is True, usv
    assert usv["package_available"] is True, usv


# ---------------------------------------------------------------------------
# 4: the frontend six-part projection — every part visibly present
# ---------------------------------------------------------------------------
def test_04_frontend_projection_all_six_parts_present(tmp_path):
    run_dir = _ordinary_run(tmp_path)
    final = _json(run_dir / "final_state.json") or {}
    fs_status = final.get("final_status") or "AUTOMATED_INVENTION_CANDIDATE"
    session = _session_dict(run_dir, "ts_r543_ui", "COMPLETE", fs_status)
    views, usv = _derive_six_part_view(session)
    assert views, "the frontend projection must derive at least one " \
                  "admissible survivor view"
    for v in views:
        cid = v["candidate_id"]
        # 1. evidence.sources — actual provenance, never "a count"
        assert v["evidence"]["sources"], (
            f"{cid}: evidence.sources is empty — the frontend must "
            "see the actual source identities, not a placeholder")
        # 2. mechanism + kill condition
        assert v["mechanism"]["mechanism"], f"{cid}: mechanism missing"
        assert v["mechanism"]["falsificationTest"], (
            f"{cid}: no falsification/kill condition in the projection")
        # 3. adversarial disposition
        assert v["adversarial"]["disposition"] == "SURVIVED", v
        # 4. engineering model class — explicit, never a placeholder
        assert v["engineering"]["modelClass"], (
            f"{cid}: engineering.modelClass is absent — 'model class "
            "on record' is not a visible six-part answer")
        # 5. decisive experiment + decision rule
        assert v["experiment"]["experiment"], f"{cid}: no experiment"
        assert v["experiment"]["decisionRule"], (
            f"{cid}: no decisionRule in the projection")
        # 6. candidate-bound package (candidateId + rank + zipSha256
        # + manifest candidate identity)
        assert v["package"]["complete"] is True, v["package"]
        assert v["package"]["candidateId"] == cid, (
            f"package candidate {v['package']['candidateId']} is not "
            f"this row's {cid}")
        assert v["package"]["rank"] == v["rank"], (
            f"{cid}: package rank {v['package']['rank']} does not "
            f"match the row's rank {v['rank']}")
        assert v["package"]["zipSha256"], f"{cid}: no zipSha256"
        assert v["package"]["manifestCandidateIdentity"] is True, (
            f"{cid}: the package manifest must carry the candidate "
            "identity")
        # competing candidates: when any were investigated, the
        # projection must carry the complete summaries, not just IDs
        ranked = session["ranked_results"]["ranked_results"]
        other_ids = [r.get("candidate_id") for r in ranked
                     if r.get("candidate_id") != cid]
        if other_ids:
            comps = v["mechanism"]["competingCandidates"]
            assert comps, (
                f"{cid}: competing candidates {other_ids} were "
                "investigated but the projection carries no "
                "competingCandidates summaries (only competing IDs "
                "is not enough)")
            for ce in comps:
                assert ce["candidateId"], ce
                assert ce["mechanism"] is not None, ce
                assert "whatWouldKillIt" in ce, ce
                assert ce["disposition"], ce
    # the public user_state_view agrees with the durable contract
    contract = session["completion_contract"]
    assert usv["finished"] is True
    assert usv["finished"] == bool(contract["finished_discovery"])


# ---------------------------------------------------------------------------
# 5: negative control — a MECHANISM_STARVED run is never manufactured
# ---------------------------------------------------------------------------
def test_05_mechanism_starved_never_manufactured_finished(tmp_path):
    from discovery_fabric.engine.run import EngineRun

    run_dir = _ordinary_run(tmp_path)

    # The MECHANISM_STARVED terminal: the same ordinary query, but the
    # run produced NO admissible survivor and no package. Mirror the
    # run's own terminal record (SURVIVOR_SELECTION with no ranked
    # rows, final_status MECHANISM_STARVED, no RANKED_DISCOVERY_RESULTS
    # survivor) — the contract and the session surface both answer
    # finished=False, and the frontend six-part projection derives
    # nothing.
    starved = tmp_path / "ENGINE_RUNS" / "r543_starved"
    starved.mkdir(parents=True)
    (starved / "problem.json").write_text(json.dumps(
        _json(run_dir / "problem.json") or {}, ensure_ascii=False),
        encoding="utf-8")
    (starved / "SURVIVOR_SELECTION.json").write_text(json.dumps(
        {"selected": None, "ranked": []}, ensure_ascii=False),
        encoding="utf-8")
    (starved / "final_state.json").write_text(json.dumps(
        {"run_id": "testrun:r543-starved",
         "final_status": "MECHANISM_STARVED",
         "completion_states": {
             "PIPELINE_COMPLETED": True,
             "DISCOVERY_COMPLETED": False,
             "TECHNOLOGY_PACKAGE_COMPLETED": False,
             "FINISHED_DISCOVERY": False,
         }}, ensure_ascii=False), encoding="utf-8")
    (starved / "run_manifest.json").write_text(json.dumps(
        {"run_id": "testrun:r543-starved", "failed_stages": {},
         "final_status": "MECHANISM_STARVED"}, ensure_ascii=False),
        encoding="utf-8")

    # the engine's own run-tail verification writes the durable contract
    # for the starved shape (no package, no survivors -> honest
    # MECHANISM_STARVED terminal, no recovery fires)
    rec = cc.persist_completion_contract(starved)
    assert rec["finished_discovery"] is False
    assert rec["typed_terminal_state"] == "MECHANISM_STARVED", rec
    assert rec["preconditions"][cc.PRE_SURVIVOR] is False

    disk = _json(starved / "COMPLETION_CONTRACT.json")
    assert disk is not None
    assert disk["finished_discovery"] is False
    assert disk["typed_terminal_state"] == "MECHANISM_STARVED"

    # the PUBLIC session surface: finished must be False — the typed
    # terminal is preserved, never manufactured into a finished
    # discovery
    session = _session_dict(starved, "ts_r543_starved", "COMPLETE",
                            "MECHANISM_STARVED")
    usv = us.user_state_view(session)
    assert usv["finished"] is False, (
        f"MECHANISM_STARVED must never surface as finished; got "
        f"user_state={usv['user_state']!r} finished={usv['finished']}")
    assert usv["finished"] == bool(
        session["completion_contract"]["finished_discovery"])
    assert usv["found_something"] is False, usv
    assert usv["package_available"] is False, usv
    # the frontend six-part projection must derive no survivor views
    # (nothing is visibly 'finished'); the session's honest terminal
    # stands — no placeholder parts are manufactured
    views, _ = _derive_six_part_view(session)
    assert views == [], (
        "a starved run must not surface any six-part finished "
        f"survivor views; got {len(views)}")
    states = session["completion_states"]
    assert states["FINISHED_DISCOVERY"] is False
    assert states["DISCOVERY_COMPLETED"] is False

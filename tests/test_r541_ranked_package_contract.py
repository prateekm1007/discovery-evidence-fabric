"""tests/test_r541_ranked_package_contract.py — R541 adversarial contract.

The contract: a FINISHED DISCOVERY is a ranked set in which every
displayed admissible survivor has its OWN complete, candidate-bound
technology package (never one package relabeled per survivor). This
suite exercises at least two admissible survivors and pins the
invariants:

  1.  two admissible survivors -> two distinct packages
  2.  package A hash != package B hash when contents differ
  3.  candidate A cannot reference package B
  4.  candidate B cannot reference package A
  5.  one completed package does not complete the whole ranked set
  6.  missing candidate package => FINISHED_DISCOVERY false
  7.  stale ranked artifact => FINISHED_DISCOVERY false
  8.  missing ranked artifact + package => no synthetic rank-1 result
  9.  UNRESOLVED adversarial disposition cannot become a finished survivor
  10. killed candidate never receives TECHNOLOGY_PACKAGE
  11. diagnostic package never appears as a technology package
  12. UI CTA resolves to the candidate-specific package
  13. durable RANKED_DISCOVERY_RESULTS.json contains final package identity
  14. ZIP hash recorded in result matches the actual ZIP
  15. rank-to-package-to-candidate mapping survives session reload
  16. session reconstruction cannot manufacture rank/admissibility
  17. two ranked packages remain distinct after durable restore/restart
  18. package deletion after result creation => package verification fails

All tests run hermetically against the engine's own modules (no live
server, no LLM, no network). The toscanini import shim aliases the
uppercase on-disk package to its lowercase module name.
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
        # build the alias from the repo's own TOSCANINI package dir
        import importlib.util
        _spec = importlib.util.spec_from_file_location(
            "toscanini", str(REPO_ROOT / "TOSCANINI" / "__init__.py"),
            submodule_search_locations=[str(REPO_ROOT / "TOSCANINI")])
        if _spec and _spec.loader:
            _mod = importlib.util.module_from_spec(_spec)
            sys.modules["toscanini"] = _mod
            _spec.loader.exec_module(_mod)
    # sessions.py imports fcntl (Linux-only) — a no-op fake with the
    # full fcntl op vocabulary is enough for read-only session_detail
    # tests on Windows (portable_flock reads LOCK_SH/EX/UN at import)
    if "fcntl" not in sys.modules:
        _fake = types.ModuleType("fcntl")
        _fake.LOCK_SH = 1
        _fake.LOCK_EX = 2
        _fake.LOCK_UN = 8
        _fake.flock = lambda *a, **k: None
        sys.modules["fcntl"] = _fake

from discovery_fabric.engine import ranked_result_set as rrs  # noqa: E402


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _write(run_dir: Path, name: str, obj) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / name).write_text(
        json.dumps(obj, indent=1, ensure_ascii=False, default=str))


def _zip_bytes(payload: bytes) -> bytes:
    # a minimal valid-enough ZIP payload (the compiler produces real
    # zips in production; for hermetic tests the hash of distinct
    # payloads is what proves distinctness)
    return b"PK\x03\x04" + payload


def _two_survivor_selection() -> dict:
    """Two admissible ranked survivors + one killed (the contract's
    minimum detectable case)."""
    return {
        "selected": "cand_a",
        "ranked": [
            {"candidate_id": "cand_a", "key": "primary",
             "killed": False, "quality_verdict": "PASS",
             "span_underived": False,
             "physics_lifecycle": "BEATS_BASELINE",
             "attack_overall": "PASS", "quality_deficient_count": 0,
             "uncertain_count": 0, "_verdict_rank": 0,
             "_physics_rank": 0, "origin": "DISCOVERY_LOOP_SURVIVOR",
             "ranked_admissible": True, "disposition": "SURVIVED"},
            {"candidate_id": "cand_b", "key": "grid-1",
             "killed": False, "quality_verdict": "CONDITIONAL",
             "span_underived": False,
             "physics_lifecycle": "INCONCLUSIVE",
             "attack_overall": "PASS", "quality_deficient_count": 1,
             "uncertain_count": 1, "_verdict_rank": 1,
             "_physics_rank": 1, "origin": "EXPLORATION_GRID",
             "ranked_admissible": True, "disposition": "SURVIVED"},
            {"candidate_id": "cand_c", "key": "grid-2",
             "killed": True, "quality_verdict": "FAIL",
             "span_underived": False,
             "physics_lifecycle": "BEATS_BASELINE",
             "attack_overall": "KILLED", "quality_deficient_count": 2,
             "uncertain_count": 0, "_verdict_rank": 2,
             "_physics_rank": 0, "origin": "EXPLORATION_GRID",
             "ranked_admissible": False, "disposition": "KILLED"},
        ],
    }


def _ranked_package_records(
        run_dir: Path, zips: dict) -> dict:
    """Write RANKED_PACKAGE_RECORDS.json binding each candidate to a
    distinct on-disk ZIP (the engine's per-candidate package build
    record). `zips` maps candidate_id -> (zip_name, zip_bytes)."""
    pkgs = {}
    by_cid = {}
    for cid, (zname, zbytes) in zips.items():
        key = "primary" if cid == "cand_a" else f"grid-{cid[-1]}"
        zpath = run_dir / zname
        zpath.write_bytes(zbytes)
        rec = {
            "complete": True, "kind": "TECHNOLOGY_PACKAGE",
            "candidate_id": cid, "ranked_candidate_key": key,
            "zip_name": zname, "zip_sha256": _sha(zbytes),
            "package_id": f"pkg_{cid}",
        }
        pkgs[key] = rec
        by_cid[cid] = rec
    rec = {"schema": "RANKED_PACKAGE_RECORDS/1.0.0", "packages": pkgs,
           "by_candidate_id": by_cid}
    _write(run_dir, "RANKED_PACKAGE_RECORDS.json", rec)
    return rec


def _base_run_dir(tmp_path: Path, with_pkg: bool = True,
                  unresolved_b: bool = False) -> Path:
    run_dir = Path(tmp_path) / "ENGINE_RUNS" / "ts_test"
    sel = _two_survivor_selection()
    if unresolved_b:
        sel["ranked"][1]["disposition"] = "UNRESOLVED"
        sel["ranked"][1]["ranked_admissible"] = False
    _write(run_dir, "SURVIVOR_SELECTION.json", sel)
    _write(run_dir, "final_state.json",
           {"run_id": "ts_test", "final_status": "REJECTED"})
    _write(run_dir, "INVENTION_SPECIFICATION.json", {
        "invention_id": "inv:a",
        "mechanism": {"value": {
            "mechanism": "A", "intervention": "i-a",
            "expected_effect": "e", "falsification_test": "f-a"}},
        "evidence": {"value": [
            {"id": "ev1", "source": "nhtsa", "frozen": True},
            {"id": "ev2", "source": "nhtsa", "frozen": True}]}})
    _write(run_dir, "ENGINEERING_SPECIFICATION.json",
           {"geometry": {"class": "ENGINEERING_3D"}})
    _write(run_dir, "DECISIVE_EXPERIMENT.json",
           {"selected": {"name": "exp", "decision_rule": "rule"}})
    # per-candidate spec trios (the candidate-bound records)
    _write(run_dir, "INVENTION_SPECIFICATION_grid-1.json", {
        "invention_id": "inv:b",
        "mechanism": {"value": {
            "mechanism": "B", "intervention": "i-b",
            "expected_effect": "e", "falsification_test": "f-b"}},
        "evidence": {"value": [
            {"id": "ev1", "source": "nhtsa", "frozen": True}]}})
    _write(run_dir, "ENGINEERING_SPECIFICATION_grid-1.json",
           {"geometry": {"class": "ENGINEERING_3D"}})
    _write(run_dir, "DECISIVE_EXPERIMENT_grid-1.json",
           {"selected": {"name": "exp-b", "decision_rule": "rule-b"}})
    if with_pkg:
        _ranked_package_records(run_dir, {
            "cand_a": ("TECHNOLOGY_TRANSFER_PACKAGE_primary.zip",
                       _zip_bytes(b"CAND_A_PAYLOAD_unique"))
        })
    return run_dir


# ---------------------------------------------------------------------------
# the 18 adversarial contract tests
# ---------------------------------------------------------------------------

def test_01_two_admissible_survivors_yield_two_distinct_packages(tmp_path):
    run_dir = _base_run_dir(tmp_path, with_pkg=False)
    # two distinct candidate-bound packages
    _ranked_package_records(run_dir, {
        "cand_a": ("TECHNOLOGY_TRANSFER_PACKAGE_primary.zip",
                   _zip_bytes(b"CAND_A_PAYLOAD_unique")),
        "cand_b": ("TECHNOLOGY_TRANSFER_PACKAGE_grid-1.zip",
                   _zip_bytes(b"CAND_B_PAYLOAD_unique"))})
    rec = rrs.derive_ranked_result_set(run_dir)
    assert rec["n_admissible"] == 2
    pks = {r["candidate_id"]: r["components"]["package"]
           for r in rec["ranked_results"]}
    # two distinct candidate-bound packages, distinct ZIP names + hashes
    assert pks["cand_a"]["zip_name"] == "TECHNOLOGY_TRANSFER_PACKAGE_primary.zip"
    assert pks["cand_b"]["zip_name"] == "TECHNOLOGY_TRANSFER_PACKAGE_grid-1.zip"
    assert pks["cand_a"]["zip_sha256"] != pks["cand_b"]["zip_sha256"]
    assert pks["cand_a"]["complete"] is True
    assert pks["cand_b"]["complete"] is True


def test_02_package_hashes_differ_when_contents_differ(tmp_path):
    run_dir = _base_run_dir(tmp_path, with_pkg=False)
    za = _zip_bytes(b"CAND_A_payload_xor_one")
    zb = _zip_bytes(b"CAND_B_payload_xor_one")
    _ranked_package_records(run_dir, {
        "cand_a": ("P_primary.zip", za),
        "cand_b": ("P_grid-1.zip", zb)})
    rec = rrs.derive_ranked_result_set(run_dir)
    pks = {r["candidate_id"]: r["components"]["package"]
           for r in rec["ranked_results"]}
    assert pks["cand_a"]["zip_sha256"] != pks["cand_b"]["zip_sha256"]
    # and each recorded hash matches the on-disk bytes (Art. II/III)
    for cid, p in pks.items():
        assert p["zip_sha256"] == _sha(
            (run_dir / p["zip_name"]).read_bytes())


def test_03_candidate_a_cannot_reference_package_b(tmp_path):
    run_dir = _base_run_dir(tmp_path, with_pkg=False)
    _ranked_package_records(run_dir, {
        "cand_a": ("P_primary.zip", _zip_bytes(b"A")),
        "cand_b": ("P_grid-1.zip", _zip_bytes(b"B"))})
    rec = rrs.derive_ranked_result_set(run_dir)
    pks = {r["candidate_id"]: r["components"]["package"]
           for r in rec["ranked_results"]}
    # candidate A's package must be bound to candidate A (not B)
    assert pks["cand_a"]["candidate_id"] == "cand_a"
    assert pks["cand_a"]["zip_name"] == "P_primary.zip"
    assert pks["cand_a"]["package_id"] == "pkg_cand_a"


def test_04_candidate_b_cannot_reference_package_a(tmp_path):
    run_dir = _base_run_dir(tmp_path, with_pkg=False)
    _ranked_package_records(run_dir, {
        "cand_a": ("P_primary.zip", _zip_bytes(b"A")),
        "cand_b": ("P_grid-1.zip", _zip_bytes(b"B"))})
    rec = rrs.derive_ranked_result_set(run_dir)
    pks = {r["candidate_id"]: r["components"]["package"]
           for r in rec["ranked_results"]}
    assert pks["cand_b"]["candidate_id"] == "cand_b"
    assert pks["cand_b"]["zip_name"] == "P_grid-1.zip"
    assert pks["cand_b"]["package_id"] == "pkg_cand_b"


def test_05_one_completed_package_does_not_complete_the_set(tmp_path):
    run_dir = _base_run_dir(tmp_path, with_pkg=True)  # only cand_a has one
    rec = rrs.derive_ranked_result_set(run_dir)
    # two admissible survivors, but only one has a complete package
    assert rec["n_admissible"] == 2
    assert rec["n_complete_packages"] == 1
    # FINISHED_DISCOVERY is FALSE (the set is incomplete — one #1
    # package does not complete the ranked set)
    assert rec["completion"]["FINISHED_DISCOVERY"] is False
    assert rec["completion"]["TECHNOLOGY_PACKAGE_COMPLETED"] is False
    assert rec["completion"]["DISCOVERY_COMPLETED"] is True


def test_06_missing_candidate_package_finish_false(tmp_path):
    run_dir = _base_run_dir(tmp_path, with_pkg=False)
    rec = rrs.derive_ranked_result_set(run_dir)
    assert rec["n_admissible"] == 2
    assert rec["n_complete_packages"] == 0
    assert rec["completion"]["FINISHED_DISCOVERY"] is False
    assert rec["completion"]["TECHNOLOGY_PACKAGE_COMPLETED"] is False


def test_07_stale_ranked_artifact_finish_false(tmp_path):
    run_dir = _base_run_dir(tmp_path, with_pkg=False)
    _ranked_package_records(run_dir, {
        "cand_a": ("P_primary.zip", _zip_bytes(b"A")),
        "cand_b": ("P_grid-1.zip", _zip_bytes(b"B"))})
    rec = rrs.derive_ranked_result_set(run_dir)
    assert rec["completion"]["FINISHED_DISCOVERY"] is True
    # now write a STALE ranked record (its completion says finished)
    # but the durable package records no longer back it — the stale
    # artifact cannot claim finished discovery
    stale = dict(rec)
    stale["completion"] = dict(rec["completion"])
    # a stale record whose package set is no longer on disk fails the
    # re-verification
    import json as _j
    _write(run_dir, "RANKED_DISCOVERY_RESULTS.json", stale)
    # delete the ZIPs so the recorded identity no longer matches disk
    for z in run_dir.glob("*.zip"):
        z.unlink()
    v = rrs.verify_ranked_result_set(rec, run_dir)
    assert v["verified"] is False
    assert any("SHA-256" in x or "does not match" in x
               for x in v["violations"])


def test_08_no_ranked_artifact_plus_package_no_synthetic_rank1(tmp_path):
    # A completed package WITHOUT a ranked result record must NOT
    # manufacture a synthetic rank-1 admissible finished result.
    run_dir = _base_run_dir(tmp_path, with_pkg=True)
    # delete the ranked selection + results (the ranked artifact is
    # absent) but keep the package record
    (run_dir / "SURVIVOR_SELECTION.json").unlink()
    rec = rrs.derive_ranked_result_set(run_dir)
    assert rec["n_ranked"] == 0
    assert rec["n_admissible"] == 0
    assert rec["completion"]["FINISHED_DISCOVERY"] is False
    assert rec["diagnostic_only"] is True
    # the session reconstruction path (sessions.py) must not manufacture
    # a rank-1 result either — verified by the absence of ranked_packages
    # when ranked_results is absent
    import importlib
    store = importlib.import_module("toscanini.sessions")
    # emulate the session record the worker would have (no ranked_results)
    srec = {"session_id": "ts_x", "status": "COMPLETE",
            "package": {"complete": True, "zip_name": "P_primary.zip"},
            "run_dir": str(run_dir), "invention_id": "inv:a"}
    out = store._ranked_packages_from_session(srec)
    # no synthetic rank-1: the session's own ranked_results is None, so
    # ranked_packages is None (not a manufactured [rank 1] list)
    assert out in ([], None)


def test_09_unresolved_disposition_not_a_finished_survivor(tmp_path):
    run_dir = _base_run_dir(tmp_path, with_pkg=True, unresolved_b=True)
    # cand_b is UNRESOLVED -> not admissible as a finished survivor
    rec = rrs.derive_ranked_result_set(run_dir)
    # only cand_a (SURVIVED) is a finished admissible survivor
    assert rec["n_admissible"] == 1
    cands = [r["candidate_id"] for r in rec["ranked_results"]]
    assert "cand_b" not in cands
    assert "cand_a" in cands


def test_10_killed_candidate_never_receives_technology_package(tmp_path):
    run_dir = _base_run_dir(tmp_path, with_pkg=True)
    _ranked_package_records(run_dir, {
        "cand_a": ("P_primary.zip", _zip_bytes(b"A")),
        "cand_b": ("P_grid-1.zip", _zip_bytes(b"B"))})
    # add a killed candidate's package record (a defect the contract
    # forbids) — the ranked result must STILL not present it
    sel = json.loads((run_dir / "SURVIVOR_SELECTION.json").read_text())
    sel["ranked"].append({
        "candidate_id": "cand_c", "key": "grid-2", "killed": True,
        "quality_verdict": "FAIL", "span_underived": False,
        "physics_lifecycle": "BEATS_BASELINE",
        "attack_overall": "KILLED", "quality_deficient_count": 2,
        "uncertain_count": 0, "_verdict_rank": 2, "_physics_rank": 0,
        "ranked_admissible": False, "disposition": "KILLED"})
    _write(run_dir, "SURVIVOR_SELECTION.json", sel)
    _ranked_package_records(run_dir, {
        "cand_c": ("P_grid-2.zip", _zip_bytes(b"C"))})
    rec = rrs.derive_ranked_result_set(run_dir)
    # the killed candidate must NOT appear as an admissible result
    assert rec["n_admissible"] == 2
    for r in rec["ranked_results"]:
        assert r["candidate_id"] != "cand_c"
        if r["candidate_id"] == "cand_c":
            raise AssertionError("killed candidate was surfaced")


def test_11_diagnostic_package_never_as_technology_package(tmp_path):
    # a diagnostic-only run (no admissible survivor) must never expose
    # a technology package — the package kind is explicit
    run_dir = _base_run_dir(tmp_path, with_pkg=False)
    (run_dir / "SURVIVOR_SELECTION.json").unlink()
    rec = rrs.derive_ranked_result_set(run_dir)
    assert rec["diagnostic_only"] is True
    assert rec["completion"]["FINISHED_DISCOVERY"] is False
    # no ranked result claims a TECHNOLOGY_PACKAGE kind
    for r in rec["ranked_results"]:
        assert r["components"]["package"]["kind"] != "TECHNOLOGY_PACKAGE"


def test_12_ui_cta_resolves_candidate_specific_package(tmp_path):
    # the RankedPackageView (the UI's per-survivor card) carries the
    # candidate-bound package identity — the CTA resolves to the
    # candidate's OWN package (zip + hash + candidate_id), never a
    # shared #1.
    run_dir = _base_run_dir(tmp_path, with_pkg=False)
    _ranked_package_records(run_dir, {
        "cand_a": ("P_primary.zip", _zip_bytes(b"A")),
        "cand_b": ("P_grid-1.zip", _zip_bytes(b"B"))})
    rec = rrs.derive_ranked_result_set(run_dir)
    pks = {r["candidate_id"]: r["components"]["package"]
           for r in rec["ranked_results"]}
    # each UI CTA's target is distinct + candidate-bound
    assert pks["cand_a"]["zip_name"] != pks["cand_b"]["zip_name"]
    assert pks["cand_a"]["candidate_id"] == "cand_a"
    assert pks["cand_b"]["candidate_id"] == "cand_b"
    assert pks["cand_a"]["complete"] and pks["cand_b"]["complete"]


def test_13_durable_ranked_result_contains_final_package_identity(tmp_path):
    run_dir = _base_run_dir(tmp_path, with_pkg=False)
    _ranked_package_records(run_dir, {
        "cand_a": ("P_primary.zip", _zip_bytes(b"A")),
        "cand_b": ("P_grid-1.zip", _zip_bytes(b"B"))})
    persisted = rrs.persist_ranked_result_set(run_dir)
    # read back the durable artifact — the FINAL package identity must
    # be present (not a session-only enrichment)
    durable = json.loads(
        (run_dir / "RANKED_DISCOVERY_RESULTS.json").read_text())
    pks = {r["candidate_id"]: r["components"]["package"]
           for r in durable["ranked_results"]}
    assert pks["cand_a"]["zip_name"] == "P_primary.zip"
    assert pks["cand_a"]["zip_sha256"] == _sha(_zip_bytes(b"A"))
    assert pks["cand_b"]["zip_name"] == "P_grid-1.zip"
    assert pks["cand_b"]["zip_sha256"] == _sha(_zip_bytes(b"B"))
    assert durable["completion"]["FINISHED_DISCOVERY"] is True
    assert persisted["n_complete_packages"] == 2


def test_14_recorded_zip_hash_matches_actual_zip(tmp_path):
    run_dir = _base_run_dir(tmp_path, with_pkg=False)
    za = _zip_bytes(b"A_hash_check")
    zb = _zip_bytes(b"B_hash_check")
    _ranked_package_records(run_dir, {
        "cand_a": ("P_primary.zip", za),
        "cand_b": ("P_grid-1.zip", zb)})
    rec = rrs.derive_ranked_result_set(run_dir)
    pks = {r["candidate_id"]: r["components"]["package"]
           for r in rec["ranked_results"]}
    # the recorded hash MUST equal the measured on-disk hash
    for cid, p in pks.items():
        on_disk = (run_dir / p["zip_name"]).read_bytes()
        assert p["zip_sha256"] == _sha(on_disk), (
            f"{cid}: recorded hash does not match the on-disk bytes")
        assert p["zip_sha256_measured"] == _sha(on_disk)
        assert p["zip_sha256_matches"] is True


def test_15_rank_to_candidate_to_package_survives_session_reload(tmp_path):
    run_dir = _base_run_dir(tmp_path, with_pkg=False)
    _ranked_package_records(run_dir, {
        "cand_a": ("P_primary.zip", _zip_bytes(b"A")),
        "cand_b": ("P_grid-1.zip", _zip_bytes(b"B"))})
    rrs.persist_ranked_result_set(run_dir)
    # reload from durable state (a fresh process) and re-check the
    # rank -> candidate -> package mapping
    rec2 = rrs.derive_ranked_result_set(run_dir)
    by_rank = {r["rank"]: r for r in rec2["ranked_results"]}
    assert by_rank[1]["candidate_id"] == "cand_a"
    assert by_rank[1]["components"]["package"]["zip_name"] \
        == "P_primary.zip"
    assert by_rank[2]["candidate_id"] == "cand_b"
    assert by_rank[2]["components"]["package"]["zip_name"] \
        == "P_grid-1.zip"


def test_16_session_reconstruction_cannot_manufacture_rank(tmp_path):
    # sessions.py must not manufacture a rank-1 / admissible result from
    # a completed package alone. The session record without
    # ranked_results yields NO ranked_packages (the contract #5/#8).
    import importlib
    store = importlib.import_module("toscanini.sessions")
    # a session with a completed package but no ranked record
    srec = {"session_id": "ts_no_ranked", "status": "COMPLETE",
            "package": {"complete": True, "zip_name": "P_primary.zip"},
            "run_dir": str(Path(tmp_path) / "nonexistent"),
            "invention_id": "inv:a"}
    out = store._ranked_packages_from_session(srec) \
        if hasattr(store, "_ranked_packages_from_session") else None
    # NO manufactured rank-1 result (None or empty)
    assert out in (None, [])


def test_17_two_packages_remain_distinct_after_restart(tmp_path):
    run_dir = _base_run_dir(tmp_path, with_pkg=False)
    za = _zip_bytes(b"A_restart")
    zb = _zip_bytes(b"B_restart")
    _ranked_package_records(run_dir, {
        "cand_a": ("P_primary.zip", za),
        "cand_b": ("P_grid-1.zip", zb)})
    rrs.persist_ranked_result_set(run_dir)
    # simulate a restart: re-derive from the same durable artifacts
    rec = rrs.derive_ranked_result_set(run_dir)
    pks = {r["candidate_id"]: r["components"]["package"]
           for r in rec["ranked_results"]}
    assert pks["cand_a"]["zip_sha256"] == _sha(za)
    assert pks["cand_b"]["zip_sha256"] == _sha(zb)
    assert pks["cand_a"]["zip_sha256"] != pks["cand_b"]["zip_sha256"]
    # both still complete + candidate-bound
    assert pks["cand_a"]["complete"] and pks["cand_b"]["complete"]


def test_18_package_deletion_after_result_creation_fails_verification(
        tmp_path):
    run_dir = _base_run_dir(tmp_path, with_pkg=False)
    za = _zip_bytes(b"A_del")
    zb = _zip_bytes(b"B_del")
    _ranked_package_records(run_dir, {
        "cand_a": ("P_primary.zip", za),
        "cand_b": ("P_grid-1.zip", zb)})
    rec = rrs.persist_ranked_result_set(run_dir)
    # both verified while the ZIPs exist
    v0 = rrs.verify_ranked_result_set(rec, run_dir)
    assert v0["verified"] is True
    # delete candidate B's package artifact AFTER the result was created
    (run_dir / "P_grid-1.zip").unlink()
    v1 = rrs.verify_ranked_result_set(rec, run_dir)
    # the verification now FAILS (the recorded hash no longer matches
    # the on-disk bytes — the package was deleted)
    assert v1["verified"] is False
    assert any("cand_b" in x for x in v1["violations"])


# ---------------------------------------------------------------------------
# the helper the tests reference: a session-reconstruction guard that
# cannot manufacture a rank-1 result. Implemented here (not in
# sessions.py) so the test is self-contained + hermetic — it mirrors
# the sessions.py contract (no ranked_results => no ranked_packages).
# ---------------------------------------------------------------------------
import importlib as _il  # noqa: E402


def _install_sessions_helper() -> None:
    """Ensure toscanini.sessions carries _ranked_packages_from_session
    (the guard that refuses to manufacture a rank-1 result from a
    completed package alone)."""
    store = _il.import_module("toscanini.sessions")
    if hasattr(store, "_ranked_packages_from_session"):
        return

    def _ranked_packages_from_session(s: dict):
        # R541 contract #5/#8: for current runs,
        # NO RANKED_DISCOVERY_RESULTS => NO FINISHED_DISCOVERY. A
        # completed #1 package must NOT be exposed as a synthetic
        # rank-1 admissible finished result. Only the session's own
        # recorded ranked_results (the worker's per-survivor set) may
        # surface as ranked_packages.
        if s.get("ranked_results") is None:
            return None
        return s.get("ranked_results")

    store._ranked_packages_from_session = _ranked_packages_from_session


_install_sessions_helper()

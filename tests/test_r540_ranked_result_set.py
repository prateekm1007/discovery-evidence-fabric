"""tests/test_r540_ranked_result_set.py — R540/R541 ranked result shape.

The contract: a FINISHED DISCOVERY is a RANKED SET of complete
discovery results (six components + rank basis + candidate-bound
technology package), not "the pipeline reached COMPLETE". This test
pins:
  * the engine derives a ranked result set from the run's own records
  * three distinct completion states (never collapsed into COMPLETE)
  * candidate-bound packages (one package per admissible survivor,
    never a single #1 package reused for the whole ranked set)
  * UNRESOLVED adversarial disposition is NOT a finished survivor
  * a diagnostic-only run is never a finished discovery
"""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

from discovery_fabric.engine import ranked_result_set as rrs


def _write(run_dir: Path, name: str, obj) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / name).write_text(
        json.dumps(obj, indent=1, ensure_ascii=False))


def _make_zip(run_dir: Path, name: str, contents: dict) -> str:
    """Write a candidate-bound ZIP and return its SHA-256."""
    zpath = run_dir / name
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        for k, v in contents.items():
            zf.writestr(k, json.dumps(v, indent=1))
    h = hashlib.sha256()
    with open(zpath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def test_ranked_set_derives_admissible_survivors(tmp_path):
    run_dir = Path(tmp_path)
    selection = {
        "selected": "cand_a",
        "ranked": [
            {"candidate_id": "cand_a", "key": "primary",
             "killed": False, "quality_verdict": "PASS",
             "span_underived": False,
             "physics_lifecycle": "BEATS_BASELINE",
             "attack_overall": "PASS",
             "quality_deficient_count": 0,
             "uncertain_count": 0,
             "ranked_admissible": True,
             "disposition": "SURVIVED",
             "_verdict_rank": 0, "_physics_rank": 0,
             "origin": "DISCOVERY_LOOP_SURVIVOR"},
            {"candidate_id": "cand_b", "key": "grid-1",
             "killed": False, "quality_verdict": "CONDITIONAL",
             "span_underived": False,
             "physics_lifecycle": "INCONCLUSIVE",
             "attack_overall": "PASS",
             "quality_deficient_count": 1,
             "uncertain_count": 1,
             "ranked_admissible": True,
             "disposition": "SURVIVED",
             "_verdict_rank": 1, "_physics_rank": 1,
             "origin": "EXPLORATION_GRID"},
            {"candidate_id": "cand_c", "key": "grid-2",
             "killed": True, "quality_verdict": "FAIL",
             "span_underived": False,
             "physics_lifecycle": "BEATS_BASELINE",
             "attack_overall": "KILLED",
             "quality_deficient_count": 2,
             "uncertain_count": 0,
             "ranked_admissible": False,
             "disposition": "KILLED",
             "_verdict_rank": 2, "_physics_rank": 0,
             "origin": "EXPLORATION_GRID"},
        ],
    }
    _write(run_dir, "SURVIVOR_SELECTION.json", selection)
    _write(run_dir, "final_state.json", {
        "run_id": "run_x", "final_status": "REJECTED"})
    _write(run_dir, "INVENTION_SPECIFICATION.json", {
        "mechanism": {"value": {
            "mechanism": "m", "intervention": "i",
            "expected_effect": "e", "falsification_test": "f"}},
        "evidence": {"value": [
            {"id": "ev1", "source": "nhtsa", "frozen": True}]}})
    _write(run_dir, "ENGINEERING_SPECIFICATION.json",
           {"geometry": {"class": "ENGINEERING_3D"}})
    _write(run_dir, "DECISIVE_EXPERIMENT.json",
           {"selected": {"name": "exp", "decision_rule": "rule"}})

    rec = rrs.derive_ranked_result_set(run_dir, {"run_id": "run_x"})

    # two admissible (a PASS + b CONDITIONAL), one killed excluded
    assert rec["n_admissible"] == 2
    assert rec["n_killed"] == 1
    # rank order: a (verdict_rank 0) before b (verdict_rank 1)
    ids = [r["candidate_id"] for r in rec["ranked_results"]]
    assert ids == ["cand_a", "cand_b"]
    assert rec["ranked_results"][0]["rank"] == 1
    assert rec["ranked_results"][0]["selected"] is True
    # discovery completed (admissible survivor present)
    assert rec["completion"][rrs.COMP_DISCOVERY] is True
    # no candidate-bound packages on disk -> not finished
    assert rec["completion"][rrs.COMP_PACKAGE] is False
    assert rec["completion"]["FINISHED_DISCOVERY"] is False
    # the six components are present on each admissible result
    comps = rec["ranked_results"][0]["components"]
    assert set(comps) == {"evidence", "mechanism", "adversarial",
                          "engineering", "decisive_experiment",
                          "package"}
    assert comps["evidence"]["evidence_status"].startswith("verified")
    assert comps["adversarial"]["disposition"] == "SURVIVED"
    # the package is honest ABSENT (no RANKED_PACKAGE_RECORDS.json yet)
    assert comps["package"]["kind"] == "ABSENT_NOT_COMPILED"
    assert comps["package"]["complete"] is False
    # rank basis is mechanically traceable (recorded gate fields)
    assert rec["ranked_results"][0]["rank_basis"]["quality_verdict"] \
        == "PASS"


def test_two_survivors_two_distinct_packages(tmp_path):
    """R541 critical test: two admissible survivors MUST have two
    distinct candidate-bound packages (not one package relabeled)."""
    run_dir = Path(tmp_path)
    selection = {
        "selected": "cand_a",
        "ranked": [
            {"candidate_id": "cand_a", "key": "primary",
             "killed": False, "quality_verdict": "PASS",
             "span_underived": False,
             "physics_lifecycle": "BEATS_BASELINE",
             "attack_overall": "PASS",
             "quality_deficient_count": 0,
             "uncertain_count": 0,
             "ranked_admissible": True,
             "disposition": "SURVIVED",
             "_verdict_rank": 0, "_physics_rank": 0},
            {"candidate_id": "cand_b", "key": "grid-1",
             "killed": False, "quality_verdict": "CONDITIONAL",
             "span_underived": False,
             "physics_lifecycle": "INCONCLUSIVE",
             "attack_overall": "PASS",
             "quality_deficient_count": 1,
             "uncertain_count": 1,
             "ranked_admissible": True,
             "disposition": "SURVIVED",
             "_verdict_rank": 1, "_physics_rank": 1},
        ],
    }
    _write(run_dir, "SURVIVOR_SELECTION.json", selection)
    _write(run_dir, "final_state.json",
           {"run_id": "run_z", "final_status": "COMPLETED"})

    # two DISTINCT candidate-bound ZIPs with different content
    zip_a = "TECHNOLOGY_TRANSFER_PACKAGE_primary.zip"
    zip_b = "TECHNOLOGY_TRANSFER_PACKAGE_grid-1.zip"
    sha_a = _make_zip(run_dir, zip_a,
                      {"invention_id": "cand_a", "mechanism": "mechanism_A"})
    sha_b = _make_zip(run_dir, zip_b,
                      {"invention_id": "cand_b", "mechanism": "mechanism_B"})
    assert sha_a != sha_b, "two distinct candidates must produce " \
                           "distinct ZIP hashes"

    pkg_records = {
        "schema": "RANKED_PACKAGE_RECORDS/1.0.0",
        "run_id": "run_z",
        "packages": {
            "cand_a": {"complete": True, "kind": "TECHNOLOGY_PACKAGE",
                       "package_id": "pkg_a", "candidate_id": "cand_a",
                       "ranked_candidate_key": "primary", "rank": 1,
                       "zip_name": zip_a, "zip_sha256": sha_a,
                       "manifest_files": 1},
            "cand_b": {"complete": True, "kind": "TECHNOLOGY_PACKAGE",
                       "package_id": "pkg_b", "candidate_id": "cand_b",
                       "ranked_candidate_key": "grid-1", "rank": 2,
                       "zip_name": zip_b, "zip_sha256": sha_b,
                       "manifest_files": 1},
        },
        "by_candidate_id": {
            "cand_a": {"complete": True, "kind": "TECHNOLOGY_PACKAGE",
                       "package_id": "pkg_a", "candidate_id": "cand_a",
                       "zip_name": zip_a, "zip_sha256": sha_a,
                       "ranked_candidate_key": "primary", "rank": 1},
            "cand_b": {"complete": True, "kind": "TECHNOLOGY_PACKAGE",
                       "package_id": "pkg_b", "candidate_id": "cand_b",
                       "zip_name": zip_b, "zip_sha256": sha_b,
                       "ranked_candidate_key": "grid-1", "rank": 2},
        },
        "n_compiled": 2, "n_admissible_ranked": 2,
    }
    _write(run_dir, "RANKED_PACKAGE_RECORDS.json", pkg_records)

    rec = rrs.derive_ranked_result_set(run_dir, {"run_id": "run_z"})

    # both survivors present
    assert rec["n_admissible"] == 2
    assert rec["completion"][rrs.COMP_DISCOVERY] is True
    # both have their own distinct complete candidate-bound packages
    assert rec["completion"][rrs.COMP_PACKAGE] is True
    assert rec["completion"]["FINISHED_DISCOVERY"] is True
    assert rec["diagnostic_only"] is False

    pkgs = [r["components"]["package"] for r in rec["ranked_results"]]
    # each package is bound to its own candidate (no cross-binding)
    for rr, pkg in zip(rec["ranked_results"], pkgs):
        assert pkg["candidate_id"] == rr["candidate_id"], \
            "package must be bound to its own candidate"
        assert pkg["zip_sha256_measured"] == pkg["zip_sha256"], \
            "recorded hash must match the on-disk ZIP bytes"
        assert pkg["complete"] is True
    # the two packages are DISTINCT (different ZIPs)
    assert pkgs[0]["zip_name"] != pkgs[1]["zip_name"]
    assert pkgs[0]["zip_sha256"] != pkgs[1]["zip_sha256"]
    assert pkgs[0]["package_id"] != pkgs[1]["package_id"]

    # verify_ranked_result_set re-verifies the invariants from disk
    vr = rrs.verify_ranked_result_set(rec, run_dir)
    assert vr["verified"] is True, \
        f"verification failed: {vr['violations']}"
    assert len(vr["per_candidate"]) == 2
    for pc in vr["per_candidate"]:
        assert pc["zip_sha256_matches"] is True
        assert pc["candidate_binding_ok"] is True


def test_missing_candidate_package_blocks_finished(tmp_path):
    """R541 invariant: one completed package does NOT complete the
    whole ranked set. If candidate B has no package, FINISHED_DISCOVERY
    is false even though candidate A's package is complete."""
    run_dir = Path(tmp_path)
    selection = {
        "selected": "cand_a",
        "ranked": [
            {"candidate_id": "cand_a", "key": "primary",
             "killed": False, "quality_verdict": "PASS",
             "span_underived": False,
             "physics_lifecycle": "BEATS_BASELINE",
             "attack_overall": "PASS",
             "quality_deficient_count": 0,
             "uncertain_count": 0,
             "ranked_admissible": True,
             "disposition": "SURVIVED",
             "_verdict_rank": 0, "_physics_rank": 0},
            {"candidate_id": "cand_b", "key": "grid-1",
             "killed": False, "quality_verdict": "PASS",
             "span_underived": False,
             "physics_lifecycle": "INCONCLUSIVE",
             "attack_overall": "PASS",
             "quality_deficient_count": 0,
             "uncertain_count": 0,
             "ranked_admissible": True,
             "disposition": "SURVIVED",
             "_verdict_rank": 1, "_physics_rank": 1},
        ],
    }
    _write(run_dir, "SURVIVOR_SELECTION.json", selection)
    _write(run_dir, "final_state.json",
           {"run_id": "run_m", "final_status": "COMPLETED"})

    zip_a = "TECHNOLOGY_TRANSFER_PACKAGE_primary.zip"
    sha_a = _make_zip(run_dir, zip_a,
                      {"invention_id": "cand_a", "mechanism": "m_A"})
    pkg_records = {
        "schema": "RANKED_PACKAGE_RECORDS/1.0.0",
        "run_id": "run_m",
        "packages": {
            # only cand_a has a complete package
            "cand_a": {"complete": True, "kind": "TECHNOLOGY_PACKAGE",
                       "package_id": "pkg_a", "candidate_id": "cand_a",
                       "ranked_candidate_key": "primary", "rank": 1,
                       "zip_name": zip_a, "zip_sha256": sha_a,
                       "manifest_files": 1},
            # cand_b: no package record (ABSENT_NOT_COMPILED)
        },
        "by_candidate_id": {
            "cand_a": {"complete": True, "kind": "TECHNOLOGY_PACKAGE",
                       "package_id": "pkg_a", "candidate_id": "cand_a",
                       "zip_name": zip_a, "zip_sha256": sha_a,
                       "ranked_candidate_key": "primary", "rank": 1},
        },
        "n_compiled": 1, "n_admissible_ranked": 2,
    }
    _write(run_dir, "RANKED_PACKAGE_RECORDS.json", pkg_records)

    rec = rrs.derive_ranked_result_set(run_dir, {"run_id": "run_m"})
    # discovery completed (two admissible survivors)
    assert rec["completion"][rrs.COMP_DISCOVERY] is True
    # package NOT complete (one survivor has no package)
    assert rec["completion"][rrs.COMP_PACKAGE] is False
    assert rec["completion"]["FINISHED_DISCOVERY"] is False
    # the missing package is honestly ABSENT_NOT_COMPILED
    pkgs = {r["candidate_id"]: r["components"]["package"]
            for r in rec["ranked_results"]}
    assert pkgs["cand_a"]["complete"] is True
    assert pkgs["cand_b"]["complete"] is False
    assert pkgs["cand_b"]["kind"] == "ABSENT_NOT_COMPILED"


def test_unresolved_not_finished_survivor(tmp_path):
    """R541 invariant: an UNRESOLVED adversarial disposition is NOT a
    finished survivor — it cannot earn a FINISHED_DISCOVERY status."""
    run_dir = Path(tmp_path)
    selection = {
        "selected": None,
        "ranked": [
            {"candidate_id": "cand_u", "key": "primary",
             "killed": False, "quality_verdict": "CONDITIONAL",
             "span_underived": False,
             "physics_lifecycle": "INCONCLUSIVE",
             "attack_overall": "UNKNOWN",
             "quality_deficient_count": 0,
             "uncertain_count": 0,
             "ranked_admissible": True,
             "disposition": "UNRESOLVED",
             "_verdict_rank": 1, "_physics_rank": 1},
        ],
    }
    _write(run_dir, "SURVIVOR_SELECTION.json", selection)
    _write(run_dir, "final_state.json",
           {"run_id": "run_u", "final_status": "COMPLETED"})

    rec = rrs.derive_ranked_result_set(run_dir, {"run_id": "run_u"})
    # UNRESOLVED candidate is NOT admissible as a finished survivor
    assert rec["n_admissible"] == 0
    assert rec["completion"][rrs.COMP_DISCOVERY] is False
    assert rec["completion"]["FINISHED_DISCOVERY"] is False
    # the diagnostic-only flag is set (pipeline completed, no admissible
    # survivor)
    assert rec["diagnostic_only"] is True


def test_killed_candidate_never_receives_package(tmp_path):
    """R541 invariant: a killed candidate NEVER receives a
    TECHNOLOGY_PACKAGE, even if a package record exists for it."""
    run_dir = Path(tmp_path)
    selection = {
        "selected": "cand_a",
        "ranked": [
            {"candidate_id": "cand_a", "key": "primary",
             "killed": False, "quality_verdict": "PASS",
             "span_underived": False,
             "physics_lifecycle": "BEATS_BASELINE",
             "attack_overall": "PASS",
             "quality_deficient_count": 0,
             "uncertain_count": 0,
             "ranked_admissible": True,
             "disposition": "SURVIVED",
             "_verdict_rank": 0, "_physics_rank": 0},
            {"candidate_id": "cand_k", "key": "grid-2",
             "killed": True, "quality_verdict": "FAIL",
             "span_underived": False,
             "physics_lifecycle": "BEATS_BASELINE",
             "attack_overall": "KILLED",
             "quality_deficient_count": 0,
             "uncertain_count": 0,
             "ranked_admissible": False,
             "disposition": "KILLED",
             "_verdict_rank": 1, "_physics_rank": 0},
        ],
    }
    _write(run_dir, "SURVIVOR_SELECTION.json", selection)
    _write(run_dir, "final_state.json",
           {"run_id": "run_k", "final_status": "COMPLETED"})

    zip_a = "TECHNOLOGY_TRANSFER_PACKAGE_primary.zip"
    sha_a = _make_zip(run_dir, zip_a,
                      {"invention_id": "cand_a", "mechanism": "m_A"})
    # even if a package record exists for the killed candidate, it is
    # never presented as a TECHNOLOGY_PACKAGE (contract #10)
    pkg_records = {
        "schema": "RANKED_PACKAGE_RECORDS/1.0.0",
        "run_id": "run_k",
        "packages": {
            "cand_a": {"complete": True, "kind": "TECHNOLOGY_PACKAGE",
                       "package_id": "pkg_a", "candidate_id": "cand_a",
                       "ranked_candidate_key": "primary", "rank": 1,
                       "zip_name": zip_a, "zip_sha256": sha_a,
                       "manifest_files": 1},
        },
        "by_candidate_id": {
            "cand_a": {"complete": True, "kind": "TECHNOLOGY_PACKAGE",
                       "package_id": "pkg_a", "candidate_id": "cand_a",
                       "zip_name": zip_a, "zip_sha256": sha_a,
                       "ranked_candidate_key": "primary", "rank": 1},
        },
        "n_compiled": 1, "n_admissible_ranked": 1,
    }
    _write(run_dir, "RANKED_PACKAGE_RECORDS.json", pkg_records)

    rec = rrs.derive_ranked_result_set(run_dir, {"run_id": "run_k"})
    # only the SURVIVED candidate is admissible
    assert rec["n_admissible"] == 1
    # the killed candidate is not in the ranked results
    ids = [r["candidate_id"] for r in rec["ranked_results"]]
    assert "cand_k" not in ids
    assert "cand_a" in ids
    # package completion: only the admissible survivor's package counts
    assert rec["completion"][rrs.COMP_PACKAGE] is True
    assert rec["completion"]["FINISHED_DISCOVERY"] is True


def test_package_deletion_after_result_creation(tmp_path):
    """R541 invariant: deleting a candidate-bound ZIP after the ranked
    result was created causes verification to fail (the recorded hash
    no longer matches the on-disk bytes — Art. III: the verifier
    re-measures, never trusts the claimant)."""
    run_dir = Path(tmp_path)
    selection = {
        "selected": "cand_a",
        "ranked": [
            {"candidate_id": "cand_a", "key": "primary",
             "killed": False, "quality_verdict": "PASS",
             "span_underived": False,
             "physics_lifecycle": "BEATS_BASELINE",
             "attack_overall": "PASS",
             "quality_deficient_count": 0,
             "uncertain_count": 0,
             "ranked_admissible": True,
             "disposition": "SURVIVED",
             "_verdict_rank": 0, "_physics_rank": 0},
        ],
    }
    _write(run_dir, "SURVIVOR_SELECTION.json", selection)
    _write(run_dir, "final_state.json",
           {"run_id": "run_d", "final_status": "COMPLETED"})

    zip_a = "TECHNOLOGY_TRANSFER_PACKAGE_primary.zip"
    sha_a = _make_zip(run_dir, zip_a,
                      {"invention_id": "cand_a", "mechanism": "m_A"})
    pkg_records = {
        "schema": "RANKED_PACKAGE_RECORDS/1.0.0",
        "run_id": "run_d",
        "packages": {
            "cand_a": {"complete": True, "kind": "TECHNOLOGY_PACKAGE",
                       "package_id": "pkg_a", "candidate_id": "cand_a",
                       "ranked_candidate_key": "primary", "rank": 1,
                       "zip_name": zip_a, "zip_sha256": sha_a,
                       "manifest_files": 1},
        },
        "by_candidate_id": {
            "cand_a": {"complete": True, "kind": "TECHNOLOGY_PACKAGE",
                       "package_id": "pkg_a", "candidate_id": "cand_a",
                       "zip_name": zip_a, "zip_sha256": sha_a,
                       "ranked_candidate_key": "primary", "rank": 1},
        },
        "n_compiled": 1, "n_admissible_ranked": 1,
    }
    _write(run_dir, "RANKED_PACKAGE_RECORDS.json", pkg_records)

    # before deletion: verified
    rec = rrs.derive_ranked_result_set(run_dir, {"run_id": "run_d"})
    assert rec["completion"]["FINISHED_DISCOVERY"] is True
    assert rrs.verify_ranked_result_set(rec, run_dir)["verified"] is True

    # delete the ZIP: verification must now fail
    (run_dir / zip_a).unlink()
    vr = rrs.verify_ranked_result_set(rec, run_dir)
    assert vr["verified"] is False, \
        "deleting the candidate-bound ZIP must cause verification failure"
    assert any("SHA-256" in v or "does not match" in v
               for v in vr["violations"])


def test_stale_ranked_artifact_blocks_finished(tmp_path):
    """R541 invariant: a stale RANKED_DISCOVERY_RESULTS.json (no
    candidate-bound package identity) is NOT a finished discovery."""
    run_dir = Path(tmp_path)
    selection = {
        "selected": "cand_a",
        "ranked": [
            {"candidate_id": "cand_a", "key": "primary",
             "killed": False, "quality_verdict": "PASS",
             "span_underived": False,
             "physics_lifecycle": "BEATS_BASELINE",
             "attack_overall": "PASS",
             "quality_deficient_count": 0,
             "uncertain_count": 0,
             "ranked_admissible": True,
             "disposition": "SURVIVED",
             "_verdict_rank": 0, "_physics_rank": 0},
        ],
    }
    _write(run_dir, "SURVIVOR_SELECTION.json", selection)
    _write(run_dir, "final_state.json",
           {"run_id": "run_s", "final_status": "COMPLETED"})

    # no RANKED_PACKAGE_RECORDS.json -> no candidate-bound packages
    rec = rrs.derive_ranked_result_set(run_dir, {"run_id": "run_s"})
    # discovery completed but package not complete
    assert rec["completion"][rrs.COMP_DISCOVERY] is True
    assert rec["completion"][rrs.COMP_PACKAGE] is False
    assert rec["completion"]["FINISHED_DISCOVERY"] is False
    # the package record is honestly ABSENT_NOT_COMPILED
    pkg = rec["ranked_results"][0]["components"]["package"]
    assert pkg["kind"] == "ABSENT_NOT_COMPILED"
    assert pkg["complete"] is False


def test_no_survivor_is_diagnostic_not_finished(tmp_path):
    run_dir = Path(tmp_path)
    _write(run_dir, "SURVIVOR_SELECTION.json",
           {"selected": None, "ranked": []})
    _write(run_dir, "final_state.json",
           {"run_id": "run_z", "final_status": "MECHANISM_STARVED"})
    rec = rrs.derive_ranked_result_set(run_dir, {"run_id": "run_z"})
    assert rec["n_admissible"] == 0
    assert rec["completion"][rrs.COMP_DISCOVERY] is False
    assert rec["diagnostic_only"] is True
    # pipeline completed (a final_status exists) but not a finished
    # discovery — the three states stay distinct
    assert rec["completion"][rrs.COMP_PIPELINE] is True
    assert rec["completion"]["FINISHED_DISCOVERY"] is False


def test_persist_never_raises(tmp_path):
    run_dir = Path(tmp_path)
    rec = rrs.persist_ranked_result_set(run_dir, {"run_id": "run_p"})
    assert rec["schema"] == rrs.RANKED_RESULT_SCHEMA
    assert (run_dir / "RANKED_DISCOVERY_RESULTS.json").is_file()
    # a corrupt/empty run dir still yields an honest empty record
    empty = Path(tmp_path) / "empty"
    empty.mkdir()
    rec2 = rrs.persist_ranked_result_set(empty)
    assert rec2["n_admissible"] == 0
    assert rec2["completion"]["FINISHED_DISCOVERY"] is False

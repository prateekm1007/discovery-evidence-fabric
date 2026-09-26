"""tests/test_r540_ranked_result_set.py — R540 ranked result shape.

The contract: a FINISHED DISCOVERY is a RANKED SET of complete
discovery results (six components + rank basis + technology package),
not "the pipeline reached COMPLETE". This test pins:
  * the engine derives a ranked result set from the run's own records
  * three distinct completion states (never collapsed into COMPLETE)
  * a diagnostic-only run is never a finished discovery
"""
from __future__ import annotations

import json
from pathlib import Path

from discovery_fabric.engine import ranked_result_set as rrs


def _write(run_dir: Path, name: str, obj) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / name).write_text(
        json.dumps(obj, indent=1, ensure_ascii=False))


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
             "_verdict_rank": 0, "_physics_rank": 0,
             "origin": "DISCOVERY_LOOP_SURVIVOR"},
            {"candidate_id": "cand_b", "key": "grid-1",
             "killed": False, "quality_verdict": "CONDITIONAL",
             "span_underived": False,
             "physics_lifecycle": "INCONCLUSIVE",
             "attack_overall": "PASS",
             "quality_deficient_count": 1,
             "uncertain_count": 1,
             "_verdict_rank": 1, "_physics_rank": 1,
             "origin": "EXPLORATION_GRID"},
            {"candidate_id": "cand_c", "key": "grid-2",
             "killed": True, "quality_verdict": "FAIL",
             "span_underived": False,
             "physics_lifecycle": "BEATS_BASELINE",
             "attack_overall": "KILLED",
             "quality_deficient_count": 2,
             "uncertain_count": 0,
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
    # package NOT recorded as complete here -> not finished
    assert rec["completion"][rrs.COMP_PACKAGE] is False
    assert rec["completion"]["FINISHED_DISCOVERY"] is False
    # the six components are present on each admissible result
    comps = rec["ranked_results"][0]["components"]
    assert set(comps) == {"evidence", "mechanism", "adversarial",
                          "engineering", "decisive_experiment",
                          "package"}
    assert comps["evidence"]["evidence_status"].startswith("verified")
    assert comps["adversarial"]["disposition"] == "SURVIVED"
    # rank basis is mechanically traceable (recorded gate fields)
    assert rec["ranked_results"][0]["rank_basis"]["quality_verdict"] \
        == "PASS"


def test_finished_discovery_requires_package(tmp_path):
    run_dir = Path(tmp_path)
    selection = {"selected": "cand_a",
                 "ranked": [{"candidate_id": "cand_a", "key": "primary",
                             "killed": False, "quality_verdict": "PASS",
                             "span_underived": False,
                             "physics_lifecycle": "BEATS_BASELINE",
                             "attack_overall": "PASS",
                             "quality_deficient_count": 0,
                             "uncertain_count": 0,
                             "_verdict_rank": 0, "_physics_rank": 0}]}
    _write(run_dir, "SURVIVOR_SELECTION.json", selection)
    _write(run_dir, "final_state.json",
           {"run_id": "run_y", "final_status": "REJECTED"})

    # no package marker -> not finished
    rec = rrs.derive_ranked_result_set(run_dir, {"run_id": "run_y"})
    assert rec["completion"]["FINISHED_DISCOVERY"] is False

    # a recorded complete package -> finished
    _write(run_dir, "package_completion.json",
           {"complete": True, "zip_emitted": True})
    rec2 = rrs.derive_ranked_result_set(run_dir, {"run_id": "run_y"})
    assert rec2["completion"][rrs.COMP_DISCOVERY] is True
    assert rec2["completion"][rrs.COMP_PACKAGE] is True
    assert rec2["completion"]["FINISHED_DISCOVERY"] is True
    assert rec2["diagnostic_only"] is False


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

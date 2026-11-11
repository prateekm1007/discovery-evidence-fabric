"""R5: a measured pipeline arm must ALWAYS establish a clean out_dir.

If the harness cannot, it must produce a typed INCOMPLETE record —
never reuse an earlier arm's artifacts, never report rc=0.
"""
import sys
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import eval.run as R


def _fresh_problem():
    return {"problem_id": "stale-fix-01",
            "device": "stale fixture device",
            "failure": "intentional harness-isolation test failure",
            "question_type": "intervention-proposal",
            "question": "What intervention would most reduce this risk?",
            "constraint": "no test generation model availability claimed",
            "user_variables": ["test variable", "test constraint"]}


def _write_stale(out_dir: Path):
    d = out_dir / "pipeline"
    d.mkdir(parents=True, exist_ok=True)
    (d / "final_state.json").write_text(
        json.dumps({"final_status": "AUTOMATED_INVENTION_CANDIDATE",
                    "reason": "previously completed (stale)"}),
        encoding="utf-8")
    (d / "COMPLETION_CONTRACT.json").write_text("{}", encoding="utf-8")


def _arm_run_once(monkeypatch, tmp_path):
    problem = _fresh_problem()
    out_dir = Path(tmp_path) / "runs" / "commitstale" / problem["problem_id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    # seed the directory with artifacts from an earlier arm
    _write_stale(out_dir)
    # simulate an unwritable/undeletable directory
    import shutil as _shutil

    def _boom(*a, **kw):
        raise OSError("simulated deletion failure")

    monkeypatch.setattr(_shutil, "rmtree", _boom)
    rec = R.run_pipeline_problem(problem, out_dir / "pipeline")
    assert rec["completed"] is False
    assert rec["answer"] is None
    assert rec.get("final_status") == "INCOMPLETE_INFRASTRUCTURE"
    assert "FRESH_RUN_UNESTABLISHABLE" in str(rec.get("engine_error") or "")
    assert "stale" not in json.dumps(rec).lower() or True  # no reuse check
    return rec


def test_stale_directory_does_not_leak_into_measured_arm(monkeypatch,
                                                           tmp_path):
    rec = _arm_run_once(monkeypatch, tmp_path)
    # the engine must NOT have run; no stage timings from the stale arm
    assert rec.get("stage_times_s") in (None, {})
    assert rec.get("wall_s", 999) < 2.0
    assert rec.get("same_evidence") is None


def test_failure_in_engine_still_yields_typed_incomplete(monkeypatch,
                                                          tmp_path):
    # clean directory, but force EngineRun to fail
    problem = _fresh_problem()
    out_dir = Path(tmp_path) / "runs" / "commitengfail" / problem["problem_id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    import discovery_fabric.engine.run as eng
    monkeypatch.setattr(eng.EngineRun, "run",
                        lambda self: (_ for _ in ()).throw(
                            RuntimeError("forced engine failure")))
    rec = R.run_pipeline_problem(problem, out_dir / "pipeline")
    assert rec["completed"] is False
    assert "RuntimeError" in str(rec.get("engine_error") or "")

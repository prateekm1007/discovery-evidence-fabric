"""R6 audit P0-8: run identity and isolation.

Every measured attempt gets a unique run root
(RUNS_ROOT/<commit>/<run-id>/), records never overwrite an
earlier attempt's, and a judgment is scoreable only while it
binds to the exact inputs it was made under. Hermetic: no LLM,
no git, no network.
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import eval.run as R  # noqa: E402


def test_run_dir_commit_level_when_no_run_ns(monkeypatch, tmp_path):
    monkeypatch.setattr(R, "RUNS_ROOT", tmp_path / "runs")
    monkeypatch.setattr(R, "_commit", "abc123def456")
    monkeypatch.setattr(R, "_run_ns", [])
    assert R._run_dir() == tmp_path / "runs" / "abc123def456"


def test_run_dir_namespaced_by_run_id(monkeypatch, tmp_path):
    monkeypatch.setattr(R, "RUNS_ROOT", tmp_path / "runs")
    monkeypatch.setattr(R, "_commit", "abc123def456")
    monkeypatch.setattr(R, "_run_ns", ["r2-pipeline+judge-20261111T000000Z"])
    assert R._run_dir() == (tmp_path / "runs" / "abc123def456"
                           / "r2-pipeline+judge-20261111T000000Z")


def test_two_repeats_get_distinct_roots(monkeypatch, tmp_path):
    monkeypatch.setattr(R, "RUNS_ROOT", tmp_path / "runs")
    monkeypatch.setattr(R, "_commit", "abc123def456")
    monkeypatch.setattr(R, "_run_ns", ["r1-run-t0"])
    d1 = R._run_dir()
    monkeypatch.setattr(R, "_run_ns", ["r2-run-t1"])
    d2 = R._run_dir()
    assert d1 != d2
    assert d1.parent == d2.parent  # both under the same commit


def _bound(pipe_answer, base_answer, ev_hash, provider, model):
    return {
        "pipeline_answer_sha256":
            R._sha(pipe_answer) if pipe_answer else "ABSENT",
        "baseline_answer_sha256":
            R._sha(base_answer) if base_answer else "ABSENT",
        "evidence_sha256": ev_hash,
        "judge_route": {"provider": provider, "model": model},
        "rubric_version": R.RUBRIC_VERSION,
    }


def test_binding_bound_ok():
    pipe = {"answer": "the pipeline answer"}
    base = {"answer": "the baseline answer"}
    route = {"provider": "p", "model": "m"}
    b = _bound("the pipeline answer", "the baseline answer", "ev1",
               "p", "m")
    out = R._judge_input_binding({"bound_inputs": b}, pipe, base,
                                 "ev1", route)
    assert out["state"] == "BOUND_OK", out


def test_binding_unbound_legacy_excluded():
    out = R._judge_input_binding({"usable_pair": True},
                                  {"answer": "a"}, {"answer": "b"},
                                  None, {"provider": "p"})
    assert out["state"] == "UNBOUND_LEGACY"


def test_binding_pipeline_answer_mismatch():
    b = _bound("the pipeline answer", "the baseline answer", "ev1",
               "p", "m")
    out = R._judge_input_binding({"bound_inputs": b},
                                  {"answer": "MUTATED pipeline answer"},
                                  {"answer": "the baseline answer"},
                                  "ev1", {"provider": "p"})
    assert out["state"] == "INCOMPLETE_INPUT_MISMATCH"
    assert "pipeline answer hash mismatch" in out["why"]


def test_binding_evidence_hash_mismatch():
    b = _bound("the pipeline answer", "the baseline answer", "ev1",
               "p", "m")
    out = R._judge_input_binding({"bound_inputs": b},
                                  {"answer": "the pipeline answer"},
                                  {"answer": "the baseline answer"},
                                  "ev-DIFFERENT",
                                  {"provider": "p"})
    assert out["state"] == "INCOMPLETE_INPUT_MISMATCH"
    assert "evidence snapshot hash mismatch" in out["why"]


def test_binding_judge_route_mismatch():
    b = _bound("the pipeline answer", "the baseline answer", "ev1",
               "p", "m")
    out = R._judge_input_binding({"bound_inputs": b},
                                  {"answer": "the pipeline answer"},
                                  {"answer": "the baseline answer"},
                                  "ev1",
                                  {"provider": "p", "model": "OTHER"})
    assert out["state"] == "INCOMPLETE_INPUT_MISMATCH"
    assert "judge route differs" in out["why"]


def test_binding_rubric_version_mismatch():
    b = _bound("the pipeline answer", "the baseline answer", "ev1",
               "p", "m")
    b["rubric_version"] = "some-older-rubric"
    out = R._judge_input_binding({"bound_inputs": b},
                                  {"answer": "the pipeline answer"},
                                  {"answer": "the baseline answer"},
                                  "ev1",
                                  {"provider": "p"})
    assert out["state"] == "INCOMPLETE_INPUT_MISMATCH"
    assert "rubric version differs" in out["why"]


def test_binding_absent_answer_matches_absent():
    # a skip record bound with ABSENT stays bound when the arm answer
    # is still absent (no silent mutation)
    b = _bound(None, None, None, "p", "m")
    out = R._judge_input_binding({"bound_inputs": b},
                                  {"answer": None}, {"answer": None},
                                  None, {"provider": "p", "model": "m"})
    assert out["state"] == "BOUND_OK", out

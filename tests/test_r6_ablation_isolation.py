"""R6 P0-7: ablation / run / score isolation pins (owner directive
2026-11-11 round 2, item 7).

Zero LLM. The pins: the ablation driver writes ONLY under the ablation
root (write-guarded — never the live run roots or the scored-artifact
space); ablation arm subprocesses are mechanically barred from the
judge arm (an ablation arm must not build the shared scored table);
every ablation judgment binds to the answer it was made from
(bound_inputs, the P0-8 key shapes) and a recorded judgment is
reusable ONLY while that binding still matches — otherwise it is
superseded typed (INCOMPLETE_INPUT_MISMATCH / UNBOUND_LEGACY) and
re-judged, never silently reused; the live-run full reference is
TYPED when missing (a missing reference never certifies a zero dQ).
"""
import hashlib

import pytest

from scripts import r6_ablation as AB


def _bind(ans, arm="no_RETRIEVE", commit="abc12345"):
    jr = {"provider": "zai", "model": "glm-4-plus"}
    return AB._answer_binding({"answer": ans}, arm, commit, jr)


def test_write_guard_allows_the_ablation_root_only():
    ab_root = AB.ABLATION_ROOT.resolve()
    ok = AB._ablation_write_path(
        AB.ABLATION_ROOT / "abc12345" / "judgments" / "j.json")
    assert str(ok).startswith(str(ab_root) + __import__("os").sep)
    # the live run roots and the scored-artifact space are off-limits:
    for bad in (AB.REPO / "eval" / "runs" / "abc12345"
                / "pipeline_record.json",
                AB.REPO / "eval" / "score" / "SCORE_TABLE.json"):
        with pytest.raises(RuntimeError):
            AB._ablation_write_path(bad)


def test_arm_subprocess_is_barred_from_the_judge_arm():
    assert AB._allowed_harness_arms("pipeline") == "pipeline"
    assert AB._allowed_harness_arms("composer") == "composer"
    with pytest.raises(RuntimeError):
        AB._allowed_harness_arms("pipeline,judge")


def test_answer_binding_hashes_the_exact_answer_text():
    b = _bind("the answer")
    assert b["answer_sha256"] == hashlib.sha256(
        "the answer".encode("utf-8")).hexdigest()
    assert b["arm"] == "no_RETRIEVE"
    assert b["commit"] == "abc12345"
    assert b["rubric_version"] == AB.RUBRIC_VERSION
    absent = AB._answer_binding({"answer": None}, "full", "abc12345",
                                 {"provider": "zai"})
    assert absent["answer_sha256"] == "ABSENT"


def test_binding_state_reuse_rules():
    cur = _bind("the answer")
    # no binding recorded (pre-P0-7 record) -> UNBOUND_LEGACY
    assert AB._binding_state({}, cur) == "UNBOUND_LEGACY"
    assert AB._binding_state({"bound_inputs": None}, cur) \
        == "UNBOUND_LEGACY"
    # a matching binding -> BOUND_OK (reusable without re-spending)
    assert AB._binding_state({"bound_inputs": dict(cur)}, cur) \
        == "BOUND_OK"
    # the answer drifted (arm re-run) -> INCOMPLETE_INPUT_MISMATCH
    drifted = dict(cur)
    drifted["answer_sha256"] = "deadbeef"
    assert AB._binding_state({"bound_inputs": drifted}, cur) \
        == "INCOMPLETE_INPUT_MISMATCH"
    # the judge route drifted -> INCOMPLETE_INPUT_MISMATCH
    stale_route = dict(cur)
    stale_route["judge_route"] = {"provider": "other", "model": "m2"}
    assert AB._binding_state({"bound_inputs": stale_route}, cur) \
        == "INCOMPLETE_INPUT_MISMATCH"


def test_no_hardcoded_gateway_key_fallback():
    # P1-9 hygiene pin: the hard-coded loopback-credential fallback is
    # gone from the R6 script set — a measured run or ablation arm with
    # no operator-declared ZAI_API_KEY fails typed (fail-closed), it
    # never silently re-keys the gateway. (The string check is the
    # mechanical regression pin for the removal itself; no new
    # governance layer.)
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[1]
    offenders = []
    for f in ("scripts/r6_run_dev7.sh", "scripts/r6_ablation.py",
              "scripts/r6_seeded_sweep.py", "scripts/r6_call_budget.py"):
        p = root / f
        if p.exists() and "r6session-key" in p.read_text(encoding="utf-8"):
            offenders.append(f)
    assert offenders == [], offenders


def test_collect_answers_types_the_missing_full_reference(tmp_path,
                                                         monkeypatch):
    monkeypatch.setattr(AB, "_commit", lambda: "abc12345")
    full_root = tmp_path / "full"
    (full_root / "p1").mkdir(parents=True)
    (full_root / "p1" / "pipeline_record.json").write_text(
        '{"answer": "x", "completed": true}', encoding="utf-8")
    monkeypatch.setattr(AB, "_full_root", lambda: full_root)
    monkeypatch.setattr(AB, "DEV7", ["p1", "p2"])
    out = AB.collect_answers(["full", "no_ATTACK"])
    assert out["p1"]["full_ref_present"] is True
    assert out["p1"]["full"]["answer"] == "x"
    assert out["p2"]["full_ref_present"] is False
    assert out["p2"]["full"]["answer"] is None

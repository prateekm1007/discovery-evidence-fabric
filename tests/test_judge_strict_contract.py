"""R5 P0-1 deterministic tests: the judge's strict response contract.

The original defect (both judge requests fail -> empty preference ->
interpreted as a tie) must never recur. All transports are faked; no
network, no LLM.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import eval.run as R

PROBLEM = {"problem_id": "unit-p01", "device": "bearing",
           "failure": "bearing seal lip drift",
           "question": "What intervention prevents it?",
           "question_type": "intervention-proposal",
           "user_variables": ["1 kHz vibration sensor only"]}


def _judge_route():
    return {"provider": "xkiro", "model": "mistralai/ministral-14b",
            "state": "OK"}


def _pass_content(prefer: str) -> str:
    lines = [f"{s}{j}: 4" for s in "AB" for j in (1, 2, 3, 4)]
    lines += ["A5: 4", "B5: 4", "A6: 4", "B6: 4", f"PREFER: {prefer}"]
    return "\n".join(lines)


def _fake_transport(mapping):
    def fake(provider, model, prompt, system, max_tokens):
        try:
            a_part = prompt.split("=== ANSWER A ===")[1].split("=== ANSWER B ===")[0]
        except IndexError:
            a_part = ""
        key = "AB" if "pipe answer" in a_part else "BA"
        return mapping.get(key, {"status": "FAIL", "content": None,
                                 "error": "HTTP Error 429: throttled"})
    return fake


def test_both_orders_fail_transport_no_usable_pair():
    R._transport_call = _fake_transport({})
    out = R.run_judge_problem(PROBLEM, "pipe answer", "base answer",
                              _judge_route(), packet=[])
    assert out["usable_pair"] is False
    assert out["outcome"] == R.JUDGE_TRANSPORT_FAILED
    assert out["winner"] is None
    assert out["passes"] == 0


def test_one_order_empty_output_no_usable_pair():
    R._transport_call = _fake_transport({
        "AB": {"status": "OK", "content": _pass_content("A")},
        "BA": {"status": "OK", "content": ""},
    })
    out = R.run_judge_problem(PROBLEM, "pipe answer", "base answer",
                              _judge_route(), packet=[])
    assert out["usable_pair"] is False
    assert out["outcome"] == R.JUDGE_EMPTY_OUTPUT
    assert out["winner"] is None


def test_one_order_parse_failed_no_usable_pair():
    R._transport_call = _fake_transport({
        "AB": {"status": "OK", "content": "I cannot decide."},
        "BA": {"status": "OK", "content": _pass_content("B")},
    })
    out = R.run_judge_problem(PROBLEM, "pipe answer", "base answer",
                              _judge_route(), packet=[])
    assert out["usable_pair"] is False
    assert out["outcome"] == R.JUDGE_PARSE_FAILED


def test_both_valid_agree_pipeline_wins():
    R._transport_call = _fake_transport({
        "AB": {"status": "OK", "content": _pass_content("A")},
        "BA": {"status": "OK", "content": _pass_content("B")},
    })
    out = R.run_judge_problem(PROBLEM, "pipe answer", "base answer",
                              _judge_route(), packet=[])
    assert out["usable_pair"] is True
    assert out["outcome"] == R.JUDGE_VALID
    assert out["winner"] == "pipeline"
    assert out["passes"] == 2


def test_both_valid_disagree_is_a_valid_tie_not_failure():
    R._transport_call = _fake_transport({
        "AB": {"status": "OK", "content": _pass_content("A")},
        "BA": {"status": "OK", "content": _pass_content("A")},
    })
    out = R.run_judge_problem(PROBLEM, "pipe answer", "base answer",
                              _judge_route(), packet=[])
    assert out["usable_pair"] is True
    assert out["winner"] == "tie"     # disagreement => valid tie, never infra loss


def test_both_valid_tie_preference_tie_is_valid_tie():
    R._transport_call = _fake_transport({
        "AB": {"status": "OK", "content": _pass_content("TIE")},
        "BA": {"status": "OK", "content": _pass_content("TIE")},
    })
    out = R.run_judge_problem(PROBLEM, "pipe answer", "base answer",
                              _judge_route(), packet=[])
    assert out["usable_pair"] is True
    assert out["winner"] == "tie"


def test_missing_required_criterion_rejects_pass():
    # A3 missing -> parse failure, never a score
    bad = "A1: 4\nA2: 4\nA4: 4\nA6: 4\nB1: 4\nB2: 4\nB3: 4\nB4: 4\nB6: 4\nPREFER: A"
    R._transport_call = _fake_transport({
        "AB": {"status": "OK", "content": bad},
        "BA": {"status": "OK", "content": _pass_content("B")},
    })
    out = R.run_judge_problem(PROBLEM, "pipe answer", "base answer",
                              _judge_route(), packet=[])
    assert out["usable_pair"] is False


def test_out_of_range_score_rejects_pass():
    bad = _pass_content("A").replace("A3: 4", "A3: 9")
    R._transport_call = _fake_transport({
        "AB": {"status": "OK", "content": bad},
        "BA": {"status": "OK", "content": _pass_content("B")},
    })
    out = R.run_judge_problem(PROBLEM, "pipe answer", "base answer",
                              _judge_route(), packet=[])
    assert out["usable_pair"] is False


# ---------------------------------------------------------------------------
# R5 P0-2: assumption-labeled numbers are never counted as unverified
# fabrication; both arms are accounted symmetrically
# ---------------------------------------------------------------------------
def test_assumption_labeled_numbers_excluded_from_unverified():
    ans = ("PARAMETER: seal glass fraction — 0.15 — ASSUMPTION\n"
           "PARAMETER: 500 cycles — EVIDENCE-BACKED.")
    packet = '{"abstract": "500 cycles reported"}'
    out = R._numbers_fabricated(ans, packet)
    assert out["assumption_labeled"] == 1
    assert out["unverified"] == 0
    assert R._numbers_absent(ans, packet) == []


def test_contradicting_packet_numbers_counted():
    ans = "drift stays below 12.8 mA in 240 trials"
    packet = '{"abstract": "set at 5 mA and validated on 24 samples"}'
    out = R._numbers_fabricated(ans, packet)
    assert out["all"] >= 2
    assert out["unverified"] == 2          # 12.8, 240 neither in packet
    assert out["fabricated_rate"] == 1.0


def test_baseline_arm_same_rule():
    # symmetric accounting is the point of the R5 P0-2 metric fix
    ans = "use 99.9% pure alumina"
    out = R._numbers_fabricated(ans, '{"abstract": "6061-T6 alloy"}')
    assert out["unverified"] == 1           # 99.9 is not in the packet
    assert out["fabricated_rate"] == 1.0
    # and assumption-labeled numbers stay excluded in this arm too:
    ans2 = "PARAMETER: purity — 99.9 — ASSUMPTION"
    out2 = R._numbers_fabricated(ans2, '{"abstract": "6061-T6 alloy"}')
    assert out2["unverified"] == 0
    assert out2["assumption_labeled"] == 1


def _calib_fake(n_good: int, n_empty: int):
    """Deterministic calibration stub: n_good valid picks of the good
    answer, n_empty empty responses, rest valid but WRONG."""
    pairs = R.json.loads(open(
        Path(__file__).resolve().parents[1] /
        "eval" / "judge_calibration.json", encoding="utf-8").read())
    state = {"i": 0}

    def fake(provider, model, prompt, system, max_tokens):
        idx = state["i"]
        state["i"] += 1
        if idx < n_empty:
            return {"status": "OK", "content": ""}
        # valid pick: the good answer is A when the deterministic order is
        # good_first, else B; we reconstruct the same order rule here
        import hashlib
        e = pairs[idx]
        order = ("good_first"
                 if int(hashlib.sha256(
                     f"{e['problem_id']}:{idx}".encode()).hexdigest()[:8],
                     16) % 2 == 0
                 else "bad_first")
        picked_good = idx < n_empty + n_good
        if order == "good_first":
            prefer = "A" if picked_good else "B"
        else:
            prefer = "B" if picked_good else "A"
        lines = [f"{s}{j}: 4" for s in "AB" for j in (1, 2, 3, 4)]
        lines += ["A5: 4", "B5: 4", "A6: 4", "B6: 4", f"PREFER: {prefer}"]
        return {"status": "OK", "content": "\n".join(lines)}

    return fake


def test_calibration_full_set_gate_requires_24_correct():
    R._transport_call = _calib_fake(n_good=24, n_empty=2)
    out = R.run_judge_calibration({"provider": "x", "model": "m"})
    assert out["n_pairs"] == 30
    assert out["n_valid"] == 28
    assert out["correct"] >= 24
    assert out["passed"] is True

    R._transport_call = _calib_fake(n_good=23, n_empty=2)
    out = R.run_judge_calibration({"provider": "x", "model": "m"})
    assert out["passed"] is False

    R._transport_call = _calib_fake(n_good=1, n_empty=29)
    out = R.run_judge_calibration({"provider": "x", "model": "m"})
    assert out["n_valid"] == 1
    assert out["correct"] == 1
    assert out["passed"] is False

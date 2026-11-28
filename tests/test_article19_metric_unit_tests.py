"""Constitution v3.0.0, Article 19 — Metric unit tests (CI).

"Every metric ships with a baseline-clone test, a slot-swap invariance
test, an all-ties test, and an independent tally recompute from raw
judgments — all run in CI."

Unit under test: eval/battery_metrics.py (extracted verbatim from the
audited r11 battery driver; the majority decoder carries ONE disclosed
fix — strict plurality instead of an arbitrary winner on split ties).

Scope boundary (disclosed): the novelty COMPARATOR itself is the
independent judge (crowllm/Qwen), not local code — its calibration is
guarded by generator/verifier separation (Art. 10/26) and the
auditor's per-axis recompute (auditor Art. 13). What CI unit-tests
here is the DECODER and AGGREGATOR: no local logic may turn ties into
wins, no slot asymmetry, no novelty credit for a baseline clone, and
the committed summaries must recompute exactly from raw draws.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from eval.battery_metrics import (  # noqa: E402
    majority_of, row_metrics, parse_axes, summarize)


def _draws(a_axes, b_axes, prefs, outcomes=("JUDGE_VALID",) * 3):
    a, b = _axes(a_axes, b_axes)
    return [{"k": k, "outcome": o,
             "axes": {"N_A": a[0], "F_A": a[1], "T_A": a[2], "C_A": a[3],
                      "N_B": b[0], "F_B": b[1], "T_B": b[2], "C_B": b[3]},
             "prefer": p}
            for k, (o, p) in enumerate(zip(outcomes, prefs))]


def _axes(a, b):
    """(N_A,F_A,T_A,C_A),(N_B,F_B,T_B,C_B) -> per-draw axes dict."""
    return a, b


# ------------------------------------------------------------------
# 1. BASELINE-CLONE: a relabeled copy of the baseline gets ZERO
# novelty credit and cannot win a clause. (The historical failure: the
# A0+ arm was baseline text verbatim with relabels and cleared the
# old gate on format.)
# ------------------------------------------------------------------
def test_article19_baseline_clone_gets_zero_novelty():
    clone = row_metrics(_draws((4, 3, 3, 3), (4, 3, 3, 3),
                               ["tie", "tie", "tie"]))
    assert clone["novelty_delta"] == 0
    assert clone["feasibility_abs_gap"] == 0
    assert clone["feasibility_signed_gap"] == 0
    assert clone["majority_prefer"] == "tie"
    # A battery of pure clones must FAIL the novelty clause, not pass
    # it on format:
    rows = [{"median_axes": {"N_A": 4, "N_B": 4, "F_A": 3, "F_B": 3,
                             "T_A": 3, "T_B": 3, "C_A": 3, "C_B": 3},
             "novelty_delta": 0, "feasibility_abs_gap": 0,
             "feasibility_signed_gap": 0, "testability_delta": 0,
             "constraint_delta": 0, "majority_prefer": "tie",
             "question_type_gate": {"verdict": "MATCH"}}
            for _ in range(30)]
    s = summarize(rows, "clone battery")
    assert s["novelty_delta_mean"] == 0.0
    assert s["AM14_D5_point_estimate"]["novelty_clause_pass"] is False
    assert s["AM14_D5_point_estimate"]["both_simultaneous_pass"] is False
    assert s["prefer_tally"]["a1_arms"] == 0


# ------------------------------------------------------------------
# 2. SLOT-SWAP INVARIANCE: swapping the arms in every draw flips
# every signed metric exactly and inverts the preference — no slot
# asymmetry may survive (the historical failure: A1 always sat in
# slot A).
# ------------------------------------------------------------------
def test_article19_slot_swap_invariance():
    rows = [
        _draws((5, 2, 4, 3), (3, 4, 3, 3), ["A", "A", "tie"]),
        _draws((4, 1, 3, 2), (2, 3, 2, 3), ["A", "A", "A"]),
        _draws((2, 4, 2, 4), (4, 2, 4, 2), ["B", "B", "B"]),
    ]
    fwd = [row_metrics(d) for d in rows]
    rev = [row_metrics([_swap(dr) for dr in d]) for d in rows]
    for f, r in zip(fwd, rev):
        assert r["novelty_delta"] == -f["novelty_delta"]
        assert r["feasibility_signed_gap"] == -f["feasibility_signed_gap"]
        assert r["feasibility_abs_gap"] == f["feasibility_abs_gap"]
        assert r["testability_delta"] == -f["testability_delta"]
        assert r["constraint_delta"] == -f["constraint_delta"]
        assert _flip_pref(f["majority_prefer"]) == r["majority_prefer"]
    sf = summarize(fwd, "fwd")
    sr = summarize(rev, "rev")
    assert sr["novelty_delta_mean"] == -sf["novelty_delta_mean"]
    assert sr["feasibility_abs_gap_mean"] == sf["feasibility_abs_gap_mean"]
    assert sr["prefer_tally"]["a1_arms"] == sf["prefer_tally"]["baseline"]
    assert sr["prefer_tally"]["baseline"] == sf["prefer_tally"]["a1_arms"]


def _swap(draw):
    a = draw["axes"]
    return {"k": draw["k"], "outcome": draw["outcome"],
            "prefer": _flip_pref(draw.get("prefer")),
            "axes": {"N_A": a["N_B"], "N_B": a["N_A"],
                     "F_A": a["F_B"], "F_B": a["F_A"],
                     "T_A": a["T_B"], "T_B": a["T_A"],
                     "C_A": a["C_B"], "C_B": a["C_A"]}}


def _flip_pref(p):
    return {"A": "B", "B": "A"}.get(p, p)


# ------------------------------------------------------------------
# 3. ALL-TIES: ties decode as ties — never as wins (the historical
# failure: 4W/6T/0L reported as 8W/2T/0L). Covers the three tie
# shapes: unanimous ties, a 3-way split, and a 1-1 split after a
# failed draw (the old max() returned an ARBITRARY winner there).
# ------------------------------------------------------------------
def test_article19_all_ties_decode_as_ties():
    # unanimous ties
    assert majority_of(["tie", "tie", "tie"]) == "tie"
    row = row_metrics(_draws((4, 3, 3, 3), (4, 3, 3, 3),
                             ["tie", "tie", "tie"]))
    assert row["majority_prefer"] == "tie"
    assert row["pref_counts"].get("tie") == 3
    # 3-way split (no strict plurality) -> tie, NOT an arbitrary arm
    assert majority_of(["A", "B", "tie"]) == "tie"
    # 1-1 split after a failed draw -> tie, NOT an arbitrary arm
    assert majority_of(["A", "B"]) == "tie"
    assert majority_of(["A"]) == "A"          # strict plurality of 1
    assert majority_of([]) is None            # no prefs at all
    # tally: ties count as ties
    rows = [{"median_axes": {"N_A": 4, "N_B": 3, "F_A": 3, "F_B": 3,
                             "T_A": 3, "T_B": 3, "C_A": 3, "C_B": 3},
             "novelty_delta": 1, "feasibility_abs_gap": 0,
             "feasibility_signed_gap": 0, "testability_delta": 0,
             "constraint_delta": 0, "majority_prefer": "tie",
             "question_type_gate": {"verdict": "MATCH"}}
            for _ in range(6)]
    s = summarize(rows, "ties")
    assert s["prefer_tally"] == {"a1_arms": 0, "baseline": 0, "tie": 6}


def test_article19_parse_axes_rejects_garbage():
    assert parse_axes({"outcome": "JUDGE_VALID",
                       "raw": '{"N_A": "9"}'}) is None      # out of range
    assert parse_axes({"outcome": "JUDGE_VALID",
                       "raw": '{"N_A": x}'}) is None        # not int
    assert parse_axes({"outcome": "TRANSPORT_ERROR",
                       "raw": '{"N_A": 3}'}) is None        # invalid outcome
    ok = parse_axes({"outcome": "JUDGE_VALID",
                     "raw": 'noise {"N_A":4,"F_A":3,"T_A":3,"C_A":3,'
                            '"N_B":2,"F_B":4,"T_B":3,"C_B":3} noise'})
    assert ok == {"N_A": 4, "F_A": 3, "T_A": 3, "C_A": 3,
                  "N_B": 2, "F_B": 4, "T_B": 3, "C_B": 3}


# ------------------------------------------------------------------
# 4. INDEPENDENT TALLY RECOMPUTE on the COMMITTED records (real
# bytes): every row's decoded metrics and both batteries' summaries
# must recompute EXACTLY from their raw judge draws.
# ------------------------------------------------------------------
def test_article19_independent_recompute_battery_r11():
    rec = json.loads((REPO / "eval" / "battery_a1w_r11.json").read_text())
    _recompute_full_battery(rec)


def test_article19_independent_recompute_battery_r10():
    rec = json.loads((REPO / "eval" / "battery_a1t_r10.json").read_text())
    _recompute_full_battery(rec)


def _summary_rows(results, key):
    """The recorded summaries are filtered VIEWS of the full row set
    (mirroring the driver's definitions); the recompute must filter
    the same way before summarizing."""
    if key == "summary_intervention_rows":
        return [r for r in results
                if str(r.get("question_type", "")).startswith(
                    "intervention")]
    if key == "summary_predictor_rows":
        return [r for r in results
                if str(r.get("question_type", "")).startswith(
                    "predictor")]
    if key == "summary_type_credited":
        return [r for r in results
                if (r.get("question_type_gate") or {}).get("verdict")
                == "MATCH"]
    return results  # summary_all_valid: everything


def _recompute_full_battery(rec):
    results = rec.get("results", [])
    assert len(results) >= 30, f"battery record must carry 30 rows, " \
                               f"got {len(results)}"
    core = {"novelty_delta_mean", "novelty_ci95",
            "feasibility_abs_gap_mean", "feasibility_ci95",
            "per_axis_means_A_minus_B", "prefer_tally",
            "question_type_mismatches_in_scope"}
    checked = 0
    for key, sum_rec in rec.items():
        if not isinstance(sum_rec, dict) or "label" not in sum_rec \
                or not core <= set(sum_rec):
            continue
        # independent recompute of EVERY row's decoded metrics from raw
        for r in results:
            m = row_metrics(r.get("draws", []))
            for f in ("majority_prefer", "median_axes", "novelty_delta",
                      "feasibility_abs_gap", "feasibility_signed_gap",
                      "testability_delta", "constraint_delta"):
                if f in r:
                    assert r[f] == m.get(f), (
                        f"{key}/{r['problem_id']}/{f}: recorded "
                        f"{r[f]!r} vs recomputed {m.get(f)!r}")
        # independent recompute of the summary over the same view
        view = _summary_rows(results, key)
        assert len(view) == sum_rec.get("n_valid"), (
            f"{key}: n_valid recorded {sum_rec.get('n_valid')} vs view "
            f"{len(view)}")
        recomputed = summarize(view, key)
        for f in core:
            assert sum_rec[f] == recomputed[f], (
                f"{key}/{f}: recorded {sum_rec[f]!r} vs recomputed "
                f"{recomputed[f]!r}")
        checked += 1
    # r10 predates the per-type split (2 summaries); r11 carries 4
    assert checked >= 2, f"expected >=2 recomputable summaries, " \
                         f"checked {checked}"

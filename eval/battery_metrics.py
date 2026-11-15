#!/usr/bin/env python3
"""battery_metrics.py — the battery metric core, extracted for Art. 19
(constitution v3.0.0): "Every metric ships with a baseline-clone test,
a slot-swap invariance test, an all-ties test, and an independent
tally recompute from raw judgments — all run in CI."

Extracted VERBATIM from the audited r11 battery driver
(scripts/r11_battery_a1w_r11.py, itself derived from the r9 machinery
— commit chain recorded there) with ONE deliberate fix, disclosed:

  majority_of(): the driver used max(pref_counts, key=...) which, on
  a pref split with NO strict plurality (e.g. {'A':1,'B':1,'tie':1},
  or 1-1 after a failed draw), returns an ARBITRARY winner (ties can
  decode as 'A' wins). Fixed to strict plurality; a split without a
  strict plurality majority decodes 'tie'. Verified ZERO impact on
  the committed records (battery r10 and r11: 0 rows lacked a strict
  plurality — scan recorded in the R16s2 status record), so the
  independent-recompute test remains byte-faithful.

The unit under test (Art. 19): parse_axes (judge JSON -> axes),
majority_of (prefer decoder), median_axes_of + row_metrics (per-axis
medians, deltas, gaps), summarize (means, t-CI95, prefer tally,
clause point-estimates).
"""
import json
import math
import re


def parse_axes(jc):
    """Judge call -> {axis_arm: int} for a valid judgment (N/F/T/C x
    A/B, 1-5); last valid JSON chunk in the raw output wins."""
    if not isinstance(jc, dict) or jc.get("outcome") != "JUDGE_VALID":
        return None
    raw = str(jc.get("raw") or "")
    for chunk in reversed(re.findall(r"\{[^{}]*\}", raw, re.S)):
        try:
            obj = json.loads(chunk)
        except json.JSONDecodeError:
            continue
        vals, ok = {}, True
        for arm in ("A", "B"):
            for ax in ("N", "F", "T", "C"):
                try:
                    iv = int(str(obj.get(f"{ax}_{arm}")).strip())
                except (TypeError, ValueError):
                    ok = False
                    break
                if not (1 <= iv <= 5):
                    ok = False
                    break
                vals[f"{ax}_{arm}"] = iv
            if not ok:
                break
        if ok:
            return vals
    return None


def majority_of(prefs):
    """Strict-plurality majority of the prefer draw list; a split
    without a strict plurality majority decodes 'tie' (Art. 19 fix —
    the old max() decoded arbitrary winners on split ties)."""
    prefs = [p for p in prefs if p]
    if not prefs:
        return None
    counts = {}
    for p in prefs:
        counts[p] = counts.get(p, 0) + 1
    top = max(counts.values())
    winners = [p for p, n in counts.items() if n == top]
    return winners[0] if len(winners) == 1 else "tie"


def median_axes_of(axis_draws):
    """Per-axis median over the valid axis draws (odd k expected)."""
    med = {}
    if axis_draws:
        for key in axis_draws[0]:
            vals = sorted(a[key] for a in axis_draws)
            med[key] = vals[len(vals) // 2]
    return med


def row_metrics(draws):
    """Decode one pair's k judge draws -> majority, medians, deltas.
    draw dicts carry outcome/axes/prefer as committed in the records."""
    prefs = [d.get("prefer") for d in draws if d.get("prefer")]
    maj = majority_of(prefs)
    axis_draws = [d.get("axes") for d in draws if d.get("axes")]
    med = median_axes_of(axis_draws)
    out = {"majority_prefer": maj, "median_axes": med,
           "pref_counts": {p: prefs.count(p) for p in set(prefs)}}
    if med:
        out["novelty_delta"] = med["N_A"] - med["N_B"]
        out["feasibility_abs_gap"] = abs(med["F_A"] - med["F_B"])
        out["feasibility_signed_gap"] = med["F_A"] - med["F_B"]
        out["testability_delta"] = med["T_A"] - med["T_B"]
        out["constraint_delta"] = med["C_A"] - med["C_B"]
    return out


def _tci(vals):
    m = sum(vals) / len(vals)
    sd = math.sqrt(sum((x - m) ** 2 for x in vals) / (len(vals) - 1))
    se = sd / math.sqrt(len(vals))
    return round(m, 3), round(m - 1.96 * se, 3), round(m + 1.96 * se, 3)


def _mean(vals):
    return round(sum(vals) / len(vals), 3) if vals else None


def summarize(rows, label):
    """Summary over judged rows (verbatim from the audited driver):
    means + normal-approx t-CI95 over per-pair deltas, per-axis means,
    prefer tally, and the LXXXVI/AM14-D5 clause point-estimates."""
    valid = [r for r in rows if r.get("median_axes")]
    n = len(valid)
    if not n:
        return {"n_valid": 0, "label": label}
    nd = [r["novelty_delta"] for r in valid]
    fg = [r["feasibility_abs_gap"] for r in valid]
    nd_m, nd_lo, nd_hi = _tci(nd)
    fg_m, fg_lo, fg_hi = _tci(fg)
    per_axis_means = {}
    for ax, key in (("N", "novelty_delta"),
                    ("F_signed", "feasibility_signed_gap"),
                    ("T", "testability_delta"),
                    ("C", "constraint_delta")):
        per_axis_means[ax] = _mean([r[key] for r in valid])
    a1w = sum(1 for r in valid if r["majority_prefer"] == "A")
    bw = sum(1 for r in valid if r["majority_prefer"] == "B")
    n_mismatch = sum(1 for r in rows
                     if (r.get("question_type_gate") or {}).get(
                         "verdict") == "MISMATCH")
    return {
        "label": label,
        "n_valid": n,
        "novelty_delta_mean": nd_m,
        "novelty_ci95": [nd_lo, nd_hi],
        "feasibility_abs_gap_mean": fg_m,
        "feasibility_ci95": [fg_lo, fg_hi],
        "per_axis_means_A_minus_B": per_axis_means,
        "prefer_tally": {"a1_arms": a1w, "baseline": bw,
                         "tie": n - a1w - bw},
        "question_type_mismatches_in_scope": n_mismatch,
        "AM14_D5_point_estimate": {
            "novelty_clause_pass": nd_m >= 0.5,
            "feasibility_clause_pass": fg_m <= 0.25,
            "both_simultaneous_pass": (nd_m >= 0.5 and fg_m <= 0.25
                                       and n >= 30),
            "form": "mean over judged pairs (the Art. 14 gate form)",
            "threshold_provenance": "owner directive 2026-11-15 "
                                    "(AM14 D5); class BUYER_DEFINED",
        },
        "r7_comparable_CI": {
            "novelty_clause_pass": nd_lo >= 0.5,
            "feasibility_clause_pass": fg_hi <= 0.25,
            "both_simultaneous_pass": (nd_lo >= 0.5 and fg_hi <= 0.25
                                       and n >= 30),
        },
    }

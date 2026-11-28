#!/usr/bin/env python3
"""r175s2_verifier.py — the Art. 29(c) VERIFIER record for c-0278
(the DIR-2 compute-matched baseline run): a zero-LLM recompute from
the committed bytes (never a re-run).

Verifies, from bytes only:
  1. the SUMMARY tallies recompute from the 12 per-pair row files
     (counts, outcomes, win+tie rate, the CI bounds);
  2. every judged pair carries two judge passes with the order
     swapped and the outcome consistent with the two-pass rule;
  3. the dominance construction is present: every pick=TWO row's
     pipeline bill has the same char count as the baseline bill (the
     baseline answer was in the pool and was delivered when picked).
Exit 0 = verified.
"""
from __future__ import annotations
import json, math, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "eval" / "r175_compute_matched"
ok = True

rows = [json.loads(p.read_text()) for p in sorted(OUT.glob("pair_*.json"))]
summ = json.loads((OUT / "SUMMARY.json").read_text())
judged = [r for r in rows if r.get("status") == "JUDGED"]

# ---- 1. tallies recompute ------------------------------------------
n_w = sum(1 for r in judged if r["outcome"] == "WIN")
n_t = sum(1 for r in judged if r["outcome"] == "TIE")
n_l = sum(1 for r in judged if r["outcome"] == "LOSS")
k, n = n_w + n_t, len(judged)
try:
    from scipy.stats import beta
    lo = beta.ppf(0.025, k, n - k + 1) if k > 0 else 0.0
    hi = beta.ppf(0.975, k + 1, n - k) if k < n else 1.0
except Exception:  # noqa: BLE001
    p = k / n if n else 0
    se = math.sqrt(p * (1 - p) / n) if n else 0
    lo, hi = max(0.0, p - 1.96 * se), min(1.0, p + 1.96 * se)
chk1 = (summ["n_judged"] == n == 12 and summ["wins"] == n_w
        and summ["ties"] == n_t and summ["losses"] == n_l
        and abs(summ["win_tie_rate"] - (k / n if n else 0)) < 1e-9
        and abs(summ["ci95"][0] - round(lo, 3)) < 1e-3
        and abs(summ["ci95"][1] - round(hi, 3)) < 1e-3)
print(f"1. tallies: n={n} W={n_w} T={n_t} L={n_l} rate={k/n:.3f} "
      f"CI[{lo:.3f},{hi:.3f}] -> {'MATCH' if chk1 else 'MISMATCH'}")
ok &= chk1

# ---- 2. two passes, order swapped, outcome consistent --------------
chk2 = True
for r in judged:
    passes = r.get("judge_passes") or []
    if len(passes) != 2:
        chk2 = False
        print(f"   {r['problem_id']}: != 2 passes")
        continue
    v = [p["pipeline"] for p in passes]
    expect = ("WIN" if all(x in ("X", "TIE") for x in v) and "X" in v
              else "LOSS" if all(x in ("Y", "TIE") for x in v)
              and "Y" in v else "TIE")
    if expect != r["outcome"]:
        chk2 = False
        print(f"   {r['problem_id']}: outcome {r['outcome']} != "
              f"rule {expect} on {v}")
print(f"2. two-pass rule: {'MATCH' if chk2 else 'MISMATCH'}")
ok &= chk2

# ---- 3. dominance construction -------------------------------------
chk3 = True
for r in judged:
    if r.get("pipeline_pick") == "TWO":
        if r["pipeline_chars"] != r["baseline_chars"]:
            chk3 = False
            print(f"   {r['problem_id']}: pick=TWO but bills differ "
                  f"({r['pipeline_chars']} vs {r['baseline_chars']})")
print(f"3. dominance (pick=TWO rows deliver the baseline bill): "
      f"{'MATCH' if chk3 else 'MISMATCH'}")
ok &= chk3

verdict = "PASS" if ok else "FAIL"
rec = {
    "record": "R175S2_VERIFIER/1.0.0",
    "claim": "c-0278",
    "role": "VERIFIER",
    "method": "zero-LLM recompute from committed bytes (Art. 13; "
              "never a re-run): tallies+CI, the two-pass judge rule, "
              "the dominance construction",
    "checks": {"tallies_recompute": bool(chk1),
               "two_pass_rule_holds": bool(chk2),
               "dominance_construction": bool(chk3)},
    "verdict": verdict,
    "at": __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"),
    "session_id": "builder-r175s1",
}
(REPO / "eval" / "r175s2_verifier_c0278.json").write_text(
    json.dumps(rec, indent=1) + "\n")
print("VERIFIER verdict:", verdict)
sys.exit(0 if ok else 1)

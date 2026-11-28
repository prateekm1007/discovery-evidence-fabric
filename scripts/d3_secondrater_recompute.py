#!/usr/bin/env python3
"""D3 second-rater agreement on the substance tally + gate
re-computation on the n=28 battery evidence (all offline — zero
provider calls; the quota window recovers meanwhile).

Second rater = the D6 battery's mistral-14b blind judgments
(battery30_r11_r5.json, 28/30 JUDGE_VALID) vs the auditor's r7
tally (7 A1 / 2 baseline / 1 tie, single-rater provisional) on the
OVERLAPPING pairs. The battery's rubric prefer is a blind A/B
verdict on (a1, baseline) — the same contrast the auditor's
overall_preference records.

Gate re-computation: the auditor's method on the promoted delivery
was n=10: novelty delta mean +0.8 CI[0.14,1.46]; feasibility |gap|
0.5 CI[0.12,0.88]. The battery adds the mistral judgments on 28
pairs — but the battery does NOT carry per-axis novelty/feasibility
scores; the rubric axes A4/A6 vs B4/B6 are groundedness/design
axes. The honest re-computation available offline: the SUBSTANCE
clause (sign test on win/tie/loss) at n=28, and the t-CI on the
auditor's own per-pair novelty deltas is re-derived to confirm the
pipeline reproduces the auditor's numbers (agreement=true already
verified for the n=10 set by AM7).

Art. XXV/XXVI: nothing here re-judges the auditor's scores; this
adds the SECOND RATER the AM7 direction 3 asks for and reports
per-axis + overall agreement. The gate decision remains the
auditor's.
"""
import json
import math
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# ---- inputs ---------------------------------------------------------
aud = json.loads(Path("/tmp/auditor_r7.json").read_text())
bat = json.loads((REPO / "eval" / "battery30_r11_r5.json").read_text())
battery_pairs = {r["problem_id"]: r for r in bat["results"]
                 if r.get("judge_outcome") == "JUDGE_VALID"}

# ---- D3: per-pair agreement on the overlap --------------------------
overlap = [p for p in aud["pairs"] if p["problem_id"] in battery_pairs]
per_pair = []
agree = disagree = 0
for p in overlap:
    b = battery_pairs[p["problem_id"]]
    # battery: prefer A means the FIRST-presented arm won. The battery
    # presents (a1, baseline) in that order (one_pair: a1 first).
    b_pref = b.get("prefer")
    b_verdict = ("a1" if b_pref == "A"
                 else "baseline" if b_pref == "B" else "tie")
    a_verdict = p["overall_preference"]
    same = b_verdict == a_verdict
    per_pair.append({
        "problem_id": p["problem_id"],
        "auditor": a_verdict, "battery_mistral": b_verdict,
        "agree": same})
    agree += same
    disagree += not same

n_overlap = len(overlap)

# overall agreement + Cohen's kappa on {a1, baseline, tie}
def _kappa(rows):
    cats = sorted({r["auditor"] for r in rows} |
                  {r["battery_mistral"] for r in rows})
    n = len(rows)
    if n == 0:
        return None
    po = sum(r["agree"] for r in rows) / n
    from collections import Counter
    ca = Counter(r["auditor"] for r in rows)
    cb = Counter(r["battery_mistral"] for r in rows)
    pe = sum(ca[c] * cb[c] for c in cats) / (n * n)
    return None if pe >= 1.0 else round((po - pe) / (1 - pe), 3)

# ---- substance re-test at n=28 (sign test, battery as the rater) ----
wins = sum(1 for r in battery_pairs.values() if r.get("prefer") == "A")
losses = sum(1 for r in battery_pairs.values() if r.get("prefer") == "B")
ties = len(battery_pairs) - wins - losses
decisive = wins + losses


def sign_test_p(k, n):
    """Two-sided binomial p at 0.5."""
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(0, min(k, n - k) + 1))
    p = min(1.0, 2 * tail / (2 ** n))
    return round(p, 4)


# Wilson CI for the win rate among decisive pairs (the battery's own
# summary used wilson over all valid; we recompute over decisive +
# separately over all valid for comparability)
def wilson(k, n, z=1.96):
    if n == 0:
        return (None, None, None)
    ph = k / n
    d = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / d
    hw = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / d
    return (round(c - hw, 4), round(ph, 4), round(c + hw, 4))


# ---- novelty clause: auditor deltas (n=10) reproduced + battery
# novelty proxy unavailable (typed honestly) -------------------------
deltas = [p["novelty_delta"] for p in aud["pairs"]]
gaps = [p["feasibility_abs_gap"] for p in aud["pairs"]]
mean_d = sum(deltas) / len(deltas)
mean_g = sum(gaps) / len(gaps)
sd_d = math.sqrt(sum((x - mean_d) ** 2 for x in deltas) / (len(deltas) - 1))
sd_g = math.sqrt(sum((x - mean_g) ** 2 for x in gaps) / (len(gaps) - 1))
se_d = sd_d / math.sqrt(len(deltas))
se_g = sd_g / math.sqrt(len(gaps))
ci_d = (round(mean_d - 1.96 * se_d, 3), round(mean_d + 1.96 * se_d, 3))
ci_g = (round(mean_g - 1.96 * se_g, 3), round(mean_g + 1.96 * se_g, 3))

out = {
 "record": "D3_SECONDRATER_GATE_RECOMPUTE/1.0.0",
 "at": __import__("datetime").datetime.now(
     __import__("datetime").UTC).isoformat(),
 "second_rater": "xkiro/mistralai/ministral-14b blind rubric judgments "
                 "(D6 battery r5, 28/30 JUDGE_VALID, missing-keys "
                 "retry active)",
 "D3_agreement": {
  "n_overlap": n_overlap,
  "per_pair": per_pair,
  "overall_agreement": round(agree / n_overlap, 3) if n_overlap else None,
  "agree": agree, "disagree": disagree,
  "cohens_kappa": _kappa(per_pair),
  "note": "agreement computed on the OVERLAP of the auditor's 10 judged "
          "pairs and the battery's 28 valid pairs; per-pair rows carry "
          "both verdicts — the tally is CONFIRMED or REVISED by "
          "agreement evidence, not by substitution (Art. XXVI)",
 },
 "substance_retest_n28": {
  "rater": "battery mistral-14b (blind)",
  "a1_wins": wins, "baseline_wins": losses, "ties": ties,
  "n_valid": len(battery_pairs),
  "sign_test_decisive": {"wins": wins, "losses": losses,
                          "p_two_sided": sign_test_p(wins, decisive)},
  "wilson_win_rate_decisive": wilson(wins, decisive),
  "wilson_win_rate_all_valid": wilson(wins, len(battery_pairs)),
 },
 "gate_recompute": {
  "novelty_delta_mean": round(mean_d, 3),
  "novelty_ci95": ci_d,
  "novelty_point_estimate_passes_05": mean_d >= 0.5,
  "novelty_clause_resolved": ci_d[0] >= 0.5,
  "feasibility_abs_gap_mean": round(mean_g, 3),
  "feasibility_ci95": ci_g,
  "feasibility_clause_resolved": ci_g[1] <= 0.25,
  "n_basis": "auditor r7 per-pair deltas (n=10) — the battery does not "
             "carry per-axis novelty/feasibility scores, so the two "
             "formal clauses remain auditor-judgeable; this record "
             "reproduces the pipeline on the same inputs "
             "(agreement with AM7's numbers expected) and adds the "
             "n=28 substance re-test",
  "caveat": "novelty/feasibility CIs at n=10 remain UNRESOLVED "
            "(CI crosses the thresholds); the n=28 battery result "
            "strengthens the substance clause but per-axis scoring "
            "on all 30 pairs remains the auditor's re-judgment task",
 },
}
path = REPO / "eval" / "d3_secondrater_gate_recompute_r11.json"
path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8")
print(f"overlap pairs: {n_overlap} | agree {agree} / disagree {disagree}")
print(f"substance n=28: {wins}W / {losses}L / {ties}T | sign p="
      f"{out['substance_retest_n28']['sign_test_decisive']['p_two_sided']}")
print(f"novelty: mean {mean_d:.2f} CI {ci_d} | feasibility: mean "
      f"{mean_g:.2f} CI {ci_g}")
print(f"-> {path}")

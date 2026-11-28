#!/usr/bin/env python3
"""r184_holdout_tally.py -- INDEPENDENT Art. 13 recompute of the fresh
holdout gate from RAW pair bytes (never the runner's own summary)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PRE = REPO / "eval" / "r184_holdout_prereg.json"
OUT = REPO / "eval" / "r184_holdout_run"


def wilson(k, n, z=1.96):
    if n == 0:
        return [0.0, 0.0, 0.0]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return [round(max(0.0, c - h), 3), round(p, 3),
            round(min(1.0, c + h), 3)]


def main():
    pre = json.loads(PRE.read_text(encoding="utf-8"))
    pids = pre["corpus"]["item_hashes_sha256"]  # 24 items
    present = sorted(OUT.glob("pair_*.json"))
    rows = [json.loads(p.read_text(encoding="utf-8")) for p in present]
    judged = [r for r in rows if r.get("status") == "JUDGED"]
    n = len(judged)
    wt = [r["problem_id"] for r in judged
          if r["outcome"] in ("WIN", "TIE")]
    wins = [r["problem_id"] for r in judged if r["outcome"] == "WIN"]
    ties = [r["problem_id"] for r in judged if r["outcome"] == "TIE"]
    losses = [r["problem_id"] for r in judged if r["outcome"] == "LOSS"]
    ci = wilson(len(wt), n)
    cites = sum(1 for r in judged
                if r.get("deterministic_verifier", {}).get(
                    "citation_patterns"))
    fallback = [r["problem_id"] for r in judged
                if r.get("deterministic_verifier", {}).get("fallback")]
    tally = {
        "record": "R184_HOLDOUT_TALLY/1.0.0 (independent recompute "
                  "from raw pair bytes; Art. 13)",
        "n_corpus": 24, "n_pairs_present": len(rows), "n_judged": n,
        "missing_pids": [f"index {i+1}" for i in range(24)
                         if i >= len(pids) or not any(
                             r["problem_id"].startswith(f"r184h-{i+1:02d}-")
                             for r in rows)],
        "wins": wins, "ties": ties, "losses": losses,
        "wins_plus_ties": len(wt), "wins_plus_ties_share":
            round(len(wt) / n, 4) if n else None,
        "wins_plus_ties_ci95": ci,
        "fabricated_citation_patterns": cites,
        "verifier_fallbacks": fallback,
        "gate_score4": {
            "ci_lower_gt_50": bool(n == 24 and ci[0] > 0.50),
            "zero_fabricated_citations": bool(cites == 0),
            "met": bool(n == 24 and ci[0] > 0.50 and cites == 0)},
        "honest_note": "machine judgments are the pre-registered instrument; "
                       "no dominance tie or plain best-of-N reclassification "
                       "is applied in this wins+ties holdout gate"
    }
    (OUT / "tally.json").write_text(
        json.dumps(tally, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(json.dumps(tally, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

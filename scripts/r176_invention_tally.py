#!/usr/bin/env python3
"""r176_invention_tally.py — the INDEPENDENT Art. 13/19 recompute for
the AM53 invention lane (claim c-0283): recomputes the genuine-win
tally, the AM53 exclusion classes and the Wilson CI from the RAW pair
bytes — never trusting the producing driver's own SUMMARY.

Usage: python3 scripts/r176_invention_tally.py [--out DIR]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CORPUS = REPO / "eval" / "r176_invention_corpus" / "items.jsonl"


def wilson(k: int, n: int, z: float = 1.96) -> list:
    if n == 0:
        return [0.0, 0.0, 0.0]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return [round(max(0.0, c - h), 3), round(p, 3),
            round(min(1.0, c + h), 3)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out",
                    default=str(REPO / "eval" / "r176_invention_run"))
    args = ap.parse_args()
    out = Path(args.out)

    pids = [json.loads(l)["problem_id"]
            for l in CORPUS.read_text().splitlines() if l.strip()]
    rows, missing = [], []
    for pid in sorted(pids):
        f = out / f"pair_{pid}.json"
        if not f.exists():
            missing.append(pid)
            continue
        rows.append(json.loads(f.read_text(encoding="utf-8")))

    judged = [r for r in rows if r.get("status") == "JUDGED"]
    # the recompute reclassifies from the RAW fields (champion +
    # blind outcome) — never trusting the stored genuine_win flag
    def cls(r):
        c = r.get("champion")
        return ("baseline" if c == "baseline"
                else "plain" if c == "plain" else "novel")

    n = len(judged)
    g = [r for r in judged if cls(r) == "novel"
         and r.get("blind_outcome") == "WIN"]
    dom = [r["problem_id"] for r in judged if cls(r) == "baseline"]
    plain = [r["problem_id"] for r in judged if cls(r) == "plain"]
    novel_ch = [r for r in judged if cls(r) == "novel"]
    novel_t = [r for r in novel_ch
               if r.get("blind_outcome") == "TIE"]
    novel_l = [r for r in novel_ch
               if r.get("blind_outcome") == "LOSS"]
    b_w = [r for r in judged if r.get("blind_outcome") == "WIN"]
    b_t = [r for r in judged if r.get("blind_outcome") == "TIE"]
    b_l = [r for r in judged if r.get("blind_outcome") == "LOSS"]

    tally = {
        "record": "R176_INVENTION_TALLY/1.0.0 (independent recompute "
                  "from raw pair bytes)",
        "n_corpus": len(pids), "n_pairs_present": len(rows),
        "n_judged": n, "missing_pairs": missing,
        "genuine_wins": len(g),
        "genuine_win_pids": [r["problem_id"] for r in g],
        "genuine_win_share": round(len(g) / n, 3) if n else None,
        "genuine_win_ci95": wilson(len(g), n),
        "exclusions_per_AM53": {
            "dominance_tie_pids": dom, "n_dominance_ties": len(dom),
            "plain_best_of_n_pids": plain, "n_plain": len(plain)},
        "novel_champions": {
            "n": len(novel_ch),
            "wins": len(g), "ties": len(novel_t), "losses": len(novel_l),
            "wins_plus_ties_ci95": wilson(len(g) + len(novel_t), n)},
        "blind_totals": {"win": len(b_w), "tie": len(b_t),
                         "loss": len(b_l)},
        "gate_point": bool(n and len(g) / n >= 0.5),
        "gate_ci_lower": bool(n and wilson(len(g), n)[0] > 0.50),
        "machine_panel_is_input_not_gate": True,
    }
    f = out / "tally.json"
    f.write_text(json.dumps(tally, indent=1, ensure_ascii=False)
                 + "\n", encoding="utf-8")
    print(json.dumps(tally, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

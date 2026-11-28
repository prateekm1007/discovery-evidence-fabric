#!/usr/bin/env python3
"""r183_collider_tally.py -- INDEPENDENT Art. 13/19 recompute for the
DIR-2 paired collider run. Recomputes BOTH arms' AM53 genuine-win tallies,
the exclusions and the Wilson CIs from the RAW pair bytes (champion +
blind outcome + tournament wins), never trusting the producing driver's
SUMMARY or its stored genuine_win flags.

Writes eval/r183_collider_run/tally.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CORPUS = REPO / "eval" / "r176_invention_corpus" / "items.jsonl"
OUT = REPO / "eval" / "r183_collider_run"
NOVEL_BASE = ("departure", "contradiction", "relaxation")
NOVEL_WITH = NOVEL_BASE + ("collision",)


def wilson(k: int, n: int, z: float = 1.96) -> list:
    if n == 0:
        return [0.0, 0.0, 0.0]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return [round(max(0.0, c - h), 3), round(p, 3),
            round(min(1.0, c + h), 3)]


def cls(name: str) -> str:
    return ("baseline" if name == "baseline" else
            "plain" if name == "plain" else "novel")


def arm(rows: list, arm_key: str, novel: tuple) -> dict:
    judged = [r for r in rows if r.get("status") == "JUDGED"
              and arm_key in r]
    n = len(judged)
    g = [r["problem_id"] for r in judged
         if r[arm_key]["champion"] in novel
         and r[arm_key]["blind_outcome"] == "WIN"]
    dom = [r["problem_id"] for r in judged
           if r[arm_key]["champion"] == "baseline"]
    plain = [r["problem_id"] for r in judged
             if r[arm_key]["champion"] == "plain"]
    novel_ch = [r["problem_id"] for r in judged
                if r[arm_key]["champion"] in novel]
    wins_plus_ties = sum(1 for r in judged
                         if r[arm_key]["champion"] in novel
                         and r[arm_key]["blind_outcome"] in ("WIN", "TIE"))
    return {
        "n_judged": n,
        "genuine_wins": len(g), "genuine_win_pids": g,
        "genuine_win_share": round(len(g) / n, 4) if n else None,
        "genuine_win_ci95": wilson(len(g), n),
        "novel_champions": len(novel_ch),
        "novel_wins_plus_ties": wins_plus_ties,
        "novel_wins_plus_ties_ci95": wilson(wins_plus_ties, n),
        "exclusions": {"dominance_ties": dom, "n_dominance": len(dom),
                       "plain_best_of_n": plain, "n_plain": len(plain)},
        "blind_totals": {
            "win": sum(1 for r in judged
                       if r[arm_key]["blind_outcome"] == "WIN"),
            "tie": sum(1 for r in judged
                       if r[arm_key]["blind_outcome"] == "TIE"),
            "loss": sum(1 for r in judged
                        if r[arm_key]["blind_outcome"] == "LOSS")},
        "champion_counts": {name: sum(1 for r in judged
                              if r[arm_key]["champion"] == name)
                            for name in sorted({r[arm_key]["champion"]
                                                for r in judged})},
        "collision_champions": sum(1 for r in judged
                                   if r[arm_key]["champion"] == "collision"),
    }


def main() -> int:
    pids = [json.loads(l)["problem_id"]
            for l in CORPUS.read_text().splitlines() if l.strip()]
    present, missing = [], []
    for pid in sorted(pids):
        f = OUT / f"pair_{pid}.json"
        (present if f.exists() else missing).append(
            pid if f.exists() else pid)
    rows = [json.loads((OUT / f"pair_{pid}.json").read_text(
        encoding="utf-8")) for pid in present]
    judged = [r for r in rows if r.get("status") == "JUDGED"]
    with_r = arm(rows, "with_collider", NOVEL_WITH)
    no_r = arm(rows, "no_collider", NOVEL_BASE)

    # paired discordance (McNemar-style, from raw flags)
    a = b = 0  # a: with wins/no loses; b: with loses/no wins
    for r in judged:
        w = r["with_collider"]["genuine_win"]
        n = r["no_collider"]["genuine_win"]
        if w and not n:
            a += 1
        if n and not w:
            b += 1

    n = with_r["n_judged"]
    delta = (round(with_r["genuine_win_share"] - no_r["genuine_win_share"], 4)
             if n else None)
    tally = {
        "record": "R183_COLLIDER_TALLY/1.0.0 (independent recompute "
                  "from raw pair bytes)",
        "art": "Art. 13/19 -- independent of the producing driver's SUMMARY",
        "n_corpus": len(pids), "n_pairs_present": len(rows),
        "n_judged": n, "missing_pairs": missing,
        "with_collider": with_r,
        "no_collider": no_r,
        "paired": {
            "with_only_wins": a, "no_only_wins": b,
            "genuine_rate_delta": delta,
            "collider_keep_rule_met": bool(delta is not None and
                                           delta >= 0.05),
            "note": "keep only if +>=0.05 genuine win-rate (DIR 3); "
                    "otherwise the DIR-2 kill criterion applies"},
        "gate_score4": {
            "n_required": 24, "n_have": n,
            "point_17_of_24": bool(n == 24 and
                                   with_r["genuine_wins"] >= 17),
            "ci_lower_gt_50": bool(n and
                                   with_r["genuine_win_ci95"][0] > 0.50),
            "met": bool(n == 24 and with_r["genuine_wins"] >= 17 and
                        with_r["genuine_win_ci95"][0] > 0.50)},
        "disclosures": {
            "generator_transport": "direct-agnes-api (z-ai CLI absent; "
                                   "same served model agnes-3.0-flash)",
            "judge_seat": "tr-deepseek (ctai 429/burned; snlite "
                          "xkiro-quota-blocked -- both measured)",
            "paired_from_one_wave": True,
            "machine_judgments_are_input_not_gate": True,
        },
    }
    (OUT / "tally.json").write_text(
        json.dumps(tally, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(json.dumps(tally, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

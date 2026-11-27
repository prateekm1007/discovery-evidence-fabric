#!/usr/bin/env python3
"""r175_cmb_tally.py — the INDEPENDENT tally recompute for the DIR-2
compute-matched baseline (claim c-0276; auditor constitution Art. 13 /
epistemic Art. 19: every reported tally is recomputed by a standalone
script from the raw judgment bytes, never trusted from the producing
driver's own summary).

Reads (committed bytes only):
  eval/r175_cmb_run/pair_{pid}.json            (pipeline answers + call accounting)
  eval/r175_cmb_run/{pid}_baseline.json        (baseline best + call accounting)
  eval/r175_cmb_run/{pid}_pipeline.json        (K_i accounting)
  eval/r175_cmb_run/ab_map.json                (A/B assignment, seeded)
  eval/r175_cmb_run/judgment_{seat}_{pid}_pass{1,2}.json  (raw legs)

Computes:
  per judge  : the pass-consistent outcome (both passes agree on the
               same ARM -> that arm wins; disagreement or double-TIE
               -> TIE, typed position_disagreement; an exhausted-leg
               pair for a judge -> that judge ABSTAINS typed)
  per pair   : the majority over consistent judges (no majority ->
               TIE typed no_majority)
  overall    : pipeline WINS/TIES/LOSSES over pairs; PRIMARY
               P(wins+ties) Wilson 95% (item-clustered: one outcome
               per pair, never per leg); SECONDARY tie-credit rate
               (wins + 0.5 ties)/n; per-axis majorities; the
               STRICT-BUDGET sensitivity (pairs where the pipeline's
               total calls <= the baseline's); INVALID leg census.

Writes: eval/r175_cmb_run/tally.json + prints the summary.
Machine panel judgments are INPUT (Art. 14) — the reviewer's blind
judgment from the review packets is the GATE (AM52 auditor-judged).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "eval" / "r175_cmb_run"
CORPUS = REPO / "eval" / "problems_dev12.json"


def wilson(k: int, n: int, z: float = 1.96) -> list:
    if n == 0:
        return [0.0, 0.0, 0.0]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 4), round(p, 4), round(c + h, 4)]


def problems() -> list:
    d = json.loads(CORPUS.read_text(encoding="utf-8"))
    return d.get("problems", d) if isinstance(d, dict) else d


def arm_of(assign: dict, label: str) -> str | None:
    if label not in ("A", "B"):
        return None
    return assign.get(label)


def judge_outcome(pid: str, seat: str, assign: dict) -> dict:
    """One judge's pass-consistent outcome for one pair."""
    v = {}
    for pno in (1, 2):
        f = OUT / f"judgment_{seat}_{pid}_pass{pno}.json"
        if not f.exists():
            return {"state": "ABSTAIN_MISSING_LEG"}
        leg = json.loads(f.read_text(encoding="utf-8"))
        if leg.get("outcome") != "VALID":
            return {"state": f"ABSTAIN_{leg.get('outcome')}"}
        v[pno] = leg["verdict"]
    a1 = arm_of(assign, v[1].get("winner"))
    a2 = arm_of(assign, v[2].get("winner"))
    if a1 is None and a2 is None:
        return {"state": "TIE", "typed": "double_TIE",
                "axes": _axes(assign, v)}
    if a1 is None:
        a1, a2 = a2, a1  # one TIE pass maps to the other's arm
    if a1 == a2:
        return {"state": "WIN", "arm": a1, "axes": _axes(assign, v)}
    return {"state": "TIE", "typed": "position_disagreement",
            "axes": _axes(assign, v)}


def _axes(assign: dict, v: dict) -> dict:
    """Axis majorities across the two passes (A/B -> arm)."""
    out = {}
    for ax in ("novelty", "feasibility", "grounding"):
        arms = [arm_of(assign, v[p].get(ax)) for p in (1, 2)]
        arms = [a for a in arms if a]
        if len(set(arms)) == 1:
            out[ax] = arms[0]
        elif not arms:
            out[ax] = "EVEN"
        else:
            out[ax] = "EVEN"
    return out


def main() -> int:
    amap = json.loads((OUT / "ab_map.json").read_text(encoding="utf-8"))
    rows, invalid_legs, abstains = [], [], 0
    seats = set()
    for prob in problems():
        pid = prob["problem_id"]
        pairf, basef = (OUT / f"pair_{pid}.json",
                        OUT / f"{pid}_baseline.json")
        if not pairf.exists() or not basef.exists():
            rows.append({"pid": pid, "state": "INCOMPLETE_PAIR"})
            continue
        pair = json.loads(pairf.read_text(encoding="utf-8"))
        base = json.loads(basef.read_text(encoding="utf-8"))
        if pair.get("state") != "OK" or base.get("state") != "OK":
            rows.append({"pid": pid, "state": "TYPED_ARM_INCOMPLETE",
                         "pair_state": pair.get("state"),
                         "base_state": base.get("state")})
            continue
        assign = amap["pairs"][pid]
        jf = {}
        for f in OUT.glob(f"judgment_*_{pid}_pass*.json"):
            seat = f.name.split("_")[1]
            seats.add(seat)
            leg = json.loads(f.read_text(encoding="utf-8"))
            if leg.get("outcome") != "VALID":
                invalid_legs.append(f.name)
        for seat in sorted(seats):
            jo = judge_outcome(pid, seat, assign)
            jf[seat] = jo
            if jo["state"].startswith("ABSTAIN"):
                abstains += 1
        winners = [j["arm"] for j in jf.values()
                   if j.get("state") == "WIN"]
        ties = [j for j in jf.values() if j.get("state") == "TIE"]
        if winners and winners.count("pipeline") > winners.count(
                "baseline"):
            outcome, mech = "WIN", "majority_pipeline"
        elif winners and winners.count("baseline") > winners.count(
                "pipeline"):
            outcome, mech = "LOSS", "majority_baseline"
        else:
            outcome, mech = "TIE", (
                "no_majority" if winners else "all_tie_or_abstain")
        rows.append({
            "pid": pid, "state": "JUDGED", "outcome": outcome,
            "outcome_mechanism": mech, "judges": jf,
            "call_accounting": {
                "pipeline_total": (pair.get("call_accounting") or {})
                .get("pipeline_total_calls"),
                "baseline_total": (pair.get("call_accounting") or {})
                .get("baseline_total_calls"),
                "pipeline_strict_within_budget": (
                    pair.get("call_accounting") or {})
                .get("pipeline_strict_within_budget")},
            "A": assign.get("A"), "B": assign.get("B"),
        })

    judged = [r for r in rows if r.get("state") == "JUDGED"]
    wins = [r for r in judged if r["outcome"] == "WIN"]
    losses = [r for r in judged if r["outcome"] == "LOSS"]
    ties = [r for r in judged if r["outcome"] == "TIE"]
    n = len(judged)
    strict = [r for r in judged if (r["call_accounting"] or {}).get(
        "pipeline_strict_within_budget")]
    strict_nwt = len([r for r in strict if r["outcome"] != "LOSS"])
    axis = {"novelty": {"pipeline": 0, "baseline": 0, "EVEN": 0},
            "feasibility": {"pipeline": 0, "baseline": 0, "EVEN": 0},
            "grounding": {"pipeline": 0, "baseline": 0, "EVEN": 0}}
    for r in judged:
        for ax in axis:
            votes = [j.get("axes", {}).get(ax)
                     for j in r["judges"].values()]
            votes = [v for v in votes if v]
            if votes and votes.count("pipeline") > votes.count(
                    "baseline"):
                axis[ax]["pipeline"] += 1
            elif votes and votes.count("baseline") > votes.count(
                    "pipeline"):
                axis[ax]["baseline"] += 1
            else:
                axis[ax]["EVEN"] += 1

    tally = {
        "record": "R175_CMB_TALLY/1.0.0 (independent recompute)",
        "n_pairs_total": len(rows), "n_judged": n,
        "wins": len(wins), "losses": len(losses), "ties": len(ties),
        "primary_wins_plus_ties": {
            "rate": round((len(wins) + len(ties)) / n, 4) if n else None,
            "wilson_95": wilson(len(wins) + len(ties), n)},
        "secondary_tie_credit": {
            "rate": round((len(wins) + 0.5 * len(ties)) / n, 4)
            if n else None,
            "wilson_95": wilson(len(wins) + 0.5 * len(ties), n)},
        "strict_budget_sensitivity": {
            "n": len(strict),
            "wins_plus_ties": strict_nwt,
            "rate": round(strict_nwt / len(strict), 4) if strict
            else None},
        "per_axis_majorities": axis,
        "invalid_legs": invalid_legs,
        "abstains": abstains,
        "machine_panel_is_input_not_gate": True,
        "rows": rows,
    }
    (OUT / "tally.json").write_text(
        json.dumps(tally, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(json.dumps({k: v for k, v in tally.items()
                      if k != "rows"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

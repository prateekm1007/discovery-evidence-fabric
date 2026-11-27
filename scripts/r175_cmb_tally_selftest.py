#!/usr/bin/env python3
"""r175_cmb_tally_selftest.py — the Art. 19 unit evidence for the
DIR-2 tally (claim c-0276): fixtures assert the Wilson interval, the
pass-consistency mapping, the majority rule and the tie-credit rate
BEFORE any real judgment is tallied. Zero network, zero LLM."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import r175_cmb_tally as T  # noqa: E402

FIX = REPO / "ENGINE_RUNS" / "r175_cmb_tally_fixtures"
FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  [{'PASS' if cond else 'FAIL'}] {name} {detail}")
    if not cond:
        FAILS.append(name)


def main() -> int:
    # 1) wilson bounds contain the point, are monotone, and match a
    # COMPUTED value (verified with the same formula in-code; the
    # fixture author's first hand-typed value was wrong — the
    # self-test caught it, which is the point of this file)
    w = T.wilson(7, 12)
    check("wilson_7_12", w == [0.3195, 0.5833, 0.8067], str(w))
    check("wilson_0_12", T.wilson(0, 12)[0] == 0.0)
    check("wilson_12_12", T.wilson(12, 12)[2] == 1.0)

    # 2) pass-consistency mapping on fixtures (fresh fixture dir
    # every run — stale legs from a prior run never leak in)
    import shutil
    if FIX.exists():
        shutil.rmtree(FIX)
    FIX.mkdir(parents=True, exist_ok=True)
    T.OUT = FIX
    pid = "fx-01"
    assign = {"A": "pipeline", "B": "baseline"}

    def leg(pass_no, winner, outcome="VALID"):
        v = {"winner": winner, "novelty": "A", "feasibility": "B",
             "grounding": "A", "rationale": "fixture"}
        (FIX / f"judgment_snlite_{pid}_pass{pass_no}.json").write_text(
            json.dumps({"outcome": outcome, "verdict": v}), "utf-8")

    # (A,A): the judge picks the SAME arm (label A = pipeline) in both
    # presentation orders -> CONSISTENT -> pipeline WIN
    leg(1, "A"); leg(2, "A")
    jo = T.judge_outcome(pid, "snlite", assign)
    check("consistent_passes->pipeline_win",
          jo == {"state": "WIN", "arm": "pipeline",
                 "axes": {"novelty": "pipeline",
                          "feasibility": "baseline",
                          "grounding": "pipeline"}}, str(jo))

    # (A,B): the judge follows PRESENTATION POSITION (pass 1 presents
    # A first; pass 2 presents B first) -> position bias -> TIE
    leg(1, "A"); leg(2, "B")
    jo = T.judge_outcome(pid, "snlite", assign)
    check("position_bias->TIE", jo["state"] == "TIE"
          and jo.get("typed") == "position_disagreement", str(jo))

    leg(1, "TIE"); leg(2, "TIE")  # double TIE
    jo = T.judge_outcome(pid, "snlite", assign)
    check("double_tie->TIE", jo["state"] == "TIE", str(jo))

    leg(1, "A", outcome="PARSE_FAILED"); leg(2, "B")
    jo = T.judge_outcome(pid, "snlite", assign)
    check("exhausted_leg->ABSTAIN",
          jo["state"].startswith("ABSTAIN"), str(jo))

    # 3) majority rule via the full tally on a 3-pair fixture corpus
    (FIX / "ab_map.json").write_text(json.dumps(
        {"seed": "fx", "pairs": {
            "fx-01": {"A": "pipeline", "B": "baseline"},
            "fx-02": {"A": "baseline", "B": "pipeline"},
            "fx-03": {"A": "pipeline", "B": "baseline"}}}), "utf-8")
    for p, state in (("fx-01", "OK"), ("fx-02", "OK"),
                     ("fx-03", "OK")):
        (FIX / f"pair_{p}.json").write_text(json.dumps(
            {"pid": p, "state": state, "pipeline_answer": "x",
             "call_accounting": {"pipeline_total_calls": 13,
                                 "baseline_total_calls": 13,
                                 "pipeline_strict_within_budget":
                                     True}}), "utf-8")
        (FIX / f"{p}_baseline.json").write_text(json.dumps(
            {"pid": p, "state": "OK", "baseline_best": "y",
             "calls_total": 13}), "utf-8")
    # fx-01: pipeline wins (both judges consistent on A); fx-02:
    # baseline wins (both judges consistent on B); fx-03: split
    # judges (snlite->A, gpt6luna->B) -> no majority -> TIE
    for seat in ("snlite", "gpt6luna"):
        (FIX / f"judgment_{seat}_fx-01_pass1.json").write_text(
            json.dumps({"outcome": "VALID", "verdict": {
                "winner": "A", "novelty": "A", "feasibility": "A",
                "grounding": "A", "rationale": ""}}), "utf-8")
        (FIX / f"judgment_{seat}_fx-01_pass2.json").write_text(
            json.dumps({"outcome": "VALID", "verdict": {
                "winner": "A", "novelty": "A", "feasibility": "A",
                "grounding": "A", "rationale": ""}}), "utf-8")
        # fx-02 assign: A=baseline, B=pipeline -> consistent (A,A)
        # verdicts are BASELINE wins (the map is exercised, not
        # assumed)
        (FIX / f"judgment_{seat}_fx-02_pass1.json").write_text(
            json.dumps({"outcome": "VALID", "verdict": {
                "winner": "A", "novelty": "A", "feasibility": "A",
                "grounding": "A", "rationale": ""}}), "utf-8")
        (FIX / f"judgment_{seat}_fx-02_pass2.json").write_text(
            json.dumps({"outcome": "VALID", "verdict": {
                "winner": "A", "novelty": "A", "feasibility": "A",
                "grounding": "A", "rationale": ""}}), "utf-8")
    (FIX / "judgment_snlite_fx-03_pass1.json").write_text(
        json.dumps({"outcome": "VALID", "verdict": {
            "winner": "A", "novelty": "A", "feasibility": "A",
            "grounding": "A", "rationale": ""}}), "utf-8")
    (FIX / "judgment_snlite_fx-03_pass2.json").write_text(
        json.dumps({"outcome": "VALID", "verdict": {
            "winner": "A", "novelty": "A", "feasibility": "A",
            "grounding": "A", "rationale": ""}}), "utf-8")
    (FIX / "judgment_gpt6luna_fx-03_pass1.json").write_text(
        json.dumps({"outcome": "VALID", "verdict": {
            "winner": "B", "novelty": "B", "feasibility": "B",
            "grounding": "B", "rationale": ""}}), "utf-8")
    (FIX / "judgment_gpt6luna_fx-03_pass2.json").write_text(
        json.dumps({"outcome": "VALID", "verdict": {
            "winner": "B", "novelty": "B", "feasibility": "B",
            "grounding": "B", "rationale": ""}}), "utf-8")
    T.CORPUS = FIX / "corpus.json"
    (FIX / "corpus.json").write_text(json.dumps(
        [{"problem_id": "fx-01"}, {"problem_id": "fx-02"},
         {"problem_id": "fx-03"}]), "utf-8")
    T.main()
    tally = json.loads((FIX / "tally.json").read_text("utf-8"))
    check("fixture tally W/T/L",
          (tally["wins"], tally["ties"], tally["losses"]) == (1, 1, 1),
          str((tally["wins"], tally["ties"], tally["losses"])))
    check("primary 2/3", tally["primary_wins_plus_ties"]["rate"]
          == round(2 / 3, 4))
    check("tie-credit (1+0.5)/3",
          tally["secondary_tie_credit"]["rate"] == round(1.5 / 3, 4))
    check("strict budget 2/3",
          tally["strict_budget_sensitivity"]["rate"] == round(2 / 3, 4))
    check("fx-03 no_majority", any(
        r["pid"] == "fx-03" and r["outcome_mechanism"] == "no_majority"
        for r in tally["rows"]))

    print(("SELFTEST PASS" if not FAILS
           else f"SELFTEST FAIL: {FAILS}"))
    return 0 if not FAILS else 2


if __name__ == "__main__":
    raise SystemExit(main())

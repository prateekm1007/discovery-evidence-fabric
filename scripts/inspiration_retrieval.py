#!/usr/bin/env python3
"""r191s2 inspiration retrieval (owner DIR-6 / Score-7).

The MOOSE-Chem rediscovery benchmark (eval/moose_chem/
rediscovery_benchmark.json, 51 items, all public dates 2024 = post
knowledge-cutoff 2023-10) measures mechanism-level rediscovery:
given ONLY the background question + survey, the machine must
retrieve INSPIRATION (pre-cutoff literature mechanisms) and propose
a hypothesis whose MECHANISM matches the paper's true hypothesis.

This module implements the retrieval stage:
  retrieve_inspirations(background_question, background_survey)
    -> ranked pre-cutoff inspiration mechanisms (typed provenance)

And the full run driver:
  python3 scripts/r191s2_inspiration_retrieval.py [--n 20] [--only ID]

Scoring (the pre-declared gate): mechanism-level match judged by the
two-family panel (hy4 + qwen3.8), blind, order-swapped — machine rate
>= 30% vs no-evidence baseline <= 15% on N >= 20 items.

Design notes (typed):
- Retrieval is GENERATOR-SIDE (agnes) drawing on pre-cutoff knowledge
  only; the judge never sees which inspirations were retrieved.
- The restriction (literature STRICTLY BEFORE the item's public date)
  is enforced in the prompt + recorded per item; the true_hypothesis
  is NEVER shown to the generator or the judge before the verdict.
- Byte-resume: eval/r191s2_rediscovery/item_{id}.json.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r186s1_ablation_run import (  # noqa: E402  (byte-faithful reuse)
    JUDGES, agnes, blind_prompt, env_keys, judge_leg,
)

OUT = REPO / "eval" / "r191s2_rediscovery"
OUT.mkdir(exist_ok=True)
BENCH = REPO / "eval" / "moose_chem" / "rediscovery_benchmark.json"

CUTOFF = "2023-10"  # knowledge cutoff; every item is post-cutoff


def retrieval_prompt(item: dict) -> str:
    return (
        "You are a research librarian with a literature corpus that "
        f"ends at {CUTOFF}. From the BACKGROUND below, identify the "
        "3-5 PRE-EXISTING mechanisms, phenomena or materials-science "
        "strategies (things published well before the cutoff) that "
        "are most likely to INSPIRE a novel hypothesis answering the "
        "background question. For each: name the mechanism, its "
        "source literature class, and the one-line reason it applies. "
        "Do NOT propose the final hypothesis yet — only the "
        "inspirations.\n\n"
        f"BACKGROUND QUESTION:\n{item['background_question']}\n\n"
        f"BACKGROUND SURVEY:\n{item['background_survey'][:3000]}\n\n"
        "Answer with ONLY a numbered list (3-5 items), one line each: "
        "MECHANISM — source class — why it applies."
    )


def hypothesis_prompt(item: dict, inspirations: str) -> str:
    return (
        "Using the INSPIRATIONS below as your evidence base, propose "
        "ONE novel hypothesis that answers the BACKGROUND QUESTION: a "
        "concrete mechanism (materials, geometry, chemistry, regime) "
        "with the reason it should work and the decisive test.\n\n"
        f"BACKGROUND QUESTION:\n{item['background_question']}\n\n"
        f"BACKGROUND SURVEY:\n{item['background_survey'][:3000]}\n\n"
        f"INSPIRATIONS:\n{inspirations}\n\n"
        "Answer with ONLY the hypothesis (mechanism first, then the "
        "reason, then the test)."
    )


def baseline_prompt(item: dict) -> str:
    """The no-evidence baseline arm: question + survey, no retrieval."""
    return (
        "Propose ONE novel hypothesis that answers the BACKGROUND "
        "QUESTION: a concrete mechanism with the reason it should "
        "work and the decisive test.\n\n"
        f"BACKGROUND QUESTION:\n{item['background_question']}\n\n"
        f"BACKGROUND SURVEY:\n{item['background_survey'][:3000]}\n\n"
        "Answer with ONLY the hypothesis."
    )


def mech_match_prompt(question: str, true_hyp: str, proposed: str) -> str:
    return (
        "Does the PROPOSED hypothesis reproduce the MECHANISM of the "
        "TRUE hypothesis (the core physical/chemical idea — not the "
        "wording, not the materials naming)? Score Y if the core "
        "mechanism matches, X if it does not.\n\n"
        f"BACKGROUND QUESTION:\n{question}\n\n"
        f"TRUE HYPOTHESIS:\n{true_hyp}\n\n"
        f"PROPOSED HYPOTHESIS:\n{proposed}\n\n"
        "Answer with ONLY: VERDICT: Y or VERDICT: X"
    )


def run_item(item: dict, keys: dict, with_evidence: bool) -> dict:
    t0 = time.time()
    calls = 0
    if with_evidence:
        insp = agnes(retrieval_prompt(item), keys,
                     what=f"{item['item_id']} retrieve")
        calls += 1
        hyp = agnes(hypothesis_prompt(item, insp), keys,
                    what=f"{item['item_id']} hypothesize")
        calls += 1
    else:
        insp = ""
        hyp = agnes(baseline_prompt(item), keys,
                    what=f"{item['item_id']} baseline")
        calls += 1
    # blind two-family mechanism match (judges never see inspirations)
    votes = {}
    for seat_tag in ("hy4-flash-centai", "qwen3.8-max-xkiro"):
        vs = []
        for order in ("XY", "YX"):
            a, b = ((hyp, item["true_hypothesis"]) if order == "XY"
                    else (item["true_hypothesis"], hyp))
            try:
                v, _ = judge_leg(
                    seat_tag, mech_match_prompt(
                        item["background_question"], a, b),
                    keys, f"{item['item_id']} {seat_tag} {order}")
            except Exception as e:  # noqa: BLE001 typed, never re-roll
                v = f"TYPED_JUDGE_FAILURE {type(e).__name__}"
            pip = (v if order == "XY" else
                   "X" if v == "Y" else "Y" if v == "X" else v)
            vs.append(pip)
        yes = sum(1 for v in vs if v == "Y")
        votes[seat_tag] = "MATCH" if yes == 2 else (
            "NO_MATCH" if yes == 0 else "SPLIT")
    return {
        "item_id": item["item_id"], "arm": ("evidence" if with_evidence
                                            else "baseline"),
        "inspirations": insp[:2000], "hypothesis": hyp[:3000],
        "votes": votes, "calls": calls,
        "wall_s": round(time.time() - t0, 1),
        "retrieval_restriction": item["retrieval_restriction"]["rule"],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20,
                    help="items to run (the pre-registered N >= 20)")
    ap.add_argument("--only", default=None,
                    help="single item id (byte-resume friendly)")
    args = ap.parse_args()

    bench = json.loads(BENCH.read_text(encoding="utf-8"))
    items = bench["items"][:args.n] if not args.only else \
        [i for i in bench["items"] if i["item_id"] == args.only]
    keys = env_keys()

    for item in items:
        for arm in ("evidence", "baseline"):
            f = OUT / f"item_{item['item_id']}_{arm}.json"
            if f.exists():
                continue
            r = run_item(item, keys, with_evidence=(arm == "evidence"))
            f.write_text(json.dumps(r, indent=1, ensure_ascii=False),
                         encoding="utf-8")
            print(f"  {item['item_id']} {arm}: {r['votes']} "
                  f"{r['wall_s']}s", flush=True)

    # tally (Art. 13: recomputable from the item bytes)
    tally = {"record": "R191S2_REDISCOVERY_TALLY/1.0.0", "n": 0,
             "evidence_matches": 0, "baseline_matches": 0,
             "gate": ">=30% evidence vs <=15% baseline, N >= 20"}
    per = []
    for item in items:
        row = {"item_id": item["item_id"]}
        for arm, k in (("evidence", "evidence_matches"),
                       ("baseline", "baseline_matches")):
            f = OUT / f"item_{item['item_id']}_{arm}.json"
            if not f.exists():
                continue
            d = json.loads(f.read_text(encoding="utf-8"))
            vs = list(d["votes"].values())
            m = "MATCH" if vs.count("MATCH") >= 1 and "SPLIT" not in vs \
                else "SPLIT" if "SPLIT" in vs else "NO_MATCH"
            row[arm] = m
            if m == "MATCH":
                tally[k] += 1
        per.append(row)
    tally["n"] = len(per)
    tally["evidence_rate"] = round(
        tally["evidence_matches"] / max(1, tally["n"]), 3)
    tally["baseline_rate"] = round(
        tally["baseline_matches"] / max(1, tally["n"]), 3)
    tally["per_item"] = per
    (OUT / "tally.json").write_text(
        json.dumps(tally, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in tally.items()
                      if k != "per_item"}, indent=1))


if __name__ == "__main__":
    main()

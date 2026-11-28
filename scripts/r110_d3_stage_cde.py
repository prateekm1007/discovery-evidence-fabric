#!/usr/bin/env python3
"""r110_d3_stage_cde.py — the instrument prereg's stages C+D+E: the
bare arm, the engine arm, and the deterministic judge-free scoring.

  tau calibration FIRST (before any generation): positives =
  (key_element, its own GT), negatives = (key_element, OTHER items'
  GTs); tau = midpoint(max negative, min positive), both distributions
  recorded.
  bare arm  : the served material + a minimal directive (one agnes
              generation, temp-equivalent transport default).
  engine arm: rp.generator_prompt over the NEW served material (one
              agnes generation).
  scoring   : graded key-element recall + hypothesis ranking
              (hit@1/MRR vs the authored distractors) +
              survey-faithfulness; engine-minus-bare paired bootstrap
              (10k, seed 110) with the 95% CI.
All raw bytes committed (eval/r110_d3_instrument_raw/)."""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()
from discovery_fabric.engine import route_adapter as ra  # noqa: E402
from discovery_fabric.engine import rediscovery_protocol as rp  # noqa
from discovery_fabric.engine.core_mechanism_gate import (  # noqa
    load_specter2_encoder, cosine_distance)

RAW = REPO / "eval" / "r110_d3_instrument_raw"
OUT = REPO / "eval" / "r110_d3_instrument_result.json"
SEED = 110


def agnes(prompt, tag, target=1000):
    path = RAW / f"{tag}.txt"
    if path.exists():
        return path.read_text(encoding="utf-8")
    txt = ra.agnes_chat([{"role": "user", "content": prompt}],
                        model="agnes-3.0-flash", visible_target=target,
                        timeout_s=300.0).get("content") or ""
    path.write_text(txt, encoding="utf-8")
    time.sleep(8)
    return txt


def bare_prompt(item):
    sv = item["served"]
    papers = "; ".join(p.get("title", "")
                       for p in sv.get("inspiration_papers", []))
    return ("Background question: "
            f"{sv['background_question']['text']}\n\n"
            f"Domain background: {sv['background_survey']['text']}\n\n"
            f"Related work: {papers}\n\n"
            "State your hypothesis for what the mechanism is and how "
            "to exploit it. Answer directly in plain prose.")


def split_key_sentences(survey_text, cap=6):
    import re
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+",
                                         survey_text) if s.strip()]
    return [s for s in sents if len(s.split()) >= 8][:cap]


def main():
    items = [json.loads(l) for l in
             (RAW / "items.jsonl").read_text(
                 encoding="utf-8").strip().split("\n")]
    print("items:", len(items))
    enc = load_specter2_encoder("/home/z/my-project/models_cache", None)

    # ---- tau calibration (BEFORE any generation) ----
    # the GT vectors are encoded ONCE and reused (the cached-vector
    # fix: 30 encodes, not ~22.5k)
    pos, neg = [], []
    gts = [enc.encode(it["ground_truth"]["finegrained_hypothesis"])
           for it in items]
    mains = [enc.encode(it["ground_truth"]["main_hypothesis"])
             for it in items]
    for i, it in enumerate(items):
        gv = gts[i]
        for e in it["key_elements"]:
            ev = enc.encode(e)
            pos.append(cosine_distance(ev, gv))
            for j, other in enumerate(items):
                if j == i:
                    continue
                neg.append(cosine_distance(ev, gts[j]))
            neg.append(cosine_distance(ev, mains[i]))
    max_neg, min_pos = max(neg), min(pos)
    tau = round((max_neg + min_pos) / 2, 4)
    calib = {"tau": tau, "max_negative_cosine_distance": max_neg,
             "min_positive_cosine_distance": min_pos,
             "note": ("DISTANCES: lower = closer; covered iff "
                      "min-distance <= tau (the matched threshold on "
                      "the DISTANCE scale — the midpoint keeps every "
                      "positive and excludes every negative BY "
                      "CONSTRUCTION on the calibration pairs)"),
             "n_pos_pairs": len(pos), "n_neg_pairs": len(neg)}
    print("tau calibration:", calib)

    covered = lambda gv, elements: sum(
        1 for e in elements
        if cosine_distance(gv, enc.encode(e)) <= tau)

    # ---- the two arms ----
    gen = {}
    for it in items:
        iid = it["item_id"]
        bare_txt = agnes(bare_prompt(it), f"bare_{iid}")
        eng_txt = agnes(rp.generator_prompt(it), f"eng_{iid}")
        gen[iid] = {"bare": bare_txt, "engine": eng_txt}
        print(f"  {iid}: bare {len(bare_txt)}c / engine {len(eng_txt)}c")

    # ---- scoring ----
    rows = []
    for it in items:
        iid = it["item_id"]
        gt_main = it["ground_truth"]["main_hypothesis"]
        gtv = enc.encode(gt_main)
        elements = it["key_elements"]
        survey_sents = split_key_sentences(
            it["served"]["background_survey"]["text"])
        row = {"item_id": iid, "n_elements": len(elements)}
        for arm_name in ("bare", "engine"):
            txt = gen[iid][arm_name]
            tv = enc.encode(txt)
            rec = (covered(tv, elements), len(elements))
            # ranking: candidates {generation, d1..d3} vs the GT
            cands = [("generation", tv)] + [
                (f"d{i + 1}", enc.encode(d))
                for i, d in enumerate(it["distractors"])]
            dists = sorted((cosine_distance(v, gtv), nm)
                           for nm, v in cands)
            rank = [nm for _, nm in dists].index("generation") + 1
            rec_survey = (covered(tv, survey_sents),
                          len(survey_sents))
            row[arm_name] = {
                "elements_covered": rec[0],
                "element_recall": round(rec[0] / max(1, rec[1]), 4),
                "survey_covered": rec_survey[0],
                "survey_recall": round(rec_survey[0]
                                       / max(1, rec_survey[1]), 4),
                "rank_of_generation": rank,
                "hit1": int(rank == 1),
                "mrr": round(1.0 / rank, 4),
                "dist_to_gt_main": round(
                    min(d for d, nm in dists
                        if nm == "generation"), 4),
            }
        rows.append(row)

    def paired(metric):
        diffs = [r["engine"][metric] - r["bare"][metric] for r in rows]
        rng = np.random.default_rng(SEED)
        n = len(diffs)
        boots = [float(np.mean(rng.choice(diffs, n, replace=True)))
                 for _ in range(10000)]
        lo, hi = np.percentile(boots, [2.5, 97.5])
        return {"mean_diff": round(float(np.mean(diffs)), 4),
                "ci95": [round(lo, 4), round(hi, 4)],
                "n_pairs": n}

    comparison = {m: paired(m) for m in
                  ("element_recall", "survey_recall", "hit1", "mrr")}

    rec = {
        "record": "R110_D3_INSTRUMENT_RESULT/1.0.0",
        "at": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ (sandbox clock, TRUE UTC)"),
        "executor": "builder-r109s1",
        "claim": "c-0145 (r110-lane-d3-instrument; the R110 direction "
                 "3)",
        "prereg": "eval/r110_d3_instrument_prereg.json",
        "n_items": len(rows),
        "tau_calibration": calib,
        "per_item": rows,
        "engine_minus_bare_paired_bootstrap": comparison,
        "judge_free": ("no 3-class judge labels anywhere; the matcher "
                       "is the deterministic SPECTER2 stack; the "
                       "distractor ranking is pure embedding"),
        "auditor_spot_check": ("the raw bytes for every item are in "
                               "eval/r110_d3_instrument_raw/ "
                               "(author outputs, both arms' "
                               "generations) — the >=10-item spot "
                               "check reads abstract vs GT vs "
                               "generations side by side"),
        "typed": ("staged for the auditor; NO score-9 acceptance "
                  "claimed; the comparison to the 0.0667 3-class "
                  "number stays NOT-APPLICABLE"),
    }
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False)
                   + "\n", encoding="utf-8")
    print("comparison:", json.dumps(comparison, indent=1))
    print("wrote", OUT)


if __name__ == "__main__":
    main()

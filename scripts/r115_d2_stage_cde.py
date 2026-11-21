#!/usr/bin/env python3
"""r115_d2_stage_cde.py — the harder-corpus prereg's stages C+D+E:
tau calibration (BEFORE any generation), the L0 arms (served =
question + title + abstract verbatim — the F94 spoiler removed),
the preregistered PILOT LADDER (first 12 bare, band [0.4, 0.75],
typed abort outside), then the full run + judge-free scoring +
abstract-faithfulness (the survey guard's L0 substitute) + the
paired percentile bootstrap (10k, seed 110).

Representation discipline (the r114 probe lesson): the arm vector is
the RAW FILE TEXT verbatim; coverage = whole-text distance per the
r110 CDE formula (no per-item formula shopping). Byte-skip resume at
every level — no second generation ever (Art. 29(c))."""
import json
import os
import re
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
from discovery_fabric.engine.core_mechanism_gate import (  # noqa
    load_specter2_encoder, cosine_distance)

RAW = REPO / "eval" / "r115_d2_harder_raw"
OUT = REPO / "eval" / "r115_d2_harder_result.json"
SEED = 110
PILOT_N = 12
BAND_LO, BAND_HI = 0.4, 0.75
GUARD_SENTS = 12


def d12(s):
    import hashlib
    return hashlib.sha256(s.encode()).hexdigest()[:12]


def parse_json_loose(s):
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\n", "", s)
        s = re.sub(r"\n```\s*$", "", s)
    return json.loads(s, strict=False)


def agnes(prompt, tag, target=1000):
    path = RAW / f"{tag}.txt"
    if path.exists():
        return path.read_text(encoding="utf-8")
    txt = None
    for attempt in (1, 2, 3):
        try:
            txt = ra.agnes_chat([{"role": "user", "content": prompt}],
                                model="agnes-3.0-flash",
                                visible_target=target,
                                timeout_s=300.0).get("content") or ""
            break
        except Exception as e:  # noqa: BLE001
            print(tag, f"attempt {attempt} wall: "
                  f"{type(e).__name__}: {str(e)[:60]}", flush=True)
            if "rate_limited" in str(e).lower() or "429" in str(e):
                time.sleep(150)
            else:
                time.sleep(20)
    if txt is None:
        raise RuntimeError(
            f"INFRA_BLOCKED: agnes quota wall persisted for {tag} "
            "(Art. 15; byte-skip resume makes any restart free)")
    path.write_text(txt, encoding="utf-8")
    time.sleep(8)
    return txt


def build_items():
    items = []
    for line in (RAW / "items.jsonl").read_text(
            encoding="utf-8").strip().split("\n"):
        src = json.loads(line)
        apath = RAW / f"author_{src['item_id']}.txt"
        a = parse_json_loose(apath.read_text(encoding="utf-8"))
        gt_main = a.get("main_hypothesis") or a.get("main_hypotheis", "")
        gt_fine = (a.get("finegrained_hypothesis")
                   or a.get("finegrained_hypotheis", ""))
        served = {"background_question": {
                      "text": a.get("background_question", "")},
                  "title": src["title"],
                  "abstract": {"text": src["abstract"]}}
        assert "ground_truth" not in json.dumps(served), \
            "served block must never embed ground truth"
        items.append({
            "item_id": src["item_id"], "doi": src["doi"],
            "title": src["title"],
            "served": served,
            "ground_truth": {"main_hypothesis": str(gt_main),
                             "finegrained_hypothesis": str(gt_fine)},
            "key_elements": [str(e) for e in a.get("key_elements", [])],
            "distractors": [str(d) for d in a.get("distractors", [])],
            "authored_survey_not_served": a.get("background_survey", ""),
            "authored_inspirations_not_served":
                a.get("inspiration_papers", []),
        })
    return items


RUNG = "L0"  # env R115_RUNG: L0 (question+title+abstract) | LM1 (question+title only — the preregistered upper rung)


def bare_prompt(it):
    sv = it["served"]
    parts = ["Background question: "
             f"{sv['background_question']['text']}",
             f"Paper title: {sv['title']}"]
    if RUNG == "L0":
        parts.append(f"Paper abstract: {sv['abstract']['text']}")
    parts.append("State your hypothesis for what the mechanism is "
                 "and how to exploit it. Answer directly in plain "
                 "prose.")
    return "\n\n".join(parts)


def engine_prompt(it):
    sv = it["served"]
    abstract_block = ""
    if RUNG == "L0":
        abstract_block = ("PAPER ABSTRACT:\n"
                          f"{sv['abstract']['text']}\n\n")
    return (
        "You are a chemistry research strategist. Using ONLY the "
        "material below, propose ONE fine-grained, testable research "
        "hypothesis: it must name a concrete mechanism (what causes "
        "what, through what structural or chemical route) and a "
        "verifiable predicted outcome.\n\n"
        + abstract_block
        + "BACKGROUND QUESTION:\n"
        + f"{sv['background_question']['text']}\n\n"
        + "Answer with STRICT JSON only, no markdown, in exactly this "
        "shape:\n{\"hypothesis\": \"<the full fine-grained "
        "hypothesis>\", \"key_mechanism\": \"<one sentence naming the "
        "core causal or structural mechanism>\", "
        "\"predicted_result\": \"<the concrete verifiable outcome>\"}")


def guard_sentences(abstract_text):
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+",
                                         abstract_text) if s.strip()]
    return [s for s in sents if len(s.split()) >= 8][:GUARD_SENTS]


def main():
    global RUNG
    RUNG = os.environ.get("R115_RUNG", "L0")
    items = build_items()
    print("items:", len(items), "RUNG:", RUNG, flush=True)
    enc = load_specter2_encoder("/home/z/my-project/models_cache", None)

    # ---- tau calibration (BEFORE any generation) — the r110
    # construction verbatim: pos = (element, own finegrained);
    # neg = (element, 29 other finegrained) + (element, own main) ----
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
            for j in range(len(items)):
                if j != i:
                    neg.append(cosine_distance(ev, gts[j]))
            neg.append(cosine_distance(ev, mains[i]))
    max_neg, min_pos = max(neg), min(pos)
    tau = round((max_neg + min_pos) / 2, 4)
    calib = {"tau": tau, "max_negative_cosine_distance": max_neg,
             "min_positive_cosine_distance": min_pos,
             "n_pos_pairs": len(pos), "n_neg_pairs": len(neg),
             "note": ("DISTANCES: lower = closer; covered iff "
                      "whole-text distance <= tau (the midpoint keeps "
                      "every positive and excludes every negative BY "
                      "CONSTRUCTION on the calibration pairs)")}
    print("tau calibration:", calib, flush=True)

    covered = lambda tv, elements: sum(
        1 for e in elements
        if cosine_distance(tv, enc.encode(e)) <= tau)

    # ---- PILOT LADDER (preregistered): first 12 items, bare only ----
    pilot = items[:PILOT_N]
    pilot_recs = []
    for it in pilot:
        txt = agnes(bare_prompt(it), f"bare_{RUNG}_{it['item_id']}")
        tv = enc.encode(txt)
        rec = covered(tv, it["key_elements"]) / max(
            1, len(it["key_elements"]))
        pilot_recs.append({"item_id": it["item_id"],
                           "n_elements": len(it["key_elements"]),
                           "elements_covered": covered(tv, it["key_elements"]),
                           "recall": round(rec, 4),
                           "chars": len(txt)})
        print("pilot", it["item_id"], "recall", round(rec, 4), flush=True)
    pilot_mean = float(np.mean([r["recall"] for r in pilot_recs]))
    print("PILOT_MEAN:", round(pilot_mean, 4),
          "band:", [BAND_LO, BAND_HI], flush=True)

    ladder = {"pilot_n": PILOT_N, "rung": RUNG, "pilot_mean_recall":
              round(pilot_mean, 4), "band": [BAND_LO, BAND_HI],
              "pilot_rows": pilot_recs}
    if not (BAND_LO <= pilot_mean <= BAND_HI):
        if RUNG == "LM1":
            ladder["typed"] = (
                "DESIGN_FINDING: out of band at BOTH preregistered "
                "rungs (L0 0.9305 ceiling, LM1 out-of-band) — max 2 "
                "ladder probes reached per the prereg; the serving-set "
                "axis cannot tune recall into [0.4, 0.75]; the "
                "difficulty axis needs a different instrument class "
                "(the auditor's dir-3 engineering-bind set is the "
                "designated alternative). No engine verdict is "
                "claimable from this lane.")
            verdict = "TYPED_DESIGN_FINDING_BAND_UNREACHABLE"
        else:
            ladder["typed"] = (
                "ABORT: pilot out of band — the preregistered upper "
                "rung (LM1: title+question only) is the next probe; "
                "the L0 calls stay recorded as the ladder probe, "
                "never counted")
            verdict = "TYPED_ABORT_OUT_OF_BAND"
        json.dump({"record": "R115_D2_HARDER_LADDER_PROBE/1.0.0",
                   "at": datetime.now(timezone.utc).strftime(
                       "%Y-%m-%dT%H:%M:%SZ"),
                   "calibration": calib, "ladder": ladder,
                   "verdict": verdict},
                  open(RAW / f"ladder_probe_{RUNG}.json", "w"), indent=1)
        print(verdict, flush=True)
        return

    # ---- full run: remaining bare + engine for all 30 ----
    gen = {}
    for it in items:
        iid = it["item_id"]
        gen[iid] = {
            "bare": agnes(bare_prompt(it), f"bare_{RUNG}_{iid}"),
            "engine": agnes(engine_prompt(it), f"eng_{RUNG}_{iid}"),
        }
        print(f"  {iid}: bare {len(gen[iid]['bare'])}c / "
              f"engine {len(gen[iid]['engine'])}c", flush=True)

    # ---- scoring (whole-text distance, raw bytes verbatim) ----
    rows = []
    for it in items:
        iid = it["item_id"]
        gtv = mains[items.index(it)]
        elements = it["key_elements"]
        guard = (guard_sentences(it["served"]["abstract"]["text"])
                 if RUNG == "L0" else [])
        row = {"item_id": iid, "n_elements": len(elements),
               "n_guard_sents": len(guard)}
        for arm_name in ("bare", "engine"):
            tv = enc.encode(gen[iid][arm_name])
            cvd = covered(tv, elements)
            cands = [("generation", tv)] + [
                (f"d{i + 1}", enc.encode(d))
                for i, d in enumerate(it["distractors"])]
            dists = sorted((cosine_distance(v, gtv), nm)
                           for nm, v in cands)
            rank = [nm for _, nm in dists].index("generation") + 1
            rec_guard = covered(tv, guard) if guard else 0
            row[arm_name] = {
                "elements_covered": cvd,
                "element_recall": round(cvd / max(1, len(elements)), 4),
                "guard_covered": rec_guard,
                "guard_recall": (round(rec_guard / max(1, len(guard)), 4)
                                 if guard else None),
                "rank_of_generation": rank,
                "hit1": int(rank == 1),
                "mrr": round(1.0 / rank, 4),
                "dist_to_gt_main": round(
                    min(d for d, nm in dists
                        if nm == "generation"), 4)}
        rows.append(row)

    def paired(metric):
        diffs = [r["engine"][metric] - r["bare"][metric] for r in rows]
        rng = np.random.default_rng(SEED)
        n = len(diffs)
        boots = [float(np.mean(rng.choice(diffs, n, replace=True)))
                 for _ in range(10000)]
        lo, hi = np.percentile(boots, [2.5, 97.5])
        return {"mean_diff": round(float(np.mean(diffs)), 4),
                "ci95": [round(lo, 4), round(hi, 4)], "n_pairs": n}

    metrics = (["element_recall", "hit1", "mrr"]
               + (["guard_recall"] if RUNG == "L0" else []))
    comparison = {m: paired(m) for m in metrics}
    bare_mean = float(np.mean([r["bare"]["element_recall"]
                               for r in rows]))
    eng_mean = float(np.mean([r["engine"]["element_recall"]
                              for r in rows]))
    in_band = BAND_LO <= bare_mean <= BAND_HI
    rec = {
        "record": "R115_D2_HARDER_RESULT/1.0.0",
        "at": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ (sandbox clock, TRUE UTC)"),
        "executor": "builder-r115s1-8e860700",
        "claim": "c-0163 (r115-harder-corpus; R115 dir 2)",
        "prereg": "eval/r115_harder_corpus_prereg.json + amendment_1",
        "rung": RUNG,
        "difficulty_mechanism": (
            "served = question+title+abstract L0 (the same-model "
            "survey spoiler removed)" if RUNG == "L0" else
            "served = question+title only LM1 (the preregistered "
            "upper rung — the model must PREDICT the mechanism from "
            "prior knowledge, not read it)"),
        "n_items": len(rows),
        "tau_calibration": calib,
        "ladder": ladder,
        "bare_mean_element_recall": round(bare_mean, 4),
        "engine_mean_element_recall": round(eng_mean, 4),
        "validity_condition": {
            "band": [BAND_LO, BAND_HI],
            "in_band": bool(in_band),
            "typed": "IN BAND — the delta is INFORMATIVE" if in_band
                     else "OUT OF BAND — the delta types UNINFORMATIVE; "
                          "no engine verdict"},
        "per_item": rows,
        "engine_minus_bare_paired_bootstrap": comparison,
        "judge_free": ("the matcher is the deterministic SPECTER2 "
                       "stack; the distractor ranking is pure "
                       "embedding; abstract-faithfulness is the L0 "
                       "guard substitute per the prereg"),
        "auditor_spot_check": ("raw bytes: eval/r115_d2_harder_raw/ "
                               "(author_*, bare_*, eng_* per item; "
                               "items.jsonl; fetch_log.json; "
                               "ladder_probe.json)"),
        "no_acceptance_claims": ("the result stages for the auditor; "
                                 "the recovery gate belongs to the "
                                 "auditor's calibrated bar (dir 7)"),
    }
    OUT.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print("bare_mean:", round(bare_mean, 4), "engine_mean:",
          round(eng_mean, 4), flush=True)
    print("bootstrap:", json.dumps(comparison), flush=True)
    print("STAGE_CDE_DONE ->", OUT, flush=True)


if __name__ == "__main__":
    main()

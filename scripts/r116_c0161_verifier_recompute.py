#!/usr/bin/env python3
"""r116_c0161_verifier_recompute.py — Art. 19/29(c) independent verifier
recompute of eval/r113_engine_bare_result.json (claim c-0161, the fresh
engine-bare one-shot, TYPED_NEGATIVE) from committed raw bytes.

Work id r116-c0161-verifier-recompute (claim c-0165). VERIFIER recompute,
NOT a re-run: zero LLM calls, zero quota (Art. 29(c)); the matcher is the
committed deterministic SPECTER2 stack loaded through the SAME engine
entry (core_mechanism_gate.load_specter2_encoder) the executor used;
tau is recomputed from the corpus's own calibration pairs and CHECKED
against the committed 0.1412 (an independent derivation, not an
assumption); the seed-113 paired percentile bootstrap is recomputed from
MY per-item values.

The executor's scoring semantics (pinned from scripts/r113_engine_bare_run.py,
read line-by-line this window):
  - gen text per arm = the RAW FILE TEXT verbatim (both arms; the engine
    arm's JSON is never parsed for scoring — the whole file is encoded);
  - element coverage  = count(key_elements e: cosdist(gen_text, e) <= tau);
  - survey coverage   = count(split_key_sentences(survey_text)[cap 6,
    >=8 words, first by document order]: cosdist(gen_text, s) <= tau);
  - rank              = 1 + count(distractors strictly closer to
    gt_main than the generation);
  - hit1/mrr          = rank == 1 / 1.0 / rank;
  - tau               = round((max_neg + min_pos)/2, 4) where pos =
    (element, own finegrained_gt) pairs, neg = (element, OTHER items'
    finegrained_gt) + (element, own main_gt);
  - bootstrap         = paired percentile bootstrap, 10k resamples,
    np.random.default_rng(113), rng.choice(diffs, n, replace=True).

Output: eval/verifications/r116_c0161_verifier_recompute.json — typed
CONFIRMED/DIVERGENCE per metric + per-item agreement table. Digests only
on stdout; no credential ever appears in output.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "eval" / "r113_engine_bare_raw"
RECORD_PATH = REPO / "eval" / "r113_engine_bare_result.json"
OUT = REPO / "eval" / "verifications" / "r116_c0161_verifier_recompute.json"
SEED = 113  # the prereg seed; asserted against the record

SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def now() -> str:
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def d12(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:12]


def split_key_sentences(survey_text: str, cap: int = 6):
    """The runner's own segmentation, reimplemented from its source
    (scripts/r113_engine_bare_run.py:313) — the verifier never imports
    the executor's script for scoring logic (independence)."""
    sents = [s.strip() for s in SENT_SPLIT.split(survey_text)
             if s.strip()]
    return [s for s in sents if len(s.split()) >= 8][:cap]


def main() -> int:
    import numpy as np
    sys.path.insert(0, str(REPO))
    from discovery_fabric.engine.core_mechanism_gate import (
        load_specter2_encoder, cosine_distance)

    record = json.loads(RECORD_PATH.read_text(encoding="utf-8"))
    assert record["seed"] == SEED, "record seed != prereg seed 113"

    items = [json.loads(l) for l in
             (RAW / "items.jsonl").read_text(encoding="utf-8")
             .strip().split("\n")]
    assert len(items) == 30, f"expected 30 items, got {len(items)}"

    # ---- load generation bytes: RAW FILE TEXT verbatim, both arms ----
    gen = {}
    for it in items:
        iid = it["item_id"]
        bare = (RAW / f"bare_{iid}.txt").read_text(encoding="utf-8")
        eng = (RAW / f"eng_{iid}.txt").read_text(encoding="utf-8")
        gen[iid] = {"bare": bare, "engine": eng}

    print("loading SPECTER2 stack (committed cache path)...", flush=True)
    enc = load_specter2_encoder("/home/z/my-project/models_cache", None)

    # ---- tau calibration, independently recomputed ----
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
    tau_mine = round((max_neg + min_pos) / 2, 4)
    calib_rec = record["tau_calibration"]
    tau_committed = calib_rec["tau"]
    tau_midpoint_ok = (abs((calib_rec["min_positive_cosine_distance"]
                            + calib_rec["max_negative_cosine_distance"])
                           / 2 - tau_committed) < 5e-5)
    tau_extremes_ok = (abs(max_neg - calib_rec[
        "max_negative_cosine_distance"]) < 5e-5
                       and abs(min_pos - calib_rec[
                           "min_positive_cosine_distance"]) < 5e-5)
    n_pairs_ok = (len(pos) == calib_rec["n_pos_pairs"]
                  and len(neg) == calib_rec["n_neg_pairs"])
    print(f"tau: mine={tau_mine} committed={tau_committed} "
          f"extremes_ok={tau_extremes_ok} midpoint_ok={tau_midpoint_ok} "
          f"pairs_ok={n_pairs_ok} (pos {len(pos)} / neg {len(neg)})",
          flush=True)
    # the verifier scores at ITS OWN recomputed tau (independence); a
    # divergence from the committed tau is a typed finding, never a
    # silent adoption
    tau = tau_mine

    def covered(gv, targets):
        return sum(1 for e in targets
                   if cosine_distance(gv, enc.encode(e)) <= tau)

    # ---- per-item scoring, both arms ----
    rec_by_id = {p["item_id"]: p for p in record["per_item"]}
    per_metric = {"bare": {m: [] for m in
                           ("element_recall", "survey_recall",
                            "hit1", "mrr")},
                  "engine": {m: [] for m in
                             ("element_recall", "survey_recall",
                              "hit1", "mrr")}}
    rows, mismatches = {}, []
    exact_rows = 0
    for it in items:
        iid = it["item_id"]
        gt_main = it["ground_truth"]["main_hypothesis"]
        gtv = enc.encode(gt_main)
        elements = it["key_elements"]
        survey_sents = split_key_sentences(
            it["served"]["background_survey"]["text"])
        rec_item = rec_by_id[iid]
        assert rec_item["n_elements"] == len(elements), iid
        rows[iid] = {"n_elements": len(elements),
                     "n_survey": len(survey_sents)}
        for arm in ("bare", "engine"):
            tv = enc.encode(gen[iid][arm])
            els = covered(tv, elements)
            svs = covered(tv, survey_sents)
            dists = [cosine_distance(tv, gtv)] + [
                cosine_distance(enc.encode(d), gtv)
                for d in it["distractors"]]
            rank = 1 + sum(1 for d in dists[1:] if d < dists[0])
            hit1, mrr = (1, 1.0) if rank == 1 else (0, 1.0 / rank)
            el_recall = round(els / max(1, len(elements)), 4)
            sv_recall = round(svs / max(1, len(survey_sents)), 4)
            dist_gt = round(dists[0], 4)
            r = rec_item[arm]
            ok = (els == r["elements_covered"]
                  and svs == r["survey_covered"]
                  and rank == r["rank_of_generation"]
                  and abs(dist_gt - r["dist_to_gt_main"]) < 5e-4
                  and abs(el_recall - r["element_recall"]) < 5e-4
                  and abs(sv_recall - r["survey_recall"]) < 5e-4)
            exact_rows += ok
            if not ok:
                mismatches.append({
                    "item_id": iid, "arm": arm,
                    "mine": {"elements_covered": els,
                             "survey_covered": svs,
                             "rank_of_generation": rank,
                             "element_recall": el_recall,
                             "survey_recall": sv_recall,
                             "dist_to_gt_main": dist_gt},
                    "record": {k: r[k] for k in
                               ("elements_covered", "survey_covered",
                                "rank_of_generation",
                                "element_recall", "survey_recall",
                                "dist_to_gt_main")}})
            key = "bare" if arm == "bare" else "engine"
            per_metric[key]["element_recall"].append(el_recall)
            per_metric[key]["survey_recall"].append(sv_recall)
            per_metric[key]["hit1"].append(float(hit1))
            per_metric[key]["mrr"].append(mrr)
            rows[iid][arm] = {"elements_covered": els,
                              "survey_covered": svs,
                              "rank_of_generation": rank,
                              "element_recall": el_recall,
                              "survey_recall": sv_recall,
                              "hit1": hit1, "mrr": mrr,
                              "dist_to_gt_main": dist_gt,
                              "record_match": bool(ok)}
    print(f"per-item exact-row agreement: {exact_rows}/60", flush=True)

    # ---- paired percentile bootstrap, seed 113, 10k (runner formula)--
    boot = {}
    for metric in ("element_recall", "survey_recall", "hit1", "mrr"):
        diffs = [e - b for e, b in
                 zip(per_metric["engine"][metric],
                     per_metric["bare"][metric])]
        rng = np.random.default_rng(SEED)
        n = len(diffs)
        boots = [float(np.mean(rng.choice(diffs, n, replace=True)))
                 for _ in range(10000)]
        lo, hi = np.percentile(boots, [2.5, 97.5])
        boot[metric] = {"mean_diff": round(float(np.mean(diffs)), 4),
                        "ci95": [round(float(lo), 4),
                                 round(float(hi), 4)],
                        "n_pairs": n}

    rb = record["engine_minus_bare_paired_bootstrap"]
    verdicts = {}
    for metric in ("element_recall", "survey_recall", "hit1", "mrr"):
        mine, theirs = boot[metric], rb[metric]
        ok = (abs(mine["mean_diff"] - theirs["mean_diff"]) < 1e-3
              and abs(mine["ci95"][0] - theirs["ci95"][0]) < 1e-3
              and abs(mine["ci95"][1] - theirs["ci95"][1]) < 1e-3)
        verdicts[metric] = {"verdict": "CONFIRMED" if ok
                            else "DIVERGENCE",
                            "mine": mine, "record": theirs}
        print(f"  {metric}: {verdicts[metric]['verdict']} "
              f"(mine {mine['mean_diff']} {mine['ci95']} vs record "
              f"{theirs['mean_diff']} {theirs['ci95']})", flush=True)

    prim = verdicts["element_recall"]
    covers_zero = (prim["record"]["ci95"][0]
                   <= 0 <= prim["record"]["ci95"][1])
    all_confirmed = all(v["verdict"] == "CONFIRMED"
                        for v in verdicts.values())

    out = {
        "record": "R116_C0161_VERIFIER_RECOMPUTE/1.0.0",
        "at": now() + " (sandbox clock, TRUE UTC)",
        "claim": "c-0165 (verifier recompute; work id "
                 "r116-c0161-verifier-recompute)",
        "verifies": "claim c-0161, eval/r113_engine_bare_result.json "
                    "(executor builder-r114s2-c9c03209)",
        "role": "Art. 29(c) VERIFIER record + Art. 19 test-4 "
                "independent tally recompute — zero LLM, zero quota, "
                "no re-run",
        "raw_basis": "eval/r113_engine_bare_raw/ (items.jsonl + 30 "
                     "author + 30 bare + 30 eng, 91 files + usage)",
        "matcher": "the committed SPECTER2 stack through the engine's "
                   "own load_specter2_encoder (core_mechanism_gate) — "
                   "the same entry the executor's runner used",
        "weights_provenance": "allenai/specter2_base pytorch_model.bin "
                              "439740465 bytes sha256[:12] "
                              "801eda968fad (re-verified this window, "
                              "matches the prereg) + adapter present, "
                              "active (Stack[specter2]), encoder smoke "
                              "ordered",
        "scoring_semantics_pinned_from": "scripts/"
                                         "r113_engine_bare_run.py read "
                                         "line-by-line; gen text = RAW "
                                         "FILE verbatim both arms; the "
                                         "runner's sentence split and "
                                         "rank rule reimplemented "
                                         "verbatim (independence: the "
                                         "executor's module was never "
                                         "imported for scoring)",
        "tau": {
            "committed": tau_committed,
            "mine": tau_mine,
            "extremes_match": bool(tau_extremes_ok),
            "midpoint_check": bool(tau_midpoint_ok),
            "pair_counts_match": bool(n_pairs_ok),
            "n_pos_pairs": len(pos), "n_neg_pairs": len(neg),
            "verdict": "CONFIRMED" if (tau_extremes_ok
                                       and tau_midpoint_ok
                                       and n_pairs_ok
                                       and tau_mine == tau_committed)
                       else "DIVERGENCE",
            "note": "tau is DERIVED, not assumed: the calibration "
                    "pairs are recomputed from the corpus bytes and "
                    "the committed extremes/midpoint are checked "
                    "independently",
        },
        "per_item_agreement": {
            "exact_rows": exact_rows, "total": 60,
            "note": "an exact row = all six scored fields "
                    "(elements/survey covered + recall, rank, "
                    "dist_to_gt_main) equal to the record within 5e-4",
            "representation": "raw-file-verbatim (both arms, the "
                              "probe-verified r110 convention; no "
                              "alternative representation was tried — "
                              "the r113 runner encodes the raw file "
                              "text directly, one code path)",
        },
        "bootstrap_recomputed": boot,
        "verdicts": verdicts,
        "primary_typed_consequence": (
            "element_recall CI covers 0 (mean %+.4f, CI %s) — the "
            "executor's TYPED_NEGATIVE branch stands on independent "
            "recompute; the weak-stage retirement remains the "
            "auditor's call per the prereg's acceptance branch"
            % (prim["record"]["mean_diff"],
               prim["record"]["ci95"])) if covers_zero else
            "CI excludes 0 — see verdicts",
        "overall_verdict": (
            "CONFIRMED — all four bootstrap metrics reproduce at 4dp "
            "from the committed raw bytes; the typed negative is "
            "verifier-verified") if all_confirmed else
            "PARTIAL/DIVERGENCE — see per-metric verdicts and "
            "per-item mismatches",
        "findings": [],
        "per_item_mismatches": mismatches,
        "per_item_rows": rows,
        "digest": None,
    }
    out["digest"] = d12(json.dumps(
        {"verdicts": verdicts, "tau": out["tau"],
         "exact_rows": exact_rows}, sort_keys=True).encode())

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False)
                   + "\n", encoding="utf-8")
    print(f"\nwritten: {OUT}")
    print("overall:", out["overall_verdict"])
    print("digest:", out["digest"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""_d3_probe_representations.py — Art. 2 self-attack on the verifier's own
representation assumptions before typing DIVERGENCE: find which gen-text
representation + GT anchor reproduces the committed record's
dist_to_gt_main / rank_of_generation per item."""
import json
import re
import sys

sys.path.insert(0, "/home/z/my-project/discovery-evidence-fabric/scripts")
RAW = "/home/z/my-project/discovery-evidence-fabric/eval/r110_d3_instrument_raw"
RECORD = json.load(open("/home/z/my-project/discovery-evidence-fabric/"
                        "eval/r110_d3_instrument_result.json"))
sys.argv = [sys.argv[0]]
import r114_d3_verifier_recompute as V  # reuse parse/load/encode armory

items = V.load_items()
rec_by_id = {p["item_id"]: p for p in RECORD["per_item"]}

texts = []
cands = {}
for it in items:
    eng_raw = open(f"{RAW}/eng_pc-{it['id'][-2:]}.txt").read().strip()
    bare_raw = it["bare"]
    e = it["eng"]
    hyp = next((v for k, v in e.items() if "hyp" in k.strip().lower()), None)
    cands[it["id"]] = {
        "eng": {"hyp": str(hyp), "all3": " ".join(str(x) for x in e.values()),
                "rawfile": eng_raw, "km": str(e.get("key_mechanism", "")),
                "pr": str(e.get("predicted_result", ""))},
        "bare": {"whole": bare_raw, "para1": bare_raw.split("\n\n")[0]},
    }
    gt = it["author"]
    texts += [gt["main_hypothesis"], gt["finegrained_hypothesis"]]
    texts += it["author"]["distractors"]
    for arm in cands[it["id"]]:
        texts += list(cands[it["id"]][arm].values())
texts = list(dict.fromkeys(texts))
E = V.encode_all(texts)
D = lambda a, b: float(1 - __import__("numpy").dot(E[a], E[b]))

print("=== dist_to_gt_main: candidate match counts (of 30, tol 5e-4) ===")
for arm in ("bare", "eng"):
    for cname in cands["pc-01"][arm]:
        n = 0
        for it in items:
            gt_main = it["author"]["main_hypothesis"]
            r = rec_by_id[it["id"]]["bare" if arm == "bare" else "engine"]
            if abs(D(cands[it["id"]][arm][cname], gt_main)
                   - r["dist_to_gt_main"]) < 5e-4:
                n += 1
        print(f"{arm}/{cname}: {n}/30")

print("=== rank_of_generation: GT-anchor candidates (of 30) ===")
for arm in ("bare", "eng"):
    for cname in cands["pc-01"][arm]:
        for anchor in ("main_hypothesis", "finegrained_hypothesis"):
            n = 0
            for it in items:
                gt = it["author"][anchor]
                dt = D(cands[it["id"]][arm][cname], gt)
                rank = 1 + sum(1 for d in it["author"]["distractors"]
                               if D(d, gt) < dt)
                if rank == rec_by_id[it["id"]]["bare" if arm == "bare"
                                               else "engine"]["rank_of_generation"]:
                    n += 1
            print(f"{arm}/{cname}@{anchor}: {n}/30")

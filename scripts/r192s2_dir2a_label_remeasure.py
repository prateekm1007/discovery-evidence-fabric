#!/usr/bin/env python3
"""R192S2 DIR 2a: the locked-selector re-measure over the committed 48
labels — ZERO new LLM bytes (the owner's accept: "clean-pick and
novel-pick counts FROM BYTES, >=7/8 both").

Selector (owner-fixed, never tuned): pool = departure -> relaxation ->
contradiction (plain deleted, baseline out of the pool); pick the FIRST
pool arm whose label is clean (serious_error=False); if none is clean
in the pool, the item is a NO_CLEAN_PICK item (the pick declines —
item 05 is the owner-declared generation frontier). Clean-pick = the
picked arm is clean; novel-pick = the picked arm is a pool (novel
strategy) arm; mean rank = mean auditor_rank_of_6 over picked arms.

Cross-checks the owner's committed sweep target: 7/8 clean, 7/8
novel-eligible, mean rank 2.29. No labels are re-derived; this is an
Art. 7 recompute from the owner-delivered bytes.
"""
import json, sys

d = json.load(open("eval/auditor_error_labels_dev.json"))
rows = d["rows"]
POOL = ("departure", "relaxation", "contradiction")
by_item = {}
for r in rows:
    by_item.setdefault(r["item_id"], {})[r["arm"]] = r

n_clean = n_novel = 0
ranks = []
detail = []
for item in sorted(by_item):
    arms = by_item[item]
    pick = None
    for arm in POOL:
        lab = arms[arm]["label"]
        if not lab.get("serious_error"):
            pick = arm
            break
    if pick:
        n_clean += 1
        n_novel += 1
        rank = arms[pick]["label"]["auditor_rank_of_6"]
        ranks.append(rank)
        clean_all = [a for a in d["arm_order"]
                     if not arms[a]["label"].get("serious_error")]
        detail.append({"item": item, "pick": pick, "rank_of_6": rank,
                       "rule": "FIRST_CLEAN",
                       "clean_arms_all6": clean_all})
    else:
        clean_any = [a for a in d["arm_order"]
                     if not arms[a]["label"].get("serious_error")]
        detail.append({"item": item, "pick": None, "rank_of_6": None,
                       "rule": "NO_CLEAN_PICK",
                       "clean_arms_all6": clean_any})

mean_rank = sum(ranks) / len(ranks) if ranks else None
summary = {
    "record": "R192S2_DIR2A_LABEL_REMEASURE/1.0.0",
    "instrument": "locked selector over the committed 48 labels (zero new LLM bytes)",
    "pool": list(POOL),
    "clean_picks": n_clean, "novel_picks": n_novel,
    "mean_rank_of_6": round(mean_rank, 3) if mean_rank is not None else None,
    "owner_committed_sweep_target": {"clean": 7, "novel": 7,
                                     "mean_rank": 2.29},
    "matches_owner": (n_clean == 7 and n_novel == 7
                      and mean_rank is not None
                      and abs(mean_rank - 2.29) <= 0.02),
    "per_item": detail,
}
with open("eval/r192s2_dir2a_label_remeasure.json", "w",
          encoding="utf-8") as fh:
    json.dump(summary, fh, indent=1, ensure_ascii=False)
    fh.write("\n")
print(json.dumps({k: summary[k] for k in
                  ("clean_picks", "novel_picks", "mean_rank_of_6",
                   "owner_committed_sweep_target", "matches_owner")},
                 indent=1))
for x in detail:
    print(f"  {x['item']}: pick={x['pick']} rank={x['rank_of_6']} "
          f"clean_all6={x['clean_arms_all6']}")
sys.exit(0 if summary["matches_owner"] else 1)

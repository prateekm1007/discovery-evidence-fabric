#!/usr/bin/env python3
"""r136s2_f31f_cluster_rescore.py — ITEM-CLUSTERED re-score of the F31f
replication (claim c-0217; zero LLM; committed bytes only).

ADAPTED COPY of scripts/r128_cluster_rescore.py (the owner-directed
clustering convention the auditor's dir-6 gate names): the 24 rows
(12 items x 2 draws) are resampled at the ITEM level — each resampled
item contributes BOTH its draws' paired diffs, so the interval is the
honest width for n=12 clusters. Row-level bootstrap reproduced for
continuity. Seed 131 (the fresh-set lineage 123/124/125/127/129 -> 131,
disclosed in the prereg). Sign test on discordant rows (heals vs
breaks). Per-class table (the >=3-nonzero-bare-classes gate).
"""
from __future__ import annotations

import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from r121_successor_score import bill_defect_classes  # canonical detector

REPO = Path(__file__).resolve().parent.parent
RUN = REPO / "eval" / "r136s2_f31f_run"
SET = REPO / "eval" / "r136s2_f31f_set" / "items.jsonl"
B = 10000
SEED = 131

items = {json.loads(l)["problem_id"]: json.loads(l)
         for l in SET.read_text().splitlines() if l.strip()}

rows = {}
for f in sorted(RUN.glob("bare_d?_bench-*.txt")):
    pid = f.stem[len("bare_d1_"):] if f.stem.startswith("bare_d1_") \
        else f.stem[len("bare_d2_"):]
    draw = f.stem.split("_")[1]
    rows[(pid, draw)] = {"bare": f.read_text(encoding="utf-8")}
for f in sorted(RUN.glob("succ_d?_bench-*.json")):
    pid = f.stem[len("succ_d1_"):] if f.stem.startswith("succ_d1_") \
        else f.stem[len("succ_d2_"):]
    draw = f.stem.split("_")[1]
    rec = json.loads(f.read_text(encoding="utf-8"))
    assert rec["authored_bill"] == rows[(pid, draw)]["bare"], (
        f"{pid}/{draw}: authored bill != committed bare bytes")
    rows[(pid, draw)]["succ"] = rec["delivered_bill"]

pairs = []
for pid, prob in items.items():
    for draw in ("d1", "d2"):
        r = rows[(pid, draw)]
        pairs.append({
            "pid": pid, "draw": draw,
            "bare_classes": bill_defect_classes(prob, r["bare"]),
            "succ_classes": bill_defect_classes(prob, r["succ"]),
        })

by_pid = {}
for p in pairs:
    by_pid.setdefault(p["pid"], []).append(p)


def mean(xs):
    return sum(xs) / len(xs)


def row_boot(seed):
    diffs = [float(bool(p["bare_classes"])) - float(bool(p["succ_classes"]))
             for p in pairs]
    rng = random.Random(seed)
    out = []
    n = len(diffs)
    for _ in range(B):
        out.append(mean([diffs[rng.randrange(n)] for _ in range(n)]))
    out.sort()
    return out


def cluster_boot(seed):
    pids = sorted(by_pid)
    rng = random.Random(seed)
    out = []
    for _ in range(B):
        samp = []
        for _ in range(len(pids)):
            pid = pids[rng.randrange(len(pids))]
            for p in by_pid[pid]:
                samp.append(float(bool(p["bare_classes"]))
                            - float(bool(p["succ_classes"])))
        out.append(mean(samp))
    out.sort()
    return out


def ci(boots):
    return [round(boots[int(0.025 * B)], 4),
            round(boots[int(0.975 * B) - 1], 4)]


rb, cb = row_boot(SEED), cluster_boot(SEED)
diffs = [float(bool(p["bare_classes"])) - float(bool(p["succ_classes"]))
         for p in pairs]
discordant = [(p["pid"], p["draw"]) for p, d in zip(pairs, diffs) if d != 0]
heals = sum(1 for p, d in zip(pairs, diffs) if d > 0)
breaks = sum(1 for p, d in zip(pairs, diffs) if d < 0)
n_disc = len(discordant)
# exact two-sided binomial sign test
from math import comb
if n_disc:
    k = max(heals, breaks)
    if 2 * k == n_disc:
        p_two = 1.0  # symmetric split: two-sided p is maximal
    else:
        tail = sum(comb(n_disc, i) for i in range(k, n_disc + 1)) \
            / (2 ** n_disc)
        p_two = min(1.0, 2.0 * tail)
else:
    p_two = 1.0

per_class_bare, per_class_succ = Counter(), Counter()
for p in pairs:
    per_class_bare.update(p["bare_classes"])
    per_class_succ.update(p["succ_classes"])
classes_all = ["input_availability", "duty_pricing",
               "constraint_violation", "physics_direction_inversion"]
nonzero_bare = [c for c in classes_all if per_class_bare.get(c, 0) > 0]

record = {
    "record": "R136S2_F31F_CLUSTERED_RESCORE/1.0.0",
    "claim": "c-0217",
    "source_bytes": "eval/r136s2_f31f_run/{bare,succ}_d{1,2}_bench-*.txt|json",
    "detector": "canonical bill_defect_classes (unchanged bytes)",
    "n_rows": len(pairs),
    "n_items": len(by_pid),
    "n_clusters": len(by_pid),
    "bare_rows": sum(1 for p in pairs if p["bare_classes"]),
    "succ_rows": sum(1 for p in pairs if p["succ_classes"]),
    "bare_rate": round(sum(1 for p in pairs if p["bare_classes"])
                       / len(pairs), 4),
    "succ_rate": round(sum(1 for p in pairs if p["succ_classes"])
                       / len(pairs), 4),
    "paired_mean_diff": round(mean(diffs), 4),
    "row_level_ci95": ci(rb),
    "item_clustered_ci95": ci(cb),
    "bootstrap": {"B": B, "seed": SEED,
                  "seed_lineage_note": "fresh-set lineage 123/124/125/"
                                       "127/129; F31f replication 131"},
    "sign_test": {"n_discordant": n_disc, "heals": heals,
                  "breaks": breaks,
                  "p_two_sided_exact": round(p_two, 6)},
    "per_class": {c: {"bare": per_class_bare.get(c, 0),
                      "succ": per_class_succ.get(c, 0)}
                  for c in classes_all},
    "gates": {
        "treated_rate_le_0.25": sum(1 for p in pairs
                                    if p["succ_classes"]) / len(pairs)
        <= 0.25,
        "damage_le_0.25": (
            sum(1 for p in pairs if not p["bare_classes"]
                and [c for c in p["succ_classes"]
                     if c not in p["bare_classes"]]) / len(pairs)) <= 0.25,
        "ge3_classes_nonzero_bare": len(nonzero_bare) >= 3,
        "nonzero_bare_classes": nonzero_bare,
    },
    "discordant_rows": [{"pid": pid, "draw": draw}
                        for (pid, draw) in discordant],
}
(RUN / "clustered_rescore.json").write_text(
    json.dumps(record, indent=1, ensure_ascii=False) + "\n",
    encoding="utf-8")
print(json.dumps({k: record[k] for k in
                  ("n_rows", "n_clusters", "bare_rate", "succ_rate",
                   "paired_mean_diff", "row_level_ci95",
                   "item_clustered_ci95", "sign_test", "gates")},
                 indent=1))

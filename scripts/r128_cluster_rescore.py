#!/usr/bin/env python3
"""R128 dir-2 (owner): ITEM-CLUSTERED re-score of the F31e result.

The owner's finding: the accepted score-9 axis pooled 48 rows that come
from only 24 ITEMS (two draws each); the accepted paired bootstrap
resampled ROWS, which treats the two draws of one item as independent
evidence. The row-level interval is therefore anti-conservative when
per-item difficulty varies (an easy item heals in both draws and its two
heals are correlated evidence).

This script re-scores from committed bytes ONLY (zero LLM):
  1. per-row defect vectors under the canonical detector (bill_defect_classes,
     unchanged bytes 92485038719557e4), for both draws x both arms;
  2. the row-level (unclustered) paired bootstrap — reproduces the accepted
     number for continuity;
  3. the ITEM-CLUSTERED paired bootstrap (resample the 24 items with
     replacement; each resampled item contributes BOTH its draws' paired
     diffs; every item carries exactly 2 rows, so mean-of-rows over
     resampled items == mean-of-cluster-means);
  4. the exact sign test on the discordant rows (heals vs breaks);
  5. the per-class table (dir 6: the claim is CLASS-RESTRICTED).
Art. 14 note: n=24 clusters is the set the axis was accepted on; the
clustered width is the honest width for THAT n — a fresh non-builder set
(dir 3) is the power fix, not a bigger bootstrap.
Seeds: the fresh-set lineage is 123/124/125/127; this re-score uses 129
(disclosed in the record).
"""
import json
import random
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from r121_successor_score import bill_defect_classes  # canonical detector

REPO = Path(__file__).resolve().parent.parent
RUN = REPO / "eval" / "r125_f31e_run"
SET = REPO / "eval" / "r125_f31e_set" / "items.jsonl"
B = 10000
SEED = 129

items = {json.loads(l)["problem_id"]: json.loads(l) for l in SET.read_text().splitlines() if l.strip()}

# ---- per-row defects from committed bytes --------------------------------
rows = {}  # (item, draw) -> {"bare": set, "succ": set}
for f in sorted(RUN.glob("bare_d?_r125-*.txt")):
    _, draw, pid = f.stem.split("_", 2)  # e.g. bare_d1_r125-01-s1
    rows.setdefault((pid, draw), {})["bare"] = bill_defect_classes(
        items[pid], f.read_text())
for f in sorted(RUN.glob("succ_d?_r125-*.json")):
    _, draw, pid = f.stem.split("_", 2)
    rec = json.loads(f.read_text())
    bill = rec["delivered_bill"]
    rows.setdefault((pid, draw), {})["succ"] = bill_defect_classes(items[pid], bill)

missing = [k for k, v in rows.items() if set(v) != {"bare", "succ"}]
assert not missing, f"rows missing an arm: {missing[:5]} (n={len(rows)})"
draws = sorted({d for (_, d) in rows})
print(f"rows: {len(rows)} | draws: {draws}")

bare_n = sum(1 for r in rows.values() if r["bare"])
succ_n = sum(1 for r in rows.values() if r["succ"])
print(f"bare defective rows: {bare_n}/48 ({bare_n/48:.4f})")
print(f"succ defective rows: {succ_n}/48 ({succ_n/48:.4f})")

# per-class tables (dir 6)
cls_bare, cls_succ = Counter(), Counter()
for r in rows.values():
    cls_bare.update(r["bare"])
    cls_succ.update(r["succ"])
print("per-class (bare -> succ):",
      {c: (cls_bare[c], cls_succ[c]) for c in sorted(set(cls_bare) | set(cls_succ))})

# ---- paired diffs --------------------------------------------------------
pairs = []  # (pid, draw, diff)
for (pid, draw), r in sorted(rows.items()):
    diff = int(bool(r["bare"])) - int(bool(r["succ"]))
    pairs.append((pid, draw, diff))
mean_diff = statistics.mean(d for _, _, d in pairs)
print(f"paired mean diff (rows): {mean_diff:.4f}")

# ---- row-level bootstrap (reproduces the accepted interval) --------------
rng = random.Random(SEED)
diffs = [d for _, _, d in pairs]
boot_rows = []
for _ in range(B):
    boot_rows.append(statistics.mean(rng.choice(diffs) for _ in diffs))
boot_rows.sort()
lo_r = boot_rows[int(0.025 * B)]
hi_r = boot_rows[int(0.975 * B) - 1]
print(f"ROW-level CI95 (seed {SEED}): [{lo_r:+.4f}, {hi_r:+.4f}]")

# ---- ITEM-CLUSTERED bootstrap --------------------------------------------
by_item = {}
for pid, draw, d in pairs:
    by_item.setdefault(pid, []).append(d)
pids = sorted(by_item)
assert len(pids) == 24 and all(len(v) == 2 for v in by_item.values()), \
    "expected 24 items x 2 draws (the clustering premise)"
boot_cl = []
for _ in range(B):
    samp = [rng.choice(pids) for _ in range(24)]
    vals = [d for p in samp for d in by_item[p]]  # both draws ride the item
    boot_cl.append(statistics.mean(vals))
boot_cl.sort()
lo_c = boot_cl[int(0.025 * B)]
hi_c = boot_cl[int(0.975 * B) - 1]
print(f"ITEM-CLUSTERED CI95 (seed {SEED}, 24 clusters): [{lo_c:+.4f}, {hi_c:+.4f}]")

# ---- sign test on discordant rows ----------------------------------------
heals = sum(1 for _, _, d in pairs if d == 1)
breaks = sum(1 for _, _, d in pairs if d == -1)
n_disc = heals + breaks
from math import comb
p_two = sum(comb(n_disc, k) for k in range(0, min(heals, breaks) + 1)) / 2 ** n_disc * 2
p_two = min(1.0, p_two)
print(f"discordant rows: {n_disc} (heals {heals}, breaks {breaks}) | "
      f"two-sided exact sign-test p = {p_two:.4f}")

# ---- verdict per the owner's acceptance test -----------------------------
verdict = "AXIS STAYS ACCEPTED (clustered LB > 0)" if lo_c > 0 else \
          "AXIS FAILS THE CLUSTERED GATE (LB <= 0)"
print(f"VERDICT: {verdict}")

# ---- machine-readable record ---------------------------------------------
out = {
    "record": "R128_F31E_CLUSTERED_RESCORE/1.0.0",
    "source_bytes": "eval/r125_f31e_run/{bare,succ}_d{1,2}_r125-*.txt @ 63e692733",
    "detector": "canonical bill_defect_classes (92485038719557e4 bytes, unchanged)",
    "n_rows": 48, "n_items": 24, "n_clusters": 24,
    "bare_rows": bare_n, "succ_rows": succ_n,
    "bare_rate": bare_n / 48, "succ_rate": succ_n / 48,
    "paired_mean_diff": mean_diff,
    "row_level_ci95": [lo_r, hi_r],
    "item_clustered_ci95": [lo_c, hi_c],
    "bootstrap": {"B": B, "seed": SEED,
                  "seed_lineage_note": "fresh-set lineage 123/124/125/127; re-score 129"},
    "sign_test": {"n_discordant": n_disc, "heals": heals, "breaks": breaks,
                  "p_two_sided_exact": p_two},
    "per_class": {c: {"bare": cls_bare[c], "succ": cls_succ[c]}
                  for c in sorted(set(cls_bare) | set(cls_succ))},
    "verdict": verdict,
    "claim_scope": ("CLASS-RESTRICTED (dir 6): the accepted effect is the bind-check + "
                    "reviewer-fix loop reducing UNPRICED-DUTY-CYCLE (duty_pricing) "
                    "defects on the F31e corpus under the fixed input-availability "
                    "detector; it is NOT a general viability claim"),
}
(REPO / "eval" / "r128_f31e_clustered_rescore.json").write_text(
    json.dumps(out, indent=1) + "\n")
print("record written: eval/r128_f31e_clustered_rescore.json")

# ---- dir 5 recompute: the absorbed-backoff figure from committed bytes ----
GATE = REPO / "eval" / "r127_phaseA" / "gate"
lat = []
for f in sorted(GATE.glob("gate_r125-*.json")):
    r = json.loads(f.read_text())
    for c in r.get("calls") or []:
        l = c.get("latency_s")
        if c.get("leg") == "reviewer" and l:
            lat.append((f.stem.replace("gate_", ""), l))
slow = [(p, l) for p, l in lat if l > 100]
print(f"\ndir-5 recompute: reviewer legs with latency > 100 s (each = one absorbed "
      f"120 s backoff + the call): {len(slow)}")
for p, l in slow:
    print(f"   {p}: {l:.2f} s")

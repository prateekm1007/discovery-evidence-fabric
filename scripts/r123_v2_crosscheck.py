#!/usr/bin/env python3
"""r123_v2_crosscheck.py — the INDEPENDENT arithmetic cross-check of
the F31d scoring: every scoring.json number re-derived from the raw
v2 records + committed bare bytes, with the aggregate math
re-implemented here (not imported) and the bootstrap re-run under a
different construction."""
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r121_successor_score import bill_defect_classes  # noqa: E402

items = {json.loads(l)["problem_id"]: json.loads(l)
         for l in (REPO / "eval" / "r123_fresh_set" / "items.jsonl")
         .read_text(encoding="utf-8").strip().split("\n") if l}
RUN = REPO / "eval" / "r123_v2_run"

bare_def, succ_def = [], []
clean_rows = dmg_rows = 0
same_draw_ok = True
for lane in ("replication", "claiming"):
    for pid in sorted(items):
        prob = items[pid]
        if lane == "replication":
            bare = (REPO / "eval" / "r123_fresh_run"
                    / f"bare_{pid}.txt").read_text(encoding="utf-8")
        else:
            bare = json.loads((REPO / "eval"
                               / "r123_fresh_confirmation_run"
                               / f"row_{pid}.json").read_text(
                encoding="utf-8"))["authored_bill"]
        rec = json.loads((RUN / f"v2_{lane}_{pid}.json").read_text(
            encoding="utf-8"))
        assert rec["problem_id"] == pid and rec["lane"] == lane
        if rec["authored_bill"] != bare:
            same_draw_ok = False
        b_cls = bill_defect_classes(prob, bare)
        s_cls = bill_defect_classes(prob, rec["delivered_bill"])
        bare_def.append(bool(b_cls))
        succ_def.append(bool(s_cls))
        if not b_cls:
            clean_rows += 1
            if [c for c in s_cls if c not in b_cls]:
                dmg_rows += 1
n = len(bare_def)
b_rate = sum(bare_def) / n
s_rate = sum(succ_def) / n
damage = dmg_rows / clean_rows
diffs = [float(b) - float(s) for b, s in zip(bare_def, succ_def)]
rng = np.random.default_rng(126)
idx = rng.integers(0, n, size=(10000, n))
boots = [float(np.mean([diffs[i] for i in row])) for row in idx]
lo, hi = np.percentile(boots, [2.5, 97.5])

print(f"same-draw construction byte-verified: {same_draw_ok}")
print(f"n={n} bare={sum(bare_def)}/{n} ({b_rate:.4f}) "
      f"succ_v2={sum(succ_def)}/{n} ({s_rate:.4f}) "
      f"damage={dmg_rows}/{clean_rows} ({damage:.4f})")
print(f"bootstrap(independent construction): mean={np.mean(diffs):.4f} "
      f"CI95=[{lo:.4f},{hi:.4f}]")

sc = json.loads((RUN / "scoring.json").read_text())
p = sc["pooled"]
bt = sc["paired_bootstrap"]
checks = {
    "bare_rate": abs(p["bare_rate"] - b_rate) <= 5e-5 + 1e-9,
    "succ_rate": abs(p["succ_rate"] - s_rate) <= 5e-5 + 1e-9,
    "damage": abs(p["damage"]["rate"] - damage) <= 5e-5 + 1e-9,
    "damage_denominator": p["damage"]["clean_bare_items"] == clean_rows,
    "boot_mean": abs(bt["mean_diff"] - np.mean(diffs)) < 5e-4,
    "boot_lo": abs(bt["ci95"][0] - lo) < 5e-3,
    "boot_hi": abs(bt["ci95"][1] - hi) < 5e-3,
    "gates_recomputed": (
        sc["score9_gates"]["all_three"] ==
        (s_rate <= 0.25 and lo > 0 and damage <= 0.25)),
}
print("cross-check:", checks)
assert all(checks.values()), "CROSS-CHECK MISMATCH"
print("ARITHMETIC CROSS-CHECK: PASS — every scoring.json number "
      "reproduces from the raw bytes under an independent construction")

#!/usr/bin/env python3
"""r125_f31e_crosscheck.py — the INDEPENDENT arithmetic cross-check of
the F31e scoring: every number re-derived from the raw run bytes with
an independent construction (explicit-index bootstrap, independent
aggregates), the same-draw construction verified byte-identical."""
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r121_successor_score import bill_defect_classes  # noqa: E402

items = [json.loads(l) for l in (REPO / "eval" / "r125_f31e_set"
         / "items.jsonl").read_text(encoding="utf-8").strip()
         .split("\n") if l]
RUN = REPO / "eval" / "r125_f31e_run"

bare_def, succ_def = [], []
clean_rows = dmg_rows = 0
same_ok = True
for draw in ("d1", "d2"):
    for prob in items:
        pid = prob["problem_id"]
        bare = (RUN / f"bare_{draw}_{pid}.txt").read_text(
            encoding="utf-8")
        rec = json.loads((RUN / f"succ_{draw}_{pid}.json").read_text(
            encoding="utf-8"))
        if rec["authored_bill"] != bare:
            same_ok = False
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
rng = np.random.default_rng(127)
idx = rng.integers(0, n, size=(10000, n))
boots = [float(np.mean([diffs[i] for i in row])) for row in idx]
lo, hi = np.percentile(boots, [2.5, 97.5])

print(f"same-draw construction byte-verified: {same_ok}")
print(f"n={n} bare={sum(bare_def)}/{n} ({b_rate:.4f}) "
      f"succ={sum(succ_def)}/{n} ({s_rate:.4f}) "
      f"damage={dmg_rows}/{clean_rows} ({damage:.4f})")
print(f"bootstrap(independent): mean={np.mean(diffs):.4f} "
      f"CI95=[{lo:.4f},{hi:.4f}]")

sc = json.loads(Path(sys.argv[1] if len(sys.argv) > 1
                     else str(RUN / "scoring.json")).read_text())
p, bt = sc["pooled"], sc["paired_bootstrap"]
checks = {
    "bare_rate": abs(p["bare_rate"] - b_rate) <= 1e-9 + 5e-5,
    "succ_rate": abs(p["succ_rate"] - s_rate) <= 1e-9 + 5e-5,
    "damage": abs(p["damage"]["rate"] - damage) <= 1e-9 + 5e-5,
    "damage_denominator":
        p["damage"]["clean_bare_items"] == clean_rows,
    "boot_mean": abs(bt["mean_diff"] - np.mean(diffs)) < 5e-4,
    "boot_lo": abs(bt["ci95"][0] - lo) < 5e-3,
    "boot_hi": abs(bt["ci95"][1] - hi) < 5e-3,
    "gates_recomputed": (
        sc["score9_gates"]["all_three"] ==
        (s_rate <= 0.25 and lo > 0 and damage <= 0.25)),
}
print("cross-check:", checks)
assert all(checks.values()), "CROSS-CHECK MISMATCH"
print("ARITHMETIC CROSS-CHECK: PASS")

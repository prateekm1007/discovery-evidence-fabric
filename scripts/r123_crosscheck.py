#!/usr/bin/env python3
"""r123_crosscheck.py — the INDEPENDENT arithmetic cross-check of the
F31c scoring (the auditor's discipline; Art. 1: exact bytes). Re-derives
every number in eval/r123_fresh_run/scoring.json from the RAW artifacts
(the 48 committed files), with the aggregate math re-implemented here
(not imported from the scorer) and the bootstrap re-run under a
re-keyed construction that must agree to <= 0.005 on the percentile
bounds."""
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
         .read_text(encoding="utf-8").strip().split("\n")}
RUN = REPO / "eval" / "r123_fresh_run"

bare_def, succ_def, pairs = [], [], []
for pid in sorted(items):
    prob = items[pid]
    b = (RUN / f"bare_{pid}.txt").read_text(encoding="utf-8")
    rec = json.loads((RUN / f"succ_{pid}.json").read_text(
        encoding="utf-8"))
    assert rec["problem_id"] == pid
    assert rec["authored_bill"] == b, (
        f"{pid}: the successor record's authored bill is NOT the bare "
        "arm's committed bytes (the same-draw construction broke)")
    b_cls = bill_defect_classes(prob, b)
    s_cls = bill_defect_classes(prob, rec["delivered_bill"])
    bare_def.append(bool([c for c in b_cls
                          if not c.startswith("DETECTOR_ERROR")]))
    succ_def.append(bool([c for c in s_cls
                          if not c.startswith("DETECTOR_ERROR")]))
    pairs.append((pid, b_cls, s_cls))

n = len(pairs)
bare_rate = sum(bare_def) / n
succ_rate = sum(succ_def) / n

# damage: clean-bare items where the successor introduced a class
clean = [p for p in pairs if not p[1]]
damaged = [p for p in clean if [c for c in p[2]
                                if c not in p[1]]]
damage = len(damaged) / len(clean)

diffs = [float(b) - float(s) for b, s in zip(bare_def, succ_def)]
rng = np.random.default_rng(123)
idx = rng.integers(0, n, size=(10000, n))  # different construction
boots = [float(np.mean([diffs[i] for i in row])) for row in idx]
lo, hi = np.percentile(boots, [2.5, 97.5])

print(f"n={n} bare_rate={bare_rate:.4f} ({sum(bare_def)}/{n}) "
      f"succ_rate={succ_rate:.4f} ({sum(succ_def)}/{n})")
print(f"damage={damage:.4f} ({len(damaged)}/{len(clean)}) "
      f"damaged={[p[0] for p in damaged]}")
print(f"bootstrap(independent construction): mean={np.mean(diffs):.4f} "
      f"CI95=[{lo:.4f}, {hi:.4f}]")

scoring = json.loads((RUN / "scoring.json").read_text())
s = scoring["delivered_defect_rate"]
d = scoring["damage_gate"]
bt = scoring["paired_bootstrap"]
checks = {
    "bare_rate": abs(s["bare_only"] - bare_rate) <= 5e-5 + 1e-9,
    "succ_rate": abs(s["successor"] - succ_rate) <= 5e-5 + 1e-9,
    "damage": abs(d["rate"] - damage) <= 5e-5 + 1e-9,
    "damage_denominator": d["clean_bare_items"] == len(clean),
    "boot_mean": abs(bt["mean_diff"] - np.mean(diffs)) < 5e-4,
    "boot_lo": abs(bt["ci95"][0] - lo) < 5e-3,
    "boot_hi": abs(bt["ci95"][1] - hi) < 5e-3,
    "per_item_rows": len(scoring["per_item"]) == n,
}
print("cross-check:", checks)
assert all(checks.values()), "CROSS-CHECK MISMATCH"
print("ARITHMETIC CROSS-CHECK: PASS — every scoring.json number "
      "reproduces from the raw bytes under an independent construction")

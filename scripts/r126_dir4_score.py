#!/usr/bin/env python3
"""r126_dir4_score.py — the independent recompute for claim c-0197
(Art. 13: from committed bytes only, zero LLM). Reproduces
eval/r126_dir4_score.json: bare = the committed F31e bare bytes;
succ = the r126_dir4_run delivered_bill; the unmodified wrapper;
seed-127 paired bootstrap."""
import collections
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))
from r121_successor_score import bill_defect_classes  # noqa: E402

SRC = REPO / "eval" / "r125_f31e_run"
OUT = REPO / "eval" / "r126_dir4_run"
items = {json.loads(l)["problem_id"]: json.loads(l)
         for l in (REPO / "eval/r125_f31e_set/items.jsonl")
         .read_text().strip().split("\n") if l}

res = {}
for pid in sorted(items):
    for draw in ("d1", "d2"):
        bare = (SRC / f"bare_{draw}_{pid}.txt").read_text(encoding="utf-8")
        rec = json.loads((OUT / f"succ_{draw}_{pid}.json").read_text())
        res[f"{draw}/{pid}"] = (bill_defect_classes(items[pid], bare),
                                bill_defect_classes(items[pid],
                                                    rec["delivered_bill"]))

per = [int(bool(b)) - int(bool(s)) for b, s in res.values()]
bare_n = sum(bool(b) for b, _ in res.values())
succ_n = sum(bool(s) for _, s in res.values())
cls = collections.Counter(c for _, s in res.values() for c in s)
dam = [k for k, (b, s) in res.items() if not b and s]
clean = [k for k, (b, s) in res.items() if not b]
a = np.array(per, dtype=float)
rng = np.random.default_rng(127)
bs = [float(np.mean(rng.choice(a, len(a), replace=True)))
      for _ in range(10000)]
lo, hi = np.percentile(bs, [2.5, 97.5])
print(f"pooled n={len(per)}: bare {bare_n} succ {succ_n} "
      f"mean {a.mean():.4f} CI95 [{lo:.4f},{hi:.4f}]")
print(f"successor classes: {dict(cls) or '{}'}")
print(f"damage {len(dam)}/{len(clean)} rows: {dam}")
g1 = succ_n < 2 and not cls.get("duty_pricing")
g2 = (len(dam) / len(clean)) <= 0.25
g3 = not cls.get("input_availability") and succ_n <= 2
print(f"g1 duty residual < 2/48: {g1} | g2 damage <= .25: {g2} "
      f"| g3 no regression: {g3}")

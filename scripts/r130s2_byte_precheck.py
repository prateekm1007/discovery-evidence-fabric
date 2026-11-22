#!/usr/bin/env python3
"""r130s2_byte_precheck.py — the Art. 3 byte-consistency pre-check for
the BoN round-2 parity (claim c-0208). ZERO LLM, zero network: re-tally
(1) the incumbent single-shot arm from the COMMITTED F31e succ bytes
    (eval/r125_f31e_run/succ_d{1,2}_*.txt — 48 rows), pin 2/48;
(2) the round-1 bon2 arm from the COMMITTED round-1 records
    (eval/r129_bon_run/bon_*.json — 24 selected rows), pin 0/24.
The prereg is typed only after both pins reproduce. Stale-bytecode
hazard: __pycache__ purged by the caller before this runs."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r121_successor_score import bill_defect_classes  # noqa: E402

items = {}
for line in (REPO / "eval" / "r125_f31e_set" / "items.jsonl") \
        .read_text(encoding="utf-8").strip().split("\n"):
    if line:
        p = json.loads(line)
        items[p["problem_id"]] = p

print(f"items loaded: {len(items)}")

# (1) incumbent from committed bytes (the succ records are JSON)
inc = []
inc_rows = 0
for f in sorted((REPO / "eval" / "r125_f31e_run").glob("succ_d*.json")):
    d = json.loads(f.read_text(encoding="utf-8"))
    inc_rows += 1
    cls = bill_defect_classes(items[d["problem_id"]],
                              d["delivered_bill"])
    if cls:
        inc.append({"pid": d["problem_id"], "draw": d["draw"],
                    "classes": cls})
print(f"incumbent rows recomputed: {inc_rows}")
print(f"incumbent defect rows: {len(inc)} {json.dumps(inc)}")

# (2) round-1 arm from committed bytes
arm = []
arm_rows = 0
arm_fail = []
for f in sorted((REPO / "eval" / "r129_bon_run").glob("bon_*.json")):
    r = json.loads(f.read_text(encoding="utf-8"))
    if r.get("delivered_bill"):
        arm_rows += 1
        cls = bill_defect_classes(items[r["problem_id"]],
                                  r["delivered_bill"])
        if cls:
            arm.append({"pid": r["problem_id"], "classes": cls})
    else:
        arm_fail.append(r["problem_id"])
print(f"round-1 arm selected rows recomputed: {arm_rows} "
      f"(typed-fail items: {arm_fail})")
print(f"round-1 arm defect rows: {len(arm)} {json.dumps(arm)}")

pin_ok = (inc_rows == 48 and len(inc) == 2
          and all(i["classes"] == ["duty_pricing"] and i["draw"] == "d1"
                  for i in inc)
          and arm_rows == 24 and len(arm) == 0)
print(f"PINS {'REPRODUCED' if pin_ok else 'NOT REPRODUCED'} "
      f"(incumbent 2/48 duty_pricing d1 x2; round-1 arm 0/24)")
sys.exit(0 if pin_ok else 1)

#!/usr/bin/env python3
"""R95: design-verification probe — run the REAL r22 base_scan over the
committed v11 answer corpus, extract every BILL_UNTAGGED row, and check
which typed procurement class each row belongs to by the directive's own
definitions. The classifier rules are tuned ON THESE OBSERVED SHAPES, and
the ambiguity rate is COMPUTED (never assumed)."""
import json
import re
import sys
import importlib.util
from pathlib import Path

REPO = Path("/home/z/my-project/discovery-evidence-fabric")
sys.path.insert(0, str(REPO / "scripts"))

spec = importlib.util.spec_from_file_location("r22scan", REPO / "scripts" / "r22_a1w_v5_repair.py")
r22 = importlib.util.module_from_spec(spec)
sys.modules["r22scan"] = r22
spec.loader.exec_module(r22)

# typed class markers (from the r22 REPAIR_DIRECTIVE's own definitions;
# the consequence-row extensions follow the corpus's own committed
# convention — HO10-01's scored answer tags cost/burden rows (a)/(c))
A_RE = re.compile(r"\b(existing|already (present|installed|in place)|no new|"
                  r"rides (entirely )?on|reuses?|uses? the existing|zero|"
                  r"no (new|physical|additional|modifications|hardware|"
                  r"sensors|coatings|installation))\b", re.I)
B_RE = re.compile(r"\b(commercial[- ]grade|commercial|catalog|off-the-shelf|"
                  r"stock|standard (catalog|grade|part)|commodity|"
                  r"procurable|supplier|purchased|procured)\b", re.I)
C_RE = re.compile(r"\b(reconfigure|retune|reprogram|schedule|setpoint|duty|"
                  r"procedure|set \w+ to|switch(ing)?|threshold|interval|"
                  r"mode|adjust|increase|decrease|reduce|raise|lower|"
                  r"retiming|intermittent|pulse|dosing|per (event|cycle|"
                  r"batch)|downtime|dip)\b", re.I)

ev = json.load(open(REPO / "eval/holdout_v11_generation/events.json"))
untagged_rows = []
for e in ev["events"]:
    attempts = e.get("attempts") or []
    last = attempts[-1] if attempts else {}
    finds = (last.get("scan") or {}).get("BILL_UNTAGGED") or []
    for f in finds:
        untagged_rows.append((e["problem_id"], f))

print(f"last-attempt BILL_UNTAGGED flagged rows across v11: {len(untagged_rows)}")
cls = {"a": 0, "b": 0, "c": 0, "ambiguous": 0, "none": 0, "tagged_fmt": 0}
for pid, f in untagged_rows:
    if re.search(r"\(Tag: ?[abc]\)", f):
        cls["tagged_fmt"] += 1
        continue
    if "(a)" in f or "(b)" in f or "(c)" in f:
        continue  # already scannable-tagged (scan state lag in the sample)
    a, b, c = bool(A_RE.search(f)), bool(B_RE.search(f)), bool(C_RE.search(f))
    hits = sum([a, b, c])
    if hits == 1:
        cls["a" if a else "b" if b else "c"] += 1
    elif hits > 1:
        cls["ambiguous"] += 1
    else:
        cls["none"] += 1
print("typed classification:", cls)
print("\nsample flagged rows (last attempt, first 6):")
for pid, f in untagged_rows[:6]:
    a, b, c = bool(A_RE.search(f)), bool(B_RE.search(f)), bool(C_RE.search(f))
    print(f"  [{pid}] a={a} b={b} c={c} :: {f[:110]}")

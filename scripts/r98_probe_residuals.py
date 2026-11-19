#!/usr/bin/env python3
"""R97 ⑥: run the c-0109 classifier over every residual BILL_UNTAGGED
text mined from the sealed v12 ledger (read-only, committed bytes) and
report current verdict + the fired markers. Output drives the typed
vocabulary extension decision table."""
import json, re, sys
from pathlib import Path
_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))
from discovery_fabric.engine.tool_grounded_critic import (
    A_CLASS_RE, B_CLASS_RE, C_ACTION_RE, C_NOUN_RE, classify_bill_row)

led = json.load(open(str(_REPO) + "/eval/holdout_v12_generation/events.json"))
texts = {}
for e in led.get("events", []):
    if e.get("attempts"):
        for t in (e["attempts"][-1].get("scan") or {}).get(
                "BILL_UNTAGGED", []) or []:
            key = t.strip()[:90]
            texts.setdefault(key, t.strip())

def markers(row):
    return [m for m, r in (("a", A_CLASS_RE), ("b", B_CLASS_RE),
                           ("c", C_ACTION_RE)) if r.search(row)], \
           bool(C_NOUN_RE.search(row)), \
           bool(re.search(r"\*{0,2}[^*\n]{1,60}:\s*\*{0,2}\s*$", row))

out = []
for key, full in sorted(texts.items()):
    cls = classify_bill_row(full)
    fired, cnoun, hdr = markers(full)
    out.append((cls, key, fired, cnoun, hdr, full))

from collections import Counter
print("current verdicts:", dict(Counter(c for c, *_ in out)))
print()
for cls, key, fired, cnoun, hdr, full in out:
    tag = cls if cls else ("HDR" if hdr else "NONE")
    print(f"{tag:4s} fired={','.join(fired) or '-'}"
          f"{' +cnoun' if cnoun else ''}{' (header)' if hdr else ''}"
          f"  | {key}")

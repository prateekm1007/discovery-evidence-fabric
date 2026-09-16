#!/usr/bin/env python3
"""R475 — reproduce the operator's three-way proof on the REAL branch
records: the R472 learning-card gate is structurally dead on the killed
class (gate reads final_status against a set holding the OUTCOME name;
killed runs carry final_status = INVENTION_UNDER_DEVELOPMENT).

Population measurement over origin/runtime-state-hf:sessions.json (the
211-session durable state): every COMPLETE session, its final_status
and outcome vocabulary, and what learning_card() returns for each.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from toscanini.run_state import learning_card  # noqa: E402

d = json.load(open("/tmp/r475/sessions.json"))
sess = d.get("sessions", []) if isinstance(d, dict) else d
print(f"total sessions: {len(sess)}")

complete = [s for s in sess if (s.get("status") or "") == "COMPLETE"]
print(f"COMPLETE: {len(complete)}")

from collections import Counter
fs = Counter((s.get("final_status") or "<absent>") for s in complete)
oc = Counter((s.get("outcome") or "<absent>") for s in complete)
print("\nfinal_status distribution (COMPLETE):")
for k, v in fs.most_common():
    print(f"  {v:4d}  {k}")
print("\noutcome distribution (COMPLETE):")
for k, v in oc.most_common():
    print(f"  {v:4d}  {k}")

# the killed class: what the operator says is excluded
killed_fs = [s for s in complete
             if (s.get("final_status") or "") == "INVENTION_UNDER_DEVELOPMENT"]
killed_oc = [s for s in complete
             if (s.get("outcome") or "") == "INVENTION_KILLED_BY_CHALLENGE"]
print(f"\nfinal_status=INVENTION_UNDER_DEVELOPMENT: {len(killed_fs)}")
print(f"outcome=INVENTION_KILLED_BY_CHALLENGE:    {len(killed_oc)}")

# the verdict fields a fixed gate could read
killed = killed_oc or killed_fs
if killed:
    s = killed[0]
    for k in ("final_status", "outcome", "outcome_label", "verdict",
              "package_available", "killed_by", "kill_reason"):
        print(f"  sample {k!r}: {str(s.get(k))[:90]!r}")

# run the REAL function over every COMPLETE session
fires, dead = [], []
for s in complete:
    card = learning_card(dict(s))  # no run_dir: lineage-absent branch records
    (fires if card else dead).append(s)
print(f"\nlearning_card() on branch records: fires={len(fires)} dead={len(dead)}")
from collections import Counter as C
print("fires by final_status:", dict(C((s.get('final_status') or '<absent>') for s in fires)))
print("dead  by final_status:", dict(C((s.get('final_status') or '<absent>') for s in dead)))
print("dead  by outcome:      ", dict(C((s.get('outcome') or '<absent>') for s in dead)))

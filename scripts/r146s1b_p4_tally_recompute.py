#!/usr/bin/env python3
"""R146s1-b: the DIR-4 P4 panel tally + INDEPENDENT recompute (the
driver writes legs; this script recomputes the acceptance from the
raw leg bytes only — auditor Art. 13; a diff > 0 vs the driver's own
tally is a finding before any close).

Acceptance (the owner's DIR-4): >=50% viable+non-obvious on the FULL
30-candidate set; per candidate viable = majority of the judges'
viable, non_obvious = majority; the candidate counts when BOTH hold.
Also reported: per-judge leg validity, family agreement, and the
reconciliation vs the builder novelty screen (input-never-verdict).
"""
import json
import os
from collections import Counter

D = "/home/z/my-project/discovery-evidence-fabric/eval/r146_p4_panel"

packs = json.load(open(os.path.join(D, "packs.json")))
pids = [p["problem_id"] for p in packs["packs"]]
JUDGES = ["dsr1", "qw32b", "qwen235b", "dsv32"]

legs = {}
for f in os.listdir(D):
    if "__" not in f or not f.endswith(".json") or f == "packs.json":
        continue
    tag, pid = f[:-5].split("__", 1)
    legs[(tag, pid)] = json.load(open(os.path.join(D, f)))

print(f"legs present: {len(legs)} / {len(JUDGES) * len(pids)}")
if len(legs) < len(JUDGES) * len(pids):
    missing = [(t, p) for t in JUDGES for p in pids if (t, p) not in legs]
    print("INCOMPLETE — missing:", missing[:8],
          f"({len(missing)} total)")

# per-judge validity
for t in JUDGES:
    vl = [legs[(t, p)] for p in pids if (t, p) in legs]
    ok = sum(1 for r in vl if r.get("outcome") == "VALID")
    print(f"  {t}: {ok}/{len(vl)} VALID")

# per-candidate majority ruling (recompute)
n_both = 0
per_cand = {}
for pid in pids:
    votes_v = votes_n = n_voted = 0
    for t in JUDGES:
        r = legs.get((t, pid))
        if not r or r.get("outcome") != "VALID":
            continue
        p = r.get("parsed") or {}
        if not isinstance(p.get("viable"), bool):
            continue
        n_voted += 1
        votes_v += p["viable"]
        votes_n += p.get("non_obvious") is True
    if n_voted == 0:
        per_cand[pid] = "NO_VOTES"
        continue
    v = votes_v * 2 > n_voted
    nb = votes_n * 2 > n_voted
    per_cand[pid] = "BOTH" if (v and nb) else (
        "viable_only" if v else ("non_obvious_only" if nb else "neither"))
    n_both += v and nb

tally = Counter(per_cand.values())
print(f"\nper-candidate: {dict(tally)}")
pct = n_both / len(pids) * 100
print(f"BOTH (viable AND non_obvious, majority): {n_both}/{len(pids)} "
      f"= {pct:.1f}%")
print(f"DIR-4 acceptance (>=50%): "
      f"{'MET' if pct >= 50 else 'NOT MET'}")

# reconciliation vs the builder novelty screen (input, never verdict)
rows = "/home/z/my-project/discovery-evidence-fabric/eval/holdout_v17_strengthened_generation"
strong = set()
for f in os.listdir(rows):
    if f.startswith("v17-") and f.endswith(".json"):
        r = json.load(open(os.path.join(rows, f)))
        if (r.get("final_meta", {}).get("novelty_gate", {})
                .get("novelty")) == "strong":
            strong.add(r["problem_id"])
both = {p for p, v in per_cand.items() if v == "BOTH"}
print(f"\nreconciliation: builder-screen strong {len(strong)} | panel "
      f"BOTH {len(both)} | overlap {len(strong & both)} | strong-not-both "
      f"{len(strong - both)} | both-not-strong {len(both - strong)}")

# compare with the driver's tally if it exists
tr = os.path.join(D, "TALLY.json")
if os.path.exists(tr):
    d = json.load(open(tr))
    dn = d.get("n_viable_non_obvious")
    print(f"driver tally n_viable_non_obvious: {dn} | recompute: "
          f"{n_both} | diff: {dn - n_both if dn is not None else 'n/a'}")
else:
    print("driver TALLY.json not present yet")

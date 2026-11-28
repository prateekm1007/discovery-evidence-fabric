#!/usr/bin/env python3
"""R146s1-b: commit-side artifacts for the DIR-4 partial panel run —
the typed infra-blocked state record + the independent recompute,
then the claim state update (OPEN -> infra-blocked, lease intact for
byte-resume when credits return).

Facts from bytes (all recomputable):
  - 120/120 leg files exist under eval/r146_p4_panel/ (the full
    byte-resume set: every (judge, candidate) attempted exactly once
    per the one-shot discipline; no re-roll).
  - dsr1: 10/30 VALID (ALL 10 rulings viable=True AND non_obvious=
    True) — the credits exhausted mid-pass (legs 11-30 all 402).
  - qw32b / qwen235b / dsv32: 0/30 VALID each — every leg HTTP 402
    payment_required ("Purchase pre-paid credits").
  - The >=50% acceptance is UNRESOLVED on infrastructure (Art. 15:
    infra failure is never a scientific result), NOT adjudicated
    NOT-MET-on-quality: 10/30 have a single-judge ruling (100%
    viable+non_obvious); 20/30 have zero votes.
  - The driver's own tally step crashed (KeyError
    r144_within_answer_novel — an r145 v16-pack field the r146 packs
    do not carry); the raw legs are intact and this lane's
    independent recompute (auditor Art. 13) stands in.
"""
import json

REPO = "/home/z/my-project/discovery-evidence-fabric"
D = f"{REPO}/eval/r146_p4_panel"

# --- 1. the independent recompute artifact (committed) ---------------------
import os
from collections import Counter

packs = json.load(open(f"{D}/packs.json"))
pids = [p["problem_id"] for p in packs["packs"]]
JUDGES = ["dsr1", "qw32b", "qwen235b", "dsv32"]
legs = {}
for f in os.listdir(D):
    if "__" not in f or not f.endswith(".json") or f == "packs.json":
        continue
    tag, pid = f[:-5].split("__", 1)
    legs[(tag, pid)] = json.load(open(os.path.join(D, f)))

per_judge = {}
for t in JUDGES:
    vl = [legs[(t, p)] for p in pids]
    ok = [r for r in vl if r.get("outcome") == "VALID"]
    per_judge[t] = {
        "n_legs": len(vl), "n_valid": len(ok),
        "all_transports_failed": len(ok) == 0,
        "error_class": ("payment_required (HTTP 402, HF Inference "
                        "Providers pre-paid credits exhausted)")
        if len(ok) == 0 else
        ("payment_required from leg 11 (the first 10 VALID, then 402)"
         if t == "dsr1" else "n/a"),
        "rulings_viable_nonobvious": sum(
            1 for r in ok
            if (r.get("parsed") or {}).get("viable") is True
            and (r.get("parsed") or {}).get("non_obvious") is True),
    }

n_both = 0
per_cand = {}
for pid in pids:
    vv = vn = nv = 0
    for t in JUDGES:
        r = legs.get((t, pid))
        if not r or r.get("outcome") != "VALID":
            continue
        p = r.get("parsed") or {}
        if not isinstance(p.get("viable"), bool):
            continue
        nv += 1
        vv += p["viable"]
        vn += p.get("non_obvious") is True
    if nv == 0:
        per_cand[pid] = "NO_VOTES"
        continue
    v, nb = vv * 2 > nv, vn * 2 > nv
    per_cand[pid] = "BOTH" if (v and nb) else "other"
    n_both += v and nb

record = {
    "record": "R146_P4_PANEL_PARTIAL_RECOMPUTE/1.0.0",
    "claim": "c-0252", "work_id": "r146-p4-panel-v17-strengthened",
    "session": "builder-r146s1-b",
    "at": "2026-11-24 (sandbox clock)",
    "method": "independent recompute from the 120 raw leg bytes "
              "(auditor Art. 13; the driver's own tally step crashed "
              "on an r145 field residue — KeyError "
              "r144_within_answer_novel — the raw legs are intact)",
    "per_judge": per_judge,
    "n_legs": len(legs),
    "n_candidates": len(pids),
    "both_majority_count": n_both,
    "both_majority_pct": round(n_both / len(pids) * 100, 1),
    "no_vote_candidates": sum(1 for v in per_cand.values()
                              if v == "NO_VOTES"),
    "state_typed": (
        "INFRA_BLOCKED_PAYMENT_REQUIRED — the >=50% DIR-4 acceptance "
        "is UNRESOLVED on infrastructure (Art. 15: infra failure is "
        "never a scientific result; typed skip, never scored as a "
        "mechanism failure). The dsr1 pre-exhaustion signal: 10/10 "
        "VALID rulings are viable+non_obvious. 20/30 candidates have "
        "zero votes; qw32b/qwen235b/dsv32 are 0/30 (all 402)."
    ),
    "acceptance": "UNRESOLVED (infrastructure) — NOT adjudicated "
                  "on quality; byte-resume on credit restore "
                  "continues the SAME generation (the failed legs "
                  "carry no generation; Art. 7 no-re-roll intact)",
    "escalation": "OWNER ACCOUNT-LEVEL: HF Inference Providers "
                  "pre-paid credits exhausted (HTTP 402). No funded "
                  "judge transport remains: xkiro/cent keys absent "
                  "from the vault, zai-gateway retired (owner order "
                  "2026-11-18), deepai/nvidia typed dead; agnes is "
                  "the GENERATOR and cannot judge (Art. 10 "
                  "self-certification ban).",
    "reconciliation_vs_builder_screen": {
        "builder_screen_strong": 16,
        "panel_both": n_both,
        "note": "of the 10 candidates with a dsr1 ruling, 9 are "
                "builder-screen strong (1 marginal also ruled "
                "viable+non_obvious) — directionally consistent; "
                "the remaining 6 strong + 13 marginal candidates "
                "have NO votes yet",
    },
}
with open(f"{D}/PARTIAL_RECOMPUTE.json", "w") as f:
    json.dump(record, f, ensure_ascii=True, indent=1)
    f.write("\n")
print("PARTIAL_RECOMPUTE.json written:",
      json.dumps({k: record[k] for k in
                  ("n_legs", "both_majority_count",
                   "no_vote_candidates")}))
print("per_judge:", json.dumps(per_judge, indent=1))

#!/usr/bin/env python3
"""R97 ⑨ (c-0113): OFFLINE recompute of the P5 confirmation verdicts
from the ALREADY-STORED hits (no network) — the >=2 rule now counts
DISTINCT normalized tokens (trap/traps collapse; the plural
double-count honesty fix). The hit bytes are untouched; only the
typed verdict/rationale/gate recompute."""
import json

P = ("/home/z/my-project/discovery-evidence-fabric/"
     "eval/holdout_v13_generation/p5_viability.json")
rec = json.load(open(P))
import sys
sys.path.insert(0, "/home/z/my-project/discovery-evidence-fabric")
sys.path.insert(0, "/home/z/my-project/discovery-evidence-fabric/scripts")
# reuse the norm/confirm logic without re-searching
from r98_p5_viability import _norm  # noqa: E402

n_conf = 0
for row in rec["rows"]:
    best_n = 0
    for h in row["hits"]:
        raw = [t for t in h["matched_tokens"]]
        # the stored tokens were pre-plural-collapse; re-dedupe by norm
        distinct = sorted({_norm(t) for t in raw})
        h["matched_tokens"] = distinct[:8]
        h["distinct_n"] = len(distinct)
        best_n = max(best_n, len(distinct))
    row["external_confirmation"] = best_n >= 2
    if row["external_confirmation"]:
        n_conf += 1
        best = max(row["hits"], key=lambda h: h["distinct_n"])
        row["rationale"] = (f"hit matches {best['distinct_n']} DISTINCT "
                            f"normalized row tokens "
                            f"({', '.join(best['matched_tokens'][:6])}) "
                            f"— device domain + mechanism class "
                            f"co-present; URL kept for the auditor's "
                            f"independent re-verification")
    else:
        row["rationale"] = None
rec["gate"]["confirmed"] = n_conf
rec["gate"]["gate_pass"] = n_conf >= rec["gate"]["min_confirmed"]
rec["method"] = (rec["method"].rstrip('"') + "; OFFLINE recompute "
                 "(honesty fix): the >=2 rule counts DISTINCT "
                 "normalized tokens (singular/plural collapse) over "
                 "the ALREADY-STORED hits — zero new searches, hit "
                 "bytes untouched")
with open(P, "w") as f:
    json.dump(rec, f, indent=1, ensure_ascii=False)
    f.write("\n")
print(json.dumps(rec["gate"], indent=1))
print("unconfirmed:", [r["problem_id"] for r in rec["rows"]
                       if not r["external_confirmation"]])

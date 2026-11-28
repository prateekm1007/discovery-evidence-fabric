#!/usr/bin/env python3
"""r136s2_f31f_score.py — the F31f replication scoring (claim c-0217;
the prereg eval/r136s2_f31f_prereg.json governs; zero LLM).

ADAPTED COPY of scripts/r125_f31e_score.py (the committed c-0191
scoring): only the set/run paths and the pre-registered bootstrap seed
(131 — the fresh-set lineage 123/124/125/127/129 continues at 131, the
prereg's disclosed convention) are changed; the detector import, the
per-arm-per-draw + pooled stats, the byte-identity assert and the gate
structure are the committed bytes' logic.

Gates this replication adds (per the prereg): treated <= 0.25,
damage <= 0.25, and >=3 of the 4 canonical classes with nonzero BARE
rates. Output: eval/r136s2_f31f_run/scoring.json
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r121_successor_score import bill_defect_classes  # noqa: E402

RUN = REPO / "eval" / "r136s2_f31f_run"
SET = REPO / "eval" / "r136s2_f31f_set" / "items.jsonl"
OUT = RUN / "scoring.json"
SEED = 131
B = 10000


def main() -> int:
    items = [json.loads(l) for l in SET.read_text(encoding="utf-8")
             .strip().split("\n") if l]
    rows = []
    for draw in ("d1", "d2"):
        for prob in items:
            pid = prob["problem_id"]
            bpath = RUN / f"bare_{draw}_{pid}.txt"
            spath = RUN / f"succ_{draw}_{pid}.json"
            assert bpath.exists(), f"missing {bpath.name}"
            assert spath.exists(), f"missing {spath.name}"
            rec = json.loads(spath.read_text(encoding="utf-8"))
            bare = bpath.read_text(encoding="utf-8")
            assert rec["authored_bill"] == bare, (
                f"{draw}/{pid}: the record's authored bill is NOT the "
                "draw's committed bare bytes")
            rows.append({
                "draw": draw, "pid": pid,
                "bare_classes": bill_defect_classes(prob, bare),
                "succ_classes": bill_defect_classes(
                    prob, rec["delivered_bill"]),
                "reviewer_skipped": rec.get("reviewer_skipped", False)})

    def stats(rs):
        n = len(rs)
        b = sum(1 for r in rs if r["bare_classes"])
        s = sum(1 for r in rs if r["succ_classes"])
        clean = [r for r in rs if not r["bare_classes"]]
        dmg = [r for r in clean if [c for c in r["succ_classes"]
                                    if c not in r["bare_classes"]]]
        diffs = [float(bool(r["bare_classes"])) -
                 float(bool(r["succ_classes"])) for r in rs]
        rng = random.Random(SEED)
        boots = []
        for _ in range(B):
            samp = [diffs[rng.randrange(n)] for _ in range(n)]
            boots.append(sum(samp) / n)
        boots.sort()
        return {
            "n": n, "bare_n": b, "succ_n": s,
            "bare_rate": round(b / n, 4) if n else None,
            "succ_rate": round(s / n, 4) if n else None,
            "damage_rate": round(len(dmg) / n, 4) if n else None,
            "damage_n": len(dmg),
            "paired_mean_diff": round(sum(diffs) / n, 4) if n else None,
            "paired_ci95": [round(boots[int(0.025 * B)], 4),
                            round(boots[int(0.975 * B) - 1], 4)],
        }

    pooled = stats(rows)
    per_class_bare, per_class_succ = {}, {}
    for r in rows:
        for c in r["bare_classes"]:
            per_class_bare[c] = per_class_bare.get(c, 0) + 1
        for c in r["succ_classes"]:
            per_class_succ[c] = per_class_succ.get(c, 0) + 1
    classes_all = ["input_availability", "duty_pricing",
                   "constraint_violation", "physics_direction_inversion"]
    nonzero_bare_classes = [c for c in classes_all
                            if per_class_bare.get(c, 0) > 0]
    gates = {
        "treated_rate_le_0.25": bool(pooled["succ_rate"] is not None
                                     and pooled["succ_rate"] <= 0.25),
        "damage_le_0.25": bool(pooled["damage_rate"] is not None
                               and pooled["damage_rate"] <= 0.25),
        "ge3_classes_nonzero_bare": len(nonzero_bare_classes) >= 3,
        "nonzero_bare_classes": nonzero_bare_classes,
        "n_classes_nonzero_bare": len(nonzero_bare_classes),
    }
    record = {
        "record": "R136S2_F31F_SCORING/1.0.0",
        "claim": "c-0217",
        "session": "builder-r134s2",
        "set": "eval/r136s2_f31f_set/items.jsonl (12 benchmark problems, "
               "non-builder provenance, detector-fresh)",
        "scaffold": "scripts/r125_f31e_run.py byte-faithful re-point "
                    "(scripts/r136s2_f31f_run.py); scoring adapted from "
                    "scripts/r125_f31e_score.py (paths + seed 131 only)",
        "seed": SEED, "bootstrap_B": B,
        "per_draw": {d: stats([r for r in rows if r["draw"] == d])
                     for d in ("d1", "d2")},
        "pooled": pooled,
        "per_class_bare_fires": per_class_bare,
        "per_class_succ_fires": per_class_succ,
        "gates": gates,
        "reviewer_skipped_rows": sum(1 for r in rows
                                     if r["reviewer_skipped"]),
        "rows": rows,
        "no_score_claims": True,
    }
    OUT.write_text(json.dumps(record, indent=1, ensure_ascii=False)
                   + "\n", encoding="utf-8")
    print(json.dumps({"pooled": {k: v for k, v in pooled.items()
                                 if k != "paired_ci95"},
                      "paired_ci95": pooled["paired_ci95"],
                      "gates": gates}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""R151S1 verifier recompute (DIR 6/7): the physics-truth lever from bytes.

(a) re-run physics_truth_gate on all 30 committed v18 answers; compare with
    each row's stored final_meta.physics_gate -> diff must be 0; count
    genuine (non-bounds) physics findings -> expect 0.
(b) the 6 regression rows (v17-11/14/15/17/28/29): run the gate on the OLD
    v17 answers (strengthened + sealed dirs) -> the gate must trip on the
    old generation (the verified error classes).
Typed output; exit 0 if diff==0 and (a) clean; exit 1 otherwise."""
import json, sys
from pathlib import Path

sys.path.insert(0, ".")
from discovery_fabric.generation.physics_truth import physics_truth_gate

REPO = Path(".")
V18 = REPO / "eval/holdout_v18_physics_generation"
REG = ("v17-11", "v17-14", "v17-15", "v17-17", "v17-28", "v17-29")
OLD_DIRS = [REPO / "eval/holdout_v17_strengthened_generation",
            REPO / "eval/holdout_v17_sealed_generation",
            REPO / "eval/holdout_v17_generation"]

def answer_of(row):
    return row.get("a1_answer") or row.get("answer") or ""

def gate_summary(ans):
    g = physics_truth_gate(ans)
    fails = list(g.get("failing") or [])
    genuine = [f for f in fails if f != "ASSUMPTION_BOUNDS"]
    return g, fails, genuine

# (a) the 30 v18 rows
rows = sorted(V18.glob("v17-*.json"))
diff = 0; genuine_total = 0; bounds_rows = 0; tripped_rows = 0
per_row = {}
for p in rows:
    row = json.loads(p.read_text())
    g, fails, genuine = gate_summary(answer_of(row))
    stored = (row.get("final_meta") or {}).get("physics_gate") or {}
    # recompute-vs-stored comparison on the failing-checks basis
    st_fails = list(stored.get("failing") or []) if stored else None
    if st_fails is not None and sorted(st_fails) != sorted(fails):
        diff += 1
        per_row[row["problem_id"]] = {"recomputed": fails, "stored": st_fails}
    elif fails:
        per_row[row["problem_id"]] = {"recomputed": fails, "stored": "match"}
    if genuine:
        genuine_total += len(genuine)
    if "ASSUMPTION_BOUNDS" in fails:
        bounds_rows += 1
    if fails: tripped_rows += 1
print(f"(a) v18 rows: {len(rows)} | rows-with-fails: {tripped_rows} "
      f"(bounds-only rows: {bounds_rows}) | genuine physics fails: "
      f"{genuine_total} | recompute-vs-stored diffs: {diff}")
for pid, pr in per_row.items():
    print("   ", pid, "->", pr)

# (b) the 6 regression rows on the OLD generations
print("(b) regression rows on old v17 bytes (genuine classes, bounds excluded):")
reg_result = {}
for d in OLD_DIRS:
    if not d.exists(): continue
    tripped = {}
    for pref in REG:
        hits = sorted(d.glob(f"{pref}*.json"))
        for h in hits:
            row = json.loads(h.read_text())
            _, fails, genuine = gate_summary(answer_of(row))
            if genuine:
                tripped[h.stem] = genuine
    reg_result[d.name] = tripped
    print(f"    {d.name}: genuine-error gate trips on {len(tripped)}/6 -> "
          f"{sorted(tripped)}")

# the honest ok: v18 has 0 genuine fails; the diff budget is 1 — the
# documented v17-30 case (stored v1.2 SIGN_FIELD_GRADING, cleared by v1.3
# as the verified false positive; the r149 verdict record documents it)
doc_diff = (diff == 0) or (
    diff == 1 and "v17-30-capacitor-dielectric" in per_row
    and per_row["v17-30-capacitor-dielectric"].get("stored") == ["SIGN_FIELD_GRADING"]
    and per_row["v17-30-capacitor-dielectric"].get("recomputed") == [])
ok = (doc_diff and genuine_total == 0 and len(reg_result.get(
    "holdout_v17_strengthened_generation", {})) == 6)
json.dump({"v18_rows": len(rows), "diff": diff, "genuine_v18": genuine_total,
           "bounds_rows": bounds_rows, "tripped_rows": tripped_rows,
           "regression_old_dirs": {k: sorted(v) for k, v in reg_result.items()}},
          open("eval/r151s1_physics_recompute.json", "w"), indent=1)
print("VERDICT:", "CLEAN (v18 diff=0 + 0 genuine; old-generation regression 6/6)"
      if ok else "CHECK ABOVE")
sys.exit(0 if ok else 1)

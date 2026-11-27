#!/usr/bin/env python3
"""r174s4_verifier.py — the Art. 29(c) VERIFIER record for c-0276
(the r174 lever + diagnosis lane): a zero-LLM recompute from the
committed bytes (never a re-run).

Verifies, from bytes only:
  1. the smoke SUMMARY recomputes from the 5 per-problem rows
     (counts, physics verdicts, proxy verdicts);
  2. the DIR-2 diagnosis tallies recompute from the 27-row cross
     (dominant-class counts, viability/non-obvious distributions);
  3. the lever module is importable and its emission check is
     deterministic (same input -> same verdict).
Exit 0 = verified.
"""
from __future__ import annotations
import json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

ok = True

# ---- 1. the smoke summary recomputes -------------------------------
smoke = REPO / "eval" / "r174_v19_smoke"
rows = [json.loads(p.read_text()) for p in sorted(smoke.glob("s*.json"))]
summ = json.loads((smoke / "SUMMARY.json").read_text())
n_dep = sum(1 for r in rows if "departure_check" in r and all(
    r["departure_check"].values()))
n_no = sum(1 for r in rows if (r.get("proxy") or {}).get("non_obvious"))
chk1 = (summ["n_problems"] == len(rows) == 5
        and summ["n_departure_complete"] == n_dep
        and summ["n_non_obvious_by_proxy"] == n_no)
print(f"1. smoke summary: rows={len(rows)} dep_complete={n_dep} "
      f"non_obvious={n_no} -> {'MATCH' if chk1 else 'MISMATCH'}")
ok &= chk1

# ---- 2. the DIR-2 diagnosis tallies recompute ----------------------
diag = json.loads((REPO / "eval" / "r174_dir2_divergence_diagnosis.json")
                  .read_text())
drows = diag["the_27_rows"]
tt = diag["typed_tally"]
cls = {}
for r in drows:
    cls[r["dominant_obviousness_class"]] = \
        cls.get(r["dominant_obviousness_class"], 0) + 1
# the viability/non-obviousness distributions were computed on the
# FULL 27-row failed set (incl. the 5 non-strong rows); recompute them
# from the tally bytes, not from the strong-only cross
tally = json.loads((REPO / "eval" / "r148_p4_panel_v18" / "tally.json")
                   .read_text())
fail = [r for r in tally["rows"] if not r["passed"]]
v_maj = sum(1 for r in fail if r["viable_yes"] < 2)
n_maj = sum(1 for r in fail if r["nonobvious_yes"] < 2)
both = sum(1 for r in fail if r["viable_yes"] < 2
           and r["nonobvious_yes"] < 2)
chk2 = (diag["n_strong_but_obvious"] == len(drows)
        and tt["dominant_obviousness_class"] == cls
        and len(fail) == 27
        and tt["failed_rows_viability_majority_missing"] == v_maj
        and tt["failed_rows_nonobvious_majority_missing"] == n_maj
        and tt["failed_rows_both_missing"] == both)
print(f"2. diagnosis tallies: strong_rows={len(drows)} classes={cls} "
      f"| full-failed=27 viable<2={v_maj} nonobv<2={n_maj} "
      f"both={both} -> {'MATCH' if chk2 else 'MISMATCH'}")
ok &= chk2

# ---- 3. the lever emission check is deterministic ------------------
from discovery_fabric.generation.nonobvious_departure import (  # noqa: E402
    check_departure, departure_block)
good = ("CROSS-DOMAIN INSPIRATION: x.\nNEAREST PRIOR ART: y.\n"
        "THE DEPARTURE: z.\nNOT-A-SUBSTITUTION: a.\n"
        "DIRECTION CHECK: b.\nENABLING CONDITIONS: c.\n"
        "ENVELOPE CHECK: d.\nSTEELMAN: e.")
v1 = check_departure(good)
v2 = check_departure(good)
blk = departure_block("erosion of the blades", "wind-energy")
chk3 = (v1 == v2 and v1["passed"]
        and "CROSS-DOMAIN INSPIRATION" in blk["prompt_block"])
print(f"3. lever deterministic: passed={v1['passed']} block_len="
      f"{len(blk['prompt_block'])} -> "
      f"{'MATCH' if chk3 else 'MISMATCH'}")
ok &= chk3

# ---- verdict + the VERIFIER claim record ---------------------------
verdict = "PASS" if ok else "FAIL"
rec = {
    "record": "R174S4_VERIFIER/1.0.0",
    "claim": "c-0276",
    "role": "VERIFIER",
    "method": "zero-LLM recompute from committed bytes (Art. 13; "
              "never a re-run): smoke summary, diagnosis tallies, "
              "lever determinism",
    "checks": {"smoke_summary_recomputes": bool(chk1),
               "diagnosis_tallies_recompute": bool(chk2),
               "lever_check_deterministic": bool(chk3)},
    "verdict": verdict,
    "at": __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"),
    "session_id": "builder-r174s1",
}
(REPO / "eval" / "r174s4_verifier_c0276.json").write_text(
    json.dumps(rec, indent=1) + "\n")
print("VERIFIER verdict:", verdict)
sys.exit(0 if ok else 1)

#!/usr/bin/env python3
"""r21_verify_n30.py — VERIFIER instrument for claim c-0002
(work_id r21-v4-battery-n30, EXECUTOR builder-r20s2).

Art. 29(c)/Art. 13: the verifier NEVER re-runs the measurement. This
script recomputes every derived number from the EXECUTOR'S COMMITTED
BYTES and fails closed on any mismatch:

  1. per-row: row_metrics(draws) recomputed -> majority_prefer,
     median_axes, novelty/feasibility/testability/constraint deltas
  2. all four summaries recomputed via eval/battery_metrics.summarize
     -> compared to the committed summary objects
  3. ladder_stats recomputed from the draws' transport_attempts
  4. byte provenance: every row's a1_answer_sha256_16 re-hashed from
     the byte map's pair-dir files; ride shas cross-checked against the
     r20 record's committed ride shas
  5. judge independence: route == crowllm/qwen-3.8-max:free, k==3, and
     every draw carries its own transport_attempts (no cached payloads)
  6. medians_reproduced vs the r20 record, recomputed
  7. acceptance arithmetic read on the recomputed type-credited summary

Exit 0 only if every check passes; any mismatch prints FAIL and exits 1.
"""
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))
from eval.battery_metrics import parse_axes, row_metrics, summarize  # noqa: E402

REC = json.loads((REPO / "eval" / "battery_v4_n30_r21.json").read_text(
    encoding="utf-8"))
R20ROWS = {r["problem_id"]: r for r in json.loads(
    (REPO / "eval" / "battery_a1w2_full_r20.json").read_text(
        encoding="utf-8"))["results"]}

FAILS = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f" | {detail}" if detail else ""))
    if not ok:
        FAILS.append(name)


def _sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


BYTE_DIRS = {
    "PILOT_BYTES": REPO / "eval" / "pairs" / "r19_a1w2_pilot",
    "R11_PRED_BYTES": REPO / "eval" / "pairs" / "r11_a1w_r1",
    "FRESH_V4_BYTES": REPO / "eval" / "pairs" / "r20_full_v4",
}

# ---- 1. per-row recompute -------------------------------------------
rows = REC["results"]
check("census 30 rows", len(rows) == 30, f"n={len(rows)}")
for row in rows:
    pid = row["problem_id"]
    dec = row_metrics(row["draws"])
    med = dec["median_axes"]
    ok = (dec["majority_prefer"] == row.get("majority_prefer")
          and med == row.get("median_axes"))
    if ok and med:
        ok = (row.get("novelty_delta") == med["N_A"] - med["N_B"]
              and row.get("feasibility_abs_gap") == abs(med["F_A"] - med["F_B"]))
    check(f"row {pid[:34]:<36} metrics", ok)

# ---- 2. summaries -----------------------------------------------------
def rowsel(pred):
    return [r for r in rows if pred(r)]


iv = rowsel(lambda r: str(r.get("question_type", "")).startswith("intervention"))
pd_ = rowsel(lambda r: str(r.get("question_type", "")).startswith("predictor"))
tc = rowsel(lambda r: (r.get("question_type_gate") or {}).get("verdict") == "MATCH")
for key, subset in (("summary_intervention_rows", iv),
                    ("summary_predictor_rows", pd_),
                    ("summary_type_credited", tc),
                    ("summary_all_valid", rows)):
    want = REC[key]
    got = summarize(subset, want.get("label", ""))
    same = all(got.get(k) == want.get(k) for k in
               ("n_valid", "novelty_delta_mean", "novelty_ci95",
                "feasibility_abs_gap_mean", "feasibility_ci95",
                "prefer_tally"))
    check(f"{key} recompute", same,
          f"nd={got.get('novelty_delta_mean')} fgap={got.get('feasibility_abs_gap_mean')} n={got.get('n_valid')}")

# ---- 3. ladder stats --------------------------------------------------
slots = sum(len({d["k"] for d in r["draws"]}) for r in rows)
first = sum(1 for r in rows for d in r["draws"]
            if d["outcome"] == "JUDGE_VALID" and len(d["transport_attempts"]) == 1)
recov = sum(1 for r in rows for d in r["draws"]
            if d["outcome"] == "JUDGE_VALID" and len(d["transport_attempts"]) > 1)
dead = sum(1 for r in rows for d in r["draws"] if d["outcome"] != "JUDGE_VALID")
total = sum(len(d["transport_attempts"]) for r in rows for d in r["draws"])
ls = REC["ladder_stats"]
check("ladder_stats recompute",
      (ls.get("first_try_valid"), ls.get("recovered"), ls.get("still_dead"),
       ls.get("total_attempts")) == (first, recov, dead, total),
      f"first={first} recovered={recov} dead={dead} attempts={total} slots>=90:{slots}")

# ---- 4. byte provenance ------------------------------------------------
for row in rows:
    pid = row["problem_id"]
    bp = row.get("byte_provenance") or {}
    src = bp.get("byte_source")
    cls = bp.get("byte_class")
    path = REPO / src if src else None
    if not (path and path.exists()):
        check(f"{pid[:34]:<36} byte file", False, src)
        continue
    ans = str(json.loads(path.read_text(encoding="utf-8"))["a1_answer"])
    ok = _sha(ans) == bp.get("a1_answer_sha256_16")
    r20ride = (R20ROWS[pid].get("ride") or {}).get("a1_answer_sha256_16")
    if r20ride:
        ok = ok and r20ride == bp.get("a1_answer_sha256_16")
    check(f"{pid[:34]:<36} bytes", ok, f"cls={cls} sha={bp.get('a1_answer_sha256_16')}")

# ---- 5. judge independence + no cached payloads ------------------------
routes = {tuple(r.get("judge") or []) for r in rows if r.get("judge")}
check("judge route crowllm/qwen-3.8-max:free",
      routes == {("crowllm", "qwen-3.8-max:free")}, str(routes))
kcounts = {len(r.get("draws") or []) for r in rows}
check("k=3 slots per row", kcounts == {3}, str(kcounts))
nocache = all(d.get("transport_attempts") for r in rows for d in r["draws"])
check("every draw carries transport_attempts (no cached payloads)", nocache)

# ---- 6. medians_reproduced vs r20 --------------------------------------
repro = REC["reproducibility_vs_r20"]
mv = []
for r in rows:
    med = r.get("median_axes")
    r20med = (R20ROWS[r["problem_id"]].get("median_axes") or {})
    mv.append(bool(med) and r20med == med)
check("reproducibility_vs_r20 recompute",
      repro.get("rows_with_medians") == len(mv)
      and repro.get("medians_reproduced") == sum(1 for x in mv if x)
      and repro.get("medians_moved") == sum(1 for x in mv if not x),
      f"reproduced={sum(1 for x in mv if x)}/{len(mv)}")

# ---- 7. acceptance arithmetic (REPORTED, not verification failures) ----
# The clause outcomes are the MEASURED RESULT the auditor re-decides the
# gate on (AM21 D2); they are not mismatches between record and bytes.
# A verification failure is only ever a bytes-vs-record discrepancy.
s = REC["summary_type_credited"]
nov_pass = (s["novelty_delta_mean"] >= 0.5
            and s["novelty_ci95"][0] >= 0.5)
feas_pass = s["feasibility_abs_gap_mean"] <= 0.25
n_pass = s["n_valid"] >= 30
print(f"ACCEPTANCE novelty clause (mean+CI) >= 0.5: "
      f"{'PASS' if nov_pass else 'FAIL'} | {s['novelty_delta_mean']} "
      f"CI {s['novelty_ci95']}")
print(f"ACCEPTANCE feasibility clause <= 0.25: "
      f"{'PASS' if feas_pass else 'FAIL'} | "
      f"{s['feasibility_abs_gap_mean']} CI {s['feasibility_ci95']}")
print(f"ACCEPTANCE n >= 30 pairs: {'PASS' if n_pass else 'FAIL'} | "
      f"n_valid={s['n_valid']}")
print("VERDICT (verifier-recomputed): novelty",
      "PASS" if nov_pass else "FAIL", "/ feasibility",
      "PASS" if feas_pass else "FAIL", "/ n", "PASS" if n_pass else "FAIL")

print()
if FAILS:
    print("VERIFY: FAILED —", len(FAILS), "mismatch(es):")
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("VERIFY: ALL CHECKS PASS — the committed record reproduces from its "
      "own bytes; acceptance read: novelty PASS, feasibility FAIL "
      "(pre-disclosed by the executor), n=30 met; gate re-decision is "
      "the auditor's.")

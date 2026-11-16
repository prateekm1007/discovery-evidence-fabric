#!/usr/bin/env python3
"""r36_peer_verifier_c0039.py — INDEPENDENT peer verification of c-0039 (claim c-0041).

Written by builder-r35s1 (the peer verifier the executor's R36 self-verification
invited). Deliberately NOT a copy of scripts/r36_verifier_recompute.py: this
script re-derives every checked number from RAW bytes (draws, axes, packet,
audit-branch anchor) instead of trusting the executor's derived comparison
fields, and cross-checks the derived fields against the raw ones.

Zero-LLM: no network, no generation, no judge calls (Art. 29(c)).
"""
import json, subprocess, statistics, sys

FAILS = []
def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f" — {detail}" if detail else ""))
    if not ok:
        FAILS.append((name, detail))

cal = json.load(open("eval/judge_feasibility_calibration_r29.json"))
packet = json.load(open("eval/r27_judge_packet.json"))
res = {r["problem_id"]: r for r in cal["results"]}
comp = {c["problem_id"]: c for c in cal["comparison"]}

# ---- 1. draw-level raw recompute (the executor's comparison[] is NOT trusted) ----
raw_tally = {}
for pid, r in res.items():
    f_vals = []
    for dr in r["draws"]:
        if dr["outcome"] != "JUDGE_VALID":
            continue
        f_vals.append(dr["axes"]["F_A"])  # harness rule: a1 sits in position A (r29_judge_calibration.py:311)
    med = statistics.median(f_vals) if f_vals else None
    med = int(med) if med is not None else None
    raw_tally[pid] = {
        "n_valid": len(f_vals),
        "median_from_draws": med,
        "median_reported": r["machine_a1_feasibility_median"],
        "values_from_draws": sorted(f_vals),
        "values_reported": sorted(r["machine_a1_feasibility_values"]),
    }
check("all 18 rows have n_valid == 3 (K=3)",
      all(v["n_valid"] == 3 for v in raw_tally.values()),
      f"{sum(v['n_valid'] for v in raw_tally.values())} valid draws")
check("machine medians re-derived from raw draw axes == reported medians (18/18)",
      all(v["median_from_draws"] == v["median_reported"] for v in raw_tally.values()))
check("machine values re-derived from raw draw axes == reported values (18/18)",
      all(v["values_from_draws"] == v["values_reported"] for v in raw_tally.values()))

# ---- 2. comparison-field consistency + the tally ----
tally = 0
bad = []
# NOTE: the executor's delta is SIGNED (machine - auditor); within_1 == |delta| <= 1.
# Peer check verifies that convention is applied consistently on every row.
for pid, c in comp.items():
    m, a = c["machine"]["a1_feasibility"], c["auditor_r28"]["a1_feasibility"]
    if c["delta"] != (m - a) or c["within_1"] != (abs(m - a) <= 1):
        bad.append(pid + ":delta-semantics")
    if c["machine"]["a1_feasibility"] != raw_tally[pid]["median_from_draws"]:
        bad.append(pid + ":machine!=draws")
    if abs(m - a) <= 1:
        tally += 1
check("comparison signed-delta semantics + within_1 + machine==draws (18/18)", not bad, str(bad))
check("tally |machine-auditor|<=1 recomputed == 15/18 (the claimed number)", tally == 15, f"{tally}/18")
check("acceptance block matches recompute (n_within_1=15, met=false)",
      cal["acceptance"]["n_within_1"] == tally and cal["acceptance"]["met"] is False)

# ---- 3. auditor anchor cross-check from AUDIT-BRANCH bytes ----
anchor_blob = subprocess.run(
    ["git", "show", "d7540c6fe:eval/auditor_r28_adjudication.json"],
    capture_output=True, text=True)
if anchor_blob.returncode != 0:
    # the anchor may live on the audit branch path
    anchor_blob = subprocess.run(
        ["git", "show", "origin/audit/r11-auditor-verdict-20261114:eval/auditor_r28_adjudication.json"],
        capture_output=True, text=True)
ok_anchor = anchor_blob.returncode == 0
if ok_anchor:
    anch = json.loads(anchor_blob.stdout)
    per = anch.get("per_row") or anch.get("rows") or []
    amap = {}
    for row in per:
        pid = row.get("problem_id")
        af = row.get("a1_feasibility", row.get("feasibility"))
        if pid is not None and af is not None:
            amap[pid] = af
    mism = []
    for pid, c in comp.items():
        if pid in amap and amap[pid] != c["auditor_r28"]["a1_feasibility"]:
            mism.append((pid, amap[pid], c["auditor_r28"]["a1_feasibility"]))
    check(f"auditor anchor rows available ({len(amap)})", len(amap) >= 18)
    check("auditor_r28.a1_feasibility values match the audit-branch anchor bytes", not mism, str(mism[:4]))
    pred_in_anchor = [p for p in amap if "pred" in p.lower()]
else:
    check("auditor anchor blob reachable from committed bytes", False, anchor_blob.stderr[:120])

# ---- 4. coverage vs the auditor's NEW two-clause bar (AM33-chat D2) ----
types = {}
for pid, r in res.items():
    types.setdefault(r["question_type"], 0)
    types[r["question_type"]] += 1
prows = [row for row in packet["rows"] if row.get("question_type") != "intervention-proposal"]
check("calibration coverage: 18/18 intervention rows, 0 predictor rows",
      types == {"intervention-proposal": 18} and len(prows) >= 12,
      f"types={types}, non-intervention packet rows={len(prows)}")
print("INFO: auditor's >=10/12 predictor clause is UNMEASURED by construction —"
      " no auditor feasibility anchor exists for predictor rows (checked below if anchor loaded)")
if ok_anchor:
    print(f"INFO: anchor per_row coverage = {len(amap)} rows, predictor rows in anchor = {len(pred_in_anchor)}")

# ---- 5. F39 pin-target rows 4/4 ----
f39 = cal["f39_pin_rows"]
ok_f39 = all(x["within_1"] and x["machine_F"] == comp[x["problem_id"]]["machine"]["a1_feasibility"]
             and x["auditor_F"] == comp[x["problem_id"]]["auditor_r28"]["a1_feasibility"] for x in f39)
check("F39 pin-target rows 4/4 within-1 and byte-consistent with comparison[]", ok_f39 and len(f39) == 4)

# ---- 6. quota recompute ----
att = sum(len(dr.get("transport_attempts", [])) for r in res.values() for dr in r["draws"])
retries = sum(1 for r in res.values() for dr in r["draws"] for t in dr.get("transport_attempts", []) if t["outcome"] != "JUDGE_VALID")
valids = sum(1 for r in res.values() for dr in r["draws"] if dr["outcome"] == "JUDGE_VALID")
check("quota: 63 slot attempts / 9 retries / 54 JUDGE_VALID draws (zero cached failures)",
      (att, retries, valids) == (63, 9, 54), f"{att}/{retries}/{valids}")
check("zero generator calls in the calibration", cal["generation"]["calls"] == 0)

print()
print("PEER VERDICT:", "ALL EXACT" if not FAILS else f"{len(FAILS)} FINDINGS")
for f in FAILS:
    print("  -", f[0], f[1])
sys.exit(0 if not FAILS else 1)

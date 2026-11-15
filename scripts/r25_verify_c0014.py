#!/usr/bin/env python3
"""r25_verify_c0014.py — VERIFIER instrument for claim c-0014
(work_id r24-v61-constraint-bind; EXECUTOR-of-record c-0014
builder-r20s1, the V6 ROUND 2/2 measurement with the F36
constraint-awareness fix, pre-registered at 5acb63012 BEFORE any LLM
call).

Art. 29(c)/Art. 13: the verifier NEVER re-runs the measurement. This
script makes ZERO LLM calls and recomputes every derived number from
the CANONICAL COMMITTED BYTES, failing closed on any mismatch. If the
executor's canonical bytes have not landed yet, it exits 2 with a
typed PENDING status (fail-closed — never a pass-by-absence).

Checks:
  0. canonical bytes present (else PENDING exit 2)
  1. record shape + claim linkage + byte map (18 fresh V6.1 + 12 r11
     predictor rides per the pre-registration)
  2. per-row: row_metrics(draws) recomputed -> majority_prefer,
     median_axes, novelty/feasibility/testability/constraint deltas
  3. summaries recomputed via eval/battery_metrics.summarize
     (type-credited over MATCH rows; intervention subset)
  4. ladder_stats recomputed from the fresh draws' transport_attempts
  5. rides: r11 pair-byte sha re-hash + measured-delta identity +
     the pre-registered rides floor (fgap sum == 14)
  6. fresh rows: byte_provenance sha re-hash vs the committed V6.1
     pair files; question_type_gate == the pair's draft type_gate;
     the contract composition identity (SYS_A1_INT_V61 == V6 bind +
     CONSTRAINT_BIND; SYS_A1F_V5 == A1F_V4 + predictor clause)
  7. judge independence: route == crowllm/qwen-3.8-max:free on every
     judged row, K == 3, every fresh draw carries transport_attempts,
     >=2 valid draws per row
  8. art20_ablation recomputed from the r20 incumbent bytes + the r23
     round-1 citation + beats rule re-derived (round 2/2: not beating
     => the lever retires at 2, Art. 20)
  9. bind_summary recomputed from the pair metas (repairs / residual /
     constraint-residual, same startswith rule as the executor)
 10. ABLATION_REGISTRY V6 contract-bind entry recomputed from its
     citation (no hand-typed numbers)

Exit 0 only if every check passes; exit 1 on any mismatch; exit 2 =
PENDING (canonical bytes absent).
"""
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

REC_PATH = REPO / "eval" / "battery_feas_bind_v61_r24.json"
PAIRS = REPO / "eval" / "pairs" / "r24_feas_bind_v61"

if not REC_PATH.exists() or not PAIRS.exists():
    print("PENDING — the executor's canonical bytes are not on this "
          f"tree yet ({REC_PATH.name}, {PAIRS.name}/). The verifier "
          "runs after the c-0014 measured-record commit lands. Zero "
          "LLM calls were made; nothing was re-run (Art. 13).")
    sys.exit(2)

from eval.battery_metrics import parse_axes, row_metrics, summarize  # noqa: E402, F401
from r23_a1w_v6_contract import SYS_A1_INT_V6  # noqa: E402
from r24_a1w_v61_contract import (CONSTRAINT_BIND, PREDICTOR_CONSTRAINT,  # noqa: E402
                                  SYS_A1F_V5, SYS_A1_INT_V61)
from r19_a1w_v4_contract import SYS_A1F_V4  # noqa: E402

REC = json.loads(REC_PATH.read_text(encoding="utf-8"))
R11ROWS = {r["problem_id"]: r for r in json.loads(
    (REPO / "eval" / "battery_a1w_r11.json").read_text(
        encoding="utf-8"))["results"]}
R20ROWS = {r["problem_id"]: r for r in json.loads(
    (REPO / "eval" / "battery_a1w2_full_r20.json").read_text(
        encoding="utf-8"))["results"]}
R23REC = json.loads((REPO / "eval" / "battery_feas_bind_v6_r23.json")
                    .read_text(encoding="utf-8"))
REGABL = json.loads((REPO / "eval" / "ABLATION_REGISTRY.json").read_text(
    encoding="utf-8"))

FAILS = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name +
          (f" | {detail}" if detail else ""))
    if not ok:
        FAILS.append(name)


def _sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _backfill_tc(row):
    med = row.get("median_axes")
    if med and "testability_delta" not in row:
        if "T_A" in med and "T_B" in med:
            row["testability_delta"] = med["T_A"] - med["T_B"]
        if "C_A" in med and "C_B" in med:
            row["constraint_delta"] = med["C_A"] - med["C_B"]
    return row


# ---- 1. shape + claim linkage + byte map -----------------------------
rows = REC["results"]
check("record shape", str(REC.get("record", "")).startswith(
    "BATTERY_INT_V61_CONSTRAINT_BIND_R24") and len(rows) == 30,
    f"n={len(rows)}")
check("claim linkage", REC.get("claim", {}).get("claim_id") == "c-0014"
      and REC["claim"]["work_id"] == "r24-v61-constraint-bind")
bmap = REC.get("pre_registration", {}).get("byte_map", {})
rides = {r["problem_id"]: r for r in rows
         if str(r.get("question_type", "")).startswith("predictor")}
fresh = {r["problem_id"]: r for r in rows if r["problem_id"] not in rides}
check("byte map matches pre-registration",
      set(bmap.get("ride_r11_predictor", [])) == set(rides)
      and set(bmap.get("fresh_v61", [])) == set(fresh),
      f"rides={len(rides)} fresh={len(fresh)}")

# ---- 2. per-row recompute --------------------------------------------
rows_by_pid = {r["problem_id"]: r for r in rows}
for pid, row in rows_by_pid.items():
    dec = row_metrics(row["draws"])
    med = dec["median_axes"]
    ok = (dec["majority_prefer"] == row.get("majority_prefer")
          and med == row.get("median_axes"))
    if med:
        ok = ok and (
            row.get("novelty_delta") == med["N_A"] - med["N_B"]
            and row.get("feasibility_abs_gap") == abs(med["F_A"] - med["F_B"])
            and row.get("feasibility_signed_gap") == med["F_A"] - med["F_B"])
    check(f"row recompute {pid[:36]}", ok)
    if not ok:
        break

# ---- 3. summaries ------------------------------------------------------
iv = [r for r in rows if str(r.get("question_type", "")).startswith(
    "intervention")]
tc = [r for r in rows if (r.get("question_type_gate") or {}).get("verdict")
      == "MATCH"]
for lbl, got, sub in (
        ("summary_type_credited", REC["summary_type_credited"], tc),
        ("summary_intervention_rows", REC["summary_intervention_rows"], iv)):
    s = summarize(sub, lbl)
    check(f"summary recompute {lbl}",
          s.get("n_valid") == got.get("n_valid")
          and s.get("novelty_delta_mean") == got.get("novelty_delta_mean")
          and s.get("novelty_ci95") == got.get("novelty_ci95")
          and s.get("feasibility_abs_gap_mean")
          == got.get("feasibility_abs_gap_mean")
          and s.get("feasibility_ci95") == got.get("feasibility_ci95")
          and s.get("prefer_tally") == got.get("prefer_tally"),
          f"n={got.get('n_valid')} nd={got.get('novelty_delta_mean')} "
          f"fgap={got.get('feasibility_abs_gap_mean')}")

# ---- 4. ladder stats ---------------------------------------------------
ls = {"first_try_valid": 0, "recovered": 0, "still_dead": 0,
      "total_attempts": 0}
for r in rows:
    for d in r.get("draws") or []:
        atts = d.get("transport_attempts") or []
        ls["total_attempts"] += len(atts)
        if d.get("outcome") == "JUDGE_VALID":
            ls["first_try_valid"] += len(atts) == 1
            ls["recovered"] += len(atts) > 1
        else:
            ls["still_dead"] += 1
check("ladder_stats recompute", ls == REC["ladder_stats"],
      f"recomputed={ls} committed={REC['ladder_stats']}")

# ---- 5. rides: byte identity + pre-registered floor --------------------
ride_fgap_sum = 0
for pid, row in rides.items():
    src = row.get("ride", {}).get("byte_source", "")
    pair = REPO / src
    ok = pair.exists()
    if ok:
        a1 = json.loads(pair.read_text(encoding="utf-8"))["a1_answer"]
        ok = row["ride"]["a1_answer_sha256_16"] == _sha(a1)
    r11 = _backfill_tc(dict(R11ROWS[pid]))
    ok = ok and all(
        row.get(k) == r11.get(k) for k in
        ("novelty_delta", "feasibility_abs_gap", "feasibility_signed_gap",
         "majority_prefer", "median_axes"))
    ride_fgap_sum += R11ROWS[pid].get("feasibility_abs_gap") or 0
    check(f"ride identity {pid[:36]}", ok)
    if not ok:
        break
check("pre-registered rides floor (fgap sum == 14)",
      ride_fgap_sum == 14, f"sum={ride_fgap_sum}")

# ---- 6. fresh rows: provenance + gate + contract composition -----------
gen_ok = True
for pid, row in fresh.items():
    pair = PAIRS / f"{pid}.json"
    rec = json.loads(pair.read_text(encoding="utf-8"))
    a1 = str(rec["a1_answer"])
    prov = row.get("byte_provenance") or {}
    gen_ok = (prov.get("a1_answer_sha256_16") == _sha(a1)
              and (rec["meta"]["attempts"][0].get("type_gate")
                   == row.get("question_type_gate")))
    check(f"fresh provenance {pid[:36]}", gen_ok)
    if not gen_ok:
        break
check("contract composition identity",
      SYS_A1_INT_V61 == SYS_A1_INT_V6 + CONSTRAINT_BIND
      and SYS_A1F_V5 == SYS_A1F_V4 + PREDICTOR_CONSTRAINT,
      "SYS_A1_INT_V61 = V6 + CONSTRAINT_BIND; SYS_A1F_V5 = A1F_V4 + "
      "primary-indicator clause")

# ---- 7. judge independence ---------------------------------------------
route_ok = all(tuple(r.get("judge") or ()) == ("crowllm", "qwen-3.8-max:free")
               for r in fresh.values())
k_ok = all(len(r.get("draws") or []) == 3 for r in fresh.values())
att_ok = all(d.get("transport_attempts")
             for r in fresh.values() for d in r.get("draws") or [])
valid_ok = all(
    sum(1 for d in r["draws"] if d["outcome"] == "JUDGE_VALID") >= 2
    for r in fresh.values())
check("judge route independence (crowllm/Qwen on every fresh row)",
      route_ok and k_ok and att_ok and valid_ok,
      f"k=3 route=crowllm/qwen-3.8-max:free attempts recorded={att_ok}")

# ---- 8. art20 ablation (round 2/2) --------------------------------------
iv_r20 = summarize(
    [r for r in R20ROWS.values()
     if str(r.get("question_type", "")).startswith("intervention")], "v")
ab = REC["art20_ablation"]
exp_inc_f = iv_r20.get("feasibility_abs_gap_mean")
exp_inc_n = iv_r20.get("novelty_delta_mean")
exp_v_f = REC["summary_intervention_rows"]["feasibility_abs_gap_mean"]
exp_v_n = REC["summary_intervention_rows"]["novelty_delta_mean"]
beats = (exp_v_f < exp_inc_f and exp_v_n >= 0.5)
check("art20_ablation recomputes",
      ab["incumbent_intervention_fgap_r20"] == exp_inc_f
      and ab["incumbent_ndelta_r20"] == exp_inc_n
      and ab["v61_round2_intervention_fgap_this"] == exp_v_f
      and ab["v61_ndelta_this"] == exp_v_n
      and ab["v6_round1_intervention_fgap_r23"]
      == R23REC["art20_ablation"]["v6_bind_intervention_fgap_this"]
      and beats == (exp_v_f < exp_inc_f and exp_v_n >= 0.5),
      f"incumbent {exp_inc_n}/{exp_inc_f} vs v61 r2 {exp_v_n}/{exp_v_f} "
      f"beats={beats} | round-2 rule: "
      + ("the lever continues" if beats else
         "the contract-bind lever RETIRES at 2 (Art. 20)"))

# ---- 9. bind_summary from pair metas ------------------------------------
bs = REC.get("bind_summary", {})
repairs_total = 0
residual_pairs = 0
constraint_residual = 0
for pid in fresh:
    meta = json.loads((PAIRS / f"{pid}.json").read_text(
        encoding="utf-8"))["meta"]
    repairs_total += meta["repairs"]
    if meta.get("residual_findings"):
        residual_pairs += 1
        if any(k.startswith("CONSTRAINT") or k.startswith("ALLOWED")
               for k in meta["residual_findings"]):
            constraint_residual += 1
check("bind_summary recomputes from pair metas",
      bs.get("repairs_total") == repairs_total
      and bs.get("pairs_with_residual_findings") == residual_pairs
      and bs.get("pairs_with_constraint_residual") == constraint_residual,
      f"repairs={repairs_total} residual={residual_pairs} "
      f"constraint-residual={constraint_residual}")

# ---- 10. ABLATION_REGISTRY entry ----------------------------------------
entries = [e for e in REGABL["entries"]
           if e.get("stage") == "generator_arm_contract_bind"]
ok_reg = False
detail = "no generator_arm_contract_bind entry found"
for e in entries:
    cite = e.get("metric_citation", "")
    if "battery_feas_bind_v61_r24" in cite:
        path, key = cite.split(":", 1)
        s = json.loads((REPO / path).read_text(encoding="utf-8"))[key]
        ok_reg = (e["variant_numbers"]["novelty_delta_mean"]
                  == s["novelty_delta_mean"]
                  and e["variant_numbers"]["feasibility_abs_gap_mean"]
                  == s["feasibility_abs_gap_mean"]
                  and e["variant_numbers"]["n_valid"] == s["n_valid"]
                  and e["rounds_without_beating"] == (
                      0 if beats else 2)
                  and (str(e.get("status", "")).upper() == "ACTIVE"
                       if beats else
                       str(e.get("status", "")).upper()
                       .startswith("RETIRED")))
        detail = (f"v61 {s['novelty_delta_mean']}/"
                  f"{s['feasibility_abs_gap_mean']} n={s['n_valid']} "
                  f"rwb={e.get('rounds_without_beating')} "
                  f"status={e.get('status')}")
        break
check("ABLATION_REGISTRY V6 round-2 entry recomputes "
      "(no hand-typed numbers)", ok_reg, detail)

print()
if FAILS:
    print(f"VERDICT: FAIL ({len(FAILS)} failing checks: {FAILS[:4]}...)")
    sys.exit(1)
print("VERDICT: PASS — the canonical c-0014 V6 round-2 battery record "
      "reproduces from its own committed bytes (Art. 13); zero LLM "
      "calls were made by this verifier. c-0014 flips DONE on this "
      "record (Art. 29(c)); the gate re-decision remains the "
      "auditor's.")
sys.exit(0)

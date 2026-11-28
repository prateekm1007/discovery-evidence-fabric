#!/usr/bin/env python3
"""r23_verify_c0006.py — VERIFIER instrument for claim c-0012
(work_id r22-feas-repair-b18; EXECUTOR-of-record c-0006 builder-r20s1,
canonical battery bytes b20954150 as completed by the peer's push-mutex
win — see RACE #9, preserved out-of-repo).

Art. 29(c)/Art. 13: the verifier NEVER re-runs the measurement. This
script makes ZERO LLM calls and recomputes every derived number from
the CANONICAL COMMITTED BYTES, failing closed on any mismatch:

  1. per-row: row_metrics(draws) recomputed -> majority_prefer,
     median_axes, novelty/feasibility/testability/constraint deltas
     (30/30 rows: 18 fresh V5-repair + 12 r11 rides)
  2. all four summaries recomputed via eval/battery_metrics.summarize
     -> compared to the committed summary objects
  3. ladder_stats recomputed from the fresh draws' transport_attempts
  4. rides: r11 pair-byte sha re-hash + measured-delta identity vs the
     r11 committed rows (byte-identical rides rule, AM19 sec.2) +
     the pre-registered rides floor (fgap sum == 14)
  5. fresh rows: byte_provenance sha re-hash vs the committed V5 pair
     files; question_type_gate == the pair's draft type_gate;
     AUDIT_HEADER presence == meta.audit_block
  6. generation_record + repair_leg_summary recomputed from the pair
     metas (repairs / residual findings / audit blocks)
  7. judge independence: route == crowllm/qwen-3.8-max:free on every
     judged row, K == 3, every fresh draw carries transport_attempts
  8. art20_ablation recomputed from the r20 incumbent bytes +
     beats_incumbent re-derived
  9. ABLATION_REGISTRY V5 entry recomputed from the cited record
     (no hand-typed numbers)

Exit 0 only if every check passes; any mismatch prints FAIL, exits 1.
"""
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))
from eval.battery_metrics import parse_axes, row_metrics, summarize  # noqa: E402
from r22_a1w_v5_repair import AUDIT_HEADER  # noqa: E402

REC = json.loads((REPO / "eval" / "battery_feas_repair_r22.json").read_text(
    encoding="utf-8"))
R11ROWS = {r["problem_id"]: r for r in json.loads(
    (REPO / "eval" / "battery_a1w_r11.json").read_text(
        encoding="utf-8"))["results"]}
R20ROWS = {r["problem_id"]: r for r in json.loads(
    (REPO / "eval" / "battery_a1w2_full_r20.json").read_text(
        encoding="utf-8"))["results"]}
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
        row["tc_backfilled_from"] = "median_axes (committed bytes)"
    return row


rows = REC["results"]
check("record shape", REC.get("record", "").startswith(
    "BATTERY_INT_FREPAIR_R22") and len(rows) == 30,
    f"n={len(rows)}")
check("claim linkage", REC["claim"]["claim_id"] == "c-0006"
      and REC["claim"]["work_id"] == "r22-feas-repair-b18")

rides = {r["problem_id"]: r for r in rows
         if str(r.get("question_type", "")).startswith("predictor")}
fresh = {r["problem_id"]: r for r in rows if r["problem_id"] not in rides}
check("byte map", len(rides) == 12 and len(fresh) == 18,
      f"rides={len(rides)} fresh={len(fresh)}")

# ---- 1. per-row recompute --------------------------------------------
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
            and row.get("feasibility_signed_gap") == med["F_A"] - med["F_B"]
            and row.get("testability_delta") == med["T_A"] - med["T_B"]
            and row.get("constraint_delta") == med["C_A"] - med["C_B"])
    check(f"row recompute {pid[:36]}", ok)
    if not ok:
        break

# ---- 2. summaries -----------------------------------------------------
iv = [r for r in rows if str(r.get("question_type", "")).startswith(
    "intervention")]
pd_ = [r for r in rows if str(r.get("question_type", "")).startswith(
    "predictor")]
tc = [r for r in rows if (r.get("question_type_gate") or {}).get("verdict")
      == "MATCH"]
for lbl, got, sub in (
        ("summary_type_credited", REC["summary_type_credited"], tc),
        ("summary_intervention_rows", REC["summary_intervention_rows"], iv),
        ("summary_predictor_rows", REC["summary_predictor_rows"], pd_),
        ("summary_all_valid", REC["summary_all_valid"], rows)):
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

# ---- 3. ladder stats --------------------------------------------------
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

# ---- 4. rides: byte identity + pre-registered floor -------------------
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

# ---- 5. fresh rows: provenance + gate + audit block -------------------
gen_ok = True
for pid, row in fresh.items():
    pair = REPO / "eval" / "pairs" / "r22_feas_repair_v5" / f"{pid}.json"
    rec = json.loads(pair.read_text(encoding="utf-8"))
    a1 = str(rec["a1_answer"])
    prov = row.get("byte_provenance") or {}
    gen_ok = (prov.get("a1_answer_sha256_16") == _sha(a1)
              and (rec["meta"]["attempts"][0].get("type_gate")
                   == row.get("question_type_gate"))
              and bool(rec["meta"].get("audit_block"))
              == (AUDIT_HEADER in a1))
    check(f"fresh provenance {pid[:36]}", gen_ok)
    if not gen_ok:
        break

# ---- 6. generation_record + repair_leg_summary ------------------------
gr = REC["generation_record"]
gr_ok = all(
    g["repairs"] == json.loads((REPO / "eval" / "pairs" / "r22_feas_repair_v5"
                                / f"{g['problem_id']}.json").read_text(
                                    encoding="utf-8"))["meta"]["repairs"]
    and (g["residual_findings"] == json.loads(
        (REPO / "eval" / "pairs" / "r22_feas_repair_v5"
         / f"{g['problem_id']}.json").read_text(encoding="utf-8"))
        ["meta"]["residual_findings"] or g["residual_findings"] == "CLEAN")
    and g["audit_block"] == json.loads(
        (REPO / "eval" / "pairs" / "r22_feas_repair_v5"
         / f"{g['problem_id']}.json").read_text(encoding="utf-8"))
    ["meta"]["audit_block"]
    for g in gr)
check("generation_record recomputes from pair metas", gr_ok,
      f"n={len(gr)}")
repairs_total = sum(g["repairs"] for g in gr)
residual = sum(1 for g in gr
               if g["residual_findings"] not in (None, [], "CLEAN"))
audit_blocks = sum(1 for g in gr if g.get("audit_block"))
rls = REC["repair_leg_summary"]
check("repair_leg_summary recompute",
      rls["repairs_total"] == repairs_total
      and rls["pairs_with_residual_findings"] == residual
      and rls["pairs_with_audit_block"] == audit_blocks,
      f"repairs={repairs_total} residual={residual} audit={audit_blocks}")

# ---- 7. judge independence --------------------------------------------
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

# ---- 8. art20 ablation ------------------------------------------------
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
      and ab["v5_intervention_fgap_this"] == exp_v_f
      and ab["v5_ndelta_this"] == exp_v_n
      and ab["beats_incumbent"] == beats,
      f"incumbent {exp_inc_n}/{exp_inc_f} vs v5 {exp_v_n}/{exp_v_f} "
      f"beats={beats}")

# ---- 9. ABLATION_REGISTRY V5 entry ------------------------------------
v5 = next(e for e in REGABL["entries"]
          if "V5 feasibility-repair leg" in e.get("variant", ""))
path, key = v5["metric_citation"].split(":")
s = json.loads((REPO / path).read_text(encoding="utf-8"))[key]
inc = v5["incumbent_numbers"]
expect_beats = (s["novelty_delta_mean"] >= inc["novelty_delta_mean"]
                and s["feasibility_abs_gap_mean"]
                <= inc["feasibility_abs_gap_mean"]
                and (s["novelty_delta_mean"] > inc["novelty_delta_mean"]
                     or s["feasibility_abs_gap_mean"]
                     < inc["feasibility_abs_gap_mean"]))
check("ABLATION_REGISTRY V5 entry recomputes (no hand-typed numbers)",
      v5["variant_numbers"]["novelty_delta_mean"] == s["novelty_delta_mean"]
      and v5["variant_numbers"]["feasibility_abs_gap_mean"]
      == s["feasibility_abs_gap_mean"]
      and v5["variant_numbers"]["n_valid"] == s["n_valid"]
      and v5["beats_incumbent"] == expect_beats,
      f"v5 {s['novelty_delta_mean']}/{s['feasibility_abs_gap_mean']} "
      f"n={s['n_valid']} beats={expect_beats}")

print()
if FAILS:
    print(f"VERDICT: FAIL ({len(FAILS)} failing checks: {FAILS[:4]}...)")
    sys.exit(1)
print("VERDICT: PASS — the canonical c-0006 battery record reproduces "
      "from its own committed bytes (Art. 13); zero LLM calls were "
      "made by this verifier.")
sys.exit(0)

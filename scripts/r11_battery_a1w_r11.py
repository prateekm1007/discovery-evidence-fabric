#!/usr/bin/env python3
"""Battery r11 — the AM16 D1 measurement: the WEIGHT-BOUND arms (the
F30 isolated-frontier fix) vs the SAME curated baselines as batteries
r7/r8/r9/r10 (assembly identical), judged by the ACCEPTED judge (F28
CLOSED-ACCEPTED, AM12 paragraph 1: the k=3 majority + per-axis-median
machinery, calibrated v2 axis suffix, headline kappa 0.556 disclosed,
the eval-new01 adjudication applied), judge != generator
(crowllm/Qwen vs zai/GLM).

Derived from the audited r9/r10 measurement machinery (Art. XXVII
provenance), retargeted to the r11_a1w_r1 arm. The 12 predictor arms
are the r10 BYTE-IDENTICAL records re-judged (parity measured on
identical bytes); the 18 intervention arms are the new
SYS_A1_INT_WB generations — battery r11 isolates the weight-bound
contract change to the intervention arm exactly as r10 isolated F31.

AM16 D1 acceptance: intervention feasibility |gap| <= 0.25 (or
SHARPLY REDUCED — typed movement vs r10's 2.389) AND novelty delta
>= 0.5 on >= 30 pairs, with predictor parity maintained (predictor
rows re-judged from identical bytes vs r10's 1.167). The per-type
summaries (summary_intervention_rows / summary_predictor_rows) are
the primary frontier read; the type-credited all-pairs form and the
all-valid sensitivity ride alongside. MISMATCH pairs stay recorded
but are excluded from clause credit. The gate decision stays the
AUDITOR'S (Art. XXVI/LXXXVI-2).

Judge env overrides (R12_JUDGE_PROVIDER/R12_JUDGE_MODEL/R12_PACE_S)
exist ONLY for an auditor-adjudicated substitute route — never a
coder-silent swap (Art. XXX).
"""
import json
import os
import sys
import time
import math
import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()
os.environ.setdefault("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")
os.environ.setdefault("FABRIC_BREAKER_THRESHOLD", "60")

from eval.run import _rubric_prompt, _judge_judgment_call  # noqa: E402
from discovery_fabric.engine import llm_economy as econ  # noqa: E402
from r13_question_type_gate import gate_question_type  # noqa: E402

JUDGE = (os.environ.get("R12_JUDGE_PROVIDER", "crowllm"),
         os.environ.get("R12_JUDGE_MODEL", "qwen-3.8-max:free"))
PACE_S = float(os.environ.get("R12_PACE_S", "13.0"))
K = 3
AXIS_SUFFIX = (REPO / "scripts" / "_f28_axis_suffix_v2.txt").read_text()

A1F_DIR = REPO / "eval" / "pairs" / "r11_a1w_r1"
R8_RECORD = REPO / "eval" / "battery_a1t_r10.json"
PARTIAL = REPO / "eval" / "battery_a1w_r11.partial.json"

EVAL_NEW01_ADJUDICATION = {
    "problem_id": "eval-new01-supercap-dryout",
    "am11_section": "3 (eval-new01 adjudication, Art. XXVI), adopted "
                    "by AM12 paragraph 1 with the judge acceptance",
    "holding": ("the judge's unanimous baseline preference on this pair "
                "is axis-weighting (operational familiarity), not a "
                "calibration error; A's novelty departure counts on the "
                "novelty axis; familiarity is a feasibility "
                "consideration already carried by the feasibility gap"),
    "application": ("the pair's measured axes ride the record UNTOUCHED "
                    "with an adjudication_note; the auditor applies "
                    "their own per-axis re-judgment (AM12 direction 2) "
                    "on this pair first"),
}

NEW07 = "eval-new07-transformer-dga-predictor"


def parse_axes(jc):
    if jc.get("outcome") != "JUDGE_VALID":
        return None
    import re
    raw = str(jc.get("raw") or "")
    for chunk in reversed(re.findall(r"\{[^{}]*\}", raw, re.S)):
        try:
            obj = json.loads(chunk)
        except json.JSONDecodeError:
            continue
        vals, ok = {}, True
        for arm in ("A", "B"):
            for ax in ("N", "F", "T", "C"):
                try:
                    iv = int(str(obj.get(f"{ax}_{arm}")).strip())
                except (TypeError, ValueError):
                    ok = False
                    break
                if not (1 <= iv <= 5):
                    ok = False
                    break
                vals[f"{ax}_{arm}"] = iv
            if not ok:
                break
        if ok:
            return vals
    return None


def _r9_reference() -> dict:
    """Per-pair battery r10 medians (the type-aware arms) so the
    r10->r11 movement reads from this record without a join."""
    if not R8_RECORD.exists():
        return {}
    try:
        r10 = json.loads(R8_RECORD.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    out = {}
    for r in r10.get("results", []):
        med = r.get("median_axes") or {}
        if med:
            out[r["problem_id"]] = {
                "n_delta_r10": r.get("novelty_delta"),
                "f_abs_gap_r10": r.get("feasibility_abs_gap"),
                "f_signed_gap_r10": r.get("feasibility_signed_gap"),
                "prefer_r10": r.get("majority_prefer"),
            }
    return out


def main():
    plist = json.loads((REPO / "eval" / "problems.json").read_text())
    plist = plist if isinstance(plist, list) else plist.get("problems", [])
    probs = {str(p.get("problem_id") or p.get("id")): p for p in plist}
    for p in json.loads((REPO / "eval" / "problems_dev12.json")
                        .read_text())["problems"]:
        probs.setdefault(p["problem_id"], p)

    r10_ref = _r10_reference()
    pairs = []
    for pid in sorted(probs):
        a1f = A1F_DIR / f"{pid}.json"
        if not a1f.exists():
            continue
        rec = json.loads(a1f.read_text(encoding="utf-8"))
        a1 = str(rec.get("a1_answer") or "")
        arm = str(rec.get("a1_source") or "")
        base = ""
        b_src = ""
        d12 = REPO / "eval" / "pairs" / "dev12_fresh" / f"{pid}.json"
        cur = REPO / "eval" / "baselines_curated" / f"{pid}.json"
        if d12.exists():
            base = str(json.loads(d12.read_text()).get(
                "baseline_answer") or "")
            b_src = "CURATED_COMMITTED_dev12"
        if not base.strip() and cur.exists():
            base = str(json.loads(cur.read_text()).get(
                "baseline_answer") or "")
            b_src = "CURATED_STANDARD_REFERENCE_builder"
        if a1.strip() and base.strip():
            tg = gate_question_type(a1, probs[pid])
            pairs.append({"problem_id": pid, "prob": probs[pid],
                          "a1": a1[:7000], "base": base[:7000],
                          "b_src": b_src, "tg": tg, "arm": arm,
                          "critic_verdict": rec.get("critic_verdict")})
    print(f"[r11] pool: {len(pairs)} pairs "
          f"(A=r11_a1w_r1 WEIGHT-BOUND, B=curated baselines "
          f"identical to r7/r8/r9/r10)", flush=True)
    if len(pairs) < 29:
        print(f"[r11] BLOCKED_INCOMPLETE_POOL: {len(pairs)} pairs "
              f"assembled (need 29 or 30); refusing a sub-29 gate "
              f"measurement", flush=True)
        return 2

    results = []
    t0 = time.time()
    for i, pr in enumerate(pairs):
        pid = pr["problem_id"]
        prompt = _rubric_prompt(pr["prob"], pr["a1"], pr["base"],
                                None) + AXIS_SUFFIX
        draws = []
        for k in range(K):
            econ.reset_governor(f"r11:{pid}:{k}")
            jc = _judge_judgment_call(JUDGE[0], JUDGE[1], prompt,
                                      max_tokens=4000)
            draws.append({"k": k, "outcome": jc.get("outcome"),
                          "axes": parse_axes(jc),
                          "prefer": (jc.get("valid") or {}).get("prefer")})
            time.sleep(PACE_S)
        prefs = [d["prefer"] for d in draws if d.get("prefer")]
        pref_counts = {p: prefs.count(p) for p in set(prefs)}
        maj = max(pref_counts, key=pref_counts.get) if prefs else None
        axis_draws = [d["axes"] for d in draws if d.get("axes")]
        med = {}
        if axis_draws:
            for key in axis_draws[0]:
                vals = sorted(a[key] for a in axis_draws)
                med[key] = vals[len(vals)//2]
        row = {"problem_id": pid,
               "a1_arm": pr["arm"],
               "question_type": pr["prob"].get("question_type"),
               "question_type_gate": pr["tg"],
               "critic_verdict": pr["critic_verdict"],
               "baseline_source": pr["b_src"],
               "judge": list(JUDGE), "draws": draws,
               "majority_prefer": maj, "median_axes": med}
        if med:
            row["novelty_delta"] = med["N_A"] - med["N_B"]
            row["feasibility_abs_gap"] = abs(med["F_A"] - med["F_B"])
            row["feasibility_signed_gap"] = med["F_A"] - med["F_B"]
            row["testability_delta"] = med["T_A"] - med["T_B"]
            row["constraint_delta"] = med["C_A"] - med["C_B"]
        if pid in r10_ref:
            row["r10_battery_reference"] = r10_ref[pid]
        if pid == EVAL_NEW01_ADJUDICATION["problem_id"]:
            row["adjudication_note"] = EVAL_NEW01_ADJUDICATION["holding"]
        results.append(row)
        print(f"  [{i+1}/{len(pairs)}] {pid[:34]:<36} "
              f"gate={pr['tg']['verdict']} "
              f"nd={row.get('novelty_delta')} "
              f"fgap={row.get('feasibility_abs_gap')} "
              f"sg={row.get('feasibility_signed_gap')} "
              f"td={row.get('testability_delta')} "
              f"cd={row.get('constraint_delta')} "
              f"pref={maj} {pref_counts}", flush=True)
        PARTIAL.write_text(
            json.dumps(results, indent=1, default=str) + "\n",
            encoding="utf-8")

    def _summary(rows, label):
        valid = [r for r in rows if r.get("median_axes")]
        n = len(valid)
        if not n:
            return {"n_valid": 0, "label": label}

        def _mean(vals):
            return round(sum(vals)/len(vals), 3) if vals else None

        def _tci(vals):
            m = sum(vals)/len(vals)
            sd = math.sqrt(sum((x-m)**2 for x in vals)/(len(vals)-1))
            se = sd/math.sqrt(len(vals))
            return round(m, 3), round(m-1.96*se, 3), round(m+1.96*se, 3)

        nd = [r["novelty_delta"] for r in valid]
        fg = [r["feasibility_abs_gap"] for r in valid]
        nd_m, nd_lo, nd_hi = _tci(nd)
        fg_m, fg_lo, fg_hi = _tci(fg)
        per_axis_means = {}
        for ax, key in (("N", "novelty_delta"),
                        ("F_signed", "feasibility_signed_gap"),
                        ("T", "testability_delta"),
                        ("C", "constraint_delta")):
            per_axis_means[ax] = _mean([r[key] for r in valid])
        a1w = sum(1 for r in valid if r["majority_prefer"] == "A")
        bw = sum(1 for r in valid if r["majority_prefer"] == "B")
        n_mismatch = sum(1 for r in rows
                         if (r.get("question_type_gate") or {}).get(
                             "verdict") == "MISMATCH")
        both_move = [r for r in valid if "r10_battery_reference" in r]
        return {
            "label": label,
            "n_valid": n,
            "novelty_delta_mean": nd_m,
            "novelty_ci95": [nd_lo, nd_hi],
            "feasibility_abs_gap_mean": fg_m,
            "feasibility_ci95": [fg_lo, fg_hi],
            "per_axis_means_A_minus_B": per_axis_means,
            "AM14_D5_point_estimate": {
                "novelty_clause_pass": nd_m >= 0.5,
                "feasibility_clause_pass": fg_m <= 0.25,
                "both_simultaneous_pass": (nd_m >= 0.5 and fg_m <= 0.25
                                           and n >= 30),
                "form": "mean over judged pairs (the Art. LXXXVI gate "
                        "form; AM14 D5 thresholds verbatim)",
                "threshold_provenance": "owner directive 2026-11-15 "
                                        "(AM14 D5: feasibility |gap| "
                                        "<=0.25 AND novelty delta "
                                        ">=0.5 on >=30 pairs); class "
                                        "BUYER_DEFINED",
            },
            "r7_comparable_CI": {
                "novelty_clause_pass": nd_lo >= 0.5,
                "feasibility_clause_pass": fg_hi <= 0.25,
                "both_simultaneous_pass": (nd_lo >= 0.5 and fg_hi <= 0.25
                                           and n >= 30),
                "form": "batteries r7/r8's conservative t-CI form — "
                        "disclosed for cross-battery comparability",
            },
            "prefer_tally": {"a1_arms": a1w, "baseline": bw,
                             "tie": n - a1w - bw},
            "question_type_mismatches_in_scope": n_mismatch,
            "r10_to_r11_movement": {
                "note": "means over pairs carrying an r10 battery "
                        "reference row",
                "novelty_delta_r10_mean": _mean([
                    r["r10_battery_reference"]["n_delta_r10"]
                    for r in both_move]),
                "novelty_delta_r11_mean": _mean([
                    r["novelty_delta"] for r in both_move]),
                "feasibility_abs_gap_r10_mean": _mean([
                    r["r10_battery_reference"]["f_abs_gap_r10"]
                    for r in both_move]),
                "feasibility_abs_gap_r11_mean": _mean([
                    r["feasibility_abs_gap"] for r in both_move]),
            },
        }

    record = {
        "record": "BATTERY_A1W_R11/1.0.0",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "arms": {
            "A": "WEIGHT-BOUND GLM generations (eval/pairs/r11_a1w_r1;"
                 " the AM16 D1 F30 fix): the 18 intervention-proposal "
                 "arms regenerated under SYS_A1_INT_WB (novelty lives "
                 "in the MECHANISM, weight lives in the "
                 "IMPLEMENTATION; bill itemized against the standard "
                 "practice's own bill); the 12 predictor arms are the "
                 "r10 BYTE-IDENTICAL records reused (parity on "
                 "identical bytes); every answer passed the AM14 D3 "
                 "question-type gate in-process",
            "B": "CURATED baselines — assembly IDENTICAL to batteries "
                 "r7/r8/r9/r10 (only arm A changed, isolating the "
                 "weight-bound contract change to the intervention "
                 "arm)",
        },
        "judge": {
            "route": list(JUDGE),
            "route_provenance": ("F28 CLOSED-ACCEPTED (AM12 paragraph "
                                 "1): k=3 majority + per-axis median, "
                                 "calibrated v2 axis suffix, headline "
                                 "kappa 0.556 disclosed, novelty-sign "
                                 "0.9, bench-p02 correct; env overrides "
                                 "ONLY for an auditor-adjudicated "
                                 "substitute (never a coder-silent "
                                 "swap, Art. XXX)"),
            "independence": "crowllm/Qwen vs zai/GLM generator — "
                            "provider AND family independent",
            "k": K, "pace_s": PACE_S,
            "eval_new01_adjudication_applied": EVAL_NEW01_ADJUDICATION,
        },
        "results": results,
        "summary_intervention_rows": _summary(
            [r for r in results if str(r.get("question_type", "")).startswith("intervention")],
            "INTERVENTION rows only — the PRIMARY AM16 D1 frontier "
            "read (feasibility |gap| movement vs r10's 2.389; novelty "
            "must stay >= 0.5)"),
        "summary_predictor_rows": _summary(
            [r for r in results if str(r.get("question_type", "")).startswith("predictor")],
            "PREDICTOR rows only (r10 byte-identical records re-judged "
            "— parity vs r10's 1.167)"),
        "summary_type_credited": _summary(
            [r for r in results
             if (r.get("question_type_gate") or {}).get("verdict")
             == "MATCH"],
            "type-MATCH pairs only — wrong-type novelty does NOT "
            "count (AM14 sec.2); MISMATCH pairs stay recorded but "
            "excluded"),
        "summary_all_valid": _summary(
            results, "all valid pairs (unfiltered sensitivity — the "
                     "r9-comparable form)"),
        "gate_note": ("MEASUREMENT for the auditor (Art. XXVI/LXXXVI-2): "
                      "the AM16 D1 acceptance — intervention "
                      "feasibility |gap| <= 0.25 OR sharply reduced "
                      "(typed movement vs r10's 2.389) AND novelty "
                      "delta >= 0.5 on >= 30 pairs, predictor parity "
                      "maintained — read on the per-type summaries "
                      "(primary) plus the type-credited all-pairs "
                      "form; MISMATCH pairs excluded from clause "
                      "credit, still recorded; the authoritative gate "
                      "re-decision is the auditor's per-axis "
                      "re-judgment on the committed bytes"),
    }
    out = REPO / "eval" / "battery_a1w_r11.json"
    out.write_text(json.dumps(record, indent=1, default=str) + "\n",
                   encoding="utf-8")
    iv = record["summary_intervention_rows"]
    pd_ = record["summary_predictor_rows"]
    stc = record["summary_type_credited"]
    s = record["summary_all_valid"]
    print(f"\n[r11] INTERVENTION rows (PRIMARY AM16 D1 frontier): "
          f"n={iv['n_valid']} | nov Δ {iv['novelty_delta_mean']} "
          f"CI {iv['novelty_ci95']} | feas |gap| "
          f"{iv['feasibility_abs_gap_mean']} CI "
          f"{iv['feasibility_ci95']} (r10 was 2.389)")
    print(f"[r11] PREDICTOR rows (parity, identical bytes re-judged): "
          f"n={pd_['n_valid']} | nov Δ {pd_['novelty_delta_mean']} "
          f"| feas |gap| {pd_['feasibility_abs_gap_mean']} "
          f"(r10 was 1.167)")
    print(f"[r11] type-credited all-pairs: n={stc['n_valid']} "
          f"nov Δ {stc['novelty_delta_mean']} CI "
          f"{stc['novelty_ci95']} | feas |gap| "
          f"{stc['feasibility_abs_gap_mean']} CI "
          f"{stc['feasibility_ci95']} | prefer "
          f"{stc['prefer_tally']} | mismatches "
          f"{stc['question_type_mismatches_in_scope']}")
    print(f"[r11] r10->r11 movement: {stc['r10_to_r11_movement']}")
    print(f"[r11] ALL-VALID sensitivity: n={s['n_valid']} "
          f"nov Δ {s['novelty_delta_mean']} feas |gap| "
          f"{s['feasibility_abs_gap_mean']}")
    print(f"-> {out}")


if __name__ == "__main__":
    raise SystemExit(main() or 0)

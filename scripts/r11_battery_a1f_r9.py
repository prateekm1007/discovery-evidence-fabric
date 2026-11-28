#!/usr/bin/env python3
"""Battery r9 — the AM12 direction-3 measurement on the SYS_A1F_V3
SAME-CLASS-NOVELTY arms (eval/pairs/r11_a1f_r3, GLM generator) vs the
SAME curated baselines as batteries r7/r8 (assembly identical: 10
CURATED_COMMITTED_dev12 + 20 CURATED_STANDARD_REFERENCE_builder), judged
by the ACCEPTED judge (F28 CLOSED-ACCEPTED, AM12 paragraph 1: the k=3
majority + per-axis-median machinery, calibrated v2 axis suffix,
headline kappa 0.556 disclosed, the eval-new01 adjudication applied),
judge != generator (crowllm/Qwen vs zai/GLM).

This driver is session-2's adaptation of the AUTHORITATIVE battery r8
driver (session-1's committed scripts/r11_battery_a1f_r8.py — the one
that measured r8; pusher-wins) retargeted to the r3 arm. The
component-wise A1F_DIR construction is preserved (their 37745e315
self-caught: a sed retarget of a slash-string missed the component-wise
path — same bug class not repeated here).

AM12 acceptance (direction 1 verbatim, applied to the direction-3
iteration): novelty delta >= 0.5 AND feasibility |gap| <= 0.25
SIMULTANEOUSLY on n=30, per-axis. BOTH forms reported:
  - AM12_point_estimate (the Art. LXXXVI gate form: mean over pairs)
  - r7_comparable_CI (battery r7/r8's conservative t-CI form)
The gate decision stays the AUDITOR'S (Art. XXVI/LXXXVI-2).

eval-new07 admissibility: the r3 set's one typed-KILL-with-recheck
pair rides the pool WITH full disclosure (critic verdict + the
instrument_recheck pointer on the row); the summary reports the
all-pairs AND the excluding-new07 sensitivity; which n governs the
acceptance is the auditor's call (Art. XXV). The pool guard accepts
29 or 30 pairs (29 = the auditor-excluded sensitivity), refuses less.

Judge env overrides (R12_JUDGE_PROVIDER/R12_JUDGE_MODEL/R12_PACE_S)
exist ONLY for an auditor-adjudicated substitute route — never a
coder-silent swap (Art. XXX).

BLOCKED-ON-KEY state: the accepted crowllm route needs the
CROWLLM_API_KEY in the executing session (this session's census:
absent here; session-1 holds the live key — either session runs it,
one measurement owner is enough).
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

JUDGE = (os.environ.get("R12_JUDGE_PROVIDER", "crowllm"),
         os.environ.get("R12_JUDGE_MODEL", "qwen-3.8-max:free"))
PACE_S = float(os.environ.get("R12_PACE_S", "13.0"))
K = 3
AXIS_SUFFIX = (REPO / "scripts" / "_f28_axis_suffix_v2.txt").read_text()

A1F_DIR = REPO / "eval" / "pairs" / "r11_a1f_r3"
R8_RECORD = REPO / "eval" / "battery_a1f_r8.json"
PARTIAL = REPO / "eval" / "battery_a1f_r9.partial.json"

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


def _r8_reference() -> dict:
    """Per-pair battery r8 medians (the SYS_A1F_V2 arms) so the
    V2->V3 movement reads from this record without a join."""
    if not R8_RECORD.exists():
        return {}
    try:
        r8 = json.loads(R8_RECORD.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    out = {}
    for r in r8.get("results", []):
        med = r.get("median_axes") or {}
        if med:
            out[r["problem_id"]] = {
                "n_delta_r8": r.get("novelty_delta"),
                "f_abs_gap_r8": r.get("feasibility_abs_gap"),
                "f_signed_gap_r8": r.get("feasibility_signed_gap"),
                "prefer_r8": r.get("majority_prefer"),
            }
    return out


def main():
    plist = json.loads((REPO / "eval" / "problems.json").read_text())
    plist = plist if isinstance(plist, list) else plist.get("problems", [])
    probs = {str(p.get("problem_id") or p.get("id")): p for p in plist}
    for p in json.loads((REPO / "eval" / "problems_dev12.json")
                        .read_text())["problems"]:
        probs.setdefault(p["problem_id"], p)

    r8_ref = _r8_reference()
    pairs = []
    for pid in sorted(probs):
        a1f = A1F_DIR / f"{pid}.json"
        if not a1f.exists():
            continue
        rec = json.loads(a1f.read_text(encoding="utf-8"))
        a1 = str(rec.get("a1_answer") or "")
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
            pairs.append({"problem_id": pid, "prob": probs[pid],
                          "a1": a1[:7000], "base": base[:7000],
                          "b_src": b_src,
                          "critic_verdict": rec.get("critic_verdict"),
                          "instrument_recheck": bool(
                              rec.get("instrument_recheck"))})
    print(f"[r9] pool: {len(pairs)} pairs "
          f"(A=r11_a1f_r3 SYS_A1F_V3, B=curated baselines identical "
          f"to r7/r8)", flush=True)
    if len(pairs) < 29:
        print(f"[r9] BLOCKED_INCOMPLETE_POOL: {len(pairs)} pairs "
              f"assembled (need 29 or 30 — 30 all-pairs, 29 the "
              f"auditor-excluded-new07 sensitivity); refusing a "
              f"sub-29 gate measurement", flush=True)
        return 2

    results = []
    t0 = time.time()
    for i, pr in enumerate(pairs):
        pid = pr["problem_id"]
        prompt = _rubric_prompt(pr["prob"], pr["a1"], pr["base"],
                                None) + AXIS_SUFFIX
        draws = []
        for k in range(K):
            econ.reset_governor(f"r9:{pid}:{k}")
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
               "a1_arm": "A1F_V3_same_class_novelty_GLM",
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
        if pid == NEW07:
            row["admissibility_disclosure"] = (
                "typed-KILL-with-recheck pair (critic "
                "ALLOWED_SIGNAL_ANSWER on a located lexical "
                "false-positive contrast phrase; the TESA formula "
                "verifiably consumes only the four stated channels — "
                "instrument_recheck field on the r3 record): included "
                "here WITH disclosure; the auditor decides whether "
                "this pair or the n=29 sensitivity governs (Art. XXV)")
        if pid in r8_ref:
            row["r8_battery_reference"] = r8_ref[pid]
        if pid == EVAL_NEW01_ADJUDICATION["problem_id"]:
            row["adjudication_note"] = EVAL_NEW01_ADJUDICATION["holding"]
        results.append(row)
        print(f"  [{i+1}/{len(pairs)}] {pid[:34]:<36} "
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
            return round(m,3), round(m-1.96*se,3), round(m+1.96*se,3)

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
        both_move = [r for r in valid if "r8_battery_reference" in r]
        return {
            "label": label,
            "n_valid": n,
            "novelty_delta_mean": nd_m,
            "novelty_ci95": [nd_lo, nd_hi],
            "feasibility_abs_gap_mean": fg_m,
            "feasibility_ci95": [fg_lo, fg_hi],
            "per_axis_means_A_minus_B": per_axis_means,
            "AM12_point_estimate": {
                "novelty_clause_pass": nd_m >= 0.5,
                "feasibility_clause_pass": fg_m <= 0.25,
                "both_simultaneous_pass": (nd_m >= 0.5 and fg_m <= 0.25
                                           and n >= 30),
                "form": "mean over judged pairs (the Art. LXXXVI gate "
                        "form; AM12 direction-1 thresholds verbatim)",
                "threshold_provenance": "owner directive 2026-11-14 "
                                        "item 9 (Art. LXXXVI), "
                                        "restated AM12 direction 1; "
                                        "class BUYER_DEFINED",
            },
            "r7_comparable_CI": {
                "novelty_clause_pass": nd_lo >= 0.5,
                "feasibility_clause_pass": fg_hi <= 0.25,
                "both_simultaneous_pass": (nd_lo >= 0.5 and fg_hi <= 0.25
                                           and n >= 30),
                "form": "batteries r7/r8's conservative t-CI form — "
                        "disclosed for cross-battery comparability",
            },
            "prefer_tally": {"a1f_v3": a1w, "baseline": bw,
                             "tie": n - a1w - bw},
            "v2_to_v3_movement": {
                "note": "means over pairs carrying an r8 reference row",
                "novelty_delta_v2_mean": _mean([
                    r["r8_battery_reference"]["n_delta_r8"]
                    for r in both_move]),
                "novelty_delta_v3_mean": _mean([
                    r["novelty_delta"] for r in both_move]),
                "feasibility_abs_gap_v2_mean": _mean([
                    r["r8_battery_reference"]["f_abs_gap_r8"]
                    for r in both_move]),
                "feasibility_abs_gap_v3_mean": _mean([
                    r["feasibility_abs_gap"] for r in both_move]),
            },
        }

    record = {
        "record": "BATTERY_A1F_R9/1.0.0",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "arms": {
            "A": "A1F_V3 SAME-CLASS-NOVELTY GLM generations "
                 "(eval/pairs/r11_a1f_r3, SYS_A1F_V3: the standard "
                 "practice's own outcome class + a genuinely different "
                 "mechanism at the same burden class; both r8-measured "
                 "failure modes named forbidden; 30/30 committed — "
                 "28 CLEAN / 1 FLAG / 1 KILL-with-recheck)",
            "B": "CURATED baselines — assembly IDENTICAL to batteries "
                 "r7/r8 (10 committed dev12 + 20 builder "
                 "STANDARD_REFERENCE): the only changed arm is A "
                 "(V2 -> V3), so the v2-to-v3 movement isolates the "
                 "contract change",
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
        "summary": _summary(results, "all pairs (n=30 pool)"),
        "summary_excluding_new07": _summary(
            [r for r in results if r["problem_id"] != NEW07],
            "auditor-excluded-new07 sensitivity (the typed-KILL-with-"
            "recheck pair removed; which n governs is the auditor's, "
            "Art. XXV)"),
        "gate_note": ("MEASUREMENT for the auditor (Art. XXVI/LXXXVI-2): "
                      "the AM12 direction-3 acceptance (novelty delta "
                      ">= 0.5 AND feasibility |gap| <= 0.25 "
                      "simultaneously, per-axis) evaluated on the "
                      "SYS_A1F_V3 arm; both acceptance forms reported "
                      "and labelled, the all-pairs and "
                      "excluding-new07 sensitivities both carried; the "
                      "authoritative gate re-decision is the auditor's "
                      "per-axis re-judgment on the committed bytes"),
    }
    out = REPO / "eval" / "battery_a1f_r9.json"
    out.write_text(json.dumps(record, indent=1, default=str) + "\n",
                   encoding="utf-8")
    s = record["summary"]
    pe = s["AM12_point_estimate"]
    print(f"\n[r9] valid {s['n_valid']}/{s['n_pairs'] if 'n_pairs' in s else len(results)} | "
          f"novelty Δ {s['novelty_delta_mean']} CI {s['novelty_ci95']} "
          f"| feas |gap| {s['feasibility_abs_gap_mean']} CI "
          f"{s['feasibility_ci95']}")
    print(f"[r9] per-axis means (A-B): {s['per_axis_means_A_minus_B']}")
    print(f"[r9] AM12 point-estimate: {pe['both_simultaneous_pass']} "
          f"(nov {pe['novelty_clause_pass']}, "
          f"feas {pe['feasibility_clause_pass']}) | CI form: "
          f"{s['r7_comparable_CI']['both_simultaneous_pass']}")
    print(f"[r9] v2->v3 movement: {s['v2_to_v3_movement']}")
    s2 = record["summary_excluding_new07"]
    pe2 = s2["AM12_point_estimate"]
    print(f"[r9] excl-new07 sensitivity: n={s2['n_valid']} "
          f"point-estimate both={pe2['both_simultaneous_pass']} "
          f"(nov {pe2['novelty_clause_pass']}, "
          f"feas {pe2['feasibility_clause_pass']})")
    print(f"-> {out}")


if __name__ == "__main__":
    raise SystemExit(main() or 0)

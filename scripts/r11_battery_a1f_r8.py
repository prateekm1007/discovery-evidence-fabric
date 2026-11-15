#!/usr/bin/env python3
"""Battery r8 — the AM11 D1/F30 measurement: the FEASIBILITY-AWARE
A1F_V2 arms (GLM, SYS_A1F_V2: novelty in the observable, feasibility
in the implementation) vs the CURATED baselines at n=30, judged by
the SAME recalibrated judge (v2 axis suffix, k=3 majority — the D2
method), judge != generator (crowllm/qwen vs zai/GLM).

AM9 acceptance: feasibility |gap| <= 0.25 AND novelty delta >= 0.5
on >= 30 pairs.

Arms:
  A = A1F answer (eval/pairs/r11_a1f_r2/, GLM SYS_A1F — the
      feasibility-grounding leg: physics check, implementation bill,
      standard-practice parity, executable test).
  B = CURATED baseline (dev12 committed where non-empty; else the
      builder-authored STANDARD_REFERENCE baselines, pending auditor
      adoption).

Judge: crowllm/qwen-3.8-max:free, k=3 draws per pair (13s pace),
majority prefer + per-axis median. Pacing: 30 pairs x 3 draws x 13s
~ 20 min. This is a MEASUREMENT for the auditor (Art. XXVI).
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

JUDGE = ("crowllm", "qwen-3.8-max:free")
PACE_S = 13.0
K = 3
AXIS_SUFFIX = (REPO / "scripts" / "_f28_axis_suffix_v2.txt").read_text()

A1F_DIR = REPO / "eval" / "pairs" / "r11_a1f_r2"


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


def main():
    plist = json.loads((REPO / "eval" / "problems.json").read_text())
    plist = plist if isinstance(plist, list) else plist.get("problems", [])
    probs = {str(p.get("problem_id") or p.get("id")): p for p in plist}
    for p in json.loads((REPO / "eval" / "problems_dev12.json")
                        .read_text())["problems"]:
        probs.setdefault(p["problem_id"], p)

    pairs = []
    for pid in sorted(probs):
        a1f = A1F_DIR / f"{pid}.json"
        if not a1f.exists():
            continue
        a1 = str(json.loads(a1f.read_text()).get("a1_answer") or "")
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
                          "b_src": b_src})
    print(f"[r8] pool: {len(pairs)} pairs")

    results = []
    t0 = time.time()
    for i, pr in enumerate(pairs):
        pid = pr["problem_id"]
        prompt = _rubric_prompt(pr["prob"], pr["a1"], pr["base"],
                                None) + AXIS_SUFFIX
        draws = []
        for k in range(K):
            econ.reset_governor(f"r8:{pid}:{k}")
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
               "a1_arm": "A1F_V2_feasibility_aware_GLM",
               "baseline_source": pr["b_src"],
               "judge": list(JUDGE), "draws": draws,
               "majority_prefer": maj, "median_axes": med}
        if med:
            row["novelty_delta"] = med["N_A"] - med["N_B"]
            row["feasibility_abs_gap"] = abs(med["F_A"] - med["F_B"])
            row["feasibility_signed_gap"] = med["F_A"] - med["F_B"]
        results.append(row)
        print(f"  [{i+1}/{len(pairs)}] {pid[:34]:<36} "
              f"nd={row.get('novelty_delta')} "
              f"fgap={row.get('feasibility_abs_gap')} "
              f"sg={row.get('feasibility_signed_gap')} "
              f"pref={maj} {pref_counts}", flush=True)
        (REPO / "eval" / "battery_a1f_r8.partial.json").write_text(
            json.dumps(results, indent=1, default=str) + "\n",
            encoding="utf-8")

    valid = [r for r in results if r.get("median_axes")]
    n = len(valid)

    def _tci(vals):
        m = sum(vals)/len(vals)
        sd = math.sqrt(sum((x-m)**2 for x in vals)/(len(vals)-1))
        se = sd/math.sqrt(len(vals))
        return round(m,3), round(m-1.96*se,3), round(m+1.96*se,3)

    nd = [r["novelty_delta"] for r in valid]
    fg = [r["feasibility_abs_gap"] for r in valid]
    nd_m, nd_lo, nd_hi = _tci(nd)
    fg_m, fg_lo, fg_hi = _tci(fg)
    a1w = sum(1 for r in valid if r["majority_prefer"] == "A")
    bw = sum(1 for r in valid if r["majority_prefer"] == "B")
    record = {
        "record": "BATTERY_A1F_R8/1.0.0",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "arms": {
            "A": "A1F feasibility-grounded GLM generations "
                 "(eval/pairs/r11_a1f_r2, SYS_A1F: physics check + "
                 "implementation bill + standard-practice parity + "
                 "executable test)",
            "B": "CURATED baselines (12 committed dev12 + 20 "
                 "builder STANDARD_REFERENCE, pending auditor "
                 "adoption)"},
        "judge": {
            "route": list(JUDGE),
            "independence": "crowllm/Qwen vs zai/GLM generator — "
                            "provider AND family independent",
            "calibration": "the D2 recalibrated v2 axis suffix, k=3 "
                           "majority vote + per-axis median "
                           "(eval/judge_recalibration_f28_k3.json)"},
        "results": results,
        "summary": {
            "n_pairs": len(pairs), "n_valid": n,
            "novelty_delta_mean": nd_m, "novelty_ci95": [nd_lo, nd_hi],
            "novelty_clause_pass": nd_lo >= 0.5,
            "feasibility_abs_gap_mean": fg_m,
            "feasibility_ci95": [fg_lo, fg_hi],
            "feasibility_clause_pass": fg_hi <= 0.25,
            "AM9_acceptance_met": (nd_lo is not None and nd_lo >= 0.5
                                   and fg_hi is not None
                                   and fg_hi <= 0.25 and n >= 30),
            "prefer_tally": {"a1f": a1w, "baseline": bw,
                             "tie": n - a1w - bw},
            "wall_s": round(time.time() - t0, 1),
        },
        "gate_note": ("MEASUREMENT for the auditor (Art. XXVI): the "
                      "AM9 direction-4 acceptance (feasibility |gap| "
                      "<= 0.25 AND novelty delta >= 0.5 at n >= 30) "
                      "evaluated on the feasibility-grounded arm; the "
                      "gate decision stays the auditor's."),
    }
    out = REPO / "eval" / "battery_a1f_r8.json"
    out.write_text(json.dumps(record, indent=1, default=str) + "\n",
                   encoding="utf-8")
    s = record["summary"]
    print(f"\n[r7] valid {s['n_valid']}/{s['n_pairs']} | "
          f"novelty Δ {s['novelty_delta_mean']} CI {s['novelty_ci95']} "
          f"(pass {s['novelty_clause_pass']}) | "
          f"feas |gap| {s['feasibility_abs_gap_mean']} CI "
          f"{s['feasibility_ci95']} (pass {s['feasibility_clause_pass']}) "
          f"| AM9 acceptance: {s['AM9_acceptance_met']}")
    print(f"-> {out}")


if __name__ == "__main__":
    main()

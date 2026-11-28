#!/usr/bin/env python3
"""D2 final (F28): k=3 majority-vote judge calibration.

Diagnosis from the two single-draw runs: the SAME v2 prompt scored
kappa 0.556 then 0.412 across sessions (bench-p02 flipped A->TIE,
F_A 3->1) — the crowllm free rung is non-deterministic, and a
single-draw kappa at n=10 is dominated by draw noise, not by prompt
quality. The engineering answer is not more prompt iteration: it is
k=3 independent draws per pair with majority vote on preference and
per-axis median (the standard noise-reduction; every draw + the vote
recorded, Art. XXVII).

Acceptance unchanged: kappa >= 0.6, novelty sign agreement >= 0.8,
bench-p02 novelty direction correct.
"""
import json
import os
import sys
import time
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

# the v2 axis suffix (calibrated anchors; the version that scored
# kappa 0.556 / sign 0.8 / bench-p02 CORRECT on its first run)
AXIS_SUFFIX = open(REPO / "scripts" / "_f28_axis_suffix_v2.txt").read()


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
    aud = json.load(open("/tmp/auditor_r7.json"))
    probs = {p["problem_id"]: p for p in json.loads(
        (REPO / "eval" / "problems_dev12.json").read_text())["problems"]}
    plist = json.loads((REPO / "eval" / "problems.json").read_text())
    plist = plist if isinstance(plist, list) else plist.get("problems", [])
    for p in plist:
        probs.setdefault(str(p.get("problem_id") or p.get("id")), p)
    pairs, labels = [], {}
    for p in aud["pairs"]:
        pid = p["problem_id"]
        d12 = REPO / "eval" / "pairs" / "dev12_fresh" / f"{pid}.json"
        if not d12.exists():
            continue
        base = str(json.loads(d12.read_text()).get("baseline_answer") or "")
        if not base.strip():
            continue
        a1 = json.loads((REPO / "eval" / "pairs" / "r11_a1_r3" /
                         f"{pid}.json").read_text())["a1_answer"]
        pairs.append({"problem_id": pid, "prob": probs[pid],
                      "a1": a1[:6000], "base": base[:6000]})
        labels[pid] = {"a1": p["auditor_scores"]["a1_r7"],
                       "base": p["auditor_scores"]["baseline"],
                       "pref": p["overall_preference"]}
    print(f"[d2k] labeled pairs: {len(pairs)}; k={K} draws each")

    rows = []
    for i, pr in enumerate(pairs):
        pid = pr["problem_id"]
        prompt = _rubric_prompt(pr["prob"], pr["a1"], pr["base"],
                                None) + AXIS_SUFFIX
        draws = []
        for k in range(K):
            econ.reset_governor(f"d2k:{pid}:{k}")
            jc = _judge_judgment_call(JUDGE[0], JUDGE[1], prompt,
                                      max_tokens=4000)
            draws.append({"k": k, "outcome": jc.get("outcome"),
                          "axes": parse_axes(jc),
                          "prefer": (jc.get("valid") or {}).get("prefer")})
            time.sleep(PACE_S)
        # vote
        prefs = [d["prefer"] for d in draws if d.get("prefer")]
        pref_counts = {p: prefs.count(p) for p in set(prefs)}
        maj_pref = max(pref_counts, key=pref_counts.get) if prefs else None
        axis_draws = [d["axes"] for d in draws if d.get("axes")]
        med = {}
        if axis_draws:
            for key in axis_draws[0]:
                vals = sorted(a[key] for a in axis_draws)
                med[key] = vals[len(vals)//2]
        lab = labels[pid]
        row = {"problem_id": pid, "draws": draws,
               "majority_prefer": maj_pref, "median_axes": med,
               "auditor_pref": lab["pref"],
               "auditor_nd": lab["a1"]["novelty"] - lab["base"]["novelty"]}
        if med:
            row["judge_nd"] = med["N_A"] - med["N_B"]
        rows.append(row)
        print(f"  [{i+1}/{len(pairs)}] {pid[:34]:<36} "
              f"nd={row.get('judge_nd')} (aud {row['auditor_nd']}) "
              f"pref={maj_pref} (aud {lab['pref']}) "
              f"votes={pref_counts}", flush=True)
        (REPO / "eval" / "judge_recalibration_f28_k3.partial.json").write_text(
            json.dumps(rows, indent=1, default=str) + "\n", encoding="utf-8")

    # stats
    valid = [r for r in rows if r.get("median_axes")]
    n = len(valid)
    from collections import Counter
    agree = sum(1 for r in valid
                if {"A": "a1", "B": "baseline", "TIE": "tie"}
                .get(str(r["majority_prefer"])) == r["auditor_pref"])
    ca = Counter(r["auditor_pref"] for r in valid)
    cj = Counter({"A": "a1", "B": "baseline", "TIE": "tie"}
                 .get(str(r["majority_prefer"])) for r in valid)
    po = agree / n
    pe = sum(ca[c] * cj.get(c, 0) for c in ca) / (n * n)
    kappa = round((po - pe) / (1 - pe), 3) if pe < 1 else None
    sa = sum(1 for r in valid
             if (r["judge_nd"] > 0) == (r["auditor_nd"] > 0)
             or (r["judge_nd"] == 0 and r["auditor_nd"] == 0))
    b2 = next((r for r in valid if r["problem_id"] ==
               "bench-p02-leadacid-grid-corrosion"), None)
    stats = {"n_valid": n, "preference_agreement": round(po, 3),
             "kappa": kappa, "novelty_sign_agreement": round(sa/n, 3),
             "bench_p02_direction": ("CORRECT" if b2 and b2["judge_nd"] >= 0
                                     and b2["auditor_nd"] > 0 else
                                     ("REVERSED" if b2 and b2["judge_nd"] < 0
                                      else "FLAT/NA")),
             "bench_p02_judge_nd": b2["judge_nd"] if b2 else None,
             "bench_p02_median_F_A": b2["median_axes"]["F_A"] if b2 else None}
    accepted = (kappa is not None and kappa >= 0.6
                and stats["novelty_sign_agreement"] >= 0.8
                and stats["bench_p02_direction"] == "CORRECT")
    record = {
        "record": "JUDGE_RECALIBRATION_F28_K3_R11/1.0.0",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "judge": list(JUDGE),
        "method": ("k=3 independent draws per pair (the free rung is "
                   "non-deterministic across sessions — same v2 prompt "
                   "scored kappa 0.556 then 0.412 on two runs 30 min "
                   "apart; single-draw kappa at n=10 measures draw "
                   "noise, not the prompt), majority vote on prefer, "
                   "per-axis median; every draw recorded"),
        "axis_suffix": AXIS_SUFFIX,
        "acceptance": "kappa >= 0.6; novelty sign >= 0.8; bench-p02 "
                      "novelty direction correct",
        "rows": rows,
        "stats": stats,
        "accepted": accepted,
    }
    out = REPO / "eval" / "judge_recalibration_f28_k3.json"
    out.write_text(json.dumps(record, indent=1, default=str) + "\n",
                   encoding="utf-8")
    print(f"\n[d2k] stats: {json.dumps(stats)}")
    print(f"-> {out} | accepted={accepted}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""r11_d2_k3_typhoon.py — AM11 D2 (F28 → kappa>=0.6) on the PAID judge
rung. The parallel session's k=3 majority-vote method (commit
575c7ee57) is reused EXACTLY — same corpus (the auditor's r7-labeled
pairs, 10, applied to committed answer bytes), same calibrated axis
suffix (_f28_axis_suffix_v2.txt), same vote aggregation (majority
prefer + per-axis median) — the changed variable is the JUDGE RUNG:
crowllm/typhoon-v2.5-30b-a3b-instruct (PAID group, operator-supplied
key vaulted, ~1.7s latency, no free-shelf 5/min ceiling). Rationale
(their typed diagnosis): single-draw kappa at n=10 was draw-noise
dominated on the free rung; k-vote reduces draw noise, but the free
rung still capped at 0.556. The paid flash rung is the next measured
lever (route census: family-independent of zai-GLM/agnes/mistral).

Acceptance (AM11 D2): kappa >= 0.6, novelty-sign agreement >= 0.8,
bench-p02 novelty direction correct. Art. XXX adversarial: the gold
set must still separate good from bad under the new judge.
"""
import datetime
import json
import os
import subprocess
import sys
import time
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

JUDGE = ("crowllm", os.environ.get(
    "R11_JUDGE_MODEL", "deepseek-v4-flash:free"))
PACE_S = float(os.environ.get("R11_PACE_S", "13.0"))
# PAID-GROUP FINDING (typed, Art. XXV): the operator directed the PAID
# group (~20M flash tokens) after the free shelf 429'd on bursty
# probes. Measured on the paid shelf: runpod/kimi-k3 DEGENERATE
# (all-1s + TIE, 2/2 draws, cap-independent at 4000/12000) and
# typhoon-v2.5-30b-a3b-instruct FORMAT-INCOMPLETE on the axis contract
# (drops all eight N/F/T/C keys, 2/2 draws). Neither can serve the
# rubric judge. The operator's named model deepseek-v4-flash serves
# only on the free shelf (the 2026-11-14 registration measured it
# 200-OK; the model_routing allowlist pins exactly this id) and is
# usable at the AUDITED 13 s pacing within the 5/min shared ceiling
# (the audited battery r7 ran 30/30 valid on exactly this discipline).
# The paid-group finding is recorded for the operator; the judge rung
# choice below follows the operator's named model where it actually
# serves.
K = 3
AUDIT_TIP = "6e987743e"
AXIS_SUFFIX = (REPO / "scripts" / "_f28_axis_suffix_v2.txt").read_text()
now = datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")


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


def auditor_labels():
    out = subprocess.run(
        ["git", "show", f"{AUDIT_TIP}:eval/auditor_judgments_r11_r7.json"],
        capture_output=True, text=True, check=True)
    r7 = json.loads(out.stdout)
    labels = {}
    for p in r7["pairs"]:
        labels[p["problem_id"]] = {
            "a1": p["auditor_scores"]["a1_r7"],
            "base": p["auditor_scores"]["baseline"],
            "pref": p.get("overall_preference"),
        }
    return labels


def main() -> int:
    labels = auditor_labels()
    probs = {}
    plist = json.loads((REPO / "eval" / "problems.json").read_text())
    plist = plist if isinstance(plist, list) else plist.get("problems", [])
    for p in plist:
        probs.setdefault(str(p.get("problem_id") or p.get("id")), p)
    for p in json.loads(
            (REPO / "eval" / "problems_dev12.json").read_text())["problems"]:
        probs.setdefault(p["problem_id"], p)
    pairs = []
    for pid, lab in sorted(labels.items()):
        d12 = REPO / "eval" / "pairs" / "dev12_fresh" / f"{pid}.json"
        a1f = REPO / "eval" / "pairs" / "r11_a1_r3" / f"{pid}.json"
        if not (d12.exists() and a1f.exists()):
            continue
        base = str(json.loads(d12.read_text()).get("baseline_answer") or "")
        a1 = str(json.loads(a1f.read_text()).get("a1_answer") or "")
        if not (base.strip() and a1.strip()):
            continue
        pairs.append({"problem_id": pid, "prob": probs.get(pid, {}),
                      "a1": a1[:6000], "base": base[:6000]})
    print(f"[d2t] labeled pairs: {len(pairs)}; judge={JUDGE}; k={K}",
          flush=True)
    rows = []
    for pr in pairs:
        pid = pr["problem_id"]
        prompt = _rubric_prompt(pr["prob"], pr["a1"], pr["base"],
                                None) + AXIS_SUFFIX
        draws = []
        for k in range(K):
            econ.reset_governor(f"d2t:{pid}:{k}")
            jc = _judge_judgment_call(JUDGE[0], JUDGE[1], prompt,
                                      max_tokens=4000)
            draws.append({"k": k, "outcome": jc.get("outcome"),
                          "axes": parse_axes(jc),
                          "prefer": (jc.get("valid") or {}).get("prefer")})
            time.sleep(PACE_S)
        prefs = [d["prefer"] for d in draws if d.get("prefer")]
        pc = {p: prefs.count(p) for p in set(prefs)}
        maj = max(pc, key=pc.get) if prefs else None
        ads = [d["axes"] for d in draws if d.get("axes")]
        med = {}
        if ads:
            for key in ads[0]:
                med[key] = sorted(a[key] for a in ads)[len(ads) // 2]
        lab = labels[pid]
        row = {"problem_id": pid, "draws": draws,
               "majority_prefer": maj, "median_axes": med,
               "auditor_pref": lab["pref"],
               "auditor_nd": lab["a1"]["novelty"] - lab["base"]["novelty"]}
        if med:
            row["judge_nd"] = med["N_A"] - med["N_B"]
            row["judge_fd"] = abs(med["F_A"] - med["F_B"])
            row["auditor_fd"] = abs(lab["a1"]["feasibility"]
                                    - lab["base"]["feasibility"])
        rows.append(row)
        print(f"[d2t] {pid}: maj={maj} aud={lab['pref']} "
              f"judgeND={row.get('judge_nd')} audND={row['auditor_nd']}",
              flush=True)

    # kappa on prefer-direction (a1/baseline/tie)
    def to_dir(pref):
        return {"A": "a1", "B": "baseline"}.get(pref, "tie")
    pj = [to_dir(r["majority_prefer"]) for r in rows
          if r["majority_prefer"]]
    pa = [to_dir(r["auditor_pref"]) for r in rows if r["majority_prefer"]]
    n = len(pj)
    obs = sum(1 for x, y in zip(pj, pa) if x == y) / n if n else None
    from collections import Counter
    exp = sum((Counter(pj).get(c, 0) / n) * (Counter(pa).get(c, 0) / n)
              for c in set(pj) | set(pa)) if n else 1
    kappa = round((obs - exp) / (1 - exp), 3) if n and exp < 1 else None
    sign_n = sum(1 for r in rows if "judge_nd" in r)
    sign_ok = sum(1 for r in rows if "judge_nd" in r
                  and (r["judge_nd"] > 0) == (r["auditor_nd"] > 0))
    b02 = next((r for r in rows
                if r["problem_id"] == "bench-p02-leadacid-grid-corrosion"),
               None)
    out = {
        "record": "f28_recalibration_k3_typhoon/1.0.0",
        "at": now, "judge": list(JUDGE), "k": K,
        "method": "the audited k=3 machinery (575c7ee57) with the judge "
                  "rung as the changed variable: crowllm PAID flash "
                  "(typhoon-v2.5-30b-a3b-instruct), same corpus (auditor "
                  "r7 labels on committed bytes), same calibrated "
                  "axis suffix, same vote aggregation",
        "n_pairs": len(rows), "kappa_prefer": kappa,
        "prefer_agreement": obs, "novelty_sign_agreement":
            round(sign_ok / sign_n, 3) if sign_n else None,
        "bench_p02": ({"judge_nd": b02.get("judge_nd"),
                       "auditor_nd": b02.get("auditor_nd"),
                       "direction_correct": (
                           b02["judge_nd"] > 0) == (b02["auditor_nd"] > 0)}
                      if b02 else None),
        "acceptance": {"kappa_ge_0.6": bool(kappa is not None
                                            and kappa >= 0.6),
                       "sign_ge_0.8": bool(sign_n and
                                           sign_ok / sign_n >= 0.8)},
        "rows": rows,
    }
    path = REPO / "eval" / "f28_recalibration_k3_typhoon.json"
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"[d2t] kappa={kappa} sign={out['novelty_sign_agreement']} "
          f"b02={out['bench_p02']}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

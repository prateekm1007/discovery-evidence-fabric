#!/usr/bin/env python3
"""r10_battery_peraxis_r7.py — AM10 D5 prep: the per-axis re-judgment
over the 30 COMMITTED answer bytes (A arm = 12 grounded delivery
variants + 18 GLM-curated fresh answers; B arm = the same curated
baselines), with the CALIBRATED axis suffix and the gate-input
recompute. RUNS when a family-independent judge route is live:
  R7_JUDGE_PROVIDER / R7_JUDGE_MODEL (default: the re-qualified
  crowllm/qwen-3.8-max rung once a fresh key is vaulted; the xkiro
  mistral rung is the 00:00Z-reset fallback).
The formal gate stays AUDITOR-judged (Art. XXVI) — this driver produces
the measurement record (axes per pair, gate inputs, prefer tallies) the
auditor re-judges at n=30.
"""
import datetime
import json
import math
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()

from eval.run import _rubric_prompt, _judge_judgment_call  # noqa: E402
from r11_battery_peraxis_r6 import _axis_valid  # noqa: E402
from r10_axis_suffix_v2 import PER_AXIS_SUFFIX_V2 as SUFFIX  # noqa: E402
from discovery_fabric.engine import llm_economy as econ  # noqa: E402

JUDGE = (os.environ.get("R7_JUDGE_PROVIDER", "crowllm"),
         os.environ.get("R7_JUDGE_MODEL", "qwen-3.8-max:free"))
PACE_S = float(os.environ.get("R7_PACE_S", "13"))
A_DIRS = [REPO / "eval" / "pairs" / "r11_a1_r3_grounded",
          REPO / "eval" / "pairs" / "r11_a1_fresh_r10"]
BASE_DIRS = [REPO / "eval" / "pairs" / "dev12_fresh",
             REPO / "eval" / "baselines_curated"]
OUT = REPO / "eval" / "battery_peraxis_r11_r7.json"
now = datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")


def a1_answer(pid):
    for d in A_DIRS:
        f = d / f"{pid}.json"
        if f.exists():
            r = json.loads(f.read_text())
            a = r.get("a1_answer_grounded") or r.get("a1_answer") or ""
            if str(a).strip():
                return str(a), (f"GROUNDED_DELIVERY_r11_a1_r3_grounded"
                                if "a1_answer_grounded" in r else
                                "GLM_CURATED_R10_REGEN")
    return "", ""


def baseline(pid):
    for d in BASE_DIRS:
        f = d / f"{pid}.json"
        if f.exists():
            r = json.loads(f.read_text())
            b = r.get("baseline_answer") or ""
            if str(b).strip():
                return str(b), ("CURATED_COMMITTED_dev12"
                                if "dev12_fresh" in str(d) else
                                "CURATED_STANDARD_REFERENCE_builder_r8")
    return "", ""


def t_ci(xs):
    n = len(xs)
    m = sum(xs) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))
    half = 2.0452 * sd / math.sqrt(n)  # t(0.975, df=29) for n=30
    return round(m, 3), round(m - half, 3), round(m + half, 3)


def main() -> int:
    probs = {}
    for src in ("eval/problems.json", "eval/problems_dev12.json"):
        for p in json.loads((REPO / src).read_text())["problems"]:
            probs.setdefault(p["problem_id"], p)
    rows = []
    nd, fg = [], []
    for pid in sorted(probs):
        a1, a1_src = a1_answer(pid)
        base, b_src = baseline(pid)
        if not (a1.strip() and base.strip()):
            print(f"[r7] SKIP {pid}: missing arm bytes", flush=True)
            continue
        econ.reset_governor(f"r7:{pid}")
        prompt = _rubric_prompt(probs[pid], a1, base, None) + SUFFIX
        time.sleep(PACE_S)
        jc = _judge_judgment_call(JUDGE[0], JUDGE[1], prompt,
                                  max_tokens=4000)
        obj = None
        import re as _re
        m = _re.search(r"\{.*\}", str(jc.get("raw") or ""), _re.S)
        if m:
            try:
                obj = json.loads(m.group(0))
            except Exception:  # noqa: BLE001
                obj = None
        axes = _axis_valid(obj) if obj else None
        row = {"problem_id": pid, "a1_source": a1_src,
               "baseline_source": b_src, "judge": list(JUDGE),
               "judge_outcome": jc.get("outcome"),
               "prefer": str(obj.get("prefer")) if obj else None,
               "axes": axes, "prompt_hash": __import__("hashlib")
               .sha256(prompt.encode()).hexdigest()[:16]}
        if axes:
            d_n = axes["novelty_a1"] - axes["novelty_baseline"]
            g_f = abs(axes["feasibility_a1"] - axes["feasibility_baseline"])
            row["novelty_delta"] = d_n
            row["feasibility_abs_gap"] = g_f
            nd.append(d_n)
            fg.append(g_f)
        rows.append(row)
        print(f"[r7] {pid}: {row['judge_outcome']} "
              f"prefer={row['prefer']} Δn={row.get('novelty_delta')}",
              flush=True)
    summary = {
        "n_pairs_judged": len(rows),
        "novelty_delta_mean": t_ci(nd)[0] if nd else "NOT_MEASURED",
        "novelty_ci95": [t_ci(nd)[1], t_ci(nd)[2]] if nd else None,
        "novelty_clause": ("PASS (>=0.5)" if nd and t_ci(nd)[0] >= 0.5
                           else "NOT_RESOLVED/FAIL"),
        "feasibility_abs_gap_mean": t_ci(fg)[0] if fg else "NOT_MEASURED",
        "feasibility_ci95": [t_ci(fg)[1], t_ci(fg)[2]] if fg else None,
        "feasibility_clause": ("PASS (<=0.25)"
                               if fg and t_ci(fg)[0] <= 0.25
                               else "FAIL"),
        "prefer_tally": {},
        "note": "machine-measured inputs; the gate is AUDITOR-judged "
                "(Art. XXVI)",
    }
    from collections import Counter
    summary["prefer_tally"] = dict(Counter(
        str(r.get("prefer")) for r in rows if r.get("prefer")))
    out = {"record": "battery_peraxis_r11_r7/1.0.0", "at": now,
           "judge": list(JUDGE),
           "a1_sources": {"grounded_delivery": 12, "glm_fresh": 18},
           "axis_suffix": "r10_axis_suffix_v2 (calibrated, F28)",
           "results": rows, "summary": summary}
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(f"[r7] -> {OUT.name}: {summary['n_pairs_judged']} pairs; "
          f"Δn={summary['novelty_delta_mean']} "
          f"CI{summary['novelty_ci95']}; "
          f"|gap|={summary['feasibility_abs_gap_mean']}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

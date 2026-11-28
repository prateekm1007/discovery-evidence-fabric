#!/usr/bin/env python3
"""r10_judge_recalibrate.py — AM10 D3 (F28): judge recalibration on the
AUDITOR's per-axis labels.

Corpus: the r5 auditor per-axis scores (10 gate pairs, both arms, all 4
axes — the audit-branch bytes) applied to the COMMITTED answer bytes
(a1 = eval/pairs/r11_a1_r3/<pid>.json promoted delivery; baseline =
eval/pairs/dev12_fresh/ or eval/baselines_curated/ curated records).
Blind protocol unchanged: _rubric_prompt randomizes A/B by
sha256(problem_id::pair) parity; the judge never sees arm names.

Runs:
  stage 2 (PROMPT_VARIANT=current): reproduce the measured defect on
    the CURRENT per-axis suffix (bench-p02 novelty reversal, kappa 0.40,
    dev12-subset divergence) — the defect must reproduce before it is
    repaired (Art. XXX: the adversarial test must first fail).
  stage 3 (PROMPT_VARIANT=calibrated): the anchored suffix
    (scripts/r10_axis_suffix_v2.py) re-measures the SAME corpus.
    Acceptance: kappa >= 0.6 on prefer-direction, novelty-axis sign
    agreement >= 0.8, bench-p02 direction corrected, and the gold-set
    good/bad separation must survive (Art. XXX adversarial check).

Outputs eval/judge_recalibration_r10_<variant>.json.
"""
import datetime
import hashlib
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

from eval.run import (  # noqa: E402
    _rubric_prompt, _judge_judgment_call, _parse_rubric)
from discovery_fabric.engine import llm_economy as econ  # noqa: E402

VARIANT = os.environ.get("PROMPT_VARIANT", "current")
AUDIT_TIP = "42179ee15"
R5_PATH = "eval/auditor_judgments_r11_r5.json"
JUDGE = ("crowllm", "qwen-3.8-max:free")
PACE_S = 13.0
now = datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")

if VARIANT == "calibrated":
    from r10_axis_suffix_v2 import PER_AXIS_SUFFIX_V2 as SUFFIX
    VARIANT_NOTE = ("anchored suffix (r10_axis_suffix_v2): novelty "
                    "anchors — field-standard practice scores 1-2 BY "
                    "DEFINITION regardless of execution polish; "
                    "mechanism difference drives novelty. feasibility "
                    "anchors — workability within stated constraints, "
                    "not elegance: sound mechanism + concrete "
                    "parameters + realistic data/test path is 3+; 1-2 "
                    "reserved for physically impossible or unit-"
                    "incoherent designs. gold-set adversarial check "
                    "must still separate good from bad.")
else:
    from r11_battery_peraxis_r6 import PER_AXIS_SUFFIX as SUFFIX
    VARIANT_NOTE = "the CURRENT per-axis suffix (r6 instrument bytes)"


def auditor_labels():
    out = subprocess.run(["git", "show", f"{AUDIT_TIP}:{R5_PATH}"],
                         capture_output=True, text=True, check=True)
    r5 = json.loads(out.stdout)
    labels = {}
    for p in r5["pairs"]:
        labels[p["problem_id"]] = {
            "a1": p["auditor_scores"]["a1_r5"],
            "baseline": p["auditor_scores"]["baseline"],
            "novelty_delta": p["novelty_delta"],
            "feasibility_abs_gap": p["feasibility_abs_gap"],
            "overall_preference": p.get("overall_preference"),
        }
    return labels


def answer_bytes(pid):
    a1 = json.loads((REPO / "eval" / "pairs" / "r11_a1_r3"
                     / f"{pid}.json").read_text()).get("a1_answer")
    base = ""
    for d in ("eval/pairs/dev12_fresh", "eval/baselines_curated"):
        f = REPO / d / f"{pid}.json"
        if f.exists():
            base = (json.loads(f.read_text()).get("baseline_answer")
                    or json.loads(f.read_text()).get("standard_answer")
                    or "")
            if str(base).strip():
                break
    return str(a1 or "")[:6000], str(base or "")[:6000]


def problems():
    probs = {}
    for src in ("eval/problems.json", "eval/problems_dev12.json"):
        for p in json.loads((REPO / src).read_text())["problems"]:
            probs.setdefault(p["problem_id"], p)
    return probs


def axis_diff(judge_axes, auditor):
    """judge axes are keyed novelty_a1/...; auditor a1/baseline dicts."""
    rows = {}
    for arm in ("a1", "baseline"):
        for ax in ("novelty", "feasibility", "testability",
                   "constraint_compliance"):
            jv = judge_axes.get(f"{ax}_{arm}")
            av = auditor[arm].get(ax if ax != "constraint_compliance"
                                  else "constraint_compliance")
            if jv is not None and av is not None:
                rows[f"{ax}_{arm}"] = {"judge": jv, "auditor": av,
                                       "diff": jv - av}
    return rows


def main() -> int:
    labels = auditor_labels()
    probs = problems()
    rows = []
    sign_ok = 0
    sign_n = 0
    prefer_j, prefer_a = [], []
    bench02 = None
    for pid, lab in sorted(labels.items()):
        a1, base = answer_bytes(pid)
        if not a1.strip() or not base.strip():
            print(f"[cal] SKIP {pid}: missing arm bytes")
            continue
        prob = probs.get(pid, {})
        econ.reset_governor(f"cal:{pid}")
        prompt = _rubric_prompt(prob, a1, base, None) + SUFFIX
        time.sleep(PACE_S)
        jc = _judge_judgment_call(JUDGE[0], JUDGE[1], prompt,
                                  max_tokens=4000)
        obj = None
        # robust: re-extract the full JSON object from raw
        import re as _re
        m = _re.search(r"\{.*\}", str(jc.get("raw") or ""), _re.S)
        if m:
            try:
                obj = json.loads(m.group(0))
            except Exception:  # noqa: BLE001
                obj = None
        axes = None
        prefer_judge = None
        if obj:
            from r11_battery_peraxis_r6 import _axis_valid
            axes = _axis_valid(obj)
            prefer_judge = str(obj.get("prefer") or "")
        row = {
            "problem_id": pid,
            "judge_outcome": jc.get("outcome"),
            "prefer_judge": prefer_judge,
            "prefer_auditor": lab["overall_preference"],
            "auditor_novelty_delta": lab["novelty_delta"],
            "auditor_feasibility_abs_gap": lab["feasibility_abs_gap"],
        }
        if axes:
            row["axes"] = axes
            row["axis_diff"] = axis_diff(axes, lab)
            jd = axes["novelty_a1"] - axes["novelty_baseline"]
            row["judge_novelty_delta"] = jd
            sign_n += 1
            if (jd > 0) == (lab["novelty_delta"] > 0) or jd == 0:
                sign_ok += 1
            prefer_j.append(prefer_judge)
            prefer_a.append({"A": "a1", "B": "baseline"}.get(
                prefer_judge, "tie")
                if prefer_judge in ("A", "B") else "tie")
            if pid == "bench-p02-leadacid-grid-corrosion":
                bench02 = {"judge_novelty_delta": jd,
                           "auditor_novelty_delta": lab["novelty_delta"],
                           "reversed": (jd < 0) != (lab["novelty_delta"] < 0)
                           and jd != 0}
        rows.append(row)
        print(f"[cal] {pid}: {jc.get('outcome')} prefer={prefer_judge} "
              f"judgeΔn={row.get('judge_novelty_delta')} "
              f"audΔn={lab['novelty_delta']}")

    # kappa on the prefer direction (a1/baseline/tie), Cohen's kappa
    def kappa(a, b):
        n = len(a)
        if not n:
            return None
        obs = sum(1 for x, y in zip(a, b) if x == y) / n
        from collections import Counter
        pa = Counter(a)
        pb = Counter(b)
        exp = sum((pa.get(k, 0) / n) * (pb.get(k, 0) / n)
                  for k in set(pa) | set(pb))
        return round((obs - exp) / (1 - exp), 3) if exp < 1 else None

    k = kappa(prefer_j, prefer_a)
    sign_rate = round(sign_ok / sign_n, 3) if sign_n else None
    out = {
        "record": f"judge_recalibration_r10_{VARIANT}/1.0.0",
        "at": now, "variant": VARIANT, "variant_note": VARIANT_NOTE,
        "judge": list(JUDGE),
        "corpus": "auditor r5 per-axis labels (audit tip "
                  f"{AUDIT_TIP}) applied to committed answer bytes; "
                  "blind A/B parity unchanged",
        "n_pairs": len(rows),
        "kappa_prefer": k,
        "novelty_sign_agreement": sign_rate,
        "bench_p02": bench02,
        "rows": rows,
    }
    path = REPO / "eval" / f"judge_recalibration_r10_{VARIANT}.json"
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"[cal] kappa={k} novelty_sign={sign_rate} bench02={bench02}")
    print(f"[cal] -> {path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

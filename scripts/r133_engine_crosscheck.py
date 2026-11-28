#!/usr/bin/env python3
"""r133_engine_crosscheck — run the ENGINE tally (panel_agreement)
over the same raw records and diff against the independent recompute
(the prereg's built-in two-code-path check). Appends the result to
eval/r133_panel_calibration.json.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from discovery_fabric.engine.panel_agreement import (
    rcal_qualification, swap_robust_panel)

REPO = Path(__file__).resolve().parent.parent
RAW = REPO / "eval" / "r133_panel"
TAGS = {"qwen235b": "qwen235b", "dsv32": "dsv32",
        "llama4mav": "llama4mav", "llama33": "llama33"}

# load raw records into the engine module's expected shape
judge_rows = {t: [] for t in TAGS}
import subprocess
r5 = json.loads(subprocess.run(
    ["git", "show", "009ce91a8:eval/auditor_judgments_r11_r5.json"],
    capture_output=True, text=True, check=True).stdout)
labels = {p["problem_id"]: p["overall_preference"]
          for p in r5["pairs"]
          if p.get("overall_preference") in ("a1", "baseline")}
gold = json.loads(subprocess.run(
    ["git", "show",
     "009ce91a8:audit/gold_set/AUDITOR_GOLD_SET_v1.json"],
    capture_output=True, text=True, check=True).stdout)
gold_nov = {s["id"]: {"pid": Path(s["path"]).stem,
                       "arm": s.get("arm", "a1"),
                       "label": s["label"]}
            for s in gold["specimens"]}

for f in sorted(RAW.glob("*.json")):
    parts = f.stem.split("__")
    if len(parts) != 3 or parts[0] not in TAGS:
        continue
    r = json.loads(f.read_text())
    r["pid"] = parts[1]
    judge_rows[parts[0]].append(r)

eng = rcal_qualification(judge_rows, labels)
qualified = [t for t, j in eng.items() if j["qualified"]]
panel = swap_robust_panel(judge_rows, qualified, labels,
                          gold_novelty=gold_nov)

# diff vs the independent recompute
ind = json.loads((REPO / "eval" / "r133_panel_calibration.json")
                 .read_text())
diffs = []
for t, j in ind["judges"].items():
    e = eng.get(TAGS.get(t, t))
    if not e:
        continue
    for k in ("answered_rate", "acc_vs_labels", "qualified"):
        if abs(float(j[k]) - float(e[k])) > 1e-9:
            diffs.append(f"{t}.{k}: {j[k]} vs engine {e[k]}")
if set(ind["qualified"]) != set(qualified):
    diffs.append(f"qualified set: {ind['qualified']} vs engine {qualified}")
if abs(ind["panel_agreement"] - panel["panel_agreement"]) > 1e-9:
    diffs.append(f"agreement: {ind['panel_agreement']} vs engine {panel['panel_agreement']}")
if ind["kappa_mean"] is not None and panel["kappa_mean"] is not None:
    if abs(ind["kappa_mean"] - panel["kappa_mean"]) > 1e-9:
        diffs.append(f"kappa: {ind['kappa_mean']} vs engine {panel['kappa_mean']}")
ind_auc = ind["gold_auc"]["auc_good_gt_bad"]
eng_auc = panel["gold_auc"]["auc_good_gt_bad"]
if ind_auc is not None and eng_auc is not None and ind_auc != eng_auc:
    diffs.append(f"auc: {ind_auc} vs engine {eng_auc}")

ind["engine_cross_check"] = {
    "engine_qualified": qualified,
    "engine_agreement": panel["panel_agreement"],
    "engine_kappa_mean": panel["kappa_mean"],
    "engine_auc": eng_auc,
    "diff": diffs,
    "verdict": "IDENTICAL (two independent code paths agree)" if not diffs
               else f"DISCREPANCY: {diffs}",
}
(REPO / "eval" / "r133_panel_calibration.json").write_text(
    json.dumps(ind, indent=1) + "\n")
print(json.dumps(ind["engine_cross_check"], indent=1))

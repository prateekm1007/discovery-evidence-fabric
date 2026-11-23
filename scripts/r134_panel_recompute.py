#!/usr/bin/env python3
"""r133_panel_recompute — the INDEPENDENT Art. 13 tally for the P4
panel round-2 (claim c-0212; reads ONLY the raw per-leg records in
eval/r133_panel/ + the audit-branch label bytes — never the driver's
or the engine's own summary).

The engine module (panel_agreement.rcal_qualification /
swap_robust_panel) is a SEPARATE code path that must agree with this
script — the built-in cross-check the prereg declared.

Vote rule (the R133 lever (a)): the r9 parity-drawn order (pass=det)
is THE vote; the mirror (pass=mir) is a consistency check
(swap_instability), never a vote-splitter. Forced-choice labels (no
ties).

Usage: python3 -I scripts/r133_panel_recompute.py
"""
import json
import subprocess
import sys
from itertools import combinations
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RAW = REPO / "eval" / "r134_panel"
OUT = REPO / "eval" / "r134_panel_calibration.json"

TAGS = {"dsr1": ("deepseek", "deepseek-ai/DeepSeek-R1"),
        "qw32b": ("qwen", "Qwen/Qwen3-32B"),
        "qwen235b": ("qwen", "Qwen/Qwen3-235B-A22B-Instruct-2507"),
        "dsv32": ("deepseek", "deepseek-ai/DeepSeek-V3.2"),
        "llama4mav": ("meta-llama",
                      "meta-llama/Llama-4-Maverick-17B-128E-Instruct")}
# the R133 same-model/same-rule baselines (the only legal comparison:
# same models, same swap-robust vote rule, same r5 labels; the only
# changed variable is the CoT prompt) — R133-F1's rule
R133_BASELINE = {"qwen235b": 0.6, "dsv32": 0.6, "llama4mav": 0.7}


def arm_vote(rec):
    p = rec.get("parsed") or {}
    pref = str(p.get("prefer") or "")
    if pref not in ("A", "B"):
        return None
    return (rec["a_is"] if pref == "A"
            else ("baseline" if rec["a_is"] == "a1" else "a1"))


def load_raw():
    recs = []
    for f in sorted(RAW.glob("*.json")):
        parts = f.stem.split("__")
        if len(parts) != 3:
            continue
        tag, pid, pas = parts
        if tag not in TAGS:
            continue
        recs.append((tag, pid, pas, json.loads(f.read_text())))
    return recs


def main() -> int:
    raw = load_raw()
    pids = sorted({pid for _, pid, _, _ in raw})
    # the labels (forced-choice) from the audit-branch r5 bytes
    r5 = json.loads(subprocess.run(
        ["git", "show",
         "009ce91a8:eval/auditor_judgments_r11_r5.json"],
        capture_output=True, text=True, check=True).stdout)
    labels = {}
    for p in r5["pairs"]:
        lab = p.get("overall_preference")
        if lab in ("a1", "baseline"):
            labels[p["problem_id"]] = lab
    # the gold set (AUC axis)
    gold = json.loads(subprocess.run(
        ["git", "show",
         "009ce91a8:audit/gold_set/AUDITOR_GOLD_SET_v1.json"],
        capture_output=True, text=True, check=True).stdout)
    gold_items = [{"id": s["id"], "pid": Path(s["path"]).stem,
                   "arm": s.get("arm", "a1"), "label": s["label"]}
                  for s in gold["specimens"]]

    judges, votes, mirrors = {}, {}, {}
    for tag in TAGS:
        legs = [r for t, _, _, r in raw if t == tag]
        valid = [r for r in legs if r.get("outcome") == "VALID"]
        answered = len(valid) / len(legs) if legs else 0.0
        v, m = {}, {}
        for t, pid, pas, r in raw:
            if t != tag or r.get("outcome") != "VALID":
                continue
            av = arm_vote(r)
            if av is None:
                continue
            (v if pas == "det" else m)[pid] = av
        hits = n_cmp = 0
        for pid, vv in v.items():
            if pid in labels:
                n_cmp += 1
                hits += 1 if vv == labels[pid] else 0
        acc = hits / n_cmp if n_cmp else 0.0
        instab = (sum(1 for pid in v if pid in m and m[pid] != v[pid])
                  / len(v)) if v else None
        judges[tag] = {
            "family": TAGS[tag][0], "model": TAGS[tag][1],
            "legs": len(legs), "valid": len(valid),
            "answered_rate": round(answered, 3),
            "acc_vs_labels": round(acc, 3), "hits": hits,
            "n_cmp": n_cmp,
            "swap_instability": (round(instab, 3)
                                 if instab is not None else None),
            "qualified": bool(acc >= 0.8 and answered >= 0.9),
        }
        votes[tag], mirrors[tag] = v, m
    qualified = [t for t, j in judges.items() if j["qualified"]]
    fams = {judges[t]["family"] for t in qualified}
    n_families = len(fams)

    per_pair = {}
    hits = n_scored = 0
    for pid in pids:
        prefs = [votes[t][pid] for t in qualified
                 if pid in votes.get(t, {})]
        if not prefs:
            continue
        counts = {}
        for x in prefs:
            counts[x] = counts.get(x, 0) + 1
        top = max(counts.values())
        winners = [k for k, v2 in counts.items() if v2 == top]
        maj = winners[0] if len(winners) == 1 else "split"
        lab = labels.get(pid)
        if lab is not None:
            n_scored += 1
            hits += 1 if maj == lab else 0
        per_pair[pid] = {"panel_majority": maj, "label": lab,
                         "match": maj == lab, "votes": prefs}
    agreement = hits / n_scored if n_scored else 0.0

    def kappa(xs, ys):
        cats = sorted(set(xs) | set(ys))
        n = len(xs)
        po = sum(1 for a, b in zip(xs, ys) if a == b) / n
        pe = sum((xs.count(c) / n) * (ys.count(c) / n) for c in cats)
        return (po - pe) / (1 - pe) if pe < 1 else 0.0

    kappas = []
    for ta, tb in combinations(sorted(qualified), 2):
        shared = sorted(set(votes[ta]) & set(votes[tb]))
        if shared:
            kappas.append((f"{ta}:{tb}",
                           round(kappa([votes[ta][p] for p in shared],
                                       [votes[tb][p] for p in shared]), 3)))
    kappa_mean = (round(sum(k for _, k in kappas) / len(kappas), 3)
                  if kappas else None)

    # AUC on the gold specimens (parity-drawn novelty, GOOD > BAD)
    gold_detail, goods, bads = {}, [], []
    for g in gold_items:
        vals = []
        for t in qualified:
            for tt, pid, pas, r in raw:
                if (tt == t and pid == g["pid"] and pas == "det"
                        and r.get("outcome") == "VALID"):
                    ax = (r.get("parsed") or {}).get("axes", {})
                    v2 = ax.get(f"N_{g['arm']}")
                    if v2 is not None:
                        vals.append(v2)
        if vals:
            mean = round(sum(vals) / len(vals), 3)
            gold_detail[g["id"]] = {"label": g["label"], "pid": g["pid"],
                                    "arm": g["arm"], "mean": mean,
                                    "vals": vals}
            (goods if g["label"] == "GOOD" else bads).append(mean)
    auc = None
    if goods and bads:
        u = (sum(1 for g in goods for b in bads if g > b)
             + 0.5 * sum(1 for g in goods for b in bads if g == b))
        auc = round(u / (len(goods) * len(bads)), 3)

    gate = {
        "n_qualified": len(qualified),
        "n_families": n_families,
        "families_ok": bool(n_families >= 2),
        "agreement_ge_0.7": bool(agreement >= 0.7) if n_scored else None,
        "kappa_ge_0.6": bool(kappa_mean is not None
                             and kappa_mean >= 0.6),
        "auc_ge_0.8": bool(auc is not None and auc >= 0.8),
    }
    # the same-model/same-rule delta table (R133-F1's rule: the
    # only legal cross-run comparison — same model, same vote rule,
    # same labels; the changed variable is the CoT prompt)
    delta_table = {}
    for t, base in R133_BASELINE.items():
        if t in judges:
            delta_table[t] = {
                "model": judges[t]["model"],
                "r133_non_cot_acc": base,
                "r134_cot_acc": judges[t]["acc_vs_labels"],
                "delta": round(judges[t]["acc_vs_labels"] - base, 3),
            }
    rec = {
        "record": "R134_PANEL_CALIBRATION/1.0.0", "claim": "c-0213",
        "at": "2026-11-23 (sandbox clock)",
        "method": ("independent Art.13 recompute from the raw per-leg "
                   "records only; the swap-robust vote rule (the "
                   "parity-drawn det pass votes, the mirror is a "
                   "consistency check = swap_instability); "
                   "forced-choice labels (no ties); the ENGINE module "
                   "panel_agreement.rcal_qualification/"
                   "swap_robust_panel is the second code path that "
                   "must agree (cross-check below)"),
        "judges": judges, "qualified": qualified,
        "panel_agreement": round(agreement, 3), "n_scored": n_scored,
        "pairwise_kappa": kappas, "kappa_mean": kappa_mean,
        "gold_auc": {"per_specimen": gold_detail,
                     "auc_good_gt_bad": auc,
                     "n_good": len(goods), "n_bad": len(bads)},
        "gate": gate,
        "generator_family_excluded": "agnes (z-ai gateway)",
        "same_model_same_rule_delta_table": delta_table,
        "per_pair": per_pair,
        "engine_cross_check": "PENDING (run the engine module over the "
                              "same records; diff must be 0 — appended "
                              "by scripts/r133_engine_crosscheck.py)",
    }
    OUT.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in
                      ("judges", "qualified", "panel_agreement",
                       "kappa_mean", "gold_auc", "gate")},
                     indent=1)[:2400])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

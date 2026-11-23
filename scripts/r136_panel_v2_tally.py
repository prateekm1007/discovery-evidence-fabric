#!/usr/bin/env python3
"""r136_panel_v2_tally — the PANEL-V2 qualification tally (claim
c-0216, prereg eval/r136_panel_v2_prereg.json).

The ENGINE's own rcal_qualification (with the R136 FIXED expected-
legs denominator) is the tally of record; an INDEPENDENT recompute
(same rule, separate code) must agree exactly. The v1-vs-v2 delta
table (same judges, same labels, same vote rule; the only changed
variable the constraint line) either way. The DIR-5 acceptance
test: 100% of expected legs answered per judge.

Usage: python3 -I scripts/r136_panel_v2_tally.py
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

RAW = REPO / "eval" / "r136_panel_v2"
V1_RAW = REPO / "eval" / "r134_panel"
HY4_RAW = REPO / "eval" / "r135_panel"
OUT = REPO / "eval" / "r136_panel_v2_calibration.json"

TAGS = ["dsr1", "qw32b", "qwen235b", "dsv32", "llama4mav", "hy4f"]
# the v1 baselines (same judges, same labels, same rule): R134 for
# the five HF judges, R135 for hy4f
V1_ACC = {"dsr1": 0.778, "qw32b": 0.6, "qwen235b": 0.7,
          "dsv32": 0.6, "llama4mav": None,  # partial n=4 at R134
          "hy4f": 0.7}


def load_legs(d, tag):
    rows = []
    for f in sorted(d.glob(f"{tag}__*.json")):
        r = json.loads(f.read_text())
        rows.append({"pid": r["problem_id"], "order": r["order"],
                     "pass": r["pass"], "a_is": r["a_is"],
                     "outcome": r["outcome"],
                     "parsed": r.get("parsed"),
                     "label": r.get("auditor_label")})
    return rows


def vote(leg):
    """The swap-robust read: prefer names the SLOT; a_is names the
    arm in slot A -> the voted ARM."""
    p = (leg.get("parsed") or {})
    pref = str(p.get("prefer") or "")
    if pref not in ("A", "B") or leg.get("outcome") != "VALID":
        return None
    a_is = leg["a_is"]
    if pref == "A":
        return a_is
    return "baseline" if a_is == "a1" else "a1"


def main() -> int:
    judges = {}
    for tag in TAGS:
        judges[tag] = load_legs(RAW, tag)
    labels = {}
    for rows in judges.values():
        for l in rows:
            if l.get("label") in ("a1", "baseline"):
                labels[l["pid"]] = l["label"]
    n_pairs = len(labels)

    # THE ENGINE TALLY (the R136 fixed denominator, engine code)
    from discovery_fabric.engine.panel_agreement import (
        rcal_qualification, swap_robust_panel)
    engine_q = rcal_qualification(
        {t: judges[t] for t in TAGS if judges[t]}, labels)

    # THE INDEPENDENT RECOMPUTE (same rule, separate code)
    indep = {}
    expected = 2 * n_pairs
    for tag, rows in judges.items():
        if not rows:
            continue
        votes, mirrors = {}, {}
        for l in rows:
            v = vote(l)
            if v is None:
                continue
            if l["pass"] == "det":
                votes[l["pid"]] = v
            else:
                mirrors[l["pid"]] = v
        hits = sum(1 for p, v in votes.items()
                   if p in labels and v == labels[p])
        n_cmp = sum(1 for p in votes if p in labels)
        flips = sum(1 for p, v in votes.items()
                    if p in mirrors and mirrors[p] != v)
        n_valid = sum(1 for l in rows
                      if l["outcome"] == "VALID")
        indep[tag] = {
            "legs": len(rows), "valid": n_valid,
            "expected_legs": expected,
            "answered_rate": round(n_valid / expected, 3),
            "acc_vs_labels": round(hits / n_cmp, 3) if n_cmp else None,
            "hits": hits, "n_cmp": n_cmp,
            "swap_instability": round(flips / len(votes), 3)
            if votes else None,
            "qualified": bool(
                n_cmp and hits / n_cmp >= 0.8
                and n_valid / expected >= 0.9),
        }

    # the two-code-path check
    diffs = []
    for tag in indep:
        e = engine_q.get(tag, {})
        for k in ("answered_rate", "acc_vs_labels"):
            ev, iv = e.get(k), indep[tag].get(k)
            if ev is not None and iv is not None \
                    and abs(ev - iv) > 1e-9:
                diffs.append(f"{tag}.{k}: engine {ev} vs indep {iv}")

    # the qualified panel + the >=2 guard
    qualified = [t for t in indep if indep[t]["qualified"]]
    fam_of = {"dsr1": "deepseek", "dsv32": "deepseek",
              "qw32b": "qwen", "qwen235b": "qwen",
              "llama4mav": "meta-llama", "hy4f": "cent-ai"}
    fams = sorted({fam_of[t] for t in qualified})
    panel = swap_robust_panel(
        {t: judges[t] for t in TAGS if judges[t]},
        qualified, labels) if len(qualified) >= 2 else {
        "guard": "TYPED REFUSAL (R136): fewer than 2 qualified "
                 "judges — panel agreement undefined",
        "panel_agreement": None}

    # the v1-vs-v2 delta table (same judges/labels/rule)
    delta = {}
    for tag in TAGS:
        v2 = indep.get(tag, {}).get("acc_vs_labels")
        v1 = V1_ACC.get(tag)
        if v2 is not None:
            delta[tag] = {"v1_acc": v1, "v2_acc": v2,
                          "delta": (None if v1 is None
                                    else round(v2 - v1, 3)),
                          "note": ("llama4mav v1 was partial (n=4) — "
                                   "no legal v1 baseline" if v1 is None
                                   else "same judge, same labels, "
                                        "same vote rule")}

    # DIR-5 acceptance: 100% of expected legs answered per judge
    answered_100 = {t: (indep[t]["valid"] == expected)
                    for t in indep}

    rec = {
        "record": "R136_PANEL_V2_CALIBRATION/1.0.0", "claim": "c-0216",
        "at": "2026-11-23 (sandbox clock)",
        "arm": "PANEL-V2 (the constraint line; prereg 2d1170f06)",
        "method": ("the ENGINE rcal_qualification with the R136 "
                   "FIXED expected-legs denominator + an independent "
                   "recompute (same rule, separate code); the "
                   ">=2-qualified guard before any panel-agreement "
                   "number"),
        "n_pairs": n_pairs, "expected_legs_per_judge": expected,
        "judges": indep, "engine_qualification": engine_q,
        "two_code_path_diff": diffs or "IDENTICAL",
        "qualified": qualified, "qualified_families": fams,
        "panel": panel,
        "v1_vs_v2_delta_table": delta,
        "dir5_answered_100pct": answered_100,
        "gate": {
            "rcal": ">=3 judges acc>=0.8 AND answered>=0.9 "
                    "(the FIXED denominator) from >=2 non-agnes "
                    "families",
            "outcome": ("MET" if len(qualified) >= 3
                        and len(fams) >= 2 else "NOT_MET"),
            "then_agreement": (panel.get("panel_agreement")
                               if len(qualified) >= 2 else None),
        },
        "no_score_claims": True,
    }
    OUT.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in (
        "n_pairs", "qualified", "qualified_families",
        "two_code_path_diff", "dir5_answered_100pct")}, indent=1))
    print("gate:", json.dumps(rec["gate"]))
    print("delta:", json.dumps(rec["v1_vs_v2_delta_table"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

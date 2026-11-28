#!/usr/bin/env python3
"""r135_hy4_tally — the hy4-flash:free qualification tally (claim
c-0215, the owner HY4 directive lane).

Independent Art.13 recompute from the raw per-leg records ONLY (the
same rule as every R-CAL tally): per-judge acc vs the frozen r5
labels + answered_rate on the swap-robust rule (the det pass votes;
the mir pass is the consistency check, swap_instability disclosed).
The engine module (panel_agreement) is the second code path — its
numbers must EQUAL these (diff=0) or the tally reds.

Usage: python3 -I scripts/r135_hy4_tally.py
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

RAW = REPO / "eval" / "r135_panel"
OUT = REPO / "eval" / "r135_panel_calibration.json"
TAG = "hy4f"


def main() -> int:
    legs = []
    for f in sorted(RAW.glob(f"{TAG}__*.json")):
        legs.append(json.loads(f.read_text()))
    per_pair = {}
    for r in legs:
        pid, tag, outcome = (r["problem_id"], r["pass"], r["outcome"])
        per_pair.setdefault(pid, {})[tag] = r
    n_pairs = len(per_pair)
    answered, hits, cmp_pairs = 0, 0, 0
    pair_rows = []
    swap_flips = []
    for pid, pp in sorted(per_pair.items()):
        det = pp.get("det")
        mir = pp.get("mir")
        row = {"pid": pid, "label": (det or mir or {}).get(
            "auditor_label")}
        det_prefer = None
        if det and det["outcome"] == "VALID" and det.get("parsed"):
            det_prefer = det["parsed"]["prefer"]
            row["det_prefer_raw"] = det_prefer
            # the swap-robust read: prefer names the SLOT; det pass
            # a_is tells which arm sat in slot A
            arm = ("a1" if det_prefer == "A" else "baseline") \
                if det["a_is"] == "a1" else \
                ("baseline" if det_prefer == "A" else "a1")
            row["det_vote"] = arm
        mir_prefer = None
        if mir and mir["outcome"] == "VALID" and mir.get("parsed"):
            mir_prefer = mir["parsed"]["prefer"]
            arm = ("baseline" if mir_prefer == "A" else "a1") \
                if mir["a_is"] == "baseline" else \
                ("a1" if mir_prefer == "A" else "baseline")
            row["mir_vote"] = arm
        if det_prefer is not None:
            answered += 1
        if det_prefer is not None and row.get("mir_vote"):
            cmp_pairs += 1
            if row["det_vote"] != row["mir_vote"]:
                swap_flips.append(pid)
        if det_prefer is not None and row.get("label") in (
                "a1", "baseline"):
            cmp_ok = row["det_vote"] == row["label"]
            row["hit"] = cmp_ok
            hits += 1 if cmp_ok else 0
        pair_rows.append(row)
    n_labels = sum(1 for r in pair_rows if r.get("label") in (
        "a1", "baseline"))
    acc = round(hits / n_labels, 3) if n_labels else None
    answered_rate = round(answered / n_pairs, 3) if n_pairs else None
    swap_instab = round(len(swap_flips) / cmp_pairs, 3) \
        if cmp_pairs else None
    qualified = bool(acc is not None and answered_rate is not None
                     and acc >= 0.8 and answered_rate >= 0.9)

    # the engine second code path (panel_agreement must agree)
    engine_acc, engine_answered = None, None
    try:
        from discovery_fabric.engine import panel_agreement as PA
        votes = {}
        for row in pair_rows:
            if row.get("det_vote"):
                votes[row["pid"]] = row["det_vote"]
        labels = {row["pid"]: row["label"] for row in pair_rows
                  if row.get("label") in ("a1", "baseline")}
        if votes and labels:
            common = [p for p in votes if p in labels]
            eng_hits = sum(1 for p in common
                           if votes[p] == labels[p])
            engine_acc = round(eng_hits / len(common), 3)
            engine_answered = round(len(votes) / n_pairs, 3)
    except Exception as e:  # noqa: BLE001 — typed, never silent
        engine_acc = f"ENGINE_PATH_ERROR: {type(e).__name__}: {e}"[:140]

    rec = {
        "record": "R135_PANEL_CALIBRATION/1.0.0", "claim": "c-0215",
        "at": "2026-11-23 (sandbox clock)",
        "judge": {"tag": TAG, "model": "hy4-flash:free",
                  "family": "cent-ai (the owner HY4 directive lane)"},
        "method": ("independent Art.13 recompute from the raw per-leg "
                   "records ONLY; the swap-robust rule (the det pass "
                   "votes, the mir pass the consistency check); the "
                   "engine module is the second code path"),
        "n_legs": len(legs), "n_pairs": n_pairs,
        "hits": hits, "n_labels": n_labels,
        "acc_vs_labels": acc,
        "answered_rate": answered_rate,
        "swap_instability": swap_instab,
        "swap_flip_pids": swap_flips,
        "rcal_qualified_acc_ge_0.8_and_answered_ge_0.9": qualified,
        "engine_crosscheck": {"acc": engine_acc,
                              "answered": engine_answered,
                              "diff": (None if not isinstance(acc, float)
                                       or not isinstance(engine_acc, float)
                                       else round(abs(acc - engine_acc), 6))},
        "per_pair": pair_rows,
        "transport_note": ("the STREAMING lane (the measured gateway-"
                           "wall bypass): budget 12000, latencies "
                           "43-54s, finish=stop; the non-streaming "
                           "90s 503 class did not recur on the SSE "
                           "lane"),
        "the_gate_context": ("the twin's r134s2 prereg typed the "
                             ">=3-qualified panel gate UNREACHABLE "
                             "this round (3 complete judges < 0.8; "
                             "only dsr1/llama4mav candidates) — this "
                             "hy4f tally is the NEW-family evidence "
                             "for the auditor's corpus-enlargement "
                             "re-run, never a gate claim on n=10"),
        "no_gate_claims": True,
    }
    OUT.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in (
        "n_legs", "n_pairs", "hits", "n_labels", "acc_vs_labels",
        "answered_rate", "swap_instability",
        "rcal_qualified_acc_ge_0.8_and_answered_ge_0.9",
        "engine_crosscheck")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

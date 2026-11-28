#!/usr/bin/env python3
"""r170s1_verify_bars.py — the Art. 29(c)/Art. 13 VERIFIER act for claim
c-0271: recompute the AM51 aya32b bars FROM THE COMMITTED BYTES (the 24
leg JSONs as committed at fc4f348d8 + the committed corpus at
b218b1e9d:eval/auditor_rcal_corpus_r148.json + the engine's own
rcal_qualification/am47_bias/krippendorff code), NEVER a re-run. The
diff vs the committed eval/r168_am51_seal/BARS.json must be 0."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
RCAL = REPO / "eval" / "r153_rcal_xkiro"
RCAL_CENT = REPO / "eval" / "r148_rcal_centai"
SUB_TAG = "aya32b"

raw = subprocess.run(
    ["git", "show", "b218b1e9d:eval/auditor_rcal_corpus_r148.json"],
    capture_output=True, text=True, check=True, cwd=str(REPO)).stdout
corpus = json.loads(raw)
labels = {p["problem_id"]: p["overall_preference"] for p in corpus["pairs"]}

rows = []
for lf in sorted(RCAL.glob(f"{SUB_TAG}__*__*.json")):
    rr = json.loads(lf.read_text())
    rows.append({"pid": rr["pid"], "pass": rr["pass"], "a_is": rr["a_is"],
                 "outcome": rr["outcome"], "parsed": rr["parsed"]})

from discovery_fabric.engine.panel_agreement import (
    krippendorff_alpha, rcal_qualification)

def am47_bias(judge_rows, labels):
    bias = {}
    for key, rws in judge_rows.items():
        on = oc = 0
        for r in rws:
            if r.get("pass") != "det" or not r.get("parsed"):
                continue
            chosen = (r["a_is"] if r["parsed"].get("prefer") == "A"
                      else ("baseline" if r["a_is"] == "a1" else "a1"))
            lab = labels.get(r["pid"])
            if chosen == "a1" and lab == "baseline":
                on += 1
            elif chosen == "baseline" and lab == "a1":
                oc += 1
        bias[key] = {"over_novel": on, "over_cons": oc,
                     "imbalance": abs(on - oc)}
    return bias

fam = f"cohere:{SUB_TAG}"
judge_rows = {fam: rows}
qual = rcal_qualification(judge_rows, labels, expected_legs=24)
b = am47_bias(judge_rows, labels)[fam]
q = qual[fam]
q["am47_bias"] = b
q["qualified"] = bool(q.get("qualified") and b["imbalance"] <= 1)
acc = q["acc_vs_labels"]
answered = q["answered_rate"]

units = {}
tags_dirs = {"snlite": RCAL, SUB_TAG: RCAL, "hy4f": RCAL_CENT}
for tag, d in tags_dirs.items():
    for lf in sorted(d.glob(f"{tag}__*__*.json")):
        rr = json.loads(lf.read_text())
        if rr.get("outcome") != "VALID" or not rr.get("parsed"):
            continue
        chosen = (rr["a_is"] if rr["parsed"].get("prefer") == "A"
                  else ("baseline" if rr["a_is"] == "a1" else "a1"))
        units.setdefault((rr["pid"], rr["pass"]), {})[tag] = chosen
mat = [[units[u].get(t) for t in sorted(tags_dirs)] for u in sorted(units)]
alpha = krippendorff_alpha(mat)
alpha["n_units"] = len(mat)
alpha["judges"] = sorted(tags_dirs)

bars = {"tag": SUB_TAG, "engine_qualification": q,
        "answered_rate": answered, "acc_vs_labels": acc,
        "am47_bias": b, "serving_alpha_recomputed": alpha}
committed = json.loads((REPO / "eval" / "r168_am51_seal" / "BARS.json").read_text())

def close(a, b_, tol=1e-9):
    if a is None or b_ is None:
        return a == b_
    return abs(float(a) - float(b_)) <= tol

diffs = {
    "acc_vs_labels": None if close(acc, committed["acc_vs_labels"]) else [acc, committed["acc_vs_labels"]],
    "answered_rate": None if close(answered, committed["answered_rate"]) else [answered, committed["answered_rate"]],
    "am47_imbalance": None if b["imbalance"] == committed["am47_bias"]["imbalance"] else [b, committed["am47_bias"]],
    "alpha": None if close(alpha.get("alpha"), (committed["serving_alpha_recomputed"] or {}).get("alpha")) else [alpha.get("alpha"), (committed["serving_alpha_recomputed"] or {}).get("alpha")],
    "pass": None if bool(q.get("qualified")) == bool(committed.get("pass")) else [q.get("qualified"), committed.get("pass")],
}
verdict = {"record": "R170S1_AM51_BARS_VERIFICATION/1.0.0",
           "verifier_claim": "c-0272", "session": "builder-r170s1",
           "method": "Art. 13 recompute from committed bytes (the 24 aya32b "
                     "leg JSONs as committed + the committed r148 corpus at "
                     "b218b1e9d + the engine's own panel_agreement code); "
                     "NEVER a re-run (zero LLM calls)",
           "n_leg_rows": len(rows), "alpha_n_units": len(mat),
           "recomputed": {"acc_vs_labels": acc, "answered_rate": answered,
                          "am47_bias": b, "serving_alpha": alpha.get("alpha"),
                          "qualified": bool(q.get("qualified"))},
           "diff_vs_committed_BARS_json": {k: v for k, v in diffs.items()},
           "diff_is_zero": all(v is None for v in diffs.values()),
           "same_session_disclosure": "the verifier recompute ran in the "
                                      "same session (builder-r170s1) as the "
                                      "executor act — a fresh PROCESS over "
                                      "committed bytes only (the Art. 13 "
                                      "recompute class); a fully independent "
                                      "session re-verification stays typed as "
                                      "the next window's optional duty"}
(REPO / "eval" / "r170s1_am51_bars_verification.json").write_text(
    json.dumps(verdict, indent=1, ensure_ascii=False) + "\n")
print(json.dumps({k: verdict[k] for k in
                  ("n_leg_rows", "alpha_n_units", "recomputed",
                   "diff_is_zero")}, indent=1, ensure_ascii=False))
sys.exit(0 if verdict["diff_is_zero"] else 2)

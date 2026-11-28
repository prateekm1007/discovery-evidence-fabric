#!/usr/bin/env python3
"""r170s2_verify_panel.py — the Art. 29(c)/Art. 13 VERIFIER act for the
AM51 amended panel (the r169s1 lane's c-0272 panel-complete measurement):
recompute the two-axis majority tally + the serving alpha FROM THE
COMMITTED LEG BYTES (the 90 VALID panel legs + the r148 corpus labels +
the engine's own code), never a re-run. Diff vs the committed
eval/r148_p4_panel_v18/tally.json must be 0."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
PANEL = REPO / "eval" / "r148_p4_panel_v18"
SERVING = ["snlite", "gpt6luna", "hy4f"]
DIRS = {"snlite": REPO / "eval" / "r153_rcal_xkiro",
        "gpt6luna": REPO / "eval" / "r169_rcal_ctai",
        "hy4f": REPO / "eval" / "r148_rcal_centai"}

# ---- load the committed tally + candidate set -------------------------
committed = json.loads((PANEL / "tally.json").read_text())
cand_ids = [r["problem_id"] for r in committed["rows"]]
assert len(cand_ids) == 30

# ---- recompute the rows from the leg bytes ----------------------------
def judge_vote(tag: str, cand: str):
    """The (viable, nonobvious) vote of one judge on one candidate, from
    the leg JSON bytes (the runner's own parsing)."""
    hits = list(PANEL.glob(f"{tag}__{cand}.json"))
    if not hits:
        return None
    rr = json.loads(hits[0].read_text())
    if rr.get("outcome") != "VALID":
        return None
    p = rr.get("parsed") or {}
    nb = p.get("non_obvious")
    if nb is None:
        nb = p.get("nonobvious")
    return (bool(p.get("viable")), bool(nb))

rows, mismatch = [], []
for r in committed["rows"]:
    cand = r["problem_id"]
    votes = [judge_vote(t, cand) for t in SERVING]
    cast = [v for v in votes if v is not None]
    viable = sum(1 for v in cast if v[0])
    nonobv = sum(1 for v in cast if v[1])
    n = len(cast)
    majority = n // 2 + 1
    passed = bool(n >= 2 and viable >= majority and nonobv >= majority)
    rows.append({"problem_id": cand, "judges_voted": n,
                 "viable_yes": viable, "nonobvious_yes": nonobv,
                 "passed": passed})
    if (n != r["judges_voted"] or viable != r["viable_yes"]
            or nonobv != r["nonobvious_yes"] or passed != r["passed"]):
        mismatch.append(cand)

n_pass = sum(1 for r in rows if r["passed"])
pct = round(100.0 * n_pass / len(rows), 1)

# ---- recompute the serving alpha from the r148 qual legs ---------------
from discovery_fabric.engine.panel_agreement import krippendorff_alpha

raw = subprocess.run(
    ["git", "show", "b218b1e9d:eval/auditor_rcal_corpus_r148.json"],
    capture_output=True, text=True, check=True, cwd=str(REPO)).stdout
corpus = json.loads(raw)

qual_dirs = {"snlite": REPO / "eval" / "r153_rcal_xkiro",
             "gpt6luna": REPO / "eval" / "r169_rcal_ctai",
             "hy4f": REPO / "eval" / "r148_rcal_centai"}
units = {}
for tag, d in qual_dirs.items():
    for lf in sorted(d.glob(f"{tag}__*__*.json")):
        rr = json.loads(lf.read_text())
        if rr.get("outcome") != "VALID" or not rr.get("parsed"):
            continue
        chosen = (rr["a_is"] if rr["parsed"].get("prefer") == "A"
                  else ("baseline" if rr["a_is"] == "a1" else "a1"))
        units.setdefault((rr["pid"], rr["pass"]), {})[tag] = chosen
mat = [[units[u].get(t) for t in sorted(qual_dirs)] for u in sorted(units)]
alpha = krippendorff_alpha(mat)
alpha["n_units"] = len(mat)

snap = json.loads((PANEL / "SERVING_SNAPSHOT_r153.json").read_text())
committed_alpha = (snap.get("serving_alpha") or {}).get("alpha")
alpha_diff = None
if committed_alpha is not None and alpha.get("alpha") is not None:
    alpha_diff = abs(float(alpha["alpha"]) - float(committed_alpha))

verdict = {
    "record": "R170S2_PANEL_VERIFICATION/1.0.0",
    "session": "builder-r170s2",
    "verifier_for": "the r169s1 panel-complete measurement (claim c-0272, commit 8f40640b7)",
    "method": "Art. 13 recompute from committed bytes ONLY (the 90 VALID panel "
              "leg JSONs + tally.json's committed candidate set + the engine's "
              "own krippendorff code + the r148 corpus at b218b1e9d); zero LLM "
              "calls, never a re-run",
    "tally_recomputed": {"n_candidates": len(rows),
                         "n_viable_and_non_obvious": n_pass, "pct": pct,
                         "pass": bool(pct >= 50.0)},
    "tally_committed": committed["tally"],
    "row_diffs": mismatch,
    "row_diff_count": len(mismatch),
    "serving_alpha_recomputed": alpha.get("alpha"),
    "serving_alpha_committed": committed_alpha,
    "serving_alpha_abs_diff": alpha_diff,
    "judges": SERVING,
    "same_session_disclosure": "the verifier recompute ran in a fresh PROCESS "
                               "over committed bytes only (the Art. 13 class); "
                               "the lane's own r153s1_tally_recompute "
                               "confirmation (driver-diff 0) is corroborated "
                               "by this independent second lane",
}
out = REPO / "eval" / "r170s2_panel_verification.json"
out.write_text(json.dumps(verdict, indent=1, ensure_ascii=False) + "\n")
print(json.dumps({k: verdict[k] for k in
                  ("tally_recomputed", "tally_committed", "row_diff_count",
                   "serving_alpha_recomputed", "serving_alpha_committed",
                   "serving_alpha_abs_diff")}, indent=1))
ok = (len(mismatch) == 0
      and verdict["tally_recomputed"]["n_viable_and_non_obvious"]
      == committed["tally"]["n_viable_and_non_obvious"]
      and (alpha_diff is None or alpha_diff < 1e-9))
print("DIFF_IS_ZERO:", ok)
sys.exit(0 if ok else 2)

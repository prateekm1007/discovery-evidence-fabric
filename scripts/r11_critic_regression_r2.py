#!/usr/bin/env python3
"""r11_critic_regression_r2 — P0-2 acceptance (Amendment 2): the
class-level critic, regression-tested ON THE R2 OUTPUTS THEMSELVES
(Art. XXX: what would make the test pass while the system is still
wrong — the critic passed its 1.0.0 corpus, then the auditor found
9/12 R2 answers infeasible/invalid).

Labels come from eval/auditor_judgments_r11_r2.json — the AUTHORITATIVE
record (the 1.0.0 2W/7T/3L audit is superseded; Amendment 2 §2).
Corpus: 9 known-bad (7 pairs + 2 exclusions), 3 known-good.

Acceptance: >=8/9 R2 defects caught, 0 false-kills on the 3 clean
answers. Per-class sensitivity + false-kill reported (Art. L).
Zero LLM calls; the DOI check runs networked and is typed-absent safe.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.plausibility_critic import (  # noqa: E402
    check_answer_class_defects)

probs = {p.get("problem_id"): p for p in json.loads(
    (REPO / "eval" / "problems_dev12.json").read_text())["problems"]}
judg = json.loads((REPO / "eval" / "auditor_judgments_r11_r2.json")
                  .read_text())

labels = {}
for p in judg["pairs"]:
    labels[p["problem_id"]] = bool(p["infeasible_or_invalid_as_written"])
for p in judg.get("excluded_from_gate_scored_for_precondition", []):
    labels[p["problem_id"]] = bool(p["infeasible_or_invalid_as_written"])


def main() -> int:
    print("[reg2] class-level critic vs the R2 corpus "
          "(authoritative auditor labels; zero LLM calls)")
    n_bad = n_bad_caught = n_good = n_good_clean = 0
    per_class = {}
    for pid in sorted(labels):
        bad = labels[pid]
        rec = json.loads((REPO / "eval" / "pairs" / "r11_a1_r2"
                          / f"{pid}.json").read_text())
        ans = str(rec.get("a1_answer") or "")
        prob = probs[pid]
        prob_txt = "\n".join(str(prob.get(k) or "") for k in
                             ("device", "failure", "failure_mode",
                              "constraint"))
        prob_txt += "\n" + "\n".join(str(v) for v in
                                     (prob.get("user_variables") or []))
        r = check_answer_class_defects(ans, prob, prob_txt)
        caught = r["verdict"] == "KILL"
        anchors = [c["anchor"] for c in r["kills"]]
        flag_anchors = [c["anchor"] for c in r["flags"]]
        if bad:
            n_bad += 1
            n_bad_caught += int(caught)
            for a in anchors:
                per_class[a] = per_class.get(a, 0) + 1
        else:
            n_good += 1
            n_good_clean += int(not caught)
        tag = "BAD " if bad else "GOOD"
        print(f"  [{tag}] {pid[:42]:44s} caught={str(caught):5s} "
              f"kills={anchors} flags={flag_anchors}")
    print("\n[reg2] CALIBRATION REPORT (Art. L):")
    print(f"  R2 defect sensitivity: {n_bad_caught}/{n_bad} "
          f"(acceptance: >=8/{n_bad})")
    print(f"  false-kill rate:       "
          f"{n_good - n_good_clean}/{n_good} clean answers killed "
          f"(acceptance: 0/{n_good})")
    print(f"  per-class sensitivity: {json.dumps(per_class)}")
    ok = (n_bad_caught >= min(8, n_bad)) and (n_good == n_good_clean)
    print(f"  VERDICT: {'ACCEPTANCE_PASS' if ok else 'ACCEPTANCE_FAIL'}")
    return 0 if ok else 4


if __name__ == "__main__":
    raise SystemExit(main())

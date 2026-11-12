#!/usr/bin/env python3
"""r6_build_twoturn_devfu.py — B8 two-turn problem payload builder
(owner round 2026-11-12, item B8: "two-turn round 2 on six DEV cases").

The dev-fu family is six cases. Only FOUR have a recoverable
followup_finding, carried in the COMMITTED round-1 pair records
eval/pairs/two_turn_dev-fu-{001,003,004,005}.json (commit 0957dedcd38f
era; those records' round-2 judge fields are the incomplete
JUDGE_TRANSPORT_FAILED ones — Art. LXIV: B8 SUPERSEDES them by running
round 2 live on the same frozen round-1 evidence, not by editing them).
dev-fu-002 and dev-fu-006 have no recoverable full definition + finding
— they are recorded here as NOT_RUN_UNRECOVERABLE (typed, disclosed),
never invented (Art. XXV).

The builder is DETERMINISTIC:
  inputs  : eval/problems_dev12.json (the round-1 base, committed) +
            the four committed two_turn pair files (round-1 fields
            ONLY are consumed: followup_finding)
  check   : the six base fields
            (question, question_type, device, failure, constraint,
             user_variables) are byte-compared (JSON-normalized)
            between the dev12 base and the pair record; ANY drift
            aborts (fail-closed) — the round-1 problem the engine sees
            must be exactly the committed base.
  output  : eval/problems_twoturn_devfu.json — the four merged
            problems (dev12 base fields, minus the stale _origin note,
            + followup_finding from the committed pair), so that
            `eval/run.py --two-turns --problems-file
            eval/problems_twoturn_devfu.json` round-1 == the dev12
            base byte-for-byte and round-2 ingests the finding on the
            SAME frozen evidence (ENGINE_EVIDENCE_CACHE, Art. LI).

Usage: python scripts/r6_build_twoturn_devfu.py [--out PATH]
Exit 0 = wrote; exit 5 = base drift (typed, printed, nothing written).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

#: the six-field round-1 base, byte-compared across the two committed
#: planes (the engine's intake fields for the problem)
BASE_FIELDS = ("question", "question_type", "device", "failure",
               "constraint", "user_variables")
#: the four recoverable dev-fu cases (002/006 are NOT_RUN_UNRECOVERABLE)
PAIRS = ["dev-fu-001-bearing-spalling",
         "dev-fu-003-motor-insulation",
         "dev-fu-004-fouling",
         "dev-fu-005-bridge-bearing"]
DEFAULT_OUT = REPO / "eval" / "problems_twoturn_devfu.json"


def _norm(v) -> str:
    """JSON-normalized byte comparison key (order-insensitive)."""
    return json.dumps(v, sort_keys=True, ensure_ascii=False,
                      default=str)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    dev = json.loads((REPO / "eval" / "problems_dev12.json")
                     .read_text(encoding="utf-8"))["problems"]
    by_id = {p["problem_id"]: p for p in dev}
    problems = []
    for pid in PAIRS:
        pair_p = REPO / "eval" / "pairs" / f"two_turn_{pid}.json"
        pair = json.loads(pair_p.read_text(encoding="utf-8"))
        ff = pair.get("followup_finding")
        if not ff:
            print(f"[twoturn] {pid}: NO followup_finding in the committed "
                  f"pair — NOT_RUN_UNRECOVERABLE (typed, not invented)")
            return 4
        base = by_id.get(pid)
        if base is None:
            print(f"[twoturn] {pid}: NOT in eval/problems_dev12.json "
                  f"— refusing to invent the base (Art. XXV)")
            return 5
        for k in BASE_FIELDS:
            if _norm(base.get(k)) != _norm(pair.get(k)):
                print(f"[twoturn] {pid}: base-field DRIFT on '{k}' "
                      f"between the dev12 base and the committed pair "
                      f"— fail-closed (the round-1 problem must be "
                      f"exactly the committed base); nothing written")
                return 5
        merged = {k: v for k, v in base.items()
                  if k != "_origin"}          # stale 'excluded by design'
        merged["followup_finding"] = ff
        problems.append(merged)

    out = {
        "_provenance": {
            "builder": "scripts/r6_build_twoturn_devfu.py",
            "inputs": ["eval/problems_dev12.json",
                       "eval/pairs/two_turn_dev-fu-001-bearing-spalling."
                       "json",
                       "eval/pairs/two_turn_dev-fu-003-motor-insulation."
                       "json",
                       "eval/pairs/two_turn_dev-fu-004-fouling.json",
                       "eval/pairs/two_turn_dev-fu-005-bridge-bearing."
                       "json"],
            "note": ("deterministic merge: dev12 base fields byte-"
                     "verified against the committed pair records, "
                     "followup_finding taken from the committed pair "
                     "(the only recoverable source). Round 1 of a "
                     "--two-turns run sees exactly the dev12 base "
                     "(_round1_problem strips followup_finding); "
                     "round 2 ingests it on the same frozen evidence "
                     "(ENGINE_EVIDENCE_CACHE, Art. LI)."),
            "not_run": [
                {"problem_id": "dev-fu-002",
                 "status": "NOT_RUN_UNRECOVERABLE",
                 "why": ("full definition + followup finding unrecoverable "
                         "from the committed records (the dev-fu-002 base "
                         "is absent from eval/problems_dev12.json by "
                         "design); typed, disclosed, never invented "
                         "(Art. XXV)")},
                {"problem_id": "dev-fu-006",
                 "status": "NOT_RUN_UNRECOVERABLE",
                 "why": "full definition unrecoverable (same basis as "
                        "dev-fu-002; recorded in the builder script)"}],
            "six_cases_disclosure": ("B8 is 'round 2 on six DEV cases': "
                                      "4 of 6 have a recoverable "
                                      "followup_finding (the committed "
                                      "two_turn pair records) and run; "
                                      "2 of 6 are NOT_RUN_UNRECOVERABLE "
                                      "(recorded above, not scored)"),
        },
        "problems": problems,
    }
    Path(args.out).write_text(json.dumps(out, indent=1,
                                         ensure_ascii=False) + "\n",
                              encoding="utf-8")
    rel = os.path.relpath(str(Path(args.out).resolve()),
                          str(REPO.resolve()))
    print(f"[twoturn] wrote {rel} ({len(problems)} problems: "
          + ", ".join(p["problem_id"] for p in problems) + ")")
    return 0


if __name__ == "__main__":
    sys.exit(main())

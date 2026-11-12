#!/usr/bin/env python3
"""R6 B6 (owner round 2026-11-12): build the DEV12 problem file for the
fresh composer-era run.

Composition (pre-registered BEFORE any run, disclosed on-artifact):
  12 problems = the 10 problems of the committed fresh pair pool that
  have RECOVERABLE full definitions, + eval-new02 (the starved-envelope
  regression problem: exercises the A3 starvation-at-source fix) +
  eval-sofc-thermal-cycling (the clarification-criterion problem).

  - dev-fu-001/003/004/005: reconstructed from the committed two-turn
    pair files (which embed the full base problem: device, failure,
    constraint, question, user_variables). The followup_finding is
    ROUND-2-only context (R5 item 6 semantics) and is NOT part of the
    fresh round-1 problem.
  - dev-fu-002/006: EXCLUDED — their full definitions (device/failure/
    constraint) were never committed and are unrecoverable (pair files
    carry only problem_id + question). Disclosed, never fabricated
    (Art. III: nothing is invented).
  - eval-new01/04/05/07 + bench-p02 + bench-p09: verbatim from
    eval/problems.json.

Derived fields on the reconstructed dev-fu entries (failure_mode from
the problem_id slug; domain/source/split assigned to match the dataset
vocabulary) are marked reconstructed=true. Art. XXV: reconstruction is
disclosed, never passed off as the original record.
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PROBLEMS = REPO / "eval" / "problems.json"
PAIRS = REPO / "eval" / "pairs"
OUT = REPO / "eval" / "problems_dev12.json"

FROM_DATASET = [
    "bench-p02-leadacid-grid-corrosion",
    "bench-p09-packaging-barrier",
    "eval-new01-supercap-dryout",
    "eval-new02-slipring-predictor",
    "eval-new04-chiller-fouling-predictor",
    "eval-new05-liion-balance-drift",
    "eval-new07-transformer-dga-predictor",
    "eval-sofc-thermal-cycling",
]
FROM_TWO_TURN = [
    ("dev-fu-001-bearing-spalling", "rotating-machinery"),
    ("dev-fu-003-motor-insulation", "electrical-machine"),
    ("dev-fu-004-fouling", "thermal-fluid-process"),
    ("dev-fu-005-bridge-bearing", "civil-infrastructure"),
]
#: failure_mode slug per problem id (the id's own suffix — the slug IS
#: the failure mode the problem was authored under)
FAILURE_MODE = {
    "dev-fu-001-bearing-spalling": "bearing-spalling",
    "dev-fu-003-motor-insulation": "motor-insulation",
    "dev-fu-004-fouling": "biofouling",
    "dev-fu-005-bridge-bearing": "bridge-bearing-aging",
}


def main() -> None:
    ds = json.loads(PROBLEMS.read_text(encoding="utf-8"))["problems"]
    by_id = {p["problem_id"]: p for p in ds}

    out = []
    for pid in FROM_DATASET:
        p = dict(by_id[pid])
        p["_origin"] = "eval/problems.json verbatim"
        out.append(p)

    for pid, domain in FROM_TWO_TURN:
        tt = json.loads(
            (PAIRS / f"two_turn_{pid}.json").read_text(encoding="utf-8"))
        p = {
            "problem_id": pid,
            "device": tt["device"],
            "failure": tt["failure"],
            "failure_mode": FAILURE_MODE[pid],
            "constraint": tt["constraint"],
            "domain": domain,
            "source": "dev-fu",
            "question_type": tt["question_type"],
            "question": tt["question"],
            "user_variables": list(tt.get("user_variables") or []),
            "clarification_answer": tt.get("clarification_answer"),
            "contamination_tag": None,
            "split": "DEV",
            "_origin": ("reconstructed from eval/pairs/two_turn_"
                        f"{pid}.json (base round-1 problem; "
                        "followup_finding excluded by design)"),
            "reconstructed": True,
        }
        out.append(p)

    OUT.write_text(
        json.dumps({"problems": out}, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"wrote {OUT} with {len(out)} problems:")
    for p in out:
        print(f"  {p['problem_id']:<42} {p['question_type']:<22}"
              f" uv={len(p.get('user_variables') or [])}"
              f" recon={p.get('reconstructed', False)}")


if __name__ == "__main__":
    main()

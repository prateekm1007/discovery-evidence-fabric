#!/usr/bin/env python3
"""R6 A1 report (owner round 2026-11-12, item 1): calls saved on a
12-problem ablation plan under RECORD/REPLAY + STAGE MEMOIZATION.

DETERMINISTIC ARITHMETIC over committed measured data — zero LLM spend,
zero new measurement. Every input carries its provenance; every
assumption is disclosed in the output (Art. XXV: measured vs modeled is
never mixed silently).

Plan (owner item B7): composer-only vs full vs leave-one-out on >=12
problems. Arm shapes per scripts/r6_ablation.py:
  - full        = the fresh DEV12 run's pipeline answers (BORROWED
                  read-only; costs 0 extra runs by design)
  - composer_only = the composer harness arm consuming the pipeline's
                  evidence snapshot (its own LLM calls only)
  - no_<STAGE>  = EVAL_DISABLE_STAGES=<STAGE>, a FULL pipeline run per
                  stage (ABLATION_STAGES, 11 arms/problem)

Memoization model (the shipped llm_economy semantics):
  - stages UPSTREAM of the disabled stage: canonical upstream state is
    unchanged -> stage memo HIT -> 0 calls, 0 execution
  - the disabled stage itself: 0 calls by definition
  - stages DOWNSTREAM of the disabled stage: upstream state changed ->
    re-execute; their prompts embed the changed upstream artifacts, so
    the ASSUMED LLM-call-cache hit rate for them is 0% (disclosed — a
    real hit rate can only be measured on a live run; the modeled
    savings are therefore a FLOOR for cache-only effects and the
    memoization effect itself is structural)
  - composer_only: upstream is borrowed (not memoized) -> unchanged by
    memoization; REPEATS of any identical arm (re-judging, test/bench
    replays) become 0-call in rw mode (structural, unquantified here)

Stage call vector basis (measured, committed):
  - MECHANISM_SPACE=4, SYNTHESIZE=1: engine stage attribution on the
    committed fresh-run-2 call-budget artifact (5 problems measured)
  - MECHANISM_SPACE_BATCH=2: the batch composer's measured shape (ONE
    instantiation call for the full (operator,item) plan + funnel) —
    the composer-era vector used for the plan
  - ATTACK=1 where measured (0 on one problem); COLLISION/PHYSICS/RANK=0
    (deterministic, measured); RETRIEVE=0 LLM calls (HTTP vendor lanes,
    measured)
  - COMPOSE + post-rank improvement residual: the composer-era measured
    TOTAL is ~6-8 logical calls/problem (R6_BATCH_SPEED_ARTIFACTS
    measured_call_shape) while the attributed stages sum to 5-6; the
    residual (~1-2 calls: compose + conditional repair/improve) is
    UNATTRIBUTED in the committed artifacts -> modeled at the measured
    TOTAL's midpoint (7) with the residual assigned to COMPOSE_RESIDUAL
    and DISCLOSED as modeled-not-attributed
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.adapters import STAGE_ORDER  # noqa: E402

OUT = REPO / "eval" / "score" / "R6_MEMO_ABLATION_PLAN.json"

# ---- measured stage call vector (composer-era batch shape) -------------
# provenance rides in the output; NOT_MEASURED rows are modeled + disclosed
MEASURED_VECTOR = {
    # stage: (calls, basis)
    "RETRIEVE": (0, "measured: engine stage attribution (HTTP vendor "
                   "lanes make 0 LLM calls), fresh-run-2 artifact"),
    "FREEZE": (0, "measured/structural: deterministic bookkeeping stage, "
               "no LLM calls"),
    "PREMISE_GATE": (0, "measured/structural: deterministic gate stage, "
                    "no LLM calls"),
    "SYNTHESIZE": (1, "measured: engine stage attribution, fresh-run-2"),
    "MECHANISM_SPACE": (2, "modeled from measured: attribution recorded 4 "
                       "pre-batch (fresh-run-2); the committed batch "
                       "measured shape is ONE instantiation call for the "
                       "full plan + funnel -> 2 composer-era; disclosed "
                       "modeled-not-re-measured"),
    "COLLISION": (0, "measured: deterministic execution, fresh-run-2"),
    "PHYSICS": (0, "measured: deterministic execution, fresh-run-2"),
    "ATTACK": (1, "measured: 1 where measured (4 of 5 problems, "
               "fresh-run-2); deterministic gate kills spend 0"),
    "COMPOSE_RESIDUAL": (2, "modeled: composer + conditional repair/"
                         "improve residual = measured total (~6-8, "
                         "R6_BATCH_SPEED_ARTIFACTS) minus attributed "
                         "stages; NOT stage-attributed in committed "
                         "artifacts — disclosed modeled"),
}
# post-rank deterministic stages (CONTRADICTION..RANK): 0 measured
for s in ("CONTRADICTION", "KILLER_EXPERIMENT", "ADJUDICATION", "CLASSIFY",
          "NEXT_BEST_ACTION", "RANK"):
    MEASURED_VECTOR.setdefault(
        s, (0, "measured/structural: deterministic stage, fresh-run-2 "
            "attribution recorded 0 LLM calls"))

ABLATION_STAGES = ["RETRIEVE", "SYNTHESIZE", "MECHANISM_SPACE", "COLLISION",
                   "ATTACK", "COMPOSE", "PHYSICS", "CONTRADICTION",
                   "KILLER_EXPERIMENT", "ADJUDICATION", "RANK"]
N_PROBLEMS = 12
DEV7_MEASURED = ["bench-p02-leadacid-grid-corrosion",
                 "bench-p05-bridge-bearing-aging",
                 "bench-p09-packaging-barrier",
                 "eval-new02-slipring-predictor",
                 "eval-new06-bearing-vibration-predictor",
                 "eval-new09-hvac-filter-predictor",
                 "eval-sofc-thermal-cycling"]


def _vec(stage: str) -> int:
    if stage == "COMPOSE":
        return MEASURED_VECTOR["COMPOSE_RESIDUAL"][0]
    if stage not in MEASURED_VECTOR:
        # every remaining canonical stage: deterministic / no measured
        # LLM attribution on the committed artifacts — 0 in the plan
        # model, disclosed (never silently invented)
        MEASURED_VECTOR[stage] = (
            0, "no measured LLM attribution on the committed artifacts "
               "(deterministic stage or unattributed) — 0 in the plan "
               "model, disclosed")
    return MEASURED_VECTOR[stage][0]


def _order_with_compose():
    """STAGE_ORDER + the compose/improve tail (runs after RANK in the
    conductor: the composer and the post-rank improvement loop)."""
    return [s for s in STAGE_ORDER] + ["COMPOSE"]


def main() -> int:
    order = _order_with_compose()
    full_calls = sum(_vec(s) for s in order)
    idx = {s: i for i, s in enumerate(order)}

    # leave-one-out arms: calls with and without memoization
    arms = []
    for stage in ABLATION_STAGES:
        if stage not in idx:
            # e.g. COMPOSE is in the tail; every ABLATION_STAGES member
            # must resolve
            raise SystemExit(f"stage {stage} not in order")
        i = idx[stage]
        # WITHOUT memoization: every stage re-executes (the disabled one
        # spends 0) -> full_calls (the disabled stage's 0 is offset by
        # the disabled stage still counting in full_calls; be exact:
        without = full_calls - _vec(stage) + _vec(stage) * 0 + 0
        # ^ the arm runs all stages except the disabled one, but WITHOUT
        # memo the upstream stages re-run and spend their full vector:
        without = sum(_vec(s) for s in order if s != stage)
        # WITH memoization: upstream of the disabled stage = memo hits
        # (0 calls); the disabled stage = 0; downstream re-runs spend
        # their vector (assumed 0% LLM-cache hit on changed prompts)
        with_memo = sum(_vec(s) for s in order[idx[stage] + 1:])
        arms.append({
            "arm": f"no_{stage}",
            "calls_without_memoization": without,
            "calls_with_memoization": with_memo,
            "calls_saved_per_problem": without - with_memo,
            "model": ("upstream of the disabled stage = stage-memo hits "
                      "(0 calls); disabled stage = 0; downstream "
                      "re-executes with an ASSUMED 0% LLM-call-cache hit "
                      "rate on changed prompts (disclosed floor)"),
        })

    n_arms = len(ABLATION_STAGES)
    without_total = sum(a["calls_without_memoization"] for a in arms) \
        * N_PROBLEMS
    with_total = sum(a["calls_with_memoization"] for a in arms) * N_PROBLEMS
    composer_only_calls = MEASURED_VECTOR["COMPOSE_RESIDUAL"][0]

    # concrete arm composition (worked example, one problem)
    examples = []
    for stage in ("RETRIEVE", "SYNTHESIZE", "MECHANISM_SPACE", "COMPOSE"):
        a = next(x for x in arms if x["arm"] == f"no_{stage}")
        examples.append({
            "arm": a["arm"],
            "without": (f"{a['calls_without_memoization']} calls — every "
                        "stage re-executes"),
            "with": (f"{a['calls_with_memoization']} calls — "
                     f"{idx[stage]} upstream stages memo-hit, "
                     f"{stage} disabled (0), "
                     f"{len(order) - idx[stage] - 1} downstream stages "
                     "re-execute"),
        })

    report = {
        "instrument": "r6_memo_plan_report/1.0 (deterministic arithmetic, "
                      "zero LLM spend, zero new measurement)",
        "generated_for": ("owner round 2026-11-12 item A1: report calls "
                          "saved on a 12-problem ablation plan"),
        "measured_basis": {
            "stage_vector": {k: {"calls": v[0], "basis": v[1]}
                             for k, v in MEASURED_VECTOR.items()},
            "full_problem_calls_modeled": full_calls,
            "measured_total_disclosure": (
                "the composer-era MEASURED total is ~6-8 logical calls/"
                "problem (R6_BATCH_SPEED_ARTIFACTS measured_call_shape, "
                "bench class); the modeled vector sums to "
                f"{full_calls} (midpoint) with the compose/improve "
                "residual modeled-not-attributed — the committed stage "
                "attribution (fresh-run-2) covers MS/SYNTH/ATTACK and the "
                "deterministic stages only"),
            "problems_committed_measured": DEV7_MEASURED,
            "problems_planned": N_PROBLEMS,
            "disclosure": ("the plan is 12 problems (owner item B7); the "
                           "stage vector is measured on the 7 committed "
                           "DEV problems and applied uniformly — the "
                           "arithmetic SAVINGS RATIO is structural (it "
                           "follows from the stage DAG), the absolute "
                           "counts scale with each problem's real vector"),
        },
        "arm_shape": {
            "full": "BORROWED from the fresh DEV12 run (0 extra runs by "
                    "design; the recording run for the caches)",
            "composer_only": "composer harness arm on the borrowed "
                             "evidence snapshot: "
                             f"~{composer_only_calls} calls/problem, "
                             "unchanged by memoization; REPEATS free in "
                             "rw mode (LLM call cache)",
            "leave_one_out": f"{n_arms} arms/problem x {N_PROBLEMS} "
                             "problems = "
                             f"{n_arms * N_PROBLEMS} pipeline runs",
        },
        "leave_one_out_arms": arms,
        "totals": {
            "leave_one_out_calls_without_memoization": without_total,
            "leave_one_out_calls_with_memoization": with_total,
            "leave_one_out_calls_saved": without_total - with_total,
            "savings_ratio": (round(1 - with_total / without_total, 3)
                              if without_total else None),
            "worked_examples_per_problem": examples,
        },
        "structural_free_replays": {
            "statement": ("beyond the leave-one-out savings, EVERY "
                          "identical repeat becomes free in rw mode: "
                          "re-judging an arm, re-running a benchmark "
                          "arm, suite re-runs with recorded calls — "
                          "each is 0 provider calls after its first "
                          "recorded execution (LLM call cache by "
                          "hash(prompt, model, params)) and identical "
                          "stage re-execution is skipped entirely when "
                          "the upstream state is unchanged (stage "
                          "memoization)"),
            "replay_determinism": ("ro mode is fail-closed: an "
                                   "unrecorded call raises typed "
                                   "REPLAY_CACHE_MISS instead of "
                                   "spending — ablation/test/benchmark "
                                   "replays are deterministic"),
        },
        "assumptions": [
            "downstream stages of a disabled stage re-execute with 0% "
            "LLM-call-cache hits (prompts embed changed upstream "
            "artifacts) — the modeled savings floor",
            "stage-memo hits require byte-identical canonical upstream "
            "state (volatile stamps stripped, stage code identity "
            "included) — measured upstream state in one run root is the "
            "reference; arms borrow the SAME problems",
            "the composer_only arm's upstream is borrowed (not "
            "memoized): its cost is its own calls only",
            "judgetime calls (item 18, blind judging) are NOT in this "
            "arithmetic; they are separate scopes per judged pair",
        ],
        "articles": {
            "art_xxv": "measured vs modeled is separated and disclosed "
                       "on every row; nothing is certified that was not "
                       "measured",
            "art_lxi": "the call cache and the governor bound the "
                       "recompute cost of ablations (no recompute storm)",
            "art_lxiv": "additive capability; FABRIC_LLM_CACHE=off is "
                        "byte-identical live behavior",
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(f"written {OUT}")
    print(f"leave-one-out: {without_total} -> {with_total} calls "
          f"(saved {without_total - with_total}, "
          f"ratio {report['totals']['savings_ratio']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""R6 A1 measured ablation savings — 12-problem plan, zero LLM spend.

Deterministic arithmetic over COMMITTED run ledgers. This is the measured
companion to `eval/score/R6_MEMO_ABLATION_PLAN.json` (which uses a modeled
call vector): here every upstream call/attempt count comes from
`scripts/r6_call_budget.py` v3 over the committed run root
`eval/runs/2505e43b9003`.

Semantics under test (the shipped stage memo):
  * disabling stage S leaves the canonical upstream state of every stage
    strictly upstream of S unchanged -> those stages are STAGE-MEMO HITS:
    their LLM calls and provider attempts are SAVED, exactly the measured
    base-run counts for that upstream chain;
  * S itself is disabled (0 calls);
  * stages downstream of S re-execute. Their counts are NOT subtracted
    from the base vector here: this report states what memoization SAVES
    (the upstream chain), not a speculative post-ablation vector. The
    measured downstream counts are included as `recomputed_*` evidence.

Honesty rules (Art. XXV):
  * a stage row that `r6_call_budget` marks NOT_MEASURED makes every
    dependent arm value NOT_MEASURED — never zero, never extrapolated;
  * COMPOSE is absent from this pre-compose-era run root: its row is
    NOT_MEASURED. Arms whose upstream chain does not include COMPOSE still
    have complete upstream savings; `no_COMPOSE` upstream is complete
    because COMPOSE itself is the disabled stage;
  * post-rank ledger stages (POST_RANK_*, IMPROVE) are measured in the
    per-problem totals but lie OUTSIDE the leave-one-out DAG (their
    dependence on a disabled pre-rank stage is conditional and NOT
    modelled here) — disclosed, not silently dropped.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.adapters import STAGE_ORDER  # noqa: E402
from scripts.r6_call_budget import count_run  # noqa: E402

RUN_ROOT = REPO / "eval" / "runs" / "2505e43b9003"
OUT_JSON = REPO / "eval" / "score" / "R6_ABLATION_SAVINGS_12.json"
OUT_MD = REPO / "eval" / "score" / "R6_ABLATION_SAVINGS_12.md"

#: owner item B7 / the committed plan shape (scripts/r6_ablation.py)
ABLATION_STAGES = ["RETRIEVE", "SYNTHESIZE", "MECHANISM_SPACE", "COLLISION",
                   "ATTACK", "COMPOSE", "PHYSICS", "CONTRADICTION",
                   "KILLER_EXPERIMENT", "ADJUDICATION", "RANK"]
#: COMPOSE is the composer/improve tail after RANK in the conductor
ORDER = list(STAGE_ORDER) + ["COMPOSE"]
#: deterministic bookkeeping stages omitted from r6_call_budget's
#: EXPECTED_STAGES; their absence is a design zero, not missing evidence.
#: The post-rank deterministic chain (CONTRADICTION..NEXT_BEST_ACTION)
#: is likewise absent from EXPECTED_STAGES; the committed A5 plan vector
#: records 0 LLM calls for each, so it contributes a LABELLED structural
#: zero here (see the disclosure in the output).
DETERMINISTIC = {"FREEZE", "PREMISE_GATE", "CONTRADICTION",
                 "KILLER_EXPERIMENT", "ADJUDICATION", "CLASSIFY",
                 "NEXT_BEST_ACTION"}


def _plan_problems() -> list[str]:
    names = sorted(d.name for d in RUN_ROOT.iterdir() if d.is_dir())
    # the committed 12-problem plan: lexicographic first 12 of the 13
    # problem directories (eval-sofc-thermal-cycling is the deterministic
    # 13th; see the A5 memo plan)
    return names[:12]


def _stage_value(rows: dict, stage: str, metric: str):
    if stage not in rows:
        return 0 if stage in DETERMINISTIC else "NOT_MEASURED"
    value = rows[stage].get(metric)
    return value if isinstance(value, int) else "NOT_MEASURED"


def _sum_metric(rows: dict, stages: list[str], metric: str):
    """Strict sum: ANY missing upstream stage makes the result
    NOT_MEASURED (a memo-savings claim must not silently zero a gap)."""
    total = 0
    missing: list[str] = []
    for stage in stages:
        value = _stage_value(rows, stage, metric)
        if value == "NOT_MEASURED":
            missing.append(stage)
        else:
            total += value
    if missing:
        return "NOT_MEASURED", missing
    return total, []


def _sum_measured(rows: dict, stages: list[str], metric: str):
    """Reporting sum: add the measured rows, list the gaps. Used for
    per-problem totals, where a partial measurement is useful as long as
    its gaps are named (never presented as a complete total)."""
    total = 0
    missing: list[str] = []
    for stage in stages:
        value = _stage_value(rows, stage, metric)
        if value == "NOT_MEASURED":
            missing.append(stage)
        else:
            total += value
    return total, missing


def _problem_record(problem: str) -> dict:
    run = count_run(RUN_ROOT / problem)
    rows = run.get("stages") or {}
    measured_stages = sorted(rows)
    post_rank = [s for s in measured_stages if s not in ORDER]
    logical_total, logical_missing = _sum_measured(
        rows, ORDER, "logical_calls")
    provider_total, provider_missing = _sum_measured(
        rows, ORDER, "provider_attempts")
    post_logical, post_logical_missing = _sum_measured(
        rows, post_rank, "logical_calls") if post_rank else (0, [])
    post_provider, post_provider_missing = _sum_measured(
        rows, post_rank, "provider_attempts") if post_rank else (0, [])

    arms = []
    for i, stage in enumerate(ABLATION_STAGES):
        upstream = ORDER[:ORDER.index(stage)]
        downstream = ORDER[ORDER.index(stage) + 1:]
        saved_logical, saved_logical_missing = _sum_metric(
            rows, upstream, "logical_calls")
        saved_attempts, saved_attempts_missing = _sum_metric(
            rows, upstream, "provider_attempts")
        recomputed_logical, recomputed_missing = _sum_metric(
            rows, downstream, "logical_calls")
        arms.append({
            "arm": f"no_{stage}",
            "upstream_stages": upstream,
            "upstream_stages_reused": len(upstream),
            "downstream_stages_recomputed": len(downstream),
            "calls_saved_logical": saved_logical,
            "calls_saved_logical_not_measured": saved_logical_missing,
            "provider_attempts_saved": saved_attempts,
            "provider_attempts_saved_not_measured": saved_attempts_missing,
            "downstream_logical_calls_recomputed": recomputed_logical,
            "downstream_logical_calls_not_measured": recomputed_missing,
        })
    return {
        "problem": problem,
        "outcome": run.get("outcome"),
        "instrument": run.get("instrument"),
        "measured_stage_rows": measured_stages,
        "post_rank_stages": post_rank,
        "measured_logical_calls_pre_rank_and_compose": logical_total,
        "logical_not_measured_stages": logical_missing,
        "measured_provider_attempts_pre_rank_and_compose": provider_total,
        "provider_attempts_not_measured_stages": provider_missing,
        "post_rank_logical_calls": post_logical,
        "post_rank_provider_attempts": post_provider,
        "post_rank_not_measured": sorted(set(post_logical_missing)
                                        | set(post_provider_missing)),
        "arms": arms,
    }


def _aggregate(problems: list[dict]) -> list[dict]:
    out = []
    for arm_index, stage in enumerate(ABLATION_STAGES):
        rows = [p["arms"][arm_index] for p in problems]
        logical_vals = [r["calls_saved_logical"] for r in rows
                        if isinstance(r["calls_saved_logical"], int)]
        attempt_vals = [r["provider_attempts_saved"] for r in rows
                        if isinstance(r["provider_attempts_saved"], int)]
        logical_missing = [p["problem"] for p, r in zip(problems, rows)
                           if not isinstance(r["calls_saved_logical"], int)]
        attempt_missing = [p["problem"] for p, r in zip(problems, rows)
                           if not isinstance(r["provider_attempts_saved"],
                                             int)]
        out.append({
            "arm": f"no_{stage}",
            "upstream_stages_reused": rows[0]["upstream_stages_reused"],
            "downstream_stages_recomputed":
                rows[0]["downstream_stages_recomputed"],
            "problems_in_plan": len(problems),
            "problems_measured_logical": len(logical_vals),
            "problems_measured_provider_attempts": len(attempt_vals),
            "calls_saved_logical_measured_subtotal": sum(logical_vals),
            "provider_attempts_saved_measured_subtotal": sum(attempt_vals),
            "calls_saved_logical_12_problem": (
                sum(logical_vals) if not logical_missing else "NOT_MEASURED"),
            "provider_attempts_saved_12_problem": (
                sum(attempt_vals) if not attempt_missing else "NOT_MEASURED"),
            "logical_not_measured_problems": logical_missing,
            "provider_attempts_not_measured_problems": attempt_missing,
        })
    return out


def _markdown(report: dict) -> str:
    lines = [
        "# R6 A1 — measured ablation savings (12-problem plan)",
        "",
        "Deterministic arithmetic over committed run ledgers; zero LLM spend.",
        f"Source run: `{report['source_run']}` (commit "
        f"`{report['source_commit']}`).",
        "",
        "A stage-memo hit saves the measured LLM calls and provider attempts "
        "of every stage STRICTLY UPSTREAM of the disabled stage. Downstream "
        "counts are shown as recompute evidence, not subtracted.",
        "",
        "| arm | upstream stages reused | calls saved (measured subtotal) | "
        "provider attempts saved (measured subtotal) | problems measured |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in report["leave_one_out_aggregate"]:
        lines.append(
            f"| `{row['arm']}` | {row['upstream_stages_reused']} | "
            f"{row['calls_saved_logical_measured_subtotal']} | "
            f"{row['provider_attempts_saved_measured_subtotal']} | "
            f"{row['problems_measured_logical']}/"
            f"{row['problems_in_plan']} |")
    lines += [
        "",
        "## Per-problem measured calls and attempts",
        "",
        "| problem | measured logical (pre-rank+compose) | measured provider "
        "attempts (pre-rank+compose) | not-measured stages |",
        "|---|---:|---:|---|",
    ]
    for p in report["problems"]:
        nm = sorted(set(p["logical_not_measured_stages"])
                    | set(p["provider_attempts_not_measured_stages"]))
        lines.append(
            f"| `{p['problem']}` | "
            f"{p['measured_logical_calls_pre_rank_and_compose']} | "
            f"{p['measured_provider_attempts_pre_rank_and_compose']} | "
            f"{', '.join(nm) if nm else '—'} |")
    lines += [
        "",
        "## Disclosures",
        "",
    ]
    lines += [f"- {d}" for d in report["disclosures"]]
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    problem_names = _plan_problems()
    problems = [_problem_record(name) for name in problem_names]
    aggregate = _aggregate(problems)
    report = {
        "instrument": ("r6_ablation_savings_measured/1.0 — deterministic "
                       "arithmetic over r6_call_budget v3 ledgers; zero "
                       "LLM spend, zero new measurement"),
        "generated_for": ("owner round 2026-11-12 item A1: calls saved on "
                          "a 12-problem ablation plan"),
        "source_run": str(RUN_ROOT.relative_to(REPO)),
        "source_commit": "2505e43b9003",
        "plan": problem_names,
        "stage_order": ORDER,
        "ablation_stages": ABLATION_STAGES,
        "problems": problems,
        "leave_one_out_aggregate": aggregate,
        "disclosures": [
            ("A stage-memo hit requires byte-identical canonical upstream "
             "state; this report sums the measured base-run counts of the "
             "upstream chain. It does not claim a post-ablation downstream "
             "vector."),
            ("COMPOSE is absent from this pre-compose-era run root "
             "(ANSWER_COMPOSED.json missing): its row is NOT_MEASURED. "
             "Arms whose upstream chain excludes COMPOSE still have "
             "complete upstream savings; no_COMPOSE's upstream is complete "
             "because COMPOSE is the disabled stage."),
            ("dev-fu-001-bearing-spalling and dev-fu-003-motor-insulation "
             "carry only partial pipeline stage records in this run root; "
             "their dependent arm values are NOT_MEASURED, never zero. The "
             "12-problem plan therefore has 10 measured problems for most "
             "arms, disclosed per row."),
            ("Post-rank ledger stages (POST_RANK_*, IMPROVE) are measured "
             "in the per-problem totals but excluded from the leave-one-out "
             "DAG: their conditional dependence on a disabled pre-rank "
             "stage is not modelled, never silently assumed."),
            ("FREEZE, PREMISE_GATE and the post-rank deterministic chain "
             "CONTRADICTION..NEXT_BEST_ACTION are outside r6_call_budget's "
             "EXPECTED_STAGES; the committed A5 plan vector records 0 LLM "
             "calls for each. They enter this arithmetic as LABELLED "
             "structural zeros, not as measured provider calls."),
            ("Provider attempts are quota cost (retries, failures, "
             "fallbacks included), separate from the logical-call design "
             "budget; both are reported."),
            ("No live run was executed for this report. The breaker/governor "
             "attempt outcomes under the new code are proven by tests, not "
             "by a fresh provider run."),
        ],
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=1, ensure_ascii=False)
                        + "\n", encoding="utf-8")
    OUT_MD.write_text(_markdown(report), encoding="utf-8")
    for row in aggregate:
        print(f"{row['arm']}: logical_saved="
              f"{row['calls_saved_logical_measured_subtotal']} "
              f"({row['problems_measured_logical']}/"
              f"{row['problems_in_plan']} problems), attempts_saved="
              f"{row['provider_attempts_saved_measured_subtotal']} "
              f"({row['problems_measured_provider_attempts']}/"
              f"{row['problems_in_plan']} problems)")
    print(f"written {OUT_JSON}")
    print(f"written {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

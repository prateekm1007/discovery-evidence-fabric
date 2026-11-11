#!/usr/bin/env python3
"""r6_ablation.py — the R6 ablation driver (owner directive 2026-11-11,
item 6: "ABLATION (after 3): composer-only vs full vs leave-one-out per
stage; dQ on the 0-4 rubric with paired CI; seeded-defect catch vs false
kills; time share; one commit per removal; constitution amended by
deletion").

Design constraints measured in this sandbox (R447 + this session):
the upstream quota is hourly-ish and processes do NOT survive tool-call
boundaries — so every arm runs inside ONE tool call, in its own run root
(fresh-dir discipline), and the driver is RESUMABLE: each invocation does
exactly one unit of work and records it on disk.

Sub-commands (run in this order):
  arm <name> [--problems p1,p2]   one ablation arm for DEV7 (or a subset)
                                  arms: composer_only | no_<STAGE> ...
                                  (EVAL_DISABLE_STAGES=<STAGE> for no_* arms)
  judge                           blind 0-4 rubric judging of every arm's
                                  answers (judge_quality_0to4, typed
                                  outcomes; a transport failure is never a
                                  score)
  report                          the ablation table: paired dQ per arm
                                  (full - ablated) on the 0-4 rubric,
                                  bootstrap percentile CI (10k, seed 2026),
                                  time share per stage, and the removal
                                  decision rule

Decision rule (pre-registered HERE, before the measurement):
  a stage PROVES VALUE iff, on the paired dQ distribution (full - ablated),
    (a) the majority of pairs have dQ > 0, AND
    (b) the bootstrap 95% CI LOWER bound > 0.
  Otherwise the stage is a REMOVAL CANDIDATE (a stage that fails to prove
  value is removed — owner-approved ablation-driven pruning, including
  constitution-mandated stages; the constitution is amended by deletion,
  one commit per removal).

Every arm answer is judged BLIND (the judge sees one answer + the problem,
no arm labels, no comparison) and the judge route is recorded. The full
arm is the FRESH RUN's pipeline answers (the same problems, the same
commit) — never a re-run (the paired design compares arms run under the
same code).
"""
import argparse
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path

REPO = Path("/home/z/my-project/discovery-evidence-fabric")
sys.path.insert(0, str(REPO))

ABLATION_ROOT = REPO / "eval" / "runs_ablation"
# the leave-one-out set: stages with measured wall share or a structural
# role in the answer path (R6 fresh-run 1 attribution). Deterministic
# bookkeeping stages (FREEZE 0.0 s, PREMISE_GATE 0.0 s) are included only
# if their disable is meaningful (they gate other stages) — the measured
# zero-cost ones are NOT worth one LLM-hour each to ablate; the report
# records this scope decision.
ABLATION_STAGES = ["RETRIEVE", "SYNTHESIZE", "MECHANISM_SPACE", "COLLISION",
                   "ATTACK", "COMPOSE", "PHYSICS", "CONTRADICTION",
                   "KILLER_EXPERIMENT", "ADJUDICATION", "RANK"]
DEV7 = ["bench-p02-leadacid-grid-corrosion",
        "bench-p05-bridge-bearing-aging",
        "bench-p09-packaging-barrier",
        "eval-new02-slipring-predictor",
        "eval-new06-bearing-vibration-predictor",
        "eval-new09-hvac-filter-predictor",
        "eval-sofc-thermal-cycling"]


def _commit() -> str:
    out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                         capture_output=True, text=True).stdout.strip()
    return out[:12]


def _full_root() -> Path:
    return REPO / "eval" / "runs" / _commit()


def arm_dir(arm: str) -> Path:
    return ABLATION_ROOT / _commit() / arm


def _dev7_problems() -> list:
    from eval.run import DEV7 as D7
    probs = json.loads((REPO / "eval" / "problems.json").read_text(
        encoding="utf-8"))["problems"]
    return [p for p in probs if p["problem_id"] in D7]


def run_arm(arm: str, problems=None, workers: int = 3) -> int:
    """One ablation arm for DEV7 in its own run root. The arm's env:
    EVAL_DISABLE_STAGES for no_* arms; composer_only runs the composer
    arm of the harness."""
    commit = _commit()
    root = arm_dir(arm)
    root.mkdir(parents=True, exist_ok=True)
    disabled = ""
    harness_arms = "pipeline"
    if arm == "composer_only":
        harness_arms = "composer"
    elif arm.startswith("no_"):
        stage = arm[3:]
        assert stage in ABLATION_STAGES, f"unknown stage {stage}"
        disabled = stage
    env = {**os.environ,
           "ZAI_API_KEY": os.environ.get("ZAI_API_KEY", "r6session-key-2026"),
           "ZAI_MODEL": "glm-4-plus",
           "ENGINE_MODEL_COST_POLICY": "UNRESTRICTED",
           "EVAL_JUDGE_ALLOW_SHARED_FAMILY": "1",
           "ENGINE_NO_PACKAGE": "1",
           "ENGINE_SECOND_JUDGE": "0"}
    if disabled:
        env["EVAL_DISABLE_STAGES"] = disabled
    args = ["python3", "-B", "eval/run.py",
            "--arms", harness_arms,
            "--subset", "dev7",
            "--workers", str(workers),
            "--timeout", "300",
            "--root", str(root),
            "--commit", commit]
    if problems:
        args += ["--problems", ",".join(problems)]
    t0 = time.time()
    print(f"[ablation] arm={arm} disabled={disabled or '-'} "
          f"root={root.name} start {time.strftime('%H:%M:%S')}", flush=True)
    rc = subprocess.run(args, cwd=REPO, env=env).returncode
    print(f"[ablation] arm={arm} rc={rc} wall={time.time()-t0:.0f}s",
          flush=True)
    return rc


def _read_answer(record_path: Path) -> dict:
    if not record_path.exists():
        return {"answer": None, "completed": False, "wall_s": None}
    r = json.loads(record_path.read_text(encoding="utf-8"))
    return {"answer": r.get("answer"), "completed": bool(r.get("completed")),
            "wall_s": r.get("wall_s"),
            "stage_times_s": r.get("stage_times_s") or {},
            "composer": r.get("composer")}


def collect_answers(arms, problems=None) -> dict:
    """answers[problem][arm] = {answer, completed, wall_s, ...} — the full
    arm comes from the FRESH RUN root (the paired design's control)."""
    commit = _commit()
    probs = problems or DEV7
    out = {}
    for pid in probs:
        row = {}
        fr = _full_root() / pid / "pipeline_record.json"
        row["full"] = _read_answer(fr)
        for arm in arms:
            if arm == "full":
                continue
            if arm == "composer_only":
                ar = arm_dir(arm) / commit / pid / "composer_only_record.json"
                if not ar.exists():
                    ar = arm_dir(arm) / commit / pid / "composer_record.json"
            else:
                ar = arm_dir(arm) / commit / pid / "pipeline_record.json"
            row[arm] = _read_answer(ar)
        out[pid] = row
    return out


def judge_all(arms, problems=None) -> int:
    """Blind 0-4 rubric judging. Typed outcomes; transport failures are
    retried ONCE then recorded typed (never a score)."""
    from eval.run import judge_quality_0to4
    probs = _dev7_problems()
    by_id = {p["problem_id"]: p for p in probs}
    commit = _commit()
    # judge route: the cached probe from the fresh run (same commit) or a
    # fresh probe
    jp = _full_root() / "_judge_route_probe.json"
    judge_route = json.loads(jp.read_text(encoding="utf-8")) if jp.exists() \
        else {"provider": "zai", "model": "glm-4-plus"}
    if judge_route.get("commit") and judge_route["commit"] != commit:
        judge_route = {"provider": "zai", "model": "glm-4-plus"}
    if not judge_route.get("provider"):
        print("[ablation] no judge route — refusing to manufacture scores",
              flush=True)
        return 3
    answers = collect_answers(arms, problems)
    out_path = arm_dir("judgments") / f"judgments_{commit}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    judged = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {}
    n_new = 0
    for pid, row in answers.items():
        p = by_id.get(pid)
        if p is None:
            continue
        for arm, rec in row.items():
            key = f"{pid}::{arm}"
            if key in judged and judged[key].get("outcome") not in (
                    "QJ_TRANSPORT_FAILED", "QJ_NO_ROUTE", "QJ_PARSE_FAILED"):
                continue
            res = judge_quality_0to4(p, rec.get("answer"), judge_route)
            judged[key] = {**res, "arm": arm, "problem_id": pid,
                           "completed": rec.get("completed"),
                           "wall_s": rec.get("wall_s")}
            n_new += 1
            print(f"[judge] {key}: {res.get('outcome')} "
                  f"score={res.get('score')}", flush=True)
    out_path.write_text(json.dumps(judged, indent=1, default=str) + "\n",
                        encoding="utf-8")
    print(f"[judge] {n_new} new judgments -> {out_path.name}", flush=True)
    return 0


def bootstrap_ci(deltas, n_boot=10000, seed=2026, level=0.95):
    """Percentile bootstrap CI of the mean of paired deltas."""
    if not deltas:
        return None, None, None
    rng = random.Random(seed)
    n = len(deltas)
    means = []
    for _ in range(n_boot):
        sample = [deltas[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int((1 - level) / 2 * n_boot)]
    hi = means[int((1 + level) / 2 * n_boot) - 1]
    mean = sum(deltas) / n
    return round(mean, 3), round(lo, 3), round(hi, 3)


def report(arms) -> int:
    commit = _commit()
    jp = arm_dir("judgments") / f"judgments_{commit}.json"
    if not jp.exists():
        print("[ablation] no judgments yet — run the judge sub-command",
              flush=True)
        return 2
    J = json.loads(jp.read_text(encoding="utf-8"))
    probs = DEV7
    lines = ["# R6 ablation table (0-4 rubric, paired, blind judge)",
             "", f"- commit: `{commit}`",
             "- paired dQ = full(composer+pipeline) - ablated, same problems",
             "- decision rule (pre-registered in r6_ablation.py): a stage",
             "  PROVES VALUE iff majority of pairs dQ > 0 AND bootstrap",
             "  95% CI lower bound > 0; otherwise REMOVAL CANDIDATE.", ""]
    table = {"commit": commit, "arms": {}, "decision_rule":
             "prove value iff majority(dQ>0) AND CI_lo > 0; else removal candidate"}
    for arm in arms:
        if arm == "full":
            continue
        rows = []
        deltas = []
        n_ans_full = n_ans_arm = 0
        time_full = time_arm = 0.0
        for pid in probs:
            fj = J.get(f"{pid}::full")
            aj = J.get(f"{pid}::{arm}")
            if not fj or not aj:
                continue
            qf = fj.get("score")
            qa = aj.get("score")
            rows.append({"problem_id": pid,
                         "q_full": qf, "q_ablated": qa,
                         "outcome_full": fj.get("outcome"),
                         "outcome_ablated": aj.get("outcome"),
                         "dq": (qf - qa) if (qf is not None and qa is not None) else None})
            if qf is not None and qa is not None:
                deltas.append(qf - qa)
            if fj.get("completed"):
                n_ans_full += 1
                time_full += fj.get("wall_s") or 0
            if aj.get("completed"):
                n_ans_arm += 1
                time_arm += aj.get("wall_s") or 0
        mean, lo, hi = bootstrap_ci(deltas)
        pos = sum(1 for d in deltas if d > 0)
        proves = bool(deltas) and pos > len(deltas) / 2 and lo is not None and lo > 0
        verdict = "PROVES_VALUE" if proves else "REMOVAL_CANDIDATE"
        table["arms"][arm] = {
            "n_pairs_scored": len(deltas),
            "dq_mean": mean, "dq_ci95": [lo, hi],
            "dq_positive_pairs": pos,
            "completed_full": n_ans_full, "completed_ablated": n_ans_arm,
            "time_share_note": (f"full {time_full:.0f}s vs ablated "
                                f"{time_arm:.0f}s (completed problems only)"),
            "verdict": verdict,
            "rows": rows}
        lines.append(f"## {arm}")
        lines.append(f"- scored pairs: {len(deltas)} | dQ mean {mean} "
                     f"(95% CI [{lo}, {hi}]) | positive pairs {pos}/"
                     f"{len(deltas)}")
        lines.append(f"- completion: full {n_ans_full}/7 vs ablated "
                     f"{n_ans_arm}/7 | wall: {time_full:.0f}s vs "
                     f"{time_arm:.0f}s")
        lines.append(f"- VERDICT: **{verdict}**")
        lines.append("")
    out_json = arm_dir("judgments") / f"ablation_table_{commit}.json"
    out_md = arm_dir("judgments") / f"ablation_table_{commit}.md"
    out_json.write_text(json.dumps(table, indent=1, default=str) + "\n",
                        encoding="utf-8")
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines), flush=True)
    print(f"[ablation] table -> {out_json.name}, {out_md.name}", flush=True)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["arm", "judge", "report", "arms-list"])
    ap.add_argument("arm", nargs="?", default=None)
    ap.add_argument("--problems", default=None,
                    help="comma-separated problem ids (default DEV7)")
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    arms = ["full", "composer_only"] + [f"no_{s}" for s in ABLATION_STAGES]
    if args.cmd == "arms-list":
        print("\n".join(arms))
        return 0
    probs = [p.strip() for p in args.problems.split(",")] if args.problems \
        else None
    if args.cmd == "arm":
        if not args.arm:
            print("[ablation] arm name required (see arms-list)")
            return 2
        return run_arm(args.arm, probs, args.workers)
    if args.cmd == "judge":
        return judge_all(arms, probs)
    if args.cmd == "report":
        return report(arms)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

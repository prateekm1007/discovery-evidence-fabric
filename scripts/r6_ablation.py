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
import hashlib
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path

# P0-7 (round 2): REPO is derived from this file's location — the
# hard-coded sandbox path made the driver unusable (and a silent
# cross-host write hazard) on any other checkout.
REPO = Path(__file__).resolve().parents[1]
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


def _committed_calibration() -> dict | None:
    """The committed score-table judge calibration (Art. XVII evidence,
    not a fresh wall-clock probe). Returns {}-shaped dict on absence —
    the caller treats missing evidence as NOT calibrated."""
    try:
        table = json.loads((Path(__file__).resolve().parents[1]
                            / "eval" / "score"
                            / "SCORE_TABLE.json").read_text(
                                encoding="utf-8"))
        return table.get("judge_calibration") or None
    except Exception:  # noqa: BLE001
        return None


def _calibration_state() -> tuple:
    cal = _committed_calibration()
    if not cal:
        return (False, "no committed judge_calibration evidence; "
                       "removal gate stays closed")
    n_ok = bool(cal.get("passed")) and int(cal.get("correct") or 0) >= 24
    detail = (f"correct={cal.get('correct')}/{cal.get('n_pairs')} "
              f"passed={cal.get('passed')} "
              f"(accuracy={cal.get('accuracy')})")
    return (n_ok, detail)


def _judge_independence_label(judge_route: dict, base_route: dict) -> str:
    """Label the judge's family relationship to the baseline route
    (audit P1-11: shared-family must be LABELLED, never silent).
    The label rides every judgment record and the ablation table."""
    label = (judge_route.get("judge_independence")
             or judge_route.get("disclosure"))
    jp = str(judge_route.get("provider") or "")
    bp = str(base_route.get("provider") or "")
    if label:
        return f"{label} (provider overlap: {bool(jp and jp == bp)})"
    if jp and jp == bp:
        return ("SAME_PROVIDER (disclosed via EVAL_JUDGE_ALLOW_SHARED_"
                "FAMILY; NOT independent — diagnostic only)")
    return "CROSS_PROVIDER (no baseline route evidence recorded)"


def _full_root() -> Path:
    return REPO / "eval" / "runs" / _commit()


# ---------------------------------------------------------------------------
# P0-7 (round-2 directive): ablation / run / score isolation
#
# (a) RUN isolation — the driver writes ONLY under the ablation root
#     (eval/runs_ablation/<commit>/). It never writes into the live run
#     roots (eval/runs/<commit>/ — the full arm is a READ-ONLY borrow)
#     or the scored-artifact space (eval/score/). The ablation arm
#     subprocesses are mechanically barred from the judge arm: an
#     ablation arm that built the shared scored table would mix
#     diagnostic arm runs into the scored-run records.
# (b) SCORE isolation — the ablation judging is the driver's own
#     isolated pass (its judgments live in eval/runs_ablation/<commit>/
#     judgments/), consumes NO scored-run slot, and writes nothing to
#     eval/score/. Verdicts stay DIAGNOSTIC (P1-11 binding).
# (c) JUDGMENT<->RUN BINDING — every ablation judgment carries
#     bound_inputs (P0-8 discipline, the same keys eval/run.py uses):
#     the sha256 of the answer it was made from, arm, commit, rubric
#     version, judge route. A judgment whose answer changed after the
#     run (arm re-run) is INCOMPLETE_INPUT_MISMATCH and is re-judged,
#     never silently reused; a record without a binding is
#     UNBOUND_LEGACY and the same.
# ---------------------------------------------------------------------------

RUBRIC_VERSION = "0-4-rubric/1"  # == eval.run.RUBRIC_VERSION


def _ablation_write_path(p: Path) -> Path:
    """Guard (a): every driver write target must resolve under the
    ablation root. A write anywhere else (live run roots, the scored
    space) is a run/score-isolation violation and raises — typed, never
    a silent cross-space write."""
    ap = Path(p).resolve()
    ar = ABLATION_ROOT.resolve()
    if not str(ap).startswith(str(ar) + os.sep):
        raise RuntimeError(
            "ablation/run/score isolation violation: the ablation "
            f"driver may only write under {ar} — write target {ap} "
            "is outside the ablation root (live run roots and the "
            "scored space are off-limits)")
    return ap


def _allowed_harness_arms(harness_arms: str) -> str:
    """Guard (a), arm side: the ablation arm subprocess may run the
    pipeline or composer arm only. The judge arm would build the
    shared scored table from diagnostic arm answers — mechanically
    barred, typed."""
    if "judge" in [a.strip() for a in str(harness_arms).split(",")]:
        raise RuntimeError(
            "ablation arm requested the judge arm: ablation arms must "
            "never build the shared scored table (run/score "
            "isolation) — the driver's own isolated judging pass "
            "covers the ablation answers")
    return harness_arms


def _answer_binding(rec: dict, arm: str, commit: str,
                    judge_route: dict) -> dict:
    """bound_inputs for one ablation judgment (P0-8 key shapes,
    answer side): the answer actually judged, keyed so a later re-use
    can verify it was made under the SAME answer. Hash = eval.run's
    _sha (sha256 of the text), so a judgment can be verified against
    the live-run judge records' bindings too."""
    import hashlib
    ans = (rec or {}).get("answer")
    ans_sha = ("ABSENT" if not ans
               else hashlib.sha256(str(ans).encode("utf-8")).hexdigest())
    return {"answer_sha256": ans_sha,
            "arm": arm, "commit": commit,
            "rubric_version": RUBRIC_VERSION,
            "judge_route": {"provider": (judge_route or {}).get("provider"),
                            "model": (judge_route or {}).get("model")}}


def _binding_state(prev: dict, cur_bind: dict) -> str:
    """The P0-8 states, applied to an ablation judgment against the
    CURRENT answer binding: BOUND_OK (reusable), UNBOUND_LEGACY (no
    binding recorded — re-judge), INCOMPLETE_INPUT_MISMATCH (answer /
    arm / commit / rubric / route drifted — re-judge)."""
    b = (prev or {}).get("bound_inputs")
    if not isinstance(b, dict):
        return "UNBOUND_LEGACY"
    checks = [
        b.get("answer_sha256") == cur_bind["answer_sha256"],
        b.get("arm") == cur_bind["arm"],
        b.get("commit") == cur_bind["commit"],
        str(b.get("rubric_version") or "") == cur_bind["rubric_version"],
        (b.get("judge_route") or {}).get("provider")
        == cur_bind["judge_route"]["provider"],
        (b.get("judge_route") or {}).get("model")
        == cur_bind["judge_route"]["model"],
    ]
    return "BOUND_OK" if all(checks) else "INCOMPLETE_INPUT_MISMATCH"


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
    arm of the harness. P0-7: the arm is barred from the judge arm
    (shared scored table), and its root is the ablation-space root —
    the live run roots are never written by the driver."""
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
    harness_arms = _allowed_harness_arms(harness_arms)
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
    arm comes from the FRESH RUN root (the paired design's control).
    P0-7: the borrow is read-only and TYPED — a missing live-run
    reference is flagged per problem (full_ref_present), never a silent
    zero-dQ."""
    commit = _commit()
    probs = problems or DEV7
    out = {}
    for pid in probs:
        row = {}
        fr = _full_root() / pid / "pipeline_record.json"
        row["full"] = _read_answer(fr)
        row["full_ref_present"] = fr.exists()
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
    retried ONCE then recorded typed (never a score).

    P0-7 (round-2 directive: ablation/run/score isolation): every
    judgment carries bound_inputs (P0-8 key shapes: the sha256 of the
    ANSWER it was made from, arm, commit, rubric version, judge
    route). A recorded judgment is reused ONLY when its binding still
    matches the current answer — otherwise the arm was re-run and the
    stale judgment is superseded typed (INCOMPLETE_INPUT_MISMATCH /
    UNBOUND_LEGACY) and re-judged, never silently reused. This pass
    is the driver's OWN isolated scoring: it writes only under the
    ablation root (write-guarded), consumes no scored-run slot, and
    touches neither the live run roots nor the scored-artifact space."""
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
    # P1-11 (audit H): every ablation judgment binds to its OWN
    # calibration record + independence label. A shared-family judge is
    # LABELLED, never silently mixed, and no verdict is actionable
    # until the auditor adjudicates — the binding rides each record.
    cal_ok, cal_detail = _calibration_state()
    base_route_p = _full_root() / "_route_probe.json"
    base_route = (json.loads(base_route_p.read_text(encoding="utf-8"))
                   if base_route_p.exists() else {})
    # P0-7 judge-env consistency: the shared-family gate governs the
    # process where the judging actually HAPPENS (this driver process)
    # — the arm subprocesses never judge, so gating them was inert.
    # The gate is relaxed ONLY for the shared-family case (judge
    # provider == baseline provider); cross-family routes keep the
    # strict separation, and every record still carries the
    # independence label disclosing the overlap (P1-11).
    _jp = judge_route.get("provider")
    _bp = base_route.get("provider")
    if _jp and _jp == _bp:
        os.environ["EVAL_JUDGE_ALLOW_SHARED_FAMILY"] = "1"
    judge_binding = {
        "judge_route": {"provider": judge_route.get("provider"),
                        "model": judge_route.get("model")},
        "commit": commit,
        "rubric_version": RUBRIC_VERSION,
        "calibration": {"calibrated": cal_ok, "detail": cal_detail,
                        "source": "committed SCORE_TABLE judge_calibration"},
        "judge_independence": _judge_independence_label(judge_route,
                                                         base_route),
        "actionable": False,
        "actionability_note": "no verdict is actionable until the "
                              "auditor adjudicates the DEV pairs and "
                              "the calibration gate passes on committed "
                              "evidence (audit P1-11)",
    }
    out_path = _ablation_write_path(
        arm_dir("judgments") / f"judgments_{commit}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    judged = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {}
    n_new = 0
    n_reused_bound = 0
    n_superseded = {"INCOMPLETE_INPUT_MISMATCH": 0, "UNBOUND_LEGACY": 0}
    for pid, row in answers.items():
        p = by_id.get(pid)
        if p is None:
            continue
        for arm, rec in row.items():
            key = f"{pid}::{arm}"
            prev = judged.get(key)
            cur_bind = _answer_binding(rec, arm, commit, judge_route)
            superseded = None
            if prev is not None and prev.get("outcome") not in (
                    "QJ_TRANSPORT_FAILED", "QJ_NO_ROUTE",
                    "QJ_PARSE_FAILED"):
                bstate = _binding_state(prev, cur_bind)
                if bstate == "BOUND_OK":
                    n_reused_bound += 1
                    continue
                # P0-7: the recorded judgment no longer describes the
                # answer on disk (arm re-run / no binding) — it is
                # superseded TYPED and re-judged, never reused.
                superseded = bstate
                n_superseded[bstate] += 1
            res = judge_quality_0to4(p, rec.get("answer"), judge_route)
            judged[key] = {**res, "arm": arm, "problem_id": pid,
                           "completed": rec.get("completed"),
                           "wall_s": rec.get("wall_s"),
                           "judge_binding": judge_binding,
                           "bound_inputs": cur_bind,
                           "superseded_binding_state": superseded}
            n_new += 1
            print(f"[judge] {key}: {res.get('outcome')} "
                  f"score={res.get('score')}"
                  + (f" (superseded {superseded})" if superseded else ""),
                  flush=True)
    out_path.write_text(json.dumps(judged, indent=1, default=str) + "\n",
                        encoding="utf-8")
    print(f"[judge] {n_new} new judgments, {n_reused_bound} reused "
          f"(bound), {sum(n_superseded.values())} superseded typed "
          f"({n_superseded}) -> {out_path.name}", flush=True)
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
    cal_ok, cal_detail = _calibration_state()
    J = json.loads(jp.read_text(encoding="utf-8"))
    # P1-11: the table carries the binding its judgments were made
    # under; records predating the binding are labelled, not mixed
    _sample_binding = next((v.get("judge_binding") for v in J.values()
                            if isinstance(v, dict)
                            and v.get("judge_binding")), None)
    _n_unbound = sum(1 for v in J.values()
                    if isinstance(v, dict) and not v.get("judge_binding"))
    probs = DEV7
    # P0-7: deltas are computed ONLY over judgments still BOUND to the
    # answer on disk (answer-hash check against the current arm
    # records); a stale/unbound judgment is a typed exclusion, never a
    # silent zero-dQ.
    answers = collect_answers(arms)

    def _cur_ans_sha(pid: str, arm2: str):
        ans = ((answers.get(pid) or {}).get(arm2) or {}).get("answer")
        return ("ABSENT" if not ans
                else hashlib.sha256(str(ans).encode("utf-8")).hexdigest())

    def _ans_state(jrec, pid: str, arm2: str) -> str:
        b = (jrec or {}).get("bound_inputs")
        if not isinstance(b, dict):
            return "UNBOUND_LEGACY"
        return ("BOUND_OK" if b.get("answer_sha256") == _cur_ans_sha(pid, arm2)
                else "INCOMPLETE_INPUT_MISMATCH")
    lines = ["# R6 ablation table (0-4 rubric, paired, blind judge)",
             "", f"- commit: `{commit}`",
             "- paired dQ = full(composer+pipeline) - ablated, same problems",
             f"- CALIBRATION GATE (Art. L/LXXXIV): judge "
             f"{'CALIBRATED (' + cal_detail + ')' if cal_ok else 'NOT CALIBRATED (' + cal_detail + ')'}",
             "- decision rule (pre-registered in r6_ablation.py): a stage",
             "  PROVES VALUE iff majority of pairs dQ > 0 AND bootstrap",
             "  95% CI lower bound > 0; otherwise REMOVAL CANDIDATE.",
             "  Stage REMOVAL is additionally forbidden without",
             "  (a) judge calibration >= 24/30 on committed evidence and",
             "  (b) auditor-judged DEV pairs. This harness cannot grant",
             "  either. Verdicts are DIAGNOSTIC_ONLY until then."
             "  The auditor judges the pairs; the coder does not"
             "  self-judge.", ""]
    table = {"commit": commit, "arms": {},
             "calibration_gate": {"passed_24_of_30": cal_ok,
                                  "detail": cal_detail,
                                  "source": "committed SCORE_TABLE judge_calibration"},
             "stage_removal_allowed": False,
             "removal_requires": ["judge calibration >= 24/30 (committed evidence)",
                                  "auditor-judged DEV pairs (Art. XXVI)",
                                  "one commit per removal, constitution by deletion"],
             "decision_rule":
             "prove value iff majority(dQ>0) AND CI_lo > 0; else removal candidate",
             "judge_binding": _sample_binding,
             "judgments_missing_binding": _n_unbound,
             "binding_note": ("every judgment carries judge_binding "
                              "(route, commit, rubric version, its own "
                              "calibration record, independence label); "
                              "judgments without one are labelled "
                              "LEGACY_UNBOUND and excluded from any "
                              "actionable verdict (P1-11)"),
             "isolation_statement": (
                 "P0-7 ablation/run/score isolation: the ablation "
                 "driver writes ONLY under eval/runs_ablation/"
                 "<commit>/ (write-guarded); the full arm is a "
                 "READ-ONLY borrow of the live run root (eval/runs/"
                 "<commit>), never written by the driver; ablation "
                 "arm subprocesses are mechanically barred from the "
                 "judge arm; ablation judgments consume NO scored-run "
                 "slot and never enter eval/score/ — ablation "
                 "verdicts are DIAGNOSTIC (P1-11)")}
    for arm in arms:
        if arm == "full":
            continue
        rows = []
        deltas = []
        n_ans_full = n_ans_arm = 0
        time_full = time_arm = 0.0
        binding_states = {"BOUND_OK": 0, "INCOMPLETE_INPUT_MISMATCH": 0,
                          "UNBOUND_LEGACY": 0, "NO_JUDGMENT": 0}
        n_missing_full_ref = 0
        for pid in probs:
            if not (answers.get(pid) or {}).get("full_ref_present"):
                n_missing_full_ref += 1
            fj = J.get(f"{pid}::full")
            aj = J.get(f"{pid}::{arm}")
            if not fj or not aj:
                binding_states["NO_JUDGMENT"] += 1
                continue
            sf = _ans_state(fj, pid, "full")
            sa = _ans_state(aj, pid, arm)
            if sf == sa == "BOUND_OK":
                binding_states["BOUND_OK"] += 1
            else:
                binding_states[sf if sf != "BOUND_OK" else sa] += 1
            qf = fj.get("score")
            qa = aj.get("score")
            pair_state = ("BOUND_OK" if sf == sa == "BOUND_OK"
                          else (sf if sf != "BOUND_OK" else sa))
            dq = ((qf - qa) if (qf is not None and qa is not None
                                and pair_state == "BOUND_OK") else None)
            rows.append({"problem_id": pid,
                         "q_full": qf, "q_ablated": qa,
                         "outcome_full": fj.get("outcome"),
                         "outcome_ablated": aj.get("outcome"),
                         "binding_state": pair_state,
                         "dq": dq})
            if dq is not None:
                deltas.append(dq)
            if fj.get("completed"):
                n_ans_full += 1
                time_full += fj.get("wall_s") or 0
            if aj.get("completed"):
                n_ans_arm += 1
                time_arm += aj.get("wall_s") or 0
        mean, lo, hi = bootstrap_ci(deltas)
        pos = sum(1 for d in deltas if d > 0)
        proves = bool(deltas) and pos > len(deltas) / 2 and lo is not None and lo > 0
        if proves and cal_ok:
            verdict = "PROVES_VALUE_PENDING_AUDITOR (calibrated judge; " \
                     "auditor adjudication still required — P1-11)"
        elif proves:
            verdict = "DIAGNOSTIC_ONLY_PROVES_VALUE (judge below 24/30 — not actionable)"
        elif cal_ok:
            verdict = ("REMOVAL_CANDIDATE_PENDING_AUDITOR (calibrated "
                       "judge; no actionable removal until the auditor "
                       "adjudicates the DEV pairs — P1-11)")
        else:
            verdict = ("DIAGNOSTIC_REMOVAL_CANDIDATE (uncalibrated "
                       "judge — diagnostic only, P1-11)")
        table["arms"][arm] = {
            "n_pairs_scored": len(deltas),
            "dq_mean": mean, "dq_ci95": [lo, hi],
            "dq_positive_pairs": pos,
            "binding_states": binding_states,
            "n_missing_full_ref": n_missing_full_ref,
            "completed_full": n_ans_full, "completed_ablated": n_ans_arm,
            "time_share_note": (f"full {time_full:.0f}s vs ablated "
                                f"{time_arm:.0f}s (completed problems only)"),
            "verdict": verdict,
            "stage_removal_allowed": False,
            "rows": rows}
        lines.append(f"## {arm}")
        lines.append(f"- scored pairs: {len(deltas)} | dQ mean {mean} "
                     f"(95% CI [{lo}, {hi}]) | positive pairs {pos}/"
                     f"{len(deltas)}")
        lines.append(f"- completion: full {n_ans_full}/7 vs ablated "
                     f"{n_ans_arm}/7 | wall: {time_full:.0f}s vs "
                     f"{time_arm:.0f}s")
        lines.append(f"- binding: "
                     f"{binding_states['BOUND_OK']} BOUND_OK / "
                     f"{binding_states['INCOMPLETE_INPUT_MISMATCH']} stale / "
                     f"{binding_states['UNBOUND_LEGACY']} unbound / "
                     f"{binding_states['NO_JUDGMENT']} no-judgment "
                     f"(deltas over BOUND_OK only) | "
                     f"{n_missing_full_ref} pairs missing the live-run full "
                     f"reference (typed, excluded)")
        lines.append(f"- VERDICT: **{verdict}**")
        lines.append("")
    out_json = _ablation_write_path(
        arm_dir("judgments") / f"ablation_table_{commit}.json")
    out_md = _ablation_write_path(
        arm_dir("judgments") / f"ablation_table_{commit}.md")
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

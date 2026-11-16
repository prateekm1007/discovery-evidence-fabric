#!/usr/bin/env python3
"""r36_deepseek_rung_gold_calibration.py — the R-JUDGE auditor act (claim c-0043).

A fresh calibration of the RETIRED crowllm/deepseek-v4-flash:free judge
rung under the UNCHANGED v3 axis suffix, on the auditor's 10-specimen gold
corpus (audit/gold_set/AUDITOR_GOLD_SET_v1.json: 4 GOOD / 6 BAD, each with
an `expect` criterion). >=0.8 accuracy makes the rung an ELIGIBLE judge
rung (c-0026 may run on it); below 0.8 it STAYS RETIRED.

DISCIPLINE:
  - Gold bytes ride `git show` from the audit branch / source commits —
    never copied into the queue tree.
  - The v3 axis suffix (the scoring contract) is byte-identical to the
    pre-registered calibration (imported from r29_judge_calibration).
  - The canonical c-0026 judge route (crowllm/qwen-3.8-max:free) is NOT
    touched: this measures exactly the rung the auditor granted.
  - a1 answers judged at position A; the real baseline at B where the
    specimen record carries one; G03 has no baseline -> typed
    single-answer mode (B is a placeholder; only A-side axes are consumed).
  - Criteria are parsed mechanically from the `expect` strings:
    BAD feasibility-class: F_A <= 1 (or an infeasible/invalid read);
    BAD constraint-class:  C_A <= 1 (or an invalid read);
    GOOD: survive (no infeasible/invalid read) + the numeric floors in
    `expect` (feasibility/testability thresholds when stated).
  - K=1 per specimen (the gate is the gold agreement rate, not variance);
    one typed retry per failed call; failures never cached (Art. 26).
  - Zero generator calls.

Usage: python3 scripts/r36_deepseek_rung_calibration.py [probe|run]
"""
import json, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import r29_judge_calibration as cal  # unchanged pre-registered instrument (V3_SUFFIX)

AUDIT_REF = "origin/audit/r11-auditor-verdict-20261114"
GOLD_REF = f"{AUDIT_REF}:audit/gold_set/AUDITOR_GOLD_SET_v1.json"
RUNG = ("crowllm", "deepseek-v4-flash:free")
OUT = REPO / "eval" / "deepseek_rung_gold_calibration_r36.json"
RUN_LOG = REPO / "ENGINE_RUNS" / "r36_deepseek_rung_gold_calibration.log"
MAX_TOKENS = cal.MAX_TOKENS


def _now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _log(msg):
    line = f"[{_now()}] {msg}"
    print(line, flush=True)
    RUN_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(RUN_LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def _git_show(ref):
    out = subprocess.run(["git", "-C", str(REPO), "show", ref],
                         capture_output=True, text=True, check=True)
    return out.stdout


def _criterion(spec):
    """Mechanically parse the gold `expect` string into a check fn."""
    expect = spec["expect"].lower()
    is_bad = spec["label"] == "BAD"
    if "constraint_compliance <=1" in expect or "invalid flag" in expect:
        axis, floor = "C_A", 1
        mode = "constraint"
    elif "testability >=4" in expect:
        axis, floor = "T_A", 4
        mode = "good_floor"
    elif "testability >=3" in expect:
        axis, floor = "T_A", 3
        mode = "good_floor"
    elif "feasibility >=3" in expect:
        axis, floor = "F_A", 3
        mode = "good_floor"
    else:  # BAD feasibility-class
        axis, floor = "F_A", 1
        mode = "feasibility"
    def check(axes, flagged):
        a = axes.get(axis)
        if a is None:
            return False
        if mode in ("feasibility", "constraint"):
            return a <= floor or flagged
        return (not flagged) and a >= floor
    return mode, axis, floor, check


def _specimen_prompt(spec, rec, problem_q, baseline):
    a1 = str(rec.get("a1_answer") or "")
    if baseline:
        b_txt = ("ANSWER B (baseline practice):\n" + str(baseline))
    else:
        b_txt = ("ANSWER B: NO SECOND ANSWER PROVIDED (single-answer "
                 "specimen; only the A-side axes are consumed).")
    header = (
        "You are a strict, independent engineering evaluator. You are given "
        "one problem and two candidate answers (A and B). Judge BOTH answers "
        "on the axis contract below, then apply the contract's flags. "
        "English only. The problem and answers are frozen bytes.\n\n"
        f"PROBLEM:\n{problem_q}\n\n"
        f"ANSWER A (candidate under judgment):\n{a1}\n\n"
        f"{b_txt}\n\n")
    return header + cal.V3_SUFFIX


def probe():
    time.sleep(25.0)  # crowllm free tier: 10 req/60s (failed included); _judge_judgment_call makes 2-3 HTTP calls internally — 25s keeps the whole ladder under the ceiling
    r = cal._transport_call(RUNG[0], RUNG[1], "Reply with exactly: OK",
                            "You are a servability probe. English only.",
                            max_tokens=20)
    ok = r.get("status") == "OK" and str(r.get("content") or "").strip()
    _log(f"[probe] rung {RUNG[0]}/{RUNG[1]} tiny -> {r.get('status')} "
         f"chars={len(str(r.get('content') or ''))}")
    time.sleep(25.0)
    jc = cal._judge_judgment_call(RUNG[0], RUNG[1], cal.PROBE_RUBRIC,
                                  max_tokens=MAX_TOKENS)
    _log(f"[probe] verdict-shaped outcome={jc.get('outcome')} valid={bool(jc.get('valid'))}")
    print(json.dumps({"probe": "PASS" if (ok and jc.get("valid")) else "FAIL",
                      "tiny_status": r.get("status"),
                      "verdict_outcome": jc.get("outcome")}))
    return 0 if (ok and jc.get("valid")) else 1


def run():
    gold = json.loads(_git_show(GOLD_REF))
    assert gold["n"] == 10 and len(gold["specimens"]) == 10
    results = []
    n_correct = 0
    n_calls = 0
    for spec in gold["specimens"]:
        sid = spec["id"]
        rec = json.loads(_git_show(f"{spec['source_commit']}:{spec['path']}"))
        pid = rec.get("problem_id")
        pf = REPO / "eval" / "pairs" / "dev12_fresh" / f"{pid}.json"
        problem_q, baseline = "", None
        if pf.exists():
            p = json.loads(pf.read_text(encoding="utf-8"))
            problem_q = str(p.get("question") or "")
            baseline = p.get("baseline_answer")
        mode, axis, floor, check = _criterion(spec)
        prompt = _specimen_prompt(spec, rec, problem_q, baseline)
        jc = None
        outcome = None
        attempts = []
        for try_n in range(2):  # one typed retry; failures never cached
            time.sleep(25.0)  # pace under the crowllm 10 req/60s ceiling (2-3 HTTP calls per judgment call)
            if try_n:
                time.sleep(45.0)
            jc = cal._judge_judgment_call(RUNG[0], RUNG[1], prompt,
                                          max_tokens=MAX_TOKENS)
            n_calls += 1
            outcome = jc.get("outcome")
            attempts.append({"n": try_n + 1, "outcome": outcome})
            if outcome == "JUDGE_VALID":
                break
        axes = cal.parse_axes(jc) if outcome == "JUDGE_VALID" else {}
        flagged = bool(axes.get("A1") is not None and (axes.get("A1") == 0))
        # 'flagged' heuristic: some verdicts carry explicit invalid/infeasible
        # markers as A1==0; the numeric floor check below is primary.
        correct = check(axes, flagged) if outcome == "JUDGE_VALID" else False
        if correct:
            n_correct += 1
        results.append({
            "id": sid, "label": spec["label"], "defect_class": spec["defect_class"],
            "problem_id": pid, "mode": mode, "axis": axis, "floor": floor,
            "outcome": outcome, "axes": axes,
            f"{axis}_read": axes.get(axis),
            "criterion_met": correct,
            "why": spec.get("why", "")[:160],
            "transport_attempts": attempts,
            "single_answer_mode": baseline is None})
        _log(f"[run] {sid} {spec['label']:<4} {mode}/{axis}<= or >= floor {floor} "
             f"read={axes.get(axis)} outcome={outcome} "
             f"{'PASS' if correct else 'MISS'}")
    accuracy = n_correct / 10.0
    eligible = accuracy >= 0.8
    rec = {
        "record": "DEEPSEEK_RUNG_GOLD_CALIBRATION_R36/1.0.0",
        "at": _now(),
        "typed": ("R-JUDGE auditor act: recalibration of the RETIRED "
                  "crowllm/deepseek-v4-flash:free judge rung on the gold "
                  "corpus under the UNCHANGED v3 axis suffix"),
        "claim": {"claim_id": "c-0043",
                  "work_id": "r36-deepseek-rung-gold-calibration",
                  "session": "builder-r35s1", "base_sha": "8cd31d0d7"},
        "rung": {"provider": RUNG[0], "model": RUNG[1],
                 "previous_calibration": 0.667, "status_before": "RETIRED"},
        "gold_corpus": {"provenance": f"audit branch {GOLD_REF}",
                        "n": 10, "n_good": gold["n_good"], "n_bad": gold["n_bad"]},
        "axis_contract": "v3 suffix byte-identical (imported from the pre-registered r29 harness)",
        "results": results,
        "accuracy": accuracy,
        "eligibility": {"bar": 0.8, "met": eligible,
                        "disposition": ("deepseek-v4-flash:free is an ELIGIBLE judge rung — c-0026 MAY run on it (auditor act consumed)"
                                        if eligible else
                                        "deepseek-v4-flash:free STAYS RETIRED (below the 0.8 bar); the canonical c-0026 judge remains crowllm/qwen-3.8-max:free")},
        "quota": {"judge_calls": n_calls, "pacing_s": 25.0,
                  "ceiling_note": "crowllm free tier 10 req/60s (failed included); each judgment call is 2-3 HTTP calls internally — 25s pacing typed after the first pass starved on 429s (that 0/10 pass is a rate-limit artifact, not a scoring result)",
                  "note": "K=1 per specimen + one typed retry; failures never cached (Art. 26)"},
        "generation": {"calls": 0, "note": "zero generator calls — gold bytes only"},
        "limitations": ("the wrapper around the v3 suffix is a specimen-composed "
                        "header (the gold corpus does not ride the packet's "
                        "rubric_prompt); the axis CONTRACT is byte-identical; "
                        "G03 runs in typed single-answer mode"),
        "art_27": "NO CAPABILITY CHANGE (rung eligibility measurement only)"}
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    _log(f"[run] COMPLETE: {n_correct}/10 correct -> accuracy {accuracy:.2f} "
         f"-> {'ELIGIBLE' if eligible else 'STAYS RETIRED'}")
    print(json.dumps({"n_correct": n_correct, "accuracy": accuracy,
                      "eligible": eligible}))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "probe"
    {"probe": probe, "run": run}[cmd]()

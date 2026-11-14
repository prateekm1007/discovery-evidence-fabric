#!/usr/bin/env python3
"""r11_triples.py — OWNER ROUND R11 (2026-11-14, item 2): the
INVENTION-RUBRIC TRIPLES.

For every DEV12 problem the COMPLETE TRIPLE (baseline / A0+ / full
pipeline) is committed to eval/triples/r11/ for the AUDITOR'S BLIND
JUDGING, and every arm is scored on the invention rubric
(novelty vs the standard solution / feasibility / testability /
constraint compliance, 0-4 each) into eval/invention_rubric_r11.json.

Correctness scoring stays the correctness-rubric judge's job — this
record never feeds the correctness gate (the owner: 'Correctness
scoring stays separate').

Arm sources (committed bytes only — never session memory):
  baseline  eval/pairs/dev12_fresh/<pid>.json baseline_answer
            (fu-004/sofc carry empty baselines in the committed pairs
            — TYPED_SKIP_BASELINE_ABSENT, the compared object does
            not exist, Art. XXV)
  a0plus    eval/pairs/r11_a0plus/<pid>.json a0plus_answer (the
            3.1.0 default-path delivery; typed state rides)
  full      eval/pairs/dev12_fresh/<pid>.json pipeline_answer
            (CONTRACT-INVALID committed markers are typed, not
            answers)
  a1        eval/pairs/r11_a1/<pid>.json (when present — the
            invention arm rides the same rubric record)

Serves: Arts. LXXVII (the deliverable is judged as an invention),
XXVI (coder scores disclosed with rationale, never self-certified
as the gate — the auditor's blind judging is authoritative), XXV
(typed skips stay typed), XLIX (artifacts carry their commit).
"""
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.invention_rubric import (  # noqa: E402
    score_triple, INVENTION_RUBRIC_VERSION)

DEV12 = REPO / "eval" / "problems_dev12.json"
PAIRS_FRESH = REPO / "eval" / "pairs" / "dev12_fresh"
PAIRS_A0 = REPO / "eval" / "pairs" / "r11_a0plus"
PAIRS_A1 = REPO / "eval" / "pairs" / "r11_a1"
TRIPLES = REPO / "eval" / "triples" / "r11"


def _sha(s: str) -> str:
    return hashlib.sha256(str(s or "").encode("utf-8")).hexdigest()


def _dev12_problems() -> list:
    d = json.loads(DEV12.read_text(encoding="utf-8"))
    plist = d if isinstance(d, list) else d.get("problems", [])
    return sorted(plist, key=lambda p: str(p.get("problem_id")
                                           or p.get("id")))


def _load(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — typed, never silent
        return None


def main() -> int:
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO),
                            capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(
        ["git", "status", "--porcelain"], cwd=str(REPO),
        capture_output=True, text=True).stdout.strip())
    TRIPLES.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    problems = _dev12_problems()
    all_scores: dict = {
        "record": "invention_rubric_r11/1.0.0",
        "rubric_version": INVENTION_RUBRIC_VERSION,
        "commit": commit,
        "dirty_tree": dirty,
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "scorer_disclosure": (
            "coder-deterministic scores WITH rationale (the "
            "invention-rubric module's byte-level anchors) — an INPUT "
            "to the auditor's blind judging, never the gate "
            "(Art. XXVI); correctness scoring is the correctness "
            "judge's separate instrument"),
        "problems": {}}
    n_triples = 0
    for prob in problems:
        pid = str(prob.get("problem_id") or prob.get("id"))
        fresh = _load(PAIRS_FRESH / f"{pid}.json") or {}
        a0 = _load(PAIRS_A0 / f"{pid}.json") or {}
        a1 = _load(PAIRS_A1 / f"{pid}.json") or {}

        base_ans = str(fresh.get("baseline_answer") or "")
        base_state = ("BASELINE" if base_ans.strip()
                      else "TYPED_SKIP_BASELINE_ABSENT")
        full_ans = str(fresh.get("pipeline_answer") or "")
        full_state = "NOT_SCORED"
        if not full_ans.strip():
            full_state = "TYPED_SKIP_NO_FULL_BYTES"
        elif full_ans.startswith("CONTRACT-INVALID"):
            full_state = "CONTRACT_INVALID_MARKER"

        a0_ans = str(a0.get("a0plus_answer") or "")
        a0_state = str(a0.get("result") or "NOT_RUN")
        a1_ans = str((a1.get("a1_answer")
                      or a1.get("answer") or ""))
        a1_state = str(a1.get("result") or "NOT_RUN")

        triple = {
            "record": "invention_triple/1.0.0",
            "problem_id": pid,
            "commit": commit,
            "purpose": ("the complete arm set for this problem, "
                        "committed for the AUDITOR'S BLIND JUDGING "
                        "(owner R11 item 2); the arm identities are "
                        "declared here, the judging protocol "
                        "anonymizes sides per its own record"),
            "arms": {
                "baseline": {
                    "answer": base_ans,
                    "sha256": _sha(base_ans),
                    "typed_state": base_state,
                    "source": "eval/pairs/dev12_fresh (committed)"},
                "a0plus": {
                    "answer": a0_ans,
                    "sha256": _sha(a0_ans),
                    "typed_state": a0_state,
                    "source": "eval/pairs/r11_a0plus (committed; the "
                              "3.1.0 default-path delivery)"},
                "full_pipeline": {
                    "answer": full_ans,
                    "sha256": _sha(full_ans),
                    "typed_state": full_state,
                    "source": "eval/pairs/dev12_fresh (committed)"},
            },
        }
        if a1_ans.strip():
            triple["arms"]["a1"] = {
                "answer": a1_ans,
                "sha256": _sha(a1_ans),
                "typed_state": a1_state,
                "source": "eval/pairs/r11_a1 (committed; the "
                          "invention arm)"}
        (TRIPLES / f"{pid}.json").write_text(
            json.dumps(triple, indent=1, default=str) + "\n",
            encoding="utf-8")
        n_triples += 1

        arms = {"baseline": {"answer": base_ans,
                             "typed_state": base_state},
                "a0plus": {"answer": a0_ans,
                           "typed_state": a0_state},
                "full": {"answer": full_ans,
                         "typed_state": full_state}}
        if a1_ans.strip():
            arms["a1"] = {"answer": a1_ans,
                          "typed_state": a1_state}
        all_scores["problems"][pid] = score_triple(prob, arms)

    # the per-arm rubric means over the problems where the arm HAS
    # bytes (typed skips are excluded from the mean and their count
    # disclosed — never averaged as zero, Art. XXV)
    means: dict = {}
    for arm in ("baseline", "a0plus", "full", "a1"):
        per_axis: dict = {}
        n_scored = 0
        skips = 0
        for pid, rec in all_scores["problems"].items():
            arec = (rec.get("arms") or {}).get(arm) or {}
            if not arec.get("scores"):
                skips += 1
                continue
            n_scored += 1
            for ax, v in arec["scores"].items():
                per_axis.setdefault(ax, []).append(v)
        means[arm] = {
            "n_scored": n_scored, "n_typed_skips": skips,
            "mean": {ax: (round(sum(v) / len(v), 2)
                          if v else "NOT_MEASURED")
                     for ax, v in per_axis.items()}}
    all_scores["arm_means"] = means

    # the item-9 gate QUANTITIES (machine-measured inputs; the gate
    # itself is auditor-judged, owner R11 item 9): per problem the
    # novelty delta and feasibility gap of each arm vs the baseline
    gate_inputs: dict = {}
    for pid, rec in all_scores["problems"].items():
        b = (rec.get("arms") or {}).get("baseline") or {}
        bs = b.get("scores") or {}
        for arm in ("a0plus", "full", "a1"):
            arec = (rec.get("arms") or {}).get(arm) or {}
            ascs = arec.get("scores") or {}
            if not bs or not ascs:
                gate_inputs[f"{arm}:{pid}"] = "NOT_MEASURED"
                continue
            gate_inputs[f"{arm}:{pid}"] = {
                "novelty_delta": round(
                    ascs["novelty"] - bs.get("novelty", 0), 2),
                "feasibility_gap": round(
                    abs(ascs["feasibility"]
                        - bs.get("feasibility", 0)), 2)}
    _a1_deltas = [v["novelty_delta"] for k, v in gate_inputs.items()
                  if isinstance(v, dict) and k.startswith("a1:")]
    _a1_gaps = [v["feasibility_gap"] for k, v in gate_inputs.items()
                if isinstance(v, dict) and k.startswith("a1:")]
    all_scores["gate_inputs"] = gate_inputs
    all_scores["gate_inputs_summary"] = {
        "a1_novelty_delta_mean": (round(sum(_a1_deltas)
                                        / len(_a1_deltas), 2)
                                  if _a1_deltas else "NOT_MEASURED"),
        "a1_feasibility_gap_mean": (round(sum(_a1_gaps)
                                          / len(_a1_gaps), 2)
                                    if _a1_gaps else "NOT_MEASURED"),
        "a1_novelty_delta": (round(sum(_a1_deltas)
                                   / len(_a1_deltas), 2)
                             if _a1_deltas else "NOT_MEASURED"),
        "note": "machine-measured inputs to the item-9 holdout gate; "
                "the gate is AUDITOR-judged on >=10 pairs"}
    all_scores["n_triples"] = n_triples
    all_scores["wall_s"] = round(time.time() - t0, 1)
    OUT = REPO / "eval" / "invention_rubric_r11.json"
    OUT.write_text(json.dumps(all_scores, indent=1, default=str) + "\n",
                   encoding="utf-8")
    print(f"[r11trip] {n_triples} triples -> {TRIPLES}")
    for arm, m in means.items():
        print(f"[r11trip] {arm:10} n={m['n_scored']:2} "
              f"skips={m['n_typed_skips']} means={m['mean']}")
    print(f"[r11trip] scores -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

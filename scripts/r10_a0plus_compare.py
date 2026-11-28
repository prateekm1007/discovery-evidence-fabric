#!/usr/bin/env python3
"""r10_a0plus_compare.py — OWNER ROUND R10 (2026-11-13, P1 item 8): the
PAIRED BLIND COMPARISON re-run against the FINAL candidate snapshot,
with the simple arm's typed states DISCLOSED PER JUDGMENT.

R9 corrections carried forward and the R10 additions:
  * the calibration gate runs IN this script (probe_judge_route — the
    gate is re-earned per scoring pass);
  * the blind protocol: side order randomized per pair (sha256 parity,
    disclosed); the judge never learns the arm names;
  * the compared A0+ object is the arm's DELIVERED answer bytes — every
    measured arm's judgment carries its typed result
    (COMPLETE / INCOMPLETE_*) in the record. The typed state is
    metadata, not a verdict conversion (Art. X: labels describe the
    actual delivery); typed-INCOMPLETE arms ARE judged (the R10
    directive) and their count is disclosed per tally;
  * typed exclusions REPORTED, never silent: no-answer-byte arms (the
    fu-004/sofc typed skips; the bench-p05/new06 provenance-incomplete
    arms) and full-pipeline CONTRACT-INVALID markers;
  * the interpretation rule (owner R10): a winning tally over a
    PARTIAL valid set is NOT universal superiority, and the pruning
    decision stays blocked unless >= 10 valid A0+-vs-full judgments
    exist. The record carries the pruning_decision field typed.

Output: eval/a0plus_compare_r10.json (tracked, sanitized).

Serves: Arts. LXXVII, XLV, XLVII, LXXIX, XXV.
"""
import hashlib
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402

names = _load_key_vault()
print("[r10cmp] vault loaded (names only):", sorted(names))
os.environ.setdefault("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")
os.environ["ENGINE_LLM_TIMEOUT_S"] = "40"
os.environ["ENGINE_LLM_RETRY_SLEEP_S"] = "0"
# the per-problem healthy-call cap (12) is a PIPELINE-stage protection;
# this driver's workload is the 30-pair calibration + the comparison
# judgments — a different shape the cap was never scoped for (the R9
# measured finding). The override is disclosed and rides the record.
os.environ["FABRIC_PROBLEM_CALL_CAP"] = "80"

import subprocess  # noqa: E402
gw = subprocess.run(["bash", "scripts/zai_gateway_env.sh"], cwd=str(REPO),
                    capture_output=True, text=True, timeout=90)
if gw.returncode == 0:
    for line in (gw.stdout or "").splitlines():
        line = line.strip()
        if line.startswith("export ") and "=" in line:
            k, v = line[len("export "):].split("=", 1)
            os.environ[k] = v
    print("[r10cmp] zai gateway admitted")
else:
    print("[r10cmp] zai gateway unavailable (typed) — the judge probe "
          "runs against the remote cascade alone")

from eval.run import (probe_judge_route, _rubric_prompt, _parse_rubric,  # noqa: E402
                      _validate_rubric_pass, _transport_call,
                      _judge_judgment_call)

route = probe_judge_route("zai")
calib = route.get("calibration_full") or {}
if not route.get("provider") or not calib.get("passed"):
    print("[r10cmp] TYPED: no calibration-eligible judge this window — "
          "no comparison runs (Art. LXI)")
    sys.exit(3)
prov, model = route["provider"], route["model"]
print(f"[r10cmp] calibrated judge: {prov}/{model} "
      f"({calib.get('correct')}/{calib.get('n_pairs')}, "
      f"corpus {str(calib.get('corpus_sha256'))[:12]}...)")

from r7_a0plus import _packet_by_id_from_run_tree, _unique_packet_list, \
    _load_pair, _arm_queue_ids  # noqa: E402

V3 = REPO / "eval" / "pairs" / "r10_a0plus"
DEV12 = REPO / "eval" / "problems_dev12.json"
PROBLEMS_ALL = REPO / "eval" / "problems.json"


def _problem_record(pid: str) -> dict:
    for src in (DEV12, PROBLEMS_ALL):
        if not src.exists():
            continue
        d = json.loads(src.read_text(encoding="utf-8"))
        plist = d if isinstance(d, list) else d.get("problems", [])
        for p in plist:
            if str(p.get("problem_id") or p.get("id")) == pid:
                return p
    raise KeyError(pid)


def blind_order(pid: str, pair_kind: str):
    """Deterministic per-pair side order (disclosed, reproducible)."""
    h = hashlib.sha256(f"{pid}::{pair_kind}".encode()).hexdigest()
    return ("a0plus_first" if int(h, 16) % 2 == 0
            else "other_first")


judgments: list = []
exclusions: list = []
t0 = time.time()
n_calls = 0
for pid in _arm_queue_ids():
    vf = V3 / f"{pid}.json"
    if not vf.exists():
        exclusions.append({"problem_id": pid, "from": "both",
                           "why": "no v3 arm record (typed)"})
        continue
    rec = json.loads(vf.read_text(encoding="utf-8"))
    a0_state = str(rec.get("result") or "?")
    a0_ans = str(rec.get("a0plus_answer") or "")
    if not a0_ans.strip():
        exclusions.append({
            "problem_id": pid, "from": "both",
            "why": (f"arm typed {a0_state} with NO answer bytes — the "
                    "compared object does not exist (Art. XXV)")})
        continue
    try:
        prob = _problem_record(pid)
    except KeyError:
        exclusions.append({"problem_id": pid, "from": "both",
                           "why": "no problem record (typed)"})
        continue
    pair = _load_pair(pid)
    base_ans = str((pair or {}).get("baseline_answer") or "")
    full_ans = str((pair or {}).get("pipeline_answer")
                   or rec.get("full_pipeline_answer") or "")
    packet_by_id = _packet_by_id_from_run_tree(pair) if pair else {}
    packet = _unique_packet_list(packet_by_id)
    # the committed full-pipeline marker is NOT an answer
    full_is_answer = (len(full_ans) > 200
                      and not full_ans.startswith("CONTRACT-INVALID"))
    if not full_is_answer:
        exclusions.append({
            "problem_id": pid, "from": "a0plus_vs_full",
            "why": ("the committed full-pipeline bytes are a typed "
                    f"marker ({full_ans[:60] if full_ans else 'EMPTY'}), "
                    "not an answer — the compared object does not exist")})

    for kind, other_ans, other_name in (
            ("a0plus_vs_baseline", base_ans, "baseline"),
            ("a0plus_vs_full", full_ans, "full_pipeline")):
        if kind == "a0plus_vs_full" and not full_is_answer:
            continue
        if not other_ans.strip():
            exclusions.append({"problem_id": pid, "from": kind,
                               "why": f"empty {other_name} bytes (typed)"})
            continue
        order = blind_order(pid, kind)
        a_text, b_text = ((a0_ans, other_ans) if order == "a0plus_first"
                          else (other_ans, a0_ans))
        prompt = _rubric_prompt(prob, a_text, b_text, packet)
        tc0 = time.time()
        res = _transport_call(prov, model, prompt,
                              "You are a strict blind rubric judge. "
                              "English only. Follow the exact output "
                              "lines.", max_tokens=300)
        lat = round(time.time() - tc0, 1)
        n_calls += 1
        jrec = {"problem_id": pid, "pair": kind,
                "order": order, "judge": f"{prov}/{model}",
                "a0plus_typed_state": a0_state,
                "latency_s": lat,
                "prompt_hash": hashlib.sha256(
                    prompt.encode("utf-8")).hexdigest()}
        if res.get("status") != "OK":
            jrec.update({"outcome": "JUDGE_TRANSPORT_FAILED",
                         "error": str(res.get("error"))[:120]})
            judgments.append(jrec)
            continue
        content = res.get("content") or ""
        if content:
            jrec["output_hash"] = hashlib.sha256(
                content.encode("utf-8")).hexdigest()
        parsed = _parse_rubric(content)
        valid = _validate_rubric_pass(
            parsed, bool(prob.get("clarification_answer")))
        if valid is None:
            jrec.update({"outcome": "JUDGE_PARSE_FAILED",
                         "error": "missing/invalid required rubric fields"})
            judgments.append(jrec)
            continue
        prefer = valid["prefer"]
        picked = ("a0plus" if (prefer == "A") == (order == "a0plus_first")
                  else "other" if prefer in ("A", "B")
                  else "tie")
        jrec.update({"outcome": "JUDGE_VALID", "prefer": prefer,
                     "picked": picked,
                     "axes": {k: v for k, v in valid.items()
                              if k != "prefer"}})
        judgments.append(jrec)
        print(f"[r10cmp] {pid[:34]:36} {kind:20} "
              f"state={a0_state[:14]:16} prefer={prefer:4} "
              f"-> {picked} ({lat}s)")

wall = round(time.time() - t0, 1)


def tally(pair_kind: str) -> dict:
    vs = [j for j in judgments
          if j["pair"] == pair_kind and j["outcome"] == "JUDGE_VALID"]
    w = sum(1 for j in vs if j["picked"] == "a0plus")
    l = sum(1 for j in vs if j["picked"] == "other")
    t = sum(1 for j in vs if j["picked"] == "tie")
    ti = sum(1 for j in vs if j["a0plus_typed_state"] != "COMPLETE")
    parse_fail = sum(1 for j in judgments
                     if j["pair"] == pair_kind
                     and j["outcome"] == "JUDGE_PARSE_FAILED")
    transport_fail = sum(1 for j in judgments
                         if j["pair"] == pair_kind
                         and j["outcome"] == "JUDGE_TRANSPORT_FAILED")
    return {"wins_a0plus": w, "ties": t, "losses_a0plus": l,
            "n_valid": len(vs), "typed_incomplete_arms_judged": ti,
            "parse_failed": parse_fail,
            "transport_failed": transport_fail}


tb = tally("a0plus_vs_baseline")
tf = tally("a0plus_vs_full")
n_valid_full = tf["n_valid"]
if n_valid_full >= 10:
    pruning = "ELIGIBLE (>=10 valid A0+-vs-full judgments)"
else:
    pruning = "BLOCKED_INSUFFICIENT_VALID_FULL_JUDGMENTS"

record = {
    "record": "r10_a0plus_compare/1.0.0",
    "commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO),
                             capture_output=True,
                             text=True).stdout.strip(),
    "dirty_tree": bool(subprocess.run(
        ["git", "status", "--porcelain"], cwd=str(REPO),
        capture_output=True, text=True).stdout.strip()),
    "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "judge": {"provider": prov, "model": model,
              "selection": route.get("selection"),
              "judge_independence": route.get("judge_independence"),
              "calibration": {k: calib.get(k) for k in
                              ("correct", "n_pairs", "accuracy",
                               "threshold", "passed",
                               "corpus_sha256")}},
    "blind_protocol": ("side order randomized per pair by "
                       "sha256(problem_id::pair) parity; the judge "
                       "never sees the arm names"),
    "typed_state_disclosure": ("the A0+ arm's typed result "
                               "(COMPLETE/INCOMPLETE_*) rides EVERY "
                               "judgment as metadata; typed-INCOMPLETE "
                               "arms ARE judged and their count is "
                               "disclosed per tally — the typed state "
                               "is never a verdict conversion (Art. X)"),
    "env_disclosure": {"FABRIC_PROBLEM_CALL_CAP": "80",
                       "why": ("the driver's workload is the 30-pair "
                               "calibration + the comparison judgments "
                               "— not one problem's pipeline stage "
                               "chain the cap 12 protects")},
    "tally_vs_baseline": tb,
    "tally_vs_full_pipeline": tf,
    "exclusions": exclusions,
    "interpretation": (
        "NOT universal A0+ superiority even on a winning tally: the "
        "valid set is partial (typed exclusions above), and the "
        "A0+-vs-full valid count is "
        + ("AT or ABOVE the 10-judgment threshold"
           if n_valid_full >= 10 else
           "BELOW the 10-judgment threshold — the pruning decision is "
           "BLOCKED (the 48-item ablation and heavy-stage removal stay "
           "blocked, owner R10 P1 item 8)")),
    "pruning_decision": pruning,
    "n_judgment_calls": n_calls,
    "wall_s": wall,
    "judgments": judgments,
}
OUT = REPO / "eval" / "a0plus_compare_r10.json"
OUT.write_text(json.dumps(record, indent=1, default=str) + "\n",
               encoding="utf-8")
print(f"[r10cmp] A0+ vs baseline: W{tb['wins_a0plus']}/T{tb['ties']}/"
      f"L{tb['losses_a0plus']} (valid {tb['n_valid']}, "
      f"typed-incomplete judged {tb['typed_incomplete_arms_judged']}, "
      f"parse_fail {tb['parse_failed']})")
print(f"[r10cmp] A0+ vs full pipeline: W{tf['wins_a0plus']}/T{tf['ties']}/"
      f"L{tf['losses_a0plus']} (valid {tf['n_valid']}, "
      f"typed-incomplete judged {tf['typed_incomplete_arms_judged']}, "
      f"parse_fail {tf['parse_failed']})")
print(f"[r10cmp] pruning_decision: {pruning}")
print(f"[r10cmp] exclusions: {len(exclusions)} | calls {n_calls} | "
      f"wall {wall}s -> {OUT}")

#!/usr/bin/env python3
"""r11_a0plus_compare.py — OWNER ROUND R11 (2026-11-14): the
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

R11 changes: the judge rides the STRUCTURED-OUTPUT contract (JSON
schema, ONE parse retry, raw output logged — owner item 5); the A0+
compared object is the 3.1.0 default-path delivery; the A1 invention
arm (r11_a1) rides the same blind protocol and is paired against the
baseline AND against A0+ (owner item 3). The record reports the
item-9 gate quantities (novelty delta / feasibility gap) as
CODER-measured inputs — the gate itself is AUDITOR-judged on >=10
pairs and stays PENDING until those judgments exist.

Output: eval/a0plus_compare_r11.json (tracked, sanitized).

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
print("[r11cmp] vault loaded (names only):", sorted(names))
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
    print("[r11cmp] zai gateway admitted")
else:
    print("[r11cmp] zai gateway unavailable (typed) — the judge probe "
          "runs against the remote cascade alone")

from eval.run import (probe_judge_route, _rubric_prompt, _parse_rubric,  # noqa: E402
                      _validate_rubric_pass, _transport_call,
                      _judge_judgment_call)

route = probe_judge_route("zai")
calib = route.get("calibration_full") or {}
if not route.get("provider") or not calib.get("passed"):
    print("[r11cmp] TYPED: no calibration-eligible judge this window — "
          "no comparison runs (Art. LXI)")
    sys.exit(3)
prov, model = route["provider"], route["model"]
print(f"[r11cmp] calibrated judge: {prov}/{model} "
      f"({calib.get('correct')}/{calib.get('n_pairs')}, "
      f"corpus {str(calib.get('corpus_sha256'))[:12]}...)")

from r7_a0plus import _packet_by_id_from_run_tree, _unique_packet_list, \
    _load_pair, _arm_queue_ids  # noqa: E402

V3 = REPO / "eval" / "pairs" / "r11_a0plus"
V1A1 = REPO / "eval" / "pairs" / "r11_a1"
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


_RUBRIC_REC = REPO / "eval" / "invention_rubric_r11.json"
all_scores_ref = None
if _RUBRIC_REC.exists():
    try:
        all_scores_ref = json.loads(
            _RUBRIC_REC.read_text(encoding="utf-8")).get("gate_inputs")
    except Exception:  # noqa: BLE001
        all_scores_ref = None

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

    a1_ans = ""
    a1_state = "NOT_RUN"
    a1f = V1A1 / f"{pid}.json"
    if a1f.exists():
        try:
            _a1 = json.loads(a1f.read_text(encoding="utf-8"))
            a1_ans = str(_a1.get("a1_answer") or "")
            a1_state = str(_a1.get("result") or "?")
        except Exception:  # noqa: BLE001
            a1_ans = ""
    if not a1_ans.strip():
        exclusions.append({
            "problem_id": pid, "from": "a1_pairs",
            "why": (f"A1 typed {a1_state} with no answer bytes "
                    "(typed)")})

    def _judge_pair(kind, x_ans, y_ans, x_state):
        order = blind_order(pid, kind)
        a_text, b_text = ((x_ans, y_ans) if order == "a0plus_first"
                          else (y_ans, x_ans))
        return order, a_text, b_text

    for kind, other_ans, other_name, other_is_a0 in (
            ("a0plus_vs_baseline", base_ans, "baseline", False),
            ("a0plus_vs_full", full_ans, "full_pipeline", False),
            ("a1_vs_baseline", base_ans, "baseline", False),
            ("a1_vs_a0plus", a0_ans, "a0plus", True)):
        if kind == "a0plus_vs_full" and not full_is_answer:
            continue
        if kind == "a1_vs_baseline" and not base_ans.strip():
            exclusions.append({"problem_id": pid, "from": kind,
                               "why": "empty baseline bytes (typed)"})
            continue
        if kind == "a1_vs_a0plus" and not a0_ans.strip():
            exclusions.append({"problem_id": pid, "from": kind,
                               "why": "empty a0plus bytes (typed)"})
            continue
        if not other_ans.strip():
            exclusions.append({"problem_id": pid, "from": kind,
                               "why": f"empty {other_name} bytes (typed)"})
            continue
        x_ans = a1_ans if kind.startswith("a1_") else a0_ans
        x_state = a1_state if kind.startswith("a1_") else a0_state
        order = blind_order(pid, kind)
        a_text, b_text = ((x_ans, other_ans) if order == "a0plus_first"
                          else (other_ans, x_ans))
        prompt = _rubric_prompt(prob, a_text, b_text, packet)
        n_calls += 1
        # R11 item 5: ONE structured-output call + ONE parse retry,
        # raw output logged per attempt (typed outcomes, never
        # converted)
        jc = _judge_judgment_call(prov, model, prompt, max_tokens=300,
                                  clar=bool(
                                      prob.get("clarification_answer")))
        lat = round(sum(jc.get("latencies") or [0]), 1)
        jrec = {"problem_id": pid, "pair": kind,
                "order": order, "judge": f"{prov}/{model}",
                "a0plus_typed_state": a0_state,
                "latency_s": lat,
                "n_parse_attempts": len(jc.get("attempts") or []),
                "raw_output": (jc.get("raw") or "")[:400],
                "prompt_hash": hashlib.sha256(
                    prompt.encode("utf-8")).hexdigest()}
        if jc["outcome"] != "JUDGE_VALID":
            jrec.update({"outcome": jc["outcome"],
                         "error": str((jc.get("errors") or [""])[0])[:120]})
            judgments.append(jrec)
            continue
        valid = jc["valid"]
        prefer = valid["prefer"]
        _x_name = "a1" if kind.startswith("a1_") else "a0plus"
        _y_name = other_name
        picked = (_x_name if (prefer == "A") == (order == "a0plus_first")
                  else _y_name if prefer in ("A", "B")
                  else "tie")
        jrec.update({"outcome": "JUDGE_VALID", "prefer": prefer,
                     "x_arm": _x_name, "y_arm": _y_name,
                     "x_typed_state": x_state,
                     "picked": picked,
                     "axes": {k: v for k, v in valid.items()
                              if k != "prefer"}})
        judgments.append(jrec)
        print(f"[r11cmp] {pid[:34]:36} {kind:20} "
              f"state={a0_state[:14]:16} prefer={prefer:4} "
              f"-> {picked} ({lat}s)")

wall = round(time.time() - t0, 1)


def tally(pair_kind: str, x_arm: str = "a0plus") -> dict:
    vs = [j for j in judgments
          if j["pair"] == pair_kind and j["outcome"] == "JUDGE_VALID"]
    w = sum(1 for j in vs if j["picked"] == x_arm)
    l = sum(1 for j in vs if j["picked"] not in ("tie", x_arm))
    t = sum(1 for j in vs if j["picked"] == "tie")
    ti = sum(1 for j in vs
             if (j.get("x_typed_state")
                 or j["a0plus_typed_state"]) != "COMPLETE")
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
ta1b = tally("a1_vs_baseline", x_arm="a1")
ta1a = tally("a1_vs_a0plus", x_arm="a1")
n_valid_full = tf["n_valid"]
if n_valid_full >= 10:
    pruning = "ELIGIBLE (>=10 valid A0+-vs-full judgments)"
else:
    pruning = "BLOCKED_INSUFFICIENT_VALID_FULL_JUDGMENTS"

record = {
    "record": "r11_a0plus_compare/1.0.0",
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
    "tally_a1_vs_baseline": ta1b,
    "tally_a1_vs_a0plus": ta1a,
    "holdout_gate_r11": {
        "definition": ("an arm beats the baseline on invention-rubric "
                       "NOVELTY by >=0.5 with feasibility within 0.25 "
                       "of the baseline, AUDITOR-judged on >=10 pairs "
                       "(owner R11 item 9); format wins do not count"),
        "machine_judgments_are": "INPUTS, never the gate (Art. XXVI)",
        "status": "PENDING_AUDITOR_JUDGMENTS",
        "machine_measured_novelty_delta_a1_vs_baseline":
            (all_scores_ref.get("a1_novelty_delta")
             if all_scores_ref else "NOT_MEASURED")},
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
OUT = REPO / "eval" / "a0plus_compare_r11.json"
OUT.write_text(json.dumps(record, indent=1, default=str) + "\n",
               encoding="utf-8")
print(f"[r11cmp] A1 vs baseline: W{ta1b['wins_a0plus']}/T{ta1b['ties']}/"
      f"L{ta1b['losses_a0plus']} (valid {ta1b['n_valid']})")
print(f"[r11cmp] A1 vs A0+: W{ta1a['wins_a0plus']}/T{ta1a['ties']}/"
      f"L{ta1a['losses_a0plus']} (valid {ta1a['n_valid']})")
print(f"[r11cmp] A0+ vs baseline: W{tb['wins_a0plus']}/T{tb['ties']}/"
      f"L{tb['losses_a0plus']} (valid {tb['n_valid']}, "
      f"typed-incomplete judged {tb['typed_incomplete_arms_judged']}, "
      f"parse_fail {tb['parse_failed']})")
print(f"[r11cmp] A0+ vs full pipeline: W{tf['wins_a0plus']}/T{tf['ties']}/"
      f"L{tf['losses_a0plus']} (valid {tf['n_valid']}, "
      f"typed-incomplete judged {tf['typed_incomplete_arms_judged']}, "
      f"parse_fail {tf['parse_failed']})")
print(f"[r11cmp] pruning_decision: {pruning}")
print(f"[r11cmp] exclusions: {len(exclusions)} | calls {n_calls} | "
      f"wall {wall}s -> {OUT}")

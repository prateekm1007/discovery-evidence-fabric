#!/usr/bin/env python3
"""r9_a0plus_compare.py — OWNER ROUND 2026-11-13 P0 item 2.7 + P0 item 3.4:
the PAIRED BLIND COMPARISON of the validated A0+ arm against (a) the
committed baseline and (b) the committed full-pipeline answer, judged by
the CALIBRATED judge (the calibration gate runs IN this script — a tiny
probe alone is not a judge result).

Blind protocol: the judge sees ANSWER A / ANSWER B with the side order
deterministically randomized per pair (sha256(problem_id+pair) parity,
disclosed); it never learns which side is which arm. The rubric is the
committed _rubric_prompt (the same instrument the score table uses); the
strict response contract (_parse_rubric + _validate_rubric_pass) applies
— a malformed response is JUDGE_PARSE_FAILED, never a verdict.

Recorded per judgment: problem, pair, order, outcome, prefer, axis
scores, picked side, latency, prompt/output hashes (byte-bound). Typed
exclusions: problems whose committed full-pipeline bytes are a
CONTRACT-INVALID marker (not an answer) are excluded from the
A0+-vs-full comparison and REPORTED (never silently dropped).

Output: eval/a0plus_compare_r9.json (tracked, sanitized — no credential
material, no raw answer bytes in the record).

Serves: Art. LXXVII (the deliverable is judged, not the pipeline),
Art. XLV (judge independence: the calibrated xkiro rung is a different
provider+family from the zai synthesis head), Art. XLVII (baseline
supremacy), Art. XXV (every exclusion typed, nothing invented).
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
print("[r9cmp] vault loaded (names only):", sorted(names))
os.environ.setdefault("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")
os.environ.setdefault("ENGINE_LLM_TIMEOUT_S", "40")
# R9 measured: the per-problem healthy-call cap (12) is a PIPELINE-stage
# protection — one problem's stage chain. This driver's workload is the
# 30-pair calibration (~30 calls) + the comparison judgments (~20) — a
# DIFFERENT shape the cap was never scoped for; without the override the
# calibration consumes the budget and the judgments transport-fail
# typed (measured: 5 judgments HEALTHY_CALL_CAP_EXCEEDED). The override
# is disclosed here and rides the record (never silent, Art. XXVII).
os.environ["FABRIC_PROBLEM_CALL_CAP"] = "80"

gw = subprocess_run = None
import subprocess  # noqa: E402
gw = subprocess.run(["bash", "scripts/zai_gateway_env.sh"], cwd=str(REPO),
                    capture_output=True, text=True, timeout=90)
if gw.returncode == 0:
    for line in (gw.stdout or "").splitlines():
        line = line.strip()
        if line.startswith("export ") and "=" in line:
            k, v = line[len("export "):].split("=", 1)
            os.environ[k] = v
    print("[r9cmp] zai gateway admitted (the synthesis head the judge "
          "must differ from)")
else:
    print("[r9cmp] zai gateway unavailable (typed) — the judge probe "
          "runs against the remote cascade alone")

import importlib  # noqa: E402
_run = importlib.import_module("eval.run")

from eval.run import (probe_judge_route, _rubric_prompt, _parse_rubric,  # noqa: E402
                      _validate_rubric_pass, _transport_call)

# ---- the CALIBRATED judge (the gate runs HERE) ------------------------
route = probe_judge_route("zai")
calib = route.get("calibration_full") or {}
if not route.get("provider") or not calib.get("passed"):
    print("[r9cmp] TYPED: no calibration-eligible judge this window — "
          "no comparison runs (Art. LXI)")
    sys.exit(3)
prov, model = route["provider"], route["model"]
print(f"[r9cmp] calibrated judge: {prov}/{model} "
      f"({calib.get('correct')}/{calib.get('n_pairs')}, "
      f"corpus {str(calib.get('corpus_sha256'))[:12]}...)")

sys.path.insert(0, str(REPO))
from r7_a0plus import _packet_by_id_from_run_tree, _unique_packet_list, \
    _load_pair  # noqa: E402

V2 = REPO / "eval" / "pairs" / "r9_a0plus"
dev = json.loads((REPO / "eval" / "problems_dev12.json").read_text(
    encoding="utf-8"))
plist = dev if isinstance(dev, list) else dev.get("problems", [])


def blind_order(pid: str, pair_kind: str):
    """Deterministic per-pair side order (disclosed, reproducible)."""
    h = hashlib.sha256(f"{pid}::{pair_kind}".encode()).hexdigest()
    return ("a0plus_first" if int(h, 16) % 2 == 0
            else "other_first")


judgments: list = []
exclusions: list = []
t0 = time.time()
n_calls = 0
for prob in plist:
    pid = str(prob.get("problem_id") or prob.get("id"))
    vf = V2 / f"{pid}.json"
    if not vf.exists():
        exclusions.append({"problem_id": pid, "from": "both",
                           "why": "no COMPLETE v2 A0+ arm (typed)"})
        continue
    rec = json.loads(vf.read_text(encoding="utf-8"))
    if rec.get("result") != "COMPLETE":
        exclusions.append({"problem_id": pid, "from": "both",
                           "why": f"v2 arm result={rec.get('result')} (typed)"})
        continue
    a0_ans = str(rec.get("a0plus_answer") or "")
    base_ans = str(rec.get("baseline_answer") or "")
    full_ans = str(rec.get("full_pipeline_answer") or "")
    pair = _load_pair(pid)
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
        print(f"[r9cmp] {pid[:34]:36} {kind:20} prefer={prefer:4} "
              f"-> {picked} ({lat}s)")

wall = round(time.time() - t0, 1)


def tally(pair_kind: str) -> dict:
    vs = [j for j in judgments
          if j["pair"] == pair_kind and j["outcome"] == "JUDGE_VALID"]
    w = sum(1 for j in vs if j["picked"] == "a0plus")
    l = sum(1 for j in vs if j["picked"] == "other")
    t = sum(1 for j in vs if j["picked"] == "tie")
    parse_fail = sum(1 for j in judgments
                     if j["pair"] == pair_kind
                     and j["outcome"] == "JUDGE_PARSE_FAILED")
    transport_fail = sum(1 for j in judgments
                         if j["pair"] == pair_kind
                         and j["outcome"] == "JUDGE_TRANSPORT_FAILED")
    return {"wins_a0plus": w, "ties": t, "losses_a0plus": l,
            "n_valid": len(vs), "parse_failed": parse_fail,
            "transport_failed": transport_fail}


record = {
    "record": "r9_a0plus_compare/1.0.0",
    "commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO),
                             capture_output=True,
                             text=True).stdout.strip(),
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
    "env_disclosure": {"FABRIC_PROBLEM_CALL_CAP": "80",
                       "why": ("the driver's workload is the 30-pair "
                               "calibration + the comparison judgments "
                               "— not one problem's pipeline stage "
                               "chain the cap 12 protects")},
    "tally_vs_baseline": tally("a0plus_vs_baseline"),
    "tally_vs_full_pipeline": tally("a0plus_vs_full"),
    "exclusions": exclusions,
    "n_judgment_calls": n_calls,
    "wall_s": wall,
    "judgments": judgments,
}
OUT = REPO / "eval" / "a0plus_compare_r9.json"
OUT.write_text(json.dumps(record, indent=1, default=str) + "\n",
               encoding="utf-8")
tb = record["tally_vs_baseline"]
tf = record["tally_vs_full_pipeline"]
print(f"[r9cmp] A0+ vs baseline: W{tb['wins_a0plus']}/T{tb['ties']}/"
      f"L{tb['losses_a0plus']} (valid {tb['n_valid']}, "
      f"parse_fail {tb['parse_failed']})")
print(f"[r9cmp] A0+ vs full pipeline: W{tf['wins_a0plus']}/T{tf['ties']}/"
      f"L{tf['losses_a0plus']} (valid {tf['n_valid']}, "
      f"parse_fail {tf['parse_failed']})")
print(f"[r9cmp] exclusions: {len(exclusions)} | calls {n_calls} | "
      f"wall {wall}s -> {OUT}")

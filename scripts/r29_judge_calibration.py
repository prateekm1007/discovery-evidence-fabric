#!/usr/bin/env python3
"""r29_judge_calibration.py — AM27 D3 (F39): the judge feasibility-axis
CALIBRATION run (claim c-0026, work_id r29-judge-feasibility-calibration,
pre-registered BEFORE the first judge LLM call).

WHAT THIS IS (AM27, typed): the machine judge's feasibility axis is
UNCALIBRATED for procedure-class rows (the R28 cross-check assigned
F_A=1 to pure firmware/procedure changes on existing hardware —
bench-p10's inverter duty cycle, dev-fu-005's install cycling,
eval-new05's BMS schedule, eval-sofc-redox's gas sequencing — all
procurable by construction; the auditor REJECTED the read as
uncalibrated, F39). This run measures the CALIBRATED judge (the v3
axis suffix carrying the auditor's two pins verbatim-in-spirit:
firmware/procedure change on existing hardware => F >= 4;
new-process development => F <= 3) against the auditor's 18-row
re-judgment.

ACCEPTANCE (AM27 D3): judge feasibility within +/-1 of the auditor on
>= 16/18 rows; until then the machine judge stays a novelty-only
cross-check. This is a MEASUREMENT of the cross-check instrument —
never a gate input on feasibility (the gate is auditor-judged,
Art. 14/LXXXVI; the builder never scores — Art. 10).

INPUT DISCIPLINE (pre-registered on the claim):
  - the 18 intervention rows of eval/r27_judge_packet.json — the SAME
    problem/a1/baseline bytes the auditor re-judged (the packet is
    the auditor's own judged input);
  - the prompt per row = the packet's rubric_prompt with the v2 axis
    suffix replaced by the v3 suffix — the PRE-SUFFIX prefix is
    BYTE-IDENTICAL to the packet prompt (the verifier recomputes);
    the ONLY delta is the F-axis calibration pins inside the suffix;
  - the auditor's per-row scores are read from the pinned audit tip
    via git show (auditor-controlled content is never copied into
    the queue tree; the bytes ride the record only as the comparison
    anchor with their exact provenance).

ROUTE (canonical, unchanged from the r28 cross-check): crowllm /
qwen-3.8-max:free, K=3 draws per row, pace 13 s, max_tokens 4000,
transport ladder (20 s / 60 s), one parse retry per call; provider
AND family independent of the zai/GLM generator (Art. 10/26); the
credential rides the gitignored vault (.env.keys, operator-supplied);
servability-gated by a probe on the ACTUAL route through the ACTUAL
transport path before any judging (the R11 catalog-poisoning lesson).

MODES
  probe     servability gate (tiny + verdict-shaped trials); PASS
            gates the run, FAIL types the block and stops.
  run       judge the 18 rows (resumable via the partial file; a row
            with >=1 valid draw is never re-judged).
  assemble  build the calibration record + the acceptance recompute
            (zero LLM calls).
"""
import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()

os.environ.setdefault("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")
os.environ.setdefault("FABRIC_BREAKER_THRESHOLD", "60")
os.environ.setdefault(
    "ZAI_GATEWAY_LOG",
    str(REPO / "ENGINE_RUNS" / "zai_gateway_calls.jsonl"))

from eval.run import _judge_judgment_call, _transport_call  # noqa: E402
from eval.battery_metrics import parse_axes  # noqa: E402
from discovery_fabric.engine import llm_economy as econ  # noqa: E402

PACKET = REPO / "eval" / "r27_judge_packet.json"
V3_SUFFIX = (REPO / "scripts" / "_r29_axis_suffix_v3.txt").read_text()
V2_SUFFIX = (REPO / "scripts" / "_f28_axis_suffix_v2.txt").read_text()
SUFFIX_MARKER = "=== PER-AXIS SCORING CONTRACT"

OUT = REPO / "eval" / "judge_feasibility_calibration_r29.json"
PARTIAL = REPO / "eval" / "judge_feasibility_calibration_r29.partial.json"
RUN_LOG = REPO / "ENGINE_RUNS" / "r29_judge_calibration.log"

JUDGE = (os.environ.get("R12_JUDGE_PROVIDER", "crowllm"),
         os.environ.get("R12_JUDGE_MODEL", "qwen-3.8-max:free"))
K = 3
PACE_S = float(os.environ.get("R12_PACE_S", "13.0"))
LADDER_BACKOFF_S = (20.0, 60.0)
MAX_TOKENS = 4000

CLAIM = "c-0026"
WORK_ID = "r29-judge-feasibility-calibration"
SESSION = "builder-r29s1"
BASE_SHA = "2d006679b"

AUDITOR_ANCHOR_SHA = "d7540c6fe"
AUDITOR_ANCHOR_REF = ("audit/r11-auditor-verdict-20261114 @ d7540c6fe:"
                      "eval/auditor_r28_adjudication.json")

ACCEPT_WITHIN = 1      # |machine - auditor| <= 1 on a1_feasibility
ACCEPT_MIN_ROWS = 16   # on >= 16 of the 18 rows


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace(
        "+00:00", "Z")


def _sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _log(msg):
    line = f"[{_now()}] {msg}"
    print(line, flush=True)
    RUN_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(RUN_LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def _auditor_rejudgment():
    """The auditor's 18-row re-judgment, extracted VERBATIM from the
    pinned audit tip (auditor-controlled content is never copied into
    the queue tree; the bytes ride the record only as the comparison
    anchor with their exact provenance)."""
    out = subprocess.run(
        ["git", "-C", str(REPO), "show",
         f"{AUDITOR_ANCHOR_SHA}:eval/auditor_r28_adjudication.json"],
        capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def _v3_prompt(packet_row):
    """The calibrated prompt: the packet's rubric_prompt with the v2
    suffix replaced by the v3 suffix. The PRE-SUFFIX prefix must be
    BYTE-IDENTICAL to the packet prompt (asserted)."""
    rp = packet_row["rubric_prompt"]
    assert rp.endswith(V2_SUFFIX), \
        f"packet prompt does not end with the v2 suffix: {packet_row['problem_id']}"
    prefix = rp[: -len(V2_SUFFIX)]
    assert SUFFIX_MARKER in V3_SUFFIX
    return prefix + V3_SUFFIX


def judge_transport_ready():
    from discovery_fabric.engine import llm_registry as lr
    spec = next((s for s in lr.PROVIDER_SPECS
                 if s.provider_id == JUDGE[0]), None)
    if spec is None:
        return False, f"NO_SPEC for judge provider {JUDGE[0]}"
    if not lr.active_key_value(spec).strip():
        return False, (f"judge provider {JUDGE[0]} holds NO credential "
                       f"(env {spec.env_var} empty; Art. 17: keys are "
                       "operator-supplied)")
    return True, "key present (names only, never the value)"


# ---------------------------------------------------------------- probe

PROBE_RUBRIC = """You judge two engineering answers to the same user problem.

DEVICE: laboratory magnetic stirrer hotplate
FAILURE: the stir bar decouples at high viscosity, stopping agitation mid-reaction
USER'S QUESTION: What engineering change would keep agitation coupled at high viscosity, and what test would falsify it?

=== ANSWER A ===
Use a commercially available PTFE-coated oval stir bar of the next larger size in the standard manufacturer size chart, driven at the same 60 percent of rated speed. The larger moment arm keeps the magnetic coupling above the decoupling torque across the viscosity range. Falsification: run the OEM load test at the top of the specified viscosity range; if decoupling occurs twice in ten runs, the change fails.

=== ANSWER B ===
The standard practice is to reduce the setpoint speed until coupling is stable, accepting slower agitation. Falsification: observe the drive current; if it stops oscillating, coupling is stable.

First, three YES/NO compliance gates for EACH answer (0 = fails, 1 = passes):
1 answers the asked question
2 uses user-stated variables
3 gives a specific testable prediction
Then score BOTH answers 1 (bad) to 5 (excellent) on:
4 grounded in the provided evidence
6 gives a specific, non-obvious design (not the generic default)
Then state your overall preference. Respond with ONLY one JSON object - no prose, no markdown fences - with exactly these integer keys:
{"A1": <0|1>, "A2": <0|1>, "A3": <0|1>, "A4": <1-5>,
"B1": <0|1>, "B2": <0|1>, "B3": <0|1>, "B4": <1-5>,
"A6": <1-5>, "B6": <1-5>,
"prefer": "A" | "B" | "TIE"}

""" + V3_SUFFIX


def probe():
    """Servability gate on the ACTUAL judge route through the ACTUAL
    transport path (the R11 catalog-poisoning lesson). PASS = tiny call
    non-empty AND >=1 verdict-shaped trial returns a parseable rubric
    JSON. FAIL types the block and stops — no silent re-routing."""
    ok, detail = judge_transport_ready()
    _log(f"[preflight] judge_transport_ready: {detail}")
    if not ok:
        rec = {"record": "R29_CALIB_PROBE/1.0.0", "at": _now(),
               "gate": "BLOCKED", "class": "NO_CREDENTIAL",
               "detail": detail}
        print(json.dumps(rec, indent=1))
        return 2
    results = {"record": "R29_CALIB_PROBE/1.0.0", "at": _now(),
               "route": {"provider": JUDGE[0], "model": JUDGE[1],
                         "axis_suffix": "v3 (calibrated F pins)"},
               "tiny": None, "verdict_shaped": [], "gate": None}
    t0 = time.time()
    r = _transport_call(JUDGE[0], JUDGE[1],
                        "Reply with exactly: OK",
                        "You are a servability probe. English only.",
                        max_tokens=20)
    results["tiny"] = {"status": r.get("status"),
                       "content_chars": len(str(r.get("content") or "")),
                       "error": (r.get("error") or "")[:120],
                       "latency_s": round(time.time() - t0, 1)}
    _log(f"[probe][tiny] {results['tiny']}")
    if r.get("status") != "OK" or not str(r.get("content") or "").strip():
        results["gate"] = "BLOCKED"
        results["class"] = "TINY_CALL_FAILED"
        print(json.dumps(results, indent=1))
        return 2
    for i in (1, 2):
        t0 = time.time()
        jc = _judge_judgment_call(JUDGE[0], JUDGE[1], PROBE_RUBRIC,
                                  max_tokens=MAX_TOKENS)
        trial = {"trial": i, "outcome": jc.get("outcome"),
                 "valid": bool(jc.get("valid")),
                 "latencies": jc.get("latencies"),
                 "raw_excerpt": str(jc.get("raw") or "")[:200]}
        results["verdict_shaped"].append(trial)
        _log(f"[probe][verdict-shaped {i}] outcome={trial['outcome']} "
             f"valid={trial['valid']}")
        time.sleep(8.0)
    n_valid = sum(1 for t in results["verdict_shaped"] if t["valid"])
    if n_valid >= 1:
        results["gate"] = "PASS"
        results["n_verdict_valid"] = n_valid
    else:
        results["gate"] = "BLOCKED"
        results["class"] = "VERDICT_JSON_NOT_SERVED"
    print(json.dumps(results, indent=1))
    return 0 if results["gate"] == "PASS" else 2


# ------------------------------------------------------------------ run

def judge_slot(pid, k, prompt):
    """The canonical judge ladder (the r28 crosscheck's judge_slot
    verbatim modulo the scope prefix): ladder (0/20/60), governor reset
    per attempt, one parse retry inside the call."""
    attempts = []
    jc = None
    outcome = None
    for try_n in range(1 + len(LADDER_BACKOFF_S)):
        if try_n:
            time.sleep(LADDER_BACKOFF_S[try_n - 1])
        econ.reset_governor(f"r29cal:{pid}:{k}"
                            + (f":retry{try_n}" if try_n else ""))
        jc = _judge_judgment_call(JUDGE[0], JUDGE[1], prompt,
                                  max_tokens=MAX_TOKENS)
        outcome = jc.get("outcome")
        attempts.append({"n": try_n + 1, "outcome": outcome,
                         "latency_s": (jc.get("latencies")
                                       or [None])[-1]})
        if outcome == "JUDGE_VALID":
            break
    return jc, outcome, attempts


def _rows():
    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    return [r for r in packet["rows"]
            if str(r.get("question_type", "")).startswith("intervention")]


def run():
    rows = _rows()
    assert len(rows) == 18, f"expected 18 intervention rows: {len(rows)}"
    prior = {}
    if PARTIAL.exists():
        for r in json.loads(PARTIAL.read_text(encoding="utf-8")):
            prior[r["problem_id"]] = r
    results = []
    n_calls = 0
    n_ladder = 0
    t_start = time.time()
    for row in rows:
        pid = row["problem_id"]
        if pid in prior:
            results.append(prior[pid])
            _log(f"[run] {pid[:40]:<42} resumed "
                 f"(F_A={prior[pid].get('machine_a1_feasibility')})")
            continue
        prompt = _v3_prompt(row)
        assert prompt.endswith(V3_SUFFIX)
        draws = []
        for k in range(K):
            jc, outcome, atts = judge_slot(pid, k, prompt)
            n_calls += len(atts)
            n_ladder += max(0, len(atts) - 1)
            draws.append({"k": k, "outcome": outcome,
                          "axes": parse_axes(jc),
                          "transport_attempts": atts})
            if k < K - 1:
                time.sleep(PACE_S)
        valid_axes = [d["axes"] for d in draws
                      if d["outcome"] == "JUDGE_VALID" and d["axes"]]
        f_vals = sorted(a["F_A"] for a in valid_axes if "F_A" in a)
        n_vals = sorted(a["N_A"] for a in valid_axes if "N_A" in a)
        med = (f_vals[len(f_vals) // 2] if f_vals else None)
        med_n = (n_vals[len(n_vals) // 2] if n_vals else None)
        rec = {"problem_id": pid,
               "question_type": row.get("question_type"),
               "stage": row.get("stage"),
               "judge": list(JUDGE),
               "axis_suffix": "v3 (calibrated F pins)",
               "v3_prompt_sha256_16": _sha(prompt),
               "packet_prefix_byte_identical": True,
               "draws": draws,
               "n_valid_draws": sum(1 for d in draws
                                    if d["outcome"] == "JUDGE_VALID"),
               "machine_a1_feasibility_median": med,
               "machine_a1_feasibility_values": f_vals,
               "machine_a1_novelty_median": med_n}
        results.append(rec)
        PARTIAL.write_text(
            json.dumps(results, indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8")
        _log(f"[run] {pid[:40]:<42} F_A={med} (vals {f_vals}) "
             f"N_A={med_n} valid={rec['n_valid_draws']}/{K} "
             f"({time.time()-t_start:.0f}s elapsed, calls={n_calls})")
    _log(f"[run] COMPLETE: {len(results)} rows, "
         f"judge_slot_attempts={n_calls} ladder_retries={n_ladder}")
    print(json.dumps({"rows": len(results),
                      "judge_slot_attempts": n_calls,
                      "ladder_retries": n_ladder}, indent=1))
    return 0


# ------------------------------------------------------------- assemble

def assemble():
    rows = json.loads(PARTIAL.read_text(encoding="utf-8"))
    assert len(rows) == 18, f"partial incomplete: {len(rows)}/18"
    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    packet_rows = {r["problem_id"]: r for r in packet["rows"]}

    # prompt discipline recompute: prefix byte-identical + v3 suffix
    for r in rows:
        pr = packet_rows[r["problem_id"]]
        v3 = _v3_prompt(pr)
        assert _sha(v3) == r["v3_prompt_sha256_16"], \
            f"v3 prompt sha drift {r['problem_id']}"
        assert v3.endswith(V3_SUFFIX)

    auditor = _auditor_rejudgment()
    # the adjudication's per_row IS the 18-row re-judgment
    auditor_rows = {p["problem_id"]: p for p in auditor["per_row"]}

    comparison = []
    n_within = 0
    n_compared = 0
    for r in rows:
        a = auditor_rows[r["problem_id"]]
        m_f = r["machine_a1_feasibility_median"]
        a_f = a["a1_feasibility"]
        entry = {
            "problem_id": r["problem_id"],
            "stage": r["stage"],
            "machine": {"a1_feasibility": m_f,
                        "values": r["machine_a1_feasibility_values"],
                        "novelty_median": r["machine_a1_novelty_median"],
                        "n_valid_draws": r["n_valid_draws"]},
            "auditor_r28": {"a1_feasibility": a_f,
                            "baseline_feasibility":
                                a["baseline_feasibility"],
                            "feasibility_abs_gap":
                                a["feasibility_abs_gap"],
                            "novelty_delta": a["novelty_delta"]},
        }
        if m_f is not None:
            n_compared += 1
            d = m_f - a_f
            entry["delta"] = d
            entry["within_1"] = abs(d) <= ACCEPT_WITHIN
            if abs(d) <= ACCEPT_WITHIN:
                n_within += 1
        comparison.append(entry)

    acceptance = {
        "rule": ("judge feasibility within +/-1 of the auditor on "
                 ">=16/18 rows (AM27 D3); until then the machine judge "
                 "stays a novelty-only cross-check"),
        "n_rows": len(rows),
        "n_compared": n_compared,
        "n_within_1": n_within,
        "met": bool(n_compared == 18 and n_within >= ACCEPT_MIN_ROWS),
        "disposition": (
            "CALIBRATED (within +/-1 on >=16/18)" if (
                n_compared == 18 and n_within >= ACCEPT_MIN_ROWS)
            else "NOVELTY-ONLY CROSS-CHECK (the feasibility axis stays "
                 "uncalibrated; the auditor's read governs)"),
    }

    # the F39 pin rows: the four procedure-class rows the R28 machine
    # read F_A=1 on (the auditor's tolerance-ruling basis)
    f39_rows = ["bench-p10-pv-pid", "dev-fu-005-bridge-bearing",
                "eval-new05-liion-balance-drift", "eval-sofc-redox"]
    f39_check = [{
        "problem_id": e["problem_id"],
        "machine_F": e["machine"]["a1_feasibility"],
        "auditor_F": e["auditor_r28"]["a1_feasibility"],
        "within_1": e.get("within_1"),
    } for e in comparison if e["problem_id"] in f39_rows]

    n_calls = 0
    n_ladder = 0
    for r in rows:
        for d in r["draws"]:
            atts = d.get("transport_attempts") or []
            n_calls += len(atts)
            n_ladder += max(0, len(atts) - 1)

    record = {
        "record": "JUDGE_FEASIBILITY_CALIBRATION_R29/1.0.0",
        "at": _now(),
        "typed": ("CROSS-CHECK INSTRUMENT CALIBRATION — AM27 D3/F39; "
                  "the machine judge is an INPUT, never the verdict; "
                  "the gate is auditor-judged (Art. 14/LXXXVI); the "
                  "builder never scores its own generation (Art. 10)"),
        "claim": {"claim_id": CLAIM, "work_id": WORK_ID,
                  "session": SESSION, "base_sha": BASE_SHA},
        "input": {
            "packet": "eval/r27_judge_packet.json",
            "rows": 18,
            "prompt_discipline": ("problem/a1/baseline bytes BYTE-EXACT "
                                  "from the packet; the ONLY prompt delta "
                                  "vs the packet's rubric_prompt is the "
                                  "v2->v3 axis-suffix block (the F-axis "
                                  "calibration pins); the pre-suffix "
                                  "prefix is byte-identical (recomputed "
                                  "by scripts/r29_verify_calibration.py)"),
            "axis_suffix": {
                "v2": "scripts/_f28_axis_suffix_v2.txt",
                "v3": "scripts/_r29_axis_suffix_v3.txt",
                "delta": ("exactly the F-axis CALIBRATION PINS — "
                          "firmware/schedule/parameter-procedure change "
                          "on existing hardware => F >= 4; new-process "
                          "development => F <= 3; the N/T/C axis text "
                          "and every other suffix byte unchanged"),
            },
        },
        "judge": {
            "route": list(JUDGE),
            "k": K, "pace_s": PACE_S, "max_tokens": MAX_TOKENS,
            "transport_ladder": list(LADDER_BACKOFF_S),
            "independence": ("crowllm/Qwen vs zai/GLM generator — "
                             "provider AND family independent "
                             "(Art. 10/26); the canonical r28 route, "
                             "unchanged"),
        },
        "auditor_anchor": {
            "provenance": AUDITOR_ANCHOR_REF,
            "sha": AUDITOR_ANCHOR_SHA,
            "basis": ("the auditor's 18-row re-judgment (novelty 2.444 "
                      "/ feasibility 0.556 CI [0.249, 0.862]) — the "
                      "same packet bytes this run rides"),
        },
        "results": rows,
        "comparison": comparison,
        "f39_pin_rows": f39_check,
        "acceptance": acceptance,
        "quota": {"judge_slot_attempts": n_calls,
                  "ladder_retries": n_ladder,
                  "budget": "18 rows x K=3 = 54 logical judge calls + "
                            "typed ladder retries"},
        "generation": {"calls": 0,
                       "note": "zero generator calls — pure judge "
                               "measurement on frozen bytes"},
    }
    OUT.write_text(json.dumps(record, indent=1, ensure_ascii=False)
                   + "\n", encoding="utf-8")
    _log(f"[assemble] wrote {OUT.name}: within_1 {n_within}/{n_compared} "
         f"-> {acceptance['disposition']}")
    print(json.dumps({"out": str(OUT),
                      "acceptance": acceptance,
                      "f39_pin_rows": f39_check}, indent=1))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("probe", "run", "assemble", "all"))
    args = ap.parse_args()
    if args.mode == "probe":
        return probe()
    if args.mode == "run":
        return run()
    if args.mode == "assemble":
        return assemble()
    if args.mode == "all":
        rc = probe()
        if rc != 0:
            return rc
        rc = run()
        if rc != 0:
            return rc
        return assemble()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

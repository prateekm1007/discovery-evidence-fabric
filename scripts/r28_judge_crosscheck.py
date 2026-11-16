#!/usr/bin/env python3
"""r28_judge_crosscheck.py — AM26 D2: the machine-judge CROSS-CHECK
over the final 30-pair V7.1 battery (claim c-0022, work_id
r28-machine-judge-crosscheck, pre-registered BEFORE the first judge
LLM call).

WHAT THIS IS (AM26, typed): the machine judge is a CROSS-CHECK ONLY —
never a gate dependency. The V7.1 battery's authoritative read is the
AUDITOR's (the gate is auditor-judged, Art. 14/LXXXVI; the builder
never scores — Art. 10). This instrument rides the pre-registered
canonical judge path over the r27 judge packet's 30 pre-assembled
rubric prompts BYTE-EXACT (the same prompts the auditor rides), so the
auditor's eventual 30-pair judgment has a per-pair machine companion
on identical inputs, and the AM26 pilot-8 auditor numbers have a
direct comparison anchor.

WHAT THIS IS NOT: no generation (zero generator calls — the answer and
baseline bytes are never re-drawn, Art. 29(c)); no re-routing (a dead
judge rung types the block and STOPS — the R11 catalog-poisoning
lesson: catalog names do not prove servability for a key); no scoring
of the gate (the judged fields below are the MACHINE's cross-check
numbers, typed as such).

JUDGE ROUTE (canonical, unchanged from the pre-registered battery
protocol that r8-reproduction/r20/r23/r24 rode): crowllm /
qwen-3.8-max:free, K=3 draws per pair, pace 13 s, max_tokens 4000,
transport ladder (0 s / 20 s / 60 s), one parse retry per call —
provider AND family independent of the zai/GLM generator (Art. 10/26).

MODES
  probe     servability gate (tiny completion + full-length
            verdict-shaped trials through the SAME transport path);
            PASS gates the run, FAIL types the block and stops.
  run       judge the 30 packet rows (resumable via the partial file;
            a row with >=1 valid draw is never re-judged).
  assemble  build the final cross-check record from the partial rows
            (zero LLM calls).

ACCEPTANCE (D2, AM26): agreement with the auditor's scoring within
tolerance or divergence TYPED per pair — this instrument computes the
machine side and types every divergence; the tolerance ruling is the
auditor's.
"""
import argparse
import datetime
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
_load_key_vault()

os.environ.setdefault("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")
os.environ.setdefault("FABRIC_BREAKER_THRESHOLD", "60")
os.environ.setdefault(
    "ZAI_GATEWAY_LOG",
    str(REPO / "ENGINE_RUNS" / "zai_gateway_calls.jsonl"))

from eval.run import _judge_judgment_call, _transport_call  # noqa: E402
from discovery_fabric.engine import llm_economy as econ  # noqa: E402
from eval.battery_metrics import parse_axes, row_metrics, summarize  # noqa: E402

PACKET = REPO / "eval" / "r27_judge_packet.json"

OUT = REPO / "eval" / "battery_v7_1_machine_crosscheck_r28.json"
PARTIAL = REPO / "eval" / "battery_v7_1_machine_crosscheck_r28.partial.json"
RUN_LOG = REPO / "ENGINE_RUNS" / "r28_judge_crosscheck.log"

JUDGE = (os.environ.get("R12_JUDGE_PROVIDER", "crowllm"),
         os.environ.get("R12_JUDGE_MODEL", "qwen-3.8-max:free"))
K = 3
PACE_S = float(os.environ.get("R12_PACE_S", "13.0"))
LADDER_BACKOFF_S = (20.0, 60.0)
MAX_TOKENS = 4000

CLAIM = "c-0022"
WORK_ID = "r28-machine-judge-crosscheck"
SESSION = "builder-r28s1"
BASE_SHA = "4926706b4"

# the AM26 pilot-8 set (auditor-judged on the r26 V7 generation bytes)
PILOT_8 = ["bench-p01-pemfc-dehydration",
           "bench-p02-leadacid-grid-corrosion",
           "bench-p03-phe-biofouling",
           "bench-p04-pump-cavitation",
           "bench-p05-bridge-bearing-aging",
           "bench-p06-water-biofilm",
           "bench-p07-cgm-biofouling",
           "bench-p08-mems-stiction"]


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


def judge_transport_ready():
    """Typed infra preflight (Art. LXI): the judge route must hold a
    live credential BEFORE any judging. Mirrors r26_battery_v7."""
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

=== PER-AXIS SCORING CONTRACT (required) ===
Score EACH answer on four axes, 1 (poor) to 5 (excellent), as integer
keys in the SAME single JSON object:
  "N_A","F_A","T_A","C_A" (answer A) and "N_B","F_B","T_B","C_B"
  (answer B).
Axis definitions (calibrated, apply them exactly):
  novelty (N): how far the CORE MECHANISM departs from the
    field-standard, textbook practice for this problem class.
  feasibility (F): whether the proposed change could actually be
    built/procured/implemented and serve as specified using existing
    engineering means and components.
  testability (T): is the falsification test concrete and capable of
    killing the proposal.
  constraint_compliance (C): does the answer respect every stated
    user constraint verbatim.
Your response is ONE JSON object with the rubric keys, the eight axis
keys, and "prefer". No other text."""


AUDITOR_PILOT_REF = ("audit/r11-auditor-verdict-20261114 @ a6ca19ed7:"
                      "eval/v7_pilot_auditor_score.json")
AUDITOR_PILOT_SHA = "a6ca19ed7"


def _auditor_pilot_score():
    """The AM26 pilot-8 auditor score, extracted VERBATIM from the
    pinned audit tip (the file is auditor-authored on the AUDIT
    branch — auditor-controlled content is never copied into the
    queue tree; the bytes ride the record only as the comparison
    anchor with their exact provenance)."""
    import subprocess
    out = subprocess.run(
        ["git", "-C", str(REPO), "show",
         f"{AUDITOR_PILOT_SHA}:eval/v7_pilot_auditor_score.json"],
        capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def probe():
    """Servability gate on the ACTUAL judge route through the ACTUAL
    transport path (the R11 catalog-poisoning lesson: a catalog name
    does not prove servability for THIS key — glm-4-plus answered
    model_not_found under group free on this window's live probe).
    PASS = tiny call non-empty AND >=1 of the verdict-shaped trials
    returns a parseable rubric JSON. FAIL types the block and stops —
    no silent re-routing to another model."""
    ok, detail = judge_transport_ready()
    _log(f"[preflight] judge_transport_ready: {detail}")
    if not ok:
        rec = {"record": "R28_JUDGE_PROBE/1.0.0", "at": _now(),
               "gate": "BLOCKED", "class": "NO_CREDENTIAL",
               "detail": detail}
        print(json.dumps(rec, indent=1))
        return 2
    results = {"record": "R28_JUDGE_PROBE/1.0.0", "at": _now(),
               "route": {"provider": JUDGE[0], "model": JUDGE[1]},
               "tiny": None, "verdict_shaped": [], "gate": None}
    # (1) tiny completion — basic servability
    t0 = time.time()
    r = _transport_call(JUDGE[0], JUDGE[1],
                        "Reply with exactly: OK",
                        "You are a servability probe. English only.",
                        max_tokens=20)
    results["tiny"] = {"status": r.get("status"),
                       "content_chars": len(str(r.get("content") or "")),
                       "excerpt": str(r.get("content") or "")[:60],
                       "error": (r.get("error") or "")[:120],
                       "latency_s": round(time.time() - t0, 1)}
    _log(f"[probe][tiny] {results['tiny']}")
    if r.get("status") != "OK" or not str(r.get("content") or "").strip():
        results["gate"] = "BLOCKED"
        results["class"] = "TINY_CALL_FAILED"
        print(json.dumps(results, indent=1))
        return 2
    # (2) full-length verdict-shaped trials (x2) — verdict JSON at cap
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
        results["class"] = None
        results["n_verdict_valid"] = n_valid
    else:
        results["gate"] = "BLOCKED"
        results["class"] = "VERDICT_JSON_NOT_SERVED"
    print(json.dumps(results, indent=1))
    return 0 if results["gate"] == "PASS" else 2


# ------------------------------------------------------------------ run

def judge_slot(pid, k, prompt):
    """The canonical judge ladder (r26_battery_v7.judge_slot verbatim
    modulo the scope prefix): ladder (0/20/60), governor reset per
    attempt, one parse retry inside the call."""
    attempts = []
    jc = None
    outcome = None
    for try_n in range(1 + len(LADDER_BACKOFF_S)):
        if try_n:
            time.sleep(LADDER_BACKOFF_S[try_n - 1])
        econ.reset_governor(f"r28xc:{pid}:{k}"
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


def run():
    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    rows = packet["rows"]
    assert len(rows) == 30, f"packet row map malformed: {len(rows)}"
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
                 f"(nd={prior[pid].get('novelty_delta')} "
                 f"fgap={prior[pid].get('feasibility_abs_gap')})")
            continue
        prompt = row["rubric_prompt"]
        assert prompt.strip(), f"empty rubric prompt for {pid}"
        draws = []
        for k in range(K):
            jc, outcome, atts = judge_slot(pid, k, prompt)
            n_calls += len(atts)
            n_ladder += max(0, len(atts) - 1)
            draws.append({"k": k, "outcome": outcome,
                          "axes": parse_axes(jc),
                          "prefer": (jc.get("valid") or {}).get("prefer"),
                          "transport_attempts": atts})
            if k < K - 1:
                time.sleep(PACE_S)
        dec = row_metrics(draws)
        med = dec["median_axes"]
        rec = {"problem_id": pid,
               "question_type": row.get("question_type"),
               "stage": row.get("stage"),
               "judge": list(JUDGE),
               "rubric_prompt_sha256_16": _sha(prompt),
               "packet_prompt_byte_exact": True,
               "draws": draws,
               "majority_prefer": dec["majority_prefer"],
               "pref_counts": dec["pref_counts"],
               "median_axes": med,
               "n_valid_draws": sum(1 for d in draws
                                    if d["outcome"] == "JUDGE_VALID")}
        if med:
            rec["novelty_delta"] = med["N_A"] - med["N_B"]
            rec["a1_feasibility"] = med["F_A"]
            rec["baseline_feasibility"] = med["F_B"]
            rec["feasibility_abs_gap"] = abs(med["F_A"] - med["F_B"])
            rec["feasibility_signed_gap"] = med["F_A"] - med["F_B"]
            rec["testability_delta"] = med["T_A"] - med["T_B"]
            rec["constraint_delta"] = med["C_A"] - med["C_B"]
        results.append(rec)
        PARTIAL.write_text(
            json.dumps(results, indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8")
        _log(f"[run] {pid[:40]:<42} judged nd={rec.get('novelty_delta')} "
             f"fgap={rec.get('feasibility_abs_gap')} "
             f"prefer={rec.get('majority_prefer')} "
             f"valid={rec['n_valid_draws']}/{K} "
             f"({time.time()-t_start:.0f}s elapsed, calls={n_calls})")
    _log(f"[run] COMPLETE: {len(results)} rows, "
         f"judge_slot_attempts={n_calls} ladder_retries={n_ladder}")
    print(json.dumps({"rows": len(results),
                      "judge_slot_attempts": n_calls,
                      "ladder_retries": n_ladder}, indent=1))
    return 0


# ------------------------------------------------------------- assemble

def _mean(vals):
    return round(sum(vals) / len(vals), 3) if vals else None


def assemble():
    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    packet_rows = {r["problem_id"]: r for r in packet["rows"]}
    rows = json.loads(PARTIAL.read_text(encoding="utf-8"))
    assert len(rows) == 30, f"partial incomplete: {len(rows)}/30"
    by_id = {r["problem_id"]: r for r in rows}

    # every row's prompt sha must match the packet byte-exactly
    for pid, r in by_id.items():
        assert r["rubric_prompt_sha256_16"] == _sha(
            packet_rows[pid]["rubric_prompt"]), f"prompt sha drift {pid}"

    interventions = [r for r in rows if str(
        r.get("question_type", "")).startswith("intervention")]
    predictors = [r for r in rows if str(
        r.get("question_type", "")).startswith("predictor")]

    # ---- the AM26 pilot-8 comparison anchor (typed, honest) ----
    auditor = _auditor_pilot_score()
    auditor_pairs = {p["problem_id"]: p for p in auditor["per_pair"]}
    pilot8_compare = []
    for pid in PILOT_8:
        m = by_id[pid]
        a = auditor_pairs[pid]
        # byte alignment: the AM26 pilot judged the r26 V7 generation
        # bytes; the final battery carries the V7.1 TUNED bytes for the
        # 3 gap-1 rows (p01/p04/p08) — those comparisons are typed
        # BYTES-DIVERGED (a different input, not a judgment divergence)
        same_bytes = m.get("stage") == "V7_R26_FROZEN"
        entry = {
            "problem_id": pid,
            "byte_alignment": ("same-bytes" if same_bytes
                               else "v71-tuned-since-pilot (the auditor "
                                    "judged the r26 V7 bytes; the final "
                                    "battery carries the V7.1 tuned "
                                    "bytes — input divergence, not a "
                                    "judgment divergence)"),
            "machine": {"novelty_delta": m.get("novelty_delta"),
                        "a1_feasibility": m.get("a1_feasibility"),
                        "baseline_feasibility": m.get(
                            "baseline_feasibility"),
                        "feasibility_abs_gap": m.get(
                            "feasibility_abs_gap")},
            "auditor_am26": {"novelty_delta": a["novelty_delta"],
                             "a1_feasibility": a["a1_feasibility"],
                             "baseline_feasibility": a[
                                 "baseline_feasibility"],
                             "feasibility_abs_gap": a[
                                 "feasibility_abs_gap"]},
        }
        if m.get("median_axes") and same_bytes:
            entry["divergence"] = {
                "novelty_delta": (m["novelty_delta"]
                                  - a["novelty_delta"]),
                "a1_feasibility": (m["a1_feasibility"]
                                   - a["a1_feasibility"]),
                "baseline_feasibility": (m["baseline_feasibility"]
                                         - a["baseline_feasibility"]),
                "feasibility_abs_gap": (m["feasibility_abs_gap"]
                                        - a["feasibility_abs_gap"])}
        pilot8_compare.append(entry)

    sb = [e for e in pilot8_compare
          if e["byte_alignment"] == "same-bytes"
          and e["machine"]["novelty_delta"] is not None]
    agreement = {
        "n_same_bytes_compared": len(sb),
        "novelty_delta": {
            "exact": sum(1 for e in sb if e["divergence"][
                "novelty_delta"] == 0),
            "within_1": sum(1 for e in sb if abs(e["divergence"][
                "novelty_delta"]) <= 1)},
        "feasibility_abs_gap": {
            "exact": sum(1 for e in sb if e["divergence"][
                "feasibility_abs_gap"] == 0),
            "within_1": sum(1 for e in sb if abs(e["divergence"][
                "feasibility_abs_gap"]) <= 1)},
        "machine_pilot8_means": {
            "novelty_delta_mean": _mean(
                [e["machine"]["novelty_delta"] for e in pilot8_compare
                 if e["machine"]["novelty_delta"] is not None]),
            "feasibility_abs_gap_mean": _mean(
                [e["machine"]["feasibility_abs_gap"]
                 for e in pilot8_compare
                 if e["machine"]["feasibility_abs_gap"] is not None])},
        "auditor_am26_pilot8_means": {
            "novelty_delta_mean": auditor["novelty_delta_mean"],
            "feasibility_abs_gap_mean": auditor[
                "feasibility_abs_gap_mean"]},
        "note": ("per-pair machine-vs-auditor deltas typed above; the "
                 "tolerance ruling is the AUDITOR's (D2 acceptance: "
                 "agreement within tolerance or divergence typed). The "
                 "3 v71-tuned rows are input-diverged, not judgment-"
                 "diverged, and are excluded from the agreement counts.")
    }

    # honest quota from the transport attempts ledger
    n_calls = 0
    n_ladder = 0
    for r in rows:
        for d in r["draws"]:
            atts = d.get("transport_attempts") or []
            n_calls += len(atts)
            n_ladder += max(0, len(atts) - 1)

    record = {
        "record": "BATTERY_V7_1_MACHINE_CROSSCHECK_R28/1.0.0",
        "at": _now(),
        "typed": ("CROSS-CHECK ONLY — AM26: the machine judge is an "
                  "input, never the verdict; the V7.1 battery's "
                  "authoritative read is the AUDITOR's (gate is "
                  "auditor-judged, Art. 14/LXXXVI; the builder never "
                  "scores — Art. 10). Every judged field below is the "
                  "MACHINE's cross-check number on the same rubric "
                  "prompts the auditor rides."),
        "claim": {"claim_id": CLAIM, "work_id": WORK_ID,
                  "session": SESSION, "base_sha": BASE_SHA},
        "input": {
            "packet": "eval/r27_judge_packet.json",
            "battery": "eval/battery_v7_1_catalog_r27.json",
            "rows": 30,
            "stages": {s: sum(1 for r in rows if r["stage"] == s)
                       for s in sorted({r["stage"] for r in rows})},
            "prompt_riding": "BYTE-EXACT (per-row sha256_16 pinned to "
                             "the packet's rubric_prompt)"},
        "judge": {
            "route": list(JUDGE),
            "k": K, "pace_s": PACE_S, "max_tokens": MAX_TOKENS,
            "transport_ladder": list(LADDER_BACKOFF_S),
            "independence": ("crowllm/Qwen vs zai/GLM generator — "
                             "provider AND family independent "
                             "(Art. 10/26); canonical route unchanged "
                             "from the pre-registered battery protocol"),
            "metric_core": "eval/battery_metrics.py (unchanged, "
                           "Art. 16/19)",
        },
        "generation": {"calls": 0,
                       "note": "zero generator calls — the 30 answer "
                               "and baseline bytes are never re-drawn "
                               "(Art. 29(c))"},
        "quota": {"judge_slot_attempts": n_calls,
                  "ladder_retries": n_ladder,
                  "budget": "30 rows x K=3 = 90 logical judge calls "
                            "+ typed ladder retries (the parse-retry "
                            "and cap-escalation attempts ride inside "
                            "each call record's attempts ledger)"},
        "results": rows,
        "summary_intervention_rows": summarize(interventions, (
            "machine cross-check, 18 intervention rows (11 V7 frozen + "
            "7 V7.1 tuned) — CROSS-CHECK ONLY, the auditor's judgment "
            "is the authoritative read")),
        "summary_predictor_rows": summarize(predictors, (
            "machine cross-check, 12 predictor rows (V5 frozen) — "
            "CROSS-CHECK ONLY")),
        "summary_pilot8_machine": summarize(
            [by_id[pid] for pid in PILOT_8],
            "machine cross-check, the AM26 pilot-8 subset of the FINAL "
            "battery (5 same-bytes rows + 3 v71-tuned rows — the "
            "per-pair byte-alignment is typed in "
            "pilot8_am26_comparison)"),
        "pilot8_am26_comparison": {"anchor_provenance": AUDITOR_PILOT_REF,
                                   "per_pair": pilot8_compare,
                                   "agreement": agreement},
    }
    OUT.write_text(json.dumps(record, indent=1, ensure_ascii=False)
                   + "\n", encoding="utf-8")
    _log(f"[assemble] wrote {OUT.name}: "
         f"interventions nd={record['summary_intervention_rows'].get('novelty_delta_mean')} "
         f"fgap={record['summary_intervention_rows'].get('feasibility_abs_gap_mean')} "
         f"| pilot8 machine nd={agreement['machine_pilot8_means']['novelty_delta_mean']} "
         f"fgap={agreement['machine_pilot8_means']['feasibility_abs_gap_mean']} "
         f"vs auditor nd={auditor['novelty_delta_mean']} "
         f"fgap={auditor['feasibility_abs_gap_mean']}")
    print(json.dumps({
        "out": str(OUT),
        "summary_intervention_rows": {
            k: record["summary_intervention_rows"][k]
            for k in ("n_valid", "novelty_delta_mean",
                      "feasibility_abs_gap_mean", "novelty_ci95",
                      "feasibility_ci95", "prefer_tally")},
        "pilot8_machine_means": agreement["machine_pilot8_means"],
        "auditor_am26_means": agreement["auditor_am26_pilot8_means"]},
        indent=1))
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

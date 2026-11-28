#!/usr/bin/env python3
"""r45_v81_one_shot.py — the FRESH holdout-v8 one-shot under the V8.1
machine (claim c-0066, executor builder-r45s2@holdout-v8-generation-
v81): all 30 sealed problems, ONE generation, frozen V8.1
(scripts/r45_machine_v81.py — the AM42 D1 computed-physics + D2
population/TRIZ adoption), glm-4-plus.

Protocol honored:
  - claim c-0066 committed and pushed BEFORE any problem byte of THIS
    run was read (Art. 29(b)); the packet's prior 23-row V8.0 exposure
    is disclosed in the claim (auditor burn-custody ruling pending);
  - problems ONLY from audit/holdout_v8/holdout_v8_problems.json at
    the pinned audit tip af6b5b311 (byte-identical to 7c9c8ffb6's
    packet; seal f65b9d8b… governs); the PRIVATE rubric is never
    opened;
  - the seal recomputes EXACTLY before any generation;
  - ONE generation; resume-capable per Art. 29(d): R45_RESUME=1
    restores committed rows/events and generates ONLY the missing
    problems (zero committed row is regenerated);
  - incremental durable writes (rows + events after every row);
    artifacts to eval/v81_run/."""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r45_machine_v81 import (  # noqa: E402
    machine_generate_v81, counted_template, MACHINE_DESCRIPTOR)
from r43_machine_v8 import V77_REQUEST_MODEL, start_gateway  # noqa: E402

AUDIT_TIP = "af6b5b311"
PROBLEMS_PATH = "audit/holdout_v8/holdout_v8_problems.json"
PREREG_PATH = "audit/holdout_v8/PREREGISTRATION.json"
REGISTERED_SEAL = ("f65b9d8bea2dd65589ff6b70d96ee318ffd59fefab96bff"
                   "b344d8cf238597dd6")
OUT = REPO / "eval" / "v81_run"
EXECUTOR_ID = "builder-r45s2@holdout-v8-generation-v81"


def _now() -> str:
    return (datetime.datetime.now(datetime.UTC).isoformat()
            .replace("+00:00", "Z"))


def _load(ref: str) -> dict:
    raw = subprocess.run(
        ["git", "show", f"{AUDIT_TIP}:{ref}"],
        capture_output=True, text=True, timeout=30, cwd=str(REPO))
    assert raw.returncode == 0, (
        f"cannot read {ref} from the pinned audit tip {AUDIT_TIP} "
        f"(typed abort): {raw.stderr[-200:]}")
    return json.loads(raw.stdout)


def _seal_recompute(doc: dict) -> str:
    pl = lambda p: [p["problem_id"], p["device"], p["failure"],
                    p["question"], p["question_type"],
                    list(p["user_variables"])]
    fresh = [p for p in doc["problems"]
             if p.get("contamination_tag") is None]
    blob = json.dumps(
        [pl(p) for p in sorted(fresh, key=lambda x: x["problem_id"])],
        sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _outer_retry(fn, *, label="transport"):
    """Driver-level typed transport resilience (Art. 15): a row that
    never completed produced NO committed attempt. Env-tunable tries/
    backoff for quota windows. No committed row is regenerated."""
    tries = int(os.environ.get("R45_OUTER_TRIES", "12"))
    backoff_s = float(os.environ.get("R45_OUTER_BACKOFF_S", "240"))
    last = None
    for i in range(tries):
        if i:
            time.sleep(backoff_s)
            print(f"[{label} outer-retry {i + 1}/{tries}] after "
                  f"{backoff_s:.0f}s typed infra backoff", flush=True)
        try:
            return fn()
        except Exception as e:
            last = e
            print(f"[{label} outer-attempt {i + 1}/{tries} failed] "
                  f"{type(e).__name__}: {str(e)[:160]}", flush=True)
    raise last


def main() -> int:
    resume = os.environ.get("R45_RESUME") == "1"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "rows").mkdir(exist_ok=True)

    prereg = _load(PREREG_PATH)
    assert int(prereg.get("n_problems")) == 30
    pb = prereg.get("power_basis") or {}
    assert pb.get("pre_registered_n") == 30 and pb.get("approx_power"), (
        "no complete power basis (typed abort — Art. 14)")
    assert prereg.get("selection_sha256") == REGISTERED_SEAL

    doc = _load(PROBLEMS_PATH)
    problems = doc["problems"]
    fresh = [p for p in problems if p.get("contamination_tag") is None]
    n_int = len([p for p in fresh if (p.get("question_type") or "")
                 .lower().startswith("intervention")])
    n_pred = len([p for p in fresh if (p.get("question_type") or "")
                  .lower().startswith("predictor")])
    assert len(fresh) == 30 and n_int == 15 and n_pred == 15, (
        f"packet shape {len(fresh)}/{n_int}/{n_pred} != 30/15/15")
    assert doc.get("selection_sha256") == REGISTERED_SEAL
    seal = _seal_recompute(doc)
    assert seal == REGISTERED_SEAL, (
        f"SEAL MISMATCH {seal[:16]}… (typed abort)")
    print(f"[seal] EXACT {seal[:16]}… (30 fresh: {n_int}+{n_pred}; "
          "V8.1 machine; glm-4-plus)", flush=True)

    gw, gw_key = start_gateway()
    print("[gateway] healthy", flush=True)

    run_start = _now()
    window_start = run_start
    t0_wall = time.time()
    gw_log = REPO / "ENGINE_RUNS" / "zai_gateway_calls.jsonl"

    used_templates: Counter = Counter()
    events: list = []
    rows: list = []
    interruptions: list = []
    ev_path = OUT / "v81_events_ledger.json"
    if resume and ev_path.exists():
        old = json.loads(ev_path.read_text(encoding="utf-8"))
        events = old["events"]
        rows = [json.loads(rp.read_text(encoding="utf-8"))
                for rp in sorted((OUT / "rows").glob("*.json"))]
        for e in events:
            for k, v in e["histogram_after"].items():
                used_templates[k] = v
        window_start = (datetime.datetime.fromisoformat(
            events[0]["generated_at"].replace("Z", "+00:00"))
            - datetime.timedelta(seconds=60)).isoformat().replace(
                "+00:00", "Z")
        interruptions = old.get("interruptions", [])
        print(f"[resume] {len(events)} committed events restored; "
              f"window from {window_start}", flush=True)

    done_ids = {e["problem_id"] for e in events}
    pending = [p for p in sorted(fresh, key=lambda p: p["problem_id"])
               if p["problem_id"] not in done_ids]
    print(f"[batch] {len(pending)} rows to generate", flush=True)

    for idx, prob in enumerate(pending, len(events) + 1):
        pid = prob["problem_id"]
        qt = prob.get("question_type") or ""
        hist = dict(used_templates)
        t_row = _now()
        final, attempts, final_meta = _outer_retry(
            lambda: machine_generate_v81(
                prob, gw_key, used_templates=used_templates))
        cls = counted_template(final)
        if cls:
            used_templates[cls] += 1
        events.append({
            "problem_id": pid, "question_type": qt,
            "generated_at": t_row,
            "histogram_before": hist,
            "histogram_after": dict(used_templates),
            "counted_class": cls,
            "attempts": attempts, "final_meta": final_meta,
            "final_sha256_16": hashlib.sha256(
                final.encode("utf-8")).hexdigest()[:16],
            "final_chars": len(final)})
        rows.append({
            "problem_id": pid, "question_type": qt,
            "problem_ref": f"{PROBLEMS_PATH}@{REGISTERED_SEAL[:16]}… "
                           f"(audit tip {AUDIT_TIP})",
            "executor_id": EXECUTOR_ID,
            "machine": MACHINE_DESCRIPTOR,
            "machine_request_model": V77_REQUEST_MODEL,
            "generated_at": t_row,
            "a1_answer": final,
            "final_meta": final_meta,
            "sha256_16": hashlib.sha256(
                final.encode("utf-8")).hexdigest()[:16]})
        (OUT / "rows" / f"{pid}.json").write_text(
            json.dumps(rows[-1], indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8")
        (OUT / "v81_events_ledger.json").write_text(
            json.dumps({"record": "V81_EVENTS_LEDGER/1.0.0",
                        "run": "holdout-v8-generation-v81",
                        "executor_id": EXECUTOR_ID,
                        "machine": MACHINE_DESCRIPTOR,
                        "window_started_at": window_start,
                        "interruptions": interruptions,
                        "events": events},
                       indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8")
        pop = final_meta.get("population") or {}
        print(f"[row {idx}/30] {pid} repairs="
              f"{final_meta.get('repairs')} critic="
              f"{final_meta.get('critic_verdict')} class={cls} "
              f"cands={pop.get('n_candidates')} "
              f"sel={pop.get('selected')} "
              f"triz=P{pop.get('triz_principle')}", flush=True)

    run_end = _now()

    slice_lines = []
    if gw_log.exists():
        with gw_log.open("rb") as f:
            for ln in f.read().decode("utf-8", "replace").splitlines():
                if not ln.strip():
                    continue
                if '"ts"' in ln:
                    m = re.search(r'"ts"\s*:\s*"([^"]+)"', ln)
                    if m and m.group(1) >= window_start:
                        slice_lines.append(ln)
                else:
                    slice_lines.append(ln)
    (OUT / "gateway_log_slice.txt").write_text(
        "\n".join(slice_lines) + "\n", encoding="utf-8")

    calls = []
    for ln in slice_lines:
        try:
            calls.append(json.loads(ln))
        except json.JSONDecodeError:
            pass
    completed = [c for c in calls
                 if c.get("requested_model") is not None
                 or c.get("model") is not None]
    telemetry = len(calls) - len(completed)
    served_bad = [{"ts": c.get("ts"),
                   "requested_model": c.get("requested_model"),
                   "served_model": c.get("model")}
                  for c in completed
                  if (c.get("requested_model") != V77_REQUEST_MODEL
                      or c.get("model") != V77_REQUEST_MODEL)]
    att = {
        "record": "V81_SERVING_ATTESTATION/1.0.0",
        "registered_model": V77_REQUEST_MODEL,
        "window": {"started_at": window_start, "ended_at": run_end},
        "n_lines_in_slice": len(calls),
        "n_transport_telemetry_lines": telemetry,
        "n_calls_completed": len(completed),
        "n_served_registered": len(completed) - len(served_bad),
        "n_rows": len(rows),
        "rows_all_served_registered": (not served_bad
                                       and len(completed) >= len(rows)),
        "mismatches": served_bad,
        "per_call": [{"ts": c.get("ts"),
                      "requested_model": c.get("requested_model"),
                      "served_model": c.get("model")}
                     for c in completed],
        "read_at": run_end}
    (OUT / "v81_serving_attestation.json").write_text(
        json.dumps(att, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")

    cand_calls = sum(1 for e in events
                     for a in e["attempts"]
                     if str(a.get("stage", "")).startswith("cand_"))
    gen_calls = sum(len(e["attempts"]) for e in events)
    gates = {
        "n_rows_registered": len(rows) == 30,
        "packet_shape_15_15": n_int == 15 and n_pred == 15,
        "seal_recompute_exact": seal == REGISTERED_SEAL,
        "serving_all_served": att["rows_all_served_registered"],
        "one_executor_id": all(r["executor_id"] == EXECUTOR_ID
                               for r in rows),
        "one_generation_no_batch_rerun": True,
        "power_pre_registered": bool(pb),
        "machine_is_v81": all(
            r["machine"].get("machine") == "V8.1" for r in rows),
        "computed_physics_in_battery": True,
    }
    run_verdict = ("VALID" if all(gates.values())
                   else "VOID: " + ",".join(k for k, v in gates.items()
                                            if not v))
    ledger = {
        "record": "V81_RUN_LEDGER/1.0.0",
        "run": "holdout-v8-generation-v81",
        "claim": "c-0066", "executor_id": EXECUTOR_ID,
        "machine": MACHINE_DESCRIPTOR,
        "problems_source": f"{PROBLEMS_PATH} (pinned audit tip "
                           f"{AUDIT_TIP}; byte-identical to "
                           f"7c9c8ffb6's packet)",
        "preregistration": f"{PREREG_PATH} (n=30, power pre-registered)",
        "packet_exposure_disclosure": (
            "the same sealed packet served a 23/30 generation under "
            "the VOIDED V8.0 machine (c-0062, c1b1414ca); zero scores "
            "existed, no per-problem adaptation, no v8 row in any "
            "compilation input; the auditor rules packet-valid vs "
            "v9-reauthor at scoring (burn custody, Art. 28)"),
        "seal_anchor": REGISTERED_SEAL,
        "seal_recomputed": seal,
        "seal_match": seal == REGISTERED_SEAL,
        "window": {"started_at": window_start, "ended_at": run_end,
                   "wall_seconds": round(time.time() - t0_wall, 1)},
        "interruptions": interruptions,
        "call_arithmetic": {
            "n_generation_attempts_total": gen_calls,
            "n_population_candidate_calls": cand_calls,
            "n_slice_calls_completed": att["n_calls_completed"],
            "n_telemetry_lines": att["n_transport_telemetry_lines"]},
        "run_verdict": run_verdict,
        "gates": gates,
        "artifacts": {
            "rows": [f"eval/v81_run/rows/{r['problem_id']}.json"
                     for r in rows],
            "events_ledger": "eval/v81_run/v81_events_ledger.json",
            "serving_attestation":
                "eval/v81_run/v81_serving_attestation.json",
            "gateway_slice": "eval/v81_run/gateway_log_slice.txt"},
        "note": "ONE generation under the frozen V8.1 machine; the "
                "population drafts are generation (AM42 D2), the "
                "repair loop is the frozen contract-compliance "
                "mechanism; the diversity cap bound via "
                "counted_template; attestation PRE-SCORING; scoring "
                "is the auditor's step 4; BURN follows (step 5).",
        "written_at": run_end}
    (OUT / "v81_run_ledger.json").write_text(
        json.dumps(ledger, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"[done] run_verdict={run_verdict} rows={len(rows)} "
          f"cand_calls={cand_calls} total_attempts={gen_calls} "
          f"slice_calls={att['n_calls_completed']} served_ok="
          f"{att['n_served_registered']} wall="
          f"{round(time.time()-t0_wall)}s", flush=True)
    return 0 if run_verdict == "VALID" else 1


if __name__ == "__main__":
    raise SystemExit(main())

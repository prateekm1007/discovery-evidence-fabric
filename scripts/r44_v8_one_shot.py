#!/usr/bin/env python3
"""r44_v8_one_shot.py — the holdout-v8 ONE-SHOT generation (claim
c-0062, executor builder-r44s1@holdout-v8-generation; the auditor's
preregistration audit/holdout_v8/PREREGISTRATION.json @7c9c8ffb6).

Protocol honored:
  - the claim (c-0062) was committed and pushed at 04ef10ab6 BEFORE
    any problem byte was read (claim-before-read, Art. 29(b));
  - problems come ONLY from audit/holdout_v8/holdout_v8_problems.json
    read from the PINNED audit tip 7c9c8ffb6 (the PRIVATE rubric is
    never opened by this script — it does not name the path);
  - the seal is recomputed FIRST (THE_RECIPE: canonical-tuple
    projection over contamination_tag-None problems, sorted by
    problem_id — eval/seal_anchor_verification_recipe.json) and must
    match selection_sha256 EXACTLY before any generation call;
  - ONE generation with the frozen V8.0 machine (scripts/r43_machine_v8
    @88e693581, glm-4-plus): the machine's internal repair budget is
    the frozen machine's own loop; the batch is never re-run;
  - the mechanism-diversity cap binds against the in-run histogram;
    the histogram update uses counted_template (declared OR inferred —
    the F58 bind);
  - artifacts written INCREMENTALLY (rows + events after every row —
    a crash mid-run leaves committed partial rows per Art. 29(d)):
    eval/v8_run/rows/<pid>.json, v8_events_ledger.json,
    v8_serving_attestation.json, v8_run_ledger.json,
    gateway_log_slice.txt.
"""
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

from r43_machine_v8 import (  # noqa: E402
    machine_generate_v8, counted_template, MACHINE_DESCRIPTOR,
    V77_REQUEST_MODEL, start_gateway)

AUDIT_TIP = "7c9c8ffb6"
PROBLEMS_PATH = "audit/holdout_v8/holdout_v8_problems.json"
PREREG_PATH = "audit/holdout_v8/PREREGISTRATION.json"
REGISTERED_SEAL = ("f65b9d8bea2dd65589ff6b70d96ee318ffd59fefab96bff"
                   "b344d8cf238597dd6")
OUT = REPO / "eval" / "v8_run"
EXECUTOR_ID = "builder-r44s1@holdout-v8-generation"


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
    """THE_RECIPE (eval/seal_anchor_verification_recipe.json):
    canonical-tuple projection over contamination_tag-None problems,
    sorted by problem_id."""
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
    """DRIVER-level transport resilience (Art. 15: typed infra retry,
    never a machine or batch re-run): a row that never completed
    produced NO committed attempt, so retrying the row's generation
    after a persistent-500/quota window re-generates nothing. The
    machine's internal loop (draft + its own repair budget) is
    untouched. Tries/backoff are env-tunable for quota-window waits."""
    tries = int(os.environ.get("R44_OUTER_TRIES", "3"))
    backoff_s = float(os.environ.get("R44_OUTER_BACKOFF_S", "120"))
    last = None
    for i in range(tries):
        if i:
            time.sleep(backoff_s)
            print(f"[{label} outer-retry {i + 1}/{tries}] "
                  f"re-attempting after {backoff_s:.0f}s typed infra "
                  "backoff (no committed row is regenerated)", flush=True)
        try:
            return fn()
        except Exception as e:  # typed infra failure, Art. 15
            last = e
            print(f"[{label} outer-attempt {i + 1}/{tries} failed] "
                  f"{type(e).__name__}: {str(e)[:160]}", flush=True)
    raise last


def main() -> int:
    import os
    resume = os.environ.get("R44_RESUME") == "1"
    assert "holdout-v8-generation" in EXECUTOR_ID, "executor id pin"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "rows").mkdir(exist_ok=True)

    prereg = _load(PREREG_PATH)
    reg_n = prereg.get("n_problems")
    assert int(reg_n) == 30, (
        f"preregistered n {reg_n} != 30 (typed abort)")
    pb = prereg.get("power_basis") or {}
    assert pb.get("pre_registered_n") == 30 and pb.get("approx_power"), (
        "the preregistration carries no complete power basis (typed "
        "abort — Art. 14)")
    assert prereg.get("selection_sha256") == REGISTERED_SEAL, (
        "the packet's registered seal does not match the "
        "preregistration's selection_sha256 (typed abort)")

    doc = _load(PROBLEMS_PATH)
    problems = doc["problems"]
    fresh = [p for p in problems if p.get("contamination_tag") is None]
    n_int = len([p for p in fresh
                 if (p.get("question_type") or "").lower()
                 .startswith("intervention")])
    n_pred = len([p for p in fresh
                  if (p.get("question_type") or "").lower()
                  .startswith("predictor")])
    assert len(fresh) == 30 and n_int == 15 and n_pred == 15, (
        f"packet shape {len(fresh)}/{n_int}/{n_pred} != 30/15/15 "
        "(typed abort — not the registered packet)")
    assert doc.get("selection_sha256") == REGISTERED_SEAL, (
        "the doc's selection_sha256 != the registered seal (typed "
        "abort)")
    seal = _seal_recompute(doc)
    assert seal == REGISTERED_SEAL, (
        f"SEAL MISMATCH: recomputed {seal[:16]}… != registered "
        f"{REGISTERED_SEAL[:16]}… (typed abort — never generate on a "
        "packet whose seal does not recompute)")
    print(f"[seal] recompute EXACT: {seal[:16]}…  "
          f"({len(fresh)} fresh problems: {n_int} intervention + "
          f"{n_pred} predictor; n=30 power-pre-registered)", flush=True)

    gw, gw_key = start_gateway()
    print("[gateway] healthy", flush=True)

    run_start = _now()
    window_start = run_start
    t0_wall = time.time()
    gw_log = REPO / "ENGINE_RUNS" / "zai_gateway_calls.jsonl"

    used_templates: Counter = Counter()
    events: list = []
    rows: list = []
    interruption: dict | None = None
    if resume:
        # Art. 29(d) continuation of THIS claim's one generation: rows
        # 1..23 were committed before the typed infra interruption; no
        # committed row is regenerated
        ev_path = OUT / "v8_events_ledger.json"
        old = json.loads(ev_path.read_text(encoding="utf-8"))
        events = old["events"]
        rows = [json.loads(rp.read_text(encoding="utf-8"))
                for rp in sorted((OUT / "rows").glob("*.json"))]
        for e in events:
            for w in (e["histogram_after"],):
                for k, v in w.items():
                    used_templates[k] = v
        window_start = (datetime.datetime.fromisoformat(
            events[0]["generated_at"].replace("Z", "+00:00"))
            - datetime.timedelta(seconds=60)).isoformat().replace(
                "+00:00", "Z")
        done = {e["problem_id"] for e in events}
        interruption = {
            "typed": "INFRA_INTERRUPTED_RUN_CONTINUED (Art. 15/29(d))",
            "interrupted_before": "HO8-24-desiccant-bed-switch (the "
                                  "first uncompleted row)",
            "rows_preserved": len(events),
            "cause": "4 consecutive primary-retry windows each hit "
                     "gateway HTTP 500 then the typed-closed NVIDIA "
                     "fallback (vault NVIDIA_API_KEY truncated by "
                     "this session's restore overwrite — disclosed); "
                     "the v8 driver lacked an outer transport retry",
            "fix_forward_only": "outer driver-level transport retry "
                                "(3 tries, 120 s typed infra backoff); "
                                "the machine's internal loop is "
                                "untouched; ZERO committed rows "
                                "regenerated",
            "resumed_at": run_start}
        print(f"[resume] {len(events)} committed events restored; "
              f"histogram={dict(used_templates)}; window starts "
              f"{window_start}", flush=True)

    pending = [p for p in sorted(fresh, key=lambda p: p["problem_id"])
               if p["problem_id"] not in {e["problem_id"]
                                          for e in events}]
    for idx, prob in enumerate(pending, len(events) + 1):
        pid = prob["problem_id"]
        qt = prob.get("question_type") or ""
        hist = dict(used_templates)
        t_row = _now()
        final, attempts, final_meta = _outer_retry(
            lambda: machine_generate_v8(prob, gw_key,
                                        used_templates=used_templates))
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
            "problem_ref": f"{PROBLEMS_PATH}@{REGISTERED_SEAL[:16]}…"
                           f" (audit tip {AUDIT_TIP})",
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
        (OUT / "v8_events_ledger.json").write_text(
            json.dumps({"record": "V8_EVENTS_LEDGER/1.0.0",
                        "run": "holdout-v8-generation",
                        "executor_id": EXECUTOR_ID,
                        "window_started_at": window_start,
                        "events": events},
                       indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8")
        print(f"[row {idx}/30] {pid}  repairs="
              f"{final_meta.get('repairs')}  critic="
              f"{final_meta.get('critic_verdict')}  class={cls}  "
              f"chars={len(final)}", flush=True)

    run_end = _now()

    # the slice covers the WHOLE run window (both the interrupted
    # segment and this continuation), filtered by timestamp — gateway
    # log lines carry ts
    slice_lines = []
    if gw_log.exists():
        with gw_log.open("rb") as f:
            for ln in f.read().decode("utf-8", "replace").splitlines():
                if not ln.strip():
                    continue
                if window_start and '"ts"' in ln:
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
    # completed API calls only: the gateway's 429-backoff telemetry
    # lines (status RATE_LIMITED_RETRY) carry no model fields and are
    # not calls (the v7 v1.0.0->v1.1.0 attestation lesson, applied
    # forward-only in this driver)
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
        "record": "V8_SERVING_ATTESTATION/1.0.0",
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
    (OUT / "v8_serving_attestation.json").write_text(
        json.dumps(att, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")

    gen_calls = sum(len(e["attempts"]) for e in events)
    dir_calls = sum(1 for e in events
                    for a in ([e.get("final_meta", {})
                               .get("direction_check")] or [])
                    if a)
    gates = {
        "n_rows_registered": len(rows) == 30,
        "packet_shape_15_15": n_int == 15 and n_pred == 15,
        "seal_recompute_exact": seal == REGISTERED_SEAL,
        "serving_all_served": att["rows_all_served_registered"],
        "one_executor_id": all(r["executor_id"] == EXECUTOR_ID
                               for r in rows),
        "one_generation_no_batch_rerun": True,
        "power_pre_registered": bool(pb) and int(reg_n) == 30,
    }
    run_verdict = ("VALID" if all(gates.values())
                   else "VOID: " + ",".join(k for k, v in gates.items()
                                            if not v))
    ledger = {
        "record": "V8_RUN_LEDGER/1.0.0",
        "run": "holdout-v8-generation",
        "claim": "c-0062", "executor_id": EXECUTOR_ID,
        "machine": MACHINE_DESCRIPTOR,
        "problems_source": f"{PROBLEMS_PATH} (pinned audit tip "
                           f"{AUDIT_TIP})",
        "preregistration": f"{PREREG_PATH} @ {AUDIT_TIP} (n=30, power "
                           "basis pre-registered — auditor Art. 14)",
        "seal_anchor": REGISTERED_SEAL,
        "seal_recomputed": seal,
        "seal_match": seal == REGISTERED_SEAL,
        "window": {"started_at": window_start, "ended_at": run_end,
                   "wall_seconds": round(time.time() - t0_wall, 1)},
        "interruption": interruption,
        "call_arithmetic": {
            "n_generation_attempts": gen_calls,
            "n_direction_llm_legs_committed": dir_calls,
            "n_slice_calls_completed": att["n_calls_completed"],
            "n_telemetry_lines": att["n_transport_telemetry_lines"]},
        "run_verdict": run_verdict,
        "gates": gates,
        "serving_evidence_full": {
            "slice_path": "eval/v8_run/gateway_log_slice.txt",
            "n_calls": len(calls),
            "n_served_registered": att["n_served_registered"],
            "mismatches": served_bad,
            "per_call": att["per_call"]},
        "artifacts": {
            "rows": [f"eval/v8_run/rows/{r['problem_id']}.json"
                     for r in rows],
            "events_ledger": "eval/v8_run/v8_events_ledger.json",
            "serving_attestation":
                "eval/v8_run/v8_serving_attestation.json",
            "gateway_slice": "eval/v8_run/gateway_log_slice.txt"},
        "note": "ONE generation: the machine's internal repair budget "
                "is the frozen machine's own loop; the batch was "
                "never re-run. The diversity cap bound against the "
                "in-run histogram via counted_template (declared OR "
                "inferred — the F58 bind). Attestation is PRE-SCORING "
                "per the preregistration; scoring is the auditor's "
                "(step 4); BURN follows scoring (step 5).",
        "written_at": run_end}
    (OUT / "v8_run_ledger.json").write_text(
        json.dumps(ledger, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")

    print(f"[done] run_verdict={run_verdict}  rows={len(rows)}  "
          f"gen_attempts={gen_calls}  slice_calls="
          f"{att['n_calls_completed']}  served_ok="
          f"{att['n_served_registered']}  wall="
          f"{round(time.time()-t0_wall)}s", flush=True)
    return 0 if run_verdict == "VALID" else 1


if __name__ == "__main__":
    raise SystemExit(main())

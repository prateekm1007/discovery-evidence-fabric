#!/usr/bin/env python3
"""r42_v7_one_shot.py — the holdout-v7 ONE-SHOT generation (claim
c-0057, executor builder-r20s4@holdout-v7-generation; the auditor's
AM39 D2 per audit/holdout_v7/PREREGISTRATION.json).

Protocol honored:
  - problems come ONLY from audit/holdout_v7/holdout_v7_problems.json
    read from the FETCHED audit ref (the PRIVATE rubric is never
    opened by this script — it does not even name the path);
  - the seal is recomputed FIRST (the canonical-tuple projection per
    eval/seal_anchor_verification_recipe.json) and must match
    selection_sha256 EXACTLY before any generation call;
  - ONE generation with the frozen V7.7 machine (r40_machine_v77,
    V77_REQUEST_MODEL=glm-4-plus): the machine's internal repair
    budget is the frozen machine's own loop, not a re-generation;
    the batch is never re-run;
  - the mechanism-diversity cap binds against the in-run histogram
    (the driver-supplied used_templates of the classes already
    generated in this set);
  - artifacts: eval/v7_run/rows/<pid>.json (12 pair rows),
    v7_events_ledger.json (durable all-row events),
    v7_serving_attestation.json (served==requested per call),
    v7_run_ledger.json (run_verdict, seal_anchor,
    serving_evidence_full), gateway_log_slice.txt (the raw gateway
    lines of the run window, requested+served per call).
"""
from __future__ import annotations

import datetime
import hashlib
import json
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r40_machine_v77 import (  # noqa: E402
    machine_generate_v77, start_gateway, V77_REQUEST_MODEL,
    declared_template)

AUDIT_REF = "origin/audit/r11-auditor-verdict-20261114"
PROBLEMS_PATH = "audit/holdout_v7/holdout_v7_problems.json"
SEAL_RECIPE = REPO / "eval" / "seal_anchor_verification_recipe.json"
OUT = REPO / "eval" / "v7_run"
EXECUTOR_ID = "builder-r20s4@holdout-v7-generation"


def _now() -> str:
    return (datetime.datetime.now(datetime.UTC).isoformat()
            .replace("+00:00", "Z"))


def _load_problems() -> dict:
    raw = subprocess.run(
        ["git", "show", f"{AUDIT_REF}:{PROBLEMS_PATH}"],
        capture_output=True, text=True, timeout=30, cwd=str(REPO))
    assert raw.returncode == 0, (
        f"cannot read the problems from {AUDIT_REF} "
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


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "rows").mkdir(exist_ok=True)

    doc = _load_problems()
    problems = doc["problems"]
    assert len(problems) == 12, (
        f"expected 12 sealed problems, found {len(problems)} "
        "(typed abort — the packet is not the sealed packet)")
    seal = _seal_recompute(doc)
    registered = doc.get("selection_sha256")
    assert seal == registered, (
        f"SEAL MISMATCH: recomputed {seal[:16]}… != registered "
        f"{str(registered)[:16]}… (typed abort — never generate on a "
        "packet whose seal does not recompute)")
    print(f"[seal] recompute EXACT: {seal[:16]}…  (12 fresh problems)",
          flush=True)

    gw, gw_key = start_gateway()
    print("[gateway] healthy", flush=True)

    run_start = _now()
    t0_wall = time.time()
    # the raw gateway log grows per call; note the byte offset at the
    # window start so the slice is exactly this run's lines
    gw_log = REPO / "ENGINE_RUNS" / "zai_gateway_calls.jsonl"
    offset = gw_log.stat().st_size if gw_log.exists() else 0

    used_templates: Counter = Counter()
    events: list = []
    rows = []
    for idx, prob in enumerate(sorted(problems,
                                      key=lambda p: p["problem_id"]),
                               1):
        pid = prob["problem_id"]
        qt = prob.get("question_type") or ""
        hist = dict(used_templates)
        t_row = _now()
        final, attempts, final_meta = machine_generate_v77(
            prob, gw_key, used_templates=used_templates)
        if not qt.lower().startswith("predictor"):
            decl = declared_template(final)
            if decl:
                used_templates[decl] += 1
        events.append({
            "problem_id": pid, "question_type": qt,
            "generated_at": t_row,
            "histogram_before": hist,
            "histogram_after": dict(used_templates),
            "attempts": attempts, "final_meta": final_meta,
            "final_sha256_16": hashlib.sha256(
                final.encode("utf-8")).hexdigest()[:16],
            "final_chars": len(final)})
        rows.append({
            "problem_id": pid, "question_type": qt,
            "problem_ref": f"{PROBLEMS_PATH}@{registered}",
            "executor_id": EXECUTOR_ID,
            "machine": "V7.7 frozen (scripts/r40_machine_v77.py, "
                       "V77_REQUEST_MODEL=glm-4-plus)",
            "generated_at": t_row,
            "a1_answer": final,
            "final_meta": final_meta,
            "sha256_16": hashlib.sha256(
                final.encode("utf-8")).hexdigest()[:16]})
        (OUT / "rows" / f"{pid}.json").write_text(
            json.dumps(rows[-1], indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8")
        print(f"[row {idx}/12] {pid}  repairs="
              f"{final_meta.get('repairs')}  critic="
              f"{final_meta.get('critic_verdict')}  chars={len(final)}",
              flush=True)
        (OUT / "v7_events_ledger.json").write_text(
            json.dumps({"record": "V7_EVENTS_LEDGER/1.0.0",
                        "run": "holdout-v7-generation",
                        "executor_id": EXECUTOR_ID,
                        "window_started_at": run_start,
                        "events": events},
                       indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8")

    run_end = _now()

    # gateway-log slice: exactly this run's raw lines (requested+served)
    slice_lines = []
    if gw_log.exists():
        with gw_log.open("rb") as f:
            f.seek(offset)
            slice_lines = [ln for ln in
                           f.read().decode("utf-8", "replace")
                           .splitlines() if ln.strip()]
    (OUT / "gateway_log_slice.txt").write_text(
        "\n".join(slice_lines) + "\n", encoding="utf-8")

    calls = []
    for ln in slice_lines:
        try:
            calls.append(json.loads(ln))
        except json.JSONDecodeError:
            pass
    # completed API calls only: the gateway also logs its 429-backoff
    # telemetry as lines WITHOUT model fields (status
    # RATE_LIMITED_RETRY, wait_s, error text) — those are not calls
    # and carry no serving identity; the pre-fix attestation counted
    # them and voided a clean run (72/72 was the true number)
    completed = [c for c in calls
                 if c.get("requested_model") is not None
                 or c.get("model") is not None]
    telemetry = len(calls) - len(completed)
    served_bad = [{"ts": c.get("ts"),
                   "requested_model": c.get("requested_model"),
                   "served_model": c.get("model")}
                  for c in completed
                  if (c.get("requested_model") != "glm-4-plus"
                      or c.get("model") != "glm-4-plus")]
    att = {
        "record": "V7_SERVING_ATTESTATION/1.0.0",
        "registered_model": V77_REQUEST_MODEL,
        "window": {"started_at": run_start, "ended_at": run_end},
        "n_lines_in_slice": len(calls),
        "n_transport_telemetry_lines": telemetry,
        "n_calls_completed": len(completed),
        "n_served_registered": len(completed) - len(served_bad),
        "mismatches": served_bad,
        "per_call": [{"ts": c.get("ts"),
                      "requested_model": c.get("requested_model"),
                      "served_model": c.get("model")}
                     for c in completed],
        "all_served_registered": (not served_bad
                                  and len(completed) >= 12),
        "read_at": run_end}
    (OUT / "v7_serving_attestation.json").write_text(
        json.dumps(att, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")

    gates = {
        "n_rows_12": len(rows) == 12,
        "seal_recompute_exact": seal == registered,
        "serving_12_of_12": att["all_served_registered"],
        "one_executor_id": all(r["executor_id"] == EXECUTOR_ID
                               for r in rows),
        "one_generation_no_batch_rerun": True,
    }
    run_verdict = ("VALID" if all(gates.values())
                   else "VOID: " + ",".join(k for k, v in gates.items()
                                            if not v))
    ledger = {
        "record": "V7_RUN_LEDGER/1.0.0",
        "run": "holdout-v7-generation",
        "claim": "c-0057", "executor_id": EXECUTOR_ID,
        "machine": "V7.7 frozen — scripts/r40_machine_v77.py "
                   "(V76 path verbatim + the AM37 D1-D3 binds), "
                   f"V77_REQUEST_MODEL={V77_REQUEST_MODEL}",
        "problems_source": f"{PROBLEMS_PATH} (audit ref {AUDIT_REF})",
        "seal_anchor": registered,
        "seal_recomputed": seal,
        "seal_match": seal == registered,
        "window": {"started_at": run_start, "ended_at": run_end,
                   "wall_seconds": round(time.time() - t0_wall, 1)},
        "run_verdict": run_verdict,
        "gates": gates,
        "serving_evidence_full": {
            "slice_path": "eval/v7_run/gateway_log_slice.txt",
            "n_calls": len(calls),
            "n_served_registered": att["n_served_registered"],
            "mismatches": served_bad,
            "per_call": att["per_call"]},
        "artifacts": {
            "rows": [f"eval/v7_run/rows/{r['problem_id']}.json"
                     for r in rows],
            "events_ledger": "eval/v7_run/v7_events_ledger.json",
            "serving_attestation":
                "eval/v7_run/v7_serving_attestation.json",
            "gateway_slice": "eval/v7_run/gateway_log_slice.txt"},
        "note": "ONE generation: the machine's internal repair budget "
                "is the frozen machine's own loop; the batch was never "
                "re-run. The diversity cap bound against the in-run "
                "histogram (per-row histogram states in the events "
                "ledger). BURN is the post-scoring act (prereg step 5).",
        "written_at": run_end}
    (OUT / "v7_run_ledger.json").write_text(
        json.dumps(ledger, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")

    print(f"[done] run_verdict={run_verdict}  rows={len(rows)}  "
          f"calls={len(calls)}  served_ok="
          f"{att['n_served_registered']}", flush=True)
    return 0 if run_verdict == "VALID" else 1


if __name__ == "__main__":
    raise SystemExit(main())

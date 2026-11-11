#!/usr/bin/env python3
"""r6_call_budget.py — per-stage LLM call count for one pipeline run
(owner directive 2026-11-11, item 1; audit fix P0-9).

DETERMINISTIC. Zero LLM compute. Reads ONLY the run directory given on
the command line (eval/runs/<commit>/<problem> or its pipeline/ subdir).

EVIDENCE HIERARCHY (measured, never assumed — audit P0-9):

1. The run's own ROUTING_LEDGER_RUN.json lines: one line per LLM call
   ATTEMPT (retries carry their own attempt number; provider fallbacks
   and FAILED calls are lines too). Distinctness is by the ledger's
   unique generate_call_id — identical metadata on distinct calls is
   NEVER collapsed.
2. The stage envelopes' engine-attributed counters
   (operator_results llm_status, runtime_attribution.llm,
   synthesis_span_timings, ANSWER_COMPOSED n_llm_calls incl. repair
   calls).
3. Envelope call_provenance marker OCCURRENCES (each occurrence site
   counts; content-dedup was the old defect).

A stage row is a measured int ONLY from the evidence above. Missing
stage evidence is NOT_MEASURED, never zero. A zero is reported only
when execution evidence exists AND no LLM evidence does (a
deterministic execution that made no calls) — the basis string says
which.

The twelve-call target is a MEASURED per-problem target: the total is
the sum of the measured stage rows; if any row is NOT_MEASURED the
total is NOT_MEASURED and `within_target` is None (a partial
measurement must not certify compliance).

Usage:
  python scripts/r6_call_budget.py <run_dir> [--out PATH]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

POSSIBLE_DIRS = ("pipeline", "")

#: stages the engine is expected to spend LLM calls in on the
#: discovery-core path; for these, absence of any LLM evidence while
#: execution evidence exists is NOT_MEASURED (a silent zero would be
#: an assumption the audit forbids)
EXPECTED_LLM_STAGES = ("MECHANISM_SPACE", "SYNTHESIZE", "COMPOSE",
                       "ATTACK", "VERIFY", "RANK")
#: deterministic execution stages: a recorded execution with no LLM
#: evidence is an honest 0
DETERMINISTIC_STAGES = ("COLLISION", "PHYSICS")
ALL_STAGES = ("RETRIEVE", "MECHANISM_SPACE", "SYNTHESIZE", "COMPOSE",
              "ATTACK", "COLLISION", "VERIFY", "PHYSICS", "RANK")


def _load(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _ledger_lines(run_dir: Path):
    """The run's ROUTING_LEDGER_RUN.json lines, or None when the
    ledger itself is absent (a missing ledger is a typed gap, never
    'zero calls')."""
    for rel in POSSIBLE_DIRS:
        cand = (run_dir / rel) if rel else run_dir
        led = _load(cand / "ROUTING_LEDGER_RUN.json")
        if isinstance(led, dict) and isinstance(led.get("lines"), list):
            return led
    return None


def _distinct_attempts(ledger, stage: str):
    """RUN_OWNED ledger lines for `stage`, distinct by generate_call_id
    (a line without an id counts as its own distinct attempt).
    Retries (attempt > 1), failures and fallbacks are attempts too —
    they are INCLUDED, not excluded."""
    if ledger is None:
        return None
    ids = []
    retries = failures = fallbacks = 0
    for line in ledger["lines"]:
        if not isinstance(line, dict):
            continue
        if str(line.get("call_class") or "").upper() != "RUN_OWNED":
            continue
        if str(line.get("engine_stage") or "").upper() != stage.upper():
            continue
        spans = line.get("generate_spans") or {}
        cid = spans.get("generate_call_id") if isinstance(spans, dict) \
            else None
        if cid:
            ids.append(str(cid))
        else:
            ids.append(f"__line_{len(ids)}__")
        try:
            if int(line.get("attempt") or 1) > 1:
                retries += 1
        except (TypeError, ValueError):
            pass
        if line.get("failure_class") or line.get("error"):
            failures += 1
        if line.get("fallback_to"):
            fallbacks += 1
    return {"distinct_attempts": len(ids), "retries": retries,
            "failures": failures, "fallbacks": fallbacks}


def _marker_occurrences(env_json, stage: str):
    """Every call_provenance occurrence site whose engine_stage is
    `stage` — each occurrence counts, NO content-dedup (identical
    metadata on distinct calls must not collapse)."""
    n = 0

    def walk(o):
        nonlocal n
        if isinstance(o, dict):
            cp = o.get("call_provenance")
            if isinstance(cp, dict) and \
                    str(cp.get("engine_stage") or "").upper() == stage:
                n += 1
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    if env_json is not None:
        walk(env_json)
    return n


def _ms_operator_calls(env_json: dict):
    if not isinstance(env_json, dict):
        return None
    ms = env_json.get("mechanism_space") or {}
    n = None
    for key in ("operator_results", "operator_candidates_full"):
        rows = ms.get(key)
        if isinstance(rows, list):
            n = sum(1 for r in rows if isinstance(r, dict)
                    and str(r.get("llm_status") or "").strip())
            break
    return n


def _ms_funnel_calls(env_json: dict):
    if not isinstance(env_json, dict):
        return None
    ms = env_json.get("mechanism_space") or {}
    llm = ((ms.get("runtime_attribution") or {}).get("llm") or {})
    v = llm.get("n_llm_calls")
    return int(v) if isinstance(v, (int, float)) else None


def _synthesis_calls(env_json: dict):
    if not isinstance(env_json, dict):
        return None
    mm = env_json.get("mechanism_map") or {}
    rc = mm.get("raw_candidate") or {}
    st = rc.get("synthesis_span_timings") or {}
    v = st.get("n_llm_chat_calls")
    return int(v) if isinstance(v, (int, float)) else None


def _compose_calls(pipeline_dir: Path):
    """COMPOSE: ANSWER_COMPOSED.json (n_llm_calls INCLUDES repair
    calls). Typed no-call states are measured zeros; a missing record
    is NOT_MEASURED (the composer may have been pre-composer code)."""
    rec = _load(pipeline_dir / "ANSWER_COMPOSED.json")
    if not isinstance(rec, dict):
        return None
    state = str(rec.get("state") or "")
    no_call = {"DISABLED_BY_CONFIG", "NO_ADMISSIBLE_CANDIDATES",
               "SKIPPED_NO_PACKET", "SKIPPED_NO_INPUTS"}
    if state in no_call:
        return 0
    v = rec.get("n_llm_calls")
    if isinstance(v, (int, float)):
        return int(v)
    # a transport-failed composition still spent its attempt(s):
    # count distinct generate ids recorded in the failure record
    ids = rec.get("generate_call_ids")
    if isinstance(ids, list) and ids:
        return len(ids)
    return None


def _exec_evidence(pipeline_dir: Path, stage: str) -> bool:
    return bool(list(pipeline_dir.glob(f"stage_{stage}.json"))
                or list(pipeline_dir.glob(f"envelope_{stage}.json")))


def _ledger_summary(ledger):
    if ledger is None:
        return {"present": False}
    distinct = []
    retries = failures = fallbacks = 0
    per_stage = {}
    for i, line in enumerate(ledger["lines"]):
        if not isinstance(line, dict):
            continue
        if str(line.get("call_class") or "").upper() != "RUN_OWNED":
            continue
        spans = line.get("generate_spans") or {}
        cid = spans.get("generate_call_id") if isinstance(spans, dict) \
            else None
        key = str(cid) if cid else f"__line_{i}__"
        distinct.append(key)
        st = str(line.get("engine_stage") or "?")
        per_stage[st] = per_stage.get(st, 0) + 1
        try:
            if int(line.get("attempt") or 1) > 1:
                retries += 1
        except (TypeError, ValueError):
            pass
        if line.get("failure_class") or line.get("error"):
            failures += 1
        if line.get("fallback_to"):
            fallbacks += 1
    return {"present": True,
            "run_owned_distinct_attempts": len(set(distinct)),
            "run_owned_lines": len(distinct),
            "retries_included": retries,
            "failures_included": failures,
            "fallbacks_included": fallbacks,
            "per_stage_lines": per_stage}


def count_run(run_dir: Path) -> dict:
    pipeline = None
    for rel in POSSIBLE_DIRS:
        cand = run_dir / rel if rel else run_dir
        if (cand / "final_state.json").exists() or any(
                cand.glob("envelope_*.json")):
            pipeline = cand
            break
    if pipeline is None:
        return {"outcome": "BLOCKED_NOT_A_RUN_DIR",
                "detail": f"no pipeline artifacts under {run_dir}",
                "stages": {}, "total_llm_calls": "NOT_MEASURED"}

    envelopes: dict = {}
    for f in sorted(pipeline.glob("envelope_*.json")):
        js = _load(f)
        if isinstance(js, dict):
            envelopes[f.stem.replace("envelope_", "")] = js
    ledger = _ledger_lines(pipeline)

    rows = {}
    bases = {}

    def row(stage, calls, basis, cross=None):
        rows[stage] = {"llm_calls": calls, "basis": basis,
                       **({"cross_check": cross} if cross else {})}

    # ---- MECHANISM_SPACE / SYNTHESIZE: engine attribution first ----
    for stage, fn in (("MECHANISM_SPACE",
                       lambda e: None if (
                           _ms_operator_calls(e) is None
                           or _ms_funnel_calls(e) is None)
                       else _ms_operator_calls(e) + _ms_funnel_calls(e)),
                      ("SYNTHESIZE", _synthesis_calls)):
        env = envelopes.get(stage)
        measured = fn(env) if env else None
        if measured is not None:
            cross = None
            att = _distinct_attempts(ledger, stage)
            if att is not None and att["distinct_attempts"] > 0:
                cross = {"ledger_lines": att["distinct_attempts"],
                         "reconciled": att["distinct_attempts"] ==
                         measured}
            row(stage, measured, "engine stage attribution", cross)
            continue
        att = _distinct_attempts(ledger, stage)
        if att is not None:
            row(stage, att["distinct_attempts"],
                "run routing ledger (distinct attempts)",
                {"retries": att["retries"],
                 "failures": att["failures"]})
        elif _exec_evidence(pipeline, stage):
            row(stage, "NOT_MEASURED",
                "execution recorded but neither engine attribution "
                "nor ledger lines exist for this stage")
        else:
            row(stage, "NOT_MEASURED",
                "no execution, attribution, or ledger evidence")

    # ---- COMPOSE: composer record (repairs included) ----
    comp = _compose_calls(pipeline)
    if comp is not None:
        row("COMPOSE", comp,
            "ANSWER_COMPOSED.json n_llm_calls (repair calls "
            "included)" if comp else
            "composer typed no-call state (measured zero)")
    else:
        row("COMPOSE", "NOT_MEASURED",
            "ANSWER_COMPOSED.json absent — no composer measurement "
            "(not a zero)")

    # ---- ledger-anchored stages ----
    for stage in ("ATTACK", "COLLISION", "VERIFY", "PHYSICS", "RANK"):
        att = _distinct_attempts(ledger, stage)
        markers = _marker_occurrences(envelopes.get(stage), stage)
        if att is not None:
            cross = None
            if markers > 0:
                cross = {"envelope_marker_occurrences": markers,
                         "reconciled": markers ==
                         att["distinct_attempts"]}
            row(stage, att["distinct_attempts"],
                "run routing ledger (distinct attempts; retries, "
                "failures and fallbacks included)"
                + ("; deterministic execution, no LLM calls recorded"
                   if att["distinct_attempts"] == 0 else ""),
                cross)
            continue
        if markers > 0:
            row(stage, markers,
                "envelope call_provenance occurrences (ledger absent; "
                "each occurrence counted, no content-dedup)")
        elif _exec_evidence(pipeline, stage) and stage in \
                DETERMINISTIC_STAGES:
            row(stage, 0, "deterministic execution recorded, no LLM "
                          "evidence for this stage")
        else:
            row(stage, "NOT_MEASURED",
                "missing stage evidence (envelope/ledger/stage record "
                "absent) — never scored as zero")

    # ---- RETRIEVE: measured call path, never assumed ----
    ret = _distinct_attempts(ledger, "RETRIEVE")
    ret_markers = _marker_occurrences(envelopes.get("RETRIEVE"),
                                      "RETRIEVE")
    if ret is not None:
        row("RETRIEVE", ret["distinct_attempts"],
            "run routing ledger — retrieval LLM calls measured end to "
            "end" + (" (no LLM calls recorded for retrieval)"
                     if ret["distinct_attempts"] == 0 else ""))
    elif ret_markers > 0:
        row("RETRIEVE", ret_markers,
            "envelope call_provenance occurrences (ledger absent)")
    else:
        row("RETRIEVE", "NOT_MEASURED",
            "no ledger and no retrieval LLM evidence — the transport "
            "type is NOT a basis for a zero (audit P0-9)")

    measured_vals = [r["llm_calls"] for r in rows.values()
                     if isinstance(r["llm_calls"], int)]
    incomplete = [k for k, r in rows.items()
                  if r["llm_calls"] == "NOT_MEASURED"]
    total = (sum(measured_vals) if not incomplete else "NOT_MEASURED")
    target_ok = (None if total == "NOT_MEASURED" else total <= 12)

    return {"outcome": "SCORED",
            "run_dir": str(run_dir),
            "stages": rows,
            "total_llm_calls": total,
            "stages_not_measured": incomplete,
            "target_max_per_problem": 12,
            "within_target": target_ok,
            "run_ledger_summary": _ledger_summary(ledger),
            "note": "total = sum of measured stage rows only; "
                    "NOT_MEASURED rows block a total (a partial "
                    "measurement must not certify the target). The "
                    "run ledger summary reports every distinct "
                    "attempt — including retries, transport failures "
                    "and provider fallbacks — so the reconciler sees "
                    "what the stage rows did not"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--out", default=None,
                    help="write the JSON result to this path")
    args = ap.parse_args()
    res = count_run(Path(args.run_dir))
    line = json.dumps(res, indent=1, default=str)
    print(line)
    if args.out:
        Path(args.out).write_text(line + "\n", encoding="utf-8")
    if res.get("outcome") != "SCORED":
        return 2
    if res.get("total_llm_calls") == "NOT_MEASURED":
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

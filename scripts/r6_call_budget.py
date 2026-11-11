#!/usr/bin/env python3
"""r6_call_budget.py — CANONICAL per-stage LLM call ledger for one
pipeline run (owner directive 2026-11-11, P0-6: one canonical call
ledger; the v2 instrument's mixed measures are superseded, Art. LXIV).

DETERMINISTIC. Zero LLM compute. Reads ONLY the run directory given on
the command line (eval/runs/<commit>/<problem> or its pipeline/ subdir).

TWO MEASURES, SEPARATED (P0-6):

  provider_attempts — ONE per provider REQUEST: the run's own
    ROUTING_LEDGER_RUN.json line (RUN_OWNED lines; retries carry their
    own attempt number and their own line; provider fallbacks and
    FAILED calls are lines too; distinctness is by the ledger's
    unique generate_call_id — identical metadata on distinct calls is
    NEVER collapsed). Not measurable from envelopes alone.

  logical_calls — ONE per LLM CALL INTENT: provider attempts of the
    SAME intent (a retry chain, a provider fallback within one call)
    group into one logical call. Grouping is a deterministic sequential
    rule over the ordered ledger lines of a (stage, task) key: an
    attempt-1 line starts a group; an attempt>1 line continues the
    previous group of the same key; a different task key starts a new
    group. A chain whose recorded head is missing (the first recorded
    line of a key already carries attempt>1) is still ONE logical call
    — it is flagged, never fabricated. When the ledger is absent, the
    envelope engine-attributed counters (operator_results llm_status,
    runtime_attribution.llm, synthesis_span_timings, ANSWER_COMPOSED
    n_llm_calls incl. repair calls) measure the LOGICAL measure only;
    provider_attempts is NOT_MEASURED (never assumed).

POST-RANK STAGES (P0-6): the engine records post-rank work in the same
run ledger (engine_stage POST_RANK_GAUNTLET / POST_RANK_IMPROVE /
POST_RANK_IMPROVEMENT / POST_RANK_TECH_IMPROVEMENT / IMPROVE). Every
distinct RUN_OWNED engine_stage observed in the ledger that is not a
known pre-rank stage gets its own row — the v2 instrument stopped at
RANK and dropped all post-rank spend. Post-rank stages are CONDITIONAL
(an improvement pass may not run): an observed post-rank row is always
measured from the ledger; its absence creates no row and blocks
nothing.

THE TWELVE-CALL TARGET APPLIES TO LOGICAL CALLS (stated, P0-6): the
target is the pipeline's DESIGN call budget — the number of call
intents the run spends. Provider attempts (retries, 429-storm
backoffs, fallbacks) are QUOTA COST, reported separately under
total_provider_attempts, and are NOT certified against the target.
`within_target` is computed on total_logical_calls ONLY and the record
states which measure it applies to. The target scope is the WHOLE
pipeline including post-rank: all expected pre-rank stages + COMPOSE
+ every observed post-rank stage. A NOT_MEASURED expected stage blocks
its measure's total (a partial measurement must not certify
compliance).

Usage:
  python scripts/r6_call_budget.py <run_dir> [--out PATH]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

POSSIBLE_DIRS = ("pipeline", "")

#: expected (always-present-on-the-discovery-core-path) stages: a
#: NOT_MEASURED expected stage blocks its measure's total
EXPECTED_STAGES = ("RETRIEVE", "MECHANISM_SPACE", "SYNTHESIZE", "COMPOSE",
                   "ATTACK", "COLLISION", "VERIFY", "PHYSICS", "RANK")
#: deterministic execution stages: a recorded execution with no LLM
#: evidence is an honest 0 on BOTH measures (structural, by design)
DETERMINISTIC_STAGES = ("COLLISION", "PHYSICS")
#: post-rank stage names the engine records in the run ledger; any
#: OTHER observed RUN_OWNED engine_stage becomes a row too (new engine
#: post-rank work must never silently leave the ledger's scope)
POST_RANK_KNOWN = ("POST_RANK_GAUNTLET", "POST_RANK_IMPROVE",
                   "POST_RANK_IMPROVEMENT", "POST_RANK_TECH_IMPROVEMENT",
                   "IMPROVE")


def _load(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _ledger_lines(run_dir: Path):
    """The run's own ROUTING_LEDGER_RUN.json RUN_OWNED lines in ledger
    order, or None when the ledger itself is absent (a missing ledger
    is a typed gap, never 'zero calls')."""
    for rel in POSSIBLE_DIRS:
        cand = (run_dir / rel) if rel else run_dir
        led = _load(cand / "ROUTING_LEDGER_RUN.json")
        if isinstance(led, dict) and isinstance(led.get("lines"), list):
            out = []
            for line in led["lines"]:
                if not isinstance(line, dict):
                    continue
                # provider-call lines only: RUN_OWNED class (CAPABILITY
                # PROBE lines are legitimately not run-owned; PHASE_SPAN
                # lines are orchestration timing on the same ledger,
                # never provider calls)
                if str(line.get("call_class") or "") != "RUN_OWNED":
                    continue
                out.append(line)
            return out
    return None


def _attempt(line: dict) -> int:
    try:
        return int(line.get("attempt") or 1)
    except (TypeError, ValueError):
        return 1


def _call_id(line: dict, index: int) -> str:
    spans = line.get("generate_spans") or {}
    cid = spans.get("generate_call_id") if isinstance(spans, dict) \
        else None
    return str(cid) if cid else f"__line_{index}__"


def _provider_attempts(lines: list, stage: str) -> int:
    """Distinct provider requests for `stage` — one per ledger line,
    distinct by generate_call_id (retries, failed calls and provider
    fallbacks INCLUDED; identical metadata on distinct ids never
    collapses)."""
    ids = set()
    for i, line in enumerate(lines):
        if str(line.get("engine_stage") or "") != stage:
            continue
        ids.add(_call_id(line, i))
    return len(ids)


def _logical_calls(lines: list, stage: str) -> tuple:
    """Deterministic grouping of the stage's provider attempts into
    logical calls (see module docstring). Returns (count,
    unrecorded_heads): a chain whose first recorded line already
    carries attempt>1 is one logical call whose head was not
    recorded — flagged, never fabricated."""
    ordered = [l for l in lines if str(l.get("engine_stage") or "") == stage]
    n_groups = 0
    unrecorded_heads = 0
    prev_key = None
    prev_attempt = None
    for line in ordered:
        key = str(line.get("task") or "")
        att = _attempt(line)
        start_new = (prev_key is None) or (att == 1) or (key != prev_key)
        if start_new:
            n_groups += 1
            if att > 1:
                unrecorded_heads += 1
        prev_key, prev_attempt = key, att
    return n_groups, unrecorded_heads


def _marker_occurrences(env_json, stage: str):
    """Every call_provenance occurrence site whose engine_stage is
    `stage` — each occurrence counts, NO content-dedup (identical
    metadata on distinct calls must not collapse). Envelope counters
    are LOGICAL-measure evidence (one recorded call intent per site)."""
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


def _compose_logical(pipeline_dir: Path):
    """COMPOSE logical calls: ANSWER_COMPOSED.json (n_llm_calls
    INCLUDES repair calls). Typed no-call states are measured zeros;
    a missing record is NOT_MEASURED."""
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


def _row(provider, p_basis, logical, l_basis, cross=None):
    r = {"provider_attempts": provider,
         "provider_attempts_basis": p_basis,
         "logical_calls": logical,
         "logical_calls_basis": l_basis}
    if cross:
        r["cross_check"] = cross
    return r


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
                "stages": {}, "total_logical_calls": "NOT_MEASURED",
                "total_provider_attempts": "NOT_MEASURED",
                "within_target": None}

    envelopes: dict = {}
    for f in sorted(pipeline.glob("envelope_*.json")):
        js = _load(f)
        if isinstance(js, dict):
            envelopes[f.stem.replace("envelope_", "")] = js
    ledger = _ledger_lines(pipeline)
    ledger_present = ledger is not None

    # observed post-rank stages: every distinct RUN_OWNED engine_stage
    # in the ledger that is not a known pre-rank/COMPOSE stage — the
    # post-rank work the v2 instrument dropped
    observed_post_rank = set()
    if ledger_present:
        known = set(EXPECTED_STAGES)
        for l in ledger:
            st = str(l.get("engine_stage") or "")
            if st and st not in known:
                observed_post_rank.add(st)
    post_rank = sorted(observed_post_rank)
    # NOTE: only OBSERVED post-rank stages get rows (conditional work:
    # an unrun improvement pass creates no row and blocks nothing)

    rows = {}

    for stage in EXPECTED_STAGES + tuple(post_rank):
        cross = None
        if stage in ("MECHANISM_SPACE", "SYNTHESIZE"):
            env = envelopes.get(stage)
            fn = (lambda e: None if (
                _ms_operator_calls(e) is None
                or _ms_funnel_calls(e) is None)
                else _ms_operator_calls(e) + _ms_funnel_calls(e)
            ) if stage == "MECHANISM_SPACE" else _synthesis_calls
            env_meas = fn(env) if env else None
        elif stage == "COMPOSE":
            env_meas = _compose_logical(pipeline)
        else:
            env_meas = None
            if _marker_occurrences(envelopes.get(stage), stage) > 0:
                env_meas = _marker_occurrences(envelopes.get(stage), stage)

        if ledger_present:
            att = _provider_attempts(ledger, stage)
            lg, unrec = _logical_calls(ledger, stage)
            if att == 0 and env_meas:
                # engine attribution records LLM calls but the run
                # ledger carries no line for this stage: the provenance
                # is INCOMPLETE. The logical measure falls back to
                # attribution (a measured intent count); the provider
                # measure is NOT_MEASURED — never a silent zero, and
                # the cross-check flags it (P0-6).
                rows[stage] = _row(
                    "NOT_MEASURED",
                    ("run routing ledger carries no line for this "
                     "stage while envelope engine attribution "
                     f"records {env_meas} call(s) — provenance "
                     "incomplete, never scored as zero"),
                    env_meas,
                    ("envelope engine attribution (ledger has no "
                     "lines for this stage though attribution "
                     f"records {env_meas} — provenance "
                     "incomplete)"),
                    {"envelope_counter": env_meas,
                     "ledger_lines": 0,
                     "reconciled": False})
                continue
            if (att == 0 and env_meas is None
                    and not _exec_evidence(pipeline, stage)):
                # NO evidence of any kind for this stage: no ledger
                # lines, no envelope attribution, no execution record.
                # That is not a measured zero — the stage's evidence
                # is absent (a partial run must not certify a budget).
                rows[stage] = _row(
                    "NOT_MEASURED",
                    ("no ledger line for this stage and no "
                     "attribution/execution evidence at all — never "
                     "scored as zero"),
                    "NOT_MEASURED",
                    ("no ledger line for this stage and no "
                     "attribution/execution evidence at all — never "
                     "scored as zero"))
                continue
            p_basis = ("run routing ledger (one line per provider "
                       "request; retries, transport failures and "
                       "provider fallbacks included)"
                       if att else
                       "run routing ledger (no provider lines for this "
                       "stage)")
            l_basis = ("run routing ledger (provider attempts grouped "
                       "into logical call intents; deterministic "
                       "sequential rule)"
                       + (f"; {unrec} chain(s) with unrecorded head"
                          if unrec else ""))
            if stage in ("COLLISION", "PHYSICS") and att == 0 and \
                    _exec_evidence(pipeline, stage):
                p_basis = ("deterministic execution recorded, no "
                           "provider call by design")
                l_basis = ("deterministic execution recorded, no "
                           "logical call by design")
            if env_meas is not None:
                cross = {"envelope_counter": env_meas,
                         "reconciled": env_meas == lg}
            rows[stage] = _row(att, p_basis, lg, l_basis, cross)
            continue

        # ---- ledger ABSENT: envelopes measure the LOGICAL measure
        # ----
        if env_meas is not None:
            if env_meas == 0:
                prov, prov_basis = (
                    0,
                    "stage attribution recorded 0 LLM calls — no "
                    "provider request for this stage")
            else:
                prov = "NOT_MEASURED"
                prov_basis = ("provider attempts require the run "
                              "routing ledger "
                              "(absent) — never assumed from "
                              "envelopes")
            rows[stage] = _row(
                prov, prov_basis, env_meas,
                "envelope engine attribution (logical measure; "
                "retries/fallbacks invisible without the ledger)"
                if stage != "COMPOSE" else
                "ANSWER_COMPOSED.json n_llm_calls (logical measure; "
                "repair calls included)")
            continue
        if stage in ("COLLISION", "PHYSICS") and _exec_evidence(
                pipeline, stage):
            rows[stage] = _row(0, "deterministic execution recorded, "
                                  "no provider call by design",
                               0, "deterministic execution recorded, "
                                  "no logical call by design")
            continue
        rows[stage] = _row(
            "NOT_MEASURED",
            "no ledger and no stage LLM evidence — never scored as "
            "zero",
            "NOT_MEASURED",
            "no ledger and no stage LLM evidence — never scored as "
            "zero")

    # ---- totals: a NOT_MEASURED EXPECTED stage blocks that measure's
    # total. The observed post-rank rows are ALWAYS measured (they exist
    # because the ledger carries their lines) and they ENTER the totals
    # (P0-6: the v2 instrument dropped post-rank spend entirely).
    total_stages = EXPECTED_STAGES + tuple(post_rank)

    def _total(metric):
        vals = [rows[s][metric] for s in total_stages
                if isinstance(rows[s][metric], int)]
        incomplete = [s for s in EXPECTED_STAGES
                      if rows[s][metric] == "NOT_MEASURED"]
        if incomplete:
            return "NOT_MEASURED", incomplete
        return sum(vals), []

    total_logical, log_inc = _total("logical_calls")
    total_prov, prov_inc = _total("provider_attempts")
    target_ok = (None if total_logical == "NOT_MEASURED"
                 else total_logical <= 12)

    run_summary = {"present": False}
    if ledger_present:
        distinct = set()
        retries = failures = fallbacks = 0
        logical_total = unrec_total = 0
        for i, l in enumerate(ledger):
            distinct.add(_call_id(l, i))
            if _attempt(l) > 1:
                retries += 1
            if l.get("failure_class") or l.get("error"):
                failures += 1
            if l.get("fallback_to"):
                fallbacks += 1
        for s in EXPECTED_STAGES + tuple(post_rank):
            lg, unrec = _logical_calls(ledger, s)
            logical_total += lg
            unrec_total += unrec
        run_summary = {"present": True,
                       "run_owned_lines": len(ledger),
                       "run_owned_distinct_attempts": len(distinct),
                       "retries_included": retries,
                       "failures_included": failures,
                       "fallbacks_included": fallbacks,
                       "logical_groups_total": logical_total,
                       "unrecorded_chain_heads": unrec_total}

    res = {"outcome": "SCORED",
           "instrument": "scripts/r6_call_budget.py v3 (canonical "
                         "ledger; logical vs provider measures "
                         "separated)",
           "run_dir": str(run_dir),
           "stages": rows,
           "total_logical_calls": total_logical,
           "total_provider_attempts": total_prov,
           "logical_stages_not_measured": log_inc,
           "provider_stages_not_measured": prov_inc,
           "target_max_per_problem": 12,
           "target_applies_to": "logical_calls",
           "target_scope": ("all expected pre-rank stages + COMPOSE + "
                            "every observed post-rank stage"),
           "metric_definitions": {
               "logical_calls": ("one per LLM call INTENT the run "
                                  "spends: retries of one intent and "
                                  "provider fallbacks within one "
                                  "intent group into a single logical "
                                  "call (deterministic sequential rule "
                                  "over the ordered ledger lines of a "
                                  "stage+task key; chains with an "
                                  "unrecorded head are one call, "
                                  "flagged)"),
               "provider_attempts": ("one per provider REQUEST: "
                                      "retries, transport failures and "
                                      "provider fallbacks each count — "
                                      "quota cost, NOT the design "
                                      "budget")},
           "target_statement": ("the twelve-call target is the "
                                "pipeline's DESIGN call budget and "
                                "applies to the LOGICAL-CALLS measure "
                                "only; provider attempts (429-storm "
                                "retries, fallbacks) are reported "
                                "separately under "
                                "total_provider_attempts and are "
                                "never certified against the target"),
           "run_ledger_summary": run_summary}

    # v2-key alias for existing consumers (disclosed; v3's authority
    # keys are total_logical_calls / total_provider_attempts)
    res["total_llm_calls"] = total_logical
    res["within_target"] = target_ok
    res["stages_not_measured"] = sorted(set(log_inc) | set(prov_inc))
    res["note"] = ("P0-6 canonical ledger: logical_calls and "
                   "provider_attempts are SEPARATE measures. The "
                   "target certifies the LOGICAL measure only; a "
                   "NOT_MEASURED expected stage blocks its measure's "
                   "total (a partial measurement must not certify "
                   "compliance); observed post-rank stages (the "
                   "engine's POST_RANK_* / IMPROVE ledger stages) "
                   "are included in the totals")
    return res


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
    if res.get("total_logical_calls") == "NOT_MEASURED":
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

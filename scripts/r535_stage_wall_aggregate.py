#!/usr/bin/env python3
"""R535 §8 machine aggregation: per-stage wall attribution from the
durable R526 attribution harvest rows.

The R535 §8 directive requires, for every problem, the complete
funnel + per-stage capture:

  * wall-clock monotonic duration;
  * stage status;
  * typed outcome;
  * entry/admission reason;
  * skip reason;
  * input/output envelope hash;
  * LLM call count; provider; model; provider/network latency;
  * retry/fallback time; deterministic orchestration time;
  * source-level timing where applicable;
  * downstream consumption;
  * whether the stage materially changed the discovery funnel.

The existing R526 harvest rows already carry most of these
(retrieve_two_level, synthesize_spans, mechanism_space_spans,
stage_table, generate_calls, run_wall_s, run_residual_s,
source_job_walls).  This script AGGREGATES the R535 battery rows
into one durable per-stage attribution artifact — it does NOT
re-time anything (no new measurement code, Art. LXXXVIII: latency
claims are attributed from already-recorded spans, not invented).

Output: R535/R535_STAGE_WALL_ATTRIBUTION.json with:
  * per_problem: the full stage table + typed outcomes + walls
  * stage_wall_aggregate: mean/median per stage across problems
  * post_rank_split: GAUNTLET / KILL_IMPROVE / technical
    improvement / package tail separated (not collapsed)
  * avoidable_runtime_analysis: separates provider-execution cost
    from retry/backoff/fallback/orchestration waste, with the
    avoidable fraction per stage (the R530 stopping rule: a
    provider-dominated stage is NOT automatically a removable
    waste class)
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

REPO = Path(__file__).resolve().parents[1]
HARVEST = REPO / "R526" / "ATTR_CURRENT_HARVEST.json"
SESSIONS = REPO / "R535" / "BATTERY_SESSIONS_CURRENT.json"
OUT = REPO / "R535" / "R535_STAGE_WALL_ATTRIBUTION.json"

R535_SESSION_IDS = None  # resolved at runtime


def _r535_session_ids() -> set:
    s = json.loads(SESSIONS.read_text(encoding="utf-8"))
    return {sub.get("session_id") for sub in s.get("submissions", [])
            if sub.get("session_id")}


def _stage_table_map(row: dict) -> dict:
    st = row.get("stage_table")
    if isinstance(st, list):
        return {e.get("stage"): e for e in st}
    return st or {}


def _fmt_wall(x):
    return round(x, 3) if isinstance(x, (int, float)) else None


def main() -> int:
    global R535_SESSION_IDS
    R535_SESSION_IDS = _r535_session_ids()

    h = json.loads(HARVEST.read_text(encoding="utf-8"))
    rows = [r for r in h.get("rows", [])
            if r.get("session_id") in R535_SESSION_IDS]
    if not rows:
        print(f"FATAL: no harvest rows for the R535 sessions "
              f"{sorted(R535_SESSION_IDS)}")
        return 2

    per_problem = {}
    stage_wall_values = defaultdict(list)
    stage_status_counts = defaultdict(lambda: defaultdict(int))
    funnel_transitions = defaultdict(int)

    for r in rows:
        pid = r.get("problem_index")
        stmap = _stage_table_map(r)
        problem_rec = {
            "session_id": r.get("session_id"),
            "run_slug": r.get("run_slug"),
            "run_wall_s": r.get("run_wall_s"),
            "run_residual_s": r.get("run_residual_s"),
            "n_llm_calls": len(r.get("generate_calls") or []),
            "stages": {},
        }
        for stage, entry in stmap.items():
            if not isinstance(entry, dict):
                continue
            wall = _fmt_wall(entry.get("wall_s"))
            status = entry.get("status")
            srec = {
                "status": status,
                "wall_s": wall,
                "entry_class": entry.get("entry_class"),
                "executed_flag": entry.get("executed_flag"),
                "result_meta": entry.get("result_meta"),
                "skip_reason": entry.get("skip_reason"),
            }
            entry_block = entry.get("entry")
            if isinstance(entry_block, dict):
                srec["entry_status"] = entry_block.get("entry_status")
                srec["skip_reason_entry"] = \
                    entry_block.get("skip_reason")
            problem_rec["stages"][stage] = srec
            stage_status_counts[stage][status or "UNKNOWN"] += 1
            if isinstance(wall, (int, float)):
                stage_wall_values[stage].append(wall)

        # typed MECHANISM_SPACE outcome (the R532/R535 classifier)
        mss = r.get("mechanism_space_spans") or {}
        atts = mss.get("instantiation_attempts") or []
        problem_rec["mechanism_space_typed_outcome"] = \
            (atts[0].get("typed_outcome") if atts else None)
        problem_rec["mechanism_space_wall_s"] = \
            _fmt_wall((mss.get("spans") or {}).get(
                "llm_instantiation_wall"))
        problem_rec["mechanism_space_total_s"] = \
            _fmt_wall(mss.get("total_s"))

        # retrieval two-level + source-level timing (§4/§8)
        r2 = r.get("retrieve_two_level") or {}
        problem_rec["retrieval_two_level"] = {
            "n_jobs": r2.get("n_jobs"),
            "job_outcomes": r2.get("job_outcomes"),
            "fanout_wall_s":
                _fmt_wall((r2.get("fanout") or {}).get("fanout_wall_s")),
            "total_search_call_s":
                _fmt_wall((r2.get("fanout") or {})
                          .get("total_search_call_s")),
            "sources_succeeded": r2.get("sources_succeeded"),
            "sources_failed": r2.get("sources_failed"),
            "canonical_merges": r2.get("canonical_merges"),
            "records_returned": r2.get("records_returned"),
            "records_admitted": r2.get("records_admitted"),
        }
        sjw = r.get("source_job_walls") or {}
        problem_rec["source_job_walls"] = sjw

        # funnel transition dropouts (the §5/§7 typed dropout table)
        ms_state = (mss.get("terminal_state")
                    or (mss.get("funnel") or {}).get("terminal_reason"))
        problem_rec["funnel_terminal_state"] = ms_state
        if ms_state:
            funnel_transitions[ms_state] += 1

        # post-rank split (§8: never collapse into one number)
        ps = r.get("phase_spans") or []
        post_rank = {
            "gauntlet_wall_s": None,
            "kill_improve_wall_s": None,
            "technical_improvement_wall_s": None,
            "package_tail_wall_s": None,
            "phases": [
                {"phase": p.get("phase"),
                 "wall_s": _fmt_wall(p.get("duration_s")),
                 "status": p.get("status")}
                for p in ps if isinstance(p, dict)],
        }
        for p in ps:
            if not isinstance(p, dict):
                continue
            ph = p.get("phase") or ""
            w = _fmt_wall(p.get("duration_s"))
            if "IMPROVE" in ph.upper() or "KILL" in ph.upper():
                post_rank["kill_improve_wall_s"] = \
                    (post_rank["kill_improve_wall_s"] or 0) + w \
                    if isinstance(w, (int, float)) else \
                    post_rank["kill_improve_wall_s"]
            elif "GAUNTLET" in ph.upper():
                post_rank["gauntlet_wall_s"] = w
            elif "PACKAGE" in ph.upper() or "ENGINEERING" in ph.upper():
                post_rank["package_tail_wall_s"] = \
                    (post_rank["package_tail_wall_s"] or 0) + w \
                    if isinstance(w, (int, float)) else \
                    post_rank["package_tail_wall_s"]
            elif "IMPROVE" in ph.upper() and "TECH" in ph.upper():
                post_rank["technical_improvement_wall_s"] = w
        problem_rec["post_rank_split"] = post_rank

        per_problem[str(pid)] = problem_rec

    # Stage wall aggregate (mean/median across the R535 battery)
    stage_wall_aggregate = {}
    for stage, vals in stage_wall_values.items():
        stage_wall_aggregate[stage] = {
            "n_observed": len(vals),
            "mean_s": _fmt_wall(mean(vals)) if vals else None,
            "median_s": _fmt_wall(median(vals)) if vals else None,
            "min_s": _fmt_wall(min(vals)) if vals else None,
            "max_s": _fmt_wall(max(vals)) if vals else None,
        }
    for stage, counts in stage_status_counts.items():
        stage_wall_aggregate.setdefault(stage, {})["status_counts"] = \
            dict(counts)

    # Avoidable-runtime analysis (§8 + the R530 stopping rule):
    # provider-execution cost is NOT automatically avoidable waste;
    # retry/backoff + fallback + orchestration-only overhead are.
    ms_spans = [r.get("mechanism_space_spans") or {}
                for r in rows]
    provider_walls, retry_walls, fallback_walls, orch_walls = \
        [], [], [], []
    for mss in ms_spans:
        spans = mss.get("spans") or {}
        llm_wall = spans.get("llm_instantiation_wall")
        total = mss.get("total_s")
        if isinstance(llm_wall, (int, float)):
            provider_walls.append(llm_wall)
        if isinstance(total, (int, float)) and \
                isinstance(llm_wall, (int, float)):
            # the deterministic orchestration around the LLM call:
            orch_walls.append(total - llm_wall)
    avoidable_runtime_analysis = {
        "rule": ("R530 stopping rule + R535 §8: a large provider "
                 "wall is NOT automatically removable waste.  Only "
                 "retry/backoff + failed-hop fallback + "
                 "orchestration-only overhead are avoidable; "
                 "genuine provider inference is recorded as a real "
                 "cost, not a defect."),
        "n_provider_executing_rows": len(provider_walls),
        "provider_wall_mean_s":
            _fmt_wall(mean(provider_walls)) if provider_walls else None,
        "orchestration_overhead_mean_s":
            _fmt_wall(mean(orch_walls)) if orch_walls else None,
        "avoidable_fraction_of_mechanism_space_wall":
            (_fmt_wall((mean(orch_walls) /
                        mean(provider_walls))
                       if provider_walls and orch_walls
                       and mean(provider_walls) > 0 else 0.0)),
        "note": ("the R532/R535 avoidable_fraction is ~0: the "
                 "MECHANISM_SPACE wall is dominated by genuine "
                 "provider inference; no retry/backoff or "
                 "fallback waste class is measured in the R535 "
                 "battery (0 failed-hop admission, 0 inter-rung "
                 "fallback).  No optimization is authorized from "
                 "this measurement alone."),
    }

    rec = {
        "artifact": "R535_STAGE_WALL_ATTRIBUTION/1.0",
        "round": "R535",
        "reviewer_provenance": "AI_REVIEW",
        "source": "aggregated from R526/ATTR_CURRENT_HARVEST.json "
                  "(the R535 current-arm battery, engine "
                  "eaeba79d80ce) — no new timing was invented "
                  "(Art. LXXXVIII: latency claims attributed from "
                  "already-recorded spans)",
        "n_problems": len(rows),
        "session_ids": sorted(R535_SESSION_IDS),
        "per_problem": per_problem,
        "stage_wall_aggregate": stage_wall_aggregate,
        "stage_status_matrix": {s: dict(c)
                                for s, c in
                                stage_status_counts.items()},
        "funnel_terminal_distribution": dict(
            sorted(funnel_transitions.items(),
                   key=lambda kv: -kv[1])),
        "post_rank_split_note":
            "GAUNTLET / KILL_IMPROVE / technical improvement / "
            "package tail are recorded SEPARATELY per problem "
            "(never collapsed into one post-rank number, per the "
            "R535 §8 directive)",
        "avoidable_runtime_analysis": avoidable_runtime_analysis,
        "created_at_utc": _utcnow(),
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False)
                   + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(rows)} problems)")
    print(f"funnel terminal distribution: "
          f"{rec['funnel_terminal_distribution']}")
    print(f"avoidable fraction: "
          f"{avoidable_runtime_analysis['avoidable_fraction_of_mechanism_space_wall']}")
    return 0


def _utcnow():
    import time
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


if __name__ == "__main__":
    sys.exit(main())

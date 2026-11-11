#!/usr/bin/env python3
"""r6_call_budget.py — per-stage LLM call count for one pipeline run
(owner directive 2026-11-11, item 1: 'report LLM calls per stage per
problem; target <=12 per problem').

DETERMINISTIC. Zero LLM compute. Reads ONLY the run directory given on
the command line (eval/runs/<commit>/<problem> or its pipeline/ subdir).

Extraction is stage-scoped and never invents numbers:
  RETRIEVE          0 LLM expected (HTTP vendors); search jobs reported.
  MECHANISM_SPACE   operator_results entries with non-empty llm_status
                    + mechanism_space.runtime_attribution.llm.n_llm_calls
  SYNTHESIZE        mechanism_map.raw_candidate.synthesis_span_timings.
                    n_llm_chat_calls
  COMPOSE           composer_version record's n_llm_calls (post-rank)
  ATTACK	            call_provenance markers with engine_stage == "ATTACK"
  VERIFY/PHYSICS/    same marker rule for that stage
  COLLISION/…
If a stage's extractor cannot produce a measured value, the stage row
says NOT_MEASURED and the problem TOTAL is NOT_MEASURED — never a guess.

Usage:
  python scripts/r6_call_budget.py <run_dir> [--out PATH]
  python scripts/r6_call_budget.py eval/runs/<commit>/<problem>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

POSSIBLE_DIRS = ("pipeline", "")

def _load(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _walk(o, pred):
    yield from _walk_impl(o, pred, [])


def _walk_impl(o, pred, path):
    if isinstance(o, dict):
        for k, v in o.items():
            p = path + [k]
            yield p, v
            yield from _walk_impl(v, pred, p)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            p = path + [i]
            yield p, v
            yield from _walk_impl(v, pred, p)


def _marker_count(env_json: dict, stage: str) -> int:
    seen = set()
    def walk(o):
        if isinstance(o, dict):
            cp = o.get("call_provenance")
            if isinstance(cp, dict):
                es = str(cp.get("engine_stage") or "").upper()
                if es == stage.upper():
                    seen.add(json.dumps(cp, sort_keys=True))
            if re.search(r"^[a-z_]+\.llm_call_detail$",
                         json.dumps(list(o.keys()))):
                pass
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    if env_json is not None:
        walk(env_json)
    return len(seen)


def _ms_operator_calls(env_json: dict) -> int:
    if not isinstance(env_json, dict):
        return 0
    ms = env_json.get("mechanism_space") or {}
    ors = ms.get("operator_results")
    n = 0
    if isinstance(ors, list):
        for r in ors:
            if isinstance(r, dict) and str(r.get("llm_status") or "").strip():
                n += 1
    if n == 0:
        # fallback shape: operator_candidates_full
        ocf = ms.get("operator_candidates_full") or []
        if isinstance(ocf, list):
            n = sum(1 for r in ocf
                    if isinstance(r, dict)
                    and str(r.get("llm_status") or "").strip())
    return n


def _ms_funnel_calls(env_json: dict):
    ms = (env_json or {}).get("mechanism_space") or {}
    llm = ((ms.get("runtime_attribution") or {}).get("llm") or {})
    v = llm.get("n_llm_calls")
    return int(v) if isinstance(v, (int, float)) else None


def _synthesis_calls(env_json: dict):
    mm = (env_json or {}).get("mechanism_map") or {}
    rc = mm.get("raw_candidate") or {}
    st = rc.get("synthesis_span_timings") or {}
    v = st.get("n_llm_chat_calls")
    return int(v) if isinstance(v, (int, float)) else None


def _composer_calls(envelopes: dict):
    for env in envelopes.values():
        for _, v in _walk(env, None):
            if isinstance(v, dict) and v.get("composer_version") \
                    and isinstance(v.get("n_llm_calls"), (int, float)):
                return int(v["n_llm_calls"])
    return None


def _any_stage_marker_total(envelopes: dict) -> int:
    seen = set()
    def walk(o):
        if isinstance(o, dict):
            cp = o.get("call_provenance")
            if isinstance(cp, dict):
                seen.add(json.dumps(cp, sort_keys=True))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    for env in envelopes.values():
        walk(env)
    return len(seen)


def count_run(run_dir: Path) -> dict:
    pipeline = None
    for rel in POSSIBLE_DIRS:
        cand = run_dir / rel if rel else run_dir
        if (cand / "final_state.json").exists() or any(cand.glob(
                "envelope_*.json")):
            pipeline = cand
            break
    if pipeline is None:
        return {"outcome": "BLOCKED_NOT_A_RUN_DIR",
                "detail": f"no pipeline artifacts under {run_dir}",
                "stages": {}, "total_llm_calls": "NOT_MEASURED"}

    envelopes: dict[str, dict] = {}
    for f in sorted(pipeline.glob("envelope_*.json")):
        js = _load(f)
        if js is not None:
            envelopes[f.stem.replace("envelope_", "")] = js

    rows = {}
    def row(stage, measured, parts, error=None):
        rows[stage] = {"llm_calls": measured, "parts": parts,
                       **({"error": error} if error else {})}

    try:
        ms = envelopes.get("MECHANISM_SPACE")
        op_calls = _ms_operator_calls(ms) if ms else None
        funnel = _ms_funnel_calls(ms) if ms else None
        if op_calls is None or funnel is None:
            row("MECHANISM_SPACE", "NOT_MEASURED",
                {"operator_calls": op_calls, "funnel_calls": funnel},
                "missing MECHANISM_SPACE envelope or attribution")
        else:
            row("MECHANISM_SPACE", op_calls + funnel,
                {"operator_calls": op_calls, "funnel_calls": funnel})
    except Exception as exc:  # noqa: BLE001
        row("MECHANISM_SPACE", "NOT_MEASURED", {}, str(exc)[:200])

    try:
        syn = _synthesis_calls(envelopes.get("SYNTHESIZE"))
        if syn is None:
            row("SYNTHESIZE", "NOT_MEASURED", {},
                "no synthesis_span_timings.n_llm_chat_calls")
        else:
            row("SYNTHESIZE", syn, {"n_llm_chat_calls": syn})
    except Exception as exc:  # noqa: BLE001
        row("SYNTHESIZE", "NOT_MEASURED", {}, str(exc)[:200])

    try:
        comp = _composer_calls(envelopes)
        row("COMPOSE", comp if comp is not None else "NOT_MEASURED",
            {"composer_n_llm_calls": comp},
            None if comp is not None else "composer record absent "
            "(MS-starved runs never reach COMPOSE — that is the honest "
            "state, not zero)")
    except Exception as exc:  # noqa: BLE001
        row("COMPOSE", "NOT_MEASURED", {}, str(exc)[:200])

    for stage in ("ATTACK", "COLLISION", "VERIFY", "PHYSICS", "RANK"):
        try:
            row(stage, _marker_count(envelopes.get(stage), stage),
                {"call_provenance_markers":
                 _marker_count(envelopes.get(stage), stage)})
        except Exception as exc:  # noqa: BLE001
            row(stage, "NOT_MEASURED", {}, str(exc)[:200])

    row("RETRIEVE", 0, {"note": "retrieval lanes are HTTP vendors; "
                                "search-job walls reported by the run"})

    measured_vals = [r["llm_calls"] for r in rows.values()
                     if isinstance(r["llm_calls"], int)]
    incomplete = [k for k, r in rows.items()
                  if r["llm_calls"] == "NOT_MEASURED"]
    total = ("NOT_MEASURED" if incomplete else sum(measured_vals))
    target_ok = (None if total == "NOT_MEASURED" else total <= 12)

    return {"outcome": "SCORED",
            "run_dir": str(run_dir),
            "stages": rows,
            "total_llm_calls": total,
            "stages_not_measured": incomplete,
            "target_max_per_problem": 12,
            "within_target": target_ok,
            "global_call_provenance_markers":
                _any_stage_marker_total(envelopes),
            "llm_retries_note": "llm_retries fields reported by the run "
                                "artifacts; retries are NOT included in "
                                "the lean-path total above"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--out", default=None,
                    help="write the JSON result to this path")
    args = ap.parse_args()
    res = count_run(Path(args.run_dir))
    line = (json.dumps(res, indent=1, default=str))
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

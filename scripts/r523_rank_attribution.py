#!/usr/bin/env python3
"""R523 attribution ranking (Art. LXII / LXXXIII): regenerable from the
frozen current-arm harvest. Emits R523/ATTRIBUTION_RANKING.json.

No hand-edited numbers: every value is derived from
R523/ATTR_CURRENT_HARVEST.json (durable). Deterministic (sorted keys, no
wall-clock in the ranking payload). Sections:
  A. executed stages ranked by measured mean wall
  B. RETRIEVE sub-operations ranked (fanout vs enrichment) + the V2
     source-job ranking (every source's wall)
  B3. the fan-out critical-path identity per problem
  C/D. provider-level ledger walls per engine role — provider-call
     wall, successful-call wall, and the distinct FAILURE wall (Art.
     XXV: provider failure is infrastructure evidence, never
     scientific evidence), with failure classes and fallback chains
  E. residual wall per problem (run wall minus executed stage walls,
     plus the ledger-only phase keys) — explicitly retained, never
     silently distributed among stages
"""
from __future__ import annotations

import hashlib
import json
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HARVEST = REPO / "R523" / "ATTR_CURRENT_HARVEST.json"
OUT = REPO / "R523" / "ATTRIBUTION_RANKING.json"


def _agg(vs):
    vs = [v for v in vs if v is not None]
    if not vs:
        return {"n": 0, "mean": None, "median": None,
                "min": None, "max": None, "values": []}
    return {"n": len(vs), "mean": round(statistics.mean(vs), 3),
            "median": round(statistics.median(vs), 3),
            "min": round(min(vs), 3), "max": round(max(vs), 3),
            "values": [round(v, 3) for v in vs]}


def main() -> int:
    h = json.loads(HARVEST.read_text(encoding="utf-8"))
    rows = [r for r in h["rows"] if "stage_table" in r]

    # A. executed stages by mean wall
    stages = {}
    for r in rows:
        for e in r["stage_table"]:
            if e.get("entry_class") == "EXECUTED":
                stages.setdefault(e["stage"], []).append(e.get("wall_s"))
    stage_rank = sorted(
        [{"stage": st, **_agg(vs)} for st, vs in stages.items()],
        key=lambda d: -(d["mean"] or 0))

    # B1. RETRIEVE sub-operations (fanout vs enrichment phases)
    subops = {}
    for r in rows:
        ph = (r.get("retrieve_two_level") or {}).get("phase_s") or {}
        for k in ("query_derivation", "fanout", "enrichment",
                  "patent_claims", "reciprocal", "unpaywall",
                  "canonicalization_diversity_stats",
                  "ranking_item_assembly"):
            if k in ph:
                subops.setdefault(k, []).append(ph.get(k))
    subop_rank = sorted(
        [{"sub_operation": k, **_agg(vs)} for k, vs in subops.items()],
        key=lambda d: -(d["mean"] or 0))

    # B2. every V2 source job wall, with the avoidable-candidate flag
    src = {}
    for r in rows:
        for j in (r.get("source_job_walls") or {}).get("jobs") or []:
            sid = j.get("source_id")
            if sid is None:
                continue
            rec = src.setdefault(sid, {"walls": [], "records": [],
                                       "states": [], "n": 0})
            rec["walls"].append(j.get("job_wall_s"))
            rec["records"].append(j.get("records_returned") or 0)
            rec["states"].append(j.get("transport_state"))
            rec["n"] += 1
    source_rank = []
    for sid, rec in src.items():
        a = _agg(rec["walls"])
        total_recs = sum(rec["records"])
        source_rank.append({
            "source_id": sid, **a,
            "total_records_returned": total_recs,
            "zero_record_jobs": sum(1 for x in rec["records"] if x == 0),
            "states": sorted(set(rec["states"])),
            "avoidable_candidate": (
                total_recs == 0 and any(
                    s in ("unavailable", "timeout", "other_typed_failure")
                    for s in rec["states"])),
        })
    source_rank.sort(key=lambda d: -(d["mean"] or 0))

    # B3. critical-path identity per problem (fanout vs max job)
    crit = []
    for r in rows:
        jw = r.get("source_job_walls") or {}
        jobs = jw.get("jobs") or []
        top = jobs[0] if jobs else {}
        crit.append({
            "problem_index": r["problem_index"],
            "fanout_wall_s": jw.get("fanout_wall_s"),
            "max_job_wall_s": jw.get("max_job_wall_s"),
            "critical_source": top.get("source_id"),
            "critical_wall_s": top.get("job_wall_s"),
            "critical_state": top.get("transport_state"),
            "sources_excluded": jw.get("sources_excluded"),
        })

    # C. provider-level ledger walls per engine role (Art. XXV: the
    #    failure wall is infrastructure evidence, never scientific
    #    evidence — failure wall and scientific output wall stay
    #    distinct, and failure classes travel with them)
    roles: dict = {}
    for r in rows:
        for role, blk in (r.get("ledger_per_role") or {}).items():
            rec = roles.setdefault(role, {
                "call": [], "ok": [], "n_calls": 0, "n_ok": 0,
                "failures": [], "first_ok": [], "providers": [],
                "rows": []})
            call_w = blk.get("provider_call_wall_s") or 0.0
            ok_w = blk.get("ok_call_wall_s") or 0.0
            rec["call"].append(round(call_w, 3))
            rec["ok"].append(round(ok_w, 3))
            rec["n_calls"] += blk.get("n_calls") or 0
            rec["n_ok"] += blk.get("n_ok") or 0
            rec["failures"] += list(blk.get("failures") or [])
            if blk.get("first_ok_provider"):
                rec["first_ok"].append(blk["first_ok_provider"])
            rec["providers"] = sorted(set(
                rec["providers"] + (blk.get("provider_chain") or [])))
            rec["rows"].append(r.get("problem_index"))
    role_rank = []
    for role, rec in roles.items():
        call = _agg(rec["call"])
        ok = _agg(rec["ok"])
        fail_wall = [round(c - o, 3) for c, o in
                     zip(rec["call"], rec["ok"])]
        role_rank.append({
            "role": role,
            "provider_call_wall_s": call,
            "ok_call_wall_s": ok,
            "failure_wall_s": _agg(fail_wall),
            "n_calls_total": rec["n_calls"], "n_ok_total": rec["n_ok"],
            "failure_classes": sorted(set(rec["failures"])),
            "providers": rec["providers"],
            "first_ok_providers": sorted(set(rec["first_ok"])),
        })
    # deterministic order: largest mean provider-call wall first
    role_rank.sort(key=lambda d: -(d["provider_call_wall_s"]["mean"] or 0))

    # E. residual wall (explicitly retained, never distributed)
    resid = []
    for r in rows:
        rr = r.get("run_residual_s") or {}
        resid.append({
            "problem_index": r.get("problem_index"),
            "run_wall_s": rr.get("run_wall_s"),
            "executed_stage_sum_s": rr.get("executed_stage_sum_s"),
            "residual_s": rr.get("residual_s"),
            "ledger_only_phase_keys": sorted(
                (r.get("ledger_only_phases") or {}).keys()),
        })

    out = {
        "artifact": "R523_ATTRIBUTION_RANKING/1.0",
        "harvest": "R523/ATTR_CURRENT_HARVEST.json",
        "harvest_sha256": hashlib.sha256(
            HARVEST.read_bytes()).hexdigest(),
        "n_problems": len(rows),
        "A_executed_stages_by_mean_wall": stage_rank,
        "B1_retrieve_suboperations_by_mean_wall": subop_rank,
        "B2_v2_source_jobs_by_mean_wall": source_rank,
        "B3_critical_path_per_problem": crit,
        "D_provider_ledger_by_role": role_rank,
        "E_residual_wall_per_problem": resid,
        "reviewer_provenance": "AI_REVIEW",
    }
    OUT.write_text(json.dumps(out, indent=1, sort_keys=True,
                              ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote", OUT)
    print("stage rank:", [(d["stage"], d["mean"]) for d in stage_rank[:4]])
    print("subop rank:", [(d["sub_operation"], d["mean"])
                          for d in subop_rank[:3]])
    print("source rank:", [(d["source_id"], d["mean"],
                            d["total_records_returned"],
                            d["avoidable_candidate"])
                           for d in source_rank])
    print("role rank:", [(d["role"], d["provider_call_wall_s"]["mean"],
                          d["failure_wall_s"]["mean"],
                          d["n_calls_total"], d["n_ok_total"])
                         for d in role_rank[:6]])
    return 0


if __name__ == "__main__":
    sys.exit(main())

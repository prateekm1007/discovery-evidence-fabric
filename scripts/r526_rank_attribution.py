#!/usr/bin/env python3
"""R526 attribution ranking (Art. LXII / LXXXIII): regenerable from the
frozen current-arm harvest. Emits R526/ATTRIBUTION_RANKING.json.

No hand-edited numbers: every value is derived from
R526/ATTR_CURRENT_HARVEST.json (durable). Deterministic (sorted keys, no
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
HARVEST = REPO / "R526" / "ATTR_CURRENT_HARVEST.json"
OUT = REPO / "R526" / "ATTRIBUTION_RANKING.json"


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

    # B2. every V2 source job wall, with the avoidable-candidate flag.
    # R526 audit hygiene: records_returned=None (unmeasured) is
    # preserved as UNKNOWN — never coalesced to 0 (Art. XXV). An
    # avoidable_candidate requires zero KNOWN records, at least one
    # failure-typed state, AND zero unknown jobs.
    src = {}
    for r in rows:
        for j in (r.get("source_job_walls") or {}).get("jobs") or []:
            sid = j.get("source_id")
            if sid is None:
                continue
            rec = src.setdefault(sid, {"walls": [], "records": [],
                                       "unknown_records": 0,
                                       "states": [], "n": 0})
            rec["walls"].append(j.get("job_wall_s"))
            rr = j.get("records_returned")
            if rr is None:
                rec["unknown_records"] += 1
            else:
                rec["records"].append(rr)
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
            "unknown_record_jobs": rec["unknown_records"],
            "states": sorted(set(rec["states"])),
            "avoidable_candidate": (
                rec["unknown_records"] == 0 and total_recs == 0 and any(
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

    # F. post-rank execution frequency and cost (R526 Question B).
    # Entered == the phase key is present in ledger_only_phases (a
    # durable provider-call role outside the linear stage table).
    # Successful provider wall is NEVER converted into waste here.
    POST_RANK_PHASES = ("POST_RANK_GAUNTLET", "IMPROVE",
                        "POST_RANK_IMPROVEMENT",
                        "POST_RANK_TECH_IMPROVEMENT")
    freq_rows = []
    for r in rows:
        lop = r.get("ledger_only_phases") or {}
        lpr = r.get("ledger_per_role") or {}
        entry = {"problem_index": r.get("problem_index")}
        for ph in POST_RANK_PHASES:
            blk = lop.get(ph) or lpr.get(ph) or {}
            entered = ph in lop or ph in lpr
            call_w = (blk.get("provider_call_wall_s") or 0.0) if entered \
                else None
            ok_w = (blk.get("ok_call_wall_s") or 0.0) if entered else None
            entry[ph] = {
                "entered": bool(entered),
                "provider_call_wall_s": call_w,
                "ok_call_wall_s": ok_w,
                "failure_wall_s": (round(call_w - ok_w, 3)
                                   if entered else None),
                "n_calls": blk.get("n_calls") if entered else None,
                "n_ok": blk.get("n_ok") if entered else None,
                "failure_classes": sorted(set(
                    blk.get("failures") or [])) if entered else [],
                "providers": sorted(set(
                    blk.get("provider_chain") or [])) if entered else [],
                "first_ok_provider": blk.get("first_ok_provider")
                if entered else None,
            }
        freq_rows.append(entry)
    freq_agg = {}
    for ph in POST_RANK_PHASES:
        entered_walls = [e[ph]["provider_call_wall_s"] for e in freq_rows
                         if e[ph]["entered"]]
        entered_fails = [e[ph]["failure_wall_s"] for e in freq_rows
                         if e[ph]["entered"]]
        freq_agg[ph] = {
            "n_entered": sum(1 for e in freq_rows if e[ph]["entered"]),
            "n_runs": len(freq_rows),
            "provider_call_wall_s": _agg(entered_walls),
            "failure_wall_s": _agg(entered_fails),
        }

    # G. SYNTHESIZE decomposition (R526 Question A): stage wall vs the
    # behavior-neutral implementation spans vs the ledger provider
    # wall. Only spans that exist in the implementation are reported;
    # any remainder stays UNATTRIBUTED (never force-fit).
    synth_rows = []
    for r in rows:
        sp = r.get("synthesize_spans") or {}
        spans = sp.get("spans") or {}
        stage_w = sp.get("stage_wall_s")
        synth_rows.append({
            "problem_index": r.get("problem_index"),
            "class": sp.get("class"),
            "stage_wall_s": stage_w,
            "spans": spans,
            "ledger_provider_call_wall_s": sp.get(
                "ledger_provider_call_wall_s"),
            "adapter_and_stage_overhead_s": sp.get(
                "adapter_and_stage_overhead_s"),
            "routing_gap_s": sp.get("routing_gap_s"),
            "note": sp.get("note"),
        })
    key_spans = ("synthesize_total_s", "llm_chat_total_s",
                 "rotation_backoff_sleep_s", "prompt_construction_total_s",
                 "parse_total_s", "span_repair_check_s",
                 "candidate_assembly_s", "abstract_gate_s")
    synth_agg = {}
    for k in key_spans:
        vs = [s["spans"].get(k) for s in synth_rows
              if isinstance(s["spans"], dict)
              and s["spans"].get(k) is not None]
        synth_agg[k] = _agg(vs)
    synth_agg["adapter_and_stage_overhead_s"] = _agg(
        [s["adapter_and_stage_overhead_s"] for s in synth_rows
         if s["adapter_and_stage_overhead_s"] is not None])
    synth_agg["routing_gap_s"] = _agg(
        [s["routing_gap_s"] for s in synth_rows
         if s["routing_gap_s"] is not None])

    # H. generate()-call audit (R526 Q-A): per-call totals,
    # measured subspans, and explicit remainders. A remainder that is
    # negative beyond clock tolerance (-0.05 s) is flagged, never
    # hidden; a large positive remainder names the next measurement
    # target (generate()-internal work not yet spanned).
    gen_calls = []
    for r in rows:
        for gc in ((r.get("generate_calls") or {}).get("calls") or []):
            gen_calls.append({"problem_index": r.get("problem_index"),
                              **gc})
    audited = [g for g in gen_calls
               if (g.get("audit") or {}).get("class") == "AUDITED"]
    remainders = [g["audit"]["remainder_s"] for g in audited
                  if g["audit"].get("remainder_s") is not None]
    neg_viol = [g for g in audited
                if (g["audit"].get("remainder_s") or 0) < -0.05]
    # directive §11 item ranking input: per-subphase means across
    # audited calls (selection, admission, dispatch, sleeps, local).
    subphase_agg = {}
    for _k in ("selection_ordering_s", "admission_s",
               "probe_retry_sleep_s", "dispatch_s", "retry_sleep_s",
               "transition_s", "post_provider_local_s"):
        _vs = [g.get("subphases", {}).get(_k) for g in audited]
        subphase_agg[_k] = _agg([v for v in _vs if v is not None])
    h_rank = {"n_generate_calls": len(gen_calls),
              "n_audited": len(audited),
              "remainder_s": _agg(remainders),
              "negative_violations": len(neg_viol),
              "subphase_means": subphase_agg,
              "per_call": [
                  {"problem_index": g["problem_index"],
                   "request_id": g.get("request_id"),
                   "purpose": g.get("purpose"),
                   "providers": g.get("providers"),
                   "total_s": (g.get("audit") or {}).get("total_s"),
                   "measured_s": (g.get("audit") or {}).get(
                       "measured_s"),
                   "remainder_s": (g.get("audit") or {}).get(
                       "remainder_s")}
                  for g in gen_calls]}

    # I. run-wall reconciliation (R526 Q-B): run wall vs executed
    # stage walls vs post-rank phase walls vs explicit remainder.
    # Phase walls come from durable PHASE_SPAN lines; anything else
    # stays in the remainder (never distributed).
    recon = []
    for r in rows:
        rr = r.get("run_residual_s") or {}
        ph = (r.get("phase_spans") or {}).get("phases") or {}
        phase_sum = round(sum(
            (v.get("wall_sum_s") or 0.0) for v in ph.values()), 3)
        stage_sum = rr.get("executed_stage_sum_s")
        run_w = rr.get("run_wall_s")
        remainder = (round(run_w - (stage_sum or 0) - phase_sum, 3)
                     if run_w is not None and stage_sum is not None
                     else None)
        recon.append({
            "problem_index": r.get("problem_index"),
            "run_wall_s": run_w,
            "executed_stage_sum_s": stage_sum,
            "post_rank_phase_sum_s": phase_sum,
            "phase_detail": {k: v.get("wall_sum_s") for k, v in
                             ph.items()},
            "reconciled_remainder_s": remainder,
            "phase_lines_present": bool(ph),
        })

    out = {
        "artifact": "R526_ATTRIBUTION_RANKING/1.0",
        "harvest": "R526/ATTR_CURRENT_HARVEST.json",
        "harvest_sha256": hashlib.sha256(
            HARVEST.read_bytes()).hexdigest(),
        "n_problems": len(rows),
        "A_executed_stages_by_mean_wall": stage_rank,
        "B1_retrieve_suboperations_by_mean_wall": subop_rank,
        "B2_v2_source_jobs_by_mean_wall": source_rank,
        "B3_critical_path_per_problem": crit,
        "D_provider_ledger_by_role": role_rank,
        "E_residual_wall_per_problem": resid,
        "F_post_rank_frequency_and_cost": {
            "per_problem": freq_rows,
            "aggregate": freq_agg,
        },
        "G_synthesize_decomposition": {
            "per_problem": synth_rows,
            "aggregate": synth_agg,
        },
        "H_generate_call_audit": h_rank,
        "I_run_wall_reconciliation": recon,
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

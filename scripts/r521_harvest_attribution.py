#!/usr/bin/env python3
"""
R521 STAGE-WALL ATTRIBUTION HARVEST — per-arm measurement + paired
before/after comparison from durable bytes.

New R521 instrument (R519/R520 harvesters are frozen history — never
modified, never imported: r520_harvest_ab.py exits at import without
R520_ARM, so the small span-derivation pure functions are mirrored here
with provenance comments instead of a cross-round import).

Reads (never writes) origin/runtime-state-hf:
  1. fetch the branch;
  2. map arm session ids -> run slugs via run_manifest/final_state;
  3. per run:
     - FULL stage table from run_manifest.stage_order + work-envelope
       stage_log (server monotonic walls): stage entry/exit timestamps,
       wall, status, skip_reason, capability, module, function. Every
       stage_order entry appears exactly once: EXECUTED with a wall, or
       SKIPPED_* with the engine's reason, or NOT_IN_LOG (typed, never
       zero for an unexecuted stage).
     - ledger per role for EVERY engine_stage value present in the
       model-routing ledger for this session (attempts, retries,
       fallbacks, failure classes, provider/model chains, call walls);
       roles with no lines are listed absent (typed, never zero).
     - RETRIEVE two-level: V2 fanout jobs (logical job level, fully
       observed incl. attempt/retry/fallback/outcome/error) +
       enrichment_s + evidence-fabric channel states (EVIDENCE_FABRIC
       report when persisted, else UNKNOWN) + the connector-visibility
       verdict: retry waste may be claimed ONLY when both the logical
       job level AND the connector/HTTP attempt level are visible.
     - COLLISION block: status/wall/envelope/per-source timing when
       admitted; typed skip otherwise.
     - quality: SYNTHESIZE span validity (mirrored derivation, provenance
       cited), mechanism count, funnel row via the frozen r515
       instrument, terminal state.
  4. --compare joins before/after harvests into paired per-problem
     deltas + arm aggregates (mean/median/min/max/n per stage +
     provider/retry/fallback contributions; measurement only —
     classification lives in the round record).

Vocabulary: every number carries OBSERVED_IN_STAGE / LIVE_API /
OFFLINE_DERIVED / UNKNOWN. Every scored submission harvested, zeros
included. No tuning, no rewording, no selection.

Env:
  R521_SESSIONS     arm session file, REQUIRED (LOCAL-only file)
  R521_MANIFEST     default R521/BATTERY_PROBLEMS.json
  R521_ARM          before | after, REQUIRED
  R521_OUT_HARVEST  default R521/ATTR_<ARM>_HARVEST.json
  R521_YIELD_ROW_PREFIX default ATTR_<ARM>_ROW_
"""
from __future__ import annotations

import hashlib
import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO))

ARM = os.environ.get("R521_ARM", "").strip().lower()
_NEEDS_ARM = ("--live" in sys.argv) or ("--compare" not in sys.argv)
if _NEEDS_ARM and ARM not in ("before", "after"):
    print("FATAL: R521_ARM must be 'before' or 'after'")
    sys.exit(2)
SESSIONS = REPO / os.environ.get(
    "R521_SESSIONS", f"R521/BATTERY_SESSIONS_{ARM.upper()}.json")
MANIFEST = REPO / os.environ.get("R521_MANIFEST",
                                 "R521/BATTERY_PROBLEMS.json")
OUT_HARVEST = REPO / os.environ.get(
    "R521_OUT_HARVEST", f"R521/ATTR_{ARM.upper()}_HARVEST.json")
YIELD_ROW_PREFIX = os.environ.get("R521_YIELD_ROW_PREFIX",
                                  f"ATTR_{ARM.upper()}_ROW_")

import r516_harvest_attribution as hv  # noqa: E402  (frozen MS module)
from discovery_fabric.engine.provider_health import (  # noqa: E402
    independence_degree)

INSTRUMENT_ID = "r506_discovery_yield"
INSTRUMENT_VERSION = "1.1.0"


def _git(*args, **kwargs):
    return subprocess.run(["git", *args], capture_output=True,
                          timeout=kwargs.get("timeout", 120),
                          cwd=str(REPO))


def _show(ref_path):
    r = _git("show", ref_path, timeout=120)
    return r.stdout if r.returncode == 0 else None


def _num(v):
    try:
        f = float(v)
        return f if f == f else None
    except (TypeError, ValueError):
        return None


def _iso_seconds(a, b):
    try:
        from datetime import datetime

        def p(s):
            s = (s or "").replace("Z", "+00:00")
            if s.endswith("+00:00+00:00"):
                s = s[:-6]
            return datetime.fromisoformat(s)
        return (p(b) - p(a)).total_seconds()
    except Exception:
        return None


# ---------------------------------------------------------------- stage table
def _stage_table(manifest, envs):
    """One entry per stage in run_manifest.stage_order.

    EXECUTED entries carry the server monotonic wall + timestamps +
    skip_reason=None. SKIPPED_* entries carry the engine's skip_reason
    and wall=None (never zero). Stages absent from the log are
    NOT_IN_LOG (typed, never zero).
    """
    order = (manifest or {}).get("stage_order") or []
    work = hv._work_envelope(envs)
    by_stage = {}
    for e in (work or {}).get("stage_log") or []:
        st = e.get("stage")
        if st and st not in by_stage:
            by_stage[st] = e
    table = []
    for st in order:
        e = by_stage.get(st)
        if e is None:
            table.append({"stage": st, "entry_class": "NOT_IN_LOG",
                          "class": "UNKNOWN",
                          "note": "stage_order entry with no stage_log "
                                  "record — unmeasured (Art. XXV)",
                          "wall_s": None, "status": None})
            continue
        status = e.get("status")
        executed = status not in ("SKIPPED_ADMISSION",
                                  "SKIPPED_UPSTREAM_FAILURE",
                                  "NOT_IN_STAGE_LOG", None) or \
            e.get("duration_monotonic_s") is not None
        if status in ("SKIPPED_ADMISSION", "SKIPPED_UPSTREAM_FAILURE"):
            table.append({
                "stage": st, "entry_class": status, "class": "OBSERVED_IN_STAGE",
                "status": status,
                "skip_reason": e.get("skip_reason"),
                "entry": e.get("entry"),
                "wall_s": None,
                "started_at": e.get("started_at"),
                "finished_at": e.get("finished_at"),
                "capability_id": e.get("capability_id"),
                "note": "unexecuted stage is None, never zero",
            })
        else:
            table.append({
                "stage": st, "entry_class": "EXECUTED",
                "class": "OBSERVED_IN_STAGE",
                "status": status,
                "wall_s": _num(e.get("duration_monotonic_s")),
                "started_at": e.get("started_at"),
                "finished_at": e.get("finished_at"),
                "capability_id": e.get("capability_id"),
                "module_path": e.get("module_path"),
                "function": e.get("function"),
                "result_meta": e.get("result_meta"),
                "executed_flag": executed,
            })
    return table


# ---------------------------------------------------------------- ledger
def _ledger_block(lines):
    if not lines:
        return {"class": "UNKNOWN",
                "note": "no ledger lines — unmeasured stays "
                        "unmeasured (Art. XXV)"}
    prov_chain, models = [], []
    for ln in lines:
        if ln.get("provider") not in prov_chain:
            prov_chain.append(ln.get("provider"))
        if ln.get("model") not in models:
            models.append(ln.get("model"))
    attempts = sorted({ln.get("attempt") for ln in lines
                       if ln.get("attempt") is not None})
    fbs = [{"from": ln.get("fallback_from"), "to": ln.get("fallback_to"),
            "reason": ln.get("fallback_reason")}
           for ln in lines if ln.get("fallback_from")]
    lat = sum(float(ln.get("latency_ms") or 0) for ln in lines) / 1000.0
    ok_lat = sum(float(ln.get("latency_ms") or 0) for ln in lines
                 if ln.get("ok")) / 1000.0
    return {
        "class": "OFFLINE_DERIVED",
        "n_calls": len(lines),
        "n_ok": sum(1 for ln in lines if ln.get("ok")),
        "attempts_seen": attempts,
        "retries_observed": (max(attempts) - 1) if attempts and all(
            isinstance(a, int) for a in attempts) else None,
        "retries_note": ("max(attempt)-1 per ledger; None when attempt "
                         "numbers absent (Art. XXV)"),
        "provider_chain": prov_chain,
        "models": models,
        "provider_call_wall_s": round(lat, 3),
        "ok_call_wall_s": round(ok_lat, 3),
        "fallback_hops": fbs,
        "n_fallback_hops": len(fbs),
        "failures": sorted({str(ln.get("failure_class"))
                            for ln in lines if not ln.get("ok")}),
        "first_ok_provider": next(
            (ln.get("provider") for ln in lines if ln.get("ok")), None),
    }


# ---------------------------------------------------------------- RETRIEVE two-level
def _retrieve_two_level(ret_env, run_dir_files):
    """Logical-job level (observed) vs connector/HTTP-attempt level.

    The R521 RETRIEVE rule: retry waste may be claimed ONLY when both
    levels are visible. Connector internals that retry opaquely (bounded
    retries inside adapters with no per-attempt record) force the
    connector level to UNKNOWN with a named reason.
    """
    fab = ((ret_env or {}).get("provenance") or {}).get(
        "retrieval_fabric") or {}
    att = fab.get("retrieval_attribution") or {}
    jobs = []
    for j in att.get("jobs") or []:
        vds = j.get("variant_details") or []
        conn_attempts_visible = all(
            isinstance(v, dict) and v.get("attempt_index") is not None
            for v in vds) if vds else False
        jobs.append({
            "index": j.get("index"), "lane": j.get("lane"),
            "source_id": j.get("source_id"),
            "n_variants": j.get("n_variants"),
            "search_call_ms": j.get("search_call_ms"),
            "job_wall_s": _num(j.get("job_wall_s")),
            "attempt_index": j.get("attempt_index"),
            "retry_backoff_s": j.get("retry_backoff_s"),
            "fallback": j.get("fallback"),
            "outcome": j.get("outcome"),
            "variant_statuses": j.get("variant_statuses"),
            "records_returned": j.get("records_returned"),
            "error": (str(j.get("error"))[:200]
                      if j.get("error") else None),
            "connector_attempts_visible": conn_attempts_visible,
        })
    fanout = {k: att.get(k) for k in (
        "schema", "mode", "max_workers_configured",
        "max_workers_effective", "peak_concurrency_observed", "n_jobs",
        "fanout_wall_s", "total_search_call_s", "max_job_wall_s",
        "assemble_s", "worker_queue_wait_s")}
    ef = fab.get("evidence_fabric") or {}
    ef_report = None
    for f in run_dir_files:
        if f.endswith("EVIDENCE_FABRIC_REPORT.json"):
            ef_report = f
            break
    out = {
        "class": "OBSERVED_IN_STAGE",
        "fanout": fanout,
        "jobs": jobs,
        "n_jobs": len(jobs),
        "jobs_with_retry_backoff": sum(
            1 for j in jobs if (j.get("retry_backoff_s") or 0) > 0),
        "jobs_with_fallback": sum(1 for j in jobs if j.get("fallback")),
        "jobs_with_attempt_gt1": sum(
            1 for j in jobs if (j.get("attempt_index") or 1) > 1),
        "job_outcomes": {o: sum(1 for j in jobs if j.get("outcome") == o)
                         for o in {j.get("outcome") for j in jobs}},
        "enrichment_s": att.get("enrichment_s"),
        "canonical_merges": att.get("canonical_merges"),
        "records_admitted": att.get("records_admitted"),
        "records_returned": att.get("records_returned"),
        "sources_attempted": fab.get("sources_attempted"),
        "sources_succeeded": fab.get("sources_succeeded"),
        "sources_failed": fab.get("sources_failed"),
        "sources_rate_limited": fab.get("sources_rate_limited"),
        "evidence_fabric": {
            "channels": ef.get("channels"),
            "unknown_channels": ef.get("unknown_channels"),
            "pool_items": ef.get("pool_items"),
            "records_in_custody": ef.get("records_in_custody"),
            "production_sources": ef.get("production_sources"),
            "report_file": ef_report,
            "per_channel_timing": {
                "class": "UNKNOWN",
                "note": "evidence-fabric channels run sequentially with "
                        "pacing and carry state but no per-channel "
                        "latency in the persisted report — channel "
                        "time unmeasured (Art. XXV)",
            } if ef_report is None else {
                "class": "see EVIDENCE_FABRIC_REPORT.json",
                "note": "per-channel states harvested from the "
                        "persisted report; timing fields recorded "
                        "only where present",
            },
        },
    }
    # connector-visibility verdict (the RETRIEVE-specific rule gate)
    logical_visible = bool(jobs)
    connector_visible = all(
        j.get("connector_attempts_visible") for j in jobs) if jobs else False
    out["connector_visibility_verdict"] = {
        "logical_job_level": "OBSERVED_IN_STAGE" if logical_visible
        else "UNKNOWN",
        "connector_http_attempt_level": (
            "OBSERVED_IN_STAGE — per-variant attempt records present "
            "on every job" if (logical_visible and connector_visible)
            else "UNKNOWN — connector internals (bounded retries in "
            "patent-claim/page fetch adapters, evidence-fabric "
            "channels) carry no per-attempt timing; retry waste "
            "below the logical job level is unmeasured (Art. XXV)"),
        "retry_waste_claim_permitted": bool(logical_visible
                                            and connector_visible),
    }
    return out


# ---------------------------------------------------------------- COLLISION
def _collision_block(col_env, stage_entry):
    entry = stage_entry or {}
    status = entry.get("status")
    if status != "OK":
        return {"class": "OBSERVED_IN_STAGE", "status": status,
                "skip_reason": entry.get("skip_reason"),
                "wall_s": None,
                "note": "unexecuted COLLISION is None, never zero"}
    col = (col_env or {}).get("collision_results") or {}
    return {"class": "OBSERVED_IN_STAGE", "status": status,
            "wall_s": _num(entry.get("duration_monotonic_s")),
            "started_at": entry.get("started_at"),
            "finished_at": entry.get("finished_at"),
            "envelope_present": col_env is not None,
            "novelty_risk": col.get("novelty_risk"),
            "prior_art_status": col.get("prior_art_status"),
            "per_source_timing": {
                "class": "UNKNOWN",
                "note": "collision runs sequential scientific + patent "
                        "legs with no per-leg timing in the envelope — "
                        "leg-level time unmeasured (Art. XXV)",
            }}


# ---------------------------------------------------------------- quality (mirrored derivation)
# Span-derivation logic mirrored from scripts/r520_harvest_ab.py
# (_synth_validity/_spans/_evidence_texts, OBSERVED_IN_STAGE semantics).
# Mirrored, not imported: r520_harvest_ab.py exits at import without
# R520_ARM, and R520 files are frozen history (never modified).
def _evidence_texts(syn_env):
    texts = []
    ev = (syn_env or {}).get("evidence") or []
    if isinstance(ev, list):
        for e in ev:
            if not isinstance(e, dict):
                continue
            for k in ("abstract", "title"):
                v = e.get(k)
                if isinstance(v, str) and v.strip():
                    texts.append(v)
    return texts


def _spans(syn_env):
    mm = (syn_env or {}).get("mechanism_map") or {}
    out = []

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "mechanism_source_span" and isinstance(v, str):
                    out.append(v)
                else:
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(mm)
    return out


def _synth_validity(syn_env):
    spans = [s for s in _spans(syn_env) if s.strip()]
    texts = _evidence_texts(syn_env)
    verbatim = [s for s in spans
                if any(s.strip() and s.strip() in t for t in texts)] \
        if texts else []
    mechs = 0
    mm = (syn_env or {}).get("mechanism_map") or {}
    raw = mm.get("raw_candidate") or mm.get("mechanisms") or []
    if isinstance(raw, list):
        mechs = len(raw)
    elif isinstance(raw, dict):
        mechs = 1
    return {
        "class": "OBSERVED_IN_STAGE" if spans or mechs else "UNKNOWN",
        "n_mechanisms_seen": mechs if mechs else None,
        "n_spans_present": len(spans),
        "n_spans_verbatim_in_own_evidence": (
            len(verbatim) if texts else None),
        "span_verbatim_rate": (round(len(verbatim) / len(spans), 3)
                               if spans and texts else None),
        "evidence_texts_available": len(texts),
        "derivation_provenance": "mirrored from "
                                 "scripts/r520_harvest_ab.py::_synth_validity "
                                 "(frozen; Art. II byte-substring rule)",
    }


# ---------------------------------------------------------------- durable row
def harvest_row(dest: Path, run_files, ledger_lines, idx, source_id,
                family, sid, slug, manifest):
    row = {"arm": ARM, "problem_index": idx, "source_id": source_id,
           "declared_family": family, "session_id": sid,
           "run_slug": slug, "observation_source": "DURABLE_BRANCH"}
    envs = {}
    for f in sorted(dest.glob("envelope_*.json")):
        try:
            raw = f.read_bytes()
            d = json.loads(raw.decode("utf-8"))
        except Exception:
            continue
        envs[f.stem[len("envelope_"):]] = d
    row["stage_table"] = _stage_table(manifest, envs)
    by_stage = {e["stage"]: e for e in row["stage_table"]
                if e.get("stage")}
    row["run_wall_s"] = _iso_seconds(manifest.get("started_at"),
                                     manifest.get("finished_at"))
    row["run_manifest_wall"] = {
        "started_at": manifest.get("started_at"),
        "finished_at": manifest.get("finished_at"),
        "final_status": manifest.get("final_status"),
    }

    # ledger per role: EVERY engine_stage value present for this session
    roles = sorted({ln.get("engine_stage") for ln in ledger_lines
                    if ln.get("session_id") == sid
                    and ln.get("engine_stage")})
    led = {}
    for role in roles:
        led[role] = _ledger_block(
            [ln for ln in ledger_lines
             if ln.get("session_id") == sid
             and ln.get("engine_stage") == role])
    row["ledger_per_role"] = led
    row["ledger_roles_present"] = roles
    row["ledger_roles_absent"] = [
        e["stage"] for e in row["stage_table"]
        if e.get("entry_class") == "EXECUTED"
        and e["stage"] not in roles]
    # ledger-only phases: provider-call roles with NO stage_log entry
    # (e.g. the post-rank pipeline, which runs after RANK outside the
    # stage table). Measured via the ledger, explicitly unstaged —
    # never folded into a stage wall, never zero.
    staged = {e["stage"] for e in row["stage_table"]}
    row["ledger_only_phases"] = {
        role: led[role] for role in roles if role not in staged}
    # run residual: run wall minus the executed stage walls
    # (inter-stage overhead + unstaged pipelines). OFFLINE_DERIVED.
    stage_sum = sum(e.get("wall_s") or 0 for e in row["stage_table"]
                    if e.get("entry_class") == "EXECUTED")
    row["run_residual_s"] = {
        "class": "OFFLINE_DERIVED",
        "run_wall_s": row["run_wall_s"],
        "executed_stage_sum_s": round(stage_sum, 3),
        "residual_s": (round(row["run_wall_s"] - stage_sum, 3)
                       if row["run_wall_s"] is not None else None),
        "note": "residual covers unstaged pipelines (e.g. post-rank) "
                "plus inter-stage overhead; see ledger_only_phases",
    }

    # RETRIEVE two-level + COLLISION + quality
    row["retrieve_two_level"] = _retrieve_two_level(
        envs.get("RETRIEVE"), run_files)
    row["collision"] = _collision_block(
        envs.get("COLLISION"), by_stage.get("COLLISION"))
    row["synthesize_validity"] = _synth_validity(envs.get("SYNTHESIZE"))
    atk_env = envs.get("ATTACK") or {}
    ar = atk_env.get("attack_results") or {}
    row["attack"] = {
        "class": "OBSERVED_IN_STAGE",
        "overall": ar.get("overall") if isinstance(ar, dict) else None,
        "status": (by_stage.get("ATTACK") or {}).get("status"),
        "skip_reason": (by_stage.get("ATTACK") or {}).get("skip_reason"),
        "evidence": "envelope_ATTACK.json $.attack_results + stage_log",
    }
    gen = (led.get("SYNTHESIZE") or {}).get("first_ok_provider")
    atk_lines = [ln for ln in ledger_lines
                 if ln.get("session_id") == sid
                 and ln.get("engine_stage") == "ATTACK"]
    atk_ok = next((ln.get("provider") for ln in atk_lines
                   if ln.get("ok")), None)
    row["attack"]["generator_provider"] = gen
    row["attack"]["attacker_chain"] = [
        ln.get("provider") for ln in atk_lines] or None
    if not (atk_lines and (by_stage.get("ATTACK") or {}).get(
            "status") == "OK"):
        row["attack"]["independence"] = {
            "class": "UNKNOWN",
            "note": "ATTACK did not run to OK on this run — "
                    "independence unmeasured (Art. XXV/LXI)"}
    else:
        row["attack"]["independence"] = {
            "class": "OFFLINE_DERIVED",
            "degree": independence_degree(gen, atk_ok),
            "generator": gen, "attacker": atk_ok,
            "authority": "provider_health.independence_degree (Art. X)",
        }

    # funnel row via the frozen instrument + determinism check
    out = REPO / "R521" / f"{YIELD_ROW_PREFIX}{idx}_{slug}.json"
    r = subprocess.run(
        [sys.executable, str(hv.INSTRUMENT), "--run-dir",
         str(dest), "--out", str(out)],
        capture_output=True, text=True, timeout=300)
    if r.returncode == 0:
        try:
            frow2 = json.loads(out.read_text(
                encoding="utf-8"))["rows"][0]
            row["funnel_row"] = frow2
            row["funnel_row_class"] = "OBSERVED_IN_STAGE"
        except Exception as exc:  # noqa: BLE001
            row["funnel_row"] = None
            row["funnel_row_class"] = "UNKNOWN"
            row["funnel_row_note"] = f"row parse: {exc}"[:160]
    else:
        row["funnel_row"] = None
        row["funnel_row_class"] = "UNKNOWN"
        row["funnel_row_note"] = f"instrument error: {r.stderr[-200:]}"
    row["row_file"] = str(out.relative_to(REPO))
    return row


# ---------------------------------------------------------------- merge store
def _load_existing():
    if OUT_HARVEST.exists():
        try:
            d = json.loads(OUT_HARVEST.read_text(encoding="utf-8"))
            if d.get("arm") != ARM:
                print(f"FATAL: existing harvest is arm={d.get('arm')}, "
                      f"not {ARM} — refusing cross-arm merge")
                sys.exit(2)
            rows = {r.get("session_id"): r for r in d.get("rows", [])}
            return d, rows
        except SystemExit:
            raise
        except Exception:
            pass
    return None, {}


def _is_placeholder(r):
    return "stage_table" not in r and "harvest" in r


def _write_merged(header_extra, new_rows):
    header, rows = _load_existing()
    for r in new_rows:
        sid = r.get("session_id")
        prev = rows.get(sid)
        if prev is not None and _is_placeholder(r) and not _is_placeholder(prev):
            continue
        rows[sid] = r
    out = {
        "artifact_type": "R521_ATTRIBUTION_HARVEST",
        "battery": "R521-STAGE-ATTRIBUTION",
        "arm": ARM,
        "instrument": f"{INSTRUMENT_ID}/{INSTRUMENT_VERSION}",
        "ms_module": "scripts/r516_harvest_attribution.py (frozen import)",
        "manifest_sha256": hashlib.sha256(
            MANIFEST.read_bytes()).hexdigest(),
        "harvested_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                           time.gmtime()),
        "n_rows": len(rows),
        "rows": [rows[k] for k in sorted(rows)],
        "reviewer_provenance": "AI_REVIEW",
    }
    out.update(header_extra or {})
    OUT_HARVEST.write_text(json.dumps(out, indent=1, sort_keys=True,
                                      ensure_ascii=False) + "\n",
                           encoding="utf-8")
    print(f"wrote {OUT_HARVEST} ({len(rows)} rows total)")
    return out


# ---------------------------------------------------------------- live fallback
def harvest_live(result_path: str, idx: int) -> int:
    """Harvest one run from its LIVE /result payload (owner-scoped).

    Full stage table from live stages[] timestamps (all stages present
    in the payload); ledger grouped by EVERY model_route role present;
    RETRIEVE two-level and envelope-derived quality are UNKNOWN with
    named reasons (live retrieval_route is the string "UNKNOWN"; spans
    need envelopes). Never backfilled.
    """
    d = json.loads(Path(result_path).read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_idx = {p["selection_index"]: p for p in manifest["problems"]}
    p = by_idx[idx]
    sid = d.get("session_id")
    row = {"arm": ARM, "problem_index": idx,
           "source_id": p["source_id"],
           "declared_family": p["declared_family"],
           "session_id": sid,
           "observation_source": "LIVE_API",
           "observation_note": (
               "harvested from the live owner-scoped /result payload; "
               "the durable row, when it lands, supersedes only on "
               "byte-identical session_id with fuller evidence")}
    table = []
    for e in d.get("stages") or []:
        st = e.get("stage")
        status = e.get("status")
        if status in ("SKIPPED_ADMISSION", "SKIPPED_UPSTREAM_FAILURE"):
            table.append({"stage": st, "entry_class": status,
                          "class": "LIVE_API", "status": status,
                          "wall_s": None,
                          "note": "unexecuted stage is None, never zero"})
        else:
            dur = _iso_seconds(e.get("started_at"), e.get("finished_at"))
            table.append({"stage": st, "entry_class": "EXECUTED",
                          "class": "OFFLINE_DERIVED_FROM_TIMESTAMPS",
                          "status": status,
                          "wall_s": round(dur, 3) if dur is not None else None,
                          "started_at": e.get("started_at"),
                          "finished_at": e.get("finished_at"),
                          "evidence": "live /result stages[] timestamps"})
    row["stage_table"] = table
    row["run_terminal"] = {"class": "OBSERVED_LIVE",
                           "status": d.get("status"),
                           "final_status": d.get("final_status")}
    calls = ((d.get("run_state") or {}).get("model_route") or {}).get(
        "calls") or []
    roles = sorted({c.get("role") for c in calls if c.get("role")})
    led = {}
    for role in roles:
        lines = [c for c in calls if (c.get("role") or "") == role]
        provs, models = [], []
        for c in lines:
            if c.get("provider") not in provs:
                provs.append(c.get("provider"))
            if c.get("model") not in models:
                models.append(c.get("model"))
        wall = sum(float(c.get("latency_ms") or 0)
                   for c in lines) / 1000.0
        led[role] = {
            "class": "LIVE_API", "n_calls": len(lines),
            "n_ok": sum(1 for c in lines if c.get("status") == "OK"),
            "attempts_seen": None, "retries_observed": None,
            "retries_note": "live calls carry no attempt numbers",
            "provider_chain": provs, "models": models,
            "provider_call_wall_s": round(wall, 3),
            "fallback_hops": None,
            "fallback_note": "live calls carry no fallback edges",
            "failures": sorted({str(c.get("status")) for c in lines
                                if c.get("status") != "OK"}),
            "first_ok_provider": next(
                (c.get("provider") for c in lines
                 if c.get("status") == "OK"), None),
        }
    row["ledger_per_role"] = led
    row["ledger_roles_present"] = roles
    ms = ((d.get("run_state") or {}).get("mechanism_state") or {})
    row["synthesize_validity"] = {
        "class": "LIVE_API_PARTIAL",
        "mechanism_text_chars": len(str(ms.get("mechanism") or "")),
        "candidate_count": ms.get("candidate_count"),
        "evidence_pack_present": bool(d.get("evidence_pack")),
        "span_verbatim_rate": None,
        "span_note": "envelope-level spans unavailable live (Art. XXV)",
    }
    row["retrieve_two_level"] = {
        "class": "UNKNOWN",
        "note": "live retrieval_route is uninformative; two-level "
                "attribution needs the durable RETRIEVE envelope "
                "(Art. XXV)",
    }
    row["collision"] = {
        "class": "LIVE_API",
        "status": next((e.get("status") for e in d.get("stages") or []
                        if e.get("stage") == "COLLISION"), None),
        "note": "leg-level timing unavailable live",
    }
    row["attack"] = {
        "class": "LIVE_API",
        "overall": (d.get("final_state") or {}).get("adversarial_overall"),
        "status": next((e.get("status") for e in d.get("stages") or []
                        if e.get("stage") == "ATTACK"), None),
    }
    row["funnel_row"] = None
    row["funnel_row_class"] = "UNKNOWN"
    row["funnel_row_note"] = "funnel instrument needs durable run bytes"
    _write_merged({"live_harvest_note": (
        "rows tagged LIVE_API predate their durable rows; re-harvest "
        "merges by session_id when the branch lands")}, [row])
    return 0


# ---------------------------------------------------------------- durable arm
def harvest_arm() -> int:
    branch = "origin/runtime-state-hf"
    print("fetching durable branch ...")
    fr = _git("fetch", "origin", "runtime-state-hf", timeout=300)
    print("fetch rc=", fr.returncode)
    sessions = json.loads(SESSIONS.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    ls = _git("ls-tree", "--name-only", f"{branch}:runs", timeout=120)
    slugs = sorted(ls.stdout.decode("utf-8", "replace").split())
    slug_of = {}
    for slug in slugs:
        for name in ("run_manifest.json", "final_state.json"):
            raw = _show(f"{branch}:runs/{slug}/{name}")
            if not raw:
                continue
            try:
                dd = json.loads(raw.decode("utf-8"))
            except Exception:
                continue
            if dd.get("session_id"):
                slug_of[dd["session_id"]] = slug
                break
    print(f"mapped {len(slug_of)} sessions to slugs")

    led_raw = _show(f"{branch}:model_routing/ledger.jsonl") or b""
    ledger_lines = []
    for line in led_raw.decode("utf-8", "replace").splitlines():
        try:
            ledger_lines.append(json.loads(line))
        except Exception:
            continue
    print(f"ledger lines: {len(ledger_lines)}")

    try:
        import tempfile
        tmp = Path(tempfile.mkdtemp(prefix="r521_harvest_"))
        rows = []
        for s in sessions["submissions"]:
            sid = s.get("session_id")
            idx = s.get("problem_index")
            slug = slug_of.get(sid)
            if not slug:
                rows.append({"arm": ARM, "problem_index": idx,
                             "session_id": sid, "harvest": "NOT_YET",
                             "note": "session not on durable branch yet"})
                print(f"#{idx} {sid}: not on durable branch yet")
                continue
            dest = tmp / "runs" / slug
            dest.mkdir(parents=True, exist_ok=True)
            fl = _git("ls-tree", "--name-only",
                      f"{branch}:runs/{slug}", timeout=120)
            files = sorted(
                fl.stdout.decode("utf-8", "replace").split())
            for f in files:
                raw = _show(f"{branch}:runs/{slug}/{f}")
                if raw is not None:
                    (dest / f).write_bytes(raw)
            man_raw = _show(f"{branch}:runs/{slug}/run_manifest.json")
            man = json.loads(man_raw.decode("utf-8")) if man_raw else {}
            by_idx = {pp["selection_index"]: pp
                      for pp in manifest["problems"]}
            pp = by_idx[idx]
            row = harvest_row(dest, files, ledger_lines, idx,
                              pp["source_id"], pp["declared_family"],
                              sid, slug, man)
            rows.append(row)
            st = {e["stage"]: e.get("status")
                  for e in row["stage_table"]
                  if e.get("stage") in ("RETRIEVE", "SYNTHESIZE",
                                        "MECHANISM_SPACE", "COLLISION",
                                        "PHYSICS", "ATTACK")}
            print(f"#{idx} {slug[-24:]}: " + " ".join(
                f"{k}={v}" for k, v in st.items()))
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    _write_merged({}, rows)
    return 0


# ---------------------------------------------------------------- compare
def _agg(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return {"n": 0, "mean": None, "median": None, "min": None,
                "max": None, "stdev": None, "values": []}
    return {"n": len(vals), "mean": round(sum(vals) / len(vals), 3),
            "median": round(statistics.median(vals), 3),
            "min": round(min(vals), 3), "max": round(max(vals), 3),
            "stdev": round(statistics.pstdev(vals), 3)
            if len(vals) > 1 else 0.0,
            "values": [round(v, 3) for v in vals]}


def compare(base_path, opt_path, out_path):
    base = json.loads(Path(base_path).read_text(encoding="utf-8"))
    opt = json.loads(Path(opt_path).read_text(encoding="utf-8"))
    ar = {r["problem_index"]: r for r in base["rows"]
          if "stage_table" in r}
    br = {r["problem_index"]: r for r in opt["rows"]
          if "stage_table" in r}
    pairs = []
    for idx in sorted(set(ar) & set(br)):
        ra, rb = ar[idx], br[idx]
        ta = {e["stage"]: e for e in ra["stage_table"]}
        tb = {e["stage"]: e for e in rb["stage_table"]}
        pair = {"problem_index": idx,
                "source_id": ra["source_id"],
                "declared_family": ra["declared_family"],
                "before_source": ra.get("observation_source"),
                "after_source": rb.get("observation_source"),
                "stages": {}}
        for st in sorted(set(ta) | set(tb)):
            ea, eb = ta.get(st) or {}, tb.get(st) or {}
            wa, wb = ea.get("wall_s"), eb.get("wall_s")
            pair["stages"][st] = {
                "before_wall_s": wa, "after_wall_s": wb,
                "delta_s": (round(wb - wa, 3)
                            if wa is not None and wb is not None
                            else None),
                "before_status": ea.get("status"),
                "after_status": eb.get("status"),
            }
        la, lb = ra.get("ledger_per_role", {}), rb.get(
            "ledger_per_role", {})
        pair["ledger"] = {}
        for role in sorted(set(la) | set(lb)):
            ba, bb = la.get(role) or {}, lb.get(role) or {}
            pair["ledger"][role] = {
                "before_call_wall_s": ba.get("provider_call_wall_s"),
                "after_call_wall_s": bb.get("provider_call_wall_s"),
                "before_providers": ba.get("provider_chain"),
                "after_providers": bb.get("provider_chain"),
                "before_retries": ba.get("retries_observed"),
                "after_retries": bb.get("retries_observed"),
                "before_fallbacks": ba.get("n_fallback_hops"),
                "after_fallbacks": bb.get("n_fallback_hops"),
            }
        pair["ledger_only_phases"] = {
            "before": sorted((ra.get("ledger_only_phases") or {}).keys()),
            "after": sorted((rb.get("ledger_only_phases") or {}).keys()),
        }
        pair["run_residual_s"] = {
            "before": (ra.get("run_residual_s") or {}).get("residual_s"),
            "after": (rb.get("run_residual_s") or {}).get("residual_s"),
        }
        pairs.append(pair)
    agg = {}
    for tag, rows in (("before", [ar[i] for i in sorted(
            set(ar) & set(br))]),
                      ("after", [br[i] for i in sorted(
                          set(ar) & set(br))])):
        per_stage = {}
        stages = set()
        for r in rows:
            for e in r["stage_table"]:
                if e.get("entry_class") == "EXECUTED":
                    stages.add(e["stage"])
        for st in sorted(stages):
            per_stage[st] = _agg([
                next((e.get("wall_s") for e in r["stage_table"]
                      if e.get("stage") == st), None) for r in rows])
        # provider / retry / fallback contributions across all roles
        prov, retr, fb = {}, {}, {}
        for r in rows:
            for role, b in (r.get("ledger_per_role") or {}).items():
                for pv in b.get("provider_chain") or []:
                    prov[pv] = prov.get(pv, 0) + (b.get(
                        "provider_call_wall_s") or 0)
                if b.get("retries_observed"):
                    retr[role] = retr.get(role, 0) + b["retries_observed"]
                if b.get("n_fallback_hops"):
                    fb[role] = fb.get(role, 0) + b["n_fallback_hops"]
        agg[tag] = {"n_paired": len(rows), "per_stage": per_stage,
                    "provider_wall_contribution_s": {
                        k: round(v, 3) for k, v in prov.items()},
                    "retry_counts": retr, "fallback_counts": fb}
    out = {
        "artifact_type": "R521_ATTRIBUTION_COMPARISON",
        "battery": "R521-STAGE-ATTRIBUTION",
        "before_harvest": str(base_path),
        "after_harvest": str(opt_path),
        "n_paired_problems": len(pairs),
        "pairs": pairs,
        "aggregates": agg,
        "statistics_note": ("raw paired rows + arm aggregates "
                            "(mean/median/min/max/stdev; no significance "
                            "theater). Classification lives in the round "
                            "record."),
        "reviewer_provenance": "AI_REVIEW",
    }
    Path(out_path).write_text(json.dumps(out, indent=1, sort_keys=True,
                                         ensure_ascii=False) + "\n",
                              encoding="utf-8")
    print(f"wrote {out_path} ({len(pairs)} paired problems)")
    return 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--compare", nargs=2, metavar=("BEFORE", "AFTER"),
                    default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--live", default=None,
                    help="live /result payload path to harvest")
    ap.add_argument("--idx", type=int, default=None,
                    help="manifest selection_index for --live")
    args = ap.parse_args()
    if args.compare:
        sys.exit(compare(args.compare[0], args.compare[1],
                         args.out or "R521/ATTR_COMPARISON.json"))
    if args.live:
        if args.idx is None:
            print("FATAL: --live requires --idx")
            sys.exit(2)
        sys.exit(harvest_live(args.live, args.idx))
    sys.exit(harvest_arm())

#!/usr/bin/env python3
"""R412 gradient arm v2 — the sealed runner.

Runs the SAME 10 seeds as the v1 arm under the v2 instrument (the
only deltas: the field-line TVM proposal prompt + the v2 parser/
evidence contract + RAW proposal persistence + family-expanded
queries). Everything downstream (backcast, feasibility, why-not,
availability, causal delta, fresh novelty, fresh attack) reuses the
SEALED v1 machinery unchanged. Output goes ONLY to
R412/GRADIENT_V2/RUN/ — the v1 artifacts are never touched.

The runner is fail-closed: every stage re-verifies the v2.1 seal
first (population hash, substrate hashes, prompts, family map, the
10-seed allocation) and REFUSES on drift. The zai gateway is
managed as a child process for the invocation's duration.

Stages (resumable; use --limit for bounded invocations):
  seal        pin verification, no model calls
  tvm-build   the v2 TVM construction (12-call TOTAL cap, raw
              persistence, allocation rungs first)
  tvm-freeze  the Art. XLIV snapshot + sha256
  ga3         the deterministic cheapest-kill query per seed
  ga4         the capability backcast (v1 machinery)
  ga5         transfer feasibility (v1 machinery)
  ga55        why-not-already-adopted (v1 machinery)
  ga6         present-day availability (v1 machinery)
  ga7         causal-architecture delta (v1 machinery)
  ga8         fresh novelty (v1 machinery)
  ga9         fresh attack with the NOT_CALIBRATED caveat
  finalize    the funnel + the operator's Phase L comparison table
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "R412" / "GRADIENT_V2"))

OUT_DIR = REPO / "R412" / "GRADIENT_V2" / "RUN"
PREREG = REPO / "R412" / "GRADIENT_V2" / \
    "R412_GRADIENT_V2_1_PREREGISTRATION.json"
FAM_MAP_V2 = REPO / "R412" / "GRADIENT_V2" / \
    "CAPABILITY_FAMILY_MAP_V2.json"
GA1B_SRC = REPO / "R412" / "RECOVERY_ARM" / "GRADIENT_RUN" / \
    "ga1b.jsonl"
GA2_SRC = REPO / "R412" / "RECOVERY_ARM" / "GRADIENT_RUN" / \
    "ga2.jsonl"
RUN_R411 = REPO / "R411" / "DISCOVERY_RUN"
WATERFALL = REPO / "R412" / "R412_DEATH_CAUSE_WATERFALL.json"

TVM_CONSTRUCTED = OUT_DIR / "TVM_V2_CONSTRUCTED.json"
TVM_FROZEN = OUT_DIR / "TVM_V2_FROZEN.json"

MODEL_PINS = {"ENGINE_LLM_PROVIDER": "zai"}

TERMINAL_STATUSES = {"OK", "INSUFFICIENT_FRONTIER"}
MAX_ATTEMPTS = 2

GW_PORT = 8787


def _utc() -> str:
    import datetime
    return datetime.datetime.now(
        datetime.timezone.utc).isoformat()


def _load(p: Path):
    return json.loads(p.read_text())


def _read_lines(p: Path):
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines()
            if l.strip()]


def _append(p: Path, rec: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(json.dumps(rec) + "\n")


def _latest(lines, key, val):
    out = None
    for l in lines:
        if l.get(key) == val:
            out = l
    return out


# ---------------------------------------------------------------------------
# gateway management (child process for the invocation duration)
# ---------------------------------------------------------------------------

def _gateway_alive() -> bool:
    import urllib.request
    try:
        urllib.request.urlopen(
            f"http://127.0.0.1:{GW_PORT}/healthz", timeout=3)
        return True
    except Exception:
        return False


def _start_gateway() -> bool:
    import secrets
    key = "r412v2-" + secrets.token_hex(8)
    env = dict(os.environ, ZAI_GATEWAY_KEY=key, ZAI_API_KEY=key)
    subprocess.run(["pkill", "-f", "zai_gateway.mjs"],
                   capture_output=True, timeout=5)
    time.sleep(0.5)
    proc = subprocess.Popen(
        ["node", "scripts/zai_gateway.mjs", str(GW_PORT)],
        cwd=str(REPO), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True)
    for _ in range(30):
        time.sleep(0.5)
        if _gateway_alive():
            os.environ["ZAI_API_KEY"] = key
            os.environ["ZAI_GATEWAY_KEY"] = key
            return True
    proc.terminate()
    return False


def _with_pins(fn):
    saved = {k: os.environ.get(k, "") for k in MODEL_PINS}
    for k, v in MODEL_PINS.items():
        os.environ[k] = v
    try:
        return fn()
    finally:
        for k, v in saved.items():
            if v:
                os.environ[k] = v
            else:
                os.environ.pop(k, None)


def _llm(prompt, system, purpose):
    from discovery_fabric.engine.adapters import load_credentials
    load_credentials()
    from discovery_fabric.engine.mechanism_space import llm_generate
    return llm_generate(prompt, system=system, purpose=purpose,
                        max_tokens=2600)


def _retrieve(query: str):
    from discovery_fabric.retrieval_fabric.pipeline import \
        retrieve_fabric
    problem = {"device": query[:120], "failure_mode":
               query[120:240] or query[:120]}
    items, report = retrieve_fabric(
        problem, lane_caps=None,
        enable_reciprocal=False, enable_unpaywall=False)
    return items, report


def _cand(cid):
    scored = _load(RUN_R411 / "scored_pool.json")
    for c in scored:
        if c["candidate_id"] == cid:
            return c
    raise KeyError(cid)


def _death(cid):
    w = _load(WATERFALL)
    for d in w["deaths"]:
        if d["candidate_id"] == cid:
            return d
    raise KeyError(cid)


def _priority():
    prereg = _load(PREREG)
    return prereg["seed_allocation"]["priority_order"], prereg


# ---------------------------------------------------------------------------
# stage: seal (fail-closed pin verification; no model calls)
# ---------------------------------------------------------------------------

def stage_seal(limit=None) -> int:
    import hashlib
    if not PREREG.exists():
        print("REFUSED: v2.1 preregistration absent — seal first")
        return 1
    prereg = _load(PREREG)
    if prereg["run_gate"]["state"] != "RUN_ALLOWED":
        print(f"REFUSED: run gate {prereg['run_gate']['state']}")
        return 1
    problems = []
    # population hash live recompute
    from discovery_fabric.r412.recovery import \
        build_population_accounting
    recomputed = build_population_accounting(
        _load(RUN_R411 / "funnel_collision.json"),
        _load(RUN_R411 / "scored_pool.json"),
        _load(RUN_R411 / "shortlist.json"),
        _load(RUN_R411 / "selection.json"),
        _load(WATERFALL))
    if recomputed["population_sha256"] != \
            prereg["population"]["population_sha256"]:
        problems.append("population hash drift vs live records")
    # substrate pins
    for name, s in prereg["tvm_substrate_hashes"].items():
        p = REPO / s["path"]
        if not p.exists():
            problems.append(f"substrate absent: {name}")
            continue
        if hashlib.sha256(p.read_bytes()).hexdigest() != s["sha256"]:
            problems.append(f"substrate hash drift: {name}")
    # prompt pins
    for name, pin in prereg["prompt_pins"].items():
        p = REPO / "R412" / "GRADIENT_V2" / "PROMPTS" / \
            f"{name}.json"
        if hashlib.sha256(p.read_bytes()).hexdigest() != \
                pin["sha256"]:
            problems.append(f"prompt hash drift: {name}")
    # family map pin
    if hashlib.sha256(FAM_MAP_V2.read_bytes()).hexdigest() != \
            prereg["capability_family_map"]["sha256"]:
        problems.append("family map hash drift")
    # allocation vs committed ga3
    ga3_ids = [l["candidate_id"] for l in _read_lines(
        REPO / "R412" / "RECOVERY_ARM" / "GRADIENT_RUN" /
        "ga3.jsonl")]
    if ga3_ids != prereg["seed_allocation"]["priority_order"]:
        problems.append("allocation drift vs committed ga3")
    rec = {"ts": _utc(), "stage": "V2_SEAL_CHECK",
           "seal_valid": not problems, "problems": problems,
           "action": "RUN_ALLOWED" if not problems else "REFUSE"}
    _append(OUT_DIR / "seal.jsonl", rec)
    if problems:
        print("REFUSED: seal problems:", *problems, sep="\n  ")
        return 1
    print("v2 seal verified: population hash, substrates, prompts, "
          "family map, allocation — all pins match live bytes")
    return 0


# ---------------------------------------------------------------------------
# stage: tvm-build (the v2 instrument)
# ---------------------------------------------------------------------------

def stage_tvm_build(limit=None) -> int:
    from discovery_fabric.r412.gradient_v2 import (
        build_v2_query, parse_v2_proposals, verify_v2_proposals,
        construction_log_entry, TVM_V2_VERSION)
    if stage_seal() != 0:
        return 1
    prereg = _load(PREREG)
    cap = prereg["token_and_cost_budgets"][
        "tvm_construction_llm_calls_max"]
    priority = prereg["seed_allocation"]["priority_order"]
    ga1b = [l for l in _read_lines(GA1B_SRC)
            if l.get("status") == "OK"]
    rung_by_cid = {}
    rungs = {}
    for l in ga1b:
        rung = (l.get("gate") or {}).get("capability_rung")
        if rung:
            rung_by_cid[l["candidate_id"]] = rung
            rungs.setdefault(rung.casefold(), rung)
    ordered = []
    for cid in priority:
        rung = rung_by_cid.get(cid)
        if rung and rung.casefold() not in ordered:
            ordered.append(rung.casefold())
    for key in rungs:
        if key not in ordered:
            ordered.append(key)
    if TVM_CONSTRUCTED.exists():
        tvm = _load(TVM_CONSTRUCTED)
    else:
        tvm = {"tvm_version": TVM_V2_VERSION, "entries": [],
               "construction_log": []}
    log = tvm.get("construction_log") or []
    attempted_done = {str(e.get("rung")).casefold() for e in log
                      if e.get("n_retrieved") is not None}
    shortfall_recorded = {str(e.get("rung")).casefold() for e in log
                          if e.get("status") ==
                          "INCOMPLETE_BUDGET_SHORTFALL"}
    built = 0
    shortfall = []
    total_attempts = len(attempted_done)
    for key in ordered:
        rung = rungs[key]
        if key in attempted_done or key in shortfall_recorded:
            continue
        if total_attempts + built >= cap:
            shortfall.append(rung)
            continue
        if limit is not None and built >= limit:
            break
        q = build_v2_query(rung)
        try:
            items, report = _retrieve(q["query"])
        except Exception as e:
            tvm["construction_log"].append(
                {"rung": rung, "status": "INCOMPLETE_TRANSPORT",
                 "error": str(e)[:200]})
            _write_tvm(tvm)
            continue
        records = [
            {"record_id": r.get("record_id") or r.get("id"),
             "title": r.get("title"),
             "abstract": str(r.get("abstract") or
                             r.get("snippet") or "")[:600]}
            for r in (items or [])[:12]]
        # the v2 proposal prompt from the sealed template
        tmpl = _load(REPO / "R412" / "GRADIENT_V2" / "PROMPTS" /
                     "TVM_V2_FRONTIER_ENTRY_PROPOSAL.json")
        brief = json.dumps({
            "capability_rung": rung,
            "family": q.get("family"),
            "capability_family": q.get("capability_family"),
            "measurement_dimension":
                q.get("measurement_dimension"),
            "search_vocabulary_evidence_grounded":
                q.get("evidence_vocabulary"),
            "search_vocabulary_exploratory_priority":
                q.get("exploratory_vocabulary"),
        }, indent=1)
        recs = "\n".join(
            f"- record_id: {r['record_id']} | title: "
            f"{str(r['title'])[:120]} | abstract: "
            f"{r['abstract'][:400]}" for r in records) or "(none)"
        prompt = tmpl["template"].replace(
            "{{SEARCH_BRIEF}}", brief).replace(
            "{{RECORDS}}", recs)
        # the template is self-contained; append brief+records
        prompt = (tmpl["template"] +
                  "\n\nSEARCH BRIEF:\n" + brief +
                  "\n\nSOURCE RECORDS (title+abstract is the source "
                  "text for quoted_span):\n" + recs + "\n")
        meta = _with_pins(lambda: _llm(
            prompt,
            system="You bind measured evidence verbatim. Never "
                   "assert numbers.",
            purpose="r412_gradient_v2_tvm_proposal"))
        parsed = parse_v2_proposals(meta.get("content") or "")
        gate = verify_v2_proposals(
            parsed.get("proposals") or [], records, rung,
            retrieved_at=(report or {}).get("retrieved_at"))
        tvm["entries"].extend(gate["admitted"])
        tvm["construction_log"].append(construction_log_entry(
            rung, records, parsed, gate,
            model=meta.get("model"),
            retrieved_at=(report or {}).get("retrieved_at"),
            fabric_version=(report or {}).get("fabric_version"),
            prompt_hash=meta.get("prompt_hash"),
            output_hash=meta.get("output_hash"),
            raw_llm_output=str(meta.get("content") or "")[:20000],
            query=q))
        built += 1
        _write_tvm(tvm)
        print(f"  rung '{rung}': {len(gate['admitted'])} admitted / "
              f"{len(gate['rejected'])} rejected "
              f"({parsed['parse_status']})")
    for rung in shortfall:
        tvm["construction_log"].append({
            "rung": rung,
            "status": "INCOMPLETE_BUDGET_SHORTFALL",
            "note": "the sealed 12-call construction cap was reached "
                    "before this rung (recorded, never dropped; no "
                    "re-allocation)",
        })
        print(f"  rung '{rung}': INCOMPLETE_BUDGET_SHORTFALL")
    _write_tvm(tvm)
    print(f"tvm-build-v2: {len(tvm['entries'])} span-verified "
          f"entries across {len(rungs)} rungs "
          f"({len(attempted_done) + built} attempts)")
    return 0


def _write_tvm(tvm) -> None:
    tvm["n_entries"] = len(tvm.get("entries") or [])
    TVM_CONSTRUCTED.parent.mkdir(parents=True, exist_ok=True)
    TVM_CONSTRUCTED.write_text(json.dumps(tvm, indent=1) + "\n")


def stage_tvm_freeze(limit=None) -> int:
    from discovery_fabric.r412.gradient_v2 import build_v2_snapshot
    if stage_seal() != 0:
        return 1
    if not TVM_CONSTRUCTED.exists():
        print("REFUSED: no constructed v2 TVM to freeze")
        return 1
    snap = build_v2_snapshot(_load(TVM_CONSTRUCTED))
    TVM_FROZEN.parent.mkdir(parents=True, exist_ok=True)
    TVM_FROZEN.write_text(json.dumps(snap, indent=1) + "\n")
    print(f"tvm-freeze-v2: {snap['n_entries']} entries, sha256="
          f"{snap['sha256'][:16]}... — GA-4 unlocked")
    return 0


# ---------------------------------------------------------------------------
# stage: ga3 (the deterministic cheapest kill on the v2 map)
# ---------------------------------------------------------------------------

def stage_ga3(limit=None) -> int:
    from discovery_fabric.r412.gradient_v2 import query_v2_tvm
    if stage_seal() != 0:
        return 1
    if not TVM_FROZEN.exists():
        print("REFUSED: the v2 TVM must be frozen before GA-3 "
              "(Art. XLIV)")
        return 1
    tvm = _load(TVM_FROZEN)
    priority = _load(PREREG)["seed_allocation"]["priority_order"]
    ga1b = [l for l in _read_lines(GA1B_SRC)
            if l.get("status") == "OK"]
    ordered = [l for l in ga1b if l["candidate_id"] in priority]
    path = OUT_DIR / "ga3.jsonl"
    lines = _read_lines(path)
    for l in ordered:
        cid = l["candidate_id"]
        if _latest(lines, "candidate_id", cid):
            continue
        rung = (l.get("gate") or {}).get("capability_rung")
        q = query_v2_tvm(tvm, rung)
        ranked = [
            {"domain": s.get("domain"),
             "metric": s.get("metric"),
             "slope": s.get("slope"),
             "unit": s.get("unit"),
             "from_year": s.get("from_year"),
             "to_year": s.get("to_year"),
             "points": s.get("points")}
            for s in q.get("slopes") or []]
        rec = {"candidate_id": cid, "ts": _utc(), "rung": rung,
               "verdict": q["verdict"], "ranked": ranked,
               "n_entries_on_rung": q.get("n_entries_on_rung")}
        _append(path, rec)
        lines.append(rec)
        print(f"  {cid}: {q['verdict']} (rung={rung})")
    n_dead = sum(1 for l in lines
                 if l.get("verdict") == "DEAD_AT_TVM_QUERY")
    print(f"ga3-v2: {len(lines)} queries, {n_dead} cheapest-kills")
    return 0


# ---------------------------------------------------------------------------
# stages ga4..ga9 — the sealed v1 machinery, RUN_V2 paths
# ---------------------------------------------------------------------------

def stage_ga4(limit=None) -> int:
    from discovery_fabric.r412.gradient import (
        build_backcast_prompt, parse_backcast, verify_backcast)
    if stage_seal() != 0:
        return 1
    if not TVM_FROZEN.exists():
        print("REFUSED: the TVM must be frozen before GA-4")
        return 1
    priority, _ = _load(PREREG)["seed_allocation"][
        "priority_order"], None
    allocation = set(priority)
    ga3 = _read_lines(OUT_DIR / "ga3.jsonl")
    path = OUT_DIR / "ga4.jsonl"
    lines = _read_lines(path)
    done = 0
    for q in ga3:
        cid = q["candidate_id"]
        if q.get("verdict") != "FAST_MOVERS_RANKED":
            continue
        if cid not in allocation:
            print(f"  {cid}: REFUSED backcast outside the sealed "
                  f"allocation")
            continue
        last = _latest(lines, "candidate_id", cid)
        if last and last.get("status") in TERMINAL_STATUSES:
            continue
        if last and last.get("attempt", 1) >= MAX_ATTEMPTS:
            continue
        if limit is not None and done >= limit:
            break
        attempt = (last.get("attempt", 0) + 1) if last else 1
        deficit = (_latest(_read_lines(GA1B_SRC),
                           "candidate_id", cid) or {}).get("gate") \
            or {}
        prompt = build_backcast_prompt(
            _cand(cid), _death(cid), deficit, q)
        meta = _with_pins(lambda: _llm(
            prompt,
            system="You are a rigorous engineering scientist "
                   "transferring a causal mechanism, never an "
                   "industry label.",
            purpose="r412_gradient_v2_ga4_backcast"))
        parsed = parse_backcast(meta.get("content") or "")
        gate = verify_backcast(parsed, _cand(cid), deficit)
        status = ("OK" if meta.get("ok") and
                  gate["gate"] in ("PASS", "HONEST_STOP")
                  and parsed["parse_status"] in
                  ("OK", "INSUFFICIENT_FRONTIER")
                  else "INCOMPLETE_TRANSPORT" if not meta.get("ok")
                  else "PARSE_INCOMPLETE")
        if status == "OK" and parsed["parse_status"] == \
                "INSUFFICIENT_FRONTIER":
            status = "INSUFFICIENT_FRONTIER"
        rec = {
            "candidate_id": cid, "ts": _utc(), "attempt": attempt,
            "status": status, "backcast": parsed, "gate": gate,
            "prompt_hash": meta.get("prompt_hash"),
            "output_hash": meta.get("output_hash"),
            "model": meta.get("model"),
            "reviewer_provenance": "AI_REVIEW",
        }
        _append(path, rec)
        lines.append(rec)
        done += 1
        print(f"  {cid}: {status}")
    n_ok = sum(1 for l in lines if l.get("status") == "OK")
    print(f"ga4: {n_ok} backcasts OK ({len(lines)} invocations)")
    return 0


def stage_ga5(limit=None) -> int:
    from discovery_fabric.r412.gradient import (
        build_feasibility_prompt, parse_feasibility, verify_feasibility)
    if stage_seal() != 0:
        return 1
    ga4 = [l for l in _read_lines(OUT_DIR / "ga4.jsonl")
           if l.get("status") == "OK"]
    path = OUT_DIR / "ga5.jsonl"
    lines = _read_lines(path)
    done = 0
    for b in ga4:
        cid = b["candidate_id"]
        if _latest(lines, "candidate_id", cid):
            continue
        if limit is not None and done >= limit:
            break
        deficit = (_latest(_read_lines(GA1B_SRC),
                           "candidate_id", cid) or {}).get("gate") \
            or {}
        fields = (b.get("backcast") or {}).get("fields") or {}
        query = " ".join([str(fields.get("OUTCOME") or ""),
                          str(fields.get("TECHNOLOGY") or "")])[:240]
        try:
            items, _report = _retrieve(query)
            anchor_records = [
                {"record_id": r.get("record_id") or r.get("id"),
                 "title": r.get("title"),
                 "abstract": str(r.get("abstract") or
                                 r.get("snippet") or "")[:600]}
                for r in (items or [])[:12]]
            anchor_ids = [str(r["record_id"])
                          for r in anchor_records]
            transport_error = None
        except Exception as e:
            anchor_records, anchor_ids = [], []
            transport_error = str(e)[:200]
        prompt = build_feasibility_prompt(
            b.get("backcast") or {}, deficit)
        meta = _with_pins(lambda: _llm(
            prompt,
            system="You assess transfer feasibility honestly. "
                   "Unanchored assumptions are recorded, never "
                   "invented away.",
            purpose="r412_gradient_v2_ga5_feasibility"))
        parsed = parse_feasibility(meta.get("content") or "")
        gate = verify_feasibility(parsed, anchor_ids)
        status = ("OK" if meta.get("ok") and
                  parsed.get("parse_status") == "OK"
                  else "INCOMPLETE_TRANSPORT" if not meta.get("ok")
                  else "PARSE_INCOMPLETE")
        if transport_error and status != "OK":
            status = "INCOMPLETE_TRANSPORT"
        rec = {
            "candidate_id": cid, "ts": _utc(), "status": status,
            "feasibility": parsed, "gate": gate,
            "anchor_pool": {
                "n_records": len(anchor_records),
                "record_ids": anchor_ids[:12],
                "transport_error": transport_error},
            "model": meta.get("model"),
            "reviewer_provenance": "AI_REVIEW"}
        _append(path, rec)
        lines.append(rec)
        done += 1
        print(f"  {cid}: {status} ({gate.get('verdict')})")
    n_ok = sum(1 for l in lines if l.get("status") == "OK")
    print(f"ga5: {n_ok} feasibility records ({len(lines)} calls)")
    return 0


def stage_ga55(limit=None) -> int:
    from discovery_fabric.r412.gradient import (
        build_why_not_prompt, parse_why_not, verify_why_not)
    if stage_seal() != 0:
        return 1
    ga5 = [l for l in _read_lines(OUT_DIR / "ga5.jsonl")
           if l.get("status") == "OK"]
    path = OUT_DIR / "ga55.jsonl"
    lines = _read_lines(path)
    done = 0
    for f in ga5:
        cid = f["candidate_id"]
        if _latest(lines, "candidate_id", cid):
            continue
        if limit is not None and done >= limit:
            break
        ga4_rec = _latest(_read_lines(OUT_DIR / "ga4.jsonl"),
                          "candidate_id", cid)
        fields = (ga4_rec.get("backcast") or {}).get("fields") or {}
        domain = str(_cand(cid).get("target_domain") or
                     _cand(cid).get("domain_id") or "")[:80]
        capability = str(fields.get("CAPABILITY") or "")[:200]
        query = f"{domain} limitations state of the art review"
        try:
            items, _report = _retrieve(query)
            records = [
                {"record_id": r.get("record_id") or r.get("id"),
                 "title": r.get("title"),
                 "abstract": str(r.get("abstract") or
                                 r.get("snippet") or "")[:600]}
                for r in (items or [])[:12]]
            transport_error = None
        except Exception as e:
            records = []
            transport_error = str(e)[:200]
        prompt = build_why_not_prompt(domain, capability, records)
        meta = _with_pins(lambda: _llm(
            prompt,
            system="You investigate adoption absence honestly. "
                   "UNKNOWN is a valid answer.",
            purpose="r412_gradient_v2_ga55_why_not"))
        parsed = parse_why_not(meta.get("content") or "")
        gate = verify_why_not(parsed, records)
        status = ("OK" if meta.get("ok") and
                  parsed.get("parse_status") == "OK"
                  else "INCOMPLETE_TRANSPORT" if not meta.get("ok")
                  else "PARSE_INCOMPLETE")
        if transport_error and status != "OK":
            status = "INCOMPLETE_TRANSPORT"
        rec = {
            "candidate_id": cid, "ts": _utc(), "status": status,
            "why_not": parsed, "gate": gate,
            "target_domain_records": {
                "n_records": len(records),
                "record_ids": [str(r.get("record_id"))
                               for r in records][:12],
                "transport_error": transport_error},
            "model": meta.get("model"),
            "reviewer_provenance": "AI_REVIEW"}
        _append(path, rec)
        lines.append(rec)
        done += 1
        print(f"  {cid}: {status} (finding={gate.get('finding')})")
    n_ok = sum(1 for l in lines if l.get("status") == "OK")
    print(f"ga55: {n_ok} why-not records ({len(lines)} calls)")
    return 0


def stage_ga6(limit=None) -> int:
    from discovery_fabric.r412.temporal import (
        build_decomposition_prompt, parse_decomposition,
        cross_check_capabilities)
    from discovery_fabric.r412.temporal_pipeline import (
        verify_capability)
    from discovery_fabric.r412.gradient import availability_map
    from discovery_fabric.r412.recovery import availability_branch
    if stage_seal() != 0:
        return 1
    ga4 = [l for l in _read_lines(OUT_DIR / "ga4.jsonl")
           if l.get("status") == "OK"]
    dec_path = OUT_DIR / "ga6_decomposition.jsonl"
    ver_path = OUT_DIR / "ga6_verification.jsonl"
    av_path = OUT_DIR / "ga6_availability.jsonl"
    dec_lines = _read_lines(dec_path)
    ver_lines = _read_lines(ver_path)
    done = 0
    for b in ga4:
        cid = b["candidate_id"]
        last_dec = _latest(dec_lines, "candidate_id", cid)
        if not last_dec or last_dec.get("status") != "OK":
            if limit is not None and done >= limit:
                break
            pseudo_evo = {
                "fields": {
                    "NEW_ARCHITECTURE":
                        (b.get("backcast") or {}).get("fields",
                                                     {}).get(
                                                         "OUTCOME",
                                                         ""),
                    "MECHANISM_CHAIN":
                        (b.get("backcast") or {}).get("fields",
                                                     {}).get(
                        "PHYSICAL_MECHANISM", ""),
                    "INTERVENTION":
                        (b.get("backcast") or {}).get("fields",
                                                     {}).get(
                        "TECHNOLOGY", ""),
                    "PREDICTED_EFFECT":
                        (b.get("backcast") or {}).get("fields",
                                                     {}).get(
                        "PREDICTED_NEW_EFFECT", ""),
                    "BOUNDARY_CONDITIONS": ""},
                "capabilities": [
                    c for c in (b.get("backcast") or {}).get(
                        "capabilities") or []
                    if c.get("parse_status") == "OK"]}
            prompt = build_decomposition_prompt(pseudo_evo)
            meta = _with_pins(lambda: _llm(
                prompt,
                system="You decompose requirements backward and "
                       "judge today's demonstrated capability "
                       "honestly.",
                purpose="r412_gradient_v2_ga6_decomposition"))
            parsed = parse_decomposition(meta.get("content") or "")
            cross = cross_check_capabilities(pseudo_evo, parsed)
            status = ("OK" if meta.get("ok") and
                      parsed.get("parse_status") == "OK"
                      else "INCOMPLETE_TRANSPORT" if not
                      meta.get("ok") else "PARSE_INCOMPLETE")
            rec = {"candidate_id": cid, "ts": _utc(),
                   "status": status, "rows": parsed["rows"],
                   "cross_check_defects": cross,
                   "model": meta.get("model"),
                   "reviewer_provenance": "AI_REVIEW"}
            _append(dec_path, rec)
            dec_lines.append(rec)
            done += 1
            print(f"  {cid}: decomposition {status} "
                  f"({len(parsed['rows'])} rows)")
    for b in ga4:
        cid = b["candidate_id"]
        dec = _latest(dec_lines, "candidate_id", cid)
        if not dec or dec.get("status") != "OK":
            continue
        caps = [c for c in (b.get("backcast") or {}).get(
            "capabilities") or []
            if c.get("parse_status") == "OK"
            and str(c.get("essential_today", "")).strip().lower()
            == "yes"][:3]

        def row_for(cap):
            n = str(cap.get("name") or "").casefold().strip()
            for r in dec.get("rows") or []:
                k = str(r.get("name") or "").casefold()
                if n in k or k in n:
                    return r
            return None
        for cap in caps:
            key = f"{cid}::{cap.get('name')}"
            last = _latest(ver_lines, "key", key)
            if last and last.get("status") in (
                    "OK", "INCOMPLETE_TRANSPORT_BUDGET",
                    "DECOMPOSITION_ROW_MISSING"):
                continue
            row = row_for(cap)
            if row is None:
                v = {"capability": cap.get("name"),
                     "verdict": "NOT_DEMONSTRATED",
                     "issues": "decomposition row missing"}
                rec = {"key": key, "candidate_id": cid,
                       "ts": _utc(),
                       "status": "DECOMPOSITION_ROW_MISSING",
                       "verification": v,
                       "reviewer_provenance": "AI_REVIEW"}
                _append(ver_path, rec)
                ver_lines.append(rec)
                continue
            if limit is not None and done >= limit:
                break
            query = str(cap.get("name") or "")[:200] + \
                " demonstrated capability"
            try:
                items, _report = _retrieve(query)
                records = [
                    {"record_id": r.get("record_id") or r.get("id"),
                     "title": r.get("title"),
                     "abstract": str(r.get("abstract") or
                                     r.get("snippet") or "")[:600]}
                    for r in (items or [])[:6]]
            except Exception as e:
                records = []
                transport_error = str(e)[:200]
            else:
                transport_error = None
            v = verify_capability(cap, row, records)
            status = ("OK" if records else
                      "INCOMPLETE_TRANSPORT_BUDGET")
            if transport_error:
                status = "INCOMPLETE_TRANSPORT_BUDGET"
            rec = {"key": key, "candidate_id": cid, "ts": _utc(),
                   "status": status, "verification": v,
                   "capability": cap.get("name"),
                   "record_ids": [str(r.get("record_id"))
                                  for r in records][:6],
                   "reviewer_provenance": "AI_REVIEW"}
            _append(ver_path, rec)
            ver_lines.append(rec)
            done += 1
            print(f"  {cid}: cap '{cap.get('name')}' -> "
                  f"{v.get('verdict')}")
    # availability branch
    av_lines = _read_lines(av_path)
    for b in ga4:
        cid = b["candidate_id"]
        if _latest(av_lines, "candidate_id", cid):
            continue
        dec = _latest(dec_lines, "candidate_id", cid)
        if not dec or dec.get("status") != "OK":
            continue
        caps = [c for c in (b.get("backcast") or {}).get(
            "capabilities") or []
            if c.get("parse_status") == "OK"]
        vers = [l.get("verification") for l in ver_lines
                if l.get("candidate_id") == cid]
        amap = availability_map(caps, dec.get("rows") or [], vers)
        branch = availability_branch(amap)
        rec = {"candidate_id": cid, "ts": _utc(),
               "availability_map": amap, "branch": branch,
               "reviewer_provenance": "AI_REVIEW"}
        _append(av_path, rec)
        av_lines.append(rec)
        print(f"  {cid}: availability branch "
              f"{branch.get('branch')}")
    n_ok = sum(1 for l in av_lines
               if (l.get("branch") or {}).get("branch") ==
               "PRESENT_CAPABILITY_REDISCOVERY")
    print(f"ga6: {n_ok} present-capability rediscovery branches")
    return 0


def stage_ga7(limit=None) -> int:
    from discovery_fabric.r412.recovery import (
        compute_causal_delta, verify_causal_delta)
    if stage_seal() != 0:
        return 1
    ga4 = [l for l in _read_lines(OUT_DIR / "ga4.jsonl")
           if l.get("status") == "OK"]
    av_lines = _read_lines(OUT_DIR / "ga6_availability.jsonl")
    path = OUT_DIR / "ga7.jsonl"
    lines = _read_lines(path)
    for b in ga4:
        cid = b["candidate_id"]
        if _latest(lines, "candidate_id", cid):
            continue
        av = _latest(av_lines, "candidate_id", cid)
        if not av or av.get("branch", {}).get("branch") != \
                "PRESENT_CAPABILITY_REDISCOVERY":
            continue
        bc = b.get("backcast") or {}
        fields = bc.get("fields") or {}
        delta = compute_causal_delta(
            bc.get("parent_graph") or {"nodes": [], "edges": []},
            bc.get("descendant_graph") or {"nodes": [],
                                           "edges": []})
        delta["new_interaction"] = str(
            fields.get("NEW_INTERACTION") or "")
        delta["predicted_new_effect"] = str(
            fields.get("PREDICTED_NEW_EFFECT") or "")
        delta["measurement"] = str(
            fields.get("MEASUREMENT_PLAN") or
            fields.get("MEASUREMENT") or "")
        gate = verify_causal_delta(
            delta, delta["new_interaction"],
            delta["predicted_new_effect"], delta["measurement"])
        rec = {"candidate_id": cid, "ts": _utc(), "delta": delta,
               "gate": gate, "reviewer_provenance": "AI_REVIEW"}
        _append(path, rec)
        lines.append(rec)
        print(f"  {cid}: {gate['verdict']}")
    n_pass = sum(1 for l in lines
                 if (l.get("gate") or {}).get("gate") == "PASS")
    print(f"ga7: {n_pass}/{len(lines)} new-causal-architecture "
          f"verdicts PASS")
    return 0


def stage_ga8(limit=None) -> int:
    from discovery_fabric.r412.temporal_pipeline import (
        build_novelty_prompt, parse_novelty, new_candidate_identity)
    if stage_seal() != 0:
        return 1
    ga7 = _read_lines(OUT_DIR / "ga7.jsonl")
    ga4_lines = _read_lines(OUT_DIR / "ga4.jsonl")
    path = OUT_DIR / "ga8.jsonl"
    lines = _read_lines(path)
    done = 0
    for g in ga7:
        cid = g["candidate_id"]
        if (g.get("gate") or {}).get("gate") != "PASS":
            continue
        if _latest(lines, "candidate_id", cid):
            continue
        if limit is not None and done >= limit:
            break
        b = _latest(ga4_lines, "candidate_id", cid)
        fields = (b.get("backcast") or {}).get("fields") or {}
        identity = new_candidate_identity(cid, {
            "fields": fields,
            "capabilities": (b.get("backcast") or {}).get(
                "capabilities") or []})
        query = " ".join([str(fields.get("TECHNOLOGY") or ""),
                          str(fields.get("PHYSICAL_MECHANISM") or
                              "")[:120]])
        t0 = time.time()
        items, _report = _retrieve(query)
        pa_records = [
            {"record_id": r.get("record_id") or r.get("id"),
             "title": r.get("title"),
             "abstract": str(r.get("abstract") or "")[:200]}
            for r in (items or [])[:12]]
        meta = _with_pins(lambda: _llm(
            build_novelty_prompt(
                {"new_candidate_id": identity["new_candidate_id"],
                 "fields": fields}, pa_records),
            system="You are a novelty classifier. Use exactly the "
                   "five classes.",
            purpose="r412_gradient_v2_ga8_novelty"))
        novelty = parse_novelty(meta.get("content") or "")
        rec = {"candidate_id": cid, "ts": _utc(),
               "identity": identity,
               "fresh_prior_art": {
                   "n_records": len(pa_records),
                   "elapsed_s": round(time.time() - t0, 1)},
               "novelty": novelty, "model": meta.get("model"),
               "reviewer_provenance": "AI_REVIEW"}
        _append(path, rec)
        lines.append(rec)
        done += 1
        print(f"  {cid}: novelty={novelty.get('novelty_class')}")
    print(f"ga8: {done} fresh novelty classifications")
    return 0


def stage_ga9(limit=None) -> int:
    from discovery_fabric.r412.temporal_pipeline import \
        temporal_attack
    from discovery_fabric.r412.recovery import attacker_caveat
    if stage_seal() != 0:
        return 1
    ga8 = _read_lines(OUT_DIR / "ga8.jsonl")
    ga4_lines = _read_lines(OUT_DIR / "ga4.jsonl")
    path = OUT_DIR / "ga9.jsonl"
    lines = _read_lines(path)
    done = 0
    for n in ga8:
        cid = n["candidate_id"]
        cls = (n.get("novelty") or {}).get("novelty_class") or ""
        if cls not in ("NEW_MECHANISM", "NEW_CAUSAL_ARCHITECTURE",
                       "NEW_APPLICATION", "NEW_REGIME"):
            continue
        if _latest(lines, "candidate_id", cid):
            continue
        if limit is not None and done >= limit:
            break
        b = _latest(ga4_lines, "candidate_id", cid)
        fields = (b.get("backcast") or {}).get("fields") or {}
        new_cand = {
            "new_candidate_id":
                (n.get("identity") or {}).get("new_candidate_id")
                or cid, "fields": fields}
        pseudo_evo = {
            "fields": fields,
            "capabilities": (b.get("backcast") or {}).get(
                "capabilities") or []}
        attack = _with_pins(lambda: temporal_attack(
            new_cand, pseudo_evo,
            [{"record_id": "ga8-pool", "title": "fresh prior-art "
                                     "pool", "abstract": ""}],
            llm_generate=lambda p, system, purpose,
            max_tokens=2600: _llm(p, system, purpose)))
        rec = {"candidate_id": cid, "ts": _utc(), "attack": attack,
               "attacker_calibration_status": attacker_caveat(),
               "model": attack.get("model"),
               "reviewer_provenance": "AI_REVIEW"}
        _append(path, rec)
        lines.append(rec)
        done += 1
        print(f"  {cid}: attack={attack.get('verdict')} "
              f"(NOT_CALIBRATED caveat attached)")
    print(f"ga9: {done} fresh attacks (caveat travels)")
    return 0


# ---------------------------------------------------------------------------
# stage: finalize — the operator's Phase L comparison table
# ---------------------------------------------------------------------------

def stage_finalize(limit=None) -> int:
    if stage_seal() != 0:
        return 1
    ga3 = _read_lines(OUT_DIR / "ga3.jsonl")
    tvm = _load(TVM_FROZEN) if TVM_FROZEN.exists() else {
        "entries": []}
    entries = tvm.get("entries") or []
    domains = sorted({str(e.get("domain")) for e in entries})
    ga6_av = _read_lines(OUT_DIR / "ga6_availability.jsonl")
    present = sum(1 for l in ga6_av if (l.get("branch") or {})
                  .get("branch") == "PRESENT_CAPABILITY_"
                                      "REDISCOVERY")
    ga7 = _read_lines(OUT_DIR / "ga7.jsonl")
    descendants = sum(1 for l in ga7)
    ga8 = _read_lines(OUT_DIR / "ga8.jsonl")
    novelty_survivors = sum(
        1 for l in ga8 if (l.get("novelty") or {}).get(
            "novelty_class") in ("NEW_MECHANISM",
                                 "NEW_CAUSAL_ARCHITECTURE",
                                 "NEW_APPLICATION", "NEW_REGIME"))
    ga9 = _read_lines(OUT_DIR / "ga9.jsonl")
    attacker_survivors = sum(
        1 for l in ga9 if (l.get("attack") or {}).get("verdict")
        in ("HOLDS", "SURVIVES"))
    attempted = len(ga3)
    tvm_log = (_load(TVM_CONSTRUCTED).get("construction_log")
               if TVM_CONSTRUCTED.exists() else []) or []
    n_proposals = sum(e.get("n_proposed", 0) for e in tvm_log
                      if e.get("n_retrieved") is not None)
    doc = {
        "artifact_type": "R412_GRADIENT_V2_RUN_FINAL",
        "created_at": _utc(),
        "gradient_version": "R412-GRADIENT-V2",
        "operator_comparison_table": {
            "measurement": [
                "Seeds", "TVM proposals", "Valid frontier entries",
                "Frontier domains", "Present-capability "
                "rediscoveries", "Causal descendants",
                "Fresh novelty survivors", "Attacker survivors",
                "Buyer-grade inventions"],
            "r412_v1": [10, 34, 0, 0, 0, 0, 0, 0, 0],
            "r412_v2": [attempted, n_proposals, len(entries),
                        len(domains), present, descendants,
                        novelty_survivors, attacker_survivors, 0],
            "confound": "v1 proposer minimax/minimax-m3:free "
                        "(OpenRouter); v2 proposer zai/glm-4-plus "
                        "(this workspace's only live transport). "
                        "Admission deltas are attributable to "
                        "instrument + proposer; no pure "
                        "instrument attribution is claimed",
        },
        "funnel": {
            "attempted": attempted,
            "measured_movers": sum(1 for l in ga3 if l.get(
                "verdict") == "FAST_MOVERS_RANKED"),
            "backcasts_ok": sum(1 for l in _read_lines(
                OUT_DIR / "ga4.jsonl") if l.get("status") == "OK"),
            "present_capability_branches": present,
            "causal_descendants": descendants,
            "novelty_survivors": novelty_survivors,
            "attacker_survivors": attacker_survivors,
            "liry": (attacker_survivors / attempted)
            if attempted else 0.0,
        },
        "honest_zero_rule": "a zero is reported as a zero (Art. "
                            "LXVIII); the attacker caveat "
                            "NOT_CALIBRATED travels on every "
                            "attack verdict",
        "reviewer_provenance": "AI_REVIEW",
    }
    p = OUT_DIR / "R412_GRADIENT_V2_RUN_FINAL.json"
    p.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"finalize: table written {p}")
    print(json.dumps(doc["operator_comparison_table"], indent=1))
    return 0


STAGES = {
    "seal": stage_seal,
    "tvm-build": stage_tvm_build,
    "tvm-freeze": stage_tvm_freeze,
    "ga3": stage_ga3,
    "ga4": stage_ga4,
    "ga5": stage_ga5,
    "ga55": stage_ga55,
    "ga6": stage_ga6,
    "ga7": stage_ga7,
    "ga8": stage_ga8,
    "ga9": stage_ga9,
    "finalize": stage_finalize,
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stages", nargs="+", choices=list(STAGES))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--gateway", action="store_true",
                    help="manage the zai gateway for this "
                         "invocation (required for LLM stages)")
    args = ap.parse_args()
    if args.gateway and not _gateway_alive():
        if not _start_gateway():
            print("REFUSED: the zai gateway failed to start — "
                  "no LLM stage may run (fail-closed)")
            return 1
        print("zai gateway live on 127.0.0.1:8787")
    rc = 0
    for s in args.stages:
        print(f"=== {s} ===")
        rc = STAGES[s](limit=args.limit) or rc
        if rc != 0:
            return rc
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

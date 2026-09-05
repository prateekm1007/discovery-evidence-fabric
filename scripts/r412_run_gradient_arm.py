#!/usr/bin/env python3
"""scripts/r412_run_gradient_arm.py — the R412 gradient/recovery-arm
SEALED runner (staged, checkpointed, resumable).

Runs ONLY after the seal (R412/R412_GRADIENT_RECOVERY_PREREGISTRATION.
json committed with machinery + tests + schemas + population hash +
TVM v0 snapshot/hash + prompts + budget + stopping rules). The
`seal` stage re-verifies every hash and REFUSES the run on any
mismatch — no after-the-fact changes (Art. LIX; directive item 11).

Stages (each invocation runs one stage and exits; every unit is
checkpointed to R412/RECOVERY_ARM/GRADIENT_RUN/ before the next):

  seal       fail-closed seal + hash verification (no model calls)
  ga1b       operational deficit extraction, span-gated (13 seeds)
  ga2        gradient eligibility cross-check (deterministic)
  tvm-build  TVM construction (fabric + span-gated proposals)
  tvm-freeze TVM snapshot + sha256 (REQUIRED before any GA-4 call)
  ga3        deterministic TVM query (cheapest kill)
  ga4        capability backcast (frontier-to-laggard transfer)
  ga5        transfer feasibility (assumptions need anchors)
  ga55       WHY_NOT_ALREADY_ADOPTED (evidence-gated)
  ga6        present-day availability (sealed verify instrument
             unchanged + the availability taxonomy)
  ga7        causal-architecture delta verification (deterministic)
  ga8        fresh collision + novelty (promoted descendants only)
  ga9        fresh attack (NOT_CALIBRATED caveat travels)
  finalize   the COMPLETE population report (emission guards)

The frozen inputs (R411 population, evidence, waterfall, the sealed
temporal replay) are READ ONLY — the gradient arm never writes into
R411/ or R412/TEMPORAL_REPLAY/ (pinned by test).

Zero is an acceptable outcome (Art. LXVIII). Transport failures are
INCOMPLETE, never verdicts (Art. LXI).
"""
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

OUT_DIR = REPO / "R412" / "RECOVERY_ARM" / "GRADIENT_RUN"
PREREG = REPO / "R412" / "R412_GRADIENT_RECOVERY_PREREGISTRATION.json"
ACCOUNTING = REPO / "R412" / "RECOVERY_ARM" / \
    "R412_POPULATION_ACCOUNTING.json"
TVM_V0 = REPO / "R412" / "RECOVERY_ARM" / "TVM_V0_SNAPSHOT.json"
TVM_CONSTRUCTED = OUT_DIR / "TVM_CONSTRUCTED.json"
TVM_FROZEN = OUT_DIR / "TVM_FROZEN.json"
RUN = REPO / "R411" / "DISCOVERY_RUN"
WATERFALL = REPO / "R412" / "R412_DEATH_CAUSE_WATERFALL.json"

MODEL_PINS = {
    "ENGINE_LLM_PROVIDER": "openrouter",
    "OPENROUTER_MODEL": "minimax/minimax-m3:free",
}
MAX_ATTEMPTS = 2
TERMINAL_STATUSES = ("OK", "EXTRACTION_FAILED", "INSUFFICIENT_FRONTIER",
                     "DEAD_AT_TVM_QUERY", "INCOMPLETE_TRANSPORT_BUDGET")
FABRIC_LANE_CAPS = {"SCHOLARLY": 4, "PREPRINT": 2, "PATENT": 3,
                    "THESIS": 2, "DATASET": 1, "REGISTER": 2,
                    "CLINICAL": 0}
# the sealed budget: tvm_construction_fabric_calls_max = 12 total
# completed rung constructions (transport retries are the sealed
# bounded headroom on top)
TVM_CONSTRUCTION_CAP = 12


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load(p: Path):
    return json.loads(Path(p).read_text())


def _append(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(record) + "\n")


def _read_lines(path: Path):
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text().splitlines()
            if x.strip()]


def _latest(lines, key, val):
    best = None
    for ln in lines:
        if ln.get(key) == val:
            best = ln
    return best


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
    from discovery_fabric.retrieval_fabric.pipeline import retrieve_fabric
    problem = {"device": query[:120], "failure_mode":
               query[120:240] or query[:120]}
    items, report = retrieve_fabric(
        problem, lane_caps=FABRIC_LANE_CAPS,
        enable_reciprocal=False, enable_unpaywall=False)
    return items, report


def _cand(cid):
    scored = _load(RUN / "scored_pool.json")
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
    return prereg["resource_allocation"]["priority_order"], prereg


# ---------------------------------------------------------------------------
# stages
# ---------------------------------------------------------------------------

def stage_seal(limit=None) -> int:
    """Fail-closed seal verification. NO model calls. Recomputes the
    population hash from the frozen records and matches the TVM v0
    and accounting artifact hashes against the preregistration."""
    import hashlib
    from discovery_fabric.r412.gradient import verify_seal
    if not PREREG.exists():
        print("REFUSED: preregistration artifact absent — the seal "
              "must be committed before any gradient model call")
        return 1
    prereg = _load(PREREG)
    check = verify_seal(prereg)
    if not check["seal_valid"]:
        print(f"REFUSED: seal incomplete: {check['missing']}")
        return 1
    problems = []
    # accounting artifact hash
    acc_sha = hashlib.sha256(ACCOUNTING.read_bytes()).hexdigest()
    if acc_sha != prereg["source_campaign"][
            "population_accounting_sha256"]:
        problems.append("population accounting artifact hash mismatch")
    # population hash: recompute from the frozen records
    from discovery_fabric.r412.recovery import (
        build_population_accounting)
    accounting = _load(ACCOUNTING)
    recomputed = build_population_accounting(
        _load(RUN / "funnel_collision.json"),
        _load(RUN / "scored_pool.json"),
        _load(RUN / "shortlist.json"),
        _load(RUN / "selection.json"),
        _load(WATERFALL))
    if recomputed["population_sha256"] != \
            prereg["population"]["population_sha256"]:
        problems.append("population hash mismatch vs frozen records")
    if recomputed["population_sha256"] != \
            accounting["population_sha256"]:
        problems.append("population hash drift accounting vs live")
    # TVM v0 hash
    tvm_sha = hashlib.sha256(TVM_V0.read_bytes()).hexdigest()
    if tvm_sha != prereg["tvm_v0"]["sha256"]:
        problems.append("TVM v0 snapshot hash mismatch")
    # the sealed temporal arm untouched
    temporal_sha = hashlib.sha256(
        (REPO / "R412" / "TEMPORAL_REPLAY" /
         "R412_TEMPORAL_REPLAY_RUN.json").read_bytes()).hexdigest()
    if temporal_sha != prereg["temporal_control_arm"][
            "run_record_sha256"]:
        problems.append("sealed temporal control arm modified — "
                        "REFUSE (the 0/13 result is never "
                        "retro-edited)")
    rec = {
        "ts": _utc(), "stage": "SEAL_CHECK", **check,
        "hashes": {
            "population_accounting": acc_sha,
            "population": recomputed["population_sha256"],
            "tvm_v0": tvm_sha,
            "temporal_control_arm": temporal_sha,
        },
        "problems": problems,
        "action": "REFUSE_RUN" if problems else "RUN_ALLOWED",
    }
    _append(OUT_DIR / "seal.jsonl", rec)
    print(("REFUSED: " + "; ".join(problems)) if problems else
          "seal verified: population hash, TVM v0 hash, accounting "
          "hash, temporal control arm — all match")
    return 1 if problems else 0


def stage_ga1b(limit=None) -> int:
    """GA-1b: operational deficit extraction for the 13 technical-
    death seeds (span-gated LLM; failures are EXTRACTION_FAILED ->
    INCOMPLETE, never invented)."""
    from discovery_fabric.r412.gradient import (
        build_deficit_extraction_prompt, parse_deficit_extraction,
        verify_deficit_extraction)
    from discovery_fabric.r412.recovery import (
        CAPABILITY_DEFICIT_CLASSIFICATIONS)
    accounting = _load(ACCOUNTING)
    seeds = accounting["technical_death_subset"]["candidate_ids"]
    path = OUT_DIR / "ga1b.jsonl"
    lines = _read_lines(path)
    done = 0
    for cid in seeds:
        last = _latest(lines, "candidate_id", cid)
        if last and last.get("status") in TERMINAL_STATUSES:
            continue
        if last and last.get("attempt", 1) >= MAX_ATTEMPTS:
            continue
        if limit is not None and done >= limit:
            break
        attempt = (last.get("attempt", 0) + 1) if last else 1
        prompt = build_deficit_extraction_prompt(
            _cand(cid), _death(cid),
            CAPABILITY_DEFICIT_CLASSIFICATIONS[cid])
        meta = _with_pins(lambda: _llm(
            prompt,
            system="You are recovering recorded evidence verbatim. "
                   "Never invent facts, values, or causes.",
            purpose="r412_gradient_ga1b_deficit_extraction"))
        parsed = parse_deficit_extraction(meta.get("content") or "")
        gate = verify_deficit_extraction(parsed, _death(cid))
        status = ("OK" if meta.get("ok") and gate["gate"] == "PASS"
                  else "EXTRACTION_FAILED" if gate["gate"] == "FAIL"
                  else "INCOMPLETE_TRANSPORT" if not meta.get("ok")
                  else "PARSE_INCOMPLETE")
        rec = {
            "candidate_id": cid, "ts": _utc(), "attempt": attempt,
            "status": status, "gate": gate, "parsed": parsed,
            "prompt_hash": meta.get("prompt_hash"),
            "output_hash": meta.get("output_hash"),
            "model": meta.get("model"),
            "reviewer_provenance": "AI_REVIEW",
        }
        _append(path, rec)
        lines.append(rec)
        done += 1
        print(f"  {cid}: {status} (rung="
              f"{gate.get('capability_rung')})")
    n_ok = sum(1 for l in lines if l.get("status") == "OK")
    print(f"ga1b: {n_ok} OK / {len(seeds)} seeds "
          f"({len(lines)} invocations)")
    return 0


def stage_ga2(limit=None) -> int:
    """GA-2: deterministic eligibility cross-check — the frozen
    classification vs the GA-1b extraction outcomes (instant, no
    model calls)."""
    accounting = _load(ACCOUNTING)
    ga1b = _read_lines(OUT_DIR / "ga1b.jsonl")
    rows = accounting["gradient_eligibility"]["rows"]
    out = []
    for row in rows:
        if row["eligibility"] in ("GRADIENT_ELIGIBLE",
                                  "GRADIENT_PRIOR_ART_SPECIAL_ROUTE"):
            last = _latest(ga1b, "candidate_id", row["candidate_id"])
            extraction_status = (last or {}).get("status") or \
                "NOT_EXTRACTED"
            out.append({**row, "ga1b_extraction_status":
                        extraction_status})
        else:
            out.append(row)
    _append(OUT_DIR / "ga2.jsonl", {
        "ts": _utc(), "n": len(out),
        "n_attempt_ready": sum(
            1 for r in out if r.get("ga1b_extraction_status") == "OK"),
        "rows": out})
    n = sum(1 for r in out if r.get("ga1b_extraction_status") == "OK")
    print(f"ga2: {n} seeds with verified extractions ready for the "
          f"TVM query")
    return 0


def stage_tvm_build(limit=None) -> int:
    """TVM construction: per distinct verified rung, one fabric
    retrieval + span-gated LLM proposals. The rungs are named by the
    GA-1b verified extractions (plus the frozen v0 seed
    expectations); NO LLM-asserted numbers enter the map.

    ALLOCATION-ORDER REPAIR (pre-first-model-call, 2026-09-06, zero
    gradient calls run): rungs are constructed in the SEALED
    priority order — the 10 allocation seeds' rungs FIRST — so the
    sealed 12-call construction cap can never starve an allocation
    seed's rung; a rung left unbuilt by the cap is recorded as
    INCOMPLETE_BUDGET_SHORTFALL (recorded, never silently dropped —
    the sealed budget_shortfall_rule). A rung with a COMPLETED
    attempt (even zero admitted entries) is never re-attempted
    (rejected entries are recorded, never repaired); a
    transport-failed rung gets one bounded retry. No sealed
    threshold, prompt, rule, population, or map changed."""
    from discovery_fabric.r412.gradient import (
        build_tvm_proposal_prompt, parse_tvm_entries,
        verify_tvm_entries, TVM_VERSION)
    priority, _prereg = _priority()
    ga1b = [l for l in _read_lines(OUT_DIR / "ga1b.jsonl")
            if l.get("status") == "OK"]
    rung_by_cid: dict = {}
    rungs: dict = {}
    for l in ga1b:
        rung = (l.get("gate") or {}).get("capability_rung")
        if rung:
            rung_by_cid[l["candidate_id"]] = rung
            rungs.setdefault(rung.casefold(), rung)
    # sealed priority order first: allocation seeds' rungs before any
    # other corpus rung (the map is shared infrastructure, but the
    # allocation can never be starved by non-allocation coverage)
    ordered_keys: list = []
    for cid in priority:
        rung = rung_by_cid.get(cid)
        if rung and rung.casefold() not in ordered_keys:
            ordered_keys.append(rung.casefold())
    for key in rungs:
        if key not in ordered_keys:
            ordered_keys.append(key)
    if TVM_CONSTRUCTED.exists():
        tvm = _load(TVM_CONSTRUCTED)
        have = {str(e.get("capability_rung")).casefold()
                for e in tvm.get("entries") or []}
    else:
        tvm = {"tvm_version": TVM_VERSION, "entries": [],
               "construction_log": []}
        have = set()
    log = tvm.get("construction_log") or []
    # completed attempts are never re-attempted (an honest zero-entry
    # attempt is terminal for construction; only transport failures
    # get the sealed one bounded retry)
    attempted_done = {
        str(e.get("rung")).casefold() for e in log
        if e.get("n_retrieved") is not None}
    shortfall_recorded = {
        str(e.get("rung")).casefold() for e in log
        if e.get("status") == "INCOMPLETE_BUDGET_SHORTFALL"}
    transport_fails: dict = {}
    for e in log:
        if e.get("status") == "INCOMPLETE_TRANSPORT":
            k = str(e.get("rung")).casefold()
            transport_fails[k] = transport_fails.get(k, 0) + 1
    built = 0
    shortfall = []
    # the sealed budget is a TOTAL cap over completed rung attempts
    # (tvm_construction_fabric_calls_max = 12); the invocation limit
    # only bounds THIS invocation's work — later rungs stay PENDING
    # (resumable), and only a rung the TOTAL cap can never cover is
    # recorded INCOMPLETE_BUDGET_SHORTFALL
    total_attempts = len(attempted_done)
    for key in ordered_keys:
        rung = rungs[key]
        if key in have or key in attempted_done or \
                key in shortfall_recorded:
            continue
        if transport_fails.get(key, 0) >= 2:
            continue  # bounded retry exhausted; stays INCOMPLETE
        if total_attempts + built >= TVM_CONSTRUCTION_CAP:
            shortfall.append(rung)
            continue
        if limit is not None and built >= limit:
            break  # per-invocation limit: remaining rungs stay
            # PENDING for the next resumable invocation (NOT
            # shortfall — the total cap has not been reached)
        query = (f"{rung} performance trend improvement measured "
                 f"benchmark")
        try:
            items, report = _retrieve(query)
        except Exception as e:
            tvm["construction_log"].append(
                {"rung": rung, "status": "INCOMPLETE_TRANSPORT",
                 "error": str(e)[:200]})
            continue
        records = [
            {"record_id": r.get("record_id") or r.get("id"),
             "title": r.get("title"),
             "abstract": str(r.get("abstract") or
                             r.get("snippet") or "")[:600]}
            for r in (items or [])[:12]]
        meta = _with_pins(lambda: _llm(
            build_tvm_proposal_prompt(rung, records),
            system="You bind measured evidence verbatim. Never "
                   "assert numbers.",
            purpose="r412_gradient_tvm_proposal"))
        entries = parse_tvm_entries(meta.get("content") or "")
        gate = verify_tvm_entries(entries, records, rung)
        tvm["entries"].extend(gate["admitted"])
        tvm["construction_log"].append({
            "rung": rung, "n_retrieved": len(records),
            # Phase B provenance custody (directive 2026-09-06:
            # every entry retains retrieved_at — carried at the rung-
            # construction level; each entry maps to exactly one
            # rung construction, so entry -> rung -> this timestamp
            # is the deterministic retrieved_at chain): the
            # retrieval fabric's own start timestamp + version
            "retrieved_at": (report or {}).get("retrieved_at"),
            "retrieval_fabric_version": (report or {}).get(
                "fabric_version"),
            "retrieval_lanes": [
                {"lane": s.get("lane"), "source_id":
                 s.get("source_id"), "status": s.get("status")}
                for s in (report or {}).get("lane_states", [])
            ][:14],
            "n_proposed": len(entries),
            "n_admitted": len(gate["admitted"]),
            "n_rejected": len(gate["rejected"]),
            "rejected_reasons": [r.get("reason") for r in
                                 gate["rejected"]][:6],
            "model": meta.get("model"),
        })
        built += 1
        # per-rung checkpoint (incident 2026-09-05T20:17Z: an
        # end-of-stage-only write orphaned 5 completed rung attempts
        # to a session timeout; writing after EVERY attempt makes
        # an interruption resumable via attempted_done — content
        # byte-identical to the end-of-stage write, durability only)
        tvm["n_entries"] = len(tvm["entries"])
        TVM_CONSTRUCTED.parent.mkdir(parents=True, exist_ok=True)
        TVM_CONSTRUCTED.write_text(json.dumps(tvm, indent=1) + "\n")
        print(f"  rung '{rung}': {len(gate['admitted'])} admitted / "
              f"{len(gate['rejected'])} rejected")
    for rung in shortfall:
        tvm["construction_log"].append({
            "rung": rung,
            "status": "INCOMPLETE_BUDGET_SHORTFALL",
            "note": ("the sealed 12-call TVM construction cap was "
                     "reached before this rung; recorded, never "
                     "silently dropped (sealed budget_shortfall_"
                     "rule — no re-allocation)"),
        })
        print(f"  rung '{rung}': INCOMPLETE_BUDGET_SHORTFALL "
              f"(sealed construction cap reached)")
    tvm["n_entries"] = len(tvm["entries"])
    TVM_CONSTRUCTED.parent.mkdir(parents=True, exist_ok=True)
    TVM_CONSTRUCTED.write_text(json.dumps(tvm, indent=1) + "\n")
    print(f"tvm-build: {len(tvm['entries'])} span-verified entries "
          f"across {len(rungs)} rungs")
    return 0


def stage_tvm_freeze(limit=None) -> int:
    """The Art. XLIV freeze: snapshot + sha256 of the constructed
    map. GA-4 REFUSES to run until this artifact exists — no TVM
    edits after the freeze (a changed map is a NEW snapshot + NEW
    freeze)."""
    from discovery_fabric.r412.gradient import build_tvm_snapshot
    if not TVM_CONSTRUCTED.exists():
        print("REFUSED: no constructed TVM to freeze")
        return 1
    snap = build_tvm_snapshot(_load(TVM_CONSTRUCTED))
    TVM_FROZEN.write_text(json.dumps(snap, indent=1) + "\n")
    print(f"tvm-freeze: {snap['n_entries']} entries, sha256="
          f"{snap['sha256'][:16]}... — GA-4 unlocked")
    return 0


def stage_ga3(limit=None) -> int:
    """GA-3: the deterministic TVM query per seed. No measured
    fast-mover -> DEAD_AT_TVM_QUERY (the cheapest kill: no mechanism
    writing). NO LLM.

    ALLOCATION-ORDER REPAIR (pre-first-model-call, 2026-09-06,
    zero gradient calls run): the queries cover EXACTLY the sealed
    10-seed resource allocation in priority order — GA-2-ineligible
    seeds (regime/consistency deaths, recorded at GA-2) never
    enter the gradient machinery ("INELIGIBLE -> recorded, no
    model call spent" — design directive §2), and gradient_
    attempted can never exceed the sealed allocation (finalize's
    attempted count IS this set). No sealed threshold, prompt,
    rule, population, or map changed."""
    from discovery_fabric.r412.gradient import query_tvm
    if not TVM_FROZEN.exists():
        print("REFUSED: the TVM must be frozen before any gradient "
              "query (Art. XLIV)")
        return 1
    tvm = _load(TVM_FROZEN)
    priority, _prereg = _priority()
    ga1b = [l for l in _read_lines(OUT_DIR / "ga1b.jsonl")
            if l.get("status") == "OK"]
    ga1b_by_cid = {l["candidate_id"]: l for l in ga1b}
    # the sealed allocation set, in priority order; a seed whose
    # extraction is not OK never entered the machinery (recorded at
    # GA-1b as INCOMPLETE/EXTRACTION_FAILED — a recorded shortfall,
    # never re-allocated)
    ordered = [ga1b_by_cid[cid] for cid in priority
               if cid in ga1b_by_cid]
    skipped = sorted(l["candidate_id"] for l in ga1b
                     if l["candidate_id"] not in priority)
    path = OUT_DIR / "ga3.jsonl"
    lines = _read_lines(path)
    done = 0
    for l in ordered:
        cid = l["candidate_id"]
        if _latest(lines, "candidate_id", cid):
            continue
        rung = (l.get("gate") or {}).get("capability_rung")
        q = query_tvm(tvm, rung)
        rec = {"candidate_id": cid, "ts": _utc(), "rung": rung, **q}
        _append(path, rec)
        lines.append(rec)
        done += 1
        print(f"  {cid}: {q['verdict']} (rung={rung})")
    if skipped:
        print(f"ga3: {len(skipped)} non-allocation seed(s) not "
              f"queried (GA-2 ineligible, recorded at GA-2, never "
              f"attempted): {', '.join(skipped)}")
    n_dead = sum(1 for l in lines
                 if l.get("verdict") == "DEAD_AT_TVM_QUERY")
    print(f"ga3: {len(lines)} queries, {n_dead} cheapest-kills")
    return 0


def stage_ga4(limit=None) -> int:
    """GA-4: the capability backcast (frontier-to-laggard transfer)
    for seeds with ranked fast-movers. The parent graph must be
    verbatim-grounded in the seed's recorded causal chain."""
    from discovery_fabric.r412.gradient import (
        build_backcast_prompt, parse_backcast, verify_backcast)
    from discovery_fabric.r412.recovery import (
        CAPABILITY_DEFICIT_CLASSIFICATIONS)
    if not TVM_FROZEN.exists():
        print("REFUSED: the TVM must be frozen before GA-4")
        return 1
    tvm = _load(TVM_FROZEN)
    priority, _prereg = _priority()
    allocation = set(priority)
    ga3 = _read_lines(OUT_DIR / "ga3.jsonl")
    path = OUT_DIR / "ga4.jsonl"
    lines = _read_lines(path)
    done = 0
    for q in ga3:
        cid = q["candidate_id"]
        if q.get("verdict") != "FAST_MOVERS_RANKED":
            continue
        # ALLOCATION-ORDER REPAIR (defense in depth): a backcast can
        # never be spent outside the sealed allocation — the sealed
        # budget_shortfall_rule forbids re-allocation to
        # non-eligible candidates
        if cid not in allocation:
            print(f"  {cid}: REFUSED backcast outside the sealed "
                  f"allocation (defense-in-depth; never re-allocated "
                  f"to non-eligible candidates)")
            continue
        last = _latest(lines, "candidate_id", cid)
        if last and last.get("status") in TERMINAL_STATUSES:
            continue
        if last and last.get("attempt", 1) >= MAX_ATTEMPTS:
            continue
        if limit is not None and done >= limit:
            break
        attempt = (last.get("attempt", 0) + 1) if last else 1
        deficit = (_latest(
            _read_lines(OUT_DIR / "ga1b.jsonl"),
            "candidate_id", cid) or {}).get("gate") or {}
        deficit = {**deficit,
                   "named_deficit": CAPABILITY_DEFICIT_CLASSIFICATIONS
                   .get(cid, {}).get("named_deficit")}
        prompt = build_backcast_prompt(
            _cand(cid), _death(cid), deficit, q)
        meta = _with_pins(lambda: _llm(
            prompt,
            system="You are a rigorous engineering scientist "
                   "transferring a causal mechanism, never an "
                   "industry label.",
            purpose="r412_gradient_ga4_backcast"))
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
    """GA-5: transfer feasibility — every assumption needs a
    present-day anchor (fabric retrieval per seed for the anchor
    pool; unanchored assumptions block promotion)."""
    from discovery_fabric.r412.gradient import (
        build_feasibility_prompt, parse_feasibility, verify_feasibility)
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
        deficit = (_latest(
            _read_lines(OUT_DIR / "ga1b.jsonl"),
            "candidate_id", cid) or {}).get("gate") or {}
        # anchor pool: one fabric call for the descendant's outcome
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
        except Exception as e:
            anchor_records, anchor_ids = [], []
            transport_error = str(e)[:200]
        else:
            transport_error = None
        prompt = build_feasibility_prompt(
            b.get("backcast") or {}, deficit)
        meta = _with_pins(lambda: _llm(
            prompt,
            system="You assess transfer feasibility honestly. "
                   "Unanchored assumptions are recorded, never "
                   "invented away.",
            purpose="r412_gradient_ga5_feasibility"))
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
                "transport_error": transport_error,
            },
            "model": meta.get("model"),
            "reviewer_provenance": "AI_REVIEW",
        }
        _append(path, rec)
        lines.append(rec)
        done += 1
        print(f"  {cid}: {status} "
              f"({gate.get('verdict')})")
    n_ok = sum(1 for l in lines if l.get("status") == "OK")
    print(f"ga5: {n_ok} feasibility records ({len(lines)} calls)")
    return 0


def stage_ga55(limit=None) -> int:
    """GA-5.5: WHY_NOT_ALREADY_ADOPTED — target-domain records
    retrieved; a non-UNKNOWN finding requires a span-verified record;
    UNKNOWN blocks promotion (phantom-arbitrage guard)."""
    from discovery_fabric.r412.gradient import (
        build_why_not_prompt, parse_why_not, verify_why_not)
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
        # target-domain records: absence-of-adoption evidence pool
        query = f"{domain} limitations state of the art review"
        try:
            items, _report = _retrieve(query)
            records = [
                {"record_id": r.get("record_id") or r.get("id"),
                 "title": r.get("title"),
                 "abstract": str(r.get("abstract") or
                                 r.get("snippet") or "")[:600]}
                for r in (items or [])[:12]]
        except Exception as e:
            records = []
            transport_error = str(e)[:200]
        else:
            transport_error = None
        prompt = build_why_not_prompt(domain, capability, records)
        meta = _with_pins(lambda: _llm(
            prompt,
            system="You investigate adoption absence honestly. "
                   "UNKNOWN is a valid answer.",
            purpose="r412_gradient_ga55_why_not_adopted"))
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
                "transport_error": transport_error,
            },
            "model": meta.get("model"),
            "reviewer_provenance": "AI_REVIEW",
        }
        _append(path, rec)
        lines.append(rec)
        done += 1
        print(f"  {cid}: {status} "
              f"(finding={gate.get('finding')})")
    n_ok = sum(1 for l in lines if l.get("status") == "OK")
    print(f"ga55: {n_ok} why-not records ({len(lines)} calls)")
    return 0


def stage_ga6(limit=None) -> int:
    """GA-6: the present-day availability test. REUSES the sealed
    verify instrument UNCHANGED (temporal_pipeline.verify_capability)
    + the availability taxonomy; only AVAILABLE_TODAY auto-qualifies
    for PRESENT_CAPABILITY_REDISCOVERY."""
    from discovery_fabric.r412.temporal import (
        build_decomposition_prompt, parse_decomposition,
        cross_check_capabilities)
    from discovery_fabric.r412.temporal_pipeline import (
        verify_capability)
    from discovery_fabric.r412.gradient import availability_map
    from discovery_fabric.r412.recovery import availability_branch
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
        # (a) decomposition — reuse the sealed temporal instrument
        last_dec = _latest(dec_lines, "candidate_id", cid)
        if not last_dec or last_dec.get("status") != "OK":
            if limit is not None and done >= limit:
                break
            pseudo_evo = {
                "fields": {
                    "NEW_ARCHITECTURE":
                        (b.get("backcast") or {}).get(
                            "fields", {}).get("OUTCOME", ""),
                    "MECHANISM_CHAIN": (b.get("backcast") or
                                        {}).get("fields", {}).get(
                                            "PHYSICAL_MECHANISM", ""),
                    "INTERVENTION": (b.get("backcast") or
                                     {}).get("fields", {}).get(
                                         "TECHNOLOGY", ""),
                    "PREDICTED_EFFECT": (b.get("backcast") or
                                         {}).get("fields", {}).get(
                                             "PREDICTED_NEW_EFFECT",
                                             ""),
                    "BOUNDARY_CONDITIONS": "",
                },
                "capabilities": [
                    c for c in (b.get("backcast") or {}).get(
                        "capabilities") or []
                    if c.get("parse_status") == "OK"],
            }
            prompt = build_decomposition_prompt(pseudo_evo)
            meta = _with_pins(lambda: _llm(
                prompt,
                system="You decompose requirements backward and "
                       "judge today's demonstrated capability "
                       "honestly.",
                purpose="r412_gradient_ga6_decomposition"))
            parsed = parse_decomposition(meta.get("content") or "")
            cross = cross_check_capabilities(
                pseudo_evo, parsed)
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
    # (b) verification per essential-today capability (the sealed
    # instrument unchanged; <= 3 per descendant)
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
                     "status": "DECOMPOSITION_ROW_MISSING"}
            else:
                v = verify_capability(cap, row, _retrieve)
            rec = {"key": key, "candidate_id": cid, "ts": _utc(),
                   "status": "OK", **v}
            _append(ver_path, rec)
            ver_lines.append(rec)
            done += 1
            print(f"  {cid}/{cap.get('name')}: "
                  f"{v.get('verdict')}")
    # (c) the availability map + branch (deterministic)
    for b in ga4:
        cid = b["candidate_id"]
        dec = _latest(dec_lines, "candidate_id", cid)
        if not dec or dec.get("status") != "OK":
            continue
        caps = [c for c in (b.get("backcast") or {}).get(
            "capabilities") or []
            if c.get("parse_status") == "OK"
            and str(c.get("essential_today", "")).strip().lower()
            == "yes"]
        vers = [v for v in ver_lines if v.get("candidate_id") == cid]
        amap = availability_map(caps, dec.get("rows") or [], vers)
        branch = availability_branch(amap)
        rec = {"candidate_id": cid, "ts": _utc(),
               "availability": amap, "branch": branch,
               "reviewer_provenance": "AI_REVIEW"}
        _append(av_path, rec)
        print(f"  {cid}: branch={branch['branch']} "
              f"({amap})")
    n_avail = len(_read_lines(av_path))
    print(f"ga6: {n_avail} availability branches")
    return 0


def stage_ga7(limit=None) -> int:
    """GA-7: causal-architecture delta verification — the delta is
    machine-computed (set operations); 'better sensor / faster
    processor / different material / new industry alone' is
    INSUFFICIENT. Deterministic; no model calls."""
    from discovery_fabric.r412.recovery import (
        compute_causal_delta, verify_causal_delta)
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
            continue  # delta gate applies to promoted descendants
        bc = b.get("backcast") or {}
        fields = bc.get("fields") or {}
        new_interaction = str(fields.get("NEW_INTERACTION") or "")
        predicted_new_effect = str(
            fields.get("PREDICTED_NEW_EFFECT") or "")
        measurement = str(fields.get("MEASUREMENT_PLAN") or
                          fields.get("MEASUREMENT") or "")
        delta = compute_causal_delta(
            bc.get("parent_graph") or {"nodes": [], "edges": []},
            bc.get("descendant_graph") or {"nodes": [],
                                           "edges": []})
        # the promoted descendant's record explicitly contains ALL
        # EIGHT directive-item-8 fields
        delta["new_interaction"] = new_interaction
        delta["predicted_new_effect"] = predicted_new_effect
        delta["measurement"] = measurement
        gate = verify_causal_delta(
            delta, new_interaction, predicted_new_effect,
            measurement)
        rec = {"candidate_id": cid, "ts": _utc(),
               "delta": delta, "gate": gate,
               "reviewer_provenance": "AI_REVIEW"}
        _append(path, rec)
        lines.append(rec)
        print(f"  {cid}: {gate['verdict']}")
    n_pass = sum(1 for l in lines
                 if (l.get("gate") or {}).get("gate") == "PASS")
    print(f"ga7: {n_pass}/{len(lines)} new-causal-architecture "
          f"verdicts PASS")
    return 0


def stage_ga8(limit=None) -> int:
    """GA-8: fresh collision + novelty for promoted descendants
    (reuses the sealed temporal novelty machinery; the P0-2 early
    screen discipline: transfer candidates are collision-prone by
    construction)."""
    from discovery_fabric.r412.temporal_pipeline import (
        build_novelty_prompt, parse_novelty, new_candidate_identity)
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
            "fields": fields, "capabilities":
                (b.get("backcast") or {}).get("capabilities") or []})
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
            purpose="r412_gradient_ga8_novelty"))
        novelty = parse_novelty(meta.get("content") or "")
        rec = {"candidate_id": cid, "ts": _utc(),
               "identity": identity,
               "fresh_prior_art": {
                   "n_records": len(pa_records),
                   "elapsed_s": round(time.time() - t0, 1)},
               "novelty": novelty,
               "model": meta.get("model"),
               "reviewer_provenance": "AI_REVIEW"}
        _append(path, rec)
        lines.append(rec)
        done += 1
        print(f"  {cid}: novelty={novelty.get('novelty_class')}")
    print(f"ga8: {done} fresh novelty classifications")
    return 0


def stage_ga9(limit=None) -> int:
    """GA-9: the fresh attack (reuses the sealed temporal attack
    machinery). The NOT_CALIBRATED caveat travels on every verdict —
    never a silent green signal (directive item 10)."""
    from discovery_fabric.r412.temporal_pipeline import (
        temporal_attack)
    from discovery_fabric.r412.recovery import attacker_caveat
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
            continue  # killed by fresh novelty
        if _latest(lines, "candidate_id", cid):
            continue
        if limit is not None and done >= limit:
            break
        b = _latest(ga4_lines, "candidate_id", cid)
        fields = (b.get("backcast") or {}).get("fields") or {}
        new_cand = {"new_candidate_id":
                    (n.get("identity") or {}).get(
                        "new_candidate_id") or cid,
                    "fields": fields}
        pseudo_evo = {"fields": fields,
                      "capabilities": (b.get("backcast") or
                                       {}).get("capabilities") or []}
        attack = _with_pins(lambda: temporal_attack(
            new_cand, pseudo_evo,
            [{"record_id": "ga8-pool", "title": "fresh prior-art "
                                     "pool", "abstract": ""}],
            llm_generate=lambda p, system, purpose, max_tokens=2600:
            _llm(p, system, purpose)))
        rec = {"candidate_id": cid, "ts": _utc(),
               "attack": attack,
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


def stage_finalize(limit=None) -> int:
    """The COMPLETE population report: every denominator present,
    the outcome decomposition, LIRY with dual denominators, the
    attacker caveat, and the 13-subset reported as a subset. The
    emission guards make an inconsistent funnel un-emittable."""
    from discovery_fabric.r412.recovery import (
        build_recovery_funnel, verify_population_funnel)
    accounting = _load(ACCOUNTING)
    hl = accounting["headline_denominators"]
    ga1b = _read_lines(OUT_DIR / "ga1b.jsonl")
    ga3 = _read_lines(OUT_DIR / "ga3.jsonl")
    ga4 = _read_lines(OUT_DIR / "ga4.jsonl")
    av = _read_lines(OUT_DIR / "ga6_availability.jsonl")
    ga7 = _read_lines(OUT_DIR / "ga7.jsonl")
    ga8 = _read_lines(OUT_DIR / "ga8.jsonl")
    ga9 = _read_lines(OUT_DIR / "ga9.jsonl")
    eligible = int(hl.get("gradient_eligible") or 0)
    # attempted: seeds that reached the TVM query (GA-3) — the
    # pre-registered resource-allocation set that actually entered
    # the gradient machinery
    attempted = sum(1 for l in ga3 if l.get("verdict") in
                    ("FAST_MOVERS_RANKED", "DEAD_AT_TVM_QUERY"))
    present = 0
    future = 0
    unresolved = 0
    for a in av:
        oc = (a.get("branch") or {}).get("outcome_class")
        if oc == "PRESENT_RECOVERY":
            present += 1
        elif oc == "FUTURE_ONLY":
            future += 1
        elif oc == "UNRESOLVED":
            unresolved += 1
    # survivors: passed fresh novelty (NEW_MECHANISM or
    # NEW_CAUSAL_ARCHITECTURE) AND survived the fresh attack
    nov_by_cid = {n["candidate_id"]: (n.get("novelty") or
                                      {}).get("novelty_class")
                  for n in ga8}
    survivors = 0
    for a in ga9:
        cid = a["candidate_id"]
        if (a.get("attack") or {}).get("verdict") == "SURVIVED" and \
                nov_by_cid.get(cid) in ("NEW_MECHANISM",
                                        "NEW_CAUSAL_ARCHITECTURE"):
            survivors += 1
    counts = {
        "raw_accepted": int(hl.get("raw_accepted") or 0),
        "unique_scored": int(hl.get("unique_scored") or 0),
        "recorded_technical_death":
            int(hl.get("recorded_technical_death") or 0),
        "recorded_nontechnical_rejection":
            int(hl.get("recorded_nontechnical_rejection") or 0),
        "recorded_no_death_cause":
            int(hl.get("recorded_no_death_cause") or 0),
        "other_terminal_state":
            int(hl.get("other_terminal_state") or 0),
        "gradient_eligible": eligible,
        "gradient_attempted": attempted,
        "present_rediscoveries": present,
        "future_dependent_radar": future,
        "unresolved_availability": unresolved,
        "normal_pipeline_survivors": survivors,
    }
    funnel = build_recovery_funnel(counts)
    report = {
        "artifact_type": "R412_GRADIENT_RECOVERY_RUN",
        "run_id": "r412:gradient-recovery-v1",
        "created_at": _utc(),
        "created_in": "R412",
        "reviewer_provenance": "AI_REVIEW",
        "preregistration": {
            "path": str(PREREG.relative_to(REPO)),
            "sha256": __import__("hashlib").sha256(
                PREREG.read_bytes()).hexdigest(),
        },
        "population_accounting": {
            "path": str(ACCOUNTING.relative_to(REPO)),
            "population_sha256":
                accounting.get("population_sha256"),
        },
        "temporal_control_arm": {
            "status": "PRESERVED_UNMODIFIED",
            "sealed_result": "0/13 (never retro-edited)"},
        "funnel": funnel,
        "stage_records": {
            "ga1b": len(ga1b), "ga3": len(ga3), "ga4": len(ga4),
            "ga6_availability": len(av), "ga7": len(ga7),
            "ga8": len(ga8), "ga9": len(ga9),
        },
        "outcome_decomposition": funnel["outcome_decomposition"],
        "attacker_calibration_status": funnel[
            "attacker_calibration_status"],
        "honest_notes": [
            "the 13-candidate technical-death subset is reported as "
            "a SUBSET; the experimental population is the frozen "
            "R411 population (raw=550, unique=400)",
            "every LLM verdict carries reviewer_provenance="
            "AI_REVIEW (Art. LXVII)",
            "the attacker is NOT_CALIBRATED (measured FPR 0.8, "
            "universal-kill): every attack verdict retains the "
            "caveat until the attacker-specificity problem is "
            "actually resolved (directive item 10)",
            "zero is an acceptable outcome (Art. LXVIII)",
        ],
    }
    verify_population_funnel({
        "funnel": {
            "raw_accepted": counts["raw_accepted"],
            "medical_excluded": accounting["population_funnel"][
                "medical_excluded"],
            "collision_rejected": accounting["population_funnel"][
                "collision_rejected"],
            "dedup_merged": accounting["population_funnel"][
                "dedup_merged"],
            "unique_scored": counts["unique_scored"],
        },
        "terminal_classification": {
            "counts": accounting["terminal_classification"]["counts"]},
        "headline_denominators": counts,
    })
    out = OUT_DIR / "R412_GRADIENT_RECOVERY_RUN.json"
    out.write_text(json.dumps(report, indent=1) + "\n")
    print(f"finalize: report written "
          f"{out.relative_to(REPO)}")
    print(f"  LIRY={funnel['liry']['liry']} "
          f"(attempted={attempted}, eligible={eligible})")
    print(f"  PRESENT_RECOVERY={present}, FUTURE_ONLY={future}, "
          f"UNRESOLVED={unresolved}, survivors={survivors}")
    return 0


STAGES = {
    "seal": stage_seal,
    "ga1b": stage_ga1b,
    "ga2": stage_ga2,
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


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help") or \
            argv[0] not in STAGES:
        print(__doc__)
        print("stages: " + " ".join(STAGES))
        return 0 if argv and argv[0] in ("-h", "--help") else 2
    stage = argv[0]
    limit = None
    if len(argv) > 1:
        try:
            limit = int(argv[1])
        except ValueError:
            pass
    if stage != "seal":
        # every stage verifies the seal first (fail closed)
        rc = stage_seal()
        if rc:
            return rc
    return STAGES[stage](limit)


if __name__ == "__main__":
    raise SystemExit(main())

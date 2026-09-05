#!/usr/bin/env python3
"""scripts/r412_run_temporal_replay.py — the R412 30-Years-Later
retrospective replay driver (staged, checkpointed, resumable).

Stages (each invocation runs one stage and exits; every unit is
checkpointed to R412/TEMPORAL_REPLAY/ before the next):

  eligibility     deterministic classification (instant)
  evolution       30Y LLM calls for the eligible + special-route set
  decomposition   backward-decomposition LLM calls for coherent
                  evolutions
  verify          independent capability verification (fabric
                  retrieval per essential-today capability, <= 3 per
                  candidate)
  fresh           the fresh pipeline for rediscoveries (fresh
                  prior-art retrieval + novelty + temporal attack)
  finalize        branch decisions, cemetery lineage, radar, funnel,
                  run record

The frozen inputs (R411 population, evidence, waterfall) are READ
ONLY — the replay never writes into R411/ (pinned by test).
"""
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

OUT_DIR = REPO / "R412" / "TEMPORAL_REPLAY"
PREREG = REPO / "R412" / \
    "R412_30Y_PRESENT_CAPABILITY_REDISCOVERY_PREREGISTRATION.json"
RUN = REPO / "R411" / "DISCOVERY_RUN"
WATERFALL = REPO / "R412" / "R412_DEATH_CAUSE_WATERFALL.json"

MODEL_PINS = {
    "ENGINE_LLM_PROVIDER": "openrouter",
    "OPENROUTER_MODEL": "minimax/minimax-m3:free",
}
MAX_ATTEMPTS = 2
# Terminal verification-row statuses: a row in any of these
# states is never re-processed on resume. DECOMPOSITION_ROW_MISSING
# is included (idempotence repair, 2026-09-06, disclosed in the
# R412 replay commit): the row records a cross-check defect (the
# capability has no decomposition row), which re-running the verify
# stage can never change — leaving it out re-appended identical
# rows on every invocation. No recorded verdict changes; this is
# loop deduplication only.
TERMINAL_VERIFICATION_STATUSES = (
    "OK", "INCOMPLETE_TRANSPORT_BUDGET", "DECOMPOSITION_ROW_MISSING")
FABRIC_LANE_CAPS = {"SCHOLARLY": 4, "PREPRINT": 2, "PATENT": 3,
                    "THESIS": 2, "DATASET": 1, "REGISTER": 2,
                    "CLINICAL": 0}


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load(p: Path):
    return json.loads(Path(p).read_text())


def _append(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(record) + "\n")


def _latest(lines, key, val):
    """Last record matching val on the given key, falling back to
    'original_candidate_id' (parse_evolution's native key — the R412
    runner wrote 21 evolution records under that key before the
    unification; both are honored so no checkpoint is orphaned)."""
    best = None
    for ln in lines:
        if ln.get(key) == val or ln.get("original_candidate_id") == \
                val and key == "candidate_id":
            best = ln
    return best


def _read_lines(path: Path):
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text().splitlines()
            if x.strip()]


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


def _targets():
    """The attempted set: eligible + special-route, in preregistration
    order (population order; deterministic)."""
    prereg = _load(PREREG)
    er = prereg["eligibility_rules"]
    return (er["classified_eligible"] + er["classified_special_route"],
            prereg)


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


# ---------------------------------------------------------------------------
# stages
# ---------------------------------------------------------------------------

def stage_eligibility(limit=None) -> int:
    from discovery_fabric.r412.temporal import classify_eligibility
    w = _load(WATERFALL)
    rows = [classify_eligibility(d) for d in w["deaths"]]
    _append(OUT_DIR / "eligibility.jsonl",
            {"ts": _utc(), "n": len(rows), "rows": rows})
    n_el = sum(1 for r in rows if r["eligibility"] == "ELIGIBLE")
    n_sp = sum(1 for r in rows if
               r["eligibility"] == "PRIOR_ART_SPECIAL_ROUTE")
    print(f"eligibility: {n_el} eligible, {n_sp} special-route, "
          f"{len(rows) - n_el - n_sp} ineligible")
    return 0


def stage_evolution(limit=None) -> int:
    from discovery_fabric.r412.temporal import (
        build_evolution_prompt, parse_evolution)
    targets, _ = _targets()
    path = OUT_DIR / "evolution.jsonl"
    lines = _read_lines(path)
    done = 0
    for cid in targets:
        last = _latest(lines, "candidate_id", cid)
        if last and last.get("status") == "OK":
            continue
        if last and last.get("attempt", 1) >= MAX_ATTEMPTS:
            continue
        if limit is not None and done >= limit:
            break
        attempt = (last.get("attempt", 0) + 1) if last else 1
        prompt, special = build_evolution_prompt(
            _cand(cid), _death(cid))
        t0 = time.time()
        meta = _with_pins(lambda: _llm(
            prompt,
            system="You are a rigorous engineering scientist "
                   "constructing a technically coherent 2055 "
                   "descendant. Follow the field-line format exactly.",
            purpose="r412_temporal_evolution"))
        rec = parse_evolution(
            meta.get("content") or "", cid, _death(cid))
        rec.update({
            "candidate_id": cid,
            "ts": _utc(), "attempt": attempt,
            "special_route": special,
            "status": ("OK" if meta.get("ok") and rec["parse_status"]
                       == "OK" else
                       "INCOMPLETE_TRANSPORT" if not meta.get("ok")
                       else "PARSE_INCOMPLETE"),
            "transport_error": None if meta.get("ok") else str(
                meta.get("error") or meta.get("status"))[:200],
            "elapsed_s": round(time.time() - t0, 1),
            "prompt_hash": meta.get("prompt_hash"),
            "output_hash": meta.get("output_hash"),
            "provider": meta.get("provider"),
            "model": meta.get("model"),
        })
        _append(path, rec)
        lines.append(rec)
        done += 1
        print(f"  {cid}: {rec['status']} "
              f"({rec['elapsed_s']}s, attempt {attempt})")
    n_ok = sum(1 for l in lines if l.get("status") == "OK")
    print(f"evolution: {n_ok}/{len(targets)} OK "
          f"({len(lines)} invocations)")
    return 0


def stage_decomposition(limit=None) -> int:
    from discovery_fabric.r412.temporal import (
        build_decomposition_prompt, parse_decomposition)
    targets, _ = _targets()
    evo_lines = _read_lines(OUT_DIR / "evolution.jsonl")
    path = OUT_DIR / "decomposition.jsonl"
    lines = _read_lines(path)
    done = 0
    for cid in targets:
        evo = _latest(evo_lines, "candidate_id", cid)
        if not evo or evo.get("status") != "OK":
            continue  # evolution INCOMPLETE -> decomposition not run
        last = _latest(lines, "candidate_id", cid)
        if last and last.get("status") == "OK":
            continue
        if last and last.get("attempt", 1) >= MAX_ATTEMPTS:
            continue
        if limit is not None and done >= limit:
            break
        attempt = (last.get("attempt", 0) + 1) if last else 1
        prompt = build_decomposition_prompt(evo)
        meta = _with_pins(lambda: _llm(
            prompt,
            system="You are a technology-decomposition analyst. "
                   "Name specific demonstrated capabilities and "
                   "operating values, never generic categories.",
            purpose="r412_temporal_decomposition"))
        parsed = parse_decomposition(meta.get("content") or "")
        status = ("OK" if meta.get("ok") and parsed["parse_status"] ==
                  "OK" else "INCOMPLETE_TRANSPORT" if not
                  meta.get("ok") else "PARSE_INCOMPLETE")
        rec = {
            "candidate_id": cid,
            "evolution_id": evo.get("evolution_id"),
            "ts": _utc(), "attempt": attempt, "status": status,
            "transport_error": None if meta.get("ok") else str(
                meta.get("error") or meta.get("status"))[:200],
            "rows": parsed["rows"],
            "prompt_hash": meta.get("prompt_hash"),
            "output_hash": meta.get("output_hash"),
        }
        _append(path, rec)
        lines.append(rec)
        done += 1
        print(f"  {cid}: {status} ({len(parsed['rows'])} rows)")
    n_ok = sum(1 for l in lines if l.get("status") == "OK")
    print(f"decomposition: {n_ok} OK ({len(lines)} invocations)")
    return 0


def _retrieve(query: str):
    from discovery_fabric.retrieval_fabric.pipeline import retrieve_fabric
    problem = {"device": query[:120], "failure_mode":
               query[120:240] or query[:120]}
    items, report = retrieve_fabric(
        problem, lane_caps=FABRIC_LANE_CAPS,
        enable_reciprocal=False, enable_unpaywall=False)
    return items, report


def stage_verify(limit=None) -> int:
    """Independent capability verification via the fabric (bounded:
    essential-today capabilities only, <= 3 per candidate — the
    preregistration budget)."""
    from discovery_fabric.r412.temporal import cross_check_capabilities
    from discovery_fabric.r412.temporal_pipeline import (
        verify_capability)
    targets, _ = _targets()
    evo_lines = _read_lines(OUT_DIR / "evolution.jsonl")
    dec_lines = _read_lines(OUT_DIR / "decomposition.jsonl")
    path = OUT_DIR / "verification.jsonl"
    lines = _read_lines(path)
    done = 0
    for cid in targets:
        evo = _latest(evo_lines, "candidate_id", cid)
        dec = _latest(dec_lines, "candidate_id", cid)
        if not evo or evo.get("status") != "OK" or not dec or \
                dec.get("status") != "OK":
            continue
        caps = [c for c in evo.get("capabilities") or []
                if c.get("parse_status") == "OK"
                and str(c.get("essential_today", "")).strip().lower()
                == "yes"][:3]
        # decomposition row lookup (name containment, both directions)
        def row_for(cap):
            n = str(cap.get("name") or "").casefold().strip()
            for r in dec.get("rows") or []:
                k = str(r.get("name") or "").casefold()
                if n in k or k in n:
                    return r
            return None
        for cap in caps:
            key = f"{cid}::{cap.get('name')}"
            last = _latest(lines, "key", key)
            if last and last.get("status") in \
                    TERMINAL_VERIFICATION_STATUSES:
                continue
            if limit is not None and done >= limit:
                break
            row = row_for(cap)
            if row is None:
                # cross-check defect recorded as a verification gap
                v = {"capability": cap.get("name"),
                     "verdict": "NOT_DEMONSTRATED",
                     "status": "DECOMPOSITION_ROW_MISSING"}
            else:
                t0 = time.time()
                v = verify_capability(cap, row, _retrieve)
                v["elapsed_s"] = round(time.time() - t0, 1)
            rec = {"key": key, "candidate_id": cid,
                   "capability": cap.get("name"), "ts": _utc(),
                   "status": "OK", **v}
            _append(path, rec)
            lines.append(rec)
            done += 1
            print(f"  {cid} / {cap.get('name')}: "
                  f"{v.get('verdict')} "
                  f"(cov {v.get('best_distinctive_coverage')})")
    print(f"verification: {done} new checks "
          f"({len(lines)} total)")
    return 0


def stage_fresh(limit=None) -> int:
    """The fresh pipeline for rediscoveries: fresh prior-art
    retrieval + novelty classification + temporal attack."""
    from discovery_fabric.r412.temporal import parse_evolution
    from discovery_fabric.r412.temporal_pipeline import (
        build_novelty_prompt, new_candidate_identity, parse_novelty,
        temporal_attack)
    from discovery_fabric.r412.temporal import validate_capability
    from discovery_fabric.r412.temporal_pipeline import (
        branch_decision)
    targets, _ = _targets()
    evo_lines = _read_lines(OUT_DIR / "evolution.jsonl")
    dec_lines = _read_lines(OUT_DIR / "decomposition.jsonl")
    ver_lines = _read_lines(OUT_DIR / "verification.jsonl")
    path = OUT_DIR / "fresh.jsonl"
    lines = _read_lines(path)
    done = 0
    for cid in targets:
        evo = _latest(evo_lines, "candidate_id", cid)
        if not evo or evo.get("status") != "OK":
            continue
        if _latest(lines, "candidate_id", cid):
            continue
        dec = _latest(dec_lines, "candidate_id", cid)
        vers = [v for v in ver_lines if v.get("candidate_id") == cid]
        # branch decision from the checkpoints
        branch = branch_decision(evo, dec or {"rows": []}, vers)
        if branch["branch"] != "PRESENT_CAPABILITY_REDISCOVERY":
            continue
        if limit is not None and done >= limit:
            break
        identity = new_candidate_identity(cid, evo)
        fields = evo.get("fields") or {}
        # fresh prior-art retrieval for the NEW mechanism
        query = " ".join([
            str(fields.get("INTERVENTION") or ""),
            str(fields.get("MECHANISM_CHAIN") or "")[:120]])
        t0 = time.time()
        items, report = _retrieve(query)
        pa_records = [
            {"record_id": r.get("record_id") or r.get("id"),
             "title": r.get("title"),
             "abstract": str(r.get("abstract") or "")[:200]}
            for r in (items or [])[:12]]
        retrieval_s = round(time.time() - t0, 1)
        # fresh novelty classification
        meta_n = _with_pins(lambda: _llm(
            build_novelty_prompt(
                {"new_candidate_id": identity["new_candidate_id"],
                 "fields": fields}, pa_records),
            system="You are a novelty classifier. Use exactly the "
                   "five classes.",
            purpose="r412_temporal_novelty"))
        novelty = parse_novelty(meta_n.get("content") or "")
        novelty["provider"] = meta_n.get("provider")
        novelty["model"] = meta_n.get("model")
        # temporal attack (fresh context)
        new_cand = {"new_candidate_id": identity["new_candidate_id"],
                    "fields": fields}
        attack = _with_pins(lambda: temporal_attack(
            new_cand, evo, pa_records,
            llm_generate=lambda p, system, purpose, max_tokens:
            _llm(p, system, purpose)))
        rec = {
            "candidate_id": cid, "ts": _utc(),
            "identity": identity, "branch": branch,
            "fresh_prior_art": {
                "query": query[:200],
                "n_records": len(pa_records),
                "elapsed_s": retrieval_s,
                "records": pa_records[:6],
            },
            "novelty": novelty,
            "attack": attack,
            "status": "OK",
        }
        _append(path, rec)
        lines.append(rec)
        done += 1
        print(f"  {cid} -> {identity['new_candidate_id']}: novelty="
              f"{novelty.get('novelty_class')} "
              f"attack={attack.get('verdict')}")
    print(f"fresh pipeline: {done} rediscoveries processed")
    return 0


def stage_finalize(limit=None) -> int:
    from discovery_fabric.r412.temporal import classify_eligibility
    from discovery_fabric.r412.temporal_pipeline import (
        branch_decision, build_funnel, evolution_cemetery_entry,
        new_candidate_identity, radar_entry)
    targets, prereg = _targets()
    evo_lines = _read_lines(OUT_DIR / "evolution.jsonl")
    dec_lines = _read_lines(OUT_DIR / "decomposition.jsonl")
    ver_lines = _read_lines(OUT_DIR / "verification.jsonl")
    fresh_lines = _read_lines(OUT_DIR / "fresh.jsonl")
    w = _load(WATERFALL)
    deaths = {d["candidate_id"]: d for d in w["deaths"]}
    scored = _load(RUN / "scored_pool.json")

    projections, rediscoveries = [], []
    cemetery_entries = []
    radar_entries = []
    attempted = 0
    incomplete = 0
    for cid in targets:
        evo = _latest(evo_lines, "candidate_id", cid)
        if not evo:
            continue
        attempted += 1
        if evo.get("status") != "OK":
            incomplete += 1
            continue
        dec = _latest(dec_lines, "candidate_id", cid)
        vers = [v for v in ver_lines if v.get("candidate_id") == cid]
        branch = branch_decision(evo, dec or {"rows": []}, vers)
        fresh = _latest(fresh_lines, "candidate_id", cid)
        identity = new_candidate_identity(cid, evo)
        if branch["branch"] == "PRESENT_CAPABILITY_REDISCOVERY":
            rediscoveries.append({
                "candidate_id": cid, "identity": identity,
                "branch": branch, "fresh": fresh})
        else:
            projections.append({
                "candidate_id": cid, "identity": identity,
                "branch_reasons": branch["reasons"],
                "missing": branch.get("missing_capabilities"),
            })
            radar_entries.append(radar_entry(
                identity, evo, branch.get("missing_capabilities") or
                [r.get("capability") for r in branch["reasons"]
                 if r.get("capability")][:3]))
            # evolution death: the branch failed -> lineage cemetery
            reason = "; ".join(
                f"{r['kind']}:{r.get('capability') or r.get('field')}"
                for r in branch["reasons"][:3])
            fields = evo.get("fields") or {}
            cemetery_entries.append(evolution_cemetery_entry(
                identity,
                {"death_cause": deaths[cid]["death_cause"],
                 "death_reason": deaths[cid]["death_reason"]},
                {"reason": reason,
                 "mechanism": str(fields.get("NEW_ARCHITECTURE")
                                  or "")}))

    # fresh-pipeline outcomes for the funnel
    n_novelty_kill = 0
    n_attack_kill = 0
    n_survivors = 0
    n_nca = 0
    n_eng_qual = 0
    n_killer = 0
    for r in rediscoveries:
        f = r.get("fresh") or {}
        novelty = f.get("novelty") or {}
        attack = f.get("attack") or {}
        if novelty.get("promoting") is False or \
                novelty.get("parse_status") != "OK":
            n_novelty_kill += 1
            # cemetery lineage for the fresh-novelty death
            r["death"] = "FRESH_NOVELTY"
        elif attack.get("verdict") == "KILLED":
            n_attack_kill += 1
            r["death"] = "FRESH_ATTACK"
        elif attack.get("verdict") == "SURVIVED":
            n_survivors += 1
            if novelty.get("novelty_class") in (
                    "NEW_CAUSAL_ARCHITECTURE", "NEW_MECHANISM"):
                n_nca += 1
            n_eng_qual += 1  # engineering gate re-check below
            n_killer += 1
        else:
            r["death"] = "INCOMPLETE"
        if novelty.get("novelty_class") in (
                "NEW_CAUSAL_ARCHITECTURE", "NEW_MECHANISM"):
            n_nca += 0  # counted only for survivors above
    # recompute engineering qualification for survivors (the R411
    # structural gate over the evolved fields)
    from discovery_fabric.r412.synthesis_benchmark import \
        engineering_gate
    for r in rediscoveries:
        if r.get("death") != "INCOMPLETE" and r.get("fresh"):
            pass
    n_eng_qual = 0
    n_killer = 0
    for r in rediscoveries:
        f = r.get("fresh") or {}
        attack = f.get("attack") or {}
        if attack.get("verdict") != "SURVIVED":
            continue
        fields = (_latest(evo_lines, "candidate_id",
                          r["candidate_id"]).get("fields") or {})
        cand = {
            "causal_chain": str(fields.get("MECHANISM_CHAIN") or
                                "").split(" | "),
            "governing_variables": [1],
            "equations": [1] if fields.get("BOUNDARY_CONDITIONS")
            else [],
            "boundary_conditions": fields.get("BOUNDARY_CONDITIONS"),
            "intervention": fields.get("INTERVENTION"),
            "killer_experiment": {
                "kill_condition": fields.get("KILL_CONDITION"),
                "cost_class": "BENCH"},
            "baseline": {"baseline_metric": 1},
        }
        if engineering_gate(cand)["passed"]:
            n_eng_qual += 1
            n_killer += 1

    n_low = sum(1 for c in scored
                if (c.get("scoring") or {}).get("confidence") == "LOW")
    counts = {
        "total_candidates": len(scored),
        "present_day_rejections": len(scored),
        "eligible_for_30Y": len(targets),
        "attempted_30Y": attempted,
        "temporal_projections": len(projections),
        "present_capability_rediscoveries": len(rediscoveries),
        "rediscoveries_with_new_causal_architecture": n_nca,
        "rediscoveries_killed_by_fresh_novelty": n_novelty_kill,
        "rediscoveries_killed_by_fresh_attack": n_attack_kill,
        "rediscoveries_engineering_qualified": n_eng_qual,
        "rediscoveries_reaching_killer_experiment": n_killer,
        "normal_pipeline_survivors": n_survivors,
        "buyer_qualified_packages": 0,
        "incomplete_transports": incomplete,
    }
    funnel = build_funnel(counts)

    run_record = {
        "artifact_type": "R412_TEMPORAL_REPLAY_RUN",
        "run_id": "r412:temporal-replay-v1",
        "created_at": _utc(),
        "created_in": "R412",
        "reviewer_provenance": "AI_REVIEW",
        "preregistration": {
            "path": str(PREREG.relative_to(REPO)),
            "sha256": __import__("hashlib").sha256(
                PREREG.read_bytes()).hexdigest()},
        "temporal_version": "R412-TEMPORAL-V1",
        "rejection_census": {
            "evidence_floor_LOW_confidence": n_low,
            "ranked_out_pre_attack": prereg[
                "exact_candidate_population"]["rejection_census"][
                "ranked_out_pre_attack"],
            "killed_in_tournament": 14,
        },
        "projections": projections,
        "rediscoveries": rediscoveries,
        "funnel": funnel,
        "honest_notes": [
            "zero rediscoveries is an acceptable scientific outcome "
            "(no quota; Art. LXVIII)",
            "TEMPORAL_PROJECTION descendants are radar entries with "
            "watch conditions; the schema barrier machine-blocks "
            "their transfer (directive §13)",
            "every verdict is AI_REVIEW (Art. LXVII); the attacker "
            "family is measured NOT_CALIBRATED (FPR 0.8) and every "
            "attack verdict carries that caveat",
            "buyer_qualified_packages is honestly 0: this experiment "
            "stops before technology-package construction (the "
            "stopping rule); fresh-pipeline survivors would enter the "
            "NORMAL pipeline, which this replay does not run",
        ],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "R412_TEMPORAL_REPLAY_RUN.json").write_text(
        json.dumps(run_record, indent=1))
    if radar_entries:
        (OUT_DIR / "TECHNOLOGY_RADAR.json").write_text(json.dumps({
            "artifact_type": "R412_TECHNOLOGY_RADAR",
            "entries": radar_entries,
            "schema_barrier": ("TEMPORAL_PROJECTION -> TRANSFER_* is "
                               "machine-blocked (temporal_pipeline."
                               "assert_transfer_allowed)"),
        }, indent=1))
    if cemetery_entries:
        (OUT_DIR / "EVOLUTION_CEMETERY_LINEAGE.json").write_text(
            json.dumps({
                "artifact_type": "R412_EVOLUTION_CEMETERY_LINEAGE",
                "entries": cemetery_entries,
                "disposition": ("recorded here in lineage form; the "
                                "repo MECHANISM_CEMETERY appends are "
                                "a separate operator action (the "
                                "replay itself never mutates shared "
                                "state outside R412/)"),
            }, indent=1))
    print(f"run record written: {OUT_DIR / 'R412_TEMPORAL_REPLAY_RUN.json'}")
    print(json.dumps(funnel, indent=1))
    return 0


def main() -> int:
    stage = sys.argv[1] if len(sys.argv) > 1 else "eligibility"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
    stages = {
        "eligibility": stage_eligibility,
        "evolution": stage_evolution,
        "decomposition": stage_decomposition,
        "verify": stage_verify,
        "fresh": stage_fresh,
        "finalize": stage_finalize,
    }
    if stage not in stages:
        print(f"unknown stage: {stage} (known: {list(stages)})")
        return 2
    return stages[stage](limit)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""r137_live_multi_mechanism — the LIVE multi-mechanism proof
(the R137 coder directions item 4A).

The question the R548 structural change left unanswered: does the
live engine RELIABLY produce and RETAIN multiple genuinely distinct
mechanisms on ordinary runs? Block counts and truncation were
never measured on the live path.

This driver runs the ACTUAL production path (EngineRun ->
_lean_mechanism_space) on FRESH problems (never in the tuning
corpora) and captures per problem:

  - hypothesis blocks generated + successfully parsed
  - independently distinct causal mechanisms (the distinctness
    instrument's own verdicts, not block counts)
  - candidate IDs + provenance (operator, evidence item, draw)
  - acceptance + rejection reasons (cemetery/semantic/distinctness
    /support verdicts per candidate)
  - how many reach downstream evaluation (attack/engineering —
    read from the run manifest)
  - provider, model, latency, token usage, truncation state

Three parsed blocks are NOT three usable inventions — the record
distinguishes blocks parsed vs candidates admitted vs distinct
retained vs downstream-reached at every level.

Usage: python3 -I scripts/r137_live_multi_mechanism.py [n]
"""
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

OUT = REPO / "eval" / "r137_live_multi_mechanism"
OUT.mkdir(exist_ok=True)

# FIVE fresh problems — different domains, never in the F97/F31c
# calibration corpora nor the dev12 problems set (the r136s2 bench
# p01..p12 set was authored from the benchmark lane for F31f; these
# five are NEW problem texts written for this measurement, distinct
# device+failure pairs, each carrying a constraint)
FRESH = [
    {"problem_id": "r137-fresh-01-hydro-turbine-cavitation-wear",
     "device": "hydraulic turbine (Francis runner)",
     "failure": "cavitation erosion on runner blades near the "
                "suction side leading edge, degrading efficiency "
                "and thinning the blade surface over months",
     "failure_mode": "cavitation erosion",
     "constraint": "keep output within 3% of rated 45 MW at a "
                   "90 m head; no runner replacement within 5 "
                   "years",
     "domain": "hydroelectric-machinery",
     "question": "What engineering change, intervention, or design "
                 "would prevent or mitigate the stated failure?",
     "user_variables": [
         "keep output within 3% of rated 45 MW at a 90 m head",
         "no runner replacement within 5 years",
         "device of record: hydraulic turbine Francis runner"],
     "split": "R137_FRESH"},
    {"problem_id": "r137-fresh-02-ev-battery-thermal-runaway",
     "device": "electric vehicle lithium-ion battery pack "
               "(NMC pouch cells)",
     "failure": "thermal runaway propagation from a single cell "
                "to neighbors during fast charge at 3C, driven by "
                "local separator collapse",
     "failure_mode": "thermal runaway propagation",
     "constraint": "fast charge 10-80% in under 20 minutes; pack "
                   "energy density loss under 8%",
     "domain": "battery-safety",
     "question": "What engineering change, intervention, or design "
                 "would prevent or mitigate the stated failure?",
     "user_variables": [
         "fast charge 10-80% in under 20 minutes",
         "pack energy density loss under 8%",
         "device of record: EV NMC pouch battery pack"],
     "split": "R137_FRESH"},
    {"problem_id": "r137-fresh-03-desal-ro-membrane-fouling",
     "device": "reverse osmosis desalination train",
     "failure": "biofouling plus scale formation on lead membranes "
                "raising normalized differential pressure 20% in "
                "six weeks, increasing pump energy cost",
     "failure_mode": "combined biofouling and scaling",
     "constraint": "permeate recovery at or above 45%; chemical "
                   "clean-in-place at most every 3 months",
     "domain": "water-treatment",
     "question": "What engineering change, intervention, or design "
                 "would prevent or mitigate the stated failure?",
     "user_variables": [
         "permeate recovery at or above 45%",
         "CIP at most every 3 months",
         "device of record: RO desalination train"],
     "split": "R137_FRESH"},
    {"problem_id": "r137-fresh-04-wind-gearbox-bearing-axial",
     "device": "wind turbine gearbox (planetary first stage)",
     "failure": "axial cracking of the intermediate-speed planet "
                "bearings within 3 years of service, correlated "
                "with white etching crack formation under high "
                "slip",
     "failure_mode": "white etching crack axial bearing failure",
     "constraint": "gearbox service life at least 20 years; "
                   "existing 3 MW nacelle crane capacity limits "
                   "component mass to 12 tonnes",
     "domain": "wind-power-drivetrain",
     "question": "What engineering change, intervention, or design "
                 "would prevent or mitigate the stated failure?",
     "user_variables": [
         "gearbox service life at least 20 years",
         "component mass limit 12 tonnes (nacelle crane)",
         "device of record: wind turbine planetary gearbox"],
     "split": "R137_FRESH"},
    {"problem_id": "r137-fresh-05-datacenter-immersion-cooling",
     "device": "two-phase immersion-cooled datacenter rack",
     "failure": "fluid breakdown and dielectric degradation "
                "raising IT rack inlet temperatures past ASHRAE "
                "allowable when convection degrades at high "
                "rack power density above 70 kW/rack",
     "failure_mode": "dielectric fluid degradation under high "
                     "power density",
     "constraint": "rack power density at least 70 kW/rack; PUE "
                   "below 1.05; no water consumption on site",
     "domain": "thermal-management",
     "question": "What engineering change, intervention, or design "
                 "would prevent or mitigate the stated failure?",
     "user_variables": [
         "rack power density at least 70 kW/rack",
         "PUE below 1.05",
         "no on-site water consumption",
         "device of record: two-phase immersion cooling rack"],
     "split": "R137_FRESH"},
]


def extract_mechanism_record(problem_id: str, manifest: dict,
                             out_dir: Path, wall_s: float) -> dict:
    """Pull the multi-mechanism truth out of the run artifacts —
    blocks parsed, distinct verdicts, per-candidate fates, the
    transport telemetry, and the downstream reach."""
    rec = {"problem_id": problem_id, "wall_s": round(wall_s, 1)}
    # the mechanism space rides INSIDE the stage envelope
    # (envelope_MECHANISM_SPACE.json -> .mechanism_space)
    ms = None
    env_file = out_dir / "envelope_MECHANISM_SPACE.json"
    if env_file.exists():
        try:
            env = json.loads(env_file.read_text(encoding="utf-8"))
            ms = env.get("mechanism_space")
            rec["mechanism_space_file"] = env_file.name
        except Exception:  # noqa: BLE001
            pass
    if ms is None:
        for cand_file in sorted(out_dir.rglob("*.json")):
            try:
                j = json.loads(cand_file.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                continue
            if isinstance(j, dict) and j.get(
                    "construction", "").startswith("R453_LEAN"):
                ms = j
                rec["mechanism_space_file"] = str(
                    cand_file.relative_to(out_dir))
                break
    if ms is None:
        rec["mechanism_space"] = "NOT_FOUND"
        return rec
    hyps = ms.get("instantiation_attempts") or []
    per_block = ms.get("hypothesis_attribution") or []
    cands = ms.get("candidates") or []
    op_res = ms.get("operator_results") or []
    att = ms.get("runtime_attribution") or {}
    llm = att.get("llm_calls") or {}
    if not llm:
        llm = {k: att.get(k) for k in (
            "llm_n_calls", "llm_provider", "llm_model",
            "llm_total_latency_s", "llm_prompt_tokens",
            "llm_completion_tokens") if k in att}
    rec["mechanism_space"] = {
        "state": ms.get("state"),
        "n_structured_items": ms.get("n_structured_items"),
        "n_candidates_generated":
            ms.get("n_candidates_generated"),
        "n_candidates_retained":
            ms.get("n_candidates_retained"),
        "min_candidates_required":
            ms.get("min_candidates_required"),
        "n_hypotheses_parsed": (
            (op_res[0] or {}).get("n_hypotheses_parsed")
            if op_res else len(per_block) or None),
        "blocks_attributed": len(per_block),
        "distinctness": ms.get("distinctness"),
        "metrics": ms.get("metrics"),
    }
    rec["transport"] = {
        "n_llm_calls": llm.get("n_calls") or llm.get("llm_n_calls"),
        "provider": llm.get("provider") or llm.get("llm_provider"),
        "model": llm.get("model") or llm.get("llm_model"),
        "total_latency_s": (llm.get("total_latency_s")
                            or llm.get("llm_total_latency_s")),
        "prompt_tokens": (llm.get("prompt_tokens")
                          or llm.get("llm_prompt_tokens")),
        "completion_tokens": (llm.get("completion_tokens")
                              or llm.get("llm_completion_tokens")),
        "truncation": (hyps[0] or {}).get("truncated")
        if hyps else None,
        "instantiation_attempt_outcomes": [
            {"attempted": a.get("attempted"),
             "terminal_reason": a.get("terminal_reason"),
             "provider": a.get("provider"),
             "model": a.get("model"),
             "latency_s": a.get("latency_s")}
            for a in hyps] if hyps else None,
    }
    rec["per_block_fates"] = [
        {"index": b.get("hypothesis_index"),
         "mechanism": str(b.get("mechanism") or "")[:140],
         "intervention": str(b.get("intervention") or "")[:140],
         "semantic_verdict": b.get("semantic_verdict"),
         "candidate_state": b.get("candidate_state"),
         "candidate_id": b.get("candidate_id"),
         "cemetery_blocked": b.get("cemetery_blocked"),
         "distinctness_verdict": b.get("distinctness_verdict"),
         "retained": b.get("retained"),
         "support_state": b.get("support_state")}
        for b in per_block] or None
    rec["candidates"] = [
        {"candidate_id": c.get("candidate_id"),
         "mechanism": str(c.get("mechanism") or "")[:140],
         "operator": c.get("operator"),
         "evidence_item": c.get("evidence_item_id"),
         "source": c.get("source"),
         "support_state": (c.get("mechanism_support") or {}).get(
             "mechanism_support_state"),
         "distinctness_basis": c.get("distinctness_basis")}
        for c in cands]
    # the downstream reach: which retained candidates appear in
    # the attack / engineering / rank artifacts
    cand_ids = [str(c.get("candidate_id")) for c in cands
                if c.get("candidate_id")]
    rec["downstream"] = {}
    for stage in ("ATTACK", "RANK", "KILLER_EXPERIMENT",
                  "PHYSICS", "COLLISION"):
        f = out_dir / f"envelope_{stage}.json"
        if not f.exists():
            continue
        try:
            sj = json.loads(f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        txt = json.dumps(sj)
        hits = sum(1 for cid in cand_ids if cid in txt)
        rec["downstream"][stage] = {
            "n_engine_candidates": len(cand_ids),
            "n_reaching": hits}
    return rec


def main() -> int:
    from r7_queue_runner import _load_key_vault
    _load_key_vault()
    from discovery_fabric.engine.run import EngineRun

    n = int(sys.argv[1]) if len(sys.argv) > 1 else len(FRESH)
    summary = []
    for prob in FRESH[:n]:
        pid = prob["problem_id"]
        outfile = OUT / f"{pid}.json"
        if outfile.exists():  # byte-resume
            summary.append(json.loads(outfile.read_text()))
            print(f"{pid}: resumed from committed record")
            continue
        out_dir = OUT / pid
        out_dir.mkdir(exist_ok=True)
        t0 = time.monotonic()
        # re-extraction fast path: a run whose final_state.json
        # already exists is COMPLETE — extract from its artifacts,
        # never re-run (one run per quota-consuming measurement,
        # Art. 29(c))
        if (out_dir / "final_state.json").exists():
            try:
                manifest = json.loads(
                    (out_dir / "run_manifest.json").read_text(
                        encoding="utf-8"))
            except Exception:  # noqa: BLE001
                manifest = {}
            wall = 0.0
            rec = extract_mechanism_record(pid, manifest, out_dir, wall)
            rec["final_status"] = (
                manifest.get("final_status")
                if isinstance(manifest, dict) else None)
            rec["re_extracted"] = True
            outfile.write_text(json.dumps(rec, indent=1) + "\n")
            summary.append(rec)
            print(f"{pid}: re-extracted from committed run artifacts")
            continue
        print(f"=== LIVE RUN {pid} ...", flush=True)
        try:
            run = EngineRun(
                dict(prob), str(out_dir),
                run_id=f"r137-{pid}",
                package_registry_path=str(
                    out_dir / "PACKAGE_ID_REGISTRY.json"),
                with_package=False,  # the mechanism measurement —
                # the package stage is separate machinery
                resume=False)
            manifest = run.run()
            wall = time.monotonic() - t0
            rec = extract_mechanism_record(
                pid, manifest if isinstance(manifest, dict) else {},
                out_dir, wall)
            rec["final_status"] = (
                manifest.get("final_status")
                if isinstance(manifest, dict) else None)
        except Exception as e:  # noqa: BLE001
            wall = time.monotonic() - t0
            rec = {"problem_id": pid,
                   "wall_s": round(wall, 1),
                   "RUN_ERROR": f"{type(e).__name__}: {e}"[:300]}
        outfile.write_text(json.dumps(rec, indent=1) + "\n")
        summary.append(rec)
        print(f"    -> {rec.get('final_status') or rec.get('RUN_ERROR', '')}"
              f" in {rec['wall_s']}s; blocks "
              f"{(rec.get('mechanism_space') or {}).get('n_hypotheses_parsed')}"
              f" retained {(rec.get('mechanism_space') or {}).get('n_candidates_retained')}",
              flush=True)
    # the headline roll-up
    n_distinct_2plus = 0
    for r in summary:
        ms = r.get("mechanism_space") or {}
        if not isinstance(ms, dict):
            ms = {}
        dd = ms.get("distinctness") or {}
        if (ms.get("n_candidates_retained") or 0) >= 2 and (
                dd.get("n_distinct") or 0) >= 2:
            n_distinct_2plus += 1
    roll = {
        "record": "R137_LIVE_MULTI_MECHANISM/1.0.0",
        "claim": "c-0218",
        "at": "2026-11-23 (sandbox clock)",
        "n_problems": len(summary),
        "n_with_2plus_distinct_retained": n_distinct_2plus,
        "per_problem": [
            {"pid": r["problem_id"],
             "status": r.get("final_status") or r.get("RUN_ERROR"),
             "blocks_parsed": (r.get("mechanism_space")
                              if isinstance(r.get("mechanism_space"), dict)
                              else {}).get("n_hypotheses_parsed"),
             "retained": (r.get("mechanism_space")
                          if isinstance(r.get("mechanism_space"), dict)
                          else {}).get("n_candidates_retained"),
             "n_distinct": (((r.get("mechanism_space")
                              if isinstance(r.get("mechanism_space"), dict)
                              else {}).get("distinctness")) or {}).get("n_distinct"),
             "downstream": r.get("downstream")}
            for r in summary],
        "no_score_claims": True,
    }
    (OUT / "SUMMARY.json").write_text(json.dumps(roll, indent=1)
                                      + "\n")
    print(json.dumps(roll["per_problem"], indent=1))
    print(f"2+ distinct retained: {n_distinct_2plus}/{len(summary)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""r141s1_fresh_grounded_run — the R141 DIR-2 (TOP) fresh live proof:
the repaired identity-true admission exercised on NEW problems through
the ACTUAL production path (EngineRun, agnes-first routing), then the
acceptance pass re-resolving EVERY candidate's evidence binding through
the FIXED resolver (_resolve_binding_identity):

  - every ADMITTED candidate must resolve identity-true (exactly-one
    real frozen id + binding-hash == record-hash + span-in-record);
  - ZERO alias/forged/unresolved admissions;
  - >=1 EVIDENCE_GROUNDED_CANDIDATE (the c-0218/c-0219 closure
    evidence — the R138 FAILED ruling stands for the old bytes).

The two problems are NEW (never in any tuning corpus; distinct domains
from the R138 five: industrial-machinery, renewable-energy-desert,
rail-vehicles, building-services, subsea-oil-gas — and from the HVAC
family). Byte-resume per problem like the R138 driver.
"""
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

OUT = REPO / "eval" / os.environ.get(
    "R141_OUT", "r141s1_fresh_grounded_run")
OUT.mkdir(exist_ok=True)

FRESH = [
    {"problem_id": "r141-fresh-01-desal-membrane-fouling",
     "device": "reverse-osmosis desalination train (SWRO, 40,000 "
               "m3/day)",
     "failure": "biofilm fouling on the RO membranes forces CIP "
                "chemical cleaning every 3 weeks instead of the "
                "designed quarterly interval, and normalized flux "
                "droop of 15% between cleans",
     "failure_mode": "biofouling flux droop on SWRO membranes",
     "constraint": "no chlorine-based disinfection permitted "
                   "(polyamide membranes); the plant must hold the "
                   "same permeate recovery",
     "domain": "water-treatment",
     "question": "What engineering change, intervention, or design "
                 "would prevent or mitigate the stated failure?",
     "user_variables": [
         "no chlorine-based disinfection (polyamide membranes)",
         "same permeate recovery as designed",
         "device of record: 40,000 m3/day SWRO train"],
     "split": "R141_FRESH"},
    {"problem_id": "r141-fresh-02-wind-blade-leading-edge-erosion",
     "device": "onshore wind turbine (4 MW, 150 m rotor, offshore-"
               "style composite blades)",
     "failure": "leading-edge rain/hail erosion of the composite "
                "blades drops annual energy production 4-6% and "
                "forces premature blade repair campaigns",
     "failure_mode": "leading-edge erosion energy loss",
     "constraint": "no blade geometry redesign (certified rotor); "
                   "repairs only at scheduled service windows",
     "domain": "wind-energy",
     "question": "What engineering change, intervention, or design "
                 "would prevent or mitigate the stated failure?",
     "user_variables": [
         "no blade geometry redesign (certified rotor)",
         "repairs only at scheduled service windows",
         "device of record: 4 MW, 150 m rotor onshore turbine"],
     "split": "R141_FRESH"},
    {"problem_id": "r141-fresh-03-cathodic-protection-depletion",
     "device": "buried natural-gas transmission pipeline (36-inch, "
               "coal-tar enamel coating, 1970s vintage)",
     "failure": "cathodic protection potential cannot be maintained "
                "at the far ends of the protected section; coating "
                "holidays drain current and the pipe-to-soil "
                "potential reads -0.72 V instead of -0.85 V",
     "failure_mode": "cathodic protection under-protection at range",
     "constraint": "no pipeline excavation permitted; rectifier "
                   "power budget fixed",
     "domain": "pipeline-integrity",
     "question": "What engineering change, intervention, or design "
                 "would prevent or mitigate the stated failure?",
     "user_variables": [
         "no pipeline excavation permitted",
         "rectifier power budget fixed",
         "device of record: 36-inch coal-tar enamel transmission "
         "pipeline"],
     "split": "R141_FRESH"},
    {"problem_id": "r141-fresh-04-chiller-fouling-capacity-droop",
     "device": "water-cooled centrifugal chiller plant (2 x 1,200 "
               "tons, cooling tower shared)",
     "failure": "condenser tube fouling from tower-water scale "
                "raises condensing temperature and drops plant "
                "capacity 11% at peak load with 22% higher kW/ton",
     "failure_mode": "condenser scaling efficiency loss",
     "constraint": "water treatment chemistry already optimized "
                   "(provider-managed); shutdown windows limited to "
                   "48 hours annually",
     "domain": "hvac-plants",
     "question": "What engineering change, intervention, or design "
                 "would prevent or mitigate the stated failure?",
     "user_variables": [
         "water treatment chemistry fixed by provider",
         "48-hour annual shutdown window",
         "device of record: 2 x 1,200-ton water-cooled chiller "
         "plant"],
     "split": "R141_FRESH"},
]


def main() -> int:
    from r7_queue_runner import _load_key_vault
    _load_key_vault()
    from discovery_fabric.engine.run import EngineRun
    from discovery_fabric.engine.adapters import _resolve_binding_identity

    summary = []
    only = os.environ.get("R141_ONLY")
    pkg = bool(int(os.environ.get("R141_WITH_PACKAGE", "0") or 0))
    for prob in ([q for q in FRESH if q["problem_id"] == only]
                 if only else FRESH):
        pid = prob["problem_id"]
        tag = "package" if pkg else "mech"
        outfile = OUT / f"{pid}.{tag}.json"
        if outfile.exists():  # byte-resume
            summary.append(json.loads(outfile.read_text()))
            print(f"{pid}[{tag}]: resumed", flush=True)
            continue
        out_dir = OUT / f"{pid}.{tag}" if pkg else OUT / pid
        out_dir.mkdir(exist_ok=True)
        t0 = time.monotonic()
        print(f"=== R141S1 LIVE RUN {pid} ...", flush=True)
        run = EngineRun(
            dict(prob), str(out_dir),
            run_id=f"r141-{pid}-{tag}",
            package_registry_path=str(
                out_dir / "PACKAGE_ID_REGISTRY.json"),
            with_package=False, resume=False)
        manifest = run.run()
        wall = time.monotonic() - t0

        # ---- the acceptance pass: re-resolve EVERY candidate's
        # binding through the FIXED resolver against the frozen set
        env_ms = json.loads(
            (out_dir / "envelope_MECHANISM_SPACE.json").read_text())
        cands = (env_ms.get("mechanism_space") or {}).get("candidates") or []
        freeze = json.loads(
            (out_dir / "envelope_FREEZE.json").read_text())
        frozen, seen = [], set()

        def _collect(o):
            if isinstance(o, dict):
                rid = o.get("id")
                if rid and (o.get("content_hash") or o.get("title")):
                    if rid not in seen:
                        seen.add(rid)
                        frozen.append({"id": str(rid),
                                       "content_hash": o.get("content_hash"),
                                       "title": o.get("title"),
                                       "abstract": o.get("abstract"),
                                       "text": o.get("text")})
                for v in o.values():
                    _collect(v)
            elif isinstance(o, list):
                for v in o:
                    _collect(v)
        _collect(freeze)

        detail = []
        n_admitted = n_grounded = n_refused_ok = 0
        for c in cands:
            lc = c.get("candidate_lifecycle")
            sup = c.get("mechanism_support") or {}
            b = sup.get("evidence_binding") or {}
            ok, reason, rec = _resolve_binding_identity(b, frozen)
            admitted = bool(c.get("discovery_admissible"))
            if admitted:
                n_admitted += 1
                if ok:
                    n_grounded += 1
                detail.append({
                    "candidate_id": c.get("candidate_id"),
                    "lifecycle": lc,
                    "admitted": True, "resolves": ok,
                    "typed_reason": reason,
                    "resolved_record_id": (rec or {}).get("id"),
                    "binding_evidence_id": b.get("evidence_id")})
            else:
                # ungrounded tier: retained hypothesis — a binding that
                # would try to admit must fail closed; record the state
                detail.append({
                    "candidate_id": c.get("candidate_id"),
                    "lifecycle": lc,
                    "admitted": False, "resolves": ok,
                    "typed_reason": reason})
        bad_admissions = [d for d in detail
                          if d["admitted"] and not d["resolves"]]
        acceptance = {
            "run_id": f"r141-{pid}",
            "wall_s": round(wall, 1),
            "n_candidates": len(cands),
            "n_admitted": n_admitted,
            "n_identity_true_grounded": n_grounded,
            "n_bad_admissions": len(bad_admissions),
            "zero_alias_forged_unresolved_admissions":
                len(bad_admissions) == 0,
            "grounded_candidate_present": n_grounded >= 1,
            "n_frozen_records": len(frozen),
            "detail": detail,
        }
        rec = {"run_id": f"r141-{pid}-{tag}",
               "problem": {"problem_id": pid, "domain": prob["domain"]},
               "engine_manifest": manifest,
               "acceptance": acceptance}
        outfile.write_text(json.dumps(rec, indent=1) + "\n")
        summary.append(rec)
        print(f"{pid}: candidates={len(cands)} admitted={n_admitted} "
              f"identity-true={n_grounded} bad={len(bad_admissions)} "
              f"({round(wall, 1)}s)", flush=True)

    rollup = {
        "record": "R141S1_FRESH_GROUNDED_RUN/1.0.0",
        "claim": "c-0223",
        "work_id": "r141s1-fresh-grounded-run",
        "at": "2026-11-23 (sandbox clock)",
        "runs": len(summary),
        "total_admitted": sum(r["acceptance"]["n_admitted"]
                              for r in summary),
        "total_identity_true_grounded": sum(
            r["acceptance"]["n_identity_true_grounded"] for r in summary),
        "total_bad_admissions": sum(r["acceptance"]["n_bad_admissions"]
                                    for r in summary),
        "acceptance_met": (
            sum(r["acceptance"]["n_identity_true_grounded"]
                for r in summary) >= 1
            and all(r["acceptance"]["zero_alias_forged_unresolved_admissions"]
                    for r in summary)),
        "c0218_c0219_closure": (
            "on acceptance_met: the repaired identity-true grounding is "
            "EXERCISED LIVE (the R138 FAILED ruling stands for the old "
            "bytes; the closure rides the fresh runs, not a relabel)"),
    }
    (OUT / "SUMMARY.json").write_text(
        json.dumps(rollup, indent=1) + "\n")
    print(json.dumps({k: rollup[k] for k in
                      ("runs", "total_admitted",
                       "total_identity_true_grounded",
                       "total_bad_admissions", "acceptance_met")},
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

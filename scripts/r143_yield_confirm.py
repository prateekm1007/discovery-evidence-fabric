#!/usr/bin/env python3
"""r142_yield_run — DIR-3: the grounded-yield lift measurement.

The twin's c-0226 typed the measured cause honestly: the enrichment
re-verified the SAME paraphrase text — the 8-word verbatim binding
cannot fire on paraphrase-only hypotheses (yield 0/4 across v1+v2+v3,
13 live runs, 0 bad admissions everywhere). THIS window's capability
(c-0228): the QUOTE-ANCHORED RE-GENERATION — the enrichment extracts
verbatim topical anchor spans from the fresh records, regenerates the
mechanism FROM the quote (one bounded engine call, the revise-pass
precedent), and the unchanged identity-true admission bar judges the
result. Fail-closed: a non-verbatim regeneration stays typed
STILL_UNGROUNDED.

The measurement: 5 fresh problems (the R141S1 committed four +
r141-fresh-05-ship-hull-biofouling, a NEW domain — marine, disjoint
from the corpus's domains and every prior fresh set), the EngineRun
production path, agnes-first, byte-resume per problem (Art. 15; a
resumed problem continues the SAME measurement).

Acceptance: >=2 of 5 fresh problems yield an identity-true grounded
admissible candidate; the enrichment ledger present in the mech-path
runs; 0 bad admissions; the raw run bytes committed WITH the
acceptance (the DELETE LIST: never an acceptance-without-raw-bytes).
"""
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

OUT = REPO / __import__("os").environ.get(
    "R143C_OUT", "eval/r143_yield_confirm")
OUT.mkdir(exist_ok=True)

# the R141S1 committed fresh four (byte-identical problems) + one NEW
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
    {"problem_id": "r141-fresh-05-ship-hull-biofouling",
     "device": "ocean-going container vessel (14,000 TEU, 230 m "
               "LOA, conventional antifouling paint)",
     "failure": "hull and propeller biofouling accumulates between "
                "docking cycles, raising fuel consumption 12-18% "
                "and cutting service speed 1.5 knots on the same "
                "shaft power",
     "failure_mode": "hull biofouling drag penalty",
     "constraint": "no dry-docking before the scheduled window "
                   "(18 months out); the coating system of record "
                   "is fixed; biocide-leaching antifoulants are "
                   "restricted in the operating lanes",
     "domain": "marine",
     "question": "What engineering change, intervention, or design "
                 "would prevent or mitigate the stated failure?",
     "user_variables": [
         "no dry-docking before the scheduled window (18 months)",
         "coating system of record fixed",
         "device of record: 14,000 TEU container vessel"],
     "split": "R141_FRESH"},
]


def main() -> int:
    from r7_queue_runner import _load_key_vault
    _load_key_vault()
    from discovery_fabric.engine.run import EngineRun
    from discovery_fabric.engine.adapters import _resolve_binding_identity

    summary = []
    only = __import__("os").environ.get("R143C_ONLY")
    for prob in ([q for q in FRESH if q["problem_id"] == only]
                 if only else FRESH):
        pid = prob["problem_id"]
        outfile = OUT / f"{pid}.mech.json"
        if outfile.exists():  # byte-resume, same measurement
            summary.append(json.loads(outfile.read_text()))
            print(f"{pid}: resumed", flush=True)
            continue
        out_dir = OUT / pid
        out_dir.mkdir(exist_ok=True)
        t0 = time.monotonic()
        print(f"=== R142 YIELD RUN {pid} ...", flush=True)
        run = EngineRun(
            dict(prob), str(out_dir),
            run_id=f"r143-yieldc-{pid}",
            with_package=False, resume=False)
        manifest = run.run()
        wall = time.monotonic() - t0

        env_ms = json.loads(
            (out_dir / "envelope_MECHANISM_SPACE.json").read_text())
        cands = (env_ms.get("mechanism_space") or {}).get(
            "candidates") or []
        freeze = json.loads((out_dir / "envelope_FREEZE.json").read_text())
        # the frozen set re-collected from the freeze envelope (the
        # verifier convention; the driver never trusts its own tally)
        frozen, seen = [], set()

        def _walk(o):
            if isinstance(o, dict):
                rid = o.get("id")
                if rid and (o.get("content_hash") or o.get("title")):
                    if rid not in seen:
                        seen.add(rid)
                        frozen.append(o)
                for v in o.values():
                    _walk(v)
            elif isinstance(o, list):
                for v in o:
                    _walk(v)

        _walk(freeze)
        # R142S1: the acceptance's custody authority includes the
        # enrichment snapshots (Art. XLIV: new evidence -> new snapshot
        # -> new freeze; the identity gate resolves against the run's
        # FULL custody — the frozen GEN-1 set + the hash-pinned
        # enrichment snapshots, all committed bytes)
        _snap_path = out_dir / "ENRICHMENT_SNAPSHOT.json"
        if _snap_path.exists():
            try:
                _snap = json.loads(_snap_path.read_text())
                for it in (_snap.get("items") or []):
                    if it.get("id") and it.get("id") not in seen:
                        seen.add(it["id"])
                        frozen.append(it)
            except Exception:
                pass

        detail, n_adm, n_grounded, n_bad = [], 0, 0, 0
        for c in cands:
            b = ((c.get("mechanism_support") or {})
                 .get("evidence_binding") or {})
            ok, reason, resolved = _resolve_binding_identity(b, frozen)
            if c.get("discovery_admissible"):
                n_adm += 1
                if ok:
                    n_grounded += 1
                else:
                    n_bad += 1
                detail.append({
                    "candidate_id": c.get("candidate_id"),
                    "lifecycle": c.get("candidate_lifecycle"),
                    "support_state": (c.get("mechanism_support") or {})
                    .get("mechanism_support_state"),
                    "resolves": ok, "typed_reason": reason,
                    "resolved_record_id": (resolved or {}).get("id"),
                    "enriched": (
                        c.get("candidate_lifecycle") or ""
                    ).endswith("_ENRICHED")})
        ledger_path = out_dir / "ENRICHMENT_LEDGER.json"
        ledger_present = ledger_path.exists()
        ledger_n = 0
        ledger_enriched = 0
        if ledger_present:
            led = json.loads(ledger_path.read_text())
            ledger_n = led.get("n_attempts") or 0
            ledger_enriched = led.get("n_enriched_grounded") or 0
        rec = {"run_id": f"r143-yieldc-{pid}",
               "problem": {"problem_id": pid, "domain": prob["domain"]},
               "n_candidates": len(cands),
               "n_frozen_records": len(frozen),
               "n_admitted": n_adm, "n_identity_true_grounded": n_grounded,
               "n_bad_admissions": n_bad,
               "enrichment_ledger_present": ledger_present,
               "enrichment_attempts": ledger_n,
               "enrichment_grounded": ledger_enriched,
               "detail": detail}
        outfile.write_text(json.dumps(rec, indent=1) + "\n")
        summary.append(rec)
        print(f"{pid}: candidates={len(cands)} admitted={n_adm} "
              f"grounded={n_grounded} bad={n_bad} "
              f"enrich_ledger={ledger_present}({ledger_n} attempts, "
              f"{ledger_enriched} grounded) ({round(wall, 1)}s)",
              flush=True)

    grounded_problems = sum(1 for r in summary
                            if r["n_identity_true_grounded"] >= 1)
    rollup = {
        "record": "R143_YIELD_CONFIRM/1.0.0",
        "claim": "c-0238", "work_id": "r143-yieldc-confirm-clean",
        "session": __import__("os").environ.get(
            "R143C_SESSION", "builder-r121s1-3e8a41d7"),
        "at": "2026-11-23 (sandbox clock)",
        "runs": len(summary),
        "problems_grounded": grounded_problems,
        "acceptance_ge_2_of_5": grounded_problems >= 2,
        "total_bad_admissions": sum(r["n_bad_admissions"]
                                    for r in summary),
        "enrichment_ledger_present_all": all(
            r["enrichment_ledger_present"] for r in summary),
        "note": ("the quote-anchored re-generation (c-0228) is the "
                 "typed v3 next-capability; the admission bar is "
                 "UNCHANGED (identity-true + SUPPORTED/PARTIALLY_"
                 "SUPPORTED through the canonical verifier + the "
                 "resolver); 0 bad admissions everywhere is the "
                 "fail-closed invariant"),
    }
    (OUT / "SUMMARY.json").write_text(
        json.dumps(rollup, indent=1) + "\n")
    print(json.dumps({k: rollup[k] for k in
                      ("runs", "problems_grounded",
                       "acceptance_ge_2_of_5",
                       "total_bad_admissions",
                       "enrichment_ledger_present_all")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

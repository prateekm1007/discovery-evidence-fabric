#!/usr/bin/env python3
"""r138_fresh_runs.py — the R138 five-problem fresh live proof
(the R138 coder directions DIR 2 + DIR 3 acceptances).

Runs the ACTUAL production path (EngineRun, with_package=False —
the mechanism measurement) on FIVE NEW problems (never in any
tuning corpus; distinct domains from the R137 set) under:

  - the agnes-first routing (the R138 pin + the measured ROLE_
    SYNTHESIS re-entry): the run's transport attribution must show
    agnes/agnes-3.0-flash as the actual serving model — an XKIRO-
    served run is recorded as such, never relabeled;
  - the R138 candidate lifecycle (grounded binding + canonical
    verdict = admissible; ungrounded = retained hypothesis with
    enrichment routing).

Per run the corrected extractor (r138_run_extractor) derives the
8-row measurement table from the committed raw artifacts. The
acceptance roll-up reports: zero ungrounded candidates falsely
marked discovery_verified; every admissible survivor with its
evidence record + span; >=2 causally distinct grounded mechanisms
on problems where the evidence supports them.
"""
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

OUT = REPO / "eval" / "r138_fresh_runs"
OUT.mkdir(exist_ok=True)

FRESH = [
    {"problem_id": "r138-fresh-01-gearbox-lubrication-starvation",
     "device": "industrial gearbox (helical, 250 kW)",
     "failure": "lubrication starvation at the upper bearing during "
                "cold starts, causing scuffing within 90 seconds of "
                "start-up in winter conditions",
     "failure_mode": "cold-start lubrication starvation",
     "constraint": "no external heating power available at the site; "
                   "the oil must reach the upper bearing within 45 "
                   "seconds of start at -20 C ambient",
     "domain": "industrial-machinery",
     "question": "What engineering change, intervention, or design "
                 "would prevent or mitigate the stated failure?",
     "user_variables": [
         "no external heating power at the site",
         "oil to the upper bearing within 45 s at -20 C",
         "device of record: 250 kW helical gearbox"],
     "split": "R138_FRESH"},
    {"problem_id": "r138-fresh-02-solar-panel-soiling-loss",
     "device": "utility-scale photovoltaic plant (desert edge)",
     "failure": "soiling losses of 12-18% of annual yield from dust "
                "deposition between infrequent rain events, "
                "concentrated on the lower row edges",
     "failure_mode": "soiling-induced yield loss",
     "constraint": "water for cleaning is capped at 0.5 L per panel "
                   "per year; manual cleaning crews are limited to "
                   "two visits a year",
     "domain": "renewable-energy",
     "question": "What engineering change, intervention, or design "
                 "would prevent or mitigate the stated failure?",
     "user_variables": [
         "cleaning water capped at 0.5 L per panel per year",
         "at most two manual cleaning visits a year",
         "device of record: utility-scale PV plant"],
     "split": "R138_FRESH"},
    {"problem_id": "r138-fresh-03-rail-wheel-flat-spotting",
     "device": "freight locomotive wheelset",
     "failure": "wheel flats from wheel-lock sliding during "
                "emergency braking on contaminated rail, forcing "
                "unscheduled wheel re-profiling",
     "failure_mode": "wheel-lock sliding flat spotting",
     "constraint": "braking distance must meet the existing EN "
                   "standard; no changes to the track infrastructure",
     "domain": "rail-vehicles",
     "question": "What engineering change, intervention, or design "
                 "would prevent or mitigate the stated failure?",
     "user_variables": [
         "braking distance per the existing EN standard",
         "no track infrastructure changes",
         "device of record: freight locomotive wheelset"],
     "split": "R138_FRESH"},
    {"problem_id": "r138-fresh-04-hvac-coil-freezing",
     "device": "rooftop HVAC unit (air-cooled condenser)",
     "failure": "condenser coil freezing during shoulder-season "
                "low-load nights, cracking the refrigerant circuit "
                "and losing charge",
     "failure_mode": "low-load condenser coil freezing",
     "constraint": "no refrigerant change permitted (existing "
                   "charge inventory); unit downtime under 2 hours "
                   "per intervention",
     "domain": "building-services",
     "question": "What engineering change, intervention, or design "
                 "would prevent or mitigate the stated failure?",
     "user_variables": [
         "no refrigerant change permitted",
         "unit downtime under 2 hours per intervention",
         "device of record: rooftop HVAC air-cooled condenser"],
     "split": "R138_FRESH"},
    {"problem_id": "r138-fresh-05-pipeline-gel-plugging",
     "device": "subsea multiphase production pipeline",
     "failure": "waxy crude gel formation during a 3-day shutdown "
                "plugs the 8-inch flowline; restart pressure exceeds "
                "the MAOP",
     "failure_mode": "wax gel plugging on restart",
     "constraint": "no chemical injection skid exists; the restart "
                   "must not exceed the pipeline MAOP",
     "domain": "subsea-oil-gas",
     "question": "What engineering change, intervention, or design "
                 "would prevent or mitigate the stated failure?",
     "user_variables": [
         "no chemical injection skid",
         "restart pressure under the MAOP",
         "device of record: 8-inch subsea multiphase flowline"],
     "split": "R138_FRESH"},
]


def main() -> int:
    from r7_queue_runner import _load_key_vault
    _load_key_vault()
    from discovery_fabric.engine.run import EngineRun
    from r138_run_extractor import extract_run

    n = int(sys.argv[1]) if len(sys.argv) > 1 else len(FRESH)
    summary = []
    for prob in FRESH[:n]:
        pid = prob["problem_id"]
        outfile = OUT / f"{pid}.json"
        if outfile.exists():  # byte-resume
            summary.append(json.loads(outfile.read_text()))
            print(f"{pid}: resumed from the committed record")
            continue
        out_dir = OUT / pid
        out_dir.mkdir(exist_ok=True)
        t0 = time.monotonic()
        print(f"=== R138 LIVE RUN {pid} ...", flush=True)
        try:
            run = EngineRun(
                dict(prob), str(out_dir),
                run_id=f"r138-{pid}",
                package_registry_path=str(
                    out_dir / "PACKAGE_ID_REGISTRY.json"),
                with_package=False, resume=False)
            manifest = run.run()
            wall = time.monotonic() - t0
            rec = extract_run(out_dir)
            rec["wall_s"] = round(wall, 1)
            rec["final_status"] = (
                manifest.get("final_status")
                if isinstance(manifest, dict) else None)
        except Exception as e:  # noqa: BLE001
            wall = time.monotonic() - t0
            rec = {"run_dir": str(out_dir), "wall_s": round(wall, 1),
                   "RUN_ERROR": f"{type(e).__name__}: {e}"[:300]}
        outfile.write_text(json.dumps(rec, indent=1) + "\n")
        ta = rec.get("transport_attribution") or {}
        print(f"    -> {rec.get('final_status') or rec.get('RUN_ERROR', '')}"
              f" in {rec['wall_s']}s | served by {ta.get('mechanism_space_providers')}"
              f" {ta.get('mechanism_space_models')}"
              f" | grounded {rec.get('grounded_candidates', {}).get('value')}"
              f" admissible {rec.get('admissible_survivors', {}).get('value')}",
              flush=True)
        summary.append(rec)
    # the acceptance roll-up
    agnes_served = 0
    for r in summary:
        ta = r.get("transport_attribution") or {}
        if "agnes" in (ta.get("mechanism_space_providers") or []):
            agnes_served += 1
    roll = {
        "record": "R138_FRESH_RUNS/1.0.0",
        "claim": "c-0219",
        "at": "2026-11-23 (sandbox clock)",
        "n_problems": len(summary),
        "agnes_serving_runs": agnes_served,
        "agnes_acceptance": (
            "MET — agnes is the actual serving provider"
            if agnes_served == len(summary) else
            f"PARTIAL/NOT MET — agnes served {agnes_served}/{len(summary)};"
            " every alternate-provider run is recorded with its typed "
            "substitution (never relabeled as Agnes)"),
        "per_run": [
            {"pid": r.get("run_dir", "").rsplit("/", 1)[-1],
             "status": r.get("final_status") or r.get("RUN_ERROR"),
             "grounded": r.get("grounded_candidates", {}).get("value"),
             "admissible": r.get("admissible_survivors", {}).get("value"),
             "ungrounded_retained": r.get("ungrounded_hypotheses",
                                          {}).get("value"),
             "distinct": r.get("distinct_mechanisms", {}).get("value"),
             "providers": r.get("transport_attribution", {}).get(
                 "mechanism_space_providers")}
            for r in summary],
        "no_score_claims": True,
    }
    (OUT / "SUMMARY.json").write_text(json.dumps(roll, indent=1) + "\n")
    print(json.dumps(roll["per_run"], indent=1))
    print("agnes serving:", agnes_served, "/", len(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

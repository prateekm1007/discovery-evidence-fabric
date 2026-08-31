"""COLLISION REPLAY MEASUREMENT — CEO directive 2026-08-31 (R376).

> "Measure the change using the existing candidate-quality instrument.
>  Do not invent a new success metric that makes the numbers look
>  better."
> "Run this on difficult non-medical and medical cases and compare
>  before/after Q2 and Q3."

CONTROLLED COMPARISON (single variable):
  BEFORE = the frozen R375 survey (TOSCANINI/INVENTION_CHAIN_QUALITY_
           SURVEY.json) — same 53 runs, OLD collision search
  AFTER  = the SAME candidates (same mechanism maps, same interventions,
           read from each run's own artifacts) with the NEW R376
           mechanism-centered collision re-run LIVE

The candidate is held constant; only the prior-art search changes.
Replayed specs are written to TOSCANINI/COLLISION_REPLAY/ — production
run directories are NEVER touched (Art. IX). The instrument
(discovery_fabric/benchmark/candidate_quality.py) is byte-identical
(pinned by test). Q1/Q4/Q5 must measure identically on the replayed
spec because only the prior-art fields are replaced — they act as an
internal control that the replay is faithful.

LLM-free: the collision stage is search + adjudication only.

Reproduction:
    PYTHONPATH=. python3 scripts/collision_replay_measurement.py
    PYTHONPATH=. python3 scripts/collision_replay_measurement.py --runs t6_energy_ev_thermal_runaway,t6_medical_infusion_occlusion
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from discovery_fabric.benchmark import candidate_quality as cq  # noqa: E402
from discovery_fabric.prior_art_v2 import collision_resolution as cr  # noqa: E402

SURVEY = REPO / "TOSCANINI" / "INVENTION_CHAIN_QUALITY_SURVEY.json"
REPLAY_DIR = REPO / "TOSCANINI" / "COLLISION_REPLAY"


def final_candidate_of(run_dir: Path) -> Dict[str, Any]:
    """The FINAL candidate the run produced — the thing that SHOULD have
    been differentiated. For grid-candidate runs the canonical
    INVENTION_SPECIFICATION.json IS the selected grid candidate (its
    intervention may differ from the naive envelope's mechanism map);
    the spec's own mechanism + intervention are the honest source."""
    spec = json.loads(
        (run_dir / "INVENTION_SPECIFICATION.json").read_text())
    problem = json.loads((run_dir / "problem.json").read_text())
    mech = (spec.get("mechanism") or {}).get("value") or {}
    df = (spec.get("distinguishing_features") or {}).get("value") or {}
    return {
        "mechanism_map": {
            "intervention": df.get("intervention")
                            or mech.get("intervention", ""),
            "mechanism": mech.get("mechanism", ""),
            "expected_effect": mech.get("expected_effect", ""),
        },
        "problem": problem,
        "spec": spec,
    }


def replay_spec(spec: Dict[str, Any], collision: Dict[str, Any]
                ) -> Dict[str, Any]:
    """Copy the spec, replacing ONLY the prior-art-derived fields with
    the replayed collision. Everything else is passed through — Q1/Q4/Q5
    are the internal control."""
    out = json.loads(json.dumps(spec))  # deep copy
    resolution = collision["differentiation_resolution"]
    status = resolution["state"]

    nh = (out.get("novelty_hypothesis") or {}).get("value") or {}
    nh["prior_art_status"] = status
    nh["collision_novelty_risk"] = collision["novelty_risk"]
    nh["differentiation_resolution_state"] = status
    out["novelty_hypothesis"]["value"] = nh

    pa = (out.get("prior_art") or {}).get("value") or {}
    pa["status"] = status
    pa["nearest"] = collision["nearest_prior_art"]
    pa["queries"] = [
        {"query_class": s.get("query_class"), "query": s.get("query")}
        for s in collision.get("query_ladder", [])]
    out["prior_art"]["value"] = pa

    df = (out.get("distinguishing_features") or {}).get("value") or {}
    df["vs_nearest_prior_art"] = collision["nearest_prior_art"]
    df["surviving_differentiators"] = resolution.get(
        "surviving_differentiators")
    out["distinguishing_features"]["value"] = df
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="",
                    help="comma-separated run dir names (default: all)")
    ap.add_argument("--retry-failed", action="store_true",
                    help="re-run only runs whose previous replay ended "
                         "UNRESOLVED_INSUFFICIENT_EVIDENCE (source "
                         "failures); merges into the existing report")
    ap.add_argument("--sleep", type=float, default=1.0,
                    help="inter-query sleep (Lens politeness; default 1.0)")
    args = ap.parse_args()

    survey = json.loads(SURVEY.read_text())
    before = {r["run"]: r for r in survey["per_run"]}

    dest = REPO / "TOSCANINI" / "PRIOR_ART_RESOLUTION_BEFORE_AFTER.json"
    existing_rows: Dict[str, Dict[str, Any]] = {}
    if dest.exists():
        try:
            existing_rows = {r["run"]: r for r in
                             json.loads(dest.read_text())["per_run"]}
        except Exception:  # noqa: BLE001 — fresh start on corrupt
            existing_rows = {}

    only = {r.strip() for r in args.runs.split(",") if r.strip()}
    if args.retry_failed:
        only = {name for name, row in existing_rows.items()
                if row.get("q3_status_after") ==
                "UNRESOLVED_INSUFFICIENT_EVIDENCE"}
        print(f"[retry-failed] {len(only)} runs to retry")

    REPLAY_DIR.mkdir(parents=True, exist_ok=True)
    runs_root = REPO / "ENGINE_RUNS"
    rows: List[Dict[str, Any]] = []
    status_counts: Dict[str, int] = {}
    skipped = []

    for run_dir in sorted(runs_root.iterdir()):
        if not run_dir.is_dir():
            continue
        if not (run_dir / "INVENTION_SPECIFICATION.json").exists():
            continue
        if only and run_dir.name not in only:
            continue
        cand = final_candidate_of(run_dir)
        print(f"[replay] {run_dir.name} ...", flush=True)
        try:
            collision = cr.run_collision(
                cand["mechanism_map"], cand["problem"],
                sleep_between=args.sleep)
        except Exception as exc:  # noqa: BLE001 — recorded honestly
            skipped.append({"run": run_dir.name,
                            "error": f"{type(exc).__name__}: {exc}"})
            continue

        # write replayed spec to the REPLAY dir (production untouched)
        out_dir = REPLAY_DIR / run_dir.name
        out_dir.mkdir(parents=True, exist_ok=True)
        rspec = replay_spec(cand["spec"], collision)
        (out_dir / "INVENTION_SPECIFICATION.json").write_text(
            json.dumps(rspec, indent=1))
        dec = run_dir / "DECISIVE_EXPERIMENT.json"
        if dec.exists():
            (out_dir / "DECISIVE_EXPERIMENT.json").write_text(
                dec.read_text())
        (out_dir / "REPLAY_COLLISION.json").write_text(
            json.dumps(collision, indent=1))

        after = cq.measure_run(out_dir)
        before_row = before.get(run_dir.name, {})
        before_dims = before_row  # survey carries per-run summary only
        # re-derive BEFORE Q2/Q3 from the ORIGINAL run dir (instrument,
        # unchanged, on the original artifacts)
        before_meas = cq.measure_run(run_dir)
        bd = {d["dimension"]: d.get("score")
              for d in before_meas.get("dimensions", [])}
        ad = {d["dimension"]: d.get("score")
              for d in after.get("dimensions", [])}
        status = collision["prior_art_status"]
        status_counts[status] = status_counts.get(status, 0) + 1
        rows.append({
            "run": run_dir.name,
            "q2_before": bd.get("Q2_PRIOR_ART_SPECIFICITY"),
            "q2_after": ad.get("Q2_PRIOR_ART_SPECIFICITY"),
            "q3_before": bd.get("Q3_PRIOR_ART_RESOLUTION"),
            "q3_after": ad.get("Q3_PRIOR_ART_RESOLUTION"),
            "q3_status_after": status,
            "q1_before": bd.get("Q1_EVIDENCE_BINDING"),
            "q1_after": ad.get("Q1_EVIDENCE_BINDING"),
            "q4_before": bd.get("Q4_EXPERIMENT_DECISIVENESS"),
            "q4_after": ad.get("Q4_EXPERIMENT_DECISIVENESS"),
            "q5_before": bd.get("Q5_CHAIN_COMPLETENESS"),
            "q5_after": ad.get("Q5_CHAIN_COMPLETENESS"),
            "n_families": collision["differentiation_resolution"][
                "n_families"],
            "n_nearest": len(collision["nearest_prior_art"]),
            "band_before": before_meas.get("band"),
            "band_after": after.get("band"),
        })

    # merge: freshly replayed rows replace existing rows by run name
    merged = dict(existing_rows)
    for row in rows:
        merged[row["run"]] = row
    rows = [merged[k] for k in sorted(merged)]
    status_counts = {}
    for r in rows:
        s = r.get("q3_status_after")
        if s:
            status_counts[s] = status_counts.get(s, 0) + 1

    def _avg(rows_, key):
        vals = [r[key] for r in rows_
                if isinstance(r.get(key), (int, float))]
        return round(sum(vals) / len(vals), 3) if vals else None

    report = {
        "artifact": "COLLISION_REPLAY_BEFORE_AFTER",
        "directive": "CEO 2026-08-31 — prior-art differentiation + "
                     "resolution; before/after Q2/Q3 with the UNCHANGED "
                     "instrument",
        "design": ("controlled single-variable replay: same candidates "
                   "(same mechanism maps), new mechanism-centered "
                   "collision; production run dirs untouched (Art. IX); "
                   "instrument byte-identical (pinned by test)"),
        "n_runs_replayed": len(rows),
        "n_runs_skipped_error": len(skipped),
        "skipped": skipped,
        "resolution_state_distribution_after": status_counts,
        "pooled": {
            "Q2_PRIOR_ART_SPECIFICITY": {
                "before": _avg(rows, "q2_before"),
                "after": _avg(rows, "q2_after")},
            "Q3_PRIOR_ART_RESOLUTION": {
                "before": _avg(rows, "q3_before"),
                "after": _avg(rows, "q3_after")},
            "internal_controls_unchanged": {
                "Q1": {"before": _avg(rows, "q1_before"),
                       "after": _avg(rows, "q1_after")},
                "Q4": {"before": _avg(rows, "q4_before"),
                       "after": _avg(rows, "q4_after")},
                "Q5": {"before": _avg(rows, "q5_before"),
                       "after": _avg(rows, "q5_after")},
            },
        },
        "per_run": rows,
    }
    dest = REPO / "TOSCANINI" / "PRIOR_ART_RESOLUTION_BEFORE_AFTER.json"
    dest.write_text(json.dumps(report, indent=1))

    print(f"\nreplayed {len(rows)} runs -> {dest}")
    print("\n=== POOLED BEFORE/AFTER (unchanged instrument) ===")
    for dim in ("Q2_PRIOR_ART_SPECIFICITY",
                "Q3_PRIOR_ART_RESOLUTION"):
        b, a = report["pooled"][dim]["before"], report["pooled"][dim]["after"]
        print(f"  {dim:28s} {b}  ->  {a}")
    print("\n=== RESOLUTION STATE DISTRIBUTION (after) ===")
    for s, n in sorted(status_counts.items(), key=lambda kv: -kv[1]):
        print(f"  {s:38s} {n}")
    print("\n=== INTERNAL CONTROLS (must be unchanged) ===")
    for k, v in report["pooled"]["internal_controls_unchanged"].items():
        print(f"  {k}: {v['before']} -> {v['after']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

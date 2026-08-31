"""R377 Task 8 — CONTROLLED REPLAY: six fresh-domain survivors with the
R377 collision core + fixed experiment selector.

BEFORE = the frozen artifacts in ENGINE_RUNS/ (R376 collision, R376
         selector) — measured by BOTH instruments in
         TOSCANINI/INVENTION_QUALITY_BASELINE_R377.json
AFTER  = the SAME candidates (same mechanism maps, same interventions,
         same killer-experiment options, same NBA actions — read from
         each run's own artifacts) with the R377 collision re-run LIVE
         and the decisive experiment re-selected by the fixed selector

Single-variable discipline: the CANDIDATE is held constant; only the
prior-art reasoning (search formulation, adjudication precision,
evidence depth) and the experiment selection change. The Q instrument
is the FROZEN one (hash-pinned); the I instrument is the new R377 one.
Production run directories are NEVER touched (Art. IX).

Reproduction:
    PYTHONPATH=. python3 scripts/r377_replay_measurement.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from discovery_fabric.benchmark import candidate_quality as cq  # noqa: E402
from discovery_fabric.benchmark import invention_quality as iq  # noqa: E402
from discovery_fabric.prior_art_v2 import collision_resolution as cr  # noqa: E402
from scripts.collision_replay_measurement import (  # noqa: E402
    final_candidate_of, replay_spec)

SURVIVOR_RUNS = [
    "t6_medical_infusion_occlusion",
    "t6_aerospace_battery_thermal_event",
    "t6_energy_ev_thermal_runaway",
    "t6_industrial_rolling_stock_equipment_failure",
    "t6_materials_rail_steel_fatigue",
    "t6_electronics_li_battery_product_fire",
]
REPLAY_DIR = REPO / "TOSCANINI" / "R377_REPLAY"


def _reselect(run_dir: Path) -> Dict[str, Any]:
    """Deterministic re-selection with the fixed policy."""
    ke_env = json.loads(
        (run_dir / "envelope_KILLER_EXPERIMENT.json").read_text())
    ke = (ke_env.get("killer_experiment") or ke_env.get("value")
          or ke_env)
    nba_env = json.loads(
        (run_dir / "envelope_NEXT_BEST_ACTION.json").read_text())
    nba = (nba_env.get("next_best_action") or nba_env.get("value")
           or nba_env)

    from discovery_fabric.engine.experiment_selector import _is_experiment
    shortlist = []
    excluded = []
    sel_name = ((ke.get("selected") or {}).get("name")
                if isinstance(ke.get("selected"), dict)
                else ke.get("selected"))
    for opt in (ke.get("options_ranked") or []):
        item = {
            "experiment": opt.get("name", ""),
            "source_stage": "KILLER_EXPERIMENT",
            "expected_information_gain": opt.get("eig"),
            "eig_per_cost": opt.get("eig_per_cost"),
            "decision_impact": 0.9,
            "kill_probability": "UNKNOWN (no sourced base rate exists)",
            "cost": ("UNKNOWN absolute cost (options ranked on a "
                     "relative-1.0 scale per bayesian_eig; no sourced "
                     "dollar/time estimate exists — Art. XXV)"),
            "time": "UNKNOWN",
            "dependency": "design article must exist first",
            "is_selected_killer": opt.get("name") == sel_name,
            "basis": "COMPUTED (Bayesian EIG over MODEL_DERIVED priors)"}
        if opt.get("name") == sel_name and ke.get("hypotheses"):
            item["hypotheses"] = ke.get("hypotheses")
        shortlist.append(item)
    for act in (nba.get("ranked_actions") or [])[:5]:
        item = {
            "experiment": act.get("description", ""),
            "source_stage": "NEXT_BEST_ACTION",
            "action_id": act.get("action_id"),
            "expected_information_gain": act.get(
                "expected_information_gain"),
            "score": act.get("score"),
            "decision_impact": act.get("decision_impact"),
            "probability_of_decision_change": act.get(
                "probability_of_decision_change"),
            "kill_probability": "UNKNOWN (no sourced base rate exists)",
            "cost": act.get("cost"),
            "time": "UNKNOWN",
            "dependency": act.get("provider", ""),
            "basis": "COMPUTED (NBA score formula engine-v1)"}
        if _is_experiment(item):
            shortlist.append(item)
        else:
            excluded.append({
                "action_id": act.get("action_id"),
                "description": act.get("description", ""),
                "exclusion_reason": "administrative action (R377)"})

    def _rank(item):
        if item.get("source_stage") == "KILLER_EXPERIMENT":
            return float(item.get("eig_per_cost") or 0.0)
        return float(item.get("score") or 0.0)

    shortlist.sort(key=_rank, reverse=True)
    best = shortlist[0] if shortlist else None
    return {
        "shortlist": shortlist,
        "administrative_actions_excluded": excluded,
        "selected": best,
        "explanation": (
            f"R377 replay re-selection: {best['source_stage']} ranking"
            if best else "no experiment options recorded"),
        "no_invented_values_note": "UNKNOWN preserved (Art. XXV)",
        "timestamp": "replayed",
    }


def main() -> int:
    REPLAY_DIR.mkdir(parents=True, exist_ok=True)
    runs_root = REPO / "ENGINE_RUNS"
    rows: List[Dict[str, Any]] = []
    only = set(sys.argv[1:])

    for name in SURVIVOR_RUNS:
        run_dir = runs_root / name
        if only and name not in only:
            continue
        if not run_dir.exists():
            continue
        # the SURVIVOR's spec (grid candidate), not the naive envelope
        sel = json.loads((run_dir / "SURVIVOR_SELECTION.json").read_text())
        cid = sel["selected"]
        grid_key = cid.split(":")[2] if cid.count(":") >= 2 else None
        spec_path = run_dir / f"INVENTION_SPECIFICATION_grid-{grid_key}.json"
        if not spec_path.exists():
            spec_path = run_dir / "INVENTION_SPECIFICATION.json"
        spec = json.loads(spec_path.read_text())
        problem = json.loads((run_dir / "problem.json").read_text())
        mech = (spec.get("mechanism") or {}).get("value") or {}
        df = (spec.get("distinguishing_features") or {}).get("value") or {}
        cand = {
            "mechanism_map": {
                "intervention": df.get("intervention")
                                or mech.get("intervention", ""),
                "mechanism": mech.get("mechanism", ""),
                "expected_effect": mech.get("expected_effect", ""),
            },
            "problem": problem,
            "spec": spec,
        }
        print(f"[replay] {name} ({grid_key}) ...", flush=True)
        try:
            collision = cr.run_collision(
                cand["mechanism_map"], problem, sleep_between=1.0)
        except Exception as exc:  # noqa: BLE001 — recorded honestly
            rows.append({"run": name, "error": f"{type(exc).__name__}: {exc}"})
            continue

        out_dir = REPLAY_DIR / name
        out_dir.mkdir(parents=True, exist_ok=True)
        rspec = replay_spec(cand["spec"], collision)
        # propagate the new family adjudicated text onto the replayed
        # spec's prior_art so I4 can measure (same fields the live
        # engine now records)
        rspec["prior_art"]["value"][
            "differentiation_resolution"] = collision[
            "differentiation_resolution"]
        (out_dir / "INVENTION_SPECIFICATION.json").write_text(
            json.dumps(rspec, indent=1))
        (out_dir / "REPLAY_COLLISION.json").write_text(
            json.dumps(collision, indent=1))
        # decisive experiment re-selected with the FIXED policy
        dec = _reselect(run_dir)
        (out_dir / "DECISIVE_EXPERIMENT.json").write_text(
            json.dumps(dec, indent=1))

        q_after = cq.measure_run(out_dir)
        i_after = iq.measure_run(out_dir)
        q_before = cq.measure_run(run_dir)
        i_before = iq.measure_run(run_dir)

        qbd = {d["dimension"]: d.get("score")
               for d in q_before.get("dimensions", [])}
        qad = {d["dimension"]: d.get("score")
               for d in q_after.get("dimensions", [])}
        ibd = {d["dimension"]: d.get("score")
               for d in i_before.get("dimensions", [])}
        iad = {d["dimension"]: d.get("score")
               for d in i_after.get("dimensions", [])}
        rows.append({
            "run": name,
            "survivor": cid,
            "q_before": qbd, "q_after": qad,
            "q_average_before": q_before.get("average"),
            "q_average_after": q_after.get("average"),
            "i_before": ibd, "i_after": iad,
            "i_average_before": i_before.get("average"),
            "i_average_after": i_after.get("average"),
            "i_band_after": i_after.get("band"),
            "i_flags_after": i_after.get("flags"),
            "prior_art_status_after":
                collision["prior_art_status"],
            "n_families_after":
                (collision["differentiation_resolution"] or {})
                .get("n_families"),
            "n_term_collisions_demoted": len(
                (collision.get("patent") or {})
                .get("cross_domain_term_collisions") or []),
            "function_query": next(
                (s.get("query") for s in collision.get("query_ladder", [])
                 if s.get("query_class") == "FUNCTION"), None),
            "selected_experiment_after":
                ((dec.get("selected") or {}).get("experiment")),
            "administrative_excluded": [
                e.get("description")
                for e in dec.get("administrative_actions_excluded", [])],
        })
        print(f"    Q {q_before.get('average')} -> {q_after.get('average')}"
              f" | I {i_before.get('average')} -> "
              f"{i_after.get('average')} ({i_after.get('band')}) | "
              f"status {collision['prior_art_status']}")

    report = {
        "artifact": "R377_CONTROLLED_REPLAY",
        "design": ("same candidates, R377 collision core + fixed "
                   "experiment selector; Q instrument FROZEN "
                   "(hash-pinned), I instrument new R377; production "
                   "runs untouched (Art. IX)"),
        "per_run": rows,
    }
    dest = REPO / "TOSCANINI" / "R377_REPLAY_MEASUREMENT.json"
    dest.write_text(json.dumps(report, indent=1, ensure_ascii=False))
    print(f"-> {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

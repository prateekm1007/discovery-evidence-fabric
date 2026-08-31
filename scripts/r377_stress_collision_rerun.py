"""R377 — resolve the stress-run survivors' prior-art positions.

The s7/m7 grid-candidate collisions hit sustained Lens 429 rate-limiting
during the live runs (10/10 query failures per candidate -> recorded
UNRESOLVED_INSUFFICIENT_EVIDENCE — the honest state, never fabricated
absence). This script re-runs the collision for each stress survivor
with long courtesy spacing once the quota window clears, and updates
the run's own prior-art position so the measurement artifact carries
resolved positions where resolution is now possible.

Production discipline (Art. IX): the re-run collision is stored as
R377_COLLISION_RERUN.json alongside the run's own artifacts, and the
run's INVENTION_SPECIFICATION prior-art fields are updated ONLY for
the survivor spec (the run is complete; this is a recorded post-hoc
re-measurement with the R377 collision core, disclosed in the artifact).

Reproduction: PYTHONPATH=. python3 scripts/r377_stress_collision_rerun.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from discovery_fabric.prior_art_v2 import collision_resolution as cr  # noqa: E402

RUNS = [
    "s7_aerospace_satellite_solder_thermal_cycling",
    "m7_manufacturing_titanium_grinding_wheel_loading",
]


def main() -> int:
    summary = []
    for run in RUNS:
        rd = REPO / "ENGINE_RUNS" / run
        sel = json.loads((rd / "SURVIVOR_SELECTION.json").read_text())
        selected = sel.get("selected")
        if not selected:
            summary.append({"run": run, "state": "NO_SURVIVOR"})
            continue
        grid_key = selected.split(":")[2]
        spec_path = rd / f"INVENTION_SPECIFICATION_grid-{grid_key}.json"
        if not spec_path.exists():
            spec_path = rd / "INVENTION_SPECIFICATION.json"
        spec = json.loads(spec_path.read_text())
        problem = json.loads((rd / "problem.json").read_text())
        mv = (spec.get("mechanism") or {}).get("value") or {}
        df = (spec.get("distinguishing_features") or {}).get("value") or {}
        mm = {
            "intervention": df.get("intervention")
                            or mv.get("intervention", ""),
            "mechanism": mv.get("mechanism", ""),
            "expected_effect": mv.get("expected_effect", ""),
        }
        print(f"[rerun] {run} ({grid_key}) ...", flush=True)
        col = cr.run_collision(mm, problem, sleep_between=3.0)
        res = col["differentiation_resolution"]
        print(f"   state={res['state']} families={res.get('n_families')} "
              f"errors={res.get('n_search_errors')}", flush=True)
        (rd / "R377_COLLISION_RERUN.json").write_text(
            json.dumps(col, indent=1))

        # update the survivor spec's prior-art position (recorded, with
        # the rerun provenance — never silent)
        spec["prior_art"]["value"]["status"] = res["state"]
        spec["prior_art"]["value"]["differentiation_resolution"] = res
        spec["prior_art"]["value"]["nearest"] = col["nearest_prior_art"]
        spec["prior_art"]["value"]["queries"] = [
            {"query_class": s.get("query_class"), "query": s.get("query")}
            for s in col.get("query_ladder", [])]
        spec["prior_art"]["value"]["rerun_note"] = (
            "R377 post-hoc collision re-run (original grid-candidate "
            "collision hit Lens rate-limiting -> UNRESOLVED_INSUFFICIENT_"
            "EVIDENCE; rerun with 3s spacing after the quota window; "
            "recorded in R377_COLLISION_RERUN.json)")
        nh = (spec.get("novelty_hypothesis") or {}).get("value") or {}
        nh["prior_art_status"] = res["state"]
        spec["novelty_hypothesis"]["value"] = nh
        dfv = (spec.get("distinguishing_features") or {}).get("value") or {}
        dfv["vs_nearest_prior_art"] = col["nearest_prior_art"]
        dfv["surviving_differentiators"] = res.get(
            "surviving_differentiators")
        spec["distinguishing_features"]["value"] = dfv
        spec_path.write_text(json.dumps(spec, indent=1))

        # also update the canonical INVENTION_SPECIFICATION.json if it is
        # the same candidate (the instruments read that file)
        canon = rd / "INVENTION_SPECIFICATION.json"
        canon_spec = json.loads(canon.read_text())
        canon_ids = ((canon_spec.get("invention_id") or "")
                     if isinstance(canon_spec, dict) else "")
        sel_in_spec = (spec.get("_exploration_candidate") or {})
        same_candidate = (canon_spec.get("_survivor_gate") or {})
        # conservative: copy prior-art fields when the canonical spec's
        # intervention matches the survivor's
        canon_int = ((canon_spec.get("mechanism") or {})
                     .get("value", {}) or {}).get("intervention", "")
        if canon_int == mv.get("intervention", ""):
            canon_spec["prior_art"] = spec["prior_art"]
            canon_spec["novelty_hypothesis"] = spec["novelty_hypothesis"]
            canon_spec["distinguishing_features"] = \
                spec["distinguishing_features"]
            canon.write_text(json.dumps(canon_spec, indent=1))
            copied = True
        else:
            copied = False
        summary.append({
            "run": run, "state": res["state"],
            "n_families": res.get("n_families"),
            "n_errors": res.get("n_search_errors"),
            "canonical_spec_updated": copied})
        time.sleep(5)
    dest = REPO / "TOSCANINI" / "R377_STRESS_COLLISION_RERUN.json"
    dest.write_text(json.dumps(summary, indent=1))
    print(f"-> {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

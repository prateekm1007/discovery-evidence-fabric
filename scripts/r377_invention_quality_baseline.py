"""R377 Task 4 — baseline (BEFORE) measurement of the new
INVENTION-QUALITY instrument on the six fresh-domain survivors and the
full run corpus.

Diagnostic only (Art. XXVI). The frozen Q-instrument
(candidate_quality.py, hash-pinned) is run UNCHANGED alongside for
comparability — this survey reports BOTH instruments' BEFORE state so
the post-improvement re-measurement has a controlled baseline.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from discovery_fabric.benchmark import candidate_quality as cq  # noqa: E402
from discovery_fabric.benchmark import invention_quality as iq  # noqa: E402
from scripts.candidate_quality_survey import domain_family  # noqa: E402

SURVIVOR_RUNS = [
    "t6_medical_infusion_occlusion",
    "t6_aerospace_battery_thermal_event",
    "t6_energy_ev_thermal_runaway",
    "t6_industrial_rolling_stock_equipment_failure",
    "t6_materials_rail_steel_fatigue",
    "t6_electronics_li_battery_product_fire",
]


def measure_corpus() -> dict:
    runs_root = REPO / "ENGINE_RUNS"
    measured = []
    for run_dir in sorted(runs_root.iterdir()):
        if not run_dir.is_dir():
            continue
        if not (run_dir / "INVENTION_SPECIFICATION.json").exists():
            continue
        q = cq.measure_run(run_dir)
        i = iq.measure_run(run_dir)
        measured.append({
            "run": run_dir.name,
            "family": domain_family(run_dir),
            "q_instrument": {
                "average": q.get("average"), "band": q.get("band"),
                "dimensions": [
                    {"d": d["dimension"], "score": d.get("score")}
                    for d in (q.get("dimensions") or [])],
            },
            "i_instrument": {
                "average": i.get("average"), "band": i.get("band"),
                "flags": i.get("flags"),
                "dimensions": [
                    {"d": d["dimension"], "score": d.get("score"),
                     "state": d.get("state")}
                    for d in (i.get("dimensions") or [])],
            },
        })
    return measured


def agg(rows, key_path):
    vals = []
    for r in rows:
        node = r
        for k in key_path:
            node = (node or {}).get(k) if isinstance(node, dict) else None
        if isinstance(node, (int, float)):
            vals.append(node)
    return round(sum(vals) / len(vals), 3) if vals else None


def main() -> int:
    measured = measure_corpus()
    survivors = [m for m in measured if m["run"] in SURVIVOR_RUNS]

    report = {
        "artifact": "INVENTION_QUALITY_BASELINE_R377",
        "directive": "CEO 2026-08-31 — measure the QUALITY OF THE "
                     "INVENTION ITSELF; before/after must stay comparable "
                     "(Q instrument frozen and hash-pinned)",
        "q_instrument": "discovery_fabric/benchmark/candidate_quality.py "
                        "(FROZEN)",
        "i_instrument": "discovery_fabric/benchmark/invention_quality.py "
                        "(NEW R377)",
        "n_runs_measured": len(measured),
        "six_survivors": survivors,
        "six_survivor_aggregates": {
            "q_average": agg(survivors, ["q_instrument", "average"]),
            "i_average": agg(survivors, ["i_instrument", "average"]),
            "i_by_dimension": {
                d: agg(survivors, ["i_instrument", "dimensions"])
                for d in []},  # filled below
        },
        "corpus_aggregates": {
            "q_average": agg(measured, ["q_instrument", "average"]),
            "i_average": agg(measured, ["i_instrument", "average"]),
        },
    }
    # per-dimension aggregates for the six survivors
    dim_agg = {}
    for m in survivors:
        for d in m["i_instrument"]["dimensions"]:
            dim_agg.setdefault(d["d"], []).append(d["score"])
    report["six_survivor_aggregates"]["i_by_dimension"] = {
        k: (round(sum(v) / len(v), 3)
            if all(isinstance(x, (int, float)) for x in v) and v else
            [x for x in v if x is None][:1] or None)
        for k, v in sorted(dim_agg.items())
    }

    out = REPO / "TOSCANINI" / "INVENTION_QUALITY_BASELINE_R377.json"
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False))

    print(f"measured {len(measured)} runs; six survivors:")
    print(f"  Q-instrument (frozen) six-survivor average: "
          f"{report['six_survivor_aggregates']['q_average']}")
    print(f"  I-instrument (new)     six-survivor average: "
          f"{report['six_survivor_aggregates']['i_average']}")
    for k, v in report["six_survivor_aggregates"]["i_by_dimension"].items():
        print(f"    {k:42s} {v}")
    print(f"corpus: Q={report['corpus_aggregates']['q_average']} "
          f"I={report['corpus_aggregates']['i_average']}")
    for m in survivors:
        print(f"  {m['run']:52s} Q={m['q_instrument']['average']} "
              f"I={m['i_instrument']['average']} "
              f"({m['i_instrument']['band']}) "
              f"flags={m['i_instrument']['flags']}")
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

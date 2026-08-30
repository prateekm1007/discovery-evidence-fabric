"""Run the INVENTION_CHAIN quality instrument across engine runs — CEO
directive 2026-08-31 ("compare the quality of surviving candidates, not
just whether the pipeline completes").

Measures every ENGINE_RUNS/* directory that carries an
INVENTION_SPECIFICATION.json, groups by domain family (medical vs
non-medical), and reports the honest aggregate. Diagnostic only (Art.
XXVI): the instrument never feeds kill/promote decisions.

Reproduction: PYTHONPATH=. python3 scripts/candidate_quality_survey.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from discovery_fabric.benchmark import candidate_quality as cq  # noqa: E402

MEDICAL_HINTS = ("medical", "infusion", "osteolysis", "thrombus",
                 "shunt", "catheter", "hydrocephalus", "prosthesis",
                 "hip", "knee", "implant", "ventilator", "pump",
                 "aseptic", "tube_occlusion")


def domain_family(run_dir: Path) -> str:
    name = run_dir.name.lower()
    if any(h in name for h in MEDICAL_HINTS):
        return "medical"
    if any(h in name for h in ("battery", "thermal", "energy", "hydrogen")):
        return "energy"
    if any(h in name for h in ("aerospace",)):
        return "aerospace"
    if any(h in name for h in ("materials", "rail_steel", "steel")):
        return "materials"
    if any(h in name for h in ("industrial", "rolling_stock")):
        return "industrial"
    if any(h in name for h in ("electronics", "product_fire")):
        return "electronics"
    if "toscanini_ui" in name:
        return "ui_unclassified"
    return "other"


def main() -> int:
    runs_root = REPO / "ENGINE_RUNS"
    measured, unmeasurable = [], []
    for run_dir in sorted(runs_root.iterdir()):
        if not run_dir.is_dir():
            continue
        if not (run_dir / "INVENTION_SPECIFICATION.json").exists():
            continue
        result = cq.measure_run(run_dir)
        result["family"] = domain_family(run_dir)
        if result.get("state") == "MEASURED":
            measured.append(result)
        else:
            unmeasurable.append(result)

    families: dict = {}
    for r in measured:
        families.setdefault(r["family"], []).append(r)

    report = {
        "artifact": "INVENTION_CHAIN_QUALITY_SURVEY",
        "directive": "CEO 2026-08-31 — better invention machine evidence: "
                     "measure candidate-chain QUALITY, not pipeline "
                     "completion",
        "instrument": "discovery_fabric/benchmark/candidate_quality.py "
                      "(Art. XXVI builder-measured diagnostic; never wired "
                      "into kill/promote)",
        "bands_declared": ">=0.70 STRONG / 0.40-0.69 ADEQUATE / <0.40 WEAK "
                          "(ENGINEERING judgment, Art. XXVII)",
        "runs_measured": len(measured),
        "runs_without_spec": len(unmeasurable),
        "per_run": [
            {"run": r["run_dir"].split("/")[-1], "family": r["family"],
             "average": r["average"], "band": r["band"],
             "weakest": r["weakest_dimension"]}
            for r in measured],
        "by_family": {},
    }
    print(f"measured {len(measured)} runs "
          f"({len(unmeasurable)} engine-run dirs without a spec)")
    for fam, rows in sorted(families.items()):
        avgs = [r["average"] for r in rows if r["average"] is not None]
        fam_avg = round(sum(avgs) / len(avgs), 3) if avgs else None
        dim_scores: dict = {}
        for r in rows:
            for d in r["dimensions"]:
                if isinstance(d.get("score"), (int, float)):
                    dim_scores.setdefault(d["dimension"], []).append(d["score"])
        dim_avg = {k: round(sum(v) / len(v), 3)
                   for k, v in sorted(dim_scores.items())}
        report["by_family"][fam] = {
            "n_runs": len(rows), "family_average": fam_avg,
            "band": cq.grade_band(fam_avg),
            "dimension_averages": dim_avg,
        }
        print(f"\n=== family {fam:16s} n={len(rows)} "
              f"avg={fam_avg} band={cq.grade_band(fam_avg)}")
        for k, v in dim_avg.items():
            print(f"    {k:32s} {v}")

    out = REPO / "TOSCANINI" / "INVENTION_CHAIN_QUALITY_SURVEY.json"
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False))
    print(f"\n[survey] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

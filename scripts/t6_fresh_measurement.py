"""R376 fresh six-domain end-to-end measurement — save the before/after
artifact for the CEO milestone evidence.

BEFORE: the archived R375 t6 runs (ENGINE_RUNS_ARCHIVE_R376_BEFORE/t6_*)
        measured with the UNCHANGED instrument
AFTER:  fresh full-chain runs (ENGINE_RUNS/t6_*) through the R376
        mechanism-centered collision — synthesis -> collision -> attack
        -> grid (per-candidate collisions) -> specs

Reproduction:
    PYTHONPATH=. python3 scripts/t6_fresh_measurement.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from discovery_fabric.benchmark import candidate_quality as cq  # noqa: E402
from candidate_quality_survey import domain_family  # noqa: E402


def main() -> int:
    before_root = REPO / "ENGINE_RUNS_ARCHIVE_R376_BEFORE"
    after_root = REPO / "ENGINE_RUNS"
    rows = []
    for after_dir in sorted(after_root.glob("t6_*")):
        before_dir = before_root / after_dir.name
        b = cq.measure_run(before_dir) if before_dir.exists() else {}
        a = cq.measure_run(after_dir)
        bd = {d["dimension"]: d.get("score")
              for d in b.get("dimensions", [])}
        ad = {d["dimension"]: d.get("score")
              for d in a.get("dimensions", [])}
        rows.append({
            "run": after_dir.name,
            "family": domain_family(after_dir),
            "q2_before": bd.get("Q2_PRIOR_ART_SPECIFICITY"),
            "q2_after": ad.get("Q2_PRIOR_ART_SPECIFICITY"),
            "q3_before": bd.get("Q3_PRIOR_ART_RESOLUTION"),
            "q3_after": ad.get("Q3_PRIOR_ART_RESOLUTION"),
            "band_before": b.get("band"),
            "band_after": a.get("band"),
            "weakest_after": a.get("weakest_dimension"),
        })

    def avg(key):
        vals = [r[key] for r in rows
                if isinstance(r.get(key), (int, float))]
        return round(sum(vals) / len(vals), 3) if vals else None

    report = {
        "artifact": "T6_FRESH_END_TO_END_BEFORE_AFTER",
        "directive": "CEO 2026-08-31 — 'Run this on difficult non-medical "
                     "and medical cases and compare before/after Q2 and "
                     "Q3' + milestone: 'measured evidence that Toscanini "
                     "can turn evidence into genuinely differentiated "
                     "invention candidates'",
        "design": ("fresh FULL-CHAIN runs (not replay): each domain ran "
                   "synthesis -> mechanism-centered collision -> adversarial "
                   "attack -> exploration grid (per-candidate collisions) "
                   "-> invention specifications; instrument byte-identical "
                   "(pinned by test); before = the archived R375 t6 runs"),
        "n_domains": len(rows),
        "pooled": {
            "Q2_PRIOR_ART_SPECIFICITY": {
                "before": avg("q2_before"), "after": avg("q2_after")},
            "Q3_PRIOR_ART_RESOLUTION": {
                "before": avg("q3_before"), "after": avg("q3_after")},
        },
        "bands_after": [r["band_after"] for r in rows],
        "per_domain": rows,
    }
    dest = REPO / "TOSCANINI" / "T6_FRESH_END_TO_END_BEFORE_AFTER.json"
    dest.write_text(json.dumps(report, indent=1))
    print(f"n={len(rows)} -> {dest}")
    print(f"Q2: {avg('q2_before')} -> {avg('q2_after')}")
    print(f"Q3: {avg('q3_before')} -> {avg('q3_after')}")
    print(f"bands: {report['bands_after']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

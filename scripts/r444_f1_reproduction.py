#!/usr/bin/env python3
"""scripts/r444_f1_reproduction.py — reproduce Coder 2's F1 finding
(R444/R444_C2_ROUND_RECORD.json coder1_feedback_filed) against THIS
round's fresh battery runs: run the invention bridge (geometry ->
package compile) over an EVOLVED battery survivor and record the exact
typed outcome (package built vs PACKAGE_BUILD_BLOCKED and why).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

OUT = REPO_ROOT / "R444" / "F1_REPRODUCTION.json"

RUN = REPO_ROOT / "R401-WC2" / "BENCHMARK" / "RUNS" / "r401" / \
    "bench-p03-phe-biofouling"


def main() -> int:
    run_result = json.loads((RUN / "final_state.json").read_text())
    # the bridge expects the run_result envelope shape used in
    # production: final_state carries the essentials; the lineage's
    # final_state is the same record the worker passes
    lineage = json.loads((RUN / "INVENTION_LINEAGE.json").read_text())
    run_result = lineage.get("final_state") or run_result

    from discovery_fabric.engine.invention_bridge.bridge import bridge
    out = bridge(run_result, None, str(RUN),
                 build_renders=False,  # reproduce F1: package path only
                 run_id="r444-f1-repro")

    package_out = out.get("package_out") or {}
    rec = {
        "reproduction_of": ("R444/R444_C2_ROUND_RECORD.json "
                            "coder1_feedback_filed.f1_package_gate_"
                            "blocks_every_fresh_package"),
        "run": str(RUN.relative_to(REPO_ROOT)),
        "package_state": package_out.get("state"),
        "package_blocked": package_out.get("blocked"),
        "block_reason": package_out.get("block_reason")
        or package_out.get("reason"),
        "violations": package_out.get("violations"),
        "zip_path": package_out.get("zip_path"),
        "visualizability_class": (out.get("visualizability") or {}).get(
            "visualizability_class"),
        "bridge_steps": [f"{s.get('step') or s.get('name')}:{s.get('status')}"
                         for s in ((out.get("report") or {})
                                   .get("steps") or [])],
    }
    # the geometry quality gate record, when present
    geo = out.get("geometry_out") or {}
    gqg = geo.get("quality_gate") or geo.get("gate") or None
    if gqg:
        rec["geometry_gate"] = {
            k: gqg.get(k) for k in ("verdict", "failed_checks",
                                    "domain_family", "checks")}

    OUT.write_text(json.dumps(rec, indent=1, default=str))
    print(json.dumps({k: rec[k] for k in (
        "package_state", "package_blocked", "block_reason",
        "zip_path", "visualizability_class")}, indent=1, default=str))
    print(f"full record -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

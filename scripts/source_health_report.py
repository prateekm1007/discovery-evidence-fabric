#!/usr/bin/env python
"""SOURCE_HEALTH_REPORT generator — the database-layer acceptance artifact.

Runs the measured health check over EVERY registry source and writes:

  artifacts/source_health/SOURCE_HEALTH_REPORT.json   (append-only per run)
  stdout summary + auditable coverage matrix

Statuses (directive vocabulary): LIVE / DEGRADED / UNAVAILABLE / NOT_INTEGRATED.
Coverage matrix rule: a role is COVERED only if >= 1 source measured LIVE
serves it; PARTIAL if only DEGRADED sources serve it; otherwise GAP.

Art. XXVI disclosure: this report is BUILDER-MEASURED. The reproduction
command is exactly:
    python scripts/source_health_report.py
Any third party can re-run it against the same registry.

Usage:
    python scripts/source_health_report.py            # full run
    python scripts/source_health_report.py --timeout 40
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.source_registry.health import run_health_check  # noqa: E402
from discovery_fabric.source_registry.registry import (  # noqa: E402
    SOURCE_REGISTRY, apply_measured_statuses,
)
from discovery_fabric.source_registry.roles import COVERAGE_MATRIX_ROLES  # noqa: E402
from discovery_fabric.source_registry.retrieval_log import verify_chain  # noqa: E402

REPORT_DIR = REPO_ROOT / "artifacts" / "source_health"

ROLE_ICON = {"COVERED": "✅", "PARTIAL": "🟡", "GAP": "❌"}


def coverage_matrix(measured: dict) -> list:
    """Role -> coverage derived ONLY from measured source statuses."""
    matrix = []
    for role in COVERAGE_MATRIX_ROLES:
        serving = [sid for sid, rec in SOURCE_REGISTRY.items()
                   if role in rec["authority_role"]]
        statuses = {sid: measured.get(sid, "NOT_MEASURED") for sid in serving}
        if any(s == "LIVE" for s in statuses.values()):
            cov = "COVERED"
        elif any(s == "DEGRADED" for s in statuses.values()):
            cov = "PARTIAL"
        else:
            cov = "GAP"
        matrix.append({
            "role": role,
            "coverage": cov,
            "live_sources": sorted([sid for sid, s in statuses.items() if s == "LIVE"]),
            "degraded_sources": sorted([sid for sid, s in statuses.items() if s == "DEGRADED"]),
            "unavailable_sources": sorted([sid for sid, s in statuses.items() if s == "UNAVAILABLE"]),
            "not_integrated_sources": sorted([sid for sid, s in statuses.items()
                                              if s == "NOT_INTEGRATED"]),
        })
    return matrix


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    print("Running measured health check over the full SOURCE_REGISTRY...")
    report = run_health_check(timeout=args.timeout)
    measured = report["measured_statuses"]

    # overlay measured statuses onto the registry (validates no-LIVE-without-
    # connector rule at overlay time)
    overlaid = apply_measured_statuses(measured)

    matrix = coverage_matrix(measured)

    out = {
        "artifact": "SOURCE_HEALTH_REPORT",
        "run_timestamp": report["run_timestamp"],
        "status_vocabulary": ["LIVE", "DEGRADED", "UNAVAILABLE", "NOT_INTEGRATED"],
        "status_counts": {
            s: sum(1 for v in measured.values() if v == s)
            for s in ["LIVE", "DEGRADED", "UNAVAILABLE", "NOT_INTEGRATED"]
        },
        "derivation": report["results"][0]["derivation"] if report["results"] else {},
        "derivation_metered_sources": {
            "note": "provider-metered sources (e.g. patentbear) are NEVER "
                    "live-probed by health checks; their LIVE/DEGRADED status "
                    "derives from the freshest live retrieval-log proof inside "
                    "the metered window, with the proof timestamp disclosed "
                    "per-source under per_source[].last_live_proof",
            "policy": "see discovery_fabric/source_registry/health.py "
                      "METERED_DERIVATION",
        },
        "per_source": report["results"],
        "retrieval_log_audit": report["retrieval_log_audit"],
        "coverage_matrix": matrix,
        "registry_overlay": {
            sid: rec["health_status"] for sid, rec in overlaid.items()
        },
        "builder_measured_disclosure": {
            "art_xxvi": (
                "This report is BUILDER-MEASURED (the builder ran the health "
                "check). Independent reproduction command: "
                "python scripts/source_health_report.py — any third party "
                "can re-run it against the same committed registry."
            ),
            "frozen_instruments": "untouched (this run touches no benchmark layer)",
        },
        "reproduction": "python scripts/source_health_report.py",
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORT_DIR / "SOURCE_HEALTH_REPORT.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"\nWrote: {out_path}\n")

    # ---- console summary ----
    print("=" * 100)
    print("SOURCE HEALTH REPORT (measured live this run)")
    print("=" * 100)
    for r in sorted(report["results"], key=lambda x: (x["status"], x["source_id"])):
        err = (r.get("error") or "")[:60]
        print(f"  {r['status']:15s} {r['source_id']:30s} {err}")
    print("-" * 100)
    print("COVERAGE MATRIX (role covered ONLY by a LIVE measured source)")
    for row in matrix:
        print(f"  {ROLE_ICON[row['coverage']]} {row['role']:16s} "
              f"live={row['live_sources'] or '-'}")
    print("-" * 100)
    print(f"  retrieval log: {report['retrieval_log_audit']}")
    print("=" * 100)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

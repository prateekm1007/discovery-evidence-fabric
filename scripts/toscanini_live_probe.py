#!/usr/bin/env python
"""Targeted live probe for the Toscanini database coverage audit (R377).

Re-measures ONLY the sources whose 2026-08-29 health status was not LIVE,
to report TODAY's true state (Art. XV / Art. XXI: measured, not assumed).

Does NOT modify the registry or any artifact — prints results only.
Appends to the standard retrieval log via the normal connector path
(that is the designed custody mechanism, append-only).
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path("/home/z/my-project/discovery-evidence-fabric")
sys.path.insert(0, str(REPO))

from discovery_fabric.source_registry.health import check_source  # noqa: E402
from discovery_fabric.source_registry.registry import SOURCE_REGISTRY  # noqa: E402

TARGETS = [
    "europepmc",       # UNAVAILABLE (normalization flag) — most-used source (366 log entries)
    "openalex",        # DEGRADED (429 budget at last probe)
    "semantic_scholar",  # DEGRADED
    "epo_ops",         # UNAVAILABLE
    "uspto_odp",       # UNAVAILABLE
    "materials_project",  # UNAVAILABLE (ASN block)
    "patsnap_eureka",  # UNAVAILABLE
    "google_bigquery_patents",  # UNAVAILABLE
]


def main() -> None:
    print(f"{'source':28s} {'status':14s} detail")
    print("-" * 78)
    for sid in TARGETS:
        try:
            res = check_source(sid, timeout=30)
        except Exception as exc:  # noqa: BLE001
            print(f"{sid:28s} RAISED         {type(exc).__name__}: {str(exc)[:90]}")
            continue
        chain = res.get("chain", {})
        failed = [k for k, v in chain.items() if v is False]
        print(f"{sid:28s} {res.get('status','?'):14s} failed_steps={failed or 'none'}")


if __name__ == "__main__":
    main()

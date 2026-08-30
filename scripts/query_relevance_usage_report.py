#!/usr/bin/env python3
"""Report the per-source relevance-adjudication USAGE aggregation.

Reproduction: python3 scripts/query_relevance_usage_report.py

Reads the append-only custody log
(artifacts/source_health/relevance_adjudication_log.jsonl), verifies its
hash chain, aggregates per-source usage measurements, and writes
TOSCANINI/QUERY_RELEVANCE_USAGE.json (committed instrument output —
builder-measured per Art. XXVI; this script IS the reproduction command).

This is the aggregation side of maturity-model §6.1 ('persist per-source
relevance-adjudication aggregation in the custody log → then measure it').
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from discovery_fabric.source_registry import relevance_aggregation  # noqa: E402

OUT_PATH = REPO / "TOSCANINI" / "QUERY_RELEVANCE_USAGE.json"


def main() -> int:
    report = relevance_aggregation.aggregate_usage()
    report["directive"] = (
        "CEO 2026-08-30 audit — close the QUERY_RELEVANCE aggregation gap: "
        "per-source relevance-adjudication aggregation persisted in custody "
        "and measured from real engine usage"
    )
    report["reproduction"] = "python3 scripts/query_relevance_usage_report.py"
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(report, indent=1, ensure_ascii=False))

    chain = report["chain_valid"]
    n_src = len(report["sources"])
    banded = sum(1 for s in report["sources"].values()
                 if isinstance(s.get("usage_band"), int))
    flagged = [sid for sid, s in report["sources"].items()
               if s.get("zero_relevant_ok_status", {}).get("flagged")]
    print(f"[usage] chain_valid={chain} entries={report['log_entries']} "
          f"sources={n_src} banded={banded} "
          f"zero-relevant-flagged={flagged or 'none'}")
    print(f"[usage] wrote {OUT_PATH}")
    if not chain:
        print("[usage] CHAIN INVALID — refuse to treat as measurement (Art. XI)")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

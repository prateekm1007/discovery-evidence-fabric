#!/usr/bin/env python3
"""R535 §12 bookkeeping correction (append-only, Art. XI).

The R535 completion narrative said the battery used "6 vehicles."
The sealed R535/BATTERY_PROBLEMS.json manifest actually scored
problems from 5 distinct vehicles; the 6th (nissan|altima|2022)
appeared only in the raw-fetch acquisition set (its class pairs
yielded no qualifying THIRD complaint, so it contributed no scored
problem).

This script:
  1. does NOT rewrite the sealed manifest (Art. XI);
  2. re-derives the scored-vehicle count mechanically from the
     manifest;
  3. writes an append-only correction artifact that records the
     discrepancy and the machine-verified truth.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "R535" / "BATTERY_PROBLEMS.json"
OUT = REPO / "R535" / "R535_VEHICLE_COUNT_CORRECTION.json"


def main() -> int:
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    scored_vehicles = sorted(
        {p.get("vehicle") for p in man.get("problems", [])
         if p.get("vehicle")})
    raw_vehicles = sorted((man.get("raw_fetches") or {}).keys())
    raw_only = [v for v in raw_vehicles if v not in scored_vehicles]

    rec = {
        "artifact": "R535_VEHICLE_COUNT_CORRECTION/1.0",
        "round": "R535",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
        "reviewer_provenance": "AI_REVIEW",
        "constitution_ref": ("Art. XI: historical evidence is "
                             "preserved, not silently rewritten; "
                             "corrections are appended and "
                             "explicitly labelled"),
        "correction_type": "APPEND_ONLY_BOOKKEEPING",
        "reported_summary": "6 vehicles (the R535 completion "
                            "narrative)",
        "actual_scored_distinct_vehicles": scored_vehicles,
        "actual_scored_distinct_vehicle_count":
            len(scored_vehicles),
        "raw_fetch_vehicles": raw_vehicles,
        "raw_fetch_vehicle_count": len(raw_vehicles),
        "raw_only_not_scored": raw_only,
        "explanation": (
            "The raw-fetch acquisition set contained 6 vehicle "
            "queries.  The scored problem set (8 problems) draws "
            "from 5 of those vehicles; "
            + ", ".join(raw_only or ["(none)"])
            + " yielded no qualifying third complaint under the "
            "frozen mechanical filters, so it contributed no "
            "scored problem.  The sealed manifest "
            "R535/BATTERY_PROBLEMS.json is NOT modified — this "
            "correction records the discrepancy and is the "
            "authoritative statement of the scored-vehicle count."),
        "sealed_manifest_unmodified": True,
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False)
                   + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"scored distinct vehicles: {len(scored_vehicles)} "
          f"({scored_vehicles})")
    print(f"raw-only (not scored): {raw_only}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

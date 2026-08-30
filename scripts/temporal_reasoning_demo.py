#!/usr/bin/env python3
"""Live verification of the temporal-reasoning layer on REAL records.

Queries two independent live sources (EuropePMC + Crossref) for the same
known DOI, plus ClinicalTrials.gov for a real trial's status fields, then
runs: entity_resolution -> detect_contradictions -> order_contradictions
-> entity_timeline -> supersession_view.

Output: TOSCANINI/TEMPORAL_REASONING_DEMO.json (committed instrument
output — builder-measured per Art. XXVI; this script IS the reproduction
command).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from discovery_fabric.source_registry.connectors.scientific import (  # noqa: E402
    CrossrefConnector, EuropePmcConnector,
)
from discovery_fabric.source_registry.connectors.clinicaltrials import (  # noqa: E402
    ClinicalTrialsConnector,
)
from discovery_fabric.source_registry.entity_resolution import (  # noqa: E402
    detect_contradictions,
)
from discovery_fabric.source_registry.temporal_reasoning import (  # noqa: E402
    STATE_LIKE_FIELDS, entity_timeline, order_contradictions,
    supersession_view,
)

OUT = REPO / "TOSCANINI" / "TEMPORAL_REASONING_DEMO.json"

# anchor DOI used by the earlier CROSS_SOURCE_DEMO (known resolvable in
# both EuropePMC and Crossref)
DOI = "10.1007/s00701-026-06952-x"
TRIAL_QUERY = "hydrocephalus shunt"


def main() -> int:
    records = []
    sources_used = {}

    for name, cls, query in (
        ("europepmc", EuropePmcConnector, DOI),
        ("crossref", CrossrefConnector, DOI),
        ("clinicaltrials_gov", ClinicalTrialsConnector, TRIAL_QUERY),
    ):
        res = cls().search(query, timeout=30)
        recs = [r.to_dict() for r in res.records]
        sources_used[name] = {"status": res.status, "records": len(recs)}
        records.extend(recs)
        print(f"[temporal] {name:20s} {res.status:8s} {len(recs)} records")

    cons = detect_contradictions(records)
    ordered = order_contradictions(cons, records)
    tl = entity_timeline(records)
    sv = supersession_view(records, fields=STATE_LIKE_FIELDS)

    out = {
        "artifact": "TEMPORAL_REASONING_DEMO",
        "directive": "CEO 2026-08-30 #6 — strengthen cross-source identity, "
                     "contradiction, negative evidence, and temporal "
                     "reasoning",
        "sources_used": sources_used,
        "records_total": len(records),
        "contradictions_surfaced": len(cons),
        "contradictions_temporally_ordered": sum(
            1 for c in ordered
            if c.get("temporal_order", {}).get("kind") == "ORDERED"),
        "state_progression_patterns": sum(
            1 for c in ordered if "temporal_pattern" in c),
        "contradictions": ordered,
        "timelines": tl,
        "supersession": sv,
        "reproduction": "python3 scripts/temporal_reasoning_demo.py",
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"[temporal] contradictions={len(cons)} "
          f"ordered={out['contradictions_temporally_ordered']} "
          f"state_patterns={out['state_progression_patterns']}")
    print(f"[temporal] entities with timelines={len(tl['entities'])} "
          f"undated_total={tl['undated_total']}")
    print(f"[temporal] wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

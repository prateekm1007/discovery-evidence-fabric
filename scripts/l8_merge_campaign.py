#!/usr/bin/env python
"""Merge the three L8 campaign chunk reports into the authoritative
CAMPAIGN_REPORT.json (the campaign was run in chunks for timeout
discipline; this merge is deterministic and discloses its sources).

    python scripts/l8_merge_campaign.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "discovery_campaigns" / "CAMPAIGN_L8_2026-08-29"


def main() -> int:
    chunks = []
    for name in ("CHUNK_R1.json", "CHUNK_R2.json", "CHUNK_R3.json"):
        p = OUT_DIR / name
        if not p.exists():
            print(f"missing chunk: {p}", file=sys.stderr)
            return 1
        chunks.append(json.loads(p.read_text()))

    results = []
    kills = []
    survivors = []
    territories = []
    engine_decisions = []
    for c in chunks:
        results.extend(c.get("results", []))
        kills.extend(c.get("cemetery_entries_directive_format", []))
        survivors.extend(c.get("dossier_candidates_ranked", []))
        territories.extend(c.get("territories", []))
        engine_decisions.extend(c.get("engine_decisions", []))

    survivors.sort(key=lambda s: (
        -s["survivor_score"]["transfer_domains"],
        -(s["survivor_score"]["root_cause_evidence"]
          + s["survivor_score"]["narrative_evidence"]),
        -s["survivor_score"]["problem_signal_records"]))

    report = {
        "artifact": "L8_DISCOVERY_CAMPAIGN_REPORT",
        "campaign": "15-territory medical-device campaign (CEO lifecycle "
                    "directive 2026-08-29)",
        "merge_disclosure": "Campaign executed in three chunk runs with "
                            "the CORRECTED operator (query-ladder fix: "
                            "retrieve_failures now broadens brand-name "
                            "field queries to full-text phrase queries "
                            "before concluding PROBLEM_NOT_DOCUMENTED). "
                            "Chunks R1 (01-04,06), R2 (07,08,11,15), "
                            "R3 (05,09-14) remain in this directory. The "
                            "pre-correction run is preserved in "
                            "CHUNK_1/2/3.json with its 6 kills "
                            "re-measured: 3 territories revived (09 "
                            "venous filter, 12 intracranial stent, 14 "
                            "limb prosthesis), 3 stayed killed (05, 10, "
                            "13). Corrected kills are canonical in "
                            "MECHANISM_CEMETERY (CE-804..806).",
        "territories": territories,
        "engine_decisions": engine_decisions,
        "summary": {
            "territories_run": len(results),
            "blocked": sum(1 for r in results if r["engine_decision"]
                           == "BLOCKED_PROVIDER_FAILURE"),
            "killed_territories": sum(1 for r in results
                                      if r["engine_decision"] == "KILLED"),
            "candidates_killed": len(kills),
            "survivors": len(survivors),
        },
        "cemetery_entries_directive_format": kills,
        "dossier_candidates_ranked": survivors,
        "dossier_promotion_note": chunks[0]["dossier_promotion_note"],
        "builder_measured_disclosure": {
            "art_xxvi": "BUILDER-MEASURED. Reproduction (chunks): "
                        "python scripts/l8_campaign.py --only 01,02,03,04,06 "
                        "/ 07,08,11,15 / 05,09,10,12,13,14, then python "
                        "scripts/l8_merge_campaign.py",
            "reproduction": "python scripts/l8_campaign.py && "
                            "python scripts/l8_merge_campaign.py",
        },
        "results": results,
    }
    out = OUT_DIR / "CAMPAIGN_REPORT.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    print(f"merged: {len(results)} territories, {len(kills)} kills, "
          f"{len(survivors)} survivors")
    print("\nENGINE DECISIONS:")
    for d in engine_decisions:
        print(f"  [{d['territory_id']}] {d['device_query']:32s} "
              f"{d['decision']:24s} kills={d['kills']} survivors={d['survivors']}")
    print("\nTOP 5 DOSSIER CANDIDATES (ranked, NOT dossiered):")
    for s in survivors[:5]:
        print(f"  {s['territory_id']} {s['device_query']:30s} "
              f"{s['principle']:28s} transfer={len(s['transfer_domains'])} "
              f"evidence={s['survivor_score']['root_cause_evidence'] + s['survivor_score']['narrative_evidence']}")
    print(f"\nreport: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

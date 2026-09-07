#!/usr/bin/env python3
"""scripts/r417_dev_query_form_ab.py — audit item 3 (R417): the LIVE
dev-set A/B for the adopted comparison-targeted query form.

CONTEXT (Art. LI — learning must change future search):
  The R412-V3 gate-fail decomposition measured the query form as the
  DOMINANT retrieval variable for numeric-bearing evidence (the 12
  unmatched numeric-bearing reference records were europepmc/core-
  indexed; the '{capability} experimental comparison' acquisition form
  outperformed all three sealed lane forms on reference recall). R417
  adopts the form into the canonical retrieval instrument
  (query_expansion COMPARISON_TARGETED + additive source routing).
  THIS script measures the adoption on a DEV capability set — NOT the
  frozen benchmark (Art. LIX: tuning/verification discipline; the
  benchmark's blind re-verification requires a second sealed corpus,
  recorded as the owner-gated path).

DESIGN (fixed before the run):
  - 8 dev capabilities, DISJOINT from the benchmark's 8 areas, spanning
    medical / energy / industrial / materials.
  - Control arm: plain keyword form '<capability>'.
  - Treatment arm: '<capability> experimental comparison'.
  - SAME source (EuropePMC), SAME cap, SAME connector, same window;
    the ONLY variable is the query form (the diagnosis's variable).
  - Numeric-bearing = the engine's own deterministic FEAL scan
    (extract_numeric_evidence over title+abstract) returns >= 1 item.
  - Reported per arm: pools, records, numeric-bearing rate, mean
    numeric-bearing records per query. Raw per-query results committed.

  Pre-registered expectation (falsifiable): the comparison arm
  retrieves a HIGHER numeric-bearing rate (the form selects for
  comparative-experimental literature — the numeric-bearing document
  class). The falsifying outcome: no difference or the reverse —
  recorded as such, never tuned away.

Constitutional grounding:
  - Art. LI: the adoption + this measurement ARE the behavioral
    change from the V3 failure knowledge.
  - Art. LIX: dev set, not the frozen benchmark.
  - Art. XXI.3/LXI: provider failures are recorded failures, never
    absence; an INCOMPLETE query never counts in either direction.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

OUT_PATH = REPO / "R417" / "RETRIEVAL_QUERY_FORM" / "DEV_AB_MEASUREMENT.json"

DEV_CAPABILITIES = [
    # dev set — disjoint from the benchmark's 8 areas; medical/energy/
    # industrial/materials spread
    "photoacoustic contrast agent clearance",
    "solid electrolyte interphase stability",
    "vibration energy harvester bandwidth",
    "catheter surface thrombosis resistance",
    "perovskite moisture degradation",
    "geothermal heat exchanger fouling",
    "ultrasonic machining burr formation",
    "lithium extraction brine selectivity",
]

PACE_SECONDS = 1.0


def _numeric_bearing(title: str, abstract: str) -> int:
    from discovery_fabric.r412.frontier_evidence import (
        extract_numeric_evidence)
    try:
        ev = extract_numeric_evidence(title or "", abstract or "")
        return len(ev.get("evidences") or [])
    except Exception:  # noqa: BLE001 — recorded, never silent
        return 0


def _search(conn, query: str) -> Dict[str, Any]:
    try:
        res = conn.search(query)
        return {"status": res.status, "ok": bool(res.ok),
                "n": len(res.records),
                "records": [
                    {"record_id": r.record_id,
                     "title": r.title,
                     "abstract": (r.normalized or {}).get("abstract")
                     or ""}
                    for r in (res.records or [])],
                "error": res.error}
    except Exception as exc:  # noqa: BLE001 — Art. XXI.3
        return {"status": "EXCEPTION", "ok": False, "n": 0,
                "records": [], "error": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    from discovery_fabric.source_registry.connectors.scientific import (
        EuropePmcConnector)

    conn = EuropePmcConnector()
    per_query: List[Dict[str, Any]] = []
    for cap in DEV_CAPABILITIES:
        for arm, query in (("CONTROL_KEYWORD", cap),
                           ("TREATMENT_COMPARISON",
                            f"{cap} experimental comparison")):
            out = _search(conn, query)
            time.sleep(PACE_SECONDS)
            bearing = [
                {"record_id": r["record_id"],
                 "n_numeric": _numeric_bearing(r["title"], r["abstract"])}
                for r in out["records"]]
            n_bearing = sum(1 for b in bearing if b["n_numeric"] > 0)
            per_query.append({
                "capability": cap, "arm": arm, "query": query,
                "status": out["status"], "n_records": out["n"],
                "n_numeric_bearing": n_bearing,
                "numeric_bearing_rate": (
                    round(n_bearing / out["n"], 4) if out["n"] else None),
                "error": out.get("error"),
            })
            print(f"  [{arm:>20}] {cap[:44]:<44} n={out['n']:<3} "
                  f"numeric={n_bearing:<3} "
                  f"rate={per_query[-1]['numeric_bearing_rate']}")

    def _arm(arm: str) -> Dict[str, Any]:
        rows = [q for q in per_query if q["arm"] == arm
                and q["n_records"] is not None]
        done = [q for q in rows if q["status"] == "OK"]
        total_records = sum(q["n_records"] for q in rows)
        total_bearing = sum(q["n_numeric_bearing"] for q in rows)
        rates = [q["numeric_bearing_rate"] for q in rows
                 if q["numeric_bearing_rate"] is not None]
        return {
            "n_queries": len(rows), "n_ok": len(done),
            "total_records": total_records,
            "total_numeric_bearing": total_bearing,
            "mean_bearing_rate": (
                round(sum(rates) / len(rates), 4) if rates else None),
            "mean_bearing_per_query": (
                round(total_bearing / len(rows), 3) if rows else None),
        }

    control = _arm("CONTROL_KEYWORD")
    treatment = _arm("TREATMENT_COMPARISON")
    c_rate, t_rate = (control["mean_bearing_rate"],
                      treatment["mean_bearing_rate"])
    if c_rate is not None and t_rate is not None:
        outcome = ("CONFIRMED: the comparison arm retrieves a higher "
                   "numeric-bearing rate on the dev set — the adoption "
                   "is measured effective forward"
                   if t_rate > c_rate else
                   "NOT_CONFIRMED: no measured advantage on this dev "
                   "set — recorded honestly; the adoption's basis "
                   "remains the V3 reference-recall decomposition")
    else:
        outcome = "INCOMPLETE: transport failures dominate (Art. LXI)"

    record = {
        "artifact_type": "R417_DEV_QUERY_FORM_AB_MEASUREMENT",
        "purpose": ("the LIVE dev measurement of the adopted "
                    "COMPARISON_TARGETED query form (Art. LI adoption "
                    "of the R412-V3 query-form learning)"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dev_set_discipline": (
            "the 8 dev capabilities are DISJOINT from the frozen "
            "benchmark's 8 areas (Art. LIX: dev-set measurement; the "
            "benchmark is not consumed by this run); the blind "
            "re-verification path (a second sealed corpus) is recorded "
            "as owner-gated"),
        "design": {
            "variable": "query form ONLY (the diagnosis's variable)",
            "control_arm": "plain keyword form '<capability>'",
            "treatment_arm": "'<capability> experimental comparison'",
            "source": "europepmc (the source the V3 decomposition named "
                      "for 9 of the 12 unmatched numeric-bearing "
                      "records; key-free, live)",
            "numeric_bearing_instrument": (
                "the engine's deterministic FEAL scan "
                "(discovery_fabric/r412/frontier_evidence."
                "extract_numeric_evidence over title+abstract)"),
            "pre_registered_expectation": (
                "the comparison arm retrieves a higher numeric-bearing "
                "rate; falsifying outcome recorded as NOT_CONFIRMED"),
        },
        "control": control,
        "treatment": treatment,
        "outcome": outcome,
        "per_query": per_query,
        "reviewer_provenance": "AI_REVIEW (Art. LXVII)",
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(record, indent=1))
    print(json.dumps({"control": control, "treatment": treatment,
                      "outcome": outcome}, indent=1))
    print(f"measurement: {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

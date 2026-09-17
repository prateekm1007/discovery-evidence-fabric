#!/usr/bin/env python3
"""R497 — live collision-transport measurement through the FIXED production path.

Budget discipline (metered source): the pb_live_ key reported 13/20 remaining
(floor 2 -> 11 usable). This measurement spends at most 4 PatentBear searches:
  1. fixed-path liveness re-proof ("virtual reality" -> REAL hits expected,
     the exact query that false-zeroed pre-fix)
  2. a 3-step mechanism-derived query ladder (Art. XLIII neutral: derived from
     the a2dev corpus case's OWN mechanism facts, not from desired outcomes)
     through the REAL collision stage (search_patents) with per-source typed
     states: google_patents (free, re-measured), lens_patent (re-measured),
     patentbear (the R378 CEO-designated source, now live)

Everything typed per Art. XXI.3: provider failures are never absence; no
novelty verdict is emitted (Art. XLVI — this is a transport/stage measurement).
Writes R497/R497_COLLISION_TRANSPORT_MEASUREMENT.json.
"""
import json
import sys
import time
from pathlib import Path

REPO = Path("/home/z/my-project/repos/discovery-evidence-fabric")
sys.path.insert(0, str(REPO))

from discovery_fabric.prior_art_v2 import sources as src  # noqa: E402
from discovery_fabric.prior_art_v2 import collision_resolution as cr  # noqa: E402

OUT = REPO / "R497" / "R497_COLLISION_TRANSPORT_MEASUREMENT.json"
METER = REPO / "patent_sources" / "patentbear_meter.json"


def meter_now():
    try:
        return json.loads(METER.read_text())
    except Exception:  # noqa: BLE001
        return {"monthly_remaining": None}


def main():
    t0 = time.time()
    rec = {
        "measurement_id": "R497_COLLISION_TRANSPORT_MEASUREMENT",
        "measured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "reviewer_provenance": "AI_REVIEW",
        "context": "the re-audit's P0 #3 names collisions incomplete (atria dark, "
                   "Lens 401/google 503 in the R491-era picture); Coder 2's R496 left "
                   "the patent side PATENT_BLIND with the bearer-capable token named as "
                   "the missing piece; the operator rotated the PatentBear key this "
                   "round and the transport measured LIVE after the R497 scope-order fix",
        "meter_before": meter_now(),
        "sections": {},
    }

    # ---- 1. fixed-path liveness re-proof (the exact false-zeroed query) ----
    r = src.search_patent_bear("virtual reality", 5)
    rec["sections"]["fixed_path_liveness"] = {
        "query": "virtual reality",
        "state": "OK" if r.success else "TYPED_FAILURE",
        "hits": len(r.hits or []),
        "hit_ids": [h.patent_id for h in (r.hits or [])][:5],
        "error": r.error,
        "rate_limit_remaining": r.rate_limit_remaining,
        "note": "the exact query that measured 200/0-hits pre-fix through the broken "
                "scope='all' order; through the fixed patents-first order it must "
                "return real records",
    }
    print(f"[liveness] success={r.success} hits={len(r.hits or [])} "
          f"meter={meter_now().get('monthly_remaining')}")
    if not r.success or not (r.hits or []):
        rec["sections"]["aborted"] = ("liveness re-proof failed — ladder not run "
                                      "(quota preserved; typed failure above)")
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(rec, indent=1) + "\n")
        print("ABORTED after liveness (quota preserved)")
        return

    # ---- 2. the CANONICAL ladder from a corpus case's own profile ----
    # Art. XLIII: every term below is taken from the a2dev-09 case's own
    # mechanism/intervention text (the frozen R492 DEV corpus, seeded-defect
    # candidate: electrochlorination at uptake with hydrogen safety claimed
    # from turbulent dilution + the existing tank vent alone). No solution
    # class injected; the 5-class ladder is the stage's own canonical shape.
    profile = cr.CandidateProfile(
        intervention="in-line electrochlorination at ballast uptake; hydrogen "
                     "released to the carrier stream, kept below LEL by turbulent "
                     "dilution and the tank's existing pressure-vacuum vent",
        mechanism="electrolytic generation of active chlorine in the ballast "
                  "stream dosing 8-10 mg/L TRO for 3-log kill with 4 h dwell; "
                  "cathodic hydrogen diluted below flammable concentration by "
                  "turbulent ballast flow and natural tank venting",
        expected_effect="3-log organism kill at uptake plus hydrogen held below "
                        "the lower explosive limit without dedicated ventilation",
        entity_terms=["ballast water", "electrochlorination", "ship"],
        mechanism_terms=["electrolytic chlorine generation", "hydrogen dilution",
                         "tank venting"],
        distinguishing_terms=["electrochlorination", "hydrogen",
                              "explosive limit"],
        adjacent_terms=["disinfection", "gas removal", "ventilation"],
        device_terms=["ballast tank", "electrolyzer"],
        function_terms=["inactivation", "dilution", "venting"],
        distinguishing_full=["electrochlorination", "electrolytic", "active chlorine",
                             "TRO", "hydrogen", "cathode", "dilution", "turbulent flow",
                             "pressure-vacuum vent", "LEL", "ballast uptake", "dwell"],
    )
    ladder = cr.build_query_ladder(profile)
    rec["ladder_derivation"] = {
        "source_case": "a2dev-09-electrochlor-h2-natural-vent (R492 frozen DEV "
                       "corpus, TRUE_POSITIVE_seeded_defect)",
        "derivation_rule": "every profile term taken from the case's own "
                           "mechanism/intervention text (Art. XLIII search-space "
                           "neutral); the 5-class ladder is the collision stage's "
                           "own canonical build_query_ladder shape",
        "ladder": [{"query_class": s["query_class"], "query": s["query"],
                    "query_compact": s.get("query_compact", "")}
                   for s in ladder],
    }

    t1 = time.time()
    hits, errors = cr.search_patents(
        ladder, sources=["google_patents", "lens_patent", "patentbear"],
        sleep_between=0.4, per_source_results=5)
    wall = round(time.time() - t1, 1)

    per_source = {}
    for e in errors:
        per_source.setdefault(e.get("source"), []).append(
            {"query": e.get("query"), "state": e.get("state") or e.get("error"),
             "error": str(e.get("error"))[:160]})
    for h in hits:
        per_source.setdefault(h.source_id, [])
    rec["sections"]["collision_ladder"] = {
        "wall_s": wall,
        "total_hits": len(hits),
        "per_source_hit_counts": {s: sum(1 for h in hits if h.source_id == s)
                                  for s in {h.source_id for h in hits}},
        "per_source_errors": per_source,
        "hit_sample": [
            {"source": h.source_id, "id": h.patent_id or h.doi,
             "title": (h.title or "")[:110],
             "date": h.publication_date, "query": h.query}
            for h in hits[:12]],
    }
    print(f"[ladder] hits={len(hits)} per_source="
          f"{rec['sections']['collision_ladder']['per_source_hit_counts']} "
          f"errors={len(errors)} wall={wall}s")
    for e in errors[:12]:
        print("  ERR", e.get("source"), str(e.get("error"))[:90])

    # ---- 3. meter after + honest accounting ----
    rec["meter_after"] = meter_now()
    rec["searches_spent_estimate"] = {
        "patentbear_wire_calls": "1 (liveness) + ladder (1 per step; 'all'-scope "
                                 "only on zero-hit steps)",
        "remaining_after": meter_now().get("monthly_remaining"),
    }
    rec["no_novelty_verdict"] = ("Art. XLVI: this is a transport/stage measurement — "
                                 "no novelty determination is emitted; retrieval "
                                 "absence is not novelty proof")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1) + "\n")
    print(f"record -> {OUT} (wall {round(time.time()-t0,1)}s)")


if __name__ == "__main__":
    main()

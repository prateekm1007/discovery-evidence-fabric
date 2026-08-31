"""R377 Task 2 — PATENT TEXT GROUND TRUTH FETCH (CEO directive 2).

> "For at least several resolved positions, inspect the actual underlying
>  patent text/claims where available. Determine exactly where the current
>  term-overlap method agrees with—and where it diverges from—the
>  substantive technical relationship."

Step 1 (this script): fetch the FULL abstract for every family
representative of the six survivors' resolved positions, via the Lens
patent API doc_key query (measured: works while patents.google.com is
503-blocked from this ASN and the engine's claims-fetch URL format is
404-broken). Saves raw text for substantive inspection.

MEASURED DEFECTS (recorded for Task 5):
  - fetch_claim_evidence builds
    https://patents.google.com/patent/US_20260253984_A1_20260827/en
    from the Lens doc_key; Google's canonical format is US20260253984A1
    -> every correctly-formed ID 404s before the 503 bot-block even
    applies. All 30 families in the six fresh runs recorded
    claims_fetch_status='HTTP 503' -> every family adjudicated at
    ABSTRACT tier on 400-char truncated snippets.

Output: TOSCANINI/R377_PATENT_TEXT_FETCH.json (full abstracts, raw)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.prior_art_v2 import sources  # noqa: E402

BASE = Path(__file__).resolve().parents[1]
RUNS = [
    "t6_medical_infusion_occlusion",
    "t6_aerospace_battery_thermal_event",
    "t6_energy_ev_thermal_runaway",
    "t6_industrial_rolling_stock_equipment_failure",
    "t6_materials_rail_steel_fatigue",
    "t6_electronics_li_battery_product_fire",
]


def _fetch_full_abstract(doc_key: str) -> dict:
    """Lens patent search by doc_key; returns the FULL abstract text."""
    url = "https://api.lens.org/patent/search"
    payload = json.dumps({
        "query": f'doc_key:("{doc_key}")',
        "size": 1,
    }).encode()
    headers = {"Authorization": f"Bearer {sources.LENS_TOKEN}"}
    status, body, latency = sources._http_post(
        url, payload, headers=headers, timeout=25)
    if status != 200:
        return {"fetch_status": f"HTTP {status}", "latency_ms": latency}
    try:
        data = json.loads(body)
    except Exception as exc:  # noqa: BLE001
        return {"fetch_status": f"parse error: {exc}"}
    recs = data.get("data") or []
    if not recs:
        return {"fetch_status": "NO_RECORD"}
    rec = recs[0]
    abstract = rec.get("abstract") or ""
    if isinstance(abstract, list):
        abstract = abstract[0].get("text", "") if abstract else ""
    biblio = rec.get("biblio") or {}
    it = biblio.get("invention_title")
    title = ""
    if isinstance(it, list):
        for item in it:
            if isinstance(item, dict) and item.get("text"):
                title = str(item["text"])
                break
    elif isinstance(it, str):
        title = it
    return {
        "fetch_status": "OK",
        "title": title,
        "abstract_full": str(abstract),
        "abstract_len": len(str(abstract)),
        "doc_key": rec.get("doc_key"),
        "lens_id": rec.get("lens_id"),
        "jurisdiction": rec.get("jurisdiction"),
        "date_published": rec.get("date_published"),
        "latency_ms": latency,
    }


def main() -> None:
    out = []
    for run in RUNS:
        rd = BASE / "ENGINE_RUNS" / run
        sel = json.loads((rd / "SURVIVOR_SELECTION.json").read_text())
        cid = sel["selected"]
        grid_key = cid.split(":")[2] if cid.count(":") >= 2 else None
        spec_path = rd / f"INVENTION_SPECIFICATION_grid-{grid_key}.json"
        if not spec_path.exists():
            spec_path = rd / "INVENTION_SPECIFICATION.json"
        spec = json.loads(spec_path.read_text())
        dv = (spec.get("distinguishing_features") or {}).get("value") or {}
        intervention = str(dv.get("intervention") or "")
        pav = (spec.get("prior_art") or {}).get("value") or {}
        res = pav.get("differentiation_resolution") or {}
        fams = res.get("per_family") or []
        run_entry = {
            "run": run,
            "survivor": cid,
            "intervention": intervention,
            "mechanism": (spec.get("mechanism") or {}).get("value", {})
            .get("mechanism"),
            "families": [],
        }
        for fam in fams:
            rep = fam.get("representative") or {}
            doc_key = rep.get("patent_id")
            cov = fam.get("coverage") or {}
            fetched = _fetch_full_abstract(doc_key)
            fetched.update({
                "family_id": fam.get("family_id"),
                "engine_recorded": {
                    "title": rep.get("title"),
                    "evidence_tier": fam.get("evidence_tier"),
                    "coverage_class": cov.get("coverage_class"),
                    "coverage_ratio": cov.get("coverage_ratio"),
                    "mechanism_overlap_terms":
                        cov.get("mechanism_overlap_terms"),
                    "distinguishing_terms_covered":
                        cov.get("distinguishing_terms_covered"),
                    "distinguishing_terms_surviving":
                        cov.get("distinguishing_terms_surviving"),
                },
            })
            run_entry["families"].append(fetched)
            time.sleep(1.0)  # Lens courtesy interval
        out.append(run_entry)
        print(f"{run}: {len(fams)} families fetched")

    dest = BASE / "TOSCANINI" / "R377_PATENT_TEXT_FETCH.json"
    dest.write_text(json.dumps(out, indent=1))
    print(f"-> {dest}")


if __name__ == "__main__":
    main()

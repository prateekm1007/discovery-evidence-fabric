"""A2 prior art — search for existing solutions."""
from __future__ import annotations
import json, re, ssl, time, urllib.request, urllib.parse
from datetime import datetime, timezone

_SSL = ssl.create_default_context()
_SSL.check_hostname = False
_SSL.verify_mode = ssl.CERT_NONE

def search_prior_art(intervention: str, device: str) -> dict:
    """Step 5: Search for prior art. Never claim 'nobody has done this'."""
    queries = [
        f"{device} {intervention[:50]}",
        f"{intervention[:50]} medical device",
    ]
    results = []
    for q in queries:
        try:
            encoded = urllib.parse.quote(q)
            url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={encoded}&format=json&pageSize=3"
            req = urllib.request.Request(url, headers={"User-Agent": "A2-PriorArt/1.0"})
            resp = urllib.request.urlopen(req, timeout=20, context=_SSL)
            data = json.loads(resp.read())
            for r in data.get("resultList", {}).get("result", []):
                results.append({"title": r.get("title", ""), "id": r.get("id", ""), "query": q})
        except Exception:
            pass
        time.sleep(1.0)

    # Determine prior art status
    if not results:
        status = "NO_MATCHING_EVIDENCE_FOUND"
    elif len(results) >= 3:
        status = "LIKELY_PRIOR_ART_EXISTS"
    else:
        status = "PARTIAL_PRIOR_ART"

    report = {
        "prior_art_status": status,
        "databases_searched": ["EuropePMC"],
        "queries": queries,
        "date_range": "all",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "result_count": len(results),
        "results": results[:5],
        "limitations": [
            "Only EuropePMC searched",
            "No patent databases searched",
            "No ClinicalTrials.gov searched",
        ],
        "note": "Never claim 'nobody has done this.' Only report 'No matching evidence found within the searched universe.'",
    }
    print(f"  [prior_art] status={status} results={len(results)}")
    return report

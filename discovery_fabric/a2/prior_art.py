"""A2 prior art — search for existing solutions."""
from __future__ import annotations
import json, re, ssl, time, urllib.request, urllib.parse
from datetime import datetime, timezone

_SSL = ssl.create_default_context()
_SSL.check_hostname = False
_SSL.verify_mode = ssl.CERT_NONE

def search_prior_art_with_queries(queries: list) -> dict:
    """Step 5 (R376 form): search EuropePMC with ENGINE-FORMED keyword
    queries (device+failure / mechanism keyword_form) instead of the
    legacy raw '{device} {intervention[:50]}' pair — the legacy queries
    measured as filler-polluted. Status vocabulary unchanged; provider
    failure is recorded honestly (an exception on a query contributes
    zero results and the query is kept in the report with its outcome)."""
    results = []
    query_log = []
    for q in queries:
        if not q or not str(q).strip():
            continue
        try:
            encoded = urllib.parse.quote(q)
            url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={encoded}&format=json&pageSize=3"
            req = urllib.request.Request(url, headers={"User-Agent": "A2-PriorArt/1.0"})
            resp = urllib.request.urlopen(req, timeout=20, context=_SSL)
            data = json.loads(resp.read())
            got = []
            for r in data.get("resultList", {}).get("result", []):
                got.append({"title": r.get("title", ""), "id": r.get("id", ""), "query": q})
            results.extend(got)
            query_log.append({"query": q, "status": "OK",
                              "result_count": len(got)})
        except Exception as exc:  # noqa: BLE001 — recorded, never hidden
            query_log.append({"query": q, "status": "SEARCH_FAILED",
                              "error": f"{type(exc).__name__}: {exc}"})
        time.sleep(1.0)

    if not results:
        status = "NO_MATCHING_EVIDENCE_FOUND"
    elif len(results) >= 3:
        status = "LIKELY_PRIOR_ART_EXISTS"
    else:
        status = "PARTIAL_PRIOR_ART"

    report = {
        "prior_art_status": status,
        "databases_searched": ["EuropePMC"],
        "queries": [q for q in queries if q and str(q).strip()],
        "query_log": query_log,
        "date_range": "all",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "result_count": len(results),
        "results": results[:5],
        "limitations": [
            "Only EuropePMC searched",
            "No patent databases searched (patent side handled by the collision core)",
            "No ClinicalTrials.gov searched",
        ],
        "note": "Never claim 'nobody has done this.' Only report 'No matching evidence found within the searched universe.'",
    }
    print(f"  [prior_art] status={status} results={len(results)}")
    return report


def search_prior_art(intervention: str, device: str) -> dict:
    """Step 5: Search for prior art. Never claim 'nobody has done this'.

    LEGACY entry point — kept for backwards compatibility (a2/run.py and
    older tests). The engine's COLLISION stage now calls
    search_prior_art_with_queries with engine-formed keyword queries."""
    queries = [
        f"{device} {intervention[:50]}",
        f"{intervention[:50]} medical device",
    ]
    return search_prior_art_with_queries(queries)

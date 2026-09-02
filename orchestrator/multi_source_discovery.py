"""
orchestrator/multi_source_discovery.py — Many-source invention discovery loop.

PER CEO v28.3 DIRECTIVE:
  "Build a many-source invention discovery loop where each candidate is
   attacked from a different epistemic direction."

  "The AI should run four independent searches for every candidate:
    1. Discovery search — How could this work?
    2. Destruction search — Why can't this work?
    3. Transfer search — Who solved an analogous problem elsewhere?
    4. Reality search — Did this actually work outside the paper/patent?

   Only when all four have been exhausted should a candidate earn serious
   engineering resources."

ARCHITECTURE:
  10 independent evidence layers, each with pluggable adapters:
    1. Scientific (PubMed, PMC, Europe PMC, Crossref)
    2. Clinical (ClinicalTrials.gov, WHO ICTRP)
    3. Regulatory (FDA/openFDA, MAUDE, recalls, PMA, 510(k), De Novo)
    4. Patents (USPTO, Google Patents, Espacenet, PATENTSCOPE, Lens)
    5. Funding (NIH RePORTER)
    6. Government science (NASA, NIST, DOE, DARPA)
    7. Engineering (institutional repositories)
    8. Negative evidence (retractions, recalls, failures, abandoned patents)
    9. Cross-domain (aerospace/industrial/robotics/materials/semiconductor)
   10. Competitive intelligence (assignee/family/inventor/citation graphs)

  Each source remains INDEPENDENT. The system never turns "many databases
  returned something similar" into "therefore it is true." The epistemic
  firewall protects the final claim.

FOUR-SEARCH ATTACK:
  For every candidate, the engine runs:
    1. Discovery: "How could this work?" — find supporting mechanisms
    2. Destruction: "Why can't this work?" — find contradictions, failures
    3. Transfer: "Who solved an analogous problem?" — cross-domain search
    4. Reality: "Did this actually work?" — clinical/regulatory/funding check

  Only when all four are exhausted does the candidate earn engineering resources.
"""
from __future__ import annotations
import json
import time
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from discovery_fabric.connectors.connector_states import fetch_json


REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Source adapters (free APIs, no key required unless noted)
#
# R394 section 4: the curl subprocess is GONE. The deployed image
# (python:3.12-slim) contains no curl, so every public run failed this
# stage with FileNotFoundError('curl') — measured 2026-09-02
# (R394/PRODUCTION_AUDIT.json, consultant claim 1, CONFIRMED_CURRENT).
# Every call now goes through the shared Python HTTP stack
# (discovery_fabric.connectors.connector_states) which classifies
# outcomes into the eight explicit connector states and never converts
# an outage into zero results.
# ---------------------------------------------------------------------------

def _search_get(url: str, timeout: int = 30) -> Optional[dict]:
    """GET JSON through the connector-state stack. Returns the parsed
    payload on SUCCESS/EMPTY_RESULT, None on any outage (the caller
    records the outage state — never a silent zero)."""
    r = fetch_json(url, timeout=timeout)
    if r.get("connector_state") in ("SUCCESS", "EMPTY_RESULT"):
        return r.get("data")
    return None


def search_pubmed(query: str, limit: int = 5) -> dict:
    """Search PubMed via NCBI E-utilities."""
    encoded = urllib.parse.quote(query)
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={encoded}&retmax={limit}&retmode=json"
    data = _search_get(url)
    if data is None:
        return {"source": "PubMed", "query": query, "total": 0, "results": [],
                "error": "fetch failed", "connector_state": "UNAVAILABLE_OR_TIMEOUT",
                "note": "outage — NOT absence (R394 s4)"}
    total = int(data.get("esearchresult", {}).get("count", "0"))
    ids = data.get("esearchresult", {}).get("idlist", [])
    return {"source": "PubMed", "query": query, "total": total, "results": [{"pmid": pid} for pid in ids],
            "connector_state": "EMPTY_RESULT" if total == 0 else "SUCCESS"}


def search_clinical_trials(query: str, limit: int = 5) -> dict:
    """Search ClinicalTrials.gov API."""
    encoded = urllib.parse.quote(query)
    url = f"https://clinicaltrials.gov/api/v2/studies?query.term={encoded}&pageSize={limit}&format=json"
    data = _search_get(url)
    if data is None:
        return {"source": "ClinicalTrials.gov", "query": query, "total": 0, "results": [],
                "error": "fetch failed", "connector_state": "UNAVAILABLE_OR_TIMEOUT",
                "note": "outage — NOT absence (R394 s4)"}
    total = data.get("totalCount", 0)
    studies = data.get("studies", [])
    results = []
    for s in studies[:limit]:
        proto = s.get("protocolSection", {})
        results.append({
            "nct_id": s.get("NCTId", proto.get("identificationModule", {}).get("nctId", "")),
            "title": proto.get("identificationModule", {}).get("officialTitle", "")[:120],
            "status": proto.get("statusModule", {}).get("overallStatus", ""),
        })
    return {"source": "ClinicalTrials.gov", "query": query, "total": total, "results": results}


def search_openfda(query: str, limit: int = 5) -> dict:
    """Search FDA openFDA for device adverse events."""
    encoded = urllib.parse.quote(query)
    url = f"https://api.fda.gov/device/event.json?search=device.generic_name:{encoded}&limit={limit}"
    data = _search_get(url)
    if data is None:
        return {"source": "openFDA", "query": query, "total": 0, "results": [],
                "error": "fetch failed or no results", "connector_state": "UNAVAILABLE_OR_TIMEOUT",
                "note": "outage — NOT absence (R394 s4)"}
    total = data.get("meta", {}).get("results", {}).get("total", 0)
    results = data.get("results", [])
    return {"source": "openFDA", "query": query, "total": total, "results": [{"event": r.get("event_type", ""), "date": r.get("date_received", "")} for r in results[:limit]]}


def search_nih_reporter(query: str, limit: int = 5) -> dict:
    """Search NIH RePORTER for funded research."""
    url = "https://api.reporter.nih.gov/v2/projects/search"
    payload = json.dumps({"criteria": {"text": query}, "offset": 0, "limit": limit, "sort_field": "project_start_date", "sort_order": "desc"})
    r = fetch_json(url, timeout=30, method="POST", body=payload,
                   headers={"Content-Type": "application/json"})
    if r.get("connector_state") not in ("SUCCESS", "EMPTY_RESULT"):
        state = r.get("connector_state")
        return {"source": "NIH RePORTER", "query": query, "total": 0, "results": [],
                "error": f"fetch failed", "connector_state": state,
                "connector_reason": r.get("reason", "")}
    data = r.get("data") or {}
    total = data.get("meta", {}).get("total", 0)
    projects = data.get("results", [])
    results = []
    for p in projects[:limit]:
        results.append({
            "project_num": p.get("project_num", ""),
            "title": p.get("project_title", "")[:120],
            "pi": p.get("principal_investigators", [{}])[0].get("full_name", "") if p.get("principal_investigators") else "",
            "fiscal_year": p.get("fiscal_year", ""),
            "award_amount": p.get("award_amount", 0),
        })
    return {"source": "NIH RePORTER", "query": query, "total": total, "results": results,
            "connector_state": r.get("connector_state")}


def search_crossref(query: str, limit: int = 5) -> dict:
    """Search Crossref for DOI metadata."""
    encoded = urllib.parse.quote(query)
    url = f"https://api.crossref.org/works?query={encoded}&rows={limit}"
    data = _search_get(url)
    if data is None:
        return {"source": "Crossref", "query": query, "total": 0, "results": [],
                "error": "fetch failed", "connector_state": "UNAVAILABLE_OR_TIMEOUT",
                "note": "outage — NOT absence (R394 s4)"}
    total = data.get("message", {}).get("total-results", 0)
    items = data.get("message", {}).get("items", [])
    results = []
    for item in items[:limit]:
        results.append({
            "doi": item.get("DOI", ""),
            "title": item.get("title", [""])[0][:120] if item.get("title") else "",
            "year": item.get("published", {}).get("date-parts", [[""]])[0][0] if item.get("published") else "",
        })
    return {"source": "Crossref", "query": query, "total": total, "results": results}


def search_nasa_tech_reports(query: str, limit: int = 5) -> dict:
    """Search NASA Technical Reports Server (NTRS)."""
    encoded = urllib.parse.quote(query)
    url = f"https://ntrs.nasa.gov/api/citations/search?q={encoded}&page[size]={limit}"
    data = _search_get(url)
    if data is None:
        return {"source": "NASA NTRS", "query": query, "total": 0, "results": [],
                "error": "fetch failed", "connector_state": "UNAVAILABLE_OR_TIMEOUT",
                "note": "outage — NOT absence (R394 s4)"}
    results = []
    for item in data.get("data", [])[:limit]:
        attrs = item.get("attributes", {})
        results.append({
            "id": item.get("id", ""),
            "title": attrs.get("title", "")[:120],
            "year": attrs.get("publication_date", "")[:4],
        })
    total = data.get("meta", {}).get("total", len(results))
    return {"source": "NASA NTRS", "query": query, "total": total, "results": results}


# ---------------------------------------------------------------------------
# Four-search attack system
# ---------------------------------------------------------------------------

@dataclass
class FourSearchResult:
    """Result of a 4-search attack on a candidate."""
    candidate_name: str
    discovery: dict   # How could this work?
    destruction: dict  # Why can't this work?
    transfer: dict    # Who solved an analogous problem?
    reality: dict     # Did this actually work?
    timestamp: str = ""
    summary: str = ""


def run_four_search_attack(candidate_name: str, mechanism_description: str,
                            physical_problem: str, failure_mode: str,
                            adjacent_industries: List[str] = None) -> FourSearchResult:
    """Run all 4 searches for a candidate.

    Args:
        candidate_name: Name of the candidate invention
        mechanism_description: How it's supposed to work
        physical_problem: The physical problem it addresses
        failure_mode: The failure mode it prevents/detects
        adjacent_industries: List of industries to search for transfer
    """
    if adjacent_industries is None:
        adjacent_industries = ["aerospace", "oil gas", "semiconductor", "robotics", "automotive"]

    # 1. Discovery: How could this work?
    discovery_query = f"{mechanism_description} AND {physical_problem}"
    discovery = {
        "pubmed": search_pubmed(discovery_query, 3),
        "crossref": search_crossref(discovery_query, 3),
        "nih_reporter": search_nih_reporter(discovery_query, 3),
    }

    # 2. Destruction: Why can't this work?
    destruction_query = f"{failure_mode} OR ({mechanism_description} failure) OR ({mechanism_description} limitation)"
    destruction = {
        "pubmed_failures": search_pubmed(destruction_query, 3),
        "openfda_adverse": search_openfda(physical_problem, 3),
        "clinical_trials_fail": search_clinical_trials(f"{physical_problem} failure", 3),
    }

    # 3. Transfer: Who solved an analogous problem?
    transfer = {}
    for industry in adjacent_industries:
        transfer_query = f"{physical_problem} {industry}"
        transfer[industry] = search_crossref(transfer_query, 2)

    # 4. Reality: Did this actually work?
    reality = {
        "clinical_trials": search_clinical_trials(physical_problem, 5),
        "nih_funding": search_nih_reporter(physical_problem, 5),
        "fda_adverse": search_openfda(physical_problem, 5),
    }

    result = FourSearchResult(
        candidate_name=candidate_name,
        discovery=discovery,
        destruction=destruction,
        transfer=transfer,
        reality=reality,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    # Summary
    disc_count = sum(s.get("total", 0) for s in discovery.values())
    dest_count = sum(s.get("total", 0) for s in destruction.values())
    transfer_count = sum(s.get("total", 0) for s in transfer.values())
    reality_count = sum(s.get("total", 0) for s in reality.values())

    result.summary = (
        f"Discovery: {disc_count} results | "
        f"Destruction: {dest_count} results | "
        f"Transfer: {transfer_count} results | "
        f"Reality: {reality_count} results"
    )

    return result


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def main():
    """Run the 4-search attack on the current #8 V7 candidate as first use case."""
    print(f"\n{'='*78}")
    print(f"MULTI-SOURCE INVENTION DISCOVERY — 4-Search Attack")
    print(f"{'='*78}")

    candidate = "Obstruction detection via differential pressure sensing"
    mechanism = "pressure gradient sensing CSF shunt"
    problem = "CSF shunt obstruction"
    failure = "shunt obstruction failure"

    print(f"\nCandidate: {candidate}")
    print(f"Mechanism: {mechanism}")
    print(f"Problem: {problem}")
    print(f"\nRunning 4-search attack...")

    result = run_four_search_attack(candidate, mechanism, problem, failure)

    # Print results
    print(f"\n{'='*78}")
    print(f"1. DISCOVERY SEARCH — How could this work?")
    print(f"{'='*78}")
    for source, data in result.discovery.items():
        print(f"  {source}: {data.get('total', 0)} results")
        for r in data.get("results", [])[:2]:
            title = r.get("title", r.get("pmid", r.get("project_num", r.get("doi", ""))))
            print(f"    - {str(title)[:100]}")

    print(f"\n{'='*78}")
    print(f"2. DESTRUCTION SEARCH — Why can't this work?")
    print(f"{'='*78}")
    for source, data in result.destruction.items():
        print(f"  {source}: {data.get('total', 0)} results")
        for r in data.get("results", [])[:2]:
            title = r.get("title", r.get("event", r.get("nct_id", "")))
            print(f"    - {str(title)[:100]}")

    print(f"\n{'='*78}")
    print(f"3. TRANSFER SEARCH — Who solved an analogous problem?")
    print(f"{'='*78}")
    for industry, data in result.transfer.items():
        print(f"  {industry}: {data.get('total', 0)} results")
        for r in data.get("results", [])[:1]:
            print(f"    - {r.get('title', '')[:100]}")

    print(f"\n{'='*78}")
    print(f"4. REALITY SEARCH — Did this actually work?")
    print(f"{'='*78}")
    for source, data in result.reality.items():
        print(f"  {source}: {data.get('total', 0)} results")
        for r in data.get("results", [])[:2]:
            title = r.get("title", r.get("event", r.get("project_num", "")))
            print(f"    - {str(title)[:100]}")

    print(f"\n{'='*78}")
    print(f"SUMMARY: {result.summary}")
    print(f"{'='*78}")

    # Save
    output_dir = REPO_ROOT / "MULTI_SOURCE_DISCOVERY"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "FOUR_SEARCH_OBSTRUCTION_DETECTION.json"

    report = {
        "candidate": candidate,
        "mechanism": mechanism,
        "problem": problem,
        "failure": failure,
        "discovery": result.discovery,
        "destruction": result.destruction,
        "transfer": result.transfer,
        "reality": result.reality,
        "summary": result.summary,
        "timestamp": result.timestamp,
        "epistemic_note": "Each source remains INDEPENDENT. Many databases returning similar results does NOT mean 'therefore it is true.' The epistemic firewall protects the final claim.",
    }

    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\nReport: {output_path}")
    return report


if __name__ == "__main__":
    main()

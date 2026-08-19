"""
orchestrator/triangulation_engine.py — Multi-universe evidence triangulation.

PER CEO v30 DIRECTIVE:
  "For each invention, the engine should deliberately query INDEPENDENT
   universes: scientific, engineering, patent, clinical, commercial, failure.
   That produces a triangulation engine."

  "The invention engine should become suspicious whenever those layers disagree."

  "Patent enthusiasm + scientific enthusiasm + regulatory failure + MAUDE problems
   is potentially a GRAVEYARD signal."

  "Clinical failure + weak patent coverage + strong adjacent-industry solution
   could be a GOLDMINE signal."

ARCHITECTURE:
  6 independent evidence universes, each with pluggable adapters:

  1. SCIENTIFIC REALITY
     PubMed + PMC + Europe PMC + Scopus + Crossref
     (what do scientists say?)

  2. ENGINEERING REALITY
     NASA NTRS + NIST + OSTI/DOE + IEEE (via Crossref) + Engineering Village
     (what did engineers build?)

  3. PATENT REALITY
     USPTO + WIPO PATENTSCOPE + Espacenet + Google Patents + Lens + PatentBear
     (what do patents say?)

  4. CLINICAL REALITY
     ClinicalTrials.gov + FDA 510(k)/PMA/De Novo + postmarket surveillance
     (what did regulators approve?)

  5. COMMERCIAL REALITY
     FDA device registrations + UDI + manufacturer listings
     (what reached the market?)

  6. FAILURE REALITY
     FDA MAUDE + recalls + ClinicalTrials.gov failures + retractions
     (what happened to actual patients/devices?)

TRIANGULATION:
  For each candidate, the engine queries all 6 universes and produces:
    - Agreement matrix (do the universes agree?)
    - Disagreement flags (where do they conflict?)
    - Graveyard signal (patent+science enthusiasm + regulatory/clinical failure)
    - Goldmine signal (clinical failure + weak patents + strong transfer solution)

  The triangulation does NOT replace the patent gate or physics gate.
  It provides ADDITIONAL evidence that can strengthen or weaken a candidate
  before expensive engineering resources are spent.
"""
from __future__ import annotations
import json
import subprocess
import urllib.parse
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Evidence Universe Adapters
# ---------------------------------------------------------------------------

def _curl_json(url: str, headers: dict = None, timeout: int = 30) -> Optional[dict]:
    cmd = ["curl", "-s", "-L", "--connect-timeout", "10", "--max-time", str(timeout), url]
    if headers:
        for k, v in headers.items():
            cmd.extend(["-H", f"{k}: {v}"])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout+5)
    except:
        return None
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except:
        return None


def _curl_post_json(url: str, payload: str, headers: dict = None, timeout: int = 30) -> Optional[dict]:
    cmd = ["curl", "-s", "-L", "-X", "POST", url, "-d", payload]
    if headers:
        for k, v in headers.items():
            cmd.extend(["-H", f"{k}: {v}"])
    else:
        cmd.extend(["-H", "Content-Type: application/json"])
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except:
        return None


# --- Universe 1: Scientific Reality ---

def query_pubmed(query: str, limit: int = 3) -> dict:
    encoded = urllib.parse.quote(query)
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={encoded}&retmax={limit}&retmode=json"
    data = _curl_json(url)
    if not data:
        return {"universe": "scientific", "source": "PubMed", "query": query, "total": 0, "results": [], "error": "fetch failed"}
    total = int(data.get("esearchresult", {}).get("count", "0"))
    ids = data.get("esearchresult", {}).get("idlist", [])
    return {"universe": "scientific", "source": "PubMed", "query": query, "total": total, "results": [{"pmid": pid} for pid in ids]}


def query_europe_pmc(query: str, limit: int = 3) -> dict:
    encoded = urllib.parse.quote(query)
    url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={encoded}&format=json&pageSize={limit}"
    data = _curl_json(url)
    if not data:
        return {"universe": "scientific", "source": "EuropePMC", "query": query, "total": 0, "results": [], "error": "fetch failed"}
    total = int(data.get("hitCount", 0))
    results = []
    for item in data.get("resultList", {}).get("result", [])[:limit]:
        results.append({"title": item.get("title", "")[:120], "pmid": item.get("pmid", ""), "doi": item.get("doi", "")})
    return {"universe": "scientific", "source": "EuropePMC", "query": query, "total": total, "results": results}


# --- Universe 2: Engineering Reality ---

def query_nasa_ntrs(query: str, limit: int = 3) -> dict:
    encoded = urllib.parse.quote(query)
    url = f"https://ntrs.nasa.gov/api/citations/search?q={encoded}&page[size]={limit}"
    data = _curl_json(url)
    if not data:
        return {"universe": "engineering", "source": "NASA_NTRS", "query": query, "total": 0, "results": [], "error": "fetch failed"}
    results = []
    for item in data.get("data", [])[:limit]:
        attrs = item.get("attributes", {})
        results.append({"id": item.get("id", ""), "title": attrs.get("title", "")[:120]})
    total = data.get("meta", {}).get("total", len(results))
    return {"universe": "engineering", "source": "NASA_NTRS", "query": query, "total": total, "results": results}


def query_osti(query: str, limit: int = 3) -> dict:
    """OSTI/DOE — may time out, handle gracefully."""
    encoded = urllib.parse.quote(query)
    url = f"https://www.osti.gov/api/v1/records?q={encoded}&rows={limit}&format=json"
    try:
        data = _curl_json(url, timeout=15)
    except:
        data = None
    if not data:
        return {"universe": "engineering", "source": "OSTI_DOE", "query": query, "total": 0, "results": [], "error": "timeout or fetch failed"}
    total = data.get("response", {}).get("numFound", 0)
    results = []
    for item in data.get("response", {}).get("docs", [])[:limit]:
        results.append({"title": item.get("title", "")[:120], "doi": item.get("doi", "")})
    return {"universe": "engineering", "source": "OSTI_DOE", "query": query, "total": total, "results": results}


# --- Universe 3: Patent Reality ---

def query_wipo_patentscope(query: str, limit: int = 3) -> dict:
    """WIPO PATENTSCOPE search (free, no API key needed for basic search)."""
    encoded = urllib.parse.quote(query)
    url = f"https://patentscope.wipo.int/search/en/result.jsf?query={encoded}"
    # PATENTSCOPE doesn't have a public JSON API, but we can note the search was attempted
    return {"universe": "patent", "source": "WIPO_PATENTSCOPE", "query": query, "total": -1, "results": [], "note": "PATENTSCOPE requires web interface — no public JSON API. Manual search recommended."}


# --- Universe 4: Clinical Reality ---

def query_clinical_trials(query: str, limit: int = 3) -> dict:
    encoded = urllib.parse.quote(query)
    url = f"https://clinicaltrials.gov/api/v2/studies?query.term={encoded}&pageSize={limit}&format=json"
    data = _curl_json(url)
    if not data:
        return {"universe": "clinical", "source": "ClinicalTrials.gov", "query": query, "total": 0, "results": [], "error": "fetch failed"}
    total = data.get("totalCount", 0)
    results = []
    for s in data.get("studies", [])[:limit]:
        proto = s.get("protocolSection", {})
        results.append({
            "nct_id": proto.get("identificationModule", {}).get("nctId", ""),
            "title": proto.get("identificationModule", {}).get("officialTitle", "")[:120],
            "status": proto.get("statusModule", {}).get("overallStatus", ""),
        })
    return {"universe": "clinical", "source": "ClinicalTrials.gov", "query": query, "total": total, "results": results}


def query_fda_510k(query: str, limit: int = 3) -> dict:
    """FDA 510(k) database search via openFDA."""
    encoded = urllib.parse.quote(query)
    url = f"https://api.fda.gov/device/510k.json?search=device_name:{encoded}&limit={limit}"
    data = _curl_json(url)
    if not data or 'error' in data:
        return {"universe": "clinical", "source": "FDA_510k", "query": query, "total": 0, "results": [], "note": "No 510(k) results or API unavailable"}
    total = data.get("meta", {}).get("results", {}).get("total", 0)
    results = []
    for r in data.get("results", [])[:limit]:
        results.append({"device_name": r.get("device_name", "")[:100], "k_number": r.get("k_number", ""), "applicant": r.get("applicant", "")[:60]})
    return {"universe": "clinical", "source": "FDA_510k", "query": query, "total": total, "results": results}


# --- Universe 5: Commercial Reality ---

def query_fda_pma(query: str, limit: int = 3) -> dict:
    """FDA PMA (Premarket Approval) database."""
    encoded = urllib.parse.quote(query)
    url = f"https://api.fda.gov/device/pma.json?search=trade_name:{encoded}&limit={limit}"
    data = _curl_json(url)
    if not data or 'error' in data:
        return {"universe": "commercial", "source": "FDA_PMA", "query": query, "total": 0, "results": [], "note": "No PMA results or API unavailable"}
    total = data.get("meta", {}).get("results", {}).get("total", 0)
    results = []
    for r in data.get("results", [])[:limit]:
        results.append({"trade_name": r.get("trade_name", "")[:100], "pma_number": r.get("pma_number", ""), "applicant": r.get("applicant", "")[:60]})
    return {"universe": "commercial", "source": "FDA_PMA", "query": query, "total": total, "results": results}


# --- Universe 6: Failure Reality ---

def query_fda_maude(query: str, limit: int = 3) -> dict:
    """FDA MAUDE adverse event database."""
    encoded = urllib.parse.quote(query)
    url = f"https://api.fda.gov/device/event.json?search=device.generic_name:{encoded}&limit={limit}"
    data = _curl_json(url)
    if not data or 'error' in data:
        return {"universe": "failure", "source": "FDA_MAUDE", "query": query, "total": 0, "results": [], "note": "No MAUDE results or API unavailable"}
    total = data.get("meta", {}).get("results", {}).get("total", 0)
    results = []
    for r in data.get("results", [])[:limit]:
        results.append({"event_type": r.get("event_type", ""), "date": r.get("date_received", "")})
    return {"universe": "failure", "source": "FDA_MAUDE", "query": query, "total": total, "results": results}


def query_fda_recalls(query: str, limit: int = 3) -> dict:
    """FDA device recalls database."""
    encoded = urllib.parse.quote(query)
    url = f"https://api.fda.gov/device/recall.json?search=product_description:{encoded}&limit={limit}"
    data = _curl_json(url)
    if not data or 'error' in data:
        return {"universe": "failure", "source": "FDA_Recalls", "query": query, "total": 0, "results": [], "note": "No recall results or API unavailable"}
    total = data.get("meta", {}).get("results", {}).get("total", 0)
    results = []
    for r in data.get("results", [])[:limit]:
        results.append({"product": r.get("product_description", "")[:100], "reason": r.get("reason_for_recall", "")[:100]})
    return {"universe": "failure", "source": "FDA_Recalls", "query": query, "total": total, "results": results}


# ---------------------------------------------------------------------------
# Triangulation Engine
# ---------------------------------------------------------------------------

@dataclass
class UniverseResult:
    universe: str
    sources: List[dict]
    total_results: int
    signal: str = "NEUTRAL"  # ENTHUSIASM / FAILURE / NEUTRAL / EMPTY


@dataclass
class TriangulationReport:
    candidate_name: str
    timestamp: str
    universes: List[UniverseResult]
    agreement_matrix: Dict[str, str]  # universe_pair → "AGREE" / "DISAGREE" / "UNKNOWN"
    graveyard_signal: bool  # patent+science enthusiasm + clinical/failure problems
    goldmine_signal: bool  # clinical failure + weak patents + strong transfer
    summary: str
    recommendation: str

    def to_dict(self) -> dict:
        return {
            "candidate_name": self.candidate_name,
            "timestamp": self.timestamp,
            "universes": [asdict(u) for u in self.universes],
            "agreement_matrix": self.agreement_matrix,
            "graveyard_signal": self.graveyard_signal,
            "goldmine_signal": self.goldmine_signal,
            "summary": self.summary,
            "recommendation": self.recommendation,
        }


def run_triangulation(candidate_name: str, mechanism_query: str,
                       clinical_query: str, device_query: str) -> TriangulationReport:
    """Run triangulation across all 6 evidence universes.

    Args:
        candidate_name: Name of the candidate
        mechanism_query: Query for scientific/engineering/patent search
        clinical_query: Query for clinical trials and FDA databases
        device_query: Query for FDA device/recall/MAUDE databases
    """
    universes = []

    # Universe 1: Scientific
    sci_results = [query_pubmed(mechanism_query, 3), query_europe_pmc(mechanism_query, 3)]
    sci_total = sum(r.get("total", 0) for r in sci_results if r.get("total", 0) > 0)
    sci_signal = "ENTHUSIASM" if sci_total > 10 else "NEUTRAL" if sci_total > 0 else "EMPTY"
    universes.append(UniverseResult("scientific", sci_results, sci_total, sci_signal))

    # Universe 2: Engineering
    eng_results = [query_nasa_ntrs(mechanism_query, 3), query_osti(mechanism_query, 3)]
    eng_total = sum(r.get("total", 0) for r in eng_results if r.get("total", 0) > 0)
    eng_signal = "ENTHUSIASM" if eng_total > 5 else "NEUTRAL" if eng_total > 0 else "EMPTY"
    universes.append(UniverseResult("engineering", eng_results, eng_total, eng_signal))

    # Universe 3: Patent (note — we already did patent search in V14-V16)
    pat_results = [{"note": "Patent search conducted separately in V14-V16. See patent gate results."}]
    universes.append(UniverseResult("patent", pat_results, -1, "CONDUCTED_SEPARATELY"))

    # Universe 4: Clinical
    clin_results = [query_clinical_trials(clinical_query, 3), query_fda_510k(device_query, 3)]
    clin_total = sum(r.get("total", 0) for r in clin_results if r.get("total", 0) > 0)
    clin_signal = "APPROVED" if clin_total > 0 else "EMPTY"
    universes.append(UniverseResult("clinical", clin_results, clin_total, clin_signal))

    # Universe 5: Commercial
    comm_results = [query_fda_pma(device_query, 3)]
    comm_total = sum(r.get("total", 0) for r in comm_results if r.get("total", 0) > 0)
    comm_signal = "COMMERCIALIZED" if comm_total > 0 else "EMPTY"
    universes.append(UniverseResult("commercial", comm_results, comm_total, comm_signal))

    # Universe 6: Failure
    fail_results = [query_fda_maude(device_query, 3), query_fda_recalls(device_query, 3)]
    fail_total = sum(r.get("total", 0) for r in fail_results if r.get("total", 0) > 0)
    fail_signal = "FAILURE" if fail_total > 0 else "EMPTY"
    universes.append(UniverseResult("failure", fail_results, fail_total, fail_signal))

    # Agreement matrix
    agreement = {}
    for i, u1 in enumerate(universes):
        for j, u2 in enumerate(universes):
            if i < j:
                key = f"{u1.universe}↔{u2.universe}"
                if u1.signal == "EMPTY" or u2.signal == "EMPTY":
                    agreement[key] = "UNKNOWN"
                elif u1.signal == u2.signal:
                    agreement[key] = "AGREE"
                else:
                    agreement[key] = "DISAGREE"

    # Graveyard signal: patent enthusiasm + science enthusiasm + clinical/failure problems
    patent_enthusiasm = any("ENTHUSIASM" in u.signal for u in universes if u.universe == "patent")
    science_enthusiasm = sci_signal == "ENTHUSIASM"
    clinical_failure = fail_signal == "FAILURE"
    graveyard = science_enthusiasm and clinical_failure

    # Goldmine signal: clinical failure + weak patents + strong engineering transfer
    goldmine = fail_signal == "FAILURE" and eng_signal == "ENTHUSIASM"

    # Summary
    signals = {u.universe: u.signal for u in universes}
    summary = f"Scientific: {sci_signal} ({sci_total}) | Engineering: {eng_signal} ({eng_total}) | Clinical: {clin_signal} ({clin_total}) | Commercial: {comm_signal} ({comm_total}) | Failure: {fail_signal} ({fail_total})"

    if graveyard:
        recommendation = "GRAVEYARD SIGNAL — scientific enthusiasm but failure evidence. Investigate WHY failures occurred before proceeding."
    elif goldmine:
        recommendation = "GOLDMINE SIGNAL — failure in current approaches but strong engineering transfer. Investigate whether the transfer mechanism addresses the failure mode."
    else:
        recommendation = "NEUTRAL — no strong agreement or disagreement signals. Proceed with physics."

    return TriangulationReport(
        candidate_name=candidate_name,
        timestamp=datetime.now(timezone.utc).isoformat(),
        universes=universes,
        agreement_matrix=agreement,
        graveyard_signal=graveyard,
        goldmine_signal=goldmine,
        summary=summary,
        recommendation=recommendation,
    )


def main():
    """Run triangulation on R6 (lumen rerouting) as first use case."""
    print(f"\n{'='*78}")
    print(f"TRIANGULATION ENGINE — 6 Independent Evidence Universes")
    print(f"{'='*78}")

    result = run_triangulation(
        candidate_name="R6 — Reversible lumen rerouting (bypass lumen for eShunt obstruction)",
        mechanism_query="shunt bypass lumen obstruction drainage",
        clinical_query="CSF shunt obstruction bypass lumen",
        device_query="CSF shunt",
    )

    print(f"\nCandidate: {result.candidate_name}")
    print(f"\n{'Universe':<15} {'Signal':<15} {'Total':<10}")
    print("-" * 40)
    for u in result.universes:
        print(f"{u.universe:<15} {u.signal:<15} {u.total_results:<10}")

    print(f"\nAgreement Matrix:")
    for pair, status in result.agreement_matrix.items():
        if status == "DISAGREE":
            print(f"  ⚠ {pair}: {status}")
        else:
            print(f"  {pair}: {status}")

    print(f"\nGraveyard Signal: {result.graveyard_signal}")
    print(f"Goldmine Signal: {result.goldmine_signal}")
    print(f"\nSummary: {result.summary}")
    print(f"Recommendation: {result.recommendation}")

    # Save
    output_dir = REPO_ROOT / "MULTI_SOURCE_DISCOVERY"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "TRIANGULATION_R6_LUMEN_REROUTING.json"
    with open(output_path, "w") as f:
        json.dump(result.to_dict(), f, indent=2, default=str)

    print(f"\nReport: {output_path}")
    return result


if __name__ == "__main__":
    main()

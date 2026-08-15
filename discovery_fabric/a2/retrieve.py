"""A2 retrieval — Europe PMC search → EvidenceItem."""
from __future__ import annotations
import json, re, hashlib, ssl, time, urllib.request, urllib.parse
from datetime import datetime, timezone

_SSL = ssl.create_default_context()
_SSL.check_hostname = False
_SSL.verify_mode = ssl.CERT_NONE

def search_europe_pmc(query: str, per_page: int = 5) -> list[dict]:
    try:
        encoded = urllib.parse.quote(query)
        url = (f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={encoded}"
               f"&format=json&pageSize={per_page}&resultType=core")
        req = urllib.request.Request(url, headers={"User-Agent": "A2-Discovery/1.0"})
        resp = urllib.request.urlopen(req, timeout=20, context=_SSL)
        data = json.loads(resp.read())
        items = []
        now = datetime.now(timezone.utc).isoformat()
        for r in data.get("resultList", {}).get("result", []):
            abstract = re.sub(r"<[^>]+>", " ", r.get("abstractText", "") or "")
            abstract = re.sub(r"\s+", " ", abstract).strip()
            if len(abstract) < 50: continue
            source_id = f"europepmc:{r.get('id', r.get('pmid', ''))}"
            core = {"source_id": source_id, "title": r.get("title", ""), "doi": r.get("doi", ""), "pub_date": r.get("firstPublicationDate", "")}
            content_hash = hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()
            items.append({
                "id": source_id, "source_type": "scientific_paper", "source": "EuropePMC",
                "source_id": source_id, "source_uri": f"https://europepmc.org/article/{r.get('id', '')}",
                "title": r.get("title", "") or "", "abstract": abstract[:2000],
                "doi": r.get("doi", "") or None, "publication_date": r.get("firstPublicationDate", "") or None,
                "retrieval_timestamp": now, "retrieval_method": "europepmc_api", "content_hash": content_hash,
                "provenance": {"provider": "EuropePMC", "retrieved_at": now, "query_or_method": query, "api_version": "rest"},
                "epistemic_state": "OBSERVED",
            })
        return items
    except Exception:
        return []

def retrieve(problem: dict) -> list[dict]:
    fm = problem.get("failure_mode", "MECHANICAL_FAILURE")
    query = f"{problem.get('device', '')} {fm.lower().replace('_', ' ')} mechanism".strip()
    print(f"  [retrieve] query: {query}")
    items = search_europe_pmc(query, per_page=5)
    time.sleep(1.0)
    print(f"  [retrieve] found {len(items)} evidence items")
    return items

"""
PatSnap Intelligence Layer V1
==============================

Implements CEO directive: PatSnap as primary evidence substrate.

Architecture:
  COUNT → DISCOVERY → SEMANTIC RANKING → FAMILY COLLAPSE → RELEVANCE → CLAIMS → DEEP EVIDENCE

Capabilities:
  1. Discovery: assignee search, query search, family collapse, pagination
  2. Semantic: similar patent search (P007)
  3. Evidence: claims (batch), legal status, citations, description offsets
  4. Family/citation expansion
  5. Company intelligence

Governance:
  - LLM facts = hypotheses. Retrieved text = evidence.
  - Keyword = discovery, not claim evidence.
  - Three graphs: technology, ownership, buyer. Never merge.
  - Every conclusion traces to evidence_id → primary source.
"""
from __future__ import annotations
import os, sys, json, ssl, urllib.request, urllib.error, urllib.parse, re, hashlib, time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()

def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

def _load_api_key() -> str:
    keys_file = Path(__file__).resolve().parents[2] / ".env.keys"
    if not keys_file.exists():
        return ""
    for line in keys_file.read_text().splitlines():
        if line.startswith("PATSNAP_EUREKA_API_KEY="):
            return line.split("=", 1)[1].strip()
    return ""

_BASE = "https://connect.patsnap.com"
_KEY = ""
_SSL = None

def _init():
    global _KEY, _SSL
    if not _KEY:
        _KEY = _load_api_key()
        _SSL = ssl.create_default_context()
        _SSL.check_hostname = False
        _SSL.verify_mode = ssl.CERT_NONE

def _get(path: str, params: Dict = None) -> Tuple[int, dict, str]:
    _init()
    url = _BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, method="GET", headers={
            "Authorization": f"Bearer {_KEY}", "Accept": "application/json"})
        resp = urllib.request.urlopen(req, timeout=20, context=_SSL)
        return resp.status, json.loads(resp.read()), ""
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")[:300]
        try:
            return e.code, json.loads(body), f"HTTP {e.code}"
        except:
            return e.code, {}, body
    except Exception as e:
        return 0, {}, str(e)[:200]

def _post(path: str, payload: dict) -> Tuple[int, dict, str]:
    _init()
    url = _BASE + path
    data = json.dumps(payload).encode()
    try:
        req = urllib.request.Request(url, data=data, method="POST", headers={
            "Authorization": f"Bearer {_KEY}", "Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=20, context=_SSL)
        return resp.status, json.loads(resp.read()), ""
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")[:300]
        try:
            return e.code, json.loads(body), f"HTTP {e.code}"
        except:
            return e.code, {}, body
    except Exception as e:
        return 0, {}, str(e)[:200]


# ============================================================
# PRIORITY 1: DISCOVERY
# ============================================================

def assignee_search(assignee: str, limit: int = 100, offset: int = 0) -> Dict:
    """P005: Current assignee search. Returns patent IDs and metadata."""
    status, data, err = _post("/search/patent/current-search-patent", {
        "assignee": assignee, "limit": limit, "offset": offset
    })
    if not data.get("status"):
        return {"error": err or data.get("error_msg", "unknown"), "patents": []}
    d = data.get("data", {})
    patents = d.get("patents", d.get("list", d.get("results", [])))
    total = d.get("total_search_result_count", 0)
    return {"total": total, "returned": len(patents), "patents": patents}


def assignee_search_all(assignee: str, max_results: int = 1000) -> List[Dict]:
    """Paginate through all results from assignee search."""
    all_pats = []
    offset = 0
    while offset < max_results:
        result = assignee_search(assignee, limit=100, offset=offset)
        if result.get("error"):
            break
        pats = result.get("patents", [])
        if not pats:
            break
        all_pats.extend(pats)
        total = result.get("total", 0)
        if offset + len(pats) >= total:
            break
        offset += 100
        time.sleep(0.3)
    return all_pats


def query_search_count(query: str, collapse_by: str = "DOCDB") -> int:
    """P003: Query search count. Returns total result count."""
    status, data, err = _post("/search/patent/query-search-count/v2", {
        "query_text": query, "collapse_by": collapse_by,
        "collapse_type": "ALL", "collapse_order": "LATEST"
    })
    if not data.get("status"):
        return 0
    return data.get("data", {}).get("total_search_result_count", 0)


def query_search_multi_collapse(query: str) -> Dict[str, int]:
    """Run same query with different collapse modes."""
    results = {}
    for mode in ["PBD", "DOCDB", "INPADOC", "EXTEND"]:
        results[mode] = query_search_count(query, collapse_by=mode)
        time.sleep(0.2)
    return results


# ============================================================
# PRIORITY 2: SEMANTIC HOSTILE SEARCH
# ============================================================

def similar_patents(patent_number: str, limit: int = 20) -> Dict:
    """P007: Find patents similar to a given patent number."""
    status, data, err = _post("/search/patent/similar-search-patent", {
        "patent_number": patent_number, "limit": limit
    })
    if not data.get("status"):
        return {"error": err or data.get("error_msg", "unknown"), "results": []}
    d = data.get("data", {})
    results = d.get("results", [])
    total = d.get("total_search_result_count", 0)
    return {"total": total, "returned": len(results), "results": results}


def semantic_hostile_search(target_patents: List[str]) -> Dict:
    """Run similar patent search for multiple target patents.
    
    Per CEO: find inventions most similar to ours, achieving the same
    technical effect through different mechanisms, solving the same
    problem without our architecture, and substitutable for each limitation.
    """
    all_similar = {}
    for pn in target_patents:
        result = similar_patents(pn, limit=20)
        if result.get("results"):
            all_similar[pn] = result
        time.sleep(0.3)
    return all_similar


# ============================================================
# PRIORITY 3: EVIDENCE ENRICHMENT
# ============================================================

def get_claims(patent_number: str) -> Optional[Dict]:
    """P018: Retrieve patent claims."""
    status, data, err = _get("/basic-patent-data/claim-data", 
                            {"patent_number": patent_number})
    if not data.get("status"):
        return None
    records = data.get("data", [])
    if not records:
        return None
    r = records[0]
    raw_html = r.get("claims", [{}])[0].get("claim_text", "") if r.get("claims") else ""
    text = re.sub(r"<[^>]+>", " ", raw_html)
    text = re.sub(r"\s+", " ", text).strip()
    
    claims = []
    parts = re.split(r"(?=\b\d+\.\s+[A-Z])", text)
    for p in parts:
        p = p.strip()
        if re.match(r"^\d+\.\s+", p) and len(p) > 10:
            claims.append(p[:3000])
    
    return {
        "patent_number": patent_number,
        "patent_id": r.get("patent_id", ""),
        "claim_count": r.get("claim_count", len(claims)),
        "independent_claim_count": r.get("claims", [{}])[0].get("claim_independent_count", 0) if r.get("claims") else 0,
        "claims": claims,
        "content_hash": _sha256(raw_html)[:16],
        "retrieved_at": _now_utc(),
    }


def get_claims_batch(patent_numbers: List[str]) -> List[Dict]:
    """Batch retrieve claims for multiple patents."""
    results = []
    for pn in patent_numbers:
        rec = get_claims(pn)
        if rec:
            results.append(rec)
        time.sleep(0.2)
    return results


def get_legal_status(patent_number: str) -> Optional[Dict]:
    """P013: Retrieve legal status."""
    status, data, err = _get("/basic-patent-data/legal-status",
                            {"patent_number": patent_number})
    if not data.get("status"):
        return None
    records = data.get("data", [])
    if not records:
        return None
    r = records[0]
    legal = r.get("patent_legal", {})
    return {
        "patent_number": patent_number,
        "simple_legal_status": legal.get("simple_legal_status", []),
        "legal_status": legal.get("legal_status", []),
        "legal_date": r.get("legal_date"),
    }


def get_citations(patent_number: str) -> Optional[Dict]:
    """P015: Retrieve citation graph (forward + backward)."""
    status, data, err = _get("/basic-patent-data/backward-citation",
                            {"patent_number": patent_number})
    if not data.get("status"):
        return None
    records = data.get("data", [])
    if not records:
        return None
    r = records[0]
    patent_cited = r.get("patent_cited", {})
    
    cited_by = patent_cited.get("cited_by_patents", [])  # forward citations
    citations = patent_cited.get("citations", [])  # backward citations
    
    def normalize_cite(c):
        return f"{c.get('country','')}{c.get('doc_number','')}{c.get('kind','')}"
    
    return {
        "patent_number": patent_number,
        "forward_citations": [normalize_cite(c) for c in cited_by],
        "forward_count": len(cited_by),
        "backward_citations": [normalize_cite(c) for c in citations],
        "backward_count": len(citations),
    }


def get_description_offsets(patent_number: str) -> Optional[Dict]:
    """P073: Retrieve description section offsets."""
    status, data, err = _get("/basic-patent-data/description-offset",
                            {"patent_number": patent_number})
    if not data.get("status"):
        return None
    d = data.get("data", {})
    sections = d.get("sections", [])
    return {
        "patent_number": patent_number,
        "section_count": len(sections),
        "sections": [
            {
                "name": s.get("section_name", {}).get("text", "").strip(),
                "category": s.get("section_name", {}).get("category_name", []),
                "start": s.get("section_content", {}).get("idx_start", 0),
                "end": s.get("section_content", {}).get("idx_end", 0),
            }
            for s in sections
        ],
    }


# ============================================================
# PRIORITY 4: FAMILY/CITATION EXPANSION
# ============================================================

def expand_citation_neighborhood(patent_number: str, depth: int = 1) -> Dict:
    """Expand citation neighborhood for a patent."""
    citations = get_citations(patent_number)
    if not citations:
        return {"patent_number": patent_number, "forward": [], "backward": []}
    
    result = {
        "patent_number": patent_number,
        "forward": citations["forward_citations"][:20],  # limit
        "backward": citations["backward_citations"][:20],
        "forward_count": citations["forward_count"],
        "backward_count": citations["backward_count"],
    }
    
    if depth > 1:
        # Expand one level deeper for top forward citations
        for fc in result["forward"][:5]:
            sub = get_citations(fc)
            if sub:
                result[f"forward_{fc}"] = sub["forward_citations"][:10]
            time.sleep(0.2)
    
    return result


# ============================================================
# PRIORITY 5: COMPANY INTELLIGENCE
# ============================================================

@dataclass
class CompanyIntelligence:
    """Company-level intelligence object."""
    company_name: str
    total_patents: int = 0
    us_patents: int = 0
    granted: int = 0
    pending: int = 0
    abandoned: int = 0
    expired: int = 0
    patent_numbers: List[str] = field(default_factory=list)
    families: Dict[str, List[str]] = field(default_factory=dict)
    technology_clusters: Dict[str, List[str]] = field(default_factory=dict)
    citation_graph: Dict[str, Dict] = field(default_factory=dict)
    legal_status_map: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self):
        return asdict(self)


def build_company_intelligence(company_name: str, max_patents: int = 200) -> CompanyIntelligence:
    """Build complete company intelligence from PatSnap."""
    ci = CompanyIntelligence(company_name=company_name)
    
    # 1. Get all patents via assignee search
    print(f"Searching for {company_name} patents...")
    patents = assignee_search_all(company_name, max_results=max_patents)
    ci.total_patents = len(patents)
    
    # Extract patent numbers
    pns = []
    for p in patents:
        pn = p.get("pn", p.get("patent_number", p.get("publication_number", "")))
        if pn:
            pns.append(pn)
    ci.patent_numbers = pns
    
    # Count by country
    ci.us_patents = sum(1 for pn in pns if pn.startswith("US"))
    
    print(f"  Found {ci.total_patents} patents ({ci.us_patents} US)")
    
    # 2. Get legal status for US granted patents (batch, but individual for now)
    us_granted = [pn for pn in pns if pn.startswith("US") and "B" in pn[-2:]]
    print(f"  Getting legal status for {len(us_granted)} US granted patents...")
    
    for pn in us_granted[:30]:  # limit to 30 to manage time
        ls = get_legal_status(pn)
        if ls:
            status_str = ",".join(ls.get("simple_legal_status", ["UNKNOWN"]))
            ci.legal_status_map[pn] = status_str
            if "Active" in status_str:
                ci.granted += 1
            elif "Abandoned" in status_str or "Withdrawn" in status_str:
                ci.abandoned += 1
            elif "Expired" in status_str or "Lapsed" in status_str:
                ci.expired += 1
        time.sleep(0.2)
    
    # 3. Get citations for key patents
    key_patents = us_granted[:5]  # top 5
    print(f"  Getting citations for {len(key_patents)} key patents...")
    
    for pn in key_patents:
        cite = expand_citation_neighborhood(pn, depth=1)
        ci.citation_graph[pn] = cite
        time.sleep(0.3)
    
    # 4. Get similar patents for key patents
    print(f"  Getting similar patents for {len(key_patents)} key patents...")
    for pn in key_patents:
        sim = similar_patents(pn, limit=20)
        if sim.get("results"):
            ci.technology_clusters[pn] = [r.get("pn", "") for r in sim["results"] if r.get("pn")]
        time.sleep(0.3)
    
    return ci


# ============================================================
# EVIDENCE LEDGER
# ============================================================

@dataclass
class EvidenceItem:
    """Single evidence item with full provenance."""
    evidence_id: str
    source: str  # "PatSnap_P018", "PatSnap_P015", etc.
    patent_number: str
    patent_id: str = ""
    family_id: str = ""
    claim_number: str = ""
    exact_passage: str = ""
    content_hash: str = ""
    retrieval_timestamp: str = ""
    analysis_model: str = ""
    analysis_version: str = ""


class EvidenceLedger:
    """Manages all evidence with provenance tracking."""
    
    def __init__(self):
        self.items: List[EvidenceItem] = []
        self.counter = 0
    
    def add(self, source: str, patent_number: str, exact_passage: str = "",
            patent_id: str = "", family_id: str = "", claim_number: str = "",
            content_hash: str = "", model: str = "", version: str = "") -> str:
        self.counter += 1
        eid = f"EV_{self.counter:04d}"
        self.items.append(EvidenceItem(
            evidence_id=eid, source=source, patent_number=patent_number,
            patent_id=patent_id, family_id=family_id, claim_number=claim_number,
            exact_passage=exact_passage[:500], content_hash=content_hash,
            retrieval_timestamp=_now_utc(), analysis_model=model,
            analysis_version=version,
        ))
        return eid
    
    def to_dict(self) -> List[Dict]:
        return [asdict(item) for item in self.items]
    
    def verify_chain(self, conclusion_evidence_id: str) -> bool:
        """Verify that a conclusion traces to primary source."""
        for item in self.items:
            if item.evidence_id == conclusion_evidence_id:
                return bool(item.patent_number and item.exact_passage)
        return False

"""
V5 Patent Discovery — Union Historical + Fresh Search (FIXED)
==============================================================
Fixes:
  1. Family collapse: country code ≠ family. Set NOT_AVAILABLE when no metadata.
  2. Relevance fallback: NO fallback to unique_ids when no DIRECTLY_RELEVANT.
"""
from __future__ import annotations
import os, sys, json, re, time, hashlib
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.prior_art_v2.patsnap_claims import fetch_patsnap_claims
from discovery_fabric.prior_art_v2.source_failover import patsnap_search_count
from discovery_fabric.prior_art_v2.elite_v3 import LLMClient, _now_utc, _sha256


@dataclass
class PatentIDWithProvenance:
    patent_id: str
    source: str = ""
    origin: str = ""
    query_id: str = ""
    retrieval_timestamp: str = ""
    relevance: str = "UNCLEAR"
    family_id: Optional[str] = None  # Only set when verified


@dataclass
class DiscoveryMatrix:
    invention_id: str = ""
    query_families: List[Dict[str, Any]] = field(default_factory=list)
    all_patent_ids: List[PatentIDWithProvenance] = field(default_factory=list)
    unique_patent_ids: List[str] = field(default_factory=list)

    # FIX 1: family_collapse = NOT_AVAILABLE when no family metadata
    family_resolution_status: str = "NOT_AVAILABLE"  # RESOLVED / NOT_AVAILABLE
    family_collapsed: List[str] = field(default_factory=list)  # empty if NOT_AVAILABLE

    # Freshness
    historical_only: List[str] = field(default_factory=list)
    fresh_only: List[str] = field(default_factory=list)
    overlap: List[str] = field(default_factory=list)

    # Sources
    sources_used: List[str] = field(default_factory=list)
    sources_failed: List[str] = field(default_factory=list)
    fresh_search_attempted: bool = False
    fresh_search_status: str = "NOT_ATTEMPTED"

    # PatSnap count (discovery signal only)
    patsnap_count: Optional[int] = None

    # FIX 2: No fallback. directly_relevant_ids stays empty if no DIRECTLY_RELEVANT found.
    directly_relevant_ids: List[str] = field(default_factory=list)

    timestamp: str = ""


class V5DiscoveryRouter:
    """Union discovery: historical + fresh, no suppression, no fallback."""

    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or LLMClient()

    def discover(self, invention_id: str, claim_text: str,
                 device_class: str = "") -> DiscoveryMatrix:
        matrix = DiscoveryMatrix(invention_id=invention_id, timestamp=_now_utc())

        queries = self._generate_queries(claim_text, device_class)
        matrix.query_families = [{"query_id": q[0], "query": q[1]} for q in queries]

        all_ids: List[PatentIDWithProvenance] = []

        # Source 1: Historical (V4 stored)
        historical_ids = self._get_historical_ids(invention_id)
        for pid in historical_ids:
            all_ids.append(PatentIDWithProvenance(
                patent_id=pid, source="V4_HISTORICAL", origin="HISTORICAL",
                retrieval_timestamp=_now_utc()))
        if historical_ids:
            matrix.sources_used.append("V4_HISTORICAL")

        # Source 2: Fresh — Google Patents
        matrix.fresh_search_attempted = True
        google_ids = self._try_google(claim_text[:200])
        if google_ids:
            for pid in google_ids:
                all_ids.append(PatentIDWithProvenance(
                    patent_id=pid, source="GOOGLE_PATENTS", origin="FRESH",
                    retrieval_timestamp=_now_utc()))
            matrix.sources_used.append("GOOGLE_PATENTS")
            matrix.fresh_search_status = "IDS_FOUND"
        else:
            matrix.sources_failed.append("GOOGLE_PATENTS")
            matrix.fresh_search_status = "FAILED"

        # Source 3: PatSnap count (discovery signal only)
        count = patsnap_search_count(claim_text[:200])
        if count is not None and count > 0:
            matrix.patsnap_count = count
            matrix.sources_used.append("PATSNAP_COUNT")

        # Source 4: Patent Bear
        pb_ids = self._try_patent_bear(claim_text[:200])
        if pb_ids:
            for pid in pb_ids:
                all_ids.append(PatentIDWithProvenance(
                    patent_id=pid, source="PATENT_BEAR", origin="FRESH",
                    retrieval_timestamp=_now_utc()))
            matrix.sources_used.append("PATENT_BEAR")
        else:
            matrix.sources_failed.append("PATENT_BEAR")

        # UNION + dedup
        seen = set()
        for p in all_ids:
            if p.patent_id not in seen:
                seen.add(p.patent_id)
                matrix.all_patent_ids.append(p)
                matrix.unique_patent_ids.append(p.patent_id)

        # Freshness analysis
        h_set = {p.patent_id for p in all_ids if p.origin == "HISTORICAL"}
        f_set = {p.patent_id for p in all_ids if p.origin == "FRESH"}
        matrix.historical_only = list(h_set - f_set)
        matrix.fresh_only = list(f_set - h_set)
        matrix.overlap = list(h_set & f_set)

        # FIX 1: Family collapse — NO country-code-as-family
        # Real family requires family_id from patent metadata.
        # We don't have family metadata from the discovery step.
        # Therefore: family_resolution_status = NOT_AVAILABLE, family_collapsed = []
        matrix.family_resolution_status = "NOT_AVAILABLE"
        matrix.family_collapsed = []  # empty — no family metadata available

        # FIX 2: Relevance filter — NO FALLBACK
        # Only DIRECTLY_RELEVANT from V4 stored results enter the GOLD pool.
        # If no DIRECTLY_RELEVANT: directly_relevant_ids stays EMPTY.
        # This means GOLD = 0, which is the correct honest state.
        matrix.directly_relevant_ids = self._get_directly_relevant_ids(invention_id)
        # NO fallback to unique_patent_ids[:10] — this was the dangerous bug.

        return matrix

    def _generate_queries(self, claim: str, device: str) -> List[Tuple[str, str]]:
        words = re.findall(r'\b[a-z]{4,}\b', claim.lower())
        stopwords = {"comprising","wherein","configured","adapted","said","the","and","for","with","from","into","that","this","which","thereby"}
        keywords = [w for w in words if w not in stopwords][:5]
        base = device or " ".join(keywords[:2])
        mech = " ".join(keywords[2:4]) if len(keywords) >= 4 else keywords[0] if keywords else base
        return [
            ("Q1", f"{base} failure"), ("Q2", f"{base} {mech}"),
            ("Q3", f"{mech} structure"), ("Q4", f"material {mech}"),
            ("Q5", f"relationship {mech}"), ("Q6", f"technical effect {mech}"),
            ("Q7", f"{base} {mech} structure"), ("Q8", f"functional equivalent {base}"),
            ("Q9", f"structural equivalent {mech}"), ("Q10", f"CPC {base}"),
        ]

    def _get_historical_ids(self, invention_id: str) -> List[str]:
        p = REPO_ROOT / "patentability" / "retrieval_v4" / invention_id / "RETRIEVAL_RESULTS.json"
        if not p.exists(): return []
        d = json.loads(p.read_text())
        ids = [rp.get("patent_id") for rp in d.get("retrieved_patents",[]) if rp.get("patent_id")]
        return list(dict.fromkeys(ids))

    def _get_directly_relevant_ids(self, invention_id: str) -> List[str]:
        """Only DIRECTLY_RELEVANT from V4. NO fallback."""
        p = REPO_ROOT / "patentability" / "retrieval_v4" / invention_id / "RETRIEVAL_RESULTS.json"
        if not p.exists(): return []
        d = json.loads(p.read_text())
        ids = []
        for rp in d.get("retrieved_patents", []):
            if rp.get("relevance", {}).get("relevance_level") == "DIRECTLY_RELEVANT":
                pid = rp.get("patent_id")
                if pid: ids.append(pid)
        return list(dict.fromkeys(ids))

    def _try_google(self, query: str) -> List[str]:
        from discovery_fabric.prior_art_v2.sources import search_google_patents
        try:
            result = search_google_patents(query, 5)
            if result.success:
                return [h.patent_id for h in result.hits if h.patent_id]
        except: pass
        return []

    def _try_patent_bear(self, query: str) -> List[str]:
        from discovery_fabric.prior_art_v2.sources import search_patent_bear
        try:
            result = search_patent_bear(query, 5)
            if result.success:
                return [h.patent_id for h in result.hits if h.patent_id]
        except: pass
        return []

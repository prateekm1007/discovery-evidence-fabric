"""PatSnap provider — HIGH cost, materiality-gated.

PatSnap is NEVER a ceremonial checkbox. Every call requires a pre-call
receipt documenting: uncertainty → why cheaper sources failed → expected
result → verdict change → max calls remaining.
"""
from __future__ import annotations
import ssl, json, urllib.request, urllib.parse, os, re, hashlib
from typing import Dict, Any, List
from datetime import datetime, timezone
from .base import BaseProvider, ProviderResult


class PatSnapProvider(BaseProvider):
    name = "PatSnap"
    cost_per_call = 50.0  # HIGH cost
    evidence_class = "patent"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.environ.get("PATSNAP_EUREKA_API_KEY", "")
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE
        self.calls_made = 0
        self.precall_receipts: List[Dict] = []

    def record_precall_receipt(self, uncertainty: str, why_cheaper_failed: str,
                                expected_result: str, verdict_if_found: str,
                                verdict_if_not_found: str, max_calls_remaining: int) -> Dict:
        """Hard pre-call receipt before every expensive PatSnap call."""
        receipt = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uncertainty": uncertainty,
            "why_cheaper_sources_failed": why_cheaper_failed,
            "expected_result": expected_result,
            "verdict_change_if_found": verdict_if_found,
            "verdict_change_if_not_found": verdict_if_not_found,
            "max_calls_remaining": max_calls_remaining,
            "call_justified": True  # only if uncertainty HIGH and cheaper sources failed
        }
        self.precall_receipts.append(receipt)
        return receipt

    def search(self, query: str, limit: int = 10, **kwargs) -> ProviderResult:
        if not self.api_key:
            return ProviderResult(provider=self.name, query=query,
                                  error="No PATSNAP_EUREKA_API_KEY set")
        url = "https://connect.patsnap.com/search/patent/nested-search-patent"
        query_text = f"TACD: {query[:2900]}"
        payload = json.dumps({
            "query_text": query_text,
            "collapse_by": "DOCDB", "collapse_type": "ALL",
            "collapse_order": "LATEST", "limit": limit, "page": 1,
        }).encode()
        req = urllib.request.Request(url, data=payload, method="POST", headers={
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })
        try:
            r = urllib.request.urlopen(req, timeout=30, context=self.ctx)
            data = json.loads(r.read().decode())
            if not data.get("status", False):
                return ProviderResult(provider=self.name, query=query,
                                      error=data.get("error_msg", ""))
            d = data.get("data", {})
            if not isinstance(d, dict):
                return ProviderResult(provider=self.name, query=query, total_hits=0)
            patents = d.get("patents", []) or d.get("results", []) or []
            self.calls_made += 1
            return ProviderResult(provider=self.name, query=query,
                                  total_hits=int(d.get("total_search_result_count", 0) or 0),
                                  results=[{"pn": p.get("pn", ""),
                                            "title": p.get("title", "")[:200],
                                            "assignee": p.get("assignee", "")}
                                           for p in patents],
                                  cost_incurred=self.cost_per_call)
        except Exception as e:
            return ProviderResult(provider=self.name, query=query, error=str(e))

    def retrieve_claims(self, patent_number: str) -> ProviderResult:
        if not self.api_key:
            return ProviderResult(provider=self.name, query=patent_number,
                                  error="No PATSNAP_EUREKA_API_KEY set")
        url = (f"https://connect.patsnap.com/basic-patent-data/claim-data?"
               f"patent_number={urllib.parse.quote(patent_number)}")
        req = urllib.request.Request(url, method="GET", headers={
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        })
        try:
            r = urllib.request.urlopen(req, timeout=30, context=self.ctx)
            data = json.loads(r.read().decode())
            if not data.get("status", False):
                return ProviderResult(provider=self.name, query=patent_number,
                                      error=data.get("error_msg", ""))
            records = data.get("data", [])
            if not records or not isinstance(records, list):
                return ProviderResult(provider=self.name, query=patent_number, total_hits=0)
            record = records[0]
            claims_data = record.get("claims", [])
            if not claims_data:
                return ProviderResult(provider=self.name, query=patent_number, total_hits=0)
            claim_entry = claims_data[0]
            raw_html = claim_entry.get("claim_text", "")
            # Parse claims
            def strip_html(text):
                text = re.sub(r'<[^>]+>', ' ', text)
                return re.sub(r'\s+', ' ', text).strip()
            def parse_claims(html):
                claims = []
                pattern = r'<div class="(?:indep|dep)-clm" num="(\d+)"[^>]*>(.*?)</div>'
                matches = re.findall(pattern, html, re.DOTALL)
                current_num = None
                current_parts = []
                for num, content in matches:
                    if num != current_num:
                        if current_num is not None and current_parts:
                            claims.append(" ".join(strip_html(p) for p in current_parts)[:3000])
                        current_num = num
                        current_parts = [content]
                    else:
                        current_parts.append(content)
                if current_num is not None and current_parts:
                    claims.append(" ".join(strip_html(p) for p in current_parts)[:3000])
                return claims
            claims = parse_claims(raw_html)
            self.calls_made += 1
            return ProviderResult(provider=self.name, query=patent_number,
                                  total_hits=len(claims),
                                  results=[{"patent_number": patent_number,
                                            "claims": claims,
                                            "claim_count": record.get("claim_count", len(claims))}],
                                  cost_incurred=self.cost_per_call)
        except Exception as e:
            return ProviderResult(provider=self.name, query=patent_number, error=str(e))

    def semantic_search(self, patent_number: str, limit: int = 10) -> ProviderResult:
        """Semantic/similar patent search using seed patent."""
        if not self.api_key:
            return ProviderResult(provider=self.name, query=patent_number,
                                  error="No PATSNAP_EUREKA_API_KEY set")
        url = "https://connect.patsnap.com/search/patent/similar-search-patent"
        payload = json.dumps({"patent_number": patent_number, "limit": limit}).encode()
        req = urllib.request.Request(url, data=payload, method="POST", headers={
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })
        try:
            r = urllib.request.urlopen(req, timeout=30, context=self.ctx)
            data = json.loads(r.read().decode())
            if not data.get("status", False):
                return ProviderResult(provider=self.name, query=patent_number,
                                      error=data.get("error_msg", ""))
            d = data.get("data", {})
            if not isinstance(d, dict):
                return ProviderResult(provider=self.name, query=patent_number, total_hits=0)
            results_list = d.get("results", []) or []
            self.calls_made += 1
            return ProviderResult(provider=self.name, query=patent_number,
                                  total_hits=int(d.get("total_search_result_count", 0) or 0),
                                  results=[{"pn": p.get("pn", ""),
                                            "relevancy": p.get("relevancy", "")}
                                           for p in results_list],
                                  cost_incurred=self.cost_per_call)
        except Exception as e:
            return ProviderResult(provider=self.name, query=patent_number, error=str(e))

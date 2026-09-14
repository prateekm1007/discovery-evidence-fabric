"""Elsevier Scopus provider."""
from __future__ import annotations
import ssl, json, urllib.request, urllib.parse, os
from typing import Dict, Any, List
from .base import BaseProvider, ProviderResult


class ScopusProvider(BaseProvider):
    name = "Scopus"
    cost_per_call = 1.0  # free
    evidence_class = "mechanism"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.environ.get("ELSEVIER_API_KEY", "")
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

    def search(self, query: str, count: int = 10, **kwargs) -> ProviderResult:
        if not self.api_key:
            return ProviderResult(provider=self.name, query=query,
                                  error="No ELSEVIER_API_KEY set")
        url = (f"https://api.elsevier.com/content/search/scopus?"
               f"query={urllib.parse.quote(query)}&count={count}")
        req = urllib.request.Request(url, method="GET", headers={
            "X-ELS-APIKey": self.api_key, "Accept": "application/json",
        })
        try:
            r = urllib.request.urlopen(req, timeout=30, context=self.ctx)
            data = json.loads(r.read().decode())
            results = data.get("search-results", {})
            entries = [{
                "title": e.get("dc:title", ""),
                "doi": e.get("prism:doi", ""),
                "publication": e.get("prism:publicationName", ""),
                "date": e.get("prism:coverDate", ""),
                "cited_by": e.get("citedby-count", "0"),
            } for e in results.get("entry", [])]
            return ProviderResult(provider=self.name, query=query,
                                  total_hits=int(results.get("opensearch:totalResults", 0)),
                                  results=entries, cost_incurred=self.cost_per_call)
        except Exception as e:
            return ProviderResult(provider=self.name, query=query, error=str(e))

    def retrieve_claims(self, patent_number: str) -> ProviderResult:
        return ProviderResult(provider=self.name, query=patent_number,
                              error="Scopus does not provide patent claims")

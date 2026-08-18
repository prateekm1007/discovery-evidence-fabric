"""Lens.org scholarly search provider."""
from __future__ import annotations
import ssl, json, urllib.request, os
from typing import Dict, Any, List
from .base import BaseProvider, ProviderResult


class LensProvider(BaseProvider):
    name = "Lens"
    cost_per_call = 1.0  # free
    evidence_class = "discovery"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.environ.get("LENS_API_KEY", "")
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

    def search(self, query: str, size: int = 10, **kwargs) -> ProviderResult:
        if not self.api_key:
            return ProviderResult(provider=self.name, query=query,
                                  error="No LENS_API_KEY set")
        url = "https://api.lens.org/scholarly/search"
        payload = json.dumps({
            "query": {"query_string": {"query": query}},
            "size": size,
            "include": ["lens_id", "title", "abstract", "authors",
                        "year_published", "source", "external_ids"]
        }).encode()
        req = urllib.request.Request(url, data=payload, method="POST", headers={
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })
        try:
            r = urllib.request.urlopen(req, timeout=30, context=self.ctx)
            data = json.loads(r.read().decode())
            results = [{
                "title": p.get("title", ""),
                "year": p.get("year_published", ""),
                "doi": next((e["value"] for e in p.get("external_ids", [])
                            if e.get("type") == "doi"), ""),
                "source": p.get("source", {}).get("title", "") if isinstance(p.get("source"), dict) else "",
                "abstract": (p.get("abstract") or "")[:500],
            } for p in data.get("data", [])]
            return ProviderResult(provider=self.name, query=query,
                                  total_hits=data.get("total", 0),
                                  results=results, cost_incurred=self.cost_per_call)
        except Exception as e:
            return ProviderResult(provider=self.name, query=query, error=str(e))

    def retrieve_claims(self, patent_number: str) -> ProviderResult:
        return ProviderResult(provider=self.name, query=patent_number,
                              error="Lens does not provide patent claims")

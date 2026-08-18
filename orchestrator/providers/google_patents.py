"""Google Patents provider (via agent-browser)."""
from __future__ import annotations
import subprocess, time, json, re
from typing import Dict, Any, List
from .base import BaseProvider, ProviderResult


class GooglePatentsProvider(BaseProvider):
    name = "GooglePatents"
    cost_per_call = 1.0  # free
    evidence_class = "discovery"

    def search(self, query: str, limit: int = 10, **kwargs) -> ProviderResult:
        url = f"https://patents.google.com/?q={query}"
        try:
            subprocess.run(["agent-browser", "open", url],
                           capture_output=True, text=True, timeout=60)
            time.sleep(5)
            result = subprocess.run(
                ["agent-browser", "eval",
                 "Array.from(document.querySelectorAll('a[href*=\"/patent/\"]'))"
                 ".slice(0," + str(limit) + ")"
                 ".map(a=>({pn:a.href.match(/\\/patent\\/([^/?#]+)/)?.[1]||'',"
                 "title:a.innerText.substring(0,200)}))",
                 ],
                capture_output=True, text=True, timeout=30
            )
            data = json.loads(result.stdout.strip().strip('"').replace('\\"', '"'))
            return ProviderResult(provider=self.name, query=query,
                                  total_hits=len(data), results=data,
                                  cost_incurred=self.cost_per_call)
        except Exception as e:
            return ProviderResult(provider=self.name, query=query, error=str(e))

    def retrieve_claims(self, patent_number: str) -> ProviderResult:
        url = f"https://patents.google.com/patent/{patent_number}/en"
        try:
            subprocess.run(["agent-browser", "open", url],
                           capture_output=True, text=True, timeout=60)
            time.sleep(3)
            result = subprocess.run(
                ["agent-browser", "eval",
                 "Array.from(document.querySelectorAll('section'))"
                 ".filter(s=>s.innerText.toLowerCase().includes('what is claimed'))"
                 ".map(s=>s.innerText.substring(0,20000)).join('\\n')"],
                capture_output=True, text=True, timeout=30
            )
            claims = result.stdout.strip()
            if claims.startswith('"'):
                claims = json.loads(claims)
            return ProviderResult(provider=self.name, query=patent_number,
                                  total_hits=1 if claims else 0,
                                  results=[{"patent_number": patent_number,
                                            "claims_text": claims}],
                                  cost_incurred=self.cost_per_call)
        except Exception as e:
            return ProviderResult(provider=self.name, query=patent_number, error=str(e))

"""PatentBear free web search provider (via agent-browser)."""
from __future__ import annotations
import subprocess, time, json, re, urllib.parse
from typing import Dict, Any, List
from .base import BaseProvider, ProviderResult


class PatentBearProvider(BaseProvider):
    name = "PatentBear"
    cost_per_call = 1.0  # free
    evidence_class = "hostile_prior_art"

    def search(self, query: str, limit: int = 10, **kwargs) -> ProviderResult:
        """Boolean search via PatentBear free public web search."""
        url = (f"https://www.patentbear.com/search?"
               f"k={urllib.parse.quote(query)}&m=boolean&"
               f"f=title,abstract,claims,descriptionText")
        try:
            subprocess.run(["agent-browser", "open", url],
                           capture_output=True, text=True, timeout=60)
            time.sleep(5)
            result = subprocess.run(
                ["agent-browser", "eval",
                 "(function(){var b=document.body.innerText;"
                 "var m=b.match(/([\\d,]+)\\s*hits/);"
                 "var t=m?m[1].replace(/,/g,''):'0';"
                 "var p=Array.from(document.querySelectorAll('a[href*=\"/patent/\"]'))"
                 ".map(a=>({pn:a.href.match(/\\/patents\\/([^/?#]+)/)?.[1]||'',"
                 "title:a.innerText.substring(0,200)}));"
                 "return JSON.stringify({total:t,patents:p.slice(0," + str(limit) + ")})})();"],
                capture_output=True, text=True, timeout=30
            )
            data = json.loads(result.stdout.strip().strip('"').replace('\\"', '"'))
            return ProviderResult(provider=self.name, query=query,
                                  total_hits=int(data.get("total", 0)),
                                  results=data.get("patents", []),
                                  cost_incurred=self.cost_per_call)
        except Exception as e:
            return ProviderResult(provider=self.name, query=query, error=str(e))

    def retrieve_claims(self, patent_number: str) -> ProviderResult:
        """Retrieve claims from PatentBear patent page."""
        url = f"https://www.patentbear.com/patents/{patent_number}"
        try:
            subprocess.run(["agent-browser", "open", url],
                           capture_output=True, text=True, timeout=60)
            time.sleep(5)
            result = subprocess.run(
                ["agent-browser", "eval",
                 "document.body.innerText.substring(0, 80000)"],
                capture_output=True, text=True, timeout=30
            )
            body = result.stdout.strip()
            if body.startswith('"'):
                body = json.loads(body)
            # Extract claims section
            claims_match = re.search(r'CLAIMS\s*\(\d+\)(.+?)(?=\nDESCRIPTION|\nFIGURES|\nABSTRACT|$)',
                                     body, re.DOTALL)
            claims_text = claims_match.group(1).strip()[:20000] if claims_match else ""
            return ProviderResult(provider=self.name, query=patent_number,
                                  total_hits=1 if claims_text else 0,
                                  results=[{"patent_number": patent_number,
                                            "claims_text": claims_text}],
                                  cost_incurred=self.cost_per_call)
        except Exception as e:
            return ProviderResult(provider=self.name, query=patent_number, error=str(e))

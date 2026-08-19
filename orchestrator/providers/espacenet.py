"""
Espacenet / EPO Open Patent Services provider.

Uses OAuth 2.0 (Consumer Key / Consumer Secret) to access the
EPO Open Patent Services API, which provides access to >170M patent
documents worldwide with classification and family information.

PER CEO v28.3 DIRECTIVE:
  "Use several independent patent systems rather than treating Lens as
   the patent oracle. Espacenet >170M patent documents, international
   coverage, classifications and family information."

  "Don't search only invention keywords. Search the physical problem,
   failure mechanism, measurement, material, geometry, alternative
   mechanism, and adjacent industry separately."

CREDENTIALS:
  Consumer Key and Secret are provided inline by the caller.
  They are NEVER persisted to the repository.
  The credential scanner (G6/G12) will detect them if committed.
"""
from __future__ import annotations
import base64
import json
import subprocess
import time
import urllib.parse
from typing import Dict, Any, List

from .base import BaseProvider, ProviderResult


class EspacenetProvider(BaseProvider):
    """Espacenet / EPO Open Patent Services provider.

    Requires OAuth 2.0 authentication using Consumer Key/Secret.
    Access token is cached for the session.
    """
    name = "Espacenet"
    cost_per_call = 0.0  # free
    evidence_class = "patent_international"

    AUTH_URL = "https://ops.epo.org/3.2/auth/accesstoken"
    SEARCH_URL = "https://ops.epo.org/3.2/rest-services/published-data/search"
    PUBLICATION_URL = "https://ops.epo.org/3.2/rest-services/published-data/publication/epodoc/{doc_id}/biblio"

    def __init__(self, consumer_key: str, consumer_secret: str):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self._access_token: str = ""
        self._token_expiry: float = 0

    def _get_access_token(self) -> str:
        """Get OAuth 2.0 access token using client credentials grant."""
        if self._access_token and time.time() < self._token_expiry - 60:
            return self._access_token

        credentials = f"{self.consumer_key}:{self.consumer_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()

        result = subprocess.run(
            ["curl", "-s", "-X", "POST", self.AUTH_URL,
             "-H", f"Authorization: Basic {encoded}",
             "-H", "Content-Type: application/x-www-form-urlencoded",
             "-d", "grant_type=client_credentials"],
            capture_output=True, text=True, timeout=30
        )

        if result.returncode != 0:
            raise RuntimeError(f"Espacenet auth failed: {result.stderr}")

        data = json.loads(result.stdout)
        self._access_token = data.get("access_token", "")
        expires_in = data.get("expires_in", 3600)
        self._token_expiry = time.time() + expires_in
        return self._access_token

    def search(self, query: str, limit: int = 10, **kwargs) -> ProviderResult:
        """Search Espacenet for patents matching the query.

        Uses EPO query syntax (similar to Espacenet advanced search).
        Example: ta="shape memory alloy" AND pa="CereVasc"
        """
        try:
            token = self._get_access_token()
            encoded_query = urllib.parse.quote(query)
            url = f"{self.SEARCH_URL}?q={encoded_query}&range=1-{limit}"

            result = subprocess.run(
                ["curl", "-s", url,
                 "-H", f"Authorization: Bearer {token}",
                 "-H", "Accept: application/json"],
                capture_output=True, text=True, timeout=30
            )

            if result.returncode != 0:
                return ProviderResult(provider=self.name, query=query,
                                      error=f"Search failed: {result.stderr}")

            data = json.loads(result.stdout)
            hits = data.get("ops:world-patent-data", {}).get("ops:biblio-search", {})
            total = int(hits.get("@total-result-count", "0"))
            docs = hits.get("ops:search-result", [])

            patents = []
            for doc in docs:
                pub_ref = doc.get("publication-reference", {})
                docs_list = pub_ref.get("document-id", [])
                doc_id = ""
                title = ""
                for d in docs_list:
                    if d.get("@document-id-type") == "epodoc":
                        doc_id = d.get("doc-number", "")
                inventors = doc.get("inventor", [])
                patents.append({
                    "patent_number": doc_id,
                    "title": title,
                    "query": query,
                })

            return ProviderResult(provider=self.name, query=query,
                                  total_hits=total, results=patents,
                                  cost_incurred=self.cost_per_call)

        except Exception as e:
            return ProviderResult(provider=self.name, query=query, error=str(e))

    def retrieve_claims(self, patent_number: str) -> ProviderResult:
        """Retrieve bibliographic data for a patent (full claims require
        additional API calls not available in the free tier)."""
        try:
            token = self._get_access_token()
            url = self.PUBLICATION_URL.format(doc_id=patent_number)

            result = subprocess.run(
                ["curl", "-s", url,
                 "-H", f"Authorization: Bearer {token}",
                 "-H", "Accept: application/json"],
                capture_output=True, text=True, timeout=30
            )

            if result.returncode != 0:
                return ProviderResult(provider=self.name, query=patent_number,
                                      error=f"Retrieve failed: {result.stderr}")

            data = json.loads(result.stdout)
            return ProviderResult(provider=self.name, query=patent_number,
                                  results=[data], cost_incurred=self.cost_per_call)

        except Exception as e:
            return ProviderResult(provider=self.name, query=patent_number, error=str(e))

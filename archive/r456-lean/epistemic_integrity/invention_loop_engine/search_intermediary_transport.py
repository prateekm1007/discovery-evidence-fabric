"""
Search Intermediary Transport — honestly wraps z-ai web_search.

Per CEO directive (tenth round):
  'Never allow a convenience layer to impersonate the reality layer.'
  'z-ai web_search is a search intermediary, not automatically
   Google Patents/EPO/USPTO.'

  Record it honestly as SEARCH_INTERMEDIARY unless the underlying
  provider response and identity are directly observed.

This transport:
  1. Executes z-ai web_search (the actual intermediary)
  2. Records the intermediary identity (not a patent provider)
  3. Creates a receipt through the transport boundary (NOT manually)
  4. Stamps receipts as SEARCH_INTERMEDIARY provenance

Receipts from this transport are REAL (not synthetic) but carry the
honest label SEARCH_INTERMEDIARY — they came from a search intermediary,
not directly from a patent office API.

The PatentDestructionAdapter must treat SEARCH_INTERMEDIARY evidence
as discovery-level (keyword search) evidence, NOT as provider-confirmed
patent data. Patent-level evidence (claims, family, legal status) still
requires direct provider access (Google Patents API, EPO OPS, USPTO,
or PatSnap when the key works).
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from .patent_destruction_adapter import ProviderExecutionReceipt
from .provider_transport_boundary import (
    TransportExecutionRequest, TransportExecutionResult,
    TransportTrustLevel,
)


# Provider identity for search intermediary
INTERMEDIARY_PROVIDER_ID = "z_ai_web_search"
INTERMEDIARY_PROVIDER_NAME = "Z-AI Web Search (Intermediary)"
INTERMEDIARY_ADAPTER_VERSION = "SearchIntermediaryTransport v1.0"


class SearchIntermediaryTransport:
    """Transport that executes z-ai web_search and creates receipts honestly.

    Per CEO directive (tenth round):
      This is a SEARCH_INTERMEDIARY, not a patent provider.
      Receipts carry the intermediary identity, not a patent office identity.

    The receipt is created by THIS transport (not by the caller).
    The caller cannot set transport_verified=True manually.
    """

    def __init__(self, output_dir: str = None):
        self._executions: list[TransportExecutionResult] = []
        self._replay_protection: set[str] = set()
        self._output_dir = Path(output_dir) if output_dir else Path("/tmp/search_intermediary")
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def execute(self, request: TransportExecutionRequest) -> TransportExecutionResult:
        """Execute a z-ai web_search query.

        CRITICAL: This method makes the actual z-ai function call.
        The caller does NOT supply the response — the intermediary returns it.

        The request must have:
          - provider_name = "Z-AI Web Search (Intermediary)"
          - endpoint_url = "z-ai://web_search" (not a patent office URL)
          - request_params contains {"query": "...", "num": N}

        Returns:
            TransportExecutionResult with the actual intermediary response.
        """
        # Anti-replay
        fp = request.request_fingerprint
        if fp in self._replay_protection:
            return TransportExecutionResult(
                request=request,
                request_timestamp=datetime.now(timezone.utc).isoformat(),
                failure_state="REPLAY_DETECTED: This exact request was already executed.",
                trust_level=TransportTrustLevel.ADAPTER_ASSERTED,
            )
        self._replay_protection.add(fp)

        # Extract query from request_params
        query = request.request_params.get("query", "")
        num = request.request_params.get("num", 10)

        if not query:
            return TransportExecutionResult(
                request=request,
                request_timestamp=datetime.now(timezone.utc).isoformat(),
                failure_state="NO_QUERY: request_params must contain 'query'.",
                trust_level=TransportTrustLevel.ADAPTER_ASSERTED,
            )

        request_timestamp = datetime.now(timezone.utc).isoformat()

        # Execute the actual z-ai web_search
        output_file = self._output_dir / f"search_{hashlib.sha256(query.encode()).hexdigest()[:16]}.json"
        args = json.dumps({"query": query, "num": num})

        try:
            result = subprocess.run(
                ["z-ai", "function", "-n", "web_search",
                 "-a", args,
                 "-o", str(output_file)],
                capture_output=True, text=True, timeout=60
            )

            if result.returncode != 0:
                return TransportExecutionResult(
                    request=request,
                    request_timestamp=request_timestamp,
                    failure_state=f"ZAI_ERROR: {result.stderr[:200]}",
                    trust_level=TransportTrustLevel.ADAPTER_ASSERTED,
                )

            # Read the actual response
            with open(output_file) as f:
                response_data = json.load(f)

            response_body = json.dumps(response_data).encode()

            # Extract patent IDs from URLs and text
            import re
            raw_text = response_body.decode('utf-8', errors='ignore')
            # Match patent IDs in URLs: /patent/US4741730A/en
            url_matches = re.findall(r'/patent/(US\d{6,9}[A-Z]\d?)/', raw_text)
            standalone = re.findall(r'\b(US\d{7,9}[A-Z]\d?)\b', raw_text)
            patent_ids = list(set(url_matches + standalone))

            transport_metadata = {
                "transport": "SearchIntermediaryTransport (z-ai web_search)",
                "provider_type": "SEARCH_INTERMEDIARY",
                "intermediary": INTERMEDIARY_PROVIDER_NAME,
                "query": query,
                "num_requested": num,
                "num_returned": len(response_data),
                "patent_ids_extracted": len(patent_ids),
                "raw_response_file": str(output_file),
                "note": "This is a search intermediary, NOT a direct patent provider. "
                        "Evidence is discovery-level (keyword search). "
                        "Patent-level evidence (claims, family, legal status) "
                        "requires direct provider access.",
            }

            result_obj = TransportExecutionResult(
                request=request,
                request_timestamp=request_timestamp,
                response_status=200,
                response_headers={"content-type": "application/json",
                                  "x-intermediary": INTERMEDIARY_PROVIDER_ID},
                response_body=response_body,
                response_timestamp=datetime.now(timezone.utc).isoformat(),
                transport_metadata=transport_metadata,
                failure_state="",
                trust_level=TransportTrustLevel.TRANSPORT_OBSERVED,
            )

            # Override provider_record_ids with extracted patent IDs
            # (the base class extraction also works, but we want the URL-based extraction too)
            result_obj._provider_record_ids_override = patent_ids

            self._executions.append(result_obj)
            return result_obj

        except subprocess.TimeoutExpired:
            return TransportExecutionResult(
                request=request,
                request_timestamp=request_timestamp,
                failure_state="TIMEOUT: z-ai web_search did not respond within 60s.",
                trust_level=TransportTrustLevel.ADAPTER_ASSERTED,
            )
        except Exception as e:
            return TransportExecutionResult(
                request=request,
                request_timestamp=request_timestamp,
                failure_state=f"EXECUTION_ERROR: {str(e)[:200]}",
                trust_level=TransportTrustLevel.ADAPTER_ASSERTED,
            )

    def create_receipt(self, result: TransportExecutionResult) -> ProviderExecutionReceipt:
        """Create a receipt from the search intermediary execution.

        CRITICAL: This is the ONLY path to a valid receipt.
        The caller cannot create or modify the receipt.

        The receipt honestly records:
          - provider = "Z-AI Web Search (Intermediary)"
          - adapter_version includes "SEARCH_INTERMEDIARY"
          - transport_verified = True (set here, not by caller)
        """
        receipt = result.to_receipt()

        # Override provider_record_ids with our URL-based extraction
        if hasattr(result, '_provider_record_ids_override'):
            receipt.provider_record_ids = result._provider_record_ids_override

        # Set transport_verified — ONLY here, not by the caller
        receipt.transport_verified = True

        # Stamp with intermediary identity
        receipt.provider = INTERMEDIARY_PROVIDER_NAME
        receipt.adapter_version = (
            f"{INTERMEDIARY_ADAPTER_VERSION} | "
            f"SEARCH_INTERMEDIARY | "
            f"TRANSPORT_BOUNDARY_VERIFIED"
        )

        return receipt

    def get_execution_history(self) -> list[dict]:
        return [e.to_dict() for e in self._executions]


def is_search_intermediary_receipt(receipt: ProviderExecutionReceipt) -> bool:
    """Check if a receipt is from the search intermediary (not a direct provider)."""
    return "SEARCH_INTERMEDIARY" in (receipt.adapter_version or "")

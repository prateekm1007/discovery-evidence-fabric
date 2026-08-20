"""
Live vs Synthetic Provider Transport — absolute provenance boundary.

Per CEO directive (ninth round):
  'A simulator of reality must never be allowed to masquerade as contact
   with reality.'

  Split the system into:
    LIVE_PROVIDER_TRANSPORT — actual HTTP/API client, response from real provider
    SYNTHETIC_PROVIDER_TRANSPORT — testing only, response supplied by caller

  Only LIVE can produce evidence eligible for a real patent attack.
  SYNTHETIC evidence is permanently stamped SYNTHETIC_TEST_ONLY and rejected
  by the real patent-destruction verdict path.

  The live path:
    adapter request → trusted provider registry → actual HTTP/API client →
    response → receipt

  The caller must NOT supply:
    response_body, response_status, response_headers
  Those must come from the actual HTTP client.

  Provider identity resolves from:
    provider_id → approved endpoint(s) → transport configuration
  A caller cannot say provider_name="USPTO" + arbitrary URL.
"""

from __future__ import annotations

import hashlib
import json
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4
from enum import Enum

from .patent_destruction_adapter import ProviderExecutionReceipt
from .provider_transport_boundary import (
    TransportExecutionRequest, TransportExecutionResult,
    TransportTrustLevel, ProviderTransportBoundary,
)


class TransportMode(str, Enum):
    """The mode of transport execution.

    Per CEO directive (ninth round):
      LIVE — actual HTTP request to a real provider. Response comes from
             the external provider. Evidence is eligible for real patent attacks.
      SYNTHETIC — response is supplied by the caller for testing. Evidence
                  is permanently stamped SYNTHETIC_TEST_ONLY and CANNOT
                  influence real patent-destruction verdicts.
    """
    LIVE = "LIVE"
    SYNTHETIC = "SYNTHETIC"


@dataclass
class ProviderRegistryEntry:
    """A trusted provider registry entry.

    Per CEO directive (ninth round):
      Provider identity must resolve from:
        provider_id → approved endpoint(s) → transport configuration

      A caller cannot say provider_name="USPTO" + arbitrary URL.
      The endpoint must come from this registry, not from the caller.
    """
    provider_id: str           # e.g., "google_patents", "epo_espacenet"
    provider_name: str         # Human-readable: "Google Patents"
    approved_endpoints: list[str]  # Approved base URLs
    transport_config: dict = field(default_factory=dict)  # timeout, headers, etc.
    adapter_version: str = ""  # Version stamped by registry, not caller

    def resolves_endpoint(self, endpoint_url: str) -> bool:
        """Check if an endpoint URL is approved for this provider."""
        for approved in self.approved_endpoints:
            if endpoint_url.startswith(approved):
                return True
        return False

    def to_dict(self) -> dict:
        return {
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "approved_endpoints": self.approved_endpoints,
            "transport_config": self.transport_config,
            "adapter_version": self.adapter_version,
        }


class TrustedProviderRegistry:
    """Registry of approved patent search providers.

    Per CEO directive (ninth round):
      A caller cannot supply provider_name="USPTO" + arbitrary URL.
      The provider_id must resolve to approved endpoints from this registry.
    """

    def __init__(self):
        self._providers: dict[str, ProviderRegistryEntry] = {}
        self._register_default_providers()

    def _register_default_providers(self):
        """Register the frozen source universe providers."""
        providers = [
            ProviderRegistryEntry(
                provider_id="google_patents",
                provider_name="Google Patents",
                approved_endpoints=[
                    "https://patents.google.com/",
                    "https://patents.google.com/?",
                ],
                transport_config={"timeout": 30, "user_agent": "CereVasc-Invention-Loop/1.0"},
                adapter_version="GooglePatentsAdapter v1.0",
            ),
            ProviderRegistryEntry(
                provider_id="epo_espacenet",
                provider_name="EPO/Espacenet",
                approved_endpoints=[
                    "https://worldwide.espacenet.com/",
                    "https://ops.epo.org/",
                ],
                transport_config={"timeout": 30},
                adapter_version="EpoEspacenetAdapter v1.0",
            ),
            ProviderRegistryEntry(
                provider_id="uspto",
                provider_name="USPTO Patent Public Search",
                approved_endpoints=[
                    "https://patents.uspto.gov/",
                    "https://ppubs.uspto.gov/",
                ],
                transport_config={"timeout": 30},
                adapter_version="UsptoAdapter v1.0",
            ),
            ProviderRegistryEntry(
                provider_id="wipo_patentscope",
                provider_name="WIPO PATENTSCOPE",
                approved_endpoints=[
                    "https://patentscope.wipo.int/",
                ],
                transport_config={"timeout": 30},
                adapter_version="WipoPatentscopeAdapter v1.0",
            ),
            ProviderRegistryEntry(
                provider_id="lens",
                provider_name="Lens",
                approved_endpoints=[
                    "https://www.lens.org/",
                    "https://api.lens.org/",
                ],
                transport_config={"timeout": 30},
                adapter_version="LensAdapter v1.0",
            ),
            ProviderRegistryEntry(
                provider_id="patentbear",
                provider_name="PatentBear",
                approved_endpoints=[
                    "https://www.patentbear.com/",
                ],
                transport_config={"timeout": 30},
                adapter_version="PatentBearAdapter v1.0",
            ),
        ]
        for p in providers:
            self._providers[p.provider_id] = p

    def resolve(self, provider_id: str) -> Optional[ProviderRegistryEntry]:
        """Resolve a provider_id to its registry entry."""
        return self._providers.get(provider_id)

    def validate_endpoint(self, provider_id: str, endpoint_url: str) -> bool:
        """Validate that an endpoint URL is approved for the given provider."""
        entry = self.resolve(provider_id)
        if entry is None:
            return False
        return entry.resolves_endpoint(endpoint_url)

    def get_adapter_version(self, provider_id: str) -> str:
        """Get the adapter version stamped by the registry."""
        entry = self.resolve(provider_id)
        if entry is None:
            return ""
        return entry.adapter_version


class LiveProviderTransport:
    """LIVE provider transport — performs actual HTTP requests.

    Per CEO directive (ninth round):
      The caller must NOT supply response_body, response_status, response_headers.
      Those must come from the actual HTTP client.

      Only LIVE can produce evidence eligible for a real patent attack.

    This class makes actual HTTP requests using urllib.
    The response is observed by the transport layer — the caller has no control
    over what the provider returns.
    """

    def __init__(self, registry: TrustedProviderRegistry):
        self.registry = registry
        self._executions: list[TransportExecutionResult] = []
        self._replay_protection: set[str] = set()

    def execute(self, request: TransportExecutionRequest) -> TransportExecutionResult:
        """Execute an actual HTTP request to a real provider.

        CRITICAL: This method does NOT accept response_body/status/headers.
        It makes the actual HTTP request and observes the response.

        The request.provider_name must resolve to an approved provider in the
        registry, and the endpoint_url must be an approved endpoint.

        Args:
            request: The execution request. Must have provider_name that
                     resolves in the registry, and endpoint_url that is approved.

        Returns:
            TransportExecutionResult with the actual response from the provider.
        """
        # Anti-replay check
        fp = request.request_fingerprint
        if fp in self._replay_protection:
            return TransportExecutionResult(
                request=request,
                request_timestamp=datetime.now(timezone.utc).isoformat(),
                failure_state="REPLAY_DETECTED: This exact request was already executed.",
                trust_level=TransportTrustLevel.TRANSPORT_OBSERVED,
            )
        self._replay_protection.add(fp)

        # Resolve provider from registry
        # The provider_name in the request must match a registry entry
        provider_id = self._resolve_provider_id(request.provider_name)
        if provider_id is None:
            return TransportExecutionResult(
                request=request,
                request_timestamp=datetime.now(timezone.utc).isoformat(),
                failure_state=f"UNKNOWN_PROVIDER: '{request.provider_name}' is not "
                              f"in the trusted provider registry.",
                trust_level=TransportTrustLevel.TRANSPORT_OBSERVED,
            )

        entry = self.registry.resolve(provider_id)
        if entry is None:
            return TransportExecutionResult(
                request=request,
                request_timestamp=datetime.now(timezone.utc).isoformat(),
                failure_state=f"PROVIDER_NOT_REGISTERED: '{request.provider_name}' "
                              f"is not registered.",
                trust_level=TransportTrustLevel.TRANSPORT_OBSERVED,
            )

        # Validate endpoint
        if not entry.resolves_endpoint(request.endpoint_url):
            return TransportExecutionResult(
                request=request,
                request_timestamp=datetime.now(timezone.utc).isoformat(),
                failure_state=f"ENDPOINT_NOT_APPROVED: '{request.endpoint_url}' is not "
                              f"an approved endpoint for '{request.provider_name}'. "
                              f"Approved: {entry.approved_endpoints}",
                trust_level=TransportTrustLevel.TRANSPORT_OBSERVED,
            )

        # Stamp adapter version from registry (not from caller)
        stamped_version = entry.adapter_version

        # Make the actual HTTP request
        request_timestamp = datetime.now(timezone.utc).isoformat()
        try:
            # Build the URL with query params
            url = request.endpoint_url
            if request.request_params:
                from urllib.parse import urlencode
                url = f"{url}&{urlencode(request.request_params)}" if "?" in url \
                      else f"{url}?{urlencode(request.request_params)}"

            # Create the request
            headers = dict(request.request_headers)
            headers.setdefault("User-Agent",
                             entry.transport_config.get("user_agent",
                                                       "CereVasc-Invention-Loop/1.0"))

            req = urllib.request.Request(url, headers=headers, method=request.request_method)
            timeout = entry.transport_config.get("timeout", 30)

            # Execute the request
            with urllib.request.urlopen(req, timeout=timeout) as response:
                response_body = response.read()
                response_status = response.status
                response_headers = dict(response.headers)

            transport_metadata = {
                "transport": "LiveProviderTransport (actual HTTP)",
                "mode": TransportMode.LIVE.value,
                "provider_id": provider_id,
                "url": url,
                "timeout": timeout,
            }

            result = TransportExecutionResult(
                request=request,
                request_timestamp=request_timestamp,
                response_status=response_status,
                response_headers=response_headers,
                response_body=response_body,
                response_timestamp=datetime.now(timezone.utc).isoformat(),
                transport_metadata=transport_metadata,
                failure_state="",
                trust_level=TransportTrustLevel.TRANSPORT_OBSERVED,
            )

            # Stamp adapter version from registry
            result.request.adapter_version = stamped_version

        except urllib.error.HTTPError as e:
            result = TransportExecutionResult(
                request=request,
                request_timestamp=request_timestamp,
                response_status=e.code,
                response_headers=dict(e.headers) if e.headers else {},
                response_body=e.read() if e.fp else b"",
                response_timestamp=datetime.now(timezone.utc).isoformat(),
                transport_metadata={"transport": "LiveProviderTransport",
                                   "mode": TransportMode.LIVE.value,
                                   "error": f"HTTPError: {e.code}"},
                failure_state=f"HTTP_ERROR: {e.code} {e.reason}",
                trust_level=TransportTrustLevel.TRANSPORT_OBSERVED,
            )

        except urllib.error.URLError as e:
            result = TransportExecutionResult(
                request=request,
                request_timestamp=request_timestamp,
                failure_state=f"URL_ERROR: {str(e.reason)}",
                trust_level=TransportTrustLevel.TRANSPORT_OBSERVED,
            )

        except Exception as e:
            result = TransportExecutionResult(
                request=request,
                request_timestamp=request_timestamp,
                failure_state=f"TRANSPORT_ERROR: {str(e)}",
                trust_level=TransportTrustLevel.TRANSPORT_OBSERVED,
            )

        self._executions.append(result)
        return result

    def create_receipt(self, result: TransportExecutionResult) -> ProviderExecutionReceipt:
        """Create a ProviderExecutionReceipt from a live transport execution.

        CRITICAL: This receipt is from a LIVE transport execution.
        It is eligible for real patent-destruction verdicts.
        """
        receipt = result.to_receipt()
        receipt.transport_verified = True
        receipt.adapter_version = f"{receipt.adapter_version} | LIVE_TRANSPORT_VERIFIED"
        return receipt

    def _resolve_provider_id(self, provider_name: str) -> Optional[str]:
        """Resolve a provider name to a provider_id in the registry."""
        for pid, entry in self.registry._providers.items():
            if entry.provider_name == provider_name:
                return pid
        return None


class SyntheticProviderTransport:
    """SYNTHETIC provider transport — for testing only.

    Per CEO directive (ninth round):
      Synthetic responses are allowed for testing the framework, but their
      provenance must permanently say SYNTHETIC_TEST_ONLY, and such evidence
      must be rejected by the real patent-destruction verdict path.

      'A simulator of reality must never be allowed to masquerade as
       contact with reality.'

    This class accepts response_body/status/headers from the caller (for testing).
    ALL receipts from this transport are permanently stamped SYNTHETIC_TEST_ONLY.
    """

    def __init__(self):
        self._executions: list[TransportExecutionResult] = []
        self._replay_protection: set[str] = set()

    def execute(self, request: TransportExecutionRequest,
                response_body: bytes,
                response_status: int = 200,
                response_headers: dict = None,
                failure_state: str = "") -> TransportExecutionResult:
        """Execute a SYNTHETIC transport (for testing only).

        CRITICAL: This method accepts response_body/status/headers from the caller.
        This is ONLY for testing the framework. Evidence from this transport is
        permanently SYNTHETIC_TEST_ONLY and CANNOT influence real patent verdicts.
        """
        # Anti-replay check
        fp = request.request_fingerprint
        if fp in self._replay_protection:
            return TransportExecutionResult(
                request=request,
                request_timestamp=datetime.now(timezone.utc).isoformat(),
                failure_state="REPLAY_DETECTED: Synthetic replay.",
                trust_level=TransportTrustLevel.ADAPTER_ASSERTED,
            )
        self._replay_protection.add(fp)

        result = TransportExecutionResult(
            request=request,
            request_timestamp=datetime.now(timezone.utc).isoformat(),
            response_status=response_status,
            response_headers=response_headers or {},
            response_body=response_body,
            response_timestamp=datetime.now(timezone.utc).isoformat(),
            transport_metadata={
                "transport": "SyntheticProviderTransport (TESTING ONLY)",
                "mode": TransportMode.SYNTHETIC.value,
                "WARNING": "This is NOT a real provider response. "
                          "Evidence is SYNTHETIC_TEST_ONLY and cannot "
                          "influence real patent-destruction verdicts.",
            },
            failure_state=failure_state,
            trust_level=TransportTrustLevel.ADAPTER_ASSERTED,  # NOT TRANSPORT_OBSERVED
        )

        self._executions.append(result)
        return result

    def create_receipt(self, result: TransportExecutionResult) -> ProviderExecutionReceipt:
        """Create a SYNTHETIC receipt.

        CRITICAL: This receipt is SYNTHETIC_TEST_ONLY.
        It is NOT eligible for real patent-destruction verdicts.
        The manifest must reject SYNTHETIC receipts for real verdicts.
        """
        receipt = result.to_receipt()
        receipt.transport_verified = True  # Technically verified by synthetic transport
        receipt.adapter_version = f"{receipt.adapter_version} | SYNTHETIC_TEST_ONLY"
        receipt.failure_state = "SYNTHETIC_TEST_ONLY: This receipt is from a "
        receipt.failure_state += "synthetic transport and CANNOT influence "
        receipt.failure_state += "real patent-destruction verdicts."
        return receipt


def is_eligible_for_real_verdict(receipt: ProviderExecutionReceipt) -> bool:
    """Check if a receipt is eligible for real patent-destruction verdicts.

    Per CEO directive (ninth round):
      SYNTHETIC_TEST_ONLY evidence must be rejected by the real
      patent-destruction verdict path.

    A receipt is eligible ONLY if:
      1. transport_verified = True
      2. failure_state does not contain "SYNTHETIC_TEST_ONLY"
      3. adapter_version does not contain "SYNTHETIC_TEST_ONLY"
    """
    if not receipt.transport_verified:
        return False
    if "SYNTHETIC_TEST_ONLY" in (receipt.failure_state or ""):
        return False
    if "SYNTHETIC_TEST_ONLY" in (receipt.adapter_version or ""):
        return False
    return receipt.provider_confirmed

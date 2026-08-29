"""Connector base for the source registry — the 7-step proof chain.

CEO database-layer directive, per-source proof chain:

    CONNECTOR EXISTS -> LIVE REQUEST WORKS -> RESPONSE PARSES ->
    NORMALIZATION WORKS -> PROVENANCE STORES -> RETRIEVAL LOG STORES ->
    HEALTH CHECK PASSES

Constitutional anchors:
- Art. XXI.3: provider failure is NOT absence. Statuses TIMEOUT /
  SEARCH_FAILED / AUTH_FAILED / RATE_LIMITED / PARSE_FAILED are distinct
  from EMPTY. EMPTY is emitted ONLY after HTTP 200 + successful parse +
  successful normalization + zero matching records.
- Art. XXI.9: every result enters provenance custody:
  query -> provider -> raw result -> record ID -> hash -> epistemic class.
- Art. VI: the base never fabricates hashes, timestamps, or ids.
- Art. XXV: unknown stays unknown; failures are surfaced, never swallowed.
"""

from __future__ import annotations

import hashlib
import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# Permissive SSL mirrors the existing connector base in this codebase
# (a2/retrieve.py, prior_art_v2/sources.py). Tightening is a separate,
# explicit hardening task; silently changing it here could alter measured
# behavior of existing integrations.
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Request status vocabulary (Art. XXI.3 — these are NEVER collapsed).
STATUS_OK = "OK"
STATUS_EMPTY = "EMPTY"                    # HTTP 200 + parsed + 0 records — the ONLY true empty
STATUS_TIMEOUT = "TIMEOUT"
STATUS_SEARCH_FAILED = "SEARCH_FAILED"    # network-level failure
STATUS_AUTH_FAILED = "AUTH_FAILED"        # 401/403
STATUS_RATE_LIMITED = "RATE_LIMITED"      # 429 / explicit budget exhausted
STATUS_UNAVAILABLE = "UNAVAILABLE"        # 5xx
STATUS_PARSE_FAILED = "PARSE_FAILED"      # request OK, body not parseable
STATUS_NOT_IMPLEMENTED = "NOT_IMPLEMENTED"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_obj(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    ).hexdigest()


@dataclass
class SourceRecord:
    """One normalized record from a source, with full provenance custody.

    Art. XXI.9 chain: query -> provider -> raw result -> exact record ID ->
    content hash -> epistemic class.
    """

    source_id: str                 # registry source id, e.g. "fda_maude"
    role: str                      # authority role served for this record
    record_id: str                 # exact id in the source namespace
    title: str
    uri: str
    retrieved_at: str              # ISO 8601 UTC
    query: str                     # the query that produced this record
    raw_payload_sha256: str        # sha256 of the raw response payload
    normalized: Dict[str, Any]     # source-specific normalized fields
    provenance: Dict[str, Any]
    epistemic_state: str = "OBSERVED"
    limitations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "role": self.role,
            "record_id": self.record_id,
            "title": self.title,
            "uri": self.uri,
            "retrieved_at": self.retrieved_at,
            "query": self.query,
            "raw_payload_sha256": self.raw_payload_sha256,
            "normalized": self.normalized,
            "provenance": self.provenance,
            "epistemic_state": self.epistemic_state,
            "limitations": self.limitations,
        }


@dataclass
class SourceQueryResult:
    """Result of one source query — statuses per Art. XXI.3."""

    source_id: str
    status: str                     # STATUS_* vocabulary
    ok: bool                        # True only for OK / EMPTY (provider answered)
    http_status: Optional[int] = None
    latency_ms: Optional[int] = None
    records: List[SourceRecord] = field(default_factory=list)
    error: Optional[str] = None
    rate_limit_remaining: Optional[str] = None
    query: str = ""
    retrieved_at: Optional[str] = None
    total_hits: Optional[int] = None  # provider-reported total population, when the API reports it

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "status": self.status,
            "ok": self.ok,
            "http_status": self.http_status,
            "latency_ms": self.latency_ms,
            "record_count": len(self.records),
            "error": self.error,
            "rate_limit_remaining": self.rate_limit_remaining,
            "query": self.query,
            "retrieved_at": self.retrieved_at,
            "total_hits": self.total_hits,
            "records": [r.to_dict() for r in self.records],
        }


class ConnectorBase:
    """Base class every source connector implements.

    Subclasses define:
      SOURCE_ID, ROLE(S), and search(query) which MUST go through
      _execute() so the failure semantics + logging are uniform.
    """

    SOURCE_ID: str = ""
    ROLES: Tuple[str, ...] = ()
    #: health-check probe query (tiny, deterministic)
    HEALTH_QUERY: str = ""

    # ---- steps of the 7-step chain, overridable -------------------------

    def definitive_empty(self, http_status: Optional[int], body: Optional[bytes]) -> bool:
        """True when the PROVIDER DEFINITIVELY answered 'zero records'.

        Art. XXI.3 requires distinguishing 'provider failed' from 'provider
        answered: nothing matches'. Some APIs (openFDA) signal zero results
        with HTTP 404 + a structured error body. Default: no API-specific
        knowledge -> False (fail-safe: a 404 is NOT treated as absence).
        """
        return False

    def extract_total_hits(self, payload: Any) -> Optional[int]:
        """Provider-reported TOTAL population for the query, if the API
        reports one (e.g. openFDA meta.results.total). Used to disclose the
        difference between the retrieved sample and the population — the
        sample is never silently presented as the whole."""
        return None

    def build_url(self, query: str) -> str:
        raise NotImplementedError

    def parse_payload(self, raw: bytes, query: str) -> Any:
        """Parse raw bytes -> structured payload. Raise on unparseable."""
        raise NotImplementedError

    def normalize_payload(self, payload: Any, query: str, raw_sha: str) -> List[SourceRecord]:
        """Structured payload -> normalized SourceRecords. Raise on structure violation."""
        raise NotImplementedError

    # ---- engine ----------------------------------------------------------

    def _request(self, url: str, timeout: int = 25) -> Tuple[Optional[bytes], str, Optional[int], Optional[str], Optional[str]]:
        """Live HTTP GET with Art. XXI.3 status discipline.

        Returns (body, status, http_status, error, rate_limit_remaining).
        """
        t0 = time.time()
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": USER_AGENT, "Accept": "application/json,*/*"}
            )
            resp = urllib.request.urlopen(req, timeout=timeout, context=SSL_CONTEXT)
            body = resp.read()
            remaining = resp.headers.get("X-RateLimit-Remaining")
            return body, STATUS_OK, resp.status, None, remaining
        except urllib.error.HTTPError as e:
            code = e.code
            try:
                error_body = e.read()
            except Exception:
                error_body = b""
            if code in (401, 403):
                status = STATUS_AUTH_FAILED
            elif code == 429:
                status = STATUS_RATE_LIMITED
            elif code >= 500:
                status = STATUS_UNAVAILABLE
            else:
                status = STATUS_SEARCH_FAILED
            detail = error_body[:300].decode("utf-8", "replace")
            return error_body, status, code, f"HTTP {code}: {detail[:200]}", None
        except urllib.error.URLError as e:
            if isinstance(getattr(e, "reason", None), TimeoutError) or "timed out" in str(e).lower():
                return None, STATUS_TIMEOUT, None, f"URLError: {e}", None
            return None, STATUS_SEARCH_FAILED, None, f"URLError: {e}", None
        except TimeoutError:
            return None, STATUS_TIMEOUT, None, "TimeoutError", None
        except Exception as e:  # noqa: BLE001 — surfaced, never swallowed
            return None, STATUS_SEARCH_FAILED, None, f"{type(e).__name__}: {e}", None

    def _execute(self, query: str, timeout: int = 25) -> SourceQueryResult:
        """Uniform query execution: request -> parse -> normalize -> log.

        Flow discipline: parse/normalize run ONLY on a 2xx success body.
        An error-status body is inspected solely through definitive_empty()
        (provider's structured 'zero records' answer). This prevents error
        bodies (429 rate-limit JSON, 5xx HTML) from masquerading as
        PARSE_FAILED payloads and masking the true provider status
        (Art. XXI.3).
        """
        url = self.build_url(query)
        t0 = time.time()
        body, status, http_status, error, remaining = self._request(url, timeout=timeout)

        # Provider-definitive zero: HTTP error status + provider's own
        # 'no records' body -> EMPTY (ok=True: the provider ANSWERED).
        if status != STATUS_OK and body is not None and self.definitive_empty(http_status, body):
            return self._finish(
                SourceQueryResult(
                    source_id=self.SOURCE_ID, status=STATUS_EMPTY, ok=True,
                    http_status=http_status, latency_ms=int((time.time() - t0) * 1000),
                    error=None, rate_limit_remaining=remaining, query=query,
                    retrieved_at=utc_now(),
                ),
                query, url, sha256_bytes(body),
            )

        if status == STATUS_OK and body is not None:
            raw_sha = sha256_bytes(body)
            try:
                payload = self.parse_payload(body, query)
            except Exception as e:  # noqa: BLE001 — recorded as PARSE_FAILED
                return self._finish(
                    SourceQueryResult(
                        source_id=self.SOURCE_ID, status=STATUS_PARSE_FAILED, ok=False,
                        http_status=http_status, latency_ms=int((time.time() - t0) * 1000),
                        error=f"parse: {type(e).__name__}: {e}", query=query,
                        retrieved_at=utc_now(),
                    ),
                    query, url, raw_sha,
                )
            try:
                records = self.normalize_payload(payload, query, raw_sha)
            except Exception as e:  # noqa: BLE001
                return self._finish(
                    SourceQueryResult(
                        source_id=self.SOURCE_ID, status=STATUS_PARSE_FAILED, ok=False,
                        http_status=http_status, latency_ms=int((time.time() - t0) * 1000),
                        error=f"normalize: {type(e).__name__}: {e}", query=query,
                        retrieved_at=utc_now(),
                    ),
                    query, url, raw_sha,
                )
            final_status = STATUS_OK if records else STATUS_EMPTY
            return self._finish(
                SourceQueryResult(
                    source_id=self.SOURCE_ID, status=final_status, ok=True,
                    http_status=http_status, latency_ms=int((time.time() - t0) * 1000),
                    records=records, rate_limit_remaining=remaining, query=query,
                    retrieved_at=utc_now(),
                    total_hits=self.extract_total_hits(payload),
                ),
                query, url, raw_sha,
            )

        # Provider failure — Art. XXI.3: never EMPTY, never silent.
        return self._finish(
            SourceQueryResult(
                source_id=self.SOURCE_ID, status=status, ok=False,
                http_status=http_status,
                latency_ms=int((time.time() - t0) * 1000),
                error=error, query=query, retrieved_at=utc_now(),
            ),
            query, url, None,
        )

    def search(self, query: str, timeout: int = 25) -> SourceQueryResult:
        """Public entrypoint. Subclasses may override only to add params."""
        return self._execute(query, timeout=timeout)

    # ---- retrieval-log custody -------------------------------------------

    def _finish(self, result: SourceQueryResult, query: str, url: str, raw_sha: Optional[str]) -> SourceQueryResult:
        """Write the retrieval-log entry (provenance custody, Art. XXI.9)."""
        try:
            from discovery_fabric.source_registry.retrieval_log import append_entry
            append_entry(
                source_id=result.source_id, query=query, url=url,
                status=result.status, http_status=result.http_status,
                latency_ms=result.latency_ms, record_count=len(result.records),
                raw_payload_sha256=raw_sha,
                error=result.error,
            )
        except Exception as e:  # noqa: BLE001
            # Logging failure must not corrupt the result, but MUST surface.
            result.error = (result.error or "") + f" | retrieval_log_write_failed: {e}"
        return result

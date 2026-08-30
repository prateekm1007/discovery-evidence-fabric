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

    # ---- rate-limit recovery policy (2026-08-30, CEO fix-degraded) -----
    #: bounded retries for transient RATE_LIMITED answers; 0 disables.
    RATE_LIMIT_RETRIES: int = 2
    #: base seconds for exponential backoff (2**attempt * base), capped.
    BACKOFF_BASE_SECONDS: float = 2.0
    BACKOFF_CAP_SECONDS: float = 30.0

    def is_metered(self) -> bool:
        """True when the source is provider-metered (quota per window).

        Metered sources NEVER auto-retry rate limits: a retry spends the
        same scarce quota the 429 is protecting (PatentBear 20/month,
        Lens credits). The registry's metered_quota marker is the
        authority; connectors may override for policy reasons.
        """
        try:
            from discovery_fabric.source_registry.registry import SOURCE_REGISTRY
            rec = SOURCE_REGISTRY.get(self.SOURCE_ID, {})
            return bool(rec.get("metered_quota"))
        except Exception:  # noqa: BLE001 — registry unavailable = not metered
            return False

    def _backoff_seconds(self, error: Optional[str], attempt: int) -> float:
        """Delay before retry attempt N. Honors provider Retry-After when
        present in the error string (surfaced by _request), else
        exponential with cap."""
        import re as _re
        if error:
            m = _re.search(r"Retry-After:\s*(\d+)", error)
            if m:
                return min(float(m.group(1)), self.BACKOFF_CAP_SECONDS)
        return min((2 ** attempt) * self.BACKOFF_BASE_SECONDS,
                   self.BACKOFF_CAP_SECONDS)

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

    # POST-API support (2026-08-30, NIH RePORTER integration): connectors
    # for POST-only JSON APIs set HTTP_METHOD="POST" and return a JSON
    # body from build_request_body(). The retrieval log still records the
    # URL (never the body), so custody discipline is unchanged. Default
    # stays GET — every existing connector is untouched.
    HTTP_METHOD = "GET"

    def build_request_body(self, query: str) -> Optional[bytes]:
        return None

    def parse_payload(self, raw: bytes, query: str) -> Any:
        """Parse raw bytes -> structured payload. Raise on unparseable."""
        raise NotImplementedError

    def normalize_payload(self, payload: Any, query: str, raw_sha: str) -> List[SourceRecord]:
        """Structured payload -> normalized SourceRecords. Raise on structure violation."""
        raise NotImplementedError

    # ---- engine ----------------------------------------------------------

    def request_headers(self) -> Dict[str, str]:
        """Extra request headers for authenticated sources (e.g. API keys).

        Keys live in .env.keys (gitignored) and are NEVER placed in URLs —
        the retrieval log stores the URL, so header auth also keeps
        credentials out of the custody log (S-01 discipline).
        """
        return {}

    def _request(self, url: str, timeout: int = 25) -> Tuple[Optional[bytes], str, Optional[int], Optional[str], Optional[str]]:
        """Live HTTP GET with Art. XXI.3 status discipline.

        Returns (body, status, http_status, error, rate_limit_remaining).
        """
        t0 = time.time()
        try:
            method = getattr(self, "HTTP_METHOD", "GET")
            # POST body is built from the CURRENT query stashed by
            # _execute (keeps _request(url, timeout) signature stable
            # for every existing subclass and test stub)
            body = self.build_request_body(
                getattr(self, "_current_query", "")) \
                if method == "POST" else None
            headers = {
                "User-Agent": USER_AGENT,
                "Accept": "application/json,*/*",
                **self.request_headers(),
            }
            if body is not None:
                headers["Content-Type"] = "application/json"
            req = urllib.request.Request(
                url,
                data=body,
                headers=headers,
                method=method,
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
            retry_after = e.headers.get("Retry-After") if getattr(e, "headers", None) else None
            err = f"HTTP {code}: {detail[:200]}"
            if status == STATUS_RATE_LIMITED and retry_after:
                err += f" | Retry-After: {retry_after}"
            return error_body, status, code, err, None
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
        self._current_query = query  # consumed by _request for POST APIs
        t0 = time.time()
        body, status, http_status, error, remaining = self._request(url, timeout=timeout)

        # 2026-08-30 (CEO fix-degraded directive): RATE_LIMITED answers get
        # bounded exponential backoff with provider Retry-After honored —
        # BUT ONLY for non-metered sources. A metered source must never
        # auto-retry: every retry burns provider quota (PatentBear
        # 20/month discipline). Budget-window limits (OpenAlex
        # 'Insufficient budget', $0 remaining) retry once politely then
        # fail honestly — a spent daily budget is provider-side state,
        # not something code can spend differently.
        retries_used = 0
        while (status == STATUS_RATE_LIMITED
               and retries_used < self.RATE_LIMIT_RETRIES
               and not self.is_metered()):
            delay = self._backoff_seconds(error, retries_used)
            time.sleep(delay)
            retries_used += 1
            body, status, http_status, error, remaining = self._request(url, timeout=timeout)
        if retries_used and status != STATUS_RATE_LIMITED:
            note = f"recovered after {retries_used} backoff retry(ies)"
            error = f"{error} | {note}" if error else note

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
                    # carry the backoff-recovery note (non-fatal) when the
                    # answer arrived only after retries
                    error=error if error and "recovered after" in error else None,
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

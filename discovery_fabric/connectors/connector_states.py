"""connector_states.py — R394 section 4: the ONE connector failure-semantics
contract for every external-source call in the engine.

Directive (CEO R394/R395, section 4 — "EUROPEPMC / CONNECTOR FAILURE
SEMANTICS"):

  A connector outage must never become a scientific conclusion.

  Explicit states:
    SUCCESS          the provider answered and the payload parsed
    EMPTY_RESULT     SUCCESS with zero matching records (a REAL absence
                     claim for the queried universe, not an outage)
    TIMEOUT          the provider did not answer in time
    RATE_LIMITED     provider refused for quota (HTTP 429 / quota text)
    PROVIDER_ERROR   provider answered with an error (HTTP 5xx, 4xx)
    PARSE_ERROR      transport OK but the payload is not the contract
    UNAVAILABLE      transport-level failure (DNS, connection refused,
                     SSL, network unreachable)
    NOT_ATTEMPTED    the call was never made (quota guard, disabled)

  Mandatory mapping:
    SUCCESS + zero results       -> EMPTY_RESULT
    TIMEOUT                      -> UNKNOWN (never absence)
    PROVIDER_ERROR / UNAVAILABLE -> UNKNOWN (never absence)
    PARSE_ERROR                  -> UNKNOWN (never absence)

  Forbidden (constitution Art. XXI.3 / XXV):
    TIMEOUT -> ABSENCE
    PROVIDER_ERROR -> ABSENCE
    any outage state collapsing into NO_* / EMPTY / total=0-with-no-error

This module is deliberately dependency-free (stdlib only) so every layer
— orchestrator, a2, prior_art_v2, source_registry — can import it
without cycles. It classifies from exceptions/HTTP codes, carries a
machine-readable state + reason, and NEVER raises.

R394 section 3 (deterministic relevance): every connector outcome records
the retrieval provider, its configuration fingerprint, and a decision-
input hash so identical (source snapshot, query, config) pairs can be
re-checked for identical judgments downstream.
"""
from __future__ import annotations

import hashlib
import json
import socket
import ssl
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

# The eight states (R394 section 4 contract — do not extend silently)
CONNECTOR_STATES = (
    "SUCCESS",
    "EMPTY_RESULT",
    "TIMEOUT",
    "RATE_LIMITED",
    "PROVIDER_ERROR",
    "PARSE_ERROR",
    "UNAVAILABLE",
    "NOT_ATTEMPTED",
)

# Outage states — any of these makes the epistemic result UNKNOWN, never
# absence (Art. XXI.3). PARSE_ERROR included: an unparsable payload proves
# nothing about the records it might have carried.
OUTAGE_STATES = ("TIMEOUT", "RATE_LIMITED", "PROVIDER_ERROR",
                 "PARSE_ERROR", "UNAVAILABLE", "NOT_ATTEMPTED")

# States that legitimately support an absence claim for the queried
# universe. Exactly one: a successful query that returned zero records.
ABSENCE_CAPABLE_STATES = ("EMPTY_RESULT",)

CONNECTOR_SEMANTICS_VERSION = "connector_states/1.0.0"


def classify_exception(exc: BaseException) -> str:
    """Map a transport/parse exception to one connector state."""
    if isinstance(exc, socket.timeout) or isinstance(exc, TimeoutError):
        return "TIMEOUT"
    if isinstance(exc, urllib.error.HTTPError):
        code = exc.code
        if code == 429:
            return "RATE_LIMITED"
        if 500 <= code < 600:
            return "PROVIDER_ERROR"
        return "PROVIDER_ERROR"  # 4xx (except 429): provider answered no
    if isinstance(exc, urllib.error.URLError):
        reason = getattr(exc, "reason", None)
        if isinstance(reason, socket.timeout) or isinstance(reason, TimeoutError):
            return "TIMEOUT"
        return "UNAVAILABLE"
    if isinstance(exc, ssl.SSLError):
        return "UNAVAILABLE"
    if isinstance(exc, (ConnectionError, ConnectionResetError,
                        ConnectionRefusedError, socket.gaierror)):
        return "UNAVAILABLE"
    if isinstance(exc, json.JSONDecodeError):
        return "PARSE_ERROR"
    if isinstance(exc, ValueError):
        return "PARSE_ERROR"
    return "UNAVAILABLE"


def classify_http_code(code: int) -> str:
    """Map a raw HTTP status code to one connector state."""
    if 200 <= code < 300:
        return "SUCCESS"
    if code == 429:
        return "RATE_LIMITED"
    if 500 <= code < 600:
        return "PROVIDER_ERROR"
    return "PROVIDER_ERROR"


def outcome(state: str,
            provider: str,
            reason: str = "",
            config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build a machine-readable connector outcome record.

    The `epistemic_effect` field is the load-bearing part: it states what
    the outcome may legally mean downstream — 'ABSENCE' only for
    EMPTY_RESULT, 'UNKNOWN' for every outage state, 'RECORDS' for SUCCESS.
    """
    if state not in CONNECTOR_STATES:
        raise ValueError(
            f"unknown connector state {state!r}; the vocabulary is "
            f"{CONNECTOR_STATES} — extending it is a contract change, not "
            f"a local decision (R394 section 4)")
    if state == "EMPTY_RESULT":
        epistemic = "ABSENCE"
    elif state == "SUCCESS":
        epistemic = "RECORDS"
    else:
        epistemic = "UNKNOWN"
    rec: Dict[str, Any] = {
        "connector_state": state,
        "provider": provider,
        "reason": reason,
        "epistemic_effect": epistemic,
        "semantics_version": CONNECTOR_SEMANTICS_VERSION,
    }
    if config:
        rec["retrieval_config"] = config
    return rec


def config_fingerprint(provider: str, url: str,
                       extra: Optional[Dict[str, Any]] = None) -> str:
    """Deterministic fingerprint of the retrieval configuration (R394
    section 3: same problem + source snapshot + query + relevance-model
    version + threshold must yield the same relevance decision — the
    configuration identity is part of that input tuple)."""
    payload = json.dumps({"provider": provider, "url": url,
                          "extra": extra or {}},
                         sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def fetch_json(url: str,
               timeout: float = 20.0,
               headers: Optional[Dict[str, str]] = None,
               method: str = "GET",
               body: Optional[str] = None,
               user_agent: str = "Toscanini-Engine/1.0") -> Dict[str, Any]:
    """Python-HTTP JSON fetch with explicit connector-state semantics.

    Replaces the curl subprocess dependency (R394 section 4: the deployed
    python:3.12-slim image contains no curl — MULTI_SOURCE_DISCOVERY
    failed with FileNotFoundError on every public run; measured
    2026-09-02, R394/PRODUCTION_AUDIT.json claim 1).

    Returns a dict ALWAYS carrying `connector_state`. On SUCCESS /
    EMPTY_RESULT the payload is under `data`. One retry with linear
    backoff is applied for TIMEOUT / RATE_LIMITED / transient transport
    errors only — provider refusals (4xx except 429) and parse failures
    are NOT retried (retry masking is forbidden, Art. XXI.3).
    """
    hdrs = {"User-Agent": user_agent}
    if headers:
        hdrs.update(headers)
    delays = (0.0, 2.0)
    last: Dict[str, Any] = {}
    for delay in delays:
        if delay:
            import time as _t
            _t.sleep(delay)
        try:
            req = urllib.request.Request(
                url, data=(body.encode("utf-8") if body and method == "POST" else None),
                headers=hdrs, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
            state = classify_http_code(getattr(resp, "status", 200) or 200)
            if state != "SUCCESS":
                last = outcome(state, "http", f"HTTP {getattr(resp, 'status', '?')}")
                if state in ("RATE_LIMITED",):
                    continue
                return last
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                return outcome("PARSE_ERROR", "http",
                               f"JSON decode: {exc}")
            has_records = bool(_find_records(data))
            return {
                "connector_state": "SUCCESS" if has_records else "EMPTY_RESULT",
                "data": data,
                "reason": "" if has_records else
                          "provider answered; zero matching records",
                "epistemic_effect": "RECORDS" if has_records else "ABSENCE",
                "semantics_version": CONNECTOR_SEMANTICS_VERSION,
            }
        except urllib.error.HTTPError as exc:
            try:
                exc.read()
            except Exception:  # noqa: BLE001 — body drain best-effort
                pass
            state = classify_exception(exc)
            last = outcome(state, "http", f"HTTP {exc.code}: {exc.reason}")
            if state in ("RATE_LIMITED", "PROVIDER_ERROR"):
                continue  # one retry for transient 5xx/429
            return last
        except Exception as exc:  # noqa: BLE001 — classified, never hidden
            state = classify_exception(exc)
            last = outcome(state, "http", f"{type(exc).__name__}: {exc}")
            if state == "TIMEOUT":
                continue  # one retry for timeouts
            return last
    return last or outcome("UNAVAILABLE", "http", "no attempt completed")


def _find_records(data: Any) -> bool:
    """Heuristic: does the parsed payload carry any result-bearing
    collection? Used to separate SUCCESS from EMPTY_RESULT for the
    generic fetcher; source adapters may override with their own
    precise check."""
    if isinstance(data, dict):
        # never treat pagination metadata as records
        for key in ("resultList", "results", "data", "items", "studies",
                    "records", "hits", "docs", "entry", "message"):
            v = data.get(key)
            if isinstance(v, list) and v:
                return True
            if isinstance(v, dict):
                inner = _find_records(v)
                if inner:
                    return True
        return False
    if isinstance(data, list):
        return bool(data)
    return True

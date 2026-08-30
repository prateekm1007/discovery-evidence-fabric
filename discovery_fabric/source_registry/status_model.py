"""Mechanically honest source-status model (CEO directive 2026-08-30 #5):

    Make source status mechanically honest: LIVE / DEGRADED / BLOCKED /
    NOT_INTEGRATED.

VOCABULARY RENAME (recorded epistemic event, Art. XI)
-----------------------------------------------------
The pre-2026-08-30 vocabulary was LIVE / DEGRADED / UNAVAILABLE /
NOT_INTEGRATED. `UNAVAILABLE` conflated materially different conditions:
a missing API key, a provider retiring an endpoint, our egress IP being
blocked, a registration wall, a 5xx, and a network timeout all collapsed
into one word — which is exactly the kind of semantic blur the CEO's
directive targets. The rename UNAVAILABLE -> BLOCKED is vocabulary-only:
every BLOCKED status carries a MECHANICALLY DERIVED block class (derived
from the measured request status / HTTP code / error signature, never
hand-assigned) plus the measured evidence and its date.

Old artifacts that say UNAVAILABLE remain interpretable through
LEGACY_VOCABULARY_MAP. History is not rewritten; the rename is recorded
here.

BLOCK CLASSES (machine-derived; derivation table below)
-------------------------------------------------------
AUTH               credential missing/invalid — engine-side unblockable
                   without a key action
EGRESS             provider answered by blocking us (IP/ASN/bot), or an
                   intermediary blocks the endpoint from this network
PROVIDER_RETIRED   endpoint retired/changed shape (incl. HTML-200 masks)
REGISTRATION       provider requires account/registration/login we do
                   not have (access-policy wall, not a technical fault)
HTTP_5XX           provider error page without a more specific signature
NETWORK            timeout / connection-level failure
METERED_WINDOW     metered source with no live proof inside the metered
                   window (probe suppressed by quota policy)
CONNECTOR_IMPORT   connector module failed to import (code defect —
                   ALWAYS an engine-side action item, never the
                   provider's fault)

Constitutional anchors: Art. XXI.3 (a provider failure is recorded as the
failure it is), Art. XXV (unknown stays unknown), Art. XXVII (classes are
derived from measured signatures with declared rules, not invented).
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

STATUS_VOCABULARY = ("LIVE", "DEGRADED", "BLOCKED", "NOT_INTEGRATED")

# Art. XI: the rename is a recorded event, old artifacts stay readable.
LEGACY_VOCABULARY_MAP = {
    "UNAVAILABLE": "BLOCKED",
    "legacy_note": (
        "2026-08-30 vocabulary rename (CEO directive #5): UNAVAILABLE -> "
        "BLOCKED with machine-derived block_class. Old artifacts saying "
        "UNAVAILABLE are interpreted through this map; they are not "
        "rewritten."
    ),
}

BLOCK_CLASSES = (
    "AUTH", "EGRESS", "PROVIDER_RETIRED", "REGISTRATION",
    "HTTP_5XX", "NETWORK", "METERED_WINDOW", "CONNECTOR_IMPORT",
    "ENGINE_QUERY_GRAMMAR",
)

BLOCK_CLASS_DERIVATION = {
    "AUTH": (
        "request_status == AUTH_FAILED, or the measured error names a "
        "missing/invalid credential (API key not configured, 401)"
    ),
    "EGRESS": (
        "HTTP 403 naming our IP/ASN/bot (provider blocks us), or a "
        "bot-block 503, or an explicit network-level block signature"
    ),
    "PROVIDER_RETIRED": (
        "measured error names endpoint retirement or an HTML-200 mask "
        "(API endpoint replaced by an HTML page)"
    ),
    "REGISTRATION": (
        "measured error names registration/login/bot-protection walls "
        "(access-policy requirement, not a technical failure)"
    ),
    "HTTP_5XX": "HTTP >= 500 without a more specific signature",
    "NETWORK": "TIMEOUT / SEARCH_FAILED (connection-level failure)",
    "METERED_WINDOW": (
        "metered source: no live proof inside the metered window; live "
        "probes suppressed by quota policy (disclosed, dated)"
    ),
    "CONNECTOR_IMPORT": "connector module import failed (code defect)",
    "ENGINE_QUERY_GRAMMAR": (
        "request_status == GRAMMAR_MISMATCH — the ENGINE asked a source a "
        "question outside its declared grammar (e.g. free text to a "
        "make|model|year endpoint). Engine-side routing defect, NOT a "
        "provider failure and NOT absence (Art. XXV): the source's health "
        "is unmeasured through that query until the engine asks correctly"
    ),
}

# Signature rules, checked IN ORDER (most specific first). Ordering is
# load-bearing and adversarially tested (tests/test_status_model.py):
#   1. PROVIDER_RETIRED — retired endpoints often ALSO 401/403, so
#      retirement must out-rank AUTH.
#   2. REGISTRATION — access-policy walls ("registration required",
#      "bot-protection: register") must out-rank the generic bot-check.
#   3. EGRESS — provider-side blocks of US (IP/ASN/bot-check/captcha/403).
#   4. AUTH — credential missing/invalid.
# Only then do the request-status fast-paths and HTTP-code fallbacks run.
_SIG_RETIRED = re.compile(
    r"retired|deprecat|html page measured|endpoint.*(moved|changed)|"
    r"no longer", re.I)
_SIG_REGISTRATION = re.compile(
    r"registration|register\b|login|sign.?in|account required", re.I)
_SIG_EGRESS = re.compile(
    r"ip address|\basn\b|blocked from accessing|bot.?check|bot.?block|"
    r"captcha|forbidden", re.I)
_SIG_AUTH = re.compile(
    r"api[_ ]?key|not configured|no \w* ?credentials|unauthorized|token|"
    r"402 payment|subscription", re.I)

_RULES: Tuple[Tuple[str, re.Pattern], ...] = (
    ("PROVIDER_RETIRED", _SIG_RETIRED),
    ("REGISTRATION", _SIG_REGISTRATION),
    ("EGRESS", _SIG_EGRESS),
    ("AUTH", _SIG_AUTH),
)


def classify_block(request_status: Optional[str] = None,
                   error: Optional[str] = None,
                   http_status: Optional[int] = None,
                   metered_window: bool = False) -> Dict[str, Any]:
    """Derive (BLOCKED, block_class, evidence) from the measured signature.

    Pure function of its inputs — no registry lookups, no state, no
    hand-assigned overrides. Whatever it returns is traceable to the exact
    rule that fired (Art. XXVII).
    """
    err = error or ""
    fired_rule = None

    if metered_window:
        block_class = "METERED_WINDOW"
        fired_rule = "metered_window=True (no live proof in window)"
    elif request_status == "CONNECTOR_IMPORT":
        block_class = "CONNECTOR_IMPORT"
        fired_rule = "request_status == CONNECTOR_IMPORT (engine code defect)"
    elif request_status == "GRAMMAR_MISMATCH":
        block_class = "ENGINE_QUERY_GRAMMAR"
        fired_rule = (
            "request_status == GRAMMAR_MISMATCH (engine asked outside the "
            "source's declared grammar — engine-side defect, provider "
            "unmeasured through this query)"
        )
    else:
        for cls, pattern in _RULES:
            if pattern.search(err):
                block_class = cls
                fired_rule = (
                    f"signature {pattern.pattern!r} matched measured error")
                break
        else:
            if request_status == "AUTH_FAILED":
                block_class = "AUTH"
                fired_rule = "request_status == AUTH_FAILED (no finer signature)"
            elif request_status in ("TIMEOUT", "SEARCH_FAILED"):
                block_class = "NETWORK"
                fired_rule = f"request_status == {request_status}"
            elif (http_status or 0) >= 500:
                block_class = "HTTP_5XX"
                fired_rule = f"http_status {http_status} >= 500"
            elif (http_status or 0) == 403:
                block_class = "EGRESS"
                fired_rule = "http_status 403 without finer signature"
            elif (http_status or 0) == 401:
                block_class = "AUTH"
                fired_rule = "http_status 401 without finer signature"
            else:
                block_class = "NETWORK"
                fired_rule = (
                    f"unmapped signature (status={request_status!r}, "
                    f"http={http_status!r}) defaulting to NETWORK — class "
                    "disclosed as least-specific"
                )

    return {
        "status": "BLOCKED",
        "block_class": block_class,
        "block_evidence": {
            "request_status": request_status,
            "http_status": http_status,
            "error_excerpt": err[:220] or None,
            "fired_rule": fired_rule,
        },
    }


def map_legacy_status(status: str) -> str:
    """Interpret old-artifact statuses through the rename map (Art. XI)."""
    return LEGACY_VOCABULARY_MAP.get(status, status)

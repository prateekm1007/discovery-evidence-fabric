"""Rate-limit backoff policy tests (hermetic) — 2026-08-30 CEO fix-degraded.

Policy in ConnectorBase._execute:
- non-metered source + transient 429 -> bounded retries with exponential
  backoff, provider Retry-After honored when present
- metered source + 429 -> NO retry (every retry burns provider quota)
- budget-window exhaustion ($0 remaining) -> fails honestly after retries;
  never converts RATE_LIMITED into EMPTY (Art. XXI.3)
"""

from __future__ import annotations

import sys
import urllib.error
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from discovery_fabric.source_registry.base import (
    ConnectorBase, STATUS_OK, STATUS_RATE_LIMITED,
)
from discovery_fabric.source_registry.connectors.scientific import (
    OpenAlexConnector, SemanticScholarConnector,
)
from discovery_fabric.source_registry.connectors.patents import PatentBearConnector


def _http_error(code, body=b"{}", headers=None):
    err = urllib.error.HTTPError("url", code, "err", headers or {}, None)
    err.read = lambda: body
    return err


class _FakeConn(OpenAlexConnector):
    """Non-metered concrete connector with instrumented request."""
    def __init__(self, statuses):
        self.statuses = list(statuses)
        self.calls = 0

    def _request(self, url, timeout=25):
        self.calls += 1
        st = self.statuses.pop(0) if self.statuses else STATUS_OK
        if st == STATUS_RATE_LIMITED:
            return (b'{"error":"Too Many Requests","Retry-After":"2"}',
                    STATUS_RATE_LIMITED, 429, "HTTP 429 | Retry-After: 2", None)
        return (b'{"results":[]}', STATUS_OK, 200, None, "plenty")


def test_non_metered_retries_rate_limit_and_recovers():
    conn = _FakeConn([STATUS_RATE_LIMITED, STATUS_OK])
    with mock.patch("time.sleep") as slept:
        result = conn._execute("q")
    assert conn.calls == 2
    # recovered: provider answered (EMPTY here = definitive zero, ok=True)
    assert result.ok is True
    assert result.status in ("OK", "EMPTY")
    assert "recovered after 1 backoff" in (result.error or "")


def test_retry_after_header_honored_over_exponential():
    conn = _FakeConn([STATUS_RATE_LIMITED, STATUS_OK])
    with mock.patch("time.sleep") as slept:
        conn._execute("q")
        delay = slept.call_args_list[0].args[0]
    assert delay == 2  # Retry-After: 2 wins over 2**0*5


def test_exhausted_retries_fail_honestly_rate_limited():
    conn = _FakeConn([STATUS_RATE_LIMITED] * 5)
    conn.RATE_LIMIT_RETRIES = 2
    conn.BACKOFF_BASE_SECONDS = 0.01  # keep the test fast
    with mock.patch("time.sleep"):
        result = conn._execute("q")
    assert result.status == STATUS_RATE_LIMITED
    assert result.ok is False
    assert conn.calls == 3  # initial + 2 retries


def test_metered_source_never_auto_retries():
    conn = PatentBearConnector()
    assert conn.is_metered() is True
    calls = {"n": 0}

    def fake_request(url, timeout=25):
        calls["n"] += 1
        return (b"{}", STATUS_RATE_LIMITED, 429, "HTTP 429", None)

    with mock.patch.object(conn, "_request", side_effect=fake_request):
        with mock.patch("time.sleep") as slept:
            result = conn._execute("q")
    assert calls["n"] == 1          # single attempt — no quota burn
    assert slept.call_count == 0    # no waiting either
    assert result.status == STATUS_RATE_LIMITED


def test_s2_key_header_only_when_provisioned():
    conn = SemanticScholarConnector()
    with mock.patch("discovery_fabric.source_registry.keys.load_key",
                    return_value="S2KEY"):
        assert conn.request_headers() == {"x-api-key": "S2KEY"}
    with mock.patch("discovery_fabric.source_registry.keys.load_key",
                    return_value=""):
        assert conn.request_headers() == {}
        # and the URL never carries the key
        assert "api-key" not in conn.build_url("q")

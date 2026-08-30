"""uspto_odp adapter: retired-endpoint mask control (hermetic).

The 2026-08-30 live probe measured api.patentsview.org serving an HTML SPA
page with HTTP 200 — the adapter used to die with 'JSON parse error:
Expecting value', masking an endpoint retirement as a transient parse
failure (Art. XXI.3 violation class). These tests pin:
- keyless -> immediate AUTH_FAILURE (no burn, no mask)
- 200-with-HTML + key -> ENDPOINT_RETIRED (never a JSON parse crash)
- 200-with-JSON + key -> normal parse path
"""

from __future__ import annotations

import io
import sys
import urllib.error
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from discovery_fabric.prior_art_v2 import uspto_odp_adapter as mod


def test_keyless_fails_auth_immediately():
    with mock.patch.object(mod, "_load_uspto_key", return_value=""):
        att = mod.uspto_search("pacemaker", limit=3)
    assert att.failure_substate == "AUTH_FAILURE"
    assert "retired" in (att.api_error_msg or "")
    assert att.patents == []


class _Resp(io.BytesIO):
    def __init__(self, body, ctype):
        super().__init__(body)
        self.status = 200
        self.headers = {"Content-Type": ctype}


def test_html_200_is_endpoint_retired_not_parse_error():
    with mock.patch.object(mod, "_load_uspto_key", return_value="K"):
        with mock.patch.object(
            mod.urllib.request, "urlopen",
            return_value=_Resp(b"<!doctype html><html>SPA</html>", "text/html"),
        ):
            att = mod.uspto_search("pacemaker", limit=3)
    assert att.failure_substate == "ENDPOINT_RETIRED"
    assert "JSON parse error" not in (att.api_error_msg or "")
    assert "text/html" in att.api_error_msg


def test_json_200_parses_records():
    payload = (
        b'{"patents": [{"patent_number": "1234567", "patent_title": "T",'
        b' "patent_abstract": "A", "patent_date": "2020-01-01",'
        b' "assignees": []}]}'
    )
    with mock.patch.object(mod, "_load_uspto_key", return_value="K"):
        with mock.patch.object(
            mod.urllib.request, "urlopen",
            return_value=_Resp(payload, "application/json"),
        ):
            att = mod.uspto_search("pacemaker", limit=3)
    assert att.normalized_state == "SEARCH_RETURNED_PATENTS"
    assert att.patents and att.patents[0].patent_number == "1234567"


def test_legacy_endpoint_constant_records_retirement_date():
    # the measured retirement date is part of the audit trail (Art. XXXI)
    assert mod._PV_ENDPOINTS_MEASURED_RETIRED == "2026-08-30"
    assert "search.patentsview.org" in mod.USPTO_PV_BASE

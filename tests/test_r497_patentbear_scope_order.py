"""R497 — PatentBear scope-order fix: hermetic tests (no network).

The measured defect (2026-09-18, live, operator's rotated pb_live_ key):
scope="all" now returns HTTP 200 with EMPTY hits for guaranteed-hit queries
("virtual reality": all -> 200/0 hits vs patents -> 200/num_hits=410163/5
records). The R378 all-first order false-zeroed real results into
NO_RESULTS — an Art. XXI.3 violation (provider-side empty is NEVER absence).

The fix under test (all hermetic, _http_post stubbed):
  1. "patents" is queried FIRST (the reliable scope);
  2. "all" is consulted only when "patents" measures zero hits;
  3. true zero requires BOTH scopes empty;
  4. num_hits>0 with an empty hits list is PROVIDER_INCONSISTENT (typed
     failure), never absence;
  5. a non-200 on "patents" is a typed failure with NO all-scope fallback;
  6. a usage-less response never overwrites a numeric meter with UNKNOWN;
  7. a numeric monthly_remaining still persists (R378 behavior preserved);
  8. the reserve-floor guard still refuses before any network call.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from discovery_fabric.prior_art_v2 import sources as src  # noqa: E402


def _mcp_body(inner: dict, http_status: int = 200):
    """Build an MCP JSON-RPC envelope around an inner search payload."""
    if http_status != 200:
        return http_status, json.dumps(inner).encode(), 10
    envelope = {"jsonrpc": "2.0", "id": 1, "result": {
        "content": [{"type": "text", "text": json.dumps(inner)}]}}
    return 200, json.dumps(envelope).encode(), 10


def _inner(hits=None, num_hits=0, monthly_remaining=None):
    inner = {"query": "q", "scope": "patents", "num_hits": num_hits,
             "elapsed_time_micros": 1, "hits": hits or []}
    if monthly_remaining is not None:
        inner["usage"] = {"allowed": True, "monthly_limit": 20,
                          "monthly_used": 5,
                          "monthly_remaining": monthly_remaining}
    return inner


HIT = {"id": "US5774878A", "source_type": "publication",
       "title": "Virtual reality generator for use with financial information",
       "abstract": "A virtual reality generator...",
       "snippet": {}}


@pytest.fixture()
def hermetic_meter(tmp_path, monkeypatch):
    """Isolate the persisted meter per test; UNKNOWN by default."""
    meter = tmp_path / "patentbear_meter.json"
    monkeypatch.setattr(src, "PATENTBEAR_METER_PATH", meter)
    monkeypatch.setattr(src, "PATENT_BEAR_KEY", "pb_live_TESTHERMETICKEY")
    return meter


def test_patents_scope_queried_first(hermetic_meter):
    """The first wire call must be scope='patents' (the reliable scope)."""
    calls = []

    def fake_post(url, payload, headers=None, timeout=30):
        calls.append(json.loads(payload)["params"]["arguments"]["scope"])
        return _mcp_body(_inner(hits=[HIT], num_hits=1,
                                monthly_remaining=13))

    with mock.patch.object(src, "_http_post", side_effect=fake_post):
        r = src.search_patent_bear("virtual reality", 5)
    assert r.success and len(r.hits) == 1
    assert calls == ["patents"], "patents must be the FIRST scope queried"


def test_hits_on_patents_means_no_all_call(hermetic_meter):
    """Hits on the reliable scope: the broken 'all' scope is never consulted
    (quota never burned on a known-broken path)."""
    calls = []

    def fake_post(url, payload, headers=None, timeout=30):
        calls.append(1)
        return _mcp_body(_inner(hits=[HIT], num_hits=1,
                                monthly_remaining=13))

    with mock.patch.object(src, "_http_post", side_effect=fake_post):
        src.search_patent_bear("virtual reality", 5)
    assert len(calls) == 1


def test_zero_on_patents_consults_all_then_true_zero(hermetic_meter):
    """Zero on patents -> ONE all-scope attempt; both empty -> success with
    zero hits (the honest NO_RESULTS shape: both scopes measured empty)."""
    calls = []

    def fake_post(url, payload, headers=None, timeout=30):
        scope = json.loads(payload)["params"]["arguments"]["scope"]
        calls.append(scope)
        return _mcp_body(_inner(hits=[], num_hits=0))

    with mock.patch.object(src, "_http_post", side_effect=fake_post):
        r = src.search_patent_bear("qqzzxxwbar9", 5)
    assert calls == ["patents", "all"]
    assert r.success and len(r.hits) == 0


def test_zero_on_patents_npl_hits_on_all(hermetic_meter):
    """Zero patents + NPL hits on 'all' -> the all-scope results are served
    (NPL coverage preserved through the fallback)."""
    npl_hit = dict(HIT, id="doi:10.1/x", source_type="article")

    def fake_post(url, payload, headers=None, timeout=30):
        scope = json.loads(payload)["params"]["arguments"]["scope"]
        if scope == "patents":
            return _mcp_body(_inner(hits=[], num_hits=0))
        return _mcp_body(_inner(hits=[npl_hit], num_hits=1))

    with mock.patch.object(src, "_http_post", side_effect=fake_post):
        r = src.search_patent_bear("some npl topic", 5)
    assert r.success and len(r.hits) == 1
    assert r.hits[0].patent_id is None  # article, not a patent


def test_num_hits_positive_empty_hits_is_provider_inconsistent(hermetic_meter):
    """num_hits>0 with an empty hits list is a TYPED FAILURE — the index
    matched but the provider returned no records. Never absence (Art. XXI.3)."""
    def fake_post(url, payload, headers=None, timeout=30):
        return _mcp_body(_inner(hits=[], num_hits=410163))

    with mock.patch.object(src, "_http_post", side_effect=fake_post):
        r = src.search_patent_bear("virtual reality", 5)
    assert not r.success
    assert "PROVIDER_INCONSISTENT" in (r.error or "")
    assert "never absence" in (r.error or "")


def test_non_200_on_patents_is_typed_failure_no_all_fallback(hermetic_meter):
    """A provider failure on the reliable scope is typed and NEVER falls back
    to the broken 'all' scope (which would mask the failure as zero)."""
    calls = []

    def fake_post(url, payload, headers=None, timeout=30):
        calls.append(json.loads(payload)["params"]["arguments"]["scope"])
        return 502, b"bad gateway", 10

    with mock.patch.object(src, "_http_post", side_effect=fake_post):
        r = src.search_patent_bear("virtual reality", 5)
    assert not r.success and r.error_code == 502
    assert calls == ["patents"], "no all-scope fallback on provider failure"


def test_meter_never_regresses_to_unknown_on_usageless_response(hermetic_meter):
    """R497 meter guard: a response without monthly_remaining must NOT
    overwrite a persisted numeric meter (measured live regression)."""
    hermetic_meter.write_text(json.dumps(
        {"monthly_remaining": 13, "updated_at": "t0", "reserve_floor": 2}))

    def fake_post(url, payload, headers=None, timeout=30):
        return _mcp_body(_inner(hits=[HIT], num_hits=1))  # no usage block

    with mock.patch.object(src, "_http_post", side_effect=fake_post):
        src.search_patent_bear("virtual reality", 5)
    meter = json.loads(hermetic_meter.read_text())
    assert meter["monthly_remaining"] == 13, \
        "usage-less response must not regress the meter to UNKNOWN"


def test_meter_updates_on_numeric_remaining(hermetic_meter):
    """R378 behavior preserved: a provider-reported numeric
    monthly_remaining persists after the call."""
    hermetic_meter.write_text(json.dumps(
        {"monthly_remaining": 13, "updated_at": "t0", "reserve_floor": 2}))

    def fake_post(url, payload, headers=None, timeout=30):
        return _mcp_body(_inner(hits=[HIT], num_hits=1,
                                monthly_remaining=12))

    with mock.patch.object(src, "_http_post", side_effect=fake_post):
        r = src.search_patent_bear("virtual reality", 5)
    assert r.rate_limit_remaining == 12
    assert json.loads(hermetic_meter.read_text())["monthly_remaining"] == 12


def test_reserve_floor_guard_refuses_before_network(hermetic_meter):
    """R378 guard preserved: a persisted meter at/below the floor refuses
    BEFORE any network call (the refusal is an error, never absence)."""
    hermetic_meter.write_text(json.dumps(
        {"monthly_remaining": 2, "updated_at": "t0", "reserve_floor": 2}))
    with mock.patch.object(
            src, "_http_post",
            side_effect=AssertionError("network must not be touched")):
        r = src.search_patent_bear("virtual reality", 5)
    assert not r.success and r.error_code == 429
    assert "reserve floor" in (r.error or "")


def test_missing_key_is_typed_not_absence(hermetic_meter, monkeypatch):
    """No key configured -> typed configuration failure (never absence)."""
    monkeypatch.setattr(src, "PATENT_BEAR_KEY", "")
    r = src.search_patent_bear("virtual reality", 5)
    assert not r.success and "not configured" in (r.error or "")

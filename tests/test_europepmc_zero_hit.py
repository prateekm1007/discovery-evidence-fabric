"""EuropePMC definitive-zero regression (found live 2026-08-30).

The 2026-08-29 health report marked europepmc UNAVAILABLE/PARSE_FAILED
because a zero-hit probe query returned hitCount=0 with NO resultList.result
key and normalize_payload raised ValueError. A definitive provider answer of
zero was misclassified as a provider failure — the exact Art. XXI.3
violation class (provider failure is not absence; and absence, when it IS
the provider's answer, is EMPTY not PARSE_FAILED). Fixed same day; this test
pins the fix in both directions.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from discovery_fabric.source_registry.connectors.scientific import (
    EuropePmcConnector,
)


@pytest.fixture()
def conn():
    return EuropePmcConnector()


def test_zero_hit_without_result_key_is_definitive_empty(conn):
    """Measured provider shape: {'hitCount': 0} with no resultList.result."""
    recs = conn.normalize_payload({"hitCount": 0}, "zz_nonexistent", "sha")
    assert recs == []


def test_zero_hit_with_empty_result_list_is_definitive_empty(conn):
    recs = conn.normalize_payload(
        {"hitCount": 0, "resultList": {"result": []}}, "q", "sha")
    assert recs == []


def test_malformed_payload_still_raises(conn):
    """Not a provider answer at all (no hitCount, no resultList) — the
    parse failure must survive; the fix may not become a swallow-all."""
    with pytest.raises(ValueError):
        conn.normalize_payload({}, "q", "sha")
    with pytest.raises(ValueError):
        conn.normalize_payload({"resultList": {"result": "not-a-list"}}, "q", "sha")


def test_positive_hits_normalize(conn):
    payload = {"hitCount": 1, "resultList": {"result": [{
        "id": "12345", "source": "MED", "title": "T",
        "abstractText": "A", "doi": "10.1/x", "pmid": "12345",
    }]}}
    recs = conn.normalize_payload(payload, "q", "sha")
    assert len(recs) == 1
    assert recs[0].record_id == "europepmc:12345"
    assert recs[0].normalized["doi"] == "10.1/x"

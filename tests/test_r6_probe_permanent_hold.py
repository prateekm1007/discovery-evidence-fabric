#!/usr/bin/env python3
"""R6 A2 follow-up regression (owner round 2026-11-12, measured live):
a PERMANENT-class probe failure (dead key AUTH_FAILURE, gone model,
credit gate, region gate) must HOLD for the capability record's TTL —
the 30 s failure floor re-probed a dead rung 13 times inside one
3-problem chunk (measured in the routing ledger, run root
r1-pipeline+baseline+judge-2026-11-12035842000).

Art. XXV: the fix is measured-reality-driven. Art. LXI: the TTL expiry
still re-probes — an operator key fix is picked up within PROBE_TTL_S,
never silently never."""
import json
import time
from pathlib import Path

import pytest

from discovery_fabric.engine import provider_health as ph
from discovery_fabric.engine import runtime_admission as ra


@pytest.fixture()
def state(tmp_path, monkeypatch):
    p = Path(tmp_path) / "capability_state.json"
    ra.set_state_path(p)
    yield p
    ra.set_state_path(None)


def _record(state_path, failure_class, age_s):
    """Write a probe-failure record aged age_s seconds directly (the
    probe's own persistence shape, record_capability)."""
    rec = {
        "provider": "openrouter",
        "model": "deepseek/deepseek-v4-flash-0731",
        "ok": False,
        "failure_class": failure_class,
        "source": "probe",
        "at_epoch": time.time() - age_s,
        "latency_ms": 40,
        "note": failure_class or "",
    }
    state_path.write_text(
        json.dumps({"capability_records": {
            "openrouter::deepseek/deepseek-v4-flash-0731": rec}}),
        encoding="utf-8")
    return rec


def test_auth_failure_holds_for_ttl(state):
    """AUTH_FAILURE 10 s old (< floor 30): the OLD code re-probed (age <
    floor -> True). The fix: a permanent class holds — no probe."""
    _record(state, "AUTH_FAILURE", age_s=10)
    assert ra.requires_probe("openrouter",
                             "deepseek/deepseek-v4-flash-0731") is False


def test_credit_and_region_and_gone_hold(state):
    """Every permanent class holds at ages that would cross the 30 s
    floor (the measured 13-probe storm class)."""
    for cls in ("CREDIT_EXHAUSTED", "REGION_NOT_SERVED", "GONE",
                "MODEL_NOT_FOUND"):
        _record(state, cls, age_s=45)
        assert ra.requires_probe(
            "openrouter", "deepseek/deepseek-v4-flash-0731") is False, cls


def test_transient_failure_still_ages_out_at_floor(state):
    """TIMEOUT 45 s old (> floor 30, < TTL): still re-probes — the
    R451-C1.3 transient-outage recovery is unchanged."""
    _record(state, "TIMEOUT", age_s=45)
    assert ra.requires_probe("openrouter",
                             "deepseek/deepseek-v4-flash-0731") is True


def test_ttl_expiry_reprobes_permanent_too(state):
    """A permanent failure past the capability TTL is PROBE_EXPIRED ->
    re-probe (operator key fix picked up within TTL, never never)."""
    _record(state, "AUTH_FAILURE",
            age_s=ra.capability_ttl_s() + 10)
    assert ra.requires_probe("openrouter",
                             "deepseek/deepseek-v4-flash-0731") is True


def test_permanent_class_vocabulary_matches_taxonomy(state):
    """The hold vocabulary is exactly the taxonomy's permanent set (the
    comment block's own list) — a drift on either side fails here."""
    expected = {"AUTH_FAILURE", "GONE", "MODEL_NOT_FOUND",
                "CREDIT_EXHAUSTED", "REGION_NOT_SERVED"}
    assert set(ra.PERMANENT_PROBE_CLASSES) == expected
    # transient classes are NOT permanent
    assert not (set(ra.TRANSIENT_PROBE_CLASSES)
                & set(ra.PERMANENT_PROBE_CLASSES))
    # every permanent class exists in the provider-health taxonomy
    for cls in ra.PERMANENT_PROBE_CLASSES:
        assert getattr(ph, cls) == cls

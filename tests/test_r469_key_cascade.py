#!/usr/bin/env python3
"""R469 — the seven-key rotation cascade tests.

The operator's directive: atria is the discovery engine's default API;
when one key exhausts the engine advances to the next within the same
call; RATE_LIMITED never advances; all-dead types honestly; every
advance is recorded with NO key material anywhere.
"""
from __future__ import annotations

import io
import sys
import urllib.error
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import llm_registry as reg  # noqa: E402

SLOTS = ["ATRIA_API_KEY"] + [f"ATRIA_API_KEY_{i}" for i in range(2, 8)]
SPEC = reg._SPEC_BY_ID["atria"]


def _http_error(code: int, body: bytes) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        "https://api.atria-asi.ai/v1/chat/completions", code, "err",
        {}, io.BytesIO(body))


def _content_payload(text: str = "FIELD_MECHANISM: ok") -> dict:
    return {"choices": [{"message": {"content": text},
                         "finish_reason": "stop"}]}


def _fresh(monkeypatch):
    reg._KEY_STATE.clear()
    reg._LAST_KEY_ADVANCES.clear()
    reg._LAST_KEY_SLOT.clear()
    for name in SLOTS:
        monkeypatch.setenv(name, f"testkey-for-{name}")
    # every OTHER provider's env stays whatever it is; the atria spec
    # is exercised directly


def test_atria_cascade_declared():
    assert list(SPEC.key_env_cascade or []) == SLOTS
    # every other registered rung keeps the single-slot behavior
    for s in reg.PROVIDER_SPECS:
        if s.provider_id != "atria":
            assert s.key_env_cascade is None, s.provider_id


def test_cascade_advances_on_credit_exhausted(monkeypatch):
    _fresh(monkeypatch)
    calls = []

    def fake_post(url, payload, headers, timeout):
        calls.append(headers["Authorization"])
        if len(calls) == 1:
            raise _http_error(402, b'{"error": {"message": '
                                 b'"insufficient balance"}}')
        return _content_payload()

    with mock.patch.object(reg, "_post_json", fake_post):
        out = reg._call_openai_flavor(SPEC, [{"role": "user",
                                              "content": "p"}], 30, 512)
    assert out == "FIELD_MECHANISM: ok"
    assert len(calls) == 2
    # slot 1 is dead + recorded; slot 2 served
    assert reg._KEY_STATE[("atria", "ATRIA_API_KEY")]["state"] == "DEAD"
    assert reg._KEY_STATE[("atria", "ATRIA_API_KEY")][
        "failure_class"] == "CREDIT_EXHAUSTED"
    assert reg._LAST_KEY_SLOT["atria"] == "ATRIA_API_KEY_2"
    assert reg._LAST_KEY_ADVANCES[0]["failure_class"] == "CREDIT_EXHAUSTED"


def test_cascade_advances_on_auth_failure(monkeypatch):
    _fresh(monkeypatch)

    def fake_post(url, payload, headers, timeout):
        raise _http_error(401, b'{"error": {"message": "bad key"}}')

    served = []

    def post_two(url, payload, headers, timeout):
        served.append(headers["Authorization"])
        if len(served) == 1:
            raise _http_error(401, b'{"error": {"message": "bad key"}}')
        return _content_payload()

    with mock.patch.object(reg, "_post_json", post_two):
        out = reg._call_openai_flavor(SPEC, [{"role": "user",
                                              "content": "p"}], 30, 512)
    assert out
    assert reg._KEY_STATE[("atria", "ATRIA_API_KEY")][
        "failure_class"] == "AUTH_FAILURE"


def test_rate_limited_does_not_advance(monkeypatch):
    _fresh(monkeypatch)

    def fake_post(url, payload, headers, timeout):
        raise _http_error(429, b'{"error": {"message": "busy pool"}}')

    with mock.patch.object(reg, "_post_json", fake_post):
        try:
            reg._call_openai_flavor(SPEC, [{"role": "user",
                                            "content": "p"}], 30, 512)
            raise AssertionError("expected the 429 to re-raise")
        except urllib.error.HTTPError:
            pass
    # NO slot was marked dead; no advance recorded
    assert not reg._KEY_STATE
    assert not reg._LAST_KEY_ADVANCES


def test_all_slots_dead_types_honestly(monkeypatch):
    _fresh(monkeypatch)

    def fake_post(url, payload, headers, timeout):
        raise _http_error(402, b'{"error": {"message": '
                               b'"insufficient balance"}}')

    with mock.patch.object(reg, "_post_json", fake_post):
        try:
            reg._call_openai_flavor(SPEC, [{"role": "user",
                                            "content": "p"}], 30, 512)
            raise AssertionError("expected all-slots-dead failure")
        except RuntimeError as exc:
            assert "all 7 live credential slots dead" in str(exc), exc
    # the ledger holds the full typed story
    assert len(reg._KEY_STATE) == 7
    assert len(reg._LAST_KEY_ADVANCES) == 7


def test_key_envs_drops_dead_and_empty(monkeypatch):
    _fresh(monkeypatch)
    assert reg._key_envs_for(SPEC) == SLOTS
    reg._mark_key_dead("atria", "ATRIA_API_KEY", "CREDIT_EXHAUSTED", "x")
    monkeypatch.delenv("ATRIA_API_KEY_3")
    assert reg._key_envs_for(SPEC) == ["ATRIA_API_KEY_2"] + SLOTS[3:]


def test_single_slot_specs_unchanged(monkeypatch):
    _fresh(monkeypatch)
    other = [s for s in reg.PROVIDER_SPECS
             if s.provider_id == "unorouter"][0]
    monkeypatch.setenv("UNOROUTER_API_KEY", "k-unorouter")
    assert reg._key_envs_for(other) == ["UNOROUTER_API_KEY"]
    assert len(reg._key_envs_for(other)) == 1


def test_no_key_material_in_ledger(monkeypatch):
    _fresh(monkeypatch)
    calls = []

    def post_two(url, payload, headers, timeout):
        calls.append(headers["Authorization"])
        if len(calls) == 1:
            raise _http_error(402, b'{"error": {"message": '
                                   b'"insufficient balance"}}')
        return _content_payload()

    with mock.patch.object(reg, "_post_json", post_two):
        reg._call_openai_flavor(SPEC, [{"role": "user",
                                        "content": "p"}], 30, 512)
    blob = (repr(reg._KEY_STATE) + repr(reg._LAST_KEY_ADVANCES) +
            repr(reg._LAST_KEY_SLOT))
    assert "testkey-for-" not in blob
    assert reg._LAST_KEY_SLOT["atria"] == "ATRIA_API_KEY_2"


def test_walk_gate_uses_the_cascade():
    """The SKIPPED_NO_CREDENTIAL gate consults _key_envs_for — a dead
    primary with live reserve slots still counts as keyed."""
    # structural: the gate expression is the cascade helper (source check)
    src = (REPO / "discovery_fabric" / "engine" /
           "llm_registry.py").read_text()
    assert "not _key_envs_for(_spec_rung)" in src

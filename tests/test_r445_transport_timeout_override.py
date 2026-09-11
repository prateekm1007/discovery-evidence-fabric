"""tests/test_r445_transport_timeout_override.py — the R445-C transport
control battery.

Operator directive R445 section C (resolve the transport/quota blocker
before re-running the frozen causal-evolution cases): the measured
failure was a provider endpoint that ACCEPTS the request and then
stalls — each cascade attempt then consumes the FULL per-call socket
timeout (240 s default) before rotating, so ONE stalling endpoint could
consume >1 h of a single call's bounded cascade (3 attempts x up to 5
hops). The fix is the ENGINE_LLM_TIMEOUT_S operator override in
llm_registry.generate() — the documented R391/R418 operator-override
class: transport-only, explicit, recorded; provider selection policy,
quality tiers, retry semantics, and epistemic semantics untouched.

This battery verifies the control (Art. XVI/XVII — code is a hypothesis,
tests are evidence):
  1. the override, when set, bounds the timeout actually handed to the
     provider call (measured at the call boundary, not the signature);
  2. the default with the override UNSET is exactly 240 (unchanged
     behavior — no silent semantic change);
  3. a malformed override is ignored without crashing (fail-open on
     config parse, never on transport);
  4. the floor: an absurdly small override clamps to 5 s minimum (a
     1-second timeout would starve even healthy calls);
  5. the override applies identically on the RETRY path (the second
     attempt of the same rung uses the same bounded timeout).

Hermetic (Art. IX): the provider call, the routing ladder, and the
health/routing state are monkeypatched — no network, no production
state, deterministic.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import discovery_fabric.engine.llm_registry as reg  # noqa: E402
from discovery_fabric.engine.llm_registry import (  # noqa: E402
    SelectionPolicy)


def _hermetic(monkeypatch, captured, content="FIELD: ok",
              fail_first=0):
    """Deterministic provider-call + ladder replacement (no network)."""
    state = {"calls": 0}

    def fake_call(spec, messages, timeout, max_tokens,
                  model_override=None):
        state["calls"] += 1
        captured.append({"timeout": timeout, "call_no": state["calls"]})
        if state["calls"] <= fail_first:
            raise TimeoutError("simulated stall")
        return content

    monkeypatch.setattr(reg, "_call_openai_flavor", fake_call)

    def fake_ladder(task, role=None, avoid_provider=None,
                    preferred_providers=None, available_providers=None):
        return {"rungs": [{"provider": "nvidia",
                           "model": "test/test-model", "band": "PRIMARY"}],
                "provenance": {"source": "TEST"}}

    import discovery_fabric.engine.model_routing as mr_mod
    monkeypatch.setattr(mr_mod, "build_ladder", fake_ladder)

    def fake_available(pid):
        return True

    # availability matrix must see a credential for the pinned provider
    monkeypatch.setenv("NVIDIA_API_KEY", "fake-key-hermetic-test")
    monkeypatch.setattr(reg, "availability_matrix",
                        lambda: [{"provider_id": "nvidia",
                                  "available": True}])


class TestTimeoutOverride:
    def test_override_bounds_the_call_timeout(self, monkeypatch):
        captured: list = []
        _hermetic(monkeypatch, captured)
        monkeypatch.setenv("ENGINE_LLM_TIMEOUT_S", "37")
        res = reg.generate(
            "prompt", policy=SelectionPolicy(
                preferred_providers=["nvidia"], purpose="general"))
        assert res.ok, f"expected OK, got {res.status} ({res.error})"
        assert captured, "provider call never reached"
        assert captured[0]["timeout"] == 37

    def test_default_240_unchanged_when_unset(self, monkeypatch):
        captured: list = []
        _hermetic(monkeypatch, captured)
        monkeypatch.delenv("ENGINE_LLM_TIMEOUT_S", raising=False)
        res = reg.generate(
            "prompt", policy=SelectionPolicy(
                preferred_providers=["nvidia"], purpose="general"))
        assert res.ok
        assert captured[0]["timeout"] == 240

    def test_malformed_override_ignored_no_crash(self, monkeypatch):
        captured: list = []
        _hermetic(monkeypatch, captured)
        monkeypatch.setenv("ENGINE_LLM_TIMEOUT_S", "not-a-number")
        res = reg.generate(
            "prompt", policy=SelectionPolicy(
                preferred_providers=["nvidia"], purpose="general"))
        assert res.ok
        assert captured[0]["timeout"] == 240  # unchanged

    def test_floor_clamps_absurdly_small_override(self, monkeypatch):
        captured: list = []
        _hermetic(monkeypatch, captured)
        monkeypatch.setenv("ENGINE_LLM_TIMEOUT_S", "1")
        res = reg.generate(
            "prompt", policy=SelectionPolicy(
                preferred_providers=["nvidia"], purpose="general"))
        assert res.ok
        assert captured[0]["timeout"] == 5

    def test_override_applies_on_the_retry_path(self, monkeypatch):
        """First attempt stalls (simulated); the retry uses the SAME
        bounded timeout — the override is not a first-attempt-only
        accident."""
        captured: list = []
        _hermetic(monkeypatch, captured, fail_first=1)
        monkeypatch.setenv("ENGINE_LLM_TIMEOUT_S", "41")
        res = reg.generate(
            "prompt", policy=SelectionPolicy(
                preferred_providers=["nvidia"], purpose="general"))
        assert res.ok
        assert len(captured) == 2
        assert captured[0]["timeout"] == 41
        assert captured[1]["timeout"] == 41


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))

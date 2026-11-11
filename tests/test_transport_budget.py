"""R6 transport call budget (owner directive: FAST and LEAN).

Measured basis (R6 fresh-run 1): the judge-calibration phase sat ~15 min
inside HTTPResponse.readinto on ONE wedged gateway connection because the
per-attempt socket budget was 900 s (x 3 attempts = 45 min worst). The
judge/baseline arms are single-shot short-answer calls with measured OK
latency <= 15 s; the per-attempt budget is now 180 s and every retry
opens a FRESH connection. This test pins the budget at the registry
boundary (the monkeypatched flavor call records what it was asked to
wait).
"""
import pytest

import eval.run as er


def test_transport_call_budget_is_bounded(monkeypatch):
    captured = {}

    def fake_flavor(spec, messages, timeout, max_tokens, model_override=None):
        captured["timeout"] = timeout
        return "ok-content"

    class _Spec:
        provider_id = "zai"
        flavor = "openai"

    monkeypatch.setattr(er, "_SPEC_FIND", None, raising=False)
    import discovery_fabric.engine.llm_registry as lr
    monkeypatch.setattr(lr, "_call_openai_flavor", fake_flavor)
    # no real network: the provider spec lookup must resolve the test spec
    monkeypatch.setattr(lr, "PROVIDER_SPECS", [_Spec()])
    res = er._transport_call("zai", "glm-4-plus", "prompt", "system",
                             max_tokens=64)
    assert res["status"] == "OK", res
    assert captured["timeout"] == 180, captured


def test_transport_call_failure_is_typed(monkeypatch):
    def boom(spec, messages, timeout, max_tokens, model_override=None):
        raise TimeoutError("simulated silent wedge")

    class _Spec:
        provider_id = "zai"
        flavor = "openai"

    import discovery_fabric.engine.llm_registry as lr
    monkeypatch.setattr(lr, "_call_openai_flavor", boom)
    monkeypatch.setattr(lr, "PROVIDER_SPECS", [_Spec()])
    res = er._transport_call("zai", "glm-4-plus", "prompt", "system",
                             max_tokens=64)
    assert res["status"] == "FAIL"
    assert "silent wedge" in (res.get("error") or "")
    assert res["content"] is None

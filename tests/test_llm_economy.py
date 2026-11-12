"""R6 A1/A2 tests (owner round 2026-11-12, zero LLM spend):

A1 — record/replay LLM call cache (hash(prompt, model, params), gitignored
store, rw/ro modes, typed replay miss) + stage memoization (upstream-hash
keyed, memo_hit recorded on the stage_log entry, invalidated by upstream
change).
A2 — per-problem call governor (12 healthy + 6 retry caps, typed stops) +
per-provider retry-storm circuit breaker (3 consecutive transient failures
open it; typed refusal during cooldown; success closes; re-open doubles the
cooldown).
"""
import json
import os
import shutil
import tempfile
import time
import urllib.error
from pathlib import Path

import pytest

from discovery_fabric.engine import llm_economy as econ
from discovery_fabric.engine import llm_registry as lr
from discovery_fabric.engine.candidate import Candidate


@pytest.fixture()
def econ_env(tmp_path, monkeypatch):
    """Isolated store + fresh counter state for every test."""
    monkeypatch.setenv("FABRIC_LLM_ECONOMY_DIR", str(tmp_path / "store"))
    monkeypatch.setenv("FABRIC_LLM_CACHE", "off")
    monkeypatch.delenv("FABRIC_PROBLEM_CALL_CAP", raising=False)
    monkeypatch.delenv("FABRIC_PROBLEM_RETRY_CAP", raising=False)
    monkeypatch.delenv("FABRIC_BREAKER_THRESHOLD", raising=False)
    monkeypatch.delenv("FABRIC_BREAKER_COOLDOWN_S", raising=False)
    monkeypatch.delenv("FABRIC_CALL_GOVERNOR", raising=False)
    monkeypatch.delenv("FABRIC_BREAKER", raising=False)
    econ._breakers.clear()  # breaker state is process-global: isolate
    econ.reset_run_counters("test-scope")
    yield tmp_path


# ---------------------------------------------------------------------------
# A1: LLM call cache


def _mkcache(tmp_path, monkeypatch, mode):
    monkeypatch.setenv("FABRIC_LLM_CACHE", mode)
    monkeypatch.setenv("FABRIC_LLM_ECONOMY_DIR", str(tmp_path / "store"))


def test_cache_key_stability_and_differentiation(econ_env):
    msgs = [{"role": "user", "content": "hello"}]
    k1 = econ.llm_cache_key("prov", "m1", msgs, 512)
    k2 = econ.llm_cache_key("prov", "m1", msgs, 512)
    assert k1 == k2 and len(k1) == 64
    assert econ.llm_cache_key("prov", "m1", msgs, 600) != k1  # params differ
    assert econ.llm_cache_key("prov", "m2", msgs, 512) != k1  # model differs
    assert econ.llm_cache_key("prov2", "m1", msgs, 512) != k1  # provider differs
    assert econ.llm_cache_key(
        "prov", "m1", [{"role": "user", "content": "hellp"}], 512) != k1


def test_cache_off_is_fully_inert(econ_env, tmp_path):
    econ_env  # store root untouched when off
    assert econ.cache_get("abc") is None
    econ.cache_put("abc", {"content": "x"})
    assert not (econ.econ_root() / "calls").exists()


def test_cache_rw_roundtrip_and_counters(econ_env, monkeypatch):
    _mkcache(econ_env, monkeypatch, "rw")
    key = econ.llm_cache_key("p", "m", [{"role": "user", "content": "q"}], 512)
    assert econ.cache_get(key) is None  # miss (rw: no raise)
    entry = {"content": "ANSWER", "finish_reason": "stop",
             "model": "m", "provider_id": "p", "max_tokens": 512}
    econ.cache_put(key, entry)
    hit = econ.cache_get(key)
    assert hit is not None and hit["content"] == "ANSWER"
    assert hit["recorded_at"]  # provenance stamp travels
    snap = econ.snapshot()
    assert snap["counters"]["cache_writes"] == 1
    assert snap["counters"]["cache_hits"] == 1


def test_cache_ro_replay_is_fail_closed(econ_env, monkeypatch):
    _mkcache(econ_env, monkeypatch, "ro")
    key = econ.llm_cache_key("p", "m", [{"role": "user", "content": "q"}], 512)
    with pytest.raises(econ.TypedCacheMiss):
        econ.cache_get(key)  # unrecorded call: typed, never a live spend
    # record, then replay succeeds
    monkeypatch.setenv("FABRIC_LLM_CACHE", "rw")
    econ.cache_put(key, {"content": "A", "finish_reason": "stop",
                         "model": "m", "provider_id": "p"})
    monkeypatch.setenv("FABRIC_LLM_CACHE", "ro")
    assert econ.cache_get(key)["content"] == "A"


# ---------------------------------------------------------------------------
# A1: stage memoization


def _cand():
    c = Candidate(problem={"device": "d", "failure": "f"},
                  problem_id="p1")
    c.candidate_id = "c1"
    return c


def _stage_fn(env, section):  # noqa: ANN001 - test fixture
    return {"_engine_result": True,
            "apply_to": {section: {"written": True}},
            "note": "stage ran"}


def test_stage_memo_hit_serves_cached_output(econ_env, monkeypatch):
    _mkcache(econ_env, monkeypatch, "rw")
    calls = {"n": 0}

    def fn(env):
        calls["n"] += 1
        return _stage_fn(env, "mechanism_map")

    c = _cand()
    e1 = c.run_stage("MECHANISM_SPACE", "cap/1.0", "mod.py", "fn", fn, c)
    assert e1["status"] == "OK" and "memo_hit" not in e1
    assert calls["n"] == 1
    assert c.mechanism_map == {"written": True}

    c2 = _cand()  # SAME upstream state, fresh envelope
    e2 = c2.run_stage("MECHANISM_SPACE", "cap/1.0", "mod.py", "fn", fn, c2)
    assert e2["status"] == "OK" and e2["memo_hit"] is True
    assert e2["memo_key"]  # the reuse is RECORDED, never silent (Art. XXV)
    assert calls["n"] == 1  # the stage fn NEVER re-executed
    assert c2.mechanism_map == {"written": True}
    assert e2["candidate_delta"] == ["mechanism_map"]


def test_stage_memo_invalidated_by_upstream_change(econ_env, monkeypatch):
    _mkcache(econ_env, monkeypatch, "rw")
    calls = {"n": 0}

    def fn(env):
        calls["n"] += 1
        return _stage_fn(env, "mechanism_map")

    c = _cand()
    c.run_stage("MECHANISM_SPACE", "cap/1.0", "mod.py", "fn", fn, c)
    c2 = _cand()
    c2.problem = {"device": "d", "failure": "DIFFERENT"}  # upstream changed
    e2 = c2.run_stage("MECHANISM_SPACE", "cap/1.0", "mod.py", "fn", fn, c2)
    assert "memo_hit" not in e2
    assert calls["n"] == 2  # re-executed honestly


def test_stage_memo_off_mode_never_caches(econ_env):
    calls = {"n": 0}

    def fn(env):
        calls["n"] += 1
        return _stage_fn(env, "mechanism_map")

    c = _cand()
    c.run_stage("S", "cap", "m", "f", fn, c)
    c2 = _cand()
    c2.run_stage("S", "cap", "m", "f", fn, c2)
    assert calls["n"] == 2  # off: zero behavior change
    assert not (econ.econ_root() / "stages").exists()


def test_stage_memo_invalidated_by_semantic_config(econ_env, monkeypatch):
    """An A/B arm that changes a semantic ENGINE_* knob must NOT reuse
    the base arm's memoized stage output. Returning to the base config
    must hit the original entry again (the key is deterministic)."""
    _mkcache(econ_env, monkeypatch, "rw")
    monkeypatch.setenv("ENGINE_R6_MEMO_CONFIG_PROBE", "A")
    calls = {"n": 0}

    def fn(env):
        calls["n"] += 1
        return _stage_fn(env, "mechanism_map")

    c = _cand()
    c.run_stage("MECHANISM_SPACE", "cap/1.0", "mod.py", "fn", fn, c)
    assert calls["n"] == 1

    monkeypatch.setenv("ENGINE_R6_MEMO_CONFIG_PROBE", "B")
    c2 = _cand()
    e2 = c2.run_stage("MECHANISM_SPACE", "cap/1.0", "mod.py", "fn", fn, c2)
    assert "memo_hit" not in e2
    assert calls["n"] == 2  # config changed -> honest re-execution

    monkeypatch.setenv("ENGINE_R6_MEMO_CONFIG_PROBE", "A")
    c3 = _cand()
    e3 = c3.run_stage("MECHANISM_SPACE", "cap/1.0", "mod.py", "fn", fn, c3)
    assert e3["memo_hit"] is True
    assert calls["n"] == 2  # base config hit, no third execution


def test_stage_memo_survives_cache_mode_switch(econ_env, monkeypatch):
    """The memo store mode (rw -> ro) is economy mechanics, not stage
    semantics: switching to replay must not invalidate a recorded stage."""
    _mkcache(econ_env, monkeypatch, "rw")
    calls = {"n": 0}

    def fn(env):
        calls["n"] += 1
        return _stage_fn(env, "mechanism_map")

    c = _cand()
    c.run_stage("S", "cap", "m", "f", fn, c)
    monkeypatch.setenv("FABRIC_LLM_CACHE", "ro")
    c2 = _cand()
    e2 = c2.run_stage("S", "cap", "m", "f", fn, c2)
    assert e2["memo_hit"] is True
    assert calls["n"] == 1


# ---------------------------------------------------------------------------
# A2: per-problem call governor


def test_governor_healthy_cap_and_retry_cap_typed(econ_env, monkeypatch):
    monkeypatch.setenv("FABRIC_PROBLEM_CALL_CAP", "3")
    monkeypatch.setenv("FABRIC_PROBLEM_RETRY_CAP", "2")
    econ.reset_governor("t")
    keys = [f"k{i}" for i in range(3)]
    for k in keys:
        out = econ.governor_attempt(k)
        assert out["kind"] == "healthy"
    with pytest.raises(econ.HealthyCallCapExceeded):
        econ.governor_attempt("k-new")  # 4th distinct logical call
    # retries of an existing key: 2 allowed, 3rd typed-stops
    assert econ.governor_attempt(keys[0])["kind"] == "retry"
    assert econ.governor_attempt(keys[0])["kind"] == "retry"
    with pytest.raises(econ.RetryCapExceeded):
        econ.governor_attempt(keys[0])
    snap = econ.snapshot()
    assert snap["governor"]["stops"], "typed stops are recorded"


def test_governor_reset_clears_scope(econ_env):
    econ.reset_governor("p1")
    econ.governor_attempt("a")
    econ.reset_governor("p2")
    snap = econ.snapshot()
    assert snap["governor"]["healthy_calls"] == 0
    assert snap["governor"]["scope"] == "p2"
    econ.governor_attempt("a")  # same key again after reset = healthy
    assert econ.snapshot()["governor"]["healthy_calls"] == 1


def test_governor_off_escape_hatch(econ_env, monkeypatch):
    monkeypatch.setenv("FABRIC_CALL_GOVERNOR", "off")
    for i in range(20):
        econ.governor_attempt(f"k{i}")  # no cap raises when disabled
    assert econ.snapshot()["governor"]["enabled"] is False


# ---------------------------------------------------------------------------
# A2: per-provider circuit breaker


class _HTTP429(urllib.error.HTTPError):
    def __init__(self):
        super().__init__("url", 429, "rate limited", None, None)


class _Spec:
    provider_id = "prov-a"
    flavor = "openai"
    env_var = "R6_TEST_PROVIDER_KEY"
    key_env_vars = None
    extra_body = None
    extra_headers = None

    def url_for_call(self):
        return "http://127.0.0.1:1/v1/chat/completions"

    def model_for_call(self):
        return "model-x"


def test_breaker_opens_after_threshold_and_refuses(econ_env):
    assert econ.breaker_failure("prov-x") is False  # 1
    assert econ.breaker_failure("prov-x") is False  # 2
    assert econ.breaker_failure("prov-x") is True   # 3 -> OPEN
    with pytest.raises(econ.BreakerOpen):
        econ.breaker_check("prov-x")  # typed refusal during cooldown
    econ.breaker_success("prov-x")
    econ.breaker_check("prov-x")  # closed again: passes


def test_breaker_cooldown_elapses_to_half_open(econ_env, monkeypatch):
    monkeypatch.setenv("FABRIC_BREAKER_COOLDOWN_S", "1")
    econ.reset_run_counters("t2")
    for _ in range(3):
        econ.breaker_failure("prov-y")
    time.sleep(1.05)
    econ.breaker_check("prov-y")  # cooldown elapsed -> half-open, allowed
    st = econ.breaker_state("prov-y")
    assert st["half_open"] is True and st["open"] is False
    assert econ.breaker_failure("prov-y") is True  # probe fails -> re-open
    st = econ.breaker_state("prov-y")
    assert st["open"] is True
    # AIMD: the re-open DOUBLES the initial cooldown (env-pinned to 1 s)
    assert st["cooldown_s"] == pytest.approx(2.0)


def test_breaker_disabled_never_opens(econ_env, monkeypatch):
    monkeypatch.setenv("FABRIC_BREAKER", "off")
    for _ in range(10):
        assert econ.breaker_failure("prov-z") is False
    econ.breaker_check("prov-z")  # no raise


# ---------------------------------------------------------------------------
# integration: the flavor transport honors breaker + cache + governor


def _fast_sleep(monkeypatch):
    """The flavor ladder's exponential-backoff sleeps are irrelevant when
    _post_json is a stub — no-op them so the typed-state tests stay fast."""
    monkeypatch.setattr(lr.time, "sleep", lambda s: None)


def _ok_response(content="CACHED-CONTENT"):
    return {"choices": [{"message": {"content": content},
                         "finish_reason": "stop"}]}


def test_flavor_breaker_aborts_storm_and_refuses_next_call(
        econ_env, monkeypatch):
    econ.reset_run_counters("t3")
    _fast_sleep(monkeypatch)
    posted = {"n": 0}

    def fake_post(url, payload, headers, timeout):
        posted["n"] += 1
        raise _HTTP429()

    monkeypatch.setattr(lr, "_post_json", fake_post)
    spec = _Spec()
    # the threshold-crossing failure is re-raised as the TYPED breaker
    # state (the caller/generate walk records CIRCUIT_BREAKER_OPEN)
    with pytest.raises(econ.BreakerOpen):
        lr._call_openai_flavor(spec, [{"role": "user", "content": "p"}],
                               5, 64)
    # the breaker opens ON the threshold-th consecutive failure and the
    # ladder aborts immediately: exactly 3 requests, not the old storm
    assert posted["n"] == 3
    assert econ.breaker_state("prov-a")["open"] is True
    # the NEXT call is refused with ZERO provider requests
    with pytest.raises(econ.BreakerOpen):
        lr._call_openai_flavor(spec, [{"role": "user", "content": "p"}],
                               5, 64)
    assert posted["n"] == 3


def test_flavor_governor_caps_provider_attempts(econ_env, monkeypatch):
    monkeypatch.setenv("FABRIC_PROBLEM_RETRY_CAP", "4")
    monkeypatch.setenv("FABRIC_BREAKER", "off")
    econ.reset_run_counters("t4")
    _fast_sleep(monkeypatch)
    posted = {"n": 0}

    def flaky_post(url, payload, headers, timeout):
        posted["n"] += 1
        if posted["n"] % 2 == 1:
            raise _HTTP429()
        return _ok_response(f"ok-{posted['n']}")

    monkeypatch.setattr(lr, "_post_json", flaky_post)
    spec = _Spec()
    msgs = [{"role": "user", "content": "same-call"}]
    # call 1: attempt 1 fails (429), attempt 2 succeeds -> 1 healthy + 1 retry
    out1 = lr._call_openai_flavor(spec, msgs, 5, 64)
    assert out1 == "ok-2"
    # hammer the same logical call: retries 2,3,4 succeed-or-fail, the 5th
    # re-attempt trips the typed retry cap BEFORE another request
    outs = []
    for _ in range(4):
        try:
            outs.append(lr._call_openai_flavor(spec, msgs, 5, 64))
        except econ.RetryCapExceeded:
            break
    with pytest.raises(econ.RetryCapExceeded):
        lr._call_openai_flavor(spec, msgs, 5, 64)
    snap = econ.snapshot()
    assert snap["governor"]["stops"], "the cap stop is recorded + logged"


def test_flavor_cache_hit_serves_with_zero_provider_requests(
        econ_env, monkeypatch):
    monkeypatch.setenv("FABRIC_LLM_CACHE", "rw")
    econ.reset_run_counters("t5")
    posted = {"n": 0}

    def fake_post(url, payload, headers, timeout):
        posted["n"] += 1
        return _ok_response()

    monkeypatch.setattr(lr, "_post_json", fake_post)
    spec = _Spec()
    msgs = [{"role": "user", "content": "record-me"}]
    out1 = lr._call_openai_flavor(spec, msgs, 5, 64)
    assert out1 == "CACHED-CONTENT" and posted["n"] == 1
    out2 = lr._call_openai_flavor(spec, msgs, 5, 64)
    assert out2 == "CACHED-CONTENT" and posted["n"] == 1  # ZERO new spend
    snap = econ.snapshot()
    assert snap["counters"]["cache_hits"] == 1
    # different params -> different key -> a real provider request
    lr._call_openai_flavor(spec, msgs, 5, 128)
    assert posted["n"] == 2


class _HTTP401(urllib.error.HTTPError):
    def __init__(self):
        super().__init__("url", 401, "unauthorized", None, None)


class _AnthropicSpec(_Spec):
    flavor = "anthropic"


def _anthropic_ok(text="A"):
    return {"content": [{"text": text}], "stop_reason": "end_turn"}


def test_anthropic_cache_key_includes_system_prompt(econ_env, monkeypatch):
    """The anthropic flavor splits the system turn out of messages; the
    cache key must still carry it, or two different prompts collide."""
    monkeypatch.setenv("FABRIC_LLM_CACHE", "rw")
    monkeypatch.setenv("R6_TEST_PROVIDER_KEY", "test-key")
    econ.reset_run_counters("anth-system")
    posted = {"n": 0}

    def fake_post(url, payload, headers, timeout):
        posted["n"] += 1
        return _anthropic_ok(f"A{posted['n']}")

    monkeypatch.setattr(lr, "_post_json", fake_post)
    spec = _AnthropicSpec()
    user = [{"role": "user", "content": "same user turn"}]
    out_a = lr._call_anthropic_flavor(
        spec, [{"role": "system", "content": "SYSTEM A"}] + user, 5, 64)
    out_b = lr._call_anthropic_flavor(
        spec, [{"role": "system", "content": "SYSTEM B"}] + user, 5, 64)
    assert (out_a, out_b) == ("A1", "A2")
    assert posted["n"] == 2  # different system prompt = different call
    # replay of SYSTEM A hits its own recorded entry, zero new spend
    out_a2 = lr._call_anthropic_flavor(
        spec, [{"role": "system", "content": "SYSTEM A"}] + user, 5, 64)
    assert out_a2 == "A1" and posted["n"] == 2


def test_anthropic_breaker_ignores_permanent_failures(econ_env, monkeypatch):
    """A 401 is a permanent auth failure, not congestion: it must never
    open the retry-storm breaker (Art. LXI counts infrastructure only)."""
    monkeypatch.setenv("R6_TEST_PROVIDER_KEY", "test-key")
    econ.reset_run_counters("anth-auth")
    posted = {"n": 0}

    def fake_post(url, payload, headers, timeout):
        posted["n"] += 1
        raise _HTTP401()

    monkeypatch.setattr(lr, "_post_json", fake_post)
    spec = _AnthropicSpec()
    msgs = [{"role": "system", "content": "S"},
            {"role": "user", "content": "Q"}]
    for _ in range(5):
        with pytest.raises(urllib.error.HTTPError):
            lr._call_anthropic_flavor(spec, msgs, 5, 64)
    st = econ.breaker_state("prov-a")
    assert st["open"] is False
    assert st["consecutive_transient_failures"] == 0


def _install_single_rung(monkeypatch, provider="localqwen",
                         model="qwen3-1.7b"):
    """A one-provider generate() walk with zero network/probe work, so
    the typed-stop route is tested in isolation."""
    from discovery_fabric.engine import model_cost_policy as mcp
    from discovery_fabric.engine import model_routing as mr
    from discovery_fabric.engine import provider_health as ph
    from discovery_fabric.engine import runtime_admission as ra

    monkeypatch.setenv("LOCAL_QWEN_BASE_URL",
                       "http://127.0.0.1:8790/v1/chat/completions")
    row = {
        "provider_id": provider, "env_var": "LOCAL_QWEN_BASE_URL",
        "available": True, "cost_policy_eligible": True,
        "cost_policy_note": "", "model": model,
        "quality_tier": 4, "cost_tier": 1, "latency_tier": 4,
        "context_capacity_tokens": 32768,
        "cost_basis": "ZERO_PAID_COST_SELF_HOSTED",
        "locality": "LOCAL", "license": "apache-2.0",
        "model_revision": "test", "account_domain": "LOCAL_COMPUTE",
        "capability_state": "PROBE_OK", "policy_note": "",
    }
    monkeypatch.setattr(lr, "availability_matrix", lambda: [row])
    monkeypatch.setattr(ph, "order_for_role",
                        lambda *a, **k: [provider])
    monkeypatch.setattr(ph, "apply_route_retirement",
                        lambda chain, **k: (list(chain), []))
    monkeypatch.setattr(mcp, "filter_chain",
                        lambda chain, specs, policy=None: (list(chain), []))
    monkeypatch.setattr(mcp, "provider_eligibility",
                        lambda spec, policy=None: (True, "test"))
    monkeypatch.setattr(mr, "build_ladder", lambda *a, **k: {
        "rungs": [{"provider": provider, "model": model,
                   "band": "TEST",
                   "task_capabilities": [mr.TASK_STRONG]}]})
    monkeypatch.setattr(mr, "is_model_gone", lambda *a, **k: False)
    monkeypatch.setattr(ra, "requires_probe", lambda *a, **k: False)
    monkeypatch.setattr(ra, "runtime_admission",
                        lambda *a, **k: (True, "", {}))
    monkeypatch.setattr(ra, "ladder_capability_evidence",
                        lambda rungs, **k: [])
    return provider, model


@pytest.mark.parametrize("exc_type,state,scope", [
    (econ.BreakerOpen, "CIRCUIT_BREAKER_OPEN", "RUNG"),
    (econ.HealthyCallCapExceeded, "HEALTHY_CALL_CAP_EXCEEDED", "WALK"),
    (econ.RetryCapExceeded, "RETRY_CAP_EXCEEDED", "WALK"),
    (econ.TypedCacheMiss, "REPLAY_CACHE_MISS", "WALK"),
])
def test_generate_records_typed_economy_stop_without_retry(
        econ_env, monkeypatch, exc_type, state, scope):
    provider, _model = _install_single_rung(monkeypatch)
    calls = {"n": 0}

    def fake_flavor(*args, **kwargs):
        calls["n"] += 1
        raise exc_type("typed stop under test")

    monkeypatch.setattr(lr, "_call_openai_flavor", fake_flavor)
    out = lr.generate("probe", max_retries=2)
    assert calls["n"] == 1, "a typed stop is never retried on the rung"
    assert out.status == lr.ST_CALL_FAILED
    assert out.failure_type == state
    typed = [h for h in (out.route or [])
             if h.get("status") == "ABORTED_TYPED"]
    assert len(typed) == 1
    assert typed[0]["failure_type"] == state
    assert typed[0]["typed_state"] == state
    assert typed[0]["provider_attempted"] == provider
    # these fakes refuse BEFORE a provider request: zero spend is recorded
    assert typed[0]["capability_state"] == "NOT_ATTEMPTED"
    assert typed[0]["attempts"] == 0


def test_breaker_threshold_request_is_still_an_attempt(econ_env, monkeypatch):
    """The request that CROSSES the breaker threshold is a real provider
    attempt. The typed stop must not erase it from the route, provider
    health, or the routing ledger (Art. XXV: a request that happened is
    never silently dropped)."""
    provider, _model = _install_single_rung(monkeypatch)
    from discovery_fabric.engine import model_routing as mr
    from discovery_fabric.engine import provider_health as ph
    seen = {"health": [], "ledger": []}
    monkeypatch.setattr(ph.HEALTH, "record_failure",
                        lambda *a, **k: seen["health"].append((a, k)))
    monkeypatch.setattr(mr, "record_call_outcome",
                        lambda *a, **k: seen["ledger"].append((a, k)))

    def fake_flavor(*args, **kwargs):
        raise econ.BreakerOpen("threshold crossed", request_made=True) \
            from TimeoutError("provider timed out")

    monkeypatch.setattr(lr, "_call_openai_flavor", fake_flavor)
    out = lr.generate("probe", max_retries=2)
    assert out.failure_type == "CIRCUIT_BREAKER_OPEN"
    typed = [h for h in (out.route or [])
             if h.get("status") == "FAILED_BREAKER_OPEN"]
    assert len(typed) == 1
    assert typed[0]["provider_attempted"] == provider
    assert typed[0]["provider_failure_type"] == "TIMEOUT"
    assert typed[0]["capability_state"] == "PROBE_OK"
    assert typed[0]["attempts"] == 1
    assert seen["health"], "provider health must see the threshold request"
    assert any(k.get("failure_type") == "TIMEOUT"
               for _, k in seen["ledger"]), \
        "the routing ledger must keep the request that opened the breaker"


def test_events_log_records_economy_decisions(econ_env):
    econ.breaker_failure("prov-log")
    econ.breaker_failure("prov-log")
    econ.breaker_failure("prov-log")
    ev_path = econ.econ_root() / "events.jsonl"
    assert ev_path.exists()
    kinds = [json.loads(l)["kind"]
             for l in ev_path.read_text().strip().splitlines()]
    assert "governor_reset" in kinds and "breaker_open" in kinds

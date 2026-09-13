"""tests/test_r415_discovery_availability.py — the P0 directive battery.

CODER P0: MAKE DISCOVERY ALWAYS AVAILABLE + FIX THE FRONTEND.

Covers the directive's own acceptance shape (section 19) plus the
subsystem contracts:

  - fallback ladder: Provider A = 410 -> B = rate limited -> C = timeout
    -> D = success  =>  the run SUCCEEDS, the provider failures are
    recorded (typed route + MODEL_ROUTING_LEDGER), D is selected, and
    the user sees a normal discovery experience (status OK).
  - all routes exhausted: A = 410, B = rate limited, C = timeout,
    D = unavailable  =>  RUN_BLOCKED_TRANSPORT, the problem is retained,
    no fake invention, resume possible.
  - 410 GONE is a distinct failure class + provider-health state; a GONE
    MODEL is demoted while the provider's other models stay eligible
    (Art. V: fail closed without becoming a universal rejector).
  - the availability score decays exponentially (yesterday's outage does
    not permanently poison a provider) and is tracked separately for
    provider / model / task.
  - health probes are TTL-cached and invalidated immediately on failure.
  - startup validation reports CONFIGURED without ever leaking the key.
  - /api/health carries the section-13 operational block with no keys.
  - POST /api/discovery returns 202 + run_id; GET /api/discovery/{id}
    returns the canonical run state.
  - the MODEL_ROUTING_LEDGER records the section-16 schema fields.
  - the ladders are task-class shaped (FAST/STRONG/CHEAP; the FAST
    ladder carries a secondary-reasoning rung and a last-resort rung).

Constitutional contract (Art. IX): every routing test redirects the
ledger / state / catalog to a tmp dir — production state is never
touched; the catalog is UNDISCOVERED (pinned defaults stand in) so no
test ever touches the network. Art. XVI/XVII: the cascade tests attack
the implementation (typed-route disclosure, no-silent-failover, bounded
walk, GONE-skip-retry) rather than asserting happy paths.
"""
from __future__ import annotations

import http.client
import json
import os
import sys
import threading
import time
import urllib.error
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine import llm_registry as reg  # noqa: E402
from discovery_fabric.engine import model_routing as mr
from discovery_fabric.engine import runtime_admission as ra  # noqa: E402
from discovery_fabric.engine import provider_health as ph  # noqa: E402
from toscanini import run_state as rs  # noqa: E402
from toscanini import user_state as us  # noqa: E402


# ---------------------------------------------------------------------------
# hermetic routing fixtures (Art. IX: production state is never touched)
# ---------------------------------------------------------------------------
@pytest.fixture()
def hermetic(monkeypatch, tmp_path):
    """Redirect the routing ledger / state / probe cache to tmp and make
    catalog discovery UNDISCOVERED (no network, pinned defaults).

    R451: this battery exercises the ROUTING MECHANICS (ladders, GONE,
    cooldowns, typed routes) against paid providers — the cost policy
    is therefore UNRESTRICTED here (the ZERO_PAID_COST policy's own
    fail-closed contract is covered by tests/test_r451_zero_paid.py;
    without this pin the default policy would rightly refuse every paid
    rung and the ladder mechanics could never be exercised)."""
    monkeypatch.setenv("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")
    tmp = Path(tmp_path)
    monkeypatch.setattr(mr, "LEDGER", mr.RoutingLedger(
        path=tmp / "ledger.jsonl"))
    monkeypatch.setattr(mr, "STATE_PATH", tmp / "state.json")
    # R451-C1.3: the capability store is production admission
    # state — tests redirect it (Art. IX)
    ra.set_state_path(tmp / "capability_state.json")
    monkeypatch.setattr(mr, "CATALOG_DIR", tmp / "catalog")
    # keep the REAL catalog discoverer reachable for its own unit tests
    monkeypatch.setattr(mr, "_real_discover_catalog", mr.discover_catalog,
                        raising=False)
    monkeypatch.setattr(
        mr, "discover_catalog",
        lambda provider_id, force=False: {
            "provider": provider_id, "status": "UNDISCOVERED",
            "fetched_at_epoch": 0.0, "models": [],
            "catalog_size": 0, "eligible_count": 0})
    mr.clear_probe_cache()
    book = ph.ProviderHealthBook(health_dir=tmp / "ph")
    monkeypatch.setattr(ph, "HEALTH", book)
    yield monkeypatch, tmp
    mr.clear_probe_cache()


def _route_rungs():
    """The pinned-default (provider, model) pairs the hermetic ladder
    will emit for STRONG, in a deterministic environment."""
    out = []
    for pid in ("nvidia", "openrouter", "zai"):
        for d in mr.PINNED_DEFAULT_MODELS.get(pid, []):
            out.append((pid, d["model"]))
    return out


# ---------------------------------------------------------------------------
# 1. The directive section-19 fallback ladder — scenario 1 (success)
# ---------------------------------------------------------------------------
class TestFallbackLadderSuccess:
    def test_a410_b_ratelimited_c_timeout_d_success(
            self, hermetic, monkeypatch):
        """Model A = 410, B = rate limited, C = timeout, D = success
        (the directive section-19 ladder, four sequential rungs): the run
        succeeds; failures recorded; D selected; the user sees a normal
        discovery experience (status OK — never three internal errors
        surfaced)."""
        monkeypatch, tmp = hermetic
        monkeypatch.setenv("NVIDIA_API_KEY", "k-a")
        monkeypatch.setenv("ZAI_API_KEY", "k-d")
        for k in ("OPENROUTER_API_KEY", "QWEN_API_KEY",
                  "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY",
                  "DEEPSEEK_API_KEY", "MISTRAL_API_KEY",
                  "TOKEN_ROUTER_API_KEY"):
            monkeypatch.delenv(k, raising=False)
        # two providers, two models each — the ROUND-ROBIN ladder walks
        # A (nvidia#1) -> B (zai#1) -> C (nvidia#2) -> D (zai#2)
        monkeypatch.setattr(mr, "PINNED_DEFAULT_MODELS", {
            "nvidia": [
                {"model": "nvidia/model-a",
                 "task_capabilities": ["STRONG", "FAST", "CHEAP"],
                 "cost_class": 1, "latency_class": 1,
                 "context_limit": 128000},
                {"model": "nvidia/model-c",
                 "task_capabilities": ["STRONG", "FAST", "CHEAP"],
                 "cost_class": 1, "latency_class": 1,
                 "context_limit": 128000}],
            "zai": [
                {"model": "zai/model-b",
                 "task_capabilities": ["STRONG", "FAST", "CHEAP"],
                 "cost_class": 1, "latency_class": 1,
                 "context_limit": 128000},
                {"model": "zai/model-d",
                 "task_capabilities": ["STRONG", "FAST", "CHEAP"],
                 "cost_class": 1, "latency_class": 1,
                 "context_limit": 128000}],
        })

        behavior = {                       # the directive's A/B/C/D roles
            "nvidia/model-a": lambda: urllib.error.HTTPError(
                "u", 410, "Gone", None, None),        # A = 410
            "zai/model-b": lambda: urllib.error.HTTPError(
                "u", 429, "Too Many Requests", None, None),  # B = rate
            "nvidia/model-c": lambda: TimeoutError("call timed out"),
            # zai/model-d = D: succeeds
        }

        def fake_call(spec, messages, timeout, max_tokens,
                      model_override=None):
            fn = behavior.get(model_override)
            if fn is not None:
                raise fn()
            return "DISCOVERY_ANSWER"

        monkeypatch.setattr(reg, "_call_openai_flavor", fake_call)
        res = reg.generate(
            "p", system="s", max_retries=0, timeout=5,
            policy=reg.SelectionPolicy(
                preferred_providers=["nvidia", "zai"],
                purpose="independent_attack"))
        # THE RUN SUCCEEDS — the user never sees the three failures
        assert res.status == "OK"
        assert res.model == "zai/model-d"        # D selected
        assert res.content == "DISCOVERY_ANSWER"
        # ...and the failures are all RECORDED (route + ledger), never
        # silent: A=410 -> GONE, B=429 -> RATE_LIMITED, C -> TIMEOUT
        classes = [h["failure_type"] for h in (res.route or [])]
        assert ph.GONE in classes
        assert ph.RATE_LIMITED in classes
        assert ph.TIMEOUT in classes
        attempted = [h["model"] for h in (res.route or [])]
        # the rungs walked A -> B -> C in order before D
        assert attempted[:3] == ["nvidia/model-a", "zai/model-b",
                                 "nvidia/model-c"]
        # the ledger carries the same typed failures (one line each)
        entries = [e for e in mr.LEDGER.tail() if not e.get("ok")]
        led_classes = {e["failure_class"] for e in entries}
        assert {ph.GONE, ph.RATE_LIMITED, ph.TIMEOUT} <= led_classes
        # the success line exists too — the evidence base for routing
        ok_entries = [e for e in mr.LEDGER.tail() if e.get("ok")]
        assert ok_entries and ok_entries[-1]["model"] == "zai/model-d"


# ---------------------------------------------------------------------------
# 2. The directive section-19 — scenario 2 (all routes exhausted)
# ---------------------------------------------------------------------------
class TestAllRoutesExhausted:
    def _all_fail(self, hermetic, monkeypatch):
        monkeypatch, tmp = hermetic
        monkeypatch.setenv("NVIDIA_API_KEY", "k-a")
        monkeypatch.setenv("ZAI_API_KEY", "k-d")
        for k in ("OPENROUTER_API_KEY", "QWEN_API_KEY",
                  "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY",
                  "DEEPSEEK_API_KEY", "MISTRAL_API_KEY",
                  "TOKEN_ROUTER_API_KEY"):
            monkeypatch.delenv(k, raising=False)
        monkeypatch.setattr(mr, "PINNED_DEFAULT_MODELS", {
            "nvidia": [
                {"model": "nvidia/model-a",
                 "task_capabilities": ["STRONG", "FAST", "CHEAP"],
                 "cost_class": 1, "latency_class": 1,
                 "context_limit": 128000},
                {"model": "nvidia/model-c",
                 "task_capabilities": ["STRONG", "FAST", "CHEAP"],
                 "cost_class": 1, "latency_class": 1,
                 "context_limit": 128000}],
            "zai": [
                {"model": "zai/model-b",
                 "task_capabilities": ["STRONG", "FAST", "CHEAP"],
                 "cost_class": 1, "latency_class": 1,
                 "context_limit": 128000},
                {"model": "zai/model-d",
                 "task_capabilities": ["STRONG", "FAST", "CHEAP"],
                 "cost_class": 1, "latency_class": 1,
                 "context_limit": 128000}],
        })

        behavior = {                          # D = unavailable too
            "nvidia/model-a": lambda: urllib.error.HTTPError(
                "u", 410, "Gone", None, None),
            "zai/model-b": lambda: urllib.error.HTTPError(
                "u", 429, "Too Many Requests", None, None),
            "nvidia/model-c": lambda: TimeoutError("call timed out"),
            "zai/model-d": lambda: ConnectionError("connection refused"),
        }

        def fake_call(spec, messages, timeout, max_tokens,
                      model_override=None):
            raise behavior[model_override]()

        monkeypatch.setattr(reg, "_call_openai_flavor", fake_call)
        return reg.generate(
            "p", system="s", max_retries=0, timeout=5,
            policy=reg.SelectionPolicy(
                preferred_providers=["nvidia", "zai"],
                purpose="independent_attack"))

    def test_call_failed_with_full_typed_route(self, hermetic, monkeypatch):
        res = self._all_fail(hermetic, monkeypatch)
        # infrastructure failure is CALL_FAILED — never a discovery verdict
        assert res.status == "CALL_FAILED"
        assert res.content is None
        classes = {h["failure_type"] for h in (res.route or [])}
        assert {ph.GONE, ph.RATE_LIMITED, ph.TIMEOUT,
                ph.NETWORK_FAILURE} <= classes
        assert res.route, "every hop recorded, never a bare failure"

    def test_worker_terminal_run_blocked_transport_problem_retained(
            self, hermetic, monkeypatch, tmp_path):
        """A/B/C/D all down -> the WORKER terminates the session as
        RUN_BLOCKED_TRANSPORT; the problem text is retained; no
        invention is fabricated; the session stays resumable."""
        monkeypatch, tmp = hermetic
        from toscanini import worker as wk
        from toscanini import sessions as store

        session = {"session_id": "s-r415", "user_text":
                   "Why do hemodialysis grafts clot at the venous "
                   "anastomosis despite anticoagulation?",
                   "status": "PENDING", "run_dir": None, "final_status":
                   None, "package": {}}
        updates = {}

        monkeypatch.setattr(store, "get_session",
                            lambda sid: dict(session) if sid == "s-r415"
                            else None)
        monkeypatch.setattr(store, "update_session",
                            lambda sid, **kw: updates.update(kw))
        monkeypatch.setattr(wk, "_snapshot", lambda *a, **k: None)
        monkeypatch.setattr(wk, "_serialize_run", lambda: None)
        # the probe fails through EVERY rung (ladder-aware, typed route)
        probe = {
            "status": "CALL_FAILED",
            "error": "HTTPError: HTTP Error 410: Gone",
            "route": [{"provider_attempted": "nvidia",
                       "model": "deepseek-ai/deepseek-v4-flash-0731",
                       "attempts": 1, "failure_type": "GONE",
                       "timestamp": "2026-09-06T00:00:00Z"}],
        }
        monkeypatch.setattr(wk.gw, "ensure_gateway",
                            lambda: {"status": "EXTERNAL",
                                     "base_url": "https://x.example"})
        monkeypatch.setattr(wk.gw, "preflight_probe", lambda: probe)
        monkeypatch.setattr(time, "sleep", lambda s: None)

        wk.run("s-r415")

        # RUN_BLOCKED_TRANSPORT — never "no invention found"
        assert updates.get("status") == "RUN_BLOCKED_TRANSPORT"
        err = updates.get("error", "")
        # the user-facing sentence is the directive's exact copy
        assert "Discovery temporarily blocked by infrastructure" in err
        assert "Your problem is saved and ready to resume" in err
        # the section-1 failure record travels with it
        assert "provider=nvidia" in err
        assert "failure_class=GONE" in err
        # the problem is retained (the session record was never deleted)
        assert session["user_text"].startswith("Why do hemodialysis")
        # no invention fabricated on an infrastructure terminal
        assert session.get("final_status") is None
        assert not (updates.get("package") or {}).get("complete")

    def test_run_blocked_is_resumable(self, hermetic, monkeypatch,
                                      tmp_path):
        """resume possible: a RUN_BLOCKED_TRANSPORT session re-enters the
        SAME worker path (status -> PENDING), its problem text and error
        history preserved (append-only)."""
        monkeypatch, tmp = hermetic
        from toscanini import sessions as store
        session = {"session_id": "s-r415",
                   "user_text": "the saved problem text goes here",
                   "status": "RUN_BLOCKED_TRANSPORT",
                   "error": "transport exhausted"}
        updates = {}
        monkeypatch.setattr(store, "get_session", lambda sid: dict(session))

        def fake_update(sid, **kw):
            updates.update(kw)
            out = dict(session)
            out.update(kw)
            return out

        monkeypatch.setattr(store, "update_session", fake_update)
        out = store.retry_session("s-r415")
        # the SAME session re-queued (append-only history, no new record)
        assert out["status"] == "PENDING"
        assert updates["retry_attempts"] == 1
        assert updates["last_error"] == "transport exhausted"
        assert session["user_text"].startswith("the saved problem")


# ---------------------------------------------------------------------------
# 3. GONE (410) — distinct class, model demotion, provider stays
# ---------------------------------------------------------------------------
class TestGoneModel:
    def test_410_marks_model_gone_and_demotes_only_that_model(
            self, hermetic, monkeypatch):
        monkeypatch, tmp = hermetic
        monkeypatch.setenv("NVIDIA_API_KEY", "k-a")
        for k in ("OPENROUTER_API_KEY", "ZAI_API_KEY", "QWEN_API_KEY",
                  "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY",
                  "DEEPSEEK_API_KEY", "MISTRAL_API_KEY",
                  "TOKEN_ROUTER_API_KEY"):
            monkeypatch.delenv(k, raising=False)

        dead = {"deepseek-ai/deepseek-v4-flash-0731"}

        def fake_call(spec, messages, timeout, max_tokens,
                      model_override=None):
            if model_override in dead:
                raise urllib.error.HTTPError(
                    "u", 410, "Gone", None, None)
            return "ALIVE_MODEL_ANSWER"

        monkeypatch.setattr(reg, "_call_openai_flavor", fake_call)
        res = reg.generate("p", system="s", max_retries=0, timeout=5,
                           policy=reg.SelectionPolicy(
                               preferred_providers=["nvidia"],
                               purpose="mechanism_space"))
        # the provider's FIRST model was retired — the run still succeeds
        # on the provider's OTHER model (the exact production fix)
        assert res.status == "OK"
        assert res.provider_id == "nvidia"
        assert res.model not in dead
        assert res.route and res.route[0]["failure_type"] == ph.GONE
        # the model is recorded GONE (excluded from future ladders)
        assert mr.is_model_gone("nvidia",
                                "deepseek-ai/deepseek-v4-flash-0731")
        ladder = mr.build_ladder("STRONG", role="synthesis")
        models = [r["model"] for r in ladder["rungs"]
                  if r["provider"] == "nvidia"]
        assert "deepseek-ai/deepseek-v4-flash-0731" not in models
        assert models, "the PROVIDER stays eligible with other models"

    def test_gone_model_skips_same_model_retries(self, hermetic,
                                                 monkeypatch):
        """A 410 fails over immediately — retrying a retired model burns
        the budget for nothing (measured behavior of the cascade: every
        remaining rung is attempted exactly once, never the same dead
        model again)."""
        monkeypatch, tmp = hermetic
        monkeypatch.setenv("NVIDIA_API_KEY", "k-a")
        for k in ("OPENROUTER_API_KEY", "ZAI_API_KEY", "QWEN_API_KEY",
                  "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY",
                  "DEEPSEEK_API_KEY", "MISTRAL_API_KEY",
                  "TOKEN_ROUTER_API_KEY"):
            monkeypatch.delenv(k, raising=False)
        calls = {"n": 0}

        def fake_call(spec, messages, timeout, max_tokens,
                      model_override=None):
            calls["n"] += 1
            raise urllib.error.HTTPError("u", 410, "Gone", None, None)

        monkeypatch.setattr(reg, "_call_openai_flavor", fake_call)
        res = reg.generate("p", system="s", max_retries=3, timeout=5,
                           policy=reg.SelectionPolicy(
                               preferred_providers=["nvidia"],
                               purpose="mechanism_space"))
        assert res.status == "CALL_FAILED"
        # nvidia's 3 distinct models (2 STRONG-capable round-robin rungs
        # + 1 last-resort), ONE attempt each — max_retries=3 is ignored
        # after a 410 (a retired model never gets a same-model retry)
        assert calls["n"] == 3
        assert len(res.route) == 3
        gone_models = {h["model"] for h in (res.route or [])}
        assert "deepseek-ai/deepseek-v4-flash-0731" in gone_models

    def test_success_clears_gone(self, hermetic):
        """A model that serves again is un-GONE (the catalog/R415 state
        is a cache of provider responses, never a permanent exile)."""
        monkeypatch, tmp = hermetic
        mr.mark_model_gone("nvidia", "some/model")
        assert mr.is_model_gone("nvidia", "some/model")
        mr.record_call_outcome("nvidia", "some/model", ok=True,
                               latency_ms=120)
        assert not mr.is_model_gone("nvidia", "some/model")


# ---------------------------------------------------------------------------
# 4. The availability score (directive section 4) — decay + separation
# ---------------------------------------------------------------------------
class TestAvailabilityScore:
    def _ledger_with(self, entries):
        for e in entries:
            mr.LEDGER.record(e)

    def test_yesterdays_outage_does_not_permanently_poison(
            self, hermetic):
        """An old failure decays to near-zero weight; a fresh success on
        the same provider scores high — the score recovers."""
        monkeypatch, tmp = hermetic
        now = time.time()
        self._ledger_with([
            {"provider": "zai", "model": "glm-4-plus", "ok": False,
             "latency_ms": 100, "recorded_at_epoch": now - 24 * 3600},
            {"provider": "zai", "model": "glm-4-plus", "ok": False,
             "latency_ms": 100, "recorded_at_epoch": now - 23 * 3600},
        ])
        old = mr.availability_report(provider="zai", now=now)
        assert old["recent_success_rate"] == 0.0
        # 24 h later (>5 half-lives at 4 h) the decayed weight is small
        assert old["decayed_observation_weight"] < 0.2
        # a fresh success dominates the ancient outage
        self._ledger_with([
            {"provider": "zai", "model": "glm-4-plus", "ok": True,
             "latency_ms": 900, "recorded_at_epoch": now - 60},
        ])
        fresh = mr.availability_report(provider="zai", now=now)
        assert fresh["recent_success_rate"] > 0.9

    def test_separate_provider_model_task_scores(self, hermetic):
        monkeypatch, tmp = hermetic
        now = time.time()
        self._ledger_with([
            {"provider": "zai", "model": "glm-4-plus", "task": "STRONG",
             "ok": True, "latency_ms": 500, "recorded_at_epoch": now},
            {"provider": "zai", "model": "glm-4-plus", "task": "CHEAP",
             "ok": False, "latency_ms": 50, "recorded_at_epoch": now},
            {"provider": "zai", "model": "glm-4-air", "task": "STRONG",
             "ok": False, "latency_ms": 500, "recorded_at_epoch": now},
        ])
        p = mr.availability_report(provider="zai", now=now)
        m = mr.availability_report(provider="zai", model="glm-4-plus",
                                   now=now)
        t = mr.availability_report(provider="zai", task="CHEAP", now=now)
        assert p["recent_success_rate"] is not None
        assert m["recent_success_rate"] == 0.5   # 1/2 on this model
        assert t["recent_success_rate"] == 0.0   # 0/1 on this task
        assert p["recent_success_rate"] == pytest.approx(1 / 3, abs=1e-3)

    def test_no_telemetry_is_not_a_zero_rate(self, hermetic):
        """Art. XXV: insufficient evidence is None (a disclosed neutral
        prior downstream), never a fabricated 0.0."""
        rep = mr.availability_report(provider="never-called")
        assert rep["recent_success_rate"] is None
        assert rep["decayed_observation_weight"] == 0.0

    def test_score_formula_documented_in_ladder(self, hermetic):
        ladder = mr.build_ladder("FAST", role="synthesis")
        di = ladder["decision_inputs"]
        assert "recent_success_rate" in di["score_formula"]
        assert di["decay_half_life_s"] == mr.DECAY_HALF_LIFE_S
        assert di["prior_strength"] == mr.PRIOR_STRENGTH


# ---------------------------------------------------------------------------
# 5. Health probes: TTL cache + failure invalidation (directive section 6)
# ---------------------------------------------------------------------------
class TestProbeCache:
    def test_ttl_expiry(self, hermetic):
        mr.probe_cache_put("zai", "glm-4-plus",
                           {"status": "HEALTHY", "ok": True})
        assert mr.probe_cache_get("zai", "glm-4-plus") is not None
        # force age beyond the TTL
        with mr._PROBE_LOCK:
            mr._PROBE_CACHE[("zai", "glm-4-plus")]["at_epoch"] = \
                time.time() - mr.PROBE_TTL_S - 1
        assert mr.probe_cache_get("zai", "glm-4-plus") is None

    def test_failure_invalidates_immediately(self, hermetic):
        mr.probe_cache_put("zai", "glm-4-plus",
                           {"status": "HEALTHY", "ok": True})
        mr.clear_probe_cache("zai", "glm-4-plus")
        assert mr.probe_cache_get("zai", "glm-4-plus") is None
        # record_call_outcome(failure) also invalidates (section 6)
        mr.probe_cache_put("zai", "glm-4-plus",
                           {"status": "HEALTHY", "ok": True})
        mr.record_call_outcome("zai", "glm-4-plus", ok=False,
                               failure_type=ph.TIMEOUT)
        assert mr.probe_cache_get("zai", "glm-4-plus") is None

    def test_provider_state_vocabulary(self, hermetic):
        """directive section 6: the state list is exactly
        HEALTHY/DEGRADED/RATE_LIMITED/AUTH_FAILED/GONE/TIMEOUT/
        UNAVAILABLE/UNKNOWN (UNAVAILABLE = no credential is the honest
        no-key state)."""
        assert mr.PROVIDER_STATES == (
            "HEALTHY", "DEGRADED", "RATE_LIMITED", "AUTH_FAILED", "GONE",
            "TIMEOUT", "UNAVAILABLE", "UNKNOWN")
        assert mr.provider_state("nvidia", has_key=False) == "UNAVAILABLE"


# ---------------------------------------------------------------------------
# 6. Startup validation + secrets (directive section 2)
# ---------------------------------------------------------------------------
class TestStartupValidation:
    def test_reports_configured_never_the_secret(self, hermetic,
                                                 monkeypatch):
        monkeypatch.setenv("NVIDIA_API_KEY", "nv SECRET-VALUE-r415")
        monkeypatch.setenv("OPENROUTER_API_KEY", "or SECRET-VALUE-r415")
        lines = mr.startup_validation()
        text = "\n".join(lines)
        assert "NVIDIA: CONFIGURED" in text
        assert "OPENROUTER: CONFIGURED" in text
        # the secret NEVER appears — not even a fragment
        assert "SECRET-VALUE" not in text
        assert "nv SECRET" not in text

    def test_provider_summary_never_leaks_keys(self, hermetic,
                                               monkeypatch):
        monkeypatch.setenv("NVIDIA_API_KEY", "nv SECRET-VALUE-r415")
        summary = mr.provider_summary()
        blob = json.dumps(summary)
        assert "SECRET-VALUE" not in blob
        nv = summary.get("nvidia", {})
        assert nv.get("credential") == "CONFIGURED"
        assert nv.get("available_models", 0) >= 1   # pinned defaults stand
        assert "key" not in blob.lower()


# ---------------------------------------------------------------------------
# 7. /api/health (directive section 13) + the API contract (section 9)
# ---------------------------------------------------------------------------
class TestHealthPayload:
    def test_section13_block_present_no_keys(self, hermetic, monkeypatch):
        from toscanini import server as sv
        monkeypatch.setenv("NVIDIA_API_KEY", "nv SECRET-VALUE-r415")
        payload = sv._health_payload()
        # the directive's exact field names, top-level
        for field in ("showcase_ready", "discovery_ready", "providers",
                      "retrieval_ready", "physics_ready",
                      "reality_loop_ready"):
            assert field in payload, field
        providers = payload["providers"]
        assert "nvidia" in providers and "openrouter" in providers
        for pid, rec in providers.items():
            assert set(rec.keys()) == {"status", "available_models"}
            assert isinstance(rec["available_models"], int)
        blob = json.dumps(payload)
        assert "SECRET-VALUE" not in blob
        # the R414 nested surface stays intact (one payload, two views)
        assert "readiness" in payload and \
            isinstance(payload["readiness"].get("providers"), list)
        assert "model_routing" in payload

    def test_health_never_carries_env_key_values(self, hermetic,
                                                 monkeypatch):
        from toscanini import server as sv
        monkeypatch.setenv("ZAI_API_KEY", "zai-SECRET-r415")
        monkeypatch.setenv("OPENROUTER_API_KEY", "or-SECRET-r415")
        blob = json.dumps(sv._health_payload())
        assert "SECRET" not in blob and "zai-SECRET" not in blob


class TestDiscoveryApi:
    def _server(self, monkeypatch):
        from toscanini import server as sv

        class _MemStore:
            def __init__(self):
                self.sessions = {}

            def create_session(self, title, user_text, owner_key=None):
                sid = f"ts_{len(self.sessions):06d}"
                s = {"session_id": sid, "title": title,
                     "user_text": user_text, "status": "PENDING",
                     "package": {}, "final_status": None,
                     "run_dir": None, "created_at": "now"}
                self.sessions[sid] = s
                return s

            def get_session(self, sid):
                return self.sessions.get(sid)

            @staticmethod
            def session_access(sid, owner_key=None, operator_key=None):
                return "OWNER"

        mem = _MemStore()
        monkeypatch.setattr(sv, "store", mem)
        monkeypatch.setattr(sv.Handler, "_spawn_worker",
                            lambda self, sid: None)

        class _Quiet(ThreadingHTTPServer):
            def handle_error(self, request, client_address):
                pass

        srv = _Quiet(("127.0.0.1", 0), sv.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        return srv, mem

    def test_post_api_discovery_returns_202_and_run_id(
            self, hermetic, monkeypatch):
        srv, mem = self._server(monkeypatch)
        port = srv.server_address[1]
        try:
            conn = http.client.HTTPConnection("127.0.0.1", port,
                                              timeout=10)
            body = json.dumps({"text": "How can EV traction-battery "
                                       "thermal runaway initiation be "
                                       "prevented?"})
            conn.request("POST", "/api/discovery", body=body,
                         headers={"Content-Type": "application/json"})
            resp = conn.getresponse()
            data = json.loads(resp.read())
            assert resp.status == 202          # the directive's contract
            assert data["run_id"]
            assert data["state"] == "DISCOVERY_RUN_STARTED"
            assert mem.get_session(data["run_id"])["user_text"] \
                .startswith("How can EV")
            # the problem is durable from acceptance (never lost)
            # GET /api/discovery/{run_id} returns the canonical state
            conn.request("GET", f"/api/discovery/{data['run_id']}")
            resp2 = conn.getresponse()
            state = json.loads(resp2.read())
            assert resp2.status == 200
            assert state["run_id"] == data["run_id"]
            assert state["outcome"] == "PENDING"   # in flight, honest
            conn.close()
        finally:
            srv.shutdown()
            srv.server_close()

    def test_short_problem_rejected(self, hermetic, monkeypatch):
        srv, mem = self._server(monkeypatch)
        port = srv.server_address[1]
        try:
            conn = http.client.HTTPConnection("127.0.0.1", port,
                                              timeout=10)
            conn.request("POST", "/api/discovery",
                         body=json.dumps({"text": "too short"}),
                         headers={"Content-Type": "application/json"})
            assert conn.getresponse().status == 400
            conn.close()
        finally:
            srv.shutdown()
            srv.server_close()


# ---------------------------------------------------------------------------
# 8. The MODEL_ROUTING_LEDGER schema (directive section 16)
# ---------------------------------------------------------------------------
class TestRoutingLedger:
    def test_every_field_present(self, hermetic):
        mr.record_call_outcome(
            "zai", "glm-4-plus", ok=False, failure_type=ph.GONE,
            latency_ms=410, task="FAST", stage="independent_attack",
            run_id="ts_000001", request_id="req_abc", attempt=2,
            tokens=512, estimated_cost=0.0,
            fallback_from="zai", fallback_to="openrouter",
            error="HTTP Error 410: Gone")
        entries = mr.LEDGER.tail()
        assert entries
        e = entries[-1]
        for field in ("request_id", "run_id", "stage", "provider",
                      "model", "attempt", "latency", "status",
                      "failure_class", "tokens", "estimated_cost",
                      "fallback_from", "fallback_to"):
            assert field in e, field
        assert e["status"] == "FAILED"
        assert e["failure_class"] == "GONE"
        assert e["attempt"] == 2

    def test_ledger_is_the_routing_evidence_base(self, hermetic):
        """section 17: every successful/failed call updates the ledger,
        and the availability report derives FROM the ledger bytes."""
        mr.record_call_outcome("zai", "glm-4-plus", ok=True,
                               latency_ms=800, task="FAST")
        rep = mr.availability_report(provider="zai", model="glm-4-plus")
        assert rep["recent_success_rate"] == 1.0
        assert rep["latency_ema_ms"] == 800.0


# ---------------------------------------------------------------------------
# 9. Ladder shape (directive section 5) + provider separation (section 15)
# ---------------------------------------------------------------------------
class TestLadderShape:
    def test_task_classes_and_role_mapping(self, hermetic):
        assert mr.task_class_for_role("synthesis") == "STRONG"
        assert mr.task_class_for_role("extraction") == "CHEAP"
        assert mr.task_class_for_role("attack") == "FAST"
        assert mr.task_class_for_role("transform") == "CHEAP"

    def test_fast_ladder_has_secondary_reasoning_and_last_resort(
            self, hermetic, monkeypatch):
        monkeypatch.setenv("NVIDIA_API_KEY", "k")
        monkeypatch.setenv("OPENROUTER_API_KEY", "k")
        # a STRONG-only model exercises the LAST_RESORT band on a FAST
        # ladder (any-capability final rung) and a reasoning-capable
        # second model exercises SECONDARY_REASONING
        monkeypatch.setattr(mr, "PINNED_DEFAULT_MODELS", {
            "nvidia": [
                {"model": "nvidia/fast-primary",
                 "task_capabilities": ["FAST", "CHEAP"],
                 "cost_class": 1, "latency_class": 1,
                 "context_limit": 128000},
                {"model": "nvidia/reasoning-second",
                 "task_capabilities": ["STRONG", "FAST"],
                 "cost_class": 2, "latency_class": 2,
                 "context_limit": 128000},
                {"model": "nvidia/strong-only",
                 "task_capabilities": ["STRONG"],
                 "cost_class": 2, "latency_class": 3,
                 "context_limit": 128000}],
            "openrouter": [
                {"model": "openrouter/fast-free",
                 "task_capabilities": ["FAST", "CHEAP"],
                 "cost_class": 1, "latency_class": 2,
                 "context_limit": 128000}],
        })
        ladder = mr.build_ladder("FAST", role="attack",
                                 avoid_provider="nvidia")
        bands = [r["band"] for r in ladder["rungs"]]
        assert "SECONDARY_REASONING" in bands
        assert "LAST_RESORT" in bands          # the strong-only model
        # cheap-first: the FIRST rung is a FAST/CHEAP primary, never the
        # reasoning model (never burn a strong model on a fast task)
        assert ladder["rungs"][0]["model"] in (
            "nvidia/fast-primary", "openrouter/fast-free")
        # the secondary-reasoning rung comes AFTER the primary rungs
        assert bands.index("SECONDARY_REASONING") > 0

    def test_cheap_ladder_prefers_latency_class_1(self, hermetic,
                                                  monkeypatch):
        monkeypatch.setenv("ZAI_API_KEY", "k")
        monkeypatch.setenv("NVIDIA_API_KEY", "k")
        ladder = mr.build_ladder("CHEAP", role="extraction")
        first = ladder["rungs"][0]
        assert first["latency_class"] == 1 or first["cost_class"] == 1

    def test_ladder_bounded(self, hermetic, monkeypatch):
        for k in ("NVIDIA_API_KEY", "OPENROUTER_API_KEY", "ZAI_API_KEY",
                  "QWEN_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY",
                  "GEMINI_API_KEY", "DEEPSEEK_API_KEY",
                  "MISTRAL_API_KEY", "TOKEN_ROUTER_API_KEY"):
            monkeypatch.setenv(k, "k")
        ladder = mr.build_ladder("STRONG", role="synthesis")
        assert len(ladder["rungs"]) <= 8

    def test_allowlist_is_families_not_a_day_catalog(self, hermetic):
        """section 18: the pinned allowlist pins FAMILIES; a model id
        matches by family pattern, and the pinned defaults are all
        allowlist members."""
        assert mr._family_match(
            "nvidia/nemotron-3.5-lightning-30b-a3b",
            mr.PINNED_MODEL_FAMILIES["nvidia"])
        assert not mr._family_match(
            "vendor/unknown-family-model",
            mr.PINNED_MODEL_FAMILIES["nvidia"])
        for pid, models in mr.PINNED_DEFAULT_MODELS.items():
            for d in models:
                assert mr._family_match(
                    d["model"], mr.PINNED_MODEL_FAMILIES[pid]), \
                    f"{d['model']} not in the {pid} allowlist"

    def test_catalog_discovery_falls_back_honestly(self, hermetic):
        """UNDISCOVERED is disclosed (with the error recorded); the
        pinned defaults stand in; a discovered catalog's eligible models
        carry CATALOG source."""
        monkeypatch, tmp = hermetic
        # the REAL discoverer, with its HTTP layer failing (no network
        # in tests — the failure path is the path under test)
        def _fail(url, key, timeout=20):
            raise ConnectionError("no route to host (test)")
        monkeypatch.setattr(mr, "_get_json", _fail)
        cat = mr._real_discover_catalog("nvidia")
        assert cat["status"] == "UNDISCOVERED"
        assert cat.get("error")          # the failure is DISCLOSED
        recs = mr.eligible_models("nvidia", "STRONG")
        assert recs and all(r.source == "PINNED_DEFAULT" for r in recs)
        # a discovered catalog feeds CATALOG-sourced records
        monkeypatch.setattr(
            mr, "discover_catalog",
            lambda provider_id, force=False: {
                "provider": provider_id, "status": "DISCOVERED",
                "fetched_at_epoch": time.time(),
                "models": ["nvidia/nemotron-3.5-lightning-30b-a3b"],
                "catalog_size": 3, "eligible_count": 1})
        recs = mr.eligible_models("nvidia", "FAST")
        assert any(r.source == "CATALOG" and r.model ==
                   "nvidia/nemotron-3.5-lightning-30b-a3b" for r in recs)


# ---------------------------------------------------------------------------
# 10. The run/user-state projections for the blocked state
# ---------------------------------------------------------------------------
class TestBlockedProjections:
    def _blocked_session(self):
        return {"session_id": "s1", "user_text": "a real problem text",
                "status": "RUN_BLOCKED_TRANSPORT",
                "final_status": None, "package": {}, "run_dir": None,
                "error": "route: provider=nvidia failure_class=GONE"}

    def test_outcome_is_run_blocked_not_a_verdict(self):
        o = rs.terminal_outcome(self._blocked_session())
        assert o["outcome"] == rs.OUTCOME_RUN_BLOCKED
        assert "never a scientific rejection" in o["basis"]

    def test_user_state_is_blocked_transport(self):
        v = us.user_state_view(self._blocked_session())
        assert v["user_state"] == "BLOCKED_TRANSPORT"
        assert v["finished"] is True
        assert v["rejected"] is False        # never a kill
        assert "saved and ready to resume" in v["meaning"]
        assert "not a rejection" in v["meaning"]

    def test_legacy_error_transport_still_maps(self):
        v = us.user_state_view(
            {"session_id": "s2", "user_text": "x",
             "status": "ERROR_TRANSPORT", "final_status": None,
             "package": {}, "run_dir": None})
        assert v["user_state"] == "FAILED_TRANSPORT"  # legacy sessions

    def test_canonical_run_state_carries_blocked_failure_state(self):
        state = rs.canonical_run_state(self._blocked_session())
        assert state["status"] == "RUN_BLOCKED_TRANSPORT"
        assert state["failure_state"]["state"] == "INFRASTRUCTURE"
        assert state["outcome"] == rs.OUTCOME_RUN_BLOCKED


# ---------------------------------------------------------------------------
# 11. The two defects the LIVE acceptance runs caught (Art. XV/XVI — a
# failure discovered by the system is a success of the system)
# ---------------------------------------------------------------------------
class TestLiveCaughtDefects:
    def test_select_survivors_honors_entry_killed_flag(self):
        """RUN 2 (scale fouling) caught this live: the R401 Phase-6
        independent-attack KILL sets evaluated['killed']=True while
        attack.overall stays NEEDS_REPAIR — select_survivors derived
        killed ONLY from attack.overall, ranked the killed candidate
        alive, SELECTED it, and the chosen lookup raised StopIteration
        (package failed; the run lost its package on a bug). The entry's
        own killed flag is authoritative."""
        from discovery_fabric.engine.engineering_attack import \
            select_survivors
        evaluated = [
            {   # killed by the INDEPENDENT attacker (the exact shape)
                "candidate_id": "cand:MS:DIRECT_TRANSFER:x",
                "attack": {"overall": "NEEDS_REPAIR",
                           "counts": {"UNCERTAIN": 2, "REPAIR": 1}},
                "independent_attack": {"overall": "KILLED"},
                "quality": None, "repaired": False,
                "span_underived": False,
                "physics_lifecycle": "MECHANISM_NOT_SIMULATABLE",
                "killed": True},
            {   # quality FAIL (the A2 candidate's shape)
                "candidate_id": "cand:A2:primary",
                "attack": {"overall": "NEEDS_REPAIR",
                           "counts": {"UNCERTAIN": 2}},
                "quality": {"verdict": "FAIL",
                            "deficient_areas": ["a", "b"]},
                "repaired": False, "span_underived": False,
                "physics_lifecycle": "MECHANISM_NOT_SIMULATABLE",
                "killed": False},
            {   # a live survivor
                "candidate_id": "cand:MS:GEOMETRIC:y",
                "attack": {"overall": "NEEDS_REPAIR",
                           "counts": {"UNCERTAIN": 1}},
                "quality": {"verdict": "PASS", "deficient_areas": []},
                "repaired": False, "span_underived": False,
                "physics_lifecycle": "MEANISM_NOT_SIMULABLE"
                if False else "MECHANISM_NOT_SIMULATABLE",
                "killed": False},
        ]
        sel = select_survivors(evaluated)
        ranked = {r["candidate_id"]: r for r in sel["ranked"]}
        # the independent-attack kill is honored: ranked killed=True
        assert ranked["cand:MS:DIRECT_TRANSFER:x"]["killed"] is True
        assert "cand:MS:DIRECT_TRANSFER:x" in sel["killed"]
        # never selected; the live survivor is
        assert sel["selected"] != "cand:MS:DIRECT_TRANSFER:x"
        assert sel["selected"] == "cand:MS:GEOMETRIC:y"
        # the chosen lookup can never raise StopIteration on this input
        chosen = next(e for e in evaluated
                      if e["candidate_id"] == sel["selected"]
                      and not e.get("killed"))
        assert chosen["candidate_id"] == "cand:MS:GEOMETRIC:y"

    def test_select_survivors_no_killed_candidate_selected(self):
        """the converse guard: when every candidate is killed or
        quality-rejected, selection is None (an honest no-survivor —
        the caller records PACKAGE_FAILED at SURVIVOR_SELECTION and
        NEVER crashes)."""
        from discovery_fabric.engine.engineering_attack import \
            select_survivors
        evaluated = [
            {"candidate_id": "c1", "attack": {"overall": "NEEDS_REPAIR",
                                              "counts": {}},
             "independent_attack": {"overall": "KILLED"},
             "quality": None, "repaired": False, "span_underived": False,
             "physics_lifecycle": "MECHANISM_NOT_SIMULATABLE",
             "killed": True},
            {"candidate_id": "c2", "attack": {"overall": "PASS",
                                              "counts": {}},
             "quality": {"verdict": "FAIL", "deficient_areas": ["x"]},
             "repaired": False, "span_underived": False,
             "physics_lifecycle": "MECHANISM_NOT_SIMULATABLE",
             "killed": False},
        ]
        sel = select_survivors(evaluated)
        assert sel["selected"] is None

    def test_s2_null_data_shape_is_rate_limited_not_a_crash(
            self, monkeypatch, tmp_path):
        """RUN 1 (anastomotic leakage) caught this live: Semantic
        Scholar answered HTTP 200 with body {"data": null} (throttled
        shape) and len(None) raised TypeError, crashing the RETRIEVE
        stage — a provider failure masquerading as an engine crash
        (Art. XXI.3). The shape is now classified RATE_LIMITED with the
        S2_200_NULL_DATA custody disclosure."""
        import io
        from discovery_fabric.retrieval_fabric import reciprocal as rec
        from discovery_fabric.source_registry import retrieval_log as rl

        class _FakeResp(io.BytesIO):
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def _fake_urlopen(req, timeout=25, context=None):
            return _FakeResp(b'{"data": null}')

        monkeypatch.setattr(rec.urllib.request, "urlopen", _fake_urlopen)
        sandbox = tmp_path / "retrieval_log_SANDBOX.jsonl"
        monkeypatch.setattr(rl, "LOG_PATH", sandbox)
        r = rec._s2_get("https://api.semanticscholar.org/graph/v1/paper/x"
                        "/citations?limit=5")
        # no exception; honest typed state; normalized data
        assert r["status"] == rec.STATUS_RATE_LIMITED
        assert (r.get("data") or {}).get("data") == []
        # the custody entry discloses the shape
        entry = json.loads(sandbox.read_text().splitlines()[-1])
        assert "S2_200_NULL_DATA" in (entry.get("error") or "")
        assert entry["record_count"] == 0

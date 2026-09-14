"""tests/test_r414_product_integration.py — the R414 battery.

Operator directive (product integration): the website and the discovery
engine are ONE product. This battery pins the constitutional invariants
of that integration:

  - provider resilience (§6-10): the failure taxonomy, the cross-
    provider cascade, cooldown demotion, and the NEVER-silent-failover
    contract (a success after failover carries the route)
  - the canonical DiscoveryRun state (§4) and the four terminal
    outcomes (§18) — RUN_BLOCKED is infrastructure-only; a scientific
    rejection is NO_DEFENSIBLE_INVENTION (Art. LXI)
  - the Canonical Invention Object (§12-14): maturity fields are
    derived from run artifacts, never frontend badges; no invention
    artifacts -> no CIO (never fabricated)
  - the counsel package (§20): derived from run artifacts only; the
    cover note never asserts patentability (§3)
  - the language guard: banned patentability words are detected and
    kept off the product surface

Art. VIII/V discipline: positives must pass, negatives must fail,
metamorphic mutations must fail. Production state (the singleton health
book, the real sessions store) is NEVER touched — every test builds
its own book / run-dir in a temp directory.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import urllib.error
import zipfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import provider_health as ph  # noqa: E402
from discovery_fabric.engine import llm_registry as reg  # noqa: E402
from toscanini import cio as cio_mod  # noqa: E402
# R456: toscanini/counsel.py ARCHIVED_TO archive/r456-lean/ (route retired R423A; zero importers) — the builder-pin class moved to the archive with the module (Art. LXIV).
from toscanini import run_state as rs  # noqa: E402


# ---------------------------------------------------------------------------
# 1. The failure taxonomy (directive §8 — exact vocabulary)
# ---------------------------------------------------------------------------
class TestFailureTaxonomy:
    def test_all_eight_types_classified(self):
        cases = [
            (urllib.error.HTTPError("u", 429, "Too Many Requests",
                                    None, None), ph.RATE_LIMITED),
            (urllib.error.HTTPError("u", 401, "Unauthorized",
                                    None, None), ph.AUTH_FAILURE),
            (urllib.error.HTTPError("u", 403, "Forbidden",
                                    None, None), ph.AUTH_FAILURE),
            (urllib.error.HTTPError("u", 503, "Service Unavailable",
                                    None, None), ph.MODEL_FAILURE),
            (urllib.error.HTTPError("u", 400, "Bad Request",
                                    None, None), ph.INVALID_RESPONSE),
            (TimeoutError("operation timed out"), ph.TIMEOUT),
            (ConnectionError("connection refused"), ph.NETWORK_FAILURE),
            (json.JSONDecodeError("x", "y", 0), ph.INVALID_RESPONSE),
            (RuntimeError("nvidia returned empty content "
                          "(finish_reason=length)"), ph.MODEL_FAILURE),
            (Exception("something weird"), ph.UNKNOWN),
        ]
        for exc, want in cases:
            got = ph.classify_failure(exc)
            assert got == want, f"{type(exc).__name__}: {got} != {want}"

    def test_rate_limit_distinguished_from_empty_and_unknown(self):
        """Directive §8 + the checkout line 'rate limits distinguished
        from empty': 429 is RATE_LIMITED, empty content is
        MODEL_FAILURE, and neither may collapse into the other."""
        assert ph.classify_failure(
            RuntimeError("429 Too Many Requests")) == ph.RATE_LIMITED
        assert ph.classify_failure(
            RuntimeError("empty content (finish_reason=stop)")
        ) == ph.MODEL_FAILURE
        assert ph.classify_failure(Exception("???")) == ph.UNKNOWN

    def test_failure_vocabulary_exact(self):
        # R415 amendment (P0 directive section 1): + GONE — HTTP 410 is a
        # distinct class/state. The amendment EXTENDS the R414 vocabulary;
        # it reclassifies nothing already pinned above.
        # R442 reconciliation (Art. LXIV rule 2, dated investigation):
        # R436 added CREDIT_EXHAUSTED (provider_health.py: cannot afford
        # the request — distinct from RATE_LIMITED, observed live in the
        # production transport route); this exact-set assertion was not
        # updated in the same change. Reconciled to the shipped set.
        assert set(ph.FAILURE_TYPES) == {
            "RATE_LIMITED", "TIMEOUT", "AUTH_FAILURE", "NETWORK_FAILURE",
            "INVALID_RESPONSE", "MODEL_FAILURE", "PARSER_FAILURE", "GONE",
            "CREDIT_EXHAUSTED", "UNKNOWN"}

    def test_410_gone_is_distinct(self):
        """R415 (P0 directive section 1): 410 must not collapse into
        INVALID_RESPONSE — the retired-resource fact stays knowable."""
        assert ph.classify_failure(
            urllib.error.HTTPError("u", 410, "Gone", None, None)) == ph.GONE
        assert ph.classify_failure(
            Exception("HTTPError: HTTP Error 410: Gone"),
            http_status=410) == ph.GONE

    def test_message_hint_classification(self):
        assert ph.classify_failure(
            Exception("HTTP 429 quota exceeded")) == ph.RATE_LIMITED
        assert ph.classify_failure(
            Exception("401 invalid api key")) == ph.AUTH_FAILURE
        assert ph.classify_failure(
            Exception("read operation timed out")) == ph.TIMEOUT


# ---------------------------------------------------------------------------
# 2. The health book (directive §10 — per-provider health)
# ---------------------------------------------------------------------------
class TestHealthBook:
    def _book(self, tmp):
        return ph.ProviderHealthBook(health_dir=Path(tmp) / "ph")

    def test_success_failure_recording_and_persistence(self, tmp_path):
        b = self._book(tmp_path)
        b.record_success("zai", 1200, purpose="probe", model="glm-4-plus")
        b.record_failure("zai", ph.TIMEOUT, purpose="probe")
        # re-load from disk: persistence works, state is not memory-only
        b2 = ph.ProviderHealthBook(health_dir=Path(tmp_path) / "ph")
        specs = [{
            "provider_id": "zai", "available": True, "model": "m",
            "quality_tier": 2, "cost_tier": 1, "latency_tier": 1,
            "context_capacity_tokens": 128000}]
        snap = b2.snapshot(provider_specs=specs)
        zai = next(p for p in snap if p["provider"] == "zai")
        assert zai["status"] == "DEGRADED"
        assert zai["call_count"] == 2
        assert zai["last_failure_type"] == "TIMEOUT"

    def test_rate_limit_cooldown_ladder_and_demotion(self, tmp_path):
        b = self._book(tmp_path)
        b.record_failure("zai", ph.RATE_LIMITED)
        assert b.in_cooldown("zai")
        assert 0 < b.cooldown_remaining_s("zai") <= 60
        b.record_failure("zai", ph.RATE_LIMITED)
        assert b.cooldown_remaining_s("zai") > 60  # ladder escalated
        # a success clears the cooldown
        b.record_success("zai", 800)
        assert not b.in_cooldown("zai")

    def test_never_called_is_reported_never_called(self, tmp_path):
        """A configured provider with no call history is NEVER_CALLED —
        never 'healthy' (Art. XXV: unknown stays unknown)."""
        b = self._book(tmp_path)
        snap = b.snapshot(provider_specs=[{
            "provider_id": "openrouter", "available": True,
            "model": "x", "quality_tier": 2, "cost_tier": 2,
            "latency_tier": 2, "context_capacity_tokens": 128000}])
        assert snap[0]["status"] == "NEVER_CALLED"

    def test_unavailable_is_reported_unavailable(self, tmp_path):
        b = self._book(tmp_path)
        snap = b.snapshot(provider_specs=[{
            "provider_id": "nvidia", "available": False, "model": "y",
            "quality_tier": 2, "cost_tier": 1, "latency_tier": 1,
            "context_capacity_tokens": 128000}])
        assert snap[0]["status"] == "UNAVAILABLE"

    def test_recent_failure_rate_needs_two_calls(self, tmp_path):
        b = self._book(tmp_path)
        b.record_failure("zai", ph.TIMEOUT)
        assert b.recent_failure_rate("zai") is None  # insufficient
        b.record_failure("zai", ph.TIMEOUT)
        assert b.recent_failure_rate("zai") == 1.0


# ---------------------------------------------------------------------------
# 3. The role router + independence (directive §7, §9; Art. XLV)
# ---------------------------------------------------------------------------
class TestRoleRouter:
    def _matrix(self):
        return [
            {"provider_id": "zai", "available": True, "model": "a",
             "quality_tier": 2, "cost_tier": 1, "latency_tier": 1,
             "context_capacity_tokens": 128000},
            {"provider_id": "openrouter", "available": True, "model": "b",
             "quality_tier": 2, "cost_tier": 2, "latency_tier": 2,
             "context_capacity_tokens": 128000},
            {"provider_id": "anthropic", "available": True, "model": "c",
             "quality_tier": 1, "cost_tier": 3, "latency_tier": 3,
             "context_capacity_tokens": 200000},
        ]

    def test_attack_role_avoids_generator_provider(self):
        order = ph.order_for_role(self._matrix(), ph.ROLE_ATTACK,
                                  avoid_provider="zai")
        assert order[0] != "zai"

    def test_extraction_role_prefers_fast_latency(self):
        order = ph.order_for_role(self._matrix(), ph.ROLE_EXTRACTION)
        assert order[0] == "zai"  # latency tier 1

    def test_synthesis_role_prefers_quality(self):
        order = ph.order_for_role(self._matrix(), ph.ROLE_SYNTHESIS)
        assert order[0] == "anthropic"  # quality tier 1

    def test_cooldown_demotion_never_removal(self, tmp_path):
        b = ph.ProviderHealthBook(health_dir=tmp_path / "b")
        b.record_failure("anthropic", ph.RATE_LIMITED)
        order = ph.order_for_role(self._matrix(), ph.ROLE_SYNTHESIS,
                                  book=b)
        assert "anthropic" in order          # demoted, not removed
        assert order[-1] == "anthropic"     # to the END

    def test_purpose_role_hints(self):
        assert ph.role_for_purpose(
            "structured_evidence_extraction") == ph.ROLE_EXTRACTION
        assert ph.role_for_purpose(
            "independent_attack") == ph.ROLE_ATTACK
        assert ph.role_for_purpose("whatever") == ph.ROLE_SYNTHESIS

    def test_independence_vocabulary(self):
        assert ph.independence_degree(
            "zai", "openrouter") == "SEPARATE_PROVIDER"
        assert ph.independence_degree(
            "zai", "zai") == "SEPARATE_CONTEXT_ONLY"
        assert ph.independence_degree(None, "zai") == "NOT_INDEPENDENT"


# ---------------------------------------------------------------------------
# 4. The provider cascade (directive §8 — never silent, bounded)
# ---------------------------------------------------------------------------
class TestProviderCascade:
    def _setup_env(self, monkeypatch):
        monkeypatch.setenv("ZAI_API_KEY", "k-zai")
        monkeypatch.setenv("OPENROUTER_API_KEY", "k-or")
        monkeypatch.delenv("NVIDIA_API_KEY", raising=False)

    def _hermetic_routing(self, monkeypatch, tmp_path):
        """R415: the cascade now routes through model_routing (ladder
        build + ledger + gone-state). Tests must never touch the
        production ledger/state/catalog (Art. IX) and must never hit the
        network (catalog discovery) — everything is redirected to a
        tmp dir and the catalog is reported UNDISCOVERED so the pinned
        defaults stand in."""
        from discovery_fabric.engine import model_routing as mr
        tmp = Path(tmp_path)
        monkeypatch.setattr(mr, "LEDGER", mr.RoutingLedger(
            path=tmp / "ledger.jsonl"))
        monkeypatch.setattr(mr, "STATE_PATH", tmp / "state.json")
        monkeypatch.setattr(
            mr, "discover_catalog",
            lambda provider_id, force=False: {
                "provider": provider_id, "status": "UNDISCOVERED",
                "fetched_at_epoch": 0.0, "models": [],
                "catalog_size": 0, "eligible_count": 0})
        mr.clear_probe_cache()
        return mr

    def test_failover_success_carries_route_never_silent(
            self, monkeypatch, tmp_path):
        """MODEL A fails (429) -> MODEL B succeeds: status OK, and the
        result CARRIES the failed hop (a silent failover is the exact
        failure mode the directive forbids)."""
        self._setup_env(monkeypatch)
        self._hermetic_routing(monkeypatch, tmp_path)
        book = ph.ProviderHealthBook(health_dir=tmp_path / "ph")
        calls = {"n": 0}

        def fake_call(spec, messages, timeout, max_tokens,
                      model_override=None):
            calls["n"] += 1
            if spec.provider_id == "zai":
                raise urllib.error.HTTPError(
                    "u", 429, "Too Many Requests", None, None)
            return "FALLBACK_ANSWER"

        monkeypatch.setattr(reg, "_call_openai_flavor", fake_call)
        monkeypatch.setattr(ph, "HEALTH", book)
        res = reg.generate("p", system="s", max_retries=0, timeout=5,
                           policy=reg.SelectionPolicy(
                               preferred_providers=["zai", "openrouter"],
                               purpose="test"))
        assert res.status == "OK"
        assert res.provider_id == "openrouter"
        assert res.route and len(res.route) == 1
        hop = res.route[0]
        assert hop["provider_attempted"] == "zai"
        assert hop["failure_type"] == ph.RATE_LIMITED
        assert res.failure_type is None
        # the health book recorded the failure AND the success
        snap = {p["provider"]: p for p in book.snapshot(
            provider_specs=reg.availability_matrix())}
        assert snap["zai"]["status"] == "RATE_LIMITED"
        assert snap["openrouter"]["status"] == "OK"

    def test_total_failure_is_call_failed_with_typed_route(
            self, monkeypatch, tmp_path):
        self._setup_env(monkeypatch)
        self._hermetic_routing(monkeypatch, tmp_path)
        book = ph.ProviderHealthBook(health_dir=tmp_path / "ph")

        def fake_call(spec, messages, timeout, max_tokens,
                      model_override=None):
            raise urllib.error.HTTPError(
                "u", 503, "Service Unavailable", None, None)

        monkeypatch.setattr(reg, "_call_openai_flavor", fake_call)
        monkeypatch.setattr(ph, "HEALTH", book)
        res = reg.generate("p", system="s", max_retries=0, timeout=5,
                           policy=reg.SelectionPolicy(
                               preferred_providers=["zai", "openrouter"],
                               purpose="test"))
        assert res.status == "CALL_FAILED"
        assert res.route and all(
            h["failure_type"] == ph.MODEL_FAILURE for h in res.route)
        assert res.failure_type == ph.MODEL_FAILURE
        assert res.content is None  # never a silent partial success

    def test_cascade_is_bounded(self, monkeypatch, tmp_path):
        """MODEL A -> B -> C, never an unbounded walk. R415: the bound
        is now 1 + max_provider_fallbacks + 2 MODEL hops (the directive's
        model-level cascade) — still bounded, still small."""
        self._setup_env(monkeypatch)
        for k in ("NVIDIA_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY",
                  "GEMINI_API_KEY", "QWEN_API_KEY", "DEEPSEEK_API_KEY",
                  "MISTRAL_API_KEY", "TOKEN_ROUTER_API_KEY"):
            monkeypatch.setenv(k, "k")
        self._hermetic_routing(monkeypatch, tmp_path)
        book = ph.ProviderHealthBook(health_dir=tmp_path / "ph")
        attempted = []

        def fake_call(spec, messages, timeout, max_tokens,
                      model_override=None):
            attempted.append((spec.provider_id, model_override))
            raise urllib.error.HTTPError(
                "u", 500, "boom", None, None)

        monkeypatch.setattr(reg, "_call_openai_flavor", fake_call)
        monkeypatch.setattr(reg, "_call_anthropic_flavor", fake_call)
        monkeypatch.setattr(ph, "HEALTH", book)
        res = reg.generate("p", system="s", max_retries=0, timeout=5,
                           max_provider_fallbacks=2)
        assert res.status == "CALL_FAILED"
        # exactly 1 + 2 provider fallbacks + 2 model hops
        assert len(attempted) == 5

    def test_no_credentials_is_provider_unavailable(self, monkeypatch):
        for k in list(os.environ):
            if k.endswith("_API_KEY") or k == "TOKEN_ROUTER_API_KEY":
                monkeypatch.delenv(k, raising=False)
        res = reg.generate("p", system="s", max_retries=0, timeout=5)
        assert res.status == "PROVIDER_UNAVAILABLE"
        assert res.content is None

    def test_cooldown_demoted_in_cascade(self, monkeypatch, tmp_path):
        """The cascade head skips a provider in rate-limit cooldown —
        but a lone cooled provider is still attempted (never a hard
        block; Art. V)."""
        self._setup_env(monkeypatch)
        self._hermetic_routing(monkeypatch, tmp_path)
        book = ph.ProviderHealthBook(health_dir=tmp_path / "ph")
        book.record_failure("zai", ph.RATE_LIMITED)
        order_seen = []

        def fake_call(spec, messages, timeout, max_tokens,
                      model_override=None):
            order_seen.append(spec.provider_id)
            return "OK-" + spec.provider_id

        monkeypatch.setattr(reg, "_call_openai_flavor", fake_call)
        monkeypatch.setattr(ph, "HEALTH", book)
        res = reg.generate("p", system="s", max_retries=0, timeout=5,
                           policy=reg.SelectionPolicy(
                               preferred_providers=["zai", "openrouter"],
                               purpose="test"))
        assert res.status == "OK"
        assert order_seen[0] == "openrouter"  # zai demoted behind it


# ---------------------------------------------------------------------------
# 5. The canonical run state + the four outcomes (directive §4, §18)
# ---------------------------------------------------------------------------
class TestTerminalOutcome:
    def _session(self, **kw):
        base = {"session_id": "s1", "user_text": "problem text",
                "status": "COMPLETE", "final_status": None,
                "package": {}, "run_dir": None}
        base.update(kw)
        return base

    def test_pending_while_running(self):
        for status in ("PENDING", "BUILDING_PROBLEM", "RUNNING"):
            o = rs.terminal_outcome(self._session(status=status))
            assert o["outcome"] == rs.OUTCOME_PENDING

    def test_survived_with_package(self):
        o = rs.terminal_outcome(self._session(
            final_status="AUTOMATED_INVENTION_CANDIDATE",
            package={"complete": True}))
        assert o["outcome"] == rs.OUTCOME_SURVIVED

    def test_requires_experiment_survivor_without_package(self):
        o = rs.terminal_outcome(self._session(
            final_status="AUTOMATED_INVENTION_CANDIDATE",
            package={}))
        assert o["outcome"] == rs.OUTCOME_REQUIRES_EXPERIMENT

    def test_no_defensible_for_rejected_and_false_premise(self):
        # R442 reconciliation (Art. LXIV rule 2, dated investigation):
        # R416 (honest causes + evolution V1, operator directive) remapped
        # REJECTED/MALFORMED_OR_FALSE_PREMISE to INVENTION_UNDER_DEVELOPMENT
        # / FALSE_PREMISE_INCOHERENT — the product never renders the banned
        # dead-end sentence; the recorded challenge outcome rides the
        # basis, the lineage carries the generations. The Art. LXI intent
        # is preserved and STILL asserted: neither outcome is RUN_BLOCKED.
        o = rs.terminal_outcome(self._session(final_status="REJECTED"))
        assert o["outcome"] == rs.OUTCOME_UNDER_DEVELOPMENT
        assert "REJECTED" in o["basis"]
        assert o["outcome"] != rs.OUTCOME_RUN_BLOCKED
        o2 = rs.terminal_outcome(
            self._session(final_status="MALFORMED_OR_FALSE_PREMISE"))
        assert o2["outcome"] == rs.OUTCOME_FALSE_PREMISE
        assert o2["outcome"] != rs.OUTCOME_RUN_BLOCKED

    def test_run_blocked_is_infrastructure_only(self):
        """Art. LXI: infrastructure failure is never scientific
        rejection — RUN_BLOCKED is reserved for the infrastructure
        class, and NO scientific rejection ever lands there."""
        for status in ("ERROR_TRANSPORT", "ERROR_BUILD", "ERROR_RUN",
                       "ERROR_STUCK", "INTERRUPTED"):
            o = rs.terminal_outcome(self._session(status=status))
            assert o["outcome"] == rs.OUTCOME_RUN_BLOCKED, status
            assert "infrastructure" in o["basis"]
        # COMPLETE without a verdict: not a rejection — blocked honestly
        o = rs.terminal_outcome(self._session(final_status="UNKNOWN"))
        assert o["outcome"] == rs.OUTCOME_RUN_BLOCKED
        o = rs.terminal_outcome(self._session(final_status=""))
        assert o["outcome"] == rs.OUTCOME_RUN_BLOCKED

    def test_no_rejection_maps_to_blocked(self):
        """A scientific REJECTED must NEVER become RUN_BLOCKED (the
        converse of Art. LXI — an honest kill is a real result).
        R442 reconciliation: the R416 contract carries the rejection as
        INVENTION_UNDER_DEVELOPMENT with the recorded basis (never the
        banned dead-end surface), which satisfies the same invariant."""
        o = rs.terminal_outcome(self._session(final_status="REJECTED"))
        assert o["outcome"] == rs.OUTCOME_UNDER_DEVELOPMENT
        assert o["outcome"] != rs.OUTCOME_RUN_BLOCKED
        assert "REJECTED" in o["basis"]

    def test_outcome_vocabulary_exact(self):
        assert {rs.OUTCOME_PENDING, rs.OUTCOME_SURVIVED,
                rs.OUTCOME_REQUIRES_EXPERIMENT,
                rs.OUTCOME_NO_DEFENSIBLE,
                rs.OUTCOME_RUN_BLOCKED} == {
            "PENDING", "INVENTION_SURVIVED",
            "INVENTION_REQUIRES_EXPERIMENT", "NO_DEFENSIBLE_INVENTION",
            "RUN_BLOCKED"}


class TestCanonicalRunState:
    def test_schema_fields_present(self, tmp_path):
        s = {"session_id": "s1", "user_text": "the problem",
             "created_at": "2026-09-06T00:00:00Z", "status": "RUNNING",
             "final_status": None, "package": {},
             "run_dir": str(tmp_path)}
        state = rs.canonical_run_state(s)
        for key in ("run_id", "user_problem", "created_at", "status",
                    "model_route", "retrieval_route", "evidence_state",
                    "mechanism_state", "invention_state", "physics_state",
                    "novelty_state", "attack_state", "experiment_state",
                    "package_state", "provenance", "failure_state",
                    "outcome", "phase_progression"):
            assert key in state, key

    def test_phases_never_fabricated_without_manifest(self, tmp_path):
        """No run manifest -> no phase claims DONE (honest NOT_STARTED /
        IN_PROGRESS only — the phase states come from the engine's own
        stage log, never from inference)."""
        s = {"session_id": "s1", "user_text": "p", "status": "RUNNING",
             "final_status": None, "package": {}, "run_dir": str(tmp_path)}
        state = rs.canonical_run_state(s)
        for ph in state["phase_progression"]:
            assert ph["state"] in ("NOT_STARTED", "IN_PROGRESS")
            assert ph["state"] != "DONE"

    def test_phases_done_only_from_recorded_stage_log(self, tmp_path):
        manifest = {"stage_log": [
            {"stage": "RETRIEVE", "status": "OK"},
            {"stage": "FREEZE", "status": "OK"},
            {"stage": "VERIFY", "status": "OK"},
        ]}
        (tmp_path / "run_manifest.json").write_text(json.dumps(manifest))
        s = {"session_id": "s1", "user_text": "p", "status": "COMPLETE",
             "final_status": "REJECTED", "package": {},
             "run_dir": str(tmp_path)}
        state = rs.canonical_run_state(s)
        phases = {p["phase"]: p for p in state["phase_progression"]}
        assert phases["GATHERING_EVIDENCE"]["state"] == "DONE"
        assert phases["MAPPING_MECHANISMS"]["state"] == "NOT_STARTED"

    def test_model_route_only_from_persisted_records(self, tmp_path):
        """model_route reports ONLY the run's own routing-ledger
        records — a fabricated provider (never called, embedded in an
        envelope) must not appear.

        R455-LEAN-1 §4 re-pin: the source is ROUTING_LEDGER_RUN.json
        (the run-id-isolated routing ledger, R451-C1.3-3) — envelope
        aggregation is dead (the audited 13-vs-1 defect, Art. XXIV)."""
        s = {"session_id": "s1", "user_text": "p", "status": "COMPLETE",
             "final_status": "REJECTED", "package": {},
             "run_dir": str(tmp_path)}
        state = rs.canonical_run_state(s)
        assert state["model_route"]["call_count"] == 0
        # the fabricated record: an envelope-embedded provider entry
        env = {"mechanism_map": {"llm": {"provider": "zai",
                                         "model": "glm-4-plus"}}}
        (tmp_path / "envelope_SYNTHESIZE.json").write_text(
            json.dumps(env))
        state = rs.canonical_run_state(s)
        assert state["model_route"]["call_count"] == 0
        assert not any(c.get("provider") == "zai"
                       for c in state["model_route"]["calls"])
        # the REAL record: the run's own ledger — and now it appears
        (tmp_path / "ROUTING_LEDGER_RUN.json").write_text(json.dumps({
            "run_id": "s1", "line_count": 1,
            "run_owned_call_lines": 1,
            "lines": [{"run_id": "s1", "call_class": "RUN_OWNED",
                       "engine_stage": "SYNTHESIZE",
                       "provider": "zai", "model": "glm-4-plus",
                       "status": "OK", "task": "STRONG"}]}))
        state = rs.canonical_run_state(s)
        assert state["model_route"]["call_count"] >= 1
        assert any(c.get("provider") == "zai"
                   for c in state["model_route"]["calls"])


# ---------------------------------------------------------------------------
# 6. The Canonical Invention Object (directive §12-14)
# ---------------------------------------------------------------------------
class TestCIO:
    def _run_dir(self, tmp_path, with_spec=True, with_pm=True,
                 with_physics=False, with_model_dir=False):
        if with_spec:
            (tmp_path / "INVENTION_SPECIFICATION.json").write_text(
                json.dumps({
                    "invention_id": "INV-1",
                    "mechanism": "the mechanism",
                    "novelty_hypothesis": "the hypothesis",
                    "evidence": [{"id": "e1", "title": "Evidence one",
                                  "source": "europepmc",
                                  "evidence_class": "SOURCE_FACT"}],
                    "killer_experiment": {"name": "the experiment"}}))
        if with_pm:
            (tmp_path / "PARAMETRIC_MODEL.json").write_text(
                json.dumps({"parameters": [
                    {"param_id": "d", "value": 2.4, "unit": "mm",
                     "range_min": 1.0, "range_max": 4.0}]}))
        if with_physics:
            (tmp_path / "envelope_PHYSICS.json").write_text(
                json.dumps({"physics": {
                    "lifecycle_verdict": "PASSES_BOUNDS",
                    "baseline_comparison": {"outcome":
                                            "IMPROVES_BASELINE"}}}))
        if with_model_dir:
            m = tmp_path / "MODEL"
            m.mkdir(exist_ok=True)
            (m / "design.glb").write_bytes(b"GLB_BYTES")
        return tmp_path

    def _session(self, run_dir, final="AUTOMATED_INVENTION_CANDIDATE"):
        return {"session_id": "s1", "user_text": "p",
                "status": "COMPLETE", "final_status": final,
                "package": {"complete": True}, "run_dir": str(run_dir)}

    def test_no_artifacts_no_cio(self, tmp_path):
        """An existing-but-empty run dir produces NO CIO — an empty
        object would still look like an invention surface (honest
        absence instead, Art. XXV).

        R455-LEAN-1 §1 re-pin: `final_state.json` is RUN state, not
        invention-side state — every run writes one, so it no longer
        manufactures a CIO. ONE invention-side artifact is still enough
        to build the object (Art. V: not a universal rejector)."""
        assert cio_mod.build_cio(
            {"session_id": "s", "run_dir": str(tmp_path)}) is None
        # the RUN's own state record alone manufactures nothing
        (tmp_path / "final_state.json").write_text(
            json.dumps({"final_status": "REJECTED"}))
        assert cio_mod.build_cio(
            {"session_id": "s", "run_dir": str(tmp_path)}) is None
        # one invention-side artifact is enough
        (tmp_path / "INVENTION_SPECIFICATION.json").write_text(
            json.dumps({"invention_id": {"value": "INV-1"}}))
        assert cio_mod.build_cio(
            {"session_id": "s", "run_dir": str(tmp_path)}) is not None

    def test_maturity_fields_from_artifacts(self, tmp_path):
        rd = self._run_dir(tmp_path, with_physics=True,
                           with_model_dir=False)
        cio = cio_mod.build_cio(self._session(rd))
        assert cio is not None
        m = cio["maturity"]
        assert m["design"] is True            # parametric model present
        assert m["simulation"] is True        # PHYSICS verdict recorded
        assert m["evidence_supported"] is True
        assert m["experimentally_verified"] is False  # honest — no real
        # observation (Art. LIII: reality cannot be simulated into
        # existence)
        assert "DESIGNED" in m["maturity_ladder"]
        assert "EXPERIMENTALLY_VERIFIED" not in m["maturity_ladder"]

    def test_maturity_falls_to_false_without_artifacts(self, tmp_path):
        rd = self._run_dir(tmp_path, with_pm=False, with_physics=False)
        cio = cio_mod.build_cio(self._session(rd, final="REJECTED"))
        assert cio["maturity"]["design"] is False
        assert cio["maturity"]["simulation"] is False

    def test_geometry_from_run_model_dir(self, tmp_path):
        rd = self._run_dir(tmp_path, with_model_dir=True)
        cio = cio_mod.build_cio(self._session(rd))
        assert cio["geometry"]["present"] is True
        assert cio["geometry"]["glb"] == "/api/run/s1/model"
        assert cio["geometry"]["glb_sha256"]

    def test_simulation_class_is_computational_result(self, tmp_path):
        rd = self._run_dir(tmp_path, with_physics=True)
        cio = cio_mod.build_cio(self._session(rd))
        assert cio["simulation"]["epistemic_class"] == \
            "COMPUTATIONAL_RESULT"

    def test_legal_position_carried_never_patentability(self, tmp_path):
        rd = self._run_dir(tmp_path)
        cio = cio_mod.build_cio(self._session(rd))
        assert "patent counsel" in cio["legal_position"].lower()
        assert "formal legal review required" in cio[
            "novelty_language"].lower()

    def test_counsel_download_route(self, tmp_path):
        # R423A Phase 3 — ONE package: the separate counsel export is no
        # longer a customer surface. The CIO must NOT advertise a second
        # package route, and the technical evidence it carried rides
        # inside the single technology transfer package.
        rd = self._run_dir(tmp_path)
        cio = cio_mod.build_cio(self._session(rd))
        assert "counsel_package" not in cio["downloads"]
        assert cio["downloads"]["package_kind"] == \
            "TECHNOLOGY_TRANSFER_PACKAGE"
        assert cio["downloads"]["package_origin"] in (
            "INVENTION_BRIDGE", "BUYER_RELEASE_CHAIN")


# ---------------------------------------------------------------------------
# 7. The language guard (directive §3 — not a patent court)
# ---------------------------------------------------------------------------
class TestLanguageGuard:
    def test_banned_words_detected(self):
        for phrase in ("This invention is patentable",
                       "FTO confirmed for the design",
                       "patent guaranteed",
                       "the mechanism is legally novel"):
            g = cio_mod.language_guard(phrase)
            assert g["clean"] is False, phrase

    def test_preferred_language_clean(self):
        g = cio_mod.language_guard(cio_mod.PREFERRED_NOVELTY_LANGUAGE)
        assert g["clean"] is True
        g2 = cio_mod.language_guard(cio_mod.LEGAL_POSITION)
        assert g2["clean"] is True

    def test_guard_on_quarantined_narrative(self, tmp_path):
        """A model-generated narrative carrying 'patentable' is detected
        on the CIO and DISCLOSED — never silently edited (Art. XV)."""
        (tmp_path / "INVENTION_SPECIFICATION.json").write_text(json.dumps(
            {"invention_id": "X", "mechanism":
             "a mechanism that is patentable and novel"}))
        cio = cio_mod.build_cio({
            "session_id": "s", "user_text": "p", "status": "COMPLETE",
            "final_status": "AUTOMATED_INVENTION_CANDIDATE",
            "package": {}, "run_dir": str(tmp_path)})
        assert cio["language_guard"]["clean"] is False
        assert "patentable" in cio["language_guard"]["violations"]

    def test_product_copy_files_clean(self):
        """The deterministic product surface carries no patentability
        assertions (scan the shipped UI copy + server copy)."""
        banned = ("patentable", "patent guaranteed", "patent cleared",
                  "fto confirmed", "legally novel")
        files = list((REPO / "TOSCANINI_UI" / "webapp" / "app").glob(
            "**/*.tsx")) + list(
            (REPO / "TOSCANINI_UI" / "webapp" / "components").glob(
                "*.tsx"))
        assert files, "webapp sources not found"
        for f in files:
            text = f.read_text().lower()
            for b in banned:
                assert b not in text, f"{f.name} carries '{b}'"


# ---------------------------------------------------------------------------
# 8. The counsel package (directive §20)
# ---------------------------------------------------------------------------

class TestProjections:
    def test_user_state_view_carries_outcome(self):
        from toscanini.user_state import user_state_view
        v = user_state_view({"status": "COMPLETE",
                             "final_status": "REJECTED",
                             "package": {}})
        # R442 reconciliation: the R416 surface contract (the banned
        # dead-end sentence is never rendered; the shipped mapping is
        # INVENTION_UNDER_DEVELOPMENT).
        assert v["outcome"] == "INVENTION_UNDER_DEVELOPMENT"
        v2 = user_state_view({"status": "ERROR_TRANSPORT",
                              "final_status": None, "package": {}})
        assert v2["outcome"] == "RUN_BLOCKED"
        v3 = user_state_view({"status": "RUNNING", "final_status": None,
                              "package": {}})
        assert v3["outcome"] == "PENDING"

    def test_health_payload_has_provider_surface(self):
        from toscanini import server
        h = server._health_payload()
        r = h["readiness"]
        assert isinstance(r["providers"], list)
        assert len(r["providers"]) == 10
        assert "status" in r["providers"][0]
        for key in ("llm_ready", "physics_ready", "reality_loop_ready",
                    "showcase_ready", "retrieval_ready", "providers"):
            assert key in r, key

    def test_no_provider_secrets_in_health(self):
        """Directive §6: keys never appear in /api/health."""
        from toscanini import server
        h = json.dumps(server._health_payload())
        for k in ("ZAI_API_KEY", "NVIDIA_API_KEY", "OPENROUTER_API_KEY",
                  "TOKEN_ROUTER_API_KEY", "ANTHROPIC_API_KEY"):
            assert k not in h
            assert "Bearer" not in h


# ---------------------------------------------------------------------------
# 10. Metamorphic / adversarial (Art. VIII, XVII)
# ---------------------------------------------------------------------------
class TestAdversarial:
    def test_outcome_flip_on_package_availability(self):
        """The terminal outcome is a pure function of recorded fields:
        flipping package.complete flips SURVIVED to
        REQUIRES_EXPERIMENT (no cached verdicts)."""
        base = {"session_id": "s", "user_text": "p", "status": "COMPLETE",
                "final_status": "AUTOMATED_INVENTION_CANDIDATE",
                "package": {"complete": True}}
        assert rs.terminal_outcome(base)["outcome"] == \
            rs.OUTCOME_SURVIVED
        base["package"] = {"complete": False}
        assert rs.terminal_outcome(base)["outcome"] == \
            rs.OUTCOME_REQUIRES_EXPERIMENT

    def test_tampered_final_status_flips_outcome(self):
        base = {"session_id": "s", "user_text": "p", "status": "COMPLETE",
                "final_status": "REJECTED", "package": {}}
        # R442 reconciliation: the shipped R416 mapping for REJECTED.
        assert rs.terminal_outcome(base)["outcome"] == \
            rs.OUTCOME_UNDER_DEVELOPMENT
        base["final_status"] = "AUTOMATED_INVENTION_CANDIDATE"
        assert rs.terminal_outcome(base)["outcome"] == \
            rs.OUTCOME_REQUIRES_EXPERIMENT

    def test_cascade_route_is_complete_not_summarized(self):
        """Every failed hop appears in the route with the directive §8
        fields — a summarized route would hide a failover."""
        hop_fields = ("provider_attempted", "model", "failure_type",
                      "timestamp", "fallback_provider")
        res = reg.LLMCallResult(
            status="OK", route=[{
                "provider_attempted": "zai", "model": "m",
                "failure_type": "RATE_LIMITED", "timestamp": "t",
                "fallback_provider": "openrouter"}])
        for f in hop_fields:
            assert f in res.route[0]
        meta = res.to_meta()
        assert meta["provider_route"][0]["provider"] == "zai"

    def test_unknown_failure_stays_unknown(self, tmp_path):
        """An unclassifiable exception is UNKNOWN — never forced into a
        confident class (Art. XXV)."""
        book = ph.ProviderHealthBook(health_dir=tmp_path)
        book.record_failure("zai", "SOMETHING_ODD")
        assert book.last_failure_type("zai") == ph.UNKNOWN

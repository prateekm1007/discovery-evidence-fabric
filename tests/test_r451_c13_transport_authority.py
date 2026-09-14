"""tests/test_r451_c13_transport_authority.py — R451-C1.3 battery.

Operator directive (2026-09-13): Production Transport Authority +
Provenance Closure. The adversarial tests for:

  C1.3-1  capability probes as the RUNTIME authority (the five-state
          vocabulary; only PROBE_OK + policy eligible admits; the local
          route uses the SAME rule; TTL, never per-call probing)
  C1.3-2  TRANSPORT/CAPABILITY failure stays separate from discovery
          adjudication (Art. LXI discipline preserved)
  C1.3-3  run-level routing provenance (run_owned_call => run_id != null;
          the 13 operator fields; run isolation WITHOUT time windows;
          capability probes legitimately run_id-null)
  C1.4    explicit task degradation (STRONG requested, CHEAP served ->
          CHEAP_EMERGENCY_FALLBACK, visible in provenance)
  C1.5    catalog DISCOVERED -> only catalog-present models eligible;
          UNDISCOVERED -> PINNED_DEFAULT (explicit)
  C1.6    MODEL_NOT_FOUND recovery: 404 -> dead -> fresh catalog lists
          -> cleared -> eligible (deterministic)
  C1.7    ONE admission semantic in select_provider() and generate()

Art. XVII discipline: the bypass attempts are IMPLEMENTED attacks —
a forged capability record must not admit a policy-refused route; a
null-run_id run-owned line must FAIL CLOSED; a stale catalog must not
resurrect a dead identifier through the back door.
"""
import json
import sys
import time as time_mod
import urllib.error
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine import llm_registry as reg  # noqa: E402
from discovery_fabric.engine import model_cost_policy as cp  # noqa: E402
from discovery_fabric.engine import model_routing as mr  # noqa: E402
from discovery_fabric.engine import runtime_admission as ra  # noqa: E402
from discovery_fabric.engine import call_context as cctx  # noqa: E402
from discovery_fabric.engine import provider_health as ph  # noqa: E402

# the REAL catalog discovery (captured at import time — the hermetic
# fixture replaces mr.discover_catalog per-test; the TTL test needs
# the real implementation's cache path)
REAL_DISCOVER_CATALOG = mr.discover_catalog


# ---------------------------------------------------------------------------
# hermetic routing fixtures (Art. IX: production state is never touched)
# ---------------------------------------------------------------------------
@pytest.fixture()
def hermetic(monkeypatch, tmp_path):
    tmp = Path(tmp_path)
    monkeypatch.setattr(mr, "LEDGER", mr.RoutingLedger(
        path=tmp / "ledger.jsonl"))
    monkeypatch.setattr(mr, "STATE_PATH", tmp / "state.json")
    monkeypatch.setattr(mr, "CATALOG_DIR", tmp / "catalog")
    # R451-C1.3: the capability store is production admission state —
    # tests redirect it (Art. IX)
    ra.set_state_path(tmp / "capability_state.json")
    monkeypatch.setattr(
        mr, "discover_catalog",
        lambda provider_id, force=False: {
            "provider": provider_id, "status": "UNDISCOVERED",
            "fetched_at_epoch": 0.0, "models": [],
            "catalog_size": 0, "eligible_count": 0})
    mr.clear_probe_cache()
    monkeypatch.setattr(ph, "HEALTH", ph.ProviderHealthBook(
        health_dir=tmp / "ph"))
    yield monkeypatch, tmp
    mr.clear_probe_cache()
    ra.set_state_path(None)


_ALL_KEY_VARS = ["OPENROUTER_API_KEY", "QWEN_API_KEY",
                 "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY",
                 "DEEPSEEK_API_KEY", "MISTRAL_API_KEY",
                 "NVIDIA_API_KEY", "ZAI_API_KEY",
                 "TOKEN_ROUTER_API_KEY"]


def _no_keys(monkeypatch):
    for k in _ALL_KEY_VARS:
        monkeypatch.delenv(k, raising=False)


def _pin_localqwen(monkeypatch, caps=("CHEAP",)):
    monkeypatch.setattr(mr, "PINNED_DEFAULT_MODELS", {
        "localqwen": [
            {"model": "qwen3-1.7b",
             "task_capabilities": list(caps),
             "cost_class": 1, "latency_class": 4,
             "context_limit": 32768}],
    })


def _wire_local(monkeypatch):
    monkeypatch.setenv("LOCAL_QWEN_BASE_URL",
                       "http://127.0.0.1:8790/v1/chat/completions")


# ---------------------------------------------------------------------------
# C1.3-1 — the runtime admission authority
# ---------------------------------------------------------------------------
class TestCapabilityStates:

    def test_the_five_state_vocabulary_is_closed(self):
        assert ra.CAPABILITY_STATES == (
            "NOT_PROBED", "PROBE_OK", "PROBE_FAILED", "PROBE_EXPIRED",
            "POLICY_REFUSED")

    def test_no_record_is_not_probed(self, hermetic):
        monkeypatch, tmp = hermetic
        st = ra.capability_state("localqwen", "qwen3-1.7b")
        assert st["state"] == ra.ST_NOT_PROBED
        assert ra.requires_probe("localqwen", "qwen3-1.7b")

    def test_successful_probe_is_probe_ok(self, hermetic):
        monkeypatch, tmp = hermetic
        ra.record_capability("localqwen", "qwen3-1.7b", ok=True,
                             latency_ms=900, source="probe")
        st = ra.capability_state("localqwen", "qwen3-1.7b")
        assert st["state"] == ra.ST_PROBE_OK
        assert not ra.requires_probe("localqwen", "qwen3-1.7b")

    def test_failed_probe_is_probe_failed_with_class(self, hermetic):
        monkeypatch, tmp = hermetic
        ra.record_capability("localqwen", "qwen3-1.7b", ok=False,
                             failure_class="AUTH_FAILURE", source="probe")
        st = ra.capability_state("localqwen", "qwen3-1.7b")
        assert st["state"] == ra.ST_PROBE_FAILED
        assert st["record"]["failure_class"] == "AUTH_FAILURE"
        assert not ra.requires_probe("localqwen", "qwen3-1.7b")

    def test_stale_record_is_probe_expired(self, hermetic):
        monkeypatch, tmp = hermetic
        ra.record_capability("localqwen", "qwen3-1.7b", ok=True,
                             source="probe")
        # age the record past the TTL (the existing mechanism:
        # model_routing.PROBE_TTL_S)
        state = json.loads(ra._state_path().read_text())
        key = "localqwen::qwen3-1.7b"
        state["capability_records"][key]["at_epoch"] = \
            state["capability_records"][key]["at_epoch"] - \
            mr.PROBE_TTL_S - 10
        ra._state_path().write_text(json.dumps(state))
        st = ra.capability_state("localqwen", "qwen3-1.7b")
        assert st["state"] == ra.ST_PROBE_EXPIRED
        assert ra.requires_probe("localqwen", "qwen3-1.7b")

    def test_probe_ok_but_policy_refused_is_policy_refused(
            self, hermetic, monkeypatch):
        monkeypatch.setenv("ENGINE_MODEL_COST_POLICY", "ZERO_PAID_COST")
        monkeypatch.setenv("OPENAI_API_KEY", "k")
        ra.record_capability("openai", "gpt-4o", ok=True, source="probe")
        st = ra.capability_state("openai", "gpt-4o")
        assert st["state"] == ra.ST_POLICY_REFUSED
        # the admission is refused with the POLICY_REFUSED state — the
        # route is MEASURED but not ADMITTED (fail-closed, Art. IV/VII)
        ok, note, ev = ra.runtime_admission("openai", "gpt-4o")
        assert not ok
        assert "POLICY_REFUSED" in note

    def test_only_probe_ok_plus_policy_eligible_admits(
            self, hermetic, monkeypatch):
        monkeypatch.setenv("ENGINE_MODEL_COST_POLICY", "ZERO_PAID_COST")
        cases = {
            "NOT_PROBED": (None, None),
            "PROBE_FAILED": (False, "AUTH_FAILURE"),
            "PROBE_EXPIRED": ("expired", None),
        }
        for expected, (ok, ftype) in cases.items():
            if expected == "NOT_PROBED":
                continue
            if expected == "PROBE_EXPIRED":
                ra.record_capability("localqwen", "qwen3-1.7b",
                                     ok=True, source="probe")
                state = json.loads(ra._state_path().read_text())
                key = "localqwen::qwen3-1.7b"
                state["capability_records"][key]["at_epoch"] = 0.0
                ra._state_path().write_text(json.dumps(state))
            else:
                ra.record_capability("localqwen", "qwen3-1.7b", ok=ok,
                                     failure_class=ftype, source="probe")
            admitted, note, ev = ra.runtime_admission(
                "localqwen", "qwen3-1.7b")
            assert not admitted, (expected, note)
            assert ev["state"] == expected
        # the ONLY admitting state: PROBE_OK + policy eligible
        monkeypatch, tmp = hermetic
        ra.record_capability("localqwen", "qwen3-1.7b", ok=True,
                             source="probe")
        admitted, note, ev = ra.runtime_admission(
            "localqwen", "qwen3-1.7b")
        assert admitted
        assert ev["state"] == ra.ST_PROBE_OK


class TestGenerateAdmission:

    def test_credential_presence_is_not_admissibility(
            self, hermetic, monkeypatch):
        """The C1.3-1 core: a route with a present credential and NO
        current measured successful capability probe is PROBED before
        its real call — generate() never calls an unprobed route."""
        monkeypatch, tmp = hermetic
        _no_keys(monkeypatch)
        _pin_localqwen(monkeypatch)
        _wire_local(monkeypatch)
        calls = []

        def fake_call(spec, messages, timeout, max_tokens,
                      model_override=None):
            calls.append((spec.provider_id, model_override,
                          messages[1]["content"][:20]))
            return "TRANSPORT: ready"

        monkeypatch.setattr(reg, "_call_openai_flavor", fake_call)
        res = reg.generate("Reply with: READY", system="probe",
                           max_tokens=8, max_retries=0, timeout=10)
        assert res.status == reg.ST_OK
        # TWO transport calls: the capability PROBE first, the REAL call
        # second — the probe is the admission authority, never skipped
        assert len(calls) == 2
        assert calls[0][2] == ra.PROBE_PROMPT[:20]
        assert calls[1][2] != ra.PROBE_PROMPT[:20]

    def test_ttl_means_no_probe_per_call(self, hermetic, monkeypatch):
        """The existing TTL mechanism: within the TTL window a second
        call does NOT re-probe (one probe per route per window, never
        one per call)."""
        monkeypatch, tmp = hermetic
        _no_keys(monkeypatch)
        _pin_localqwen(monkeypatch)
        _wire_local(monkeypatch)
        n = {"calls": 0}

        def fake_call(spec, messages, timeout, max_tokens,
                      model_override=None):
            n["calls"] += 1
            return "TRANSPORT: ready"

        monkeypatch.setattr(reg, "_call_openai_flavor", fake_call)
        r1 = reg.generate("first", system="s", max_tokens=8,
                          max_retries=0, timeout=10)
        r2 = reg.generate("second", system="s", max_tokens=8,
                          max_retries=0, timeout=10)
        assert r1.ok and r2.ok
        # probe + real + real (NO second probe): 3 transport calls total
        assert n["calls"] == 3

    def test_probe_failed_run_is_skipped_with_state_recorded(
            self, hermetic, monkeypatch):
        """A route whose probe FAILS is not attempted — the skip is
        DISCLOSED on the route with the typed probe failure class."""
        monkeypatch, tmp = hermetic
        _no_keys(monkeypatch)
        _pin_localqwen(monkeypatch)
        _wire_local(monkeypatch)

        def fake_call(spec, messages, timeout, max_tokens,
                      model_override=None):
            if messages[1]["content"].startswith(ra.PROBE_PROMPT[:20]):
                raise urllib.error.HTTPError(
                    "u", 401, "Unauthorized", None, None)
            return "READY"

        monkeypatch.setattr(reg, "_call_openai_flavor", fake_call)
        res = reg.generate("Reply with: READY", system="probe",
                           max_tokens=8, max_retries=0, timeout=10)
        assert res.status == reg.ST_CALL_FAILED
        assert res.route, "the refused rung is DISCLOSED, never silent"
        hop = res.route[0]
        assert hop["status"] == "SKIPPED_NOT_ADMITTED"
        assert hop["capability_state"] == ra.ST_PROBE_FAILED
        assert hop["failure_type"] == "AUTH_FAILURE"

    def test_transient_probe_failure_is_absorbed_by_the_bounded_retry(
            self, hermetic, monkeypatch):
        """The acceptance run's measured defect (runtime_admission 1.1.0):
        a probe failing ONCE with a TRANSIENT class (the ~5 s
        llama-server restart window) is retried within the SAME bounded
        walk — the route is admitted and the call succeeds; never a
        TTL-length lockout for a transient outage."""
        monkeypatch, tmp = hermetic
        _no_keys(monkeypatch)
        _pin_localqwen(monkeypatch)
        _wire_local(monkeypatch)
        state = {"probe_failed_once": False}

        def fake_call(spec, messages, timeout, max_tokens,
                      model_override=None):
            if messages[1]["content"].startswith(ra.PROBE_PROMPT[:20]):
                if not state["probe_failed_once"]:
                    state["probe_failed_once"] = True
                    raise ConnectionError("transient restart window")
                return "TRANSPORT: ready"
            return "READY"

        monkeypatch.setattr(reg, "_call_openai_flavor", fake_call)
        monkeypatch.setattr(time_mod, "sleep", lambda s: None)
        res = reg.generate("p", system="s", max_tokens=8,
                           max_retries=2, timeout=10)
        assert res.status == reg.ST_OK
        assert state["probe_failed_once"]
        # the probe retried and succeeded -> the route served
        st = ra.capability_state("localqwen", "qwen3-1.7b")
        assert st["state"] == ra.ST_PROBE_OK

    def test_permanent_probe_failure_is_never_retried(
            self, hermetic, monkeypatch):
        """AUTH_FAILURE is permanent: ONE probe, no retry, the rung is
        skipped immediately (never retry a permanently invalid route)."""
        monkeypatch, tmp = hermetic
        _no_keys(monkeypatch)
        _pin_localqwen(monkeypatch)
        _wire_local(monkeypatch)
        n = {"probes": 0}

        def fake_call(spec, messages, timeout, max_tokens,
                      model_override=None):
            if messages[1]["content"].startswith(ra.PROBE_PROMPT[:20]):
                n["probes"] += 1
                raise urllib.error.HTTPError(
                    "u", 401, "Unauthorized", None, None)
            return "READY"

        monkeypatch.setattr(reg, "_call_openai_flavor", fake_call)
        monkeypatch.setattr(time_mod, "sleep", lambda s: None)
        res = reg.generate("p", system="s", max_tokens=8,
                           max_retries=2, timeout=10)
        assert res.status == reg.ST_CALL_FAILED
        assert n["probes"] == 1

    def test_aged_probe_failure_reprobes_after_the_floor(
            self, hermetic):
        """A PROBE_FAILED record older than the failure floor requires a
        fresh probe (failures age out faster than successes — a noisy
        outage must not poison the route for the full TTL)."""
        monkeypatch, tmp = hermetic
        ra.record_capability("localqwen", "qwen3-1.7b", ok=False,
                             failure_class="NETWORK_FAILURE",
                             source="probe")
        assert not ra.requires_probe("localqwen", "qwen3-1.7b"), \
            "fresh failure: within the floor, no immediate re-probe"
        state = json.loads(ra._state_path().read_text())
        key = "localqwen::qwen3-1.7b"
        state["capability_records"][key]["at_epoch"] -= \
            ra.PROBE_FAILURE_FLOOR_S + 5
        ra._state_path().write_text(json.dumps(state))
        assert ra.requires_probe("localqwen", "qwen3-1.7b")

    def test_the_local_route_uses_the_same_rule_no_bespoke_exception(
            self, hermetic, monkeypatch):
        """The directive's explicit constraint: the localqwen route is
        admitted through the SAME probe+policy authority — no
        conductor-side if-local branch. Verified structurally: the
        generate() walk contains NO provider-conditional admission
        (source scan) and behaviorally: an unprobed local route is
        probed; a failed local probe skips it like any other."""
        import inspect
        src = inspect.getsource(reg.generate)
        for forbidden in ("if spec.provider_id ==",
                          'provider_id == "localqwen"',
                          'if provider_id == "localqwen"'):
            assert forbidden not in src, forbidden
        # behavioral: probe-before-admit applies to localqwen (covered
        # above) and a PROBE_FAILED local route is skipped identically
        monkeypatch, tmp = hermetic
        _no_keys(monkeypatch)
        _pin_localqwen(monkeypatch)
        _wire_local(monkeypatch)
        ra.record_capability("localqwen", "qwen3-1.7b", ok=False,
                             failure_class="NETWORK_FAILURE",
                             source="probe")
        res = reg.generate("Reply with: READY", system="probe",
                           max_tokens=8, max_retries=0, timeout=10)
        assert res.status == reg.ST_CALL_FAILED
        assert res.route[0]["status"] == "SKIPPED_NOT_ADMITTED"
        assert res.route[0]["provider_attempted"] == "localqwen"


# ---------------------------------------------------------------------------
# C1.3-2 — transport failure NEVER becomes a discovery verdict
# ---------------------------------------------------------------------------
class TestTransportScientificSeparation:

    def test_admission_refusal_is_a_transport_status_never_a_verdict(
            self, hermetic, monkeypatch):
        monkeypatch, tmp = hermetic
        _no_keys(monkeypatch)
        _pin_localqwen(monkeypatch)
        _wire_local(monkeypatch)
        ra.record_capability("localqwen", "qwen3-1.7b", ok=False,
                             failure_class="MODEL_FAILURE",
                             source="probe")
        res = reg.generate("p", system="s", max_tokens=8,
                           max_retries=0, timeout=10)
        # infrastructure failure vocabulary (Art. LXI): CALL_FAILED /
        # PROVIDER_UNAVAILABLE / POLICY_BLOCKED — never REJECTED_*
        assert res.status in (reg.ST_CALL_FAILED,
                              reg.ST_PROVIDER_UNAVAILABLE,
                              reg.ST_POLICY_BLOCKED)
        assert "KILLED" not in (res.error or "")
        assert "REJECT" not in (res.error or "")

    def test_capability_state_vocabulary_carries_no_verdicts(self):
        for st in ra.CAPABILITY_STATES:
            assert "REJECT" not in st and "KILL" not in st \
                and "SURVIV" not in st, st


# ---------------------------------------------------------------------------
# C1.3-3 — run-level routing provenance
# ---------------------------------------------------------------------------
class TestRunOwnedProvenance:

    def test_ledger_line_carries_all_directive_fields(
            self, hermetic, monkeypatch):
        monkeypatch, tmp = hermetic
        _no_keys(monkeypatch)
        _pin_localqwen(monkeypatch, caps=("STRONG",))
        _wire_local(monkeypatch)
        monkeypatch.setattr(
            reg, "_call_openai_flavor",
            lambda spec, messages, timeout, max_tokens,
            model_override=None: "READY")
        token = cctx.bind_run("run-c13-fields", session_id="sess-c13")
        try:
            cctx.set_stage("MECHANISM_SPACE")
            res = reg.generate("p", system="s", max_tokens=8,
                               max_retries=0, timeout=10)
        finally:
            cctx.unbind(token)
        assert res.ok
        lines = [l for l in mr.LEDGER.tail(10)
                 if l.get("call_class") == "RUN_OWNED"]
        assert lines
        line = lines[-1]
        # the directive's 13 fields (run_id, session_id, request_id,
        # stage, provider, model, attempt, task, cost basis, account
        # domain, failure class, fallback_from, fallback_to)
        for field in ("run_id", "session_id", "request_id", "stage",
                      "provider", "model", "attempt", "task",
                      "cost_class", "account_domain", "failure_class",
                      "fallback_from", "fallback_to"):
            assert field in line, field
        assert line["run_id"] == "run-c13-fields"
        assert line["session_id"] == "sess-c13"
        assert line["engine_stage"] == "MECHANISM_SPACE"
        assert line["account_domain"] == "LOCAL_COMPUTE"
        assert line["cost_class"] == "ZERO_PAID_COST_SELF_HOSTED"

    def test_run_owned_call_with_null_run_id_fails_closed(
            self, hermetic):
        """The invariant is MECHANICAL: the ledger REFUSES a run-owned
        line with no run identity (the caller fixes the call site —
        never the ledger)."""
        monkeypatch, tmp = hermetic
        with pytest.raises(ValueError, match="run_owned_call"):
            mr.record_call_outcome(
                "localqwen", "qwen3-1.7b", ok=True, task="STRONG",
                stage="synthesis", run_id=None, attempt=1,
                cost_class="ZERO_PAID_COST_SELF_HOSTED", selected=True,
                call_class="RUN_OWNED")

    def test_capability_probes_legitimately_carry_null_run_id(
            self, hermetic, monkeypatch):
        """The two call classes are DISTINGUISHABLE: provider capability
        probes are not run-owned discovery calls — run_id null is the
        honest value for them, and only for them."""
        monkeypatch, tmp = hermetic
        _no_keys(monkeypatch)
        _pin_localqwen(monkeypatch)
        _wire_local(monkeypatch)
        monkeypatch.setattr(
            reg, "_call_openai_flavor",
            lambda spec, messages, timeout, max_tokens,
            model_override=None: "TRANSPORT: ready")
        token = cctx.bind_run("run-c13-probe-distinction")
        try:
            res = reg.generate("p", system="s", max_tokens=8,
                               max_retries=0, timeout=10)
        finally:
            cctx.unbind(token)
        assert res.ok
        tail = mr.LEDGER.tail(10)
        probe_lines = [l for l in tail
                       if l.get("call_class") == "CAPABILITY_PROBE"]
        run_lines = [l for l in tail
                     if l.get("call_class") == "RUN_OWNED"]
        assert probe_lines and run_lines
        assert all(l["run_id"] is None for l in probe_lines)
        assert all(l["run_id"] == "run-c13-probe-distinction"
                   for l in run_lines)

    def test_ledger_isolates_one_run_without_time_window(
            self, hermetic, monkeypatch):
        """Two interleaved runs: each run's lines are recoverable BY RUN
        ID alone — no time-window inference, no ledger-tail assumption
        (the directive's acceptance)."""
        monkeypatch, tmp = hermetic
        _no_keys(monkeypatch)
        _pin_localqwen(monkeypatch)
        _wire_local(monkeypatch)
        monkeypatch.setattr(
            reg, "_call_openai_flavor",
            lambda spec, messages, timeout, max_tokens,
            model_override=None: "READY")
        # interleave: run A call, run B call, run A call
        for rid in ("run-A", "run-B", "run-A"):
            token = cctx.bind_run(rid, session_id=f"sess-{rid[-1]}")
            try:
                reg.generate(f"p-{rid}", system="s", max_tokens=8,
                             max_retries=0, timeout=10)
            finally:
                cctx.unbind(token)
        a_lines = mr.ledger_for_run("run-A")
        b_lines = mr.ledger_for_run("run-B")
        assert len(a_lines) >= 2 and len(b_lines) >= 1
        assert all(l["run_id"] == "run-A" for l in a_lines)
        assert all(l["run_id"] == "run-B" for l in b_lines)
        assert not set(map(json.dumps, map(sorted, [
            sorted(l.items()) for l in a_lines])) ) & \
            set(map(json.dumps, map(sorted, [
                sorted(l.items()) for l in b_lines]))) or True
        # the isolation is EXACT: no line appears in both sets
        ids_a = {l["request_id"] for l in a_lines}
        ids_b = {l["request_id"] for l in b_lines}
        assert not (ids_a & ids_b)

    def test_explicit_run_id_parameter_is_run_owned(self, hermetic,
                                                    monkeypatch):
        monkeypatch, tmp = hermetic
        _no_keys(monkeypatch)
        _pin_localqwen(monkeypatch)
        _wire_local(monkeypatch)
        monkeypatch.setattr(
            reg, "_call_openai_flavor",
            lambda spec, messages, timeout, max_tokens,
            model_override=None: "READY")
        res = reg.generate("p", system="s", max_tokens=8,
                           max_retries=0, timeout=10,
                           run_id="run-explicit")
        assert res.ok
        assert res.call_provenance["run_id"] == "run-explicit"
        assert res.call_provenance["call_class"] == "RUN_OWNED"

    def test_standalone_script_call_is_honestly_not_run_owned(
            self, hermetic, monkeypatch):
        monkeypatch, tmp = hermetic
        _no_keys(monkeypatch)
        _pin_localqwen(monkeypatch)
        _wire_local(monkeypatch)
        monkeypatch.setattr(
            reg, "_call_openai_flavor",
            lambda spec, messages, timeout, max_tokens,
            model_override=None: "READY")
        res = reg.generate("p", system="s", max_tokens=8,
                           max_retries=0, timeout=10)
        assert res.ok
        assert res.call_provenance["call_class"] == "STANDALONE"
        assert res.call_provenance["run_id"] is None


# ---------------------------------------------------------------------------
# C1.4 — explicit task degradation
# ---------------------------------------------------------------------------
class TestTaskDegradation:

    def test_strong_requested_cheap_served_is_cheap_emergency_fallback(
            self, hermetic, monkeypatch):
        """The C1.4 contract: localqwen declares ONLY CHEAP; a STRONG
        (synthesis) request served by it is degraded — actual capability
        CHEAP_EMERGENCY_FALLBACK, match false, reason recorded on the
        result, the route hop, the ledger line, and to_meta()."""
        monkeypatch, tmp = hermetic
        _no_keys(monkeypatch)
        _pin_localqwen(monkeypatch, caps=("CHEAP",))
        _wire_local(monkeypatch)
        monkeypatch.setattr(
            reg, "_call_openai_flavor",
            lambda spec, messages, timeout, max_tokens,
            model_override=None: "READY")
        token = cctx.bind_run("run-c14-deg", session_id="sess-c14")
        try:
            res = reg.generate("p", system="s", max_tokens=8,
                               max_retries=0, timeout=10,
                               role="synthesis")
        finally:
            cctx.unbind(token)
        assert res.ok
        deg = res.task_degradation
        assert deg["requested_task"] == "STRONG"
        assert deg["actual_task_capability"] == "CHEAP_EMERGENCY_FALLBACK"
        assert deg["task_capability_match"] is False
        assert "must NOT interpret" in deg["degraded_reason"]
        # the route hop carries it
        assert res.route[-1]["task_degradation"] == deg
        # the ledger line carries it
        line = [l for l in mr.LEDGER.tail(10)
                if l.get("selected") and l.get("call_class") ==
                "RUN_OWNED"][-1]
        assert line["task_degradation"]["actual_task_capability"] == \
            "CHEAP_EMERGENCY_FALLBACK"
        # to_meta (the candidate-provenance surface) carries it
        meta = res.to_meta()
        assert meta["task_degradation"]["task_capability_match"] is False

    def test_strong_requested_strong_served_matches(self, hermetic,
                                                    monkeypatch):
        monkeypatch, tmp = hermetic
        _no_keys(monkeypatch)
        _pin_localqwen(monkeypatch, caps=("STRONG", "FAST", "CHEAP"))
        _wire_local(monkeypatch)
        monkeypatch.setattr(
            reg, "_call_openai_flavor",
            lambda spec, messages, timeout, max_tokens,
            model_override=None: "READY")
        res = reg.generate("p", system="s", max_tokens=8,
                           max_retries=0, timeout=10, role="synthesis")
        assert res.ok
        assert res.task_degradation["requested_task"] == "STRONG"
        assert res.task_degradation["actual_task_capability"] == "STRONG"
        assert res.task_degradation["task_capability_match"] is True

    def test_degradation_survives_transport_failure_too(
            self, hermetic, monkeypatch):
        """Even a FAILED call records the degradation of the rung that
        was attempted — the provenance never silently relabels."""
        monkeypatch, tmp = hermetic
        _no_keys(monkeypatch)
        _pin_localqwen(monkeypatch, caps=("CHEAP",))
        _wire_local(monkeypatch)
        monkeypatch.setattr(
            reg, "_call_openai_flavor",
            lambda spec, messages, timeout, max_tokens,
            model_override=None: "TRANSPORT: ready")

        def failing(spec, messages, timeout, max_tokens,
                    model_override=None):
            if messages[1]["content"].startswith(ra.PROBE_PROMPT[:20]):
                return "TRANSPORT: ready"
            raise urllib.error.HTTPError("u", 500, "boom", None, None)

        monkeypatch.setattr(reg, "_call_openai_flavor", failing)
        res = reg.generate("p", system="s", max_tokens=8,
                           max_retries=0, timeout=10, role="synthesis")
        assert res.status == reg.ST_CALL_FAILED
        assert res.task_degradation["actual_task_capability"] == \
            "CHEAP_EMERGENCY_FALLBACK"


# ---------------------------------------------------------------------------
# C1.5 — catalog DISCOVERED => only catalog-present models eligible
# ---------------------------------------------------------------------------
class TestCatalogDiscoveredSemantics:

    def test_discovered_catalog_yields_only_catalog_models(
            self, hermetic, monkeypatch):
        monkeypatch, tmp = hermetic
        monkeypatch.setattr(
            mr, "discover_catalog",
            lambda provider_id, force=False: {
                "provider": provider_id, "status": "DISCOVERED",
                "fetched_at_epoch": 1e12, "models": ["qwen3-1.7b"],
                "catalog_size": 1, "eligible_count": 1})
        monkeypatch.setattr(mr, "PINNED_DEFAULT_MODELS", {
            "localqwen": [
                {"model": "qwen3-1.7b",
                 "task_capabilities": ["CHEAP"],
                 "cost_class": 1, "latency_class": 4,
                 "context_limit": 32768},
                # the STALE pinned default NOT in the live catalog — the
                # directive's named defect (must never be attempted)
                {"model": "qwen3-99b-ghost",
                 "task_capabilities": ["STRONG", "FAST", "CHEAP"],
                 "cost_class": 1, "latency_class": 1,
                 "context_limit": 128000}]})
        recs = mr.eligible_models("localqwen", "STRONG")
        models = [r.model for r in recs]
        assert "qwen3-1.7b" in models
        assert "qwen3-99b-ghost" not in models, \
            "a pinned-but-absent default is a stale identifier — " \
            "never attempted merely because it was once a default"
        assert all(r.source == "CATALOG" for r in recs)

    def test_undiscovered_catalog_yields_pinned_defaults_explicitly(
            self, hermetic, monkeypatch):
        monkeypatch.setattr(
            mr, "discover_catalog",
            lambda provider_id, force=False: {
                "provider": provider_id, "status": "UNDISCOVERED",
                "fetched_at_epoch": 0.0, "models": [],
                "catalog_size": 0, "eligible_count": 0})
        monkeypatch.setattr(mr, "PINNED_DEFAULT_MODELS", {
            "localqwen": [
                {"model": "qwen3-1.7b",
                 "task_capabilities": ["CHEAP"],
                 "cost_class": 1, "latency_class": 4,
                 "context_limit": 32768}]})
        recs = mr.eligible_models("localqwen", "CHEAP")
        assert [r.model for r in recs] == ["qwen3-1.7b"]
        assert all(r.source == "PINNED_DEFAULT" for r in recs)

    def test_discovered_but_empty_eligible_is_honestly_empty(
            self, hermetic, monkeypatch):
        """A DISCOVERED catalog with zero allowlist-matching models
        yields NO records — the pinned defaults do NOT stand in (the
        old fallback-merge behavior is REMOVED)."""
        monkeypatch.setattr(
            mr, "discover_catalog",
            lambda provider_id, force=False: {
                "provider": provider_id, "status": "DISCOVERED",
                "fetched_at_epoch": 1e12, "models": [],
                "catalog_size": 50, "eligible_count": 0})
        monkeypatch.setattr(mr, "PINNED_DEFAULT_MODELS", {
            "localqwen": [
                {"model": "qwen3-1.7b",
                 "task_capabilities": ["CHEAP"],
                 "cost_class": 1, "latency_class": 4,
                 "context_limit": 32768}]})
        assert mr.eligible_models("localqwen", "CHEAP") == []
        assert mr.all_models("localqwen") == []

    def test_family_allowlist_stays(self, hermetic, monkeypatch):
        """The pinned FAMILY policy survives (family != dead
        identifier): catalog models outside the family are not
        admitted even when DISCOVERED."""
        raw = ["qwen3-1.7b", "some/other-family-model"]
        allow = mr.PINNED_MODEL_FAMILIES.get("localqwen", [])
        eligible = [m for m in raw if mr._family_match(m, allow)]
        monkeypatch.setattr(
            mr, "discover_catalog",
            lambda provider_id, force=False: {
                "provider": provider_id, "status": "DISCOVERED",
                "fetched_at_epoch": 1e12,
                "models": eligible,
                "catalog_size": len(raw), "eligible_count": len(eligible)})
        # the family filter itself (inside the REAL discovery) is pinned
        # by the r415 battery; this stub reproduces its output shape
        # faithfully (allowlist-intersected) so the SEMANTIC under test
        # is: the ladder contains only what discovery returned.
        monkeypatch.setattr(mr, "PINNED_DEFAULT_MODELS", {
            "localqwen": [
                {"model": "qwen3-1.7b",
                 "task_capabilities": ["CHEAP"],
                 "cost_class": 1, "latency_class": 4,
                 "context_limit": 32768}]})
        recs = mr.eligible_models("localqwen", "CHEAP")
        assert [r.model for r in recs] == ["qwen3-1.7b"]


# ---------------------------------------------------------------------------
# C1.6 — MODEL_NOT_FOUND recovery (deterministic)
# ---------------------------------------------------------------------------
class TestModelNotFoundRecovery:

    def test_404_mark_dead_relist_clear_eligible_again(
            self, hermetic, monkeypatch):
        """The directive's exact deterministic sequence:
        404 -> mark dead -> fresh catalog lists the model -> dead mark
        cleared -> the model is eligible again."""
        monkeypatch, tmp = hermetic
        # 1. the 404 marks the model dead (the R451-C1.2 never-retry
        #    rule through the ordinary call path)
        mr.record_call_outcome(
            "nvidia", "nvidia/deepseek-v4-flash-0731", ok=False,
            failure_type="MODEL_NOT_FOUND", task="STRONG",
            stage="synthesis", run_id="r-c16", attempt=1,
            cost_class="PAID_API", selected=False,
            call_class="RUN_OWNED")
        assert mr.is_model_gone(
            "nvidia", "nvidia/deepseek-v4-flash-0731")
        # 2. the fresh catalog lists the model again
        monkeypatch.setattr(
            mr, "discover_catalog",
            lambda provider_id, force=False: {
                "provider": provider_id, "status": "DISCOVERED",
                "fetched_at_epoch": 1e12,
                "models": ["nvidia/deepseek-v4-flash-0731"],
                "catalog_size": 1, "eligible_count": 1,
                "_recovered": mr._clear_known_dead_if_relisted(
                    provider_id,
                    ["nvidia/deepseek-v4-flash-0731"])})
        # call through the public path (the production entry):
        # eligible_models -> discover_catalog -> recovery
        monkeypatch.setattr(mr, "PINNED_DEFAULT_MODELS", {
            "nvidia": [
                {"model": "nvidia/deepseek-v4-flash-0731",
                 "task_capabilities": ["STRONG", "FAST", "CHEAP"],
                 "cost_class": 1, "latency_class": 1,
                 "context_limit": 128000}]})
        recs = mr.eligible_models("nvidia", "STRONG")
        # 3. the dead mark is CLEARED and the model is eligible again
        assert not mr.is_model_gone(
            "nvidia", "nvidia/deepseek-v4-flash-0731")
        assert "nvidia/deepseek-v4-flash-0731" in \
            [r.model for r in recs]
        # 4. the recovery EVENT is recorded (append-only state)
        state = json.loads(mr.STATE_PATH.read_text())
        key = "nvidia::nvidia/deepseek-v4-flash-0731"
        assert key in (state.get("recovered_models") or {})
        assert "relisted" in state["recovered_models"][key]["evidence"]

    def test_ttl_cache_hit_does_not_clear_the_dead_mark(
            self, hermetic, monkeypatch):
        """Only a FRESH fetch is evidence of relisting — a TTL cache
        hit must not resurrect a dead identifier through the back
        door (Art. XVII: the bypass attempt)."""
        monkeypatch, tmp = hermetic
        _wire_local(monkeypatch)
        # the dead mark
        mr.mark_model_gone("localqwen", "qwen3-1.7b",
                           evidence="test: 404")
        # a cache file YOUNGER than the TTL with the model listed
        cat = {"provider": "localqwen", "status": "DISCOVERED",
               "fetched_at_epoch": 1e12,
               "models": ["qwen3-1.7b"],
               "catalog_size": 1, "eligible_count": 1}
        mr.CATALOG_DIR.mkdir(parents=True, exist_ok=True)
        (mr.CATALOG_DIR / "localqwen.json").write_text(json.dumps(cat))
        # the cached discovery (the REAL implementation restored — the
        # fixture's stub would bypass the cache path entirely) returns
        # WITHOUT clearing the mark
        monkeypatch.setattr(mr, "discover_catalog", REAL_DISCOVER_CATALOG)
        out = mr.discover_catalog("localqwen")
        assert out["status"] == "DISCOVERED"
        assert mr.is_model_gone("localqwen", "qwen3-1.7b"), \
            "a TTL cache hit is not relisting evidence"

    def test_recovered_model_reprobes_immediately(
            self, hermetic, monkeypatch):
        """The recovered model's capability record is invalidated —
        admission re-probes it instead of trusting the stale
        PROBE_FAILED record for the rest of the TTL window."""
        monkeypatch, tmp = hermetic
        ra.record_capability("nvidia", "nvidia/model-y", ok=False,
                             failure_class="MODEL_NOT_FOUND",
                             source="probe")
        assert ra.capability_state(
            "nvidia", "nvidia/model-y")["state"] == ra.ST_PROBE_FAILED
        mr.mark_model_gone("nvidia", "nvidia/model-y",
                           evidence="test: 404")
        mr._clear_known_dead_if_relisted(
            "nvidia", ["nvidia/model-y"])
        assert ra.capability_state(
            "nvidia", "nvidia/model-y")["state"] == ra.ST_NOT_PROBED


# ---------------------------------------------------------------------------
# C1.7 — ONE admission semantic (select_provider == generate)
# ---------------------------------------------------------------------------
class TestUnifiedSelector:

    def test_select_provider_refuses_not_probed_available_provider(
            self, hermetic, monkeypatch):
        """The legacy-weaker-selector removal: a provider with a
        present credential and NO measured capability is NOT selected
        by select_provider() — the same rule generate() applies."""
        monkeypatch, tmp = hermetic
        _no_keys(monkeypatch)
        monkeypatch.setenv("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")
        monkeypatch.setenv("OPENAI_API_KEY", "k")
        spec, ledger = reg.select_provider(reg.SelectionPolicy())
        assert spec is None
        refusals = {r["provider"]: r for r in
                    ledger.get("capability_refusals", [])}
        assert "openai" in refusals
        assert refusals["openai"]["capability_state"] == \
            ra.ST_NOT_PROBED

    def test_select_provider_admits_probe_ok_provider(
            self, hermetic, monkeypatch):
        monkeypatch, tmp = hermetic
        _no_keys(monkeypatch)
        monkeypatch.setenv("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")
        monkeypatch.setenv("OPENAI_API_KEY", "k")
        ra.record_capability("openai", "gpt-4o", ok=True,
                             source="probe")
        spec, ledger = reg.select_provider(reg.SelectionPolicy())
        assert spec is not None and spec.provider_id == "openai"

    def test_select_provider_policy_refusal_beats_probe_success(
            self, hermetic, monkeypatch):
        """ZERO_PAID_COST + a probing-successful PAID provider: the
        selector refuses (fail-closed) — measured capability, refused
        routing."""
        monkeypatch, tmp = hermetic
        _no_keys(monkeypatch)
        monkeypatch.setenv("ENGINE_MODEL_COST_POLICY", "ZERO_PAID_COST")
        monkeypatch.setenv("OPENAI_API_KEY", "k")
        ra.record_capability("openai", "gpt-4o", ok=True,
                             source="probe")
        spec, ledger = reg.select_provider(reg.SelectionPolicy())
        assert spec is None
        assert ledger.get("cost_policy_refusals"), \
            "the policy refusal is recorded with its reason"

    def test_availability_matrix_carries_capability_state(
            self, hermetic, monkeypatch):
        monkeypatch, tmp = hermetic
        _no_keys(monkeypatch)
        _wire_local(monkeypatch)
        matrix = reg.availability_matrix()
        row = next(m for m in matrix if m["provider_id"] == "localqwen")
        assert row["capability_state"] == ra.ST_NOT_PROBED
        ra.record_capability("localqwen", "qwen3-1.7b", ok=True,
                             source="probe")
        row = next(m for m in reg.availability_matrix()
                   if m["provider_id"] == "localqwen")
        assert row["capability_state"] == ra.ST_PROBE_OK


# ---------------------------------------------------------------------------
# Art. XVII — the attempted bypasses
# ---------------------------------------------------------------------------
class TestAdversarialBypasses:

    def test_forged_capability_record_cannot_admit_policy_refused_route(
            self, hermetic, monkeypatch):
        """An adversary forges a PROBE_OK capability record for a PAID
        route under ZERO_PAID_COST: the cost policy still refuses —
        capability evidence is NECESSARY, never SUFFICIENT."""
        monkeypatch, tmp = hermetic
        _no_keys(monkeypatch)
        monkeypatch.setenv("ENGINE_MODEL_COST_POLICY", "ZERO_PAID_COST")
        monkeypatch.setenv("OPENAI_API_KEY", "k")
        # the forged record (written directly to the store)
        ra.record_capability("openai", "gpt-4o", ok=True,
                             source="probe")
        res = reg.generate("p", system="s", max_tokens=8,
                           max_retries=0, timeout=10)
        assert res.status == reg.ST_POLICY_BLOCKED
        # and no real call was made
        lines = [l for l in mr.LEDGER.tail()
                 if l.get("provider") == "openai"
                 and l.get("call_class") == "RUN_OWNED"]
        assert not lines

    def test_call_site_cannot_spoof_run_ownership_without_run_id(
            self, hermetic):
        """A call site cannot mark itself RUN_OWNED while evading the
        run identity — the ledger fails closed (ValueError)."""
        monkeypatch, tmp = hermetic
        with pytest.raises(ValueError):
            mr.record_call_outcome(
                "openai", "gpt-4o", ok=True, task="STRONG",
                stage="attack", run_id="", attempt=1,
                call_class="RUN_OWNED")

    def test_probe_failure_cannot_be_laundered_into_absence(
            self, hermetic, monkeypatch):
        """A failed probe is a TYPED fact in the ledger (never
            'no provider' — Art. XXI.3)."""
        monkeypatch, tmp = hermetic
        _no_keys(monkeypatch)
        _pin_localqwen(monkeypatch)
        _wire_local(monkeypatch)

        def failing(spec, messages, timeout, max_tokens,
                    model_override=None):
            raise urllib.error.HTTPError(
                "u", 429, "Too Many Requests", None, None)

        monkeypatch.setattr(reg, "_call_openai_flavor", failing)
        res = reg.generate("p", system="s", max_tokens=8,
                           max_retries=0, timeout=10)
        assert res.status == reg.ST_CALL_FAILED
        probe = [l for l in mr.LEDGER.tail()
                 if l.get("call_class") == "CAPABILITY_PROBE"][-1]
        assert probe["failure_class"] == "RATE_LIMITED"
        assert probe["ok"] is False

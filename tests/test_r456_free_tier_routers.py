"""R456-A3 — the operator's free-tier router quartet: contract battery.

The operator directive (verbatim, the registration authority):
  "Use these to use free ai models like qwen 3.8, glm 5.3, deepseek,
   minimax etc. once tokens run out of one go to the next provider"

Contracts pinned here:
1. every router spec is LIVE-MEASURED before registration (the probe
   evidence is quoted in its policy_note — catalog presence alone is
   never admission evidence);
2. FREE_TIER_API is eligible under ZERO_PAID_COST ONLY by the recorded
   operator amendment (model_cost_policy v1.1.0) — PAID_API /
   ENVIRONMENT_GRANT / UNDECLARED stay refused;
3. the four accounts are DISTINCT economic domains (the rotation is
   genuine redundancy: one account's exhaustion cannot kill the others);
4. the Cloudflare browser-UA transport requirement rides every xkiro /
   apinex call (chat, probe, catalog);
5. the measured failure specimens classify to the cascade-advancing
   classes (CREDIT_EXHAUSTED / RATE_LIMITED — never AUTH_FAILURE), so
   token exhaustion ADVANCES the provider chain (the operator's
   rotation rule).
"""
import os
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine import llm_registry as reg  # noqa: E402
from discovery_fabric.engine import model_cost_policy as cp  # noqa: E402
from discovery_fabric.engine import model_routing as mr  # noqa: E402
from discovery_fabric.engine import provider_health as ph  # noqa: E402
from discovery_fabric.engine import transport_capability as tc  # noqa: E402

ROUTERS = ("unorouter", "xkiro", "apinex", "bai")


def _spec(pid):
    return reg._SPEC_BY_ID[pid]


# ---------------------------------------------------------------------------
# 1. registration + measured admission
# ---------------------------------------------------------------------------

class TestRegistration:

    def test_all_four_routers_registered(self):
        for pid in ROUTERS:
            assert pid in reg._SPEC_BY_ID, pid

    def test_every_router_declares_free_tier_basis(self):
        for pid in ROUTERS:
            assert _spec(pid).cost_basis == "FREE_TIER_API", pid

    def test_policy_notes_carry_measured_probe_evidence(self):
        # the probe-before-admit discipline: each note quotes a measured
        # completion (latency + model), not catalog presence
        for pid in ROUTERS:
            note = _spec(pid).policy_note
            assert "LIVE-MEASURED" in note, pid
            assert "PROBE_OK" in note, pid

    def test_strong_rungs_exist_on_three_routers(self):
        # unorouter (glm-5.3:free), xkiro (qwen3.8-max/minimax-m3),
        # apinex (deepseek-v4.1-flash) — bai is honestly FAST+CHEAP only
        strong = {"unorouter", "xkiro", "apinex"}
        for pid in strong:
            rungs = mr.PINNED_DEFAULT_MODELS.get(pid, [])
            assert any(mr.TASK_STRONG in r["task_capabilities"]
                       for r in rungs), pid
        for r in mr.PINNED_DEFAULT_MODELS.get("bai", []):
            assert mr.TASK_STRONG not in r["task_capabilities"]

    def test_family_allowlists_admit_only_free_answerers(self):
        # bai's allowlist must not admit its deposit-gated premium ids
        fam = mr.PINNED_MODEL_FAMILIES["bai"]
        assert any("__" not in p for p in fam)
        import re
        for premium in ("glm-5.3", "minimax-m3", "claude-opus-5",
                        "gpt-5.5"):
            assert not any(re.match(p, premium)
                           for p in fam), premium


# ---------------------------------------------------------------------------
# 2. the operator policy amendment
# ---------------------------------------------------------------------------

class TestPolicyAmendment:

    def test_free_tier_eligible_under_zero_paid(self, monkeypatch):
        monkeypatch.setenv("ENGINE_MODEL_COST_POLICY", "ZERO_PAID_COST")
        ok, _ = cp.provider_eligibility(_spec("unorouter"))
        assert ok is True

    def test_paid_still_refused_under_zero_paid(self, monkeypatch):
        monkeypatch.setenv("ENGINE_MODEL_COST_POLICY", "ZERO_PAID_COST")
        for pid in ("openrouter", "openai", "anthropic"):
            ok, _ = cp.provider_eligibility(_spec(pid))
            assert ok is False, pid

    def test_amendment_provenance_recorded(self):
        # Art. XXVII: the policy change carries its authority — the
        # operator directive quoted verbatim + the version bump
        src = open(cp.__file__).read()
        assert "Use these to use free ai models" in src
        assert cp.COST_POLICY_VERSION == "model_cost_policy/1.1.0"

    def test_localqwen_still_eligible(self, monkeypatch):
        monkeypatch.setenv("ENGINE_MODEL_COST_POLICY", "ZERO_PAID_COST")
        ok, _ = cp.provider_eligibility(_spec("localqwen"))
        assert ok is True


# ---------------------------------------------------------------------------
# 3. genuine account redundancy (the rotation's economic basis)
# ---------------------------------------------------------------------------

class TestAccountDomains:

    def test_four_distinct_owner_accounts(self):
        domains = {_spec(pid).account_domain for pid in ROUTERS}
        assert domains == {"OWNER_UNOROUTER_ACCOUNT",
                           "OWNER_XKIRO_ACCOUNT",
                           "OWNER_APINEX_ACCOUNT",
                           "OWNER_BAI_ACCOUNT"}

    def test_domains_in_closed_vocabulary(self):
        for pid in ROUTERS:
            assert _spec(pid).account_domain in tc.ACCOUNT_DOMAIN_VOCAB, \
                pid


# ---------------------------------------------------------------------------
# 4. the Cloudflare browser-UA transport requirement
# ---------------------------------------------------------------------------

class TestTransportHeaders:

    def test_xkiro_apinex_carry_browser_ua(self):
        for pid in ("xkiro", "apinex"):
            ua = (_spec(pid).extra_headers or {}).get("User-Agent", "")
            assert "Mozilla/5.0" in ua, pid

    def test_unorouter_bai_need_no_ua(self):
        # measured: the default urllib UA passes on their endpoints
        assert not _spec("unorouter").extra_headers
        assert not _spec("bai").extra_headers

    def test_ua_rides_the_openai_flavor_headers(self, monkeypatch):
        # transport-level: the merged header set the call would send
        captured = {}

        def fake_post(url, payload, headers, timeout):
            captured.update(headers)
            return {"choices": [{"message": {"content": "ok"}}]}

        monkeypatch.setattr(reg, "_post_json", fake_post)
        monkeypatch.setenv("XKIRO_API_KEY", "k")
        reg._call_openai_flavor(
            _spec("xkiro"),
            [{"role": "user", "content": "x"}], 10, 8)
        assert "Mozilla/5.0" in captured.get("User-Agent", "")
        assert captured.get("Authorization") == "Bearer k"

    def test_ua_rides_catalog_discovery(self, monkeypatch):
        captured = {}

        def fake_get(url, key, timeout=20, extra_headers=None):
            captured.update(extra_headers or {})
            return {"data": [{"id": "qwen/qwen3.8-max:free"}]}

        monkeypatch.setattr(mr, "_get_json", fake_get)
        monkeypatch.setattr(mr, "CATALOG_DIR",
                            Path(mr.CATALOG_DIR) / ".." / "tmp_probe_cat")
        monkeypatch.setenv("XKIRO_API_KEY", "k")
        out = mr.discover_catalog("xkiro", force=True)
        assert "Mozilla/5.0" in captured.get("User-Agent", "")
        assert out["status"] == "DISCOVERED"


# ---------------------------------------------------------------------------
# 5. the measured failure specimens classify to cascade-advancing
#    classes (the rotation rule)
# ---------------------------------------------------------------------------

class _FakeHTTPError(urllib.error.HTTPError):
    """An HTTPError carrying a prefetched body (the real one streams)."""

    def __init__(self, code, body):
        super().__init__("u", code, "reason", None, None)
        self._body = body.encode()

    def read(self, amt=None):
        b, self._body = self._body, b""
        return b


class TestFailureClassification:

    def test_unorouter_busy_pool_403_is_rate_limited(self):
        exc = _FakeHTTPError(403, "This model is busy right now (free "
                                  "providers hit their rate limit). "
                                  "Please try again in a little while, "
                                  "or switch to another model.")
        assert ph.classify_failure(exc) == ph.RATE_LIMITED

    def test_xkiro_deposit_403_is_credit_exhausted(self):
        exc = _FakeHTTPError(403, "This pay-as-you-go premium model "
                                  "requires real deposited balance — it "
                                  "is billed from your wallet")
        assert ph.classify_failure(exc) == ph.CREDIT_EXHAUSTED

    def test_bai_deposit_403_is_credit_exhausted(self):
        exc = _FakeHTTPError(403, '{"error":{"code":"access_denied",'
                                  '"message":"Access restricted. Deposit '
                                  'required to unlock premium models."}}')
        assert ph.classify_failure(exc) == ph.CREDIT_EXHAUSTED

    def test_bai_insufficient_balance_400_is_credit_exhausted(self):
        exc = _FakeHTTPError(400, '{"error":{"message":"credit '
                                  'insufficient balance: balance=0 '
                                  'required=2406"}}')
        assert ph.classify_failure(exc) == ph.CREDIT_EXHAUSTED

    def test_plain_403_still_auth_failure(self):
        # the pre-existing behavior is untouched: a body-less 403 (or
        # one without the measured wording) stays AUTH_FAILURE
        exc = _FakeHTTPError(403, "forbidden")
        assert ph.classify_failure(exc) == ph.AUTH_FAILURE

    def test_401_stays_auth_failure_even_with_wording(self):
        # 401 is always auth — the free-tier hints only soften 403/400
        exc = _FakeHTTPError(401, "deposit required")
        # body hints are checked inside the 401/403 branch for 403 only
        # per the amendment; 401 remains strictly auth
        got = ph.classify_failure(exc)
        assert got == ph.AUTH_FAILURE

    def test_runtime_error_body_path_credit(self):
        # the 200-body error envelope path (llm_registry raises
        # RuntimeError carrying the provider's message)
        err = RuntimeError("unorouter API error: credit insufficient "
                           "balance: balance=0 required=100")
        assert ph.classify_failure(err) == ph.CREDIT_EXHAUSTED

    def test_runtime_error_body_path_rate(self):
        err = RuntimeError("unorouter API error: free providers hit "
                           "their rate limit")
        assert ph.classify_failure(err) == ph.RATE_LIMITED


# ---------------------------------------------------------------------------
# 6. the capability gate now sees STRONG free routes (the A3 unblock)
# ---------------------------------------------------------------------------

class TestCapabilityUnblock:

    def test_strong_route_capability_ok_with_router_keys(
            self, monkeypatch, tmp_path):
        # the R455 gate: with a reachable STRONG rung the mirror must
        # report OK (not DEGRADED_ONLY) — the A3 capability floor is
        # unblocked by the operator's free-tier frontier access
        from discovery_fabric.engine import runtime_admission as ra
        for k in ("OPENROUTER_API_KEY", "NVIDIA_API_KEY",
                  "ANTHROPIC_API_KEY", "OPENAI_API_KEY",
                  "GEMINI_API_KEY", "QWEN_API_KEY",
                  "DEEPSEEK_API_KEY", "MISTRAL_API_KEY",
                  "ZAI_API_KEY", "TOKEN_ROUTER_API_KEY",
                  "LOCAL_QWEN_BASE_URL", "ENGINE_MODEL_COST_POLICY"):
            monkeypatch.delenv(k, raising=False)
        monkeypatch.setenv("UNOROUTER_API_KEY", "k")
        monkeypatch.setattr(mr, "STATE_PATH", tmp_path / "state.json")
        monkeypatch.setattr(mr, "LEDGER", mr.RoutingLedger(
            path=tmp_path / "ledger.jsonl"))
        monkeypatch.setattr(
            mr, "discover_catalog",
            lambda pid, force=False: {
                "provider": pid, "status": "UNDISCOVERED",
                "fetched_at_epoch": 0.0, "models": [],
                "catalog_size": 0, "eligible_count": 0})
        ra.set_state_path(tmp_path / "cap.json")
        out = reg.strong_route_capability()
        assert out["state"] == "OK", out
        strong = {r["provider"] for r in out["strong_rungs"]}
        assert "unorouter" in strong

    def test_gate_still_degraded_without_router_keys(
            self, monkeypatch, tmp_path):
        # hermetic: no router keys -> the free routers are unavailable;
        # with ONLY the CHEAP localqwen rung reachable the gate reads
        # DEGRADED_ONLY exactly as before (the R455 tripwire class;
        # tests never carry real credentials)
        from discovery_fabric.engine import runtime_admission as ra
        for k in list(os.environ):
            if k.endswith("_API_KEY"):
                monkeypatch.delenv(k, raising=False)
        monkeypatch.setenv("LOCAL_QWEN_BASE_URL",
                           "http://127.0.0.1:8790/v1/chat/completions")
        monkeypatch.setattr(mr, "STATE_PATH", tmp_path / "state.json")
        monkeypatch.setattr(mr, "LEDGER", mr.RoutingLedger(
            path=tmp_path / "ledger.jsonl"))
        monkeypatch.setattr(
            mr, "discover_catalog",
            lambda pid, force=False: {
                "provider": pid, "status": "UNDISCOVERED",
                "fetched_at_epoch": 0.0, "models": [],
                "catalog_size": 0, "eligible_count": 0})
        ra.set_state_path(tmp_path / "cap.json")
        out = reg.strong_route_capability()
        assert out["state"] == "DEGRADED_ONLY", out
        assert all(r["provider"] == "localqwen"
                   for r in out["degraded_rungs"])

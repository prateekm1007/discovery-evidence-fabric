"""R461 — the fifth free-tier router (bynara) + the newly-measured free
rungs: contract battery.

The operator directives (verbatim, the registration authorities):
  R456-A3 (the quartet): "Use these to use free ai models like qwen 3.8,
   glm 5.3, deepseek, minimax etc. once tokens run out of one go to the
   next provider"
  R461 (the fifth + the escalation resolution): "bynara (new router) —
   key valid  telegram joined"

Contracts pinned here:
1. bynara is LIVE-MEASURED before registration (post-owner-action
   probes; catalog presence alone is never admission evidence);
2. the Art. LXV escalation record exists, carries the owner action
   verbatim, and is RESOLVED (the account-entry gate answered);
3. the five accounts are DISTINCT economic domains (the rotation's
   economic basis — genuine redundancy);
4. bynara's family allowlist admits ONLY the -free family (premium
   ids never become rungs silently);
5. the measured bynara failure specimens classify to cascade-advancing
   classes (CREDIT_EXHAUSTED / RATE_LIMITED — never AUTH_FAILURE);
6. the newly-measured free rungs on the standing quartet are pinned
   (xkiro qwen3.5-plus, apinex deepseek-v4-pro + glm-5.3-flash);
7. bynara's honest tier: FAST+CHEAP rung only, no STRONG claim (the
   free-tier serving path is unmeasured on the structured protocol);
8. secret discipline: the R461 artifacts carry masked fingerprints
   only, never key values (BS-021).
"""
import json
import re
import urllib.error
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine import llm_registry as reg  # noqa: E402
from discovery_fabric.engine import model_cost_policy as cp  # noqa: E402
from discovery_fabric.engine import model_routing as mr  # noqa: E402
from discovery_fabric.engine import provider_health as ph  # noqa: E402
from discovery_fabric.engine import transport_capability as tc  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
ROUTERS = ("unorouter", "xkiro", "apinex", "bai", "bynara")


def _spec(pid):
    return reg._SPEC_BY_ID[pid]


# ---------------------------------------------------------------------------
# 1. registration + measured admission (the fifth router)
# ---------------------------------------------------------------------------

class TestRegistration:

    def test_bynara_registered_as_fifth_free_tier_router(self):
        assert "bynara" in reg._SPEC_BY_ID
        s = _spec("bynara")
        assert s.cost_basis == "FREE_TIER_API"
        assert s.env_var == "BYNARA_API_KEY"
        assert s.url == ("https://router.bynara.id/v1/chat/"
                         "completions")
        assert s.default_model == "tencent-hy3-free"

    def test_all_five_routers_registered(self):
        for pid in ROUTERS:
            assert pid in reg._SPEC_BY_ID, pid

    def test_policy_note_carries_post_owner_action_measurement(self):
        note = _spec("bynara").policy_note
        assert "LIVE-MEASURED" in note
        assert "PROBE_OK" in note
        assert "tencent-hy3-free" in note
        # the escalation story is quoted (Art. LXV closure)
        assert "telegram" in note

    def test_bynara_eligible_under_zero_paid(self):
        ok, note = cp.provider_eligibility(_spec("bynara"))
        assert ok is True, note

    def test_bynara_account_domain_distinct_from_quartet(self):
        d5 = {_spec(pid).account_domain for pid in ROUTERS}
        assert d5 == {"OWNER_UNOROUTER_ACCOUNT",
                      "OWNER_XKIRO_ACCOUNT",
                      "OWNER_APINEX_ACCOUNT",
                      "OWNER_BAI_ACCOUNT",
                      "OWNER_BYNARA_ACCOUNT"}
        for pid in ROUTERS:
            assert _spec(pid).account_domain in tc.ACCOUNT_DOMAIN_VOCAB, \
                pid

    def test_bynara_needs_no_browser_ua(self):
        # measured: the default urllib UA passes on router.bynara.id
        # (no Cloudflare browser-signature check, unlike xkiro/apinex)
        assert not _spec("bynara").extra_headers


# ---------------------------------------------------------------------------
# 2. the Art. LXV escalation record (owner action answered)
# ---------------------------------------------------------------------------

class TestEscalationRecord:

    def _record(self):
        p = REPO / "R461" / "BYNARA_OWNER_ACTION_ESCALATION.json"
        assert p.exists(), "the escalation record must exist"
        return json.loads(p.read_text())

    def test_owner_action_quoted_verbatim(self):
        rec = self._record()
        assert rec["the_owner_action"]["directive_verbatim"] == \
            "bynara (new router) — key valid  telegram joined"

    def test_gate_specimen_carried_verbatim(self):
        rec = self._record()
        assert "telegram_required" in \
            rec["the_gate"]["specimen_verbatim"]
        assert "relink" in rec["the_gate"]["specimen_verbatim"]

    def test_escalation_is_resolved_with_count(self):
        rec = self._record()
        assert rec["the_escalation"]["escalation_count"] == 1
        assert rec["the_owner_action"]["escalation_resolved_at"] == \
            "2026-09-15"
        # Art. LXV: recurrence re-opens at count 2, never idles silently
        assert rec["recurrence_protocol"][
            "escalation_count_if_reopened"] == 2

    def test_no_deposit_authorized(self):
        rec = self._record()
        residual = json.dumps(rec["the_resolution_measurement"])
        assert "ZERO_PAID_COST holds" in residual


# ---------------------------------------------------------------------------
# 3. the family allowlist admits only the -free family
# ---------------------------------------------------------------------------

class TestFamilyAllowlist:

    def test_bynara_allowlist_admits_the_measured_free_family(self):
        fam = mr.PINNED_MODEL_FAMILIES["bynara"]
        for mid in ("tencent-hy3-free", "glm-5.3-free",
                    "qwen3.8-flash-free", "mimo-v2.5-free",
                    "muse-spark-1.3-contributor-free"):
            assert any(re.match(p, mid) for p in fam), mid

    def test_bynara_premium_ids_never_admitted(self):
        fam = mr.PINNED_MODEL_FAMILIES["bynara"]
        # the measured catalog's premium ids (49-model catalog): none
        # of these may silently become rungs
        for premium in ("glm-5.3", "qwen3.8-max", "qwen3.8-flash",
                        "deepseek-v4.1-flash", "claude-opus-5",
                        "gpt-6-astra", "gemini-3.1-pro-high",
                        "minimax-m3", "kimi-k3", "mimo-v2.5",
                        "muse-spark-1.3"):
            assert not any(re.match(p, premium)
                           for p in fam), premium

    def test_bynara_pinned_default_is_the_measured_answerer(self):
        rungs = mr.PINNED_DEFAULT_MODELS["bynara"]
        assert [r["model"] for r in rungs] == ["tencent-hy3-free"]

    def test_bynara_honest_tier_no_strong_claim(self):
        for r in mr.PINNED_DEFAULT_MODELS["bynara"]:
            assert mr.TASK_STRONG not in r["task_capabilities"]
            assert mr.TASK_FAST in r["task_capabilities"]


# ---------------------------------------------------------------------------
# 4. the measured bynara failure specimens classify to
#    cascade-advancing classes (never AUTH_FAILURE)
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

    def test_bynara_plan_gate_403_is_credit_exhausted(self):
        exc = _FakeHTTPError(
            403, '{"error":{"type":"forbidden","message":"Your plan '
                 'does not include the requested model."}}')
        assert ph.classify_failure(exc) == ph.CREDIT_EXHAUSTED

    def test_bynara_insufficient_credits_402_is_credit_exhausted(self):
        exc = _FakeHTTPError(
            402, '{"error":{"type":"payment_required","message":'
                 '"Insufficient credits. Please top up your '
                 'balance."}}')
        assert ph.classify_failure(exc) == ph.CREDIT_EXHAUSTED

    def test_bynara_429_rate_limited_with_credit_wording(self):
        # the provider's own remedy: "try again in a few minutes" —
        # the rate-limit class (cooldown + advance) even though the
        # body mentions credits
        exc = _FakeHTTPError(
            429, '{"error":{"type":"rate_limited","message":'
                 '"Insufficient credits. Please top up your balance '
                 'and try again in a few minutes."}}')
        assert ph.classify_failure(exc) == ph.RATE_LIMITED

    def test_bynara_telegram_gate_403_never_auth_failure(self):
        # the account-entry specimen: the KEY is valid; the ACCOUNT
        # must act (join telegram + relink). Recurrence classifies to
        # the account-gate family, advances the cascade — never
        # AUTH_FAILURE (a valid key is not a failed key)
        exc = _FakeHTTPError(
            403, '{"error":{"type":"forbidden","message":'
                 '"telegram_required: Join the required Telegram '
                 'group/channel and relink at /settings to '
                 'continue."}}')
        assert ph.classify_failure(exc) == ph.CREDIT_EXHAUSTED

    def test_runtime_error_plan_gate_path(self):
        err = RuntimeError("bynara API error: Your plan does not "
                           "include the requested model.")
        assert ph.classify_failure(err) == ph.CREDIT_EXHAUSTED

    def test_plain_403_still_auth_failure(self):
        exc = _FakeHTTPError(403, "forbidden")
        assert ph.classify_failure(exc) == ph.AUTH_FAILURE

    def test_401_stays_auth_failure_even_with_wording(self):
        exc = _FakeHTTPError(401, "telegram_required")
        assert ph.classify_failure(exc) == ph.AUTH_FAILURE


# ---------------------------------------------------------------------------
# 5. the newly-measured free rungs on the standing quartet
# ---------------------------------------------------------------------------

class TestNewRungs:

    def test_xkiro_qwen35_plus_rung(self):
        rungs = {r["model"] for r in mr.PINNED_DEFAULT_MODELS["xkiro"]}
        assert "qwen/qwen3.5-plus:free" in rungs

    def test_apinex_deepseek_v4_pro_rung(self):
        rungs = {r["model"] for r in mr.PINNED_DEFAULT_MODELS["apinex"]}
        assert "free/deepseek-v4-pro-0813" in rungs
        assert "free/glm-5.3-flash" in rungs

    def test_apinex_deepseek_pro_family_pattern_matches(self):
        fam = mr.PINNED_MODEL_FAMILIES["apinex"]
        assert any(re.match(p, "free/deepseek-v4-pro-0813")
                   for p in fam)

    def test_strong_rungs_now_on_three_routers_plus_new_rungs(self):
        # unorouter/xkiro/apinex declare STRONG; bai and bynara stay
        # honestly FAST+CHEAP
        for pid in ("unorouter", "xkiro", "apinex"):
            rungs = mr.PINNED_DEFAULT_MODELS.get(pid, [])
            assert any(mr.TASK_STRONG in r["task_capabilities"]
                       for r in rungs), pid
        for pid in ("bai", "bynara"):
            for r in mr.PINNED_DEFAULT_MODELS.get(pid, []):
                assert mr.TASK_STRONG not in r["task_capabilities"], pid


# ---------------------------------------------------------------------------
# 6. secret discipline (BS-021): artifacts carry fingerprints, never keys
# ---------------------------------------------------------------------------

class TestSecretDiscipline:

    # distinctive MIDDLE substrings of the delivered key values — the
    # BS-021 rule allows masked fingerprints (6-char prefix + 4-char
    # suffix, the probe artifact's own format) but NEVER a key's
    # recoverable body
    KEY_MARKERS = ("d2vAl4mX5", "G1hkrHjoY34N", "c3643f65cf5a27b6b",
                   "b192726df7e00209325b", "ewjhuu4e2zm85")

    def test_r461_artifacts_carry_no_key_values(self):
        for name in ("PROBE_CATALOG.json", "PROBE_COMPLETIONS.json",
                     "BYNARA_OWNER_ACTION_ESCALATION.json"):
            p = REPO / "R461" / name
            if not p.exists():
                continue
            text = p.read_text()
            for marker in self.KEY_MARKERS:
                assert marker not in text, (name, marker)

    def test_registration_sources_carry_no_key_values(self):
        for rel in ("discovery_fabric/engine/llm_registry.py",
                    "discovery_fabric/engine/model_routing.py",
                    "discovery_fabric/engine/provider_health.py",
                    "discovery_fabric/engine/transport_capability.py",
                    "scripts/r456_space_deploy.py"):
            text = (REPO / rel).read_text()
            for marker in self.KEY_MARKERS:
                assert marker not in text, (rel, marker)

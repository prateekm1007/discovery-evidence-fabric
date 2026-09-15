"""R463 — the seventh free-tier router CANDIDATE (aerolink.lat), met by
probe-before-admit and refused at the measured ACCOUNT-PLAN GATE:
contract battery.

The operator delivery (verbatim, key body redacted — BS-021):
  "https://aerolink.lat/dashboard/api-keys: aero_l...lon0"
  (delivered 2026-09-15 together with the re-provisioned HF_TOKEN —
  the R462 unblock action 2)

Contracts pinned here:
1. the probe artifact carries the MEASURED gate: all 4 catalog models
   403 permission_error (the account-plan specimen), the bogus-key
   401 differential on the SERVING endpoint (the key PROVEN valid —
   unlike tokenharbor, where validity was unmeasurable), the public
   catalog control, the UA gate (CF 1010 on Python-urllib), the
   Anthropic-dialect control, the admission refusal (probe-before-
   admit held — no registration), and the API-base discovery
   provenance (capi.aerolink.lat — externally sourced, never guessed);
2. the account-plan-gate specimen classifies CREDIT_EXHAUSTED (the
   newly-registered wording: 'free starter access' / 'upgrade your
   plan' / 'add paid balance') — never AUTH_FAILURE for a PROVEN-valid
   key, never the cooldown ladder;
3. aerolink is NOT registered (no ProviderSpec, no account domain — a
   guessed default rung would manufacture knowledge, Art. VI /
   XXVII), tokenharbor remains unregistered (the R462 state), and the
   five-router registration is untouched;
4. the Art. LXV escalation record is OPEN (count 1), carries the
   specimen verbatim, the redacted owner delivery, the pay-or-park-
   or-wait unblock path under ZERO_PAID_COST, and the recurrence
   protocol (count 2 if reopened);
5. the §5 scrub guard catches the new vocabulary (aerolink; the
   CREDIT_EXHAUSTED class name);
6. the HF Space secrets artifact records the sixth and seventh keys
   as SET with masked fingerprints only (the R462 unblock resolved);
7. secret discipline: the R463 artifacts carry masked fingerprints
   only, never either key's value (BS-021).
"""
import json
import urllib.error
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine import llm_registry as reg      # noqa: E402
from discovery_fabric.engine import provider_health as ph     # noqa: E402
from discovery_fabric.engine import transport_capability as tc  # noqa: E402
from toscanini.conversational import transport_invisibility as ti  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
THE_FIVE_ROUTERS = ("unorouter", "xkiro", "apinex", "bai", "bynara")

# the measured specimen body, verbatim from R463/PROBE_CATALOG.json
SPECIMEN_BODY = (
    '{"error":{"message":"Free Starter access is currently '
    'unavailable. Please upgrade your plan or add paid balance to '
    'continue using the service.","type":"permission_error"},'
    '"type":"error"}')


class _FakeHTTPError(urllib.error.HTTPError):
    """An HTTPError carrying a prefetched body (the real one streams)."""

    def __init__(self, code, body):
        super().__init__("u", code, "reason", None, None)
        self._body = body.encode()

    def read(self, amt=None):
        b, self._body = self._body, b""
        return b


def _probe_catalog():
    p = REPO / "R463" / "PROBE_CATALOG.json"
    assert p.exists(), "the R463 probe artifact must exist"
    return json.loads(p.read_text())


# ---------------------------------------------------------------------------
# 1. the measured gate (the probe artifact's own contracts)
# ---------------------------------------------------------------------------

class TestProbeArtifact:

    def test_key_recorded_as_fingerprint_only(self):
        k = _probe_catalog()["key"]
        assert k["present"] is True
        assert k["fingerprint"] == "aero_l...lon0"
        assert k["value"] == "<never recorded>"

    def test_the_catalog_measured_200_with_four_models(self):
        cat = _probe_catalog()
        assert cat["the_catalog"]["status"] == 200
        assert cat["the_catalog"]["model_count"] == 4
        assert sorted(cat["the_catalog"]["model_ids_verbatim"]) == [
            "claude-opus-4-7", "claude-opus-5",
            "claude-sonnet-4-6", "claude-sonnet-5"]

    def test_all_catalog_models_measured_403_plan_gate(self):
        cat = _probe_catalog()
        gate = cat["the_measured_gate"]
        assert gate["all_catalog_models_gated"] is True
        assert len(gate["measured_on_models"]) == 4
        v = gate["typed_specimen_verbatim"]
        assert "Free Starter access is currently unavailable" in v
        assert "upgrade your plan or add paid balance" in v

    def test_the_bogus_key_differential_proves_key_validity(self):
        # the differential ran on the SERVING endpoint: bogus -> 401
        # authentication_error while the real key answers the 403 plan
        # gate — auth is evaluated BEFORE the plan gate, so the
        # delivered key PASSED authentication (PROVEN valid, measured)
        cat = _probe_catalog()
        bogus = [p for p in cat["probes"]
                 if "bogus" in p["key"]
                 and p["endpoint"] == "/v1/messages"]
        assert len(bogus) == 1
        assert bogus[0]["status"] == 401
        assert bogus[0]["typed_gate"]["error_type"] == \
            "authentication_error"
        assert "PROVEN VALID" in cat["the_measured_gate"]["auth_ordering"]

    def test_the_catalog_endpoint_is_public(self):
        # the catalog answers 200 even for a bogus key — no auth check
        # there; the auth ordering is only measurable on /v1/messages
        cat = _probe_catalog()
        bogus_catalog = [p for p in cat["probes"]
                         if "bogus" in p["key"]
                         and p["endpoint"] == "/v1/models"]
        assert len(bogus_catalog) == 1
        assert bogus_catalog[0]["status"] == 200

    def test_the_ua_gate_measured_cf_1010(self):
        cat = _probe_catalog()
        plain = [p for p in cat["probes"] if p.get("ua") == "plain-urllib"]
        assert len(plain) == 1
        assert plain[0]["status"] == 403
        assert "1010" in (plain[0].get("note") or "")
        assert "xkiro/apinex extra_headers remedy" in \
            cat["the_measured_gate"]["ua_discipline"]

    def test_the_dialect_control_anthropic_only(self):
        cat = _probe_catalog()
        dialect = [p for p in cat["probes"]
                   if p["endpoint"] == "/v1/chat/completions"]
        assert len(dialect) == 1
        assert dialect[0]["status"] == 404
        assert "Anthropic Messages ONLY" in \
            cat["the_measured_gate"]["dialect"]

    def test_the_region_is_not_gated(self):
        assert "NOT gated" in \
            _probe_catalog()["the_measured_gate"]["region"]

    def test_admission_refused_in_the_artifact(self):
        decision = _probe_catalog()["admission_decision"]
        assert decision.startswith("NOT ADMITTED")
        assert "probe-before-admit" in decision
        assert "Art. VI" in decision  # no guessed default rung

    def test_api_base_discovery_provenance_recorded(self):
        # Art. VI — the base URL is DISCOVERED with cited external
        # provenance (the claude-code-free provider table), never guessed
        disc = _probe_catalog()["api_base_discovery"]
        assert disc["api_base"] == "https://capi.aerolink.lat"
        assert "EXTERNAL" in disc["provenance"]
        assert "claude-code-free" in disc["provenance"]
        assert "never guessed" in disc["provenance"]


# ---------------------------------------------------------------------------
# 2. the account-plan-gate classification (the provider-agnostic fix)
# ---------------------------------------------------------------------------

class TestPlanGateClassification:

    def test_measured_specimen_classifies_credit_exhausted(self):
        exc = _FakeHTTPError(403, SPECIMEN_BODY)
        assert ph.classify_failure(exc) == ph.CREDIT_EXHAUSTED

    def test_each_registered_wording_classifies_credit_exhausted(self):
        for wording in ("Free Starter access is currently unavailable",
                        "Please upgrade your plan to continue",
                        "add paid balance to continue using the service"):
            assert ph.classify_failure(
                _FakeHTTPError(403, wording)) == ph.CREDIT_EXHAUSTED, \
                wording

    def test_http_status_path_classifies_credit_exhausted(self):
        err = RuntimeError("HTTP Error 403: Forbidden")
        assert ph.classify_failure(
            err, http_status=403,
            body_snippet=("Free Starter access is currently "
                          "unavailable.")) == ph.CREDIT_EXHAUSTED

    def test_plain_403_still_auth_failure(self):
        exc = _FakeHTTPError(403, "forbidden")
        assert ph.classify_failure(exc) == ph.AUTH_FAILURE

    def test_401_stays_auth_even_with_plan_wording(self):
        # 401 stays strictly AUTH: a failed key is a failed key
        # whatever the body says (the standing R456-A3 discipline)
        exc = _FakeHTTPError(401, "upgrade your plan or add paid balance")
        assert ph.classify_failure(exc) == ph.AUTH_FAILURE

    def test_region_gate_beats_plan_gate_wording(self):
        # the R462 ordering discipline: the region class checks FIRST
        both = ('{"error":{"message":"API access from your region is '
                'not available. Free Starter access is currently '
                'unavailable.","code":"region_blocked"}}')
        assert ph.classify_failure(
            _FakeHTTPError(403, both)) == ph.REGION_NOT_SERVED

    def test_standing_specimens_still_classify_unchanged(self):
        # the R456-A3/R461 measured specimens are NOT reclassified by
        # the R463 additions (an extension, never a reclassification)
        assert ph.classify_failure(_FakeHTTPError(
            403, "Deposit required to unlock premium models")) == \
            ph.CREDIT_EXHAUSTED
        assert ph.classify_failure(_FakeHTTPError(
            403, "Your plan does not include the requested model.")) == \
            ph.CREDIT_EXHAUSTED
        assert ph.classify_failure(_FakeHTTPError(
            403, "This model is busy right now (free providers hit "
                 "their rate limit).")) == ph.RATE_LIMITED

    def test_plan_gate_never_enters_cooldown(self):
        # cooldown is the RATE_LIMITED remedy only: an account-plan
        # gate is not waited out (the R461 discipline — the fix is at
        # the provider's billing page, not the clock)
        book = ph.ProviderHealthBook()
        book.record_failure("aerolink", ph.CREDIT_EXHAUSTED,
                            purpose="probe", model="claude-sonnet-5",
                            error="403 permission_error")
        assert book.last_failure_type("aerolink") == ph.CREDIT_EXHAUSTED
        assert book.in_cooldown("aerolink") is False


# ---------------------------------------------------------------------------
# 3. NO registration (probe-before-admit held)
# ---------------------------------------------------------------------------

class TestNoRegistration:

    def test_aerolink_not_registered(self):
        assert "aerolink" not in reg._SPEC_BY_ID

    def test_no_aerolink_account_domain(self):
        assert "OWNER_AEROLINK_ACCOUNT" not in tc.ACCOUNT_DOMAIN_VOCAB

    def test_tokenharbor_remains_unregistered(self):
        # the R462 state is preserved (admission still deferred)
        assert "tokenharbor" not in reg._SPEC_BY_ID
        assert "OWNER_TOKENHARBOR_ACCOUNT" not in tc.ACCOUNT_DOMAIN_VOCAB

    def test_the_five_router_registration_untouched(self):
        for pid in THE_FIVE_ROUTERS:
            assert pid in reg._SPEC_BY_ID, pid
        domains = {reg._SPEC_BY_ID[p].account_domain
                   for p in THE_FIVE_ROUTERS}
        assert domains == {"OWNER_UNOROUTER_ACCOUNT",
                           "OWNER_XKIRO_ACCOUNT",
                           "OWNER_APINEX_ACCOUNT",
                           "OWNER_BAI_ACCOUNT",
                           "OWNER_BYNARA_ACCOUNT"}


# ---------------------------------------------------------------------------
# 4. the Art. LXV escalation record (OPEN — count 1)
# ---------------------------------------------------------------------------

class TestEscalationRecord:

    def _record(self):
        p = REPO / "R463" / "AEROLINK_OWNER_ESCALATION.json"
        assert p.exists(), "the escalation record must exist"
        return json.loads(p.read_text())

    def test_gate_specimen_carried_verbatim(self):
        rec = self._record()
        v = rec["the_gate"]["specimen_verbatim"]
        assert "Free Starter access is currently unavailable" in v
        assert "upgrade your plan or add paid balance" in v

    def test_typed_class_is_credit_exhausted_family(self):
        rec = self._record()
        assert "CREDIT_EXHAUSTED" in rec["the_gate"]["typed_class"]
        assert "never AUTH_FAILURE" in rec["the_gate"]["typed_class"]

    def test_key_validity_is_measured_not_assumed(self):
        rec = self._record()
        assert "PROVEN VALID" in rec["the_gate"]["key_validity"]
        assert "401" in rec["the_gate"]["key_validity"]

    def test_escalation_is_OPEN_with_count_1(self):
        rec = self._record()
        assert rec["the_escalation"]["escalation_count"] == 1
        # the honest OPEN state: no resolution is claimed anywhere
        assert "escalation_resolved_at" not in \
            rec.get("the_owner_delivery", {})
        assert "the_resolution_measurement" not in rec

    def test_owner_delivery_redacted_to_fingerprint(self):
        rec = self._record()
        v = rec["the_owner_delivery"]["directive_verbatim"]
        assert "aero_l...lon0" in v
        assert "BS-021" in v  # the redaction is explicit, never silent
        # the HF_TOKEN re-provision is part of the same delivery record
        assert "HF_TOKEN" in v

    def test_unblock_path_is_pay_or_park_or_wait(self):
        rec = self._record()
        u = json.dumps(rec["what_unblocks"])
        assert "ZERO_PAID_COST" in u
        assert "pay_or_park" in u
        assert "wait_and_re_prove" in u
        # the machine NEVER takes the wallet decision (Art. XXXIII)
        assert "never" in rec["what_unblocks"][
            "owner_action_1_pay_or_park"]

    def test_this_round_is_not_delivery_blocked(self):
        rec = self._record()
        assert "NOT delivery-blocked" in rec["what_unblocks"][
            "not_a_blocker_for_delivery"]

    def test_recurrence_protocol_count_2(self):
        rec = self._record()
        assert rec["recurrence_protocol"][
            "escalation_count_if_reopened"] == 2


# ---------------------------------------------------------------------------
# 5. the §5 scrub guard catches the new vocabulary
# ---------------------------------------------------------------------------

class TestScrubGuardExtensions:

    def test_aerolink_provider_id_is_a_violation(self):
        v = ti.transport_detail_violations(
            "aerolink returned HTTP 403")
        assert "provider-id-in-product-surface" in v
        assert "http-error-code-in-product-surface" in v

    def test_credits_exhausted_class_name_is_a_violation(self):
        v = ti.transport_detail_violations("failed: CREDIT_EXHAUSTED")
        assert "failure-class-in-product-surface" in v

    def test_standing_provider_ids_still_violations(self):
        for pid in ("tokenharbor", "bynara", "unorouter"):
            v = ti.transport_detail_violations(f"{pid} is busy")
            assert "provider-id-in-product-surface" in v, pid

    def test_directive_sentences_still_clean(self):
        assert ti.transport_detail_violations(
            "I continued using another verified reasoning route.") == []
        assert ti.transport_detail_violations(
            "The requested test could not be completed.") == []


# ---------------------------------------------------------------------------
# 6. the HF Space secrets artifact (the R462 unblock resolved)
# ---------------------------------------------------------------------------

class TestSpaceSecretsArtifact:

    def _secrets(self):
        p = REPO / "R463" / "HF_SPACE_SECRETS.json"
        assert p.exists(), "the secrets artifact must exist"
        return json.loads(p.read_text())

    def test_both_new_keys_recorded_set(self):
        s = self._secrets()["secrets"]
        assert set(s) == {"TOKENHARBOR_API_KEY", "AEROLINK_API_KEY"}
        for var, entry in s.items():
            assert entry["set"] is True, var
            assert entry["value"] == "<never recorded>", var

    def test_fingerprints_masked_only(self):
        s = self._secrets()["secrets"]
        assert s["TOKENHARBOR_API_KEY"]["key_fingerprint"] == \
            "thk_li...sEVu"
        assert s["AEROLINK_API_KEY"]["key_fingerprint"] == "aero_l...lon0"

    def test_the_artifact_names_the_space_and_inertness(self):
        art = self._secrets()
        assert art["space"] == "prateekm1/toscanini-prod-validation"
        assert "INERT" in art["note"]

    def test_deploy_driver_wires_the_extended_set(self):
        # the standing driver re-wires all seven keys when present in
        # the environment (the operator's never-insert-again persistence)
        src = (REPO / "scripts" / "r456_space_deploy.py").read_text()
        for var in ("UNOROUTER_API_KEY", "XKIRO_API_KEY",
                    "APINEX_API_KEY", "BAI_API_KEY", "BYNARA_API_KEY",
                    "TOKENHARBOR_API_KEY", "AEROLINK_API_KEY"):
            assert var in src, var


# ---------------------------------------------------------------------------
# 7. secret discipline (BS-021): fingerprints only, never key values
# ---------------------------------------------------------------------------

class TestSecretDiscipline:

    # distinctive MIDDLE substrings of the delivered keys — the BS-021
    # rule allows masked fingerprints (6-char prefix + 4-char suffix)
    # but NEVER a key's recoverable body
    AEROLINK_KEY_MARKER = "sYOlp64FY6pj3awNcf"
    TOKENHARBOR_KEY_MARKER = "6ymQG662YEmKKmiXMw"

    def test_r463_artifacts_carry_no_key_values(self):
        for name in ("PROBE_CATALOG.json",
                     "AEROLINK_OWNER_ESCALATION.json",
                     "HF_SPACE_SECRETS.json",
                     "R463_ROUND_RECORD.json"):
            p = REPO / "R463" / name
            if not p.exists():
                continue
            text = p.read_text()
            assert self.AEROLINK_KEY_MARKER not in text, name
            assert self.TOKENHARBOR_KEY_MARKER not in text, name

    def test_round_sources_carry_no_key_values(self):
        for rel in ("scripts/r463_probe_aerolink.py",
                    "scripts/r463_hf_secrets.py",
                    "scripts/r456_space_deploy.py",
                    "discovery_fabric/engine/provider_health.py",
                    "toscanini/conversational/transport_invisibility.py"):
            text = (REPO / rel).read_text()
            assert self.AEROLINK_KEY_MARKER not in text, rel
            assert self.TOKENHARBOR_KEY_MARKER not in text, rel

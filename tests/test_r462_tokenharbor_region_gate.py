"""R462 — the sixth free-tier router CANDIDATE (tokenharbor.ai), met by
probe-before-admit and refused at the measured REGION GATE: contract
battery.

The operator delivery (verbatim, key body redacted — BS-021):
  "https://tokenharbor.ai/dashboard/api-keys: thk_li...sEVu"

Contracts pinned here:
1. the probe artifact carries the MEASURED gate: every endpoint 403
   region_blocked, the pre-auth differential control, UA independence,
   the admission refusal (probe-before-admit held — no registration);
2. the REGION_NOT_SERVED failure class exists, classifies the measured
   specimen (never AUTH_FAILURE — the key is not measured failed),
   and is PERMANENT (never a transient-probe class);
3. tokenharbor is NOT registered (no ProviderSpec, no account domain —
   a guessed default rung would manufacture knowledge, Art. VI /
   XXVII) and the five-router registration is untouched;
4. the Art. LXV escalation record is OPEN (count 1), carries the
   specimen verbatim, the redacted owner delivery, the unblock path,
   and the recurrence protocol (count 2 if the Space side also blocks);
5. the §5 scrub guard catches the new vocabulary (tokenharbor,
   bynara — the disclosed R461 gap — REGION_NOT_SERVED, and the
   disclosed AUTH_FAILURE typo fix);
6. secret discipline: the R462 artifacts carry a masked fingerprint
   only, never the key value (BS-021).
"""
import json
import urllib.error
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine import llm_registry as reg      # noqa: E402
from discovery_fabric.engine import provider_health as ph     # noqa: E402
from discovery_fabric.engine import runtime_admission as ra   # noqa: E402
from discovery_fabric.engine import transport_capability as tc  # noqa: E402
from toscanini.conversational import transport_invisibility as ti  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
THE_FIVE_ROUTERS = ("unorouter", "xkiro", "apinex", "bai", "bynara")

# the measured specimen body, verbatim from R462/PROBE_CATALOG.json
SPECIMEN_BODY = (
    '{"error":{"message":"API access from your region is not '
    'available. Token Harbor cannot serve requests from regions under '
    'US sanctions or export controls, Mainland China, Hong Kong and '
    'Macau, or regions our AI provider (Anthropic) does not support. '
    'If you are using a VPN or proxy, please turn it off and try '
    'again \\u2014 we can only see the country your connection exits '
    'from, not where you are. If you believe this is in error, '
    'contact support@tokenharbor.ai.","type":"region_blocked",'
    '"code":"region_blocked"}}')


class _FakeHTTPError(urllib.error.HTTPError):
    """An HTTPError carrying a prefetched body (the real one streams)."""

    def __init__(self, code, body):
        super().__init__("u", code, "reason", None, None)
        self._body = body.encode()

    def read(self, amt=None):
        b, self._body = self._body, b""
        return b


def _probe_catalog():
    p = REPO / "R462" / "PROBE_CATALOG.json"
    assert p.exists(), "the R462 probe artifact must exist"
    return json.loads(p.read_text())


# ---------------------------------------------------------------------------
# 1. the measured gate (the probe artifact's own contracts)
# ---------------------------------------------------------------------------

class TestProbeArtifact:

    def test_key_recorded_as_fingerprint_only(self):
        k = _probe_catalog()["key"]
        assert k["present"] is True
        assert k["fingerprint"] == "thk_li...sEVu"
        assert k["value"] == "<never recorded>"

    def test_every_primary_probe_measured_403_region_blocked(self):
        cat = _probe_catalog()
        primary = [p for p in cat["probes"]
                   if p["base"] == "https://tokenharbor.ai/v1"]
        assert len(primary) == 4  # chrome + plain + bogus + chat
        for p in primary:
            assert p["status"] == 403
            assert p["typed_gate"]["error_code"] == "region_blocked"

    def test_the_pre_auth_differential_control(self):
        cat = _probe_catalog()
        bogus = [p for p in cat["probes"] if "bogus" in p["key"]]
        assert len(bogus) == 1
        assert bogus[0]["status"] == 403
        assert bogus[0]["typed_gate"]["error_code"] == "region_blocked"
        assert "PRE-AUTH" in cat["the_typed_gate"]["auth_ordering"]
        assert "UNMEASURABLE" in cat["the_typed_gate"]["auth_ordering"]

    def test_ua_independence_measured(self):
        assert _probe_catalog()["the_typed_gate"]["ua_independent"] is True

    def test_admission_refused_in_the_artifact(self):
        decision = _probe_catalog()["admission_decision"]
        assert decision.startswith("NOT ADMITTED")
        assert "probe-before-admit" in decision
        assert "Art. VI" in decision  # no guessed default rung

    def test_specimen_verbatim_carried(self):
        verbatim = _probe_catalog()["the_typed_gate"]["specimen_verbatim"]
        assert "API access from your region is not available" in verbatim
        assert "US sanctions or export controls" in verbatim


# ---------------------------------------------------------------------------
# 2. the REGION_NOT_SERVED failure class (the provider-agnostic fix)
# ---------------------------------------------------------------------------

class TestRegionNotServedClassification:

    def test_class_registered_in_failure_types(self):
        assert ph.REGION_NOT_SERVED == "REGION_NOT_SERVED"
        assert ph.REGION_NOT_SERVED in ph.FAILURE_TYPES

    def test_measured_specimen_classifies_region_not_served(self):
        exc = _FakeHTTPError(403, SPECIMEN_BODY)
        assert ph.classify_failure(exc) == ph.REGION_NOT_SERVED

    def test_the_class_is_connection_typed_not_key_typed(self):
        # the bogus-key differential: the IDENTICAL body (what a blocked
        # egress answers whatever the key) classifies identically — the
        # class names the refused CONNECTION, never a failed key
        exc = _FakeHTTPError(403, SPECIMEN_BODY)
        assert ph.classify_failure(exc) == ph.REGION_NOT_SERVED

    def test_http_status_path_classifies_region_not_served(self):
        err = RuntimeError("HTTP Error 403: Forbidden")
        assert ph.classify_failure(
            err, http_status=403,
            body_snippet=("region_blocked: API access from your region "
                          "is not available.")) == ph.REGION_NOT_SERVED

    def test_plain_403_still_auth_failure(self):
        exc = _FakeHTTPError(403, "forbidden")
        assert ph.classify_failure(exc) == ph.AUTH_FAILURE

    def test_401_stays_auth_even_with_region_wording(self):
        exc = _FakeHTTPError(401, "region_blocked")
        assert ph.classify_failure(exc) == ph.AUTH_FAILURE

    def test_region_gate_beats_account_gate_wording(self):
        # a body carrying BOTH region and account-gate wording names the
        # region first (the provider's own typed code is unambiguous)
        both = ('{"error":{"message":"API access from your region is '
                'not available. telegram_required","code":'
                '"region_blocked"}}')
        assert ph.classify_failure(
            _FakeHTTPError(403, both)) == ph.REGION_NOT_SERVED

    def test_class_is_permanent_never_transient(self):
        # runtime_admission: permanent classes are never probe-retried
        # within a walk — a region gate answers identically on retry
        assert ph.REGION_NOT_SERVED not in ra.TRANSIENT_PROBE_CLASSES

    def test_book_records_the_class_without_cooldown(self):
        book = ph.ProviderHealthBook()
        book.record_failure("tokenharbor", ph.REGION_NOT_SERVED,
                            purpose="probe", model="unknown",
                            error="403 region_blocked")
        assert book.last_failure_type("tokenharbor") == \
            ph.REGION_NOT_SERVED
        assert book.in_cooldown("tokenharbor") is False


# ---------------------------------------------------------------------------
# 3. NO registration (probe-before-admit held)
# ---------------------------------------------------------------------------

class TestNoRegistration:

    def test_tokenharbor_not_registered(self):
        assert "tokenharbor" not in reg._SPEC_BY_ID

    def test_no_tokenharbor_account_domain(self):
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
        p = REPO / "R462" / "TOKENHARBOR_OWNER_ESCALATION.json"
        assert p.exists(), "the escalation record must exist"
        return json.loads(p.read_text())

    def test_gate_specimen_carried_verbatim(self):
        rec = self._record()
        v = rec["the_gate"]["specimen_verbatim"]
        assert "API access from your region is not available" in v
        assert "US sanctions or export controls" in v

    def test_typed_class_is_region_not_served(self):
        rec = self._record()
        assert "REGION_NOT_SERVED" in rec["the_gate"]["typed_class"]
        assert "never AUTH_FAILURE" in rec["the_gate"]["typed_class"]

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
        assert "thk_li...sEVu" in v
        assert "BS-021" in v  # the redaction is explicit, never silent

    def test_unblock_path_names_hf_token(self):
        rec = self._record()
        assert "HF_TOKEN" in json.dumps(rec["what_unblocks"])
        assert "Space" in json.dumps(rec["what_unblocks"])

    def test_recurrence_protocol_count_2(self):
        rec = self._record()
        assert rec["recurrence_protocol"][
            "escalation_count_if_reopened"] == 2


# ---------------------------------------------------------------------------
# 5. the §5 scrub guard catches the new vocabulary
# ---------------------------------------------------------------------------

class TestScrubGuardExtensions:

    def test_tokenharbor_provider_id_is_a_violation(self):
        v = ti.transport_detail_violations(
            "tokenharbor returned HTTP 403")
        assert "provider-id-in-product-surface" in v
        assert "http-error-code-in-product-surface" in v

    def test_bynara_provider_id_is_a_violation(self):
        # the disclosed R461 gap: a REGISTERED provider's id must be
        # scrubbed as mechanically as the quartet's (Art. XXXI)
        v = ti.transport_detail_violations("bynara is busy right now")
        assert "provider-id-in-product-surface" in v

    def test_region_not_served_is_a_failure_class_violation(self):
        v = ti.transport_detail_violations("failed: REGION_NOT_SERVED")
        assert "failure-class-in-product-surface" in v

    def test_auth_failure_class_name_is_a_violation(self):
        # the disclosed R458 typo: the actual class name AUTH_FAILURE
        # leaked undetected while only AUTH_FAILED was scrubbed
        v = ti.transport_detail_violations("probe classified "
                                           "AUTH_FAILURE")
        assert "failure-class-in-product-surface" in v

    def test_directive_sentences_still_clean(self):
        assert ti.transport_detail_violations(
            "I continued using another verified reasoning route.") == []
        assert ti.transport_detail_violations(
            "The requested test could not be completed.") == []


# ---------------------------------------------------------------------------
# 6. secret discipline (BS-021): fingerprints only, never key values
# ---------------------------------------------------------------------------

class TestSecretDiscipline:

    # a distinctive MIDDLE substring of the delivered key — the BS-021
    # rule allows masked fingerprints (6-char prefix + 4-char suffix)
    # but NEVER a key's recoverable body
    KEY_MARKER = "6ymQG662YEmKKmiXMw"

    def test_r462_artifacts_carry_no_key_values(self):
        for name in ("PROBE_CATALOG.json",
                     "TOKENHARBOR_OWNER_ESCALATION.json",
                     "R462_ROUND_RECORD.json"):
            p = REPO / "R462" / name
            if not p.exists():
                continue
            assert self.KEY_MARKER not in p.read_text(), name

    def test_round_sources_carry_no_key_values(self):
        for rel in ("scripts/r462_probe_tokenharbor.py",
                    "discovery_fabric/engine/provider_health.py",
                    "discovery_fabric/engine/llm_registry.py",
                    "discovery_fabric/engine/runtime_admission.py",
                    "toscanini/conversational/transport_invisibility.py"):
            assert self.KEY_MARKER not in (REPO / rel).read_text(), rel

"""R469 — the atria DEFAULT-PROVIDER + KEY-RING rotation round: contracts.

The operator delivery (2026-09-16, verbatim, key bodies redacted BS-021):
  "https://api.atria-asi.ai/console/keys: atr_6...Ku5f and
   atr_7...HJmm and atr_Q...ILrJ"
  "From Now on atira is out default API for discovery engine. Keep
   going to a new key of atira if one is exhausted. Wire it in the
   discovery engine. 4 api keys is 400million tokens"

Contracts pinned here:
1. THE RING REGISTRATION: atria's ProviderSpec carries the three-key
   ring in operator-declared order (ATRIA_API_KEY -> _2 -> _3); the
   availability marker stays ATRIA_API_KEY (the FIRST slot); every
   OTHER provider degrades to exactly [env_var] (pre-R469 behavior);
2. THE ROTATION CLASSES: the closed set is CREDIT_EXHAUSTED /
   AUTH_FAILURE / RATE_LIMITED — GONE / MODEL_NOT_FOUND /
   REGION_NOT_SERVED never rotate (a dead identifier or a region gate
   answers identically on every key);
3. THE RING WALK: active-slot selection skips empty slots and wraps;
   rotate_key walks forward only, and a fully exhausted ring RESETS to
   the first present slot (exhaustion is never persisted as a fact);
4. THE AVAILABILITY SURFACE: a provider with ANY present slot is
   available; the matrix row reports the ring, the present slots, and
   the active slot;
5. THE PROBE RIDES THE RING: probe_capability rotates on exhaustion-
   class failures (an exhausted head key must not PROBE_FAILED the
   rung before generate()'s rotation can fire) and records every
   rotation;
6. THE CALL PATH ROTATES: generate() on an exhaustion-class failure
   rotates to the next PRESENT key on the SAME rung BEFORE any
   provider fallback — the route carries FAILED_KEY_EXHAUSTED +
   action KEY_ROTATED hops, the serving hop records which slot
   answered, and the provider is NOT health-failure-marked by a
   key-slot exhaustion the ring survives;
7. THE FULL-EXHAUSTION FALLBACK: a ring that exhausts entirely falls
   through to the standing cascade — typed failure, sticky slot reset
   (auto-recovery), never a bill, never silent;
8. THE DEFAULT-PROVIDER PIN: atria heads every role's default order
   (ENGINE_DEFAULT_PROVIDER, code default "atria"); the Art. XLV
   attack-independence rule and the honest quality tiers are preserved
   (a routing pin, never a quality rewrite); "" disables; an unknown
   pin value is a no-op;
9. THE PROBE-BEFORE-RECORD artifact: key 3 was validated by the
   bogus-key differential BEFORE persistence (R469/PROBE_ATRIA_KEY3);
10. secret discipline: the R469 artifacts and scripts carry masked
    fingerprints only — no key VALUE ever (the BS-021 key-marker
    guard, regex + env-value forms).
"""
import json
import os
import re
import sys
import urllib.error
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import llm_registry as lr  # noqa: E402
from discovery_fabric.engine import provider_health as ph  # noqa: E402
from discovery_fabric.engine import runtime_admission as ra  # noqa: E402

PROBE = REPO / "R469" / "PROBE_ATRIA_KEY3.json"
SMOKE = REPO / "R469" / "ROTATION_SMOKE.json"
PROBE_SCRIPT = REPO / "scripts" / "r469_probe_atria_key3.py"
SECRETS_SCRIPT = REPO / "scripts" / "r469_hf_secrets.py"

# R470 (2026-09-16): the ring grew 3 -> 9 valid slots — the operator
# supplied seven more keys; ATRIA_API_KEY_8 was NOT registered then (its
# catalog probe answered a DETERMINISTIC 401 x3 — typed invalid,
# excluded, operator re-supply invited; R470/PROBE_ATRIA_KEYS4TO10.json).
# Slot numbering is NOT compressed: names keep their operator-given
# numbers so future keys append unambiguously.
# R472 (2026-09-16, the PARALLEL-LINE RECONCILIATION): the operator
# re-supplied key 8 (same string) and delivered keys 11-15 (the union
# of both lines' deliveries). BOTH probe records stand: the sibling's
# (R472/PROBE_ATRIA_KEYS11TO13.json, 22:40Z) measured key 8 catalog
# 200 x3 — cleared on their line; THIS line's
# (R472/PROBE_ATRIA_KEYS11TO15.json, 22:57Z) measured the SAME value
# DETERMINISTIC 401 x3, and the post-rebase decisive re-measure
# answered 401 x3 again — key 8's provider state FLAPPED; the LATEST
# typed verdict is INVALID, so the registration excludes it. The ring
# is FOURTEEN operator-ordered valid slots (1-7, 9-15).
# R478 (2026-09-17): key 8 REINSTATED per the LATEST typed measurement
# (R478/RING_VALIDATION.json: catalog 200 x3 + one 200 tiny completion;
# the flap history recorded in the registry comment) — FIFTEEN slots.
RING = ["ATRIA_API_KEY", "ATRIA_API_KEY_2", "ATRIA_API_KEY_3",
        "ATRIA_API_KEY_4", "ATRIA_API_KEY_5", "ATRIA_API_KEY_6",
        "ATRIA_API_KEY_7", "ATRIA_API_KEY_8", "ATRIA_API_KEY_9",
        "ATRIA_API_KEY_10", "ATRIA_API_KEY_11", "ATRIA_API_KEY_12",
        "ATRIA_API_KEY_13", "ATRIA_API_KEY_14", "ATRIA_API_KEY_15"]
# (R472 reconciliation end) (R472 — the 2026-09-16 audit's Top-10 #9 + P0-4, and the ring grows to the FIFTEEN-key delivery (probe-validated 14 valid slots). (1) TOP-10 #9 (the 30-day roadmap's driver item): the E2E driver's Leg-D retry observation is now committed into the record BEFORE the save and BEFORE the multi-minute resume poll (record[legs][D_retry] = d immediately; on_terminal assigned in every branch pre-save; the prior-202 branch keeps BOTH halves) — a kill during the poll can no longer lose the 202+retry_id body (the R471 disclosed reconstruction class is dead; tests/test_r472_driver_persistence.py 5/5: source-order pins + the real _save round-trip with OUT redirected). Engineer-drafted by Atria-Dawn-Preview (R472/ATRIA_ENGINEER_A.json, key 11, 6402 tokens, 57.6s, finish=stop), CTO-integrated verbatim. (2) P0-4 (the no-survivor learning card): toscanini/run_state.py learning_card() — the terminal no-mechanism/killed-lineage surface that TEACHES: what_was_tested, strongest_failed_hypothesis, key_missing_evidence, 2-3 ranked typed next actions (ADD_EVIDENCE/REFINE_PROBLEM/NEW_TERRITORY), basis line; fires ONLY for terminal scientific no-survivor (never premise/blocked/survivor/package); recorded fields only, absent facts labeled absent (Art. VI/XXV; genuine kills per the Art. LXI capability-signature rule). Wired into user_state_view (after outcome_label, pre-strip per the R414 discipline), the run-state object, the webapp types (LearningCard/LearningCardAction) and RunNarrative's settled-no-survivor banner (data-learning-card marker; the four audit-named sections; the verdict sentence unchanged — the card adds, never softens). CTO-completed per spec after the engineer's B-session hit the provider's measured cap limits (12k truncation x2, 32k+ 502s x4 — disclosed in R472/ATRIA_ENGINEER_B.json; the A-session pattern held). Tests: test_r472_learning_card 14/14 + webapp adversarial_r472 8/8. (3) THE RING: probe-before-record on the five new keys (R472/PROBE_ATRIA_KEYS11TO15.json): keys 11-15 ALL VALID (catalog 200, sole model Atria-Dawn-Preview; tiny completion 200 on key 11, 4.06s); all fifteen pairwise distinct; keys 1-10 identity-confirmed vs R470. ATRIA_API_KEY_8 re-probed per the operator's re-supply: DETERMINISTIC 401 x3 — the exclusion STANDS (re-measured, never assumed). Space surface extended: 15/15 ring names PRESENT (R472/HF_SPACE_SECRETS_ATRIA_RING15.json; the R470 direct-endpoint verification method). key_env_vars = the FOURTEEN valid operator-ordered slots (1-7, 9-15; key 8 excluded, slot numbers never compressed). keyring batteries moved forward (test_r469/test_r470 registration pins to the 14-slot contract) + test_r472_keyring14 (15 new). Batteries: r471 54, r470 78, r469 34+1skip, r468 20+1skip, r467 23, r465 15, r469_span 11 all green; webapp 13 files 155/155; tsc strict clean; production build green (/ first-load 119 kB, unchanged); MODULE_INVENTORY regenerated, zero drift; pre-commit constitution check PASS; BS-021 sweep: 18 credential values, zero occurrences in the tree. reviewer_provenance=AI_REVIEW)

# fake credential bodies — deliberately SHORT and non-matching to the
# BS-021 key-marker regex (atr_[A-Za-z0-9_-]{20,}); no real value here
K1, K2, K3 = "atr_local_k1", "atr_local_k2", "atr_local_k3"

BS021_TARGETS = [
    PROBE, SMOKE, PROBE_SCRIPT, SECRETS_SCRIPT,
    REPO / "discovery_fabric/engine/llm_registry.py",
    REPO / "discovery_fabric/engine/runtime_admission.py",
    REPO / "discovery_fabric/engine/provider_health.py",
    REPO / "discovery_fabric/engine/model_routing.py",
]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _clear_atria_env(monkeypatch):
    for v in RING:
        monkeypatch.delenv(v, raising=False)
    lr._reset_key_ring("atria")


def _set_ring(monkeypatch, k1=K1, k2=K2, k3=K3):
    _clear_atria_env(monkeypatch)
    monkeypatch.setenv("ATRIA_API_KEY", k1)
    monkeypatch.setenv("ATRIA_API_KEY_2", k2)
    monkeypatch.setenv("ATRIA_API_KEY_3", k3)


class _Http402(urllib.error.HTTPError):
    """A synthetic 402 (CREDIT_EXHAUSTED) matching the classifier's
    HTTPError handling (file-like body read)."""

    def __init__(self, body='{"error": "Insufficient credits"}'):
        import io
        super().__init__("https://atria.test/v1/chat/completions", 402,
                         "Payment Required", None, io.BytesIO(body.encode()))


class _Http401(urllib.error.HTTPError):
    def __init__(self):
        import io
        super().__init__("https://atria.test/v1/chat/completions", 401,
                         "Unauthorized", None,
                         io.BytesIO(b'{"error": "invalid key"}'))


# ---------------------------------------------------------------------------
# 1. the ring registration
# ---------------------------------------------------------------------------

def test_atria_ring_registered_in_operator_order():
    spec = lr._SPEC_BY_ID["atria"]
    assert lr.key_ring_slots(spec) == RING
    assert spec.env_var == "ATRIA_API_KEY"   # the marker stays slot 1
    # R470: 401x3 excluded key 8; R472 re-measured 401 x3 again; R478
    # (2026-09-17) measured catalog 200 x3 + a 200 tiny completion
    # (R478/RING_VALIDATION.json) — the LATEST typed verdict rules
    # (Art. III in BOTH directions, timestamps deciding): key 8 is
    # REINSTATED, every earlier probe record standing as history
    assert "ATRIA_API_KEY_8" in lr.key_ring_slots(spec)
    assert "ATRIA_API_KEY_15" in lr.key_ring_slots(spec)


def test_every_other_provider_degrades_to_single_key():
    for pid, spec in lr._SPEC_BY_ID.items():
        if pid == "atria":
            continue
        assert lr.key_ring_slots(spec) == [spec.env_var], pid


def test_ring_comment_carries_operator_directive_verbatim():
    src = (REPO / "discovery_fabric/engine/llm_registry.py").read_text()
    # the operator's directive, verbatim spelling ("atira") — Art. VI:
    # operator declarations are recorded as delivered, never corrected
    assert "Keep going to a new key of" in src
    assert "atira if one is exhausted" in src
    assert 'key_env_vars=["ATRIA_API_KEY", "ATRIA_API_KEY_2",' in src


# ---------------------------------------------------------------------------
# 2. the rotation classes
# ---------------------------------------------------------------------------

def test_rotation_classes_are_the_exhaustion_triad():
    assert set(lr.KEY_ROTATION_FAILURE_CLASSES) == {
        "CREDIT_EXHAUSTED", "AUTH_FAILURE", "RATE_LIMITED"}


def test_permanent_classes_never_rotate():
    for cls in ("GONE", "MODEL_NOT_FOUND", "REGION_NOT_SERVED"):
        assert cls not in lr.KEY_ROTATION_FAILURE_CLASSES


def test_classifier_maps_the_ring_failures_correctly():
    assert ph.classify_failure(_Http402()) == "CREDIT_EXHAUSTED"
    assert ph.classify_failure(_Http401()) == "AUTH_FAILURE"


# ---------------------------------------------------------------------------
# 3. the ring walk
# ---------------------------------------------------------------------------

def test_active_slot_skips_empty_and_wraps(monkeypatch):
    _clear_atria_env(monkeypatch)
    spec = lr._SPEC_BY_ID["atria"]
    assert lr.active_key_slot(spec) is None          # nothing present
    monkeypatch.setenv("ATRIA_API_KEY_3", K3)
    assert lr.active_key_slot(spec) == 2             # only slot 2
    monkeypatch.setenv("ATRIA_API_KEY", K1)
    assert lr.active_key_slot(spec) == 0
    assert lr.active_key_value(spec) == K1


def test_rotate_walks_forward_skips_empty_resets_on_exhaustion(monkeypatch):
    _set_ring(monkeypatch, k2="")                    # middle slot empty
    spec = lr._SPEC_BY_ID["atria"]
    assert lr.rotate_key(spec) == 2                  # skips empty slot 1
    assert lr.active_key_value(spec) == K3
    assert lr.rotate_key(spec) is None               # exhausted
    assert lr.active_key_slot(spec) == 0             # auto-recovery


def test_sticky_slot_avoids_repaying_the_exhausted_key(monkeypatch):
    _set_ring(monkeypatch)
    spec = lr._SPEC_BY_ID["atria"]
    assert lr.rotate_key(spec) == 1
    assert lr.rotate_key(spec) == 2
    assert lr.active_key_slot(spec) == 2             # stays rotated


# ---------------------------------------------------------------------------
# 4. the availability surface
# ---------------------------------------------------------------------------

def test_availability_matrix_reports_the_ring(monkeypatch):
    _clear_atria_env(monkeypatch)
    monkeypatch.setenv("ATRIA_API_KEY_2", K2)        # ONLY slot 2 present
    row = next(r for r in lr.availability_matrix()
               if r["provider_id"] == "atria")
    assert row["available"] is True
    assert row["key_ring_env_vars"] == RING
    assert row["key_slots_present"] == [1]
    assert row["key_slot_active"] == 1
    assert row["env_var"] == "ATRIA_API_KEY"


def test_unkeyed_provider_ring_all_empty(monkeypatch):
    _clear_atria_env(monkeypatch)
    spec = lr._SPEC_BY_ID["atria"]
    assert lr.active_key_slot(spec) is None
    row = next(r for r in lr.availability_matrix()
               if r["provider_id"] == "atria")
    assert row["available"] is False
    assert row["key_slots_present"] == []


# ---------------------------------------------------------------------------
# 5. the probe rides the ring
# ---------------------------------------------------------------------------

def test_probe_capability_rotates_and_records(monkeypatch):
    _set_ring(monkeypatch)
    calls = []

    def fake_call(spec, messages, timeout, max_tokens, model_override=None):
        key = lr.active_key_value(spec)
        calls.append(key)
        if key == K1:
            raise _Http402()
        return "TRANSPORT: ready"

    monkeypatch.setattr(lr, "_call_openai_flavor", fake_call)
    out = ra.probe_capability("atria", "Atria-Dawn-Preview",
                              persist_ledger=False)
    assert out["ok"] is True
    assert calls == [K1, K2]                         # rotated, no re-pay
    assert len(out["key_rotations"]) == 1
    rot = out["key_rotations"][0]
    assert rot["from_slot"] == 0 and rot["to_slot"] == 1
    assert rot["failure_class"] == "CREDIT_EXHAUSTED"
    assert rot["key_env_var"] == "ATRIA_API_KEY_2"
    assert out["key_slot"] == 1
    assert out["attempts"] == 2


def test_probe_full_ring_exhaustion_records_typed_failure(monkeypatch):
    _set_ring(monkeypatch)

    def fake_call(spec, messages, timeout, max_tokens, model_override=None):
        raise _Http402()

    monkeypatch.setattr(lr, "_call_openai_flavor", fake_call)
    out = ra.probe_capability("atria", "Atria-Dawn-Preview",
                              persist_ledger=False)
    assert out["ok"] is False
    assert out["failure_class"] == "CREDIT_EXHAUSTED"
    assert len(out["key_rotations"]) == 2            # 0->1, 1->2
    assert lr.active_key_slot(lr._SPEC_BY_ID["atria"]) == 0  # reset


# ---------------------------------------------------------------------------
# 5b. the probe's small-cap starvation recovery (R467 measured, R469 wired)
# ---------------------------------------------------------------------------

def test_probe_escalates_cap_on_reasoning_starvation(monkeypatch):
    """The R467 specimen: a reasoning model spends the probe budget
    (the rung's DECLARED probe_max_tokens included — the R469-C2
    mechanism) on hidden reasoning -> EmptyContentWithFinish; the
    documented recovery is the SAME rung at max_tokens 2000. The probe
    escalates ONCE past the declared budget and records it."""
    _set_ring(monkeypatch)
    caps = []

    def fake_call(spec, messages, timeout, max_tokens, model_override=None):
        caps.append(max_tokens)
        if max_tokens < 512:
            raise lr.EmptyContentWithFinish(
                "atria returned empty content (finish_reason=length, "
                f"max_tokens={max_tokens})", finish_reason="length")
        return "TRANSPORT: ready"

    monkeypatch.setattr(lr, "_call_openai_flavor", fake_call)
    out = ra.probe_capability("atria", "Atria-Dawn-Preview",
                              persist_ledger=False)
    assert out["ok"] is True
    # the R469-C2 declared budget (256) feeds the R469 escalation
    assert caps == [256, 2000]
    assert out["cap_escalation"] == {"from": 256, "to": 2000}
    assert out["key_rotations"] == []                # NOT a key failure


def test_probe_declared_budget_serves_when_content_fits(monkeypatch):
    """The R469-C2 mechanism intact under the R469 restructure: a rung
    that declares probe_max_tokens serves its DECLARED budget (no
    escalation, no rotation) — the two mechanisms compose, neither
    displaces the other."""
    _set_ring(monkeypatch)
    caps = []

    def fake_call(spec, messages, timeout, max_tokens, model_override=None):
        caps.append(max_tokens)
        return "TRANSPORT: ready"

    monkeypatch.setattr(lr, "_call_openai_flavor", fake_call)
    out = ra.probe_capability("atria", "Atria-Dawn-Preview",
                              persist_ledger=False)
    assert out["ok"] is True
    assert caps == [256]                              # the declared budget
    assert out["cap_escalation"] is None              # no starvation
    assert out["key_rotations"] == []


def test_probe_escalation_is_one_shot_and_typed(monkeypatch):
    """A model that starves even at 2000 stays a TYPED probe failure
    (MODEL_FAILURE) after exactly one escalation — bounded, honest."""
    _set_ring(monkeypatch)
    caps = []

    def fake_call(spec, messages, timeout, max_tokens, model_override=None):
        caps.append(max_tokens)
        raise lr.EmptyContentWithFinish(
            "atria returned empty content (finish_reason=length, "
            f"max_tokens={max_tokens})", finish_reason="length")

    monkeypatch.setattr(lr, "_call_openai_flavor", fake_call)
    out = ra.probe_capability("atria", "Atria-Dawn-Preview",
                              persist_ledger=False)
    assert out["ok"] is False
    assert out["failure_class"] == "MODEL_FAILURE"
    assert caps == [256, 2000]                        # bounded at two tries
    assert out["cap_escalation"] == {"from": 256, "to": 2000}


# ---------------------------------------------------------------------------
# 6/7. the generate() call path
# ---------------------------------------------------------------------------

def _hermetic_generate_env(monkeypatch):
    """Only the atria ring is keyed; admission is pre-seeded so the walk
    reaches the CALL loop directly (the probe path has its own tests)."""
    for var in list(lr._SPEC_BY_ID.keys()):
        env = lr._SPEC_BY_ID[var].env_var
        monkeypatch.delenv(env, raising=False)
    _set_ring(monkeypatch)
    monkeypatch.setattr(ra, "requires_probe",
                        lambda *a, **k: False)
    monkeypatch.setattr(
        ra, "runtime_admission",
        lambda *a, **k: (True, "PROBE_OK", {"state": "PROBE_OK"}))


def test_generate_rotates_on_exhaustion_same_rung(monkeypatch):
    _hermetic_generate_env(monkeypatch)
    calls = []

    def fake_call(spec, messages, timeout, max_tokens, model_override=None):
        key = lr.active_key_value(spec)
        calls.append(key)
        if key == K1:
            raise _Http402()
        return "FIELD_MECHANISM: cavitation threshold"

    monkeypatch.setattr(lr, "_call_openai_flavor", fake_call)
    monkeypatch.setattr(lr, "_call_anthropic_flavor", fake_call)
    # R519: atria is retired from ORDINARY synthesis routing (R518/R519
    # route retirement). This test measures the R469 KEY RING, which is a
    # measurement act — it reaches atria through the R491 explicit
    # measurement pin (hard_pin_provider), the single sanctioned
    # operator-override path for a retired provider (kept + recorded,
    # never silent).
    res = lr.generate("test prompt", schema=["FIELD_MECHANISM"],
                      role="synthesis", max_retries=0,
                      hard_pin_provider="atria")
    assert res.ok is True
    assert res.provider_id == "atria"
    assert calls == [K1, K2]
    # the route reconstructs the rotation (never silent)
    rot = [h for h in res.route if h.get("action") == "KEY_ROTATED"]
    assert len(rot) == 1
    assert rot[0]["status"] == "FAILED_KEY_EXHAUSTED"
    assert rot[0]["failure_type"] == "CREDIT_EXHAUSTED"
    assert rot[0]["key_slot_exhausted"] == 0 and rot[0]["key_slot"] == 1
    assert rot[0]["key_env_var"] == "ATRIA_API_KEY_2"
    assert rot[0]["fallback_provider"] == "atria"    # SAME provider
    # the serving hop records WHICH slot answered
    ok_hop = [h for h in res.route if h.get("status") == "OK"][-1]
    assert ok_hop["key_slot"] == 1
    assert ok_hop["key_env_var"] == "ATRIA_API_KEY_2"
    assert ok_hop["key_rotations"] == 1
    assert any("rotated to slot 1" in n for n in res.retry_notes)


def test_generate_ring_exhaustion_falls_through_typed(monkeypatch):
    _hermetic_generate_env(monkeypatch)
    attempts = []

    def fake_call(spec, messages, timeout, max_tokens, model_override=None):
        attempts.append(lr.active_key_value(spec))
        raise _Http402()

    monkeypatch.setattr(lr, "_call_openai_flavor", fake_call)
    monkeypatch.setattr(lr, "_call_anthropic_flavor", fake_call)
    res = lr.generate("test prompt", role="synthesis", max_retries=0,
                      hard_pin_provider="atria")
    assert res.ok is False
    assert res.status == lr.ST_CALL_FAILED
    assert res.failure_type == "CREDIT_EXHAUSTED"    # typed, never a bill
    # all three keys were tried on the SAME rung before giving up
    assert attempts == [K1, K2, K3]
    rots = [h for h in res.route if h.get("action") == "KEY_ROTATED"]
    assert len(rots) == 2                            # 0->1 and 1->2
    # auto-recovery: the sticky slot reset to the head key
    assert lr.active_key_slot(lr._SPEC_BY_ID["atria"]) == 0


def test_generate_does_not_rotate_on_gone(monkeypatch):
    """A dead model identifier answers identically on every key — the
    ring must NOT be consumed (the cascade advances instead)."""
    import io
    _hermetic_generate_env(monkeypatch)
    attempts = []

    def fake_call(spec, messages, timeout, max_tokens, model_override=None):
        attempts.append(lr.active_key_value(spec))
        raise urllib.error.HTTPError(
            "https://atria.test/v1/chat/completions", 404, "Not Found",
            None, io.BytesIO(b'{"error": {"code": "model_not_found"}}'))

    monkeypatch.setattr(lr, "_call_openai_flavor", fake_call)
    monkeypatch.setattr(lr, "_call_anthropic_flavor", fake_call)
    res = lr.generate("test prompt", role="synthesis", max_retries=0,
                      hard_pin_provider="atria")
    assert res.ok is False
    assert len(attempts) == 1                        # NO ring consumption
    assert lr.active_key_slot(lr._SPEC_BY_ID["atria"]) == 0


# ---------------------------------------------------------------------------
# 8. the default-provider pin
# ---------------------------------------------------------------------------

def _matrix_two_providers(monkeypatch):
    for pid, spec in lr._SPEC_BY_ID.items():
        monkeypatch.delenv(spec.env_var, raising=False)
    lr._reset_key_ring("atria")
    monkeypatch.setenv("ATRIA_API_KEY", K1)
    monkeypatch.setenv("ATRIA_API_KEY_2", K2)
    monkeypatch.setenv("ATRIA_API_KEY_3", K3)
    # unorouter (2,1,2) naturally outranks atria (2,1,3) unpinned
    monkeypatch.setenv("UNOROUTER_API_KEY", "unorouter_local_k")
    return lr.availability_matrix()


def test_pinned_default_heads_the_order(monkeypatch):
    # R518/R519: the R469 "atria heads the default order" policy is
    # SUPERSEDED — the default pin was cleared and atria is retired from
    # ORDINARY synthesis routing. With no explicit operator act, atria is
    # absent from the order (Art. LXIV: the superseded expectation is
    # retired, not left silently true).
    monkeypatch.delenv("ENGINE_DEFAULT_PROVIDER", raising=False)
    matrix = _matrix_two_providers(monkeypatch)
    order = ph.order_for_role(matrix, "synthesis")
    assert "atria" not in order                      # retired from ordinary route
    assert order[0] == "unorouter"                   # natural rank serves


def test_pin_disabled_restores_natural_rank(monkeypatch):
    # R519 §5: an EXPLICIT operator re-pin (ENGINE_DEFAULT_PROVIDER=atria)
    # remains possible under the selected semantics — retirement removes a
    # provider from ORDINARY routing, not from a deliberate, RECORDED
    # operator override. The re-pin is never silent: the order_for_role
    # out_events record the EXPLICIT_OPERATOR_OVERRIDE_ALLOWED state.
    matrix = _matrix_two_providers(monkeypatch)
    monkeypatch.setenv("ENGINE_DEFAULT_PROVIDER", "atria")
    events = []
    order = ph.order_for_role(matrix, "synthesis", out_events=events)
    assert order[0] == "atria"                       # explicit operator act serves
    assert any(e["retirement_state"] ==
               "EXPLICIT_OPERATOR_OVERRIDE_ALLOWED" for e in events)


def test_pin_env_overrides_to_another_provider(monkeypatch):
    matrix = _matrix_two_providers(monkeypatch)
    monkeypatch.setenv("ENGINE_DEFAULT_PROVIDER", "unorouter")
    assert ph.order_for_role(matrix, "synthesis")[0] == "unorouter"


def test_attack_independence_survives_the_pin(monkeypatch):
    monkeypatch.delenv("ENGINE_DEFAULT_PROVIDER", raising=False)
    matrix = _matrix_two_providers(monkeypatch)
    atk = ph.order_for_role(matrix, "attack", avoid_provider="atria")
    assert atk[0] != "atria"                         # Art. XLV wins


def test_unknown_pin_is_a_noop(monkeypatch):
    matrix = _matrix_two_providers(monkeypatch)
    monkeypatch.setenv("ENGINE_DEFAULT_PROVIDER", "nonexistent_provider")
    order = ph.order_for_role(matrix, "synthesis")
    assert order[0] == "unorouter"                   # natural rank


def test_ordinary_synthesis_route_has_no_default_pin(monkeypatch):
    # R539 SUPERSEDES R519: the operator's 2026-09-26 number-1-API
    # directive ("put this as the number 1 api, so infrastucture
    # failure doesnt happen again") re-pins the code-level default to
    # agnes (measured live 2026-09-26: catalog 200, flash rungs 200 OK
    # + 3/3 FIELD-line compliant). The R518/R519 cleared-pin state is
    # retired, not left silently true (Art. LXIV).
    monkeypatch.delenv("ENGINE_DEFAULT_PROVIDER", raising=False)
    assert ph._DEFAULT_PROVIDER_PIN == "agnes"


def test_agnes_pin_heads_the_order_when_available(monkeypatch):
    # R539: with the agnes credential present and no explicit operator
    # override, agnes heads every role's ordinary order (the number-1
    # API); the two standing rules still win (Art. XLV attack
    # independence, Art. V cooldown demotion).
    for pid, spec in lr._SPEC_BY_ID.items():
        monkeypatch.delenv(spec.env_var, raising=False)
    monkeypatch.delenv("ENGINE_DEFAULT_PROVIDER", raising=False)
    monkeypatch.setenv("AGNES_API_KEY", "agnes_local_k")
    monkeypatch.setenv("UNOROUTER_API_KEY", "unorouter_local_k")
    matrix = lr.availability_matrix()
    assert ph.order_for_role(matrix, "synthesis")[0] == "agnes"
    assert ph.order_for_role(matrix, "extraction")[0] == "agnes"
    atk = ph.order_for_role(matrix, "attack", avoid_provider="agnes")
    assert atk[0] != "agnes"                         # Art. XLV wins


def test_catalog_discovery_uses_active_ring_key(monkeypatch):
    """model_routing._get_json must receive the ACTIVE ring key (a
    rotated-forward provider does not re-pay the exhausted head key)."""
    _set_ring(monkeypatch)
    seen = {}

    def fake_get_json(url, key, timeout=20, extra_headers=None):
        seen["url"], seen["key"] = url, key
        return {"data": [{"id": "Atria-Dawn-Preview"}]}

    from discovery_fabric.engine import model_routing as mrmod
    monkeypatch.setattr(mrmod, "_get_json", fake_get_json)
    # force a fresh fetch (bypass the TTL cache)
    monkeypatch.setattr(mrmod, "CATALOG_TTL_S", 0)
    cache = mrmod.CATALOG_DIR / "atria.json"
    if cache.exists():
        cache.unlink()
    out = mrmod.discover_catalog("atria", force=True)
    assert out["status"] == "DISCOVERED"
    assert seen["key"] == K1
    assert "Atria-Dawn-Preview" in out["models"]
    # rotate forward -> the NEXT catalog fetch rides the new key
    assert lr.rotate_key(lr._SPEC_BY_ID["atria"]) == 1
    out2 = mrmod.discover_catalog("atria", force=True)
    assert out2["status"] == "DISCOVERED"
    assert seen["key"] == K2


# ---------------------------------------------------------------------------
# 9. the probe-before-record artifact
# ---------------------------------------------------------------------------

def test_probe_artifact_records_key3_validation():
    if not PROBE.exists():
        pytest.skip("probe artifact not yet generated this round")
    art = json.loads(PROBE.read_text())
    assert art["verdict"]["key3_valid"] is True
    assert art["verdict"]["completion_ok"] is True
    assert art["verdict"]["ring_size_measured"] == 3
    assert art["identity_checks"]["key1_same_as_r467"] is True
    assert art["identity_checks"]["key2_same_as_r468"] is True
    assert art["identity_checks"]["all_three_distinct"] is True
    # the bogus-key differential control separated
    bogus = next(p for p in art["probes"]
                 if p["probe"] == "models_bogus_key")
    assert bogus["status"] in (401, 403)
    ring200 = [r for r in art["ring_catalog_view"]
               if r.get("status") == 200]
    assert len(ring200) == 3
    for r in ring200:
        assert r["model_ids"] == ["Atria-Dawn-Preview"]


def test_probe_script_reads_env_only():
    src = PROBE_SCRIPT.read_text()
    assert 'os.environ.get("ATRIA_API_KEY_3", "").strip()' in src
    assert "atr_Q02" not in src and "atr_63" not in src \
        and "atr_7WW" not in src


def test_rotation_smoke_artifact_all_green():
    if not SMOKE.exists():
        pytest.skip("rotation smoke not yet generated this round")
    art = json.loads(SMOKE.read_text())
    assert art["verdict"]["ALL_GREEN"] is True
    arms = {a["arm"]: a for a in art["arms"]}
    assert arms["control_all_real"]["serving_key_env_var"] == \
        "ATRIA_API_KEY"
    assert arms["probe_rotation_key1_dead"][
        "serving_key_env_var"] == "ATRIA_API_KEY_2"
    loop = arms["callloop_rotation_key1_dead"]
    assert loop["serving_key_env_var"] == "ATRIA_API_KEY_2"
    assert loop["rotation_hops"][0]["failure_type"] == "AUTH_FAILURE"
    assert loop["rotation_hops"][0]["status"] == "FAILED_KEY_EXHAUSTED"
    assert arms["two_hop_keys12_dead"][
        "serving_key_env_var"] == "ATRIA_API_KEY_3"
    # every arm answered the structured protocol
    for a in art["arms"]:
        assert len(a["fields_present"]) == 3, a["arm"]


def test_secrets_script_reads_env_only():
    if not SECRETS_SCRIPT.exists():
        pytest.skip("secrets script not yet written this round")
    src = SECRETS_SCRIPT.read_text()
    assert 'SET_NOW = ("ATRIA_API_KEY_3",)' in src
    assert 'os.environ.get(var, "").strip()' in src
    assert 'os.environ.get("HF_TOKEN", "").strip()' in src  # the gate
    assert "atr_Q02" not in src and "atr_63" not in src \
        and "atr_7WW" not in src


def test_hf_secrets_artifact_surface():
    p = REPO / "R469" / "HF_SPACE_SECRETS.json"
    if not p.exists():
        pytest.skip("secrets artifact not yet generated this round")
    art = json.loads(p.read_text())
    assert art["set_this_round"]["ATRIA_API_KEY_3"]["set"] is True
    assert art["set_this_round"]["ATRIA_API_KEY_3"][
        "value"] == "<never recorded>"
    assert art["key3_probe_verdict"]["key3_valid"] is True
    # the full expected surface present, none ABSENT
    absent = [k for k, v in art["verified_names"].items()
              if v == "ABSENT"]
    assert absent == []
    assert "ATRIA_API_KEY_3" in art["verified_names"]


# ---------------------------------------------------------------------------
# 10. secret discipline — the BS-021 key-marker guard (R469 targets)
# ---------------------------------------------------------------------------

def test_artifacts_carry_no_key_values_regex():
    patterns = [
        r"atr_[A-Za-z0-9_-]{20,}",
        r"hf_[A-Za-z0-9_-]{20,}",
        r"ghp_[A-Za-z0-9_-]{20,}",
    ]
    for target in BS021_TARGETS:
        if not target.exists():
            continue
        text = target.read_text()
        for pat in patterns:
            m = re.search(pat, text)
            assert m is None, \
                f"key-value pattern {pat!r} found in {target.name}: " \
                f"{m.group(0)[:8]}..."


def test_artifacts_carry_no_env_key_values():
    values = [v.strip() for v in (
        os.environ.get("ATRIA_API_KEY", ""),
        os.environ.get("ATRIA_API_KEY_2", ""),
        os.environ.get("ATRIA_API_KEY_3", ""),
        os.environ.get("HF_TOKEN", ""),
    ) if len(v.strip()) >= 20]
    if not values:
        pytest.skip("no key values in session env (BS-021 env-only)")
    for target in BS021_TARGETS:
        if not target.exists():
            continue
        text = target.read_text()
        for val in values:
            assert val not in text, \
                f"a live key VALUE leaked into {target.name}"


def test_test_fixtures_do_not_match_key_marker_regex():
    for val in (K1, K2, K3):
        assert re.search(r"atr_[A-Za-z0-9_-]{20,}", val) is None


# ---------------------------------------------------------------------------
# R469 reconciliation: the operator's LATEST directive supplies SEVEN
# atria keys. The declared ring carries all seven names; only the
# PRESENT slots participate; a slot that appears later joins in order.
# ---------------------------------------------------------------------------

def test_seven_slot_ring_declared_and_present_behavior(monkeypatch):
    spec = lr._SPEC_BY_ID["atria"]
    # the declared ring is the seven-name operator order
    assert lr.key_ring_slots(spec) == RING
    # only PRESENT slots participate (slots 4-7 absent from this env)
    for name in RING[:3]:
        monkeypatch.setenv(name, f"k-{name}")
    for name in RING[3:]:
        monkeypatch.delenv(name, raising=False)
    present = [n for n in RING
               if os.environ.get(n, "").strip()]
    assert present == RING[:3]
    # an absent slot never yields a value
    for name in RING[3:]:
        monkeypatch.delenv(name, raising=False)

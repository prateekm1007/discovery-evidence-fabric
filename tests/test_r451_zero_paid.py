"""tests/test_r451_zero_paid.py — the R451-C1.1 battery (hermetic).

FREE-MODEL / ZERO-PAID-COST DISCOVERY — the production discovery
restoration contract:

  1. MODEL_COST_POLICY = ZERO_PAID_COST is a REAL policy:
     only ZERO_PAID_COST_SELF_HOSTED bases are eligible; PAID_API /
     ENVIRONMENT_GRANT / FREE_TIER_API / UNDECLARED are refused with a
     recorded refusal — never silently fallen back to (the R450
     production defect: the stale glm-4-plus paid rung was the last
     rung of a PAID fallback chain).
  2. The local provider (localqwen) is an ORDINARY registry provider:
     no bespoke `if local_model` branch — same ProviderSpec shape,
     same routing rungs, cost provenance on every call.
  3. Fail-closed: when the policy filters out every provider, the call
     is POLICY_BLOCKED (paid keys PRESENT in the environment are
     REFUSED) — the engine records WHY, it never widens the policy.
  4. The stale glm-4-plus fallback is RETIRED: neither the zai spec's
     default model nor the zai routing rung names it.
  5. THE VERIFIABLE DIRECTION_DELTA (R451 §3): the R450 shortcut
     (gap retrieval returned items -> evidence_changed_direction =
     True) is REPLACED — the flag is True ONLY when a CLOSED causal
     field changed WITH a verified attribution to exact new evidence
     whose span appears VERBATIM; no causal change -> False, no
     exceptions.
  6. Routing observability (R451 §6): every actual attempt — success
     OR failure — is persisted with provider, model, attempt, status,
     failure_class, latency, cost_class, selected, fallback_reason;
     the in-result route reconstructs the exact path including the
     SELECTED hop (never a bare "models unavailable" summary).

Constitutional anchors: Art. IV (no fallback epistemology — no silent
widening of the cost policy), Art. VI (provenance never manufactured),
Art. XVII (attempted bypasses below), Art. XXV (unknown cost basis is
never silently free), Art. LXI (a policy refusal is infrastructure,
never a scientific verdict).
"""
from __future__ import annotations

import json
import sys
import urllib.error
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine import llm_registry as reg  # noqa: E402
from discovery_fabric.engine import model_cost_policy as cp  # noqa: E402
from discovery_fabric.engine import model_routing as mr
from discovery_fabric.engine import runtime_admission as ra  # noqa: E402
from discovery_fabric.engine import provider_health as ph  # noqa: E402
from discovery_fabric.directional.delta import (  # noqa: E402
    CAUSAL_FIELDS, direction_delta, parse_attribution_lines)
from discovery_fabric.directional import loop as dloop  # noqa: E402


# ---------------------------------------------------------------------------
# hermetic routing fixtures (Art. IX: production state is never touched)
# ---------------------------------------------------------------------------
@pytest.fixture()
def hermetic(monkeypatch, tmp_path):
    tmp = Path(tmp_path)
    monkeypatch.setattr(mr, "LEDGER", mr.RoutingLedger(
        path=tmp / "ledger.jsonl"))
    monkeypatch.setattr(mr, "STATE_PATH", tmp / "state.json")
    # R451-C1.3: the capability store is production admission
    # state — tests redirect it (Art. IX)
    ra.set_state_path(tmp / "capability_state.json")
    monkeypatch.setattr(mr, "CATALOG_DIR", tmp / "catalog")
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


_ALL_KEY_VARS = ["OPENROUTER_API_KEY", "QWEN_API_KEY",
                 "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY",
                 "DEEPSEEK_API_KEY", "MISTRAL_API_KEY",
                 "NVIDIA_API_KEY", "ZAI_API_KEY",
                 "TOKEN_ROUTER_API_KEY"]


def _no_keys(monkeypatch):
    for k in _ALL_KEY_VARS:
        monkeypatch.delenv(k, raising=False)


# ---------------------------------------------------------------------------
# 1. the cost policy is a REAL policy (fail-closed, closed vocabulary)
# ---------------------------------------------------------------------------
class TestCostPolicy:

    def test_default_policy_is_zero_paid(self, monkeypatch):
        monkeypatch.delenv("ENGINE_MODEL_COST_POLICY", raising=False)
        assert cp.active_policy() == cp.ZERO_PAID_COST

    def test_env_override_unrestricted_is_honest(self, monkeypatch):
        monkeypatch.setenv("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")
        assert cp.active_policy() == cp.UNRESTRICTED
        assert set(cp.eligible_bases()) == set(cp.COST_BASIS_VOCAB)

    def test_unknown_policy_value_falls_to_zero_paid(self, monkeypatch):
        monkeypatch.setenv("ENGINE_MODEL_COST_POLICY", "SOMETHING_ODD")
        assert cp.active_policy() == cp.ZERO_PAID_COST

    def test_only_self_hosted_basis_eligible(self, monkeypatch):
        monkeypatch.setenv("ENGINE_MODEL_COST_POLICY", "ZERO_PAID_COST")

        class Spec:
            def __init__(self, basis):
                self.cost_basis = basis

        # R456-A3 reconciliation (Art. LXIV rule 2, dated 2026-09-15):
        # the R451 pin froze the eligible set to self-hosted only; the
        # operator's recorded amendment (model_cost_policy.py v1.1.0,
        # directive quoted verbatim there) admits FREE_TIER_API. The
        # fail-closed invariant is unchanged: PAID_API,
        # ENVIRONMENT_GRANT, and UNDECLARED are still refused — a paid
        # route can never silently ride the amendment.
        for basis in ("PAID_API", "ENVIRONMENT_GRANT", "UNDECLARED"):
            ok, _ = cp.provider_eligibility(Spec(basis))
            assert ok is False, basis
        for basis in ("ZERO_PAID_COST_SELF_HOSTED", "FREE_TIER_API"):
            ok, _ = cp.provider_eligibility(Spec(basis))
            assert ok is True, basis

    def test_undeclared_cost_basis_is_never_silently_free(
            self, monkeypatch):
        monkeypatch.setenv("ENGINE_MODEL_COST_POLICY", "ZERO_PAID_COST")

        class Spec:
            cost_basis = "UNDECLARED"

        ok, note = cp.provider_eligibility(Spec())
        assert ok is False
        assert "never silently treated as free" in note

    def test_filter_chain_records_refusals(self, monkeypatch):
        monkeypatch.setenv("ENGINE_MODEL_COST_POLICY", "ZERO_PAID_COST")

        class Spec:
            def __init__(self, pid, basis):
                self.provider_id = pid
                self.cost_basis = basis

        by_id = {"localqwen": Spec("localqwen",
                                   "ZERO_PAID_COST_SELF_HOSTED"),
                 "openai": Spec("openai", "PAID_API"),
                 "zai": Spec("zai", "ENVIRONMENT_GRANT")}
        chain, refusals = cp.filter_chain(
            ["localqwen", "openai", "zai", "ghost"], by_id)
        assert chain == ["localqwen"]
        assert {r["provider"] for r in refusals} == {"openai", "zai"}
        assert all(r["policy"] == "ZERO_PAID_COST" for r in refusals)

    def test_cost_provenance_carries_the_full_model_card(self):
        class Spec:
            cost_basis = "ZERO_PAID_COST_SELF_HOSTED"
            locality = "LOCAL"
            license = "apache-2.0"
            model_revision = "gguf-sha-abc"
            model_for_call = lambda self="": "qwen3-1.7b"  # noqa: E731
            url_for_call = lambda self="": "http://127.0.0.1:8790/v1"  # noqa: E731

        prov = cp.cost_provenance(Spec())
        for key in ("model_id", "model_revision", "transport",
                    "local_or_remote", "license", "cost_basis",
                    "policy", "policy_version"):
            assert key in prov, key
        assert prov["model_id"] == "qwen3-1.7b"
        assert prov["local_or_remote"] == "LOCAL"
        assert prov["license"] == "apache-2.0"


# ---------------------------------------------------------------------------
# 2. the local provider is an ORDINARY registry provider
# ---------------------------------------------------------------------------
class TestLocalProviderRegistry:

    def test_localqwen_spec_exists_with_zero_paid_basis(self):
        spec = reg._SPEC_BY_ID["localqwen"]
        assert spec.cost_basis == "ZERO_PAID_COST_SELF_HOSTED"
        assert spec.locality == "LOCAL"
        assert spec.license == "apache-2.0"
        assert "dcb19155" in spec.model_revision  # pinned GGUF build
        assert spec.env_var == "LOCAL_QWEN_BASE_URL"
        # the transport-only extra (thinking disabled) rides the SAME
        # openai-flavor path — no bespoke call branch anywhere
        assert spec.extra_body == {
            "chat_template_kwargs": {"enable_thinking": False}}

    def test_localqwen_has_routing_rungs(self):
        rungs = mr.PINNED_DEFAULT_MODELS.get("localqwen") or []
        assert rungs and rungs[0]["model"] == "qwen3-1.7b"

    def test_every_spec_declares_a_cost_basis(self):
        for spec in reg.PROVIDER_SPECS:
            assert spec.cost_basis in cp.COST_BASIS_VOCAB, \
                spec.provider_id
            assert spec.locality in ("LOCAL", "REMOTE",
                                     "UNDECLARED"), spec.provider_id

    def test_availability_matrix_carries_cost_fields(
            self, hermetic, monkeypatch):
        monkeypatch, _ = hermetic
        _no_keys(monkeypatch)
        monkeypatch.setenv("LOCAL_QWEN_BASE_URL",
                           "http://127.0.0.1:8790/v1/chat/completions")
        matrix = reg.availability_matrix()
        row = {m["provider_id"]: m for m in matrix}["localqwen"]
        assert row["available"] is True
        assert row["cost_policy_eligible"] is True
        assert row["cost_basis"] == "ZERO_PAID_COST_SELF_HOSTED"
        # a paid provider with a key present is available but REFUSED
        monkeypatch.setenv("OPENAI_API_KEY", "sk-paid")
        matrix = reg.availability_matrix()
        row = {m["provider_id"]: m for m in matrix}["openai"]
        assert row["available"] is True
        assert row["cost_policy_eligible"] is False


# ---------------------------------------------------------------------------
# 3. fail-closed: paid keys PRESENT are REFUSED, never silently used
# ---------------------------------------------------------------------------
class TestFailClosed:

    def test_paid_keys_present_are_refused(self, hermetic, monkeypatch):
        """THE attempted bypass (Art. XVII): an adversary (or an
        operator habit) leaves EVERY paid credential in the environment
        with the local provider unwired — the policy must REFUSE them
        all (POLICY_BLOCKED), never silently fall back to a paid route."""
        monkeypatch, _ = hermetic
        _no_keys(monkeypatch)
        monkeypatch.delenv("LOCAL_QWEN_BASE_URL", raising=False)
        monkeypatch.setenv("ENGINE_MODEL_COST_POLICY", "ZERO_PAID_COST")
        # every PAID credential PRESENT.
        # R456-A3 reconciliation: TOKEN_ROUTER_API_KEY leaves the
        # adversary set — its provider is FREE_TIER_API (the operator
        # amendment, model_cost_policy v1.1.0), so a present key makes
        # it ELIGIBLE and an attempted call, not a policy refusal; with
        # garbage credentials it fails honestly (CALL_FAILED, typed
        # classification, recorded in the ledger) and can never
        # silently serve. The invariant this test pins is unchanged:
        # every PAID basis is refused, no paid route is ever reached.
        for k in _ALL_KEY_VARS:
            if k not in ("LOCAL_QWEN_BASE_URL", "TOKEN_ROUTER_API_KEY"):
                monkeypatch.setenv(k, "adversary-supplied-key")
        res = reg.generate("Reply with: READY", system="policy probe",
                           max_tokens=8, max_retries=0, timeout=10)
        assert res.status == reg.ST_POLICY_BLOCKED
        assert res.content is None
        refusals = (res.selection_ledger or {}).get(
            "cost_policy_refusals") or []
        refused = {r["provider"] for r in refusals}
        assert "openai" in refused and "anthropic" in refused
        assert "zai" in refused  # ENVIRONMENT_GRANT is refused too

    def test_policy_blocked_is_a_distinct_status(self):
        assert reg.ST_POLICY_BLOCKED == "POLICY_BLOCKED"
        assert reg.ST_POLICY_BLOCKED != reg.ST_PROVIDER_UNAVAILABLE
        assert reg.ST_POLICY_BLOCKED != reg.ST_CALL_FAILED

    def test_no_provider_at_all_is_provider_unavailable(
            self, hermetic, monkeypatch):
        monkeypatch, _ = hermetic
        _no_keys(monkeypatch)
        monkeypatch.delenv("LOCAL_QWEN_BASE_URL", raising=False)
        res = reg.generate("Reply with: READY", system="probe",
                           max_tokens=8, max_retries=0, timeout=10)
        assert res.status == reg.ST_PROVIDER_UNAVAILABLE

    def test_zero_paid_call_serves_with_cost_provenance(
            self, hermetic, monkeypatch):
        """The happy path: the local provider wired, a paid key ALSO
        present — the call goes to localqwen (the only eligible route)
        and the cost provenance names it."""
        monkeypatch, tmp = hermetic
        _no_keys(monkeypatch)
        monkeypatch.setenv("LOCAL_QWEN_BASE_URL",
                           "http://127.0.0.1:8790/v1/chat/completions")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-paid-present")
        monkeypatch.setattr(
            reg, "_call_openai_flavor",
            lambda spec, messages, timeout, max_tokens,
            model_override=None: "READY")
        res = reg.generate("Reply with: READY", system="probe",
                           max_tokens=8, max_retries=0, timeout=10)
        assert res.status == reg.ST_OK
        assert res.provider_id == "localqwen"
        assert res.cost_provenance["cost_basis"] == \
            "ZERO_PAID_COST_SELF_HOSTED"
        assert res.cost_provenance["local_or_remote"] == "LOCAL"

    def test_all_paid_preferred_chain_extends_to_eligible(
            self, hermetic, monkeypatch):
        """R451-C1.1: the SYNTHESIS pin (a preferred chain of paid
        providers only) must not dead-end into POLICY_BLOCKED while an
        eligible zero-paid route serves — the chain EXTENDS to the
        eligible providers (recorded in the ledger, never silent, never
        INTO a paid route)."""
        monkeypatch, tmp = hermetic
        _no_keys(monkeypatch)
        monkeypatch.setenv("LOCAL_QWEN_BASE_URL",
                           "http://127.0.0.1:8790/v1/chat/completions")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-paid")  # paid AND live
        monkeypatch.setattr(
            reg, "_call_openai_flavor",
            lambda spec, messages, timeout, max_tokens,
            model_override=None: "READY")
        res = reg.generate(
            "Reply with: READY", system="probe", max_tokens=8,
            max_retries=0, timeout=10,
            policy=reg.SelectionPolicy(
                preferred_providers=["openrouter", "deepseek",
                                     "anthropic", "openai", "gemini",
                                     "qwen", "nvidia"],
                purpose="synthesis"))
        assert res.status == reg.ST_OK
        assert res.provider_id == "localqwen"  # NEVER the paid key
        ledger = res.selection_ledger or {}
        assert ledger.get("cost_policy_chain_extension") == \
            ["localqwen"]
        refusals = ledger.get("cost_policy_refusals") or []
        assert any(r["provider"] == "openai" for r in refusals)


# ---------------------------------------------------------------------------
# 4. the stale glm-4-plus fallback is RETIRED
# ---------------------------------------------------------------------------
class TestStaleFallbackRetired:

    def test_zai_spec_default_is_not_glm4plus(self):
        spec = reg._SPEC_BY_ID["zai"]
        assert spec.model_for_call() != "glm-4-plus"
        assert spec.model_for_call() == "zai-org/GLM-5.3"

    def test_no_routing_rung_names_glm4plus(self):
        for pid, rungs in mr.PINNED_DEFAULT_MODELS.items():
            for r in rungs:
                assert r["model"] != "glm-4-plus", (pid, r)

    def test_no_spec_default_names_glm4plus(self):
        for spec in reg.PROVIDER_SPECS:
            assert spec.model_for_call() != "glm-4-plus", \
                spec.provider_id

    def test_gateway_reports_env_model_not_stale_label(self):
        from toscanini import gateway as gw
        snap = gw.transport_snapshot()
        if snap.get("model"):
            assert snap["model"] != "glm-4-plus"


# ---------------------------------------------------------------------------
# 5. THE VERIFIABLE DIRECTION_DELTA (the shortcut is REPLACED)
# ---------------------------------------------------------------------------
EV_A = {"id": "ev:aaa111", "title": "Slurry erosion of white irons",
        "abstract": "Erosion rate falls with carbide volume fraction "
                    "above 35 percent in quartz slurry."}
EV_B = {"id": "ev:bbb222", "title": "Rubber linings",
        "abstract": "Natural rubber outlasts white iron by 3x below "
                    "60 C in abrasive acid slurry."}


def _before(**over):
    h = {f: "" for f in CAUSAL_FIELDS}
    h.update({
        "target_variable": "carbide volume fraction",
        "current_value": "28 percent",
        "proposed_value": "35 percent",
        "direction": "INCREASE",
        "mechanism_affected": "carbide-supported erosion resistance",
        "intervention_type": "MATERIAL_MUTATION",
        "predicted_effect": "erosion rate falls in quartz slurry",
    })
    h.update(over)
    return h


class TestDirectionDelta:

    def test_no_causal_change_is_false_no_exceptions(self):
        after = _before()
        delta = direction_delta(_before(), [EV_A, EV_B], after, [])
        assert delta["evidence_changed_direction"] is False
        assert delta["verdict"] == "EVIDENCE_ARRIVED_NO_CHANGE"

    def test_cosmetic_changes_never_count(self):
        after = _before(confidence="HIGH")  # not a causal field
        delta = direction_delta(_before(), [EV_A], after, [])
        assert delta["evidence_changed_direction"] is False

    def test_verified_attribution_sets_true(self):
        after = _before(proposed_value="42 percent",
                        direction="INCREASE")
        claims = [{"field": "proposed_value",
                   "evidence_id": "ev:aaa111",
                   "reason": "erosion falls above 35 percent"}]
        delta = direction_delta(_before(), [EV_A], after, claims)
        assert delta["evidence_changed_direction"] is True
        assert delta["verdict"] == "DIRECTION_CHANGED_BY_EVIDENCE"
        changed = delta["changed_fields"][0]
        assert changed["field"] == "proposed_value"
        assert changed["before"] == "35 percent"
        assert changed["after"] == "42 percent"
        assert changed["attribution"]["span_verified"] is True

    def test_unattributed_change_only_is_false(self):
        """A causal field changed but the model claimed NO evidence
        caused it -> LLM variance, not evidence causation."""
        after = _before(proposed_value="42 percent")
        delta = direction_delta(_before(), [EV_A], after, [])
        assert delta["evidence_changed_direction"] is False
        assert delta["verdict"] == "UNVERIFIED_CHANGE_ONLY"

    def test_attribution_to_absent_evidence_id_is_unverified(self):
        """THE attempted bypass: the model attributes its change to an
        id that is NOT among the new evidence — the attribution does
        not verify (Art. III: the claimant cannot define the evidence)."""
        after = _before(proposed_value="42 percent")
        claims = [{"field": "proposed_value",
                   "evidence_id": "ev:ghost999",
                   "reason": "fabricated citation"}]
        delta = direction_delta(_before(), [EV_A], after, claims)
        assert delta["evidence_changed_direction"] is False

    def test_no_new_evidence_is_false(self):
        after = _before(proposed_value="42 percent")
        delta = direction_delta(_before(), [], after, [])
        assert delta["evidence_changed_direction"] is False
        assert delta["verdict"] == "NO_NEW_EVIDENCE"

    def test_parse_attribution_lines(self):
        content = ("EVIDENCE_CAUSED: PROPOSED_VALUE <- ev:aaa111 because "
                   "erosion falls above 35 percent\n"
                   "EVIDENCE_CAUSED: DIRECTION <- ev:bbb222 because "
                   "rubber outlasts iron\n")
        claims = parse_attribution_lines(content)
        assert claims[0]["field"] == "proposed_value"
        assert claims[0]["evidence_id"] == "ev:aaa111"
        assert claims[1]["evidence_id"] == "ev:bbb222"

    def test_partial_attribution_is_recorded_honestly(self):
        """TWO fields changed; only ONE carries a verified attribution —
        the direction WAS changed by evidence; the unattributed field
        carries its UNVERIFIED verdict (never silently credited)."""
        after = _before(proposed_value="42 percent",
                        direction="CHANGE_MECHANISM")
        claims = [{"field": "proposed_value",
                   "evidence_id": "ev:aaa111",
                   "reason": "erosion falls above 35 percent"}]
        delta = direction_delta(_before(), [EV_A], after, claims)
        assert delta["evidence_changed_direction"] is True
        assert delta["verdict"] == \
            "DIRECTION_CHANGED_BY_EVIDENCE_PARTIAL_ATTRIBUTION"
        by_field = {c["field"]: c for c in delta["changed_fields"]}
        assert by_field["proposed_value"]["verdict"] == \
            "ATTRIBUTED_VERIFIED"
        assert by_field["direction"]["verdict"] == "UNATTRIBUTED"


# ---------------------------------------------------------------------------
# 5b. the LOOP wires the delta (the shortcut is gone at the loop level)
# ---------------------------------------------------------------------------
class TestLoopReversePath:
    """directional_step's reverse path: retrieval -> RE-PROPOSAL ->
    VERIFIED delta. All LLM/retrieval surfaces are monkeypatched — the
    tests assert the CONTRACT, not any network behavior."""

    def _step(self, monkeypatch, tmp_path, *, after, gap_items,
              claims):
        # a BEFORE proposal that passes the gate's structural checks
        # and declares gaps (triggering the reverse path)
        hyp_before = {
            "hypothesis_id": "dh:before0000000000000000",
            "candidate_id": "cand-1",
            "failure_id": "diag:1",
            "causal_diagnosis_id": "diag:1",
            "target_variable": "carbide volume fraction",
            "current_value": "28 percent",
            "proposed_value": "35 percent",
            "direction": "INCREASE",
            "mechanism_affected": "carbide-supported erosion resistance",
            "causal_rationale": "the diagnosed cause is hydro-abrasive "
                                "erosion of the carbide matrix",
            "predicted_effect": "erosion rate falls in quartz slurry",
            "predicted_magnitude_or_range": "",
            "competing_explanations": [],
            "evidence_support": [],
            "evidence_gaps": ["carbide fraction above 35 percent "
                              "erosion data"],
            "falsifier": "erosion rate measured above the white-iron "
                         "baseline under identical slurry conditions",
            "measurement_required": "quartz slurry erosion coupon test",
            "intervention_type": "MATERIAL_MUTATION",
            "confidence": "LOW",
            "provenance": {"class": "AI_PROPOSED"},
            "status": "PROPOSED",
            "gate": {},
        }
        monkeypatch.setattr(
            dloop, "propose_directional_hypothesis",
            lambda *a, **k: hyp_before)
        monkeypatch.setattr(
            dloop, "serve_evidence_gaps",
            lambda problem, hyp: (gap_items, {
                "loop_step": "EVIDENCE_GAP_RETRIEVAL", "state": "OK",
                "n_items": len(gap_items)}))
        monkeypatch.setattr(
            dloop, "repropose_with_evidence",
            lambda before, ev, attempt=1: after)
        parent = {"invention_id": "cand-1",
                  "architecture": {"mechanism":
                                   "white iron carbide impeller"}}
        problem = {"device": "slurry pump impeller",
                   "failure": "erosion at 1100 hours",
                   "constraint": "6000 hour service life"}
        diagnosis = {"diagnosis_id": "diag:1", "cause": "ADVERSARIAL_KILL",
                     "basis": ["carbide fraction too low"]}
        return dloop.directional_step(
            run_dir=Path(tmp_path), problem=problem, parent=parent,
            diagnosis=diagnosis, failure_summary="attack killed",
            evidence_items=[], gen_n=2)

    def test_retrieval_alone_never_sets_the_flag(self, monkeypatch,
                                                 tmp_path):
        """THE R450 SHORTCUT, REJECTED: gap retrieval returns items and
        the re-proposal keeps every causal field UNCHANGED — the flag
        is False and the honest no-change state is recorded (support
        arrives, the DIRECTION does not move)."""
        after = _before()  # identical causal fields
        after["evidence_gaps"] = []
        hyp = self._step(monkeypatch, tmp_path, after=after,
                         gap_items=[EV_A, EV_B], claims=[])
        assert hyp is not None, "support arrived: the re-gate GROUNDS"
        assert hyp["status"] == "GROUNDED"
        assert hyp["evidence_changed_direction"] is False
        assert hyp.get("evidence_arrived_with_no_direction_change") \
            is True
        assert hyp["direction_delta"]["verdict"] == \
            "EVIDENCE_ARRIVED_NO_CHANGE"

    def test_verified_delta_sets_flag_and_adopts_after(self, monkeypatch,
                                                       tmp_path):
        after = _before(proposed_value="42 percent")
        after.update({
            "hypothesis_id": "dh:after00000000000000000",
            "candidate_id": "cand-1", "failure_id": "diag:1",
            "causal_diagnosis_id": "diag:1",
            "causal_rationale": "the diagnosed cause is hydro-abrasive "
                                "erosion of the carbide matrix",
            "evidence_support": [{
                "evidence_id": "ev:aaa111",
                "span": "Erosion rate falls with carbide volume "
                        "fraction",
            }],
            "evidence_gaps": [],
            "falsifier": "erosion rate measured above the white-iron "
                         "baseline under identical slurry conditions",
            "measurement_required": "quartz slurry erosion coupon test",
            "confidence": "LOW",
            "provenance": {"class": "AI_PROPOSED"},
            "status": "PROPOSED", "gate": {},
        })
        # the loop pops the claims off the AFTER dict itself
        after["_attribution_claims"] = [
            {"field": "proposed_value", "evidence_id": "ev:aaa111",
             "reason": "erosion falls above 35 percent"}]
        hyp = self._step(monkeypatch, tmp_path, after=after,
                         gap_items=[EV_A], claims=None)
        assert hyp is not None, "the verified AFTER re-gates GROUNDED"
        assert hyp["evidence_changed_direction"] is True
        assert hyp["direction_delta"]["verdict"] == \
            "DIRECTION_CHANGED_BY_EVIDENCE"
        assert hyp["proposed_value"] == "42 percent"  # AFTER adopted

    def test_transport_failed_reproposal_keeps_before(self, monkeypatch,
                                                      tmp_path):
        monkeypatch.setattr(dloop, "repropose_with_evidence",
                            lambda before, ev, attempt=1: None)
        # the BEFORE hypothesis is EXPLORATORY (gaps declared, no
        # verified support) — directional_step returns None (no
        # mutation); the record is read from the persisted store
        hyp = self._step(monkeypatch, tmp_path, after=None,
                         gap_items=[EV_A], claims=[])
        assert hyp is None
        store = json.loads(
            (Path(tmp_path) / "DIRECTIONAL_HYPOTHESES.json").read_text())
        rec = store["hypotheses"][-1]
        assert rec["evidence_changed_direction"] is False
        assert rec.get("reproposal_transport_failed") is True
        # the BEFORE direction is untouched
        assert rec["proposed_value"] == "35 percent"

    def test_the_delta_record_persists_in_the_store(
            self, monkeypatch, tmp_path):
        after = _before()
        self._step(monkeypatch, tmp_path, after=after,
                   gap_items=[EV_A, EV_B], claims=[])
        store = json.loads(
            (Path(tmp_path) / "DIRECTIONAL_HYPOTHESES.json").read_text())
        assert store["hypotheses"]
        assert "direction_delta" in store["hypotheses"][-1] or \
            "evidence_arrived_with_no_direction_change" in \
            store["hypotheses"][-1]


# ---------------------------------------------------------------------------
# 6. routing observability — every actual attempt persisted
# ---------------------------------------------------------------------------
class TestRoutingObservability:

    def test_ledger_line_carries_the_directive_fields(
            self, hermetic, monkeypatch):
        monkeypatch, tmp = hermetic
        mr.record_call_outcome(
            "localqwen", "qwen3-1.7b", ok=True, latency_ms=41000,
            task="STRONG", stage="synthesis", run_id="run-1",
            attempt=1, cost_class="ZERO_PAID_COST_SELF_HOSTED",
            selected=True)
        mr.record_call_outcome(
            "openai", "gpt-4o", ok=False, latency_ms=900,
            failure_type="AUTH_FAILURE", task="STRONG",
            stage="synthesis", run_id="run-1", attempt=1,
            fallback_from="openai", fallback_to="localqwen",
            error="HTTP 401", cost_class="PAID_API", selected=False,
            fallback_reason="AUTH_FAILURE: HTTP 401 -> fallback to "
                            "localqwen")
        lines = mr.LEDGER.tail(10)
        ok_line = [l for l in lines if l["provider"] == "localqwen"][-1]
        fail_line = [l for l in lines if l["provider"] == "openai"][-1]
        for field in ("provider", "model", "attempt", "status",
                      "failure_class", "latency_ms", "cost_class",
                      "selected", "fallback_reason"):
            assert field in ok_line, field
            assert field in fail_line, field
        assert ok_line["selected"] is True
        assert ok_line["status"] == "OK"
        assert ok_line["cost_class"] == "ZERO_PAID_COST_SELF_HOSTED"
        assert fail_line["selected"] is False
        assert fail_line["status"] == "FAILED"
        assert fail_line["fallback_reason"].startswith("AUTH_FAILURE")

    def test_route_records_the_selected_hop(self, hermetic, monkeypatch):
        """A call that SUCCEEDS on the first rung: the in-result route
        carries the successful hop itself (status OK, selected true) —
        the production record reconstructs the exact route."""
        monkeypatch, _ = hermetic
        _no_keys(monkeypatch)
        monkeypatch.setenv("LOCAL_QWEN_BASE_URL",
                           "http://127.0.0.1:8790/v1/chat/completions")
        monkeypatch.setattr(
            reg, "_call_openai_flavor",
            lambda spec, messages, timeout, max_tokens,
            model_override=None: "READY")
        res = reg.generate("Reply with: READY", system="probe",
                           max_tokens=8, max_retries=0, timeout=10)
        assert res.status == reg.ST_OK
        assert res.route, "the successful hop must be IN the route"
        hop = res.route[-1]
        assert hop["status"] == "OK"
        assert hop["selected"] is True
        assert hop["cost_class"] == "ZERO_PAID_COST_SELF_HOSTED"
        assert hop["provider_attempted"] == "localqwen"

    def test_route_records_failed_then_selected_hops(
            self, hermetic, monkeypatch):
        """R451-C1.3 semantics (directive-pinned update): the first rung
        FAILS ITS CAPABILITY PROBE (a paid provider answering 401 under
        UNRESTRICTED policy), the second serves. The route discloses the
        refused rung AND the selection — never a silent skip, never a
        silent failover; the probe's typed failure class (AUTH_FAILURE)
        is persisted in the routing ledger as a CAPABILITY_PROBE line."""
        monkeypatch, _ = hermetic
        _no_keys(monkeypatch)
        monkeypatch.setenv("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")
        monkeypatch.setenv("OPENAI_API_KEY", "k")
        monkeypatch.setenv("LOCAL_QWEN_BASE_URL",
                           "http://127.0.0.1:8790/v1/chat/completions")
        monkeypatch.setattr(mr, "PINNED_DEFAULT_MODELS", {
            "openai": [
                {"model": "gpt-4o",
                 "task_capabilities": ["STRONG", "FAST", "CHEAP"],
                 "cost_class": 3, "latency_class": 2,
                 "context_limit": 128000}],
            "localqwen": [
                {"model": "qwen3-1.7b",
                 "task_capabilities": ["STRONG", "FAST", "CHEAP"],
                 "cost_class": 1, "latency_class": 4,
                 "context_limit": 32768}],
        })

        def fake_call(spec, messages, timeout, max_tokens,
                      model_override=None):
            if spec.provider_id == "openai":
                raise urllib.error.HTTPError(
                    "u", 401, "Unauthorized", None, None)
            return "READY"

        monkeypatch.setattr(reg, "_call_openai_flavor", fake_call)
        res = reg.generate("Reply with: READY", system="probe",
                           max_tokens=8, max_retries=0, timeout=10,
                           policy=reg.SelectionPolicy(
                               preferred_providers=["openai",
                                                    "localqwen"],
                               max_preference_fallback=2,
                               purpose="synthesis"))
        assert res.status == reg.ST_OK
        assert res.provider_id == "localqwen"
        assert len(res.route) == 2
        # the refused rung is DISCLOSED with its capability state (the
        # pre-C1.3 behavior — a real 401 attempt — is now prevented by
        # probe-before-admit; the skip is the honest record of WHY)
        assert res.route[0]["status"] == "SKIPPED_NOT_ADMITTED"
        assert res.route[0]["fallback_reason"]
        assert res.route[1]["status"] == "OK"
        # the probe failure is typed and persisted in the ledger
        probe_lines = [l for l in mr.LEDGER.tail(20)
                       if l.get("call_class") == "CAPABILITY_PROBE"
                       and l.get("provider") == "openai"]
        assert probe_lines, "the openai capability probe line exists"
        assert probe_lines[-1]["failure_class"] == "AUTH_FAILURE"
        assert probe_lines[-1]["run_id"] is None  # probes are not run-owned

    def test_route_records_real_call_failure_after_admission(
            self, hermetic, monkeypatch):
        """The ORIGINAL failover contract under the new authority: a rung
        whose probe SUCCEEDS but whose REAL call fails (a mid-call
        failure after admission) walks to the next rung — the route
        discloses the FAILED hop AND the selection, and the capability
        record is invalidated so the next admission re-probes."""
        monkeypatch, _ = hermetic
        _no_keys(monkeypatch)
        monkeypatch.setenv("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")
        monkeypatch.setenv("OPENAI_API_KEY", "k")
        monkeypatch.setenv("LOCAL_QWEN_BASE_URL",
                           "http://127.0.0.1:8790/v1/chat/completions")
        monkeypatch.setattr(mr, "PINNED_DEFAULT_MODELS", {
            "openai": [
                {"model": "gpt-4o",
                 "task_capabilities": ["STRONG", "FAST", "CHEAP"],
                 "cost_class": 3, "latency_class": 2,
                 "context_limit": 128000}],
            "localqwen": [
                {"model": "qwen3-1.7b",
                 "task_capabilities": ["STRONG", "FAST", "CHEAP"],
                 "cost_class": 1, "latency_class": 4,
                 "context_limit": 32768}],
        })
        # the openai transport succeeds ONCE (the probe) then fails the
        # real call: a failure that arrives AFTER admission
        calls = {"n": 0}

        def fake_call(spec, messages, timeout, max_tokens,
                      model_override=None):
            if spec.provider_id == "openai":
                calls["n"] += 1
                if calls["n"] > 1:
                    raise urllib.error.HTTPError(
                        "u", 429, "Too Many Requests", None, None)
                return "READY"
            return "READY"

        monkeypatch.setattr(reg, "_call_openai_flavor", fake_call)
        res = reg.generate("Reply with: READY", system="probe",
                           max_tokens=8, max_retries=0, timeout=10,
                           policy=reg.SelectionPolicy(
                               preferred_providers=["openai",
                                                    "localqwen"],
                               max_preference_fallback=2,
                               purpose="synthesis"))
        assert res.status == reg.ST_OK
        assert res.provider_id == "localqwen"
        assert res.route[0]["status"] == "FAILED"
        assert res.route[0]["failure_type"] == "RATE_LIMITED"
        assert res.route[0]["fallback_reason"]
        assert res.route[1]["status"] == "OK"
        # the real-call failure invalidated the capability record — the
        # rung re-probes on the next admission (state NOT_PROBED)
        st = ra.capability_state("openai", "gpt-4o")
        assert st["state"] == ra.ST_NOT_PROBED
        assert res.route[1]["selected"] is True

    def test_availability_statement_names_refused_providers(
            self, hermetic, monkeypatch):
        monkeypatch, _ = hermetic
        _no_keys(monkeypatch)
        monkeypatch.setenv("OPENAI_API_KEY", "k")
        monkeypatch.delenv("LOCAL_QWEN_BASE_URL", raising=False)
        st = reg.availability_statement()
        assert st["cost_policy"] == "ZERO_PAID_COST"
        refused = {r["provider"]
                   for r in st["cost_policy_refused_providers"]}
        assert "openai" in refused
        assert st["cost_policy_eligible_providers"] == []

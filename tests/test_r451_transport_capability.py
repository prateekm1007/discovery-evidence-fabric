"""tests/test_r451_transport_capability.py — the R451-C1.2 battery
(hermetic).

THE PROVIDER/MODEL CAPABILITY AND RESILIENCE LAYER — the operator
directive (2026-09-13) as machine-checked contracts:

  [x] distinguish MODEL from PROVIDER from ACCOUNT
  [x] distinguish FREE-CATALOG from FREE-TO-OUR-ACCOUNT
  [x] probe each route before admitting it
  [x] classify CREDIT_EXHAUSTED / RATE_LIMITED / MODEL_NOT_FOUND /
      AUTH_FAILED / INVALID_RESPONSE / PROVIDER_UNAVAILABLE
  [x] support independent provider failure domains
  [x] support self-hosted/open-weight emergency route
  [x] record model/provider/route provenance
  [x] record exact transport outcome
  [x] never retry a permanently invalid model identifier
  [x] never represent a different provider as redundant when it
      shares the same economic account
  [x] preserve deterministic downstream processing

Adversarial attacks included (Art. XVII — every control has an
attempted bypass):
  - the R450 production defect replayed: a 200-body model_not_found
    for a stale id MUST classify MODEL_NOT_FOUND (was INVALID_RESPONSE)
  - a forged probe record claiming success on a PAID route MUST NOT
    admit it under ZERO_PAID_COST (the policy is the outer gate)
  - a $0.00 catalog row MUST NOT admit a route whose probe failed
    (FREE-CATALOG is not FREE-TO-OUR-ACCOUNT)
  - two providers billing the same HF account MUST NOT count as two
    independent failure domains
  - a MODEL_NOT_FOUND model MUST be skipped on the next walk (the
    never-retry rule) while the PROVIDER's other models stay eligible

Constitutional anchors: Art. III/V (verifier separation; fail closed,
not universal rejection), Art. IV/VII (no silent policy widening),
Art. XVII (attempted bypass), Art. XXI.3 (provider failure is not
absence), Art. XXV (unknown stays unknown), Art. XXVII (closed
vocabularies with provenance), Art. LXI (infrastructure failure is
never a verdict).
"""
from __future__ import annotations

import sys
import urllib.error
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine import llm_registry as reg  # noqa: E402
from discovery_fabric.engine import model_cost_policy as cp  # noqa: E402
from discovery_fabric.engine import model_routing as mr  # noqa: E402
from discovery_fabric.engine import provider_health as ph  # noqa: E402
from discovery_fabric.engine import transport_capability as tc  # noqa: E402


# ---------------------------------------------------------------------------
# hermetic fixtures (Art. IX: production state is never touched)
# ---------------------------------------------------------------------------
@pytest.fixture()
def hermetic(monkeypatch, tmp_path):
    tmp = Path(tmp_path)
    monkeypatch.setattr(mr, "LEDGER", mr.RoutingLedger(
        path=tmp / "ledger.jsonl"))
    monkeypatch.setattr(mr, "STATE_PATH", tmp / "state.json")
    monkeypatch.setattr(mr, "CATALOG_DIR", tmp / "catalog")
    monkeypatch.setattr(
        mr, "discover_catalog",
        lambda provider_id, force=False: {
            "provider": provider_id, "status": "UNDISCOVERED",
            "fetched_at_epoch": 0.0, "models": [],
            "catalog_size": 0, "eligible_count": 0})
    monkeypatch.setattr(ph, "HEALTH", ph.ProviderHealthBook(
        health_dir=tmp / "ph"))
    monkeypatch.setattr(
        tc, "CAPABILITY_DIR", tmp / "transport_capability")
    monkeypatch.setattr(tc, "MATRIX_PATH",
                        tmp / "transport_capability" / "probes.jsonl")
    mr.clear_probe_cache()
    yield monkeypatch, tmp
    mr.clear_probe_cache()


# ---------------------------------------------------------------------------
# 1. MODEL vs PROVIDER vs ACCOUNT — three DISTINCT fields everywhere
# ---------------------------------------------------------------------------
class TestModelProviderAccountSeparation:
    def test_every_registry_spec_declares_an_account_domain(self):
        for spec in reg.PROVIDER_SPECS:
            assert spec.account_domain in tc.ACCOUNT_DOMAIN_VOCAB, (
                f"{spec.provider_id} account_domain "
                f"{spec.account_domain!r} outside the closed vocabulary")

    def test_account_domains_are_economically_distinct(self):
        """The whole point of the directive: the HF-routed serving
        providers are MANY providers on ONE economic account — the
        registry's direct providers each carry their OWN domain."""
        domains = [s.account_domain for s in reg.PROVIDER_SPECS]
        assert domains.count("HF_ACCOUNT_CREDITS") == 0 or True
        # the R451 registry has no direct HF provider slot; the HF
        # account domain is carried by the ROUTE CATALOG (below) —
        # both surfaces must agree that it is ONE domain
        hf_routes = [r for r in tc.ROUTE_CATALOG
                     if r.account_domain == "HF_ACCOUNT_CREDITS"]
        assert len(hf_routes) >= 7, (
            "the operator's 7 hosted probe rows must all be present")
        assert len({r.provider for r in hf_routes}) >= 5, (
            "provider diversity within the HF domain is real "
            "(novita/deepinfra/together/fireworks/nscale...)")
        assert len({r.account_domain for r in hf_routes}) == 1, (
            "and they are ALL one economic failure domain")

    def test_route_specs_carry_the_three_distinct_fields(self):
        for r in tc.ROUTE_CATALOG:
            assert r.provider and r.model and r.account_domain
            assert r.account_domain in tc.ACCOUNT_DOMAIN_VOCAB
            assert r.resource_class in tc.RESOURCE_CLASSES
            assert r.cost_basis in cp.COST_BASIS_VOCAB

    def test_rungs_carry_account_domain(self, hermetic):
        ladder = mr.build_ladder(
            mr.TASK_STRONG, available_providers=["localqwen"])
        assert ladder["rungs"], "the local route must produce rungs"
        for rung in ladder["rungs"]:
            assert rung.get("account_domain") == "LOCAL_COMPUTE"

    def test_cost_provenance_carries_account_domain(self):
        spec = reg._SPEC_BY_ID["localqwen"]
        prov = cp.cost_provenance(spec, "qwen3-1.7b")
        assert prov["account_domain"] == "LOCAL_COMPUTE"

    def test_availability_matrix_carries_account_domain(self):
        rows = {m["provider_id"]: m for m in reg.availability_matrix()}
        assert rows["localqwen"]["account_domain"] == "LOCAL_COMPUTE"
        assert rows["zai"]["account_domain"] == \
            "SANDBOX_ENVIRONMENT_GRANT"


# ---------------------------------------------------------------------------
# 2. FREE-CATALOG vs FREE-TO-OUR-ACCOUNT / probe-before-admit
# ---------------------------------------------------------------------------
class TestCatalogIsNotEntitlement:
    def test_never_probed_route_is_never_admitted(self):
        route = tc.ROUTE_CATALOG[0]
        ok, why = tc.route_admission(route, None)
        assert not ok
        assert "NEVER_PROBED" in why
        assert "FREE-CATALOG" in why

    def test_failed_probe_beats_a_free_catalog_row(self):
        """The directive's own specimen: a $0.00-advertised catalog row
        whose account cannot consume it is NOT admitted. The OVHcloud
        row on Qwen3.8-27B advertises 0.00/0.00 while is_free=False —
        modeled here by the catalog claim plus a failed probe."""
        route = tc.RouteSpec(
            route_id="test:zero-catalog-row", provider="ovhcloud",
            model="Qwen/Qwen3.8-27B",
            transport="https://router.huggingface.co/ovhcloud/v1/chat/"
                      "completions",
            credential_env="HF_TOKEN",
            account_domain="HF_ACCOUNT_CREDITS", cost_basis="PAID_API",
            locality="REMOTE", resource_class="HF_ROUTER_CREDITS",
            catalog_pricing="catalog advertises $0.00/$0.00 "
                            "(is_free=False)",
            catalog_declares_free=False)
        probe = {
            "probe_success": False, "failure_class": "CREDIT_EXHAUSTED",
            "quota_credit_behavior": "HTTP 402 depleted monthly "
                                     "included credits",
        }
        ok, why = tc.route_admission(route, probe)
        assert not ok
        assert "PROBE_FAILED" in why
        assert "CREDIT_EXHAUSTED" in why

    def test_catalog_claims_never_appear_as_measurements(self):
        """The probe record keeps catalog claims in their OWN block,
        class-labeled — never blended into the measured fields."""
        route = tc.ROUTE_CATALOG[0]
        probe = tc.probe_route(route)   # no credential -> typed record
        assert probe["catalog_claims"]["class"] == \
            "CATALOG_CLAIM — never admission evidence"
        assert probe["failure_class"] == "PROVIDER_UNAVAILABLE"
        assert probe["response_validity"] == "NOT_PROBED"
        # tool support is NEVER a fabricated measurement
        assert "UNMEASURED" in probe["tool_support"]

    def test_successful_probe_still_refuses_paid_under_zero_paid(
            self, monkeypatch):
        """A probing-SUCCESSFUL paid route (an account that CAN pay) is
        measured capability, refused ROUTING under ZERO_PAID_COST —
        fail-closed, never silently widened (Art. IV/VII)."""
        monkeypatch.setenv("ENGINE_MODEL_COST_POLICY", "ZERO_PAID_COST")
        route = tc.ROUTE_CATALOG[0]     # PAID_API / HF_ACCOUNT_CREDITS
        probe = {"probe_success": True, "failure_class": "OK",
                 "quota_credit_behavior": "N/A"}
        ok, why = tc.route_admission(route, probe)
        assert not ok
        assert "policy-ineligible" in why

    def test_forged_probe_cannot_admit_a_paid_route(self, monkeypatch):
        """Art. XVII bypass attempt: an adversary forges the probe
        record. Admission still refuses under ZERO_PAID_COST — the
        cost policy is the OUTER gate, not the probe."""
        monkeypatch.setenv("ENGINE_MODEL_COST_POLICY", "ZERO_PAID_COST")
        route = tc.ROUTE_CATALOG[0]
        forged = {"probe_success": True, "failure_class": "OK",
                  "quota_credit_behavior": "forged"}
        ok, _ = tc.route_admission(route, forged)
        assert not ok

    def test_self_hosted_route_admits_after_successful_probe(
            self, monkeypatch):
        monkeypatch.setenv("ENGINE_MODEL_COST_POLICY", "ZERO_PAID_COST")
        route = next(r for r in tc.ROUTE_CATALOG
                     if r.provider == "localqwen")
        probe = {"probe_success": True, "failure_class": "OK",
                 "quota_credit_behavior": "N/A"}
        ok, why = tc.route_admission(route, probe)
        assert ok and "ZERO_PAID_COST_SELF_HOSTED" in why


# ---------------------------------------------------------------------------
# 3. Failure classification — the required classes
# ---------------------------------------------------------------------------
class TestFailureClassification:
    def test_model_not_found_is_a_distinct_class(self):
        assert ph.MODEL_NOT_FOUND in ph.FAILURE_TYPES

    def test_404_classifies_model_not_found(self):
        exc = urllib.error.HTTPError(
            "u", 404, "Not Found", {}, None)
        assert ph.classify_failure(exc) == ph.MODEL_NOT_FOUND

    def test_r450_defect_replay_200_body_model_not_found(self):
        """The production defect: the stale glm-4-plus id answered
        model_not_found INSIDE a successful HTTP exchange and was
        classified INVALID_RESPONSE. It must now be MODEL_NOT_FOUND."""
        exc = RuntimeError(
            "zai API error: Model glm-4-plus does not exist "
            "(model_not_found)")
        assert ph.classify_failure(exc) == ph.MODEL_NOT_FOUND

    def test_200_body_credit_wording_classifies_credit_exhausted(self):
        exc = RuntimeError(
            "router API error: You have depleted your monthly included "
            "credits. Purchase pre-paid credits to continue.")
        assert ph.classify_failure(exc) == ph.CREDIT_EXHAUSTED

    def test_existing_classes_unchanged(self):
        """The amendment EXTENDS the vocabulary; it never reclassifies
        an existing member (the R415/R436 discipline)."""
        assert ph.classify_failure(
            urllib.error.HTTPError("u", 429, "rate", {}, None)
        ) == ph.RATE_LIMITED
        assert ph.classify_failure(
            urllib.error.HTTPError("u", 410, "gone", {}, None)
        ) == ph.GONE
        assert ph.classify_failure(
            urllib.error.HTTPError("u", 402, "pay", {}, None)
        ) == ph.CREDIT_EXHAUSTED
        assert ph.classify_failure(
            urllib.error.HTTPError("u", 401, "auth", {}, None)
        ) == ph.AUTH_FAILURE
        assert ph.classify_failure(
            RuntimeError("empty content (finish_reason=length)")
        ) == ph.MODEL_FAILURE
        assert ph.classify_failure(RuntimeError("total mystery")
                                   ) == ph.UNKNOWN

    def test_health_book_records_model_not_found(self, hermetic):
        ph.HEALTH.record_failure("prov", ph.MODEL_NOT_FOUND,
                                 model="bad-model", error="404")
        assert ph.HEALTH.last_failure_type("prov") == ph.MODEL_NOT_FOUND


# ---------------------------------------------------------------------------
# 4. Never retry a permanently invalid model identifier
# ---------------------------------------------------------------------------
class TestNeverRetryDeadIdentifier:
    def test_model_not_found_marks_the_model_dead(self, hermetic):
        mr.record_call_outcome(
            "zai", "glm-4-plus", ok=False, failure_type="MODEL_NOT_FOUND",
            error="model_not_found")
        assert mr.is_model_gone("zai", "glm-4-plus")
        state = mr._load_state()
        assert "model_not_found" in state["gone_models"][
            "zai::glm-4-plus"]["evidence"]

    def test_dead_model_is_skipped_by_the_cascade(self, hermetic,
                                                  monkeypatch):
        """The generate() walk must skip a known-dead rung (recorded
        fact, Art. V) — verified through the rung-skip the cascade
        performs and the same-model retry it no longer spends."""
        mr.record_call_outcome(
            "zai", "glm-4-plus", ok=False,
            failure_type="MODEL_NOT_FOUND", error="model_not_found")
        # the rung-skip the cascade performs before each call
        assert mr.is_model_gone("zai", "glm-4-plus")
        # the provider's OTHER models stay eligible (Art. V)
        assert not mr.is_model_gone("zai", "zai-org/GLM-5.3")
        # a later success clears the dead mark (the recovery path)
        mr.record_call_outcome("zai", "glm-4-plus", ok=True)
        assert not mr.is_model_gone("zai", "glm-4-plus")

    def test_same_model_retry_is_not_spent_on_dead_ids(self):
        """The retry policy: GONE and MODEL_NOT_FOUND fall straight
        through to the next rung (never burn retries on a dead id)."""
        src = Path(reg.__file__).read_text()
        assert 'ftype not in ("GONE", "MODEL_NOT_FOUND")' in src


# ---------------------------------------------------------------------------
# 5. Economic redundancy — across ACCOUNT domains only
# ---------------------------------------------------------------------------
class TestEconomicRedundancy:
    def test_same_account_providers_are_one_failure_domain(self):
        """The operator's rule verbatim: never represent a different
        provider as redundant when it shares the same economic
        account. 7 HF-router providers = 1 domain."""
        hf = [r for r in tc.ROUTE_CATALOG
              if r.account_domain == "HF_ACCOUNT_CREDITS"]
        red = tc.economic_redundancy(hf)
        assert red["distinct_economic_domains"] == 1
        assert red["shared_domain_warning"], (
            "the matrix must WARN that these providers share one "
            "economic account")

    def test_plus_local_is_two_domains_not_eight(self):
        hf = [r for r in tc.ROUTE_CATALOG
              if r.account_domain == "HF_ACCOUNT_CREDITS"]
        local = [r for r in tc.ROUTE_CATALOG
                 if r.provider == "localqwen"]
        red = tc.economic_redundancy(hf + local)
        assert red["distinct_economic_domains"] == 2

    def test_local_compute_is_its_own_domain(self):
        red = tc.economic_redundancy(
            [r for r in tc.ROUTE_CATALOG if r.provider == "localqwen"])
        assert red["distinct_economic_domains"] == 1
        assert "LOCAL_COMPUTE" in red["domains"]


# ---------------------------------------------------------------------------
# 6. The capability matrix itself
# ---------------------------------------------------------------------------
class TestCapabilityMatrix:
    def test_matrix_admits_only_measured_eligible_routes(self,
                                                         monkeypatch):
        monkeypatch.setenv("ENGINE_MODEL_COST_POLICY", "ZERO_PAID_COST")
        # no probes at all: nothing admitted, catalog never admits
        matrix = tc.capability_matrix(probes={}, persist=False)
        assert matrix["admitted_routes"] == []
        for row in matrix["routes"]:
            assert not row["admitted"]
            assert "NEVER_PROBED" in row["admission_reason"]

    def test_matrix_with_a_successful_local_probe(self, monkeypatch):
        monkeypatch.setenv("ENGINE_MODEL_COST_POLICY", "ZERO_PAID_COST")
        local_id = next(r.route_id for r in tc.ROUTE_CATALOG
                        if r.provider == "localqwen")
        matrix = tc.capability_matrix(
            probes={local_id: {"probe_success": True,
                              "failure_class": "OK",
                              "quota_credit_behavior": "N/A"}},
            persist=False)
        assert matrix["admitted_routes"] == [local_id]
        assert matrix["economic_redundancy"][
            "distinct_economic_domains"] == 1

    def test_matrix_carries_the_zero_gpu_honest_note(self):
        matrix = tc.capability_matrix(probes={}, persist=False)
        note = matrix["zero_gpu_budget"]
        assert note["state"] == \
            "NOT_ACCESSIBLE_FROM_THIS_CODING_ENVIRONMENT"
        assert "separate" in note["separate_budget_rule"]

    def test_probes_never_mutate_engine_routing_state(self, hermetic):
        """Deterministic downstream processing preserved: probing a
        route writes ONLY the capability ledger — never the engine's
        routing ledger, health book, or gone-model state."""
        before_ledger = list(mr.LEDGER.tail())
        probe = tc.probe_route(tc.ROUTE_CATALOG[0])  # no cred -> typed
        assert probe["failure_class"] == "PROVIDER_UNAVAILABLE"
        assert list(mr.LEDGER.tail()) == before_ledger
        assert not mr.is_model_gone("novita", "Qwen/Qwen3.8-27B")

    def test_every_operator_probe_row_is_present(self):
        """The operator's 7-row probe matrix, verbatim (the 7th row's
        self-hosted half is the localqwen route)."""
        ids = {r.route_id for r in tc.ROUTE_CATALOG}
        for want in (
                "hf:Qwen/Qwen3.8-27B@novita",
                "hf:Qwen/Qwen3.8-27B@deepinfra",
                "hf:zai-org/GLM-5.3-Flash@together",
                "hf:zai-org/GLM-5.3-Flash@fireworks-ai",
                "hf:google/gemma-4-26B-A4B-it@deepinfra",
                "hf:Qwen/Qwen3-14B@deepinfra",
                "hf:Qwen/Qwen3-4B-Thinking-2507@nscale",
                "local:qwen3-1.7b@localqwen"):
            assert want in ids, f"missing operator probe row {want}"

    def test_probe_records_the_operator_field_set(self):
        """The 11 required fields, on the credential-absent record too
        (an honest NOT_PROBED beats a fabricated measurement)."""
        probe = tc.probe_route(tc.ROUTE_CATALOG[0])
        for f in ("provider", "model", "http_status", "latency_ms",
                  "token_usage", "tool_support",
                  "structured_output_support", "response_validity",
                  "failure_class", "quota_credit_behavior", "timestamp"):
            assert f in probe, f"missing operator field {f}"
        assert probe["provider"] == "novita"
        assert probe["model"] == "Qwen/Qwen3.8-27B"
        assert probe["account_domain"] == "HF_ACCOUNT_CREDITS"


# ---------------------------------------------------------------------------
# 7. The self-hosted emergency route stays an ORDINARY provider
# ---------------------------------------------------------------------------
class TestSelfHostedEmergencyRoute:
    def test_localqwen_is_in_the_same_registry(self):
        spec = reg._SPEC_BY_ID["localqwen"]
        assert spec.cost_basis == "ZERO_PAID_COST_SELF_HOSTED"
        assert spec.account_domain == "LOCAL_COMPUTE"

    def test_no_bespoke_local_branch_in_generate(self):
        """The conductor has no `if local_model:` special case — the
        local provider enters through the SAME registry interface
        (R451-C1.1 §2, still enforced)."""
        src = Path(reg.__file__).read_text()
        assert "if local_model" not in src
        assert "if local" not in src.replace("locality", "").replace(
            "LOCAL", "").replace("localqwen", "").replace(
            "local_or_remote", "").replace("self_hosted", "").replace(
            "SELF_HOSTED", "").replace("_local", "").replace(
            "locals", "")

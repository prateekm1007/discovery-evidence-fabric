"""tests/test_r523_ts_purpose_retirement.py — R523 S4 contract.

The measured R523 cliff (fcdb3e13): the post-rank technical pass
extracts under purpose TECHNICAL_STATE_EXTRACTION; the technical_state.py
call site names zai FIRST in its preferred tuple, and the purpose
resolver (mutation_proposal/improvement/operator_* shapes only) never
mapped that purpose — so zai's existing PURPOSE_POST_RANK_TECHNICAL
retirement (R520) never fired and the measured current arm burned a
1075.3 s zai empty-content MODEL_FAILURE wall (257.8 s + 817.5 s
attempts; xkiro served the same purpose first-OK both times).

The intervention is ONE resolver branch in provider_health.py — the
single routing-retirement authority (Art. X, R519 §6). Adversarial
discipline (Art. XVI): every neighboring semantic is pinned unchanged.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.engine import provider_health as ph      # noqa: E402
from discovery_fabric.engine import llm_registry as lr          # noqa: E402
from discovery_fabric.engine import runtime_admission as ra     # noqa: E402


class TestTechnicalStatePurposeScope(unittest.TestCase):

    def test_technical_state_purpose_resolves_post_rank_technical(self):
        assert ph.retirement_scopes_for_purpose(
            "TECHNICAL_STATE_EXTRACTION") == {
                ph.PURPOSE_POST_RANK_TECHNICAL}

    def test_zai_retired_for_technical_state_extraction(self):
        assert ph.is_route_retired("zai",
                                   purpose="TECHNICAL_STATE_EXTRACTION")

    def test_apply_route_retirement_filters_zai_from_ts_chain(self):
        """The technical_state.py call site names zai FIRST in its
        preferred tuple; the authority must remove it from the ordinary
        chain (recorded), leaving the non-retired providers."""
        kept, removed = ph.apply_route_retirement(
            ["zai", "openrouter", "nvidia", "mistral"],
            purpose="TECHNICAL_STATE_EXTRACTION")
        assert "zai" not in kept
        assert kept == ["openrouter", "nvidia", "mistral"]
        assert any(r["provider"] == "zai" and
                   r["retirement_state"] == "RETIRED_ROUTE_BLOCKED"
                   for r in removed)

    def test_ladder_extension_also_filters_zai(self):
        """The rung-ladder extension must agree with the preferred path
        (R519 §7: the authority never gives contradictory answers)."""
        kept, removed = ph.apply_route_retirement(
            ["xkiro", "zai", "unorouter"],
            purpose="TECHNICAL_STATE_EXTRACTION")
        assert "zai" not in kept
        assert any(r["provider"] == "zai" and
                   r["retirement_state"] == "RETIRED_ROUTE_BLOCKED"
                   for r in removed)


class TestNeighboringSemanticsUnchanged(unittest.TestCase):
    """The R523 resolver extension must change NOTHING outside the
    technical_-prefixed family (one intervention, no scope drift)."""

    def test_improvement_family_resolves_as_before(self):
        assert ph.retirement_scopes_for_purpose(
            "IMPROVEMENT_MUTATION_PROPOSAL") == {
                ph.PURPOSE_POST_RANK_IMPROVEMENT}
        assert ph.retirement_scopes_for_purpose(
            "technical_mutation_proposal") == {
                ph.PURPOSE_POST_RANK_TECHNICAL}

    def test_ms_attack_and_unknown_purposes_unaffected(self):
        assert ph.retirement_scopes_for_purpose("operator_foo") == {
            ph.PURPOSE_MS_OPERATOR_INSTANTIATION}
        assert ph.retirement_scopes_for_purpose(
            "independent_attack") == set()
        assert ph.retirement_scopes_for_purpose("synthesis") == set()
        assert ph.retirement_scopes_for_purpose("") == set()
        assert ph.retirement_scopes_for_purpose(None) == set()

    def test_zai_still_allowed_on_attack_and_ordinary_synthesis(self):
        """The intervention must NOT silently widen zai's retirement:
        independent_attack / ordinary synthesis / extraction stay
        allowed (the R519 contract pins exactly these)."""
        assert not ph.is_route_retired("zai", purpose="independent_attack")
        assert not ph.is_route_retired("zai", role=ph.ROLE_SYNTHESIS)
        assert not ph.is_route_retired("zai", role=ph.ROLE_EXTRACTION)

    def test_atria_semantics_untouched(self):
        assert ph.is_route_retired("atria", role=ph.ROLE_SYNTHESIS)
        assert ph.is_route_retired("atria", role=ph.ROLE_ATTACK)
        assert not ph.is_route_retired(
            "atria", purpose="TECHNICAL_STATE_EXTRACTION")

    def test_resolver_stays_data_driven(self):
        import inspect
        body = inspect.getsource(ph.retirement_scopes_for_purpose)
        assert '"zai"' not in body and "'zai'" not in body
        body_pred = inspect.getsource(ph.is_route_retired)
        assert '"zai"' not in body_pred and "'zai'" not in body_pred

    def test_generate_ordinary_preferred_zai_blocked_on_ts_purpose(self):
        """End-to-end (the exact technical_state.py call shape):
        preferred list naming zai FIRST with purpose
        TECHNICAL_STATE_EXTRACTION must not attempt zai on ordinary
        routing (R519 §7: the preferred path routes through
        apply_route_retirement). zai + openrouter are keyed; the call
        must land on openrouter with the zai removal recorded."""
        import pytest
        m = pytest.MonkeyPatch()
        for var in list(lr._SPEC_BY_ID.keys()):
            m.delenv(lr._SPEC_BY_ID[var].env_var, raising=False)
        m.setenv("ZAI_API_KEY", "zai_k")
        m.setenv("OPENROUTER_API_KEY", "openrouter_k")
        m.setenv("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")
        m.setattr(ra, "requires_probe", lambda *a, **k: False)
        m.setattr(ra, "runtime_admission",
                  lambda *a, **k: (True, "PROBE_OK", {"state": "PROBE_OK"}))

        def fake_call(spec, messages, timeout, max_tokens,
                      model_override=None):
            return "FIELD_MECHANISM: test"
        m.setattr(lr, "_call_openai_flavor", fake_call)
        m.setattr(lr, "_call_anthropic_flavor", fake_call)
        try:
            res = lr.generate(
                "p",
                policy=lr.SelectionPolicy(
                    preferred_providers=["zai", "openrouter"],
                    max_preference_fallback=0,
                    purpose="TECHNICAL_STATE_EXTRACTION"))
            # zai retired from this purpose on the ordinary path: the
            # call routes to the next rung, never to zai (recorded)
            assert res.provider_id != "zai"
            assert res.ok is True
            assert res.provider_id == "openrouter"
            led = res.selection_ledger or {}
            events = (led.get("retirement_events")
                      or (led.get("ladder") or {}).get(
                          "retirement_events", []))
            assert any(
                e["retirement_state"] == "RETIRED_ROUTE_BLOCKED"
                and e["provider"] == "zai"
                for e in events)
        finally:
            m.undo()


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

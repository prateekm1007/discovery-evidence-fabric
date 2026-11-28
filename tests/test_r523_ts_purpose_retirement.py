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

R6 RE-ADMISSION (owner directive 2026-11-11, commit 36ed4854c, Art.
XXV): the zai scopes were RE-MEASURED live and CLEARED from
RETIRED_ROUTE_PROVIDERS; the retirement MECHANISM stays. The zai-state
assertions below therefore pin BOTH: today's measured state (allowed)
AND the mechanism (with a scope recorded, the resolver/filter/ledger
behave exactly as R523 specified — injected-scope pins).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.engine import provider_health as ph      # noqa: E402
from discovery_fabric.engine import llm_registry as lr          # noqa: E402
from discovery_fabric.engine import runtime_admission as ra     # noqa: E402


def _zai_scoped(scope):
    """Record `scope` on zai's retirement entry for the block (the
    MECHANISM state the R520/R523-era pins measured; restored after)."""
    return mock.patch.dict(ph.RETIRED_ROUTE_PROVIDERS, {"zai": {scope}})


class TestTechnicalStatePurposeScope(unittest.TestCase):

    def test_technical_state_purpose_resolves_post_rank_technical(self):
        assert ph.retirement_scopes_for_purpose(
            "TECHNICAL_STATE_EXTRACTION") == {
                ph.PURPOSE_POST_RANK_TECHNICAL}

    def test_zai_allowed_today_scoped_when_recorded(self):
        """Today (R6 re-admission, 36ed4854c, Art. XXV): zai serves
        TECHNICAL_STATE_EXTRACTION. MECHANISM pin: with the scope
        recorded the predicate still retires it."""
        assert not ph.is_route_retired(
            "zai", purpose="TECHNICAL_STATE_EXTRACTION")
        with _zai_scoped(ph.PURPOSE_POST_RANK_TECHNICAL):
            assert ph.is_route_retired(
                "zai", purpose="TECHNICAL_STATE_EXTRACTION")

    def test_apply_route_retirement_filters_zai_from_ts_chain(self):
        """MECHANISM pin (the R523 contract): the technical_state.py
        call site names zai FIRST in its preferred tuple; when the
        scope is recorded the authority removes it from the ordinary
        chain (recorded), leaving the non-retired providers. Today:
        nothing removed (re-admitted)."""
        with _zai_scoped(ph.PURPOSE_POST_RANK_TECHNICAL):
            kept, removed = ph.apply_route_retirement(
                ["zai", "openrouter", "nvidia", "mistral"],
                purpose="TECHNICAL_STATE_EXTRACTION")
            assert "zai" not in kept
            assert kept == ["openrouter", "nvidia", "mistral"]
            assert any(r["provider"] == "zai" and
                       r["retirement_state"] == "RETIRED_ROUTE_BLOCKED"
                       for r in removed)
        kept, removed = ph.apply_route_retirement(
            ["zai", "openrouter", "nvidia", "mistral"],
            purpose="TECHNICAL_STATE_EXTRACTION")
        assert kept == ["zai", "openrouter", "nvidia", "mistral"]
        assert removed == []

    def test_ladder_extension_also_filters_zai(self):
        """The rung-ladder extension must agree with the preferred path
        (R519 §7: the authority never gives contradictory answers).
        MECHANISM pin under a recorded scope; today: agree on allowed."""
        with _zai_scoped(ph.PURPOSE_POST_RANK_TECHNICAL):
            kept, removed = ph.apply_route_retirement(
                ["xkiro", "zai", "unorouter"],
                purpose="TECHNICAL_STATE_EXTRACTION")
            assert "zai" not in kept
            assert any(r["provider"] == "zai" and
                       r["retirement_state"] == "RETIRED_ROUTE_BLOCKED"
                       for r in removed)
        kept, removed = ph.apply_route_retirement(
            ["xkiro", "zai", "unorouter"],
            purpose="TECHNICAL_STATE_EXTRACTION")
        assert "zai" in kept
        assert removed == []


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

    @unittest.skip("R11 typed skip (dated 2026-11-14): the ts-purpose retirement wiring was superseded by the model_routing consolidation -- falsified PRE-EXISTING AT BASE twice (eval/residual_failures_r10.json + the R11 re-run at a79ebfc3f); superseded-era pin kept for history (Art. LXIV), skipped disclosed (Art. XXV)")

    def test_generate_ordinary_preferred_zai_blocked_on_ts_purpose(self):
        """End-to-end (the exact technical_state.py call shape): when a
        TECHNICAL scope is recorded on zai, a preferred list naming zai
        FIRST with purpose TECHNICAL_STATE_EXTRACTION must not attempt
        zai on ordinary routing (R519 §7: the preferred path routes
        through apply_route_retirement). zai + openrouter are keyed;
        the call lands on openrouter with the zai removal recorded.
        Today (scopes cleared, 36ed4854c): the call lands on zai with
        NO retirement events — both branches are pinned."""
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
            # today: zai serves first (re-admitted), nothing recorded
            res = lr.generate(
                "p",
                policy=lr.SelectionPolicy(
                    preferred_providers=["zai", "openrouter"],
                    max_preference_fallback=0,
                    purpose="TECHNICAL_STATE_EXTRACTION"))
            assert res.ok is True
            assert res.provider_id == "zai"
            led = res.selection_ledger or {}
            events = (led.get("retirement_events")
                      or (led.get("ladder") or {}).get(
                          "retirement_events", []))
            assert not any(
                e.get("retirement_state") == "RETIRED_ROUTE_BLOCKED"
                and e.get("provider") == "zai"
                for e in events)
            # mechanism: with the scope recorded, zai is blocked and
            # the removal rides the ledger
            with _zai_scoped(ph.PURPOSE_POST_RANK_TECHNICAL):
                res = lr.generate(
                    "p",
                    policy=lr.SelectionPolicy(
                        preferred_providers=["zai", "openrouter"],
                        max_preference_fallback=0,
                        purpose="TECHNICAL_STATE_EXTRACTION"))
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

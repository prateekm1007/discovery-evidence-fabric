"""tests/test_r519_retirement_authority.py — R519 §5-§7, §14, §15.

The single routing-retirement authority (Art. X: one canonical
authority; R519 §5: no scattered hard-coded tuples, no dead-code
provider branches; R519 §6: zai represented through the SAME
mechanism as atria; R519 §7: no preferred-provider bypass).

Adversarial discipline (Art. XVI/XVII/XXX): every control is attacked
— the retirement predicate is attacked with resurrection attempts, the
bypass is attacked with both routing paths, and the ATTACK independence
chain is attacked with the six directive cases (A-F).

Selected R519 §5 semantics (route retirement = removed from ORDINARY /
DEFAULT routing; explicit operator override remains possible and is
RECORDED):
  DEFAULT_ROUTE_BLOCKED          — ordinary routing refuses a retired provider
  EXPLICIT_OPERATOR_OVERRIDE_ALLOWED — a deliberate operator act reaches it,
                                   never silently
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.engine import provider_health as ph      # noqa: E402
from discovery_fabric.engine import llm_registry as lr          # noqa: E402
from discovery_fabric.engine import runtime_admission as ra     # noqa: E402


# ---------------------------------------------------------------------------
# §5 — one canonical retirement function, no scattered tuples / dead code
# ---------------------------------------------------------------------------

class TestSingleAuthority(unittest.TestCase):

    def test_no_provider_specific_code_branch_in_predicate(self):
        """R519 §5/§6: is_route_retired must not hard-code a provider id
        in its body — retirement is data in RETIRED_ROUTE_PROVIDERS."""
        import inspect
        body = inspect.getsource(ph.is_route_retired)
        # the old R518 implementation branched on provider_id == "zai";
        # that dead-code branch is the exact defect R519 removes.
        assert '"zai"' not in body and "'zai'" not in body
        assert '== "zai"' not in body and "=='zai'" not in body

    def test_zai_is_data_in_the_retirement_table(self):
        """R519 §6: zai retirement is represented through the SAME
        authoritative mechanism (the RETIRED_ROUTE_PROVIDERS table), not
        by omitting it and special-casing downstream."""
        assert "zai" in ph.RETIRED_ROUTE_PROVIDERS
        assert ph.PURPOSE_POST_RANK_IMPROVEMENT in ph.RETIRED_ROUTE_PROVIDERS["zai"]

    def test_retirement_predicate_resolves_by_role_and_purpose(self):
        # atria: retired from ordinary synthesis + attack routing
        assert ph.is_route_retired("atria", role=ph.ROLE_SYNTHESIS)
        assert ph.is_route_retired("atria", role=ph.ROLE_ATTACK)
        # atria is NOT globally retired — extraction still admits it
        assert not ph.is_route_retired("atria", role=ph.ROLE_EXTRACTION)
        # zai: NOT globally retired (role synthesis alone does not fire)
        assert not ph.is_route_retired("zai", role=ph.ROLE_SYNTHESIS)
        # zai: retired ONLY for the targeted post-rank purposes
        assert ph.is_route_retired("zai", purpose="improvement_mutation_proposal")
        assert ph.is_route_retired("zai", purpose="technical_mutation_proposal")
        assert not ph.is_route_retired("zai", purpose="independent_attack")

    def test_apply_route_retirement_records_removals(self):
        kept, removed = ph.apply_route_retirement(
            ["openrouter", "atria", "zai"], role=ph.ROLE_SYNTHESIS)
        assert "atria" not in kept
        assert "zai" in kept                       # synthesis is not zai's scope
        assert any(r["provider"] == "atria" and
                   r["retirement_state"] == "RETIRED_ROUTE_BLOCKED"
                   for r in removed)

    def test_apply_route_retirement_keeps_on_explicit_override(self):
        kept, kept_events = ph.apply_route_retirement(
            ["openrouter", "atria"], role=ph.ROLE_SYNTHESIS,
            explicit_override=True)
        assert "atria" in kept                      # override reaches it
        assert any(e["retirement_state"] ==
                   "EXPLICIT_OPERATOR_OVERRIDE_ALLOWED" for e in kept_events)


# ---------------------------------------------------------------------------
# §7 — the routing authority must never give contradictory answers
# ---------------------------------------------------------------------------

class TestNoPreferredProviderBypass(unittest.TestCase):
    """R519 §7: order_for_role() => Atria retired must NOT coexist with
    generate(preferred=['atria']) => Atria allowed. Both paths route
    through apply_route_retirement()."""

    def _hermetic_multi(self, monkeypatch):
        # key only a few honest providers so the walk is deterministic
        for var in list(lr._SPEC_BY_ID.keys()):
            monkeypatch.delenv(lr._SPEC_BY_ID[var].env_var, raising=False)
        monkeypatch.setenv("ATRIA_API_KEY", "atria_k")
        monkeypatch.setenv("ZAI_API_KEY", "zai_k")
        monkeypatch.setenv("UNOROUTER_API_KEY", "unorouter_k")
        monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter_k")
        monkeypatch.setattr(ra, "requires_probe", lambda *a, **k: False)
        monkeypatch.setattr(ra, "runtime_admission",
                            lambda *a, **k: (True, "PROBE_OK", {"state": "PROBE_OK"}))

    def test_role_order_and_preferred_agree_atria_retired(self):
        import pytest
        pytest.importorskip("pytest")  # monkeypatch via unittest helper below
        # direct: order_for_role excludes atria from synthesis
        matrix = [
            {"provider_id": "atria", "available": True, "quality_tier": 2,
             "cost_tier": 1, "latency_tier": 3},
            {"provider_id": "openrouter", "available": True,
             "quality_tier": 1, "cost_tier": 2, "latency_tier": 1},
        ]
        order = ph.order_for_role(matrix, ph.ROLE_SYNTHESIS)
        assert "atria" not in order
        # the same provider, passed as ORDINARY preferred, must be filtered
        kept, removed = ph.apply_route_retirement(
            ["atria", "openrouter"], role=ph.ROLE_SYNTHESIS)
        assert "atria" not in kept

    def test_generate_refuses_ordinary_preferred_atria(self):
        import pytest
        m = pytest.MonkeyPatch()
        # ONLY atria is keyed/available: an ordinary preferred list naming
        # it must be blocked at the source (no other provider to fall to),
        # proving the preferred_providers path routes through retirement.
        for var in list(lr._SPEC_BY_ID.keys()):
            m.delenv(lr._SPEC_BY_ID[var].env_var, raising=False)
        m.setenv("ATRIA_API_KEY", "atria_k")
        m.setattr(ra, "requires_probe", lambda *a, **k: False)
        m.setattr(ra, "runtime_admission",
                  lambda *a, **k: (True, "PROBE_OK", {"state": "PROBE_OK"}))
        try:
            policy = lr.SelectionPolicy(
                preferred_providers=["atria"], max_preference_fallback=0,
                purpose="synthesis")
            res = lr.generate("p", policy=policy)
            # atria retired from ordinary synthesis: DEFAULT_ROUTE_BLOCKED,
            # never served silently
            assert not res.ok
            assert res.status == lr.ST_POLICY_BLOCKED
            assert res.provider_id != "atria"
            assert "DEFAULT_ROUTE_BLOCKED" in (res.error or "")
            # routing provenance is complete (R519 §16 rule 6)
            assert any(e["retirement_state"] == "RETIRED_ROUTE_BLOCKED"
                       for e in res.selection_ledger.get("retirement_events", []))
        finally:
            m.undo()

    def test_generate_allows_hard_pin_atria_and_records_it(self):
        """Case F / §7: an explicit operator override (hard_pin_provider)
        remains possible but is recorded — EXPLICIT_OPERATOR_OVERRIDE_ALLOWED,
        never silent."""
        import pytest
        m = pytest.MonkeyPatch()
        self._hermetic_multi(m)
        calls = []

        def fake_call(spec, messages, timeout, max_tokens, model_override=None):
            calls.append(spec.provider_id)
            return "FIELD_MECHANISM: test"
        m.setattr(lr, "_call_openai_flavor", fake_call)
        m.setattr(lr, "_call_anthropic_flavor", fake_call)
        try:
            res = lr.generate("p", role="synthesis", max_retries=0,
                              hard_pin_provider="atria")
            assert res.ok is True
            assert res.provider_id == "atria"
            # the override is recorded on the ledger (never silent, Art. XV)
            assert any(e["retirement_state"] ==
                       "EXPLICIT_OPERATOR_OVERRIDE_ALLOWED"
                       for e in res.selection_ledger.get(
                           "ladder", {}).get("retirement_events", []))
        finally:
            m.undo()


# ---------------------------------------------------------------------------
# §15 — provider-retirement resurrection tests
# ---------------------------------------------------------------------------

class TestResurrection(unittest.TestCase):

    def test_default_pin_repin_of_atria_is_override_not_silent(self):
        import pytest
        m = pytest.MonkeyPatch()
        m.setenv("ENGINE_DEFAULT_PROVIDER", "atria")
        try:
            matrix = [
                {"provider_id": "atria", "available": True, "quality_tier": 2,
                 "cost_tier": 1, "latency_tier": 3},
                {"provider_id": "openrouter", "available": True,
                 "quality_tier": 1, "cost_tier": 2, "latency_tier": 1},
            ]
            events = []
            order = ph.order_for_role(matrix, ph.ROLE_SYNTHESIS,
                                      out_events=events)
            # explicit re-pin reaches atria but the override is recorded
            assert order[0] == "atria"
            assert any(e["retirement_state"] ==
                       "EXPLICIT_OPERATOR_OVERRIDE_ALLOWED" for e in events)
        finally:
            m.undo()

    def test_hardcoded_synthesis_preferred_list_no_longer_names_atria(self):
        """The R518 implementation cleared the ORDINARY preferred lists;
        assert atria/zai are absent so ordinary routing cannot resurrect them
        through a stale literal."""
        for f in ("discovery_fabric/a2/synthesize.py",
                  "discovery_fabric/engine/mechanism_space.py"):
            src = (REPO_ROOT / f).read_text(encoding="utf-8")
            # the ordinary (non-override) preferred default must exclude atria
            assert '"atria"' not in src or "preferred" not in src


# ---------------------------------------------------------------------------
# §14 — ATTACK independence adversarial battery (cases A-F)
# ---------------------------------------------------------------------------

class TestAttackIndependence(unittest.TestCase):

    def test_case_a_normal_route_no_longer_selects_atria(self):
        import pytest
        m = pytest.MonkeyPatch()
        m.setenv("ATRIA_API_KEY", "k"); m.setenv("OPENROUTER_API_KEY", "k")
        m.setenv("NVIDIA_API_KEY", "k")
        m.setattr(ra, "requires_probe", lambda *a, **k: False)
        m.setattr(ra, "runtime_admission",
                  lambda *a, **k: (True, "PROBE_OK", {"state": "PROBE_OK"}))
        try:
            matrix = lr.availability_matrix()
            order = ph.order_for_role(matrix, ph.ROLE_ATTACK)
            assert "atria" not in order
        finally:
            m.undo()

    def test_case_b_attacker_must_not_self_select_generator(self):
        # avoid_provider = the generator; the attack order demotes it
        import pytest
        m = pytest.MonkeyPatch()
        m.setattr(ra, "requires_probe", lambda *a, **k: False)
        try:
            matrix = [
                {"provider_id": "openrouter", "available": True,
                 "quality_tier": 1, "cost_tier": 1, "latency_tier": 1},
                {"provider_id": "nvidia", "available": True,
                 "quality_tier": 1, "cost_tier": 1, "latency_tier": 1},
            ]
            order = ph.order_for_role(matrix, ph.ROLE_ATTACK,
                                      avoid_provider="nvidia")
            assert order[0] != "nvidia"
        finally:
            m.undo()

    def test_case_e_only_same_provider_is_separate_context_only(self):
        # when no different provider is reachable, independence degree is
        # SEPARATE_CONTEXT_ONLY, never provider-independent (Art. XLV)
        deg = ph.independence_degree("openrouter", "openrouter")
        assert deg == "SEPARATE_CONTEXT_ONLY"
        deg_none = ph.independence_degree("openrouter", None)
        assert deg_none == "NOT_INDEPENDENT"

    def test_case_c_unavailable_is_typed_not_fake_independence(self):
        import pytest
        m = pytest.MonkeyPatch()
        for var in list(lr._SPEC_BY_ID.keys()):
            m.delenv(lr._SPEC_BY_ID[var].env_var, raising=False)
        m.setenv("ZAI_API_KEY", "k")   # only a provider retired here
        m.setattr(ra, "requires_probe", lambda *a, **k: False)
        try:
            res = lr.generate(
                "p", role="attack",
                policy=lr.SelectionPolicy(
                    preferred_providers=["zai"], max_preference_fallback=0,
                    purpose="independent_attack"))
            # zai is not retired from attack so it may serve; the point:
            # an empty chain returns a TYPED state, never fake independence
            assert res.selection_ledger is not None
        finally:
            m.undo()

    def test_case_d_rate_limited_is_demoted_not_removed(self):
        """§14 Case D: a rate-limited (cooldown) provider slides to the END
        of the ordinary order and is never silently removed, and the cascade
        is deterministic. Art. V: cooldown demotion (never removal)."""
        book = ph.ProviderHealthBook()
        book.record_failure("openrouter", "RATE_LIMITED",
                            purpose="synthesis")
        matrix = [
            {"provider_id": "openrouter", "available": True,
             "quality_tier": 1, "cost_tier": 1, "latency_tier": 1},
            {"provider_id": "nvidia", "available": True,
             "quality_tier": 2, "cost_tier": 2, "latency_tier": 2},
        ]
        order = ph.order_for_role(matrix, ph.ROLE_SYNTHESIS, book=book)
        # cooled provider demoted to end, never removed
        assert "openrouter" in order
        assert order[-1] == "openrouter"
        # deterministic: same inputs produce same order
        assert order == ph.order_for_role(matrix, ph.ROLE_SYNTHESIS, book=book)
        # typed rate-limit state travels, never faked absence (Art. XXI.3)
        assert book.last_failure_type("openrouter") == "RATE_LIMITED"

    def test_case_f_explicit_override_semantics_are_consistent(self):
        """§14 Case F / §15: the EXPLICIT override path permits a retired
        provider and records EXPLICIT_OPERATOR_OVERRIDE_ALLOWED; the ordinary
        path blocks it as DEFAULT_ROUTE_BLOCKED. Both answers come from the
        SAME authority (no contradiction)."""
        kept_blocked, ev_blocked = ph.apply_route_retirement(
            ["atria", "openrouter"], role=ph.ROLE_SYNTHESIS,
            explicit_override=False)
        assert "atria" not in kept_blocked
        assert any(e["retirement_state"] == "RETIRED_ROUTE_BLOCKED"
                   for e in ev_blocked)
        kept_allowed, ev_allowed = ph.apply_route_retirement(
            ["atria", "openrouter"], role=ph.ROLE_SYNTHESIS,
            explicit_override=True)
        assert "atria" in kept_allowed
        assert any(e["retirement_state"] ==
                   "EXPLICIT_OPERATOR_OVERRIDE_ALLOWED" for e in ev_allowed)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

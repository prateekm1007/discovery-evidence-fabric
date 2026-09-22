#!/usr/bin/env python3
"""R520 — adversarial tests for the single MECHANISM_SPACE routing change.

The ONE behavioral intervention: zai is retired from the MS
operator-instantiation route (purpose scope
PURPOSE_MS_OPERATOR_INSTANTIATION, resolved for operator_* purposes)
via the single routing-retirement authority. Everything else —
SYNTHESIZE routing, ATTACK, evidence extraction, post-rank purposes,
prompts, budgets, retries — is unchanged.

Each test states the bypass it attempts; a passing suite means every
attempted bypass failed closed.
"""
from discovery_fabric.engine import provider_health as ph

OPERATOR_IDS = ["DIRECT_TRANSFER", "CROSS_DOMAIN_ANALOGY",
                "GEOMETRIC_TRANSFORMATION", "BOUNDARY_CONDITION_CHANGE",
                "FAILURE_PATH_INVERSION"]


def test_ms_operator_purposes_retire_zai():
    """All five MS operator-instantiation purposes (+retry) retire zai."""
    for op in OPERATOR_IDS:
        for purpose in (f"operator_{op}", f"operator_{op}_retry"):
            assert ph.is_route_retired("zai", purpose=purpose), purpose


def test_zai_retirement_recorded_not_silent():
    """Ordinary MS routing removes zai AND records the removal."""
    kept, removed = ph.apply_route_retirement(
        ["zai", "xkiro"], role=ph.ROLE_SYNTHESIS,
        purpose="operator_DIRECT_TRANSFER")
    assert kept == ["xkiro"]
    assert len(removed) == 1
    assert removed[0]["provider"] == "zai"
    assert removed[0]["retirement_state"] == "RETIRED_ROUTE_BLOCKED"
    assert removed[0]["purpose"] == "operator_DIRECT_TRANSFER"


def test_synthesis_attack_extraction_routes_unchanged():
    """The MS scope does not leak into any other route (one route only)."""
    for purpose in ("synthesis", "attack", "independent_attack",
                    "structured_evidence_extraction",
                    "structured_evidence_extraction_retry",
                    "ensemble_invention", "mechanism_space",
                    "diversity_exploration", "operator"):
        assert not ph.is_route_retired("zai", purpose=purpose), purpose


def test_post_rank_zai_retirement_intact():
    """R518/R519 post-rank zai retirement still holds (regression)."""
    assert ph.is_route_retired(
        "zai", purpose="improvement_mutation_proposal")
    assert ph.is_route_retired(
        "zai", purpose="technical_mutation_proposal")


def test_atria_scopes_unchanged():
    """Atria stays retired exactly where R518/R519 put it — and the new
    MS purpose scope does not add atria anywhere (purpose-only check)."""
    assert ph.is_route_retired("atria", role=ph.ROLE_SYNTHESIS)
    assert ph.is_route_retired("atria", role=ph.ROLE_ATTACK)
    assert not ph.is_route_retired(
        "atria", purpose="operator_DIRECT_TRANSFER")
    assert not ph.is_route_retired("atria", purpose="synthesis")


def test_explicit_override_keeps_zai_and_records():
    """An explicit operator override can still reach zai — recorded,
    never silent (selected R519 §5 semantics preserved)."""
    kept, removed = ph.apply_route_retirement(
        ["zai", "xkiro"], role=ph.ROLE_SYNTHESIS,
        purpose="operator_DIRECT_TRANSFER", explicit_override=True)
    assert kept == ["zai", "xkiro"]
    assert [e["retirement_state"] for e in removed] == [
        "EXPLICIT_OPERATOR_OVERRIDE_ALLOWED"]


def test_case_whitespace_bypass_fails():
    """Normalization bypass attempts still resolve the MS scope."""
    assert ph.is_route_retired("zai", purpose="OPERATOR_DIRECT_TRANSFER")
    assert ph.is_route_retired(
        "zai", purpose="  operator_direct_transfer  ")


def test_unrelated_providers_untouched_on_ms_route():
    """xkiro/unorouter/openrouter are not retired from the MS route —
    the authority removes exactly zai, nothing else."""
    for pid in ("xkiro", "unorouter", "openrouter", "nvidia"):
        assert not ph.is_route_retired(
            pid, role=ph.ROLE_SYNTHESIS,
            purpose="operator_DIRECT_TRANSFER"), pid
    kept, removed = ph.apply_route_retirement(
        ["xkiro", "unorouter", "zai"], role=ph.ROLE_SYNTHESIS,
        purpose="operator_GEOMETRIC_TRANSFORMATION")
    assert kept == ["xkiro", "unorouter"]
    assert [e["provider"] for e in removed] == ["zai"]

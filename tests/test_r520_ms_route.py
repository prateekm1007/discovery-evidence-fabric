#!/usr/bin/env python3
"""R520 — adversarial tests for the single MECHANISM_SPACE routing change.

R520 original intervention: zai retired from the MS operator-
instantiation route via the single routing-retirement authority.
R6 RE-ADMISSION (owner directive 2026-11-11, "world-class, end-to-end,
FAST and LEAN — capability only"): the runtime transport was RE-MEASURED
live in the R6 session (commit 36ed4854c, Art. XXV — a recorded
classification that no longer matches measured reality is corrected to
the measured state) and the zai scopes were CLEARED from
RETIRED_ROUTE_PROVIDERS; the retirement MECHANISM stays. The tests
therefore pin BOTH: (a) today's measured state — zai is NOT retired on
any of these scopes; (b) the MECHANISM — with a scope recorded, the
predicate, the filter and the ledger still behave exactly as R520
specified (injected-scope pins; a future measured failure re-enters a
scope and these pins fire again).

Each test states the bypass it attempts; a passing suite means every
attempted bypass failed closed.
"""
from unittest import mock

from discovery_fabric.engine import provider_health as ph

OPERATOR_IDS = ["DIRECT_TRANSFER", "CROSS_DOMAIN_ANALOGY",
                "GEOMETRIC_TRANSFORMATION", "BOUNDARY_CONDITION_CHANGE",
                "FAILURE_PATH_INVERSION"]


def _zai_scoped(scope):
    """Context manager: record `scope` on zai's retirement entry (the
    MECHANISM state the R517/R520/R525-era pins measured), restored
    after. The entry itself stays (the mechanism is retained — the
    R6 re-admission cleared the SCOPES, not the authority)."""
    return mock.patch.dict(ph.RETIRED_ROUTE_PROVIDERS,
                           {"zai": {scope}})


def test_ms_operator_purposes_currently_allowed():
    """R6 re-admission (36ed4854c, Art. XXV, measured live 2026-11-11:
    MS instantiation 4/4 OK 4.2-11.1 s, 3/3/3/3 hypotheses parsed):
    all five operator purposes (+retry) are ALLOWED on zai."""
    for op in OPERATOR_IDS:
        for purpose in (f"operator_{op}", f"operator_{op}_retry"):
            assert not ph.is_route_retired("zai", purpose=purpose), purpose


def test_ms_scope_mechanism_still_enforced_when_recorded():
    """MECHANISM pin: with an operator scope recorded on zai, every
    operator purpose (+retry) resolves it and retires zai — while
    non-operator purposes stay untouched (scope exactness)."""
    with _zai_scoped(ph.PURPOSE_MS_OPERATOR_INSTANTIATION):
        for op in OPERATOR_IDS:
            for purpose in (f"operator_{op}", f"operator_{op}_retry"):
                assert ph.is_route_retired("zai", purpose=purpose), purpose
        for purpose in ("synthesis", "attack", "independent_attack"):
            assert not ph.is_route_retired("zai", purpose=purpose), purpose


def test_zai_retirement_recorded_not_silent():
    """MECHANISM pin: ordinary MS routing removes zai AND records the
    removal when a scope is recorded (never silent — Art. XV/XXVII)."""
    with _zai_scoped(ph.PURPOSE_MS_OPERATOR_INSTANTIATION):
        kept, removed = ph.apply_route_retirement(
            ["zai", "xkiro"], role=ph.ROLE_SYNTHESIS,
            purpose="operator_DIRECT_TRANSFER")
        assert kept == ["xkiro"]
        assert len(removed) == 1
        assert removed[0]["provider"] == "zai"
        assert removed[0]["retirement_state"] == "RETIRED_ROUTE_BLOCKED"
        assert removed[0]["purpose"] == "operator_DIRECT_TRANSFER"
    # today (scopes cleared): nothing is removed and nothing is
    # recorded — the re-admission is a measured state, not a bypass.
    kept, removed = ph.apply_route_retirement(
        ["zai", "xkiro"], role=ph.ROLE_SYNTHESIS,
        purpose="operator_DIRECT_TRANSFER")
    assert kept == ["zai", "xkiro"]
    assert removed == []


def test_synthesis_attack_extraction_routes_unchanged():
    """The MS scope does not leak into any other route (one route only)."""
    for purpose in ("synthesis", "attack", "independent_attack",
                    "structured_evidence_extraction",
                    "structured_evidence_extraction_retry",
                    "ensemble_invention", "mechanism_space",
                    "diversity_exploration", "operator"):
        assert not ph.is_route_retired("zai", purpose=purpose), purpose


def test_post_rank_zai_scopes_cleared_r6_readmission():
    """R6 re-admission: the R518/R519 post-rank zai scopes are CLEARED
    on the same measured evidence class (same transport, same per-call
    failure modes; the R517 battery's 564 s wall was the OLD gateway's
    30/60/90 s ladder, which the current runtime does not exhibit —
    36ed4854c, Art. XXV)."""
    assert not ph.is_route_retired(
        "zai", purpose="improvement_mutation_proposal")
    assert not ph.is_route_retired(
        "zai", purpose="technical_mutation_proposal")
    assert not ph.is_route_retired(
        "zai", purpose="TECHNICAL_STATE_EXTRACTION")


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
    never silent (selected R519 §5 semantics preserved). MECHANISM
    pin with a recorded scope; today's cleared state records nothing."""
    with _zai_scoped(ph.PURPOSE_MS_OPERATOR_INSTANTIATION):
        kept, removed = ph.apply_route_retirement(
            ["zai", "xkiro"], role=ph.ROLE_SYNTHESIS,
            purpose="operator_DIRECT_TRANSFER", explicit_override=True)
        assert kept == ["zai", "xkiro"]
        assert [e["retirement_state"] for e in removed] == [
            "EXPLICIT_OPERATOR_OVERRIDE_ALLOWED"]
    kept, removed = ph.apply_route_retirement(
        ["zai", "xkiro"], role=ph.ROLE_SYNTHESIS,
        purpose="operator_DIRECT_TRANSFER", explicit_override=True)
    assert kept == ["zai", "xkiro"]
    assert removed == []


def test_case_whitespace_bypass_fails():
    """Normalization bypass attempts still resolve the MS scope
    (MECHANISM pin under a recorded scope; today nothing is retired
    either way — the normalization contract is what stays pinned)."""
    with _zai_scoped(ph.PURPOSE_MS_OPERATOR_INSTANTIATION):
        assert ph.is_route_retired("zai", purpose="OPERATOR_DIRECT_TRANSFER")
        assert ph.is_route_retired(
            "zai", purpose="  operator_direct_transfer  ")


def test_unrelated_providers_untouched_on_ms_route():
    """xkiro/unorouter/openrouter are not retired from the MS route —
    the authority removes exactly the scoped provider, nothing else."""
    for pid in ("xkiro", "unorouter", "openrouter", "nvidia"):
        assert not ph.is_route_retired(
            pid, role=ph.ROLE_SYNTHESIS,
            purpose="operator_DIRECT_TRANSFER"), pid
    with _zai_scoped(ph.PURPOSE_MS_OPERATOR_INSTANTIATION):
        kept, removed = ph.apply_route_retirement(
            ["xkiro", "unorouter", "zai"], role=ph.ROLE_SYNTHESIS,
            purpose="operator_GEOMETRIC_TRANSFORMATION")
        assert kept == ["xkiro", "unorouter"]
        assert [e["provider"] for e in removed] == ["zai"]

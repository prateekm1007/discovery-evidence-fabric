"""R457 — the operator frontier transport battery.

The operator directive (2026-09-15): four free-tier aggregator
credentials with run-down-the-ladder depletion semantics. Covers:
  - the four specs exist in the operator's listed order with the
    OPERATOR_FREE_TIER_DECLARED basis (Art. XXVII recorded policy input)
  - the new cost basis is inside the closed vocabulary and ELIGIBLE
    under ZERO_PAID_COST (the operator action recorded in the policy
    docstring + round record); the generic FREE_TIER_API stays
    INELIGIBLE (the sanctioned shape of "free" is the declared one)
  - the eligible chain under ZERO_PAID_COST is exactly the operator's
    ladder + the self-hosted terminal rung
  - probe-before-admit: the measured probe artifacts are committed and
    record each rung's live evidence (R455 §O.2 test a discipline)
  - per-rung measurement disclosures travel in the specs (the unstable
    interstitial class, the null-content defect, the premium 403s)
  - keys are env-var names ONLY: no aggregator key material anywhere in
    the registry source (BS-021 / R451-C2 scrub discipline)

Offline by construction (the probe artifacts are committed records; no
network in this battery).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import llm_registry as lr  # noqa: E402
from discovery_fabric.engine import model_cost_policy as mcp  # noqa: E402

LADDER = ["unorouter", "xkiro", "apinex", "bai"]
KEY_ENVS = {"unorouter": "UNOROUTER_API_KEY", "xkiro": "XKIRO_API_KEY",
            "apinex": "APINEX_API_KEY", "bai": "BAI_API_KEY"}
PROBE_FILES = ["R456/OPERATOR_TRANSPORT_PROBE.json",
               "R456/OPERATOR_TRANSPORT_PROBE_R2.json"]


def _spec(pid):
    return next(s for s in lr.PROVIDER_SPECS if s.provider_id == pid)


def test_ladder_order_is_the_operators_directive():
    ids = [s.provider_id for s in lr.PROVIDER_SPECS]
    assert ids[:4] == LADDER
    # the self-hosted baseline stays the terminal eligible rung
    assert ids[4] == "localqwen"


def test_operator_free_tier_declared_is_in_the_closed_vocabulary():
    assert "OPERATOR_FREE_TIER_DECLARED" in mcp.COST_BASIS_VOCAB
    assert "OPERATOR_FREE_TIER_DECLARED" in mcp.eligible_bases(
        mcp.ZERO_PAID_COST)


def test_generic_free_tier_api_stays_ineligible_under_zero_paid():
    ok, note = mcp.provider_eligibility(_spec("tokenrouter"))
    assert not ok
    assert "ineligible" in note


def test_eligible_chain_is_ladder_plus_localqwen():
    specs = {s.provider_id: s for s in lr.PROVIDER_SPECS}
    chain, refusals = mcp.filter_chain(
        [s.provider_id for s in lr.PROVIDER_SPECS], specs)
    assert chain == LADDER + ["localqwen"]
    # every refusal names its policy basis (never silent, Art. XXI.3)
    assert all(r["policy"] == mcp.ZERO_PAID_COST for r in refusals)
    assert len(refusals) >= 1


def test_all_four_rungs_carry_the_operator_basis_and_distinct_accounts():
    domains = set()
    for pid in LADDER:
        s = _spec(pid)
        assert s.cost_basis == "OPERATOR_FREE_TIER_DECLARED", pid
        assert s.locality == "REMOTE", pid
        domains.add(s.account_domain)
    # four DISTINCT account domains (the R451-C1.2 account-redundancy
    # lesson: providers sharing one account are NOT redundant — here
    # each aggregator is its own account, so the ladder is real
    # redundancy, exactly the operator's "go to the next" semantics)
    assert len(domains) == 4


def test_probe_before_admit_artifacts_are_committed():
    for rel in PROBE_FILES:
        f = REPO / rel
        assert f.exists(), rel
        d = json.loads(f.read_text())
        assert d["reviewer_provenance"] == "AI_REVIEW"
    r2 = json.loads((REPO / PROBE_FILES[1]).read_text())
    # the pinned default models carry their OWN measured completions
    pinned = {r["model"]: r for r in r2["results"]}
    assert pinned["qwen/qwen3.8-max:free"]["verdict"] == "LIVE_OK"
    # every measured defect is IN the artifact (disclosed, Art. XV)
    verdicts = {r["model"]: r["verdict"] for r in r2["results"]}
    assert verdicts["z-ai/glm-5.3-flash"].startswith("HTTP_403")
    assert verdicts["glm-5.3"].startswith("HTTP_")
    assert verdicts["deepseek-v3-0324"].startswith(("HTTP_", "ERROR"))


def test_rung_notes_disclose_their_measurements():
    notes = {pid: _spec(pid).policy_note for pid in LADDER}
    assert "UNSTABLE" in notes["unorouter"]
    assert "PROBE_OK" in notes["xkiro"] and "MEASURED-STABLEST" in notes["xkiro"]
    assert "content=null" in notes["apinex"]
    assert "UNSTABLE" in notes["bai"]
    # the premium-refusal evidence is recorded (the :free pin is
    # load-bearing under the zero-paid policy)
    assert "403" in notes["xkiro"]


def test_no_key_material_in_the_registry_source():
    src = (REPO / "discovery_fabric" / "engine" / "llm_registry.py").read_text()
    import re
    for pat in (r"sk-[A-Za-z0-9]{16,}", r"sk-xt-[A-Za-z0-9]{10,}",
                r"sk-apx[A-Za-z0-9]{10,}"):
        assert not re.search(pat, src), f"key material leaked: {pat}"
    # the availability markers are env-var NAMES, not values
    for pid in LADDER:
        s = _spec(pid)
        assert s.env_var == KEY_ENVS[pid]
        assert s.env_var.isupper()


def test_identical_tiers_preserve_the_operator_order_in_the_ranking():
    """The default ranking sorts by (quality, cost, latency) with a
    stable sort — identical tiers mean the registry order (the
    operator's listing) IS the selection order."""
    rungs = [_spec(p) for p in LADDER]
    keys = {(s.quality_tier, s.cost_tier, s.latency_tier) for s in rungs}
    assert len(keys) == 1, "tiers must be identical for a stable ladder"
    ranked = sorted(rungs, key=lambda s: (s.quality_tier, s.cost_tier,
                                          s.latency_tier))
    assert [s.provider_id for s in ranked] == LADDER


def test_capability_gate_opens_on_the_frontier(monkeypatch):
    """strong_route_capability mirrors admission: with an operator key
    present the route is no longer DEGRADED_ONLY (the R455
    RUN_BLOCKED_CAPABILITY terminal stops firing) — mirrored here with
    the env key injected and the probe machinery stubbed offline."""
    s = _spec("xkiro")
    monkeypatch.setenv(s.env_var, "test-only-marker")
    matrix = lr.availability_matrix()
    xk = next(m for m in matrix if m["provider_id"] == "xkiro")
    assert xk["available"] is True
    assert xk["cost_policy_eligible"] is True
    monkeypatch.delenv(s.env_var)
    matrix2 = lr.availability_matrix()
    xk2 = next(m for m in matrix2 if m["provider_id"] == "xkiro")
    assert xk2["available"] is False

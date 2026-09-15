"""tests/test_r463_hf_credential_path.py — R463: the USER's Hugging
Face credential path in the real production registry.

The operator's P0 architectural ruling: **one legitimate user/
application AI credential path** — the user gives Toscanini AI access
(HF_TOKEN), and Toscanini does the rest. No hidden operator key,
developer key, or second secret may be required solely to make the
engine run.

These tests pin the HONEST registration: the credential is valid and
authorized (whoami 200, inference.serverless.write), the catalog
serves (142 models), and the completions measured 402 — the account's
monthly included Inference Providers credits are depleted. The route
is registered capable-not-currently-servable: typed CREDIT_EXHAUSTED,
cascade-advancing, self-servable on credit reset — never a fabricated
probe success (Art. XV/XXV/LXI).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.llm_registry import (  # noqa: E402
    _SPEC_BY_ID, PROVIDER_SPECS)
from discovery_fabric.engine.model_cost_policy import (  # noqa: E402
    ZERO_PAID_COST, eligible_bases)
from discovery_fabric.engine.provider_health import (  # noqa: E402
    CREDIT_EXHAUSTED, classify_failure)


def test_hf_route_registered_with_user_credential():
    spec = _SPEC_BY_ID.get("hf")
    assert spec is not None, "the HF Inference Providers route is missing"
    # the ONE legitimate credential: the user's own HF token
    assert spec.env_var == "HF_TOKEN"
    assert "huggingface.co" in spec.url
    assert spec.flavor == "openai"          # OpenAI-compatible transport
    # the strong rung is the flagship class the catalog serves
    assert spec.default_model == "openai/gpt-oss-120b"


def test_hf_account_domain_is_not_redundant_with_routers():
    """Every model behind the HF router bills the SAME included credits
    (the measured R450 domain) — the spec must declare that ONE domain
    so the redundancy mathematics stay honest."""
    spec = _SPEC_BY_ID["hf"]
    assert spec.account_domain == "HF_ACCOUNT_CREDITS"
    # and no other registered provider shares it
    sharers = [p.provider_id for p in PROVIDER_SPECS
               if p.account_domain == "HF_ACCOUNT_CREDITS"
               and p.provider_id != "hf"]
    assert sharers == [], \
        f"unexpected providers share the HF credits domain: {sharers}"


def test_hf_cost_basis_is_eligible_under_zero_paid_cost():
    spec = _SPEC_BY_ID["hf"]
    eligible = eligible_bases(ZERO_PAID_COST)
    assert spec.cost_basis in eligible


def test_hf_registration_quotes_measured_402_specimen():
    """Art. III: the registration's evidence lives in a committed probe
    artifact, and the artifact records the HONEST outcome."""
    probe = REPO / "R463" / "PROBE_HF_ROUTER.json"
    assert probe.exists(), "the live probe artifact must be committed"
    ev = json.loads(probe.read_text())
    assert ev["probe_before_admit"] is True
    steps = {m["step"]: m for m in ev["measurements"]}
    # valid credential, verified live
    who = steps["whoami"]
    assert who["http"] == 200
    assert who["identity"]["inference_scope"].startswith(
        "inference.serverless.write present")
    # the catalog serves
    assert steps["catalog"]["http"] == 200
    assert steps["catalog"]["model_count"] >= 100
    # the completions measured 402 — CREDIT_EXHAUSTED, verbatim recorded
    for name in ("openai/gpt-oss-120b", "zai-org/GLM-5.3"):
        comp = [m for m in ev["measurements"]
                if m["step"] == "tiny_completion" and m["model"] == name][0]
        assert comp["http"] == 402
        assert comp["failure_class"] == "CREDIT_EXHAUSTED"
        assert "depleted" in comp["provider_words"].lower()
    assert "Art. XV" in ev["honest_conclusion"] or "Art. XXV" in \
        ev["honest_conclusion"]


def test_402_classifies_credit_exhausted():
    """The rung's measured specimen classifies typed (R436 class) — the
    cascade advances instead of mislabeling the account or retrying a
    dead budget forever."""
    exc = RuntimeError("HTTP Error 402: Payment Required")
    cls = classify_failure(exc, http_status=402)
    assert cls == CREDIT_EXHAUSTED


def test_no_second_engine_secret_registered():
    """The P0 ruling, executable: no provider spec may require a key
    whose only purpose is internal engine operation (an operator/
    developer key). Every env_var is a PROVIDER credential."""
    for spec in PROVIDER_SPECS:
        assert not spec.env_var.startswith("ENGINE_"), \
            f"{spec.provider_id} requires an ENGINE_* secret: " \
            f"{spec.env_var}"
    assert not any(p.provider_id == "operator" for p in PROVIDER_SPECS)

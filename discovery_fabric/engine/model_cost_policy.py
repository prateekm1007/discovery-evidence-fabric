"""discovery_fabric/engine/model_cost_policy.py — R451 §1.

MODEL_COST_POLICY = ZERO_PAID_COST: the engine's LLM transport may use
ONLY models whose measured cost basis is zero for the operator —
self-hosted weights running locally (license-recorded, revision-pinned)
or an explicitly-declared free tier. A route that would require paid
inference credits is REFUSED, fail-closed:

  * a provider whose cost basis is PAID_API / credit-router is
    ineligible — never silently fallen back to (the R450 production
    defect: the stale glm-4-plus id on the HF router, model_not_found
    classified INVALID_RESPONSE, was the last rung of a PAID fallback
    chain);
  * when the policy filters out every provider, the call returns
    PROVIDER_UNAVAILABLE with the policy reason in the ledger — the
    engine records WHY nothing was generated (Art. LXI), it never
    widens the policy to make a run succeed (Art. IV/VII);
  * "free" is not a permanent property of a model: each provider spec
    carries its MEASURED basis, and the cost provenance travels with
    every call result so the run record states which model, which
    revision, which transport, local or remote, under which license,
    at what cost basis actually produced each generation.

Cost-basis vocabulary (closed):
  ZERO_PAID_COST_SELF_HOSTED  weights on local disk, local inference
                              (llama.cpp llama-server), no per-token
                              billing of any kind — the R451 baseline
                              class (Qwen/Qwen3-1.7B, apache-2.0)
  FREE_TIER_API               a provider route MEASURED free at wiring
                              time (may deplete — re-measured per run;
                              the tokenrouter glm-5.3-free precedent)
  ENVIRONMENT_GRANT           an embedding of the coding sandbox itself
                              (the z-ai CLI gateway); costs the operator
                              nothing but is NOT self-hosted weights —
                              ineligible under ZERO_PAID_COST, recorded
                              so the distinction is never blurred
  PAID_API                    per-token or credit billing (the HF
                              inference router's 402-depleted credit
                              state is the canonical example)

The active policy is read from ENGINE_MODEL_COST_POLICY at CALL time
(default ZERO_PAID_COST from R451; UNRESTRICTED is the recorded
operator escape hatch — a policy change is an operator action, never a
coder's convenience).
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

ZERO_PAID_COST = "ZERO_PAID_COST"
UNRESTRICTED = "UNRESTRICTED"
POLICY_VOCAB = [ZERO_PAID_COST, UNRESTRICTED]

COST_BASIS_VOCAB = [
    "ZERO_PAID_COST_SELF_HOSTED",
    "FREE_TIER_API",
    "ENVIRONMENT_GRANT",
    "PAID_API",
]

#: the bases eligible under each policy (closed mapping)
_ELIGIBLE: Dict[str, List[str]] = {
    ZERO_PAID_COST: ["ZERO_PAID_COST_SELF_HOSTED"],
    UNRESTRICTED: list(COST_BASIS_VOCAB),
}

COST_POLICY_VERSION = "model_cost_policy/1.0.0"


def active_policy() -> str:
    """The active cost policy, read at call time (Art. XXIV)."""
    p = (os.environ.get("ENGINE_MODEL_COST_POLICY", "").strip()
         or ZERO_PAID_COST).upper()
    return p if p in POLICY_VOCAB else ZERO_PAID_COST


def eligible_bases(policy: Optional[str] = None) -> List[str]:
    p = policy or active_policy()
    return list(_ELIGIBLE.get(p, _ELIGIBLE[ZERO_PAID_COST]))


def provider_eligibility(spec: Any,
                         policy: Optional[str] = None
                         ) -> Tuple[bool, str]:
    """Is this provider spec eligible under the active cost policy?

    Returns (eligible, basis_note). A spec without a cost basis (a
    legacy spec) is INELIGIBLE under ZERO_PAID_COST — unknown is never
    silently treated as free (Art. XXV).
    """
    p = policy or active_policy()
    basis = str(getattr(spec, "cost_basis", "") or "")
    if basis not in COST_BASIS_VOCAB:
        return False, (f"cost basis {basis or 'UNDECLARED'!r} outside "
                       f"the closed vocabulary — ineligible (never "
                       f"silently treated as free)")
    if basis in _ELIGIBLE.get(p, []):
        return True, f"cost basis {basis} eligible under {p}"
    return False, f"cost basis {basis} ineligible under {p}"


def filter_chain(chain: List[str],
                 spec_by_id: Dict[str, Any],
                 policy: Optional[str] = None
                 ) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Filter a provider-id chain by the cost policy.

    Returns (filtered_chain, refusals) where each refusal records the
    provider and the policy basis — the refusals travel in the
    selection ledger so a filtered run states WHY (never silent).
    """
    p = policy or active_policy()
    out: List[str] = []
    refusals: List[Dict[str, Any]] = []
    for pid in chain:
        spec = spec_by_id.get(pid)
        if spec is None:
            continue
        ok, note = provider_eligibility(spec, p)
        if ok:
            out.append(pid)
        else:
            refusals.append({"provider": pid, "reason": note,
                             "policy": p})
    return out, refusals


def cost_provenance(spec: Any, model: Optional[str] = None) -> Dict[str, Any]:
    """The per-call cost provenance record (R451 §1: model_id, model_
    revision, transport, local_or_remote, license, cost_basis).

    Built from the spec's OWN declared fields — never invented (Art.
    VI); a spec that does not declare them records UNDECLARED (an
    honest unknown, not a guess).
    """
    return {
        "model_id": model or getattr(spec, "model_for_call", lambda: "")(),
        "model_revision": str(getattr(spec, "model_revision", "")
                              or "UNDECLARED"),
        "transport": str(getattr(spec, "url_for_call", lambda: "")()),
        "local_or_remote": str(getattr(spec, "locality", "")
                               or "UNDECLARED"),
        "license": str(getattr(spec, "license", "") or "UNDECLARED"),
        "cost_basis": str(getattr(spec, "cost_basis", "")
                          or "UNDECLARED"),
        # R451-C1.2: the economic account that paid (or was attempted) —
        # the ACCOUNT failure domain, distinct from provider and model
        # (operator directive: distinguish MODEL from PROVIDER from
        # ACCOUNT; two providers on one account domain are NOT redundant)
        "account_domain": str(getattr(spec, "account_domain", "")
                              or "UNDECLARED"),
        "policy": active_policy(),
        "policy_version": COST_POLICY_VERSION,
    }

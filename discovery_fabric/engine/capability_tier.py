"""discovery_fabric/engine/capability_tier.py — R452: capability/science
separation.

Constitution v2.5.0, Article LXXI (Capability Identity and Model
Provenance):

> A degraded model/provider configuration must not silently redefine the
> product's scientific capability. Any downgrade that materially affects
> reasoning, evidence handling, attack execution, or invention quality
> must be explicitly recorded as a capability downgrade and must trigger
> re-validation of mission claims.

> Canonical state carries a CAPABILITY_TIER, measured (never asserted)
> from the live provider/model reality. The system cannot claim a
> capability above its measured tier.

THE DEFECT THIS MODULE FIXES (external audit): a transport repair
silently reduced 11 nominal providers to 1 admissible provider
(Qwen3-1.7B) while the product's scientific ambition stayed unchanged —
a capability-floor problem recorded only as CHEAP_EMERGENCY_FALLBACK (a
transport fact misused as a capability statement).

DESIGN (capability/science SEPARATION — the tier is about the MODEL
CONFIGURATION, orthogonal to the science domain of the problem):

    TIER_1_TRANSPORT_ONLY      text in/out survives; no evidence discipline
    TIER_2_EVIDENCE_CAPABLE    retrieves, cites, respects provenance
    TIER_3_REASONING_CAPABLE   sustains causal chains and adjudication
    TIER_4_ADVERSARIAL_SCIENTIFIC  attack execution, calibrated verdicts
    TIER_5_ENGINEERING         parameterized engineering synthesis
    TIER_6_EXPERIMENT_REALITY_LOOP  closed-loop causal learning

The tier is MEASURED from probe results (never asserted), and every
capability claim is evaluated against the measured tier
(evaluate_capability_claim) — a claim above the tier is a typed
CAPABILITY_EXCEEDS_MEASURED_TIER violation, not a warning.

reviewer_provenance: AI_REVIEW (Art. LXVII).
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

TIER_1 = "TIER_1_TRANSPORT_ONLY"
TIER_2 = "TIER_2_EVIDENCE_CAPABLE"
TIER_3 = "TIER_3_REASONING_CAPABLE"
TIER_4 = "TIER_4_ADVERSARIAL_SCIENTIFIC"
TIER_5 = "TIER_5_ENGINEERING"
TIER_6 = "TIER_6_EXPERIMENT_REALITY_LOOP"

TIER_ORDER: List[str] = [TIER_1, TIER_2, TIER_3, TIER_4, TIER_5, TIER_6]

# the probes that define each tier boundary (measured, never asserted).
# Each probe is a binary measured capability of the CURRENT model config.
PROBES = {
    TIER_2: "evidence_citation",
    TIER_3: "causal_chain_completion",
    TIER_4: "attack_execution",
    TIER_5: "parameterized_engineering_synthesis",
    TIER_6: "closed_loop_learning",
}

# claims and the minimum measured tier each requires
CLAIM_REQUIREMENTS: Dict[str, str] = {
    "evidence-grounded synthesis": TIER_2,
    "evidence handling": TIER_2,
    "causal mechanism reasoning": TIER_3,
    "adjudication": TIER_3,
    "adversarial attack execution": TIER_4,
    "attacker verdicts": TIER_4,
    "calibrated attack": TIER_4,
    "parameterized engineering synthesis": TIER_5,
    "engineering geometry synthesis": TIER_5,
    "closed-loop causal learning": TIER_6,
    "autonomous discovery loop": TIER_6,
}

MODULE_VERSION = "1.0.0"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def measure_capability_tier(model_id: str, provider: str,
                            probe_results: Dict[str, bool],
                            model_revision: Optional[str] = None,
                            inference_config: Optional[Dict] = None,
                            ) -> Dict[str, Any]:
    """Measure the capability tier from probe results.

    Tier logic (fail-closed, Art. V): the tier is the HIGHEST contiguous
    tier whose probe passed AND all lower-tier probes passed. A missing
    probe counts as failed (unknown stays unknown — never asserted up).
    """
    probes_run = 0
    passed: Dict[str, bool] = {}
    for t in TIER_ORDER[1:]:
        probe = PROBES[t]
        probes_run += 1
        ok = bool(probe_results.get(probe, False))
        passed[probe] = ok
    # tier = highest CONTIGUOUS tier whose probe (and all lower-tier
    # probes) passed — a higher probe passing over a broken lower one
    # does not count (fail-closed, Art. V: no fallback epistemology)
    tier = TIER_1
    for t in TIER_ORDER[1:]:
        if not passed[PROBES[t]]:
            break
        tier = t
    return {
        "organ": "CAPABILITY_TIER",
        "module_version": MODULE_VERSION,
        "at": _now(),
        "tier": tier,
        "basis": {
            "probes_run": probes_run,
            "probe_results": passed,
            "measurement_rule": ("highest contiguous tier with all "
                                 "lower-tier probes passed; a missing "
                                 "probe counts as failed (fail-closed)"),
            "reviewer_provenance": "AI_REVIEW",
        },
        "model_provenance": {
            "model_id": model_id,
            "model_revision": model_revision,
            "provider": provider,
            "inference_config": inference_config or {},
        },
        "constitution": "v2.5.0 Art. LXXI (capability tiers are measured, "
                        "not labeled)",
    }


def evaluate_capability_claim(measured_tier: str,
                              claim: str) -> Dict[str, Any]:
    """Evaluate a capability claim against the measured tier. A claim
    above the measured tier is a typed violation (never a warning)."""
    required = CLAIM_REQUIREMENTS.get(claim)
    if required is None:
        # unknown claims map to the strictest sensible default: they may
        # not exceed TIER_3 reasoning without a registered requirement
        required = TIER_3
    allowed = (TIER_ORDER.index(measured_tier)
               >= TIER_ORDER.index(required))
    out = {
        "claim": claim,
        "measured_tier": measured_tier,
        "required_tier": required,
        "allowed": allowed,
        "constitution": "v2.5.0 Art. LXXI",
        "at": _now(),
    }
    if not allowed:
        out["violation"] = "CAPABILITY_EXCEEDS_MEASURED_TIER"
        out["required_action"] = (
            "record the claim as unavailable at the current tier; "
            "re-validate after a measured tier increase (capability "
            "integrity — the Discovery Mission Preservation Principle)")
    return out


def capability_identity(model_id: str, provider: str,
                        constitution_version: str,
                        model_revision: Optional[str] = None,
                        commit: Optional[str] = None,
                        capability_tier: Optional[str] = None,
                        extra: Optional[Dict[str, Any]] = None,
                        ) -> Dict[str, Any]:
    """The Article LXXI experiment identity tuple: model identity,
    revision, provider, inference configuration, capability tier and the
    governing constitution are part of the provenance of every
    model-derived scientific assertion."""
    ident = {
        "organ": "CAPABILITY_IDENTITY",
        "module_version": MODULE_VERSION,
        "model_id": model_id,
        "model_revision": model_revision,
        "provider": provider,
        "capability_tier": capability_tier or TIER_1,
        "constitution_version": constitution_version,
        "commit": commit,
        "at": _now(),
        "note": ("model revision is scientific provenance, exactly like "
                 "reagent lot numbers (Art. LXXI)"),
    }
    if extra:
        ident.update(extra)
    return ident

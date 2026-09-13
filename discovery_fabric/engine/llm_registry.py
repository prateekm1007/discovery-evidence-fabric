"""discovery_fabric/engine/llm_registry.py — E1 credential-independent LLM layer.

CEO directive E1: the engine must not depend on one LLM vendor. This registry
exposes ONE interface:

    generate(prompt, system, schema, policy) -> LLMCallResult

over ten providers (tokenrouter, zai, OpenRouter, NVIDIA, Anthropic,
Gemini, OpenAI, Qwen, DeepSeek, Mistral). The engine selects a provider
by explicit policy: availability -> quality tier -> cost tier -> latency
tier. The ninth provider (zai, 2026-08-30) is the sandbox-local gateway
added as the healthy transport path after the NVIDIA latency collapse;
the tenth (tokenrouter, 2026-09-05) is the owner-supplied Token Router
credential that unblocked the R411 campaign when the sandbox zai
transport's shared upstream quota rate-limited — E1 credential
independence working as designed, not a policy change.

Constitutional contract (Art. I, IV, VI, XVIII, XXV):
  - A missing API key is PROVIDER_UNAVAILABLE, never NO_INVENTION and never
    silent degradation: the full availability matrix travels with every call
    result so the conductor can record WHY nothing was generated.
  - Substitution is explicit, never silent: if the policy-head provider is
    unavailable, the result records `substituted_from` with the reason. The
    policy orders by quality tier first, so a substitution is never to a
    *better*-hidden weaker model — it is recorded, inspectable, and the
    caller may pin `policy.preferred_providers` to forbid it entirely.
  - The LLM is an untrusted component (Art. XVIII): its output is content,
    never evidence. Call results carry prompt/output hashes for the
    provenance chain; nothing here grants epistemic authority.
  - Keys are read at CALL time (not import time) so late credential
    bootstrap (.env.keys) works (Art. XXIV: exact mechanics matter).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import ssl
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from . import model_cost_policy as _cost_policy

# Status vocabulary (explicit; Art. XXV — unknown stays unknown)
ST_OK = "OK"
ST_PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
ST_CALL_FAILED = "CALL_FAILED"
# R451: a policy-refused call (the cost policy filtered every route;
# fail-closed, never a silent widening — Art. IV/VII)
ST_POLICY_BLOCKED = "POLICY_BLOCKED"


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"


@dataclass(frozen=True)
class ProviderSpec:
    """One vendor entry. quality_tier 1 = best (lower is better)."""
    provider_id: str
    env_var: str
    url: str
    default_model: str
    flavor: str                 # openai | anthropic
    context_capacity_tokens: int
    quality_tier: int
    cost_tier: int              # 1 = cheapest
    latency_tier: int           # 1 = fastest
    policy_note: str
    # ---- R451 §1: cost provenance (closed vocabulary in
    # model_cost_policy.py; UNDECLARED stays ineligible under
    # ZERO_PAID_COST — never silently free) ---------------------------
    cost_basis: str = "UNDECLARED"
    locality: str = "UNDECLARED"    # LOCAL | REMOTE
    license: str = "UNDECLARED"
    model_revision: str = "UNDECLARED"
    # R451-C1.2 (operator transport-capability directive): the ECONOMIC
    # ACCOUNT that pays for this provider's calls — MODEL vs PROVIDER vs
    # ACCOUNT are three distinct failure domains. Two providers that
    # share one account domain (e.g. every HF-router-routed serving
    # provider billing the SAME HF account's inference credits) are NOT
    # redundant: the account's credit exhaustion kills them all at once
    # (the R450 production failure). Closed vocabulary in
    # transport_capability.ACCOUNT_DOMAIN_VOCAB; UNDECLARED stays honest.
    account_domain: str = "UNDECLARED"
    #: transport-only request extras merged into the openai-flavor
    #: body (e.g. disabling Qwen3's default thinking mode on the local
    #: llama-server — measured: thinking mode leaks meta-commentary
    #: into FIELD lines and multiplies latency)
    extra_body: Optional[Dict[str, Any]] = None

    def url_for_call(self) -> str:
        """Effective endpoint for this call.

        R391 (deployment): an EXPLICIT operator override `{PROVIDER}_BASE_URL`
        re-points a provider slot at a public OpenAI-compatible endpoint —
        the mechanism that lets a hosted engine use the same registry
        without the sandbox-local gateway. Transport-only: provider
        selection policy, quality tiers, and epistemic semantics are
        untouched (same operator-override class as the ENGINE_*_PROVIDER
        pins — recorded, never silent)."""
        return (os.environ.get(f"{self.provider_id.upper()}_BASE_URL", "")
                .strip() or self.url)

    def model_for_call(self) -> str:
        override = os.environ.get(f"{self.provider_id.upper()}_MODEL", "")
        return override or self.default_model


# The provider registry (CEO E1; ten providers since 2026-09-05 — the
# tokenrouter direct-HTTPS provider is the R411-campaign unblock). Quality
# tiers are RECORDED POLICY INPUTS (Art. XXVII: explicit, documented), not
# measurements; they encode the engine's default preference order and are
# inspected in every ledger.
PROVIDER_SPECS: List[ProviderSpec] = [
    ProviderSpec(
        # R451 §1-2: the ZERO-PAID local baseline — self-hosted weights
        # (Qwen/Qwen3-1.7B, apache-2.0) served by llama.cpp llama-server
        # on 127.0.0.1. No credential: availability is the LOCAL_QWEN_BASE_URL
        # operator wiring (set by the benchmark/engine wrapper which owns the
        # server lifecycle — the sandbox reaps spawned processes at the
        # tool-call boundary, measured R447). HONEST TIERS: quality_tier 4
        # (a 1.7B model is NOT a world-class scientific reasoner — the R451
        # test is whether the Toscanini architecture still closes its loop
        # with a smaller, weaker model), latency_tier 4 (measured 6.3 tok/s
        # on 2 vCPU, 2026-09-12). Eligible under MODEL_COST_POLICY=
        # ZERO_PAID_COST by construction.
        "localqwen", "LOCAL_QWEN_BASE_URL",
        "http://127.0.0.1:8790/v1/chat/completions",
        "qwen3-1.7b", "openai", 32_768,
        quality_tier=4, cost_tier=1, latency_tier=4,
        cost_basis="ZERO_PAID_COST_SELF_HOSTED",
        locality="LOCAL",
        license="apache-2.0",
        account_domain="LOCAL_COMPUTE",
        model_revision=("GGUF build bartowski/Qwen_Qwen3-1.7B-GGUF "
                        "dcb19155b962dbb6389f4691a982043a8e651022; "
                        "gguf sha256 72c5c3cb38fa32d5256e2fe30d03e7a64c"
                        "6c79e668ad84057e3bd66e250b24fb; base model "
                        "Qwen/Qwen3-1.7B"),
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        policy_note=(
            "R451 zero-paid local baseline: Qwen/Qwen3-1.7B Q4_K_M "
            "weights (1.28 GB) served by llama.cpp llama-server b10930 "
            "(CPU, 2 threads, context 8192) via scripts/r451_local_qwen.py; "
            "OpenAI-compatible endpoint; measured 6.3 tok/s on the "
            "benchmark host 2026-09-12 (513-token prompt, 191-token "
            "completion, 30.2 s). No API key: the wrapper sets "
            "LOCAL_QWEN_BASE_URL when it owns the server. Thinking mode "
            "DISABLED via chat_template_kwargs (measured: Qwen3's default "
            "thinking leaks meta-commentary into FIELD lines). Cost basis "
            "ZERO_PAID_COST_SELF_HOSTED: self-hosted weights, local "
            "inference, no per-token billing of any kind — the ONLY basis "
            "eligible under MODEL_COST_POLICY=ZERO_PAID_COST.")),
    ProviderSpec(
        "tokenrouter", "TOKEN_ROUTER_API_KEY",
        "https://api.tokenrouter.com/v1/chat/completions",
        "z-ai/glm-5.3-free", "openai", 128_000,
        quality_tier=2, cost_tier=1, latency_tier=2,
        cost_basis="FREE_TIER_API", locality="REMOTE",
        license="proprietary serving terms (z-ai free tier)",
        account_domain="OWNER_TOKENROUTER_ACCOUNT",
        policy_note=(
            "owner-supplied Token Router credential (delivered 2026-09-05 "
            "with the statement 'GLM 5.3 is free to use'), wired as the "
            "tenth provider to unblock the R411 campaign when the sandbox "
            "zai gateway's shared upstream GLM quota rate-limited mid-F4a "
            "(137/400 evidence resolutions measured, 263 pending, Art. LXI "
            "INCOMPLETE discipline held). LIVE-MEASURED at wiring time "
            "(Art. III): GET /v1/models -> 200 with 135 served models "
            "incl. the z-ai GLM family; z-ai/glm-5.3-free tiny completion "
            "-> 200, serves the FLAGSHIP glm-5.3 model, 3.5-4.5 s plain / "
            "~16 s with reasoning enabled on a realistic evidence-resolution "
            "prompt (the model's default thinking mode is kept: it is "
            "format-compliant for the engine's FIELD-line protocol, unlike "
            "thinking-disabled which measured 5x faster but leaked "
            "meta-commentary instead of field lines); the paid z-ai/glm-5.3 "
            "route measured 403 insufficient_user_quota ($0.00 credit), so "
            "the free tier is the operative path; default urllib User-Agent "
            "passes (no CF block on api.tokenrouter.com, unlike "
            "token-router.ai). Placed at the head of the tier-2 group "
            "(before zai) so llm_generate's availability-order prefers it "
            "when the key is present — the documented healthy-path "
            "precedent of the zai insertion (R375). Tier assignment is a "
            "recorded policy input (Art. XXVII), not a measurement; the "
            "latency tier honestly records the measured reasoning latency "
            "behind the sandbox gateway's ~2 s. FREE_TIER_API under R451: "
            "free is NOT permanent — the tier can deplete (re-measured "
            "per run), and under MODEL_COST_POLICY=ZERO_PAID_COST this "
            "provider is INELIGIBLE (fail-closed) — the R451 zero-paid "
            "baseline is the self-hosted localqwen.")),
    ProviderSpec(
        "zai", "ZAI_API_KEY",
        "http://127.0.0.1:8787/v1/chat/completions",
        # R451 §1: the stale PAID fallback id glm-4-plus is REMOVED from
        # this spec's default (the R450-recorded engine defect: on the
        # hosted deployment the ZAI_BASE_URL re-point sends this slot to
        # the HF inference router, where glm-4-plus answers model_not_found
        # classified INVALID_RESPONSE — a PAID-credit route as the last
        # rung of the fallback chain). The default now names the env-
        # contract model the R447 deployment actually serves (ZAI_MODEL
        # overrides per call); under ZERO_PAID_COST this provider is
        # INELIGIBLE either way (ENVIRONMENT_GRANT in the sandbox,
        # credit-router when re-pointed) — recorded, never silent.
        "zai-org/GLM-5.3", "openai", 128_000,
        quality_tier=2, cost_tier=1, latency_tier=1,
        # sandbox gateway is loopback (LOCAL); the ZAI_BASE_URL re-point
        # to the HF inference router makes it REMOTE and credit-based —
        # both states are recorded per call in cost_provenance
        cost_basis="ENVIRONMENT_GRANT", locality="LOCAL",
        account_domain="SANDBOX_ENVIRONMENT_GRANT",
        policy_note=(
            "sandbox-local OpenAI-compatible gateway (scripts/zai_gateway.mjs) "
            "backed by the z-ai SDK (the CLI's embedded model; verified "
            "live 2026-08-30: READY probe, ~2 s). R451: the gateway's "
            "historical glm-4-plus request model is a PAID commercial "
            "model riding an environment grant — the id is REMOVED from "
            "the fallback chain (the R450-recorded stale-id defect on the "
            "HF router) and the spec's default now names the env-contract "
            "model (ZAI_MODEL overrides per call). Cost basis "
            "ENVIRONMENT_GRANT: the sandbox's embedded grant, not "
            "self-hosted weights — INELIGIBLE under MODEL_COST_POLICY="
            "ZERO_PAID_COST (R451), recorded so the distinction is never "
            "blurred. Registered as the HEALTHY "
            "transport path after the measured NVIDIA latency collapse "
            "(35 s..>240 s variance on identical calls; tiny-call timeouts "
            "re-verified 2026-08-30) and the Mistral 401 — the documented "
            "M1 unblock ('a healthy/second LLM provider'). Placed at the "
            "head of the tier-2 group so the DEFAULT policy (availability "
            "-> quality -> cost -> latency) prefers the healthy path over "
            "the degraded one; purpose-specific call sites select it via "
            "the explicit ENGINE_*_PROVIDER operator overrides (recorded "
            "in candidate provenance, never silent). Tier assignment is a "
            "recorded policy input (Art. XXVII), not a measurement")),
    ProviderSpec(
        "openrouter", "OPENROUTER_API_KEY",
        "https://openrouter.ai/api/v1/chat/completions",
        "deepseek/deepseek-v4-flash-0731", "openai", 128_000,
        quality_tier=2, cost_tier=2, latency_tier=2,
        cost_basis="PAID_API", locality="REMOTE",
        license="commercial API terms",
        account_domain="OWNER_OPENROUTER_ACCOUNT",
        policy_note=("legacy synthesis provider; frozen synthesis model "
                     "deepseek/deepseek-v4-flash-0731 (a2 FROZEN_MODEL); "
                     "PAID_API under R451 — ineligible under "
                     "ZERO_PAID_COST")),
    ProviderSpec(
        "nvidia", "NVIDIA_API_KEY",
        "https://integrate.api.nvidia.com/v1/chat/completions",
        "deepseek-ai/deepseek-v4-flash-0731", "openai", 128_000,
        quality_tier=2, cost_tier=1, latency_tier=1,
        cost_basis="PAID_API", locality="REMOTE",
        license="commercial API terms",
        account_domain="OWNER_NVIDIA_ACCOUNT",
        policy_note=("hosts the FROZEN synthesis model "
                     "deepseek-ai/deepseek-v4-flash-0731 (same family as the "
                     "a2 FROZEN_MODEL); legacy default meta/llama-3.1-8b-"
                     "instruct was retired from the NVIDIA catalog (HTTP 410, "
                     "verified 2026-08-27) — replacement is EXPLICIT, not "
                     "silent, and stays on the frozen model family; PAID_API "
                     "under R451 — ineligible under ZERO_PAID_COST")),
    ProviderSpec(
        "anthropic", "ANTHROPIC_API_KEY",
        "https://api.anthropic.com/v1/messages",
        "claude-sonnet-4-20250514", "anthropic", 200_000,
        quality_tier=1, cost_tier=3, latency_tier=3,
        cost_basis="PAID_API", locality="REMOTE",
        license="commercial API terms",
        account_domain="OWNER_ANTHROPIC_ACCOUNT",
        policy_note="highest quality tier; used first when available; "
                    "PAID_API under R451"),
    ProviderSpec(
        "gemini", "GEMINI_API_KEY",
        "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "gemini-2.0-flash", "openai", 1_000_000,
        quality_tier=2, cost_tier=1, latency_tier=2,
        cost_basis="PAID_API", locality="REMOTE",
        license="commercial API terms",
        account_domain="OWNER_GOOGLE_ACCOUNT",
        policy_note="largest context capacity; OpenAI-compatible endpoint; "
                    "PAID_API under R451"),
    ProviderSpec(
        "openai", "OPENAI_API_KEY",
        "https://api.openai.com/v1/chat/completions",
        "gpt-4o", "openai", 128_000,
        quality_tier=1, cost_tier=3, latency_tier=2,
        cost_basis="PAID_API", locality="REMOTE",
        license="commercial API terms",
        account_domain="OWNER_OPENAI_ACCOUNT",
        policy_note="highest quality tier; used first when available; "
                    "PAID_API under R451"),
    ProviderSpec(
        "qwen", "QWEN_API_KEY",
        "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "qwen-max", "openai", 128_000,
        quality_tier=2, cost_tier=2, latency_tier=2,
        cost_basis="PAID_API", locality="REMOTE",
        license="commercial API terms",
        account_domain="OWNER_ALIBABA_ACCOUNT",
        policy_note="DashScope OpenAI-compatible mode; PAID_API under "
                    "R451 — the zero-paid Qwen path is the self-hosted "
                    "localqwen provider, not this API"),
    ProviderSpec(
        "deepseek", "DEEPSEEK_API_KEY",
        "https://api.deepseek.com/chat/completions",
        "deepseek-chat", "openai", 128_000,
        quality_tier=2, cost_tier=1, latency_tier=2,
        cost_basis="PAID_API", locality="REMOTE",
        license="commercial API terms",
        account_domain="OWNER_DEEPSEEK_ACCOUNT",
        policy_note="direct DeepSeek API (same family as frozen synthesis "
                    "model); PAID_API under R451"),
    ProviderSpec(
        "mistral", "MISTRAL_API_KEY",
        "https://api.mistral.ai/v1/chat/completions",
        "mistral-small-latest", "openai", 128_000,
        quality_tier=3, cost_tier=1, latency_tier=1,
        cost_basis="PAID_API", locality="REMOTE",
        license="commercial API terms",
        account_domain="OWNER_MISTRAL_ACCOUNT",
        policy_note=("mistral-large-latest timed out at 240 s on this account "
                     "(verified 2026-08-27); default is mistral-small-latest "
                     "(~1 s latency) — an EXPLICIT recorded tier-3 choice, "
                     "overridable via MISTRAL_MODEL (never a silent "
                     "substitution); PAID_API under R451")),
]

_SPEC_BY_ID = {p.provider_id: p for p in PROVIDER_SPECS}


@dataclass
class SelectionPolicy:
    """Explicit provider-selection policy (CEO E1).

    preferred_providers: when set, ONLY these ids are eligible, in this
    order (no fallback beyond the list). When empty, the default policy is
    availability -> quality_tier -> cost_tier -> latency_tier.
    max_preference_fallback: how far down the default order the engine may
    fall when the head is unavailable. 0 = no substitution allowed (a
    missing head provider is PROVIDER_UNAVAILABLE, full stop).
    """
    preferred_providers: List[str] = field(default_factory=list)
    max_preference_fallback: int = 8
    purpose: str = "general"          # synthesis | attack | evaluation | general


@dataclass
class LLMCallResult:
    status: str                        # OK | PROVIDER_UNAVAILABLE | CALL_FAILED
    content: Optional[str] = None
    provider_id: Optional[str] = None
    model: Optional[str] = None
    prompt_hash: Optional[str] = None
    output_hash: Optional[str] = None
    latency_ms: Optional[int] = None
    error: Optional[str] = None
    substituted_from: Optional[str] = None   # provider the policy wanted first
    selection_ledger: Dict[str, Any] = field(default_factory=dict)
    retry_notes: Optional[List[str]] = None  # recorded same-provider retries
    # R414 (provider resilience directive §8): the failover route and
    # the typed failure of the last hop. A provider failure is NEVER
    # silently treated as success — a successful result after failover
    # carries the full route disclosing every hop that failed first.
    route: Optional[List[Dict[str, Any]]] = None
    failure_type: Optional[str] = None
    # R451 §1: the cost provenance of the model that actually produced
    # (or was attempted for) this content — model_id, model_revision,
    # transport, local_or_remote, license, cost_basis, policy.
    cost_provenance: Optional[Dict[str, Any]] = None
    # R451-C1.3-3: run-level routing provenance — the effective call
    # identity (run_id/session_id/engine_stage/call_class) resolved
    # from the explicit parameter or the bound run context; carried on
    # the RESULT so run records surface it without re-deriving it.
    call_provenance: Optional[Dict[str, Any]] = None
    # R451-C1.4: task degradation — requested_task vs the capability of
    # the model that actually served. A critical scientific stage must
    # KNOW whether it received STRONG or CHEAP_EMERGENCY_FALLBACK; the
    # downgrade is explicit in provenance and final scientific records,
    # never silently relabeled as the requested capability.
    task_degradation: Optional[Dict[str, Any]] = None

    @property
    def ok(self) -> bool:
        return self.status == ST_OK

    def to_meta(self) -> Dict[str, Any]:
        """Provenance metadata for candidates (Art. VI: real values only;
        R451: the cost provenance travels with every generation;
        R451-C1.3/C1.4: the run provenance and the task-degradation
        record travel with it — a candidate states WHICH capability
        class actually produced it)."""
        return {
            "provider": self.provider_id,
            "model": self.model,
            "prompt_hash": self.prompt_hash,
            "output_hash": self.output_hash,
            "latency_ms": self.latency_ms,
            "substituted_from": self.substituted_from,
            "status": self.status,
            "cost_provenance": self.cost_provenance,
            "call_provenance": self.call_provenance,
            "task_degradation": self.task_degradation,
            "retry_notes": list(self.retry_notes or []),
            "provider_route": [
                {"provider": h.get("provider_attempted"),
                 "failure_type": h.get("failure_type"),
                 "fallback_provider": h.get("fallback_provider")}
                for h in (self.route or [])
            ] if self.route else [],
            "failure_type": self.failure_type,
        }


# --------------------------------------------------------------------------
def availability_matrix() -> List[Dict[str, Any]]:
    """Key presence per provider, evaluated at call time.

    R451: each row also carries the provider's declared cost basis,
    locality, license, model revision, and its eligibility under the
    ACTIVE cost policy — the matrix is the honest surface that answers
    "which models, at what cost, may this engine use right now".
    R451-C1.3: each row also carries the MEASURED ROUTE STATE (the
    five-state capability vocabulary) for the provider's default
    call-model — credential presence is a configuration fact, never
    capability evidence (the C1.3-1 rule). Read-only derivation: this
    function performs NO probes."""
    from . import runtime_admission as _ra
    policy = _cost_policy.active_policy()
    out = []
    for p in PROVIDER_SPECS:
        key = os.environ.get(p.env_var, "")
        eligible, elig_note = _cost_policy.provider_eligibility(p, policy)
        cap = _ra.capability_state(p.provider_id, p.model_for_call(),
                                   policy=policy)
        out.append({
            "provider_id": p.provider_id,
            "env_var": p.env_var,
            "available": bool(key.strip()),
            "model": p.model_for_call(),
            "quality_tier": p.quality_tier,
            "cost_tier": p.cost_tier,
            "latency_tier": p.latency_tier,
            "context_capacity_tokens": p.context_capacity_tokens,
            "cost_basis": p.cost_basis,
            "locality": p.locality,
            "license": p.license,
            "model_revision": p.model_revision,
            "account_domain": p.account_domain,
            "cost_policy": policy,
            "cost_policy_eligible": eligible,
            "cost_policy_note": elig_note,
            "capability_state": cap["state"],
            "policy_note": p.policy_note,
        })
    return out


def select_provider(policy: Optional[SelectionPolicy] = None) -> tuple:
    """Return (spec_or_None, ledger). Performs NO network I/O and NO
    probes — it READS persisted capability measurements (the C1.3-1
    five-state vocabulary) from the capability store.

    R451: the ACTIVE cost policy filters eligibility FIRST. A provider
    that is available but policy-ineligible (paid API, environment
    grant, undeclared basis) is excluded with its refusal recorded in
    the ledger — never silently usable, never silently widened.

    R451-C1.3/C1.7: the ONE runtime-admission semantic shared with
    generate() (no legacy selector with weaker rules):

        available
        AND cost_policy_eligible
        AND measured_capability_eligible (PROBE_OK within TTL)

    A provider with no CURRENT measured successful capability probe is
    NOT selected (NOT_PROBED / PROBE_FAILED / PROBE_EXPIRED are honest
    refusals recorded with their state — the caller probes before it
    admits; generate() probes lazily on the rungs it walks)."""
    from . import runtime_admission as _ra
    policy = policy or SelectionPolicy()
    matrix = availability_matrix()
    active_cost_policy = _cost_policy.active_policy()
    avail_ids = [m["provider_id"] for m in matrix
                 if m["available"] and m["cost_policy_eligible"]]
    refusals = [m for m in matrix
                if m["available"] and not m["cost_policy_eligible"]]
    # C1.7: the same measured-capability gate generate() applies — a
    # credential present is NOT runtime admissibility. Read-only: the
    # states travel in the ledger (capability evidence persisted).
    capability_refusals = []
    admitted_ids = []
    for m in matrix:
        if not (m["available"] and m["cost_policy_eligible"]):
            continue
        ok, note, _ev = _ra.runtime_admission(
            m["provider_id"], m["model"], policy=active_cost_policy)
        if ok:
            admitted_ids.append(m["provider_id"])
        else:
            capability_refusals.append({
                "provider": m["provider_id"], "model": m["model"],
                "capability_state": m["capability_state"],
                "reason": note})
    wanted_head: Optional[str] = None
    if policy.preferred_providers:
        eligible = [pid for pid in policy.preferred_providers
                    if pid in admitted_ids]
        order_source = policy.preferred_providers
    else:
        ranked = sorted(matrix, key=lambda m: (m["quality_tier"],
                                               m["cost_tier"], m["latency_tier"]))
        eligible = [m["provider_id"] for m in ranked
                    if m["provider_id"] in admitted_ids]
        order_source = [m["provider_id"] for m in ranked]
    substituted_from = None
    if order_source and eligible:
        first_avail = next((pid for pid in order_source if pid in eligible), None)
        wanted_head = order_source[0]
        if first_avail and wanted_head and first_avail != wanted_head:
            substituted_from = wanted_head
    if not eligible:
        ledger = {
            "policy": {"preferred": policy.preferred_providers,
                       "purpose": policy.purpose,
                       "max_preference_fallback":
                           policy.max_preference_fallback},
            "cost_policy": active_cost_policy,
            "cost_policy_refusals": [
                {"provider": r["provider_id"],
                 "reason": r["cost_policy_note"]} for r in refusals],
            "capability_refusals": capability_refusals,
            "availability": matrix,
            "selected": None,
            "reason": ("no provider has a usable credential in the "
                       "environment" if not [m for m in matrix
                                             if m["available"]] else
                       (f"the active cost policy {active_cost_policy} "
                        f"excluded every available provider — paid routes "
                        f"are REFUSED, never silently widened (R451 §1)"
                        if capability_refusals == [] and refusals else
                        "no available provider is RUNTIME-ADMISSIBLE: a "
                        "current measured successful capability probe is "
                        "required (C1.3-1) — states: "
                        + "; ".join(f"{r['provider']}={r['capability_state']}"
                                     for r in capability_refusals))),
            "decided_at": utc_now(),
        }
        return None, ledger
    if policy.preferred_providers:
        # Hard preference order; no quality re-ranking beyond the given list.
        chosen = eligible[0]
        if (policy.max_preference_fallback == 0
                and eligible[0] != policy.preferred_providers[0]):
            chosen = None
    else:
        within = [pid for pid in eligible][:max(1, policy.max_preference_fallback)]
        chosen = within[0] if within else None
    ledger = {
        "policy": {"preferred": policy.preferred_providers,
                   "purpose": policy.purpose,
                   "max_preference_fallback": policy.max_preference_fallback},
        "cost_policy": active_cost_policy,
        "cost_policy_refusals": [
            {"provider": r["provider_id"],
             "reason": r["cost_policy_note"]} for r in refusals],
        "capability_refusals": capability_refusals,
        "availability": matrix,
        "eligible_order": eligible,
        "selected": chosen,
        "substituted_from": substituted_from,
        "reason": ("explicit preferred order" if policy.preferred_providers
                   else "default policy: availability -> quality -> cost -> "
                        "latency (runtime-admission semantics: available "
                        "AND cost_policy_eligible AND "
                        "measured_capability_eligible)"),
        "decided_at": utc_now(),
    }
    return (_SPEC_BY_ID.get(chosen) if chosen else None), ledger


# --------------------------------------------------------------------------
def _post_json(url: str, payload: dict, headers: Dict[str, str],
               timeout: int) -> Dict[str, Any]:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _call_openai_flavor(spec: ProviderSpec, messages: List[dict],
                        timeout: int, max_tokens: int,
                        model_override: Optional[str] = None) -> str:
    key = os.environ.get(spec.env_var, "").strip()
    model = model_override or spec.model_for_call()
    payload: Dict[str, Any] = {"model": model, "messages": messages,
                               "temperature": 0.0,
                               # bounded generation: the structured FIELD-line outputs are short;
                               # an unbounded cap lets reasoning models generate for many minutes
                               # (measured 2026-08-27: wall time scales with the token cap on the
                               # NVIDIA deepseek-v4-flash endpoint)
                               "max_tokens": max_tokens}
    # R451: transport-only per-provider request extras (e.g. disabling
    # Qwen3's default thinking mode on the local llama-server — merged
    # verbatim, never inventing new semantics)
    if spec.extra_body:
        payload.update(spec.extra_body)
    data = _post_json(
        spec.url_for_call(), payload,
        {"Authorization": f"Bearer {key}"}, timeout)
    if "error" in data:
        err = data["error"]
        msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
        raise RuntimeError(f"{spec.provider_id} API error: {msg[:300]}")
    choice = (data.get("choices") or [{}])[0]
    content = choice.get("message", {}).get("content", "") or ""
    if not content:
        finish = choice.get("finish_reason", "unknown")
        raise EmptyContentWithFinish(
            f"{spec.provider_id} returned empty content "
            f"(finish_reason={finish}, max_tokens={max_tokens})",
            finish_reason=finish)
    return content


class EmptyContentWithFinish(RuntimeError):
    """Empty completion with the API's finish_reason carried for retry "
    policy (reasoning models can spend the entire cap on hidden reasoning
    tokens; a larger cap on the SAME provider/model is not a downgrade)."""

    def __init__(self, message: str, finish_reason: str = "unknown"):
        super().__init__(message)
        self.finish_reason = finish_reason


def _call_anthropic_flavor(spec: ProviderSpec, messages: List[dict],
                           timeout: int, max_tokens: int,
                           model_override: Optional[str] = None) -> str:
    key = os.environ.get(spec.env_var, "").strip()
    model = model_override or spec.model_for_call()
    system = ""
    msgs = []
    for m in messages:
        if m["role"] == "system":
            system = m["content"]
        else:
            msgs.append(m)
    data = _post_json(
        spec.url_for_call(),
        {"model": model, "max_tokens": max_tokens,
         "messages": msgs, **({"system": system} if system else {})},
        {"x-api-key": key, "anthropic-version": "2023-06-01"}, timeout)
    content = "".join(b.get("text", "") for b in data.get("content", []))
    if not content:
        raise RuntimeError(f"{spec.provider_id} returned empty content")
    return content


_FIELD_RE_CACHE: Dict[int, re.Pattern] = {}


def parse_structured(content: str, schema: Optional[List[str]]) -> Dict[str, Any]:
    """Extract `FIELD: value` lines per schema (the engine's structured-output
    protocol). Missing fields stay absent — never fabricated (Art. VI)."""
    if not schema:
        return {"_raw": content}
    pat = _FIELD_RE_CACHE.get(len(schema)) or re.compile(
        rf'^({"|".join(sorted(schema, key=len, reverse=True))})\s*:\s*(.*)$',
        re.MULTILINE)
    parsed: Dict[str, Any] = {}
    for m in pat.finditer(content):
        parsed[m.group(1).lower()] = m.group(2).strip()
    parsed["_schema_missing"] = [f.lower() for f in schema
                                 if f.lower() not in parsed]
    parsed["_raw"] = content
    return parsed


def generate(prompt: str, system: str = "",
             schema: Optional[List[str]] = None,
             evidence: Optional[List[Dict[str, Any]]] = None,
             policy: Optional[SelectionPolicy] = None,
             timeout: int = 240, max_retries: int = 2,
             max_tokens: int = 512,
             max_provider_fallbacks: int = 2,
             role: Optional[str] = None,
             avoid_provider: Optional[str] = None,
             run_id: Optional[str] = None) -> LLMCallResult:
    """CEO E1 single entry point:
    generate(prompt, evidence, schema) -> structured candidate.
    `evidence` items (already-custodied evidence dicts) are appended to the
    prompt as clearly delimited context; the registry never treats model
    output as evidence (Art. XVIII).
    max_tokens=512 default: the FIELD-line output protocol needs ~150-250
    tokens; a larger cap multiplies wall time on reasoning endpoints without
    improving output quality (measured 2026-08-27).

    R414 (provider-resilience directive §8): MODEL A -> failure ->
    MODEL B -> failure -> MODEL C — every hop classified onto the failure
    taxonomy and recorded. R415 (P0 directive §§3-7): the cascade walks
    (provider, MODEL) rungs built by the routing registry — a provider's
    pinned model answering 410 GONE no longer kills the provider's other
    models: the rung list comes from model_routing.build_ladder (live
    catalog ∩ pinned family allowlist, availability-scored, cooldown-
    demoted-never-removed), each attempt is recorded in the
    MODEL_ROUTING_LEDGER, and a 410 marks that MODEL gone (known-dead from
    the provider's own response) while the provider stays eligible
    (Art. V). Bounded: at most 1 + max_provider_fallbacks + 2 model hops.
    A SUCCESS after failover carries the route (never silent); a total
    failure keeps status CALL_FAILED with the typed failures of every hop
    (Art. XXI.3: a provider failure is never absence, never a verdict).
    Cooldown demotion: providers the health book holds in rate-limit
    cooldown are demoted to the END of the cascade, never removed — the
    engine never refuses to run on a heuristic (Art. V)."""
    from .provider_health import (ROLE_SYNTHESIS, HEALTH, classify_failure,
                                  order_for_role, role_for_purpose)
    from . import model_routing as mr

    # R445-C transport override: ENGINE_LLM_TIMEOUT_S bounds the per-call
    # socket timeout (the R391/R418 operator-override class — explicit,
    # recorded in the call ledger via the route, never silent). Motivation
    # (measured live this round): a provider endpoint that accepts the
    # request and then stalls holds each attempt for the FULL timeout
    # before the cascade can rotate; with the 240 s default and the
    # bounded cascade (3 attempts x up to 5 hops) a single stalling
    # endpoint can consume >1 h for ONE call. A smaller bound (e.g. 90)
    # converts the same failure into a fast rotate. Transport-only:
    # provider selection policy, quality tiers, retry semantics, and
    # epistemic semantics are untouched (same class as ENGINE_*_PROVIDER).
    env_to = os.environ.get("ENGINE_LLM_TIMEOUT_S", "").strip()
    if env_to:
        try:
            timeout = max(5, int(env_to))
        except (TypeError, ValueError):
            pass  # malformed override ignored (recorded policy: no crash)

    # R451-C1.3-3: the effective run-level provenance for THIS call —
    # the explicit run_id parameter or the bound run context (the
    # conductor binds EngineRun's identity; mechanism_space/evolution
    # call sites inherit it without new parameters). run_owned_call =>
    # run_id != null is guaranteed by construction here: a bound
    # context ALWAYS carries a non-null run_id (EngineRun.run_id), and
    # an explicit run_id is non-null by definition.
    from . import call_context as _cctx
    from . import runtime_admission as _ra
    call_prov = _cctx.effective(run_id)

    matrix = availability_matrix()
    avail_ids = [m["provider_id"] for m in matrix
                 if m["available"] and m["cost_policy_eligible"]]
    policy_refusals = [
        {"provider": m["provider_id"], "reason": m["cost_policy_note"]}
        for m in matrix if m["available"] and not m["cost_policy_eligible"]]

    # -- the provider chain (policy order, then role ordering) -------------
    if policy and policy.preferred_providers:
        chain = [pid for pid in policy.preferred_providers
                 if pid in avail_ids]
        chain_source = "policy.preferred_providers"
    else:
        eff_role = role or (role_for_purpose(
            policy.purpose if policy else "") if policy else None) \
            or ROLE_SYNTHESIS
        chain = order_for_role(matrix, eff_role,
                               avoid_provider=avoid_provider)
        chain_source = f"role_order:{eff_role}"
    # cooldown demotion applies to BOTH chain sources: a rate-limited
    # provider slides to the end (never removed — a lone cooled provider
    # is still tried; Art. V)
    if len(chain) > 1:
        cooled = [p for p in chain if HEALTH.in_cooldown(p)]
        if cooled:
            chain = [p for p in chain if p not in cooled] + cooled
    # R451 §1: the cost policy REFUSES ineligible rungs — including the
    # ones the ladder would add beyond the policy chain (LAST_RESORT
    # rungs, preferred pins pointing at paid providers). A paid route
    # is never silently fallen back to; the refusals travel in the
    # ledger (fail-closed, Art. IV/VII).
    chain, _chain_refusals = _cost_policy.filter_chain(
        chain, _SPEC_BY_ID)
    # R451-C1.1: a preferred chain that named ONLY policy-ineligible
    # (paid) providers does not dead-end the call when an ELIGIBLE
    # zero-paid route exists — the chain is EXTENDED with the eligible
    # providers (the extension is recorded in every ledger; it only
    # ever adds cost-eligible rungs, never paid ones — the historical
    # synthesis pin ['openrouter', 'deepseek', ...] must not turn the
    # zero-paid policy into POLICY_BLOCKED while localqwen serves)
    cost_policy_chain_extension = [p for p in avail_ids
                                   if p not in chain] if not chain else []
    if cost_policy_chain_extension:
        chain = list(cost_policy_chain_extension)
    if not chain:
        # preferred_providers exhausted or policy-refused with no
        # eligible provider: keep the historical honest semantics (no
        # silent widening beyond the operator's list — Art. IV) and
        # name the COST POLICY refusal when that is the cause
        _, ledger = select_provider(policy)
        any_avail = any(m["available"] for m in matrix)
        return LLMCallResult(
            status=(ST_POLICY_BLOCKED if any_avail
                    else ST_PROVIDER_UNAVAILABLE),
            error=(
                f"the active cost policy "
                f"{_cost_policy.active_policy()} refused every "
                f"available provider — paid routes are never silently "
                f"used (R451 §1)" if any_avail else
                "no provider credential available (see selection_ledger)"),
            prompt_hash=_sha(prompt),
            selection_ledger={**ledger,
                              "cost_policy_refusals": policy_refusals
                              or ledger.get("cost_policy_refusals")},
            call_provenance=call_prov)

    # -- R415: the (provider, model) rung list from the routing registry --
    eff_role = role or (role_for_purpose(
        policy.purpose if policy else "") if policy else None) \
        or ROLE_SYNTHESIS
    task = mr.task_class_for_role(eff_role)
    purpose_tag = (policy.purpose if policy else "") or eff_role
    ladder = mr.build_ladder(
        task, role=eff_role, avoid_provider=avoid_provider,
        preferred_providers=list(chain),
        available_providers=avail_ids)
    rungs = [(r["provider"], r["model"], r) for r in ladder["rungs"]]
    # R451: policy-filter the rungs (the ladder's LAST_RESORT band may
    # add providers the policy chain never asked for — paid models are
    # refused here too, with each refusal recorded on the ladder)
    _rung_refusals = []
    _rungs_kept = []
    for provider_id, model_id, r in rungs:
        spec_r = _SPEC_BY_ID.get(provider_id)
        ok_r, note_r = _cost_policy.provider_eligibility(spec_r) \
            if spec_r else (False, "unknown provider")
        if ok_r:
            _rungs_kept.append((provider_id, model_id, r))
        else:
            _rung_refusals.append({"provider": provider_id,
                                   "model": model_id,
                                   "reason": note_r})
    rungs = _rungs_kept
    ladder.setdefault("cost_policy", _cost_policy.active_policy())
    ladder.setdefault("cost_policy_rung_refusals", _rung_refusals)
    # the ladder may add last-resort providers beyond the policy chain
    # (the directive's LAST-RESORT rung); bound the walk:
    # 1 + max_provider_fallbacks + 2 model hops
    rungs = rungs[:max(3, 1 + max(0, max_provider_fallbacks) + 2)]
    if not rungs:
        return LLMCallResult(
            status=ST_PROVIDER_UNAVAILABLE,
            error="no routing rung available for this task "
                  "(see selection_ledger)",
            prompt_hash=_sha(prompt),
            selection_ledger={"chain": list(chain),
                              "ladder": ladder},
            call_provenance=call_prov)

    # R451-C1.3-1: persisted capability evidence for every rung of the
    # ladder the walk considered (the acceptance gate: capability
    # evidence is persisted — read-only snapshot BEFORE any probing)
    ladder["capability_evidence"] = _ra.ladder_capability_evidence(
        [{"provider": p, "model": m} for p, m, _meta in rungs])

    wanted_head = rungs[0][0]

    messages: List[dict] = []
    # Constitutional transport contract: engine LLM output is ENGLISH ONLY
    # (CEO standing rule) and must follow the requested format exactly.
    # Callers may pass a richer system prompt; this directive is PREPENDED,
    # never substituted.
    system_directive = ("RESPOND IN ENGLISH ONLY. Follow the requested "
                        "output format exactly; no preamble, no markdown "
                        "fences.")
    system = f"{system_directive}{(' ' + system) if system else ''}"
    if system:
        messages.append({"role": "system", "content": system})
    body = prompt
    if evidence:
        ev_block = "\n\n".join(
            f"[EVIDENCE {e.get('id', i)}]\n{(e.get('abstract') or e.get('content') or '')[:1500]}"
            for i, e in enumerate(evidence[:3]))
        body = f"{prompt}\n\n=== RETRIEVED EVIDENCE (custodied) ===\n{ev_block}"
    messages.append({"role": "user", "content": body})

    route: List[Dict[str, Any]] = []
    last_err = None
    last_failure_type = None
    # R451-C1.4: the task-degradation record of the rung that actually
    # served (or the last attempted rung when everything fails)
    last_degradation: Optional[Dict[str, Any]] = None

    def _degradation_record(rung_meta: Dict[str, Any]) -> Dict[str, Any]:
        """R451-C1.4: requested task vs the SERVING model's capability —
        never silently use a CHEAP model as a STRONG model. The
        emergency fallback stays PERMITTED (the system may continue
        under an explicitly recorded emergency policy) but the
        downgrade is visible in provenance and final scientific
        records."""
        caps = list(rung_meta.get("task_capabilities") or [])
        match = task in caps
        if match:
            actual = task
            reason = ("the serving model declares the requested "
                      "task capability")
        elif caps:
            actual = ("CHEAP_EMERGENCY_FALLBACK"
                      if task == mr.TASK_STRONG else caps[0])
            reason = (
                f"requested {task}; the serving model declares only "
                f"{caps} — the call ran under the explicitly permitted "
                f"emergency fallback (R451-C1.4): downstream readers "
                f"must NOT interpret the result as {task}-class "
                f"reasoning")
        else:
            actual = "UNKNOWN"
            reason = "the serving model declares no task capabilities"
        return {
            "requested_task": task,
            "actual_task_capability": actual,
            "task_capability_match": match,
            "degraded_reason": reason,
        }

    for hop_idx, (provider_id, model_id, rung_meta) in enumerate(rungs):
        spec = _SPEC_BY_ID.get(provider_id)
        if spec is None:
            continue
        next_rung = rungs[hop_idx + 1] if hop_idx + 1 < len(rungs) \
            else None
        next_provider = next_rung[0] if next_rung else None
        next_model = next_rung[1] if next_rung else None
        # a rung whose model is recorded GONE is skipped (known-dead from
        # the provider's own 410 — a recorded fact, not a heuristic)
        if mr.is_model_gone(provider_id, model_id):
            continue
        # -- R451-C1.3-1: RUNTIME ADMISSION — a route requires a CURRENT
        # measured successful capability probe; credential presence is
        # NOT admissibility. NOT_PROBED / PROBE_EXPIRED rungs are probed
        # HERE (lazily, only when the walk reaches them — the TTL
        # mechanism means at most one probe per route per window, never
        # one per call). PROBE_FAILED / POLICY_REFUSED rungs are skipped
        # with the state recorded on the route (never a silent skip). The
        # LOCAL route uses the SAME rule — no bespoke local exception.
        #
        # Transient-failure absorption (the old cascade's measured
        # resilience, applied to the admission authority): a probe that
        # fails with a TRANSIENT class (NETWORK_FAILURE / TIMEOUT /
        # RATE_LIMITED) is retried within the SAME bounded walk with the
        # same backoff the real-call path uses — a ~5 s server restart
        # window must not lock the route out for the TTL (the acceptance
        # run's measured defect). PERMANENT classes (AUTH_FAILURE, GONE,
        # MODEL_NOT_FOUND, CREDIT_EXHAUSTED) are never retried.
        if _ra.requires_probe(provider_id, model_id):
            _ra.probe_capability(provider_id, model_id,
                                 timeout_s=min(timeout, 30))
            _tries = 0
            while (_tries < max_retries
                   and _ra.probe_failure_is_transient(
                       provider_id, model_id)):
                time.sleep(2 * (_tries + 1))
                _ra.probe_capability(provider_id, model_id,
                                     timeout_s=min(timeout, 30))
                _tries += 1
        _adm, _adm_note, _adm_ev = _ra.runtime_admission(
            provider_id, model_id)
        if not _adm:
            # the probe's own typed failure class (when the state is
            # PROBE_FAILED) rides the hop — the route stays fully
            # reconstructable: WHY this rung was refused is a measured
            # class, never a bare "not admitted"
            _probe_ftype = ((_adm_ev.get("record") or {}).get(
                "failure_class") if _adm_ev.get("state") == "PROBE_FAILED"
                else None)
            route.append({
                "provider_attempted": spec.provider_id,
                "model": model_id,
                "status": "SKIPPED_NOT_ADMITTED",
                "failure_type": _probe_ftype,
                "capability_state": _adm_ev.get("state"),
                "timestamp": utc_now(),
                "retry_count": 0,
                "attempts": 0,
                "latency_ms": 0,
                "error": _adm_note[:300],
                "fallback_provider": next_provider,
                "fallback_model": next_model,
                "fallback_reason": (
                    f"runtime admission refused ({_adm_note[:160]}) -> "
                    f"fallback to {next_provider or 'none (last rung)'}"),
                "cost_class": spec.cost_basis,
                "selected": False,
                "rung_band": rung_meta.get("band"),
                "task": task,
            })
            last_err = (f"runtime admission refused for {provider_id}/"
                        f"{model_id}: {_adm_note}")
            last_failure_type = None
            continue
        degradation = _degradation_record(rung_meta)
        last_degradation = degradation
        attempt_budget = max_tokens
        retry_notes: List[str] = []
        hop_t0 = time.time()
        attempt = 0
        for attempt in range(max_retries + 1):
            t0 = time.time()
            try:
                if spec.flavor == "anthropic":
                    content = _call_anthropic_flavor(
                        spec, messages, timeout, attempt_budget,
                        model_override=model_id)
                else:
                    content = _call_openai_flavor(
                        spec, messages, timeout, attempt_budget,
                        model_override=model_id)
                latency_ms = int((time.time() - t0) * 1000)
                HEALTH.record_success(
                    spec.provider_id, latency_ms,
                    purpose=purpose_tag,
                    model=model_id)
                mr.record_call_outcome(
                    provider_id, model_id, ok=True,
                    latency_ms=latency_ms, task=task, stage=purpose_tag,
                    run_id=call_prov["run_id"], attempt=attempt + 1,
                    cost_class=spec.cost_basis, selected=True,
                    session_id=call_prov["session_id"],
                    engine_stage=call_prov["engine_stage"],
                    call_class=call_prov["call_class"],
                    account_domain=spec.account_domain,
                    task_degradation=degradation,
                    capability_state="PROBE_OK")
                # R451 §6: the SUCCESSFUL hop is part of the route too —
                # the in-result route must reconstruct the exact path
                # (every failure first, then the selected provider),
                # never a bare "models unavailable" summary
                route.append({
                    "provider_attempted": spec.provider_id,
                    "model": model_id,
                    "status": "OK",
                    "failure_type": None,
                    "timestamp": utc_now(),
                    "retry_count": attempt,
                    "attempts": attempt + 1,
                    "latency_ms": latency_ms,
                    "error": None,
                    "fallback_provider": None,
                    "fallback_model": None,
                    "fallback_reason": "",
                    "cost_class": spec.cost_basis,
                    "account_domain": spec.account_domain,
                    "selected": True,
                    "rung_band": rung_meta.get("band"),
                    "task": task,
                    "task_degradation": degradation,
                    "capability_state": "PROBE_OK",
                })
                # a successful real call is a STRONGER capability
                # measurement than the probe — refresh the TTL window
                # (runtime_admission.record_capability source=real_call)
                try:
                    _ra.record_capability(
                        provider_id, model_id, ok=True,
                        latency_ms=latency_ms, source="real_call")
                except Exception:  # noqa: BLE001 — telemetry best-effort
                    pass
                # success after a failed hop is OK ONLY with the route
                # disclosing every failure that preceded it (never a
                # silent failover — directive §8)
                return LLMCallResult(
                    status=ST_OK, content=content,
                    provider_id=spec.provider_id,
                    model=model_id,
                    prompt_hash=_sha(body), output_hash=_sha(content),
                    latency_ms=latency_ms,
                    substituted_from=(
                        wanted_head if wanted_head != spec.provider_id
                        else None),
                    selection_ledger={
                        "chain": list(chain),
                        "chain_source": chain_source,
                        "cost_policy_chain_extension":
                            list(cost_policy_chain_extension),
                        "cost_policy_refusals": policy_refusals,
                        "ladder": ladder,
                        "availability": matrix,
                    },
                    retry_notes=retry_notes,
                    route=route or None,
                    failure_type=None,
                    cost_provenance=_cost_policy.cost_provenance(
                        spec, model_id),
                    call_provenance=call_prov,
                    task_degradation=degradation)
            except EmptyContentWithFinish as exc:
                last_err = f"{type(exc).__name__}: {exc}"
                ftype = classify_failure(exc)
                # reasoning-token exhaustion: SAME provider/model, larger
                # cap (recorded in retry_notes — never a silent change)
                if attempt_budget < 2048:
                    attempt_budget = min(2048, attempt_budget * 4)
                    retry_notes.append(
                        f"attempt {attempt + 1}: empty content "
                        f"(finish_reason={exc.finish_reason}); same "
                        f"provider/model retried with max_tokens="
                        f"{attempt_budget}")
                if attempt < max_retries:
                    time.sleep(2 * (attempt + 1))
                    continue
            except Exception as exc:  # noqa: BLE001 — recorded, retried
                last_err = f"{type(exc).__name__}: {exc}"
                ftype = classify_failure(exc)
                # GONE (410) / MODEL_NOT_FOUND (404 or the provider's
                # own model_not_found body — R451-C1.2): the identifier
                # is known-dead on this route — retrying the SAME dead
                # model wastes the budget (operator directive: never
                # retry a permanently invalid model identifier). Skip
                # the same-model retry (fall straight through to the hop
                # RECORDING and the next rung); the hop must still be
                # recorded — a dead id that is silently skipped would be
                # exactly the unrecorded-failover the directive forbids.
                if ftype not in ("GONE", "MODEL_NOT_FOUND") \
                        and attempt < max_retries:
                    time.sleep(2 * (attempt + 1))
                    continue
            # this attempt exhausted the same-model budget -> record
            # the hop honestly and move to the next rung
            HEALTH.record_failure(
                spec.provider_id, ftype,
                purpose=purpose_tag,
                model=model_id, error=str(last_err))
            mr.record_call_outcome(
                provider_id, model_id, ok=False,
                latency_ms=int((time.time() - hop_t0) * 1000),
                failure_type=ftype, task=task, stage=purpose_tag,
                run_id=call_prov["run_id"], attempt=attempt + 1,
                session_id=call_prov["session_id"],
                engine_stage=call_prov["engine_stage"],
                call_class=call_prov["call_class"],
                account_domain=spec.account_domain,
                task_degradation=degradation,
                capability_state="PROBE_OK",
                fallback_from=(provider_id if next_provider else None),
                fallback_to=next_provider,
                error=str(last_err),
                cost_class=spec.cost_basis, selected=False,
                fallback_reason=(
                    f"{ftype}: {str(last_err)[:160]} -> fallback to "
                    f"{next_provider or 'none (last rung)'}"))
            # a real-call transport failure invalidates the capability
            # record so the NEXT admission re-probes instead of trusting
            # the stale probe success (the R415 clear_probe_cache
            # discipline, applied to the runtime authority)
            if ftype not in ("INVALID_RESPONSE", "PARSER_FAILURE"):
                try:
                    _ra.invalidate_capability(
                        provider_id, model_id,
                        reason=f"real-call failure class {ftype}")
                except Exception:  # noqa: BLE001
                    pass
            route.append({
                "provider_attempted": spec.provider_id,
                "model": model_id,
                "status": "FAILED",
                "failure_type": ftype,
                "timestamp": utc_now(),
                "retry_count": attempt,
                "attempts": attempt + 1,
                "latency_ms": int((time.time() - hop_t0) * 1000),
                "error": str(last_err)[:300],
                "fallback_provider": next_provider,
                "fallback_model": next_model,
                "fallback_reason": (
                    f"{ftype}: {str(last_err)[:160]} -> fallback to "
                    f"{next_provider or 'none (last rung)'}"),
                "cost_class": spec.cost_basis,
                "account_domain": spec.account_domain,
                "selected": False,
                "rung_band": rung_meta.get("band"),
                "task": task,
                "task_degradation": degradation,
                "capability_state": "PROBE_OK",
            })
            last_failure_type = ftype
            break

    # every rung failed: CALL_FAILED with the full typed route (a
    # provider outage is infrastructure, never a verdict — the CALLER
    # decides meaning; Art. XXI.3 / LXI)
    last_spec = _SPEC_BY_ID.get(rungs[-1][0]) if rungs else None
    return LLMCallResult(
        status=ST_CALL_FAILED, error=last_err,
        provider_id=(rungs[-1][0] if rungs else None),
        model=(rungs[-1][1] if rungs else None),
        prompt_hash=_sha(body),
        selection_ledger={"chain": list(chain),
                          "chain_source": chain_source,
                          "cost_policy_chain_extension":
                              list(cost_policy_chain_extension),
                          "cost_policy_refusals": policy_refusals,
                          "ladder": ladder,
                          "availability": matrix},
        retry_notes=[],
        route=route or None,
        failure_type=last_failure_type,
        cost_provenance=(
            _cost_policy.cost_provenance(last_spec, rungs[-1][1])
            if last_spec else None),
        call_provenance=call_prov,
        task_degradation=last_degradation)


def availability_statement() -> Dict[str, Any]:
    """Compact statement for run manifests: which capabilities are blocked
    purely by credentials, and which env keys would unblock them.
    R451: also the cost-policy state — which providers the ACTIVE
    policy would refuse even with credentials present."""
    matrix = availability_matrix()
    return {
        "any_provider_available": any(m["available"] for m in matrix),
        "available_providers": [m["provider_id"] for m in matrix if m["available"]],
        "unblock_with_env": [m["env_var"] for m in matrix if not m["available"]],
        "cost_policy": _cost_policy.active_policy(),
        "cost_policy_eligible_providers": [
            m["provider_id"] for m in matrix
            if m["available"] and m["cost_policy_eligible"]],
        "cost_policy_refused_providers": [
            {"provider": m["provider_id"],
             "reason": m["cost_policy_note"]}
            for m in matrix
            if m["available"] and not m["cost_policy_eligible"]],
        "evaluated_at": utc_now(),
    }

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
import threading
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
    #: owner-confirmed date for the cost basis (FREE_TIER_API is a
    #: dated owner statement, never an assumption)
    cost_basis_date: str = ""
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
    #: R456-A3: transport-only request HEADERS merged into every call
    #: (chat, probe, catalog). The measured need: xkiro.com and
    #: apinex.bond sit behind Cloudflare browser-signature checks —
    #: the default python urllib UA is banned with error 1010 while a
    #: standard browser UA passes (measured 2026-09-14: /models 403
    #: 1010 with urllib UA, 200 with a Chrome UA). Transport plumbing
    #: only — never evidence, never semantics.
    extra_headers: Optional[Dict[str, str]] = None
    #: R469 (the six-item minimum path): the capability probe's token
    #: budget for THIS rung. The shared probe spends 16 tokens — enough
    #: for a plain completion, but a REASONING model spends its whole
    #: budget on hidden reasoning at 16 and returns content=null, which
    #: would fail the probe for a rung that is in fact alive (the
    #: measured EmptyContentWithFinish class — atria's FIELD test
    #: starves content at max_tokens 300). Rungs that need more declare
    #: it here; every other rung keeps the 16-token probe. Consumed by
    #: runtime_admission.probe_capability (typed fallback to 16).
    probe_max_tokens: int = 16

    #: R483 (the EmptyContentWithFinish class): the SAME-model retry
    #: ceiling for reasoning-token exhaustion — the x4 bump ladder's
    #: cap. The standing default 2048 is unchanged for every existing
    #: provider; a reasoning model whose measured failures terminate
    #: at 2048 with finish_reason=length declares a larger ceiling
    #: (the class docstring's own rule: a larger cap on the SAME
    #: provider/model is not a downgrade).
    reasoning_retry_ceiling: int = 2048
    #: R469: the provider's CREDENTIAL RING — the ordered env-var
    #: names the transport rotates through on exhaustion-class
    #: failures (the operator's keep-going directive: "Keep going to
    #: a new key of atira if one is exhausted"). None/empty degrades
    #: to [env_var] (single-key — every pre-R469 provider is exactly
    #: this). The availability marker stays env_var (the FIRST ring
    #: slot); every rotation is a recorded route hop, never silent
    #: (Art. IV).
    key_env_vars: Optional[List[str]] = None

    def url_for_call(self) -> str:
        """Effective endpoint for this call.

        R391 (deployment): an EXPLICIT operator override `{PROVIDER}_BASE_URL`
        re-points a provider slot at a public OpenAI-compatible endpoint —
        the mechanism that lets a hosted engine use the same registry
        without the sandbox-local gateway. Transport-only: provider
        selection policy, quality tiers, and epistemic semantics are
        untouched (same operator-override class as the ENGINE_*_PROVIDER
        pins — recorded, never silent).

        R453-LEAN-CORE (the external auditor mandate, "one generate()
        contract — a single documented base URL"): when no override is
        set, the provider's OWN env_var (the availability marker) is
        honored as the URL if it carries one. This closes the dual-
        variable footgun measured live in R452-A3 (LOCAL_QWEN_BASE_URL
        the availability marker vs LOCALQWEN_BASE_URL the URL override:
        drivers that set only the marker silently called the spec's
        DEFAULT port while the actual server lived elsewhere). ONE
        documented variable per provider is now sufficient — the
        override remains the explicit escape hatch, never a second
        required configuration."""
        override = (os.environ.get(
            f"{self.provider_id.upper()}_BASE_URL", "").strip())
        if override:
            return override
        marker = (os.environ.get(self.env_var, "").strip())
        if "://" in marker:
            return marker
        return self.url

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
            "LOCAL_QWEN_BASE_URL when it owns the server — R453-LEAN: "
            "that ONE documented variable is BOTH the availability "
            "marker AND the endpoint URL (a second override variable "
            "is no longer required; the dual-variable footgun is "
            "closed in url_for_call). Thinking mode "
            "DISABLED via chat_template_kwargs (measured: Qwen3's default "
            "thinking leaks meta-commentary into FIELD lines). Cost basis "
            "ZERO_PAID_COST_SELF_HOSTED: self-hosted weights, local "
            "inference, no per-token billing of any kind — the ONLY basis "
            "eligible under MODEL_COST_POLICY=ZERO_PAID_COST.")),
    ProviderSpec(
        "inception", "INCEPTION_API_KEY",
        "https://api.inceptionlabs.ai/v1/chat/completions",
        "mercury-3", "openai", 128_000,
        quality_tier=2, cost_tier=1, latency_tier=1,
        cost_basis="FREE_TIER_API", cost_basis_date="2026-11-10",
        locality="REMOTE",
        license="provider serving terms (operator-supplied key)",
        account_domain="OWNER_INCEPTION_ACCOUNT",
        model_revision="mercury-3 measured live 2026-11-10 (tiny "
                       "completion OK at 64 tokens); no per-model revision "
                       "pin exposed by the router - recorded honest "
                       "(Art. VI)",
        probe_max_tokens=64,
        policy_note=(
            "R1 infra (operator-supplied): Inception Labs Mercury 3, "
            "used alongside agnes. LIVE-MEASURED at registration "
            "(Art. III): GET /v1/models -> 200 with 4 mercury-* models; "
            "mercury-3 tiny completion -> 200 OK at 64 tokens (content "
            "starves at 16 - probe_max_tokens=64). Default urllib UA "
            "passes (no CF block). Tiers recorded policy inputs "
            "(Art. XXVII).")),
    ProviderSpec(
        "agnes", "AGNES_API_KEY",
        "https://apihub.agnes-ai.com/v1/chat/completions",
        "agnes-3.0-flash", "openai", 128_000,
        quality_tier=2, cost_tier=1, latency_tier=2,
        cost_basis="FREE_TIER_API", locality="REMOTE",
        license="provider serving terms (operator-supplied key; "
                "flash served at $0 balance, pro gated)",
        account_domain="OWNER_AGNES_ACCOUNT",
        model_revision="agnes router; agnes-3.0-flash / agnes-2.5-flash "
                       "/ agnes-2.0-flash measured live 2026-09-26 "
                       "(tiny completions + 3/3 FIELD-line compliance); "
                       "no per-model revision pin exposed by the router "
                       "— recorded honest (Art. VI)",
        probe_max_tokens=64,
        policy_note=(
            "R539 operator-supplied router #9 (agnes, apihub.agnes-ai."
            "com) — the operator's number-1 API. LIVE-MEASURED at "
            "registration (Art. III): GET /v1/models -> 200 with 12 "
            "agnes-* models; agnes-3.0-flash tiny completion -> 200 OK "
            "non-empty 0.95-6.2 s; agnes-2.5-flash -> 200 OK (content "
            "starves at cap 16, answers at cap 64 — probe_max_tokens=64 "
            "declared); agnes-2.0-flash -> 200 OK 0.48 s; the three "
            "pro rungs -> 403 insufficient_user_quota $0.000000 "
            "(per-model credit gate, CREDIT_EXHAUSTED, cascade "
            "advances). FIELD-line protocol 3/3 clean on both flash "
            "rungs (1.11 s / 0.77 s) — the STRONG-rung measurement. "
            "Default urllib User-Agent passes (no CF block). Tiers are "
            "recorded policy inputs (Art. XXVII).")),
    ProviderSpec(
        "unorouter", "UNOROUTER_API_KEY",
        "https://api.unorouter.com/v1/chat/completions",
        "glm-5.3:free", "openai", 128_000,
        quality_tier=2, cost_tier=1, latency_tier=2,
        cost_basis="FREE_TIER_API", locality="REMOTE",
        license="provider serving terms (free tier, no deposit)",
        account_domain="OWNER_UNOROUTER_ACCOUNT",
        model_revision="router free tier; glm-5.3:free measured live "
                       "2026-09-14 (tiny completion 3.9 s); no per-model "
                       "revision pin exposed by the router — recorded "
                       "honest (Art. VI)",
        policy_note=(
            "R456-A3 operator-supplied free-tier router #1. LIVE-MEASURED "
            "at registration (Art. III): GET /v1/models -> 200 with 244 "
            "models incl. the :free family (glm-5.3:free, glm-5.3-flash:"
            "free, qwen3.8-27b:free, glm-5.2:free...); glm-5.3:free tiny "
            "completion -> 200 PROBE_OK 3.9 s; glm-5.3-thinking:free -> "
            "200 PROBE_OK 6.2 s (110 reasoning tokens). Free-pool "
            "congestion measured as HTTP 403 'This model is busy right "
            "now (free providers hit their rate limit). Please try again "
            "in a little while, or switch to another model' — the "
            "provider's own remedy IS the cascade rotation; classified "
            "RATE_LIMITED (the measured specimen rides "
            "provider_health). Default urllib User-Agent passes (no CF "
            "block on api.unorouter.com). glm-5.3:free is the STRONG "
            "rung (the same GLM-5.3 flagship class the zai env contract "
            "serves); the thinking variant is NOT the default (the "
            "engine's FIELD-line protocol prefers non-reasoning output). "
            "Tier assignments are recorded policy inputs (Art. XXVII). "
            "FREE_TIER_API under the R456-A3 operator amendment: "
            "eligible under ZERO_PAID_COST; depletion stays a typed "
            "failure that advances the cascade — never a bill.")),
    ProviderSpec(
        "xkiro", "XKIRO_API_KEY",
        # R8 credential round 2026-11-13: the DOCS-named OpenAI-SDK base
        # is https://api.xkiro.com/v1; the legacy xkiro.com host answers
        # the SAME validator (measured live: byte-identical 401 bodies
        # on both hosts, both header schemes). The spec re-points to the
        # documented host — recorded, never silent (Art. XXV).
        "https://api.xkiro.com/v1/chat/completions",
        # R8 re-point 2026-11-13: the 2026-09-14 default qwen/
        # qwen3.8-max:free is NO LONGER in the catalog (fresh /v1/models
        # = 69 models, ZERO qwen/*, minimax/* or z-ai/* namespaces — the
        # catalog drifted); the default names the MEASURED serving rung
        # instead (mistralai/ministral-14b: live 2026-11-10, judge
        # calibration 27/30) — the owner's measured "mistral free tier"
        # (all eight mistralai models free per the gateway's deals page,
        # fetched 2026-11-13).
        "mistralai/ministral-14b", "openai", 128_000,
        quality_tier=2, cost_tier=1, latency_tier=2,
        cost_basis="FREE_TIER_API", locality="REMOTE",
        license="provider serving terms (free tier, no deposit)",
        account_domain="OWNER_XKIRO_ACCOUNT",
        model_revision="router free tier; mistralai/ministral-14b is the "
                       "measured serving rung (2026-11-10 live, judge "
                       "calibration 27/30); no per-model revision pin "
                       "exposed by the router — recorded honest (Art. VI)",
        extra_headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/131.0.0.0 Safari/537.36"},
        policy_note=(
            "R456-A3 operator-supplied free-tier router #2. TRANSPORT "
            "REQUIREMENT (measured): xkiro.com sits behind a Cloudflare "
            "browser-signature check — the default python urllib UA is "
            "banned (403 error 1010 on every endpoint) while a standard "
            "Chrome UA passes; the spec's extra_headers carries that UA "
            "on EVERY call, probe, and catalog fetch (transport plumbing "
            "only). R8 CREDENTIAL ROUND (measured live 2026-11-13, probe "
            "record ENGINE_RUNS/r8_xkiro_mercury3_probe.json + curl "
            "variants): (a) KEYLESS SERVING IS DEAD — the chat endpoint "
            "answers 401 'Missing ClientApiKey. Send \"Authorization: "
            "Bearer <key>\" or the x-api-key header.' on EVERY "
            "unauthenticated call (the 2026-11-12 keyless measurement is "
            "history, not current fact); (b) the owner's supplied "
            "credential (dashboard key 'Mercury 3', named for the "
            "mistral free tier the owner intends) answers 401 'Invalid "
            "or disabled ClientApiKey' on BOTH hosts and BOTH documented "
            "header schemes — the validator itself rejects it: the key "
            "is disabled/invalid/incomplete dashboard-side and NOTHING "
            "this repository can do heals that (typed AUTH_FAILURE, a "
            "dashboard-side act, Art. LXI); (c) the fresh catalog is 69 "
            "models — NO mercury id exists on this gateway at all (the "
            "owner's 'Mercury 3' name resolves to nothing servable "
            "here; the 2026-11-12 mercury removal on the INCEPTION path "
            "stays scoped there); (d) the MISTRAL FREE TIER is real per "
            "the gateway's own deals page ('All eight Mistral models "
            "are free on xKiro: Mistral Large, Medium 3.5, Small, "
            "Codestral, Devstral Medium and the Ministral 14B / 8B / 3B "
            "family', fetched 2026-11-13; 500K tokens/day free plan) — "
            "the moment a VALID credential sits in XKIRO_API_KEY the "
            "registry picks it up at call time with ZERO code change "
            "(the queue runner loads the gitignored vault at startup); "
            "the allowlist is NOT extended to the unmeasured mistral "
            "ids (premium-precedent: measured ids only — the whole free "
            "family is one measurement away). (e) RESOLUTION, same "
            "round: the owner supplied a SECOND dashboard credential "
            "(the sk-xt- form; the value lives ONLY in the gitignored "
            "vault, never in tracked bytes) and it VALIDATES — measured "
            "live 2026-11-13: mistralai/ministral-14b tiny -> 200 OK "
            "0.57 s (content 'READY', finish=stop); mistralai/"
            "ministral-8b tiny -> 200 OK 0.46 s; LONG-FORM at 420 AND "
            "1000 max_tokens — the exact protocol where mercury "
            "starved — BOTH rungs serve COMPLETE answers (ministral-"
            "14b: 1437-1510 content chars, 5.7-6.0 s, finish=stop; "
            "ministral-8b: 1301-1449 chars, 2.1-2.6 s, finish=stop); "
            "the engine's own admission probe through the vault-loaded "
            "path -> ok=True fields_ok=True 622 ms. The committed judge "
            "rung (mistralai/ministral-14b) is CREDENTIALED AND "
            "SERVING; the other free mistral ids stay one measurement "
            "away. "
            "LIVE-MEASURED at registration: GET /v1/models -> 200 "
            "with 109 namespaced models (qwen/*, minimax/*, z-ai/*, "
            "deepseek/*, anthropic/*...); qwen/qwen3.8-max:free tiny "
            "completion -> 200 PROBE_OK 3.2 s; minimax/minimax-m3:free "
            "-> 200 PROBE_OK 3.4 s; qwen/qwen3-max:free -> 200 PROBE_OK "
            "2.9 s. Premium (non-:free) models answer 403 'requires real "
            "deposited balance' — classified CREDIT_EXHAUSTED, the "
            "cascade advances (the rung is per-model gated, the provider "
            "stays eligible). minimax m2.x :free variants return empty "
            "content with reasoning_content at small caps (reasoning "
            "models — EmptyContentWithFinish handles the retry class). "
            "qwen3.8-max is the STRONG rung (the MAX tier is Qwen's "
            "flagship class). Tiers are recorded policy inputs "
            "(Art. XXVII).")),
    ProviderSpec(
        "hf", "HF_TOKEN",
        "https://router.huggingface.co/v1/chat/completions",
        "openai/gpt-oss-120b", "openai", 128_000,
        quality_tier=2, cost_tier=1, latency_tier=2,
        cost_basis="FREE_TIER_API", locality="REMOTE",
        license="provider serving terms (monthly included credits; "
                "pre-paid top-up available)",
        account_domain="HF_ACCOUNT_CREDITS",
        model_revision="served-by-provider; openai/gpt-oss-120b and "
                       "zai-org/GLM-5.3 are the catalog-verified strong "
                       "rungs (2026-09-15 catalog); no per-model revision "
                       "pin exposed by the router — recorded honest "
                       "(Art. VI)",
        policy_note=(
            "R463 the user's OWN Hugging Face credential (HF_TOKEN) on "
            "the Inference Providers router — the P0 architectural "
            "ruling's one legitimate credential path. LIVE-MEASURED at "
            "registration (R463/PROBE_HF_ROUTER.json): whoami-v2 -> 200 "
            "(fine-grained token, inference.serverless.write present); "
            "GET /v1/models -> 200 with 142 models incl. openai/"
            "gpt-oss-120b, zai-org/GLM-5.3, deepseek-ai/DeepSeek-V3.2, "
            "Qwen/Qwen3-235B-A22B-Instruct-2507, meta-llama/"
            "Llama-3.3-70B-Instruct; tiny completions on BOTH strong "
            "rungs -> HTTP 402 'You have depleted your monthly included "
            "credits. Purchase pre-paid credits to continue using "
            "Inference Providers.' — the R436 CREDIT_EXHAUSTED class on "
            "the WHOLE account domain (R450 measured precedent: every "
            "model behind one HF account bills the same included "
            "credits). The account domain is HF_ACCOUNT_CREDITS — NOT "
            "redundant with any other router (one budget kills every "
            "rung behind it), which is exactly why the cascade keeps "
            "the independent account domains. Default urllib "
            "User-Agent passes (no CF block on router.huggingface.co). "
            "HONEST TIERS: quality_tier 2 (the STRONG rung is the "
            "gpt-oss-120b flagship class — the claim is about the "
            "catalog-class model, unmeasured on the engine's protocol "
            "while credits are depleted; the tier claim is the "
            "recorded policy input, Art. XXVII). The rung serves "
            "automatically when the account's credits reset or are "
            "topped up — no code change, no new secret.")),
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


# --------------------------------------------------------------------------
# R469: THE KEY RING — multi-credential rotation on one provider.
#
# Operator directive (2026-09-16, verbatim):
#   "From Now on atira is out default API for discovery engine. Keep
#    going to a new key of atira if one is exhausted. Wire it in the
#    discovery engine."
#
# A provider whose operator holds MULTIPLE keys for the same account
# surface registers them as an ordered ring. An EXHAUSTION-class
# failure on one slot rotates to the next PRESENT slot on the SAME
# rung (same provider, same model) BEFORE any provider-level fallback
# — the ring is consumed key by key, exactly the directive's order.
# Every rotation is a recorded route hop (status
# FAILED_KEY_EXHAUSTED + action KEY_ROTATED) and a routing-ledger
# event; a ring that exhausts entirely falls through to the standing
# cascade (typed failure, never a bill, never silent). The sticky
# slot is PROCESS state: a rotated-forward ring does not re-pay the
# exhausted key's round-trip on every call, and a fully exhausted
# ring RESETS to the first present slot so the next call re-measures
# the head key (budgets reset; exhaustion is never persisted as a
# fact — the cooldown discipline, Art. V).
# --------------------------------------------------------------------------
KEY_ROTATION_FAILURE_CLASSES = frozenset({
    "CREDIT_EXHAUSTED",   # 402 / credit wording — THIS key's budget
    "AUTH_FAILURE",       # 401 — THIS key revoked/invalid
    "RATE_LIMITED",       # 429 — often per-key on free routers
})

_KEY_RING_SLOT: Dict[str, int] = {}


def key_ring_slots(spec: ProviderSpec) -> List[str]:
    """The provider's credential ring (env-var names, registration
    order). Single-key providers degrade to [env_var] — the exact
    pre-R469 behavior."""
    return (list(spec.key_env_vars) if spec.key_env_vars
            else [spec.env_var])


def _ring_slot_present(spec: ProviderSpec, idx: int) -> bool:
    names = key_ring_slots(spec)
    return (0 <= idx < len(names)
            and bool(os.environ.get(names[idx], "").strip()))


def active_key_slot(spec: ProviderSpec) -> Optional[int]:
    """The ring slot a call uses NOW: the sticky slot (skipping empty
    slots forward, wrapping once) — the first present slot when no
    rotation has happened. None when NO slot holds a credential."""
    names = key_ring_slots(spec)
    if not names:
        return None
    start = _KEY_RING_SLOT.get(spec.provider_id, 0) % len(names)
    for off in range(len(names)):
        idx = (start + off) % len(names)
        if _ring_slot_present(spec, idx):
            return idx
    return None


def active_key_value(spec: ProviderSpec) -> str:
    """The credential VALUE the transport uses (the active ring slot;
    '' when absent — callers keep the PROVIDER_UNAVAILABLE
    semantics). The single key-selection authority for chat calls,
    probes, and catalog fetches alike (Art. X)."""
    idx = active_key_slot(spec)
    if idx is None:
        return os.environ.get(spec.env_var, "").strip()
    return os.environ.get(key_ring_slots(spec)[idx], "").strip()


def rotate_key(spec: ProviderSpec) -> Optional[int]:
    """Advance the ring to the NEXT present slot (the operator's
    keep-going directive). Returns the new slot index, or None when
    the ring is exhausted — in which case the sticky slot RESETS to
    the first present slot (auto-recovery: the next call re-measures
    the head key; exhaustion is a per-call measurement, never a
    persisted fact).

    R470: the walk starts from the slot the failing call ACTUALLY
    served on (active_key_slot — sticky when set, first-present
    otherwise). The pre-R470 code started from the sticky DEFAULT 0,
    which re-returned the just-failed slot whenever the first present
    slot was not slot 0 (a middle-only ring double-spent its head key
    before advancing). Starting from the active slot is correct in
    every configuration."""
    names = key_ring_slots(spec)
    cur = active_key_slot(spec)
    if cur is None:
        return None
    for nxt in range(cur + 1, len(names)):
        if _ring_slot_present(spec, nxt):
            _KEY_RING_SLOT[spec.provider_id] = nxt
            return nxt
    # ring exhausted from the active slot — reset to first present
    _KEY_RING_SLOT[spec.provider_id] = 0
    for idx in range(len(names)):
        if _ring_slot_present(spec, idx):
            _KEY_RING_SLOT[spec.provider_id] = idx
            break
    return None


def _reset_key_ring(provider_id: str) -> None:
    """Test/ops hook: drop the sticky slot (never on the hot path)."""
    _KEY_RING_SLOT.pop(provider_id, None)


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
    # R519 §5/§7: the single routing-retirement authority treats a
    # caller-set explicit operator override as DELIBERATE (kept but
    # recorded), never as ordinary routing. Ordinary preferred_providers
    # lists are subject to route retirement; setting operator_override=True
    # marks a call an intentional operator act whose override must appear
    # on the selection ledger (never silent — Art. XV/XXVII).
    operator_override: bool = False


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
    # R6 owner round 2026-11-12 item 1 — the typed truncation signal:
    # the API's own finish-reason report for the completion that
    # produced this content, normalized in the transport ("length" =
    # cut at the token budget, "stop" = the model finished, "unknown"
    # = no finish-reason reported; any newer raw API value rides
    # verbatim — never invented, Art. XXV). Absent (None) on the
    # failure results that carry no completion.
    finish_reason: Optional[str] = None
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
                 # R483 (the dropped-ledger observability defect): the
                 # walk's skip/refuse states travel on the route — a
                 # SKIPPED_NOT_ADMITTED hop is answerable from committed
                 # bytes (status + capability_state), never only from a
                 # sandbox session's memory.
                 "status": h.get("status"),
                 "capability_state": h.get("capability_state"),
                 "fallback_provider": h.get("fallback_provider")}
                for h in (self.route or [])
            ] if self.route else [],
            "failure_type": self.failure_type,
            "finish_reason": self.finish_reason,
        }


# --------------------------------------------------------------------------
#: R483 — the sandbox-era classification of the re-pointable zai slot
#: (recorded policy constants: the values the spec ships with, restored
#: whenever the slot is NOT externally re-pointed).
_ZAI_SANDBOX_CLASSIFICATION = {
    "cost_basis": "ENVIRONMENT_GRANT",
    "locality": "LOCAL",
    "account_domain": "SANDBOX_ENVIRONMENT_GRANT",
}
#: R483 — the credited-remote classification applied when the slot IS
#: externally re-pointed. The R480 repoint (recorded in
#: R480/SPACE_REPOINT_RECORD.json) placed the credited atria ring key 1
#: into ZAI_API_KEY (fingerprint fp_9a89731ad93f == key 1's) and
#: ZAI_BASE_URL at the credited endpoint, so the slot's RUNTIME reality
#: is the operator-declared credited-provider class (the R467 atria
#: admission's declared class), never the sandbox grant. Art. XXV: a
#: recorded classification that no longer matches measured reality is
#: corrected to the measured state — this reconciliation is that
#: correction, applied at every selection surface (Art. XXVII: an
#: operator action recorded, never a coder's silent reclassification).
_ZAI_CREDITED_REMOTE_CLASSIFICATION = {
    "cost_basis": "FREE_TIER_API",
    "locality": "REMOTE",
    "account_domain": "OWNER_ATRIA_ACCOUNT",
}
_ZAI_RECONCILE_NOTE = (
    "R483 runtime reconciliation: the slot is externally re-pointed "
    "(ZAI_BASE_URL non-loopback, the R480 operator repoint to the "
    "credited provider with ring key 1 in ZAI_API_KEY) — the sandbox "
    "ENVIRONMENT_GRANT/LOCAL classification no longer matches measured "
    "reality and would have the ZERO_PAID_COST policy refuse the "
    "operator-pinned synthesis head, silently walking the decisive "
    "stage onto weaker rungs (measured 3x in production, "
    "R481/R482/R483 durable ledger). Classified credited-remote "
    "(FREE_TIER_API/REMOTE/OWNER_ATRIA_ACCOUNT) per the operator's "
    "R467 atria admission class and R480 repoint record.")


def _install_zai_spec(cost_basis: str, locality: str, account_domain: str,
                      policy_note: str) -> None:
    """Atomically replace the frozen zai spec with the reconciled one in
    BOTH surfaces that read it (the by-id map and the ordered list) —
    ProviderSpec is frozen (recorded policy, never mutated in place).
    """
    import dataclasses as _dc
    old = _SPEC_BY_ID["zai"]
    new = _dc.replace(old, cost_basis=cost_basis, locality=locality,
                      account_domain=account_domain,
                      policy_note=policy_note)
    _SPEC_BY_ID["zai"] = new
    for _i, _p in enumerate(PROVIDER_SPECS):
        if _p.provider_id == "zai":
            PROVIDER_SPECS[_i] = new
            break


def reconcile_runtime_classifications() -> Dict[str, Any]:
    """R483: align the re-pointable zai slot's recorded classification
    with its measured runtime state (the R480 repoint completion).

    Mechanism: when ZAI_BASE_URL resolves to a non-loopback endpoint,
    the slot rides an operator-supplied credential at an operator-
    supplied endpoint — the sandbox ENVIRONMENT_GRANT/LOCAL
    classification is factually false and the ZERO_PAID_COST policy
    (correctly reading the declared basis) refuses the very slot the
    deployment pins as the synthesis head; the R451-C1.1 chain
    extension then replaces the emptied chain with every available
    provider and the decisive stage routes to whichever free router
    scores best that minute (the measured production defect). This
    function flips the slot's declared basis/locality/account to the
    credited-remote class while the re-point is live, and restores the
    sandbox class when it is not. Idempotent, env-driven, no I/O;
    called at every selection surface (availability_matrix,
    select_provider, generate) so no path can read a stale class.

    The verifier is untouched; this is transport classification only
    (the {PROVIDER}_BASE_URL override class, Art. XXVII)."""
    spec = _SPEC_BY_ID.get("zai")
    if spec is None:
        return {"reconciled": False, "reason": "zai spec absent"}
    url = spec.url_for_call()
    host = ""
    try:
        from urllib.parse import urlparse as _up
        host = (_up(url).hostname or "").lower()
    except Exception:  # noqa: BLE001 — classification degrades honestly
        host = ""
    external = bool(url) and host not in ("127.0.0.1", "localhost", "::1", "")
    target = (_ZAI_CREDITED_REMOTE_CLASSIFICATION if external
              else _ZAI_SANDBOX_CLASSIFICATION)
    changed = []
    for field, value in target.items():
        if getattr(spec, field, None) != value:
            changed.append(f"{field}: {getattr(spec, field, None)} -> {value}")
    note = getattr(spec, "policy_note", "") or ""
    if external and "R483 runtime reconciliation" not in note:
        note = note + " | " + _ZAI_RECONCILE_NOTE
        changed.append("policy_note: +R483 reconciliation record")
    elif not external and "R483 runtime reconciliation" in note:
        note = note.replace(" | " + _ZAI_RECONCILE_NOTE, "")
        changed.append("policy_note: -R483 reconciliation record")
    if changed:
        _install_zai_spec(target["cost_basis"], target["locality"],
                          target["account_domain"], note)
    return {"reconciled": True, "external_repoint": external,
            "classification": dict(target),
            "changed": changed, "url_host": host or None}


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
    from . import call_context as _cctx2
    if _cctx2.fixture() is not None:
        return [{
            "provider_id": "DRY_RUN_FIXTURE",
            "env_var": "DRY_RUN_FIXTURE_MODE",
            "available": True,
            "key_ring_env_vars": [],
            "key_slots_present": [],
            "key_slot_active": None,
            "model": "fixture-text/1",
            "quality_tier": "FIXTURE",
            "cost_tier": "none",
            "latency_tier": "instant",
            "context_capacity_tokens": 0,
            "cost_basis": "no-charge-fixture",
            "locality": "in-process-fixture",
            "license": "n/a-fixture",
            "model_revision": "fixture/1",
            "account_domain": "none",
            "cost_policy": None,
            "cost_policy_eligible": True,
            "cost_policy_note": "fixture transport: no charge, no "
                                "credential (dry-run only)",
            "capability_state": "FIXTURE",
            "policy_note": "dry-run fixture provider (test transport; "
                           "never epistemic evidence)",
        }]
    from . import runtime_admission as _ra
    reconcile_runtime_classifications()  # R483: the re-point class authority
    policy = _cost_policy.active_policy()
    out = []
    for p in PROVIDER_SPECS:
        # R469: availability is ANY ring slot present (the marker env_var
        # stays the FIRST slot's name — the row reports the full ring)
        _ring = key_ring_slots(p)
        _present = [i for i, _n in enumerate(_ring)
                    if os.environ.get(_n, "").strip()]
        key = (os.environ.get(_ring[_present[0]], "")
               if _present else os.environ.get(p.env_var, ""))
        eligible, elig_note = _cost_policy.provider_eligibility(p, policy)
        cap = _ra.capability_state(p.provider_id, p.model_for_call(),
                                   policy=policy)
        out.append({
            "provider_id": p.provider_id,
            "env_var": p.env_var,
            "available": bool(_present),
            "key_ring_env_vars": _ring,
            "key_slots_present": _present,
            "key_slot_active": active_key_slot(p),
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


def strong_route_capability() -> Dict[str, Any]:
    """R455-LEAN-1 §2 — read-only STRONG-route admission mirror.

    Answers ONE question from PERSISTED state only (zero network, zero
    probes, zero side effects — a mirror of `generate()`'s admission
    inputs, not a new capability store): can the registry currently
    serve a STRONG-class synthesis request at STRONG capability, or is
    every reachable rung CHEAP-class (a guaranteed
    CHEAP_EMERGENCY_FALLBACK)?

    A rung is REACHABLE when its provider is available AND
    cost-policy-eligible AND the model is not recorded known-dead. A
    reachable rung's DECLARED task capabilities decide the class:
    declared capability is a property of the model, independent of
    probe freshness — so a STRONG rung with a stale/failed probe is
    still strong-capable (the walk probes it lazily; this gate must
    never deadlock a route behind its own probe TTL, Art. V).

    Returns {"state": OK | DEGRADED_ONLY | UNKNOWN, ...} — UNKNOWN
    fails OPEN (the conductor is never held hostage by the gate; the
    disclosed error travels on the record, Art. XV).
    """
    from . import model_routing as mr

    record: Dict[str, Any] = {
        "gate": "R455-LEAN-1/strong_route_capability/1.0.0",
        "state": "UNKNOWN",
        "requested_task": mr.TASK_STRONG,
        "strong_rungs": [],
        "degraded_rungs": [],
        "refused_rungs": [],
        "basis": ("declared task capabilities of every reachable "
                  "(available + cost-eligible + not known-dead) rung; "
                  "probe state is deliberately NOT consulted — declared "
                  "capability is probe-independent (Art. V: the gate "
                  "must never deadlock a route behind its own probe "
                  "TTL)"),
    }
    try:
        matrix = availability_matrix()
        avail_ids = [m["provider_id"] for m in matrix
                     if m["available"] and m["cost_policy_eligible"]]
        # the UNBOUNDED ladder view: the mirror asks whether ANY
        # reachable rung declares STRONG anywhere in the registry, so
        # the walk bound of generate() is deliberately not applied
        # (a bound here could manufacture a false DEGRADED_ONLY)
        ladder = mr.build_ladder(
            mr.TASK_STRONG, role=mr.ROLE_SYNTHESIS,
            available_providers=avail_ids, max_rungs=64)
        active_cost_policy = _cost_policy.active_policy()
        for r in ladder.get("rungs") or []:
            pid, mid = r.get("provider"), r.get("model")
            spec = _SPEC_BY_ID.get(pid)
            if spec is None:
                continue
            ok_elig, elig_note = _cost_policy.provider_eligibility(spec)
            if not ok_elig:
                record["refused_rungs"].append({
                    "provider": pid, "model": mid,
                    "reason": f"cost policy {active_cost_policy}: "
                              f"{elig_note}"})
                continue
            if mr.is_model_gone(pid, mid):
                record["refused_rungs"].append({
                    "provider": pid, "model": mid,
                    "reason": "known-dead model (the provider's own "
                              "recorded 410)"})
                continue
            caps = list(r.get("task_capabilities") or [])
            entry = {"provider": pid, "model": mid,
                     "task_capabilities": caps}
            if mr.TASK_STRONG in caps:
                record["strong_rungs"].append(entry)
            else:
                record["degraded_rungs"].append(entry)
        if record["strong_rungs"]:
            record["state"] = "OK"
        elif record["degraded_rungs"]:
            record["state"] = "DEGRADED_ONLY"
        else:
            # no reachable rung at all: NOT a capability verdict — the
            # transport class owns that case (the worker's preflight
            # probe records it honestly); this gate never fires here
            record["state"] = "OK"
            record["note"] = ("no reachable rung — not a capability "
                              "block; the transport preflight owns the "
                              "no-route case (Art. LXI)")
        return record
    except Exception as exc:  # noqa: BLE001 — fail OPEN, disclosed
        record["state"] = "UNKNOWN"
        record["error"] = f"{type(exc).__name__}: {exc}"
        record["basis"] = (record["basis"] +
                           " — the gate itself failed and fails OPEN "
                           "(the conductor is never held hostage; the "
                           "disclosed error travels on this record)")
        return record


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
    # OWNER ROUND 2026-11-13 item 2 — the per-call timeline: time-to-
    # first-response-byte (headers received; the honest TTFT proxy for
    # a non-streaming call, never estimated) and the total attempt wall,
    # recorded THREAD-LOCALLY and consumed by generate() into the same
    # attempt record (same-thread read immediately after the call, like
    # the finish-reason signal). A hang is measured, not guessed:
    # ttfb consuming >= 90% of the attempt's socket timeout means the
    # gateway accepted the request and produced nothing — hang time is
    # EXCLUDED from work-time sums (the owner's rule: no gateway hangs
    # counted as work), while the attempt stays typed infrastructure.
    _t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        _ttfb = time.perf_counter() - _t0
        data = json.loads(resp.read())
    _post_timing.last = {
        "ttfb_s": round(_ttfb, 3),
        "total_s": round(time.perf_counter() - _t0, 3),
        "timeout": timeout,
        "gateway_hang": bool(_ttfb >= 0.9 * timeout)}
    return data


_post_timing = threading.local()


# --------------------------------------------------------------------------
# R6 owner round 2026-11-12 item 1 — the typed truncation signal.
# The flavor transports keep their one-value `str` return contract
# (four external call sites — eval's baseline/judge direct calls and
# the runtime probes — pin it); the API's finish-reason signal is
# therefore recorded THREAD-LOCALLY at the moment of return and
# consumed by generate() on the same thread immediately after the
# flavor call. Concurrency is safe: the read follows the call with
# no gap, on the same thread (the operator thread-pool runs each
# generate() end-to-end in its own thread).
#
# Normalized vocabulary: "length" (the API says the output was cut at
# the token budget — openai finish_reason=length, anthropic
# stop_reason=max_tokens), "stop" (the API says the model finished,
# including a filter/tool stop — not a truncation), "unknown" (no
# finish-reason reported). Any newer raw API value is recorded
# VERBATIM (never mapped by guess — Art. XXV: unknown stays
# unknown), and a consumer claims truncation ONLY on "length".
_finish_state = threading.local()

_OPENAI_FINISH_MAP = {"length": "length", "stop": "stop",
                      "content_filter": "stop", "tool_calls": "stop"}
_ANTHROPIC_FINISH_MAP = {"max_tokens": "length", "end_turn": "stop",
                         "stop_sequence": "stop", "tool_use": "stop"}


def _finish_from_openai(raw: Any) -> str:
    if raw is None:
        return "unknown"
    v = str(raw)
    return _OPENAI_FINISH_MAP.get(v, v)


def _finish_from_anthropic(raw: Any) -> str:
    if raw is None:
        return "unknown"
    v = str(raw)
    return _ANTHROPIC_FINISH_MAP.get(v, v)


def _record_finish_reason(value: str) -> None:
    _finish_state.finish_reason = value


def _take_finish_reason() -> Optional[str]:
    return getattr(_finish_state, "finish_reason", None)


def _call_openai_flavor(spec: ProviderSpec, messages: List[dict],
                        timeout: int, max_tokens: int,
                        model_override: Optional[str] = None) -> str:
    # R469: the ACTIVE ring key (single-key providers: env_var, exactly
    # the pre-R469 read — one key-selection authority, Art. X)
    key = active_key_value(spec)
    model = model_override or spec.model_for_call()
    # R6 A1/A2 (owner round 2026-11-12): breaker check -> cache read ->
    # governed attempts -> cache write. Order matters: an OPEN breaker
    # refuses before anything else (typed BreakerOpen, zero requests); a
    # cache hit serves the recorded content with ZERO provider spend (the
    # hit is logged, the finish-reason signal is restored so downstream
    # truncation-retry logic behaves identically); live attempts are
    # counted by the per-problem governor (<=12 healthy + <=6 retries).
    from . import llm_economy as _econ
    _econ.breaker_check(spec.provider_id)
    _ck = _econ.llm_cache_key(spec.provider_id, model, messages,
                              max_tokens, spec.extra_body)
    _cached = _econ.cache_get(_ck)
    if _cached is not None:
        _record_finish_reason(_cached.get("finish_reason") or "stop")
        return _cached["content"]
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
    headers = {"Authorization": f"Bearer {key}"}
    if spec.extra_headers:
        headers.update(spec.extra_headers)
    # R1 infra fix (Art. LXI): transient overload / rate-limit responses
    # (429, 502, 503, 504) are infrastructure, not verdicts. ONE
    # immediate retry before surfacing the typed failure (owner round
    # 2026-11-13 item 2: no fixed backoff sleep); never retries
    # auth/quota (401/403/402).
    _TRANSIENT = (429, 502, 503, 504)
    last_exc = None
    # OWNER ROUND 2026-11-13 item 2: the same-rung retry ladder is ONE
    # IMMEDIATE retry (no fixed sleep) — the measured wall spent 5-20 s
    # per failed attempt asleep while the ring recovered; the
    # rotate-to-next-rung cascade is the real resilience, and the A2
    # breaker still aborts a genuine storm (Art. LXI: infrastructure
    # absence is typed, never slept through)
    for attempt in range(2):
        # A2 governor: ONE provider request = ONE count; re-attempts of the
        # same logical call are RETRIES, capped per problem (default 6).
        _econ.governor_attempt(_ck)
        try:
            data = _post_json(
                spec.url_for_call(), payload, headers, timeout)
            break
        except urllib.error.HTTPError as he:
            if he.code in _TRANSIENT:
                # A2 breaker: count the transient failure; if the breaker
                # JUST opened, abort the ladder IMMEDIATELY — the measured
                # retry storm (31-40 provider attempts per problem) stops
                # here instead of hammering through the retry ladder.
                if _econ.breaker_failure(spec.provider_id):
                    raise _econ.BreakerOpen(
                        f"CIRCUIT_BREAKER_OPEN: provider "
                        f"'{spec.provider_id}' hit the transient-failure "
                        f"threshold; the same-rung retry ladder aborts "
                        f"(Art. LXI)", request_made=True) from he
            if he.code in _TRANSIENT and attempt < 1:
                last_exc = he
                continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError) as ne:
            if _econ.breaker_failure(spec.provider_id):
                raise _econ.BreakerOpen(
                    f"CIRCUIT_BREAKER_OPEN: provider "
                    f"'{spec.provider_id}' hit the transient-failure "
                    f"threshold; the same-rung retry ladder aborts "
                    f"(Art. LXI)", request_made=True) from ne
            if attempt < 1:
                last_exc = ne
                continue
            raise
    else:
        if last_exc is not None:
            raise last_exc
    _econ.breaker_success(spec.provider_id)
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
    # the typed truncation signal for a NON-empty completion (the
    # empty-content case above raises before it): recorded thread-
    # locally, consumed by generate() into the LLMCallResult
    _finish = _finish_from_openai(choice.get("finish_reason"))
    _record_finish_reason(_finish)
    # A1 record: the successful call is cached for replay (rw mode only;
    # an empty-content or API-error result never reaches here, so the
    # composer's larger-budget truncation retry keeps its own distinct
    # cache key via max_tokens). OWNER DIRECTIVE 2026-11-12 (defect:
    # the replay served a frozen failure): ONLY finish_reason=stop is
    # a result — a "length" cut is an infrastructure truncation, never
    # cached (the retry path's larger budget re-runs it live).
    if _finish == "stop":
        _econ.cache_put(_ck, {"content": content, "finish_reason": _finish,
                              "model": model, "provider_id": spec.provider_id,
                              "max_tokens": max_tokens})
    return content


class EmptyContentWithFinish(RuntimeError):
    """Empty completion with the API's finish_reason carried for retry "
    policy (reasoning models can spend the entire cap on hidden reasoning
    tokens; a larger cap on the SAME provider/model is not a downgrade)."""

    def __init__(self, message: str, finish_reason: str = "unknown"):
        super().__init__(message)
        self.finish_reason = finish_reason


def _retry_sleep_s(retries_used: int) -> float:
    """R10 P0-2 (owner): the same-model retry pacing is a TYPED knob —
    ENGINE_LLM_RETRY_SLEEP_S overrides the historical exponential
    backoff (2 s after the first retry, 4 s after the second). The
    unattended arms set it to 0 (NO fixed sleeps on the active path:
    the schedule is the pacing, and a live process parked in sleep()
    burns wall time without work). Default keeps the measured history
    (2*retries) — behavior-identical when the knob is absent."""
    raw = os.environ.get("ENGINE_LLM_RETRY_SLEEP_S", "").strip()
    if raw:
        try:
            v = float(raw)
            if v >= 0:
                return v
        except (TypeError, ValueError):
            pass
    return 2.0 * retries_used


def _call_anthropic_flavor(spec: ProviderSpec, messages: List[dict],
                           timeout: int, max_tokens: int,
                           model_override: Optional[str] = None) -> str:
    # R469: the ACTIVE ring key (see _call_openai_flavor)
    key = active_key_value(spec)
    model = model_override or spec.model_for_call()
    system = ""
    msgs = []
    for m in messages:
        if m["role"] == "system":
            system = m["content"]
        else:
            msgs.append(m)
    # A1/A2 hooks on the anthropic flavor (single-shot): breaker -> cache
    # -> governed attempt -> cache write (same contract as the openai
    # flavor above)
    from . import llm_economy as _econ
    _econ.breaker_check(spec.provider_id)
    # the system prompt was split out of `msgs` above: it MUST ride the
    # cache key or two different prompts would share one recorded answer
    _ck = _econ.llm_cache_key(spec.provider_id, model, msgs, max_tokens,
                              None, system=system)
    _cached = _econ.cache_get(_ck)
    if _cached is not None:
        _record_finish_reason(_cached.get("finish_reason") or "stop")
        return _cached["content"]
    _econ.governor_attempt(_ck)
    try:
        data = _post_json(
            spec.url_for_call(),
            {"model": model, "max_tokens": max_tokens,
             "messages": msgs, **({"system": system} if system else {})},
            {"x-api-key": key, "anthropic-version": "2023-06-01"}, timeout)
    except Exception as exc:
        # transient 429/timeout/5xx/network failures feed the breaker;
        # permanent auth/model failures are typed provider failures and
        # must never open a congestion breaker (a bad key is not a storm)
        if _econ.is_transient_provider_failure(exc):
            if _econ.breaker_failure(spec.provider_id):
                raise _econ.BreakerOpen(
                    f"CIRCUIT_BREAKER_OPEN: provider "
                    f"'{spec.provider_id}' hit the transient-failure "
                    f"threshold (Art. LXI)", request_made=True) from exc
        raise
    _econ.breaker_success(spec.provider_id)
    content = "".join(b.get("text", "") for b in data.get("content", []))
    if not content:
        raise RuntimeError(f"{spec.provider_id} returned empty content")
    # the typed truncation signal (stop_reason=max_tokens -> "length"),
    # recorded thread-locally, consumed by generate() into the
    # LLMCallResult
    _record_finish_reason(_finish_from_anthropic(data.get("stop_reason")))
    # OWNER DIRECTIVE 2026-11-12: only a clean stop is a result — a
    # max_tokens cut is infrastructure truncation, never cached
    if _finish_from_anthropic(data.get("stop_reason")) == "stop":
        _econ.cache_put(_ck, {"content": content, "finish_reason":
                              _finish_from_anthropic(
                                  data.get("stop_reason")),
                              "model": model, "provider_id": spec.provider_id,
                              "max_tokens": max_tokens})
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
             run_id: Optional[str] = None,
             hard_pin_provider: Optional[str] = None) -> LLMCallResult:
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
    engine never refuses to run on a heuristic (Art. V).

    R491 hard_pin_provider: the measurement ring pin. When set, the
    walk is restricted to rungs of EXACTLY this provider — the R415
    ladder's LAST_RESORT band and the rung-count floor cannot extend
    it, a failing pinned call is CALL_FAILED (never a silent cascade
    to a different ring). Purpose: the sealed-corpus calibration
    measurement must measure the instrument on the ring it declares
    (the R488 lesson: attacker calibration is (rules x ring); the
    cascade under load served the free-tier ring and the same rules
    measured FPR 1.0 live vs 0.25 on the strong ring's outputs).
    Production paths never set it (Art. V stands for them)."""
    from . import call_context as _cctx
    _fixture = _cctx.fixture()
    if _fixture is not None:
        _purpose = ""
        _route = ""
        try:
            _purpose = str((policy.purpose if policy is not None
                            else "") or "")
            _pref = (policy.preferred_providers
                     if policy is not None else None) or []
            _route = str(_pref[0]) if _pref else ""
        except Exception:
            _purpose = ""
            _route = ""
        return _fixture.serve(prompt=prompt, system=system,
                              purpose=_purpose, run_id=run_id,
                              timeout=timeout, route=_route)
    from .provider_health import (ROLE_SYNTHESIS, HEALTH, classify_failure,
                                  order_for_role, role_for_purpose,
                                  apply_route_retirement)
    from . import model_routing as mr
    from . import llm_economy as _econ

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

    # R526 Q-A (behavior-neutral per-attempt span instrumentation):
    # read-only perf_counter/utc timestamps around the phases that
    # actually exist in generate(). No routing, retry, budget, gate,
    # probe, admission, or transport logic is touched — the record
    # rides every durable ledger line of this call so the harvester
    # can split llm_chat_total_s from provider-call wall without
    # inventing sub-phases. Anything unmeasured stays UNATTRIBUTED
    # downstream (never force-fit). Audit rule per call:
    #   generate_total_s = measured_subspans + unattributed_remainder
    _gen_t0 = time.perf_counter()
    _gen_spans = {
        "instrument": "gen_spans/1.0",
        "purpose": None,
        "generate_total_s": None,
        "selection_ordering_s": None,
        # R530 §3: selection subspan decomposition (A–I) + the
        # selection-path diagnostic counts. Behavior-neutral
        # telemetry: perf_counter deltas around operations that
        # already exist; no routing, scoring, or I/O change.
        "selection_subspans": None,
        "selection_diag": None,
        "ladder_before_filtering": [],
        "retirement_removed": [],
        "cost_refusals": [],
        "chain_source": None,
        "rungs": [],
    }
    # R526 Q-A: one stable identity for every durable ledger line of
    # THIS generate() call (grouping without time-window inference) +
    # the wall-clock start for the call-total audit rule. Precedent:
    # dry_run already reuses request_id per run; nothing assumes
    # per-line uniqueness (verified).
    import uuid as _uuid
    _gen_call_id = f"gen_{_uuid.uuid4().hex[:12]}"
    _gen_start_epoch = time.time()
    _t_sel0 = time.perf_counter()
    # R530 §3: selection subspan accumulators (A–H) + the diagnostic
    # take-and-zero. Behavior-neutral: perf_counter reads + counter
    # take only. The take() zeroes model_routing's diag counters so
    # the close-time delta is exactly this call's selection work;
    # abandoned early-return selections discard via take() at their
    # return sites (same function, below).
    mr.selection_diag_take()
    # R531 §6: open the invocation-local score memo table (fresh;
    # closed at span close + early-return discard sites).
    mr.selection_memo_begin()
    _sA_matrix_s = 0.0
    _sB_chain_s = 0.0
    _sC_retirement_s = 0.0
    _sD_costpolicy_s = 0.0
    _sE_ladder_s = 0.0
    _sH_capevidence_s = 0.0

    def _gen_span_snapshot(final: bool = False) -> Dict[str, Any]:
        """R526 Q-A: self-contained span snapshot for one durable ledger
        line. Rung/attempt dicts are serialized by the ledger writer at
        call time, so later mutations cannot rewrite history. On
        terminal lines (a return follows immediately) the snapshot
        carries generate_total_s; elsewhere the total stays None and
        the harvester treats it as UNATTRIBUTED for the call total.
        A4.10: the snapshot itself is a pure read of local state; it
        never raises on its own (every value it reads is a plain
        float/None/list)."""
        try:
            snap = {"instrument": _gen_spans["instrument"],
                    "purpose": _gen_spans["purpose"],
                    "generate_call_id": _gen_call_id,
                    "generate_start_epoch": _gen_start_epoch,
                    "generate_total_s": (
                        round(time.perf_counter() - _gen_t0, 6)
                        if final else None),
                    "generate_elapsed_s": round(
                        time.perf_counter() - _gen_t0, 6),
                    "selection_ordering_s": _gen_spans[
                        "selection_ordering_s"],
                    # R530 §3: subspan decomposition + diag counts ride
                    # every ledger line (None until the selection span
                    # closes; the terminal line carries the final
                    # values — same pattern as selection_ordering_s).
                    "selection_subspans": _gen_spans.get(
                        "selection_subspans"),
                    "selection_diag": _gen_spans.get("selection_diag"),
                    "ladder_before_filtering": [
                        list(x) for x in
                        _gen_spans["ladder_before_filtering"]],
                    "retirement_removed": list(
                        _gen_spans["retirement_removed"]),
                    "cost_refusals": list(_gen_spans["cost_refusals"]),
                    "chain_source": _gen_spans["chain_source"],
                    "rungs": [{k: (list(v) if k == "attempts" else v)
                               for k, v in _hop.items() if not k.startswith(
                                   "_")}
                              for _hop in _gen_spans["rungs"]],
                    "post_success_sleep_s": None,
                    "post_success_sleep_note": (
                        "no fixed post-success sleep in generate(); the "
                        "0.5 s sleep lives in a2/synthesize.llm_chat and "
                        "rides inside llm_chat_total_s"),
                    "response_normalization_s": None,
                    "response_normalization_note": (
                        "no response-normalization step exists in "
                        "generate(); provider content flows straight to "
                        "the result record")}
            return snap
        except Exception:  # noqa: BLE001 — telemetry never raises
            return {"instrument": _gen_spans["instrument"],
                    "generate_call_id": _gen_call_id,
                    "generate_total_s": None,
                    "snapshot_error": "SPAN_SNAPSHOT_FAILED"}

    # R530 §3 subspan A: availability snapshot phase
    # (reconcile_runtime_classifications + availability_matrix +
    # cost-policy refusal list — pre-ladder route assembly).
    _tA0 = time.perf_counter()
    reconcile_runtime_classifications()  # R483: the re-point class authority
    matrix = availability_matrix()
    avail_ids = [m["provider_id"] for m in matrix
                 if m["available"] and m["cost_policy_eligible"]]
    policy_refusals = [
        {"provider": m["provider_id"], "reason": m["cost_policy_note"]}
        for m in matrix if m["available"] and not m["cost_policy_eligible"]]
    _sA_matrix_s += time.perf_counter() - _tA0
    # -- the provider chain (policy order, then role ordering) -------------
    # R519 §5/§7: THE single routing-retirement authority. Every chain
    # source — ordinary preferred_providers, the role order, the cost
    # extension, and the rung ladder — is filtered through
    # apply_route_retirement(), so no path can answer "retired" while
    # another answers "allowed" (R519 §7: the authority must never give
    # contradictory answers). An EXPLICIT operator override — the R491
    # hard_pin_provider, or a call site that set policy.operator_override
    # because it is honoring an ENGINE_*_PROVIDER env pin — remains
    # possible under the selected R519 §5 semantics but is NEVER silent:
    # the kept override is recorded in retirement_events and travels on
    # the selection ledger. Ordinary (call-site-listed) preferred lists
    # are subject to route retirement.
    _purpose_tag0 = (policy.purpose if policy else "") or ""
    _explicit_override = bool(
        hard_pin_provider
        or getattr(policy, "operator_override", False))
    # R6 owner round 2026-11-12 (measured 2026-11-12, the fu-001
    # successor smoke): with an ENGINE_*_PROVIDER pin naming provider A
    # while A is PROVIDER_UNAVAILABLE on the host, the cost-policy
    # extension AND the rung filter kept RETIRED providers the operator
    # never named — agnes (429 "1 request per 3 minutes") served the
    # synthesis live (14:55:26), broke the per-problem healthy cap, and
    # the evaluator was then refused (EVALUATOR_CALL_FAILED -> composer
    # NO_ADMISSIBLE_CANDIDATES -> answer=None -> "pipeline answer
    # missing"). The R519 §5 explicit-override KEEP is now SCOPED to
    # the operator-NAMED providers themselves (the policy preferred
    # list ∪ the hard pin): every other candidate — including the
    # whole cost-policy extension and the ladder's LAST_RESORT band —
    # gets ORDINARY retirement semantics. A named retired pin still
    # rides (recorded, never silent); a never-named retired member is
    # never re-admitted.
    _named_keep = set(getattr(policy, "preferred_providers", None) or [])
    if hard_pin_provider:
        _named_keep.add(hard_pin_provider)
    retirement_events: List[Dict[str, Any]] = []
    # R530 §3 subspan B: chain construction (policy preferred list
    # or role order + cooldown demotion). The nested
    # apply_route_retirement call is subspan C — B accumulates the
    # block wall EXCLUSIVE of C (record C first, subtract its delta).
    _tB0 = time.perf_counter()
    _cB0 = _sC_retirement_s
    if policy and policy.preferred_providers:
        chain = [pid for pid in policy.preferred_providers
                 if pid in avail_ids]
        _chain_role = role or role_for_purpose(_purpose_tag0) or ROLE_SYNTHESIS
        _tC0 = time.perf_counter()
        chain, _rr = apply_route_retirement(
            chain, role=_chain_role, purpose=_purpose_tag0,
            explicit_override=_explicit_override)
        _sC_retirement_s += time.perf_counter() - _tC0
        retirement_events.extend(_rr)
        chain_source = "policy.preferred_providers" + (
            " (EXPLICIT_OPERATOR_OVERRIDE)" if _explicit_override else "")
    else:
        eff_role = role or (role_for_purpose(
            policy.purpose if policy else "") if policy else None) \
            or ROLE_SYNTHESIS
        chain = order_for_role(matrix, eff_role,
                               avoid_provider=avoid_provider,
                               purpose=_purpose_tag0,
                               out_events=retirement_events)
        chain_source = f"role_order:{eff_role}"
    # cooldown demotion applies to BOTH chain sources: a rate-limited
    # provider slides to the end (never removed — a lone cooled provider
    # is still tried; Art. V)
    if len(chain) > 1:
        cooled = [p for p in chain if HEALTH.in_cooldown(p)]
        if cooled:
            chain = [p for p in chain if p not in cooled] + cooled
    _sB_chain_s += (time.perf_counter() - _tB0) - (
        _sC_retirement_s - _cB0)
    # R451 §1: the cost policy REFUSES ineligible rungs — including the
    # ones the ladder would add beyond the policy chain (LAST_RESORT
    # rungs, preferred pins pointing at paid providers). A paid route
    # is never silently fallen back to; the refusals travel in the
    # ledger (fail-closed, Art. IV/VII).
    # R530 §3 subspan D: cost-policy filtering (filter_chain on the
    # policy chain).
    _tD0 = time.perf_counter()
    chain, _chain_refusals = _cost_policy.filter_chain(
        chain, _SPEC_BY_ID)
    _sD_costpolicy_s += time.perf_counter() - _tD0
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
        # R530 §3: the extension block is subspan D exclusive of the
        # nested subspan-C retirement call (same exclusive pattern
        # as B). R6 owner round 2026-11-12: the extension's retirement
        # filter uses the SCOPED keep (named providers only) — never
        # the blanket explicit_override keep (see _named_keep above).
        _tD1 = time.perf_counter()
        _cD1 = _sC_retirement_s
        _chain_role = role or role_for_purpose(
            _purpose_tag0) or ROLE_SYNTHESIS
        _tC0 = time.perf_counter()
        if _explicit_override and _named_keep:
            _named_ext = [p for p in cost_policy_chain_extension
                          if p in _named_keep]
            _rest_ext = [p for p in cost_policy_chain_extension
                         if p not in _named_keep]
            _rest_ext, _rr = apply_route_retirement(
                _rest_ext, role=_chain_role, purpose=_purpose_tag0,
                explicit_override=False)
            cost_policy_chain_extension = _named_ext + _rest_ext
        else:
            cost_policy_chain_extension, _rr = apply_route_retirement(
                cost_policy_chain_extension, role=_chain_role,
                purpose=_purpose_tag0, explicit_override=False)
        _sC_retirement_s += time.perf_counter() - _tC0
        retirement_events.extend(_rr)
        chain = list(cost_policy_chain_extension)
        _sD_costpolicy_s += (time.perf_counter() - _tD1) - (
            _sC_retirement_s - _cD1)
    if not chain:
        # preferred_providers exhausted or policy-refused with no
        # eligible provider: keep the historical honest semantics (no
        # silent widening beyond the operator's list — Art. IV) and
        # name the COST POLICY refusal when that is the cause. R519: if
        # the chain emptied because route retirement removed every
        # candidate, that is the typed reason — DEFAULT_ROUTE_BLOCKED,
        # never a silent provider-unavailable (routing provenance is
        # complete, R519 §16 rule 6).
        _, ledger = select_provider(policy)
        any_avail = any(m["available"] for m in matrix)
        _retired_all = any(e["retirement_state"] == "RETIRED_ROUTE_BLOCKED"
                           for e in retirement_events)
        _status = (ST_POLICY_BLOCKED if (_retired_all or any_avail)
                   else ST_PROVIDER_UNAVAILABLE)
        _err = (
            f"route retirement blocked every eligible provider for "
            f"this role/purpose (R519 single retirement authority): "
              f"{[e['provider'] for e in retirement_events if e['retirement_state'] == 'RETIRED_ROUTE_BLOCKED']} — "
              f"DEFAULT_ROUTE_BLOCKED; an explicit operator override "
              f"(hard_pin_provider / operator_override) remains the only "
              f"sanctioned path to a retired provider"
              if _retired_all else
              (f"the active cost policy "
               f"{_cost_policy.active_policy()} refused every "
               f"available provider — paid routes are never silently "
               f"used (R451 §1)" if any_avail else
               "no provider credential available (see selection_ledger)"))
        # R530 §3: abandoned selection — discard this call's diag
        # counts so they cannot pollute the next call's delta (the
        # selection span never closes on this path). R531 §6: also
        # close the memo table.
        mr.selection_diag_take()
        mr.selection_memo_end()
        return LLMCallResult(
            status=_status, error=_err,
            prompt_hash=_sha(prompt),
            selection_ledger={**ledger,
                              "retirement_events": list(retirement_events),
                              "cost_policy_refusals": policy_refusals
                              or ledger.get("cost_policy_refusals")},
            call_provenance=call_prov)

    # -- R415: the (provider, model) rung list from the routing registry --
    eff_role = role or (role_for_purpose(
        policy.purpose if policy else "") if policy else None) \
        or ROLE_SYNTHESIS
    task = mr.task_class_for_role(eff_role)
    purpose_tag = (policy.purpose if policy else "") or eff_role
    # R530 §3 subspan E: build_ladder (per-provider eligible lists,
    # score-ranked sort, round-robin + LAST_RESORT emission). E is
    # INCLUSIVE of the catalog (F) and scoring (G) detail reported
    # from model_routing's diag counters — F/G are detail-of-E, not
    # additive (documented, never double-counted).
    _tE0 = time.perf_counter()
    ladder = mr.build_ladder(
        task, role=eff_role, avoid_provider=avoid_provider,
        preferred_providers=list(chain),
        available_providers=avail_ids,
        purpose=purpose_tag)
    _sE_ladder_s += time.perf_counter() - _tE0
    rungs = [(r["provider"], r["model"], r) for r in ladder["rungs"]]
    # R526 Q-A: the candidate ladder BEFORE cost/retirement filtering
    # (durable per attempt — same list rides every ledger line of the
    # call; small by construction).
    _gen_spans["ladder_before_filtering"] = [
        [p, m] for p, m, _r in rungs]
    # R451: policy-filter the rungs (the ladder's LAST_RESORT band may
    # add providers the policy chain never asked for — paid models are
    # refused here too, with each refusal recorded on the ladder).
    # R530 §3: the rung eligibility loop is subspan D (cost-policy).
    _rung_refusals = []
    _rungs_kept = []
    _tD2 = time.perf_counter()
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
    _sD_costpolicy_s += time.perf_counter() - _tD2
    rungs = _rungs_kept
    ladder.setdefault("cost_policy", _cost_policy.active_policy())
    ladder.setdefault("cost_policy_rung_refusals", _rung_refusals)
    # R519 §7 (R6 owner round 2026-11-12): the rung list passes through
    # the same SCOPED keep — the ladder's LAST_RESORT band can add a
    # retired provider the chain never asked for; ordinary routing must
    # not reach it. Only the operator-NAMED providers ride the keep
    # (recorded); everyone else gets ordinary retirement.
    _retire_role = role or role_for_purpose(purpose_tag) or ROLE_SYNTHESIS
    _rung_provider_order: List[str] = []
    for provider_id, _model_id, _r in rungs:
        if provider_id not in _rung_provider_order:
            _rung_provider_order.append(provider_id)
    # R530 §3 subspan C (site 3): rung-list retirement filter.
    _tC0 = time.perf_counter()
    if _explicit_override and _named_keep:
        _named_r = [p for p in _rung_provider_order if p in _named_keep]
        _rest_r = [p for p in _rung_provider_order
                   if p not in _named_keep]
        _rest_r, _rr = apply_route_retirement(
            _rest_r, role=_retire_role, purpose=purpose_tag,
            explicit_override=False)
        _allowed_providers = _named_r + _rest_r
    else:
        _allowed_providers, _rr = apply_route_retirement(
            _rung_provider_order, role=_retire_role, purpose=purpose_tag,
            explicit_override=bool(hard_pin_provider) or _explicit_override)
    _sC_retirement_s += time.perf_counter() - _tC0
    retirement_events.extend(_rr)
    _allowed_set = set(_allowed_providers)
    rungs = [x for x in rungs if x[0] in _allowed_set]
    ladder["retirement_events"] = list(retirement_events)
    # R526 Q-A: retirement removals + cost refusals as durable
    # per-call facts (the ladder's full retirement_events already
    # carry the per-removal records; these lists are the compact
    # per-attempt view).
    _gen_spans["retirement_removed"] = sorted({
        e.get("provider") for e in retirement_events
        if e.get("retirement_state") == "RETIRED_ROUTE_BLOCKED"
        and e.get("provider")})
    _gen_spans["cost_refusals"] = sorted({
        r.get("provider") for r in (policy_refusals + _rung_refusals)
        if r.get("provider")})
    _gen_spans["chain_source"] = chain_source
    # the ladder may add last-resort providers beyond the policy chain
    # (the directive's LAST-RESORT rung); bound the walk:
    # 1 + max_provider_fallbacks + 2 model hops
    rungs = rungs[:max(3, 1 + max(0, max_provider_fallbacks) + 2)]
    # R491: the measurement ring pin — applied AFTER the floor so the
    # LAST_RESORT band and the max(3, ...) minimum can never widen a
    # pinned walk. A pin with no admissible rung fails closed here.
    if hard_pin_provider:
        _pinned_rungs = [r for r in rungs
                         if r[0] == hard_pin_provider]
        if not _pinned_rungs:
            # R530 §3: abandoned selection — discard diag counts.
            # R531 §6: also close the memo table.
            mr.selection_diag_take()
            mr.selection_memo_end()
            return LLMCallResult(
                status=ST_PROVIDER_UNAVAILABLE,
                error=(f"hard-pinned provider '{hard_pin_provider}' "
                       f"has no admissible routing rung in this "
                       f"deployment (credential, cost policy, or "
                       f"capability state) — fail-closed, never a "
                       f"silent ring change"),
                prompt_hash=_sha(prompt),
                selection_ledger={
                    "chain": list(chain), "ladder": ladder,
                    "hard_pin": {"requested": hard_pin_provider,
                                 "status": "NO_ADMISSIBLE_RUNG"}},
                call_provenance=call_prov)
        rungs = _pinned_rungs
    if not rungs:
        # R530 §3: abandoned selection — discard diag counts.
        # R531 §6: also close the memo table.
        mr.selection_diag_take()
        mr.selection_memo_end()
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
    # R530 §3 subspan H: capability-evidence snapshot.
    _tH0 = time.perf_counter()
    ladder["capability_evidence"] = _ra.ladder_capability_evidence(
        [{"provider": p, "model": m} for p, m, _meta in rungs])
    _sH_capevidence_s += time.perf_counter() - _tH0
    # R526 Q-A (A3): the selection/ordering span closes JUST BEFORE
    # message construction begins. It measures the chain assembly,
    # cost filter, ladder build, rung filter, retirement, and
    # capability-evidence snapshot — NOT message construction (the
    # `messages` list is built below, outside the span). No
    # speculative extra timer is added; the timer end is placed
    # exactly at the last pre-walk setup step.
    # R530 §3: the subspan decomposition closes here. A–E + H are
    # mutually exclusive walls; F (catalog) + G (scoring) are
    # detail-of-E from model_routing's diag counters (NOT additive —
    # they already ride inside E's wall); I is the remainder
    # (total − A − B − C − D − E − H). A negative I beyond the
    # documented −0.05 s clock tolerance is an instrumentation
    # violation, recorded never hidden (same contract as the Q-A
    # remainder).
    _sel_total = time.perf_counter() - _t_sel0
    _gen_spans["selection_ordering_s"] = round(_sel_total, 6)
    _diag1 = mr.selection_diag_take()
    _sA = round(_sA_matrix_s, 6)
    _sB = round(_sB_chain_s, 6)
    _sC = round(_sC_retirement_s, 6)
    _sD = round(_sD_costpolicy_s, 6)
    _sE = round(_sE_ladder_s, 6)
    _sH = round(_sH_capevidence_s, 6)
    _sF = round(_diag1.get("eligible_models_s", 0.0), 6)
    # NOTE (R530 accounting correction): F is the INCLUSIVE
    # eligible_models wall (it already contains its inner
    # discover_catalog work — catalog fetches happen inside
    # eligible_models/all_models, never beside them). Adding
    # discover_catalog_s again would double-count the nested wall
    # (measured live: F_double = 2.49 s > E = 1.29 s on a hermetic
    # call — the nested catalog wall counted twice). The raw
    # discover_catalog_s + cache-hit counts remain in
    # selection_diag as detail, never added to F.
    _sG = round(_diag1.get("availability_score_s", 0.0), 6)
    _sI = round(_sel_total - (_sA + _sB + _sC + _sD + _sE + _sH), 6)
    _gen_spans["selection_subspans"] = {
        "instrument": "gen_spans/1.0",
        "A_availability_matrix_s": _sA,
        "B_chain_construction_s": _sB,
        "C_route_retirement_s": _sC,
        "D_cost_policy_s": _sD,
        "E_build_ladder_s": _sE,
        "F_catalog_detail_s": _sF,
        "G_scoring_detail_s": _sG,
        "H_capability_evidence_s": _sH,
        "I_selection_remainder_s": _sI,
        "accounting": ("A+B+C+D+E+H+I = selection_ordering_s; "
                       "F+G are detail-of-E (inclusive), not additive; "
                       "F = eligible_models wall inclusive of catalog "
                       "fetches; G = availability_score wall inclusive "
                       "of ledger scans"),
    }
    _gen_spans["selection_diag"] = {
        "n_providers_inspected": _diag1.get(
            "ladder_providers_inspected", 0),
        "n_models_inspected": _diag1.get("ladder_models_inspected", 0),
        "n_ladder_rungs_emitted": _diag1.get("ladder_rungs_emitted", 0),
        "n_availability_score_calls": _diag1.get(
            "availability_score_calls", 0),
        "availability_score_s": round(
            _diag1.get("availability_score_s", 0.0), 6),
        # R531 §6: memo hits (reuse without recomputation).
        # recomputes + hits = the unmemoized call count.
        "n_selection_memo_hits": _diag1.get(
            "selection_memo_hits", 0),
        "n_availability_report_scans": _diag1.get(
            "availability_report_calls", 0),
        "availability_report_s": round(
            _diag1.get("availability_report_s", 0.0), 6),
        "n_eligible_models_calls": _diag1.get(
            "eligible_models_calls", 0),
        "n_eligible_models_returned": _diag1.get(
            "eligible_models_returned", 0),
        "n_discover_catalog_calls": _diag1.get(
            "discover_catalog_calls", 0),
        "n_discover_catalog_cache_hits": _diag1.get(
            "discover_catalog_cache_hits", 0),
        "n_span_failed_recently_calls": _diag1.get(
            "span_failed_recently_calls", 0),
    }
    # R531 §6: close the invocation-local score memo table (the
    # next call's begin() would replace it anyway; explicit close
    # keeps the lifecycle exact).
    mr.selection_memo_end()
    _gen_spans["purpose"] = purpose_tag

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
        # R526 Q-A: per-rung span record, appended immediately so even
        # skipped rungs (spec-None/GONE/no-credential/not-admitted
        # continues below) ride the next durable ledger line of this
        # call — mutated in place along the path, serialized at write.
        _hop = {"rung_index": hop_idx, "provider": provider_id,
                "model": model_id, "purpose": purpose_tag,
                "admission": {"admitted": None},
                "attempts": [], "post_provider_local_s": None,
                "note": None}
        _gen_spans["rungs"].append(_hop)
        # R526 Q-A: transition links attempts WITHIN a rung only;
        # rung-to-rung gaps ride the unattributed remainder.
        _prev_att, _prev_end, _prev_sleep = None, None, 0.0
        if spec is None:
            _hop["note"] = "spec absent — rung skipped, no attempt"
            continue
        next_rung = rungs[hop_idx + 1] if hop_idx + 1 < len(rungs) \
            else None
        next_provider = next_rung[0] if next_rung else None
        next_model = next_rung[1] if next_rung else None
        # a rung whose model is recorded GONE is skipped (known-dead from
        # the provider's own 410 — a recorded fact, not a heuristic)
        if mr.is_model_gone(provider_id, model_id):
            _hop["note"] = "model GONE — rung skipped, no attempt"
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
        # R453-LEAN-CORE (the mandate, "do not probe providers with
        # empty credentials"): a rung whose provider credential is
        # empty is skipped WITHOUT a probe or a call attempt — the
        # typed refusal is recorded on the route (structural: an
        # unkeyed provider can never be probed through generate(),
        # whatever the ladder pinned). The availability matrix is the
        # same authority the chain was built from, so this fires only
        # for rungs added beyond the keyed chain (last-resort bands,
        # stale pins) — never as a silent availability change.
        _spec_rung = _SPEC_BY_ID.get(provider_id)
        # R469: the credential check is ring-aware — a provider with ANY
        # present slot is keyed (the single-key form is the exact
        # pre-R469 check)
        if _spec_rung is not None and active_key_slot(_spec_rung) is None:
            route.append({
                "provider_attempted": provider_id,
                "model": model_id,
                "status": "SKIPPED_NO_CREDENTIAL",
                "failure_type": "NO_CREDENTIAL",
                "timestamp": utc_now(),
                "latency_ms": 0,
                "error": (f"provider {provider_id} has no credential "
                          f"in the environment (ring "
                          f"{key_ring_slots(_spec_rung)} all empty) "
                          "— not probed, not called "
                          "(R453-LEAN-CORE; R469 ring form)"),
                "fallback_provider": next_provider,
                "fallback_model": next_model,
                "cost_class": _spec_rung.cost_basis,
                "selected": False,
                "rung_band": rung_meta.get("band"),
                "task": task,
            })
            last_err = (f"provider {provider_id} unkeyed — no probe, "
                        "no call (empty credential)")
            last_failure_type = "NO_CREDENTIAL"
            _hop["admission"] = {"admitted": False,
                                 "reason": "NO_CREDENTIAL"}
            _hop["note"] = "no credential — rung skipped, no attempt"
            continue
        # R526 Q-A (S4): probe + admission wall, measured where
        # performed. The probe transient-retry sleeps are cooldown-
        # class waiting (measured separately, never folded into the
        # probe wall). A2 (exclusive Q-A subspans) + PART 5
        # (accumulate ALL probe segments): every probe-attempt
        # interval is accumulated into _probe_admission_exclusive_s;
        # the measured probe_retry_sleep is EXCLUDED from each
        # interval (opened just before the probe call, closed just
        # after it; the sleep is a separate measured component). The
        # canonical decomposition
        #   generate_total_s = selection_ordering_exclusive_s
        #     + admission_exclusive_s + probe_retry_sleep_s
        #     + dispatch_s + retry_sleep_s + transition_s
        #     + post_provider_local_s + unattributed_remainder_s
        # double-counts nothing: admission_exclusive_s accounts for
        # ALL probe-attempt walls (first + every retry) plus the
        # final admission check; probe_retry_sleep_s accounts for
        # every probe-retry sleep exactly once. Routing, admission,
        # and transport logic are untouched: telemetry only.
        _probe_admission_exclusive_s = 0.0
        _probe_retry_sleep_s = 0.0
        if _ra.requires_probe(provider_id, model_id):
            _t_adm0 = time.perf_counter()
            _ra.probe_capability(provider_id, model_id,
                                  timeout_s=min(timeout, 30))
            _probe_admission_exclusive_s += (
                time.perf_counter() - _t_adm0)
            _tries = 0
            while (_tries < max_retries
                   and _ra.probe_failure_is_transient(
                       provider_id, model_id)):
                # owner round 2026-11-13 item 2: the probe re-try is
                # IMMEDIATE (no fixed sleep) — the admission probe is
                # a lightweight capability check, not a generation
                _t_adm0 = time.perf_counter()
                _ra.probe_capability(provider_id, model_id,
                                     timeout_s=min(timeout, 30))
                _probe_admission_exclusive_s += (
                    time.perf_counter() - _t_adm0)
                _tries += 1
        else:
            # R526 Q-A (S5): the no-probe path has no separate prep
            # interval to measure (the timer that would bracket an
            # empty block reads ~0 and was not durable evidence). The
            # runtime_admission() call below is the ONLY measured
            # admission wall on this path, and it is accumulated into
            # _probe_admission_exclusive_s via _t_admchk0 below —
            # never a near-zero interval that masks the real wall.
            _probe_admission_exclusive_s = 0.0
        # R526 Q-A (S5): the runtime_admission() call itself is the
        # measured admission-check wall — the timer opens IMMEDIATELY
        # BEFORE the call and closes immediately after, so the wall is
        # included in the exclusive total (S4 defect: the timer was
        # opened AFTER the call returned, so the admission wall was
        # never captured and rode the unattributed remainder).
        _t_admchk0 = time.perf_counter()
        _adm, _adm_note, _adm_ev = _ra.runtime_admission(
            provider_id, model_id)
        _probe_admission_exclusive_s += (
            time.perf_counter() - _t_admchk0)
        _hop["admission"] = {
            "admitted": bool(_adm),
            "probe_admission_s": round(
                _probe_admission_exclusive_s, 6),
            "probe_retry_sleep_s": round(_probe_retry_sleep_s, 6),
            "capability_state": (_adm_ev or {}).get("state"),
            "note": (None if _adm else str(_adm_note)[:200]),
        }
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
        # R526 Q-A: per-attempt span records for this rung (appended to
        # _hop["attempts"]; the rung dict rides every durable ledger
        # line of this call). Transition overhead between consecutive
        # attempts is measured, not inferred.
        _prev_att = None
        _prev_end = None
        _prev_sleep = 0.0
        # R469: the attempt budget is EXTENDED by the credential ring —
        # a KEY ROTATION is not a same-model retry (a different
        # credential is a different request path: it neither consumes
        # the same-model retry budget nor pays a backoff sleep). For
        # every single-key provider ring_extra is 0 and the loop below
        # is behavior-identical to the pre-R469 for-range.
        ring_extra = max(0, len(key_ring_slots(spec)) - 1)
        max_attempts = max_retries + 1 + ring_extra
        retries_used = 0
        key_rotations = 0
        attempt = 0
        # R6 A2 correctness: an economy refusal (open breaker, exhausted
        # healthy/retry budget, replay-cache miss) is a TYPED stop — it
        # must never be retried inside the same-rung ladder. RUNG scope
        # advances to the next provider rung; WALK scope ends the stage.
        _typed_stop: Optional[str] = None
        _typed_stop_scope: Optional[str] = None
        while attempt < max_attempts:
            t0 = time.time()
            # R526 Q-A: attempt record opens here (budget = the cap THIS
            # attempt actually uses; escalations re-record per attempt).
            _t_att0 = time.perf_counter()
            _att = {"attempt_index": attempt + 1,
                    "attempt_budget": attempt_budget,
                    "start_utc": utc_now(),
                    "dispatch_s": None, "retry_sleep_s": 0.0,
                    "transition_to_next_s": None,
                    "ttfb_s": None, "gateway_hang": False,
                    "outcome": None, "failure_type": None,
                    "end_utc": None}
            # R526 Q-A (S4): the transition computation is placed here
            # (next-attempt-open time) but the end timestamp used is the
            # one captured BEFORE the previous attempt's retry sleep,
            # so transition_to_next_s = next_start - prev_end -
            # prev_retry_sleep. The prev_end captured after the sleep
            # would double-subtract the sleep (transition would be
            # negative by the sleep amount); the pre-sleep end makes the
            # decomposition exclusive: the retry sleep is its own
            # component and the transition is the pure bookkeeping gap.
            if _prev_att is not None:
                _prev_att["transition_to_next_s"] = round(
                    time.perf_counter() - _prev_end - _prev_sleep, 6)
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
                # owner round 2026-11-13 item 2: the per-call timeline —
                # the serving transport recorded ttfb/total thread-locally
                # moments above (same thread); a hang is measured, never
                # estimated, and hang walls are excluded from work sums
                _pt = getattr(_post_timing, "last", None)
                if isinstance(_pt, dict) and _pt.get("ttfb_s") is not None:
                    _att["ttfb_s"] = _pt["ttfb_s"]
                    _att["total_s"] = _pt.get("total_s")
                    _att["gateway_hang"] = bool(_pt.get("gateway_hang"))
                # R6 item 1: the typed finish-reason recorded by the
                # serving transport on THIS thread (the flavor call
                # returned moments above, same thread; a failed rung's
                # earlier record was overwritten by this success)
                _finish_reason = _take_finish_reason()
                # R526 Q-A: attempt dispatch wall (existing measurement,
                # copied, never redefined). Post-provider local work
                # (health/route/capability writes + result assembly)
                # completes BEFORE the durable ledger write below, so
                # the written span snapshot is terminal-complete; the
                # ledger file-append itself (~ms) rides the unattributed
                # remainder by rule (documented, never estimated). Write
                # order vs local ops shifted by microseconds only — same
                # values, same calls, same failure classes.
                _att["dispatch_s"] = round(latency_ms / 1000.0, 3)
                _t_loc0 = time.perf_counter()
                # R469: the serving hop records WHICH ring slot answered
                _ok_slot = active_key_slot(spec)
                HEALTH.record_success(
                    spec.provider_id, latency_ms,
                    purpose=purpose_tag,
                    model=model_id)
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
                    "retry_count": retries_used,
                    "attempts": attempt + 1,
                    "key_slot": _ok_slot,
                    "key_env_var": (key_ring_slots(spec)[_ok_slot]
                                    if _ok_slot is not None else None),
                    "key_rotations": key_rotations,
                    "latency_ms": latency_ms,
                    # R10 (owner latency item): TTFB is a MEASUREMENT or
                    # None — never 0. The previous `or 0` converted a
                    # transport that did not record ttfb into a zero-
                    # millisecond claim (the banned missing->0 class).
                    "ttfb_ms": (int(_pt["ttfb_s"] * 1000)
                                if (isinstance(_pt, dict)
                                    and isinstance(_pt.get("ttfb_s"),
                                                   (int, float))) else None),
                    "gateway_hang": (bool(_pt.get("gateway_hang"))
                                     if isinstance(_pt, dict) else False),
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
                _hop["post_provider_local_s"] = round(
                    time.perf_counter() - _t_loc0, 6)
                _att["outcome"] = "OK"
                _att["end_utc"] = utc_now()
                _hop["attempts"].append(_att)
                _prev_att, _prev_end, _prev_sleep = (
                    _att, time.perf_counter(), 0.0)
                # R526 Q-A (A4.10): the ledger write is best-effort
                # telemetry — a failing write must NEVER alter the
                # routing outcome (the routing decision is computed
                # above; the write only appends durable evidence).
                try:
                    mr.record_call_outcome(
                        provider_id, model_id, ok=True,
                        latency_ms=latency_ms, task=task,
                        stage=purpose_tag,
                        run_id=call_prov["run_id"],
                        attempt=attempt + 1,
                        cost_class=spec.cost_basis, selected=True,
                        session_id=call_prov["session_id"],
                        engine_stage=call_prov["engine_stage"],
                        call_class=call_prov["call_class"],
                        account_domain=spec.account_domain,
                        task_degradation=degradation,
                        capability_state="PROBE_OK",
                        request_id=_gen_call_id,
                        generate_spans=_gen_span_snapshot(
                            final=True))
                except Exception:  # noqa: BLE001 — telemetry
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
                    finish_reason=_finish_reason,
                    cost_provenance=_cost_policy.cost_provenance(
                        spec, model_id),
                    call_provenance=call_prov,
                    task_degradation=degradation)
            except EmptyContentWithFinish as exc:
                last_err = f"{type(exc).__name__}: {exc}"
                ftype = classify_failure(exc)
                # R526 Q-A: the failed dispatch wall ends here (the
                # transport raised); the attempt record closes at this
                # point — sleeps below are retry-transition walls.
                _att["dispatch_s"] = round(time.time() - t0, 3)
                _att["end_utc"] = utc_now()
                _att["failure_type"] = ftype
                # reasoning-token exhaustion: SAME provider/model, larger
                # cap (recorded in retry_notes — never a silent change)
                _ceiling = int(getattr(spec, "reasoning_retry_ceiling",
                                       2048) or 2048)
                if attempt_budget < _ceiling:
                    attempt_budget = min(_ceiling, attempt_budget * 4)
                    retry_notes.append(
                        f"attempt {attempt + 1}: empty content "
                        f"(finish_reason={exc.finish_reason}); same "
                        f"provider/model retried with max_tokens="
                        f"{attempt_budget}")
                    if retries_used < max_retries:
                        retries_used += 1
                        attempt += 1
                        # R526 Q-A (S4): capture the attempt end BEFORE
                        # the retry sleep so the next attempt's
                        # transition = next_start - prev_end -
                        # prev_retry_sleep (the sleep is its own
                        # exclusive component, never subtracted twice).
                        _prev_end_presleep = time.perf_counter()
                        _t_rsl0 = time.perf_counter()
                        time.sleep(_retry_sleep_s(retries_used))
                        _att["retry_sleep_s"] = round(
                            time.perf_counter() - _t_rsl0, 6)
                        _att["outcome"] = "RETRIED_ESCALATED"
                        _hop["attempts"].append(_att)
                        _prev_att, _prev_end, _prev_sleep = (
                            _att, _prev_end_presleep,
                            _att["retry_sleep_s"])
                        continue
                else:
                    # R514: at-ceiling empty content — the identical
                    # same-model retry is SKIPPED. An identical budget
                    # on an identical model after a completed-but-empty
                    # generation has no mechanism to succeed
                    # differently; measured R513 (durable
                    # model_routing ledger): 16 at-ceiling
                    # empty-content failures (atria/zai/xkiro,
                    # max_tokens=2048), every one resolved via provider
                    # change, none via identical retry (each wasted
                    # 25-245 s). Falls through to hop recording +
                    # cascade advance (the next rung is the recovery
                    # path, Art. V). The below-ceiling larger-budget
                    # rescue above is preserved untouched.
                    retry_notes.append(
                        f"attempt {attempt + 1}: empty content at max "
                        f"budget (max_tokens={attempt_budget}) — "
                        "identical same-model retry skipped, cascade "
                        "advances (R514)")
                # R526 Q-A: fall-through (R514 at-ceiling or retries
                # exhausted — the escalate path continued above, so
                # reaching here means the attempt failed); the hop
                # recording below closes the rung.
                _att["outcome"] = "FAILED"
                _hop["attempts"].append(_att)
                _prev_att, _prev_end, _prev_sleep = (
                    _att, time.perf_counter(), 0.0)
            except Exception as exc:  # noqa: BLE001 — recorded, retried
                last_err = f"{type(exc).__name__}: {exc}"
                _typed = _econ.typed_state(exc)
                if _typed:
                    # TYPED ECONOMY STOP (Art. XXI.3 / LXI): close the
                    # attempt honestly, record the typed route state, and
                    # do NOT retry the same rung. A healthy/retry cap or
                    # a replay-cache miss ends the whole walk (no live
                    # spend is permitted); a provider breaker only ends
                    # this provider's rung and the cascade may advance.
                    # A breaker can stop a rung BEFORE any request (already
                    # open) or ON the request that crossed the threshold.
                    # Only the latter is a provider attempt: record it as
                    # such so the route, health table and routing ledger
                    # never lose a request that actually happened.
                    _request_made = bool(
                        getattr(exc, "request_made", False))
                    _provider_ftype = None
                    if _request_made and exc.__cause__ is not None:
                        _provider_ftype = classify_failure(exc.__cause__)
                    _att["dispatch_s"] = round(time.time() - t0, 3)
                    _att["end_utc"] = utc_now()
                    _att["failure_type"] = _typed
                    _att["outcome"] = ("FAILED_BREAKER_OPEN"
                                       if _request_made
                                       else "ABORTED_TYPED")
                    _hop["attempts"].append(_att)
                    _prev_att, _prev_end, _prev_sleep = (
                        _att, time.perf_counter(), 0.0)
                    route.append({
                        "provider_attempted": spec.provider_id,
                        "model": model_id,
                        "status": ("FAILED_BREAKER_OPEN" if _request_made
                                   else "ABORTED_TYPED"),
                        "failure_type": _typed,
                        "typed_state": _typed,
                        "provider_failure_type": _provider_ftype,
                        "timestamp": utc_now(),
                        "retry_count": retries_used,
                        "attempts": attempt + (1 if _request_made else 0),
                        "key_rotations": key_rotations,
                        "latency_ms": int((time.time() - t0) * 1000),
                        "error": str(last_err)[:300],
                        "fallback_provider": next_provider,
                        "fallback_model": next_model,
                        "fallback_reason": (
                            f"{_typed}: the economy governor stopped "
                            f"this rung immediately (no same-rung retry); "
                            f"next={next_provider or 'none (last rung)'}"),
                        "cost_class": spec.cost_basis,
                        "account_domain": spec.account_domain,
                        "selected": False,
                        "rung_band": rung_meta.get("band"),
                        "task": task,
                        "capability_state": ("PROBE_OK" if _request_made
                                             else "NOT_ATTEMPTED"),
                    })
                    if _request_made and _provider_ftype:
                        # the provider DID answer (transiently failed):
                        # keep its health + durable ledger line even though
                        # the typed stop bypasses the ordinary failure path
                        HEALTH.record_failure(
                            spec.provider_id, _provider_ftype,
                            purpose=purpose_tag, model=model_id,
                            error=str(last_err))
                        try:
                            mr.record_call_outcome(
                                provider_id, model_id, ok=False,
                                latency_ms=int((time.time() - t0) * 1000),
                                failure_type=_provider_ftype, task=task,
                                stage=purpose_tag,
                                run_id=call_prov["run_id"],
                                attempt=attempt + 1,
                                session_id=call_prov["session_id"],
                                engine_stage=call_prov["engine_stage"],
                                call_class=call_prov["call_class"],
                                account_domain=spec.account_domain,
                                task_degradation=degradation,
                                capability_state="PROBE_OK",
                                fallback_from=(provider_id
                                               if next_provider else None),
                                fallback_to=next_provider,
                                error=str(last_err),
                                cost_class=spec.cost_basis, selected=False,
                                fallback_reason=(
                                    f"{_provider_ftype} opened the "
                                    f"circuit breaker -> fallback to "
                                    f"{next_provider or 'none (last rung)'}"),
                                request_id=_gen_call_id,
                                generate_spans=_gen_span_snapshot(
                                    final=(next_provider is None)))
                        except Exception:  # noqa: BLE001 — telemetry
                            pass
                    last_failure_type = _typed
                    _typed_stop = _typed
                    # a per-problem budget refusal (healthy OR retry cap)
                    # and a replay miss end the whole walk — advancing to
                    # another provider rung would spend attempts the cap
                    # forbids / diverge from the recording. Only a
                    # provider breaker is scoped to its own rung.
                    _typed_stop_scope = (
                        "WALK" if isinstance(
                            exc, (_econ.CallBudgetExceeded,
                                  _econ.TypedCacheMiss))
                        else "RUNG")
                    break
                ftype = classify_failure(exc)
                # R526 Q-A: failed dispatch wall ends here (same rule as
                # the empty-content path above).
                _att["dispatch_s"] = round(time.time() - t0, 3)
                _att["end_utc"] = utc_now()
                _att["failure_type"] = ftype
                # GONE (410) / MODEL_NOT_FOUND (404 or the provider's
                # own model_not_found body — R451-C1.2): the identifier
                # is known-dead on this route — retrying the SAME dead
                # model wastes the budget (operator directive: never
                # retry a permanently invalid model identifier). Skip
                # the same-model retry (fall straight through to the hop
                # RECORDING and the next rung); the hop must still be
                # recorded — a dead id that is silently skipped would be
                # exactly the unrecorded-failover the directive forbids.
                # R462: REGION_NOT_SERVED joins the same reasoning — a
                # region-gated endpoint (the tokenharbor specimen,
                # 403 region_blocked pre-auth) answers IDENTICALLY on
                # every same-model retry from this egress; the cascade
                # advances instead (never retried within the walk).
                # R469: OPERATOR KEY-RING ROTATION — "Keep going to a
                # new key of atira if one is exhausted." An exhaustion-
                # class failure on a multi-key provider rotates to the
                # NEXT PRESENT key on the SAME rung (same provider,
                # same model) BEFORE any provider-level fallback: the
                # ring is consumed key by key. The rotation is a
                # recorded route hop + ledger event (never silent,
                # Art. IV); the PROVIDER's health is NOT failure-marked
                # by a key-slot exhaustion the ring survives (the rung
                # continues on the next credential). A ring that
                # exhausts entirely falls through to the standing hop
                # record below (typed failure, cascade advances).
                if ftype in KEY_ROTATION_FAILURE_CLASSES:
                    _slot_from = active_key_slot(spec)
                    _slot_to = rotate_key(spec)
                    if _slot_to is not None:
                        key_rotations += 1
                        retry_notes.append(
                            f"attempt {attempt + 1}: ring slot "
                            f"{_slot_from} answered {ftype} — rotated "
                            f"to slot {_slot_to} "
                            f"({key_ring_slots(spec)[_slot_to]}), same "
                            "provider/model (R469 keep-going directive)")
                        route.append({
                            "provider_attempted": spec.provider_id,
                            "model": model_id,
                            "status": "FAILED_KEY_EXHAUSTED",
                            "failure_type": ftype,
                            "action": "KEY_ROTATED",
                            "key_slot_exhausted": _slot_from,
                            "key_slot": _slot_to,
                            "key_env_var": key_ring_slots(spec)[_slot_to],
                            "timestamp": utc_now(),
                            "retry_count": retries_used,
                            "attempts": attempt + 1,
                            "latency_ms": int((time.time() - t0) * 1000),
                            "error": str(last_err)[:300],
                            "fallback_provider": spec.provider_id,
                            "fallback_model": model_id,
                            "fallback_reason": (
                                f"{ftype} on ring slot {_slot_from} -> "
                                f"KEY_ROTATED to slot {_slot_to} (same "
                                "provider/model, next credential — the "
                                "R469 keep-going directive)"),
                            "cost_class": spec.cost_basis,
                            "account_domain": spec.account_domain,
                            "selected": False,
                            "rung_band": rung_meta.get("band"),
                            "task": task,
                        })
                        try:
                            mr.record_call_outcome(
                                provider_id, model_id, ok=False,
                                latency_ms=int(
                                    (time.time() - t0) * 1000),
                                failure_type=ftype, task=task,
                                stage=purpose_tag,
                                run_id=call_prov["run_id"],
                                attempt=attempt + 1,
                                session_id=call_prov["session_id"],
                                engine_stage=call_prov["engine_stage"],
                                call_class=call_prov["call_class"],
                                account_domain=spec.account_domain,
                                task_degradation=degradation,
                                capability_state="PROBE_OK",
                                fallback_from=provider_id,
                                fallback_to=provider_id,
                                error=str(last_err),
                                cost_class=spec.cost_basis,
                                selected=False,
                                fallback_reason=(
                                    f"{ftype} on ring slot {_slot_from} "
                                    f"-> KEY_ROTATED to slot {_slot_to} "
                                    "(same provider/model, next "
                                    "credential)"),
                                request_id=_gen_call_id,
                                generate_spans=_gen_span_snapshot())
                        except Exception:  # noqa: BLE001 — telemetry
                            pass
                        # R526 Q-A: rotation carries no backoff sleep (new
                        # credential by rule); the attempt record closes
                        # here with the rotation outcome.
                        _att["outcome"] = "ROTATED"
                        _att["key_slot_from"] = _slot_from
                        _att["key_slot_to"] = _slot_to
                        _att["end_utc"] = utc_now()
                        _hop["attempts"].append(_att)
                        _prev_att, _prev_end, _prev_sleep = (
                            _att, time.perf_counter(), 0.0)
                        attempt += 1
                        continue  # next key — no backoff (new credential)
                if ftype not in ("GONE", "MODEL_NOT_FOUND",
                                 "REGION_NOT_SERVED") \
                        and retries_used < max_retries:
                    retries_used += 1
                    attempt += 1
                    # R526 Q-A (S4): capture the attempt end BEFORE the
                    # retry sleep so the next attempt's transition =
                    # next_start - prev_end - prev_retry_sleep (the
                    # sleep is its own exclusive component, never
                    # subtracted twice).
                    _prev_end_presleep = time.perf_counter()
                    # R526 Q-A: retry-transition sleep, measured where
                    # taken (cooldown-class waiting, never folded into
                    # the dispatch wall). R10: routed through the typed
                    # pacing helper (ENGINE_LLM_RETRY_SLEEP_S knob).
                    _t_rsl0 = time.perf_counter()
                    time.sleep(_retry_sleep_s(retries_used))
                    _att["retry_sleep_s"] = round(
                        time.perf_counter() - _t_rsl0, 6)
                    _att["outcome"] = "RETRIED"
                    _att["end_utc"] = utc_now()
                    _hop["attempts"].append(_att)
                    _prev_att, _prev_end, _prev_sleep = (
                        _att, _prev_end_presleep, _att["retry_sleep_s"])
                    continue
            # R6 A2 correctness: a typed economy stop bypasses the
            # provider-failure bookkeeping below (the provider did not
            # fail — the budget/breaker did). WALK scope ends the stage
            # with the typed failure_type; RUNG scope advances honestly.
            if _typed_stop is not None:
                _hop["note"] = f"typed economy stop: {_typed_stop}"
                if _typed_stop_scope == "WALK":
                    break
                continue
            # R526 Q-A: fall-through (dead identifier or retries
            # exhausted) — the attempt failed; the hop recording below
            # closes the rung.
            if _att.get("outcome") is None:
                _att["outcome"] = "FAILED"
                _att["end_utc"] = utc_now()
                _hop["attempts"].append(_att)
                _prev_att, _prev_end, _prev_sleep = (
                    _att, time.perf_counter(), 0.0)
            # this attempt exhausted the same-model budget -> record
            # the hop honestly and move to the next rung.
            # R526 Q-A: post-provider local wall (failure bookkeeping +
            # route assembly) closes BEFORE the durable write, so the
            # written span snapshot is terminal-complete for this rung;
            # the ledger file-append itself (~ms) rides the unattributed
            # remainder by rule. Write order vs local ops shifted by
            # microseconds only — same values, same calls, same classes.
            _t_loc0 = time.perf_counter()
            HEALTH.record_failure(
                spec.provider_id, ftype,
                purpose=purpose_tag,
                model=model_id, error=str(last_err))
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
                "retry_count": retries_used,
                "attempts": attempt + 1,
                "key_rotations": key_rotations,
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
            _hop["post_provider_local_s"] = round(
                time.perf_counter() - _t_loc0, 6)
            # R526 Q-A (A4.10): best-effort telemetry — a failing
            # ledger write must never alter the routing outcome.
            try:
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
                    fallback_from=(provider_id if next_provider
                                  else None),
                    fallback_to=next_provider,
                    error=str(last_err),
                    cost_class=spec.cost_basis, selected=False,
                    fallback_reason=(
                        f"{ftype}: {str(last_err)[:160]} -> fallback "
                        f"to {next_provider or 'none (last rung)'}"),
                    request_id=_gen_call_id,
                    generate_spans=_gen_span_snapshot(
                        final=(next_provider is None)))
            except Exception:  # noqa: BLE001 — telemetry
                pass
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

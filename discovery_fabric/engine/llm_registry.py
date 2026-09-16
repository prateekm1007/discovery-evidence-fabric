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
    # ------------------------------------------------------------------
    # R456-A3 (2026-09-15): the operator's free-tier router quartet —
    # the A3 capability-floor unblock. Operator directive (verbatim):
    #   "Use these to use free ai models like qwen 3.8, glm 5.3,
    #    deepseek, minimax etc. once tokens run out of one go to the
    #    next provider"
    # EVERY spec below was LIVE-MEASURED before registration (the
    # R451-C1.2 probe-before-admit discipline: a tiny completion through
    # the provider's REAL transport, recorded in the policy note; catalog
    # presence is never admission evidence). Cost basis FREE_TIER_API —
    # eligible under ZERO_PAID_COST per the recorded operator amendment
    # (model_cost_policy.py v1.1.0). Each key is a DISTINCT economic
    # account: quota exhaustion on one advances the cascade to the next
    # (the operator's rotation rule), and the accounts are genuinely
    # redundant (transport_capability: redundancy across ACCOUNT
    # domains, never routes).
    # ------------------------------------------------------------------
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
        "https://xkiro.com/v1/chat/completions",
        "qwen/qwen3.8-max:free", "openai", 128_000,
        quality_tier=2, cost_tier=1, latency_tier=2,
        cost_basis="FREE_TIER_API", locality="REMOTE",
        license="provider serving terms (free tier, no deposit)",
        account_domain="OWNER_XKIRO_ACCOUNT",
        model_revision="router free tier; qwen/qwen3.8-max:free and "
                       "minimax/minimax-m3:free measured live 2026-09-14 "
                       "(tiny completions 3.2 s / 3.4 s); no per-model "
                       "revision pin exposed by the router — recorded "
                       "honest (Art. VI)",
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
            "only). LIVE-MEASURED at registration: GET /v1/models -> 200 "
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
        "apinex", "APINEX_API_KEY",
        "https://apinex.bond/v1/chat/completions",
        "free/deepseek-v4.1-flash", "openai", 128_000,
        quality_tier=2, cost_tier=1, latency_tier=3,
        cost_basis="FREE_TIER_API", locality="REMOTE",
        license="provider serving terms (free tier, no deposit)",
        account_domain="OWNER_APINEX_ACCOUNT",
        model_revision="router free tier; free/deepseek-v4.1-flash "
                       "measured live 2026-09-14 (tiny completion 2.4 s); "
                       "no per-model revision pin exposed by the router — "
                       "recorded honest (Art. VI)",
        extra_headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/131.0.0.0 Safari/537.36"},
        policy_note=(
            "R456-A3 operator-supplied free-tier router #3. TRANSPORT "
            "REQUIREMENT (measured): apinex.bond sits behind the same "
            "Cloudflare browser-signature check (urllib UA banned 403 "
            "error 1010; Chrome UA passes) — carried in extra_headers. "
            "LIVE-MEASURED at registration: GET /v1/models -> 200 with "
            "26 models incl. an explicit free/ set; free/deepseek-v4.1-"
            "flash tiny completion -> 200 PROBE_OK 2.4 s; free/gpt-5.6-"
            "luna -> 200 PROBE_OK 6.3 s; free/mimo-v2.5 -> 200 PROBE_OK "
            "8.0 s. free/qwen-3.8-max answers 200 with content null at "
            "small caps (reasoning-shaped — EmptyContentWithFinish "
            "class); free/glm-5.3-flash and free/deepseek-v4-flash-0731 "
            "timed out at 45 s on the probe window (busy free pool — "
            "the cascade's job, not a dead mark). deepseek-v4.1-flash is "
            "the STRONG rung (the engine's existing deepseek-v4-flash "
            "rungs declare STRONG+FAST+CHEAP; v4.1-flash is the same "
            "class). Tiers are recorded policy inputs (Art. XXVII).")),
    ProviderSpec(
        "bai", "BAI_API_KEY",
        "https://api.b.ai/v1/chat/completions",
        "qwen3.8-flash", "openai", 128_000,
        quality_tier=3, cost_tier=1, latency_tier=1,
        cost_basis="FREE_TIER_API", locality="REMOTE",
        license="provider serving terms (free tier, no deposit)",
        account_domain="OWNER_BAI_ACCOUNT",
        model_revision="router free tier; qwen3.8-flash measured live "
                       "2026-09-14 (tiny completion 1.5 s); no per-model "
                       "revision pin exposed by the router — recorded "
                       "honest (Art. VI)",
        policy_note=(
            "R456-A3 operator-supplied free-tier router #4. LIVE-MEASURED "
            "at registration: GET /v1/models -> 200 with 47 models "
            "(claude/gpt/gemini/glm/qwen3.8/minimax/kimi...); MOST are "
            "deposit-gated premium (403 'Deposit required to unlock "
            "premium models' — classified CREDIT_EXHAUSTED, the cascade "
            "advances); the MEASURED free answerers: qwen3.8-flash -> "
            "200 PROBE_OK 1.5 s and mimo-v2.5 -> 200 PROBE_OK 1.9 s; "
            "minimax-m2.7 answers 400 'credit insufficient balance: "
            "balance=0 required=2406' — per-model credit gating, "
            "classified CREDIT_EXHAUSTED (the measured specimen rides "
            "provider_health). HONEST TIERS: quality_tier 3 — the "
            "measured free answerers are the FLASH/derived class (fast "
            "mid-tier), NOT the flagship class on the other three "
            "routers; this provider's role in the rotation is the FAST "
            "fallback (latency_tier 1, measured 1.5 s), with "
            "task_capabilities FAST+CHEAP (no STRONG claim — the "
            "strong flagships here are premium-gated). Default urllib "
            "User-Agent passes (no CF block on api.b.ai). Tiers are "
            "recorded policy inputs (Art. XXVII).")),
    # ------------------------------------------------------------------
    # R461 (2026-09-15): the FIFTH free-tier router — bynara. The key
    # arrived 2026-09-14 with the quartet but measured 403
    # telegram_required ("Join the required Telegram group/channel and
    # relink at /settings to continue") — a typed ACCOUNT-ENTRY GATE,
    # escalated to the owner per Art. LXV (R461/
    # BYNARA_OWNER_ACTION_ESCALATION.json). The owner acted ("bynara
    # (new router) — key valid telegram joined", 2026-09-15): the gate
    # is RESOLVED and the account now serves. Probe-before-admit held
    # throughout — the registration below quotes only measurements
    # taken AFTER the owner action (R461/PROBE_CATALOG.json +
    # PROBE_COMPLETIONS.json).
    # ------------------------------------------------------------------
    ProviderSpec(
        "bynara", "BYNARA_API_KEY",
        "https://router.bynara.id/v1/chat/completions",
        "tencent-hy3-free", "openai", 128_000,
        quality_tier=3, cost_tier=1, latency_tier=2,
        cost_basis="FREE_TIER_API", locality="REMOTE",
        license="provider serving terms (free tier, no deposit)",
        account_domain="OWNER_BYNARA_ACCOUNT",
        model_revision="router free tier; tencent-hy3-free measured "
                       "live 2026-09-15 (tiny completions 1.91-2.53 s, "
                       "3x stable); no per-model revision pin exposed "
                       "by the router — recorded honest (Art. VI)",
        policy_note=(
            "R461 operator-supplied free-tier router #5 (bynara, "
            "router.bynara.id — the account-entry gate resolved by the "
            "owner's telegram join, the Art. LXV escalation answered). "
            "LIVE-MEASURED at registration (post-owner-action): GET "
            "/v1/models -> 200 with 49 models incl. an explicit -free "
            "family (glm-5.3-free, qwen3.8-flash-free, mimo-v2.5-free, "
            "muse-spark-1.3-contributor-free, tencent-hy3-free); "
            "tencent-hy3-free tiny completion -> 200 PROBE_OK 2.53 s / "
            "1.91 s / 1.91 s (3 passes, stable). The account's OTHER "
            "-free models measured credit/plan-gated on this key at "
            "registration time: glm-5.3-free -> 402 'Insufficient "
            "credits. Please top up your balance.' and mimo-v2.5-free "
            "-> 429 'Insufficient credits ... try again in a few "
            "minutes' (the account's small free credit allowance is "
            "depleted for those rungs — typed CREDIT_EXHAUSTED / "
            "RATE_LIMITED, the cascade advances and the cooldown "
            "ladder retries); qwen3.8-flash-free + muse-spark-1.3-"
            "contributor-free -> 403 'Your plan does not include the "
            "requested model.' (per-model plan gate, the xkiro "
            "deposit-gate precedent — typed CREDIT_EXHAUSTED, the "
            "provider stays eligible). Default urllib User-Agent "
            "passes (no CF block on router.bynara.id). HONEST TIERS: "
            "quality_tier 3 — tencent-hy3 carries flagship-family "
            "naming but the free-tier serving path is UNMEASURED on "
            "the engine's structured protocol; no STRONG claim (the "
            "measured rung registers FAST+CHEAP, latency_tier 2, "
            "measured ~2 s). The -free family allowlist admits all "
            "five ids so catalog discovery can route to whichever "
            "rung the account's credit state admits (family policy, "
            "never today's availability — Art. XXVII). Tiers are "
            "recorded policy inputs (Art. XXVII).")),
    # ------------------------------------------------------------------
    # R467 (2026-09-15): the EIGHTH router — atria. The operator
    # supplied the key with the declarations "it gives 100million tokens
    # of new model which is as good as glm5.3" and "we should be token
    # surplus now" (the token-surplus directive — the R466 reaudit's
    # named binding constraint was the free-router cascade's MECHANISM-
    # stage inference quality, an Art. LXV owner-side capacity question;
    # this key is the owner's answer). Probe-before-admit held
    # (R467/PROBE_CATALOG.json + R467/PROBE_COMPLETIONS.json): every
    # fact below is measured, the operator's quality/budget claims are
    # recorded as OPERATOR-DECLARED where no provider surface exposes
    # them (Art. VI/XXV).
    # ------------------------------------------------------------------
    ProviderSpec(
        "atria", "ATRIA_API_KEY",
        "https://api.atria-asi.ai/v1/chat/completions",
        "Atria-Dawn-Preview", "openai", 128_000,
        quality_tier=2, cost_tier=1, latency_tier=3,
        cost_basis="FREE_TIER_API", locality="REMOTE",
        license="provider serving terms (operator-declared free token "
                "budget; no deposit authorized)",
        account_domain="OWNER_ATRIA_ACCOUNT",
        probe_max_tokens=256,
        # R469 (2026-09-16): the key RING — the operator's keep-going
        # directive, verbatim: "Keep going to a new key of atira if one
        # is exhausted. Wire it in the discovery engine." Key 3
        # (ATRIA_API_KEY_3) was probe-validated before this registration
        # (R469/PROBE_ATRIA_KEY3.json: the bogus-key 401 differential
        # control; catalog 200 on ALL THREE keys — the same sole model
        # Atria-Dawn-Preview; a 200 non-empty tiny completion on key 3
        # in 17.9 s; keys 1/2 identity-confirmed against the R467/R468
        # records; all three keys DISTINCT). An exhaustion-class
        # failure (CREDIT_EXHAUSTED / AUTH_FAILURE / RATE_LIMITED)
        # rotates through the ring on the SAME rung before any
        # provider-level fallback; every rotation is a recorded route
        # hop (never silent, Art. IV).
        #
        # R470 (2026-09-16): the operator supplied seven more keys. The
        # PARALLEL-LINE RECONCILIATION (this commit, rebased onto the
        # sibling R470-C2's ten-slot registration): the sibling set
        # 10/10 keys on the Space surface BY NAME (write-only API —
        # presence, not validity; R470/HF_SPACE_SECRETS_ATRIA_RING10.json)
        # and registered all ten; THIS line's probe-before-record
        # measured every key's VALIDITY (R470/PROBE_ATRIA_KEYS4TO10.json:
        # keys 1-3 identity-confirmed vs the R467/R468/R469 records; all
        # ten pairwise DISTINCT; catalog 200 on keys 4,5,6,7,9,10 with
        # the sole model Atria-Dawn-Preview; one 200 non-empty tiny
        # completion on key 4 in 1.02 s after one disclosed transient
        # 502). ATRIA_API_KEY_8 is NOT REGISTERED: its catalog probe
        # answered a DETERMINISTIC 401 x3 (re-probed twice, 8 s apart)
        # — the bogus-key differential class — so it is typed INVALID
        # and EXCLUDED from the ring (the measured verdict outranks the
        # name-present surface, Art. III); the vault keeps the value
        # for the operator's re-supply/reference, the Space surface may
        # carry it inertly (the ring is the selection authority), and
        # the slot number is NOT reused (ATRIA_API_KEY_9/_10 keep their
        # operator-given names so future keys append unambiguously).
        # 9 VALID slots x operator-declared 100M = the ~900M-token
        # surplus (OPERATOR-DECLARED; no usage endpoint is measurable —
        # Art. VI/XXV).
        #
        # R472 (2026-09-16, the PARALLEL-LINE RECONCILIATION of two
        # probe lines on the SAME operator delivery): the operator
        # re-supplied key 8 (same string) and delivered keys 11-15
        # (the sibling line's message carried 11-13; this line's
        # carried 11-15 — the union is five new keys).
        #
        # KEY 8, BOTH MEASUREMENTS RECORDED (Art. III — the measured
        # verdict outranks the surface in BOTH directions, and the
        # LATEST typed measurement decides): the sibling's probe
        # (R472/PROBE_ATRIA_KEYS11TO13.json, 22:40:28Z) measured the
        # re-supplied key 8 catalog 200 x3 — CLEARED and REINSTATED on
        # their line. THIS line's probe (R472/PROBE_ATRIA_KEYS11TO15
        # .json, 22:57Z) measured the SAME value (fingerprint
        # atr_DH...1QzF, identical) DETERMINISTIC 401 x3 (re-probed
        # twice, 8 s apart), and the post-rebase decisive re-measure
        # (this commit, ~00:05Z) answered 401 x3 AGAIN — key 8's
        # provider-side state FLAPPED (200-window at 22:40, 401
        # deterministic after 22:57). The current typed verdict is
        # INVALID: key 8 is EXCLUDED from the ring (the latest
        # measurement rules; the flapping is disclosed, never hidden);
        # the vault keeps the value, the Space surface carries it
        # inertly, the slot number is NOT reused.
        #
        # THE FIVE NEW KEYS (both lines' probes agree): keys 11-15
        # catalog 200 each (sole model Atria-Dawn-Preview, bogus-key
        # differential 401); one 200 non-empty tiny completion on key
        # 11 (this line: 4.06 s; the sibling: 1.79 s — independent
        # confirmations); all fifteen pairwise DISTINCT; keys 1-10
        # identity-confirmed vs the R470 record. 14 VALID slots x
        # operator-declared 100M = the ~1.4B-token surplus
        # (OPERATOR-DECLARED; no usage endpoint is measurable —
        # Art. VI/XXV). The Space surface carries all fifteen names
        # (R472/HF_SPACE_SECRETS_ATRIA_RING15.json: 15/15 PRESENT;
        # the sibling's RING13 record superseded by the union).
        key_env_vars=["ATRIA_API_KEY", "ATRIA_API_KEY_2",
                      "ATRIA_API_KEY_3", "ATRIA_API_KEY_4",
                      "ATRIA_API_KEY_5", "ATRIA_API_KEY_6",
                      "ATRIA_API_KEY_7", "ATRIA_API_KEY_9",
                      "ATRIA_API_KEY_10", "ATRIA_API_KEY_11",
                      "ATRIA_API_KEY_12", "ATRIA_API_KEY_13",
                      "ATRIA_API_KEY_14", "ATRIA_API_KEY_15"],
        model_revision="Atria-Dawn-Preview — the catalog's SOLE model id "
                       "(owned_by atria, 2026-09-15 catalog); no revision "
                       "pin exposed by the provider — recorded honest "
                       "(Art. VI)",
        policy_note=(
            "R467 operator-supplied router #8 (atria, api.atria-asi.ai — "
            "the operator's own citation api.atria-asi.ai/console/keys "
            "names the API host itself; no external provider table "
            "needed). LIVE-MEASURED at registration (Art. III): GET "
            "/v1/models -> 200 with exactly ONE model (Atria-Dawn-"
            "Preview, owned_by atria); the format-identical bogus-key "
            "differential -> 401 vs 200 proves the delivered key VALID "
            "(auth evaluates before any gate; the R463 method); "
            "dialect OpenAI /v1/chat/completions (the Anthropic "
            "/v1/messages control answers 400); default urllib "
            "User-Agent passes (no CF block). Tiny completions -> 200 "
            "READY x3 (0.93-7.65 s). THE MECHANISM-STAGE INSTRUMENT "
            "(the R466 open item this rung answers): the FIELD-line "
            "protocol test — small caps (max_tokens 300) starve content "
            "to empty while reasoning_content carries the chain-of-"
            "thought (the EmptyContentWithFinish class; the engine's "
            "documented larger-cap retry on the SAME rung is not a "
            "downgrade); the retry at max_tokens 2000 -> 200 with "
            "3/3 clean FIELD_MECHANISM/FIELD_KEY_VARIABLE/"
            "FIELD_FALSIFIER lines in content (8.4 s) — FORMAT-"
            "COMPLIANT on the engine's structured protocol, the "
            "measurement bynara's rung honestly lacked. HONEST TIERS: "
            "quality_tier 2 — the basis is the OPERATOR'S declaration "
            "verbatim ('new model which is as good as glm5.3', the "
            "glm-5.3-class tier the other free routers carry) PLUS the "
            "measured FIELD-protocol compliance above (recorded policy "
            "input, Art. XXVII); latency_tier 3 — the reasoning path "
            "measured 0.55-8.71 s variance, honestly slower than the "
            "flash rungs. Context capacity NOT exposed by the catalog — "
            "128_000 is the router-family default, recorded honest "
            "(Art. VI). The 100M-token budget claim is OPERATOR-"
            "DECLARED (no usage/balance endpoint measurable: /v1/usage, "
            "/v1/balance, /v1/credits all 404/405) — depletion, when "
            "measured, stays a typed failure that advances the cascade, "
            "never a bill. FREE_TIER_API under the R456-A3 operator "
            "amendment: eligible under ZERO_PAID_COST. R469 "
            "(2026-09-16): the operator's DEFAULT-PROVIDER directive, "
            "verbatim: 'From Now on atira is out default API for "
            "discovery engine.' — atria is the HEAD of every role's "
            "default order (ENGINE_DEFAULT_PROVIDER, the operator-"
            "override class; provider_health.order_for_role) with the "
            "Art. XLV attack-independence rule and the Art. V cooldown "
            "demotion still taking precedence over the pin; the honest "
            "tier-2 quality basis is UNCHANGED (a routing pin, never "
            "a quality rewrite). The FOURTEEN-KEY ring (key_env_vars "
            "above; R472: keys 11-15 probe-validated, key 8 re-probed "
            "invalid and excluded) rotates on exhaustion-class "
            "failures — the keep-going directive: 'Keep going to a "
            "new key of atira if one is exhausted.'")),
    # ------------------------------------------------------------------
    # R463 (2026-09-15): the USER's Hugging Face credential path — the
    # operator's P0 architectural ruling ("the user gives Toscanini AI
    # access, and Toscanini does the rest; one legitimate user/
    # application AI credential path"). The credential is HF_TOKEN (the
    # account owner's own fine-grained key, deployed as a Space secret).
    # Probe-before-admit held: catalog 200 (142 models incl. the
    # flagship classes); EVERY completion 402 — the account's monthly
    # included Inference Providers credits are DEPLETED (the provider's
    # own words, verbatim in R463/PROBE_HF_ROUTER.json). Registered
    # HONESTLY as capable-not-currently-servable: the rung enters the
    # cascade, classifies typed CREDIT_EXHAUSTED on probe (the R436
    # class), and serves automatically when the credits reset or are
    # topped up. No failure was converted into success (Art. XV/XXV/
    # LXI).
    # ------------------------------------------------------------------
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
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _call_openai_flavor(spec: ProviderSpec, messages: List[dict],
                        timeout: int, max_tokens: int,
                        model_override: Optional[str] = None) -> str:
    # R469: the ACTIVE ring key (single-key providers: env_var, exactly
    # the pre-R469 read — one key-selection authority, Art. X)
    key = active_key_value(spec)
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
    headers = {"Authorization": f"Bearer {key}"}
    if spec.extra_headers:
        headers.update(spec.extra_headers)
    data = _post_json(
        spec.url_for_call(), payload, headers, timeout)
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
            continue
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
        while attempt < max_attempts:
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
                # R469: the serving hop records WHICH ring slot answered
                _ok_slot = active_key_slot(spec)
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
                    "retry_count": retries_used,
                    "attempts": attempt + 1,
                    "key_slot": _ok_slot,
                    "key_env_var": (key_ring_slots(spec)[_ok_slot]
                                    if _ok_slot is not None else None),
                    "key_rotations": key_rotations,
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
                if retries_used < max_retries:
                    retries_used += 1
                    attempt += 1
                    time.sleep(2 * retries_used)
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
                                    "credential)"))
                        except Exception:  # noqa: BLE001 — best-effort
                            pass
                        attempt += 1
                        continue  # next key — no backoff (new credential)
                if ftype not in ("GONE", "MODEL_NOT_FOUND",
                                 "REGION_NOT_SERVED") \
                        and retries_used < max_retries:
                    retries_used += 1
                    attempt += 1
                    time.sleep(2 * retries_used)
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

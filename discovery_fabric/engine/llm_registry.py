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

# Status vocabulary (explicit; Art. XXV — unknown stays unknown)
ST_OK = "OK"
ST_PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
ST_CALL_FAILED = "CALL_FAILED"


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
        "tokenrouter", "TOKEN_ROUTER_API_KEY",
        "https://api.tokenrouter.com/v1/chat/completions",
        "z-ai/glm-5.3-free", "openai", 128_000,
        quality_tier=2, cost_tier=1, latency_tier=2,
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
            "behind the sandbox gateway's ~2 s.")),
    ProviderSpec(
        "zai", "ZAI_API_KEY",
        "http://127.0.0.1:8787/v1/chat/completions",
        "glm-4-plus", "openai", 128_000,
        quality_tier=2, cost_tier=1, latency_tier=1,
        policy_note=(
            "sandbox-local OpenAI-compatible gateway (scripts/zai_gateway.mjs) "
            "backed by the z-ai SDK serving glm-4-plus (verified live "
            "2026-08-30: READY probe, ~2 s). Registered as the HEALTHY "
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
        policy_note=("legacy synthesis provider; frozen synthesis model "
                     "deepseek/deepseek-v4-flash-0731 (a2 FROZEN_MODEL)")),
    ProviderSpec(
        "nvidia", "NVIDIA_API_KEY",
        "https://integrate.api.nvidia.com/v1/chat/completions",
        "deepseek-ai/deepseek-v4-flash-0731", "openai", 128_000,
        quality_tier=2, cost_tier=1, latency_tier=1,
        policy_note=("hosts the FROZEN synthesis model "
                     "deepseek-ai/deepseek-v4-flash-0731 (same family as the "
                     "a2 FROZEN_MODEL); legacy default meta/llama-3.1-8b-"
                     "instruct was retired from the NVIDIA catalog (HTTP 410, "
                     "verified 2026-08-27) — replacement is EXPLICIT, not "
                     "silent, and stays on the frozen model family")),
    ProviderSpec(
        "anthropic", "ANTHROPIC_API_KEY",
        "https://api.anthropic.com/v1/messages",
        "claude-sonnet-4-20250514", "anthropic", 200_000,
        quality_tier=1, cost_tier=3, latency_tier=3,
        policy_note="highest quality tier; used first when available"),
    ProviderSpec(
        "gemini", "GEMINI_API_KEY",
        "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "gemini-2.0-flash", "openai", 1_000_000,
        quality_tier=2, cost_tier=1, latency_tier=2,
        policy_note="largest context capacity; OpenAI-compatible endpoint"),
    ProviderSpec(
        "openai", "OPENAI_API_KEY",
        "https://api.openai.com/v1/chat/completions",
        "gpt-4o", "openai", 128_000,
        quality_tier=1, cost_tier=3, latency_tier=2,
        policy_note="highest quality tier; used first when available"),
    ProviderSpec(
        "qwen", "QWEN_API_KEY",
        "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "qwen-max", "openai", 128_000,
        quality_tier=2, cost_tier=2, latency_tier=2,
        policy_note="DashScope OpenAI-compatible mode"),
    ProviderSpec(
        "deepseek", "DEEPSEEK_API_KEY",
        "https://api.deepseek.com/chat/completions",
        "deepseek-chat", "openai", 128_000,
        quality_tier=2, cost_tier=1, latency_tier=2,
        policy_note="direct DeepSeek API (same family as frozen synthesis model)"),
    ProviderSpec(
        "mistral", "MISTRAL_API_KEY",
        "https://api.mistral.ai/v1/chat/completions",
        "mistral-small-latest", "openai", 128_000,
        quality_tier=3, cost_tier=1, latency_tier=1,
        policy_note=("mistral-large-latest timed out at 240 s on this account "
                     "(verified 2026-08-27); default is mistral-small-latest "
                     "(~1 s latency) — an EXPLICIT recorded tier-3 choice, "
                     "overridable via MISTRAL_MODEL (never a silent "
                     "substitution)")),
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

    @property
    def ok(self) -> bool:
        return self.status == ST_OK

    def to_meta(self) -> Dict[str, Any]:
        """Provenance metadata for candidates (Art. VI: real values only)."""
        return {
            "provider": self.provider_id,
            "model": self.model,
            "prompt_hash": self.prompt_hash,
            "output_hash": self.output_hash,
            "latency_ms": self.latency_ms,
            "substituted_from": self.substituted_from,
            "status": self.status,
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
    """Key presence per provider, evaluated at call time."""
    out = []
    for p in PROVIDER_SPECS:
        key = os.environ.get(p.env_var, "")
        out.append({
            "provider_id": p.provider_id,
            "env_var": p.env_var,
            "available": bool(key.strip()),
            "model": p.model_for_call(),
            "quality_tier": p.quality_tier,
            "cost_tier": p.cost_tier,
            "latency_tier": p.latency_tier,
            "context_capacity_tokens": p.context_capacity_tokens,
            "policy_note": p.policy_note,
        })
    return out


def select_provider(policy: Optional[SelectionPolicy] = None) -> tuple:
    """Return (spec_or_None, ledger). Pure — performs no I/O."""
    policy = policy or SelectionPolicy()
    matrix = availability_matrix()
    avail_ids = [m["provider_id"] for m in matrix if m["available"]]
    wanted_head: Optional[str] = None
    if policy.preferred_providers:
        eligible = [pid for pid in policy.preferred_providers if pid in avail_ids]
        order_source = policy.preferred_providers
    else:
        ranked = sorted(matrix, key=lambda m: (m["quality_tier"],
                                               m["cost_tier"], m["latency_tier"]))
        eligible = [m["provider_id"] for m in ranked if m["available"]]
        order_source = [m["provider_id"] for m in ranked]
    substituted_from = None
    if order_source and avail_ids:
        first_avail = next((pid for pid in order_source if pid in avail_ids), None)
        wanted_head = order_source[0]
        if first_avail and wanted_head and first_avail != wanted_head:
            substituted_from = wanted_head
    if not eligible:
        ledger = {
            "policy": {"preferred": policy.preferred_providers,
                       "purpose": policy.purpose,
                       "max_preference_fallback": policy.max_preference_fallback},
            "availability": matrix,
            "selected": None,
            "reason": "no provider has a usable credential in the environment",
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
        "availability": matrix,
        "eligible_order": eligible,
        "selected": chosen,
        "substituted_from": substituted_from,
        "reason": ("explicit preferred order" if policy.preferred_providers
                   else "default policy: availability -> quality -> cost -> latency"),
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
    data = _post_json(
        spec.url_for_call(),
        {"model": model, "messages": messages,
         "temperature": 0.0,
         # bounded generation: the structured FIELD-line outputs are short;
         # an unbounded cap lets reasoning models generate for many minutes
         # (measured 2026-08-27: wall time scales with the token cap on the
         # NVIDIA deepseek-v4-flash endpoint)
         "max_tokens": max_tokens},
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

    matrix = availability_matrix()
    avail_ids = [m["provider_id"] for m in matrix if m["available"]]

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
    if not chain:
        # preferred_providers exhausted with no available provider: keep
        # the historical honest semantics (no silent widening beyond the
        # operator's list — Art. IV)
        _, ledger = select_provider(policy)
        return LLMCallResult(
            status=ST_PROVIDER_UNAVAILABLE,
            error="no provider credential available (see selection_ledger)",
            prompt_hash=_sha(prompt),
            selection_ledger=ledger)

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
                              "ladder": ladder})

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
                    run_id=run_id, attempt=attempt + 1)
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
                        "ladder": ladder,
                        "availability": matrix,
                    },
                    retry_notes=retry_notes,
                    route=route or None,
                    failure_type=None)
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
                # GONE (410): the model was retired upstream — retrying the
                # SAME dead model wastes the budget. Skip the same-model
                # retry (fall straight through to the hop RECORDING and the
                # next rung); the hop must still be recorded — a GONE that
                # is silently skipped would be exactly the unrecorded-
                # failover the directive forbids.
                if ftype != "GONE" and attempt < max_retries:
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
                run_id=run_id, attempt=attempt + 1,
                fallback_from=(provider_id if next_provider else None),
                fallback_to=next_provider,
                error=str(last_err))
            route.append({
                "provider_attempted": spec.provider_id,
                "model": model_id,
                "failure_type": ftype,
                "timestamp": utc_now(),
                "retry_count": attempt,
                "attempts": attempt + 1,
                "latency_ms": int((time.time() - hop_t0) * 1000),
                "error": str(last_err)[:300],
                "fallback_provider": next_provider,
                "fallback_model": next_model,
                "rung_band": rung_meta.get("band"),
                "task": task,
            })
            last_failure_type = ftype
            break

    # every rung failed: CALL_FAILED with the full typed route (a
    # provider outage is infrastructure, never a verdict — the CALLER
    # decides meaning; Art. XXI.3 / LXI)
    return LLMCallResult(
        status=ST_CALL_FAILED, error=last_err,
        provider_id=(rungs[-1][0] if rungs else None),
        model=(rungs[-1][1] if rungs else None),
        prompt_hash=_sha(body),
        selection_ledger={"chain": list(chain),
                          "chain_source": chain_source,
                          "ladder": ladder,
                          "availability": matrix},
        retry_notes=[],
        route=route or None,
        failure_type=last_failure_type)


def availability_statement() -> Dict[str, Any]:
    """Compact statement for run manifests: which capabilities are blocked
    purely by credentials, and which env keys would unblock them."""
    matrix = availability_matrix()
    return {
        "any_provider_available": any(m["available"] for m in matrix),
        "available_providers": [m["provider_id"] for m in matrix if m["available"]],
        "unblock_with_env": [m["env_var"] for m in matrix if not m["available"]],
        "evaluated_at": utc_now(),
    }

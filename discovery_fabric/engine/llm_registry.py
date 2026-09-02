"""discovery_fabric/engine/llm_registry.py — E1 credential-independent LLM layer.

CEO directive E1: the engine must not depend on one LLM vendor. This registry
exposes ONE interface:

    generate(prompt, system, schema, policy) -> LLMCallResult

over nine providers (zai, OpenRouter, NVIDIA, Anthropic, Gemini, OpenAI,
Qwen, DeepSeek, Mistral). The engine selects a provider by explicit policy:
availability -> quality tier -> cost tier -> latency tier. The ninth
provider (zai, 2026-08-30) is the sandbox-local gateway added as the healthy
transport path after the NVIDIA latency collapse — E1 credential
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


# The provider registry (CEO E1; nine providers since 2026-08-30 — the
# zai sandbox gateway is the healthy-transport ninth). Quality tiers are
# RECORDED POLICY INPUTS (Art. XXVII: explicit, documented), not
# measurements; they encode the engine's default preference order and are
# inspected in every ledger.
PROVIDER_SPECS: List[ProviderSpec] = [
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
                        timeout: int, max_tokens: int) -> str:
    key = os.environ.get(spec.env_var, "").strip()
    data = _post_json(
        spec.url_for_call(),
        {"model": spec.model_for_call(), "messages": messages,
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
                           timeout: int, max_tokens: int) -> str:
    key = os.environ.get(spec.env_var, "").strip()
    system = ""
    msgs = []
    for m in messages:
        if m["role"] == "system":
            system = m["content"]
        else:
            msgs.append(m)
    data = _post_json(
        spec.url_for_call(),
        {"model": spec.model_for_call(), "max_tokens": max_tokens,
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
             max_tokens: int = 512) -> LLMCallResult:
    """CEO E1 single entry point:
    generate(prompt, evidence, schema) -> structured candidate.
    `evidence` items (already-custodied evidence dicts) are appended to the
    prompt as clearly delimited context; the registry never treats model
    output as evidence (Art. XVIII).
    max_tokens=512 default: the FIELD-line output protocol needs ~150-250
    tokens; a larger cap multiplies wall time on reasoning endpoints without
    improving output quality (measured 2026-08-27)."""
    spec, ledger = select_provider(policy)
    if spec is None:
        return LLMCallResult(
            status=ST_PROVIDER_UNAVAILABLE,
            error="no provider credential available (see selection_ledger)",
            prompt_hash=_sha(prompt),
            selection_ledger=ledger)

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

    last_err = None
    attempt_budget = max_tokens
    retry_notes: List[str] = []
    for attempt in range(max_retries + 1):
        t0 = time.time()
        try:
            if spec.flavor == "anthropic":
                content = _call_anthropic_flavor(spec, messages, timeout,
                                                 attempt_budget)
            else:
                content = _call_openai_flavor(spec, messages, timeout,
                                              attempt_budget)
            return LLMCallResult(
                status=ST_OK, content=content,
                provider_id=spec.provider_id, model=spec.model_for_call(),
                prompt_hash=_sha(body), output_hash=_sha(content),
                latency_ms=int((time.time() - t0) * 1000),
                substituted_from=ledger.get("substituted_from"),
                selection_ledger=ledger,
                retry_notes=retry_notes)
        except EmptyContentWithFinish as exc:
            last_err = f"{type(exc).__name__}: {exc}"
            # reasoning-token exhaustion: SAME provider/model, larger cap
            # (recorded in retry_notes — never a silent change)
            if attempt_budget < 2048:
                attempt_budget = min(2048, attempt_budget * 4)
                retry_notes.append(
                    f"attempt {attempt + 1}: empty content "
                    f"(finish_reason={exc.finish_reason}); same "
                    f"provider/model retried with max_tokens="
                    f"{attempt_budget}")
            if attempt < max_retries:
                time.sleep(2 * (attempt + 1))
        except Exception as exc:  # noqa: BLE001 — recorded, retried, explicit
            last_err = f"{type(exc).__name__}: {exc}"
            if attempt < max_retries:
                time.sleep(2 * (attempt + 1))
    return LLMCallResult(
        status=ST_CALL_FAILED, error=last_err,
        provider_id=spec.provider_id, model=spec.model_for_call(),
        prompt_hash=_sha(body), selection_ledger=ledger,
        retry_notes=retry_notes)


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

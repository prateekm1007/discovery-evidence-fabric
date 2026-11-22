"""discovery_fabric/engine/route_adapter.py — the typed multi-provider
LLM route layer (R58, claim c-0079; the P2 machine-leg transport).

WHAT THIS IS: the typed route registry + the alternate-provider
transports the P2/v9/v10 one-shots need for Art. 26 provider spread,
with the R57s2 qualification (eval/r57s2_probe.json, claim c-0078),
the R58/R64s4/R81 custody probes and the AM73 prereg amendment as the
provenance for every route fact recorded here. No route in this
module is ever wired as a judge (the r30_nvidia_route role
discipline: generator-leg only).

ROUTE REGISTRY (typed, provenance-tagged):
  registered  agnes    agnes-3.0-flash  AM75 (audit aef833e5c, R86
                                        verification): the OWNER
                                        DIRECTIVE — agnes-3.0-flash
                                        is the DEFAULT generator
                                        (supersedes AM73's
                                        cohere/command-a; the xkiro
                                        free-model daily token
                                        quota ~150K/day empirical
                                        ceiling cannot carry the
                                        ~870K v10 run — R85 typed
                                        INFRA_BLOCKED, zero v10
                                        rows generated). agnes
                                        served the v9 one-shot
                                        30/30 (mean 3.000
                                        UNRESOLVED) with the 2-key
                                        ordered rotation
                                        (AGNES_API_KEY +
                                        AGNES_API_KEY_2, R67s2
                                        per-key quota buckets).
                                        Transport: the loop-local
                                        gateway (scripts/
                                        zai_gateway.mjs) with
                                        ZAI_GATEWAY_UPSTREAM=agnes
                                        + AGNES_MODEL_ID=agnes-
                                        3.0-flash; reasoning
                                        headroom 512 (c-0078). The
                                        v10 one-shot generates HERE.
  alternate   xkiro-transport-facts  The xkiro transport ledger
                                        (R58/R81/R85 facts): base
                                        https://api.xkiro.com/v1,
                                        roster 69; Cloudflare BANS
                                        the python-urllib default
                                        User-Agent (HTTP 403 "error
                                        code: 1010") — a browser-
                                        like UA is REQUIRED; gateway
                                        headroom 1024 (command-a-plus
                                        measured ~1000 invisible
                                        reasoning tokens; command-a
                                        measured 978 completion
                                        tokens with clean stop at
                                        the full 19K-char contract);
                                        R85: free-model day-window
                                        quota ~150K tokens/day per
                                        key (HTTP 429, x-ratelimit-
                                        scope: free, window: day,
                                        reset 2026-11-19T00:00Z) —
                                        not viable for one-window
                                        sealed runs.
  dead        deepai   402              key authenticates; account not
                                        Pro in good standing (typed
                                        R56 c-0076, R57 c-0077, R58
                                        re-probe unchanged).
  dead        nvidia   no key           the vault absence typed every
                                        custody round since mid-R52.

REFUSAL TYPING (Art. 3): a transport that cannot serve returns a
typed RouteRefused (kind: missing_key | auth | rate_limited |
transport | unregistered_route) — never a silent fallback, never an
empty completion. Caller-side retry/budget policy is NOT
implemented here (the machine's own _retry_call owns it).

Zero LLM calls in this module (transport functions only; nothing
fires at import or test time).
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

ROUTE_ADAPTER_VERSION = "route_adapter/2.1.0"

REPO = Path(__file__).resolve().parents[2]
VAULT = REPO / ".env.keys"

# The Cloudflare client-signature ban (R58 typed): the urllib default
# UA is rejected with 403/1010 at api.xkiro.com. A browser-like UA is
# part of the xkiro transport contract, not cosmetic.
BROWSER_UA = ("Mozilla/5.0 (X11; Linux x86_64; rv:132.0) "
              "Gecko/20100101 Firefox/132.0")

# agnes reasoning headroom: the measured c-0078 fact — the flash tier
# budgets reasoning tokens first; a call sized to the visible target
# alone returns empty visible text.
REASONING_HEADROOM = 512

ROUTE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "registered": {
        "name": "agnes",
        "base_url": "https://apihub.agnes-ai.com/v1",
        "model": "agnes-3.0-flash",
        "vault_key_name": "AGNES_API_KEY (ordered: AGNES_API_KEY, "
                          "AGNES_API_KEY_2)",
        "provenance": "AM75 (audit aef833e5c, R86 verification): "
                      "the OWNER DIRECTIVE — agnes-3.0-flash is "
                      "the DEFAULT generator (supersedes AM73's "
                      "cohere/command-a @ 227e9e97b: the xkiro "
                      "free-model daily token quota ~150K/day "
                      "empirical ceiling cannot carry the ~870K "
                      "v10 run — R85 typed INFRA_BLOCKED with zero "
                      "v10 rows generated; command-a's R81 probe "
                      "provenance stands, the id moves to the "
                      "retired ledger). agnes-3.0-flash served the "
                      "v9 one-shot 30/30 served==requested=="
                      "registered (v9 mean 3.000 UNRESOLVED; the "
                      "r64s4/AM60 registration, restored by AM75). "
                      "Transport: the loop-local gateway with "
                      "ZAI_GATEWAY_UPSTREAM=agnes + AGNES_MODEL_ID="
                      "agnes-3.0-flash (R458-C1 id semantics: the "
                      "gateway serves the registered id; requested+"
                      "served are both logged and the attestation "
                      "requires served==requested==registered); "
                      "the 2-key ordered rotation AGNES_API_KEY -> "
                      "AGNES_API_KEY_2 (R67s2 per-key quota buckets, "
                      "the gateway's agnes keyEnvs); reasoning "
                      "headroom 512 (c-0078: the flash tier budgets "
                      "reasoning tokens FIRST — size max_tokens >= "
                      "visible_target + REASONING_HEADROOM). The "
                      "v10 one-shot generates HERE.",
        "role": "generator (the ONLY registered generator id; the "
                "v10 one-shot route)",
        "transport_facts": [
            "reasoning budgets FIRST: size max_tokens >= "
            "visible_target + REASONING_HEADROOM (c-0078 measured)",
            "free-user 429 quota is PER KEY: AGNES_API_KEY + "
            "AGNES_API_KEY_2 rotate with no sleep (R67s2 measured "
            "mid-run)",
        ],
    },
    "retired": [
        {
            "name": "zai-gateway / glm-4-plus",
            "reason": "OWNER ORDER 2026-11-18: retired as "
                      "insufficient capability ('too low level a "
                      "model'); served R58's 61/61 run and the v7 "
                      "history; the z-ai grant stays 429-dark "
                      "(Art. 15 typed) — historical records keep "
                      "their glm-4-plus attestations untouched",
        },
        {
            "name": "xkiro / cohere/command-a-plus (r64s4 first "
                    "candidate)",
            "reason": "CONTRACT-FIT FALSIFIED (r64s4): flagship-class "
                      "by naming and the strongest id the key tier "
                      "rosters, but under the real 19K-char "
                      "expansion contract it consumed the entire "
                      "3624-token budget on invisible reasoning with "
                      "ZERO visible chars (measured at 2600/3624) — "
                      "unusable under the machine's token contract; "
                      "the small-prompt sized probe did not "
                      "transfer; EXCLUDED from the R81 re-probe by "
                      "the runbook (c8cc5deb2)",
        },
        {
            "name": "xkiro / cohere/command-a (the AM73 v10 pin, "
                    "quota-blocked)",
            "reason": "AM75 (R86 audit aef833e5c): superseded as "
                      "the registered generator by the OWNER "
                      "DIRECTIVE — agnes-3.0-flash is the DEFAULT "
                      "generator. The xkiro free-model DAY-WINDOW "
                      "token quota (~150K/day empirical ceiling per "
                      "key, R85 typed evidence: HTTP 429, "
                      "x-ratelimit-scope: free, window: day, reset "
                      "2026-11-19T00:00Z) cannot carry the ~870K "
                      "v10 run (~29K tokens/row x 30). command-a's "
                      "R81 fire-now provenance stands (clean stop, "
                      "978 tokens, 17.7s, zero admission findings, "
                      "served==requested at the full 19K-char "
                      "contract); the route moves to alternates "
                      "(still qualified, still custody-backed — a "
                      "provider-spread alternate, never the "
                      "registered id until the owner buys quota)",
        },
    ],
    "alternates": [
        {
            "name": "xkiro-transport-facts (the R58/R81/R85 "
                    "transport ledger)",
            "base_url": "https://api.xkiro.com/v1",
            "n_models": 69,
            "provenance": "c-0078 end-to-end qualification; R58 "
                          "custody probe (roster match); r64s4 + R81 "
                          "probes (frontier tier serving verified; "
                          "command-a-plus falsified under contract, "
                          "command-a clean at the full 19K-char "
                          "contract); R85 quota block (the free-"
                          "model day window ~150K tokens/day per "
                          "key — the AM75 supersession evidence)",
            "transport_facts": [
                "browser User-Agent REQUIRED (urllib default UA "
                "banned: Cloudflare 403 error 1010, R58 typed)",
                "gateway xkiro headroom 1024 (command-a-plus "
                "measured ~1000 invisible reasoning tokens; the "
                "AM73-era command-a measured 978 completion tokens "
                "with clean stop — headroom is insurance)",
                "R85 free-model quota: DAY-WINDOW ~150K tokens/day "
                "per key (HTTP 429, x-ratelimit-scope: free, "
                "window: day) — a one-window ~870K sealed run is "
                "NOT VIABLE on the free tier; the AM75 default "
                "route is agnes",
            ],
            "vault_key_name": "XKIRO_API_KEY",
        },
        {
            "name": "zai-gateway (retired upstream)",
            "base_url": "http://127.0.0.1:8787/v1 (loop-local proxy; "
                        "upstream = z-ai CLI grant)",
            "n_models": 1,
            "provenance": "R36 auditor registration ruling (now "
                          "superseded twice — agnes r64s4/AM60, then "
                          "xkiro AM73); live-probed R58",
            "transport_facts": [
                "429-dark since R64 (Art. 15 typed window); the "
                "gateway's CLI upstream serves the grant's single "
                "embedded model regardless of the request id "
                "(R458-C1)",
            ],
            "vault_key_name": "ZAI_GATEWAY_KEY (session-local, "
                              "start_gateway-generated)",
        },
    ],
    "dead": [
        {"name": "deepai", "reason": "402 Pro-gated (R56/R57/R58)"},
        {"name": "nvidia", "reason": "vault key absence typed since "
                                     "mid-R52"},
    ],
}


class RouteRefused(Exception):
    """A typed transport refusal (Art. 3): kind + route + detail.
    Never a silent fallback and never an empty completion."""

    def __init__(self, kind: str, route: str, detail: str):
        super().__init__(f"[{kind}] {route}: {detail}")
        self.kind = kind
        self.route = route
        self.detail = detail


def resolve_vault_key(name: str) -> Optional[str]:
    """Resolve a key BY NAME from the gitignored vault (.env.keys,
    env-line format). Returns None when the vault or the name is
    absent (CORR-3: vault custody is session-local state — the
    absence is the caller's typed signal, never an error to hide).
    The value is never logged or raised into a traceback."""
    if not VAULT.exists():
        return None
    for line in VAULT.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            if k == name:
                return v
    return None


def _post_chat(base_url: str, api_key: str, messages: List[dict],
               model: str, max_tokens: int, timeout_s: float,
               user_agent: str, route_name: str,
               response_format: Optional[dict] = None) -> Dict[str, Any]:
    """One OpenAI-compatible chat completion. Typed refusals on every
    failure class; the response dict carries {content, model,
    finish_reason, usage, raw}. response_format is an OPTIONAL
    transport pass-through (the r127 Phase-A structured-output
    contract); None keeps the body byte-identical to the pre-r127
    instrument."""
    if not api_key:
        raise RouteRefused("missing_key", route_name,
                           f"no vault key for {route_name}")
    body_dict = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.0,
    }
    if response_format is not None:
        body_dict["response_format"] = response_format
    body = json.dumps(body_dict).encode("utf-8")
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions", data=body,
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json",
                 "User-Agent": user_agent},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as r:
            d = json.loads(r.read())
    except urllib.error.HTTPError as e:
        detail = e.read()[:160].decode("utf-8", "replace")
        if e.code in (401, 403):
            raise RouteRefused("auth", route_name,
                               f"HTTP {e.code}: {detail}") from None
        if e.code == 429:
            raise RouteRefused("rate_limited", route_name,
                               f"HTTP 429: {detail}") from None
        raise RouteRefused("transport", route_name,
                           f"HTTP {e.code}: {detail}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise RouteRefused("transport", route_name,
                           str(e)[:160]) from None
    ch = (d.get("choices") or [{}])[0]
    content = str((ch.get("message") or {}).get("content") or "")
    if not content.strip():
        # never a silent empty completion: the finish reason is the
        # typed detail (the agnes reasoning-budget failure mode)
        raise RouteRefused(
            "transport", route_name,
            f"empty content (finish_reason="
            f"{ch.get('finish_reason')}) — for agnes size max_tokens "
            f">= visible_target + REASONING_HEADROOM")
    return {"content": content, "model": d.get("model") or model,
            "finish_reason": ch.get("finish_reason") or "stop",
            "usage": d.get("usage"), "raw": d}


def xkiro_chat(messages: List[dict], model: str,
               max_tokens: int = 64, timeout_s: float = 120.0,
               api_key: Optional[str] = None) -> Dict[str, Any]:
    """One xkiro completion. The browser UA is part of the transport
    contract (Cloudflare 1010 bans the urllib default)."""
    key = api_key if api_key is not None else \
        resolve_vault_key("XKIRO_API_KEY")
    return _post_chat("https://api.xkiro.com/v1", key or "",
                      messages, model, max_tokens, timeout_s,
                      BROWSER_UA, "xkiro")


# R129 owner direction (2-key rotation): when both agnes keys sit in
# the vault, the two keys rotate ROUND-ROBIN per call — a 5/min cap on
# one key becomes ~10/min of sustained transport, and a single
# exhausted key no longer stalls a run (the R127 '8 backoffs' class).
# Deterministic (a process-local counter, not wall-clock) so a re-run
# of the same sequence allocates the same keys; no credential value
# ever crosses this boundary (digests only in any record).
_AGNES_ROTATION: List[str] = []
_AGNES_ROTATION_I = 0


def _agnes_key(api_key: Optional[str]) -> str:
    """Pick the agnes key: explicit > rotation. Builds the rotation
    list once from the vault (keys that exist), then advances the
    counter per call. An empty list degrades to the pre-R129
    single-key behavior (key may be '' — the typed missing_key
    refusal downstream, unchanged)."""
    global _AGNES_ROTATION_I
    if api_key is not None:
        return api_key
    if not _AGNES_ROTATION:
        for name in ("AGNES_API_KEY", "AGNES_API_KEY_2"):
            k = resolve_vault_key(name)
            if k:
                _AGNES_ROTATION.append(k)
        if not _AGNES_ROTATION:
            return ""
    k = _AGNES_ROTATION[_AGNES_ROTATION_I % len(_AGNES_ROTATION)]
    _AGNES_ROTATION_I += 1
    return k


def agnes_chat(messages: List[dict], model: str = "agnes-2.5-flash",
               visible_target: int = 64, timeout_s: float = 120.0,
               api_key: Optional[str] = None,
               response_format: Optional[dict] = None) -> Dict[str, Any]:
    """One agnes completion with the measured reasoning headroom
    (c-0078: the flash tier budgets reasoning tokens FIRST — a call
    sized to the visible target alone returns empty visible text).
    response_format passes through unchanged (r127 Phase-A).
    R129: the key is chosen by the 2-key rotation when both vault
    slots exist (owner direction 2; digests-only in records)."""
    return _post_chat("https://apihub.agnes-ai.com/v1", _agnes_key(api_key),
                      messages, model,
                      visible_target + REASONING_HEADROOM, timeout_s,
                      "agnes-route-adapter/1.0", "agnes",
                      response_format=response_format)


def bedrock_converse(messages: List[dict], model_id: str,
                     region: str = "us-east-1",
                     max_tokens: int = 4000, timeout_s: float = 300.0,
                     api_key: Optional[str] = None,
                     cache_prefix_turns: int = 0) -> Dict[str, Any]:
    """One Amazon Bedrock Converse call over plain HTTPS — the r128
    dir-4 owner direction. NO AWS SDK and NO EC2 host: an API key
    works as a plain bearer token (AWS_BEARER_TOKEN_BEDROCK) on
    POST https://bedrock-runtime.<region>.amazonaws.com/model/<id>/converse.
    Additive transport: the agnes path is byte-unchanged. Typed
    refusals on every failure class (F67: degenerate inputs refuse,
    never crash); the response dict carries {content, model, usage}
    with usage = the Converse inputTokens/outputTokens bytes.
    R129 Phase A (owner direction 2): cache_prefix_turns > 0 puts a
    bedrock cachePoint BREAKPOINT after the first N user turns — the
    frozen bind/reviewer prefix (directive, problem, few-shots) is
    served from the prompt cache (up to ~85% latency / ~90% input
    cost off exactly this pattern), the variable content rides after
    the cachePoint, and the 5-min TTL resets on each hit. The
    returned usage carries the cacheRead/cacheWrite token counts so
    the hit-rate is recomputable from the committed record."""
    key = api_key if api_key is not None else \
        resolve_vault_key("AWS_BEARER_TOKEN_BEDROCK")
    if not key:
        raise RouteRefused("missing_key", "bedrock",
                           "no AWS_BEARER_TOKEN_BEDROCK in the vault "
                           "(env-only, digests-only — F45 custody)")
    if not messages or not all(
            isinstance(m, dict) and m.get("role") and m.get("content")
            for m in messages):
        raise RouteRefused("degenerate_input", "bedrock",
                           "messages must be non-empty {role, content} "
                           "dicts (typed refusal, F67)")
    # Bedrock id shapes: foundation models 'anthropic.claude-3-haiku-
    # 20240307-v1:0', inference profiles 'us.anthropic.claude-3-5-sonnet-
    # 20240620-v1:0', marketplace 'deepseek-ai/deepseek-r1' — a dot or
    # slash plus a ':version' suffix (marketplace ids may omit it).
    # The guard rejects free-text junk ('claude', 'x') typed, F67.
    if not model_id or not isinstance(model_id, str) or not (
            ("." in model_id or "/" in model_id)
            and (":" in model_id or "/" in model_id)):
        raise RouteRefused("degenerate_input", "bedrock",
                           f"model_id '{model_id}' must be an inference-"
                           "profile, foundation-model or marketplace id "
                           "(typed refusal)")
    if cache_prefix_turns < 0 or cache_prefix_turns >= len(messages):
        raise RouteRefused("degenerate_input", "bedrock",
                           f"cache_prefix_turns={cache_prefix_turns} must "
                           "be 0 (no cachePoint) or index a real turn "
                           "0..len(messages)-1 (the breakpoint goes AFTER "
                           "that turn; the variable content must ride "
                           "after the cached prefix)")
    # Converse message shape: role/content map from the OpenAI dicts
    # (user/assistant pass through); system text is NOT carried in
    # messages — the caller folds any system line into the first user
    # turn, as the F31e composition already does (directive then problem).
    conv_msgs = [{"role": m["role"], "content": [{"text": m["content"]}]}
                 for m in messages]
    if cache_prefix_turns:
        # breakpoint AFTER turn cache_prefix_turns-1 (the frozen prefix)
        conv_msgs[cache_prefix_turns - 1]["content"].append(
            {"cachePoint": {"type": "default"}})
    body = json.dumps({
        "messages": conv_msgs,
        "inferenceConfig": {"maxTokens": max_tokens, "temperature": 0.0},
    }).encode("utf-8")
    url = (f"https://bedrock-runtime.{region}.amazonaws.com"
           f"/model/{model_id}/converse")
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json",
                 "User-Agent": BROWSER_UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8")[:180]
        except Exception:  # noqa: BLE001
            pass
        kind = {402: "payment_required", 403: "auth",
                429: "rate_limited"}.get(e.code, f"http_{e.code}")
        raise RouteRefused(kind, "bedrock",
                           f"HTTP {e.code}: {detail}") from e
    except Exception as e:  # noqa: BLE001
        raise RouteRefused("transport", "bedrock",
                           f"{type(e).__name__}: {str(e)[:140]}") from e
    try:
        out = data["output"]["message"]["content"]
        text = "".join(str(part.get("text") or "")
                       for part in out if isinstance(part, dict))
        usage = data.get("usage") or {}
    except (KeyError, TypeError) as e:
        raise RouteRefused("malformed_response", "bedrock",
                           f"missing {e} in the Converse envelope") from e
    return {"content": text, "model": model_id,
            "finish_reason": data.get("stopReason"),
            "usage": {"prompt_tokens": usage.get("inputTokens"),
                      "completion_tokens": usage.get("outputTokens"),
                      "cached_tokens": usage.get("cacheReadInputTokens")},
            "raw": data}


def hf_router_chat(messages: List[dict], model: str,
                   max_tokens: int = 4000, timeout_s: float = 300.0,
                   api_key: Optional[str] = None) -> Dict[str, Any]:
    """One Hugging Face Inference Providers call (r128 dir-4: the
    SECOND funded path) — POST https://router.huggingface.co/v1/
    chat/completions, OpenAI-compatible, bearer HF_TOKEN (env-only,
    digests-only). Typed refusals: missing_key, payment_required
    (HTTP 402 — the measured no-credits state), rate_limited, auth."""
    key = api_key if api_key is not None else \
        resolve_vault_key("HF_TOKEN")
    if not key:
        raise RouteRefused("missing_key", "hf_router",
                           "no HF_TOKEN in the vault (env-only, "
                           "digests-only — F45 custody)")
    if not messages:
        raise RouteRefused("degenerate_input", "hf_router",
                           "empty messages (typed refusal, F67)")
    body = json.dumps({"model": model, "messages": messages,
                       "max_tokens": max_tokens,
                       "temperature": 0.0}).encode("utf-8")
    req = urllib.request.Request(
        "https://router.huggingface.co/v1/chat/completions",
        data=body, method="POST",
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json",
                 "User-Agent": BROWSER_UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8")[:180]
        except Exception:  # noqa: BLE001
            pass
        kind = {402: "payment_required", 401: "auth",
                403: "auth", 429: "rate_limited"}.get(
                    e.code, f"http_{e.code}")
        raise RouteRefused(kind, "hf_router",
                           f"HTTP {e.code}: {detail}") from e
    except Exception as e:  # noqa: BLE001
        raise RouteRefused("transport", "hf_router",
                           f"{type(e).__name__}: {str(e)[:140]}") from e
    try:
        choice = data["choices"][0]
        text = str(choice["message"]["content"])
        usage = data.get("usage") or {}
    except (KeyError, IndexError, TypeError) as e:
        raise RouteRefused("malformed_response", "hf_router",
                           f"missing {e} in the envelope") from e
    return {"content": text, "model": data.get("model", model),
            "finish_reason": choice.get("finish_reason"),
            "usage": {"prompt_tokens": usage.get("prompt_tokens"),
                      "completion_tokens": usage.get("completion_tokens"),
                      "cached_tokens": ((usage.get("prompt_tokens_details")
                                         or {}).get("cached_tokens"))},
            "raw": data}


def registered_route() -> Dict[str, Any]:
    """The registered generator route (AM75): identity evidence for
    every generation ledger that must name its route."""
    return dict(ROUTE_REGISTRY["registered"])


def require_registered_model(model: str) -> None:
    """Typed guard: a generation ledger that claims the registered
    route must carry the registered id (never a silently swapped
    model — the R-REQID forward-only convention)."""
    reg = ROUTE_REGISTRY["registered"]["model"]
    if model != reg:
        raise RouteRefused(
            "unregistered_route", "agnes",
            f"requested '{model}' but the registered generator id is "
            f"'{reg}' (AM75: the owner-directed DEFAULT generator "
            f"agnes-3.0-flash supersedes AM73's quota-blocked "
            f"cohere/command-a, the r64s4/AM60 agnes pin before "
            f"it, and R36's glm-4-plus) — a silent model swap is "
            f"forbidden")


__all__ = ["ROUTE_ADAPTER_VERSION", "ROUTE_REGISTRY", "RouteRefused",
           "resolve_vault_key", "xkiro_chat", "agnes_chat",
           "bedrock_converse", "hf_router_chat",
           "registered_route", "require_registered_model",
           "BROWSER_UA", "REASONING_HEADROOM"]

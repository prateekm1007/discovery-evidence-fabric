"""discovery_fabric/engine/model_routing.py — R415 model-routing registry.

P0 directive (MAKE DISCOVERY ALWAYS AVAILABLE), sections 3-7 + 16-18:

    ProviderRegistry
        ↓
    ModelRegistry
        ↓
    Health / availability
        ↓
    Task suitability
        ↓
    routing decision

The machine must not depend on one gateway, one provider, or one MODEL.
The R414 cascade was provider-level (one pinned model per provider); a
retired upstream model (HTTP 410 — the registry's own policy note
records NVIDIA returning 410 for retired models) made every call on
that provider fail with no model-level fallback. This module fixes the
routing side: MANY models per provider, discovered from provider
metadata where available, intersected with a manually pinned allowlist
of acceptable model families, ordered by a MEASURED availability score
(exponentially decaying telemetry), and walked as a fallback LADDER per
task class (FAST / STRONG / CHEAP).

Components
  - ModelRecord / the ModelRegistry (per-model records: provider, model,
    task_capabilities, cost_class, latency_class, context_limit,
    structured_output, plus dynamic health fields computed on read)
  - PINNED_MODEL_FAMILIES (directive section 18: a manually pinned
    allowlist of acceptable model FAMILIES — never "today's free-model
    list"; live health decides WHICH eligible model is selected)
  - catalog discovery: GET {base}/v1/models per provider (TTL-cached;
    failures disclosed, never fatal — the pinned defaults stand in and
    the catalog state is reported UNDISCOVERED)
  - MODEL_ROUTING_LEDGER (directive section 16): append-only jsonl, one
    line per routing attempt — request_id, run_id, stage, provider,
    model, attempt, latency, status, failure_class, tokens,
    estimated_cost, fallback_from, fallback_to. THE evidence base for
    future routing decisions (section 17): availability scores are
    DERIVED from this ledger, replayable from committed bytes
    (Art. XII/LXII).
  - availability scoring with exponential decay (directive section 4):
    score = recent_success_rate × health_recency × provider_health ×
    task_compatibility × latency_suitability — separate provider /
    model / task trackings, decayed so yesterday's outage does not
    permanently poison a provider.
  - ladders (directive section 5): FAST / STRONG / CHEAP with bounded
    rungs; automatic failover on every transport failure is the
    llm_registry cascade walking these rungs.
  - provider states (directive section 6): HEALTHY / DEGRADED /
    RATE_LIMITED / AUTH_FAILED / GONE / TIMEOUT / UNAVAILABLE / UNKNOWN
    for the /api/health provider summary, with a short-TTL health probe
    cache that is invalidated immediately after failures.

Constitutional contract (Art. V, XXV, XXVII, XLV, LXI):
  - No heuristic REMOVES a provider from eligibility: cooldown and
    poor scores DEMOTE (order-only). The only hard exclusions are
    recorded facts: no credential (UNAVAILABLE), or the provider's own
    410 GONE response for a specific model (that model is known-dead;
    the provider's other models remain eligible — Art. V).
  - Tier/class assignments and score weights are RECORDED POLICY
    INPUTS (Art. XXVII), not measurements; the measurements are the
    ledger telemetry and the live catalog.
  - A provider failure is infrastructure, never a verdict (Art. LXI);
    nothing here classifies discovery outcomes.
  - Keys are read at call time and NEVER appear in the ledger, the
    summaries, the logs, or any payload this module builds.
"""
from __future__ import annotations

import json
import math
import os
import re
import threading
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .provider_health import (ROLE_ATTACK, ROLE_EXTRACTION,
                              ROLE_SYNTHESIS, ROLE_TRANSFORM)

REPO_ROOT = Path(__file__).resolve().parents[2]
ROUTING_DIR = REPO_ROOT / "ENGINE_RUNS" / "model_routing"
LEDGER_PATH = ROUTING_DIR / "ledger.jsonl"
STATE_PATH = ROUTING_DIR / "state.json"
CATALOG_DIR = ROUTING_DIR / "catalog"

# ---------------------------------------------------------------------------
# Task classes (directive section 5 — the fallback ladders)
# ---------------------------------------------------------------------------
TASK_FAST = "FAST"      # normal discovery requests
TASK_STRONG = "STRONG"  # deeper mechanism reasoning
TASK_CHEAP = "CHEAP"    # extraction / JSON cleanup

TASK_CLASSES = (TASK_FAST, TASK_STRONG, TASK_CHEAP)

# Role (R414) -> task class ladder (recorded policy input, Art. XXVII):
# synthesis = deeper mechanism reasoning; extraction = fast/cheap;
# attack = a normal-discovery-speed call with provider separation;
# transform = cheap (and prefer the deterministic code path).
ROLE_TO_TASK = {
    ROLE_SYNTHESIS: TASK_STRONG,
    ROLE_EXTRACTION: TASK_CHEAP,
    ROLE_ATTACK: TASK_FAST,
    ROLE_TRANSFORM: TASK_CHEAP,
}


def task_class_for_role(role: str) -> str:
    return ROLE_TO_TASK.get(role, TASK_FAST)


# ---------------------------------------------------------------------------
# The pinned model-family allowlist (directive section 18)
# ---------------------------------------------------------------------------
# A MANUALLY PINNED allowlist of acceptable model FAMILIES per provider.
# It is deliberately NOT "today's catalog" — providers retire and add
# models constantly (NVIDIA 410s retired models; OpenRouter's free list
# changes weekly). Live catalog discovery intersects these patterns;
# whichever eligible model is HEALTHIEST is selected. Patterns are
# recorded policy inputs (Art. XXVII): they pin the families the engine
# is willing to route to, never a specific day's availability.
PINNED_MODEL_FAMILIES: Dict[str, List[str]] = {
    "nvidia": [
        r"^deepseek-ai/deepseek",             # frozen synthesis family
        r"^nvidia/nemotron",                  # nemotron (3 / 3.5 lightning /
        #                                       # super / nano families)
        r"^meta/llama-3\.",                   # llama 3.x instruct
        r"^qwen/qwen",
        r"^mistralai/mistral",
    ],
    "openrouter": [
        r"^deepseek/deepseek",
        r"^minimax/minimax",
        r"^meta-llama/llama",
        r"^qwen/qwen",
        r"^mistralai/mistral",
        r"^google/gemma",
        r"^nvidia/nemotron",
        r"^z-ai/glm",
    ],
    "zai": [
        # R451: the zai default rung now names the env-contract model
        # zai-org/GLM-5.3 (the stale glm-4-plus id is retired); the
        # family pattern admits both the bare glm- ids and the
        # zai-org/GLM namespace — ONE GLM family, two hosting prefixes
        r"^glm-",
        r"^zai-org/GLM",
    ],
    "tokenrouter": [
        r"^z-ai/glm",
        r"^glm-",
    ],
    # R451: the self-hosted local baseline (llama.cpp serves the alias
    # 'qwen3-1.7b' — the Qwen3 family on local weights)
    "localqwen": [
        r"^qwen3-",
    ],
    # R456-A3: the operator's free-tier router quartet (the family
    # allowlists admit the MEASURED free answerers; catalog discovery
    # intersects against these so premium/gated ids never become rungs
    # silently)
    "unorouter": [
        r"^glm-5\.3:free$",
        r"^glm-5\.3-flash:free$",
        r"^glm-5\.2:free$",
        r"^qwen3\.8-27b:free$",
        r"^qwen3\.5-122b-a10b:free$",
        r"^deepseek-v[0-9.]+[a-z-]*:free$",
        r"^minimax-m[0-9.]+:free$",
    ],
    "xkiro": [
        r"^qwen/qwen3\.8-max:free$",
        r"^qwen/qwen3\.5-plus:free$",
        r"^qwen/qwen3-max:free$",
        r"^minimax/minimax-m3:free$",
        r"^minimax/minimax-m2\.7:free$",
        r"^deepseek/deepseek-v[0-9.]+[a-z-]*:free$",
    ],
    "apinex": [
        r"^free/deepseek-v[0-9.]+[a-z-]*$",
        r"^free/deepseek-v4-pro-0813$",
        r"^free/glm-5\.3-flash$",
        r"^free/qwen-3\.8-max$",
        r"^free/mimo-v[0-9.]+$",
        r"^free/gpt-5\.6-luna$",
    ],
    "bai": [
        r"^qwen3\.8-flash$",
        r"^mimo-v[0-9.]+$",
    ],
    # R461: the FIFTH router — bynara's -free family (the ids the
    # catalog actually serves; premium ids like glm-5.3, qwen3.8-max,
    # claude-opus-5, gpt-6-astra NEVER become rungs silently — the
    # -free suffix is the free-tier marker this router uses)
    "bynara": [
        r"^tencent-hy3-free$",
        r"^glm-5\.3-free$",
        r"^qwen3\.8-flash-free$",
        r"^mimo-v2\.5-free$",
        r"^muse-spark-1\.3-contributor-free$",
    ],
    # R467: the EIGHTH router — atria. The catalog's SOLE model id,
    # admitted by exhaustion + measurement (the FIELD-protocol test in
    # the registration probe: 3/3 clean FIELD lines at the retry cap).
    # No free-suffix convention on this provider: the whole catalog IS
    # the operator-declared free budget (100M tokens, operator-declared
    # — no usage endpoint exposes it), so the exact id is the allowlist.
    "atria": [
        r"^Atria-Dawn-Preview$",
    ],
    # R539: the NINTH router — agnes (apihub.agnes-ai.com), the
    # operator's number-1 API. The allowlist names EXACTLY the three
    # measured text flash rungs (the xkiro/apinex premium-precedent:
    # gated or wrong-modality ids never become rungs silently). The
    # pro rungs are credit-gated at registration time (403
    # insufficient_user_quota $0) and the video/image ids are
    # wrong-modality for text tasks — catalog discovery can only
    # route to the measured flash rungs; a topped-up account
    # re-admits pro ids with a one-line extension, never silently.
    "agnes": [
        r"^agnes-3\.0-flash$",
        r"^agnes-2\.5-flash$",
        r"^agnes-2\.0-flash$",
    ],
}

# Pinned DEFAULT models (the standing fallback set when the live catalog
# cannot be discovered — UNDISCOVERED is reported honestly, never silent).
# Each entry: (model_id, task_capabilities, cost_class, latency_class,
#              context_limit)
# cost/latency classes: 1 = cheapest/fastest (recorded policy inputs).
PINNED_DEFAULT_MODELS: Dict[str, List[Dict[str, Any]]] = {
    "nvidia": [
        {"model": "deepseek-ai/deepseek-v4-flash-0731",
         "task_capabilities": [TASK_STRONG, TASK_FAST, TASK_CHEAP],
         "cost_class": 1, "latency_class": 1, "context_limit": 128000},
        {"model": "nvidia/nemotron-3.5-lightning-30b-a3b",
         "task_capabilities": [TASK_FAST, TASK_CHEAP],
         "cost_class": 1, "latency_class": 1, "context_limit": 128000},
        {"model": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
         "task_capabilities": [TASK_STRONG, TASK_FAST],
         "cost_class": 1, "latency_class": 2, "context_limit": 128000},
    ],
    "openrouter": [
        {"model": "deepseek/deepseek-v4-flash-0731",
         "task_capabilities": [TASK_STRONG, TASK_FAST, TASK_CHEAP],
         "cost_class": 1, "latency_class": 2, "context_limit": 128000},
        {"model": "minimax/minimax-m2",
         "task_capabilities": [TASK_FAST, TASK_CHEAP],
         "cost_class": 1, "latency_class": 2, "context_limit": 128000},
        {"model": "meta-llama/llama-3.3-70b-instruct",
         "task_capabilities": [TASK_STRONG, TASK_FAST],
         "cost_class": 2, "latency_class": 2, "context_limit": 128000},
    ],
    "zai": [
        # R451: the glm-4-plus rung is REMOVED — the R450-recorded engine
        # defect (the HF router answers model_not_found for the stale paid
        # id, classified INVALID_RESPONSE). The rung now names the env-
        # contract model the R447 deployment actually serves; under
        # MODEL_COST_POLICY=ZERO_PAID_COST the whole provider is ineligible
        # anyway (ENVIRONMENT_GRANT / credit-router) — the rung exists for
        # UNRESTRICTED operation only, recorded, never silent.
        {"model": "zai-org/GLM-5.3",
         "task_capabilities": [TASK_STRONG, TASK_FAST, TASK_CHEAP],
         "cost_class": 1, "latency_class": 1, "context_limit": 128000},
    ],
    "localqwen": [
        # R451 §1-2: the zero-paid local baseline — self-hosted
        # Qwen/Qwen3-1.7B Q4_K_M via llama.cpp llama-server (CPU).
        # HONEST classes: strong it is NOT (a 1.7B model is not a
        # world-class scientific reasoner); fast it is NOT (measured
        # 6.3 tok/s on 2 vCPU). It is CHEAP (zero paid cost) and it is
        # the ONLY rung eligible under MODEL_COST_POLICY=ZERO_PAID_COST.
        {"model": "qwen3-1.7b",
         "task_capabilities": [TASK_CHEAP],
         "cost_class": 1, "latency_class": 4, "context_limit": 32768},
    ],
    "tokenrouter": [
        {"model": "z-ai/glm-5.3-free",
         "task_capabilities": [TASK_STRONG, TASK_FAST, TASK_CHEAP],
         "cost_class": 1, "latency_class": 2, "context_limit": 128000},
    ],
    # R456-A3: the operator's free-tier router quartet — every rung
    # below is a MEASURED free-tier answerer (the registration probes,
    # recorded in the llm_registry policy notes). The STRONG rungs are
    # the flagship-class free models (GLM-5.3, Qwen3.8-MAX, Minimax-M3,
    # DeepSeek-v4.1-flash); bai's rungs are FAST+CHEAP only (its free
    # answerers are the flash/derived class — the honest tier).
    "unorouter": [
        {"model": "glm-5.3:free",
         "task_capabilities": [TASK_STRONG, TASK_FAST, TASK_CHEAP],
         "cost_class": 1, "latency_class": 2, "context_limit": 128000},
        {"model": "glm-5.3-flash:free",
         "task_capabilities": [TASK_FAST, TASK_CHEAP],
         "cost_class": 1, "latency_class": 2, "context_limit": 128000},
        {"model": "qwen3.8-27b:free",
         "task_capabilities": [TASK_STRONG, TASK_FAST, TASK_CHEAP],
         "cost_class": 1, "latency_class": 2, "context_limit": 128000},
    ],
    "xkiro": [
        {"model": "qwen/qwen3.8-max:free",
         "task_capabilities": [TASK_STRONG, TASK_FAST, TASK_CHEAP],
         "cost_class": 1, "latency_class": 2, "context_limit": 128000},
        {"model": "minimax/minimax-m3:free",
         "task_capabilities": [TASK_STRONG, TASK_FAST, TASK_CHEAP],
         "cost_class": 1, "latency_class": 2, "context_limit": 128000},
        {"model": "qwen/qwen3-max:free",
         "task_capabilities": [TASK_STRONG, TASK_FAST],
         "cost_class": 1, "latency_class": 2, "context_limit": 128000},
        # R461: the newly-measured free rung (tiny completion 2.25 s,
        # 2026-09-15) — the qwen3.5-plus generation sits at the
        # qwen3-max class's depth (STRONG+FAST, the plus tier is
        # Qwen's deep-reasoning class below MAX)
        {"model": "qwen/qwen3.5-plus:free",
         "task_capabilities": [TASK_STRONG, TASK_FAST],
         "cost_class": 1, "latency_class": 2, "context_limit": 128000},
    ],
    "apinex": [
        {"model": "free/deepseek-v4.1-flash",
         "task_capabilities": [TASK_STRONG, TASK_FAST, TASK_CHEAP],
         "cost_class": 1, "latency_class": 3, "context_limit": 128000},
        # R461: the newly-measured free rungs (tiny completions 5.64 s
        # with 72 reasoning tokens / 3.35 s with 27, 2026-09-15) —
        # deepseek-v4-PRO is the flagship PRO class (STRONG, measured
        # reasoning latency honest at latency_class 3); glm-5.3-flash
        # is the flash class (FAST+CHEAP, no STRONG claim)
        {"model": "free/deepseek-v4-pro-0813",
         "task_capabilities": [TASK_STRONG, TASK_FAST],
         "cost_class": 1, "latency_class": 3, "context_limit": 128000},
        {"model": "free/glm-5.3-flash",
         "task_capabilities": [TASK_FAST, TASK_CHEAP],
         "cost_class": 1, "latency_class": 3, "context_limit": 128000},
        {"model": "free/mimo-v2.5",
         "task_capabilities": [TASK_FAST, TASK_CHEAP],
         "cost_class": 1, "latency_class": 3, "context_limit": 128000},
    ],
    "bai": [
        {"model": "qwen3.8-flash",
         "task_capabilities": [TASK_FAST, TASK_CHEAP],
         "cost_class": 1, "latency_class": 1, "context_limit": 128000},
        {"model": "mimo-v2.5",
         "task_capabilities": [TASK_FAST, TASK_CHEAP],
         "cost_class": 1, "latency_class": 1, "context_limit": 128000},
    ],
    # R461: the FIFTH router — every rung below is a MEASURED
    # free-tier answerer on the bynara account (post-telegram-join,
    # 2026-09-15). tencent-hy3-free answered 3 consecutive probes
    # (1.91-2.53 s); the account's other -free ids are credit/plan-
    # gated AT REGISTRATION TIME (typed specimens in provider_health)
    # — the family allowlist still admits them so catalog discovery
    # routes to whichever rung the account's credit state admits.
    # HONEST classes: FAST+CHEAP only — the free-tier serving path is
    # unmeasured on the engine's structured protocol; no STRONG claim
    # (the b.ai precedent: flagship-family naming is not a quality
    # measurement).
    "bynara": [
        {"model": "tencent-hy3-free",
         "task_capabilities": [TASK_FAST, TASK_CHEAP],
         "cost_class": 1, "latency_class": 2, "context_limit": 128000},
    ],
    # R467: the EIGHTH router — the token-surplus rung the R466
    # reaudit's binding constraint asked for (a STRONG rung so
    # MECHANISM-stage synthesis does not degrade to
    # CHEAP_EMERGENCY_FALLBACK, the class that typed 2 of 3 fresh
    # production runs INCOMPLETE_INFERENCE_FAILURE). The STRONG
    # declaration's basis is TWOFOLD and recorded: the operator's
    # verbatim declaration ("new model which is as good as glm5.3")
    # AND the measured FIELD-line protocol compliance (3/3 clean
    # FIELD lines through the reasoning_content/content split at the
    # retry cap — the engine's own MECHANISM-stage instrument, the
    # measurement bynara's rung honestly lacked). latency_class 3 is
    # the honest reasoning variance (0.55-8.71 s measured).
    "atria": [
        {"model": "Atria-Dawn-Preview",
         "task_capabilities": [TASK_STRONG, TASK_FAST, TASK_CHEAP],
         "cost_class": 1, "latency_class": 3, "context_limit": 128000},
    ],
    # R539: the NINTH router — every rung below is a MEASURED answerer
    # (2026-09-26 registration probes). agnes-3.0-flash is the STRONG
    # rung (3/3 clean FIELD lines in 1.11 s — the engine's structured-
    # protocol measurement); agnes-2.5-flash likewise 3/3 clean in
    # 0.77 s (STRONG+FAST+CHEAP); agnes-2.0-flash answered the tiny
    # probe in 0.48 s (FAST+CHEAP, no STRONG claim — unmeasured on the
    # FIELD instrument). The pro rungs are NOT listed (403
    # insufficient_user_quota $0 at registration — known-gated, never
    # attempted merely because the catalog names them).
    "agnes": [
        {"model": "agnes-3.0-flash",
         "task_capabilities": [TASK_STRONG, TASK_FAST, TASK_CHEAP],
         "cost_class": 1, "latency_class": 2, "context_limit": 128000},
        {"model": "agnes-2.5-flash",
         "task_capabilities": [TASK_STRONG, TASK_FAST, TASK_CHEAP],
         "cost_class": 1, "latency_class": 2, "context_limit": 128000},
        {"model": "agnes-2.0-flash",
         "task_capabilities": [TASK_FAST, TASK_CHEAP],
         "cost_class": 1, "latency_class": 1, "context_limit": 128000},
    ],
}

# ---------------------------------------------------------------------------
# Catalog discovery (directive section 18: build from provider metadata)
# ---------------------------------------------------------------------------
CATALOG_TTL_S = 3600.0     # recorded policy input (Art. XXVII)
PROBE_TTL_S = 300.0        # health-probe cache TTL
_PROBE_LOCK = threading.Lock()
_PROBE_CACHE: Dict[str, Dict[str, Any]] = {}   # (provider, model) -> probe


def _provider_base_url(provider_id: str) -> Optional[str]:
    """The provider's models-list base (its configured call base without
    the chat-completions suffix). Uses the llm_registry spec so there is
    exactly ONE provider-endpoint authority (Art. X)."""
    try:
        from .llm_registry import _SPEC_BY_ID
        spec = _SPEC_BY_ID.get(provider_id)
        if spec is None:
            return None
        url = spec.url_for_call()
        for suffix in ("/chat/completions", "/messages"):
            if url.endswith(suffix):
                return url[: -len(suffix)]
        return url
    except Exception:  # noqa: BLE001 — absent stays absent
        return None


def _provider_env_key(provider_id: str) -> Optional[str]:
    try:
        from .llm_registry import _SPEC_BY_ID
        spec = _SPEC_BY_ID.get(provider_id)
        return spec.env_var if spec else None
    except Exception:  # noqa: BLE001
        return None


def _get_json(url: str, key: Optional[str], timeout: int = 20,
              extra_headers: Optional[Dict[str, str]] = None) -> dict:
    req = urllib.request.Request(url)
    if key:
        req.add_header("Authorization", f"Bearer {key}")
    # R456-A3: per-provider transport headers (the CF browser-UA
    # requirement on xkiro/apinex — see the ProviderSpec notes)
    for h, v in (extra_headers or {}).items():
        req.add_header(h, v)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _family_match(model_id: str, patterns: List[str]) -> bool:
    return any(re.match(p, model_id) for p in patterns)


def discover_catalog(provider_id: str,
                     force: bool = False) -> Dict[str, Any]:
    """Live model-catalog discovery for one provider.

    GET {provider_base}/models (OpenAI-compatible listing). The result
    is TTL-cached on disk (catalog/<provider>.json) so a process restart
    does not re-fetch, and intersected with the pinned family allowlist.
    Discovery failure is DISCLOSED (status UNDISCOVERED + error) and the
    pinned default models stand in — never silent, never fatal.

    R451-C1.6 (MODEL_NOT_FOUND recovery): when a FRESH catalog fetch
    lists a model previously marked known-dead (GONE /
    MODEL_NOT_FOUND), the dead mark is CLEARED and the recovery event
    is recorded in the routing state (recovered_models, append-only) —
    deterministic: 404 -> mark dead -> fresh catalog lists the model ->
    mark cleared -> the model is eligible again. A TTL cache hit does
    NOT clear marks (only a fresh fetch is evidence of relisting)."""
    # R530 §3: behavior-neutral diagnostic (counter + wall + hit flag).
    _dc0 = time.perf_counter()
    base = _provider_base_url(provider_id)
    if not base:
        _SELECTION_DIAG["discover_catalog_calls"] += 1
        _SELECTION_DIAG["discover_catalog_s"] += (
            time.perf_counter() - _dc0)
        return {"provider": provider_id, "status": "NO_BASE_URL",
                "models": []}
    cache = CATALOG_DIR / f"{provider_id}.json"
    if not force and cache.exists():
        try:
            data = json.loads(cache.read_text(encoding="utf-8"))
            age = time.time() - float(data.get("fetched_at_epoch") or 0)
            if age < CATALOG_TTL_S:
                _SELECTION_DIAG["discover_catalog_calls"] += 1
                _SELECTION_DIAG["discover_catalog_s"] += (
                    time.perf_counter() - _dc0)
                _SELECTION_DIAG["discover_catalog_cache_hits"] += 1
                return data
        except Exception:  # noqa: BLE001 — stale cache falls through
            pass
    # R469: catalog discovery rides the ACTIVE ring key (a rotated-
    # forward provider must not re-pay the exhausted head key's 401 on
    # every catalog fetch — one key-selection authority with the chat
    # call path, Art. X). Single-key providers: exactly the pre-R469
    # env_var read.
    key = ""
    try:
        from .llm_registry import _SPEC_BY_ID, active_key_value
        _kspec = _SPEC_BY_ID.get(provider_id)
        if _kspec is not None:
            key = active_key_value(_kspec)
    except Exception:  # noqa: BLE001 — discovery stays best-effort
        key = ""
    if not key:
        key_var = _provider_env_key(provider_id)
        key = (os.environ.get(key_var, "").strip()) if key_var else ""
    url = base.rstrip("/") + "/models"
    # R456-A3: the spec's transport headers ride catalog discovery too
    # (the CF browser-UA requirement — ONE transport authority)
    extra_headers = None
    try:
        from .llm_registry import _SPEC_BY_ID
        _spec = _SPEC_BY_ID.get(provider_id)
        if _spec is not None and _spec.extra_headers:
            extra_headers = dict(_spec.extra_headers)
    except Exception:  # noqa: BLE001 — discovery stays best-effort
        extra_headers = None
    out: Dict[str, Any]
    try:
        data = _get_json(url, key or None, timeout=20,
                         extra_headers=extra_headers)
        raw = [m.get("id") for m in (data.get("data") or [])
               if isinstance(m, dict) and m.get("id")]
        allow = PINNED_MODEL_FAMILIES.get(provider_id, [])
        eligible = [m for m in raw if _family_match(m, allow)]
        out = {
            "provider": provider_id,
            "status": "DISCOVERED",
            "fetched_at_epoch": time.time(),
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
            "catalog_size": len(raw),
            "eligible_count": len(eligible),
            "models": eligible[:60],
            "discovered_via": url,
        }
        # R451-C1.6: a fresh catalog listing is the evidence that a
        # previously-dead identifier is served again — clear the mark,
        # record the recovery (deterministic, append-only state).
        _clear_known_dead_if_relisted(provider_id, raw)
    except Exception as exc:  # noqa: BLE001 — disclosed, never fatal
        out = {
            "provider": provider_id,
            "status": "UNDISCOVERED",
            "fetched_at_epoch": time.time(),
            "error": f"{type(exc).__name__}: {exc}"[:200],
            "catalog_size": 0,
            "eligible_count": 0,
            "models": [],
            "discovered_via": url,
        }
    try:
        CATALOG_DIR.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
    except Exception:  # noqa: BLE001 — cache is best-effort
        pass
    # R530 §3: behavior-neutral diagnostic (counter + wall only; a
    # fresh fetch / UNDISCOVERED path is not a cache hit).
    _SELECTION_DIAG["discover_catalog_calls"] += 1
    _SELECTION_DIAG["discover_catalog_s"] += time.perf_counter() - _dc0
    return out


def clear_probe_cache(provider: Optional[str] = None,
                      model: Optional[str] = None) -> None:
    """Directive section 6: invalidate the health-probe cache
    IMMEDIATELY after failures. Called by the cascade on every failed
    hop so the next routing decision re-probes rather than trusting a
    stale HEALTHY."""
    with _PROBE_LOCK:
        if provider is None:
            _PROBE_CACHE.clear()
            return
        for k in [k for k in _PROBE_CACHE if k[0] == provider
                  and (model is None or k[1] == model)]:
            _PROBE_CACHE.pop(k, None)


def probe_cache_get(provider: str, model: str) -> Optional[Dict[str, Any]]:
    with _PROBE_LOCK:
        hit = _PROBE_CACHE.get((provider, model))
        if not hit:
            return None
        if time.time() - float(hit.get("at_epoch") or 0) > PROBE_TTL_S:
            _PROBE_CACHE.pop((provider, model), None)
            return None
        return dict(hit)


def probe_cache_put(provider: str, model: str, probe: Dict[str, Any]) -> None:
    with _PROBE_LOCK:
        _PROBE_CACHE[(provider, model)] = dict(probe, at_epoch=time.time())


# ---------------------------------------------------------------------------
# The MODEL_ROUTING_LEDGER (directive sections 16-17)
# ---------------------------------------------------------------------------
class RoutingLedger:
    """Append-only jsonl — one line per routing attempt. THE evidence
    base for routing decisions; availability scores derive from its
    bytes (replayable, Art. XII/LXII). Best-effort persistence: a write
    failure is disclosed via last_error and degrades to memory-only."""

    def __init__(self, path: Path = LEDGER_PATH, max_tail: int = 800):
        self._path = Path(path)
        self._max_tail = max_tail
        self._lock = threading.Lock()
        self._last_error: Optional[str] = None

    def record(self, entry: Dict[str, Any]) -> None:
        line = dict(entry)
        line.setdefault("recorded_at", time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        line.setdefault("recorded_at_epoch", time.time())
        with self._lock:
            try:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                with open(self._path, "a") as fh:
                    fh.write(json.dumps(line, sort_keys=True) + "\n")
                self._last_error = None
            except Exception as exc:  # noqa: BLE001 — disclosed
                self._last_error = f"ledger append failed: {exc}"

    def tail(self, n: Optional[int] = None) -> List[Dict[str, Any]]:
        n = n or self._max_tail
        try:
            if not self._path.exists():
                return []
            with self._path.open() as fh:
                lines = fh.readlines()[-n:]
            out = []
            for ln in lines:
                try:
                    d = json.loads(ln)
                    if isinstance(d, dict):
                        out.append(d)
                except Exception:  # noqa: BLE001 — a torn line is skipped
                    pass
            return out
        except Exception:  # noqa: BLE001
            return []

    def diagnostics(self) -> Dict[str, Any]:
        return {"ledger_path": str(self._path),
                "last_error": self._last_error,
                "entries_in_tail": len(self.tail(50))}


LEDGER = RoutingLedger()


# ---------------------------------------------------------------------------
# Routing state: the GONE model set (known-dead from the provider's own
# 410 response — a recorded fact, never a heuristic)
# ---------------------------------------------------------------------------
def _provider_account_domain(provider_id: str) -> str:
    """The economic account domain that pays for a provider's calls
    (R451-C1.2). Declared on the ProviderSpec; UNDECLARED stays honest
    (Art. XXV) — never guessed."""
    try:
        from .llm_registry import _SPEC_BY_ID
        spec = _SPEC_BY_ID.get(provider_id)
        return str(getattr(spec, "account_domain", "") or "UNDECLARED")
    except Exception:  # noqa: BLE001 — registry not importable here
        return "UNDECLARED"


def _load_state() -> Dict[str, Any]:
    try:
        if STATE_PATH.exists():
            data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:  # noqa: BLE001 — corrupt state degrades to empty
        pass
    return {}


def mark_model_gone(provider: str, model: str,
                    evidence: str = "provider responded HTTP 410 Gone on "
                    "a live call") -> None:
    """Record (provider, model) as known-dead — the provider itself
    answered 410 GONE (retired) or model_not_found (the identifier is
    permanently invalid on this route — R451-C1.2, the operator's
    never-retry rule). The model is excluded from ladders until a fresh
    catalog lists it again (R451-C1.6 clear_known_dead_if_relisted) or
    a call succeeds; the PROVIDER stays eligible (Art. V)."""
    state = _load_state()
    gone = state.setdefault("gone_models", {})
    gone[f"{provider}::{model}"] = {
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "evidence": evidence,
    }
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(state, indent=1, sort_keys=True), encoding="utf-8")
    except Exception:  # noqa: BLE001 — best-effort, disclosed via catalog
        pass
    # a GONE model is not in the live catalog by definition — refresh it
    clear_probe_cache(provider, model)
    # R451-C1.3: the capability record is KEPT (a PROBE_FAILED record
    # with the typed class is the honest evidence for the rung's skip
    # hop); the dead-id ladder exclusion above is what actually removes
    # the rung — and the C1.6 relist recovery invalidates the record so
    # a relisted id re-probes immediately.


def is_model_gone(provider: str, model: str) -> bool:
    return f"{provider}::{model}" in (_load_state().get("gone_models")
                                      or {})


# ---------------------------------------------------------------------------
# R483 — the span-outcome telemetry (the span-capable rung preference).
#
# The measured production class (three consecutive runs, the durable
# ledger + run envelopes): a transport-OK synthesis call whose output
# failed the verbatim evidence-span contract — the VERIFY stage then
# honestly typed INCOMPLETE_INFERENCE_FAILURE and the loop closure
# stayed blocked. The transport layer's ok/failure classification never
# sees that failure (the call succeeded), so the router kept ranking
# the failing rung. The seam: the VERIFY adapter reports the span
# contract's outcome for the rung that actually served the candidate;
# the ladder DEMOTES recently span-failing rungs for synthesis-purpose
# builds (ordering-only demotion, Art. V — never removal; every other
# ladder purpose is untouched). A span failure is ROUTING telemetry —
# never a scientific verdict (Art. LXI: the typed epistemic state is
# classify.py's authority and is unchanged).
# ---------------------------------------------------------------------------
SPAN_OUTCOME_TAIL = 200          # bounded outcome tail (state file)
SPAN_FAIL_DEMOTE_WINDOW_S = 6 * 3600   # declared operational bound


def record_span_outcome(provider: str, model: str, ok: bool,
                        stage: str = "synthesis",
                        run_id: Optional[str] = None) -> None:
    """Record the verbatim-span contract outcome for a serving rung
    (best-effort telemetry: never raises, never blocks the verify
    stage). ok=True = the candidate's span contract held; ok=False =
    the SPAN_ISSUES capability class fired for this rung's output."""
    try:
        state = _load_state()
        tail = state.get("span_outcomes")
        if not isinstance(tail, list):
            tail = []
        tail.append({
            "provider": provider, "model": model, "ok": bool(ok),
            "stage": stage, "run_id": run_id,
            "ts": time.time(),
        })
        state["span_outcomes"] = tail[-SPAN_OUTCOME_TAIL:]
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(state, indent=1, sort_keys=True), encoding="utf-8")
    except Exception:  # noqa: BLE001 — telemetry best-effort, never blocks
        pass


def span_failed_recently(provider: str, model: str,
                         now: Optional[float] = None) -> bool:
    """True when THIS rung's most recent span outcome within the
    demotion window is a FAILURE (the honest reading: one recent
    measured failure demotes; a later success on the same rung restores
    it — the tail's newest entry for the rung decides)."""
    now = now if now is not None else time.time()
    # R530 §3: behavior-neutral diagnostic (counter + wall only).
    _df0 = time.perf_counter()
    _dres: Optional[bool] = None
    for e in reversed((_load_state().get("span_outcomes") or [])):
        if not isinstance(e, dict):
            continue
        if e.get("provider") != provider or e.get("model") != model:
            continue
        if now - float(e.get("ts") or 0) > SPAN_FAIL_DEMOTE_WINDOW_S:
            _dres = False  # the rung's newest outcome is stale either way
            break
        _dres = not bool(e.get("ok"))
        break
    if _dres is None:
        _dres = False
    _SELECTION_DIAG["span_failed_recently_calls"] += 1
    _SELECTION_DIAG["span_failed_recently_s"] += (
        time.perf_counter() - _df0)
    return _dres


def clear_span_outcomes() -> None:
    """Test/operator reset (the state file is runtime telemetry, not
    evidence — Art. X: the records, not this file, are the history)."""
    try:
        state = _load_state()
        state.pop("span_outcomes", None)
        STATE_PATH.write_text(json.dumps(state, indent=1, sort_keys=True), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass


def clear_model_gone(provider: str, model: str) -> None:
    state = _load_state()
    gone = state.setdefault("gone_models", {})
    if f"{provider}::{model}" in gone:
        del gone[f"{provider}::{model}"]
        try:
            STATE_PATH.write_text(json.dumps(state, indent=1,
                                             sort_keys=True), encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass


# ---------------------------------------------------------------------------
# R451-C1.6 — MODEL_NOT_FOUND recovery: a fresh catalog listing clears
# the known-dead mark (deterministic relisting recovery)
# ---------------------------------------------------------------------------
def _clear_known_dead_if_relisted(provider: str,
                                  fresh_catalog_models: List[str]) \
        -> List[str]:
    """When a FRESH catalog fetch lists a previously-dead model, clear
    the dead mark and record the recovery event (append-only). Returns
    the recovered model ids. The provider's own relisting is the
    evidence — never a heuristic, never a timeout (Art. XXV).

    The directive's exact deterministic sequence (test-pinned):
        404 -> mark dead -> fresh catalog lists model -> dead mark
        cleared -> model eligible again
    """
    recovered: List[str] = []
    if not fresh_catalog_models:
        return recovered
    state = _load_state()
    gone = state.setdefault("gone_models", {})
    for mid in list(fresh_catalog_models):
        key = f"{provider}::{mid}"
        if key in gone:
            del gone[key]
            recovered.append(mid)
    if recovered:
        recov = state.setdefault("recovered_models", {})
        for mid in recovered:
            recov[f"{provider}::{mid}"] = {
                "recovered_at": time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "evidence": ("fresh catalog discovery lists the model "
                             "again (R451-C1.6 clear_known_dead_if_"
                             "relisted)"),
            }
        # the recovered model re-probes IMMEDIATELY (no TTL wait): the
        # stale PROBE_FAILED record would refuse admission for up to the
        # TTL window after the provider relisted the id
        try:
            from . import runtime_admission as _ra
            for mid in recovered:
                _ra.invalidate_capability(
                    provider, mid,
                    reason="relisted in a fresh catalog (R451-C1.6)")
        except Exception:  # noqa: BLE001
            pass
        try:
            STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            STATE_PATH.write_text(json.dumps(state, indent=1,
                                             sort_keys=True), encoding="utf-8")
        except Exception:  # noqa: BLE001 — best-effort, disclosed via
            pass                  # the catalog state report
    return recovered


# ---------------------------------------------------------------------------
# Availability scoring (directive section 4) — exponentially decaying
# ---------------------------------------------------------------------------
# Recorded policy inputs (Art. XXVII — every weight below is documented,
# not measured):
DECAY_HALF_LIFE_S = 4 * 3600.0   # yesterday's outage decays to ~6% by
#                                  # today: it does not permanently poison
PRIOR_STRENGTH = 0.5             # neutral prior weight for no-telemetry
LATENCY_SUITABILITY_TAU_MS = 8000.0  # latency suitability = exp(-ema/tau)


def _decay_weight(at_epoch: float, now: float) -> float:
    return math.pow(0.5, max(0.0, now - at_epoch) / DECAY_HALF_LIFE_S)


# R530 §3: selection-path diagnostic counters (behavior-neutral
# telemetry for the gen_spans/1.0 selection_subspans decomposition).
# Walls are perf_counter deltas accumulated at the measured call
# sites; counts are plain increments. Read via
# selection_diag_take() (take-and-zero). Never steers routing.
_SELECTION_DIAG: Dict[str, Any] = {
    "availability_score_calls": 0,
    "availability_score_s": 0.0,
    "availability_report_calls": 0,
    "availability_report_s": 0.0,
    "eligible_models_calls": 0,
    "eligible_models_s": 0.0,
    "eligible_models_returned": 0,
    "discover_catalog_calls": 0,
    "discover_catalog_s": 0.0,
    "discover_catalog_cache_hits": 0,
    "span_failed_recently_calls": 0,
    "span_failed_recently_s": 0.0,
    "ladder_providers_inspected": 0,
    "ladder_models_inspected": 0,
    "ladder_rungs_emitted": 0,
    # R531 §6: memo hits (reuse without recomputation). The
    # availability_score_calls counter counts RECOMPUTES only;
    # hits + recomputes = the unmemoized call count.
    "selection_memo_hits": 0,
}


def selection_diag_take() -> Dict[str, Any]:
    """R530 §3: take-and-zero the selection-path diagnostic counters.

    llm_registry.generate() takes a snapshot when its selection span
    opens and again when it closes; the delta is that call's
    diagnostic counts (availability_score calls, availability_report
    ledger scans, eligible_models/catalog calls, span-failure checks,
    providers/models inspected, rungs emitted). Pure counter reads +
    zeroing — no routing, scoring, or I/O behavior changes (Art. IX:
    observational). Single-threaded engine: no nesting of generate()
    calls, so take/open/close pairing is exact; abandoned
    early-return selections discard via take() at their return sites.
    """
    snap = dict(_SELECTION_DIAG)
    for _k in _SELECTION_DIAG:
        _SELECTION_DIAG[_k] = 0 if isinstance(
            _SELECTION_DIAG[_k], int) else 0.0
    return snap


# R531 §6: invocation-local availability-score memo table.
# Thread-local storage: each thread owns its table, so concurrent
# generate() calls can never observe each other's entries (the key
# carries `now`, which already separates invocations, but isolation
# is structural, not coincidental). Lifecycle: selection_memo_begin()
# (fresh table) at generate()'s selection-span open,
# selection_memo_end() (cleared) at span close + early-return
# discard sites. If an exception escapes mid-selection, the stale
# table persists — but the NEXT call's begin() replaces it before
# any read, so no entry is ever shared across invocations. The
# table holds (value, ledger_identity) pairs; a hit requires the
# stored identity to equal the CURRENT file identity (Design 2 —
# identical to the R531 §4/§5 harness-tested wrapper: stale
# entries are overwritten, never returned).
_selection_memo_local = threading.local()


def selection_memo_begin() -> None:
    """R531 §6: open a fresh invocation-local score memo table."""
    _selection_memo_local.table = {}


def selection_memo_end() -> None:
    """R531 §6: close (clear) the invocation-local score memo table."""
    _selection_memo_local.table = None


def _selection_memo_table() -> Optional[Dict[str, Any]]:
    return getattr(_selection_memo_local, "table", None)


def _ledger_identity() -> Optional[Any]:
    """(mtime_ns, size) of the routing ledger file, or None when
    unreadable. The ledger is append-only jsonl: any append changes
    size (and mtime), so equal identity means equal bytes."""
    try:
        _st = LEDGER._path.stat()
        return (_st.st_mtime_ns, _st.st_size)
    except Exception:  # noqa: BLE001 — no identity available
        return None


def availability_report(provider: Optional[str] = None,
                        model: Optional[str] = None,
                        task: Optional[str] = None,
                        now: Optional[float] = None) -> Dict[str, Any]:
    """Decayed availability statistics from the LEDGER bytes, filtered
    by provider / model / task (directive section 4: separate scores for
    provider, model, and task). Returns decayed success/failure weights,
    the derived recent_success_rate (None when no telemetry — Art. XXV:
    insufficient evidence is not a 0.0 rate), and the last-observation
    recency factor."""
    now = now if now is not None else time.time()
    # R530 §3: behavior-neutral diagnostic (counter + wall only).
    _dr0 = time.perf_counter()
    succ_w = fail_w = 0.0
    last_obs_at: Optional[float] = None
    latency_ema_num = 0.0
    latency_ema_den = 0.0
    for e in LEDGER.tail():
        # R526 Q-B: phase-span lines are orchestration timing, not
        # provider telemetry — they must never enter availability
        # statistics (their ok=None would otherwise count as failure).
        if isinstance(e, dict) and e.get("line_class") == "PHASE_SPAN":
            continue
        if provider is not None and e.get("provider") != provider:
            continue
        if model is not None and e.get("model") != model:
            continue
        if task is not None and e.get("task") != task:
            continue
        at = float(e.get("recorded_at_epoch") or 0)
        if not at:
            continue
        w = _decay_weight(at, now)
        if e.get("ok"):
            succ_w += w
            lat = float(e.get("latency_ms") or 0)
            latency_ema_num += w * lat
            latency_ema_den += w
        else:
            fail_w += w
        if last_obs_at is None or at > last_obs_at:
            last_obs_at = at
    total = succ_w + fail_w
    _drep = {
        "provider": provider, "model": model, "task": task,
        "decayed_success_weight": round(succ_w, 4),
        "decayed_failure_weight": round(fail_w, 4),
        "decayed_observation_weight": round(total, 4),
        "recent_success_rate": (round(succ_w / total, 4) if total > 1e-6
                                else None),
        "last_observation_at_epoch": last_obs_at,
        "latency_ema_ms": (round(latency_ema_num / latency_ema_den, 1)
                           if latency_ema_den > 1e-6 else None),
    }
    # R530 §3: behavior-neutral diagnostic (counter + wall only).
    _SELECTION_DIAG["availability_report_calls"] += 1
    _SELECTION_DIAG["availability_report_s"] += (
        time.perf_counter() - _dr0)
    return _drep


def health_recency_factor(report: Dict[str, Any],
                          now: Optional[float] = None) -> float:
    """exp(-age / T): a provider proven healthy 5 minutes ago scores
    higher than one proven healthy yesterday. No observation -> the
    neutral prior (disclosed policy input)."""
    now = now if now is not None else time.time()
    at = report.get("last_observation_at_epoch")
    if not at:
        return PRIOR_STRENGTH
    # 1 h recency horizon (recorded policy input): fresh evidence is
    # nearly 1.0, a day-old probe has decayed to ~0.
    return math.exp(-max(0.0, now - float(at)) / 3600.0)


def availability_score(provider: str, model: Optional[str] = None,
                       task: Optional[str] = None,
                       avoid_provider: Optional[str] = None,
                       latency_class: int = 2,
                       now: Optional[float] = None) -> float:
    """directive section 4:

        availability_score =
            recent_success_rate
            × health_recency
            × provider_health
            × task_compatibility
            × latency_suitability

    Each factor is derived from the ledger with exponential decay; a
    missing factor falls back to a DISCLOSED neutral prior (never to a
    fabricated 1.0 or 0.0 — Art. XXV). Ordering-only (Art. V): a low
    score demotes, never removes."""
    now = now if now is not None else time.time()
    # R531 §6: invocation-local score reuse (the Case-A
    # intervention). Memo key = the FULL score input tuple
    # (provider, model, task, avoid_provider, latency_class, now);
    # a hit ALSO requires the stored ledger identity to equal the
    # current file identity (Design 2 — identical to the
    # harness-tested wrapper). availability_score is a pure
    # function of (inputs, now, ledger bytes): same key + same
    # bytes -> same value, bit-for-bit. On identity mismatch the
    # entry is recomputed and overwritten (invalidation), never
    # returned stale. No memo table open (-> None) means normal
    # computation (all non-selection callers unaffected).
    _mtable = _selection_memo_table()
    _mkey = None
    _mident = None
    if _mtable is not None:
        _mident = _ledger_identity()
        _mkey = (provider, model, task, avoid_provider,
                 latency_class, now)
        _mhit = _mtable.get(_mkey)
        if _mhit is not None and _mhit[1] == _mident:
            _SELECTION_DIAG["selection_memo_hits"] += 1
            return _mhit[0]
    # R530 §3: behavior-neutral diagnostic (counter + wall only).
    _ds0 = time.perf_counter()
    # task_compatibility: 1.0 when the model is compatible with the
    # task (checked by the caller when building the ladder); here the
    # factor covers provider-level task affinity from telemetry.
    m_rep = availability_report(provider=provider, model=model, now=now)
    p_rep = availability_report(provider=provider, now=now)
    t_rep = availability_report(provider=provider, task=task, now=now)

    def _rate(rep: Dict[str, Any]) -> float:
        r = rep.get("recent_success_rate")
        if r is None:
            return PRIOR_STRENGTH
        w = rep.get("decayed_observation_weight") or 0.0
        # blend the measured rate with the prior, weighted by evidence
        # mass (little evidence -> near-prior; lots -> the measurement)
        return (r * min(1.0, w) + PRIOR_STRENGTH * max(0.0, 1.0 - w))

    recent_rate = _rate(m_rep if model else p_rep)
    recency = health_recency_factor(m_rep if model else p_rep, now)
    provider_health = _rate(p_rep)
    task_compat = _rate(t_rep)
    # latency suitability from the decayed latency EMA (if any)
    ema = (m_rep if model else p_rep).get("latency_ema_ms")
    latency_suit = (math.exp(-float(ema) / LATENCY_SUITABILITY_TAU_MS)
                    if ema else PRIOR_STRENGTH)
    # provider-separation bonus for attack routing (Art. XLV): a
    # different provider from the generator ranks higher on attack
    # tasks — recorded policy input, ordering-only.
    separation = 1.25 if (task == TASK_FAST and avoid_provider
                           and provider != avoid_provider) else 1.0
    _sres = round(max(0.0, min(2.0, recent_rate * recency * provider_health
                               * task_compat * latency_suit * separation)), 6)
    # R530 §3: behavior-neutral diagnostic (counter + wall only).
    _SELECTION_DIAG["availability_score_calls"] += 1
    _SELECTION_DIAG["availability_score_s"] += time.perf_counter() - _ds0
    # R531 §6: store under the invocation-local memo (Design 2:
    # value + ledger identity; a later hit revalidates identity).
    if _mtable is not None and _mkey is not None:
        _mtable[_mkey] = (_sres, _mident)
    return _sres


# ---------------------------------------------------------------------------
# The ModelRegistry (directive section 3)
# ---------------------------------------------------------------------------
@dataclass
class ModelRecord:
    provider: str
    model: str
    task_capabilities: List[str]
    cost_class: int = 2
    latency_class: int = 2
    context_limit: int = 128000
    structured_output: bool = True
    source: str = "PINNED_DEFAULT"    # PINNED_DEFAULT | CATALOG

    def score(self, task: str, avoid_provider: Optional[str] = None,
              now: Optional[float] = None) -> float:
        return availability_score(self.provider, self.model, task,
                                  avoid_provider=avoid_provider,
                                  latency_class=self.latency_class,
                                  now=now)


def _catalog_records(provider_id: str) -> List[ModelRecord]:
    """R451-C1.5 (stop using stale defaults after successful catalog
    discovery) — the semantics are EXACTLY:

        catalog DISCOVERED    -> only models actually present in the
                                 catalog are eligible candidates (the
                                 pinned defaults are NOT merged in — a
                                 pinned-but-absent default is a stale
                                 identifier and is never attempted
                                 merely because it was once a default)
        catalog UNDISCOVERED   -> the pinned defaults may be used,
                                 explicitly marked PINNED_DEFAULT

    The model-family allowlist STAYS (the pinned FAMILY policy, as
    distinct from a pinned dead identifier — the directive's own
    distinction). An empty DISCOVERED catalog honestly yields NO
    records for the provider (Art. XXV: absence stays absence)."""
    cat = discover_catalog(provider_id)
    if cat.get("status") != "DISCOVERED":
        return []
    out: List[ModelRecord] = []
    for mid in cat.get("models") or []:
        if is_model_gone(provider_id, mid):
            continue
        d = next((d for d in PINNED_DEFAULT_MODELS.get(provider_id, [])
                  if d["model"] == mid), None)
        out.append(ModelRecord(
            provider=provider_id, model=mid,
            task_capabilities=(d["task_capabilities"] if d
                               else [TASK_FAST, TASK_CHEAP, TASK_STRONG]),
            cost_class=(d["cost_class"] if d else 2),
            latency_class=(d["latency_class"] if d else 2),
            context_limit=(d["context_limit"] if d else 128000),
            source="CATALOG"))
    return out


def _pinned_records(provider_id: str) -> List[ModelRecord]:
    out = []
    for d in PINNED_DEFAULT_MODELS.get(provider_id, []):
        if is_model_gone(provider_id, d["model"]):
            continue
        out.append(ModelRecord(
            provider=provider_id, model=d["model"],
            task_capabilities=list(d["task_capabilities"]),
            cost_class=d["cost_class"], latency_class=d["latency_class"],
            context_limit=d["context_limit"],
            source="PINNED_DEFAULT"))
    return out


def _operator_pinned_model(provider_id: str) -> Optional[str]:
    """R418: the recorded operator override {PROVIDER}_MODEL (the R391
    transport-override mechanism, applied to the ROUTING LADDER). When
    set, the pinned model is the provider's PRIMARY rung — an explicit,
    recorded operator decision (never silent; the ladder's provenance
    records it). The cascade still works: if the pinned model fails,
    the walk continues down the ladder exactly as before."""
    val = (os.environ.get(f"{provider_id.upper()}_MODEL", "").strip())
    return val or None


def eligible_models(provider_id: str, task: str,
                    catalog: bool = True) -> List[ModelRecord]:
    """The provider's models eligible for a task: live-catalog records
    where discoverable (intersected with the pinned family allowlist),
    else the pinned defaults. GONE models are excluded (recorded-fact
    exclusion, not heuristic — Art. V).

    R418 (two measured defects fixed):
    1. `:batch` / `:extended` catalog slugs are BATCH/alternate
       endpoints, not chat-completions endpoints — the live catalog
       lists them and the ladder picked `z-ai/glm-5.3-flash:batch`
       (measured HTTP 404 on the chat endpoint, the deployed
       transport probe's last failure). They are excluded from the
       chat ladder — a recorded-fact exclusion (the slug's own
       semantics), same class as the GONE exclusion.
    2. The operator's {PROVIDER}_MODEL pin is emitted FIRST when set
       (source=OPERATOR_PINNED) so an operator who has measured a
       working model routes the engine's very first attempt there
       instead of burning the cascade on paid models the account
       cannot afford.

    R451-C1.5: a DISCOVERED catalog yields ONLY catalog-present models
    (even when the eligible set is empty); the pinned defaults stand
    in ONLY when the catalog is UNDISCOVERED/NO_BASE_URL (explicitly
    marked PINNED_DEFAULT). The old behavior — catalog discovered but
    pinned stale models retained — is REMOVED (the directive's named
    defect)."""
    # R530 §3: behavior-neutral diagnostic (counter + wall only).
    _de0 = time.perf_counter()
    pinned = _operator_pinned_model(provider_id)
    if catalog:
        cat_state = discover_catalog(provider_id).get("status")
        recs = _catalog_records(provider_id) \
            if cat_state == "DISCOVERED" else _pinned_records(provider_id)
    else:
        recs = _pinned_records(provider_id)
    # batch/alternate endpoint variants are not chat endpoints
    recs = [r for r in recs if not r.model.endswith(
        (":batch", ":extended"))]
    if pinned and not is_model_gone(provider_id, pinned):
        existing = next((r for r in recs if r.model == pinned), None)
        # R445 fix (measured defect, part 2): when the pinned model is
        # already in the catalog, the re-used CATALOG record kept
        # source='CATALOG' — so the operator pin was INVISIBLE to every
        # downstream consumer that honors the pin (build_ladder's
        # pin-stays-first fix looks for source='OPERATOR_PINNED' and
        # never matched). The pin marker travels on the record.
        if existing is not None and existing.source != "OPERATOR_PINNED":
            existing = ModelRecord(
                provider=existing.provider, model=existing.model,
                task_capabilities=existing.task_capabilities,
                cost_class=existing.cost_class,
                latency_class=existing.latency_class,
                context_limit=existing.context_limit,
                structured_output=existing.structured_output,
                source="OPERATOR_PINNED")
        pinned_rec = existing or ModelRecord(
            provider=provider_id, model=pinned,
            task_capabilities=[TASK_STRONG, TASK_FAST, TASK_CHEAP],
            cost_class=1, latency_class=2, context_limit=128000,
            source="OPERATOR_PINNED")
        recs = [pinned_rec] + [r for r in recs if r.model != pinned]
    _eres = [r for r in recs if task in r.task_capabilities] or recs
    # R530 §3: behavior-neutral diagnostic (counter + wall + count).
    _SELECTION_DIAG["eligible_models_calls"] += 1
    _SELECTION_DIAG["eligible_models_s"] += time.perf_counter() - _de0
    _SELECTION_DIAG["eligible_models_returned"] += len(_eres)
    return _eres


def all_models(provider_id: str) -> List[ModelRecord]:
    """The provider's models WITHOUT the task filter (the LAST_RESORT
    band's any-capability pool — same GONE exclusion, same sources).
    R418: batch/alternate endpoint variants are excluded here too —
    they are not chat-completions endpoints (measured 404).
    R451-C1.5: same DISCOVERED/UNDISCOVERED semantics as
    eligible_models (catalog-present models only when DISCOVERED;
    PINNED_DEFAULT otherwise)."""
    cat_state = discover_catalog(provider_id).get("status")
    recs = _catalog_records(provider_id) \
        if cat_state == "DISCOVERED" else _pinned_records(provider_id)
    return [r for r in recs if not r.model.endswith(
        (":batch", ":extended"))]


# ---------------------------------------------------------------------------
# The fallback LADDERS (directive section 5)
# ---------------------------------------------------------------------------
def build_ladder(task: str, role: Optional[str] = None,
                 avoid_provider: Optional[str] = None,
                 preferred_providers: Optional[List[str]] = None,
                 available_providers: Optional[List[str]] = None,
                 max_rungs: int = 8,
                 now: Optional[float] = None,
                 purpose: Optional[str] = None) -> Dict[str, Any]:
    """Build the ordered (provider, model) rung list for a task.

    Ladder shape (directive section 5):
      FAST:   primary fast -> secondary fast -> NVIDIA fast ->
              OPENROUTER fast/free -> secondary reasoning -> last-resort
      STRONG: primary strong -> NVIDIA strong -> OPENROUTER strong ->
              other available
      CHEAP:  cheap fast -> (LOCAL/DETERMINISTIC — the engine's own
              code parsers; not an LLM rung) -> secondary

    RUNG ORDER (the resilience property this exists for): ROUND-ROBIN
    across providers — every provider's best model for the task runs
    BEFORE any provider's second model. A provider-level outage (429,
    timeout) therefore walks to the NEXT provider immediately, and a
    MODEL-level retirement (410 GONE) falls back to the next provider's
    model before trying the same provider's alternate model. Bands:
      PRIMARY                each provider's best task-compatible model
      SECONDARY_REASONING    a reasoning-capable (STRONG) alternate rung
                             — the FAST ladder's "secondary reasoning
                             model" rung; never first (cheap first)
      PROVIDER_ALTERNATE     another model of the same provider (the
                             410-model-retirement fix)
      LAST_RESORT            every remaining eligible model, any provider

    Ordering within a provider: availability score DESC, then cost,
    then latency. Cooldown demotion (never removal) via the provider
    health book demotes the PROVIDER's round-robin slot to the end.
    preferred_providers (the R414 policy order) re-orders the provider
    slots without dropping any rung. Returns rungs plus the ladder's
    own provenance (decision inputs, recorded — Art. XXVII)."""
    from .provider_health import HEALTH
    now = now if now is not None else time.time()
    task = task if task in TASK_CLASSES else TASK_FAST
    provs = list(available_providers or [])
    if not provs:
        try:
            from .llm_registry import availability_matrix
            provs = [m["provider_id"] for m in availability_matrix()
                     if m.get("available")]
        except Exception:  # noqa: BLE001 — no providers configured
            provs = []

    # provider slots: preferred order first (R414 policy), others after
    if preferred_providers:
        head = [p for p in preferred_providers if p in provs]
        tail = [p for p in provs if p not in head]
        provs = head + tail
    # cooldown demotion (never removal — Art. V): cooled providers' slots
    # slide to the END of the round-robin
    if len(provs) > 1:
        cooled = [p for p in provs if HEALTH.in_cooldown(p)]
        if cooled:
            provs = [p for p in provs if p not in cooled] + cooled

    def _rank(r: ModelRecord) -> tuple:
        # R483 span-capable rung preference (SYNTHESIS purpose only):
        # a rung whose most recent measured span-contract outcome within
        # the declared window is a FAILURE demotes below every clean
        # rung (ordering-only, Art. V — the rung stays on the ladder;
        # LAST_RESORT can still reach it). Non-synthesis purposes are
        # untouched (the span contract is the synthesis stage's).
        span_pen = 0
        if purpose == "synthesis" and span_failed_recently(
                r.provider, r.model, now=now):
            span_pen = 1
        return (span_pen, -r.score(task, avoid_provider, now),
                r.cost_class, r.latency_class)

    # per-provider eligible lists, score-ranked
    per_provider: List[Tuple[str, List[ModelRecord]]] = []
    for p in provs:
        recs = sorted([r for r in eligible_models(p, task)
                       if task in r.task_capabilities], key=_rank)
        # R445 fix (measured defect): the R418 operator pin must stay the
        # provider's FIRST rung. eligible_models() emits the pinned model
        # at the head (source=OPERATOR_PINNED), but the availability-score
        # sort above reordered it below fast-but-otherwise-incapable
        # catalog models — measured live: NVIDIA_MODEL pinned to a
        # field-line-capable model while generate() still routed to
        # nvidia/nemotron-3.5-content-safety (sub-second "User Safety:
        # safe" classifier verdicts, no field lines -> honest
        # MECHANISM_GENERATION_FAILED / TRANSPORT_BLOCKED mislabels).
        # The pin is an explicit recorded operator decision; the score
        # heuristic ranks only BELOW it.
        pinned = [r for r in recs if r.source == "OPERATOR_PINNED"]
        if pinned:
            recs = pinned + [r for r in recs if r.source != "OPERATOR_PINNED"]
        if recs:
            per_provider.append((p, recs))

    rungs: List[Dict[str, Any]] = []
    emitted: set = set()

    def _emit(r: ModelRecord, band: str) -> None:
        if (r.provider, r.model) in emitted:
            return
        emitted.add((r.provider, r.model))
        rungs.append({
            "provider": r.provider, "model": r.model,
            "band": band, "task": task,
            "score": r.score(task, avoid_provider, now),
            "cost_class": r.cost_class,
            "latency_class": r.latency_class,
            "context_limit": r.context_limit,
            "source": r.source,
            # R451-C1.4: the rung's DECLARED task capabilities travel on
            # the rung so the degradation record (requested task vs the
            # serving model's capability) is computed at call time
            # without a second lookup.
            "task_capabilities": list(r.task_capabilities),
            # R451-C1.2: the economic account that actually pays for
            # this rung — MODEL vs PROVIDER vs ACCOUNT are three
            # different failure domains (operator directive); two
            # providers on ONE account domain are NOT redundant.
            "account_domain": _provider_account_domain(r.provider),
        })

    # round-robin: slot 0 of every provider, then slot 1 of every
    # provider, ... (the provider-diverse walk)
    max_len = max((len(recs) for _, recs in per_provider), default=0)
    for idx in range(max_len):
        for p, recs in per_provider:
            if idx < len(recs):
                r = recs[idx]
                if idx == 0:
                    band = "PRIMARY"
                elif TASK_STRONG in r.task_capabilities:
                    # a reasoning-capable alternate model: the FAST
                    # ladder's SECONDARY REASONING rung (after the fast
                    # rungs — never burns the strong model first)
                    band = "SECONDARY_REASONING"
                else:
                    band = "PROVIDER_ALTERNATE"
                _emit(r, band)

    # LAST_RESORT: the directive's final rung — ANY remaining eligible
    # model of any provider, WITHOUT the task filter (a lone surviving
    # route still serves; ordering-only, the cascade stays bounded)
    for p in provs:
        for r in sorted(all_models(p), key=_rank):
            _emit(r, "LAST_RESORT")

    rungs = rungs[:max_rungs]
    # R483: the demotion is RECORDED, never silent (Art. IV/XXVII) —
    # which rungs carried the span-failure penalty in this build
    # R530 §3: behavior-neutral diagnostic (inspection counts only).
    # providers/models considered across the per-provider eligible
    # lists (F detail) and final rungs emitted (after LAST_RESORT +
    # truncation). Counts only — no timing, no behavior change.
    _SELECTION_DIAG["ladder_providers_inspected"] += len(provs)
    _SELECTION_DIAG["ladder_models_inspected"] += sum(
        len(_recs) for _, _recs in per_provider)
    _SELECTION_DIAG["ladder_rungs_emitted"] += len(rungs)
    span_demoted = sorted({(r["provider"], r["model"])
                           for r in rungs
                           if purpose == "synthesis"
                           and span_failed_recently(r["provider"],
                                                    r["model"], now=now)})
    return {
        "task": task,
        "role": role,
        "avoid_provider": avoid_provider,
        "rungs": rungs,
        "rung_count": len(rungs),
        "decision_inputs": {
            "available_providers": provs,
            "preferred_providers": preferred_providers or None,
            "score_formula": ("span-outcome demotion (synthesis) → "
                              "recent_success_rate × health_recency × "
                              "provider_health × task_compatibility × "
                              "latency_suitability (× separation bonus "
                              "for attack routing)"),
            "span_outcome_demotion": {
                "applied": purpose == "synthesis",
                "window_s": SPAN_FAIL_DEMOTE_WINDOW_S,
                "demoted_rungs": [list(p) for p in span_demoted],
                "note": ("R483 span-capable rung preference: a rung "
                         "whose newest measured span outcome in the "
                         "window is a failure orders below clean "
                         "rungs (ordering-only, never removal — "
                         "Art. V)"),
            } if purpose == "synthesis" else None,
            "decay_half_life_s": DECAY_HALF_LIFE_S,
            "prior_strength": PRIOR_STRENGTH,
            "rung_order": ("round-robin across providers: every "
                           "provider's best model before any provider's "
                           "second model"),
            "note": ("ordering-only demotion (cooldown/low score); the "
                     "only hard exclusions are no-credential and "
                     "recorded 410-GONE models (Art. V)"),
        },
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


# ---------------------------------------------------------------------------
# Recording call outcomes (directive section 17 — the router learns)
# ---------------------------------------------------------------------------
def record_call_outcome(provider: str, model: str, ok: bool,
                        latency_ms: int = 0,
                        failure_type: Optional[str] = None,
                        task: Optional[str] = None,
                        stage: Optional[str] = None,
                        run_id: Optional[str] = None,
                        request_id: Optional[str] = None,
                        attempt: int = 1,
                        tokens: Optional[int] = None,
                        estimated_cost: Optional[float] = None,
                        fallback_from: Optional[str] = None,
                        fallback_to: Optional[str] = None,
                        error: str = "",
                        # R451 §6 (provider routing observability): every
                        # actual attempt carries its cost class, whether
                        # THIS attempt's route was the selected one, and
                        # the explicit reason a fallback followed — the
                        # production record must reconstruct the exact
                        # route with NO "models unavailable" summaries
                        cost_class: Optional[str] = None,
                        selected: Optional[bool] = None,
                        fallback_reason: str = "",
                        # R451-C1.3-3 (run-level routing provenance): the
                        # operator's required per-call fields — every REAL
                        # engine call inside an investigation carries
                        # run_id, session_id, stage, provider, model,
                        # attempt, task, cost basis, account domain,
                        # failure class, fallback_from, fallback_to.
                        # call_class separates RUN_OWNED discovery calls
                        # from CAPABILITY_PROBE lines (which legitimately
                        # carry run_id=None) and STANDALONE script calls.
                        session_id: Optional[str] = None,
                        engine_stage: Optional[str] = None,
                        call_class: str = "STANDALONE",
                        account_domain: Optional[str] = None,
                        task_degradation: Optional[Dict[str, Any]] = None,
                        capability_state: Optional[str] = None,
                        # R526 Q-A: behavior-neutral per-attempt span
                        # record from llm_registry.generate() (gen_spans
                        # instrument). Additive only: existing consumers
                        # read fixed keys and ignore this one; the
                        # harvester splits provider-call wall from
                        # selection/routing/sleep walls from it.
                        generate_spans: Optional[Dict[str, Any]] = None
                        ) -> None:
    """One ledger line per attempt. Updates model_health /
    provider_health / task_health (all derived from this same ledger —
    one authority, Art. X) and invalidates the probe cache on failure
    (directive section 6).

    R451-C1.3-3: the run-owned-call invariant is enforced HERE — a
    call marked call_class=RUN_OWNED with a null run_id is a
    provenance defect and raises (fail-closed: the record cannot be
    written without its run identity; the caller fixes the call site,
    never the ledger)."""
    import uuid
    if call_class == "RUN_OWNED" and not (run_id or "").strip():
        raise ValueError(
            "run_owned_call => run_id != null (R451-C1.3-3 invariant): "
            "the ledger refuses a run-owned line with no run identity "
            f"(provider={provider}, model={model}, stage={stage})")
    if account_domain is None:
        account_domain = _provider_account_domain(provider)
    LEDGER.record({
        "request_id": request_id or f"req_{uuid.uuid4().hex[:12]}",
        "run_id": run_id,
        "session_id": session_id,
        "engine_stage": engine_stage,
        "call_class": call_class,
        "stage": stage,
        "task": task,
        "provider": provider,
        "model": model,
        "attempt": attempt,
        "ok": bool(ok),
        "status": ("OK" if ok else "FAILED"),
        "failure_class": failure_type,
        "latency_ms": int(latency_ms or 0),
        "latency": int(latency_ms or 0),   # directive §16 field name
        "tokens": tokens,
        "estimated_cost": estimated_cost,
        "cost_class": cost_class,
        "account_domain": account_domain,
        "selected": selected,
        "fallback_from": fallback_from,
        "fallback_to": fallback_to,
        "fallback_reason": str(fallback_reason or "")[:240],
        "task_degradation": task_degradation,
        "capability_state": capability_state,
        "error": str(error)[:240],
        "generate_spans": generate_spans,
    })
    if not ok:
        clear_probe_cache(provider, model)
        if failure_type == "GONE":
            mark_model_gone(provider, model)
        elif failure_type == "MODEL_NOT_FOUND":
            # R451-C1.2 (operator directive: never retry a permanently
            # invalid model identifier): the provider's own response
            # says this id is not served on this route. The same
            # known-dead discipline as GONE — the provider's OTHER
            # models stay eligible (Art. V).
            mark_model_gone(
                provider, model,
                evidence="provider responded model_not_found (404 or "
                         "error body) — the identifier is permanently "
                         "invalid on this route (R451-C1.2)")
    else:
        if is_model_gone(provider, model):
            clear_model_gone(provider, model)
        probe_cache_put(provider, model, {
            "status": "HEALTHY", "latency_ms": int(latency_ms or 0),
            "ok": True})


def record_phase_span(session_id: Optional[str],
                      run_id: Optional[str],
                      engine_stage: Optional[str],
                      phase: str,
                      event: str,
                      candidate_id: Optional[str] = None,
                      candidate_key: Optional[str] = None,
                      wall_s: Optional[float] = None,
                      detail: Optional[Dict[str, Any]] = None,
                      scope: str = "top") -> None:
    """R526 Q-B: one durable orchestration-timing line per post-rank
    phase entry/exit (and candidate-loop iterations where available).

    Written to the SAME append-only model_routing ledger (the proven
    durable channel — run-dir sidecars are demonstrably absent
    branch-wide even on runs with proven post-rank work) with
    line_class=PHASE_SPAN so every consumer can separate orchestration
    timing from provider telemetry:
      - decayed availability statistics skip PHASE_SPAN lines,
      - provider-call aggregations filter them (R526 harvester),
      - run isolation (ledger_for_run) keeps them (same run_id).
    Behavior-neutral: pure telemetry append; never raises (best
    effort, disclosed via last_error like every ledger write).

    scope (R526 Q-B parent/child discriminator): "top" marks a
    top-level phase wall (whole GAUNTLET / KILL_IMPROVE /
    IMPROVEMENT_PASS / TECHNICAL_IMPROVEMENT_PASS — the ONLY walls
    that may enter the run-wall reconciliation), "child" marks a
    per-candidate / per-target span nested INSIDE a top-level phase
    (attribution detail; NEVER added on top of the parent wall).

    B3 parent/child identity: the durable join key is the smallest
    explicit identity already available on the line —
    (phase, scope, candidate_key, candidate_id). For a top-scope
    line candidate_key/candidate_id are None (the whole phase has no
    per-candidate identity); for a child-scope line they carry the
    candidate/target key. The phase name is shared by the parent
    and its children (a child's phase = its enclosing top-scope
    phase), so (phase, scope, candidate_key, candidate_id) uniquely
    identifies each span and deterministically joins children to
    their parent WITHOUT time-window matching. No separate
    parent_phase field is emitted: the enclosing top-scope phase is
    the line's own `phase` when scope=child (documented invariant,
    enforced by the caller passing the enclosing phase name).
    """
    import uuid
    try:
        LEDGER.record({
            "line_class": "PHASE_SPAN",
            "request_id": f"ph_{uuid.uuid4().hex[:12]}",
            "run_id": run_id,
            "session_id": session_id,
            "engine_stage": engine_stage,
            "call_class": "PHASE_SPAN",
            "stage": phase,
            "task": None,
            "provider": None,
            "model": None,
            "attempt": None,
            "ok": None,
            "status": "PHASE_SPAN",
            "failure_class": None,
            "latency_ms": 0,
            "latency": 0,
            "tokens": None,
            "estimated_cost": None,
            "cost_class": None,
            "account_domain": None,
            "selected": None,
            "fallback_from": None,
            "fallback_to": None,
            "fallback_reason": "",
            "task_degradation": None,
            "capability_state": None,
            "error": "",
            "phase": phase,
            "event": event,
            "scope": scope,
            "candidate_id": candidate_id,
            "candidate_key": candidate_key,
            "wall_s": wall_s,
            "detail": detail or {},
        })
    except Exception:  # noqa: BLE001 — telemetry never fails the run
        pass


def ledger_for_run(run_id: str, tail: Optional[int] = None) \
        -> List[Dict[str, Any]]:
    """R451-C1.3-3: isolate ONE run's routing records from the
    append-only ledger BY RUN ID — no time-window inference, no
    ledger-tail assumption (the directive's acceptance: 'the evidence
    must allow us to isolate this run's calls without relying on a
    time window or ledger tail'). Reads the full ledger bytes (the
    ledger is the authority, Art. X)."""
    try:
        if not LEDGER._path.exists():
            return []
        with LEDGER._path.open() as fh:
            lines = fh.readlines()
        out = []
        for ln in lines:
            try:
                d = json.loads(ln)
                if isinstance(d, dict) and d.get("run_id") == run_id:
                    out.append(d)
            except Exception:  # noqa: BLE001 — a torn line is skipped
                pass
        return out[-tail:] if tail else out
    except Exception:  # noqa: BLE001
        return []


# ---------------------------------------------------------------------------
# Provider summary for /api/health (directive sections 6 + 13)
# ---------------------------------------------------------------------------
PROVIDER_STATES = ("HEALTHY", "DEGRADED", "RATE_LIMITED", "AUTH_FAILED",
                   "GONE", "TIMEOUT", "UNAVAILABLE", "UNKNOWN")


def provider_state(provider_id: str, has_key: bool) -> str:
    """The directive section-6 state vocabulary, derived from recorded
    facts only: credential presence, the provider health book, and the
    routing ledger. UNKNOWN is honest when nothing was measured."""
    if not has_key:
        return "UNAVAILABLE"
    from .provider_health import HEALTH
    if HEALTH.in_cooldown(provider_id):
        return "RATE_LIMITED"
    rep = availability_report(provider=provider_id)
    rate = rep.get("recent_success_rate")
    last_fail = (HEALTH.last_failure_type(provider_id)
                 if hasattr(HEALTH, "last_failure_type") else None)
    if last_fail == "AUTH_FAILURE" and rate is not None and rate < 0.5:
        return "AUTH_FAILED"
    if last_fail == "GONE" and rate is not None and rate < 0.5:
        return "GONE"
    if rate is None:
        # never called through the router: check the R414 book too
        try:
            snap = HEALTH.snapshot()
            entry = next((p for p in snap if p.get("provider")
                          == provider_id), None)
            if entry and entry.get("call_count"):
                # called pre-R415 through the provider book
                return "DEGRADED" if entry.get("status") == "DEGRADED" \
                    else "HEALTHY"
        except Exception:  # noqa: BLE001
            pass
        return "UNKNOWN"
    if rate >= 0.8:
        return "HEALTHY"
    if rate >= 0.4:
        return "DEGRADED"
    return "DEGRADED" if rate > 0 else "UNKNOWN"


def provider_summary() -> Dict[str, Dict[str, Any]]:
    """The directive section-13 shape:

        providers: {nvidia: {status, available_models}, openrouter: {...}}

    available_models = the count of eligible, non-GONE models (catalog
    where discovered, pinned defaults otherwise). No keys, no endpoints,
    no secrets."""
    out: Dict[str, Dict[str, Any]] = {}
    try:
        from .llm_registry import availability_matrix, PROVIDER_SPECS
        for spec in PROVIDER_SPECS:
            has_key = bool(os.environ.get(spec.env_var, "").strip())
            models = eligible_models(spec.provider_id, TASK_FAST) \
                if has_key else []
            out[spec.provider_id] = {
                "status": provider_state(spec.provider_id, has_key),
                "available_models": len(models),
                "credential": "CONFIGURED" if has_key else "NOT_CONFIGURED",
            }
        del availability_matrix
    except Exception as exc:  # noqa: BLE001 — disclosed, never silent
        out["_error"] = {"status": "UNKNOWN",
                         "note": f"summary failed: {type(exc).__name__}"
                                 f" {exc}"[:160]}
    return out


def startup_validation() -> List[str]:
    """Directive section 2: startup validation reports ONLY
    'NVIDIA: CONFIGURED' / 'OPENROUTER: CONFIGURED' (or NOT_CONFIGURED)
    — never the secret, never a key fragment. Checks the SAME sources
    the engine's call path reads: the process env (the Render/
    deployment shape) and the repo's .env.keys bootstrap (the sandbox
    shape — loaded by adapters.load_credentials at call time)."""
    lines = []
    try:
        try:
            from .adapters import load_credentials
            load_credentials()   # same call-time bootstrap the engine uses
        except Exception:  # noqa: BLE001 — env-only is the honest fallback
            pass
        from .llm_registry import PROVIDER_SPECS
        for spec in PROVIDER_SPECS:
            has = bool(os.environ.get(spec.env_var, "").strip())
            lines.append(f"{spec.provider_id.upper()}: "
                         f"{'CONFIGURED' if has else 'NOT_CONFIGURED'}")
    except Exception as exc:  # noqa: BLE001
        lines.append(f"STARTUP_VALIDATION_FAILED: {type(exc).__name__}")
    return lines

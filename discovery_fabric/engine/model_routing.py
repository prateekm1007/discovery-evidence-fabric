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
        r"^glm-",
    ],
    "tokenrouter": [
        r"^z-ai/glm",
        r"^glm-",
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
        {"model": "glm-4-plus",
         "task_capabilities": [TASK_STRONG, TASK_FAST, TASK_CHEAP],
         "cost_class": 1, "latency_class": 1, "context_limit": 128000},
    ],
    "tokenrouter": [
        {"model": "z-ai/glm-5.3-free",
         "task_capabilities": [TASK_STRONG, TASK_FAST, TASK_CHEAP],
         "cost_class": 1, "latency_class": 2, "context_limit": 128000},
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


def _get_json(url: str, key: Optional[str], timeout: int = 20) -> dict:
    req = urllib.request.Request(url)
    if key:
        req.add_header("Authorization", f"Bearer {key}")
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
    pinned default models stand in — never silent, never fatal."""
    base = _provider_base_url(provider_id)
    if not base:
        return {"provider": provider_id, "status": "NO_BASE_URL",
                "models": []}
    cache = CATALOG_DIR / f"{provider_id}.json"
    if not force and cache.exists():
        try:
            data = json.loads(cache.read_text())
            age = time.time() - float(data.get("fetched_at_epoch") or 0)
            if age < CATALOG_TTL_S:
                return data
        except Exception:  # noqa: BLE001 — stale cache falls through
            pass
    key_var = _provider_env_key(provider_id)
    key = (os.environ.get(key_var, "").strip()) if key_var else ""
    url = base.rstrip("/") + "/models"
    out: Dict[str, Any]
    try:
        data = _get_json(url, key or None, timeout=20)
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
        cache.write_text(json.dumps(out, indent=1, sort_keys=True))
    except Exception:  # noqa: BLE001 — cache is best-effort
        pass
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
def _load_state() -> Dict[str, Any]:
    try:
        if STATE_PATH.exists():
            data = json.loads(STATE_PATH.read_text())
            if isinstance(data, dict):
                return data
    except Exception:  # noqa: BLE001 — corrupt state degrades to empty
        pass
    return {}


def mark_model_gone(provider: str, model: str) -> None:
    """Record (provider, model) as GONE — the provider itself answered
    410. The model is excluded from ladders until a fresh catalog lists
    it again or a call succeeds; the PROVIDER stays eligible (Art. V)."""
    state = _load_state()
    gone = state.setdefault("gone_models", {})
    gone[f"{provider}::{model}"] = {
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "evidence": "provider responded HTTP 410 Gone on a live call",
    }
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(state, indent=1, sort_keys=True))
    except Exception:  # noqa: BLE001 — best-effort, disclosed via catalog
        pass
    # a GONE model is not in the live catalog by definition — refresh it
    clear_probe_cache(provider, model)


def is_model_gone(provider: str, model: str) -> bool:
    return f"{provider}::{model}" in (_load_state().get("gone_models")
                                      or {})


def clear_model_gone(provider: str, model: str) -> None:
    state = _load_state()
    gone = state.setdefault("gone_models", {})
    if f"{provider}::{model}" in gone:
        del gone[f"{provider}::{model}"]
        try:
            STATE_PATH.write_text(json.dumps(state, indent=1,
                                             sort_keys=True))
        except Exception:  # noqa: BLE001
            pass


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
    succ_w = fail_w = 0.0
    last_obs_at: Optional[float] = None
    latency_ema_num = 0.0
    latency_ema_den = 0.0
    for e in LEDGER.tail():
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
    return {
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
    return round(max(0.0, min(2.0, recent_rate * recency * provider_health
                              * task_compat * latency_suit * separation)), 6)


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
    cat = discover_catalog(provider_id)
    if cat.get("status") != "DISCOVERED":
        return []
    out: List[ModelRecord] = []
    emitted: set = set()
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
        emitted.add(mid)
    # pinned defaults stay visible even when the live catalog is smaller
    # (they are allowlist members; a 410 marks them GONE individually)
    for d in PINNED_DEFAULT_MODELS.get(provider_id, []):
        if d["model"] in emitted or is_model_gone(provider_id, d["model"]):
            continue
        out.append(ModelRecord(
            provider=provider_id, model=d["model"],
            task_capabilities=d["task_capabilities"],
            cost_class=d["cost_class"],
            latency_class=d["latency_class"],
            context_limit=d["context_limit"],
            source="PINNED_DEFAULT"))
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
       cannot afford."""
    pinned = _operator_pinned_model(provider_id)
    recs = _catalog_records(provider_id) if catalog else []
    if not recs:
        recs = _pinned_records(provider_id)
    # batch/alternate endpoint variants are not chat endpoints
    recs = [r for r in recs if not r.model.endswith(
        (":batch", ":extended"))]
    if pinned and not is_model_gone(provider_id, pinned):
        existing = next((r for r in recs if r.model == pinned), None)
        pinned_rec = existing or ModelRecord(
            provider=provider_id, model=pinned,
            task_capabilities=[TASK_STRONG, TASK_FAST, TASK_CHEAP],
            cost_class=1, latency_class=2, context_limit=128000,
            source="OPERATOR_PINNED")
        recs = [pinned_rec] + [r for r in recs if r.model != pinned]
    return [r for r in recs if task in r.task_capabilities] or recs


def all_models(provider_id: str) -> List[ModelRecord]:
    """The provider's models WITHOUT the task filter (the LAST_RESORT
    band's any-capability pool — same GONE exclusion, same sources).
    R418: batch/alternate endpoint variants are excluded here too —
    they are not chat-completions endpoints (measured 404)."""
    recs = _catalog_records(provider_id)
    if not recs:
        recs = _pinned_records(provider_id)
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
                 now: Optional[float] = None) -> Dict[str, Any]:
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
        return (-r.score(task, avoid_provider, now), r.cost_class,
                r.latency_class)

    # per-provider eligible lists, score-ranked
    per_provider: List[Tuple[str, List[ModelRecord]]] = []
    for p in provs:
        recs = sorted([r for r in eligible_models(p, task)
                       if task in r.task_capabilities], key=_rank)
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
    return {
        "task": task,
        "role": role,
        "avoid_provider": avoid_provider,
        "rungs": rungs,
        "rung_count": len(rungs),
        "decision_inputs": {
            "available_providers": provs,
            "preferred_providers": preferred_providers or None,
            "score_formula": ("recent_success_rate × health_recency × "
                              "provider_health × task_compatibility × "
                              "latency_suitability (× separation bonus "
                              "for attack routing)"),
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
                        error: str = "") -> None:
    """One ledger line per attempt. Updates model_health /
    provider_health / task_health (all derived from this same ledger —
    one authority, Art. X) and invalidates the probe cache on failure
    (directive section 6)."""
    import uuid
    LEDGER.record({
        "request_id": request_id or f"req_{uuid.uuid4().hex[:12]}",
        "run_id": run_id,
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
        "fallback_from": fallback_from,
        "fallback_to": fallback_to,
        "error": str(error)[:240],
    })
    if not ok:
        clear_probe_cache(provider, model)
        if failure_type == "GONE":
            mark_model_gone(provider, model)
    else:
        if is_model_gone(provider, model):
            clear_model_gone(provider, model)
        probe_cache_put(provider, model, {
            "status": "HEALTHY", "latency_ms": int(latency_ms or 0),
            "ok": True})


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

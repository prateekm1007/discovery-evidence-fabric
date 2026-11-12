"""discovery_fabric/engine/llm_economy.py — R6 owner round 2026-11-12, items A1+A2.

A1 RECORD/REPLAY + STAGE MEMOIZATION: every LLM call is cached by
hash(provider, model, messages, max_tokens, params) in a GITIGNORED store;
stage outputs are memoized by the canonical upstream envelope hash so
leave-one-out and A/B ablation arms recompute only the stages downstream of
what actually changed. Replay (ro) mode makes ablations, tests and
benchmarks free and deterministic: an unrecorded call fails TYPED instead of
spending quota (Art. XXI.3 — a typed refusal, never a silent drop and never
a silent live spend).

A2 RETRY-STORM CIRCUIT BREAKER: a per-provider breaker opens after N
consecutive transient failures (429/502/503/504/timeouts) and refuses that
provider with a typed state until a cooldown elapses (AIMD-style: the
cooldown doubles on each re-open, capped); a per-problem call governor caps
attempts at <=HEALTHY healthy (distinct logical) calls and <=RETRY retry
attempts (re-attempts of the same logical call, provider retries and ladder
hops included) — the measured defect this kills is the 31-40 provider
attempts per problem storm (owner audit fact; the healthy-call target is
<=12).

Every decision is LOGGED (events.jsonl, best-effort) and surfaced as a
counters snapshot (EngineRun persists it as LLM_ECONOMY.json and carries it
on the run manifest). When FABRIC_LLM_CACHE=off (default) the cache and the
stage memo are fully inert — zero behavior change (Art. LXIV discipline:
additive capability, retired paths stay retired). The governor and the
breaker are ON by default because they bound infrastructure failure, not
capability (Art. LXI: infrastructure failure is bounded and typed, never
unbounded waiting or unbounded spending).

Env knobs (all operator-declared, recorded in the snapshot):
  FABRIC_LLM_CACHE          off (default) | rw (record+reuse) | ro (replay)
  FABRIC_LLM_ECONOMY_DIR    store root, default .llm_cache (gitignored)
  FABRIC_PROBLEM_CALL_CAP   healthy logical calls per problem scope, default 12 (0 disables)
  FABRIC_PROBLEM_RETRY_CAP  retry attempts per problem scope, default 6 (0 disables)
  FABRIC_CALL_GOVERNOR      anything but "off" enables the governor (default on)
  FABRIC_BREAKER            anything but "off" enables the breaker (default on)
  FABRIC_BREAKER_THRESHOLD  consecutive transient failures that open it, default 3 (0 disables)
  FABRIC_BREAKER_COOLDOWN_S initial open cooldown, default 60
"""
from __future__ import annotations

import hashlib
import json
import os
import ssl
import threading
import time
import urllib.error
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# typed errors (Art. XXI.3: typed outcomes, never silent drops)


class CallEconomyError(RuntimeError):
    """Base class for every llm_economy typed state."""


class TypedCacheMiss(CallEconomyError):
    """Replay (ro) mode: the call was never recorded — replay contract is
    fail-closed (no silent live spend)."""


class CallBudgetExceeded(CallEconomyError):
    """A per-problem attempt budget was exhausted (typed base class)."""


class HealthyCallCapExceeded(CallBudgetExceeded):
    """Per-problem healthy-call cap reached (default 12)."""


class RetryCapExceeded(CallBudgetExceeded):
    """Per-problem retry cap reached (default 6)."""


class BreakerOpen(CallEconomyError):
    """Provider breaker open: consecutive transient failures exhausted.

    `request_made` distinguishes the two honest cases the route records:
    a PRE-request refusal (the breaker was already open; zero provider
    spend) from the THRESHOLD-CROSSING request (the provider was called
    and its transient failure opened the breaker). The latter must still
    reach provider health + the routing ledger — a request that happened
    is never erased by the typed stop (Art. XXV)."""

    def __init__(self, message: str, request_made: bool = False):
        super().__init__(message)
        self.request_made = bool(request_made)


def typed_state(exc: BaseException) -> Optional[str]:
    """The closed typed-state vocabulary a generate() walk records for an
    economy refusal. Ordinary provider failures return None — they keep
    the provider-health taxonomy (RATE_LIMITED, AUTH_FAILURE, ...)."""
    if isinstance(exc, BreakerOpen):
        return "CIRCUIT_BREAKER_OPEN"
    if isinstance(exc, HealthyCallCapExceeded):
        return "HEALTHY_CALL_CAP_EXCEEDED"
    if isinstance(exc, RetryCapExceeded):
        return "RETRY_CAP_EXCEEDED"
    if isinstance(exc, CallBudgetExceeded):
        return "ATTEMPT_BUDGET_EXHAUSTED"
    if isinstance(exc, TypedCacheMiss):
        return "REPLAY_CACHE_MISS"
    return None


#: HTTP statuses that mean "the provider is busy / the transport failed",
#: never "your request was wrong". 401/403/404/410/422 are PERMANENT and
#: must never feed the retry-storm breaker (a bad key is not congestion).
_TRANSIENT_HTTP_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})


def is_transient_provider_failure(exc: BaseException) -> bool:
    """Infrastructure-class failure: 429/timeout/5xx/network. The breaker
    counts ONLY these; a permanent auth/model error is a typed failure
    that the health taxonomy records, not a reason to stop the provider."""
    if isinstance(exc, urllib.error.HTTPError):
        try:
            return int(getattr(exc, "code", 0) or 0) in _TRANSIENT_HTTP_CODES
        except (TypeError, ValueError):
            return False
    return isinstance(exc, (urllib.error.URLError, TimeoutError,
                            ConnectionError, ssl.SSLError))


# ---------------------------------------------------------------------------
# config

_ENV_MODE = "FABRIC_LLM_CACHE"
_ENV_DIR = "FABRIC_LLM_ECONOMY_DIR"
_ENV_CALL_CAP = "FABRIC_PROBLEM_CALL_CAP"
_ENV_RETRY_CAP = "FABRIC_PROBLEM_RETRY_CAP"
_ENV_GOVERNOR = "FABRIC_CALL_GOVERNOR"
_ENV_BREAKER = "FABRIC_BREAKER"
_ENV_BREAKER_THRESHOLD = "FABRIC_BREAKER_THRESHOLD"
_ENV_BREAKER_COOLDOWN = "FABRIC_BREAKER_COOLDOWN_S"

_BREAKER_COOLDOWN_MAX_S = 600.0

# RLock (reentrant): reset_run_counters -> reset_governor and the
# governor_attempt stop branches nest lock acquisitions on one thread
_lock = threading.RLock()


def _env_str(name: str, default: str) -> str:
    return (os.environ.get(name, "") or "").strip() or default


def _env_int(name: str, default: int) -> int:
    raw = (os.environ.get(name, "") or "").strip()
    if not raw:
        return default
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return default  # malformed override ignored (recorded policy)


def cache_mode() -> str:
    m = _env_str(_ENV_MODE, "off").lower()
    return m if m in ("off", "rw", "ro") else "off"


def econ_root() -> Path:
    return Path(_env_str(_ENV_DIR, ".llm_cache"))


def governor_enabled() -> bool:
    return _env_str(_ENV_GOVERNOR, "on").lower() != "off"


def breaker_enabled() -> bool:
    return _env_str(_ENV_BREAKER, "on").lower() != "off"


def breaker_threshold() -> int:
    return _env_int(_ENV_BREAKER_THRESHOLD, 3)


def breaker_cooldown_s() -> float:
    raw = (os.environ.get(_ENV_BREAKER_COOLDOWN, "") or "").strip()
    try:
        v = float(raw) if raw else 60.0
    except (TypeError, ValueError):
        v = 60.0
    return max(1.0, v)


def healthy_call_cap() -> int:
    return _env_int(_ENV_CALL_CAP, 12)


def retry_cap() -> int:
    return _env_int(_ENV_RETRY_CAP, 6)


# ---------------------------------------------------------------------------
# event log (the "log it" requirement) — best-effort, never crash the caller

EVENTS_FILE = "events.jsonl"


def _log_event(kind: str, **fields: Any) -> None:
    try:
        root = econ_root()
        root.mkdir(parents=True, exist_ok=True)
        rec = {"at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
               "kind": kind}
        rec.update(fields)
        with open(root / EVENTS_FILE, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    except OSError:
        pass  # logging is best-effort; the typed state itself is authoritative


# ---------------------------------------------------------------------------
# A1: LLM call cache (gitignored store, keyed by hash(prompt, model, params))

_calls_dir = "calls"
_counters: Dict[str, Any] = {
    "cache_hits": 0, "cache_misses": 0, "cache_writes": 0,
    "cache_blocked_ro": 0,
    "governor_healthy": 0, "governor_retries": 0,
    "governor_stops": 0,
    "breaker_opens": 0, "breaker_refusals": 0,
    "stage_memo_hits": 0, "stage_memo_writes": 0,
}


def llm_cache_key(provider_id: str, model: str, messages: List[dict],
                  max_tokens: int, extra_body: Optional[dict] = None,
                  temperature: float = 0.0, system: str = "") -> str:
    """hash(prompt, model, params) — the owner's A1 key basis.

    The openai flavor carries the system prompt inside `messages`; the
    anthropic flavor splits it out of the message list before the HTTP
    body, so its cache key MUST carry the extracted `system` separately
    (two calls with the same user turn but different system directives
    are different prompts and must never share a cache entry)."""
    canon = json.dumps(
        {"provider": provider_id, "model": model, "messages": messages,
         "max_tokens": max_tokens, "temperature": temperature,
         "extra_body": extra_body or {}, "system": system},
        sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def cache_get(key: str) -> Optional[Dict[str, Any]]:
    mode = cache_mode()
    if mode == "off":
        return None
    p = econ_root() / _calls_dir / f"{key}.json"
    if not p.exists():
        with _lock:
            _counters["cache_misses"] += 1
        _log_event("cache_miss", key=key[:12], mode=mode)
        if mode == "ro":
            # replay contract: a miss in replay mode is a typed failure,
            # never a silent live spend and never a fabricated answer
            raise TypedCacheMiss(
                f"REPLAY_CACHE_MISS: no recorded call for key {key[:12]} "
                f"(store {econ_root()}); replay mode is fail-closed")
        return None
    try:
        entry = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        with _lock:
            _counters["cache_misses"] += 1
        _log_event("cache_corrupt", key=key[:12])
        if mode == "ro":
            raise TypedCacheMiss(
                f"REPLAY_CACHE_CORRUPT: unreadable entry for {key[:12]}")
        return None
    with _lock:
        _counters["cache_hits"] += 1
    _log_event("cache_hit", key=key[:12],
               provider=entry.get("provider_id"), model=entry.get("model"))
    return entry


def cache_put(key: str, entry: Dict[str, Any]) -> None:
    if cache_mode() != "rw":
        return
    try:
        p = econ_root() / _calls_dir
        p.mkdir(parents=True, exist_ok=True)
        rec = dict(entry)
        rec["recorded_at"] = time.strftime(
            "%Y-%m-%dT%H:%M:%S", time.gmtime())
        (p / f"{key}.json").write_text(
            json.dumps(rec, ensure_ascii=False, default=str),
            encoding="utf-8")
        with _lock:
            _counters["cache_writes"] += 1
        _log_event("cache_put", key=key[:12],
                   provider=entry.get("provider_id"),
                   model=entry.get("model"))
    except OSError:
        pass  # the live call already succeeded; a store write failure must
        # not turn a good answer into a failure (best-effort record)


# ---------------------------------------------------------------------------
# A1: stage memoization (upstream-hash keyed stage outputs)


_stage_dir = "stages"

# volatile keys stripped from the memo-key snapshot: wall times, request
# identities and provenance stamps vary between runs and never determine a
# stage's logic. Content hashes (e.g. evidence_sha256) are KEPT — they are
# state, not stamps.
_VOLATILE_EXACT = {
    "at", "ts", "timestamp", "started_at", "finished_at", "recorded_at",
    "generated_at", "duration_monotonic_s", "run_id", "call_id",
    "session_id", "fanout_wall_s", "job_wall_s",
}


def strip_volatile(obj: Any) -> Any:
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            ks = str(k)
            if ks in _VOLATILE_EXACT or ks.endswith(("_at", "_ts", "_wall_s",
                                                     "_elapsed_s")) \
                    or ks.startswith("duration_"):
                continue
            out[k] = strip_volatile(v)
        return out
    if isinstance(obj, (list, tuple)):
        return [strip_volatile(v) for v in obj]
    return obj


#: Environment variables that can change a STAGE'S OUTPUT. FABRIC_* is
#: deliberately excluded: every FABRIC_* knob is economy/store mechanics
#: (cache mode, store root, breaker/call caps), so flipping the memo from
#: rw to ro or changing a budget must not invalidate a memoized stage.
#: EVAL_DISABLE_STAGES is excluded for the same reason: it is the
#: ablation ORCHESTRATION switch, not a semantic input — including it
#: would make every leave-one-out arm invalidate its own upstream reuse,
#: defeating the purpose of the stage memo. Secrets are never hashed.
_CONFIG_ENV_PREFIXES = (
    "ENGINE_", "EVAL_", "MODEL_", "EVIDENCE_", "TOSCANINI_",
    "LOCAL_QWEN_", "MAX_OP_CALLS",
)
_CONFIG_ENV_SUFFIXES = (
    "_MODEL", "_PROVIDER", "_BASE_URL", "_BACKEND", "_TIMEOUT_S",
)
_CONFIG_ENV_EXCLUDE = {
    "EVAL_DISABLE_STAGES",       # ablation orchestration, not semantics
    "FABRIC_LLM_CACHE",          # store mechanics
    "FABRIC_LLM_ECONOMY_DIR",
}
_SECRET_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL",
                   "AUTH")


def _is_secret_name(name: str) -> bool:
    up = name.upper()
    return any(marker in up for marker in _SECRET_MARKERS)


def semantic_config_identity() -> str:
    """Deterministic identity of the operator-declared semantic config:
    routing pins, cost policy, retrieval/render switches, model pins.
    A/B/LOO arms that change one of these must never reuse a stage output
    computed under a different configuration (the memo is a cache of
    BEHAVIOR, not merely of bytes)."""
    picked: Dict[str, str] = {}
    for name, value in os.environ.items():
        if name in _CONFIG_ENV_EXCLUDE or name.startswith("FABRIC_"):
            continue
        if _is_secret_name(name):
            continue
        if not (name.startswith(_CONFIG_ENV_PREFIXES)
                or name.endswith(_CONFIG_ENV_SUFFIXES)):
            continue
        picked[name] = str(value)
    canon = json.dumps(picked, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


#: Package roots whose code can influence a stage's output. The stage's
#: own source is already in the key; this wider fingerprint closes the
#: imported-module blind spot (a threshold constant or helper in a
#: sibling module changes the stage's behavior without changing the
#: adapter function's own source).
_CODE_ROOTS = ("engine", "retrieval_fabric")
_code_identity_cache: Dict[str, Any] = {"sig": None, "identity": None}


def _engine_code_files() -> List[Path]:
    base = Path(__file__).resolve().parents[1]
    out: List[Path] = []
    for root_name in _CODE_ROOTS:
        root = base / root_name
        if not root.is_dir():
            continue
        for p in root.rglob("*"):
            if not p.is_file() or p.suffix not in (".py", ".json"):
                continue
            if "__pycache__" in p.parts or "node_modules" in p.parts:
                continue
            out.append(p)
    return sorted(out)


def engine_code_identity() -> str:
    """Stable digest of the engine/retrieval source + declared JSON
    config. Cached per process and refreshed only when a file's size or
    mtime changes."""
    files = _engine_code_files()
    sig = hashlib.sha256(json.dumps(
        [[str(p), p.stat().st_size, p.stat().st_mtime_ns] for p in files],
        sort_keys=True).encode("utf-8")).hexdigest()
    with _lock:
        if _code_identity_cache["sig"] == sig:
            return _code_identity_cache["identity"]
    h = hashlib.sha256()
    base = Path(__file__).resolve().parents[1]
    for p in files:
        h.update(p.relative_to(base).as_posix().encode("utf-8"))
        h.update(b"\0")
        h.update(p.read_bytes())
        h.update(b"\0")
    identity = h.hexdigest()
    with _lock:
        _code_identity_cache["sig"] = sig
        _code_identity_cache["identity"] = identity
    return identity


def stage_memo_key(stage_name: str, capability_id: str, module_path: str,
                   fn_name: str, fn_source: str,
                   upstream_snapshot: Any,
                   config_identity: Optional[str] = None,
                   code_identity: Optional[str] = None) -> str:
    """Memo key = stage identity + source + semantic config + engine code
    + canonical upstream state. Every component that can change a stage's
    output is present, so an ablated/config-changed arm cannot falsely
    hit a memoized stage from the base run."""
    canon = json.dumps(
        {"stage": stage_name, "cap": capability_id, "mod": module_path,
         "fn": fn_name, "code": hashlib.sha256(
             fn_source.encode("utf-8")).hexdigest(),
         "config": (config_identity
                    if config_identity is not None
                    else semantic_config_identity()),
         "engine_code": (code_identity if code_identity is not None
                         else engine_code_identity()),
         "upstream": upstream_snapshot},
        sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def stage_memo_lookup(key: str) -> Optional[Dict[str, Any]]:
    if cache_mode() == "off":
        return None
    p = econ_root() / _stage_dir / f"{key}.json"
    if not p.exists():
        return None  # a stage-memo miss is normal (changed upstream): the
        # replay contract is enforced at the LLM-cache layer, not here
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    with _lock:
        _counters["stage_memo_hits"] += 1
    _log_event("stage_memo_hit", key=key[:12])
    return payload


def stage_memo_put(key: str, payload: Dict[str, Any]) -> None:
    if cache_mode() != "rw":
        return
    try:
        p = econ_root() / _stage_dir
        p.mkdir(parents=True, exist_ok=True)
        (p / f"{key}.json").write_text(
            json.dumps(payload, ensure_ascii=False, default=str),
            encoding="utf-8")
        with _lock:
            _counters["stage_memo_writes"] += 1
        _log_event("stage_memo_put", key=key[:12])
    except OSError:
        pass


# ---------------------------------------------------------------------------
# A2: per-problem call governor (<=12 healthy + <=6 retries, logged)

_governor: Dict[str, Any] = {
    "scope": None, "healthy": 0, "retries": 0,
    "seen_keys": set(), "stops": [],
}


def reset_governor(scope: str) -> None:
    """Start a NEW problem scope (call at every per-problem entry point:
    EngineRun.run(), each eval arm, each judged pair)."""
    with _lock:
        _governor["scope"] = scope
        _governor["healthy"] = 0
        _governor["retries"] = 0
        _governor["seen_keys"] = set()
        _governor["stops"] = []
    _log_event("governor_reset", scope=scope)


def governor_attempt(logical_key: str) -> Dict[str, Any]:
    """Count ONE provider attempt. First attempt of a never-seen logical key
    is HEALTHY; any further attempt of the same key (transport retries,
    ladder re-attempts) is a RETRY. Raises typed when a cap is hit."""
    if not governor_enabled():
        return {"kind": "governor_off", "healthy": None, "retry_no": None}
    with _lock:
        cap_h = healthy_call_cap()
        cap_r = retry_cap()
        if logical_key in _governor["seen_keys"]:
            if cap_r > 0 and _governor["retries"] >= cap_r:
                _governor["stops"].append(
                    {"kind": "RETRY_CAP_EXCEEDED", "key": logical_key[:12],
                     "at_retries": _governor["retries"]})
                with _lock:
                    _counters["governor_stops"] += 1
                _log_event("governor_stop", state="RETRY_CAP_EXCEEDED",
                           scope=_governor["scope"],
                           key=logical_key[:12],
                           retries=_governor["retries"])
                raise RetryCapExceeded(
                    f"RETRY_CAP_EXCEEDED: per-problem retry cap {cap_r} "
                    f"reached (scope={_governor['scope']}); the retry "
                    f"storm is bounded (Art. LXI)")
            _governor["retries"] += 1
            with _lock:
                _counters["governor_retries"] += 1
            return {"kind": "retry", "retry_no": _governor["retries"],
                    "healthy": _governor["healthy"]}
        if cap_h > 0 and _governor["healthy"] >= cap_h:
            _governor["stops"].append(
                {"kind": "HEALTHY_CALL_CAP_EXCEEDED",
                 "key": logical_key[:12], "at_healthy": _governor["healthy"]})
            with _lock:
                _counters["governor_stops"] += 1
            _log_event("governor_stop", state="HEALTHY_CALL_CAP_EXCEEDED",
                       scope=_governor["scope"], key=logical_key[:12],
                       healthy=_governor["healthy"])
            raise HealthyCallCapExceeded(
                f"HEALTHY_CALL_CAP_EXCEEDED: per-problem healthy-call cap "
                f"{cap_h} reached (scope={_governor['scope']}); a problem "
                f"never spends more than {cap_h} logical calls (Art. LXI)")
        _governor["healthy"] += 1
        _governor["seen_keys"].add(logical_key)
        with _lock:
            _counters["governor_healthy"] += 1
        return {"kind": "healthy", "healthy_no": _governor["healthy"],
                "retry_no": _governor["retries"]}


# ---------------------------------------------------------------------------
# A2: per-provider circuit breaker (N consecutive transient failures)


_breakers: Dict[str, Dict[str, Any]] = {}


def breaker_check(provider_id: str) -> None:
    """Raise typed BreakerOpen while the provider is open (cooldown not
    elapsed). A closed/half-open provider passes silently."""
    if not breaker_enabled() or breaker_threshold() <= 0:
        return
    st = _breakers.get(provider_id)
    if not st or not st.get("open"):
        return
    now = time.monotonic()
    if now >= st["opened_at"] + st["cooldown_s"]:
        # cooldown elapsed: HALF-OPEN — one probe attempt is allowed; if it
        # fails, record_failure re-opens with the (doubled) cooldown
        st["open"] = False
        st["half_open"] = True
        _log_event("breaker_half_open", provider=provider_id)
        return
    with _lock:
        _counters["breaker_refusals"] += 1
    _log_event("breaker_refusal", provider=provider_id,
               cooldown_left_s=round(
                   st["opened_at"] + st["cooldown_s"] - now, 1))
    raise BreakerOpen(
        f"BREAKER_OPEN: provider '{provider_id}' hit "
        f"{st['consecutive']} consecutive transient failures; refused "
        f"for another {round(st['opened_at'] + st['cooldown_s'] - now, 1)}s "
        f"(retry-storm circuit breaker, Art. LXI)")


def breaker_failure(provider_id: str) -> bool:
    """Record ONE transient failure. Returns True if the breaker JUST
    opened (the caller aborts its retry ladder immediately — no further
    hammering)."""
    if not breaker_enabled() or breaker_threshold() <= 0:
        return False
    now = time.monotonic()
    st = _breakers.setdefault(provider_id, {
        "consecutive": 0, "open": False, "half_open": False,
        "opened_at": 0.0, "cooldown_s": breaker_cooldown_s()})
    if st.get("half_open"):
        # the probe failed: re-open with a DOUBLED cooldown (AIMD-flavored,
        # capped) — a provider that will not recover keeps costing less
        st["cooldown_s"] = min(st["cooldown_s"] * 2,
                               _BREAKER_COOLDOWN_MAX_S)
        st["open"] = True
        st["half_open"] = False
        st["opened_at"] = now
        with _lock:
            _counters["breaker_opens"] += 1
        _log_event("breaker_reopen", provider=provider_id,
                   cooldown_s=st["cooldown_s"])
        return True
    st["consecutive"] += 1
    if st["consecutive"] >= breaker_threshold() and not st["open"]:
        st["open"] = True
        st["opened_at"] = now
        st["cooldown_s"] = breaker_cooldown_s()
        with _lock:
            _counters["breaker_opens"] += 1
        _log_event("breaker_open", provider=provider_id,
                   consecutive=st["consecutive"],
                   cooldown_s=st["cooldown_s"])
        return True
    return False


def breaker_success(provider_id: str) -> None:
    st = _breakers.get(provider_id)
    if st:
        st["consecutive"] = 0
        st["open"] = False
        st["half_open"] = False
        st["cooldown_s"] = breaker_cooldown_s()


def breaker_state(provider_id: str) -> Dict[str, Any]:
    st = _breakers.get(provider_id) or {}
    return {"provider": provider_id,
            "open": bool(st.get("open")),
            "half_open": bool(st.get("half_open")),
            "consecutive_transient_failures": st.get("consecutive", 0),
            "cooldown_s": st.get("cooldown_s")}


# ---------------------------------------------------------------------------
# counters / snapshot


def reset_run_counters(scope: str) -> None:
    """Fresh per-run counter state; the on-disk cache store persists."""
    with _lock:
        for k in _counters:
            _counters[k] = 0
    reset_governor(scope)


def snapshot() -> Dict[str, Any]:
    with _lock:
        snap = {
            "instrument": "llm_economy/1.0",
            "cache_mode": cache_mode(),
            "store_root": str(econ_root()),
            "counters": dict(_counters),
            "governor": {
                "enabled": governor_enabled(),
                "scope": _governor["scope"],
                "healthy_calls": _governor["healthy"],
                "retry_attempts": _governor["retries"],
                "stops": list(_governor["stops"]),
                "healthy_call_cap": healthy_call_cap(),
                "retry_cap": retry_cap(),
            },
            "breakers": [breaker_state(p) for p in sorted(_breakers)],
            "breaker_threshold": breaker_threshold(),
        }
    return snap

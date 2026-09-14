"""discovery_fabric/engine/provider_health.py — R414 provider resilience.

Operator directive (product integration, sections 6-10):
  - NVIDIA and OpenRouter (and every other provider) are server-side
    secrets; a provider failure must not make the product appear dead.
  - Automatic failover MODEL A -> MODEL B -> MODEL C, but a provider
    failure is NEVER silently treated as successful model output.
  - Failures are classified: RATE_LIMITED / TIMEOUT / AUTH_FAILURE /
    NETWORK_FAILURE / INVALID_RESPONSE / MODEL_FAILURE / PARSER_FAILURE /
    GONE / CREDIT_EXHAUSTED / UNKNOWN — rate limits are distinguished
    from empty results; a retired model (410) and an unaffordable
    request (402) are distinguished from a malformed response.
  - Per-provider health (status, last_success, latency, rate_limit_state,
    model_count) is exposed through /api/health.

Constitutional contract (Art. XVIII, XXI.3, XXV, LXI):
  - A provider outage is an infrastructure fact, never a scientific
    verdict; the caller keeps deciding what a failed call MEANS.
  - Health state is only ever built from REAL call outcomes recorded at
    call time — never from configuration optimism (a configured key is
    UNAVAILABLE-OR-OK until a call proves which; we report NEVER_CALLED
    honestly rather than pretending "healthy").
  - The rate-limit cooldown is an ORDERING hint, never a hard block: a
    cooled provider is demoted in the failover chain, not removed, so
    the engine never refuses to run just because the book thinks a
    quota window is open (Art. V: fail closed on evidence, but do not
    become a universal rejector).

R415 amendment (P0 directive section 1 — the 410 root cause):
  - HTTP 410 GONE becomes a DISTINCT failure class and provider-health
    state. Before this amendment a 410 fell into INVALID_RESPONSE —
    converting a knowable fact (the provider retired this model/
    endpoint: the registry's own policy note records NVIDIA returning
    410 for retired models, verified 2026-08-27) into a vaguer class.
    That is the machine-level root cause of the production
    ERROR_TRANSPORT surface: a retired pinned model answered 410 on
    every call and the registry had no model-level fallback. GONE is
    recorded per (provider, model) by the R415 routing registry and the
    model is demoted from the eligible ladder (a retired model is
    KNOWN-DEAD from the provider's own response — not a heuristic);
    the PROVIDER stays eligible with its other models (Art. V).
"""
from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
HEALTH_DIR = REPO_ROOT / "ENGINE_RUNS" / "provider_health"

# ---------------------------------------------------------------------------
# The failure taxonomy (operator directive section 8 — exact vocabulary;
# R415: + GONE per the P0 directive section 1 — "410 GONE must become a
# distinct provider-health state". This EXTENDS the vocabulary; it never
# reclassifies an existing member)
# ---------------------------------------------------------------------------
RATE_LIMITED = "RATE_LIMITED"
TIMEOUT = "TIMEOUT"
AUTH_FAILURE = "AUTH_FAILURE"
NETWORK_FAILURE = "NETWORK_FAILURE"
INVALID_RESPONSE = "INVALID_RESPONSE"
MODEL_FAILURE = "MODEL_FAILURE"
PARSER_FAILURE = "PARSER_FAILURE"
GONE = "GONE"                   # R415: HTTP 410 — resource retired
# R436: HTTP 402 — the provider's own response says the account cannot
# afford the request (credit/token budget exhausted). Before this
# amendment a 402 fell into INVALID_RESPONSE via the HTTPError
# catch-all — the same pre-R415 pattern 410 had. This EXTENDS the
# vocabulary the same way R415 extended it for GONE; it never
# reclassifies an existing member. The distinction is diagnostic
# honesty (Art. XV): an operator reading failure_class=CREDIT_EXHAUSTED
# knows retrying and waiting cannot fix it and where to look (the
# wallet), while INVALID_RESPONSE pointed at the models — the exact
# misdiagnosis carried by the production RUN_BLOCKED_TRANSPORT record
# ts_bf144222321f (2026-09-08T21:53Z, root-caused R436 §1: OpenRouter
# 402 "can only afford 0 tokens" on every rung of the ladder).
CREDIT_EXHAUSTED = "CREDIT_EXHAUSTED"
# R451-C1.2 (operator transport-capability directive): HTTP 404 / a
# provider error body saying the MODEL IDENTIFIER does not exist on
# that route ("model_not_found", "unknown model", ...). Before this
# amendment the R450 production defect fell here: the stale glm-4-plus
# id on the HF router answered model_not_found and was classified
# INVALID_RESPONSE — pointing at the response shape when the knowable
# fact was "this identifier is permanently invalid on this route".
# This EXTENDS the vocabulary the same way R415 extended it for GONE
# and R436 for CREDIT_EXHAUSTED; it never reclassifies an existing
# member. The distinction is action-bearing (directive: "never retry
# a permanently invalid model identifier"): MODEL_NOT_FOUND marks the
# (provider, model) rung dead in the routing state — the provider's
# OTHER models stay eligible (Art. V).
MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
UNKNOWN = "UNKNOWN"

FAILURE_TYPES = (RATE_LIMITED, TIMEOUT, AUTH_FAILURE, NETWORK_FAILURE,
                 INVALID_RESPONSE, MODEL_FAILURE, PARSER_FAILURE, GONE,
                 CREDIT_EXHAUSTED, MODEL_NOT_FOUND, UNKNOWN)

# Cooldown ladder for rate limits (seconds). A rate-limited provider is
# demoted (not removed) for this long; repeated consecutive rate limits
# walk up the ladder. Deterministic policy input (Art. XXVII): the values
# encode "wait out the measured ~60 s quota window, then back off harder
# if it keeps happening" from the 2026-08-30 gateway measurements.
_COOLDOWN_LADDER_S = (60, 120, 240, 600)

_RATE_HINTS = ("429", "too many requests", "rate limit", "rate_limit",
               "quota", "exceeded your current quota",
               "requests per minute", "rpm limit")
_AUTH_HINTS = ("401", "403", "unauthorized", "unauthorised",
               "invalid api key", "invalid_api_key", "authentication",
               "permission denied", "insufficient_user_quota")
# R451-C1.2: the provider's own words for "this model id does not
# exist here". These hints classify the 200-body error envelope the
# HF router returns (measured R450: glm-4-plus -> "model_not_found"
# inside a successful HTTP exchange) — the exact case INVALID_RESPONSE
# misdiagnosed.
_MODEL_NOT_FOUND_HINTS = ("model not found", "model_not_found",
                          "no such model", "unknown model",
                          "model does not exist", "does not exist",
                          "invalid model", "model_id not found")
# R451-C1.2: the provider's own words for "this account cannot pay" —
# the HF router's measured 402 wording is the canonical specimen
# (R450: 'You have depleted your monthly included credits. Purchase
# pre-paid credits to continue using Inference Providers.'). Checked
# BEFORE the rate hints: 'quota' is ambiguous between rate windows
# and credit balances, these strings are not.
_CREDIT_HINTS = ("depleted your monthly included credits",
                 "purchase pre-paid credits", "insufficient credits",
                 "credit balance is", "out of credits",
                 "payment required", "billing hard limit",
                 # R456-A3 measured free-tier router specimens
                 "insufficient balance", "deposit required",
                 "deposited balance",
                 # R461 bynara per-model plan-gate specimen
                 "plan does not include")
# R456-A3: the free-tier routers' own words for "this model needs a
# deposit / the account cannot pay" — MEASURED specimens (2026-09-14):
#   xkiro 403: "requires real deposited balance — it is billed from
#               your [wallet]"
#   b.ai 403:  "Deposit required to unlock premium models"
#   b.ai 400:  "credit insufficient balance: balance=0 required=2406"
# R461 bynara specimens (2026-09-15, post-telegram-join):
#   bynara 403: "Your plan does not include the requested model."
#               (per-model PLAN gate — the xkiro deposit-gate class:
#               valid key, gated model, cascade advances, provider
#               stays eligible)
# Unambiguous credit/plan wording — checked BEFORE the 401/403 auth
# shortcut so a deposit-gated model classifies CREDIT_EXHAUSTED (the
# cascade advances to the next rung/provider; the provider stays
# eligible — the gate is per-model, not per-key)
_FREE_TIER_CREDIT_HINTS = ("insufficient balance", "deposit required",
                            "deposited balance",
                            "plan does not include")
# R461: bynara's ACCOUNT-ENTRY GATE specimen (measured 2026-09-14,
# pre-owner-action): 403 "telegram_required: Join the required
# Telegram group/channel and relink at /settings to continue." The
# KEY is valid; the ACCOUNT must take the provider's entry action.
# The owner RESOLVED it 2026-09-15 (telegram joined — R461/
# BYNARA_OWNER_ACTION_ESCALATION.json). If it RECURS, the honest
# action-bearing reading is the account-gate class (CREDIT_EXHAUSTED
# family: retrying and waiting cannot fix it; the fix is at the
# provider's settings page, not the wallet and not the key) — the
# cascade advances and the escalation record tells the operator the
# exact relink action. Never AUTH_FAILURE: the key is valid.
_ACCOUNT_ENTRY_GATE_HINTS = ("telegram_required", "relink at")
# R456-A3: unorouter's free-pool congestion wording (403 body — the
# provider's own remedy is 'switch to another model'):
#   "This model is busy right now (free providers hit their rate
#    limit). Please try again in a little while, or switch to another
#    model." — RATE_LIMITED (cooldown demotion + cascade advance),
# never AUTH_FAILURE (the key is valid; the pool is busy)
_FREE_TIER_RATE_HINTS = ("hit their rate limit",)
_TIMEOUT_HINTS = ("timed out", "timeout", "timeouterror",
                  "socket timeout", "deadline exceeded", "sigkilled")
_NETWORK_HINTS = ("connection refused", "connection reset",
                  "connection aborted", "name or service not known",
                  "temporary failure in name resolution",
                  "no route to host", "network", "ssl", "certificate",
                  "urlopen error", "broken pipe")


def classify_failure(exc: BaseException, http_status: Optional[int] = None,
                     body_snippet: str = "") -> str:
    """Map one exception (plus whatever HTTP context the caller captured)
    onto the eight-value taxonomy. Deterministic string classification:
    HTTP status first, then the exception type, then message hints. An
    unmapped failure stays UNKNOWN — never forced into a confident class
    (Art. XXV)."""
    msg = f"{type(exc).__name__}: {exc}".lower()
    status = http_status
    # R456-A3: HTTPError is file-like — the provider's own error BODY is
    # readable here (once, best-effort). The measured free-tier router
    # specimens carry their credit/rate wording in the 403/400 BODY (the
    # exception's str is only 'HTTP Error 403: Forbidden'), so the body
    # is merged into the hint text AND the code becomes the status —
    # every downstream branch (status shortcuts AND hint checks) sees
    # the provider's own words. Body read failure degrades to the
    # status-only classification (unchanged pre-R456 behavior).
    if isinstance(exc, urllib.error.HTTPError):
        _eb = ""
        try:
            _eb = exc.read().decode(errors="replace")[:400]
        except Exception:  # noqa: BLE001 — body is best-effort context
            _eb = ""
        if _eb:
            body_snippet = f"{body_snippet or ''} {_eb}".strip()
            msg = f"{msg} {_eb.lower()}".strip()
        if status is None:
            status = getattr(exc, "code", None)

    def _hints(hit: tuple) -> bool:
        text = " ".join([msg, str(body_snippet or "").lower()])
        return any(h in text for h in hit)

    if status == 429:
        return RATE_LIMITED
    if status in (401, 403):
        # R456-A3: free-tier router 403s carry credit/rate wording in
        # the BODY — the measured specimens classify correctly before
        # the auth shortcut (a valid key behind a deposit-gated model or
        # a busy free pool is NOT an auth failure). 401 stays strictly
        # AUTH: a failed key is a failed key whatever the body says.
        # R461: the bynara account-entry-gate specimen (telegram /
        # relink) classifies the same way — an account that must take
        # the provider's entry action is not a failed key.
        if status == 403 and _hints(_ACCOUNT_ENTRY_GATE_HINTS):
            return CREDIT_EXHAUSTED
        if status == 403 and _hints(_FREE_TIER_CREDIT_HINTS):
            return CREDIT_EXHAUSTED
        if status == 403 and _hints(_FREE_TIER_RATE_HINTS):
            return RATE_LIMITED
        return AUTH_FAILURE
    if status == 410:
        return GONE                  # R415: retired model/endpoint
    if status == 402:
        return CREDIT_EXHAUSTED      # R436: cannot afford the request
    if status == 404:
        return MODEL_NOT_FOUND       # R451-C1.2: the identifier is not
        #                              # served on this route (the call
        #                              # path's URLs are fixed config,
        #                              # so a 404 names the model)
    if _hints(_MODEL_NOT_FOUND_HINTS):
        return MODEL_NOT_FOUND       # R451-C1.2: router 200-body error
    if _hints(_CREDIT_HINTS):
        return CREDIT_EXHAUSTED      # R451-C1.2: 200-body credit wording
    if _hints(_RATE_HINTS):
        return RATE_LIMITED
    if status in (400, 422):
        # provider received the request and rejected the payload shape
        return INVALID_RESPONSE
    if _hints(_AUTH_HINTS):
        return AUTH_FAILURE
    if isinstance(exc, TimeoutError) or _hints(_TIMEOUT_HINTS):
        return TIMEOUT
    if isinstance(exc, (ConnectionError,)):
        return NETWORK_FAILURE
    if isinstance(exc, urllib.error.HTTPError):
        # HTTPError is a file-like object — the provider's own error
        # BODY is readable here. R456-A3: the free-tier routers answer
        # 403/400 with credit/rate wording in the body (measured
        # specimens above); the body is read ONCE, best-effort, and the
        # unambiguous wording classifies BEFORE the status shortcuts
        # (a valid key behind a deposit-gated model or a busy free pool
        # is NOT an auth failure — the cascade must advance)
        _body = ""
        try:
            _body = exc.read().decode(errors="replace")[:400]
        except Exception:  # noqa: BLE001 — body is best-effort context
            _body = ""
        _text = f"{msg} {_body}".lower()
        if any(h in _text for h in _FREE_TIER_CREDIT_HINTS):
            return CREDIT_EXHAUSTED
        if "hit their rate limit" in _text:
            return RATE_LIMITED
        # HTTPError is a URLError subclass — check it FIRST so the
        # provider's own status code wins over generic transport hints.
        code = getattr(exc, "code", None)
        if code == 429:
            return RATE_LIMITED
        if code in (401, 403):
            return AUTH_FAILURE
        if code == 410:
            return GONE              # R415: retired model/endpoint
        if code == 402:
            return CREDIT_EXHAUSTED  # R436: credits exhausted upstream
        if code == 404:
            return MODEL_NOT_FOUND   # R451-C1.2: identifier not served
        if code and code >= 500:
            return MODEL_FAILURE      # model service failed server-side
        if code is not None:
            return INVALID_RESPONSE
        return UNKNOWN
    if isinstance(exc, urllib.error.URLError):
        # URLError without an HTTP code is transport-level (DNS, TCP,
        # TLS); with a reason that mentions timeouts it is TIMEOUT.
        if _hints(_TIMEOUT_HINTS):
            return TIMEOUT
        return NETWORK_FAILURE
    if isinstance(exc, json.JSONDecodeError):
        return INVALID_RESPONSE
    if _hints(_NETWORK_HINTS):
        return NETWORK_FAILURE
    if isinstance(exc, RuntimeError) and "empty content" in msg:
        # the completion arrived but carried no usable content
        return MODEL_FAILURE
    if isinstance(exc, ValueError):
        return INVALID_RESPONSE
    return UNKNOWN


# ---------------------------------------------------------------------------
# The health book — per-provider state, persisted, thread-safe
# ---------------------------------------------------------------------------
class ProviderHealthBook:
    """Per-provider health state. RECORDED FROM REAL CALLS ONLY.

    state.json (atomic rewrite) carries the live snapshot;
    events.jsonl (append-only) carries every call outcome so any health
    claim is replayable from committed bytes (Art. XII, LXII). Both are
    best-effort: a persistence failure is disclosed in last_error and
    never crashes a discovery run (the book degrades to memory-only).
    """

    def __init__(self, health_dir: Optional[Path] = None):
        self._dir = Path(health_dir) if health_dir else HEALTH_DIR
        self._lock = threading.Lock()
        self._state: Dict[str, Dict[str, Any]] = {}
        self._last_error: Optional[str] = None
        self._load()

    # -- persistence -------------------------------------------------------
    def _load(self) -> None:
        try:
            p = self._dir / "state.json"
            if p.exists():
                data = json.loads(p.read_text())
                if isinstance(data.get("providers"), dict):
                    self._state = data["providers"]
        except Exception as exc:  # noqa: BLE001 — disclosed, non-fatal
            self._last_error = f"state load failed: {exc}"

    def _persist(self) -> None:
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            tmp = self._dir / "state.json.tmp"
            tmp.write_text(json.dumps(
                {"providers": self._state,
                 "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                             time.gmtime())},
                indent=1, sort_keys=True))
            tmp.replace(self._dir / "state.json")
            self._last_error = None
        except Exception as exc:  # noqa: BLE001
            self._last_error = f"state persist failed: {exc}"

    def _append_event(self, event: Dict[str, Any]) -> None:
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            with open(self._dir / "events.jsonl", "a") as fh:
                fh.write(json.dumps(event, sort_keys=True) + "\n")
        except Exception as exc:  # noqa: BLE001
            self._last_error = f"event append failed: {exc}"

    # -- recording ---------------------------------------------------------
    def _entry(self, provider_id: str) -> Dict[str, Any]:
        return self._state.setdefault(provider_id, {
            "call_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "consecutive_failures": 0,
            "consecutive_rate_limits": 0,
            "last_call_at": None,
            "last_success_at": None,
            "last_failure_at": None,
            "last_failure_type": None,
            "last_latency_ms": None,
            "latency_ema_ms": None,
            "cooldown_until_epoch": 0.0,
        })

    def record_success(self, provider_id: str, latency_ms: int,
                       purpose: str = "", model: str = "") -> None:
        with self._lock:
            e = self._entry(provider_id)
            e["call_count"] += 1
            e["success_count"] += 1
            e["consecutive_failures"] = 0
            e["consecutive_rate_limits"] = 0
            e["cooldown_until_epoch"] = 0.0
            e["last_call_at"] = time.time()
            e["last_success_at"] = time.time()
            e["last_latency_ms"] = int(latency_ms)
            ema = e.get("latency_ema_ms")
            if ema is None:
                e["latency_ema_ms"] = float(latency_ms)
            else:
                e["latency_ema_ms"] = round(
                    0.7 * float(ema) + 0.3 * float(latency_ms), 1)
            event = {"provider": provider_id, "ok": True,
                     "latency_ms": int(latency_ms), "purpose": purpose,
                     "model": model,
                     "at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                         time.gmtime())}
        self._append_event(event)
        self._persist()

    def record_failure(self, provider_id: str, failure_type: str,
                       purpose: str = "", model: str = "",
                       error: str = "") -> None:
        if failure_type not in FAILURE_TYPES:
            failure_type = UNKNOWN
        cooldown_s = 0.0
        with self._lock:
            e = self._entry(provider_id)
            e["call_count"] += 1
            e["failure_count"] += 1
            e["consecutive_failures"] += 1
            e["last_call_at"] = time.time()
            e["last_failure_at"] = time.time()
            e["last_failure_type"] = failure_type
            if failure_type == RATE_LIMITED:
                e["consecutive_rate_limits"] += 1
                idx = min(e["consecutive_rate_limits"],
                          len(_COOLDOWN_LADDER_S)) - 1
                cooldown_s = float(_COOLDOWN_LADDER_S[max(0, idx)])
                e["cooldown_until_epoch"] = time.time() + cooldown_s
            else:
                e["consecutive_rate_limits"] = 0
            event = {"provider": provider_id, "ok": False,
                     "failure_type": failure_type, "purpose": purpose,
                     "model": model, "error": error[:300],
                     "cooldown_s": cooldown_s,
                     "at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                         time.gmtime())}
        self._append_event(event)
        self._persist()

    # -- queries -----------------------------------------------------------
    def in_cooldown(self, provider_id: str) -> bool:
        with self._lock:
            e = self._state.get(provider_id)
            if not e:
                return False
            return float(e.get("cooldown_until_epoch") or 0) > time.time()

    def cooldown_remaining_s(self, provider_id: str) -> float:
        with self._lock:
            e = self._state.get(provider_id)
            if not e:
                return 0.0
            return max(0.0, float(e.get("cooldown_until_epoch") or 0)
                       - time.time())

    def last_failure_type(self, provider_id: str) -> Optional[str]:
        with self._lock:
            e = self._state.get(provider_id)
            return (e or {}).get("last_failure_type")

    def recent_failure_rate(self, provider_id: str,
                            window: int = 10) -> Optional[float]:
        """Failures / calls over the last `window` calls, or None when
        fewer than 2 calls were ever made (insufficient evidence is not
        a 0.0 rate — Art. XXV)."""
        with self._lock:
            e = self._state.get(provider_id)
            if not e:
                return None
            n = min(int(e.get("call_count") or 0), window)
            if n < 2:
                return None
            fails = min(int(e.get("failure_count") or 0), n)
            return round(fails / n, 3)

    def snapshot(self, provider_specs: Optional[List[Dict]] = None,
                 available_ids: Optional[List[str]] = None) -> List[Dict]:
        """The /api/health providers[] array. provider_specs comes from
        llm_registry.availability_matrix() so model/tier info is the
        registry's own recorded policy input, not a second truth."""
        out: List[Dict] = []
        specs = provider_specs or []
        avail = set(available_ids or
                    [s.get("provider_id") for s in specs
                     if s.get("available")])
        with self._lock:
            state = {k: dict(v) for k, v in self._state.items()}
        for spec in specs:
            pid = spec.get("provider_id")
            e = state.get(pid, {})
            has_key = bool(spec.get("available"))
            called = int(e.get("call_count") or 0)
            cooling = self.in_cooldown(pid)
            if not has_key:
                status = "UNAVAILABLE"          # no credential (env truth)
            elif called == 0:
                status = "NEVER_CALLED"         # configured, unproven
            elif cooling:
                status = "RATE_LIMITED"
            elif e.get("last_failure_type") == GONE and \
                    e.get("last_failure_at") and \
                    (e.get("last_success_at") or 0) < \
                    (e.get("last_failure_at") or 0):
                # R415 (directive section 1/6): 410 GONE is its own
                # provider-health state — the last call hit a retired
                # resource. The PROVIDER is not dead (other models may
                # serve); this state says exactly what was measured.
                status = "GONE"
            elif e.get("last_failure_at") and \
                    (e.get("last_success_at") or 0) < \
                    (e.get("last_failure_at") or 0):
                status = "DEGRADED"
            else:
                status = "OK"   # R414 vocabulary (UI + tests pin it); the
                # directive section-6 HEALTHY/... vocabulary lives in the
                # R415 routing registry's provider summary
            out.append({
                "provider": pid,
                "status": status,
                "available": has_key,
                "model": spec.get("model"),
                "model_count": 1,  # the engine's configured model per
                # provider; router-style providers still expose exactly
                # the one model this engine is pinned to (honest count)
                "quality_tier": spec.get("quality_tier"),
                "cost_tier": spec.get("cost_tier"),
                "latency_tier": spec.get("latency_tier"),
                "context_window": spec.get("context_capacity_tokens"),
                "last_success": (
                    time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(
                        float(e.get("last_success_at") or 0)))
                    if e.get("last_success_at") else None),
                "last_failure": (
                    time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(
                        float(e.get("last_failure_at") or 0)))
                    if e.get("last_failure_at") else None),
                "last_failure_type": e.get("last_failure_type"),
                "latency_ms": e.get("last_latency_ms"),
                "latency_ema_ms": e.get("latency_ema_ms"),
                "call_count": called,
                "failure_count": e.get("failure_count"),
                "recent_failure_rate": self.recent_failure_rate(pid),
                "rate_limit_state": (
                    f"COOLDOWN_{int(self.cooldown_remaining_s(pid))}S"
                    if cooling else "CLEAR"),
            })
        self._last_error and out.append({
            "provider": "_book", "status": "PERSISTENCE_DEGRADED",
            "note": self._last_error[:200],
        })
        return out

    def diagnostics(self) -> Dict[str, Any]:
        with self._lock:
            return {"providers_tracked": len(self._state),
                    "last_persistence_error": self._last_error,
                    "health_dir": str(self._dir)}


# Module-level singleton — one book per process, shared by the registry,
# the health endpoint and the worker. Tests construct their own instance
# with a temp dir (Art. IX: certification must not touch production
# state; the singleton is never written by tests).
HEALTH = ProviderHealthBook()


# ---------------------------------------------------------------------------
# The deterministic role router (operator directive section 7)
# ---------------------------------------------------------------------------
ROLE_SYNTHESIS = "synthesis"        # complex mechanism reasoning
ROLE_EXTRACTION = "extraction"      # fast evidence extraction
ROLE_ATTACK = "attack"              # adversarial review
ROLE_TRANSFORM = "transform"        # simple JSON shaping (prefer no LLM)

_PURPOSE_ROLE_HINTS = {
    # purposes in use across the engine (grep-verified) -> roles
    "structured_evidence_extraction": ROLE_EXTRACTION,
    "structured_evidence_extraction_retry": ROLE_EXTRACTION,
    "independent_attack": ROLE_ATTACK,
    "ensemble_invention": ROLE_SYNTHESIS,
    "mechanism_space": ROLE_SYNTHESIS,
    "improvement_mutation_proposal": ROLE_SYNTHESIS,
    "technical_mutation_proposal": ROLE_SYNTHESIS,
    "technical_state_extraction": ROLE_EXTRACTION,
    "cad_build_program_proposal": ROLE_SYNTHESIS,
    "diversity_exploration": ROLE_SYNTHESIS,
}


def role_for_purpose(purpose: str) -> str:
    p = (purpose or "").lower()
    for hint, role in _PURPOSE_ROLE_HINTS.items():
        if hint in p:
            return role
    if "attack" in p or "adversar" in p:
        return ROLE_ATTACK
    if "extract" in p:
        return ROLE_EXTRACTION
    return ROLE_SYNTHESIS


def order_for_role(matrix: List[Dict[str, Any]], role: str,
                   avoid_provider: Optional[str] = None,
                   book: Optional[ProviderHealthBook] = None) -> List[str]:
    """Deterministic provider ORDER for one role. Inputs: the registry's
    own availability matrix (availability, tiers, context capacity) and
    the health book (cooldown, recent failure rate). Ordering rules:

      attack     : providers != avoid_provider first (Art. XLV
                   SEPARATE_PROVIDER when the chain actually lands on
                   one), then quality, then latency.
      extraction : latency tier, then cost, then quality (fast/cheap
                   first — the operator's routing table).
      transform  : cost tier, then latency.
      synthesis  : quality tier, then cost, then latency (the registry
                   default).

    Cooldown demotion (never removal) applies to every role: a
    rate-limited provider slides to the end so the cascade tries the
    healthy path first without ever refusing to run (Art. V).
    """
    b = book or HEALTH
    avail = [m for m in matrix if m.get("available")]

    def _rank(m: Dict[str, Any]) -> tuple:
        if role == ROLE_ATTACK:
            first = 0 if m["provider_id"] != avoid_provider else 1
            return (first, m["quality_tier"], m["latency_tier"],
                    m["cost_tier"])
        if role == ROLE_EXTRACTION:
            return (m["latency_tier"], m["cost_tier"], m["quality_tier"])
        if role == ROLE_TRANSFORM:
            return (m["cost_tier"], m["latency_tier"], m["quality_tier"])
        return (m["quality_tier"], m["cost_tier"], m["latency_tier"])

    ranked = sorted(avail, key=_rank)
    order = [m["provider_id"] for m in ranked]
    cooled = [p for p in order if b.in_cooldown(p)]
    if cooled and len(order) > 1:
        order = [p for p in order if p not in cooled] + cooled
    return order


def independence_degree(generator_provider: Optional[str],
                        attacker_provider: Optional[str]) -> str:
    """Art. XLV vocabulary for the generator/attacker separation."""
    if not generator_provider or not attacker_provider:
        return "NOT_INDEPENDENT"
    if generator_provider != attacker_provider:
        return "SEPARATE_PROVIDER"
    return "SEPARATE_CONTEXT_ONLY"

"""discovery_fabric/engine/runtime_admission.py — R451-C1.3.

Operator directive (Production Transport Authority + Provenance Closure,
2026-09-13):

    CATALOG
       ↓
    CAPABILITY PROBE
       ↓
    MEASURED ROUTE STATE
       ↓
    COST POLICY
       ↓
    RUNTIME ADMISSION
       ↓
    ROUTING LADDER
       ↓
    CALL

    "llm_registry.generate() must not consider a route
    runtime-admissible merely because credential_present = true.
    A route requires a current measured successful capability probe.
    Use the existing TTL mechanism rather than probing every single
    call."

The five required states (closed vocabulary):

    NOT_PROBED       no capability measurement exists for the rung
    PROBE_OK         a current (within TTL) measured successful probe
    PROBE_FAILED     a current measured FAILED probe (typed class)
    PROBE_EXPIRED    a measurement exists but is older than the TTL
    POLICY_REFUSED   the probe is OK but the ACTIVE cost policy
                     refuses the provider (fail-closed, Art. IV/VII)

Only PROBE_OK + policy eligible can become runtime-admissible. The
LOCAL route uses the SAME rule — no bespoke local exception (the
directive's explicit constraint, test-enforced).

Mechanics:
  * The capability probe is ONE tiny completion through the rung's REAL
    transport (the same _call_openai_flavor/_call_anthropic_flavor the
    engine's real calls use — never a separate HTTP path) with THIS
    environment's credential state.
  * The TTL mechanism is the EXISTING one (model_routing.PROBE_TTL_S —
    the R415 health-probe cache pattern: epoch-aged records, expired ==
    stale, invalidated immediately after failures). Capability records
    are ALSO refreshed by successful real calls (a successful call is a
    STRONGER measurement of the same capability — recorded with
    source='real_call') and invalidated after real-call transport
    failures (the R415 clear_probe_cache discipline: the next admission
    re-probes instead of trusting a stale success).
  * Probe attempts are persisted BOTH in the capability store
    (ENGINE_RUNS/transport_capability/capability_state.json —
    replayable committed bytes) and in the MODEL_ROUTING_LEDGER with
    call_class='CAPABILITY_PROBE' and run_id=None — provider capability
    probes are NOT run-owned discovery calls (the directive's own
    distinction), so they legitimately carry no run_id while
    run-owned calls must never be null (the C1.3-3 invariant).

Constitutional contract (Art. III, IV, V, VII, XXV, LXI):
  - A credential present is a CONFIGURATION fact, never a capability
    measurement (BS-028's "model availability assumed static" and the
    R451-C1.2 "catalog is not entitlement" rule, now applied to the
    RUNTIME path itself).
  - POLICY_REFUSED is fail-closed: a probing-successful paid route is
    measured capability, refused routing — never silently widened.
  - This module is TRANSPORT authority only: its states never classify
    discovery outcomes (Art. LXI — a probe failure is a transport fact;
    the conductor keeps deciding what a blocked call MEANS).
  - No verifier, gate, threshold, or epistemic semantics is modified
    here (Art. VII): this is routing-layer machinery only.
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
CAPABILITY_DIR = REPO_ROOT / "ENGINE_RUNS" / "transport_capability"
CAPABILITY_STATE_PATH = CAPABILITY_DIR / "capability_state.json"

# ---------------------------------------------------------------------------
# The closed state vocabulary (operator directive C1.3-1)
# ---------------------------------------------------------------------------
ST_NOT_PROBED = "NOT_PROBED"
ST_PROBE_OK = "PROBE_OK"
ST_PROBE_FAILED = "PROBE_FAILED"
ST_PROBE_EXPIRED = "PROBE_EXPIRED"
ST_POLICY_REFUSED = "POLICY_REFUSED"

CAPABILITY_STATES = (ST_NOT_PROBED, ST_PROBE_OK, ST_PROBE_FAILED,
                     ST_PROBE_EXPIRED, ST_POLICY_REFUSED)

#: the probe TTL — the EXISTING mechanism (model_routing.PROBE_TTL_S,
#: the R415 health-probe cache): a record older than the TTL is stale
#: and the route requires a fresh probe. Reused verbatim so there is
#: ONE TTL authority (Art. X); a capability record refreshed by a
#: successful real call extends the same window (a real call is a
#: stronger measurement of the same capability).
def capability_ttl_s() -> float:
    try:
        from .model_routing import PROBE_TTL_S
        return float(PROBE_TTL_S)
    except Exception:  # noqa: BLE001 — absent stays the default
        return 300.0


RUNTIME_ADMISSION_VERSION = "runtime_admission/1.1.0"

#: failure re-probe floor (recorded policy input, Art. XXVII): a FAILED
#: probe ages out of "current" faster than a successful one — failures
#: are noisy (transient outages), successes are stable. After the floor
#: the next admission re-probes instead of trusting the failure for the
#: full success TTL. This preserves the directive's "no per-call
#: probing" (a failing route is probed at most once per floor window)
#: while a transient outage cannot lock a route out for the whole TTL
#: (the R451-C1.3 acceptance's measured defect: a ~5 s llama-server
#: restart window poisoned the route for 300 s and transport-blocked
#: the ATTACK stage's evaluator call).
PROBE_FAILURE_FLOOR_S = 30.0

#: transient failure classes (the provider-health taxonomy's own
#: vocabulary): a probe failing with one of these may be RETRIED within
#: the SAME bounded walk (the old cascade's transient absorption,
#: applied to the admission authority). The permanent classes
#: (AUTH_FAILURE, GONE, MODEL_NOT_FOUND, CREDIT_EXHAUSTED, and R462's
#: REGION_NOT_SERVED — a region-gated endpoint answers identically on
#: every retry from the same egress) are never retried — never retry a
#: permanently invalid route.
TRANSIENT_PROBE_CLASSES = ("NETWORK_FAILURE", "TIMEOUT", "RATE_LIMITED")

_STATE_LOCK = threading.Lock()
_STATE_PATH_OVERRIDE: Optional[Path] = None


def _state_path() -> Path:
    return _STATE_PATH_OVERRIDE or CAPABILITY_STATE_PATH


def set_state_path(path: Optional[Path]) -> None:
    """Test/sealed-run redirection (Art. IX: production capability
    state is never touched by tests)."""
    global _STATE_PATH_OVERRIDE
    _STATE_PATH_OVERRIDE = Path(path) if path else None


def _load_state() -> Dict[str, Any]:
    try:
        if _state_path().exists():
            data = json.loads(_state_path().read_text())
            if isinstance(data, dict):
                return data
    except Exception:  # noqa: BLE001 — corrupt state degrades to empty
        pass
    return {}


def _save_state(state: Dict[str, Any]) -> None:
    try:
        _state_path().parent.mkdir(parents=True, exist_ok=True)
        _state_path().write_text(
            json.dumps(state, indent=1, sort_keys=True))
    except Exception:  # noqa: BLE001 — best-effort telemetry, disclosed
        pass


def _rung_key(provider: str, model: str) -> str:
    return f"{provider}::{model}"


# ---------------------------------------------------------------------------
# The measured route state (the capability records)
# ---------------------------------------------------------------------------
def record_capability(provider: str, model: str, ok: bool,
                      latency_ms: int = 0,
                      failure_class: Optional[str] = None,
                      source: str = "probe",
                      fields_ok: Optional[bool] = None,
                      note: str = "") -> Dict[str, Any]:
    """Persist one capability measurement for (provider, model).

    source: 'probe' (the dedicated tiny completion) or 'real_call'
    (a successful engine call through the same transport — a STRONGER
    measurement of the same capability; refreshes the TTL window).
    """
    rec = {
        "provider": provider,
        "model": model,
        "ok": bool(ok),
        "latency_ms": int(latency_ms or 0),
        "failure_class": failure_class,
        "source": source,
        "fields_ok": fields_ok,
        "note": note[:200],
        "at_epoch": time.time(),
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "version": RUNTIME_ADMISSION_VERSION,
    }
    with _STATE_LOCK:
        state = _load_state()
        records = state.setdefault("capability_records", {})
        records[_rung_key(provider, model)] = rec
        _save_state(state)
    return rec


def invalidate_capability(provider: str, model: str,
                          reason: str = "") -> None:
    """Drop the capability record so the next admission RE-PROBES (the
    R415 clear_probe_cache discipline: never trust a stale success
    after a failure). A GONE/MODEL_NOT_FOUND dead-id mark is a
    separate, stronger exclusion handled by model_routing."""
    with _STATE_LOCK:
        state = _load_state()
        records = state.setdefault("capability_records", {})
        if _rung_key(provider, model) in records:
            del records[_rung_key(provider, model)]
            _save_state(state)


def capability_record(provider: str, model: str,
                      now: Optional[float] = None
                      ) -> Optional[Dict[str, Any]]:
    """The latest persisted capability measurement, or None."""
    now = now if now is not None else time.time()
    rec = (_load_state().get("capability_records")
           or {}).get(_rung_key(provider, model))
    if not isinstance(rec, dict):
        return None
    return rec


# ---------------------------------------------------------------------------
# The measured route state -> the five-state vocabulary
# ---------------------------------------------------------------------------
def capability_state(provider: str, model: str,
                     policy: Optional[str] = None,
                     now: Optional[float] = None) -> Dict[str, Any]:
    """Derive the rung's MEASURED ROUTE STATE (the closed five-state
    vocabulary). POLICY_REFUSED is derived here (probe OK + the cost
    policy refuses the provider) so callers never re-derive it."""
    from . import model_cost_policy as _cp
    now = now if now is not None else time.time()
    p = policy or _cp.active_policy()
    rec = capability_record(provider, model, now=now)
    if rec is None:
        return {"state": ST_NOT_PROBED, "record": None, "policy": p}
    age = now - float(rec.get("at_epoch") or 0)
    if age > capability_ttl_s():
        return {"state": ST_PROBE_EXPIRED, "record": rec, "policy": p,
                "age_s": round(age, 1)}
    if not rec.get("ok"):
        return {"state": ST_PROBE_FAILED, "record": rec, "policy": p,
                "age_s": round(age, 1)}
    # a current successful measurement: the cost policy decides
    try:
        from .llm_registry import _SPEC_BY_ID
        spec = _SPEC_BY_ID.get(provider)
    except Exception:  # noqa: BLE001 — registry not importable here
        spec = None
    ok, note = _cp.provider_eligibility(spec, p) if spec else (
        False, "unknown provider")
    if not ok:
        return {"state": ST_POLICY_REFUSED, "record": rec, "policy": p,
                "policy_note": note}
    return {"state": ST_PROBE_OK, "record": rec, "policy": p}


def requires_probe(provider: str, model: str,
                   now: Optional[float] = None) -> bool:
    """NOT_PROBED, PROBE_EXPIRED, or a PROBE_FAILED older than the
    failure floor -> the rung needs a fresh probe before it can be
    runtime-admissible (the failure aged out — failures are noisy,
    successes stable)."""
    now = now if now is not None else time.time()
    cap = capability_state(provider, model, now=now)
    st = cap["state"]
    if st in (ST_NOT_PROBED, ST_PROBE_EXPIRED):
        return True
    if st == ST_PROBE_FAILED:
        rec = cap.get("record") or {}
        age = now - float(rec.get("at_epoch") or 0)
        return age > PROBE_FAILURE_FLOOR_S
    return False


def probe_failure_is_transient(provider: str, model: str,
                               now: Optional[float] = None) -> bool:
    """The last probe failed with a TRANSIENT class (retryable within
    the same bounded walk — never the permanent classes)."""
    cap = capability_state(provider, model, now=now)
    if cap["state"] != ST_PROBE_FAILED:
        return False
    fc = (cap.get("record") or {}).get("failure_class")
    return fc in TRANSIENT_PROBE_CLASSES


# ---------------------------------------------------------------------------
# RUNTIME ADMISSION — the single common semantics (C1.7)
# ---------------------------------------------------------------------------
def runtime_admission(provider: str, model: str,
                      policy: Optional[str] = None,
                      now: Optional[float] = None,
                      available: Optional[bool] = None,
                      ) -> Tuple[bool, str, Dict[str, Any]]:
    """The ONE admission semantic shared by select_provider() and
    generate() (C1.7: no legacy selector with weaker rules):

        available
        AND cost_policy_eligible
        AND measured_capability_eligible (PROBE_OK within TTL)

    Returns (admitted, state_or_refusal_note, evidence). The evidence
    dict is persisted in ledgers/selection records (the acceptance
    gate: capability evidence is persisted)."""
    from . import model_cost_policy as _cp
    now = now if now is not None else time.time()
    p = policy or _cp.active_policy()
    if available is False:
        return (False, "UNAVAILABLE (no credential in this environment)",
                {"state": ST_NOT_PROBED, "policy": p})
    cap = capability_state(provider, model, policy=p, now=now)
    st = cap["state"]
    if st == ST_PROBE_OK:
        return True, st, cap
    if st == ST_POLICY_REFUSED:
        return (False,
                f"{st}: probe OK but "
                f"{cap.get('policy_note', 'cost policy refuses')}",
                cap)
    if st == ST_PROBE_FAILED:
        fc = (cap.get("record") or {}).get("failure_class") or "UNKNOWN"
        return (False, f"{st} (failure_class={fc})", cap)
    if st == ST_PROBE_EXPIRED:
        return (False, f"{st} (age {cap.get('age_s')}s > TTL "
                       f"{capability_ttl_s():.0f}s)", cap)
    return False, ST_NOT_PROBED, cap


# ---------------------------------------------------------------------------
# THE capability probe — one tiny completion through the rung's REAL
# transport with THIS environment's credential state
# ---------------------------------------------------------------------------
PROBE_PROMPT = ("Reply with exactly one line, nothing else:\n"
                "TRANSPORT: ready")


def probe_capability(provider: str, model: str,
                     timeout_s: int = 20,
                     max_tokens: int = 16,
                     stage: str = "CAPABILITY_PROBE",
                     purpose: str = "capability_probe",
                     persist_ledger: bool = True) -> Dict[str, Any]:
    """Measure one rung's capability: a tiny completion through the
    SAME call functions the engine's real calls use (never a second
    HTTP path — Art. X: one transport authority).

    The probe's success criterion is a NON-EMPTY completion (the
    R451-C1.1 ladder's 'tiny completion succeeds' rung — transport
    capability). The FIELD-line structured-output contract is recorded
    as additional evidence (fields_ok) without gating admission: a
    model that misses FIELD lines on a probe is measured honest extra
    evidence, not transport-dead.

    The probe attempt is recorded in the routing ledger with
    call_class='CAPABILITY_PROBE' and run_id=None — provider
    capability probes are NOT run-owned discovery calls (the C1.3-3
    distinction; the invariant test separates the two classes)."""
    from .llm_registry import (KEY_ROTATION_FAILURE_CLASSES,
                               EmptyContentWithFinish,
                               _SPEC_BY_ID, _call_anthropic_flavor,
                               _call_openai_flavor, active_key_slot,
                               key_ring_slots, rotate_key)
    spec = _SPEC_BY_ID.get(provider)
    out: Dict[str, Any] = {
        "probe_version": RUNTIME_ADMISSION_VERSION,
        "provider": provider,
        "model": model,
        "stage": stage,
        "call_class": "CAPABILITY_PROBE",
        "transport": spec.url_for_call() if spec else None,
    }
    if spec is None:
        out.update({"ok": False, "failure_class": "UNKNOWN_PROVIDER"})
        return out
    # R467: a reasoning model spends the whole probe budget on hidden
    # reasoning at 16 tokens and returns content=null — the probe must
    # spend the rung's OWN declared budget (default stays 16; atria
    # declares 256). The probe stays one tiny completion; this only
    # sizes it so a live rung is never refused for thinking. The `or
    # 16` guards a spec that ever leaves the field falsy — the probe
    # then keeps the standing default instead of raising past the typed
    # failure states (engineer review R467).
    max_tokens = max(int(max_tokens or 16),
                     int(getattr(spec, "probe_max_tokens", 16) or 16))
    messages = [
        {"role": "system", "content":
            "RESPOND IN ENGLISH ONLY. Follow the requested output "
            "format exactly; no preamble, no markdown fences."},
        {"role": "user", "content": PROBE_PROMPT},
    ]
    t0 = time.time()
    content = ""
    ftype: Optional[str] = None
    # R469: the probe rides the RING — an exhaustion-class failure on
    # the active key rotates to the next PRESENT slot and retries the
    # tiny completion (bounded by the ring size). Without this, a
    # probe with an exhausted head key would PROBE_FAILED the rung and
    # the walk would never reach generate()'s rotation — the admission
    # authority must share the ring discipline (one key-selection
    # authority, Art. X). Every rotation is recorded in the probe
    # record (never silent, Art. IV); a fully exhausted ring records
    # the typed failure exactly as before.
    key_rotations: List[Dict[str, Any]] = []
    cap_escalated = False
    probe_cap = max_tokens
    while True:
        try:
            if spec.flavor == "anthropic":
                content = _call_anthropic_flavor(
                    spec, messages, timeout_s, probe_cap,
                    model_override=model)
            else:
                content = _call_openai_flavor(
                    spec, messages, timeout_s, probe_cap,
                    model_override=model)
            ftype = None
            break
        except EmptyContentWithFinish as exc:
            # R469: the small-cap starvation specimen (R467 measured on
            # Atria-Dawn-Preview): a reasoning model can spend the
            # probe's whole budget — the declared probe_max_tokens
            # included — on hidden reasoning and return a 200 with
            # EMPTY content: transport-capable, content-starved (NOT a
            # key exhaustion: no ring rotation fires). The R467
            # recovery measurement: the SAME rung at max_tokens 2000
            # answers with clean content ("the small-cap starvation
            # specimen recovered at the larger cap"). Escalate ONCE
            # past the declared budget (recorded in the probe record,
            # never silent); the probe's success criterion stays a
            # NON-EMPTY completion.
            if not cap_escalated and probe_cap < 512:
                cap_escalated = True
                probe_cap = 2000
                continue
            from .provider_health import classify_failure
            ftype = classify_failure(exc)
            break
        except Exception as exc:  # noqa: BLE001 — typed, recorded
            from .provider_health import classify_failure
            ftype = classify_failure(exc)
            if ftype in KEY_ROTATION_FAILURE_CLASSES:
                _slot_from = active_key_slot(spec)
                _slot_to = rotate_key(spec)
                if _slot_to is not None:
                    key_rotations.append({
                        "from_slot": _slot_from,
                        "to_slot": _slot_to,
                        "failure_class": ftype,
                        "key_env_var": key_ring_slots(spec)[_slot_to],
                    })
                    continue
            break
    latency_ms = int((time.time() - t0) * 1000)
    ok = ftype is None and bool(content)
    fields_ok = None
    if ok:
        # honest extra evidence: the FIELD-line protocol shape (the
        # R451-C1.1 top rung) — recorded, never gating (see docstring)
        for line in content.splitlines():
            if line.strip().upper().startswith("TRANSPORT:"):
                fields_ok = True
                break
        else:
            fields_ok = False
    rec = record_capability(
        provider, model, ok=ok, latency_ms=latency_ms,
        failure_class=ftype, source="probe", fields_ok=fields_ok,
        note=(ftype or "completion ok")[:200])
    out.update({"ok": ok, "latency_ms": latency_ms,
                "failure_class": ftype,
                "fields_ok": fields_ok, "record": rec,
                # R469: the ring view — which slot served, which slots
                # were rotated past (recorded, never silent)
                "key_slot": active_key_slot(spec),
                "key_rotations": key_rotations,
                "attempts": 1 + len(key_rotations),
                # R469: the small-cap starvation recovery (R467
                # measured) — the one-shot probe cap escalation
                "cap_escalation": ({"from": max_tokens, "to": probe_cap}
                                   if cap_escalated else None)})
    if persist_ledger:
        try:
            from .model_routing import record_call_outcome
            record_call_outcome(
                provider, model, ok=ok, latency_ms=latency_ms,
                failure_type=ftype, task=None, stage=stage,
                run_id=None, attempt=1, cost_class=spec.cost_basis,
                selected=False, call_class="CAPABILITY_PROBE",
                account_domain=spec.account_domain,
                capability_state=("PROBE_OK" if ok else "PROBE_FAILED"),
                fallback_reason=(
                    "capability probe (call_class=CAPABILITY_PROBE, "
                    "not run-owned): "
                    + (ftype or "ok")), )
        except Exception:  # noqa: BLE001 — ledger is best-effort
            pass
    return out


# ---------------------------------------------------------------------------
# The ladder's capability view (for selection ledgers — persisted
# evidence, the acceptance gate)
# ---------------------------------------------------------------------------
def ladder_capability_evidence(rungs: List[Dict[str, Any]],
                               policy: Optional[str] = None,
                               now: Optional[float] = None
                               ) -> List[Dict[str, Any]]:
    """Per-rung measured-route-state summary for a ladder (persisted
    in selection ledgers). Reads only — performs NO probes."""
    out = []
    for r in rungs:
        cap = capability_state(r["provider"], r["model"],
                               policy=policy, now=now)
        out.append({
            "provider": r["provider"],
            "model": r["model"],
            "capability_state": cap["state"],
            "capability_source": (cap.get("record") or {}).get("source"),
            "capability_age_s": cap.get("age_s"),
        })
    return out

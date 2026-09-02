"""Source health checker — runs the 7-step proof chain per source.

CEO database-layer directive, per source:

    CONNECTOR EXISTS -> LIVE REQUEST WORKS -> RESPONSE PARSES ->
    NORMALIZATION WORKS -> PROVENANCE STORES -> RETRIEVAL LOG STORES ->
    HEALTH CHECK PASSES

and emits the measured status vocabulary (CEO directive 2026-08-30 #5,
mechanically honest):

    LIVE / DEGRADED / BLOCKED / NOT_INTEGRATED

Every BLOCKED status carries a machine-derived block_class (AUTH /
EGRESS / PROVIDER_RETIRED / REGISTRATION / HTTP_5XX / NETWORK /
METERED_WINDOW / CONNECTOR_IMPORT) derived from the measured request
status, HTTP code, and error signature by status_model.py — never
hand-assigned. The pre-2026-08-30 label `UNAVAILABLE` is the same state
family; it is interpreted through status_model.LEGACY_VOCABULARY_MAP
(Art. XI — history is not rewritten, the rename is recorded).

Constitutional anchors:
- Art. XXVI: no self-certification. The health checker is a MEASUREMENT
  INSTRUMENT: it records what happened when the source was queried. Its
  output is BUILDER-MEASURED and must be independently reproducible (the
  committed reporter script is the reproduction command).
- Art. XXI.3: a provider failure is recorded as the failure it is — it can
  never downgrade a source to 'fewer records' or upgrade to absence.
- Art. IX: the health check must not mutate production epistemic state; it
  only APPENDS to the retrieval log (custody of its own measurements).
- Art. XV: failures are reported as failures.

DEGRADED (defined, not invented — Art. XXVII):
  A source is DEGRADED when the provider ANSWERED (request reached it) but
  the answer is restricted: rate-limit/budget exhaustion (429), partial
  parse, or unusually high latency vs. its measured peers. The threshold
  'latency_ms > 10000' is an operational MODEL_DERIVED triage bound
  recorded with the report, not a claim about the provider's health.
"""

from __future__ import annotations

import importlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from discovery_fabric.source_registry.base import (
    STATUS_OK, STATUS_EMPTY, STATUS_RATE_LIMITED,
)
from discovery_fabric.source_registry.registry import SOURCE_REGISTRY

# Operational triage bound (MODEL_DERIVED, disclosed): a provider that
# answers but takes > 10 s for a 5-100 record probe is flagged DEGRADED
# (latency), not LIVE. This is a triage convention, not a claim about the
# provider's intrinsic health.
LATENCY_DEGRADED_MS = 10_000

DERIVATION = {
    "LIVE": "all 7 chain steps passed; provider answered with parseable, "
            "normalizable records (or a definitive zero)",
    "DEGRADED": "provider answered but restricted: rate-limit/budget, or "
                f"latency above the disclosed {LATENCY_DEGRADED_MS} ms triage bound",
    "BLOCKED": "connector exists; the live request could not be answered "
               "usefully — block_class (AUTH/EGRESS/PROVIDER_RETIRED/"
               "REGISTRATION/HTTP_5XX/NETWORK/METERED_WINDOW) is derived "
               "mechanically from the measured signature by status_model.py",
    "NOT_INTEGRATED": "no connector exists (registry records the gap; "
                      "README mentions are not integration — Art. XXI)",
}

# Legacy vocabulary note (Art. XI): artifacts before 2026-08-30 say
# UNAVAILABLE where this module now says BLOCKED (+ block_class).
from discovery_fabric.source_registry.status_model import (  # noqa: E402
    LEGACY_VOCABULARY_MAP, classify_block,
)

# Metered-source policy (Patent Bear class of providers):
# a live health probe costs provider quota (Patent Bear: 1 of 20 monthly
# requests), so automated probes are SUPPRESSED. Health is derived from the
# freshest live retrieval-log proof inside the metered window. This is a
# POLICY decision recorded here (Art. XXVII), not a provider fact; every
# derived status discloses the last-live-proof timestamp so a reader can
# judge its age. A source with NO live proof inside the window is
# UNAVAILABLE('no live proof') — never silently LIVE.
METERED_DERIVATION = {
    "LIVE": "metered source: 7 chain steps passed on the freshest live "
            "retrieval-log proof inside the metered window; live re-probe "
            "suppressed to protect provider quota",
    "DEGRADED": "metered source: freshest live proof shows provider "
                "rate/quota limit, or quota exhausted since (guard active)",
    "BLOCKED": "metered source: no live proof inside the metered "
               "window (quota-protected probe suppressed) — block_class "
               "METERED_WINDOW",
}


def _check_metered_source(source_id: str, metered: Dict[str, Any]) -> Dict[str, Any]:
    """Health for a provider-metered source WITHOUT a live probe.

    Reads the append-only retrieval log: the freshest entry with status
    OK/EMPTY (a live provider answer) inside the metered window is the
    last live proof. Quota state comes from the provider-reported
    rate_limit_remaining in the freshest entry that carries one (Art. VI:
    provider accounting, never an engine estimate).
    """
    from discovery_fabric.source_registry.retrieval_log import read_entries

    window_days = int(metered.get("metered_window_days", 31))
    window_start = datetime.now(timezone.utc) - timedelta(days=window_days)

    entries = read_entries(source_id=source_id)
    last_live = None
    last_quota = None
    for e in reversed(entries):
        if last_live is None and e.get("status") in (STATUS_OK, STATUS_EMPTY):
            try:
                ts = datetime.fromisoformat(e["timestamp"])
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts >= window_start:
                    last_live = e
            except (KeyError, ValueError):
                continue
        if e.get("rate_limit_remaining") not in (None, ""):
            last_quota = e
        if last_live is not None and last_quota is not None:
            break

    chain = {
        "connector_exists": True,
        "live_request_works": None,   # not re-executed (quota-protected)
        "response_parses": None,
        "normalization_works": None,
        "provenance_stores": None,
        "retrieval_log_stores": True,  # the proof lives IN the log
        "health_check_passes": None,
        "proof_kind": "last_live_measurement",
    }

    if last_live is None:
        return {
            "source_id": source_id,
            "status": "BLOCKED",
            "block": classify_block(metered_window=True),
            "chain": chain,
            "request_status": "NOT_PROBED",
            "error": (
                f"metered source: no live retrieval-log proof inside the "
                f"{window_days}-day metered window; live probe suppressed "
                "to protect provider quota — LIVE is not assertable "
                "without a real work-driven call (Art. VI/XXI)"
            ),
            "derivation": METERED_DERIVATION,
            "metered": {
                **metered,
                "last_quota_reported": (last_quota or {}).get("rate_limit_remaining"),
                "last_quota_at": (last_quota or {}).get("timestamp"),
            },
        }

    # Quota guard state: provider-reported remaining in the freshest usage
    remaining = None
    if last_quota is not None:
        try:
            remaining = int(str(last_quota.get("rate_limit_remaining")).strip())
        except (TypeError, ValueError):
            remaining = None

    status = "LIVE"
    reason = None
    if remaining is not None and remaining <= 0:
        status = "DEGRADED"
        reason = (
            f"provider-reported quota exhausted (remaining={remaining} at "
            f"{last_quota.get('timestamp')}); connector guard returns "
            "RATE_LIMITED without spending a request"
        )
    elif last_live.get("status") == STATUS_RATE_LIMITED:
        status = "DEGRADED"
        reason = f"last live proof was itself rate-limited: {last_live.get('error')}"

    chain["live_request_works"] = True
    chain["response_parses"] = True
    chain["normalization_works"] = True
    chain["provenance_stores"] = True
    chain["health_check_passes"] = status == "LIVE"

    return {
        "source_id": source_id,
        "status": status,
        "chain": chain,
        "request_status": "NOT_PROBED (metered; quota-protected)",
        "last_live_proof": {
            "timestamp": last_live.get("timestamp"),
            "status": last_live.get("status"),
            "query": last_live.get("query"),
            "record_count": last_live.get("record_count"),
            "raw_payload_sha256": last_live.get("raw_payload_sha256"),
        },
        "error": reason,
        "derivation": METERED_DERIVATION,
        "metered": {
            **metered,
            "provider_reported_remaining": remaining,
            "last_quota_at": (last_quota or {}).get("timestamp"),
        },
    }


def load_connector(source_id: str) -> Optional[Any]:
    """Import the connector class named in the registry (step 1)."""
    rec = SOURCE_REGISTRY[source_id]
    spec = rec.get("connector")
    if not spec:
        return None
    module_path, cls_name = spec.split(":")
    module = importlib.import_module(module_path)
    return getattr(module, cls_name)


def check_source(source_id: str, timeout: int = 30) -> Dict[str, Any]:
    """Run the 7-step chain for ONE source; return the measured result."""
    rec = SOURCE_REGISTRY[source_id]

    # R399 W3: a non-ACTIVE routing state is reported WITHOUT probing
    # the source (no HTTP, no quota burn for a parked source) — the
    # state, basis and reinstatement criterion travel in the record;
    # never a silent skip, never a BLOCKED (the provider is reachable —
    # the ENGINE chose not to route to it).
    if rec.get("routing_state") and rec["routing_state"] != "ACTIVE":
        from discovery_fabric.source_registry.registry import routing_info
        return {
            "source_id": source_id,
            "status": rec["routing_state"],
            "probed": False,
            "routing": routing_info(source_id),
            "chain": None,
            "error": None,
            "derivation": DERIVATION,
            "note": (f"routing state {rec['routing_state']} — source NOT "
                     f"probed (R399 W3): the health of the provider is "
                     f"not in question; the engine's routing decision is "
                     f"the recorded fact"),
        }

    # Metered sources: NO live probe — derived health (see policy above).
    if rec.get("metered_quota"):
        return _check_metered_source(source_id, rec["metered_quota"])

    chain = {
        "connector_exists": False,
        "live_request_works": False,
        "response_parses": False,
        "normalization_works": False,
        "provenance_stores": False,
        "retrieval_log_stores": False,
        "health_check_passes": False,
    }

    # step 1: CONNECTOR EXISTS
    try:
        connector = load_connector(source_id)
    except Exception as e:  # noqa: BLE001
        return {
            "source_id": source_id,
            "status": "BLOCKED",
            "block": classify_block(
                request_status="CONNECTOR_IMPORT",
                error=f"connector import failed: {type(e).__name__}: {e}"),
            "chain": {**chain, "connector_exists": False},
            "error": f"connector import failed: {type(e).__name__}: {e}",
            "derivation": DERIVATION,
        }
    if connector is None:
        return {
            "source_id": source_id,
            "status": "NOT_INTEGRATED",
            "chain": chain,
            "error": None,
            "derivation": DERIVATION,
        }
    chain["connector_exists"] = True

    inst = connector()
    query = getattr(inst, "HEALTH_QUERY", "") or rec["source_id"]

    # steps 2-4: LIVE REQUEST -> PARSE -> NORMALIZE (via search())
    result = inst.search(query, timeout=timeout)

    if result.status in (STATUS_OK, STATUS_EMPTY):
        chain["live_request_works"] = True
        chain["response_parses"] = True
        chain["normalization_works"] = True
    elif result.status == STATUS_RATE_LIMITED:
        chain["live_request_works"] = True  # provider answered (with a limit)
    elif result.status == "PARSE_FAILED":
        # request reached the provider and returned a body; parse/normalize
        # is distinguished in the error string
        err = (result.error or "")
        chain["live_request_works"] = True
        if err.startswith("parse:"):
            chain["response_parses"] = False
        elif err.startswith("normalize:"):
            chain["response_parses"] = True
            chain["normalization_works"] = False
    # else: provider-side failure; live_request_works stays False

    # steps 5-6: PROVENANCE STORES + RETRIEVAL LOG STORES
    # (verified against the append-only log written by _finish)
    if result.status in (STATUS_OK, STATUS_EMPTY) and result.records:
        rec0 = result.records[0]
        prov_ok = bool(
            rec0.provenance.get("provider")
            and rec0.raw_payload_sha256
            and rec0.retrieved_at
        )
        chain["provenance_stores"] = prov_ok
    elif result.status == STATUS_EMPTY:
        chain["provenance_stores"] = True  # custody of the definitive-zero itself
    if result.status:  # every executed query wrote a log entry via _finish
        from discovery_fabric.source_registry.retrieval_log import read_entries
        entries = read_entries(source_id=source_id)
        chain["retrieval_log_stores"] = len(entries) > 0

    # step 7 + status derivation (mechanically honest vocabulary; BLOCKED
    # classes derived by status_model.classify_block from the measured
    # signature — CEO directive 2026-08-30 #5)
    status: str
    block_info: Optional[Dict[str, Any]] = None
    if result.status in (STATUS_OK, STATUS_EMPTY):
        status = "LIVE"
        if result.status == STATUS_EMPTY:
            status = "LIVE"  # definitive zero is a healthy provider answer
        if (result.latency_ms or 0) > LATENCY_DEGRADED_MS:
            status = "DEGRADED"
            reason = f"latency {result.latency_ms} ms above triage bound"
        else:
            reason = None
    elif result.status == STATUS_RATE_LIMITED:
        status = "DEGRADED"
        reason = f"provider answered with rate/budget limit: {result.error}"
    elif result.status in ("AUTH_FAILED", "UNAVAILABLE", "TIMEOUT",
                           "SEARCH_FAILED", "PARSE_FAILED", "NOT_IMPLEMENTED",
                           "GRAMMAR_MISMATCH"):
        block_info = classify_block(
            request_status=result.status, error=result.error,
            http_status=result.http_status)
        status = block_info["status"]
        reason = (f"{result.status}: {result.error} "
                  f"[block_class={block_info['block_class']}]")
    else:  # unknown status — honest recording, never silence
        block_info = classify_block(
            request_status=result.status, error=result.error,
            http_status=result.http_status)
        status = block_info["status"]
        reason = (f"unmapped status {result.status!r}: {result.error} "
                  f"[block_class={block_info['block_class']}]")

    chain["health_check_passes"] = status == "LIVE"

    out = {
        "source_id": source_id,
        "status": status,
        "chain": chain,
        "request_status": result.status,
        "http_status": result.http_status,
        "latency_ms": result.latency_ms,
        "record_count": len(result.records),
        "query": query,
        "error": reason if status != "LIVE" else None,
        "derivation": DERIVATION,
    }
    if block_info is not None:
        out["block"] = block_info
    return out


def run_health_check(source_ids: Optional[List[str]] = None,
                     timeout: int = 30) -> Dict[str, Any]:
    """Run the checker over the whole registry (or a subset)."""
    from discovery_fabric.source_registry.base import utc_now
    from discovery_fabric.source_registry.retrieval_log import verify_chain

    ids = source_ids or list(SOURCE_REGISTRY.keys())
    results = []
    for sid in ids:
        results.append(check_source(sid, timeout=timeout))

    measured = {r["source_id"]: r["status"] for r in results}
    return {
        "run_timestamp": utc_now(),
        "results": results,
        "measured_statuses": measured,
        "retrieval_log_audit": verify_chain(),
    }

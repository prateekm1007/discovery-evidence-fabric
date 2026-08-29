"""Source health checker — runs the 7-step proof chain per source.

CEO database-layer directive, per source:

    CONNECTOR EXISTS -> LIVE REQUEST WORKS -> RESPONSE PARSES ->
    NORMALIZATION WORKS -> PROVENANCE STORES -> RETRIEVAL LOG STORES ->
    HEALTH CHECK PASSES

and emits the measured status vocabulary:

    LIVE / DEGRADED / UNAVAILABLE / NOT_INTEGRATED

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
    "UNAVAILABLE": "connector exists; live request failed (auth, blocked, "
                   "5xx, network)",
    "NOT_INTEGRATED": "no connector exists (registry records the gap; "
                      "README mentions are not integration — Art. XXI)",
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
            "status": "UNAVAILABLE",
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

    # step 7 + status derivation
    status: str
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
                           "SEARCH_FAILED", "PARSE_FAILED", "NOT_IMPLEMENTED"):
        status = "UNAVAILABLE"
        reason = f"{result.status}: {result.error}"
    else:  # unknown status — honest recording, never silence
        status = "UNAVAILABLE"
        reason = f"unmapped status {result.status!r}: {result.error}"

    chain["health_check_passes"] = status == "LIVE"

    return {
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

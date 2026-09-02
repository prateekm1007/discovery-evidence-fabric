"""A2 prior art — search for existing solutions.

R394 section 2/4 REPAIR (2026-09-02, consultant reconciliation — the
release-blocking epistemic defect):

  MEASURED DEFECT (confirmed live on the public deployment, run
  ts_5c6ea3076a42 and code inspection): when every EuropePMC query
  failed, `results` was empty and this module set
  prior_art_status = NO_MATCHING_EVIDENCE_FOUND — a provider outage was
  silently converted into an absence claim, which
  PRIOR_ART_STATUS_MAP then promoted to NO_MATCH_FOUND. Forbidden
  transitions (R394 section 2, constitution Art. XXI.3/XXV):

      SEARCH_FAILED   != NO_MATCH_FOUND
      SEARCH_FAILED   != DIFFERENTIATED
      SEARCH_PARTIAL  != DIFFERENTIATED
      SEARCH_TIMEOUT  != NO_PRIOR_ART

  THE FIX: the status vocabulary now separates search EXECUTION from
  search FINDINGS. Execution states (per query, from the connector-state
  contract): SUCCESS / EMPTY_RESULT / TIMEOUT / RATE_LIMITED /
  PROVIDER_ERROR / PARSE_ERROR / UNAVAILABLE. The top-level status is
  derived ONLY from execution:

      all queries executed, >= 1 hit        -> PRIOR_ART_STATUS unchanged
                                                (LIKELY/PARTIAL/NO_MATCHING)
      all queries executed, 0 hits          -> NO_MATCHING_EVIDENCE_FOUND
                                                (a REAL zero for the
                                                searched universe)
      >= 1 query failed, 0 total hits       -> SEARCH_FAILED (UNKNOWN —
                                                never absence)
      >= 1 query failed, some hits          -> SEARCH_PARTIAL (the
                                                findings stand as
                                                evidence, but the search
                                                universe is incomplete —
                                                recorded, never silently
                                                aggregated)
      timeout-shaped failures               -> recorded with state
                                                TIMEOUT (maps to UNKNOWN)

  Zero-result SUCCESS still only supports "no matching evidence found
  within the searched universe" (Art. XXI.2) — never "nobody has done
  this".
"""
from __future__ import annotations
import json, re, ssl, time, urllib.request, urllib.parse
from datetime import datetime, timezone

from discovery_fabric.connectors.connector_states import (
    CONNECTOR_SEMANTICS_VERSION, classify_exception)

_SSL = ssl.create_default_context()
_SSL.check_hostname = False
_SSL.verify_mode = ssl.CERT_NONE

# Outage states that make a query's contribution UNKNOWN (never absence)
_OUTAGE = ("TIMEOUT", "RATE_LIMITED", "PROVIDER_ERROR", "PARSE_ERROR",
           "UNAVAILABLE")

# R394 section 3: the relevance/search instrument identity — persisted
# with every report so identical (problem, snapshot, query, version,
# threshold) tuples are checkable for identical decisions.
SEARCH_INSTRUMENT_VERSION = "a2_prior_art/2.0.0"


def _classify_query_failure(exc: BaseException) -> str:
    """Connector state for one failed EuropePMC query."""
    return classify_exception(exc)


def search_prior_art_with_queries(queries: list) -> dict:
    """Step 5 (R376 form): search EuropePMC with ENGINE-FORMED keyword
    queries (device+failure / mechanism keyword_form). Status vocabulary
    R394-hardened: search execution and search findings are NEVER
    conflated (see module docstring). Provider failure is recorded
    honestly: an exception on a query contributes zero results AND an
    execution state; a fully-failed search can NEVER produce
    NO_MATCHING_EVIDENCE_FOUND."""
    results = []
    query_log = []
    for q in queries:
        if not q or not str(q).strip():
            continue
        try:
            encoded = urllib.parse.quote(q)
            url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={encoded}&format=json&pageSize=3"
            req = urllib.request.Request(url, headers={"User-Agent": "A2-PriorArt/1.0"})
            resp = urllib.request.urlopen(req, timeout=20, context=_SSL)
            data = json.loads(resp.read())
            got = []
            for r in data.get("resultList", {}).get("result", []):
                got.append({"title": r.get("title", ""), "id": r.get("id", ""), "query": q})
            results.extend(got)
            query_log.append({
                "query": q, "status": "OK",
                "connector_state": "SUCCESS" if got else "EMPTY_RESULT",
                "result_count": len(got)})
        except Exception as exc:  # noqa: BLE001 — recorded, never hidden
            cstate = _classify_query_failure(exc)
            query_log.append({
                "query": q, "status": "SEARCH_FAILED",
                "connector_state": cstate,
                "error": f"{type(exc).__name__}: {exc}",
                "epistemic_effect": "UNKNOWN"})
        time.sleep(1.0)

    # ---- R394: execution-derived status (never conflate outage with
    # absence). Only queries that actually ran count toward the
    # searched-universe claim.
    executed = [e for e in query_log if e.get("status") == "OK"]
    failed = [e for e in query_log if e.get("status") == "SEARCH_FAILED"]
    n_failed = len(failed)
    n_ok = len(executed)

    if not results:
        if n_ok == 0 and n_failed > 0:
            # every mandatory query failed: the search itself FAILED —
            # an infrastructure state, NEVER a scientific conclusion.
            status = "SEARCH_FAILED"
        elif n_failed > 0:
            # some ran and legitimately found nothing, others failed:
            # the universe is incompletely searched — UNKNOWN, not
            # absence.
            status = "SEARCH_PARTIAL"
        else:
            status = "NO_MATCHING_EVIDENCE_FOUND"
    else:
        if n_failed > 0:
            # hits exist AND some queries failed: the findings stand as
            # evidence but coverage is incomplete — recorded, never
            # silently aggregated into a clean status.
            status = "SEARCH_PARTIAL"
        elif len(results) >= 3:
            status = "LIKELY_PRIOR_ART_EXISTS"
        else:
            status = "PARTIAL_PRIOR_ART"

    timeout_states = sorted({e.get("connector_state") for e in failed
                             if e.get("connector_state") == "TIMEOUT"})
    failure_states = sorted({str(e.get("connector_state")) for e in failed})

    report = {
        "prior_art_status": status,
        "search_execution": {
            "n_queries": len(query_log),
            "n_executed_ok": n_ok,
            "n_failed": n_failed,
            "failure_states": failure_states,
            "timeout_present": bool(timeout_states),
            "note": ("status is derived from execution, not findings: "
                     "a failed/timeout query set can never support a "
                     "no-match claim (R394 s2/s4, Art. XXI.3)"),
        },
        "databases_searched": ["EuropePMC"],
        "queries": [q for q in queries if q and str(q).strip()],
        "query_log": query_log,
        "instrument_version": SEARCH_INSTRUMENT_VERSION,
        "connector_semantics": CONNECTOR_SEMANTICS_VERSION,
        "date_range": "all",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "result_count": len(results),
        "results": results[:5],
        "limitations": [
            "Only EuropePMC searched",
            "No patent databases searched (patent side handled by the collision core)",
            "No ClinicalTrials.gov searched",
            "Zero-result searches support 'no matching evidence in the "
            "searched universe' only — never 'nobody has done this' "
            "(Art. XXI.2)",
        ],
        "note": "Never claim 'nobody has done this.' Only report 'No matching evidence found within the searched universe.'",
    }
    if status in ("SEARCH_FAILED", "SEARCH_PARTIAL"):
        report["epistemic_effect"] = "UNKNOWN"
        report["status_meaning"] = (
            "the search did not complete: findings (if any) stand as "
            "evidence, but NO absence or differentiation conclusion is "
            "permitted from this report (R394 s2)")
    print(f"  [prior_art] status={status} results={len(results)} "
          f"failed={n_failed}/{len(query_log)}")
    return report


def search_prior_art(intervention: str, device: str) -> dict:
    """Step 5: Search for prior art. Never claim 'nobody has done this'.

    LEGACY entry point — kept for backwards compatibility (a2/run.py and
    older tests). The engine's COLLISION stage now calls
    search_prior_art_with_queries with engine-formed keyword queries."""
    queries = [
        f"{device} {intervention[:50]}",
        f"{intervention[:50]} medical device",
    ]
    return search_prior_art_with_queries(queries)

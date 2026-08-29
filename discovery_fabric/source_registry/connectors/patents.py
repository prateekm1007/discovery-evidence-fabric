"""Patent connectors — thin wrappers over the EXISTING prior_art_v2 adapters.

REUSE PRINCIPLE (standing CEO directive: no second factory). The heavy
lifting (HTTP, provenance, PriorArtHit schema, hash custody) already lives
in discovery_fabric/prior_art_v2/. These wrappers only:

  1. adapt the prior_art_v2 SourceQueryResult shape to the registry's
     SourceQueryResult shape;
  2. map provider failures onto the Art. XXI.3 status vocabulary;
  3. write registry retrieval-log entries for custody.
"""

from __future__ import annotations

from typing import List

from discovery_fabric.source_registry.base import (
    ConnectorBase, SourceRecord, SourceQueryResult, utc_now,
)


def _hits_to_records(source_id: str, role: str, hits) -> List[SourceRecord]:
    out = []
    for h in hits:
        d = h if isinstance(h, dict) else vars(h)
        out.append(SourceRecord(
            source_id=source_id,
            role=role,
            record_id=f"patent:{d.get('patent_id') or d.get('source_url')}",
            title=d.get("title") or "",
            uri=d.get("source_url") or "",
            retrieved_at=d.get("retrieved_at_utc") or utc_now(),
            query=d.get("query") or "",
            raw_payload_sha256=d.get("raw_payload_sha256") or "",
            normalized={
                "patent_id": d.get("patent_id"),
                "snippet": d.get("snippet"),
                "assignee_or_authors": d.get("assignee_or_authors"),
                "publication_date": d.get("publication_date"),
                "doi": d.get("doi"),
                "raw_metadata": d.get("raw_metadata") or {},
            },
            provenance={
                "provider": source_id,
                "adapter": "prior_art_v2.sources",
                "query": d.get("query"),
                "raw_payload_sha256": d.get("raw_payload_sha256"),
                "retrieved_at": d.get("retrieved_at_utc"),
            },
            epistemic_state="OBSERVED",
            limitations=[
                "Bibliographic hit: a search result is NOT a claim-chart "
                "novelty determination (Art. XXI.2)",
                "Snippet relevance is provider-ranked; full claims were "
                "not retrieved for this record",
                "Patent existence does not establish commercial practice "
                "or technical viability",
            ],
        ))
    return out


def _adapt(source_id: str, role: str, pa_result, query: str, url_hint: str) -> SourceQueryResult:
    """prior_art_v2 SourceQueryResult -> registry SourceQueryResult."""
    from discovery_fabric.source_registry.base import STATUS_RATE_LIMITED

    if pa_result is None:
        return SourceQueryResult(
            source_id=source_id, status="SEARCH_FAILED", ok=False,
            error="prior_art_v2 returned None", query=query, retrieved_at=utc_now(),
        )
    success = bool(getattr(pa_result, "success", False))
    error = getattr(pa_result, "error", None)
    error_code = getattr(pa_result, "error_code", None)
    hits = list(getattr(pa_result, "hits", []) or [])
    latency = getattr(pa_result, "latency_ms", None)

    if success:
        records = _hits_to_records(source_id, role, hits)
        status = "OK" if records else "EMPTY"
        out = SourceQueryResult(
            source_id=source_id, status=status, ok=True,
            http_status=error_code, latency_ms=latency, records=records,
            query=query, retrieved_at=utc_now(),
            rate_limit_remaining=(str(pa_result.rate_limit_remaining)
                                  if getattr(pa_result, "rate_limit_remaining", None) is not None
                                  else None),
        )
    else:
        msg = (error or "").lower()
        if ("not configured" in msg or "no token" in msg or "token not" in msg
                or "api key" in msg or "key not" in msg or "credentials" in msg):
            status = "AUTH_FAILED"
        elif error_code == 429 or "rate" in msg or "429" in msg:
            status = STATUS_RATE_LIMITED
        elif error_code in (401, 403):
            status = "AUTH_FAILED"
        elif error_code and error_code >= 500:
            status = "UNAVAILABLE"
        else:
            status = "SEARCH_FAILED"
        out = SourceQueryResult(
            source_id=source_id, status=status, ok=False,
            http_status=error_code, latency_ms=latency, error=error,
            query=query, retrieved_at=utc_now(),
        )
    out._registry_url_hint = url_hint  # type: ignore[attr-defined]
    return out


class _PaV2Wrapper(ConnectorBase):
    """Base for prior_art_v2-backed connectors."""
    ROLE = "PATENT"
    URL_HINT = ""

    def build_url(self, query: str) -> str:
        return self.URL_HINT

    def parse_payload(self, raw, query):  # pragma: no cover — unused path
        raise RuntimeError("prior_art_v2 wrappers do not use parse_payload")

    def normalize_payload(self, payload, query, raw_sha):  # pragma: no cover
        raise RuntimeError("prior_art_v2 wrappers do not use normalize_payload")

    def _finish_pa(self, out: SourceQueryResult, query: str) -> SourceQueryResult:
        from discovery_fabric.source_registry.retrieval_log import append_entry
        try:
            append_entry(
                source_id=out.source_id, query=query,
                url=getattr(out, "_registry_url_hint", "") or "",
                status=out.status, http_status=out.http_status,
                latency_ms=out.latency_ms, record_count=len(out.records),
                raw_payload_sha256=(out.records[0].raw_payload_sha256
                                    if out.records else None),
                error=out.error,
                rate_limit_remaining=out.rate_limit_remaining,
            )
        except Exception as e:  # noqa: BLE001
            out.error = (out.error or "") + f" | retrieval_log_write_failed: {e}"
        return out


class GooglePatentsConnector(_PaV2Wrapper):
    SOURCE_ID = "google_patents"
    ROLES = ("PATENT",)
    HEALTH_QUERY = "pacemaker lead"
    URL_HINT = "https://patents.google.com/xhr/query.json"

    def search(self, query: str, timeout: int = 25) -> SourceQueryResult:
        from discovery_fabric.prior_art_v2.sources import search_google_patents
        pa = search_google_patents(query, num_results=5)
        return self._finish_pa(_adapt(self.SOURCE_ID, self.ROLE, pa, query, self.URL_HINT), query)


class LensConnector(_PaV2Wrapper):
    """The Lens SCHOLARLY (NPL) resource — SCIENTIFIC role only.

    CEO Section 4 / elite_v3: LENS_PATENT and LENS_SCHOLARLY are SEPARATE
    sources and are never merged. The patent-side connector is
    LensPatentConnector below. Measured 2026-08-29: the provisioned token
    authenticates on BOTH endpoints (one transient 401 observed 14 min
    after provisioning, then 200s — see registry measurement history).
    """

    SOURCE_ID = "lens_scholarly"
    ROLES = ("SCIENTIFIC",)
    HEALTH_QUERY = "pacemaker lead"
    URL_HINT = "https://api.lens.org/scholarly/search"

    def search(self, query: str, timeout: int = 25) -> SourceQueryResult:
        from discovery_fabric.prior_art_v2.sources import search_lens_scholarly
        pa = search_lens_scholarly(query, num_results=5)
        return self._finish_pa(_adapt(self.SOURCE_ID, self.ROLE, pa, query, self.URL_HINT), query)


class LensPatentConnector(_PaV2Wrapper):
    """The Lens PATENT resource — PATENT role.

    Measured 2026-08-29: HTTP 200 with real patent records on the
    provisioned token. Bibliographic coverage (title/abstract/applicants/
    doc_key); claim TEXT is not in search results (see registry known_gaps).
    """

    SOURCE_ID = "lens_patent"
    ROLES = ("PATENT",)
    HEALTH_QUERY = "hydrocephalus shunt valve"
    URL_HINT = "https://api.lens.org/patent/search"

    def search(self, query: str, timeout: int = 25) -> SourceQueryResult:
        from discovery_fabric.prior_art_v2.sources import search_lens_patent
        pa = search_lens_patent(query, num_results=5)
        return self._finish_pa(_adapt(self.SOURCE_ID, self.ROLE, pa, query, self.URL_HINT), query)


class PatentBearConnector(_PaV2Wrapper):
    """Patent Bear MCP — PATENT role, PROVIDER-METERED (20 requests/month).

    Quota discipline (measured 2026-08-29, provider usage block):
    - search_patents and get_patent_record draw from the SAME 20/month pool;
    - the provider's usage block is logged verbatim per response
      (rate_limit_remaining in the retrieval log);
    - GUARD: if the freshest provider-reported remaining is 0, search()
      returns RATE_LIMITED WITHOUT making the call (Art. XXI.3 — a quota
      exhaustion is a provider state, never 'no results');
    - run_lab / get_lab_result BILL CREDITS and are NEVER called by this
      engine (registry metered_quota.prohibited_tools).
    """

    SOURCE_ID = "patentbear"
    ROLES = ("PATENT",)
    HEALTH_QUERY = "hydrocephalus shunt valve"
    URL_HINT = "https://www.patentbear.com/mcp"

    def _last_reported_remaining(self) -> int | None:
        """Freshest provider-reported monthly_remaining for this source,
        from the append-only retrieval log (None = never reported)."""
        from discovery_fabric.source_registry.retrieval_log import read_entries
        for e in reversed(read_entries(source_id=self.SOURCE_ID)):
            v = e.get("rate_limit_remaining")
            if v is not None and str(v).strip() != "":
                try:
                    return int(str(v).strip())
                except ValueError:
                    continue
        return None

    def search(self, query: str, timeout: int = 25) -> SourceQueryResult:
        remaining = self._last_reported_remaining()
        if remaining is not None and remaining <= 0:
            return self._finish_pa(
                SourceQueryResult(
                    source_id=self.SOURCE_ID, status="RATE_LIMITED", ok=False,
                    error=(
                        "Patent Bear monthly quota exhausted (provider-reported "
                        f"remaining={remaining} in the freshest logged usage "
                        "block); NO request was made — this is a provider "
                        "metering state, not an absence of patents "
                        "(Art. XXI.3)"
                    ),
                    query=query, retrieved_at=utc_now(),
                ),
                query,
            )
        from discovery_fabric.prior_art_v2.sources import search_patent_bear
        pa = search_patent_bear(query, num_results=5)
        return self._finish_pa(_adapt(self.SOURCE_ID, self.ROLE, pa, query, self.URL_HINT), query)


class PatSnapConnector(_PaV2Wrapper):
    SOURCE_ID = "patsnap_eureka"
    ROLES = ("PATENT",)
    HEALTH_QUERY = "pacemaker lead"
    URL_HINT = "https://open-api.patsnap.com/"

    def search(self, query: str, timeout: int = 25) -> SourceQueryResult:
        from discovery_fabric.prior_art_v2.sources import search_patsnap_eureka
        pa = search_patsnap_eureka(query, num_results=5)
        return self._finish_pa(_adapt(self.SOURCE_ID, self.ROLE, pa, query, self.URL_HINT), query)


class EpoOpsConnector(_PaV2Wrapper):
    SOURCE_ID = "epo_ops"
    ROLES = ("PATENT",)
    HEALTH_QUERY = "pacemaker"
    URL_HINT = "https://ops.epo.org/3.2/rest-services/"

    def search(self, query: str, timeout: int = 25) -> SourceQueryResult:
        from discovery_fabric.prior_art_v2.epo_ops_adapter import epo_ops_search
        try:
            att = epo_ops_search(query, range_start=1, range_end=5)
        except Exception as e:  # noqa: BLE001 — adapter may raise before auth
            return self._finish_pa(
                SourceQueryResult(
                    source_id=self.SOURCE_ID, status="SEARCH_FAILED", ok=False,
                    error=f"adapter: {type(e).__name__}: {e}", query=query,
                    retrieved_at=utc_now(),
                ),
                query,
            )
        if att is None:
            return self._finish_pa(
                SourceQueryResult(
                    source_id=self.SOURCE_ID, status="AUTH_FAILED", ok=False,
                    error="EPO OPS: no OAuth consumer credentials provisioned",
                    query=query, retrieved_at=utc_now(),
                ),
                query,
            )
        records = []
        state = getattr(att, "normalized_state", "SOURCE_UNAVAILABLE")
        substate = getattr(att, "failure_substate", "NONE")
        api_ok = state not in ("SOURCE_UNAVAILABLE", "SOURCE_FAILED", "SOURCE_EXCEPTION") \
            and substate not in ("EXCEPTION", "AUTH_FAILURE")
        if api_ok and getattr(att, "records", None):
            for rec in att.records:
                d = rec if isinstance(rec, dict) else vars(rec)
                records.append(SourceRecord(
                    source_id=self.SOURCE_ID, role=self.ROLE,
                    record_id=f"epo:{d.get('publication_number', d.get('patent_number', ''))}",
                    title=d.get("title") or "",
                    uri=d.get("source_url") or "https://ops.epo.org",
                    retrieved_at=getattr(att, "timestamp", utc_now()),
                    query=query,
                    raw_payload_sha256=d.get("raw_sha256", ""),
                    normalized={
                        "publication_number": d.get("publication_number", d.get("patent_number")),
                        "title": d.get("title"),
                        "applicant": d.get("applicant"),
                        "publication_date": d.get("publication_date"),
                        "raw": d,
                    },
                    provenance={
                        "provider": self.SOURCE_ID,
                        "adapter": "prior_art_v2.epo_ops_adapter",
                        "query": query,
                        "retrieved_at": getattr(att, "timestamp", None),
                    },
                    epistemic_state="OBSERVED",
                    limitations=[],
                ))
        if api_ok:
            status = "OK" if records else "EMPTY"
            err = None
        else:
            status = "AUTH_FAILED" if substate == "AUTH_FAILURE" else "SEARCH_FAILED"
            err = f"{state}/{substate}"
        return self._finish_pa(
            SourceQueryResult(
                source_id=self.SOURCE_ID, status=status,
                ok=api_ok,
                error=err, records=records,
                query=query, retrieved_at=utc_now(),
            ),
            query,
        )


class UsptoOdpConnector(_PaV2Wrapper):
    SOURCE_ID = "uspto_odp"
    ROLES = ("PATENT",)
    HEALTH_QUERY = "pacemaker"
    URL_HINT = "https://api.uspto.gov/api/v1/patent/grants"

    def search(self, query: str, timeout: int = 25) -> SourceQueryResult:
        from discovery_fabric.prior_art_v2.uspto_odp_adapter import uspto_search
        att = uspto_search(query, limit=5)
        # TRUTH CRITERION (measured): the adapter's api_status flag is TRUE
        # even when the body fails to parse (masked failure); the honest
        # success signal is normalized_state. 'api_status=True' alone would
        # report a broken path as LIVE (Art. XXI false positive — caught in
        # this session's first full health run).
        state = getattr(att, "normalized_state", "SOURCE_UNAVAILABLE")
        substate = getattr(att, "failure_substate", "NONE")
        api_ok = state not in ("SOURCE_UNAVAILABLE", "SOURCE_FAILED", "SOURCE_EXCEPTION") \
            and substate not in ("EXCEPTION", "AUTH_FAILURE")
        records = []
        if api_ok and getattr(att, "patents", None):
            for rec in att.patents:
                d = rec if isinstance(rec, dict) else vars(rec)
                records.append(SourceRecord(
                    source_id=self.SOURCE_ID, role=self.ROLE,
                    record_id=f"uspto:{d.get('patent_number', '')}",
                    title=d.get("title") or "",
                    uri=f"https://ppubs.uspto.gov/dirsearch-public/patent/{d.get('patent_number')}",
                    retrieved_at=getattr(att, "retrieved_at_utc", utc_now()),
                    query=query,
                    raw_payload_sha256=d.get("raw_sha256", ""),
                    normalized={
                        "patent_number": d.get("patent_number"),
                        "title": d.get("title"),
                        "abstract": d.get("abstract"),
                        "publication_date": d.get("publication_date"),
                        "assignee": d.get("assignee"),
                    },
                    provenance={
                        "provider": self.SOURCE_ID,
                        "adapter": "prior_art_v2.uspto_odp_adapter",
                        "query": query,
                        "retrieved_at": getattr(att, "retrieved_at_utc", None),
                    },
                    epistemic_state="OBSERVED",
                    limitations=[],
                ))
        if api_ok:
            status = "OK" if records else "EMPTY"
            err = None
        else:
            msg = (getattr(att, "api_error_msg", "") or "")
            status = "AUTH_FAILED" if substate == "AUTH_FAILURE" or "key" in msg.lower() else "SEARCH_FAILED"
            err = f"{state}/{substate}: {msg}" if msg else f"{state}/{substate}"
        out = SourceQueryResult(
            source_id=self.SOURCE_ID, status=status, ok=api_ok,
            http_status=getattr(att, "http_status", 0) or None,
            error=err, records=records, query=query, retrieved_at=utc_now(),
        )
        return self._finish_pa(out, query)


class BigQueryPatentsConnector(_PaV2Wrapper):
    SOURCE_ID = "google_bigquery_patents"
    ROLES = ("PATENT",)
    HEALTH_QUERY = "pacemaker"
    URL_HINT = "https://bigquery.googleapis.com/"

    def search(self, query: str, timeout: int = 25) -> SourceQueryResult:
        from discovery_fabric.prior_art_v2.bigquery_patents_adapter import (
            is_bigquery_available, bigquery_search_concepts,
        )
        if not is_bigquery_available():
            return self._finish_pa(
                SourceQueryResult(
                    source_id=self.SOURCE_ID, status="AUTH_FAILED", ok=False,
                    error="BigQuery: no GCP credentials provisioned",
                    query=query, retrieved_at=utc_now(),
                ),
                query,
            )
        attempt = bigquery_search_concepts(query, limit=5)
        records = []
        if attempt and getattr(attempt, "records", None):
            for rec in attempt.records:
                d = rec if isinstance(rec, dict) else vars(rec)
                records.append(SourceRecord(
                    source_id=self.SOURCE_ID, role=self.ROLE,
                    record_id=f"bqpatent:{d.get('patent_number', '')}",
                    title=d.get("title") or "",
                    uri=d.get("source_url") or "",
                    retrieved_at=getattr(attempt, "timestamp", utc_now()),
                    query=query,
                    raw_payload_sha256=d.get("raw_sha256", ""),
                    normalized=d,
                    provenance={
                        "provider": self.SOURCE_ID,
                        "adapter": "prior_art_v2.bigquery_patents_adapter",
                        "query": query,
                    },
                    epistemic_state="OBSERVED",
                    limitations=[],
                ))
        status = "OK" if getattr(attempt, "success", False) else "SEARCH_FAILED"
        return self._finish_pa(
            SourceQueryResult(
                source_id=self.SOURCE_ID, status=status,
                ok=bool(getattr(attempt, "success", False)),
                error=getattr(attempt, "error", None), records=records,
                query=query, retrieved_at=utc_now(),
            ),
            query,
        )

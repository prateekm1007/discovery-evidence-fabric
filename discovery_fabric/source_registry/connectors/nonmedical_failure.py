"""Non-medical failure-evidence connectors — NTSB/NHTSA family.

CEO directive 2026-08-30 (negative-evidence architecture + free/open
priority sources): Toscanini's failure evidence was MEDICAL-ONLY (maturity
model engine finding, 2026-08-30). This module starts the non-medical
failure layer.

Measured live (this session):
- NHTSA recalls: https://api.nhtsa.gov/recalls/recallsByVehicle
  200 application/json; results[] with Manufacturer,
  NHTSACampaignNumber, ReportReceivedDate, Component, Summary...
  (the older www.nhtsa.gov/webapi/api/Recalls route answers 403 to this
  egress — the api.nhtsa.gov route is the measured working one)
- NTSB CAROL: every probed API path (carol-main-public, carol1-, carol-,
  /api/ root) serves HTML — no machine route measured. NOT registered;
  recorded as a route-blocked gap in the Toscanini audit trail.

Query semantics: the recallsByVehicle endpoint is parameterized by
make/model/modelYear, not free text. search() accepts
"<make>|<model>|<year>" and the connector decomposes it; malformed
queries fail SEARCH_FAILED (never guessed) — the engine's query ladder
adapts, provenance records the exact URL used.

Epistemic class (Art. XXI.5 analog): a recall campaign is a regulatory
DEFECT-ACKNOWLEDGMENT event — the manufacturer/NHTSA acknowledged a
safety defect. It is NOT an incidence rate, NOT a failure-rate estimate,
and absence of a recall is NOT absence of the defect.
"""

from __future__ import annotations

import json
import urllib.parse
from typing import Any, Dict, List, Optional

from discovery_fabric.source_registry.base import (
    ConnectorBase,
    SourceRecord,
    utc_now,
)

NHTSA_LIMITATIONS = [
    "RECALL_SEMANTICS: a recall campaign is an acknowledged safety defect, "
    "NOT an incidence or failure rate",
    "POPULATION_UNKNOWN: affected-unit counts exist per campaign but "
    "field-failure counts are not derivable from recall records",
    "JURISDICTION: US vehicle market only — non-US campaigns are not "
    "covered by this endpoint",
    "VOLUNTARY_REPORTING_MIX: recall initiation mixes voluntary "
    "manufacturer action and NHTSA-influenced campaigns",
]


class NhtsaRecallConnector(ConnectorBase):
    """NHTSA vehicle-recall campaigns — transport-domain failure evidence."""

    SOURCE_ID = "nhtsa_recalls"
    ROLES = ("RECALL",)
    HEALTH_QUERY = "toyota|camry|2020"
    LIMIT = 25  # endpoint-controlled; kept at API default page size

    def parse_query(self, query: str) -> Optional[Dict[str, str]]:
        """'<make>|<model>|<year>' -> {make, model, modelYear} or None."""
        parts = [p.strip() for p in query.split("|")]
        if len(parts) != 3 or not all(parts):
            return None
        make, model, year = parts
        if not (year.isdigit() and 1900 <= int(year) <= 2100):
            return None
        return {"make": make, "model": model, "modelYear": year}

    def build_url(self, query: str) -> str:
        pq = self.parse_query(query) or {}
        return ("https://api.nhtsa.gov/recalls/recallsByVehicle"
                f"?make={urllib.parse.quote(pq.get('make', ''))}"
                f"&model={urllib.parse.quote(pq.get('model', ''))}"
                f"&modelYear={urllib.parse.quote(pq.get('modelYear', ''))}")

    def parse_payload(self, raw: bytes, query: str) -> Any:
        payload = json.loads(raw.decode("utf-8"))
        # zero recalls: {"Count":0,"Message":"No results found...","results":[]}
        if not isinstance(payload, dict) or "results" not in payload:
            raise ValueError("nhtsa payload missing results key")
        return payload

    def normalize_payload(self, payload: Any, query: str, raw_sha: str) -> List[SourceRecord]:
        out: List[SourceRecord] = []
        for r in payload.get("results") or []:
            camp = r.get("NHTSACampaignNumber") or ""
            out.append(SourceRecord(
                source_id=self.SOURCE_ID,
                role="RECALL",
                record_id=f"nhtsa:{camp}",
                title=(f"{r.get('Manufacturer', '')} — {r.get('Component', '')}"
                       ).strip(" —"),
                uri=(f"https://www.nhtsa.gov/recalls?nhtsaId={camp}" if camp else ""),
                retrieved_at=utc_now(),
                query=query,
                raw_payload_sha256=raw_sha,
                normalized={
                    "nhtsa_campaign_number": camp,
                    "manufacturer": r.get("Manufacturer"),
                    "component": r.get("Component"),
                    "report_received_date": r.get("ReportReceivedDate"),
                    "recall_type": r.get("RecallType"),
                    "park_it": r.get("parkIt"),
                    "over_the_air_update": r.get("overTheAirUpdate"),
                    "defect_summary": (r.get("Summary") or "")[:4000] or None,
                    "consequence": (r.get("Conequence") or r.get("Consequence") or "")[:2000] or None,
                    "remedy": (r.get("Remedy") or "")[:2000] or None,
                    "failure_domain": "transport",
                },
                provenance={
                    "provider": self.SOURCE_ID,
                    "api": "api.nhtsa.gov/recalls/recallsByVehicle",
                    "query": query,
                    "raw_payload_sha256": raw_sha,
                    "retrieved_at": utc_now(),
                },
                epistemic_state="OBSERVED",
                limitations=list(NHTSA_LIMITATIONS),
            ))
        return out

    def extract_total_hits(self, payload: Any) -> Optional[int]:
        c = payload.get("Count")
        return c if isinstance(c, int) else None

"""ClinicalTrials.gov API v2 connector."""

from __future__ import annotations

import json
import urllib.parse
from typing import Any, Dict, List

from discovery_fabric.source_registry.base import (
    ConnectorBase, SourceRecord, utc_now,
)

API = "https://clinicaltrials.gov/api/v2/studies"


class ClinicalTrialsConnector(ConnectorBase):
    SOURCE_ID = "clinicaltrials_gov"
    ROLES = ("CLINICAL",)
    HEALTH_QUERY = "pacemaker"
    LIMIT = 10

    def build_url(self, query: str) -> str:
        q = urllib.parse.quote(query)
        return f"{API}?query.term={q}&pageSize={self.LIMIT}&countTotal=true"

    def parse_payload(self, raw: bytes, query: str) -> Any:
        return json.loads(raw.decode("utf-8"))

    def normalize_payload(self, payload: Any, query: str, raw_sha: str) -> List[SourceRecord]:
        if not isinstance(payload, dict):
            raise ValueError("payload is not an object")
        studies = payload.get("studies")
        if not isinstance(studies, list):
            raise ValueError("payload missing 'studies' list")
        return [self.to_record(s, query, raw_sha) for s in studies]

    def to_record(self, s: Dict[str, Any], query: str, raw_sha: str) -> SourceRecord:
        proto = s.get("protocolSection") or {}
        ident = proto.get("identificationModule") or {}
        status = proto.get("statusModule") or {}
        design = proto.get("designModule") or {}
        conditions = proto.get("conditionsModule") or {}
        sponsor = proto.get("sponsorCollaboratorsModule") or {}
        nct = ident.get("nctId") or ""
        return SourceRecord(
            source_id=self.SOURCE_ID,
            role="CLINICAL",
            record_id=f"nct:{nct}",
            title=f"{ident.get('briefTitle', '')[:150]}",
            uri=f"https://clinicaltrials.gov/study/{nct}" if nct else API,
            retrieved_at=utc_now(),
            query=query,
            raw_payload_sha256=raw_sha,
            normalized={
                "nct_id": nct,
                "brief_title": ident.get("briefTitle"),
                "official_title": ident.get("officialTitle"),
                "overall_status": status.get("overallStatus"),
                "study_start_date": (status.get("startDateStruct") or {}).get("date"),
                "primary_completion_date": (status.get("primaryCompletionDateStruct") or {}).get("date"),
                "completion_date": (status.get("completionDateStruct") or {}).get("date"),
                "enrollment_count": (design.get("enrollmentInfo") or {}).get("count"),
                "study_type": design.get("studyType"),
                "phases": design.get("phases"),
                "conditions": conditions.get("conditions") or [],
                "interventions": [
                    (i or {}).get("name")
                    for i in (proto.get("armsInterventionsModule", {}) or {}).get("interventions", [])
                    if isinstance(i, dict)
                ],
                "lead_sponsor": (sponsor.get("leadSponsor") or {}).get("name"),
                "collaborators": [
                    (c or {}).get("name")
                    for c in (sponsor.get("collaborators") or []) if isinstance(c, dict)
                ],
                "why_stopped": status.get("whyStopped"),
            },
            provenance={
                "provider": self.SOURCE_ID,
                "api": API,
                "query": query,
                "raw_payload_sha256": raw_sha,
                "retrieved_at": utc_now(),
            },
            epistemic_state="OBSERVED",
            limitations=[
                "Registry record, not results: completion does not imply "
                "publication or success",
                "Device interventions are free-text; identity resolution to "
                "GUDID is unresolved here",
            ],
        )

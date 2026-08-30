"""Research-attempt connectors — the EXPERIMENT information type (CEO
directive 2026-08-30 #3: prioritize sources that add NEW information
types: ... experiments ...).

NIH RePORTER — funded biomedical research PROJECTS (grants): what was
ATTEMPTED, by whom, over what period, with declared objectives. This is
the attempt-outcome universe beyond publication bias: a funded attempt
that never published still leaves a project record here.

Measured live 2026-08-30 (this session, probe artifacts):
- https://api.reporter.nih.gov/v2/projects/search (POST JSON)
  200 application/json; results[] with appl_id, project title, dates,
  organization, and (with include_fields) abstract text.

Sibling candidates measured the same session and HONESTLY BLOCKED from
this egress (no integration claim — Art. XXI):
- NSF awards api.nsf.gov: HTTP 404 on /api/v1/awards.json and 403
  Forbidden on /services/awards.json -> BLOCKED::EGRESS-class from this
  network (the connector is intentionally absent; registry row records
  the measured block).
- CORDIS (EU): API routes return the HTML app shell (no anonymous JSON
  route) -> BLOCKED::REGISTRATION.

Epistemic class: OBSERVED (project records). The EXPERIMENT role carries
its own epistemic cap (roles.py): a project record establishes that
research HAPPENED and what it targeted — never that a mechanism works;
absence of a positive outcome is not evidence of failure (Art. XXV).
"""

from __future__ import annotations

import json
import urllib.parse
from typing import Any, Dict, List

from discovery_fabric.source_registry.base import (
    ConnectorBase,
    SourceRecord,
    utc_now,
)

REPORTER_LIMITATIONS = [
    "ATTEMPT_RECORD: a funded project is an ATTEMPT with declared "
    "objectives; it is not evidence the objective was achieved",
    "OUTCOME_BIAS_INVERSE: RePORTER indexes what was FUNDED, not what "
    "failed review or was abandoned before award — absence is not "
    "evidence no attempt existed",
    "SCOPE: NIH-funded biomedical research; absence of a RePORTER "
    "project is not evidence a technology was never researched "
    "(DOE/NSF/EU attempts live in other corpora)",
    "STATUS_SEMANTICS: project dates describe administrative lifecycles; "
    "a completed project is not a successful project",
]


class NihReporterConnector(ConnectorBase):
    """NIH RePORTER v2 — funded research projects (EXPERIMENT role)."""

    SOURCE_ID = "nih_reporter"
    ROLES = ("EXPERIMENT",)
    HEALTH_QUERY = "hydrogel cartilage repair"
    HTTP_METHOD = "POST"
    LIMIT = 10

    def build_url(self, query: str) -> str:
        return "https://api.reporter.nih.gov/v2/projects/search"

    def build_request_body(self, query: str) -> bytes:
        # RePORTER v2 query shape — MEASUREDED DISCIPLINE (2026-08-30):
        # the {"query": {"operator","search_text"}} shape is SILENTLY
        # IGNORED by the API (measured: total = whole corpus 2,965,456,
        # records unrelated to the text — the status-OK-plus-irrelevant-
        # records defect class, caught by the relevance-custody instrument
        # during this connector's own 7-step proof chain). The working
        # shape is advanced_text_search (measured: projecttitle:cartilage
        # -> 2,652 on-topic titles; all:hydrogel -> 4,172 on-topic).
        # Multi-word AND queries on out-of-scope topics return a
        # definitive 0 — an honest EMPTY (NIH is biomedical-scoped), never
        # treated as absence-of-research beyond the corpus (Art. XXI.2/3).
        payload = {
            "criteria": {
                "advanced_text_search": {
                    "operator": "and",
                    "search_field": "all",
                    "search_text": query,
                },
            },
            "include_fields": [
                "ApplId", "ProjectTitle", "ProjectStartDate",
                "ProjectEndDate", "ProjectDetailUrl", "AbstractText",
                "Organization", "AgencyIcAdmin",
            ],
            "offset": 0,
            "limit": self.LIMIT,
        }
        return json.dumps(payload).encode("utf-8")

    def parse_payload(self, raw: bytes, query: str) -> Any:
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict) or not isinstance(
                payload.get("results"), list):
            raise ValueError("nih_reporter payload missing results list")
        return payload

    def extract_total_hits(self, payload: Any):
        meta = payload.get("meta") or {}
        total = meta.get("total")
        return int(total) if isinstance(total, int) else None

    def normalize_payload(self, payload: Any, query: str,
                          raw_sha: str) -> List[SourceRecord]:
        out: List[SourceRecord] = []
        for r in payload.get("results", []):
            appl_id = r.get("appl_id")
            if appl_id is None:
                continue
            org = r.get("organization") or {}
            out.append(SourceRecord(
                source_id=self.SOURCE_ID,
                role="EXPERIMENT",
                record_id=f"nih:{appl_id}",
                title=str(r.get("project_title") or f"NIH project {appl_id}"),
                uri=str(r.get("project_detail_url")
                        or f"https://reporter.nih.gov/project-details/{appl_id}"),
                retrieved_at=utc_now(),
                query=query,
                raw_payload_sha256=raw_sha,
                normalized={
                    "appl_id": appl_id,
                    "start_date": r.get("project_start_date"),
                    "completion_date": r.get("project_end_date"),
                    "org_name": org.get("org_name"),
                    "org_country": org.get("org_country"),
                    "agency": r.get("agency_ic_admin"),
                    "abstract": (r.get("abstract_text") or "")[:4000] or None,
                    "attempt_kind": "FUNDED_RESEARCH_PROJECT",
                },
                provenance={
                    "provider": self.SOURCE_ID,
                    "api": "api.reporter.nih.gov/v2/projects/search",
                    "query": query,
                    "raw_payload_sha256": raw_sha,
                    "retrieved_at": utc_now(),
                },
                epistemic_state="OBSERVED",
                limitations=list(REPORTER_LIMITATIONS),
            ))
        return out

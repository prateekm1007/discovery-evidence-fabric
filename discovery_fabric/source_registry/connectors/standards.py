"""Standards connectors: FDA Recognized Consensus Standards database and
the eCFR Title 21 (Food and Drugs) structure/full-text API.

CEO lifecycle directive (2026-08-29): close the STANDARDS authority role
with a registry that connects

    STANDARD -> DEVICE TYPE -> ENGINEERING PURPOSE -> APPLICABILITY ->
    VERIFICATION REQUIREMENT

— "Do not merely store ISO numbers."

Source 1 — FDA Recognized Consensus Standards (accessdata.fda.gov):
  The authoritative registry of consensus standards (ISO/ASTM/IEC/...)
  recognized by FDA for regulatory submissions. Each record carries:
  specialty task group area (device area), recognition number, extent of
  recognition (Complete/Partial), standards developing organization,
  designation, and title (the engineering purpose). Measured LIVE
  2026-08-29 (keyword '10993' -> 100 records).

Source 2 — eCFR Title 21 Subchapter H (Medical Devices):
  The codified US regulation: device classification parts by specialty
  panel (862-892), QMSR Part 820 (ISO 13485 incorporated by reference at
  § 820.7), MDR Part 803, recall Part 810, IDE 812, PMA 814, UDI 830.
  Measured LIVE 2026-08-29 (part 888 -> 111 sections; § 820.1 full text).

Constitutional anchors:
- Art. XXI.3: provider failure != absence; statuses stay distinct.
- Art. XXVII: 'Complete' vs 'Partial' recognition is the provider's own
  applicability classification, not an invented threshold.
- Art. VI: recognition numbers, designations and section identifiers are
  the providers' own ids; hashes are of their own bytes.
"""

from __future__ import annotations

import json
import re
import urllib.parse
from typing import Any, Dict, List, Optional

from discovery_fabric.source_registry.base import (
    ConnectorBase, SourceRecord, STATUS_OK, utc_now,
)

FDA_STDS_LIMITATIONS = [
    "Recognition by FDA declares the standard acceptable for one or more "
    "regulatory submissions — it is not a claim that any given device "
    "complies with it.",
    "'Complete' vs 'Partial' extent of recognition is FDA's applicability "
    "classification; partial recognitions carry exclusion rationale on "
    "the FDA detail page which this list-level record does not include.",
    "The specialty task group area is FDA's device-area grouping, not a "
    "product-code-level device typing.",
]

ECFR_LIMITATIONS = [
    "eCFR structure records identify codified requirements and device "
    "classification sections; the structure record does not carry the "
    "section's full text (fetch via a section query).",
    "Part 820 is the Quality Management System Regulation (QMSR); ISO "
    "13485 is incorporated by reference (§ 820.7) — the incorporated "
    "standard text itself is NOT in eCFR.",
    "Classification sections name device types and classes but do not "
    "by themselves establish device identity for a marketed product.",
]

# eCFR issue date discipline: the connector pins the ISSUE DATE IT
# MEASURED (never silently 'current' drift between chain steps). The
# date is stamped on every record's provenance.
ECFR_ISSUE_DATE = "2026-08-27"


class FdaRecognizedStandardsConnector(ConnectorBase):
    """FDA Recognized Consensus Standards database (HTML results table)."""

    SOURCE_ID = "fda_recognized_standards"
    ROLES = ("STANDARDS",)
    HEALTH_QUERY = "10993"          # biocompatibility family — measured
    LIMIT = 100

    _HEADER_CELL = "Date of Entry"

    def build_url(self, query: str) -> str:
        q = urllib.parse.quote(query)
        return ("https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/"
                f"cfstandards/results.cfm?start_search=1&keyword={q}")

    def parse_payload(self, raw: bytes, query: str) -> Any:
        html = raw.decode("utf-8", "replace")
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S)
        parsed: List[Dict[str, Any]] = []
        for row in rows:
            cells_raw = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)
            if len(cells_raw) < 7:
                continue
            cells = []
            for c in cells_raw:
                t = re.sub(r"<[^>]+>", " ", c)
                t = re.sub(r"&nbsp;?", " ", t)
                t = re.sub(r"\s+", " ", t).strip()
                cells.append(t)
            if cells[0] == self._HEADER_CELL:
                continue
            # detail link (provider's own standard identification no)
            m = re.search(
                r"detail\.cfm\?standard__identification_no=(\d+)", row)
            parsed.append({
                "date_of_entry": cells[0],
                "specialty_task_group_area": cells[1],
                "recognition_number": cells[2],
                "extent_of_recognition": cells[3],
                "standards_organization": cells[4],
                "standard_designation": cells[5],
                "standard_title": cells[6],
                "standard_identification_no": m.group(1) if m else None,
            })
        if not parsed and "cfstandards" not in html and "<tr" not in html:
            # A body that is neither the results app nor has any table
            # row at all is a gateway/maintenance page -> unparseable.
            raise ValueError("fda_recognized_standards: no results table "
                             "in response body")
        return {"records": parsed}

    def normalize_payload(self, payload: Any, query: str, raw_sha: str) -> List[SourceRecord]:
        out: List[SourceRecord] = []
        for r in payload.get("records", [])[: self.LIMIT]:
            rec_no = r.get("recognition_number")
            designation = r.get("standard_designation")
            if not rec_no or not designation:
                # A row without the provider's recognition number or
                # designation cannot be identified -> not a record
                # (Art. VI: no invented identifiers).
                continue
            ident = r.get("standard_identification_no")
            uri = ("https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/"
                   "cfstandards/detail.cfm?standard__identification_no="
                   f"{ident}") if ident else (
                   "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/"
                   "cfstandards/search.cfm")
            out.append(SourceRecord(
                source_id=self.SOURCE_ID,
                role="STANDARDS",
                record_id=f"fda_std:rec:{rec_no}",
                title=f"{r.get('standards_organization','')} {designation}",
                uri=uri,
                retrieved_at=utc_now(),
                query=query,
                raw_payload_sha256=raw_sha,
                normalized={
                    "recognition_number": rec_no,
                    "standard_designation": designation,
                    "standard_title": r.get("standard_title"),
                    "standards_organization": r.get("standards_organization"),
                    "specialty_task_group_area": r.get("specialty_task_group_area"),
                    "extent_of_recognition": r.get("extent_of_recognition"),
                    "date_of_entry": r.get("date_of_entry"),
                    "standard_identification_no": ident,
                },
                provenance={
                    "provider": self.SOURCE_ID,
                    "api": "accessdata.fda.gov/scripts/cdrh/cfdocs/cfstandards",
                    "query": query,
                    "raw_payload_sha256": raw_sha,
                    "retrieved_at": utc_now(),
                },
                epistemic_state="OBSERVED",
                limitations=FDA_STDS_LIMITATIONS,
            ))
        return out


class EcfrTitle21Connector(ConnectorBase):
    """eCFR Title 21 (Food and Drugs) — structure + section full text.

    Query grammar (exact, two forms):
      "<part>"        e.g. "888"   -> structure records for that part
      "<part>.<sec>"  e.g. "820.1" -> full text record for that section
    Anything else raises at build_url (deterministic grammar, not fuzzy).
    """

    SOURCE_ID = "ecfr_title21"
    ROLES = ("STANDARDS",)
    HEALTH_QUERY = "888"            # Orthopedic Devices part — measured
    LIMIT = 200

    _SECTION_RE = re.compile(r"^(\d{2,4})\.(\d{1,4}([a-z]?)(-\d+)?)$")

    def build_url(self, query: str) -> str:
        q = (query or "").strip()
        if self._SECTION_RE.match(q):
            return (f"https://www.ecfr.gov/api/versioner/v1/full/"
                    f"{ECFR_ISSUE_DATE}/title-21.xml?part={int(q.split('.')[0])}"
                    f"&section={urllib.parse.quote(q)}")
        if q.isdigit() and 1 <= int(q) <= 1299:
            return (f"https://www.ecfr.gov/api/versioner/v1/structure/"
                    f"{ECFR_ISSUE_DATE}/title-21.json?chapter=I&subchapter=H"
                    f"&part={int(q)}")
        raise ValueError(
            "ecfr_title21 query grammar: '<part>' (e.g. 888) or "
            f"'<part>.<section>' (e.g. 820.1); got {query!r}")

    def parse_payload(self, raw: bytes, query: str) -> Any:
        q = (query or "").strip()
        if self._SECTION_RE.match(q):
            xml = raw.decode("utf-8", "replace")
            if "<section" not in xml and "<DIV" not in xml and "body" not in xml.lower():
                raise ValueError("ecfr full-text response is not a section body")
            # strip tags to exact text (the section text is the evidence)
            text = re.sub(r"<[^>]+>", " ", xml)
            text = re.sub(r"\s+", " ", text).strip()
            if not text:
                raise ValueError("ecfr section body empty")
            return {"kind": "section", "text": text}
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict) or "children" not in payload:
            raise ValueError("ecfr structure payload missing children")
        return {"kind": "structure", "payload": payload}

    def _walk(self, node: Dict[str, Any], part: str, subpart: Optional[str],
              out: List[Dict[str, Any]]) -> None:
        typ = node.get("type")
        ident = str(node.get("identifier", ""))
        label = node.get("label", "")
        if typ == "subpart":
            subpart = label
        if typ == "section":
            out.append({
                "part": part,
                "subpart": subpart,
                "section": ident,
                "label": label,
            })
        for child in node.get("children", []):
            self._walk(child, part, subpart, out)

    def normalize_payload(self, payload: Any, query: str, raw_sha: str) -> List[SourceRecord]:
        out: List[SourceRecord] = []
        if payload.get("kind") == "section":
            text = payload["text"]
            sec = (query or "").strip()
            out.append(SourceRecord(
                source_id=self.SOURCE_ID,
                role="STANDARDS",
                record_id=f"ecfr:21cfr:{sec}",
                title=f"21 CFR § {sec}",
                uri=(f"https://www.ecfr.gov/current/title-21/section-{sec}"),
                retrieved_at=utc_now(),
                query=query,
                raw_payload_sha256=raw_sha,
                normalized={
                    "cfr_title": 21,
                    "section": sec,
                    "section_text": text[:8000],
                    "issue_date": ECFR_ISSUE_DATE,
                },
                provenance={
                    "provider": self.SOURCE_ID,
                    "api": "www.ecfr.gov/api/versioner/v1",
                    "issue_date": ECFR_ISSUE_DATE,
                    "query": query,
                    "raw_payload_sha256": raw_sha,
                    "retrieved_at": utc_now(),
                },
                epistemic_state="OBSERVED",
                limitations=ECFR_LIMITATIONS,
            ))
            return out
        # structure records: walk to the requested part
        root = payload["payload"]
        node = root
        # descend chapter -> subchapter -> part
        for child in node.get("children", []):
            if str(child.get("identifier")) == "I":
                node = child
                break
        for child in node.get("children", []):
            if str(child.get("identifier")) == "H":
                node = child
                break
        part_node = None
        for child in node.get("children", []):
            if str(child.get("identifier")) == str(int(query)):
                part_node = child
                break
        if part_node is None:
            return out  # provider answered; part has no sections here
        part_label = part_node.get("label", "")
        sections: List[Dict[str, Any]] = []
        self._walk(part_node, str(int(query)), None, sections)
        for s in sections[: self.LIMIT]:
            out.append(SourceRecord(
                source_id=self.SOURCE_ID,
                role="STANDARDS",
                record_id=f"ecfr:21cfr:{s['section']}",
                title=s["label"],
                uri=(f"https://www.ecfr.gov/current/title-21/"
                     f"section-{s['section']}"),
                retrieved_at=utc_now(),
                query=query,
                raw_payload_sha256=raw_sha,
                normalized={
                    "cfr_title": 21,
                    "part": s["part"],
                    "part_label": part_label,
                    "subpart": s["subpart"],
                    "section": s["section"],
                    "issue_date": ECFR_ISSUE_DATE,
                },
                provenance={
                    "provider": self.SOURCE_ID,
                    "api": "www.ecfr.gov/api/versioner/v1",
                    "issue_date": ECFR_ISSUE_DATE,
                    "query": query,
                    "raw_payload_sha256": raw_sha,
                    "retrieved_at": utc_now(),
                },
                epistemic_state="OBSERVED",
                limitations=ECFR_LIMITATIONS,
            ))
        return out

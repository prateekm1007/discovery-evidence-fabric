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
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from discovery_fabric.source_registry.base import (
    ConnectorBase, SourceRecord, STATUS_OK, utc_now, SSL_CONTEXT,
    USER_AGENT, sha256_bytes,
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
    """FDA Recognized Consensus Standards database (HTML results table).

    DEFECT MEASURED LIVE 2026-08-30 (QUERY_RELEVANCE battery): the CDRH
    results.cfm endpoint IGNORES every probed server-side filter param
    (keyword=, title=, stdsgn=, designation= — all return the identical
    first catalog page of 100 rows). Pagination DOES work (pgnum=N).
    Behavior before this finding: the connector believed the server had
    filtered by keyword and shipped the first 100 catalog rows as if
    they answered the query — status-OK-plus-irrelevant-records (the
    Lens-DSL / OSTI `query=` defect class).

    Honest semantics AFTER the fix: the connector fetches a PAGE_BUDGET
    window of the recognition catalog (newest-first, 100 rows/page) and
    filters CLIENT-SIDE on designation+title. A zero-match result is a
    definitive EMPTY **of the fetched window only** — every record and
    the registry known_gaps carry that limitation; it is NEVER evidence
    that a standard is not recognized (Art. XXI.3/XXV).
    """

    SOURCE_ID = "fda_recognized_standards"
    ROLES = ("STANDARDS",)
    HEALTH_QUERY = "10993"          # biocompatibility family — measured
    LIMIT = 100
    #: catalog pages fetched per query (100 rows each) — ENGINEERING
    #: budget: 3 pages bounds the cost of one query while giving the
    #: client-side filter a 300-row window (disclosed per record).
    PAGE_BUDGET = 3

    _HEADER_CELL = "Date of Entry"

    def build_url(self, query: str, page: int = 1) -> str:
        # NOTE: no server-side query param is trusted (measured ignored);
        # the query is applied client-side in normalize_payload.
        return ("https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/"
                f"cfstandards/results.cfm?start_search=1&pgnum={page}")

    def fetch_pages(self, timeout: int) -> List[Tuple[bytes, str]]:
        """Fetch the PAGE_BUDGET catalog window via the base _request
        (so status discipline + test interception both hold)."""
        out: List[Tuple[bytes, str]] = []
        for page in range(1, self.PAGE_BUDGET + 1):
            url = self.build_url("", page=page)
            body, status, http_status, error, _rem = self._request(
                url, timeout=timeout)
            if status != STATUS_OK or not body:
                if page == 1:
                    # first page failed: the provider did not answer
                    raise RuntimeError(
                        f"first catalog page failed: status={status} "
                        f"http={http_status} error={error!r}")
                break  # later-page failure: window is what we have
            out.append((body, sha256_bytes(body)))
            if not self._page_has_rows(body):
                break  # exhausted catalog before budget
        return out

    def _page_has_rows(self, body: bytes) -> bool:
        return b"detail.cfm?standard__identification_no=" in body

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

    def search(self, query: str, timeout: int = 25) -> "SourceQueryResult":  # type: ignore[override]
        """Catalog-window search: fetch pages, parse, client-side filter.

        The base _execute() contract assumes one request per query; this
        connector needs PAGE_BUDGET requests + a client filter. Custody
        (retrieval-log entry with the union sha of fetched pages) is
        preserved via _finish.
        """
        import hashlib
        from discovery_fabric.source_registry.base import SourceQueryResult as SQR
        t0 = time.time()
        try:
            pages = self.fetch_pages(timeout)
        except urllib.error.HTTPError as e:
            status = ("UNAVAILABLE" if e.code >= 500 else
                      "AUTH_FAILED" if e.code in (401, 403) else
                      "RATE_LIMITED" if e.code == 429 else "SEARCH_FAILED")
            return self._finish(SQR(source_id=self.SOURCE_ID, status=status,
                                    ok=False, http_status=e.code,
                                    latency_ms=int((time.time() - t0) * 1000),
                                    error=str(e)[:300], query=query,
                                    retrieved_at=utc_now()),
                                query, self.build_url(""), None)
        except RuntimeError as e:  # first page failed (provider answer class)
            from discovery_fabric.source_registry.base import STATUS_UNAVAILABLE as _U
            return self._finish(SQR(source_id=self.SOURCE_ID,
                                    status=_U, ok=False,
                                    latency_ms=int((time.time() - t0) * 1000),
                                    error=str(e)[:300], query=query,
                                    retrieved_at=utc_now()),
                                query, self.build_url(""), None)
        except Exception as e:  # noqa: BLE001
            return self._finish(SQR(source_id=self.SOURCE_ID,
                                    status="SEARCH_FAILED", ok=False,
                                    latency_ms=int((time.time() - t0) * 1000),
                                    error=repr(e)[:300], query=query,
                                    retrieved_at=utc_now()),
                                query, self.build_url(""), None)
        all_records: List[Dict[str, Any]] = []
        union_sha = hashlib.sha256()
        n_pages = 0
        try:
            for body, sha in pages:
                n_pages += 1
                union_sha.update(sha.encode("ascii"))
                payload = self.parse_payload(body, query)
                all_records.extend(payload.get("records", []))
        except ValueError as e:
            # gateway/maintenance page: unparseable body (old contract kept)
            return self._finish(SQR(source_id=self.SOURCE_ID,
                                    status="PARSE_FAILED", ok=False,
                                    latency_ms=int((time.time() - t0) * 1000),
                                    error=str(e)[:300], query=query,
                                    retrieved_at=utc_now()),
                                query, self.build_url(""), None)
        raw_sha = union_sha.hexdigest()
        qterms = [t for t in re.split(r"[^a-z0-9]+", query.lower()) if t]
        filtered = []
        for r in all_records:
            hay = " ".join([r.get("standard_designation") or "",
                             r.get("standard_title") or ""]).lower()
            if not qterms or all(t in hay for t in qterms):
                filtered.append(r)
        dedup: Dict[str, Dict[str, Any]] = {}
        for r in filtered:
            key = r.get("recognition_number")
            if key and key not in dedup:
                dedup[key] = r
        records = self.normalize_payload(
            {"records": list(dedup.values())[: self.LIMIT]}, query, raw_sha)
        for rec in records:
            rec.normalized["client_side_filtered"] = True
            rec.normalized["catalog_window_pages"] = n_pages
            rec.normalized["window_rows_scanned"] = len(all_records)
            rec.limitations = list(rec.limitations or []) + [
                f"server-side keyword filter measured broken 2026-08-30; "
                f"query applied client-side over a {n_pages}-page "
                f"({len(all_records)}-row) catalog window — EMPTY means "
                f"'not in the fetched window', NEVER 'not recognized'"
            ]
        status = "OK" if records else "EMPTY"
        return self._finish(SQR(source_id=self.SOURCE_ID, status=status,
                                ok=True,
                                latency_ms=int((time.time() - t0) * 1000),
                                records=records, query=query,
                                retrieved_at=utc_now()),
                            query, self.build_url(""), raw_sha)

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

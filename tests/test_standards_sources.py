"""Standards-role tests (L2) — hermetic, no network, Art. XVII hardened.

Covers:
- FDA Recognized Standards connector: table parse, header-row skip,
  recognition-number record ids, EMPTY-on-zero-rows, gateway-page
  PARSE_FAILED.
- eCFR connector: query grammar (part / part.section), structure walk,
  section full-text records, grammar violation rejection.
- Standards registry: the directive's 5 columns per row, custody-bound;
  rows without required columns are REJECTED (disclosed, never dropped
  silently); verification classes derive from title grammar; QMSR
  anchor requires eCFR custody.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from discovery_fabric.source_registry import retrieval_log
from discovery_fabric.source_registry.base import (
    STATUS_EMPTY, STATUS_OK, SourceRecord, utc_now,
)
from discovery_fabric.source_registry.connectors.standards import (
    EcfrTitle21Connector, FdaRecognizedStandardsConnector,
)
from discovery_fabric.knowledge_graph.standards_registry import (
    build_standards_registry, registry_row_from_record,
    verification_requirement_class,
)
from discovery_fabric.source_registry.registry import (
    SOURCE_REGISTRY, validate_registry,
)


@pytest.fixture(autouse=True)
def _isolated_log(tmp_path, monkeypatch):
    monkeypatch.setattr(retrieval_log, "LOG_PATH", tmp_path / "retrieval_log.jsonl")
    yield


def _wire(connector, payload: bytes | None, http_status=200, status=STATUS_OK):
    if payload is not None:
        connector._request = lambda url, timeout=25: (
            payload, status, http_status, None, None)
    else:
        connector._request = lambda url, timeout=25: (
            None, status, http_status, "injected", None)
    return connector


def _row(cells, ident="45631"):
    tds = "".join(f"<td>{c}</td>" for c in cells)
    link = (f'<a href="detail.cfm?standard__identification_no={ident}">'
            f"{cells[6]}</a>")
    return f'<tr>{tds[: 0]}<td>{cells[0]}</td><td>{cells[1]}</td><td>{cells[2]}</td><td>{cells[3]}</td><td>{cells[4]}</td><td>{cells[5]}</td><td>{link}</td></tr>'


FDA_HTML = (
    b"<html><body><table>"
    + _row(["12/23/2024", "Anesthesiology", "1-183", "Complete", "ASTM",
            "G175-24",
            "Standard Test Method for Evaluating the Ignition Sensitivity and Fault Tolerance of Oxygen Regulators"],
           ident="45631").encode()
    + _row(["06/01/2023", "Biocompatibility", "2-248", "Complete", "ISO",
            "10993-14 First edition 2001-11-15",
            "Biological evaluation of medical devices - Part 14: Identification and quantification of degradation products from ceramics"],
           ident="45000").encode()
    + b"</table></body></html>"
)

FDA_HTML_HEADER_ONLY = (
    b"<html><body><table>"
    b"<tr><td>Date of Entry</td><td>Specialty Task Group Area</td>"
    b"<td>Recognition Number</td><td>Extent of Recognition</td>"
    b"<td>Standards Developing Organization</td>"
    b"<td>Standard Designation Number and Date</td>"
    b"<td>Standard Title</td></tr>"
    b"</table></body></html>"
)

GATEWAY_HTML = b"<html><body><h1>Service Unavailable</h1></body></html>"

ECFR_STRUCTURE = {
    "identifier": "21", "label": "Title 21", "type": "title",
    "children": [{
        "identifier": "I", "label": "Chapter I", "type": "chapter",
        "children": [{
            "identifier": "H", "label": "Subchapter H", "type": "subchapter",
            "children": [{
                "identifier": "888", "type": "part",
                "label": "Part 888\u2014Orthopedic Devices",
                "children": [
                    {"identifier": "A", "type": "subpart",
                     "label": "Subpart A\u2014General Provisions",
                     "children": [
                         {"identifier": "888.1", "type": "section",
                          "label": "\u00a7 888.1 Scope."},
                         {"identifier": "888.3", "type": "section",
                          "label": "\u00a7 888.3 Effective dates."},
                     ]},
                ],
            }],
        }],
    }],
}

ECFR_SECTION_XML = (
    b"<section><head>\xa7 820.1 Scope.</head>"
    b"<p>(a) Applicability. Current good manufacturing practice (CGMP) "
    b"requirements are set forth in this quality management system "
    b"regulation (QMSR).</p></section>"
)


class TestFdaRecognizedStandards:
    def test_results_table_parses_to_records(self):
        # 2026-08-30 contract change: server-side keyword filter measured
        # BROKEN; the connector now client-side filters a page window.
        # Query '10993' -> only the ISO 10993-14 row survives the filter
        # (the old assertion len==2 pinned the unfiltered-catalog defect).
        c = _wire(FdaRecognizedStandardsConnector(), FDA_HTML)
        res = c.search("10993")
        assert res.status == STATUS_OK
        assert len(res.records) == 1
        assert res.records[0].record_id == "fda_std:rec:2-248"
        assert any("client-side" in x for x in res.records[0].limitations)
        # an empty query returns the whole window
        res_all = c.search("")
        assert res_all.status == STATUS_OK
        assert len(res_all.records) == 2
        r0 = res.records[0]
        assert r0.normalized["specialty_task_group_area"] == "Biocompatibility"
        assert r0.normalized["extent_of_recognition"] == "Complete"
        assert r0.normalized["standard_identification_no"] == "45000"
        assert r0.uri.endswith("standard__identification_no=45000")

    def test_header_row_is_skipped_not_a_record(self):
        c = _wire(FdaRecognizedStandardsConnector(), FDA_HTML_HEADER_ONLY)
        res = c.search("10993")
        assert res.status == STATUS_EMPTY
        assert res.ok is True and res.records == []

    def test_gateway_page_is_parse_failed(self):
        # Art. XXV: a maintenance page is a failure, not 'no standards'
        c = _wire(FdaRecognizedStandardsConnector(), GATEWAY_HTML)
        res = c.search("10993")
        assert res.status == "PARSE_FAILED"
        assert res.ok is False

    def test_row_without_recognition_number_dropped_honestly(self):
        # cell[2] empty -> no provider identity -> not a record (Art. VI)
        row = _row(["2024", "Cardiovascular", "", "Complete", "ISO",
                    "5840-1", "Title"], ident="1")
        html = b"<html><body><table>" + row.encode() + b"</table></body></html>"
        c = _wire(FdaRecognizedStandardsConnector(), html)
        res = c.search("q")
        assert res.status == STATUS_EMPTY

    def test_limitations_disclose_recognition_semantics(self):
        c = _wire(FdaRecognizedStandardsConnector(), FDA_HTML)
        res = c.search("10993")
        assert any("Recognition by FDA" in l for l in res.records[0].limitations)


class TestEcfrTitle21:
    def test_part_query_builds_structure_url(self):
        url = EcfrTitle21Connector().build_url("888")
        assert "structure" in url and "part=888" in url

    def test_section_query_builds_full_text_url(self):
        url = EcfrTitle21Connector().build_url("820.1")
        assert "full" in url and "section=820.1" in url

    def test_bad_query_grammar_rejected(self):
        with pytest.raises(ValueError, match="grammar"):
            EcfrTitle21Connector().build_url("orthopedic devices")

    def test_structure_walk_produces_section_records(self):
        c = _wire(EcfrTitle21Connector(),
                  json.dumps(ECFR_STRUCTURE).encode())
        res = c.search("888")
        assert res.status == STATUS_OK
        ids = [r.record_id for r in res.records]
        assert "ecfr:21cfr:888.1" in ids
        assert all(r.normalized["part"] == "888" for r in res.records)
        assert res.records[0].normalized["part_label"].startswith("Part 888")

    def test_section_query_returns_text_record(self):
        c = _wire(EcfrTitle21Connector(), ECFR_SECTION_XML)
        res = c.search("820.1")
        assert res.status == STATUS_OK
        assert len(res.records) == 1
        assert "quality management system regulation" in res.records[0].normalized["section_text"]
        assert res.records[0].normalized["issue_date"] == "2026-08-27"

    def test_non_section_body_is_parse_failed(self):
        c = _wire(EcfrTitle21Connector(), b"404 Not Found")
        res = c.search("820.1")
        assert res.status == "PARSE_FAILED"


class TestVerificationClasses:
    def test_test_method_from_title(self):
        v = verification_requirement_class(
            "Standard Test Method for Evaluating the Ignition Sensitivity", "G175-24")
        assert "test_method" in v["verification_classes"]

    def test_biocompatibility_from_10993(self):
        v = verification_requirement_class(
            "Biological evaluation of medical devices", "10993-14")
        assert "biocompatibility" in v["verification_classes"]

    def test_unclassified_is_explicit(self):
        v = verification_requirement_class("Weird title", "XYZ-1")
        assert v["verification_classes"] == ["unclassified"]

    def test_qmsr_anchor_present(self):
        v = verification_requirement_class("Spec for stents", "ISO 25539")
        assert "820" in v["qmsr_anchor"] and "ISO 13485" in v["qmsr_anchor"]


class TestStandardsRegistry:
    def _std_record(self):
        return SourceRecord(
            source_id="fda_recognized_standards", role="STANDARDS",
            record_id="fda_std:rec:2-248",
            title="ISO 10993-14",
            uri="https://example.org", retrieved_at=utc_now(),
            query="10993", raw_payload_sha256="abc123",
            normalized={
                "recognition_number": "2-248",
                "standard_designation": "10993-14 First edition 2001-11-15",
                "standard_title": "Biological evaluation of medical devices - Part 14",
                "standards_organization": "ISO",
                "specialty_task_group_area": "Biocompatibility",
                "extent_of_recognition": "Complete",
                "date_of_entry": "06/01/2023",
                "standard_identification_no": "45000",
            },
            provenance={"provider": "fda_recognized_standards"},
        )

    def _ecfr_record(self):
        return SourceRecord(
            source_id="ecfr_title21", role="STANDARDS",
            record_id="ecfr:21cfr:820.1", title="21 CFR § 820.1",
            uri="https://www.ecfr.gov/current/title-21/section-820.1",
            retrieved_at=utc_now(), query="820.1", raw_payload_sha256="def456",
            normalized={"cfr_title": 21, "section": "820.1",
                        "section_text": "scope", "issue_date": "2026-08-27"},
            provenance={"provider": "ecfr_title21"},
        )

    def test_row_has_all_five_directive_columns(self):
        row = registry_row_from_record(self._std_record())
        for col in ("standard", "device_type", "engineering_purpose",
                    "applicability", "verification_requirement"):
            assert col in row
        assert row["standard"]["designation"].startswith("10993-14")
        assert row["device_type"]["specialty_task_group_area"] == "Biocompatibility"
        assert row["applicability"]["extent_of_recognition"] == "Complete"

    def test_row_carries_custody(self):
        row = registry_row_from_record(self._std_record())
        assert row["custody"][0]["record_id"] == "fda_std:rec:2-248"
        assert row["custody"][0]["raw_payload_sha256"] == "abc123"

    def test_incomplete_record_rejected_and_disclosed(self):
        rec = self._std_record()
        rec.normalized["standard_title"] = None
        assert registry_row_from_record(rec) is None
        reg = build_standards_registry([rec])
        assert reg["row_count"] == 0
        assert len(reg["rejected_rows"]) == 1
        assert reg["rejected_rows"][0]["reason"]

    def test_qmsr_anchor_requires_ecfr_custody(self):
        reg = build_standards_registry([self._std_record()], [self._ecfr_record()])
        anchors = reg["qmsr_anchor"]["ecfr_custody"]
        assert len(anchors) == 1
        assert anchors[0]["section"] == "820.1"
        assert anchors[0]["raw_payload_sha256"] == "def456"

    def test_qmsr_anchor_empty_without_ecfr_records(self):
        reg = build_standards_registry([self._std_record()])
        assert reg["qmsr_anchor"]["ecfr_custody"] == []


class TestStandardsRegistryWiring:
    def test_sources_resolve_to_real_connectors(self):
        from discovery_fabric.source_registry.health import load_connector
        for sid in ("fda_recognized_standards", "ecfr_title21"):
            cls = load_connector(sid)
            assert cls is not None and cls.SOURCE_ID == sid

    def test_registry_validates_clean_after_standards_edit(self):
        assert validate_registry() == []

    def test_iso_astm_catalogues_stay_honestly_not_integrated(self):
        # No public API measured for raw catalogue browse; the STANDARDS
        # role is covered through FDA recognition + eCFR instead.
        for sid in ("iso_catalogue", "astm_standards"):
            assert SOURCE_REGISTRY[sid]["connector"] == "" or \
                SOURCE_REGISTRY[sid]["connector"] is None or \
                not SOURCE_REGISTRY[sid]["connector"]

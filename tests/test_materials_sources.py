"""Materials-role tests (L1) — hermetic, no network, Art. XVII hardened.

Covers:
- COD OPTIMADE connector: URL building, payload parse, normalization
  custody, epistemic split stamping (PROPERTY_DATA / NOT_ESTABLISHED).
- NIST WebBook connector: species-page parse, EMPTY-on-zero-species,
  multi-match records.
- Materials Project connector: implemented + header-auth key path (key
  absent -> no header; present -> X-API-KEY, never in URL).
- materials_policy: the PROPERTY_DATA vs IMPLANT_SUITABILITY split is
  mechanically enforced (negative control: a MATERIALS-role record may
  NOT assert suitability; Art. IV no-fallback).
- Registry wiring: cod_optimade + nist_webbook + materials_project all
  resolve to real connectors; registry still validates clean.
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
from discovery_fabric.source_registry.connectors.materials import (
    CodOptimadeConnector, MaterialsProjectConnector, NistWebbookConnector,
)
from discovery_fabric.source_registry.materials_policy import (
    DIMENSION_IMPLANT_SUITABILITY,
    DIMENSION_PROPERTY_DATA,
    IMPLANT_SUITABILITY_NOT_ESTABLISHED,
    assert_implant_suitability_role,
    classify_material_evidence,
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


COD_PAYLOAD = {
    "data": [
        {
            "id": "2300273",
            "type": "structures",
            "attributes": {
                "chemical_formula_descriptive": "Ca5HO13P3",
                "_cod_chemname": "hydroxyapatite",
                "_cod_mineral": None,
                "_cod_sg": "P 63/m",
                "_cod_a": 9.424, "_cod_b": 9.424, "_cod_c": 6.879,
                "elements": ["Ca", "H", "O", "P"],
                "_cod_journal": "Acta Crystallographica",
                "_cod_year": "2004",
            },
        },
    ],
    "meta": {"data_returned": 6, "data_available": 534832,
             "more_data_available": True},
}

WEBBOOK_SPECIES_HTML = (
    b"<html><head><title>zirconium dioxide</title></head><body>"
    b'<a href="/cgi/cbook.cgi?ID=C1314234&Units=SI#Thermo-Co">x</a>'
    b"<h2>Formula: O<sub>2</sub>Zr</h2>"
    b"Molecular weight: 123.223 | zirconium dioxide"
    b"Condensed phase thermochemistry data</body></html>"
)


class TestCodOptimade:
    def test_url_contains_chemname_filter_and_limit(self):
        url = CodOptimadeConnector().build_url("hydroxyapatite")
        assert "crystallography.net/cod/optimade/v1/structures" in url
        assert "page_limit=5" in url
        assert "_cod_chemname" in url

    def test_parse_rejects_non_optimade_body(self):
        with pytest.raises(ValueError):
            CodOptimadeConnector().parse_payload(b'{"nope": 1}', "q")

    def test_normalize_stamps_epistemic_split(self):
        c = _wire(CodOptimadeConnector(), json.dumps(COD_PAYLOAD).encode())
        res = c.search("hydroxyapatite")
        assert res.status == STATUS_OK
        assert len(res.records) == 1
        r = res.records[0]
        assert r.record_id == "cod:2300273"
        assert r.normalized["evidence_dimension"] == DIMENSION_PROPERTY_DATA
        assert r.normalized["implant_suitability"] == IMPLANT_SUITABILITY_NOT_ESTABLISHED
        assert r.normalized["space_group"] == "P 63/m"
        # custody chain complete (Art. XXI.9)
        assert r.provenance["raw_payload_sha256"] == res.records[0].raw_payload_sha256
        assert r.uri.startswith("https://www.crystallography.net/cod/")

    def test_total_hits_is_query_returned_not_db_population(self):
        # meta.data_available (534832) is the WHOLE DB; the query
        # population is meta.data_returned (6). Sample != population.
        c = _wire(CodOptimadeConnector(), json.dumps(COD_PAYLOAD).encode())
        res = c.search("hydroxyapatite")
        assert res.total_hits == 6

    def test_zero_structures_is_provider_answered_empty(self):
        c = _wire(CodOptimadeConnector(), json.dumps({"data": [], "meta": {}}).encode())
        res = c.search("unobtainium ceramic")
        assert res.status == STATUS_EMPTY
        assert res.ok is True

    def test_limitations_disclose_property_data_boundary(self):
        c = _wire(CodOptimadeConnector(), json.dumps(COD_PAYLOAD).encode())
        res = c.search("hydroxyapatite")
        assert any("NOT implant suitability" in l for l in res.records[0].limitations)


class TestNistWebbook:
    def test_species_page_normalizes_with_cas_id(self):
        c = _wire(NistWebbookConnector(), WEBBOOK_SPECIES_HTML)
        res = c.search("zirconium dioxide")
        assert res.status == STATUS_OK
        r = res.records[0]
        assert r.record_id.startswith("nist_webbook:cas:")
        assert r.normalized["molecular_weight"] == "123.223"
        assert "Condensed phase thermochemistry data" in r.normalized["property_sections"]
        assert r.normalized["evidence_dimension"] == DIMENSION_PROPERTY_DATA

    def test_page_without_title_is_parse_failed_not_empty(self):
        # Art. XXV: unparseable is unparseable; it is not 'no data exists'
        c = _wire(NistWebbookConnector(), b"<html><body>gateway error</body></html>")
        res = c.search("anything")
        assert res.status == "PARSE_FAILED"
        assert res.ok is False

    def test_zero_species_page_is_empty_and_ok(self):
        # a valid page that yields no species = provider answered: zero
        html = b"<html><head><title>NIST Chemistry WebBook</title></head><body>Search Results none</body></html>"
        c = _wire(NistWebbookConnector(), html)
        res = c.search("definitely not a chemical")
        assert res.status == STATUS_EMPTY
        assert res.ok is True


class TestMaterialsProject:
    def test_connector_registered_and_implemented(self):
        rec = SOURCE_REGISTRY["materials_project"]
        assert rec["connector"].endswith("MaterialsProjectConnector")

    def test_key_never_in_url(self):
        c = MaterialsProjectConnector()
        url = c.build_url("TiO2")
        assert "api.materialsproject.org" in url
        assert "X-API-KEY" not in url and "api_key" not in url

    def test_no_key_means_no_auth_header(self):
        assert MaterialsProjectConnector().request_headers() == {}

    def test_with_key_header_only(self, monkeypatch):
        import discovery_fabric.source_registry.connectors.materials as m
        monkeypatch.setattr(m, "load_key", lambda name: "SECRET" if name == "MATERIALS_PROJECT_API_KEY" else "")
        h = MaterialsProjectConnector().request_headers()
        assert h == {"X-API-KEY": "SECRET"}

    def test_computational_epistemic_state(self):
        payload = {"data": [{"id": "mp-2657", "attributes": {
            "chemical_formula_descriptive": "TiO2",
            "nelements": 2}}], "meta": {}}
        c = _wire(MaterialsProjectConnector(), json.dumps(payload).encode())
        res = c.search("TiO2")
        assert res.status == STATUS_OK
        assert res.records[0].epistemic_state == "COMPUTATIONAL"
        assert res.records[0].normalized["implant_suitability"] == IMPLANT_SUITABILITY_NOT_ESTABLISHED


class TestMaterialsPolicy:
    def test_materials_role_cannot_establish_implant_suitability(self):
        # negative control (Art. XVII): the forbidden promotion attempt
        with pytest.raises(ValueError, match="no silent semantic promotion|implant suitability"):
            assert_implant_suitability_role("MATERIALS")

    def test_chemistry_role_cannot_either(self):
        with pytest.raises(ValueError):
            assert_implant_suitability_role("CHEMISTRY")

    def test_regulatory_role_may(self):
        assert_implant_suitability_role("REGULATORY")
        assert_implant_suitability_role("CLINICAL")
        assert_implant_suitability_role("ADVERSE_EVENT")
        assert_implant_suitability_role("STANDARDS")

    def test_classifier_ignores_claimant_attachments(self):
        # Art. III: the VERIFIER decides the dimension from the source
        # role, not from what a claimant wrote into the record.
        r = SourceRecord(
            source_id="cod_optimade", role="MATERIALS", record_id="cod:1",
            title="x", uri="u", retrieved_at=utc_now(), query="q",
            raw_payload_sha256="h",
            normalized={"implant_suitability": "CLAIMED_SUITABLE"},
            provenance={"provider": "cod_optimade"},
        )
        cls = classify_material_evidence(r)
        assert cls["implant_suitability"] == IMPLANT_SUITABILITY_NOT_ESTABLISHED

    def test_unknown_role_stays_unknown(self):
        cls = classify_material_evidence(
            SourceRecord(source_id="s", role="WHATEVER", record_id="1",
                         title="t", uri="u", retrieved_at=utc_now(),
                         query="q", raw_payload_sha256="h",
                         normalized={}, provenance={}))
        assert cls["evidence_dimension"] == "UNKNOWN"


class TestRegistryWiring:
    def test_materials_sources_resolve_to_real_connectors(self):
        from discovery_fabric.source_registry.health import load_connector
        for sid in ("cod_optimade", "nist_webbook", "materials_project"):
            cls = load_connector(sid)
            assert cls is not None, sid
            assert cls.SOURCE_ID == sid

    def test_registry_validates_clean_after_materials_edit(self):
        assert validate_registry() == []

    def test_placeholder_nist_materials_removed(self):
        assert "nist_materials" not in SOURCE_REGISTRY

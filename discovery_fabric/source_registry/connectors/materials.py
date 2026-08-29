"""Materials connectors: Crystallography Open Database (OPTIMADE),
NIST Chemistry WebBook, and Materials Project (OPTIMADE).

CEO lifecycle directive (2026-08-29): close the MATERIALS authority role
with real integrations that pass the 7-step proof chain —
CONNECTOR_EXISTS -> LIVE_REQUEST -> PARSE -> NORMALIZE -> PROVENANCE ->
RETRIEVAL_LOG -> HEALTH. No README-only integrations.

EPISTEMIC SPLIT (directive, verbatim intent): "distinguish chemistry/
property data from actual implant-material suitability." Every record from
these sources carries:

    evidence_dimension  = "PROPERTY_DATA"
    implant_suitability = "NOT_ESTABLISHED_BY_THIS_SOURCE"

A computed/measured bulk property or a crystal structure is evidence about
MATTER, not evidence that the material is fit for implantation. Implant
suitability may only be established by REGULATORY (510(k)/PMA material
descriptions), CLINICAL, ADVERSE_EVENT (material-related failures), or
STANDARDS (ISO 10993-class recognized standards) sources — see
materials_policy.py, which mechanically enforces the distinction.

Constitutional anchors:
- Art. XXI.3: provider failure is NOT absence. statuses stay distinct.
- Art. VI / XXI.9: record ids are the provider's own ids; hashes are of
  the provider's own payload bytes.
- Art. XXV: an unparseable page is PARSE_FAILED, never 'no data exists'.
"""

from __future__ import annotations

import json
import re
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

from discovery_fabric.source_registry.base import (
    ConnectorBase, SourceRecord, STATUS_OK, utc_now, sha256_bytes,
)
from discovery_fabric.source_registry.keys import load_key
from discovery_fabric.source_registry.materials_policy import (
    DIMENSION_PROPERTY_DATA,
    IMPLANT_SUITABILITY_NOT_ESTABLISHED,
    materials_limitations,
)


class CodOptimadeConnector(ConnectorBase):
    """Crystallography Open Database via the OPTIMADE v1 API.

    Measured LIVE 2026-08-29 (probe: _cod_chemname CONTAINS
    "hydroxyapatite" -> Ca5HO13P3, space group P 63/m). COD is an open
    academic crystallography consortium database: peer-reviewed published
    CIF structures. Free, no key.
    """

    SOURCE_ID = "cod_optimade"
    ROLES = ("MATERIALS",)
    HEALTH_QUERY = "hydroxyapatite"
    LIMIT = 5

    def build_url(self, query: str) -> str:
        f = urllib.parse.quote(f'_cod_chemname CONTAINS "{query}"')
        return (f"https://www.crystallography.net/cod/optimade/v1/structures"
                f"?filter={f}&page_limit={self.LIMIT}")

    def parse_payload(self, raw: bytes, query: str) -> Any:
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise ValueError("cod_optimade payload missing data list")
        return payload

    def extract_total_hits(self, payload: Any) -> Optional[int]:
        # OPTIMADE meta.data_returned = entries matching THIS query
        # (meta.data_available is the whole-database count — never use
        # that as the query population; sample != population, Art. XV).
        meta = (payload or {}).get("meta") or {}
        v = meta.get("data_returned")
        return v if isinstance(v, int) else None

    def normalize_payload(self, payload: Any, query: str, raw_sha: str) -> List[SourceRecord]:
        out: List[SourceRecord] = []
        for entry in payload.get("data", []):
            a = entry.get("attributes") or {}
            cod_id = entry.get("id")
            if cod_id is None:
                continue
            formula = a.get("chemical_formula_descriptive") or a.get("_cod_calcformula")
            chemname = a.get("_cod_chemname")
            mineral = a.get("_cod_mineral")
            sg = a.get("_cod_sg") or a.get("_cod_sgHall")
            title = chemname or mineral or formula or f"COD {cod_id}"
            out.append(SourceRecord(
                source_id=self.SOURCE_ID,
                role="MATERIALS",
                record_id=f"cod:{cod_id}",
                title=title,
                uri=f"https://www.crystallography.net/cod/{cod_id}.html",
                retrieved_at=utc_now(),
                query=query,
                raw_payload_sha256=raw_sha,
                normalized={
                    "cod_id": cod_id,
                    "chemical_formula": formula,
                    "chemical_name": chemname,
                    "mineral_name": mineral,
                    "space_group": sg,
                    "cell_a": a.get("_cod_a"),
                    "cell_b": a.get("_cod_b"),
                    "cell_c": a.get("_cod_c"),
                    "elements": a.get("elements"),
                    "journal": a.get("_cod_journal"),
                    "year": a.get("_cod_year"),
                    "evidence_dimension": DIMENSION_PROPERTY_DATA,
                    "implant_suitability": IMPLANT_SUITABILITY_NOT_ESTABLISHED,
                },
                provenance={
                    "provider": self.SOURCE_ID,
                    "api": "www.crystallography.net/cod/optimade/v1",
                    "query": query,
                    "raw_payload_sha256": raw_sha,
                    "retrieved_at": utc_now(),
                },
                epistemic_state="OBSERVED",
                limitations=materials_limitations("COD"),
            ))
        return out


class NistWebbookConnector(ConnectorBase):
    """NIST Chemistry WebBook — authoritative NIST thermophysical property
    reference data (by species name).

    Measured LIVE 2026-08-29 (probe: 'zirconium dioxide' -> species page,
    MW 123.223, condensed-phase thermochemistry present; 'titanium' ->
    CAS 7440-32-6 species page). Free, no key. HTML responses are parsed
    with anchored extraction; a page that yields zero species is a
    provider-answered EMPTY (HTTP 200 + parsed + 0 records), never a
    silent failure.
    """

    SOURCE_ID = "nist_webbook"
    ROLES = ("MATERIALS",)
    HEALTH_QUERY = "zirconium dioxide"
    LIMIT = 10

    _SECTION_LABELS = [
        "Gas phase thermochemistry data",
        "Condensed phase thermochemistry data",
        "Phase change data",
        "Reaction thermochemistry data",
        "Gas phase ion energetics data",
        "Ion clustering data",
        "Spectral data",
        "Other data",
    ]

    def build_url(self, query: str) -> str:
        q = urllib.parse.quote(query)
        return f"https://webbook.nist.gov/cgi/cbook.cgi?Name={q}&Units=SI"

    def parse_payload(self, raw: bytes, query: str) -> Any:
        html = raw.decode("utf-8", "replace")
        # Structural parse requirements (not invented thresholds): a
        # WebBook response page carries a <title> element. Anything else
        # (bare gateway body, empty bytes) is PARSE_FAILED, never EMPTY.
        title_m = re.search(r"<title>(.*?)</title>", html, re.S)
        if not title_m:
            raise ValueError("nist_webbook page has no title element")
        title = re.sub(r"\s+", " ", title_m.group(1)).strip()

        # single-species page: has a CAS anchor (ID=C######)
        cas_m = re.search(r"[?&]ID=C(\d{2,9})\d?", html)
        formula_m = re.search(
            r"<h2[^>]*>\s*Formula:\s*([^<]+)</h2>", html)
        mw_m = re.search(r"Molecular weight[^\d]*([\d.]+)", html)
        sections = [s for s in self._SECTION_LABELS if s in html]

        # multi-match 'Search Results' page: species rows
        species: List[Dict[str, Any]] = []
        for _href, cas_digits, name in re.findall(
                r'href="(/cgi/cbook\.cgi\?ID=C(\d{2,9})[^"]*)"[^>]*>(.*?)</a>',
                html):
            label = re.sub(r"<[^>]+>", " ", name)
            label = re.sub(r"\s+", " ", label).strip()
            if label:
                species.append({"cas_number": cas_digits, "name": label})
        return {
            "title": title,
            "cas_id": (cas_m.group(1) if cas_m else None),
            "formula": (formula_m.group(1).strip() if formula_m else None),
            "molecular_weight": (mw_m.group(1) if mw_m else None),
            "property_sections": sections,
            "species_links": species,
            "is_search_results": "Search Results" in html,
        }

    def normalize_payload(self, payload: Any, query: str, raw_sha: str) -> List[SourceRecord]:
        out: List[SourceRecord] = []
        cas = payload.get("cas_id")
        if cas:
            name = payload.get("title") or query
            out.append(SourceRecord(
                source_id=self.SOURCE_ID,
                role="MATERIALS",
                record_id=f"nist_webbook:cas:{cas}",
                title=name,
                uri=f"https://webbook.nist.gov/cgi/cbook.cgi?ID=C{cas}&Units=SI",
                retrieved_at=utc_now(),
                query=query,
                raw_payload_sha256=raw_sha,
                normalized={
                    "species_name": name,
                    "cas_registry_number": cas,
                    "formula": payload.get("formula"),
                    "molecular_weight": payload.get("molecular_weight"),
                    "property_sections": payload.get("property_sections"),
                    "evidence_dimension": DIMENSION_PROPERTY_DATA,
                    "implant_suitability": IMPLANT_SUITABILITY_NOT_ESTABLISHED,
                },
                provenance={
                    "provider": self.SOURCE_ID,
                    "api": "webbook.nist.gov/cgi/cbook.cgi",
                    "query": query,
                    "raw_payload_sha256": raw_sha,
                    "retrieved_at": utc_now(),
                },
                epistemic_state="OBSERVED",
                limitations=materials_limitations("NIST WebBook"),
            ))
        # multi-match pages contribute one record per listed species
        for sp in payload.get("species_links", [])[: self.LIMIT]:
            out.append(SourceRecord(
                source_id=self.SOURCE_ID,
                role="MATERIALS",
                record_id=f"nist_webbook:match:{sp.get('name', '')[:60]}",
                title=sp.get("name", ""),
                uri="https://webbook.nist.gov/cgi/cbook.cgi?Name="
                    + urllib.parse.quote(query) + "&Units=SI",
                retrieved_at=utc_now(),
                query=query,
                raw_payload_sha256=raw_sha,
                normalized={
                    "species_name": sp.get("name"),
                    "match_only": True,
                    "evidence_dimension": DIMENSION_PROPERTY_DATA,
                    "implant_suitability": IMPLANT_SUITABILITY_NOT_ESTABLISHED,
                },
                provenance={
                    "provider": self.SOURCE_ID,
                    "api": "webbook.nist.gov/cgi/cbook.cgi",
                    "query": query,
                    "raw_payload_sha256": raw_sha,
                    "retrieved_at": utc_now(),
                },
                epistemic_state="OBSERVED",
                limitations=materials_limitations("NIST WebBook"),
            ))
        return out


class MaterialsProjectConnector(ConnectorBase):
    """Materials Project via OPTIMADE v1 — computed (DFT) materials
    properties for inorganic compounds.

    Connector IMPLEMENTED (this file). Measured 2026-08-29: HTTP 403 with
    provider body 'IP address or ASN has been (temporarily) blocked' —
    cloud egress ASN is blocked before credentials are even evaluated.
    Health therefore derives UNAVAILABLE (live_request_works=False) until
    (a) a MATERIALS_PROJECT_API_KEY is provisioned in .env.keys AND
    (b) the ASN block clears. Both conditions are external to this repo;
    the honest chain state is recorded, never gamed (Art. XV).

    API key goes in the X-API-KEY header — never in the URL — so the
    retrieval log stays credential-free (S-01 discipline).
    """

    SOURCE_ID = "materials_project"
    ROLES = ("MATERIALS",)
    HEALTH_QUERY = "TiO2"
    LIMIT = 5

    def request_headers(self) -> Dict[str, str]:
        key = load_key("MATERIALS_PROJECT_API_KEY")
        return {"X-API-KEY": key} if key else {}

    def build_url(self, query: str) -> str:
        f = urllib.parse.quote(f'chemical_formula_descriptive CONTAINS "{query}"')
        return (f"https://api.materialsproject.org/optimade/v1/structures"
                f"?filter={f}&page_limit={self.LIMIT}")

    def parse_payload(self, raw: bytes, query: str) -> Any:
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise ValueError("materials_project payload missing data list")
        return payload

    def normalize_payload(self, payload: Any, query: str, raw_sha: str) -> List[SourceRecord]:
        out: List[SourceRecord] = []
        for entry in payload.get("data", []):
            a = entry.get("attributes") or {}
            mid = entry.get("id")
            formula = a.get("chemical_formula_descriptive") or a.get("chemical_formula_reduced")
            out.append(SourceRecord(
                source_id=self.SOURCE_ID,
                role="MATERIALS",
                record_id=f"mp:{mid}",
                title=formula or f"Materials Project {mid}",
                uri=f"https://materialsproject.org/materials/{mid}",
                retrieved_at=utc_now(),
                query=query,
                raw_payload_sha256=raw_sha,
                normalized={
                    "material_id": mid,
                    "chemical_formula": formula,
                    "nelements": a.get("nelements"),
                    "evidence_dimension": DIMENSION_PROPERTY_DATA,
                    "implant_suitability": IMPLANT_SUITABILITY_NOT_ESTABLISHED,
                },
                provenance={
                    "provider": self.SOURCE_ID,
                    "api": "api.materialsproject.org/optimade/v1",
                    "query": query,
                    "raw_payload_sha256": raw_sha,
                    "retrieved_at": utc_now(),
                },
                epistemic_state="COMPUTATIONAL",
                limitations=materials_limitations("Materials Project"),
            ))
        return out

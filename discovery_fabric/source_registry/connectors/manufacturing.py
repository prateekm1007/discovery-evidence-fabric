"""Manufacturing connectors — the MANUFACTURING authority role.

CEO lifecycle directive (2026-08-29): close the MANUFACTURING role with
structured evidence for

    extrusion, injection molding, machining, additive manufacturing,
    laser processing, coatings, microfabrication, medical-device
    sterilization

so the engine can reason: mechanism -> candidate manufacturing route ->
process constraint -> quality risk -> verification.

Three live-source lenses (all measured against live APIs this session):

1. fda_pma_supplements — FDA-reviewed manufacturing/process-change
   supplements to PMA approvals (openFDA device/pma.json). Measured:
   56,995 supplement records; reasons include 'Process Change -
   Manufacturer/Sterilizer/Packager/Supplier' and 'Change
   Design/Components/Specifications/Material'. This is REAL regulatory
   evidence of manufacturing changes on approved devices.

2. manufacturing_literature — EuropePMC (same measured REST transport
   as the SCIENTIFIC role) queried through the 8-process taxonomy, with
   exact-span constraint/risk/verification extraction from abstracts.

3. gudid_sterilization — GUDID sterilization fields on marketed devices
   (openFDA device/udi.json; measured 5,083,929 records carry the
   sterilization block, e.g. sterilization_methods='Moist Heat or Steam
   Sterilization'). Device-level sterilization evidence with FDA
   provenance.

Constitutional anchors: Art. XXI.3 (statuses distinct), Art. II (exact
spans — the literature extractor quotes the abstract's own sentences,
never paraphrase), Art. VI (supplement/PMA numbers are FDA's own ids).
"""

from __future__ import annotations

import json
import re
import urllib.parse
from typing import Any, Dict, List

from discovery_fabric.source_registry.base import (
    ConnectorBase, SourceRecord, utc_now,
)
from discovery_fabric.source_registry.connectors.openfda import _OpenFdaBase

#: The directive's 8-process taxonomy (exact process names + the
#: literature query terms that target them on EuropePMC).
PROCESS_TAXONOMY = {
    "extrusion": ["extrusion", "extruded"],
    "injection_molding": ["injection molding", "injection moulding"],
    "machining": ["machining", "micromachining", "turning", "milling"],
    "additive_manufacturing": ["additive manufacturing", "3D printing",
                               "selective laser melting", "electron beam melting",
                               "direct metal laser sintering"],
    "laser_processing": ["laser processing", "laser cutting", "laser welding",
                         "laser ablation", "laser micromachining"],
    "coatings": ["coating", "coated", "thin film coating", "surface coating",
                 "hydroxyapatite coating", "diamond-like carbon"],
    "microfabrication": ["microfabrication", "MEMS", "cleanroom",
                         "photolithography", "etching"],
    "sterilization": ["sterilization", "sterilisation", "sterility assurance",
                      "ethylene oxide", "steam sterilization", "e-beam",
                      "gamma irradiation"],
}

# Grammar for exact-span extraction from abstracts (Art. II: the span is
# the abstract's own sentence, quoted — never paraphrased).
_CONSTRAINT_GRAMMAR = re.compile(
    r"\b(tolerance|dimensional|shrinkage|residual stress|porosity|"
    r"surface roughness|roughness|warping|crack|delamination|"
    r"microstructure|grain size|defect|defects|oxidation|degradation|"
    r"heat-affected|process window|thermal budget|viscosity|flow rate|"
    r"cooling rate|dose|dose mapping|overexposure|temperature limit)\b", re.I)
_RISK_GRAMMAR = re.compile(
    r"\b(failure|fail|risk|defect|reject|rework|compromise|invalidat|"
    r"unacceptable|nonconformance|non-conformance|leach|leaching|"
    r"residual|toxic|embrittl|corrosion|infection|contaminat|fatigue)\b", re.I)
_VERIFICATION_GRAMMAR = re.compile(
    r"\b(validat|verification|qualif|process capability|Cpk|"
    r"statistical process control|SPC|inspection|nondestructive|"
    r"non-destructive|testing|measured|characteriz|audit|release criteria|"
    r"acceptance)\b", re.I)

PMA_SUPPLEMENT_LIMITATIONS = [
    "PMA supplements evidence REGULATORY REVIEW of a manufacturing "
    "change; the supplement reason text is FDA's categorical label, not "
    "the full engineering content of the change.",
    "Coverage is PMA-class devices only; 510(k)-class manufacturing "
    "changes are not represented in this endpoint.",
    "A supplement's existence is not evidence the change caused any "
    "subsequent device failure or improvement.",
]

MANUFACTURING_LITERATURE_LIMITATIONS = [
    "Literature records carry peer-reviewed process evidence; abstract "
    "spans are exact quotes, but abstracts may not contain the study's "
    "full constraint data.",
    "Process classification is derived from title/abstract grammar "
    "(exact terms of the 8-process taxonomy); a record matching no "
    "taxonomy term carries process=None and is still retrievable.",
    "In vitro / engineering studies do not establish clinical outcomes.",
]

GUDID_STERILIZATION_LIMITATIONS = [
    "Sterilization fields are manufacturer-declared GUDID fields, not "
    "validated sterilization cycles.",
    "sterilization_methods is free text; method taxonomies are the "
    "labeler's own wording.",
    "A device's declared method is not evidence of its sterilization "
    "VALIDATION (see ISO 17665/11135/11137 families via the STANDARDS "
    "role).",
]


def _sentences_with(text: str, rx: re.Pattern) -> List[str]:
    """Exact sentences of the abstract matching the grammar (Art. II:
    exact spans, quoted from the provider's own text)."""
    if not text:
        return []
    out = []
    for s in re.split(r"(?<=[.!?])\s+", text):
        if s and rx.search(s):
            out.append(s.strip()[:400])
        if len(out) >= 5:
            break
    return out


def classify_process(text: str) -> List[str]:
    """Which taxonomy processes does this text name exactly?"""
    found = []
    for process, terms in PROCESS_TAXONOMY.items():
        if any(t.lower() in (text or "").lower() for t in terms):
            found.append(process)
    return found


class PmaManufacturingSupplementConnector(_OpenFdaBase):
    """FDA PMA manufacturing/process-change supplements (openFDA)."""

    SOURCE_ID = "fda_pma_supplements"
    ROLES = ("MANUFACTURING",)
    ENDPOINT = "device/pma.json"
    HEALTH_QUERY = ('supplement_reason:"Process Change - '
                    'Manufacturer/Sterilizer/Packager/Supplier"')
    LIMIT = 5

    def to_record(self, r: Dict[str, Any], query: str, raw_sha: str) -> SourceRecord:
        pma = r.get("pma_number") or ""
        sup = r.get("supplement_number") or ""
        reason = r.get("supplement_reason") or ""
        stype = r.get("supplement_type") or ""
        rec_id = f"pma-sup:{pma}S{sup}" if (pma and sup) else f"pma-sup:{pma}"
        is_process = "process change" in reason.lower()
        is_sterilizer = "sterilizer" in reason.lower()
        is_material = ("material" in reason.lower()
                       or "design/components" in reason.lower())
        devices = r.get("devices") or []
        return SourceRecord(
            source_id=self.SOURCE_ID,
            role="MANUFACTURING",
            record_id=rec_id,
            title=(f"{pma} S{sup} ({stype}): {reason[:70]}"),
            uri=(f"https://api.fda.gov/device/pma.json?search=pma_number:{pma}"
                 if pma else "https://api.fda.gov/device/pma.json"),
            retrieved_at=utc_now(),
            query=query,
            raw_payload_sha256=raw_sha,
            normalized={
                "pma_number": pma,
                "supplement_number": sup,
                "supplement_type": stype,
                "supplement_reason": reason,
                "trade_name": r.get("trade_name"),
                "applicant": r.get("applicant"),
                "generic_name": r.get("generic_name"),
                "decision_code": r.get("decision_code"),
                "decision_date": r.get("decision_date"),
                "product_code": r.get("product_code"),
                "devices": devices,
                "classification": {
                    "is_process_change": is_process,
                    "is_sterilizer_change": is_sterilizer,
                    "is_material_or_design_change": is_material,
                },
            },
            provenance=self._prov(query, raw_sha),
            epistemic_state="OBSERVED",
            limitations=PMA_SUPPLEMENT_LIMITATIONS,
        )


class ManufacturingLiteratureConnector(ConnectorBase):
    """EuropePMC through the 8-process manufacturing taxonomy."""

    SOURCE_ID = "manufacturing_literature"
    ROLES = ("MANUFACTURING",)
    HEALTH_QUERY = "additive manufacturing"
    LIMIT = 10

    def build_url(self, query: str) -> str:
        q = urllib.parse.quote(
            f'("{query}") AND ("medical device" OR implant)')
        return ("https://www.ebi.ac.uk/europepmc/webservices/rest/search"
                f"?query={q}&format=json&pageSize={self.LIMIT}&resultType=core")

    def parse_payload(self, raw: bytes, query: str) -> Any:
        payload = json.loads(raw.decode("utf-8"))
        result = (payload or {}).get("resultList") or {}
        if not isinstance(result.get("result"), list):
            raise ValueError("manufacturing_literature payload missing resultList.result")
        return payload

    def normalize_payload(self, payload: Any, query: str, raw_sha: str) -> List[SourceRecord]:
        results = (payload or {}).get("resultList", {}).get("result", [])
        out: List[SourceRecord] = []
        for r in results:
            rid = r.get("id") or r.get("pmid") or ""
            abstract = (r.get("abstractText") or "").strip()
            title = r.get("title", "") or ""
            blob = f"{title} {abstract}"
            processes = classify_process(blob)
            out.append(SourceRecord(
                source_id=self.SOURCE_ID,
                role="MANUFACTURING",
                record_id=f"mfg-lit:{rid}",
                title=title,
                uri=f"https://europepmc.org/article/{r.get('source', 'MED')}/{rid}",
                retrieved_at=utc_now(),
                query=query,
                raw_payload_sha256=raw_sha,
                normalized={
                    "pmid": r.get("pmid"),
                    "doi": r.get("doi"),
                    "title": title,
                    "abstract": abstract[:4000] or None,
                    "processes": processes,
                    "process_constraint_spans": _sentences_with(abstract, _CONSTRAINT_GRAMMAR),
                    "quality_risk_spans": _sentences_with(abstract, _RISK_GRAMMAR),
                    "verification_spans": _sentences_with(abstract, _VERIFICATION_GRAMMAR),
                    "journal": r.get("journalTitle"),
                    "publication_date": r.get("firstPublicationDate"),
                },
                provenance={
                    "provider": self.SOURCE_ID,
                    "api": "www.ebi.ac.uk/europepmc/webservices/rest",
                    "query": query,
                    "raw_payload_sha256": raw_sha,
                    "retrieved_at": utc_now(),
                },
                epistemic_state="OBSERVED",
                limitations=MANUFACTURING_LITERATURE_LIMITATIONS,
            ))
        return out


class GudidSterilizationConnector(_OpenFdaBase):
    """GUDID sterilization fields on marketed devices (openFDA UDI)."""

    SOURCE_ID = "gudid_sterilization"
    ROLES = ("MANUFACTURING",)
    ENDPOINT = "device/udi.json"
    HEALTH_QUERY = 'brand_name:"catheter" AND _exists_:sterilization'
    LIMIT = 10

    def to_record(self, r: Dict[str, Any], query: str, raw_sha: str) -> SourceRecord:
        key = r.get("public_device_record_key") or ""
        brand = r.get("brand_name") or ""
        ster = r.get("sterilization") or {}
        methods = ster.get("sterilization_methods")
        method_list = None
        if methods:
            method_list = [m.strip() for m in re.split(r"\s+or\s+|;", methods) if m.strip()]
        return SourceRecord(
            source_id=self.SOURCE_ID,
            role="MANUFACTURING",
            record_id=f"gudid-ster:{key or brand[:40]}",
            title=f"{brand}: {methods or ('sterile' if str(ster.get('is_sterile')).lower()=='true' else 'non-sterile')}",
            uri=(f"https://api.fda.gov/device/udi.json?search=public_device_record_key:{key}"
                 if key else "https://api.fda.gov/device/udi.json"),
            retrieved_at=utc_now(),
            query=query,
            raw_payload_sha256=raw_sha,
            normalized={
                "public_device_record_key": key,
                "brand_name": brand,
                "company_name": r.get("company_name"),
                "is_sterile": ster.get("is_sterile"),
                "is_sterilization_prior_use": ster.get("is_sterilization_prior_use"),
                "sterilization_methods": methods,
                "sterilization_method_list": method_list,
                "device_description": r.get("device_description"),
                "product_codes": [
                    (p or {}).get("code") for p in (r.get("product_codes") or [])
                    if isinstance(p, dict)
                ],
                "processes": (["sterilization"] if (methods or ster.get("is_sterile")) else []),
            },
            provenance=self._prov(query, raw_sha),
            epistemic_state="OBSERVED",
            limitations=GUDID_STERILIZATION_LIMITATIONS,
        )

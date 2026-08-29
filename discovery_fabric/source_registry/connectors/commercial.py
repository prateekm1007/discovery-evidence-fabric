"""Commercial connector — GUDID commercial layer via openFDA UDI.

CEO lifecycle directive (2026-08-29): close the COMMERCIAL authority role
with defensible provenance only:

    commercialized device / marketed product / company / product
    category / competitive mechanism / pricing-procurement signal /
    commercial failure-recall

Source: the FDA Global UDI Database (GUDID), served through openFDA's
device/udi.json endpoint (the same measured transport as fda_udi, but a
COMMERCIAL normalization lens — separate custody entries per role). This
is the FDA's own registry of marketed devices: company, brand, product
codes, GMDN terms, commercial distribution status ("In Commercial
Distribution" / "Not in Commercial Distribution"), distribution end
date, device counts, package configuration.

COMMERCIAL_DIMENSION_COVERAGE (below) is the honest coverage map for the
directive's commercial sub-capabilities:

    COMMERCIALIZED_DEVICE        COVERED            gudid_commercial
    MARKETED_PRODUCT             COVERED            gudid_commercial
    COMPANY                      COVERED            gudid_commercial
    PRODUCT_CATEGORY             COVERED            gudid_commercial
    COMPETITIVE_MECHANISM        GRAPH_DERIVED      device->patent edges
    PRICING_PROCUREMENT_SIGNAL   NOT_COVERED        no open source with
                                                   defensible provenance
                                                   exists; licensed
                                                   market intelligence
                                                   required (honest gap)
    COMMERCIAL_FAILURE_RECALL    OVERLAY            RECALL role records
                                                   (fda_recall), bound
                                                   in the knowledge graph

'Use only sources with defensible provenance' — no scraped pricing
pages, no vendor marketing claims. The pricing gap stays a gap (Art.
XXV: unknown is a legitimate state; it is never filled with noise).

Constitutional anchors: Art. XXI.3 (statuses), Art. VI (manufacturer-
declared fields are labeled as such), Art. XV (the gap is disclosed).
"""

from __future__ import annotations

from typing import Any, Dict, List

from discovery_fabric.source_registry.base import SourceRecord, utc_now
from discovery_fabric.source_registry.connectors.openfda import _OpenFdaBase

GUDID_COMMERCIAL_LIMITATIONS = [
    "GUDID fields are manufacturer-declared and not independently "
    "verified by FDA",
    "Commercial distribution status is labeler-declared at record "
    "version level; a record may lag a firm's actual market exit",
    "GUDID covers US-marketed devices with UDI obligations; global "
    "market presence is out of scope",
    "PRICING_PROCUREMENT_SIGNAL: NOT covered by any integrated source — "
    "pricing/procurement reality requires licensed market intelligence",
]

#: The directive's commercial sub-capabilities and their honest state.
#: A dimension is only 'COVERED' when a real query returns usable
#: records with provenance (the coverage report re-derives this
#: mechanically from measured source health — this map only names the
#: dimension->source binding).
COMMERCIAL_DIMENSION_COVERAGE = {
    "COMMERCIALIZED_DEVICE": {
        "state": "COVERED", "source": "gudid_commercial",
        "evidence": "GUDID public device records (DI, versions)"},
    "MARKETED_PRODUCT": {
        "state": "COVERED", "source": "gudid_commercial",
        "evidence": "brand_name + commercial_distribution_status"},
    "COMPANY": {
        "state": "COVERED", "source": "gudid_commercial",
        "evidence": "company_name + labeler_duns_number"},
    "PRODUCT_CATEGORY": {
        "state": "COVERED", "source": "gudid_commercial",
        "evidence": "product_codes + gmdn_terms"},
    "COMPETITIVE_MECHANISM": {
        "state": "GRAPH_DERIVED",
        "source": "knowledge-graph device->patent edges",
        "evidence": "competitive mechanism is inferred from patent "
                    "coverage of comparable devices, not asserted from "
                    "a commercial source"},
    "PRICING_PROCUREMENT_SIGNAL": {
        "state": "NOT_COVERED", "source": None,
        "evidence": "no open source with defensible provenance; licensed "
                    "market intelligence required (honest gap)"},
    "COMMERCIAL_FAILURE_RECALL": {
        "state": "OVERLAY", "source": "fda_recall",
        "evidence": "recall enforcement records joined to commercial "
                    "products through evidence-bound graph edges"},
}


class GudidCommercialConnector(_OpenFdaBase):
    """GUDID commercial lens: marketed-product reality with FDA
    provenance. Measured LIVE 2026-08-29 (brand_name:'hip system' ->
    'Consensus Hip System', Shalby Advanced Technologies, In Commercial
    Distribution)."""

    SOURCE_ID = "gudid_commercial"
    ROLES = ("COMMERCIAL",)
    ENDPOINT = "device/udi.json"
    HEALTH_QUERY = 'brand_name:"hip system"'
    LIMIT = 10

    def to_record(self, r: Dict[str, Any], query: str, raw_sha: str) -> SourceRecord:
        key = r.get("public_device_record_key") or ""
        brand = r.get("brand_name") or ""
        company = r.get("company_name") or ""
        product_codes = [
            (p or {}).get("code") for p in (r.get("product_codes") or [])
            if isinstance(p, dict)
        ]
        product_code_names = [
            (p or {}).get("name") for p in (r.get("product_codes") or [])
            if isinstance(p, dict)
        ]
        gmdn = [
            (g or {}).get("gmdn_pt_name")
            for g in (r.get("gmdn_terms") or []) if isinstance(g, dict)
        ]
        status = r.get("commercial_distribution_status")
        return SourceRecord(
            source_id=self.SOURCE_ID,
            role="COMMERCIAL",
            record_id=f"gudid-commercial:{key or brand[:40]}",
            title=f"{brand} ({company})",
            uri=(f"https://api.fda.gov/device/udi.json?search=public_device_record_key:{key}"
                 if key else "https://api.fda.gov/device/udi.json"),
            retrieved_at=utc_now(),
            query=query,
            raw_payload_sha256=raw_sha,
            normalized={
                "public_device_record_key": key,
                "brand_name": brand,
                "company_name": company,
                "labeler_duns_number": r.get("labeler_duns_number"),
                "version_or_model_number": r.get("version_or_model_number"),
                "catalog_number": r.get("catalog_number"),
                "product_codes": product_codes,
                "product_code_names": product_code_names,
                "gmdn_pt_names": gmdn,
                "commercial_distribution_status": status,
                "commercial_distribution_end_date": r.get("commercial_distribution_end_date"),
                "is_on_market": status == "In Commercial Distribution",
                "device_count_in_base_package": r.get("device_count_in_base_package"),
                "is_kit": r.get("is_kit"),
                "is_combination_product": r.get("is_combination_product"),
                "publish_date": r.get("publish_date"),
                "public_version_status": r.get("public_version_status"),
            },
            provenance=self._prov(query, raw_sha),
            epistemic_state="OBSERVED",
            limitations=GUDID_COMMERCIAL_LIMITATIONS,
        )

#!/usr/bin/env python
"""EVIDENCE_COVERAGE_REPORT generator — the lifecycle-layer acceptance
artifact (CEO directive 2026-08-29, point 6).

Ten mechanically derived coverage dimensions:

    SCIENCE_COVERAGE, PATENT_COVERAGE, DEVICE_COVERAGE,
    REGULATORY_COVERAGE, CLINICAL_COVERAGE, FAILURE_COVERAGE,
    MATERIAL_COVERAGE, MANUFACTURING_COVERAGE, STANDARDS_COVERAGE,
    COMMERCIAL_COVERAGE

Coverage rule (directive, verbatim intent): "A source role is 'covered'
only if a real query returns usable records with provenance."

This is STRONGER than the source-health check: it does not ask whether
a connector is healthy, it RUNS a real domain query per dimension and
verifies that usable records with full custody (record_id +
raw_payload_sha256 + provenance block + limitations) actually come back.
A dimension whose probe returns a provider failure is NOT covered —
provider failure is not absence (Art. XXI.3) and not coverage either.

Usable-record rule: >= 1 record with non-empty record_id,
raw_payload_sha256, provenance.provider, and non-empty limitations
(the epistemic caveats ride with the data — Art. XV).

Art. XXVI disclosure: BUILDER-MEASURED. Reproduction command:

    python scripts/evidence_coverage_report.py

Usage:
    python scripts/evidence_coverage_report.py [--timeout 40]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.source_registry.base import (  # noqa: E402
    STATUS_EMPTY, STATUS_OK,
)
from discovery_fabric.source_registry.connectors.commercial import (  # noqa: E402
    GudidCommercialConnector,
)
from discovery_fabric.source_registry.connectors.manufacturing import (  # noqa: E402
    ManufacturingLiteratureConnector,
)
from discovery_fabric.source_registry.connectors.materials import (  # noqa: E402
    CodOptimadeConnector,
)
from discovery_fabric.source_registry.connectors.openfda import (  # noqa: E402
    FdaRecallConnector, FdaUdiConnector, Fda510kConnector,
)
from discovery_fabric.source_registry.connectors.scientific import (  # noqa: E402
    EuropePmcConnector,
)
from discovery_fabric.source_registry.connectors.standards import (  # noqa: E402
    EcfrTitle21Connector, FdaRecognizedStandardsConnector,
)
from discovery_fabric.source_registry.registry import (  # noqa: E402
    sources_for_role,
)

REPORT_DIR = REPO_ROOT / "artifacts" / "coverage"

#: The directive's 10 dimensions, each with the authority roles it
#: covers and a REAL domain query (not a keyword-only health probe).
DIMENSION_PROBES = [
    {"dimension": "SCIENCE_COVERAGE", "roles": ["SCIENTIFIC"],
     "probe": ("What is known scientifically about hydroxyapatite "
               "biocompatibility"),
     "query": "hydroxyapatite implant osseointegration"},
    {"dimension": "PATENT_COVERAGE", "roles": ["PATENT"],
     "probe": "What patent families exist for hip implant wear",
     "query": 'hip implant wear'},
    {"dimension": "DEVICE_COVERAGE", "roles": ["DEVICE_IDENTITY"],
     "probe": "Device identity for marketed hip systems",
     "query": 'brand_name:"hip system"'},
    {"dimension": "REGULATORY_COVERAGE", "roles": ["REGULATORY"],
     "probe": "510(k) clearances for hip prostheses",
     "query": 'device_name:"hip prosthesis"'},
    {"dimension": "CLINICAL_COVERAGE", "roles": ["CLINICAL"],
     "probe": "Trials studying hip implants",
     "query": "hip implant"},
    {"dimension": "FAILURE_COVERAGE", "roles": ["ADVERSE_EVENT", "RECALL"],
     "probe": "Adverse events and recalls for hip prostheses",
     "query": 'product_description:"hip prosthesis"'},
    {"dimension": "MATERIAL_COVERAGE", "roles": ["MATERIALS"],
     "probe": "Material property data for hydroxyapatite",
     "query": "hydroxyapatite"},
    {"dimension": "MANUFACTURING_COVERAGE", "roles": ["MANUFACTURING"],
     "probe": "Manufacturing process evidence for additive manufacturing",
     "query": "additive manufacturing"},
    {"dimension": "STANDARDS_COVERAGE", "roles": ["STANDARDS"],
     "probe": "Recognized standards for biocompatibility (10993 family)",
     "query": "10993"},
    {"dimension": "COMMERCIAL_COVERAGE", "roles": ["COMMERCIAL"],
     "probe": "Commercial reality of marketed hip systems",
     "query": 'brand_name:"hip system"'},
]


def _connector_for(dimension: str):
    """One live connector per dimension (the most reliable measured
    source for that role)."""
    if dimension == "SCIENCE_COVERAGE":
        return EuropePmcConnector()
    if dimension == "DEVICE_COVERAGE":
        return FdaUdiConnector()
    if dimension == "REGULATORY_COVERAGE":
        return Fda510kConnector()
    if dimension == "FAILURE_COVERAGE":
        return FdaRecallConnector()
    if dimension == "MATERIAL_COVERAGE":
        return CodOptimadeConnector()
    if dimension == "MANUFACTURING_COVERAGE":
        return ManufacturingLiteratureConnector()
    if dimension == "STANDARDS_COVERAGE":
        return FdaRecognizedStandardsConnector()
    if dimension == "COMMERCIAL_COVERAGE":
        return GudidCommercialConnector()
    if dimension == "PATENT_COVERAGE":
        # PatentBear is metered (20/month); Lens is the unmetered live
        # patent source — use it for the coverage probe.
        from discovery_fabric.source_registry.connectors.patents import (  # noqa: E402
            LensPatentConnector,
        )
        return LensPatentConnector()
    if dimension == "CLINICAL_COVERAGE":
        from discovery_fabric.source_registry.connectors.clinicaltrials import (  # noqa: E402
            ClinicalTrialsConnector,
        )
        return ClinicalTrialsConnector()
    raise KeyError(dimension)


def _usable(record) -> bool:
    """Usable = full custody chain + limitations attached (Art. XV/XXI.9)."""
    n = getattr(record, "normalized", None)
    return bool(
        getattr(record, "record_id", None)
        and getattr(record, "raw_payload_sha256", None)
        and isinstance(n, dict) and n
        and isinstance(getattr(record, "provenance", None), dict)
        and record.provenance.get("provider")
        and getattr(record, "limitations", None)
    )


def measure_dimension(spec: dict, timeout: int) -> dict:
    dim = spec["dimension"]
    connector = _connector_for(dim)
    result = connector.search(spec["query"], timeout=timeout)
    usable = [r for r in result.records if _usable(r)]
    custody_verified = all(
        r.provenance.get("raw_payload_sha256") == r.raw_payload_sha256
        for r in usable)
    if result.status in (STATUS_OK, STATUS_EMPTY):
        status = "COVERED" if (usable and custody_verified) else (
            "COVERED_NO_MATCH" if result.status == STATUS_EMPTY else "GAP")
    else:
        status = "PROVIDER_FAILURE"
    return {
        "dimension": dim,
        "roles_covered": spec["roles"],
        "probe": spec["probe"],
        "query": spec["query"],
        "source": result.source_id,
        "provider_status": result.status,
        "records_returned": len(result.records),
        "usable_records": len(usable),
        "custody_verified": custody_verified,
        "coverage": status,
        "sample_record": ({
            "record_id": usable[0].record_id,
            "title": usable[0].title,
            "raw_payload_sha256": usable[0].raw_payload_sha256,
            "limitations_count": len(usable[0].limitations),
        } if usable else None),
        "roles_in_registry": {
            r: len(sources_for_role(r)) for r in spec["roles"]},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=40)
    args = parser.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    dimensions = []
    for spec in DIMENSION_PROBES:
        try:
            measured = measure_dimension(spec, args.timeout)
        except Exception as e:  # noqa: BLE001 — surfaced, never swallowed
            measured = {
                "dimension": spec["dimension"],
                "roles_covered": spec["roles"],
                "coverage": "ERROR",
                "error": f"{type(e).__name__}: {e}",
            }
        dimensions.append(measured)
        print(f"{measured['coverage']:20s} {measured['dimension']} "
              f"(source={measured.get('source')}, "
              f"usable={measured.get('usable_records')})")

    covered = sum(1 for d in dimensions if d["coverage"] == "COVERED")
    report = {
        "artifact": "EVIDENCE_COVERAGE_REPORT",
        "directive": "CEO lifecycle directive 2026-08-29 point 6: ten "
                     "mechanically derived coverage dimensions; a role is "
                     "covered only if a real query returns usable records "
                     "with provenance.",
        "coverage_rule": "COVERED = live query returned >=1 usable record "
                         "(full custody chain: record_id + "
                         "raw_payload_sha256 + provenance block + "
                         "limitations attached) and custody hashes match. "
                         "COVERED_NO_MATCH = provider definitively answered "
                         "zero for this probe. PROVIDER_FAILURE = transport/"
                         "auth/rate failure — not absence, not coverage.",
        "dimensions": dimensions,
        "summary": {
            "total_dimensions": len(dimensions),
            "covered": covered,
            "covered_no_match": sum(1 for d in dimensions
                                    if d["coverage"] == "COVERED_NO_MATCH"),
            "gaps": sum(1 for d in dimensions if d["coverage"] == "GAP"),
            "provider_failures": sum(1 for d in dimensions
                                     if d["coverage"] == "PROVIDER_FAILURE"),
        },
        "builder_measured_disclosure": {
            "art_xxvi": "BUILDER-MEASURED. The reproduction command is "
                        "exactly: python scripts/evidence_coverage_report.py",
            "reproduction": "python scripts/evidence_coverage_report.py",
        },
    }

    out = REPORT_DIR / "EVIDENCE_COVERAGE_REPORT.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n{covered}/{len(dimensions)} dimensions COVERED")
    print(f"report: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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


def _role_depth_from_health(roles):
    """Join the SOURCE_HEALTH_REPORT coverage matrix (if present) to
    expose, per authority role: which sources are LIVE vs DEGRADED vs
    UNAVAILABLE vs NOT_INTEGRATED. CEO audit finding (2026-08-29):
    ROLE_COVERED must never imply comprehensive coverage — the depth
    breakdown rides WITH the verdict. A stale or missing health report
    is recorded as such, never silently omitted (Art. XXV)."""
    health_path = REPO_ROOT / "artifacts" / "source_health" / \
        "SOURCE_HEALTH_REPORT.json"
    if not health_path.exists():
        return {"available": False,
                "note": "SOURCE_HEALTH_REPORT.json not found — depth "
                        "breakback unavailable; role_covered verdict "
                        "stands alone (Art. XXV)"}
    try:
        health = json.loads(health_path.read_text())
    except Exception as e:  # noqa: BLE001
        return {"available": False, "error": f"{type(e).__name__}: {e}"}
    matrix = {m.get("role"): m for m in health.get("coverage_matrix", [])}
    out = {
        "available": True,
        "health_report_timestamp": health.get("run_timestamp"),
        "roles": {},
    }
    for role in roles:
        m = matrix.get(role)
        if not m:
            out["roles"][role] = {"in_health_matrix": False}
            continue
        out["roles"][role] = {
            "in_health_matrix": True,
            "role_coverage": m.get("coverage"),
            "live_sources": m.get("live_sources", []),
            "degraded_sources": m.get("degraded_sources", []),
            "unavailable_sources": m.get("unavailable_sources", []),
            "not_integrated_sources": m.get("not_integrated_sources", []),
            "live_depth": len(m.get("live_sources", [])),
            "registered_depth": (len(m.get("live_sources", []))
                                 + len(m.get("degraded_sources", []))
                                 + len(m.get("unavailable_sources", []))
                                 + len(m.get("not_integrated_sources", []))),
        }
    return out


def _known_gaps_for(roles):
    """Honest, MECHANICALLY RECORDED capability gaps per role. These are
    the audit's KNOWN_GAPS: role coverage (a live query answered) does
    NOT mean the role's evidence universe is complete. Each gap names
    its evidence basis — never a narrative invention (Art. XV/XXVII)."""
    gaps = []
    health_path = REPO_ROOT / "artifacts" / "source_health" / \
        "SOURCE_HEALTH_REPORT.json"
    matrix = {}
    if health_path.exists():
        try:
            matrix = {m.get("role"): m for m in json.loads(
                health_path.read_text()).get("coverage_matrix", [])}
        except Exception:  # noqa: BLE001
            matrix = {}
    for role in roles:
        m = matrix.get(role) or {}
        for sid in m.get("not_integrated_sources", []):
            gaps.append({
                "role": role,
                "kind": "SOURCE_NOT_INTEGRATED",
                "gap": f"{sid} is not integrated — the role's evidence "
                       "universe is deeper than what this engine can "
                       "query",
                "evidence": "SOURCE_HEALTH_REPORT coverage_matrix",
            })
        for sid in m.get("unavailable_sources", []):
            gaps.append({
                "role": role,
                "kind": "SOURCE_UNAVAILABLE",
                "gap": f"{sid} is registered but currently unreachable",
                "evidence": "SOURCE_HEALTH_REPORT coverage_matrix",
            })
    return gaps


#: Capability-level gaps that no single-source status captures. Each is
#: an honestly recorded limitation of what the role's coverage MEANS
#: (CEO audit 2026-08-29: the coverage report must never imply
#: comprehensive coverage).
CAPABILITY_GAPS = {
    "PATENT": "Live patent sources answer novelty-adjacent queries, but a "
              "patent search result is NOT a novelty determination "
              "(Art. XXVIII); classification-exhaustive searches remain "
              "outside the engine.",
    "MATERIALS": "Property data coverage is NOT implant-suitability "
                 "coverage — the PROPERTY_DATA vs IMPLANT_SUITABILITY "
                 "epistemic split is mechanically enforced "
                 "(materials_policy.py); Materials Project is 403-blocked "
                 "(ASN) and remains a measured gap.",
    "STANDARDS": "FDA recognized standards + eCFR are live; ISO/ASTM raw "
                 "catalogues remain NOT_INTEGRATED — the standards "
                 "universe is partially covered.",
    "COMMERCIAL": "GUDID commercial lens is live; pricing/procurement "
                  "signals remain NOT_COVERED — commercial coverage is "
                  "identity-level, not market-dynamics-level.",
    "MANUFACTURING": "PMA supplements + literature + sterilization are "
                     "live; process-capability data (Cpk, yields) is not "
                     "queryable from any integrated source.",
}


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
        "role_coverage_depth": _role_depth_from_health(spec["roles"]),
        "known_gaps": _known_gaps_for(spec["roles"]) + [
            {"role": role, "kind": "CAPABILITY_BOUNDARY",
             "gap": CAPABILITY_GAPS[role],
             "evidence": "recorded limitation (L-series measurement)"}
            for role in spec["roles"] if role in CAPABILITY_GAPS],
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
        "coverage_semantics": {
            "ROLE_COVERED": "at least ONE live source answered a real query "
                            "with usable custodied records for this role",
            "SOURCE_COVERAGE_DEPTH": "per-role live/degraded/unavailable/"
                                     "not_integrated breakdown — carried on "
                                     "every dimension (role_coverage_depth)",
            "KNOWN_GAPS": "not-integrated sources, unreachable sources, "
                          "and capability boundaries — carried on every "
                          "dimension (known_gaps)",
            "warning": "ROLE_COVERED never implies comprehensive coverage: "
                       "one live source does not mean the search universe "
                       "is complete (CEO audit 2026-08-29). Every dimension "
                       "carries its own depth breakdown and gap list.",
        },
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

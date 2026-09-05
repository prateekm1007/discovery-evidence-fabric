"""Retrieval Diversity metrics (directive section 7).

Optimize for INDEPENDENCE, not result count:
  unique_sources, unique_source_families,
  independent_source_families (via lineage.independence_clusters),
  records_by_source, overlap_ratio, source_concentration,
  plus coverage breakdowns for search-space-neutrality measurement
  (directive section 11): coverage_by_source_family,
  coverage_by_document_type, coverage_by_publication_status,
  coverage_by_lane, coverage_by_year.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from discovery_fabric.retrieval_fabric.fabric_registry import source_family
from discovery_fabric.retrieval_fabric.lineage import source_independence_score


def retrieval_diversity(canonical_records: List[Dict[str, Any]],
                        record_sources_by_canonical: Dict[str, List[str]],
                        ) -> Dict[str, Any]:
    """Diversity + independence metrics over the canonical record pool.

    Args:
      canonical_records: list of CanonicalRecord.to_dict() entries.
      record_sources_by_canonical: canonical_id -> [source_id...].
    """
    source_ids: List[str] = sorted({s for srcs in
                                    record_sources_by_canonical.values()
                                    for s in srcs})
    independence = source_independence_score(source_ids,
                                              record_sources_by_canonical)
    records_by_source: Dict[str, int] = {}
    for srcs in record_sources_by_canonical.values():
        for s in srcs:
            records_by_source[s] = records_by_source.get(s, 0) + 1
    fam_counts: Counter = Counter()
    type_counts: Counter = Counter()
    status_counts: Counter = Counter()
    lane_counts: Counter = Counter()
    year_counts: Counter = Counter()
    for rec in canonical_records:
        for s in record_sources_by_canonical.get(rec["canonical_id"], []):
            fam_counts[source_family(s)] += 1
        type_counts[rec.get("document_type") or "UNKNOWN"] += 1
        status_counts[rec.get("publication_status") or "UNKNOWN"] += 1
        lane_counts[rec.get("evidence_lane") or "REPOSITORY"] += 1
        year = str(rec.get("publication_year") or "UNKNOWN")[:4]
        year_counts[year if year[:4].isdigit() else "UNKNOWN"] += 1
    return {
        "total_canonical_records": len(canonical_records),
        "unique_sources": independence["unique_sources"],
        "unique_source_families": independence["unique_source_families"],
        "independent_source_families":
            independence["independent_source_families"],
        "source_independence_score":
            independence["source_independence_score"],
        "overlap_ratio": independence["overlap_ratio"],
        "source_concentration": independence["source_concentration"],
        "family_record_counts": independence["family_record_counts"],
        "independence_clusters": independence["independence_clusters"],
        "correlation_evidence": independence["correlation_evidence"],
        "independence_rule": independence["independence_rule"],
        "records_by_source": dict(sorted(records_by_source.items())),
        "coverage_by_source_family": dict(sorted(fam_counts.items())),
        "coverage_by_document_type": dict(sorted(type_counts.items())),
        "coverage_by_publication_status": dict(sorted(status_counts.items())),
        "coverage_by_evidence_lane": dict(sorted(lane_counts.items())),
        "coverage_by_year": dict(sorted(year_counts.items())),
        "diversity_definition": (
            "Retrieval Diversity = independent family coverage, NOT result "
            "count: a query producing 500 records from effectively one "
            "bibliographic ecosystem is weaker than a query producing 100 "
            "records across independent repositories, theses, patents, "
            "preprints and citation graphs (directive section 7)."),
    }


def blind_spot_analysis(diversity: Dict[str, Any]) -> List[str]:
    """Directive section 11: identify retrieval_blind_spots — discovery-
    system DEFECTS, not merely reporting statistics. Deterministic rules
    over the measured coverage."""
    blind_spots: List[str] = []
    lane_cov = diversity.get("coverage_by_evidence_lane", {})
    status_cov = diversity.get("coverage_by_publication_status", {})
    fam_cov = diversity.get("coverage_by_source_family", {})
    if not lane_cov.get("PATENT") and not lane_cov.get("SCHOLARLY"):
        blind_spots.append("NO_LITERATURE_COVERAGE: no SCHOLARLY or PATENT "
                           "records retrieved")
    if not lane_cov.get("PATENT"):
        blind_spots.append("PATENT_BLIND_SPOT: zero patent records — patent "
                           "prior-art coverage is a discovery-system defect "
                           "when the mechanism domain is patent-dense")
    if not (status_cov.get("THESIS")):
        blind_spots.append("THESIS_BLIND_SPOT: zero thesis/dissertation "
                           "records — journal articles are not the universe "
                           "of technical knowledge (the P13 lesson)")
    if not (status_cov.get("PREPRINT")):
        blind_spots.append("PREPRINT_BLIND_SPOT: zero preprint records")
    if len(fam_cov) < 6:
        blind_spots.append(
            f"LOW_FAMILY_COVERAGE: only {len(fam_cov)} source families "
            "contributed records (directive acceptance bar: >= 6 materially "
            "different open/free families queried successfully)")
    return blind_spots

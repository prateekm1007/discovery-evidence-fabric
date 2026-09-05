"""Source lineage / dependency graph + source_independence_score.

Directive section 3: do not create "10 sources" that are actually one
source. For every retrieved record the fabric attributes:
    origin_source, indexing_sources[], metadata_providers[],
    fulltext_source, citation_graph_sources[]

and the run-level independence model merges families that (a) declare a
shared metadata upstream AND (b) measured actual canonical-record
overlap in THIS run (union-find). Independence is measured, never
assumed (Art. XXI.7).
"""
from __future__ import annotations

from typing import Any, Dict, FrozenSet, Iterable, List, Set, Tuple

from discovery_fabric.retrieval_fabric.fabric_registry import (
    derives_from, source_family,
)


class UnionFind:
    def __init__(self) -> None:
        self.parent: Dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def _shared_upstream(a: str, b: str) -> bool:
    """True when two source_ids declare a shared derives_from upstream
    (or one derives from the other's family registrant, e.g. OpenAIRE
    aggregates DataCite)."""
    da: Set[str] = set(derives_from(a))
    db: Set[str] = set(derives_from(b))
    fa, fb = source_family(a), source_family(b)
    # one family deriving FROM the other family's registrant counts as
    # shared upstream (e.g. openaire -> datacite; unpaywall -> crossref)
    upstream_tokens_a = set(da) | ({fb.replace("doi_registrant_", "")
                                    } if f"doi_registrant_{fb.replace('doi_registrant_', '')}" else set())
    # simpler, declarative: families share upstream if their derives_from
    # sets intersect OR one lists the other's family stem as upstream
    stems_a = {u for u in da} | {fa.replace("doi_registrant_", "")}
    stems_b = {u for u in db} | {fb.replace("doi_registrant_", "")}
    return bool(stems_a & stems_b)


def independence_clusters(
    source_ids: Iterable[str],
    record_sources_by_canonical: Dict[str, List[str]],
) -> Tuple[List[List[str]], Dict[str, List[str]]]:
    """Merge families into independence clusters.

    Args:
      source_ids: sources that returned >=1 record in this run.
      record_sources_by_canonical: canonical_id -> [source_id, ...] that
        returned that canonical record (MEASURED overlap evidence).

    Returns:
      (clusters, correlation_evidence) where clusters is a list of
      source-id lists and correlation_evidence maps
      "familyA~familyB" -> [canonical_ids they overlapped on].
    """
    fam_of: Dict[str, str] = {s: source_family(s) for s in source_ids}
    fams: List[str] = sorted({fam_of[s] for s in source_ids})
    uf = UnionFind()
    for f in fams:
        uf.find(f)
    # members of each family, for overlap measurement
    fam_members: Dict[str, List[str]] = {}
    for s in source_ids:
        fam_members.setdefault(fam_of[s], []).append(s)
    correlation: Dict[str, List[str]] = {}
    # measured overlap between family pairs
    for i, fa in enumerate(fams):
        for fb in fams[i + 1:]:
            shared: List[str] = []
            members_b = set(fam_members.get(fb, []))
            for cid, srcs in record_sources_by_canonical.items():
                if any(s in members_b for s in srcs) and \
                        any(source_family(s) == fa for s in srcs):
                    shared.append(cid)
            if shared and _shared_upstream_pair(fa, fb):
                uf.union(fa, fb)
                correlation[f"{fa}~{fb}"] = shared
    clusters_map: Dict[str, List[str]] = {}
    for s in source_ids:
        clusters_map.setdefault(uf.find(fam_of[s]), []).append(s)
    clusters = [sorted(v) for v in clusters_map.values()]
    return clusters, correlation


def _shared_upstream_pair(fa: str, fb: str) -> bool:
    """Family-level shared-upstream test using the fabric registry's
    derives_from declarations (crossref/pudmed/mag/repos/... tokens)."""
    fams = _families_with_upstreams()
    ua = fams.get(fa, set())
    ub = fams.get(fb, set())
    # a family derives from the other family itself (e.g. openaire
    # derives_from datacite; unpaywall derives_from crossref)
    tokens_a = ua | {fa.replace("doi_registrant_", "").replace(
        "repository_aggregator_", "").replace("scholarly_index_", "")}
    tokens_b = ub | {fb.replace("doi_registrant_", "").replace(
        "repository_aggregator_", "").replace("scholarly_index_", "")}
    return bool(tokens_a & tokens_b)


_fams_cache: Dict[str, FrozenSet[str]] | None = None


def _families_with_upstreams() -> Dict[str, Set[str]]:
    """family -> set of upstream tokens its members declare."""
    from discovery_fabric.retrieval_fabric.fabric_registry import load_fabric_sources
    global _fams_cache
    if _fams_cache is not None:
        return {k: set(v) for k, v in _fams_cache.items()}
    out: Dict[str, Set[str]] = {}
    for s in load_fabric_sources()["sources"]:
        fam = s["source_family"]
        out.setdefault(fam, set()).update(
            u.replace("doi_registrant_", "").replace(
                "repository_aggregator_", "")
            for u in s.get("derives_from", []))
    _fams_cache = {k: frozenset(v) for k, v in out.items()}
    return out


def source_independence_score(
    source_ids: List[str],
    record_sources_by_canonical: Dict[str, List[str]],
) -> Dict[str, Any]:
    """The run-level independence metrics (directive sections 3 + 7).

    Returns a dict with:
      unique_sources, unique_source_families,
      independent_source_families (cluster count),
      source_independence_score = independent/unique families in (0, 1],
      overlap_ratio = canonical records found by >=2 sources / total,
      source_concentration = max family share of canonical records,
      correlation_evidence (families merged + the records that proved it).
    """
    fam_of = {s: source_family(s) for s in source_ids}
    fams = sorted({fam_of[s] for s in source_ids})
    clusters, correlation = independence_clusters(source_ids,
                                                  record_sources_by_canonical)
    total_records = len(record_sources_by_canonical)
    multi = sum(1 for srcs in record_sources_by_canonical.values()
                if len({source_family(s) for s in srcs}) >= 2)
    fam_record_counts: Dict[str, int] = {}
    for srcs in record_sources_by_canonical.values():
        for f in {source_family(s) for s in srcs}:
            fam_record_counts[f] = fam_record_counts.get(f, 0) + 1
    concentration = (max(fam_record_counts.values()) / total_records
                     if total_records and fam_record_counts else 0.0)
    score = (len(clusters) / len(fams)) if fams else 0.0
    return {
        "unique_sources": sorted(source_ids),
        "unique_source_families": fams,
        "independent_source_families": len(clusters),
        "source_independence_score": round(score, 4),
        "overlap_ratio": round(multi / total_records, 4) if total_records else 0.0,
        "source_concentration": round(concentration, 4),
        "family_record_counts": dict(sorted(fam_record_counts.items())),
        "independence_clusters": clusters,
        "correlation_evidence": {
            k: len(v) for k, v in correlation.items()},
        "independence_rule": ("families merged when a shared derives_from "
                              "upstream is DECLARED and record overlap was "
                              "MEASURED in this run (Art. XXI.7: measured, "
                              "never assumed)"),
    }

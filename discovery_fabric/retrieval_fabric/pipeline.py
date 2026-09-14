"""RETRIEVAL_FABRIC_V2 pipeline — the multi-channel discovery retrieval.

Replaces nothing: RETRIEVAL_FABRIC_V1 (discovery_fabric/a2/retrieve.py,
Europe PMC + OpenAlex) stays byte-unchanged and its historical corpus
immutable (directive section 13). V2 is the fabric: Europe PMC and
OpenAlex become two nodes among materially different open source
families, queried through the registry's 7-step connector chain with
per-run health, canonical dedup with preserved provenance, lineage
attribution, evidence lanes, publication-status labeling, reciprocal
expansion and diversity measurement.

Output contract (engine-compatible, ADDITIVE fields only):
  items: evidence dicts with the a2/retrieve.py schema
    (id, source_type, source, source_id, source_uri, title, abstract,
     doi, publication_date, retrieval_timestamp, retrieval_method,
     content_hash, provenance, epistemic_state)
  PLUS fabric fields:
    publication_status, document_type, evidence_lane, source_family,
    canonical_id, retrieval_status, query_variant, derivation_class,
    source_rank, fulltext_url, authors, raw_record_hash, limitations,
    lane_relevance.
  fabric_report: the full machine-readable provenance record (an
    independent auditor can reconstruct the discovery event from it).
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from discovery_fabric.retrieval_fabric.adapters import (
    LaneRunState, _connector_for, fabric_health_of, fetch_patent_claims_custoied,
    patent_record_from_hit, run_stats,
)
from discovery_fabric.retrieval_fabric.canonical import (
    Canonicalizer, CanonicalRecord,
)
from discovery_fabric.retrieval_fabric.diversity import (
    blind_spot_analysis, retrieval_diversity,
)
from discovery_fabric.retrieval_fabric.fabric_registry import (
    FABRIC_VERSION, fabric_sources_for_version, get_fabric_source,
    source_family,
)
from discovery_fabric.retrieval_fabric.publication_status import (
    label_publication_status, lane_for_publication_status,
)
from discovery_fabric.retrieval_fabric.query_expansion import (
    expand_query, mechanism_query,
)
from discovery_fabric.source_registry.base import SourceQueryResult
from discovery_fabric.source_registry.query_relevance import (
    adjudicate_record, keyword_form, record_text, terms,
)

FABRIC_VERSION_STRING = f"V{FABRIC_VERSION}"

#: per-lane item caps for the engine evidence pool (bounded context for
#: SYNTHESIZE; the FULL pool + provenance lives in the fabric report —
#: nothing is silently dropped, everything is attributed)
DEFAULT_LANE_CAPS = {
    "SCHOLARLY": 6, "PREPRINT": 3, "THESIS": 3, "PATENT": 5,
    "TECHNICAL_REPORT": 2, "DATASET": 2, "REPOSITORY": 4,
    "OA_LOCATION": 0,   # resolution lane: enriches, does not emit items
}

#: lanes and the sources that serve them (fabric registry authority)
LANE_SOURCE_MAP = {
    "SCHOLARLY": ["europepmc", "openalex", "semantic_scholar", "crossref",
                  "doaj"],
    "PREPRINT": ["arxiv"],
    "THESIS": ["crossref", "datacite", "openaire", "core"],
    "PATENT": ["google_patents"],
    "REPOSITORY": ["openaire", "core", "datacite"],
    "TECHNICAL_REPORT": ["datacite", "core"],
    "DATASET": ["datacite"],
}

#: which query variant class each source receives (grammar discipline):
#: weak-ranking repository sources get DOMAIN_NARROW; keyword sources
#: get PRIMARY/keyword-form; thesis lane gets alternative terminology.
SOURCE_VARIANT_POLICY = {
    # R417 (Art. LI adoption of the R412-V3 query-form learning): the
    # two sources the V3 decomposition measured for the numeric-
    # bearing reference gap (europepmc 9 / core 3 of the 12 unmatched
    # records) additionally receive the COMPARISON_TARGETED variant —
    # ADDITIVE to their existing selection, never replacing it.
    "europepmc": "PRIMARY_AND_COMPARISON",
    "openalex": "KEYWORD_FORM",
    "semantic_scholar": "PRIMARY",
    "crossref": "PRIMARY",
    "doaj": "PRIMARY",
    "arxiv": "PRIMARY",
    "datacite": "NARROW_OR_PRIMARY",
    "openaire": "PRIMARY",
    "core": "NARROW_AND_COMPARISON",
    "google_patents": "PRIMARY_AND_CROSS_DOMAIN",
}

UNPAYWALL_TOP_K = 5
PATENT_CLAIM_FETCH_TOP_K = 2


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _content_hash(item_core: Dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(item_core, sort_keys=True, ensure_ascii=False,
                   default=str).encode("utf-8")).hexdigest()


def _select_variants(variants: List[Dict[str, Any]],
                     policy: str) -> List[Dict[str, Any]]:
    """Choose which query variants a source receives (deterministic)."""
    by_class: Dict[str, Dict[str, Any]] = {}
    for v in variants:
        by_class.setdefault(v["derivation_class"], v)
    primary = by_class.get("PRIMARY")
    kw = {"query": keyword_form(primary["query"]),
          "derivation_class": "PRIMARY",
          "derivation_basis": "keyword-form of the primary query"}
    if policy == "PRIMARY":
        return [primary] if primary else []
    if policy == "KEYWORD_FORM":
        return [kw] if primary else []
    if policy == "DOMAIN_NARROW":
        v = by_class.get("DOMAIN_NARROW") or kw
        return [v]
    if policy == "NARROW_OR_PRIMARY":
        v = by_class.get("DOMAIN_NARROW")
        return [v, primary] if (v and primary) else ([primary] if primary else [])
    if policy == "PRIMARY_AND_CROSS_DOMAIN":
        out = [primary] if primary else []
        cd = by_class.get("CROSS_DOMAIN_TERM")
        if cd:
            out.append(cd)
        return out
    # R417: additive comparison-targeted routing for the sources the
    # V3 measurement named (the numeric-bearing reference records were
    # europepmc/core-indexed; the comparison form retrieved them)
    if policy == "PRIMARY_AND_COMPARISON":
        out = [primary] if primary else []
        comp = by_class.get("COMPARISON_TARGETED")
        if comp:
            out.append(comp)
        return out
    if policy == "NARROW_AND_COMPARISON":
        v = by_class.get("DOMAIN_NARROW") or kw
        out = [v]
        comp = by_class.get("COMPARISON_TARGETED")
        if comp:
            out.append(comp)
        return out
    return [primary] if primary else []


def _ingest_s2_record(rec: Dict[str, Any], canonicalizer: Canonicalizer,
                      lane_states: List[LaneRunState]) -> None:
    """Ingest a reciprocal-expansion record (S2 adapter output) into the
    canonical pool with proper labeling + attribution."""
    status_label = label_publication_status("semantic_scholar", rec)
    lane = lane_for_publication_status(status_label["publication_status"],
                                       "semantic_scholar")
    canonicalizer.add(
        "semantic_scholar", rec, rec.get("query", ""),
        status_label["publication_status"], lane,
        "" if lane != "PATENT" else "PATENT",
        status_label["source_type_evidence"],
        fulltext_url=None, limitations=[
            "Reciprocal-expansion record (citation/reference/recommendation "
            "expansion): entered the pool through a REAL provider endpoint "
            f"with derivation {rec.get('expansion_derivation')}",
        ])
    lane_states.append(LaneRunState(
        lane="SCHOLARLY_RECIPROCAL", source_id="semantic_scholar",
        queries=[rec.get("query", "")], status="OK",
        fabric_health="AVAILABLE", record_count=1))


def retrieve_fabric(problem: Dict[str, Any],
                    lane_caps: Optional[Dict[str, int]] = None,
                    llm_generate: Optional[Callable[[str], str]] = None,
                    enable_reciprocal: bool = True,
                    enable_unpaywall: bool = True,
                    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Run the V2 fabric retrieval for one problem.

    Returns (evidence_items, fabric_report). Never raises on provider
    failures — every failure is a recorded lane state (Art. XXI.3);
    a total failure of ALL lanes still returns ([], report) with every
    failure explicit.
    """
    started_at = utc_now()
    lane_caps = {**DEFAULT_LANE_CAPS, **(lane_caps or {})}
    lane_states: List[LaneRunState] = []
    canonicalizer = Canonicalizer()

    # ---- 1-2. query derivation + expansion (Art. XLIII) -------------
    primary = mechanism_query(problem)
    variants = expand_query(primary, problem)
    from discovery_fabric.retrieval_fabric.query_expansion import llm_expand
    llm_variants = llm_expand(primary, llm_generate)
    all_variants = variants + llm_variants

    # ---- 3. lane fan-out (each source through the 7-step chain) -----
    for lane, source_ids in LANE_SOURCE_MAP.items():
        for source_id in source_ids:
            fabric_src = get_fabric_source(source_id)
            if fabric_src is None:
                continue  # not in this fabric version
            policy = SOURCE_VARIANT_POLICY.get(source_id, "PRIMARY")
            scoped = "THESIS" if (lane == "THESIS" and
                                  source_id in ("crossref", "datacite")) else None
            chosen = _select_variants(all_variants, policy)
            if lane == "THESIS" and source_id in ("openaire", "core"):
                # thesis lane on post-hoc sources: use a CROSS_DOMAIN
                # variant if present (alternative terminology is the
                # measured discovery path for theses)
                chosen = ([v for v in all_variants
                           if v["derivation_class"] == "CROSS_DOMAIN_TERM"][:1]
                          or chosen)
            if not chosen:
                continue
            conn = _connector_for(source_id, scoped)
            if conn is None:
                lane_states.append(LaneRunState(
                    lane=lane, source_id=source_id,
                    queries=[v["query"] for v in chosen],
                    status="NOT_IMPLEMENTED", fabric_health="DEGRADED",
                    error="connector unavailable in registry wiring"))
                continue
            state = LaneRunState(lane=lane, source_id=source_id,
                                 queries=[v["query"] for v in chosen])
            total_records = 0
            variant_statuses: List[str] = []
            errors: List[str] = []
            for v in chosen:
                q = v["query"]
                try:
                    result: SourceQueryResult = conn.search(
                        q, retrieval_role="DISCOVERY")
                except TypeError:
                    # some registry connectors (prior_art_v2 wrappers) do
                    # not accept the retrieval_role kwarg — call without
                    # it (the custody log entry is still written by the
                    # wrapper's own _finish path)
                    result = conn.search(q)
                variant_statuses.append(result.status)
                total_records += len(result.records)
                if result.error:
                    errors.append(f"[{result.status}] {str(result.error)[:120]}")
                for rec in result.records:
                    _ingest_record(canonicalizer, source_id, rec, q,
                                   v["derivation_class"], lane_states, lane,
                                   scoped)
            # multi-variant honesty: the source is AVAILABLE when ANY
            # variant was answered (OK/EMPTY); a variant-level failure is
            # recorded in the error string, never masked as total failure
            any_answered = any(s in ("OK", "EMPTY") for s in variant_statuses)
            if any_answered:
                state.status = "OK" if total_records else "EMPTY"
            else:
                state.status = variant_statuses[-1] if variant_statuses else "SEARCH_FAILED"
            state.record_count = total_records
            state.error = "; ".join(errors)[:300] or None
            state.fabric_health = fabric_health_of(state.status)
            lane_states.append(state)

    # ---- PATENT lane: claim-level fetch for top hits ------------------
    patent_records = [r for r in canonicalizer.canonical_records()
                      if r.document_type == "PATENT"]
    claim_fetches: List[Dict[str, Any]] = []
    for rec in patent_records[:PATENT_CLAIM_FETCH_TOP_K]:
        pid = rec.patent_number
        if not pid:
            continue
        cf = fetch_patent_claims_custoied(pid)
        if cf.ok:
            rec.best_record["claims_excerpt"] = cf.claims_excerpt
            rec.best_record["claim_count"] = cf.claim_count
        rec.best_record["claim_text_available"] = cf.ok
        claim_fetches.append({
            "patent_id": pid, "ok": cf.ok,
            "claim_count": cf.claim_count,
            "raw_payload_sha256": cf.raw_payload_sha256,
            "error": cf.error,
        })

    # ---- 4. reciprocal expansion (bounded, S2) -------------------------
    reciprocal_report: Dict[str, Any] = {"enabled": enable_reciprocal,
                                         "calls": [], "records_added": 0}
    if enable_reciprocal:
        from discovery_fabric.retrieval_fabric.reciprocal import (
            ReciprocalBudget, reciprocal_expansion,
        )
        seeds = [r for r in canonicalizer.canonical_records()
                 if r.evidence_lane == "SCHOLARLY" and r.doi]
        seeds.sort(key=lambda r: -(r.best_record.get("citation_count") or
                                   r.best_record.get("cited_by_count") or 0))
        seed = seeds[0] if seeds else None
        if seed is not None:
            seed_id = (f"DOI:{seed.doi}"
                       if seed.doi else
                       (seed.best_record.get("paper_id") or ""))
            if seed_id:
                author_names = seed.best_record.get("authors") or \
                    ([seed.best_record.get("author_string")]
                     if seed.best_record.get("author_string") else [])
                rr = reciprocal_expansion(
                    seed_id, [a for a in author_names if a][:1],
                    budget=ReciprocalBudget())
                for rec in rr["records"]:
                    _ingest_s2_record(rec, canonicalizer, lane_states)
                reciprocal_report = {
                    "enabled": True,
                    "seed": {"canonical_id": seed.canonical_id,
                             "seed_id": seed_id,
                             "title": seed.title[:120]},
                    "calls": rr["calls"],
                    "budget": rr["budget"],
                    "records_added": len(rr["records"]),
                    "retrieved_at": rr["retrieved_at"],
                }

    # ---- 5. Unpaywall full-text resolution (resolution, not discovery) -
    unpaywall_report: Dict[str, Any] = {"enabled": enable_unpaywall,
                                        "resolved": 0, "oa_found": 0,
                                        "lookups": []}
    if enable_unpaywall:
        conn = _connector_for("unpaywall")
        if conn is not None:
            doi_records = [r for r in canonicalizer.canonical_records()
                           if r.doi]
            doi_records.sort(key=lambda r: -len(
                (r.best_record.get("abstract") or "")))
            for rec in doi_records[:UNPAYWALL_TOP_K]:
                result = conn.search(rec.doi,
                                     retrieval_role="FULLTEXT_RESOLUTION")
                st = LaneRunState(lane="OA_LOCATION", source_id="unpaywall",
                                  queries=[rec.doi],
                                  status=result.status,
                                  fabric_health=fabric_health_of(result.status),
                                  latency_ms=result.latency_ms)
                lane_states.append(st)
                entry: Dict[str, Any] = {"doi": rec.doi,
                                         "status": result.status}
                if result.status in ("OK", "EMPTY") and result.records:
                    n = result.records[0].normalized
                    entry.update({
                        "is_oa": n.get("is_oa"),
                        "oa_status": n.get("oa_status"),
                        "fulltext_url": n.get("fulltext_url"),
                        "host_type": n.get("host_type"),
                    })
                    if n.get("fulltext_url"):
                        rec.fulltext_url = str(n.get("fulltext_url"))
                        unpaywall_report["oa_found"] += 1
                    # lineage attribution: Unpaywall as fulltext source
                    rec.best_record.setdefault("oa_resolution", {
                        "provider": "unpaywall",
                        "resolved_at": result.retrieved_at,
                        "is_oa": n.get("is_oa"),
                        "oa_status": n.get("oa_status"),
                        "host_type": n.get("host_type"),
                        "repository_institution": n.get("repository_institution"),
                    })
                unpaywall_report["lookups"].append(entry)
                if result.status in ("OK", "EMPTY"):
                    unpaywall_report["resolved"] += 1

    # ---- 6-8. canonicalization done; compute diversity + stats --------
    canonical_records = canonicalizer.canonical_records()
    record_sources: Dict[str, List[str]] = {
        r.canonical_id: r.indexing_sources for r in canonical_records}
    diversity = retrieval_diversity(
        [r.to_dict() for r in canonical_records], record_sources)
    stats = run_stats(lane_states)
    blind_spots = blind_spot_analysis(diversity)

    # ---- per-lane relevance ranking (deterministic, same instrument
    # the discovery pipeline uses; lanes ranked SEPARATELY so a highly
    # cited review cannot bury a relevant patent claim or dissertation)
    lane_pools: Dict[str, List[CanonicalRecord]] = {}
    for rec in canonical_records:
        # blank-title records cannot serve synthesis or downstream
        # relevance — kept in the canonical pool (provenance preserved)
        # but never emitted as engine evidence items
        if not (rec.title or "").strip():
            continue
        lane_pools.setdefault(rec.evidence_lane, []).append(rec)
    primary_terms = set(terms(primary))
    # R456: the Phase-P1 semantic rerank of the lane pools — when the
    # zero-paid embedding engine is configured+reachable, records sort
    # by semantic proximity to the problem FIRST (the audited
    # lexical-only ordering let a highly-cited off-domain review bury a
    # relevant patent claim or dissertation); the lexical keys remain
    # the tie-breakers and the WHOLE layer is skipped (byte-identical
    # ordering) when the engine is off/unreachable — typed, never
    # silent (Art. IV).
    sem_scores: Dict[str, float] = {}
    sem_note = "off (LOCAL_EMBED_URL unset — lexical ordering, unchanged)"
    try:
        from discovery_fabric.source_registry import semantic_relevance
        if semantic_relevance.endpoint_url() is not None:
            lane_recs = [rec for pool in lane_pools.values()
                         for rec in pool]
            texts = [
                f"{rec.title}. "
                f"{rec.best_record.get('abstract') or ''}".strip()
                for rec in lane_recs]
            problem_text = " ".join(
                [str(problem.get(k) or "") for k in
                 ("device", "failure", "failure_mode", "constraint",
                  "problem")] + [str(primary)]).strip()
            sems = semantic_relevance.semantic_adjudicate(
                problem_text, texts)
            if sems and sems[0]["semantic_state"] != "SEMANTIC_UNAVAILABLE":
                sem_scores = {
                    rec.canonical_id: (sems[i]["semantic_cosine"] or 0.0)
                    for i, rec in enumerate(lane_recs)}
                sem_note = (
                    f"on ({semantic_relevance.SEMANTIC_RELEVANCE_VERSION}, "
                    f"{len(lane_recs)} records ranked semantically)")
            elif sems:
                sem_note = ("typed SEMANTIC_UNAVAILABLE — lexical "
                            "ordering, unchanged (the engine's typed "
                            "reason rides the fabric report)")
    except Exception:  # noqa: BLE001 — ranking aid only, never a break
        sem_note = "error-contained (lexical ordering, unchanged)"

    def _sem_key(rec: CanonicalRecord) -> float:
        return sem_scores.get(rec.canonical_id, 0.0)

    for lane, pool in lane_pools.items():
        def _score(rec: CanonicalRecord) -> Tuple[int, int, int]:
            adj = adjudicate_record(
                {"title": rec.title,
                 "normalized": rec.best_record,
                 "query": rec.queries_by_source.get(rec.origin_source, "")},
                primary)
            overlap = len(primary_terms & set(terms(record_text(
                {"title": rec.title, "normalized": rec.best_record}))))
            # synthesis-compatibility ordering (disclosed): records with
            # an abstract (mechanism-bearing text) rank above metadata-only
            # records within the same relevance tier — SYNTHESIZE consumes
            # evidence[0].abstract, which a title-only record cannot supply
            abstract_len = len((rec.best_record.get("abstract") or ""))
            has_text = 1 if abstract_len >= 50 or \
                rec.best_record.get("claim_text_available") else 0
            return (1 if adj.get("relevant") else 0, overlap, has_text)
        pool.sort(key=lambda rec: (
                      # R456: semantic proximity is the PRIMARY key when
                      # the engine is on (sem_scores empty -> 0.0 for
                      # every record -> this key is a no-op and the
                      # lexical ordering below is byte-identical)
                      round(_sem_key(rec), 3),
                      _score(rec)[0], _score(rec)[1],
                      _score(rec)[2],
                      -len((rec.best_record.get("abstract") or ""))),
                  reverse=True)

    # ---- 9. engine evidence items (a2-compatible + fabric fields) ----
    items: List[Dict[str, Any]] = []
    lane_item_counts: Dict[str, int] = {}
    for lane in ("SCHOLARLY", "PATENT", "THESIS", "PREPRINT",
                 "TECHNICAL_REPORT", "REPOSITORY", "DATASET"):
        pool = lane_pools.get(lane, [])
        cap = lane_caps.get(lane, 3)
        for rank, rec in enumerate(pool[:cap]):
            items.append(_to_engine_item(rec, rank, lane))
            lane_item_counts[lane] = lane_item_counts.get(lane, 0) + 1

    fabric_report = {
        "fabric_version": FABRIC_VERSION_STRING,
        "fabric_name": "RETRIEVAL_FABRIC_V2",
        "retrieved_at": started_at,
        "completed_at": utc_now(),
        "problem": {"device": problem.get("device", ""),
                    "failure_mode": problem.get("failure_mode", "")},
        "primary_query": primary,
        "query_variants": all_variants,
        "llm_expansion_used": bool(llm_variants),
        "no_fabrication_rule": ("LLM proposed query variants ONLY; every "
                                "record originated from a source adapter "
                                "result (test-enforced)"),
        "retrieval_stats": stats,
        "retrieval_diversity": diversity,
        "retrieval_blind_spots": blind_spots,
        "semantic_lane_rerank": {
            "note": sem_note,
            "version": "retrieval_fabric+semantic_relevance/1.0.0 (R456)",
            "disclosure": ("semantic proximity is the primary lane-order "
                           "key ONLY when the zero-paid embedding engine "
                           "is configured and reachable; otherwise the "
                           "ordering is byte-identical to the lexical "
                           "instrument (typed in this note, never silent)"),
        },
        "canonical_record_count": len(canonical_records),
        "dedup_merge_events": canonicalizer.merge_events,
        "patent_claim_fetches": claim_fetches,
        "reciprocal_expansion": reciprocal_report,
        "unpaywall_resolution": unpaywall_report,
        "evidence_pool": {"items_by_lane": lane_item_counts,
                          "total_items": len(items),
                          "lane_caps": lane_caps,
                          "note": ("the engine evidence pool is capped per "
                                   "lane for synthesis context; the FULL "
                                   "canonical pool + per-record provenance "
                                   "is preserved in canonical_records")},
        "canonical_records": [r.to_dict() for r in canonical_records],
        "constitution_compliance": {
            "art_xxi_3": ("every provider failure recorded as an explicit "
                          "lane state — never absence"),
            "art_xxi_7": ("independence measured by declared lineage + "
                          "measured record overlap, never API count"),
            "art_xliii": ("primary query derived from problem facts only; "
                          "every variant carries its derivation class"),
            "art_lxii": ("machine-readable provenance sufficient to "
                         "reconstruct the discovery event: query, variant, "
                         "source, record id, raw payload hash, lane, "
                         "labeling evidence, timing"),
        },
    }
    FABRIC_REPORT.clear()
    FABRIC_REPORT.update(fabric_report)
    return items, fabric_report


def _ingest_record(canonicalizer: Canonicalizer, source_id: str,
                   rec: Any, query: str, derivation_class: str,
                   lane_states: List[LaneRunState], lane_hint: str,
                   scoped: Optional[str] = None) -> None:
    """Ingest one SourceRecord into the canonical pool with labeling."""
    normalized = dict(rec.normalized or {})
    normalized.setdefault("record_id", rec.record_id)
    if source_id in ("crossref", "datacite") and scoped == "THESIS":
        normalized["fabric_scoped_query"] = "THESIS_LANE_TYPE_FILTER"
    status_label = label_publication_status(source_id, normalized)
    if source_id in ("crossref", "datacite") and scoped == "THESIS":
        # type-scoped thesis-lane query: the server-side filter guarantees
        # the document class (recorded in the query URL, custody-logged)
        status_label = {"publication_status": "THESIS",
                        "source_type_evidence":
                            status_label["source_type_evidence"] or
                            "server-side type filter (type:dissertation / "
                            "resourceTypeGeneral=Dissertation)"}
    is_patent = (source_id in ("google_patents", "epo_ops", "lens_patent",
                               "patentbear", "patsnap_eureka"))
    if is_patent:
        # patent records: use the directive's patent schema
        hit = {"patent_id": (normalized.get("patent_id")
                             or rec.record_id.split("patent:")[-1]),
               "title": rec.title, "snippet": normalized.get("snippet"),
               "assignee_or_authors": normalized.get("assignee_or_authors"),
               "publication_date": normalized.get("publication_date"),
               "source_url": rec.uri,
               "raw_payload_sha256": rec.raw_payload_sha256,
               "raw_metadata": (normalized.get("raw_metadata") or {}),
               "query": query}
        patent_rec = patent_record_from_hit(hit, query)
        normalized.update(patent_rec)
        status_label = {"publication_status": "UNKNOWN",
                        "source_type_evidence": "document_type=PATENT"}
    lane = lane_for_publication_status(
        status_label["publication_status"], source_id, is_patent)
    fulltext = normalized.get("fulltext_url") or (
        rec.uri if source_id in ("doaj", "arxiv") else None)
    canonicalizer.add(
        source_id, normalized, query,
        status_label["publication_status"], lane,
        "PATENT" if is_patent else "",
        status_label["source_type_evidence"],
        fulltext_url=fulltext,
        limitations=list(rec.limitations or []),
    )
    # query-variant attribution for provenance
    rec_queried = canonicalizer._by_key.get(
        _canonical_key_of(normalized, is_patent))
    if rec_queried is not None:
        rec_queried.best_record.setdefault(
            "query_variant_derivation", derivation_class)


def _canonical_key_of(normalized: Dict[str, Any], is_patent: bool) -> str:
    from discovery_fabric.retrieval_fabric.canonical import (
        normalize_doi, normalize_patent_number, title_fingerprint,
    )
    doi = normalize_doi(normalized.get("doi"))
    patent = normalize_patent_number(normalized.get("patent_number"))
    if is_patent and patent:
        return f"patent:{patent}"
    if doi:
        return f"doi:{doi}"
    arxiv = normalized.get("arxiv_id")
    if arxiv:
        return f"arxiv:{arxiv}"
    fp = title_fingerprint(normalized.get("title"),
                           normalized.get("publication_year")
                           or normalized.get("year"))
    return f"title:{fp}"


def _to_engine_item(rec: CanonicalRecord, rank: int,
                    lane: str) -> Dict[str, Any]:
    """CanonicalRecord -> engine evidence item (a2 schema + fabric fields)."""
    best = rec.best_record
    abstract = (best.get("abstract") or best.get("claims_excerpt")
                or best.get("summary") or best.get("snippet") or "")
    core = {
        "canonical_id": rec.canonical_id,
        "title": rec.title,
        "doi": rec.doi,
        "patent_number": rec.patent_number,
        "publication_year": rec.publication_year,
        "publication_status": rec.publication_status,
        "evidence_lane": lane,
    }
    return {
        # a2-compatible schema (downstream stages keep working):
        "id": rec.canonical_id,
        "source_type": ("patent" if rec.document_type == "PATENT"
                        else "scientific_paper"),
        "source": rec.origin_source,
        "source_id": f"{rec.origin_source}:{rec.record_ids_by_source.get(rec.origin_source, '')}",
        "source_uri": best.get("url") or best.get("source_url") or
        (f"https://doi.org/{rec.doi}" if rec.doi else ""),
        "title": rec.title or "",
        "abstract": str(abstract)[:2400],
        "doi": rec.doi or None,
        "patent_number": rec.patent_number or None,
        "publication_number": rec.patent_number or None,
        "publication_date": (str(rec.publication_year)
                             if rec.publication_year else None),
        "retrieval_timestamp": utc_now(),
        "retrieval_method": f"retrieval_fabric_v{FABRIC_VERSION}",
        "content_hash": _content_hash(core),
        "provenance": {
            "fabric_version": FABRIC_VERSION_STRING,
            "origin_source": rec.origin_source,
            "indexing_sources": sorted(set(rec.indexing_sources)),
            "record_ids_by_source": rec.record_ids_by_source,
            "queries_by_source": rec.queries_by_source,
            "query_variant_derivation": best.get("query_variant_derivation"),
            "source_family": source_family(rec.origin_source),
            "identity_basis": rec.identity_basis,
            "raw_payload_sha256": (rec.best_record.get("raw_payload_sha256")
                                   or rec.best_record.get("raw_record_sha256")
                                   or ""),
            "publication_status_evidence": rec.source_type_evidence,
            "oa_resolution": best.get("oa_resolution"),
        },
        "epistemic_state": "OBSERVED",
        # fabric fields (additive):
        "publication_status": rec.publication_status,
        "document_type": rec.document_type or "",
        "evidence_lane": lane,
        "source_family": source_family(rec.origin_source),
        "canonical_id": rec.canonical_id,
        "retrieval_status": "SUCCESS",
        "query_variant": rec.queries_by_source.get(rec.origin_source, ""),
        "source_rank": rank,
        "fulltext_url": rec.fulltext_url,
        "authors": best.get("authors") or [],
        "raw_record_hash": (best.get("raw_payload_sha256")
                            or best.get("raw_record_sha256") or ""),
        "limitations": rec.limitations,
    }


#: module-level access to the last fabric report (mirrors a2/retrieve's
#: RETRIEVAL_LANES pattern for machine-visible lane honesty)
FABRIC_REPORT: Dict[str, Any] = {}

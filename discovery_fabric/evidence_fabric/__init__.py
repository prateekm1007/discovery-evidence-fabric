"""EVIDENCE_FABRIC — the federated evidence layer that connects
HuggingFace-hosted datasets to the invention engine (R449).

Design contract (the operator's R449 constraints, enforced here):
  - FEDERATED: every query goes to the REMOTE datasets-server; nothing
    is bulk-downloaded; there is NO local vector store, NO second
    knowledge graph, NO warehouse. The existing retrieval_fabric V2
    (EuropePMC/OpenAlex/...) is NOT replaced — this layer is an
    ADDITIVE evidence channel beside it.
  - ONE canonical representation: every source normalizes into
    EvidenceRecord (Phase 3). There are no per-source truth systems.
  - EXACT-SPAN CUSTODY (Phase 4): source + document + version +
    location + verbatim text + content hash. The LLM interprets the
    span (proposition/entities/mechanisms); it can never redefine it.
  - SOURCE SUBSTITUTION (Phase 5): an unavailable source degrades to a
    declared alternate with the SAME proposition search, provenance
    preserved, and the COVERAGE LIMITATION recorded — an LLM's internal
    knowledge is NEVER a substitute for a source (the forbidden ladder:
    "OpenAlex unavailable -> LLM knows the literature -> evidence").
  - FAIL-CLOSED: records from unverified-license sources are
    BLOCKED_LICENSE_UNVERIFIED and never reach the evidence pool.

Public API:
    retrieve_evidence(problem) -> (engine_items, fabric_report)

    engine_items carry the a2 evidence schema + additive
    `evidence_fabric` fields (the V1->V2 additive discipline), so the
    engine's downstream stages (FREEZE -> SYNTHESIZE -> ...) consume
    them unchanged. The fabric_report carries the full custody
    records, per-source connector states, substitution decisions, and
    the relevance adjudications — an independent auditor can
    reconstruct the retrieval event from it.
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from discovery_fabric.evidence_fabric import connectors as hc
from discovery_fabric.evidence_fabric.evidence_record import (
    ADMISSIBILITY_STATES, EVIDENCE_FABRIC_VERSION, EvidenceRecord,
    build_evidence_record, make_evidence_id, sha256_text, utc_now,
    validate_record,
)
from discovery_fabric.evidence_fabric.registry import (
    license_ok, load_registry, production_sources,
)
from discovery_fabric.evidence_fabric.substitution import (
    substitution_ladder, substitute_source,
)

EVIDENCE_FABRIC_VERSION_STRING = EVIDENCE_FABRIC_VERSION

#: per-source retrieval caps (bounded evidence pull per problem; the
#: anti-warehouse discipline applies to RESULTS too, not just storage)
DEFAULT_PER_SOURCE_LIMIT = int(os.environ.get(
    "EVIDENCE_FABRIC_PER_SOURCE_LIMIT", "4"))

#: how many evidence-fabric items may enter the engine evidence pool
#: (additive to the V2 fabric's own lane caps)
DEFAULT_POOL_CAP = int(os.environ.get("EVIDENCE_FABRIC_POOL_CAP", "12"))

#: inter-channel pacing against datasets-server request quotas
#: (measured live this round: back-to-back channels burst RATE_LIMITED)
_CHANNEL_PACING_S = float(os.environ.get(
    "EVIDENCE_FABRIC_CHANNEL_PACING_S", "2.0"))

#: the relevance adjudicator's keyword-collision discipline (Art. XXI.4:
#: relevance must be independently established — a string match is
#: insufficient). Deterministic term-overlap adjudication + the problem's
#: domain terms; every decision recorded in the fabric report.
_STOP = set("""a an and are as at be by for from has have in into is it of
on or that the their there these they this to was were will with without
using used use can could design designs designed system systems method
methods new novel improve improved improvement reducing reduce reduces
high low more less than then when where which while
not problem state limited documented
invention relates discloses""".split())
# R456 (measured lexical-gate defect, frozen R449 arm_b evidence): the
# generic terms {problem, state, not, limited, documented} admitted four
# OpenFOAM prompt-template garbage records as RELEVANT via shared_terms
# ["problem", "state"] - pure filler collisions, zero domain content.
# The patent-structural trio {invention, relates, discloses} is the
# same class: every patent span carries them, so they carry no
# relevance information (the R449 records 0-3 all open with "The
# invention discloses/provides...").


def _terms(text: str) -> List[str]:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return [w for w in words if len(w) > 2 and w not in _STOP]


def problem_queries(problem: Dict[str, Any]) -> List[str]:
    """Deterministic evidence queries derived from the PROBLEM (never a
    solution class — Art. XLIII search-space neutrality: the query
    derives from problem facts, failure, and constraints only)."""
    device = str(problem.get("device") or "")
    failure = str(problem.get("failure") or problem.get("problem") or "")
    user_text = str(problem.get("user_text") or "")
    parts = [p for p in (device, failure) if p.strip()]
    queries: List[str] = []
    if device:
        queries.append(" ".join(_terms(device)[:6]))
    for p in parts:
        t = _terms(p)
        if len(t) >= 2:
            queries.append(" ".join(t[:8]))
    # the user_text's problem-fact core (first sentences carry the
    # failure statement; the objective sentence is EXCLUDED — the
    # "Design a ..." clause is the solution space, not the problem)
    if user_text:
        factual = user_text.split(".")[0]
        t = _terms(factual)
        if len(t) >= 4:
            queries.append(" ".join(t[:8]))
    # dedupe, drop empties, cap
    seen, out = set(), []
    for q in queries:
        q = q.strip()
        if q and q not in seen:
            seen.add(q)
            out.append(q)
    return out[:4]


def adjudicate_relevance(record: EvidenceRecord,
                         problem_terms: List[str],
                         problem_elems: List[str],
                         query: str) -> Dict[str, Any]:
    """Art. XXI.4 relevance adjudication — deterministic, recorded.

    TWO modes, both recorded with their basis:
    TEXT spans (patents/papers/cases): the span's terms must overlap the
    problem's DISTINCT domain terms (not just the query echo). Two or
    more shared terms, or one rare (>=7 char) shared term, adjudicates
    RELEVANT.
    STRUCTURED spans (formula/SMILES — materials/chemistry families):
    element-level overlap — the problem's elements (names expanded to
    symbols) vs the span's element tokens. At least one STRUCTURAL
    METAL shared (Cu/Ni/Ti/Zn/Fe/Al/...) adjudicates RELEVANT; only
    non-metal overlap (C/H/O in organics) is WEAK (every organic
    molecule shares them — not problem-specific); zero overlap is
    REJECTED (keyword/proximity collision).
    """
    span = record.exact_span
    structured = record.source_type in (
        "E4_materials_intelligence", "E5_chemical_intelligence") and \
        span.field in ("chemical_formula_reduced", "smiles",
                      "chemical_formula", "formula", "contents")
    if structured:
        span_elems = set(m if not m[-1].isdigit() else m.rstrip("0123456789")
                         for m in _FORMULA_TOKEN_RE.findall(span.text))
        shared = sorted(span_elems & set(problem_elems))
        structural_metals = {"Cu", "Ni", "Ti", "Zn", "Fe", "Al", "Mg",
                             "Cr", "Mo", "Ag", "Au", "Sn", "Pb", "Co",
                             "Mn", "V", "W", "Ta", "Zr", "Nb"}
        metal_shared = [e for e in shared if e in structural_metals]
        if metal_shared:
            verdict = "RELEVANT"
            basis = ("element-level overlap on structural metals: "
                     + ", ".join(metal_shared))
        elif shared:
            verdict = "WEAK_RELEVANCE"
            basis = ("only non-metal element overlap ("
                     + ", ".join(shared[:5]) + ") — not problem-specific")
        else:
            verdict = "REJECTED"
            basis = ("no element overlap with the problem's elements ("
                     + ", ".join(problem_elems) + ")")
        return {
            "verdict": verdict,
            "mode": "STRUCTURED_ELEMENT_OVERLAP",
            "shared_elements": shared,
            "structural_metals_shared": metal_shared,
            "problem_elements": problem_elems,
            "query": query,
            "method": basis + "; the decision is recorded per record "
                      "(Art. XXI.4)",
        }
    span_terms = set(_terms(span.text))
    prob_terms = set(problem_terms)
    shared_terms = sorted(span_terms & prob_terms)
    rare_shared = [t for t in shared_terms if len(t) >= 7]
    if len(shared_terms) >= 2 or rare_shared:
        verdict = "RELEVANT"
    elif len(shared_terms) == 1:
        verdict = "WEAK_RELEVANCE"
    else:
        verdict = "REJECTED"
    return {
        "verdict": verdict,
        "mode": "TEXT_TERM_OVERLAP",
        "shared_terms": shared_terms,
        "rare_shared_terms": rare_shared,
        "query": query,
        "method": "deterministic term-overlap (problem terms vs span "
                  "terms); the decision is recorded per record "
                  "(Art. XXI.4)",
    }


def _relevance_promote(record: EvidenceRecord,
                       decision: Dict[str, Any]) -> None:
    v = decision["verdict"]
    record.relevance = decision
    if v == "RELEVANT":
        record.admissibility.state = "PENDING_CORROBORATION"
        record.admissibility.reasons = [
            "relevance adjudicated RELEVANT ("
            + str(decision.get("authority") or
                  "deterministic term overlap")
            + "); corroboration across independent families pending"]
    elif v == "WEAK_RELEVANCE":
        record.admissibility.state = "PENDING_RELEVANCE"
        record.admissibility.reasons = [
            "insufficient for admission ("
            + str(decision.get("mode") or "single shared domain term")
            + ") — kept in custody, NOT admitted"]
    else:
        record.admissibility.state = "BLOCKED_RELEVANCE_REJECTED"
        record.admissibility.reasons = [
            "rejected by BOTH relevance authorities ("
            + str(decision.get("mode") or
                  "no shared domain terms")
            + "; Art. XXI.4); record kept in custody, never admitted"]


#: element names -> symbols (the deterministic problem-element
#: expansion for structured-record relevance: a Cu-bearing compound
#: IS relevant evidence to a copper-corrosion problem)
_ELEMENT_NAMES = {
    "copper": "Cu", "nickel": "Ni", "titanium": "Ti", "zinc": "Zn",
    "iron": "Fe", "aluminum": "Al", "aluminium": "Al",
    "magnesium": "Mg", "chromium": "Cr", "molybdenum": "Mo",
    "silver": "Ag", "gold": "Au", "tin": "Sn", "lead": "Pb",
    "cobalt": "Co", "manganese": "Mn", "vanadium": "V",
    "tungsten": "W", "tantalum": "Ta", "zirconium": "Zr",
    "niobium": "Nb", "silicon": "Si", "carbon": "C",
    "nitrogen": "N", "oxygen": "O", "sulfur": "S", "sulphur": "S",
    "phosphorus": "P", "hydrogen": "H", "lithium": "Li",
    "sodium": "Na", "potassium": "K", "calcium": "Ca",
    "chlorine": "Cl", "fluorine": "F", "bromine": "Br",
}

#: structural metals get relevance priority in the element expansion
#: (the corrosion/alloy filter terms)
_ELEMENT_RE = re.compile(
    r"\b(Cu|Ni|Ti|Zn|Fe|Al|Mg|Cr|Mo|Ag|Au|Sn|Pb|Co|"
    r"Mn|V|W|Ta|Zr|Nb|Si|C|N|O|S|P|H|Li|Na|K|Ca)\b")

#: formula/SMILES span tokenizer: element-segment symbols
_FORMULA_TOKEN_RE = re.compile(
    r"\b(Cu|Ni|Ti|Zn|Fe|Al|Mg|Cr|Mo|Ag|Au|Sn|Pb|Co|Mn|V|W|Ta|Zr|Nb|Si|"
    r"C|N|O|S|P|H|F|Cl|Br|Li|Na|K|Ca)\d*")


def problem_elements(problem: Dict[str, Any]) -> List[str]:
    """Element symbols present in the problem statement (both symbol
    occurrences and element NAMES expanded deterministically —
    copper->Cu). Structural metals first. The full user_text is
    included: the terse device/failure extractions can drop the
    material words ("copper-nickel tubing" -> device "Marine growth
    chloride corrosion" — measured on the fresh R449 problem)."""
    keys = ("device", "failure", "constraint", "problem", "user_text",
            "failure_mode")
    text = " ".join(str(problem.get(k) or "") for k in keys).lower()
    found: List[str] = []
    for name, sym in _ELEMENT_NAMES.items():
        if re.search(r"\b" + name + r"\b", text) and sym not in found:
            found.append(sym)
    for sym in _ELEMENT_RE.findall(text):
        if sym not in found:
            found.append(sym)
    return found[:4]


def _query_source(source: Dict[str, Any], query: str,
                  problem: Optional[Dict[str, Any]] = None,
                  limit: int = DEFAULT_PER_SOURCE_LIMIT
                  ) -> Tuple[Optional[List[EvidenceRecord]],
                             Dict[str, Any]]:
    """Query ONE production source federated; normalize rows to
    EvidenceRecords. Returns (records_or_None, channel_meta)."""
    ds = source["dataset_id"]
    config = source.get("config") or "default"
    split = source.get("split") or "train"
    mode = source.get("query_mode") or "search"
    text_field = source.get("text_field") or "text"
    fallback_field = source.get("fallback_text_field") or ""
    doc_field = source.get("document_field") or "id"
    lic_ok_ = license_ok(source)
    rows: Optional[List[Dict[str, Any]]] = None
    meta: Dict[str, Any] = {
        "source_id": source["source_id"], "dataset_id": ds,
        "family": source.get("family"), "query": query, "mode": mode,
        "license_verified": bool(source.get("license_verified")),
        "license_ok_for_production": lic_ok_,
    }
    if not lic_ok_:
        # fail-closed: the query is not even issued for a source whose
        # license state is not verified (no records from it can ever be
        # admissible)
        meta["state"] = "BLOCKED_LICENSE_UNVERIFIED"
        meta["reason"] = ("source license/access state not verified — "
                          "no retrieval issued (fail-closed)")
        return None, meta
    if mode == "filter":
        where = source.get("where_template", "")
        if not where:
            meta["state"] = "NOT_ATTEMPTED"
            meta["reason"] = "filter source without where_template"
            return None, meta
        # problem-derived element substitution: the template's
        # {element} placeholder is filled from the problem's OWN
        # element symbols (Art. XLIII — problem facts, never a solution
        # class). A template WITHOUT a placeholder is the source's
        # frozen declared screen (recorded verbatim).
        if "{element}" in where:
            elems = problem_elements(problem or {}) or [""]
            where = where.replace("{element}", elems[0] or "")
            meta["where_term_source"] = ("problem_elements:"
                                          + ",".join(elems))
        rows, rmeta = hc.filter_rows(ds, config, split, where, length=limit)
        meta["state"] = rmeta.get("state")
        meta["num_rows_total"] = rmeta.get("num_rows_total")
        meta["where"] = where
        endpoint = "filter"
    else:
        rows, rmeta = hc.search_rows(ds, config, split, query, length=limit)
        meta["state"] = rmeta.get("state")
        meta["reason"] = rmeta.get("reason")
        meta["num_rows_total"] = rmeta.get("num_rows_total")
        meta["attempts"] = rmeta.get("attempts")
        endpoint = "search"
    if rows is None:
        meta["state"] = "UNKNOWN"
        return None, meta
    records: List[EvidenceRecord] = []
    schema_invalid = 0
    fallback_used = 0
    measurement_fields = source.get("measurement_fields") or []
    for r in rows:
        row_idx = int(r.get("row_idx", -1))
        row = r.get("row") or {}
        use_field = text_field
        if row.get(text_field) is None or not str(
                row.get(text_field) or "").strip():
            if fallback_field and str(row.get(fallback_field) or "").strip():
                use_field = fallback_field
                fallback_used += 1
            else:
                schema_invalid += 1
                continue
        rec = build_evidence_record(
            source=source, row=row, row_idx=row_idx,
            text_field=use_field, document_field=doc_field,
            retrieval_endpoint=endpoint,
            connector_state=meta.get("state", "SUCCESS"),
            license_verified=bool(source.get("license_verified")),
            license_basis=str(source.get("license_basis") or "UNVERIFIED"),
            card_license=source.get("license"),
            origin_description=str(source.get("provenance_origin") or ""),
            measurement_fields=measurement_fields,
            retrieval_query=query)
        if rec is None:
            schema_invalid += 1
            continue
        records.append(rec)
    if schema_invalid:
        meta["schema_invalid_rows"] = schema_invalid
    if fallback_used:
        meta["fallback_field_rows"] = fallback_used
    meta["records"] = len(records)
    return records, meta


def retrieve_evidence(problem: Dict[str, Any],
                      extra_queries: Optional[List[str]] = None,
                      per_source_limit: int = DEFAULT_PER_SOURCE_LIMIT,
                      pool_cap: int = DEFAULT_POOL_CAP
                      ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """The evidence-fabric retrieval entry point.

    Returns (engine_items, fabric_report):
      engine_items  — a2-schema-compatible dicts (+ additive
                      evidence_fabric fields), ADMISSIBLE-side only
                      (PENDING_CORROBORATION or ADMITTED); blocked
                      records stay in the report, never the pool.
      fabric_report — full custody: per-query/per-source channel
                      states, substitution decisions, every record's
                      admissibility + relevance decision.
    """
    started = utc_now()
    queries = problem_queries(problem)
    for q in extra_queries or []:
        if q and q not in queries:
            queries.append(q)
    problem_terms = _terms(
        " ".join([str(problem.get(k) or "") for k in
                  ("device", "failure", "constraint", "problem")]))
    problem_elems = problem_elements(problem)
    report: Dict[str, Any] = {
        "fabric_version": EVIDENCE_FABRIC_VERSION_STRING,
        "retrieved_at": started,
        "federated": True,
        "bulk_download": False,
        "problem_queries": queries,
        "problem_elements": problem_elems,
        "channels": [],
        "substitutions": [],
        "records": [],
        "pool": {"requested_cap": pool_cap, "items": 0,
                 "by_state": {}},
        "coverage_limitations": [],
        "source_failures": [],
    }
    try:
        sources = production_sources()
    except FileNotFoundError:
        report["registry_state"] = "REGISTRY_MISSING"
        return [], report

    ladder = substitution_ladder()
    records_all: List[EvidenceRecord] = []
    _channel_count = 0

    def _run_source(src: Dict[str, Any], q: str,
                    why: str) -> None:
        nonlocal _channel_count
        _channel_count += 1
        if _channel_count > 1:
            # pacing: the datasets-server enforces request quotas
            # (measured live this round: RATE_LIMITED bursts when
            # channels fire back-to-back)
            time.sleep(_CHANNEL_PACING_S)
        recs, ch = _query_source(src, q, problem=problem,
                                 limit=per_source_limit)
        ch["attempted_as"] = why
        report["channels"].append(ch)
        if ch.get("state") == "UNKNOWN":
            entry = {"source_id": src["source_id"],
                     "query": q,
                     "state": "UNKNOWN",
                     "reason": ch.get("reason") or "provider failure"}
            report["source_failures"].append(entry)
        if recs:
            records_all.extend(recs)

    def _queries_for(src: Dict[str, Any]) -> List[str]:
        """Query-kind discipline (Art. XLIII): TEXT sources get the
        problem queries; ELEMENT sources (materials/chemistry formula
        indexes) get the problem's OWN element symbols — never a
        solution class."""
        kind = src.get("query_kind") or "text_problem"
        if kind == "element":
            return problem_elems[:2]
        return queries[:2]

    # ---- Phase A: ALL primaries first (every production source) -------
    for src in sources:
        for q in _queries_for(src):
            _run_source(src, q, "primary")

    # ---- Phase B: source substitution (Phase 5) — only for sources
    # whose EVERY primary channel failed (UNKNOWN class), only with an
    # alternate that was NOT already served as a primary, with the
    # coverage limitation recorded. Absence of a working source is
    # NEVER filled by the LLM (the forbidden ladder). --------------------
    for src in sources:
        sid = src["source_id"]
        chans = [c for c in report["channels"]
                 if c.get("source_id") == sid
                 and c.get("attempted_as") == "primary"]
        if not chans:
            continue
        failed = all(c.get("state") == "UNKNOWN" for c in chans)
        if not failed:
            continue
        sub = substitute_source(sid, ladder, sources)
        served_primary = {s["source_id"] for s in sources}
        if sub is not None and sub["source_id"] not in served_primary:
            alt_id = sub["source_id"]
            for q in _queries_for(sub):
                _run_source(sub, q, f"substitute_for:{sid}")
            report["substitutions"].append({
                "primary": sid,
                "alternate": alt_id,
                "queries": _queries_for(sub),
                "coverage_limitation": ladder.get(sid, {}).get(
                    "coverage_limitation", ""),
                "provenance": "the alternate source serves the records; "
                              "every record carries ITS source identity "
                              "(never the primary's)",
            })
        else:
            lim = ladder.get(sid, {}).get("coverage_limitation", "")
            if lim:
                report["coverage_limitations"].append(
                    {"source_id": sid, "limitation": lim})

    # ---- family-level coverage limitations (Phase 5 discipline):
    # families with NO production source this round are recorded — the
    # coverage gap is never silently filled by the LLM or by pretending
    # the existing fabric's channels are the evidence fabric's
    served_families = {s.get("family") for s in sources}
    for fam in ("E1_patent_intelligence", "E2_scientific_intelligence",
                "E3_engineering_intelligence",
                "E4_materials_intelligence", "E5_chemical_intelligence"):
        if fam not in served_families:
            report["coverage_limitations"].append({
                "family": fam,
                "limitation": (
                    "no PRODUCTION evidence-fabric source in this family "
                    "this round; the evidence fabric serves NOTHING for "
                    "this family (any paper/patent evidence in the engine "
                    "pool comes from the existing V2 fabric channels, "
                    "which are a different retrieval system — never "
                    "conflated with evidence-fabric provenance)"),
            })

    # ---- relevance adjudication (recorded per record) ----------------
    # R456: the Phase-P1 semantic layer composes with the lexical gate
    lexical_decisions = [
        adjudicate_relevance(rec, problem_terms, problem_elems, "")
        for rec in records_all]
    problem_text = " ".join(
        [str(problem.get(k) or "") for k in
         ("device", "failure", "constraint", "problem")]
        + [str(problem.get("user_text") or "")]).strip()
    record_texts = []
    for rec in records_all:
        title = str(_title_of(rec) or "")
        span = str((rec.exact_span.text or "")[:1000])
        record_texts.append(f"{title}. {span}".strip())
    try:
        from discovery_fabric.source_registry import semantic_relevance
        semantic_decisions = semantic_relevance.semantic_adjudicate(
            problem_text, record_texts)
    except Exception:  # noqa: BLE001 — the semantic layer can never
        # break the fabric channel (Art. LXI): typed unavailability
        semantic_decisions = None
    for i, rec in enumerate(records_all):
        decision = lexical_decisions[i]
        if semantic_decisions is not None:
            if decision.get("mode") == "TEXT_TERM_OVERLAP":
                # TEXT spans: the composed gate (OR for admission — the
                # Phase-P1 reranker restores the semantically-clear
                # records the lexical gate dark-rejects)
                decision = semantic_relevance.compose_verdict(
                    decision, semantic_decisions[i])
            else:
                # STRUCTURED spans (element overlap): the element rule
                # stays authoritative — a bare formula's dense embedding
                # carries no domain semantics; the semantic decision is
                # RECORDED (custody) but does not compose
                decision = dict(decision)
                decision["semantic"] = semantic_decisions[i]
                decision["semantic_composition"] = (
                    "STRUCTURED span: element authority retained; "
                    "semantic recorded for custody only")
        _relevance_promote(rec, decision)
        report["records"].append(rec.to_dict())
    if semantic_decisions is not None:
        report["semantic_relevance"] = {
            "version": semantic_relevance.SEMANTIC_RELEVANCE_VERSION,
            "model": semantic_relevance.model_name(),
            "engine_url_present": semantic_relevance.endpoint_url()
            is not None,
            "states": {
                s: sum(1 for d in semantic_decisions
                       if d["semantic_state"] == s)
                for s in semantic_relevance.SEMANTIC_STATES},
            "note": "OR-composition for admission; both authorities "
                    "recorded per record (the Phase-P1 reranker, R456)",
        }

    # ---- pool assembly: admissible-side only, family-balanced ---------
    admissible = [r for r in records_all if r.admissibility.state in
                  ("PENDING_CORROBORATION", "ADMITTED")]
    def _rel_strength(r: EvidenceRecord) -> int:
        rel = r.relevance or {}
        return (len(rel.get("structural_metals_shared") or []) * 10 +
                len(rel.get("shared_terms") or []))
    admissible.sort(key=lambda r: (
        0 if r.admissibility.state == "ADMITTED" else 1,
        -_rel_strength(r)))
    by_state: Dict[str, int] = {}
    for r in records_all:
        by_state[r.admissibility.state] = \
            by_state.get(r.admissibility.state, 0) + 1
    pool = admissible[:pool_cap]
    report["pool"]["items"] = len(pool)
    report["pool"]["by_state"] = by_state
    engine_items = [r.to_engine_item() for r in pool]
    report["pool"]["evidence_ids"] = [i["id"] for i in engine_items]
    report["completed_at"] = utc_now()
    return engine_items, report


def enabled() -> bool:
    """The channel is ON by default; ENGINE_EVIDENCE_FABRIC=0 disables
    (the comparison experiment's Arm A)."""
    return (os.environ.get("ENGINE_EVIDENCE_FABRIC", "1").strip()
            or "1") != "0"

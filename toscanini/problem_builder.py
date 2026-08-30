"""Evidence-bound problem builder — free text -> EngineRun problem dict.

Constitutional pattern (Art. XX / XXI, mirroring the six-domain benchmark
builders): a problem typed by a user is a HYPOTHESIS until live evidence
retrieval binds it. Flow:

  1. MODEL_DERIVED extraction (LLM via the engine's own llm_registry):
     domain family, device, failure_mode, constraint, retrieval queries.
  2. LIVE retrieval through the engine's source connectors (family routed
     by domain). Every connector result is recorded with its status;
     provider failure is recorded as failure, never as absence (Art. XXI.3).
  3. Failure statement composed from the retrieved records with the
     source-class limitations stamped INLINE (Art. XXI.5 generalized).

The output problem dict is exactly the engine's problem schema
({problem_id, device, failure_mode, failure, constraint, sources}), so the
UI path runs the SAME engine as the campaigns — no second engine.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Domain families -> engine connectors (existing, live-measured)
# ---------------------------------------------------------------------------


def _families():
    """Lazy import so the server can list sessions without heavy imports."""
    from discovery_fabric.source_registry.connectors.openfda import (
        MaudeConnector)
    from discovery_fabric.source_registry.connectors.scientific import (
        EuropePmcConnector, ArxivConnector)
    from discovery_fabric.source_registry.connectors.failure_universe import (
        NhtsaComplaintConnector, CpscRecallConnector, FraRailAccidentConnector)
    from discovery_fabric.source_registry.connectors.govtech_reports import (
        NasaNtrsConnector, DoeOstiConnector)
    from discovery_fabric.source_registry.connectors.nonmedical_failure import (
        NhtsaRecallConnector)
    from discovery_fabric.source_registry.connectors.materials import (
        CodOptimadeConnector)
    return {
        "medical": [
            ("fda_maude", "failure", MaudeConnector),
            ("europepmc", "science", EuropePmcConnector),
        ],
        "automotive": [
            ("nhtsa_complaints", "failure", NhtsaComplaintConnector),
            ("nhtsa_recalls", "failure", NhtsaRecallConnector),
        ],
        "energy": [
            ("nhtsa_complaints", "failure", NhtsaComplaintConnector),
            ("doe_osti", "science", DoeOstiConnector),
        ],
        "aerospace": [
            ("nasa_ntrs", "science", NasaNtrsConnector),
            ("doe_osti", "science", DoeOstiConnector),
        ],
        "electronics": [
            ("cpsc_recalls", "failure", CpscRecallConnector),
            ("arxiv", "science", ArxivConnector),
        ],
        "industrial": [
            ("fra_rail_accidents", "failure", FraRailAccidentConnector),
            ("doe_osti", "science", DoeOstiConnector),
        ],
        "materials": [
            ("cod_optimade", "property", CodOptimadeConnector),
            ("arxiv", "science", ArxivConnector),
        ],
        "general": [
            ("europepmc", "science", EuropePmcConnector),
            ("arxiv", "science", ArxivConnector),
            ("doe_osti", "science", DoeOstiConnector),
        ],
    }


LIMIT_STAMPS = {
    "failure": ("LIMITS STAMPED INLINE: voluntary/regulatory reports; counts "
                "are NOT incidence rates; causality UNVERIFIED (Art. XXI.5)"),
    "science": ("LIMITS STAMPED INLINE: literature context establishes the "
                "problem class, not event rates"),
    "property": ("LIMITS STAMPED INLINE: property databases characterize "
                 "materials, not field failures"),
}


# ---------------------------------------------------------------------------
# Query-form discipline — CEO source-routing directive 2026-08-31.
# The IMPLEMENTATION lives in the engine (discovery_fabric/source_registry/
# query_relevance.keyword_form) so the UI builder and the prior-art
# collision stage share ONE method; re-exported here for convenience.
# ---------------------------------------------------------------------------
from discovery_fabric.source_registry.query_relevance import (  # noqa: E402
    is_question_form as _is_question_form,
    keyword_form,
)

_INTERROGATIVE_RE = re.compile(
    r"^(how|why|what|when|which|where|who|can|could|should|is|are|do|does|did)\b[ \-]?",
    re.IGNORECASE,
)


def _slug(text: str, n: int = 42) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return s[:n].rstrip("_") or "problem"


def extract_problem_fields(text: str) -> Dict[str, Any]:
    """LLM extraction of structured problem fields (MODEL_DERIVED).

    Uses the engine's llm_registry single entry point; the model may propose
    but retrieval decides admissibility (Art. XVIII). Models sometimes omit
    fields — one corrective retry lists the missing fields; if DEVICE or
    FAILURE_MODE are still absent they are derived from FAILURE_QUERY (all
    still MODEL_DERIVED, never presented as evidence)."""
    from discovery_fabric.engine import llm_registry as reg
    schema = ["DOMAIN", "DEVICE", "FAILURE_MODE", "CONSTRAINT",
              "FAILURE_QUERY", "SCIENCE_QUERY", "VEHICLE"]
    system = (
        "You convert a user's engineering problem description into "
        "structured discovery-engine fields. The first SIX field lines are "
        "MANDATORY, each on its own line as FIELD: value. DOMAIN must be "
        "exactly one of: medical, automotive, energy, aerospace, "
        "electronics, industrial, materials, general. DEVICE is a concise "
        "noun phrase naming the technical system (never a question). "
        "FAILURE_MODE is a concise noun phrase naming the failure "
        "mechanism. FAILURE_QUERY and SCIENCE_QUERY are KEYWORD search "
        "strings: 3-8 content nouns each, NO question words (how/why/what), "
        "NO punctuation — e.g. 'lithium battery thermal runaway', not 'Why "
        "do lithium batteries fail?'. CONSTRAINT states the engineering "
        "requirement any solution must satisfy. VEHICLE is OPTIONAL: only "
        "when the problem names a specific road vehicle, emit VEHICLE: "
        "make|model|year (e.g. VEHICLE: toyota|camry|2020); otherwise omit "
        "the line. No preamble, no markdown.")
    prompt = f"User problem description:\n\"\"\"\n{text[:2000]}\n\"\"\""

    def _parse(content: str) -> Dict[str, str]:
        parsed = {}
        for line in (content or "").splitlines():
            m = re.match(r"^\s*[*_`>-]*\s*([A-Z_]+)\s*[:\u2013-]\s*(.+?)\s*$",
                         line.strip())
            if m and m.group(1) in schema:
                parsed.setdefault(m.group(1).lower(), m.group(2).strip())
        return parsed

    res = reg.generate(system=system, prompt=prompt, schema=schema,
                       timeout=180, max_tokens=420)
    parsed = _parse(res.content) if res.status == "OK" else {}
    missing = [f for f in schema[:6] if f.lower() not in parsed]
    if missing and res.status == "OK":
        retry = reg.generate(
            system=system,
            prompt=(f"User problem description:\n\"\"\"\n{text[:2000]}\n\"\"\"\n\n"
                    f"Your previous reply omitted these mandatory fields: "
                    f"{', '.join(missing)}. Reply again with ALL SIX field "
                    f"lines."),
            schema=schema, timeout=180, max_tokens=420)
        if retry.status == "OK":
            parsed.update(_parse(retry.content))
            parsed["_retried"] = True

    # Deterministic MODEL_DERIVED derivation for any still-missing core field.
    # 2026-08-31 fix (relevance-failure investigation): the old fallback
    # `parsed.get('failure_query') or text[:60]` passed the raw user
    # QUESTION to search APIs when the LLM omitted the field. Fallbacks now
    # derive keyword-form content — never the raw interrogative sentence.
    fq = parsed.get("failure_query") or keyword_form(text) or text[:60]
    # Query-form discipline: whatever the LLM proposed, queries leaving
    # this builder for free-text sources are keyword-form (measured OSTI
    # degradation on question strings; the rule is deterministic and
    # disclosed in keyword_form's docstring).
    if parsed.get("failure_query"):
        parsed["failure_query"] = (keyword_form(parsed["failure_query"])
                                    or parsed["failure_query"])
    if parsed.get("science_query"):
        parsed["science_query"] = (keyword_form(parsed["science_query"])
                                   or parsed["science_query"])
    # VEHICLE grammar validation: only a well-formed make|model|year value
    # may reach the NHTSA connectors (their grammar gate refuses anything
    # else — here we pre-filter so the routing decision is visible).
    veh = parsed.get("vehicle") or ""
    if veh and not re.fullmatch(r"[\w .\-]+\|[\w .\-]+\|\d{4}", veh):
        parsed["_vehicle_dropped"] = veh
        parsed.pop("vehicle")
    if "device" not in parsed:
        parsed["device"] = " ".join(fq.split()[:4])
    if "failure_mode" not in parsed:
        parsed["failure_mode"] = " ".join(fq.split()[4:10]) or fq
    parsed.setdefault("constraint",
                      "Solution must address the documented failure mode "
                      "without introducing a larger one.")
    parsed["_llm"] = {
        "status": res.status, "provider": res.provider_id,
        "latency_ms": res.latency_ms,
    }
    return parsed


def _record_years(records: List[dict]) -> str:
    years = []
    for r in records:
        for k, v in (r.get("normalized") or {}).items():
            if isinstance(v, str) and len(v) >= 4 and v[:2] in ("19", "20") \
                    and v[2:4].isdigit():
                years.append(v[:4])
    return f"{min(years)}-{max(years)}" if years else "dates in custody log"


def _narratives(records: List[dict], n: int = 2, maxlen: int = 200) -> List[str]:
    out = []
    for r in records:
        norm = r.get("normalized") or {}
        v = None
        for field in ("event_text", "summary", "description", "narrative",
                      "cause", "hazards", "products"):
            cand = norm.get(field)
            if isinstance(cand, str) and len(cand) > 40:
                v = cand
                break
        if v is None:
            t = r.get("title") or ""
            if len(t) > 40:
                v = t
        if v:
            out.append(v[:maxlen])
        if len(out) >= n:
            break
    return out


def _search_one(name: str, role: str, cls, query: str, timeout: int = 40,
                run_id: str = "toscanini:ui"):
    try:
        conn = cls()
        res = conn.search(query, timeout=timeout)
        recs = [r.to_dict() for r in res.records] if res.status == "OK" else []
        # Art. XXI.4: every record entering the evidence pipeline is
        # relevance-adjudicated with the SAME term-overlap rule as the
        # discovery pipeline and the battery (one method, not two), and the
        # adjudication is persisted in custody through the SAME aggregation
        # path (maturity §6.1 closure).
        from discovery_fabric.source_registry import query_relevance as _qr
        from discovery_fabric.source_registry import relevance_aggregation as _ra
        adjudications = [
            _qr.adjudicate_record(rec, query) for rec in recs]
        n_rel = sum(1 for a in adjudications
                    if a["relevance"] == _qr.RELEVANT)
        try:
            _ra.record_adjudications(
                source_id=res.source_id or name,
                query=query,
                adjudicated_records=adjudications,
                run_id=run_id,
                provider_status=res.status,
            )
        except Exception as exc:  # noqa: BLE001 — disclosed, never silent
            return {"source": name, "role": role, "status": res.status,
                    "count": len(recs), "records": recs,
                    "relevant": n_rel,
                    "custody_note": f"relevance-custody append failed: {exc}",
                    "error": (res.error or "")[:160] if res.status != "OK" else ""}
        return {"source": name, "role": role, "status": res.status,
                "count": len(recs), "records": recs,
                "relevant": n_rel,
                "error": (res.error or "")[:160] if res.status != "OK" else ""}
    except Exception as exc:  # noqa: BLE001
        return {"source": name, "role": role, "status": "CALL_FAILED",
                "count": 0, "records": [], "relevant": 0,
                "error": f"{type(exc).__name__}: {exc}"[:160]}


def build_problem(text: str, on_event=None) -> Dict[str, Any]:
    """Free text -> {problem, evidence_pack, extraction}.

    on_event(cb) receives progress dicts for the UI stream
    ({"phase": "..."}), all derived from real steps — no fabricated
    progress events.
    """
    def emit(ev: dict):
        if on_event:
            on_event(ev)

    emit({"phase": "EXTRACT", "label": "Structuring the problem "
          "(MODEL_DERIVED extraction)"})
    extraction = extract_problem_fields(text)
    domain = (extraction.get("domain") or "general").strip().lower()
    if domain not in _families():
        domain = "general"
    device = extraction.get("device") or text[:80]
    failure_mode = extraction.get("failure_mode") or "unspecified failure mode"
    constraint = (extraction.get("constraint")
                  or "Solution must address the documented failure mode "
                     "without introducing a larger one.")
    # 2026-08-31 query-form discipline: free-text search sources receive
    # KEYWORD-form queries (keyword_form applied inside extraction; the
    # fallbacks below also derive keyword content — never the raw
    # interrogative user sentence, which measurably degrades/zeroes OSTI).
    fail_q = extraction.get("failure_query") or keyword_form(device)
    sci_q = (extraction.get("science_query")
             or keyword_form(f"{device} {failure_mode}"))
    vehicle = extraction.get("vehicle") or ""
    # Defensive re-validation at the routing boundary (the extraction path
    # validates too, but build_problem must be safe against any caller):
    # only a well-formed make|model|year reaches the NHTSA grammar.
    if vehicle and not re.fullmatch(r"[\w .\-]+\|[\w .\-]+\|\d{4}", vehicle):
        vehicle = ""

    emit({"phase": "RETRIEVE_EVIDENCE", "label":
          f"Live evidence retrieval — domain family '{domain}'"})
    results = []
    routing_notes = []
    for name, role, cls in _families()[domain]:
        # Grammar-aware routing (CEO source-routing directive 2026-08-31):
        # the automotive family's NHTSA connectors answer ONLY
        # make|model|year questions. Without an extracted vehicle, asking
        # them a free-text failure query is a question they cannot answer
        # (measured: HTTP 500, burned as a provider failure). The source is
        # honestly recorded as NOT_QUERIED_GRAMMAR — an engine routing
        # decision, never absence (Art. XXV).
        if getattr(cls, "QUERY_GRAMMAR", "") and "make|model|year" in cls.QUERY_GRAMMAR \
                and not vehicle:
            routing_notes.append(
                f"{name}: not queried — no vehicle (make|model|year) "
                f"extracted from the problem; this source answers "
                f"vehicle-parameterized questions only")
            results.append({
                "source": name, "role": role,
                "status": "NOT_QUERIED_GRAMMAR", "count": 0,
                "records": [], "relevant": 0,
                "error": "no vehicle extracted; source grammar is "
                         "make|model|year (routing decision, not absence)",
            })
            continue
        # NHTSA-style sources WITH a vehicle: the vehicle IS the query —
        # the failure query is free-text and would be a grammar mismatch.
        query = vehicle if getattr(cls, "QUERY_GRAMMAR", "") and "make|model|year" \
            in cls.QUERY_GRAMMAR else (fail_q if role == "failure" else sci_q)
        emit({"phase": "RETRIEVE_EVIDENCE", "label":
              f"Querying {name} ({role}): '{query[:70]}'"})
        results.append(_search_one(name, role, cls, query))

    ok_results = [r for r in results if r["status"] == "OK"]
    emit({"phase": "EVIDENCE_BOUND", "label":
          f"Evidence bound: {len(ok_results)}/{len(results)} sources OK"})

    # Compose the failure statement from retrieved records (Art. XX).
    parts = [f"User-submitted engineering problem (session input): "
             f"\"{text[:300]}\". "]
    for note in routing_notes:
        parts.append(f"ROUTING: {note}.")
    for r in results:
        if r["status"] != "OK" or not r["records"]:
            parts.append(f"[{r['source']}] retrieval status {r['status']}"
                         + (f" ({r['error']})" if r["error"] else "")
                         + " — provider outcome recorded, not treated as "
                           "absence (Art. XXI.3).")
            continue
        recs = r["records"]
        nars = _narratives(recs)
        parts.append(
            f"[{r['source']}] {len(recs)} records retrieved live "
            f"({_record_years(recs)}). "
            + ("Illustrative records: "
               + "; ".join(f"'{q}'" for q in nars) + ". " if nars else "")
            + LIMIT_STAMPS.get(r["role"], "") + ".")
    failure = (
        f"Documented problem '{failure_mode}' concerning {device}. "
        + " ".join(parts)
        + f" Problem-existence basis: {'live records retrieved' if ok_results else 'NO SOURCE RETURNED RECORDS — problem existence UNVERIFIED by live evidence (Art. XX); treat as hypothesis'}."
    )

    problem_id = f"ui_{_slug(failure_mode)}_{int(time.time()) % 1000000}"
    problem = {
        "problem_id": problem_id,
        "device": device,
        "failure_mode": failure_mode,
        "failure": failure,
        "constraint": constraint,
        "sources": {r["source"]: r["status"] for r in results},
        "origin": "toscanini_ui",
        "user_text": text[:2000],
    }
    evidence_pack = {
        "extraction": {
            "domain": domain, "device": device, "failure_mode": failure_mode,
            "epistemic_class": "MODEL_DERIVED",
            "llm": {k: extraction["_llm"][k] for k in
                    ("status", "provider", "latency_ms")},
            "user_text_epistemic_class": "EXTERNAL_EVIDENCE",
            "query_form": "keyword (deterministic normalization; question "
                          "forms degraded measured relevance — 2026-08-31 "
                          "investigation)",
            "routing_notes": routing_notes,
        },
        "retrieval": [
            {"source": r["source"], "role": r["role"], "status": r["status"],
             "count": r["count"], "relevant": r.get("relevant"),
             "error": r["error"],
             "epistemic_class": "EXTERNAL_EVIDENCE",
             "records": [
                 {"title": (rec.get("title")
                            or (rec.get("normalized") or {}).get("summary")
                            or rec.get("source_id") or "(untitled record)")[:180],
                  "source_id": rec.get("source_id") or "",
                  "uri": rec.get("source_uri") or "",
                  "date": (rec.get("publication_date")
                           or (rec.get("normalized") or {}).get("date") or ""),
                  }
                 for rec in r["records"][:8]]}
            for r in results],
    }
    return {"problem": problem, "evidence_pack": evidence_pack,
            "domain": domain}

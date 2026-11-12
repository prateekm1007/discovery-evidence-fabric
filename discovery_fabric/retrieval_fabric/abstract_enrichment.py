"""Keyless abstract enrichment (owner round 2026-11-12, item A1).

Measured starvation cause (live baseline over the 12 DEV problems, pre-fix
envelope committed as eval/score/R6_RETRIEVAL_BEFORE_12.json): ~57% of
canonical records arrive abstract-less (the crossref title-only lane
dominates), and the existing S2 backfill enriched 0 of 6 attempts
(rate-limited keyless shared pool). This layer adds the keyless
OpenAlex abstract_inverted_index reconstruction in BATCH form (up to 50
DOIs per API call — the one-call-per-50 discipline OpenAlex documents;
cost ~$0.0001/DOI against the keyless polite pool, recorded in the
custody log), plus bounded arXiv / Europe PMC / Semantic Scholar
fallbacks for the records still textless after the batch pass.

Discipline (Art. XXV / XXI.3 / VI):
  * every attempt is typed and custody-logged (retrieval_log) — a source
    that returns nothing is EMPTY, a 429 is RATE_LIMITED, never absence;
  * every enrichment records provenance ON the record
    (abstract_enriched_from + abstract_enrichment_sha256) — it is a
    recorded enrichment, never a silent rewrite;
  * no new credential: OpenAlex keyless (mailto polite pool), arXiv open
    API, Europe PMC open webservice, S2 keyless graph (the existing
    reciprocal _s2_get path);
  * deterministic candidate order: citation-count desc, then
    canonical_id (same key as the backfill above it).
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple

_OA_BASE = "https://api.openalex.org/works"
_ARXIV_API = "https://export.arxiv.org/api/query"
_EPMC_SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
_USER_AGENT = "discovery-evidence-fabric (abstract-enrichment)"


def _env_int(name: str, default: int) -> int:
    try:
        return int(float((os.environ.get(name, "") or "").strip() or default))
    except (TypeError, ValueError):
        return default


def _openalex_mailto() -> str:
    """Same budget-window discipline as the OpenAlexConnector: the
    registered contact email (OPENALEX_EMAIL in .env.keys) switches the
    keyless request onto the polite pool; the placeholder keeps today's
    behavior when it is absent (the connector's own measured note)."""
    try:
        from discovery_fabric.source_registry.keys import load_key
        return load_key("OPENALEX_EMAIL") or "discovery-fabric@example.org"
    except Exception:  # noqa: BLE001 — credential layer optional here
        return "discovery-fabric@example.org"


def _http_get(url: str, timeout: int = 40) -> Tuple[int, bytes, str, int]:
    """Raw HTTP GET as (status, body, error, latency_ms). One typed
    result per call; no retry storms (the breaker belongs to the LLM
    path, not retrieval: retrieval failures are recorded lane states,
    Art. XXI.3)."""
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    t0 = time.perf_counter()
    status, body, err = 0, b"", ""
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            status, body = r.getcode(), r.read()
    except urllib.error.HTTPError as e:
        status, body = e.code, (e.read() if e.fp else b"")
    except Exception as e:  # noqa: BLE001 — typed, recorded
        err = f"{type(e).__name__}: {e}"[:200]
    return status, body, err, int((time.perf_counter() - t0) * 1000)


def _reconstruct_abstract(inverted: Optional[Dict[str, Any]]) -> Optional[str]:
    """Reuse the shipped OpenAlex mapper (byte-identical instrument)."""
    from discovery_fabric.connectors.openalex.mapper import (
        _reconstruct_abstract as _map_reconstruct,
    )
    return _map_reconstruct(inverted or {})


def _norm_doi(doi: str) -> str:
    d = str(doi or "").strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if d.startswith(prefix):
            d = d[len(prefix):]
    return d


def _record_arxiv_id(rec: Any) -> str:
    """An arXiv identifier from any of the three carrying places
    (connector normalized field, DataCite DOI form, canonical id basis)."""
    br = rec.best_record or {}
    aid = str(br.get("arxiv_id") or "").strip()
    if aid:
        return aid
    doi = str(rec.doi or "")
    if doi.lower().startswith("10.48550/arxiv."):
        return doi.split("/", 1)[1]
    if rec.canonical_id.startswith("arxiv:"):
        return rec.canonical_id.split(":", 1)[1]
    return ""


def _apply(rec: Any, text: str, from_source: str) -> bool:
    """Enrich the record with provenance (Art. VI: recorded, never silent).
    Only a LONGER abstract is applied (a source saying less than what we
    already hold is a no-op, recorded as EMPTY)."""
    if len(text) <= len((rec.best_record.get("abstract") or "")):
        return False
    rec.best_record["abstract"] = text[:4000]
    rec.best_record["abstract_enriched_from"] = from_source
    rec.best_record["abstract_enrichment_sha256"] = hashlib.sha256(
        text.encode("utf-8")).hexdigest()
    return True


def _openalex_batch(dois: List[str], batch: int,
                    mailto: str) -> Dict[str, Any]:
    """Keyless OpenAlex calls of <=50 DOIs each (their documented batch
    form: filter=doi:a|doi:b, select=doi,abstract_inverted_index).
    Returns {doi: {norm_doi: abstract_or_empty}, status, error,
    record_count, raw_sha, http_status, latency_ms}."""
    out: Dict[str, Any] = {"doi": {}, "status": "OK", "error": None,
                           "record_count": 0, "raw_sha": None,
                           "http_status": None, "latency_ms": None}
    for i in range(0, len(dois), batch):
        chunk = dois[i:i + batch]
        flt = "doi:" + "|".join(chunk)
        url = (f"{_OA_BASE}?filter={urllib.parse.quote(flt)}"
               f"&select=doi,abstract_inverted_index"
               f"&per-page={min(len(chunk), 50)}"
               f"&mailto={urllib.parse.quote(mailto)}")
        status, body, err, lat = _http_get(url)
        out["latency_ms"] = lat
        out["http_status"] = status
        out["raw_sha"] = hashlib.sha256(body).hexdigest() if body else None
        if err:
            out["status"] = f"ERROR_{err.split(':')[0]}"
            out["error"] = err
            break
        if status != 200:
            out["status"] = ("RATE_LIMITED" if status == 429
                            else f"HTTP_{status}")
            out["error"] = f"HTTP {status}"
            break
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            out["status"] = "ERROR_PAYLOAD"
            out["error"] = f"{type(e).__name__}"[:100]
            break
        for w in (payload.get("results") or []):
            nd = _norm_doi(w.get("doi") or "")
            abstract = _reconstruct_abstract(w.get("abstract_inverted_index"))
            out["doi"][nd] = (abstract or "").strip()
            out["record_count"] += 1
    return out


def _arxiv_batch(ids: List[str]) -> Dict[str, Any]:
    """Bounded arXiv API id_list query; the Atom <summary> IS the
    abstract (the preprint's own text, the richest free form)."""
    out: Dict[str, Any] = {"arxiv": {}, "status": "OK", "error": None,
                           "record_count": 0, "raw_sha": None,
                           "http_status": None, "latency_ms": None}
    if not ids:
        return out
    url = (f"{_ARXIV_API}?id_list={urllib.parse.quote(','.join(ids))}"
           f"&max_results={min(len(ids), 20)}")
    status, body, err, lat = _http_get(url, timeout=60)
    out["latency_ms"] = lat
    out["http_status"] = status
    out["raw_sha"] = hashlib.sha256(body).hexdigest() if body else None
    if err:
        out["status"] = f"ERROR_{err.split(':')[0]}"
        out["error"] = err
        return out
    if status != 200:
        out["status"] = ("RATE_LIMITED" if status == 429
                         else f"HTTP_{status}")
        out["error"] = f"HTTP {status}"
        return out
    ns = {"a": "http://www.w3.org/2005/Atom"}
    try:
        root = ET.fromstring(body.decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        out["status"] = "ERROR_PAYLOAD"
        out["error"] = f"{type(e).__name__}"[:100]
        return out
    for entry in root.findall("a:entry", ns):
        id_elem = entry.find("a:id", ns)
        summary = entry.find("a:summary", ns)
        if id_elem is None:
            continue
        m = id_elem.gettext() or ""
        m = m.rsplit("/", 1)[-1]
        m = m.split("v")[0] if m.lower().startswith("arxiv:") else m
        out["arxiv"][m] = ((summary.gettext() or "").strip()
                           if summary is not None else "")
        out["record_count"] += 1
    return out


def _epmc_doi(doi: str) -> Dict[str, Any]:
    """Bounded Europe PMC DOI search; abstractText when the record is
    abstract-bearing (many protocol/article types carry none — recorded
    as EMPTY, never invented, Art. XXV)."""
    out: Dict[str, Any] = {"abstract": "", "status": "OK", "error": None,
                           "record_count": 0, "raw_sha": None,
                           "http_status": None, "latency_ms": None}
    url = (f"{_EPMC_SEARCH}?query={urllib.parse.quote('DOI:\"' + doi + '\"')}"
           f"&format=json&pageSize=1")
    status, body, err, lat = _http_get(url)
    out["latency_ms"] = lat
    out["http_status"] = status
    out["raw_sha"] = hashlib.sha256(body).hexdigest() if body else None
    if err:
        out["status"] = f"ERROR_{err.split(':')[0]}"
        out["error"] = err
        return out
    if status != 200:
        out["status"] = ("RATE_LIMITED" if status == 429 else f"HTTP_{status}")
        out["error"] = f"HTTP {status}"
        return out
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        out["status"] = "ERROR_PAYLOAD"
        out["error"] = f"{type(e).__name__}"[:100]
        return out
    results = (payload.get("resultList") or {}).get("result") or []
    if results:
        out["abstract"] = str(results[0].get("abstractText") or "").strip()
        out["record_count"] = 1
        if not out["abstract"]:
            out["status"] = "EMPTY"
    else:
        out["status"] = "EMPTY"
    return out


def _s2_doi(doi: str) -> Dict[str, Any]:
    """The EXISTING keyless S2 metadata path (reciprocal._s2_get) — the
    backfill's own source, reused for the records the batch pass missed."""
    from discovery_fabric.retrieval_fabric import reciprocal as _recip
    url = (f"{_recip._S2_GRAPH}/paper/DOI:{urllib.parse.quote(doi)}"
           "?fields=title,abstract,externalIds")
    r = _recip._s2_get(url)
    abstract = ""
    if r.get("status") == "OK" and isinstance(r.get("data"), dict):
        abstract = str(r["data"].get("abstract") or "").strip()
        if not abstract:
            r["status"] = "EMPTY"
    return {"abstract": abstract, "status": str(r.get("status")),
            "error": r.get("error"),
            "record_count": 1 if abstract else 0,
            "raw_payload_sha256": r.get("raw_payload_sha256"),
            "http_status": r.get("http_status"),
            "latency_ms": r.get("latency_ms")}


def enrich_missing_abstracts(canonicalizer: Any,
                             lane_states: List[Any],
                             problem: Optional[Dict[str, Any]] = None,
                             ) -> Dict[str, Any]:
    """Run the keyless enrichment passes over the canonical pool.

    Pass order (deterministic; earlier passes cost less):
      1. OpenAlex batch (bounded top-K by citation, one call per <=50)
      2. arXiv API batch (preprints still textless)
      3. Europe PMC (DOI records still textless, bounded)
      4. Semantic Scholar (DOI records still textless, bounded; the
         backfill above already took the top-6, this is the remainder)
    """
    from discovery_fabric.retrieval_fabric.adapters import LaneRunState
    from discovery_fabric.source_registry.retrieval_log import append_entry

    enabled = _env_int("RETRIEVE_ABSTRACT_ENRICH", 1)
    if enabled <= 0:
        return {"enabled": False, "note":
                "disabled by RETRIEVE_ABSTRACT_ENRICH<=0"}
    oa_batch = _env_int("RETRIEVE_ENRICH_OA_BATCH", 50)
    oa_k = _env_int("RETRIEVE_ENRICH_OA_K", 25)
    epmc_k = _env_int("RETRIEVE_ENRICH_EPMC_K", 12)
    s2_k = _env_int("RETRIEVE_ENRICH_S2_K", 8)

    candidates = [r for r in canonicalizer.canonical_records()
                  if ((r.doi or _record_arxiv_id(r))
                      and len((r.best_record.get("abstract") or "")) < 50
                      and r.evidence_lane in ("SCHOLARLY", "PREPRINT"))]
    candidates.sort(key=lambda r: (
        -(r.best_record.get("citation_count")
          or r.best_record.get("cited_by_count") or 0),
        r.canonical_id))
    n_candidates = len(candidates)

    report: Dict[str, Any] = {"enabled": True, "candidates": n_candidates,
                              "passes": {}, "enriched": 0,
                              "textless_after": 0,
                              "note": ("keyless OpenAlex batch + arXiv + "
                                       "Europe PMC + S2 fallbacks; typed "
                                       "per-attempt, custody-logged")}

    def _textless() -> List[Any]:
        return [r for r in candidates
                if len((r.best_record.get("abstract") or "")) < 50]

    # ---- pass 1: OpenAlex abstract_inverted_index batch --------------
    doi_recs = [r for r in _textless() if r.doi][:oa_k]
    if doi_recs:
        res = _openalex_batch([r.doi for r in doi_recs], oa_batch,
                              _openalex_mailto())
        enriched_here = 0
        for r in doi_recs:
            got = res["doi"].get(_norm_doi(r.doi))
            if got and _apply(r, got, "openalex_abstract_inverted_index"):
                enriched_here += 1
        append_entry(
            source_id="openalex",
            query=f"abstract-enrichment-batch:{len(doi_recs)}-dois",
            url=(f"{_OA_BASE}?filter=doi:<{len(doi_recs)} doIs, "
                 f"batch of {oa_batch}>"),
            status=res["status"], http_status=res.get("http_status"),
            latency_ms=res.get("latency_ms"),
            record_count=res.get("record_count") or 0,
            raw_payload_sha256=res.get("raw_sha"),
            error=res.get("error"),
            retrieval_role="FULLTEXT_RESOLUTION")
        report["passes"]["openalex"] = {"attempted": len(doi_recs),
                                        "returned": res.get("record_count") or 0,
                                        "enriched": enriched_here,
                                        "status": res["status"],
                                        "batch_size": oa_batch,
                                        "error": res.get("error")}
        report["enriched"] += enriched_here

    # ---- pass 2: arXiv preprints still textless ----------------------
    arxiv_recs = [r for r in _textless() if _record_arxiv_id(r)]
    if arxiv_recs:
        ids = [_record_arxiv_id(r) for r in arxiv_recs]
        res = _arxiv_batch(ids)
        enriched_here = 0
        for r in arxiv_recs:
            got = res["arxiv"].get(_record_arxiv_id(r))
            if got and _apply(r, got, "arxiv_api"):
                enriched_here += 1
        append_entry(
            source_id="arxiv",
            query=f"abstract-enrichment-arxiv:{len(arxiv_recs)}-ids",
            url=f"{_ARXIV_API}?id_list=<{len(arxiv_recs)} ids>",
            status=res["status"], http_status=res.get("http_status"),
            latency_ms=res.get("latency_ms"),
            record_count=res.get("record_count") or 0,
            raw_payload_sha256=res.get("raw_sha"),
            error=res.get("error"),
            retrieval_role="FULLTEXT_RESOLUTION")
        report["passes"]["arxiv"] = {"attempted": len(arxiv_recs),
                                     "enriched": enriched_here,
                                     "status": res["status"],
                                     "error": res.get("error")}
        report["enriched"] += enriched_here

    # ---- pass 3: Europe PMC (bounded) --------------------------------
    epmc_recs = [r for r in _textless() if r.doi][:epmc_k]
    if epmc_recs:
        per_lookup = []
        enriched_here = 0
        for r in epmc_recs:
            res = _epmc_doi(r.doi)
            ok = bool(res["abstract"]) and _apply(
                r, res["abstract"], "europepmc_abstract")
            if ok:
                enriched_here += 1
            append_entry(
                source_id="europepmc",
                query=f"abstract-enrichment:doi:{r.doi}",
                url=(f"{_EPMC_SEARCH}?query={urllib.parse.quote('DOI:\"' + r.doi + '\"')}"
                     f"&format=json&pageSize=1"),
                status=("OK" if ok else res["status"]),
                http_status=res.get("http_status"),
                latency_ms=res.get("latency_ms"),
                record_count=1 if ok else 0,
                raw_payload_sha256=res.get("raw_sha"),
                error=(None if ok else
                       (res.get("error") or "no abstractText in the "
                        "Europe PMC record (typed EMPTY, never absence)")),
                retrieval_role="FULLTEXT_RESOLUTION")
            per_lookup.append({"doi": r.doi, "status": res["status"],
                               "enriched": ok})
        report["passes"]["europepmc"] = {"attempted": len(epmc_recs),
                                         "enriched": enriched_here,
                                         "lookups": per_lookup}
        report["enriched"] += enriched_here

    # ---- pass 4: Semantic Scholar (bounded remainder) ---------------
    s2_recs = [r for r in _textless() if r.doi][:s2_k]
    if s2_recs:
        per_lookup = []
        enriched_here = 0
        for r in s2_recs:
            res = _s2_doi(r.doi)
            ok = bool(res["abstract"]) and _apply(
                r, res["abstract"], "semantic_scholar_metadata")
            if ok:
                enriched_here += 1
            append_entry(
                source_id="semantic_scholar_metadata",
                query=f"abstract-enrichment:doi:{r.doi}",
                url=(f"https://api.semanticscholar.org/graph/v1"
                     f"/paper/DOI:{urllib.parse.quote(r.doi)}"
                     "?fields=title,abstract,externalIds"),
                status=("OK" if ok else res["status"]),
                http_status=res.get("http_status"),
                latency_ms=res.get("latency_ms"),
                record_count=1 if ok else 0,
                raw_payload_sha256=res.get("raw_payload_sha256"),
                error=(None if ok else
                       (str(res.get("error") or "")[:200] or
                        "no abstract from the S2 metadata lane "
                        "(typed, never absence)")),
                retrieval_role="FULLTEXT_RESOLUTION")
            per_lookup.append({"doi": r.doi, "status": res["status"],
                               "enriched": ok})
        report["passes"]["semantic_scholar"] = {
            "attempted": len(s2_recs), "enriched": enriched_here,
            "lookups": per_lookup}
        report["enriched"] += enriched_here

    textless_after = len(_textless())
    report["textless_after"] = textless_after
    if textless_after:
        report["note"] += (f"; {textless_after} of {n_candidates} "
                           "candidates remain textless after all keyless "
                           "passes (typed per-pass, never fabricated)")
    lane_states.append(LaneRunState(
        lane="SCHOLARLY", source_id="abstract_enrichment",
        queries=[f"keyless enrichment for {n_candidates} textless "
                 f"records (OpenAlex batch + arXiv + EPMC + S2)"],
        status=("OK" if report["enriched"]
                else ("EMPTY" if n_candidates else "NOT_RUN")),
        record_count=report["enriched"],
        error=(None if not textless_after else
               f"{textless_after} of {n_candidates} still textless "
               "after all keyless passes (typed per-pass)")))
    return report

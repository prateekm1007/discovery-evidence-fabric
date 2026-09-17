"""Free Evidence Sources — the Patent Evidence Fabric's first free legs (R499).

Operator directive (2026-09-18): "use huggingface and other free sources".

Two legs, both MEASURED LIVE this round (R499/R499_FREE_SOURCE_PROBES.json):

LEG A — HUGGING FACE USPTO CORPUS (Tier-3 ML/RAG corpus, discovery side)
    The HF datasets-server (https://datasets-server.huggingface.co) serves
    common-pile/uspto: 131,755 full-text US patent documents, anonymous,
    free, per-record CC BY 4.0 license, structured ids (US-71623224-A).
    Endpoints measured: /splits 200, /rows 200. /search measured 500
    INDEX_LOADING (typed transient, retriable — never absence).

LEG B — EPO LINKED OPEN DATA (identity + family + primary documents)
    The R498 406 was an endpoint-URL error, not a dead service: the SPARQL
    1.1 protocol endpoint is https://data.epo.org/linked-data/query
    (discovered from the platform's own runtime config + UI bundle this
    round). Measured: publication identity (number/kind/authority/date,
    multi-language titles, abstract), application reference, priorities,
    citation graph (citesPatentPublication both directions), SIMPLE FAMILY
    collapse (application -> family -> member applications -> their
    publications), and Tier-1 PRIMARY DOCUMENT representations (XML + PDF
    both 200, official ep-patent-document DTD). Anonymous, free.

    Measured constraints (typed, never assumed):
    - COVERAGE: EP-centric identity; US publications present but PARTIAL
      (US 3268123 A in-graph; US 8968233 B2 not-in-graph). NOT_IN_GRAPH is
      a coverage state about THIS dataset, never evidence of absence
      (Art. XXI.3, LXXV clause 2).
    - QUERY COST: full-graph scans (unbounded FILTER / GROUP BY COUNT)
      time out; subject-anchored queries return in seconds. All queries
      issued by this transport are subject-anchored by construction.

Constitutional government: Article LXXV (constitution 2.7.0) — every hit
carries the five custody fields; a single green run seals nothing; coverage
is measured, never inferred from counts; secondary indexes discover, primary
records verify.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# ONE schema: reuse the unified hit/result dataclasses from the transport
from .sources import PriorArtHit, SourceQueryResult

# ----------------------- SHARED LOW-LEVEL -----------------------
_SSL = ssl.create_default_context()
_SSL.check_hostname = False
_SSL.verify_mode = ssl.CERT_NONE

_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

TRANSPORT_VERSION = "1.1.0"  # 1.1.0 (R504): HF_TOKEN attach-when-present (disclosed, transport-level)
REGISTERED_SOURCES = ("HF_USPTO_CORPUS", "EPO_LINKED_OPEN_DATA")

# R504 — HF_TOKEN authenticated quota (attach-when-present), measured
# BEFORE integration in BOTH modes per endpoint
# (R504/R504_HF_AUTH_PROBE.json): /splits, /rows and the Hub catalog
# answer 200 in BOTH modes — the authenticated mode never degrades a
# measured endpoint — and the /search 500 warming transient is
# server-side index state, identical in both modes (the credential is
# not a /search lever). The header is attached whenever the HF_TOKEN
# environment variable is present — the canonical Space carries it as a
# standing secret, so the DEPLOYED legs run authenticated — and the
# per-call custody provenance records the credential mode actually used
# (LXXV clause 1). A missing token degrades to the measured keyless
# mode; it is never a failure.
HF_AUTH_ENV = "HF_TOKEN"
HF_MODE_AUTHENTICATED = "AUTHENTICATED_HF_TOKEN"
HF_MODE_ANONYMOUS = "ANONYMOUS"


def hf_auth_header() -> Tuple[Dict[str, str], str]:
    """(headers, credential_mode) for the HF surfaces — attach-when-present."""
    tok = os.environ.get(HF_AUTH_ENV, "")
    if tok:
        return {"Authorization": f"Bearer {tok}"}, HF_MODE_AUTHENTICATED
    return {}, HF_MODE_ANONYMOUS


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(payload: bytes | str) -> str:
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _http_get(url: str, headers: Optional[Dict[str, str]] = None,
              timeout: int = 30, max_bytes: int = 0) -> Tuple[int, bytes, int]:
    h = {"User-Agent": _UA, "Accept": "application/json"}
    if headers:
        h.update(headers)
    t0 = time.time()
    req = urllib.request.Request(url, headers=h, method="GET")
    try:
        resp = urllib.request.urlopen(req, timeout=timeout, context=_SSL)
        if max_bytes:
            body = resp.read(max_bytes)
        else:
            body = resp.read()
        return resp.status, body, int((time.time() - t0) * 1000)
    except urllib.error.HTTPError as e:
        try:
            body = e.read()
        except Exception:
            body = b""
        return e.code, body, int((time.time() - t0) * 1000)
    except urllib.error.URLError as e:
        return -1, str(e).encode(), int((time.time() - t0) * 1000)
    except Exception as e:  # socket timeout etc.
        return -2, str(e).encode(), int((time.time() - t0) * 1000)


# ----------------------- LXXV CUSTODY FIELDS -----------------------
# Constitution 2.7.0, Article LXXV clause 1: five custody fields, preserved
# end to end. A patent-derived assertion missing any field is
# PROVENANCE_INCOMPLETE and may not support a consequential decision.

CUSTODY_FIELDS = ("provenance", "publication_identity", "family_relationship",
                  "temporal_status", "source")


def make_custody(*, source: str, endpoint: str, query: str, retrieved_at_utc: str,
                 publication_number: Optional[str] = None,
                 kind_code: Optional[str] = None,
                 application_reference: Optional[str] = None,
                 family_uri: Optional[str] = None,
                 family_members: Optional[List[str]] = None,
                 publication_date: Optional[str] = None,
                 legal_status_basis: Optional[str] = None) -> Dict[str, Any]:
    """Build the five LXXV custody fields for one evidence object."""
    return {
        "provenance": {
            "source": source,
            "endpoint": endpoint,
            "query": query,
            "retrieved_at_utc": retrieved_at_utc,
        },
        "publication_identity": {
            "publication_number": publication_number,
            "kind_code": kind_code,
            "application_reference": application_reference,
        },
        "family_relationship": {
            "family_uri": family_uri,
            "family_members": family_members or [],
            "family_basis": "SIMPLE_FAMILY" if family_uri else None,
        },
        "temporal_status": {
            "publication_date": publication_date,
            "legal_status_basis": legal_status_basis,
        },
        "source": source,
    }


def custody_completeness(custody: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Type a custody block per LXXV clause 1. Never silently complete."""
    if not custody:
        return {"state": "PROVENANCE_INCOMPLETE", "missing": list(CUSTODY_FIELDS)}
    missing = []
    for f in CUSTODY_FIELDS:
        v = custody.get(f)
        if v is None or v == "" or v == {} or v == []:
            missing.append(f)
    # family is a knowledge boundary the TRANSPORT must declare explicitly
    # (family_uri, or members, or an explicit family_basis like UNKNOWN /
    # NO_FAMILY_TRIPLE_IN_GRAPH). An empty family field is never auto-typed:
    # silent completion is exactly what LXXV forbids.
    if "family_relationship" not in missing:
        fr = custody.get("family_relationship", {})
        if fr.get("family_uri") is None and not fr.get("family_members") and fr.get("family_basis") is None:
            missing.append("family_relationship")
    state = "COMPLETE" if not missing else "PROVENANCE_INCOMPLETE"
    return {"state": state, "missing": missing}


# ----------------------- LEG A: HF USPTO CORPUS -----------------------
# Tier-3 discovery corpus. Free, anonymous, per-record CC BY 4.0.
# Measured R499: /splits 200 (config default / split train, 131,755 rows),
# /rows 200. /search: 500 INDEX_LOADING at probe time (transient server-side
# index build; typed, retriable, never absence).

HF_DSER_BASE = "https://datasets-server.huggingface.co"
HF_USPTO_DATASET = "common-pile/uspto"
HF_USPTO_CONFIG = "default"
HF_USPTO_SPLIT = "train"
HF_ROWS_PAGE_MAX = 100  # datasets-server page cap (per public API docs)

# typed transport states (extend the standing vocabulary; per-call, never assumed)
HF_STATE_OK = "OK"
HF_STATE_INDEX_LOADING = "INDEX_WARMING_TRANSIENT"      # 500 + 'dataset index is loading' — server-side, retriable
HF_STATE_RATE_LIMITED = "RATE_LIMITED"                  # 429
HF_STATE_HTTP_ERROR = "HTTP_ERROR"
HF_STATE_PARSE_ERROR = "PARSE_ERROR"
HF_STATE_TRANSPORT_ERROR = "TRANSPORT_ERROR"
HF_STATE_SCHEMA_MISMATCH = "SCHEMA_MISMATCH"


def hf_uspto_corpus_status() -> Dict[str, Any]:
    """Measure the corpus (splits + row count). A count signal, never coverage (LXXV.2)."""
    url = f"{HF_DSER_BASE}/splits?dataset={urllib.parse.quote(HF_USPTO_DATASET)}"
    auth_h, cred_mode = hf_auth_header()
    status, body, latency = _http_get(url, headers=auth_h)
    if status != 200:
        return {"source_id": "HF_USPTO_CORPUS", "state": HF_STATE_HTTP_ERROR if status > 0 else HF_STATE_TRANSPORT_ERROR,
                "http_status": status, "latency_ms": latency,
                "credential_mode": cred_mode}
    try:
        js = json.loads(body)
    except Exception as e:
        return {"source_id": "HF_USPTO_CORPUS", "state": HF_STATE_PARSE_ERROR, "error": str(e),
                "credential_mode": cred_mode}
    splits = js.get("splits", [])
    return {"source_id": "HF_USPTO_CORPUS", "state": HF_STATE_OK,
            "dataset": HF_USPTO_DATASET, "splits": splits,
            "credential_mode": cred_mode,
            "note": "row counts are count signals, never coverage statements (LXXV clause 2)"}


def _hf_row_to_hit(row: Dict[str, Any], query: str, payload_sha: str,
                   credential_mode: str = HF_MODE_ANONYMOUS) -> PriorArtHit:
    """Map one datasets-server row to the unified PriorArtHit with LXXV custody."""
    rid = str(row.get("id") or "")
    text = str(row.get("text") or "")
    meta = row.get("metadata") or {}
    source_name = str(row.get("source") or "common-pile/uspto")
    pub_date = meta.get("publication_date") or row.get("created")
    # id shape measured: US-71623224-A
    m = re.match(r"^([A-Z]{2})-(\d+)-([A-Z]\d?)$", rid)
    patent_id = None
    if m:
        patent_id = f"{m.group(1)}{m.group(2)}{m.group(3)}"
    custody = make_custody(
        source="HF_USPTO_CORPUS",
        endpoint=f"{HF_DSER_BASE}/search|/rows",
        query=query,
        retrieved_at_utc=_now_utc(),
        publication_number=(f"{m.group(1)}{m.group(2)}" if m else rid or None),
        kind_code=(m.group(3) if m else None),
        publication_date=str(pub_date) if pub_date else None,
    )
    # LXXV clause 1 provenance extension (R504): the credential mode the
    # record was actually fetched under — AUTHENTICATED_HF_TOKEN or the
    # measured keyless fallback.
    custody["provenance"]["credential_mode"] = credential_mode
    custody["license"] = meta.get("license")  # measured per-record (CC BY 4.0 seen R499)
    return PriorArtHit(
        source_id="HF_USPTO_CORPUS",
        source_url=f"https://huggingface.co/datasets/{HF_USPTO_DATASET}",
        retrieved_at_utc=_now_utc(),
        query=query,
        raw_payload_sha256=payload_sha,
        title=(text[:120].strip() or rid),
        snippet=re.sub(r"\s+", " ", text[:300]).strip(),
        assignee_or_authors=[],
        publication_date=str(pub_date) if pub_date else None,
        patent_id=patent_id or rid,
        raw_metadata={
            "corpus_id": rid,
            "corpus_source": source_name,
            "license": meta.get("license"),
            "language": meta.get("language"),
            "added": row.get("added"),
            "created": row.get("created"),
            "custody_lxxv": custody,
        },
    )


def search_hf_uspto(query: str, num_results: int = 8) -> SourceQueryResult:
    """Full-text search the free USPTO corpus via HF datasets-server /search.

    Typed states per call (LXXV enforcement point 5). Zero hits with state OK
    is a true-zero FOR THIS CORPUS ONLY — never a patent-layer absence claim.
    """
    base = (f"{HF_DSER_BASE}/search?dataset={urllib.parse.quote(HF_USPTO_DATASET)}"
            f"&config={HF_USPTO_CONFIG}&split={HF_USPTO_SPLIT}"
            f"&query={urllib.parse.quote(query)}&offset=0&length={min(num_results, HF_ROWS_PAGE_MAX)}")
    auth_h, cred_mode = hf_auth_header()
    status, body, latency = _http_get(base, headers=auth_h, timeout=45)
    if status == 500:
        try:
            err = json.loads(body).get("error", "")
        except Exception:
            err = body.decode("utf-8", "replace")[:200]
        if "index is loading" in err:
            return SourceQueryResult(source_id="HF_USPTO_CORPUS", success=False,
                                     latency_ms=latency, error=f"INDEX_WARMING_TRANSIENT: {err}",
                                     error_code=status)
        return SourceQueryResult(source_id="HF_USPTO_CORPUS", success=False,
                                 latency_ms=latency, error=f"HTTP 500: {err}", error_code=status)
    if status == 429:
        return SourceQueryResult(source_id="HF_USPTO_CORPUS", success=False,
                                 latency_ms=latency, error="RATE_LIMITED", error_code=status)
    if status != 200:
        return SourceQueryResult(source_id="HF_USPTO_CORPUS", success=False,
                                 latency_ms=latency, error=f"HTTP {status}", error_code=status)
    try:
        js = json.loads(body)
    except Exception as e:
        return SourceQueryResult(source_id="HF_USPTO_CORPUS", success=False,
                                 latency_ms=latency, error=f"PARSE_ERROR: {e}")
    rows = js.get("rows") or []
    if rows and not isinstance(rows[0].get("row", None), dict):
        return SourceQueryResult(source_id="HF_USPTO_CORPUS", success=False,
                                 latency_ms=latency, error="SCHEMA_MISMATCH: rows[].row not an object")
    payload_sha = _sha256(body)
    hits = [_hf_row_to_hit(r.get("row", {}), query, payload_sha, cred_mode) for r in rows]
    return SourceQueryResult(source_id="HF_USPTO_CORPUS", success=True,
                             latency_ms=latency, hits=hits)


def fetch_hf_uspto_rows(offset: int = 0, length: int = 10) -> SourceQueryResult:
    """Deterministic corpus retrieval via datasets-server /rows.

    Measured R499: 200, fast, stable (the reliable Tier-3 retrieval path today;
    /search measured INDEX_WARMING_TRANSIENT across ~10 minutes of probes on
    the large text corpora — typed, retriable, never promoted to a coverage
    claim). Use for corpus-scale work (claim extraction substrate, the fabric
    build order #3); a page fetch is a page, never a search-coverage signal.
    """
    length = max(1, min(length, HF_ROWS_PAGE_MAX))
    url = (f"{HF_DSER_BASE}/rows?dataset={urllib.parse.quote(HF_USPTO_DATASET)}"
           f"&config={HF_USPTO_CONFIG}&split={HF_USPTO_SPLIT}&offset={offset}&length={length}")
    auth_h, cred_mode = hf_auth_header()
    status, body, latency = _http_get(url, headers=auth_h, timeout=45)
    if status != 200:
        return SourceQueryResult(source_id="HF_USPTO_CORPUS", success=False, latency_ms=latency,
                                 error=(f"HTTP {status}" if status > 0 else "TRANSPORT_ERROR"),
                                 error_code=(status if status > 0 else None))
    try:
        js = json.loads(body)
    except Exception as e:
        return SourceQueryResult(source_id="HF_USPTO_CORPUS", success=False, latency_ms=latency,
                                 error=f"PARSE_ERROR: {e}")
    rows = js.get("rows") or []
    payload_sha = _sha256(body)
    hits = [_hf_row_to_hit(r.get("row", {}), f"rows:{offset}+{length}", payload_sha, cred_mode) for r in rows]
    res = SourceQueryResult(source_id="HF_USPTO_CORPUS", success=True, latency_ms=latency, hits=hits)
    res.rate_limit_remaining = js.get("num_rows_total")  # carry the total as a count signal
    return res


# ----------------------- LEG B: EPO LINKED OPEN DATA -----------------------
# Identity + family + primary documents. Free, anonymous, SPARQL 1.1.
# Endpoint discovered R499: https://data.epo.org/linked-data/query
# (the R498-probed /linked-data/data/sparql URL is the query UI — the 406
# root cause; it is NOT the protocol endpoint).

EPO_LOD_SPARQL = "https://data.epo.org/linked-data/query"
EPO_LOD_PUB_URI = "http://data.epo.org/linked-data/data/publication/{cc}/{num}/{kind}/-"
PATENT_DEF = "http://data.epo.org/linked-data/def/patent/"

# typed states
EPO_STATE_OK = "OK"
EPO_STATE_NOT_IN_GRAPH = "NOT_IN_GRAPH"          # 0 bindings — a coverage state of THIS dataset, NEVER absence
EPO_STATE_QUERY_TIMEOUT = "QUERY_COST_TIMEOUT"   # endpoint read timeout (full-graph scans) — subject-anchored queries only
EPO_STATE_HTTP_ERROR = "HTTP_ERROR"
EPO_STATE_PARSE_ERROR = "PARSE_ERROR"
EPO_STATE_TRANSPORT_ERROR = "TRANSPORT_ERROR"


def epo_publication_uri(country: str, number: str, kind: str) -> str:
    """URI shape measured R499: .../publication/EP/0084638/A1/- (trailing dash required)."""
    return EPO_LOD_PUB_URI.format(cc=country.upper(), num=number, kind=kind.upper())


def _sparql(query: str, timeout: int = 45) -> Tuple[str, Any, int, str]:
    """Run one SPARQL SELECT. Returns (state, parsed_json_or_error, latency_ms, error)."""
    url = EPO_LOD_SPARQL + "?query=" + urllib.parse.quote(query)
    status, body, latency = _http_get(url, headers={"Accept": "application/sparql-results+json"},
                                      timeout=timeout)
    if status in (-1, -2):
        raw = body.decode("utf-8", "replace")
        if "timed out" in raw.lower() or "timeout" in raw.lower():
            return EPO_STATE_QUERY_TIMEOUT, None, latency, raw[:200]
        return EPO_STATE_TRANSPORT_ERROR, None, latency, raw[:200]
    if status != 200:
        return EPO_STATE_HTTP_ERROR, None, latency, f"HTTP {status}: {body[:200]!r}"
    try:
        return EPO_STATE_OK, json.loads(body), latency, ""
    except Exception as e:
        return EPO_STATE_PARSE_ERROR, None, latency, str(e)


def _bindings(js: Dict[str, Any]) -> List[Dict[str, str]]:
    out = []
    for b in js.get("results", {}).get("bindings", []):
        out.append({k: v.get("value", "") for k, v in b.items()})
    return out


def epo_lod_identity(country: str, number: str, kind: str) -> Dict[str, Any]:
    """Publication identity + custody. NOT_IN_GRAPH is a typed coverage state, never absence (LXXV.2)."""
    uri = epo_publication_uri(country, number, kind)
    q = f"SELECT ?p ?o WHERE {{ <{uri}> ?p ?o . }} LIMIT 200"
    state, js, latency, err = _sparql(q)
    base = {"source_id": "EPO_LINKED_OPEN_DATA", "uri": uri, "latency_ms": latency}
    if state != EPO_STATE_OK:
        base.update({"state": state, "error": err})
        return base
    binds = _bindings(js)
    if not binds:
        base.update({"state": EPO_STATE_NOT_IN_GRAPH,
                     "note": "0 bindings in THIS dataset — coverage state, never evidence of absence (Art. XXI.3 / LXXV clause 2)"})
        return base
    by_pred: Dict[str, List[str]] = {}
    for b in binds:
        p = b["p"]
        o = b.get("o", "")
        by_pred.setdefault(p, []).append(o)

    def vals(suffix: str) -> List[str]:
        return by_pred.get(PATENT_DEF + suffix, [])

    titles = [t for t in vals("titleOfInvention")]
    abstracts = [a for a in by_pred.get("http://purl.org/dc/terms/abstract", [])]
    label = (by_pred.get("http://www.w3.org/2000/01/rdf-schema#label") or [""])[0]
    applications = vals("application")
    priorities = vals("priority")
    citations = vals("citesPatentPublication")
    representations = vals("representation")
    pub_date = (vals("publicationDate") or [None])[0]
    pub_kind = (vals("publicationKind") or [""])[0].rsplit("_", 1)[-1] or None
    pub_authority = (vals("publicationAuthority") or [""])[0].rsplit("/", 1)[-1] or None
    custody = make_custody(
        source="EPO_LINKED_OPEN_DATA",
        endpoint=EPO_LOD_SPARQL,
        query=q,
        retrieved_at_utc=_now_utc(),
        publication_number=f"{country.upper()}{number}",
        kind_code=pub_kind,
        application_reference=(applications[0] if applications else None),
        publication_date=pub_date,
    )
    # family is a SEPARATE measured chain (epo_lod_family_for_publication);
    # this call declares the boundary explicitly — never silently incomplete,
    # never silently complete (LXXV clause 1).
    custody["family_relationship"]["family_basis"] = "NOT_MEASURED_THIS_CALL"
    base.update({
        "state": EPO_STATE_OK,
        "label": label,
        "publication_number": f"{country.upper()}{number}",
        "kind_code": pub_kind,
        "publication_authority": pub_authority,
        "publication_date": pub_date,
        "titles": titles,
        "abstracts": abstracts,
        "applications": applications,
        "priorities": priorities,
        "cites": citations,
        "citations_count_signal": len(citations),  # count signal only (XXI.1)
        "representations": representations,
        "custody_lxxv": custody,
        "custody_completeness": custody_completeness(custody),
    })
    return base


def epo_lod_family_for_publication(country: str, number: str, kind: str,
                                   max_members: int = 50) -> Dict[str, Any]:
    """Simple-family collapse: publication -> application -> family -> members.

    Measured chain (R499): familyMemberOf attaches to the APPLICATION
    resource; family -> patent:familyMember -> applications; application ->
    patent:publication -> publications. Subject-anchored only (query-cost bound).
    """
    pub_uri = epo_publication_uri(country, number, kind)
    # step 1: the publication's application(s)
    q1 = (f"PREFIX patent: <{PATENT_DEF}>\n"
          f"SELECT ?app WHERE {{ <{pub_uri}> patent:application ?app . }} LIMIT 10")
    state, js, latency, err = _sparql(q1)
    base = {"source_id": "EPO_LINKED_OPEN_DATA", "uri": pub_uri, "latency_ms": latency}
    if state != EPO_STATE_OK:
        base.update({"state": state, "error": err}); return base
    apps = [b["app"] for b in _bindings(js) if b.get("app")]
    if not apps:
        base.update({"state": EPO_STATE_NOT_IN_GRAPH,
                     "note": "no application triple in THIS dataset — coverage state, never absence"})
        return base
    # step 2: application -> simple family
    app = apps[0]
    q2 = (f"PREFIX patent: <{PATENT_DEF}>\n"
          f"SELECT ?fam WHERE {{ <{app}> patent:familyMemberOf ?fam . }} LIMIT 5")
    state, js, latency2, err = _sparql(q2)
    base["latency_ms"] += latency2
    if state != EPO_STATE_OK:
        base.update({"state": state, "error": err, "application": app}); return base
    fams = [b["fam"] for b in _bindings(js) if b.get("fam")]
    if not fams:
        base.update({"state": "OK", "application": app, "family_uri": None,
                     "family_basis": "NO_FAMILY_TRIPLE_IN_GRAPH",
                     "note": "the application is in-graph but no family triple exists here — typed, never absence"})
        return base
    fam = fams[0]
    # step 3: family -> member applications (+ their publications)
    q3 = (f"PREFIX patent: <{PATENT_DEF}>\n"
          f"SELECT ?app2 ?pub WHERE {{ <{fam}> patent:familyMember ?app2 . "
          f"OPTIONAL {{ ?app2 patent:publication ?pub . }} }} LIMIT {max_members * 3}")
    state, js, latency3, err = _sparql(q3)
    base["latency_ms"] += latency3
    if state != EPO_STATE_OK:
        base.update({"state": state, "error": err, "application": app, "family_uri": fam}); return base
    members: Dict[str, List[str]] = {}
    for b in _bindings(js):
        a2 = b.get("app2", "")
        if a2:
            members.setdefault(a2, [])
            if b.get("pub"):
                members[a2].append(b["pub"])
    custody = make_custody(
        source="EPO_LINKED_OPEN_DATA",
        endpoint=EPO_LOD_SPARQL,
        query=q3,
        retrieved_at_utc=_now_utc(),
        publication_number=f"{country.upper()}{number}",
        application_reference=app,
        family_uri=fam,
        family_members=list(members.keys()),
    )
    base.update({
        "state": "OK",
        "application": app,
        "family_uri": fam,
        "family_basis": "SIMPLE_FAMILY",
        "member_applications": list(members.keys()),
        "member_publications": {a: p for a, p in members.items()},
        "family_size_count_signal": len(members),  # count signal only (XXI.1)
        "custody_lxxv": custody,
        "custody_completeness": custody_completeness(custody),
    })
    return base


def epo_lod_fetch_document(representation_url: str, max_bytes: int = 2_000_000) -> Dict[str, Any]:
    """Fetch a Tier-1 primary document (XML/PDF) from its representation URL.

    Measured R499: XML (official ep-patent-document DTD) and PDF both 200,
    anonymous. Returns sha256 + content-type + size for byte binding (Art. II/III).
    """
    if not representation_url.startswith("https://data.epo.org/"):
        return {"state": "REJECTED_NON_EPO_ORIGIN", "url": representation_url,
                "note": "primary-document fetch is restricted to EPO origin URLs"}
    status, body, latency = _http_get(representation_url, headers={"Accept": "*/*"},
                                      timeout=60, max_bytes=max_bytes + 1)
    if status != 200:
        return {"state": EPO_STATE_HTTP_ERROR if status > 0 else EPO_STATE_TRANSPORT_ERROR,
                "http_status": status, "latency_ms": latency}
    truncated = len(body) > max_bytes
    return {
        "state": "OK",
        "url": representation_url,
        "http_status": status,
        "content_type": "application/xml" if representation_url.endswith(".xml") else (
            "application/pdf" if representation_url.endswith(".pdf") else None),
        "size_bytes": len(body),
        "truncated_at_max_bytes": truncated,
        "sha256": _sha256(body),
        "retrieved_at_utc": _now_utc(),
        "source": "EPO_LINKED_OPEN_DATA",
    }


def get_free_source_status() -> Dict[str, Dict[str, Any]]:
    """Per-source status for the free legs (typed states, per-call basis)."""
    return {
        "HF_USPTO_CORPUS": {
            "transport_version": TRANSPORT_VERSION,
            "dataset": HF_USPTO_DATASET,
            "tier": 3,
            "free": True,
            # LXXV AUTHENTICATED property (re-typed MEASURED at R504): the
            # transport attaches the HF_TOKEN Bearer header whenever the
            # environment holds it (the Space carries it as a standing
            # secret) and degrades to the measured keyless mode otherwise;
            # never a failure. Both modes measured live on /splits, /rows
            # and the Hub catalog (R504/R504_HF_AUTH_PROBE.json).
            "authenticated": True,
            "auth_env": HF_AUTH_ENV,
            "auth_mode": "attach-when-present (degrades to measured keyless; never fails on a missing token)",
            "anonymous_fallback": True,
            "metered": False,
            "measured_round": "R499 (keyless) + R504 (both modes)",
        },
        "EPO_LINKED_OPEN_DATA": {
            "transport_version": TRANSPORT_VERSION,
            "sparql_endpoint": EPO_LOD_SPARQL,
            "tier": 1,  # EPO's own open data service: primary-origin identity + documents
            "free": True, "authenticated": False, "metered": False,
            "query_cost_bound": "subject-anchored only (full-graph scans measured to time out R499)",
            "coverage_note": "EP-centric identity; US/worldwide partial — NOT_IN_GRAPH is a coverage state, never absence",
            "measured_round": "R499",
        },
    }

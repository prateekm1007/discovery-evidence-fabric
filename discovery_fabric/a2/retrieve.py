"""A2 retrieval — multi-source scholarly lanes → EvidenceItem.

HISTORY
  2026-08-30 (R375) constitutional repair: candidate 11 retrieved ZERO
  evidence because the MAUDE problem-term phrase contains literal
  'or'/'and'/'(s)' which EuropePMC parses as boolean operators. Two Art.
  XXI defects were fixed here: (1) Art. XXI.3 — ANY provider exception
  previously swallowed into `return []` (provider outage masquerading as
  "zero evidence"); provider failure now RAISES and is never recorded as
  absence. (2) Art. XXI.2 — zero results for ONE query string is not
  evidence of absence; a reduced-fallback + core-term query ladder runs,
  with every query recorded in each item's provenance.

  2026-09-03 (R401 step 1) — multi-source lanes, driven by MEASURED
  cross-check (bench/results/db_ab.json, 8 problems × 6 sources, live):
    - OpenAlex   8/8 domains, ~1.7s, cross-domain, abstracts via
                 inverted index  → PRIMARY lane (always queried)
    - arXiv      8/8, reliable physics/ENG preprints → always queried
    - EuropePMC  EMPTY on 4/8 non-biomedical problems (measured) →
                 BIOMEDICAL-ROUTED lane only (also saves the 2-4s of
                 guaranteed-empty calls on engineering domains)
    - Crossref   fastest (~1.3s), metadata-strong → top-up lane when the
                 merge is thin (< MIN_MERGE items)
    - OSTI       broken (measured twice: R397 + R401) → not wired here
    - S2         429 without key → not wired (key request is an open
                 R401 action; wiring slot below stays honest about it)
  Cross-source redundancy measured at 96.7% on the R401 fixture set →
  spine-dedup (first-60-normalized-chars, identical definition to the
  benchmark harness) runs at merge time. Every per-source outcome is
  classified through the ONE connector failure-semantics contract
  (connectors/connector_states.py — SUCCESS / EMPTY_RESULT / TIMEOUT /
  RATE_LIMITED / PROVIDER_ERROR / PARSE_ERROR / UNAVAILABLE /
  NOT_ATTEMPTED). An outage on one lane NEVER blocks the others, and a
  total zero with ANY outage state raises (UNKNOWN, never absence); a
  total zero with all-EMPTY states after the ladder is a REAL absence
  (EMPTY_RESULT is the only absence-capable state).
"""
from __future__ import annotations
import json, re, hashlib, ssl, time, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from discovery_fabric.connectors.connector_states import (
    classify_exception, outcome,
)
from discovery_fabric.connectors.openalex.mapper import (
    _reconstruct_abstract as _openalex_abstract,
)

_SSL = ssl.create_default_context()
_SSL.check_hostname = False
_SSL.verify_mode = ssl.CERT_NONE

_CONTACT = "discovery-fabric@example.org"  # polite-pool identity (OpenAlex/Crossref)

# Merge policy (R401 measurement-backed)
PER_SOURCE = 5            # per-source page size (EuropePMC historic value)
MERGE_CAP = 12            # max merged items handed to classify
MIN_MERGE = 3             # below this, the Crossref top-up lane fires

# Module-level report of the last retrieve() call — per-source connector
# outcomes + queries (observability + test surface; NEVER used to fake a
# scientific result, only to make infrastructure state inspectable).
LAST_RETRIEVAL_REPORT: dict = {}


class SearchProviderFailure(RuntimeError):
    """Transport/provider error — NEVER evidence of absence (Art. XXI.3)."""


def sanitize_query(text: str) -> str:
    """Strip boolean-operator words and (s)-style suffix fragments that
    EuropePMC would parse as operators. Vocabulary hygiene only — the
    sanitized query is recorded in the provenance of every item it
    retrieves, never silently substituted for the original."""
    t = re.sub(r"\(s\)", "", text or "")
    t = re.sub(r"\b(?:or|and|not)\b", " ", t, flags=re.I)
    t = re.sub(r"[()]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _item(source: str, source_id: str, uri: str, title: str, abstract: str,
          doi, pub_date, method: str, query: str) -> dict:
    """Build ONE a2 EvidenceItem (schema identical to the R375 EuropePMC
    item — classify/synthesize/verify are untouched by R401 step 1)."""
    core = {"source_id": source_id, "title": title, "doi": doi or "",
            "pub_date": pub_date or ""}
    content_hash = hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()
    return {
        "id": source_id, "source_type": "scientific_paper", "source": source,
        "source_id": source_id, "source_uri": uri,
        "title": title or "", "abstract": (abstract or "")[:2000],
        "doi": doi or None, "publication_date": pub_date or None,
        "retrieval_timestamp": _now(), "retrieval_method": method,
        "content_hash": content_hash,
        "provenance": {"provider": source, "retrieved_at": _now(),
                       "query_or_method": query, "api_version": "rest",
                       "connector_state": "SUCCESS"},
        "epistemic_state": "OBSERVED",
    }


def _get(url: str, timeout: int = 20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "A2-Discovery/1.0"})
    resp = urllib.request.urlopen(req, timeout=timeout, context=_SSL)
    return resp.read()


# ---------------------------------------------------------------- OpenAlex
def search_openalex(query: str, per_page: int = PER_SOURCE) -> list[dict]:
    """PRIMARY lane — cross-domain works with reconstructed abstracts."""
    try:
        url = ("https://api.openalex.org/works?search="
               + urllib.parse.quote(query)
               + f"&per-page={per_page}&mailto={_CONTACT}")
        data = json.loads(_get(url))
        items = []
        for w in data.get("results", []):
            abstract = _openalex_abstract(w.get("abstract_inverted_index")) or ""
            if len(abstract) < 50:
                continue  # same evidence-quality bar as the R375 adapter
            oid = (w.get("id") or "").rsplit("/", 1)[-1] or w.get("doi") or ""
            items.append(_item(
                "OpenAlex", f"openalex:{oid}", w.get("id") or "",
                w.get("display_name") or w.get("title") or "", abstract,
                w.get("doi"), str(w.get("publication_date") or ""),
                "openalex_api", query))
        return items
    except Exception as exc:
        raise SearchProviderFailure(
            f"OpenAlex transport/error (NOT absence): "
            f"{type(exc).__name__}: {exc}") from exc


# ------------------------------------------------------------------- arXiv
def search_arxiv(query: str, per_page: int = PER_SOURCE) -> list[dict]:
    """Engineering/physics preprint lane (Atom API)."""
    try:
        url = ("http://export.arxiv.org/api/query?search_query=all:"
               + urllib.parse.quote(query)
               + f"&start=0&max_results={per_page}")
        root = ET.fromstring(_get(url))
        ns = {"a": "http://www.w3.org/2005/Atom",
              "ax": "http://arxiv.org/schemas/atom"}
        items = []
        for e in root.findall("a:entry", ns):
            abstract = re.sub(r"\s+", " ", e.findtext("a:summary", "", ns) or "").strip()
            if len(abstract) < 50:
                continue
            aid = (e.findtext("a:id", "", ns) or "").rsplit("/", 1)[-1]
            doi = e.findtext("ax:doi", None, ns)
            items.append(_item(
                "arXiv", f"arxiv:{aid}", e.findtext("a:id", "", ns) or "",
                re.sub(r"\s+", " ", e.findtext("a:title", "", ns) or "").strip(),
                abstract, doi,
                (e.findtext("a:published", "", ns) or "")[:10],
                "arxiv_atom_api", query))
        return items
    except Exception as exc:
        raise SearchProviderFailure(
            f"arXiv transport/error (NOT absence): "
            f"{type(exc).__name__}: {exc}") from exc


# ---------------------------------------------------------------- Crossref
def search_crossref(query: str, per_page: int = PER_SOURCE) -> list[dict]:
    """Top-up lane — fastest provider, metadata-strong, abstracts sparse."""
    try:
        url = ("https://api.crossref.org/works?query="
               + urllib.parse.quote(query)
               + f"&rows={per_page}&mailto={_CONTACT}")
        data = json.loads(_get(url))
        items = []
        for m in data.get("message", {}).get("items", []):
            title = (m.get("title") or [""])[0]
            abstract = re.sub(r"<[^>]+>", " ", m.get("abstract", "") or "")
            abstract = re.sub(r"\s+", " ", abstract).strip()
            if len(abstract) < 50:
                continue  # no-abstract records add merge noise, not evidence
            doi = m.get("DOI", "")
            date = m.get("issued", {}).get("date-parts", [[None]])[0]
            pub = "-".join(str(x) for x in date) if date and date[0] else ""
            items.append(_item(
                "Crossref", f"crossref:{doi}",
                f"https://doi.org/{doi}" if doi else "", title, abstract,
                doi, pub, "crossref_api", query))
        return items
    except Exception as exc:
        raise SearchProviderFailure(
            f"Crossref transport/error (NOT absence): "
            f"{type(exc).__name__}: {exc}") from exc


# --------------------------------------------------------------- EuropePMC
def search_europe_pmc(query: str, per_page: int = PER_SOURCE) -> list[dict]:
    try:
        encoded = urllib.parse.quote(query)
        url = (f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={encoded}"
               f"&format=json&pageSize={per_page}&resultType=core")
        req = urllib.request.Request(url, headers={"User-Agent": "A2-Discovery/1.0"})
        resp = urllib.request.urlopen(req, timeout=20, context=_SSL)
        data = json.loads(resp.read())
        items = []
        now = _now()
        for r in data.get("resultList", {}).get("result", []):
            abstract = re.sub(r"<[^>]+>", " ", r.get("abstractText", "") or "")
            abstract = re.sub(r"\s+", " ", abstract).strip()
            if len(abstract) < 50: continue
            source_id = f"europepmc:{r.get('id', r.get('pmid', ''))}"
            core = {"source_id": source_id, "title": r.get("title", ""), "doi": r.get("doi", ""), "pub_date": r.get("firstPublicationDate", "")}
            content_hash = hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()
            items.append({
                "id": source_id, "source_type": "scientific_paper", "source": "EuropePMC",
                "source_id": source_id, "source_uri": f"https://europepmc.org/article/{r.get('id', '')}",
                "title": r.get("title", "") or "", "abstract": abstract[:2000],
                "doi": r.get("doi", "") or None, "publication_date": r.get("firstPublicationDate", "") or None,
                "retrieval_timestamp": now, "retrieval_method": "europepmc_api", "content_hash": content_hash,
                "provenance": {"provider": "EuropePMC", "retrieved_at": now, "query_or_method": query, "api_version": "rest", "connector_state": "SUCCESS"},
                "epistemic_state": "OBSERVED",
            })
        return items
    except Exception as exc:
        # Art. XXI.3: provider failure is NEVER "zero results". Raise so
        # the RETRIEVE stage records an explicit infrastructure failure
        # (rerunnable), instead of fabricating absence.
        raise SearchProviderFailure(
            f"EuropePMC transport/error (NOT absence): "
            f"{type(exc).__name__}: {exc}") from exc


# ------------------------------------------------------------- merge/dedup
def _norm_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (title or "").lower())


def spine_dedup(items: list[dict]) -> list[dict]:
    """Cross-source dedup keeping the RICHER record (longer abstract).

    R401 Phase-5 adversarial measurement (bench/results/dedup_adversarial.json):
    head-60 spine keys FALSE-MERGE 50% of long-shared-prefix title pairs and
    FALSE-SPLIT 50% of prefixed duplicates; guarded containment (shorter
    normalized title is a substring of the longer, len>=20, ratio>=0.8)
    scores 16/16 on the adjudicated fixture (ratio-guarded substring 15/16;
    substring-OR-head60 11/16 - the OR re-imports prefix collisions; the
    fixture is 16 adjudicated pairs, production merge rates must be
    re-measured on live pulls). Title
    dedup is INGEST HYGIENE ONLY — mechanism-level distinctness is the
    structural dedup in discovery_fabric/mechanism_space (Phase 10)."""
    kept: list[dict] = []
    for it in items:
        nt = _norm_title(it.get("title", ""))
        if not nt:
            continue
        dup_of = None
        for k in kept:
            ko = _norm_title(k.get("title", ""))
            lo, hi = (nt, ko) if len(nt) <= len(ko) else (ko, nt)
            if lo == hi or (len(lo) >= 20 and (hi.startswith(lo) or hi.endswith(lo))):
                dup_of = k
                break
        if dup_of is None:
            kept.append(it)
        elif len(it.get("abstract", "")) > len(dup_of.get("abstract", "")):
            kept[kept.index(dup_of)] = it  # richer record wins the merge
    return kept


_BIOMED_KEYWORDS = (
    "dialysis", "catheter", "pacemaker", "stent", "graft", "infusion",
    "insulin", "patient", "clinical", "medical", "biologic", "hemolog",
    "hemodial", "vascular", "endovascular", "wound", "drug", "glucose",
    "sepsis", "thrombosis", "embol", "oncolog", "tumor", "immune",
)


def _is_biomedical(problem: dict) -> bool:
    """Lane router: explicit domain hint wins; otherwise keyword heuristic
    on device + failure_mode text. Non-biomedical problems skip EuropePMC
    (measured EMPTY on 4/8 R401 fixture domains)."""
    if (problem.get("domain") or "").lower() in ("biomedical", "medical", "biomed"):
        return True
    hay = f"{problem.get('device', '')} {problem.get('failure_mode', '')}".lower()
    return any(k in hay for k in _BIOMED_KEYWORDS)


def _search_lane(lane_name: str, fn, query: str) -> tuple[list[dict], dict]:
    """Run ONE provider call; convert failure into a recorded connector
    outcome (UNKNOWN — never absence) without blocking the other lanes."""
    try:
        items = fn(query)
        state = "SUCCESS" if items else "EMPTY_RESULT"
        return items, outcome(state, lane_name, f"query={query!r}")
    except SearchProviderFailure as exc:
        cause = exc.__cause__ or exc
        state = classify_exception(cause)
        return [], outcome(state, lane_name,
                           f"{type(cause).__name__}: {cause}"[:200])


def retrieve(problem: dict) -> list[dict]:
    fm = problem.get("failure_mode", "MECHANICAL_FAILURE")
    device = problem.get("device", "")
    primary = f"{device} {fm.lower().replace('_', ' ')} mechanism".strip()
    biomed = _is_biomedical(problem)
    lanes_label = "OpenAlex+arXiv" + ("+EuropePMC" if biomed
                                      else " (EuropePMC skipped: non-biomedical)")
    print(f"  [retrieve] query: {primary} (lanes: {lanes_label}+Crossref-topup)")

    queries = [primary]
    # Reduced-fallback + core-term ladder strings (R375/R377 discipline,
    # unchanged — one reduced fallback, then core terms).
    lead = sanitize_query(fm.lower().replace("_", " ")).split()
    fallback = " ".join(x for x in (device, lead[0] if lead else "", "mechanism") if x)
    core = " ".join(sanitize_query(
        f"{device} {fm.lower().replace('_', ' ')}").split()[:4])

    lanes = [("openalex", search_openalex), ("arxiv", search_arxiv)]
    if biomed:
        lanes.append(("europepmc", search_europe_pmc))

    outcomes, merged = [], []
    ladder = [primary]
    if fallback and fallback != primary:
        ladder.append(fallback)
    if core and core not in ladder:
        ladder.append(core)

    for qi, q in enumerate(ladder):
        if q not in queries:
            queries.append(q)
        for name, fn in lanes:
            items, oc = _search_lane(name, fn, q)
            outcomes.append(oc)
            merged.extend(items)
            if name == "europepmc" and qi < len(ladder) - 1 and items:
                time.sleep(1.0)  # EuropePMC courtesy between ladder steps
        merged = spine_dedup(merged)
        if merged:
            break  # Art. XXI.2: ladder stops at the first producing query
        print(f"  [retrieve] ladder step {qi + 1} zero — escalating")

    # Crossref top-up only when the merge is thin (rate-budget respect).
    if len(spine_dedup(merged)) < MIN_MERGE:
        items, oc = _search_lane("crossref", search_crossref, primary)
        outcomes.append(oc)
        merged.extend(items)
        merged = spine_dedup(merged)

    merged = spine_dedup(merged)[:MERGE_CAP]

    outage = [o for o in outcomes if o["connector_state"] not in
              ("SUCCESS", "EMPTY_RESULT")]
    LAST_RETRIEVAL_REPORT.clear()
    LAST_RETRIEVAL_REPORT.update({
        "queries": list(queries), "outcomes": outcomes,
        "biomedical": biomed, "merged": len(merged),
    })

    if not merged:
        if outage:
            # Art. XXI.3: at least one lane is UNKNOWN → the total is
            # UNKNOWN, never absence. Raise (rerunnable stage failure).
            states = ", ".join(f"{o['provider']}={o['connector_state']}"
                               for o in outage)
            raise SearchProviderFailure(
                f"retrieval total-zero with outage lanes (NOT absence): {states}")
        # All lanes EMPTY_RESULT after the full ladder → REAL absence for
        # the queried universes (EMPTY_RESULT is the only absence-capable
        # state). Honest zero, returned as zero.
        print(f"  [retrieve] found 0 evidence items after full ladder "
              f"(all lanes EMPTY_RESULT — honest absence)")
        return merged

    by_source: dict[str, int] = {}
    for it in merged:
        by_source[it["source"]] = by_source.get(it["source"], 0) + 1
    print(f"  [retrieve] found {len(merged)} evidence items "
          f"({', '.join(f'{k}={v}' for k, v in by_source.items())}; "
          f"queries tried: {len(queries)})")
    return merged

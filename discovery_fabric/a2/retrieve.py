"""A2 retrieval — Europe PMC search → EvidenceItem.

2026-08-30 (R375) constitutional repair, driven by a live campaign finding:
candidate 11 ('venous filter / coagulation in device or device ingredient(s)
or component(s)') retrieved ZERO evidence because the MAUDE problem-term
phrase contains the literal words 'or'/'and' and '(s)' suffixes, which
EuropePMC parses as boolean operators with dangling operands (verified
live: the poisoned query returns hitCount 0 while 'venous filter
coagulation mechanism' returns 4580). Two Art. XXI defects existed here:

  (1) Art. XXI.3 violation: ANY provider exception was swallowed into
      `return []` — a provider timeout/error masqueraded as "zero
      evidence". Provider failure now RAISES (explicit stage failure,
      rerunnable infrastructure state) and is never recorded as absence.
  (2) Art. XXI.2 discipline: zero results for ONE query string is not
      evidence of absence. The adapter now (a) sanitizes boolean-poisoned
      vocabulary (MAUDE terms are vocabulary, not boolean expressions —
      recorded in the query log), and (b) if the primary query returns a
      true zero, runs ONE reduced fallback query (device + leading
      failure-mode keyword). Both queries travel in every item's
      provenance; nothing is silently substituted.
"""
from __future__ import annotations
import json, re, hashlib, ssl, time, urllib.request, urllib.parse
from datetime import datetime, timezone

_SSL = ssl.create_default_context()
_SSL.check_hostname = False
_SSL.verify_mode = ssl.CERT_NONE


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


def search_europe_pmc(query: str, per_page: int = 5) -> list[dict]:
    try:
        encoded = urllib.parse.quote(query)
        url = (f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={encoded}"
               f"&format=json&pageSize={per_page}&resultType=core")
        req = urllib.request.Request(url, headers={"User-Agent": "A2-Discovery/1.0"})
        resp = urllib.request.urlopen(req, timeout=20, context=_SSL)
        data = json.loads(resp.read())
        items = []
        now = datetime.now(timezone.utc).isoformat()
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
                "provenance": {"provider": "EuropePMC", "retrieved_at": now, "query_or_method": query, "api_version": "rest"},
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


def retrieve(problem: dict) -> list[dict]:
    fm = problem.get("failure_mode", "MECHANICAL_FAILURE")
    device = problem.get("device", "")
    primary = f"{device} {fm.lower().replace('_', ' ')} mechanism".strip()
    print(f"  [retrieve] query: {primary}")
    items = search_europe_pmc(primary, per_page=5)
    queries = [primary]
    if not items:
        # Art. XXI.2: zero hits on ONE query string is not absence. ONE
        # reduced fallback: device + leading failure-mode keyword, with
        # boolean-poisoned vocabulary sanitized. Recorded per item.
        lead = sanitize_query(fm.lower().replace("_", " ")).split()
        lead_kw = lead[0] if lead else ""
        fallback = " ".join(x for x in (device, lead_kw, "mechanism") if x)
        if fallback and fallback != primary:
            print(f"  [retrieve] primary query returned 0 — fallback: "
                  f"{fallback}")
            time.sleep(1.0)
            items = search_europe_pmc(fallback, per_page=5)
            queries.append(fallback)
    if not items:
        # R377 measured defect (stress test m7, titanium grinding): for
        # NON-MEDICAL engineering domains the device string itself can
        # be long and specific enough to zero-hit EuropePMC even after
        # the fallback ('vitrified-bond aluminum-oxide grinding wheel
        # for titanium alloy parts wheel mechanism' -> 0) while a
        # CORE-TERM query returns real domain literature ('titanium
        # grinding wheel loading' -> 2, 'grinding titanium alloy' -> 3).
        # A third escalation on the top content terms of device+failure
        # is search-BREADTH expansion (more evidence sought, Art.
        # XXI.2 discipline intact: every query recorded, absence never
        # claimed without exhausting the ladder).
        core = " ".join(sanitize_query(
            f"{device} {fm.lower().replace('_', ' ')}").split()[:4])
        if core and core not in queries:
            print(f"  [retrieve] fallback returned 0 — core-term query: "
                  f"{core}")
            time.sleep(1.0)
            items = search_europe_pmc(core, per_page=5)
            queries.append(core)
    time.sleep(1.0)
    # ---- R401-WC2 (CEO directive 5): the OpenAlex lane in the CANONICAL
    # primary path. EuropePMC stays the primary lane; OpenAlex is a
    # SECOND discovery lane queried with its own derived query, merged
    # with cross-source dedup by DOI/title. Provenance is preserved by
    # construction: the lane goes through the source-registry connector
    # (custody log entry with retrieval_role=DISCOVERY; every item
    # carries the registry's own provenance record). A lane failure
    # (e.g. the 2025+ credit-budget 429 measured live) is an HONEST
    # PARTIAL state recorded in RETRIEVAL_LANES and returned with the
    # evidence — never absence, never a raised stage failure when the
    # other lane produced evidence (Art. XXI.3 discipline is unchanged
    # for the primary lane: if EuropePMC itself fails, retrieve() still
    # raises).
    lanes: dict = {"europepmc": {"queries": queries,
                                 "n_items": len(items), "status": "OK"}}
    openalex_items = _search_openalex_lane(device, fm, lanes)
    items, dedup = _merge_lanes(items, openalex_items)
    if dedup:
        lanes["cross_source_dedup"] = dedup
    print(f"  [retrieve] found {len(items)} evidence items "
          f"(queries tried: {len(queries)}; lanes: "
          f"{ {k: v['n_items'] for k, v in lanes.items() if 'n_items' in v} })")
    RETRIEVAL_LANES.clear()
    RETRIEVAL_LANES.update(lanes)
    return items


# The lane-state record for the LAST retrieve() call (the conductor
# attaches it to the RETRIEVE envelope — machine-visible lane honesty).
RETRIEVAL_LANES: dict = {}


def _search_openalex_lane(device: str, fm: str,
                          lanes: dict) -> list[dict]:
    """One OpenAlex query (device + failure-mode terms; the primary
    'mechanism' suffix is deliberately dropped — keyword_form and the
    collision-measured 'mechanism' meta-word defect). Failures return
    [] with the lane state recorded (never raised: a partial-lane
    failure is not a stage failure when the primary lane succeeded)."""
    from discovery_fabric.source_registry.query_relevance import \
        keyword_form
    q = keyword_form(f"{device} {fm.lower().replace('_', ' ')}")
    if not q:
        lanes["openalex"] = {"queries": [], "n_items": 0,
                             "status": "NO_QUERY_FORMED"}
        return []
    try:
        from discovery_fabric.source_registry.connectors.scientific \
            import OpenAlexConnector
        r = OpenAlexConnector().search(q, retrieval_role="DISCOVERY")
    except Exception as exc:  # noqa: BLE001 — honest lane state
        lanes["openalex"] = {"queries": [q], "n_items": 0,
                             "status": "SEARCH_FAILED",
                             "error": f"{type(exc).__name__}: {exc}"[:160]}
        return []
    items = []
    for rec in r.records:
        n = rec.normalized or {}
        abstract = n.get("abstract") or ""
        if not abstract or len(str(abstract)) < 200:
            continue
        items.append({
            "id": f"openalex:{rec.record_id}",
            "source_type": "scientific_paper",
            "source": "OpenAlex",
            "source_id": f"openalex:{rec.record_id}",
            "source_uri": rec.uri,
            "title": rec.title or "",
            "abstract": str(abstract)[:2400],
            "doi": n.get("doi") or None,
            "publication_date": None,
            "retrieval_timestamp": rec.retrieved_at,
            "retrieval_method": "source_registry_openalex",
            "content_hash": rec.raw_payload_sha256 or "",
            "provenance": {"provider": "OpenAlex",
                           "retrieved_at": rec.retrieved_at,
                           "query_or_method": q,
                           "retrieval_role": "DISCOVERY",
                           "registry_provenance": rec.provenance or {}},
            "epistemic_state": "OBSERVED",
            "limitations": [
                "Abstracts are inverted-index reconstructions",
                "Credit-budget model: 429 'Insufficient budget' "
                "measured this session — availability resets per "
                "provider policy"],
        })
    lanes["openalex"] = {"queries": [q], "n_items": len(items),
                         "status": r.status}
    if r.error:
        lanes["openalex"]["error"] = str(r.error)[:160]
    return items


def _merge_lanes(primary: list[dict],
                secondary: list[dict]) -> tuple[list[dict], list[dict]]:
    """Merge two lanes' items with cross-source dedup: same DOI or a
    ~normalized title match means the same paper — the PRIMARY lane's
    item wins (the record's abstract is already provenance-bound);
    the dedup record is RETURNED (recorded in the lane states, never
    silently dropped). Returns (merged, dedup_record)."""
    def _title_key(t: str) -> str:
        return " ".join(re.findall(r"[a-z0-9]+", (t or "").lower()))[:80]
    seen_doi = {i.get("doi") for i in primary if i.get("doi")}
    seen_title = {_title_key(i.get("title", "")) for i in primary}
    out = list(primary)
    dedup = []
    for it in secondary:
        doi = it.get("doi")
        tk = _title_key(it.get("title", ""))
        if (doi and doi in seen_doi) or (tk and tk in seen_title):
            dedup.append({"deduped_id": it.get("id"),
                          "basis": "doi" if doi and doi in seen_doi
                          else "title"})
            continue
        out.append(it)
        if doi:
            seen_doi.add(doi)
        if tk:
            seen_title.add(tk)
    return out, dedup

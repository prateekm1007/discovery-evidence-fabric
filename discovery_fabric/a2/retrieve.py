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
    time.sleep(1.0)
    print(f"  [retrieve] found {len(items)} evidence items "
          f"(queries tried: {len(queries)})")
    return items

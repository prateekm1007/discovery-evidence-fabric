#!/usr/bin/env python3
"""R499 free-source probe set — the operator directive 'use huggingface and other free sources'.

Design (per Art. XXI / LXXV):
- public endpoints only; registration-gated sources are typed by their measured
  access boundary (401/403 shape), never probed around it;
- every probe records url / at_utc / http_status / seconds / body_len / parse;
- a 406 from R498 (EPO LOD) is retried with the SPARQL 1.1 protocol's proper
  content negotiation (Accept: application/sparql-results+json) — the R498
  probe used output=json as a query parameter, which the endpoint rejected;
- HF datasets-server (the actual retrieval path for Tier-3 corpora) is probed
  for the first time: /splits, /rows, /search on common-pile/uspto.

Output: R499/R499_FREE_SOURCE_PROBES.json
"""
import json
import os
import ssl
import time
import urllib.request
import urllib.error
import urllib.parse

SSL = ssl.create_default_context()
SSL.check_hostname = False
SSL.verify_mode = ssl.CERT_NONE
UA = "Mozilla/5.0 (X11; Linux x_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "R499", "R499_FREE_SOURCE_PROBES.json")


def http(method, url, headers=None, payload=None, timeout=25):
    h = {"User-Agent": UA, "Accept": "application/json"}
    if headers:
        h.update(headers)
    data = payload.encode() if isinstance(payload, str) else payload
    req = urllib.request.Request(url, headers=h, data=data, method=method)
    t0 = time.time()
    try:
        resp = urllib.request.urlopen(req, timeout=timeout, context=SSL)
        body = resp.read()
        return resp.status, body, round(time.time() - t0, 2), None
    except urllib.error.HTTPError as e:
        try:
            body = e.read()
        except Exception:
            body = b""
        return e.code, body, round(time.time() - t0, 2), str(e)
    except Exception as e:
        return None, b"", round(time.time() - t0, 2), f"{type(e).__name__}: {e}"


def probe(probes, name, method, url, headers=None, payload=None, excerpt_fn=None):
    status, body, secs, err = http(method, url, headers=headers, payload=payload)
    rec = {"probe": name, "url": url if "patentbear" not in url else url.split("?")[0],
           "at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "http_status": status, "seconds": secs, "body_len": len(body)}
    if err and status is None:
        rec["error"] = err
    try:
        js = json.loads(body)
        rec["parse"] = "OK"
        if excerpt_fn:
            rec["payload_excerpt"] = excerpt_fn(js)
    except Exception as ex:
        if status is not None:
            rec["parse"] = f"NOT_JSON ({ex})" if body else "EMPTY_BODY"
            if body:
                rec["body_excerpt"] = body[:400].decode("utf-8", "replace")
    probes.append(rec)
    print(f"[{status}] {name} ({secs}s, {len(body)}B)" + (f" ERR={err}" if status is None else ""))
    return status, body


def main():
    probes = []

    # ---- 1. HuggingFace datasets index (R498 measured LIVE_200; stability re-probe) ----
    probe(probes, "hf_datasets_index_stability",
          "GET", "https://huggingface.co/api/datasets?search=patent&limit=5",
          excerpt_fn=lambda js: {"first_ids": [d.get("id") for d in js[:5]], "len": len(js)})

    # ---- 2. HF datasets-server: the retrieval path (FIRST TIME MEASURED) ----
    probe(probes, "hf_dser_splits_common_pile_uspto",
          "GET", "https://datasets-server.huggingface.co/splits?dataset=common-pile/uspto",
          excerpt_fn=lambda js: {"splits": [{"config": s.get("config"), "split": s.get("split")} for s in js.get("splits", [])][:10]})

    # rows probe (config/split discovered above; try default/train first)
    status, body = probe(probes, "hf_dser_rows_common_pile_uspto",
                         "GET", "https://datasets-server.huggingface.co/rows?dataset=common-pile/uspto&config=default&split=train&offset=0&length=2")
    splits_info = None
    if status == 200:
        try:
            splits_info = json.loads(body)
        except Exception:
            pass
    if status != 200:
        # discover real config/split names from the splits endpoint
        st2, b2 = http("GET", "https://datasets-server.huggingface.co/splits?dataset=common-pile/uspto")
        if st2 == 200:
            try:
                splits_info = json.loads(b2)
            except Exception:
                pass
    if splits_info:
        sp = (splits_info.get("splits") or [])
        if sp:
            cfg, spl = sp[0].get("config"), sp[0].get("split")
            probe(probes, "hf_dser_rows_common_pile_uspto_discovered",
                  "GET", f"https://datasets-server.huggingface.co/rows?dataset=common-pile/uspto&config={urllib.parse.quote(str(cfg))}&split={urllib.parse.quote(str(spl))}&offset=0&length=2",
                  excerpt_fn=lambda js: {"config_columns": [c.get("name") for c in js.get("features", [])],
                                          "first_row_keys": list((js.get("rows") or [{}])[0].get("row", {}).keys()) if js.get("rows") else [],
                                          "num_rows_total": js.get("num_rows_total")})

    # full-text search probe on the discovered config/split
    if splits_info:
        sp = (splits_info.get("splits") or [])
        if sp:
            cfg, spl = sp[0].get("config"), sp[0].get("split")
            q = "ballast water treatment"
            probe(probes, "hf_dser_search_common_pile_uspto",
                  "GET", f"https://datasets-server.huggingface.co/search?dataset=common-pile/uspto&config={urllib.parse.quote(str(cfg))}&split={urllib.parse.quote(str(spl))}&query={urllib.parse.quote(q)}&offset=0&length=3",
                  excerpt_fn=lambda js: {"num_rows_total": js.get("num_rows_total"),
                                          "first_titles": [((r.get("row") or {}).get("title") or str(((r.get("row") or {}).get("text") or ""))[:80]) for r in (js.get("rows") or [])[:3]]})

    # HUPD (Harvard USPTO Patent Dataset) — the well-known patent-application corpus
    probe(probes, "hf_dser_splits_hupd",
          "GET", "https://datasets-server.huggingface.co/splits?dataset=HUPD/hupd",
          excerpt_fn=lambda js: {"splits": [{"config": s.get("config"), "split": s.get("split")} for s in js.get("splits", [])][:8]})

    # ---- 3. EPO Linked Open Data SPARQL — the R498 406 retried with SPARQL 1.1 negotiation ----
    sparql = "SELECT ?s ?p ?o WHERE { ?s ?p ?o . } LIMIT 1"
    url_sparql = "https://data.epo.org/linked-data/data/sparql?query=" + urllib.parse.quote(sparql)
    status, body = probe(probes, "epo_lod_sparql_json_negotiation",
                         "GET", url_sparql,
                         headers={"Accept": "application/sparql-results+json"})
    if status != 200:
        # try POST form per SPARQL 1.1 protocol
        probe(probes, "epo_lod_sparql_post_form",
              "POST", "https://data.epo.org/linked-data/data/sparql",
              headers={"Accept": "application/sparql-results+json",
                       "Content-Type": "application/x-www-form-urlencoded"},
              payload="query=" + urllib.parse.quote(sparql))
    # a real identity query against a known publication (US8968233B2 — the F10 record of the sealed RBG patent leg)
    if status == 200:
        ident = ("SELECT ?p ?o WHERE { <http://data.epo.org/linked-data/data/publication/US/8968233/B2> ?p ?o . } LIMIT 20")
        probe(probes, "epo_lod_publication_identity_us8968233b2",
              "GET", "https://data.epo.org/linked-data/data/sparql?query=" + urllib.parse.quote(ident),
              headers={"Accept": "application/sparql-results+json"},
              excerpt_fn=lambda js: {"bindings": [dict((k, v.get("value", "")) for k, v in b.items()) for b in (js.get("results", {}).get("bindings") or [])][:8]})

    # ---- 4. Anonymous boundaries of registration-gated Tier-1 sources (measured, typed) ----
    probe(probes, "epo_ops_anonymous_boundary",
          "GET", "https://ops.epo.org/3.2/rest-services/published-data/search?q=" + urllib.parse.quote('ti="ballast water"') + "&Range=1-2")
    probe(probes, "patentsview_anonymous_boundary",
          "GET", "https://search.patentsview.org/api/v1/patent/?q=" + urllib.parse.quote('{"_text_any":{"patent_title":"ballast"}}') + "&f[]=patent_id")
    probe(probes, "uspto_odp_anonymous_boundary",
          "GET", "https://api.uspto.gov/v1/patent/applications/search?queryText=ballast")
    probe(probes, "uspto_patft_public_boundary",
          "GET", "https://ppubs.uspto.gov/pubwebapp/static/pages/ppubsbasic.html")

    # ---- 5. Zenodo (free research corpus host) ----
    probe(probes, "zenodo_patent_records",
          "GET", "https://zenodo.org/api/records?q=patent%20corpus&size=3",
          excerpt_fn=lambda js: {"hits_total": js.get("hits", {}).get("total"),
                                  "first_titles": [h.get("metadata", {}).get("title") for h in (js.get("hits", {}).get("hits") or [])[:3]]})

    # ---- 6. GitHub API retry (R498: per-IP 403 budget state) ----
    probe(probes, "github_patents_public_data_retry",
          "GET", "https://api.github.com/repos/google/patents-public-data",
          excerpt_fn=lambda js: {"full_name": js.get("full_name"), "default_branch": js.get("default_branch")} if isinstance(js, dict) and "full_name" in js else {"note": "non-200 or non-json"})

    # ---- 7. Google Patents transport stability (the live integrated provider) ----
    probe(probes, "google_patents_xhr_stability",
          "GET", "https://patents.google.com/xhr/query?" + urllib.parse.urlencode({"url": "q=ballast+water+treatment&num=3", "exp": ""}),
          excerpt_fn=lambda js: {"cluster_len": len(js.get("results", {}).get("cluster", []))})

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    record = {
        "probe_set": "R499_FREE_SOURCE_PROBES",
        "design": ("public endpoints only; registration-gated sources typed by their measured anonymous boundary, "
                   "never probed around it; the R498 EPO LOD 406 retried with SPARQL 1.1 content negotiation "
                   "(Accept: application/sparql-results+json); HF datasets-server (splits/rows/search) measured "
                   "for the first time — it is the actual retrieval path behind the R498 dataset-API 200"),
        "operator_directive": "use huggingface and other free sources (2026-09-18)",
        "probes": probes,
        "reviewer_provenance": "AI_REVIEW",
    }
    with open(OUT, "w") as f:
        json.dump(record, f, indent=1)
    print(f"\nwrote {OUT} ({len(probes)} probes)")


if __name__ == "__main__":
    main()

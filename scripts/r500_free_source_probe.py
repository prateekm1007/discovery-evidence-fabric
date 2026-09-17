#!/usr/bin/env python3
"""R500 — the probe-driver round: measure every free source before any
integration (never research-typing). KEYLESS round: ZERO PatentBear debits.

Operator leads (Art. XXIV: the operator's narrative is a source, never a
measurement -- every claim below is RE-MEASURED from this environment):

  L1  EPO LOD protocol endpoint https://data.epo.org/linked-data/query
      (R498 measured 406 at the /data/sparql shape -- wrong-endpoint
      hypothesis, the operator's UI-config archaeology names /query)
  L2  publication identity of the sealed F10 record US8968233B2 in the
      Tier-1 graph (number/kind/authority/date, application, priorities,
      multi-language titles, abstract, citations, representations)
  L3  family membership (familyMemberOf) + full-document representations
      (PDF/XML) -- content-bearing fetches, Range-bounded
  L4  HF datasets-server /search retry (server-side index-warming lead --
      typed transient state, never absence)
  L5  cross-provider fingerprint check: EPO LOD title/abstract vs the
      R498 PatentBear-measured fingerprint (title_sha256_12=3712021fb352,
      abstract_len=718) -- fingerprint-level only, ZERO debits; byte-level
      adjudication deferred to a future debit window (stewardship)

Constitutional anchors: Art. XXII (baseline), Art. XXIV (research vs
measurement), LXXV.1 (coverage is measured, never counted), LXXV.2 (only
content-bearing LIVE measurements confer coverage), Art. XXI (typed
absence/failure states).
"""
from __future__ import annotations

import hashlib
import json
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

REPO = "/home/z/my-project/hf_space"
OUT = REPO + "/R500/R500_FREE_SOURCE_PROBE.json"

UA = "toscanini-rbg-probe/1.0 (keyless epistemic measurement; operator-directed)"
SEALED_F10 = {
    "record_id": "US8968233B2",
    "title_sha256_12": "3712021fb352",
    "abstract_len": 718,
    "source": "R498/R498_PATENTBEAR_ROTATION_PROBE.json first_hit_fingerprint",
}
LEDGER = {
    "probe": "R500_FREE_SOURCE_PROBE",
    "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "debits_spent": 0,
    "auth": "NONE (keyless by design; the shared PatentBear bucket at 19/20 is untouched)",
    "rounds": [],
}


def call(name, url, method="GET", headers=None, params=None, data=None,
         timeout=45, notes=""):
    """One measured HTTP interaction. Never hard-types: the typed_state is
    decided by the caller from the measured response."""
    entry = {"name": name, "method": method, "url": url, "params": params,
             "request_headers": headers or {}, "notes": notes,
             "utc": time.strftime("%H:%M:%SZ", time.gmtime())}
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
        entry["url_full"] = url
    try:
        req = urllib.request.Request(url, method=method,
                                     headers=dict(entry["request_headers"]),
                                     data=data)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            entry.update({
                "http": r.status,
                "response_headers": {k: v for k, v in r.headers.items()
                                     if k.lower() in (
                                         "content-type", "content-length",
                                         "content-range", "date", "server",
                                         "accept-ranges", "vary")},
                "body_len": len(body),
                "body_sha256_12": hashlib.sha256(body).hexdigest()[:12],
            })
            entry["_body"] = body
    except urllib.error.HTTPError as e:
        body = b""
        try:
            body = e.read()
        except Exception:
            pass
        entry.update({"http": e.code, "error": "HTTPError",
                      "body_len": len(body),
                      "body_sha256_12": hashlib.sha256(body).hexdigest()[:12]
                      if body else None})
        entry["_body"] = body
    except Exception as e:  # DNS, timeout, SSL...
        entry.update({"http": None, "error": type(e).__name__,
                      "error_detail": str(e)[:200]})
        entry["_body"] = b""
    LEDGER["rounds"].append({k: v for k, v in entry.items() if k != "_body"})
    return entry


def _is_json(e):
    try:
        json.loads(e.get("_body", b"") or b"")
        return True
    except Exception:
        return False


def excerpt(e, n=420):
    b = e.get("_body", b"") or b""
    return b[:n].decode("utf-8", "replace")


# ---------------------------------------------------------------- L1: EPO LOD protocol
Q_BASIC = "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 3"
r_proto = call(
    "L1_epo_lod_sparql_protocol_GET",
    "https://data.epo.org/linked-data/query",
    params={"query": Q_BASIC},
    headers={"User-Agent": UA, "Accept": "application/sparql-results+json"},
    notes="R498 measured 406 at a DIFFERENT url shape; operator UI-config "
          "lead names /linked-data/query as the SPARQL protocol endpoint")
proto_json = None
if r_proto.get("http") == 200:
    try:
        proto_json = json.loads(r_proto["_body"])
    except Exception:
        proto_json = None
r_proto["typed_state"] = (
    "LIVE_PROTOCOL_SPARQL_JSON" if proto_json and "results" in proto_json
    else "HTML_APP_NOT_PROTOCOL" if r_proto.get("http") == 200 and
         b"<html" in (r_proto.get("_body", b"") or b"").lower()
    else "TYPED_FROM_RESPONSE_HTTP_%s" % r_proto.get("http"))
if proto_json and "results" in proto_json:
    r_proto["evidence"] = {
        "bindings": len(proto_json["results"].get("bindings", [])),
        "first_binding": proto_json["results"].get("bindings", [{}])[0] or {},
    }

# POST form variant (SPARQL 1.1 protocol alternative binding)
r_post = call(
    "L1_epo_lod_sparql_protocol_POST_form",
    "https://data.epo.org/linked-data/query",
    method="POST",
    data=urllib.parse.urlencode({"query": Q_BASIC}).encode(),
    headers={"User-Agent": UA, "Accept": "application/sparql-results+json",
             "Content-Type": "application/x-www-form-urlencoded"},
    notes="SPARQL 1.1 protocol POST form-encoding variant")
post_json = None
if r_post.get("http") == 200:
    try:
        post_json = json.loads(r_post["_body"])
    except Exception:
        post_json = None
r_post["typed_state"] = (
    "LIVE_PROTOCOL_SPARQL_JSON" if post_json and "results" in post_json
    else "TYPED_FROM_RESPONSE_HTTP_%s" % r_post.get("http"))

# ------------------------------------------------- L2/L3: publication identity + family + docs
PATTERNS = [
    ("P1_bare", "https://data.epo.org/linked-data/data/publication/US/8968233B2"),
    ("P2_trailing_slash", "https://data.epo.org/linked-data/data/publication/US/8968233B2/"),
    ("P3_dashed", "https://data.epo.org/linked-data/data/publication/US/8968233-B2"),
]
pub_entry, pub_ld = None, None
for tag, url in PATTERNS:
    e = call("L2_publication_uri_%s" % tag, url,
             headers={"User-Agent": UA, "Accept": "application/ld+json"},
             notes="direct publication-URI pattern probe (operator lead: "
                   "'the URI pattern needs the suffix')")
    e["typed_state"] = ("LIVE_RDF_JSONLD" if e.get("http") == 200 and
                        _is_json(e) else "HTTP_%s" % e.get("http"))
    if e["typed_state"] == "LIVE_RDF_JSONLD":
        pub_entry, pub_ld = e, json.loads(e["_body"])
        break
    if pub_entry is None:
        pub_entry = e

if pub_ld is None and pub_entry is not None and pub_entry.get("http") == 200:
    pub_entry["typed_state"] = "HTTP_200_NON_JSON_BODY"

title_match, titles_fp, abstract_info = None, [], {}
pub_uri = None
if pub_ld is not None:
    graph = pub_ld if isinstance(pub_ld, list) else pub_ld.get("@graph", [pub_ld])
    nodes = [n for n in (graph if isinstance(graph, list) else [graph])
             if isinstance(n, dict)]
    pub_node = next((n for n in nodes if any("8968233" in str(v)
                     for v in n.values() if isinstance(v, (str, list)))), None)
    if pub_node is None and nodes:
        pub_node = nodes[0]
    if pub_node is not None:
        pub_uri = pub_node.get("@id")
        preds = {}
        for k, v in pub_node.items():
            if k == "@id":
                continue
            preds[k] = v if not isinstance(v, (dict, list)) else (
                json.dumps(v)[:300])
        pub_entry["identity_predicates"] = preds
        pub_entry["identity_predicate_names"] = sorted(
            k for k in pub_node if k != "@id")
        # titles (multi-language), abstract, family, citations, representations
        for k, v in pub_node.items():
            kl = k.lower()
            vs = v if isinstance(v, list) else [v]
            vals = [x.get("@value", x) if isinstance(x, dict) else x
                    for x in vs if isinstance(x, (dict, str))]
            langs = [x.get("@language") if isinstance(x, dict) else None
                     for x in vs]
            if "title" in kl:
                for val, lg in zip(vals, langs):
                    if isinstance(val, str) and val.strip():
                        fp = hashlib.sha256(val.encode()).hexdigest()[:12]
                        titles_fp.append({"lang": lg, "len": len(val),
                                          "sha256_12": fp,
                                          "matches_patentbear": fp ==
                                          SEALED_F10["title_sha256_12"]})
            if "abstract" in kl:
                for val, lg in zip(vals, langs):
                    if isinstance(val, str) and val.strip():
                        abstract_info.setdefault(lg or "und",
                                                 {"len": len(val),
                                                  "sha256_12": hashlib.sha256(
                                                      val.encode()).hexdigest()[:12]})
            if "family" in kl:
                fam = [x.get("@id") if isinstance(x, dict) else x for x in vs]
                pub_entry["family_objects"] = fam
            if "cites" in kl.replace("description", ""):
                pub_entry["citation_objects"] = (
                    json.dumps(v)[:300] if not isinstance(v, list)
                    else [x.get("@id") if isinstance(x, dict) else x
                          for x in v][:8])
            if "representation" in kl or "primaryDocument" in kl or \
               kl.endswith("page"):
                pub_entry.setdefault("representation_hints", {})[k] = (
                    json.dumps(v)[:300])
        pub_entry["title_fingerprints"] = titles_fp
        pub_entry["abstract_lengths_by_lang"] = abstract_info
        pub_entry["match_verdict"] = (
            "CROSS_PROVIDER_TITLE_FINGERPRINT_MATCH" if any(
                t["matches_patentbear"] for t in titles_fp)
            else "CROSS_PROVIDER_TITLE_MISMATCH_UNADJUDICATED"
            if titles_fp else "NO_TITLE_IN_GRAPH")
        # any doc URIs anywhere in the node (pdf/xml)
        blob = json.dumps(pub_node)
        doc_urls = sorted(set(
            re.findall(r'https://[^"\s<>]+?\.(?:pdf|xml)', blob) +
            re.findall(r'https://[^"\s<>]+?/(?:pdf|xml)(?:/[a-z]{2})?(?=["\s<>]|$)', blob)
        ))[:6]
        pub_entry["document_urls_found"] = doc_urls
        # L3a: family object fetch (first family URI)
        fam_uris = [u for u in (pub_entry.get("family_objects") or [])
                    if isinstance(u, str) and u.startswith("http")]
        if fam_uris:
            rf = call("L3_family_object_GET", fam_uris[0],
                      headers={"User-Agent": UA, "Accept": "application/ld+json"},
                      notes="family membership object (familyMemberOf)")
            rf["typed_state"] = "HTTP_%s" % rf.get("http")
            if rf.get("http") == 200 and _is_json(rf):
                try:
                    fj = json.loads(rf["_body"])
                    rf["family_node_keys"] = sorted(
                        k for n in (fj.get("@graph", [fj]) if
                                    isinstance(fj, dict) else fj)
                        if isinstance(n, dict) for k in n)[:24]
                    rf["typed_state"] = "LIVE_RDF_JSONLD"
                except Exception:
                    pass
        # L3b: document fetches, Range-bounded (content-bearing proof)
        for i, du in enumerate(doc_urls[:3]):
            rd = call("L3_document_fetch_%d" % i, du,
                      headers={"User-Agent": UA,
                               "Range": "bytes=0-255"},
                      notes="Tier-1 primary text availability, Range-bounded")
            ct = (rd.get("response_headers") or {}).get("Content-Type", "?")
            rd["typed_state"] = (
                "LIVE_CONTENT_BEARING_BYTES" if rd.get("http") in (200, 206)
                and rd.get("body_len", 0) > 0 else "HTTP_%s" % rd.get("http"))
            rd["content_type"] = ct
else:
    # SPARQL fallback: locate the publication node by literal scan
    Q_FIND = ('SELECT ?pub WHERE { ?pub ?p "US8968233B2" } LIMIT 5')
    rf = call("L2_sparql_fallback_locate_publication",
              "https://data.epo.org/linked-data/query",
              params={"query": Q_FIND},
              headers={"User-Agent": UA, "Accept": "application/sparql-results+json"},
              notes="fallback: find the publication node by literal",
              timeout=70)
    rf["typed_state"] = "HTTP_%s" % rf.get("http")

# ---------------------------------------------------------------- L4: HF search retry
r_hf = call(
    "L4_hf_datasets_server_search_retry",
    "https://datasets-server.huggingface.co/search",
    params={"dataset": "common-pile/uspto", "config": "default",
            "split": "train", "query": "shunt valve", "offset": 0,
            "length": 3},
    headers={"User-Agent": UA},
    notes="operator lead: search index warming server-side -- typed "
          "transient state, never absence")
hb = r_hf.get("_body", b"") or b""
try:
    hj = json.loads(hb)
except Exception:
    hj = None
if r_hf.get("http") == 200 and hj and hj.get("rows") is not None:
    r_hf["typed_state"] = "LIVE_CONTENT_BEARING_SEARCH_ROWS"
    r_hf["evidence"] = {"num_rows_returned": len(hj.get("rows", [])),
                        "num_total": hj.get("num_rows_total"),
                        "first_row_preview_keys": sorted(
                            (hj["rows"][0].get("row") or {}).keys())[:12]
                        if hj.get("rows") else []}
else:
    msg = ""
    if isinstance(hj, dict):
        msg = str(hj.get("error"))[:200]
    r_hf["typed_state"] = (
        "TRANSIENT_INDEX_WARMING_OR_UNAVAILABLE_%s" % r_hf.get("http"))
    r_hf["provider_message"] = msg
    r_hf["body_excerpt"] = excerpt(r_hf, 240)

# ------------------------------------------------- L5: corroboration summary (no new calls)
summary = {
    "epo_lod_protocol": r_proto.get("typed_state"),
    "epo_lod_protocol_post": r_post.get("typed_state"),
    "publication_uri_resolved": pub_uri or
        (pub_entry or {}).get("url_full", "UNRESOLVED"),
    "publication_state": (pub_entry or {}).get("typed_state"),
    "title_fingerprints": titles_fp,
    "abstract_lengths_by_lang": abstract_info,
    "sealed_f10_reference": SEALED_F10,
    "cross_provider_verdict": (pub_entry or {}).get("match_verdict",
                                                    "PUBLICATION_UNRESOLVED"),
    "hf_search_state": r_hf.get("typed_state"),
}
LEDGER["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
LEDGER["summary"] = summary
import os
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w") as f:
    json.dump(LEDGER, f, indent=1, ensure_ascii=False)
print(json.dumps(summary, indent=1, ensure_ascii=False))
print("ledger ->", OUT)

#!/usr/bin/env python3
"""R500 PASS-2 — the located-publication flow (companion to
r500_free_source_probe.py; that pass proved the protocol endpoint LIVE and
left three named open items):

  1. L2-fallback SELECT ?pub {?pub ?p "US8968233B2"} measured HTTP 200 —
     this pass CAPTURES the bindings (pass-1 hashed only) and derives the
     real publication URI shape;
  2. negotiation ladder on the located URI (ld+json / turtle / rdf+xml /
     .json suffix / ?format=json) until a content-bearing RDF body lands;
  3. identity-model extraction: multi-language titles (sha256_12 vs the
     R498 PatentBear fingerprint 3712021fb352), abstract lengths (vs 718),
     application/priorities/dates, citations, classifications, family
     membership, document representations;
  4. family object + Range-bounded document fetches (content-bearing proof);
  5. HF datasets-server /search retry at timeout=90 (pass-1 read timed out
     at 45s — typed transient, never absence).

KEYLESS. ZERO PatentBear debits. Art. XXIV/XXI/LXXV discipline throughout.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

REPO = "/home/z/my-project/hf_space"
OUT = REPO + "/R500/R500_FREE_SOURCE_PROBE_PASS2.json"
UA = "toscanini-rbg-probe/1.0 (keyless epistemic measurement; operator-directed)"
QEND = "https://data.epo.org/linked-data/query"
SEALED = {"record_id": "US8968233B2",
          "title_sha256_12": "3712021fb352", "abstract_len": 718}
LEDGER = {"probe": "R500_FREE_SOURCE_PROBE_PASS2",
          "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
          "debits_spent": 0, "rounds": []}


def call(name, url, method="GET", headers=None, params=None, data=None,
         timeout=60, notes=""):
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
            entry.update({"http": r.status,
                          "response_headers": {k: v for k, v in
                                               r.headers.items() if k.lower()
                                               in ("content-type",
                                                   "content-length",
                                                   "content-range", "date",
                                                   "vary", "accept-ranges")},
                          "body_len": len(body),
                          "body_sha256_12":
                          hashlib.sha256(body).hexdigest()[:12]})
            entry["_body"] = body
    except urllib.error.HTTPError as e:
        body = b""
        try:
            body = e.read()
        except Exception:
            pass
        hdrs = {k: v for k, v in (e.headers or {}).items() if k.lower() in
                ("content-type", "content-length", "vary")}
        entry.update({"http": e.code, "error": "HTTPError",
                      "response_headers": hdrs, "body_len": len(body),
                      "body_sha256_12": hashlib.sha256(body).hexdigest()[:12]
                      if body else None})
        entry["_body"] = body
    except Exception as e:
        entry.update({"http": None, "error": type(e).__name__,
                      "error_detail": str(e)[:200]})
        entry["_body"] = b""
    entry["body_excerpt"] = (entry.get("_body", b"") or
                             b"")[:300].decode("utf-8", "replace")
    LEDGER["rounds"].append({k: v for k, v in entry.items() if k != "_body"})
    return entry


def sj(e):
    try:
        return json.loads(e.get("_body", b"") or b"")
    except Exception:
        return None


# ---- step 1: locate the publication node (pass-1 fallback proved 200) ----
Q_FIND = 'SELECT ?pub WHERE { ?pub ?p "US8968233B2" } LIMIT 5'
r_loc = call("P2_locate_publication_literal",
             QEND, params={"query": Q_FIND},
             headers={"User-Agent": UA,
                      "Accept": "application/sparql-results+json"},
             notes="pass-1 measured this 200 but hashed the body; now "
                   "capturing the bindings")
loc = sj(r_loc)
pub_uris = []
if r_loc.get("http") == 200 and loc:
    binds = loc.get("results", {}).get("bindings", [])
    pub_uris = [b["pub"]["value"] for b in binds if b.get("pub")]
    r_loc["located_pub_uris"] = pub_uris
    r_loc["typed_state"] = ("LIVE_LOCATED_%d_URIS" % len(pub_uris)
                            if pub_uris else "LIVE_ZERO_BINDINGS")
else:
    r_loc["typed_state"] = "HTTP_%s" % r_loc.get("http")

# ---- step 2: negotiation ladder on the located URI ----
pub_ld, pub_entry = None, None
target = pub_uris[0] if pub_uris else \
    "https://data.epo.org/linked-data/data/publication/US/8968233B2"
LADDER = [
    ("ld+json", None),
    ("turtle", None),
    ("rdf+xml", None),
    ("ld+json_json_suffix", target + ".json"),
    ("ld+json_format_param", None),
]
for tag, url_override in LADDER:
    url = url_override or target
    h = {"User-Agent": UA}
    params = None
    if tag == "ld+json":
        h["Accept"] = "application/ld+json"
    elif tag == "turtle":
        h["Accept"] = "text/turtle"
    elif tag == "rdf+xml":
        h["Accept"] = "application/rdf+xml"
    elif tag == "ld+json_json_suffix":
        h["Accept"] = "application/ld+json"
    elif tag == "ld+json_format_param":
        h["Accept"] = "application/ld+json"
        params = {"format": "json"}
    e = call("P2_located_fetch_%s" % tag, url, headers=h, params=params,
             notes="negotiation ladder on the located publication URI")
    body = e.get("_body", b"") or b""
    e["looks_like"] = ("json" if body[:1] in (b"{", b"[") else
                       "turtle" if re.match(rb"br?\s*@prefix", body[:200]) or
                       b"@prefix" in body[:600] else
                       "xml" if body[:5] in (b"<?xml", b"<rdf:", b"<RDF:") else
                       "other")
    parsed = sj(e) if e["looks_like"] == "json" else None
    if parsed is not None:
        e["typed_state"] = "LIVE_RDF_JSONLD"
        pub_ld, pub_entry = parsed, e
        break
    e["typed_state"] = "HTTP_%s_BODY_%s" % (e.get("http"), e["looks_like"])
    if pub_entry is None:
        pub_entry = e
    if e.get("http") == 200:
        break  # a 200 non-JSON body is itself informative; stop climbing

# ---- step 3: identity model extraction + fingerprint check ----
extracted = {}
if pub_ld is not None:
    graph = pub_ld if isinstance(pub_ld, list) else pub_ld.get("@graph",
                                                              [pub_ld])
    nodes = [n for n in (graph if isinstance(graph, list) else [graph])
             if isinstance(n, dict)]
    node = next((n for n in nodes if any("8968233" in str(v)
                 for v in n.values() if isinstance(v, (str, list)))), None)
    if node is None and nodes:
        node = nodes[0]
    blob = json.dumps(node)
    titles, abstracts, fam, cites, classes, docs = [], {}, [], [], [], []
    for k, v in node.items():
        kl = k.lower()
        vs = v if isinstance(v, list) else [v]
        vals = [(x.get("@value"), x.get("@language")) if isinstance(x, dict)
                else (x, None) for x in vs if isinstance(x, (dict, str))]
        if "title" in kl:
            for val, lg in vals:
                if isinstance(val, str) and val.strip():
                    titles.append({
                        "lang": lg, "len": len(val),
                        "sha256_12": hashlib.sha256(
                            val.encode()).hexdigest()[:12],
                        "matches_patentbear": hashlib.sha256(
                            val.encode()).hexdigest()[:12] ==
                        SEALED["title_sha256_12"],
                        "preview": val[:110]})
        if "abstract" in kl:
            for val, lg in vals:
                if isinstance(val, str) and val.strip():
                    abstracts[lg or "und"] = {
                        "len": len(val),
                        "sha256_12": hashlib.sha256(
                            val.encode()).hexdigest()[:12],
                        "preview": val[:110]}
        if "family" in kl:
            fam += [x.get("@id") if isinstance(x, dict) else x for x in vs
                    if isinstance(x, (dict, str))]
        if "cites" in kl:
            cites += [x.get("@id") if isinstance(x, dict) else x for x in vs
                      if isinstance(x, (dict, str))][:10]
        if "classification" in kl or kl.endswith("cpc") or kl.endswith("ipc"):
            classes += [x.get("@id") if isinstance(x, dict) else x for x in vs
                        if isinstance(x, (dict, str))][:10]
    extracted = {
        "node_id": node.get("@id"),
        "predicate_names": sorted(k for k in node if k != "@id"),
        "identity_fields": {k: (v if isinstance(v, (str, int, float))
                                else json.dumps(v)[:200])
                            for k, v in node.items()
                            if k != "@id" and not isinstance(v, dict)},
        "titles": titles,
        "abstracts_by_lang": abstracts,
        "family_objects": fam[:6],
        "citation_objects": cites,
        "classification_objects": classes,
        "document_urls": sorted(set(
            re.findall(r'https://[^"\s<>]+?\.(?:pdf|xml)', blob) +
            re.findall(r'https://[^"\s<>]+?/(?:pdf|xml)(?:/[a-z]{2})?'
                       r'(?=["\s<>]|$)', blob)))[:6],
    }
    extracted["cross_provider_verdict"] = (
        "CROSS_PROVIDER_TITLE_FINGERPRINT_MATCH" if any(
            t["matches_patentbear"] for t in titles)
        else "CROSS_PROVIDER_TITLE_MISMATCH_UNADJUDICATED" if titles
        else "NO_TITLE_IN_GRAPH")

    # ---- step 4a: family object fetch ----
    fam_uris = [u for u in fam if isinstance(u, str) and u.startswith("http")]
    if fam_uris:
        rf = call("P2_family_object_GET", fam_uris[0],
                  headers={"User-Agent": UA, "Accept": "application/ld+json"},
                  notes="familyMemberOf object (L3 lead)")
        rf["typed_state"] = ("LIVE_RDF_JSONLD" if rf.get("http") == 200 and
                             sj(rf) is not None else
                             "HTTP_%s" % rf.get("http"))
        fj = sj(rf)
        if fj:
            g2 = fj.get("@graph", [fj]) if isinstance(fj, dict) else fj
            rf["family_node_keys"] = sorted(
                {k for n in (g2 if isinstance(g2, list) else [g2])
                 if isinstance(n, dict) for k in n})[:24]
    # ---- step 4b: Range-bounded document fetches ----
    for i, du in enumerate(extracted["document_urls"][:3]):
        rd = call("P2_document_fetch_%d" % i, du,
                  headers={"User-Agent": UA, "Range": "bytes=0-255"},
                  notes="Tier-1 primary text availability, Range-bounded")
        rd["typed_state"] = (
            "LIVE_CONTENT_BEARING_BYTES" if rd.get("http") in (200, 206) and
            rd.get("body_len", 0) > 0 else "HTTP_%s" % rd.get("http"))
else:
    extracted = {"status": "PUBLICATION_BODY_NOT_PARSED_AS_JSONLD",
                 "negotiation_final": (pub_entry or {}).get("typed_state")}

# ---- step 5: HF /search retry, longer window ----
r_hf = call("P2_hf_search_retry_90s",
            "https://datasets-server.huggingface.co/search",
            params={"dataset": "common-pile/uspto", "config": "default",
                    "split": "train", "query": "shunt valve", "offset": 0,
                    "length": 3},
            headers={"User-Agent": UA}, timeout=90,
            notes="pass-1 read timed out at 45s; retry with a 90s window")
hj = sj(r_hf)
if r_hf.get("http") == 200 and hj and hj.get("rows") is not None:
    r_hf["typed_state"] = "LIVE_CONTENT_BEARING_SEARCH_ROWS"
    r_hf["evidence"] = {"rows_returned": len(hj.get("rows", [])),
                        "num_rows_total": hj.get("num_rows_total"),
                        "row_keys": sorted(
                            (hj["rows"][0].get("row") or {}).keys())[:12]
                        if hj.get("rows") else []}
else:
    r_hf["typed_state"] = ("TRANSIENT_%s_%s" % (
        r_hf.get("error") or "HTTP", r_hf.get("http")))

LEDGER["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
LEDGER["summary"] = {
    "located_pub_uris": pub_uris,
    "negotiation_winner": (pub_entry or {}).get("typed_state"),
    "identity": extracted,
    "hf_search_state": r_hf.get("typed_state"),
    "hf_search_evidence": r_hf.get("evidence") or r_hf.get("error_detail"),
    "sealed_f10_reference": SEALED,
}
import os
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w") as f:
    json.dump(LEDGER, f, indent=1, ensure_ascii=False)
print(json.dumps(LEDGER["summary"], indent=1, ensure_ascii=False)[:4000])
print("ledger ->", OUT)

#!/usr/bin/env python3
"""R500 PASS-4 (final) — the full identity model behind Elda's page wrapper.

PASS-3 measured the publication resource 200 under Accept: text/turtle and
identified its shape: an Elda LDA page wrapper (vocab#items/vocab#page/
lda#notice) whose canonical self-URI carries the .ttl suffix (the operator's
"/-suffix" lead, now measured). The publication's real description lives in
the vocab#items object(s); the lda#notice object carries the license/
attribution notice (LICENSE-COMPATIBLE evidence for the LXXV six-property
law).

This pass: wrapper -> items -> identity model (multi-language titles,
abstracts, application/priorities/dates, citations, classifications, family
membership, document representations) -> fingerprints against the R498
PatentBear measurement -> family fetch -> Range-bounded document fetches ->
search endpoint (turtle negotiation variant).

KEYLESS. ZERO PatentBear debits. Art. XXI typed states throughout.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
import urllib.error

import rdflib

REPO = "/home/z/my-project/hf_space"
OUT = REPO + "/R500/R500_FREE_SOURCE_PROBE_PASS4.json"
UA = "toscanini-rbg-probe/1.0 (keyless epistemic measurement; operator-directed)"
PUB = "https://data.epo.org/linked-data/data/publication/US/8968233B2"
SEALED = {"record_id": "US8968233B2",
          "title_sha256_12": "3712021fb352", "abstract_len": 718}
LEDGER = {"probe": "R500_FREE_SOURCE_PROBE_PASS4",
          "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
          "debits_spent": 0, "rounds": []}


def call(name, url, headers=None, params=None, timeout=60, notes=""):
    entry = {"name": name, "url": url, "params": params,
             "request_headers": headers or {}, "notes": notes,
             "utc": time.strftime("%H:%M:%SZ", time.gmtime())}
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
        entry["url_full"] = url
    try:
        req = urllib.request.Request(url, headers=dict(entry["request_headers"]))
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            entry.update({"http": r.status, "body_len": len(body),
                          "body_sha256_12": hashlib.sha256(
                              body).hexdigest()[:12]})
            entry["_body"] = body
    except urllib.error.HTTPError as e:
        body = b""
        try:
            body = e.read()
        except Exception:
            pass
        entry.update({"http": e.code, "error": "HTTPError",
                      "body_len": len(body)})
        entry["_body"] = body
    except Exception as e:
        entry.update({"http": None, "error": type(e).__name__,
                      "error_detail": str(e)[:200]})
        entry["_body"] = b""
    LEDGER["rounds"].append({k: v for k, v in entry.items() if k != "_body"})
    return entry


def turtle_graph(e, base):
    g = rdflib.Graph()
    g.parse(data=(e.get("_body", b"") or b"").decode("utf-8", "replace"),
            format="turtle", publicID=base)
    return g


# ---- step 1: wrapper -> items + notice ----
r_wrap = call("P4_wrapper_turtle", PUB,
              headers={"User-Agent": UA, "Accept": "text/turtle"},
              notes="PASS-3 shape re-measured (cached by provider?)")
gw = turtle_graph(r_wrap, PUB)
r_wrap["typed_state"] = "LIVE_RDF_TURTLE_PARSED"
r_wrap["triples"] = len(gw)

V_ITEMS = None
for p in set(gw.predicates(None, None)):
    if str(p).endswith("items"):
        V_ITEMS = p
notice_uris = [str(o) for s, p, o in gw if str(p).endswith("notice")
               and isinstance(o, rdflib.URIRef)]
item_uris = [str(o) for s, p, o in gw if str(p).endswith("items") and
             isinstance(o, (rdflib.URIRef, rdflib.BNode))]
r_wrap["item_uris"] = [str(u) for u in item_uris][:4]
r_wrap["notice_uris"] = notice_uris[:3]

# ---- step 2: fetch the item description(s) ----
g_all = rdflib.Graph()
for i, iu in enumerate(item_uris[:2]):
    iu_str = str(iu)
    url = iu_str if iu_str.startswith("http") else \
        "https://data.epo.org/linked-data/data/publication/US/" + iu_str
    if not url.endswith(".ttl") and not url.endswith("#id"):
        url = url + ".ttl" if url.count("/") < 6 else url
    ri = call("P4_item_turtle_%d" % i, url,
              headers={"User-Agent": UA, "Accept": "text/turtle"},
              notes="the publication description node (full identity model)")
    try:
        gi = turtle_graph(ri, url)
        ri["typed_state"] = "LIVE_RDF_TURTLE_PARSED"
        ri["triples"] = len(gi)
        g_all += gi
    except Exception as ex:
        ri["typed_state"] = "TURTLE_PARSE_FAILED: %s" % type(ex).__name__

# find the described publication node: the subject carrying title/abstract
identity = {"pub_uri": PUB, "item_graph_triples": len(g_all)}
node = None
for s in set(g_all.subjects()):
    preds = {str(p).lower() for p in g_all.predicates(s, None)}
    if any("title" in p for p in preds) or \
       any("abstract" in p for p in preds):
        node = s
        break
if node is None:
    # fall back: the subject with the most triples
    cnt = {}
    for s, _, _ in g_all:
        cnt[s] = cnt.get(s, 0) + 1
    node = max(cnt, key=cnt.get) if cnt else None
identity["identity_node"] = str(node) if node is not None else None

if node is not None:
    titles, abstracts = [], []
    for p, o in g_all.predicate_objects(node):
        pl, val = str(p).lower(), str(o)
        if "title" in pl:
            titles.append({"lang": getattr(o, "language", None),
                           "len": len(val), "pred": pl,
                           "sha256_12": hashlib.sha256(
                               val.encode()).hexdigest()[:12],
                           "matches_patentbear": hashlib.sha256(
                               val.encode()).hexdigest()[:12] ==
                           SEALED["title_sha256_12"],
                           "preview": val[:120]})
        if "abstract" in pl:
            abstracts.append({"lang": getattr(o, "language", None),
                              "len": len(val), "pred": pl,
                              "sha256_12": hashlib.sha256(
                                  val.encode()).hexdigest()[:12],
                              "preview": val[:120]})
    identity["titles"] = titles
    identity["abstracts"] = abstracts
    identity["abstract_len_matches_patentbear_718"] = any(
        a["len"] == SEALED["abstract_len"] for a in abstracts)
    identity["cross_provider_verdict"] = (
        "CROSS_PROVIDER_TITLE_FINGERPRINT_MATCH" if any(
            t["matches_patentbear"] for t in titles)
        else "CROSS_PROVIDER_TITLE_MISMATCH_UNADJUDICATED" if titles
        else "NO_TITLE_IN_GRAPH")
    for field in ("applicationReference", "priority", "publicationDate",
                  "publicationNumber", "publicationKind",
                  "publicationAuthority", "grantDate", "inventedBy",
                  "applicantName"):
        vals = [str(o) for p, o in g_all.predicate_objects(node)
                if field.lower() in str(p).lower()]
        if vals:
            identity[field] = sorted(set(vals))[:8]
    identity["family_uris"] = [str(o) for p, o in
                               g_all.predicate_objects(node)
                               if "family" in str(p).lower()][:6]
    identity["citation_uris"] = [str(o) for p, o in
                                 g_all.predicate_objects(node)
                                 if "cites" in str(p).lower()][:8]
    identity["classification_uris"] = [str(o) for p, o in
                                       g_all.predicate_objects(node)
                                       if "classification" in
                                       str(p).lower()][:8]
    uriset = set()
    for s2, p2, o2 in g_all:
        for t in (s2, p2, o2):
            t = str(t)
            if t.startswith("http") and re.search(
                    r"(pdf|xml|doc/|represent)", t, re.I):
                uriset.add(t)
    identity["representation_uris"] = sorted(uriset)[:10]

# ---- step 3: the license notice (LICENSE-COMPATIBLE evidence) ----
if notice_uris:
    rn = call("P4_license_notice", notice_uris[0],
              headers={"User-Agent": UA, "Accept": "text/turtle"},
              notes="lda#notice object — the license/attribution artifact")
    try:
        gn = turtle_graph(rn, notice_uris[0])
        rn["typed_state"] = "LIVE_RDF_TURTLE_PARSED"
        notice_text = [str(o) for _, o in gn if isinstance(o,
                        rdflib.Literal) and len(str(o)) > 40]
        rn["notice_literals"] = notice_text[:4]
        license_uris = sorted({str(o) for _, o in gn if "license" in
                               str(o).lower() or "creativecommons" in
                               str(o).lower()})
        rn["license_uris"] = license_uris[:5]
    except Exception as ex:
        rn["typed_state"] = "PARSE_FAILED_%s_HTTP_%s" % (
            type(ex).__name__, rn.get("http"))

# ---- step 4: family + Range-bounded documents ----
fam_uris = [u for u in identity.get("family_uris", []) if
            u.startswith("http")]
if fam_uris:
    r_fam = call("P4_family_turtle", fam_uris[0],
                 headers={"User-Agent": UA, "Accept": "text/turtle"},
                 notes="familyMemberOf object")
    try:
        gf = turtle_graph(r_fam, fam_uris[0])
        r_fam["typed_state"] = "LIVE_RDF_TURTLE_PARSED"
        r_fam["triples"] = len(gf)
        r_fam["family_members_sample"] = sorted(
            {str(o) for _, o in gf if "member" in str(o).lower() or
             isinstance(o, rdflib.URIRef) and "/publication/" in
             str(o)})[:12]
    except Exception as ex:
        r_fam["typed_state"] = "PARSE_FAILED_%s_HTTP_%s" % (
            type(ex).__name__, r_fam.get("http"))
for i, du in enumerate(identity.get("representation_uris", [])[:2]):
    rd = call("P4_document_range_%d" % i, du,
              headers={"User-Agent": UA, "Range": "bytes=0-255"},
              notes="Tier-1 primary text, Range-bounded")
    rd["typed_state"] = ("LIVE_CONTENT_BEARING_BYTES" if
                         rd.get("http") in (200, 206) and
                         rd.get("body_len", 0) > 0 else
                         "HTTP_%s_%s" % (rd.get("http"),
                                         rd.get("error", "")))

# ---- step 5: search endpoint, turtle negotiation variant ----
r_s2 = call("P4_search_turtle", "https://data.epo.org/linked-data/data/search",
            headers={"User-Agent": UA, "Accept": "text/turtle"},
            params={"q": "8968233"},
            notes="operator warming lead; turtle negotiation variant")
try:
    gs = turtle_graph(r_s2, "https://data.epo.org/linked-data/data/search")
    r_s2["typed_state"] = "LIVE_RDF_TURTLE_PARSED"
    r_s2["triples"] = len(gs)
    hits = sorted({str(o) for _, o in gs if "/publication/" in
                   str(o)})[:8]
    r_s2["publication_hits_sample"] = hits
except Exception as ex:
    r_s2["typed_state"] = "HTTP_%s_%s" % (r_s2.get("http"),
                                          r_s2.get("error", "") or
                                          type(ex).__name__)

LEDGER["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
LEDGER["summary"] = {"identity": identity, "sealed_f10_reference": SEALED}
import os
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w") as f:
    json.dump(LEDGER, f, indent=1, ensure_ascii=False)
print(json.dumps(LEDGER["summary"], indent=1, ensure_ascii=False)[:5000])
print("ledger ->", OUT)

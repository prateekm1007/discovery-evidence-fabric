#!/usr/bin/env python3
"""R500 PASS-3 — the Tier-1 identity extraction on the turtle-negotiated
publication resource.

PASS-1 proved the SPARQL protocol endpoint LIVE (GET+POST, 200 sparql-json).
PASS-2 proved the direct publication URI https://data.epo.org/linked-data/
data/publication/US/8968233B2 answers 200 under Accept: text/turtle (the
406s were a negotiation miss, NOT absence — and NOT a wrong URI), and
captured HF's verbatim transient state ("the dataset index is loading").
This pass: parse the turtle with rdflib, extract the full identity model
for the SEALED F10 record US8968233B2, fingerprint the titles/abstracts
against the R498 PatentBear measurement (title_sha256_12=3712021fb352,
abstract_len=718), fetch family + Range-bounded documents, and probe the
EPO LOD discovery/search endpoint the operator flagged.

KEYLESS. ZERO PatentBear debits.
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
OUT = REPO + "/R500/R500_FREE_SOURCE_PROBE_PASS3.json"
UA = "toscanini-rbg-probe/1.0 (keyless epistemic measurement; operator-directed)"
PUB = "https://data.epo.org/linked-data/data/publication/US/8968233B2"
SEALED = {"record_id": "US8968233B2",
          "title_sha256_12": "3712021fb352", "abstract_len": 718}
LEDGER = {"probe": "R500_FREE_SOURCE_PROBE_PASS3",
          "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
          "debits_spent": 0, "rounds": []}


def call(name, url, method="GET", headers=None, params=None, timeout=60,
         notes=""):
    entry = {"name": name, "method": method, "url": url, "params": params,
             "request_headers": headers or {}, "notes": notes,
             "utc": time.strftime("%H:%M:%SZ", time.gmtime())}
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
        entry["url_full"] = url
    try:
        req = urllib.request.Request(url, method=method,
                                     headers=dict(entry["request_headers"]))
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            entry.update({"http": r.status,
                          "response_headers": {k: v for k, v in
                                               r.headers.items() if
                                               k.lower() in (
                                                   "content-type",
                                                   "content-length",
                                                   "content-range", "date",
                                                   "vary")},
                          "body_len": len(body),
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


# ---- step 1: the publication graph, turtle ----
r_pub = call("P3_publication_turtle", PUB,
             headers={"User-Agent": UA, "Accept": "text/turtle"},
             notes="PASS-2 measured this negotiation 200; now parsed")
g = rdflib.Graph()
identity = {"pub_uri": PUB}
try:
    g.parse(data=r_pub["_body"].decode("utf-8", "replace"),
            format="turtle", publicID=PUB)
    r_pub["typed_state"] = "LIVE_RDF_TURTLE_PARSED"
    r_pub["triples"] = len(g)
    identity["triples_in_publication_graph"] = len(g)
    identity["predicates"] = sorted(
        str(p).split("/")[-1] for _, p, _ in g)[:40]

    # ---- identity model ----
    s = rdflib.URIRef(PUB) if (rdflib.URIRef(PUB), None, None) in g or \
        (None, None, rdflib.URIRef(PUB)) in g else None
    if s is None:
        # the resource may be described under a canonical @id variant
        subj_counts = {}
        for sp, _, _ in g:
            subj_counts[str(sp)] = subj_counts.get(str(sp), 0) + 1
        pick = sorted(subj_counts.items(), key=lambda kv: -kv[1])
        identity["subject_counts_top"] = pick[:6]
        s = rdflib.URIRef(pick[0][0]) if pick else None
        identity["canonical_subject"] = str(s) if s is not None else None

    def objs(pred_local):
        out = []
        for p in set(g.predicates(None, None)):
            if str(p).lower().endswith(pred_local.lower()) or \
               pred_local.lower() in str(p).lower():
                out += [o for o in g.objects(s, p)] if s is not None else []
        seen, res = set(), []
        for o in out:
            k = (str(o), getattr(o, "language", None))
            if k not in seen:
                seen.add(k)
                res.append(o)
        return res

    for o in objs("title"):
        val = str(o)
        titles = identity.setdefault("titles", [])
        titles.append({"lang": getattr(o, "language", None), "len": len(val),
                       "sha256_12": hashlib.sha256(
                           val.encode()).hexdigest()[:12],
                       "matches_patentbear": hashlib.sha256(
                           val.encode()).hexdigest()[:12] ==
                       SEALED["title_sha256_12"],
                       "preview": val[:120]})
    for o in objs("abstract"):
        val = str(o)
        ab = identity.setdefault("abstracts", [])
        ab.append({"lang": getattr(o, "language", None), "len": len(val),
                   "sha256_12": hashlib.sha256(
                       val.encode()).hexdigest()[:12],
                   "preview": val[:120]})
    identity["abstract_len_matches_patentbear_718"] = any(
        a["len"] == SEALED["abstract_len"] for a in
        identity.get("abstracts", []))
    identity["cross_provider_verdict"] = (
        "CROSS_PROVIDER_TITLE_FINGERPRINT_MATCH" if any(
            t["matches_patentbear"] for t in identity.get("titles", []))
        else "CROSS_PROVIDER_TITLE_MISMATCH_UNADJUDICATED" if
        identity.get("titles")
        else "NO_TITLE_IN_GRAPH")
    for field in ("applicationReference", "priorities", "publicationDate",
                  "publicationNumber", "publicationKind",
                  "publicationAuthority", "granted", "classification"):
        vals = objs(field)
        if vals:
            identity[field] = [str(v)[:120] for v in vals][:8]
    identity["family_uris"] = [str(v) for v in objs("familyMemberOf")][:6] \
        or [str(v) for v in objs("family")][:6]
    identity["citation_uris"] = [str(v) for v in
                                 objs("citesPatentPublication")][:8]

    # doc representations: any object/subject URI containing pdf|xml|doc
    alluris = set()
    for a, b, c in g:
        for term in (a, b, c):
            t = str(term)
            if t.startswith("http") and re.search(
                    r"(pdf|xml|doc|represent)", t, re.I):
                alluris.add(t)
    identity["representation_uris"] = sorted(alluris)[:10]
except Exception as ex:
    r_pub["typed_state"] = "TURTLE_PARSE_FAILED: %s" % type(ex).__name__
    identity["parse_error"] = str(ex)[:300]

# ---- step 2: family object (content-bearing proof of the membership edge) ----
fam_uris = [u for u in identity.get("family_uris", [])
            if u.startswith("http")]
if fam_uris:
    r_fam = call("P3_family_turtle", fam_uris[0],
                 headers={"User-Agent": UA, "Accept": "text/turtle"},
                 notes="familyMemberOf object under turtle negotiation")
    gf = rdflib.Graph()
    try:
        gf.parse(data=r_fam["_body"].decode("utf-8", "replace"),
                 format="turtle", publicID=fam_uris[0])
        r_fam["typed_state"] = "LIVE_RDF_TURTLE_PARSED"
        r_fam["triples"] = len(gf)
        members = sorted({str(o) for _, p, o in gf
                          if "member" in str(p).lower()})[:12]
        r_fam["family_members_sample"] = members
        r_fam["family_member_count_measured"] = len(members)
    except Exception as ex:
        r_fam["typed_state"] = "TURTLE_PARSE_FAILED: %s" % type(ex).__name__

# ---- step 3: Range-bounded primary-document fetches ----
for i, du in enumerate(identity.get("representation_uris", [])[:3]):
    rd = call("P3_document_range_fetch_%d" % i, du,
              headers={"User-Agent": UA, "Range": "bytes=0-255"},
              notes="Tier-1 primary text, Range-bounded")
    rd["typed_state"] = ("LIVE_CONTENT_BEARING_BYTES" if
                         rd.get("http") in (200, 206) and
                         rd.get("body_len", 0) > 0 else
                         "HTTP_%s" % rd.get("http"))

# ---- step 4: the discovery/search endpoint (operator warming lead) ----
r_srch = call("P3_epo_lod_search", PUB.rsplit("/publication/", 1)[0] +
              "/search",
              params={"q": "8968233"},
              headers={"User-Agent": UA, "Accept": "application/json"},
              notes="the operator's 'index warming' discovery endpoint "
                    "(typed transient state, never absence)")
try:
    sjs = json.loads(r_srch.get("_body", b"") or b"null")
except Exception:
    sjs = None
if r_srch.get("http") == 200 and sjs:
    r_srch["typed_state"] = "LIVE_SEARCH_JSON"
    r_srch["results_preview"] = json.dumps(sjs)[:600]
else:
    r_srch["typed_state"] = "HTTP_%s_%s" % (r_srch.get("http"),
                                            r_srch.get("error", ""))
    r_srch["body_excerpt"] = (r_srch.get("_body", b"") or
                              b"")[:300].decode("utf-8", "replace")

LEDGER["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
LEDGER["summary"] = {"identity": identity,
                     "sealed_f10_reference": SEALED}
import os
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w") as f:
    json.dump(LEDGER, f, indent=1, ensure_ascii=False)
print(json.dumps(LEDGER["summary"], indent=1, ensure_ascii=False)[:5000])
print("ledger ->", OUT)

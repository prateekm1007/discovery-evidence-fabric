#!/usr/bin/env python3
"""R500 PASS-5 (final) — locate the publication resource via the PROVEN
SPARQL protocol channel.

Measured so far: /query protocol LIVE (GET+POST sparql-json); the
/data/publication/US/8968233B2 endpoint answers 200-turtle but is an Elda
ListEndpoint with items=rdf:nil (soft-empty page — not existence evidence,
Art. XXI.3 discipline); lod.apps.epo.org direct 403 (internal host;
data.epo.org is the front door); the lda#notice measures 'Provided by the
European Patent Office.'

This pass, via exact-IRI lookups (no store scans):
  1. SELECT ?p ?o over candidate /resource/ IRIs (Elda convention: /data/
     = endpoint, /resource/ = the described thing) on 3 host/path shapes;
  2. data-URI matrix under turtle: number-without-kind, number/kind split,
     _view=all, _metadata=all — an items list != rdf:nil proves the right
     key shape;
  3. on ANY hit: extract the identity model + fingerprints vs the R498
     PatentBear measurement (title_sha256_12=3712021fb352, abstract_len=718).

KEYLESS. ZERO PatentBear debits."""
from __future__ import annotations

import hashlib
import json
import time
import urllib.parse
import urllib.request
import urllib.error

import rdflib

REPO = "/home/z/my-project/hf_space"
OUT = REPO + "/R500/R500_FREE_SOURCE_PROBE_PASS5.json"
UA = "toscanini-rbg-probe/1.0 (keyless epistemic measurement; operator-directed)"
QEND = "https://data.epo.org/linked-data/query"
SEALED = {"record_id": "US8968233B2",
          "title_sha256_12": "3712021fb352", "abstract_len": 718}
LEDGER = {"probe": "R500_FREE_SOURCE_PROBE_PASS5",
          "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
          "debits_spent": 0, "rounds": []}


def sparql(name, query, timeout=70, notes=""):
    entry = {"name": name, "kind": "sparql_GET", "utc": time.strftime(
        "%H:%M:%SZ", time.gmtime()), "notes": notes}
    q = urllib.parse.urlencode({"query": query})
    try:
        req = urllib.request.Request(
            QEND + "?" + q, headers={
                "User-Agent": UA,
                "Accept": "application/sparql-results+json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
        entry["http"] = 200
        j = json.loads(body)
        binds = j.get("results", {}).get("bindings", [])
        entry["bindings"] = len(binds)
        entry["rows"] = [{k: v.get("value") for k, v in b.items()}
                         for b in binds[:8]]
        entry["typed_state"] = "LIVE_%d_BINDINGS" % len(binds) if binds \
            else "LIVE_ZERO_BINDINGS"
    except urllib.error.HTTPError as e:
        entry["http"] = e.code
        entry["typed_state"] = "HTTP_%s" % e.code
    except Exception as e:
        entry["http"] = None
        entry["error"] = "%s: %s" % (type(e).__name__, str(e)[:160])
        entry["typed_state"] = "ERROR_TRANSIENT"
    LEDGER["rounds"].append(entry)
    return entry


def get_turtle(name, url, notes=""):
    entry = {"name": name, "url": url, "utc": time.strftime(
        "%H:%M:%SZ", time.gmtime()), "notes": notes}
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": UA, "Accept": "text/turtle"})
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read()
            entry["http"] = r.status
    except urllib.error.HTTPError as e:
        body = b""
        try:
            body = e.read()
        except Exception:
            pass
        entry["http"] = e.code
    except Exception as e:
        entry["http"] = None
        entry["error"] = "%s: %s" % (type(e).__name__, str(e)[:160])
        entry["typed_state"] = "ERROR_TRANSIENT"
        LEDGER["rounds"].append(entry)
        return entry, b""
    entry["body_len"] = len(body)
    entry["body_sha256_12"] = hashlib.sha256(body).hexdigest()[:12]
    items_not_nil = b"nil" not in body[:2000] or b"items" not in body
    entry["typed_state"] = "HTTP_%s" % entry["http"]
    LEDGER["rounds"].append(entry)
    return entry, body


# ---- 1: exact-IRI lookups on the proven protocol endpoint ----
CANDIDATES = [
    "https://data.epo.org/linked-data/resource/publication/US/8968233B2",
    "http://data.epo.org/linked-data/resource/publication/US/8968233B2",
    "https://lod.apps.epo.org/linked-data/resource/publication/US/8968233B2",
    "https://data.epo.org/linked-data/resource/publication/US/8968233/B2",
]
hits = []
for c in CANDIDATES:
    r = sparql("P5_resource_iri_lookup",
               "SELECT ?p ?o WHERE { <%s> ?p ?o } LIMIT 60" % c,
               notes="exact-IRI lookup, no scan")
    if r.get("bindings"):
        hits.append({"iri": c, "rows": r["rows"]})

# ---- 2: data-URI matrix under turtle ----
MATRIX = [
    ("no_kind", "https://data.epo.org/linked-data/data/publication/US/8968233"),
    ("kind_split", "https://data.epo.org/linked-data/data/publication/US/8968233/B2"),
    ("view_all", "https://data.epo.org/linked-data/data/publication/US/8968233B2?_view=all"),
    ("metadata_all", "https://data.epo.org/linked-data/data/publication/US/8968233B2?_metadata=all"),
]
best = None
for tag, url in MATRIX:
    e, body = get_turtle("P5_data_matrix_%s" % tag, url,
                         notes="turtle negotiation; items!=rdf:nil proves "
                               "the key shape")
    if e.get("http") == 200 and body:
        has_items = (b"items" in body) and (b"nil" not in body)
        e["items_non_nil"] = has_items
        if has_items and best is None:
            best = (tag, url, body)

# ---- 3: identity extraction on any hit ----
identity = {}
if hits:
    src = hits[0]
    identity["via_sparql_iri"] = src["iri"]
    identity["identity_rows"] = src["rows"][:8]
    blob = json.dumps(src["rows"])
    titles = []
    for row in src["rows"]:
        for k, v in row.items():
            if "title" in k.lower() and isinstance(v, str) and v.strip():
                fp = hashlib.sha256(v.encode()).hexdigest()[:12]
                titles.append({"field": k, "len": len(v), "sha256_12": fp,
                               "matches_patentbear": fp ==
                               SEALED["title_sha256_12"],
                               "preview": v[:120]})
    identity["titles"] = titles
    identity["cross_provider_verdict"] = (
        "CROSS_PROVIDER_TITLE_FINGERPRINT_MATCH" if any(
            t["matches_patentbear"] for t in titles)
        else "CROSS_PROVIDER_TITLE_MISMATCH_UNADJUDICATED" if titles
        else "NO_TITLE_FIELD_IN_ROWS")
elif best:
    tag, url, body = best
    identity["via_data_matrix"] = {"tag": tag, "url": url}
    g = rdflib.Graph()
    try:
        g.parse(data=body.decode("utf-8", "replace"), format="turtle",
                publicID=url)
        identity["triples"] = len(g)
        node = None
        for s in set(g.subjects()):
            preds = {str(p).lower() for p in g.predicates(s, None)}
            if any("title" in p or "abstract" in p for p in preds):
                node = s
                break
        if node is not None:
            identity["identity_node"] = str(node)
            titles, abstracts = [], []
            for p, o in g.predicate_objects(node):
                pl, val = str(p).lower(), str(o)
                if "title" in pl:
                    fp = hashlib.sha256(val.encode()).hexdigest()[:12]
                    titles.append({"lang": getattr(o, "language", None),
                                   "pred": pl, "len": len(val),
                                   "sha256_12": fp,
                                   "matches_patentbear": fp ==
                                   SEALED["title_sha256_12"],
                                   "preview": val[:120]})
                if "abstract" in pl:
                    abstracts.append({"lang": getattr(o, "language", None),
                                      "pred": pl, "len": len(val),
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
            for field in ("applicationReference", "priority",
                          "publicationDate", "publicationKind",
                          "publicationAuthority", "familyMemberOf",
                          "citesPatentPublication", "classification"):
                vals = [str(o) for p, o in g.predicate_objects(node)
                        if field.lower() in str(p).lower()]
                if vals:
                    identity[field] = sorted(set(vals))[:6]
    except Exception as ex:
        identity["parse_error"] = "%s: %s" % (type(ex).__name__,
                                              str(ex)[:160])
else:
    identity = {
        "status": "PUBLICATION_RESOURCE_UNRESOLVED_THIS_RUN",
        "note": "protocol LIVE; exact-IRI candidates and key-shape matrix "
                "all typed zero/empty — the item-level lookup stays OPEN "
                "with the operator's measured claim held as "
                "OPERATOR_MEASURED_UNREPRODUCED_THIS_ENVIRONMENT (Art. "
                "XXIV: neither confirmed nor refuted here)"}

LEDGER["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
LEDGER["summary"] = {"identity": identity, "sealed_f10_reference": SEALED}
import os
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w") as f:
    json.dump(LEDGER, f, indent=1, ensure_ascii=False)
print(json.dumps(LEDGER["summary"], indent=1, ensure_ascii=False)[:4000])
print("ledger ->", OUT)

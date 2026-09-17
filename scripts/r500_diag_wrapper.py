#!/usr/bin/env python3
"""R500 diagnostic — dump the Elda wrapper triples and follow its routing
objects (hasPart / vocab#page / vocab#first / extendedMetadataVersion /
lda#notice) to locate the real publication description node."""
import hashlib
import json
import time
import urllib.request
import urllib.error

import rdflib

UA = "toscanini-rbg-probe/1.0 (keyless epistemic measurement)"
import sys
PUB = sys.argv[1] if len(sys.argv) > 1 else \
    "https://data.epo.org/linked-data/data/publication/US/8968233B2"


def get(url):
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": UA, "Accept": "text/turtle"})
        with urllib.request.urlopen(req, timeout=45) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        try:
            return e.code, e.read()
        except Exception:
            return e.code, b""
    except Exception as e:
        return None, str(e).encode()


st, body = get(PUB)
print("wrapper:", st, len(body), "bytes")
g = rdflib.Graph()
g.parse(data=body.decode("utf-8", "replace"), format="turtle", publicID=PUB)
print("--- wrapper triples (%d) ---" % len(g))
for s, p, o in sorted(g, key=lambda t: str(t[1])):
    print(" ", str(s).split("/")[-1][:60], "|",
          str(p).split("/")[-1][:40], "|",
          str(o)[:110])

# follow routing objects
targets = set()
for s, p, o in g:
    pl, ol = str(p), str(o)
    if any(k in pl for k in ("hasPart", "page", "first", "MetadataVersion",
                             "notice")) and ol.startswith("http"):
        targets.add(ol)
print("--- routing targets ---")
for t in sorted(targets)[:6]:
    st2, b2 = get(t)
    info = ""
    if st2 == 200:
        try:
            g2 = rdflib.Graph()
            g2.parse(data=b2.decode("utf-8", "replace"), format="turtle",
                     publicID=t)
            preds = sorted({str(p).split("/")[-1] for _, p, _ in g2})
            info = "triples=%d preds=%s" % (len(g2), preds[:14])
        except Exception as ex:
            info = "parse-fail %s" % type(ex).__name__
    print(" ", st2, t[:120], info)

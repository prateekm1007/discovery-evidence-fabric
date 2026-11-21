#!/usr/bin/env python3
"""r115_d2_stage_a_corpus.py — the harder-corpus prereg's stage A:
fresh post-cutoff items fetched from Crossref (read-only, polite pool,
zero quota) under the SIX preregistered query terms; mechanical
round-robin selection; eligibility = JATS-stripped abstract >= 800
chars, DOI not in the r110 corpus, title present. Misses typed OUT.
The selection is model-free (relevance order, round-robin) — the
anti-tuning clause."""
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "eval" / "r115_d2_harder_raw"
RAW.mkdir(exist_ok=True)
OUT = RAW / "items.jsonl"
LOG = RAW / "fetch_log.json"
UA = ("r115s1-harder-corpus/1.0 (mailto:builder-r115s1@users.noreply."
      "github.com)")
ABSTRACT_MIN = 800  # preregistered
TERMS = ["electrocatalyst degradation",
         "perovskite solar cell stability",
         "lithium battery cathode interface",
         "polymer membrane fouling",
         "enzyme immobilization stability",
         "photocatalyst mechanism"]
ROWS = 25  # preregistered
TARGET = 30
JATS = re.compile(r"</?jats:[a-z]+>")


def norm(s):
    return set(re.findall(r"[a-z0-9]+", (s or "").lower()))


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def jats_strip(a):
    return JATS.sub("", a or "").replace("\n", " ").strip()


r110_dois = set()
src = REPO / "eval" / "r110_d3_corpus_source" / "fetched_abstracts.jsonl"
if src.exists():
    for line in src.read_text(encoding="utf-8").strip().split("\n"):
        d = json.loads(line)
        if d.get("doi"):
            r110_dois.add(d["doi"].lower())

pool = {}
log = []
for t in TERMS:
    q = urllib.parse.quote(t)
    url = (f"https://api.crossref.org/works?query.bibliographic={q}"
           f"&filter=from-pub-date:2025-09-01,type:journal-article,"
           f"has-abstract:true&rows={ROWS}"
           "&select=DOI,title,abstract,container-title,published,"
           "publisher,is-referenced-by-count")
    try:
        d = fetch(url)
    except Exception as e:  # noqa: BLE001
        log.append({"term": t, "typed": f"FETCH_FAIL: {e}"[:120]})
        print(t, "FETCH_FAIL", str(e)[:60], flush=True)
        continue
    elig = []
    for w in d.get("message", {}).get("items", []):
        doi = (w.get("DOI") or "").lower()
        title = (w.get("title") or [""])[0]
        ab = jats_strip((w.get("abstract") or ""))
        if not title or not doi or doi in r110_dois:
            continue
        if len(ab) < ABSTRACT_MIN:
            continue
        elig.append({"doi": doi, "title": title, "abstract": ab,
                     "container": (w.get("container-title") or [""])[0],
                     "publisher": w.get("publisher", ""),
                     "issued": (w.get("published", {})
                                .get("date-parts", [[None]])[0][0])})
    pool[t] = elig
    log.append({"term": t, "eligible": len(elig)})
    print(t, "eligible:", len(elig), flush=True)
    time.sleep(1)

items, seen = [], set()
round_i = 0
while len(items) < TARGET:
    took = 0
    for t in TERMS:
        if len(items) >= TARGET:
            break
        cand = None
        while pool.get(t):
            cand = pool[t].pop(0)
            if cand["doi"] not in seen:
                break
            cand = None
        if cand:
            seen.add(cand["doi"])
            nn = "%02d" % (len(items) + 1)
            items.append({"item_id": f"hc-{nn}", "query_term": t,
                          **cand})
            took += 1
    if took == 0:
        break
    round_i += 1

OUT.write_text("\n".join(json.dumps(x) for x in items),
               encoding="utf-8")
log.append({"typed": "SELECTED", "n": len(items),
            "rounds": round_i,
            "per_term": {t: sum(1 for x in items if x["query_term"] == t)
                         for t in TERMS}})
LOG.write_text(json.dumps(log, indent=1), encoding="utf-8")
print("SELECTED", len(items), "items ->", OUT, flush=True)

#!/usr/bin/env python3
"""r110_d3_stage_a_refetch.py — the instrument prereg's stage A: the
source abstracts re-fetched from Crossref BY TITLE (read-only, the
polite pool, zero quota). Per item: the fetched DOI/title/abstract
(JATS-stripped)/publisher/date + the title-match score; a match below
the preregistered 0.8 token-overlap types the item OUT (fail-closed —
a wrong source is worse than a missing one)."""
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CORPUS = REPO / "eval" / "r106_score9_corpus_postcutoff" / "sampled_items.jsonl"
OUTDIR = REPO / "eval" / "r110_d3_corpus_source"
OUT = OUTDIR / "fetched_abstracts.jsonl"
OUTDIR.mkdir(exist_ok=True)
UA = ("r110s1-instrument/1.0 (mailto:builder-r109s1@users.noreply."
      "github.com)")
MATCH_MIN = 0.8  # the preregistered normalized token-overlap floor
JATS = re.compile(r"</?jats:[a-z]+>")


def norm(s):
    return set(re.findall(r"[a-z0-9]+", (s or "").lower()))


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


items = [json.loads(l) for l in
         CORPUS.read_text(encoding="utf-8").strip().split("\n")]
out, misses = [], []
for it in items:
    title = it["title_for_record"]
    q = urllib.parse.quote(title)
    try:
        d = fetch(f"https://api.crossref.org/works?query.title={q}"
                  "&rows=3&select=DOI,title,abstract,container-title,"
                  "published,publisher,is-referenced-by-count")
    except Exception as e:  # noqa: BLE001
        misses.append({"item_id": it["item_id"],
                       "typed": f"FETCH_FAIL: {type(e).__name__}: "
                                f"{str(e)[:80]}"})
        print(it["item_id"], "FETCH_FAIL", str(e)[:60])
        time.sleep(1)
        continue
    tn = norm(title)
    best, best_score = None, 0.0
    for w in d.get("message", {}).get("items", []):
        ft = (w.get("title") or [""])[0]
        fn = norm(ft)
        score = (len(tn & fn) / max(1, len(tn | fn)))  # Jaccard
        if score > best_score:
            best, best_score = w, score
    if best is None or best_score < MATCH_MIN:
        misses.append({"item_id": it["item_id"], "typed":
                       f"TITLE_MATCH_FAIL (best {best_score:.2f})"})
        print(it["item_id"], "MATCH_FAIL", round(best_score, 2))
        time.sleep(1)
        continue
    ab = best.get("abstract") or ""
    ab = JATS.sub("", ab).replace("\n", " ").strip()
    pub = (best.get("published") or {}).get("date-parts", [[None]])
    rec = {
        "item_id": it["item_id"],
        "title_for_record": title,
        "fetched_doi": best.get("DOI"),
        "fetched_title": (best.get("title") or [""])[0],
        "title_match_jaccard": round(best_score, 3),
        "abstract_chars": len(ab),
        "abstract": ab,
        "publisher": best.get("publisher"),
        "published": pub[0] if pub else None,
        "is_referenced_by_count": best.get("is-referenced-by-count"),
        "fetched_at": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"),
    }
    if not ab:
        misses.append({"item_id": it["item_id"],
                       "typed": "NO_ABSTRACT_IN_CROSSREF"})
        print(it["item_id"], "NO_ABSTRACT")
        time.sleep(1)
        continue
    out.append(rec)
    print(it["item_id"], "OK", round(best_score, 2),
          f"{len(ab)} chars")
    time.sleep(1)

OUT.write_text("\n".join(json.dumps(r, ensure_ascii=False)
                         for r in out) + ("\n" if out else ""),
               encoding="utf-8")
(OUTDIR / "fetch_misses.json").write_text(
    json.dumps({"record": "R110_D3_FETCH_MISSES/1.0.0",
                "match_floor": MATCH_MIN, "n_out": len(out),
                "n_misses": len(misses), "misses": misses},
               indent=1, ensure_ascii=False) + "\n")
print(f"fetched {len(out)}/30; misses {len(misses)} (typed)")

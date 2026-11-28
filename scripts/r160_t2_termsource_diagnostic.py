#!/usr/bin/env python3
"""r160s1 (claim c-0266, follow-up diagnostic): WHY did v2 score 0/18 on
TRUE positives — measure counterfactual term sources, typed as DIAGNOSTIC
(not an instrument):
  T-A: v2 blob + FULL uncapped km terms (all 4+ char words, stoplist)
  T-B: v2 blob + terms from the corpus item's main_inspiration text
  T-C: v2 blob + terms from the corpus finegrained_hypothesis
  T-D: title-similarity support: resolved title vs the corpus inspiration
       title (the mapping similarity itself, for reference)
No instrument changes; the numbers feed the NEXT prereg's term-source
choice."""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path("/home/z/my-project/discovery-evidence-fabric")
CAL = REPO / "eval" / "r160_t2_calibration.json"
CORPUS = REPO / "eval" / "r106_score9_corpus_postcutoff" / "sampled_items.jsonl"
OUT = REPO / "eval" / "r160_t2_termsource_diagnostic.json"

UA = "p5-t2-calibration/1.0 (mailto:research@example.invalid)"

spec_ns = {"__file__": str(REPO / "scripts" / "r158_p5_tokenrouter_run.py")}
exec((REPO / "scripts" / "r158_p5_tokenrouter_run.py")
     .read_text().split('if __name__')[0], spec_ns)  # noqa: S102
mechanism_terms = spec_ns["mechanism_terms"]
DISTINCT_STOP = spec_ns["DISTINCT_STOP"]


def norm_title(s: str) -> str:
    s = (s or "").casefold()
    s = re.sub(r"[-\u2013\u2014_]", " ", s)
    return re.sub(r"[^a-z0-9 ]+", " ", re.sub(r"\s+", " ", s)).strip()


def terms_uncapped(km: str) -> list:
    ws = [w.lower() for w in re.findall(r"[A-Za-z\-]{4,}", km or "")
          if w.lower() not in DISTINCT_STOP]
    seen, out = set(), []
    for w in ws:
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out  # NO [:6] cap


def terms_from_text(txt: str) -> list:
    return terms_uncapped(txt)


def expand(ts: list) -> list:
    out = []
    for t in ts:
        out.append(t)
        if len(t) >= 5 and t.endswith("s"):
            out.append(t[:-1])
        if "-" in t:
            out.append(t.replace("-", " "))
    seen, dedup = set(), []
    for t in out:
        if t not in seen:
            seen.add(t)
            dedup.append(t)
    return dedup


def main() -> int:
    cal = json.loads(CAL.read_text())
    detail = cal["detail"]
    corpus = {json.loads(l)["item_id"]: json.loads(l)
              for l in CORPUS.read_text().splitlines() if l.strip()}
    rows = []
    counts = {"A": 0, "B": 0, "C": 0, "n": 0}
    for d in detail:
        if not d.get("doi") or d.get("old") == "work-fetch-error":
            continue
        iid = d["item_id"]
        citem = corpus.get(iid, {})
        km = d.get("km", "")
        insp_txt = " ".join(
            p.get("title", "") for p in
            ((citem.get("served") or {}).get("inspiration_papers") or []))
        insp_txt += " " + str((citem.get("served") or {}).get(
            "main_inspiration") or "")
        fgh = str((citem.get("ground_truth") or {}).get(
            "finegrained_hypothesis") or "")
        url = f"https://api.crossref.org/works/{urllib.parse.quote(d['doi'])}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=45) as r:
                msg = json.loads(r.read().decode()).get("message", {})
        except Exception:  # noqa: BLE001
            continue
        time.sleep(0.7)
        title = " ".join(msg.get("title") or [])
        abstract = re.sub(r"<[^>]+>", " ", str(msg.get("abstract") or ""))
        ct = msg.get("container-title")
        container = " ".join(str(x) for x in ct if x) if isinstance(
            ct, list) else str(ct or "")
        subject = " ".join(str(x) for x in (msg.get("subject") or []) if x)
        blob = norm_title(f"{title} {abstract} {subject} {container}")
        res = {}
        for tag, ts in (("A", expand(terms_uncapped(km))),
                        ("B", expand(terms_from_text(insp_txt))),
                        ("C", expand(terms_from_text(fgh)))):
            hits = sum(1 for t in ts if norm_title(t) in blob)
            res[tag] = hits
        has_abstract = len(abstract.strip()) > 40
        rows.append({"item_id": iid, "doi": d["doi"],
                     "title": title[:90], "has_abstract": has_abstract,
                     "blob_len": len(blob),
                     "hits_A_full_km": res["A"],
                     "hits_B_inspiration": res["B"],
                     "hits_C_finegrained": res["C"]})
        counts["n"] += 1
        for tag in "ABC":
            if res[tag] >= 2:
                counts[tag] += 1

    n = counts["n"]
    out = {
        "record": "R160_T2_TERMSOURCE_DIAGNOSTIC/1.0.0",
        "claim": "c-0266",
        "session": "builder-r160s1",
        "typed_as": "DIAGNOSTIC — not an instrument; feeds the next "
                    "prereg's term-source choice",
        "n_true_positives": n,
        "accept_at_2hits": {
            "A_full_uncapped_generator_km": counts["A"],
            "B_corpus_inspiration_text": counts["B"],
            "C_corpus_finegrained_hypothesis": counts["C"],
        },
        "rates": {k: round(v / n, 3) for k, v in counts.items()
                  if k != "n"},
        "abstract_availability": round(
            sum(1 for r in rows if r["has_abstract"]) / n, 3) if n else 0,
        "rows": rows,
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "rows"},
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

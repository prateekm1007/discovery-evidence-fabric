#!/usr/bin/env python3
"""r160s1 (claim c-0266): the T2-resolver calibration check (DIR 4).

WHY (from committed bytes, eval/r158_p5_tokenrouter_run.json):
42 citations, 0 unparsed, 7 transport errors, 0 supporting,
35 resolved-but-thin — real Crossref-resolved papers rejected by the
frozen v1 bar (>=2 raw mechanism-term substrings over Crossref
title+abstract). Title-only blobs (no abstract on most Crossref
records), no stemming, no hyphen/case normalization.

DESIGN (pre-registered before running, Art. 9/14):
  TRUE POSITIVES: each corpus item's own inspiration_papers titles
  (the papers the target actually built on — the corpus's ground
  truth) are mapped to DOIs via the Crossref bibliographic query,
  accepted only when the returned title matches the corpus title at
  normalized token-set similarity >= 0.82 (typed threshold; else the
  pair is typed UNMAPPED and excluded).
  SENSITIVITY_OLD: the FROZEN v1 resolver (imported from the r158
  module, byte-identical machinery) over the mapped true DOIs, with
  each item's own committed key_mechanism — expected ~0 (the finding).
  SENSITIVITY_V2: the PRE-REGISTERED v2 spec — normalization:
  casefold; [-–—_] -> space; whitespace collapse; plural-fold
  (strip one trailing 's' when len >= 5) as ADDITIONAL candidate
  terms; blob = title + subtitle + abstract (tags stripped) +
  subject + container-title; the support bar stays >= 2 distinct
  term hits (unchanged bar semantics).
  NEGATIVE CONTROLS (specificity): item i's true DOIs evaluated with
  item (i+1 mod n)'s key_mechanism (real paper, wrong mechanism) —
  v2 must stay ~0; the OLD resolver is reported on the same pairs.
  ACCEPTANCE (typed): v2 sensitivity >= 0.5 AND v2 negative-control
  support == 0 AND old sensitivity < 0.2 => "v1 false-negative-
  dominant; v2 restores T2 discriminating power" (the SPECTER2-gate
  class confirmed/recalibrated). Any other outcome is typed as-is.

Zero quota burn: Crossref public API only; no P5 corpus re-run; no
generator calls. The fresh-sealed-set re-run stays the auditor's act.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path("/home/z/my-project/discovery-evidence-fabric")
RUN = REPO / "eval" / "r158_p5_tokenrouter_run.json"
CORPUS = REPO / "eval" / "r106_score9_corpus_postcutoff" / "sampled_items.jsonl"
OUT = REPO / "eval" / "r160_t2_calibration.json"

spec = importlib.util.spec_from_file_location(
    "r158mod", REPO / "scripts" / "r158_p5_tokenrouter_run.py")
r158 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r158)

UA = "p5-t2-calibration/1.0 (mailto:research@example.invalid)"


def norm_title(s: str) -> str:
    s = (s or "").casefold()
    s = re.sub(r"[-\u2013\u2014_]", " ", s)
    return re.sub(r"[^a-z0-9 ]+", " ", re.sub(r"\s+", " ", s)).strip()


def tokset(s: str) -> set:
    return {w for w in norm_title(s).split() if len(w) > 2}


def sim(a: str, b: str) -> float:
    A, B = tokset(a), tokset(b)
    if not A or not B:
        return 0.0
    return len(A & B) / min(len(A), len(B))


def crossref_map(title: str) -> dict:
    """Map a corpus inspiration title to a DOI (typed threshold)."""
    q = urllib.parse.quote(re.sub(r"\s+", " ", title).strip()[:240])
    url = (f"https://api.crossref.org/works?query.bibliographic={q}"
           f"&rows=5&select=DOI,title,author,issued")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=45) as r:
            items = json.loads(r.read().decode()).get("message", {}).get(
                "items", [])
        best, best_s = None, 0.0
        for it in items:
            t = " ".join(it.get("title") or [])
            s = sim(title, t)
            if s > best_s:
                best, best_s = it, s
        if best and best_s >= 0.82:
            return {"doi": best["DOI"], "matched_title":
                    " ".join(best.get("title") or [])[:160],
                    "similarity": round(best_s, 3), "mapped": True}
        return {"mapped": False, "best_similarity": round(best_s, 3),
                "best_title": (" ".join(best.get("title") or [])
                               [:120] if best else None)}
    except Exception as e:  # noqa: BLE001 — typed degradation
        return {"mapped": False, "error": f"{type(e).__name__}: {str(e)[:120]}"}


# --- the pre-registered v2 resolver -------------------------------------
def _expand_terms(km: str) -> list:
    base = r158.mechanism_terms(km)
    out = []
    for t in base:
        out.append(t)
        if len(t) >= 5 and t.endswith("s"):
            out.append(t[:-1])
    # de-hyphenated variants (normalization handles the blob side too)
    for t in list(base):
        if "-" in t:
            out.append(t.replace("-", " "))
    seen, dedup = set(), []
    for t in out:
        if t not in seen:
            seen.add(t)
            dedup.append(t)
    return dedup


def _container(msg: dict) -> str:
    ct = msg.get("container-title")
    if isinstance(ct, list):
        return " ".join(str(x) for x in ct if x)
    return str(ct or "")


def resolve_v2(doi: str, km: str, msg: dict) -> dict:
    title = " ".join(msg.get("title") or [])
    subtitle = " ".join(msg.get("subtitle") or [])
    abstract = re.sub(r"<[^>]+>", " ",
                      str(msg.get("abstract") or ""))
    subject = " ".join(str(x) for x in (msg.get("subject") or [])
                       if x)
    container = _container(msg)
    blob = norm_title(f"{title} {subtitle} {abstract} {subject} {container}")
    terms = _expand_terms(km)
    hits = sum(1 for t in terms if norm_title(t) in blob)
    return {"doi": doi, "hits": hits,
            "supports_claim_as_stated": hits >= 2,
            "blob_len": len(blob), "terms": terms[:8]}


def crossref_work(doi: str) -> dict | None:
    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=45) as r:
            return json.loads(r.read().decode()).get("message", {})
    except Exception as e:  # noqa: BLE001
        return None


def main() -> int:
    run = json.loads(RUN.read_text())
    per = run["per_item"]
    corpus = {json.loads(l)["item_id"]: json.loads(l)
              for l in CORPUS.read_text().splitlines() if l.strip()}
    usage = {"crossref_search": 0, "crossref_work": 0, "old_resolver_http": 0}

    rows, unmapped = [], []
    tps = []  # (item_id, km, doi, corpus_title)
    for iid, it in sorted(per.items()):
        km = (it.get("generation") or {}).get("key_mechanism", "")
        papers = (((corpus.get(iid) or {}).get("served") or {})
                  .get("inspiration_papers") or [])
        for p in papers:
            t = p.get("title") or ""
            m = crossref_map(t)
            usage["crossref_search"] += 1
            time.sleep(1.0)
            if m.get("mapped"):
                tps.append({"item_id": iid, "km": km, "doi": m["doi"],
                            "corpus_title": t[:120],
                            "matched_title": m["matched_title"],
                            "similarity": m["similarity"]})
            else:
                unmapped.append({"item_id": iid, "corpus_title": t[:120],
                                 **{k: v for k, v in m.items()
                                    if k != "mapped"}})
            rows.append({"item_id": iid, "corpus_title": t[:120],
                         "mapping": m})

    # sensitivity: OLD (frozen v1) vs NEW (v2) on the SAME true positives
    old_sup = v2_sup = old_err = 0
    detail = []
    for tp in tps:
        msg = crossref_work(tp["doi"])
        usage["crossref_work"] += 1
        time.sleep(0.7)
        if not msg:
            old_err += 1
            detail.append({**tp, "old": "work-fetch-error", "v2": None})
            continue
        old = r158.resolve_citation(tp["doi"], tp["km"])
        usage["old_resolver_http"] += 1
        v2 = resolve_v2(tp["doi"], tp["km"], msg)
        old_sup += bool(old.get("supports_claim_as_stated"))
        v2_sup += bool(v2["supports_claim_as_stated"])
        detail.append({**tp, "old_sup": old.get("supports_claim_as_stated"),
                       "old_hits": old.get("term_hits"),
                       "v2_sup": v2["supports_claim_as_stated"],
                       "v2_hits": v2["hits"],
                       "v2_title": " ".join(msg.get("title") or [])[:110]})

    # negative controls: real paper, WRONG mechanism (next item's km)
    nctrl = []
    n_sup_v2 = n_sup_old = 0
    for i, tp in enumerate(tps):
        wrong = tps[(i + 1) % len(tps)]["km"]
        msg = crossref_work(tp["doi"])
        usage["crossref_work"] += 1
        time.sleep(0.7)
        if not msg:
            continue
        v2n = resolve_v2(tp["doi"], wrong, msg)
        oldn = r158.resolve_citation(tp["doi"], wrong)
        usage["old_resolver_http"] += 1
        n_sup_v2 += bool(v2n["supports_claim_as_stated"])
        n_sup_old += bool(oldn.get("supports_claim_as_stated"))
        nctrl.append({"item_id": tp["item_id"], "doi": tp["doi"],
                      "wrong_km_of": tps[(i + 1) % len(tps)]["item_id"],
                      "v2_sup": v2n["supports_claim_as_stated"],
                      "v2_hits": v2n["hits"],
                      "old_sup": oldn.get("supports_claim_as_stated")})

    n = len(tps)
    sens_old = round(old_sup / n, 3) if n else None
    sens_v2 = round(v2_sup / n, 3) if n else None
    if sens_old is not None and sens_v2 is not None:
        if sens_v2 >= 0.5 and n_sup_v2 == 0 and sens_old < 0.2:
            verdict = ("CONFIRMED+RECALIBRATED: v1 false-negative-dominant "
                       "(the SPECTER2-gate class); v2 restores "
                       "discriminating power at specificity 0")
        elif sens_v2 >= 0.5 and n_sup_v2 > 0:
            verdict = ("PARTIAL: v2 sensitivity restored but the "
                       "negative controls are NOT clean — tighten v2 "
                       "before any re-run")
        else:
            verdict = ("NOT_RECALIBRATED: v2 does not clear the "
                       "pre-registered acceptance — the bar itself or "
                       "the term expansion needs a next revision")
    else:
        verdict = "UNRESOLVED: no mappable true positives"

    out = {
        "record": "R160_T2_CALIBRATION/1.0.0",
        "claim": "c-0266",
        "session": "builder-r160s1",
        "at": datetime.now(timezone.utc).isoformat(),
        "basis": "committed bytes: eval/r158_p5_tokenrouter_run.json "
                 "(42 citations: 0 unparsed / 7 errors / 0 supporting / "
                 "35 resolved-but-thin) + eval/r106_score9_corpus_"
                 "postcutoff/sampled_items.jsonl (inspiration_papers)",
        "v2_spec_preregistered": {
            "normalization": "casefold; [-\u2013\u2014_]->space; "
                             "whitespace collapse; plural-fold strip one "
                             "trailing 's' (len>=5) as extra candidate "
                             "terms; de-hyphenated variants",
            "blob": "title + subtitle + abstract(tags stripped) + subject "
                    "+ container-title",
            "bar": ">= 2 distinct term hits (unchanged from v1)",
        },
        "true_positive_mapping": {
            "inspiration_papers_seen": len(rows),
            "mapped_dois": n,
            "unmapped": unmapped,
            "threshold": 0.82,
        },
        "sensitivity_old_v1": sens_old,
        "sensitivity_v2": sens_v2,
        "old_transport_errors": old_err,
        "negative_controls": {
            "n": len(nctrl),
            "v2_supporting": n_sup_v2,
            "old_supporting": n_sup_old,
            "rows": nctrl,
        },
        "verdict": verdict,
        "detail": detail,
        "usage": usage,
        "note": "the frozen v1 instrument is NOT modified; v2 is a "
                "pre-registered successor for the NEXT sealed run's "
                "prereg (the auditor seals the fresh set); no P5 "
                "corpus re-run this session",
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print("mapped true positives:", n, "/", len(rows))
    print("sensitivity v1(old):", sens_old, "| v2:", sens_v2)
    print("negative controls: n=", len(nctrl), "v2_sup=", n_sup_v2,
          "old_sup=", n_sup_old)
    print("VERDICT:", verdict)
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

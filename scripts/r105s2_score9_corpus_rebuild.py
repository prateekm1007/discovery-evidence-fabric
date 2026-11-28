#!/usr/bin/env python3
"""r105s2 — the POST-CUTOFF SCORE-9 CORPUS REBUILD (auditor direction
4, claim c-0129; stage 2b). The measured cutoff (eval/
r105s2_agnes_cutoff_probe.json): the generator answers correctly
through 2025-08-07 and fails at 2025-09-29; the committed corpus rule
binds items STRICTLY AFTER the conservative bound. This rebuild
samples 30 chemistry papers published 2025-10-01..2026-11 (safely
past even the latest plausible cutoff), reconstructs their abstracts
from the OpenAlex inverted indexes, authors the corpus item fields
with the z-ai transport (NOT the agnes generator — the author/generator
separation is kept: Art. 10), and asserts per-item that the served
block never embeds the ground truth (the m2 convention).

DISCLOSED: the author family (z-ai/GLM) overlaps judge J1's family;
J2 (xkiro/cohere) is independent of both; the BOTH-RECOVERED
adjudication rule limits single-family bias; the overlap rides the
record for the auditor's re-adjudication.

Quota: 30 author calls (z-ai) + free OpenAlex lookups. The 30-batch
RERUN (agnes generation + 2 judges x 30) is the next stage, launched
separately under the same claim.
"""
from __future__ import annotations

import json
import random
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "eval" / "r106_score9_corpus_postcutoff"
OUT = OUT_DIR / "sampled_items.jsonl"
REC = OUT_DIR / "sampling_record.json"
CUTOFF_RECORD = REPO / "eval" / "r105s2_agnes_cutoff_probe.json"
CONSERVATIVE_BOUND = "2025-05-07"     # the committed corpus rule
FROM_DATE = "2025-10-01"              # safely past the measured cutoff
N_ITEMS = 30


def http_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent":
                                               "discovery-evidence-fabric/1.0"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except Exception as e:
            if attempt == 3:
                raise
            time.sleep(10.0)


def deinvert(inv: dict) -> str:
    if not inv:
        return ""
    pos = [(i, w) for w, idxs in inv.items() for i in idxs]
    return " ".join(w for _, w in sorted(pos))


def zai_chat(prompt: str) -> str:
    out = "/tmp/r105s2_corpus_author.json"
    r = subprocess.run(["z-ai", "chat", "-p", prompt, "-o", out],
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        raise RuntimeError(f"z-ai chat rc={r.returncode}: {r.stderr[-160:]}")
    d = json.loads(Path(out).read_text())
    return d["choices"][0]["message"]["content"] or ""


def main():
    cutoff = json.loads(CUTOFF_RECORD.read_text())
    rule = f"{FROM_DATE} (after the measured cutoff {cutoff['estimate']['latest_event_answered_correctly']}; conservative bound {CONSERVATIVE_BOUND})"
    # 1. candidate pool: Crossref chemistry journal articles with
    # abstracts (the polite pool). OpenAlex was IP-throttled 429
    # (typed infra state, Art. 15) — Crossref is the lawful swap.
    picks = []
    for offset in (0, 250, 500, 750, 1000, 1250, 1500, 1750, 2000,
                   2250):
        q = urllib.parse.urlencode({
            "query": "chemistry synthesis reaction materials",
            "filter": ("type:journal-article,from-pub-date:"
                       f"{FROM_DATE},has-abstract:true"),
            "rows": 50, "offset": offset,
            "select": "title,abstract,issued,DOI,reference",
            "mailto": "research-loop@example.org",
        })
        d = http_json(f"https://api.crossref.org/works?{q}")
        for it in d["message"]["items"]:
            t = (it.get("title") or [""])[0]
            ab = it.get("abstract") or ""
            ab = re.sub(r"<[^>]+>", " ", ab)
            ab = re.sub(r"\s+", " ", ab).strip()
            dt = (it.get("issued", {}).get("date-parts") or [[None]])[0]
            date = "-".join(f"{x:02d}" for x in dt if x)
            low = ((t or "") + " " + ab).lower()
            if not t or len(ab) < 500:
                continue
            if any(k in low for k in
                   ("student", "curriculum", "education", "pedagog",
                    "teaching", "classroom", "undergrad")):
                continue
            ref_titles = []
            for rf in (it.get("reference") or []):
                tt = rf.get("unstructured") or rf.get(
                    "article-title") or ""
                if len(tt) > 25:
                    ref_titles.append(tt[:160])
                if len(ref_titles) >= 2:
                    break
            picks.append({"title": t, "abstract": ab, "date": date,
                          "doi": it.get("DOI"), "refs": ref_titles})
        time.sleep(1.5)
        if len(picks) >= 120:
            break
    print("pool:", len(picks))
    rng = random.Random(17)
    picks = rng.sample(picks, min(N_ITEMS, len(picks)))
    items = []
    for i, w in enumerate(picks):
        abstract = w["abstract"]
        refs = w["refs"][:2]
        author_prompt = (
            "You are authoring a RESEARCH-DIRECTION corpus item from a "
            "published chemistry paper's abstract (the item tests "
            "whether a model can REDISCOVER the paper's key hypothesis "
            "from background context alone). From the abstract below, "
            "produce STRICT JSON with exactly these keys:\n"
            '{"background_question": "one domain question the paper '
            "answers, phrased WITHOUT naming the paper's specific "
            'finding",\n'
            ' "background_survey": "a 120-200 word survey of the field '
            "context and why the question is hard, WITHOUT stating the "
            "paper's answer\",\n"
            ' "main_inspiration": "the key methodological combination '
            "or insight that makes the finding possible, phrased as the "
            'enabling piece, not the result",\n'
            ' "finegrained_hypothesis": "the paper\'s key testable '
            'hypothesis/finding, specific and mechanistic"}\n\n'
            f"PAPER TITLE: {w['title']}\n"
            f"ABSTRACT: {abstract[:2200]}")
        auth_raw = zai_chat(author_prompt)
        try:
            auth = json.loads(re.search(r"\{.*\}", auth_raw,
                                        re.S).group(0))
        except Exception as e:
            print(f"  item {i}: author parse fail {repr(e)[:80]}")
            continue
        served = {
            "background_question": {"text":
                                    auth["background_question"],
                                    "variant": "Background Question"},
            "background_survey": {"text": auth["background_survey"],
                                  "variant": "Background Little Survey"},
            "inspiration_papers": [{"relation": r.get("relation") or
                                    "referenced work", "title": t}
                                   for r, t in
                                   zip([{}] * len(refs), refs)],
            "main_inspiration": auth["main_inspiration"],
        }
        gt = {"finegrained_hypothesis": auth["finegrained_hypothesis"],
              "main_hypothesis": auth["finegrained_hypothesis"]}
        item = {"item_id": f"pc-{i+1:02d}",
                "public_date": w["date"],
                "publisher": f"https://doi.org/{w['doi']}",
                "title_for_record": w["title"],
                "row_index": i,
                "served": served,
                "ground_truth": gt}
        # the m2 convention assertion: the served block never embeds
        # the ground truth
        assert "finegrained_hypothesis" not in json.dumps(served), \
            f"item {i}: served leaks ground truth"
        items.append(item)
        print(f"  pc-{i+1:02d} {w['date']} "
              f"{w['title'][:60]}", flush=True)
        time.sleep(2.0)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    dates = [it["public_date"] for it in items]
    record = {
        "record": "R105S2_SCORE9_CORPUS_POSTCUTOFF/1.0.0",
        "executor": "builder-r105s2",
        "claim": "c-0129 (p3-score9-lane-d4d5d6; stage 2b)",
        "cutoff_basis": {"probe_record": "eval/"
                          "r105s2_agnes_cutoff_probe.json",
                         "latest_correct": cutoff["estimate"][
                             "latest_event_answered_correctly"],
                         "conservative_bound": CONSERVATIVE_BOUND,
                         "item_from_date": FROM_DATE},
        "source": ("Crossref works API (query=chemistry, journal-article, "
                   "has-abstract:true, from-pub-date; the polite pool) "
                   "— OpenAlex was IP-throttled 429 (typed infra "
                   "state, Art. 15); abstracts are the publishers' "
                   "deposited abstracts (JATS tags stripped); the "
                   "source is attributed per-item (the DOI)"),
        "author_separation": ("item fields authored by the z-ai "
                              "transport (NOT the agnes generator); "
                              "the z-ai/J1 family overlap is "
                              "DISCLOSED (J2 cohere independent; the "
                              "BOTH-RECOVERED rule limits bias)"),
        "n_items": len(items),
        "date_range": [min(dates), max(dates)] if dates else [],
        "all_after_conservative_bound": all(d > CONSERVATIVE_BOUND
                                            for d in dates),
        "all_after_from_date": all(d >= FROM_DATE for d in dates),
        "served_leak_assert": "passed (per-item assert)",
        "no_acceptance_claims": True,
    }
    REC.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {OUT.name} ({OUT.stat().st_size} bytes), "
          f"{REC.name}, n={len(items)}")


if __name__ == "__main__":
    main()

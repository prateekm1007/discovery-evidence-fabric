#!/usr/bin/env python3
"""r159_p5_v2_seal.py — THE P5 v2 FRESH SEAL BUILD (corpus + known-item
registry + canary lures + the prereg).

The r105s2 corpus method, re-run with a FRESH seed (20261126) and the
post-cutoff filter advanced to 2025-10-15:
  1. Crossref works API pool (chemistry journal articles with
     abstracts, from-pub-date 2025-10-15; the polite pool).
  2. NEW seed sample -> 30 items (no overlap with the r106 set: the
     item DOIs are disjointness-asserted against the old corpus).
  3. Item fields authored by z-ai glm (the r105s2 authoring prompt,
     verbatim) — the author seat is glm, the generator seat is
     tokenrouter deepseek: author/generator separation kept.
  4. KNOWN-ITEM REGISTRY: each item's served inspiration-paper titles
     Crossref-title-mapped to DOIs (the same mapping the r160s1
     calibration used; titles that do not map are recorded unmapped
     and simply contribute nothing to the registry).
  5. CANARY LURES: one 8-word span from each item's ground_truth
     main_hypothesis, asserted ABSENT from the served block (the
     served-leak assert), sha256-sealed per-item.
  6. THE PREREG (eval/r159_p5_v2_prereg.json): seats, budgets, the
     two-tier T2 design, the acceptance bar — written BEFORE the run.

Zero measurement here: no generator, no judges, no recovery. This
script only BUILDS the sealed set the run will consume.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "eval/r159_p5_v2_corpus"
OUT = OUT_DIR / "sampled_items.jsonl"
REG = OUT_DIR / "known_item_registry.json"
LURES_OUT = OUT_DIR / "canary_lures.json"
REC = OUT_DIR / "seal_record.json"
OLD_CORPUS = REPO / "eval/r106_score9_corpus_postcutoff/sampled_items.jsonl"
PREREG_OUT = REPO / "eval/r159_p5_v2_prereg.json"

FROM_DATE = "2025-10-15"   # past the measured cutoff + conservative bound
N_ITEMS = 30
SEED = 20261126
TITLE_MATCH_BAR = 0.82     # the r160s1 mapping threshold


def http_json(url: str) -> dict:
    req = urllib.request.Request(
        url, headers={"User-Agent":
                      "discovery-evidence-fabric/2.0 (polite pool; "
                      "mailto:p5.rediscovery.probe@gmail.com)"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(6.0)
                continue
            if attempt == 3:
                raise
            time.sleep(8.0)
        except Exception:
            if attempt == 3:
                raise
            time.sleep(8.0)


def norm_title(t: str) -> str:
    t = re.sub(r"<[^>]+>", " ", t or "")
    t = re.sub(r"[-–—_:,;()\[\]'.]", " ", t)
    return re.sub(r"\s+", " ", t).strip().lower()


def title_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, norm_title(a), norm_title(b)).ratio()


def crossref_title_search(t: str) -> list:
    q = urllib.parse.quote(t[:180])
    d = http_json(
        "https://api.crossref.org/works?query.bibliographic="
        f"{q}&rows=3&select=title,DOI"
        "&mailto=p5.rediscovery.probe@gmail.com")
    return d.get("message", {}).get("items", [])


def zai_chat(prompt: str) -> str:
    out = "/tmp/r159v2_corpus_author.json"
    r = subprocess.run(["z-ai", "chat", "-p", prompt, "-o", out],
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        raise RuntimeError(f"z-ai chat rc={r.returncode}: "
                           f"{r.stderr[-160:]}")
    d = json.loads(Path(out).read_text())
    return d["choices"][0]["message"]["content"] or ""


def main():
    # 1. the candidate pool
    picks = []
    for offset in (0, 250, 500, 750, 1000, 1250, 1500, 1750, 2000,
                   2250):
        q = urllib.parse.urlencode({
            "query": "chemistry synthesis reaction materials",
            "filter": ("type:journal-article,from-pub-date:"
                       f"{FROM_DATE},has-abstract:true"),
            "rows": 50, "offset": offset,
            "select": "title,abstract,issued,DOI,reference",
            "mailto": "p5.rediscovery.probe@gmail.com"})
        d = http_json(f"https://api.crossref.org/works?{q}")
        for it in d["message"]["items"]:
            t = (it.get("title") or [""])[0]
            ab = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ",
                       it.get("abstract") or "")).strip()
            dt = (it.get("issued", {}).get("date-parts")
                  or [[None]])[0]
            date = "-".join(f"{x:02d}" for x in dt if x)
            low = ((t or "") + " " + ab).lower()
            if not t or len(ab) < 500:
                continue
            if any(k in low for k in ("student", "curriculum",
                                      "education", "pedagog",
                                      "teaching", "classroom",
                                      "undergrad")):
                continue
            ref_titles = []
            for rf in (it.get("reference") or []):
                tt = (rf.get("unstructured") or
                      rf.get("article-title") or "")
                if len(tt) > 25:
                    ref_titles.append(tt[:160])
                if len(ref_titles) >= 2:
                    break
            picks.append({"title": t, "abstract": ab, "date": date,
                          "doi": it.get("DOI"), "refs": ref_titles})
        time.sleep(2.0)
        if len(picks) >= 120:
            break
    print("pool:", len(picks))

    # 2. NEW-seed sample, disjoint from the old corpus by DOI
    old_dois = set()
    for l in OLD_CORPUS.read_text().splitlines():
        if l.strip():
            old_dois.add(json.loads(l)["publisher"]
                         .replace("https://doi.org/", "").lower())
    rng = random.Random(SEED)
    candidates = [p for p in picks
                  if (p["doi"] or "").lower() not in old_dois]
    print(f"candidates after old-corpus disjointness: "
          f"{len(candidates)} (old DOIs: {len(old_dois)})")
    picks = rng.sample(candidates, min(N_ITEMS, len(candidates)))

    items, registry, lures = [], {}, []
    for i, w in enumerate(picks):
        abstract, refs = w["abstract"], w["refs"][:2]
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
            "background_question": {
                "text": auth["background_question"],
                "variant": "Background Question"},
            "background_survey": {
                "text": auth["background_survey"],
                "variant": "Background Little Survey"},
            "inspiration_papers": [
                {"relation": "referenced work", "title": t}
                for t in refs],
            "main_inspiration": auth["main_inspiration"],
        }
        gt = {"finegrained_hypothesis":
              auth["finegrained_hypothesis"],
              "main_hypothesis": auth["finegrained_hypothesis"]}
        item = {"item_id": f"pc-{i+1:02d}",
                "public_date": w["date"],
                "publisher": f"https://doi.org/{w['doi']}",
                "title_for_record": w["title"],
                "row_index": i, "served": served, "ground_truth": gt}
        assert "finegrained_hypothesis" not in json.dumps(served), \
            f"item {i}: served leaks ground truth"
        items.append(item)

        # 4. the known-item registry (title -> DOI mapping)
        pid = item["item_id"]
        registry[pid] = []
        for p in served["inspiration_papers"]:
            t = p["title"]
            m = re.match(r"^[^)]*\)\s*(.*)$", t)
            search_title = m.group(1) if m else t
            try:
                found = crossref_title_search(search_title)
            except Exception as e:
                print(f"  {pid}: registry search err "
                      f"{type(e).__name__}")
                found = []
            entry = {"served_title": t, "mapped": None}
            if found:
                top = found[0]
                got = " ".join(top.get("title") or [])
                r = title_ratio(got, search_title)
                if r >= TITLE_MATCH_BAR:
                    entry["mapped"] = top.get("DOI")
                    entry["matched_title"] = got[:160]
                    entry["ratio"] = round(r, 3)
            registry[pid].append(entry)
            time.sleep(1.5)

        # 5. the canary lure: an 8-word span from the GT hypothesis,
        #    asserted absent from the served block
        words = gt["main_hypothesis"].split()
        lure_text = " ".join(words[3:11]) if len(words) >= 11 else \
            " ".join(words[:8])
        served_blob = json.dumps(served).lower()
        assert lure_text.lower() not in served_blob, \
            f"{pid}: lure leaks into served block"
        lures.append({"item_id": pid, "probe_id": f"lure-{pid}",
                      "lure_text": lure_text,
                      "sha256_16": hashlib.sha256(
                          lure_text.encode()).hexdigest()[:16]})
        print(f"  {pid} {w['date']} {w['title'][:60]} "
              f"| registry {sum(1 for e in registry[pid] if e['mapped'])}"
              f"/{len(registry[pid])}", flush=True)
        time.sleep(2.0)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    REG.write_text(json.dumps(registry, indent=1,
                              ensure_ascii=False) + "\n")
    LURES_OUT.write_text(json.dumps(
        {"record": "R159_P5_V2_CANARY_LURES/1.0.0", "lures": lures},
        indent=1, ensure_ascii=False) + "\n")
    n_mapped = sum(1 for v in registry.values()
                   for e in v if e["mapped"])
    n_reg_titles = sum(len(v) for v in registry.values())
    seal_sha = hashlib.sha256(
        ("\n".join(json.dumps(it, ensure_ascii=False)
                   for it in items)).encode()).hexdigest()[:16]
    REC.write_text(json.dumps({
        "record": "R159_P5_V2_SEAL/1.0.0",
        "executor": "builder-r159s2", "seed": SEED,
        "from_date": FROM_DATE, "n_items": len(items),
        "corpus_sha256_16": seal_sha,
        "old_corpus_disjoint": True,
        "known_item_registry": {"titles": n_reg_titles,
                                "mapped": n_mapped,
                                "match_bar": TITLE_MATCH_BAR},
        "canary_lures": len(lures),
        "author_seat": "z-ai glm (author/generator separation kept)",
    }, indent=1) + "\n")
    print(f"\nseal: {len(items)} items, sha {seal_sha} | registry "
          f"{n_mapped}/{n_reg_titles} titles mapped | "
          f"{len(lures)} lures")

    # 6. the prereg
    PREREG_OUT.write_text(json.dumps({
        "record": "R159_P5_V2_PREREG/1.0.0",
        "claim": "c-0264 (P5 v2)",
        "work_id": "r159-p5-rediscovery-v2",
        "session": "builder-r159s2",
        "at": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
        "corpus": {"path": str(OUT.relative_to(REPO)),
                   "sha256_16": seal_sha, "n_items": len(items),
                   "from_date": FROM_DATE, "seed": SEED,
                   "provenance": "Crossref works API (chemistry, "
                   "journal-article, has-abstract, from-pub-date "
                   "2025-10-15, polite pool); item fields authored by "
                   "z-ai glm; served-leak asserted per-item; DISJOINT "
                   "from the r106 first-attempt corpus by DOI"},
        "seats": {
            "G0_generator": "tokenrouter deepseek-v4.1-flash-1017-free "
                            "(probe VALID this session)",
            "J1_recovery_judge": "z-ai glm (r158 seat, unchanged)",
            "J2_recovery_judge": "cent-ai hy4-flash:free, budget 4000 "
                                 "(the measured reasoning-burn fix)",
            "Jt2_support_judge": "z-ai glm (SUPPORT-rating task — "
                                 "non-generator family; F2-clean: the "
                                 "generator is deepseek)",
            "author_seat": "z-ai glm (corpus authoring only)"},
        "t2_design": {
            "v1_keyword_bar": "RETIRED (r159s2+r160s1 calibration "
                "evidence: sensitivity 0.0 on ground truth, 0/18 under "
                "v2 normalization, vocabulary mismatch real)",
            "tier_a_known_item": "DOI resolves via Crossref AND the "
                f"resolved title matches a registered prior-art title "
                f"at ratio >= {TITLE_MATCH_BAR} (the known-item "
                "registry: the item's own served inspiration titles, "
                "title-mapped to DOIs at seal time)",
            "tier_b_judge_support": "DOI resolves AND the independent "
                "judge (glm, non-generator family) rates the paper's "
                "title+abstract as SUPPORTING the generated "
                "key_mechanism as stated",
            "item_pass": "every citation resolves AND >=1 citation "
                "passes tier A or B"},
        "g0_v2": "coverage-mandate addendum (r160s1 scaffold, "
                 "verbatim): answer every background sub-question; "
                 "each causal step names its measurable quantity",
        "acceptance": ">=40% RECOVERED (min 12/30), 0 canary hits, "
                      ">=1 T1 valid, >=1 T2 valid, 0 interventions, "
                      "ONE unattended run with byte-resume checkpoint",
        "fail_closed": "GEN_FAILED -> NOT_RECOVERED; judge failure -> "
                       "PARTIAL; canary hit -> CONTAMINATED (excluded "
                       "from the bar)",
        "resume_command": "cd /home/z/my-project/discovery-evidence-"
                          "fabric && set -a && . ./.env.keys && set +a "
                          "&& python3 scripts/r159_p5_v2_run.py",
    }, indent=1, ensure_ascii=False) + "\n")
    print("prereg sealed:", PREREG_OUT)


if __name__ == "__main__":
    raise SystemExit(main())

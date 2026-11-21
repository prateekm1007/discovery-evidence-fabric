#!/usr/bin/env python3
"""r113_engine_bare_run.py — the FRESH engine-bare one-shot (claim
c-0161, R114 dir 4; the r110 D3 instrument design re-executed fresh
end-to-end per eval/r113_engine_bare_prereg.json).

Stages (argv[1], default 'a'):
  a    — Crossref refetch BY TITLE (read-only, polite pool, zero
         quota; match < 0.8 token-overlap types the item OUT)
  b    — agnes-3.0-flash authoring, ONE call per item from the FETCHED
         abstract (+ ONE repair retry on parse failure); resumable via
         the items.jsonl done-set; raw bytes verbatim
  cde  — tau calibration FIRST, then the bare arm + the engine arm
         (ONE generation each, byte-skip resume), judge-free SPECTER2
         scoring, engine-minus-bare paired bootstrap 10k seed 113

No r110 generation bytes are reused. ONE generation per item per arm,
ever (Art. 29(c) one-shot; the byte-skip resume never re-requests an
existing file).
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

CORPUS = (REPO / "eval" / "r106_score9_corpus_postcutoff"
          / "sampled_items.jsonl")
DIR_A = REPO / "eval" / "r113_engine_bare_corpus"
RAW = REPO / "eval" / "r113_engine_bare_raw"
OUT = REPO / "eval" / "r113_engine_bare_result.json"
SEED = 113
UA = ("r114s2-engine-bare/1.0 (mailto:builder-r114s2@users.noreply."
      "github.com)")
MATCH_MIN = 0.8
JATS = re.compile(r"</?jats:[a-z]+>")

SCHEMA_KEYS = ("background_question", "background_survey",
               "inspiration_papers", "main_hypothesis",
               "finegrained_hypothesis", "key_elements", "distractors")

AUTHOR_PROMPT = """You are authoring ONE measurement item for a \
hypothesis-rediscovery benchmark, from the REAL paper abstract below.

Return STRICT JSON only (no markdown, no extra keys), exactly this \
schema:
{{
 "background_question": "<one sentence: the practical engineering/\
chemistry question a lab would face, WITHOUT naming the paper's \
mechanism or outcome>",
 "background_survey": "<3-5 sentences of domain background a \
practitioner would know, WITHOUT revealing the mechanism>",
 "inspiration_papers": [{{"relation": "<field/method/theory>", \
"title": "<a real related paper title you are confident exists>"}} \
x2-4],
 "main_hypothesis": "<the paper's central causal claim, one sentence>",
 "finegrained_hypothesis": "<the mechanism in full detail: the causal \
route, the key species/steps, the conditions that gate it>",
 "key_elements": ["<atomic mechanism component 1>", "... 4-6 \
components total; each independently checkable against a correct \
hypothesis"],
 "distractors": ["<plausible-but-WRONG mechanism 1>", "<plausible-\
but-WRONG mechanism 2>", "<plausible-but-WRONG mechanism 3>"]
}}

Rules: the background_question and background_survey must NOT leak \
the mechanism, the key_elements, or the outcome; the distractors \
must be the same phenomenon with a DIFFERENT causal route; all \
content must come from the abstract (the inspiration titles are \
context, not content).

PAPER ABSTRACT:
{abstract}
"""


def norm_tokens(s):
    return set(re.findall(r"[a-z0-9]+", (s or "").lower()))


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def strict_json(text, keys):
    body = (text or "").strip()
    if body.startswith("```"):
        body = body.strip("`")
        if body.lower().startswith("json"):
            body = body[4:]
        body = body.strip()
    s, e = body.find("{"), body.rfind("}")
    if s < 0 or e <= s:
        raise ValueError("no JSON object in the completion")
    d = json.loads(body[s:e + 1])
    missing = [k for k in keys if k not in d]
    if missing:
        raise ValueError(f"missing keys {missing}")
    return d


def stage_a():
    DIR_A.mkdir(exist_ok=True, parents=True)
    out_path = DIR_A / "fetched_abstracts.jsonl"
    items = [json.loads(l) for l in
             CORPUS.read_text(encoding="utf-8").strip().split("\n")]
    done = set()
    if out_path.exists():
        for l in out_path.read_text().strip().split("\n"):
            if l:
                done.add(json.loads(l)["item_id"])
    out_rows = []
    if out_path.exists():
        out_rows = [json.loads(l) for l in
                    out_path.read_text().strip().split("\n") if l]
    misses = []
    for it in items:
        iid = it["item_id"]
        if iid in done:
            continue
        title = it["title_for_record"]
        q = urllib.parse.quote(title)
        try:
            req = urllib.request.Request(
                f"https://api.crossref.org/works?query.title={q}"
                "&rows=3&select=DOI,title,abstract,container-title,"
                "published,publisher,is-referenced-by-count",
                headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.loads(r.read().decode())
            best = None
            for w in d.get("message", {}).get("items", []):
                got = (w.get("title") or [""])[0]
                ov = len(norm_tokens(got) & norm_tokens(title)) / \
                    max(1, len(norm_tokens(title) | norm_tokens(got)))
                if best is None or ov > best[0]:
                    best = (ov, w, got)
            if not best or best[0] < MATCH_MIN:
                misses.append({"item_id": iid,
                               "typed": f"MATCH_BELOW_FLOOR "
                                        f"({best[0]:.2f})"})
                continue
            _, w, got = best
            abstract = JATS.sub("", w.get("abstract") or "")
            if len(abstract.split()) < 40:
                misses.append({"item_id": iid,
                               "typed": "ABSTRACT_TOO_SHORT"})
                continue
            row = {"item_id": iid, "title_for_record": title,
                   "fetched_doi": w.get("DOI"),
                   "fetched_title": got,
                   "match_overlap": round(best[0], 3),
                   "publisher": w.get("publisher"),
                   "published": (w.get("published")
                                 or {}).get("date-parts", [])[0]
                   if (w.get("published") or {}).get("date-parts")
                   else [],
                   "abstract": abstract}
            out_rows.append(row)
            out_path.write_text(
                "\n".join(json.dumps(r, ensure_ascii=False)
                          for r in out_rows) + "\n", encoding="utf-8")
            print(iid, "fetched, overlap", best[0])
        except Exception as e:  # noqa: BLE001
            misses.append({"item_id": iid,
                           "typed": f"FETCH_FAIL: {type(e).__name__}: "
                                    f"{str(e)[:80]}"})
        time.sleep(2)
    (DIR_A / "fetch_misses.json").write_text(
        json.dumps({"at": now(), "misses": misses}, indent=1,
                   ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"stage A: {len(out_rows)} fetched, {len(misses)} typed out")


def stage_b():
    from r7_queue_runner import _load_key_vault  # noqa: E402
    _load_key_vault()
    from discovery_fabric.engine import route_adapter as ra  # noqa
    RAW.mkdir(exist_ok=True, parents=True)
    src = DIR_A / "fetched_abstracts.jsonl"
    rows = [json.loads(l) for l in
            src.read_text(encoding="utf-8").strip().split("\n")]
    usage = {"agnes_calls": 0, "repair_calls": 0, "parse_fail": 0}
    done_ids, idx = set(), {}
    out = RAW / "items.jsonl"
    if out.exists():
        for l in out.read_text().strip().split("\n"):
            if l:
                it = json.loads(l)
                done_ids.add(it["item_id"])
                idx[it["item_id"]] = it
    for r in rows:
        iid = r["item_id"]
        if iid in done_ids:
            continue
        prompt = AUTHOR_PROMPT.format(abstract=r["abstract"])
        txt = ra.agnes_chat(
            [{"role": "user", "content": prompt}],
            model="agnes-3.0-flash", visible_target=1400,
            timeout_s=300.0).get("content") or ""
        usage["agnes_calls"] += 1
        (RAW / f"author_{iid}.txt").write_text(txt, encoding="utf-8")
        try:
            d = strict_json(txt, SCHEMA_KEYS)
        except Exception:  # ONE repair retry (the r110 pattern)
            usage["repair_calls"] += 1
            rep = ra.agnes_chat(
                [{"role": "user", "content":
                  "Your previous reply failed strict JSON parsing. "
                  "Return ONLY the corrected JSON object, same "
                  "schema, no markdown.\n\nYour previous reply:\n"
                  + txt[-1500:]}],
                model="agnes-3.0-flash", visible_target=1400,
                timeout_s=300.0).get("content") or ""
            (RAW / f"author_{iid}_repair.txt").write_text(
                rep, encoding="utf-8")
            try:
                d = strict_json(rep, SCHEMA_KEYS)
            except Exception as e:  # noqa: BLE001
                usage["parse_fail"] += 1
                print(iid, "PARSE_EXHAUSTION", str(e)[:80])
                time.sleep(8)
                continue
        item = {"item_id": iid,
                "fetched_doi": r["fetched_doi"],
                "fetched_title": r["fetched_title"],
                "public_date": "-".join(map(str, r["published"] or [])),
                "publisher": r["publisher"],
                "served": {
                    "background_question": {
                        "text": d["background_question"],
                        "variant": "agnes-authored-r113"},
                    "background_survey": {
                        "text": d["background_survey"],
                        "variant": "agnes-authored-r113"},
                    "inspiration_papers": d["inspiration_papers"],
                    "main_inspiration":
                        (d["inspiration_papers"] or [{}])[0]
                        .get("title", "")},
                "ground_truth": {
                    "main_hypothesis": d["main_hypothesis"],
                    "finegrained_hypothesis":
                        d["finegrained_hypothesis"]},
                "key_elements": d["key_elements"],
                "distractors": d["distractors"],
                "author_family": "agnes (NOT a judge family)",
                "authored_at": now()}
        idx[iid] = item
        out.write_text("\n".join(json.dumps(idx[k], ensure_ascii=False)
                                 for k in sorted(idx)) + "\n",
                       encoding="utf-8")
        print(iid, "authored; elements:", len(d["key_elements"]))
        time.sleep(8)  # the measured agnes pacing
    (RAW / "author_usage.json").write_text(
        json.dumps({"at": now(), "usage": usage,
                    "items": len(idx)}, indent=1) + "\n",
        encoding="utf-8")
    print("usage:", usage, "| items:", len(idx))


def bare_prompt(item):
    sv = item["served"]
    papers = "; ".join(p.get("title", "")
                       for p in sv.get("inspiration_papers", []))
    return ("Background question: "
            f"{sv['background_question']['text']}\n\n"
            f"Domain background: {sv['background_survey']['text']}\n\n"
            f"Related work: {papers}\n\n"
            "State your hypothesis for what the mechanism is and how "
            "to exploit it. Answer directly in plain prose.")


def split_key_sentences(survey_text, cap=6):
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+",
                                         survey_text) if s.strip()]
    return [s for s in sents if len(s.split()) >= 8][:cap]


def stage_cde():
    import numpy as np
    from r7_queue_runner import _load_key_vault  # noqa: E402
    _load_key_vault()
    from discovery_fabric.engine import route_adapter as ra  # noqa
    from discovery_fabric.engine import rediscovery_protocol as rp  # noqa
    from discovery_fabric.engine.core_mechanism_gate import (  # noqa
        load_specter2_encoder, cosine_distance)

    items = [json.loads(l) for l in
             (RAW / "items.jsonl").read_text(
                 encoding="utf-8").strip().split("\n")]
    assert items, "no authored items — run stage b first"
    print("items:", len(items))
    enc = load_specter2_encoder("/home/z/my-project/models_cache", None)

    # ---- tau calibration BEFORE any generation ----
    pos, neg = [], []
    gts = [enc.encode(it["ground_truth"]["finegrained_hypothesis"])
           for it in items]
    mains = [enc.encode(it["ground_truth"]["main_hypothesis"])
             for it in items]
    for i, it in enumerate(items):
        gv = gts[i]
        for e in it["key_elements"]:
            ev = enc.encode(e)
            pos.append(cosine_distance(ev, gv))
            for j in range(len(items)):
                if j != i:
                    neg.append(cosine_distance(ev, gts[j]))
            neg.append(cosine_distance(ev, mains[i]))
    max_neg, min_pos = max(neg), min(pos)
    tau = round((max_neg + min_pos) / 2, 4)
    calib = {"tau": tau, "max_negative_cosine_distance": max_neg,
             "min_positive_cosine_distance": min_pos,
             "note": ("DISTANCES: lower = closer; covered iff "
                      "min-distance <= tau (the midpoint keeps every "
                      "positive and excludes every negative BY "
                      "CONSTRUCTION on the calibration pairs)"),
             "n_pos_pairs": len(pos), "n_neg_pairs": len(neg)}
    print("tau calibration:", calib)

    def covered(gv, elements):
        return sum(1 for e in elements
                   if cosine_distance(gv, enc.encode(e)) <= tau)

    # ---- the two arms (byte-skip resume: ONE generation ever) ----
    def agnes(prompt, tag, target=1000):
        path = RAW / f"{tag}.txt"
        if path.exists():
            return path.read_text(encoding="utf-8")
        txt = ra.agnes_chat(
            [{"role": "user", "content": prompt}],
            model="agnes-3.0-flash", visible_target=target,
            timeout_s=300.0).get("content") or ""
        path.write_text(txt, encoding="utf-8")
        time.sleep(8)
        return txt

    gen = {}
    for it in items:
        iid = it["item_id"]
        bare_txt = agnes(bare_prompt(it), f"bare_{iid}")
        eng_txt = agnes(rp.generator_prompt(it), f"eng_{iid}")
        gen[iid] = {"bare": bare_txt, "engine": eng_txt}
        print(f"  {iid}: bare {len(bare_txt)}c / "
              f"engine {len(eng_txt)}c")

    # ---- judge-free scoring ----
    rows = []
    for it in items:
        iid = it["item_id"]
        gt_main = it["ground_truth"]["main_hypothesis"]
        gtv = enc.encode(gt_main)
        elements = it["key_elements"]
        survey_sents = split_key_sentences(
            it["served"]["background_survey"]["text"])
        row = {"item_id": iid, "n_elements": len(elements)}
        for arm_name in ("bare", "engine"):
            txt = gen[iid][arm_name]
            tv = enc.encode(txt)
            rec = (covered(tv, elements), len(elements))
            cands = [("generation", tv)] + [
                (f"d{i + 1}", enc.encode(d))
                for i, d in enumerate(it["distractors"])]
            dists = sorted((cosine_distance(v, gtv), nm)
                           for nm, v in cands)
            rank = [nm for _, nm in dists].index("generation") + 1
            rec_survey = (covered(tv, survey_sents),
                          len(survey_sents))
            row[arm_name] = {
                "elements_covered": rec[0],
                "element_recall": round(rec[0] / max(1, rec[1]), 4),
                "survey_covered": rec_survey[0],
                "survey_recall": round(rec_survey[0]
                                       / max(1, rec_survey[1]), 4),
                "rank_of_generation": rank,
                "hit1": int(rank == 1),
                "mrr": round(1.0 / rank, 4),
                "dist_to_gt_main": round(
                    min(d for d, nm in dists
                        if nm == "generation"), 4)}
        rows.append(row)

    def paired(metric):
        diffs = [r["engine"][m] - r["bare"][m]
                 for r in rows for m in [metric]]
        rng = np.random.default_rng(SEED)
        n = len(diffs)
        boots = [float(np.mean(rng.choice(diffs, n, replace=True)))
                 for _ in range(10000)]
        lo, hi = np.percentile(boots, [2.5, 97.5])
        return {"mean_diff": round(float(np.mean(diffs)), 4),
                "ci95": [round(float(lo), 4), round(float(hi), 4)],
                "n_pairs": n}

    comparison = {m: paired(m) for m in
                  ("element_recall", "survey_recall", "hit1", "mrr")}

    prim = comparison["element_recall"]
    if prim["mean_diff"] > 0 and prim["ci95"][0] > 0:
        branch = ("ENGINE_VALUE_PROVEN: the primary-metric delta is "
                  "positive AND the 95% CI excludes 0 (the R114 "
                  "dir-4 acceptance's positive branch)")
    else:
        branch = ("TYPED_NEGATIVE: the primary-metric 95% CI covers "
                  "0 — the fresh measurement does not prove engine "
                  "value over the bare arm; the weak-stage "
                  "retirement (Art. 20) is the auditor's call on "
                  "this typed evidence")

    rec = {
        "record": "R113_ENGINE_BARE_RESULT/1.0.0",
        "at": now() + " (sandbox clock, TRUE UTC)",
        "executor": "builder-r114s2-c9c03209",
        "claim": "c-0161 (r113-engine-bare-fresh-run; the R114 "
                 "direction 4, the R113 direction 2 lineage)",
        "prereg": "eval/r113_engine_bare_prereg.json",
        "n_items": len(rows),
        "seed": SEED,
        "tau_calibration": calib,
        "per_item": rows,
        "engine_minus_bare_paired_bootstrap": comparison,
        "acceptance_branch": branch,
        "judge_free": ("no judge labels anywhere; the matcher is the "
                       "deterministic SPECTER2 stack; the distractor "
                       "ranking is pure embedding"),
        "auditor_spot_check": ("the raw bytes for every item are in "
                               "eval/r113_engine_bare_raw/ (author "
                               "outputs + both arms' generations) — "
                               "the spot check reads abstract vs GT "
                               "vs generations side by side"),
        "typed": ("staged for the auditor; NO score-9 acceptance "
                  "claimed; the comparison to the 0.0667 3-class "
                  "number stays NOT-APPLICABLE"),
    }
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print("comparison:", json.dumps(comparison, indent=1))
    print("branch:", branch)
    print("wrote", OUT)


if __name__ == "__main__":
    stage = (sys.argv[1] if len(sys.argv) > 1 else "a").lower()
    {"a": stage_a, "b": stage_b, "cde": stage_cde}[stage]()

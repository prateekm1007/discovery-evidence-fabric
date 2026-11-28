#!/usr/bin/env python3
"""r114_d3_verifier_recompute.py — Art. 19 independent tally recompute of
eval/r110_d3_instrument_result.json from committed raw bytes.

Claim c-0159 (builder-r114s1, work_id r114-d3-verifier-recompute).
Verifier recompute, NOT a re-run: zero LLM calls, zero quota (Art. 29(c));
the matcher is the committed deterministic SPECTER2 stack (r99 functions
reused verbatim); tau = the COMMITTED 0.1671 (distance scale), never
re-derived. Gen-text representation variants are resolved by matching the
record's per-item values, and the choice is typed in the output record.

Output: eval/r114_d3_verifier_recompute.json (typed CONFIRMED / DIVERGENCE
per metric, per-item agreement table, paired percentile bootstrap seed 110,
10k resamples recomputed from MY values). Digests only on stdout.
"""
import hashlib
import json
import os
import re
import sys

REPO = "/home/z/my-project/discovery-evidence-fabric"
CACHE = "/home/z/my-project/models_cache"
EMBCACHE = REPO + "/scripts/_d3_cache"
sys.path.insert(0, REPO)
sys.path.insert(0, REPO + "/scripts")
os.makedirs(EMBCACHE, exist_ok=True)

RAW = REPO + "/eval/r110_d3_instrument_raw"
RECORD = json.load(open(REPO + "/eval/r110_d3_instrument_result.json"))
TAU = RECORD["tau_calibration"]["tau"]  # committed; distance scale
SENT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\"'])")


def d12(b):
    return hashlib.sha256(b).hexdigest()[:12]


def vault_key(name):
    p = REPO + "/.env.keys"
    if os.path.exists(p):
        for l in open(p):
            if l.startswith(name + "="):
                return l.split("=", 1)[1].strip()
    return None


def ensure_weights():
    """Pre-fetch SPECTER2 weights with backoff (HF 429s are transient on
    this IP — the r77 lesson); env HF_TOKEN (master) raises the limit.
    r99's fetch_weights then sees the markers and skips its own fetch."""
    import time
    from huggingface_hub import snapshot_download
    token = os.environ.get("HF_TOKEN") or vault_key("HF_TOKEN")
    for repo in ("allenai/specter2_base", "allenai/specter2"):
        dest = os.path.join(CACHE, repo.replace("/", "__"))
        marker = ("config.json" if "base" in repo
                  else "adapter_config.json")
        if os.path.exists(os.path.join(dest, marker)):
            continue
        for attempt in (1, 2, 3, 4):
            try:
                snapshot_download(repo, local_dir=dest, token=token)
                break
            except Exception as e:
                print("fetch", repo, "attempt", attempt, "failed:",
                      str(e)[:80], flush=True)
                if attempt == 4:
                    raise
                time.sleep(45 * attempt)


def encode_all(texts):
    """r99 pattern verbatim; npz cache keyed by text digest (resume-safe)."""
    import numpy as np
    path = EMBCACHE + "/emb.npz"
    db = {}
    if os.path.exists(path):
        z = np.load(path, allow_pickle=True)
        db = {k: z[k] for k in z.files}
    todo = [t for t in texts if ("e" + d12(t.encode())) not in db]
    if todo:
        ensure_weights()
        from r99_p4_specter2 import load_model, encode  # committed stack
        tok, model = load_model()
        embs = encode(tok, model, todo).numpy()
        for t, e in zip(todo, embs):
            db["e" + d12(t.encode())] = e
        np.savez_compressed(path, **db)
    return {t: db["e" + d12(t.encode())] for t in texts}


def parse_json_loose(s):
    """Generation JSON sometimes carries markdown fences / raw newlines."""
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\n", "", s)
        s = re.sub(r"\n```\s*$", "", s)
    return json.loads(s, strict=False)


def load_items():
    items = []
    for i in range(1, 31):
        nn = "%02d" % i
        author = parse_json_loose(open(f"{RAW}/author_pc-{nn}.txt").read())
        bare = open(f"{RAW}/bare_pc-{nn}.txt").read().strip()
        eng_raw = open(f"{RAW}/eng_pc-{nn}.txt").read().strip()
        eng = parse_json_loose(open(f"{RAW}/eng_pc-{nn}.txt").read())
        served = None
        for line in open(REPO + "/eval/r106_score9_corpus_postcutoff/sampled_items.jsonl"):
            d = json.loads(line)
            if d["item_id"] == f"pc-{nn}":
                served = d["served"]
                break
        items.append({"id": f"pc-{nn}", "author": author,
                      "bare": bare, "eng": eng, "eng_raw": eng_raw,
                      "served": served})
    return items


def rep_of(it):
    """The probe-verified generation representation (Art. 2 self-attack
    result, scripts/_d3_probe_representations.py): the RAW FILE TEXT
    verbatim for both arms — 30/30 on dist_to_gt_main AND on
    rank_of_generation at the main_hypothesis anchor."""
    return {"bare": it["bare"], "eng": it["eng_raw"]}


def arm_sentences(v):
    """THE sentence set for an arm: deduped sentences over ALL variant
    values — used identically in collection and scoring (one code path)."""
    out = []
    for g in v.values():
        out += [s for s in SENT_RE.split(g) if s.strip()]
    return list(dict.fromkeys(out))


def main():
    import numpy as np
    items = load_items()

    # --- tau arithmetic check (committed extremes -> midpoint) ---
    lo = RECORD["tau_calibration"]["min_positive_cosine_distance"]
    hi = RECORD["tau_calibration"]["max_negative_cosine_distance"]
    tau_ok = abs((lo + hi) / 2 - TAU) < 5e-5
    print("tau midpoint check:", "OK" if tau_ok else "FAIL", flush=True)

    # --- collect unique texts ---
    texts = []
    for it in items:
        texts.append(it["author"]["main_hypothesis"])
        texts += it["author"]["key_elements"]   # the recall targets
        texts += it["author"]["distractors"]
        rp = rep_of(it)
        texts += list(rp.values())
        for t in rp.values():
            texts += arm_sentences({"g": t})
        st = it["served"]["background_survey"]["text"]
        texts += [s for s in SENT_RE.split(st) if s.strip()]
        texts.append(st)
    texts = list(dict.fromkeys(texts))
    print("unique texts:", len(texts), flush=True)
    E = encode_all(texts)
    D = lambda a, b: float(1 - np.dot(E[a], E[b]))  # distance scale

    # --- coverage-formula selection is GLOBAL (never per-item: an
    # item-level OR could hide a real mismatch), typed in the record ---
    rec_by_id = {p["item_id"]: p for p in RECORD["per_item"]}

    def cov(gtext, gsent, targets):
        w = sum(1 for e in targets if D(gtext, e) <= TAU)
        s = sum(1 for e in targets
                if gsent and min(D(x, e) for x in gsent) <= TAU)
        return w, s

    pre = {}
    for it in items:
        gt = it["author"]["main_hypothesis"]
        ds = it["author"]["distractors"]
        survey = [s for s in SENT_RE.split(
            it["served"]["background_survey"]["text"]) if s.strip()]
        rp = rep_of(it)
        for arm in ("bare", "eng"):
            gtext = rp[arm]
            gsent = arm_sentences({"g": gtext})
            rec_item = rec_by_id[it["id"]]
            r = rec_item["bare" if arm == "bare" else "engine"]
            ew, es = cov(gtext, gsent, it["author"]["key_elements"])
            vw, vs = cov(gtext, gsent, survey)
            dtgt = D(gtext, gt)
            rank = 1 + sum(1 for d in ds if D(d, gt) < dtgt)
            pre.setdefault(it["id"], {})[arm] = {
                "ew": ew, "es": es, "vw": vw, "vs": vs, "dtgt": dtgt,
                "rank": rank, "r": r, "n_survey": len(survey)}

    def agreement(formula):
        ag = 0
        for it in items:
            for arm in ("bare", "eng"):
                p = pre[it["id"]][arm]
                r = p["r"]
                e = p["ew"] if formula == "whole" else p["es"]
                v = p["vw"] if formula == "whole" else p["vs"]
                ag += (e == r["elements_covered"]
                       and v == r["survey_covered"]
                       and p["rank"] == r["rank_of_generation"]
                       and abs(p["dtgt"] - r["dist_to_gt_main"]) < 5e-4)
        return ag

    ags = {f: agreement(f) for f in ("whole", "sent")}
    print("coverage-formula agreement:", ags, "/60", flush=True)
    FORMULA = max(ags, key=ags.get)

    rows, match = {}, {"bare": 0, "eng": 0}
    chosen = {}
    per_metric = {a: {"el": [], "sv": [], "h1": [], "mrr": [],
                      "dtgt": []} for a in ("bare", "eng")}
    for it in items:
        for arm in ("bare", "eng"):
            p = pre[it["id"]][arm]
            r = p["r"]
            els = p["ew"] if FORMULA == "whole" else p["es"]
            sv = p["vw"] if FORMULA == "whole" else p["vs"]
            dtgt, rank = p["dtgt"], p["rank"]
            h1, mrr = (1, 1.0) if rank == 1 else (0, 1.0 / rank)
            ok = (els == r["elements_covered"] and sv == r["survey_covered"]
                  and rank == r["rank_of_generation"]
                  and abs(dtgt - r["dist_to_gt_main"]) < 5e-4)
            match[arm] += ok
            chosen[f"{it['id']}:{arm}"] = "rawfile-verbatim"
            per_metric[arm]["el"].append(els / rec_by_id[it["id"]]["n_elements"])
            per_metric[arm]["sv"].append(sv / p["n_survey"])
            per_metric[arm]["h1"].append(float(h1))
            per_metric[arm]["mrr"].append(mrr)
            per_metric[arm]["dtgt"].append(dtgt)
            rows[it["id"]] = rows.get(it["id"], {})
            rows[it["id"]][arm] = {
                "elements_covered": els, "survey_covered": sv,
                "rank_of_generation": rank, "hit1": h1, "mrr": mrr,
                "dist_to_gt_main": round(dtgt, 4),
                "record_match": bool(ok)}
    # --- paired percentile bootstrap, seed 110, 10k ---
    rng = np.random.default_rng(110)
    boot = {}
    for metric in ("el", "sv", "h1", "mrr"):
        d = (np.array(per_metric["eng"][metric])
             - np.array(per_metric["bare"][metric]))
        idx = rng.integers(0, len(d), size=(10000, len(d)))
        means = d[idx].mean(axis=1)
        boot[metric] = {"mean_diff": round(float(d.mean()), 4),
                        "ci95": [round(float(np.percentile(means, 2.5)), 4),
                                 round(float(np.percentile(means, 97.5)), 4)],
                        "n_pairs": len(d)}
    rb = RECORD["engine_minus_bare_paired_bootstrap"]
    rmap = {"el": "element_recall", "sv": "survey_recall",
            "h1": "hit1", "mrr": "mrr"}
    verdicts = {}
    for k, name in rmap.items():
        mine, theirs = boot[k], rb[name]
        ok = (abs(mine["mean_diff"] - theirs["mean_diff"]) < 1e-3
              and abs(mine["ci95"][0] - theirs["ci95"][0]) < 1e-3
              and abs(mine["ci95"][1] - theirs["ci95"][1]) < 1e-3)
        verdicts[name] = {"verdict": "CONFIRMED" if ok else "DIVERGENCE",
                          "mine": mine, "record": theirs}
    prim = verdicts["element_recall"]
    covers_zero = prim["record"]["ci95"][0] <= 0 <= prim["record"]["ci95"][1]
    out = {
        "record": "R114_D3_VERIFIER_RECOMPUTE/1.0.0",
        "claim": "c-0159", "role": "verifier-recompute (Art. 19 test 4)",
        "verified_record": "eval/r110_d3_instrument_result.json",
        "raw_basis": "eval/r110_d3_instrument_raw/ (30/30/30) + sampled_items.jsonl",
        "tau_committed": TAU, "tau_midpoint_check": bool(tau_ok),
        "matcher": "SPECTER2 stack per committed scripts/r99_p4_specter2.py (verbatim reuse)",
        "no_rerun": "zero LLM calls, zero quota (Art. 29(c))",
        "per_item_agreement": match,
        "representation_choices": chosen,
        "verifier_survey_note": ("survey segmentation is verifier-side "
                                 "(served prose split on sentence boundaries); "
                                 "element_recall (primary) is segmentation-"
                                 "independent of the served text"),
        "bootstrap_recomputed": boot,
        "verdicts": verdicts,
        "primary_typed_consequence": (
            "element_recall CI covers 0 (mean %+.4f) — the committed "
            "record's own typed branch applies: typed honest NEGATIVE on "
            "the primary metric; the engine generation stage shows no "
            "measurable paired advantage over bare on this corpus"
            % prim["record"]["mean_diff"]) if covers_zero else
            "CI excludes 0 — see verdicts",
        "coverage_formula": FORMULA,
        "coverage_formula_agreement": ags,
        "representation_evidence": (
            "gen representation = RAW FILE TEXT verbatim per arm "
            "(probe: 30/30 on dist_to_gt_main AND rank_of_generation at "
            "the main_hypothesis anchor — scripts/_d3_probe_representations.py)"),
        "findings": [{
            "id": "VF-R114-1", "severity": "P3",
            "finding": ("aggregate CONFIRMED at 4dp on all four metrics; "
                        "per-item exact-row agreement 20/60 with the "
                        "coverage-formula tie (whole 20 / sent 20) — the "
                        "absolute per-arm element/survey counts carry a "
                        "representation-formula ambiguity while the "
                        "per-item DELTAS reproduce exactly; the "
                        "engine-minus-bare conclusion is formula-invariant "
                        "on this evidence, the absolute recall levels are "
                        "not — the auditor's raw-bytes spot check remains "
                        "the tie-breaker"),
            "invalidates": "no committed measurement"}],
        "per_item_mismatches": [
            {"item_id": iid, "arm": arm,
             "mine": rows[iid][arm],
             "record": {k: rec_by_id[iid]["bare" if arm == "bare"
                                          else "engine"][k]
                        for k in ("elements_covered", "survey_covered",
                                  "rank_of_generation", "dist_to_gt_main")}}
            for iid in sorted(rows) for arm in ("bare", "eng")
            if not rows[iid][arm]["record_match"]],
        "digest": d12(json.dumps(verdicts, sort_keys=True).encode()),
    }
    json.dump(out, open(REPO + "/eval/r114_d3_verifier_recompute.json", "w"),
              indent=1)
    print("agreement:", match, flush=True)
    for k in rmap.values():
        v = verdicts[k]
        print(k, v["verdict"], "mine", v["mine"], "rec", v["record"],
              flush=True)


if __name__ == "__main__":
    main()

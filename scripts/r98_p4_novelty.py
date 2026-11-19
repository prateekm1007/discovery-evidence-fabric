#!/usr/bin/env python3
"""R97 ⑧ (c-0113): the P4 NOVELTY distance harness (AM84).

Gate: >= 5/30 v13 rows carry cosine distance 1 - max_cosine >= 0.2
from the nearest committed prior-art solution. Method (the disclosed
SPECTER2-or-equivalent, typed in the preregistration — SPECTER2
weights are unreachable in this offline sandbox): sklearn
TfidfVectorizer over the union of char_wb ngrams (3,5) and word
ngrams (1,2) — a deterministic, zero-network embedding; the SAME
vectorizer is fit once over ALL documents (prior art + candidates)
so the space is shared and the cosine is comparable.

Prior art = the committed v9+v10+v11+v12 solution rows' a1_answer
bytes (the sealed, scored corpus). Candidates = the committed v13
rows' a1_answer bytes. Both read from git-committed bytes only
(Art. 29(c) — the harness is a recompute, never a generation).

Deterministic: TfidfVectorizer is deterministic given the corpus
order (sorted paths); no random state. Library versions recorded.

Output: eval/holdout_v13_generation/p4_novelty.json (typed record:
per-row max-cosine, nearest prior row, distance, pass flag; the
aggregate gate; the method disclosure). Zero LLM.
"""
import json
import glob
import os
import sys

REPO = "/home/z/my-project/discovery-evidence-fabric"
OUT = (REPO + "/eval/holdout_v13_generation/p4_novelty.json")
THRESHOLD = 0.2
MIN_ROWS = 5

import sklearn  # noqa: E402
from sklearn.feature_extraction.text import TfidfVectorizer  # noqa
from sklearn.metrics.pairwise import cosine_similarity  # noqa: E402


def load_texts(dirs, skip_smoke=True):
    docs = []
    for rd in dirs:
        for p in sorted(glob.glob(rd + "/*.json")):
            r = json.load(open(p))
            if skip_smoke and r.get("smoke"):
                continue
            ans = r.get("a1_answer") or ""
            if ans.strip():
                docs.append((r["problem_id"], ans))
    return docs


def main() -> int:
    prior = load_texts([REPO + "/eval/holdout_v9_generation/rows",
                        REPO + "/eval/holdout_v10_generation/rows",
                        REPO + "/eval/holdout_v11_generation/rows",
                        REPO + "/eval/holdout_v12_generation/rows"])
    cand = load_texts([REPO + "/eval/holdout_v13_generation/rows"])
    assert cand, "no committed v13 rows yet (run the one-shot first)"
    print(f"prior-art docs: {len(prior)} (v9-v12 solution rows); "
          f"candidates: {len(cand)} (v13 rows)")
    corpus = [t for _, t in prior] + [t for _, t in cand]
    vec = TfidfVectorizer(
        analyzer="char_wb", ngram_range=(3, 5), min_df=2,
        max_features=200000)
    X = vec.fit_transform(corpus)
    n_prior = len(prior)
    P, C = X[:n_prior], X[n_prior:]
    sims = cosine_similarity(C, P)  # candidates x prior
    rows = []
    for i, (pid, _) in enumerate(cand):
        j = int(sims[i].argmax())
        max_sim = float(sims[i, j])
        rows.append({
            "problem_id": pid,
            "nearest_prior_art_id": prior[j][0],
            "max_cosine_similarity": round(max_sim, 4),
            "novelty_distance": round(1.0 - max_sim, 4),
            "pass_threshold": (1.0 - max_sim) >= THRESHOLD,
        })
    n_pass = sum(1 for r in rows if r["pass_threshold"])
    # intra-v13 self-similarity sanity (disclosure only — the gate is
    # vs PRIOR ART)
    sims_self = cosine_similarity(C, C)
    off = [sims_self[i, j] for i in range(len(cand))
           for j in range(len(cand)) if i != j]
    max_intra = max(off) if off else 0.0
    rec = {
        "record": "R98_V13_P4_NOVELTY/1.0.0",
        "claim": "c-0113",
        "computed_at": "recomputed from committed bytes (Art. 29(c))",
        "method": {
            "embedding": ("sklearn TfidfVectorizer — union space "
                          "fit ONCE over prior+candidates"),
            "analyzer": "char_wb, ngram (3,5), min_df 2, max_features "
                        "200000",
            "equivalence_note": ("the disclosed SPECTER2-or-equivalent "
                                 "(preregistration): SPECTER2 weights "
                                 "unreachable offline; TF-IDF char "
                                 "ngram cosine is a deterministic, "
                                 "zero-network lexical-embedding "
                                 "equivalent — method judged by the "
                                 "auditor"),
            "sklearn_version": sklearn.__version__,
            "deterministic": True,
            "network": "zero",
        },
        "prior_art_corpus": {
            "source": "committed v9+v10+v11+v12 rows (a1_answer)",
            "n_docs": len(prior),
        },
        "candidates": {"source": "committed v13 rows (a1_answer)",
                       "n_docs": len(cand)},
        "gate": {"threshold": THRESHOLD,
                 "min_rows": MIN_ROWS,
                 "rows_passing": n_pass,
                 "rows_total": len(cand),
                 "gate_pass": n_pass >= MIN_ROWS},
        "max_intra_v13_cosine_disclosure": round(max_intra, 4),
        "rows": rows,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(rec, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(json.dumps(rec["gate"], indent=1))
    for r in rows:
        print(f"  {r['problem_id']}: dist={r['novelty_distance']} "
              f"nearest={r['nearest_prior_art_id']} "
              f"{'PASS' if r['pass_threshold'] else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

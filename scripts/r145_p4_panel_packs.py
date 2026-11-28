#!/usr/bin/env python3
"""r145_p4_panel_packs.py — DIR-2 (the score-8 gate re-run): the
DETERMINISTIC prior-art packs for the calibrated-panel P4 run.

The rejected rung (the R145 direction): the 9/13 subset verdict used
a WITHIN-ANSWER contrast (the answer's own quoted standard practice
vs its own departure) — a proxy the owner rejected; the honest
full-set measures were 2/30 and 6.7%. The P4 non-obviousness gate is
now the CALIBRATED PANEL (V109-qualified judges) assessing each
candidate against EXTERNAL prior art via the problem-solution
approach (closest prior art -> distinguishing features -> objective
technical problem) — the EPO inventive-step shape, not a cosine band
and not a within-answer contrast.

This script builds what the judges see (zero LLM, deterministic):
  - the candidates: ALL 30 committed v16 inventions (the FULL set —
    no subsets, no marker cut);
  - the external prior art per candidate: the TOP-3 nearest prior-
    art SOLUTIONS from the committed v9-v12 holdout corpus (120
    docs, the standing AM48 corpus family), SPECTER2-retrieved —
    the same encoder + cache as the r99/r144 harness;
  - the presentation order of the 3 prior arts is sha-parity
    rotated per candidate (the blind-swap convention applied to the
    prior-art block; the candidate is labeled neutrally
    'CANDIDATE SOLUTION', never 'the engine's invention').

The reconciliation data (the rejected cuts, never discarded): each
pack carries the candidate's SPECTER2 nearest-prior distance, the
corpus pairwise p95 band, and the r144 within-answer pair cut where
extractable — the panel record reports all cuts side by side.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

OUT_DIR = REPO / "eval" / "r145_p4_panel"
OUT_DIR.mkdir(exist_ok=True)
OUT = OUT_DIR / "packs.json"

K_PRIOR = 3


def main() -> int:
    from r98_p4_novelty import load_texts
    from r99_p4_specter2 import load_model, encode

    tok, model = load_model()
    prior = load_texts([
        str(REPO / "eval/holdout_v9_generation/rows"),
        str(REPO / "eval/holdout_v10_generation/rows"),
        str(REPO / "eval/holdout_v11_generation/rows"),
        str(REPO / "eval/holdout_v12_generation/rows")])
    cand = load_texts([str(REPO / "eval/holdout_v16_generation")])
    scoring = json.loads(
        (REPO / "eval/v16_auditor_scoring.json").read_text())
    pp = scoring["per_problem"]
    print(f"prior docs {len(prior)} | candidates {len(cand)}",
          flush=True)

    P = encode(tok, model, [t for _, t in prior])
    C = encode(tok, model, [t for _, t in cand])
    sims = (C @ P.T)

    # the corpus's own pairwise distance band (the reconciliation
    # basis for the rejected distribution cut)
    import itertools
    import torch
    Psims = (P @ P.T)
    pair_d = sorted(float(1 - Psims[i, j].item()) for i, j in
                    itertools.combinations(range(P.size(0)), 2))
    p50 = pair_d[len(pair_d) // 2]
    p95 = pair_d[int(len(pair_d) * 0.95)]

    # the r144 within-answer pair cut (for the reconciliation table;
    # the rejected instrument's numbers, never discarded)
    r144 = json.loads(
        (REPO / "eval/r144_p4_production_rung.json").read_text())
    r144_pairs = {r["problem_id"]: r["novel_ranks_farther"]
                  for r in r144.get("pair_rows", [])}

    packs = []
    for i, (pid, ans) in enumerate(cand):
        top = torch.topk(sims[i], K_PRIOR)
        arts = []
        for k in range(K_PRIOR):
            j = int(top.indices[k].item())
            arts.append({
                "prior_id": prior[j][0],
                "text": prior[j][1],
                "cosine": round(float(top.values[k].item()), 4),
            })
        # sha-parity rotation of the prior-art presentation order
        h = int(hashlib.sha256(f"{pid}::r145pack".encode())
                .hexdigest(), 16)
        if h % 2 == 1:
            arts = list(reversed(arts))
        nearest_d = round(float(1 - top.values[0].item()), 4)
        packs.append({
            "problem_id": pid,
            "auditor_score_v16": pp.get(pid),
            "problem_text": None,   # filled by the runner from probs
            "candidate_text": ans,
            "prior_arts": arts,
            "specter2_nearest_distance": nearest_d,
            "corpus_band": {"p50": round(p50, 4),
                            "p95": round(p95, 4)},
            "inside_self_similarity_band": nearest_d < p95,
            "r144_within_answer_novel": r144_pairs.get(pid),
        })

    rec = {
        "record": "R145_P4_PANEL_PACKS/1.0.0",
        "claim": "c-0243", "session": "builder-r144s1",
        "at": "2026-11-24 (sandbox clock)",
        "design": ("the calibrated-panel P4 re-run's deterministic "
                   "inputs: ALL 30 v16 candidates (the FULL set), "
                   f"each with its top-{K_PRIOR} SPECTER2-nearest "
                   "prior-art SOLUTIONS from the committed v9-v12 "
                   "corpus (120 docs), sha-parity presentation "
                   "rotation; the rejected cuts carried for the "
                   "reconciliation (never discarded)"),
        "n_candidates": len(packs),
        "n_prior_corpus": len(prior),
        "corpus_band": {"p50": round(p50, 4), "p95": round(p95, 4)},
        "packs": packs,
        "zero_generation": True,
        "deterministic": True,
    }
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False)
                   + "\n")
    n_in_band = sum(1 for p in packs
                    if p["inside_self_similarity_band"])
    print(f"packs: {len(packs)} | inside-band (reconciliation): "
          f"{n_in_band}/{len(packs)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

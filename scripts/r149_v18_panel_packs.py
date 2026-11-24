#!/usr/bin/env python3
"""r149s1 v18 SEALED PANEL PACKS — the deterministic prior-art packs
for the c-0259 arbitration over the v18 physics-correct rows.

Same method as the r145 sealed packs (one source of truth): ALL 30 v18
candidates (the FULL set — the score-8 accept is on the full set), each
with its top-3 SPECTER2-nearest prior-art SOLUTIONS from the committed
v9-v12 corpus, sha-parity presentation rotation (the blind-swap
convention; the candidate labeled neutrally), the corpus pairwise band
carried for the reconciliation. Zero generation, zero LLM: the packs
are a deterministic packaging of already-landed bytes (Art. 18/22).
"""
from __future__ import annotations

import glob
import hashlib
import itertools
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

OUT_DIR = REPO / "eval" / "r149_v18_panel"
OUT_DIR.mkdir(exist_ok=True)
OUT = OUT_DIR / "packs_sealed_set.json"
K_PRIOR = 3


def main() -> int:
    from r98_p4_novelty import load_texts
    from r99_p4_specter2 import load_model, encode

    # the v18 candidates (the landed physics-correct rows)
    cand = []
    for f in sorted(glob.glob(str(
            REPO / "eval/holdout_v18_physics_generation/v17-*.json"))):
        d = json.loads(Path(f).read_text())
        cand.append((d["problem_id"], d["a1_answer"]))
    assert len(cand) == 30, f"expected 30 v18 rows, got {len(cand)}"

    prior = load_texts([
        str(REPO / "eval/holdout_v9_generation/rows"),
        str(REPO / "eval/holdout_v10_generation/rows"),
        str(REPO / "eval/holdout_v11_generation/rows"),
        str(REPO / "eval/holdout_v12_generation/rows"),
    ])
    print(f"prior docs {len(prior)} | v18 candidates {len(cand)}",
          flush=True)

    tok, model = load_model()
    P = encode(tok, model, [t for _, t in prior])
    C = encode(tok, model, [t for _, t in cand])
    sims = (C @ P.T)

    import torch
    Psims = (P @ P.T)
    pair_d = sorted(float(1 - Psims[i, j].item()) for i, j in
                    itertools.combinations(range(P.size(0)), 2))
    p50 = pair_d[len(pair_d) // 2]
    p95 = pair_d[int(len(pair_d) * 0.95)]

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
        h = int(hashlib.sha256(f"{pid}::r149pack".encode())
                .hexdigest(), 16)
        arts_rotated = list(reversed(arts)) if h % 2 == 1 else arts
        nearest_d = round(float(1 - top.values[0].item()), 4)
        packs.append({
            "problem_id": pid,
            "problem_text": None,   # filled by the runner from probs
            "candidate_text": ans,
            "prior_arts": arts,
            "prior_arts_rotated": arts_rotated,
            "nearest_cosine": round(float(top.values[0].item()), 4),
            "specter2_nearest_distance": nearest_d,
            "corpus_band": {"p50": round(p50, 4),
                            "p95": round(p95, 4)},
            "inside_self_similarity_band": nearest_d < p95,
        })

    rec = {
        "record": "R149_V18_PANEL_PACKS/1.0.0",
        "claim": "c-0260", "session_id": "builder-r147s1",
        "at": "2026-11-24 (sandbox clock)",
        "design": ("the v18 arbitration's deterministic inputs: ALL 30 "
                   "v18 physics-correct candidates (the FULL set), each "
                   f"with its top-{K_PRIOR} SPECTER2-nearest prior-art "
                   "SOLUTIONS from the committed v9-v12 corpus, "
                   "sha-parity presentation rotation; zero generation, "
                   "zero LLM — a packaging of landed bytes"),
        "n_candidates": len(packs),
        "n_prior_corpus": len(prior),
        "corpus_band": {"p50": round(p50, 4), "p95": round(p95, 4)},
        "packs": packs,
        "zero_generation": True,
        "deterministic": True,
    }
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    n_in_band = sum(1 for p in packs
                    if p["inside_self_similarity_band"])
    print(f"packs: {len(packs)} | inside-band (reconciliation): "
          f"{n_in_band} | OUT {OUT.relative_to(REPO)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

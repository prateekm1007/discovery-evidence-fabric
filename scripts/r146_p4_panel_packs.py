#!/usr/bin/env python3
"""r146s1 P4 packs — the r145 packs instrument re-pointed at the
r146 v17 NOVELTY-strength candidates (DIR-4: the panel must rate the
STRENGTHENED v17 generation, not the weak v16). The instrument is
byte-faithful to the validated r145 packs (the same prior corpus,
the same K_PRIOR=3 nearest-neighbor prior-art blocks, the same
sha-parity rotation, the same band reconciliation) with two typed
deltas: the auditor per-problem scores are None (the v17 r146 rows
are PENDING-AUDITOR — no cherry-picked proxy inputs), and the
candidate source is the r146 rows.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

OUT_DIR = REPO / "eval" / "r146_p4_panel"
OUT_DIR.mkdir(exist_ok=True)
OUT = OUT_DIR / "packs.json"

K_PRIOR = 3


def main() -> int:
    from r98_p4_novelty import load_texts
    from r99_p4_specter2 import load_model, encode

    prior = load_texts([
        str(REPO / "eval/holdout_v9_generation/rows"),
        str(REPO / "eval/holdout_v10_generation/rows"),
        str(REPO / "eval/holdout_v11_generation/rows"),
        str(REPO / "eval/holdout_v12_generation/rows")])
    cand = load_texts([str(REPO / "eval/holdout_v17_generation_r146")])
    print(f"prior docs {len(prior)} | candidates {len(cand)}",
          flush=True)
    assert len(cand) == 30, f"expected the full 30-candidate set, " \
        f"got {len(cand)} (no subsets)"

    tok, model = load_model()
    P = encode(tok, model, [t for _, t in prior])
    C = encode(tok, model, [t for _, t in cand])
    sims = (C @ P.T)

    import itertools
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
        h = int(hashlib.sha256(f"{pid}::r146pack".encode())
                .hexdigest(), 16)
        if h % 2 == 1:
            arts = list(reversed(arts))
        nearest_d = round(float(1 - top.values[0].item()), 4)
        packs.append({
            "problem_id": pid,
            "auditor_score": None,   # typed: the r146 rows are
            # PENDING-AUDITOR; no proxy inputs feed the instrument
            "problem_text": None,    # filled by the runner
            "candidate_text": ans,
            "prior_arts": arts,
            "nearest_prior_distance": nearest_d,
            "inside_band": bool(p50 * 0.5 <= nearest_d <= p95 * 1.5),
        })

    doc = {
        "record": "r146_p4_packs/1.0.0 — the r145 packs instrument "
                  "on the r146 v17 novelty-strength candidates "
                  "(DIR-4); the prior corpus + the rotation + the "
                  "band are byte-faithful; the auditor scores are "
                  "typed None (PENDING-AUDITOR)",
        "band": {"p50": round(p50, 4), "p95": round(p95, 4)},
        "n_candidates": len(packs),
        "packs": packs}
    OUT.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"packs written: {len(packs)} | band p50={p50:.4f} "
          f"p95={p95:.4f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

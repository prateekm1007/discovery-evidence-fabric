#!/usr/bin/env python3
"""r147s1 sealed-set panel packs — REBUILD the panel packs against
the SEALED-BYTES strengthened generation (the DIR-2 acceptance
subject).

TYPED MISTAKE-CAUGHT (the peer-catch discipline): the c-0252 lane's
committed packs.json was rebuilt at some point against the twin's
NON-sealed run (v17-01-rail-shelling ids, eval/
holdout_v17_generation_r146/ candidates — verified by byte-match),
so the R147 cent resume started judging the WRONG candidate set.
The wrong-set legs (hy4flash 1, dsv41 21, qw38 1 on rail-shelling
pids) are killed and stand as committed bytes on THEIR set, typed
NOT-counting toward the DIR-2 acceptance. The dsr1 legs are on the
SEALED-set pids (slurry-pump ids) — this script re-derives the
sealed-set retrieval and CHECKS the dsr1 legs' prior_order
fingerprint against it before they are counted.

Output: eval/r146_p4_panel/packs_sealed_set.json (the twin's
committed packs.json is NOT overwritten — Art. 4)."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
OUT = REPO / "eval" / "r146_p4_panel" / "packs_sealed_set.json"
K_PRIOR = 3
CORPUS_DIRS = [
    "eval/holdout_v9_generation/rows",
    "eval/holdout_v10_generation/rows",
    "eval/holdout_v11_generation/rows",
    "eval/holdout_v12_generation/rows",
]


def main() -> int:
    import torch
    from r99_p4_specter2 import load_model, encode
    from r98_p4_novelty import load_texts

    rows = []
    for f in sorted((REPO / "eval" /
                     "holdout_v17_strengthened_generation")
                    .glob("v17-*.json")):
        d = json.loads(f.read_text())
        rows.append((d["problem_id"], d["a1_answer"]))
    assert len(rows) == 30, f"expected 30 sealed rows, got {len(rows)}"
    print("candidates:", rows[0][0], "...", rows[-1][0])
    prior = load_texts([str(REPO / d) for d in CORPUS_DIRS])
    tok, model = load_model()
    P = encode(tok, model, [t for _, t in prior])
    C = encode(tok, model, [t for _, t in rows])
    sims = (C @ P.T)
    packs = []
    for i, (pid, ans) in enumerate(rows):
        top = torch.topk(sims[i], K_PRIOR)
        arts = [{"prior_id": prior[int(top.indices[k].item())][0],
                 "text": prior[int(top.indices[k].item())][1],
                 "cosine": round(float(top.values[k].item()), 4)}
                for k in range(K_PRIOR)]
        h = int(hashlib.sha256(f"{pid}::r146pack".encode())
                .hexdigest(), 16)
        rotated = list(reversed(arts)) if h % 2 == 1 else arts
        packs.append({
            "problem_id": pid,
            "candidate_text": ans,
            "prior_arts": arts,
            "prior_arts_rotated": rotated,
            "nearest_cosine": round(float(top.values[0].item()), 4),
        })
    OUT.write_text(json.dumps({
        "record": "R147_PANEL_PACKS_SEALED_SET/1.0.0",
        "retrieval": ("SPECTER2 against each SEALED-BYTES "
                      "strengthened candidate text; the standing "
                      "AM48 corpus family (120 docs); the sha-parity "
                      "presentation rotation (r146pack) carried as "
                      "prior_arts_rotated"),
        "mistake_caught": ("the c-0252 committed packs.json carried "
                           "the NON-sealed rail-shelling candidates "
                           "(byte-verified); this rebuild points the "
                           "panel at the DIR-2 acceptance subject"),
        "packs": packs}, indent=1) + "\n")
    # the dsr1 fingerprint check
    import glob
    ok = bad = 0
    for lf in sorted(glob.glob(str(REPO / "eval/r146_p4_panel/"
                                     "dsr1__v17-*.json"))):
        leg = json.loads(Path(lf).read_text())
        pid = leg["pid"]
        pack = next(p for p in packs if p["problem_id"] == pid)
        orders = [[a["prior_id"] for a in pack["prior_arts"]],
                  [a["prior_id"] for a in pack["prior_arts_rotated"]]]
        match = leg["prior_order"] in orders
        ok += match
        bad += (not match)
    print(f"dsr1 prior_order fingerprint: {ok} match, {bad} mismatch")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""r146s1 prior-art packs — the GENERATION-TIME EPO problem-solution
input (DIR 2, R145-F1): for each SEALED v17 problem, the top-3
SPECTER2-nearest solutions from the committed v9-v12 corpus (the
standing AM48 corpus family — EXTERNAL prior art, not the answer's
own quoted standard practice). Cached to eval/r146_novelty/
prior_art_packs.json; the sha-parity rotation of the presentation
order rides the DRIVER (the same discipline as the panel packs), so
the cache stays a pure retrieval record."""
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
OUT_DIR = REPO / "eval" / "r146_novelty"
OUT_DIR.mkdir(exist_ok=True)
OUT = OUT_DIR / "prior_art_packs.json"
K_PRIOR = 3

CORPUS_DIRS = [
    "eval/holdout_v9_generation/rows",
    "eval/holdout_v10_generation/rows",
    "eval/holdout_v11_generation/rows",
    "eval/holdout_v12_generation/rows",
]


def main() -> int:
    import torch  # noqa: F401
    from r99_p4_specter2 import load_model, encode
    from r98_p4_novelty import load_texts
    import subprocess

    sealed = json.loads(subprocess.run(
        ["git", "show",
         "origin/audit/r11-auditor-verdict-20261114:eval/holdout_v17/"
         "problems.json"],
        capture_output=True, text=True).stdout)
    probs = sealed.get("problems") if isinstance(sealed, dict) else sealed

    tok, model = load_model()
    prior = load_texts([str(REPO / d) for d in CORPUS_DIRS])
    print(f"prior docs {len(prior)} | problems {len(probs)}", flush=True)
    P = encode(tok, model, [t for _, t in prior])
    Q = encode(tok, model, [str(p.get("problem", "")) for p in probs])
    sims = (Q @ P.T)

    packs = {}
    for i, p in enumerate(probs):
        pid = p["problem_id"]
        top = torch.topk(sims[i], K_PRIOR)
        arts = []
        for k in range(K_PRIOR):
            j = int(top.indices[k].item())
            arts.append({
                "prior_id": prior[j][0],
                "text": prior[j][1],
                "cosine": round(float(top.values[k].item()), 4),
            })
        packs[pid] = {
            "failure_class_query": str(p.get("problem", ""))[:120],
            "prior_arts": arts,
            "nearest_cosine": arts[0]["cosine"],
            "pack_sha256_16": hashlib.sha256(json.dumps(
                [a["prior_id"] for a in arts], sort_keys=True)
                .encode()).hexdigest()[:16],
        }
        print(pid, "->", ", ".join(a["prior_id"] for a in arts),
              flush=True)
    OUT.write_text(json.dumps({
        "record": "R146_PRIOR_ART_PACKS/1.0.0",
        "retrieval": ("SPECTER2 (the standing AM48 corpus family), "
                      "query = the sealed problem text, top-3, the "
                      "v9-v12 committed corpus (120 docs); the "
                      "presentation-order parity rotation rides the "
                      "driver"),
        "corpus_dirs": CORPUS_DIRS,
        "packs": packs,
    }, indent=1) + "\n")
    print("cached ->", OUT, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

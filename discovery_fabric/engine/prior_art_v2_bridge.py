"""Engine bridge to the R376 collision core.

Thin adapter so run.py's grid/ensemble candidate path and the COLLISION
stage share ONE collision authority (Art. X) without the engine package
importing prior_art_v2 internals inline. Returns the (collision, prior_art)
pair in the same shapes the COLLISION adapter applies to the envelope.
"""
from __future__ import annotations

from typing import Any, Dict


def candidate_collision(mechanism_map: Dict[str, Any],
                        problem: Dict[str, Any]) -> Dict[str, Any]:
    """Run the mechanism-centered collision for ONE candidate's mechanism
    map. Used for grid/ensemble candidates so each is differentiated
    against art searched for ITS OWN mechanism (R376 defect class E).
    Raises on infrastructure failure — the caller records the honest
    UNRESOLVED state (never inherited art, never fabricated absence)."""
    from discovery_fabric.prior_art_v2.collision_resolution import (
        run_collision)
    collision = run_collision(mechanism_map, problem)
    resolution = collision["differentiation_resolution"]
    prior_art = {
        "prior_art_status": resolution["state"],
        "differentiation_resolution": resolution,
        "state_vocabulary": "collision_resolution R376 + classify/v4",
        "note": ("per-candidate collision re-run (grid/ensemble path); "
                 "the naive candidate's collision results are NOT "
                 "inherited"),
    }
    return {"collision": collision, "prior_art": prior_art}


# ---------------------------------------------------------------------------
# SPECTER2 (R133 DIR-4 / R132-F2): the P4 prior-art cosine gate's
# deterministic embedding instrument, as ENGINE code. The HF-hosted
# adapter (allenai/specter2 over allenai/specter2_base) runs LOCALLY
# (torch CPU) — no inference-API dependence (the api-inference host
# is not on the sandbox egress allowlist; the hub CDN is).
# ---------------------------------------------------------------------------
SPECTER2_MODEL_IDS = ("allenai/specter2_base", "allenai/specter2")
SPECTER2_DIM = 768
_SPECTER2_STATE: dict = {}


def _specter2_model():
    """Lazy singleton: tokenizer + base + the specter2 adapter
    (Stack-active). Deterministic: eval mode, no dropout, no
    sampling; the CLS-pool convention (the specter lineage)."""
    if _SPECTER2_STATE.get("model") is not None:
        return _SPECTER2_STATE["tok"], _SPECTER2_STATE["model"]
    import torch  # noqa: F401 — local-only; the typed import error
    # class below keeps the engine importable without torch
    from adapters import AutoAdapterModel  # the documented route
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(SPECTER2_MODEL_IDS[0])
    model = AutoAdapterModel.from_pretrained(SPECTER2_MODEL_IDS[0])
    model.load_adapter(SPECTER2_MODEL_IDS[1], set_active=True,
                       load_as="specter2")
    model.eval()
    _SPECTER2_STATE.update(tok=tok, model=model)
    return tok, model


class Specter2Unavailable(RuntimeError):
    """TYPED refusal: the local torch/adapters/transformers stack
    (or the cached model weights) is absent — the cosine gate NEVER
    falls back to a cheaper embedding (fail-closed, Art. 3)."""


def specter2_embed(text: str) -> list:
    """One text -> one 768-dim unit-normalized vector (CLS-pool,
    L2-normalized; deterministic across calls, seeds and processes —
    no dropout, no sampling, fixed weights). Raises
    Specter2Unavailable when the stack is absent."""
    try:
        import numpy as np
        import torch
    except ImportError as e:
        raise Specter2Unavailable(
            f"the local embedding stack is absent: {e}") from e
    tok, model = _specter2_model()
    inp = tok(text or " ", padding=True, truncation=True,
              return_tensors="pt", max_length=512)
    with torch.no_grad():
        out = model(**inp)
    vec = out.last_hidden_state[:, 0, :].squeeze(0).numpy()
    norm = float(np.linalg.norm(vec))
    if norm == 0.0:  # degenerate input -> typed, never a zero vector
        raise Specter2Unavailable("zero-norm embedding (degenerate)")
    return (vec / norm).tolist()


def specter2_cosine(a: str, b: str) -> float:
    """Cosine similarity of two texts' SPECTER2 embeddings (inputs
    L2-normalized in specter2_embed, so this is the dot product)."""
    import numpy as np
    va, vb = np.asarray(specter2_embed(a)), np.asarray(specter2_embed(b))
    return round(float(va @ vb), 6)


def specter2_separation(known_novel: list, known_obvious: list,
                        prior_art_corpus: list) -> dict:
    """The P4 prior-art gate instrument: mean cosine-to-corpus of the
    KNOWN-NOVEL controls minus that of the KNOWN-OBVIOUS controls.
    Separation >= 0.2 (the P4 gate value) with every control's
    nearest-corpus cosine reported. Deterministic; cross-seed stable
    (no hash-order containers in the math — inputs are sequences)."""
    import numpy as np
    corpus_vecs = [np.asarray(specter2_embed(t)) for t in prior_art_corpus]
    def mean_cos(text):
        v = np.asarray(specter2_embed(text))
        return float(np.mean([v @ c for c in corpus_vecs]))
    nov = [round(mean_cos(t), 6) for t in known_novel]
    obv = [round(mean_cos(t), 6) for t in known_obvious]
    sep = round(float(np.mean(nov) - np.mean(obv)), 6)
    return {
        "instrument": "allenai/specter2 (adapter over base, CLS-pool, "
                      "L2-normalized, local CPU)",
        "known_novel_mean_cos": round(float(np.mean(nov)), 6),
        "known_obvious_mean_cos": round(float(np.mean(obv)), 6),
        "separation": sep,
        "gate_ge_0.2": bool(sep >= 0.2),
        "n_novel": len(nov), "n_obvious": len(obv),
        "n_corpus": len(corpus_vecs),
        "per_control": {"novel": nov, "obvious": obv},
        "determinism": "eval mode, fixed weights, no sampling; "
                       "identical across calls/seeds/processes",
    }


# ---------------------------------------------------------------------------
# The RETRIEVAL-DISTANCE instrument (R134 DIR-3 / R133-F2): prior-art
# novelty as a RANKING problem (AUC of novel-vs-obvious retrieval
# distance) + the nearest-K prior-claim retrieval distance, per the
# literature's retrieval-based novelty (nearest-50 cosine, threshold
# ~0.75) — NOT a fixed per-problem absolute margin. Deterministic.
# ---------------------------------------------------------------------------
def specter2_auc(known_novel: list, known_obvious: list,
                 prior_art_corpus: list) -> dict:
    """The RANKING form of the separation gate: for every control,
    the retrieval distance = 1 - max cosine to the prior-art corpus
    (the nearest-claim distance; the literature's retrieval form).
    AUC = P(novel's distance > obvious's distance) via Mann-Whitney U
    over all novel x obvious pairs. AUC 0.5 = no discrimination;
    1.0 = perfect ranking. This is the scale-free form the compressed
    cosine band (~0.84-0.94) needs — the margin compression that
    made the >=0.2 absolute gate unreachable does NOT compress the
    RANKING."""
    import numpy as np
    corpus_vecs = [np.asarray(specter2_embed(t))
                   for t in prior_art_corpus]

    def nearest_cos(text):
        v = np.asarray(specter2_embed(text))
        return float(np.max([v @ c for c in corpus_vecs]))

    nov_near = [round(nearest_cos(t), 6) for t in known_novel]
    obv_near = [round(nearest_cos(t), 6) for t in known_obvious]
    if not nov_near or not obv_near:
        return {"auc": None, "n_novel": len(nov_near),
                "n_obvious": len(obv_near)}
    u = (sum(1 for g in obv_near for b in nov_near if g > b)
         + 0.5 * sum(1 for g in obv_near for b in nov_near
                     if g == b))
    auc = round(u / (len(nov_near) * len(obv_near)), 6)
    return {
        "instrument": "SPECTER2 nearest-claim retrieval distance, "
                      "AUC(novel farther than obvious)",
        "novel_nearest_cos": nov_near,
        "obvious_nearest_cos": obv_near,
        "novel_mean_nearest": round(float(np.mean(nov_near)), 6),
        "obvious_mean_nearest": round(float(np.mean(obv_near)), 6),
        "auc_novel_farther": auc,
        "gate_auc_ge_0.8": bool(auc >= 0.8),
        "n_novel": len(nov_near), "n_obvious": len(obv_near),
        "n_corpus": len(corpus_vecs),
        "determinism": "identical across calls/seeds/processes",
    }


def specter2_retrieval_novelty(text: str, prior_art_corpus: list,
                               k: int = 5,
                               threshold: float = 0.75) -> dict:
    """The PER-CANDIDATE retrieval-distance verdict: the nearest-K
    prior claims by cosine (the retrieval form), the distance to the
    nearest claim, and the thresholded novelty flag. The threshold
    default (0.75) is the literature's retrieval threshold (NIH
    NOT-OD-26-087 nearest-50 form); the CALLER owns the corpus, the
    instrument is deterministic."""
    import numpy as np
    v = np.asarray(specter2_embed(text))
    sims = sorted(
        ((float(v @ np.asarray(specter2_embed(t))), i)
         for i, t in enumerate(prior_art_corpus)),
        reverse=True)
    nearest = sims[0][0] if sims else None
    return {
        "nearest_cos": round(nearest, 6) if nearest is not None else None,
        "nearest_k": [
            {"cos": round(s, 6), "index": i} for s, i in sims[:k]],
        "threshold": threshold,
        "novel_by_retrieval": (bool(nearest is not None
                                    and nearest < threshold)),
        "k": min(k, len(sims)) if sims else 0,
    }


def specter2_ica_separation(known_novel: list, known_obvious: list,
                            prior_art_corpus: list) -> dict:
    """The ICA-normalized dynamic-range test (R133-F2's second
    lever): whiten + ICA-rotate the pooled control+corpus embeddings,
    then measure the absolute-margin separation in the rotated space.
    ICA rotation preserves inner products' discrimination structure
    while re-scaling axes; IF the compression is an artifact of the
    raw CLS geometry, the rotated margin widens. Deterministic (fixed
    random_state; FastICA on n_components=min(dim, n_samples-1))."""
    import numpy as np
    try:
        from sklearn.decomposition import FastICA
    except ImportError as e:
        raise Specter2Unavailable(
            f"sklearn absent for the ICA test: {e}") from e
    texts = known_novel + known_obvious + prior_art_corpus
    n_nov, n_obv = len(known_novel), len(known_obvious)
    X = np.asarray([specter2_embed(t) for t in texts])
    n_comp = min(X.shape[1], X.shape[0] - 1)
    ica = FastICA(n_components=n_comp, random_state=0,
                  whiten="arbitrary-variance", max_iter=1000)
    Y = ica.fit_transform(X)
    # re-L2-normalize the rotated rows (unit vectors in the new basis)
    Yn = Y / np.maximum(
        np.linalg.norm(Y, axis=1, keepdims=True), 1e-12)
    corpus = Yn[n_nov + n_obv:]
    nov = Yn[:n_nov]
    obv = Yn[n_nov:n_nov + n_obv]
    nov_cos = [float(np.max([v @ c for c in corpus])) for v in nov]
    obv_cos = [float(np.max([v @ c for c in corpus])) for v in obv]
    sep = round(float(np.mean(obv_cos) - np.mean(nov_cos)), 6)
    return {
        "instrument": "SPECTER2 + FastICA rotation (random_state=0), "
                      "unit-normalized rows, nearest-claim cosine",
        "novel_nearest_cos": [round(c, 6) for c in nov_cos],
        "obvious_nearest_cos": [round(c, 6) for c in obv_cos],
        "ica_margin_obvious_minus_novel": sep,
        "raw_margin_reference": "+0.037 (the R133 record, same "
                                "controls, unrotated)",
        "dynamic_range_widened": None,  # filled by the caller
        "n_components": n_comp,
        "determinism": "FastICA random_state=0 — deterministic",
    }

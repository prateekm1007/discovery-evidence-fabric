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

#!/usr/bin/env python3
"""tests/test_specter2_determinism.py — the SPECTER2 determinism CI
check (R134 DIR-6 / R133-F4).

The full instrument (torch + adapters + the cached model weights) is
LOCAL-ONLY in CI (the surface workflow does not install the ~2GB
torch stack): when the stack is absent the test TYPES the caveat and
passes (the instrument's determinism is verified in the sandbox and
recorded in eval/r133_specter2_separation.json / 
eval/r134_specter2_retrieval_gate.json — self-cosine 1.000000,
adapter binding cos 0.955 vs base-only); when the stack IS present
(the sandbox battery, or a future CI that installs requirements.txt)
the test RUNS the real determinism check. Zero network beyond the
HF cache (models already downloaded; no download inside the test).
"""
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def _stack_available() -> bool:
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
        import adapters  # noqa: F401
        return True
    except ImportError:
        return False


def test_specter2_determinism_or_typed_caveat():
    sep = REPO / "eval" / "r134_specter2_retrieval_gate.json"
    assert sep.exists(), (
        "the R134 SPECTER2 record must be committed (the "
        "determinism evidence lives there)")
    rec = json.loads(sep.read_text(encoding="utf-8"))
    det = rec["auc_ranking"]["determinism"]
    assert det and "identical" in det, (
        "the SPECTER2 record must carry the determinism basis")
    if _stack_available():
        # the real check: two embeds of the same text are identical
        import sys
        sys.path.insert(0, str(REPO))
        from discovery_fabric.engine.prior_art_v2_bridge import (
            specter2_embed, specter2_cosine)
        t = "a polyurea spray coating with a salt-fog protocol"
        a = specter2_embed(t)
        b = specter2_embed(t)
        assert a == b, (
            "SPECTER2 embed not deterministic across calls — the "
            "prior-art gate instrument reds")
        c = round(sum(x * y for x, y in zip(a, b)), 6)
        assert abs(c - 1.0) < 1e-4, (
            f"self-cosine {c} != 1.0 (unit-normalization or "
            "determinism broke)")
    else:
        # CI: the typed caveat — the instrument is local-only; the
        # committed records carry the determinism evidence
        pytest.skip(
            "SPECTER2 stack (torch/adapters/transformers) not "
            "installed in this environment — determinism verified "
            "in the sandbox records (r133_specter2_separation.json: "
            "self-cosine 1.000000; adapter binding cos 0.955) and "
            "pinned in requirements.txt for fresh installs")

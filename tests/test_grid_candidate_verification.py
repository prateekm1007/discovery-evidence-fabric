#!/usr/bin/env python3
"""tests/test_grid_candidate_verification.py — the R137 DIR-4B
pin: grid candidates can no longer enter the engineering pool on
a lexical span score alone.

What is pinned (source-level contracts, no live transport):
1. run.py's grid pool-builder calls the CANONICAL
   verify_mechanism_support per grid candidate (the same
   instrument the lean path uses — one authority).
2. A CONTESTED candidate (contradicting evidence) is blocked from
   the pool (held for human review, recorded — never silently
   dropped, never admitted).
3. Every pooled grid candidate carries its
   mechanism_support_state; "discovery_verified" is true only for
   SUPPORTED/PARTIALLY_SUPPORTED — a lexical span_derivation
   alone never marks a candidate verified.
4. The exploration grid stays CONDITIONAL: the grid path only
   runs when the naive candidate was rejected AND adjudication is
   not blocked AND the evidence-verification entry gate passes.
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RUN = REPO / "discovery_fabric" / "engine" / "run.py"
SRC = RUN.read_text(encoding="utf-8")


def test_grid_builder_calls_canonical_verification():
    """The pool-builder must run the canonical instrument per grid
    candidate (not a local re-implementation)."""
    grid_block = SRC[SRC.index("E16-E/E16-F: the exploration grid"):
                     SRC.index("R401: the structured mechanism space")]
    assert "verify_mechanism_support" in grid_block, (
        "the grid pool-builder must call the canonical "
        "mechanism_space.verify_mechanism_support")
    assert "from .mechanism_space import" in grid_block


def test_contested_candidates_blocked():
    """A CONTESTED (contradicted) grid candidate must not enter
    the pool."""
    grid_block = SRC[SRC.index("E16-E/E16-F: the exploration grid"):
                     SRC.index("R401: the structured mechanism space")]
    assert "_verification_blocked" in grid_block, (
        "the CONTESTED block path must exist")
    # the blocked candidate is skipped before pool.append
    blocked_skip = re.search(
        r'if c\.get\("_verification_blocked"\):\n\s+continue',
        grid_block)
    assert blocked_skip, (
        "a blocked candidate must 'continue' before pool.append")


def test_pool_entries_carry_support_state():
    """Every pooled grid entry carries mechanism_support_state and
    an honest discovery_verified flag."""
    grid_block = SRC[SRC.index("E16-E/E16-F: the exploration grid"):
                     SRC.index("R401: the structured mechanism space")]
    assert '"mechanism_support_state"' in grid_block
    assert '"discovery_verified"' in grid_block
    # verified ONLY on the canonical support states
    assert re.search(
        r'"discovery_verified": bool\(\s*_sup and _sup\.get\(\s*'
        r'"mechanism_support_state"\) in \(\s*"SUPPORTED",\s*'
        r'"PARTIALLY_SUPPORTED"\)\)', grid_block), (
        "discovery_verified must key on the canonical verifier's "
        "own states — never on the lexical span score")


def test_grid_stays_conditional():
    """The grid runs ONLY on the rejected-naive path (never on
    every ordinary run)."""
    assert "if not self._naive_survivor and not adjudication_blocked:" \
        in SRC
    assert "SKIPPED_ADJUDICATION_BLOCKED" in SRC
    assert "SKIPPED_EVIDENCE_VERIFICATION_FAILED" in SRC


def test_verifier_instrument_is_llm_free():
    """The reused instrument is deterministic (zero LLM calls) —
    the grid fix adds no transport cost."""
    ms = (REPO / "discovery_fabric" / "engine"
          / "mechanism_space.py").read_text(encoding="utf-8")
    fn = ms[ms.index("def verify_mechanism_support"):
            ms.index("def ", ms.index("def verify_mechanism_support") + 10)]
    assert "llm" not in fn.lower().replace(
        "zero llm", "").replace("no llm", ""), (
        "verify_mechanism_support must stay deterministic — a "
        "verification instrument that calls a model would price "
        "the grid out of every ordinary run")

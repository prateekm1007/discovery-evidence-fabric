#!/usr/bin/env python3
"""tests/test_article15_cross_seed_determinism.py — EPISTEMIC v3.2.0
Art. 15 CI wiring (AM52/V49 ratification): CROSS-SEED DETERMINISM for the
engine's content hashes.

Grounded in F64: the original default=str canonicalization rotated set
iteration per process under PYTHONHASHSEED (seed-luck hashes) and a
sandbox-bound driver was committed-but-unreproducible. The c-0071 remedy
(sorted-set serialization; derived_at excluded from hashed fields) is
pinned here from CI: identical hashes across PYTHONHASHSEED 1/2/3/random,
in fresh subprocesses (not in-process), plus static guards on the hash
input construction.

Zero LLM. Deterministic. No external calls.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

_PROBE = r'''
import json, sys
sys.path.insert(0, ".")
from discovery_fabric.engine.candidate import sha256_obj

# Seed-sensitive input: sets/frozensets nested in dicts + strings whose
# dict ordering must not matter (sort_keys) — the F64 rotating classes.
seed_sensitive = {
    "ops": {"quench", "anneal", "passivate"},          # set
    "nested": {"tiers": frozenset(["t1", "t2", "t3"])},
    "ordering": {"z": 1, "a": 2, "m": {"b": 1, "a": 2}},
    "list_order_matters": [1, 2, 3],
}
print(json.dumps({
    "obj": sha256_obj(seed_sensitive),
    "str": sha256_obj("deterministic-string"),
    "set_alone": sha256_obj({"only-set": frozenset(["x", "y"])}),
}))
'''


def _probe(seed: str) -> dict:
    import os
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = seed
    r = subprocess.run([sys.executable, "-I", "-c", _PROBE],
                       capture_output=True, text=True, env=env,
                       cwd=REPO, timeout=60)
    assert r.returncode == 0, f"probe failed under seed {seed}: {r.stderr[-200:]}"
    return json.loads(r.stdout)


def test_hashes_identical_across_hash_seeds() -> None:
    """F64 class, CI-pinned: sha256_obj output is identical across
    PYTHONHASHSEED 1/2/3/random in fresh processes."""
    outs = {s: _probe(s) for s in ("1", "2", "3", "random")}
    ref = outs["1"]
    for seed, out in outs.items():
        assert out == ref, (
            f"hash output differs under PYTHONHASHSEED={seed} — seed-luck "
            "hashes (F64 class) are back: canonicalization must serialize "
            "every unordered container deterministically")


def test_canonical_default_sorts_sets_source_check() -> None:
    """Static guard: the canonical default serializes sets/frozensets as
    sorted string lists (the c-0071 remedy), not seed-order reprs."""
    src = (REPO / "discovery_fabric" / "engine" / "candidate.py").read_text(
        encoding="utf-8")
    assert "isinstance(o, (set, frozenset))" in src, (
        "_canonical_default must special-case sets/frozensets")
    assert "sorted(map(str, o))" in src, (
        "sets serialize SORTED (the seed-luck class, F64)")


def test_wall_clock_excluded_from_hashed_fields() -> None:
    """Static guard: derived_at (wall-clock) is excluded from the hashed
    derivation trace, and utc_now() is never inside candidate_hash or
    structured_hash input construction."""
    ms = (REPO / "discovery_fabric" / "engine" / "mechanism_space.py").read_text(
        encoding="utf-8")
    assert 'if k != "derived_at"' in ms, (
        "derived_at must be excluded from the hashed trace (F64)")
    cand = (REPO / "discovery_fabric" / "engine" / "candidate.py").read_text(
        encoding="utf-8")
    start = cand.index("def canonical_json")
    end = cand.index("@dataclass")
    hash_region = cand[start:end]
    assert "utc_now" not in hash_region and "now(" not in hash_region, (
        "no wall-clock inside the canonicalization/hash construction "
        "(the utc_now helper lives elsewhere and must stay there)")

#!/usr/bin/env python3
"""Article 15 determinism gate (epistemic constitution v3.2.0 CI
addition for F64; ratification claim c-0080).

TWO LEGS, BOTH ZERO-LLM:

Leg 1 — CROSS-SEED DETERMINISM: scripts/r59_seed_hash_probe.py runs
the integrated engine route over a fixed committed DEV problem and
prints candidate_id/candidate_hash + canonical digests. The test
invokes it under PYTHONHASHSEED 1/2/3/random and asserts byte-identical
stdout (the F64 failure mode: hashes rotating per process under
hash-seed luck; the pre-fix _content_words returned a SET and rotated
the scanner verdict).

Leg 2 — BYTE-IDENTICAL FRESH CLONE: a fresh `git clone` of the
working tree at HEAD reproduces the committed P1 regression artifact
(eval/r52_labelled_regression.json) BYTE-IDENTICALLY when the
deterministic driver runs inside the clone. "Reproducible" means
byte-identical, not merely "runs" (auditor constitution Art. 1 v1.3.0:
evidence that is sandbox-path-bound or hash-seed-dependent is
UNVERIFIED even when committed).

Both legs run in the queue workflow (pytest, no network).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SEEDS = ["1", "2", "3", "random"]


def _run_probe(seed: str) -> str:
    env = dict(os.environ, PYTHONHASHSEED=seed)
    out = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "r59_seed_hash_probe.py")],
        capture_output=True, text=True, env=env, timeout=300, cwd=str(REPO))
    assert out.returncode == 0, (
        f"seed probe failed under PYTHONHASHSEED={seed}: "
        f"{out.stderr[-300:]}")
    return out.stdout


def test_cross_seed_determinism_of_engine_content_hashes():
    ref = _run_probe(SEEDS[0])
    payload = json.loads(ref)
    assert payload["results"], "the probe produced no candidate results"
    for r in payload["results"]:
        assert r["candidate_id"], "candidate_id missing (unminted)"
        assert r["candidate_hash"], "candidate_hash missing (unminted)"
    for seed in SEEDS[1:]:
        other = _run_probe(seed)
        assert other == ref, (
            f"CONTENT HASHES ROTATE UNDER PYTHONHASHSEED={seed} — the "
            "F64 failure mode (seed-luck identity) is present in the "
            "measured path")


def test_fresh_clone_reproduces_the_p1_artifact_byte_identically():
    ref_bytes = (REPO / "eval" / "r52_labelled_regression.json") \
        .read_bytes()
    with tempfile.TemporaryDirectory(prefix="r59_fresh_clone_") as td:
        clone = Path(td) / "clone"
        cl = subprocess.run(
            ["git", "clone", "--quiet", "--no-hardlinks",
             str(REPO), str(clone)],
            capture_output=True, text=True, timeout=300)
        assert cl.returncode == 0, (
            f"fresh clone failed (typed): {cl.stderr[-300:]}")
        # the clone is at HEAD (same commit as the working tree)
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO),
                              capture_output=True, text=True).stdout.strip()
        clone_head = subprocess.run(["git", "rev-parse", "HEAD"],
                                    cwd=str(clone), capture_output=True,
                                    text=True).stdout.strip()
        assert clone_head == head, (
            f"clone at {clone_head[:9]} != worktree HEAD {head[:9]}")
        run = subprocess.run(
            [sys.executable, "scripts/r52_labelled_regression.py"],
            capture_output=True, text=True, timeout=600, cwd=str(clone))
        assert run.returncode == 0, (
            f"deterministic driver failed INSIDE the fresh clone "
            f"(typed): {run.stderr[-300:]}")
        reproduced = (clone / "eval" / "r52_labelled_regression.json") \
            .read_bytes()
        assert reproduced == ref_bytes, (
            "FRESH-CLONE REPRODUCTION IS NOT BYTE-IDENTICAL — the "
            "committed P1 artifact is sandbox-bound or environment-"
            "dependent (auditor Art. 1 v1.3.0: UNVERIFIED even when "
            "committed)")

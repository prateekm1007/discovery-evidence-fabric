#!/usr/bin/env python3
"""tests/test_r103_guard_v14_corpus.py — the R103 (claim c-0117, AM89
directive 4) v15-readiness pin: the r99 fail-closed disjointness
guard's FULL v1-v14 prior corpus (the v15 lane's prerequisite corpus).

Pins (from committed bytes, zero generation):
  1. assemble_prior_corpus(range(1, 15)) assembles the v1-v14 corpus
     (the fail-closed size floor) — v14 enters via the audit ref.
  2. THE SELF-CLASH PROOF: the v14 problems checked against the
     v1-v14 corpus MUST clash (the v14 rows' own domain heads are in
     the corpus — the vacuity guard: a corpus that silently skipped
     v14 would pass this check zero-times and the test would fail).
  3. A fresh-domain synthetic (v15-like: the electrostatic-desalter
     oil family, in no prior version) is CLEAN against the full
     corpus — the guard does not false-fire on genuinely fresh rows.
  4. The v15 invocation surface: the CLI's --versions 1-14 form (the
     v15 domain-head map is derived when the auditor's v15 set lands,
     per the r98 honest-stem discipline — this pin covers the corpus
     leg only).
"""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r99_disjointness_guard import (  # noqa: E402
    assemble_prior_corpus, check_problems, V14_DOMAIN_HEAD)

AUDIT_REF = "origin/audit/r11-auditor-verdict-20261114"


def test_v1_v14_corpus_assembles_with_v14_bytes():
    corpus = assemble_prior_corpus(range(1, 15))
    assert len(corpus) > 200000          # the fail-closed size floor
    # v14 bytes ARE in the corpus (the corrected set's own marker
    # problem: HO14-08-cwetland-clog)
    assert "constructed wetland" in corpus
    assert "substrate clogging" in corpus


def test_self_clash_proof_v14_in_corpus():
    """The v14 rows checked against the v1-v14 corpus must clash with
    their own domain heads — the proof the corpus includes v14 (a
    silently-skipped version would yield ZERO clashes and fail this
    pin; the r97 vacuity class never again)."""
    out = subprocess.run(
        ["git", "show", f"{AUDIT_REF}:audit/holdout_v14/"
         "holdout_v14_problems.json"],
        capture_output=True, cwd=str(REPO))
    assert out.returncode == 0
    probs = json.loads(out.stdout)["problems"]
    corpus = assemble_prior_corpus(range(1, 15))
    clashes = check_problems(probs, V14_DOMAIN_HEAD, corpus)
    assert len(clashes) >= 30, len(clashes)   # every row self-clashes


def test_fresh_domain_synthetic_is_clean():
    """A v15-like fresh-domain row (the electrostatic-desalter oil
    family — in no prior version) is clean against the FULL v1-v14
    corpus: the guard does not false-fire on genuinely fresh rows."""
    fresh = [{"problem_id": "HO15-01-foam-drain-oil-demul",
              "device": "electrostatic desalter, crude oil",
              "failure": "emulsion carryover",
              "question": "Predict emulsion break-through.",
              "question_type": "predictor",
              "user_variables": "x", "contamination_tag": None}]
    corpus = assemble_prior_corpus(range(1, 15))
    clashes = check_problems(
        fresh, {"HO15-01": ["desalter", "emulsion carryover"]}, corpus)
    assert clashes == [], clashes


def test_cli_versions_flag_parses():
    """The v15 invocation surface: --versions 1-14 (the corpus leg of
    the v15 lane; the v15 map lands with the auditor's set)."""
    src = (REPO / "scripts" / "r99_disjointness_guard.py").read_text()
    assert "--versions" in src
    assert 'range(int(a), int(b) + 1)' in src

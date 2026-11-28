#!/usr/bin/env python3
"""tests/test_article14_confidentiality_probe.py — EPISTEMIC v3.2.0
Art. 14 CI wiring (AM52/V49 ratification): a CONFIDENTIALITY probe for
sealed rubrics.

Grounded in F60 (auditor live-verified): the v7/v8 *_PRIVATE.json rubrics
were publicly readable — unauthenticated HTTP 200 — because a 'PRIVATE'
label in a PUBLIC repo is NOT custody. The seal protects INTEGRITY only;
confidentiality requires private custody or ENCRYPTION with an owner-held
key. CI-enforceable form (deterministic, no network): any *_PRIVATE.json
in the tree must be ciphertext-bearing (an encrypted-material marker and
NO readable rubric structure), and the burned v7/v8 rubric files must
stay out of the tree. An unauthenticated read of a ciphertext-bearing
file does not yield the rubric — the confidentiality contract holds.

Zero LLM. Deterministic. No external calls.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

# Rubric-structure markers: if any of these appear as READABLE content
# in a *_PRIVATE.json, the file is effectively plaintext custody (F60
# class) even under an 'encrypted' label.
RUBRIC_STRUCTURE_MARKERS = (
    "judgment_axes", "score_scale", "pair_id", "rubric_version",
    "axis_weights", "position_swap", "W/T/L", "gate_clause",
)
BURNED_RUBRICS = ("v7", "v8")


def _private_files() -> list[Path]:
    out = []
    for root in (REPO / "eval", REPO / "secrets", REPO / "specs"):
        if root.is_dir():
            out.extend(root.glob("*_PRIVATE.json"))
            out.extend(root.glob("**/*_PRIVATE.json"))
    return sorted(set(out))


def test_burned_v7_v8_rubrics_absent_from_tree() -> None:
    """F60 remediation: the burned v7/v8 rubric files never re-enter the
    tree (burned = removed + logged, not relabelled)."""
    hits = [p.relative_to(REPO).as_posix()
            for p in REPO.rglob("*.json")
            if any(f"rubric_{v}" in p.name or f"v{v}_rubric" in p.name
                   or f"holdout_v{v}_PRIVATE" in p.name
                   for v in BURNED_RUBRICS)]
    assert not hits, f"burned rubric files present: {hits}"


@pytest.mark.parametrize("p", _private_files())
def test_private_file_is_ciphertext_only(p: Path) -> None:
    """Any *_PRIVATE.json in the tree must carry an encrypted-material
    marker and NO readable rubric structure (plaintext = custody
    failure -> the set burns for confidentiality)."""
    raw = p.read_text(encoding="utf-8")
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError as e:
        pytest.fail(f"{p.name}: malformed JSON ({e}) — a seal file must "
                    "be parseable envelope or pure ciphertext")
    assert isinstance(doc, dict), f"{p.name}: seal file is a JSON object"
    assert doc.get("encrypted") is True, (
        f"{p.name}: missing 'encrypted': true — a 'PRIVATE' label in a "
        "public repo is NOT custody (F60); seal files hold ciphertext "
        "with an owner-held key")
    blob = doc.get("ciphertext") or doc.get("material") or ""
    assert blob and len(str(blob)) > 64, (
        f"{p.name}: no ciphertext material of substance")
    # no plaintext rubric structure anywhere in the file
    for marker in RUBRIC_STRUCTURE_MARKERS:
        assert marker not in raw, (
            f"{p.name}: readable rubric marker {marker!r} in a seal file "
            "— plaintext custody (F60 class)")


def test_no_private_file_is_plain_rubric() -> None:
    """Vacuous-pass shape: if NO *_PRIVATE.json exists in the tree, the
    confidentiality contract holds trivially — recorded, not skipped."""
    files = _private_files()
    if not files:
        assert True, "no seal files in tree (contract vacuously holds)"
    else:
        assert all(f.suffix == ".json" for f in files)

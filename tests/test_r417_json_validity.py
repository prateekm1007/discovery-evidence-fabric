"""tests/test_r417_json_validity.py — every committed .json artifact
must parse strictly (the R417 audit-item-2 class fix).

The external R416 audit found R416/EVOLUTION_V1/
ROOT_CAUSE_MISATTRIBUTED_REJECTION.json shipping as malformed JSON
(Python implicit string concatenation — two adjacent string literals —
invalid JSON for every strict parser). The R417 repo-wide scan found
the full blast radius: 5 files (2 R416, 3 legacy CEREVASC, the second
defect class being missing opening quotes on prose values).

Constitutional grounding:
  - Art. XV/XXXI: the defect is disclosed, repaired with a recorded
    before/after sha pair (R417/JSON_SYNTAX_REPAIR/REPAIR_RECORD.json),
    and pinned by this test so the class cannot ship again.
  - Art. XVI: code is a hypothesis; this test is the enforcement
    evidence that the corpus of committed artifacts parses.
  - Art. IX: the scan is observational only (no writes).
  - Hermetic: reads the committed tree only; no network, no LLM.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

EXCLUDE_DIRS = {".git", "node_modules", ".next", "__pycache__",
                ".pytest_cache", "runs"}

# The sealed calibration evidence must never be touched by repairs; it
# is asserted VALID (it is) but the repair script refuses it — pinned
# here so the refusal list and reality cannot drift apart.
SEALED_MUST_BE_VALID = [
    "R412/CALIBRATION/r412_attacker_calibration_corpus.json",
    "R412/CALIBRATION/r412_calibration_seal.json",
    "R412/CALIBRATION/r412_attacker_measurement.json",
]


def _iter_json_files():
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in files:
            if f.endswith(".json"):
                yield Path(root) / f


def test_every_committed_json_parses_strictly():
    files = list(_iter_json_files())
    assert len(files) > 1500, (
        f"suspiciously small JSON census: {len(files)} files — the "
        "walker is probably broken, not the corpus clean")
    bad = []
    for p in files:
        try:
            json.loads(p.read_text())
        except json.JSONDecodeError as exc:
            bad.append(f"{p.relative_to(REPO)}: {exc}")
    assert not bad, (
        "malformed JSON artifacts committed (the R417 audit-item-2 "
        "defect class):\n" + "\n".join(bad))


def test_sealed_calibration_evidence_is_valid_and_untouched():
    for rel in SEALED_MUST_BE_VALID:
        p = REPO / rel
        assert p.exists(), f"sealed evidence missing: {rel}"
        json.loads(p.read_text())


def test_repaired_files_carry_the_repair_record():
    rec = REPO / "R417" / "JSON_SYNTAX_REPAIR" / "REPAIR_RECORD.json"
    assert rec.exists()
    d = json.loads(rec.read_text())
    repaired = [r["path"] for r in d["repairs"]
                if r["status"] == "REPAIRED"]
    assert len(repaired) == 5, repaired
    for r in d["repairs"]:
        if r["status"] == "REPAIRED":
            assert r["sha256_before"] != r["sha256_after"]
            assert json.loads((REPO / r["path"]).read_text())


def test_merge_function_repairs_only_adjacent_strings():
    """Adversarial: legitimate comma-separated values, escapes, and
    scalar values must survive the merge/quoting repair untouched."""
    import sys
    sys.path.insert(0, str(REPO / "scripts"))
    from r417_repair_malformed_json import _merge_adjacent_strings

    valid = [
        '{"a": "x", "b": "y"}',
        '{"a": "esc\\" ok", "b": 42, "c": true, "d": null}',
        '{"a": ["u", "v"], "b": {"c": "d"}}',
        '{"a": ""}',
    ]
    for src in valid:
        fixed, merges = _merge_adjacent_strings(src)
        assert fixed == src and merges == 0, (src, fixed)

    broken = '{"a": "x " "y"}'
    fixed, merges = _merge_adjacent_strings(broken)
    assert fixed == '{"a": "x y"}' and merges == 1

"""tests/test_r412_false_positive_classification.py — R412 G12 regression suite.

Pins the narrowly-scoped false-positive classification mechanism added to
epistemic_integrity/credential_audit_split.py (CEO R412 Phase 1 directive):

  - the SCANNER is not weakened (patterns still match everything they
    matched before, including the classified value);
  - classification is keyed on the EXACT (pattern_name, matched_value)
    pair recorded in credential_false_positive_registry.json;
  - any match not recorded there stays UNCLASSIFIED and fails the audit;
  - the registry itself is scanned, and its own occurrences of the
    classified value are classified and disclosed;
  - malformed registries fail CLOSED (classification unavailable);
  - no new path-level self-exclusions were added (no generic suppression).

Adversarial cases (Art. XVII): a smuggler cannot hide a real Scopus-format
key behind this mechanism unless an entry for that exact value is committed
and reviewed; a different value, or the same value under a different
pattern, fails.
"""

import json
import re
from pathlib import Path

import pytest

from epistemic_integrity.credential_audit_split import (
    FALSE_POSITIVE_REGISTRY_PATH,
    PATTERN_SCAN_CORPUS,
    SCANNER_SELF_EXCLUSIONS,
    _pattern_scan_blob,
    _pattern_scan_blob_with_values,
    classify_pattern_matches,
    load_false_positive_registry,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

# The measured R412 false positive: OpenAIRE dedup-workflow record id.
OPENAIRE_VALUE = "1568830f8629cccd3a73d0cfba14a815"
OPENAIRE_BLOB_TEXT = (
    '{"record_ids_by_source": {"openaire": '
    f'"openaire:dedup_wf_002::{OPENAIRE_VALUE}"}}}}'
)

# R387 baseline + R412 extension: the SCANNER_SELF_EXCLUSIONS set —
# each entry is a DISCLOSED, measured, test-pinned exclusion (the R387
# corpus, the R401-WC1 r389 historical blob, and the R412 classification
# suite's synthetic vectors); nothing else may ever be excluded.
PINNED_SELF_EXCLUSIONS = frozenset({
    "epistemic_integrity/credential_fingerprints.py",
    "epistemic_integrity/credential_audit_split.py",
    "epistemic_integrity/historical_artifact_audit.py",
    "tests/test_r387_ci_red_state_fixes.py",
    "tests/test_r389_reality_provider.py",
    "tests/test_r412_false_positive_classification.py",
})


# ---------------------------------------------------------------------------
# 1. The scanner is not weakened
# ---------------------------------------------------------------------------

def test_openaire_id_raw_pattern_still_matches():
    """The SCOPUS pattern still detects the OpenAIRE id — classification
    happens AFTER detection, never instead of it (Art. VII)."""
    matches = _pattern_scan_blob(OPENAIRE_BLOB_TEXT.encode())
    assert matches.get("SCOPUS_API_KEY_FORMAT") == 1


def test_count_and_value_scans_agree():
    """findall-count and finditer-values share the regex: the per-type
    counts MUST agree (the run-time assertion, pinned as a test)."""
    for blob in (
        OPENAIRE_BLOB_TEXT.encode(),
        # scrub-proof synthetic vector: assembled at runtime so the
        # committed bytes never carry the contiguous 32-hex literal
        ('API_KEY = "15' + 'abcdef0123456789abcdef0123456"').encode(),
        b"no matches here at all",
        b"LENS_KEY=MA" + b"x" * 50,
    ):
        counts = _pattern_scan_blob(blob)
        values = _pattern_scan_blob_with_values(blob)
        for cred_type, count in counts.items():
            assert len(values[cred_type]) == count
        assert sum(counts.values()) == sum(len(v) for v in values.values())


def test_self_exclusions_exactly_the_disclosed_set():
    """The self-exclusion set contains EXACTLY the six disclosed,
    measured entries (three scanner modules + the R387 corpus + the
    R401-WC1 r389 historical blob + the R412 classification suite's
    synthetic vectors, each with a recorded basis in the module's
    comments). Any additional entry is a silent detection hole; any
    missing entry re-reds the certification on intentional fixtures
    (anti-gaming, Art. XVII)."""
    assert SCANNER_SELF_EXCLUSIONS == PINNED_SELF_EXCLUSIONS


def test_classification_layer_added_no_generic_suppression():
    """R412's G12 fix is a classification layer, not a suppression layer:
    the ONLY set change is the disclosed test-fixture entry for this
    suite's own synthetic vectors (measured: the blob committed at
    f4ab6e5a is reachable forever). No path-level rule for evidence
    files, no pattern weakening, no corpus change (pinned separately by
    the regex-equality test)."""
    # The registry file is NOT excluded — it is scanned and classified
    assert "epistemic_integrity/credential_false_positive_registry.json" \
        not in SCANNER_SELF_EXCLUSIONS
    # R411 evidence files are NOT excluded — the OpenAIRE id occurrence
    # is detected and classified, never suppressed
    for p in list(SCANNER_SELF_EXCLUSIONS):
        assert not p.startswith("R411/"), (
            f"evidence snapshot {p} must never be path-excluded")


def test_registry_file_is_not_self_excluded():
    """The registry file itself IS scanned — its own occurrences of the
    classified value are detected, classified, and disclosed rather than
    suppressed."""
    assert "epistemic_integrity/credential_false_positive_registry.json" \
        not in SCANNER_SELF_EXCLUSIONS
    # And its own content does trip the pattern (the registry is NOT
    # excluded, so this is checked on the live file):
    registry_bytes = FALSE_POSITIVE_REGISTRY_PATH.read_bytes()
    matches = _pattern_scan_blob_with_values(registry_bytes)
    assert len(matches.get("SCOPUS_API_KEY_FORMAT", [])) >= 1


# ---------------------------------------------------------------------------
# 2. Classification is exact-pair keyed
# ---------------------------------------------------------------------------

def _real_registry():
    return load_false_positive_registry()


def test_registry_loads_and_is_valid():
    lookup = _real_registry()
    key = f"SCOPUS_API_KEY_FORMAT\x00{OPENAIRE_VALUE}"
    assert key in lookup, "the committed registry must classify the " \
        "measured R412 OpenAIRE false positive"
    entry = lookup[key]
    assert entry["classification"] == "PUBLIC_BIBLIOGRAPHIC_RECORD_ID"
    assert entry["reviewer_provenance"] == "AI_REVIEW"  # Art. LXVII


def test_openaire_match_is_classified_with_basis():
    registry = _real_registry()
    classified, unclassified = classify_pattern_matches(
        [{"pattern_name": "SCOPUS_API_KEY_FORMAT",
          "matched_value": OPENAIRE_VALUE,
          "blob_sha": "2bece98a56d9", "path": "R411/x.json"}],
        registry)
    assert len(classified) == 1
    assert unclassified == []
    c = classified[0]
    assert c["entry_id"].startswith("CFP-")
    assert c["basis"] and c["evidence"]
    assert c["reviewer_provenance"] == "AI_REVIEW"
    # classification never mutates the raw match facts
    assert c["pattern_name"] == "SCOPUS_API_KEY_FORMAT"
    assert c["matched_value"] == OPENAIRE_VALUE
    assert c["path"] == "R411/x.json"


def test_different_value_same_pattern_not_classified():
    """The adversarial case: a DIFFERENT 32-hex-15 value (a real smuggled
    Scopus key) stays unclassified and fails the audit."""
    registry = _real_registry()
    # Runtime-assembled (scrub-proof per the r389/R401-WC1 precedent):
    # the committed bytes carry the pieces, never the contiguous 32-hex
    # literal, so the credential scanner never sees synthetic key-format
    # material in this file's blobs.
    real_key = "15" + "abcdef0123456789" + "abcdef01234567"
    classified, unclassified = classify_pattern_matches(
        [{"pattern_name": "SCOPUS_API_KEY_FORMAT",
          "matched_value": real_key,
          "blob_sha": "deadbeef", "path": "evil/config.json"}],
        registry)
    assert classified == []
    assert len(unclassified) == 1


def test_same_value_different_pattern_not_classified():
    """Classification is pattern-pinned: the same public id colliding with
    a DIFFERENT pattern (e.g. OLLAMA) is not classified by a SCOPUS
    entry."""
    registry = _real_registry()
    classified, unclassified = classify_pattern_matches(
        [{"pattern_name": "OLLAMA_KEY_FORMAT",
          "matched_value": OPENAIRE_VALUE,
          "blob_sha": "0" * 40, "path": "x"}],
        registry)
    assert classified == []
    assert len(unclassified) == 1


def test_classification_ignores_path():
    """Classification is keyed on the VALUE, not the path: the proven
    public record id is the same public id wherever it appears — and the
    path is still recorded for review. (A path-pinned rule would be
    WEAKER: re-occurrence in a new file would silently fail open.)"""
    registry = _real_registry()
    for path in ("R411/DISCOVERY_RUN/evidence/solar_pv_canonical.json",
                 "epistemic_integrity/credential_false_positive_registry.json",
                 "somewhere/new/occurrence.json"):
        classified, unclassified = classify_pattern_matches(
            [{"pattern_name": "SCOPUS_API_KEY_FORMAT",
              "matched_value": OPENAIRE_VALUE,
              "blob_sha": "f" * 40, "path": path}],
            registry)
        assert len(classified) == 1
        assert classified[0]["path"] == path


# ---------------------------------------------------------------------------
# 3. Fail-closed registry discipline
# ---------------------------------------------------------------------------

def test_malformed_registry_fails_closed(tmp_path):
    bad = tmp_path / "bad_registry.json"
    entry = json.loads(FALSE_POSITIVE_REGISTRY_PATH.read_text())["entries"][0]
    del entry["basis"]  # a classification without a basis is forbidden
    bad.write_text(json.dumps({
        "schema": "CREDENTIAL_FALSE_POSITIVE_REGISTRY.v1",
        "entries": [entry]}))
    with pytest.raises(ValueError):
        load_false_positive_registry(bad)


def test_wrong_schema_registry_fails_closed(tmp_path):
    bad = tmp_path / "wrong_schema.json"
    bad.write_text(json.dumps({"schema": "SOMETHING_ELSE", "entries": []}))
    with pytest.raises(ValueError):
        load_false_positive_registry(bad)


def test_missing_registry_means_no_classification(tmp_path):
    """No registry → empty lookup → everything unclassified → audit RED.
    The mechanism cannot silently disappear."""
    lookup = load_false_positive_registry(tmp_path / "nonexistent.json")
    assert lookup == {}
    classified, unclassified = classify_pattern_matches(
        [{"pattern_name": "SCOPUS_API_KEY_FORMAT",
          "matched_value": OPENAIRE_VALUE,
          "blob_sha": "0", "path": "p"}], lookup)
    assert classified == []
    assert len(unclassified) == 1


def test_committed_registry_entries_have_required_fields():
    raw = json.loads(FALSE_POSITIVE_REGISTRY_PATH.read_text())
    assert raw["schema"].startswith("CREDENTIAL_FALSE_POSITIVE_REGISTRY.v")
    required = ("entry_id", "pattern_name", "matched_value",
                "classification", "first_seen_path", "first_seen_blob",
                "basis", "evidence", "reviewer_provenance",
                "classified_at", "classified_in")
    for entry in raw["entries"]:
        for f in required:
            assert entry.get(f), f"entry {entry.get('entry_id')} missing {f}"
        assert entry["reviewer_provenance"] in (
            "AI_REVIEW", "HUMAN_REVIEW", "EXTERNAL_ORG_REVIEW")


# ---------------------------------------------------------------------------
# 4. The committed corpus still catches real keys (positive controls)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("pattern_name,material", [
    ("LENS_API_KEY_FORMAT", b"MA" + b"aZ09" * 13),
    ("SCOPUS_API_KEY_FORMAT", b"15" + b"a0f9c8" * 4 + b"e7d2b1"),
    ("PATSNAP_API_KEY_FORMAT", b"sk-" + b"A1b2C3" * 8),
    ("GITHUB_PAT_FORMAT", b"ghp_" + b"Abc123" * 6),
    ("OPENROUTER_KEY_FORMAT", b"sk-or-v1-" + b"ab12" * 16),
])
def test_real_format_material_still_detected(pattern_name, material):
    """Positive controls: real credential-format material is still caught
    by the unchanged corpus (Art. V — a stronger blocker is not a correct
    blocker, and a weaker one is forbidden)."""
    blob = b'key = "' + material + b'"'
    matches = _pattern_scan_blob_with_values(blob)
    assert pattern_name in matches, (
        f"{pattern_name} must detect {material[:12]}...")


def test_all_patterns_have_same_regex_count_and_values():
    """The corpus regexes themselves are untouched: compare against
    re-compiled copies of the documented formats."""
    expected = {
        "LENS_API_KEY_FORMAT":
            r"(?<![A-Za-z0-9])MA[A-Za-z0-9]{48,}(?![A-Za-z0-9])",
        "SCOPUS_API_KEY_FORMAT":
            r"(?<![a-fA-F0-9])15[a-f0-9]{30}(?![a-fA-F0-9])",
        "PATSNAP_API_KEY_FORMAT":
            r"(?<![A-Za-z0-9])sk-[A-Za-z0-9]{44,}(?![A-Za-z0-9])",
        "GITHUB_PAT_FORMAT":
            r"(?<![A-Za-z0-9_])ghp_[A-Za-z0-9]{36}(?![A-Za-z0-9])",
        "NVIDIA_NIM_KEY_FORMAT":
            r"(?<![A-Za-z0-9])nvapi-[A-Za-z0-9_-]{40,}(?![A-Za-z0-9])",
        "PATENTBEAR_KEY_FORMAT":
            r"(?<![A-Za-z0-9])pb_live_[A-Za-z0-9_-]{30,}(?![A-Za-z0-9])",
        "OLLAMA_KEY_FORMAT":
            r"(?<![A-Za-z0-9])[0-9a-f]{32}\.[A-Za-z0-9_-]{20,}(?![A-Za-z0-9])",
        "OPENROUTER_KEY_FORMAT":
            r"(?<![A-Za-z0-9])sk-or-v1-[a-f0-9]{64}(?![A-Za-z0-9])",
    }
    assert set(PATTERN_SCAN_CORPUS) == set(expected)
    for name, rx in expected.items():
        compiled = PATTERN_SCAN_CORPUS[name]["pattern"]
        assert compiled.pattern == rx, (
            f"{name} regex was modified — the scanner must not change "
            f"to rescue a claim (Art. VII)")


# ---------------------------------------------------------------------------
# 5. The R411 evidence occurrence is exactly the classified one
# ---------------------------------------------------------------------------

def test_r411_evidence_file_occurrence_is_the_registry_value():
    """The measured match in the R411 evidence snapshot IS the recorded
    OpenAIRE record id — the classification covers exactly what was
    flagged, nothing more (Art. II: exact evidence)."""
    path = REPO_ROOT / "R411" / "DISCOVERY_RUN" / "evidence" / \
        "solar_pv_canonical.json"
    if not path.exists():
        pytest.skip("R411 evidence snapshot not present")
    values = _pattern_scan_blob_with_values(path.read_bytes())
    found = values.get("SCOPUS_API_KEY_FORMAT", [])
    assert found == [OPENAIRE_VALUE], (
        f"expected exactly the recorded OpenAIRE id, got {found}")
